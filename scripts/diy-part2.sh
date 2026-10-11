#!/bin/bash
# Patch feed packages after feeds are updated and installed.
set -euo pipefail

# Keep the honk config, init script and LuCI app, but leave the honk-core
# binary and v2ray-geoip (geoip.dat) out of the firmware to save flash space.
honk_makefile="feeds/honk/honk/Makefile"
if [ ! -f "$honk_makefile" ]; then
  echo "::error::$honk_makefile not found"
  exit 1
fi

geoip_dep='[[:space:]]\+v2ray-geoip([[:space:]]|$)'
core_install='\$\(INSTALL_BIN\)[[:space:]]+\$\(PKG_BUILD_DIR\)/honk-core[[:space:]]'

if ! grep -Eq "$geoip_dep" "$honk_makefile"; then
  echo "::error::honk Makefile no longer depends on v2ray-geoip; review the patch"
  exit 1
fi
if ! grep -Eq "$core_install" "$honk_makefile"; then
  echo "::error::honk Makefile no longer installs honk-core this way; review the patch"
  exit 1
fi

sed -i -E \
  -e "s/$geoip_dep/\\1/" \
  -e "\\#$core_install#d" \
  "$honk_makefile"

if grep -Eq "$geoip_dep|$core_install" "$honk_makefile"; then
  echo "::error::Failed to strip honk-core and v2ray-geoip from $honk_makefile"
  exit 1
fi

echo "=== patched honk package ==="
grep -nE 'DEPENDS|v2ray|honk-core' "$honk_makefile"
