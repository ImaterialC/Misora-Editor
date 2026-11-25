#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S05 (v1.4.5) Verification Suite:
- Probe 1 (U-3): Speaker Cyclic Jump via dropdown menu cycles occurrences cleanly without mutation.
- Probe 2 (U-3, U-4): Speaker Entry FocusOut safeguard ignores popup listbox focus, commits only on Enter/selection/external FocusOut/flush, and enforces Translation Lock.
- Probe 3 (U-3): Google-style Speaker Autocomplete lists actors + {playername} + narration, filters live, and selects cleanly.
- Probe 4 (U02): Win32 console toggle queries IsWindowVisible(hwnd) before ShowWindow and handles hwnd=0 (pythonw.exe) without spawning a process.
- Probe 5 (U05): Modal About dialog -> SupportMeDialog sequential-frame GIF playback (single active PhotoImage, clean close), missing GIF fallback, exact Indonesian caption, PayPal URL & SHOW_PAYPAL_BUTTON toggle.
- Guard 1 (QW-B01): Clearing speaker to '' adjacent to narration keeps boxes separate.
- Guard 2 (Rule 3): About and SupportMeDialog create tk.Toplevel children of app, never a second tk.Tk().
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from PIL import Image  # noqa: E402

import misora  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402


class TestV15S05SpeakerConsoleAbout(unittest.TestCase):
    """Failing-first probes and regression guards for v1.5 S05 (v1.4.5)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s05_"))
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
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.geometry("1280x720")
        self.app.update_idletasks()
        self.app.update()

    def tearDown(self) -> None:
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _attach_doc(self, doc: StoryDocument, name: str = "s05_test.unity3d") -> Path:
        p = self.tmp_dir / name
        self.app.open_documents[p] = {"doc": doc, "plain_text": "", "dirty": False}
        self.app.current_file_path = p
        self.app.current_doc = doc
        self.app.is_box0_active = False
        self.app.current_box_idx = 0
        self.app.is_dirty = False
        self.app._update_views()
        self.app.update_idletasks()
        return p

    @staticmethod
    def _create_multi_speaker_doc() -> StoryDocument:
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Hiyori 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Line 3"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Hiyori 2"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Hiyori 3"]),
        ]
        return StoryDocument(recs)

    @staticmethod
    def _make_synthetic_gif(path: Path, frame_count: int = 4) -> Path:
        colors = [
            (220, 60, 80, 255),
            (60, 180, 90, 255),
            (70, 120, 230, 255),
            (240, 200, 60, 255),
        ]
        frames = [Image.new("RGBA", (64, 48), colors[i % len(colors)]) for i in range(frame_count)]
        frames[0].save(
            path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=50,
            loop=0,
        )
        return path

    @staticmethod
    def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
        out: list[tk.Misc] = []
        for child in widget.winfo_children():
            out.append(child)
            out.extend(TestV15S05SpeakerConsoleAbout._collect_descendants(child))
        return out

    # ------------------------------------------------------------------
    # Defect / Behavior Probes (MUST FAIL pre-patch, PASS post-patch)
    # ------------------------------------------------------------------
    def test_probe_1_speaker_jump_cycles_occurrences_and_notifies(self) -> None:
        """Probe 1 (U-3): Dropdown Jump cycles Hiyori occurrences (1->3->5->1) without mutating speakers."""
        doc = self._create_multi_speaker_doc()
        self._attach_doc(doc)

        tip = getattr(self.app.btn_speaker_dropdown, "_tooltip", None)
        self.assertIsNotNone(tip)
        self.assertIn("Jump to Speaker Box", getattr(tip, "text", ""))

        self.assertTrue(hasattr(self.app, "_jump_to_speaker"), "_jump_to_speaker must exist")

        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app._jump_to_speaker("Hiyori")
            self.assertEqual(self.app.current_box_idx, 1)
            self.assertIn("Jumped to Box #2", mock_toast.call_args[0][0])
            self.assertIn("(1/3)", mock_toast.call_args[0][0])

            self.app._jump_to_speaker("Hiyori")
            self.assertEqual(self.app.current_box_idx, 3)
            self.assertIn("Jumped to Box #4", mock_toast.call_args[0][0])
            self.assertIn("(2/3)", mock_toast.call_args[0][0])

            self.app._jump_to_speaker("Hiyori")
            self.assertEqual(self.app.current_box_idx, 5)
            self.assertIn("Jumped to Box #6", mock_toast.call_args[0][0])
            self.assertIn("(3/3)", mock_toast.call_args[0][0])

            self.app._jump_to_speaker("Hiyori")
            self.assertEqual(self.app.current_box_idx, 1)
            self.assertIn("Jumped to Box #2", mock_toast.call_args[0][0])
            self.assertIn("(1/3)", mock_toast.call_args[0][0])

        self.assertEqual(
            [b.speaker for b in doc.boxes],
            ["Pecorine", "Hiyori", "Kokkoro", "Hiyori", "", "Hiyori"],
            "Cyclic speaker jump must never mutate any speaker",
        )
        self.assertFalse(self.app.is_dirty)

    def test_probe_2_speaker_focus_into_popup_does_not_prematurely_commit_and_enforces_lock(self) -> None:
        """Probe 2 (U-3, U-4): Typing does not commit on KeyRelease; FocusOut to popup does not commit prematurely; lock blocks rename."""
        doc = self._create_multi_speaker_doc()
        self._attach_doc(doc)

        self.app.entry_speaker.focus_force()
        self.app.update()

        # Simulate typing without pressing Enter
        self.app.speaker_var.set("Hiy")
        self.app.entry_speaker.event_generate("<KeyRelease>")
        self.app.update()

        self.assertEqual(doc.boxes[0].speaker, "Pecorine", "<KeyRelease> must NOT commit speaker rename")
        popup = getattr(self.app, "_speaker_popup", None)
        listbox = getattr(self.app, "_speaker_listbox", None)
        self.assertIsNotNone(popup, "Speaker autocomplete popup must open")
        self.assertTrue(popup.winfo_exists())
        self.assertIsNotNone(listbox)

        # Move focus from entry_speaker into its popup listbox -> FocusOut must NOT commit or close popup
        listbox.focus_set()
        self.app.entry_speaker.event_generate("<FocusOut>")
        self.app.after(60, lambda: None)
        self.app.update()
        import time as _time
        _time.sleep(0.05)
        self.app.update()

        self.assertEqual(doc.boxes[0].speaker, "Pecorine", "FocusOut into autocomplete popup must NOT commit prematurely")
        self.assertTrue(popup.winfo_exists(), "Autocomplete popup must remain open when focused inside listbox")

        # Commit explicitly via Enter on entry_speaker
        self.app.entry_speaker.focus_set()
        self.app._speaker_popup_navigated = False
        self.app._on_speaker_enter(None)
        self.app.update()
        self.assertEqual(doc.boxes[0].speaker, "Hiy")
        self.assertEqual(self.app.undo_journal.undo_depth, 1)

        # Lock Box #3 (idx=2, Kokkoro) and attempt speaker rename -> must block and revert
        self.app.current_box_idx = 2
        self.app._update_views()
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(2))

        self.app.speaker_var.set("Kyaru")
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            res = self.app._commit_speaker_edit()
        self.assertFalse(res)
        self.assertEqual(doc.boxes[2].speaker, "Kokkoro")
        self.assertEqual(self.app.speaker_var.get(), "Kokkoro")
        self.assertTrue(
            any("locked" in str(call.args[0]).lower() for call in mock_toast.call_args_list),
            "Locked speaker rename must emit a clear toast notification",
        )

    def test_probe_3_speaker_autocomplete_filters_and_selects(self) -> None:
        """Probe 3 (U-3): Speaker autocomplete opens on focus/clear, lists actors+{playername}+narration, filters live, and selects."""
        doc = self._create_multi_speaker_doc()
        self._attach_doc(doc)

        self.app.entry_speaker.focus_force()
        self.app.speaker_var.set("")
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="BackSpace"))
        self.app.update()

        popup = getattr(self.app, "_speaker_popup", None)
        listbox = getattr(self.app, "_speaker_listbox", None)
        self.assertIsNotNone(popup)
        self.assertTrue(popup.winfo_exists())
        items = list(listbox.get(0, tk.END))
        self.assertTrue(any("Hiyori" in it for it in items))
        self.assertTrue(any("Kokkoro" in it for it in items))
        self.assertTrue(any("Pecorine" in it for it in items))
        self.assertIn("{playername}", items)
        self.assertTrue(any("Narration" in it for it in items))

        # Live substring filter
        self.app.speaker_var.set("kok")
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="k"))
        self.app.update()
        filtered = list(listbox.get(0, tk.END))
        self.assertEqual(filtered, ["Kokkoro"])

        # Select filtered candidate -> renames box and closes popup
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(0)
        self.app._accept_speaker_autocomplete_selection()
        self.app.update()

        self.assertEqual(doc.boxes[0].speaker, "Kokkoro")
        self.assertEqual(self.app.speaker_var.get(), "Kokkoro")
        self.assertFalse(popup.winfo_exists())

    def test_probe_4_win32_console_uses_iswindowvisible_and_handles_pythonw(self) -> None:
        """Probe 4 (U02): Win32 toggle queries IsWindowVisible before ShowWindow and handles hwnd=0 safely."""
        fake_kernel32 = MagicMock()
        fake_user32 = MagicMock()
        fake_kernel32.GetConsoleWindow.return_value = 12345
        fake_user32.IsWindowVisible.side_effect = [1, 0]
        fake_user32.ShowWindow.return_value = 1

        fake_windll = types.SimpleNamespace(kernel32=fake_kernel32, user32=fake_user32)

        with patch.object(misora.ctypes, "windll", fake_windll, create=True):
            self.app._toggle_console_shortcut()
            fake_user32.ShowWindow.assert_called_with(12345, 0)
            self.assertFalse(self.app.var_console_visible.get())

            self.app._toggle_console_shortcut()
            fake_user32.ShowWindow.assert_called_with(12345, 5)
            self.assertTrue(self.app.var_console_visible.get())

            # F12 inside an editor widget must toggle once and return "break"
            fake_user32.IsWindowVisible.side_effect = [1]
            fake_user32.ShowWindow.reset_mock()
            ev = types.SimpleNamespace(keysym="F12", state=0, widget=self.app.txt_dialogue)
            ret = self.app._on_misora_shortcut(ev)
            self.assertEqual(ret, "break")
            fake_user32.ShowWindow.assert_called_once_with(12345, 0)

        # pythonw.exe (hwnd == 0): must not crash or spawn process; emits informative toast
        fake_kernel32_zero = MagicMock()
        fake_user32_zero = MagicMock()
        fake_kernel32_zero.GetConsoleWindow.return_value = 0
        fake_windll_zero = types.SimpleNamespace(kernel32=fake_kernel32_zero, user32=fake_user32_zero)
        with patch.object(misora.ctypes, "windll", fake_windll_zero, create=True), \
             patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app._toggle_console_shortcut()
            fake_user32_zero.ShowWindow.assert_not_called()
            self.assertFalse(self.app.var_console_visible.get())
            self.assertTrue(
                any("no windows terminal console" in str(c.args[0]).lower() for c in mock_toast.call_args_list),
                "Missing console must notify user cleanly",
            )

    def test_probe_5_support_me_sequential_gif_cleanup_missing_fallback_and_paypal(self) -> None:
        """Probe 5 (U05): Modal About -> SupportMeDialog sequential GIF streaming, cleanup, missing fallback, caption & PayPal toggle."""
        # 1. Modal About dialog (must NOT use messagebox.showinfo)
        with patch.object(misora.messagebox, "showinfo") as mock_info:
            self.app.on_about()
            mock_info.assert_not_called()

        about_dlg = getattr(self.app, "_about_dialog", None)
        self.assertIsNotNone(about_dlg)
        self.assertIsInstance(about_dlg, tk.Toplevel)
        self.assertTrue(about_dlg.winfo_exists())
        about_labels = [
            w.cget("text")
            for w in self._collect_descendants(about_dlg)
            if isinstance(w, (tk.Label, tk.Button)) or w.winfo_class().endswith("Button") or w.winfo_class().endswith("Label")
        ]
        joined_about = "\n".join(str(x) for x in about_labels)
        self.assertIn("Misora: Story Editor", joined_about)
        self.assertIn(f"v{misora.__version__}", joined_about)
        self.assertIn("Support Me", joined_about)
        about_dlg.destroy()

        # 2. Sequential GIF playback on synthetic 4-frame GIF
        gif_path = self._make_synthetic_gif(self.tmp_dir / "service_test.gif", frame_count=4)
        dlg = misora.SupportMeDialog(self.app, gif_path=gif_path)
        self.app.update_idletasks()
        self.app.update()

        self.assertIsInstance(dlg, tk.Toplevel)
        self.assertFalse(hasattr(dlg, "_gif_frames"), "Must NOT retain a list of all decoded GIF frames in RAM")
        self.assertEqual(dlg._gif_frame_count, 4)
        self.assertIsNotNone(dlg._gif_image)
        self.assertIsNotNone(dlg._current_frame_photo)
        self.assertIsNotNone(dlg._gif_after_id)

        first_photo = dlg._current_frame_photo
        dlg._advance_gif_frame()
        self.assertEqual(dlg._gif_frame_idx, 1)
        self.assertIs(dlg._current_frame_photo, first_photo, "Must reuse single active PhotoImage sequentially")

        # Verify Indonesian caption & crowdfunding URLs
        desc = self._collect_descendants(dlg)
        texts = []
        for w in desc:
            try:
                texts.append(str(w.cget("text")))
            except Exception:
                pass
        all_text = "\n".join(texts)
        self.assertIn(
            "Terima kasih. Dukungan sekecil apa pun sangat saya hargai; ini juga membantu menutup biaya penggunaan AI.",
            all_text,
        )

        with patch("webbrowser.open") as mock_open:
            dlg.support_buttons["Ko-fi"].invoke()
            dlg.support_buttons["Patreon"].invoke()
            dlg.support_buttons["PayPal"].invoke()
            opened_urls = [c.args[0] for c in mock_open.call_args_list]
        self.assertEqual(
            opened_urls,
            [
                "https://ko-fi.com/imaterial",
                "https://patreon.com/imaterial",
                "https://paypal.me/CorneliaCrimson",
            ],
        )

        # Close cleanup: cancels timer, closes PIL image handle, clears PhotoImage
        pil_handle = dlg._gif_image
        dlg.close()
        self.app.update()
        self.assertIsNone(dlg._gif_after_id)
        self.assertIsNone(dlg._gif_image)
        self.assertIsNone(dlg._current_frame_photo)
        self.assertFalse(dlg.winfo_exists())
        self.assertTrue(getattr(pil_handle, "fp", None) is None)

        # 3. Missing GIF fallback (must not raise)
        dlg_missing = misora.SupportMeDialog(self.app, gif_path=self.tmp_dir / "does_not_exist.gif")
        self.app.update_idletasks()
        self.assertIsNone(dlg_missing._gif_image)
        self.assertIsNone(dlg_missing._gif_after_id)
        dlg_missing.close()

        # 4. SHOW_PAYPAL_BUTTON = False hides PayPal button cleanly
        with patch.object(misora, "SHOW_PAYPAL_BUTTON", False):
            dlg_nopaypal = misora.SupportMeDialog(self.app, gif_path=self.tmp_dir / "does_not_exist.gif")
            self.assertIn("Ko-fi", dlg_nopaypal.support_buttons)
            self.assertIn("Patreon", dlg_nopaypal.support_buttons)
            self.assertNotIn("PayPal", dlg_nopaypal.support_buttons)
            dlg_nopaypal.close()

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_clearing_speaker_keeps_adjacent_narration_separate(self) -> None:
        """Guard 1 (QW-B01): Clearing speaker to '' adjacent to narration (cmd_id=35) keeps boxes separate."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Spoken line"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Adjacent narration"]),
        ]
        doc = StoryDocument(recs)
        self._attach_doc(doc, name="guard_narration.unity3d")

        self.app.speaker_var.set("")
        committed = self.app._commit_speaker_edit()
        self.assertTrue(committed)
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].kind, "tag")
        self.assertEqual(doc.boxes[0].speaker, "")
        self.assertEqual(doc.boxes[1].kind, "tag")
        self.assertEqual(doc.boxes[1].clean_text, "Adjacent narration")

    def test_guard_2_no_second_tk_root_created(self) -> None:
        """Guard 2 (Rule 3): Opening About and Support Me creates tk.Toplevel children of app, never a second tk.Tk()."""
        root_before = tk._default_root
        self.app.on_about()
        about_dlg = getattr(self.app, "_about_dialog", None)
        if about_dlg is not None and about_dlg.winfo_exists():
            self.assertIsInstance(about_dlg, tk.Toplevel)
            self.assertIs(about_dlg.master, self.app)
            about_dlg.destroy()

        if hasattr(misora, "SupportMeDialog"):
            dlg = misora.SupportMeDialog(self.app, gif_path=self.tmp_dir / "absent.gif")
            self.assertIsInstance(dlg, tk.Toplevel)
            self.assertIs(dlg.master, self.app)
            dlg.close()

        self.assertIs(tk._default_root, root_before)


if __name__ == "__main__":
    unittest.main()
