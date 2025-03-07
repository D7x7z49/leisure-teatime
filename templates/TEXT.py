# templates/TEXT.py
from pathlib import Path
from core.utils.decorators import task_runner

@task_runner(Path(__file__), "index.html")
def execute(data, known_vars):
    """Extract text from HTML and convert to Markdown, storing results in known_vars.

    Args:
        data (str): HTML content from the task directory (e.g., index.html or dom.html).
        known_vars (dict): Dictionary to store extracted text and images.

    Blacklist Rules:
        - Format: (condition, None) to skip elements and their children.
        - Example: (lambda elem: elem.tag == 'script', None) skips <script> tags.

    Extraction Rules:
        - Format: (condition, process, priority) to extract and process elements.
        - Example: (lambda elem: elem.tag == 'h1', lambda elem: f'# {clean_text(elem.text_content())}', 10)

    Helper Functions:
        - clean_text(text): Remove extra whitespace and normalize text.
        - to_markdown(tag, text): Convert text to Markdown based on tag.
        - has_ancestor(elem, tag, attr, value): Check if ancestor matches criteria.
        - normalize_link(url, base_url): Normalize relative URLs.
    """
    from lxml import html
    import re
    from urllib.parse import urljoin

    if not data:
        known_vars["cleaned_text"] = "No HTML data available"
        known_vars["images"] = []
        return

    # Helper functions
    def clean_text(text: str) -> str:
        """Remove extra whitespace and normalize text."""
        return re.sub(r'\s+', ' ', text.strip()) if text and text.strip() else ""

    def to_markdown(tag: str, text: str) -> str:
        """Convert text to Markdown based on tag."""
        if tag == "h1":
            return f"# {clean_text(text)}\n"
        if tag == "h2":
            return f"## {clean_text(text)}\n"
        if tag == "p":
            return f"{clean_text(text)}\n\n"
        if tag == "a" and text:
            return f"[{clean_text(text)}]({text})" if text.startswith("http") else f"[{clean_text(text)}]"
        return clean_text(text)

    def has_ancestor(elem, tag=None, attr=None, value=None) -> bool:
        """Check if ancestor matches tag, attribute, or value."""
        parent = elem.getparent()
        while parent is not None:
            if (tag is None or parent.tag == tag) and \
               (attr is None or parent.get(attr) == value):
                return True
            parent = parent.getparent()
        return False

    def normalize_link(url: str, base_url: str) -> str:
        """Normalize relative URLs using base URL."""
        return urljoin(base_url, url)

    # Constants
    TAB = "  "  # Indentation for nested elements
    IMG_PLACEHOLDER = "[[+_+]]"  # Non-Markdown placeholder for images
    MAX_DEPTH = 1000  # Maximum recursion depth to prevent stack overflow

    # Blacklist rules (short rules kept concise, long rules split)
    BLACKLIST_RULES = [
        # Skip scripts and styles
        (lambda elem: elem.tag in {"script", "style"}, None),
        # Skip elements with class="ignore" or id starting with "skip-"
        (lambda elem: (
            elem.get("class") == "ignore" or
            elem.get("id", "").startswith("skip-")
        ), None),
    ]

    # Extraction rules (short rules concise, long rules formatted)
    EXTRACT_RULES = [
        # Simple heading rules
        (lambda elem: elem.tag == "h1", lambda elem: to_markdown("h1", elem.text_content()), 10),
        (lambda elem: elem.tag == "h2", lambda elem: to_markdown("h2", elem.text_content()), 10),
        # Paragraph rule
        (lambda elem: elem.tag == "p", lambda elem: to_markdown("p", elem.text_content()), 10),
        # Links with ancestor check for specific sections
        (lambda elem: (
            elem.tag == "a" and
            has_ancestor(elem, tag="div", attr="class", value="content")
        ), lambda elem: to_markdown("a", elem.get("href", "")), 10),
        # Images with normalized links
        (lambda elem: elem.tag == "img", lambda elem: (
            known_vars["images"].append(normalize_link(elem.get("src", ""), data)) or
            f"![Image]({elem.get('src', IMG_PLACEHOLDER)})\n"
        ) if elem.get("src") else IMG_PLACEHOLDER, 10),
        # Default rule for remaining text
        (lambda _: True, lambda elem: clean_text(elem.text), 20),
    ]

    # Sort extraction rules by priority
    EXTRACT_RULES.sort(key=lambda x: x[2])

    tree = html.fromstring(data)
    root = tree  # Use entire tree, replace with your XPath if needed (e.g., '//body')
    base_url = tree.base_url or ""  # Use document base URL for links

    known_vars["images"] = []
    def process_recursive(element, depth=0, cache=None):
        """Recursively process HTML elements with separate blacklist and extraction rules."""
        if depth > MAX_DEPTH:
            return []

        if cache is None:
            cache = {}

        result = []
        elem_id = id(element)
        if elem_id not in cache:
            cache[elem_id] = {"tag": element.tag, "attrib": element.attrib}
        elem_info = cache[elem_id]

        # Check blacklist first
        for condition, _ in BLACKLIST_RULES:
            if condition(element):
                return result  # Skip element and its children

        # Apply extraction rules
        for condition, process, _ in EXTRACT_RULES:
            if condition(element):
                processed_text = process(element)
                if processed_text:
                    result.append(processed_text)
                break

        # Process tail text
        if element.tail and element.tail.strip():
            result.append(clean_text(element.tail))

        # Recurse into children
        for child in element:
            result.extend(process_recursive(child, depth + 1, cache))

        return result

    text_list = process_recursive(root)
    known_vars["cleaned_text"] = "".join(text_list)

if __name__ == "__main__":
    execute()
