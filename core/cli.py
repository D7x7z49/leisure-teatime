# core/cli.py
from pathlib import Path
from typing import Dict
import click
import asyncio
import shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from core.config import StaticConfig, Paths
from core.manager import TaskDataManager, ScriptDataManager
from core.fetchers.browser import fetch_page, AsyncBrowserManager
from core.logging import get_logger
from core.utils.files import write_file  # 更新导入
import importlib.util

logger = get_logger("cli")

class AliasedGroup(click.Group):
    COMMAND_ALIASES = {
        "ta": "task-add", "tl": "task-list", "tr": "task-remove", "te": "task-exec",
        "sa": "script-add", "sl": "script-list", "sr": "script-remove", "i": "interactive"
    }

    def get_command(self, ctx, cmd_name):
        return super().get_command(ctx, self.COMMAND_ALIASES.get(cmd_name, cmd_name))

@click.group(cls=AliasedGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    if verbose:
        logger.setLevel("DEBUG")

@cli.command("task-add")
@click.argument("url")
@click.option("--name", help="Custom task name")
@click.option("--quiet", is_flag=True, help="Suppress output")
@click.option("--refresh", is_flag=True, help="Refresh HTML files without overwriting .py files")
def task_add(url, name=None, quiet=False, refresh=False):
    task_mgr = TaskDataManager()
    task_hash = task_mgr.generate_hash(url)
    task_dir = Paths.TASKS_DIR / task_hash
    task_dir.mkdir(exist_ok=True, parents=True)

    if not refresh or not (task_dir / "main.py").exists():
        for template in StaticConfig.Templates.FILES:
            shutil.copy(Paths.TEMPLATES_DIR / template["source"], task_dir / template["target"])

    raw_content, dom_content, resource_count = fetch_page(url)
    if not raw_content or not dom_content:
        logger.error(f"Failed to fetch {url}")
        return

    write_file(task_dir / Paths.RAW_HTML_FILE, raw_content)
    write_file(task_dir / Paths.DOM_HTML_FILE, dom_content)
    task_mgr.add_task(url, task_dir, raw_content, dom_content, resource_count)

    if not quiet:
        click.echo(f"Task added: {task_hash} at {task_dir} (resources: {resource_count})")

@cli.command("task-list")
@click.option("--domain", help="Filter tasks by domain")
def task_list(domain=None):
    task_mgr = TaskDataManager()
    if not task_mgr.data["tree"]:
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
    print_tree(task_mgr.data["tree"])

@cli.command("task-remove")
@click.argument("task_hash")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def task_remove(task_hash, force=False):
    task_mgr = TaskDataManager()
    node, _ = task_mgr.find_node(task_hash)
    if not node:
        click.echo(f"Task {task_hash} not found")
        return

    task_dir = Path(node["dir"])
    if task_dir.exists() and (force or click.confirm(f"Remove task {task_hash} at {task_dir}?")):
        shutil.rmtree(task_dir)
    task_mgr.remove_task(task_hash)
    click.echo(f"Task {task_hash} removed")

@cli.command("task-exec")
@click.argument("task_hash")
@click.option("--file", default="main", help="Script file to execute (main, test, or text)")
@click.option("--verbose", is_flag=True, help="Print execution results verbosely")
def task_exec(task_hash, file="main", verbose=False):
    task_mgr = TaskDataManager()
    node, _ = task_mgr.find_node(task_hash)
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
        result = module.execute(task_dir=task_dir)
        if verbose and result:
            click.echo(f"Results:\n{result}")
        else:
            click.echo(f"Task {task_hash} executed: {result.get('result', 'No result') if isinstance(result, dict) else 'Done'}")
    else:
        click.echo(f"No 'execute' function found in {script_file}")
    click.echo(f"=== Task Execution End [Hash: {task_hash}] ===")

@cli.command("script-add")
@click.argument("script_name")
def script_add(script_name):
    script_mgr = ScriptDataManager()
    script_dir = Paths.SCRIPTS_DIR / script_name
    script_dir.mkdir(exist_ok=True, parents=True)
    script_file = script_dir / f"{script_name}.py"

    content = StaticConfig.Templates.TUI_CMD_TEMPLATE.format(
        filename=script_file.name,
        cmd_name=script_name,
        func_name=script_name.replace('-', '_'),
        help_text=f"Execute custom command {script_name}",
        docstring=f"Custom command for {script_name}"
    )
    write_file(script_file, content)
    script_mgr.add_script(script_name, script_dir)
    click.echo(f"Script added: {script_file}")

@cli.command("script-list")
def script_list():
    script_mgr = ScriptDataManager()
    if not script_mgr.data["tree"]:
        click.echo("No scripts found")
        return
    for name, data in script_mgr.data["tree"].items():
        click.echo(f"{name} - {data['dir']}")

@cli.command("script-remove")
@click.argument("name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def script_remove(name, force=False):
    script_mgr = ScriptDataManager()
    if name not in script_mgr.data["tree"]:
        click.echo(f"Script {name} not found")
        return
    script_dir = Path(script_mgr.data["tree"][name]["dir"])
    if script_dir.exists() and (force or click.confirm(f"Remove script {name} at {script_dir}?")):
        shutil.rmtree(script_dir)
    script_mgr.remove_script(name)
    click.echo(f"Script {name} removed")

@cli.command("interactive")
def interactive():
    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit()

    async def run_tui():
        browser = await AsyncBrowserManager.instance()
        page = await browser.new_page()
        await page.goto("about:blank")

        commands = list(AsyncBrowserManager._registry.keys()) + ["exit"]
        completer = WordCompleter(commands, ignore_case=True)
        history_path = Paths.SCRIPTS_DIR / ".tui_history" / "history"
        history_path.parent.mkdir(exist_ok=True, parents=True)
        session = PromptSession(
            "TUI> ",
            completer=completer,
            complete_while_typing=True,
            history=FileHistory(str(history_path)),
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
                parts = cmd.split()
                cmd_name, args = parts[0], parts[1:] if len(parts) > 1 else []
                if cmd_name in AsyncBrowserManager._registry:
                    kwargs = {k.split("=")[0]: k.split("=")[1] for k in args if "=" in k}
                    pos_args = [a for a in args if "=" not in a]
                    result = await browser.execute(cmd_name, page, *pos_args, **kwargs)
                    click.echo(result)
                else:
                    click.echo(f"Unknown command: {cmd_name}. Type 'help' for commands.")
            except Exception as e:
                logger.error(f"TUI error: {e}")
                click.echo(f"Error: {e}")
            await asyncio.sleep(0.1)

        if not page.is_closed():
            await page.close()
        await browser.close()
        click.echo("TUI exited.")

    asyncio.run(run_tui())

if __name__ == "__main__":
    cli()
