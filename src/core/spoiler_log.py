"""
Spoiler Log Generator: produces txt and json logs of all changes.
"""
import json
import hashlib
import os
from typing import List, Dict, Optional
from datetime import datetime
from src.core.engine import RandomizerSettings, CharacterChange


class SpoilerLogGenerator:
    """Generates spoiler logs in txt and json format."""

    def __init__(self, seed: str, settings: RandomizerSettings, profile: dict,
                 rom_hash: str, changes: List[CharacterChange],
                 warnings: List[str], reroll_count: int = 0):
        self.seed = seed
        self.settings = settings
        self.profile = profile
        self.rom_hash = rom_hash
        self.changes = changes
        self.warnings = warnings
        self.reroll_count = reroll_count
        self.timestamp = datetime.now().isoformat()
        self.settings_hash = self._compute_settings_hash()

    def _compute_settings_hash(self) -> str:
        """Hash the settings dict for reproducibility verification."""
        s = json.dumps(self.settings.to_dict(), sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    def generate_txt(self, output_path: str):
        """Generate a human-readable text spoiler log."""
        lines = []
        lines.append("=" * 72)
        lines.append("  FIRE EMBLEM GBA RANDOMIZER — SPOILER LOG")
        lines.append("=" * 72)
        lines.append("")
        lines.append(f"  Timestamp:      {self.timestamp}")
        lines.append(f"  Seed:           {self.seed}")
        lines.append(f"  Settings Hash:  {self.settings_hash}")
        lines.append(f"  ROM Hash:       {self.rom_hash}")
        lines.append(f"  Profile:        {self.profile.get('display_name', 'Unknown')}")
        lines.append(f"  Profile ID:     {self.profile.get('profile_id', 'Unknown')}")
        lines.append(f"  Tier:           {self.profile.get('tier', '?')}")
        lines.append(f"  Reroll Count:   {self.reroll_count}")
        lines.append("")

        # Settings summary
        lines.append("-" * 72)
        lines.append("  SETTINGS")
        lines.append("-" * 72)
        sd = self.settings.to_dict()
        for key in ['class_mode', 'bases_mode', 'growths_mode', 'ranks_mode',
                     'inventory_mode', 'keep_lords', 'keep_thieves', 'keep_dancers',
                     'respect_gender', 'exclude_monsters', 'bases_variance',
                     'growths_variance', 'bases_preserve_total', 'growths_preserve_total',
                     'auto_fix', 'force_build']:
            if key in sd:
                lines.append(f"  {key:30s} = {sd[key]}")
        lines.append("")

        # Character changes
        lines.append("-" * 72)
        lines.append("  CHARACTER CHANGES")
        lines.append("-" * 72)
        lines.append("")

        for ch in self.changes:
            flags = []
            if ch.is_locked:
                flags.append("LOCKED")
            if ch.is_excluded:
                flags.append("EXCLUDED")
            if ch.flags:
                flags.extend(ch.flags)
            flag_str = f" [{', '.join(flags)}]" if flags else ""

            lines.append(f"  ▸ {ch.name} (ID {ch.char_id}){flag_str}")

            # Class change
            if ch.old_class_id != ch.new_class_id:
                lines.append(f"    Class: {ch.old_class_id} → {ch.new_class_id}")
            else:
                lines.append(f"    Class: {ch.old_class_id} (unchanged)")

            # Bases
            base_changes = self._format_stat_diff(ch.old_bases, ch.new_bases)
            if base_changes:
                lines.append(f"    Bases: {base_changes}")

            # Growths
            growth_changes = self._format_stat_diff(ch.old_growths, ch.new_growths)
            if growth_changes:
                lines.append(f"    Growths: {growth_changes}")

            # Ranks
            rank_changes = self._format_stat_diff(ch.old_ranks, ch.new_ranks)
            if rank_changes:
                lines.append(f"    Ranks: {rank_changes}")

            # Items
            item_changes = self._format_stat_diff(ch.old_items, ch.new_items)
            if item_changes:
                lines.append(f"    Items: {item_changes}")

            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("-" * 72)
            lines.append("  WARNINGS")
            lines.append("-" * 72)
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
            lines.append("")

        lines.append("=" * 72)
        lines.append("  END OF SPOILER LOG")
        lines.append("=" * 72)

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def generate_json(self, output_path: str):
        """Generate a machine-readable JSON spoiler log."""
        data = {
            "meta": {
                "timestamp": self.timestamp,
                "seed": self.seed,
                "settings_hash": self.settings_hash,
                "rom_hash": self.rom_hash,
                "profile_name": self.profile.get('display_name', 'Unknown'),
                "profile_id": self.profile.get('profile_id', 'Unknown'),
                "tier": self.profile.get('tier', '?'),
                "reroll_count": self.reroll_count,
            },
            "settings": self.settings.to_dict(),
            "characters": [],
            "warnings": self.warnings,
        }

        for ch in self.changes:
            char_data = {
                "char_id": ch.char_id,
                "name": ch.name,
                "is_locked": ch.is_locked,
                "is_excluded": ch.is_excluded,
                "flags": ch.flags,
                "class": {
                    "old": ch.old_class_id,
                    "new": ch.new_class_id,
                    "changed": ch.old_class_id != ch.new_class_id,
                },
                "bases": {
                    "old": ch.old_bases,
                    "new": ch.new_bases,
                    "deltas": {k: ch.new_bases.get(k, 0) - ch.old_bases.get(k, 0)
                               for k in ch.old_bases},
                },
                "growths": {
                    "old": ch.old_growths,
                    "new": ch.new_growths,
                    "deltas": {k: ch.new_growths.get(k, 0) - ch.old_growths.get(k, 0)
                               for k in ch.old_growths},
                },
                "ranks": {
                    "old": ch.old_ranks,
                    "new": ch.new_ranks,
                    "deltas": {k: ch.new_ranks.get(k, 0) - ch.old_ranks.get(k, 0)
                               for k in ch.old_ranks},
                },
                "items": {
                    "old": ch.old_items,
                    "new": ch.new_items,
                    "changed": ch.old_items != ch.new_items,
                },
            }
            data["characters"].append(char_data)

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _format_stat_diff(self, old: Dict[str, int], new: Dict[str, int]) -> str:
        """Format stat differences as a compact string."""
        parts = []
        all_same = True
        for key in old:
            o = old.get(key, 0)
            n = new.get(key, 0)
            diff = n - o
            short_name = key.split('_')[-1][:3].upper()
            if diff != 0:
                all_same = False
                sign = "+" if diff > 0 else ""
                parts.append(f"{short_name}:{o}→{n}({sign}{diff})")
            else:
                parts.append(f"{short_name}:{o}")

        if all_same:
            return "(unchanged)"
        return " | ".join(parts)