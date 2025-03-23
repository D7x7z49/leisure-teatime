# core/data/extractor.py
from pathlib import Path
from lxml import html
from typing import Union, List, Any, Optional
from playwright.async_api import ElementHandle
from core.data.storage import read_file

async def extract_xpath(dom: Union[str, html.HtmlElement, ElementHandle], xpath: str) -> List[Any]:
    """Extract content from DOM using XPath."""
    if isinstance(dom, str):
        tree = html.fromstring(dom)
    elif isinstance(dom, html.HtmlElement):
        tree = dom
    elif isinstance(dom, ElementHandle):
        # 从 Playwright ElementHandle 获取 HTML
        html_content = await dom.inner_html()
        tree = html.fromstring(html_content)
    else:
        raise ValueError(f"Unsupported DOM type: {type(dom)}")
    return tree.xpath(xpath)

async def extract_from_file(xpath: str, filename: str = "dom.html", dir: Optional[Path] = None) -> List[Any]:
    """Extract XPath content from a cached file."""
    content = await read_file(filename, dir)
    if content:
        return await extract_xpath(content, xpath)
    return []

async def extract_from_element(element: ElementHandle, xpath: str) -> List[Any]:
    """Extract XPath content from a Playwright ElementHandle."""
    return await extract_xpath(element, xpath)

# 示例用法
if __name__ == "__main__":
    import asyncio
    async def test():
        # 从文件提取
        titles = await extract_from_file("//title/text()")
        print(f"Extracted titles: {titles}")

    asyncio.run(test())
