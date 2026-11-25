"""Test Suite for Misora Editor Session S15: Selection, Left Drawer, Empty State & Multi-Open.

Scope: BUG-41, FEAT-05, FEAT-06, FEAT-07 (Track 2 - Group G2).
Failing-first defect probes:
- Probe 1: BUG-41 & FEAT-05 (Select Box in Dialogue view, Card #0 checkbox, reserved lock slot)
- Probe 2: FEAT-06 (Clean collapsible left drawer via h_paned, zero place() overlay)
- Probe 3: FEAT-07 (Empty state with 0 docs, btn_tab_files double-click, batched askopenfilenames)
Regression guard:
- Guard 1: Direct assertions for paned minsize, widget flush, and core contracts
"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import misora
from misora import MisoraApp
from core import Box, StoryDocument


class TestP3S15SelectionDrawerOpen(unittest.TestCase):
    """Test suite covering S15 defect probes and regression guards."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.tmp_config = self.tmp_path / "misora_config.json"
        self.tmp_backup_dir = self.tmp_path / "backups"
        self.tmp_backup_dir.mkdir(parents=True, exist_ok=True)

        self._orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_config

        # Suppress modal dialog popups during automated tests
        self._patch_info = mock.patch("tkinter.messagebox.showinfo")
        self._patch_warn = mock.patch("tkinter.messagebox.showwarning")
        self._patch_err = mock.patch("tkinter.messagebox.showerror")
        self._patch_askyesno = mock.patch("tkinter.messagebox.askyesno", return_value=False)
        self._patch_askyesnocancel = mock.patch("tkinter.messagebox.askyesnocancel", return_value=False)

        self._patch_info.start()
        self._patch_warn.start()
        self._patch_err.start()
        self._patch_askyesno.start()
        self._patch_askyesnocancel.start()

        self.app = None

    def tearDown(self) -> None:
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None

        misora.CONFIG_PATH = self._orig_config_path

        self._patch_info.stop()
        self._patch_warn.stop()
        self._patch_err.stop()
        self._patch_askyesno.stop()
        self._patch_askyesnocancel.stop()

        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # DEFECT PROBE 1: BUG-41 & FEAT-05
    # -------------------------------------------------------------------------
    def test_probe_1_bug41_feat05_select_box_both_views_and_reserved_slot(self) -> None:
        """Probe 1: Select Box works in Dialogue view, Card #0 has checkbox, lock slot is fixed width."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_backup_dir)

        # Setup dummy 3-box document with metadata
        doc = StoryDocument()
        doc.set_metadata("Ep 1", "Sub 1", "Synopsis")
        doc.insert_box(0, {"speaker": "Peco", "clean_text": "Hello world!"})
        doc.insert_box(1, {"speaker": "Kokkoro", "clean_text": "Lord Aruji."})
        doc.insert_box(2, {"speaker": "Kyaru", "clean_text": "What are you doing?!"})

        self.app.current_doc = doc
        self.app.var_continuous_view.set(False)  # Dialogue view
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.update()

        # Part 1: Dialogue View Select Box
        # Checkbox widget must exist
        self.assertTrue(
            hasattr(self.app, "cb_dialogue_select"),
            "cb_dialogue_select widget must exist in Dialogue view header"
        )

        # Toggle Select Box Mode ON
        self.app.var_select_box_mode.set(True)
        self.app._on_toggle_select_box_mode()
        self.app.update()

        self.assertTrue(
            self.app.cb_dialogue_select.winfo_ismapped(),
            "cb_dialogue_select must be visible in Dialogue view when Select Box mode is active"
        )
        cb_text = self.app.cb_dialogue_select.cget("text")
        self.assertIn("Select Box #1", cb_text)
        self.assertIn("0 selected", cb_text)

        # Check Box 1
        self.app.var_dialogue_box_sel.set(True)
        self.app._on_dialogue_box_sel_toggle()
        self.assertIn(0, self.app._selected_boxes)

        # Step to Box 3
        self.app.current_box_idx = 2
        self.app._update_views()
        self.app.update()

        cb_text3 = self.app.cb_dialogue_select.cget("text")
        self.assertIn("Select Box #3", cb_text3)
        self.assertIn("1 selected", cb_text3)

        # Check Box 3
        self.app.var_dialogue_box_sel.set(True)
        self.app._on_dialogue_box_sel_toggle()
        self.assertEqual(
            self.app._selected_boxes, {0, 2},
            "Checking Box 1 and Box 3 in Dialogue view must yield _selected_boxes == {0, 2}"
        )

        # Part 2: All Script (Technique A) Box #0 inline Select Box & Reserved Lock Slot
        self.app.var_continuous_view.set(True)
        self.app._update_views()
        self.app.update()

        # Box #0 (-1) must have inline Select Box slot in txt_all_script
        self.assertIn(-1, self.app._all_script_block_ranges, "Box #0 must be present in All Script block map")
        self.assertIn(-1, self.app._all_script_sel_ranges, "Box #0 must have inline Select Box slot")

        # Check Box 1 lock glyph horizontal position with Select Box ON
        self.assertIn(0, self.app._all_script_lock_ranges, "Box 1 must have inline lock slot registered")
        lock_s_on, _ = self.app._all_script_lock_ranges[0]
        sel_s_on, _ = self.app._all_script_sel_ranges[0]
        self.app.txt_all_script.see(lock_s_on)
        self.app.update()
        lock_bbox_on = self.app.txt_all_script.bbox(lock_s_on)
        self.assertIsNotNone(lock_bbox_on, "Lock glyph must be visible")
        lock_x_on = lock_bbox_on[0]
        self.assertGreater(lock_x_on, 0, "Lock glyph must have positive x coordinate")

        # Toggle Select Box Mode OFF
        self.app.var_select_box_mode.set(False)
        self.app._on_toggle_select_box_mode()
        self.app.update()

        lock_s_off, _ = self.app._all_script_lock_ranges[0]
        sel_s_off, _ = self.app._all_script_sel_ranges[0]
        lock_bbox_off = self.app.txt_all_script.bbox(lock_s_off)
        sel_bbox_off = self.app.txt_all_script.bbox(sel_s_off)
        self.assertIsNotNone(lock_bbox_off)
        self.assertIsNotNone(sel_bbox_off)
        lock_x_off = lock_bbox_off[0]

        # Both x coordinates must be strictly equal (zero horizontal shifting)
        self.assertEqual(
            lock_x_on, lock_x_off,
            f"Lock icon horizontal position must not shift when Select Box mode toggles! (ON: {lock_x_on}, OFF: {lock_x_off})"
        )
        # Verify lock icon sits to the right of checkbox slot
        self.assertGreater(
            lock_x_off, sel_bbox_off[0],
            f"Lock icon (x={lock_x_off}) must sit right of checkbox slot (x={sel_bbox_off[0]})"
        )

    # -------------------------------------------------------------------------
    # DEFECT PROBE 2: FEAT-06
    # -------------------------------------------------------------------------
    def test_probe_2_feat06_collapsible_left_drawer(self) -> None:
        """Probe 2: Left drawer collapses/expands cleanly via h_paned without place() overlay."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_backup_dir)
        self.app.update()

        # Initial expanded state
        self.assertFalse(getattr(self.app, "_dock_collapsed", False))
        init_w = self.app.left_frame.winfo_width()
        self.assertGreaterEqual(init_w, 160)

        # Collapse dock
        self.app._toggle_dock_collapse()
        self.app.update()

        self.assertTrue(getattr(self.app, "_dock_collapsed", False), "Dock state should be collapsed")
        collapsed_w = self.app.left_frame.winfo_width()
        self.assertLessEqual(collapsed_w, 50, f"Collapsed dock width should be <= 50px, got {collapsed_w}")

        # In collapsed state, pin/expand button MUST be visible inside collapsed frame (x < 36)
        pin_x = self.app.btn_dock_pin.winfo_x()
        self.assertLess(
            pin_x, 36,
            f"btn_dock_pin must be visible at x < 36 inside collapsed width, got x={pin_x}"
        )
        self.assertEqual(
            self.app.btn_dock_pin.cget("text"), "▶",
            "btn_dock_pin text should be '▶' when collapsed"
        )

        # Verify NO place() overlay was used
        self.assertEqual(
            self.app.left_frame.place_info(), {},
            "left_frame must strictly use h_paned management, NEVER place() overlay"
        )

        # Expand dock back
        self.app._toggle_dock_collapse()
        self.app.update()

        self.assertFalse(getattr(self.app, "_dock_collapsed", False), "Dock state should be expanded")
        expanded_w = self.app.left_frame.winfo_width()
        self.assertGreaterEqual(expanded_w, 150, "Expanded dock width must be restored")
        self.assertEqual(
            self.app.btn_dock_pin.cget("text"), "📌",
            "btn_dock_pin text should be '📌' when expanded"
        )

    # -------------------------------------------------------------------------
    # DEFECT PROBE 3: FEAT-07
    # -------------------------------------------------------------------------
    def test_probe_3_feat07_empty_state_and_batched_multi_open(self) -> None:
        """Probe 3: Empty state with 0 open docs, btn_tab_files double-click, and batched askopenfilenames."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_backup_dir)

        # Ensure 0 open documents
        self.app.open_documents.clear()
        self.app.current_doc = None
        self.app.current_file_path = None
        self.app._update_views()
        self.app.update()

        # Part 1: Empty state frame and Open Files button
        self.assertTrue(
            hasattr(self.app, "empty_state_frame"),
            "empty_state_frame must exist on app"
        )
        self.assertTrue(
            self.app.empty_state_frame.winfo_ismapped(),
            "empty_state_frame must be visible when 0 documents are open"
        )
        self.assertTrue(
            hasattr(self.app, "btn_empty_open"),
            "btn_empty_open must exist on empty_state_frame"
        )

        # Open a document -> empty state hides
        f1 = self.tmp_path / "test1.txt"
        f1.write_text("Dialogue line 1", encoding="utf-8")
        self.app.open_file(f1)
        self.app.update()

        self.assertFalse(
            self.app.empty_state_frame.winfo_ismapped(),
            "empty_state_frame must hide when at least 1 document is open"
        )

        # Part 2: Double-click on Opened Files tab invokes on_open_file
        opened_flag = []
        dbl_cmd = self.app.btn_tab_files.bind("<Double-Button-1>")
        self.assertTrue(dbl_cmd, "btn_tab_files must have <Double-Button-1> binding")
        with mock.patch.object(self.app, "on_open_file", side_effect=lambda: opened_flag.append(True)):
            self.app.btn_tab_files.event_generate("<ButtonPress-1>", x=5, y=5)
            self.app.btn_tab_files.event_generate("<ButtonRelease-1>", x=5, y=5)
            self.app.btn_tab_files.event_generate("<ButtonPress-1>", x=5, y=5)
            self.app.btn_tab_files.event_generate("<ButtonRelease-1>", x=5, y=5)
            self.app.update()
        self.assertTrue(
            opened_flag,
            "Double-clicking btn_tab_files must invoke on_open_file"
        )

        # Part 3: Batched askopenfilenames triggers ONE _update_views call
        f2 = self.tmp_path / "test2.txt"
        f3 = self.tmp_path / "test3.txt"
        f2.write_text("Dialogue line 2", encoding="utf-8")
        f3.write_text("Dialogue line 3", encoding="utf-8")

        update_calls = []
        orig_update_views = self.app._update_views

        def tracked_update_views():
            update_calls.append(True)
            return orig_update_views()

        with mock.patch("tkinter.filedialog.askopenfilenames", return_value=(str(f1), str(f2), str(f3))), \
             mock.patch.object(self.app, "_update_views", side_effect=tracked_update_views):
            self.app.on_open_file()

        self.assertEqual(
            len(update_calls), 1,
            f"Batched askopenfilenames must trigger exactly 1 _update_views() call, got {len(update_calls)}"
        )
        self.assertIn(f1.resolve(), self.app.open_documents)
        self.assertIn(f2.resolve(), self.app.open_documents)
        self.assertIn(f3.resolve(), self.app.open_documents)

    # -------------------------------------------------------------------------
    # REGRESSION GUARD 1
    # -------------------------------------------------------------------------
    def test_guard_1_core_invariants_and_dialogue_commit(self) -> None:
        """Guard 1: Direct assertions on paned minsize, widget flush, and core contracts."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_backup_dir)
        self.app.update()

        # Check paned window minsize invariants
        left_minsize = int(self.app.h_paned.panecget(self.app.left_frame, "minsize"))
        self.assertGreaterEqual(left_minsize, 160)

        panes = self.app.h_paned.panes()
        self.assertGreaterEqual(len(panes), 2)
        right_frame = self.app.nametowidget(panes[1])
        right_minsize = int(self.app.h_paned.panecget(right_frame, "minsize"))
        self.assertGreaterEqual(right_minsize, 400)

        v_panes = self.app.v_paned.panes()
        self.assertGreaterEqual(len(v_panes), 2)
        top_view = self.app.nametowidget(v_panes[0])
        bottom_view = self.app.nametowidget(v_panes[1])
        top_minsize = int(self.app.v_paned.panecget(top_view, "minsize"))
        bottom_minsize = int(self.app.v_paned.panecget(bottom_view, "minsize"))
        self.assertGreaterEqual(top_minsize, 120)
        self.assertGreaterEqual(bottom_minsize, 80)

        # Check _flush_active_widget executes cleanly without exception
        self.assertTrue(self.app._flush_active_widget())


if __name__ == "__main__":
    unittest.main()
