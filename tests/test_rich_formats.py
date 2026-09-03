import subprocess
from pathlib import Path

import pymupdf
import pytest
from docx import Document
from openpyxl import Workbook
from PIL import Image

from vibe_viewer.viewers.base import ViewerError
from vibe_viewer.viewers.document import DocumentViewer
from vibe_viewer.viewers.image import ImageViewer
from vibe_viewer.viewers.office import OfficeDocumentViewer
from vibe_viewer.viewers.spreadsheet import SpreadsheetViewer


def test_png_image_is_rendered(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    Image.new("RGB", (32, 24), "navy").save(path)
    viewer = ImageViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer._pixmap is not None
    assert viewer._pixmap.size().width() == 32


def test_disguised_eps_never_starts_ghostscript(qtbot, monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "disguised.png"
    path.write_bytes(
        b"%!PS-Adobe-3.0 EPSF-3.0\n"
        b"%%BoundingBox: 0 0 10 10\n"
        b"newpath 0 0 moveto 10 10 lineto stroke\nshowpage\n%%EOF\n"
    )
    external_calls = []

    def forbid_external_process(*args, **kwargs):
        external_calls.append((args, kwargs))
        raise AssertionError("An external program was requested")

    monkeypatch.setattr(subprocess, "check_call", forbid_external_process)
    viewer = ImageViewer()
    qtbot.addWidget(viewer)
    with pytest.raises(ViewerError):
        viewer.load_file(path)
    assert external_calls == []


def test_pdf_page_is_rendered(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "document.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((40, 60), "PDF preview")
    document.save(path)
    document.close()
    viewer = DocumentViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.page_number.maximum() == 1
    assert viewer.page_label.pixmap() is not None
    viewer.unload()


def test_docx_content_is_rendered(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    document = Document()
    document.add_heading("DOCX preview", level=1)
    document.add_paragraph("Visible document content")
    document.save(path)
    viewer = OfficeDocumentViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert "Visible document content" in viewer.browser.toPlainText()


def test_xlsx_sheet_is_rendered(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "workbook.xlsx"
    workbook = Workbook()
    workbook.active.append(["name", "score"])
    workbook.active.append(["PDF", 10])
    workbook.save(path)
    viewer = SpreadsheetViewer()
    qtbot.addWidget(viewer)
    viewer.load_file(path)
    assert viewer.table.rowCount() == 2
    assert viewer.table.item(1, 0).text() == "PDF"
    viewer.unload()
