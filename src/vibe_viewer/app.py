"""Application entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QApplication

APP_STYLE = """
QWidget { color: #172033; }
QMainWindow { background: #f5f7fa; }
QMenuBar, QMenu, QToolBar {
    color: #172033;
    background: #ffffff;
}
QMenuBar::item:selected, QMenu::item:selected { background: #dbeafe; }
QToolBar { border-bottom: 1px solid #dfe3e8; spacing: 5px; }
QTreeView, QTableWidget, QPlainTextEdit, QTextBrowser {
    color: #172033;
    background: #ffffff;
    alternate-background-color: #f7f9fc;
    border: 1px solid #dfe3e8;
    border-radius: 5px;
    selection-background-color: #dbeafe;
    selection-color: #172033;
}
QTreeView::item, QTableWidget::item { padding: 3px; }
QTreeView::item:disabled {
    color: #9a3412;
    background: #fff7ed;
}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox {
    color: #172033;
    border: 1px solid #c9d1dc;
    border-radius: 5px;
    background: #ffffff;
    padding: 5px 8px;
}
QPushButton:hover, QToolButton:hover { background: #eef4ff; border-color: #7aa7ee; }
QPushButton:disabled, QToolButton:disabled, QComboBox:disabled,
QLineEdit:disabled, QSpinBox:disabled { color: #7b8798; background: #eef1f5; }
QHeaderView::section {
    color: #172033;
    background: #eef1f5;
    padding: 6px;
    border: 0;
    border-right: 1px solid #dfe3e8;
    border-bottom: 1px solid #dfe3e8;
}
QStatusBar { color: #172033; background: #ffffff; border-top: 1px solid #dfe3e8; }
QSplitter::handle { background: #dfe3e8; width: 2px; }
QToolTip { color: #172033; background: #fff7d6; border: 1px solid #c9a227; }
"""


def configure_runtime_environment() -> None:
    """Use stable Linux rendering defaults while allowing an explicit opt-out."""
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("VIBE_VIEWER_HARDWARE_ACCELERATION") == "1":
        return

    # QWidget itself is software-rendered. These defaults also keep Qt Multimedia
    # from probing broken VA-API/Vulkan devices in VMs and remote Linux sessions.
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")
    os.environ.setdefault("QT_DISABLE_HW_TEXTURES_CONVERSION", "1")


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication instance."""
    configure_runtime_environment()
    QCoreApplication.setOrganizationName("VibeViewer")
    QCoreApplication.setApplicationName("Vibe Viewer")
    QCoreApplication.setApplicationVersion("1.0.0")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    return app


def main() -> int:
    """Run the desktop application."""
    app = create_application()
    # Importing the window also imports Qt Multimedia. Keep it after the Linux
    # rendering setup so media backends see the stable defaults immediately.
    from vibe_viewer.ui.main_window import MainWindow

    requested = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    start_directory = requested.parent if requested and requested.is_file() else requested
    window = MainWindow(start_directory=start_directory)
    window.show()
    if requested and requested.is_file():
        window.open_file(requested)
    return app.exec()
