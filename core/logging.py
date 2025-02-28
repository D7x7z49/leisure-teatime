# core/logging.py
from pathlib import Path
import logging
import sys
from core.config import Config

# 局部常量
_LOG_DIR = Config.LOG.DIR
_LOG_LEVEL = Config.LOG.LEVEL
_LOG_FILE = Config.LOG.FILENAME

LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

def setup_logger(
    name: str,
    log_dir: str = _LOG_DIR,
    level: str = _LOG_LEVEL,
    console: bool = True,
    filename: str = _LOG_FILE,
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(LEVELS.get(level.lower(), logging.INFO))
    Path(log_dir).mkdir(exist_ok=True)
    file_handler = logging.FileHandler(Path(log_dir) / filename, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(file_handler)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console_handler)
    return logger

class LogTemplates:
    FETCH_START = "Fetching {url}"
    FETCH_SUCCESS = "Fetched {url} ({size} bytes)"
    TASK_CREATED = "Created task: {task_name}"
    ERROR = "Error: {msg}"

def get_logger(name: str, **kwargs) -> logging.Logger:
    return setup_logger(name, **kwargs)
