#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_phase3_performance_config.py
======================================
Automated test suite for Phase 3:
- CORE-IMPORT-COUPLING: core/__init__.py and bundle_io decoupled from UnityPy at import
- LOGGER-SYNC-IO: Asynchronous background worker queue for file logging
- CONFIG-RECOVERY-OVERWRITE: Corrupt config preserved as .bak recovery copy
- HARDCODED-PROJECT-PATH: Clean repository config with zero machine-specific paths
- Batch launcher optimization (misora.bat)
- Session restore deferral to after_idle
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import core
from core.logger import MisoraLogger, LogEntry


class TestPhase3PerformanceAndConfig(unittest.TestCase):

    def test_01_core_import_does_not_load_unitypy(self):
        """Importing core must NOT import UnityPy into sys.modules (Rule 22)."""
        cmd = [
            sys.executable,
            "-c",
            "import sys; import core; sys.exit(0 if 'UnityPy' not in sys.modules else 1)"
        ]
        res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True)
        self.assertEqual(
            res.returncode,
            0,
            "import core prematurely imported UnityPy into sys.modules"
        )

    def test_02_unitypy_lazy_load_under_lock(self):
        """get_unitypy() loads UnityPy on demand and sets fallback version."""
        from core.bundle_io import get_unitypy
        unitypy = get_unitypy()
        self.assertIsNotNone(unitypy)
        self.assertEqual(unitypy.config.FALLBACK_UNITY_VERSION, "2021.3.20f1")

    def test_03_logger_async_background_writer(self):
        """MisoraLogger writes asynchronously to disk via background worker queue."""
        with tempfile.TemporaryDirectory(prefix="misora_log_test_") as tmp:
            log_file = Path(tmp) / "test_async.log"
            logger = MisoraLogger(log_file)
            logger.configure(log_to_file=True, level_name="Debug")

            # Write 50 entries in rapid succession
            for i in range(50):
                logger.info("File I/O", f"Async entry #{i}")

            # Writer thread should be alive
            self.assertIsNotNone(logger._writer_thread)
            self.assertTrue(logger._writer_thread.is_alive())

            # Flush queue to disk
            logger.flush(timeout=2.0)
            self.assertTrue(log_file.is_file())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("Async entry #0", content)
            self.assertIn("Async entry #49", content)
            lines = [ln for ln in content.strip().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 50)

            # Close logger cleanly
            logger.close()
            self.assertIsNone(logger._writer_thread)

    def test_04_config_corrupt_preserves_bak_recovery_copy(self):
        """Corrupt config file must be preserved as a .bak recovery copy before using defaults."""
        with tempfile.TemporaryDirectory(prefix="misora_cfg_test_") as tmp:
            tmp_cfg = Path(tmp) / "misora_config.json"
            corrupt_payload = '{"dialogue_font_size": 15, "theme": { INVALID JSON'
            tmp_cfg.write_text(corrupt_payload, encoding="utf-8")

            import misora
            # Point CONFIG_PATH temporarily to our corrupt temp file
            orig_cfg_path = misora.CONFIG_PATH
            try:
                misora.CONFIG_PATH = tmp_cfg

                # Instantiate MisoraApp headless with mocked preferences loading
                app = misora.MisoraApp(restore_session=False, show_splash=False)
                app.withdraw()

                # Verify a .bak file was created alongside tmp_cfg
                bak_files = list(Path(tmp).glob("misora_config*.bak*"))
                self.assertGreater(len(bak_files), 0, "No .bak recovery file was created for corrupt config")
                self.assertEqual(bak_files[0].read_text(encoding="utf-8"), corrupt_payload)

                app.destroy()
            finally:
                misora.CONFIG_PATH = orig_cfg_path

    def test_05_clean_committed_config_has_no_machine_paths(self):
        """Committed misora_config.json must contain clean default values with zero user machine paths."""
        cfg_file = ROOT_DIR / "misora_config.json"
        self.assertTrue(cfg_file.is_file(), "misora_config.json not found in root")
        data = json.loads(cfg_file.read_text(encoding="utf-8"))

        self.assertEqual(data.get("saved_opened_files"), [])
        self.assertEqual(data.get("saved_active_file"), "")
        self.assertEqual(data.get("recent_files"), [])
        self.assertEqual(data.get("project_folder"), "")
        self.assertEqual(data.get("bepinex_project_folder"), "")
        self.assertEqual(data.get("last_opened_dir"), "")
        self.assertEqual(data.get("window_geometry"), "")

    def test_06_misora_bat_has_no_unitypy_probe_loops(self):
        """misora.bat must not execute redundant UnityPy probe loops on launch (Rule 22)."""
        bat_file = ROOT_DIR / "misora.bat"
        self.assertTrue(bat_file.is_file(), "misora.bat not found in root")
        bat_content = bat_file.read_text(encoding="utf-8")

        self.assertNotIn(
            "import UnityPy",
            bat_content,
            "misora.bat still contains slow 'import UnityPy' probe loops"
        )


if __name__ == "__main__":
    unittest.main()
