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

### AI Agent Assistant
- Natural language interface to control Android devices
- AI-powered decision making using ReAct loop
- Command confirmation mechanism (Execute / Reject / Stop)
- Intelligent observation parsing
- Dangerous command detection and warning
- API configuration import/export

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
cd Agent
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
Copyright (c) 2024-2025 Android Device Manager Contributors

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
