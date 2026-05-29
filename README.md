# Battery Auditor

Battery Auditor es una herramienta local para Linux que registra, analiza y grafica el comportamiento real de baterías, especialmente en portátiles con varias baterías como los Lenovo ThinkPad con Power Bridge.

El objetivo principal no es ahorrar batería, sino **diagnosticarla sin contaminar demasiado la medición**.

## Qué incluye

- Collector ligero basado en `/sys/class/power_supply`.
- Escritura persistente en SQLite con WAL.
- Modo black-box para pruebas en las que el portátil puede apagarse por falta de batería.
- Detección de eventos: cambio AC, cambio de batería activa, saltos de porcentaje, caída brusca de voltaje, batería baja/crítica y sesiones interrumpidas.
- UI opcional en Python + Qt/PySide6.
- Wrapper manual para TLP: `tlp-stat`, `setcharge`, `recalibrate`.
- Servicios systemd de usuario.
- Exportación CSV/JSON para análisis externo.

## Diseño no invasivo

El collector no ejecuta `tlp-stat`, `upower`, `acpi`, `journalctl` ni comandos externos en bucle. En el camino caliente solo hace:

1. lectura de ficheros pequeños en `/sys/class/power_supply`;
2. cálculo de métricas derivadas;
3. inserción de filas compactas en SQLite.

La UI es opcional. Para una prueba de descarga seria conviene cerrar la UI y dejar solo el collector o el servicio systemd.

## Instalación en Debian 13 / Linux moderno

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tlp

# Para la UI Qt mediante pip:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ui]'
```

Si prefieres instalar PySide6 desde paquetes de Debian, instala los paquetes `python3-pyside6*` disponibles en tu versión y luego:

```bash
python -m pip install -e .
```

## Uso rápido

Leer una muestra puntual:

```bash
battery-auditor once
```

Grabar una sesión diagnóstica:

```bash
battery-auditor collect --mode diagnostic --name descarga-normal
```

Grabar en modo black-box:

```bash
battery-auditor collect --mode blackbox --name descarga-hasta-apagado
```

Listar sesiones:

```bash
battery-auditor sessions
```

Analizar la última sesión:

```bash
battery-auditor analyze
```

Exportar a CSV:

```bash
battery-auditor export --format csv --out descarga.csv
```

Abrir la UI:

```bash
battery-auditor-qt
```

## Modo black-box

El modo black-box está pensado para acotar el instante de apagado por batería:

```bash
battery-auditor collect --mode blackbox --name prueba-final
```

En este modo:

- intervalo por defecto: 1 segundo;
- SQLite `synchronous=FULL`;
- flush por muestra;
- heartbeat persistente por sesión;
- si el equipo se apaga y la sesión queda abierta, el siguiente `recover` la marca como `PROBABLE_POWER_LOSS`.

Al reiniciar:

```bash
battery-auditor recover
battery-auditor analyze
```

El instante exacto de apagado no se puede medir después de que la máquina pierde energía, pero sí se puede acotar al último heartbeat/muestra persistida y al intervalo configurado.

## Servicios systemd de usuario

Instalar unidades:

```bash
./scripts/install-user-service.sh
```

Activar collector normal:

```bash
systemctl --user enable --now battery-auditor.service
```

Iniciar una sesión black-box bajo systemd:

```bash
systemctl --user start battery-auditor-blackbox.service
```

Ver logs:

```bash
journalctl --user -u battery-auditor.service -f
```

Desinstalar unidades:

```bash
./scripts/uninstall-user-service.sh
```

## TLP

Battery Auditor no sustituye a TLP. Lo acompaña.

Comandos útiles:

```bash
battery-auditor tlp-stat battery
battery-auditor tlp-stat config
battery-auditor tlp-setcharge BAT0 75 80
battery-auditor tlp-setcharge BAT1 75 80
battery-auditor tlp-recalibrate BAT0
battery-auditor tlp-recalibrate BAT1
```

Las acciones TLP son manuales y no forman parte del collector periódico para no contaminar la medición.

## Datos registrados

Por cada muestra se guarda:

- timestamp wall-clock e ISO;
- timestamp monotónico;
- estado AC;
- energía total calculada;
- potencia total;
- porcentaje total calculado;
- métricas internas del collector;
- por batería: estado, porcentaje reportado, porcentaje calculado por Wh, salud, energía, potencia, voltaje, ciclos, tecnología, fabricante, modelo, serial y umbrales expuestos por sysfs.

Ver más en [`docs/SCHEMA.md`](docs/SCHEMA.md).

## Configuración

Copia el ejemplo:

```bash
mkdir -p ~/.config/battery-auditor
cp examples/config.toml ~/.config/battery-auditor/config.toml
```

Ajusta especialmente:

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

## Desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ui,dev]'
pytest
ruff check .
```

## Estado del proyecto

Versión inicial funcional. El collector, SQLite, CLI, systemd y UI están preparados para usarse y evolucionar. Las siguientes mejoras están en [`docs/ROADMAP.md`](docs/ROADMAP.md).
