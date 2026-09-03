"""Mail, calendar and contact files."""

from __future__ import annotations

import html
import mailbox
from email import policy
from email.parser import BytesParser
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout

from vibe_viewer.viewers.base import BaseViewer, ViewerError
from vibe_viewer.viewers.helpers import read_prefix, read_text_safely


class MessageAndContactViewer(BaseViewer):
    name = "Messages, contacts and calendars"
    category = "Messages and personal data"
    priority = 60
    extensions = (".eml", ".mbox", ".vcf", ".vcard", ".ics", ".ical", ".msg", ".oft", ".pst")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.info = QLabel()
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.browser)

    def load_file(self, path: Path) -> None:
        try:
            if path.suffix.lower() == ".eml":
                content, details = self._render_eml(path)
            elif path.suffix.lower() == ".mbox":
                content, details = self._render_mbox(path)
            elif path.suffix.lower() in {".msg", ".oft"}:
                content, details = self._render_msg(path)
            elif path.suffix.lower() == ".pst":
                content, details = self._render_pst(path)
            else:
                content, details = self._render_lines(path)
        except Exception as exc:
            raise ViewerError(f"Не удалось открыть сообщение или контакт: {exc}") from exc
        self.info.setText(f"{path.name} • {details}")
        self.browser.setHtml(content)

    @staticmethod
    def _render_eml(path: Path) -> tuple[str, str]:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        headers = "".join(
            f"<p><b>{label}:</b> {html.escape(str(message.get(key, '')))}</p>"
            for key, label in (("from", "От"), ("to", "Кому"), ("date", "Дата"), ("subject", "Тема"))
        )
        body = message.get_body(preferencelist=("html", "plain"))
        if body is None:
            body_html = "<p>Тело сообщения отсутствует</p>"
        else:
            payload = body.get_content()
            body_html = payload if body.get_content_type() == "text/html" else f"<pre>{html.escape(payload)}</pre>"
        attachments = [part.get_filename() or "без имени" for part in message.iter_attachments()]
        attachment_html = "".join(f"<li>{html.escape(name)}</li>" for name in attachments)
        return headers + body_html + (f"<h3>Вложения</h3><ul>{attachment_html}</ul>" if attachments else ""), f"EML • {len(attachments)} вложений"

    @staticmethod
    def _render_mbox(path: Path) -> tuple[str, str]:
        box = mailbox.mbox(path, create=False)
        rows = []
        for index, message in enumerate(box):
            if index >= 1000:
                break
            rows.append(
                f"<tr><td>{index + 1}</td><td>{html.escape(str(message.get('from', '')))}</td>"
                f"<td>{html.escape(str(message.get('subject', '')))}</td>"
                f"<td>{html.escape(str(message.get('date', '')))}</td></tr>"
            )
        return "<table border='1' cellspacing='0' cellpadding='5'><tr><th>#</th><th>От</th><th>Тема</th><th>Дата</th></tr>" + "".join(rows) + "</table>", f"MBOX • показано {len(rows)} сообщений"

    @staticmethod
    def _render_lines(path: Path) -> tuple[str, str]:
        text, encoding, truncated = read_text_safely(path)
        rows = []
        for line in text.splitlines():
            if ":" in line and not line.startswith((" ", "\t")):
                key, value = line.split(":", 1)
                rows.append(f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>")
        note = " • обрезан" if truncated else ""
        return "<table border='1' cellspacing='0' cellpadding='5'>" + "".join(rows) + "</table>", f"структурированный текст • {encoding}{note}"

    @staticmethod
    def _render_msg(path: Path) -> tuple[str, str]:
        import extract_msg

        message = extract_msg.Message(str(path))
        try:
            fields = (("От", message.sender), ("Кому", message.to), ("Дата", message.date), ("Тема", message.subject))
            headers = "".join(f"<p><b>{label}:</b> {html.escape(str(value or ''))}</p>" for label, value in fields)
            body = f"<pre>{html.escape(message.body or '')}</pre>"
            attachments = "".join(f"<li>{html.escape(item.longFilename or item.shortFilename or 'без имени')}</li>" for item in message.attachments)
            return headers + body + (f"<h3>Вложения</h3><ul>{attachments}</ul>" if attachments else ""), f"Outlook MSG • {len(message.attachments)} вложений"
        finally:
            message.close()

    @staticmethod
    def _render_pst(path: Path) -> tuple[str, str]:
        signature = read_prefix(path, 32)
        if not signature.startswith(b"!BDN"):
            raise ViewerError("Неверная сигнатура Outlook PST")
        return f"<pre>{html.escape(signature.hex(' '))}</pre>", f"Outlook PST • {path.stat().st_size} байт • безопасный просмотр заголовка"
