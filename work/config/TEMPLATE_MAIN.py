from pathlib import Path
from work.tools.task_executor import task_executor

@task_executor(Path(__file__))
def execute(data, known_vars):
    # Process HTML data and update known_vars using lxml XPath. Replace '<XPATH STRING>' with your XPath (e.g., '//title').
    from lxml import html

    if data:
        tree = html.fromstring(data)
        root_node = tree.xpath("//title")  # Replaced <XPATH STRING>
        known_vars["title"] = root_node[0].text if root_node else "No match found"
    else:
        known_vars["title"] = "No HTML data provided"

    print(__file__)


if __name__ == "__main__":

    pass
