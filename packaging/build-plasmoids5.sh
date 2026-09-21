#!/usr/bin/env bash
# Builds Plasma 5.27 / Qt 5.15 .plasmoid bundles.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$here/dist/plasma5"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

"$here/packaging/prepare-plasma5.sh" "$here/plasmoid" "$stage"
mkdir -p "$out"

for pkg in org.kde.plasma.poketokenbar org.kde.plasma.poketokenpet; do
  src="$stage/$pkg"
  target="$out/$pkg.plasmoid"
  rm -f "$target"
  (cd "$src" && zip -qr "$target" . -x '*.pyc' '__pycache__/*')
  echo "built $target"
done

cat <<EOF

Install with:
  kpackagetool5 -t Plasma/Applet -i $out/org.kde.plasma.poketokenbar.plasmoid
  kpackagetool5 -t Plasma/Applet -i $out/org.kde.plasma.poketokenpet.plasmoid

Upgrade an existing install with -u instead of -i.

The widgets are only the front end. Install and start the Python daemon with:
  ./install.sh --plasma5
EOF
