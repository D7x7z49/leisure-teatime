# core/utils/trie.py
from typing import TypeVar, Generic, Dict, List, Any, Optional

K = TypeVar("K")  # 路径元素类型
V = TypeVar("V")  # 值类型

class Trie(Generic[K, V]):
    """A generic trie data structure for prefix-based storage."""

    def __init__(self):
        self.root: Dict[K, Any] = {}
        self.value: Optional[V] = None  # 节点的值

    def insert(self, path: List[K], value: V) -> None:
        """Insert a value at the given path."""
        node = self.root
        for key in path:
            if key not in node:
                node[key] = {}
            node = node[key]
        node["value"] = value

    def get(self, path: List[K]) -> Optional[V]:
        """Retrieve a value by path, or None if not found."""
        node = self.root
        for key in path:
            if key not in node:
                return None
            node = node[key]
        return node.get("value")

    def remove(self, path: List[K]) -> bool:
        """Remove a value by path, return True if successful."""
        node = self.root
        stack = [(node, key) for key in path]
        for _, key in stack:
            if key not in node:
                return False
            node = node[key]
        if "value" in node:
            del node["value"]
            return True
        return False

    def list_all(self) -> List[tuple[List[K], V]]:
        """List all paths and their values."""
        result = []
        def traverse(node: Dict, current_path: List[K]) -> None:
            if "value" in node:
                result.append((current_path[:], node["value"]))
            for key, child in node.items():
                if key != "value":
                    current_path.append(key)
                    traverse(child, current_path)
                    current_path.pop()
        traverse(self.root, [])
        return result

# 示例用法
if __name__ == "__main__":
    trie = Trie[str, str]()
    trie.insert(["com", "example"], "task1")
    trie.insert(["com", "google"], "task2")
    print(trie.get(["com", "example"]))  # 输出: task1
    print(trie.list_all())  # 输出: [(['com', 'example'], 'task1'), (['com', 'google'], 'task2')]
