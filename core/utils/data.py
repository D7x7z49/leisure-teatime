# core/utils/data.py
import hashlib
import csv
from io import StringIO
from typing import List, Dict
from core.logging import get_logger

logger = get_logger("utils.data")

def clean_text(text: str) -> str:
    """Clean a string by removing extra whitespace and newlines."""
    return " ".join(text.split()).strip()

def generate_hash(data: str) -> str:
    """Generate a SHA1 hash for a given string."""
    return hashlib.sha1(data.encode("utf-8")).hexdigest()

def list_to_csv(data: List[Dict]) -> str:
    """Convert a list of dictionaries into a CSV string."""
    if not data:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

if __name__ == "__main__":
    assert clean_text("  hello  world  ") == "hello world"
    assert len(generate_hash("test")) == 40
    csv_data = [{"a": 1, "b": 2}]
    assert "a,b" in list_to_csv(csv_data)
    logger.info("Data tests passed")
