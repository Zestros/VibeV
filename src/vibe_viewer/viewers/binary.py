"""Universal metadata and hexadecimal fallback viewer."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout

from vibe_viewer.core.detection import describe_file
from vibe_viewer.viewers.base import BaseViewer

MAX_HEX_BYTES = 256 * 1024


class BinaryViewer(BaseViewer):
    name = "Binary and unknown files"
    category = "Fallback"
    priority = -100
    fallback = True
    extensions = ()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.hex = QPlainTextEdit()
        self.hex.setReadOnly(True)
        self.hex.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.hex)

    @classmethod
    def supports_path(cls, path: Path) -> bool:
        return path.is_file()

    def load_file(self, path: Path) -> None:
        size = path.stat().st_size
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            data = stream.read(MAX_HEX_BYTES)
            hasher.update(data)
        shown_hash = hasher.hexdigest() if size <= MAX_HEX_BYTES else f"{hasher.hexdigest()} (первых 256 КБ)"
        self.info.setText(
            f"{path.name} • {describe_file(path)} • {size:,} байт • SHA-256 {shown_hash}"
        )
        lines = []
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset + 16]
            hexadecimal = " ".join(f"{byte:02x}" for byte in chunk)
            printable = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)
            lines.append(f"{offset:08x}  {hexadecimal:<47}  |{printable}|")
        if size > len(data):
            lines.append(f"\n… показаны первые {MAX_HEX_BYTES:,} байт")
        self.hex.setPlainText("\n".join(lines))

