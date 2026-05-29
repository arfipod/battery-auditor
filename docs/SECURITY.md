# Seguridad y permisos

## Lectura

El collector solo necesita leer `/sys/class/power_supply`. Normalmente no requiere root.

## Escritura

La base SQLite se guarda en el directorio de estado del usuario:

```text
~/.local/state/battery-auditor/
```

## TLP

Las acciones TLP pueden requerir `sudo`:

- `tlp-stat`
- `tlp setcharge`
- `tlp recalibrate`

La UI y CLI solo ejecutan estos comandos cuando el usuario lo pide explícitamente.

## systemd

Las unidades incluidas son servicios de usuario, no servicios de sistema. No corren como root.
