"""
AppState: central application state that bridges UI and engine.
Manages ROM data, profile, settings, and async operations via QThread.
"""
import os
import copy
from PySide6.QtCore import QObject, Signal, QThread
from typing import Optional, Dict, List

from src.rom.loader import ROMData, ProfileManager, LayoutManager, load_rom
from src.rom.tables import TableManager
from src.rom.writer import ROMWriter
from src.core.engine import RandomizerSettings, RandomizationEngine, CharacterChange
from src.core.rng import RNGEngine
from src.core.validation import ValidationEngine, ValidationIssue
from src.core.spoiler_log import SpoilerLogGenerator
from src.core.presets import PresetManager


class ROMLoadWorker(QThread):
    """Worker thread for loading ROM files."""
    finished = Signal(bool, str)

    def __init__(self, path: str, profile_manager: ProfileManager, layout_manager: LayoutManager):
        super().__init__()
        self.path = path
        self.profile_manager = profile_manager
        self.layout_manager = layout_manager
        self.rom: Optional[ROMData] = None
        self.profile: Optional[dict] = None
        self.tier: str = 'C'
        self.table_manager: Optional[TableManager] = None

    def run(self):
        try:
            self.rom = load_rom(self.path)
            self.profile, self.tier = self.profile_manager.match_rom(self.rom)
            if self.profile is None:
                self.finished.emit(False, f"ROM not recognized. Game code: {self.rom.gba_game_code}")
                return
            self.table_manager = TableManager(self.rom, self.profile, self.layout_manager)
            self.table_manager.load_all_tables()
            self.finished.emit(True, "ROM loaded successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))


class PreviewWorker(QThread):
    """Worker thread for generating a preview."""
    finished = Signal()

    def __init__(self, app_state: 'AppState'):
        super().__init__()
        self.app_state = app_state

    def run(self):
        self.app_state._generate_preview()
        self.finished.emit()


class BuildWorker(QThread):
    """Worker thread for the full build process."""
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, app_state: 'AppState'):
        super().__init__()
        self.app_state = app_state

    def run(self):
        try:
            self.progress.emit(10, "Initializing randomization...")
            result = self.app_state._run_build()
            if result:
                self.finished.emit(True, f"Build complete! Output: {self.app_state.last_output_path}")
            else:
                self.finished.emit(False, "Build failed — check Safety tab for errors.")
        except Exception as e:
            self.finished.emit(False, f"Build error: {str(e)}")


class AppState(QObject):
    """Central application state and controller."""

    # Signals
    rom_loaded = Signal(bool, str)
    settings_changed = Signal()
    build_started = Signal()
    build_progress = Signal(int, str)
    build_finished = Signal(bool, str)
    preview_ready = Signal()

    def __init__(self):
        super().__init__()

        # Resolve base path (handles both dev and packaged scenarios)
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        src_path = os.path.join(self.base_path, 'src')

        # Fallback: if src_path doesn't contain profiles, try relative to cwd
        profiles_path = os.path.join(src_path, 'profiles')
        if not os.path.isdir(profiles_path):
            # Try from current working directory
            cwd_src = os.path.join(os.getcwd(), 'src')
            if os.path.isdir(os.path.join(cwd_src, 'profiles')):
                src_path = cwd_src
                self.base_path = os.getcwd()

        # Managers
        self.profile_manager = ProfileManager(os.path.join(src_path, 'profiles'))
        self.layout_manager = LayoutManager(os.path.join(src_path, 'layouts'))
        self.preset_manager = PresetManager(os.path.join(src_path, 'presets'))

        # State
        self.rom: Optional[ROMData] = None
        self.rom_path: str = ""
        self.profile: Optional[dict] = None
        self.tier: str = 'C'
        self.table_manager: Optional[TableManager] = None
        self.settings = RandomizerSettings()

        # Preview/build results
        self.preview_changes: List[CharacterChange] = []
        self.preview_warnings: List[str] = []
        self.preview_errors: List[str] = []
        self.validation_issues: List[ValidationIssue] = []
        self.last_output_path: str = ""
        self.last_spoiler_txt: str = ""
        self.last_spoiler_json: str = ""
        self.last_spoiler_content: str = ""

        # Workers
        self._load_worker: Optional[ROMLoadWorker] = None
        self._preview_worker: Optional[PreviewWorker] = None
        self._build_worker: Optional[BuildWorker] = None

    # ─── ROM Loading ──────────────────────────────────────────────

    def load_rom_async(self, path: str):
        """Start async ROM loading."""
        self.rom_path = path
        self._load_worker = ROMLoadWorker(path, self.profile_manager, self.layout_manager)
        self._load_worker.finished.connect(self._on_rom_load_finished)
        self._load_worker.start()

    def _on_rom_load_finished(self, success: bool, message: str):
        if success and self._load_worker:
            self.rom = self._load_worker.rom
            self.profile = self._load_worker.profile
            self.tier = self._load_worker.tier
            self.table_manager = self._load_worker.table_manager
        self.rom_loaded.emit(success, message)

    # ─── Preview ──────────────────────────────────────────────────

    def run_preview_async(self):
        """Start async preview generation."""
        self._preview_worker = PreviewWorker(self)
        self._preview_worker.finished.connect(self._on_preview_finished)
        self._preview_worker.start()

    def _on_preview_finished(self):
        self.preview_ready.emit()

    def _generate_preview(self):
        """Generate a preview (runs in worker thread)."""
        if not self.rom or not self.profile or not self.table_manager:
            return

        # Work on a copy of the ROM/tables so original stays clean
        preview_rom = ROMData(self.rom.filepath, bytes(self.rom.data))
        preview_tm = TableManager(preview_rom, self.profile, self.layout_manager)
        preview_tm.load_all_tables()

        seed = self.settings.seed or RNGEngine.generate_seed()
        rng = RNGEngine(seed)

        engine = RandomizationEngine(preview_tm, self.settings, self.profile, rng)
        engine.run()

        self.preview_changes = engine.get_changes()
        self.preview_warnings = engine.get_warnings()
        self.preview_errors = engine.get_errors()

        # Run validation
        validator = ValidationEngine(preview_tm, self.settings, self.profile)
        self.validation_issues = validator.run_all_checks()

    # ─── Build ────────────────────────────────────────────────────

    def run_build_async(self):
        """Start async build process."""
        self.build_started.emit()
        self._build_worker = BuildWorker(self)
        self._build_worker.progress.connect(self.build_progress.emit)
        self._build_worker.finished.connect(self._on_build_finished)
        self._build_worker.start()

    def _on_build_finished(self, success: bool, message: str):
        self.build_finished.emit(success, message)

    def _run_build(self) -> bool:
        """Execute the full build (runs in worker thread)."""
        if not self.rom or not self.profile or not self.table_manager:
            return False

        # Create a working copy of the ROM
        original_data = bytes(self.rom.data)
        working_rom = ROMData(self.rom.filepath, original_data)
        working_tm = TableManager(working_rom, self.profile, self.layout_manager)
        working_tm.load_all_tables()

        seed = self.settings.seed or RNGEngine.generate_seed()
        self.settings.seed = seed
        rng = RNGEngine(seed)

        # Randomize
        engine = RandomizationEngine(working_tm, self.settings, self.profile, rng)
        success = engine.run()

        if not success and not self.settings.force_build:
            self.preview_errors = engine.get_errors()
            return False

        # Validate
        validator = ValidationEngine(working_tm, self.settings, self.profile)
        issues = validator.run_all_checks()
        self.validation_issues = issues

        if validator.has_errors() and not self.settings.force_build:
            return False

        # Write tables back to ROM
        working_tm.write_all_tables()

        # Generate output
        output_path = self.settings.output_path
        writer = ROMWriter(self.rom, working_rom)

        if self.settings.output_mode == 'bps':
            self.last_output_path = writer.write_bps_patch(output_path)
        elif self.settings.output_mode == 'ups':
            self.last_output_path = writer.write_ups_patch(output_path)
        else:
            self.last_output_path = writer.write_rom(output_path)

        # Generate spoiler logs
        output_dir = os.path.dirname(self.last_output_path)
        self.last_spoiler_txt = os.path.join(output_dir, f"spoiler_{seed}.txt")
        self.last_spoiler_json = os.path.join(output_dir, f"spoiler_{seed}.json")

        spoiler_gen = SpoilerLogGenerator(
            seed=seed,
            settings=self.settings,
            profile=self.profile,
            rom_hash=self.rom.sha1,
            changes=engine.get_changes(),
            warnings=engine.get_warnings() + [str(i) for i in validator.get_warnings()],
        )
        spoiler_gen.generate_txt(self.last_spoiler_txt)
        spoiler_gen.generate_json(self.last_spoiler_json)

        # Cache spoiler content for the Logs tab
        try:
            with open(self.last_spoiler_txt, 'r') as f:
                self.last_spoiler_content = f.read()
        except IOError:
            self.last_spoiler_content = ""

        self.preview_changes = engine.get_changes()
        self.preview_warnings = engine.get_warnings()

        return True

    # ─── Character metadata helpers ───────────────────────────────

    def get_character_list(self) -> List[dict]:
        """Get list of characters from profile with table data."""
        if not self.profile:
            return []

        char_meta = self.profile.get('characters', {})
        char_table = self.table_manager.tables.get('characters') if self.table_manager else None

        result = []
        for cid_str, meta in sorted(char_meta.items(), key=lambda x: int(x[0])):
            cid = int(cid_str)
            entry_data = {}
            if char_table:
                for entry in char_table:
                    if entry.get('char_id', entry.index) == cid:
                        entry_data = dict(entry.fields)
                        break

            result.append({
                'id': cid,
                'name': meta.get('name', f'Char_{cid}'),
                'portrait': meta.get('portrait', ''),
                'is_lord': meta.get('is_lord', False),
                'is_required': meta.get('is_required', False),
                'is_thief': meta.get('is_thief', False),
                'is_dancer': meta.get('is_dancer', False),
                'entry': entry_data,
            })
        return result

    def get_portrait_path(self, portrait_filename: str) -> str:
        """Resolve path to a portrait PNG file."""
        if not self.profile or not portrait_filename:
            return ""

        game = self.profile.get('game', 'fe8')
        src_path = os.path.join(self.base_path, 'src')

        # Check override first
        override_path = os.path.join(src_path, 'assets_override', game, 'portraits', portrait_filename)
        if os.path.isfile(override_path):
            return override_path

        # Then bundled
        bundled_path = os.path.join(src_path, 'assets', game, 'portraits', portrait_filename)
        if os.path.isfile(bundled_path):
            return bundled_path

        # Fallback placeholder
        placeholder = os.path.join(src_path, 'assets', 'icons', 'unknown_portrait.png')
        if os.path.isfile(placeholder):
            return placeholder

        return ""