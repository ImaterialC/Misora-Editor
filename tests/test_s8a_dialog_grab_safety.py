"""
S8a — Dialog Architecture & Modal Grab Hardening
================================================
TDD tests verifying:
  - safe_grab_release() helper safely releases grabs on active, destroyed, and None dialogs without exceptions.
  - All Toplevel dialogs have explicit parent transients.
  - Modal dialogs (grab_set) register WM_DELETE_WINDOW protocol to cleanly release grab on window close.
  - Modal dialogs bind <Escape> for keyboard dismissal and grab release.
  - Tk variables instantiated inside dialogs specify master=dlg (Rule 3).
  - BatchTranslateDialog WM_DELETE_WINDOW cancels background worker thread and releases modal grab.
"""

import ast
import inspect
import sys
import tempfile
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch, MagicMock

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from misora import (  # noqa: E402
    safe_grab_release,
    MTLSettingsDialog,
    AIPromptSettingsDialog,
    BatchTranslateDialog,
    TranslatorAssistantDialog,
    ScriptPastePreviewDialog,
)
from core.script_codec import parse  # noqa: E402


def _assert_tk_vars_specify_master(test_case: unittest.TestCase, cls_or_fn) -> None:
    """Verify via AST analysis that every Tk variable explicitly passes master= (Rule 3)."""
    source = inspect.getsource(cls_or_fn)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if func_name in ("StringVar", "BooleanVar", "DoubleVar", "IntVar"):
                has_master = any(kw.arg == "master" for kw in node.keywords) or len(node.args) > 0
                test_case.assertTrue(
                    has_master,
                    f"Tk variable '{func_name}' at line {node.lineno} in {getattr(cls_or_fn, '__name__', str(cls_or_fn))} violates Rule 3 (missing master=)"
                )


def _trigger_binding(widget: tk.Widget, sequence: str) -> None:
    """Execute the callback bound to a key sequence deterministically in headless environments."""
    script = widget.bind(sequence)
    if not script:
        raise ValueError(f"No binding found for {sequence} on {widget}")
    cmd = script.strip()
    if "[" in cmd:
        cmd = cmd.split("[", 1)[1].split()[0]
    widget.tk.call(cmd)


class S8aTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s8a_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warning = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_error = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warning.start()
        cls.patch_error.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warning.stop()
        cls.patch_error.stop()
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        with patch.object(misora, "CONFIG_PATH", self.config_path):
            self.app = misora.MisoraApp()
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        try:
            # Dismiss any leftover toplevels before destroying app
            for child in list(self.app.children.values()):
                if isinstance(child, tk.Toplevel) and child.winfo_exists():
                    safe_grab_release(child)
                    child.destroy()
            self.app.destroy()
        except Exception:
            pass

    def _find_toplevel_dialog(self, title_substr: str = "") -> tk.Toplevel:
        """Find the child Toplevel matching title_substr."""
        for child in self.app.children.values():
            if isinstance(child, tk.Toplevel) and child.winfo_exists():
                if not title_substr or title_substr.lower() in child.title().lower():
                    return child
        return None


class TestS8aDialogGrabSafety(S8aTestBase):
    """S8a Dialog Architecture & Modal Grab Hardening Tests."""

    def test_01_safe_grab_release_helper(self):
        """safe_grab_release() safely handles None, destroyed widgets, and active grabs."""
        # None argument
        safe_grab_release(None)

        # Active grab
        top = tk.Toplevel(self.app)
        top.grab_set()
        self.assertEqual(self.app.grab_current(), top)
        safe_grab_release(top)
        self.assertIsNone(self.app.grab_current(), "Grab must be released")

        # Destroyed widget
        top.destroy()
        safe_grab_release(top)  # Must not raise on destroyed widget

    def test_02_dnd_settings_dialog_grab_and_protocols(self):
        """Drag & Drop settings dialog has transient, grab release, WM_DELETE_WINDOW, and Escape."""
        self.app._on_dnd_settings_dialog()
        dlg = self._find_toplevel_dialog("Drag & Drop")
        self.assertIsNotNone(dlg, "DnD settings dialog must be created")

        # Check transient parent
        self.assertEqual(str(dlg.transient()), str(self.app))

        # Check WM_DELETE_WINDOW registered
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")

        # Check Escape binding
        self.assertTrue(bool(dlg.bind("<Escape>")), "Escape must be bound")

        # Check grab was set
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger WM_DELETE_WINDOW protocol
        self.app.tk.eval(wm_del)
        self.assertIsNone(self.app.grab_current(), "Grab must be released after WM_DELETE_WINDOW")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed after WM_DELETE_WINDOW")

    def test_03_append_speaker_attribute_dialog_grab_and_escape(self):
        """Append Speaker Attribute dialog has grab release, WM_DELETE_WINDOW, and Escape."""
        self.app._prompt_append_speaker_attribute()
        dlg = self._find_toplevel_dialog("Append Speaker Attribute")
        self.assertIsNotNone(dlg, "Append Speaker Attribute dialog must be created")

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger Escape via registered binding
        _trigger_binding(dlg, "<Escape>")

        self.assertIsNone(self.app.grab_current(), "Grab must be released after Escape")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed after Escape")

    def test_04_insert_ruby_dialog_grab_and_wm_delete(self):
        """Insert Ruby dialog has grab release, WM_DELETE_WINDOW, and Escape."""
        self.app.on_insert_ruby()
        dlg = self._find_toplevel_dialog("Ruby")
        self.assertIsNotNone(dlg, "Insert Ruby dialog must be created")

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertTrue(bool(dlg.bind("<Escape>")), "Escape must be bound")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger WM_DELETE_WINDOW
        self.app.tk.eval(wm_del)
        self.assertIsNone(self.app.grab_current(), "Grab must be released after WM_DELETE_WINDOW")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed after WM_DELETE_WINDOW")

    def test_05_paths_dialog_grab_and_escape(self):
        """Configure Paths dialog has grab release, WM_DELETE_WINDOW, and Escape."""
        self.app.on_open_paths_dialog()
        dlg = self._find_toplevel_dialog("Configure Paths")
        self.assertIsNotNone(dlg, "Paths dialog must be created")

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger Escape via registered binding
        _trigger_binding(dlg, "<Escape>")

        self.assertIsNone(self.app.grab_current(), "Grab must be released after Escape")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed after Escape")

    def test_06_script_paste_preview_dialog_escape_and_wm_delete(self):
        """ScriptPastePreviewDialog has grab release, WM_DELETE_WINDOW, and Escape."""
        sample_csif = "@@Peco\nDelicious rice balls!"
        parsed = parse(sample_csif)
        dlg = ScriptPastePreviewDialog(self.app, parsed, start_idx=0)

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertTrue(bool(dlg.bind("<Escape>")), "Escape must be bound")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger WM_DELETE_WINDOW
        self.app.tk.eval(wm_del)
        self.assertFalse(dlg.confirmed, "confirmed must be False on cancel")
        self.assertIsNone(self.app.grab_current(), "Grab must be released")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed")

    def test_07_mtl_settings_dialog_vars_and_escape(self):
        """MTLSettingsDialog Tk variables specify master=self; Escape releases grab."""
        _assert_tk_vars_specify_master(self, MTLSettingsDialog)
        dlg = MTLSettingsDialog(self.app)

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger Escape via registered binding
        _trigger_binding(dlg, "<Escape>")

        self.assertIsNone(self.app.grab_current(), "Grab must be released")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed")

    def test_08_ai_prompt_settings_dialog_vars_and_escape(self):
        """AIPromptSettingsDialog Tk variables specify master=self; Escape releases grab."""
        _assert_tk_vars_specify_master(self, AIPromptSettingsDialog)
        dlg = AIPromptSettingsDialog(self.app)

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger Escape via registered binding
        _trigger_binding(dlg, "<Escape>")

        self.assertIsNone(self.app.grab_current(), "Grab must be released")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed")

    def test_09_translator_assistant_dialog_escape(self):
        """TranslatorAssistantDialog binds Escape to _on_close()."""
        _assert_tk_vars_specify_master(self, TranslatorAssistantDialog)
        dlg = TranslatorAssistantDialog(self.app)
        self.assertEqual(str(dlg.transient()), str(self.app))
        self.app._translator_dialog = dlg

        # Trigger Escape via registered binding
        _trigger_binding(dlg, "<Escape>")

        self.assertIsNone(self.app._translator_dialog, "Assistant dialog reference must be cleared")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed")

    def test_10_batch_translate_dialog_wm_delete_and_vars(self):
        """BatchTranslateDialog registers WM_DELETE_WINDOW, binds Escape, and owns its Tk vars."""
        _assert_tk_vars_specify_master(self, BatchTranslateDialog)
        dlg = BatchTranslateDialog(self.app)

        self.assertEqual(str(dlg.transient()), str(self.app))
        wm_del = dlg.protocol("WM_DELETE_WINDOW")
        self.assertTrue(bool(wm_del), "WM_DELETE_WINDOW must be registered")
        self.assertTrue(bool(dlg.bind("<Escape>")), "Escape must be bound")
        self.assertEqual(self.app.grab_current(), dlg)

        # Trigger WM_DELETE_WINDOW
        self.app.tk.eval(wm_del)
        self.assertIsNone(self.app.grab_current(), "Grab must be released")
        self.assertFalse(dlg.winfo_exists(), "Dialog must be destroyed")


if __name__ == "__main__":
    unittest.main()
