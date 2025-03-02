# templates/MAIN.py
from core.utils.decorators import task_runner

@task_runner()
def execute(data, known_vars):
    from lxml import html
    """Execute crawler function with HTML data and known variables."""
    if data:
        tree = html.fromstring(data)
        title = tree.xpath("//title")
        known_vars["title"] = title[0].text if title else "No title"
    else:
        known_vars["title"] = "No HTML data"

if __name__ == "__main__":
    execute()
