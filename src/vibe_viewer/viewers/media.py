"""Embedded audio and video player based on Qt Multimedia."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from vibe_viewer.viewers.base import BaseViewer


class MediaViewer(BaseViewer):
    name = "Audio and video"
    category = "Audio and video"
    priority = 75
    extensions = (
        ".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg",
        ".ogv", ".wmv", ".3gp", ".ts", ".mts", ".m2ts",
        ".mp3", ".wav", ".flac", ".ogg", ".oga", ".opus", ".aac", ".m4a",
        ".wma", ".aiff", ".aif", ".mid", ".midi",
    )

    @classmethod
    def supports_path(cls, path: Path) -> bool:
        if path.suffix.lower() != ".ts":
            return super().supports_path(path)
        try:
            with path.open("rb") as stream:
                sample = stream.read(377)
        except OSError:
            return False
        # MPEG transport streams normally have a 0x47 sync byte every 188 bytes.
        return len(sample) >= 377 and sample[0] == 0x47 and sample[188] == 0x47

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path: Path | None = None
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.video = QVideoWidget()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video)

        self.info = QLabel("Выберите аудио- или видеофайл")
        self.play_button = QPushButton("▶")
        self.play_button.clicked.connect(self._toggle_playback)
        stop_button = QPushButton("■")
        stop_button.clicked.connect(self.player.stop)
        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.setRange(0, 0)
        self.position.sliderMoved.connect(self.player.setPosition)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setMaximumWidth(120)
        self.volume.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        self.audio_output.setVolume(0.7)
        self.time_label = QLabel("00:00 / 00:00")

        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.playbackStateChanged.connect(self._state_changed)
        self.player.errorOccurred.connect(self._show_error)
        self.player.metaDataChanged.connect(self._metadata_changed)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(stop_button)
        controls.addWidget(self.position, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(QLabel("Громкость"))
        controls.addWidget(self.volume)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.info)
        layout.addWidget(self.video, 1)
        layout.addLayout(controls)

    def load_file(self, path: Path) -> None:
        self.player.stop()
        self._path = path
        self.info.setText(f"{path.name} • загрузка…")
        self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.player.play()

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _position_changed(self, position: int) -> None:
        if not self.position.isSliderDown():
            self.position.setValue(position)
        self.time_label.setText(f"{_format_time(position)} / {_format_time(self.player.duration())}")

    def _duration_changed(self, duration: int) -> None:
        self.position.setRange(0, duration)

    def _state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_button.setText("Ⅱ" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def _show_error(self, _error, message: str) -> None:
        self.info.setText(f"Ошибка мультимедиа: {message}")

    def _metadata_changed(self) -> None:
        if self._path is None:
            return
        media_kind = "видео" if self.player.hasVideo() else "аудио"
        self.info.setText(f"{self._path.name} • {media_kind}")

    def unload(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self._path = None


def _format_time(milliseconds: int) -> str:
    total_seconds = max(milliseconds, 0) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
