#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_phase1_manual_verification.py - Systematic automated verification
for the mandatory Windows GUI operations:
- New Box, Cut Box, Paste Box, and multi-box delimiter paste
- Both Page View and Continuous View
- Each undone by ONE Ctrl+Z (and redone by ONE Ctrl+Y)
- Each persists after Ctrl+S (save_file) and reload from disk.

All tests that require the fixture bundle are skipped when the bundle is
absent (CI / machines without game assets).  Modal dialogs are mocked
globally in setUp so the test process never blocks in a headless environment.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import misora as misora_app

MISORA_DIR = Path(__file__).resolve().parent.parent
_FIXTURE_CANDIDATES = [
    MISORA_DIR / "storydata_1001005.unity3d",
    MISORA_DIR / "1001005.unity3d",
]
FIXTURE_PATH = next((p for p in _FIXTURE_CANDIDATES if p.exists()), None)
_FIXTURE_MISSING = FIXTURE_PATH is None

_SKIP_NO_FIXTURE = unittest.skipIf(
    _FIXTURE_MISSING,
    "Fixture bundle not found — skipping bundle-dependent tests",
)


def _make_app() -> misora_app.MisoraApp:
    """Create a withdrawn MisoraApp suitable for headless testing."""
    app = misora_app.MisoraApp(restore_session=False)
    app.withdraw()
    return app


def _destroy_app(app: misora_app.MisoraApp) -> None:
    """Safely destroy the app, suppressing all Tkinter teardown errors."""
    try:
        # Prevent dirty-exit dialog on close
        app.is_dirty = False
        for doc_info in getattr(app, "open_documents", {}).values():
            if isinstance(doc_info, dict):
                doc_info["dirty"] = False
    except Exception:
        pass
    try:
        app.update_idletasks()
    except Exception:
        pass
    try:
        app.destroy()
    except Exception:
        pass


class _BasePhase1Test(unittest.TestCase):
    """Base class: creates/destroys app and mocks all modal dialogs."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_phase1_test_"))

        # Patch every messagebox variant used by misora so they never block.
        self._patches = [
            patch.object(misora_app.messagebox, "askyesno",      return_value=True),
            patch.object(misora_app.messagebox, "askyesnocancel", return_value=True),
            patch.object(misora_app.messagebox, "showinfo",       return_value=None),
            patch.object(misora_app.messagebox, "showerror",      return_value=None),
            patch.object(misora_app.messagebox, "showwarning",    return_value=None),
        ]
        for p in self._patches:
            p.start()

        self.app = _make_app()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        _destroy_app(self.app)
        for p in self._patches:
            p.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_view_mode(self, continuous: bool) -> None:
        self.app.var_continuous_view.set(continuous)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

    def _load_sample_bundle(self) -> Path:
        """Create a fresh copy of the fixture bundle in temp dir and open it."""
        target_path = self.tmp_dir / "test_story.unity3d"
        shutil.copy2(FIXTURE_PATH, target_path)
        self.app.open_file(target_path)
        self.app.update_idletasks()
        return target_path


# =============================================================================
# PAGE VIEW TESTS
# =============================================================================

class TestPageView(_BasePhase1Test):

    @_SKIP_NO_FIXTURE
    def test_new_box_undo_redo_save_reload(self):
        """Page View: New Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(False)
        self.assertFalse(self.app.var_continuous_view.get())

        initial_count = len(self.app.current_doc.boxes)
        self.assertGreater(initial_count, 0)
        self.app.current_box_idx = 0

        # 1. New Box
        self.app.on_box_new()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)
        self.assertEqual(self.app.current_box_idx, 1)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

    @_SKIP_NO_FIXTURE
    def test_cut_box_undo_redo_save_reload(self):
        """Page View: Cut Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(False)

        initial_count = len(self.app.current_doc.boxes)
        cut_box_speaker = self.app.current_doc.boxes[0].speaker
        cut_box_text    = self.app.current_doc.boxes[0].clean_text

        # 1. Cut Box at index 0
        self.app.current_box_idx = 0
        self.app.on_box_cut()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)
        self.assertEqual(self.app.current_doc.boxes[0].speaker,    cut_box_speaker)
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, cut_box_text)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

    @_SKIP_NO_FIXTURE
    def test_copy_paste_box_undo_redo_save_reload(self):
        """Page View: Copy + Paste Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(False)

        initial_count = len(self.app.current_doc.boxes)
        self.app.current_box_idx = 0
        copied_text = self.app.current_doc.boxes[0].clean_text

        # 1. Copy Box 0, then Paste Box (confirm=False bypasses dialog in tests)
        self.app.on_box_copy()
        self.app.on_box_paste(confirm=False)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, copied_text)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, copied_text)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, copied_text)

    @_SKIP_NO_FIXTURE
    def test_multibox_paste_undo_redo_save_reload(self):
        """Page View: Multi-box delimiter paste -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(False)

        initial_count = len(self.app.current_doc.boxes)
        self.app.current_box_idx = 0

        # Place 3 boxes separated by triple-enter in clipboard
        multi_payload = "Segment Alpha\n\n\nSegment Beta\n\n\nSegment Gamma"
        self.app._box_clipboard = None   # Clear internal snapshot to exercise text parsing
        self.app.clipboard_clear()
        self.app.clipboard_append(multi_payload)

        # 1. Paste Box with multi-delimiter payload (confirm=False bypasses dialog)
        self.app.on_box_paste(confirm=False)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 3)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, "Segment Alpha")
        self.assertEqual(self.app.current_doc.boxes[2].clean_text, "Segment Beta")
        self.assertEqual(self.app.current_doc.boxes[3].clean_text, "Segment Gamma")

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 3)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 3)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, "Segment Alpha")


# =============================================================================
# CONTINUOUS VIEW TESTS
# =============================================================================

class TestContinuousView(_BasePhase1Test):

    @_SKIP_NO_FIXTURE
    def test_new_box_undo_redo_save_reload(self):
        """Continuous View: New Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(True)
        self.assertTrue(self.app.var_continuous_view.get())

        initial_count = len(self.app.current_doc.boxes)
        self.app.current_box_idx = 0

        # 1. New Box
        self.app.on_box_new()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

    @_SKIP_NO_FIXTURE
    def test_cut_box_undo_redo_save_reload(self):
        """Continuous View: Cut Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(True)

        initial_count = len(self.app.current_doc.boxes)
        cut_box_text = self.app.current_doc.boxes[0].clean_text

        # 1. Cut Box
        self.app.current_box_idx = 0
        self.app.on_box_cut()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, cut_box_text)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count - 1)

    @_SKIP_NO_FIXTURE
    def test_copy_paste_box_undo_redo_save_reload(self):
        """Continuous View: Copy + Paste Box -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(True)

        initial_count = len(self.app.current_doc.boxes)
        self.app.current_box_idx = 0
        copied_text = self.app.current_doc.boxes[0].clean_text

        # 1. Copy + Paste (confirm=False bypasses dialog)
        self.app.on_box_copy()
        self.app.on_box_paste(confirm=False)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, copied_text)

        # 2. Undone by ONE Ctrl+Z
        self.app.on_undo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertEqual(len(self.app.current_doc.boxes), initial_count + 1)

    @_SKIP_NO_FIXTURE
    def test_card_paste_caret_undo_redo_save_reload(self):
        """Continuous View: Card caret-aware multi-box paste -> 1 Ctrl+Z undo -> 1 Ctrl+Y redo -> Save -> Reload."""
        fpath = self._load_sample_bundle()
        self._set_view_mode(True)

        initial_count = len(self.app.current_doc.boxes)
        orig_box0_text = self.app.current_doc.boxes[0].clean_text

        # Get the card widget for box 0
        card_info = self.app._card_widgets.get(0)
        self.assertIsNotNone(card_info)
        card_widget = card_info["txt"]

        # Prepare clipboard with multi-box delimiter
        multi_payload = "Prefix_Part\n\n\nNew_Box_1\n\n\nNew_Box_2"
        self.app.clipboard_clear()
        self.app.clipboard_append(multi_payload)

        # Simulate caret paste in card 0
        res = self.app._on_card_paste_caret(0, card_widget)
        self.assertEqual(res, "break")

        # Verify boxes 0, 1, 2 text modified across boxes
        self.assertEqual(len(self.app.current_doc.boxes), initial_count)
        self.assertIn("Prefix_Part", self.app.current_doc.boxes[0].clean_text)
        self.assertIn("New_Box_1",   self.app.current_doc.boxes[1].clean_text)
        self.assertIn("New_Box_2",   self.app.current_doc.boxes[2].clean_text)

        # 2. Undone by ONE Ctrl+Z (single batch undoes all 3 box modifications)
        self.app.on_undo()
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, orig_box0_text)
        self.assertNotIn("New_Box_1", self.app.current_doc.boxes[1].clean_text)

        # 3. Redone by ONE Ctrl+Y
        self.app.on_redo()
        self.assertIn("Prefix_Part", self.app.current_doc.boxes[0].clean_text)
        self.assertIn("New_Box_1",   self.app.current_doc.boxes[1].clean_text)

        # 4. Save and reload from disk
        self.app.on_save()
        self.app.open_file(fpath)
        self.assertIn("Prefix_Part", self.app.current_doc.boxes[0].clean_text)
        self.assertIn("New_Box_1",   self.app.current_doc.boxes[1].clean_text)


if __name__ == "__main__":
    unittest.main()
