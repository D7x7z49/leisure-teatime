# templates/TEST.py
from core.utils.decorators import task_runner

@task_runner("index.html")
def execute(data, known_vars):
    """Test text extraction with HTML data and known variables."""
    if data:
        known_vars["text"] = " ".join(data.split()[:10])
    else:
        known_vars["text"] = "No HTML data"

if __name__ == "__main__":
    execute()
