"""Shared rendering helpers."""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from pathlib import Path

from PyQt6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

MAX_TEXT_BYTES = 8 * 1024 * 1024
MAX_TABLE_ROWS = 2_000
MAX_TABLE_COLUMNS = 200


def read_prefix(path: Path, limit: int) -> bytes:
    """Read at most *limit* bytes without materializing the whole file."""
    with path.open("rb") as stream:
        return stream.read(limit)


def read_text_safely(path: Path, limit: int = MAX_TEXT_BYTES) -> tuple[str, str, bool]:
    """Read text with encoding detection and a hard memory limit."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    truncated = size > limit
    raw = raw[:limit]

    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace"), "UTF-8 BOM", truncated
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace"), "UTF-16", truncated

    try:
        return raw.decode("utf-8"), "UTF-8", truncated
    except UnicodeDecodeError:
        try:
            from charset_normalizer import from_bytes

            best = from_bytes(raw).best()
            if best is not None:
                return str(best), best.encoding or "detected", truncated
        except ImportError:
            pass
    return raw.decode("latin-1", errors="replace"), "Latin-1 fallback", truncated


def escape_lines(text: str) -> str:
    return "<br>".join(html.escape(line) for line in text.splitlines())


def fill_table(
    table: QTableWidget,
    rows: Iterable[Sequence[object]],
    headers: Sequence[object] | None = None,
) -> tuple[int, int, bool]:
    """Fill a table safely, returning rows, columns and truncation state."""
    materialized: list[list[str]] = []
    truncated = False
    for row_index, row in enumerate(rows):
        if row_index >= MAX_TABLE_ROWS:
            truncated = True
            break
        materialized.append(["" if value is None else str(value) for value in row][:MAX_TABLE_COLUMNS])

    column_count = max((len(row) for row in materialized), default=len(headers or ()))
    column_count = min(column_count, MAX_TABLE_COLUMNS)
    table.clear()
    table.setRowCount(len(materialized))
    table.setColumnCount(column_count)
    if headers:
        table.setHorizontalHeaderLabels([str(value) for value in headers][:column_count])
    for row_index, row in enumerate(materialized):
        for column_index, value in enumerate(row[:column_count]):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.resizeColumnsToContents()
    return len(materialized), column_count, truncated
