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
from vibe_viewer.viewers.helpers import fill_table, read_prefix

MAX_ARCHIVE_MEMBERS = 5_000


class ArchiveViewer(BaseViewer):
    name = "Archives"
    category = "Archives and packages"
    priority = 70
    extensions = (
        ".zip", ".jar", ".war", ".apk", ".whl", ".cbz", ".cbr",
        ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tbz2",
        ".tar.xz", ".txz", ".gz", ".bz2", ".xz", ".7z",
        ".rar", ".cab", ".iso", ".cpio", ".ar", ".deb", ".rpm", ".zst", ".lz4",
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
            elif lower_name.endswith((".rar", ".cbr")):
                rows, total_size = self._rar_rows(path)
                archive_type = "RAR"
            elif lower_name.endswith(".iso"):
                rows, total_size = self._iso_rows(path)
                archive_type = "ISO"
            elif lower_name.endswith((".ar", ".deb")):
                rows, total_size = self._ar_rows(path)
                archive_type = "DEB" if lower_name.endswith(".deb") else "AR"
            elif lower_name.endswith(".rpm"):
                rows, total_size = self._rpm_rows(path)
                archive_type = "RPM"
            elif path.suffix.lower() in {".zst", ".lz4"}:
                rows, total_size = self._modern_stream_rows(path)
                archive_type = path.suffix[1:].upper()
            elif lower_name.endswith(".cpio"):
                rows, total_size = self._cpio_rows(path)
                archive_type = "CPIO"
            elif lower_name.endswith(".cab"):
                rows, total_size = self._cab_rows(path)
                archive_type = "CAB"
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

    @staticmethod
    def _rar_rows(path: Path):
        import rarfile

        rows, total = [], 0
        with rarfile.RarFile(path) as archive:
            for item in archive.infolist()[:MAX_ARCHIVE_MEMBERS]:
                total += item.file_size
                rows.append((item.filename, _human_size(item.file_size), _human_size(item.compress_size), str(item.date_time), "папка" if item.isdir() else "файл"))
        return rows, total

    @staticmethod
    def _iso_rows(path: Path):
        import pycdlib

        iso, rows, total = pycdlib.PyCdlib(), [], 0
        iso.open(str(path))
        try:
            for root, directories, files in iso.walk(iso_path="/"):
                for name in list(directories) + list(files):
                    rows.append((f"{root}/{name}", "—", "—", "—", "элемент"))
                    if len(rows) >= MAX_ARCHIVE_MEMBERS:
                        break
        finally:
            iso.close()
        return rows, total

    @staticmethod
    def _ar_rows(path: Path):
        rows, total = [], 0
        with path.open("rb") as stream:
            if stream.read(8) != b"!<arch>\n":
                raise ViewerError("Неверная сигнатура AR")
            while len(rows) < MAX_ARCHIVE_MEMBERS:
                header = stream.read(60)
                if not header:
                    break
                if len(header) != 60 or header[58:60] != b"`\n":
                    raise ViewerError("Повреждён заголовок AR")
                name = header[:16].decode("ascii", errors="replace").strip().rstrip("/")
                try:
                    size = int(header[48:58].decode("ascii").strip())
                except ValueError as exc:
                    raise ViewerError("Повреждён размер элемента AR") from exc
                rows.append((name, _human_size(size), "—", "—", "файл"))
                total += size
                stream.seek(size + size % 2, 1)
        return rows, total

    @staticmethod
    def _rpm_rows(path: Path):
        import rpmfile

        rows, total = [], 0
        with rpmfile.open(str(path)) as archive:
            for item in archive.getmembers()[:MAX_ARCHIVE_MEMBERS]:
                total += item.size
                rows.append((item.name, _human_size(item.size), "—", str(item.mtime), "файл"))
        return rows, total

    @staticmethod
    def _modern_stream_rows(path: Path):
        if path.suffix.lower() == ".zst":
            import zstandard

            with path.open("rb") as source, zstandard.ZstdDecompressor().stream_reader(source) as stream:
                data = stream.read(64 * 1024 * 1024 + 1)
        else:
            try:
                import lz4.frame
            except ImportError as exc:
                header = read_prefix(path, 32)
                if not header.startswith(b"\x04\x22\x4d\x18"):
                    raise ViewerError("Неверная сигнатура LZ4 Frame") from exc
                size = path.stat().st_size
                return [(path.stem, "—", _human_size(size), "—", "LZ4 Frame")], size
            with lz4.frame.open(path, "rb") as stream:
                data = stream.read(64 * 1024 * 1024 + 1)
        return [(path.stem, _human_size(len(data)), _human_size(path.stat().st_size), "—", "поток")], len(data)

    @staticmethod
    def _cpio_rows(path: Path):
        """List portable SVR4 'newc' CPIO members."""
        rows, total = [], 0
        with path.open("rb") as stream:
            while len(rows) < MAX_ARCHIVE_MEMBERS:
                header = stream.read(110)
                if not header:
                    break
                if len(header) != 110 or header[:6] not in {b"070701", b"070702"}:
                    if not rows:
                        raise ViewerError("Поддерживается CPIO в формате newc/crc")
                    break
                try:
                    mode = int(header[14:22], 16)
                    mtime = int(header[46:54], 16)
                    size = int(header[54:62], 16)
                    name_size = int(header[94:102], 16)
                except ValueError as exc:
                    raise ViewerError("Повреждён заголовок CPIO") from exc
                if name_size < 1 or name_size > 1024 * 1024:
                    raise ViewerError("Некорректная длина имени CPIO")
                raw_name = stream.read(name_size)
                if len(raw_name) != name_size:
                    raise ViewerError("Неожиданный конец имени CPIO")
                stream.seek((-(110 + name_size)) % 4, 1)
                name = raw_name[:-1].decode("utf-8", errors="replace")
                if name == "TRAILER!!!":
                    break
                rows.append((name, _human_size(size), "—", datetime.fromtimestamp(mtime).isoformat(sep=" ", timespec="minutes"), "папка" if mode & 0o170000 == 0o040000 else "файл"))
                total += size
                stream.seek(size + (-size) % 4, 1)
        return rows, total

    @staticmethod
    def _cab_rows(path: Path):
        """Show CAB header information without calling platform extractors."""
        import struct

        header = read_prefix(path, 36)
        if len(header) < 36 or not header.startswith(b"MSCF"):
            raise ViewerError("Неверная сигнатура Microsoft Cabinet")
        cabinet_size = struct.unpack_from("<I", header, 8)[0]
        file_offset = struct.unpack_from("<I", header, 16)[0]
        version_minor, version_major = header[24], header[25]
        folder_count, file_count = struct.unpack_from("<HH", header, 26)
        rows = [
            ("Версия", f"{version_major}.{version_minor}", "—", "—", "метаданные"),
            ("Папки", str(folder_count), "—", "—", "метаданные"),
            ("Файлы", str(file_count), "—", "—", "метаданные"),
            ("Смещение таблицы файлов", str(file_offset), "—", "—", "метаданные"),
        ]
        return rows, cabinet_size


def _human_size(value: int) -> str:
    size = float(value)
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if size < 1024 or unit == "ТБ":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"
