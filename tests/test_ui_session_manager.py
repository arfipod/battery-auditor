from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox  # noqa: E402

from thinkpad_energy_manager.config import AuditorConfig  # noqa: E402
from thinkpad_energy_manager.core.database import BatteryDatabase  # noqa: E402
from thinkpad_energy_manager.ui.session_manager import SessionManager  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sysfs_sample"


def test_session_manager_write_action_keeps_shared_reader_open(tmp_path: Path, monkeypatch: Any) -> None:
    app = QApplication.instance() or QApplication([])
    cfg = AuditorConfig(data_dir=tmp_path, db_path=tmp_path / "test.sqlite3", sysfs_power_supply_dir=FIXTURE)
    writer = BatteryDatabase(cfg.resolved_db_path(), cfg)
    writer.init_schema()
    writer.start_session("s1", "old-name", cfg.to_json())
    writer.end_session("s1")
    writer.close()

    reader = BatteryDatabase(cfg.resolved_db_path(), cfg, read_only=True)
    reader.init_schema()
    main_refreshes: list[bool] = []
    manager = SessionManager(
        cfg,
        reader,
        open_in_chart=lambda _session_id: None,
        refresh_main=lambda: main_refreshes.append(True),
    )
    manager.refresh()

    monkeypatch.setattr(manager, "_exactly_one", lambda _title: "s1")
    monkeypatch.setattr(manager, "_collector_may_be_writing", lambda: False)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("new-name", True))

    def fail_warning(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"Unexpected warning dialog: {args!r} {kwargs!r}")

    monkeypatch.setattr(QMessageBox, "warning", fail_warning)

    manager.rename_selected()

    session = reader.get_session("s1")
    assert session is not None
    assert session["name"] == "new-name"
    assert main_refreshes == [True]
    name_item = manager.table.item(0, 2)
    assert name_item is not None
    assert name_item.text() == "new-name"

    app.processEvents()
