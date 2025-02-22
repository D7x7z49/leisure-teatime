# work/config/constants.py
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GlobalConfig:
    """Global configuration"""
    ROOT_DIR = Path(__file__).parent.parent

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
