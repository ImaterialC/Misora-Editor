#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s3_document_close.py — Failing-first TDD suite for S3.

S3: Safe Document Close & Atomic Persistence in Misora Editor.
- write_atomic_utf8() helper with atomic replacement & cleanup
- on_save() atomic write integration (plain-text & v2)
- close_file(file_path) -> bool with abort on save-fail, checkpoint cleanup, and flush
- _on_app_exit() per-file Save-All loop with cancel/save-fail abort
- close_all_files() / close_others() cancellation handling
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

spec = importlib.util.spec_from_file_location("misora_s3", MISORA_DIR / "misora.py")
misora = importlib.util.module_from_spec(spec)
sys.modules["misora_s3"] = misora
spec.loader.exec_module(misora)


class TestS3DocumentClose(unittest.TestCase):
    """S3: Safe Document Close & Atomic Persistence test suite."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s3_"))
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

    def _make_txt(self, name="doc.txt", content="Hello World"):
        p = self.tmp_dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_01_close_clean_file_no_prompt(self):
        """Closing a clean doc removes it from open_documents without prompt, returns True."""
        p = self._make_txt("clean.txt", "clean content")
        self.app.open_file(p)
        self.assertIn(p.resolve(), self.app.open_documents)

        with patch.object(misora.messagebox, "askyesnocancel") as mock_ask:
            res = self.app.close_file(p)
            mock_ask.assert_not_called()

        self.assertTrue(res)
        self.assertNotIn(p.resolve(), self.app.open_documents)

    def test_02_close_dirty_save_chosen_succeeds(self):
        """Close with Save chosen and on_save() succeeds -> returns True, doc removed, disk updated."""
        p = self._make_txt("dirty.txt", "orig")
        self.app.open_file(p)
        # Mutate dialogue
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "modified text")
        self.app._commit_widget_edit(self.app.txt_dialogue)
        self.assertTrue(self.app.open_documents[p.resolve()]["dirty"])

        with patch.object(misora.messagebox, "askyesnocancel", return_value=True):
            res = self.app.close_file(p)

        self.assertTrue(res)
        self.assertNotIn(p.resolve(), self.app.open_documents)
        self.assertEqual(p.read_text(encoding="utf-8"), "modified text")

    def test_03_close_dirty_save_chosen_fails(self):
        """Close with Save chosen but on_save() returns False -> returns False, doc retained."""
        p = self._make_txt("dirty_fail.txt", "orig")
        self.app.open_file(p)
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "modified text")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=True):
            with patch.object(self.app, "on_save", return_value=False):
                res = self.app.close_file(p)

        self.assertFalse(res)
        self.assertIn(p.resolve(), self.app.open_documents)

    def test_04_close_dirty_discard_chosen(self):
        """Close with Discard (False) -> returns True, doc removed, disk NOT overwritten."""
        p = self._make_txt("discard.txt", "orig")
        self.app.open_file(p)
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "unsaved text")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=False):
            res = self.app.close_file(p)

        self.assertTrue(res)
        self.assertNotIn(p.resolve(), self.app.open_documents)
        self.assertEqual(p.read_text(encoding="utf-8"), "orig")

    def test_05_close_dirty_cancel_chosen(self):
        """Close with Cancel (None) -> returns False, doc still in open_documents."""
        p = self._make_txt("cancel.txt", "orig")
        self.app.open_file(p)
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "cancel text")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=None):
            res = self.app.close_file(p)

        self.assertFalse(res)
        self.assertIn(p.resolve(), self.app.open_documents)

    def test_06_checkpoint_pruned_on_close(self):
        """_saved_state_checkpoints entry is removed on successful close."""
        p = self._make_txt("checkpoint.txt", "content")
        self.app.open_file(p)
        key = str(p.resolve())
        self.assertIn(key, self.app._saved_state_checkpoints)

        res = self.app.close_file(p)
        self.assertTrue(res)
        self.assertNotIn(key, self.app._saved_state_checkpoints)

    def test_07_app_exit_all_clean_no_prompts(self):
        """Exit with all clean docs -> no prompts, destroy() is called."""
        p = self._make_txt("clean1.txt", "c1")
        self.app.open_file(p)

        with patch.object(misora.messagebox, "askyesnocancel") as mock_ask:
            with patch.object(self.app, "destroy") as mock_destroy:
                self.app._on_app_exit()
                mock_ask.assert_not_called()
                mock_destroy.assert_called_once()

    def test_08_app_exit_saves_dirty_doc_on_save(self):
        """Exit with dirty doc, Save chosen -> on_save() called, destroy() called."""
        p = self._make_txt("exit_save.txt", "c1")
        self.app.open_file(p)
        self.app.txt_dialogue.insert("1.0", "edit ")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=True):
            with patch.object(self.app, "on_save", wraps=self.app.on_save) as spy_save:
                with patch.object(self.app, "destroy") as mock_destroy:
                    self.app._on_app_exit()
                    spy_save.assert_called()
                    mock_destroy.assert_called_once()

    def test_09_app_exit_cancel_aborts_exit(self):
        """Exit with dirty doc, Cancel chosen -> destroy() NOT called."""
        p = self._make_txt("exit_cancel.txt", "c1")
        self.app.open_file(p)
        self.app.txt_dialogue.insert("1.0", "edit ")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=None):
            with patch.object(self.app, "destroy") as mock_destroy:
                self.app._on_app_exit()
                mock_destroy.assert_not_called()

    def test_10_app_exit_discard_allows_exit(self):
        """Exit with dirty doc, Discard chosen -> destroy() called, on_save NOT called."""
        p = self._make_txt("exit_discard.txt", "c1")
        self.app.open_file(p)
        self.app.txt_dialogue.insert("1.0", "edit ")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=False):
            with patch.object(self.app, "on_save") as mock_save:
                with patch.object(self.app, "destroy") as mock_destroy:
                    self.app._on_app_exit()
                    mock_save.assert_not_called()
                    mock_destroy.assert_called_once()

    def test_11_app_exit_save_fail_aborts_exit(self):
        """Exit with dirty doc, Save chosen but fails -> destroy() NOT called."""
        p = self._make_txt("exit_save_fail.txt", "c1")
        self.app.open_file(p)
        self.app.txt_dialogue.insert("1.0", "edit ")
        self.app._commit_widget_edit(self.app.txt_dialogue)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=True):
            with patch.object(self.app, "on_save", return_value=False):
                with patch.object(self.app, "destroy") as mock_destroy:
                    self.app._on_app_exit()
                    mock_destroy.assert_not_called()

    def test_12_atomic_write_no_tmp_left(self):
        """write_atomic_utf8 writes content cleanly and removes .tmp file."""
        target = self.tmp_dir / "atomic_clean.txt"
        misora.write_atomic_utf8(target, "atomic content")
        self.assertTrue(target.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "atomic content")
        tmp_files = list(self.tmp_dir.glob("atomic_clean.txt*.tmp"))
        self.assertEqual(len(tmp_files), 0)

    def test_13_atomic_write_failure_leaves_original(self):
        """Simulated write failure leaves original file unchanged."""
        target = self.tmp_dir / "atomic_orig.txt"
        target.write_text("original preserved", encoding="utf-8")

        with patch("os.replace", side_effect=OSError("Permission denied")):
            with self.assertRaises(OSError):
                misora.write_atomic_utf8(target, "new corrupted data")

        self.assertEqual(target.read_text(encoding="utf-8"), "original preserved")

    def test_14_close_all_files_stops_on_cancel(self):
        """close_all_files() stops iterating if close_file returns False."""
        p1 = self._make_txt("all1.txt", "c1")
        p2 = self._make_txt("all2.txt", "c2")
        self.app.open_file(p1)
        self.app.open_file(p2)
        # Mark p1 and p2 dirty
        self.app._mark_document_dirty(p1)
        self.app._mark_document_dirty(p2)

        # Cancel on first prompt
        with patch.object(misora.messagebox, "askyesnocancel", return_value=None) as mock_ask:
            self.app.close_all_files()
            # Should have stopped after first cancel, so p2 was not prompted or closed
            self.assertEqual(mock_ask.call_count, 1)

        self.assertIn(p1.resolve(), self.app.open_documents)
        self.assertIn(p2.resolve(), self.app.open_documents)

    def test_15_app_exit_multiple_dirty_files_saved(self):
        """Exit with multiple dirty docs, user chooses Save for each -> all are saved and app exits."""
        p1 = self._make_txt("multi1.txt", "orig1")
        p2 = self._make_txt("multi2.txt", "orig2")
        self.app.open_file(p1)
        self.app.open_file(p2)
        # Modify both
        self.app.open_documents[p1.resolve()]["plain_text"] = "saved1"
        self.app._mark_document_dirty(p1)
        self.app.open_documents[p2.resolve()]["plain_text"] = "saved2"
        self.app._mark_document_dirty(p2)

        with patch.object(misora.messagebox, "askyesnocancel", return_value=True) as mock_ask:
            with patch.object(self.app, "destroy") as mock_destroy:
                self.app._on_app_exit()
                self.assertEqual(mock_ask.call_count, 2)
                mock_destroy.assert_called_once()

    def test_16_app_exit_multi_file_cancel_aborts(self):
        """Exit with multiple dirty docs, user cancels on second -> exit aborted, app not destroyed."""
        p1 = self._make_txt("cancel1.txt", "orig1")
        p2 = self._make_txt("cancel2.txt", "orig2")
        self.app.open_file(p1)
        self.app.open_file(p2)
        self.app._mark_document_dirty(p1)
        self.app._mark_document_dirty(p2)

        # First prompt True (Save), second prompt None (Cancel)
        with patch.object(misora.messagebox, "askyesnocancel", side_effect=[True, None]):
            with patch.object(self.app, "destroy") as mock_destroy:
                self.app._on_app_exit()
                mock_destroy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
