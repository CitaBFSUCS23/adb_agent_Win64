# Android Device Manager

A Python-based GUI tool for managing Android devices via ADB, featuring screen casting, script automation, and AI-powered agent assistance.

## Features

- **Device Management**: Connect and manage Android devices via USB or network
- **Screen Casting**: Low-latency screen mirroring using scrcpy
- **Key Simulation**: Simulate hardware button presses (Home, Back, Volume, Power, etc.)
- **Software Management**: Install, uninstall, enable/disable apps, export APK
- **Display Control**: Adjust screen resolution and DPI
- **Battery Simulation**: Simulate charging states and battery levels
- **Script Automation**: Run custom ADB script sequences
- **AI Agent**: Natural language control of Android devices through AI

## Third-Party Open Source Software

This project uses the following third-party software:

| Software | License | Copyright |
|----------|---------|-----------|
| [scrcpy](https://github.com/Genymobile/scrcpy) | Apache License 2.0 | Copyright (C) 2018 Genymobile, Copyright (C) 2018-2021 Romain Vimont |

For details, see the [LICENSE](LICENSE) file.

## Requirements

- Python 3.8+
- Windows OS
- Android device with USB debugging enabled
- ADB (included in `dependencies/`)

## Usage

```bash
# Run the GUI
python gui/main.py
```

## Project Structure

```
Agent/
├── gui/
│   ├── main.py          # Main entry point
│   ├── config.py        # Configuration
│   ├── i18n.py          # Internationalization
│   ├── utils.py         # ADB client utilities
│   ├── pages/           # Page modules
│   │   ├── home_page.py
│   │   ├── software_page.py
│   │   ├── display_page.py
│   │   ├── battery_page.py
│   │   ├── adjust_page.py
│   │   ├── script_page.py
│   │   └── agent_page.py
│   └── widgets/          # Widget components
│       ├── adb_terminal.py
│       └── screen_cast.py
├── dependencies/         # Binary dependencies
│   ├── adb.exe
│   ├── scrcpy.exe
│   └── ...
├── Language/             # Language packs
│   ├── zh-cn.json
│   └── en-us.json
└── LICENSE
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

This project uses scrcpy, which is also licensed under the Apache License 2.0.
