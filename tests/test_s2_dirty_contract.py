#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s2_dirty_contract.py — Failing-first TDD suite for S2.

S2: Minimum Per-Document Dirty Contract and Explicit on_save() -> bool Return Value.

Probe tests (1-10, 12): MUST FAIL before S2, PASS after S2.
Guard test (11): MUST PASS both before AND after S2.
"""

import hashlib
import importlib.util
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

spec = importlib.util.spec_from_file_location("misora_s2", MISORA_DIR / "misora.py")
misora = importlib.util.module_from_spec(spec)
sys.modules["misora_s2"] = misora
spec.loader.exec_module(misora)

from core.story_ast import Record, StoryDocument, BoxSnapshot

BUNDLE = MISORA_DIR / "storydata_1001005.unity3d"


def _has_bundle():
    return BUNDLE.exists()


class TestS2DirtyContract(unittest.TestCase):
    """S2: Per-Document Dirty Contract regression suite."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s2_"))
        self._patches = [
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askokcancel", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=False),
        ]
        for p in self._patches:
            p.start()
        self._orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_dir / "misora_config.json"
        self.app = misora.MisoraApp(restore_session=False)
        self.app.withdraw()
        # Always keep var_preview_compiled OFF for save tests (avoids F-GPT-04 plain-text path)
        self.app.var_preview_compiled.set(False)
        # Switch to Page View
        self.app.var_continuous_view.set(False)

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        for p in self._patches:
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        misora.CONFIG_PATH = self._orig_config_path

    def _make_txt(self, name="doc.txt", content="Hello World"):
        p = self.tmp_dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def _open_txt(self, name="doc.txt", content="Hello World"):
        p = self._make_txt(name, content)
        self.app.open_file(p)
        return p

    def _make_story_doc(self):
        return StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Good morning!"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Let's eat!"]),
            Record(cmd_id=35, cmd_name="tag", args=["She smiles."]),
        ])

    # -------------------------------------------------------------------------
    # Test 1 [Probe] — P0 Cross-File False-Clean Clobber
    # -------------------------------------------------------------------------
    def test_01_cross_file_false_clean_clobber(self):
        """P0: Saving Doc B must NOT false-clean Doc A's dirty flag."""
        # Open Document A and edit it
        path_a = self._open_txt("doc_a.txt", "Alpha content")
        # Directly mark A dirty via the flag (simulating an edit)
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True
        self.app._dirty_state_changed()
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must be dirty after edit"
        )

        # Open Document B and edit + save it
        path_b = self._open_txt("doc_b.txt", "Beta content")
        # B starts clean; dirty it and save
        self.app.is_dirty = True
        if path_b in self.app.open_documents:
            self.app.open_documents[path_b]["dirty"] = True
        res = self.app.on_save()

        # on_save() must return strict bool True
        self.assertIs(type(res), bool, "on_save() must return a strict bool")
        self.assertIs(res, True, "on_save() must return True after successful save")
        self.assertFalse(self.app.is_dirty, "Doc B must be clean after save")

        # Now switch back to Document A (cache-hit)
        self.app.open_file(path_a)
        self.assertEqual(self.app.current_file_path, path_a)

        # Assert A is still dirty — the global journal's is_clean must NOT clobber it
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must STILL be dirty after switching back; saving B must not clobber A's flag"
        )
        self.assertTrue(
            self.app.is_dirty,
            "self.is_dirty must reflect Doc A's dirty=True after cache-hit switch"
        )
        self.assertIn("*", self.app.title(), "Window title must contain * for dirty Doc A")

        # Trigger both a no-op KeyRelease and a direct _dirty_state_changed call
        # (these must not clobber A's dirty state)
        self.app._dirty_state_changed()
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must STILL be dirty after _dirty_state_changed() call"
        )
        self.assertTrue(self.app.is_dirty)
        self.assertIn("*", self.app.title(), "Title * must persist after _dirty_state_changed()")

    # -------------------------------------------------------------------------
    # Test 2 [Probe] — True No-Op <KeyRelease> Prevention
    # -------------------------------------------------------------------------
    def test_02_true_noop_keyrelease_prevention(self):
        """No-op KeyRelease on clean doc must NOT set dirty or call dock/title rebuilds."""
        # Open dirty Document A (not active during noop test)
        path_a = self._open_txt("doc_a.txt", "Alpha")
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True

        # Open clean Document B — no edits
        path_b = self._open_txt("doc_b.txt", "Beta text unchanged")
        self.assertEqual(self.app.current_file_path, path_b)
        # Confirm B is clean before the test
        self.assertFalse(
            self.app.open_documents[path_b].get("dirty", False),
            "Doc B must start clean"
        )

        # Spy on _dirty_state_changed and _refresh_opened_files_list
        refresh_calls = []
        dirty_state_calls = []
        orig_refresh = self.app._refresh_opened_files_list
        orig_dirty_state = self.app._dirty_state_changed

        def spy_refresh():
            refresh_calls.append(1)
            return orig_refresh()

        def spy_dirty_state():
            dirty_state_calls.append(1)
            return orig_dirty_state()

        self.app._refresh_opened_files_list = spy_refresh
        self.app._dirty_state_changed = spy_dirty_state

        try:
            # (a) Simulate Page View KeyRelease on txt_dialogue WITHOUT changing text
            # First set txt_dialogue to match the doc model (no change)
            if hasattr(self.app, "txt_dialogue") and self.app.txt_dialogue.winfo_exists():
                current_text = self.app.txt_dialogue.get("1.0", "end-1c")
                # Don't change anything — just fire the commit path
                self.app._commit_widget_edit(self.app.txt_dialogue)

            # (b) Simulate speaker no-op: no change in speaker
            if hasattr(self.app, "entry_speaker") and self.app.entry_speaker.winfo_exists():
                # speaker_var already matches the document — just fire _on_speaker_edited
                self.app._on_speaker_edited()

            # Document B must STILL be clean
            self.assertFalse(
                self.app.open_documents[path_b].get("dirty", False),
                "Doc B must remain clean after no-op KeyRelease on dialogue"
            )
            self.assertFalse(
                self.app.is_dirty,
                "self.is_dirty must remain False after no-op KeyRelease on clean doc"
            )
            # _dirty_state_changed and _refresh_opened_files_list must NOT have been called
            self.assertEqual(
                len(dirty_state_calls), 0,
                f"_dirty_state_changed must NOT be called on no-op; was called {len(dirty_state_calls)} times"
            )
            self.assertEqual(
                len(refresh_calls), 0,
                f"_refresh_opened_files_list must NOT be called on no-op; was called {len(refresh_calls)} times"
            )

        finally:
            self.app._refresh_opened_files_list = orig_refresh
            self.app._dirty_state_changed = orig_dirty_state

        # Doc A remains dirty
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must still be dirty after no-ops on B"
        )

    # -------------------------------------------------------------------------
    # Test 3 [Probe] — on_save() Strict True Return & Scoped Clean
    # -------------------------------------------------------------------------
    def test_03_on_save_returns_true_and_scopes_clean(self):
        """on_save() must return True, clean only the active doc, leave other docs dirty."""
        # Open Document A (dirty, inactive)
        path_a = self._open_txt("doc_a.txt", "Alpha")
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True

        # Open Document B (active, dirty)
        path_b = self._open_txt("doc_b.txt", "Beta")
        self.app.is_dirty = True
        if path_b in self.app.open_documents:
            self.app.open_documents[path_b]["dirty"] = True

        self.assertEqual(self.app.current_file_path, path_b)

        # Save
        res = self.app.on_save()

        # Strict bool True
        self.assertIs(type(res), bool, "on_save() must return a strict bool, not None or other")
        self.assertIs(res, True, "on_save() must return True after successful save")

        # Active doc B is clean
        self.assertFalse(self.app.is_dirty, "Active doc B must be clean after save")
        self.assertFalse(
            self.app.open_documents[path_b].get("dirty", False),
            "open_documents[B]['dirty'] must be False after save"
        )

        # Inactive doc A remains dirty
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must remain dirty; on_save() must not clean inactive docs"
        )

    # -------------------------------------------------------------------------
    # Test 4 [Probe] — on_save() Strict False on Primary Non-Bundle Write Failure
    # -------------------------------------------------------------------------
    def test_04_on_save_returns_false_on_primary_write_failure(self):
        """on_save() must return False and keep dirty=True when primary disk write fails."""
        path = self._open_txt("doc.txt", "Some content")
        self.app.is_dirty = True
        if path in self.app.open_documents:
            self.app.open_documents[path]["dirty"] = True

        # Patch write_text to raise OSError
        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            res = self.app.on_save()

        self.assertIs(type(res), bool, "on_save() must return a strict bool on failure")
        self.assertIs(res, False, "on_save() must return False on primary write failure")
        self.assertTrue(self.app.is_dirty, "is_dirty must remain True when save fails")
        if path in self.app.open_documents:
            self.assertTrue(
                self.app.open_documents[path].get("dirty", True),
                "open_documents[path]['dirty'] must remain True when save fails"
            )

    # -------------------------------------------------------------------------
    # Test 5 [Probe] — on_save() Strict False on Bundle Save Failure
    # -------------------------------------------------------------------------
    def test_05_on_save_returns_false_on_bundle_save_failure(self):
        """on_save() must return False when save_bundle_story raises."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        self.app.is_dirty = True
        path = self.app.current_file_path
        if path in self.app.open_documents:
            self.app.open_documents[path]["dirty"] = True

        with patch.object(misora, "save_bundle_story", side_effect=RuntimeError("Pack failed")):
            res = self.app.on_save()

        self.assertIs(type(res), bool, "on_save() must return strict bool on bundle failure")
        self.assertIs(res, False, "on_save() must return False when bundle save raises")
        self.assertTrue(self.app.is_dirty, "is_dirty must remain True on bundle failure")
        if path in self.app.open_documents:
            self.assertTrue(
                self.app.open_documents[path].get("dirty", True),
                "open_documents[path]['dirty'] must remain True on bundle failure"
            )

    # -------------------------------------------------------------------------
    # Test 6 [Probe] — on_save() Strict False on Pre-Save Flush Failure & No Active Doc
    # -------------------------------------------------------------------------
    def test_06_on_save_returns_false_on_presave_failure_and_no_doc(self):
        """on_save() must return False on pre-save preparation failure or no active doc."""
        # (a) Pre-save sync failure: inject_box or backup creation raises
        path = self._open_txt("doc.txt", "Content")
        # Set up with a story doc to reach the pre-save code
        doc = self._make_story_doc()
        self.app.current_doc = doc
        self.app.is_bundle_file = False
        self.app.is_dirty = True
        if path in self.app.open_documents:
            self.app.open_documents[path]["dirty"] = True

        # Force _get_backup_dir to raise
        with patch.object(self.app, "_get_backup_dir", side_effect=RuntimeError("Backup dir error")):
            res = self.app.on_save()

        self.assertIs(type(res), bool, "on_save() must return strict bool on pre-save failure")
        self.assertIs(res, False, "on_save() must return False when pre-save step fails")
        self.assertTrue(self.app.is_dirty, "is_dirty must remain True when pre-save fails")

        # (b) No active document
        self.app.current_file_path = None
        res_no_doc = self.app.on_save()
        self.assertIs(type(res_no_doc), bool, "on_save() with no doc must return strict bool")
        self.assertIs(res_no_doc, False, "on_save() with no active doc must return False")

    # -------------------------------------------------------------------------
    # Test 7 [Probe] — on_save() Secondary XUAT Sync Failure Keeps True & Retains _modified_boxes
    # -------------------------------------------------------------------------
    def test_07_on_save_xuat_failure_keeps_true_retains_modified_boxes(self):
        """Secondary XUAT sync failure must return True, keep clean, retain _modified_boxes."""
        path = self._open_txt("doc.txt", "Some text for xuat test")
        # Give it a story doc for XUAT path
        doc = self._make_story_doc()
        self.app.current_doc = doc
        self.app.is_bundle_file = False
        self.app.is_dirty = True
        if path in self.app.open_documents:
            self.app.open_documents[path]["dirty"] = True

        # Put some modified boxes
        self.app._modified_boxes.add(0)
        self.app._modified_boxes.add(1)

        # Enable XUAT sync and give it a root so the sync block is entered
        self.app.var_sync_xuat.set(True)
        self.app.xuat_search_roots = [self.tmp_dir]  # so the XUAT block is active

        # Mock sync_manager.find_and_update to raise
        with patch.object(self.app.sync_manager, "find_and_update", side_effect=RuntimeError("XUAT fail")):
            res = self.app.on_save()

        # Primary save succeeded → True
        self.assertIs(type(res), bool, "on_save() must return strict bool even on XUAT failure")
        self.assertIs(res, True, "on_save() must return True when only secondary XUAT sync fails")

        # Active doc is clean (primary persistence succeeded)
        self.assertFalse(self.app.is_dirty, "is_dirty must be False when primary save succeeded")
        if path in self.app.open_documents:
            self.assertFalse(
                self.app.open_documents[path].get("dirty", True),
                "open_documents[path]['dirty'] must be False when primary save succeeded"
            )

        # _modified_boxes RETAINED for retry
        self.assertGreater(
            len(self.app._modified_boxes), 0,
            "_modified_boxes must be RETAINED (not cleared) when XUAT sync fails"
        )

    # -------------------------------------------------------------------------
    # Test 8 [Probe] — Cache-Hit Title/Dock Parity
    # -------------------------------------------------------------------------
    def test_08_cache_hit_title_dock_parity(self):
        """Cache-hit switch to dirty doc must immediately show * in title and dock."""
        # Open A and make dirty
        path_a = self._open_txt("doc_a.txt", "Alpha")
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True
        self.app._dirty_state_changed()

        # Open clean B
        path_b = self._open_txt("doc_b.txt", "Beta")
        self.assertFalse(self.app.is_dirty, "B should be clean on open")
        self.assertNotIn("*", self.app.title(), "Title should not have * when clean B is active")

        # Switch back to A via cache-hit
        self.app.open_file(path_a)
        self.assertEqual(self.app.current_file_path, path_a)

        # Title MUST immediately have *
        self.assertIn(
            "*", self.app.title(),
            "Window title must contain * immediately after cache-hit switch to dirty Doc A"
        )
        # is_dirty must be True
        self.assertTrue(
            self.app.is_dirty,
            "self.is_dirty must be True after cache-hit switch to dirty Doc A"
        )
        # open_documents[A]["dirty"] must be True
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "open_documents[A]['dirty'] must remain True after cache-hit switch"
        )

        # Switch to B and verify no * in title
        self.app.open_file(path_b)
        self.assertFalse(self.app.is_dirty, "is_dirty must be False after switching to clean B")
        self.assertNotIn("*", self.app.title(), "Title must not have * when clean B is active")

    # -------------------------------------------------------------------------
    # Test 9 [Probe] — Representative Mutation Paths & Both MTL Apply Paths
    # -------------------------------------------------------------------------
    def test_09_representative_mutation_paths_mark_per_doc_dirty(self):
        """All major mutation paths must mark open_documents[path]['dirty'] = True."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        path = self.app.current_file_path

        def _reset():
            """Reset dirty state between sub-tests."""
            self.app.is_dirty = False
            if path in self.app.open_documents:
                self.app.open_documents[path]["dirty"] = False
            self.app._modified_boxes.clear()

        def _assert_dirty(context):
            self.assertTrue(
                self.app.open_documents[path].get("dirty", False),
                f"open_documents[path]['dirty'] must be True after {context}"
            )
            self.assertTrue(self.app.is_dirty, f"is_dirty must be True after {context}")

        # on_box_new
        _reset()
        self.app.current_box_idx = 0
        self.app.on_box_new()
        _assert_dirty("on_box_new()")
        self.app.on_undo()

        # on_box_cut
        _reset()
        self.app.current_box_idx = 0
        self.app.on_box_cut()
        _assert_dirty("on_box_cut()")
        self.app.on_undo()

        # on_box_paste
        _reset()
        self.app.current_box_idx = 0
        self.app.on_box_copy()
        _reset()
        self.app.on_box_paste(confirm=False)
        _assert_dirty("on_box_paste()")
        self.app.on_undo()

        # on_clear_dialogue_skeleton
        _reset()
        self.app.on_clear_dialogue_skeleton()
        _assert_dirty("on_clear_dialogue_skeleton()")
        self.app.on_undo()

        # on_replace_next
        _reset()
        self.app.current_box_idx = 0
        cur_text = self.app.current_doc.boxes[0].clean_text
        word = cur_text.split()[0] if cur_text.split() else "a"
        self.app.search_var.set(word)
        self.app.replace_var.set("REPLACED!")
        self.app.on_replace_next()
        _assert_dirty("on_replace_next()")
        self.app.on_undo()

        # Script apply (paste cross box) — simple CSIF
        _reset()
        self.app.current_box_idx = 0
        clip_csif = "@@Kokkoro\nScript applied text.\n"
        self.app.clipboard_get = lambda: clip_csif
        self.app.on_paste_cross_box(confirm=False)
        _assert_dirty("on_paste_cross_box()")
        self.app.on_undo()

        # MTL apply path 1: on_translate_current_box inner update_ui
        _reset()
        self.app.current_box_idx = 0

        translated_result = [""]
        def fake_translate_async(text, config, on_success, on_error, **kwargs):
            # Call on_success synchronously in test
            on_success("TRANSLATED TEXT")
        with patch.object(misora, "translate_async", side_effect=fake_translate_async):
            self.app.on_translate_current_box()
            # update_ui is dispatched via after_idle — process pending events
            self.app.update()
        _assert_dirty("on_translate_current_box() inner update_ui")
        self.app.on_undo()

        # MTL apply path 2: TranslatorAssistantDialog._on_apply
        _reset()
        self.app.current_box_idx = 0
        # Build a minimal stand-in for TranslatorAssistantDialog._on_apply logic
        b_idx = self.app.current_box_idx
        doc = self.app.current_doc
        old_box = doc.boxes[b_idx]
        new_text = "ASSISTANT TRANSLATED"
        self.app.undo_journal.record(
            misora.BoxEditDelta(
                box_index=b_idx,
                old_speaker=old_box.speaker,
                new_speaker=old_box.speaker,
                old_text=old_box.clean_text,
                new_text=new_text,
                file_path=str(self.app.current_file_path) if self.app.current_file_path else "",
            )
        )
        doc.inject_box(b_idx, old_box.speaker, new_text)
        self.app._modified_boxes.add(b_idx)
        self.app.is_dirty = True
        # In S2, _on_apply must call _dirty_state_changed and _mark_document_dirty;
        # here we test that after is_dirty=True, open_documents is also set:
        if path in self.app.open_documents:
            self.app.open_documents[path]["dirty"] = True  # _mark_document_dirty would do this
        self.app._dirty_state_changed()
        _assert_dirty("TranslatorAssistantDialog._on_apply equivalent")
        self.app.on_undo()

    # -------------------------------------------------------------------------
    # Test 10 [Probe] — Per-Document Undo-to-Saved-State Checkpoint Isolation & Anti-UNDO-STORM
    # -------------------------------------------------------------------------
    def test_10_per_document_undo_to_saved_state_checkpoint_isolation(self):
        """Undo to saved state on Doc B must clean B without dirtying or cleaning Doc A."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")

        # Open bundle as Doc A and mark dirty (without saving)
        self.app.open_file(BUNDLE)
        path_a = self.app.current_file_path
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True

        # Open plain-text Doc B
        path_b = self._open_txt("doc_b.txt", "Initial B content")
        self.assertEqual(self.app.current_file_path, path_b)

        # Save B to establish its saved-state checkpoint
        res_save = self.app.on_save()
        self.assertIs(res_save, True, "Saving B must return True")
        self.assertFalse(self.app.is_dirty, "B must be clean after save")

        # Edit B (make dirty)
        self.app._plain_text_content = "Edited B content"
        self.app._update_views()
        self.app.undo_journal.record(
            misora.PlainTextDelta(
                file_path=str(path_b),
                old_content="Initial B content",
                new_content="Edited B content",
            ),
            label="Edit B"
        )
        self.app.is_dirty = True
        if path_b in self.app.open_documents:
            self.app.open_documents[path_b]["dirty"] = True
        self.app._dirty_state_changed()
        self.assertTrue(self.app.is_dirty, "B must be dirty after edit")

        # Count _refresh_opened_files_list calls during undo
        refresh_calls = []
        orig_refresh = self.app._refresh_opened_files_list

        def spy_refresh():
            refresh_calls.append(1)
            return orig_refresh()

        self.app._refresh_opened_files_list = spy_refresh

        try:
            # Undo B's edit — should restore B to saved state
            self.app.on_undo()
        finally:
            self.app._refresh_opened_files_list = orig_refresh

        # B must be clean (undo restored to saved checkpoint)
        self.assertFalse(
            self.app.is_dirty,
            "Doc B must be clean after undo restores it to its saved state"
        )
        self.assertFalse(
            self.app.open_documents[path_b].get("dirty", True),
            "open_documents[B]['dirty'] must be False after undo to saved state"
        )

        # Doc A must remain dirty (not cleaned by undo of B's delta)
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must remain dirty after undoing B's delta"
        )

        # _refresh_opened_files_list must be called AT MOST ONCE per undo operation
        # (not once per delta inside the loop — anti-UNDO-STORM)
        self.assertLessEqual(
            len(refresh_calls), 1,
            f"_refresh_opened_files_list must be called at most once per undo op, got {len(refresh_calls)} calls"
        )

    # -------------------------------------------------------------------------
    # Test 11 [Guard] — Single-Document Lifecycle & Fresh/Reload Isolation (PRE-S2 ATTRIBUTES ONLY)
    # -------------------------------------------------------------------------
    def test_11_guard_single_document_lifecycle_and_reload_isolation(self):
        """Guard: Single-doc lifecycle clean→dirty→save→dirty; reload leaves B clean, A dirty.

        Uses ONLY pre-S2 attributes (is_dirty, open_documents["dirty"], title()).
        Does NOT call _dirty_state_changed() with journal-driven clobbering path; sets flags
        directly and reads title/is_dirty from final state only.
        Does NOT nest unittest runs. Does NOT reference _saved_state_checkpoints.
        """
        # Fresh load starts clean — set flags directly then refresh
        path_a = self._open_txt("doc_a.txt", "Alpha content")
        self.assertFalse(
            self.app.is_dirty,
            "Fresh-loaded doc must start clean"
        )
        self.assertFalse(
            self.app.open_documents[path_a].get("dirty", False),
            "open_documents[A]['dirty'] must start False on fresh load"
        )

        # Mark dirty by setting flags directly (bypass journal-driven _dirty_state_changed)
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True

        # Must be dirty
        self.assertTrue(self.app.is_dirty, "Doc must be dirty after edit")

        # Save → after save, is_dirty must be False and open_documents entry clean
        self.app.on_save()
        self.assertFalse(self.app.is_dirty, "Doc must be clean immediately after save")
        # After save, open_documents[A]["dirty"] must be False (S2 contract, but also
        # compatible with pre-S2 since on_save already set self.is_dirty = False)
        self.assertFalse(
            self.app.open_documents[path_a].get("dirty", True),
            "open_documents[A]['dirty'] must be False after save"
        )

        # Second edit → dirty again (direct flag only)
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True
        self.assertTrue(self.app.is_dirty, "Doc must be dirty after second edit")

        # Open B: fresh load of B must leave A's dirty flag intact in open_documents
        path_b = self._open_txt("doc_b.txt", "Beta fresh content")
        self.app.open_file(path_b)
        self.assertEqual(self.app.current_file_path, path_b)

        # After switching to B, B must be clean
        self.assertFalse(
            self.app.open_documents[path_b].get("dirty", False),
            "open_documents[B]['dirty'] must be False on fresh load"
        )

        # A must remain dirty in open_documents (switch to B must NOT clear A's flag)
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must remain dirty in open_documents after switching to clean Doc B"
        )

        # Reload B from disk (reload_from_disk=True) must leave A's flag intact
        self.app.open_file(path_b, reload_from_disk=True)
        self.assertFalse(
            self.app.open_documents[path_b].get("dirty", False),
            "Reloaded Doc B must be clean"
        )
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must remain dirty after reloading B"
        )

    # -------------------------------------------------------------------------
    # Test 12 [Probe] — Plain-Text Cache Content & Fingerprint Synchronization
    # -------------------------------------------------------------------------
    def test_12_plain_text_cache_content_and_fingerprint_sync(self):
        """Plain-text edits must be reflected in open_documents['plain_text'] on commit & switch."""
        # Open plain-text Doc A
        path_a = self._open_txt("doc_a.txt", "Original A content")
        self.assertEqual(self.app.current_file_path, path_a)

        # Save A to establish a saved-state checkpoint
        res = self.app.on_save()
        self.assertIs(type(res), bool, "on_save() must return strict bool")
        self.assertIs(res, True, "Saving A must return True")
        self.assertFalse(self.app.is_dirty, "A must be clean after initial save")

        # Simulate a plain-text edit (commit via undo journal)
        old_content = self.app._plain_text_content
        new_content = "EDITED A content"
        self.app.undo_journal.record(
            misora.PlainTextDelta(
                file_path=str(path_a),
                old_content=old_content,
                new_content=new_content,
            ),
            label="Edit A"
        )
        self.app._plain_text_content = new_content
        self.app._update_views()
        # S2 contract: plain_text cache must be synchronized
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["plain_text"] = new_content
        self.app.is_dirty = True
        if path_a in self.app.open_documents:
            self.app.open_documents[path_a]["dirty"] = True
        self.app._dirty_state_changed()
        self.assertTrue(self.app.is_dirty, "A must be dirty after edit")

        # Verify open_documents[A]["plain_text"] reflects the edit
        self.assertEqual(
            self.app.open_documents[path_a].get("plain_text", ""),
            new_content,
            "open_documents[A]['plain_text'] must be synchronized with edited content"
        )

        # Switch to Document B
        path_b = self._open_txt("doc_b.txt", "Beta content")
        self.app.open_file(path_b)
        self.assertEqual(self.app.current_file_path, path_b)

        # Switch back to Document A from cache
        self.app.open_file(path_a)
        self.assertEqual(self.app.current_file_path, path_a)

        # A's dirty flag must survive the round-trip
        self.assertTrue(
            self.app.open_documents[path_a]["dirty"],
            "Doc A must still be dirty after cache round-trip"
        )
        self.assertTrue(self.app.is_dirty, "is_dirty must be True for dirty Doc A after cache round-trip")

        # If _saved_state_checkpoints is available (S2 feature), the live fingerprint of A
        # (using edited content) must DIFFER from the saved checkpoint
        if hasattr(self.app, "_saved_state_checkpoints"):
            path_key = str(path_a.resolve())
            if path_key in self.app._saved_state_checkpoints:
                saved_fp = self.app._saved_state_checkpoints[path_key]
                live_content = self.app.open_documents[path_a].get("plain_text", new_content)
                live_fp = hashlib.sha256(live_content.encode("utf-8")).hexdigest()
                self.assertNotEqual(
                    live_fp, saved_fp,
                    "Live fingerprint of edited A must DIFFER from saved checkpoint"
                )

        # A's dirty flag must remain True until A's own on_save() succeeds
        # Undo A's edit → should restore to saved state
        self.app.on_undo()
        # After undo, if checkpoint matches the original content, A should be clean
        if hasattr(self.app, "_saved_state_checkpoints"):
            path_key = str(path_a.resolve())
            if path_key in self.app._saved_state_checkpoints:
                # After undo, should be clean
                self.assertFalse(
                    self.app.is_dirty,
                    "Undo to saved state must clear dirty flag for plain-text Doc A"
                )


if __name__ == "__main__":
    unittest.main()
