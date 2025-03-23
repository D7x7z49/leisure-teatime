# templates/pagination.py
import asyncio
from pathlib import Path
from typing import List
from playwright.async_api import BrowserContext
from core.browser.controller import with_cdp
from core.browser.fetcher import detect_pagination, initialize, setup_anti_detection
from core.data.storage import set_default_dir

# 设置默认数据目录
set_default_dir(Path(__file__).parent / ".data")

# 分页选择器组件
PAGINATION_TAGS = ["a", "button", "span"]  # 可点击的标签
PAGINATION_TEXTS = [
    "下一页", "下页", "Next", "next", "前进", ">>", ">"
]  # 分页相关文本
PAGINATION_ATTRIBUTES = [
    "[rel='next']",
    "[class*='next']", "[class*='page']", "[class*='pagination']",
    "[id*='next']", "[id*='page']"
]  # 属性条件

def generate_pagination_selectors() -> List[str]:
    """动态生成分页选择器，包括 CSS 和 XPath。"""
    selectors = []

    # 生成 CSS 选择器
    for tag in PAGINATION_TAGS:
        # 文本匹配
        for text in PAGINATION_TEXTS:
            selectors.append(f"{tag}:text('{text}')")
        # 属性匹配（仅限 a 和 button）
        if tag in ["a", "button"]:
            for attr in PAGINATION_ATTRIBUTES:
                selectors.append(f"{tag}{attr}")

    # 生成 XPath 选择器
    tag_conditions = " or ".join(f"self::{tag}" for tag in PAGINATION_TAGS)
    text_conditions = " or ".join(f"contains(text(), '{text}')" for text in PAGINATION_TEXTS)
    # 添加小写转换的 next 匹配
    xpath = (
        f"//*[{tag_conditions}][{text_conditions} or "
        f"contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]"
    )
    selectors.append(xpath)

    return selectors

PAGINATION_SELECTORS = generate_pagination_selectors()

async def init(context: BrowserContext) -> None:
    """初始化浏览器上下文。"""
    pass

@with_cdp
async def main(context: BrowserContext, url: str = "https://example.com"):
    """检测指定 URL 的分页情况。"""
    await initialize(context, init, is_anti_detection=True)
    result = await detect_pagination(context, url, PAGINATION_SELECTORS)
    print(result.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
