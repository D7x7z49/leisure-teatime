# work/config/constants.py
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GlobalConfig:
    """Global configuration"""
    ROOT_DIR = Path(__file__).parent.parent

@dataclass
class PersistentConfig:
    """Global configuration"""
    EXECUTABLE_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    USER_DATA_DIR = GlobalConfig.ROOT_DIR / ".playwright_user_data"
    SCRIPT_TASKS_DIR = GlobalConfig.ROOT_DIR / "script"
    JS_TASKS_DIR = SCRIPT_TASKS_DIR / "js"
    PY_TASKS_DIR = SCRIPT_TASKS_DIR / "py"

@dataclass
class TasksConfig:
    """Task generation configuration"""
    TASKS_DIR = "tasks"
    DEFAULT_HTML = "index.html"
    DEFAULT_HTML_TEMPLATE = "<!-- Cached page -->"
    DEFAULT_MAIN = "main.py"
    DEFAULT_MAIN_TEMPLATE = "# MAIN TEMPLATE\n"
    IGNORED_SUBDOMAINS = ["www"]
    TEMPLATE_MAIN_PATH = GlobalConfig.ROOT_DIR / "config" / "TEMPLATE_MAIN.py"

@dataclass
class LogConfig:
    """Logging configuration"""
    LOG_DIR = GlobalConfig.ROOT_DIR / "logs"
    LOG_FORMAT = "%(message)s"
    LOG_LEVEL = "INFO"
    STEP_PREFIX = "[+]"
    DETAIL_PREFIX = "[-]"
