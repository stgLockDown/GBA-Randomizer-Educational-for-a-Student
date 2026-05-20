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
- [x] Engine performs sanity-check on character table after load (detect garbage)
- [x] Engine force-disables destructive flags when sanity check fails

## Phase C: Validation Hardening [x]
- [x] Added translation-patch awareness to ValidationEngine (top-level summary issues)
- [x] Added "table sanity" pre-check that flags impossible stat values
- [x] Confirmed validation catches Roy HP=-19 (table-misalignment indicator) on translated ROM

## Phase D: UI Warnings [x]
- [x] Show prominent warning banner in main window (QMessageBox) when translated profile is active

## Phase E: Layout / Profile Schema Cleanup [x]
- [x] Fixed fe6_item_vanilla.json entry_size mismatch (36 → 32 to match profile)
- [x] Verified fe6_class_vanilla.json fields fit within 72-byte profile size

## Phase F: Commit & Push [ ]
- [ ] Commit all changes with descriptive message
- [ ] Push branch to GitHub via x-access-token
- [ ] Open Pull Request describing the safe-mode approach
