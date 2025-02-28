# work/tools/playwright_tool.py
import asyncio
import importlib.util
from pathlib import Path
from typing import Dict, Callable
from playwright.async_api import async_playwright, BrowserContext, Page
from urllib.parse import urlparse, urlunparse
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from work.tools.logging_utils import set_log_file, logall_msg
from work.config.constants import LogConfig as CL, PersistentConfig as CP

set_log_file(CL.LOG_DIR / f"{Path(__file__).stem}.log")

MSG = {
    "start": "browser_started",
    "exit": "browser_closed",
    "ext_exit": "browser_closed_externally",
    "cmd_fail": "command_{cmd}_failed: {err}",
    "load_cmd": "loaded_commands_from_{file}",
}

COMMANDS: Dict[str, Callable] = {}

def load_py_commands():
    """load commands from PY_TASKS_DIR"""
    print(f"Scanning: {CP.PY_TASKS_DIR}")
    for py_file in CP.PY_TASKS_DIR.glob("cmd_*.py"):
        try:
            module_name = f"work.script.py.{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Call module's register_commands if exists
            if hasattr(module, "register_commands"):
                module.register_commands(COMMANDS)
                logall_msg(MSG["load_cmd"].format(file=py_file.name), "INFO")
        except Exception as e:
            logall_msg(f"Failed to load {py_file.name}: {e}", "ERROR")
    print(f"Loaded commands: {list(COMMANDS.keys())}")

class PlaywrightTool:
    def __init__(self):
        self.context = None
        self.page = None
        self._exit = asyncio.Event()

    async def start(self):
        """launch browser and start interaction"""
        load_py_commands()
        register_base_commands()  # Register base commands after extensions
        async with async_playwright() as p:
            self.context = await p.chromium.launch_persistent_context(
                executable_path=CP.EXECUTABLE_PATH,
                user_data_dir=CP.USER_DATA_DIR,
                headless=False,
            )
            self.page = await self.context.new_page()
            self.context.on("close", lambda: self._exit.set())
            logall_msg(MSG["start"], "INFO")
            print("Browser ready. Type 'help' for commands.")
            await self.interact()

    async def interact(self):
        """run command loop with completion"""
        completer = WordCompleter(list(COMMANDS.keys()))
        session = PromptSession("Command> ", completer=completer, complete_while_typing=True)
        while not self._exit.is_set():
            try:
                cmd = (await session.prompt_async()).strip().split()
                if not cmd: continue
                cmd_name, args = cmd[0].lower(), cmd[1:]
                if cmd_name in COMMANDS:
                    await COMMANDS[cmd_name](self.page, *args)
                else:
                    print(f"Unknown command: {cmd_name}. Try 'help'.")
            except KeyboardInterrupt:
                await self.context.close()
                logall_msg(MSG["exit"], "INFO")
                print("Goodbye.")
                break
            except Exception as e:
                logall_msg(MSG["ext_exit"] if self._exit.is_set() else MSG["cmd_fail"].format(cmd=cmd_name or "unknown", err=e),
                          "INFO" if self._exit.is_set() else "ERROR")
                if self._exit.is_set():
                    print("Browser closed. Exiting.")
                    break

def register_base_commands():
    """register base commands"""
    async def help_cmd(page):
        """list all commands with descriptions
        usage: help
        """
        print("Available commands:")
        for name, func in sorted(COMMANDS.items()):
            print(f"  {name}\t# {' '.join(line.strip() for line in func.__doc__.splitlines())}")
    COMMANDS["help"] = help_cmd

    async def list_tasks(page):
        """list js tasks
        usage: list
        """
        tasks = [f.name for f in CP.JS_TASKS_DIR.glob("*.js")]
        print(f"JS tasks: {', '.join(tasks)}" if tasks else "No JS tasks.")
    COMMANDS["list"] = list_tasks

    async def load_task(page, task_name):
        """load and run js task
        usage: load <task_name>
        - <task_name>: name of js file (e.g., test)
        """
        task_path = CP.JS_TASKS_DIR / f"{task_name}.js"
        if not task_path.exists():
            print(f"Task '{task_name}.js' not found.")
            return
        result = await page.evaluate(open(task_path, "r", encoding="utf-8").read())
        print(f"Task '{task_name}.js' executed. Result: {result}")
    COMMANDS["load"] = load_task

    async def goto_url(page, url):
        """navigate to url
        usage: goto <url>
        - <url>: target website address (e.g., cnblogs.com)
        """
        if not url:
            print("URL required.")
            return
        parsed = urlparse(url if urlparse(url).scheme else f"https://{url}")
        if parsed.scheme not in ("http", "https"):
            print(f"Unsupported protocol: {parsed.scheme}. Use http or https.")
            return
        full_url = urlunparse(parsed)
        try:
            await page.goto(full_url)
            print(f"Navigated to: {full_url}")
        except Exception as e:
            http_url = urlunparse(parsed._replace(scheme="http")) if parsed.scheme == "https" else None
            await (page.goto(http_url) or print(f"Navigated to: {http_url}")) if http_url else print(f"Navigation failed: {e}")
    COMMANDS["goto"] = goto_url

    async def exit_tool(page):
        """exit tool
        usage: exit
        """
        await page.context.close()
        logall_msg(MSG["exit"], "INFO")
        print("Goodbye.")
    COMMANDS["exit"] = exit_tool

async def main():
    """run tool"""
    await PlaywrightTool().start()

if __name__ == "__main__":
    asyncio.run(main())
