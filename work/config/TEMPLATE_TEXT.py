from pathlib import Path
from work.tools.task_executor import task_executor

@task_executor(Path(__file__))
def execute(data, known_vars):
    """Process HTML data and convert to Markdown format, storing results in known_vars."""

    from lxml import html
    import re

    PROCESS_RULES = [
        ### Custom Rules ###
        # Simple rule example: match <h1> tags
        # (lambda elem: elem.tag == "h1", lambda elem: "# " + elem.text_content().strip() + "\n"),
        # Complex rule example: match <div> with class="bold" and id attribute
        # (lambda elem: elem.tag == "div" and elem.get("class") == "bold" and elem.get("id"),
        #  lambda elem: "**" + elem.text_content().strip() + "** (ID: " + elem.get("id") + ")\n"),
        (lambda elem: elem.tag == "p", lambda elem: elem.text_content().strip() + "\n"),
        ### Default Rules ###
        (lambda elem: elem.tag == "img", lambda elem: (known_vars["images"].append(elem.get("src", "")) or "[[+_+]]") if elem.get("src") else "[[+_+]]"),
        (lambda _: True, lambda elem: re.sub(r'\s+', ' ', elem.text.strip()) if elem.text and elem.text.strip() else ''),
    ]

    tree = html.fromstring(data)
    # Replaced <XPATH STRING>
    root = tree.xpath("<XPATH STRING>")[0]

    text_list = []
    known_vars["images"] = []
    for element in root.iter():
        for condition, process in PROCESS_RULES:
            if condition(element):
                processed_text = process(element)
                if processed_text:
                    text_list.append(processed_text)
                break
        if element.tail and element.tail.strip():
            text_list.append(re.sub(r'\s+', ' ', element.tail.strip()))
    known_vars["cleaned_text"] = "".join(text_list)

### Recursive Functions
# @task_executor(Path(__file__))
# def execute(data, known_vars):
#     """Process HTML data and convert to Markdown format, storing results in known_vars."""

#     from lxml import html
#     import re

#     PROCESS_RULES = [
#         ### Custom Rules ###
#         # Simple rule example: match <h1> tags
#         # (lambda elem: elem.tag == "h1", lambda elem: "# " + elem.text_content().strip() + "\n"),
#         # Complex rule example: match <div> with class="bold" and id attribute
#         # (lambda elem: elem.tag == "div" and elem.get("class") == "bold" and elem.get("id"),
#         #  lambda elem: "**" + elem.text_content().strip() + "** (ID: " + elem.get("id") + ")\n"),
#         (lambda elem: elem.tag == "p", lambda elem: elem.text_content().strip() + "\n\n"),
#         ### Default Rules ###
#         (lambda elem: elem.tag == "img", lambda elem: (known_vars["images"].append(elem.get("src", "")) or "[[+_+]]") if elem.get("src") else "[[+_+]]"),
#         (lambda _: True, lambda elem: re.sub(r'\s+', ' ', elem.text.strip()) if elem.text and elem.text.strip() else ''),
#     ]

#     tree = html.fromstring(data)
#     # Replaced <XPATH STRING>
#     root = tree.xpath("<XPATH STRING>")[0]

#     known_vars["images"] = []
#     def process_recursive(element):
#         result = []
#         for condition, process in PROCESS_RULES:
#             if condition(element):
#                 processed_text = process(element)
#                 if processed_text:
#                     result.append(processed_text)
#                 break
#         if element.tail and element.tail.strip():
#             result.append(re.sub(r'\s+', ' ', element.tail.strip()))
#         for child in element:
#             result.extend(process_recursive(child))
#         return result

#     text_list = process_recursive(root)
#     known_vars["cleaned_text"] = "".join(text_list)

### Version: Python3.8+
# @task_executor(Path(__file__))
# def execute(data, known_vars):
#     """Process HTML data and convert to Markdown format, storing results in known_vars."""

#     from lxml import html
#     import re

#     PROCESS_RULES = [
#         ### Custom Rules ###
#         # Simple rule example: match <h1> tags
#         # (lambda elem: elem.tag == "h1", lambda elem: "# " + elem.text_content().strip() + "\n"),
#         # Complex rule example: match <div> with class="bold" and id attribute
#         # (lambda elem: elem.tag == "div" and elem.get("class") == "bold" and elem.get("id"),
#         #  lambda elem: "**" + elem.text_content().strip() + "** (ID: " + elem.get("id") + ")\n"),
#         (lambda elem: elem.tag == "p", lambda elem: elem.text_content().strip() + "\n\n"),
#         ### Default Rules ###
#         (lambda elem: elem.tag == "img", lambda elem: (known_vars["images"].append(elem.get("src", "")) or "[[+_+]]") if elem.get("src") else "[[+_+]]"),
#         (lambda _: True, lambda elem: re.sub(r'\s+', ' ', elem.text.strip()) if elem.text and elem.text.strip() else ''),
#     ]

#     tree = html.fromstring(data)
#     # Replaced <XPATH STRING>
#     root = tree.xpath("<XPATH STRING>")[0]

#     known_vars["images"] = []
#     known_vars["cleaned_text"] = "".join([
#         item
#         for element in root.iter()
#         for item in (
#             [process(element)] if (processed := next((p for c, p in PROCESS_RULES if c(element)), None)) and processed else []
#         ) + (
#             [re.sub(r'\s+', ' ', element.tail.strip())] if element.tail and element.tail.strip() else []
#         )
#     ])

if __name__ == "__main__":

    pass
