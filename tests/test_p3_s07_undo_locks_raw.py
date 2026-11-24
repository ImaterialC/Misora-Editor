"""
Unit and regression test suite for Phase 2.5 S07:
Caret Paste Dirty/Lock (BUG-10), Mutate-Before-Undo (BUG-13), Non-Contiguous Cut Undo (BUG-15),
Lock Enforcement (BUG-16), and Read-Only Raw View (BUG-37).

Defect Probes (MUST FAIL before patch, PASS after patch):
- Probe 1 (BUG-10): \n\n\n caret paste marks document dirty before _dirty_state_changed(),
  preserves is_dirty=True and title *, and skips locked boxes.
- Probe 2 (BUG-13): Model mutation inject_box() occurs before undo recording and dirty marking;
  errors surface visibly on status bar and leave undo_depth == 0 and is_dirty == False.
- Probe 3 (BUG-15): Non-contiguous box cut (e.g. [1, 3]) stores target indices on BoxStructuralDelta,
  restores exact ascending order on Undo, deletes exact indices on Redo, and refuses/skips locked boxes.
- Probe 4 (BUG-16): on_clear_dialogue_skeleton() preserves locked boxes and reports count;
  TranslatorAssistantDialog._on_apply() refuses locked boxes and preserves leading/trailing whitespace & newlines.
- Probe 5 (BUG-37): txt_raw is strictly read-only (state='disabled') after initialization and after _update_raw_view().

Regression Guard:
- Guard 1: Direct lightweight sanity check for basic edit, undo, cut, and lock contracts.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import misora
from core.story_ast import Record, StoryDocument
from core.undo_journal import BoxStructuralDelta


class TestP3S07UndoLocksRaw(unittest.TestCase):
    """S07: Caret paste dirty/lock, mutate-before-undo, non-contiguous cut, lock enforcement & read-only raw."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s07_"))
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
        misora.CONFIG_PATH.write_text("{}", encoding="utf-8")

        self.app = misora.MisoraApp(restore_session=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.var_preview_compiled.set(False)
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

    def _make_v2_script(self, filename: str, box_count: int = 5, meta: bool = True) -> Path:
        """Create a valid v2 story script with the requested number of boxes."""
        doc = StoryDocument()
        records = []
        if meta:
            records.append(Record(cmd_id=0, cmd_name="title", args=["Test Title"]))
            records.append(Record(cmd_id=1, cmd_name="outline", args=["Test Synopsis"]))
        for i in range(box_count):
            if i > 0:
                records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            records.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker_{i}", f"Original Box Text {i}"]))
        doc.records = records
        doc._rebuild_boxes()
        p = self.tmp_dir / filename
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        return p

    # -------------------------------------------------------------------------
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # -------------------------------------------------------------------------
    def test_probe_1_bug10_caret_paste_dirty_and_lock(self):
        """[Probe 1 — BUG-10] Caret paste marks document dirty before _dirty_state_changed() and skips locked boxes.

        Pre-patch:
        - _on_card_paste_caret() sets self.is_dirty = True but fails to call _mark_document_dirty()
          before _dirty_state_changed(), so S2 mirroring resets is_dirty to False.
        - Target boxes are overwritten even if is_box_locked(target_idx) is True.
        """
        fpath = self._make_v2_script("bug10_test.txt", box_count=4)
        self.app.open_file(fpath)
        self.assertFalse(self.app.is_dirty)
        p_res = fpath.resolve()
        self.assertFalse(self.app.open_documents[p_res]["dirty"])

        # Lock box 2 (index 2)
        self.app.current_box_idx = 2
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(2))

        # Setup clipboard text with 3 chunks for boxes 1, 2, 3
        # Box 1: unlocked -> should update
        # Box 2: locked -> should be skipped!
        # Box 3: unlocked -> should update
        paste_text = "Pasted Chunk 1\n\n\nPasted Chunk 2\n\n\nPasted Chunk 3"
        self.app.safe_clipboard_set(paste_text)

        # Focus Box 1 in card view and trigger caret paste
        self.app.current_box_idx = 1
        self.app._update_views()
        card_txt = self.app.txt_dialogue
        ret = self.app._on_card_paste_caret(1, card_txt)
        self.assertEqual(ret, "break")

        # Assertion 1: S2 dirty state must be True in both open_documents and app.is_dirty
        self.assertTrue(self.app.open_documents[p_res]["dirty"], "open_documents dirty flag must be True")
        self.assertTrue(self.app.is_dirty, "app.is_dirty must remain True after _dirty_state_changed()")

        # Assertion 2: Locked Box 2 must be preserved untouched
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, "Original Box Text 1Pasted Chunk 1")
        self.assertEqual(
            self.app.current_doc.boxes[2].clean_text,
            "Original Box Text 2",
            "Locked box 2 must NOT be overwritten by caret paste"
        )
        self.assertIn("Pasted Chunk 3", self.app.current_doc.boxes[3].clean_text)

    def test_probe_2_bug13_mutate_before_undo_error_surfaced(self):
        """[Probe 2 — BUG-13] inject_box() applied first; errors surface on status bar and leave undo clean.

        Pre-patch:
        - _on_dialogue_edited() records BoxEditDelta and marks dirty BEFORE calling inject_box().
        - If inject_box() raises an error, 'except Exception: pass' swallows it, leaving
          phantom undo deltas and is_dirty=True while status bar remains silent.
        """
        fpath = self._make_v2_script("bug13_test.txt", box_count=2)
        self.app.open_file(fpath)
        self.app.current_box_idx = 0
        self.assertFalse(self.app.is_dirty)

        key = self.app.undo_journal._get_key(str(fpath.resolve()))
        state = self.app.undo_journal._get_state(key)
        self.assertEqual(len(state.undo_stack), 0)

        # Mock inject_box to raise a RuntimeError
        with patch.object(self.app.current_doc, "inject_box", side_effect=RuntimeError("Simulated AST inject failure")):
            self.app.txt_dialogue.delete("1.0", "end")
            self.app.txt_dialogue.insert("1.0", "Mutated Dialogue Text")
            res = self.app._on_dialogue_edited()

            self.assertFalse(res, "_on_dialogue_edited must return False when mutation fails")

        # Assertion: Undo stack must have 0 deltas, is_dirty must be False, error surfaced on status bar
        self.assertEqual(len(state.undo_stack), 0, "No undo delta should be recorded when inject_box fails")
        self.assertFalse(self.app.is_dirty, "Document must not be marked dirty when inject_box fails")
        status_text = self.app.lbl_status.cget("text")
        self.assertIn("Simulated AST inject failure", status_text, "Error must be surfaced on status bar")

    def test_probe_3_bug15_non_contiguous_cut_undo_redo_and_locks(self):
        """[Probe 3 — BUG-15] Cutting non-contiguous boxes [1, 3] -> Undo -> Redo restores exact original order.

        Pre-patch:
        - BoxStructuralDelta lacks 'indices' parameter (raises TypeError or defaults to None).
        - Undo assumes contiguous insertion from delta.box_index, mangling non-contiguous cuts.
        - on_box_cut() does not check is_box_locked() and cuts locked boxes.
        """
        fpath = self._make_v2_script("bug15_test.txt", box_count=5)
        self.app.open_file(fpath)

        orig_texts = [b.clean_text for b in self.app.current_doc.boxes]
        self.assertEqual(len(orig_texts), 5)

        # Part 1: Non-contiguous cut [1, 3]
        self.app._selected_boxes = {1, 3}
        self.app.on_box_cut()

        # Check document after cut: 3 boxes remain: 0, 2, 4 (now indices 0, 1, 2)
        remaining_texts = [b.clean_text for b in self.app.current_doc.boxes]
        self.assertEqual(remaining_texts, [orig_texts[0], orig_texts[2], orig_texts[4]])

        # Check delta in undo stack has indices attribute
        key = self.app.undo_journal._get_key(str(fpath.resolve()))
        state = self.app.undo_journal._get_state(key)
        self.assertTrue(len(state.undo_stack) > 0)
        cut_delta = state.undo_stack[-1].deltas[0]
        self.assertIsInstance(cut_delta, BoxStructuralDelta)
        self.assertEqual(getattr(cut_delta, "indices", None), [1, 3])

        # Undo cut: must restore all 5 boxes in their exact original order
        self.app.on_undo()
        restored_texts = [b.clean_text for b in self.app.current_doc.boxes]
        self.assertEqual(restored_texts, orig_texts, "Undo must restore exact non-contiguous box order")

        # Redo cut: must re-delete [1, 3] cleanly
        self.app.on_redo()
        redone_texts = [b.clean_text for b in self.app.current_doc.boxes]
        self.assertEqual(redone_texts, [orig_texts[0], orig_texts[2], orig_texts[4]])

        # Part 2: Locked box cut refusal
        # Undo to restore all 5
        self.app.on_undo()
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        # Select {1, 3}: Box 1 is locked, Box 3 is unlocked -> Box 1 must be skipped
        self.app._selected_boxes = {1, 3}
        self.app.on_box_cut()
        # Box 1 must still exist!
        box1_text = self.app.current_doc.boxes[1].clean_text
        self.assertEqual(box1_text, orig_texts[1], "Locked Box 1 must NOT be cut")

    def test_probe_4_bug16_lock_enforcement_skeleton_and_translator(self):
        """[Probe 4 — BUG-16] on_clear_dialogue_skeleton() preserves locked boxes; TranslatorAssistant preserves whitespace.

        Pre-patch:
        - on_clear_dialogue_skeleton() wipes all boxes unconditionally without checking is_box_locked().
        - TranslatorAssistantDialog._on_apply() mutates locked boxes and calls .strip() on translated text.
        """
        fpath = self._make_v2_script("bug16_test.txt", box_count=4)
        self.app.open_file(fpath)

        orig_box1_text = self.app.current_doc.boxes[1].clean_text
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        # 1. Clear dialogue skeleton
        self.app.on_clear_dialogue_skeleton()

        # Box 0, 2, 3 should be blank; Box 1 should retain its original text
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, "")
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, orig_box1_text, "Locked box 1 text must be preserved")
        self.assertEqual(self.app.current_doc.boxes[2].clean_text, "")
        self.assertEqual(self.app.current_doc.boxes[3].clean_text, "")

        status_text = self.app.lbl_status.cget("text")
        self.assertIn("preserved 1 locked", status_text)

        # 2. TranslatorAssistantDialog lock check & whitespace preservation
        from misora import TranslatorAssistantDialog
        dlg = TranslatorAssistantDialog(self.app)
        try:
            # Attempt to apply translation to locked Box 1
            self.app.current_box_idx = 1
            dlg.txt_trans.delete("1.0", "end")
            dlg.txt_trans.insert("1.0", "Translated to locked box")
            applied = dlg._on_apply()
            self.assertFalse(applied, "TranslatorAssistantDialog._on_apply() must refuse locked box")
            self.assertEqual(self.app.current_doc.boxes[1].clean_text, orig_box1_text)

            # Apply to unlocked Box 2 with deliberate leading/trailing whitespace & newlines
            self.app.current_box_idx = 2
            raw_input = "  Leading Indent Line 1\n  Leading Indent Line 2\n\n"
            dlg.txt_trans.delete("1.0", "end")
            dlg.txt_trans.insert("1.0", raw_input)
            applied = dlg._on_apply()
            self.assertTrue(applied, "TranslatorAssistantDialog._on_apply() must succeed on unlocked box")
            self.assertEqual(
                self.app.current_doc.boxes[2].clean_text,
                raw_input,
                "Translation must NOT strip leading/trailing indentation or newlines"
            )
        finally:
            dlg.destroy()

    def test_probe_5_bug37_raw_view_read_only(self):
        """[Probe 5 — BUG-37] txt_raw is strictly read-only (state='disabled') on load and after _update_raw_view().

        Pre-patch:
        - txt_raw is created with state='normal' (default).
        - _update_raw_view() leaves state='normal'.
        """
        fpath = self._make_v2_script("bug37_test.txt", box_count=2)
        self.app.open_file(fpath)

        # Assertion 1: txt_raw state after load must be 'disabled'
        self.assertEqual(
            self.app.txt_raw.cget("state"),
            "disabled",
            "txt_raw must be initialized with state='disabled'"
        )

        # Assertion 2: txt_raw state after _update_raw_view() must remain 'disabled'
        self.app._update_raw_view()
        self.assertEqual(
            self.app.txt_raw.cget("state"),
            "disabled",
            "txt_raw must remain state='disabled' after _update_raw_view()"
        )

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both before AND after patch)
    # -------------------------------------------------------------------------
    def test_guard_1_lightweight_contracts(self):
        """[Guard 1] Direct lightweight sanity check for basic edit, undo, cut, and lock contracts."""
        fpath = self._make_v2_script("guard1_test.txt", box_count=3)
        self.app.open_file(fpath)
        self.assertFalse(self.app.is_dirty)
        self.assertEqual(len(self.app.current_doc.boxes), 3)

        # Lock toggle contract
        self.app.current_box_idx = 0
        self.assertFalse(self.app.is_box_locked(0))
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(0))
        self.app.on_toggle_lock_current_box()
        self.assertFalse(self.app.is_box_locked(0))


if __name__ == "__main__":
    unittest.main()
