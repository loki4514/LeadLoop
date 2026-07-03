"""Convert an uploaded file to markdown using MarkItDown.

Handles pdf, docx, xlsx, txt, pptx, html, and more — MarkItDown picks the right
converter from the file's type/extension.
"""
from markitdown import MarkItDown

# Reuse one instance; it's cheap and stateless for our usage.
_md = MarkItDown()


def extract_markdown(path: str) -> str:
    """Return the markdown text content of the file at ``path``.

    Raises if MarkItDown cannot parse the file.
    """
    result = _md.convert(path)
    return result.text_content or ""
