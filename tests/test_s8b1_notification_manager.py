"""
S8b-1 — Status-Bar & Toast Notification Manager Tests
=====================================================
TDD tests verifying:
  - set_status() updates lbl_status text, handles contrast & error styling, and supports auto-reset timeouts.
  - show_toast() renders visual toasts with backward-compatible signatures and syncs to status bar.
  - Sequential toast queueing prevents message clobbering during rapid operations.
  - Duplicate toast coalescing refreshes timer rather than creating redundant queue backlog.
  - Interactive click-to-dismiss (<Button-1>) dismisses active toast immediately.
  - report_callback_exception() surfaces both status-bar error and prominent visual toast (Rule 28).
  - Toast geometry hovers cleanly above the action bar without occluding primary Save buttons.
  - Calling destroy() cleanly cancels all pending after() timers and clears queues.
"""

import re
import tempfile
import time
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
import sys
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402


class S8b1TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s8b1_test_"))
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
            self.app.destroy()
        except Exception:
            pass


class TestS8b1NotificationManager(S8b1TestBase):
    """S8b-1 Notification & Status Manager Tests."""

    def test_01_set_status_updates_label_and_contrast(self):
        """set_status() updates lbl_status text and applies proper styling for normal vs error."""
        self.app.set_status("Operation completed normally", is_error=False)
        self.assertEqual(self.app.lbl_status.cget("text"), "Operation completed normally")
        normal_fg = self.app.lbl_status.cget("fg")

        self.app.set_status("Fatal error occurred", is_error=True)
        self.assertEqual(self.app.lbl_status.cget("text"), "Fatal error occurred")
        error_fg = self.app.lbl_status.cget("fg")

        self.assertNotEqual(normal_fg, error_fg, "Error status must have distinctive styling/contrast")

    def test_02_set_status_timeout_auto_reset(self):
        """set_status() with timeout_ms automatically reverts to default status."""
        default_text = getattr(self.app, "_default_status_text", "Ready. Drag & Drop or open a .unity3d bundle or folder to begin.")
        self.app.set_status("Temporary warning", is_error=False, timeout_ms=50)
        self.assertEqual(self.app.lbl_status.cget("text"), "Temporary warning")

        # Let the after callback fire
        time.sleep(0.08)
        self.app.update()

        self.assertEqual(self.app.lbl_status.cget("text"), default_text)

    def test_03_show_toast_basic_display_and_dismissal(self):
        """show_toast() creates/displays the toast widget, and _dismiss_toast() hides it."""
        self.app.show_toast("Story saved successfully")
        self.assertTrue(hasattr(self.app, "_toast_widget"))
        self.assertTrue(self.app._toast_widget.winfo_exists())
        self.assertIn("Story saved successfully", self.app._toast_widget.cget("text"))
        self.assertTrue(bool(self.app._toast_widget.winfo_ismapped() or self.app._toast_widget.place_info()))

        # Dismiss
        self.app._dismiss_toast()
        self.assertEqual(self.app._toast_widget.place_info(), {}, "Toast widget must be unmapped after dismiss")

    def test_04_show_toast_syncs_status_bar(self):
        """show_toast() synchronizes to lbl_status when status_bar=True."""
        self.app.show_toast("Exported 15 boxes", status_bar=True)
        self.assertEqual(self.app.lbl_status.cget("text"), "Exported 15 boxes")

        self.app.lbl_status.config(text="Pre-existing status")
        self.app.show_toast("Quiet toast", status_bar=False)
        self.assertEqual(self.app.lbl_status.cget("text"), "Pre-existing status", "status_bar=False must not clobber status bar")

    def test_05_toast_queue_sequential_processing(self):
        """Rapid toasts queue and process in sequence without clobbering."""
        self.app.show_toast("Message 1", duration_ms=2000)
        self.app.show_toast("Message 2", duration_ms=2000)
        self.app.show_toast("Message 3", duration_ms=2000)

        # Message 1 is active; 2 and 3 should be in queue
        self.assertIn("Message 1", self.app._toast_widget.cget("text"))
        self.assertEqual(len(self.app._toast_queue), 2)

        # Dismiss Message 1 -> Message 2 should immediately show
        self.app._dismiss_toast()
        self.assertIn("Message 2", self.app._toast_widget.cget("text"))
        self.assertEqual(len(self.app._toast_queue), 1)

        # Dismiss Message 2 -> Message 3 should show
        self.app._dismiss_toast()
        self.assertIn("Message 3", self.app._toast_widget.cget("text"))
        self.assertEqual(len(self.app._toast_queue), 0)

    def test_06_toast_click_to_dismiss(self):
        """Clicking on toast (<Button-1>) dismisses it immediately."""
        self.app.show_toast("Click to dismiss this notification")
        self.assertTrue(bool(self.app._toast_widget.place_info()))

        # Trigger <Button-1> (via headless-safe binding invocation)
        raw_binding = self.app._toast_widget.bind("<Button-1>")
        self.assertTrue(bool(raw_binding), "<Button-1> must be bound to toast widget")
        match = re.search(r'\[(\S+)', raw_binding)
        if match:
            self.app._toast_widget.tk.call(match.group(1))
        else:
            self.app._toast_widget.event_generate("<Button-1>")
        self.app.update()

        self.assertEqual(self.app._toast_widget.place_info(), {}, "Toast must be unmapped after click")

    def test_07_report_callback_exception_surfaces_toast_and_status(self):
        """report_callback_exception() surfaces both a status-bar error and a visual toast (Rule 28)."""
        err_val = RuntimeError("Simulated UI failure in ribbon button")
        self.app.report_callback_exception(RuntimeError, err_val, None)

        # Verify status bar updated
        status_text = self.app.lbl_status.cget("text")
        self.assertIn("Simulated UI failure in ribbon button", status_text)
        self.assertTrue(status_text.startswith("Error:"), "Status text must indicate Error")

        # Verify toast displayed with error styling
        self.assertTrue(hasattr(self.app, "_toast_widget"))
        self.assertIn("Simulated UI failure in ribbon button", self.app._toast_widget.cget("text"))

    def test_08_toast_geometry_above_action_bar(self):
        """Toast placement coordinates position it above the action bar."""
        self.app.show_toast("Testing geometry layout")
        p_info = self.app._toast_widget.place_info()

        # Toast must be placed anchored to south-east
        self.assertEqual(p_info.get("anchor"), "se")

        # If y offset or rely is configured, verify it provides vertical clearance from bottom
        y_val = p_info.get("y", "")
        rely_val = p_info.get("rely", "")
        # Either rely is < 1.0 (e.g. 0.92) or y is negative offset from bottom (e.g. -50)
        has_clearance = (rely_val and float(rely_val) < 0.95) or (y_val and int(y_val) < -30)
        self.assertTrue(has_clearance, f"Toast placement {p_info} must clear action bar buttons")

    def test_09_destroy_cancels_all_timers_cleanly(self):
        """Calling destroy() cancels all pending after() jobs without errors."""
        self.app.show_toast("Will be interrupted by destroy", duration_ms=5000)
        self.app.set_status("Temporary", timeout_ms=5000)

        # Check timers were registered
        self.assertIsNotNone(self.app._toast_after_id)
        self.assertIsNotNone(self.app._status_after_id)

        # Destroy app
        self.app.destroy()

        # All timer references must be cleared and queue empty
        self.assertIsNone(self.app._toast_after_id)
        self.assertIsNone(self.app._status_after_id)
        self.assertEqual(len(self.app._toast_queue), 0)

    def test_10_coalesce_duplicate_toasts(self):
        """Firing identical toast repeatedly refreshes duration instead of building queue backlog."""
        self.app.show_toast("Identical message", duration_ms=2000)
        first_after_id = self.app._toast_after_id

        # Fire same message again
        self.app.show_toast("Identical message", duration_ms=2000)
        second_after_id = self.app._toast_after_id

        # Queue should NOT have a duplicate item
        self.assertEqual(len(self.app._toast_queue), 0, "Duplicate toast should be coalesced, not queued")
        # Timer should be refreshed
        self.assertNotEqual(first_after_id, second_after_id, "Timer should be refreshed on coalesce")


if __name__ == "__main__":
    unittest.main()
