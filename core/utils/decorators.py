# core/utils/decorators.py
import time
import sys
from functools import wraps, lru_cache
from pathlib import Path
from typing import Callable
from core.logging import get_logger, LogTemplates
from core.utils.files import read_file

logger = get_logger("utils.decorators")


def memoize(func: Callable) -> Callable:
    """Cache function results for performance."""
    @lru_cache(maxsize=128)
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

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

def task_runner(script_path: Path, html_file: str = "index.html"):
    """Decorator to inject task data and known_vars into execute function.

    Args:
        script_path (Path): Path to the script file (e.g., Path(__file__)).
        html_file (str): Name of the HTML file in the task directory (e.g., 'index.html').
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine task directory: CLI-provided task_dir takes priority over script_path
            task_dir = kwargs.get("task_dir", script_path.parent)
            # Load data from specified HTML file
            data = read_file(task_dir / html_file) or ""
            known_vars = {}

            # Execute function
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
