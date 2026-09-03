from pathlib import Path

from vibe_viewer.core.registry import ViewerRegistry
from vibe_viewer.viewers import register_default_viewers


def make_registry() -> ViewerRegistry:
    registry = ViewerRegistry()
    register_default_viewers(registry)
    return registry


def test_registry_has_broad_format_support() -> None:
    registry = make_registry()
    assert registry.supported_extension_count >= 100
    assert len(registry.support_by_category()) >= 10


def test_registry_selects_expected_handlers(tmp_path: Path) -> None:
    registry = make_registry()
    expectations = {
        "report.pdf": "Documents and e-books",
        "letter.docx": "Office documents",
        "table.xlsx": "Spreadsheets",
        "photo.heic": "Images",
        "movie.mp4": "Audio and video",
        "archive.tar.gz": "Archives",
        "database.sqlite": "Databases and scientific data",
        "unknown.bin": "Binary and unknown files",
    }
    for filename, viewer_name in expectations.items():
        path = tmp_path / filename
        path.write_bytes(b"\x00\x01test")
        assert registry.viewer_for(path).name == viewer_name


def test_compound_archive_suffix_is_detected(tmp_path: Path) -> None:
    registry = make_registry()
    path = tmp_path / "backup.tar.bz2"
    path.write_bytes(b"not a real archive")
    viewer = registry.viewer_for(path)
    assert viewer.name == "Archives"


def test_typescript_is_not_mistaken_for_mpeg_transport_stream(tmp_path: Path) -> None:
    registry = make_registry()
    path = tmp_path / "component.ts"
    path.write_text("export const answer: number = 42;", encoding="utf-8")
    assert registry.viewer_for(path).name == "Text and source code"
