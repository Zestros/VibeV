"""Delimited text and spreadsheet viewers."""

from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtWidgets import QComboBox, QLabel, QTableWidget, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import fill_table, read_text_safely


class DelimitedTableViewer(BaseViewer):
    name = "Delimited tables"
    category = "Tables"
    priority = 96
    extensions = (".csv", ".tsv", ".tab")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.table = QTableWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.table)

    def load_file(self, path: Path) -> None:
        text, encoding, text_truncated = read_text_safely(path, limit=16 * 1024 * 1024)
        try:
            sample = text[:8192]
            delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else None
            if delimiter:
                dialect = csv.excel_tab
            else:
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel
            rows = csv.reader(text.splitlines(), dialect=dialect)
            row_count, column_count, rows_truncated = fill_table(self.table, rows)
        except csv.Error as exc:
            raise ViewerError(f"Не удалось разобрать таблицу: {exc}") from exc
        notes = []
        if text_truncated:
            notes.append("файл обрезан до 16 МБ")
        if rows_truncated:
            notes.append("показаны первые 2000 строк")
        suffix = f" • {', '.join(notes)}" if notes else ""
        self.info.setText(
            f"{path.name} • {encoding} • {row_count}×{column_count}{suffix}"
        )


class SpreadsheetViewer(BaseViewer):
    name = "Spreadsheets"
    category = "Office and spreadsheets"
    priority = 100
    extensions = (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls", ".ods", ".ots")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path: Path | None = None
        self._book = None
        self.info = QLabel()
        self.sheet_selector = QComboBox()
        self.sheet_selector.currentIndexChanged.connect(self._show_current_sheet)
        self.table = QTableWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.sheet_selector)
        layout.addWidget(self.table)

    def load_file(self, path: Path) -> None:
        self.unload()
        self._path = path
        suffix = path.suffix.lower()
        try:
            if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
                import openpyxl

                self._book = openpyxl.load_workbook(
                    path, read_only=True, data_only=True, keep_links=False
                )
                names = list(self._book.sheetnames)
            elif suffix == ".xls":
                import xlrd

                self._book = xlrd.open_workbook(path, on_demand=True)
                names = self._book.sheet_names()
            else:
                from odf.opendocument import load

                self._book = load(str(path))
                from odf.table import Table

                names = [str(table.getAttribute("name") or f"Лист {index + 1}") for index, table in enumerate(self._book.getElementsByType(Table))]
        except Exception as exc:
            raise ViewerError(f"Не удалось открыть электронную таблицу: {exc}") from exc

        self.sheet_selector.blockSignals(True)
        self.sheet_selector.clear()
        self.sheet_selector.addItems(names)
        self.sheet_selector.blockSignals(False)
        if names:
            self._show_current_sheet(0)
        else:
            self.info.setText(f"{path.name} • нет листов")

    def _show_current_sheet(self, index: int) -> None:
        if self._book is None or index < 0 or self._path is None:
            return
        suffix = self._path.suffix.lower()
        try:
            if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
                sheet = self._book[self._book.sheetnames[index]]
                rows = sheet.iter_rows(values_only=True)
            elif suffix == ".xls":
                sheet = self._book.sheet_by_index(index)
                rows = (sheet.row_values(row) for row in range(sheet.nrows))
            else:
                rows = self._odf_rows(index)
            row_count, column_count, truncated = fill_table(self.table, rows)
            note = " • показаны первые 2000 строк" if truncated else ""
            self.info.setText(
                f"{self._path.name} • {row_count} строк • {column_count} столбцов{note}"
            )
        except Exception as exc:
            raise ViewerError(f"Не удалось показать лист: {exc}") from exc

    def _odf_rows(self, index: int):
        from odf import teletype
        from odf.table import Table, TableCell, TableRow

        table = self._book.getElementsByType(Table)[index]
        for row in table.getElementsByType(TableRow):
            values: list[str] = []
            repeat_rows = min(int(row.getAttribute("numberrowsrepeated") or 1), 100)
            for cell in row.getElementsByType(TableCell):
                repeat_columns = min(int(cell.getAttribute("numbercolumnsrepeated") or 1), 200)
                value = teletype.extractText(cell)
                values.extend([value] * repeat_columns)
            for _ in range(repeat_rows):
                yield values

    def unload(self) -> None:
        if self._book is not None and hasattr(self._book, "close"):
            self._book.close()
        self._book = None
        self._path = None
        self.sheet_selector.clear()
        self.table.clear()
