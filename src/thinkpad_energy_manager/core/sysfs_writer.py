from __future__ import annotations

import argparse
import sys
from pathlib import Path


ALLOWED_WRITES = {
    (Path("/sys/class/backlight"), "brightness"),
    (Path("/sys/class/leds"), "brightness"),
    (Path("/sys/class/rfkill"), "soft"),
}


def _resolve_allowed_path(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("Path must be absolute.")

    for root, leaf_name in ALLOWED_WRITES:
        if path.name != leaf_name or path.parent.parent != root:
            continue
        if path.exists():
            return path
        raise ValueError(f"Path does not exist: {path}")
    raise ValueError(f"Refusing to write unsupported sysfs path: {path}")


def write_sysfs_value(path: Path, value: str) -> None:
    resolved = _resolve_allowed_path(path)
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("Value must be a single line.")
    resolved.write_text(f"{value}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a constrained ThinkPad sysfs control value.")
    parser.add_argument("path", type=Path)
    parser.add_argument("value")
    args = parser.parse_args(argv)

    try:
        write_sysfs_value(args.path, args.value)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
