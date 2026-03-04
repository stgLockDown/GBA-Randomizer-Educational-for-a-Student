"""
ROM Writer: handles atomic ROM output and patch file generation.
"""
import os
import tempfile
import shutil
from typing import Optional
from src.rom.loader import ROMData
from src.patch.bps import BPSPatcher
from src.patch.ups import UPSPatcher


class ROMWriter:
    """Writes modified ROM data to disk as ROM file or patch."""

    def __init__(self, original_rom: ROMData, modified_rom: ROMData):
        self.original = original_rom
        self.modified = modified_rom

    def write_rom(self, output_path: str) -> str:
        """
        Write modified ROM to disk using atomic write (temp file + rename).
        Returns the final output path.
        """
        output_path = self._ensure_extension(output_path, '.gba')
        dir_path = os.path.dirname(output_path) or '.'
        os.makedirs(dir_path, exist_ok=True)

        # Atomic write: write to temp file first, then rename
        fd, tmp_path = tempfile.mkstemp(suffix='.gba.tmp', dir=dir_path)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(self.modified.get_modified_bytes())
            # Rename temp to final
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(tmp_path, output_path)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return output_path

    def write_bps_patch(self, output_path: str, verify: bool = True) -> str:
        """
        Generate and write a BPS patch file.
        Returns the final output path.
        """
        output_path = self._ensure_extension(output_path, '.bps')
        dir_path = os.path.dirname(output_path) or '.'
        os.makedirs(dir_path, exist_ok=True)

        original_bytes = bytes(self.original.data)
        modified_bytes = self.modified.get_modified_bytes()

        patch_data = BPSPatcher.create_patch(original_bytes, modified_bytes)

        if verify:
            if not BPSPatcher.verify_patch(original_bytes, modified_bytes, patch_data):
                raise RuntimeError("BPS patch verification failed! Patch does not reproduce the modified ROM.")

        fd, tmp_path = tempfile.mkstemp(suffix='.bps.tmp', dir=dir_path)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(patch_data)
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(tmp_path, output_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return output_path

    def write_ups_patch(self, output_path: str, verify: bool = True) -> str:
        """
        Generate and write a UPS patch file.
        Returns the final output path.
        """
        output_path = self._ensure_extension(output_path, '.ups')
        dir_path = os.path.dirname(output_path) or '.'
        os.makedirs(dir_path, exist_ok=True)

        original_bytes = bytes(self.original.data)
        modified_bytes = self.modified.get_modified_bytes()

        patch_data = UPSPatcher.create_patch(original_bytes, modified_bytes)

        if verify:
            if not UPSPatcher.verify_patch(original_bytes, modified_bytes, patch_data):
                raise RuntimeError("UPS patch verification failed! Patch does not reproduce the modified ROM.")

        fd, tmp_path = tempfile.mkstemp(suffix='.ups.tmp', dir=dir_path)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(patch_data)
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(tmp_path, output_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return output_path

    @staticmethod
    def _ensure_extension(path: str, ext: str) -> str:
        """Ensure the path has the correct file extension."""
        if not path.lower().endswith(ext):
            path += ext
        return path

    @staticmethod
    def generate_output_filename(original_filename: str, seed: str, extension: str = '.gba') -> str:
        """Generate default output filename: OriginalName_Rand_{seed}.ext"""
        base = os.path.splitext(original_filename)[0]
        return f"{base}_Rand_{seed}{extension}"