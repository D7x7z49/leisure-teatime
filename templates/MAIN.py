# templates/MAIN.py
from pathlib import Path
from core.utils.decorators import task_runner

@task_runner(Path(__file__), "dom.html")
def execute(data, known_vars):
    """Execute main crawler function with HTML data and known variables.

    Args:
        data (str): HTML content from the task directory (e.g., dom.html).
        known_vars (dict): Dictionary to store extracted data, initialized empty.

    Example:
        # Extract title and description
        tree = html.fromstring(data)
        known_vars["title"] = tree.xpath("//title/text()")[0]
        known_vars["desc"] = tree.xpath("//meta[@name='description']/@content")[0] if tree.xpath("//meta[@name='description']") else "No description"
    """
    from lxml import html

    if data:
        tree = html.fromstring(data)
        nodes = tree.xpath("//title")
        known_vars["title"] = nodes[0].text if nodes else "No title found"
    else:
        known_vars["title"] = "No HTML data available"

if __name__ == "__main__":
    execute()
