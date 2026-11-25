#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S22 — Unified core/xuat_index.py & Separate Floating Import from XUAT Resolver (FEAT-14)
=========================================================================================
Failing-first regression test suite:
  - Probe 1: core/xuat_index.py strict Text-root scanning, backslash-parity unescape,
             NGUI-tag & {playername}/{0}-aware normalization, and O(1) MTLEngine lookup.
  - Probe 2: ImportFromXUATDialog auto-closes MTL drawer, paired fixed 3x50 read-only boxes,
             zero per-box Scrollbar widgets, overflow indicators, duplicate provenance/stepper,
             lock auto-skip & gray-out, per-box Skip, filter chips & separate speaker counts.
  - Probe 3: Pre-Apply confirmation prompt enumerating imported / lock-skipped / user-skipped /
             missing counts, mutate-before-undo single batch (source='xuat_import'), immutable JP
             key preservation, and zero XUAT .txt pruning.
  - Guard 1: Lightweight direct contract checks for S10, S06, and S21 invariants.
"""

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
from core.mtl_engine import MTLConfig, MTLEngine  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.text_encoding import write_atomic_encoded  # noqa: E402
from core.xunity_sync import XUnitySyncManager, escape_xuat_value, split_xuat_line  # noqa: E402


def _collect_descendants(widget):
    out = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class S22TestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s22_test_"))
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
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.app = None
        import gc
        gc.collect()
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _build_sample_xuat_tree(self) -> Path:
        proj_dir = self.tmp_dir / "proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "BepInEx" / "plugins").mkdir(parents=True, exist_ok=True)
        (proj_dir / "BepInEx" / "Translation" / "en" / "RedirectedResources").mkdir(parents=True, exist_ok=True)

        # Noise files that MUST be excluded
        (text_dir / "Story.missing.txt").write_text("MISSING_KEY=ShouldNotLoad\n", encoding="utf-8")
        (text_dir / "Story.report.txt").write_text("REPORT_KEY=ShouldNotLoad\n", encoding="utf-8")
        (text_dir / "_SUMMARY.txt").write_text("SUMMARY_KEY=ShouldNotLoad\n", encoding="utf-8")
        (text_dir / "_warnings.txt").write_text("WARN_KEY=ShouldNotLoad\n", encoding="utf-8")
        (proj_dir / "BepInEx" / "plugins" / "Plugin.txt").write_text("PLUGIN_KEY=ShouldNotLoad\n", encoding="utf-8")
        (proj_dir / "BepInEx" / "Translation" / "en" / "RedirectedResources" / "Res.txt").write_text(
            "RES_KEY=ShouldNotLoad\n", encoding="utf-8"
        )

        # Valid XUAT dictionaries (BOM + CRLF)
        main_txt = text_dir / "A_Main.txt"
        main_content = (
            "\ufeff"
            "# Comment line\r\n"
            "// Slash comment\r\n"
            "; Semicolon comment\r\n"
            "r:^regex$=Ignored\r\n"
            "sr:^sregex$=Ignored\r\n"
            "おはよう！=Good morning!\\nNice day.\\\\nKeepSlash\r\n"
            "こんにちは、{playername}！=Hello, {playername}!\r\n"
            "こんにちは=HelloOnly\r\n"
            "[rub:ふりがな]漢字[/rub]=KanjiBase\r\n"
            "Key\\=WithEquals=EqualsValue\r\n"
            "ペコリーヌ=Pecorine\r\n"
            "また明日ね=See you tomorrow\r\n"
            "主さま、お帰りなさいませ。=Welcome home, my Lord.\r\n"
        )
        main_txt.write_bytes(main_content.encode("utf-8"))

        dup_txt = text_dir / "B_Alt.txt"
        dup_txt.write_bytes("おはよう！=Morning everyone!\r\n".encode("utf-8"))
        return proj_dir


class TestP3S22ImportXUAT(S22TestBase):
    """Failing-first probes and guard for S22 (FEAT-14)."""

    def test_probe_1_xuat_index_strict_unescape_norm_and_o1(self):
        """[Probe 1 — core/xuat_index.py] Strict Text-root scan, parity unescape, NGUI/{playername} norm, O(1) lookup."""
        from core.xuat_index import build_xuat_index, unescape_xuat_value

        # Symmetric backslash-parity unescape: literal \n -> Enter, \\n preserved
        self.assertEqual(
            unescape_xuat_value(r"Line1\nLine2\\nLiteral\\\nLine3"),
            "Line1\n" + r"Line2\\nLiteral\\" + "\nLine3",
        )

        proj_dir = self._build_sample_xuat_tree()
        idx = build_xuat_index([proj_dir])

        # Excluded files & comments must NOT be indexed
        self.assertIsNone(idx.lookup_translation("MISSING_KEY"))
        self.assertIsNone(idx.lookup_translation("REPORT_KEY"))
        self.assertIsNone(idx.lookup_translation("SUMMARY_KEY"))
        self.assertIsNone(idx.lookup_translation("WARN_KEY"))
        self.assertIsNone(idx.lookup_translation("PLUGIN_KEY"))
        self.assertIsNone(idx.lookup_translation("RES_KEY"))
        self.assertIsNone(idx.lookup_translation("r:^regex$"))

        # First unescaped '=' split + parity unescape
        self.assertEqual(idx.lookup_translation("Key=WithEquals"), "EqualsValue")
        self.assertEqual(
            idx.lookup_translation("おはよう！"),
            "Good morning!\nNice day.\\\\nKeepSlash",
        )

        # NGUI-tag & {playername}/{0}-aware O(1) normalization (never strips {0}!)
        self.assertEqual(idx.lookup_translation("[FF0000]おはよう！[-]"), "Good morning!\nNice day.\\\\nKeepSlash")
        self.assertEqual(idx.lookup_translation("漢字"), "KanjiBase")
        self.assertEqual(idx.lookup_translation("こんにちは、{0}！"), "Hello, {playername}!")
        self.assertEqual(idx.lookup_translation("こんにちは"), "HelloOnly")

        # Duplicate provenance preserved deterministically
        dup_res = idx.lookup_candidates("おはよう！")
        self.assertEqual(dup_res.status, "duplicate")
        self.assertEqual(len(dup_res.candidates), 2)
        self.assertEqual(dup_res.candidates[0].file_path.name, "A_Main.txt")
        self.assertEqual(dup_res.candidates[1].file_path.name, "B_Alt.txt")

        # O(1) MTLEngine integration eliminates QW-E03 linear scan
        engine = MTLEngine(MTLConfig(active_engine="XUAT Cache", use_xuat_cache=True))
        self.assertEqual(
            engine.translate("[FF0000]おはよう！[-]", xuat_cache=idx),
            "Good morning!\nNice day.\\\\nKeepSlash",
        )

    def test_probe_2_import_dialog_paired_3x50_readonly_and_duplicates(self):
        """[Probe 2 — Dialog Contract] Auto-closes MTL drawer, fixed 3x50 read-only boxes, 0 scrollbars, duplicates, lock/skip."""
        proj_dir = self._build_sample_xuat_tree()
        self.app._set_project_folder(proj_dir)

        long_overflow = ("1234567890" * 6) + "\nLine 2\nLine 3\nLine 4"
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"]),
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "主さま、お帰りなさいませ。"]),
            Record(cmd_id=6, cmd_name="print", args=["キャル", long_overflow]),
            Record(cmd_id=6, cmd_name="print", args=["ユイ", "また明日ね"]),
        ])
        story_path = self.tmp_dir / "s22_story.v2.txt"
        story_path.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(story_path)

        # Lock Box 1 (index 1)
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        # Menu placement: in File menu, NOT inside MTL drawer
        file_labels = []
        for i in range(self.app.file_menu.index("end") + 1):
            try:
                lbl = self.app.file_menu.entrycget(i, "label")
                if lbl:
                    file_labels.append(lbl)
            except Exception:
                pass
        self.assertIn("Import from XUAT...", file_labels)

        mtl_desc = _collect_descendants(self.app.tab_mtl_frame)
        mtl_texts = [str(w.cget("text")) for w in mtl_desc if hasattr(w, "cget") and "text" in w.keys()]
        self.assertFalse(any("Import from XUAT" in t for t in mtl_texts))

        # Open MTL drawer, then open Import from XUAT -> must auto-close MTL drawer
        self.app._open_side_drawer("mtl")
        self.assertTrue(self.app._side_drawer_visible)

        dlg = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg)
        try:
            self.assertFalse(self.app._side_drawer_visible, "Opening Import from XUAT must auto-close MTL drawer")

            # Paired rows: fixed 3 lines x 50 digit-widths, strictly read-only, ZERO per-box Scrollbar widgets
            self.assertEqual(len(dlg._rows), 4)
            expected_safe_w = self.app._measure_dialogue_metrics("1234567890" * 5)["safe_w"]

            for row in dlg._rows:
                for txt in (row["txt_left"], row["txt_right"]):
                    self.assertEqual(str(txt.cget("state")), "disabled")
                    self.assertEqual(int(txt.cget("height")), 3)
                    self.assertEqual(str(txt.cget("wrap")), "none")
                row_desc = _collect_descendants(row["frame"])
                per_box_scrollbars = [
                    w for w in row_desc if isinstance(w, (tk.Scrollbar, ttk.Scrollbar))
                ]
                self.assertEqual(len(per_box_scrollbars), 0, "Paired rows must have ZERO per-box Scrollbar widgets")
                self.assertGreaterEqual(row["left_wrap"].winfo_reqwidth(), expected_safe_w)
                self.assertGreaterEqual(row["right_wrap"].winfo_reqwidth(), expected_safe_w)

            # Overflow indicator on Box 2 (long_overflow)
            ov_text = dlg._rows[2]["lbl_left_overflow"].cget("text")
            self.assertIn("▼", ov_text)
            self.assertIn("▶", ov_text)

            # Duplicate stepper & provenance on Box 0
            row0 = dlg._rows[0]
            self.assertIn("1/2", row0["lbl_dup_counter"].cget("text"))
            self.assertIn("A_Main.txt:", row0["lbl_provenance"].cget("text"))
            dlg._step_candidate(0, 1)
            self.assertIn("2/2", row0["lbl_dup_counter"].cget("text"))
            self.assertIn("B_Alt.txt:", row0["lbl_provenance"].cget("text"))

            # Locked Box 1 auto-skipped & Skip checkbox disabled
            row1 = dlg._rows[1]
            self.assertTrue(row1["var_skip"].get())
            self.assertEqual(str(row1["cb_skip"].cget("state")), "disabled")

            # Separate dialogue & speaker counts (GEM-R02)
            summary_txt = dlg.lbl_summary.cget("text")
            self.assertIn("Dialogue:", summary_txt)
            self.assertIn("Speakers:", summary_txt)

            # Filter chips: Missing shows only Box 2
            dlg._set_filter("missing")
            visible_missing = [r["box_idx"] for r in dlg._rows if r["frame"].winfo_manager()]
            self.assertEqual(visible_missing, [2])
            dlg._set_filter("all")
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

    def test_probe_3_pre_apply_prompt_atomic_undo_and_no_xuat_pruning(self):
        """[Probe 3 — Pre-Apply Prompt & Atomic Undo] Enumerates counts, single Undo batch, immutable JP key, 0 XUAT writes."""
        proj_dir = self._build_sample_xuat_tree()
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        xuat_snapshots = {p: p.read_bytes() for p in text_dir.glob("*.txt")}

        self.app._set_project_folder(proj_dir)

        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"]),
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "主さま、お帰りなさいませ。"]),
            Record(cmd_id=6, cmd_name="print", args=["キャル", "未翻訳セリフ"]),
            Record(cmd_id=6, cmd_name="print", args=["ユイ", "また明日ね"]),
        ])
        story_path = self.tmp_dir / "s22_apply.v2.txt"
        story_path.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(story_path)

        box0_uid = misora._get_box_uid(self.app.current_doc.boxes[0])
        self.assertEqual(self.app._original_jp_by_uid.get(box0_uid), "おはよう！")

        # Edit Box 0 locally first to verify lookup still uses immutable _original_jp_by_uid
        self.app.current_doc.inject_box(0, "ペコリーヌ", "Temp Local Edit")
        self.app._update_views()

        # Lock Box 1 (index 1)
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()

        dlg = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg)
        try:
            # User skips Box 3 (index 3), enables speaker translation
            dlg._rows[3]["var_skip"].set(True)
            dlg.var_translate_speakers.set(True)

            captured_prompts = []

            def fake_askyesno(title, msg, **kwargs):
                captured_prompts.append((title, msg))
                return True

            with patch.object(misora.messagebox, "askyesno", side_effect=fake_askyesno):
                applied = dlg._on_apply_import()

            self.assertTrue(applied)
            self.assertEqual(len(captured_prompts), 1)
            prompt_msg = captured_prompts[0][1]
            # Prompt must enumerate: (1) imported box, (2) lock-skipped box, (3) user-skipped box, (4) missing count
            self.assertIn("Box #1", prompt_msg)
            self.assertIn("Box #2", prompt_msg)
            self.assertIn("🔒", prompt_msg)
            self.assertIn("Box #4", prompt_msg)
            self.assertIn("Skip", prompt_msg)
            self.assertIn("1", prompt_msg)

            # Model state checks
            self.assertEqual(self.app.current_doc.boxes[0].segs[0].raw, "Good morning!\nNice day.\\\\nKeepSlash")
            self.assertEqual(self.app.current_doc.boxes[0].speaker, "Pecorine")
            self.assertEqual(self.app._original_jp_by_uid.get(box0_uid), "おはよう！")
            self.assertEqual(self.app.current_doc.boxes[1].clean_text, "主さま、お帰りなさいませ。")
            self.assertEqual(self.app.current_doc.boxes[3].clean_text, "また明日ね")

            # Single atomic Undo batch with source='xuat_import'
            self.assertTrue(self.app.undo_journal.can_undo())
            key = self.app.undo_journal._get_key(story_path)
            top_op = self.app.undo_journal._file_states[key].undo_stack[-1]
            self.assertTrue(all(getattr(d, "source", None) == "xuat_import" for d in top_op.deltas))

            self.app.on_undo()
            self.assertEqual(self.app.current_doc.boxes[0].clean_text, "Temp Local Edit")
            self.assertEqual(self.app.current_doc.boxes[0].speaker, "ペコリーヌ")

            # Zero XUAT .txt pruning / writes
            for p, orig_bytes in xuat_snapshots.items():
                self.assertEqual(p.read_bytes(), orig_bytes, f"XUAT file {p.name} must remain untouched")
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

    def test_guard_1_s10_s06_s21_contracts(self):
        """[Guard 1] Lightweight direct sanity checks for S10, S06, and S21 invariants."""
        self.assertEqual(split_xuat_line(r"A\=B=C"), (r"A\=B", "C"))
        self.assertEqual(escape_xuat_value("L1\nL2"), "L1\\nL2")

        mgr = XUnitySyncManager()
        mgr.register_jp_key(101, "元テキスト")
        mgr.register_jp_key(101, "上書き不可")
        self.assertEqual(mgr.get_jp_key(101), "元テキスト")

        lf_file = self.tmp_dir / "lf_guard.txt"
        write_atomic_encoded(lf_file, "a\nb\n", encoding="utf-8", newline="\n")
        self.assertNotIn(b"\r\n", lf_file.read_bytes())

        self.app._open_side_drawer("mtl")
        self.assertEqual(self.app._mtl_drawer_mode, "dialogue")
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.assertEqual(self.app._mtl_drawer_mode, "all_script")


if __name__ == "__main__":
    unittest.main(verbosity=2)
