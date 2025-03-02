# core/config.py
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import List, Any

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

class LogConfig:
    """Log-related configuration."""
    DIR = PROJECT_ROOT / "logs"
    LEVEL = "info"
    FILENAME = "teatime.log"

class WorkConfig:
    """Work directory configuration."""
    ROOT = PROJECT_ROOT / "work"
    TASK_DIR = ROOT / "tasks"
    CACHE_DIR = ROOT / "cache"
    SCRIPT_DIR = ROOT / "scripts"
    CONFIG_DIR = ROOT / "config"
    TASK_CONFIG_FILE = CONFIG_DIR / "tasks.json"
    SCRIPT_CONFIG_FILE = CONFIG_DIR / "scripts.json"
    RAW_HTML_FILE = "index.html"
    DOM_HTML_FILE = "dom.html"

class BrowserConfig:
    """Browser-related configuration."""
    DIR = PROJECT_ROOT / ".browser"
    USER_DATA_DIR = DIR / "data"
    HEADLESS = False
    TIMEOUT = 30000
    BLOCKED_RESOURCES: List[str] = ["**/*.{png,jpg,jpeg,gif}"]
    EXECUTABLE_PATH = os.getenv("LEISURE_TEATIME_BROWSER_EXECUTABLE_PATH")

class TemplatesConfig:
    """Template-related configuration."""
    DIR = PROJECT_ROOT / "templates"
    FILES = [
        {"source": "MAIN.py", "target": "main.py"},
        {"source": "TEXT.py", "target": "text.py"},
        {"source": "TEST.py", "target": "test.py"}
    ]

class Config:
    """Global configuration."""
    LOG = LogConfig
    WORK = WorkConfig
    BROWSER = BrowserConfig
    TEMPLATES = TemplatesConfig

def ensure_paths(obj: Any, visited: set = None):
    """Recursively ensure all Path directories and files exist."""
    if visited is None:
        visited = set()
    if id(obj) in visited or not hasattr(obj, "__dict__"):
        return
    visited.add(id(obj))
    for name, value in vars(obj).items():
        if isinstance(value, Path):
            if name.endswith("_FILE"):
                value.parent.mkdir(exist_ok=True, parents=True)
                if not value.exists():
                    value.touch()
            else:
                value.mkdir(exist_ok=True, parents=True)
        else:
            ensure_paths(value, visited)

ensure_paths(Config)
