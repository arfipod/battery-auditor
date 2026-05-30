# Contributing

## Recommended workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ui,dev]'
pytest
ruff check .
```

## Project principles

- The collector should remain lightweight.
- External integrations should not enter the sampling loop.
- Raw measurements should be preserved in sysfs units.
- The UI should not be required for recording.
- Destructive or long-running actions, such as recalibration, must be explicit.
