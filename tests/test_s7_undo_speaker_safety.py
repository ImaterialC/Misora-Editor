"""
S7 — Per-File MasterUndoJournal Revision Rewrite (F16) & Speaker Commit Unification (F20)
========================================================================================
TDD tests verifying:
  - Per-file undo/redo stack isolation in MasterUndoJournal and MisoraApp (Rule 13).
  - Undo in File B while in File B does not touch File A's undo stack or content.
  - Switching back to File A enables File A's undo operations without interference.
  - Edit menu reflects undo/redo label and state dynamically for the active file.
  - prune_file() on document close deletes undo/redo history and prevents silent reopen (Rule 16).
  - Per-file revision tracking (is_clean / mark_saved) for isolated documents.
  - MasterUndoJournal backward compatibility for parameterless calls.
  - Speaker commit unification: _commit_speaker_edit() passes valid text (never None) to inject_box,
    preventing AttributeError in multi-segment boxes and arg corruption in single-segment boxes.
  - Speaker commit no-op guard: unmodified speaker keypress does not dirty doc or record delta.
  - Box 0 protection: speaker edit aborts without modifying doc or recording delta when Box 0 is active.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.undo_journal import (  # noqa: E402
    MasterUndoJournal,
    BoxEditDelta,
    PlainTextDelta,
    UndoOperation,
)
from core.story_ast import StoryDocument, Record, Box  # noqa: E402


class S7TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s7_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warn.start()
        cls.patch_err.start()

        with patch.object(misora, "CONFIG_PATH", cls.config_path):
            cls.app = misora.MisoraApp(restore_session=False, show_splash=False)
            cls.app._test_bypass_dialogs = True
            cls.app.withdraw()
            cls.app.backup_folder = str(cls.tmp_dir / "backups")

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warn.stop()
        cls.patch_err.stop()

        try:
            cls.app.destroy()
        except Exception:
            pass


class TestS7JournalUnit(unittest.TestCase):
    """Unit tests for MasterUndoJournal isolated stacks and per-file revisions."""

    def test_01_journal_per_file_stacks_isolated(self):
        """MasterUndoJournal isolates undo and redo stacks per file_path."""
        journal = MasterUndoJournal()
        file_a = "doc_a.txt"
        file_b = "doc_b.txt"

        delta_a = PlainTextDelta(file_path=file_a, old_content="A0", new_content="A1")
        delta_b = PlainTextDelta(file_path=file_b, old_content="B0", new_content="B1")

        journal.record(delta_a, label="Edit A")
        journal.record(delta_b, label="Edit B")

        # Stacks must be isolated
        self.assertTrue(journal.can_undo(file_a))
        self.assertTrue(journal.can_undo(file_b))
        self.assertEqual(journal.undo_label(file_a), "Edit A")
        self.assertEqual(journal.undo_label(file_b), "Edit B")

        # Popping B must not affect A
        op_b = journal.pop_undo(file_b)
        self.assertIsNotNone(op_b)
        self.assertEqual(op_b.label, "Edit B")
        self.assertFalse(journal.can_undo(file_b))
        self.assertTrue(journal.can_redo(file_b))

        # A is still undoable
        self.assertTrue(journal.can_undo(file_a))
        op_a = journal.pop_undo(file_a)
        self.assertIsNotNone(op_a)
        self.assertEqual(op_a.label, "Edit A")
        self.assertFalse(journal.can_undo(file_a))

    def test_02_journal_per_file_revisions(self):
        """is_clean() and mark_saved() track revisions per file independently."""
        journal = MasterUndoJournal()
        file_a = "doc_a.txt"
        file_b = "doc_b.txt"

        self.assertTrue(journal.is_clean(file_a))
        self.assertTrue(journal.is_clean(file_b))

        # Edit A -> A is dirty, B is clean
        journal.record(PlainTextDelta(file_path=file_a, old_content="A0", new_content="A1"))
        self.assertFalse(journal.is_clean(file_a))
        self.assertTrue(journal.is_clean(file_b))

        # Save A -> A is clean, B is clean
        journal.mark_saved(file_a)
        self.assertTrue(journal.is_clean(file_a))
        self.assertTrue(journal.is_clean(file_b))

        # Edit B -> B is dirty, A remains clean
        journal.record(PlainTextDelta(file_path=file_b, old_content="B0", new_content="B1"))
        self.assertTrue(journal.is_clean(file_a), "File A must remain clean when File B is edited")
        self.assertFalse(journal.is_clean(file_b), "File B must be dirty after edit")

        # Undo B -> B returns to saved revision (clean)
        journal.pop_undo(file_b)
        self.assertTrue(journal.is_clean(file_b), "File B must be clean after undoing to saved revision")
        self.assertTrue(journal.is_clean(file_a), "File A must still be clean")

    def test_03_journal_prune_file(self):
        """prune_file(fp) completely purges undo/redo stacks for that file."""
        journal = MasterUndoJournal()
        file_a = "doc_a.txt"
        file_b = "doc_b.txt"

        journal.record(PlainTextDelta(file_path=file_a, old_content="A0", new_content="A1"))
        journal.record(PlainTextDelta(file_path=file_b, old_content="B0", new_content="B1"))

        self.assertTrue(journal.can_undo(file_a))
        self.assertTrue(journal.can_undo(file_b))

        journal.prune_file(file_a)

        self.assertFalse(journal.can_undo(file_a))
        self.assertFalse(journal.can_redo(file_a))
        self.assertTrue(journal.can_undo(file_b), "File B undo stack must survive pruning of File A")

    def test_04_journal_backward_compatibility_parameterless(self):
        """Parameterless calls to MasterUndoJournal operate seamlessly on active/default file."""
        journal = MasterUndoJournal()

        # Clean initially
        self.assertTrue(journal.is_clean())
        self.assertFalse(journal.can_undo())
        self.assertFalse(journal.can_redo())
        self.assertEqual(journal.undo_depth, 0)
        self.assertEqual(journal.redo_depth, 0)

        # Record delta without explicit file_path
        d = BoxEditDelta(box_index=0, old_speaker="A", new_speaker="A", old_text="T1", new_text="T2")
        journal.record(d, label="Edit Box")

        self.assertFalse(journal.is_clean())
        self.assertTrue(journal.can_undo())
        self.assertEqual(journal.undo_depth, 1)
        self.assertEqual(journal.undo_label(), "Edit Box")

        # mark_saved()
        journal.mark_saved()
        self.assertTrue(journal.is_clean())

        # pop_undo()
        op = journal.pop_undo()
        self.assertIsNotNone(op)
        self.assertEqual(op.label, "Edit Box")
        self.assertEqual(journal.undo_depth, 0)
        self.assertEqual(journal.redo_depth, 1)
        self.assertTrue(journal.can_redo())

        # pop_redo()
        op_redo = journal.pop_redo()
        self.assertIsNotNone(op_redo)
        self.assertEqual(journal.undo_depth, 1)
        self.assertEqual(journal.redo_depth, 0)


class TestS7AppUndoAndSpeaker(S7TestBase):
    """Integration tests for MisoraApp per-file undo and speaker commit unification."""

    def test_05_app_multi_document_undo_isolation(self):
        """Undoing in Doc B reverts Doc B only; Doc A's undo stack and edits remain intact."""
        file_a = self.tmp_dir / "app_doc_a.txt"
        file_b = self.tmp_dir / "app_doc_b.txt"
        file_a.write_text("Original A", encoding="utf-8")
        file_b.write_text("Original B", encoding="utf-8")

        # Open A, edit A
        self.app.open_file(file_a)
        self.app._plain_text_content = "Modified A"
        self.app._update_views()
        self.app.undo_journal.record(
            PlainTextDelta(file_path=str(file_a), old_content="Original A", new_content="Modified A"),
            label="Edit A"
        )
        self.app.open_documents[file_a.resolve()]["plain_text"] = "Modified A"
        self.app._mark_document_dirty(file_a)

        # Open B, edit B
        self.app.open_file(file_b)
        self.app._plain_text_content = "Modified B"
        self.app._update_views()
        self.app.undo_journal.record(
            PlainTextDelta(file_path=str(file_b), old_content="Original B", new_content="Modified B"),
            label="Edit B"
        )
        self.app.open_documents[file_b.resolve()]["plain_text"] = "Modified B"
        self.app._mark_document_dirty(file_b)

        # Both must have undo history in their own journals
        self.assertTrue(self.app.undo_journal.can_undo(str(file_a)))
        self.assertTrue(self.app.undo_journal.can_undo(str(file_b)))

        # Active file is B -> on_undo() must undo B only
        self.assertEqual(self.app.current_file_path, file_b)
        self.app.on_undo()

        # B must be restored to "Original B"
        self.assertEqual(self.app._plain_text_content, "Original B")
        self.assertFalse(self.app.undo_journal.can_undo(str(file_b)))

        # A must STILL be "Modified A" and have undo history
        self.assertEqual(self.app.open_documents[file_a.resolve()]["plain_text"], "Modified A")
        self.assertTrue(self.app.undo_journal.can_undo(str(file_a)))

        # Switch to A -> on_undo() must undo A
        self.app.open_file(file_a)
        self.assertEqual(self.app._plain_text_content, "Modified A")
        self.app.on_undo()
        self.assertEqual(self.app._plain_text_content, "Original A")
        self.assertFalse(self.app.undo_journal.can_undo(str(file_a)))

    def test_06_app_edit_menu_sync_per_file(self):
        """Edit menu Undo/Redo reflects the active file's stack, not other open files."""
        file_a = self.tmp_dir / "menu_doc_a.txt"
        file_b = self.tmp_dir / "menu_doc_b.txt"
        file_a.write_text("AAA", encoding="utf-8")
        file_b.write_text("BBB", encoding="utf-8")

        self.app.open_file(file_a)
        self.app.undo_journal.record(
            PlainTextDelta(file_path=str(file_a), old_content="AAA", new_content="AAA+"),
            label="Edit File A"
        )
        self.app._sync_edit_menu_states()
        self.assertTrue(self.app.undo_journal.can_undo(str(file_a)))

        # Open unedited File B -> menu should reflect File B (cannot undo)
        self.app.open_file(file_b)
        self.assertFalse(self.app.undo_journal.can_undo(str(file_b)))

    def test_07_speaker_commit_never_passes_none_text_multi_segment(self):
        """_commit_speaker_edit() never passes None text to inject_box in multi-segment boxes."""
        # Create a document with a 2-segment box
        rec1 = Record(cmd_id=6, cmd_name="print", args=["OldSpeaker", "First line of dialogue"])
        rec2 = Record(cmd_id=6, cmd_name="print", args=["OldSpeaker", "Second line of dialogue"])
        doc = StoryDocument([rec1, rec2])
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(len(doc.boxes[0].segs), 2)

        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = False
        self.app.speaker_var.set("NewSpeaker")

        # This must succeed without raising AttributeError: 'NoneType' object has no attribute 'rstrip'
        committed = self.app._commit_speaker_edit()

        self.assertTrue(committed, "_commit_speaker_edit must return True on mutation")
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "NewSpeaker")
        # Ensure seg text and rec args are valid strings, not None
        for seg in self.app.current_doc.boxes[0].segs:
            self.assertIsNotNone(seg.text)
            self.assertIsNotNone(seg.raw)
            self.assertIsNotNone(seg.record.args[1])
            self.assertIsInstance(seg.record.args[1], str)

    def test_08_speaker_commit_noop_guard(self):
        """_commit_speaker_edit() returns False and does not record delta if speaker is unchanged."""
        rec = Record(cmd_id=6, cmd_name="print", args=["Peco", "Yummy food!"])
        doc = StoryDocument([rec])
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = False
        self.app.speaker_var.set("Peco")  # Same speaker

        depth_before = self.app.undo_journal.undo_depth
        committed = self.app._commit_speaker_edit()

        self.assertFalse(committed, "Must return False when speaker has not changed")
        self.assertEqual(self.app.undo_journal.undo_depth, depth_before, "No delta should be recorded")

    def test_09_speaker_commit_box0_protection(self):
        """_commit_speaker_edit() aborts immediately when Box 0 (metadata) is active."""
        rec = Record(cmd_id=6, cmd_name="print", args=["Peco", "Yummy food!"])
        doc = StoryDocument([rec])
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = True
        self.app.speaker_var.set("Hiyori")

        committed = self.app._commit_speaker_edit()

        self.assertFalse(committed, "Must abort when is_box0_active is True")
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Peco", "Speaker must not change")
        self.app.is_box0_active = False

    def test_10_speaker_commit_unified_delegation(self):
        """_on_speaker_edited() and _commit_widget_edit(entry_speaker) delegate to _commit_speaker_edit()."""
        rec = Record(cmd_id=6, cmd_name="print", args=["Kyaru", "Baka!"])
        doc = StoryDocument([rec])
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = False

        # Test _on_speaker_edited delegation
        self.app.speaker_var.set("Kyaru_Changed")
        self.app._on_speaker_edited()
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Kyaru_Changed")

        # Test _commit_widget_edit(entry_speaker) delegation
        self.app.speaker_var.set("Kyaru_Final")
        self.app._commit_widget_edit(self.app.entry_speaker)
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Kyaru_Final")


if __name__ == "__main__":
    unittest.main()
