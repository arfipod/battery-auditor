#!/usr/bin/env bash
set -euo pipefail

systemctl --user stop battery-auditor.service 2>/dev/null || true
systemctl --user stop battery-auditor-blackbox.service 2>/dev/null || true
systemctl --user disable battery-auditor.service 2>/dev/null || true
systemctl --user disable battery-auditor-blackbox.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/battery-auditor.service"
rm -f "$HOME/.config/systemd/user/battery-auditor-blackbox.service"
systemctl --user daemon-reload

echo "Removed Battery Auditor user services."
