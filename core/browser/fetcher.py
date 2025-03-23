# core/browser/fetcher.py
from urllib.parse import parse_qs, urlparse
from playwright.async_api import BrowserContext, Page, Route, Error as PlaywrightError
import asyncio
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel
from core.config import CONFIG
from core.data.storage import file_exists, read_file, save_file  # 假设配置中可以定义反检测参数


# 现有的资源拦截函数（保持不变）
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

# 默认的反自动化检测 JS 脚本
BROWSER_ANTI_DETECTION_SCRIPT: str = """\
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
"""


async def setup_anti_detection(context: BrowserContext) -> None:
    """Set up anti-detection measures to bypass automation checks."""
    await context.add_init_script(script=BROWSER_ANTI_DETECTION_SCRIPT)


async def setup_resource_blocking(page: Page) -> None:
    """Set up resource blocking for the page to skip irrelevant assets."""
    async def handle_route(route: Route) -> None:
        # 如果资源类型在拦截列表中，则中止请求
        if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()
    await page.route("**", handle_route)

async def get_page(context: BrowserContext, target_url: str, is_resource_blocking: True) -> Page:
    for page in context.pages:
        current_url = page.url
        if current_url == target_url:
            return page
    new_page = await context.new_page()
    if is_resource_blocking:
        await setup_resource_blocking(new_page)
    return new_page


async def fetch_content(context: BrowserContext, url: str) -> Optional[str]:
    cache_file = "dom.html"

    content = None
    if await file_exists(cache_file):
        content = await read_file(cache_file)
        print(f"Loaded {len(content)} bytes from cache: {cache_file}")
    else:
        page = await get_page(context, url, is_resource_blocking=True)
        if page.url != url:
            await page.goto(url)
        content = await page.content()
        if content:
            await save_file(content, cache_file)
        else:
            print(f"Failed to fetch {url}")
    return content



async def initialize(context: BrowserContext, func: Callable, is_anti_detection: bool = True) -> None:
    if is_anti_detection:
        await setup_anti_detection(context)
    await func(context)

#########################################################################################
# 以下是新增的分页检测代码

class PaginationResult(BaseModel):
    """分页检测结果模型。"""
    has_pagination: bool
    mechanism: str
    urls: list[str]

async def _click_next_and_update(
    context: BrowserContext,
    current_page: Page,
    selectors: list[str],
    urls: list[str],
    managed_pages: list[Page]
) -> tuple[Page, bool]:
    """点击下一页并更新 URL，返回当前页面和是否成功的标志。"""
    next_locator = None
    for selector in selectors:
        locator = current_page.locator(selector)
        if await locator.count() > 0:
            next_locator = locator.first
            break

    if not next_locator:
        return current_page, False

    initial_page_count = len(context.pages)
    clicked = False
    try:
        await next_locator.click()
        await asyncio.sleep(1)
        pages = context.pages
        if len(pages) > initial_page_count:  # 新页面打开
            new_page = pages[-1]
            await new_page.wait_for_load_state("networkidle", timeout=5000)
            urls.append(new_page.url)
            managed_pages.append(new_page)
            current_page = new_page
        else:  # 原页面导航
            await current_page.wait_for_load_state("networkidle", timeout=5000)
            urls.append(current_page.url)
        clicked = True
    except PlaywrightError as e:
        print(f"Click failed: {e}")

    return current_page, clicked

async def detect_pagination(
    context: BrowserContext,
    url: str,
    selectors: List[str]
) -> PaginationResult:
    """动态检测指定 URL 页面是否存在翻页并记录 URL 变化。"""
    starting_page = await context.new_page()
    managed_pages = [starting_page]
    try:
        await starting_page.goto(url, wait_until="networkidle", timeout=10000)
    except PlaywrightError as e:
        print(f"Failed to load URL {url}: {e}")
        await starting_page.close()
        return PaginationResult(has_pagination=False, mechanism="unknown", urls=[url])

    urls = [starting_page.url]
    current_page = starting_page

    for _ in range(2):
        current_page, clicked = await _click_next_and_update(context, current_page, selectors, urls, managed_pages)
        if not clicked:
            break

        if urls[-1] == urls[0]:
            initial_content = await current_page.content()
            await asyncio.sleep(1)
            new_content = await current_page.content()
            if initial_content == new_content:
                break

    if len(urls) == 1:
        has_pagination = False
        mechanism = "unknown"
    else:
        has_pagination = True
        if urls[-1] == urls[0]:
            mechanism = "POST" if len(urls) == 2 else "AJAX"
        else:
            mechanism = "GET"

    for page in managed_pages:
        if not page.is_closed():
            await page.close()

    return PaginationResult(has_pagination=has_pagination, mechanism=mechanism, urls=urls)


############################################################################################
# 以下是测试代码

async def main():
    from core.browser.controller import with_cdp

    @with_cdp
    async def task_main(context: BrowserContext):
        # 应用反检测设置
        # await setup_anti_detection(context)
        # page = await context.new_page()
        # content = await fetch_page_content(page, "https://bing.com")
        # print(f"Content length: {len(content or '')}")
        # # 测试反检测效果
        # webdriver = await page.evaluate("() => navigator.webdriver")
        # print(f"Webdriver detected: {webdriver}")  # 应为 undefined
        pass

    # await task_main()


if __name__ == "__main__":
    asyncio.run(main())
