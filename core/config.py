# core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import platform
from typing import List, Optional

def get_default_browser_executable_path() -> Optional[Path]:
    env_path = os.getenv("LEISURE_BROWSER_EXECUTABLE_PATH")
    if env_path:
        return Path(env_path)

    system = platform.system().lower()
    possible_paths = (
        [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")
        ]
        if system == "windows" else
        [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
        if system == "darwin" else
        [Path("/usr/bin/google-chrome"), Path("/usr/lib/chromium-browser/chrome")]
    )
    path = next((p for p in possible_paths if p.exists()), None)
    if path is None:
        print("Warning: No default browser found. Set LEISURE_BROWSER_EXECUTABLE_PATH in .env.")
    return path

class Config(BaseSettings):
    # workspace
    template_dir: Path = Path(__file__).parent.parent / "templates"
    workspace_root: Path = Path(__file__).parent.parent / "work"

    # logs
    log_level: str = "INFO"
    log_dir: Path = workspace_root / "logs"
    log_filename: str = "leisure-teatime.log"

    # browser
    browser_executable_path: Optional[Path] = get_default_browser_executable_path()
    browser_user_data_dir: Path = workspace_root / ".browser"
    browser_headless: bool = False
    browser_timeout: int = 60000
    browser_cdp_port: int = 9222

    # browser launch args
    chrome_cdp_launch_args: List[str] = [
        f"--remote-debugging-port={browser_cdp_port}",
        f"--user-data-dir={browser_user_data_dir}",
        "--no-first-run",
        "--disable-popup-blocking",
        "--disable-extensions",
        "--disable-blink-features=AutomationControlled",
    ]

    # tasks
    tasks_dir: Path = workspace_root / "tasks"
    tasks_metadata_file: Path = workspace_root / "metadata.json"
    tasks_main_dir: Path = workspace_root / "main"

    # model config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LEISURE_",
        extra="ignore",
    )

    @property
    def log_path(self) -> Path:
        return self.log_dir / self.log_filename

    def ensure_exists(self) -> None:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
            self.tasks_dir.mkdir(parents=True, exist_ok=True)
            if not self.tasks_metadata_file.exists():
                self.tasks_metadata_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.tasks_metadata_file, "w", encoding="utf-8") as f:
                    f.write('{"data": {}}')
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to initialize workspace: {e}")

CONFIG = Config()
CONFIG.ensure_exists()
