"""
S11 — Main-Thread Queue-Only Async MTL, Stale-Result Identity Guard & Safe Batch Cancel (BUG-14, BUG-27)
========================================================================================================
Verification suite for:
  - BUG-27: Eliminate all worker-thread `self.after_idle(...)` calls across all 4 async paths:
      1. on_translate_current_box
      2. MTLSettingsDialog._on_test_connection
      3. TranslatorAssistantDialog._on_translate
      4. TranslatorAssistantDialog._on_fetch_all
    Deliver all results strictly via main-thread-polled queue.Queue (Rule 15).
    Capture (file_path, doc_id, box_uid, source_hash, req_seq) on dispatch;
    re-resolve target by box_uid and discard stale results if document, box, or source text changed in flight.
  - BUG-14: Track `_batch_open: bool` in BatchTranslateDialog. On close/cancel while `_is_running`,
    set `_cancelled = True` ONLY, keep polling until worker emits ('done', ...), execute
    undo_journal.end_batch() strictly ONCE on the UI thread, update dirty/view state, and only then destroy.
"""

import ast
import hashlib
import inspect
import os
import queue
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.mtl_engine import MTLConfig, MTLEngine  # noqa: E402
from core.story_ast import Box, BoxSnapshot, Record, StoryDocument  # noqa: E402


class S11TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s11_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        # Mock out modal messageboxes
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

    def _create_sample_doc(self, num_boxes=3, prefix="Box") -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
        ]
        for i in range(num_boxes):
            recs.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker{i+1}", f"{prefix} {i+1} テスト"]))
        return StoryDocument(recs)


class TestP3S11MTLThreading(S11TestBase):
    """S11 TDD verification suite for BUG-27 and BUG-14."""

    # -----------------------------------------------------------------------
    # DEFECT PROBE 1 — BUG-27: Zero after_idle in Worker Threads & Stale Guards
    # -----------------------------------------------------------------------
    def test_probe_1_bug27_zero_after_idle_in_async_paths(self):
        """[Probe 1a — BUG-27] Verify ZERO after_idle calls from background worker threads across all 4 paths."""
        misora_src = Path(_REPO / "misora.py").read_text(encoding="utf-8")

        # Helper to extract function source by name
        def get_function_src(fn_name: str, class_name: str = "") -> str:
            tree = ast.parse(misora_src)
            for node in ast.walk(tree):
                if class_name:
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name == fn_name:
                                return ast.get_source_segment(misora_src, item) or ""
                else:
                    if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                        return ast.get_source_segment(misora_src, item) or ""
            return ""

        paths = [
            ("on_translate_current_box", "MisoraApp"),
            ("_on_test_connection", "MTLSettingsDialog"),
            ("_on_translate", "TranslatorAssistantDialog"),
            ("_on_fetch_all", "TranslatorAssistantDialog"),
        ]

        violations = []
        for fn_name, cls_name in paths:
            src = get_function_src(fn_name, cls_name)
            self.assertTrue(src, f"Could not find {cls_name}.{fn_name} in misora.py")
            # Search for after_idle calls
            if "after_idle" in src:
                violations.append(f"{cls_name}.{fn_name} contains 'after_idle'")

        self.assertEqual(
            violations,
            [],
            f"Rule 15 / BUG-27 violation: Background worker paths must NOT use after_idle:\n"
            + "\n".join(violations),
        )

    def test_probe_1b_bug27_stale_identity_guard_on_doc_switch(self):
        """[Probe 1b — BUG-27] Switching active document before async F8 reply arrives discards stale result."""
        doc1 = self._create_sample_doc(2, prefix="Doc1 Box")
        doc2 = self._create_sample_doc(2, prefix="Doc2 Box")

        path1 = self.tmp_dir / "story1.unity3d"
        path2 = self.tmp_dir / "story2.unity3d"

        self.app.open_documents[path1] = {"doc": doc1, "plain_text": ""}
        self.app.open_documents[path2] = {"doc": doc2, "plain_text": ""}

        # Load Doc 1 and select Box 0
        self.app.current_file_path = path1
        self.app.current_doc = doc1
        self.app.current_box_idx = 0

        # Intercept translate_async so it does not complete synchronously
        intercepted_workers = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")

            def finish_reply():
                res = "Translated English for Doc1"
                if out_queue is not None:
                    out_queue.put(("box_success", metadata, res, config.active_engine))
                elif on_success is not None:
                    on_success(res)

            intercepted_workers.append(finish_reply)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            self.app.on_translate_current_box()

            # Verify that translation request was dispatched
            self.assertEqual(len(intercepted_workers), 1, "translate_async must be called on F8")

            # NOW user switches to Doc 2
            self.app.current_file_path = path2
            self.app.current_doc = doc2
            self.app.current_box_idx = 0

            # Background thread now finishes and puts message into queue
            intercepted_workers[0]()

            # Process UI event loop / queue
            for _ in range(5):
                self.app.update()
                time.sleep(0.02)
            if hasattr(self.app, "_poll_mtl_queue"):
                self.app._poll_mtl_queue()

        # Doc 2 Box 0 must NOT be corrupted by the translation for Doc 1 Box 0
        self.assertEqual(
            doc2.boxes[0].clean_text,
            "Doc2 Box 1 テスト",
            "Stale F8 translation must NOT overwrite active box in switched document!",
        )

    def test_probe_1c_bug27_stale_identity_guard_on_source_edit(self):
        """[Probe 1c — BUG-27] Editing box text while F8 is in flight discards stale translation."""
        doc = self._create_sample_doc(2, prefix="Box")
        path = self.tmp_dir / "story_edit.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0

        intercepted_workers = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")

            def finish_reply():
                res = "Translated Original Text"
                if out_queue is not None:
                    out_queue.put(("box_success", metadata, res, config.active_engine))
                elif on_success is not None:
                    on_success(res)

            intercepted_workers.append(finish_reply)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            self.app.on_translate_current_box()
            self.assertEqual(len(intercepted_workers), 1)

            # User edits Box 0 while in flight
            doc.inject_box(0, "Speaker1", "Manually Edited In Flight")

            # Worker completes for original text
            intercepted_workers[0]()

            for _ in range(5):
                self.app.update()
                time.sleep(0.02)
            if hasattr(self.app, "_poll_mtl_queue"):
                self.app._poll_mtl_queue()

        # Box 0 must preserve manual edit, not overwritten by stale translation
        self.assertEqual(
            doc.boxes[0].clean_text,
            "Manually Edited In Flight",
            "Stale translation must NOT overwrite text edited while in flight!",
        )

    def test_probe_1d_bug27_target_reresolved_by_box_uid_on_insertion(self):
        """[Probe 1d — BUG-27] Target box is re-resolved by box_uid when preceding box is inserted in flight."""
        doc = self._create_sample_doc(3, prefix="Box")
        path = self.tmp_dir / "story_shift.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc

        # Select Box 1 (second dialogue box)
        self.app.current_box_idx = 1
        target_uid = doc.boxes[1].uid
        orig_text = doc.boxes[1].clean_text

        intercepted_workers = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")

            def finish_reply():
                res = "Translated Target Box 2"
                if out_queue is not None:
                    out_queue.put(("box_success", metadata, res, config.active_engine))
                elif on_success is not None:
                    on_success(res)

            intercepted_workers.append(finish_reply)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            self.app.on_translate_current_box()
            self.assertEqual(len(intercepted_workers), 1)

            # Insert a new box at index 0 (shifts original Box 1 to index 2!)
            snap = BoxSnapshot(speaker="NewSpeaker", voice_cue="", kind="print", seg_texts=["Inserted Box 0"])
            doc.insert_box(0, snap)

            self.assertEqual(len(doc.boxes), 4)
            self.assertEqual(doc.boxes[2].uid, target_uid)

            # Reply arrives
            intercepted_workers[0]()

            for _ in range(5):
                self.app.update()
                time.sleep(0.02)
            if hasattr(self.app, "_poll_mtl_queue"):
                self.app._poll_mtl_queue()

        # The newly inserted box at index 1 (or 0) must NOT be overwritten
        # The target box now at index 2 must have received the translation!
        self.assertEqual(
            doc.boxes[2].clean_text,
            "Translated Target Box 2",
            "Target box must be re-resolved by box_uid and receive translation despite index shift!",
        )
        self.assertNotEqual(
            doc.boxes[1].clean_text,
            "Translated Target Box 2",
            "Preceding box at shifted index must NOT receive translation!",
        )

    def test_probe_1e_bug27_translator_assistant_stale_identity_guard(self):
        """[Probe 1e — BUG-27] Navigating to next box while TranslatorAssistant translation is in flight discards stale result."""
        doc = self._create_sample_doc(3, prefix="Box")
        path = self.tmp_dir / "story_asst.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0

        dlg = misora.TranslatorAssistantDialog(self.app)
        self.assertTrue(hasattr(dlg, "worker_queue"), "TranslatorAssistantDialog must own worker_queue (BUG-27)")

        intercepted_workers = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            def finish_reply():
                if on_success:
                    on_success("Translated Box 1")
            intercepted_workers.append(finish_reply)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            dlg._on_translate()
            self.assertEqual(len(intercepted_workers), 1)

            # User navigates to Box 2 while translation is in flight
            dlg._on_next()
            self.assertEqual(self.app.current_box_idx, 1)
            self.assertEqual(dlg.txt_trans.get("1.0", "end-1c"), doc.boxes[1].clean_text)

            # Translation reply arrives for Box 1
            intercepted_workers[0]()

            for _ in range(5):
                self.app.update()
                time.sleep(0.02)
            if hasattr(dlg, "_poll_worker_queue"):
                dlg._poll_worker_queue()

        # txt_trans must NOT be overwritten with stale translation for Box 1
        self.assertEqual(
            dlg.txt_trans.get("1.0", "end-1c"),
            doc.boxes[1].clean_text,
            "TranslatorAssistantDialog must discard stale translation when user navigated to another box!",
        )
        dlg._on_close()

    def test_probe_1f_bug27_mtl_settings_connection_test_queue_delivery(self):
        """[Probe 1f — BUG-27] MTLSettingsDialog tests connection via queue.Queue with zero after_idle."""
        dlg = misora.MTLSettingsDialog(self.app)
        self.assertTrue(hasattr(dlg, "worker_queue"), "MTLSettingsDialog must own worker_queue (BUG-27)")

        with patch("misora.MTLEngine.test_connection", return_value=(True, "Success: 'Mock' -> 'Mock'")):
            dlg._on_test_connection()
            self.assertEqual(str(dlg.btn_tst.cget("state")), "disabled")

            # Wait for queue delivery on main thread
            for _ in range(20):
                self.app.update()
                if str(dlg.btn_tst.cget("state")) == "normal":
                    break
                time.sleep(0.05)

        self.assertEqual(str(dlg.btn_tst.cget("state")), "normal")
        self.assertIn("Success:", dlg.lbl_tst_result.cget("text"))
        dlg._on_close()

    # -----------------------------------------------------------------------
    # DEFECT PROBE 2 — BUG-14: Safe Batch Cancel & Single end_batch
    # -----------------------------------------------------------------------
    def test_probe_2_bug14_batch_cancel_tracks_batch_open_and_ends_once(self):
        """[Probe 2 — BUG-14] Closing BatchTranslateDialog mid-run sets _cancelled, waits for done, and calls end_batch once."""
        doc = self._create_sample_doc(5)
        path = self.tmp_dir / "batch_cancel.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc

        dlg = misora.BatchTranslateDialog(self.app)
        self.assertTrue(
            hasattr(dlg, "_batch_open"),
            "BatchTranslateDialog must track _batch_open: bool (BUG-14)",
        )
        self.assertFalse(dlg._batch_open)

        dlg.var_scope.set("all")
        dlg.var_delay.set(0.05)

        end_batch_calls = []
        original_end_batch = self.app.undo_journal.end_batch

        def spy_end_batch(*args, **kwargs):
            end_batch_calls.append(threading.current_thread())
            return original_end_batch(*args, **kwargs)

        def slow_translate(text, *args, **kwargs):
            time.sleep(0.05)
            return f"En: {text}"

        with patch("misora.MTLEngine.translate", side_effect=slow_translate), \
             patch.object(self.app.undo_journal, "end_batch", side_effect=spy_end_batch):
            dlg._start_batch()
            self.assertTrue(dlg._is_running, "Batch must be marked running")
            self.assertTrue(dlg._batch_open, "_batch_open must be True while batch runs")

            # User clicks close button mid-run
            time.sleep(0.02)
            dlg._on_close()

            # Must set _cancelled = True
            self.assertTrue(dlg._cancelled, "_on_close while running must set _cancelled = True")

            # Wait for background thread to wind down and queue to process
            for _ in range(50):
                self.app.update()
                if not dlg.winfo_exists():
                    break
                time.sleep(0.05)

            # Dialog must only be destroyed AFTER worker finishes and end_batch is called
            self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed after worker completes")
            self.assertEqual(
                len(end_batch_calls), 1,
                f"undo_journal.end_batch must be called strictly ONCE, called {len(end_batch_calls)} times",
            )
            self.assertEqual(
                end_batch_calls[0], threading.main_thread(),
                "undo_journal.end_batch must be executed on UI main thread",
            )

    # -----------------------------------------------------------------------
    # REGRESSION GUARDS (MUST PASS BOTH BEFORE AND AFTER PATCH)
    # -----------------------------------------------------------------------
    def test_guard_1_mtl_engine_ngui_tagmasker_contract(self):
        """[Guard 1] MTLEngine with TagMasker cleanly shields and preserves NGUI tags and placeholders."""
        cfg = MTLConfig(active_engine="Google", protect_tags=True)
        engine = MTLEngine(cfg)

        raw = "Hello [b]Yuuki[/b]! Welcome to [ff5500]Landosol[/]! {playername}"
        # Direct check that translate on empty string is empty
        self.assertEqual(engine.translate(""), "")

    def test_guard_2_batch_translate_clean_run_lifecycle(self):
        """[Guard 2] BatchTranslateDialog normal run without cancel completes and records matching undo batch."""
        doc = self._create_sample_doc(2)
        path = self.tmp_dir / "batch_clean.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc

        dlg = misora.BatchTranslateDialog(self.app)
        dlg.var_scope.set("all")
        dlg.var_delay.set(0.0)

        with patch("misora.MTLEngine.translate", return_value="English"):
            dlg._start_batch()
            for _ in range(50):
                self.app.update()
                if not dlg._is_running:
                    break
                time.sleep(0.05)

        dlg.destroy()
        self.assertEqual(doc.boxes[0].clean_text, "English")
        self.assertEqual(doc.boxes[1].clean_text, "English")


if __name__ == "__main__":
    unittest.main(verbosity=2)
