# core/data/storage.py
import json
import aiofiles
import ijson
import pandas as pd
from pathlib import Path
from typing import Union, AsyncIterator, Any, Dict, List, Optional, Callable

# 全局默认目录，初始为当前工作目录
DEFAULT_DIR = Path.cwd()

def set_default_dir(dir_path: Union[str, Path]) -> None:
    """Set the default directory for file operations."""
    global DEFAULT_DIR
    DEFAULT_DIR = Path(dir_path).resolve()

def resolve_filepath(filename: str, dir: Optional[Path] = None) -> Path:
    """Resolve the full filepath based on filename and directory."""
    if Path(filename).is_absolute():
        return Path(filename)
    return (dir or DEFAULT_DIR) / filename

async def save_text(content: str, filename: str = "data.txt", dir: Optional[Path] = None) -> Path:
    """Save text content to a file asynchronously."""
    filepath = resolve_filepath(filename, dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(content)
    return filepath

async def read_text(filename: str = "data.txt", dir: Optional[Path] = None) -> str:
    """Read text content from a file asynchronously."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            return await f.read()
    return ""

async def save_json(data: Union[Dict, List], filename: str = "data.json", dir: Optional[Path] = None) -> Path:
    """Save data as JSON asynchronously."""
    filepath = resolve_filepath(filename, dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False))
    return filepath

async def read_json(filename: str = "data.json", dir: Optional[Path] = None) -> Union[Dict, List, None]:
    """Read JSON content synchronously."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            return json.loads(await f.read())  # 使用 json.loads
    return None

async def stream_json(filename: str = "data.json", dir: Optional[Path] = None) -> AsyncIterator[Any]:
    """Stream JSON content using ijson."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        async with aiofiles.open(filepath, "rb") as f:
            parser = ijson.parse(f)
            async for prefix, event, value in parser:
                yield (prefix, event, value)

async def save_csv(data: List[Dict], filename: str = "data.csv", dir: Optional[Path] = None) -> Path:
    """Save data as CSV using pandas."""
    filepath = resolve_filepath(filename, dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8")
    return filepath

async def read_csv(filename: str = "data.csv", dir: Optional[Path] = None) -> pd.DataFrame:
    """Read CSV content using pandas."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        return pd.read_csv(filepath)
    return pd.DataFrame()

async def stream_csv(filename: str = "data.csv", dir: Optional[Path] = None) -> AsyncIterator[Dict]:
    """Stream CSV content row by row."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            header = (await f.readline()).strip().split(",")
            async for line in f:
                values = line.strip().split(",")
                yield dict(zip(header, values))

async def save_xlsx(data: List[Dict], filename: str = "data.xlsx", dir: Optional[Path] = None) -> Path:
    """Save data as XLSX using pandas."""
    filepath = resolve_filepath(filename, dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, engine="openpyxl")
    return filepath

async def read_xlsx(filename: str = "data.xlsx", dir: Optional[Path] = None) -> pd.DataFrame:
    """Read XLSX content using pandas."""
    filepath = resolve_filepath(filename, dir)
    if filepath.exists():
        return pd.read_excel(filepath)
    return pd.DataFrame()

async def file_exists(filename: str, dir: Optional[Path] = None) -> bool:
    """Check if a file exists."""
    filepath = resolve_filepath(filename, dir)
    return filepath.exists()

# 文件格式处理字典
SAVE_HANDLERS: Dict[str, Callable[[Any, str, Optional[Path]], Path]] = {
    ".txt": save_text,
    ".json": save_json,
    ".csv": save_csv,
    ".xlsx": save_xlsx,
}

READ_HANDLERS: Dict[str, Callable[[str, Optional[Path]], Any]] = {
    ".txt": read_text,
    ".json": read_json,
    ".csv": read_csv,
    ".xlsx": read_xlsx,
}

async def save_file(data: Any, filename: str, dir: Optional[Path] = None) -> Path:
    """Save data to a file based on extension."""
    filepath = resolve_filepath(filename, dir)
    ext = filepath.suffix.lower()
    handler = SAVE_HANDLERS.get(ext, save_text)
    if handler:
        return await handler(data, filename, dir)
    raise ValueError(f"Unsupported file extension: {ext}")

async def read_file(filename: str, dir: Optional[Path] = None) -> Any:
    """Read data from a file based on extension."""
    filepath = resolve_filepath(filename, dir)
    ext = filepath.suffix.lower()
    handler = READ_HANDLERS.get(ext, read_text)
    if handler:
        return await handler(filename, dir)
    raise ValueError(f"Unsupported file extension: {ext}")
