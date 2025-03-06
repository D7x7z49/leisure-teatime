# core/fetchers/browser.py
from playwright.sync_api import sync_playwright, Playwright as SyncPlaywright
from playwright.async_api import async_playwright, Playwright as AsyncPlaywright, Page, APIResponse, APIRequestContext
from core.config import StaticConfig, Paths
from core.logging import get_logger, LogTemplates
from core.utils.files import ensure_dir, read_file
from functools import wraps
from typing import Callable, Dict, Any, Tuple
from pathlib import Path
import importlib.util

logger = get_logger("browser")

def with_sync_page(func: Callable) -> Callable:
    """Decorator to inject a Playwright page for sync operations with optimized resource blocking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(ensure_dir(Paths.BROWSER_DATA_DIR)),
                headless=StaticConfig.Browser.HEADLESS,
                executable_path=StaticConfig.Browser.EXECUTABLE_PATH,
            )
            page = context.new_page()
            # 优化拦截逻辑
            def block_resources(route):
                if any(route.request.resource_type in ["image", "media", "font"] for pattern in StaticConfig.Browser.BLOCKED_RESOURCES):
                    route.abort()
                else:
                    route.continue_()
            for pattern in StaticConfig.Browser.BLOCKED_RESOURCES:
                page.route(pattern, block_resources)
            try:
                result = func(page, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(LogTemplates.ERROR.format(msg=f"Page operation failed: {e}"))
                raise
            finally:
                context.close()
    return wrapper

@with_sync_page
def fetch_page(page: Page, url: str, timeout: int = StaticConfig.Browser.TIMEOUT) -> Tuple[str, str, int]:
    """Fetch raw content, rendered content, and resource count with faster DOM loading."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    resources = []
    raw_content = None

    def capture_response(response):
        nonlocal raw_content
        if response.url == url:
            try:
                raw_content = response.text()
            except Exception as e:
                logger.warning(f"Failed to capture raw content: {e}")

    page.on("response", capture_response)
    page.on("response", lambda r: resources.append(r.url))
    try:
        # 使用 domcontentloaded 代替 networkidle，加快 DOM 获取
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        dom_content = page.content()
        resource_count = len(set(resources))
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Fetch failed for {url}: {e}"))
        dom_content = page.content() if page else ""  # 超时后尝试获取已有内容
        resource_count = len(set(resources))

    logger.info(LogTemplates.FETCH_SUCCESS.format(url=url, size=len(dom_content)))
    logger.debug(f"Loaded {resource_count} unique resources")
    return raw_content or "", dom_content, resource_count

@with_sync_page
def analyze_page(page: Page, url: str, timeout: int = StaticConfig.Browser.TIMEOUT) -> Dict[str, Any]:
    """Analyze page dynamism with faster DOM loading."""
    logger.info(LogTemplates.FETCH_START.format(url=url))
    try:
        # 使用 domcontentloaded 代替 networkidle
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        initial_content = page.evaluate("document.documentElement.outerHTML")
        final_content = page.content()
        is_dynamic = "partial" if final_content != initial_content else "static"
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Analyze failed for {url}: {e}"))
        final_content = page.content() if page else ""
        is_dynamic = "unknown"

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
            user_data_dir = str(ensure_dir(Paths.BROWSER_DATA_DIR))
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=StaticConfig.Browser.HEADLESS,
                executable_path=StaticConfig.Browser.EXECUTABLE_PATH,
                devtools=True,
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
    def _load_scripts(cls):
        """Load all Python scripts from SCRIPT_DIR into the registry."""
        script_dir = Paths.SCRIPTS_DIR
        if not script_dir.exists():
            logger.warning(f"SCRIPT_DIR {script_dir} does not exist")
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
        """Register a TUI command with Page injection."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(page: Page, *args, **kwargs):
                try:
                    import inspect
                    sig = inspect.signature(func)
                    bound_args = sig.bind(page, *args, **kwargs)
                    bound_args.apply_defaults()
                    return await func(*bound_args.args, **bound_args.kwargs)
                except Exception as e:
                    logger.error(LogTemplates.ERROR.format(msg=f"Command {name} failed: {e}"))
                    return f"Error: {e}"
            cls._registry[name] = {"func": wrapper, "help": help or func.__doc__ or ""}
            return func
        return decorator

    async def execute(self, name: str, page: Page, *args, **kwargs) -> Any:
        """Execute registered operation with page."""
        if name not in self._registry:
            raise ValueError(f"Operation '{name}' not registered")

        if page.is_closed():
            logger.debug("Page closed, creating new page")
            page = await self.new_page()
            await page.goto("about:blank")

        return await self._registry[name]["func"](page, *args, **kwargs)

# 导入 TUI 命令
from core.fetchers.tui_cmd import *
