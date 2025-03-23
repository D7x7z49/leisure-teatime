# templates/main.py
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page
from core.browser.controller import with_cdp
from core.browser.fetcher import initialize
from core.data.storage import set_default_dir, save_file, read_file, file_exists
from core.utils.functional import pipeline

set_default_dir(Path(__file__).parent  / ".data")

async def init(context: BrowserContext) -> None:
    pass


async def fetch_page(page: Page, url: str = "https://example.com") -> str:
    await page.goto(url)
    return await page.content()

async def cache_content(content: str) -> str:
    if content and not await file_exists("dom.html"):
        await save_file(content, "dom.html")
    return content or await read_file("dom.html")

async def process_content(content: str) -> str:
    return f"Processed {len(content)} bytes"

async def save_result(result: str) -> None:
    await save_file(result, "output.txt")
    print(f"Saved: {result}")

@with_cdp
async def main(context: BrowserContext):
    """Main task runner, define your pipeline here."""

    initialize(context, init, is_anti_detection=True)

    steps = [
        lambda _: context.new_page(),
        fetch_page,
        cache_content,
        process_content,
        save_result,
    ]
    await pipeline(None, steps)

if __name__ == "__main__":
    asyncio.run(main())
