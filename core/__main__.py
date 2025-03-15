# core/__main__.py
import sys
import importlib

def run_module(module_path: str):
    # Convert file path to module name (e.g., 'core/events.py' -> 'core.events')
    module_name = module_path.replace('/', '.').replace('\\', '.').rstrip('.py')
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, '__main__'):
            module.__main__()
        else:
            print(f"Module {module_name} does not have a __main__ function.")
    except ImportError as e:
        print(f"Failed to import module {module_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m leisure-teatime <module_path>")
        sys.exit(1)
    module_path = sys.argv[1]
    run_module(module_path)
