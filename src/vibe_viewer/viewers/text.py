"""Plain, highlighted and structured text viewers."""

from __future__ import annotations

import configparser
import html
import json
import pprint
import tomllib
import xml.dom.minidom
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import read_text_safely


class TextViewer(BaseViewer):
    name = "Text and source code"
    category = "Text and source code"
    priority = 10
    extensions = (
        ".txt", ".log", ".md", ".markdown", ".rst", ".tex", ".adoc",
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt",
        ".kts", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".cs",
        ".go", ".rs", ".swift", ".php", ".rb", ".lua", ".r", ".dart",
        ".scala", ".sh", ".bash", ".zsh", ".fish", ".bat", ".cmd",
        ".ps1", ".sql", ".css", ".scss", ".sass", ".less", ".vue",
        ".svelte", ".asm", ".dockerfile", ".gitignore", ".editorconfig",
        ".properties", ".gradle", ".cmake", ".makefile", ".diff", ".patch",
        ".env", ".graphql", ".proto", ".sol", ".po", ".pot",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.browser)

    @classmethod
    def supports_path(cls, path: Path) -> bool:
        if super().supports_path(path):
            return True
        if path.name.lower() in {"dockerfile", "makefile", "cmakelists.txt"}:
            return True
        try:
            with path.open("rb") as stream:
                sample = stream.read(4096)
        except OSError:
            return False
        if b"\x00" in sample:
            return False
        if not sample:
            return True
        printable = sum(byte in b"\n\r\t\f\b" or 32 <= byte < 127 or byte >= 0x80 for byte in sample)
        return printable / len(sample) > 0.88

    def load_file(self, path: Path) -> None:
        text, encoding, truncated = read_text_safely(path)
        suffix = path.suffix.lower()
        note = " • показаны первые 8 МБ" if truncated else ""
        self.info.setText(f"{path.name} • {encoding} • {len(text):,} символов{note}")
        if suffix in {".md", ".markdown"}:
            try:
                import markdown

                self.browser.setHtml(markdown.markdown(text, extensions=["tables", "fenced_code"]))
                return
            except ImportError:
                pass
        if suffix in {".html", ".htm"}:
            self.browser.setHtml(text)
            return
        try:
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_for_filename
            from pygments.util import ClassNotFound

            try:
                lexer = get_lexer_for_filename(path.name, text)
            except ClassNotFound:
                lexer = None
            if lexer:
                formatter = HtmlFormatter(noclasses=True, style="friendly")
                self.browser.setHtml(highlight(text, lexer, formatter))
                return
        except ImportError:
            pass
        self.browser.setPlainText(text)


class StructuredTextViewer(TextViewer):
    name = "Structured text"
    category = "Structured data"
    priority = 55
    extensions = (
        ".json", ".jsonl", ".ndjson", ".geojson", ".xml", ".xsd", ".xsl",
        ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".desktop",
        ".plist", ".html", ".htm",
        ".ipynb", ".csvw",
    )

    @classmethod
    def supports_path(cls, path: Path) -> bool:
        """Structured viewer must not inherit the generic text-content probe."""
        lower_name = path.name.lower()
        return any(lower_name.endswith(extension) for extension in cls.extensions)

    def load_file(self, path: Path) -> None:
        text, encoding, truncated = read_text_safely(path)
        suffix = path.suffix.lower()
        formatted = text
        try:
            if suffix in {".json", ".geojson", ".ipynb", ".csvw"}:
                formatted = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            elif suffix in {".jsonl", ".ndjson"}:
                formatted = "\n".join(
                    json.dumps(json.loads(line), ensure_ascii=False, indent=2)
                    for line in text.splitlines() if line.strip()
                )
            elif suffix in {".xml", ".xsd", ".xsl", ".plist"}:
                formatted = xml.dom.minidom.parseString(text).toprettyxml(indent="  ")
            elif suffix in {".yaml", ".yml"}:
                import yaml

                formatted = yaml.safe_dump(yaml.safe_load(text), allow_unicode=True, sort_keys=False)
            elif suffix == ".toml":
                formatted = pprint.pformat(tomllib.loads(text), width=100, sort_dicts=False)
            elif suffix in {".ini", ".cfg", ".conf", ".desktop"}:
                parser = configparser.ConfigParser()
                parser.read_string(text)
                formatted = "\n\n".join(
                    f"[{section}]\n" + "\n".join(f"{key} = {value}" for key, value in parser[section].items())
                    for section in parser.sections()
                ) or text
            elif suffix in {".html", ".htm"}:
                self.info.setText(f"{path.name} • HTML • встроенный просмотр")
                self.browser.setHtml(text)
                return
        except Exception as exc:
            raise ViewerError(f"Не удалось разобрать структурированный файл: {exc}") from exc

        note = " • первые 8 МБ" if truncated else ""
        self.info.setText(f"{path.name} • {encoding}{note}")
        try:
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_for_filename

            lexer = get_lexer_for_filename(path.name, formatted)
            self.browser.setHtml(highlight(formatted, lexer, HtmlFormatter(noclasses=True, style="friendly")))
        except Exception:
            self.browser.setHtml(f"<pre>{html.escape(formatted)}</pre>")
