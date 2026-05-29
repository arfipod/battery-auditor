# Estructura del repo

```text
battery-auditor/
├─ src/battery_auditor/
│  ├─ cli.py                    # CLI principal
│  ├─ config.py                 # Configuración TOML y defaults
│  ├─ core/
│  │  ├─ analyzer.py            # Resumen y exportación
│  │  ├─ collector.py           # Loop de grabación
│  │  ├─ database.py            # SQLite WAL y esquema
│  │  ├─ events.py              # Detección de eventos
│  │  ├─ models.py              # Dataclasses de snapshots/eventos
│  │  ├─ sysfs.py               # Lectura de /sys/class/power_supply
│  │  └─ tlp.py                 # Wrapper manual de TLP
│  └─ ui/
│     └─ main.py                # App Qt/PySide6
│
├─ packaging/
│  ├─ desktop/                  # .desktop para la UI
│  └─ systemd/user/             # Servicios systemd de usuario
│
├─ scripts/
│  ├─ install-user-service.sh
│  ├─ uninstall-user-service.sh
│  ├─ record-blackbox.sh
│  └─ run-dev.sh
│
├─ examples/config.toml
├─ docs/
├─ tests/
├─ pyproject.toml
├─ README.md
└─ LICENSE
```
