#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat session management module
"""
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
from typing import ClassVar, List, Dict, Any, Optional

from gui.config import BASE_DIR


@dataclass
class ChatMessage:
    """Chat message data model"""
    role: str  # user/assistant/system/thought/command/output/complete/error
    content: str
    timestamp: str = None
    message_id: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.message_id:
            self.message_id = f"msg_{int(datetime.now().timestamp() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        return cls(**data)


@dataclass
class ChatSession:
    """Chat session data model"""

    session_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[ChatMessage]
    MAX_CONTEXT: ClassVar[int] = 20
    device_id: str = None
    model_name: str = None
    is_corp_mode: bool = False

    @classmethod
    def create_new(cls, title) -> 'ChatSession':
        now = datetime.now().isoformat()
        return cls(
            session_id=f"session_{int(datetime.now().timestamp())}",
            title=title,
            created_at=now,
            updated_at=now,
            messages=[]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "device_id": self.device_id,
            "model_name": self.model_name,
            "is_corp_mode": self.is_corp_mode,
            "messages": [m.to_dict() for m in self.messages]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            session_id=data["session_id"],
            title=data["title"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=messages,
            device_id=data.get("device_id"),
            model_name=data.get("model_name"),
            is_corp_mode=data.get("is_corp_mode", False),
        )

    def add_message(self, message: ChatMessage) -> None:
        """Add a message"""
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID"""
        for i, msg in enumerate(self.messages):
            if msg.message_id == message_id:
                self.messages.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def get_llm_context(self, max_messages: int = None) -> List[Dict[str, str]]:
        """Return last N messages as LLM context — only role+content.
        
        Merges consecutive same-role messages to avoid invalid API input
        (e.g. thought + command both map to assistant → must be merged).
        """
        limit = max_messages or self.MAX_CONTEXT
        _map = {"user": "user", "thought": "assistant",
                "command": "assistant", "output": "user", "complete": "assistant"}
        raw: List[Dict[str, str]] = []
        for m in self.messages[-limit:]:
            r = _map.get(m.role)
            if r:
                raw.append({"role": r, "content": m.content})

        # Merge consecutive same-role messages
        merged: List[Dict[str, str]] = []
        for item in raw:
            if merged and merged[-1]["role"] == item["role"]:
                merged[-1]["content"] += "\n" + item["content"]
            else:
                merged.append(dict(item))
        return merged


class ChatSessionManager:
    """Chat session manager"""

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = BASE_DIR / "history"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        self._sessions: Dict[str, ChatSession] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all sessions from disk"""
        for f in self.storage_dir.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    session = ChatSession.from_dict(json.load(fp))
                    self._sessions[session.session_id] = session
            except Exception as e:
                print(f"Warning: Failed to load session {f}: {e}")

    def list_sessions(self) -> List[ChatSession]:
        """List all sessions, newest first"""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    def create_session(self, title) -> ChatSession:
        """Create a new session"""
        session = ChatSession.create_new(title)
        self._sessions[session.session_id] = session
        self.save_session(session)
        return session

    def save_session(self, session: ChatSession) -> None:
        """Save session to disk"""
        session.updated_at = datetime.now().isoformat()
        file_path = self.storage_dir / f"{session.session_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            file_path = self.storage_dir / f"{session_id}.json"
            file_path.unlink(missing_ok=True)
            return True
        return False

    def add_message_to_session(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        """Add message to a session"""
        session = self._sessions.get(session_id)
        if session:
            session.add_message(message)
            self.save_session(session)
            return session
        return None

    def delete_message_from_session(self, session_id: str, message_id: str) -> bool:
        """Delete message from a session"""
        session = self._sessions.get(session_id)
        if session:
            if session.delete_message(message_id):
                self.save_session(session)
                return True
        return False