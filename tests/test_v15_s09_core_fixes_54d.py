#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S09 (v1.4.8) Verification Suite — Core Bug Fixes, 54d Reference Calibration, Box 0 Exemption,
Dialogue Preview Pink Arrow Fix, MTL Apply Button Placement, & Console Toggle Removal.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.script_codec import serialize  # noqa: E402
from core.story_ast import BoxSnapshot, Record, StoryDocument  # noqa: E402


class TestV15S09CoreFixes54d(unittest.TestCase):
    """7 failing-first defect/behavior probes + 2 regression guards for S09 (v1.4.8)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s09_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patch_cfg = patch.object(misora, "CONFIG_PATH", self.config_path)
        self.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        self.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        self.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)
        self.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)

        self.patch_cfg.start()
        self.patch_info.start()
        self.patch_warn.start()
        self.patch_err.start()
        self.patch_yesno.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.geometry("1280x720+80+80")
        self.app.update_idletasks()
        self.app.update()

    def tearDown(self) -> None:
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patch_yesno.stop()
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _attach_doc(self, doc: StoryDocument, name: str = "s09_test.unity3d") -> Path:
        p = self.tmp_dir / name
        self.app.open_documents[p] = {
            "doc": doc,
            "plain_text": "",
            "dirty": False,
            "current_box_idx": 0,
            "is_box0_active": False,
            "locked_box_uids": set(),
            "modified_box_uids": set(),
            "original_jp_by_uid": {},
        }
        self.app.current_file_path = p
        self.app.current_doc = doc
        self.app.is_box0_active = False
        self.app.current_box_idx = 0
        self.app.is_dirty = False
        self.app._selected_boxes = set()
        self.app._locked_box_uids = set()
        self.app._update_views()
        self.app.update_idletasks()
        return p

    def _make_sample_doc(self) -> StoryDocument:
        return StoryDocument([
            Record(cmd_id=0, cmd_name="title", args=["Test Title"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 1"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Line 2"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 3"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 5"]),
        ])

    # ------------------------------------------------------------------
    # Probe 1 (U-01): Paste Box Selection Model & Insert with Box 0
    # ------------------------------------------------------------------
    def test_probe_1_paste_replace_uses_selected_boxes_and_insert_box0(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)

        # Put 2 boxes into clipboard
        self.app._selected_boxes = {0, 2}
        self.app.on_box_copy()
        self.assertEqual(len(self.app._box_clipboard), 2)

        # 1. Empty selection -> Replace aborts with notification & leaves doc untouched
        self.app._selected_boxes = set()
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_box_paste(confirm=False, mode="replace")
        self.assertEqual(doc.boxes[0].clean_text, "Line 1")
        self.assertTrue(
            any("no boxes selected" in str(c.args[0]).lower() for c in mock_toast.call_args_list),
            "Direct replace with empty selection must notify user",
        )

        # 2. Mismatched count (1 selected vs 2 clipboard) -> aborts showing BOTH counts
        self.app._selected_boxes = {1}
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_box_paste(confirm=False, mode="replace")
        self.assertEqual(doc.boxes[1].clean_text, "Line 2")
        toast_strs = [str(c.args[0]) for c in mock_toast.call_args_list]
        self.assertTrue(
            any("1" in s and "2" in s for s in toast_strs),
            f"Count mismatch must show both counts; got: {toast_strs}",
        )

        # 3. Box 0 (-1) in _selected_boxes -> atomic abort
        self.app._selected_boxes = {-1, 0}
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_box_paste(confirm=False, mode="replace")
        self.assertEqual(doc.boxes[0].clean_text, "Line 1")
        self.assertTrue(
            any("box 0" in str(c.args[0]).lower() for c in mock_toast.call_args_list),
            "Box 0 in selection must abort Replace with clear notification",
        )

        # 4. Locked target in selection -> atomic abort (zero shifting/mutation)
        self.app.current_box_idx = 4
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(4))
        self.app._selected_boxes = {1, 4}
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_box_paste(confirm=False, mode="replace")
        self.assertEqual(doc.boxes[1].clean_text, "Line 2")
        self.assertEqual(doc.boxes[4].clean_text, "Line 5")
        self.assertTrue(
            any("locked" in str(c.args[0]).lower() for c in mock_toast.call_args_list),
            "Locked target must abort Replace atomically",
        )

        # 5. Non-contiguous valid Replace ({1, 3}) -> replaces exact selected boxes + Undo/Redo
        self.app._selected_boxes = {1, 3}
        self.app.on_box_paste(confirm=False, mode="replace")
        self.assertEqual(doc.boxes[1].speaker, "Pecorine")
        self.assertEqual(doc.boxes[1].clean_text, "Line 1")
        self.assertEqual(doc.boxes[3].speaker, "Pecorine")
        self.assertEqual(doc.boxes[3].clean_text, "Line 3")

        self.app.on_undo()
        self.assertEqual(doc.boxes[1].speaker, "Kokkoro")
        self.assertEqual(doc.boxes[1].clean_text, "Line 2")
        self.assertEqual(doc.boxes[3].speaker, "")
        self.assertEqual(doc.boxes[3].clean_text, "Narration line")

        self.app.on_redo()
        self.assertEqual(doc.boxes[1].clean_text, "Line 1")
        self.assertEqual(doc.boxes[3].clean_text, "Line 3")
        self.app.on_undo()

        # 6. Insert with Box 0 active -> inserts BEFORE index 0 (first dialogue box)
        self.app.is_box0_active = True
        self.app.current_box_idx = 0
        self.app._selected_boxes = set()
        orig_len = len(doc.boxes)
        self.app.on_box_paste(confirm=False, mode="insert")
        self.assertEqual(len(doc.boxes), orig_len + 2)
        self.assertEqual(doc.boxes[0].clean_text, "Line 1")
        self.assertEqual(doc.boxes[1].clean_text, "Line 3")
        self.assertEqual(doc.boxes[2].clean_text, "Line 1")

        self.app.on_undo()
        self.assertEqual(len(doc.boxes), orig_len)

    # ------------------------------------------------------------------
    # Probe 2 (U-02): Pin Speaker Unpin-First Actor Switching & Lock Orthogonality
    # ------------------------------------------------------------------
    def test_probe_2_pin_speaker_captured_identity_and_no_wrap_boundaries(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)

        # Box #1 (idx=0) is Pecorine; occurrences at idx 0, 2, 4
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        self.assertEqual(self.app._pinned_speaker_name, "Pecorine")

        # Boundary navigation with Pecorine pinned (idx 0 -> 2 -> 4, no wrap-around)
        self.app.on_next_box()
        self.assertEqual(self.app.current_box_idx, 2)
        self.app.on_next_box()
        self.assertEqual(self.app.current_box_idx, 4)

        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_next_box()
        self.assertEqual(self.app.current_box_idx, 4)
        self.assertTrue(
            any("last time speaking in this chapter" in str(c.args[0]).lower() for c in mock_toast.call_args_list)
        )

        self.app.on_prev_box()
        self.assertEqual(self.app.current_box_idx, 2)
        self.app.on_prev_box()
        self.assertEqual(self.app.current_box_idx, 0)
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.on_prev_box()
        self.assertEqual(self.app.current_box_idx, 0)
        self.assertTrue(
            any("first time speaking in this chapter" in str(c.args[0]).lower() for c in mock_toast.call_args_list)
        )

        # on_box_new() prefills from _pinned_speaker_name ("Pecorine")
        self.app.on_box_new()
        self.assertTrue(
            any(r.cmd_id == 6 and r.args == ["Pecorine", ""] for r in doc.records),
            "on_box_new() must prefill speaker from _pinned_speaker_name",
        )

        # Unpin Actor A -> Pin OFF, entry_speaker remains normal/editable
        self.app._on_toggle_pin_speaker()
        self.assertFalse(self.app._is_speaker_pinned)
        self.assertIsNone(self.app._pinned_speaker_name)
        self.assertEqual(str(self.app.entry_speaker.cget("state")), "normal")

        # Change speaker to Actor B ("Kyaru") while unpinned -> Pin stays OFF
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.speaker_var.set("Kyaru")
        self.app._commit_speaker_edit(source="keyboard")
        self.assertEqual(doc.boxes[0].speaker, "Kyaru")
        self.assertFalse(self.app._is_speaker_pinned)
        self.assertIsNone(self.app._pinned_speaker_name)

        # Re-pin Actor B ("Kyaru") -> navigation uses Kyaru only (idx=0 has no other Kyaru)
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        self.assertEqual(self.app._pinned_speaker_name, "Kyaru")
        self.app.on_next_box()
        self.assertEqual(self.app.current_box_idx, 0, "Old Actor A (Pecorine) must not influence navigation")

        # Attempt actor change while Pin is active -> explicit unpin-first release!
        with patch.object(self.app, "show_toast", wraps=self.app.show_toast) as mock_toast:
            self.app.speaker_var.set("Kokkoro")
            self.app._commit_speaker_edit(source="keyboard")
        self.assertEqual(doc.boxes[0].speaker, "Kokkoro")
        self.assertFalse(self.app._is_speaker_pinned, "Pin MUST turn OFF after actor change")
        self.assertIsNone(self.app._pinned_speaker_name, "Old pinned identity MUST NOT linger")
        self.assertTrue(
            any("speaker pin released" in str(c.args[0]).lower() for c in mock_toast.call_args_list),
            f"Expected explicit unpin-first toast; got: {[c.args[0] for c in mock_toast.call_args_list]}",
        )

        # Lock-Before-Unpin ordering: blocked rename on locked box MUST NOT release Pin
        self.app.current_box_idx = 1  # Kokkoro
        self.app._update_views()
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        self.assertEqual(self.app._pinned_speaker_name, "Kokkoro")
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))
        self.app.speaker_var.set("Rei")
        committed = self.app._commit_speaker_edit(source="keyboard")
        self.assertFalse(committed)
        self.assertEqual(doc.boxes[1].speaker, "Kokkoro")
        self.assertTrue(self.app._is_speaker_pinned, "Blocked rename on locked box must NOT release Speaker Pin")
        self.assertEqual(self.app._pinned_speaker_name, "Kokkoro")
        self.app.on_toggle_lock_current_box()  # unlock
        self.app._on_toggle_pin_speaker()  # unpin

        # Jump-to-Speaker (▼) is navigation-only and NEVER mutates active box's speaker
        self.app.current_box_idx = 0
        self.app._update_views()
        sp_before = doc.boxes[0].speaker
        self.app._jump_to_speaker("Pecorine")
        self.assertEqual(doc.boxes[0].speaker, sp_before, "Jump-to-Speaker must never mutate box 0's speaker")

        # Pin Narration ("")
        narr_idx = next(i for i, b in enumerate(doc.boxes) if b.speaker == "")
        self.app.current_box_idx = narr_idx
        self.app._update_views()
        self.app._on_toggle_pin_speaker()
        self.assertEqual(self.app._pinned_speaker_name, "")
        self.assertEqual(len(self.app._locked_box_uids), 0, "Pin must never modify Translation Lock state")

    # ------------------------------------------------------------------
    # Probe 3 (U-06): Speaker Autocomplete Never Flashes (0, 0) & Multi-Monitor Clamping
    # ------------------------------------------------------------------
    def test_probe_3_speaker_autocomplete_withdrawn_and_positioned_never_zero_zero(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)

        self.assertTrue(
            hasattr(self.app, "_get_monitor_work_area"),
            "Expected _get_monitor_work_area() helper for multi-monitor clamping",
        )

        self.app.entry_speaker.focus_force()
        self.app.update()
        self.app._close_speaker_autocomplete()

        events = []
        orig_withdraw = tk.Toplevel.withdraw
        orig_deiconify = tk.Toplevel.deiconify
        orig_geometry = tk.Toplevel.geometry

        def _spy_withdraw(win, *a, **kw):
            events.append("withdraw")
            return orig_withdraw(win, *a, **kw)

        def _spy_deiconify(win, *a, **kw):
            events.append("deiconify")
            return orig_deiconify(win, *a, **kw)

        def _spy_geometry(win, *a, **kw):
            if a:
                events.append(("geometry", a[0]))
            return orig_geometry(win, *a, **kw)

        with patch.object(tk.Toplevel, "withdraw", _spy_withdraw), \
             patch.object(tk.Toplevel, "deiconify", _spy_deiconify), \
             patch.object(tk.Toplevel, "geometry", _spy_geometry):
            self.app._open_speaker_autocomplete()
            self.app.update_idletasks()

        self.assertIn("withdraw", events, "Popup must be withdrawn on creation before positioning")
        self.assertIn("deiconify", events, "Popup must be deiconified after positioning")
        w_idx = events.index("withdraw")
        d_idx = events.index("deiconify")
        g_indices = [i for i, e in enumerate(events) if isinstance(e, tuple) and e[0] == "geometry"]
        self.assertTrue(g_indices, "Popup geometry must be set before deiconify")
        self.assertLess(w_idx, g_indices[0])
        self.assertLess(g_indices[0], d_idx)

        popup = getattr(self.app, "_speaker_popup", None)
        self.assertIsNotNone(popup)
        self.assertTrue(popup.winfo_exists())

        # Must NEVER be positioned at (0, 0) and must align below entry_speaker
        px = popup.winfo_x()
        py = popup.winfo_y()
        ex = self.app.entry_speaker.winfo_rootx()
        self.assertNotEqual((px, py), (0, 0), "Autocomplete popup must never map at (0, 0)")
        self.assertAlmostEqual(px, ex, delta=40)
        self.assertGreaterEqual(py, self.app.entry_speaker.winfo_rooty())

        # Multi-monitor negative coordinate clamping: secondary monitor at (-1920, 0, 0, 1080)
        with patch.object(self.app, "_get_monitor_work_area", return_value=(-1920, 0, 0, 1080)), \
             patch.object(self.app.entry_speaker, "winfo_rootx", return_value=-1800), \
             patch.object(self.app.entry_speaker, "winfo_rooty", return_value=200), \
             patch.object(self.app.entry_speaker, "winfo_height", return_value=24):
            self.app._refresh_speaker_autocomplete()
            self.app.update_idletasks()
            self.assertLess(popup.winfo_x(), 0, "Secondary monitor negative X must not be clamped to >= 0")

        # Verify S05 FocusOut safety still holds when clicking listbox
        self.app._speaker_listbox.focus_set()
        self.app.update()
        self.app._on_speaker_focus_out_deferred()
        self.assertTrue(self.app._is_speaker_popup_open())

    # ------------------------------------------------------------------
    # Probe 3b (U-06): Full-List Autocomplete on First Open & Entry Editability
    # ------------------------------------------------------------------
    def test_probe_3b_speaker_autocomplete_full_list_and_editing(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)

        # Active box 0 has speaker "Pecorine"
        self.app.current_box_idx = 0
        self.app._update_views()
        self.assertEqual(self.app.speaker_var.get(), "Pecorine")

        # 1. First popup open MUST show ALL unique document actors + (Narration — Clear Speaker)
        self.app._open_speaker_autocomplete()
        self.app.update_idletasks()
        vals = [val for _lbl, val in self.app._speaker_popup_items]
        self.assertIn("Pecorine", vals)
        self.assertIn("Kokkoro", vals, f"All actors must be shown on first open; got {vals}")
        self.assertIn("", vals, "Narration clear option must be shown on first open")

        # 2. Navigation/modifier keys MUST NOT trigger filtering
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="Right"))
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="Shift_L"))
        vals_after_nav = [val for _lbl, val in self.app._speaker_popup_items]
        self.assertIn("Kokkoro", vals_after_nav, "Navigation/modifier keys must not filter full list")

        # 3. Actual typing filters candidates; clearing query restores all candidates
        self.app.speaker_var.set("Kok")
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="k"))
        vals_filtered = [val for _lbl, val in self.app._speaker_popup_items]
        self.assertEqual(vals_filtered, ["Kokkoro"])

        self.app.speaker_var.set("")
        self.app._on_speaker_key_release(types.SimpleNamespace(keysym="BackSpace"))
        vals_restored = [val for _lbl, val in self.app._speaker_popup_items]
        self.assertIn("Pecorine", vals_restored)
        self.assertIn("Kokkoro", vals_restored)

        # 4. Selecting a different Actor while pinned commits cleanly & releases pin
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        kok_idx = vals_restored.index("Kokkoro")
        self.app._speaker_listbox.selection_clear(0, tk.END)
        self.app._speaker_listbox.selection_set(kok_idx)
        self.app._accept_speaker_autocomplete_selection()
        self.assertEqual(doc.boxes[0].speaker, "Kokkoro")
        self.assertFalse(self.app._is_speaker_pinned)
        self.assertEqual(str(self.app.entry_speaker.cget("state")), "normal")

        # 5. Entry editability does NOT bypass Translation Lock on commit
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(0))
        self.assertEqual(str(self.app.entry_speaker.cget("state")), "normal")
        self.app.speaker_var.set("Kyaru")
        self.assertFalse(self.app._commit_speaker_edit(source="autocomplete"))
        self.assertEqual(doc.boxes[0].speaker, "Kokkoro")

    # ------------------------------------------------------------------
    # Probe 4 (U-07 / U-18): Shared 54d Reference & Box 0 Immunity
    # ------------------------------------------------------------------
    def test_probe_4_shared_54d_reference_pixel_contract_and_box0_immunity(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)

        # Shared helper must exist and stay constant across Global and Japanese font presets
        self.assertTrue(hasattr(self.app, "_get_54d_reference_safe_w"))
        self.app.dialogue_font_family = misora.PRESET_GLOBAL
        safe_global = self.app._get_54d_reference_safe_w()
        self.app.dialogue_font_family = misora.PRESET_JP
        safe_jp = self.app._get_54d_reference_safe_w()
        self.assertEqual(safe_global, safe_jp, "54d reference width must stay constant across presets")

        # Verify 54 digits in Nunito Bold (Global preset) does NOT overflow, 55 digits DOES overflow
        self.app.dialogue_font_family = misora.PRESET_GLOBAL
        m_54 = self.app._measure_dialogue_metrics("1234567890" * 5 + "1234")
        m_55 = self.app._measure_dialogue_metrics("1234567890" * 5 + "12345")
        self.assertEqual(m_54["safe_w"], safe_global)
        self.assertFalse(m_54["has_width_overflow"], "54 digit-widths in Nunito Bold must NOT overflow")
        self.assertTrue(m_55["has_width_overflow"], "55 digit-widths in Nunito Bold MUST overflow")

        # Ruler labels must say 54d and >54d
        self.app._redraw_pixel_rulers()
        ruler_texts = [
            self.app.ruler_clean.itemcget(item, "text")
            for item in self.app.ruler_clean.find_all()
            if self.app.ruler_clean.type(item) == "text"
        ]
        self.assertIn("54d", ruler_texts)
        self.assertIn(">54d", ruler_texts)
        self.assertNotIn("50d", ruler_texts)

        # Header indicator uses /54d · /3L
        self.app._update_char_overflow_indicator("1234567890" * 5 + "1234")
        self.assertIn("/54d · 1/3L", self.app.lbl_char_overflow.cget("text"))

        # Box 0 immunity: no red overflow, no Auto Word Wrap
        self.app.is_box0_active = True
        self.app._update_views()
        self.app._update_char_overflow_indicator("X" * 200 + "\nL2\nL3\nL4")
        self.assertEqual(self.app.lbl_char_overflow.cget("text"), "Metadata (unmeasured)")
        stats = self.app.apply_auto_word_wrap(scope="current")
        self.assertEqual(stats["wrapped"], 0)

    # ------------------------------------------------------------------
    # Probe 5 (U-19): Dialogue Preview Pink Arrow & Continuous Border
    # ------------------------------------------------------------------
    def test_probe_5_dialogue_preview_pink_arrow_unclipped_and_continuous_border(self) -> None:
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "A" * 80 + "\nLine 2\nLine 3"]),
        ])
        self._attach_doc(doc)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.app.update()

        canvas = self.app.dialogue_preview_canvas
        arrow_items = canvas.find_withtag("preview_arrow")
        capsule_items = canvas.find_withtag("preview_capsule")
        self.assertEqual(len(arrow_items), 1, "Expected tagged preview_arrow item")
        self.assertEqual(len(capsule_items), 1, "Expected tagged preview_capsule item")

        win_bbox = canvas.bbox(self.app._dialogue_preview_win)
        arrow_bbox = canvas.bbox(arrow_items[0])
        cap_bbox = canvas.bbox(capsule_items[0])
        self.assertIsNotNone(win_bbox)
        self.assertIsNotNone(arrow_bbox)
        self.assertIsNotNone(cap_bbox)

        # Strict non-overlapping geometry:
        # text_win_right < arrow_left, text_win_right < capsule_right_inner, text_win_bottom < capsule_bottom_inner
        self.assertLess(win_bbox[2], arrow_bbox[0], f"Text window {win_bbox} overlaps arrow {arrow_bbox}")
        self.assertLess(win_bbox[2], cap_bbox[2] - 2, f"Text window {win_bbox} clips right border {cap_bbox}")
        self.assertLess(win_bbox[3], cap_bbox[3] - 2, f"Text window {win_bbox} clips bottom border {cap_bbox}")

    # ------------------------------------------------------------------
    # Probe 5b (U-19): Dialogue Preview Pink Actor Nameplate & White Contrast Text
    # ------------------------------------------------------------------
    def test_probe_5b_dialogue_preview_pink_actor_nameplate(self) -> None:
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello Priconne!"]),
        ])
        self._attach_doc(doc)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.app.update()

        canvas = self.app.dialogue_preview_canvas
        plate_items = canvas.find_withtag("preview_nameplate")
        self.assertGreaterEqual(len(plate_items), 2, "Expected nameplate image/rect + speaker text")

        # Speaker text fill must be crisp white (#FFFFFF)
        text_items = [it for it in plate_items if canvas.type(it) == "text"]
        self.assertEqual(len(text_items), 1)
        self.assertEqual(canvas.itemcget(text_items[0], "fill").upper(), "#FFFFFF")

        # Inspect actual rendered nameplate ImageTk.PhotoImage center pixel via PIL.ImageTk.getimage:
        # _dialogue_preview_images: [cap_img, plate_img, tri_img]
        from PIL import ImageTk
        self.assertGreaterEqual(len(self.app._dialogue_preview_images), 3)
        plate_img = self.app._dialogue_preview_images[1]
        pil_plate = ImageTk.getimage(plate_img)
        r, g, b = pil_plate.getpixel((pil_plate.width // 2, pil_plate.height // 2))[:3]
        self.assertGreater(r, 150, f"Nameplate red channel too low for pink: RGB={(r, g, b)}")
        self.assertGreater(r, g + 40, f"Nameplate must be pink-dominant over green: RGB={(r, g, b)}")
        self.assertGreater(r, b + 20, f"Nameplate must be pink-dominant over blue (not purple #3B2C4E): RGB={(r, g, b)}")

        # Dialogue capsule remains cream-white (#F8F6F0), NOT pink
        cap_img = self.app._dialogue_preview_images[0]
        pil_cap = ImageTk.getimage(cap_img)
        cr, cg, cb = pil_cap.getpixel((pil_cap.width // 2, pil_cap.height // 2))[:3]
        self.assertGreater(cg, 230, f"Dialogue capsule must remain cream-white, not pink: RGB={(cr, cg, cb)}")

    # ------------------------------------------------------------------
    # Probe 6 (RM-01): Console Toggle Completely Removed & Legacy Config
    # ------------------------------------------------------------------
    def test_probe_6_console_toggle_completely_removed_and_legacy_config_tolerated(self) -> None:
        self.assertFalse(hasattr(self.app, "_toggle_windows_console"))
        self.assertFalse(hasattr(self.app, "_toggle_console_visibility"))
        self.assertFalse(hasattr(self.app, "_toggle_console_shortcut"))
        self.assertFalse(hasattr(self.app, "var_console_visible"))

        # Debug menu has no Show / Hide Windows Console
        end_idx = self.app.debug_menu.index("end")
        labels = []
        if end_idx is not None:
            for i in range(end_idx + 1):
                try:
                    labels.append(self.app.debug_menu.entrycget(i, "label"))
                except Exception:
                    pass
        self.assertFalse(any("console" in lbl.lower() for lbl in labels), f"Console menu item still present: {labels}")

        # F12 is unbound
        self.assertFalse(self.app.bind("<F12>"))

        # Legacy console_visible in config loads cleanly and is NOT written back
        self.config_path.write_text(
            json.dumps({"debug": {"console_visible": True, "log_to_file": False}}),
            encoding="utf-8",
        )
        prefs = self.app._load_user_prefs()
        self.assertNotIn("console_visible", prefs.get("debug", {}))
        self.app._save_user_prefs(silent=True)
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertNotIn("console_visible", saved.get("debug", {}))

    # ------------------------------------------------------------------
    # Probe 7 (U-16): MTL Apply (←) Button Left of Engine Name
    # ------------------------------------------------------------------
    def test_probe_7_mtl_apply_button_left_of_engine_name(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)
        self.app._switch_side_drawer_tab("mtl")
        self.app._set_mtl_drawer_mode("dialogue")
        self.app.update_idletasks()
        self.app.update()

        self.assertTrue(self.app._mtl_drawer_cards, "Expected at least one MTL card")
        for eng, widgets in self.app._mtl_drawer_cards.items():
            btn_apply = widgets["btn_apply"]
            lbl_eng = widgets.get("lbl_engine")
            self.assertIsNotNone(lbl_eng, f"Card '{eng}' missing lbl_engine reference")
            self.assertLess(
                btn_apply.winfo_rootx(),
                lbl_eng.winfo_rootx(),
                f"Apply button on '{eng}' must be to the LEFT of engine name",
            )

    # ------------------------------------------------------------------
    # Guard 1: Dialogue Preview Remains Read-Only & Excluded from Save
    # ------------------------------------------------------------------
    def test_guard_1_dialogue_preview_remains_readonly_and_excluded_from_save(self) -> None:
        doc = self._make_sample_doc()
        self._attach_doc(doc)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        self.assertEqual(str(self.app.txt_dialogue_preview.cget("state")), "disabled")
        self.assertEqual(doc.boxes[0].clean_text, "Line 1")

    # ------------------------------------------------------------------
    # Guard 2: Adjacent Narration Separation & cmd_id 35/32 Preserved
    # ------------------------------------------------------------------
    def test_guard_2_adjacent_narration_separation_and_cmd_35_32_preserved(self) -> None:
        doc = StoryDocument([
            Record(cmd_id=32, cmd_name="subtitle", args=["Sub"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narr 1"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Spoken"]),
        ])
        self._attach_doc(doc)
        self.app.current_box_idx = 1
        self.app._update_views()
        self.app.speaker_var.set("")
        self.app._commit_speaker_edit()
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].segs[0].record.cmd_id, 35)
        self.assertEqual(doc.boxes[1].segs[0].record.cmd_id, 35)
        self.assertTrue(any(r.cmd_id == 32 for r in doc.records))

    # ------------------------------------------------------------------
    # Guard 3: Translation Lock on Cut Box & Clear Skeleton (Rows 11a, 11b)
    # ------------------------------------------------------------------
    def test_guard_3_translation_lock_cut_box_and_clear_skeleton(self) -> None:
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Unlocked line"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Locked line"]),
        ])
        self._attach_doc(doc)
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        # 11a: Clear Skeleton skips locked box 1, clears unlocked box 0
        self.app.on_clear_dialogue_skeleton()
        self.assertEqual(doc.boxes[0].clean_text, "")
        self.assertEqual(doc.boxes[1].clean_text, "Locked line")
        self.app.on_undo()
        self.assertEqual(doc.boxes[0].clean_text, "Unlocked line")

        # 11b: Cut Box on locked box 1 alone is blocked; mixed {0, 1} cuts only unlocked box 0
        self.app._selected_boxes = {1}
        self.app.on_box_cut()
        self.assertEqual(len(doc.boxes), 2)
        self.app._selected_boxes = {0, 1}
        self.app.on_box_cut()
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(doc.boxes[0].clean_text, "Locked line")


if __name__ == "__main__":
    unittest.main()
