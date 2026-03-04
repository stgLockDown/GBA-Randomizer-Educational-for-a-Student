"""
BPS Patch Generator: creates BPS format patches (Binary Patching System).
BPS is the modern standard for ROM patching in the GBA hacking community.
"""
import struct
import zlib
from typing import Optional


class BPSPatcher:
    """Generate and apply BPS patches."""

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode an integer as a BPS variable-length integer."""
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
        """Decode a BPS variable-length integer. Returns (value, new_offset)."""
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
        Create a BPS patch from original and modified ROM data.
        Uses a linear diff approach (SourceRead, TargetRead, SourceCopy, TargetCopy).
        """
        patch = bytearray()

        # Header: "BPS1"
        patch.extend(b'BPS1')

        # Source size
        patch.extend(BPSPatcher._encode_varint(len(original)))
        # Target size
        patch.extend(BPSPatcher._encode_varint(len(modified)))
        # Metadata size (0 = no metadata)
        patch.extend(BPSPatcher._encode_varint(0))

        # Generate actions using a simple linear approach
        # We'll use SourceRead for matching bytes and TargetRead for differing bytes
        source_offset = 0
        output_offset = 0
        target_len = len(modified)
        source_len = len(original)

        while output_offset < target_len:
            # Find how many bytes match (SourceRead)
            match_len = 0
            while (output_offset + match_len < target_len and
                   source_offset + match_len < source_len and
                   original[source_offset + match_len] == modified[output_offset + match_len]):
                match_len += 1

            if match_len > 0:
                # SourceRead: action = (length - 1) << 2 | 0
                patch.extend(BPSPatcher._encode_varint((match_len - 1) << 2 | 0))
                source_offset += match_len
                output_offset += match_len
                continue

            # Find how many bytes differ (TargetRead)
            diff_start = output_offset
            while (output_offset < target_len and
                   (output_offset >= source_len or
                    original[output_offset] != modified[output_offset])):
                output_offset += 1
                source_offset += 1
                # Also break if we find a run of matching bytes ahead
                if (output_offset < target_len and
                    source_offset < source_len and
                    output_offset + 2 < target_len and
                    source_offset + 2 < source_len):
                    if (original[source_offset] == modified[output_offset] and
                        original[source_offset + 1] == modified[output_offset + 1] and
                        original[source_offset + 2] == modified[output_offset + 2]):
                        break

            diff_len = output_offset - diff_start
            if diff_len > 0:
                # TargetRead: action = (length - 1) << 2 | 1
                patch.extend(BPSPatcher._encode_varint((diff_len - 1) << 2 | 1))
                patch.extend(modified[diff_start:diff_start + diff_len])

        # If modified is longer than original, write remaining bytes
        if output_offset < target_len:
            remaining = target_len - output_offset
            patch.extend(BPSPatcher._encode_varint((remaining - 1) << 2 | 1))
            patch.extend(modified[output_offset:])

        # Footer checksums (CRC32)
        source_crc = zlib.crc32(original) & 0xFFFFFFFF
        target_crc = zlib.crc32(modified) & 0xFFFFFFFF
        patch.extend(struct.pack('<I', source_crc))
        patch.extend(struct.pack('<I', target_crc))

        # Patch CRC (of everything before this)
        patch_crc = zlib.crc32(bytes(patch)) & 0xFFFFFFFF
        patch.extend(struct.pack('<I', patch_crc))

        return bytes(patch)

    @staticmethod
    def apply_patch(original: bytes, patch_data: bytes) -> bytes:
        """Apply a BPS patch to original data. Returns the patched result."""
        if patch_data[:4] != b'BPS1':
            raise ValueError("Invalid BPS patch: missing BPS1 header")

        offset = 4

        source_size, offset = BPSPatcher._decode_varint(patch_data, offset)
        target_size, offset = BPSPatcher._decode_varint(patch_data, offset)
        meta_size, offset = BPSPatcher._decode_varint(patch_data, offset)

        # Skip metadata
        offset += meta_size

        if len(original) != source_size:
            raise ValueError(f"Source size mismatch: expected {source_size}, got {len(original)}")

        output = bytearray(target_size)
        output_pos = 0
        source_rel = 0
        target_rel = 0

        # Actions end 12 bytes before the end (3 CRC32 values)
        actions_end = len(patch_data) - 12

        while offset < actions_end:
            action, offset = BPSPatcher._decode_varint(patch_data, offset)
            command = action & 3
            length = (action >> 2) + 1

            if command == 0:  # SourceRead
                for i in range(length):
                    if output_pos < source_size:
                        output[output_pos] = original[output_pos]
                    output_pos += 1

            elif command == 1:  # TargetRead
                for i in range(length):
                    output[output_pos] = patch_data[offset]
                    offset += 1
                    output_pos += 1

            elif command == 2:  # SourceCopy
                data_val, offset = BPSPatcher._decode_varint(patch_data, offset)
                source_rel += (-1 if data_val & 1 else 1) * (data_val >> 1)
                for i in range(length):
                    output[output_pos] = original[source_rel]
                    source_rel += 1
                    output_pos += 1

            elif command == 3:  # TargetCopy
                data_val, offset = BPSPatcher._decode_varint(patch_data, offset)
                target_rel += (-1 if data_val & 1 else 1) * (data_val >> 1)
                for i in range(length):
                    output[output_pos] = output[target_rel]
                    target_rel += 1
                    output_pos += 1

        return bytes(output)

    @staticmethod
    def verify_patch(original: bytes, modified: bytes, patch_data: bytes) -> bool:
        """Verify that applying a patch to original produces modified."""
        try:
            result = BPSPatcher.apply_patch(original, patch_data)
            return result == modified
        except Exception:
            return False