#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Phase 3 Session 14 (Track 2 · Group G1):
- BUG-38: Search Bar 5-Col Grid & Find/Replace Geometry Alignment
- FEAT-01: Hide Folder Path Entry & Browse on Scope 'current'
- FEAT-02: Player Icon-Only ({playername} fallback, no {0} text) & Remove [-] from Ribbon
- FEAT-03: Rename Continuous View -> All Script, Unified VIEW Group, Mode Headers & Raw Commands
- BUG-39 + FEAT-04: Responsive Grid/Stacked Rows (no clipping at 1280x720 / 960x720) & View > Toggle NGUI Ribbon
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import tkinter as tk

import misora
from misora import MisoraApp


class TestP3S14ToolbarSearchUI(unittest.TestCase):
    """Test suite for S14 Search Bar grid, scope toggle, player icon, VIEW group, and responsive toolbars."""

    def setUp(self) -> None:
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name)
        self.orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_dir / "misora_config.json"

        # Create app instance with splash disabled
        self.app = MisoraApp(show_splash=False)
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update_idletasks()
        self.app.update()

    def tearDown(self) -> None:
        try:
            self.app.destroy()
        except Exception:
            pass
        misora.CONFIG_PATH = self.orig_config_path
        try:
            self.tmp_dir_obj.cleanup()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Regression Guard: Pre-patch Core UI Contracts & Shortcuts
    # -------------------------------------------------------------------------
    def test_guard_01_core_ui_and_shortcuts_preserved(self) -> None:
        """Regression Guard: Text widgets have MisoraShortcuts bindtag, basic bindings, and valid editor state."""
        self.assertIsNotNone(self.app.txt_dialogue)
        tags = self.app.txt_dialogue.bindtags()
        self.assertIn("MisoraShortcuts", tags, "MisoraShortcuts bindtag must be installed on dialogue editor")

        # Standard widget copy/paste shortcut event must return None for native processing
        ev_c = tk.Event()
        ev_c.widget = self.app.txt_dialogue
        ev_c.keysym = "c"
        ev_c.state = 0x0004  # Ctrl
        ret_val = self.app._on_misora_shortcut(ev_c)
        self.assertIsNone(ret_val, "Standard Ctrl+C must return None for native handling")

    # -------------------------------------------------------------------------
    # Probe 1: BUG-38 — Search Bar 5-Column Grid & Button Parity
    # -------------------------------------------------------------------------
    def test_probe_01_bug38_search_grid_alignment(self) -> None:
        """BUG-38: Find and Replace rows use shared 5-column grid with identical entry geometry and button dimensions."""
        self.app.on_show_replace()
        self.app.update_idletasks()
        self.app.update()

        # 1. Entry X-origin and width must match identically
        s_rx = self.app.search_entry.winfo_rootx()
        r_rx = self.app.replace_entry.winfo_rootx()
        self.assertEqual(
            s_rx, r_rx,
            f"Search entry rootx ({s_rx}) must match Replace entry rootx ({r_rx})"
        )

        s_w = self.app.search_entry.winfo_width()
        r_w = self.app.replace_entry.winfo_width()
        self.assertEqual(
            s_w, r_w,
            f"Search entry width ({s_w}) must match Replace entry width ({r_w})"
        )

        # 2. All 4 buttons (Find in Files, Cancel, Replace, Replace All) must have identical width and height
        btn_find = self.app.btn_find
        btn_cancel = self.app.btn_cancel
        btn_replace = self.app.btn_replace
        btn_replace_all = self.app.btn_replace_all

        btn_widths = [
            btn_find.winfo_width(),
            btn_cancel.winfo_width(),
            btn_replace.winfo_width(),
            btn_replace_all.winfo_width(),
        ]
        btn_heights = [
            btn_find.winfo_height(),
            btn_cancel.winfo_height(),
            btn_replace.winfo_height(),
            btn_replace_all.winfo_height(),
        ]

        self.assertEqual(
            len(set(btn_widths)), 1,
            f"All 4 search/replace buttons must share identical width, got {btn_widths}"
        )
        self.assertEqual(
            len(set(btn_heights)), 1,
            f"All 4 search/replace buttons must share identical height, got {btn_heights}"
        )

    # -------------------------------------------------------------------------
    # Probe 2: FEAT-01 — Hide Path Entry & Browse Button on Scope 'current'
    # -------------------------------------------------------------------------
    def test_probe_02_feat01_scope_current_unmaps_path_widgets(self) -> None:
        """FEAT-01: Scope 'current' unmaps folder_path_entry and btn_browse_search_folder while preserving paths."""
        fake_proj = self.tmp_dir / "SavedProject"
        fake_folder = self.tmp_dir / "SavedFolder"
        fake_proj.mkdir(parents=True, exist_ok=True)
        fake_folder.mkdir(parents=True, exist_ok=True)

        self.app.project_folder = fake_proj
        self.app.selected_search_folder = fake_folder

        # Switch to Folder scope -> widgets mapped
        self.app.scope_var.set("folder")
        self.app._sync_scope_widgets()
        self.app.update_idletasks()
        self.assertNotEqual(self.app.folder_path_entry.winfo_manager(), "")
        self.assertNotEqual(self.app.btn_browse_search_folder.winfo_manager(), "")
        self.assertEqual(self.app.folder_path_var.get(), str(fake_folder))

        # Switch to Current scope -> widgets unmapped (pack_forget / grid_remove)
        self.app.scope_var.set("current")
        self.app._sync_scope_widgets()
        self.app.update_idletasks()

        self.assertEqual(
            self.app.folder_path_entry.winfo_manager(), "",
            "folder_path_entry must be unmapped (pack_forget/grid_remove) under scope 'current'"
        )
        self.assertEqual(
            self.app.btn_browse_search_folder.winfo_manager(), "",
            "btn_browse_search_folder must be unmapped under scope 'current'"
        )

        # Preserved paths intact
        self.assertEqual(self.app.project_folder, fake_proj)
        self.assertEqual(self.app.selected_search_folder, fake_folder)

        # Switch back to Folder scope -> re-mapped and path intact
        self.app.scope_var.set("folder")
        self.app._sync_scope_widgets()
        self.app.update_idletasks()
        self.assertNotEqual(self.app.folder_path_entry.winfo_manager(), "")
        self.assertNotEqual(self.app.btn_browse_search_folder.winfo_manager(), "")
        self.assertEqual(self.app.folder_path_var.get(), str(fake_folder))

    # -------------------------------------------------------------------------
    # Probe 3: FEAT-02 & FEAT-03 — Player Icon, Ribbon Clean, Headers, Raw Commands
    # -------------------------------------------------------------------------
    def test_probe_03_feat02_feat03_player_ribbon_headers(self) -> None:
        """FEAT-02 & FEAT-03: No [-] in ribbon, Player button is icon-only outside ribbon, headers & Raw Commands correct."""
        ribbon_frame = getattr(self.app, "ribbon_frame", None)
        self.assertIsNotNone(ribbon_frame, "self.app.ribbon_frame must exist")

        # 1. Ribbon has NO standalone [-] button
        ribbon_children = ribbon_frame.winfo_children()
        for child in ribbon_children:
            txt = getattr(child, "cget", lambda k: "")("text")
            self.assertNotEqual(
                txt.strip(), "[-]",
                "Ribbon frame must not contain a standalone '[-]' button"
            )

        # Unmapped compatibility self.btn_dash exists but parented outside ribbon_frame
        btn_dash = getattr(self.app, "btn_dash", None)
        self.assertIsNotNone(btn_dash, "btn_dash compatibility attribute must exist for S13 suite")
        self.assertNotEqual(
            btn_dash.master, ribbon_frame,
            "btn_dash compatibility button must be parented outside ribbon_frame"
        )
        self.assertEqual(btn_dash.winfo_manager(), "", "btn_dash must not be mapped/packed")

        # 2. Player button is icon-only, sits OUTSIDE ribbon_frame, no "{0}" in label, valid tooltip
        btn_player = getattr(self.app, "btn_player", None)
        self.assertIsNotNone(btn_player, "btn_player must exist")
        self.assertNotEqual(
            btn_player.master, ribbon_frame,
            "btn_player must be moved OUT of ribbon_frame into speaker/text-actions area"
        )
        player_text = btn_player.cget("text")
        self.assertNotIn("{0}", player_text, "btn_player label text must not contain '{0}'")
        self.assertTrue(bool(player_text.strip()), "btn_player must have a non-empty Unicode fallback text (e.g. 👤)")

        tip = getattr(btn_player, "_tooltip", None)
        self.assertIsNotNone(tip, "btn_player must have an attached ToolTip")
        self.assertTrue(
            "{playername}" in tip.text.lower() or "{0}" in tip.text,
            f"btn_player tooltip must explain {{playername}} / {{0}}, got: '{tip.text}'"
        )

        # 3. Dynamic header titles
        self.assertTrue(hasattr(self.app, "lbl_gd_title"), "lbl_gd_title must exist")
        # Default: Page View, Preview OFF -> "Dialogue"
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "Dialogue")

        # Preview ON -> "Dialogue Preview"
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "Dialogue Preview")

        # All Script ON, Preview ON -> "All Script Preview"
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "All Script Preview")

        # All Script ON, Preview OFF -> "All Script"
        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "All Script")

        # 4. Bottom pane title is strictly "Raw Commands"
        self.assertTrue(hasattr(self.app, "lbl_raw_title"), "lbl_raw_title attribute must exist")
        self.assertEqual(self.app.lbl_raw_title.cget("text"), "Raw Commands")

    # -------------------------------------------------------------------------
    # Probe 4: BUG-39 & FEAT-04 — Responsive Rows & Toggle NGUI Ribbon
    # -------------------------------------------------------------------------
    def test_probe_04_bug39_feat04_responsive_rows_and_ngui_toggle(self) -> None:
        """BUG-39 & FEAT-04: Toolbars do not clip parent at 1280x720 / 960x720; View > Toggle NGUI Ribbon hides/shows."""
        # 1. Bounds check at 1280x720 and 960x720
        top_view = getattr(self.app, "top_view", None)
        self.assertIsNotNone(top_view, "self.app.top_view must exist")

        view_group = getattr(self.app, "view_group", None)
        actions_bar = getattr(self.app, "actions_bar", None)
        ribbon_frame = getattr(self.app, "ribbon_frame", None)
        btn_player = getattr(self.app, "btn_player", None)

        self.assertIsNotNone(view_group, "view_group must exist")
        self.assertIsNotNone(actions_bar, "actions_bar must exist")
        self.assertIsNotNone(ribbon_frame, "ribbon_frame must exist")
        self.assertIsNotNone(btn_player, "btn_player must exist")

        for geo in ("1280x720", "960x720"):
            self.app.geometry(geo)
            self.app.update_idletasks()
            self.app.update()

            top_right = top_view.winfo_rootx() + top_view.winfo_width()

            # Verify key groups have positive width and do not overflow right edge of top_view
            for name, widget in [
                ("view_group", view_group),
                ("actions_bar", actions_bar),
                ("ribbon_frame", ribbon_frame),
                ("btn_player", btn_player),
            ]:
                self.assertGreater(widget.winfo_width(), 0, f"{name} must have positive width at {geo}")
                widget_right = widget.winfo_rootx() + widget.winfo_width()
                self.assertLessEqual(
                    widget_right, top_right + 5,
                    f"{name} clipped off right edge at {geo} (right={widget_right} > parent_right={top_right})"
                )

        # 2. View > Toggle NGUI Ribbon
        self.assertTrue(
            hasattr(self.app, "var_show_ngui_ribbon"),
            "self.app.var_show_ngui_ribbon BooleanVar must exist"
        )
        self.assertTrue(self.app.var_show_ngui_ribbon.get(), "NGUI ribbon must be visible by default")

        # Toggle off
        self.app.var_show_ngui_ribbon.set(False)
        self.app._on_toggle_ngui_ribbon()
        self.app.update_idletasks()
        self.app.update()

        self.assertEqual(
            ribbon_frame.winfo_manager(), "",
            "ribbon_frame must be unmapped when var_show_ngui_ribbon is False"
        )
        self.assertNotEqual(
            actions_bar.winfo_manager(), "",
            "actions_bar must remain visible when NGUI ribbon is toggled off"
        )

        # Verify saved to config
        self.assertTrue(misora.CONFIG_PATH.is_file(), "Config file must be persisted")
        saved_data = json.loads(misora.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIs(saved_data.get("show_ngui_ribbon"), False, "show_ngui_ribbon must be saved as false")

        # Toggle back on
        self.app.var_show_ngui_ribbon.set(True)
        self.app._on_toggle_ngui_ribbon()
        self.app.update_idletasks()
        self.app.update()
        self.assertNotEqual(
            ribbon_frame.winfo_manager(), "",
            "ribbon_frame must be remapped when var_show_ngui_ribbon is True"
        )


if __name__ == "__main__":
    unittest.main()
