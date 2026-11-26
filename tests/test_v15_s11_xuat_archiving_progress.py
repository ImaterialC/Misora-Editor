#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S11 (v1.4.10) Verification Suite — Async XUAT Translation Archiving, Pre-Import Archive Checkbox,
Complete Global Speaker Exclusion, 1-Line 54d Metadata/Actor Import, & Unified Progress Controller.

Failing-first Defect/Behavior Probes (5):
  - Probe 1: Async XUAT archiving worker off main thread, batched ttk.Treeview (0 per-cand widgets),
             "XUAT Translation Archiving" title, cooperative cancel, & stale rejection.
  - Probe 2: Pre-import "Archive the XUAT translation" checkbox defaults True; unchecked shows inline
             warning and runs import-only (0 disk edits); checked launches archiving non-blockingly.
  - Probe 3: U-11 complete global speaker dictionary exclusion across Pass 1/2/3 & multi-file
             duplicates, while Dialogue/Title/Subtitle classify & Import speaker matching still works.
  - Probe 4: U-14 ImportFromXUATDialog 1-line 54d Metadata/Unique Actor rows, no Box 0 in dialogue,
             no Include Actor checkbox, both font presets parity, Document Identity Guard, Synopsis
             preservation, multi-seg speaker rename, and mid-op rollback.
  - Probe 5: U-12/U-13 Unified _ProgressTaskManager concurrent isolation, stale rejection, O(1)
             progress coalescing under 5000-msg flood with reliable terminal delivery, cancellable
             os.walk discovery in build_xuat_index(), & async Reload XUAT.

Regression Guards (2):
  - Guard 1: S07 SHA-256 StaleSourceError & mandatory archive-first intact.
  - Guard 2: core.xuat_cleanup & core.xuat_index remain free of tkinter & misora imports.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.font_manager import PRESET_GLOBAL, PRESET_JP  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.undo_journal import MetadataDelta  # noqa: E402
from core.xuat_cleanup import (  # noqa: E402
    AppliedXuatRecord,
    StaleSourceError,
    classify_cleanup_candidates,
    execute_cleanup,
)
from core.xuat_index import build_xuat_index  # noqa: E402


def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class S11TestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s11_"))
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
        self.app.xuat_archive_dir = self.tmp_dir / "backups" / "xuat_archive"

    def tearDown(self) -> None:
        try:
            if self.app is not None:
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

    def _make_xuat_tree(self) -> tuple[Path, Path]:
        proj_dir = self.tmp_dir / "proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir, text_dir

    def _open_story(self, doc: StoryDocument, name: str = "s11_story.v2.txt") -> Path:
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p)
        return p

    def _wait_until(self, predicate, timeout: float = 6.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.app.update()
            except tk.TclError:
                return False
            if predicate():
                return True
            time.sleep(0.01)
        return bool(predicate())


class TestV15S11XuatArchivingProgress(S11TestBase):
    """Failing-first probes (5) and regression guards (2) for S11 (v1.4.10)."""

    def test_probe_1_async_archiving_worker_batched_treeview_and_stale_rejection(self) -> None:
        """[Probe 1] Archiving scan runs off main thread, uses batched ttk.Treeview, supports cancel & stale rejection."""
        proj_dir, text_dir = self._make_xuat_tree()
        lines = []
        records = []
        applied = []
        large_file = text_dir / "Large.txt"
        for i in range(550):
            jp = f"セリフ番号_{i:04d}_テスト会話文"
            en = f"Translated dialogue line number {i:04d} for stress test."
            lines.append(f"{jp}={en}")
            records.append(Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", en if i >= 20 else jp]))
            records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            if i < 20:
                applied.append(AppliedXuatRecord(file_path=large_file, line_number=i + 1, raw_key=jp, value=en, box_index=i))
        large_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument(records)
        self.app._set_project_folder(proj_dir)
        self._open_story(doc, "probe1.v2.txt")

        worker_thread_ids: list[int] = []
        orig_classify = misora.classify_cleanup_candidates

        def spy_classify(*args, **kwargs):
            worker_thread_ids.append(threading.get_ident())
            return orig_classify(*args, **kwargs)

        with patch.object(misora, "classify_cleanup_candidates", side_effect=spy_classify):
            dlg = misora.XuatCleanupDialog(
                self.app,
                xuat_index=idx,
                doc=doc,
                applied_records=applied,
                source_fingerprints=idx.file_fingerprints,
                mode="post_import",
            )
            try:
                self.assertEqual(dlg.title(), "XUAT Translation Archiving")
                self.assertTrue(hasattr(dlg, "tree") and isinstance(dlg.tree, ttk.Treeview))
                # No per-candidate tk.Checkbutton widgets inside candidate area
                tree_parent_desc = _collect_descendants(dlg.tree.master)
                self.assertEqual(
                    [w for w in tree_parent_desc if isinstance(w, tk.Checkbutton)],
                    [],
                    "Candidate list must use ttk.Treeview, not per-candidate tk.Checkbuttons",
                )
                # Execute button disabled while scanning/inserting batches
                done = self._wait_until(
                    lambda: (not getattr(dlg, "_is_scanning", True)) and (getattr(dlg, "_batch_insert_job", "pending") is None),
                    timeout=8.0,
                )
                self.assertTrue(done, "Async archiving scan & batched Treeview insert did not finish in time")
                self.assertTrue(worker_thread_ids, "classify_cleanup_candidates was not called")
                self.assertNotEqual(
                    worker_thread_ids[0],
                    threading.main_thread().ident,
                    "classify_cleanup_candidates must execute off the main thread",
                )
                self.assertGreaterEqual(len(dlg.tree.get_children()), 500)
                self.assertEqual(str(dlg.btn_execute.cget("state")), "normal")
            finally:
                if dlg.winfo_exists():
                    dlg._on_close()

        # Cooperative cancel + stale token rejection
        gate = threading.Event()
        cancelled_observed: list[bool] = []

        def slow_classify(*args, **kwargs):
            cancel_ev = kwargs.get("cancel_event")
            gate.wait(timeout=2.0)
            cancelled_observed.append(bool(cancel_ev is not None and cancel_ev.is_set()))
            return orig_classify(*args, **kwargs)

        with patch.object(misora, "classify_cleanup_candidates", side_effect=slow_classify):
            dlg2 = misora.XuatCleanupDialog(
                self.app,
                xuat_index=idx,
                doc=doc,
                applied_records=applied,
                source_fingerprints=idx.file_fingerprints,
                mode="manual",
            )
            cancel_ev = dlg2._scan_cancel_event
            dlg2._on_close()
            self.assertTrue(cancel_ev.is_set(), "Closing dialog must signal cooperative cancel_event")
            gate.set()
            self._wait_until(lambda: bool(cancelled_observed), timeout=3.0)
            self.app.update()
            self.assertEqual(cancelled_observed, [True])

    def test_probe_2_pre_import_archive_checkbox_default_on_and_unchecked_import_only(self) -> None:
        """[Probe 2] 'Archive the XUAT translation' defaults True; unchecked is import-only with warning; checked opens Archiving."""
        proj_dir, text_dir = self._make_xuat_tree()
        main_txt = text_dir / "Main.txt"
        orig_content = (
            "第一章=Chapter 1: Awakening\n"
            "ペコリーヌ=Pecorine\n"
            "おはよう！=Good morning, my Lord!\n"
        )
        main_txt.write_text(orig_content, encoding="utf-8")
        orig_bytes = main_txt.read_bytes()

        self.app._set_project_folder(proj_dir)
        doc1 = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"]),
        ])
        self._open_story(doc1, "probe2_unchecked.v2.txt")

        dlg = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg)
        try:
            self.assertTrue(hasattr(dlg, "var_archive_xuat"))
            self.assertTrue(dlg.var_archive_xuat.get(), "'Archive the XUAT translation' must default to True")

            # Uncheck -> inline warning shown, import only (0 archiving dialog, 0 disk changes)
            dlg.var_archive_xuat.set(False)
            self.app.update_idletasks()
            self.assertTrue(bool(dlg.lbl_archive_optout_warning.winfo_manager()))
            self.assertTrue(dlg.lbl_archive_optout_warning.cget("text").strip())

            with patch.object(misora.messagebox, "askyesno", return_value=True):
                applied = dlg._on_apply_import()
            self.assertTrue(applied)
            self.assertIsNone(getattr(self.app, "_xuat_cleanup_dialog", None))
            self.assertEqual(main_txt.read_bytes(), orig_bytes, "Unchecked Archive must leave XUAT files 100% untouched")
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Checked -> launches XUAT Translation Archiving non-blockingly with non-speaker applied_records only
        doc2 = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "おはよう！"]),
        ])
        self._open_story(doc2, "probe2_checked.v2.txt")
        dlg2 = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg2)
        try:
            self.assertTrue(dlg2.var_archive_xuat.get())
            with patch.object(misora.messagebox, "askyesno", return_value=True):
                applied2 = dlg2._on_apply_import()
            self.assertTrue(applied2)
            cdlg = getattr(self.app, "_xuat_cleanup_dialog", None)
            self.assertIsNotNone(cdlg, "Checked Archive must launch XUAT Translation Archiving")
            self.assertEqual(cdlg.title(), "XUAT Translation Archiving")
            # Applied records must NOT include speaker records
            applied_keys = {r.raw_key for r in cdlg.applied_records}
            self.assertNotIn("ペコリーヌ", applied_keys)
            self.assertIn("おはよう！", applied_keys)
            self._wait_until(lambda: not getattr(cdlg, "_is_scanning", False), timeout=5.0)
        finally:
            cdlg = getattr(self.app, "_xuat_cleanup_dialog", None)
            if cdlg is not None and cdlg.winfo_exists():
                cdlg._on_close()

    def test_probe_3_global_speaker_dictionary_completely_excluded_from_archiving(self) -> None:
        """[Probe 3] U-11: Global speaker dictionary entries excluded across Pass 1/2/3 & multi-file duplicates."""
        proj_dir, text_dir = self._make_xuat_tree()
        f_main = text_dir / "A_Main.txt"
        f_alt = text_dir / "B_Alt.txt"

        f_main.write_text(
            "ヒヨリ=Hiyori\n"
            "ペコリーヌ=Pecorine\n"
            "シズル=Shizuru\n"
            "あの子はペコリーヌ=Pecorine\n"
            "こんにちは、お元気ですか？=Hello, how are you doing today?\n"
            "第一章=Chapter 1: Opening\n"
            "プロローグ=Prologue Story\n",
            encoding="utf-8",
        )
        f_alt.write_text(
            "ペコリーヌ=Pecorine Alt\n"
            "シズル=Shizuru Alt\n",
            encoding="utf-8",
        )

        idx = build_xuat_index([proj_dir])
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Chapter 1: Opening"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Prologue Story"]),
            Record(cmd_id=6, cmd_name="print", args=["ヒヨリ", "Hello, how are you doing today?"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Pecorine"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["シズル", "別セリフ"]),
        ])

        # Even if a caller passes a speaker entry in applied_records (Pass 1) and renamed speaker in doc
        applied_with_speaker = [
            AppliedXuatRecord(file_path=f_main, line_number=3, raw_key="シズル", value="Shizuru", box_index=2),
            AppliedXuatRecord(file_path=f_main, line_number=5, raw_key="こんにちは、お元気ですか？", value="Hello, how are you doing today?", box_index=0),
        ]

        analysis = classify_cleanup_candidates(
            idx,
            doc,
            applied_records=applied_with_speaker,
            duplicate_scope="all_duplicates",
            protected_actors=["ペコリーヌ", "ヒヨリ", "シズル"],
        )

        cand_keys = {(c.file_path.name, c.line_number): c for c in analysis.candidates}
        # 1. Single-file actor entries excluded (0 rows)
        self.assertNotIn(("A_Main.txt", 1), cand_keys)  # ヒヨリ
        self.assertNotIn(("A_Main.txt", 2), cand_keys)  # ペコリーヌ
        # 2. Multi-file duplicate actor key excluded (0 rows)
        self.assertNotIn(("B_Alt.txt", 1), cand_keys)   # ペコリーヌ=Pecorine Alt
        # 3. Actor entry passed inside applied_records (Pass 1) excluded (0 rows)
        self.assertNotIn(("A_Main.txt", 3), cand_keys)  # シズル
        # 4. Duplicate of actor entry in Pass 2 excluded (0 rows)
        self.assertNotIn(("B_Alt.txt", 2), cand_keys)   # シズル=Shizuru Alt
        # 5. Dialogue right-side value ambiguous with actor/speaker entry excluded conservatively (0 rows)
        self.assertNotIn(("A_Main.txt", 4), cand_keys)  # あの子はペコリーヌ=Pecorine

        # 6. Normal Dialogue, Title, and Subtitle classify normally
        self.assertIn(("A_Main.txt", 5), cand_keys)
        self.assertEqual(cand_keys[("A_Main.txt", 5)].tier, "applied")
        self.assertIn(("A_Main.txt", 6), cand_keys)
        self.assertEqual(cand_keys[("A_Main.txt", 6)].tier, "already_translated_unique")
        self.assertIn(("A_Main.txt", 7), cand_keys)
        self.assertEqual(cand_keys[("A_Main.txt", 7)].tier, "already_translated_unique")

        # Speaker lookup remains intact for ImportFromXUATDialog
        self.assertIsNotNone(idx.lookup_translation("ヒヨリ"))
        self.assertIsNotNone(idx.lookup_translation("ペコリーヌ"))

    def test_probe_4_import_1line_metadata_unique_actors_no_box0_and_pixel_54d_width(self) -> None:
        """[Probe 4] U-14: 1-line 54d metadata & unique actors, no Box 0 in dialogue, no Include Actor, identity guard, multi-seg & rollback."""
        proj_dir, text_dir = self._make_xuat_tree()
        (text_dir / "A_Main.txt").write_text(
            "第一章=Chapter 1: Dawn\n"
            "プロローグ=Sub: Morning\n"
            "あらすじJP=Should NOT touch synopsis\n"
            "ペコリーヌ=Pecorine\n"
            "コッコロ=Kokkoro\n"
            "おはよう！=Good morning!\n",
            encoding="utf-8",
        )
        (text_dir / "B_Alt.txt").write_text(
            "第一章=Chapter 1: Alternate\n"
            "ペコリーヌ=Pecorine (Alt)\n",
            encoding="utf-8",
        )

        self.app._set_project_folder(proj_dir)
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=["あらすじJP"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["プロローグ"]),
            # Multi-segment box 0 (index 0) with speaker ペコリーヌ
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セグメント一"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セグメント二"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            # Locked box 1 (index 1) with speaker ペコリーヌ
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "ロック済み"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            # Dialogue box 2 (index 2) with speaker コッコロ
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "おはよう！"]),
        ])
        story_p = self._open_story(doc, "probe4.v2.txt")
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()

        # Check pixel-exact 54d under BOTH Global and Japanese font presets
        expected_safe_w = self.app._get_54d_reference_safe_w()
        dlg = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg)
        try:
            self.assertFalse(hasattr(dlg, "var_translate_speakers"), "Include Actor checkbox variable must be removed")
            all_cb_texts = [
                str(w.cget("text")) for w in _collect_descendants(dlg) if isinstance(w, (tk.Checkbutton, ttk.Checkbutton))
            ]
            self.assertFalse(any("speaker" in t.lower() or "actor" in t.lower() for t in all_cb_texts))

            # Box 0 excluded from ordinary dialogue rows
            self.assertEqual(len(dlg._rows), 3)
            self.assertTrue(all(r["box_idx"] >= 0 for r in dlg._rows))

            # Metadata rows (Title + Subtitle) + Unique Actor rows (ペコリーヌ, コッコロ) = 1 line x 54d
            self.assertEqual(len(dlg._metadata_rows), 2)
            self.assertEqual(len(dlg._actor_rows), 2)

            for mrow in dlg._metadata_rows:
                self.assertEqual(int(mrow["txt_left"].cget("height")), 1)
                self.assertEqual(int(mrow["txt_right"].cget("height")), 1)
                self.assertGreaterEqual(mrow["left_wrap"].winfo_reqwidth(), expected_safe_w)
                self.assertGreaterEqual(mrow["right_wrap"].winfo_reqwidth(), expected_safe_w)
                self.assertIn("cb_skip", mrow)

            # Title has duplicate switcher
            title_row = dlg._metadata_rows[0]
            self.assertEqual(title_row["field"], "title")
            self.assertIn("1/2", title_row["lbl_dup_counter"].cget("text"))

            for arow in dlg._actor_rows:
                self.assertEqual(int(arow["txt_left"].cget("height")), 1)
                self.assertEqual(int(arow["txt_right"].cget("height")), 1)
                self.assertGreaterEqual(arow["left_wrap"].winfo_reqwidth(), expected_safe_w)
                self.assertGreaterEqual(arow["right_wrap"].winfo_reqwidth(), expected_safe_w)
                self.assertIn("cb_skip", arow)

            # Ordinary dialogue rows remain 3 lines x 54d
            for drow in dlg._rows:
                self.assertEqual(int(drow["txt_left"].cget("height")), 3)
                self.assertEqual(int(drow["txt_right"].cget("height")), 3)
                self.assertEqual(drow["left_wrap"].winfo_reqwidth(), dlg._actor_rows[0]["left_wrap"].winfo_reqwidth())

            # Font preset consistency (Japanese preset yields identical 54d container width)
            prev_font = self.app.dialogue_font_family
            self.app.dialogue_font_family = PRESET_JP
            self.app._apply_theme_and_fonts_live(save=False)
            self.assertEqual(self.app._get_54d_reference_safe_w(), expected_safe_w)
            self.app.dialogue_font_family = prev_font
            self.app._apply_theme_and_fonts_live(save=False)

            # Document Identity Guard: mutate doc externally before Apply -> abort safely
            doc.inject_box(2, "コッコロ", "External change")
            self.app.undo_journal.record(
                MetadataDelta(str(story_p), "第一章", "第一章", "プロローグ", "プロローグ", "あらすじJP", "あらすじJP")
            )
            with patch.object(misora.messagebox, "askyesno", return_value=True):
                res_abort = dlg._on_apply_import()
            self.assertFalse(res_abort, "Document Identity Guard must abort when document changed since dialog opened")
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Re-open clean document for rollback + full apply tests
        doc_clean = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["第一章"]),
            Record(cmd_id=1, cmd_name="log", args=["あらすじJP"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["プロローグ"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セグメント一"]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セグメント二"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "ロック済み"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["コッコロ", "おはよう！"]),
        ])
        p_clean = self._open_story(doc_clean, "probe4_clean.v2.txt")
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.app.is_dirty = False
        self.app.open_documents[p_clean]["dirty"] = False

        # Mid-operation rollback test
        live_doc = self.app.current_doc
        dlg_rb = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg_rb)
        try:
            dlg_rb.var_archive_xuat.set(False)
            undo_before_rb = self.app.undo_journal.get_undo_depth(p_clean)
            with patch.object(live_doc, "inject_box", side_effect=RuntimeError("Inject boom")), \
                 patch.object(misora.messagebox, "askyesno", return_value=True):
                rb_res = dlg_rb._on_apply_import()
            self.assertFalse(rb_res)
            self.assertEqual(live_doc.get_metadata()["title"], "第一章", "Rollback must restore Box 0 title")
            self.assertEqual(self.app.undo_journal.get_undo_depth(p_clean), undo_before_rb, "Rollback must not push partial UndoOp")
            self.assertFalse(self.app.is_dirty, "Rollback must restore clean dirty state")
        finally:
            if dlg_rb.winfo_exists():
                dlg_rb._on_close()

        # Full successful apply: Metadata (preserving Synopsis), multi-seg actor rename, locked skip, Undo/Redo
        dlg_ok = self.app.on_import_from_xuat()
        self.assertIsNotNone(dlg_ok)
        try:
            dlg_ok.var_archive_xuat.set(False)
            undo_before = self.app.undo_journal.get_undo_depth(p_clean)
            with patch.object(misora.messagebox, "askyesno", return_value=True):
                self.assertTrue(dlg_ok._on_apply_import())

            self.assertEqual(self.app.undo_journal.get_undo_depth(p_clean), undo_before + 1)
            meta_after = live_doc.get_metadata()
            self.assertEqual(meta_after["title"], "Chapter 1: Dawn")
            self.assertEqual(meta_after["subtitle"], "Sub: Morning")
            self.assertEqual(meta_after["summary"], "あらすじJP", "Synopsis must stay strictly untouched")

            # Multi-seg box 0 speaker updated & segments preserved
            self.assertEqual(live_doc.boxes[0].speaker, "Pecorine")
            self.assertEqual(len(live_doc.boxes[0].segs), 2)
            self.assertEqual([s.text for s in live_doc.boxes[0].segs], ["セグメント一", "セグメント二"])

            # Locked box 1 speaker stayed JP
            self.assertEqual(live_doc.boxes[1].speaker, "ペコリーヌ")

            # Box 2 speaker & dialogue updated
            self.assertEqual(live_doc.boxes[2].speaker, "Kokkoro")
            self.assertEqual(live_doc.boxes[2].clean_text, "Good morning!")

            # Single Undo reverts everything atomically
            self.app.on_undo()
            self.assertEqual(live_doc.get_metadata()["title"], "第一章")
            self.assertEqual(live_doc.get_metadata()["subtitle"], "プロローグ")
            self.assertEqual(live_doc.boxes[0].speaker, "ペコリーヌ")
            self.assertEqual([s.text for s in live_doc.boxes[0].segs], ["セグメント一", "セグメント二"])
            self.assertEqual(live_doc.boxes[2].speaker, "コッコロ")
            self.assertEqual(live_doc.boxes[2].clean_text, "おはよう！")

            # Single Redo restores everything atomically
            self.app.on_redo()
            self.assertEqual(live_doc.get_metadata()["title"], "Chapter 1: Dawn")
            self.assertEqual(live_doc.boxes[0].speaker, "Pecorine")
            self.assertEqual(len(live_doc.boxes[0].segs), 2)
            self.assertEqual(live_doc.boxes[2].clean_text, "Good morning!")
        finally:
            if dlg_ok.winfo_exists():
                dlg_ok._on_close()

    def test_probe_5_unified_progress_controller_concurrent_isolation_and_reload_xuat_async(self) -> None:
        """[Probe 5] Unified _ProgressTaskManager concurrent isolation, O(1) progress flood + reliable terminal delivery, cancellable os.walk."""
        self.assertTrue(hasattr(self.app, "_progress_mgr"), "MisoraApp must expose _progress_mgr")
        mgr = self.app._progress_mgr
        self.assertTrue(hasattr(self.app, "status_progress_bar"))

        # Concurrent isolation: Task A + Task B
        mgr.start("search", 1, "Searching project...")
        mgr.start("reload_xuat", 1, "Reloading XUAT...")
        self.app.update()
        self.assertTrue(bool(self.app.status_progress_bar.winfo_manager()))

        # Completing Task A keeps Task B visible
        mgr.complete("search", 1, "Search complete.")
        self.app.update()
        self.assertTrue(bool(self.app.status_progress_bar.winfo_manager()))
        self.assertIn("Reloading XUAT", self.app.lbl_status.cget("text"))

        # Stale token rejected
        mgr.complete("reload_xuat", 0, "Stale complete")
        self.app.update()
        self.assertTrue(bool(self.app.status_progress_bar.winfo_manager()))

        # Queue-saturation / 5,000-message progress flood never drops terminal event and stays O(1)
        def flood_worker() -> None:
            for i in range(5000):
                mgr.post_progress("reload_xuat", 1, (i % 100) / 100.0, f"Reloading {i}/5000")
            mgr.post_complete("reload_xuat", 1, "XUAT reload complete.")

        wt = threading.Thread(target=flood_worker, daemon=True)
        wt.start()
        wt.join(timeout=3.0)
        self.assertLessEqual(len(mgr._latest_progress), 3, "Progress coalescing dict must stay O(1)")
        self._wait_until(lambda: not bool(self.app.status_progress_bar.winfo_manager()), timeout=3.0)
        self.assertFalse(bool(self.app.status_progress_bar.winfo_manager()))

        # Cancellable os.walk discovery in core/xuat_index.py::build_xuat_index()
        proj_dir, text_dir = self._make_xuat_tree()
        for sub in ("01_alpha", "02_beta", "03_gamma"):
            d = text_dir / sub
            d.mkdir(parents=True, exist_ok=True)
            for k in range(5):
                (d / f"f_{k}.txt").write_text(f"k_{sub}_{k}=v_{k}\n", encoding="utf-8")

        cancel_ev = threading.Event()
        seen_calls: list[str] = []

        def on_idx_prog(count: int, fname: str) -> None:
            seen_calls.append(fname)
            if count >= 2:
                cancel_ev.set()

        partial_idx = build_xuat_index([proj_dir], cancel_event=cancel_ev, progress_cb=on_idx_prog)
        self.assertTrue(cancel_ev.is_set())
        self.assertLess(len(partial_idx.files_indexed), 15, "build_xuat_index must stop mid-walk on cancel_event")

        # Async Reload XUAT runs off main thread via _ProgressTaskManager
        reload_threads: list[int] = []
        orig_build = misora.build_xuat_index

        def spy_build(*args, **kwargs):
            reload_threads.append(threading.get_ident())
            return orig_build(*args, **kwargs)

        self.app._set_project_folder(proj_dir)
        with patch.object(misora, "build_xuat_index", side_effect=spy_build):
            self.app._refresh_xuat_index_async()
            self._wait_until(lambda: bool(reload_threads) and not bool(self.app.status_progress_bar.winfo_manager()), timeout=5.0)
        self.assertTrue(reload_threads)
        self.assertNotEqual(reload_threads[0], threading.main_thread().ident)

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # -------------------------------------------------------------------------

    def test_guard_1_s07_sha256_stale_guard_and_mandatory_archive_first_intact(self) -> None:
        """[Guard 1] S07 SHA-256 StaleSourceError & mandatory archive-first remain intact."""
        proj_dir, text_dir = self._make_xuat_tree()
        tf = text_dir / "Guard.txt"
        tf.write_text("こんにちは=Hello!\n残す=Keep\n", encoding="utf-8")

        idx = build_xuat_index([proj_dir])
        fps = dict(idx.file_fingerprints)
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["ユイ", "こんにちは"])])
        analysis = classify_cleanup_candidates(
            idx,
            doc,
            applied_records=[AppliedXuatRecord(file_path=tf, line_number=1, raw_key="こんにちは", value="Hello!", box_index=0)],
        )

        # Mutate disk file -> StaleSourceError before writing archive
        tf.write_text("こんにちは=Hello!\n# Changed\n残す=Keep\n", encoding="utf-8")
        arch_dir = self.tmp_dir / "guard_arch"
        with self.assertRaises(StaleSourceError):
            execute_cleanup(
                candidates=analysis.candidates,
                source_fingerprints=fps,
                archive_dir=arch_dir,
            )
        self.assertFalse(arch_dir.exists() and any(arch_dir.iterdir()))

    def test_guard_2_core_xuat_modules_remain_free_of_tkinter_and_misora_imports(self) -> None:
        """[Guard 2] Pure-core boundary: core.xuat_cleanup and core.xuat_index import 0 tkinter/misora."""
        cmd = [
            sys.executable,
            "-c",
            (
                "import sys; import core.xuat_cleanup; import core.xuat_index; "
                "assert 'tkinter' not in sys.modules, 'tkinter imported'; "
                "assert 'misora' not in sys.modules, 'misora imported'"
            ),
        ]
        res = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Pure-core boundary failed: {res.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
