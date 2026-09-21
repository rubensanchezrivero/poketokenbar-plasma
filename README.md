<div align="center">

<img src="assets/logo.png" width="300" alt="PokeTokenBar + KDE Plasma">

# PokeTokenBar for Plasma

**Your AI coding tokens, hatched into Pokémon — right in your KDE panel.**

[![Release](https://img.shields.io/github/v/release/rubensanchezrivero/poketokenbar-plasma?color=444d56&label=release)](https://github.com/rubensanchezrivero/poketokenbar-plasma/releases)
[![KDE Plasma](https://img.shields.io/badge/KDE%20Plasma-6-1d99f3?logo=kde&logoColor=white)](https://kde.org/plasma-desktop/)
[![Qt](https://img.shields.io/badge/Qt-6-41cd52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Arch](https://img.shields.io/badge/Arch-PKGBUILD-1793d1?logo=archlinux&logoColor=white)](packaging/PKGBUILD)
[![License](https://img.shields.io/badge/license-MIT-3fb950)](LICENSE)
[![Upstream](https://img.shields.io/badge/upstream-chattymin%2FPokeTokenBar-ea4aaa?logo=github&logoColor=white)](https://github.com/chattymin/PokeTokenBar)

**An unofficial Linux port of [PokeTokenBar](https://github.com/chattymin/PokeTokenBar) by [chattymin](https://github.com/chattymin).**

<img src="assets/panel.gif" width="360" alt="The panel widget: an animated companion beside the 5-hour and weekly limit percentages">

</div>

PokeTokenBar for Plasma turns the AI coding tokens you're already burning — Claude Code and Codex — into a growing **Pokémon companion** in your KDE panel. Spend tokens, hatch an egg, evolve it through its real evolution line, graduate it into your Pokédex, and start again. Underneath the companion it's a precise usage tracker — today's spend, cost, and official 5-hour / weekly limits, read straight from your local logs.

> Token usage is read directly from local Claude Code and Codex data (`totalTokens` = input + output + cache, local date) — no external CLI needed. Unofficial, non-commercial Pokémon fan project — see [License & disclaimer](#license--disclaimer).

## Why

- **The usage tracker you actually enjoy opening.** Your spend raises a Pokémon that hatches, evolves, graduates, and fills a Pokédex — and every shiny is a reason to check back.
- See today's token spend & cost at a glance — no dashboard, no browser tab.
- Track official **5-hour / weekly** limits with reset countdowns and a burn-rate forecast for when you'll hit them.

## How it works

1. 🥚 **Code as usual.** The tokens you burn in Claude Code or Codex incubate an egg — nothing extra to run.
2. 🐣 **Hatch.** Eggs hatch into Pokémon with real evolution lines from [PokéAPI](https://pokeapi.co/) — any Gen 1–5 line (328 possible starts), weighted by the official capture rate: commons hatch often, a legendary is rare. It appears in your **Collection** immediately while you raise it. Every hatch rolls one of 25 natures — and once in a rare while, the egg hatches **✨ Shiny**.
3. ⚡ **Evolve.** Keep coding and it grows through its actual evolution tree, with a celebration banner at each step.
4. 🎓 **Graduate & collect.** Final form + threshold permanently archives it in your **Pokédex** — rarer takes longer — and a fresh egg arrives.
5. 🍬 **Max out, get a candy.** Fill a 5-hour or weekly usage limit and you earn **Rare Candy** — spend it from the **Bag** to grow your current Pokémon.
6. 🛒 **Spend at the Shop.** Every token you've used is spendable currency — buy **Rare Candy**, a **Mint** that re-rolls your Pokémon's nature, a **Shiny Charm** that permanently raises your shiny odds, or an egg to send off your current companion and start over.

## Tour

<table>
<tr>
<td width="55%" valign="top">
<h3>🏠 Home</h3>
Your companion with its rarity, nature, and evolution line — dimmed forms are the ones it hasn't reached yet. Today's tokens and cost, this week, this month, and a per-provider breakdown of input, output, and cache. Then the official limits with reset countdowns and a burn-rate forecast.
</td>
<td width="45%" align="center"><img src="assets/popup-home.png" width="300" alt="Home tab"></td>
</tr>
<tr>
<td width="45%" align="center"><img src="assets/popup-shop.png" width="300" alt="Shop tab"></td>
<td width="55%" valign="top">
<h3>🛒 Shop &amp; Bag</h3>
Spend the tokens you've already used. Rare Candy, Mint, Shiny Charm, and three grades of egg — plain, Uncommon-guaranteed, and Rare-guaranteed. The Bag shows what you're holding and what each item does.
</td>
</tr>
<tr>
<td width="55%" valign="top">
<h3>📕 Collection</h3>
A species-level Pokédex with rarity filters and paging — every form you've actually been, including the one you're raising right now. The Catch log records each individual instead: its full evolution chain, its nature, and how long it took.
</td>
<td width="45%" align="center"><img src="assets/popup-collection.png" width="300" alt="Collection tab"></td>
</tr>
</table>

### In your panel

An animated Gen-V sprite lives next to your 5-hour and weekly limit percentages, coloured green, yellow, or red as you approach the cap. Add today's tokens or cost — or turn everything off for a character-only panel.

### 🐾 Let it live on your desktop

A second widget puts your companion on the desktop at any size from 48 to 192px. Hover it for its mood, click for progress, right-click for a menu — and limit alerts can appear as a speech bubble above it.

## Also in the box

- **Burn-rate forecast** — projects when the current 5-hour window hits 100%, from the utilization trend.
- **Desktop notifications** — hatch, evolution, graduation, and limit warnings via `notify-send`.
- **Rare Candy grants** — fill a limit window and earn candy; weekly pays more than a session.
- **Ditto disguise** — once in a rare while a common hatch is secretly a Ditto, and reveals itself when it "evolves".
- **Provider status** — Claude and OpenAI incidents surface in the popup when they happen.
- **Save export / import** — move your Pokédex, tokens, bag, and companion between machines.
- **Stale detection** — if the daemon stops, the panel says so instead of quietly freezing.
- **Four languages** — English, 한국어, 日本語, Español.

## Works with

| | Status |
|---|---|
| **Claude Code** | ✅ verified against a real 559 MB log corpus |
| **Codex** | ✅ verified against upstream's own test fixtures |
| Gemini CLI, Antigravity, OpenCode, Hermes Agent, Cursor, Grok CLI, Copilot CLI, Kiro CLI | ❌ not ported — see [What's missing](#whats-missing) |

Official limits are read for Claude accounts.

## Install

### Requirements

- KDE Plasma 6 (developed on 6.7.4, Qt 6.11), or Plasma 5.27 with Qt 5.15
- Python 3.12+
- `libnotify` for notifications (optional)
- `python-orjson` for ~2× faster parsing (optional)

### Arch / CachyOS / EndeavourOS

```bash
git clone https://github.com/rubensanchezrivero/poketokenbar-plasma.git
cd poketokenbar-plasma/packaging
makepkg -si
systemctl --user enable --now poketokend
```

Installs system-wide with no venv. This package currently targets Plasma 6;
Plasma 5 users should use the compatibility installer below. Remove with
`sudo pacman -R poketokenbar-plasma`.

### Any other distro — Plasma 6

```bash
git clone https://github.com/rubensanchezrivero/poketokenbar-plasma.git
cd poketokenbar-plasma
./install.sh
```

Self-contained: creates its own venv and installs everything under `$HOME`.

### KDE Plasma 5.27

Plasma 5 uses Qt 5 and different QML APIs. A compatibility build is included
for systems that cannot upgrade to Plasma 6:

```bash
./install.sh --plasma5
```

This installs the same Python daemon and generated Plasma 5 versions of both
widgets. The Plasma 6 source remains canonical, so fixes to the UI are shared
between both builds. Plasma versions older than 5.27 are not supported. If the
widget browser was already open or an incompatible copy was already loaded,
restart Plasma Shell (or log out and back in) after installation.

### Widgets only

```bash
./packaging/build-plasmoids.sh
kpackagetool6 -t Plasma/Applet -i dist/org.kde.plasma.poketokenbar.plasmoid
kpackagetool6 -t Plasma/Applet -i dist/org.kde.plasma.poketokenpet.plasmoid
```

Then right-click your panel → **Add Widgets** → **PokeTokenBar**.
For the desktop pet, add **PokeTokenBar Pet** to your desktop.

For Plasma 5, build and install the compatibility bundles instead:

```bash
./packaging/build-plasmoids5.sh
kpackagetool5 -t Plasma/Applet -i dist/plasma5/org.kde.plasma.poketokenbar.plasmoid
kpackagetool5 -t Plasma/Applet -i dist/plasma5/org.kde.plasma.poketokenpet.plasmoid
```

## Data sources

| Path | Read for |
|---|---|
| `~/.claude/projects/**/*.jsonl` | Claude Code usage (also `~/.config/claude/projects`, `$CLAUDE_CONFIG_DIR`) |
| `~/.codex/sessions/**/*.jsonl` | Codex usage |
| `~/.claude/.credentials.json` | OAuth token for official limits |
| `~/.claude.json` | which account those limits belong to |
| [PokéAPI](https://pokeapi.co/) + [PokeAPI/sprites](https://github.com/PokeAPI/sprites) | species, evolution chains, sprites — fetched at runtime, cached locally |

Where the app keeps its own state:

| Path | Contents |
|---|---|
| `~/.local/state/poketokenbar/state.json` | what the widgets render |
| `~/.config/poketokenbar/config.json` | settings |
| `~/.local/share/poketokenbar/companion.json` | your save |
| `~/.cache/poketokenbar/` | scan cache, sprites, PokéAPI data |

## Privacy & permissions

- **Everything is local.** Token counts come from log files already on your disk. No telemetry, no analytics, no account of ours.
- **Three network calls, all optional.** PokéAPI for species data, GitHub for sprites, and `api.anthropic.com/api/oauth/usage` for your official limits using the token Claude Code already stored. If any fail, token counts keep working.
- **No credentials leave your machine.** The OAuth token is read from `~/.claude/.credentials.json` and sent only to Anthropic.
- **Nothing is bundled.** No Pokémon sprites or data ship in this repository; they're fetched at runtime and cached under `~/.cache`.

### If you use several Claude accounts

Session logs carry **no account marker**, so token totals from every account on the machine are summed and cannot be separated. Limits come from whichever account is currently logged in — so the popup names that account beside them. To keep accounts apart, give each its own `CLAUDE_CONFIG_DIR`.

## What's missing

Compared to the macOS original:

- **Eight of the ten usage providers.** Only Claude Code and Codex are ported. I have no data for the others, so porting them would mean shipping parsers nobody could verify. The provider interface is unchanged — each is one file when someone who uses one wants to add it.
- In-app updater, crash reporter, and Keychain handling — macOS concepts with no Linux equivalent, or unnecessary here.
- A diagnostics / log viewer.

## How this was built

**This port was vibe-coded.** Essentially all of the Python and QML was written by Claude (Anthropic's Claude Code) in a single long session, using the upstream Swift source as the specification, with me steering, testing on my own machine, and sending screenshots when the port drifted.

What that means in practice:

- **It's verified where verification was possible.** The Claude Code parser was checked against my real 559 MB of logs; the Codex parser matches upstream's own test fixtures exactly (312,814 and 369,215). There are 265 tests.
- **Several bugs were only caught by looking at the screen.** The panel silently failed for an entire iteration because Qt blocks `XMLHttpRequest` on `file://`; the Pokédex hid the active companion; the settings dialog opened empty because Plasma wants a `cfg_<key>Default` property. No test caught any of them.
- **Read the code before trusting it.** It only reads local logs and one Anthropic endpoint — but confirm that yourself.

## Credits

**All original design, game balance, and the idea belong to [chattymin](https://github.com/chattymin)** and the contributors to [PokeTokenBar](https://github.com/chattymin/PokeTokenBar). This is a port, not a reimagining: the token economy, evolution pacing, rarity curve, hatch thresholds, shiny odds, and shop prices are copied verbatim from the Swift source, because they are tuned values.

**If you like this, star [the upstream project](https://github.com/chattymin/PokeTokenBar), not this port.** The good idea is theirs.

- Upstream: <https://github.com/chattymin/PokeTokenBar> (MIT)
- Pokémon data & sprites: [PokéAPI](https://pokeapi.co/) — fetched at runtime, never bundled
- KDE logo © [KDE e.V.](https://kde.org/), used to indicate Plasma compatibility

## Development

```bash
python3 -m venv .venv && ./.venv/bin/pip install pytest
./.venv/bin/pytest -q
```

The upstream Swift sources are the specification — port behaviour from them rather than re-deriving it.

Architecture: a Python daemon owns all state and writes `state.json`; the QML widgets only render it and talk back through `poketokenctl`. The companion has to keep growing while the popup is shut, and Plasma reloads applets whenever you edit the panel — so game state never lives in QML.

## License & disclaimer

MIT — see [LICENSE](LICENSE). The MIT licence covers this project's source code only; it grants no rights to third-party trademarks, artwork, or data.

Pokémon is a trademark of Nintendo / Creatures Inc. / GAME FREAK Inc. This is an **unofficial, non-commercial fan project** with no affiliation to Nintendo, Game Freak, Creatures Inc., The Pokémon Company, Anthropic, OpenAI, or KDE e.V.

If you are a rights holder with a concern about this project, please open an issue and I'll respond promptly.
