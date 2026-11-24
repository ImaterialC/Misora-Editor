"""
S6 — Threading Architecture Decoupling (Rule 15)
=================================================
TDD tests verifying:
  - SEARCH-RACE: on_find_in_files() captures immutable StoryDocument snapshots on the UI thread
    before delegating to the background search thread; mutating the live document does not affect
    search snapshots.
  - Search worker thread always posts ("finished", ...) to search_queue in finally block.
  - BatchTranslateDialog worker thread NEVER mutates UndoJournal directly (mutations occur on main thread).
  - BatchTranslateDialog worker thread NEVER mutates StoryDocument directly (inject_box occurs on main thread).
  - Main thread polling loop applies queue messages, recording BoxEditDelta and injecting into doc.
  - Setting _cancelled = True terminates the worker loop and safely closes the undo batch.
  - Engine translation exceptions are posted to queue without crashing the worker or hanging poll loop.
  - Every begin_batch() in BatchTranslateDialog has a matching end_batch() on completion or cancellation.
"""

import sys
import os
import time
import queue
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.story_ast import StoryDocument, Record, Box  # noqa: E402
from core.search_engine import SearchOptions  # noqa: E402


class S6TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s6_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        # Mock out messageboxes
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
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _create_sample_doc(self, num_boxes=3) -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
        ]
        for i in range(num_boxes):
            recs.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker{i+1}", f"Original Box {i+1} テスト"]))
        return StoryDocument(recs)


# ===========================================================================
# Test Cases
# ===========================================================================

class TestS6SearchSnapshotDecoupling(S6TestBase):
    """Verify SEARCH-RACE resolution: search receives immutable snapshots, not live mutable doc."""

    def test_01_search_uses_immutable_document_snapshots(self):
        """on_find_in_files() snapshots in-memory StoryDocuments before thread start."""
        doc = self._create_sample_doc(2)
        fake_path = (self.tmp_dir / "story.unity3d").resolve()
        self.app.open_documents[fake_path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = fake_path
        self.app.current_doc = doc
        self.app.search_var.set("テスト")
        self.app.scope_var.set("current")

        captured_mem_docs = {}

        def spy_thread_target(paths, options, mem_docs=None):
            if mem_docs:
                captured_mem_docs.update(mem_docs)

        with patch.object(self.app, "_run_background_search", side_effect=spy_thread_target):
            self.app.on_start_search()

        self.assertIn(fake_path, captured_mem_docs, "Snapshotted docs must contain open document path")
        snap_doc = captured_mem_docs[fake_path]

        # Must NOT be the same object instance (must be cloned snapshot)
        self.assertIsNot(snap_doc, doc, "Search worker must receive a snapshot, not the live mutable document")

        # Mutating the live doc must not affect the snapshotted doc
        doc.inject_box(0, None, "MUTATED AFTER SNAPSHOT")
        self.assertIn("Original Box 1", snap_doc.boxes[0].clean_text)
        self.assertNotIn("MUTATED AFTER SNAPSHOT", snap_doc.boxes[0].clean_text)

    def test_02_search_queue_always_posts_finished_in_finally(self):
        """_run_background_search() always posts ('finished', ...) to search_queue."""
        opts = SearchOptions(query="test")
        non_existent = self.tmp_dir / "does_not_exist"

        # Drain any existing messages
        while not self.app.search_queue.empty():
            self.app.search_queue.get_nowait()

        # Run background search with non-existent path
        self.app._run_background_search([non_existent], opts, {})

        found_finished = False
        while not self.app.search_queue.empty():
            msg = self.app.search_queue.get_nowait()
            if msg[0] == "finished":
                found_finished = True
                break

        self.assertTrue(found_finished, "_run_background_search must post 'finished' in finally")


class TestS6BatchTranslateQueueDecoupling(S6TestBase):
    """Verify Rule 15: BatchTranslateDialog worker does NOT mutate doc or UndoJournal."""

    def test_03_batch_translate_worker_does_not_mutate_undo_journal(self):
        """Background worker thread must NEVER call undo_journal.record() or begin_batch()."""
        doc = self._create_sample_doc(2)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        undo_threads = []
        original_record = self.app.undo_journal.record

        def spy_record(delta, *args, **kwargs):
            undo_threads.append(threading.current_thread())
            return original_record(delta, *args, **kwargs)

        with patch.object(self.app.undo_journal, "record", side_effect=spy_record), \
             patch("misora.MTLEngine.translate", return_value="Translated text"):
            dlg._start_batch()
            # Wait for batch to complete (worker finishes and queue processes)
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

        dlg.destroy()

        self.assertTrue(len(undo_threads) > 0, "undo_journal.record must have been called")
        for th in undo_threads:
            self.assertEqual(
                th, threading.main_thread(),
                f"undo_journal.record must occur on main thread, but ran on {th}"
            )

    def test_04_batch_translate_worker_does_not_mutate_story_document(self):
        """Background worker thread must NEVER call doc.inject_box()."""
        doc = self._create_sample_doc(2)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        inject_threads = []
        original_inject = doc.inject_box

        def spy_inject(idx, spk, text, *args, **kwargs):
            inject_threads.append(threading.current_thread())
            return original_inject(idx, spk, text, *args, **kwargs)

        with patch.object(doc, "inject_box", side_effect=spy_inject), \
             patch("misora.MTLEngine.translate", return_value="Translated text"):
            dlg._start_batch()
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

        dlg.destroy()

        self.assertTrue(len(inject_threads) > 0, "doc.inject_box must have been called")
        for th in inject_threads:
            self.assertEqual(
                th, threading.main_thread(),
                f"doc.inject_box must occur on main thread, but ran on {th}"
            )

    def test_05_batch_translate_applies_edits_on_main_thread(self):
        """Batch translation applies translated text to doc.boxes and tracks modified boxes."""
        doc = self._create_sample_doc(2)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}
        self.app._modified_boxes.clear()

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        with patch("misora.MTLEngine.translate", return_value="English Dialogue"):
            dlg._start_batch()
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

        dlg.destroy()

        self.assertEqual(doc.boxes[0].clean_text, "English Dialogue")
        self.assertEqual(doc.boxes[1].clean_text, "English Dialogue")
        self.assertIn(0, self.app._modified_boxes)
        self.assertIn(1, self.app._modified_boxes)

    def test_06_batch_translate_cancellation_stops_worker_and_ends_batch(self):
        """Setting _cancelled = True stops worker loop and cleanly ends the undo batch."""
        doc = self._create_sample_doc(5)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.05)

        def slow_translate(text, *args, **kwargs):
            time.sleep(0.05)
            return f"Translated: {text}"

        with patch("misora.MTLEngine.translate", side_effect=slow_translate), \
             patch.object(self.app.undo_journal, "end_batch") as mock_end_batch:
            dlg._start_batch()
            time.sleep(0.02)
            dlg._cancelled = True

            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

            mock_end_batch.assert_called()

        dlg.destroy()

    def test_07_batch_translate_worker_handles_translation_exception(self):
        """Worker continues and batch completes even if one box raises translation exception."""
        doc = self._create_sample_doc(3)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        def flappy_translate(text, *args, **kwargs):
            if "Box 1" in text:
                raise RuntimeError("Simulated network timeout on Box 1")
            return f"Translated: {text}"

        with patch("misora.MTLEngine.translate", side_effect=flappy_translate):
            dlg._start_batch()
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

        dlg.destroy()

        # Box 1 failed -> remains original text
        self.assertIn("Original Box 1", doc.boxes[0].clean_text)
        # Box 2 and 3 succeeded -> translated
        self.assertIn("Translated: Original Box 2", doc.boxes[1].clean_text)
        self.assertIn("Translated: Original Box 3", doc.boxes[2].clean_text)

    def test_08_batch_translate_closes_batch_in_finally(self):
        """BatchTranslateDialog guarantees undo_journal.end_batch() is called on completion."""
        doc = self._create_sample_doc(2)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "story.unity3d"
        self.app.open_documents[self.app.current_file_path] = {"doc": doc, "plain_text": ""}

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        with patch.object(self.app.undo_journal, "end_batch") as mock_end_batch, \
             patch("misora.MTLEngine.translate", return_value="Done"):
            dlg._start_batch()
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)
            mock_end_batch.assert_called_once()

        dlg.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
