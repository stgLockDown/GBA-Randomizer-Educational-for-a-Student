# Fire Emblem GBA Character Randomizer — Build Plan

## Phase 1: Project Foundation [x]
- [x] Create project directory structure
- [x] Create requirements.txt and build configuration
- [x] Create profile JSON schema and initial profiles (FE7, FE8)
- [x] Create layout definitions for vanilla table structures
- [x] Create placeholder portrait assets system

## Phase 2: Core Engine [x]
- [x] Implement ROM loader with hash detection and profile matching
- [x] Implement table reader/writer (characters, classes, items)
- [x] Implement RNG engine (deterministic seed-based)
- [x] Implement class randomization logic
- [x] Implement bases randomization logic
- [x] Implement growths randomization logic
- [x] Implement weapon ranks randomization logic
- [x] Implement starting inventory logic
- [x] Implement validation engine (safety checks, auto-fix)
- [x] Implement spoiler log generator (txt + json)

## Phase 3: Patch Generation [x]
- [x] Implement BPS patch generation
- [x] Implement UPS patch generation
- [x] Implement ROM writer (atomic write with temp file)

## Phase 4: Preset & Settings System [x]
- [x] Implement preset JSON load/save
- [x] Implement shareable settings string (base64 encode/decode)
- [x] Create default presets (Casual, Balanced, Chaos, etc.)

## Phase 5: GUI — Main Window & Layout [x]
- [x] Create main window with left Build panel + right tabs
- [x] Implement ROM picker with drag/drop
- [x] Implement ROM info display (title, region, tier badge, hashes)
- [x] Implement output mode selector (ROM/BPS/UPS)
- [x] Implement seed controls (text box, random, copy)
- [x] Implement presets dropdown
- [x] Implement Build/Preview/Open folder buttons

## Phase 6: GUI — Tabs [x]
- [x] Characters tab (portrait list + detail panel + locks)
- [x] Classes tab (class pool checklist, weights)
- [x] Stats tab (bases/growths sliders and modes)
- [x] Items tab (inventory options)
- [x] Safety tab (warnings/errors panel)
- [x] Advanced tab (force build, tier C options)
- [x] Preview tab (before/after table with filters and color coding)
- [x] Logs tab (spoiler log viewer)

## Phase 7: Integration & Threading [x]
- [x] Wire up QThread for ROM load
- [x] Wire up QThread for preview generation
- [x] Wire up QThread for build process
- [x] Connect all UI signals to engine
- [x] End-to-end test flow

## Phase 8: Polish & Packaging [x]
- [x] Create application icon and branding
- [x] Create Nuitka build script
- [x] Create portable ZIP packaging script
- [x] Final testing and documentation
- [x] Create README with usage instructions