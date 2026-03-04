"""
Presets & Shareable Settings: load/save/export/import randomizer configurations.
"""
import json
import base64
import hashlib
import os
from typing import Optional, List, Dict
from src.core.engine import RandomizerSettings


class PresetManager:
    """Manages preset files and shareable settings strings."""

    def __init__(self, presets_dir: str = None):
        if presets_dir is None:
            presets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'presets')
        self.presets_dir = presets_dir
        self.presets: Dict[str, dict] = {}
        self._load_all_presets()

    def _load_all_presets(self):
        """Load all JSON presets from the presets directory."""
        if not os.path.isdir(self.presets_dir):
            return
        for fname in sorted(os.listdir(self.presets_dir)):
            if fname.endswith('.json'):
                fpath = os.path.join(self.presets_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        preset = json.load(f)
                    name = preset.get('name', fname.replace('.json', ''))
                    self.presets[name] = preset
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load preset {fname}: {e}")

    def get_preset_names(self) -> List[str]:
        """Return sorted list of available preset names."""
        return sorted(self.presets.keys())

    def get_preset(self, name: str) -> Optional[dict]:
        """Get a preset by name."""
        return self.presets.get(name)

    def apply_preset(self, name: str) -> Optional[RandomizerSettings]:
        """Load a preset and return a RandomizerSettings object."""
        preset = self.presets.get(name)
        if not preset:
            return None
        settings_data = preset.get('settings', {})
        return RandomizerSettings.from_dict(settings_data)

    def save_preset(self, name: str, settings: RandomizerSettings,
                    description: str = "") -> str:
        """Save current settings as a named preset. Returns filepath."""
        os.makedirs(self.presets_dir, exist_ok=True)

        preset = {
            "name": name,
            "description": description,
            "version": "1.0",
            "settings": settings.to_dict(),
        }

        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        filepath = os.path.join(self.presets_dir, f"{safe_name}.json")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2, ensure_ascii=False)

        self.presets[name] = preset
        return filepath

    def delete_preset(self, name: str) -> bool:
        """Delete a preset by name."""
        if name not in self.presets:
            return False

        preset = self.presets[name]
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        filepath = os.path.join(self.presets_dir, f"{safe_name}.json")

        if os.path.exists(filepath):
            os.remove(filepath)

        del self.presets[name]
        return True

    # ─── Shareable Settings String ────────────────────────────────────

    @staticmethod
    def encode_settings_string(settings: RandomizerSettings, profile_id: str = "") -> str:
        """
        Encode settings + profile_id as a shareable base64 string.
        Format: base64(json({profile_id, settings, checksum}))
        """
        payload = {
            "v": 1,  # format version
            "p": profile_id,
            "s": settings.to_dict(),
        }
        json_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        checksum = hashlib.md5(json_str.encode()).hexdigest()[:8]
        payload["c"] = checksum
        json_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)

        encoded = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('ascii')
        return f"FEGBA:{encoded}"

    @staticmethod
    def decode_settings_string(encoded_str: str) -> Optional[Dict]:
        """
        Decode a shareable settings string.
        Returns dict with 'profile_id' and 'settings' (RandomizerSettings), or None on failure.
        """
        try:
            if encoded_str.startswith("FEGBA:"):
                encoded_str = encoded_str[6:]

            json_bytes = base64.urlsafe_b64decode(encoded_str.encode('ascii'))
            payload = json.loads(json_bytes.decode('utf-8'))

            if payload.get("v") != 1:
                return None

            # Verify checksum
            stored_checksum = payload.pop("c", "")
            json_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            expected_checksum = hashlib.md5(json_str.encode()).hexdigest()[:8]

            if stored_checksum != expected_checksum:
                return None

            settings = RandomizerSettings.from_dict(payload.get("s", {}))

            return {
                "profile_id": payload.get("p", ""),
                "settings": settings,
            }

        except Exception:
            return None