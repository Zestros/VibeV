"""Safe structural previews for models, executables, captures and packages."""

from __future__ import annotations

import html
import json
import struct
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError


def _safe_strings(path: Path, limit: int = 8 * 1024 * 1024) -> list[str]:
    """Extract printable strings without executing or importing the file."""
    data = path.read_bytes()[:limit]
    result: list[str] = []
    current = bytearray()
    for byte in data:
        if 32 <= byte < 127:
            current.append(byte)
        else:
            if len(current) >= 5:
                result.append(current.decode("ascii"))
            current.clear()
    if len(current) >= 5:
        result.append(current.decode("ascii"))
    return result[:5000]


class TechnicalTextViewer(BaseViewer):
    """Shared compact text surface for technical formats."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.browser = QTextBrowser()
        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.browser)

    def show_text(self, title: str, text: str) -> None:
        self.info.setText(title)
        self.browser.setHtml(f"<pre>{html.escape(text[:2_000_000])}</pre>")


class ModelViewer(TechnicalTextViewer):
    name = "3D models"
    category = "3D models"
    priority = 66
    extensions = (".stl", ".obj", ".ply", ".off", ".gltf", ".glb", ".3mf")

    def load_file(self, path: Path) -> None:
        try:
            import trimesh

        except ImportError:
            self._load_without_trimesh(path)
            return
        try:
            loaded = trimesh.load(path, force="scene", process=False)
            geometries = list(loaded.geometry.values())
        except Exception:
            self._load_without_trimesh(path)
            return
        lines = [f"Сцена: {path.name}", f"Объектов: {len(geometries)}"]
        for index, geometry in enumerate(geometries[:1000], 1):
            lines.append(
                f"{index}. {type(geometry).__name__}: "
                f"vertices={len(getattr(geometry, 'vertices', []))}, "
                f"faces={len(getattr(geometry, 'faces', []))}, "
                f"bounds={getattr(geometry, 'bounds', None)}"
            )
        self.show_text(f"{path.name} • 3D • {len(geometries)} объектов", "\n".join(lines))

    def _load_without_trimesh(self, path: Path) -> None:
        """Provide a useful preview using only the standard library."""
        suffix = path.suffix.lower()
        try:
            if suffix == ".obj":
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                vertices = sum(line.startswith("v ") for line in lines)
                normals = sum(line.startswith("vn ") for line in lines)
                textures = sum(line.startswith("vt ") for line in lines)
                faces = sum(line.startswith("f ") for line in lines)
                details = [f"Вершин: {vertices}", f"Нормалей: {normals}", f"Текстурных координат: {textures}", f"Граней: {faces}"]
            elif suffix == ".off":
                lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.startswith("#")]
                counts = lines[1].split() if len(lines) > 1 else []
                details = [f"Вершин: {counts[0]}", f"Граней: {counts[1]}", f"Рёбер: {counts[2]}"] if len(counts) >= 3 else ["Заголовок OFF повреждён"]
            elif suffix == ".ply":
                header = path.read_bytes()[:1024 * 1024].split(b"end_header", 1)[0].decode("ascii", errors="replace")
                details = [line for line in header.splitlines() if line.startswith(("format ", "element ", "property ", "comment "))]
            elif suffix == ".stl":
                data = path.read_bytes()
                if len(data) >= 84 and len(data) == 84 + int.from_bytes(data[80:84], "little") * 50:
                    details = ["Формат: binary STL", f"Треугольников: {int.from_bytes(data[80:84], 'little')}"]
                else:
                    text = data.decode("ascii", errors="replace")
                    details = ["Формат: ASCII STL", f"Треугольников: {text.lower().count('facet normal')}"]
            elif suffix == ".gltf":
                document = json.loads(path.read_text(encoding="utf-8"))
                details = self._gltf_details(document)
            elif suffix == ".glb":
                data = path.read_bytes()
                if len(data) < 20 or data[:4] != b"glTF":
                    raise ViewerError("Неверная сигнатура GLB")
                version, total_size = struct.unpack_from("<II", data, 4)
                json_size, chunk_type = struct.unpack_from("<II", data, 12)
                details = [f"Версия glTF: {version}", f"Размер: {total_size} байт"]
                if chunk_type == 0x4E4F534A:
                    document = json.loads(data[20:20 + json_size].rstrip(b" \0").decode("utf-8"))
                    details.extend(self._gltf_details(document))
            elif suffix == ".3mf":
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    models = [name for name in names if name.lower().endswith(".model")]
                    details = [f"Элементов контейнера: {len(names)}", f"3D-моделей: {len(models)}"] + models[:100]
            else:
                raise ViewerError("Неизвестный формат 3D-модели")
        except ViewerError:
            raise
        except Exception as exc:
            raise ViewerError(f"Не удалось разобрать 3D-модель: {exc}") from exc
        self.show_text(f"{path.name} • 3D • встроенный просмотр", "\n".join(details))

    @staticmethod
    def _gltf_details(document: dict) -> list[str]:
        asset = document.get("asset", {})
        return [
            f"Версия glTF: {asset.get('version', '—')}",
            f"Сцен: {len(document.get('scenes', []))}",
            f"Узлов: {len(document.get('nodes', []))}",
            f"Мешей: {len(document.get('meshes', []))}",
            f"Материалов: {len(document.get('materials', []))}",
            f"Анимаций: {len(document.get('animations', []))}",
        ]


class BinaryStructureViewer(TechnicalTextViewer):
    name = "Executable and binary structures"
    category = "Executable and binary structures"
    priority = 64
    extensions = (".exe", ".dll", ".sys", ".elf", ".so", ".o", ".class", ".wasm")

    def load_file(self, path: Path) -> None:
        suffix = path.suffix.lower()
        data = path.read_bytes()[:64]
        lines = [f"Размер: {path.stat().st_size} байт", f"Заголовок: {data.hex(' ')}"]
        try:
            if suffix in {".exe", ".dll", ".sys"}:
                import pefile

                pe = pefile.PE(str(path), fast_load=True)
                lines.extend(("Формат: PE", f"Машина: 0x{pe.FILE_HEADER.Machine:04x}", f"Секций: {pe.FILE_HEADER.NumberOfSections}"))
                lines.extend(f"Секция: {section.Name.rstrip(bytes([0])).decode(errors='replace')}" for section in pe.sections)
                pe.close()
            elif suffix in {".elf", ".so", ".o"} or data.startswith(b"\x7fELF"):
                from elftools.elf.elffile import ELFFile

                with path.open("rb") as stream:
                    elf = ELFFile(stream)
                    lines.extend((f"Формат: ELF {elf.elfclass}-bit", f"Архитектура: {elf.get_machine_arch()}", f"Секций: {elf.num_sections()}"))
                    lines.extend(f"Секция: {section.name} ({section.data_size} байт)" for section in elf.iter_sections())
            elif suffix == ".class" and data.startswith(b"\xca\xfe\xba\xbe"):
                minor, major = struct.unpack(">HH", data[4:8])
                lines.extend(("Формат: Java class", f"Версия class-файла: {major}.{minor}"))
            elif suffix == ".wasm" and data.startswith(b"\0asm"):
                lines.extend(("Формат: WebAssembly", f"Версия: {int.from_bytes(data[4:8], 'little')}"))
        except Exception as exc:
            lines.append(f"Подробный разбор недоступен: {exc}")
        strings = _safe_strings(path)
        if strings:
            lines.append("\nСтроки:\n" + "\n".join(strings))
        self.show_text(f"{path.name} • безопасный структурный просмотр", "\n".join(lines))


class CaptureViewer(TechnicalTextViewer):
    name = "Network captures"
    category = "Network data"
    priority = 63
    extensions = (".pcap", ".pcapng")

    def load_file(self, path: Path) -> None:
        import dpkt

        lines: list[str] = []
        try:
            with path.open("rb") as stream:
                try:
                    reader = dpkt.pcap.Reader(stream)
                    kind = "PCAP"
                except (ValueError, dpkt.dpkt.NeedData):
                    stream.seek(0)
                    reader = dpkt.pcapng.Reader(stream)
                    kind = "PCAPNG"
                for index, (timestamp, packet) in enumerate(reader):
                    if index >= 5000:
                        break
                    lines.append(f"{index + 1:5}  {timestamp:.6f}  {len(packet):6} bytes  {packet[:32].hex(' ')}")
        except Exception as exc:
            raise ViewerError(f"Не удалось разобрать сетевой дамп: {exc}") from exc
        self.show_text(f"{path.name} • {kind} • {len(lines)} пакетов", "#      timestamp       size    first bytes\n" + "\n".join(lines))


class PackageMetadataViewer(TechnicalTextViewer):
    name = "Package metadata"
    category = "Packages and metadata"
    priority = 82
    extensions = (".torrent",)

    def load_file(self, path: Path) -> None:
        try:
            import bencodepy

            value = bencodepy.decode(path.read_bytes())

            def normalize(item):
                if isinstance(item, bytes):
                    return item.decode("utf-8", errors="replace")
                if isinstance(item, dict):
                    return {normalize(k): normalize(v) for k, v in item.items()}
                if isinstance(item, list):
                    return [normalize(v) for v in item]
                return item

            output = json.dumps(normalize(value), ensure_ascii=False, indent=2)
        except Exception as exc:
            raise ViewerError(f"Не удалось разобрать torrent: {exc}") from exc
        self.show_text(f"{path.name} • BitTorrent metadata", output)
