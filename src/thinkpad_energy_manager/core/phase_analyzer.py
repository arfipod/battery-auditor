from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from thinkpad_energy_manager.core.database import BatteryDatabase

PHASE_DISCHARGE_BAT0 = "DISCHARGE_BAT0"
PHASE_DISCHARGE_BAT1 = "DISCHARGE_BAT1"
PHASE_CHARGE_BAT0 = "CHARGE_BAT0"
PHASE_CHARGE_BAT1 = "CHARGE_BAT1"
PHASE_AC_IDLE = "AC_IDLE"
PHASE_MIXED_TRANSITION = "MIXED_TRANSITION"
PHASE_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PhaseAnalyzerConfig:
    min_stable_samples: int = 2
    min_transition_seconds: float = 0.0
    inactive_energy_epsilon_wh: float = 0.005
    active_power_epsilon_w: float = 0.1
    max_sample_gap_seconds: float | None = None


@dataclass(slots=True)
class BatterySample:
    name: str
    status: str | None
    capacity_percent: float | None
    computed_percent: float | None
    energy_now_wh: float | None
    energy_full_wh: float | None
    power_now_w: float | None
    voltage_now_v: float | None


@dataclass(slots=True)
class SamplePoint:
    seq: int
    wall_time: float
    wall_iso: str
    monotonic_time: float
    ac_online: bool | None
    batteries: dict[str, BatterySample]


@dataclass(slots=True)
class Phase:
    session_id: str
    phase_index: int
    start_wall_time: float
    end_wall_time: float
    start_wall_iso: str
    end_wall_iso: str
    duration_seconds: float
    ac_online: bool | None
    active_discharging_battery: str | None
    active_charging_battery: str | None
    battery_states: dict[str, dict[str, Any]]
    energy_delta_wh: dict[str, float | None]
    average_power_w: dict[str, float | None]
    total_energy_delta_wh: float | None
    classification: str
    sample_count: int
    start_seq: int
    end_seq: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _StateKey:
    ac_online: bool | None
    active_discharging_battery: str | None
    active_charging_battery: str | None
    statuses: tuple[tuple[str, str | None], ...]


@dataclass(slots=True)
class _Segment:
    start: int
    end: int
    force_mixed: bool = False


@dataclass(slots=True)
class _SampleBuilder:
    seq: int
    wall_time: float
    wall_iso: str
    monotonic_time: float
    ac_online: bool | None
    batteries: dict[str, BatterySample]


def analyze_session_phases(
    db: BatteryDatabase,
    session_id: str,
    *,
    config: PhaseAnalyzerConfig | None = None,
) -> list[Phase]:
    if db.get_session(session_id) is None:
        raise ValueError(f"Unknown session: {session_id}")
    samples = samples_from_rows(db.fetch_session_series(session_id))
    return analyze_samples(session_id, samples, config=config)


def analyze_samples(
    session_id: str,
    samples: list[SamplePoint],
    *,
    config: PhaseAnalyzerConfig | None = None,
) -> list[Phase]:
    cfg = config or PhaseAnalyzerConfig()
    if not samples:
        return []
    min_stable_samples = max(1, cfg.min_stable_samples)
    states = [_sample_state(samples, index, cfg) for index in range(len(samples))]
    segments = _debounced_segments(samples, states, min_stable_samples, cfg.max_sample_gap_seconds)
    segments = _fold_short_segments(segments, samples, cfg.min_transition_seconds)
    return [
        _phase_from_segment(session_id, phase_index, samples, segment, cfg)
        for phase_index, segment in enumerate(segments)
    ]


def samples_from_rows(rows: list[Any]) -> list[SamplePoint]:
    grouped: dict[int, _SampleBuilder] = {}
    for row in rows:
        seq = int(row["seq"])
        sample = grouped.get(seq)
        if sample is None:
            sample = _SampleBuilder(
                seq=seq,
                wall_time=float(row["wall_time"]),
                wall_iso=str(row["wall_iso"]),
                monotonic_time=float(row["monotonic_time"]),
                ac_online=_row_bool(row["ac_online"]),
                batteries={},
            )
            grouped[seq] = sample
        name = str(row["battery_name"])
        sample.batteries[name] = BatterySample(
            name=name,
            status=str(row["status"]) if row["status"] is not None else None,
            capacity_percent=_row_float(row["capacity_percent"]),
            computed_percent=_row_float(row["computed_percent"]),
            energy_now_wh=_micro_to_unit(row["energy_now_uwh"]),
            energy_full_wh=_micro_to_unit(row["energy_full_uwh"]),
            power_now_w=_micro_to_unit(row["power_now_uw"]),
            voltage_now_v=_micro_to_unit(row["voltage_now_uv"]),
        )
    samples: list[SamplePoint] = []
    for seq in sorted(grouped):
        item = grouped[seq]
        samples.append(
            SamplePoint(
                seq=item.seq,
                wall_time=item.wall_time,
                wall_iso=item.wall_iso,
                monotonic_time=item.monotonic_time,
                ac_online=item.ac_online,
                batteries=item.batteries,
            )
        )
    return samples


def phases_to_text(phases: list[Phase]) -> str:
    if not phases:
        return "No phases found."
    battery_names = sorted({name for phase in phases for name in phase.energy_delta_wh})
    headers = [
        "#",
        "Start",
        "End",
        "Dur",
        "AC",
        "Classification",
        "Disch",
        "Chg",
        *[f"{name} dWh" for name in battery_names],
        "Total dWh",
    ]
    rows: list[list[str]] = []
    for phase in phases:
        rows.append(
            [
                str(phase.phase_index),
                _short_iso(phase.start_wall_iso),
                _short_iso(phase.end_wall_iso),
                _format_duration(phase.duration_seconds),
                _bool_text(phase.ac_online),
                phase.classification,
                phase.active_discharging_battery or "-",
                phase.active_charging_battery or "-",
                *[_format_optional_float(phase.energy_delta_wh.get(name), precision=3) for name in battery_names],
                _format_optional_float(phase.total_energy_delta_wh, precision=3),
            ]
        )
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    lines = ["  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))]
    lines.append("  ".join("-" * width for width in widths))
    lines.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows)
    return "\n".join(lines)


def export_phases_json(phases: list[Phase], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([phase.to_dict() for phase in phases], ensure_ascii=False, indent=2), encoding="utf-8")


def export_phases_csv(phases: list[Phase], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [_phase_flat_row(phase) for phase in phases]
    with output.open("w", newline="", encoding="utf-8") as fh:
        if not rows:
            fh.write("")
            return
        fields = sorted({key for row in rows for key in row})
        preferred = [
            "session_id",
            "phase_index",
            "start_wall_iso",
            "end_wall_iso",
            "duration_seconds",
            "ac_online",
            "classification",
            "active_discharging_battery",
            "active_charging_battery",
            "total_energy_delta_wh",
            "sample_count",
            "start_seq",
            "end_seq",
        ]
        fieldnames = [field for field in preferred if field in fields] + [field for field in fields if field not in preferred]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _debounced_segments(
    samples: list[SamplePoint],
    states: list[_StateKey],
    min_stable_samples: int,
    max_sample_gap_seconds: float | None,
) -> list[_Segment]:
    segments: list[_Segment] = []
    current_state = states[0]
    current_start = 0
    candidate_state: _StateKey | None = None
    candidate_start: int | None = None
    candidate_count = 0

    for index in range(1, len(samples)):
        if max_sample_gap_seconds is not None:
            gap = samples[index].wall_time - samples[index - 1].wall_time
            if gap > max_sample_gap_seconds:
                if index - 1 >= current_start:
                    segments.append(_Segment(current_start, index - 1))
                current_start = index
                current_state = states[index]
                candidate_state = None
                candidate_start = None
                candidate_count = 0
                continue

        state = states[index]
        if state == current_state:
            candidate_state = None
            candidate_start = None
            candidate_count = 0
            continue

        if candidate_state == state:
            candidate_count += 1
        else:
            candidate_state = state
            candidate_start = index
            candidate_count = 1

        if candidate_count >= min_stable_samples and candidate_start is not None:
            if candidate_start - 1 >= current_start:
                segments.append(_Segment(current_start, candidate_start - 1))
            current_start = candidate_start
            current_state = state
            candidate_state = None
            candidate_start = None
            candidate_count = 0

    if current_start < len(samples):
        segments.append(_Segment(current_start, len(samples) - 1))
    return segments


def _fold_short_segments(segments: list[_Segment], samples: list[SamplePoint], min_seconds: float) -> list[_Segment]:
    if min_seconds <= 0.0 or len(segments) <= 1:
        return segments
    folded: list[_Segment] = []
    index = 0
    while index < len(segments):
        segment = segments[index]
        if _segment_duration(segment, samples) >= min_seconds:
            folded.append(segment)
            index += 1
            continue
        if folded and index + 1 < len(segments):
            previous = folded[-1]
            next_segment = segments[index + 1]
            if _segment_edge_state(previous, samples) == _segment_edge_state(next_segment, samples):
                folded[-1] = _Segment(previous.start, next_segment.end, previous.force_mixed or next_segment.force_mixed)
                index += 2
                continue
        folded.append(_Segment(segment.start, segment.end, True))
        index += 1
    return folded


def _phase_from_segment(
    session_id: str,
    phase_index: int,
    samples: list[SamplePoint],
    segment: _Segment,
    cfg: PhaseAnalyzerConfig,
) -> Phase:
    phase_samples = samples[segment.start : segment.end + 1]
    first = phase_samples[0]
    last = phase_samples[-1]
    duration_seconds = max(0.0, last.wall_time - first.wall_time)
    battery_names = sorted({name for sample in phase_samples for name in sample.batteries})
    battery_states: dict[str, dict[str, Any]] = {}
    energy_delta_wh: dict[str, float | None] = {}
    average_power_w: dict[str, float | None] = {}

    for name in battery_names:
        battery_series = [sample.batteries[name] for sample in phase_samples if name in sample.batteries]
        first_battery = battery_series[0]
        last_battery = battery_series[-1]
        delta = _delta(first_battery.energy_now_wh, last_battery.energy_now_wh)
        energy_delta_wh[name] = delta
        average_power_w[name] = _average_power(delta, duration_seconds, cfg.inactive_energy_epsilon_wh)
        statuses = Counter(_normalize_status(battery.status) or "unknown" for battery in battery_series)
        powers = [battery.power_now_w for battery in battery_series if battery.power_now_w is not None]
        battery_states[name] = {
            "first_status": first_battery.status,
            "last_status": last_battery.status,
            "status_counts": dict(sorted(statuses.items())),
            "first_energy_wh": first_battery.energy_now_wh,
            "last_energy_wh": last_battery.energy_now_wh,
            "first_capacity_percent": first_battery.capacity_percent,
            "last_capacity_percent": last_battery.capacity_percent,
            "first_computed_percent": first_battery.computed_percent,
            "last_computed_percent": last_battery.computed_percent,
            "energy_full_wh": last_battery.energy_full_wh,
            "mean_power_now_w": mean(powers) if powers else None,
            "inactive": delta is not None and abs(delta) <= cfg.inactive_energy_epsilon_wh,
        }

    active_discharging = _active_phase_battery(phase_samples, energy_delta_wh, "discharging", cfg)
    active_charging = _active_phase_battery(phase_samples, energy_delta_wh, "charging", cfg)
    total_delta = _total_delta(energy_delta_wh)
    classification = _classify_phase(first.ac_online, active_discharging, active_charging, total_delta, segment.force_mixed, cfg)

    return Phase(
        session_id=session_id,
        phase_index=phase_index,
        start_wall_time=first.wall_time,
        end_wall_time=last.wall_time,
        start_wall_iso=first.wall_iso,
        end_wall_iso=last.wall_iso,
        duration_seconds=duration_seconds,
        ac_online=first.ac_online,
        active_discharging_battery=active_discharging,
        active_charging_battery=active_charging,
        battery_states=battery_states,
        energy_delta_wh=energy_delta_wh,
        average_power_w=average_power_w,
        total_energy_delta_wh=total_delta,
        classification=classification,
        sample_count=len(phase_samples),
        start_seq=first.seq,
        end_seq=last.seq,
    )


def _sample_state(samples: list[SamplePoint], index: int, cfg: PhaseAnalyzerConfig) -> _StateKey:
    sample = samples[index]
    deltas = _sample_deltas(samples, index)
    active_discharge = _active_sample_battery(sample, deltas, "discharging", cfg)
    active_charge = _active_sample_battery(sample, deltas, "charging", cfg)
    statuses = tuple(
        (name, _normalize_status(battery.status))
        for name, battery in sorted(sample.batteries.items())
    )
    return _StateKey(sample.ac_online, active_discharge, active_charge, statuses)


def _sample_deltas(samples: list[SamplePoint], index: int) -> dict[str, float | None]:
    if len(samples) == 1:
        return {name: None for name in samples[index].batteries}
    previous_index = max(0, index - 1)
    if index == 0:
        previous_index = 0
        next_index = 1
    else:
        next_index = index
    before = samples[previous_index]
    after = samples[next_index]
    names = set(before.batteries) | set(after.batteries)
    return {
        name: _delta(
            before.batteries[name].energy_now_wh if name in before.batteries else None,
            after.batteries[name].energy_now_wh if name in after.batteries else None,
        )
        for name in names
    }


def _active_sample_battery(
    sample: SamplePoint,
    deltas: dict[str, float | None],
    direction: str,
    cfg: PhaseAnalyzerConfig,
) -> str | None:
    candidates: list[tuple[float, str]] = []
    for name, battery in sample.batteries.items():
        delta = deltas.get(name)
        status = _normalize_status(battery.status)
        power = battery.power_now_w or 0.0
        if direction == "discharging":
            by_energy = delta is not None and delta < -cfg.inactive_energy_epsilon_wh
            by_status = status == "discharging" and power >= cfg.active_power_epsilon_w
            by_context = sample.ac_online is False and by_energy
            if (status == "discharging" and by_energy) or by_context or by_status:
                candidates.append((abs(delta or 0.0) + power / 10_000.0, name))
        else:
            by_energy = delta is not None and delta > cfg.inactive_energy_epsilon_wh
            by_status = status == "charging" and power >= cfg.active_power_epsilon_w
            by_context = sample.ac_online is True and by_energy
            if (status == "charging" and by_energy) or by_context or by_status:
                candidates.append((abs(delta or 0.0) + power / 10_000.0, name))
    if not candidates:
        return None
    return max(candidates)[1]


def _active_phase_battery(
    phase_samples: list[SamplePoint],
    energy_delta_wh: dict[str, float | None],
    direction: str,
    cfg: PhaseAnalyzerConfig,
) -> str | None:
    candidates: list[tuple[float, str]] = []
    for name, delta in energy_delta_wh.items():
        battery_series = [sample.batteries[name] for sample in phase_samples if name in sample.batteries]
        status_counts = Counter(_normalize_status(battery.status) for battery in battery_series)
        powers = [battery.power_now_w or 0.0 for battery in battery_series]
        mean_power = mean(powers) if powers else 0.0
        if direction == "discharging":
            by_energy = delta is not None and delta < -cfg.inactive_energy_epsilon_wh
            by_status = status_counts["discharging"] > 0
        else:
            by_energy = delta is not None and delta > cfg.inactive_energy_epsilon_wh
            by_status = status_counts["charging"] > 0
        if by_energy and (by_status or mean_power >= cfg.active_power_epsilon_w):
            candidates.append((abs(delta or 0.0), name))
    if not candidates:
        return None
    return max(candidates)[1]


def _classify_phase(
    ac_online: bool | None,
    active_discharging: str | None,
    active_charging: str | None,
    total_delta: float | None,
    force_mixed: bool,
    cfg: PhaseAnalyzerConfig,
) -> str:
    if force_mixed:
        return PHASE_MIXED_TRANSITION
    if active_discharging and active_charging:
        return PHASE_MIXED_TRANSITION
    if active_discharging == "BAT0":
        return PHASE_DISCHARGE_BAT0
    if active_discharging == "BAT1":
        return PHASE_DISCHARGE_BAT1
    if active_charging == "BAT0":
        return PHASE_CHARGE_BAT0
    if active_charging == "BAT1":
        return PHASE_CHARGE_BAT1
    if ac_online is True and (total_delta is None or abs(total_delta) <= cfg.inactive_energy_epsilon_wh):
        return PHASE_AC_IDLE
    return PHASE_UNKNOWN


def _phase_flat_row(phase: Phase) -> dict[str, Any]:
    row: dict[str, Any] = {
        "session_id": phase.session_id,
        "phase_index": phase.phase_index,
        "start_wall_time": phase.start_wall_time,
        "end_wall_time": phase.end_wall_time,
        "start_wall_iso": phase.start_wall_iso,
        "end_wall_iso": phase.end_wall_iso,
        "duration_seconds": phase.duration_seconds,
        "ac_online": phase.ac_online,
        "classification": phase.classification,
        "active_discharging_battery": phase.active_discharging_battery,
        "active_charging_battery": phase.active_charging_battery,
        "total_energy_delta_wh": phase.total_energy_delta_wh,
        "sample_count": phase.sample_count,
        "start_seq": phase.start_seq,
        "end_seq": phase.end_seq,
    }
    for name, value in phase.energy_delta_wh.items():
        row[f"{name}_energy_delta_wh"] = value
    for name, value in phase.average_power_w.items():
        row[f"{name}_average_power_w"] = value
    return row


def _segment_duration(segment: _Segment, samples: list[SamplePoint]) -> float:
    return max(0.0, samples[segment.end].wall_time - samples[segment.start].wall_time)


def _segment_edge_state(segment: _Segment, samples: list[SamplePoint]) -> tuple[bool | None, str | None, str | None]:
    start = samples[segment.start]
    return (
        start.ac_online,
        _dominant_status_battery(samples[segment.start : segment.end + 1], "discharging"),
        _dominant_status_battery(samples[segment.start : segment.end + 1], "charging"),
    )


def _dominant_status_battery(samples: list[SamplePoint], status: str) -> str | None:
    counts: Counter[str] = Counter()
    for sample in samples:
        for name, battery in sample.batteries.items():
            if _normalize_status(battery.status) == status:
                counts[name] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _total_delta(values: dict[str, float | None]) -> float | None:
    present = [value for value in values.values() if value is not None]
    if not present:
        return None
    return sum(present)


def _average_power(delta_wh: float | None, duration_seconds: float, epsilon_wh: float) -> float | None:
    if delta_wh is None or duration_seconds <= 0.0 or abs(delta_wh) <= epsilon_wh:
        return None
    return delta_wh / (duration_seconds / 3600.0)


def _delta(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return end - start


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None
    cleaned = status.strip().lower()
    return cleaned or None


def _row_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _row_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _micro_to_unit(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) / 1_000_000.0


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, remainder = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m{remainder:02d}s"


def _short_iso(value: str) -> str:
    return value.replace("T", " ").split("+", maxsplit=1)[0]


def _bool_text(value: bool | None) -> str:
    if value is None:
        return "?"
    return "on" if value else "off"


def _format_optional_float(value: float | None, *, precision: int) -> str:
    if value is None:
        return "-"
    return f"{value:.{precision}f}"
