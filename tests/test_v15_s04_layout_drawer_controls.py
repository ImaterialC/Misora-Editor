#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S04 (v1.4.4) Verification Suite:
- Probe 1 (U09-U14, U22, 4.2): Header & Edit Group layout order, flat Lock before Dialogue,
  VIEW group on Row 1, icon-only MTL/AI Prompt, compact Prev/Next, Player + Undo/Redo at far
  right of Row 2 actions_bar, NGUI ribbon default OFF.
- Probe 2 (U03, 4.4): Left Drawer true 0px collapse via h_paned.forget + discoverable reopen
  button + View > Show Left Panel; zero expensive rebuilds across repeated Left/Right toggles,
  resize, and iconify/deiconify; preserves editor, search, and MTL state.
- Probe 3 (U-1): Double-clicking Search Results tab opens Find bar preserving scope.
- Probe 4 (U-2): Enabled Engines moved from MTL drawer into Translator > Enabled Engines menu.
- Probe 5 (U-6): MTL Apply arrows point left (<-) and refresh.png (32x32 RGBA) is loaded.
- Probe 6 (U21): Checkbox/Radiobutton styles & tk.Checkbuttons have WCAG >= 4.5 contrast across
  checked/unchecked/hover/disabled states in Clean Daylight and Misora Classic (Dark).
- Guard 1 (NO-03): All Script MTL drawer keeps exact 2 tk.Text widgets + 5 static status tags.
- Guard 2: Shortcut router leaves native Ctrl+C/X/A untouched and routes Ctrl+Z/Y/L/T.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from PIL import Image  # noqa: E402

import misora  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402


def _collect_descendants(widget: tk.Misc):
    out = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class TestV15S04LayoutDrawerControls(unittest.TestCase):
    """Failing-first probes and regression guards for v1.5 S04 (v1.4.4)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s04_"))
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

    @staticmethod
    def _create_sample_doc() -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "おはよう！\n今日もいい天気ですね。"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "主さま、準備は整っております。"]),
        ]
        return StoryDocument(recs)

    # ------------------------------------------------------------------
    # Defect / Behavior Probes (MUST FAIL pre-patch, PASS post-patch)
    # ------------------------------------------------------------------
    def test_probe_1_header_and_edit_group_layout_order(self) -> None:
        """Probe 1 (U09-U14, U22, 4.2): 3-row hierarchy, flat Lock before Dialogue, Row 1 VIEW+icon MTL/AI, Row 2 Edit+Player+Undo/Redo, Ribbon OFF default."""
        # 1. Flat borderless Lock immediately before lbl_gd_title on Row 1 (gd_header)
        lock_btn = self.app.btn_lock_box
        title_lbl = self.app.lbl_gd_title
        gd_header = title_lbl.master

        self.assertEqual(lock_btn.master, gd_header, "btn_lock_box must be in Row 1 (gd_header)")
        self.assertEqual(int(lock_btn.cget("bd")), 0, "btn_lock_box must be borderless (bd=0)")
        self.assertEqual(str(lock_btn.cget("relief")), "flat", "btn_lock_box must have relief='flat'")
        self.assertEqual(int(lock_btn.cget("highlightthickness")), 0, "btn_lock_box must have highlightthickness=0")
        self.assertLess(
            lock_btn.winfo_rootx(),
            title_lbl.winfo_rootx(),
            "btn_lock_box must appear before lbl_gd_title ('Dialogue')",
        )

        # Lock styling stays flat when toggled locked and unlocked
        doc = self._create_sample_doc()
        path = self.tmp_dir / "s04_lock.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.on_toggle_lock_current_box()
        self.assertEqual(int(lock_btn.cget("bd")), 0)
        self.assertEqual(str(lock_btn.cget("relief")), "flat")
        self.assertEqual(int(lock_btn.cget("highlightthickness")), 0)

        # 2. VIEW group in Row 1 left of icon-only MTL & AI Prompt, then Prev, Next, Overflow, Counter
        self.assertEqual(self.app.view_group.master, gd_header, "view_group must sit in Row 1 (gd_header)")
        self.assertEqual(self.app.btn_translate.master, gd_header)
        self.assertEqual(self.app.btn_ai_prompt.master, gd_header)

        self.app.update_idletasks()
        self.app.update()
        self.assertLess(
            self.app.view_group.winfo_rootx(),
            self.app.btn_translate.winfo_rootx(),
            "view_group must sit left of btn_translate (MTL)",
        )
        self.assertLess(self.app.btn_translate.winfo_rootx(), self.app.btn_ai_prompt.winfo_rootx())
        self.assertLess(self.app.btn_ai_prompt.winfo_rootx(), self.app.btn_prev.winfo_rootx())
        self.assertLess(self.app.btn_prev.winfo_rootx(), self.app.btn_next.winfo_rootx())
        self.assertLess(self.app.btn_next.winfo_rootx(), self.app.lbl_char_overflow.winfo_rootx())
        self.assertLess(self.app.lbl_char_overflow.winfo_rootx(), self.app.lbl_box_counter.winfo_rootx())

        # Icon-only MTL & AI Prompt when icons exist
        if self.app.ico_mtl:
            self.assertEqual(str(self.app.btn_translate.cget("compound")), "none")
        if self.app.ico_ai:
            self.assertEqual(str(self.app.btn_ai_prompt.cget("compound")), "none")
        self.assertIn("Ctrl+T", self.app.btn_translate._tooltip.text)
        self.assertIn("Ctrl+Shift+T", self.app.btn_ai_prompt._tooltip.text)

        # Smaller Prev/Next
        self.assertEqual(self.app.btn_prev.cget("text").strip(), "Prev")
        self.assertEqual(self.app.btn_next.cget("text").strip(), "Next")

        # 3. Row 2: actions_bar in speaker_view_row with Player + Undo/Redo at far right
        speaker_row = self.app.speaker_view_row
        actions_bar = self.app.actions_bar
        self.assertEqual(actions_bar.master, speaker_row, "actions_bar must move to Row 2 (speaker_view_row)")
        self.assertEqual(self.app.btn_player.master, actions_bar, "btn_player must sit inside actions_bar")
        self.assertEqual(self.app.btn_ribbon_undo.master, actions_bar, "btn_ribbon_undo must sit inside actions_bar")
        self.assertEqual(self.app.btn_ribbon_redo.master, actions_bar, "btn_ribbon_redo must sit inside actions_bar")
        self.assertNotEqual(self.app.btn_ribbon_undo.master, self.app.ribbon_frame)
        self.assertNotEqual(self.app.btn_ribbon_redo.master, self.app.ribbon_frame)

        self.assertLess(self.app.btn_box_paste.winfo_rootx(), self.app.btn_player.winfo_rootx())
        self.assertLess(self.app.btn_player.winfo_rootx(), self.app.btn_ribbon_undo.winfo_rootx())
        self.assertLess(self.app.btn_ribbon_undo.winfo_rootx(), self.app.btn_ribbon_redo.winfo_rootx())

        # 4. Row 3: NGUI ribbon defaults to OFF
        self.assertFalse(self.app.var_show_ngui_ribbon.get(), "NGUI ribbon must default to OFF (False)")
        self.assertEqual(self.app.ribbon_frame.winfo_manager(), "", "ribbon_frame must be hidden by default")

    def test_probe_2_drawer_repeated_toggle_preserves_state_and_skips_expensive_rebuilds(self) -> None:
        """Probe 2 (U03, 4.4): Repeated Left/Right drawer toggles + resize preserve state with zero expensive rebuilds."""
        doc = self._create_sample_doc()
        path = self.tmp_dir / "s04_lifecycle.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._update_views()

        # Enter an edit in txt_dialogue
        self.app.txt_dialogue.delete("1.0", tk.END)
        self.app.txt_dialogue.insert("1.0", "Edited live buffer text")
        expected_editor_text = self.app.txt_dialogue.get("1.0", "end-1c")

        # Populate search results text widget
        self.app.txt_results.config(state="normal")
        self.app.txt_results.delete("1.0", tk.END)
        self.app.txt_results.insert("1.0", "s04_lifecycle.unity3d\n  #1 Pecorine: おはよう！")
        self.app.txt_results.config(state="disabled")
        expected_results_text = self.app.txt_results.get("1.0", "end-1c")

        # Open MTL drawer and enter scratchpad text
        self.app._open_side_drawer("mtl")
        self.app.update_idletasks()
        google_scratch = self.app._mtl_drawer_cards["Google"]["scratchpad"]
        google_scratch.delete("1.0", tk.END)
        google_scratch.insert("1.0", "Scratchpad preserved")

        # Wrap expensive rebuild methods
        counts = {"update_views": 0, "render_cont": 0, "update_raw": 0}
        orig_update_views = self.app._update_views
        orig_render_cont = self.app._render_continuous_view
        orig_update_raw = self.app._update_raw_view

        def spy_update_views(*a, **kw):
            counts["update_views"] += 1
            return orig_update_views(*a, **kw)

        def spy_render_cont(*a, **kw):
            counts["render_cont"] += 1
            return orig_render_cont(*a, **kw)

        def spy_update_raw(*a, **kw):
            counts["update_raw"] += 1
            return orig_update_raw(*a, **kw)

        with patch.object(self.app, "_update_views", side_effect=spy_update_views), \
             patch.object(self.app, "_render_continuous_view", side_effect=spy_render_cont), \
             patch.object(self.app, "_update_raw_view", side_effect=spy_update_raw):

            self.assertTrue(hasattr(self.app, "btn_reopen_left"), "btn_reopen_left reopen button must exist")
            self.assertTrue(hasattr(self.app, "var_show_left_panel"), "View > Show Left Panel BooleanVar must exist")

            for i in range(5):
                # Hide Left Drawer
                self.app._toggle_dock_collapse()
                self.app.update_idletasks()
                self.assertTrue(self.app._dock_collapsed)
                self.assertFalse(self.app.var_show_left_panel.get())
                self.assertNotIn(str(self.app.left_frame), [str(p) for p in self.app.h_paned.panes()], "left_frame must be forgotten from h_paned (0px)")
                self.assertNotEqual(self.app.btn_reopen_left.winfo_manager(), "", "btn_reopen_left must be visible when collapsed")

                # Show Left Drawer (alternate menu toggle vs reopen button)
                if i % 2 == 0:
                    self.app.var_show_left_panel.set(True)
                    self.app._on_toggle_left_panel()
                else:
                    self.app._toggle_dock_collapse()
                self.app.update_idletasks()
                self.assertFalse(self.app._dock_collapsed)
                self.assertTrue(self.app.var_show_left_panel.get())
                self.assertIn(str(self.app.left_frame), [str(p) for p in self.app.h_paned.panes()], "left_frame must be restored to h_paned")
                self.assertEqual(self.app.btn_reopen_left.winfo_manager(), "", "btn_reopen_left must be hidden when expanded")

                # Toggle Right Drawer hide/show
                self.app._toggle_side_drawer("mtl")
                self.app.update_idletasks()
                self.assertFalse(self.app._side_drawer_visible)
                self.app._toggle_side_drawer("mtl")
                self.app.update_idletasks()
                self.assertTrue(self.app._side_drawer_visible)

            # Trigger resize + iconify/deiconify lifecycle checks
            self.app.geometry("1120x660")
            self.app.update_idletasks()
            self.app.update()
            self.app.iconify()
            self.app.update_idletasks()
            self.app.deiconify()
            self.app.update_idletasks()

        self.assertEqual(counts["update_views"], 0, "Drawer toggles must NOT call _update_views")
        self.assertEqual(counts["render_cont"], 0, "Drawer toggles must NOT call _render_continuous_view")
        self.assertEqual(counts["update_raw"], 0, "Drawer toggles must NOT call _update_raw_view")

        # Verify state preserved intact
        self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), expected_editor_text)
        self.assertEqual(self.app.txt_results.get("1.0", "end-1c"), expected_results_text)
        self.assertEqual(self.app.current_box_idx, 0)
        self.assertEqual(
            self.app._mtl_drawer_cards["Google"]["scratchpad"].get("1.0", "end-1c"),
            "Scratchpad preserved",
        )

        # Verify zero duplicate Tk roots or orphaned Toplevels
        toplevels = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(toplevels), 0, f"Unexpected orphaned Toplevel windows: {toplevels}")

    def test_probe_3_search_tab_double_click_opens_find_bar(self) -> None:
        """Probe 3 (U-1): Double-clicking btn_tab_search opens Find bar while preserving active scope."""
        self.app.scope_var.set("folder")
        self.assertFalse(getattr(self.app, "_search_bar_visible", False))

        self.app.btn_tab_search.update_idletasks()
        self.app.btn_tab_search.event_generate("<ButtonPress-1>", x=5, y=5)
        self.app.btn_tab_search.event_generate("<ButtonRelease-1>", x=5, y=5)
        self.app.btn_tab_search.event_generate("<ButtonPress-1>", x=5, y=5)
        self.app.btn_tab_search.event_generate("<ButtonRelease-1>", x=5, y=5)
        self.app.update_idletasks()
        self.app.update()

        self.assertTrue(self.app._search_bar_visible, "Double-clicking Search Results tab must open Find bar")
        self.assertEqual(self.app.scope_var.get(), "folder", "Active search scope must be preserved")

    def test_probe_4_mtl_enabled_engines_moved_to_translator_menu(self) -> None:
        """Probe 4 (U-2): Enabled Engines removed from MTL drawer and placed in Translator > Enabled Engines menu."""
        self.app._open_side_drawer("mtl")
        self.app.update_idletasks()

        self.assertFalse(
            hasattr(self.app, "_mtl_dialogue_eng_bar"),
            "_mtl_dialogue_eng_bar must be removed from inside the MTL drawer",
        )
        self.assertTrue(hasattr(self.app, "translator_menu"), "translator_menu must be exposed on MisoraApp")
        self.assertTrue(hasattr(self.app, "mtl_engines_menu"), "mtl_engines_menu cascade must exist")
        self.assertIn(self.app.mtl_engines_menu, self.app._all_menus, "mtl_engines_menu must be registered in _all_menus")

        # Verify cascade label exists inside translator_menu
        end_idx = self.app.translator_menu.index("end")
        labels = [self.app.translator_menu.entrycget(i, "label") for i in range(end_idx + 1) if self.app.translator_menu.type(i) != "separator"]
        self.assertIn("Enabled Engines", labels)

        # Toggle DeepL via menu variable + callback
        self.assertFalse(self.app._mtl_drawer_enabled_engines.get("DeepL", False))
        self.app._mtl_drawer_engine_vars["DeepL"].set(True)
        self.app._on_mtl_drawer_engine_toggled("DeepL")
        self.app.update_idletasks()

        self.assertTrue(self.app._mtl_drawer_enabled_engines["DeepL"])
        self.assertIn("DeepL", self.app._mtl_drawer_cards, "Enabling DeepL from menu must rebuild drawer cards")
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertIs(saved.get("mtl_drawer_enabled_engines", {}).get("DeepL"), True)

    def test_probe_5_mtl_arrows_point_left_and_refresh_icon_loaded(self) -> None:
        """Probe 5 (U-6): MTL Apply buttons use left-pointing arrow '<-' and refresh.png (32x32 RGBA) is loaded."""
        refresh_path = _REPO / "assets" / "icons" / "refresh.png"
        self.assertTrue(refresh_path.is_file(), "assets/icons/refresh.png must exist")
        with Image.open(refresh_path) as im:
            self.assertEqual(im.size, (32, 32))
            self.assertEqual(im.mode, "RGBA")

        self.app._open_side_drawer("mtl")
        self.app._set_mtl_drawer_mode("dialogue")
        self.app.update_idletasks()

        # Dialogue card Apply arrow points left
        google_card = self.app._mtl_drawer_cards["Google"]
        card_btns = [w for w in _collect_descendants(google_card["frame"]) if isinstance(w, ttk.Button)]
        apply_btns = [b for b in card_btns if "←" in str(b.cget("text")) or "→" in str(b.cget("text"))]
        self.assertTrue(apply_btns, "Card must contain an Apply arrow button")
        for b in apply_btns:
            txt = str(b.cget("text"))
            self.assertIn("←", txt)
            self.assertNotIn("→", txt)

        # Refresh buttons carry refresh icon
        ico = self.app.get_icon("refresh", (14, 14))
        self.assertIsNotNone(ico, "get_icon('refresh', (14, 14)) must return a valid PhotoImage")
        self.assertTrue(str(self.app.btn_mtl_refresh_all.cget("image")), "btn_mtl_refresh_all must attach refresh icon")
        refresh_btns = [b for b in card_btns if "↻" in str(b.cget("text")) or "Refresh" in str(b.cget("text"))]
        self.assertTrue(refresh_btns)
        self.assertTrue(str(refresh_btns[0].cget("image")), "Per-card btn_refresh must attach refresh icon")

        # All Script Apply Selected arrow points left + Refresh Selected has icon
        self.app._set_mtl_drawer_mode("all_script")
        self.app.update_idletasks()
        apply_sel_txt = str(self.app.btn_mtl_all_apply_sel.cget("text"))
        self.assertIn("←", apply_sel_txt)
        self.assertNotIn("→", apply_sel_txt)
        self.assertTrue(str(self.app.btn_mtl_all_refresh_sel.cget("image")), "btn_mtl_all_refresh_sel must attach refresh icon")

    def test_probe_6_checkbox_radio_contrast_both_themes(self) -> None:
        """Probe 6 (U21): Checkbutton & Radiobutton styles + tk.Checkbutton widgets maintain WCAG >= 4.5 across Light & Dark themes."""
        style = ttk.Style(self.app)
        for preset in ("Clean Daylight", "Misora Classic (Dark)"):
            self.app._apply_theme_preset(preset)
            self.app.update_idletasks()
            t = self.app.theme

            for style_name, surface_key in (
                ("TCheckbutton", "bg_dark"),
                ("Panel.TCheckbutton", "bg_panel"),
                ("Accent.TCheckbutton", "bg_panel"),
                ("TRadiobutton", "bg_dark"),
                ("Panel.TRadiobutton", "bg_panel"),
            ):
                bg = style.lookup(style_name, "background") or t[surface_key]
                fg_norm = style.lookup(style_name, "foreground")
                fg_act = style.lookup(style_name, "foreground", state=("active",))
                fg_dis = style.lookup(style_name, "foreground", state=("disabled",))

                ind_bg_sel = style.lookup(style_name, "indicatorbackground", state=("selected",))
                ind_fg_sel = style.lookup(style_name, "indicatorforeground", state=("selected",))
                ind_bg_unsel = style.lookup(style_name, "indicatorbackground", state=("!selected",))
                ind_fg_unsel = style.lookup(style_name, "indicatorforeground", state=("!selected",))
                ind_bg_dis = style.lookup(style_name, "indicatorbackground", state=("disabled",))
                ind_fg_dis = style.lookup(style_name, "indicatorforeground", state=("disabled",))

                for label, c1, c2 in (
                    (f"{preset}/{style_name} normal fg", fg_norm, bg),
                    (f"{preset}/{style_name} active fg", fg_act, bg),
                    (f"{preset}/{style_name} disabled fg", fg_dis, bg),
                    (f"{preset}/{style_name} selected indicator", ind_fg_sel, ind_bg_sel),
                    (f"{preset}/{style_name} unselected indicator", ind_fg_unsel, ind_bg_unsel),
                    (f"{preset}/{style_name} disabled indicator", ind_fg_dis, ind_bg_dis),
                ):
                    self.assertTrue(misora.HEX_COLOR_RE.match(c1), f"{label} missing color 1: {c1!r}")
                    self.assertTrue(misora.HEX_COLOR_RE.match(c2), f"{label} missing color 2: {c2!r}")
                    ratio = misora.wcag_contrast_ratio(c1, c2)
                    self.assertGreaterEqual(ratio, 4.5, f"{label} contrast {ratio:.2f} < 4.5 ({c1} vs {c2})")

                # Selected and unselected indicator backgrounds must differ visibly
                self.assertNotEqual(
                    ind_bg_sel.lower(),
                    ind_bg_unsel.lower(),
                    f"{preset}/{style_name} selected vs unselected indicatorbackground must be distinct",
                )

            # Check tk.Checkbutton widgets directly
            for cb_name in ("cb_dialogue_select", "cb_sel_box", "cb_cont", "cb_compiled"):
                cb = getattr(self.app, cb_name)
                bg = str(cb.cget("bg"))
                fg = str(cb.cget("fg"))
                afg = str(cb.cget("activeforeground"))
                abg = str(cb.cget("activebackground"))
                dfg = str(cb.cget("disabledforeground"))
                selcol = str(cb.cget("selectcolor"))
                for label, c1, c2 in (
                    (f"{preset}/{cb_name} fg/bg", fg, bg),
                    (f"{preset}/{cb_name} active", afg, abg),
                    (f"{preset}/{cb_name} disabled", dfg, bg),
                    (f"{preset}/{cb_name} checkmark", fg, selcol),
                ):
                    ratio = misora.wcag_contrast_ratio(c1, c2)
                    self.assertGreaterEqual(ratio, 4.5, f"{label} contrast {ratio:.2f} < 4.5 ({c1} vs {c2})")

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS pre-patch and post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_mtl_all_script_drawer_still_exact_2_text_widgets(self) -> None:
        """Guard 1 (NO-03): All Script MTL drawer keeps strictly 2 tk.Text widgets + 5 static status tags."""
        doc = self._create_sample_doc()
        path = self.tmp_dir / "s04_guard_mtl.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._update_views()

        self.app._open_side_drawer("mtl")
        self.app._set_mtl_drawer_mode("all_script")
        self.app.update_idletasks()

        text_widgets = [w for w in _collect_descendants(self.app.tab_mtl_frame) if isinstance(w, tk.Text)]
        self.assertEqual(len(text_widgets), 2, f"Expected strictly 2 tk.Text widgets, got {len(text_widgets)}")
        tags = set(self.app.txt_mtl_all_list.tag_names())
        expected = {
            "mtl_status_ready",
            "mtl_status_translating",
            "mtl_status_error",
            "mtl_status_locked",
            "mtl_status_empty",
        }
        self.assertTrue(expected.issubset(tags))

    def test_guard_2_shortcut_router_and_native_edit_keys_preserved(self) -> None:
        """Guard 2: MisoraShortcuts leaves native Ctrl+C/X/A untouched and routes Ctrl+Z/Y/L/T."""
        txt = self.app.txt_dialogue
        self.assertIn("MisoraShortcuts", txt.bindtags())

        for key in ("c", "x", "a"):
            ev = tk.Event()
            ev.widget = txt
            ev.keysym = key
            ev.state = 0x0004
            self.assertIsNone(self.app._on_misora_shortcut(ev), f"Native Ctrl+{key.upper()} must return None")

        for key in ("z", "y", "l", "t"):
            ev = tk.Event()
            ev.widget = txt
            ev.keysym = key
            ev.state = 0x0004
            self.assertEqual(self.app._on_misora_shortcut(ev), "break", f"App shortcut Ctrl+{key.upper()} must return 'break'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
