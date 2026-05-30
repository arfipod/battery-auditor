# Battery Auditor

Battery Auditor is a local Linux tool that records, analyzes, and charts real battery behavior, especially on laptops with multiple batteries such as Lenovo ThinkPads with Power Bridge.

Its main goal is not to save battery power, but to **diagnose batteries without adding much measurement noise**.

## What's included

- Lightweight collector based on `/sys/class/power_supply`.
- Persistent SQLite writes with WAL.
- Black-box mode for tests where the laptop may shut down because the battery runs out.
- Event detection: AC changes, active battery changes, percentage jumps, sudden voltage sag, low/critical battery, and interrupted sessions.
- Optional Python + Qt/PySide6 UI with interactive pyqtgraph charts.
- Manual TLP wrapper: `tlp-stat`, `setcharge`, `recalibrate`.
- User-level systemd services.
- CSV/JSON export for external analysis.

## Non-invasive design

The collector does not run `tlp-stat`, `upower`, `acpi`, `journalctl`, or any other external command in a loop. In the hot path it only performs:

1. small file reads from `/sys/class/power_supply`;
2. derived metric calculations;
3. compact row inserts into SQLite.

The UI is optional. For a serious discharge test, it is better to close the UI and leave only the collector or systemd service running.

## Installation on Debian 13 / modern Linux

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tlp libxcb-cursor0

# For the Qt UI via pip:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ui]'
```

If you prefer to install UI dependencies from Debian packages, install the `python3-pyside6*` and `python3-pyqtgraph` packages available for your version and then run:

```bash
python -m pip install -e .
```

## Quick start

Read a single snapshot:

```bash
battery-auditor once
```

Record a diagnostic session:

```bash
battery-auditor collect --mode diagnostic --name normal-discharge
```

Record in black-box mode:

```bash
battery-auditor collect --mode blackbox --name discharge-to-shutdown
```

List sessions:

```bash
battery-auditor sessions
```

Analyze the latest session:

```bash
battery-auditor analyze
```

Export to CSV:

```bash
battery-auditor export --format csv --out discharge.csv
```

Open the UI:

```bash
battery-auditor-qt
```

## Black-box mode

Black-box mode is designed to bracket the moment of battery-related shutdown:

```bash
battery-auditor collect --mode blackbox --name final-test
```

In this mode:

- default interval: 1 second;
- SQLite `synchronous=FULL`;
- flush on every sample;
- persistent per-session heartbeat;
- if the machine shuts down and the session remains open, the next `recover` marks it as `PROBABLE_POWER_LOSS`.

After rebooting:

```bash
battery-auditor recover
battery-auditor analyze
```

The exact shutdown instant cannot be measured after the machine loses power, but it can be bracketed by the last persisted heartbeat/sample and the configured interval.

## User systemd services

Install units:

```bash
./scripts/install-user-service.sh
```

Enable the normal collector:

```bash
systemctl --user enable --now battery-auditor.service
```

Start a black-box session under systemd:

```bash
systemctl --user start battery-auditor-blackbox.service
```

View logs:

```bash
journalctl --user -u battery-auditor.service -f
```

Uninstall units:

```bash
./scripts/uninstall-user-service.sh
```

## TLP

Battery Auditor does not replace TLP. It complements it.

Useful commands:

```bash
battery-auditor tlp-stat battery
battery-auditor tlp-stat config
battery-auditor tlp-setcharge BAT0 75 80
battery-auditor tlp-setcharge BAT1 75 80
battery-auditor tlp-recalibrate BAT0
battery-auditor tlp-recalibrate BAT1
```

TLP actions are manual and are not part of the periodic collector, so they do not contaminate measurements.

## Recorded data

For each sample, Battery Auditor stores:

- wall-clock and ISO timestamp;
- monotonic timestamp;
- AC state;
- computed total energy;
- total power;
- computed total percentage;
- internal collector metrics;
- per battery: status, reported percentage, Wh-based computed percentage, health, energy, power, voltage, cycles, technology, manufacturer, model, serial number, and thresholds exposed by sysfs.

See more in [`docs/SCHEMA.md`](docs/SCHEMA.md).

## Configuration

Copy the example:

```bash
mkdir -p ~/.config/battery-auditor
cp examples/config.toml ~/.config/battery-auditor/config.toml
```

Pay special attention to:

```toml
[sampling]
interval_seconds = 2.0

[expected_thresholds.BAT0]
start = 75
stop = 80

[expected_thresholds.BAT1]
start = 75
stop = 80
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ui,dev]'
pytest
ruff check .
```

## Project status

Initial functional version. The collector, SQLite, CLI, systemd units, and UI are ready to use and evolve. Upcoming improvements are listed in [`docs/ROADMAP.md`](docs/ROADMAP.md).
