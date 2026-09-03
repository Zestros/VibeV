"""Raster and vector image viewer."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QImageReader, QMovie, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from vibe_viewer.viewers.base import BaseViewer, ViewerError

PILLOW_FORMATS_BY_SUFFIX = {
    ".png": ("PNG",),
    ".jpg": ("JPEG",),
    ".jpeg": ("JPEG",),
    ".jpe": ("JPEG",),
    ".jfif": ("JPEG",),
    ".bmp": ("BMP",),
    ".dib": ("DIB", "BMP"),
    ".gif": ("GIF",),
    ".webp": ("WEBP",),
    ".tif": ("TIFF",),
    ".tiff": ("TIFF",),
    ".ico": ("ICO",),
    ".icns": ("ICNS",),
    ".ppm": ("PPM",),
    ".pgm": ("PPM",),
    ".pbm": ("PPM",),
    ".pnm": ("PPM",),
    ".pfm": ("PPM",),
    ".tga": ("TGA",),
    ".dds": ("DDS",),
    ".qoi": ("QOI",),
    ".avif": ("AVIF",),
    ".heic": ("HEIF",),
    ".heif": ("HEIF",),
    ".psd": ("PSD",),
    ".jp2": ("JPEG2000",),
    ".j2k": ("JPEG2000",),
    ".jpx": ("JPEG2000",),
    ".sgi": ("SGI",),
    ".pcx": ("PCX",),
    ".xpm": ("XPM",),
    ".xbm": ("XBM",),
    ".cur": ("CUR",),
    ".hdr": ("HDR",),
}


class ImageViewer(BaseViewer):
    name = "Images"
    category = "Images"
    priority = 90
    extensions = (
        ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".bmp", ".dib", ".gif",
        ".webp", ".tif", ".tiff", ".ico", ".icns", ".ppm", ".pgm", ".pbm",
        ".pnm", ".pfm", ".tga", ".dds", ".qoi", ".avif", ".heic", ".heif",
        ".psd", ".jp2", ".j2k", ".jpx", ".sgi", ".pcx", ".xpm", ".xbm",
        ".svg", ".dng", ".cr2", ".nef", ".arw", ".orf", ".rw2",
        ".hdr", ".exr", ".cur", ".ani",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._movie: QMovie | None = None
        self._zoom = 1.0
        self._fit = True

        self.info = QLabel("Выберите изображение")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(1, 1)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.image_label)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        zoom_out = QPushButton("−")
        zoom_in = QPushButton("+")
        fit = QPushButton("По размеру")
        actual = QPushButton("100%")
        zoom_out.clicked.connect(lambda: self._set_zoom(self._zoom / 1.25))
        zoom_in.clicked.connect(lambda: self._set_zoom(self._zoom * 1.25))
        fit.clicked.connect(self._fit_to_window)
        actual.clicked.connect(lambda: self._set_zoom(1.0))

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.info, 1)
        toolbar.addWidget(zoom_out)
        toolbar.addWidget(zoom_in)
        toolbar.addWidget(actual)
        toolbar.addWidget(fit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(toolbar)
        layout.addWidget(self.scroll)

    def load_file(self, path: Path) -> None:
        self.unload()
        suffix = path.suffix.lower()
        if suffix == ".gif":
            movie = QMovie(str(path))
            if movie.isValid():
                self._movie = movie
                self.image_label.setMovie(movie)
                movie.start()
                self.info.setText(f"{path.name} • animated GIF")
                return

        pixmap, format_name, mode = self._load_pixmap(path)
        if pixmap.isNull():
            raise ViewerError("Декодер не смог прочитать изображение")
        self._pixmap = pixmap
        self.info.setText(
            f"{path.name} • {format_name} • {pixmap.width()}×{pixmap.height()} px"
            + (f" • {mode}" if mode else "")
        )
        self._fit_to_window()

    def _load_pixmap(self, path: Path) -> tuple[QPixmap, str, str]:
        suffix = path.suffix.lower()
        if suffix == ".svg":
            pixmap = QPixmap(str(path))
            return pixmap, "SVG", "vector"

        if suffix == ".ani":
            data = path.read_bytes()
            offset = 0
            while True:
                offset = data.find(b"icon", offset)
                if offset < 0 or offset + 8 > len(data):
                    break
                size = int.from_bytes(data[offset + 4:offset + 8], "little")
                pixmap = QPixmap()
                if pixmap.loadFromData(data[offset + 8:offset + 8 + size]):
                    return pixmap, "ANI", "first frame"
                offset += 8 + size
            raise ViewerError("В ANI не найден декодируемый кадр курсора")

        if suffix in {".dng", ".cr2", ".nef", ".arw", ".orf", ".rw2"}:
            try:
                import rawpy
                from PIL import Image
                from PIL.ImageQt import ImageQt

                with rawpy.imread(str(path)) as raw:
                    rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False)
                pil_image = Image.fromarray(rgb)
                return QPixmap.fromImage(QImage(ImageQt(pil_image)).copy()), suffix[1:].upper(), "RAW"
            except Exception as exc:
                raise ViewerError(f"Не удалось проявить RAW: {exc}") from exc

        if suffix in {".hdr", ".exr"}:
            try:
                import imageio.v3 as iio
                import numpy as np
                from PIL import Image
                from PIL.ImageQt import ImageQt

                pixels = np.asarray(iio.imread(path), dtype=np.float32)
                pixels = np.nan_to_num(pixels)
                maximum = float(np.percentile(pixels, 99.5)) or 1.0
                pixels = np.clip(pixels / maximum, 0, 1) ** (1 / 2.2)
                pil_image = Image.fromarray((pixels * 255).astype("uint8")).convert("RGBA")
                return QPixmap.fromImage(QImage(ImageQt(pil_image)).copy()), suffix[1:].upper(), "tone mapped"
            except Exception as exc:
                raise ViewerError(f"Не удалось открыть HDR-изображение: {exc}") from exc

        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if not image.isNull():
            return QPixmap.fromImage(image), bytes(reader.format()).decode(errors="ignore").upper(), "Qt"

        try:
            from PIL import Image
            from PIL.ImageQt import ImageQt

            try:
                from pillow_heif import register_heif_opener

                register_heif_opener()
            except ImportError:
                pass

            if suffix == ".psd":
                try:
                    from psd_tools import PSDImage

                    pil_image = PSDImage.open(path).composite()
                except ImportError:
                    pil_image = Image.open(path, formats=("PSD",))
            else:
                allowed_formats = PILLOW_FORMATS_BY_SUFFIX.get(suffix)
                if not allowed_formats:
                    raise ViewerError("Формат изображения не разрешён")
                pil_image = Image.open(path, formats=allowed_formats)
            pil_image.seek(0)
            pil_image.load()
            format_name = pil_image.format or path.suffix.lstrip(".").upper()
            mode = pil_image.mode
            qt_image = QImage(ImageQt(pil_image.convert("RGBA"))).copy()
            return QPixmap.fromImage(qt_image), format_name, mode
        except Exception as exc:
            raise ViewerError(f"Не удалось открыть изображение: {exc}") from exc

    def _set_zoom(self, value: float) -> None:
        if self._pixmap is None:
            return
        self._fit = False
        self._zoom = max(0.05, min(value, 16.0))
        size = self._pixmap.size() * self._zoom
        self.image_label.setPixmap(
            self._pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.image_label.adjustSize()

    def _fit_to_window(self) -> None:
        if self._pixmap is None:
            return
        viewport = self.scroll.viewport().size()
        if viewport.width() < 2 or viewport.height() < 2:
            return
        available_width = max(viewport.width() - 8, 1)
        available_height = max(viewport.height() - 8, 1)
        self._zoom = min(
            available_width / self._pixmap.width(),
            available_height / self._pixmap.height(),
            1.0,
        )
        self._fit = True
        size = self._pixmap.size() * self._zoom
        self.image_label.setPixmap(
            self._pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.image_label.adjustSize()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fit:
            self._fit_to_window()

    def unload(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
        self._movie = None
        self._pixmap = None
        self.image_label.clear()
