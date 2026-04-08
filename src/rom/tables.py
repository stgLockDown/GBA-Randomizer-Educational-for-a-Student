"""
Table Reader/Writer: reads and writes structured data from ROM using layout definitions.
"""
import struct
from typing import Dict, List, Optional, Any
from src.rom.loader import ROMData, LayoutManager


class TableEntry:
    """Represents a single entry in a ROM table."""

    def __init__(self, index: int, raw_bytes: bytes, layout: dict):
        self.index = index
        self.layout = layout
        self.fields: Dict[str, Any] = {}
        self.original_fields: Dict[str, Any] = {}
        self._parse(raw_bytes)
        self.original_fields = dict(self.fields)

    def _parse(self, raw: bytes):
        """Parse raw bytes into named fields using layout definition."""
        for field_def in self.layout.get('fields', []):
            name = field_def['name']
            offset = field_def['offset']
            ftype = field_def['type']
            
            # Get size for bytes type, default to entry_size if not specified
            size = field_def.get('size', self.layout['entry_size'] - offset)

            if ftype == 'uint8':
                self.fields[name] = raw[offset]
            elif ftype == 'int8':
                self.fields[name] = struct.unpack_from('b', raw, offset)[0]
            elif ftype == 'uint16':
                self.fields[name] = struct.unpack_from('<H', raw, offset)[0]
            elif ftype == 'int16':
                self.fields[name] = struct.unpack_from('<h', raw, offset)[0]
            elif ftype == 'uint32' or ftype == 'pointer':
                self.fields[name] = struct.unpack_from('<I', raw, offset)[0]
            elif ftype == 'bytes':
                self.fields[name] = bytes(raw[offset:offset + size])
            else:
                self.fields[name] = bytes(raw[offset:offset + size])

    def to_bytes(self) -> bytes:
        """Serialize fields back to raw bytes."""
        entry_size = self.layout['entry_size']
        buf = bytearray(entry_size)

        for field_def in self.layout.get('fields', []):
            name = field_def['name']
            offset = field_def['offset']
            ftype = field_def['type']
            
            # Get size for bytes type, default to entry_size if not specified
            size = field_def.get('size', entry_size - offset)
            
            # CRITICAL FIX: Use original value if field wasn't modified
            # This prevents corrupting pointers and other unmodified fields
            if name in self.fields:
                value = self.fields[name]
            else:
                value = self.original_fields.get(name, 0)

            if ftype == 'uint8':
                buf[offset] = value & 0xFF
            elif ftype == 'int8':
                struct.pack_into('b', buf, offset, max(-128, min(127, value)))
            elif ftype == 'uint16':
                struct.pack_into('<H', buf, offset, value & 0xFFFF)
            elif ftype == 'int16':
                struct.pack_into('<h', buf, offset, max(-32768, min(32767, value)))
            elif ftype == 'uint32' or ftype == 'pointer':
                struct.pack_into('<I', buf, offset, value & 0xFFFFFFFF)
            elif ftype == 'bytes':
                if isinstance(value, (bytes, bytearray)):
                    buf[offset:offset + size] = value[:size]
            else:
                if isinstance(value, (bytes, bytearray)):
                    buf[offset:offset + size] = value[:size]

        return bytes(buf)

    def get(self, field_name: str, default=None):
        return self.fields.get(field_name, default)

    def set(self, field_name: str, value):
        self.fields[field_name] = value

    def get_original(self, field_name: str, default=None):
        return self.original_fields.get(field_name, default)

    def is_modified(self, field_name: str = None) -> bool:
        """Check if a specific field or any field has been modified."""
        if field_name:
            return self.fields.get(field_name) != self.original_fields.get(field_name)
        return self.fields != self.original_fields

    def get_stat_values(self, stat_group: str) -> Dict[str, int]:
        """Get stat values for a group (bases, growths, ranks, items)."""
        stat_fields = self.layout.get('stat_fields', {})
        field_names = stat_fields.get(stat_group, [])
        return {name: self.fields.get(name, 0) for name in field_names}

    def get_original_stat_values(self, stat_group: str) -> Dict[str, int]:
        """Get original stat values for a group."""
        stat_fields = self.layout.get('stat_fields', {})
        field_names = stat_fields.get(stat_group, [])
        return {name: self.original_fields.get(name, 0) for name in field_names}

    def set_stat_values(self, stat_group: str, values: Dict[str, int]):
        """Set stat values for a group."""
        stat_fields = self.layout.get('stat_fields', {})
        field_names = stat_fields.get(stat_group, [])
        for name in field_names:
            if name in values:
                self.fields[name] = values[name]


class ROMTable:
    """Represents a table of entries read from ROM."""

    def __init__(self, table_name: str, entries: List[TableEntry], base_address: int, layout: dict):
        self.table_name = table_name
        self.entries = entries
        self.base_address = base_address
        self.layout = layout
        self.entry_size = layout['entry_size']

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index: int) -> TableEntry:
        return self.entries[index]

    def __iter__(self):
        return iter(self.entries)

    def get_entry(self, index: int) -> Optional[TableEntry]:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None

    def get_modified_entries(self) -> List[TableEntry]:
        """Return entries that have been modified."""
        return [e for e in self.entries if e.is_modified()]


class TableManager:
    """Reads/writes tables from ROM using profiles and layouts."""

    def __init__(self, rom: ROMData, profile: dict, layout_manager: LayoutManager):
        self.rom = rom
        self.profile = profile
        self.layout_manager = layout_manager
        self.tables: Dict[str, ROMTable] = {}

    def load_table(self, table_name: str) -> Optional[ROMTable]:
        """Load a table from ROM using profile definitions."""
        tables_config = self.profile.get('tables', {})
        table_config = tables_config.get(table_name)
        if not table_config:
            return None

        layout_id = table_config.get('layout')
        layout = self.layout_manager.get_layout(layout_id)
        if not layout:
            raise ValueError(f"Layout '{layout_id}' not found for table '{table_name}'")

        # Resolve table address (direct or via pointer)
        address = table_config.get('address')
        pointer_address = table_config.get('pointer_address')

        if pointer_address is not None and address is None:
            address = self.rom.read_pointer(pointer_address)

        if address is None or address <= 0:
            raise ValueError(f"Cannot resolve address for table '{table_name}'")

        count = table_config.get('count', 0)
        entry_size = table_config.get('entry_size', layout['entry_size'])

        entries = []
        for i in range(count):
            offset = address + (i * entry_size)
            try:
                raw = self.rom.read_bytes(offset, entry_size)
                entry = TableEntry(i, raw, layout)
                entries.append(entry)
            except ValueError:
                break

        table = ROMTable(table_name, entries, address, layout)
        self.tables[table_name] = table
        return table

    def load_all_tables(self) -> Dict[str, ROMTable]:
        """Load all tables defined in the profile."""
        tables_config = self.profile.get('tables', {})
        for table_name in tables_config:
            try:
                self.load_table(table_name)
            except (ValueError, KeyError) as e:
                print(f"Warning: Failed to load table '{table_name}': {e}")
        return self.tables

    def write_table(self, table_name: str):
        """Write modified table entries back to ROM."""
        table = self.tables.get(table_name)
        if not table:
            return

        for entry in table.entries:
            if entry.is_modified():
                offset = table.base_address + (entry.index * table.entry_size)
                raw = entry.to_bytes()
                for i, byte in enumerate(raw):
                    self.rom.write_u8(offset + i, byte)

    def write_all_tables(self):
        """Write all modified tables back to ROM."""
        for table_name in self.tables:
            self.write_table(table_name)