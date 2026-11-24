#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_p3_s09_replace_all_backups.py
=======================================
Verification test suite for Phase 2.5 Slice S09:
- BUG-24: Multi-File Replace-All Cache Keys / Shared Matcher / Closed-File Undo Integrity
  1. Fix _apply_delta(BulkFileDelta) and rollback block to use canonical open_documents keys 'env' and 'obj' (never 'bundle_env'/'target_object') and dispose old env.
  2. Refresh/invalidate all affected open document caches (including inactive open tabs), refuse/prompt before overwriting dirty open files, do NOT mark disk-saved files dirty, resolve and deduplicate candidate paths.
  3. Share ONE compiled matcher (honoring Match Case, Regex, Ignore Whitespace, preserving break_char per QW-R06) and Translation Lock policy across Find, on_replace_next() (skip locked boxes in advance loop!), and on_replace_all() (multi-file bundle locks).
  4. Multi-file BulkFileDelta Undo/Redo must never silently reopen closed tabs (AGENTS.md §16) and must prompt before touching closed disk files without corrupting undo/redo stack on cancellation.
- BUG-20: Shared Collision-Resistant Backup Path Helper (QW-B17 + Grok-N03)
  1. Unique backup path using microsecond timestamp (%Y%m%d_%H%M%S_%f) + short deterministic SHA-256 prefix of normalized full path + exists() disambiguation loop.
  2. Used across on_save(), _save_document_entry(), and on_replace_all() (text and bundle).

Defect Probes (MUST FAIL before patch, PASS after patch):
- Probe 1a: Bulk undo refreshes canonical 'env' and 'obj' keys in open_documents and disposes old env.
- Probe 1b: on_replace_next() uses shared matcher and skips locked boxes in advance loop.
- Probe 1c: Multi-file on_replace_all() enforces Translation Locks across bundles.
- Probe 1d: Closed-file undo confirmation prompts without corrupting undo stack on cancel, and never reopens closed tabs.
- Probe 1e: Inactive open bundle tab has its cache refreshed (and old env disposed) on Replace-All.
- Probe 1f: Replace options matrix (Ignore Whitespace, Match Case, Regex) functions accurately.
- Probe 2: Same-stem files in different folders produce distinct backups in the same second (zero overwrite).

Regression Guards (MUST PASS both before and after patch):
- Guard 1: Collision-resistant backup filenames match *.bak_* pattern expected by existing tests.
- Guard 2: Open document key finder normalizes paths across Windows casing.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora
from core.story_ast import Record, StoryDocument, BoxSnapshot
from core.undo_journal import BulkFileDelta, UndoOperation


def _build_test_app(tmp_dir: Path) -> misora.MisoraApp:
    """Instantiate a headless MisoraApp configured for isolated unit testing."""
    app = misora.MisoraApp.__new__(misora.MisoraApp)
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()

    app.tk = root.tk
    app._w = root._w
    app.children = {}
    app._tclCommands = set()

    # Core state
    app.open_documents = {}
    app.current_file_path = None
    app.current_doc = None
    app.current_unity_env = None
    app.current_text_obj = None
    app.is_bundle_file = False
    app.is_dirty = False
    app._plain_text_content = ""
    app.current_box_idx = 0
    app.is_box0_active = False
    app._card_widgets = {}
    app._modified_boxes = set()
    app._selected_boxes = set()
    app._locked_boxes = set()
    app._locked_box_uids = set()
    app._modified_box_uids = set()
    app._original_jp_by_uid = {}
    app._original_box_texts = {}
    app._saved_state_checkpoints = {}
    app.selected_search_folder = None
    app.xuat_search_roots = []
    app.project_folder = None
    app.bepinex_project_folder = None
    app.backup_folder = str(tmp_dir / "backups")

    from core.undo_journal import MasterUndoJournal
    app.undo_journal = MasterUndoJournal()
    app.logger = MagicMock()
    app.prefs = {}
    app.theme = {
        "highlight_bg": "#aabbcc",
        "bg_panel": "#ffffff",
        "fg_text": "#000000",
        "fg_muted": "#888888",
        "misora_pink": "#ff69b4",
        "bg_editor": "#ffffff",
        "border": "#cccccc",
    }

    # Tk variables
    app.var_continuous_view = tk.BooleanVar(master=root, value=False)
    app.var_preview_compiled = tk.BooleanVar(master=root, value=False)
    app.var_select_box_mode = tk.BooleanVar(master=root, value=False)
    app.var_sync_xuat = tk.BooleanVar(master=root, value=False)
    app.var_inc_bundles = tk.BooleanVar(master=root, value=True)
    app.var_inc_text = tk.BooleanVar(master=root, value=True)
    app.var_case = tk.BooleanVar(master=root, value=False)
    app.var_regex = tk.BooleanVar(master=root, value=False)
    app.var_ignore_ws = tk.BooleanVar(master=root, value=False)
    app.search_var = tk.StringVar(master=root, value="")
    app.replace_var = tk.StringVar(master=root, value="")
    app.speaker_var = tk.StringVar(master=root, value="")
    app.scope_var = tk.StringVar(master=root, value="folder")
    app.folder_path_var = tk.StringVar(master=root, value="")

    # Widgets
    app.txt_dialogue = tk.Text(root)
    app.txt_dialogue.tag_configure("search_hit", background="#ffff00")
    app.txt_continuous = tk.Text(root)
    app.txt_raw = tk.Text(root)
    app.gd_inner = MagicMock()
    app.gd_inner.winfo_reqheight.return_value = 400
    app.gd_inner.winfo_reqwidth.return_value = 800
    app.gd_canvas = MagicMock()
    app.gd_canvas.winfo_width.return_value = 800
    app.gd_canvas.winfo_height.return_value = 600
    app._gd_canvas_win = 1
    app.lbl_status = MagicMock()
    app.lbl_gutter_clean = MagicMock()
    app.lbl_box_counter = MagicMock()
    app.lbl_voice_cue = MagicMock()
    app.lbl_speaker_voice = MagicMock()
    app.speaker_entry = MagicMock()
    app.scale_box = MagicMock()

    # Search engine
    from core.search_engine import ProjectSearchEngine
    app.search_engine = ProjectSearchEngine()

    # Toast and status stubs
    app.show_toast = MagicMock()
    app.set_status = MagicMock()
    app._root = root

    return app


class TestP3S09ReplaceAllBackups(unittest.TestCase):
    """Test suite covering BUG-24 and BUG-20 defects and regression guards."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s09_test_"))
        self.orig_config_path = misora.CONFIG_PATH
        self.tmp_config = self.tmp_dir / "misora_config.json"
        self.tmp_config.write_text("{}", encoding="utf-8")
        misora.CONFIG_PATH = self.tmp_config

        self.app = _build_test_app(self.tmp_dir)

    def tearDown(self):
        if hasattr(self, "app") and self.app is not None:
            try:
                self.app._root.destroy()
            except Exception:
                pass
            self.app = None
        misora.CONFIG_PATH = self.orig_config_path
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # =========================================================================
    # DEFECT PROBES (MUST FAIL BEFORE PATCH, PASS AFTER PATCH)
    # =========================================================================

    def test_probe_1a_bulk_undo_cache_keys_and_env_disposal(self):
        """[Probe 1a — BUG-24] BulkFileDelta undo refreshes 'env'/'obj' and disposes old env."""
        bundle_file = (self.tmp_dir / "active.unity3d").resolve()
        bundle_file.write_bytes(b"CURRENT_BUNDLE")

        orig_bak = self.tmp_dir / "active.orig_bak.unity3d"
        orig_bak.write_bytes(b"ORIGINAL_BUNDLE")
        mod_bak = self.tmp_dir / "active.mod_bak.unity3d"
        mod_bak.write_bytes(b"MODIFIED_BUNDLE")

        old_env = MagicMock(name="old_unity_env")
        old_obj = MagicMock(name="old_target_obj")
        doc_old = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Modified dialogue"])])

        self.app.open_documents[bundle_file] = {
            "doc": doc_old,
            "env": old_env,
            "obj": old_obj,
            "is_bundle": True,
            "dirty": True,
            "plain_text": "",
        }

        delta = BulkFileDelta(
            description="Replace All in bundle",
            per_file=[(str(bundle_file), str(orig_bak), str(mod_bak), True)],
        )

        new_env = MagicMock(name="new_restored_env")
        new_obj = MagicMock(name="new_restored_obj")
        doc_new = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Original dialogue"])])

        mock_dispose = MagicMock()
        with patch("misora.load_bundle_story", return_value=(doc_new, new_env, new_obj, "storydata")), \
             patch("misora.dispose_unity_env", mock_dispose):
            self.app._apply_delta(delta, reverse=True, refresh_ui=False)

        entry = self.app.open_documents[bundle_file]

        # In pre-patch code, _apply_delta stored into 'bundle_env' and 'target_object',
        # leaving 'env' and 'obj' holding stale old_env and old_obj.
        self.assertIs(entry.get("env"), new_env, "open_documents cache key 'env' must point to new_env")
        self.assertIs(entry.get("obj"), new_obj, "open_documents cache key 'obj' must point to new_obj")
        self.assertNotIn("bundle_env", entry, "Legacy key 'bundle_env' must never be populated")
        self.assertNotIn("target_object", entry, "Legacy key 'target_object' must never be populated")

        # In pre-patch code, dispose_unity_env was called on entry.get('bundle_env') (which was None),
        # so old_env was never disposed (memory leak).
        mock_dispose.assert_called_with(old_env)

    def test_probe_1b_replace_next_shared_matcher_and_skip_locked(self):
        """[Probe 1b — BUG-24] on_replace_next() honors Match Case and skips locked boxes in advance loop."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Hero", "Target Word"]),       # Box 0 (unlocked)
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hero", "Target Word"]),       # Box 1 (LOCKED)
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hero", "Target Word"]),       # Box 2 (unlocked)
        ]
        doc = StoryDocument(recs)
        self.app.current_doc = doc
        cur_file = (self.tmp_dir / "story.txt").resolve()
        cur_file.write_text("dummy", encoding="utf-8")
        self.app.current_file_path = cur_file
        self.app.open_documents[cur_file] = {"doc": doc, "dirty": False, "plain_text": ""}

        # Lock Box 1
        box1_uid = getattr(doc.boxes[1], "uid", None) or doc.boxes[1].segs[0].record.uid
        self.app._locked_boxes.add(1)
        self.app._locked_box_uids.add(box1_uid)

        self.app.search_var.set("Target Word")
        self.app.replace_var.set("Replacement Word")
        self.app.var_case.set(True)

        # First replace: replaces in Box 0
        with patch.object(self.app, "_update_views"):
            self.app.on_replace_next()

        self.assertEqual(doc.boxes[0].clean_text, "Replacement Word")
        self.assertEqual(self.app.current_box_idx, 0)

        # Second replace: Box 0 no longer matches, advance loop searches forward.
        # Box 1 is LOCKED. Pre-patch code lands on Box 1 and stops there.
        # Patched code MUST skip Box 1 and advance directly to Box 2!
        with patch.object(self.app, "_update_views"):
            self.app.on_replace_next()

        self.assertEqual(
            self.app.current_box_idx,
            2,
            "on_replace_next() advance loop must skip locked Box 1 and advance to unlocked Box 2",
        )

    def test_probe_1c_multi_file_replace_all_enforces_locks(self):
        """[Probe 1c — BUG-24] Multi-file on_replace_all() preserves locked boxes in bundles."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Hero", "Keyword in Box 0"]),  # Box 0 (LOCKED)
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hero", "Keyword in Box 1"]),  # Box 1 (unlocked)
        ]
        doc = StoryDocument(recs)
        box0_uid = getattr(doc.boxes[0], "uid", None) or doc.boxes[0].segs[0].record.uid

        bundle_path = (self.tmp_dir / "story.unity3d").resolve()
        bundle_path.write_bytes(b"BUNDLE_DATA")

        mock_env = MagicMock()
        mock_obj = MagicMock()

        self.app.open_documents[bundle_path] = {
            "doc": doc,
            "env": mock_env,
            "obj": mock_obj,
            "is_bundle": True,
            "dirty": False,
            "locked_box_uids": {box0_uid},
        }

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.search_var.set("Keyword")
        self.app.replace_var.set("Replaced")
        self.app.var_inc_bundles.set(True)
        self.app.var_inc_text.set(False)

        with patch("misora.load_bundle_story", return_value=(doc, mock_env, mock_obj, "story")), \
             patch("misora.save_bundle_story"), \
             patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # In pre-patch code, multi-file Replace-All replaced all occurrences indiscriminately.
        # Box 0 is protected by Translation Lock and must remain untouched.
        self.assertIn("Keyword in Box 0", doc.boxes[0].clean_text, "Locked Box 0 must be preserved")
        self.assertIn("Replaced in Box 1", doc.boxes[1].clean_text, "Unlocked Box 1 must be replaced")

    def test_probe_1d_closed_file_undo_confirmation_no_corruption(self):
        """[Probe 1d — BUG-24] Closed-file undo prompt does NOT corrupt undo stack on cancellation."""
        closed_file = (self.tmp_dir / "closed_script.txt").resolve()
        closed_file.write_text("current_on_disk", encoding="utf-8")

        # Record operation on closed file
        delta = BulkFileDelta(
            description="Replace in closed script",
            per_file=[(str(closed_file), "original_text", "current_on_disk")],
        )
        self.app.undo_journal.record(delta, label="Bulk Replace Op")
        self.assertTrue(self.app.undo_journal.can_undo())

        # User cancels the closed-file confirmation dialog
        with patch("misora.messagebox.askyesno", return_value=False) as mock_ask:
            self.app.on_undo()

        # Confirmation dialog MUST have been shown before touching disk
        mock_ask.assert_called_once()
        # Disk content must be untouched
        self.assertEqual(closed_file.read_text(encoding="utf-8"), "current_on_disk")
        # In pre-patch code, on_undo popped the op unconditionally, corrupting the journal.
        # In patched code, cancellation leaves the undo stack intact.
        self.assertTrue(
            self.app.undo_journal.can_undo(),
            "Undo stack must not be popped or corrupted when user cancels closed-file confirmation",
        )
        # Closed file must NEVER be silently opened into open_documents
        self.assertNotIn(closed_file, self.app.open_documents)

    def test_probe_1e_inactive_open_bundle_cache_refreshed_on_replace_all(self):
        """[Probe 1e — BUG-24] Inactive open bundle tab has its in-memory cache refreshed on Replace-All."""
        active_txt = (self.tmp_dir / "active.txt").resolve()
        active_txt.write_text("dummy", encoding="utf-8")
        self.app.current_file_path = active_txt
        self.app.open_documents[active_txt] = {"dirty": False, "plain_text": "dummy", "doc": None}

        bundle_path = (self.tmp_dir / "inactive.unity3d").resolve()
        bundle_path.write_bytes(b"BUNDLE_BYTES")

        old_env = MagicMock(name="old_inactive_env")
        old_obj = MagicMock(name="old_inactive_obj")
        doc_initial = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Hero", "Target dialogue"])])

        self.app.open_documents[bundle_path] = {
            "doc": doc_initial,
            "env": old_env,
            "obj": old_obj,
            "is_bundle": True,
            "dirty": False,
        }

        fresh_env = MagicMock(name="fresh_inactive_env")
        fresh_obj = MagicMock(name="fresh_inactive_obj")
        doc_updated = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Hero", "Updated dialogue"])])

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.search_var.set("Target")
        self.app.replace_var.set("Updated")
        self.app.var_inc_bundles.set(True)
        self.app.var_inc_text.set(False)

        mock_dispose = MagicMock()
        with patch("misora.load_bundle_story", side_effect=[
            (doc_initial, MagicMock(), MagicMock(), "story"),  # prefilter scan
            (doc_initial, MagicMock(), MagicMock(), "story"),  # replacement load
            (doc_updated, fresh_env, fresh_obj, "story"),      # cache refresh load
        ]), \
             patch("misora.save_bundle_story"), \
             patch("misora.dispose_unity_env", mock_dispose), \
             patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # In pre-patch code, line 10090 only reloaded current_file_path.
        # Inactive open bundle was left with stale doc and undisposed env.
        entry = self.app.open_documents[bundle_path]
        self.assertEqual(entry["doc"].boxes[0].clean_text, "Updated dialogue")
        self.assertIs(entry["env"], fresh_env)
        self.assertFalse(entry["dirty"], "Disk-saved document must not be marked dirty")
        mock_dispose.assert_called_with(old_env)

    def test_probe_1f_replace_options_matrix(self):
        """[Probe 1f — BUG-24] Replace helper accurately honors Ignore Whitespace, Match Case, and Regex."""
        # 1. Ignore Whitespace
        self.app.var_ignore_ws.set(True)
        self.app.var_case.set(False)
        self.app.var_regex.set(False)
        self.app.search_var.set("hello world")
        self.app.replace_var.set("greeting")

        text_ws = "Say hello   world to everyone."
        matcher_ws = self.app.search_engine._compile_matcher(
            misora.SearchOptions(query="hello world", ignore_whitespace=True)
        )
        new_tx, n = self.app._apply_compiled_replacement(
            text_ws, matcher_ws, "greeting", is_regex=False, ignore_ws=True
        )
        self.assertEqual(new_tx, "Say greeting to everyone.")
        self.assertEqual(n, 1)

        # 2. Match Case
        matcher_case = self.app.search_engine._compile_matcher(
            misora.SearchOptions(query="Hero", match_case=True)
        )
        text_case = "Hero meets hero."
        new_case, n_case = self.app._apply_compiled_replacement(
            text_case, matcher_case, "Champion", is_regex=False, ignore_ws=False
        )
        self.assertEqual(new_case, "Champion meets hero.")
        self.assertEqual(n_case, 1)

        # 3. Regex with group backreference
        matcher_rx = self.app.search_engine._compile_matcher(
            misora.SearchOptions(query=r"(\w+) (\d+)", use_regex=True)
        )
        text_rx = "Item 42 found."
        new_rx, n_rx = self.app._apply_compiled_replacement(
            text_rx, matcher_rx, r"[\2:\1]", is_regex=True, ignore_ws=False
        )
        self.assertEqual(new_rx, "[42:Item] found.")
        self.assertEqual(n_rx, 1)

    def test_probe_2_collision_resistant_backups(self):
        """[Probe 2 — BUG-20] Same-stem files in different folders produce distinct backups in same second."""
        dir1 = self.tmp_dir / "folder1"
        dir2 = self.tmp_dir / "folder2"
        dir1.mkdir()
        dir2.mkdir()

        file1 = (dir1 / "story.txt").resolve()
        file2 = (dir2 / "story.txt").resolve()
        file1.write_text("content 1", encoding="utf-8")
        file2.write_text("content 2", encoding="utf-8")

        bak_dir = self.tmp_dir / "backups"
        bak_dir.mkdir(parents=True, exist_ok=True)

        # In pre-patch code, line 8834 used `f"{stem}.bak_{ts}{suffix}"` with %Y%m%d_%H%M%S.
        # Generating paths within the same second produced the exact same path:
        # story.bak_20261124_160000.txt (overwriting file1's backup with file2's).
        bak1 = misora.make_collision_resistant_backup_path(file1, bak_dir, tag="bak")
        bak1.write_text("backup 1", encoding="utf-8")

        bak2 = misora.make_collision_resistant_backup_path(file2, bak_dir, tag="bak")
        bak2.write_text("backup 2", encoding="utf-8")

        self.assertNotEqual(
            bak1,
            bak2,
            "Same-stem files in different folders must produce distinct backup paths (BUG-20)",
        )
        all_baks = list(bak_dir.glob("story.bak_*.txt"))
        self.assertEqual(
            len(all_baks),
            2,
            f"Expected exactly 2 distinct backup files, found: {[p.name for p in all_baks]}",
        )

    # =========================================================================
    # REGRESSION GUARDS (MUST PASS BOTH BEFORE AND AFTER PATCH)
    # =========================================================================

    def test_guard_1_collision_resistant_pattern_compatibility(self):
        """[Guard 1] Generated backup filenames match sample.bak_*.txt for backward compatibility."""
        p = Path("C:/project/sample.txt")
        bak_dir = self.tmp_dir / "backups"
        bak = misora.make_collision_resistant_backup_path(p, bak_dir, tag="bak")
        self.assertTrue(
            bak.name.startswith("sample.bak_"),
            f"Backup name '{bak.name}' must start with 'sample.bak_'",
        )
        self.assertTrue(
            bak.name.endswith(".txt"),
            f"Backup name '{bak.name}' must end with '.txt'",
        )

    def test_guard_2_open_doc_key_normalizer(self):
        """[Guard 2] _find_open_doc_key normalizes case and resolution on Windows."""
        f_real = (self.tmp_dir / "SubDir" / "test.txt").resolve()
        f_real.parent.mkdir(parents=True, exist_ok=True)
        f_real.write_text("hello", encoding="utf-8")

        self.app.open_documents[f_real] = {"dirty": False}

        # Query with lowercase path
        query_path = str(f_real).lower()
        found_key = self.app._find_open_doc_key(query_path)
        self.assertEqual(found_key, f_real)

        # Query with non-open path
        self.assertIsNone(self.app._find_open_doc_key("C:/nonexistent.txt"))


if __name__ == "__main__":
    unittest.main()
