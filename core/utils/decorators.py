# core/utils/decorators.py
from functools import wraps
from typing import Callable
import time
import sys
from pathlib import Path
from core.logging import get_logger, LogTemplates
from core.utils.files import read_file  # 导入 files.read_file

logger = get_logger("utils.decorators")

def timing(func: Callable) -> Callable:
    """Log the execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} took {time.time() - start:.2f}s")
        return result
    return wrapper

def safe_call(func: Callable) -> Callable:
    """Safely call a function, catching exceptions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__}: {e}"))
            return None
    return wrapper

def retry(func: Callable, attempts: int = 3, delay: float = 1.0) -> Callable:
    """Retry mechanism for function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == attempts - 1:
                    logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__} failed after {attempts} attempts: {e}"))
                    return None
                time.sleep(delay)
                logger.warning(f"Retrying {func.__name__} (attempt {attempt + 1}/{attempts})")
    return wrapper

def log_args(func: Callable) -> Callable:
    """Log function arguments and return values."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} returned {result}")
        return result
    return wrapper

def task_runner(file_name: str = "index.html"):
    """Decorator to inject task data and known_vars into execute function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_dir = kwargs.get("task_dir", Path(sys.argv[0]).parent if "__file__" in globals() else Path.cwd())
            data_file = kwargs.get("file_name", file_name)
            data = read_file(task_dir / data_file) or ""
            known_vars = {}
            result = func(data, known_vars)
            logger.debug(f"Task executed with known_vars: {known_vars}")
            return known_vars or result
        return wrapper
    return decorator

if __name__ == "__main__":
    @timing
    @safe_call
    def test():
        time.sleep(0.1)
        return "Success"
    assert test() == "Success", "Decorator test failed"
    logger.info("Decorators tests passed")
