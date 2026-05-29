# Integración con TLP

Battery Auditor no sustituye a TLP. Registra datos y ofrece atajos manuales.

## Diagnóstico TLP

```bash
battery-auditor tlp-stat battery
battery-auditor tlp-stat config
battery-auditor tlp-stat system
```

Estos comandos pueden pedir `sudo`.

## Umbrales temporales

```bash
battery-auditor tlp-setcharge BAT0 75 80
battery-auditor tlp-setcharge BAT1 75 80
```

Esto usa `tlp setcharge`. Los cambios son temporales salvo que estén reflejados en la configuración de TLP.

## Recalibración

```bash
battery-auditor tlp-recalibrate BAT0
battery-auditor tlp-recalibrate BAT1
```

Hazlo de una batería cada vez. Durante la recalibración conviene tener el collector grabando para poder comparar antes/después.

## Verificación de umbrales

El collector registra estas rutas si existen:

```text
/sys/class/power_supply/BAT*/charge_control_start_threshold
/sys/class/power_supply/BAT*/charge_control_end_threshold
/sys/class/power_supply/BAT*/charge_start_threshold
/sys/class/power_supply/BAT*/charge_stop_threshold
/sys/class/power_supply/BAT*/charge_behaviour
```

Puedes definir umbrales esperados en `config.toml`:

```toml
[expected_thresholds.BAT0]
start = 75
stop = 80

[expected_thresholds.BAT1]
start = 75
stop = 80
```

Si lo leído desde sysfs no coincide, se registra `THRESHOLD_MISMATCH`.

## Nota de diseño

El collector no llama a `tlp-stat` periódicamente. `tlp-stat` es útil para diagnóstico manual, pero no para una medición de consumo de baja invasividad.
