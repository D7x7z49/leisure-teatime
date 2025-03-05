# core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.absolute()


class StaticConfig:
    """Static application configuration."""
    class Log:
        LEVEL = "info"
        FILENAME = "teatime.log"

    class Browser:
        HEADLESS = False
        TIMEOUT = 30000
        BLOCKED_RESOURCES: List[str] = ["**/*.{png,jpg,jpeg,gif}"]
        EXECUTABLE_PATH = os.getenv("LEISURE_TEATIME_BROWSER_EXECUTABLE_PATH")

    class Templates:
        FILES = [
            {"source": "MAIN.py", "target": "main.py"},
            {"source": "TEXT.py", "target": "text.py"},
            {"source": "TEST.py", "target": "test.py"}
        ]
        TUI_CMD_TEMPLATE = '''\
# {filename}
from core.fetchers.browser import AsyncBrowserManager

@AsyncBrowserManager.tui_cmd_register("{cmd_name}", help="""\
{help_text}

    USAGE:
      {cmd_name} <args>

    ARGUMENTS:
      args      Custom arguments for the command

    EXAMPLES:
      {cmd_name} example_arg
""")
async def tui_{func_name}(page, *args, **kwargs):
    """{docstring}"""
    return "Result: Command {cmd_name} executed with args: {{args}}"
'''


class Paths:
    """Path management for directories and files."""
    WORK_DIR = PROJECT_ROOT / "work"
    LOG_DIR = PROJECT_ROOT / "logs"
    BROWSER_DIR = PROJECT_ROOT / ".browser"
    TEMPLATES_DIR = PROJECT_ROOT / "templates"

    # Work subdirectories
    TASKS_DIR = WORK_DIR / "tasks"
    CACHE_DIR = WORK_DIR / "cache"
    SCRIPTS_DIR = WORK_DIR / "scripts"
    CONFIG_DIR = WORK_DIR / "config"

    # Data files
    TASKS_DATA = WORK_DIR / "tasks_data.json"
    SCRIPTS_DATA = WORK_DIR / "scripts_data.json"

    # Task-specific files
    RAW_HTML_FILE = "index.html"
    DOM_HTML_FILE = "dom.html"

    # Browser-specific
    BROWSER_DATA_DIR = BROWSER_DIR / "data"

    @staticmethod
    def ensure_all():
        """Ensure all directories and data files exist."""
        for attr, value in Paths.__dict__.items():
            if isinstance(value, Path):
                if attr.endswith("_DATA"):
                    value.parent.mkdir(exist_ok=True, parents=True)
                    if not value.exists():
                        value.touch()
                elif attr.endswith("_DIR"):
                    value.mkdir(exist_ok=True, parents=True)

Paths.ensure_all()
