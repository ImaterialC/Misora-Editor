#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s9c_workspace_safety.py
==================================
Verification test suite for Slice S9c:
- FOLDER-DROP-EXTRA-IGNORED: When multiple folders are dropped in DnD, only the first
  is opened and a clear status notification / toast informs the user.
- OFFSCREEN-GEOMETRY: sanitize_window_geometry clamps saved window coordinates into
  visible screen bounds so disconnected monitor setups never leave windows off-screen.
- UNDO-COALESCE-CROSS-SOURCE: BoxEditDelta tracks edit sources ("keyboard", "format",
  "cut", "replace", "mtl", "paste_script", "clear"), preventing cross-source coalescing.
- Test hygiene: default config template contains clean values.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora
from misora import MisoraApp, sanitize_window_geometry
from core.undo_journal import MasterUndoJournal, BoxEditDelta


class TestS9cWorkspaceSafety(unittest.TestCase):
    """Test suite for S9c workspace protection, geometry sanitization, and undo isolation."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s9c_test_"))
        self.orig_config_path = misora.CONFIG_PATH
        self.tmp_config = self.tmp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.tmp_config
        self.app = None

    def tearDown(self):
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None
        misora.CONFIG_PATH = self.orig_config_path
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_multiple_folders_drop_notifies_user(self):
        """Dropping multiple folders opens first and warns user about ignored extra folders."""
        dir1 = self.tmp_dir / "folder_alpha"
        dir2 = self.tmp_dir / "folder_beta"
        dir3 = self.tmp_dir / "folder_gamma"
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()

        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        with patch.object(self.app, "_process_opened_folder") as mock_open_folder, \
             patch.object(self.app, "show_toast") as mock_toast:
            self.app._handle_dropped_paths([dir1, dir2, dir3])

            # Must process first folder
            mock_open_folder.assert_called_once_with(dir1, source_label="Drag & Drop")

            # Must warn about remaining 2 folders in status and toast
            status_text = self.app.lbl_status.cget("text")
            self.assertIn("Multiple folders dropped (3)", status_text)
            self.assertIn("remaining 2 folder(s) ignored", status_text)
            mock_toast.assert_called_once()
            self.assertIn("2 ignored", mock_toast.call_args[0][0])

    def test_02_offscreen_geometry_sanitized_to_screen_bounds(self):
        """sanitize_window_geometry clamps off-screen coordinates into virtual display bounds."""
        # 1. Screen size 1920x1080, window positioned off-screen to the right (x=2500)
        clamped = sanitize_window_geometry("1280x820+2500+200", 1920, 1080)
        self.assertEqual(clamped, "1280x820+640+200")

        # 2. Positioned off-screen bottom (y=1500)
        clamped_y = sanitize_window_geometry("1280x820+100+1500", 1920, 1080)
        self.assertEqual(clamped_y, "1280x820+100+260")

        # 3. Positioned off-screen negative (x=-600, y=-300)
        clamped_neg = sanitize_window_geometry("1280x820-600-300", 1920, 1080)
        self.assertEqual(clamped_neg, "1280x820+0+0")

        # 4. Oversized window dimensions clamped to screen
        clamped_oversize = sanitize_window_geometry("3000x2000+0+0", 1920, 1080)
        self.assertEqual(clamped_oversize, "1920x1080+0+0")

        # 5. Normal on-screen geometry preserved
        normal = sanitize_window_geometry("1280x820+100+100", 1920, 1080)
        self.assertEqual(normal, "1280x820+100+100")

    def test_03_undo_coalesce_cross_source_isolation(self):
        """Consecutive deltas with different sources must NOT coalesce into one operation."""
        journal = MasterUndoJournal()
        journal.set_active_file("test.txt")

        # Same source ("keyboard") within 2s coalesces
        delta_type1 = BoxEditDelta(
            box_index=0,
            old_speaker="Spk",
            new_speaker="Spk",
            old_text="H",
            new_text="He",
            file_path="test.txt",
            source="keyboard",
        )
        delta_type2 = BoxEditDelta(
            box_index=0,
            old_speaker="Spk",
            new_speaker="Spk",
            old_text="He",
            new_text="Hello",
            file_path="test.txt",
            source="keyboard",
        )
        journal.record(delta_type1)
        journal.record(delta_type2)

        # Undo stack should have 1 coalesced op
        self.assertEqual(len(journal._get_state("test.txt").undo_stack), 1)

        # Ribbon cut or format ("cut" or "format") on same box within window
        delta_cut = BoxEditDelta(
            box_index=0,
            old_speaker="Spk",
            new_speaker="Spk",
            old_text="Hello",
            new_text="",
            file_path="test.txt",
            source="cut",
        )
        journal.record(delta_cut)

        # Undo stack must now have 2 distinct ops (cut must not coalesce with typing!)
        self.assertEqual(len(journal._get_state("test.txt").undo_stack), 2)

        # Pop undo: first pop restores cut, second pop restores typing
        op_cut = journal.pop_undo("test.txt")
        self.assertIsNotNone(op_cut)
        self.assertEqual(op_cut.deltas[0].source, "cut")

        op_type = journal.pop_undo("test.txt")
        self.assertIsNotNone(op_type)
        self.assertEqual(op_type.deltas[0].source, "keyboard")
        self.assertEqual(op_type.deltas[0].new_text, "Hello")

    def test_04_default_config_template_clean(self):
        """misora_config.default.json must exist with empty machine paths."""
        default_cfg = REPO_ROOT / "misora_config.default.json"
        self.assertTrue(default_cfg.is_file(), "misora_config.default.json does not exist")
        data = json.loads(default_cfg.read_text(encoding="utf-8"))
        self.assertEqual(data.get("saved_opened_files"), [])
        self.assertEqual(data.get("saved_active_file"), "")
        self.assertEqual(data.get("recent_files"), [])
        self.assertEqual(data.get("project_folder"), "")
        self.assertEqual(data.get("bepinex_project_folder"), "")
        self.assertEqual(data.get("last_opened_dir"), "")
        self.assertEqual(data.get("window_geometry"), "")


if __name__ == "__main__":
    unittest.main()
