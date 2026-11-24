#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_p3_s02_hygiene.py — Failing-first regression test suite for Session S02.

Scope: HYG-02, HYG-05, HYG-06 (Track 1 · Group A).
- HYG-05: core/search_engine.py typing annotations (Any, Dict).
- HYG-06: core/mtl_engine.py single-source DeepL User-Agent (__version__).
- HYG-02: tests/*.py backups folder isolation to prevent repo root pollution.

Defect Probes (MUST FAIL before patch, PASS after patch):
1. test_probe_1_hyg05_search_engine_type_hints
2. test_probe_2_hyg06_deepl_user_agent_single_version
3. test_probe_3_hyg02_backups_isolation_on_save

Regression Guards (MUST PASS both before and after patch):
1. test_guard_1_root_version_untouched
2. test_guard_2_mtl_engine_no_circular_misora_import
"""
import json
import os
import subprocess
import sys
import tempfile
import typing
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def _read_root_version() -> str:
    """Read __version__ directly from repo root __init__.py without package collision."""
    init_p = REPO_ROOT / "__init__.py"
    for line in init_p.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("__version__"):
            parts = line.split("=")
            if len(parts) == 2:
                return parts[1].strip().strip('"\'')
    return ""

from core.search_engine import ProjectSearchEngine
from core.mtl_engine import MTLEngine, MTLConfig


class TestP3S02Hygiene(unittest.TestCase):
    """S02: Hygiene & single-source-of-truth regression tests."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s02_test_"))
        self.backups_dir = REPO_ROOT / "backups"
        self.backups_dir.mkdir(exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # -------------------------------------------------------------------------

    def test_probe_1_hyg05_search_engine_type_hints(self):
        """[Probe 1 — HYG-05] typing.get_type_hints(ProjectSearchEngine.search_directory) must resolve cleanly."""
        # Pre-patch: raises NameError because 'Dict' and 'Any' are not imported in core.search_engine
        # Post-patch: returns dictionary with resolved types including in_memory_docs
        hints = typing.get_type_hints(ProjectSearchEngine.search_directory)
        self.assertIn("in_memory_docs", hints)
        self.assertIn("options", hints)
        self.assertIn("return", hints)

    def test_probe_2_hyg06_deepl_user_agent_single_version(self):
        """[Probe 2 — HYG-06] DeepL User-Agent must use root __version__ (1.4.0), not hardcoded 1.3."""
        expected_version = _read_root_version()
        expected_ua = f"Misora-Story-Editor/{expected_version}"

        engine = MTLEngine()
        cfg = MTLConfig(active_engine="DeepL", deepl_api_key="test_api_key_redacted")

        # Mock urlopen to inspect outgoing request headers
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "character_count": 42,
            "character_limit": 500000,
            "translations": [{"text": "Hello world"}],
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        # 1. Test _test_deepl_usage
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            success, msg = engine._test_deepl_usage(cfg)
            self.assertTrue(success, f"Usage test failed: {msg}")
            req = mock_urlopen.call_args[0][0]
            ua = req.headers.get("User-agent")
            self.assertEqual(
                ua,
                expected_ua,
                f"DeepL usage User-Agent mismatch: expected '{expected_ua}', got '{ua}'",
            )

        # 2. Test _translate_deepl
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = engine._translate_deepl("テスト", cfg)
            self.assertEqual(result, "Hello world")
            req = mock_urlopen.call_args[0][0]
            ua = req.headers.get("User-agent")
            self.assertEqual(
                ua,
                expected_ua,
                f"DeepL translate User-Agent mismatch: expected '{expected_ua}', got '{ua}'",
            )

    def test_probe_3_hyg02_backups_isolation_on_save(self):
        """[Probe 3 — HYG-02] Existing save/replace test suite creates ZERO new files in repo backups/."""
        # Pre-patch: running test_s8b3_encoding_detection creates .bak_ files in repo backups/
        # Post-patch: test_s8b3_encoding_detection isolates backup_folder to tempdir, creating 0 files in repo backups/
        before_files = set(self.backups_dir.iterdir())

        # Run test_s8b3_encoding_detection in subprocess
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_s8b3_encoding_detection", "-v"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        after_files = set(self.backups_dir.iterdir())
        new_files = after_files - before_files

        # Clean up any leaked files immediately so the test environment stays clean
        for f in new_files:
            try:
                if f.is_file():
                    f.unlink()
            except Exception:
                pass

        self.assertEqual(
            proc.returncode,
            0,
            f"test_s8b3_encoding_detection failed to run:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        self.assertEqual(
            len(new_files),
            0,
            f"Leaked {len(new_files)} backup file(s) into repo root backups/: {[f.name for f in new_files]}",
        )

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both before AND after patch)
    # -------------------------------------------------------------------------

    def test_guard_1_root_version_untouched(self):
        """[Guard 1] Root __init__.__version__ must remain strictly '1.4.0' until S24."""
        self.assertEqual(_read_root_version(), "1.4.0")

    def test_guard_2_mtl_engine_no_circular_misora_import(self):
        """[Guard 2] Importing core.mtl_engine must NEVER import misora.py (checked in isolated process)."""
        cmd = [
            sys.executable,
            "-c",
            "import sys, core.mtl_engine; assert 'misora' not in sys.modules, 'misora was circularly imported!'",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(
            res.returncode,
            0,
            f"core.mtl_engine caused circular import of misora:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
