"""Page-based document and e-book viewer powered by PyMuPDF."""

from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import read_prefix, read_text_safely


class DocumentViewer(BaseViewer):
    name = "Documents and e-books"
    category = "Documents and e-books"
    priority = 85
    extensions = (
        ".pdf", ".xps", ".oxps", ".epub", ".mobi", ".fb2", ".cbz", ".ps",
        ".azw", ".azw3", ".djvu", ".djv",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document = None
        self._path: Path | None = None
        self._zoom = 1.25

        self.info = QLabel("Выберите документ")
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.page_label)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        previous_button = QPushButton("◀")
        next_button = QPushButton("▶")
        zoom_out = QPushButton("−")
        zoom_in = QPushButton("+")
        self.page_number = QSpinBox()
        self.page_number.setMinimum(1)
        self.page_number.valueChanged.connect(self._render_page)
        previous_button.clicked.connect(lambda: self.page_number.setValue(self.page_number.value() - 1))
        next_button.clicked.connect(lambda: self.page_number.setValue(self.page_number.value() + 1))
        zoom_out.clicked.connect(lambda: self._change_zoom(0.8))
        zoom_in.clicked.connect(lambda: self._change_zoom(1.25))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск на странице")
        find_button = QPushButton("Найти")
        find_button.clicked.connect(self._find_on_page)

        controls = QHBoxLayout()
        controls.addWidget(self.info, 1)
        controls.addWidget(previous_button)
        controls.addWidget(self.page_number)
        controls.addWidget(next_button)
        controls.addWidget(zoom_out)
        controls.addWidget(zoom_in)
        controls.addWidget(self.search)
        controls.addWidget(find_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(controls)
        layout.addWidget(self.scroll)

    def load_file(self, path: Path) -> None:
        self.unload()
        if path.suffix.lower() in {".azw", ".azw3", ".djvu", ".djv"}:
            self._load_book_summary(path)
            return
        if path.suffix.lower() == ".ps":
            self._load_postscript_summary(path)
            return
        try:
            import pymupdf

            self._document = pymupdf.open(path)
        except Exception as exc:
            raise ViewerError(f"Не удалось открыть документ: {exc}") from exc
        if self._document.page_count < 1:
            raise ViewerError("В документе нет страниц")
        self._path = path
        self.page_number.blockSignals(True)
        self.page_number.setRange(1, self._document.page_count)
        self.page_number.setValue(1)
        self.page_number.blockSignals(False)
        self.info.setText(f"{path.name} • {self._document.page_count} стр.")
        self._render_page(1)

    def _load_book_summary(self, path: Path) -> None:
        """Show safe metadata and embedded text for formats MuPDF cannot render."""
        data = read_prefix(path, 8 * 1024 * 1024)
        signature = data[:32].hex(" ")
        strings: list[str] = []
        current = bytearray()
        for byte in data:
            if 32 <= byte < 127:
                current.append(byte)
            else:
                if len(current) >= 5:
                    strings.append(current.decode("ascii"))
                current.clear()
            if len(strings) >= 5000:
                break
        suffix = path.suffix[1:].upper()
        self._path = path
        self.page_number.setRange(1, 1)
        self.info.setText(f"{path.name} • {suffix} • {path.stat().st_size} байт")
        self.page_label.setText(
            f"{suffix}: структурный предпросмотр\n\nСигнатура:\n{signature}\n\n"
            + "\n".join(strings[:500])
        )
        self.page_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def _load_postscript_summary(self, path: Path) -> None:
        """Show PostScript document metadata and printable strings without Ghostscript."""
        text, encoding, truncated = read_text_safely(path)
        if not text.lstrip().startswith("%!PS"):
            raise ViewerError("Неверная сигнатура PostScript")

        def dsc_value(name: str) -> str | None:
            match = re.search(rf"(?m)^%%{re.escape(name)}:\s*(.+)$", text)
            return match.group(1).strip() if match else None

        declared_pages = dsc_value("Pages")
        page_markers = len(re.findall(r"(?m)^%%Page:", text))
        try:
            page_count = int((declared_pages or "").split()[0])
        except (ValueError, IndexError):
            page_count = page_markers

        strings = []
        for value in re.findall(r"(?<!\\)\((.*?)(?<!\\)\)", text):
            cleaned = (
                value.replace(r"\(", "(")
                .replace(r"\)", ")")
                .replace(r"\n", "\n")
                .replace(r"\r", "\r")
                .replace(r"\t", "\t")
                .replace(r"\\", "\\")
            )
            if cleaned.strip():
                strings.append(cleaned)
            if len(strings) >= 500:
                break

        details = ["PostScript: структурный предпросмотр"]
        for label, field in (
            ("Заголовок", "Title"),
            ("Автор", "For"),
            ("Создатель", "Creator"),
            ("BoundingBox", "BoundingBox"),
        ):
            value = dsc_value(field)
            if value:
                details.append(f"{label}: {value}")
        details.append(f"Страниц: {page_count or 'не указано'}")
        if strings:
            details.append("\nТекстовые строки:\n" + "\n".join(strings))
        if truncated:
            details.append("\nПредпросмотр ограничен первыми 8 МБ.")

        self._path = path
        self.page_number.setRange(1, 1)
        self.info.setText(
            f"{path.name} • PostScript • {encoding} • "
            f"{page_count or 'неизвестно'} стр. • структурный просмотр"
        )
        self.page_label.setText("\n".join(details))
        self.page_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def _render_page(self, page_number: int | None = None) -> None:
        if self._document is None:
            return
        number = (page_number or self.page_number.value()) - 1
        try:
            import pymupdf

            page = self._document.load_page(number)
            matrix = pymupdf.Matrix(self._zoom, self._zoom)
            pixmap = page.get_pixmap(matrix=matrix, alpha=True)
            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format.Format_RGBA8888,
            ).copy()
            self.page_label.setPixmap(QPixmap.fromImage(image))
            self.page_label.adjustSize()
            self.info.setText(
                f"{self._path.name if self._path else 'Документ'} • "
                f"страница {number + 1}/{self._document.page_count} • {int(self._zoom * 100)}%"
            )
        except Exception as exc:
            raise ViewerError(f"Не удалось отрисовать страницу: {exc}") from exc

    def _change_zoom(self, factor: float) -> None:
        self._zoom = max(0.4, min(self._zoom * factor, 4.0))
        self._render_page()

    def _find_on_page(self) -> None:
        if self._document is None or not self.search.text().strip():
            return
        page = self._document.load_page(self.page_number.value() - 1)
        count = len(page.search_for(self.search.text().strip()))
        self.info.setText(f"Найдено на странице: {count}")

    def unload(self) -> None:
        if self._document is not None:
            self._document.close()
        self._document = None
        self._path = None
        self.page_label.clear()
