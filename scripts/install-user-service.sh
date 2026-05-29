#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
cp "$PROJECT_ROOT/packaging/systemd/user/battery-auditor.service" "$UNIT_DIR/"
cp "$PROJECT_ROOT/packaging/systemd/user/battery-auditor-blackbox.service" "$UNIT_DIR/"
systemctl --user daemon-reload

echo "Installed user services."
echo "Enable normal collector:    systemctl --user enable --now battery-auditor.service"
echo "Start blackbox collector:   systemctl --user start battery-auditor-blackbox.service"
echo "View logs:                  journalctl --user -u battery-auditor.service -f"
