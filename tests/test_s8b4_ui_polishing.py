#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_s8b4_ui_polishing.py
===============================
Verification test suite for S8b-4 (Remaining UI Polishing & Responsive Scaling):
- Rule 23: Process DPI awareness initialization once at startup; no runtime mutation.
- Paned-window minsize constraints and responsive dock collapse toggle cycle.
- Rule 21: Icon-only controls have text fallbacks and accessible tooltips.
- Theme contrast safety via best_contrast_fg().
- Side drawer responsive constraints.
"""

import ast
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora
from misora import (
    MisoraApp,
    ToolTip,
    best_contrast_fg,
    init_process_dpi_awareness,
)


class TestS8b4UIPolishing(unittest.TestCase):
    """Test suite for S8b-4 UI polishing, responsive scaling, and DPI stability."""

    def setUp(self):
        # Isolate config path and backups folder
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s8b4_test_"))
        self.tmp_config = self.tmp_dir / "tmp_s8b4_config.json"
        self.orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_config
        self.app = None

    def tearDown(self):
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None
        misora.CONFIG_PATH = self.orig_config_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_dpi_startup_helper_callable(self):
        """init_process_dpi_awareness() should execute safely and idempotently."""
        # Should not raise any exception on any OS
        try:
            init_process_dpi_awareness()
        except Exception as e:
            self.fail(f"init_process_dpi_awareness() raised unexpected exception: {e}")

    def test_02_ast_eyedropper_no_runtime_dpi_mutation(self):
        """AST check: NguiColorPickerPopup must contain zero runtime DPI mutations (Rule 23)."""
        misora_path = REPO_ROOT / "misora.py"
        with open(misora_path, "r", encoding="utf-8") as f:
            source = f.read()

        parsed = ast.parse(source, filename=str(misora_path))

        # Find NguiColorPickerPopup class
        color_picker_node = None
        for node in ast.walk(parsed):
            if isinstance(node, ast.ClassDef) and node.name == "NguiColorPickerPopup":
                color_picker_node = node
                break

        self.assertIsNotNone(color_picker_node, "NguiColorPickerPopup class not found in misora.py")

        # Inspect all calls within NguiColorPickerPopup
        runtime_dpi_calls = []
        for child in ast.walk(color_picker_node):
            if isinstance(child, ast.Call):
                call_src = ast.unparse(child)
                if any(k in call_src.lower() for k in ["setprocessdpiawareness", "setprocessdpiaware"]):
                    runtime_dpi_calls.append(call_src)

        self.assertEqual(
            runtime_dpi_calls,
            [],
            f"Rule 23 violation: NguiColorPickerPopup contains runtime DPI awareness mutation: {runtime_dpi_calls}",
        )

    def test_03_paned_window_minsizes(self):
        """PanedWindow panes must have enforced minsize constraints to prevent collapse."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        # Check horizontal paned window
        left_minsize = int(self.app.h_paned.panecget(self.app.left_frame, "minsize"))
        self.assertGreaterEqual(left_minsize, 160, "Left dock minsize must be at least 160px")

        # Find right frame in h_paned
        panes = self.app.h_paned.panes()
        self.assertGreaterEqual(len(panes), 2, "h_paned must have at least 2 panes")
        right_frame = self.app.nametowidget(panes[1])
        right_minsize = int(self.app.h_paned.panecget(right_frame, "minsize"))
        self.assertGreaterEqual(right_minsize, 400, "Right editor frame minsize must be at least 400px")

        # Check vertical paned window
        v_panes = self.app.v_paned.panes()
        self.assertGreaterEqual(len(v_panes), 2, "v_paned must have at least 2 panes")
        top_view = self.app.nametowidget(v_panes[0])
        bottom_view = self.app.nametowidget(v_panes[1])
        top_minsize = int(self.app.v_paned.panecget(top_view, "minsize"))
        bottom_minsize = int(self.app.v_paned.panecget(bottom_view, "minsize"))
        self.assertGreaterEqual(top_minsize, 120, "Top game view minsize must be at least 120px")
        self.assertGreaterEqual(bottom_minsize, 80, "Bottom raw script minsize must be at least 80px")

    def test_04_dock_collapse_toggle_cycle(self):
        """_toggle_dock_collapse() must toggle cleanly between collapsed and expanded states."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        orig_w = self.app.left_frame.winfo_width()
        self.assertGreaterEqual(orig_w, 160, "Initial dock width must be >= 160px")
        self.assertFalse(getattr(self.app, "_dock_collapsed", False))

        # Collapse dock (true 0px via h_paned.forget)
        self.app._toggle_dock_collapse()
        self.app.update()

        self.assertTrue(getattr(self.app, "_dock_collapsed", False), "Dock state should be collapsed")
        self.assertNotIn(str(self.app.left_frame), [str(p) for p in self.app.h_paned.panes()], "Collapsed dock must be forgotten from h_paned")
        self.assertNotEqual(self.app.btn_reopen_left.winfo_manager(), "", "Reopen button must be visible when collapsed")

        # Expand dock
        self.app._toggle_dock_collapse()
        self.app.update()

        self.assertFalse(getattr(self.app, "_dock_collapsed", False), "Dock state should be expanded")
        self.assertIn(str(self.app.left_frame), [str(p) for p in self.app.h_paned.panes()], "Expanded dock must be restored to h_paned")
        self.assertEqual(self.app.btn_reopen_left.winfo_manager(), "", "Reopen button must be hidden when expanded")
        expanded_minsize = int(self.app.h_paned.panecget(self.app.left_frame, "minsize"))
        self.assertGreaterEqual(expanded_minsize, 160, "Expanded dock minsize should be >= 160px")
        expanded_w = self.app.left_frame.winfo_width()
        self.assertGreaterEqual(expanded_w, 150, f"Expanded dock width should be restored, got {expanded_w}")

    def test_05_icon_buttons_fallback_text(self):
        """All icon-only buttons must specify non-empty fallback text (Rule 21)."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        # Check ribbon & toolbar action buttons
        buttons_to_check = [
            ("btn_sel_story", getattr(self.app, "btn_sel_story", None)),
            ("btn_cut", getattr(self.app, "btn_cut", None)),
            ("btn_copy", getattr(self.app, "btn_copy", None)),
            ("btn_paste", getattr(self.app, "btn_paste", None)),
            ("btn_box_new", getattr(self.app, "btn_box_new", None)),
            ("btn_box_cut", getattr(self.app, "btn_box_cut", None)),
            ("btn_box_copy", getattr(self.app, "btn_box_copy", None)),
            ("btn_box_paste", getattr(self.app, "btn_box_paste", None)),
            ("btn_eyedropper", getattr(self.app, "btn_eyedropper", None)),
            ("btn_pin_speaker", getattr(self.app, "btn_pin_speaker", None)),
            ("btn_ribbon_undo", getattr(self.app, "btn_ribbon_undo", None)),
            ("btn_ribbon_redo", getattr(self.app, "btn_ribbon_redo", None)),
            ("btn_close_search", getattr(self.app, "btn_close_search", None)),
        ]

        missing_text = []
        for name, btn in buttons_to_check:
            self.assertIsNotNone(btn, f"Button {name} should exist on MisoraApp")
            txt = btn.cget("text")
            if not txt or not txt.strip():
                missing_text.append(name)

        self.assertEqual(
            missing_text,
            [],
            f"Rule 21 violation: The following buttons have empty fallback text: {missing_text}",
        )

    def test_06_icon_buttons_tooltips(self):
        """All icon-only and compact buttons must have accessible tooltips (Rule 21)."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        buttons_to_check = [
            ("btn_close_search", getattr(self.app, "btn_close_search", None)),
            ("btn_dock_pin", getattr(self.app, "btn_dock_pin", None)),
            ("btn_ribbon_swatch", getattr(self.app, "btn_ribbon_swatch", None)),
            ("btn_speaker_dropdown", getattr(self.app, "btn_speaker_dropdown", None)),
            ("btn_clear_res", getattr(self.app, "btn_clear_res", None)),
            ("btn_lock_box", getattr(self.app, "btn_lock_box", None)),
            ("btn_pin_speaker", getattr(self.app, "btn_pin_speaker", None)),
            ("btn_sel_story", getattr(self.app, "btn_sel_story", None)),
            ("btn_box_new", getattr(self.app, "btn_box_new", None)),
        ]

        missing_tooltip = []
        for name, btn in buttons_to_check:
            self.assertIsNotNone(btn, f"Button {name} should exist on MisoraApp")
            tip = getattr(btn, "_tooltip", None)
            if tip is None or not getattr(tip, "text", "").strip():
                missing_tooltip.append(name)

        self.assertEqual(
            missing_tooltip,
            [],
            f"Rule 21 violation: The following buttons lack tooltips: {missing_tooltip}",
        )

    def test_07_theme_contrast_calculations(self):
        """best_contrast_fg() must calculate proper contrast colors."""
        # Pure white background -> should return dark foreground
        fg_for_white = best_contrast_fg("#ffffff")
        self.assertEqual(fg_for_white, "#14141a")

        # Pure black background -> should return light foreground
        fg_for_black = best_contrast_fg("#000000")
        self.assertEqual(fg_for_black, "#ffffff")

        # Custom light background with explicit dark/light options
        fg_custom = best_contrast_fg("#faf8fe", "#221833", "#ffffff")
        self.assertEqual(fg_custom, "#221833")

    def test_08_side_drawer_responsive_constraints(self):
        """Opening side_drawer must apply minsize=260 and closing must cleanly forget it."""
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update()

        self.assertFalse(self.app._side_drawer_visible)

        # Open drawer
        self.app._open_side_drawer("customize")
        self.app.update()
        self.assertTrue(self.app._side_drawer_visible)
        drawer_minsize = int(self.app.h_paned.panecget(self.app.side_drawer, "minsize"))
        self.assertGreaterEqual(drawer_minsize, 260, "Side drawer minsize must be >= 260")

        # Close drawer
        self.app._close_side_drawer()
        self.app.update()
        self.assertFalse(self.app._side_drawer_visible)
        panes = self.app.h_paned.panes()
        self.assertNotIn(str(self.app.side_drawer), panes, "side_drawer should be removed from h_paned")


if __name__ == "__main__":
    unittest.main()
