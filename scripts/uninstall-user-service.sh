#!/usr/bin/env bash
set -euo pipefail

systemctl --user stop thinkpad-energy-manager.service 2>/dev/null || true
systemctl --user stop thinkpad-energy-manager-blackbox.service 2>/dev/null || true
systemctl --user disable thinkpad-energy-manager.service 2>/dev/null || true
systemctl --user disable thinkpad-energy-manager-blackbox.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/thinkpad-energy-manager.service"
rm -f "$HOME/.config/systemd/user/thinkpad-energy-manager-blackbox.service"
systemctl --user daemon-reload

echo "Removed ThinkPad Energy Manager user services."
