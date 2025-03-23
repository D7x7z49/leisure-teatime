# templates/automate.py
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page
from core.browser.controller import with_cdp
from core.browser.fetcher import initialize, setup_anti_detection
from core.data.storage import set_default_dir, save_file
from core.utils.functional import pipeline

set_default_dir(Path(__file__).parent / ".data")

async def init(context: BrowserContext) -> None:
    pass

async def navigate(page: Page, url: str) -> Page:
    await page.goto(url)
    return page

async def perform_actions(page: Page) -> Page:
    await page.click("a.login")
    await page.fill("input#username", "user")
    await page.fill("input#password", "pass")
    await page.click("button[type=submit]")
    return page

async def save_result(page: Page) -> None:
    content = await page.content()
    await save_file(content, "result.html")
    print(f"Saved automation result to result.html")

@with_cdp
async def main(context: BrowserContext, url: str = "https://example.com"):
    """Automate browser actions using a pipeline."""

    initialize(context, init, is_anti_detection=True)

    steps = [
        lambda _: context.new_page(),
        lambda page: navigate(page, url),
        perform_actions,
        save_result,
    ]
    await pipeline(None, steps)

if __name__ == "__main__":
    asyncio.run(main())
