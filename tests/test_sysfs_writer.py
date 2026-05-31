from __future__ import annotations

from pathlib import Path

import pytest

from thinkpad_energy_manager.core import sysfs_writer


def test_sysfs_writer_accepts_known_control_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "sys" / "class" / "leds"
    led = root / "thinkpad::kbd_backlight"
    led.mkdir(parents=True)
    brightness = led / "brightness"
    brightness.write_text("0\n", encoding="utf-8")

    monkeypatch.setattr(sysfs_writer, "ALLOWED_WRITES", {(root, "brightness")})

    sysfs_writer.write_sysfs_value(brightness, "2")

    assert brightness.read_text(encoding="utf-8") == "2\n"


def test_sysfs_writer_rejects_unknown_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    allowed_root = tmp_path / "sys" / "class" / "leds"
    other = tmp_path / "etc" / "shadow"
    other.parent.mkdir(parents=True)
    other.write_text("", encoding="utf-8")

    monkeypatch.setattr(sysfs_writer, "ALLOWED_WRITES", {(allowed_root, "brightness")})

    with pytest.raises(ValueError, match="Refusing"):
        sysfs_writer.write_sysfs_value(other, "2")


def test_sysfs_writer_rejects_multiline_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "sys" / "class" / "rfkill"
    radio = root / "rfkill0"
    radio.mkdir(parents=True)
    soft = radio / "soft"
    soft.write_text("0\n", encoding="utf-8")

    monkeypatch.setattr(sysfs_writer, "ALLOWED_WRITES", {(root, "soft")})

    with pytest.raises(ValueError, match="single line"):
        sysfs_writer.write_sysfs_value(soft, "1\n2")
