"""Generate safe demo files without downloading anything."""

from __future__ import annotations

import csv
import gzip
import json
import sqlite3
import struct
import sys
import tarfile
import wave
import zipfile
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "samples" / "generated"


def write_text_samples() -> None:
    (OUTPUT / "hello.txt").write_text("Привет, Vibe Viewer!\nUniversal file preview.\n", encoding="utf-8")
    (OUTPUT / "example.md").write_text(
        "# Markdown\n\n- встроенный просмотр\n- таблицы\n- исходный код\n\n```python\nprint('hello')\n```\n",
        encoding="utf-8",
    )
    (OUTPUT / "data.json").write_text(
        json.dumps({"project": "Vibe Viewer", "formats": ["JSON", "PDF", "DOCX"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTPUT / "config.yaml").write_text("project: Vibe Viewer\nready: true\nscore: 100\n", encoding="utf-8")
    (OUTPUT / "page.html").write_text("<h1>HTML preview</h1><p>Работает внутри Qt.</p>", encoding="utf-8")
    with (OUTPUT / "table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Формат", "Категория", "Готов"])
        writer.writerows([["PDF", "Документы", "Да"], ["PNG", "Изображения", "Да"]])


def write_archives() -> None:
    with zipfile.ZipFile(OUTPUT / "archive.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("readme.txt", "Archive preview")
        archive.writestr("folder/data.json", '{"ok": true}')
    with tarfile.open(OUTPUT / "archive.tar.gz", "w:gz") as archive:
        archive.add(OUTPUT / "hello.txt", arcname="hello.txt")
    with gzip.open(OUTPUT / "single.txt.gz", "wb") as stream:
        stream.write(b"Compressed text stream")


def write_sqlite() -> None:
    connection = sqlite3.connect(OUTPUT / "demo.sqlite")
    connection.execute("CREATE TABLE formats (name TEXT, category TEXT, score INTEGER)")
    connection.executemany(
        "INSERT INTO formats VALUES (?, ?, ?)",
        [("PDF", "documents", 10), ("PNG", "images", 10), ("MP4", "video", 10)],
    )
    connection.commit()
    connection.close()


def write_email_and_contacts() -> None:
    message = EmailMessage()
    message["From"] = "demo@example.test"
    message["To"] = "team@example.test"
    message["Subject"] = "Vibe Viewer demo"
    message.set_content("Это письмо отображается внутри программы.")
    (OUTPUT / "message.eml").write_bytes(message.as_bytes())
    (OUTPUT / "contact.vcf").write_text(
        "BEGIN:VCARD\nVERSION:3.0\nFN:Demo User\nEMAIL:demo@example.test\nEND:VCARD\n",
        encoding="utf-8",
    )
    (OUTPUT / "event.ics").write_text(
        "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Demo\nDTSTART:20260101T120000Z\nEND:VEVENT\nEND:VCALENDAR\n",
        encoding="utf-8",
    )


def write_wav() -> None:
    sample_rate = 8_000
    duration_samples = sample_rate // 4
    with wave.open(str(OUTPUT / "silence.wav"), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack("<h", 0) * duration_samples)


def write_optional_samples() -> None:
    try:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (640, 360), "#dbeafe")
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, 600, 320), outline="#2563eb", width=6)
        draw.text((80, 155), "Vibe Viewer image", fill="#172033")
        image.save(OUTPUT / "image.png")
        image.save(OUTPUT / "image.webp")
    except ImportError:
        pass

    try:
        import pymupdf

        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 100), "Vibe Viewer PDF demo", fontsize=24)
        document.save(OUTPUT / "document.pdf")
        document.close()
    except ImportError:
        pass

    try:
        from docx import Document

        document = Document()
        document.add_heading("Vibe Viewer DOCX", 0)
        document.add_paragraph("Документ открыт без Microsoft Word и LibreOffice.")
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Формат"
        table.cell(0, 1).text = "Статус"
        table.cell(1, 0).text = "DOCX"
        table.cell(1, 1).text = "Работает"
        document.save(OUTPUT / "document.docx")
    except ImportError:
        pass

    try:
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Форматы"
        sheet.append(["Формат", "Категория", "Готов"])
        sheet.append(["XLSX", "Таблицы", True])
        book.save(OUTPUT / "workbook.xlsx")
    except ImportError:
        pass

    try:
        from pptx import Presentation

        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = "Vibe Viewer PPTX"
        slide.placeholders[1].text = "Предпросмотр текста и изображений слайда"
        presentation.save(OUTPUT / "slides.pptx")
    except ImportError:
        pass

    try:
        import numpy as np

        np.save(OUTPUT / "array.npy", np.arange(24).reshape(4, 6))
        np.savez(OUTPUT / "arrays.npz", first=np.arange(5), second=np.eye(3))
    except ImportError:
        pass


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_text_samples()
    write_archives()
    write_sqlite()
    write_email_and_contacts()
    write_wav()
    write_optional_samples()
    print(f"Generated demo files in {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

