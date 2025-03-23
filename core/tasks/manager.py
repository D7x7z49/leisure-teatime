# core/tasks/manager.py
import hashlib
import os
import shutil
from typing import Dict, List, Optional
from urllib.parse import urlparse
from core.utils.trie import Trie
from core.config import CONFIG
from core.tasks.metadata import TasksMetadata, TaskInfo

class TaskManager:
    """Manages tasks using a trie-based structure with persistence."""

    def __init__(self):
        self.trie = Trie[str, Dict[int, dict]]()
        self.metadata = TasksMetadata.load()
        self.current_task: Optional[str] = None
        self._load_to_trie()

    def _parse_domain(self, url: str) -> tuple[list[str], int, str]:
        """Parse URL into domain path, port, and scheme."""
        parsed = urlparse(url)
        domain = parsed.netloc.split(":")[0].replace("www.", "").split(".")
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        return domain[::-1], port, parsed.scheme

    def _task_hash(self, domain: list[str], port: int) -> str:
        """Generate a unique hash for the task."""
        return hashlib.sha1("".join(domain + [str(port)]).encode()).hexdigest()[:8]

    def _load_to_trie(self) -> None:
        """Load tasks from metadata into trie."""
        for domain_str, ports in self.metadata.data.items():
            domain = domain_str.split("/")
            self.trie.insert(domain, {int(port): info.model_dump() for port, info in ports.items()})

    def add(self, url: str) -> str:
        """Add a task from URL, return its hash."""
        domain, port, scheme = self._parse_domain(url)
        task_hash = self._task_hash(domain, port)
        task_dir = CONFIG.tasks_dir / task_hash

        os.makedirs(task_dir, exist_ok=True)
        for template in CONFIG.template_dir.glob("*.py"):
            shutil.copy(template, task_dir)

        task_info = TaskInfo(scheme=scheme, task_id=task_hash, url=url)
        existing = self.trie.get(domain) or {}
        existing[port] = task_info.model_dump()
        self.trie.insert(domain, existing)
        self.metadata.data["/".join(domain)] = {port: task_info}
        self.metadata.save()

        return task_hash

    def use(self, identifier: str) -> bool:
        """Switch to a task by URL, hash, or alias, sync previous task."""
        if identifier.startswith("http"):
            domain, port, _ = self._parse_domain(identifier)
            task_hash = self._task_hash(domain, port)
        elif identifier in (self.metadata.aliases or {}):
            task_hash = self.metadata.get_task_by_alias(identifier)
        else:
            task_hash = identifier

        for _, ports in self.trie.list_all():
            if task_hash in [info["task_id"] for info in ports.values()]:
                if self.current_task and CONFIG.tasks_main_dir.exists():
                    prev_dir = CONFIG.tasks_dir / self.current_task
                    shutil.rmtree(prev_dir, ignore_errors=True)
                    shutil.copytree(CONFIG.tasks_main_dir, prev_dir)

                task_dir = CONFIG.tasks_dir / task_hash
                if CONFIG.tasks_main_dir.exists():
                    shutil.rmtree(CONFIG.tasks_main_dir)
                shutil.copytree(task_dir, CONFIG.tasks_main_dir)
                self.current_task = task_hash
                url = next((p["url"] for p in ports.values() if p["task_id"] == task_hash), "")
                self.metadata.update_history(task_hash, url)
                return True
        return False

    def remove(self, url: str) -> bool:
        """Remove a task by URL, cleaning up metadata fully."""
        domain, port, _ = self._parse_domain(url)
        tasks = self.trie.get(domain)
        if tasks and port in tasks:
            task_hash = tasks[port]["task_id"]
            # 删除任务目录
            task_dir = CONFIG.tasks_dir / task_hash
            shutil.rmtree(task_dir, ignore_errors=True)
            # 更新 trie 和 metadata.data
            del tasks[port]
            domain_str = "/".join(domain)
            if not tasks:
                self.trie.remove(domain)
                del self.metadata.data[domain_str]
            else:
                self.trie.insert(domain, tasks)
                self.metadata.data[domain_str] = {int(p): TaskInfo(**info) for p, info in tasks.items()}
            # 清理 history
            if self.metadata.history:
                self.metadata.history = [entry for entry in self.metadata.history if entry.task_id != task_hash]
            # 清理 aliases
            if self.metadata.aliases:
                self.metadata.aliases = {k: v for k, v in self.metadata.aliases.items() if v != task_hash}
            # 保存更新
            self.metadata.save()
            return True
        return False

    def list_tasks(self) -> List[tuple[List[str], Dict]]:
        """List all tasks in the trie."""
        return [(path, ports) for path, ports in self.trie.list_all()]

# 示例用法
if __name__ == "__main__":
    manager = TaskManager()
    task_hash = manager.add("https://www.example.com/path")
    print(f"Added task: {task_hash}")
    manager.use(task_hash)
    print("Switched to task")
    manager.metadata.set_alias("example", task_hash)
    print("Set alias 'example'")
    manager.use("example")
    print("Switched by alias")
    print(manager.list_tasks())
    print("History:", manager.metadata.history)
    manager.remove("https://www.example.com")
    print("Removed task")
