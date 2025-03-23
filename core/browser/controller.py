# core/browser/controller.py
import asyncio
import subprocess
import time
import psutil
from typing import Callable, Any, TypeVar
from playwright.async_api import async_playwright, BrowserContext

from core.config import CONFIG


T = TypeVar("T")

def launch_chrome_with_cdp() -> bool:
    port = CONFIG.browser_cdp_port

    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            pid = conn.pid
            if pid:
                process = psutil.Process(pid)
                if "chrome" in process.name().lower():
                    return False

    process = subprocess.Popen(
        [ str(CONFIG.browser_executable_path or "chrome") ] + CONFIG.chrome_cdp_launch_args,
        shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    return process.poll() is None

def with_cdp(task: Callable[[BrowserContext], Any]) -> Callable[..., Any]:
    async def wrapper(*args, **kwargs) -> Any:
        async with async_playwright() as pw:
            endpoint = f"http://localhost:{CONFIG.browser_cdp_port}"
            launch_chrome_with_cdp()
            browser = await pw.chromium.connect_over_cdp(endpoint)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            try:
                result = await task(context, *args, **kwargs)
            finally:
                await browser.close()
            return result
    return wrapper

def with_persistent(task: Callable[[BrowserContext], Any]) -> Callable[..., Any]:
    async def wrapper(*args, **kwargs) -> Any:
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                executable_path=CONFIG.browser_executable_path,
                user_data_dir=CONFIG.browser_user_data_dir,
                headless=CONFIG.browser_headless,
                timeout=CONFIG.browser_timeout,
            )
            try:
                result = await task(context, *args, **kwargs)
            finally:
                await context.close()
            return result
    return wrapper

async def main():

    @with_cdp
    async def test_cdp(context: BrowserContext):
        page = await context.new_page()
        await page.goto("https://www.baidu.com")
        title = await page.title()
        print(f"CDP Result: {title}")
        print(CONFIG.chrome_cdp_launch_args)

    await test_cdp()

if __name__ == "__main__":
    asyncio.run(main())
