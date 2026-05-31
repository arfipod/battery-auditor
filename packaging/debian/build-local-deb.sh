#!/bin/sh
set -eu

PACKAGE=thinkpad-energy-manager
VERSION=0.1.0-1
MAINTAINER="Angel Rafael Rubio Fernandez <arfipod@users.noreply.github.com>"
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD_DIR="$ROOT_DIR/build/deb"
PKG_DIR="$BUILD_DIR/${PACKAGE}_${VERSION}_all"
OUT_DIR="$ROOT_DIR/dist"
PYTHON_DIST="usr/lib/python3/dist-packages"

rm -rf "$PKG_DIR"
mkdir -p \
  "$PKG_DIR/DEBIAN" \
  "$PKG_DIR/usr/bin" \
  "$PKG_DIR/$PYTHON_DIST" \
  "$PKG_DIR/usr/share/applications" \
  "$PKG_DIR/usr/share/doc/$PACKAGE/docs" \
  "$PKG_DIR/usr/share/doc/$PACKAGE/examples" \
  "$PKG_DIR/usr/share/polkit-1/actions" \
  "$PKG_DIR/usr/lib/systemd/user" \
  "$OUT_DIR"

cp -a "$ROOT_DIR/src/thinkpad_energy_manager" "$PKG_DIR/$PYTHON_DIST/"
find "$PKG_DIR/$PYTHON_DIST/thinkpad_energy_manager" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$PKG_DIR/$PYTHON_DIST/thinkpad_energy_manager" -type f -name '*.pyc' -delete

DIST_INFO="$PKG_DIR/$PYTHON_DIST/thinkpad_energy_manager-0.1.0.dist-info"
mkdir -p "$DIST_INFO"
cat >"$DIST_INFO/METADATA" <<EOF
Metadata-Version: 2.1
Name: thinkpad-energy-manager
Version: 0.1.0
Summary: ThinkPad energy, battery, lighting, radio, and power-management controller for Linux.
Home-page: https://github.com/arfipod/thinkpad-energy-manager
License: MIT
Requires-Python: >=3.11
EOF
cat >"$DIST_INFO/WHEEL" <<EOF
Wheel-Version: 1.0
Generator: build-local-deb
Root-Is-Purelib: true
Tag: py3-none-any
EOF
cat >"$DIST_INFO/entry_points.txt" <<EOF
[console_scripts]
thinkpad-energy-manager = thinkpad_energy_manager.cli:main
thinkpad-energy-manager-qt = thinkpad_energy_manager.ui.main:main
thinkpad-energy-manager-sysfs-write = thinkpad_energy_manager.core.sysfs_writer:main
EOF
printf "dpkg-deb\n" >"$DIST_INFO/INSTALLER"

cat >"$PKG_DIR/usr/bin/thinkpad-energy-manager" <<'EOF'
#!/usr/bin/python3
import sys
from thinkpad_energy_manager.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
EOF
cat >"$PKG_DIR/usr/bin/thinkpad-energy-manager-qt" <<'EOF'
#!/usr/bin/python3
from thinkpad_energy_manager.ui.main import main

if __name__ == "__main__":
    raise SystemExit(main())
EOF
cat >"$PKG_DIR/usr/bin/thinkpad-energy-manager-sysfs-write" <<'EOF'
#!/usr/bin/python3
import sys
from thinkpad_energy_manager.core.sysfs_writer import main

if __name__ == "__main__":
    raise SystemExit(main())
EOF
chmod 755 \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager" \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager-qt" \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager-sysfs-write"

install -m 644 "$ROOT_DIR/packaging/desktop/thinkpad-energy-manager.desktop" \
  "$PKG_DIR/usr/share/applications/thinkpad-energy-manager.desktop"
install -m 644 "$ROOT_DIR/packaging/polkit/com.github.arfipod.thinkpad-energy-manager.policy" \
  "$PKG_DIR/usr/share/polkit-1/actions/com.github.arfipod.thinkpad-energy-manager.policy"
install -m 644 "$ROOT_DIR/packaging/systemd/user/thinkpad-energy-manager.service" \
  "$PKG_DIR/usr/lib/systemd/user/thinkpad-energy-manager.service"
install -m 644 "$ROOT_DIR/packaging/systemd/user/thinkpad-energy-manager-blackbox.service" \
  "$PKG_DIR/usr/lib/systemd/user/thinkpad-energy-manager-blackbox.service"
install -m 644 "$ROOT_DIR/examples/config.toml" \
  "$PKG_DIR/usr/share/doc/$PACKAGE/examples/config.toml"
install -m 644 "$ROOT_DIR/README.md" "$PKG_DIR/usr/share/doc/$PACKAGE/README.md"
install -m 644 "$ROOT_DIR/CHANGELOG.md" "$PKG_DIR/usr/share/doc/$PACKAGE/changelog"
gzip -9n "$PKG_DIR/usr/share/doc/$PACKAGE/changelog"
install -m 644 "$ROOT_DIR/debian/changelog" "$PKG_DIR/usr/share/doc/$PACKAGE/changelog.Debian"
gzip -9n "$PKG_DIR/usr/share/doc/$PACKAGE/changelog.Debian"
install -m 644 "$ROOT_DIR/docs/INSTALL.md" "$PKG_DIR/usr/share/doc/$PACKAGE/docs/INSTALL.md"
install -m 644 "$ROOT_DIR/docs/MEASUREMENT.md" "$PKG_DIR/usr/share/doc/$PACKAGE/docs/MEASUREMENT.md"
install -m 644 "$ROOT_DIR/docs/TLP.md" "$PKG_DIR/usr/share/doc/$PACKAGE/docs/TLP.md"
install -m 644 "$ROOT_DIR/LICENSE" "$PKG_DIR/usr/share/doc/$PACKAGE/copyright"

cat >"$PKG_DIR/DEBIAN/control" <<EOF
Package: $PACKAGE
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: $MAINTAINER
Depends: python3 (>= 3.11), libxcb-cursor0, pkexec, python3-pyqtgraph, python3-pyside6.qtwidgets, tlp
Recommends: python3-dbus-next, x11-xserver-utils, xdg-utils
Homepage: https://github.com/arfipod/thinkpad-energy-manager
Description: ThinkPad battery and energy manager
 ThinkPad Energy Manager records, analyzes, and charts local Linux battery
 behavior, especially on laptops with multiple batteries such as Lenovo
 ThinkPads with Power Bridge.
 .
 This package includes the command-line collector, Qt interface, polkit sysfs
 helper, desktop launcher, and user-level systemd service units.
EOF

find "$PKG_DIR" -type d -exec chmod 755 {} +
find "$PKG_DIR/usr" -type f -exec chmod 644 {} +
chmod 755 \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager" \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager-qt" \
  "$PKG_DIR/usr/bin/thinkpad-energy-manager-sysfs-write"
(cd "$PKG_DIR" && find usr -type f -print0 | sort -z | xargs -0 md5sum >DEBIAN/md5sums)
dpkg-deb --root-owner-group --build "$PKG_DIR" "$OUT_DIR/${PACKAGE}_${VERSION}_all.deb"
