"""Main two-pane application window."""

from __future__ import annotations

import errno
import os
from pathlib import Path

from PyQt6.QtCore import QDir, QModelIndex, QSettings, QSize, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QFileSystemModel, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vibe_viewer import __version__
from vibe_viewer.core.detection import describe_file
from vibe_viewer.core.registry import ViewerRegistry
from vibe_viewer.viewers import register_default_viewers
from vibe_viewer.viewers.base import BaseViewer


class LocalizedFileSystemModel(QFileSystemModel):
    """Filesystem model with Russian headers and honest access state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._directory_access: dict[str, str | None] = {}

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = ("Имя", "Размер", "Тип", "Дата изменения")
            if 0 <= section < len(headers):
                return headers[section]
        return super().headerData(section, orientation, role)

    def clear_access_cache(self) -> None:
        """Recheck permissions after a manual refresh."""
        self._directory_access.clear()

    def access_error(self, index) -> str | None:
        """Return an explanation when a directory cannot be listed."""
        if not index.isValid() or not self.isDir(index):
            return None
        path = self.filePath(index)
        if path not in self._directory_access:
            self._directory_access[path] = directory_access_error(Path(path))
        return self._directory_access[path]

    def flags(self, index):
        flags = super().flags(index)
        if self.access_error(index):
            flags &= ~Qt.ItemFlag.ItemIsEnabled
            flags &= ~Qt.ItemFlag.ItemIsSelectable
        return flags

    def hasChildren(self, parent=QModelIndex()):  # noqa: B008, N802
        if parent.isValid() and self.access_error(parent):
            return False
        return super().hasChildren(parent)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        access_error = self.access_error(index)
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 1 and self.isDir(index):
            return "—"
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 2:
            if self.isDir(index):
                return "Папка"
            suffix = self.fileInfo(index).suffix().upper()
            return f"{suffix} файл" if suffix else "Файл"
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 3:
            return self.fileInfo(index).lastModified().toString("dd.MM.yyyy HH:mm")
        if access_error:
            if role == Qt.ItemDataRole.DisplayRole and index.column() == 0:
                name = super().data(index, role)
                return f"{name} (нет доступа)"
            if role == Qt.ItemDataRole.ToolTipRole:
                return access_error
            if role == Qt.ItemDataRole.ForegroundRole:
                return QColor("#9a3412")
        return super().data(index, role)


def directory_access_error(path: Path) -> str | None:
    """Check whether *path* can actually be enumerated by this process."""
    try:
        with os.scandir(path) as entries:
            next(entries, None)
    except PermissionError:
        return f"Нет разрешения на чтение папки: {path}"
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EPERM}:
            return f"Нет разрешения на чтение папки: {path}"
        return f"Папка недоступна: {path}\n{exc}"
    return None


def show_directory_access_error(parent: QWidget, message: str) -> None:
    """Show a platform-neutral explanation for inaccessible directories."""
    details = "Проверьте права пользователя и разрешения приложения на доступ к файлам."
    QMessageBox.warning(parent, "Нет доступа к папке", f"{message}\n\n{details}")


def configure_file_tree(tree: QTreeView) -> None:
    """Apply the same readable layout to every filesystem tree."""
    tree.setSortingEnabled(True)
    tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    tree.setAlternatingRowColors(True)
    tree.setAnimated(True)
    tree.setUniformRowHeights(True)
    tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    tree.setTextElideMode(Qt.TextElideMode.ElideMiddle)
    tree.header().setStretchLastSection(False)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
    tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
    tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
    tree.header().setMinimumSectionSize(72)
    tree.header().resizeSection(1, 78)
    tree.header().resizeSection(2, 100)
    tree.header().resizeSection(3, 145)


class MainWindow(QMainWindow):
    """File browser on the right, embedded preview on the left."""

    def __init__(self, start_directory: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Vibe Viewer")
        self.setMinimumSize(960, 620)
        self.resize(1320, 820)

        self.registry = ViewerRegistry()
        register_default_viewers(self.registry)
        self._viewer_instances: dict[type[BaseViewer], BaseViewer] = {}
        self._active_viewer: BaseViewer | None = None
        self._history: list[Path] = []
        self._history_index = -1

        self.viewer_stack = QStackedWidget()
        self.welcome = self._build_welcome()
        self.viewer_stack.addWidget(self.welcome)
        self.browser_panel = self._build_browser()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.viewer_stack)
        splitter.addWidget(self.browser_panel)
        splitter.setSizes([700, 620])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage(
            f"Готово • {self.registry.supported_extension_count} расширений"
        )

        settings = QSettings()
        default_directory = Path.home()
        stored_directory = settings.value("last_directory", str(default_directory), str)
        initial = Path(start_directory or stored_directory)
        if not initial.exists() or not initial.is_dir():
            initial = default_directory
        self.navigate_to(initial, add_history=True)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _build_welcome(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Vibe Viewer")
        title.setStyleSheet("font-size: 34px; font-weight: 700; color: #274060")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(
            "Выберите файл в дереве справа\n"
            "Все содержимое открывается внутри программы"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #65758b")
        count = QLabel(f"Поддерживается {self.registry.supported_extension_count} расширений")
        count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count.setStyleSheet("font-size: 14px; color: #2563eb; margin-top: 16px")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(count)
        return widget

    def _build_browser(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(500)
        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(self._navigate_from_address)
        self.back_button = QPushButton("←")
        self.back_button.setToolTip("Назад")
        self.back_button.clicked.connect(self.go_back)
        up_button = QPushButton("↑")
        up_button.setToolTip("На уровень выше")
        up_button.clicked.connect(self.go_up)
        home_button = QPushButton("⌂")
        home_button.setToolTip("Домашняя папка")
        home_button.clicked.connect(lambda: self.navigate_to(Path.home()))
        refresh_button = QPushButton("↻")
        refresh_button.setToolTip("Обновить")
        refresh_button.clicked.connect(self.refresh)

        address = QHBoxLayout()
        address.addWidget(self.back_button)
        address.addWidget(up_button)
        address.addWidget(home_button)
        address.addWidget(self.path_edit, 1)
        address.addWidget(refresh_button)

        self.model = LocalizedFileSystemModel(self)
        self.model.setFilter(
            QDir.Filter.Dirs
            | QDir.Filter.Files
            | QDir.Filter.Drives
            | QDir.Filter.NoDotAndDotDot
        )
        self.model.setReadOnly(True)
        self.model.directoryLoaded.connect(self._directory_loaded)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        configure_file_tree(self.tree)
        self.tree.doubleClicked.connect(self._activate_index)
        self.tree.clicked.connect(self._preview_index)

        hint = QLabel("Щёлкните по файлу для просмотра • заголовки сортируют список")
        hint.setStyleSheet("color: #65758b")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(address)
        layout.addWidget(hint)
        layout.addWidget(self.tree)
        return panel

    def _build_actions(self) -> None:
        self.open_file_action = QAction("Открыть файл…", self)
        self.open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_file_action.triggered.connect(self.choose_file)
        self.open_folder_action = QAction("Открыть папку или файл…", self)
        self.open_folder_action.setShortcut("Ctrl+Shift+O")
        self.open_folder_action.triggered.connect(self.choose_folder)
        self.formats_action = QAction("Поддерживаемые форматы", self)
        self.formats_action.triggered.connect(self.show_supported_formats)
        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.show_about)
        self.quit_action = QAction("Выход", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("Файл")
        file_menu.addAction(self.open_file_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        view_menu = self.menuBar().addMenu("Вид")
        view_menu.addAction(self.formats_action)
        help_menu = self.menuBar().addMenu("Справка")
        help_menu.addAction(self.about_action)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Основная")
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setMovable(False)
        toolbar.addAction(self.open_file_action)
        toolbar.addAction(self.open_folder_action)
        toolbar.addSeparator()
        toolbar.addAction(self.formats_action)

    def navigate_to(self, directory: str | Path, add_history: bool = True) -> None:
        candidate = Path(directory).expanduser().resolve()
        if not candidate.is_dir():
            QMessageBox.warning(self, "Папка не найдена", f"Нет такой папки:\n{candidate}")
            return
        access_error = directory_access_error(candidate)
        if access_error:
            show_directory_access_error(self, access_error)
            return
        self.path_edit.setText(str(candidate))
        # setRootPath starts QFileSystemModel's asynchronous directory loading and
        # returns the matching valid index. model.index(path) alone may be invalid
        # before that loading starts, leaving the tree apparently empty.
        index = self.model.setRootPath(str(candidate))
        self.tree.setRootIndex(index)
        if add_history:
            self._history = self._history[: self._history_index + 1]
            if not self._history or self._history[-1] != candidate:
                self._history.append(candidate)
                self._history_index = len(self._history) - 1
        self.back_button.setEnabled(self._history_index > 0)
        QSettings().setValue("last_directory", str(candidate))
        self.statusBar().showMessage(f"Папка: {candidate}")

    def open_file(self, path: str | Path) -> None:
        candidate = Path(path)
        if not candidate.exists() or not candidate.is_file():
            QMessageBox.warning(self, "Файл не найден", f"Нет такого файла:\n{candidate}")
            return
        viewer_class = self.registry.viewer_for(candidate)
        viewer = self._viewer_instances.get(viewer_class)
        if viewer is None:
            viewer = viewer_class(self)
            self._viewer_instances[viewer_class] = viewer
            self.viewer_stack.addWidget(viewer)
        if self._active_viewer is not None and self._active_viewer is not viewer:
            self._active_viewer.unload()
        try:
            viewer.load_file(candidate)
        except Exception as exc:
            viewer.unload()
            QMessageBox.warning(
                self,
                "Не удалось открыть файл",
                f"{candidate.name}\n\n{exc}\n\nФайл будет показан в бинарном режиме.",
            )
            fallback_class = next(item for item in self.registry.viewers if item.fallback)
            viewer = self._viewer_instances.get(fallback_class)
            if viewer is None:
                viewer = fallback_class(self)
                self._viewer_instances[fallback_class] = viewer
                self.viewer_stack.addWidget(viewer)
            viewer.load_file(candidate)
        self._active_viewer = viewer
        self.viewer_stack.setCurrentWidget(viewer)
        self.setWindowTitle(f"{candidate.name} — Vibe Viewer")
        self.statusBar().showMessage(
            f"{candidate} • {describe_file(candidate)} • {viewer.name}"
        )

    def _activate_index(self, index) -> None:
        path = Path(self.model.filePath(index))
        if path.is_dir():
            self.navigate_to(path)
        elif path.is_file():
            self.open_file(path)

    def _preview_index(self, index) -> None:
        path = Path(self.model.filePath(index))
        if path.is_file():
            self.open_file(path)

    def _navigate_from_address(self) -> None:
        self.navigate_to(self.path_edit.text())

    def go_back(self) -> None:
        if self._history_index > 0:
            self._history_index -= 1
            self.navigate_to(self._history[self._history_index], add_history=False)
            self.back_button.setEnabled(self._history_index > 0)

    def go_up(self) -> None:
        current = Path(self.path_edit.text())
        if current.parent != current:
            self.navigate_to(current.parent)

    def refresh(self) -> None:
        current = self.path_edit.text()
        self.model.clear_access_cache()
        self.model.setRootPath("")
        self.navigate_to(current, add_history=False)

    def _directory_loaded(self, path: str) -> None:
        if Path(path) != Path(self.model.rootPath()):
            return
        index = self.model.index(path)
        self.statusBar().showMessage(
            f"Папка: {path} • элементов: {self.model.rowCount(index)}"
        )

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", self.path_edit.text())
        if path:
            self.open_file(path)

    def choose_folder(self) -> None:
        dialog = OpenLocationDialog(self.path_edit.text(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selected_path is None:
            return
        if dialog.selected_path.is_dir():
            self.navigate_to(dialog.selected_path)
        else:
            self.navigate_to(dialog.selected_path.parent)
            self.open_file(dialog.selected_path)

    def show_supported_formats(self) -> None:
        SupportedFormatsDialog(self.registry, self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "О Vibe Viewer",
            f"<h2>Vibe Viewer {__version__}</h2>"
            f"<p>Встроенный просмотрщик {self.registry.supported_extension_count} расширений.</p>"
            "<p>Python + PyQt6. Внешние приложения не запускаются.</p>",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        for viewer in self._viewer_instances.values():
            viewer.unload()
        QSettings().setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


class OpenLocationDialog(QDialog):
    """In-app location picker that keeps both files and directories available."""

    def __init__(self, start_directory: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Открыть папку или файл")
        self.resize(900, 620)
        self.selected_path: Path | None = None
        self.current_directory = Path(start_directory).expanduser()
        if not self.current_directory.is_dir():
            self.current_directory = Path.home()

        self.address = QLineEdit()
        self.address.returnPressed.connect(self._navigate_from_address)
        up_button = QPushButton("↑")
        up_button.setToolTip("На уровень выше")
        up_button.clicked.connect(self._go_up)
        home_button = QPushButton("⌂")
        home_button.setToolTip("Домашняя папка")
        home_button.clicked.connect(lambda: self.navigate_to(Path.home()))

        address_layout = QHBoxLayout()
        address_layout.addWidget(up_button)
        address_layout.addWidget(home_button)
        address_layout.addWidget(self.address, 1)

        self.model = LocalizedFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(
            QDir.Filter.Dirs
            | QDir.Filter.Files
            | QDir.Filter.Drives
            | QDir.Filter.NoDotAndDotDot
        )
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        configure_file_tree(self.tree)
        self.tree.doubleClicked.connect(self._activate_index)
        self.tree.selectionModel().selectionChanged.connect(self._selection_changed)

        self.selection_label = QLabel("Выберите файл или папку")
        self.selection_label.setStyleSheet("color: #65758b")
        self.open_button = QPushButton("Открыть выбранное")
        self.open_button.setDefault(True)
        self.open_button.clicked.connect(self._accept_selected)
        current_button = QPushButton("Выбрать текущую папку")
        current_button.clicked.connect(self._accept_current_directory)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.selection_label, 1)
        button_layout.addWidget(current_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.addLayout(address_layout)
        layout.addWidget(
            QLabel(
                "Файлы не скрыты: файл можно открыть, а папку — выбрать или раскрыть двойным щелчком."
            )
        )
        layout.addWidget(self.tree, 1)
        layout.addLayout(button_layout)
        self.navigate_to(self.current_directory)

    def navigate_to(self, directory: str | Path) -> None:
        candidate = Path(directory).expanduser().resolve()
        if not candidate.is_dir():
            return
        access_error = directory_access_error(candidate)
        if access_error:
            show_directory_access_error(self, access_error)
            return
        self.current_directory = candidate
        self.address.setText(str(candidate))
        index = self.model.setRootPath(str(candidate))
        self.tree.setRootIndex(index)
        self.tree.clearSelection()
        self.selection_label.setText(f"Текущая папка: {candidate.name or candidate}")

    def _navigate_from_address(self) -> None:
        candidate = Path(self.address.text()).expanduser()
        if candidate.is_file():
            self.selected_path = candidate.resolve()
            self.accept()
        elif candidate.is_dir():
            self.navigate_to(candidate)
        else:
            QMessageBox.warning(self, "Путь не найден", f"Нет такого пути:\n{candidate}")

    def _go_up(self) -> None:
        if self.current_directory.parent != self.current_directory:
            self.navigate_to(self.current_directory.parent)

    def _activate_index(self, index) -> None:
        candidate = Path(self.model.filePath(index))
        if candidate.is_dir():
            self.navigate_to(candidate)
        elif candidate.is_file():
            self.selected_path = candidate
            self.accept()

    def _selection_changed(self, *_args) -> None:
        indexes = self.tree.selectionModel().selectedRows(0)
        if not indexes:
            return
        candidate = Path(self.model.filePath(indexes[0]))
        kind = "папка" if candidate.is_dir() else "файл"
        self.selection_label.setText(f"Выбрано: {candidate.name} ({kind})")
        self.open_button.setText("Выбрать папку" if candidate.is_dir() else "Открыть файл")

    def _accept_selected(self) -> None:
        indexes = self.tree.selectionModel().selectedRows(0)
        if not indexes:
            self._accept_current_directory()
            return
        selected = Path(self.model.filePath(indexes[0]))
        if selected.is_dir():
            access_error = directory_access_error(selected)
            if access_error:
                show_directory_access_error(self, access_error)
                return
        self.selected_path = selected
        self.accept()

    def _accept_current_directory(self) -> None:
        self.selected_path = self.current_directory
        self.accept()


class SupportedFormatsDialog(QDialog):
    """Compact, automatically generated support matrix."""

    def __init__(self, registry: ViewerRegistry, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Поддерживаемые форматы")
        self.resize(620, 640)
        intro = QLabel(
            f"<b>{registry.supported_extension_count} расширений</b> в "
            f"{len(registry.support_by_category())} категориях. "
            "Неизвестные файлы открываются в HEX-режиме."
        )
        intro.setWordWrap(True)
        tree = QTreeWidget()
        tree.setHeaderLabels(("Категория / расширение", "Количество"))
        tree.setAlternatingRowColors(True)
        tree.setColumnWidth(0, 450)
        for category, extensions in registry.support_by_category().items():
            parent_item = QTreeWidgetItem((category, str(len(extensions))))
            parent_item.setExpanded(False)
            tree.addTopLevelItem(parent_item)
            for extension in extensions:
                QTreeWidgetItem(parent_item, (extension, ""))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(tree)
        layout.addWidget(buttons)
