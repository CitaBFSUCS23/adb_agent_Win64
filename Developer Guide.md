# Android Device Agent

A powerful Python-based GUI tool for managing Android devices via ADB, featuring AI-powered multi-agent collaboration, ReAct reasoning, and plugin-based architecture.

## Features

### Device Management
- Connect Android devices via USB or WiFi network debugging
- Real-time device information display (model, Android version, CPU, memory, battery, etc.)
- Quick device switching between multiple connected devices

### Screen Casting
- Low-latency screen mirroring using [scrcpy](https://github.com/Genymobile/scrcpy)
- Independent window with always-on-top option
- Screenshot capture and save

### Key Simulation (Always Accessible)
- Hardware button simulation: Back, Home, Recent Apps
- Volume controls: Volume Up, Volume Down, Mute
- Power button: Tap and Long-press (triggers system power menu with reboot/shutdown options)
- All buttons accessible from bottom bar on any page

### Software Management
- List all installed applications (All / System / Third-party)
- Enable/Disable applications
- Start/Force-stop applications
- Export APK files
- Clear application data
- Uninstall applications
- Install APK with one click

### Display Control
- View and modify screen resolution (with override support)
- View and modify DPI settings
- Auto-detect current override configurations

### Battery Simulation
- View detailed battery information
- Simulate AC/USB charging
- Set battery level
- Reset battery status

### Script Automation
- Create and save custom ADB script sequences
- Support for sleep/delay between commands
- Execute, stop, load, and delete scripts
- Button palette with categorized ADB commands (navigation, volume, power, touch, flow control)
- Interactive hint system: click a button to see parameter explanations
- Variable templates: commands use placeholders like `<x>`, `<y>`, `<duration_ms>` for easy customization
- File-based storage: scripts are saved as JSON in `scripts/` directory

### AI Agent Assistant
- **Solo Mode**: Single agent with ReAct loop (Reason → Action → Observation)
- **Corp Mode**: Multi-agent collaboration (Leader + Vision + Executor)
- Lazy-loading tool/skill details (token-efficient)
- Session memory with history compression
- Command confirmation mechanism (Execute / Reject / Stop)
- API configuration import/export
- **Tools Layer**: Fully plugin-based! Just add a .py file in `tools/`
  - ADBTool: Device control via ADB
  - PythonTool: Script execution on host
  - ScreenTool: Vision-based screen analysis
- **Skills Layer**: Fully plugin-based! Just add a .md file in `skills/`
  - Photo Export: Export photos from device
  - App Uninstall: Uninstall applications
  - Elderly Mode Setup: Configure device for elderly users
  - Screen Ops: Vision-based screen operations

### Performance Optimization
- **Multi-threaded Architecture**: All ADB operations run in background threads, UI never freezes
- **Parallel Command Execution**: Independent ADB commands within the same page execute concurrently
- **Thread-safe UI Updates**: All UI updates use Tkinter's `after()` method
- **Daemon Threads**: Background threads automatically clean up on application exit

## Architecture

### Unified Agent Architecture
The agent system features a single unified `Agent` base class with two modes:
- **Solo Mode** (`is_leader=False`): ReAct loop with direct tool execution
- **Corp Mode** (`is_leader=True`): Task decomposition + delegation to sub-agents

Key features:
- **Lazy-loading**: Tool/skill details injected only when first used
- **JSON Format**: Strict JSON response format with API-level enforcement
- **Context Compression**: Automatic history compression after 20 iterations
- **Skill Injection**: Markdown-based skill documentation injected on demand
- **Tool Context**: Shared API configuration across all tools

### Layers
```
┌─────────────────────────────────────────┐
│         Agent Layer (Unified)           │
│  ┌─────────────────────────────────┐    │
│  │ LeaderAgent (Corp Mode)         │    │
│  │ VisionAgent (Screen Perception) │    │
│  │ExecutorAgent (Command Execution)│    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│         Skills Layer (Markdown)         │
│     (Photo Export, App Uninstall, ...)  │
├─────────────────────────────────────────┤
│         Tools Layer (Plugin-based)      │
│  (ADBTool, PythonTool, ScreenTool, ...) │
├─────────────────────────────────────────┤
│      Device Control Layer (ADB/scrcpy)  │
└─────────────────────────────────────────┘
```

## Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.8 or higher
- **Android Device**: With USB debugging enabled
- **Dependencies**: ADB and scrcpy (included in `dependencies/`)

## Installation

1. Clone or download this repository
2. Ensure Python 3.8+ is installed
3. Enable USB debugging on your Android device:
   - Go to Settings > About Phone
   - Tap Build Number 7 times to enable Developer Options
   - Go to Settings > Developer Options > Enable USB Debugging
4. Connect your Android device via USB

## Usage

```bash
python gui/main.py
```

### First Launch
1. The application will automatically detect connected devices
2. Select your device from the dropdown list
3. Device information will be displayed on the home page

### Network Debugging
1. Go to Home page
2. Click "Network Debug" button
3. Enter IP address and port of the target device
4. Click "Connect"

### Screen Casting
1. Click "Screen Cast" button in the bottom bar
2. A new window will open with device screen mirroring
3. The window can be closed individually; click "Screen Cast" again to restart

### AI Agent (Solo Mode)
1. Go to Agent page
2. Configure your API (URL, Key, Model)
3. Click "Test API" to verify connection
4. Enter your task in the input box and click "Send"
5. Review AI-generated commands and click Execute/Reject/Stop

### AI Agent (Corp Mode)
1. Go to Agent page
2. Check "Agent Corp Mode"
3. Configure your API (use a vision-capable model like `qwen-vl-max`)
4. Enter your task and click "Send"
5. The agent will automatically coordinate between VisionAgent and ExecutorAgent

## Project Structure

```
adb_agent_Win64/
├── gui/
│   ├── main.py              # Main entry point and window layout
│   ├── config.py           # Configuration (ADB/scrcpy paths)
│   ├── i18n.py             # Internationalization support
│   ├── utils.py            # ADBClient class
│   ├── chat_session.py     # Session management
│   ├── pages/              # Page modules
│   │   ├── home_page.py    # Device selection and info
│   │   ├── software_page.py # App management
│   │   ├── display_page.py  # Resolution and DPI
│   │   ├── battery_page.py  # Battery info and simulation
│   │   ├── adjust_page.py   # Brightness and volume
│   │   ├── script_page.py   # Script management
│   │   └── agent_page.py    # AI Agent interface
│   └── widgets/            # Reusable components
│       ├── adb_terminal.py  # ADB command terminal
│       └── screen_cast.py   # Screen casting window
├── agents/                # Agent layer
│   ├── __init__.py        # Unified Agent base class + discovery
│   ├── agent_runtime.py   # Agent runner (Solo/Corp modes)
│   ├── leader_agent.py    # LeaderAgent (Corp mode)
│   ├── executor_agent.py  # ExecutorAgent (command execution)
│   └── vision_agent.py    # VisionAgent (screen perception)
├── tools/                 # Tools layer (plugin-based)
│   ├── __init__.py        # BaseTool + automatic loader
│   ├── adb_tool.py        # ADBTool - device control
│   ├── python_tool.py     # PythonTool - script execution
│   └── screen_tool.py     # ScreenTool - vision analysis
├── skills/                # Skills layer (plugin-based)
│   ├── photo_export.md    # Photo export skill
│   ├── app_uninstall.md   # App uninstall skill
│   ├── elderly_mode.md    # Elderly mode setup
│   └── screen_ops.md      # Vision-based screen ops
├── history/               # Session history (JSON)
├── dependencies/          # Binary dependencies
│   ├── adb.exe            # Android Debug Bridge
│   ├── scrcpy.exe         # Screen mirroring tool
│   ├── scrcpy-server      # scrcpy Android server
│   └── *.dll              # Required DLL files
├── language/              # Language packs
│   ├── zh-cn.json         # Simplified Chinese
│   └── en-us.json         # English
├── LICENSE               # Apache License 2.0
└── README.md             # This file
```

## Plugin Development Guide

### Adding New Tools (Tools Layer)

The system features a fully plugin-based tool architecture. To add a new tool:

1. Create a new file in `tools/` directory, e.g., `tools/my_tool.py`
2. Inherit from `BaseTool` and implement all abstract methods
3. That's it! No need to modify any other code - the tool is automatically discovered!

**Example Tool Structure:**

```python
from tools import BaseTool
from typing import Tuple


class MyTool(BaseTool):
    """My Custom Tool"""

    @property
    def name(self) -> str:
        """Tool name (uppercase, used for selection)"""
        return "MYTOOL"

    @property
    def description(self) -> str:
        """Tool description for AI prompt"""
        return "My custom tool for doing awesome things"

    @classmethod
    def requires_context(cls) -> bool:
        """Return True if your tool needs special initialization parameters"""
        return False  # or True if you need context

    @classmethod
    def get_init_params(cls) -> dict:
        """Return required initialization parameters if requires_context is True"""
        return {"param1": "Description of parameter 1"}

    def __init__(self, param1=None):
        """Initialize your tool"""
        self.param1 = param1

    def execute(self, command: str, context: dict = None) -> Tuple[str, bool]:
        """Execute the command and return (output, success)"""
        try:
            # Your implementation here
            return f"Result: {command}", True
        except Exception as e:
            return f"Error: {e}", False

    def get_prompt_section(self) -> str:
        """Return custom prompt section for this tool (optional)"""
        return f"""### Tool: {self.name}
- Purpose: {self.description}
- Syntax: TOOL: {self.name.upper()}, COMMAND: <command>
- Additional notes: Your tool's specific instructions here
"""
```

### Adding New Skills (Skills Layer)

Adding new skills is even easier!

1. Create a new Markdown file in `skills/` directory, e.g., `skills/my_skill.md`
2. Write your skill documentation in Markdown
3. That's it! The skill is automatically discovered!

**Example Skill Structure:**

```markdown
# Skill: My Skill Name

## Description
Brief description of what this skill does.

## Preconditions
- List any required conditions
- Device must be connected, etc.

## Steps
1. Step one explanation
2. Step two explanation
   - Substep details
3. Step three explanation

## Tips
- Helpful tip 1
- Helpful tip 2
```

### Agent Development (Agent Layer)

To add a new agent type:

1. Create a new file in `agents/` directory, e.g., `agents/my_agent.py`
2. Inherit from `Agent` base class
3. Implement `name` and `description` properties
4. Override `is_leader` if needed
5. Override `_output_format()` for custom format
6. That's it! The agent is automatically discovered!

**Example Agent:**

```python
from typing import Optional, override
from agents import Agent


class MyAgent(Agent):
    """My custom agent"""

    @property
    @override
    def name(self) -> str:
        return "MyAgent"

    @property
    @override
    def description(self) -> str:
        return "My custom agent that does awesome things"
```

## Language Support

- English (en-us)
- 简体中文 (zh-cn)

Switch language via the dropdown in the top-left corner. All interface elements will update immediately.

## Third-Party Open Source Software

| Software | License |
|----------|---------|
| [scrcpy](https://github.com/Genymobile/scrcpy) | Apache License 2.0 |

For full license text, see:
- [LICENSE](LICENSE) - Project license
- [dependencies/LICENSE-scrcpy.txt](dependencies/LICENSE-scrcpy.txt) - scrcpy license

## License

This project is licensed under the Apache License 2.0.

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.