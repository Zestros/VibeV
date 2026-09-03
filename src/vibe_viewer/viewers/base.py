"""Common viewer API."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QWidget


class ViewerError(RuntimeError):
    """Expected error while decoding or rendering a file."""


class BaseViewer(QWidget):
    """Base class for all file viewers.

    Subclasses only need to declare metadata and implement ``load_file``.
    """

    name = "Viewer"
    category = "Other"
    extensions: tuple[str, ...] = ()
    priority = 0
    fallback = False

    @classmethod
    def supports_path(cls, path: Path) -> bool:
        lower_name = path.name.lower()
        return any(lower_name.endswith(extension) for extension in cls.extensions)

    def load_file(self, path: Path) -> None:
        raise NotImplementedError

    def unload(self) -> None:
        """Release file handles or media resources before switching viewers."""

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self.unload()
        super().closeEvent(event)

