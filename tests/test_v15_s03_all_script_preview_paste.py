#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5 Session S03: All Script Technique A, Leaked 3rd Window, Precision Preview & Lossless BoxSnapshot Paste."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import misora
from core.story_ast import BoxSnapshot, Record, StoryDocument


class TestV15S03AllScriptPreviewPaste(unittest.TestCase):
    """Failing-first Defect Probes (6) and Regression Guards (4) for S03 (v1.4.3)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s03_"))
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
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

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
        for p in reversed(self.patches):
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _load_synthetic_v2(self, records: list[Record], name: str = "s03_story.v2.txt") -> StoryDocument:
        doc = StoryDocument(records)
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p, reload_from_disk=True)
        self.app.update_idletasks()
        return self.app.current_doc

    def _make_150_box_records(self) -> list[Record]:
        recs: list[Record] = [
            Record(cmd_id=0, cmd_name="fade", args=["Episode 1: Benchmark"]),
            Record(cmd_id=1, cmd_name="log", args=["150-box synthetic benchmark summary."]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Chapter 1"]),
        ]
        for i in range(150):
            if i > 0:
                recs.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            if i % 5 == 0:
                recs.append(Record(cmd_id=12, cmd_name="touch", args=[f"vo_bench_{i:03d}"]))
                recs.append(Record(cmd_id=35, cmd_name="tag", args=[f"Narration line {i + 1}."]))
            else:
                sp = ["Pecorine", "Kokkoro", "Kyaru", "Yuuki"][i % 4]
                recs.append(Record(cmd_id=6, cmd_name="print", args=[sp, f"Line {i + 1} dialogue text."]))
        return recs

    # -------------------------------------------------------------------------
    # Defect / Behavior Probes (MUST FAIL pre-patch, PASS post-patch)
    # -------------------------------------------------------------------------
    def test_probe_1_no_third_window_leaked_in_all_script_and_preview(self) -> None:
        """Probe 1: gd_scroll_wrap is never packed simultaneously with continuous_wrap."""
        self._load_synthetic_v2([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello!"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration."]),
        ])
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "")
        self.assertNotEqual(self.app.continuous_wrap.winfo_manager(), "")

        # Toggle Preview ON and OFF while in All Script and call _update_empty_state_visibility()
        for prev_val in (True, False):
            self.app.var_preview_compiled.set(prev_val)
            self.app._on_toggle_preview_compiled()
            self.app._update_empty_state_visibility()
            self.app.update_idletasks()
            self.assertEqual(
                self.app.gd_scroll_wrap.winfo_manager(),
                "",
                f"gd_scroll_wrap leaked into layout during All Script (preview={prev_val})",
            )
            self.assertNotEqual(self.app.continuous_wrap.winfo_manager(), "")

    def test_probe_2_all_script_technique_a_single_text_and_150_box_nav(self) -> None:
        """Probe 2: 150-box All Script uses ONE read-only tk.Text (txt_all_script), click selects, double-click jumps."""
        self._load_synthetic_v2(self._make_150_box_records(), name="s03_150.v2.txt")

        t0 = time.perf_counter()
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Single read-only tk.Text widget active; zero 150-card widget explosion
        self.assertTrue(hasattr(self.app, "txt_all_script"))
        self.assertIsInstance(self.app.txt_all_script, tk.Text)
        self.assertEqual(str(self.app.txt_all_script.cget("state")), "disabled")
        self.assertEqual(self.app._card_widgets, {})
        self.assertEqual(len(self.app.cont_stream_frame.winfo_children()), 0)
        self.assertTrue(hasattr(self.app, "_all_script_block_ranges"))
        self.assertIn(-1, self.app._all_script_block_ranges)
        self.assertIn(149, self.app._all_script_block_ranges)

        # Single-click on box 42 selects it in-place and updates Raw View
        start_ln, _end_ln = self.app._all_script_block_ranges[42]
        self.app._on_all_script_click_at_index(f"{start_ln}.0")
        self.assertFalse(self.app.is_box0_active)
        self.assertEqual(self.app.current_box_idx, 42)
        raw_txt = self.app.txt_raw.get("1.0", "end-1c")
        self.assertIn("Line 43 dialogue text.", raw_txt)
        self.assertIn(">>", raw_txt)

        # Single-click on Box 0 (-1) activates Box 0 cleanly
        b0_start, _ = self.app._all_script_block_ranges[-1]
        self.app._on_all_script_click_at_index(f"{b0_start}.0")
        self.assertTrue(self.app.is_box0_active)

        # Double-click on box 42 jumps cleanly into Dialogue View at box 42
        self.app._on_all_script_activate_at_index(f"{start_ln}.0")
        self.app.update_idletasks()
        self.assertFalse(self.app.var_continuous_view.get())
        self.assertFalse(self.app.is_box0_active)
        self.assertEqual(self.app.current_box_idx, 42)

        # Double-click on Box 0 (-1) jumps cleanly into Dialogue View with is_box0_active=True
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()
        b0_start, _ = self.app._all_script_block_ranges[-1]
        self.app._on_all_script_activate_at_index(f"{b0_start}.0")
        self.app.update_idletasks()
        self.assertFalse(self.app.var_continuous_view.get())
        self.assertTrue(self.app.is_box0_active)

        print(
            f"\n[S03 Benchmark] 150-box Technique A render: {elapsed_ms:.2f} ms | "
            f"Python={platform.python_version()} Tk={tk.TkVersion} OS={platform.platform()}"
        )

    def test_probe_3_preview_clean_room_frames_and_narration_no_nameplate(self) -> None:
        """Probe 3: Dialogue Preview renders clean-room Pillow capsule, omits nameplate for narration, preserves bleed & cstyle sweep."""
        overwide = "1234567890" * 6
        self._load_synthetic_v2([
            Record(cmd_id=35, cmd_name="tag", args=[f"[FF0000]Narrator line[-]\n{overwide}"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "[00FF00]Spoken line[-]"]),
        ])

        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(True)
        self.app.current_box_idx = 0
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        # Narration must have NO nameplate item on dialogue_preview_canvas
        self.assertEqual(self.app.dialogue_preview_canvas.find_withtag("preview_nameplate"), ())
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_frame")), 3)
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("wrap")), "none")
        self.assertTrue(len(self.app.txt_dialogue_preview.tag_ranges("line_overflow")) >= 2)

        # Spoken line MUST draw nameplate and sweep old cstyle_* tags
        self.app.current_box_idx = 1
        self.app._update_views()
        self.app.update_idletasks()
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_nameplate")), 1)
        cstyle_tags = [t for t in self.app.txt_dialogue_preview.tag_names() if t.startswith("cstyle_")]
        self.assertFalse(any("#ff0000" in t for t in cstyle_tags))

    def test_probe_4_lossless_box_snapshot_replace_undo_redo_all_6_fields(self) -> None:
        """Probe 4: Replace paste preserves all 6 BoxSnapshot fields, skips locked boxes, and supports 1-step Undo/Redo."""
        doc = self._load_synthetic_v2([
            Record(cmd_id=12, cmd_name="touch", args=["vo_src_001"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Seg 1", "ex_p1"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Seg 2", "ex_p2"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Target 1 orig", "ex_t1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", "Locked orig", "ex_lock"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Target 3 orig", "ex_t3"]),
        ])

        # Lock box 2 (Kyaru)
        self.app.current_box_idx = 2
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(2))

        src_snap = BoxSnapshot.from_box(doc.boxes[0])
        narr_snap = BoxSnapshot(
            speaker="",
            voice_cue="vo_narr_009",
            kind="tag",
            seg_texts=["Narr A\r\n", "Narr B"],
            raw_breaks=["Narr A\r\n", "Narr B"],
            extra_args=[["ex_n1"], ["ex_n2"]],
        )
        third_snap = BoxSnapshot(
            speaker="Rei",
            voice_cue="vo_rei_003",
            kind="print",
            seg_texts=["Replaced 3"],
            raw_breaks=["Replaced 3"],
            extra_args=[["ex_r3"]],
        )

        orig_box1_snap = BoxSnapshot.from_box(doc.boxes[1])
        orig_box2_snap = BoxSnapshot.from_box(doc.boxes[2])
        orig_box3_snap = BoxSnapshot.from_box(doc.boxes[3])

        self.app._box_clipboard = [src_snap, narr_snap, third_snap]
        self.app._box_clipboard_text = "MOCK_CLIP_REPLACE"
        self.app.current_box_idx = 1

        with patch.object(self.app, "safe_clipboard_get", return_value="MOCK_CLIP_REPLACE"):
            self.app.on_box_paste(confirm=False, mode="replace")

        # Box 1 replaced losslessly on all 6 fields
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[1]), src_snap)
        # Box 2 locked -> untouched
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[2]), orig_box2_snap)
        # Box 3 replaced with third_snap (all 6 fields)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[3]), third_snap)

        # Undo restores original snapshots on all 6 fields
        self.app.on_undo()
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[1]), orig_box1_snap)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[2]), orig_box2_snap)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[3]), orig_box3_snap)

        # Redo restores replaced snapshots on all 6 fields
        self.app.on_redo()
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[1]), src_snap)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[2]), orig_box2_snap)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[3]), third_snap)

    def test_probe_5_failed_replace_paste_leaves_document_uncorrupted(self) -> None:
        """Probe 5: Mid-operation failure in Replace paste rolls back records, boxes, and Undo journal 100%."""
        doc = self._load_synthetic_v2([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Orig 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Orig 2"]),
        ])
        orig_v2 = doc.to_v2_text()
        orig_undo_depth = self.app.undo_journal.undo_depth

        snap_ok = BoxSnapshot(speaker="Kyaru", voice_cue="", kind="print", seg_texts=["New 1"])
        snap_fail = BoxSnapshot(speaker="Yuuki", voice_cue="", kind="print", seg_texts=["New 2"])
        self.app._box_clipboard = [snap_ok, snap_fail]
        self.app._box_clipboard_text = "MOCK_FAIL_CLIP"
        self.app.current_box_idx = 0

        real_replace = doc.replace_box
        call_count = [0]

        def flaky_replace(box_index: int, snapshot: BoxSnapshot) -> BoxSnapshot:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Simulated mid-paste failure")
            return real_replace(box_index, snapshot)

        with patch.object(self.app, "safe_clipboard_get", return_value="MOCK_FAIL_CLIP"), \
             patch.object(doc, "replace_box", side_effect=flaky_replace):
            self.app.on_box_paste(confirm=False, mode="replace")

        self.assertEqual(doc.to_v2_text(), orig_v2)
        self.assertEqual(self.app.undo_journal.undo_depth, orig_undo_depth)
        self.assertFalse(self.app.is_dirty)

    def test_probe_6_native_paste_box_insert_mode_preserves_full_snapshot(self) -> None:
        """Probe 6: Native Paste Box insert mode preserves all 6 BoxSnapshot fields and undoes in 1 step."""
        doc = self._load_synthetic_v2([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Base line"]),
        ])
        snap = BoxSnapshot(
            speaker="Kokkoro",
            voice_cue="vo_ins_007",
            kind="print",
            seg_texts=["Seg A\r\n", "Seg B"],
            raw_breaks=["Seg A\r\n", "Seg B"],
            extra_args=[["ex1"], ["ex2"]],
        )
        self.app._box_clipboard = [snap]
        self.app._box_clipboard_text = "MOCK_INS_CLIP"
        self.app.current_box_idx = 0

        with patch.object(self.app, "safe_clipboard_get", return_value="MOCK_INS_CLIP"):
            self.app.on_box_paste(confirm=False, mode="insert")

        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(BoxSnapshot.from_box(doc.boxes[1]), snap)

        self.app.on_undo()
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(doc.boxes[0].clean_text, "Base line")

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # -------------------------------------------------------------------------
    def test_guard_1_txt_continuous_plain_text_fallback_intact(self) -> None:
        """Guard 1: Plain .txt file in All Script mode uses editable txt_continuous fallback."""
        plain = self.tmp_dir / "plain_guard.txt"
        plain.write_text("Plain line 1\nPlain line 2", encoding="utf-8")
        self.app.open_file(plain, reload_from_disk=True)
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        self.assertIsNone(self.app.current_doc)
        self.assertEqual(str(self.app.txt_continuous.cget("state")), "normal")
        self.assertIn("Plain line 1", self.app.txt_continuous.get("1.0", "end-1c"))
        self.app.txt_continuous.insert("end-1c", "\nPlain line 3")
        self.app._commit_widget_edit(self.app.txt_continuous)
        self.assertTrue(self.app.is_dirty)
        self.assertIn("Plain line 3", self.app._plain_text_content)

    def test_guard_2_no_atlasadv_dependency_or_copyrighted_sprite(self) -> None:
        """Guard 2: Preview code has zero AtlasAdv dependencies and uses pure Pillow/Tk."""
        import re as _re
        asset_ref_re = _re.compile(r"AtlasAdv\.(?:png|jpg|unity3d|asset)|Image\.open\([^)]*AtlasAdv", _re.IGNORECASE)
        for rel in ("misora.py", "assets/preview_frames.py"):
            p = REPO_ROOT / rel
            if p.exists():
                self.assertIsNone(asset_ref_re.search(p.read_text(encoding="utf-8")), f"Found AtlasAdv asset ref in {rel}")

    def test_guard_3_cmd_id_35_32_and_adjacent_narration_separation_preserved(self) -> None:
        """Guard 3: Narration (cmd_id 35) and subtitle (cmd_id 32) remain separate across round-trip."""
        recs = [
            Record(cmd_id=0, cmd_name="fade", args=["Title"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Subtitle"]),
            Record(cmd_id=35, cmd_name="tag", args=["First narration"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Second narration"]),
        ]
        doc = StoryDocument(recs)
        raw_bin = doc.to_binary()
        doc2 = StoryDocument.from_binary(raw_bin)
        self.assertEqual(len(doc2.boxes), 2)
        self.assertEqual(doc2.boxes[0].kind, "tag")
        self.assertEqual(doc2.boxes[1].kind, "tag")
        self.assertTrue(any(r.cmd_id == 32 and r.args == ["Subtitle"] for r in doc2.records))
        self.assertEqual(sum(1 for r in doc2.records if r.cmd_id == 35), 2)

    def test_guard_4_ribbon_cut_persists_across_navigation(self) -> None:
        """Guard 4: Ribbon Cut on Dialogue text persists cleanly across Next -> Prev navigation."""
        doc = self._load_synthetic_v2([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello World"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Second Box"]),
        ])
        self.app.var_continuous_view.set(False)
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.update_idletasks()

        self.app.txt_dialogue.focus_set()
        self.app.txt_dialogue.tag_add("sel", "1.5", "1.11")
        self.app.on_text_cut()
        self.app.update()

        self.app.on_next_box()
        self.app.update_idletasks()
        self.app.on_prev_box()
        self.app.update_idletasks()

        self.assertEqual(doc.boxes[0].clean_text, "Hello")
        self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), "Hello")


if __name__ == "__main__":
    unittest.main()
