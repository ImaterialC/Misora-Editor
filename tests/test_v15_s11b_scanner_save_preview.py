#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S11b (v1.4.11) Verification Suite — Strict XUAT English Text Scanner & Canonical Metrics (Q-01),
Ctrl+S Save Project Remap & _current_project_path Lifecycle (Q-02), and Dialogue Preview
Red-Block Removal (Q-23).

Failing-first Defect/Behavior Probes (3):
  - Probe 1 (Q-01): Strict Translation\\en\\Text root resolver (5 categories / 6 path forms +
                    valid direct .txt, 5 forbidden rejections), 5 new endswith rule exclusions +
                    legacy exclusions, deduplication, simulated read/decode failure tracking
                    (files_scanned == len(files_indexed) + len(skipped_files)) + UI distinction,
                    canonical _norm_stripped_map metrics, and empty-normalized-key __bool__() /
                    MTLEngine.translate() exact-tier parity.
  - Probe 2 (Q-02): Ctrl+S -> on_save_project() & Ctrl+Shift+S -> on_save() with single-fire
                    "break" dispatch, accurate multi-format menu/toolbar/right-clicked-tab labels,
                    README.md alignment, and full _current_project_path lifecycle (a)-(g) +
                    data-safety safeguards (never clears dirty/mark_saved, honest toast).
  - Probe 3 (Q-23): Dialogue Preview has zero line_overflow ranges (even if
                    _apply_overflow_highlights(txt_dialogue_preview) is invoked directly),
                    preserving wrap="none", pink nameplate, gold border, pink ▼, 54d x 3,
                    while Dialogue Editor (Preview OFF) retains red overflow markers.

Regression Guards (2):
  - Guard 1: core.xuat_index remains free of tkinter & misora imports.
  - Guard 2: Dialogue Preview read-only/non-save & Box 0 exemption remain intact.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.mtl_engine import MTLConfig, MTLEngine  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402
from core.xuat_index import (  # noqa: E402
    XuatEntry,
    XuatIndex,
    build_xuat_index,
    resolve_xuat_text_roots,
)


class S11bTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s11b_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patches = [
            patch.object(misora, "CONFIG_PATH", self.config_path),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askyesno", return_value=True),
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

    def _open_story(self, doc: StoryDocument, name: str = "s11b_story.v2.txt") -> Path:
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p, reload_from_disk=True)
        self.app.update_idletasks()
        return p


class TestV15S11bScannerSavePreview(S11bTestBase):
    """Failing-first probes (3) and regression guards (2) for S11b (v1.4.11)."""

    # -------------------------------------------------------------------------
    # Probe 1 (Q-01): Strict XUAT English Text Scanner & Canonical Metrics
    # -------------------------------------------------------------------------
    def test_probe_1_xuat_strict_en_text_roots_exclusions_and_canonical_metrics(self) -> None:
        """[Probe 1 — Q-01] Strict Translation\\en\\Text resolver, 5 endswith rule exclusions,
        files_scanned failure accounting + UI distinction, canonical _norm_stripped_map metrics,
        and empty-normalized-key __bool__() / MTLEngine exact-tier lookup parity.
        """
        # 1. All 5 user entry-point categories (6 concrete path forms) + direct .txt inside canonical tree
        src_game_root = self.tmp_dir / "PriconneRe-TL"
        src_text = src_game_root / "src" / "BepInEx" / "Translation" / "en" / "Text"
        src_text.mkdir(parents=True, exist_ok=True)
        direct_src_txt = src_text / "DirectValid.txt"
        direct_src_txt.write_text("おはよう=Good morning\n", encoding="utf-8")

        std_game_root = self.tmp_dir / "StandardGame"
        std_bep = std_game_root / "BepInEx"
        std_trans = std_bep / "Translation"
        std_en = std_trans / "en"
        std_text = std_en / "Text"
        std_text.mkdir(parents=True, exist_ok=True)

        self.assertEqual(resolve_xuat_text_roots([src_game_root]), [src_text])
        self.assertEqual(resolve_xuat_text_roots([std_game_root]), [std_text])
        self.assertEqual(resolve_xuat_text_roots([std_bep]), [std_text])
        self.assertEqual(resolve_xuat_text_roots([std_trans]), [std_text])
        self.assertEqual(resolve_xuat_text_roots([std_en]), [std_text])
        self.assertEqual(resolve_xuat_text_roots([std_text]), [std_text])
        self.assertEqual(resolve_xuat_text_roots([direct_src_txt]), [direct_src_txt])

        # 2. All 5 forbidden locations MUST be rejected
        ja_text = std_trans / "ja" / "Text"
        ja_text.mkdir(parents=True, exist_ok=True)
        (ja_text / "JaOnly.txt").write_text("JA_KEY=JA_VAL\n", encoding="utf-8")

        arbitrary_text = self.tmp_dir / "Random" / "Text"
        arbitrary_text.mkdir(parents=True, exist_ok=True)
        (arbitrary_text / "Arb.txt").write_text("ARB_KEY=ARB_VAL\n", encoding="utf-8")

        standalone_txt = self.tmp_dir / "StandaloneOutside.txt"
        standalone_txt.write_text("OUT_KEY=OUT_VAL\n", encoding="utf-8")

        other_dir = std_en / "Other"
        other_dir.mkdir(parents=True, exist_ok=True)
        (other_dir / "Other.txt").write_text("OTHER_KEY=OTHER_VAL\n", encoding="utf-8")

        redir_dir = std_en / "RedirectedResources"
        redir_dir.mkdir(parents=True, exist_ok=True)
        (redir_dir / "Redir.txt").write_text("REDIR_KEY=REDIR_VAL\n", encoding="utf-8")

        for bad in (ja_text, std_trans / "ja", arbitrary_text, standalone_txt, other_dir, redir_dir):
            self.assertEqual(
                resolve_xuat_text_roots([bad]),
                [],
                f"Forbidden path must be rejected by resolve_xuat_text_roots(): {bad}",
            )

        # 3. 5 new official XUAT rule exclusions (case-insensitive endswith) + legacy exclusions
        excluded_files = {
            "custom.font.txt": "EX_FONT=ShouldNotIndex\n",
            "ui.RESIZER.TXT": "EX_RESIZER=ShouldNotIndex\n",
            "StoryPostprocessors.txt": "EX_POST=ShouldNotIndex\n",
            "GlobalPreprocessors.TXT": "EX_PRE=ShouldNotIndex\n",
            "TextSubstitutions.txt": "EX_SUB=ShouldNotIndex\n",
            "Story.missing.txt": "EX_MISS=ShouldNotIndex\n",
            "Story.report.txt": "EX_REP=ShouldNotIndex\n",
            "_SUMMARY.txt": "EX_SUM=ShouldNotIndex\n",
            "_warnings.txt": "EX_WARN=ShouldNotIndex\n",
            "Main.bak_20261126.txt": "EX_BAK=ShouldNotIndex\n",
        }
        for fname, content in excluded_files.items():
            (std_text / fname).write_text(content, encoding="utf-8")

        # Valid file whose stem contains "substitutions" mid-name (NOT ending in substitutions.txt -> m-1 endswith)
        valid_mid = std_text / "my_substitutions_notes.txt"
        valid_mid.write_text(
            "こんにちは=Hello\n"
            "またね=See you\n"
            "[FF0000][-]=TagOnlyVal\n",
            encoding="utf-8",
        )
        valid_a = std_text / "A_Main.txt"
        valid_a.write_text(
            "こんにちは=Hello Main\n"
            "ありがとう=Thank you\n",
            encoding="utf-8",
        )
        valid_b = std_text / "B_Dup.txt"
        valid_b.write_text(
            "こんにちは=Hello Third\n"
            "ありがとう=Thanks Dup\n",
            encoding="utf-8",
        )
        # Simulated decode failure file (invalid UTF-8/CP932 bytes -> m-2 skipped_files + files_scanned)
        corrupt_file = std_text / "Z_Corrupt.txt"
        corrupt_file.write_bytes(b"\x81\x00\xff\xfe\x80\x81")

        # Pass overlapping roots to verify deduplication too
        idx = build_xuat_index([std_game_root, std_text, valid_a])

        for ex_k in (
            "EX_FONT", "EX_RESIZER", "EX_POST", "EX_PRE", "EX_SUB",
            "EX_MISS", "EX_REP", "EX_SUM", "EX_WARN", "EX_BAK",
        ):
            self.assertIsNone(idx.lookup_translation(ex_k), f"Excluded key leaked: {ex_k}")

        # m-1: mid-stem file WAS indexed
        self.assertIsNotNone(idx.lookup_translation("またね"))

        # m-2: files_scanned == len(files_indexed) + len(skipped_files) across successes, dups, exclusions, failures
        self.assertEqual(len(idx.files_indexed), 3)  # my_substitutions_notes, A_Main, B_Dup
        self.assertEqual(len(idx.skipped_files), 1)
        self.assertEqual(idx.skipped_files[0][0], corrupt_file)
        self.assertEqual(idx.files_scanned, 4)
        self.assertEqual(idx.files_scanned, len(idx.files_indexed) + len(idx.skipped_files))

        # Canonical metric math backed by _norm_stripped_map:
        # Valid non-empty normalized entries:
        #   my_substitutions_notes: こんにちは, またね (2; [FF0000][-] has empty norm key -> NOT counted)
        #   A_Main: こんにちは, ありがとう (2)
        #   B_Dup: こんにちは, ありがとう (2)
        # Total entries_read == entry_count == 6; unique_keys == 3 (こんにちは, またね, ありがとう);
        # duplicate_keys == 2 (こんにちは [3x], ありがとう [2x]); duplicate_entries == 6 - 3 == 3.
        self.assertEqual(idx.entry_count, 6)
        self.assertEqual(idx.entries_read, 6)
        self.assertEqual(len(idx), 6)
        self.assertEqual(idx.unique_keys, len(idx._norm_stripped_map))
        self.assertEqual(idx.unique_keys, 3)
        self.assertEqual(idx.duplicate_keys, 2)
        self.assertEqual(idx.duplicate_entries, 3)
        self.assertEqual(idx.entries_read, idx.unique_keys + idx.duplicate_entries)

        # Empty normalized key did NOT enter _norm_stripped_map, yet DID enter entries/_exact_map/_value_map
        self.assertNotIn("", idx._norm_stripped_map)
        self.assertEqual(idx.lookup_translation("[FF0000][-]"), "TagOnlyVal")
        self.assertEqual(len(idx.lookup_by_value("TagOnlyVal")), 1)

        # BLOCKER FIX regression test: XuatIndex with ONLY an empty-normalized-key entry
        idx_empty_only = XuatIndex()
        idx_empty_only.add_entry(
            XuatEntry(
                file_path=valid_mid,
                rel_path="my_substitutions_notes.txt",
                line_number=3,
                raw_key="[FF0000][-]",
                raw_value="TagOnlyVal",
                value="TagOnlyVal",
            )
        )
        self.assertTrue(bool(idx_empty_only), "XuatIndex with stored exact entry must be truthy for MTLEngine")
        self.assertEqual(len(idx_empty_only), 0)
        self.assertEqual(idx_empty_only.entry_count, 0)
        self.assertEqual(idx_empty_only.entries_read, 0)
        self.assertEqual(len(idx_empty_only._norm_stripped_map), 0)
        mtl_engine = MTLEngine(MTLConfig(active_engine="XUAT Cache", use_xuat_cache=True))
        self.assertEqual(
            mtl_engine.translate("[FF0000][-]", xuat_cache=idx_empty_only),
            "TagOnlyVal",
        )

        # m-2: UI / status distinction between Scanned vs Indexed (and Skipped)
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "こんにちは"])])
        self._open_story(doc, "probe1_ui.v2.txt")
        self.app._set_project_folder(src_game_root)
        self.assertEqual(self.app.xuat_search_roots, [src_text])

        dlg = self.app.on_import_from_xuat(xuat_index=idx)
        self.assertIsNotNone(dlg)
        try:
            summary_txt = dlg.lbl_summary.cget("text")
            self.assertIn("Scanned: 4", summary_txt)
            self.assertIn("Indexed: 3", summary_txt)
            self.assertIn("Skipped: 1", summary_txt)
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Async reload queue status string distinguishes Scanned vs Indexed
        self.app._xuat_index_seq = 99
        self.app._xuat_index_queue.put(("xuat_index_ready", 99, idx))
        self.app._progress_mgr.start("reload_xuat", 99, "Reloading...")
        self.app._poll_xuat_index_queue()
        self.app.update_idletasks()
        status_txt = self.app.lbl_status.cget("text")
        self.assertIn("Scanned: 4", status_txt)
        self.assertIn("Indexed: 3", status_txt)
        self.assertIn("Skipped: 1", status_txt)

    # -------------------------------------------------------------------------
    # Probe 2 (Q-02): Ctrl+S -> Save Project (.misora), Ctrl+Shift+S -> Save File
    # -------------------------------------------------------------------------
    def test_probe_2_ctrl_s_saves_project_and_bundle_patch_has_dedicated_shortcut(self) -> None:
        """[Probe 2 — Q-02] Ctrl+S saves .misora project (single-fire 'break', preserves dirty),
        Ctrl+Shift+S saves active file, labels/README/tab context menu match, and full
        _current_project_path lifecycle (a)-(g) passes.
        """
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Original line"])])
        story_v2 = self._open_story(doc, "probe2.v2.txt")

        # 1. Shortcut router single-fire & "break" for Ctrl+S and Ctrl+Shift+S
        ev_s = tk.Event()
        ev_s.keysym = "s"
        ev_s.state = 0x0004  # Control
        ev_s.widget = self.app.txt_dialogue

        ev_ss = tk.Event()
        ev_ss.keysym = "S"
        ev_ss.state = 0x0004 | 0x0001  # Control | Shift
        ev_ss.widget = self.app.txt_dialogue

        with patch.object(self.app, "on_save_project", return_value=True) as spy_proj, \
             patch.object(self.app, "on_save", return_value=True) as spy_save:
            res_s = self.app._on_misora_shortcut(ev_s)
            self.assertEqual(res_s, "break")
            spy_proj.assert_called_once()
            spy_save.assert_not_called()

            spy_proj.reset_mock()
            spy_save.reset_mock()

            res_ss = self.app._on_misora_shortcut(ev_ss)
            self.assertEqual(res_ss, "break")
            spy_save.assert_called_once()
            spy_proj.assert_not_called()

        # Verify real Tk keypress dispatch on MisoraShortcuts-bound widget fires EXACTLY once (no double-fire)
        self.app.deiconify()
        self.app.update_idletasks()
        self.app.txt_dialogue.focus_set()
        self.app.update()
        with patch.object(self.app, "on_save_project", return_value=True) as spy_proj_ev, \
             patch.object(self.app, "on_save", return_value=True) as spy_save_ev:
            self.app.txt_dialogue.event_generate("<Control-s>")
            self.app.update_idletasks()
            self.assertEqual(spy_proj_ev.call_count, 1, "Ctrl+S must single-fire on_save_project")
            self.assertEqual(spy_save_ev.call_count, 0)

            self.app.txt_dialogue.event_generate("<Control-Shift-S>")
            self.app.update_idletasks()
            self.assertEqual(spy_save_ev.call_count, 1, "Ctrl+Shift+S must single-fire on_save")
            self.assertEqual(spy_proj_ev.call_count, 1)
        self.app.withdraw()

        # 2. Menu labels, accelerators, toolbar button, README.md, and right-clicked tab context menus
        file_items = {}
        end_idx = self.app.file_menu.index("end")
        for i in range(end_idx + 1):
            if self.app.file_menu.type(i) == "command":
                lbl = self.app.file_menu.entrycget(i, "label")
                acc = self.app.file_menu.entrycget(i, "accelerator")
                file_items[lbl] = acc

        self.assertEqual(file_items.get("Save Project (.misora)"), "Ctrl+S")
        self.assertIn("Save Project As (.misora)...", file_items)
        self.assertEqual(file_items.get("Save File / Patch Bundle"), "Ctrl+Shift+S")
        self.assertIn("Ctrl+Shift+S", str(self.app.btn_save.cget("text")))
        self.assertIn("Save File / Patch Bundle", str(self.app.btn_save.cget("text")))
        btn_tip = getattr(self.app.btn_save, "_tooltip", None)
        self.assertIsNotNone(btn_tip)
        self.assertIn("Ctrl+Shift+S", btn_tip.text)
        self.assertIn("Ctrl+S", btn_tip.text)

        readme_text = (_REPO / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Save As | Save active story under a new filename", readme_text)
        self.assertIn("Ctrl + S", readme_text)
        self.assertIn("Save Project", readme_text)
        self.assertIn("Ctrl + Shift + S", readme_text)

        # Tab context menu checks right-clicked tab's file type across bundle, v2, and plain-text
        def _capture_ctx_labels(target_p: Path) -> list[str]:
            captured: list[str] = []
            orig_menu_cls = misora.tk.Menu

            class SpyMenu(orig_menu_cls):
                def add_command(self_m, **kwargs):
                    if "label" in kwargs:
                        captured.append(str(kwargs["label"]))
                    return super().add_command(**kwargs)

                def tk_popup(self_m, x, y, entry=""):
                    return None

            ev_ctx = tk.Event()
            ev_ctx.x_root = 10
            ev_ctx.y_root = 10
            with patch.object(misora.tk, "Menu", SpyMenu):
                self.app._show_file_context_menu(ev_ctx, target_p)
            return captured

        # Active is v2, add synthetic bundle & plain entries in open_documents
        bundle_p = self.tmp_dir / "storydata_fake.unity3d"
        bundle_p.write_bytes(b"fake")
        plain_p = self.tmp_dir / "plain_ctx.txt"
        plain_p.write_text("hello", encoding="utf-8")

        self.app.open_documents[bundle_p.resolve()] = {"doc": doc, "is_bundle": True}
        self.app.open_documents[plain_p.resolve()] = {"doc": None, "is_bundle": False}

        # Right-clicking bundle while active tab is v2 MUST still say Save & Patch Bundle
        self.assertFalse(self.app.is_bundle_file)
        bundle_labels = _capture_ctx_labels(bundle_p.resolve())
        self.assertIn("Save & Patch Bundle (Ctrl+Shift+S)", bundle_labels)

        # Right-clicking v2 while active tab is bundle MUST still say Save File
        self.app.is_bundle_file = True
        v2_labels = _capture_ctx_labels(story_v2.resolve())
        self.assertIn("Save File (Ctrl+Shift+S)", v2_labels)
        plain_labels = _capture_ctx_labels(plain_p.resolve())
        self.assertIn("Save File (Ctrl+Shift+S)", plain_labels)
        self.app.is_bundle_file = False
        self.app.open_documents.pop(bundle_p.resolve(), None)
        self.app.open_documents.pop(plain_p.resolve(), None)

        # 3. Full _current_project_path lifecycle (a)-(g) + Data Safety
        ws_a = self.tmp_dir / "proj_a.misora"
        ws_b = self.tmp_dir / "proj_b.misora"

        # (d) Cancelled save never sets _current_project_path
        self.assertIsNone(self.app._current_project_path)
        with patch.object(misora.filedialog, "asksaveasfilename", return_value="") as mock_ask:
            self.assertFalse(self.app.on_save_project())
            self.assertEqual(mock_ask.call_count, 1)
        self.assertIsNone(self.app._current_project_path)

        # (d) Failed save_workspace never sets _current_project_path
        with patch.object(misora.filedialog, "asksaveasfilename", return_value=str(ws_a)), \
             patch.object(misora, "save_workspace", side_effect=OSError("Disk full")):
            self.assertFalse(self.app.on_save_project())
        self.assertIsNone(self.app._current_project_path)

        # (a) First Ctrl+S with no loaded/saved path prompts asksaveasfilename()
        # (g) Preserves flush + dirty state + honest toast + dirty-close prompt
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Dirty unsaved edit before Ctrl+S")
        self.app._on_dialogue_edited()
        self.assertTrue(self.app.is_dirty)

        with patch.object(misora.filedialog, "asksaveasfilename", return_value=str(ws_a)) as mock_ask, \
             patch.object(self.app, "show_toast") as mock_toast, \
             patch.object(self.app, "_flush_active_widget", wraps=self.app._flush_active_widget) as spy_flush:
            self.assertTrue(self.app.on_save_project())
            self.assertEqual(mock_ask.call_count, 1)
            self.assertGreaterEqual(spy_flush.call_count, 1)
            toast_msg = " ".join(str(c.args[0]) for c in mock_toast.call_args_list)
            self.assertIn("not yet written to bundle/XUAT", toast_msg)
            self.assertIn("Ctrl+Shift+S", toast_msg)

        self.assertEqual(self.app._current_project_path, ws_a.resolve())
        self.assertTrue(ws_a.is_file())
        self.assertTrue(self.app.is_dirty, "Ctrl+S must NEVER clear dirty flag on story document")
        self.assertTrue(self.app.open_documents[story_v2.resolve()]["dirty"])
        self.assertFalse(self.app.undo_journal.is_clean(str(story_v2)))
        self.assertTrue(self.app.undo_journal.can_undo(str(story_v2)))

        # (b) Subsequent Ctrl+S saves directly without reopening dialog
        with patch.object(misora.filedialog, "asksaveasfilename") as mock_ask2:
            self.assertTrue(self.app.on_save_project())
            mock_ask2.assert_not_called()

        # (f) Separate "Save Project As (.misora)..." always prompts
        with patch.object(misora.filedialog, "asksaveasfilename", return_value=str(ws_b)) as mock_ask_as:
            self.assertTrue(self.app.on_save_project(save_as=True))
            self.assertEqual(mock_ask_as.call_count, 1)
        self.assertEqual(self.app._current_project_path, ws_b.resolve())
        self.assertTrue(ws_b.is_file())

        # (g) Dirty-close Save/Discard/Cancel still triggers after Ctrl+S (Cancel keeps doc open)
        with patch.object(misora.messagebox, "askyesnocancel", return_value=None) as mock_close_prompt:
            self.assertFalse(self.app.close_file(story_v2))
            self.assertEqual(mock_close_prompt.call_count, 1)

        # (e) Closing last document resets _current_project_path to None
        with patch.object(misora.messagebox, "askyesnocancel", return_value=False):
            self.assertTrue(self.app.close_file(story_v2))
        self.assertIsNone(self.app._current_project_path)

        # (c) open_project() sets _current_project_path -> Ctrl+S updates that loaded .misora path
        self.assertTrue(self.app.open_project(ws_a))
        self.assertEqual(self.app._current_project_path, ws_a.resolve())
        with patch.object(misora.filedialog, "asksaveasfilename") as mock_ask3:
            self.assertTrue(self.app.on_save_project())
            mock_ask3.assert_not_called()

        # (e) open_project() where all referenced files are missing keeps _current_project_path = None
        ws_missing = self.tmp_dir / "missing_all.misora"
        ws_missing.write_text(ws_a.read_text(encoding="utf-8"), encoding="utf-8")
        with patch.object(misora.messagebox, "askyesnocancel", return_value=False):
            self.assertTrue(self.app.close_file(story_v2))
        story_v2.unlink()
        self.assertTrue(self.app.open_project(ws_missing))
        self.assertEqual(len(self.app.open_documents), 0)
        self.assertIsNone(self.app._current_project_path)

    # -------------------------------------------------------------------------
    # Probe 3 (Q-23): Dialogue Preview Zero Red Overflow Blocks
    # -------------------------------------------------------------------------
    def test_probe_3_dialogue_preview_has_zero_red_blocks_while_editor_keeps_markers(self) -> None:
        """[Probe 3 — Q-23] Dialogue Preview has 0 line_overflow ranges (including defensive guard),
        retains wrap='none', pink nameplate, gold border, pink ▼, and 54d x 3, while Dialogue
        Editor (Preview OFF) keeps red overflow highlights.
        """
        overwide = "1234567890" * 6
        four_lines = f"Line 1\nLine 2\nLine 3\n{overwide}"
        self._open_story(
            StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", four_lines])]),
            "probe3.v2.txt",
        )

        # Preview ON -> ZERO red overflow highlight blocks
        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        self.assertEqual(self.app.txt_dialogue_preview.tag_ranges("line_overflow"), ())
        # Defensive guard: direct _apply_overflow_highlights(txt_dialogue_preview) still leaves 0 ranges
        self.app._apply_overflow_highlights(self.app.txt_dialogue_preview)
        self.assertEqual(self.app.txt_dialogue_preview.tag_ranges("line_overflow"), ())

        # Preserved Dialogue Preview invariants
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("wrap")), "none")
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_nameplate")), 1)
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_capsule")), 1)
        self.assertGreaterEqual(len(self.app.dialogue_preview_canvas.find_withtag("preview_arrow")), 1)
        self.assertGreaterEqual(int(self.app.txt_dialogue_preview.cget("height")), 3)

        # Switch to Dialogue Editor (Preview OFF) -> red overflow highlights MUST remain active
        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertTrue(len(self.app.txt_dialogue.tag_ranges("line_overflow")) >= 2)

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # -------------------------------------------------------------------------
    def test_guard_1_core_xuat_index_free_of_tkinter_and_misora_imports(self) -> None:
        """[Guard 1] core.xuat_index remains 100% free of tkinter and misora imports."""
        cmd = [
            sys.executable,
            "-c",
            (
                "import sys; import core.xuat_index; "
                "assert 'tkinter' not in sys.modules, 'tkinter imported'; "
                "assert 'misora' not in sys.modules, 'misora imported'"
            ),
        ]
        res = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Pure-core boundary failed: {res.stderr}")

    def test_guard_2_dialogue_preview_readonly_non_save_and_box0_exemption_intact(self) -> None:
        """[Guard 2] Dialogue Preview stays disabled/non-save and Box 0 stays exempt from overflow markers."""
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["1234567890" * 7]),
            Record(cmd_id=1, cmd_name="log", args=["L1\nL2\nL3\n" + ("1234567890" * 7)]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "[FF0000]Hello[-]"]),
        ])
        p = self._open_story(doc, "guard2.v2.txt")

        # Box 0 exempt from overflow markers
        self.app.is_box0_active = True
        self.app._update_views()
        self.app.update_idletasks()
        self.assertEqual(self.app.txt_dialogue.tag_ranges("line_overflow"), ())

        # Dialogue Preview is read-only & excluded from save path
        self.app.is_box0_active = False
        self.app.current_box_idx = 0
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("state")), "disabled")
        self.assertTrue(self.app.on_save())
        self.assertIn("[FF0000]Hello[-]", p.read_text(encoding="utf-8"))

    def test_guard_3_project_diff_dialog_theme_fallback_no_keyerror(self) -> None:
        """[Guard 3] ProjectDiffDialog resolves flat assets.icon.THEME when parent lacks .theme and uses parent.theme when provided."""
        # (a) Parent lacking .theme -> falls back to flat assets.icon.THEME without KeyError: 'dark'
        bare_parent = tk.Toplevel(self.app)
        bare_parent.withdraw()
        dlg_a = None
        try:
            with patch.object(bare_parent, "wait_window", return_value=None):
                dlg_a = misora.ProjectDiffDialog(bare_parent, [], "fallback.misora")
            self.assertEqual(str(dlg_a.cget("bg")), misora.THEME["bg_dark"])
        finally:
            if dlg_a is not None:
                try:
                    if dlg_a.winfo_exists():
                        dlg_a.destroy()
                except Exception:
                    pass
            if bare_parent.winfo_exists():
                bare_parent.destroy()

        # (b) Parent providing .theme -> uses parent.theme
        custom_theme = dict(misora.THEME)
        custom_theme["bg_main"] = "#123456"
        themed_parent = tk.Toplevel(self.app)
        themed_parent.withdraw()
        themed_parent.theme = custom_theme  # type: ignore[attr-defined]
        dlg_b = None
        try:
            with patch.object(themed_parent, "wait_window", return_value=None):
                dlg_b = misora.ProjectDiffDialog(themed_parent, [], "custom.misora")
            self.assertEqual(str(dlg_b.cget("bg")), "#123456")
        finally:
            if dlg_b is not None:
                try:
                    if dlg_b.winfo_exists():
                        dlg_b.destroy()
                except Exception:
                    pass
            if themed_parent.winfo_exists():
                themed_parent.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
