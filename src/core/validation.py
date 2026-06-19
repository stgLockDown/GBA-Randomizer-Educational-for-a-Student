"""
Validation Engine: safety checks, auto-fix, and issue reporting.
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from src.rom.tables import TableManager, ROMTable, TableEntry
from src.core.engine import RandomizerSettings


@dataclass
class ValidationIssue:
    """A single validation issue found during checks."""
    severity: str  # 'error' or 'warning'
    category: str  # 'class', 'weapon', 'bounds', 'required', etc.
    character_id: int
    character_name: str
    message: str
    suggestion: str = ""
    auto_fixable: bool = False
    fixed: bool = False

    def __str__(self):
        prefix = "ERROR" if self.severity == "error" else "WARNING"
        fix_tag = " [AUTO-FIXED]" if self.fixed else ""
        return f"[{prefix}] {self.character_name} (ID {self.character_id}): {self.message}{fix_tag}"


class ValidationEngine:
    """Runs safety checks on randomized data."""

    def __init__(self, table_manager: TableManager, settings: RandomizerSettings,
                 profile: dict):
        self.tm = table_manager
        self.settings = settings
        self.profile = profile
        self.issues: List[ValidationIssue] = []

    def run_all_checks(self) -> List[ValidationIssue]:
        """Run all validation checks and return issues."""
        self.issues.clear()

        char_table = self.tm.tables.get('characters')
        class_table = self.tm.tables.get('classes')
        item_table = self.tm.tables.get('items')

        if not char_table:
            self.issues.append(ValidationIssue(
                severity='error', category='system',
                character_id=0, character_name='SYSTEM',
                message='Character table not loaded. Cannot validate.'
            ))
            return self.issues

        char_meta = self.profile.get('characters', {})
        rules = self.profile.get('rules', {})

        # Translation-patch awareness
        translation_meta = self.profile.get('translation_metadata') or {}
        if translation_meta.get('is_translation_patch'):
            self.issues.append(ValidationIssue(
                severity='warning', category='translation',
                character_id=0, character_name='ROM',
                message=(
                    "This ROM is an English translation patch. "
                    "Internal data tables may be relocated; running in safe-mode."
                ),
                suggestion=(
                    "Only operations enabled by the profile's feature_flags "
                    "will be applied. Use the original Japanese ROM for full "
                    "randomization."
                ),
            ))
            for w in (self.profile.get('warnings') or []):
                self.issues.append(ValidationIssue(
                    severity='warning', category='translation',
                    character_id=0, character_name='ROM',
                    message=w,
                ))

        # Translation-patch-specific safety checks
        self._check_translation_patch_safety(char_table, char_meta)

        # Pre-check: detect impossible stats (table-misalignment indicator)
        self._check_table_sanity(char_table, char_meta)

        self._check_class_legality(char_table, class_table, char_meta, rules)
        self._check_weapon_usability(char_table, item_table, char_meta)
        self._check_required_characters(char_table, char_meta, rules)
        self._check_bounds(char_table, char_meta)

        # Auto-fix if enabled
        if self.settings.auto_fix:
            self._auto_fix_issues(char_table, class_table, item_table, rules)

        return self.issues

    def _check_translation_patch_safety(self, char_table: ROMTable, char_meta: dict):
        """Add validation warnings for translation-patched ROMs.

        Detects when a profile indicates a translation patch and checks that
        only safe operations are enabled. Also validates that table data
        appears reasonable (not obviously garbage).
        """
        translation_meta = self.profile.get('translation_metadata', {})
        if not translation_meta.get('is_translation_patch', False):
            return

        # Check that unsafe operations are actually disabled
        features = self.profile.get('feature_flags', {})
        unsafe_ops = translation_meta.get('known_unsafe_operations', [])
        feature_map = {
            'class_randomization': 'supports_class_randomization',
            'bases_randomization': 'supports_bases_randomization',
            'ranks_randomization': 'supports_ranks_randomization',
            'inventory_randomization': 'supports_inventory_randomization',
            'recruitment_shuffle': 'supports_recruitment_shuffle',
        }

        for op in unsafe_ops:
            flag_key = feature_map.get(op)
            if flag_key and features.get(flag_key, False):
                self.issues.append(ValidationIssue(
                    severity='error', category='translation',
                    character_id=0, character_name='ROM',
                    message=f'Unsafe operation "{op}" is enabled for a translation-patched ROM. '
                            f'This will likely corrupt the ROM.',
                    suggestion=f'Disable {flag_key} in the profile or use story_safe preset.',
                ))

        # Validate table data integrity — check first few entries for obviously garbage values
        garbage_count = 0
        for i, entry in enumerate(char_table):
            if i >= 10:
                break
            cid = entry.get('char_id', entry.index)
            class_id = entry.get('class_id', 0)
            if cid > 500 or class_id > 200:
                garbage_count += 1

        if garbage_count >= 3:
            self.issues.append(ValidationIssue(
                severity='warning', category='translation',
                character_id=0, character_name='ROM',
                message='Character table data appears corrupt or misaligned. '
                        f'{garbage_count}/10 first entries have invalid IDs. '
                        'The table address may not match the translated ROM.',
                suggestion='Only use growths randomization (safe mode) or verify table addresses.',
            ))

    def _check_table_sanity(self, char_table: ROMTable, char_meta: dict):
        """Flag impossible values that suggest the character table is misaligned."""
        suspicious_entries = 0
        sampled = 0

        for entry in char_table.entries[:64]:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid)) or char_meta.get(str(entry.index))
            if not meta:
                continue
            sampled += 1
            name = meta.get('name', f'Char_{cid}')

            bases = entry.get_stat_values('bases') or {}
            hp = bases.get('hp', bases.get('base_hp'))
            # FE6 character bases are deltas added to class bases, so 0 or
            # mildly negative values can be valid. Very large or deeply
            # negative values still indicate a likely misaligned table.
            if hp is not None and (hp < -30 or hp > 80):
                suspicious_entries += 1
                self.issues.append(ValidationIssue(
                    severity='warning', category='sanity',
                    character_id=cid, character_name=name,
                    message=f'Implausible HP base value {hp} (expected -30 to 80).',
                    suggestion='Profile table addresses may be wrong for this ROM.',
                ))
                continue

            growths = entry.get_stat_values('growths') or {}
            for fname, gval in growths.items():
                if gval < 0 or gval > 200:
                    suspicious_entries += 1
                    self.issues.append(ValidationIssue(
                        severity='warning', category='sanity',
                        character_id=cid, character_name=name,
                        message=f'Implausible growth {fname}={gval} (expected 0-200).',
                        suggestion='Profile table addresses may be wrong for this ROM.',
                    ))
                    break

        if sampled and (suspicious_entries / sampled) >= 0.5:
            self.issues.append(ValidationIssue(
                severity='error', category='sanity',
                character_id=0, character_name='ROM',
                message=(
                    f'Character table looks corrupt: '
                    f'{suspicious_entries}/{sampled} sampled entries had '
                    f'implausible values.'
                ),
                suggestion=(
                    'The profile table addresses likely do not point at real '
                    'character data on this ROM. Destructive randomization '
                    'passes have been skipped.'
                ),
            ))

    def _check_class_legality(self, char_table: ROMTable, class_table: Optional[ROMTable],
                              char_meta: dict, rules: dict):
        """Check that assigned classes are legal (gender, validity)."""
        gender_rules = rules.get('gender_locked_classes', {})
        female_only = set(gender_rules.get('female_only', []))
        male_only = set(gender_rules.get('male_only', []))
        max_class_id = class_table.entries[-1].index if class_table and class_table.entries else 127

        for entry in char_table:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid), {})
            if not meta:
                continue

            name = meta.get('name', f'Char_{cid}')
            class_id = entry.get('class_id', 0)

            # Check bounds
            if class_id < 0 or class_id > max_class_id:
                self.issues.append(ValidationIssue(
                    severity='error', category='class',
                    character_id=cid, character_name=name,
                    message=f'Invalid class ID {class_id} (max: {max_class_id}).',
                    suggestion='Assign a valid class from the allowed pool.',
                    auto_fixable=True
                ))

            # Check gender lock
            is_female = meta.get('is_female', False)
            if is_female and class_id in male_only:
                self.issues.append(ValidationIssue(
                    severity='error', category='class',
                    character_id=cid, character_name=name,
                    message=f'Female character assigned male-only class {class_id}.',
                    suggestion='Change to a gender-appropriate class.',
                    auto_fixable=True
                ))
            elif not is_female and class_id in female_only:
                self.issues.append(ValidationIssue(
                    severity='error', category='class',
                    character_id=cid, character_name=name,
                    message=f'Male character assigned female-only class {class_id}.',
                    suggestion='Change to a gender-appropriate class.',
                    auto_fixable=True
                ))

    def _check_weapon_usability(self, char_table: ROMTable, item_table: Optional[ROMTable],
                                char_meta: dict):
        """Check that characters can use at least one of their starting items."""
        if not item_table:
            return

        # Build item lookup
        item_lookup: Dict[int, TableEntry] = {}
        for ie in item_table:
            iid = ie.get('item_id', ie.index)
            item_lookup[iid] = ie

        rank_to_type_map = {
            'rank_sword': 0, 'rank_lance': 1, 'rank_axe': 2, 'rank_bow': 3,
            'rank_staff': 4, 'rank_anima': 5, 'rank_light': 6, 'rank_dark': 7,
        }

        for entry in char_table:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid), {})
            if not meta:
                continue

            name = meta.get('name', f'Char_{cid}')
            ranks = entry.get_stat_values('ranks')
            items = entry.get_stat_values('items')

            has_usable_weapon = False
            has_any_item = False

            for slot_name, item_id in items.items():
                if item_id <= 0:
                    continue
                has_any_item = True

                item_entry = item_lookup.get(item_id)
                if not item_entry:
                    continue

                item_type = item_entry.get('item_type', 8)
                required_rank = item_entry.get('rank_required', 0)

                if item_type == 8:  # consumable
                    continue

                # Find matching rank field
                for rank_field, type_val in rank_to_type_map.items():
                    if type_val == item_type:
                        char_rank = ranks.get(rank_field, 0)
                        if char_rank >= required_rank:
                            has_usable_weapon = True
                        break

            if has_any_item and not has_usable_weapon:
                self.issues.append(ValidationIssue(
                    severity='warning', category='weapon',
                    character_id=cid, character_name=name,
                    message='Character has no usable weapon in starting inventory.',
                    suggestion='Raise weapon rank or swap starting weapon.',
                    auto_fixable=True
                ))

    def _check_required_characters(self, char_table: ROMTable, char_meta: dict, rules: dict):
        """Check that required characters haven't been broken."""
        required_ids = set(rules.get('required_character_ids', []))
        lord_ids = set(rules.get('lord_character_ids', []))
        lord_class_ids = set(rules.get('lord_class_ids', []))

        for entry in char_table:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid), {})
            if not meta:
                continue

            name = meta.get('name', f'Char_{cid}')

            # CRITICAL: Check that lords have valid name identifiers (story
            # scripts depend on this). FE7/FE8-style layouts use 32-bit
            # name_pointer fields; FE6 JP uses 16-bit msg_name text IDs.
            if cid in lord_ids:
                if 'name_pointer' in entry.fields:
                    name_identifier = entry.get('name_pointer', 0)
                    name_label = 'name pointer'
                else:
                    name_identifier = entry.get('msg_name', 0)
                    name_label = 'name message ID'

                if name_identifier == 0:
                    self.issues.append(ValidationIssue(
                        severity='error', category='required',
                        character_id=cid, character_name=name,
                        message=f'Lord character has null {name_label} (will break story).',
                        suggestion='Do not modify required character table text identifiers.',
                        auto_fixable=True
                    ))

            # Check lords keep lord classes if setting requires
            if cid in lord_ids and self.settings.keep_lords:
                class_id = entry.get('class_id', 0)
                if lord_class_ids and class_id not in lord_class_ids:
                    self.issues.append(ValidationIssue(
                        severity='error', category='required',  # Changed from warning to error
                        character_id=cid, character_name=name,
                        message=f'Lord character class changed to {class_id} (not a lord class).',
                        suggestion='This WILL cause story script issues. Revert to original class.',
                        auto_fixable=True
                    ))

    def _check_bounds(self, char_table: ROMTable, char_meta: dict):
        """Check that all stat values are within valid bounds."""
        for entry in char_table:
            cid = entry.get('char_id', entry.index)
            meta = char_meta.get(str(cid), {})
            if not meta:
                continue

            name = meta.get('name', f'Char_{cid}')

            # Check bases
            bases = entry.get_stat_values('bases')
            for fname, val in bases.items():
                if val < -20 or val > 60:
                    self.issues.append(ValidationIssue(
                        severity='warning', category='bounds',
                        character_id=cid, character_name=name,
                        message=f'Stat {fname} = {val} is outside normal bounds [-20, 60].',
                        suggestion='Consider adjusting variance settings.',
                        auto_fixable=True
                    ))

            # Check growths
            growths = entry.get_stat_values('growths')
            for fname, val in growths.items():
                if val < 0 or val > 255:
                    self.issues.append(ValidationIssue(
                        severity='error', category='bounds',
                        character_id=cid, character_name=name,
                        message=f'Growth {fname} = {val} is outside valid range [0, 255].',
                        suggestion='Clamp value to valid range.',
                        auto_fixable=True
                    ))

    def _auto_fix_issues(self, char_table: ROMTable, class_table: Optional[ROMTable],
                         item_table: Optional[ROMTable], rules: dict):
        """Attempt to auto-fix issues that are marked as fixable."""
        for issue in self.issues:
            if not issue.auto_fixable or issue.fixed:
                continue

            entry = None
            for e in char_table:
                if e.get('char_id', e.index) == issue.character_id:
                    entry = e
                    break

            if not entry:
                continue

            if issue.category == 'bounds' and 'Growth' in issue.message:
                # Clamp growth values
                growths = entry.get_stat_values('growths')
                for fname, val in growths.items():
                    if val < 0:
                        growths[fname] = 0
                    elif val > 255:
                        growths[fname] = 255
                entry.set_stat_values('growths', growths)
                issue.fixed = True

            elif issue.category == 'bounds' and 'Stat' in issue.message:
                # Clamp base values
                bases = entry.get_stat_values('bases')
                for fname, val in bases.items():
                    if val < -20:
                        bases[fname] = -20
                    elif val > 60:
                        bases[fname] = 60
                entry.set_stat_values('bases', bases)
                issue.fixed = True

            elif issue.category == 'weapon' and self.settings.ranks_fix_weapon == 'raise_rank':
                self._auto_fix_weapon_rank(entry, item_table)
                issue.fixed = True

            elif issue.category == 'class':
                # Revert to original class as safest fix
                orig_class = entry.get_original('class_id')
                if orig_class is not None:
                    entry.set('class_id', orig_class)
                    issue.fixed = True
            
            elif issue.category == 'required' and 'null name pointer' in issue.message:
                # Cannot auto-fix null pointers - user must rebuild with safer settings
                # Mark as not fixable to force user attention
                issue.auto_fixable = False

    def _auto_fix_weapon_rank(self, entry: TableEntry, item_table: Optional[ROMTable]):
        """Raise weapon rank to minimum needed for first weapon."""
        if not item_table:
            return

        item_lookup = {ie.get('item_id', ie.index): ie for ie in item_table}
        rank_to_type_map = {
            'rank_sword': 0, 'rank_lance': 1, 'rank_axe': 2, 'rank_bow': 3,
            'rank_staff': 4, 'rank_anima': 5, 'rank_light': 6, 'rank_dark': 7,
        }

        items = entry.get_stat_values('items')
        for slot_name, item_id in items.items():
            if item_id <= 0:
                continue
            item_entry = item_lookup.get(item_id)
            if not item_entry:
                continue

            item_type = item_entry.get('item_type', 8)
            required_rank = item_entry.get('rank_required', 0)
            if item_type == 8:
                continue

            for rank_field, type_val in rank_to_type_map.items():
                if type_val == item_type:
                    current_rank = entry.get(rank_field, 0)
                    if current_rank < required_rank:
                        entry.set(rank_field, required_rank)
                    break
            break  # Only fix first weapon

    def has_errors(self) -> bool:
        return any(i.severity == 'error' and not i.fixed for i in self.issues)

    def has_warnings(self) -> bool:
        return any(i.severity == 'warning' and not i.fixed for i in self.issues)

    def get_errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == 'error' and not i.fixed]

    def get_warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == 'warning' and not i.fixed]

    def get_fixed(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.fixed]

    def get_summary(self) -> str:
        errors = self.get_errors()
        warnings = self.get_warnings()
        fixed = self.get_fixed()
        lines = [
            f"Validation Summary:",
            f"  Errors:   {len(errors)}",
            f"  Warnings: {len(warnings)}",
            f"  Auto-fixed: {len(fixed)}",
        ]
        if errors:
            lines.append("\nErrors (blocking):")
            for e in errors:
                lines.append(f"  • {e}")
        if warnings:
            lines.append("\nWarnings:")
            for w in warnings:
                lines.append(f"  • {w}")
        if fixed:
            lines.append("\nAuto-fixed:")
            for f_item in fixed:
                lines.append(f"  • {f_item}")
        return "\n".join(lines)