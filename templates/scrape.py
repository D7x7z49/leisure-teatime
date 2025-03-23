# templates/scrape.py
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page
from core.browser.controller import with_cdp
from core.browser.fetcher import fetch_content, initialize, setup_anti_detection
from core.data.processor import HtmlProcessNode, build_dom_tree, build_navigation_trie, filter_url
from core.data.storage import set_default_dir, save_file, read_file, file_exists
from core.data.extractor import extract_xpath
from core.utils.functional import pipeline

set_default_dir(Path(__file__).parent  / ".data")

async def init(context: BrowserContext) -> None:
    pass

@with_cdp
async def main(context: BrowserContext, url: str = "https://example.com"):
    """Scrape data from a URL"""
    await initialize(context, init, is_anti_detection=True)
    dom_text = await fetch_content(context, url)

    # 示例自定义规则
    def custom_match(node: HtmlProcessNode) -> bool:
        has_value = bool(node.text and len(node.text.strip()) < 20)
        has_url = bool(node.url)
        has_items = bool(node.items)
        return has_value and (has_url or has_items)

    hierarchy = build_dom_tree(dom_text, match_rule=custom_match, text_rule=lambda e, a:(
        e.text.strip()
        if e.text else (
            a.get('title')
            or None
        )
    ), url_rule=lambda e, a:(
        a.get('href')
        or a.get('data-url')
        or None
    ))

    trie = build_navigation_trie(hierarchy,filter=lambda node: (
        True
        # and node.text != "En"
    ))

    data = trie.list_all()
    navigation_data = {
        ".".join(k): filter_url(v["url"], url)
        for k, v in data if filter_url(v["url"], url)
    }

    await save_file([
        node.model_dump() for node in hierarchy
    ] if isinstance(hierarchy, list)
        else hierarchy.model_dump()
    , "hierarchy.json")
    await save_file(navigation_data, "navigation_trie.json")

if __name__ == "__main__":
    asyncio.run(main())
