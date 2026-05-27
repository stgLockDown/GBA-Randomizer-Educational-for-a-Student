"""
Core Randomization Engine: orchestrates all randomization modules.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from src.core.rng import RNGEngine
from src.rom.tables import TableManager, ROMTable, TableEntry


@dataclass
class RandomizerSettings:
    """All user-configurable randomization settings."""

    # Class randomization
    class_mode: str = "vanilla"  # vanilla / shuffle / random
    keep_lords: bool = True
    keep_thieves: bool = True
    keep_dancers: bool = True
    respect_gender: bool = True
    exclude_monsters: bool = True
    allowed_class_ids: List[int] = field(default_factory=list)
    max_class_copies: int = 0  # 0 = unlimited
    class_weights: Dict[int, float] = field(default_factory=dict)

    # Bases randomization
    bases_mode: str = "vanilla"  # vanilla / shuffle / random
    bases_variance: int = 3  # ±N per stat
    bases_preserve_total: bool = False
    bases_min: int = 0
    bases_max: int = 30

    # Growths randomization
    growths_mode: str = "vanilla"  # vanilla / shuffle / random
    growths_variance: int = 20  # ±N per stat
    growths_preserve_total: bool = False
    growths_min: int = 5
    growths_max: int = 100

    # Ranks randomization
    ranks_mode: str = "vanilla"  # vanilla / shuffle / random
    ranks_variance: int = 30
    ranks_fix_weapon: str = "raise_rank"  # raise_rank / swap_weapon / none

    # Inventory randomization
    inventory_mode: str = "dont_change"  # dont_change / guarantee_usable / random_consumables / full_random
    inventory_blacklist_ids: List[int] = field(default_factory=list)

    # Per-character locks and exclusions
    character_locks: Dict[int, Dict[str, bool]] = field(default_factory=dict)
    excluded_character_ids: List[int] = field(default_factory=list)

    # Output
    output_mode: str = "rom"  # rom / bps / ups
    output_path: str = ""
    seed: str = ""

    # Advanced
    force_build: bool = False
    auto_fix: bool = True

    def to_dict(self) -> dict:
        """Serialize settings to a JSON-safe dict."""
        return {
            'class_mode': self.class_mode,
            'keep_lords': self.keep_lords,
            'keep_thieves': self.keep_thieves,
            'keep_dancers': self.keep_dancers,
            'respect_gender': self.respect_gender,
            'exclude_monsters': self.exclude_monsters,
            'allowed_class_ids': self.allowed_class_ids,
            'max_class_copies': self.max_class_copies,
            'class_weights': {str(k): v for k, v in self.class_weights.items()},
            'bases_mode': self.bases_mode,
            'bases_variance': self.bases_variance,
            'bases_preserve_total': self.bases_preserve_total,
            'bases_min': self.bases_min,
            'bases_max': self.bases_max,
            'growths_mode': self.growths_mode,
            'growths_variance': self.growths_variance,
            'growths_preserve_total': self.growths_preserve_total,
            'growths_min': self.growths_min,
            'growths_max': self.growths_max,
            'ranks_mode': self.ranks_mode,
            'ranks_variance': self.ranks_variance,
            'ranks_fix_weapon': self.ranks_fix_weapon,
            'inventory_mode': self.inventory_mode,
            'inventory_blacklist_ids': self.inventory_blacklist_ids,
            'character_locks': {str(k): v for k, v in self.character_locks.items()},
            'excluded_character_ids': self.excluded_character_ids,
            'output_mode': self.output_mode,
            'seed': self.seed,
            'force_build': self.force_build,
            'auto_fix': self.auto_fix,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'RandomizerSettings':
        """Deserialize from dict."""
        s = cls()
        for key, val in d.items():
            if key == 'class_weights':
                s.class_weights = {int(k): v for k, v in val.items()}
            elif key == 'character_locks':
                s.character_locks = {int(k): v for k, v in val.items()}
            elif hasattr(s, key):
                setattr(s, key, val)
        return s


@dataclass
class CharacterChange:
    """Tracks before/after state for one character."""
    char_id: int
    name: str
    old_class_id: int
    new_class_id: int
    old_bases: Dict[str, int]
    new_bases: Dict[str, int]
    old_growths: Dict[str, int]
    new_growths: Dict[str, int]
    old_ranks: Dict[str, int]
    new_ranks: Dict[str, int]
    old_items: Dict[str, int]
    new_items: Dict[str, int]
    is_locked: bool = False
    is_excluded: bool = False
    flags: List[str] = field(default_factory=list)


class RandomizationEngine:
    """Main engine that runs all randomization passes."""

    def __init__(self, table_manager: TableManager, settings: RandomizerSettings,
                 profile: dict, rng: RNGEngine):
        self.tm = table_manager
        self.settings = settings
        self.profile = profile
        self.rng = rng
        self.changes: List[CharacterChange] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.reroll_count = 0

    def run(self) -> bool:
        """Execute all randomization passes. Returns True if successful."""
        char_table = self.tm.tables.get('characters')
        class_table = self.tm.tables.get('classes')

        if not char_table:
            self.errors.append("Character table not loaded.")
            return False

        # ---- Translation-patch awareness ----
        # If the profile is marked as a translation patch, emit warnings up front
        # and apply the safety guard that forcibly disables unsafe operations.
        translation_meta = self.profile.get('translation_metadata', {}) or {}
        if translation_meta.get('is_translation_patch'):
            self.warnings.append(
                "TRANSLATION PATCH DETECTED: data tables may be relocated; "
                "running in safe-mode (only operations explicitly enabled by the "
                "profile's feature_flags will run)."
            )
            for w in (self.profile.get('warnings') or []):
                self.warnings.append(w)

        # Build character metadata from profile
        char_meta = self.profile.get('characters', {})
        rules = self.profile.get('rules', {})
        features = dict(self.profile.get('feature_flags', {}))

        # Apply translation safety guard: forcibly disable unsafe operations
        # listed in the profile's known_unsafe_operations, even if a user
        # manually re-enables them in the UI.
        if translation_meta.get('is_translation_patch'):
            self._apply_translation_safety_guard(features, translation_meta)

        # ---- Pre-flight character table sanity check ----
        # Detect garbage table data (translated ROMs whose tables have moved).
        sanity_ok, sanity_msg = self._sanity_check_character_table(char_table)
        if not sanity_ok:
            self.warnings.append(
                f"CHARACTER TABLE SANITY CHECK FAILED: {sanity_msg} "
                "Destructive randomization passes will be skipped to protect the ROM."
            )

            # If sanity check failed, force-disable destructive feature flags.
            for unsafe_flag in (
                'supports_class_randomization',
                'supports_bases_randomization',
                'supports_ranks_randomization',
                'supports_inventory_randomization',
            ):
                features[unsafe_flag] = False

            # Force vanilla settings for all disabled features
            self.settings.class_mode = "vanilla"
            self.settings.bases_mode = "vanilla"
            self.settings.ranks_mode = "vanilla"
            self.settings.inventory_mode = "dont_change"

            # Even growths can't be safely written if the character table is
            # corrupt -- the addresses being written would land on unrelated
            # bytes. Refuse to randomize anything unless the user explicitly
            # opts in via force_build. The build pipeline checks
            # ``len(engine.errors) == 0`` and will abort cleanly.
            if not getattr(self.settings, 'force_build', False):
                features['supports_growths_randomization'] = False
                self.settings.growths_mode = "vanilla"
                self.errors.append(
                    "Refusing to randomize: the character table on this ROM "
                    "looks corrupt (wrong addresses for this build). No bytes "
                    "have been written. Use the original Japanese FE6 ROM, or "
                    "enable Advanced -> Force Build to override at your own risk."
                )

        # Filter to valid/playable characters
        playable_indices = self._get_playable_indices(char_table, char_meta)

        # Pre-record original state
        for idx in playable_indices:
            entry = char_table[idx]
            cid = entry.get('char_id', idx)
            meta = char_meta.get(str(cid), char_meta.get(str(idx), {}))
            name = meta.get('name', f'Char_{cid}')

            self.changes.append(CharacterChange(
                char_id=cid,
                name=name,
                old_class_id=entry.get('class_id', 0),
                new_class_id=entry.get('class_id', 0),
                old_bases=entry.get_stat_values('bases'),
                new_bases=entry.get_stat_values('bases'),
                old_growths=entry.get_stat_values('growths'),
                new_growths=entry.get_stat_values('growths'),
                old_ranks=entry.get_stat_values('ranks'),
                new_ranks=entry.get_stat_values('ranks'),
                old_items=entry.get_stat_values('items'),
                new_items=entry.get_stat_values('items'),
                is_locked=self._is_fully_locked(cid),
                is_excluded=cid in self.settings.excluded_character_ids,
            ))

        # Run passes in order
        if features.get('supports_class_randomization', True):
            self._randomize_classes(char_table, class_table, playable_indices, char_meta, rules)

        if features.get('supports_bases_randomization', True):
            self._randomize_bases(char_table, playable_indices, char_meta)

        if features.get('supports_growths_randomization', True):
            self._randomize_growths(char_table, playable_indices, char_meta)

        if features.get('supports_ranks_randomization', True):
            self._randomize_ranks(char_table, playable_indices, char_meta)

        if features.get('supports_inventory_randomization', True):
            self._randomize_inventory(char_table, playable_indices, char_meta)

        # Update change records with new values
        for change in self.changes:
            idx = self._find_entry_index(char_table, change.char_id, playable_indices)
            if idx is not None:
                entry = char_table[idx]
                change.new_class_id = entry.get('class_id', 0)
                change.new_bases = entry.get_stat_values('bases')
                change.new_growths = entry.get_stat_values('growths')
                change.new_ranks = entry.get_stat_values('ranks')
                change.new_items = entry.get_stat_values('items')

        return len(self.errors) == 0

    def _sanity_check_character_table(self, char_table: ROMTable) -> Tuple[bool, str]:
        """
        Heuristic check that the character table actually contains plausible
        FE GBA character data. On translated ROMs, the table addresses listed
        in the profile may point at unrelated bytes, producing absurd values.

        Returns (ok, message). ``ok=False`` means the table looks corrupt
        and destructive randomization passes should be skipped.
        """
        char_meta = self.profile.get('characters', {})
        if not char_meta:
            return True, "No character metadata to compare against."

        suspicious = 0
        checked = 0

        for entry in char_table.entries[:64]:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid)) or char_meta.get(str(entry.index))
            if not meta:
                continue
            checked += 1

            # 1. char_id should fit in a single byte
            try:
                raw_cid = entry.get('char_id', 0)
                if raw_cid < 0 or raw_cid > 0xFF:
                    suspicious += 1
                    continue
            except Exception:
                suspicious += 1
                continue

            # 2. base HP should be a small positive number
            bases = entry.get_stat_values('bases') or {}
            hp = bases.get('hp', bases.get('base_hp', None))
            if hp is not None:
                if hp <= 0 or hp > 80:
                    suspicious += 1
                    continue

            # 3. Growths should each be in [0, 200]
            growths = entry.get_stat_values('growths') or {}
            bad_growth = any((g < 0 or g > 200) for g in growths.values())
            if bad_growth:
                suspicious += 1
                continue

        if checked == 0:
            return True, "No metadata-mapped entries to verify."

        ratio = suspicious / max(1, checked)
        if ratio >= 0.5:
            return False, (
                f"{suspicious}/{checked} sampled characters had implausible "
                f"values (HP out of range, growths outside [0,200], or invalid "
                f"char_id). The table addresses in the profile probably do not "
                f"point at real character data on this ROM."
            )
        return True, f"Sanity check passed ({checked - suspicious}/{checked} ok)."

    def _get_playable_indices(self, char_table: ROMTable, char_meta: dict) -> List[int]:
        """Determine which table entries are playable characters."""
        playable = []
        for entry in char_table:
            cid = entry.get('char_id', entry.index)
            if str(cid) in char_meta or str(entry.index) in char_meta:
                playable.append(entry.index)
        return playable

    def _is_fully_locked(self, char_id: int) -> bool:
        """Check if all aspects of a character are locked."""
        locks = self.settings.character_locks.get(char_id, {})
        return all(locks.get(k, False) for k in ['class', 'bases', 'growths', 'ranks', 'items'])

    def _is_field_locked(self, char_id: int, field_name: str) -> bool:
        locks = self.settings.character_locks.get(char_id, {})
        return locks.get(field_name, False)

    def _apply_translation_safety_guard(self, features: dict, translation_meta: dict) -> None:
        """Enforce safety constraints for translation-patched ROMs.

        If the profile indicates this is a translation patch, forcibly disable
        any randomization features listed in known_unsafe_operations. This
        prevents data corruption even if a user manually enables those features
        in the UI.
        """
        unsafe_ops = translation_meta.get('known_unsafe_operations', [])
        feature_map = {
            'class_randomization': 'supports_class_randomization',
            'bases_randomization': 'supports_bases_randomization',
            'ranks_randomization': 'supports_ranks_randomization',
            'inventory_randomization': 'supports_inventory_randomization',
            'recruitment_shuffle': 'supports_recruitment_shuffle',
            'skill_tables': 'supports_skill_tables',
            'cosmetic_randomization': 'supports_cosmetic_randomization',
        }

        for op in unsafe_ops:
            flag_key = feature_map.get(op)
            if flag_key and features.get(flag_key, True):
                features[flag_key] = False
                self.warnings.append(
                    f"Translation safety: forcibly disabled '{op}' — "
                    f"this operation is unsafe for the detected translation patch."
                )

        # Also force vanilla mode for any disabled features in settings
        if not features.get('supports_class_randomization', True):
            self.settings.class_mode = "vanilla"
        if not features.get('supports_bases_randomization', True):
            self.settings.bases_mode = "vanilla"
        if not features.get('supports_growths_randomization', True):
            self.settings.growths_mode = "vanilla"
        if not features.get('supports_ranks_randomization', True):
            self.settings.ranks_mode = "vanilla"
        if not features.get('supports_inventory_randomization', True):
            self.settings.inventory_mode = "dont_change"

    def _find_entry_index(self, table: ROMTable, char_id: int, indices: List[int]) -> Optional[int]:
        for idx in indices:
            if table[idx].get('char_id', idx) == char_id:
                return idx
        return None

    # ─── CLASS RANDOMIZATION ───────────────────────────────────────────

    def _randomize_classes(self, char_table: ROMTable, class_table: Optional[ROMTable],
                           indices: List[int], char_meta: dict, rules: dict):
        if self.settings.class_mode == "vanilla":
            return

        rng = self.rng.fork("classes")
        lord_ids = set(rules.get('lord_character_ids', []))
        thief_ids = set(rules.get('thief_character_ids', []))
        dancer_ids = set(rules.get('dancer_character_ids', []))
        lord_class_ids = set(rules.get('lord_class_ids', []))
        monster_class_ids = set(rules.get('monster_class_ids', []))
        gender_rules = rules.get('gender_locked_classes', {})
        female_only = set(gender_rules.get('female_only', []))
        male_only = set(gender_rules.get('male_only', []))

        # Build allowed class pool
        allowed = self._build_class_pool(class_table, monster_class_ids, lord_class_ids)
        if not allowed:
            self.warnings.append("No valid classes in pool; skipping class randomization.")
            return

        class_count_tracker: Dict[int, int] = {}

        if self.settings.class_mode == "shuffle":
            self._shuffle_classes(char_table, indices, char_meta, lord_ids, thief_ids,
                                  dancer_ids, rng)
        elif self.settings.class_mode == "random":
            for idx in indices:
                entry = char_table[idx]
                cid = entry.get('char_id', idx)

                if cid in self.settings.excluded_character_ids:
                    continue
                if self._is_field_locked(cid, 'class'):
                    continue
                if self.settings.keep_lords and cid in lord_ids:
                    continue
                if self.settings.keep_thieves and cid in thief_ids:
                    continue
                if self.settings.keep_dancers and cid in dancer_ids:
                    continue

                # Determine gender filter
                meta = char_meta.get(str(cid), {})
                pool = list(allowed)

                if self.settings.respect_gender and class_table:
                    pool = self._filter_by_gender(pool, class_table, meta,
                                                  female_only, male_only)

                if not pool:
                    self.warnings.append(f"No valid class for character {cid}; keeping original.")
                    continue

                # Apply max copies constraint
                if self.settings.max_class_copies > 0:
                    pool = [c for c in pool
                            if class_count_tracker.get(c, 0) < self.settings.max_class_copies]
                    if not pool:
                        pool = list(allowed)  # fallback

                # Weighted or uniform selection
                if self.settings.class_weights:
                    weights = [self.settings.class_weights.get(c, 1.0) for c in pool]
                    new_class = rng.choices_weighted(pool, weights, k=1)[0]
                else:
                    new_class = rng.choice(pool)

                entry.set('class_id', new_class)
                class_count_tracker[new_class] = class_count_tracker.get(new_class, 0) + 1

    def _build_class_pool(self, class_table: Optional[ROMTable],
                          monster_ids: set, lord_ids: set) -> List[int]:
        """Build the pool of allowed class IDs."""
        if self.settings.allowed_class_ids:
            pool = list(self.settings.allowed_class_ids)
        elif class_table:
            pool = [e.get('class_id', e.index) for e in class_table]
        else:
            pool = list(range(1, 80))

        if self.settings.exclude_monsters:
            pool = [c for c in pool if c not in monster_ids]

        # Exclude lord classes from general pool
        if self.settings.keep_lords:
            pool = [c for c in pool if c not in lord_ids]

        # Remove class 0 (usually null/invalid)
        pool = [c for c in pool if c > 0]
        return pool

    def _filter_by_gender(self, pool: List[int], class_table: ROMTable,
                          meta: dict, female_only: set, male_only: set) -> List[int]:
        """Filter class pool by character gender constraints."""
        # Try to determine gender from meta or portrait conventions
        # For now, assume metadata has a gender hint or we check the class table
        is_female = meta.get('is_female', False)

        if is_female:
            return [c for c in pool if c not in male_only]
        else:
            return [c for c in pool if c not in female_only]

    def _shuffle_classes(self, char_table: ROMTable, indices: List[int],
                         char_meta: dict, lord_ids: set, thief_ids: set,
                         dancer_ids: set, rng: RNGEngine):
        """Shuffle classes among characters (1:1 swap)."""
        shuffleable = []
        fixed = []

        for idx in indices:
            entry = char_table[idx]
            cid = entry.get('char_id', idx)

            if cid in self.settings.excluded_character_ids:
                fixed.append(idx)
                continue
            if self._is_field_locked(cid, 'class'):
                fixed.append(idx)
                continue
            if self.settings.keep_lords and cid in lord_ids:
                fixed.append(idx)
                continue
            if self.settings.keep_thieves and cid in thief_ids:
                fixed.append(idx)
                continue
            if self.settings.keep_dancers and cid in dancer_ids:
                fixed.append(idx)
                continue

            shuffleable.append(idx)

        if len(shuffleable) < 2:
            return

        class_ids = [char_table[idx].get('class_id', 0) for idx in shuffleable]
        rng.shuffle(class_ids)

        for i, idx in enumerate(shuffleable):
            char_table[idx].set('class_id', class_ids[i])

    # ─── BASES RANDOMIZATION ──────────────────────────────────────────

    def _randomize_bases(self, char_table: ROMTable, indices: List[int], char_meta: dict):
        if self.settings.bases_mode == "vanilla":
            return

        rng = self.rng.fork("bases")
        stat_fields = char_table.layout.get('stat_fields', {})
        base_field_names = stat_fields.get('bases', [])

        if self.settings.bases_mode == "shuffle":
            self._shuffle_stat_group(char_table, indices, char_meta, 'bases',
                                     base_field_names, rng)
        elif self.settings.bases_mode == "random":
            for idx in indices:
                entry = char_table[idx]
                cid = entry.get('char_id', idx)

                if cid in self.settings.excluded_character_ids:
                    continue
                if self._is_field_locked(cid, 'bases'):
                    continue

                original_bases = entry.get_stat_values('bases')
                total_original = sum(original_bases.values())
                new_bases = {}

                for fname in base_field_names:
                    orig = original_bases.get(fname, 0)
                    new_val = rng.clamp_randint(
                        orig, self.settings.bases_variance,
                        self.settings.bases_min, self.settings.bases_max
                    )
                    new_bases[fname] = new_val

                # Preserve total if requested
                if self.settings.bases_preserve_total:
                    new_bases = self._adjust_to_total(new_bases, total_original,
                                                     self.settings.bases_min,
                                                     self.settings.bases_max, rng)

                entry.set_stat_values('bases', new_bases)

    # ─── GROWTHS RANDOMIZATION ────────────────────────────────────────

    def _randomize_growths(self, char_table: ROMTable, indices: List[int], char_meta: dict):
        if self.settings.growths_mode == "vanilla":
            return

        rng = self.rng.fork("growths")
        stat_fields = char_table.layout.get('stat_fields', {})
        growth_field_names = stat_fields.get('growths', [])

        if self.settings.growths_mode == "shuffle":
            self._shuffle_stat_group(char_table, indices, char_meta, 'growths',
                                     growth_field_names, rng)
        elif self.settings.growths_mode == "random":
            for idx in indices:
                entry = char_table[idx]
                cid = entry.get('char_id', idx)

                if cid in self.settings.excluded_character_ids:
                    continue
                if self._is_field_locked(cid, 'growths'):
                    continue

                original_growths = entry.get_stat_values('growths')
                total_original = sum(original_growths.values())
                new_growths = {}

                for fname in growth_field_names:
                    orig = original_growths.get(fname, 0)
                    new_val = rng.clamp_randint(
                        orig, self.settings.growths_variance,
                        self.settings.growths_min, self.settings.growths_max
                    )
                    new_growths[fname] = new_val

                if self.settings.growths_preserve_total:
                    new_growths = self._adjust_to_total(new_growths, total_original,
                                                       self.settings.growths_min,
                                                       self.settings.growths_max, rng)

                entry.set_stat_values('growths', new_growths)

    # ─── RANKS RANDOMIZATION ─────────────────────────────────────────

    def _randomize_ranks(self, char_table: ROMTable, indices: List[int], char_meta: dict):
        if self.settings.ranks_mode == "vanilla":
            return

        rng = self.rng.fork("ranks")
        stat_fields = char_table.layout.get('stat_fields', {})
        rank_field_names = stat_fields.get('ranks', [])

        if self.settings.ranks_mode == "shuffle":
            self._shuffle_stat_group(char_table, indices, char_meta, 'ranks',
                                     rank_field_names, rng)
        elif self.settings.ranks_mode == "random":
            for idx in indices:
                entry = char_table[idx]
                cid = entry.get('char_id', idx)

                if cid in self.settings.excluded_character_ids:
                    continue
                if self._is_field_locked(cid, 'ranks'):
                    continue

                original_ranks = entry.get_stat_values('ranks')
                new_ranks = {}

                for fname in rank_field_names:
                    orig = original_ranks.get(fname, 0)
                    if orig > 0:
                        new_val = rng.clamp_randint(orig, self.settings.ranks_variance, 1, 251)
                    else:
                        new_val = 0
                    new_ranks[fname] = new_val

                entry.set_stat_values('ranks', new_ranks)

    # ─── INVENTORY RANDOMIZATION ─────────────────────────────────────

    def _randomize_inventory(self, char_table: ROMTable, indices: List[int], char_meta: dict):
        if self.settings.inventory_mode == "dont_change":
            return

        rng = self.rng.fork("inventory")

        item_table = self.tm.tables.get('items')

        for idx in indices:
            entry = char_table[idx]
            cid = entry.get('char_id', idx)

            if cid in self.settings.excluded_character_ids:
                continue
            if self._is_field_locked(cid, 'items'):
                continue

            if self.settings.inventory_mode == "guarantee_usable":
                self._guarantee_usable_weapon(entry, item_table, rng)
            elif self.settings.inventory_mode == "random_consumables":
                self._randomize_consumable_items(entry, item_table, rng)
            elif self.settings.inventory_mode == "full_random":
                self._full_random_inventory(entry, item_table, rng)

    def _guarantee_usable_weapon(self, entry: TableEntry, item_table: Optional[ROMTable],
                                 rng: RNGEngine):
        """Ensure at least one weapon matches the character's rank."""
        # Simplified: check first item slot, ensure it's valid for ranks
        pass  # Full implementation would cross-reference item types with ranks

    def _randomize_consumable_items(self, entry: TableEntry, item_table: Optional[ROMTable],
                                    rng: RNGEngine):
        """Only randomize non-weapon items (vulneraries, keys, etc.)."""
        if not item_table:
            return
        consumable_ids = []
        for ie in item_table:
            item_type = ie.get('item_type', 0)
            item_id = ie.get('item_id', ie.index)
            if item_type == 8 and item_id not in self.settings.inventory_blacklist_ids:
                consumable_ids.append(item_id)

        if not consumable_ids:
            return

        stat_fields = entry.layout.get('stat_fields', {})
        item_fields = stat_fields.get('items', [])
        for fname in item_fields[1:]:  # Keep slot 0 (usually weapon)
            current = entry.get(fname, 0)
            if current > 0:
                entry.set(fname, rng.choice(consumable_ids))

    def _full_random_inventory(self, entry: TableEntry, item_table: Optional[ROMTable],
                               rng: RNGEngine):
        """Fully randomize all inventory slots."""
        if not item_table:
            return
        valid_ids = []
        for ie in item_table:
            iid = ie.get('item_id', ie.index)
            if iid > 0 and iid not in self.settings.inventory_blacklist_ids:
                valid_ids.append(iid)
        if not valid_ids:
            return

        stat_fields = entry.layout.get('stat_fields', {})
        item_fields = stat_fields.get('items', [])
        for fname in item_fields:
            if entry.get(fname, 0) > 0:  # only fill slots that had items
                entry.set(fname, rng.choice(valid_ids))

    # ─── SHARED HELPERS ──────────────────────────────────────────────

    def _shuffle_stat_group(self, char_table: ROMTable, indices: List[int],
                            char_meta: dict, group_name: str,
                            field_names: List[str], rng: RNGEngine):
        """Shuffle a stat group among characters."""
        shuffleable = []
        for idx in indices:
            cid = char_table[idx].get('char_id', idx)
            if cid in self.settings.excluded_character_ids:
                continue
            if self._is_field_locked(cid, group_name):
                continue
            shuffleable.append(idx)

        if len(shuffleable) < 2:
            return

        stat_blocks = [char_table[idx].get_stat_values(group_name) for idx in shuffleable]
        rng.shuffle(stat_blocks)

        for i, idx in enumerate(shuffleable):
            char_table[idx].set_stat_values(group_name, stat_blocks[i])

    def _adjust_to_total(self, stats: Dict[str, int], target_total: int,
                         min_val: int, max_val: int, rng: RNGEngine) -> Dict[str, int]:
        """Adjust stats to approximately match the target total."""
        current_total = sum(stats.values())
        diff = target_total - current_total

        if diff == 0:
            return stats

        keys = list(stats.keys())
        attempts = 0
        max_attempts = 100

        while diff != 0 and attempts < max_attempts:
            key = rng.choice(keys)
            val = stats[key]

            if diff > 0:
                room = max_val - val
                if room > 0:
                    add = min(diff, room, rng.randint(1, max(1, abs(diff))))
                    stats[key] = val + add
                    diff -= add
            elif diff < 0:
                room = val - min_val
                if room > 0:
                    sub = min(-diff, room, rng.randint(1, max(1, abs(diff))))
                    stats[key] = val - sub
                    diff += sub

            attempts += 1

        return stats

    def get_changes(self) -> List[CharacterChange]:
        return self.changes

    def get_warnings(self) -> List[str]:
        return self.warnings

    def get_errors(self) -> List[str]:
        return self.errors