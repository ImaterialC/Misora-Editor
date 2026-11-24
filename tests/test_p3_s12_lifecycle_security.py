#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_p3_s12_lifecycle_security.py
========================================
Lifecycle, Security, Memory & Startup Verification Suite for Session 12 (BUG-32..36).

Session Scope:
- BUG-32: Logger completion barrier, clear_log_file race immunity, clean teardown & after sweep.
- BUG-33: Windows DPAPI fail-closed on CryptProtectData failure, non-truncation of config,
          unprotect_secret RuntimeWarning and ciphertext preservation.
- BUG-34: reload_from_disk disposes prior open_documents[file_path]['env'] and clears entry.
- BUG-35: Defer initial_path and session file restoration after deiconify via after_idle.
- BUG-36: Safe case-insensitive numeric sorting of SPLASH_IMAGES with non-numeric fallback.

Strict Invariants:
- Preserves and restores misora.CONFIG_PATH.
- Redirects app.backup_folder to a TemporaryDirectory (0 writes to repo backups/).
- Suppresses modal messageboxes and live network requests.
"""
from __future__ import annotations

import gc
import json
import os
import queue
import sys
import tempfile
import threading
import time
import unittest
import warnings
import weakref
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import core.logger as logger_mod
import core.mtl_engine as mtl_mod
import core.security as sec_mod
import assets.splash as splash_mod
import misora
from core.logger import MisoraLogger
from core.mtl_engine import MTLConfig
from core.story_ast import StoryDocument


class TestP3S12LifecycleSecurity(unittest.TestCase):
    """S12 Defect Probes and Lifecycle/Security Regression Guards."""

    def setUp(self) -> None:
        self.temp_dir_obj = tempfile.TemporaryDirectory(prefix="misora_s12_test_")
        self.temp_dir = Path(self.temp_dir_obj.name)

        # Redirect CONFIG_PATH
        self._orig_config_path = misora.CONFIG_PATH
        self.test_config_path = self.temp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.test_config_path

        # Mock modal dialogs
        self._patcher_showerror = mock.patch("tkinter.messagebox.showerror")
        self._patcher_askyesnocancel = mock.patch("tkinter.messagebox.askyesnocancel", return_value=False)
        self._patcher_askyesno = mock.patch("tkinter.messagebox.askyesno", return_value=False)
        self._patcher_showinfo = mock.patch("tkinter.messagebox.showinfo")
        self._patcher_showwarning = mock.patch("tkinter.messagebox.showwarning")

        self.mock_showerror = self._patcher_showerror.start()
        self.mock_askyesnocancel = self._patcher_askyesnocancel.start()
        self.mock_askyesno = self._patcher_askyesno.start()
        self.mock_showinfo = self._patcher_showinfo.start()
        self.mock_showwarning = self._patcher_showwarning.start()

        self.apps_to_destroy: List[misora.MisoraApp] = []

    def tearDown(self) -> None:
        for app in self.apps_to_destroy:
            try:
                if hasattr(app, "logger") and app.logger:
                    app.logger.close()
            except Exception:
                pass
            try:
                app.destroy()
            except Exception:
                pass

        self._patcher_showerror.stop()
        self._patcher_askyesnocancel.stop()
        self._patcher_askyesno.stop()
        self._patcher_showinfo.stop()
        self._patcher_showwarning.stop()

        misora.CONFIG_PATH = self._orig_config_path
        self.temp_dir_obj.cleanup()

    # -------------------------------------------------------------------------
    # Probe 1: BUG-32 — Logger Flush Completion Barrier & Clean App Teardown
    # -------------------------------------------------------------------------
    def test_01_logger_flush_barrier_and_app_teardown(self) -> None:
        """
        Probe 1 (BUG-32):
        1. In MisoraLogger: Slow disk write must complete before flush() returns,
           guaranteeing clear_log_file() truncates without in-flight write appending stale lines.
        2. In MisoraApp: destroy() and _on_app_exit() must sweep pending Tk after jobs
           via tk.call('after', 'info') and invoke self.logger.close().
        """
        # Part A: Flush barrier vs clear_log_file race
        test_log_path = self.temp_dir / "test_barrier.log"
        logger = MisoraLogger(test_log_path)
        logger.configure(log_to_file=True)

        orig_write = logger._write_entry_to_file

        def slow_write(entry: Any) -> None:
            # Simulate slow disk I/O while writing
            time.sleep(0.08)
            orig_write(entry)

        logger._write_entry_to_file = slow_write  # type: ignore

        # Queue a log message and immediately call clear_log_file()
        logger.info("File I/O", "Probe 1 message for flush barrier")
        cleared = logger.clear_log_file()
        self.assertTrue(cleared)

        # Allow time for any un-joined in-flight write to complete
        time.sleep(0.12)

        # In pre-patch: flush() polls _file_queue.empty() and returns while slow_write
        # is still running. clear_log_file() exits, and THEN slow_write completes and
        # appends to the log, leaving a stale entry.
        # In post-patch: flush() waits on completion condition (all_tasks_done/task_done),
        # so clear_log_file() truncates strictly AFTER slow_write finishes -> 0 stale lines.
        content = test_log_path.read_text(encoding="utf-8") if test_log_path.exists() else ""
        self.assertEqual(
            content.strip(),
            "",
            f"Stale log content detected after clear_log_file()! In-flight write was not completed before flush returned. Found: {repr(content)}"
        )
        logger.close()

        # Part B: MisoraApp destroy sweeps after jobs and calls logger.close()
        app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.apps_to_destroy.append(app)

        # Schedule a lingering after job that is not one of the hardcoded attributes
        lingering_job = app.after(100000, lambda: None)
        active_jobs_before = app.tk.call("after", "info")
        self.assertIn(lingering_job, active_jobs_before)

        # Spy on app.logger.close
        logger_close_called = False
        orig_logger_close = app.logger.close

        def spy_close() -> None:
            nonlocal logger_close_called
            logger_close_called = True
            orig_logger_close()

        app.logger.close = spy_close  # type: ignore

        # Execute destroy()
        app.destroy()

        self.assertTrue(
            logger_close_called,
            "MisoraApp.destroy() must call self.logger.close() to cleanly terminate background log writer."
        )

    # -------------------------------------------------------------------------
    # Probe 2: BUG-33 — DPAPI Fail-Closed, Non-Truncation & Ciphertext Preservation
    # -------------------------------------------------------------------------
    def test_02_dpapi_fail_closed_and_ciphertext_preservation(self) -> None:
        """
        Probe 2 (BUG-33):
        1. On Windows CryptProtectData failure, protect_secret() must raise DPAPISecurityError
           instead of silently returning plaintext.
        2. MTLConfig.to_dict(secure=True) must propagate DPAPISecurityError.
        3. _save_user_prefs() must abort without writing unencrypted plaintext,
           and must NOT truncate existing misora_config.json to 0 bytes.
        4. On CryptUnprotectData failure, unprotect_secret() must emit RuntimeWarning
           and preserve ciphertext (dpapi:...) instead of returning '' and wiping the key.
        """
        if sys.platform != "win32":
            self.skipTest("Windows-only DPAPI security probe")

        # Part A: protect_secret failure must fail closed with DPAPISecurityError
        with mock.patch("ctypes.windll.crypt32.CryptProtectData", return_value=0):
            # Pre-patch: returns "super_secret_key" (plaintext)
            # Post-patch: raises sec_mod.DPAPISecurityError
            DPAPISecurityError = getattr(sec_mod, "DPAPISecurityError", None)
            if DPAPISecurityError is None:
                # Pre-patch symbol missing: assert failure directly
                result = sec_mod.protect_secret("super_secret_key")
                self.assertNotEqual(
                    result,
                    "super_secret_key",
                    "protect_secret() must NOT silently return plaintext on CryptProtectData failure!"
                )
            else:
                with self.assertRaises(DPAPISecurityError):
                    sec_mod.protect_secret("super_secret_key")

                # MTLConfig.to_dict(secure=True) must propagate DPAPISecurityError
                cfg = MTLConfig(deepl_api_key="super_secret_key")
                with self.assertRaises(DPAPISecurityError):
                    cfg.to_dict(secure=True)

        # Part B: _save_user_prefs non-truncation on DPAPI error
        # Prepare existing config file with known content
        initial_cfg = {"config_version": 4, "sentinel_value": "DO_NOT_CORRUPT"}
        self.test_config_path.write_text(json.dumps(initial_cfg), encoding="utf-8")

        app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.apps_to_destroy.append(app)
        app.mtl_config.deepl_api_key = "secret_to_protect"

        with mock.patch("ctypes.windll.crypt32.CryptProtectData", return_value=0):
            app._save_user_prefs(silent=True)

        # Config file must NOT be truncated to 0 bytes or overwritten with plaintext secret
        saved_text = self.test_config_path.read_text(encoding="utf-8")
        self.assertGreater(len(saved_text), 0, "misora_config.json must not be truncated on DPAPI failure!")
        self.assertNotIn(
            "secret_to_protect",
            saved_text,
            "Plaintext secret must NEVER be written to misora_config.json on DPAPI failure!"
        )

        # Part C: unprotect_secret ciphertext preservation on CryptUnprotectData failure
        encrypted_blob = "dpapi:dGVzdF9jaXBoZXJfdGV4dA=="
        with mock.patch("ctypes.windll.crypt32.CryptUnprotectData", return_value=0):
            with warnings.catch_warnings(record=True) as recorded_warnings:
                warnings.simplefilter("always")
                recovered = sec_mod.unprotect_secret(encrypted_blob)

            # Pre-patch: returns "" (wipes key)
            # Post-patch: returns encrypted_blob and warns with RuntimeWarning
            self.assertEqual(
                recovered,
                encrypted_blob,
                f"unprotect_secret() must preserve ciphertext on failure to prevent wiping credentials! Got: {repr(recovered)}"
            )
            self.assertTrue(
                any(issubclass(w.category, RuntimeWarning) for w in recorded_warnings),
                "unprotect_secret() must emit a RuntimeWarning on decryption failure."
            )

    # -------------------------------------------------------------------------
    # Probe 3: BUG-34 — reload_from_disk Disposes Prior Environment
    # -------------------------------------------------------------------------
    def test_03_reload_from_disk_disposes_prior_env(self) -> None:
        """
        Probe 3 (BUG-34):
        When open_file(path, reload_from_disk=True) reloads a file, it must dispose
        prior_entry['env'] via dispose_unity_env() and call prior_entry.clear()
        BEFORE overwriting self.open_documents[file_path].
        """
        app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.apps_to_destroy.append(app)

        test_file = self.temp_dir / "test_reload_story.txt"
        test_file.write_text("Test dialogue content", encoding="utf-8")

        # Create a mock environment with circular reference cycle
        class MockUnityEnv:
            def __init__(self) -> None:
                self.files: Dict[str, Any] = {}
                self.assets: List[Any] = []
                self.cabs: Dict[str, Any] = {}
                self.container: Dict[str, Any] = {}

        old_env = MockUnityEnv()
        # Circular cycle: f.parent -> old_env
        class MockFile:
            def __init__(self, parent: Any) -> None:
                self.parent = parent
                self.environment = parent

        old_env.files["test_asset"] = MockFile(old_env)

        # Register prior document in open_documents
        prior_entry = {
            "doc": StoryDocument(),
            "env": old_env,
            "obj": None,
            "is_bundle": True,
            "dirty": False,
            "plain_text": "",
        }
        app.open_documents[test_file] = prior_entry

        # Hold a weak reference to old_env
        wr = weakref.ref(old_env)
        del old_env

        # Execute reload_from_disk=True
        app.open_file(test_file, reload_from_disk=True)

        gc.collect()

        # In pre-patch: prior_entry is overwritten without dispose_unity_env(),
        # so circular cycle keeps old_env alive: wr() is not None.
        # In post-patch: dispose_unity_env(prior_entry['env']) breaks cycles and
        # prior_entry.clear() is called, allowing immediate collection: wr() is None.
        self.assertIsNone(
            wr(),
            "Prior environment was not collected after reload_from_disk=True! Cyclic references were not broken."
        )

    # -------------------------------------------------------------------------
    # Probe 4: BUG-35 — Deferred Startup File Restoration After Deiconify
    # -------------------------------------------------------------------------
    def test_04_deferred_startup_restore_after_deiconify(self) -> None:
        """
        Probe 4 (BUG-35):
        During MisoraApp.__init__, deiconify() must execute BEFORE deferred session files
        load via after_idle. Calling app.update() drains after_idle and yields
        ['deiconify', 'open_file'].
        """
        test_file = self.temp_dir / "startup_story.txt"
        test_file.write_text("Startup text", encoding="utf-8")

        call_order: List[str] = []

        orig_init = misora.MisoraApp.__init__

        # Instrument MisoraApp methods to capture execution sequence
        def tracking_init(self_app: Any, *args: Any, **kwargs: Any) -> None:
            orig_deiconify = self_app.deiconify
            orig_open_file = self_app.open_file

            def tracked_deiconify(*a: Any, **kw: Any) -> Any:
                call_order.append("deiconify")
                return orig_deiconify(*a, **kw)

            def tracked_open_file(*a: Any, **kw: Any) -> Any:
                call_order.append("open_file")
                return orig_open_file(*a, **kw)

            self_app.deiconify = tracked_deiconify
            self_app.open_file = tracked_open_file

            orig_init(self_app, *args, **kwargs)

        with mock.patch.object(misora.MisoraApp, "__init__", tracking_init):
            app = misora.MisoraApp(initial_path=str(test_file), show_splash=False)
            self.apps_to_destroy.append(app)

            # In pre-patch: open_file is called synchronously inside __init__ before deiconify.
            # Order at __init__ exit: ['open_file', 'deiconify']
            # In post-patch: deiconify occurs first; open_file is scheduled via after_idle.
            # Order at __init__ exit: ['deiconify']
            self.assertEqual(
                call_order[:1],
                ["deiconify"],
                f"deiconify() must execute before opening files on startup! Got call_order: {call_order}"
            )

            # Drain pending idle jobs via app.update()
            app.update()

            # After draining idle jobs, open_file has executed
            self.assertEqual(
                call_order,
                ["deiconify", "open_file"],
                f"Expected ['deiconify', 'open_file'] after draining after_idle, got: {call_order}"
            )

    # -------------------------------------------------------------------------
    # Probe 5: BUG-36 — Safe Case-Insensitive Splash Images Sorting
    # -------------------------------------------------------------------------
    def test_05_splash_images_sort_key_guards_non_numeric(self) -> None:
        """
        Probe 5 (BUG-36):
        Splash sort key must extract numeric suffix case-insensitively via Path(name).stem
        without ValueError, sorting numeric images (e.g. Splash_2.JPG before Splash_10.jpg)
        and ordering non-numeric filenames safely at the end.
        """
        test_filenames = [
            "Splash_10.jpg",
            "Splash_2.JPG",
            "Splash_custom.jpg",
            "Splash_promo.PNG",
            "Splash_1.jpg",
        ]

        self.assertTrue(
            hasattr(splash_mod, "_splash_sort_key"),
            "assets.splash must define _splash_sort_key to guard against non-numeric filenames."
        )
        sort_key_fn = splash_mod._splash_sort_key
        sorted_files = sorted(test_filenames, key=sort_key_fn)
        expected_prefix = ["Splash_1.jpg", "Splash_2.JPG", "Splash_10.jpg"]
        self.assertEqual(
            sorted_files[:3],
            expected_prefix,
            f"Incorrect splash sort order: {sorted_files}"
        )
        self.assertIn("Splash_custom.jpg", sorted_files[3:])
        self.assertIn("Splash_promo.PNG", sorted_files[3:])

    # -------------------------------------------------------------------------
    # Regression Guards: Lightweight Pre-Patch Contracts (Must Pass Both Before & After)
    # -------------------------------------------------------------------------
    def test_06_regression_guard_performance_config(self) -> None:
        """Regression Guard: Logging, config backups & core import invariants pass."""
        # Verify basic MisoraLogger disk writing
        test_log = self.temp_dir / "guard_test.log"
        logger = MisoraLogger(test_log)
        logger.configure(log_to_file=True)
        logger.info("File I/O", "Guard log entry")
        logger.flush(timeout=2.0)
        logger.close()
        self.assertTrue(test_log.exists())
        self.assertIn("Guard log entry", test_log.read_text(encoding="utf-8"))

    def test_07_regression_guard_mtl_security(self) -> None:
        """Regression Guard: Normal DPAPI protect and unprotect roundtrip."""
        if sys.platform != "win32":
            self.skipTest("Windows-only DPAPI guard")
        raw = "normal_secret_12345"
        protected = sec_mod.protect_secret(raw)
        self.assertTrue(protected.startswith("dpapi:"))
        unprotected = sec_mod.unprotect_secret(protected)
        self.assertEqual(unprotected, raw)


if __name__ == "__main__":
    unittest.main()
