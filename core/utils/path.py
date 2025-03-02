# core/utils/path.py
from pathlib import Path
import urllib.parse
import hashlib
from typing import Union
from core.utils.data import generate_hash

def resolve_path(path: Union[str, Path]) -> Path:
    """Normalize path and return absolute path."""
    return Path(path).resolve()

def generate_task_name(url: str) -> str:
    """Generate task name from URL in dotted format."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.split(".")[::-1]
    path = "".join(c for c in parsed.path.strip("/").replace("/", ".").replace("?", ".") if c.isalnum() or c == ".")
    return ".".join([*domain, path] if path else domain)

def generate_task_dir(task_dir: Path, task_name: str) -> Path:
    """Generate task directory with domain and short hash."""
    domain = ".".join(task_name.split(".")[:-1])
    short_hash = generate_hash(task_name)[:5]
    return task_dir / domain / short_hash
