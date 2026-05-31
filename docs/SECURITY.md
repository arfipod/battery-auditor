# Security and permissions

## Reading

The collector only needs to read `/sys/class/power_supply`. It normally does not require root.

## Writing

The SQLite database is stored in the user's state directory:

```text
~/.local/state/thinkpad-energy-manager/
```

The Qt hardware controls write a constrained set of sysfs files:

- `/sys/class/backlight/*/brightness`
- `/sys/class/leds/*/brightness`
- `/sys/class/rfkill/*/soft`

When direct user writes are denied, the UI uses `pkexec thinkpad-energy-manager-sysfs-write ...`. The helper refuses other paths and multiline values. Installing the optional polkit policy lets polkit keep authentication for the active session instead of prompting on every write.

## TLP

TLP actions may require `sudo`:

- `tlp-stat`
- `tlp setcharge`
- `tlp recalibrate`

The UI and CLI only run these commands when the user explicitly requests them.

## systemd

The included units are user services, not system services. They do not run as root.
