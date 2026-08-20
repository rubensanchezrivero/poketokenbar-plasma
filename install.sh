#!/usr/bin/env bash
# Installs the daemon, poketokenctl, and the plasmoid into the user's home.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app="$HOME/.local/share/poketokenbar/app"
venv="$HOME/.local/share/poketokenbar/venv"
plasma_major=6
plasmoid_source="$here/plasmoid"
stage=""

case "${1:-}" in
  "") ;;
  --plasma5) plasma_major=5 ;;
  --plasma6) plasma_major=6 ;;
  *)
    echo "usage: $0 [--plasma5|--plasma6]" >&2
    exit 2
    ;;
esac

if [ "$plasma_major" -eq 5 ]; then
  stage="$(mktemp -d)"
  trap 'rm -rf "$stage"' EXIT
  "$here/packaging/prepare-plasma5.sh" "$here/plasmoid" "$stage"
  plasmoid_source="$stage"
fi

echo "==> installing python package to $app"
mkdir -p "$app/poketokenbar"
rsync -a --delete "$here/poketokenbar/" "$app/poketokenbar/"

echo "==> creating venv at $venv"
[ -d "$venv" ] || python3 -m venv "$venv"
"$venv/bin/pip" install -q --upgrade pip
"$venv/bin/pip" install -q orjson || echo "    orjson unavailable; falling back to json"

echo "==> installing poketokenctl"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/poketokenctl" <<EOF
#!/usr/bin/env bash
PYTHONPATH="$app" exec "$venv/bin/python" -m poketokenbar.ctl "\$@"
EOF
chmod +x "$HOME/.local/bin/poketokenctl"

echo "==> installing Plasma $plasma_major plasmoids"
for pkg in org.kde.plasma.poketokenbar org.kde.plasma.poketokenpet; do
  plasmoid_dir="$HOME/.local/share/plasma/plasmoids/$pkg"
  mkdir -p "$plasmoid_dir"
  rsync -a --delete "$plasmoid_source/$pkg/" "$plasmoid_dir/"
done

echo "==> installing systemd unit"
mkdir -p "$HOME/.config/systemd/user"
install -m644 "$here/systemd/poketokend.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now poketokend.service

echo "==> done. check: systemctl --user status poketokend"
