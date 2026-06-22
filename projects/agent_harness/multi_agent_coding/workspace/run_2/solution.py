import re

def slugify(text: str) -> str:
    """Converts any text to a URL-safe slug."""

    if not text or text.isspace():
        return ""

    # 1. Strip leading/trailing whitespace
    text = text.strip()

    # 2. Convert to lowercase
    text = text.lower()

    # 3. Replace spaces and underscores with hyphens
    text = text.replace(" ", "-").replace("_", "-")

    # 4. Remove any character that is not a letter, digit, or hyphen
    text = re.sub(r"[^a-z0-9\-]", "", text)

    # 5. Collapse multiple consecutive hyphens into a single hyphen
    text = re.sub(r"-+", "-", text)

    # 6. Strip leading and trailing hyphens from the result
    text = text.strip("-")

    return text