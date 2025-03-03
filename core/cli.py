# core/cli.py
import importlib
import json
from pathlib import Path
import shlex
import time
import click
import asyncio
import shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter, WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from core.config import Config
from core.utils.files import ensure_dir, read_file, read_json, write_file, write_json
from core.utils.path import generate_task_name, generate_task_dir
from core.logging import get_logger, LogTemplates
from core.fetchers.browser import fetch_page, analyze_page, AsyncBrowserManager

logger = get_logger("cli")

# Shortened config variables
_TASK_DIR = Config.WORK.TASK_DIR
_TASK_CONFIG = Config.WORK.TASK_CONFIG_FILE
_SCRIPT_DIR = Config.WORK.SCRIPT_DIR
_SCRIPT_CONFIG = Config.WORK.SCRIPT_CONFIG_FILE
_RAW_HTML = Config.WORK.RAW_HTML_FILE
_DOM_HTML = Config.WORK.DOM_HTML_FILE
_TEMPLATES_DIR = Config.TEMPLATES.DIR
_TEMPLATE_FILES = Config.TEMPLATES.FILES

class AliasedGroup(click.Group):
    COMMAND_ALIASES = {
        "ta": "task-add",
        "tl": "task-list",
        "tr": "task-remove",
        "te": "task-exec",
        "sa": "script-add",
        "sl": "script-list",
        "sr": "script-remove",
        "i": "interactive",
    }

    def get_command(self, ctx, cmd_name):
        return super().get_command(ctx, self.COMMAND_ALIASES.get(cmd_name, cmd_name))

@click.group(cls=AliasedGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    """Leisure Teatime CLI. Commands: task-add (ta), task-list (tl), task-remove (tr), script-add (sa), script-list (sl), script-remove (sr), interactive (i)."""
    if verbose:
        logger.setLevel("DEBUG")

@cli.command("task-add")
@click.argument("url")
@click.option("--name", help="Custom task name")
@click.option("--quiet", is_flag=True, help="Suppress output")
@click.option("--refresh", is_flag=True, help="Refresh HTML files without overwriting .py files")
def task_add(url, name=None, quiet=False, refresh=False):
    """Add a task and fetch its page."""
    task_name = name or generate_task_name(url)
    task_dir = generate_task_dir(_TASK_DIR, task_name)
    task_dir.mkdir(exist_ok=True, parents=True)

    if not refresh or not (task_dir / "main.py").exists():
        for template in _TEMPLATE_FILES:
            shutil.copy(_TEMPLATES_DIR / template["source"], task_dir / template["target"])

    raw_content, dom_content, resource_count = fetch_page(url)
    if raw_content and dom_content:
        write_file(task_dir / _RAW_HTML, raw_content)
        write_file(task_dir / _DOM_HTML, dom_content)
        config = read_json(_TASK_CONFIG) or {"tasks": {}}
        config["tasks"][task_name] = {
            "url": url,
            "dir": str(task_dir),
            "hash": generate_task_dir(_TASK_DIR, task_name).name,
            "domain": task_name.split(".")[0] + "." + task_name.split(".")[1],
            "path": ".".join(task_name.split(".")[2:]) if len(task_name.split(".")) > 2 else "",
            "created": time.time(),
            "is_dynamic": "partial" if raw_content != dom_content else "static",
            "resource_count": resource_count
        }
        write_json(_TASK_CONFIG, config)
        if not quiet:
            click.echo(f"Task added: {task_name} at {task_dir} (resources: {resource_count})")
        logger.info(LogTemplates.TASK_CREATED.format(task_name=task_name))
    else:
        logger.error(LogTemplates.ERROR.format(msg=f"Failed to fetch {url}"))

@cli.command("task-list")
@click.option("--domain", help="Filter tasks by domain")
def task_list(domain=None):
    """List all tasks."""
    config = read_json(_TASK_CONFIG) or {"tasks": {}}
    tasks = config.get("tasks", {})
    if not tasks:
        click.echo("No tasks found")
        return
    [click.echo(f"{name} ({data.get('is_dynamic', 'unknown')}) - {data['dir']}")
     for name, data in tasks.items() if not domain or domain in data["domain"]]

@cli.command("task-remove")
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def task_remove(name, force=False):
    """Remove a task."""
    config = read_json(_TASK_CONFIG) or {"tasks": {}}
    tasks = config.get("tasks", {})
    if name not in tasks:
        click.echo(f"Task {name} not found")
        return
    task_dir = Path(tasks[name]["dir"])
    if task_dir.exists() and (force or click.confirm(f"Remove task {name} at {task_dir}?")):
        import shutil
        shutil.rmtree(task_dir)
        logger.info(f"Removed task: {name}")
    del tasks[name]
    write_json(_TASK_CONFIG, config)
    click.echo(f"Task {name} removed{' (directory not found)' if not task_dir.exists() else ''}")

@cli.command("task-exec")
@click.argument("task_name")
@click.option("--file", default="main", help="Script file to execute (main, test, or text)")
@click.option("--verbose", is_flag=True, help="Print execution results verbosely")
def task_exec(task_name, file="main", verbose=False):
    """Execute a task script."""
    config = read_json(_TASK_CONFIG) or {"tasks": {}}
    tasks = config.get("tasks", {})
    if task_name not in tasks:
        click.echo(f"Task {task_name} not found")
        return

    task_dir = Path(tasks[task_name]["dir"])
    script_file = task_dir / f"{file}.py"
    if not script_file.exists():
        click.echo(f"Script {script_file} not found")
        return

    spec = importlib.util.spec_from_file_location(f"task_{task_name}", script_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    click.echo("=== Task Execution GO ===")
    if hasattr(module, "execute"):
        known_vars = module.execute(task_dir=task_dir)
        if verbose:
            click.echo("=== Task Results ===")
            click.echo(f"Results:\n{json.dumps(known_vars, indent=2, ensure_ascii=False)}")
            click.echo("=== Task Results ===")
        else:
            click.echo(f"Executed {task_name}/{file}.py successfully")
        logger.info(f"Executed task: {task_name}/{file}.py")
    else:
        click.echo(f"No 'execute' function found in {script_file}")
        logger.error(f"No 'execute' function in {script_file}")
    click.echo("=== Task Execution ED ===")

@cli.command("script-add")
@click.argument("script_name")
@click.option("--request", is_flag=True, help="Add as a request task instead of a TUI command")
@click.option("--method", default="GET", help="HTTP method for request task (e.g., GET, POST)")
def script_add(script_name, request=False, method="GET"):
    """Add a script to SCRIPT_DIR as a TUI command or request task."""
    script_dir = ensure_dir(_SCRIPT_DIR / script_name)
    script_file = script_dir / f"{script_name}.py"

    template = Config.TEMPLATES.REQUEST_TEMPLATE if request else Config.TEMPLATES.TUI_CMD_TEMPLATE
    help_text = f"Execute {script_name} {'request' if request else 'command'}"
    docstring = f"Custom {'request' if request else 'command'} for {script_name}"
    content = template.format(
        filename=script_file.name,
        cmd_name=script_name,
        func_name=f"run_{script_name.replace('-', '_')}",
        method=method.upper(),
        help_text=help_text,
        docstring=docstring
    )

    if write_file(script_file, content):
        click.echo(f"Script added: {script_file}")
        logger.info(f"Script added: {script_file}")
    else:
        click.echo(f"Failed to add script: {script_file}")

@cli.command("script-list")
def script_list():
    """List all scripts in SCRIPT_DIR."""
    config = read_json(_SCRIPT_CONFIG) or {"scripts": {}}
    scripts = config.get("scripts", {})
    if not scripts:
        click.echo("No scripts found")
        return
    for name, data in scripts.items():
        script_type = "Request" if "method" in data else "Command"
        click.echo(f"{name} ({script_type}) - {data['dir']}")

@cli.command("script-remove")
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def script_remove(name, force=False):
    """Remove a script from SCRIPT_DIR."""
    config = read_json(_SCRIPT_CONFIG) or {"scripts": {}}
    scripts = config.get("scripts", {})
    if name not in scripts:
        click.echo(f"Script {name} not found")
        return
    script_dir = Path(scripts[name]["dir"])
    if script_dir.exists() and (force or click.confirm(f"Remove script {name} at {script_dir}?")):
        import shutil
        shutil.rmtree(script_dir)
        logger.info(f"Removed script: {name}")
    del scripts[name]
    write_json(_SCRIPT_CONFIG, config)
    click.echo(f"Script {name} removed{' (directory not found)' if not script_dir.exists() else ''}")

@cli.command("interactive")
def interactive():
    """Start an interactive TUI shell."""
    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        """Exit TUI with Ctrl+C."""
        event.app.exit()

    async def run_tui():
        browser = await AsyncBrowserManager.instance()
        page = await browser.new_page()
        await page.goto("about:blank")  # 初始化页面

        # 命令补全
        commands = list(AsyncBrowserManager._registry.keys()) + ["exit", "help"]
        completer = WordCompleter(commands, ignore_case=True)

        # 会话配置
        history_path = str(ensure_dir(_SCRIPT_DIR / ".tui_history") / "history")
        session = PromptSession(
            "TUI> ",
            completer=completer,
            complete_while_typing=True,
            history=FileHistory(history_path),
            key_bindings=bindings,
            multiline=False
        )

        click.echo("Interactive TUI started. Type 'help' for commands, 'exit' or Ctrl+C to quit.")
        while True:
            try:
                # 动态提示符显示页面 URL
                url = page.url if not page.is_closed() else "Closed"
                prompt = f"TUI ({url[:20]}...)> " if len(url) > 20 else f"TUI ({url})> "
                cmd = await session.prompt_async(prompt)

                cmd = cmd.strip()
                if not cmd:
                    continue
                if cmd == "exit":
                    break
                parts = shlex.split(cmd)
                cmd_name, args = parts[0], parts[1:] if len(parts) > 1 else []

                if cmd_name == "help":
                    if not args:
                        # 显示所有命令的简短帮助
                        click.echo("Available commands:")
                        for name, info in AsyncBrowserManager._registry.items():
                            short_help = info['help'].split('\n')[0]  # 提取第一行作为简短描述
                            click.echo(f"  {name}: {short_help}")
                    elif len(args) == 1:
                        # 显示指定命令的详细帮助
                        help_cmd = args[0]
                        if help_cmd in AsyncBrowserManager._registry:
                            click.echo(AsyncBrowserManager._registry[help_cmd]['help'])
                        else:
                            click.echo(f"Unknown command: {help_cmd}")
                    else:
                        click.echo("Usage: help [command]")
                else:
                    # 检查页面是否关闭，若关闭则重新创建
                    if page.is_closed():
                        page = await browser.new_page()
                        await page.goto("about:blank")
                        logger.debug("Recreated closed page")

                    # 执行命令
                    parts = shlex.split(cmd)
                    cmd_name, args = parts[0], parts[1:] if len(parts) > 1 else []
                    if cmd_name in AsyncBrowserManager._registry:
                        result = await browser.execute(cmd_name, page, *args)
                        click.echo(result)
                    else:
                        click.echo("Unknown command. Type 'help' for available commands.")
            except Exception as e:
                logger.error(f"TUI error: {e}")
                click.echo(f"Error: {e}")
                # 如果上下文关闭，退出 TUI
                if "closed" in str(e).lower():
                    click.echo("Browser context closed, exiting TUI...")
                    break
            await asyncio.sleep(1)  # 降低循环频率

        # 清理资源
        if not page.is_closed():
            await page.close()
        await browser.close()
        click.echo("TUI exited.")

    asyncio.run(run_tui())

if __name__ == "__main__":
    cli()
