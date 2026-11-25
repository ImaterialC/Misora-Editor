#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_v15_s01_stability_remediation.py
===========================================
Failing-first verification suite for v1.5 S01 (v1.4.1):
- BUG-01: Per-job search cancellation Event, bounded search_queue, 5-stage abort.
- BUG-02 / BONUS-02: Bounded MTL All Script concurrency + finite pending backpressure + shared SSL.
- BUG-03 / BONUS-01: Complete document-scoped cache pruning on close/reload + no late repopulation.
- BUG-04: Ownership-safe UnityPy env disposal on load_bundle_story() failure.
- BUG-05: Idempotent, producer-safe MisoraLogger.close() even when _file_queue is full.
- BUG-06: Atomic _is_saving guard placement in save_bundle_story().
- BONUS-03: On-demand polling & elimination of double bundle load in BulkFileDelta.
- U00 / U04: Single-source __version__ == "1.4.1" and "Misora: Story Editor" rebrand.
"""

import importlib.util
import queue
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import assets.splash as splash
import core.bundle_io as bundle_io
import core.mtl_engine as mtl_engine
from core.logger import MisoraLogger
from core.search_engine import ProjectSearchEngine, SearchOptions
from core.story_ast import Record, StoryDocument
from core.undo_journal import BulkFileDelta
from core.workspace import MISORA_WORKSPACE_EXT
import misora


def _read_root_version() -> str:
    root_init = REPO_ROOT / "__init__.py"
    spec = importlib.util.spec_from_file_location("misora_root_s01_check", str(root_init))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "__version__", "")


class TestV15S01StabilityRemediation(unittest.TestCase):
    """S01 failing-first Defect Probes and Regression Guards."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s01_"))
        self.orig_config_path = misora.CONFIG_PATH
        self.tmp_config = self.tmp_dir / "misora_config.json"
        self.tmp_config.write_text("{}", encoding="utf-8")
        misora.CONFIG_PATH = self.tmp_config

        self.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        self.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=False)
        self.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        self.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        self.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        self.patch_yesno.start()
        self.patch_yesnocancel.start()
        self.patch_info.start()
        self.patch_warn.start()
        self.patch_err.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_yesnocancel.stop()
        self.patch_yesno.stop()
        misora.CONFIG_PATH = self.orig_config_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @staticmethod
    def _make_doc(num_boxes: int = 3, prefix: str = "セリフ") -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["タイトル"]),
            Record(cmd_id=1, cmd_name="outline", args=["あらすじ"]),
        ]
        for i in range(num_boxes):
            recs.append(Record(cmd_id=6, cmd_name="print", args=[f"キャラ{i+1}", f"{prefix}_{i+1}"]))
        return StoryDocument(recs)

    # -------------------------------------------------------------------------
    # Defect / Behavior Probes (MUST FAIL pre-patch, PASS post-patch)
    # -------------------------------------------------------------------------

    def test_probe_1_search_cancel_event_bounded_queue_and_walk_abort(self):
        """[Probe 1 — BUG-01] Per-job Event, bounded search_queue, os.walk abort, and no full-queue deadlock."""
        self.assertGreater(self.app.search_queue.maxsize, 0, "search_queue must have finite maxsize")
        self.assertTrue(
            hasattr(self.app, "_search_cancel_event") and isinstance(self.app._search_cancel_event, threading.Event),
            "MisoraApp must maintain per-job _search_cancel_event (threading.Event)",
        )

        # Cancel Search A, immediately start Search B -> A's event must stay set
        search_dir = self.tmp_dir / "search_root"
        search_dir.mkdir(parents=True, exist_ok=True)
        for d_i in range(4):
            sub = search_dir / f"sub_{d_i}"
            sub.mkdir()
            (sub / f"file_{d_i}.txt").write_text("TargetKeyword\n", encoding="utf-8")

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(search_dir))
        self.app.search_var.set("TargetKeyword")

        captured_events = []

        def spy_run(paths, options, mem_docs=None, search_seq=1, skip_paths=None, initial_skipped=None, cancel_event=None):
            captured_events.append(cancel_event)

        with patch.object(self.app, "_run_background_search", side_effect=spy_run):
            self.app.on_start_search()
            if getattr(self.app, "_search_thread", None):
                self.app._search_thread.join(timeout=2.0)
            ev_a = captured_events[0]
            self.assertIsInstance(ev_a, threading.Event)
            self.app.on_cancel_search()
            self.assertTrue(ev_a.is_set(), "Cancelling Search A must set Search A's Event")

            self.app.on_start_search()
            if getattr(self.app, "_search_thread", None):
                self.app._search_thread.join(timeout=2.0)
            ev_b = captured_events[1]
            self.assertIsNot(ev_a, ev_b, "Search B must get a distinct Event")
            self.assertTrue(ev_a.is_set(), "Starting Search B must NOT clear Search A's cancelled Event")
            self.assertFalse(ev_b.is_set(), "Search B's Event must start unset")

        # os.walk abort check
        engine = ProjectSearchEngine()
        visited_files = []
        cancel_after_first = False

        def _on_prog(_cur, _tot, fname):
            nonlocal cancel_after_first
            visited_files.append(fname)
            cancel_after_first = True

        res = engine.search_directory(
            search_dir,
            SearchOptions(query="TargetKeyword", include_bundles=False, include_text=True),
            on_progress=_on_prog,
            should_cancel=lambda: cancel_after_first,
        )
        self.assertLessEqual(len(visited_files), 1, "search_directory must abort promptly on should_cancel")
        self.assertLessEqual(len(res), 1)

        # Full search_queue must NOT deadlock when cancelled
        while not self.app.search_queue.empty():
            try:
                self.app.search_queue.get_nowait()
            except queue.Empty:
                break
        for i in range(self.app.search_queue.maxsize):
            self.app.search_queue.put_nowait(("filler", i))

        ev_full = threading.Event()
        ev_full.set()
        done_flag = threading.Event()

        def _run_full():
            self.app._run_background_search(
                [search_dir],
                SearchOptions(query="TargetKeyword", include_bundles=False, include_text=True),
                {},
                search_seq=999,
                cancel_event=ev_full,
            )
            done_flag.set()

        th = threading.Thread(target=_run_full, daemon=True)
        th.start()
        self.assertTrue(done_flag.wait(timeout=2.0), "Cancelled producer must not deadlock on full search_queue")

    def test_probe_2_mtl_translate_all_bounded_workers_backpressure_and_shared_ssl(self):
        """[Probe 2 — BUG-02 / BONUS-02] Shared SSL, bounded workers (<=4), finite pending backpressure, cancel & late-reply reject."""
        e1 = mtl_engine.MTLEngine()
        e2 = mtl_engine.MTLEngine()
        self.assertIs(e1._ssl_ctx, e2._ssl_ctx, "MTLEngine must reuse one shared module-level SSLContext")

        doc = self._make_doc(40, prefix="長文テスト")
        path = (self.tmp_dir / "s01_mtl_40.unity3d").resolve()
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app.mtl_config.rate_limit_delay = 0.0
        self.app._open_side_drawer("mtl")
        self.app._set_mtl_drawer_mode("all_script")
        self.app.var_mtl_all_engine.set("Google")

        lock = threading.Lock()
        active = 0
        peak_active = 0
        started = 0
        release_event = threading.Event()

        def slow_translate(self_eng, text, config=None, xuat_cache=None):
            nonlocal active, peak_active, started
            with lock:
                active += 1
                started += 1
                peak_active = max(peak_active, active)
            release_event.wait(timeout=0.5)
            with lock:
                active -= 1
            return f"EN:{text}"

        with patch.object(mtl_engine.MTLEngine, "translate", slow_translate):
            self.app._on_mtl_all_script_translate_all()
            time.sleep(0.08)

            # While blocked, check active workers and pending Futures bound
            with lock:
                cur_peak = peak_active
                cur_started = started
            self.assertLessEqual(cur_peak, 4, f"Peak concurrent workers must be <= 4, got {cur_peak}")
            self.assertGreater(cur_peak, 0, "At least one worker should be active")
            self.assertLess(cur_started, 40, "Dispatcher must apply finite pending backpressure, not launch 40 at once")

            # Engine switch must cancel pending batch
            self.app.var_mtl_all_engine.set("DeepL")
            self.app._on_mtl_all_engine_changed()
            batch_cancel = getattr(self.app, "_mtl_all_batch_cancel", None)
            self.assertIsNotNone(batch_cancel)
            self.assertTrue(batch_cancel.is_set(), "Engine switch must cancel active Translate All batch")

            release_event.set()
            time.sleep(0.1)
            self.app._poll_mtl_drawer_queue()

        # Late replies for cancelled Google batch must NOT populate _mtl_all_results for Google
        google_entries = [k for k in self.app._mtl_all_results if k[3] == "Google"]
        self.assertEqual(len(google_entries), 0, "Cancelled/stale Google batch replies must be rejected")

    def test_probe_3_close_and_reload_prune_all_mtl_and_jp_caches_no_repopulate(self):
        """[Probe 3 — BUG-03 / BONUS-01] Close & reload prune all MTL/JP caches and reject late repopulation."""
        doc_a = self._make_doc(2, prefix="DocA")
        doc_b = self._make_doc(2, prefix="DocB")
        path_a = (self.tmp_dir / "doc_a.unity3d").resolve()
        path_b = (self.tmp_dir / "doc_b.txt").resolve()
        path_b.write_text("#!priconne-story\n", encoding="utf-8")

        self.app.open_documents[path_a] = {"doc": doc_a, "plain_text": "", "dirty": False}
        self.app.open_documents[path_b] = {"doc": doc_b, "plain_text": "", "dirty": False}

        uid_a0 = doc_a.boxes[0].uid
        uid_b0 = doc_b.boxes[0].uid
        self.app.sync_manager.register_jp_key(uid_a0, doc_a.boxes[0].clean_text)
        self.app.sync_manager.register_jp_key(uid_b0, doc_b.boxes[0].clean_text)

        ctx_a = (str(path_a), id(doc_a), uid_a0, "Google")
        ctx_b = (str(path_b), id(doc_b), uid_b0, "Google")
        self.app._mtl_all_results[ctx_a] = "Cached A"
        self.app._mtl_all_results[ctx_b] = "Cached B"
        self.app._mtl_all_statuses[ctx_a] = "ready"
        self.app._mtl_all_errors[ctx_a] = "Err A"
        self.app._mtl_all_req_seqs[(uid_a0, "Google")] = 5
        self.app._latest_applied_mtl_seq[uid_a0] = 5
        self.app._mtl_all_selected_uid = uid_a0
        self.app._mtl_all_last_ctx = ctx_a
        self.app._mtl_all_block_ranges = [(1, 3, uid_a0)]

        self.app.current_file_path = path_a
        self.app.current_doc = doc_a

        # Close Doc A
        self.assertTrue(self.app.close_file(path_a))

        self.assertFalse(any(k[0] == str(path_a) for k in self.app._mtl_all_results))
        self.assertFalse(any(k[0] == str(path_a) for k in self.app._mtl_all_statuses))
        self.assertFalse(any(k[0] == str(path_a) for k in self.app._mtl_all_errors))
        self.assertNotIn((uid_a0, "Google"), self.app._mtl_all_req_seqs)
        self.assertNotIn(uid_a0, self.app._latest_applied_mtl_seq)
        self.assertFalse(self.app.sync_manager.has_jp_key(uid_a0), "Closed Doc A JP key must be unregistered")
        self.assertTrue(self.app.sync_manager.has_jp_key(uid_b0), "Open Doc B JP key must remain intact")

        # Late queued result for Doc A must NOT repopulate _mtl_all_results
        late_meta = (str(path_a), id(doc_a), uid_a0, "fakehash", 99, "Google", "all_script")
        self.app._mtl_drawer_queue.put(("success", late_meta, "Late Zombie Translation"))
        self.app._poll_mtl_drawer_queue()
        self.assertFalse(any(k[0] == str(path_a) for k in self.app._mtl_all_results))

        # Reload Doc B must prune prior Doc B MTL caches
        self.app.open_file(path_b, reload_from_disk=True)
        self.assertFalse(any(k[1] == id(doc_b) for k in self.app._mtl_all_results))

    def test_probe_4_load_bundle_error_disposes_env_and_success_keeps_live_env(self):
        """[Probe 4 — BUG-04] load_bundle_story disposes env on failure and keeps live env on success."""
        fake_bundle = self.tmp_dir / "fake.unity3d"
        fake_bundle.write_bytes(b"FAKE_BUNDLE")

        bad_env = SimpleNamespace(objects=[])
        fake_unitypy = MagicMock()
        fake_unitypy.load.return_value = bad_env

        with patch.object(bundle_io, "get_unitypy", return_value=fake_unitypy), \
             patch.object(bundle_io, "dispose_unity_env") as mock_dispose:
            with self.assertRaises(bundle_io.BundleIOError):
                bundle_io.load_bundle_story(fake_bundle)
            mock_dispose.assert_called_once_with(bad_env)

        # Valid load must NOT dispose env
        valid_bin = self._make_doc(1).to_binary()
        good_data = SimpleNamespace(m_Name="storydata_100", m_Script=valid_bin)
        good_obj = SimpleNamespace(type=SimpleNamespace(name="TextAsset"), read=lambda: good_data)
        good_env = SimpleNamespace(objects=[good_obj])
        fake_unitypy.load.return_value = good_env

        with patch.object(bundle_io, "get_unitypy", return_value=fake_unitypy), \
             patch.object(bundle_io, "dispose_unity_env") as mock_dispose:
            doc, env, obj, name = bundle_io.load_bundle_story(fake_bundle)
            mock_dispose.assert_not_called()
            self.assertIs(env, good_env)
            self.assertEqual(name, "storydata_100")
            self.assertEqual(len(doc.boxes), 1)

    def test_probe_5_save_bundle_mkdir_failure_releases_is_saving(self):
        """[Probe 5 — BUG-06] mkdir PermissionError in save_bundle_story must reset _is_saving to False."""
        doc = self._make_doc(1)
        out_path = self.tmp_dir / "no_perm_dir" / "out.unity3d"
        fake_env = MagicMock()
        fake_obj = MagicMock()

        with patch.object(Path, "mkdir", side_effect=PermissionError("Denied")):
            with self.assertRaises(PermissionError):
                bundle_io.save_bundle_story(fake_env, fake_obj, doc, out_path)

        self.assertFalse(bundle_io._is_saving, "_is_saving must be reset to False even if mkdir fails")

    def test_probe_6_logger_close_idempotent_full_queue_and_post_close_log(self):
        """[Probe 6 — BUG-05] MisoraLogger.close() is idempotent on full queue and post-close log() does not spawn threads."""
        log_path = self.tmp_dir / "s01_logger.log"
        logger = MisoraLogger(log_path)
        logger.configure(log_to_file=True)

        # Fill _file_queue to capacity while writer is paused
        block_ev = threading.Event()
        orig_write = logger._write_entry_to_file

        def slow_write(entry):
            block_ev.wait(timeout=0.3)
            orig_write(entry)

        logger._write_entry_to_file = slow_write  # type: ignore
        logger.info("File I/O", "First entry")
        for i in range(logger._file_queue.maxsize):
            try:
                logger._file_queue.put_nowait(None if False else logger._history[-1])
            except queue.Full:
                break

        block_ev.set()
        logger.close()
        logger.close()  # Must be idempotent

        self.assertIsNone(logger._writer_thread, "Dead writer thread reference should be cleared")

        # Post-close log() must not raise, enqueue, or spawn a writer thread
        logger.info("File I/O", "After close message")
        self.assertIsNone(logger._writer_thread, "log() after close() must not respawn _writer_thread")
        self.assertTrue(logger._file_queue.empty(), "log() after close() must not enqueue to _file_queue")

    def test_probe_7_bulk_delta_refreshes_active_doc_without_double_bundle_load(self):
        """[Probe 7 — BONUS-03] BulkFileDelta refreshes active bundle doc cleanly without redundant second load_bundle_story()."""
        bundle_file = (self.tmp_dir / "bulk_active.unity3d").resolve()
        bundle_file.write_bytes(b"LIVE")
        orig_bak = self.tmp_dir / "orig.unity3d"
        mod_bak = self.tmp_dir / "mod.unity3d"
        orig_bak.write_bytes(b"ORIG")
        mod_bak.write_bytes(b"MOD")

        old_doc = self._make_doc(1, prefix="Old")
        new_doc = self._make_doc(1, prefix="New")
        old_env = MagicMock()
        new_env = MagicMock()
        new_obj = MagicMock()

        self.app.open_documents[bundle_file] = {
            "doc": old_doc,
            "env": old_env,
            "obj": MagicMock(),
            "is_bundle": True,
            "dirty": True,
            "plain_text": "",
        }
        self.app.current_file_path = bundle_file
        self.app.current_doc = old_doc
        self.app.current_unity_env = old_env
        self.app.is_dirty = True

        delta = BulkFileDelta(
            description="Bulk replace",
            per_file=[(str(bundle_file), str(orig_bak), str(mod_bak), True)],
        )

        with patch("misora.load_bundle_story", return_value=(new_doc, new_env, new_obj, "storydata")) as mock_load, \
             patch("misora.dispose_unity_env"):
            self.app._apply_delta(delta, reverse=True, refresh_ui=True)

        self.assertEqual(mock_load.call_count, 1, "Active bundle must be loaded ONCE, not twice via open_file(reload_from_disk=True)")
        self.assertIs(self.app.current_doc, new_doc)
        self.assertFalse(self.app.is_dirty)

    def test_probe_8_rebrand_and_derived_version_1_4_1(self):
        """[Probe 8 — U00 / U04] __version__ == '1.4.1', derived parity, and 'Misora: Story Editor' rebrand."""
        self.assertEqual(_read_root_version(), "1.4.1")
        self.assertEqual(misora.__version__, "1.4.1")
        self.assertEqual(splash._VERSION, "1.4.1")
        self.assertEqual(mtl_engine.APP_VERSION, "1.4.1")

        self.assertIn("Misora: Story Editor", self.app.title())
        with patch.object(misora.messagebox, "showinfo") as mock_info:
            self.app.on_about()
            mock_info.assert_called_once()
            title_arg, body_arg = mock_info.call_args[0][:2]
            self.assertIn("Misora: Story Editor", title_arg)
            self.assertIn("Misora: Story Editor", body_arg)
            self.assertIn("Version 1.4.1", body_arg)

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # -------------------------------------------------------------------------

    def test_guard_1_cmd_id_35_32_and_story_ast_roundtrip(self):
        """[Guard 1] StoryDocument binary & v2 round-trip preserves cmd_id 35 and 32 unchanged."""
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Title"]),
            Record(cmd_id=32, cmd_name="subtitle", args=["Sub"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Dialogue line"]),
        ]
        doc = StoryDocument(recs)
        raw_bin = doc.to_binary()
        doc_bin = StoryDocument.from_binary(raw_bin)
        self.assertEqual([r.cmd_id for r in doc_bin.records], [0, 32, 35, 6])

        v2 = doc_bin.to_v2_text()
        doc_v2 = StoryDocument.from_v2_text(v2)
        self.assertEqual([r.cmd_id for r in doc_v2.records], [0, 32, 35, 6])
        self.assertEqual(doc_v2.records[2].args, ["Narration line"])

    def test_guard_2_translate_async_signature_backward_compat(self):
        """[Guard 2] translate_async() supports both callback and out_queue/metadata modes."""
        cfg = mtl_engine.MTLConfig(active_engine="Google")
        cb_res = []
        ev = threading.Event()

        with patch.object(mtl_engine.MTLEngine, "translate", return_value="OK_CB"):
            t1 = mtl_engine.translate_async(
                "テスト",
                cfg,
                on_success=lambda r: (cb_res.append(r), ev.set()),
            )
            self.assertTrue(ev.wait(timeout=2.0))
            t1.join(timeout=1.0)
        self.assertEqual(cb_res, ["OK_CB"])

        q = queue.Queue()
        with patch.object(mtl_engine.MTLEngine, "translate", return_value="OK_Q"):
            t2 = mtl_engine.translate_async("テスト", cfg, out_queue=q, metadata=("meta", 1))
            t2.join(timeout=2.0)
        self.assertEqual(q.get_nowait(), ("success", ("meta", 1), "OK_Q"))

    def test_guard_3_existing_config_paths_and_misora_ext_unchanged(self):
        """[Guard 3] Internal config filename and .misora workspace extension remain unchanged."""
        self.assertEqual(self.orig_config_path.name, "misora_config.json")
        self.assertEqual(MISORA_WORKSPACE_EXT, ".misora")


if __name__ == "__main__":
    unittest.main(verbosity=2)
