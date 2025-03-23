# core/tasks/metadata.py
import json
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from core.config import CONFIG

class TaskInfo(BaseModel):
    """Individual task metadata."""
    scheme: str
    task_id: str
    url: str
    created_at: datetime = Field(default_factory=datetime.now)

class HistoryEntry(BaseModel):
    """Entry in use history."""
    task_id: str
    url: str
    timestamp: datetime = Field(default_factory=datetime.now)

class TasksMetadata(BaseModel):
    """Structure for tasks_metadata_file."""
    data: Dict[str, Dict[int, TaskInfo]] = Field(default_factory=dict)  # domain -> port -> info
    history: Optional[List[HistoryEntry]] = None  # 可选，默认空
    aliases: Optional[Dict[str, str]] = None  # 可选，默认空

    @classmethod
    def load(cls) -> "TasksMetadata":
        """Load metadata from file."""
        file_path = CONFIG.tasks_metadata_file
        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # 修复嵌套 dict 到 TaskInfo 的转换
                for domain in data.get("data", {}):
                    for port in data["data"][domain]:
                        data["data"][domain][port] = TaskInfo(**data["data"][domain][port])
                return cls.model_validate(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Failed to load metadata: {e}")
        return cls()

    def save(self) -> None:
        """Save metadata to file as JSON."""
        try:
            with CONFIG.tasks_metadata_file.open("w", encoding="utf-8") as f:
                f.write(self.model_dump_json(exclude_none=True))  # 使用 model_dump_json
        except IOError as e:
            print(f"Failed to save metadata: {e}")

    def update_history(self, task_id: str, url: str, max_entries: int = 10) -> None:
        """Update use history, keeping only the latest entries."""
        if self.history is None:
            self.history = []
        entry = HistoryEntry(task_id=task_id, url=url)
        self.history = [e for e in self.history if e.task_id != task_id]  # 移除旧记录
        self.history.append(entry)
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]
        self.save()

    def set_alias(self, alias: str, task_id: str) -> bool:
        """Set an alias for a task."""
        if self.aliases is None:
            self.aliases = {}
        if alias in self.aliases:
            return False
        self.aliases[alias] = task_id
        self.save()
        return True

    def get_task_by_alias(self, alias: str) -> Optional[str]:
        """Get task_id by alias."""
        return self.aliases.get(alias) if self.aliases else None

# 示例用法
if __name__ == "__main__":
    metadata = TasksMetadata()
    metadata.data["com/example"] = {443: TaskInfo(scheme="https", task_id="abc123", url="https://example.com")}
    metadata.update_history("abc123", "https://example.com")
    metadata.set_alias("example", "abc123")
    print(metadata.model_dump_json(indent=2))
