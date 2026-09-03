"""Capture the real QWidget layout for visual checks in Ubuntu/Xvfb."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer

from vibe_viewer.app import create_application


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "work/ubuntu-ui.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    app = create_application(["vibe-ui-capture"])
    from vibe_viewer.ui.main_window import MainWindow

    window = MainWindow(start_directory=Path("src"))
    window.resize(1320, 820)
    window.show()

    result = {"ok": False}

    def capture() -> None:
        result["ok"] = window.grab().save(str(target), "PNG")
        app.quit()

    QTimer.singleShot(500, capture)
    app.exec()
    if not result["ok"]:
        print(f"Не удалось сохранить снимок интерфейса: {target}", file=sys.stderr)
        return 1
    print(f"Снимок интерфейса сохранён: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
