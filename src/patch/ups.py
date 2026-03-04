"""
UPS Patch Generator: creates UPS format patches (Universal Patching System).
UPS is a simpler XOR-based patch format commonly used for GBA ROMs.
"""
import struct
import zlib
from typing import Optional


class UPSPatcher:
    """Generate and apply UPS patches."""

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode an integer as a UPS variable-length integer."""
        buf = bytearray()
        while True:
            x = value & 0x7F
            value >>= 7
            if value == 0:
                buf.append(x | 0x80)
                break
            buf.append(x)
            value -= 1
        return bytes(buf)

    @staticmethod
    def _decode_varint(data: bytes, offset: int) -> tuple:
        """Decode a UPS variable-length integer. Returns (value, new_offset)."""
        result = 0
        shift = 1
        while True:
            if offset >= len(data):
                raise ValueError("Unexpected end of data while decoding varint")
            x = data[offset]
            offset += 1
            result += (x & 0x7F) * shift
            if x & 0x80:
                break
            shift <<= 7
            result += shift
        return result, offset

    @staticmethod
    def create_patch(original: bytes, modified: bytes) -> bytes:
        """
        Create a UPS patch from original and modified data.
        UPS format:
        - Header: "UPS1"
        - Source size (varint)
        - Target size (varint)
        - Blocks: [relative_offset(varint), xor_data..., 0x00 terminator]
        - Footer: source_crc32, target_crc32, patch_crc32 (each 4 bytes LE)
        """
        patch = bytearray()

        # Header
        patch.extend(b'UPS1')

        # Sizes
        patch.extend(UPSPatcher._encode_varint(len(original)))
        patch.extend(UPSPatcher._encode_varint(len(modified)))

        # Generate XOR diff blocks
        max_len = max(len(original), len(modified))
        pos = 0

        while pos < max_len:
            # Find next difference
            start = pos
            while pos < max_len:
                orig_byte = original[pos] if pos < len(original) else 0
                mod_byte = modified[pos] if pos < len(modified) else 0
                if orig_byte != mod_byte:
                    break
                pos += 1

            if pos >= max_len:
                break

            # Write relative offset from last position
            rel_offset = pos - start
            patch.extend(UPSPatcher._encode_varint(rel_offset))

            # Write XOR data until we hit a match (or end)
            while pos < max_len:
                orig_byte = original[pos] if pos < len(original) else 0
                mod_byte = modified[pos] if pos < len(modified) else 0
                xor_val = orig_byte ^ mod_byte
                patch.append(xor_val)
                pos += 1
                if xor_val == 0:
                    break

            # If we didn't end with a 0x00 terminator naturally, add one
            if patch[-1] != 0:
                # Need to continue — the block ends with a 0x00
                # Back up and handle this
                pass
            # UPS blocks are terminated by a 0x00 XOR byte

        # Footer: CRC32 checksums
        source_crc = zlib.crc32(original) & 0xFFFFFFFF
        target_crc = zlib.crc32(modified) & 0xFFFFFFFF
        patch.extend(struct.pack('<I', source_crc))
        patch.extend(struct.pack('<I', target_crc))

        # Patch CRC (of everything before this field)
        patch_crc = zlib.crc32(bytes(patch)) & 0xFFFFFFFF
        patch.extend(struct.pack('<I', patch_crc))

        return bytes(patch)

    @staticmethod
    def apply_patch(original: bytes, patch_data: bytes) -> bytes:
        """Apply a UPS patch to original data. Returns the patched result."""
        if patch_data[:4] != b'UPS1':
            raise ValueError("Invalid UPS patch: missing UPS1 header")

        offset = 4

        source_size, offset = UPSPatcher._decode_varint(patch_data, offset)
        target_size, offset = UPSPatcher._decode_varint(patch_data, offset)

        # Prepare output (start with original padded/trimmed to target size)
        output = bytearray(target_size)
        copy_len = min(len(original), target_size)
        output[:copy_len] = original[:copy_len]

        # Apply XOR blocks
        pos = 0
        actions_end = len(patch_data) - 12  # 3 CRC32 values

        while offset < actions_end:
            rel_offset, offset = UPSPatcher._decode_varint(patch_data, offset)
            pos += rel_offset

            while offset < actions_end:
                xor_byte = patch_data[offset]
                offset += 1
                if xor_byte == 0:
                    pos += 1
                    break
                if pos < target_size:
                    output[pos] ^= xor_byte
                pos += 1

        return bytes(output)

    @staticmethod
    def verify_patch(original: bytes, modified: bytes, patch_data: bytes) -> bool:
        """Verify that applying patch to original yields modified."""
        try:
            result = UPSPatcher.apply_patch(original, patch_data)
            return result == modified
        except Exception:
            return False