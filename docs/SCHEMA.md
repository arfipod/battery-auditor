# Esquema SQLite

La base de datos por defecto está en:

```text
~/.local/state/battery-auditor/battery-auditor.sqlite3
```

## `sessions`

Una fila por sesión de grabación.

Campos relevantes:

- `id`
- `name`
- `started_at_wall`
- `started_at_iso`
- `ended_at_wall`
- `ended_at_iso`
- `ended_reason`
- `probable_power_loss`
- `last_heartbeat_wall`
- `last_heartbeat_iso`
- `sample_count`
- `config_json`
- `system_json`

## `samples`

Una fila por muestra temporal.

Campos relevantes:

- `session_id`
- `seq`
- `wall_time`
- `wall_iso`
- `monotonic_time`
- `ac_online`
- `total_energy_now_uwh`
- `total_energy_full_uwh`
- `total_energy_full_design_uwh`
- `total_power_now_uw`
- `total_computed_percent`
- `total_health_percent`
- `active_batteries`
- `sample_duration_ms`
- `db_write_duration_ms`
- `collector_rss_kib`
- `collector_user_cpu_seconds`
- `collector_system_cpu_seconds`
- `loop_delay_ms`

## `sample_batteries`

Una fila por batería y muestra.

Campos relevantes:

- `sample_id`
- `session_id`
- `name`
- `present`
- `status`
- `capacity_percent`
- `computed_percent`
- `health_percent`
- `capacity_level`
- `energy_now_uwh`
- `energy_full_uwh`
- `energy_full_design_uwh`
- `power_now_uw`
- `voltage_now_uv`
- `voltage_min_design_uv`
- `cycle_count`
- `technology`
- `manufacturer`
- `model_name`
- `serial_number`
- `charge_control_start_threshold`
- `charge_control_end_threshold`
- `charge_start_threshold`
- `charge_stop_threshold`
- `charge_behaviour`
- `raw_json`

## `power_supplies`

Una fila por fuente de alimentación no batería y muestra.

- `name`
- `type`
- `online`
- `raw_json`

## `events`

Eventos derivados.

- `event_type`
- `severity`
- `battery_name`
- `message`
- `details_json`

## Unidades

Las rutas sysfs de energía/potencia/voltaje suelen venir en micro-unidades:

- `energy_*`: micro-watt-hour (`uWh`)
- `power_now`: micro-watt (`uW`)
- `voltage_now`: microvolt (`uV`)

Battery Auditor conserva estas unidades crudas y calcula vistas en Wh/W/V en CLI/UI cuando hace falta.
