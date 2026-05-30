from __future__ import annotations

from pathlib import Path

from battery_auditor.config import AuditorConfig
from battery_auditor.core.database import BatteryDatabase, repair_database
from battery_auditor.core.events import EventDetector
from battery_auditor.core.sysfs import read_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "sysfs_sample"


def test_insert_and_fetch_session(tmp_path: Path) -> None:
    cfg = AuditorConfig(data_dir=tmp_path, db_path=tmp_path / "test.sqlite3", sysfs_power_supply_dir=FIXTURE)
    db = BatteryDatabase(cfg.resolved_db_path(), cfg)
    db.init_schema()
    db.start_session("s1", "test", cfg.to_json())
    detector = EventDetector(cfg)
    snap = read_snapshot(FIXTURE)
    events = detector.process(snap)
    sample_id = db.insert_snapshot("s1", 0, snap, events)
    assert sample_id > 0
    db.end_session("s1")
    sessions = db.list_sessions()
    assert len(sessions) == 1
    rows = db.fetch_session_series("s1")
    assert len(rows) == 2


def test_recover_open_session(tmp_path: Path) -> None:
    cfg = AuditorConfig(data_dir=tmp_path, db_path=tmp_path / "test.sqlite3", sysfs_power_supply_dir=FIXTURE)
    db = BatteryDatabase(cfg.resolved_db_path(), cfg)
    db.init_schema()
    db.start_session("s1", "test", cfg.to_json())
    recovered = db.recover_open_sessions()
    assert recovered == ["s1"]
    session = db.get_session("s1")
    assert session is not None
    assert session["probable_power_loss"] == 1


def test_repair_database_writes_clean_copy(tmp_path: Path) -> None:
    cfg = AuditorConfig(data_dir=tmp_path, db_path=tmp_path / "test.sqlite3", sysfs_power_supply_dir=FIXTURE)
    db = BatteryDatabase(cfg.resolved_db_path(), cfg)
    db.init_schema()
    db.start_session("s1", "test", cfg.to_json())
    snap = read_snapshot(FIXTURE)
    sample_id = db.insert_snapshot("s1", 0, snap, [])
    db.close()

    repaired_path = tmp_path / "repaired.sqlite3"
    result = repair_database(cfg.resolved_db_path(), repaired_path)

    assert result.integrity == "ok"
    assert result.repaired_path == repaired_path
    assert result.copied["sessions"] == 1
    assert result.copied["samples"] == 1
    assert result.copied["sample_batteries"] == 2

    repaired = BatteryDatabase(repaired_path, AuditorConfig(db_path=repaired_path))
    rows = repaired.fetch_session_series("s1")
    assert sample_id == 1
    assert len(rows) == 2
