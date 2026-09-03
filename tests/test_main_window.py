from pathlib import Path

from PyQt6.QtCore import Qt

from vibe_viewer.ui import main_window
from vibe_viewer.ui.main_window import LocalizedFileSystemModel, MainWindow, OpenLocationDialog


def test_main_window_opens_text_file(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "demo.txt"
    path.write_text("Vibe Viewer smoke test", encoding="utf-8")
    window = MainWindow(start_directory=tmp_path)
    qtbot.addWidget(window)
    window.open_file(path)
    assert window._active_viewer is not None
    assert window._active_viewer.name == "Text and source code"
    assert "demo.txt" in window.windowTitle()
    assert window.model.headerData(0, Qt.Orientation.Horizontal) == "Имя"


def test_navigation_starts_loading_selected_root(qtbot, tmp_path: Path) -> None:
    (tmp_path / "visible.txt").write_text("visible", encoding="utf-8")
    window = MainWindow(start_directory=tmp_path)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.model.rowCount(window.tree.rootIndex()) == 1)
    assert Path(window.model.rootPath()) == tmp_path.resolve()
    assert window.model.fileName(window.model.index(0, 0, window.tree.rootIndex())) == "visible.txt"


def test_file_tree_uses_stable_russian_columns(qtbot, tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    window = MainWindow(start_directory=tmp_path)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.model.index(str(folder)).isValid())
    name_index = window.model.index(str(folder))

    assert window.model.data(name_index.siblingAtColumn(1)) == "—"
    assert window.model.data(name_index.siblingAtColumn(2)) == "Папка"
    assert "." in window.model.data(name_index.siblingAtColumn(3))


def test_location_dialog_shows_and_accepts_files(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "available.txt"
    path.write_text("available", encoding="utf-8")
    dialog = OpenLocationDialog(tmp_path)
    qtbot.addWidget(dialog)
    qtbot.waitUntil(lambda: dialog.model.index(str(path)).isValid())
    index = dialog.model.index(str(path))
    assert index.flags() & Qt.ItemFlag.ItemIsEnabled
    dialog.tree.setCurrentIndex(index)
    dialog._accept_selected()
    assert dialog.selected_path == path


def test_inaccessible_folder_is_marked_and_disabled(qtbot, monkeypatch, tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    real_check = main_window.directory_access_error

    def fake_check(path: Path) -> str | None:
        if path == blocked:
            return f"Нет разрешения на чтение папки: {path}"
        return real_check(path)

    monkeypatch.setattr(main_window, "directory_access_error", fake_check)
    model = LocalizedFileSystemModel()
    model.setFilter(model.filter() | main_window.QDir.Filter.NoDotAndDotDot)
    model.setRootPath(str(tmp_path))
    qtbot.waitUntil(lambda: model.index(str(blocked)).isValid())

    index = model.index(str(blocked))
    assert "нет доступа" in model.data(index, Qt.ItemDataRole.DisplayRole)
    assert not model.flags(index) & Qt.ItemFlag.ItemIsEnabled
    assert not model.flags(index) & Qt.ItemFlag.ItemIsSelectable
    assert not model.hasChildren(index)


def test_access_cache_can_be_refreshed(qtbot, monkeypatch, tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    state = {"blocked": True}
    monkeypatch.setattr(
        main_window,
        "directory_access_error",
        lambda path: "Нет доступа" if path == folder and state["blocked"] else None,
    )
    model = LocalizedFileSystemModel()
    model.setRootPath(str(tmp_path))
    qtbot.waitUntil(lambda: model.index(str(folder)).isValid())
    index = model.index(str(folder))
    assert model.access_error(index) == "Нет доступа"

    state["blocked"] = False
    assert model.access_error(index) == "Нет доступа"
    model.clear_access_cache()
    assert model.access_error(index) is None
