# Instalación

## Debian 13 / Trixie

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tlp
```

Clona el repo y crea el entorno:

```bash
git clone https://github.com/angelrubiodev/battery-auditor.git
cd battery-auditor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ui]'
```

Comprueba que lee las baterías:

```bash
battery-auditor once
```

## Solo CLI, sin UI

```bash
python -m pip install -e .
```

## UI Qt

La UI usa PySide6. Puedes instalarla con pip:

```bash
python -m pip install -e '.[ui]'
```

O con paquetes de la distribución si los tienes disponibles.

## systemd user service

```bash
./scripts/install-user-service.sh
systemctl --user enable --now battery-auditor.service
```

El servicio usa `%h/.local/bin/battery-auditor`. Si instalas en un virtualenv de proyecto y no con `pip install --user`, ajusta `ExecStart` en:

```text
~/.config/systemd/user/battery-auditor.service
```

Luego:

```bash
systemctl --user daemon-reload
systemctl --user restart battery-auditor.service
```
