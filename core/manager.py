# core/manager.py
from hashlib import blake2b
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from core.config import Paths
from core.utils.files import read_file, write_file  # 更新导入
from core.logging import LogTemplates, get_logger
import time
import json

logger = get_logger("manager")

class BaseDataManager:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.data = self._load()

    def _load(self) -> Dict:
        try:
            content = read_file(self.data_file)
            return json.loads(content) if content else {"tree": {}, "index": {}}
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Failed to load {self.data_file}: {e}"))
            return {"tree": {}, "index": {}}

    def save(self):
        write_file(self.data_file, json.dumps(self.data, indent=2))

    def find_node(self, key: str) -> Tuple[Optional[Dict], List[str]]:
        path = self.data["index"].get(key, [])
        return self._traverse_path(self.data["tree"], path), path if path else []

    @staticmethod
    def _traverse_path(tree: Dict, path: List[str]) -> Dict:
        current = tree
        for key in path:
            current = current.get(key, {})
        return current

    @staticmethod
    def generate_hash(value: str, length: int = 6) -> str:
        digest = blake2b(value.encode(), digest_size=16).hexdigest()
        return digest[:length].upper()

    def count_leaf_nodes(self, tree: Dict = None) -> int:
        if tree is None:
            tree = self.data["tree"]
        count = 0
        for key, value in tree.items():
            if isinstance(value, dict) and "hash" in value:
                count += 1
            elif isinstance(value, dict):
                count += self.count_leaf_nodes(value)
        return count

    def rebuild_index(self):
        index = {}
        def walk(node: Dict, path: List[str]):
            for key, value in node.items():
                if isinstance(value, dict) and "hash" in value:
                    index[value["hash"]] = path + [key]
                elif isinstance(value, dict):
                    walk(value, path + [key])
        walk(self.data["tree"], [])
        self.data["index"] = index
        self.save()

class TaskDataManager(BaseDataManager):
    def __init__(self):
        super().__init__(Paths.TASKS_DATA)

    @staticmethod
    def parse_url(url: str) -> Tuple[List[str], List[str]]:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain_parts = parsed.netloc.split(".")
        reversed_domain = list(reversed(domain_parts))
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        return reversed_domain, path_parts

    def add_task(self, url: str, task_dir: Path, raw_content: str, dom_content: str, resource_count: int):
        task_hash = self.generate_hash(url)
        reversed_domain, path_parts = self.parse_url(url)
        current = self.data["tree"]
        for part in reversed_domain + path_parts:
            current = current.setdefault(part, {})
        task_entry = {
            "url": url,
            "dir": str(task_dir),
            "hash": task_hash,
            "created": time.time(),
            "is_dynamic": "partial" if raw_content != dom_content else "static",
            "resource_count": resource_count
        }
        current[task_hash] = task_entry
        self.data["index"][task_hash] = reversed_domain + path_parts + [task_hash]
        self.save()

    def remove_task(self, task_hash: str) -> bool:
        node, path = self.find_node(task_hash)
        if not node:
            return False
        current = self.data["tree"]
        for key in path[:-1]:
            current = current[key]
        del current[path[-1]]
        del self.data["index"][task_hash]
        self.save()
        return True

class ScriptDataManager(BaseDataManager):
    def __init__(self):
        super().__init__(Paths.SCRIPTS_DATA)

    def add_script(self, name: str, script_dir: Path):
        script_hash = self.generate_hash(name)
        self.data["tree"][name] = {
            "dir": str(script_dir),
            "hash": script_hash,
            "created": time.time()
        }
        self.data["index"][script_hash] = [name]
        self.save()

    def remove_script(self, name: str) -> bool:
        if name not in self.data["tree"]:
            return False
        script_hash = self.data["tree"][name]["hash"]
        del self.data["tree"][name]
        del self.data["index"][script_hash]
        self.save()
        return True
