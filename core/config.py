# core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import platform
from typing import Optional

WORKSPACE_ROOT = Path(__file__).parent.parent / "work"

def get_default_browser_executable_path() -> Optional[Path]:
    # Check environment variable
    env_path = os.getenv("LEISURE_BROWSER_EXECUTABLE_PATH")
    if env_path:
        return Path(env_path)

    # Check common default locations based on system
    system = platform.system().lower()
    possible_paths = []

    if system == "windows":
        possible_paths.extend([
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        ])
    elif system == "darwin":  # macOS
        possible_paths.append(
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        )
    elif system == "linux":
        possible_paths.extend([
            Path("/usr/bin/google-chrome"),
            Path("/usr/lib/chromium-browser/chrome"),
        ])

    for path in possible_paths:
        if path.exists():
            return path

    return None

class Config(BaseSettings):
    # logs
    log_level: str = "INFO"
    log_dir: Path = WORKSPACE_ROOT / "logs"

    # browser
    browser_executable_path: Optional[Path] = get_default_browser_executable_path()
    browser_user_data_dir: Path = WORKSPACE_ROOT / ".browser"
    browser_headless: bool = False
    browser_timeout: int = 60000

    # tasks
    tasks_dir: Path = WORKSPACE_ROOT / "tasks"
    tasks_metadata_file: Path = WORKSPACE_ROOT / "metadata.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LEISURE_",
        extra="ignore",
    )

    def ensure_exists(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        if not self.tasks_metadata_file.exists():
            self.tasks_metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tasks_metadata_file, "w", encoding="utf-8") as f:
                f.write('{"data": {}}')

CONFIG = Config()
CONFIG.ensure_exists()
