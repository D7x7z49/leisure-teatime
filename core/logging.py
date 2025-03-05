# core/logging.py
from pathlib import Path
import logging
import sys
from core.config import Paths, StaticConfig

def setup_logger(
    name: str,
    log_dir: str = str(Paths.LOG_DIR),  # 转换为字符串以兼容现有逻辑
    level: str = StaticConfig.Log.LEVEL,
    console: bool = True,
    filename: str = StaticConfig.Log.FILENAME,
) -> logging.Logger:
    """设置并返回一个日志记录器"""
    logger = logging.getLogger(name)
    if logger.handlers:  # 避免重复添加处理器
        return logger

    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    logger.setLevel(LEVELS.get(level.lower(), logging.INFO))

    # 确保日志目录存在
    Path(log_dir).mkdir(exist_ok=True, parents=True)

    # 文件处理器
    file_handler = logging.FileHandler(Path(log_dir) / filename, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(file_handler)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console_handler)

    return logger

class LogTemplates:
    """日志消息模板"""
    FETCH_START = "Fetching {url}"
    FETCH_SUCCESS = "Fetched {url} ({size} bytes)"
    TASK_CREATED = "Created task: {task_name}"
    ERROR = "Error: {msg}"

def get_logger(name: str, **kwargs) -> logging.Logger:
    return setup_logger(name, **kwargs)
