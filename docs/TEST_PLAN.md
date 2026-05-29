# Plan de pruebas

## Pruebas unitarias

```bash
pytest
```

Casos:

- lectura de sysfs desde fixture;
- cálculo de porcentaje por Wh;
- inserción SQLite;
- recuperación de sesión abierta;
- exportación.

## Prueba de humo en equipo real

```bash
battery-auditor once
battery-auditor collect --mode diagnostic --duration 10 --name smoke-test
battery-auditor sessions
battery-auditor analyze
battery-auditor export --format csv --out smoke.csv
```

## Prueba black-box controlada

1. Cargar el equipo a un nivel seguro.
2. Ejecutar:

```bash
battery-auditor collect --mode blackbox --name blackbox-smoke --duration 60
```

3. Confirmar:

```bash
battery-auditor analyze
```

## Prueba de recuperación

Simular un corte del collector:

```bash
battery-auditor collect --mode diagnostic --name recover-test
# En otra terminal:
pkill -f 'battery_auditor.cli.*collect'
battery-auditor recover
battery-auditor analyze
```

Debe aparecer `PROBABLE_POWER_LOSS` o sesión interrumpida.
