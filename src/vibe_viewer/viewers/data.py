"""Database, array, columnar and scientific data viewer."""

from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTextBrowser,
    QVBoxLayout,
)

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import fill_table


class DataViewer(BaseViewer):
    name = "Databases and scientific data"
    category = "Databases and scientific data"
    priority = 65
    extensions = (
        ".sqlite", ".sqlite3", ".db", ".db3",
        ".npy", ".npz", ".parquet", ".feather", ".arrow",
        ".h5", ".hdf5", ".hdf", ".dcm", ".dicom",
        ".fits", ".fts", ".fit", ".nc", ".cdf", ".mat", ".sav",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path: Path | None = None
        self._sqlite_connection: sqlite3.Connection | None = None
        self.info = QLabel()
        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self._show_sqlite_table)
        self.table = QTableWidget()
        self.text = QTextBrowser()
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.text)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.selector)
        layout.addWidget(self.stack)

    def load_file(self, path: Path) -> None:
        self.unload()
        self._path = path
        suffix = path.suffix.lower()
        try:
            if suffix in {".sqlite", ".sqlite3", ".db", ".db3"}:
                self._load_sqlite(path)
            elif suffix in {".npy", ".npz"}:
                self._load_numpy(path)
            elif suffix in {".parquet", ".feather", ".arrow"}:
                self._load_columnar(path)
            elif suffix in {".h5", ".hdf5", ".hdf"}:
                self._load_hdf5(path)
            elif suffix in {".dcm", ".dicom"}:
                self._load_dicom(path)
            elif suffix in {".fits", ".fts", ".fit"}:
                self._load_fits(path)
            elif suffix in {".nc", ".cdf"}:
                self._load_netcdf(path)
            elif suffix == ".mat":
                self._load_mat(path)
            else:
                self._load_sav(path)
        except ViewerError:
            raise
        except Exception as exc:
            raise ViewerError(f"Не удалось открыть файл данных: {exc}") from exc

    def _load_sqlite(self, path: Path) -> None:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        self._sqlite_connection = sqlite3.connect(uri, uri=True)
        tables = [
            row[0]
            for row in self._sqlite_connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
            )
        ]
        self.selector.setVisible(True)
        self.selector.blockSignals(True)
        self.selector.addItems(tables)
        self.selector.blockSignals(False)
        self.stack.setCurrentWidget(self.table)
        if tables:
            self._show_sqlite_table(0)
        else:
            self.info.setText(f"{path.name} • SQLite • таблиц нет")

    def _show_sqlite_table(self, index: int) -> None:
        if self._sqlite_connection is None or index < 0:
            return
        table_name = self.selector.itemText(index)
        escaped_name = table_name.replace('"', '""')
        cursor = self._sqlite_connection.execute(f'SELECT * FROM "{escaped_name}" LIMIT 2001')
        headers = [column[0] for column in cursor.description or ()]
        row_count, column_count, truncated = fill_table(self.table, cursor, headers=headers)
        note = " • показаны первые 2000 строк" if truncated else ""
        self.info.setText(
            f"{self._path.name if self._path else 'SQLite'} • {table_name} • "
            f"{row_count}×{column_count}{note}"
        )

    def _load_numpy(self, path: Path) -> None:
        import numpy as np

        data = np.load(path, allow_pickle=False)
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.text)
        if isinstance(data, np.lib.npyio.NpzFile):
            lines = [f"NPZ archive: {path.name}"]
            for key in data.files:
                value = data[key]
                lines.append(f"\n{key}: shape={value.shape}, dtype={value.dtype}\n{value}")
            data.close()
            output = "\n".join(lines)
        else:
            output = f"shape={data.shape}\ndtype={data.dtype}\nsize={data.size}\n\n{data}"
        self.info.setText(f"{path.name} • NumPy")
        self.text.setHtml(f"<pre>{html.escape(output[:2_000_000])}</pre>")

    def _load_columnar(self, path: Path) -> None:
        import pandas as pd

        suffix = path.suffix.lower()
        if suffix == ".parquet":
            frame = pd.read_parquet(path)
        else:
            frame = pd.read_feather(path)
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.table)
        rows, columns = frame.shape
        shown_rows, shown_columns, truncated = fill_table(
            self.table,
            frame.itertuples(index=False, name=None),
            headers=list(frame.columns),
        )
        note = " • предпросмотр ограничен" if truncated else ""
        self.info.setText(
            f"{path.name} • {rows}×{columns} • показано {shown_rows}×{shown_columns}{note}"
        )

    def _load_hdf5(self, path: Path) -> None:
        import h5py

        lines = [f"HDF5: {path.name}"]
        with h5py.File(path, "r") as handle:
            def visitor(name, item):
                kind = "dataset" if isinstance(item, h5py.Dataset) else "group"
                details = f" shape={item.shape} dtype={item.dtype}" if kind == "dataset" else ""
                lines.append(f"/{name} [{kind}]{details}")

            handle.visititems(visitor)
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.text)
        self.info.setText(f"{path.name} • HDF5 • {len(lines) - 1} объектов")
        self.text.setHtml(f"<pre>{html.escape(chr(10).join(lines[:5000]))}</pre>")

    def _load_dicom(self, path: Path) -> None:
        import pydicom

        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=True)
        lines = []
        for element in dataset.iterall():
            value = str(element.value)
            lines.append(f"{element.tag} {element.name}: {value[:500]}")
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.text)
        self.info.setText(f"{path.name} • DICOM • {len(lines)} полей")
        self.text.setHtml(f"<pre>{html.escape(chr(10).join(lines))}</pre>")

    def _show_lines(self, title: str, lines: list[str]) -> None:
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.text)
        self.info.setText(title)
        self.text.setHtml(f"<pre>{html.escape(chr(10).join(lines)[:2_000_000])}</pre>")

    def _load_fits(self, path: Path) -> None:
        from astropy.io import fits

        lines = []
        with fits.open(path, memmap=True) as document:
            for index, unit in enumerate(document):
                shape = getattr(unit.data, "shape", None)
                lines.append(f"HDU {index}: {unit.name} • {type(unit).__name__} • shape={shape}")
                lines.extend(f"  {key} = {value}" for key, value in list(unit.header.items())[:200])
        self._show_lines(f"{path.name} • FITS • {len(document)} HDU", lines)

    def _load_netcdf(self, path: Path) -> None:
        import netCDF4

        lines = []
        with netCDF4.Dataset(path, "r") as dataset:
            lines.append("Размерности:")
            lines.extend(f"  {name}: {len(value)}" for name, value in dataset.dimensions.items())
            lines.append("\nПеременные:")
            lines.extend(f"  {name}: dtype={value.dtype}, shape={value.shape}" for name, value in dataset.variables.items())
            lines.append("\nАтрибуты:")
            lines.extend(f"  {name} = {dataset.getncattr(name)}" for name in dataset.ncattrs())
        self._show_lines(f"{path.name} • NetCDF", lines)

    def _load_mat(self, path: Path) -> None:
        from scipy.io import whosmat

        variables = whosmat(path)
        lines = [f"{name}: shape={shape}, type={kind}" for name, shape, kind in variables]
        self._show_lines(f"{path.name} • MATLAB • {len(lines)} переменных", lines)

    def _load_sav(self, path: Path) -> None:
        import pyreadstat

        frame, metadata = pyreadstat.read_sav(path, row_limit=2000)
        self.selector.setVisible(False)
        self.stack.setCurrentWidget(self.table)
        shown_rows, shown_columns, truncated = fill_table(
            self.table, frame.itertuples(index=False, name=None), headers=list(frame.columns)
        )
        note = " • показаны первые 2000 строк" if truncated else ""
        self.info.setText(f"{path.name} • SPSS • {shown_rows}×{shown_columns}{note} • {metadata.file_label or ''}")

    def unload(self) -> None:
        if self._sqlite_connection is not None:
            self._sqlite_connection.close()
        self._sqlite_connection = None
        self._path = None
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.blockSignals(False)
        self.table.clear()
        self.text.clear()
