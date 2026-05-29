from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from battery_auditor.config import AuditorConfig, load_config
from battery_auditor.core.analyzer import (
    export_session_csv,
    export_session_json,
    summarize_session,
    summary_to_text,
)
from battery_auditor.core.collector import BatteryCollector
from battery_auditor.core.database import BatteryDatabase
from battery_auditor.core.sysfs import read_snapshot
from battery_auditor.core.tlp import TlpClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="battery-auditor",
        description="Low-impact Linux battery recorder and diagnostics toolkit.",
    )
    parser.add_argument("--config", type=Path, action="append", help="Extra TOML config path.")
    parser.add_argument("--db", type=Path, help="SQLite database path.")
    parser.add_argument("--sysfs", type=Path, help="Power supply sysfs root. Defaults to /sys/class/power_supply.")

    sub = parser.add_subparsers(dest="command", required=True)

    once = sub.add_parser("once", help="Read one sysfs snapshot and print it.")
    once.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    collect = sub.add_parser("collect", help="Start a recording session.")
    collect.add_argument("--name", help="Human-readable session name.")
    collect.add_argument("--interval", type=float, help="Sampling interval in seconds.")
    collect.add_argument("--duration", type=float, help="Stop after N seconds.")
    collect.add_argument(
        "--mode",
        choices=["passive", "diagnostic", "blackbox"],
        default="diagnostic",
        help="Recording profile. blackbox flushes harder for power-loss forensics.",
    )
    collect.add_argument("--no-recover", action="store_true", help="Do not mark previous open sessions as interrupted.")

    sessions = sub.add_parser("sessions", help="List recording sessions.")
    sessions.add_argument("--limit", type=int, default=50)

    analyze = sub.add_parser("analyze", help="Analyze a session.")
    analyze.add_argument("session_id", nargs="?", help="Defaults to latest session.")
    analyze.add_argument("--json", action="store_true")

    export = sub.add_parser("export", help="Export session samples.")
    export.add_argument("session_id", nargs="?", help="Defaults to latest session.")
    export.add_argument("--format", choices=["csv", "json"], default="csv")
    export.add_argument("--out", type=Path, required=True)

    recover = sub.add_parser("recover", help="Mark open sessions as interrupted/probable power loss.")
    recover.add_argument("--reason", default="manual_recover")

    tlp_b = sub.add_parser("tlp-stat", help="Run tlp-stat on demand.")
    tlp_b.add_argument("section", choices=["battery", "config", "system"], default="battery", nargs="?")
    tlp_b.add_argument("--no-sudo", action="store_true")

    setcharge = sub.add_parser("tlp-setcharge", help="Set temporary TLP charge thresholds.")
    setcharge.add_argument("battery", help="BAT0, BAT1, ...")
    setcharge.add_argument("start", type=int)
    setcharge.add_argument("stop", type=int)
    setcharge.add_argument("--no-sudo", action="store_true")

    recal = sub.add_parser("tlp-recalibrate", help="Run TLP recalibration for one battery.")
    recal.add_argument("battery", help="BAT0, BAT1, ...")
    recal.add_argument("--no-sudo", action="store_true")

    return parser


def load_runtime_config(args: argparse.Namespace) -> AuditorConfig:
    paths = None
    if args.config:
        paths = args.config
    cfg = load_config(paths=paths)
    if args.db:
        cfg.db_path = args.db
    if args.sysfs:
        cfg.sysfs_power_supply_dir = args.sysfs
    return cfg


def db_from_cfg(cfg: AuditorConfig) -> BatteryDatabase:
    db = BatteryDatabase(cfg.resolved_db_path(), cfg)
    db.init_schema()
    return db


def command_once(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    snap = read_snapshot(cfg.sysfs_power_supply_dir)
    if args.json:
        print(json.dumps(snap.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"Time: {snap.wall_iso}")
    print(f"AC online: {snap.ac_online}")
    total = snap.total_computed_percent
    if total is not None:
        print(f"Total: {total:.1f}% ({_uwh_to_wh(snap.total_energy_now_uwh):.2f} Wh / {_uwh_to_wh(snap.total_energy_full_uwh):.2f} Wh)")
    for b in snap.batteries:
        computed = f"{b.computed_percent:.1f}%" if b.computed_percent is not None else "n/a"
        health = f"{b.health_percent:.1f}%" if b.health_percent is not None else "n/a"
        print(
            f"{b.name}: status={b.status or 'n/a'} reported={b.capacity_percent} computed={computed} "
            f"health={health} energy={_uwh_to_wh(b.energy_now_uwh):.2f}/{_uwh_to_wh(b.energy_full_uwh):.2f}Wh "
            f"power={_uw_to_w(b.power_now_uw):.2f}W voltage={_uv_to_v(b.voltage_now_uv):.3f}V"
        )
    return 0


def command_collect(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    mode_interval = {"passive": 10.0, "diagnostic": cfg.interval_seconds, "blackbox": 1.0}
    interval = args.interval if args.interval is not None else mode_interval[args.mode]
    if args.mode == "blackbox":
        cfg.sqlite_synchronous = "FULL"
        cfg.blackbox_flush_each_sample = True
    collector = BatteryCollector(cfg)
    result = collector.run(
        name=args.name,
        interval_seconds=interval,
        duration_seconds=args.duration,
        blackbox=args.mode == "blackbox",
        recover_open_sessions=not args.no_recover,
    )
    print(f"Session {result.session_id} ended: reason={result.reason}, samples={result.samples}")
    return 0


def command_sessions(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    db = db_from_cfg(cfg)
    rows = db.list_sessions(limit=args.limit)
    if not rows:
        print("No sessions.")
        return 0
    for row in rows:
        status = row["ended_reason"] or "running"
        loss = " probable-power-loss" if row["probable_power_loss"] else ""
        print(
            f"{row['id']} | {row['started_at_iso']} → {row['ended_at_iso'] or 'open'} | "
            f"samples={row['sample_count']} | {status}{loss} | {row['name'] or ''}"
        )
    return 0


def command_analyze(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    db = db_from_cfg(cfg)
    session_id = args.session_id or db.latest_session_id()
    if session_id is None:
        print("No sessions found.", file=sys.stderr)
        return 2
    summary = summarize_session(db, session_id)
    if args.json:
        print(json.dumps(summary, default=lambda o: getattr(o, "__dict__", str(o)), ensure_ascii=False, indent=2))
    else:
        print(summary_to_text(summary))
    return 0


def command_export(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    db = db_from_cfg(cfg)
    session_id = args.session_id or db.latest_session_id()
    if session_id is None:
        print("No sessions found.", file=sys.stderr)
        return 2
    if args.format == "csv":
        export_session_csv(db, session_id, args.out)
    else:
        export_session_json(db, session_id, args.out)
    print(f"Exported {session_id} to {args.out}")
    return 0


def command_recover(args: argparse.Namespace, cfg: AuditorConfig) -> int:
    db = db_from_cfg(cfg)
    recovered = db.recover_open_sessions(reason=args.reason)
    if recovered:
        print("Recovered sessions:")
        for session_id in recovered:
            print(f"  {session_id}")
    else:
        print("No open sessions to recover.")
    return 0


def command_tlp_stat(args: argparse.Namespace) -> int:
    client = TlpClient(use_sudo=not args.no_sudo)
    if args.section == "battery":
        result = client.stat_battery()
    elif args.section == "config":
        result = client.stat_config()
    else:
        result = client.stat_system()
    print(result.combined_output())
    return result.returncode


def command_tlp_setcharge(args: argparse.Namespace) -> int:
    client = TlpClient(use_sudo=not args.no_sudo)
    result = client.setcharge(args.start, args.stop, args.battery)
    print(result.combined_output())
    return result.returncode


def command_tlp_recalibrate(args: argparse.Namespace) -> int:
    client = TlpClient(use_sudo=not args.no_sudo)
    result = client.recalibrate(args.battery)
    print(result.combined_output())
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = load_runtime_config(args)
    commands: dict[str, Any] = {
        "once": command_once,
        "collect": command_collect,
        "sessions": command_sessions,
        "analyze": command_analyze,
        "export": command_export,
        "recover": command_recover,
    }
    if args.command in commands:
        return int(commands[args.command](args, cfg))
    if args.command == "tlp-stat":
        return command_tlp_stat(args)
    if args.command == "tlp-setcharge":
        return command_tlp_setcharge(args)
    if args.command == "tlp-recalibrate":
        return command_tlp_recalibrate(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _uwh_to_wh(value: int | None) -> float:
    return 0.0 if value is None else value / 1_000_000.0


def _uw_to_w(value: int | None) -> float:
    return 0.0 if value is None else value / 1_000_000.0


def _uv_to_v(value: int | None) -> float:
    return 0.0 if value is None else value / 1_000_000.0


if __name__ == "__main__":
    raise SystemExit(main())
