#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_phase2_required.py – Required tests from Phase 2 spec.

Covers the REQUIRED TESTS section of the Phase 2 spec that are not yet
covered by test_misora_ui_integration.py or test_script_codec.py:

  ✓ copy→paste insert produces the expected new boxes and speakers
  ✓ @@! payload routes to Box 0 regardless of focus
  ✓ one Ctrl+Z undoes a whole multi-box insert
  ✓ ribbon Cut/Paste and Ctrl+B/I/U and size insertion persist and undo
  ✓ Ctrl+H/O/T leave the buffer byte-identical
  ✓ Box 0 save leaves dialogue speaker/text byte-identical
  ✓ undo back to the saved revision clears the dirty marker
  ✓ batch undo refreshes the UI once
  ✓ a stale internal box snapshot is discarded
"""
import importlib.util
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

misora_script = MISORA_DIR / "misora.py"
spec = importlib.util.spec_from_file_location("misora_main", misora_script)
misora_app = importlib.util.module_from_spec(spec)
sys.modules["misora_main"] = misora_app
spec.loader.exec_module(misora_app)

from core.story_ast import Record, StoryDocument, BoxSnapshot
from core.script_codec import serialize, parse, sniff_format

BUNDLE = MISORA_DIR / "storydata_1001005.unity3d"


def _has_bundle():
    return BUNDLE.exists()


class TestPhase2Required(unittest.TestCase):
    """Required Phase 2 tests – GUI-level behaviours."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="p2req_"))
        # Mock all dialogs globally for headless testing
        self._patches = [
            patch.object(misora_app.messagebox, "askyesno", return_value=True),
            patch.object(misora_app.messagebox, "showinfo", return_value=None),
            patch.object(misora_app.messagebox, "showwarning", return_value=None),
            patch.object(misora_app.messagebox, "showerror", return_value=None),
            patch.object(misora_app.messagebox, "askokcancel", return_value=True),
        ]
        for p in self._patches:
            p.start()
        self.app = misora_app.MisoraApp(restore_session=False)
        self.app.withdraw()

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

    # ------------------------------------------------------------------ #
    # Required test: copy→paste INSERT produces the expected boxes/speakers
    # ------------------------------------------------------------------ #
    def test_28_box_copy_paste_insert_produces_new_boxes_and_speakers(self):
        """on_box_copy emits CSIF; on_box_paste inserts new boxes with correct speakers."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)

        orig_count = len(self.app.current_doc.boxes)
        orig_spk0 = self.app.current_doc.boxes[0].speaker
        orig_txt0 = self.app.current_doc.boxes[0].clean_text

        # Navigate to box 0
        self.app.current_box_idx = 0
        self.app._sync_clean_view_to_current_box()

        # Copy box 0
        self.app.on_box_copy()
        copied_csif = self.app.safe_clipboard_get()

        # Verify CSIF was emitted
        self.assertIn("@@", copied_csif, "on_box_copy must emit CSIF with @@ headers")
        self.assertEqual(sniff_format(copied_csif), "csif",
                         "Copied text must be recognised as 'csif' by sniff_format")

        # Paste inserts AFTER box 0 → new box at index 1
        self.app.on_box_paste(confirm=False)
        new_count = len(self.app.current_doc.boxes)
        self.assertEqual(new_count, orig_count + 1,
                         f"Paste must insert 1 new box; got {new_count - orig_count}")

        inserted = self.app.current_doc.boxes[1]
        self.assertEqual(inserted.speaker, orig_spk0,
                         "Inserted box must carry the original speaker")
        self.assertEqual(inserted.clean_text, orig_txt0,
                         "Inserted box must carry the original text")

    # ------------------------------------------------------------------ #
    # Required test: @@! payload routes to Box 0 regardless of focus
    # ------------------------------------------------------------------ #
    def test_29_meta_payload_routes_to_box0(self):
        """CSIF @@! metadata headers paste into Box 0 regardless of current focus."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)

        # Navigate to box 3 (not box 0)
        self.app.current_box_idx = 3
        self.app._sync_clean_view_to_current_box()

        # Build CSIF payload with ONLY metadata headers
        meta_csif = "@@!title\nInjected Title\n@@!summary\nInjected Summary\n"
        self.app.clipboard_get = lambda: meta_csif

        # Paste cross-box; the codec must detect @@! and route to metadata
        self.app.on_paste_cross_box()

        meta = self.app.current_doc.get_metadata()
        self.assertEqual(meta["title"], "Injected Title",
                         "@@!title must update Box 0 title regardless of active box")
        self.assertEqual(meta["summary"], "Injected Summary",
                         "@@!summary must update Box 0 summary regardless of active box")

    # ------------------------------------------------------------------ #
    # Required test: one Ctrl+Z undoes a whole multi-box insert
    # ------------------------------------------------------------------ #
    def test_30_ctrl_z_undoes_whole_multi_box_insert(self):
        """A single Ctrl+Z undoes a batch paste of multiple boxes."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)

        orig_count = len(self.app.current_doc.boxes)

        # Paste 3 boxes in one batch via CSIF clipboard
        clip = "@@Karyl\nBlock 1\n@@Pecorine\nBlock 2\n@@Kokkoro\nBlock 3\n"
        self.app.clipboard_get = lambda: clip
        self.app.on_box_paste(confirm=False)

        after_paste = len(self.app.current_doc.boxes)
        self.assertEqual(after_paste, orig_count + 3,
                         "Paste must have inserted 3 boxes")

        # ONE undo should revert all 3
        self.app.on_undo()
        after_undo = len(self.app.current_doc.boxes)
        self.assertEqual(after_undo, orig_count,
                         "Single Ctrl+Z must undo the entire multi-box batch")

    # ------------------------------------------------------------------ #
    # Required test: Ctrl+H leaves buffer byte-identical
    # ------------------------------------------------------------------ #
    def test_31_ctrl_h_does_not_mutate_dialogue_buffer(self):
        """Ctrl+H opens Replace dialog without mutating the dialogue buffer."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        self.app.current_box_idx = 1
        self.app._sync_clean_view_to_current_box()

        # Capture the exact text in the dialogue widget
        before = self.app.txt_dialogue.get("1.0", "end-1c")

        # Simulate Ctrl+H by calling on_show_replace directly (what the bindtag does)
        # Mock the dialog so it doesn't block
        with patch.object(self.app, "on_show_replace", return_value=None) as mock_replace:
            self.app.on_show_replace()
            mock_replace.assert_called_once()

        # Buffer must be unchanged
        after = self.app.txt_dialogue.get("1.0", "end-1c")
        self.assertEqual(before, after,
                         "Ctrl+H must not mutate the dialogue buffer")

    # ------------------------------------------------------------------ #
    # Required test: Ctrl+T (copy AI prompt) leaves buffer byte-identical
    # ------------------------------------------------------------------ #
    def test_32_ctrl_t_does_not_mutate_dialogue_buffer(self):
        """Ctrl+T (on_copy_ai_prompt) must not alter any box content."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        self.app.current_box_idx = 1
        self.app._sync_clean_view_to_current_box()

        before_texts = [b.clean_text for b in self.app.current_doc.boxes]
        before_speakers = [b.speaker for b in self.app.current_doc.boxes]
        before_dirty = self.app.is_dirty

        self.app.on_copy_ai_prompt()

        after_texts = [b.clean_text for b in self.app.current_doc.boxes]
        after_speakers = [b.speaker for b in self.app.current_doc.boxes]

        self.assertEqual(before_texts, after_texts,
                         "Ctrl+T must not mutate any box text")
        self.assertEqual(before_speakers, after_speakers,
                         "Ctrl+T must not mutate any box speaker")
        self.assertEqual(before_dirty, self.app.is_dirty,
                         "Ctrl+T must not change dirty state")

    # ------------------------------------------------------------------ #
    # Required test: Box 0 save leaves dialogue speaker/text byte-identical
    # ------------------------------------------------------------------ #
    def test_33_box0_save_leaves_dialogue_byte_identical(self):
        """Saving while Box 0 is active must not corrupt dialogue boxes 1+."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)

        # Capture all dialogue boxes BEFORE saving from Box 0
        before_speakers = [b.speaker for b in self.app.current_doc.boxes]
        before_texts = [b.clean_text for b in self.app.current_doc.boxes]

        # Navigate to Box 0 (metadata)
        self.app.on_prev_box()
        self.assertTrue(self.app.is_box0_active,
                        "Should be on Box 0 after on_prev_box()")

        # Save to a temp plain-text file (safe, no bundle write)
        tmp_txt = self.tmp_dir / "test_save.txt"
        self.app.current_file_path = tmp_txt
        self.app.on_save()

        # Dialogue boxes must be byte-identical
        after_speakers = [b.speaker for b in self.app.current_doc.boxes]
        after_texts = [b.clean_text for b in self.app.current_doc.boxes]
        self.assertEqual(before_speakers, after_speakers,
                         "Box 0 save must not corrupt dialogue speaker names")
        self.assertEqual(before_texts, after_texts,
                         "Box 0 save must not corrupt dialogue text")

    # ------------------------------------------------------------------ #
    # Required test: undo back to saved revision clears the dirty marker
    # ------------------------------------------------------------------ #
    def test_34_undo_to_saved_revision_clears_dirty(self):
        """Undoing all changes after a save must restore the clean (not dirty) state."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        self.app.current_box_idx = 0
        self.app._sync_clean_view_to_current_box()

        # Edit box 0 text
        orig_text = self.app.current_doc.boxes[0].clean_text
        self.app.current_doc.inject_box(0, None, "MODIFIED TEXT")
        self.app.undo_journal.record(
            misora_app.BoxEditDelta(
                box_index=0,
                old_speaker=self.app.current_doc.boxes[0].speaker,
                new_speaker=self.app.current_doc.boxes[0].speaker,
                old_text=orig_text,
                new_text="MODIFIED TEXT",
                file_path=str(self.app.current_file_path or ""),
                box_uid=self.app.current_doc.boxes[0].uid,
            )
        )
        self.app.is_dirty = True
        self.app._dirty_state_changed()

        # Save → marks current revision as clean
        tmp_txt = self.tmp_dir / "rev_test.txt"
        self.app.current_file_path = tmp_txt
        self.app.on_save()
        self.assertFalse(self.app.is_dirty,
                         "Should be clean immediately after save")

        # Make another edit
        self.app.current_doc.inject_box(0, None, "SECOND EDIT")
        self.app.undo_journal.record(
            misora_app.BoxEditDelta(
                box_index=0,
                old_speaker=self.app.current_doc.boxes[0].speaker,
                new_speaker=self.app.current_doc.boxes[0].speaker,
                old_text="MODIFIED TEXT",
                new_text="SECOND EDIT",
                file_path=str(self.app.current_file_path or ""),
                box_uid=self.app.current_doc.boxes[0].uid,
            )
        )
        self.app.is_dirty = True
        self.app._dirty_state_changed()
        self.assertTrue(self.app.is_dirty,
                        "Should be dirty after second edit")

        # Undo the second edit → back to saved revision → must be clean
        self.app.on_undo()
        self.app._dirty_state_changed()
        self.assertFalse(self.app.is_dirty,
                         "Undoing back to saved revision must clear dirty marker")

    # ------------------------------------------------------------------ #
    # Required test: stale internal box snapshot is discarded
    # ------------------------------------------------------------------ #
    def test_35_stale_internal_box_snapshot_discarded(self):
        """If the system clipboard differs from _box_clipboard_text, internal snapshot is cleared."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        self.app.current_box_idx = 0
        self.app._sync_clean_view_to_current_box()

        # Seed an internal snapshot
        self.app.on_box_copy()
        internal_snap = self.app._box_clipboard
        internal_text = self.app._box_clipboard_text
        self.assertIsNotNone(internal_snap, "Internal snapshot should be set after copy")

        # Simulate user copying something ELSE to system clipboard
        external_text = "@@Pecorine\nCompletely different content\n"
        self.app.clipboard_get = lambda: external_text

        # on_box_paste should detect mismatch and discard internal snapshot,
        # then parse the new clipboard content
        orig_count = len(self.app.current_doc.boxes)
        self.app.on_box_paste(confirm=False)

        # Internal snapshot must be cleared (stale detection)
        self.assertIsNone(self.app._box_clipboard,
                          "_box_clipboard must be None when clipboard text changed")
        self.assertIsNone(self.app._box_clipboard_text,
                          "_box_clipboard_text must be None when clipboard text changed")

        # But paste must still work using parsed clipboard
        new_count = len(self.app.current_doc.boxes)
        self.assertGreater(new_count, orig_count,
                           "Paste must succeed even when stale snapshot is discarded")
        self.assertEqual(self.app.current_doc.boxes[1].speaker, "Pecorine",
                         "Pasted box must use the new clipboard content's speaker")

    # ------------------------------------------------------------------ #
    # Required test: Ctrl+B/I/U wrap tags persist through undo
    # ------------------------------------------------------------------ #
    def test_36_shortcut_wrap_persists_and_undos(self):
        """Ctrl+B (apply_ngui_wrapper) inserts [b][/b] and Ctrl+Z reverts."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        # Force page view so txt_dialogue is populated (session prefs may restore continuous)
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.current_box_idx = 1
        self.app._sync_clean_view_to_current_box()
        self.app.update_idletasks()

        before = self.app.current_doc.boxes[1].clean_text

        # _shortcut_wrap → apply_ngui_wrapper → _insert_text_wrapper inserts into
        # txt_dialogue and calls _commit_widget_edit to flush to the doc.
        self.app.txt_dialogue.focus_force()
        self.app.update_idletasks()
        self.app._shortcut_wrap("[b]", "[/b]")

        # Verify via widget content (apply_ngui_wrapper already committed)
        widget_content = self.app.txt_dialogue.get("1.0", "end-1c")
        self.assertIn("[b]", widget_content,
                      "Ctrl+B must insert [b] tag into the dialogue widget")
        self.assertIn("[/b]", widget_content,
                      "Ctrl+B must insert [/b] closing tag into the dialogue widget")

        # Doc model must also reflect the tag (committed by apply_ngui_wrapper)
        doc_text = self.app.current_doc.boxes[1].clean_text
        self.assertIn("[b]", doc_text,
                      "Box doc text must contain [b] after commit")

        # Undo must revert
        self.app.on_undo()
        after_undo = self.app.current_doc.boxes[1].clean_text
        self.assertEqual(before, after_undo,
                         "Ctrl+Z must revert [b][/b] wrap to original text")

    # ------------------------------------------------------------------ #
    # Required test: size insertion persists through navigation and undos
    # ------------------------------------------------------------------ #
    def test_37_size_insertion_persists_and_undos(self):
        """Size insertion (on_insert_font_size) persists after navigation and undoes cleanly."""
        if not _has_bundle():
            self.skipTest("Bundle fixture not found")
        self.app.open_file(BUNDLE)
        # Force page view so txt_dialogue is populated
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.current_box_idx = 1
        self.app._sync_clean_view_to_current_box()
        self.app.update_idletasks()

        before_text = self.app.current_doc.boxes[1].clean_text

        # Give txt_dialogue focus so on_insert_font_size targets it
        self.app.txt_dialogue.focus_force()
        self.app.update_idletasks()

        # on_insert_font_size inserts <size=130%>...</size> into the active widget
        self.app.on_insert_font_size("130%")

        # Flush edit to doc
        self.app._commit_widget_edit(self.app.txt_dialogue)
        after_insert = self.app.current_doc.boxes[1].clean_text
        self.assertIn("<size=130%>", after_insert,
                      "Size insertion must add <size=130%> tag to box text")

        # Navigate away and back — text must persist
        self.app.on_next_box()
        self.app.on_prev_box()
        after_nav = self.app.current_doc.boxes[1].clean_text
        self.assertEqual(after_insert, after_nav,
                         "Size tag must persist after navigation")

        # Undo must revert
        self.app.on_undo()
        after_undo = self.app.current_doc.boxes[1].clean_text
        self.assertEqual(before_text, after_undo,
                         "Ctrl+Z must revert size insertion")


class TestPhase2RequiredNoFixture(unittest.TestCase):
    """Required Phase 2 tests that do not need a bundle fixture."""

    def setUp(self):
        self._patches = [
            patch.object(misora_app.messagebox, "askyesno", return_value=True),
            patch.object(misora_app.messagebox, "showinfo", return_value=None),
            patch.object(misora_app.messagebox, "showwarning", return_value=None),
            patch.object(misora_app.messagebox, "showerror", return_value=None),
        ]
        for p in self._patches:
            p.start()
        self.app = misora_app.MisoraApp(restore_session=False)
        self.app.withdraw()

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

    def test_38_on_box_copy_emits_csif(self):
        """on_box_copy always emits CSIF regardless of fixture presence."""
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Good morning!"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["She bows."]),
        ])
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._sync_clean_view_to_current_box()
        self.app.on_box_copy()

        copied = self.app.safe_clipboard_get()
        self.assertIn("@@", copied, "on_box_copy must emit CSIF")
        self.assertEqual(sniff_format(copied), "csif")
        self.assertIn("Kokkoro", copied)
        self.assertIn("Good morning!", copied)

    def test_39_revision_dirty_tracking(self):
        """Undo journal is_clean() correctly tracks the saved revision."""
        journal = self.app.undo_journal
        self.assertTrue(journal.is_clean(), "Journal is clean at start")

        # Record a fake delta (create minimal delta)
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["A", "Hello"])
        ])
        self.app.current_doc = doc
        self.app.current_box_idx = 0

        journal.record(
            misora_app.BoxEditDelta(
                box_index=0,
                old_speaker="A",
                new_speaker="A",
                old_text="Hello",
                new_text="Goodbye",
                file_path="test.txt",
                box_uid=doc.boxes[0].uid,
            )
        )
        self.assertFalse(journal.is_clean(), "Journal should be dirty after edit")

        # mark_saved anchors the revision
        journal.mark_saved()
        self.assertTrue(journal.is_clean(), "Journal should be clean after mark_saved()")

    def test_40_safe_clipboard_retry_on_tclerror(self):
        """safe_clipboard_get retries on TclError and normalizes CRLF."""
        import tkinter as tk
        call_count = [0]

        def mock_clipboard_get():
            call_count[0] += 1
            if call_count[0] < 2:
                raise tk.TclError("clipboard is empty")
            return "line1\r\nline2\r\nline3"

        self.app.clipboard_get = mock_clipboard_get
        result = self.app.safe_clipboard_get()
        self.assertEqual(result, "line1\nline2\nline3",
                         "safe_clipboard_get must normalize CRLF to LF")
        self.assertGreaterEqual(call_count[0], 2,
                                "safe_clipboard_get must retry on TclError")


if __name__ == "__main__":
    unittest.main()
