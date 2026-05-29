# Contribuir

## Flujo recomendado

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ui,dev]'
pytest
ruff check .
```

## Principios del proyecto

- El collector debe seguir siendo ligero.
- Las integraciones externas no deben entrar en el bucle de muestreo.
- Las mediciones crudas deben conservarse en unidades sysfs.
- La UI no debe ser requisito para grabar.
- Las acciones destructivas o largas, como recalibración, deben ser explícitas.
