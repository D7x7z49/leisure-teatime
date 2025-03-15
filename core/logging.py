# core/logging.py
from pathlib import Path
import logging
import sys
import inspect
from typing import Literal, Optional
from pydantic import BaseModel, Field
from functools import wraps
from collections import defaultdict
import time
from core.config import CONFIG

# Log format constants
FILE_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
CONSOLE_LOG_FORMAT = "[%(levelname)-8s] %(name)-20s: %(message)s"

# Define restricted options (keep under 7)
ActionType = Literal["Starting", "Processing", "Paused", "Resumed", "Finished", "Error"]  # 6个
SubjectType = Literal["task", "url", "chain", "storage", "method"]  # 5个
LevelType = Literal["debug", "info", "warning", "error"]  # 4个

class LogMessage(BaseModel):
    action: ActionType = Field(..., description="The action being performed")
    subject: SubjectType = Field(..., description="The subject of the action")
    details: str = Field(..., description="Additional details about the action (required)")

    def format(self) -> str:
        return f"{self.action} {self.subject}: {self.details}"

class LogAnalyzer:
    """Tool class for logging statistics and performance analysis."""
    _stats = defaultdict(lambda: {"count": 0, "actions": set(), "subjects": set(), "total_time": 0, "errors": 0})

    @classmethod
    def analyze(cls, func):
        @wraps(func)
        def wrapper(self, level: LevelType):
            msg = self._msg
            if msg:
                key = self._logger.name
                start = time.time()
                result = func(self, level)
                elapsed = time.time() - start
                cls._stats[key]["count"] += 1
                cls._stats[key]["actions"].add(msg.action)
                cls._stats[key]["subjects"].add(msg.subject)
                cls._stats[key]["total_time"] += elapsed
                if level == "error":
                    cls._stats[key]["errors"] += 1
                return result
            return func(self, level)
        return wrapper

    @classmethod
    def get_stats(cls) -> dict:
        return {
            k: {
                "count": v["count"],
                "actions": list(v["actions"]),
                "subjects": list(v["subjects"]),
                "avg_time": v["total_time"] / v["count"] if v["count"] > 0 else 0,
                "error_rate": v["errors"] / v["count"] if v["count"] > 0 else 0,
            }
            for k, v in cls._stats.items()
        }

class LogBuilder:
    """Flow-style log message builder."""
    _SUBJECT_WORD_MAP = {
        "task": "task",
        "url": "url",
        "fetch": "url",
        "chain": "chain",
        "process": "chain",
        "store": "storage",
        "save": "storage",
    }

    def __init__(
        self,
        name: str,
        log_dir: str | Path = CONFIG.log_dir,
        level: str = CONFIG.log_level,
        console: bool = True,
        filename: str = "leisure-teatime.log",
    ):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            self._logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
            Path(log_dir).mkdir(exist_ok=True, parents=True)
            file_handler = logging.FileHandler(Path(log_dir) / filename, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
            self._logger.addHandler(file_handler)
            if console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))
                self._logger.addHandler(console_handler)
        self._msg: Optional[LogMessage] = None
        self._cache: dict = {}

    def message(self, action: Optional[ActionType] = None) -> 'LogBuilder':
        self._msg = LogMessage(action=action or "Processing", subject="method", details="")
        return self

    def subject(self, subject: SubjectType) -> 'LogBuilder':
        self._msg.subject = subject
        return self

    def subject_from_caller(self) -> 'LogBuilder':
        frame = inspect.stack()[2]
        func_name = frame.function.lower()
        words = func_name.split("_")
        for word in words:
            if word in self._SUBJECT_WORD_MAP:
                self._msg.subject = self._SUBJECT_WORD_MAP[word]
                return self
        self._msg.subject = "method"
        return self

    def details(self, **kwargs) -> 'LogBuilder':
        self._msg.details = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
        return self

    @LogAnalyzer.analyze
    def log(self, level: LevelType) -> None:
        if self._msg is None:
            raise ValueError("No message to log. Call message() first.")
        level_map = {
            "debug": "Starting",
            "info": "Finished",
            "warning": "Paused",
            "error": "Error",
        }
        if self._msg.action not in ActionType.__args__ or self._msg.action == "Processing":
            self._msg.action = level_map.get(level, "Processing")
        key = (self._msg.action, self._msg.subject, self._msg.details)
        if key not in self._cache:
            self._cache[key] = self._msg.format()
        getattr(self._logger, level)(self._cache[key])
        self._msg = None

def get_logger(
    name: str,
    log_dir: str | Path = CONFIG.log_dir,
    level: str = CONFIG.log_level,
    console: bool = True,
    filename: str = "leisure-teatime.log",
) -> LogBuilder:
    return LogBuilder(name, log_dir, level, console, filename)

# Example usage
def __main__():
    logger = get_logger(__name__)
    logger.message().subject("task").details(name="example").log("debug")
    logger.message("Processing").subject("chain").details(step="1").log("info")
    logger.message().subject_from_caller().details(pause=True).log("warning")
    logger.message("Resumed").subject("storage").details(result="saved").log("info")
    logger.message().subject("method").details(msg="failed").log("error")
    print(LogAnalyzer.get_stats())

if __name__ == "__main__":
    __main__()
