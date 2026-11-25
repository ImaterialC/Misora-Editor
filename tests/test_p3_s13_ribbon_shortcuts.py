#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_p3_s13_ribbon_shortcuts.py
======================================
Automated Verification Suite for Session 13 (Track 1 Final Gate).

Session Scope:
- BUG-28: Continuous ribbon/size/ruby target active card widget via _get_card_text_widget(),
          remove redundant _on_dialogue_edited() to fix Page View dirty '*' title & Undo sync,
          and call _commit_widget_edit(target) in on_insert_font_size().
- BUG-29: Reconcile canonical shortcut router table: Ctrl+T (translator) vs Ctrl+Shift+T (AI prompt),
          resolve <Control-C> vs <Control-Shift-C> collision, add missing Ctrl+R to bindtag router,
          and whitelist safe Ctrl+Alt app accelerators (X/C/V/A) while preserving AltGr.
- HYG-07: Ensure bind_all('<Control-h>', ...) returns 'break' to prevent widget backspace deletion.
- HYG-03: Complete 350ms ToolTips and Unicode fallback text for all ribbon/toolbar controls.

Strict Invariants:
- Preserves and restores misora.CONFIG_PATH.
- Redirects app.backup_folder to a TemporaryDirectory (0 writes to repo backups/).
- Suppresses modal messageboxes and live network requests.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora
from core.story_ast import Record, StoryDocument


class TestP3S13RibbonShortcuts(unittest.TestCase):
    """S13 Defect Probes and Final Track 1 Regression Guards."""

    def setUp(self) -> None:
        self.temp_dir_obj = tempfile.TemporaryDirectory(prefix="misora_s13_test_")
        self.temp_dir = Path(self.temp_dir_obj.name)

        # Redirect CONFIG_PATH
        self._orig_config_path = misora.CONFIG_PATH
        self.test_config_path = self.temp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.test_config_path

        # Mock modal dialogs to avoid hanging on test runs
        self._patcher_showerror = mock.patch("tkinter.messagebox.showerror")
        self._patcher_askyesnocancel = mock.patch("tkinter.messagebox.askyesnocancel", return_value=False)
        self._patcher_askyesno = mock.patch("tkinter.messagebox.askyesno", return_value=False)
        self._patcher_showinfo = mock.patch("tkinter.messagebox.showinfo")
        self._patcher_showwarning = mock.patch("tkinter.messagebox.showwarning")

        self.mock_showerror = self._patcher_showerror.start()
        self.mock_askyesnocancel = self._patcher_askyesnocancel.start()
        self.mock_askyesno = self._patcher_askyesno.start()
        self.mock_showinfo = self._patcher_showinfo.start()
        self.mock_showwarning = self._patcher_showwarning.start()

        # Initialize MisoraApp in headless / withdrawn mode
        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.temp_dir / "backups")

    def tearDown(self) -> None:
        try:
            if hasattr(self.app, "logger") and self.app.logger:
                self.app.logger.close()
        except Exception:
            pass

        try:
            self.app.destroy()
        except Exception:
            pass

        self._patcher_showerror.stop()
        self._patcher_askyesnocancel.stop()
        self._patcher_askyesno.stop()
        self._patcher_showinfo.stop()
        self._patcher_showwarning.stop()

        misora.CONFIG_PATH = self._orig_config_path
        self.temp_dir_obj.cleanup()

    def _setup_synthetic_story(self) -> StoryDocument:
        """Create a synthetic 2-box story document loaded into self.app."""
        doc = StoryDocument()
        doc.records = [
            Record(cmd_id=1, cmd_name="print", args=["Pecorine", "Yabai desu ne!"]),
            Record(cmd_id=1, cmd_name="print", args=["Kyaru", "Baka!"]),
        ]
        doc._rebuild_boxes()

        test_file = self.temp_dir / "test_story.txt"
        test_file.write_text("dummy", encoding="utf-8")
        self.app.open_documents[test_file] = {
            "doc": doc,
            "env": None,
            "text_obj": None,
            "is_bundle": True,
        }
        self.app.current_file_path = test_file
        self.app.current_doc = doc
        self.app.is_bundle_file = True
        self.app.current_box_idx = 0
        self.app._update_views()
        return doc

    # -------------------------------------------------------------------------
    # Probe 1: BUG-28 — Ribbon & Font Size Central Commit in Continuous & Page Views
    # -------------------------------------------------------------------------
    def test_probe_01_bug28_ribbon_and_size_commit_targets(self) -> None:
        """BUG-28: Ribbon formatting, font size, and ruby mutate active card in Continuous View,

        trigger dirty state '*' on first click in Page View, and respect box locks.
        """
        doc = self._setup_synthetic_story()

        # --- Subtest 1: Page View dirty '*' title and undo on first format click ---
        self.assertFalse(self.app.is_dirty, "Document should initially be clean")
        self.assertNotIn("*", self.app.title(), "Window title should not have '*' when clean")

        self.app.txt_dialogue.focus_set()
        self.app.txt_dialogue.tag_add("sel", "1.0", "end-1c")
        self.app.apply_ngui_wrapper("[b]", "[/b]")

        self.assertTrue(self.app.is_dirty, "apply_ngui_wrapper in Page View must mark document dirty")
        self.assertIn("*", self.app.title(), "Window title must display '*' on first format click")
        self.assertEqual(doc.boxes[0].clean_text, "[b]Yabai desu ne![/b]")
        self.assertTrue(self.app.undo_journal.can_undo(), "Undo journal must record delta on first click")

        # --- Subtest 2: All Script (Technique A) selection + jump & ribbon/size commit ---
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        # Technique A renders inside single read-only txt_all_script with block map
        self.assertEqual(self.app._card_widgets, {}, "Technique A must not create per-box card widgets")
        self.assertIn(1, self.app._all_script_block_ranges, "Box 1 must exist in All Script block map")
        s_ln, _ = self.app._all_script_block_ranges[1]
        self.app._on_all_script_click_at_index(f"{s_ln}.0")
        self.assertEqual(self.app.current_box_idx, 1)

        # Clear hidden txt_continuous to verify it is NOT polluted
        self.app.txt_continuous.delete("1.0", tk.END)

        # Jump to Dialogue View for editing Box 1 and apply bold + font size
        self.app._on_all_script_activate_at_index(f"{s_ln}.0")
        self.app.update_idletasks()
        self.assertFalse(self.app.var_continuous_view.get())
        self.app.txt_dialogue.focus_set()
        self.app.txt_dialogue.tag_add("sel", "1.0", "end-1c")
        self.app.apply_ngui_wrapper("[b]", "[/b]")

        self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), "[b]Baka![/b]",
                         "Dialogue editor must be updated by apply_ngui_wrapper")
        self.assertEqual(doc.boxes[1].clean_text, "[b]Baka![/b]",
                         "AST box 1 clean_text must be updated")
        self.assertEqual(self.app.txt_continuous.get("1.0", "end-1c"), "",
                         "Hidden txt_continuous fallback widget must NOT be modified")

        # Font size on box 1
        self.app.txt_dialogue.tag_add("sel", "1.0", "end-1c")
        self.app.on_insert_font_size("16")

        self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), "<size=16>[b]Baka![/b]</size>",
                         "Dialogue editor must receive size tag from on_insert_font_size")
        self.assertEqual(doc.boxes[1].clean_text, "<size=16>[b]Baka![/b]</size>",
                         "AST box 1 clean_text must receive size tag from on_insert_font_size commit")

        # --- Subtest 3: Locked Box Safeguard (in All Script mode too) ---
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1), "Box 1 should now be locked")

        before_lock_text = doc.boxes[1].clean_text
        self.app.apply_ngui_wrapper("[i]", "[/i]")
        self.assertEqual(doc.boxes[1].clean_text, before_lock_text,
                         "Locked box text must NOT be mutated by apply_ngui_wrapper")

        self.app.on_insert_font_size("18")
        self.assertEqual(doc.boxes[1].clean_text, before_lock_text,
                         "Locked box text must NOT be mutated by on_insert_font_size")

    # -------------------------------------------------------------------------
    # Probe 2: BUG-29 & HYG-07 — Reconcile Shortcut Table & Return 'break'
    # -------------------------------------------------------------------------
    def test_probe_02_bug29_hyg07_shortcut_table_reconciliation(self) -> None:
        """BUG-29 & HYG-07: Shortcut table dispatch: Ctrl+T (translator), Ctrl+Shift+T (prompt),

        Ctrl+Shift+C (script), Ctrl+R (ruby), Ctrl+Alt+C/V/X/A, and bind_all('<Control-h>') break.
        """
        self._setup_synthetic_story()

        # Mock action targets to observe dispatch without side-effects
        self.app.on_open_translator_assistant = mock.MagicMock()
        self.app.on_copy_ai_prompt = mock.MagicMock()
        self.app.on_copy_script = mock.MagicMock()
        self.app.on_insert_ruby = mock.MagicMock()
        self.app.on_box_copy = mock.MagicMock()
        self.app.on_box_paste = mock.MagicMock()
        self.app.on_box_cut = mock.MagicMock()
        self.app.on_select_whole_story = mock.MagicMock()
        self.app.on_show_replace = mock.MagicMock()

        # 1. Ctrl+T (no shift) -> Translator Assistant
        ev = tk.Event()
        ev.keysym = "t"
        ev.state = 0x0004  # Control
        res = self.app._on_misora_shortcut(ev)
        self.assertEqual(res, "break")
        self.app.on_open_translator_assistant.assert_called_once()
        self.app.on_copy_ai_prompt.assert_not_called()

        # 2. Ctrl+Shift+T -> Copy AI Prompt
        ev.keysym = "t"
        ev.state = 0x0004 | 0x0001  # Control | Shift
        res = self.app._on_misora_shortcut(ev)
        self.assertEqual(res, "break")
        self.app.on_copy_ai_prompt.assert_called_once()

        # 3. Ctrl+Shift+C -> Copy Script (zero collision with Ctrl+C)
        ev.keysym = "c"
        ev.state = 0x0004 | 0x0001  # Control | Shift
        res = self.app._on_misora_shortcut(ev)
        self.assertEqual(res, "break")
        self.app.on_copy_script.assert_called_once()

        # 4. Ctrl+R -> Insert Ruby in bindtag router
        ev.keysym = "r"
        ev.state = 0x0004  # Control
        res = self.app._on_misora_shortcut(ev)
        self.assertEqual(res, "break")
        self.app.on_insert_ruby.assert_called_once()

        # 5. Ctrl+Alt+C/V/X/A app accelerators (X/C/V/A)
        for key, mock_func in [
            ("c", self.app.on_box_copy),
            ("v", self.app.on_box_paste),
            ("x", self.app.on_box_cut),
            ("a", self.app.on_select_whole_story),
        ]:
            ev.keysym = key
            ev.state = 0x0004 | 0x0008  # Control | Alt
            res = self.app._on_misora_shortcut(ev)
            self.assertEqual(res, "break", f"Ctrl+Alt+{key.upper()} must return 'break'")
            mock_func.assert_called_once()

        # 6. AltGr international characters (e.g. Ctrl+Alt+E) must return None (not break)
        ev.keysym = "e"
        ev.state = 0x0004 | 0x0008  # Control | Alt
        res = self.app._on_misora_shortcut(ev)
        self.assertIsNone(res, "AltGr character keys must pass through (return None)")

        # 7. Check <Control-C> is NOT bound to continuous view toggle in root bindings
        bound_cmd = self.app.bind("<Control-C>")
        self.assertFalse(
            bound_cmd and "_toggle_continuous_shortcut" in str(bound_cmd),
            "<Control-C> must NOT be bound to _toggle_continuous_shortcut (collision with Ctrl+Shift+C)"
        )

        # 8. HYG-07: bind_all('<Control-h>', ...) must return 'break'
        h_bindings = self.app.bind_all("<Control-h>")
        self.assertTrue(h_bindings, "bind_all('<Control-h>') must exist")
        # Invoke callback with synthetic event
        ev_h = tk.Event()
        ev_h.keysym = "h"
        ev_h.state = 0x0004
        ret_val = self.app._on_ctrl_h(ev_h)
        self.assertEqual(ret_val, "break", "bind_all('<Control-h>') handler must return 'break'")

    # -------------------------------------------------------------------------
    # Probe 3: HYG-03 — Complete Ribbon ToolTips & Unicode Text Fallbacks
    # -------------------------------------------------------------------------
    def test_probe_03_hyg03_ribbon_tooltips_and_fallbacks(self) -> None:
        """HYG-03: Every ribbon/toolbar control has a valid ToolTip (delay_ms=350) and Unicode fallback."""
        required_controls = [
            ("btn_ruby", getattr(self.app, "btn_ruby", None)),
            ("btn_dash", getattr(self.app, "btn_dash", None)),
            ("btn_player", getattr(self.app, "btn_player", None)),
            ("btn_ai_prompt", getattr(self.app, "btn_ai_prompt", None)),
            ("btn_translate", getattr(self.app, "btn_translate", None)),
            ("cb_compiled", getattr(self.app, "cb_compiled", None)),
            ("cb_cont", getattr(self.app, "cb_cont", None)),
            ("cb_sel_box", getattr(self.app, "cb_sel_box", None)),
            ("btn_prev", getattr(self.app, "btn_prev", None)),
            ("btn_next", getattr(self.app, "btn_next", None)),
        ]

        # Also check mini formatting buttons B, I, U, S, Sub, Sup
        format_buttons = getattr(self.app, "btn_format_buttons", {})
        for lbl in ["B", "I", "U", "S", "Sub", "Sup"]:
            required_controls.append((f"format_{lbl}", format_buttons.get(lbl)))

        missing_tooltips = []
        missing_text = []

        for name, widget in required_controls:
            self.assertIsNotNone(widget, f"Control {name} must exist on self.app")
            tip = getattr(widget, "_tooltip", None)
            if tip is None or not getattr(tip, "text", "").strip():
                missing_tooltips.append(name)
            elif getattr(tip, "delay_ms", None) != 350:
                missing_tooltips.append(f"{name} (delay_ms={getattr(tip, 'delay_ms', None)} != 350)")

            txt = widget.cget("text")
            if not txt or not txt.strip():
                missing_text.append(name)

        self.assertEqual(missing_tooltips, [], f"The following controls lack valid 350ms ToolTips: {missing_tooltips}")
        self.assertEqual(missing_text, [], f"The following controls lack fallback text: {missing_text}")

    # -------------------------------------------------------------------------
    # Regression Guard: Native Shortcuts & Text Paste Preserved
    # -------------------------------------------------------------------------
    def test_guard_01_native_shortcuts_and_text_paste_preserved(self) -> None:
        """Native Ctrl+C, Ctrl+X, Ctrl+A, and non-CSIF Ctrl+V return None for standard widget processing."""
        ev = tk.Event()
        ev.state = 0x0004  # Control only

        for key in ["c", "x", "a"]:
            ev.keysym = key
            res = self.app._on_misora_shortcut(ev)
            self.assertIsNone(res, f"Native Ctrl+{key.upper()} must return None for standard widget processing")

        # Ctrl+V with non-CSIF text in clipboard returns None
        with mock.patch.object(self.app, "safe_clipboard_get", return_value="Regular plain text"):
            ev.keysym = "v"
            res = self.app._on_misora_shortcut(ev)
            self.assertIsNone(res, "Regular text paste must return None for standard widget processing")


if __name__ == "__main__":
    unittest.main()
