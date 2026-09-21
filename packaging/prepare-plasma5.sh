#!/usr/bin/env bash
# Generate Plasma 5.27 / Qt 5.15 plasmoid sources from the Plasma 6 sources.
#
# Keeping this as a small, mechanical compatibility layer avoids maintaining a
# second copy of the large FullRepresentation.qml file.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 SOURCE_DIR DESTINATION_DIR" >&2
  exit 2
fi

source_dir="$1"
destination_dir="$2"

if [ ! -d "$source_dir/org.kde.plasma.poketokenbar" ] \
    || [ ! -d "$source_dir/org.kde.plasma.poketokenpet" ]; then
  echo "source directory does not contain the PokeTokenBar plasmoids: $source_dir" >&2
  exit 1
fi

if [ -e "$destination_dir" ] && [ -n "$(find "$destination_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "destination directory must be empty: $destination_dir" >&2
  exit 1
fi

mkdir -p "$destination_dir"
cp -a "$source_dir/org.kde.plasma.poketokenbar" "$destination_dir/"
cp -a "$source_dir/org.kde.plasma.poketokenpet" "$destination_dir/"

while IFS= read -r -d '' qml; do
  sed -i \
    -e 's/^import QtQuick$/import QtQuick 2.15/' \
    -e 's/^import QtQuick.Controls as QQC2$/import QtQuick.Controls 2.15 as QQC2/' \
    -e 's/^import QtQuick.Layouts$/import QtQuick.Layouts 1.15/' \
    -e 's/^import Qt.labs.platform as Platform$/import Qt.labs.platform 1.1 as Platform/' \
    -e 's/^import org\.kde\.plasma\.plasmoid$/import org.kde.plasma.plasmoid 2.0/' \
    -e 's/^import org\.kde\.plasma\.components as PlasmaComponents$/import org.kde.plasma.components 3.0 as PlasmaComponents/' \
    -e 's/^import org\.kde\.plasma\.core as PlasmaCore$/import org.kde.plasma.core 2.0 as PlasmaCore/' \
    -e 's/^import org\.kde\.plasma\.extras as PlasmaExtras$/import org.kde.plasma.extras 2.0 as PlasmaExtras/' \
    -e 's/^import org\.kde\.plasma\.plasma5support as Plasma5Support$/import org.kde.plasma.core 2.0 as Plasma5Support/' \
    -e 's/^import org\.kde\.kirigami as Kirigami$/import org.kde.kirigami 2.20 as Kirigami/' \
    -e 's/^import org\.kde\.kcmutils as KCM$/import org.kde.kcm 1.6 as KCM/' \
    -e 's/^import org\.kde\.plasma\.configuration$/import org.kde.plasma.configuration 2.0/' \
    "$qml"
done < <(find "$destination_dir" -type f -name '*.qml' -print0)

for metadata in "$destination_dir"/*/metadata.json; do
  sed -i \
    -e 's/  "X-Plasma-API-Minimum-Version": "6\.0",/  "X-Plasma-API": "declarativeappletscript",\n  "X-Plasma-MainScript": "ui\/main.qml"/' \
    -e '/  "KPackageStructure": "Plasma\/Applet"/d' \
    "$metadata"
done

panel="$destination_dir/org.kde.plasma.poketokenbar/contents"
pet="$destination_dir/org.kde.plasma.poketokenpet/contents"

# Plasma 5 exposes the applet attached object to a regular Item. Plasma 6's
# PlasmoidItem convenience type and its unqualified properties do not exist.
sed -i \
  -e 's/^PlasmoidItem {/Item {/' \
  -e 's/^    compactRepresentation:/    Plasmoid.compactRepresentation:/' \
  -e 's/^    fullRepresentation:/    Plasmoid.fullRepresentation:/' \
  "$panel/ui/main.qml"

sed -i \
  -e '/^import QtQuick.Layouts 1\.15$/a import org.kde.plasma.plasmoid 2.0' \
  -e 's/root\.expanded/Plasmoid.expanded/g' \
  "$panel/ui/CompactRepresentation.qml"

sed -i \
  -e 's/Plasmoid\.internalAction("configure")/Plasmoid.action("configure")/' \
  "$panel/ui/FullRepresentation.qml"

# SimpleKCM already inherits a title property in Plasma 5. Redeclaring it is a
# construction error there, while Plasma 6's applet config loader expects it.
sed -i '/^    property string title: ""$/d' "$panel/ui/configGeneral.qml"

sed -i \
  -e 's/^PlasmoidItem {/Item {/' \
  -e 's/^    preferredRepresentation: fullRepresentation$/    Plasmoid.preferredRepresentation: Plasmoid.fullRepresentation/' \
  -e 's/^    fullRepresentation:/    Plasmoid.fullRepresentation:/' \
  "$pet/ui/main.qml"
