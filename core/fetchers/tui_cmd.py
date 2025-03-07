# core/fetchers/tui_cmd.py
from playwright.async_api import Page
from core.config import Paths
from core.fetchers.browser import AsyncBrowserManager
from core.logging import get_logger, LogTemplates
from core.utils.files import read_file
from pathlib import Path
from typing import Optional

logger = get_logger("tui_cmd")

@AsyncBrowserManager.tui_cmd_register("fetch", help="""\
Fetch and display webpage content.

    USAGE:
      fetch <url> [--timeout=MS]

    ARGUMENTS:
      url       Target URL to fetch (required)

    OPTIONS:
      --timeout  Loading timeout in milliseconds (default: 30000)

    EXAMPLES:
      fetch https://example.com
      fetch https://api.example.com/data --timeout=5000
""")
async def tui_fetch(page: Page, url: str, timeout: int = 30000) -> str:
    """Fetch page content asynchronously."""
    try:
        content = await page.goto(url, timeout=timeout)
        if content:
            text = await page.content()
            return text[:100] + "..." if len(text) > 100 else text
        logger.error(LogTemplates.ERROR.format(msg=f"Failed to fetch {url}"))
        return "Fetch failed"
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Fetch failed: {e}"))
        return f"Error: {e}"

@AsyncBrowserManager.tui_cmd_register("js", help="""\
Execute JavaScript code or file in the current page context.

    USAGE:
      js <code|@filename>

    ARGUMENTS:
      code      JavaScript code to execute, or @filename to load from SCRIPT_DIR (required)

    EXAMPLES:
      js document.title
      js @test
      js @test.js
""")
async def tui_js(page: Page, code: str) -> str:
    """Execute JavaScript code or file in the current page context."""
    try:
        if code.startswith("@"):
            script_path = Paths.SCRIPTS_DIR / code[1:]
            if not script_path.suffix:
                script_path = script_path.with_suffix(".js")
            if not script_path.exists():
                logger.error(LogTemplates.ERROR.format(msg=f"JavaScript file {script_path} not found"))
                return f"Error: File {script_path} not found"

            script_content = read_file(script_path)
            if script_content is None:
                return f"Error: Failed to read {script_path}"
            executable_code = f"(async () => {{ {script_content} }})()"
        else:
            executable_code = code

        result = await page.evaluate(executable_code)
        if result is None:
            return "Result: Executed (no return value)"
        return f"Result: {result}"
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"JavaScript execution failed: {e}"))
        return f"Error: {e}"

@AsyncBrowserManager.tui_cmd_register("status", help="""\
Show current page status.

    USAGE:
      status [--detail]

    OPTIONS:
      --detail  Show full technical details (default: false)

    OUTPUT:
      URL | Title | Frame Count | DOM Size
""")
async def tui_status(page: Page, detail: bool = False) -> str:
    """Show status of the current page."""
    if page.is_closed():
        return "Page is closed"
    try:
        url = page.url
        title = await page.title()
        frame_count = len(page.frames)
        dom_size = await page.evaluate("document.documentElement.outerHTML.length")
        if detail:
            return f"URL: {url}\nTitle: {title}\nFrame Count: {frame_count}\nDOM Size: {dom_size} bytes"
        return f"URL: {url} | Title: {title} | Frames: {frame_count} | DOM Size: {dom_size}"
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Status check failed: {e}"))
        return f"Error: {e}"

@AsyncBrowserManager.tui_cmd_register("refresh", help="""\
Refresh TUI commands by reloading scripts from SCRIPT_DIR.

    USAGE:
      refresh

    EXAMPLES:
      refresh
""")
async def tui_refresh(page: Page) -> str:
    """Refresh TUI commands by reloading scripts from SCRIPT_DIR."""
    try:
        AsyncBrowserManager._load_scripts()
        return "Commands refreshed successfully"
    except Exception as e:
        logger.error(LogTemplates.ERROR.format(msg=f"Refresh failed: {e}"))
        return f"Error: {e}"

@AsyncBrowserManager.tui_cmd_register("help", help="""\
Display command help information.

    USAGE:
      help [<command>]

    ARGUMENTS:
      command   Optional command name to show detailed help (default: list all)

    EXAMPLES:
      help
      help fetch
""")
async def tui_help(page: Page, command: Optional[str] = None) -> str:
    """Display command help information."""
    if command is None:
        output = ["Available commands:"]
        for name, info in AsyncBrowserManager._registry.items():
            short_help = info['help'].split('\n')[0]
            output.append(f"  {name}: {short_help}")
        return "\n".join(output)
    elif command in AsyncBrowserManager._registry:
        return AsyncBrowserManager._registry[command]['help']
    return f"Unknown command: {command}"
