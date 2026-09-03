from __future__ import annotations

import csv
import json
import sqlite3
import zipfile
from pathlib import Path

from vibe_viewer.viewers.archive import ArchiveViewer
from vibe_viewer.viewers.data import DataViewer
from vibe_viewer.viewers.spreadsheet import DelimitedTableViewer
from vibe_viewer.viewers.text import StructuredTextViewer, TextViewer


def test_text_viewer_reads_utf8(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "hello.txt"
    path.write_text("Привет, мир!", encoding="utf-8")
    viewer = TextViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert "Привет" in viewer.browser.toPlainText()
    assert "UTF-8" in viewer.info.text()


def test_json_viewer_pretty_prints(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"ok": True, "items": [1, 2]}), encoding="utf-8")
    viewer = StructuredTextViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    rendered = viewer.browser.toPlainText()
    assert '"ok": true' in rendered
    assert '"items"' in rendered


def test_csv_viewer_builds_table(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerows([["name", "score"], ["PDF", 10], ["PNG", 9]])
    viewer = DelimitedTableViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.table.rowCount() == 3
    assert viewer.table.columnCount() == 2


def test_single_column_csv_uses_safe_fallback_dialect(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "single.csv"
    path.write_text("value\none\ntwo\n", encoding="utf-8")
    viewer = DelimitedTableViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.table.rowCount() == 3
    assert viewer.table.columnCount() == 1


def test_archive_viewer_lists_members(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "example.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "hello")
        archive.writestr("folder/data.json", "{}")
    viewer = ArchiveViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.table.rowCount() == 2
    assert viewer.table.item(0, 0).text() == "hello.txt"


def test_sqlite_viewer_uses_read_only_database(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "demo.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE demo (name TEXT, value INTEGER)")
    connection.execute("INSERT INTO demo VALUES ('answer', 42)")
    connection.commit()
    connection.close()

    viewer = DataViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.selector.itemText(0) == "demo"
    assert viewer.table.item(0, 0).text() == "answer"
    viewer.unload()
