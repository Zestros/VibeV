"""Viewers for timed text, playlists and text-based geographic data."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QTableWidget, QTextBrowser, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import fill_table, read_text_safely


class SubtitleViewer(BaseViewer):
    """Show subtitle and synchronized-lyrics entries as a timeline."""

    name = "Subtitles and lyrics"
    category = "Subtitles and playlists"
    priority = 68
    extensions = (".srt", ".vtt", ".ass", ".ssa", ".sub", ".lrc")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.table = QTableWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.table)

    def load_file(self, path: Path) -> None:
        text, encoding, truncated = read_text_safely(path)
        suffix = path.suffix.lower()
        rows: list[tuple[str, str, str]] = []
        if suffix in {".ass", ".ssa"}:
            for line in text.splitlines():
                if line.lower().startswith("dialogue:"):
                    fields = line.split(",", 9)
                    if len(fields) == 10:
                        rows.append((fields[1], fields[2], fields[9].replace("\\N", " ")))
        elif suffix == ".lrc":
            for line in text.splitlines():
                match = re.match(r"\[(\d{1,3}:\d{2}(?:\.\d+)?)\](.*)", line)
                if match:
                    rows.append((match.group(1), "", match.group(2).strip()))
        else:
            pattern = re.compile(
                r"(?m)^(?:\d+\s*\n)?(\d\d?:\d\d:\d\d[,.]\d+)\s*-->\s*"
                r"(\d\d?:\d\d:\d\d[,.]\d+)[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
                re.DOTALL,
            )
            rows = [(a, b, " ".join(body.splitlines())) for a, b, body in pattern.findall(text)]
        if not rows:
            rows = [("", "", line) for line in text.splitlines() if line.strip()][:2000]
        count, _, limited = fill_table(self.table, rows, headers=("Начало", "Конец", "Текст"))
        note = " • предпросмотр ограничен" if truncated or limited else ""
        self.info.setText(f"{path.name} • {encoding} • {count} записей{note}")


class PlaylistViewer(BaseViewer):
    """Show local playlist, cue sheet and XSPF entries."""

    name = "Playlists"
    category = "Subtitles and playlists"
    priority = 67
    extensions = (".m3u", ".m3u8", ".pls", ".xspf", ".cue")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.table = QTableWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.table)

    def load_file(self, path: Path) -> None:
        text, encoding, _ = read_text_safely(path)
        suffix = path.suffix.lower()
        entries: list[tuple[str, str]] = []
        if suffix == ".xspf":
            root = ET.fromstring(text)
            for track in root.findall(".//{*}track"):
                title = track.findtext("{*}title", default="")
                entries.append((title, track.findtext("{*}location", default="")))
        elif suffix == ".pls":
            values = {}
            for line in text.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.lower()] = value
            for index in range(1, 10001):
                location = values.get(f"file{index}")
                if location is None:
                    continue
                entries.append((values.get(f"title{index}", ""), location))
        elif suffix == ".cue":
            current = ""
            for line in text.splitlines():
                line = line.strip()
                if line.upper().startswith("TITLE "):
                    current = line[6:].strip('"')
                elif line.upper().startswith("FILE "):
                    entries.append((current, line[5:].rsplit(" ", 1)[0].strip('"')))
        else:
            title = ""
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    title = line.partition(",")[2]
                elif line and not line.startswith("#"):
                    entries.append((title, line))
                    title = ""
        fill_table(self.table, entries, headers=("Название", "Ресурс"))
        self.info.setText(f"{path.name} • {encoding} • {len(entries)} записей")


class GeoDataViewer(BaseViewer):
    """Inspect common vector-geodata containers without online map services."""

    name = "Geographic data"
    category = "Geographic data"
    priority = 69
    extensions = (".gpx", ".kml", ".kmz", ".shp", ".gml", ".wkt")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.browser = QTextBrowser()
        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.browser)

    def load_file(self, path: Path) -> None:
        suffix = path.suffix.lower()
        try:
            if suffix == ".shp":
                import shapefile

                reader = shapefile.Reader(str(path))
                bounds = reader.bbox if reader.shapes() else []
                fields = [field[0] for field in reader.fields[1:]]
                body = f"Объектов: {len(reader)}\nПоля: {', '.join(fields)}\nГраницы: {bounds}"
                self.info.setText(f"{path.name} • Shapefile")
            elif suffix == ".kmz":
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    kml_name = next((name for name in names if name.lower().endswith(".kml")), None)
                    if not kml_name:
                        raise ViewerError("В KMZ нет KML-документа")
                    text = archive.read(kml_name).decode("utf-8", errors="replace")
                body = self._xml_summary(text)
                self.info.setText(f"{path.name} • KMZ • {len(names)} элементов")
            elif suffix in {".gpx", ".kml", ".gml"}:
                text, encoding, _ = read_text_safely(path)
                body = self._xml_summary(text)
                self.info.setText(f"{path.name} • {suffix[1:].upper()} • {encoding}")
            else:
                text, encoding, _ = read_text_safely(path)
                geometries = [line for line in text.splitlines() if line.strip()]
                body = f"Геометрий: {len(geometries)}\n\n" + "\n".join(geometries[:2000])
                self.info.setText(f"{path.name} • WKT • {encoding}")
        except ViewerError:
            raise
        except Exception as exc:
            raise ViewerError(f"Не удалось разобрать геоданные: {exc}") from exc
        self.browser.setHtml(f"<pre>{html.escape(body[:2_000_000])}</pre>")

    @staticmethod
    def _xml_summary(text: str) -> str:
        root = ET.fromstring(text)
        counts: dict[str, int] = {}
        coordinates: list[str] = []
        for node in root.iter():
            tag = node.tag.rsplit("}", 1)[-1]
            counts[tag] = counts.get(tag, 0) + 1
            if tag in {"trkpt", "wpt", "rtept"}:
                coordinates.append(f"{tag}: {node.attrib.get('lat')}, {node.attrib.get('lon')}")
            elif tag == "coordinates" and node.text:
                coordinates.extend(part.strip() for part in node.text.split()[:1000])
        summary = "Элементы:\n" + "\n".join(f"{key}: {value}" for key, value in sorted(counts.items()))
        if coordinates:
            summary += "\n\nКоординаты:\n" + "\n".join(coordinates[:2000])
        return summary
