# Android Device Manager

A powerful Python-based GUI tool for managing Android devices via ADB (Android Debug Bridge). Features include screen casting, device simulation, script automation, and AI-powered agent assistance.

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
- Variable templates: commands use placeholders like <x>, <y>, <duration_ms> for easy customization
- File-based storage: scripts are saved as JSON in `scripts/` directory, no internal database

### AI Agent Assistant
- Natural language interface to control Android devices
- AI-powered decision making using ReAct loop
- Command confirmation mechanism (Execute / Reject / Stop)
- Intelligent observation parsing
- Dangerous command detection and warning
- API configuration import/export
- **Tools Layer**: Fully plugin-based! Just add a .py file in tools/ directory that inherits from BaseTool
  - ADBTool: Device control via ADB
  - PythonTool: Script execution on host
- **Skills Layer**: Fully plugin-based! Just add a .md file in skills/ directory
  - Photo Export: Export photos from device
  - App Uninstall: Uninstall applications
  - Elderly Mode Setup: Configure device for elderly users

### Performance Optimization
- **Multi-threaded Architecture**: All ADB operations run in background threads, UI never freezes
- **Parallel Command Execution**: Independent ADB commands within the same page execute concurrently
  - Home page: 11+ getprop commands run in parallel (~10-15x faster)
  - Adjust page: 4 settings commands run in parallel (~3-4x faster)
  - Display page: wm size and density commands run in parallel (~2x faster)
- **Thread-safe UI Updates**: All UI updates use Tkinter's `after()` method for safe main-thread execution
- **Daemon Threads**: Background threads automatically clean up on application exit

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

### AI Agent
1. Go to Agent page
2. Configure your API (URL, Key, Model)
3. Click "Test API" to verify connection
4. Import/Export configuration as needed
5. Enter your task in the input box and click "Send"
6. Review AI-generated commands and click Execute/Reject/Stop

## Project Structure

```
Agent/
├── gui/
│   ├── main.py              # Main entry point and window layout
│   ├── config.py           # Configuration (ADB/scrcpy paths, default settings)
│   ├── i18n.py             # Internationalization support
│   ├── utils.py            # ADBClient class
│   ├── pages/              # Page modules
│   │   ├── home_page.py    # Device selection and info display
│   │   ├── software_page.py # App management
│   │   ├── display_page.py  # Resolution and DPI settings
│   │   ├── battery_page.py  # Battery info and simulation
│   │   ├── adjust_page.py   # Brightness and volume adjustment
│   │   ├── script_page.py   # Script management
│   │   └── agent_page.py    # AI Agent interface
│   └── widgets/            # Reusable components
│       ├── adb_terminal.py  # ADB command terminal
│       └── screen_cast.py   # Screen casting window
├── tools/                 # Tools layer (OpenClaw architecture, FULLY PLUGIN-BASED!)
│   ├── __init__.py        # BaseTool abstract base class and automatic tool loader
│   ├── adb_tool.py        # ADBTool - device control via ADB
│   └── python_tool.py     # PythonTool - script execution on host
├── skills/                # Skills layer (OpenClaw architecture, FULLY PLUGIN-BASED!)
│   ├── photo_export.md    # Photo export skill
│   ├── app_uninstall.md   # App uninstall skill
│   └── elderly_mode.md    # Elderly mode setup skill
├── dependencies/           # Binary dependencies
│   ├── adb.exe            # Android Debug Bridge
│   ├── scrcpy.exe         # Screen mirroring tool
│   ├── scrcpy-server      # scrcpy Android server
│   └── *.dll              # Required DLL files
├── Language/              # Language packs
│   ├── zh-cn.json         # Simplified Chinese
│   └── en-us.json         # English
├── LICENSE               # Apache License 2.0
└── README.md             # This file
```

## Plugin Development Guide

### Adding New Tools (Tools Layer)

The system features a **fully plugin-based tool architecture**. To add a new tool:

1. **Create a new file** in `tools/` directory, e.g., `tools/my_tool.py`
2. **Inherit from BaseTool** and implement all abstract methods
3. **That's it!** No need to modify any other code - the tool is automatically discovered!

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
        """Return custom prompt section for this tool (optional, has default)"""
        return f"""### Tool: {self.name}
- Purpose: {self.description}
- Syntax: TOOL: {self.name.upper()}, COMMAND: <command>
- Additional notes: Your tool's specific instructions here
"""
```

### Adding New Skills (Skills Layer)

Adding new skills is even easier!

1. **Create a new Markdown file** in `skills/` directory, e.g., `skills/my_skill.md`
2. **Write your skill documentation** in Markdown
3. **That's it!** The skill is automatically discovered!

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

### OpenClaw Architecture Alignment

This project now fully implements the OpenClaw architecture principles:
- **Tools Layer**: Abstract base class + plugin discovery
- **Skills Layer**: Markdown-based documentation + plugin discovery  
- **Memory Layer**: (Future work)
- **Plugins Layer**: (Future work for full plugin system)

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

This project is licensed under the **Apache License 2.0**.

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
