# Test plan

## Unit tests

```bash
pytest
```

Cases:

- sysfs reads from fixture;
- Wh-based percentage calculation;
- SQLite insert;
- open-session recovery;
- export.

## Smoke test on real hardware

```bash
battery-auditor once
battery-auditor collect --mode diagnostic --duration 10 --name smoke-test
battery-auditor sessions
battery-auditor analyze
battery-auditor export --format csv --out smoke.csv
```

## Controlled black-box test

1. Charge the machine to a safe level.
2. Run:

```bash
battery-auditor collect --mode blackbox --name blackbox-smoke --duration 60
```

3. Confirm:

```bash
battery-auditor analyze
```

## Recovery test

Simulate a collector interruption:

```bash
battery-auditor collect --mode diagnostic --name recover-test
# In another terminal:
pkill -f 'battery_auditor.cli.*collect'
battery-auditor recover
battery-auditor analyze
```

`PROBABLE_POWER_LOSS` or an interrupted session should appear.
