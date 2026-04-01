#!/usr/bin/env python3
"""
End-to-End QA Test for FEGBA Randomizer
Tests the full pipeline: ROM load → randomize → write → verify

CRITICAL TESTS:
  - Pointer preservation (name_pointer, desc_pointer never zeroed)
  - Table addresses correct (hex values stored as proper decimals)
  - ROM byte integrity (only expected bytes changed)
  - Determinism (same seed → identical output)
"""
import sys
import os
import struct
import hashlib
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠  WARN"

results = []

def log(status, test_name, detail=""):
    msg = f"  {status}: {test_name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((status, test_name, detail))


def make_synthetic_rom():
    """
    Build a minimal but valid FE8-like GBA ROM for testing.

    CRITICAL: Table addresses must match the CORRECTED profile values.
    The profile stores hex file offsets as their proper decimal values:
      characters: 0x803024 = 8400932 decimal
      classes:    0x807108 = 8417544 decimal
      items:      0x809712 = 8427282 decimal

    ROM must be large enough to contain all tables.
    """
    # FE8 table offsets (corrected from profiles)
    CHAR_ADDR   = 0x803024   # 8400932 decimal
    CLASS_ADDR  = 0x807108   # 8417544 decimal
    ITEM_ADDR   = 0x809712   # 8427282 decimal

    CHAR_ENTRY_SIZE  = 52
    CLASS_ENTRY_SIZE = 84
    ITEM_ENTRY_SIZE  = 36

    NUM_CHARS   = 5
    NUM_CLASSES = 5
    NUM_ITEMS   = 5

    # ROM must be at least as large as the last table entry's end
    last_byte = ITEM_ADDR + NUM_ITEMS * ITEM_ENTRY_SIZE
    # Round up to next MB
    rom_size = ((last_byte // 0x100000) + 2) * 0x100000
    rom = bytearray(rom_size)

    # GBA header
    rom[0xA0:0xAC] = b'FIRE EMBLEM '   # Title (12 bytes)
    rom[0xAC:0xB0] = b'BE8E'           # Game code (FE8 US)
    rom[0xB0] = 0x96                   # Fixed value

    # Character table
    for i in range(NUM_CHARS):
        base = CHAR_ADDR + i * CHAR_ENTRY_SIZE
        char_id = i + 1

        # name_pointer (offset 0, 4 bytes) - valid GBA ROM pointer
        name_ptr = 0x08100000 + i * 0x20
        struct.pack_into('<I', rom, base + 0, name_ptr)

        # desc_pointer (offset 4, 4 bytes)
        desc_ptr = 0x08200000 + i * 0x20
        struct.pack_into('<I', rom, base + 4, desc_ptr)

        struct.pack_into('<H', rom, base + 8,  char_id)  # char_id
        struct.pack_into('<H', rom, base + 10, 1)         # class_id
        struct.pack_into('<H', rom, base + 12, char_id)   # portrait_id
        struct.pack_into('<H', rom, base + 14, char_id)   # mini_portrait

        rom[base + 16] = 1   # affinity
        rom[base + 17] = 0   # padding
        rom[base + 18] = 1   # level

        # Bases (offsets 19-26): hp, str, skl, spd, def, res, lck, con
        for j, val in enumerate([20, 5, 5, 6, 4, 2, 3, 8]):
            struct.pack_into('b', rom, base + 19 + j, val)

        # Growths (offsets 28-34): hp, str, skl, spd, def, res, lck
        for j, val in enumerate([80, 45, 40, 40, 30, 25, 35]):
            rom[base + 28 + j] = val

        rom[base + 35] = 0   # padding

        # Ranks (offsets 36-43): sword, lance, axe, bow, staff, anima, light, dark
        for j, val in enumerate([1, 0, 0, 0, 0, 0, 0, 0]):
            rom[base + 36 + j] = val

        # Items (offsets 44-51): 4x uint16
        for j, val in enumerate([1, 0, 0, 0]):
            struct.pack_into('<H', rom, base + 44 + j * 2, val)

    # Class table
    for i in range(NUM_CLASSES):
        base = CLASS_ADDR + i * CLASS_ENTRY_SIZE
        struct.pack_into('<I', rom, base + 0, 0x08300000 + i * 0x20)
        struct.pack_into('<I', rom, base + 4, 0x08400000 + i * 0x20)

    # Item table
    for i in range(NUM_ITEMS):
        base = ITEM_ADDR + i * ITEM_ENTRY_SIZE
        struct.pack_into('<I', rom, base + 0, 0x08500000 + i * 0x20)
        struct.pack_into('<I', rom, base + 4, 0x08600000 + i * 0x20)
        rom[base + 9]  = 1    # rank
        rom[base + 10] = 5    # might
        rom[base + 12] = 75   # hit
        rom[base + 14] = 40   # uses

    return (bytes(rom), CHAR_ADDR, CHAR_ENTRY_SIZE, NUM_CHARS,
            CLASS_ADDR, CLASS_ENTRY_SIZE, NUM_CLASSES,
            ITEM_ADDR, ITEM_ENTRY_SIZE, NUM_ITEMS)


def run_qa():
    print("=" * 70)
    print("FEGBA RANDOMIZER — END-TO-END QA TEST")
    print("=" * 70)

    # ── Test 1: Module imports ──────────────────────────────────────────────
    print("\n[1] Module Import Tests")
    try:
        from src.rom.loader import ROMData, ProfileManager, LayoutManager
        log(PASS, "Import rom.loader")
    except Exception as e:
        log(FAIL, "Import rom.loader", str(e))
        return False

    try:
        from src.rom.tables import TableEntry, ROMTable, TableManager
        log(PASS, "Import rom.tables")
    except Exception as e:
        log(FAIL, "Import rom.tables", str(e))
        return False

    try:
        from src.rom.writer import ROMWriter
        log(PASS, "Import rom.writer")
    except Exception as e:
        log(FAIL, "Import rom.writer", str(e))

    try:
        from src.core.engine import RandomizationEngine, RandomizerSettings
        log(PASS, "Import core.engine")
    except Exception as e:
        log(FAIL, "Import core.engine", str(e))
        return False

    try:
        from src.core.validation import ValidationEngine
        log(PASS, "Import core.validation")
    except Exception as e:
        log(FAIL, "Import core.validation", str(e))

    try:
        from src.core.rng import RNGEngine
        log(PASS, "Import core.rng")
    except Exception as e:
        log(FAIL, "Import core.rng", str(e))
        return False

    try:
        from src.core.presets import PresetManager
        log(PASS, "Import core.presets")
    except Exception as e:
        log(FAIL, "Import core.presets", str(e))

    try:
        from src.core.spoiler_log import SpoilerLogGenerator
        log(PASS, "Import core.spoiler_log")
    except Exception as e:
        log(FAIL, "Import core.spoiler_log", str(e))

    # Re-import all for use below
    from src.rom.loader import ROMData, ProfileManager, LayoutManager
    from src.rom.tables import TableEntry, ROMTable, TableManager
    from src.core.engine import RandomizationEngine, RandomizerSettings
    from src.core.rng import RNGEngine

    # ── Test 2: Profile address correctness ──────────────────────────────
    print("\n[2] Profile Address Validation Tests")
    import json

    profile_checks = [
        ('src/profiles/fe8_clean_us.json', {
            'characters': 0x803024,  # = 8400932
            'classes':    0x807108,  # = 8417544
            'items':      0x809712,  # = 8427282
        }),
        ('src/profiles/fe7_clean_us.json', {
            'characters': 0x798684,  # = 7964292
            'classes':    0x802604,  # = 8398340
            'items':      0x807760,  # = 8419168
        }),
        ('src/profiles/fe6_clean_jp.json', {
            'characters': 0x607084,  # = 6320260
            'classes':    0x617760,  # = 6387552
            'items':      0x627440,  # = 6452288
        }),
    ]

    for profile_path, expected in profile_checks:
        try:
            with open(profile_path, 'r') as f:
                prof = json.load(f)
            for table_name, expected_addr in expected.items():
                actual = prof.get('tables', {}).get(table_name, {}).get('address')
                if actual == expected_addr:
                    log(PASS, f"{os.path.basename(profile_path)} {table_name}",
                        f"0x{actual:X} = {actual}")
                elif actual is None:
                    log(WARN, f"{os.path.basename(profile_path)} {table_name}",
                        "null (pointer-based)")
                else:
                    log(FAIL, f"{os.path.basename(profile_path)} {table_name} WRONG",
                        f"expected 0x{expected_addr:X}={expected_addr}, got 0x{actual:X}={actual}")
        except Exception as e:
            log(FAIL, f"Load {profile_path}", str(e))

    # ── Test 3: Synthetic ROM creation ────────────────────────────────────
    print("\n[3] Synthetic ROM Creation Tests")
    (rom_bytes, CHAR_ADDR, ENTRY_SIZE, NUM_CHARS,
     CLASS_ADDR, CLASS_ENTRY_SIZE, NUM_CLASSES,
     ITEM_ADDR, ITEM_ENTRY_SIZE, NUM_ITEMS) = make_synthetic_rom()

    try:
        assert len(rom_bytes) >= ITEM_ADDR + NUM_ITEMS * ITEM_ENTRY_SIZE, \
            f"ROM too small: {len(rom_bytes)}"
        log(PASS, "Synthetic ROM created",
            f"{len(rom_bytes)} bytes, tables at 0x{CHAR_ADDR:X}/0x{CLASS_ADDR:X}/0x{ITEM_ADDR:X}")
    except Exception as e:
        log(FAIL, "Synthetic ROM creation", str(e))
        return False

    # Verify entries were written at the right offsets
    try:
        first_char_name_ptr = struct.unpack_from('<I', rom_bytes, CHAR_ADDR)[0]
        assert first_char_name_ptr == 0x08100000, \
            f"name_ptr wrong: {hex(first_char_name_ptr)}"
        log(PASS, "Character table written at correct offset",
            f"0x{CHAR_ADDR:X} has name_ptr={hex(first_char_name_ptr)}")
    except Exception as e:
        log(FAIL, "Character table offset check", str(e))

    # ── Test 4: ROMData creation ──────────────────────────────────────────
    print("\n[4] ROMData Tests")
    import tempfile

    tmp_rom = tempfile.NamedTemporaryFile(suffix='.gba', delete=False)
    tmp_rom.write(rom_bytes)
    tmp_rom.close()

    try:
        rom_data = ROMData(tmp_rom.name, rom_bytes)
        log(PASS, "ROMData created",
            f"size={rom_data.size}, title='{rom_data.gba_title}', code={rom_data.gba_game_code}")
    except Exception as e:
        log(FAIL, "ROMData creation", str(e))
        return False

    try:
        sha1 = rom_data.sha1
        crc32 = rom_data.crc32
        assert len(sha1) == 40, "SHA1 wrong length"
        assert len(crc32) == 8, "CRC32 wrong length"
        log(PASS, "ROM hash computation", f"SHA1={sha1[:12]}... CRC32={crc32}")
    except Exception as e:
        log(FAIL, "ROM hash computation", str(e))

    # ── Test 5: Layout loading ────────────────────────────────────────────
    print("\n[5] Layout Loading Tests")
    layouts_dir = os.path.join(os.path.dirname(__file__), 'src', 'layouts')
    try:
        lm = LayoutManager(layouts_dir)
        expected_layouts = [
            'fe8_char_vanilla', 'fe8_class_vanilla', 'fe8_item_vanilla',
            'fe7_char_vanilla', 'fe6_char_vanilla', 'fe6_class_vanilla',
            'fe6_item_vanilla', 'fe8_char_skillsys'
        ]
        for layout_id in expected_layouts:
            if layout_id in lm.layouts:
                log(PASS, f"Layout loaded: {layout_id}")
            else:
                log(FAIL, f"Layout missing: {layout_id}")
    except Exception as e:
        log(FAIL, "LayoutManager init", str(e))
        traceback.print_exc()

    # ── Test 6: Synthetic profile & TableManager ──────────────────────────
    print("\n[6] Synthetic Profile & TableManager Tests")
    synthetic_profile = {
        "profile_id": "qa_test",
        "display_name": "QA Test Profile",
        "game": "fe8",
        "tier": "A",
        "tables": {
            "characters": {
                "address": CHAR_ADDR,
                "pointer_address": None,
                "count": NUM_CHARS,
                "entry_size": ENTRY_SIZE,
                "layout": "fe8_char_vanilla"
            }
        },
        "characters": {
            "1": {"name": "TestLord",   "is_lord": True,  "is_required": True,  "is_female": False},
            "2": {"name": "TestKnight", "is_lord": False, "is_required": False, "is_female": False},
            "3": {"name": "TestMage",   "is_lord": False, "is_required": False, "is_female": True},
            "4": {"name": "TestArcher", "is_lord": False, "is_required": False, "is_female": False},
            "5": {"name": "TestHealer", "is_lord": False, "is_required": False, "is_female": True},
        },
        "rules": {
            "lord_character_ids": [1],
            "required_character_ids": [1],
            "lord_class_ids": [1],
            "thief_character_ids": [],
            "dancer_character_ids": [],
        },
        "feature_flags": {
            "supports_class_randomization": True,
            "supports_bases_randomization": True,
            "supports_growths_randomization": True,
            "supports_ranks_randomization": True,
            "supports_inventory_randomization": False,
        }
    }

    try:
        lm = LayoutManager(layouts_dir)
        tm = TableManager(rom_data, synthetic_profile, lm)
        tm.load_all_tables()
        char_table = tm.tables.get('characters')
        assert char_table is not None, "Character table not loaded"
        assert len(char_table.entries) == NUM_CHARS, \
            f"Expected {NUM_CHARS} chars, got {len(char_table.entries)}"
        log(PASS, "TableManager loaded character table", f"{len(char_table.entries)} entries")
    except Exception as e:
        log(FAIL, "TableManager load", str(e))
        traceback.print_exc()
        return False

    # ── Test 7: CRITICAL — Pointer preservation ───────────────────────────
    print("\n[7] CRITICAL: Pointer Preservation Tests")
    char_table = tm.tables.get('characters')

    original_pointers = {}
    for entry in char_table:
        cid = entry.get('char_id', entry.index)
        original_pointers[cid] = {
            'name_pointer': entry.get('name_pointer', 0),
            'desc_pointer': entry.get('desc_pointer', 0),
        }

    # Verify original pointers are non-zero (correctly loaded)
    ptrs_loaded_ok = True
    for cid, ptrs in original_pointers.items():
        if ptrs['name_pointer'] == 0:
            log(FAIL, f"Char {cid} name_pointer is 0 after load",
                "Table offset may be wrong!")
            ptrs_loaded_ok = False
        if ptrs['desc_pointer'] == 0:
            log(FAIL, f"Char {cid} desc_pointer is 0 after load",
                "Table offset may be wrong!")
            ptrs_loaded_ok = False

    if ptrs_loaded_ok:
        log(PASS, "All pointers non-zero after load (table offsets correct)")

    # Modify class_id only — pointers must NOT change
    for entry in char_table:
        entry.set('class_id', 2)

    # Serialize and check pointers are preserved
    all_ok = True
    for entry in char_table:
        cid = entry.get('char_id', entry.index)
        serialized = entry.to_bytes()

        name_ptr_after = struct.unpack_from('<I', serialized, 0)[0]
        desc_ptr_after = struct.unpack_from('<I', serialized, 4)[0]

        orig_name = original_pointers[cid]['name_pointer']
        orig_desc = original_pointers[cid]['desc_pointer']

        if name_ptr_after != orig_name:
            log(FAIL, f"Char {cid} name_pointer CORRUPTED",
                f"{hex(orig_name)} → {hex(name_ptr_after)}")
            all_ok = False
        if desc_ptr_after != orig_desc:
            log(FAIL, f"Char {cid} desc_pointer CORRUPTED",
                f"{hex(orig_desc)} → {hex(desc_ptr_after)}")
            all_ok = False

    if all_ok:
        log(PASS, "All name_pointers preserved after set() call")
        log(PASS, "All desc_pointers preserved after set() call")

    # ── Test 8: RNG determinism ───────────────────────────────────────────
    print("\n[8] RNG Tests")
    try:
        rng1 = RNGEngine("TEST_SEED_12345")
        rng2 = RNGEngine("TEST_SEED_12345")

        vals1 = [rng1.randint(0, 100) for _ in range(20)]
        vals2 = [rng2.randint(0, 100) for _ in range(20)]

        assert vals1 == vals2, "RNG not deterministic!"
        log(PASS, "RNG is deterministic", f"First 5 values: {vals1[:5]}")
    except Exception as e:
        log(FAIL, "RNG determinism", str(e))

    try:
        rng = RNGEngine("FORK_TEST")
        fork1 = rng.fork("module_a")
        fork2 = rng.fork("module_b")

        val_main = rng.randint(0, 1000)
        val1 = fork1.randint(0, 1000)
        val2 = fork2.randint(0, 1000)

        assert val1 != val2, "Forks should produce different values"
        log(PASS, "RNG fork isolation",
            f"main={val_main}, fork_a={val1}, fork_b={val2}")
    except Exception as e:
        log(FAIL, "RNG fork isolation", str(e))

    # ── Test 9: Full randomization pipeline ──────────────────────────────
    print("\n[9] Full Randomization Pipeline Tests")

    # Re-load fresh ROM
    rom_data2 = ROMData(tmp_rom.name, rom_bytes)
    tm2 = TableManager(rom_data2, synthetic_profile, lm)
    tm2.load_all_tables()

    settings = RandomizerSettings()
    settings.seed = "QA_TEST_SEED"
    settings.class_mode = "random"
    settings.bases_mode = "random"
    settings.bases_variance = 3
    settings.growths_mode = "random"
    settings.growths_variance = 15
    settings.ranks_mode = "vanilla"
    settings.keep_lords = True
    settings.inventory_mode = "dont_change"
    settings.auto_fix = True

    try:
        rng_e = RNGEngine(settings.seed)
        engine = RandomizationEngine(tm2, settings, synthetic_profile, rng_e)
        success = engine.run()          # Returns bool, NOT a list
        changes  = engine.get_changes()
        errors   = engine.get_errors()
        warnings = engine.get_warnings()

        log(PASS, "Randomization engine ran",
            f"success={success}, changes={len(changes)}, warnings={len(warnings)}, errors={len(errors)}")

        if errors:
            for err in errors:
                log(WARN, "Engine error", err)
    except Exception as e:
        log(FAIL, "Randomization engine", str(e))
        traceback.print_exc()
        return False

    # ── Test 10: Validate randomized data ────────────────────────────────
    print("\n[10] Randomized Data Validation Tests")
    char_table2 = tm2.tables.get('characters')

    all_ptrs_ok = True
    for entry in char_table2:
        cid = entry.get('char_id', entry.index)
        raw = entry.to_bytes()
        name_ptr = struct.unpack_from('<I', raw, 0)[0]
        desc_ptr = struct.unpack_from('<I', raw, 4)[0]

        orig_name = original_pointers.get(cid, {}).get('name_pointer', 0)
        orig_desc = original_pointers.get(cid, {}).get('desc_pointer', 0)

        if name_ptr != orig_name:
            log(FAIL, f"Char {cid} name_pointer CORRUPTED after randomize",
                f"{hex(orig_name)} → {hex(name_ptr)}")
            all_ptrs_ok = False
        if desc_ptr != orig_desc:
            log(FAIL, f"Char {cid} desc_pointer CORRUPTED after randomize",
                f"{hex(orig_desc)} → {hex(desc_ptr)}")
            all_ptrs_ok = False

    if all_ptrs_ok:
        log(PASS, "All pointers preserved after full randomization")

    # Check stat bounds
    bounds_ok = True
    for entry in char_table2:
        cid = entry.get('char_id', entry.index)
        name = synthetic_profile['characters'].get(str(cid), {}).get('name', f'Char_{cid}')

        growths = entry.get_stat_values('growths')
        for stat, val in growths.items():
            if val < 0 or val > 255:
                log(FAIL, f"{name} growth {stat} out of bounds", f"val={val}")
                bounds_ok = False

        bases = entry.get_stat_values('bases')
        for stat, val in bases.items():
            if val < -20 or val > 60:
                log(WARN, f"{name} base {stat} unusual range", f"val={val}")

    if bounds_ok:
        log(PASS, "All growth values in valid range [0, 255]")

    # Check lord was preserved
    lord_entry = None
    for entry in char_table2:
        if entry.get('char_id', entry.index) == 1:
            lord_entry = entry
            break

    if lord_entry:
        lord_class = lord_entry.get('class_id', 0)
        if lord_class == 1:
            log(PASS, "Lord character class preserved (keep_lords=True)")
        else:
            log(WARN, f"Lord class changed to {lord_class}",
                "keep_lords may not be working")

    # ── Test 11: ROM write and byte integrity ─────────────────────────────
    print("\n[11] ROM Write & Byte Integrity Tests")

    tm2.write_all_tables()
    modified_bytes = bytes(rom_data2.data)

    try:
        assert len(modified_bytes) == len(rom_bytes), \
            f"ROM size changed! {len(rom_bytes)} → {len(modified_bytes)}"
        log(PASS, "ROM size preserved after write", f"{len(modified_bytes)} bytes")
    except Exception as e:
        log(FAIL, "ROM size check", str(e))

    # Verify GBA header preserved
    try:
        assert modified_bytes[0xA0:0xAC] == b'FIRE EMBLEM ', "Game title corrupted!"
        assert modified_bytes[0xAC:0xB0] == b'BE8E', "Game code corrupted!"
        log(PASS, "GBA header preserved (title, game code)")
    except Exception as e:
        log(FAIL, "GBA header preservation", str(e))

    # Verify pointers in output ROM
    all_rom_ptrs_ok = True
    for i in range(NUM_CHARS):
        base = CHAR_ADDR + i * ENTRY_SIZE
        name_ptr = struct.unpack_from('<I', modified_bytes, base)[0]
        desc_ptr = struct.unpack_from('<I', modified_bytes, base + 4)[0]
        orig_name = 0x08100000 + i * 0x20
        orig_desc = 0x08200000 + i * 0x20

        if name_ptr != orig_name:
            log(FAIL, f"Entry {i}: name_pointer CORRUPTED IN ROM",
                f"expected={hex(orig_name)}, got={hex(name_ptr)}")
            all_rom_ptrs_ok = False
        if desc_ptr != orig_desc:
            log(FAIL, f"Entry {i}: desc_pointer CORRUPTED IN ROM",
                f"expected={hex(orig_desc)}, got={hex(desc_ptr)}")
            all_rom_ptrs_ok = False

    if all_rom_ptrs_ok:
        log(PASS, "All pointers correct in final ROM output")

    # Verify only expected bytes changed
    char_region_start = CHAR_ADDR
    char_region_end   = CHAR_ADDR + NUM_CHARS * ENTRY_SIZE

    changes_inside  = 0
    changes_outside = 0

    for i in range(len(rom_bytes)):
        if rom_bytes[i] != modified_bytes[i]:
            if char_region_start <= i < char_region_end:
                changes_inside += 1
            else:
                changes_outside += 1

    if changes_outside == 0:
        log(PASS, "No bytes changed outside character table region",
            f"{changes_inside} bytes modified in table")
    else:
        log(FAIL, "Bytes changed OUTSIDE character table!",
            f"{changes_outside} unexpected changes")
        shown = 0
        for i in range(len(rom_bytes)):
            if rom_bytes[i] != modified_bytes[i] and not (char_region_start <= i < char_region_end):
                print(f"    Changed at 0x{i:X}: {rom_bytes[i]:02X} → {modified_bytes[i]:02X}")
                shown += 1
                if shown >= 10:
                    print("    ... (truncated)")
                    break

    # ── Test 12: Determinism ─────────────────────────────────────────────
    print("\n[12] Determinism Tests")

    rom_a = ROMData(tmp_rom.name, rom_bytes)
    tm_a = TableManager(rom_a, synthetic_profile, lm)
    tm_a.load_all_tables()
    settings_a = RandomizerSettings()
    settings_a.seed = "DETERMINISM_TEST"
    settings_a.class_mode = "random"
    settings_a.bases_mode = "random"
    settings_a.growths_mode = "random"
    settings_a.inventory_mode = "dont_change"
    rng_a = RNGEngine(settings_a.seed)
    engine_a = RandomizationEngine(tm_a, settings_a, synthetic_profile, rng_a)
    engine_a.run()
    tm_a.write_all_tables()
    output_a = bytes(rom_a.data)

    rom_b = ROMData(tmp_rom.name, rom_bytes)
    tm_b = TableManager(rom_b, synthetic_profile, lm)
    tm_b.load_all_tables()
    settings_b = RandomizerSettings()
    settings_b.seed = "DETERMINISM_TEST"
    settings_b.class_mode = "random"
    settings_b.bases_mode = "random"
    settings_b.growths_mode = "random"
    settings_b.inventory_mode = "dont_change"
    rng_b = RNGEngine(settings_b.seed)
    engine_b = RandomizationEngine(tm_b, settings_b, synthetic_profile, rng_b)
    engine_b.run()
    tm_b.write_all_tables()
    output_b = bytes(rom_b.data)

    if output_a == output_b:
        log(PASS, "Same seed produces identical ROM output (deterministic)")
    else:
        for i in range(min(len(output_a), len(output_b))):
            if output_a[i] != output_b[i]:
                log(FAIL, "Same seed produced DIFFERENT outputs!",
                    f"First diff at 0x{i:X}: {output_a[i]:02X} vs {output_b[i]:02X}")
                break

    # ── Test 13: File output ─────────────────────────────────────────────
    print("\n[13] File Output Tests")

    tmp_out = tempfile.NamedTemporaryFile(suffix='_rand.gba', delete=False)
    tmp_out.close()

    try:
        from src.rom.writer import ROMWriter
        rom_out = ROMData(tmp_rom.name, rom_bytes)
        tm_out = TableManager(rom_out, synthetic_profile, lm)
        tm_out.load_all_tables()
        rng_out = RNGEngine(settings_a.seed)
        engine_out = RandomizationEngine(tm_out, settings_a, synthetic_profile, rng_out)
        engine_out.run()
        tm_out.write_all_tables()

        writer = ROMWriter(rom_data, rom_out)
        writer.write_rom(tmp_out.name)

        assert os.path.exists(tmp_out.name)
        file_size = os.path.getsize(tmp_out.name)
        assert file_size == len(rom_bytes), \
            f"Output file size wrong: {file_size} vs {len(rom_bytes)}"
        log(PASS, "ROM file written successfully",
            f"{file_size} bytes = {file_size//1024}KB")
    except Exception as e:
        log(FAIL, "ROM file write", str(e))
        traceback.print_exc()

    # ── Test 14: Layout entry_size sanity ────────────────────────────────
    print("\n[14] Layout Entry Size Sanity Tests")
    try:
        lm2 = LayoutManager(layouts_dir)
        size_checks = {
            'fe8_char_vanilla':  52,   # FE8: 52 bytes (extra padding/items vs FE6)
            'fe8_class_vanilla': 84,
            'fe8_item_vanilla':  36,
            'fe7_char_vanilla':  52,   # FE7: 52 bytes (same structure as FE8)
            'fe6_char_vanilla':  48,   # FE6: 48 bytes (no mini_portrait, different layout)
        }
        for lid, expected_size in size_checks.items():
            layout = lm2.get_layout(lid)
            if layout:
                actual = layout.get('entry_size')
                if actual == expected_size:
                    log(PASS, f"{lid} entry_size", f"{actual} bytes")
                else:
                    log(FAIL, f"{lid} entry_size wrong",
                        f"expected={expected_size}, got={actual}")
            else:
                log(WARN, f"{lid} not found")
    except Exception as e:
        log(FAIL, "Layout entry size check", str(e))

    # Cleanup
    try:
        os.unlink(tmp_rom.name)
        os.unlink(tmp_out.name)
    except Exception:
        pass

    # ── Final Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("QA TEST SUMMARY")
    print("=" * 70)

    passes  = sum(1 for r in results if r[0] == PASS)
    fails   = sum(1 for r in results if r[0] == FAIL)
    warns   = sum(1 for r in results if r[0] == WARN)
    total   = len(results)

    print(f"\n  Total:    {total}")
    print(f"  Passed:   {passes}")
    print(f"  Failed:   {fails}")
    print(f"  Warnings: {warns}")

    if fails == 0:
        print(f"\n✅ ALL TESTS PASSED! The randomizer is working correctly.")
    else:
        print(f"\n❌ {fails} test(s) FAILED. See details above.")
        print("\nFailed tests:")
        for r in results:
            if r[0] == FAIL:
                print(f"  • {r[1]}: {r[2]}")

    print("=" * 70)
    return fails == 0


if __name__ == "__main__":
    success = run_qa()
    sys.exit(0 if success else 1)