#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s9b_replace_all_bundle_safety.py
===========================================
Verification test suite for Slice S9b:
- REPLACE-ALL-BUNDLE-PREFILTER: Candidate prefiltering on .unity3d bundles decodes
  structured story TextAssets instead of raw byte scanning.
- REPLACE-ALL-UNDO-GAP: Bundle changes in multi-file Replace-All are recorded in
  BulkFileDelta and can be cleanly undone/redone.
- All-or-nothing transaction rollback across mixed text and bundle files.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora
from misora import MisoraApp, BulkFileDelta
from core.bundle_io import load_bundle_story, dispose_unity_env


class TestS9bReplaceAllBundleSafety(unittest.TestCase):
    """Test suite for multi-file Replace-All bundle candidate discovery and undo safety."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s9b_test_"))
        self.orig_config_path = misora.CONFIG_PATH
        self.tmp_config = self.tmp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.tmp_config
        self.app = None

        # Copy fixture bundle
        self.fixture_bundle = REPO_ROOT / "storydata_1001005.unity3d"
        self.test_bundle = self.tmp_dir / "test_story.unity3d"
        if self.fixture_bundle.is_file():
            shutil.copy2(self.fixture_bundle, self.test_bundle)

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

    def test_01_bundle_candidate_discovery_extracts_dialogue(self):
        """Candidate discovery decodes structured StoryDocument and accurately counts dialogue matches."""
        if not self.fixture_bundle.is_file():
            self.skipTest("storydata_1001005.unity3d fixture not found")

        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        # Check dialogue in test bundle
        doc, env, _, _ = load_bundle_story(self.test_bundle)
        try:
            first_box_word = doc.boxes[0].clean_text.split()[0] if doc.boxes[0].clean_text else "私"
        finally:
            dispose_unity_env(env)

        # Set search query to match dialogue
        self.app.search_var.set(first_box_word)
        self.app.replace_var.set("REPLACED_WORD")
        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.var_inc_bundles.set(True)
        self.app.var_inc_text.set(False)

        # Run on_replace_all with confirmed prompt and mocked info dialog
        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # Verify bundle dialogue was updated
        doc2, env2, _, _ = load_bundle_story(self.test_bundle)
        try:
            self.assertIn("REPLACED_WORD", doc2.boxes[0].clean_text)
        finally:
            dispose_unity_env(env2)

    def test_02_bundle_multi_file_replace_all_records_undo_delta(self):
        """Multi-file Replace-All modifying a bundle must record an undoable BulkFileDelta."""
        if not self.fixture_bundle.is_file():
            self.skipTest("storydata_1001005.unity3d fixture not found")

        # Create a text file alongside the bundle
        test_txt = self.tmp_dir / "script.txt"
        test_txt.write_text("Hello TARGET_WORD world\n", encoding="utf-8")

        # Inject TARGET_WORD into the bundle first
        doc, env, obj, _ = load_bundle_story(self.test_bundle)
        try:
            doc.inject_box(0, None, "Bundle TARGET_WORD dialogue")
            from core.bundle_io import save_bundle_story
            save_bundle_story(env, obj, doc, self.test_bundle)
        finally:
            dispose_unity_env(env)

        orig_bundle_bytes = self.test_bundle.read_bytes()
        orig_txt_bytes = test_txt.read_bytes()

        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        self.app.search_var.set("TARGET_WORD")
        self.app.replace_var.set("NEW_WORD")
        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.var_inc_bundles.set(True)
        self.app.var_inc_text.set(True)

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # Both files should be updated
        self.assertIn("NEW_WORD", test_txt.read_text(encoding="utf-8"))
        doc_mod, env_mod, _, _ = load_bundle_story(self.test_bundle)
        try:
            self.assertIn("NEW_WORD", doc_mod.boxes[0].clean_text)
        finally:
            dispose_unity_env(env_mod)

        # Journal must contain an undoable operation
        self.assertTrue(self.app.undo_journal.can_undo())

        # Perform Undo
        self.app.on_undo()

        # Both files must be restored to original bytes
        self.assertEqual(test_txt.read_bytes(), orig_txt_bytes)
        self.assertEqual(self.test_bundle.read_bytes(), orig_bundle_bytes)

        # Perform Redo
        self.app.on_redo()

        self.assertIn("NEW_WORD", test_txt.read_text(encoding="utf-8"))
        doc_redo, env_redo, _, _ = load_bundle_story(self.test_bundle)
        try:
            self.assertIn("NEW_WORD", doc_redo.boxes[0].clean_text)
        finally:
            dispose_unity_env(env_redo)

    def test_03_bundle_rollback_on_write_failure(self):
        """If writing a subsequent file fails during BulkFileDelta undo, modified bundle is rolled back."""
        orig_bundle_bak = self.tmp_dir / "orig.unity3d"
        mod_bundle_bak = self.tmp_dir / "mod.unity3d"
        live_bundle = self.tmp_dir / "live.unity3d"

        orig_bundle_bak.write_bytes(b"ORIG_BUNDLE_DATA")
        mod_bundle_bak.write_bytes(b"MOD_BUNDLE_DATA")
        live_bundle.write_bytes(b"MOD_BUNDLE_DATA")

        text_file = self.tmp_dir / "test.txt"
        text_file.write_text("live_text", encoding="utf-8")

        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        delta = BulkFileDelta(
            description="Test Bulk Undo Rollback",
            per_file=[
                (str(live_bundle), str(orig_bundle_bak), str(mod_bundle_bak), True),
                (str(text_file), "old_text", "new_text"),
            ]
        )

        def write_fail(p, *args, **kwargs):
            if Path(p) == text_file:
                raise OSError("Simulated text write failure")
            orig_write_atomic(p, *args, **kwargs)

        orig_write_atomic = misora.write_atomic_utf8

        with patch("misora.write_atomic_utf8", side_effect=write_fail), \
             patch("misora.messagebox.showerror"):
            with self.assertRaises(OSError):
                self.app._apply_delta(delta, reverse=True, refresh_ui=False)

        # Rollback must restore live_bundle back to MOD_BUNDLE_DATA
        self.assertEqual(live_bundle.read_bytes(), b"MOD_BUNDLE_DATA")


if __name__ == "__main__":
    unittest.main()
