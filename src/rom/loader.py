"""
ROM Loader: reads GBA ROM files, computes hashes, matches profiles.
"""
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any


class ROMData:
    """Holds the raw ROM bytes and metadata."""

    def __init__(self, filepath: str, data: bytes):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.data = bytearray(data)
        self.size = len(data)
        self.sha1 = hashlib.sha1(data).hexdigest()
        self.crc32 = format(self._compute_crc32(data), '08X')
        self.gba_title = self._read_gba_title(data)
        self.gba_game_code = self._read_game_code(data)

    @staticmethod
    def _compute_crc32(data: bytes) -> int:
        import zlib
        return zlib.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def _read_gba_title(data: bytes) -> str:
        """Read 12-byte game title from GBA header (offset 0xA0)."""
        if len(data) < 0xC0:
            return "UNKNOWN"
        raw = data[0xA0:0xAC]
        return raw.decode('ascii', errors='replace').strip('\x00').strip()

    @staticmethod
    def _read_game_code(data: bytes) -> str:
        """Read 4-byte game code from GBA header (offset 0xAC)."""
        if len(data) < 0xB0:
            return "????"
        raw = data[0xAC:0xB0]
        return raw.decode('ascii', errors='replace').strip('\x00').strip()

    def read_bytes(self, offset: int, length: int) -> bytes:
        """Read raw bytes from ROM."""
        if offset + length > self.size:
            raise ValueError(f"Read out of bounds: offset={offset}, length={length}, rom_size={self.size}")
        return bytes(self.data[offset:offset + length])

    def read_u8(self, offset: int) -> int:
        return self.data[offset]

    def read_s8(self, offset: int) -> int:
        return struct.unpack_from('b', self.data, offset)[0]

    def read_u16(self, offset: int) -> int:
        return struct.unpack_from('<H', self.data, offset)[0]

    def read_u32(self, offset: int) -> int:
        return struct.unpack_from('<I', self.data, offset)[0]

    def read_pointer(self, offset: int) -> int:
        """Read a GBA pointer (mask off 0x08000000)."""
        raw = self.read_u32(offset)
        if raw >= 0x08000000:
            return raw - 0x08000000
        return raw

    def write_u8(self, offset: int, value: int):
        self.data[offset] = value & 0xFF

    def write_s8(self, offset: int, value: int):
        struct.pack_into('b', self.data, offset, max(-128, min(127, value)))

    def write_u16(self, offset: int, value: int):
        struct.pack_into('<H', self.data, offset, value & 0xFFFF)

    def write_u32(self, offset: int, value: int):
        struct.pack_into('<I', self.data, offset, value & 0xFFFFFFFF)

    def get_modified_bytes(self) -> bytes:
        return bytes(self.data)


class ProfileManager:
    """Loads and manages ROM profiles."""

    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'profiles')
        self.profiles_dir = profiles_dir
        self.profiles: Dict[str, dict] = {}
        self._load_all_profiles()

    def _load_all_profiles(self):
        """Load all JSON profiles from the profiles directory."""
        if not os.path.isdir(self.profiles_dir):
            return
        for fname in os.listdir(self.profiles_dir):
            if fname.endswith('.json'):
                fpath = os.path.join(self.profiles_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    pid = profile.get('profile_id', fname)
                    self.profiles[pid] = profile
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load profile {fname}: {e}")

    def get_profile_list(self) -> List[dict]:
        """Return list of all loaded profiles with basic info."""
        result = []
        for pid, prof in self.profiles.items():
            result.append({
                'profile_id': pid,
                'display_name': prof.get('display_name', pid),
                'game': prof.get('game', '?'),
                'region': prof.get('region', '?'),
                'tier': prof.get('tier', 'C'),
            })
        return result

    def match_rom(self, rom: ROMData) -> Tuple[Optional[dict], str]:
        """
        Match a ROM against known profiles.
        Returns (profile_dict, tier) or (None, 'C').

        Matching priority:
        1. Exact SHA-1 match → Tier A/B (from profile)
        2. Exact CRC32 match → Tier A/B (from profile)
        3. Secondary signature match → Tier B
        4. Game code heuristic → Tier C
        """
        # Phase 1: Exact hash match
        for pid, prof in self.profiles.items():
            hashes = prof.get('hashes', {})
            sha1_list = hashes.get('sha1', [])
            crc32_list = hashes.get('crc32', [])

            if rom.sha1 in sha1_list or rom.crc32 in crc32_list:
                return prof, prof.get('tier', 'A')

        # Phase 2: Secondary signatures (for hack bases)
        for pid, prof in self.profiles.items():
            sigs = prof.get('secondary_signatures', [])
            for sig in sigs:
                addr = sig.get('address', 0)
                expected = sig.get('bytes', '')
                if expected and addr > 0:
                    try:
                        actual = rom.read_bytes(addr, len(expected) // 2)
                        if actual.hex() == expected.lower():
                            return prof, 'B'
                    except (ValueError, IndexError):
                        continue

        # Phase 3: Game code heuristic → Tier C
        # Prefer clean (Tier A) profiles over hack base profiles
        game_code_map = {
            'BE8E': ('fe8', 'US'),
            'BE8J': ('fe8', 'JP'),
            'BE8P': ('fe8', 'EU'),
            'BE7E': ('fe7', 'US'),
            'BE7J': ('fe7', 'JP'),
            'BE7P': ('fe7', 'EU'),
            'AFEJ': ('fe6', 'JP'),
        }
        code = rom.gba_game_code
        if code in game_code_map:
            game, region = game_code_map[code]
            # First pass: prefer Tier A (clean) profiles
            for pid, prof in self.profiles.items():
                if prof.get('game') == game and prof.get('tier') == 'A':
                    return prof, 'C'
            # Second pass: any matching game profile
            for pid, prof in self.profiles.items():
                if prof.get('game') == game:
                    return prof, 'C'

        return None, 'C'


class LayoutManager:
    """Loads table layout definitions."""

    def __init__(self, layouts_dir: str = None):
        if layouts_dir is None:
            layouts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'layouts')
        self.layouts_dir = layouts_dir
        self.layouts: Dict[str, dict] = {}
        self._load_all_layouts()

    def _load_all_layouts(self):
        if not os.path.isdir(self.layouts_dir):
            return
        for fname in os.listdir(self.layouts_dir):
            if fname.endswith('.json'):
                fpath = os.path.join(self.layouts_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        layout = json.load(f)
                    lid = layout.get('layout_id', fname.replace('.json', ''))
                    self.layouts[lid] = layout
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load layout {fname}: {e}")

    def get_layout(self, layout_id: str) -> Optional[dict]:
        return self.layouts.get(layout_id)


def load_rom(filepath: str) -> ROMData:
    """Load a ROM file from disk."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"ROM file not found: {filepath}")
    with open(filepath, 'rb') as f:
        data = f.read()
    if len(data) < 0x100:
        raise ValueError("File is too small to be a valid GBA ROM")
    # Check GBA ROM header magic (multiboot or normal)
    # Normal GBA ROMs start with a branch instruction
    return ROMData(filepath, data)