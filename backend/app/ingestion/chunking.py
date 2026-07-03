"""Split markdown into chunks for embedding.

Two strategies, composed:

1. **Heading-aware** (preferred): break the document at markdown headings
   (``#``..``######``) so each section — e.g. one FAQ ``## Q``  — becomes its
   own chunk. Each chunk keeps its heading text so it is self-contained.
2. **Token-window fallback**: any section larger than ``chunk_size`` is further
   split into overlapping token windows, with the section heading prepended to
   every window so context isn't lost.

A document with no headings falls back entirely to strategy 2, so prose still
chunks sensibly.

Note: converters (e.g. MarkItDown on .docx) sometimes emit headings *inline*
rather than at the start of a line, so heading detection is NOT anchored to
line starts.
"""
import re

# A markdown ATX heading: 1-6 '#' then a space, anywhere (not line-anchored),
# because some converters flatten newlines. We capture the start of each
# heading to slice the document into sections.
_HEADING_RE = re.compile(r"(?:^|\s)(#{1,6}\s)")


def _split_sections(text: str) -> list[str]:
    """Slice markdown into sections, each starting at a heading.

    Any preamble before the first heading is its own leading section.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [text] if text.strip() else []

    sections: list[str] = []
    # The '#' itself may be preceded by whitespace we matched; locate it.
    starts = [m.start(1) for m in matches]

    preamble = text[: starts[0]].strip()
    if preamble:
        sections.append(preamble)

    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)
    return sections


def _window(tokens: list[str], chunk_size: int, overlap: int) -> list[list[str]]:
    """Overlapping token windows over a single token list."""
    if not tokens:
        return []
    windows: list[list[str]] = []
    step = chunk_size - overlap
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_size]
        if not window:
            break
        windows.append(window)
        if start + chunk_size >= len(tokens):
            break
    return windows


def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Chunk markdown, preferring heading boundaries.

    ``chunk_size``/``overlap`` are measured in whitespace-delimited tokens
    (an approximation of model tokens).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if not text.strip():
        return []

    chunks: list[str] = []
    for section in _split_sections(text):
        tokens = section.split()
        if len(tokens) <= chunk_size:
            # Small enough to stand alone — the common FAQ case.
            chunks.append(section)
            continue

        # Oversized section: window it, prepending the heading as context so
        # each window stays self-contained. The heading is the text before the
        # first "**" (e.g. "## Q12. Are there any hidden charges?"), capped.
        heading = ""
        if section.lstrip().startswith("#"):
            heading = " ".join(section.split("**", 1)[0].split()[:30])

        for window in _window(tokens, chunk_size, overlap):
            piece = " ".join(window)
            if heading and not piece.startswith(heading[:20]):
                piece = f"{heading} … {piece}"
            chunks.append(piece)

    return chunks
