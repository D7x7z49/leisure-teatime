# core/utils/files.py
from pathlib import Path
import json
import csv
import asyncio
from typing import Union, Optional, Dict, List, Iterator
from core.logging import get_logger, LogTemplates

logger = get_logger("utils.files")

# Synchronous functions
def ensure_dir(directory: Union[str, Path]) -> Path:
    """Ensure the directory exists and return a Path object."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def read_file(filepath: Union[str, Path], encoding: str = "utf-8") -> Optional[str]:
    """Read file content, return None if reading fails."""
    try:
        return Path(filepath).read_text(encoding)
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Reading {filepath}: {e}"))
        return None

def write_file(filepath: Union[str, Path], content: str, encoding: str = "utf-8") -> bool:
    """Write content to a file, return success status."""
    try:
        Path(filepath).write_text(content, encoding)
        logger.info(f"Wrote to {filepath}")
        return True
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Writing {filepath}: {e}"))
        return False

def read_json(filepath: Union[str, Path]) -> Optional[Union[Dict, List]]:
    """Read a JSON file."""
    content = read_file(filepath)
    return json.loads(content) if content else None

def write_json(filepath: Union[str, Path], data: Union[Dict, List]) -> bool:
    """Write data to a JSON file."""
    return write_file(filepath, json.dumps(data, indent=2)) if data else False

def read_csv(filepath: Union[str, Path]) -> Optional[List]:
    """Read a CSV file into a list."""
    try:
        with Path(filepath).open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Reading CSV {filepath}: {e}"))
        return None

# Asynchronous functions
async def async_read_file(filepath: Union[str, Path], encoding: str = "utf-8") -> Optional[str]:
    """Asynchronously read file content."""
    try:
        return await asyncio.to_thread(Path(filepath).read_text, encoding)
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Reading {filepath}: {e}"))
        return None

async def async_write_file(filepath: Union[str, Path], content: str, encoding: str = "utf-8") -> bool:
    """Asynchronously write content to a file."""
    try:
        await asyncio.to_thread(Path(filepath).write_text, content, encoding)
        logger.info(f"Wrote to {filepath}")
        return True
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Writing {filepath}: {e}"))
        return False

async def async_read_json(filepath: Union[str, Path]) -> Optional[Union[Dict, List]]:
    """Asynchronously read a JSON file."""
    content = await async_read_file(filepath)
    return json.loads(content) if content else None

async def async_write_json(filepath: Union[str, Path], data: Union[Dict, List]) -> bool:
    """Asynchronously write data to a JSON file."""
    return await async_write_file(filepath, json.dumps(data, indent=2)) if data else False

# Iterator functions
def iterate_files(directory: Union[str, Path], pattern: str = "*") -> Iterator[Path]:
    """Iterate over files in a directory."""
    return (p for p in Path(directory).rglob(pattern) if p.is_file())

def iterate_csv(filepath: Union[str, Path]) -> Iterator[Dict]:
    """Iterate over rows in a CSV file."""
    with Path(filepath).open("r", encoding="utf-8") as f:
        yield from csv.DictReader(f)

if __name__ == "__main__":
    test_dir = ensure_dir("test_dir")
    test_file = test_dir / "test.txt"
    assert write_file(test_file, "Hello"), "Write failed"
    assert read_file(test_file) == "Hello", "Read failed"
    logger.info("Files tests passed")
