# core/cli/commands.py
import click
from core.tasks.manager import TaskManager
from typing import List, Dict, Optional

@click.group()
def cli():
    """Leisure Teatime CLI - A tool for managing tasks."""
    pass

@cli.command()
@click.argument("url")
@click.option("-u", "--use", is_flag=True, help="Switch to the task after adding it")
def add(url: str, use: bool) -> None:
    """Add a new task from URL."""
    manager = TaskManager()
    task_hash = manager.add(url)
    click.echo(f"Task added with ID: {task_hash}")
    if use:
        if manager.use(task_hash):
            click.echo(f"Switched to task: {task_hash}")
        else:
            click.echo(f"Failed to switch to task: {task_hash}")

@cli.command()
@click.argument("identifier")
def use(identifier: str) -> None:
    """Switch to a task by URL, hash, or alias."""
    manager = TaskManager()
    if manager.use(identifier):
        click.echo(f"Switched to task: {identifier}")
    else:
        click.echo(f"Task not found: {identifier}")

@cli.command()
@click.option("-t", "--tree", is_flag=True, help="Display tasks in a tree structure")
@click.option("-d", "--domain", default=None, help="Filter tasks by domain prefix")
def list(tree: bool, domain: Optional[str]) -> None:
    """List all tasks and their metadata."""
    manager = TaskManager()
    tasks = manager.list_tasks()
    if not tasks:
        click.echo("No tasks found.")
        return

    if tree:
        # 树形输出
        click.echo("Task Tree:")
        trie_dict = {}
        for path, ports in tasks:
            node = trie_dict
            for part in path:
                node = node.setdefault(part, {})
            for port, info in ports.items():
                node[f":{port}"] = info["task_id"]

        def print_tree(node: Dict, prefix: str = "") -> None:
            for key, value in node.items():
                if isinstance(value, dict):
                    click.echo(f"{prefix}├── {key}")
                    print_tree(value, prefix + "│   ")
                else:
                    click.echo(f"{prefix}└── {key} ({value})")

        print_tree(trie_dict)
    else:
        # 默认表格输出
        click.echo("Tasks:")
        for path, ports in tasks:
            domain_str = ".".join(reversed(path))
            if domain and not domain_str.startswith(domain):
                continue
            click.echo(f"  Domain: {domain_str}")
            for port, info in ports.items():
                alias = next((k for k, v in (manager.metadata.aliases or {}).items() if v == info["task_id"]), "None")
                click.echo(f"    Port: {port}, Task ID: {info['task_id']}, URL: {info['url']}, Alias: {alias}")

@cli.command()
@click.argument("url")
def remove(url: str) -> None:
    """Remove a task by URL."""
    manager = TaskManager()
    if manager.remove(url):
        click.echo(f"Task removed: {url}")
    else:
        click.echo(f"Task not found: {url}")

@cli.command()
@click.argument("name")
@click.argument("task_id")
def alias(name: str, task_id: str) -> None:
    """Set an alias for a task."""
    manager = TaskManager()
    if manager.metadata.set_alias(name, task_id):
        click.echo(f"Alias '{name}' set for task: {task_id}")
    else:
        click.echo(f"Alias '{name}' already exists.")

@cli.command()
def history() -> None:
    """Show recent task switch history."""
    manager = TaskManager()
    if not manager.metadata.history:
        click.echo("No history available.")
        return

    click.echo("Recent task history:")
    for entry in reversed(manager.metadata.history):
        click.echo(f"  {entry.timestamp}: {entry.task_id} ({entry.url})")

if __name__ == "__main__":
    cli()
