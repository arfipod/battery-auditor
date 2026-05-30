# Installation

## Debian 13 / Trixie

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tlp libxcb-cursor0
```

Clone the repository and create the environment:

```bash
git clone https://github.com/angelrubiodev/battery-auditor.git
cd battery-auditor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ui]'
```

Check that it can read the batteries:

```bash
battery-auditor once
```

## CLI only, no UI

```bash
python -m pip install -e .
```

## UI Qt

The UI uses PySide6. You can install it with pip:

```bash
python -m pip install -e '.[ui]'
```

Or with distribution packages if you have them available.

## systemd user service

```bash
./scripts/install-user-service.sh
systemctl --user enable --now battery-auditor.service
```

The service uses `%h/.local/bin/battery-auditor`. If you install inside a project virtualenv instead of using `pip install --user`, adjust `ExecStart` in:

```text
~/.config/systemd/user/battery-auditor.service
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user restart battery-auditor.service
```
