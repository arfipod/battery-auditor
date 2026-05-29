# Metodología de medición

## Perfiles

### passive

Uso: seguimiento de largo plazo.

- intervalo: 10 s por defecto;
- bajo impacto;
- útil para ver tendencias generales.

```bash
battery-auditor collect --mode passive --name seguimiento
```

### diagnostic

Uso: descarga controlada normal.

- intervalo: 2 s por defecto;
- equilibrio entre precisión y bajo impacto.

```bash
battery-auditor collect --mode diagnostic --name descarga-normal
```

### blackbox

Uso: diagnóstico hasta apagado o fallo.

- intervalo: 1 s por defecto;
- SQLite `synchronous=FULL`;
- flush por muestra;
- heartbeat persistente.

```bash
battery-auditor collect --mode blackbox --name descarga-final
```

## Prueba recomendada para ThinkPad con dos baterías

1. Carga al estado habitual.
2. Arranca el collector en modo `diagnostic` o `blackbox`.
3. Desconecta AC.
4. Cierra la UI si quieres mínima contaminación.
5. Usa el equipo con una carga estable o déjalo en reposo controlado.
6. Al terminar, exporta y analiza.

```bash
battery-auditor sessions
battery-auditor analyze
battery-auditor export --format csv --out descarga.csv
```

## Qué buscar

### Mala calibración probable

- salto brusco de `capacity_percent`;
- diferencia entre `capacity_percent` y `computed_percent`;
- apagado cuando `energy_now` parece suficiente;
- mejora tras recalibración.

### Degradación física probable

- `health_percent` bajo;
- caída rápida de voltaje bajo carga;
- apagado con porcentaje todavía alto;
- poca autonomía incluso con porcentaje coherente.

### Comportamiento normal en doble batería

- una batería descarga primero;
- la otra queda estable;
- hay cambio de batería activa sin saltos bruscos de energía.

## No contaminar la prueba

Durante una prueba seria:

- no dejes navegador abierto con gráficas en vivo;
- no ejecutes `tlp-stat` en bucle;
- no exportes datos continuamente;
- usa `diagnostic` o `blackbox` desde CLI/systemd;
- abre la UI después.
