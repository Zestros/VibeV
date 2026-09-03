"""Safe archive index viewer. It never launches an external extractor."""

from __future__ import annotations

import bz2
import gzip
import lzma
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QTableWidget, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import fill_table

MAX_ARCHIVE_MEMBERS = 5_000


class ArchiveViewer(BaseViewer):
    name = "Archives"
    category = "Archives and packages"
    priority = 70
    extensions = (
        ".zip", ".jar", ".war", ".apk", ".whl", ".cbz",
        ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tbz2",
        ".tar.xz", ".txz", ".gz", ".bz2", ".xz", ".7z",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.table = QTableWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.table)

    def load_file(self, path: Path) -> None:
        lower_name = path.name.lower()
        try:
            if zipfile.is_zipfile(path):
                rows, total_size = self._zip_rows(path)
                archive_type = "ZIP"
            elif tarfile.is_tarfile(path):
                rows, total_size = self._tar_rows(path)
                archive_type = "TAR"
            elif lower_name.endswith(".7z"):
                rows, total_size = self._seven_zip_rows(path)
                archive_type = "7Z"
            elif path.suffix.lower() in {".gz", ".bz2", ".xz"}:
                rows, total_size = self._single_stream_rows(path)
                archive_type = path.suffix[1:].upper()
            else:
                raise ViewerError("Неизвестная структура архива")
        except ViewerError:
            raise
        except Exception as exc:
            raise ViewerError(f"Не удалось прочитать архив: {exc}") from exc
        member_count, _, truncated = fill_table(
            self.table,
            rows,
            headers=("Имя", "Размер", "Сжатый размер", "Дата", "Тип"),
        )
        note = f" • показаны первые {MAX_ARCHIVE_MEMBERS}" if truncated else ""
        self.info.setText(
            f"{path.name} • {archive_type} • {member_count} элементов • "
            f"{_human_size(total_size)} распаковано{note}"
        )

    @staticmethod
    def _zip_rows(path: Path) -> tuple[list[tuple[object, ...]], int]:
        rows = []
        total = 0
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist()[:MAX_ARCHIVE_MEMBERS]:
                total += item.file_size
                rows.append(
                    (
                        item.filename,
                        _human_size(item.file_size),
                        _human_size(item.compress_size),
                        datetime(*item.date_time).strftime("%Y-%m-%d %H:%M"),
                        "папка" if item.is_dir() else "файл",
                    )
                )
        return rows, total

    @staticmethod
    def _tar_rows(path: Path) -> tuple[list[tuple[object, ...]], int]:
        rows = []
        total = 0
        with tarfile.open(path, "r:*") as archive:
            for index, item in enumerate(archive):
                if index >= MAX_ARCHIVE_MEMBERS:
                    break
                total += item.size
                rows.append(
                    (
                        item.name,
                        _human_size(item.size),
                        "—",
                        datetime.fromtimestamp(item.mtime).isoformat(sep=" ", timespec="minutes"),
                        "папка" if item.isdir() else "файл",
                    )
                )
        return rows, total

    @staticmethod
    def _seven_zip_rows(path: Path) -> tuple[list[tuple[object, ...]], int]:
        import py7zr

        rows = []
        total = 0
        with py7zr.SevenZipFile(path, "r") as archive:
            for item in archive.list()[:MAX_ARCHIVE_MEMBERS]:
                size = int(getattr(item, "uncompressed", 0) or 0)
                compressed = int(getattr(item, "compressed", 0) or 0)
                total += size
                creation = getattr(item, "creationtime", None)
                rows.append(
                    (
                        item.filename,
                        _human_size(size),
                        _human_size(compressed),
                        str(creation or "—"),
                        "папка" if getattr(item, "is_directory", False) else "файл",
                    )
                )
        return rows, total

    @staticmethod
    def _single_stream_rows(path: Path) -> tuple[list[tuple[object, ...]], int]:
        opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}[path.suffix.lower()]
        limit = 64 * 1024 * 1024
        total = 0
        with opener(path, "rb") as stream:
            while total <= limit:
                chunk = stream.read(min(1024 * 1024, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
        display_size = f"> {_human_size(limit)}" if total > limit else _human_size(total)
        output_name = path.stem
        return [(output_name, display_size, _human_size(path.stat().st_size), "—", "поток")], total


def _human_size(value: int) -> str:
    size = float(value)
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if size < 1024 or unit == "ТБ":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"
