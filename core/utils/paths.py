# core/utils/paths.py
from pathlib import Path
from typing import Union
from core.logging import get_logger

logger = get_logger("utils.paths")

def resolve_path(path: Union[str, Path]) -> Path:
    """Normalize the given path and return its absolute form."""
    return Path(path).resolve()

if __name__ == "__main__":
    path = resolve_path(".")
    assert path.is_absolute(), "Resolve path failed"
    logger.info("Paths tests passed")
