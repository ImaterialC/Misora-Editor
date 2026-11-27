#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S11c (v1.4.13) — Unified Single-Box Quick Edit (`Q-22` Only) Tests.

Failing-first Defect/Behavior Probes (6) and Regression Guards (3):
  - Probe 1: Single persistent `txt_quick_edit` (wrap="none"), `box.clean_text`,
             `[N segs]` badge, zero red overflow tags, no `qe_canvas`/`qe_inner_frame`.
  - Probe 2: Manual Dialogue Editor vs Quick Edit AST & binary parity under
             Approved Option A (all 5 mandatory literal assertions (a)-(e); no `.strip()` hacks).
  - Probe 3: Multi-keystroke Session 1 -> Flush 1 (undo_depth == 1) -> Session 2
             (same box) -> Flush 2 (undo_depth == 2) -> Undo/Redo restores exact
             4 segments & binary round-trip + JP cache/UID/lock survival.
  - Probe 4: S09b Lock Parity (locked box manual typing ALLOWED in both editors),
             Pin perpendicular to Lock independence, View-Aware sync (0 rebuilds),
             and single-fire Ctrl+Z / Ctrl+Y shortcut execution.
  - Probe 5: `sync_from_widget=False` defensive fallback in `_refresh_quick_edit_pane()`.
  - Probe 6: Dirty Quick Edit without FocusOut flushes cleanly before `_on_dialogue_edited()`
             (Part A) and `_on_card_text_edited()` (Part B) with exact Undo ordering.
  - Guard 1: Raw Commands title preserved + Box 0 hides editable Quick Edit cleanly.
  - Guard 2: S08 stress `_qe_seg_widgets[0]` compatibility.
  - Guard 3: Idempotent pack geometry & theme/font styling across repeated box switches.
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


class TestV15S11cQuickEditUnified(unittest.TestCase):
    """Failing-first Probes (6) and Regression Guards (3) for S11c (v1.4.13)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s11c_"))
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

    @staticmethod
    def _make_4seg_records(with_meta: bool = True) -> list[Record]:
        recs: list[Record] = []
        if with_meta:
            recs.extend([
                Record(cmd_id=0, cmd_name="fade", args=["Episode Title"]),
                Record(cmd_id=1, cmd_name="log", args=["Box 0 Synopsis Line 1\nLine 2"]),
                Record(cmd_id=32, cmd_name="cmd_32", args=["Chapter Subtitle"]),
            ])
        recs.extend([
            Record(cmd_id=12, cmd_name="touch", args=["vo_4seg"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 1\nLine 1b", "ex0"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 2 {0}", "ex1"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 3", "ex2"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig Seg 4", "ex3"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Neighbor Box", "nb0"]),
        ])
        return recs

    def _open_records(self, records: list[Record], name: str = "s11c_story.v2.txt") -> StoryDocument:
        doc = StoryDocument(records)
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p, reload_from_disk=True)
        self.app.update_idletasks()
        return self.app.current_doc

    def _find_visible_card(self, box_idx: int):
        for card in getattr(self.app, "_as_card_pool", ()):
            if getattr(card, "bound_box_idx", None) == box_idx:
                return card
        return None

    # ------------------------------------------------------------------
    # Failing-First Probes (MUST FAIL pre-patch, PASS post-patch)
    # ------------------------------------------------------------------
    def test_probe_1_quick_edit_uses_single_unified_textbox_with_box_clean_text(self) -> None:
        """Probe 1: Quick Edit uses ONE persistent txt_quick_edit (wrap='none'), box.clean_text, and [N segs] badge."""
        doc = self._open_records(self._make_4seg_records(with_meta=False))
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")
        self.assertTrue(self.app.txt_quick_edit.winfo_exists())
        self.assertEqual(str(self.app.txt_quick_edit.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_quick_edit.cget("state")), "normal")
        self.assertTrue(hasattr(self.app, "qe_scroll_x"), "Horizontal scrollbar qe_scroll_x must exist")
        self.assertTrue(hasattr(self.app, "qe_scroll_y"))

        seg_widgets = getattr(self.app, "_qe_seg_widgets", [])
        self.assertEqual(len(seg_widgets), 1, f"Expected single-element compatibility alias, got {len(seg_widgets)}")
        self.assertIs(seg_widgets[0], self.app.txt_quick_edit)

        self.assertEqual(self.app.txt_quick_edit.get("1.0", "end-1c"), doc.boxes[0].clean_text)
        self.assertTrue(hasattr(self.app, "lbl_qe_segs_badge"))
        self.assertEqual(self.app.lbl_qe_segs_badge.cget("text"), "[4 segs]")
        self.assertEqual(self.app.txt_quick_edit.tag_ranges("line_overflow"), ())
        self.assertEqual(self.app.txt_quick_edit.tag_ranges("gutter_overflow"), ())
        self.assertFalse(hasattr(self.app, "qe_canvas"), "Legacy qe_canvas must be removed")
        self.assertFalse(hasattr(self.app, "qe_inner_frame"), "Legacy qe_inner_frame must be removed")

        # Navigate to 1-segment box -> badge clears
        self.app.on_next_box()
        self.app.update_idletasks()
        self.assertEqual(self.app.lbl_qe_segs_badge.cget("text"), "")
        self.assertEqual(self.app.txt_quick_edit.get("1.0", "end-1c"), doc.boxes[1].clean_text)

    def test_probe_2_manual_dialogue_vs_quick_edit_ast_and_binary_parity(self) -> None:
        """Probe 2: Exact Option A AST & binary parity between Main Dialogue Editor and Unified Quick Edit."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")

        expected_before = "Edited Line 1\nHi {playername}!"
        # Fixture-specific to 4 segments with 3 cleared trailing segments (DEF-01 ' ' sentinel in to_binary)
        expected_after_reload = expected_before + " " * 3

        # Doc A: Edit Box 0 via Main Dialogue Editor (txt_dialogue + _on_dialogue_edited)
        doc_a = self._open_records(self._make_4seg_records(with_meta=False), name="parity_dialogue.v2.txt")
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", expected_before)
        self.assertTrue(self.app._on_dialogue_edited())

        dialogue_box = doc_a.boxes[0]
        dialogue_clean = dialogue_box.clean_text
        dialogue_speaker = dialogue_box.speaker
        dialogue_voice = dialogue_box.voice_cue
        dialogue_raw_breaks = [s.raw for s in dialogue_box.segs]
        dialogue_extra_args = [list(s.record.args[2:]) for s in dialogue_box.segs]
        dialogue_records = [(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc_a.records]
        dialogue_binary = doc_a.to_binary()

        # Doc B: Edit identical Box 0 via Unified Quick Edit
        doc_b = self._open_records(self._make_4seg_records(with_meta=False), name="parity_quick_edit.v2.txt")
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", expected_before)
        self.assertTrue(self.app._on_quick_edit_changed())
        self.assertTrue(self.app._flush_quick_edit_session())

        quick_edit_box = doc_b.boxes[0]
        quick_edit_binary = doc_b.to_binary()

        # (a) Pre-binary: exact clean_text parity without extra trailing spaces
        self.assertEqual(dialogue_clean, expected_before)
        self.assertEqual(quick_edit_box.clean_text, expected_before)

        # (b) Byte-identical binary parity
        self.assertEqual(dialogue_binary, quick_edit_binary)

        # (c) Post-reload literal parity (explicitly asserting 3 fixture-specific sentinel spaces; NO strip/rstrip)
        reloaded_dialogue = StoryDocument.from_binary(dialogue_binary)
        reloaded_quick_edit = StoryDocument.from_binary(quick_edit_binary)
        self.assertEqual(reloaded_dialogue.boxes[0].clean_text, expected_after_reload)
        self.assertEqual(reloaded_quick_edit.boxes[0].clean_text, expected_after_reload)

        # (d) Re-serialization stability (zero additional spaces added on reload/save cycles)
        self.assertEqual(reloaded_dialogue.to_binary(), dialogue_binary)
        self.assertEqual(reloaded_quick_edit.to_binary(), quick_edit_binary)

        # (e) Full record arguments & extra_args parity (including {playername} -> {0}, voice_cue, raw_breaks)
        self.assertEqual(quick_edit_box.speaker, dialogue_speaker)
        self.assertEqual(quick_edit_box.voice_cue, "vo_4seg")
        self.assertEqual(quick_edit_box.voice_cue, dialogue_voice)
        self.assertEqual([s.raw for s in quick_edit_box.segs], dialogue_raw_breaks)
        self.assertIn("Hi {0}!", dialogue_raw_breaks[0])
        self.assertEqual([list(s.record.args[2:]) for s in quick_edit_box.segs], dialogue_extra_args)
        self.assertEqual(dialogue_extra_args, [["ex0"], ["ex1"], ["ex2"], ["ex3"]])
        quick_edit_records = [(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc_b.records]
        self.assertEqual(quick_edit_records, dialogue_records)

    def test_probe_3_pre_mutation_snapshot_undo_restores_exact_4_segments_and_binary_roundtrip(self) -> None:
        """Probe 3: Multi-keystroke Session 1 + same-box Session 2 Undo/Redo & JP cache/UID/lock survival."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")

        doc = self._open_records(self._make_4seg_records(with_meta=False))
        # Lock neighbor box 1 and seed sync cache to verify metadata survival across Edit/Undo/Redo
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.app.current_box_idx = 0
        self.app._update_views()

        box0 = doc.boxes[0]
        b0_uid = box0.uid
        orig_jp_val = self.app._original_jp_by_uid.get(b0_uid, box0.clean_text)
        self.app.sync_manager.register_jp_key(b0_uid, orig_jp_val)

        orig_binary = doc.to_binary()
        orig_segs = [s.text for s in box0.segs]
        orig_records = [(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records]
        orig_jp_map = dict(self.app._original_jp_by_uid)
        orig_cache = dict(self.app.sync_manager.jp_source_cache)
        orig_locked = set(self.app._locked_box_uids)

        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

        # Session 1: multiple keystrokes before Flush 1 -> ZERO per-keypress undo spam
        for step_tx in ("Step 1", "Step 1 + 2", "Session 1\nFinal Line"):
            self.app.txt_quick_edit.delete("1.0", "end")
            self.app.txt_quick_edit.insert("1.0", step_tx)
            self.assertTrue(self.app._on_quick_edit_changed())
            self.assertEqual(self.app.undo_journal.undo_depth, 0, "Typing must not spam Undo before flush")

        self.assertTrue(self.app._flush_quick_edit_session())
        self.assertEqual(self.app.undo_journal.undo_depth, 1, "Flush 1 must record EXACTLY 1 Undo delta")
        recs_after_s1 = [(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records]
        self.assertEqual(doc.boxes[0].segs[0].raw, "Session 1\nFinal Line")
        self.assertEqual([s.raw for s in doc.boxes[0].segs[1:]], ["", "", ""])

        # Session 2 on SAME box (no navigation) -> Flush 2 records EXACTLY 1 more delta
        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "Session 2 Edited")
        self.assertTrue(self.app._on_quick_edit_changed())
        self.assertEqual(self.app.undo_journal.undo_depth, 1)
        self.assertTrue(self.app._flush_quick_edit_session())
        self.assertEqual(self.app.undo_journal.undo_depth, 2, "Flush 2 on same box must record EXACTLY 1 more delta")

        post_s2_binary = doc.to_binary()
        recs_after_s2 = [(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records]
        self.assertEqual(self.app._original_jp_by_uid, orig_jp_map)
        self.assertEqual(self.app.sync_manager.jp_source_cache, orig_cache)
        self.assertEqual(self.app._locked_box_uids, orig_locked)

        # Helper: replace_box allocates a fresh Record.uid on Undo/Redo while migrating
        # immutable JP keys cleanly from old_uid -> new_uid without leaking old keys.
        b1_uid = doc.boxes[1].uid
        b1_jp_val = self.app._original_jp_by_uid[b1_uid]
        def _assert_uid_caches_migrated() -> None:
            cur_uid0 = doc.boxes[0].uid
            self.assertIsNotNone(cur_uid0)
            self.assertEqual(self.app._original_jp_by_uid.get(cur_uid0), orig_jp_val)
            self.assertEqual(self.app._original_jp_by_uid.get(b1_uid), b1_jp_val)
            self.assertEqual(len(self.app._original_jp_by_uid), len(orig_jp_map))
            self.assertEqual(self.app.sync_manager.jp_source_cache.get(cur_uid0), orig_jp_val)
            self.assertEqual(self.app.sync_manager.jp_source_cache.get(b1_uid), orig_cache[b1_uid])
            self.assertEqual(len(self.app.sync_manager.jp_source_cache), len(orig_cache))
            self.assertEqual(self.app._locked_box_uids, orig_locked)
            self.assertTrue(self.app.is_box_locked(1))

        # Undo #1: reverts Session 2 only -> back to Session 1 text and doc.records
        self.app.on_undo()
        self.app.update_idletasks()
        self.assertEqual(doc.boxes[0].clean_text, "Session 1\nFinal Line")
        self.assertEqual(self.app.txt_quick_edit.get("1.0", "end-1c"), "Session 1\nFinal Line")
        self.assertEqual([(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records], recs_after_s1)
        _assert_uid_caches_migrated()

        # Undo #2: restores exact original 4 segments, binary round-trip, badge, and caches
        self.app.on_undo()
        self.app.update_idletasks()
        self.assertEqual(len(doc.boxes[0].segs), 4)
        self.assertEqual([s.text for s in doc.boxes[0].segs], orig_segs)
        self.assertEqual([(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records], orig_records)
        self.assertEqual(doc.to_binary(), orig_binary)
        self.assertEqual(self.app.lbl_qe_segs_badge.cget("text"), "[4 segs]")
        _assert_uid_caches_migrated()

        # Redo #1 -> Redo #2: restores Session 2 binary, records, and caches
        self.app.on_redo()
        self.app.on_redo()
        self.app.update_idletasks()
        self.assertEqual(doc.to_binary(), post_s2_binary)
        self.assertEqual([(r.cmd_id, r.cmd_name, r.category, list(r.args)) for r in doc.records], recs_after_s2)
        _assert_uid_caches_migrated()

    def test_probe_4_s09b_lock_parity_and_view_aware_sync_preserved(self) -> None:
        """Probe 4: Locked-box manual typing ALLOWED in QE & Dialogue, Pin_|_Lock, View-Aware sync, single-fire Ctrl+Z/Y."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")

        doc = self._open_records(self._make_4seg_records(with_meta=False))
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        # Lock Box 0 -> both txt_quick_edit and txt_dialogue remain state="normal" (S09b Row 1 ALLOWED)
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(0))
        self.assertEqual(str(self.app.txt_quick_edit.cget("state")), "normal")
        self.assertEqual(str(self.app.txt_dialogue.cget("state")), "normal")

        # Actively type into locked box via Quick Edit (with View-Aware 0 rebuilds check)
        with patch.object(self.app, "_render_continuous_view", wraps=self.app._render_continuous_view) as spy_render:
            self.app.txt_quick_edit.delete("1.0", "end")
            self.app.txt_quick_edit.insert("1.0", "Locked Quick Edit Allowed")
            self.assertTrue(self.app._on_quick_edit_changed())
            self.assertTrue(self.app._flush_quick_edit_session())
            self.assertEqual(spy_render.call_count, 0)
        card0 = self._find_visible_card(0)
        self.assertIsNotNone(card0)
        self.assertIn("Locked Quick Edit Allowed", card0.txt_body.get("1.0", "end-1c"))
        self.assertEqual(doc.boxes[0].clean_text, "Locked Quick Edit Allowed")
        self.assertTrue(self.app.is_box_locked(0))

        # Switch to Dialogue View (Preview OFF), actively type into same locked box via txt_dialogue
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Locked Dialogue Allowed")
        self.assertTrue(self.app._on_dialogue_edited())
        self.assertEqual(doc.boxes[0].clean_text, "Locked Dialogue Allowed")
        self.assertEqual(self.app.txt_quick_edit.get("1.0", "end-1c"), "Locked Dialogue Allowed")
        self.assertTrue(self.app.is_box_locked(0))

        # Single-fire Ctrl+Z and Ctrl+Y with dirty Quick Edit session active
        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "Dirty Before CtrlZ")
        self.assertTrue(self.app._on_quick_edit_changed())
        self.app.deiconify()
        self.app.update()
        try:
            self.app.txt_quick_edit.focus_force()
            self.app.update()
            with patch.object(self.app, "on_undo", wraps=self.app.on_undo) as spy_undo:
                self.app.txt_quick_edit.event_generate("<Control-z>")
                self.app.update()
                self.assertEqual(spy_undo.call_count, 1, "Ctrl+Z must fire on_undo() exactly ONCE")
            self.assertEqual(doc.boxes[0].clean_text, "Locked Dialogue Allowed")

            with patch.object(self.app, "on_redo", wraps=self.app.on_redo) as spy_redo:
                self.app.txt_quick_edit.event_generate("<Control-y>")
                self.app.update()
                self.assertEqual(spy_redo.call_count, 1, "Ctrl+Y must fire on_redo() exactly ONCE")
            self.assertEqual(doc.boxes[0].clean_text, "Dirty Before CtrlZ")
        finally:
            self.app.withdraw()

        # Undo preserves Translation Lock; Speaker rename remains blocked & Pin_|_Lock independent
        self.app.on_undo()
        self.assertTrue(self.app.is_box_locked(0))
        self.assertFalse(self.app._is_speaker_pinned)
        self.app._on_toggle_pin_speaker()
        self.assertTrue(self.app._is_speaker_pinned)
        self.app.speaker_var.set("Kyaru")
        self.assertFalse(self.app._commit_speaker_edit())
        self.assertTrue(self.app._is_speaker_pinned)
        self.assertTrue(self.app.is_box_locked(0))
        self.app.on_toggle_lock_current_box()
        self.assertFalse(self.app.is_box_locked(0))
        self.assertTrue(self.app._is_speaker_pinned)

        # Dialogue Preview ON live sync from Quick Edit without rebuilding All Script
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        with patch.object(self.app, "_render_continuous_view") as spy_render_prev:
            self.app.txt_quick_edit.delete("1.0", "end")
            self.app.txt_quick_edit.insert("1.0", "[FF0000]Live Preview Sync[-]")
            self.app._on_quick_edit_changed()
            self.assertEqual(spy_render_prev.call_count, 0)
            self.assertEqual(str(self.app.txt_dialogue_preview.cget("state")), "disabled")
            self.assertIn("Live Preview Sync", self.app.txt_dialogue_preview.get("1.0", "end-1c"))

    def test_probe_5_external_mutation_flushes_without_sync_from_widget_overwrite(self) -> None:
        """Probe 5: External model mutation while QE dirty flushes with sync_from_widget=False without overwriting model."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")

        doc = self._open_records(self._make_4seg_records(with_meta=False))
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        # Make Quick Edit session dirty
        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "QE Pending Edit")
        self.assertTrue(self.app._on_quick_edit_changed())
        self.assertTrue(self.app._qe_session["dirty"])

        # Simulate external model change + unsaved stale widget divergence
        doc.inject_box(0, None, "External Winner")
        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "Stale Uncommitted Widget Text")

        with patch.object(self.app, "_on_quick_edit_changed", wraps=self.app._on_quick_edit_changed) as spy_qe:
            self.app._refresh_quick_edit_pane()
            self.assertEqual(
                spy_qe.call_count,
                0,
                "_refresh_quick_edit_pane() external sync must pass sync_from_widget=False (never call _on_quick_edit_changed)",
            )

        # Authoritative external winner preserved in both model and txt_quick_edit
        self.assertEqual(doc.boxes[0].clean_text, "External Winner")
        self.assertEqual(self.app.txt_quick_edit.get("1.0", "end-1c"), "External Winner")
        self.assertEqual(self.app.undo_journal.undo_depth, 1, "Defensive fallback flush must record delta")
        self.assertIsNotNone(self.app._qe_session)
        self.assertFalse(self.app._qe_session["dirty"])
        self.assertEqual(self.app._qe_session["old_snapshot"], BoxSnapshot.from_box(doc.boxes[0]))

    def test_probe_6_dialogue_edit_while_quick_edit_dirty_flushes_cleanly(self) -> None:
        """Probe 6: Dirty QE without FocusOut flushes cleanly before _on_dialogue_edited() (Part A) and _on_card_text_edited() (Part B)."""
        self.assertTrue(hasattr(self.app, "txt_quick_edit"), "Unified txt_quick_edit widget must exist")

        # Part A: _on_dialogue_edited while Quick Edit is dirty (no FocusOut)
        doc_a = self._open_records(self._make_4seg_records(with_meta=False), name="p6_dialogue.v2.txt")
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()
        self.app._switch_bottom_tab("quick_edit")
        self.app.update_idletasks()
        orig_bin_a = doc_a.to_binary()

        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "QE Unflushed Part A")
        self.assertTrue(self.app._on_quick_edit_changed())
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Dialogue Edit After QE")
        self.assertTrue(self.app._on_dialogue_edited())

        self.assertEqual(self.app.undo_journal.undo_depth, 2, "Must record QE flush then Dialogue delta in order")
        self.assertEqual(doc_a.boxes[0].clean_text, "Dialogue Edit After QE")
        self.app.on_undo()
        self.assertEqual(doc_a.boxes[0].clean_text, "QE Unflushed Part A")
        self.app.on_undo()
        self.assertEqual(len(doc_a.boxes[0].segs), 4)
        self.assertEqual(doc_a.to_binary(), orig_bin_a)

        # Part B: _on_card_text_edited while Quick Edit is dirty (no FocusOut)
        doc_b = self._open_records(self._make_4seg_records(with_meta=False), name="p6_card.v2.txt")
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app._switch_bottom_tab("quick_edit")
        self.app.update_idletasks()
        orig_bin_b = doc_b.to_binary()

        self.app.txt_quick_edit.delete("1.0", "end")
        self.app.txt_quick_edit.insert("1.0", "QE Unflushed Part B")
        self.assertTrue(self.app._on_quick_edit_changed())
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

        compat_card_txt = tk.Text(self.app)
        try:
            compat_card_txt.insert("1.0", "Card Text Edit After QE")
            self.assertTrue(self.app._on_card_text_edited(0, compat_card_txt))
        finally:
            compat_card_txt.destroy()

        self.assertEqual(self.app.undo_journal.undo_depth, 2, "Must record QE flush then CardEdit delta in order")
        self.assertEqual(doc_b.boxes[0].clean_text, "Card Text Edit After QE")
        self.app.on_undo()
        self.assertEqual(doc_b.boxes[0].clean_text, "QE Unflushed Part B")
        self.app.on_undo()
        self.assertEqual(len(doc_b.boxes[0].segs), 4)
        self.assertEqual(doc_b.to_binary(), orig_bin_b)

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS pre-patch AND post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_raw_commands_tab_name_and_box0_quick_edit_safety(self) -> None:
        """Guard 1: Raw Commands title preserved; Box 0 disables/hides editable Quick Edit; binary round-trip intact."""
        doc = self._open_records(self._make_4seg_records(with_meta=True))
        self.assertEqual(self.app.btn_tab_raw_commands.cget("text"), "Raw Commands")
        self.assertEqual(self.app.lbl_raw_title.cget("text"), "Raw Commands")

        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app._on_as_box0_click()
        self.app.update_idletasks()

        self.assertTrue(self.app.is_box0_active)
        self.assertEqual(len(getattr(self.app, "_qe_seg_widgets", [])), 0)
        if hasattr(self.app, "txt_quick_edit"):
            self.assertFalse(bool(self.app._is_widget_packed(self.app.txt_quick_edit)))
            self.assertTrue(bool(self.app._is_widget_packed(self.app.lbl_qe_placeholder)))
            self.assertEqual(self.app.lbl_qe_segs_badge.cget("text"), "")

        reloaded = StoryDocument.from_binary(doc.to_binary())
        self.assertEqual(reloaded.get_metadata()["title"], "Episode Title")
        self.assertEqual(reloaded.get_metadata()["subtitle"], "Chapter Subtitle")

    def test_guard_2_s08_stress_quick_edit_benchmark_compatibility(self) -> None:
        """Guard 2: `_qe_seg_widgets[0]` compatibility alias supports S08 stress edit/sync/flush flow."""
        doc = self._open_records(self._make_4seg_records(with_meta=False))
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        seg_widgets = getattr(self.app, "_qe_seg_widgets", [])
        self.assertGreaterEqual(len(seg_widgets), 1)
        self.assertIsInstance(seg_widgets[0], tk.Text)
        if hasattr(self.app, "txt_quick_edit"):
            self.assertIs(seg_widgets[0], self.app.txt_quick_edit)

        seg_widgets[0].delete("1.0", "end")
        seg_widgets[0].insert("1.0", "S08 Stress Compat Edit")
        self.app._on_quick_edit_changed()
        card0 = self._find_visible_card(0)
        self.assertIsNotNone(card0)
        self.assertIn("S08 Stress Compat Edit", card0.txt_body.get("1.0", "end-1c"))
        self.app._flush_quick_edit_session()
        if hasattr(self.app, "txt_quick_edit"):
            self.assertEqual(doc.boxes[0].clean_text, "S08 Stress Compat Edit")
        else:
            self.assertIn("S08 Stress Compat Edit", doc.boxes[0].clean_text)
            self.assertEqual(doc.boxes[0].segs[0].text, "S08 Stress Compat Edit")

    def test_guard_3_quick_edit_pack_geometry_idempotent_across_box_switches(self) -> None:
        """Guard 3: Repeated editable -> Box 0 -> editable -> editable switches keep pack geometry & theme styling intact."""
        self._open_records(self._make_4seg_records(with_meta=True))
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        # Cycle: editable (box 0) -> Box 0 metadata -> editable (box 1) -> editable (box 0)
        self.app._on_as_box0_click()
        self.app.update_idletasks()
        self.assertEqual(len(getattr(self.app, "_qe_seg_widgets", [])), 0)

        card1 = self._find_visible_card(1)
        self.assertIsNotNone(card1)
        self.app._on_as_card_click(card1)
        self.app.update_idletasks()
        self.assertGreaterEqual(len(getattr(self.app, "_qe_seg_widgets", [])), 1)

        card0 = self._find_visible_card(0)
        self.assertIsNotNone(card0)
        self.app._on_as_card_click(card0)
        self.app.update_idletasks()
        self.assertGreaterEqual(len(getattr(self.app, "_qe_seg_widgets", [])), 1)

        if hasattr(self.app, "txt_quick_edit"):
            slaves = self.app.qe_body_wrap.pack_slaves()
            self.assertEqual(
                slaves,
                [self.app.qe_scroll_y, self.app.qe_scroll_x, self.app.txt_quick_edit],
                f"Unexpected pack slave order/duplicates: {slaves}",
            )
            self.assertFalse(self.app._is_widget_packed(self.app.lbl_qe_placeholder))

            # Verify live theme/font update keeps txt_quick_edit synchronized
            self.app.dialogue_font_family = misora.PRESET_JP
            self.app._apply_theme_and_fonts_live(save=False)
            self.app.update_idletasks()
            expected_font = self.app._get_dialogue_font_tuple(self.app.dialogue_font_size)
            self.assertEqual(
                str(self.app.txt_quick_edit.cget("bg")),
                str(self.app.theme["bg_editor"]),
            )
            self.assertIn(expected_font[0], str(self.app.txt_quick_edit.cget("font")))


if __name__ == "__main__":
    unittest.main()
