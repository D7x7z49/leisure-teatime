# core/task_manager.py
from hashlib import blake2b
import time
import shutil
from typing import Tuple, Dict, Optional, List
from pathlib import Path
from core.config import Config
from core.utils.files import read_json, write_json, read_file, ensure_dir
from core.logging import get_logger

logger = get_logger("task_manager")

_TASK_DIR = Config.WORK.TASK_DIR
_TASK_DATA = Config.WORK.TASK_DATA_FILE

class TaskDataManager:
    _TREE_ROOT = _TASK_DATA

    @classmethod
    def load_tree(cls) -> Dict:
        """加载任务树数据"""
        return read_json(cls._TREE_ROOT) or {"tree": {}, "index": {}}

    @classmethod
    def save_tree(cls, data: Dict):
        """保存任务树数据"""
        write_json(cls._TREE_ROOT, data)

    @classmethod
    def find_node(cls, task_hash: str) -> Tuple[Optional[Dict], List[str]]:
        """通过哈希查找任务节点"""
        data = cls.load_tree()
        for hash_val, path in data["index"].items():
            if hash_val == task_hash:
                return cls._traverse_path(data["tree"], path), path
        return None, []

    @classmethod
    def _traverse_path(cls, tree: Dict, path: List[str]) -> Dict:
        """递归遍历路径"""
        current = tree
        for key in path:
            current = current.get(key, {})
        return current

    @staticmethod
    def generate_task_hash(url: str, length: int = 6) -> str:
        """生成抗碰撞任务哈希"""
        digest = blake2b(url.encode(), digest_size=16).hexdigest()
        return digest[:length].upper()

    @staticmethod
    def parse_url(url: str) -> Tuple[List[str], List[str]]:
        """解析 URL 为域名和路径部分"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain_parts = parsed.netloc.split(".")
        reversed_domain = list(reversed(domain_parts))
        path_parts = parsed.path.strip("/").split("/")
        return reversed_domain, path_parts

    @classmethod
    def count_leaf_nodes(cls, tree: Dict) -> int:
        """统计树中的叶子节点（任务）数量"""
        count = 0
        for key, value in tree.items():
            if isinstance(value, dict) and "url" in value:
                count += 1
            elif isinstance(value, dict):
                count += cls.count_leaf_nodes(value)
        return count

    @classmethod
    def rebuild_index(cls, data: Dict):
        """树结构变化后重建哈希索引"""
        index = {}
        def walk(node: Dict, path: List[str]):
            for key, value in node.items():
                if isinstance(value, dict) and "hash" in value:
                    index[value["hash"]] = path + [key]
                elif isinstance(value, dict):
                    walk(value, path + [key])
        walk(data["tree"], [])
        data["index"] = index
        return data
