#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S11d (v1.4.14) Verification Suite — Import from XUAT UX & Editor Productivity:
  - Q-06: MouseWheel label / checkbox / scope_cmb / empty-state propagation in ImportFromXUATDialog
          without clobbering focus-gated tk.Text inner scroll
  - Q-07: Per-group tri-state Select All headers (single-visual ttk.Button, O(1) guard,
          Missing/Locked exclusion, filter-agnostic toggle, tooltip, rebuild hygiene)
  - Q-08: Multi-line Box 0 Synopsis import (empty-with-no-key skip, non-empty import/Undo/Pass 3,
          cleared-in-editor import via _original_metadata_by_path, unconditional has_v inner scroll,
          U-18 Box 0 immunity, Document Identity Guard coverage)
  - Q-09: Archiving header cleanup (zero "Import Complete —") & Pass 1/3..3/3 progress labels
  - Q-10: Select All / Deselect All Box controls in gd_header across Dialogue & All Script views + Box 0
  - Q-11: Safe MTL Globe (🌐) button (Google/DeepL URLs only, clipboard copy on dialogue, Box 0 safe)
  - Q-12: Window title episode metadata (sanitized/<=65 char truncation, edit/Undo/cache-hit tab switch/close)

Regression Guards (2):
  - Guard 1: S11 Document Identity Guard & U-11 pre-pass actor exclusion remain intact
  - Guard 2: S11c unified txt_quick_edit & S11b strict Translation\\en\\Text scanner remain intact
"""
from __future__ import annotations

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

import misora  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.xuat_cleanup import AppliedXuatRecord, classify_cleanup_candidates  # noqa: E402
from core.xuat_index import build_xuat_index, resolve_xuat_text_roots  # noqa: E402


def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class _DummyWheelEvent:
    def __init__(self, delta: int = -120) -> None:
        self.delta = delta


class S11dTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s11d_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patches = [
            patch.object(misora, "CONFIG_PATH", self.config_path),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=False),
        ]
        for p in self.patches:
            p.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.xuat_archive_dir = self.tmp_dir / "backups" / "xuat_archive"

    def tearDown(self) -> None:
        try:
            dlg = getattr(self.app, "_import_xuat_dialog", None)
            if dlg is not None and dlg.winfo_exists():
                dlg._on_close()
        except Exception:
            pass
        try:
            cdlg = getattr(self.app, "_xuat_cleanup_dialog", None)
            if cdlg is not None and cdlg.winfo_exists():
                cdlg._on_close()
        except Exception:
            pass
        try:
            if hasattr(self.app, "logger") and self.app.logger:
                self.app.logger.close()
        except Exception:
            pass
        try:
            if self.app is not None:
                self.app.destroy()
        except Exception:
            pass
        self.app = None
        for p in reversed(self.patches):
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_xuat_tree(self) -> tuple[Path, Path]:
        proj_dir = self.tmp_dir / "proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir, text_dir

    def _open_story(self, doc: StoryDocument, name: str = "s11d_story.v2.txt") -> Path:
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p)
        return p


class TestV15S11dImportUxProductivity(S11dTestBase):
    """4 failing-first Probes + 2 Regression Guards for S11d (v1.4.14)."""

    def test_probe_1_import_mousewheel_over_labels_and_tristate_group_select_all(self) -> None:
        """[Probe 1] Q-06 recursive MouseWheel (preserving Text inner scroll, covering scope_cmb & empty labels) + Q-07 tri-state group headers."""
        proj_dir, text_dir = self._make_xuat_tree()
        (text_dir / "Main.txt").write_text(
            "第一章=Chapter 1\n"
            "プロローグ=Prologue\n"
            "ペコリーヌ=Pecorine\n"
            "重複セリフ=Dup A\n"
            "ロックセリフ=Locked EN\n"
            "一致セリフ=Matched EN\n",
            encoding="utf-8",
        )
        (text_dir / "Alt.txt").write_text(
            "重複セリフ=Dup B\n",
            encoding="utf-8",
        )
        self.app._set_project_folder(proj_dir)

        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["プロローグ"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "重複セリフ"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "ロックセリフ"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "未翻訳なし"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "一致セリフ"]),
        ])
        self._open_story(doc, "probe1.v2.txt")
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()

        idx = build_xuat_index([proj_dir])
        dlg = self.app.on_import_from_xuat(xuat_index=idx)
        self.assertIsNotNone(dlg)
        dlg.update_idletasks()

        # Q-06: Verify recursive MouseWheel bound on child labels, checkboxes, section headers, scope_cmb
        row_dup = dlg._rows[0]
        card = row_dup["frame"]
        labels = [w for w in _collect_descendants(card) if isinstance(w, tk.Label)]
        self.assertTrue(labels, "Expected card tk.Label descendants")
        for lbl in labels:
            self.assertTrue(
                bool(lbl.bind("<MouseWheel>")),
                f"Expected <MouseWheel> bound on child label {lbl.cget('text')!r}",
            )
        self.assertTrue(bool(row_dup["cb_skip"].bind("<MouseWheel>")))

        # Section header child labels also have <MouseWheel>
        sec_labels = [
            w for w in _collect_descendants(dlg.rows_frame)
            if isinstance(w, tk.Label) and "Dialogue Boxes" in str(w.cget("text"))
        ]
        self.assertTrue(sec_labels)
        self.assertTrue(bool(sec_labels[0].bind("<MouseWheel>")))

        # scope_cmb explicitly bound to _on_outer_mousewheel to block accidental dropdown changes
        combos = [w for w in _collect_descendants(card) if isinstance(w, ttk.Combobox)]
        self.assertEqual(len(combos), 1)
        scope_cmb = combos[0]
        self.assertTrue(bool(scope_cmb.bind("<MouseWheel>")))
        with patch.object(dlg.list_canvas, "yview_scroll") as mock_yscroll:
            before_scope = row_dup["var_scope"].get()
            func_name = scope_cmb.bind("<MouseWheel>")
            # Invoke via _on_outer_mousewheel contract directly via Tcl cmd check & call
            res = dlg._on_outer_mousewheel(_DummyWheelEvent(-120))
            self.assertEqual(res, "break")
            mock_yscroll.assert_called()
            self.assertEqual(row_dup["var_scope"].get(), before_scope)
            self.assertIn("_on_outer_mousewheel", func_name)

        # tk.Text widgets retain focus-gated inner scroll (NOT overwritten by recursive _on_outer_mousewheel)
        txt_r = row_dup["txt_right"]
        self.assertNotIn("_on_outer_mousewheel", txt_r.bind("<MouseWheel>"))

        # Empty-state placeholder label gets explicit <MouseWheel> binding when no boxes match
        orig_boxes = list(doc.boxes)
        try:
            doc.boxes = []
            dlg._populate_rows()
            empty_labels = [w for w in _collect_descendants(dlg.rows_frame) if isinstance(w, tk.Label)]
            self.assertTrue(empty_labels, "Expected empty-state placeholder label inside rows_frame")
            self.assertTrue(bool(empty_labels[0].bind("<MouseWheel>")))
        finally:
            doc.boxes = orig_boxes
            dlg._populate_rows()
            dlg.update_idletasks()

        # Q-07: Tri-state group Select All buttons & inspectable state map
        self.assertTrue(hasattr(dlg, "_group_select_states"))
        self.assertTrue(hasattr(dlg, "_group_select_buttons"))
        for gk in ("metadata", "actors", "dialogue"):
            self.assertIn(gk, dlg._group_select_buttons)
            btn = dlg._group_select_buttons[gk]
            self.assertIsInstance(btn, ttk.Button)
            self.assertEqual(dlg._group_select_states[gk], "all")
            self.assertEqual(btn.cget("text"), "[x] Select All")
            self.assertTrue(hasattr(btn, "_tooltip"))
            self.assertIn("all filters", btn._tooltip.text.lower())

        # O(1) re-entrancy guard + Missing & Locked exclusions + filter-agnostic toggling
        dlg._set_filter("duplicates")  # only row 0 visible
        with patch.object(dlg, "_update_group_header_state", wraps=dlg._update_group_header_state) as spy_upd:
            dlg._on_group_select_all("dialogue")
            self.assertEqual(spy_upd.call_count, 1, "Bulk toggle must call _update_group_header_state once")

        self.assertEqual(dlg._group_select_states["dialogue"], "none")
        self.assertEqual(dlg._group_select_buttons["dialogue"].cget("text"), "[ ] Select All")
        # Both visible duplicate (idx 0) and filtered-out matched row (idx 3) were deselected (var_skip=True)
        self.assertTrue(dlg._rows[0]["var_skip"].get())
        self.assertTrue(dlg._rows[3]["var_skip"].get())
        # Missing row (idx 2, 0 candidates) stays ineligible / untouched
        self.assertFalse(dlg._rows[2]["var_skip"].get())
        # Locked row (idx 1) stays locked/skipped
        self.assertTrue(dlg._rows[1]["var_skip"].get())

        # Partial state when 1 eligible row is toggled back ON
        dlg._rows[0]["var_skip"].set(False)
        self.assertEqual(dlg._group_select_states["dialogue"], "partial")
        self.assertEqual(dlg._group_select_buttons["dialogue"].cget("text"), "[-] Select All")

        # Clicking header on partial deselects all eligible -> none
        dlg._on_group_select_all("dialogue")
        self.assertEqual(dlg._group_select_states["dialogue"], "none")
        self.assertEqual(dlg._group_select_buttons["dialogue"].cget("text"), "[ ] Select All")
        self.assertTrue(dlg._rows[0]["var_skip"].get())

        # Reload rebuilds state cleanly with zero stale button references
        dlg._populate_rows()
        self.assertEqual(dlg._group_select_states["dialogue"], "all")

    def test_probe_2_synopsis_multiline_import_and_archiving_progress_labels(self) -> None:
        """[Probe 2] Q-08 all 3 Synopsis cases + Identity Guard + U-18 + Pass 3; Q-09 clean header & Pass 1/3..3/3 progress."""
        proj_dir, text_dir = self._make_xuat_tree()
        jp_syn_multi = "一行目あらすじ\n二行目あらすじ\n三行目あらすじ\n四行目あらすじ\n五行目あらすじ\n六行目あらすじ"
        en_syn_multi = "Line 1 summary\nLine 2 summary\nLine 3 summary\nLine 4 summary\nLine 5 summary\nLine 6 summary"
        jp_syn_cleared = "消されたあらすじの日本語原文"
        en_syn_cleared = "Restored synopsis imported into cleared empty field"
        jp_syn_long_nowrap = "長文ノーブレイク" * 10
        en_syn_long_nowrap = "WordWrappedSynopsisWithoutNewlines " * 6

        (text_dir / "Syn.txt").write_text(
            "第一章=Chapter 1\n"
            + jp_syn_multi.replace("\n", "\\n")
            + "="
            + en_syn_multi.replace("\n", "\\n")
            + "\n"
            + f"{jp_syn_cleared}={en_syn_cleared}\n"
            + f"{jp_syn_long_nowrap}={en_syn_long_nowrap}\n"
            + "セリフ=Dialogue line\n",
            encoding="utf-8",
        )
        self.app._set_project_folder(proj_dir)
        idx = build_xuat_index([proj_dir])

        # Case (a): Genuinely empty synopsis with zero source key -> skipped cleanly
        doc_empty = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=[""]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ"]),
        ])
        self._open_story(doc_empty, "syn_empty.v2.txt")
        dlg_a = self.app.on_import_from_xuat(xuat_index=idx)
        self.assertIsNotNone(dlg_a)
        self.assertFalse(any(r.get("field") == "summary" for r in dlg_a._metadata_rows))
        dlg_a._on_close()

        # Case (b): Non-empty multi-line JP synopsis -> word wrap, 5 lines, U-18 immunity, Identity Guard, Undo/Redo, Pass 3
        doc_multi = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=[jp_syn_multi.replace("\n", "\\n")]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ"]),
        ])
        p_multi = self._open_story(doc_multi, "syn_multi.v2.txt")

        # Document Identity Guard must detect external summary edit before Apply
        dlg_guard = self.app.on_import_from_xuat(xuat_index=idx)
        self.assertIsNotNone(dlg_guard)
        syn_rows = [r for r in dlg_guard._metadata_rows if r.get("field") == "summary"]
        self.assertEqual(len(syn_rows), 1)
        srow = syn_rows[0]
        self.assertEqual(int(srow["txt_left"].cget("height")), 5)
        self.assertEqual(str(srow["txt_left"].cget("wrap")), "word")
        self.assertEqual(str(srow["txt_right"].cget("wrap")), "word")
        self.assertEqual(srow["lbl_left_overflow"].cget("text"), "")
        self.assertEqual(srow["lbl_right_overflow"].cget("text"), "")

        self.app.current_doc.set_metadata(summary="Modified outside dialog")
        self.assertFalse(dlg_guard._on_apply_import(), "Identity Guard must abort when Box 0 summary changed externally")
        dlg_guard._on_close()

        # Reload clean multi-line story & test unconditional has_v inner scroll on long word-wrapped summary + Apply/Undo/Redo
        doc_nowrap = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=[jp_syn_long_nowrap]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ"]),
        ])
        self._open_story(doc_nowrap, "syn_nowrap.v2.txt")
        dlg_nw = self.app.on_import_from_xuat(xuat_index=idx)
        nw_srow = [r for r in dlg_nw._metadata_rows if r.get("field") == "summary"][0]
        dlg_nw._focused_box_widget = nw_srow["txt_right"]
        with patch.object(nw_srow["txt_right"], "yview_scroll") as spy_inner_scroll:
            # Synthesize <MouseWheel> via event callback lookup
            dlg_nw._focused_box_widget.focus_set()
            # Trigger the bound _on_wheel callback by invoking tcl eval on the bound command or focus event
            nw_srow["txt_right"].event_generate("<MouseWheel>", delta=-120)
            self.app.update_idletasks()
            spy_inner_scroll.assert_called()
        dlg_nw._on_close()

        # Re-open multi-line story cleanly for Apply + Pre-Apply prompt + Undo/Redo + Pass 3 verification
        self._open_story(doc_multi, "syn_multi2.v2.txt")
        live_multi = self.app.current_doc
        dlg_b = self.app.on_import_from_xuat(xuat_index=idx)
        dlg_b.var_archive_xuat.set(False)
        dlg_b.var_auto_word_wrap.set(True)  # Box 0 must stay exempt from auto word wrap (U-18)
        prompts: list[str] = []

        def _capture_yesno(_title, msg, **_kw):
            prompts.append(msg)
            return True

        with patch.object(misora.messagebox, "askyesno", side_effect=_capture_yesno):
            self.assertTrue(dlg_b._on_apply_import())
        self.assertTrue(prompts and "Synopsis" in prompts[0])
        self.assertEqual(live_multi.get_metadata()["summary"], en_syn_multi)
        self.app.on_undo()
        self.assertEqual(live_multi.get_metadata()["summary"], jp_syn_multi)
        self.app.on_redo()
        self.assertEqual(live_multi.get_metadata()["summary"], en_syn_multi)

        # Pass 3 archiving includes Box #0 (Synopsis) multi-line right-side match
        analysis = classify_cleanup_candidates(idx, live_multi, applied_records=())
        syn_cands = [c for c in analysis.candidates if "Synopsis" in c.reason]
        self.assertTrue(syn_cands, "Expected Pass 3 to classify multi-line Synopsis entry")
        self.assertEqual(syn_cands[0].tier, "already_translated_unique")

        # Case (c): Story opened with JP synopsis -> cleared to "" in-editor -> survives tab switch -> imported via _original_metadata_by_path
        doc_cleared = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=[jp_syn_cleared]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ"]),
        ])
        p_cleared = self._open_story(doc_cleared, "syn_cleared.v2.txt")
        self.app.current_doc.set_metadata(summary="")  # cleared in-editor!
        self.assertEqual(self.app.current_doc.get_metadata()["summary"], "")

        # Switch away to another tab and back via cache hit -> snapshot MUST remain immutable JP
        self._open_story(doc_empty, "other_tab.v2.txt")
        self.app.open_file(p_cleared)
        self.assertEqual(self.app.current_doc.get_metadata()["summary"], "")

        dlg_c = self.app.on_import_from_xuat(xuat_index=idx)
        dlg_c.var_archive_xuat.set(False)
        c_rows = [r for r in dlg_c._metadata_rows if r.get("field") == "summary"]
        self.assertEqual(len(c_rows), 1)
        self.assertEqual(c_rows[0]["txt_left"].get("1.0", "end-1c"), "")
        self.assertEqual(c_rows[0]["txt_right"].get("1.0", "end-1c"), en_syn_cleared)
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            self.assertTrue(dlg_c._on_apply_import())
        self.assertEqual(self.app.current_doc.get_metadata()["summary"], en_syn_cleared)

        # Reload refreshes _original_metadata_by_path; close prunes it cleanly (no S08 cache leak)
        norm_cleared = misora.ImportFromXUATDialog._norm_file_str(p_cleared)
        self.assertIn(norm_cleared, getattr(self.app, "_original_metadata_by_path", {}))
        self.app.close_file(p_cleared)
        self.assertNotIn(norm_cleared, getattr(self.app, "_original_metadata_by_path", {}))

        # Q-09: Archiving sub-header cleanup & Pass 1/3..3/3 progress labels
        cdlg = misora.XuatCleanupDialog(
            self.app,
            xuat_index=idx,
            doc=live_multi,
            applied_records=(),
            mode="post_import",
            xuat_roots=[text_dir],
        )
        try:
            all_lbl_texts = [str(w.cget("text")) for w in _collect_descendants(cdlg) if isinstance(w, tk.Label)]
            self.assertFalse(any("Import Complete —" in txt for txt in all_lbl_texts))
            self.assertTrue(any("XUAT Translation Archiving" in txt for txt in all_lbl_texts))
            self.assertTrue(hasattr(misora.XuatCleanupDialog, "_format_scan_progress"))
            p1 = misora.XuatCleanupDialog._format_scan_progress(100, 300)
            p2 = misora.XuatCleanupDialog._format_scan_progress(101, 300)
            p3 = misora.XuatCleanupDialog._format_scan_progress(300, 300)
            p_empty = misora.XuatCleanupDialog._format_scan_progress(1, 1)
            self.assertIn("Pass 1/3", p1)
            self.assertIn("(100/100)", p1)
            self.assertIn("Pass 2/3", p2)
            self.assertIn("(1/100)", p2)
            self.assertIn("Pass 3/3", p3)
            self.assertIn("(100/100)", p3)
            self.assertIn("Scanning XUAT entries", p_empty)
        finally:
            cdlg._on_close()

    def test_probe_3_select_all_box_excludes_box0_and_preserves_translation_lock(self) -> None:
        """[Probe 3] Q-10 All/None box controls in gd_header across Dialogue & All Script views + Box 0 exclusion + locks."""
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Title"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Line 2"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", "Line 3"]),
        ])
        self._open_story(doc, "probe3.v2.txt")
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        locked_snapshot = set(self.app._locked_box_uids)

        self.assertTrue(hasattr(self.app, "btn_select_all_boxes"))
        self.assertTrue(hasattr(self.app, "btn_deselect_all_boxes"))
        self.assertTrue(hasattr(self.app.btn_select_all_boxes, "_tooltip"))
        self.assertTrue(hasattr(self.app.btn_deselect_all_boxes, "_tooltip"))
        self.assertFalse(self.app._is_widget_packed(self.app.btn_select_all_boxes))

        # Enable Select Box mode in Dialogue view
        self.app.var_select_box_mode.set(True)
        self.app._on_toggle_select_box_mode()
        self.app.update_idletasks()
        self.assertTrue(self.app._is_widget_packed(self.app.btn_select_all_boxes))
        self.assertTrue(self.app._is_widget_packed(self.app.btn_deselect_all_boxes))

        # Select All while Box 0 is active -> selects 0..2, never -1, locks preserved
        self.app.is_box0_active = True
        self.app._update_views()
        self.assertTrue(self.app._is_widget_packed(self.app.btn_select_all_boxes))
        self.app._on_select_all_boxes()
        self.assertEqual(self.app._selected_boxes, {0, 1, 2})
        self.assertNotIn(-1, self.app._selected_boxes)
        self.assertEqual(self.app._locked_box_uids, locked_snapshot)

        # Switch to All Script view -> buttons STAY visible
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertTrue(self.app._is_widget_packed(self.app.btn_select_all_boxes))
        self.assertTrue(self.app._is_widget_packed(self.app.btn_deselect_all_boxes))

        # Deselect clears all, Select All re-selects {0, 1, 2}
        self.app._on_deselect_all_boxes()
        self.assertEqual(self.app._selected_boxes, set())
        self.app._on_select_all_boxes()
        self.assertEqual(self.app._selected_boxes, {0, 1, 2})

        # Disable Select Box mode -> hides cleanly & clears selection
        self.app.var_select_box_mode.set(False)
        self.app._on_toggle_select_box_mode()
        self.assertFalse(self.app._is_widget_packed(self.app.btn_select_all_boxes))
        self.assertFalse(self.app._is_widget_packed(self.app.btn_deselect_all_boxes))
        self.assertEqual(self.app._selected_boxes, set())

    def test_probe_4_mtl_globe_copies_clipboard_opens_official_site_and_window_title_metadata(self) -> None:
        """[Probe 4] Q-11 MTL Globe (Google/DeepL only, safe clipboard, Box 0 safe) + Q-12 dynamic episode window title."""
        long_title_a = "Episode 1:\nA Very Long\tTitle Exceeding Sixty Five Characters Overall"
        sub_a = "Morning\nArc"
        doc_a = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=[long_title_a]),
            Record(cmd_id=32, cmd_name="cmd_32", args=[sub_a]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "おはようございます！"]),
        ])
        doc_b = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Episode 2: Next"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Evening"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "こんにちは"]),
        ])

        p_a = self._open_story(doc_a, "story_a.v2.txt")
        self.app.is_box0_active = False
        self.app.current_box_idx = 0

        # Q-12: Check initial title bar on Story A (sanitized newlines/tabs, truncated <= 65 chars + '…', lbl_gd_title unchanged)
        title_a = self.app.title()
        self.assertIn("story_a.v2.txt", title_a)
        self.assertIn("—", title_a)
        meta_suffix_a = title_a.split(" — ", 1)[1]
        self.assertNotIn("\n", meta_suffix_a)
        self.assertNotIn("\t", meta_suffix_a)
        self.assertLessEqual(len(meta_suffix_a), 65)
        self.assertTrue(meta_suffix_a.endswith("…"))
        self.assertEqual(self.app.lbl_gd_title.cget("text"), "Dialogue")

        # Box 0 live edit updates title; Undo reverts
        self.app.is_box0_active = True
        self.app._update_views()
        self.app.var_box0_title.set("Edited Title")
        self.app._on_box0_metadata_edited()
        self.app._dirty_state_changed()  # mirrors real event path (L12960-12961)
        self.assertIn("Edited Title", self.app.title())
        self.app.on_undo()
        self.assertNotIn("Edited Title", self.app.title())
        self.assertIn("Episode 1:", self.app.title())

        # Cache-hit tab switch between two clean tabs refreshes title immediately without stale metadata
        p_b = self._open_story(doc_b, "story_b.v2.txt")
        self.assertIn("Episode 2: Next (Evening)", self.app.title())
        self.app.open_file(p_a)  # cache hit on clean tab A
        self.assertIn("story_a.v2.txt", self.app.title())
        self.assertNotIn("Episode 2: Next", self.app.title())

        # Q-11: MTL Drawer Globe buttons
        self.app.is_box0_active = False
        self.app.current_box_idx = 0
        for eng in self.app._MTL_DRAWER_ENGINE_ORDER:
            self.app._set_mtl_drawer_engine_enabled(eng, True)
        self.app.on_open_translator_assistant()
        self.app.update_idletasks()

        cards = self.app._mtl_drawer_cards
        self.assertIn("btn_globe", cards["Google"])
        self.assertIn("btn_globe", cards["DeepL"])
        self.assertNotIn("btn_globe", cards["XUAT Cache"])
        self.assertNotIn("btn_globe", cards["Local / Sugoi"])
        self.assertNotIn("btn_globe", cards["LLM / OpenAI"])

        with patch("misora.webbrowser.open") as mock_open:
            cards["Google"]["btn_globe"].invoke()
            self.assertEqual(self.app.safe_clipboard_get(), "おはようございます！")
            mock_open.assert_called_with("https://translate.google.com/", new=2)

            cards["DeepL"]["btn_globe"].invoke()
            mock_open.assert_called_with("https://www.deepl.com/translator", new=2)

            # Box 0 active -> opens URL without overwriting clipboard
            self.app.safe_clipboard_set("KEEP_CLIPBOARD")
            self.app.is_box0_active = True
            cards["Google"]["btn_globe"].invoke()
            self.assertEqual(self.app.safe_clipboard_get(), "KEEP_CLIPBOARD")
            mock_open.assert_called_with("https://translate.google.com/", new=2)

        # Closing last tab resets window title cleanly to base string
        self.app.close_file(p_b)
        self.app.is_dirty = False
        if p_a in self.app.open_documents:
            self.app.open_documents[p_a]["dirty"] = False
        self.app.close_file(p_a)
        self.assertEqual(self.app.title(), "Misora: Story Editor")

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_import_document_identity_guard_and_prepass_actor_exclusion_intact(self) -> None:
        """[Guard 1] S11 Document Identity Guard & U-11 pre-pass actor exclusion remain intact."""
        proj_dir, text_dir = self._make_xuat_tree()
        (text_dir / "Actors.txt").write_text(
            "ペコリーヌ=Pecorine\n"
            "長いセリフテスト=Long dialogue test\n",
            encoding="utf-8",
        )
        self.app._set_project_folder(proj_dir)
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "長いセリフテスト"]),
        ])
        self._open_story(doc, "guard1.v2.txt")
        idx = build_xuat_index([proj_dir])

        dlg = self.app.on_import_from_xuat(xuat_index=idx)
        self.assertIsNotNone(dlg)
        try:
            # S11 Identity Guard aborts if doc/metadata mutated externally
            self.app.current_doc.set_metadata(title="External mutation")
            self.assertFalse(dlg._on_apply_import())
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # U-11 Pre-Pass actor exclusion keeps 0 speaker rows in cleanup candidates
        self.app.current_doc.inject_box(0, "Pecorine", "Long dialogue test")
        analysis = classify_cleanup_candidates(
            idx, self.app.current_doc, applied_records=(AppliedXuatRecord(text_dir / "Actors.txt", 1, "ペコリーヌ", "Pecorine", 0),)
        )
        self.assertFalse(any(c.raw_key == "ペコリーヌ" for c in analysis.candidates))

    def test_guard_2_s11c_unified_quick_edit_and_s11b_strict_en_text_scanner_intact(self) -> None:
        """[Guard 2] S11c unified txt_quick_edit & S11b strict Translation\\en\\Text scanner remain intact."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"))
        self.assertEqual(str(self.app.txt_quick_edit.cget("wrap")), "none")

        root = self.tmp_dir / "strict_test"
        bad_ja = root / "BepInEx" / "Translation" / "ja" / "Text"
        good_en = root / "BepInEx" / "Translation" / "en" / "Text"
        bad_ja.mkdir(parents=True)
        good_en.mkdir(parents=True)

        self.assertEqual(resolve_xuat_text_roots([bad_ja]), [])
        self.assertEqual(resolve_xuat_text_roots([good_en]), [good_en])


if __name__ == "__main__":
    unittest.main()
