import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid
import org.kde.kirigami as Kirigami

PlasmaExtras.Representation {
    id: full

    readonly property var today: root.appState ? root.appState.today : null
    readonly property var providers: root.appState ? root.appState.providers : ({})
    readonly property var periods: root.appState && root.appState.periods ? root.appState.periods : null
    readonly property var limits: root.appState && root.appState.limits ? root.appState.limits : null
    readonly property var companion: root.appState && root.appState.companion
                                     && root.appState.companion.stage
                                     ? root.appState.companion : null
    readonly property var shopItems: root.appState && root.appState.shop ? root.appState.shop : []
    readonly property var bagItems: root.appState && root.appState.bag ? root.appState.bag : []
    readonly property var dexItems: root.appState && root.appState.dex ? root.appState.dex : []
    readonly property var catchLog: root.appState && root.appState.catch_log ? root.appState.catch_log : []
    readonly property var rarityCounts: root.appState && root.appState.rarity_counts
                                        ? root.appState.rarity_counts : ({})
    readonly property var catchCounts: root.appState && root.appState.catch_counts
                                       ? root.appState.catch_counts : ({})
    // The Pokedex counts species, the catch log counts individuals — 14
    // catches can be 28 species, so the filter pills cannot share a tally.
    readonly property var activeCounts: collectionTabs.currentIndex === 1
                                        ? catchCounts : rarityCounts
    readonly property var burn: root.appState && root.appState.burn ? root.appState.burn : ({})
    readonly property var strings: root.appState && root.appState.strings
                                   ? root.appState.strings : ({})
    readonly property var celebration: root.appState && root.appState.celebration
                                       && root.appState.celebration.kind
                                       ? root.appState.celebration : null
    property string lastUpdatedText: ""
    readonly property var providerStatus: root.appState && root.appState.provider_status
                                          ? root.appState.provider_status : ({})
    // The daemon writes updated_at every poll. If it stops, the numbers freeze
    // while still looking authoritative — so say so rather than lying quietly.
    readonly property bool stale: root.appState && root.appState.updated_at
                                  ? (Date.now() / 1000 - root.appState.updated_at) > 600
                                  : false

    property string rarityFilter: ""
    property int dexPage: 0
    readonly property int dexPageSize: 24

    Layout.minimumWidth: Kirigami.Units.gridUnit * 24
    Layout.minimumHeight: Kirigami.Units.gridUnit * 28

    function levelColor(pct) {
        if (pct >= 95)
            return Kirigami.Theme.negativeTextColor;
        if (pct >= 80)
            return Kirigami.Theme.neutralTextColor;
        return Kirigami.Theme.positiveTextColor;
    }

    function rarityColor(r) {
        if (r === "legendary")
            return "#d4a017";
        if (r === "rare")
            return "#3d8bfd";
        if (r === "uncommon")
            return "#3fb950";
        return "#8b949e";
    }

    function resetIn(iso) {
        if (!iso)
            return "";
        var ms = new Date(iso).getTime() - Date.now();
        if (ms <= 0)
            return i18n("resetting now");
        var mins = Math.floor(ms / 60000);
        var hours = Math.floor(mins / 60);
        var days = Math.floor(hours / 24);
        if (days > 0)
            return i18n("resets in %1d %2h", days, hours % 24);
        if (hours > 0)
            return i18n("resets in %1h %2m", hours, mins % 60);
        return i18n("resets in %1m", mins);
    }

    function grouped(n) {
        return n ? n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
    }

    function compact(n) {
        if (!n)
            return "0";
        if (n >= 1e9)
            return (n / 1e9).toFixed(2).replace(/\.?0+$/, "") + "B";
        if (n >= 1e6)
            return (n / 1e6).toFixed(1).replace(/\.?0+$/, "") + "M";
        if (n >= 1e3)
            return (n / 1e3).toFixed(1).replace(/\.?0+$/, "") + "K";
        return n.toString();
    }

    function money(v) {
        return "$" + (v ? v.toFixed(2) : "0.00");
    }

    function filteredDex() {
        if (!full.rarityFilter)
            return full.dexItems;
        var out = [];
        for (var i = 0; i < full.dexItems.length; i++)
            if (full.dexItems[i].rarity === full.rarityFilter)
                out.push(full.dexItems[i]);
        return out;
    }

    function pagedDex() {
        var all = filteredDex();
        var start = full.dexPage * full.dexPageSize;
        return all.slice(start, start + full.dexPageSize);
    }

    function dexPageCount() {
        return Math.max(1, Math.ceil(filteredDex().length / full.dexPageSize));
    }

    // Every action goes through poketokenctl, so validation and defaults stay
    // in the daemon rather than being duplicated here.
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: function(sourceName) { disconnectSource(sourceName); }
        function run(cmd) { connectSource(cmd); }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        QQC2.TabBar {
            id: tabs
            Layout.fillWidth: true
            QQC2.TabButton { text: i18n("Home") }
            QQC2.TabButton { text: i18n("Shop") }
            QQC2.TabButton { text: i18n("Bag") }
            QQC2.TabButton { text: i18n("Collection") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // ======================= HOME =======================
            QQC2.ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: full.width - Kirigami.Units.gridUnit
                    spacing: Kirigami.Units.smallSpacing

                    // --- celebration banner ---
                    Rectangle {
                        Layout.fillWidth: true
                        visible: full.celebration !== null
                        implicitHeight: celebrationCol.implicitHeight + Kirigami.Units.largeSpacing
                        radius: Kirigami.Units.smallSpacing
                        color: full.celebration && full.celebration.kind === "shiny"
                               ? "#8a6d1f"
                               : Kirigami.Theme.highlightColor

                        ColumnLayout {
                            id: celebrationCol
                            anchors.centerIn: parent
                            width: parent.width - Kirigami.Units.largeSpacing
                            spacing: 0

                            PlasmaComponents.Label {
                                text: full.celebration
                                      ? (full.celebration.kind === "shiny" ? "✨ " : "")
                                        + full.celebration.title
                                      : ""
                                color: "white"
                                font.bold: true
                            }
                            PlasmaComponents.Label {
                                text: full.celebration ? full.celebration.detail : ""
                                color: "white"
                                opacity: 0.9
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // --- companion ---
                    RowLayout {
                        Layout.fillWidth: true
                        visible: full.companion !== null
                        spacing: Kirigami.Units.largeSpacing

                        AnimatedImage {
                            source: full.companion && full.companion.sprite_path
                                    ? "file://" + full.companion.sprite_path : ""
                            visible: full.companion !== null && full.companion.stage === "mon"
                            playing: visible
                            smooth: false
                            fillMode: Image.PreserveAspectFit
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 5
                            Layout.preferredHeight: Kirigami.Units.gridUnit * 5
                        }

                        PlasmaComponents.Label {
                            text: "\u{1F95A}"
                            visible: full.companion !== null && full.companion.stage === "egg"
                            font.pixelSize: Kirigami.Units.gridUnit * 3
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing

                                PlasmaExtras.Heading {
                                    level: 3
                                    text: {
                                        if (!full.companion)
                                            return "";
                                        if (full.companion.stage === "egg")
                                            return i18n("Egg");
                                        return full.companion.name
                                               ? full.companion.name
                                               : "#" + full.companion.species_id;
                                    }
                                }

                                Rectangle {
                                    visible: Boolean(full.companion && full.companion.rarity)
                                    radius: height / 2
                                    color: full.companion ? full.rarityColor(full.companion.rarity) : "grey"
                                    implicitWidth: rarityLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                    implicitHeight: rarityLabel.implicitHeight + 2

                                    PlasmaComponents.Label {
                                        id: rarityLabel
                                        anchors.centerIn: parent
                                        text: full.companion && full.companion.rarity
                                              ? full.companion.rarity.toUpperCase() : ""
                                        color: "white"
                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                        font.bold: true
                                    }
                                }

                                PlasmaComponents.Label {
                                    text: "✨"
                                    visible: Boolean(full.companion && full.companion.is_shiny)
                                }
                            }

                            PlasmaComponents.Label {
                                text: full.companion && full.companion.is_final_form
                                      ? i18n("Final form")
                                      : (full.companion && full.companion.nature
                                         ? full.companion.nature : "")
                                opacity: 0.8
                            }

                            PlasmaComponents.ProgressBar {
                                Layout.fillWidth: true
                                from: 0
                                to: 1
                                value: full.companion
                                       ? (full.companion.stage === "egg"
                                          ? full.companion.egg_progress
                                          : full.companion.stage_progress)
                                       : 0
                            }

                            PlasmaComponents.Label {
                                opacity: 0.7
                                text: {
                                    if (!full.companion)
                                        return "";
                                    if (full.companion.stage === "egg")
                                        return i18n("%1% to hatch",
                                                    Math.round(full.companion.egg_progress * 100));
                                    return i18n("%1 to %2",
                                                full.companion.remaining_text,
                                                full.companion.goal);
                                }
                            }

                            PlasmaComponents.Label {
                                text: full.companion ? full.companion.status_message : ""
                                font.bold: true
                            }
                        }
                    }

                    // --- evolution line strip ---
                    RowLayout {
                        Layout.fillWidth: true
                        visible: Boolean(full.companion && full.companion.evo_line)
                                 && full.companion.evo_line.length > 1
                        spacing: Kirigami.Units.largeSpacing

                        Repeater {
                            model: full.companion && full.companion.evo_line
                                   ? full.companion.evo_line : []

                            ColumnLayout {
                                spacing: 0

                                Image {
                                    source: modelData.sprite_path
                                            ? "file://" + modelData.sprite_path : ""
                                    smooth: false
                                    fillMode: Image.PreserveAspectFit
                                    // Unreached stages are dimmed rather than
                                    // hidden, so the whole line is visible.
                                    opacity: modelData.reached ? 1.0 : 0.35
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                                    Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    width: Kirigami.Units.smallSpacing
                                    height: width
                                    radius: width / 2
                                    visible: modelData.current
                                    color: Kirigami.Theme.highlightColor
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    // --- today ---
                    PlasmaComponents.Label { text: i18n("Today's tokens"); opacity: 0.7 }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        PlasmaExtras.Heading {
                            level: 1
                            text: full.today ? full.today.tokens_compact : "—"
                        }

                        PlasmaComponents.Label {
                            text: full.today ? full.today.tokens_grouped : ""
                            opacity: 0.6
                        }

                        Item { Layout.fillWidth: true }

                        PlasmaComponents.Label {
                            text: full.today ? full.today.cost_text : ""
                            opacity: 0.9
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: Boolean(full.periods && full.periods.week)
                        spacing: Kirigami.Units.smallSpacing

                        PlasmaComponents.Label { text: i18n("This week"); opacity: 0.6 }
                        PlasmaComponents.Label {
                            font.bold: true
                            text: full.periods && full.periods.week
                                  ? full.compact(full.periods.week.tokens) : ""
                        }
                        PlasmaComponents.Label {
                            opacity: 0.6
                            text: full.periods && full.periods.week
                                  ? full.money(full.periods.week.cost) : ""
                        }

                        Item { Layout.preferredWidth: Kirigami.Units.largeSpacing }

                        PlasmaComponents.Label { text: i18n("This month"); opacity: 0.6 }
                        PlasmaComponents.Label {
                            font.bold: true
                            text: full.periods && full.periods.month
                                  ? full.compact(full.periods.month.tokens) : ""
                        }
                        PlasmaComponents.Label {
                            opacity: 0.6
                            text: full.periods && full.periods.month
                                  ? full.money(full.periods.month.cost) : ""
                        }

                        Item { Layout.fillWidth: true }
                    }

                    // --- per-provider breakdown ---
                    Repeater {
                        model: full.providers ? Object.keys(full.providers) : []

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            RowLayout {
                                Layout.fillWidth: true
                                PlasmaComponents.Label { text: modelData; font.bold: true }
                                Item { Layout.fillWidth: true }
                                PlasmaComponents.Label {
                                    text: full.providers[modelData].total_tokens_compact
                                    font.bold: true
                                }
                                PlasmaComponents.Label {
                                    text: full.money(full.providers[modelData].total_cost)
                                    opacity: 0.7
                                }
                            }

                            PlasmaComponents.Label {
                                opacity: 0.6
                                text: i18n("in %1 · out %2 · cache w %3 · cache r %4",
                                           full.compact(full.providers[modelData].input_tokens),
                                           full.compact(full.providers[modelData].output_tokens),
                                           full.compact(full.providers[modelData].cache_creation_tokens),
                                           full.compact(full.providers[modelData].cache_read_tokens))
                            }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    // --- limits ---
                    PlasmaExtras.Heading {
                        level: 4
                        text: full.limits && full.limits.plan
                              ? i18n("Limits (official) · %1", full.limits.plan.toUpperCase())
                              : i18n("Limits (official)")
                    }

                    // Token totals sum every account used on this machine;
                    // limits belong to whichever is logged in. Naming it keeps
                    // that difference visible.
                    PlasmaComponents.Label {
                        visible: text.length > 0
                        opacity: 0.7
                        text: {
                            if (!full.limits || !full.limits.account)
                                return "";
                            var a = full.limits.account;
                            var who = a.email ? a.email : a.display_name;
                            if (!who)
                                return "";
                            return a.organization
                                   ? i18n("for %1 · %2", who, a.organization)
                                   : i18n("for %1", who);
                        }
                    }

                    Repeater {
                        model: {
                            if (!full.limits)
                                return [];
                            var out = [];
                            if (full.limits.session)
                                out.push({ "label": i18n("5-hour session"),
                                           "kind": "session", "w": full.limits.session });
                            if (full.limits.weekly)
                                out.push({ "label": i18n("Weekly"),
                                           "kind": "weekly", "w": full.limits.weekly });
                            return out;
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                PlasmaComponents.Label { text: modelData.label }
                                Item { Layout.fillWidth: true }
                                PlasmaComponents.Label {
                                    text: Math.round(modelData.w.utilization) + "%"
                                    color: full.levelColor(modelData.w.utilization)
                                    font.bold: true
                                }
                            }

                            PlasmaComponents.ProgressBar {
                                Layout.fillWidth: true
                                from: 0
                                to: 100
                                value: modelData.w.utilization
                            }

                            RowLayout {
                                Layout.fillWidth: true

                                PlasmaComponents.Label {
                                    text: full.resetIn(modelData.w.resets_at)
                                    opacity: 0.7
                                }

                                Item { Layout.fillWidth: true }

                                PlasmaComponents.Label {
                                    visible: text.length > 0
                                    opacity: 0.9
                                    color: Kirigami.Theme.neutralTextColor
                                    text: {
                                        var b = full.burn[modelData.kind];
                                        if (!b || !b.eta_text)
                                            return "";
                                        return i18n("at this rate, full at %1", b.eta_text);
                                    }
                                }
                            }
                        }
                    }

                    // --- provider incidents ---
                    Repeater {
                        model: Object.keys(full.providerStatus)

                        RowLayout {
                            Layout.fillWidth: true

                            PlasmaComponents.Label {
                                text: modelData
                                opacity: 0.8
                            }

                            Item { Layout.fillWidth: true }

                            PlasmaComponents.Label {
                                text: full.providerStatus[modelData].label
                                color: full.providerStatus[modelData].severity === "crit"
                                       ? Kirigami.Theme.negativeTextColor
                                       : Kirigami.Theme.neutralTextColor
                                font.bold: true
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // ======================= SHOP =======================
            QQC2.ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: full.width - Kirigami.Units.gridUnit
                    spacing: Kirigami.Units.smallSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        PlasmaComponents.Label { text: i18n("Spendable tokens"); opacity: 0.7 }
                        PlasmaExtras.Heading {
                            level: 1
                            text: full.companion ? full.companion.spendable_text : "0"
                        }
                        PlasmaComponents.Label {
                            text: i18n("Spend the tokens you've used on items.")
                            opacity: 0.6
                        }
                    }

                    Repeater {
                        model: full.shopItems

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Image {
                                source: modelData.sprite_path
                                        ? "file://" + modelData.sprite_path : ""
                                visible: modelData.sprite_path !== ""
                                smooth: false
                                fillMode: Image.PreserveAspectFit
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 1.5
                                Layout.preferredHeight: Kirigami.Units.gridUnit * 1.5
                            }

                            PlasmaComponents.Label {
                                text: modelData.emoji
                                visible: modelData.sprite_path === ""
                                font.pixelSize: Kirigami.Units.gridUnit
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                RowLayout {
                                    spacing: Kirigami.Units.smallSpacing

                                    PlasmaComponents.Label {
                                        text: modelData.label
                                        font.bold: true
                                    }

                                    PlasmaComponents.Label {
                                        text: i18n("Owned ×%1", modelData.owned_count)
                                        visible: modelData.owned_count > 0
                                        opacity: 0.6
                                    }

                                    Rectangle {
                                        visible: modelData.badge !== ""
                                        radius: height / 2
                                        color: full.rarityColor(modelData.badge.toLowerCase())
                                        implicitWidth: badgeLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                        implicitHeight: badgeLabel.implicitHeight + 2

                                        PlasmaComponents.Label {
                                            id: badgeLabel
                                            anchors.centerIn: parent
                                            text: modelData.badge
                                            color: "white"
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                            font.bold: true
                                        }
                                    }
                                }

                                PlasmaComponents.Label {
                                    text: modelData.description
                                    opacity: 0.7
                                    wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }

                                PlasmaComponents.Label {
                                    text: i18n("Price %1", modelData.price_text)
                                    opacity: 0.6
                                }
                            }

                            QQC2.Button {
                                text: modelData.owned ? i18n("Owned") : i18n("Buy")
                                enabled: modelData.affordable
                                onClicked: runner.run("poketokenctl buy " + modelData.key)
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // ======================= BAG =======================
            ColumnLayout {
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    text: i18n("Your bag is empty.")
                    visible: full.bagItems.length === 0
                    opacity: 0.7
                }

                Repeater {
                    model: full.bagItems

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Image {
                            source: modelData.sprite_path
                                    ? "file://" + modelData.sprite_path : ""
                            visible: modelData.sprite_path !== ""
                            smooth: false
                            fillMode: Image.PreserveAspectFit
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 1.5
                            Layout.preferredHeight: Kirigami.Units.gridUnit * 1.5
                        }

                        PlasmaComponents.Label {
                            text: modelData.emoji
                            visible: modelData.sprite_path === ""
                            font.pixelSize: Kirigami.Units.gridUnit
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            PlasmaComponents.Label {
                                text: modelData.label + " ×" + modelData.count
                                font.bold: true
                            }
                            PlasmaComponents.Label {
                                text: modelData.description
                                opacity: 0.7
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                            PlasmaComponents.Label {
                                text: modelData.effect
                                opacity: 0.6
                            }
                        }

                        QQC2.Button {
                            text: modelData.passive ? i18n("Active") : i18n("Use")
                            enabled: modelData.usable
                            onClicked: runner.run("poketokenctl use " + modelData.key)
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }

            // ==================== COLLECTION ====================
            ColumnLayout {
                spacing: Kirigami.Units.smallSpacing

                QQC2.TabBar {
                    id: collectionTabs
                    Layout.fillWidth: true
                    QQC2.TabButton { text: i18n("Pokédex") }
                    QQC2.TabButton { text: i18n("Catch log") }
                }

                // rarity filters, shared by both sub-tabs
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Repeater {
                        model: ["legendary", "rare", "uncommon", "common"]

                        QQC2.Button {
                            checkable: true
                            checked: full.rarityFilter === modelData
                            text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                                  + " " + (full.activeCounts[modelData] !== undefined
                                           ? full.activeCounts[modelData] : 0)
                            onClicked: {
                                // Clicking the active filter clears it.
                                full.rarityFilter = full.rarityFilter === modelData ? "" : modelData;
                                full.dexPage = 0;
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: collectionTabs.currentIndex

                    // ---- Pokédex grid ----
                    ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing

                        PlasmaComponents.Label {
                            text: i18n("%1 species", full.dexItems.length)
                            font.bold: true
                        }

                        PlasmaComponents.Label {
                            text: i18n("No Pokémon caught yet!")
                            visible: full.dexItems.length === 0
                            opacity: 0.7
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: Kirigami.Units.smallSpacing
                            rowSpacing: Kirigami.Units.smallSpacing

                            Repeater {
                                model: full.pagedDex()

                                ColumnLayout {
                                    spacing: 0

                                    RowLayout {
                                        spacing: 2

                                        PlasmaComponents.Label {
                                            text: "#" + modelData.final_id
                                            opacity: 0.6
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                        }

                                        // Backed only by the companion being
                                        // raised: buying an egg discards it and
                                        // this square disappears, so it is
                                        // marked rather than shown as permanent.
                                        Rectangle {
                                            visible: modelData.is_raising === true
                                            radius: height / 2
                                            color: Kirigami.Theme.highlightColor
                                            implicitWidth: raisingTag.implicitWidth + 6
                                            implicitHeight: raisingTag.implicitHeight + 2

                                            PlasmaComponents.Label {
                                                id: raisingTag
                                                anchors.centerIn: parent
                                                text: i18n("RAISING")
                                                color: "white"
                                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                font.bold: true
                                            }
                                        }
                                    }

                                    Image {
                                        source: modelData.sprite_path
                                                ? "file://" + modelData.sprite_path : ""
                                        smooth: false
                                        fillMode: Image.PreserveAspectFit
                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2.5
                                        Layout.preferredHeight: Kirigami.Units.gridUnit * 2.5
                                    }

                                    PlasmaComponents.Label {
                                        text: (modelData.is_shiny ? "✨" : "")
                                              + (modelData.name ? modelData.name
                                                                : "#" + modelData.final_id)
                                        elide: Text.ElideRight
                                        // Not permanent yet: buying an egg
                                        // discards the companion and this
                                        // square disappears.
                                        opacity: modelData.is_raising ? 0.65 : 1.0
                                        font.italic: modelData.is_raising === true
                                        Layout.maximumWidth: Kirigami.Units.gridUnit * 4
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: full.dexPageCount() > 1

                            QQC2.Button {
                                text: "‹"
                                enabled: full.dexPage > 0
                                onClicked: full.dexPage = full.dexPage - 1
                            }

                            Item { Layout.fillWidth: true }

                            PlasmaComponents.Label {
                                text: (full.dexPage + 1) + " / " + full.dexPageCount()
                            }

                            Item { Layout.fillWidth: true }

                            QQC2.Button {
                                text: "›"
                                enabled: full.dexPage < full.dexPageCount() - 1
                                onClicked: full.dexPage = full.dexPage + 1
                            }
                        }
                    }

                    // ---- Catch log ----
                    QQC2.ScrollView {
                        clip: true
                        contentWidth: availableWidth

                        ColumnLayout {
                            width: full.width - Kirigami.Units.gridUnit
                            spacing: Kirigami.Units.smallSpacing

                            PlasmaComponents.Label {
                                text: i18n("%1 total", full.catchLog.length)
                                font.bold: true
                            }

                            Repeater {
                                model: full.catchLog

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: full.rarityFilter === ""
                                             || modelData.rarity === full.rarityFilter
                                    spacing: 2

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Rectangle {
                                            radius: height / 2
                                            color: full.rarityColor(modelData.rarity)
                                            implicitWidth: logRarity.implicitWidth + Kirigami.Units.smallSpacing * 2
                                            implicitHeight: logRarity.implicitHeight + 2

                                            PlasmaComponents.Label {
                                                id: logRarity
                                                anchors.centerIn: parent
                                                text: modelData.rarity.toUpperCase()
                                                color: "white"
                                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                font.bold: true
                                            }
                                        }

                                        Rectangle {
                                            visible: modelData.raising
                                            radius: height / 2
                                            color: Kirigami.Theme.highlightColor
                                            implicitWidth: raisingLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                            implicitHeight: raisingLabel.implicitHeight + 2

                                            PlasmaComponents.Label {
                                                id: raisingLabel
                                                anchors.centerIn: parent
                                                text: i18n("RAISING")
                                                color: "white"
                                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                font.bold: true
                                            }
                                        }

                                        Item { Layout.fillWidth: true }

                                        PlasmaComponents.Label {
                                            text: modelData.nature ? modelData.nature : ""
                                            opacity: 0.7
                                        }
                                    }

                                    RowLayout {
                                        spacing: Kirigami.Units.smallSpacing

                                        Repeater {
                                            model: modelData.chain

                                            RowLayout {
                                                spacing: 2

                                                PlasmaComponents.Label {
                                                    text: "→"
                                                    visible: index > 0
                                                    opacity: 0.5
                                                }

                                                ColumnLayout {
                                                    spacing: 0
                                                    Image {
                                                        source: modelData.sprite_path
                                                                ? "file://" + modelData.sprite_path : ""
                                                        smooth: false
                                                        fillMode: Image.PreserveAspectFit
                                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                                                        Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                                                    }
                                                    PlasmaComponents.Label {
                                                        text: modelData.name
                                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                    }
                                                }
                                            }
                                        }

                                        Item { Layout.fillWidth: true }
                                    }

                                    PlasmaComponents.Label {
                                        text: modelData.raised_text
                                        visible: text.length > 0
                                        opacity: 0.6
                                    }

                                    Kirigami.Separator { Layout.fillWidth: true }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }

        // ---- footer ----
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.Label {
                visible: full.stale
                text: i18n("⚠ Data is stale — is poketokend running?")
                color: Kirigami.Theme.neutralTextColor
            }

            PlasmaComponents.Label {
                visible: !full.stale && text.length > 0
                opacity: 0.6
                text: {
                    if (!root.appState || !root.appState.updated_at)
                        return "";
                    var age = Math.round(Date.now() / 1000 - root.appState.updated_at);
                    if (age < 60)
                        return i18n("Updated just now");
                    return i18n("Updated %1 min ago", Math.round(age / 60));
                }
            }

            QQC2.ToolButton {
                icon.name: "view-refresh"
                text: i18n("Refresh")
                display: QQC2.AbstractButton.TextBesideIcon
                onClicked: runner.run("poketokenctl refresh")
            }

            QQC2.ToolButton {
                icon.name: "configure"
                text: i18n("Settings")
                display: QQC2.AbstractButton.IconOnly
                // Same dialog as right-click > Configure, but discoverable.
                onClicked: Plasmoid.internalAction("configure").trigger()

                QQC2.ToolTip.visible: hovered
                QQC2.ToolTip.text: i18n("Settings")
            }

            Item { Layout.fillWidth: true }

            PlasmaComponents.Label {
                visible: text.length > 0
                text: root.stateError.length > 0
                      ? root.stateError
                      : (root.appState && root.appState.errors.length > 0
                         ? root.appState.errors.join(", ")
                         : "")
                color: Kirigami.Theme.negativeTextColor
                elide: Text.ElideRight
                Layout.maximumWidth: full.width / 2
            }
        }
    }
}
