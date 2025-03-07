# core/utils/files.py
from pathlib import Path
import json
import csv
import asyncio
from typing import Union, Callable, Optional, Iterator, Dict, List, Any
from functools import wraps
from core.logging import get_logger, LogTemplates
import ijson
import aiofiles

logger = get_logger("utils.files")

# Custom exceptions
class FileOperationError(Exception):
    pass

class FileNotFoundError(FileOperationError):
    pass

class FilePermissionError(FileOperationError):
    pass

# Decorators
def sync_file_op(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(filepath: Union[str, Path], *args, **kwargs):
        path = Path(filepath)
        if not path.exists():
            logger.error(LogTemplates.ERROR.format(msg=f"File not found: {filepath}"))
            raise FileNotFoundError(f"File not found: {filepath}")
        if not path.is_file():
            raise FileOperationError(f"{filepath} is not a file")
        try:
            return func(path, *args, **kwargs)
        except PermissionError as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Permission denied: {filepath}"))
            raise FilePermissionError(f"Permission denied: {filepath}") from e
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__} failed: {e}"))
            raise FileOperationError(f"Failed to execute {func.__name__}: {e}") from e
    return wrapper

def async_file_op(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(filepath: Union[str, Path], *args, **kwargs):
        path = Path(filepath)
        if not path.exists():
            logger.error(LogTemplates.ERROR.format(msg=f"File not found: {filepath}"))
            raise FileNotFoundError(f"File not found: {filepath}")
        if not path.is_file():
            raise FileOperationError(f"{filepath} is not a file")
        try:
            return await func(path, *args, **kwargs)
        except PermissionError as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Permission denied: {filepath}"))
            raise FilePermissionError(f"Permission denied: {filepath}") from e
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__} failed: {e}"))
            raise FileOperationError(f"Failed to execute {func.__name__}: {e}") from e
    return wrapper

def sync_write_op(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(filepath: Union[str, Path], *args, **kwargs):
        path = Path(filepath)
        try:
            return func(path, *args, **kwargs)
        except PermissionError as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Permission denied: {filepath}"))
            raise FilePermissionError(f"Permission denied: {filepath}") from e
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__} failed: {e}"))
            raise FileOperationError(f"Failed to execute {func.__name__}: {e}") from e
    return wrapper

def async_write_op(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(filepath: Union[str, Path], *args, **kwargs):
        path = Path(filepath)
        try:
            return await func(path, *args, **kwargs)
        except PermissionError as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Permission denied: {filepath}"))
            raise FilePermissionError(f"Permission denied: {filepath}") from e
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"{func.__name__} failed: {e}"))
            raise FileOperationError(f"Failed to execute {func.__name__}: {e}") from e
    return wrapper

# Directory management
def ensure_dir(directory: Union[str, Path]) -> Path:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

# Synchronous reading
@sync_file_op
def read_file(
    filepath: Path,
    format: str = "text",
    iterator: bool = False,
    callback: Optional[Callable[[Any], Any]] = None,
    encoding: str = "utf-8",
    delimiter: str = ",",  # CSV-specific
) -> Union[str, Dict, List, Iterator[Dict]]:
    """同步读取文件，支持普通读取和迭代器"""
    file_size = filepath.stat().st_size

    if format == "text":
        result = filepath.read_text(encoding)
    elif format == "json":
        result = json.loads(filepath.read_text(encoding))
    elif format == "csv":
        if not iterator:
            with filepath.open("r", encoding=encoding) as f:
                result = list(csv.DictReader(f, delimiter=delimiter))
        else:
            with filepath.open("r", encoding=encoding) as f:
                result = iter(csv.DictReader(f, delimiter=delimiter))
    else:
        raise ValueError(f"Unsupported format: {format}")

    return callback(result) if callback else result

# Asynchronous reading
@async_file_op
async def async_read_file(
    filepath: Path,
    format: str = "text",
    stream: bool = False,
    callback: Optional[Callable[[Any], Any]] = None,
    encoding: str = "utf-8",
    delimiter: str = ",",  # CSV-specific
) -> Union[str, Dict, List, Iterator[Dict]]:
    """异步读取文件，支持普通读取和流式读取"""
    file_size = filepath.stat().st_size

    if format == "text":
        async with aiofiles.open(filepath, "r", encoding=encoding) as f:
            result = await f.read()
    elif format == "json":
        if stream:  # 无需大小限制，stream=True 时总是流式读取
            async def stream_json():
                async with aiofiles.open(filepath, "rb") as f:
                    parser = ijson.parse(await f.read())
                    for prefix, event, value in parser:
                        if event in ("map_key", "string", "number"):
                            yield {"prefix": prefix, "value": value}
                        await asyncio.sleep(0)  # 模拟异步行为
            if callback:
                async def wrapped_stream():
                    async for item in stream_json():
                        yield callback(item)
                return wrapped_stream()
            return stream_json()
        else:
            async with aiofiles.open(filepath, "r", encoding=encoding) as f:
                result = json.loads(await f.read())
    elif format == "csv":
        if stream:
            async with aiofiles.open(filepath, "r", encoding=encoding) as f:
                content = await f.read()
                result = iter(csv.DictReader(content.splitlines(), delimiter=delimiter))
        else:
            async with aiofiles.open(filepath, "r", encoding=encoding) as f:
                result = list(csv.DictReader((await f.read()).splitlines(), delimiter=delimiter))
    else:
        raise ValueError(f"Unsupported format: {format}")

    return callback(result) if callback else result

# Writing functions
@sync_write_op
def write_file(filepath: Path, content: str, encoding: str = "utf-8") -> None:
    filepath.write_text(content, encoding)
    logger.info(f"Wrote to {filepath}")

@async_write_op
async def async_write_file(filepath: Path, content: str, encoding: str = "utf-8") -> None:
    async with aiofiles.open(filepath, "w", encoding=encoding) as f:
        await f.write(content)
    logger.info(f"Wrote to {filepath}")

# Example usage
if __name__ == "__main__":
    # # Sync text read
    # content = read_file("test.txt", format="text")
    # print(f"Text content: {content}")

    # # Sync CSV iterator
    # for row in read_file("test.csv", format="csv", iterator=True):
    #     print(f"CSV row: {row}")

    # Async JSON stream
    async def test_json():
        result = await async_read_file(
            "test.json",
            format="json",
            stream=True,
            callback=lambda x: x["value"] if "value" in x else x.get("name", "Unknown")
        )
        async for item in result:
            print(item)
    asyncio.run(test_json())
