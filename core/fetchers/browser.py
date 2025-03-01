# core/fetchers/browser.py
from playwright.sync_api import sync_playwright, Playwright as SyncPlaywright
from playwright.async_api import async_playwright, Playwright as AsyncPlaywright, Page
from core.config import Config
from core.logging import get_logger, LogTemplates
from core.utils.files import ensure_dir
from functools import wraps
from typing import Callable, Dict, Any

logger = get_logger("browser")

# Sync decorator for page injection
def with_sync_page(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(ensure_dir(Config.BROWSER.USER_DATA_DIR)),
                headless=Config.BROWSER.HEADLESS,
                executable_path=Config.BROWSER.EXECUTABLE_PATH,
            )
            page = context.new_page()
            for pattern in Config.BROWSER.BLOCKED_RESOURCES:
                page.route(pattern, lambda route: route.abort())
            try:
                return func(page, *args, **kwargs)
            finally:
                context.close()
    return wrapper

# Sync commands
@with_sync_page
def fetch_page(page: Page, url: str, timeout: int = Config.BROWSER.TIMEOUT) -> str:
    """Fetch page content."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    page.goto(url, timeout=timeout)
    content = page.content()
    logger.info(LogTemplates.FETCH_SUCCESS.format(url=url, size=len(content)))
    return content

@with_sync_page
def analyze_page(page: Page, url: str, timeout: int = Config.BROWSER.TIMEOUT) -> dict:
    """Analyze page dynamism."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    page.goto(url, timeout=timeout)
    initial_content = page.evaluate("document.documentElement.outerHTML")
    final_content = page.content()
    is_dynamic = "partial" if final_content != initial_content else "static"
    logger.info(LogTemplates.FETCH_SUCCESS.format(url=url, size=len(final_content)))
    return {"content": final_content, "is_dynamic": is_dynamic}

# Async Browser Manager for TUI
class AsyncBrowserManager:
    """Manage async Playwright browser instance for interactive use."""
    _instance = None
    _registry: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self._playwright: AsyncPlaywright = None
        self._context = None

    @classmethod
    async def instance(cls):
        """Get singleton instance asynchronously."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize persistent browser context."""
        self._playwright = await async_playwright().start()
        try:
            user_data_dir = str(ensure_dir(Config.BROWSER.USER_DATA_DIR))
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=Config.BROWSER.HEADLESS,
                executable_path=Config.BROWSER.EXECUTABLE_PATH,
            )
            logger.debug(f"Initialized async browser context with {user_data_dir}")
        except Exception as e:
            logger.error(LogTemplates.ERROR.format(msg=f"Browser init failed: {e}"))
            raise

    async def new_page(self) -> Page:
        """Create a new page."""
        return await self._context.new_page()

    async def close(self):
        """Close context and Playwright."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        logger.debug("Async browser context closed")

    @classmethod
    def register(cls, name: str, help: str = ""):
        """Register custom operation with help info."""
        def decorator(func: Callable):
            cls._registry[name] = {"func": func, "help": help or func.__doc__ or ""}
            return func
        return decorator

    async def execute(self, name: str, page: Page, *args, **kwargs) -> Any:
        """Execute registered operation."""
        if name not in self._registry:
            raise ValueError(f"Operation '{name}' not registered")
        return await self._registry[name]["func"](page, *args, **kwargs)

# Async commands for TUI
@AsyncBrowserManager.register("fetch", help="Fetch page content from URL. Usage: fetch <url>")
async def fetch_url(page: Page, url: str) -> str:
    content = await page.goto(url)
    if content:
        text = await page.content()
        return text[:100] + "..." if len(text) > 100 else text
    logger.error(LogTemplates.ERROR.format(msg=f"Failed to fetch {url}"))
    return "Fetch failed"

@AsyncBrowserManager.register("js", help="Run JavaScript code in browser. Usage: js <code>")
async def run_js(page: Page, code: str) -> str:
    result = await page.evaluate(code)
    return f"Result: {result}"
