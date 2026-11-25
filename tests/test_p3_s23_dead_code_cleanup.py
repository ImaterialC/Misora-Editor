#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S23 — Final Grep-Proven Dead Code & Misleading Label Cleanup (HYG-08)
======================================================================
Failing-first regression test suite:
  - Probe 1: Removed zero-caller dead functions no longer exist on their classes
             (not hasattr(MisoraApp, '_update_gutter_cont'),
              not hasattr(BatchTranslateDialog, '_toggle_pin_top')), while
             TranslatorAssistantDialog._toggle_pin_top remains intact.
  - Probe 2: NguiColorPickerPopup displays canonical hyphen gradient syntax
             (not comma) and does not write picker_error.log to CWD on init error.
  - Probe 3: AIPromptSettingsDialog speaker-header checkbox uses accurate CSIF
             wording instead of legacy === [BOX:0|...] === wording.
  - Guard 1: _update_gutter_clean remains intact and functional.
"""

import gc
import os
import shutil
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402


def _collect_descendants(widget):
    out = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class S23TestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s23_test_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patch_cfg = patch.object(misora, "CONFIG_PATH", self.config_path)
        self.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        self.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        self.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        self.patch_cfg.start()
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
        self.app = None
        gc.collect()
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestS23DeadCodeAndLabels(S23TestBase):
    def test_probe_hyg08_dead_methods_removed(self):
        """Probe 1: Zero-caller dead methods are removed while live callers stay."""
        self.assertFalse(
            hasattr(misora.MisoraApp, "_update_gutter_cont"),
            "_update_gutter_cont has 0 callers and must be removed",
        )
        self.assertFalse(
            hasattr(misora.BatchTranslateDialog, "_toggle_pin_top"),
            "BatchTranslateDialog._toggle_pin_top has 0 callers and must be removed",
        )
        # TranslatorAssistantDialog._toggle_pin_top is still wired to btn_pin
        self.assertTrue(
            hasattr(misora.TranslatorAssistantDialog, "_toggle_pin_top"),
            "TranslatorAssistantDialog._toggle_pin_top has an active caller and must stay",
        )

    def test_probe_hyg08_picker_hyphen_label_and_no_cwd_log(self):
        """Probe 2: NguiColorPickerPopup uses hyphen gradient label and writes no CWD log."""
        popup = misora.NguiColorPickerPopup(
            self.app, primary_hex="#7b42bc", secondary_hex="#ff7da7"
        )
        try:
            grad_text = popup.btn_insert_grad.cget("text")
            self.assertEqual(grad_text, "Insert [7B42BC-FF7DA7]")
            self.assertNotIn(",", grad_text)
        finally:
            popup.destroy()

        orig_cwd = os.getcwd()
        try:
            os.chdir(self.tmp_dir)
            with patch.object(
                misora.NguiColorPickerPopup,
                "_build_ui",
                side_effect=RuntimeError("boom"),
            ):
                with self.assertRaises(RuntimeError):
                    misora.NguiColorPickerPopup(self.app)
            self.assertFalse(
                (self.tmp_dir / "picker_error.log").exists(),
                "NguiColorPickerPopup must not write picker_error.log to CWD",
            )
        finally:
            os.chdir(orig_cwd)

    def test_probe_hyg08_ai_prompt_csif_wording(self):
        """Probe 3: AIPromptSettingsDialog speaker checkbox uses CSIF wording, not legacy === [BOX:0|...] ===."""
        dlg = misora.AIPromptSettingsDialog(self.app)
        try:
            check_texts = [
                w.cget("text")
                for w in _collect_descendants(dlg)
                if isinstance(w, tk.Checkbutton)
            ]
            combined = "\n".join(check_texts)
            self.assertNotIn("=== [BOX:0", combined)
            self.assertIn("@@Speaker", combined)
        finally:
            dlg.destroy()

    def test_guard_update_gutter_clean_intact(self):
        """Guard 1: _update_gutter_clean remains intact and updates line numbers."""
        self.assertTrue(hasattr(misora.MisoraApp, "_update_gutter_clean"))
        self.app.txt_dialogue.config(state="normal")
        self.app.txt_dialogue.delete("1.0", tk.END)
        self.app.txt_dialogue.insert("1.0", "Line 1\nLine 2\nLine 3\nLine 4")
        self.app._update_gutter_clean()
        gutter_text = self.app.gutter_clean.get("1.0", "end-1c")
        self.assertIn(" 1 ", gutter_text)
        self.assertIn(" 4 ", gutter_text)


if __name__ == "__main__":
    unittest.main()
