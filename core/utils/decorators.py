# core/utils/decorators.py
from functools import wraps, lru_cache
from typing import Callable
from core.logging import get_logger

logger = get_logger("decorators")

def memoize(func: Callable) -> Callable:
    """Cache function results for performance."""
    @lru_cache(maxsize=128)
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
