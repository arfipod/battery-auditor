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
