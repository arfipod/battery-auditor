# Design

## Goals

1. Measure batteries without introducing meaningful artificial load.
2. Separate the collector, storage, analysis, and UI.
3. Record enough information to diagnose multiple batteries.
4. Support sessions that end because of unexpected shutdown.
5. Integrate with TLP without calling TLP in a loop.

## Architecture

```text
battery-auditor
|-- collector
|  |-- reads /sys/class/power_supply
|  |-- generates events
|  |-- writes SQLite
|  `-- updates heartbeat
|
|-- SQLite
|  |-- sessions
|  |-- samples
|  |-- sample_batteries
|  |-- power_supplies
|  `-- events
|
|-- CLI
|  |-- once
|  |-- collect
|  |-- sessions
|  |-- analyze
|  |-- analyze phases
|  |-- export
|  `-- tlp-*
|
`-- optional Qt UI
   |-- current status
   |-- manual recording
   |-- charts
   |-- events
   `-- TLP panel
```

## Collector hot path

The collector only performs cheap operations:

- `read()` from sysfs;
- string conversion to integers/floats;
- SQLite insert;
- small JSON heartbeat.

It does not use DBus, UPower, TLP, or periodic external commands.

## Why SQLite WAL

SQLite WAL allows writing samples without blocking UI reads. Normal mode uses `synchronous=NORMAL`. Black-box mode switches to `FULL` and forces a flush for every sample to prioritize durability over minimum power use.

## Per-battery measurement

Battery Auditor does not rely only on the global percentage. Each battery has:

- kernel-reported percentage;
- computed percentage: `energy_now / energy_full * 100`;
- health: `energy_full / energy_full_design * 100`;
- instantaneous power;
- voltage;
- charging/discharging state;
- charge thresholds exposed by sysfs.

This makes it possible to distinguish normal firmware-controlled discharge from voltage sag, bad calibration, or physical degradation.

## Phase analysis

Raw samples are useful for charts, but dual-battery behavior is often easier to reason about as phases. A phase is a semantically stable run of samples where AC state, active discharging battery, active charging battery, and durable battery statuses stay the same. The analyzer debounces state changes so one-sample status noise does not create false phases, and short transitions can be kept as `MIXED_TRANSITION` instead of pretending they are a clean charge or discharge span.

The phase analyzer is intentionally post-processing only. It reads existing `samples` and `sample_batteries` rows through the normal read-only database path and does not run inside the collector loop.

On Lenovo dual-battery systems such as a ThinkPad T460s, firmware commonly charges or drains one pack while the other remains nearly flat. For example, BAT0 can discharge with BAT1 idle, then after AC connects BAT1 can charge while BAT0 stays flat. The analyzer preserves that behavior by computing per-battery signed Wh deltas, detecting inactive near-zero batteries, and classifying stable spans as `DISCHARGE_BAT0`, `DISCHARGE_BAT1`, `CHARGE_BAT0`, `CHARGE_BAT1`, `AC_IDLE`, `MIXED_TRANSITION`, or `UNKNOWN`.

## Events

Initial events:

- `AC_CONNECTED`
- `AC_DISCONNECTED`
- `BATTERY_SWITCH`
- `BATTERY_STATUS_CHANGE`
- `PERCENT_JUMP`
- `COMPUTED_PERCENT_JUMP`
- `VOLTAGE_SAG`
- `LOW_BATTERY`
- `CRITICAL_BATTERY`
- `MISSED_SAMPLE_WINDOW`
- `THRESHOLD_MISMATCH`
- `PROBABLE_POWER_LOSS`
