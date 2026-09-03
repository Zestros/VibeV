"""Small, dependency-tolerant helpers for file type detection."""

from __future__ import annotations

import mimetypes
from pathlib import Path


def describe_file(path: str | Path) -> str:
    """Return a human-readable content type without requiring libmagic."""
    candidate = Path(path)
    mime, encoding = mimetypes.guess_type(candidate.name)
    description = mime or "application/octet-stream"
    try:
        import puremagic

        matches = puremagic.magic_file(str(candidate))
        if matches:
            match = matches[0]
            description = match.mime_type or match.name or description
    except (ImportError, OSError, ValueError):
        pass
    if encoding:
        description = f"{description}; {encoding}"
    return description

