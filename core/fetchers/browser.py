# core/fetchers/browser.py
from playwright.sync_api import sync_playwright, Playwright as SyncPlaywright
from playwright.async_api import async_playwright, Playwright as AsyncPlaywright, Page
from core.config import Config
from core.logging import get_logger, LogTemplates
from core.utils.files import ensure_dir
from functools import wraps
from typing import Callable, Dict, Any, Tuple

logger = get_logger("browser")

# Private config variables for brevity and efficiency
_USER_DATA_DIR = Config.BROWSER.USER_DATA_DIR
_HEADLESS = Config.BROWSER.HEADLESS
_TIMEOUT = Config.BROWSER.TIMEOUT
_BLOCKED_RESOURCES = Config.BROWSER.BLOCKED_RESOURCES
_EXECUTABLE_PATH = Config.BROWSER.EXECUTABLE_PATH

def with_sync_page(func: Callable) -> Callable:
    """Decorator to inject a Playwright page for sync operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(ensure_dir(_USER_DATA_DIR)),
                headless=_HEADLESS,
                executable_path=_EXECUTABLE_PATH,
            )
            page = context.new_page()
            for pattern in _BLOCKED_RESOURCES:
                page.route(pattern, lambda route: route.abort())
            try:
                return func(page, *args, **kwargs)
            finally:
                context.close()
    return wrapper

@with_sync_page
def fetch_page(page: Page, url: str, timeout: int = _TIMEOUT) -> Tuple[str, str, int]:
    """Fetch raw content, rendered content, and resource count in one pass."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    resources = []
    raw_content = None

    def capture_response(response):
        nonlocal raw_content
        if response.url == url:
            raw_content = response.text()

    page.on("response", capture_response)
    page.on("response", lambda r: resources.append(r.url))
    page.goto(url, timeout=timeout, wait_until="networkidle")
    dom_content = page.content()
    resource_count = len(set(resources))

    logger.info(LogTemplates.FETCH_SUCCESS.format(url=url, size=len(dom_content)))
    logger.debug(f"Loaded {resource_count} unique resources")
    return raw_content or "", dom_content, resource_count

@with_sync_page
def analyze_page(page: Page, url: str, timeout: int = _TIMEOUT) -> Dict[str, Any]:
    """Analyze page dynamism."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    page.goto(url, timeout=timeout, wait_until="networkidle")
    initial_content = page.evaluate("document.documentElement.outerHTML")
    final_content = page.content()
    is_dynamic = "partial" if final_content != initial_content else "static"
    logger.info(LogTemplates.FETCH_SUCCESS.format(url=url, size=len(final_content)))
    return {"content": final_content, "is_dynamic": is_dynamic}

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
        """Initialize persistent browser context with DevTools enabled."""
        self._playwright = await async_playwright().start()
        try:
            user_data_dir = str(ensure_dir(_USER_DATA_DIR))
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=_HEADLESS,
                executable_path=_EXECUTABLE_PATH,
                devtools=True,  # 默认启用 DevTools
            )
            logger.debug(f"Initialized async browser context with {user_data_dir}, DevTools enabled")
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
    """Fetch page content asynchronously."""
    content = await page.goto(url)
    if content:
        text = await page.content()
        return text[:100] + "..." if len(text) > 100 else text
    logger.error(LogTemplates.ERROR.format(msg=f"Failed to fetch {url}"))
    return "Fetch failed"

@AsyncBrowserManager.register("js", help="Run JavaScript code in browser. Usage: js <code>")
async def run_js(page: Page, code: str) -> str:
    """Run JavaScript code asynchronously."""
    result = await page.evaluate(code)
    return f"Result: {result}"
