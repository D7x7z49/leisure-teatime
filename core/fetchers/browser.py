# core/fetchers/browser.py
from playwright.sync_api import sync_playwright, Playwright as SyncPlaywright
from playwright.async_api import async_playwright, Playwright as AsyncPlaywright, Page, APIResponse, APIRequestContext
from core.config import Config
from core.logging import get_logger, LogTemplates
from core.utils.files import ensure_dir, read_file
from functools import wraps
from typing import Callable, Dict, Any, Tuple
from pathlib import Path
import importlib.util

logger = get_logger("browser")

# Private config variables
_USER_DATA_DIR = Config.BROWSER.USER_DATA_DIR
_HEADLESS = Config.BROWSER.HEADLESS
_TIMEOUT = Config.BROWSER.TIMEOUT
_BLOCKED_RESOURCES = Config.BROWSER.BLOCKED_RESOURCES
_EXECUTABLE_PATH = Config.BROWSER.EXECUTABLE_PATH
_SCRIPT_DIR = Config.WORK.SCRIPT_DIR

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
        self._request_context: APIRequestContext = None

    @classmethod
    async def instance(cls):
        """Get singleton instance asynchronously and load scripts."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._initialize()
            cls._instance._load_scripts()
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
                devtools=True,
            )
            self._request_context = self._context.request
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
    def _load_scripts(cls):
        """Load all Python scripts from SCRIPT_DIR into the registry."""
        script_dir = Path(_SCRIPT_DIR)
        if not script_dir.exists():
            logger.warning(f"SCRIPT_DIR {_SCRIPT_DIR} does not exist")
            return

        for script_file in script_dir.rglob("*.py"):
            try:
                script_name = script_file.stem
                spec = importlib.util.spec_from_file_location(script_name, script_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.debug(f"Loaded script: {script_file}")
            except Exception as e:
                logger.error(LogTemplates.ERROR.format(msg=f"Failed to load script {script_file}: {e}"))

    @classmethod
    def tui_cmd_register(cls, name: str, help: str = ""):
        """Register a TUI command with Page and APIRequestContext injection."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(self, request_context: APIRequestContext, *args, page: Page = None, **kwargs):
                try:
                    return await func(*args, page=page)
                except Exception as e:
                    logger.error(LogTemplates.ERROR.format(msg=f"Command {name} failed: {e}"))
                    return f"Error: {e}"
            cls._registry[name] = {"func": wrapper, "help": help or func.__doc__ or ""}
            return func
        return decorator

    # 移除 request_register 和默认 get/post 命令
    async def execute(self, name: str, page: Page, *args, **kwargs) -> Any:
        """Execute registered operation with page or request context."""
        if name not in self._registry:
            raise ValueError(f"Operation '{name}' not registered")

        if page.is_closed():
            logger.debug("Page closed, creating new page")
            page = await self.new_page()
            await page.goto("about:blank")

        return await self._registry[name]["func"](self, self._request_context, *args, page=page, **kwargs)


# 导入 TUI 命令
from core.fetchers.tui_cmd import *
