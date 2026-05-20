# Translated FE6 ROM Support — Fix Plan

## Phase A: Profile & Hash Detection [x]
- [x] Identify translated FE6 ROM SHA-1 (32605fd456677ef740f8d521e9a3894ace4bc59c)
- [x] Identify translated FE6 ROM CRC32 (99B8B6D7)
- [x] Confirm translation patch relocates internal data tables
- [x] Create `src/profiles/fe6_translated_safe.json` with feature_flags disabling unsafe ops
- [x] Verify ProfileManager.match_rom() hits the new profile via SHA-1

## Phase B: Engine Hardening [x]
- [x] Engine respects feature_flags for class/bases/growths/ranks/inventory passes
- [x] Engine emits clear warnings when running on a translation_metadata profile
- [x] Engine performs sanity-check on character table after load
- [x] Engine force-disables destructive flags when sanity check fails

## Phase C: Validation Hardening [x]
- [x] Added translation-patch awareness to ValidationEngine
- [x] Added "table sanity" pre-check that flags impossible stat values
- [x] Validation correctly catches Roy HP=-19 on translated ROM

## Phase D: UI Warnings [x]
- [x] Show prominent warning banner (QMessageBox) when translated profile is active

## Phase E: Layout / Profile Schema Cleanup [x]
- [x] Added fe6_class_vanilla.json and fe6_item_vanilla.json layouts
- [x] Trimmed item layout to 32 bytes (FE6 items, not 36 like FE7/FE8)
- [x] Made tables.py 'size' field optional via .get()

## Phase F: Commit & Push [x]
- [x] Committed all changes with descriptive message (commit 7f844b5)
- [x] Pushed branch to GitHub via x-access-token
- [x] Opened Pull Request #3 (retargeted at feature/fegba-randomizer-v1)
- [x] PR diff is clean: +1181 / -95 (only the safe-mode work)

## Verification Summary
- Profile matches translated ROM by SHA-1 (tier C)
- All 3 tables load (227 chars / 75 classes / 128 items)
- Engine: 8 warnings, 0 errors, 43 changes (growths-only)
- Validation: 51 issues (7 translation, 41 sanity, 3 weapon, 4 bounds)
- All other profiles still load unchanged
