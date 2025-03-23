# templates/fetch.py
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page
from core.browser.controller import with_cdp
from core.browser.fetcher import fetch_page_content, initialize, setup_anti_detection, get_page, setup_resource_blocking
from core.data.storage import set_default_dir, save_file, read_file, file_exists

set_default_dir(Path(__file__).parent / ".data")

async def init(context: BrowserContext) -> None:
    pass

@with_cdp
async def main(context: BrowserContext, url: str = "https://example.com"):
    """Fetch content from a URL and cache it."""

    initialize(context, init, is_anti_detection=True)
    cache_file = "dom.html"
    if await file_exists(cache_file):
        content = await read_file(cache_file)
        print(f"Loaded {len(content)} bytes from cache: {cache_file}")
    else:
        await setup_anti_detection(context)

        page = await get_page(context, url)
        await setup_resource_blocking(page)

        content = await fetch_page_content(page, url)
        if content:
            await save_file(content, cache_file)
            print(f"Fetched and cached {len(content)} bytes from {url}")
        else:
            print(f"Failed to fetch {url}")

if __name__ == "__main__":
    asyncio.run(main())
