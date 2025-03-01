# core/config.py
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

class LogConfig:
    """Log-related configuration."""
    DIR = "logs"
    LEVEL = "info"
    FILENAME = "teatime.log"

class WorkConfig:
    """Work directory configuration."""
    ROOT = PROJECT_ROOT / "work"
    TASK_DIR = ROOT / "tasks"
    CACHE_DIR = ROOT / "cache"
    SCRIPT_DIR = ROOT / "scripts"
    TASK_CONFIG_FILE = ROOT / "config" / "tasks.json"
    SCRIPT_CONFIG_FILE = SCRIPT_DIR / "scripts.json"

class BrowserConfig:
    """Browser-related configuration."""
    TIMEOUT = 30000
    USER_DATA_DIR = WorkConfig.ROOT / ".browser"
    HEADLESS = False
    BLOCKED_RESOURCES: List[str] = ["**/*.{png,jpg,jpeg,gif}"]
    EXECUTABLE_PATH = os.getenv("LEISURE_TEATIME_BROWSER_EXECUTABLE_PATH")

class Config:
    """Global configuration."""
    LOG = LogConfig
    WORK = WorkConfig
    BROWSER = BrowserConfig
