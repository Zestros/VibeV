"""Viewer plug-in registry."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe_viewer.viewers.base import BaseViewer


class ViewerRegistry:
    """Maps files to viewer widget classes.

    Adding a new format does not require editing the main window: implement a
    ``BaseViewer`` subclass and register it in ``register_default_viewers``.
    """

    def __init__(self) -> None:
        self._viewers: list[type[BaseViewer]] = []

    @property
    def viewers(self) -> tuple[type[BaseViewer], ...]:
        return tuple(self._viewers)

    def register(self, viewer_class: type[BaseViewer]) -> None:
        if viewer_class not in self._viewers:
            self._viewers.append(viewer_class)
            self._viewers.sort(key=lambda item: item.priority, reverse=True)

    def viewer_for(self, path: str | Path) -> type[BaseViewer]:
        candidate = Path(path)
        for viewer_class in self._viewers:
            if viewer_class.fallback:
                continue
            try:
                if viewer_class.supports_path(candidate):
                    return viewer_class
            except (OSError, ValueError):
                continue
        for viewer_class in self._viewers:
            if viewer_class.fallback:
                return viewer_class
        raise LookupError("No fallback viewer is registered")

    def support_by_category(self) -> dict[str, list[str]]:
        result: dict[str, set[str]] = defaultdict(set)
        for viewer_class in self._viewers:
            if not viewer_class.fallback:
                result[viewer_class.category].update(viewer_class.extensions)
        return {
            category: sorted(extensions)
            for category, extensions in sorted(result.items())
        }

    @property
    def supported_extension_count(self) -> int:
        return len(
            {
                extension
                for viewer_class in self._viewers
                if not viewer_class.fallback
                for extension in viewer_class.extensions
            }
        )

