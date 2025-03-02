# templates/TEST.py
from pathlib import Path
from core.utils.decorators import task_runner

@task_runner(Path(__file__), "index.html")
def execute(data, known_vars):
    """Simple test function to extract text from HTML data.

    Args:
        data (str): HTML content from the task directory (e.g., index.html).
        known_vars (dict): Dictionary to store test results.

    Example:
        # Extract first 10 words as a test
        known_vars["test_text"] = " ".join(data.split()[:10])
        # For debugging, add: print(known_vars["test_text"])
    """
    if data:
        known_vars["test_text"] = " ".join(data.split()[:10])
    else:
        known_vars["test_text"] = "No HTML data available"

if __name__ == "__main__":
    execute()
