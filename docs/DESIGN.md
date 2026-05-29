# Diseño

## Objetivos

1. Medir batería sin introducir carga artificial apreciable.
2. Separar collector, almacenamiento, análisis y UI.
3. Registrar suficiente información para diagnosticar baterías múltiples.
4. Soportar sesiones que acaben por apagado inesperado.
5. Integrarse con TLP sin llamar a TLP en bucle.

## Arquitectura

```text
battery-auditor
├─ collector
│  ├─ lee /sys/class/power_supply
│  ├─ genera eventos
│  ├─ escribe SQLite
│  └─ actualiza heartbeat
│
├─ SQLite
│  ├─ sessions
│  ├─ samples
│  ├─ sample_batteries
│  ├─ power_supplies
│  └─ events
│
├─ CLI
│  ├─ once
│  ├─ collect
│  ├─ sessions
│  ├─ analyze
│  ├─ export
│  └─ tlp-*
│
└─ UI Qt opcional
   ├─ estado actual
   ├─ grabación manual
   ├─ gráficas
   ├─ eventos
   └─ panel TLP
```

## Hot path del collector

El collector solo hace operaciones baratas:

- `read()` de sysfs;
- conversión de strings a enteros/flotantes;
- inserción SQLite;
- heartbeat JSON pequeño.

No usa DBus, UPower, TLP ni comandos externos periódicos.

## Por qué SQLite WAL

SQLite WAL permite escribir muestras sin bloquear lecturas de la UI. El modo normal usa `synchronous=NORMAL`. El modo black-box cambia a `FULL` y fuerza flush por muestra para priorizar la durabilidad frente al consumo mínimo.

## Medición por batería

No se usa solo el porcentaje global. Cada batería tiene:

- porcentaje reportado por kernel;
- porcentaje calculado: `energy_now / energy_full * 100`;
- salud: `energy_full / energy_full_design * 100`;
- potencia instantánea;
- voltaje;
- estado de carga/descarga;
- umbrales de carga expuestos por sysfs.

Esto permite distinguir descarga normal por firmware de caída de voltaje, mala calibración o degradación física.

## Eventos

Eventos iniciales:

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
