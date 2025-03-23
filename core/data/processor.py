# core/data/processor.py

import re
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urljoin
from lxml import html
from pydantic import BaseModel
from core.utils.trie import Trie

class HtmlProcessNode(BaseModel):
    tag: str
    text: Optional[str] = None
    url: Optional[str] = None
    items: List["HtmlProcessNode"] = []
    depth: int = 0

HtmlProcessNode.model_rebuild()

CONTAINER_TAG = "__container__"  # 定义常量

def should_keep_node(node: HtmlProcessNode) -> bool:
    """默认判断节点是否保留自身"""
    has_value = bool(node.text and len(node.text.strip()) < 20)
    has_url = bool(node.url)
    has_items = bool(node.items)
    return has_value and (has_url or has_items)

def initialize_node(
    element: html.HtmlElement,
    depth: int = 0,
    text_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None,
    url_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None
) -> Optional[HtmlProcessNode]:
    """从 HtmlElement 初始化 Node，支持自定义 text 和 url 规则"""
    if not isinstance(element.tag, str):
        return None
    attrs = {k: v.strip() for k, v in element.items() if v and v.strip()}

    # 默认 text 规则
    default_text_rule = lambda e, a: (
        e.text.strip()
        if e.text else (
            a.get('title')
            or None
        )
    )
    # 默认 url 规则
    default_url_rule = lambda e, a: (
        a.get('href')
        or a.get('data-url')
        or None
    )

    return HtmlProcessNode(
        tag=element.tag,
        text=(text_rule or default_text_rule)(element, attrs),
        url=(url_rule or default_url_rule)(element, attrs),
        items=[],
        depth=depth
    )

NodeOrItems = Union[HtmlProcessNode, List[HtmlProcessNode]]

def process_node(
    node: html.HtmlElement,
    depth: int = 0,
    match_rule: Optional[Callable[[HtmlProcessNode], bool]] = should_keep_node,
    text_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None,
    url_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None
) -> Optional[NodeOrItems]:
    """递归处理 DOM 节点，支持自定义匹配规则"""
    current = initialize_node(node, depth, text_rule, url_rule)
    if current is None:
        return None

    for child in node:
        child_result = process_node(child, depth + 1, match_rule, text_rule, url_rule)
        if child_result is not None:
            if isinstance(child_result, HtmlProcessNode):
                current.items.append(child_result)
            elif isinstance(child_result, list):
                current.items.extend(child_result)

    if len(current.items) == 2:
        container = next((item for item in current.items if item.tag == CONTAINER_TAG), None)
        other = next((item for item in current.items if item.tag != CONTAINER_TAG), None)
        if container and other:
            other.items.extend(container.items)
            current.items = [other]

    if match_rule(current):
        return current
    elif len(current.items) > 1:
        return HtmlProcessNode(
            tag=CONTAINER_TAG,
            text=None,
            url=None,
            items=current.items,
            depth=current.depth
        )
    elif current.items:
        return current.items
    return None

def build_navigation_trie(
    hierarchy: Optional[NodeOrItems],
    filter: Optional[Callable[[HtmlProcessNode], bool]] = lambda _: True
) -> Trie[List[str], Dict]:
    """从 process_node 结果构建导航前缀树"""
    trie = Trie[List[str], Dict]()

    def traverse(node_or_items: NodeOrItems, path: List[str]) -> None:
        if isinstance(node_or_items, HtmlProcessNode):
            current_path = path.copy()
            if filter(node_or_items):
                if node_or_items.text and node_or_items.tag != CONTAINER_TAG:
                    current_path.append(node_or_items.text)
                if node_or_items.text and node_or_items.url:
                    trie.insert(current_path, {
                        "tag": node_or_items.tag,
                        "url": node_or_items.url,
                        "depth": node_or_items.depth
                    })
            for item in node_or_items.items:
                traverse(item, current_path)
        elif isinstance(node_or_items, list):
            for item in node_or_items:
                traverse(item, path)

    traverse(hierarchy, [])
    return trie

def preprocess_dom(dom: html.HtmlElement) -> None:
    """预处理 DOM，移除样式和脚本"""
    for elem in dom.xpath('//style | //script'):
        elem.getparent().remove(elem)

def build_dom_tree(
    html_str: str,
    match_rule: Optional[Callable[[HtmlProcessNode], bool]] = should_keep_node,
    text_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None,
    url_rule: Optional[Callable[[html.HtmlElement, Dict[str, str]], Optional[str]]] = None
) -> Optional[NodeOrItems]:
    """构建 DOM 树，支持自定义规则"""
    dom = html.fromstring(html_str)
    preprocess_dom(dom)
    return process_node(dom, match_rule=match_rule, text_rule=text_rule, url_rule=url_rule)

def filter_url(url: Optional[str], base_url: str) -> Optional[str]:
    """补全并过滤 URL"""
    if not url:
        return None
    if url.strip().lower() in {"javascript:;", "#", ""} or not re.match(r"^(https?://|/).*|^[^:]+$", url):
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url.strip()
    return urljoin(base_url, url.strip())
