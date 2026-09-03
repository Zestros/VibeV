"""Font previewer."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QSlider, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError


class FontViewer(BaseViewer):
    name = "Fonts"
    category = "Fonts"
    priority = 60
    extensions = (".ttf", ".otf", ".ttc")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_id = -1
        self._family = ""
        self.info = QLabel()
        self.preview = QPlainTextEdit(
            "Съешь ещё этих мягких французских булок, да выпей чаю.\n"
            "The quick brown fox jumps over the lazy dog.\n"
            "0123456789 !? №%"
        )
        self.preview.setReadOnly(False)
        self.size = QSlider(Qt.Orientation.Horizontal)
        self.size.setRange(8, 96)
        self.size.setValue(30)
        self.size.valueChanged.connect(self._apply_font)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.size)
        layout.addWidget(self.preview)

    def load_file(self, path: Path) -> None:
        self.unload()
        self._font_id = QFontDatabase.addApplicationFont(str(path))
        if self._font_id < 0:
            raise ViewerError("Qt не смог загрузить шрифт")
        families = QFontDatabase.applicationFontFamilies(self._font_id)
        self._family = families[0] if families else path.stem
        self.info.setText(f"{path.name} • {', '.join(families) or 'семейство не указано'}")
        self._apply_font()

    def _apply_font(self) -> None:
        if self._family:
            self.preview.setFont(QFont(self._family, self.size.value()))

    def unload(self) -> None:
        if self._font_id >= 0:
            QFontDatabase.removeApplicationFont(self._font_id)
        self._font_id = -1
        self._family = ""

