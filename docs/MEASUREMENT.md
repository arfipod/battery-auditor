# Measurement methodology

## Profiles

### passive

Use: long-term tracking.

- interval: 10 s by default;
- low impact;
- useful for seeing general trends.

```bash
battery-auditor collect --mode passive --name tracking
```

### diagnostic

Use: normal controlled discharge.

- interval: 2 s by default;
- balance between precision and low impact.

```bash
battery-auditor collect --mode diagnostic --name normal-discharge
```

### blackbox

Use: diagnostics until shutdown or failure.

- interval: 1 s by default;
- SQLite `synchronous=FULL`;
- flush on every sample;
- persistent heartbeat.

```bash
battery-auditor collect --mode blackbox --name final-discharge
```

## Recommended test for a ThinkPad with two batteries

1. Charge to your usual level.
2. Start the collector in `diagnostic` or `blackbox` mode.
3. Disconnect AC.
4. Close the UI if you want minimal measurement noise.
5. Use the machine under a stable load or leave it in a controlled idle state.
6. When finished, export and analyze.

```bash
battery-auditor sessions
battery-auditor analyze
battery-auditor export --format csv --out discharge.csv
```

## What to look for

### Probable bad calibration

- sudden jump in `capacity_percent`;
- gap between `capacity_percent` and `computed_percent`;
- shutdown when `energy_now` still seems sufficient;
- improvement after recalibration.

### Probable physical degradation

- low `health_percent`;
- quick voltage sag under load;
- shutdown while the percentage is still high;
- poor runtime even when the percentage is coherent.

### Normal dual-battery behavior

- one battery discharges first;
- the other remains stable;
- the active battery changes without abrupt energy jumps.

## Avoid contaminating the test

During a serious test:

- do not leave a browser open with live charts;
- do not run `tlp-stat` in a loop;
- do not export data continuously;
- use `diagnostic` or `blackbox` from the CLI/systemd;
- open the UI afterwards.
