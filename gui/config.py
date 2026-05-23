from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEPENDENCIES_DIR = BASE_DIR / "dependencies"
ADB_PATH = DEPENDENCIES_DIR / "adb.exe"
SCRCPY_PATH = DEPENDENCIES_DIR / "scrcpy.exe"
SCRIPTS_DIR = BASE_DIR / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)
HISTORY_DIR = BASE_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)

DEFAULT_LANG = "en-us"

NAV_PAGES = [
    ("home", "nav_home"),
    ("software", "nav_software"),
    ("display", "nav_display"),
    ("battery", "nav_battery"),
    ("adjust", "nav_adjust"),
    ("script", "nav_script"),
    ("agent", "nav_agent"),
]
