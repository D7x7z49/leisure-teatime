# work/tools/task_executor.py
from functools import wraps
from pathlib import Path
from contextlib import redirect_stdout
import click
import json
import importlib.util
import io
from work.tools.logging_utils import set_log_file, logall_msg
from work.config.constants import GlobalConfig as CG, TasksConfig as CT, LogConfig as CL

set_log_file(CL.LOG_DIR / f"{Path(__file__).stem}.log")

def task_executor(task_file=None):
    """Decorator to inject HTML data and known_vars into execute function"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            file_path = Path(task_file or __file__)
            task_dir = file_path.parent

            html_file = task_dir / CT.DEFAULT_HTML
            data = html_file.read_text(encoding="utf-8") if html_file.exists() else ""
            known_vars = {}

            logall_msg(f"Executing task in {task_dir}")
            logall_msg(f"=== [Task Start] ===")
            output_capture = io.StringIO()
            with redirect_stdout(output_capture):
                func(data, known_vars)
            captured_output = output_capture.getvalue().strip()
            if captured_output:
                logall_msg(captured_output)
            logall_msg(f"=== [Task Result] ===")
            logall_msg("Known variables after execution:")
            logall_msg(json.dumps(known_vars, indent=2, ensure_ascii=False))
            logall_msg(f"=== [Task End] ===")

            return known_vars
        return wrapper
    return decorator

def execute_task_module(task_module: str):
    """Execute the specified task module's execute function"""
    try:
        task_prefix = f"{CG.ROOT_DIR.name}.{CT.TASKS_DIR}"
        if not task_module.startswith(task_prefix):
            raise ValueError(f"Invalid task module: {task_module}. Must start with '{task_prefix}'")

        module_path = CG.ROOT_DIR.parent / Path(task_module.replace(".", "/")) / CT.DEFAULT_MAIN
        if not module_path.exists():
            raise FileNotFoundError(f"Task module file not found: {module_path}")

        spec = importlib.util.spec_from_file_location(task_module, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "execute"):
            logall_msg(f"Loading task: {task_module}")
            module.execute()
            logall_msg(f"Successfully executed {task_module}")
        else:
            logall_msg(f"No 'execute' function found in {task_module}", level="ERROR")
    except Exception as e:
        logall_msg(f"Failed to execute task {task_module}: {e}", level="ERROR")

@click.command()
@click.argument("task_module")
def main(task_module: str):
    """Execute a task module's execute function"""
    execute_task_module(task_module)

if __name__ == "__main__":
    main()
