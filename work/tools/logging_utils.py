# work/tools/logging_utils.py
from dataclasses import dataclass
from functools import wraps
import logging
from datetime import datetime

from work.config.constants import LogConfig as LC
from work.tools.helpers import BaseContext

@dataclass
class LogControl:
    """Global log control settings"""
    quiet: bool = False
    silent: bool = False

log_control = LogControl()

file_logger = logging.getLogger("file_logger")
file_logger.setLevel(getattr(logging, LC.LOG_LEVEL))
file_handler = None
file_logger.propagate = False

console_logger = logging.getLogger("console_logger")
console_logger.setLevel(getattr(logging, LC.LOG_LEVEL))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LC.LOG_FORMAT))
console_logger.addHandler(console_handler)
console_logger.propagate = False

def set_log_file(file_name: str):
    """Set the log file for file_logger"""
    global file_handler
    LC.LOG_DIR.mkdir(exist_ok=True)
    if file_handler:
        file_logger.removeHandler(file_handler)
    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(logging.Formatter(LC.LOG_FORMAT))
    file_logger.addHandler(file_handler)
    file_logger.info(f"--- {datetime.now()} ---")

def logall_msg(message: str, level: str = "INFO", close_console: bool = False):
    """Log a message to both file and console with specified level."""
    level = level.upper()
    log_mapping = {
        "INFO": (file_logger.info, console_logger.info),
        "ERROR": (file_logger.error, console_logger.error),
        "WARNING": (file_logger.warning, console_logger.warning),
        "DEBUG": (file_logger.debug, console_logger.debug),
    }
    if level not in log_mapping:
        raise TypeError(f"level not found: {level}")

    file_log_func, console_log_func = log_mapping[level]
    file_log_func(message)
    if not close_console:
        console_log_func(message)

def log_step(func):
    """Decorator to log function steps from queue"""
    @wraps(func)
    def wrapper(context: BaseContext, *args, **kwargs):
        result = func(context, *args, **kwargs)
        while not context.log_queue.empty():
            msg: str = context.log_queue.get()
            file_logger.info(msg)
            if not log_control.silent and (not log_control.quiet or msg.startswith(LC.STEP_PREFIX)):
                console_logger.info(msg)
        return result
    return wrapper
