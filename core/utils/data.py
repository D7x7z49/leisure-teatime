# core/utils/data.py
from typing import Any, List, Dict, Callable, Optional, Tuple
from playwright.sync_api import Page as SyncPage
from playwright.async_api import Page as AsyncPage
from lxml import etree
from urllib.parse import urljoin
from core.logging import get_logger

logger = get_logger("data_utils")

# 私有辅助函数
def _normalize_url(url: str, base_url: str) -> str:
    """Normalize a URL relative to a base URL."""
    return urljoin(base_url, url.strip())

def _clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    import re
    return re.sub(r'\s+', ' ', text.strip()) if text and text.strip() else ""

def _limit_depth(func: Callable, max_depth: int = 10) -> Callable:
    """Limit recursion depth to prevent stack overflow."""
    def wrapper(*args, depth: int = 0, **kwargs):
        if depth >= max_depth:
            logger.warning(f"Max depth {max_depth} reached in {func.__name__}")
            return {}
        return func(*args, depth=depth, **kwargs)
    return wrapper

# 规则类型定义
Rule = Tuple[Callable[[etree.Element], bool], Callable[[etree.Element], str], bool]

# 主函数 1: 同步提取 lxml 节点
def extract_lxml(page: SyncPage, xpath: str = "//body") -> Optional[etree.Element]:
    """Extract an lxml Element from a sync Page using an xpath."""
    try:
        content = page.content()
        tree = etree.HTML(content)
        nodes = tree.xpath(xpath)
        return nodes[0] if nodes else tree
    except Exception as e:
        logger.error(f"Failed to extract lxml from sync page: {e}")
        return None

# 主函数 2: 异步提取 lxml 节点
async def async_extract_lxml(page: AsyncPage, xpath: str = "//body") -> Optional[etree.Element]:
    """Extract an lxml Element from an async Page using an xpath."""
    try:
        content = await page.content()
        tree = etree.HTML(content)
        nodes = tree.xpath(xpath)
        return nodes[0] if nodes else tree
    except Exception as e:
        logger.error(f"Failed to extract lxml from async page: {e}")
        return None

# 主函数 3: 提取导航链接（基于 lxml 节点）
def extract_nav_links(
    root: etree.Element,
    base_url: str,
    rules: List[Rule] = None
) -> Dict[str, Any]:
    """Extract hierarchical links from an lxml navigation root using a rule queue."""
    if not root:
        return {}

    # 默认规则
    if rules is None:
        rules = [
            (lambda elem: elem.tag in {"li", "button"}, lambda elem: _clean_text(elem.text_content()), False),
            (lambda elem: elem.tag == "a", lambda elem: _normalize_url(elem.get("href", ""), base_url), True),
        ]

    @_limit_depth
    def process_node(node: etree.Element, rules: List[Rule], depth: int = 0) -> Dict[str, Any]:
        """Recursively process node based on rule queue."""
        result = {}
        for condition, process, stop in rules:
            if condition(node):
                key = process(node)
                if not key:
                    break
                if stop:  # Leaf node
                    result[key] = key if "http" in key else None
                else:  # Branch node
                    children = {}
                    for child in node:
                        child_result = process_node(child, rules, depth + 1)
                        if child_result:
                            children.update(child_result)
                    result[key] = children if children else key
                break
        return result

    return process_node(root, rules)

# 测试函数
def test_extraction(page: SyncPage, url: str, nav_xpath: str = "//nav") -> None:
    """Test navigation link extraction."""
    page.goto(url)
    base_url = page.url
    nav_root = extract_lxml(page, nav_xpath)
    nav_tree = extract_nav_links(nav_root, base_url)
    print(f"Navigation tree: {nav_tree}")
