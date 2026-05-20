# ⚔️ FEGBA Randomizer — Fire Emblem GBA Character Randomizer

A polished Windows-only GUI randomizer for **Fire Emblem 6**, **Fire Emblem 7**, and **Fire Emblem 8**, plus **common hack bases including Skill System**. Built with Python 3.11+ and PySide6 (Qt).

---

## ✨ Features

### Randomization
- **Class Randomization** — Vanilla / Shuffle / Full Random with constraints (keep lords, thieves, dancers; respect gender locks; exclude monsters)
- **Base Stats Randomization** — Shuffle or randomize within ±N variance, optional budget preservation
- **Growth Rates Randomization** — Same flexibility as bases, with min/max/variance sliders
- **Weapon Ranks Randomization** — Shuffle or randomize, with automatic usability fixes
- **Starting Inventory** — Don't change / Guarantee usable / Randomize consumables / Full random with blacklists

### ROM Support (Profile-Based Compatibility)
| Tier | Description | Support |
|------|-------------|---------|
| **A — Verified** | Exact hash match in database | Full features |
| **B — Recognized Hack Base** | Matches known hack base signature | Full/near-full |
| **C — Unknown (Advanced)** | Heuristic detection, user-forced modules | Limited, with warnings |

**Included Profiles:**
- `FE8: The Sacred Stones (US)` — Tier A
- `FE7: Blazing Blade (US)` — Tier A
- `FE6: Binding Blade (JP)` — Tier A
- `FE8 Skill System (SkillSys 2023+)` — Tier B

### GUI
- Dark-themed polished interface (PySide6/Qt)
- Left Build panel + 8 right-side tabs
- Drag-and-drop ROM loading
- ROM auto-detection with tier badges and hash display
- Character list with portrait thumbnails and per-character lock/exclusion toggles
- Full Preview table with before/after comparison, color-coded diffs, filters
- Safety panel with errors, warnings, auto-fix capabilities
- Spoiler log viewer + export
- Preset system (Casual, Balanced, Chaos, Vanilla+) with import/export
- Shareable settings strings (base64-encoded, copy/paste)

### Output
- **New ROM** (`.gba`) — atomic write with temp file
- **BPS Patch** — with optional verification
- **UPS Patch** — with optional verification
- **Spoiler Logs** — both `.txt` (human-readable) and `.json` (machine-readable)

---

## 🚀 Quick Start

### Direct Launch (Recommended)

**Windows:** double-click:

```text
Launch Randomizer.bat
```

The launcher keeps the working directory in the project folder, checks for Python, and starts the GUI through `launch.py`. If dependencies are missing, it will show the install command.

**Any platform with Python:**

```bash
python launch.py
```

### Running from Source Manually
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application directly
python src/app.py
```

### Building a Standalone Executable (Windows)
```bash
# Install Nuitka
pip install nuitka

# Build
python build.py
```
This produces `dist/FEGBA_Randomizer.exe` and a portable ZIP.

---

## 📁 Project Structure

```
src/
├── app.py                          # Application entry point
├── ui/
│   ├── main_window.py              # Main window with Build panel + tabs
│   ├── tabs/
│   │   ├── characters_tab.py       # Portrait list + detail panel + locks
│   │   ├── classes_tab.py          # Class pool checklist + constraints
│   │   ├── stats_tab.py            # Bases/growths/ranks sliders
│   │   ├── items_tab.py            # Inventory options
│   │   ├── safety_tab.py           # Validation issues panel
│   │   ├── advanced_tab.py         # Force build, Tier C overrides
│   │   ├── preview_tab.py          # Before/after comparison table
│   │   └── logs_tab.py             # Spoiler log viewer
│   └── models/
│       └── app_state.py            # Central state + QThread workers
├── core/
│   ├── rng.py                      # Deterministic RNG engine
│   ├── engine.py                   # Randomization engine + settings
│   ├── validation.py               # Safety checks + auto-fix
│   ├── spoiler_log.py              # Spoiler log generator (txt/json)
│   └── presets.py                  # Preset manager + settings strings
├── rom/
│   ├── loader.py                   # ROM loader + profile/layout managers
│   ├── tables.py                   # Table reader/writer (generic)
│   └── writer.py                   # Atomic ROM/patch output
├── patch/
│   ├── bps.py                      # BPS patch generation/application
│   └── ups.py                      # UPS patch generation/application
├── profiles/                       # ROM profile JSONs
│   ├── fe8_clean_us.json
│   ├── fe7_clean_us.json
│   ├── fe6_clean_jp.json
│   └── fe8_skill_system.json
├── layouts/                        # Table layout definitions
│   ├── fe8_char_vanilla.json
│   ├── fe8_class_vanilla.json
│   ├── fe8_item_vanilla.json
│   ├── fe7_char_vanilla.json
│   ├── fe6_char_vanilla.json
│   └── fe8_char_skillsys.json
├── presets/                        # Randomizer presets
│   ├── casual.json
│   ├── balanced.json
│   ├── chaos.json
│   └── vanilla_plus.json
└── assets/
    ├── icons/
    │   ├── app_icon.png
    │   ├── app_icon.ico
    │   └── unknown_portrait.png
    ├── fe6/portraits/              # FE6 portrait PNGs (user-supplied)
    ├── fe7/portraits/              # FE7 portrait PNGs (user-supplied)
    └── fe8/portraits/              # FE8 portrait PNGs (user-supplied)
```

---

## 🎮 Usage Guide

1. **Load ROM** — Drag-and-drop or browse for a `.gba` file
2. **Check compatibility** — The tool auto-detects the game and shows a Tier badge
3. **Choose settings** — Use a Preset or configure tabs manually
4. **Set seed** — Enter a seed for reproducibility, or click 🎲 for random
5. **Preview** — Click Preview to see all changes before committing
6. **Check Safety** — Review the Safety tab for errors/warnings
7. **Build** — Click BUILD to generate the randomized ROM or patch
8. **Share** — Copy the settings string to share your exact config with others

---

## 🔧 Adding New Profiles (Hack Base Support)

To support a new hack base:

1. Create a new JSON file in `src/profiles/` following the schema
2. Identify the ROM's SHA-1/CRC32 hashes (or define secondary signatures)
3. Map the table addresses and entry sizes
4. Define character metadata, rules, and feature flags
5. If table layouts differ, create new layout JSONs in `src/layouts/`

### Profile JSON Schema (key fields)
```json
{
  "profile_id": "unique_id",
  "display_name": "Display Name",
  "game": "fe8",
  "region": "US",
  "tier": "B",
  "hashes": { "sha1": ["..."], "crc32": ["..."] },
  "tables": {
    "characters": { "address": 12345, "count": 255, "entry_size": 52, "layout": "layout_id" }
  },
  "characters": { "1": {"name": "Name", "portrait": "file.png"} },
  "rules": { "lord_character_ids": [1] },
  "feature_flags": { "supports_class_randomization": true }
}
```

---

## 📋 Version Roadmap

| Version | Features |
|---------|----------|
| **v1.0** | FE8 + FE7 clean ROM profiles, full randomizer, GUI, BPS patches, spoiler logs |
| **v1.1** | FE6 profile, UPS patches, first hack base profiles (Skill System), Advanced mode |
| **v1.2+** | More hack base profiles, skill-aware randomization, cosmetic options |

---

## 🛡 Safety System

The validation engine runs these checks:
- **Class legality** — gender locks, valid IDs
- **Weapon usability** — starting weapons match character ranks
- **Required characters** — lords/story-critical units preserved
- **Stat bounds** — values within valid GBA ranges

**Auto-fix** (enabled by default):
- Raises weapon ranks to minimum for starting weapons
- Clamps out-of-bounds stats
- Reverts invalid class assignments to originals

---

## 📜 License

This project is provided as-is for personal use. Fire Emblem is a trademark of Nintendo/Intelligent Systems.