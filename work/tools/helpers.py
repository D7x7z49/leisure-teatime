# work/tools/helpers.py
from dataclasses import dataclass, field
from itertools import product
from queue import Queue
from pathlib import Path
import csv
from typing import List, Iterator, Any
from openpyxl import load_workbook, Workbook
from work.config.constants import GlobalConfig as GC

@dataclass
class BaseContext:
    """Base context with logging"""
    log_queue: Queue = field(default_factory=Queue)

    def log(self, msg: str) -> None:
        """Queue a log message"""
        self.log_queue.put(msg)

def get_module_path(task_dir: Path) -> str:
    """Get module path from task dir"""
    return f"{GC.ROOT_DIR.name}.{'.'.join(task_dir.relative_to(GC.ROOT_DIR).parts)}"
