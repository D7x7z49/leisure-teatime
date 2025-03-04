# core/cli.py
import importlib
import json
from pathlib import Path
import shlex
import time
from typing import Dict
import click
import asyncio
import shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter, WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from core.config import Config
from core.task_manager import TaskDataManager
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
@click.option("-n/--name", help="Custom task name")
@click.option("-q/--quiet", is_flag=True, help="Suppress output")
@click.option("-r/--refresh", is_flag=True, help="Refresh HTML files without overwriting .py files")
def task_add(url, name=None, quiet=False, refresh=False):
    """Add a task and fetch its page."""
    task_hash = TaskDataManager.generate_task_hash(url)
    task_dir = _TASK_DIR / task_hash
    task_dir.mkdir(exist_ok=True, parents=True)

    if not refresh or not (task_dir / "main.py").exists():
        for template in _TEMPLATE_FILES:
            shutil.copy(_TEMPLATES_DIR / template["source"], task_dir / template["target"])

    raw_content, dom_content, resource_count = fetch_page(url)
    if not raw_content or not dom_content:
        logger.error(f"Failed to fetch {url}")
        return

    write_file(task_dir / _RAW_HTML, raw_content)
    write_file(task_dir / _DOM_HTML, dom_content)

    data = TaskDataManager.load_tree()
    current = data["tree"]
    reversed_domain, path_parts = TaskDataManager.parse_url(url)

    # 构建树路径
    for part in reversed_domain:
        current = current.setdefault(part, {})
    if path_parts:
        for part in path_parts:
            current = current.setdefault(part, {})

    task_entry = {
        "url": url,
        "dir": str(task_dir),
        "hash": task_hash,
        "created": time.time(),
        "is_dynamic": "partial" if raw_content != dom_content else "static",
        "resource_count": resource_count
    }
    current[task_hash] = task_entry
    data["index"][task_hash] = reversed_domain + path_parts + [task_hash]
    TaskDataManager.save_tree(data)

    if not quiet:
        click.echo(f"Task added: {task_hash} at {task_dir} (resources: {resource_count})")
    logger.info(f"Task created: {task_hash}")

@cli.command("task-list")
@click.option("-d/--domain", help="Filter tasks by domain")
def task_list(domain=None):
    """List all tasks."""
    data = TaskDataManager.load_tree()
    if not data["tree"]:
        click.echo("No tasks found")
        return

    def print_tree(node: Dict, indent: int = 0):
        for key, value in node.items():
            if isinstance(value, dict) and "url" not in value:
                click.echo(" " * indent + f"├─ {key}")
                print_tree(value, indent + 2)
            else:
                click.echo(" " * indent + f"├─ {key} [{value.get('hash', 'N/A')}]")

    click.echo("Task Tree Structure:")
    print_tree(data["tree"])

    total_tasks = TaskDataManager.count_leaf_nodes(data["tree"])
    if total_tasks > 0:
        latest_task = max(data["index"].items(), key=lambda x: data["tree"].get(x[0], {}).get("created", 0))
        latest_hash, latest_path = latest_task
        latest_node = TaskDataManager._traverse_path(data["tree"], latest_path)
        click.echo(f"\nTotal Tasks: {total_tasks}")
        click.echo(f"Latest Task: {latest_hash} ({latest_node.get('url', 'N/A')})")

@cli.command("task-remove")
@click.argument("task_hash")
@click.option("-f/--force", is_flag=True, help="Force removal without confirmation")
def task_remove(task_hash, force=False):
    """Remove a task by hash."""
    data = TaskDataManager.load_tree()
    node, path = TaskDataManager.find_node(task_hash)
    if not node:
        click.echo(f"Task {task_hash} not found")
        return

    task_dir = Path(node["dir"])
    if task_dir.exists() and (force or click.confirm(f"Remove task {task_hash} at {task_dir}?")):
        shutil.rmtree(task_dir)
        logger.info(f"Removed task directory: {task_hash}")

    current = data["tree"]
    for key in path[:-1]:
        current = current[key]
    del current[path[-1]]
    del data["index"][task_hash]
    TaskDataManager.save_tree(data)
    click.echo(f"Task {task_hash} removed")

@cli.command("task-exec")
@click.argument("task_hash")
@click.option("-f/--file", default="main", help="Script file to execute (main, test, or text)")
@click.option("-v/--verbose", is_flag=True, help="Print execution results verbosely")
def task_exec(task_hash, file="main", verbose=False):
    """Execute a task script by hash."""
    node, _ = TaskDataManager.find_node(task_hash)
    if not node:
        click.echo(f"Task {task_hash} not found")
        return

    task_dir = Path(node["dir"])
    script_file = task_dir / f"{file}.py"
    if not script_file.exists():
        click.echo(f"Script {script_file} not found")
        return

    spec = importlib.util.spec_from_file_location(f"task_{task_hash}", script_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    click.echo(f"=== Task Execution Start [Hash: {task_hash}] ===")
    if hasattr(module, "execute"):
        known_vars = module.execute(task_dir=task_dir)
        if verbose:
            click.echo("=== Task Results ===")
            click.echo(f"Results:\n{json.dumps(known_vars, indent=2, ensure_ascii=False)}")
            click.echo("=== Task Results ===")
        else:
            result_summary = known_vars.get("result", "No result returned") if isinstance(known_vars, dict) else "Executed"
            click.echo(f"Task {task_hash} executed: {result_summary}")
        logger.info(f"Executed task: {task_hash}/{file}.py")
    else:
        click.echo(f"No 'execute' function found in {script_file}")
        logger.error(f"No 'execute' function in {script_file}")
    click.echo(f"=== Task Execution End [Hash: {task_hash}] ===")

@cli.command("script-add")
@click.argument("script_name")
def script_add(script_name):
    """Add a script to SCRIPT_DIR as a TUI command."""
    script_dir = ensure_dir(_SCRIPT_DIR / script_name)
    script_file = script_dir / f"{script_name}.py"

    template = Config.TEMPLATES.TUI_CMD_TEMPLATE
    help_text = f"Execute custom command {script_name}"
    docstring = f"Custom command for {script_name}"
    content = template.format(
        filename=script_file.name,
        cmd_name=script_name,
        func_name=script_name.replace('-', '_'),
        help_text=help_text,
        docstring=docstring
    )

    if not write_file(script_file, content):
        click.echo(f"Failed to add script: {script_file}")
        return

    config = read_json(_SCRIPT_CONFIG) or {"scripts": {}}
    scripts = config.get("scripts", {})
    script_data = {"dir": str(script_dir)}
    scripts[script_name] = script_data
    config["scripts"] = scripts

    if write_json(_SCRIPT_CONFIG, config):
        click.echo(f"Script added: {script_file}")
        logger.info(f"Script added: {script_file}")
    else:
        click.echo(f"Failed to update config for script: {script_name}")
        if script_file.exists():
            script_file.unlink()

@cli.command("script-list")
def script_list():
    """List all scripts in SCRIPT_DIR."""
    config = read_json(_SCRIPT_CONFIG) or {"scripts": {}}
    scripts = config.get("scripts", {})
    if not scripts:
        click.echo("No scripts found")
        return
    for name, data in scripts.items():
        click.echo(f"{name} - {data['dir']}")

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
        await page.goto("about:blank")

        commands = list(AsyncBrowserManager._registry.keys()) + ["exit"]
        completer = WordCompleter(commands, ignore_case=True)
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
                if cmd_name in AsyncBrowserManager._registry:
                    result = await browser.execute(cmd_name, page, *args)
                    click.echo(result)
                else:
                    click.echo(f"Unknown command: {cmd_name}. Type 'help' for available commands.")
            except Exception as e:
                logger.error(f"TUI error: {e}")
                click.echo(f"Error: {e}")
            await asyncio.sleep(1)

        if not page.is_closed():
            await page.close()
        await browser.close()
        click.echo("TUI exited.")

    asyncio.run(run_tui())

if __name__ == "__main__":
    cli()
