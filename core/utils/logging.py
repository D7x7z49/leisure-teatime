# core/utils/logging.py
from pathlib import Path
import logging
import sys
import inspect
from typing import Literal, Optional
from pydantic import BaseModel, Field
from functools import wraps
from collections import OrderedDict
import time
import asyncio
import queue
from logging.handlers import QueueHandler, QueueListener
from core.config import CONFIG

# Log format constants
FILE_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
CONSOLE_LOG_FORMAT = "[%(levelname)s] %(name)s: %(message)s"

# Restricted options
ActionType = Literal["Starting", "Processing", "Paused", "Resumed", "Finished", "Error"]
SubjectType = Literal["task", "url", "chain", "storage", "method"]
LevelType = Literal["debug", "info", "warning", "error"]

class LogMessage(BaseModel):
    action: ActionType = Field(..., description="The action being performed")
    subject: SubjectType = Field(..., description="The subject of the action")
    details: str = Field(..., description="Additional details about the action")

    def format(self) -> str:
        return f"{self.action} {self.subject}: {self.details}"

class LogAnalyzer:
    """Tool class for logging statistics and performance analysis."""
    _stats = {}

    @classmethod
    def analyze_sync(cls, func):
        """装饰器用于同步方法"""
        @wraps(func)
        def wrapper(self, level: LevelType):
            msg = self._msg
            if not msg:
                return func(self, level)
            key = self._logger.name
            cls._stats[key] = cls._stats.get(key) or {
                "count": 0, "actions": set(), "subjects": set(), "total_time": 0, "errors": 0
            }
            start = time.time()
            result = func(self, level)
            elapsed = time.time() - start
            stats = cls._stats[key]
            stats["count"] += 1
            stats["actions"].add(msg.action)
            stats["subjects"].add(msg.subject)
            stats["total_time"] += elapsed
            stats["errors"] += 1 if level == "error" else 0
            return result
        return wrapper

    @classmethod
    def analyze_async(cls, func):
        """装饰器用于异步方法"""
        @wraps(func)
        async def wrapper(self, level: LevelType):
            msg = self._msg
            if not msg:
                return await func(self, level)
            key = self._logger.name
            cls._stats[key] = cls._stats.get(key) or {
                "count": 0, "actions": set(), "subjects": set(), "total_time": 0, "errors": 0
            }
            start = time.time()
            result = await func(self, level)
            elapsed = time.time() - start
            stats = cls._stats[key]
            stats["count"] += 1
            stats["actions"].add(msg.action)
            stats["subjects"].add(msg.subject)
            stats["total_time"] += elapsed
            stats["errors"] += 1 if level == "error" else 0
            return result
        return wrapper

    @classmethod
    def get_stats(cls) -> dict:
        return {
            k: {
                "count": v["count"],
                "actions": list(v["actions"]),
                "subjects": list(v["subjects"]),
                "avg_time": v["total_time"] / v["count"] if v["count"] else 0,
                "error_rate": v["errors"] / v["count"] if v["count"] else 0,
            } for k, v in cls._stats.items()
        }

class LogBuilder:
    """Flow-style log message builder with sync and async support."""
    _SUBJECT_WORD_MAP = {
        "task": "task", "url": "url", "fetch": "url",
        "chain": "chain", "process": "chain",
        "store": "storage", "save": "storage",
    }

    def __init__(
        self,
        name: str,
        log_dir: str | Path = CONFIG.log_dir,
        level: str = CONFIG.log_level,
        console: bool = True,
        filename: str = CONFIG.log_filename,
        cache_size: int = 1000,
    ):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            self._logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
            Path(log_dir).mkdir(exist_ok=True, parents=True)
            file_handler = logging.FileHandler(Path(log_dir) / filename, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
            self._queue = queue.Queue()
            self._queue_handler = QueueHandler(self._queue)
            self._queue_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
            self._logger.addHandler(self._queue_handler)
            self._listener = QueueListener(self._queue, file_handler)
            self._listener.start()
            if console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))
                self._logger.addHandler(console_handler)
        self._msg: Optional[LogMessage] = None
        self._cache = OrderedDict()
        self._cache_size = cache_size

    def __del__(self):
        if hasattr(self, '_listener'):
            self._listener.stop()

    def message(self, action: Optional[ActionType] = None) -> 'LogBuilder':
        self._msg = LogMessage(action=action or "Processing", subject="method", details="")
        return self

    def subject(self, subject: SubjectType) -> 'LogBuilder':
        self._msg.subject = subject
        return self

    def subject_from_caller(self) -> 'LogBuilder':
        words = inspect.stack()[1].function.lower().split("_")
        self._msg.subject = next(
            (self._SUBJECT_WORD_MAP[word] for word in words if word in self._SUBJECT_WORD_MAP),
            "method"
        )
        return self

    def details(self, **kwargs) -> 'LogBuilder':
        self._msg.details = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items()) if kwargs else ""
        return self

    def _resolve_action(self, level: LevelType, action: ActionType) -> ActionType:
        level_priority = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        action_priority = {"Starting": 0, "Processing": 1, "Paused": 2, "Resumed": 2, "Finished": 3, "Error": 4}
        current = action_priority.get(action, 1)
        target = level_priority.get(level, 1)
        return action if current <= target else next(
            (act for act, prio in action_priority.items() if prio >= target), "Processing"
        )

    @LogAnalyzer.analyze_sync
    def log(self, level: LevelType) -> None:
        """Synchronous logging for lightweight, immediate tasks."""
        if not self._msg:
            raise ValueError("No message to log. Call message() first.")
        self._msg.action = self._resolve_action(level, self._msg.action)
        key = (self._msg.action, self._msg.subject, self._msg.details)
        self._cache[key] = self._cache.get(key) or self._msg.format()
        [self._cache.popitem(last=False) for _ in range(len(self._cache) - self._cache_size) if len(self._cache) > self._cache_size]
        getattr(self._logger, level)(self._cache[key])
        self._msg = None

    @LogAnalyzer.analyze_async
    async def async_log(self, level: LevelType) -> None:
        """Asynchronous logging for potentially blocking operations."""
        if not self._msg:
            raise ValueError("No message to log. Call message() first.")
        self._msg.action = self._resolve_action(level, self._msg.action)
        key = (self._msg.action, self._msg.subject, self._msg.details)
        self._cache[key] = self._cache.get(key) or self._msg.format()
        [self._cache.popitem(last=False) for _ in range(len(self._cache) - self._cache_size) if len(self._cache) > self._cache_size]
        await asyncio.get_running_loop().run_in_executor(None, getattr(self._logger, level), self._cache[key])
        self._msg = None

def get_logger(
    name: str,
    log_dir: str | Path = CONFIG.log_dir,
    level: str = CONFIG.log_level,
    console: bool = True,
    filename: str = CONFIG.log_filename,
) -> LogBuilder:
    return LogBuilder(name, log_dir, level, console, filename)

async def __main__():
    logger = get_logger(__name__)
    logger.message().subject("task").details(name="example").log("debug")
    logger.message("Processing").subject("chain").details(step="1").log("info")
    logger.message().subject_from_caller().details(pause=True).log("warning")
    await logger.message("Resumed").subject("storage").details(result="saved").async_log("info")
    logger.message().subject("method").details(msg="failed").log("error")
    print(LogAnalyzer.get_stats())

if __name__ == "__main__":
    asyncio.run(__main__())
