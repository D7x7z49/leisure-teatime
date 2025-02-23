# work/tools/task_generator.py
from dataclasses import dataclass
from pathlib import Path
from typing import Union
from urllib.parse import urlparse
import click
import requests
from work.config.constants import GlobalConfig as CG, TasksConfig as CT, LogConfig as CL
from work.tools.helpers import BaseContext, get_module_path
from work.tools.logging_utils import log_step, set_log_file, log_control

set_log_file(CL.LOG_DIR / f"{Path(__file__).stem}.log")

@dataclass
class TaskOptions:
    """Task generation options"""
    url: str
    force: bool = False
    timeout: int = 12
    quiet: bool = False
    silent: bool = False

@dataclass
class TaskContext(BaseContext):
    """Task-specific execution context"""
    options: Union[TaskOptions, None] = None

    def __post_init__(self):
        """Ensure options is set before use"""
        if self.options is None:
            raise ValueError("TaskContext.options must be provided")

def fetch_html(context: TaskContext):
    """Fetch HTML content from URL, return None if not HTML"""
    try:
        response = requests.get(context.options.url, timeout=context.options.timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            return response.text
        context.log(f"{CL.DETAIL_PREFIX} Non-HTML content: {content_type}")
        return None
    except requests.RequestException as e:
        context.log(f"{CL.DETAIL_PREFIX} Fetch failed: {e}")
        return None

def parse_domain(context: TaskContext):
    """Parse URL domain into parts"""
    parsed = urlparse(context.options.url)
    context.log(f"{CL.STEP_PREFIX} Parsing domain")
    domain_parts = parsed.netloc.split(".")
    domain_parts = [part for part in domain_parts if part not in CT.IGNORED_SUBDOMAINS]
    domain_parts = domain_parts[::-1]
    context.log(f"{CL.DETAIL_PREFIX} Host: {parsed.netloc}")
    context.log(f"{CL.DETAIL_PREFIX} Parts: {domain_parts}")
    return domain_parts

def parse_path(context: TaskContext):
    """Parse URL path into parts"""
    parsed = urlparse(context.options.url)
    context.log(f"{CL.STEP_PREFIX} Parsing path")
    path_parts = parsed.path.strip("/").split("/")
    if parsed.path and parsed.path[-1] != "/":
        path_parts = path_parts[:-1]
    context.log(f"{CL.DETAIL_PREFIX} Path: {parsed.path}")
    context.log(f"{CL.DETAIL_PREFIX} Parts: {path_parts}")
    return path_parts

def create_task_dir(context: TaskContext, domain_parts, path_parts):
    """Create task directory and return path"""
    task_dir = (CG.ROOT_DIR / CT.TASKS_DIR).joinpath(*domain_parts, *path_parts)
    context.log(f"{CL.STEP_PREFIX} Creating directory")
    task_dir.mkdir(parents=True, exist_ok=True)
    context.log(f"{CL.DETAIL_PREFIX} Dir: {task_dir}")
    return task_dir

def setup_main_file(context: TaskContext, task_dir: Path):
    """Setup main.py file in task directory"""
    main_file = task_dir / CT.DEFAULT_MAIN
    context.log(f"{CL.STEP_PREFIX} Setting up main file")
    if context.options.force or not main_file.exists():
        try:
            main_content = CT.TEMPLATE_MAIN_PATH.read_text(encoding="utf-8")
        except (FileNotFoundError, IOError) as e:
            context.log(f"{CL.DETAIL_PREFIX} Template load error: {e}")
            main_content = CT.DEFAULT_MAIN_TEMPLATE
        main_file.write_text(main_content, encoding="utf-8")
    context.log(f"{CL.DETAIL_PREFIX} File: {main_file}")
    return main_file

def setup_html_file(context: TaskContext, task_dir: Path):
    """Setup HTML file with fetched content or default"""
    html_file = task_dir / CT.DEFAULT_HTML
    context.log(f"{CL.STEP_PREFIX} Fetching HTML content")
    if context.options.force or not html_file.exists():
        html_content = fetch_html(context)
        data = html_content if html_content is not None else CT.DEFAULT_HTML_TEMPLATE
        html_file.write_text(data, encoding="utf-8")
    context.log(f"{CL.DETAIL_PREFIX} File: {html_file}")
    return html_file

def wrap_get_module_path(context: TaskContext, task_dir: Path) -> str:
    """Wrap get_module_path with logging"""
    context.log(f"{CL.STEP_PREFIX} Generating module path")
    module_path = get_module_path(task_dir)
    context.log(f"{CL.DETAIL_PREFIX} Module: {module_path}")
    return module_path

@log_step
def generate_task(context: TaskContext) -> str:
    """Generate task directory and files, return module path"""
    global log_control
    log_control.silent = context.options.silent
    log_control.quiet = context.options.quiet

    domain_parts = parse_domain(context)
    path_parts = parse_path(context)
    task_dir = create_task_dir(context, domain_parts, path_parts)
    setup_main_file(context, task_dir)
    setup_html_file(context, task_dir)
    module_path = wrap_get_module_path(context, task_dir)
    context.log(f"{CL.STEP_PREFIX} Task completed: {module_path}")
    return module_path

@click.command()
@click.argument("url")
@click.option("--force", "-f", is_flag=True, help="Force update files")
@click.option("--timeout", "-t", type=int, default=12, help="Request timeout in seconds")
@click.option("--quiet", "-q", is_flag=True, help="Show minimal logs")
@click.option("--silent", "-s", is_flag=True, help="Log to file only")
def main(url: str, **kwargs) -> None:
    """Generate a task from a URL with optional settings"""
    options = TaskOptions(url=url, **kwargs)
    context = TaskContext(options=options)
    generate_task(context)

if __name__ == "__main__":
    main()
