#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S10 (v1.4.9) — Virtualized Read-Only All Script Card Pool (54d x 3),
raw_breaks-Safe Segment-Aware Quick Edit Tab, S09b Lock Parity,
View-Aware Live Sync, Active Box Highlight, Box 0 Block, & All Script Preview Removal.
"""
from __future__ import annotations

import gc
import shutil
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora  # noqa: E402
from core.story_ast import BoxSnapshot, Record, StoryDocument  # noqa: E402


def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class TestV15S10AllScriptQuickEdit(unittest.TestCase):
    """Failing-first Defect/Behavior Probes (5) and Regression Guards (2) for S10."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s10_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patches = [
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=True),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora, "CONFIG_PATH", self.config_path),
        ]
        for p in self.patches:
            p.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.geometry("1220x780+40+40")
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.update_idletasks()

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
        gc.collect()
        for p in reversed(self.patches):
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _open_records(self, records: list[Record], name: str = "s10_story.v2.txt") -> StoryDocument:
        doc = StoryDocument(records)
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p, reload_from_disk=True)
        self.app.update_idletasks()
        return self.app.current_doc

    def _make_n_box_records(self, n: int, with_meta: bool = True) -> list[Record]:
        recs: list[Record] = []
        if with_meta:
            recs.extend([
                Record(cmd_id=0, cmd_name="fade", args=["Episode Title"]),
                Record(cmd_id=1, cmd_name="log", args=["Line A\nLine B\nLine C\nLine D synopsis text."]),
                Record(cmd_id=32, cmd_name="cmd_32", args=["Chapter Sub"]),
            ])
        for i in range(n):
            if i > 0:
                recs.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            if i % 10 == 0:
                recs.append(Record(cmd_id=12, cmd_name="touch", args=[f"vo_adv_{i:04d}"]))
            recs.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker_{i % 4}", f"Box {i + 1} line text."]))
        return recs

    def _get_pool_cards(self) -> list:
        pool = getattr(self.app, "_as_card_pool", None)
        self.assertIsNotNone(pool, "Virtualized All Script pool (_as_card_pool) is missing")
        return list(pool)

    def _find_visible_card(self, box_idx: int):
        for card in self._get_pool_cards():
            if getattr(card, "bound_box_idx", None) == box_idx:
                return card
        return None

    # ------------------------------------------------------------------
    # Failing-First Probes (MUST FAIL pre-patch, PASS post-patch)
    # ------------------------------------------------------------------
    def test_probe_1_virtualized_pool_bounded_across_150_300_1000_boxes_and_recycling_safety(self) -> None:
        """Probe 1: Pool size scales dynamically with viewport height across 150/300/1000 boxes & recycles safely."""
        pool_sizes = []
        for count in (150, 300, 1000):
            self._open_records(self._make_n_box_records(count, with_meta=False), name=f"s10_{count}.v2.txt")
            self.app.var_continuous_view.set(True)
            self.app._on_toggle_continuous_view()
            self.app.update_idletasks()
            self.app.update()

            self.assertEqual(self.app.txt_all_script.winfo_manager(), "", "Retired txt_all_script must not be mapped")
            self.assertNotEqual(self.app.cont_canvas.winfo_manager(), "", "cont_canvas must be mapped in All Script")
            pool = self._get_pool_cards()
            self.assertGreaterEqual(len(pool), 4)
            self.assertLessEqual(len(pool), 30, f"Pool exploded to {len(pool)} widgets for {count} boxes")
            pool_sizes.append(len(pool))

        self.assertEqual(len(set(pool_sizes)), 1, f"Pool size should depend on viewport, not doc length: {pool_sizes}")

        # Verify dynamic resize scales pool capacity with viewport height
        small_pool = pool_sizes[0]
        self.app._recompute_as_pool_for_height(1800)
        self.app.update_idletasks()
        grown_pool = len(self._get_pool_cards())
        self.assertGreater(grown_pool, small_pool, "Pool size must grow dynamically when viewport height increases")
        self.app._recompute_as_pool_for_height(self.app.cont_canvas.winfo_height() or 500)
        self.app.update_idletasks()

        # On 1000-box doc: enable Select Box mode, select 0 & 998, lock 1 & 999
        self.app.var_select_box_mode.set(True)
        self.app._on_toggle_select_box_mode()
        self.app._selected_boxes = {0, 998}
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.app.current_box_idx = 999
        self.app.on_toggle_lock_current_box()
        self.app._render_continuous_view()
        self.app.update_idletasks()

        # Scroll to end (box 998, 999 visible)
        self.app._on_as_scrollbar("moveto", "1.0")
        self.app.update_idletasks()
        card_998 = self._find_visible_card(998)
        card_999 = self._find_visible_card(999)
        self.assertIsNotNone(card_998)
        self.assertIsNotNone(card_999)
        self.assertEqual(card_998.bound_box_uid, self.app.current_doc.boxes[998].uid)
        self.assertIn("Box 999 line text.", card_998.txt_body.get("1.0", "end-1c"))
        self.assertIn("[x]", card_998.lbl_sel.cget("text"))
        self.assertIn("🔒", card_999.lbl_lock.cget("text"))

        # Click recycled card 998 -> dynamic callback must select 998 (never stale index)
        self.app._on_as_card_click(card_998)
        self.assertEqual(self.app.current_box_idx, 998)

        # Scroll back to top -> verify box 0 & 1 preserved cleanly with zero stale 998/999 state
        self.app._on_as_scrollbar("moveto", "0.0")
        self.app.update_idletasks()
        card_0 = self._find_visible_card(0)
        card_1 = self._find_visible_card(1)
        self.assertIsNotNone(card_0)
        self.assertIsNotNone(card_1)
        self.assertIn("Box 1 line text.", card_0.txt_body.get("1.0", "end-1c"))
        self.assertIn("[x]", card_0.lbl_sel.cget("text"))
        self.assertIn("🔒", card_1.lbl_lock.cget("text"))
        self.assertNotIn("🔒", card_0.lbl_lock.cget("text"))

    def test_probe_2_pixel_exact_54d_card_geometry_header_voice_cue_and_no_red_markers(self) -> None:
        """Probe 2: Exact 54d x 3 geometry invariant across Global/JP presets, header contract, Box 0 unclipped, zero red markers."""
        overwide = "1234567890" * 6  # 60 digits > 54d
        five_lines = f"{overwide}\nLine 2\nLine 3\nLine 4\nLine 5"
        long_syn = "Synopsis line 1 " * 20 + "\nSynopsis line 2\nSynopsis line 3\nSynopsis line 4\nSynopsis line 5"
        doc = self._open_records([
            Record(cmd_id=0, cmd_name="fade", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="log", args=[long_syn]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Sub Title"]),
            Record(cmd_id=12, cmd_name="touch", args=["vo_adv_1001001_001"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", five_lines]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Seg 2 line"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Pure narration line."]),
        ])
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.app.update()

        # Box 0 rendered at top as full-width wrap="word" block (not 54d x 3 clipped)
        box0_card = getattr(self.app, "_as_box0_card", None)
        self.assertIsNotNone(box0_card)
        self.assertEqual(str(box0_card.txt_summary.cget("wrap")), "word")
        self.assertEqual(box0_card.txt_summary.tag_ranges("line_overflow"), ())

        # Dialogue card 0 geometry & header under Global preset
        card0 = self._find_visible_card(0)
        self.assertIsNotNone(card0)
        self.assertEqual(int(card0.txt_body.cget("height")), 3)
        self.assertEqual(str(card0.txt_body.cget("wrap")), "none")
        self.assertEqual(str(card0.txt_body.cget("state")), "disabled")
        self.assertEqual(card0.txt_body.tag_ranges("line_overflow"), (), "All Script must have ZERO red overflow tags")
        self.assertEqual(card0.txt_body.tag_ranges("gutter_overflow"), ())
        self.assertEqual([w for w in _collect_descendants(card0) if isinstance(w, tk.Scrollbar)], [])
        self.assertEqual([w for w in _collect_descendants(card0.hdr) if isinstance(w, tk.Canvas)], [])

        hdr_text = " ".join(
            str(w.cget("text")) for w in _collect_descendants(card0.hdr) if isinstance(w, tk.Label)
        )
        self.assertIn("♪ vo_adv_1001001_001", hdr_text)
        self.assertIn("[2 segs]", hdr_text)
        self.assertNotIn("----", hdr_text)
        self.assertEqual(doc.boxes[0].voice_cue, "vo_adv_1001001_001")

        # Fixed-width Select Box slot never shifts Lock horizontally
        lock_x_off = card0.lbl_lock.winfo_rootx()
        self.app.var_select_box_mode.set(True)
        self.app._on_toggle_select_box_mode()
        self.app.update_idletasks()
        lock_x_on = card0.lbl_lock.winfo_rootx()
        self.assertEqual(lock_x_on, lock_x_off, "Lock icon shifted horizontally when toggling Select Box")

        # 54d pixel width invariant across Global — Nunito Bold and Japanese presets
        w_global = card0.body_wrap.winfo_reqwidth()
        expected_safe_w = self.app._get_54d_reference_safe_w()
        self.assertGreaterEqual(w_global, expected_safe_w)
        self.assertLessEqual(w_global, expected_safe_w + 32)

        self.app.dialogue_font_family = misora.PRESET_JP
        self.app._apply_theme_and_fonts_live(save=False)
        self.app.update_idletasks()
        card0_jp = self._find_visible_card(0)
        w_jp = card0_jp.body_wrap.winfo_reqwidth()
        self.assertEqual(w_global, w_jp, f"Card body width drifted across font presets: {w_global} vs {w_jp}")

    def test_probe_3_internal_card_scroll_does_not_conflict_with_outer_list_scroll(self) -> None:
        """Probe 3: Plain wheel scrolls outer list; Shift+Wheel and focused Up/Down scroll card body only; recycle resets scroll."""
        recs = []
        for i in range(25):
            if i > 0:
                recs.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            txt = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6" if i == 0 else f"Short line {i + 1}"
            recs.append(Record(cmd_id=6, cmd_name="print", args=["Pecorine", txt]))
        self._open_records(recs)

        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.app.update()

        card0 = self._find_visible_card(0)
        self.assertIsNotNone(card0)
        self.assertEqual(card0.txt_body.yview()[0], 0.0)
        self.assertEqual(self.app._as_scroll_y, 0.0)

        # 1. Plain <MouseWheel> over card body scrolls outer list only
        card0.txt_body.event_generate("<MouseWheel>", delta=-120)
        self.app.update_idletasks()
        self.assertGreater(self.app._as_scroll_y, 0.0, "Plain MouseWheel over card body must scroll outer list")
        self.assertEqual(card0.txt_body.yview()[0], 0.0, "Plain MouseWheel must not scroll card body internally")

        # Reset outer scroll to 0
        self.app._on_as_scrollbar("moveto", "0.0")
        self.app.update_idletasks()
        card0 = self._find_visible_card(0)
        self.assertEqual(self.app._as_scroll_y, 0.0)

        # 2. Shift+<MouseWheel> scrolls card body internally only
        card0.txt_body.event_generate("<Shift-MouseWheel>", delta=-120, state=0x0001)
        self.app.update_idletasks()
        self.assertGreater(card0.txt_body.yview()[0], 0.0, "Shift+MouseWheel must scroll 6-line card body internally")
        self.assertEqual(self.app._as_scroll_y, 0.0, "Shift+MouseWheel must not scroll outer All Script list")

        # 3. Focused <Down> / <Up> scrolls card body internally without scrolling outer list
        self.app.deiconify()
        self.app.update()
        try:
            card0.txt_body.yview_moveto(0.0)
            card0.txt_body.event_generate("<Button-1>", x=4, y=4)
            card0.txt_body.focus_force()
            self.app.update()
            card0.txt_body.event_generate("<Down>")
            self.app.update()
            down_y = card0.txt_body.yview()[0]
            self.assertGreater(down_y, 0.0, "Focused <Down> must scroll >3-line card internally")
            self.assertEqual(self.app._as_scroll_y, 0.0, "Focused <Down> must not scroll outer list")
            card0.txt_body.event_generate("<Up>")
            self.app.update()
            self.assertLess(card0.txt_body.yview()[0], down_y, "Focused <Up> must scroll >3-line card back up")
            self.assertEqual(self.app._as_scroll_y, 0.0, "Focused <Up> must not scroll outer list")
        finally:
            self.app.withdraw()

        # 4. Recycle that card to bottom -> internal scroll resets to 0.0
        self.app._on_as_scrollbar("moveto", "1.0")
        self.app.update_idletasks()
        self.assertEqual(card0.txt_body.yview()[0], 0.0, "Recycled card must reset internal yview to 0.0")

    def test_probe_4_active_box_highlight_and_all_script_preview_removal(self) -> None:
        """Probe 4: Active highlight + marker updates in-place; All Script Preview removed while Dialogue Preview works."""
        self._open_records(self._make_n_box_records(5, with_meta=False))
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "Dialogue Preview")

        # Enter All Script -> Preview disabled & unchecked, title is "All Script"
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertFalse(self.app.var_preview_compiled.get())
        self.assertEqual(str(self.app.cb_compiled.cget("state")), "disabled")
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "All Script")

        # Attempt to toggle Preview inside All Script stays OFF
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.assertFalse(self.app.var_preview_compiled.get())
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "All Script")

        # Active Box Highlight updates in-place on click
        card0 = self._find_visible_card(0)
        card1 = self._find_visible_card(1)
        self.assertIn("▶", card0.lbl_badge.cget("text"))
        self.assertIn("◆", card1.lbl_badge.cget("text"))
        self.assertEqual(int(card0.cget("highlightthickness")), 2)
        self.assertEqual(int(card1.cget("highlightthickness")), 1)

        self.app._on_as_card_click(card1)
        self.app.update_idletasks()
        self.assertEqual(self.app.current_box_idx, 1)
        self.assertIn("◆", card0.lbl_badge.cget("text"))
        self.assertIn("▶", card1.lbl_badge.cget("text"))
        self.assertEqual(int(card0.cget("highlightthickness")), 1)
        self.assertEqual(int(card1.cget("highlightthickness")), 2)

        # Return to Dialogue Mode -> Preview works with pink nameplate & pink ▼
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertEqual(str(self.app.cb_compiled.cget("state")), "normal")
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "Dialogue Preview")
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_nameplate")), 1)
        self.assertEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_arrow")), 1)

    def test_probe_5_quick_edit_raw_breaks_multisegment_binary_roundtrip_and_s09b_lock_parity(self) -> None:
        """Probe 5: Segment-aware Quick Edit, View-Aware sync, 4-seg binary round-trip, 1-op Undo/Redo, and S09b Lock parity."""
        doc = self._open_records([
            Record(cmd_id=12, cmd_name="touch", args=["vo_4seg"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 1\nLine 1b", "ex0"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 2 {0}", "ex1"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 3", "ex2"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 4", "ex3"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Second Box"]),
        ])
        orig_jp_uid0 = doc.boxes[0].uid
        orig_jp_val0 = self.app._original_jp_by_uid[orig_jp_uid0]
        orig_bin = doc.to_binary()

        # Bottom tabs: Quick Edit beside Raw Commands (lbl_raw_title preserved)
        self.assertTrue(hasattr(self.app, "btn_tab_quick_edit"))
        self.assertTrue(hasattr(self.app, "btn_tab_raw_commands"))
        self.assertEqual(self.app.btn_tab_raw_commands.cget("text"), "Raw Commands")
        self.assertEqual(self.app.lbl_raw_title.cget("text"), "Raw Commands")

        # Entering All Script auto-selects Quick Edit; plain surface (no ruler, no red tags)
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertEqual(self.app._bottom_tab, "quick_edit")
        seg_widgets = getattr(self.app, "_qe_seg_widgets", [])
        self.assertEqual(len(seg_widgets), 4, "4-segment box must expose 4 separate Quick Edit editors")
        for w in seg_widgets:
            self.assertEqual(w.tag_ranges("line_overflow"), ())

        # View-Aware Sync in All Script: typing patches active card in-place, ZERO _render_continuous_view calls
        with patch.object(self.app, "_render_continuous_view", wraps=self.app._render_continuous_view) as spy_render:
            seg_widgets[0].delete("1.0", "end")
            seg_widgets[0].insert("1.0", "Edited Seg 1\nSecond line")
            self.app._on_quick_edit_changed()

            seg_widgets[1].delete("1.0", "end")
            seg_widgets[1].insert("1.0", "Hi {playername}!")
            self.app._on_quick_edit_changed()

            seg_widgets[3].delete("1.0", "end")
            seg_widgets[3].insert("1.0", "Edited Seg 4")
            self.app._on_quick_edit_changed()

            self.assertEqual(spy_render.call_count, 0, "Quick Edit typing must NEVER rebuild All Script pool")

        card0 = self._find_visible_card(0)
        self.assertIn("Edited Seg 1", card0.txt_body.get("1.0", "end-1c"))

        # Flush on navigation -> exactly ONE logical Undo transaction
        self.assertEqual(self.app.undo_journal.undo_depth, 0, "Keystrokes must not spam Undo before flush")
        self.app.on_next_box()
        self.assertEqual(self.app.undo_journal.undo_depth, 1, "Flushing Quick Edit must record exactly ONE Undo op")

        # Inspect underlying doc.records directly (NOT just snapshot fields)
        box0_recs = [r for r in doc.records if r.cmd_name == "print" and r.args[0] == "Pecorine"]
        self.assertEqual(len(box0_recs), 4)
        self.assertEqual(box0_recs[0].args, ["Pecorine", "Edited Seg 1\nSecond line", "ex0"])
        self.assertEqual(box0_recs[1].args, ["Pecorine", "Hi {0}!", "ex1"])
        self.assertEqual(box0_recs[2].args, ["Pecorine", "Orig Seg 3", "ex2"])
        self.assertEqual(box0_recs[3].args, ["Pecorine", "Edited Seg 4", "ex3"])

        # Binary round-trip preserves all 4 edited segments, voice_cue, kind, extra_args
        reloaded = StoryDocument.from_binary(doc.to_binary())
        self.assertEqual(reloaded.boxes[0].voice_cue, "vo_4seg")
        self.assertEqual([s.text for s in reloaded.boxes[0].segs], [
            "Edited Seg 1\nSecond line", "Hi {0}!", "Orig Seg 3", "Edited Seg 4"
        ])
        self.assertEqual([s.record.args[2:] for s in reloaded.boxes[0].segs], [
            ["ex0"], ["ex1"], ["ex2"], ["ex3"]
        ])

        # Undo restores exact original binary & records; Redo restores edited binary & records
        self.app.on_undo()
        self.assertEqual(doc.to_binary(), orig_bin)
        self.app.on_redo()
        reloaded_redo = StoryDocument.from_binary(doc.to_binary())
        self.assertEqual([s.text for s in reloaded_redo.boxes[0].segs], [
            "Edited Seg 1\nSecond line", "Hi {0}!", "Orig Seg 3", "Edited Seg 4"
        ])

        # Immutable JP key untouched
        cur_uid0 = doc.boxes[0].uid
        self.assertEqual(self.app._original_jp_by_uid[cur_uid0], orig_jp_val0)

        # Dialogue Preview OFF + Preview ON live sync without rebuilding All Script
        self.app.current_box_idx = 1
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        with patch.object(self.app, "_render_continuous_view") as spy_render_dlg:
            self.app._qe_seg_widgets[0].delete("1.0", "end")
            self.app._qe_seg_widgets[0].insert("1.0", "Quick Dialogue Sync")
            self.app._on_quick_edit_changed()
            self.assertEqual(spy_render_dlg.call_count, 0)
            self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), "Quick Dialogue Sync")

            self.app.var_preview_compiled.set(True)
            self.app._on_toggle_preview_compiled()
            self.app._qe_seg_widgets[0].delete("1.0", "end")
            self.app._qe_seg_widgets[0].insert("1.0", "[FF0000]Live Preview Sync[-]")
            self.app._on_quick_edit_changed()
            self.assertEqual(str(self.app.txt_dialogue_preview.cget("state")), "disabled")
            self.assertIn("Live Preview Sync", self.app.txt_dialogue_preview.get("1.0", "end-1c"))

        # Raw Commands active skips redundant Quick Edit rebuilds
        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()
        self.app._switch_bottom_tab("raw")
        with patch.object(self.app, "_rebuild_quick_edit_widgets") as spy_qe_build:
            self.app.on_prev_box()
            self.assertEqual(spy_qe_build.call_count, 0, "Raw Commands active must skip redundant Quick Edit rebuilds")

        # S09b Lock Parity & Pin Independence
        self.app._switch_bottom_tab("quick_edit")
        self.app.current_box_idx = 1
        self.app._update_views()
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))
        self.assertEqual(str(self.app.txt_dialogue.cget("state")), "normal")
        self.assertEqual(str(self.app._qe_seg_widgets[0].cget("state")), "normal")

        # Locking does not alter Pin; Pinning does not alter Lock
        self.assertFalse(self.app._is_speaker_pinned)
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        self.assertTrue(self.app.is_box_locked(1))

        # Editing locked box via Quick Edit matches Dialogue typing (ALLOWED) and Undo preserves lock
        self.app._qe_seg_widgets[0].delete("1.0", "end")
        self.app._qe_seg_widgets[0].insert("1.0", "Locked QE Edit")
        self.app._on_quick_edit_changed()
        self.app._flush_quick_edit_session()
        self.assertEqual(doc.boxes[1].clean_text, "Locked QE Edit")
        self.app.on_undo()
        self.assertTrue(self.app.is_box_locked(1), "Undo of locked box Quick Edit must preserve lock")

        # Speaker rename on locked box remains BLOCKED and preserves Pin
        self.app.speaker_var.set("Kyaru")
        self.assertFalse(self.app._commit_speaker_edit())
        self.assertTrue(self.app._is_speaker_pinned)

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS pre-patch AND post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_raw_commands_tab_name_and_binary_roundtrip_preserved(self) -> None:
        """Guard 1: Bottom Raw Commands title and lossless binary round-trip work pre & post patch."""
        doc = self._open_records([
            Record(cmd_id=32, cmd_name="cmd_32", args=["Sub"]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello"]),
        ])
        self.assertEqual(self.app.lbl_raw_title.cget("text"), "Raw Commands")
        reloaded = StoryDocument.from_binary(doc.to_binary())
        self.assertEqual([r.cmd_id for r in reloaded.records], [32, 35, 6])

    def test_guard_2_multisegment_box_snapshot_immutable_jp_keys_preserved(self) -> None:
        """Guard 2: BoxSnapshot.from_box() & immutable _original_jp_by_uid preserved."""
        doc = self._open_records([
            Record(cmd_id=12, cmd_name="touch", args=["vo_g2"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "JP 1", "a1"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "JP 2", "a2"]),
        ])
        uid = doc.boxes[0].uid
        self.assertEqual(self.app._original_jp_by_uid[uid], "JP 1JP 2")
        snap = BoxSnapshot.from_box(doc.boxes[0])
        self.assertEqual(snap.seg_texts, ["JP 1", "JP 2"])
        self.assertEqual(snap.raw_breaks, ["JP 1", "JP 2"])
        self.assertEqual(snap.extra_args, [["a1"], ["a2"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
