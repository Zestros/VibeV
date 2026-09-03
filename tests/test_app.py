import os

from vibe_viewer import app


def test_linux_runtime_uses_stable_software_defaults(monkeypatch) -> None:
    keys = (
        "QT_OPENGL",
        "QT_QUICK_BACKEND",
        "QT_FFMPEG_DECODING_HW_DEVICE_TYPES",
        "QT_DISABLE_HW_TEXTURES_CONVERSION",
        "VIBE_VIEWER_HARDWARE_ACCELERATION",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(app.sys, "platform", "linux")

    app.configure_runtime_environment()

    assert os.environ["QT_OPENGL"] == "software"
    assert os.environ["QT_QUICK_BACKEND"] == "software"
    assert os.environ["QT_FFMPEG_DECODING_HW_DEVICE_TYPES"] == ","
    assert os.environ["QT_DISABLE_HW_TEXTURES_CONVERSION"] == "1"


def test_hardware_acceleration_opt_out_preserves_environment(monkeypatch) -> None:
    monkeypatch.setattr(app.sys, "platform", "linux")
    monkeypatch.setenv("VIBE_VIEWER_HARDWARE_ACCELERATION", "1")
    monkeypatch.setenv("QT_OPENGL", "desktop")

    app.configure_runtime_environment()

    assert os.environ["QT_OPENGL"] == "desktop"
