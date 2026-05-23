#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Internationalization (i18n) Management

import json
from pathlib import Path
from gui.config import DEFAULT_LANG

BASE_DIR = Path(__file__).resolve().parent.parent
LANG_DIR = BASE_DIR / "language"

_current_tr = None

def set_lang(lang_code):
    global DEFAULT_LANG, _current_tr
    lang_file = LANG_DIR / f"{lang_code}.json"
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            _current_tr = json.load(f)
            DEFAULT_LANG = lang_code
    except Exception as e:
        print(f"Error loading language file: {e}")
        _current_tr = {}

def get_lang():
    return DEFAULT_LANG

def tr(key, **kwargs):
    if _current_tr is None:
        set_lang(DEFAULT_LANG)
    text = _current_tr.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text

def available_langs():
    langs = []
    for f in LANG_DIR.glob("*.json"):
        langs.append(f.stem)
    return sorted(langs)

set_lang(DEFAULT_LANG)