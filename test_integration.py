#!/usr/bin/env python3
"""
Full integration test for FEGBA Randomizer.
Creates a synthetic ROM and runs the entire pipeline.
"""
import sys
import os
import json
import struct
import tempfile
import shutil

sys.path.insert(0, '.')

from src.core.rng import RNGEngine
from src.core.engine import RandomizerSettings, RandomizationEngine
from src.core.validation import ValidationEngine
from src.core.spoiler_log import SpoilerLogGenerator
from src.core.presets import PresetManager
from src.rom.loader import ROMData, ProfileManager, LayoutManager
from src.rom.tables import TableManager
from src.rom.writer import ROMWriter
from src.patch.bps import BPSPatcher
from src.patch.ups import UPSPatcher


def create_synthetic_rom(profile_path: str, layout_dir: str) -> bytes:
    """Create a synthetic GBA ROM with valid tables for testing."""
    # Load profile to know table addresses
    with open(profile_path, 'r') as f:
        profile = json.load(f)

    # Create 16MB ROM filled with zeros
    rom_size = 16 * 1024 * 1024
    rom = bytearray(rom_size)

    # Write GBA header
    rom[0xA0:0xAC] = b'FIREEMBLEM8\x00'  # title
    rom[0xAC:0xB0] = b'BE8E'  # game code (FE8 US)

    # Write character table (fill with plausible data)
    char_table = profile['tables']['characters']
    addr = char_table['address']
    count = min(char_table['count'], 34)  # just playable chars
    entry_size = char_table['entry_size']

    for i in range(count):
        offset = addr + (i * entry_size)
        # char_id (offset 8)
        struct.pack_into('<H', rom, offset + 8, i + 1)
        # class_id (offset 10)
        struct.pack_into('<H', rom, offset + 10, (i % 20) + 1)
        # level (offset 18)
        rom[offset + 18] = max(1, (i % 10) + 1)
        # bases: HP, STR, SKL, SPD, DEF, RES, LCK, CON (offsets 19-26)
        for j, base in enumerate([20, 8, 7, 9, 6, 3, 5, 7]):
            rom[offset + 19 + j] = base + (i % 5)
        # growths: HP, STR, SKL, SPD, DEF, RES, LCK (offsets 28-34)
        for j, growth in enumerate([70, 45, 40, 50, 30, 25, 35]):
            rom[offset + 28 + j] = growth + (i * 2) % 30
        # ranks: sword, lance, axe, bow, staff, anima, light, dark (offsets 36-43)
        rom[offset + 36] = 31 if (i % 3 == 0) else 0  # some get sword D
        rom[offset + 37] = 31 if (i % 3 == 1) else 0  # some get lance D
        rom[offset + 38] = 31 if (i % 3 == 2) else 0  # some get axe D
        # starting items (offsets 44-50)
        struct.pack_into('<H', rom, offset + 44, 1)  # item 1 = Iron Sword placeholder

    # Write class table
    class_table = profile['tables']['classes']
    caddr = class_table['address']
    ccount = min(class_table['count'], 50)
    centry = class_table['entry_size']

    for i in range(ccount):
        offset = caddr + (i * centry)
        rom[offset + 8] = i  # class_id
        rom[offset + 9] = min(i + 20, 49) if i < 20 else 0  # promotion
        # class bases
        for j in range(8):
            rom[offset + 20 + j] = 3 + (i % 5)
        # class caps
        for j in range(7):
            rom[offset + 28 + j] = 25 + (i % 10)
        # gender flag
        rom[offset + 74] = 1 if i in [46, 47, 48] else 0

    # Write item table
    item_table = profile['tables']['items']
    iaddr = item_table['address']
    icount = min(item_table['count'], 50)
    ientry = item_table['entry_size']

    for i in range(icount):
        offset = iaddr + (i * ientry)
        struct.pack_into('<H', rom, offset + 8, i + 1)  # item_id
        rom[offset + 10] = i % 9  # item_type (0-8)
        rom[offset + 20] = 40  # durability
        rom[offset + 21] = 5 + (i % 10)  # might
        rom[offset + 22] = 80 + (i % 20)  # hit
        rom[offset + 23] = 5 + (i % 5)  # weight
        rom[offset + 28] = 1 if i < 30 else 31  # rank_required

    return bytes(rom)


def test_full_pipeline():
    """Test the full randomization pipeline."""
    print("=" * 60)
    print(" FEGBA Randomizer — Integration Test")
    print("=" * 60)

    # Setup
    profile_path = 'src/profiles/fe8_clean_us.json'
    layout_dir = 'src/layouts'
    tmp_dir = tempfile.mkdtemp(prefix='fegba_test_')

    try:
        # 1. Create synthetic ROM
        print("\n[1/8] Creating synthetic ROM...")
        rom_bytes = create_synthetic_rom(profile_path, layout_dir)
        rom_path = os.path.join(tmp_dir, 'test_fe8.gba')
        with open(rom_path, 'wb') as f:
            f.write(rom_bytes)
        print(f"  Created {len(rom_bytes)} byte ROM at {rom_path}")

        # 2. Load ROM
        print("\n[2/8] Loading ROM...")
        from src.rom.loader import load_rom
        rom = load_rom(rom_path)
        print(f"  Title: {rom.gba_title}")
        print(f"  Game code: {rom.gba_game_code}")
        print(f"  SHA-1: {rom.sha1[:20]}...")
        print(f"  CRC32: {rom.crc32}")

        # 3. Match profile
        print("\n[3/8] Matching profile...")
        pm = ProfileManager('src/profiles')
        profile, tier = pm.match_rom(rom)
        assert profile is not None, "Profile should match on game code"
        print(f"  Profile: {profile['display_name']}")
        print(f"  Tier: {tier}")

        # 4. Load tables
        print("\n[4/8] Loading tables...")
        lm = LayoutManager(layout_dir)
        tm = TableManager(rom, profile, lm)
        tm.load_all_tables()
        for tname, table in tm.tables.items():
            print(f"  {tname}: {len(table)} entries")

        # 5. Randomize with "Balanced" preset
        print("\n[5/8] Randomizing (Balanced preset)...")
        preset_mgr = PresetManager('src/presets')
        settings = preset_mgr.apply_preset('Balanced')
        settings.seed = 'INTEGRATION_TEST_42'

        rng = RNGEngine(settings.seed)
        engine = RandomizationEngine(tm, settings, profile, rng)
        success = engine.run()
        print(f"  Success: {success}")
        print(f"  Changes: {len(engine.get_changes())}")
        print(f"  Warnings: {len(engine.get_warnings())}")

        # Show some changes
        changed = [c for c in engine.get_changes()
                   if c.old_class_id != c.new_class_id or c.old_bases != c.new_bases]
        print(f"  Characters modified: {len(changed)}")
        for ch in changed[:5]:
            print(f"    {ch.name}: class {ch.old_class_id} -> {ch.new_class_id}")

        # 6. Validate
        print("\n[6/8] Validating...")
        validator = ValidationEngine(tm, settings, profile)
        issues = validator.run_all_checks()
        print(f"  Total issues: {len(issues)}")
        print(f"  Errors: {len(validator.get_errors())}")
        print(f"  Warnings: {len(validator.get_warnings())}")
        print(f"  Auto-fixed: {len(validator.get_fixed())}")

        # 7. Write output
        print("\n[7/8] Writing output...")
        tm.write_all_tables()
        original_rom = load_rom(rom_path)  # reload clean original
        writer = ROMWriter(original_rom, rom)

        # Write ROM
        out_rom = os.path.join(tmp_dir, 'test_fe8_Rand_TEST.gba')
        writer.write_rom(out_rom)
        print(f"  ROM written: {os.path.getsize(out_rom)} bytes")

        # Write BPS patch
        out_bps = os.path.join(tmp_dir, 'test_fe8_Rand_TEST.bps')
        writer.write_bps_patch(out_bps, verify=False)  # skip verify for speed
        print(f"  BPS patch: {os.path.getsize(out_bps)} bytes")

        # Write UPS patch
        out_ups = os.path.join(tmp_dir, 'test_fe8_Rand_TEST.ups')
        writer.write_ups_patch(out_ups, verify=False)
        print(f"  UPS patch: {os.path.getsize(out_ups)} bytes")

        # 8. Spoiler log
        print("\n[8/8] Generating spoiler log...")
        spoiler = SpoilerLogGenerator(
            seed=settings.seed,
            settings=settings,
            profile=profile,
            rom_hash=rom.sha1,
            changes=engine.get_changes(),
            warnings=engine.get_warnings(),
        )
        log_txt = os.path.join(tmp_dir, 'spoiler_test.txt')
        log_json = os.path.join(tmp_dir, 'spoiler_test.json')
        spoiler.generate_txt(log_txt)
        spoiler.generate_json(log_json)
        print(f"  Text log: {os.path.getsize(log_txt)} bytes")
        print(f"  JSON log: {os.path.getsize(log_json)} bytes")

        # Verify JSON log is valid
        with open(log_json, 'r') as f:
            log_data = json.load(f)
        print(f"  JSON log seed: {log_data['meta']['seed']}")
        print(f"  JSON log characters: {len(log_data['characters'])}")

        # Test settings string round-trip
        encoded = PresetManager.encode_settings_string(settings, profile['profile_id'])
        decoded = PresetManager.decode_settings_string(encoded)
        assert decoded is not None
        assert decoded['settings'].class_mode == settings.class_mode
        print(f"  Settings string round-trip: OK")

        print("\n" + "=" * 60)
        print(" ALL INTEGRATION TESTS PASSED ✅")
        print("=" * 60)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    test_full_pipeline()