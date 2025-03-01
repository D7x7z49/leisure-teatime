# core/utils/cli.py
from pathlib import Path
import urllib.parse
import hashlib
from core.utils.files import ensure_dir, write_json, read_json
from core.utils.data import generate_hash

def generate_task_name(url: str) -> str:
    """Generate task name from URL in dotted format."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.split(".")[::-1]  # 列表解析逆序
    path = "".join(c for c in parsed.path.strip("/").replace("/", ".").replace("?", ".") if c.isalnum() or c == ".")
    return ".".join([*domain, path] if path else domain)

def generate_task_dir(task_dir: Path, task_name: str) -> Path:
    """Generate task directory with domain and short hash."""
    domain = ".".join(task_name.split(".")[:-1])
    short_hash = generate_hash(task_name)[:5]
    return ensure_dir(task_dir / domain / short_hash)

def update_json_config(file_path: Path, key: str, name: str, data: dict):
    """Update JSON configuration file with key-value pair."""
    config = read_json(file_path) or {key: {}}
    config[key][name] = data
    write_json(file_path, config)
