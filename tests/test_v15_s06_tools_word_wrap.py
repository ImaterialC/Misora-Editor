#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S06 (v1.4.6) Verification Suite — Top-Level Tools Menu & Lossless Auto Word Wrap:
- Probe 1 (U07): Wrap English with NGUI tags, ruby, {playername}, malformed tags, and intentional whitespace.
- Probe 2 (U07): Wrap Japanese with combining dakuten, kinsoku, NGUI tag orphan guards, existing breaks, and >3-line overflow reporting.
- Probe 3 (U07): Tools menu immediately after View, locked box skip, immutable JP keys, and single Undo/Redo batch.
- Probe 4 (U07): Multi-segment box wrapping preserves segment count and old_seg_texts/new_seg_texts across Undo/Redo.
- Probe 5 (4.5): ImportFromXUATDialog & ScriptPastePreviewDialog opt-in wrap defaults OFF; wraps inside single Undo batch when ON.
- Probe 6 (U07): 200-box document wrapping lossless character parity and < 2.0s runtime.
- Guard 1: Short lines within 50d x 3 and speaker fields remain untouched.
- Guard 2: Wrapped documents emit no CSIF headers or empty binary args and round-trip cleanly via to_binary()/from_binary().
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.script_codec import parse  # noqa: E402
from core.story_ast import Record, StoryDocument, game_to_xuat  # noqa: E402
from core.xuat_index import build_xuat_index  # noqa: E402


class TestV15S06ToolsWordWrap(unittest.TestCase):
    """Failing-first probes and regression guards for v1.5 S06 (v1.4.6)."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s06_"))
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
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.geometry("1280x720")
        self.app.update_idletasks()

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

    def _attach_doc(self, doc: StoryDocument, name: str = "s06_test.unity3d") -> Path:
        p = self.tmp_dir / name
        self.app.open_documents[p] = {"doc": doc, "plain_text": "", "dirty": False}
        self.app.current_file_path = p
        self.app.current_doc = doc
        self.app.is_box0_active = False
        self.app.current_box_idx = 0
        self.app.is_dirty = False
        self.app._original_jp_by_uid = {}
        for b in doc.boxes:
            if b.uid:
                self.app._original_jp_by_uid[b.uid] = b.clean_text
                self.app.sync_manager.register_jp_key(b.uid, b.clean_text)
        self.app._locked_box_uids = set()
        self.app._locked_boxes = set()
        self.app._modified_box_uids = set()
        self.app._modified_boxes = set()
        self.app.undo_journal.set_active_file(p)
        self.app._update_views()
        self.app.update_idletasks()
        return p

    @staticmethod
    def _mono_measure(text: str) -> int:
        # 10 px per character, matching safe_width=500 for 50 chars.
        return len(text) * 10

    @staticmethod
    def _strip_wrap_newlines_compare(orig: str, wrapped: str) -> tuple[str, str]:
        # Compare lossless character parity ignoring single spaces replaced by '\n'.
        return " ".join(orig.split()), " ".join(wrapped.split())

    # -------------------------------------------------------------------------
    # Defect / Behavior Probes (MUST FAIL pre-patch, PASS post-patch)
    # -------------------------------------------------------------------------

    def test_probe_1_wrap_ngui_tags_placeholders_malformed_and_whitespace(self) -> None:
        """Probe 1: Atomic NGUI tags, ruby, {playername}, malformed tags, and intentional whitespace."""
        from core.word_wrap import wrap_text

        sample = (
            "  [FF0000]important[-]  [rub:Command]Wish[/rub] for {playername} "
            "with an [broken unclosed tag and plenty of additional words to wrap cleanly."
        )
        res = wrap_text(sample, self._mono_measure, safe_width=300)

        self.assertTrue(res.changed)
        self.assertIn("[FF0000]important[-]", res.wrapped_text)
        self.assertIn("[rub:Command]Wish[/rub]", res.wrapped_text)
        self.assertIn("{playername}", res.wrapped_text)
        self.assertIn("[broken", res.wrapped_text)
        # Intentional leading double-space and double-space before [rub:...] preserved when not broken there
        self.assertTrue(res.wrapped_text.startswith("  [FF0000]important[-]"))
        # Zero characters dropped
        o_norm, w_norm = self._strip_wrap_newlines_compare(sample, res.wrapped_text)
        self.assertEqual(w_norm, o_norm)
        # Wrapped lines (except an unbreakable token) fit safe_width=300 (<= 30 rendered chars)
        for ln in res.wrapped_text.split("\n"):
            # Measure with same rules via wrap_text on single line
            check = wrap_text(ln, self._mono_measure, safe_width=300)
            self.assertFalse(check.still_overflows_width, f"Line exceeded width: {ln!r}")

    def test_probe_2_wrap_japanese_kinsoku_grapheme_clusters_and_existing_breaks(self) -> None:
        """Probe 2: Combining dakuten, kinsoku, NGUI tag orphan prevention, existing breaks, and >3-line reporting."""
        from core.word_wrap import wrap_text

        # Contains NFD combining dakuten (か\u3099), opening/closing NGUI tags, kinsoku punctuation, and existing \n
        line1 = "あいう[FF0000]か\u3099きく[-]。これはとても長い日本語のセリフ「テスト」です！"
        line2 = "二行目の既存改行は保持されます。"
        sample = f"{line1}\n{line2}"

        res = wrap_text(sample, self._mono_measure, safe_width=100, reflow_existing_breaks=False)
        self.assertTrue(res.changed)
        # Combining dakuten must never detach from か
        self.assertIn("か\u3099", res.wrapped_text)
        self.assertNotIn("\n\u3099", res.wrapped_text)
        # Zero-width opening/closing NGUI tags must never be orphaned
        for out_ln in res.wrapped_text.split("\n"):
            self.assertFalse(out_ln.endswith("[FF0000]"), f"Opening tag orphaned at line end: {out_ln!r}")
            self.assertFalse(out_ln.startswith("[-]"), f"Closing tag orphaned at line start: {out_ln!r}")
            # Gyoto kinsoku: closing punctuation must not start a wrapped line
            for ch in ("。", "！", "」", "、"):
                self.assertFalse(out_ln.startswith(ch), f"Kinsoku violated at start of {out_ln!r}")
            # Gyomatsu kinsoku: opening bracket must not end a wrapped line
            for ch in ("「", "（", "『"):
                self.assertFalse(out_ln.endswith(ch), f"Opening bracket orphaned at end of {out_ln!r}")

        # Existing break before line2 preserved; line2 ends cleanly
        self.assertIn("\n二行目の既存改行", res.wrapped_text)
        # Character parity (no spaces inside JP; stripping \n matches original without \n)
        self.assertEqual(res.wrapped_text.replace("\n", ""), sample.replace("\n", ""))
        self.assertTrue(res.still_overflows_lines)
        self.assertGreaterEqual(res.new_lines, 4)

    def test_probe_3_tools_menu_locks_single_undo_and_immutable_jp_keys(self) -> None:
        """Probe 3: Tools menu right of View, locked box skipped, JP keys immutable, single Undo/Redo."""
        menubar_name = self.app.cget("menu")
        menubar = self.app.nametowidget(menubar_name)
        end_idx = menubar.index("end")
        labels = [menubar.entrycget(i, "label") for i in range(end_idx + 1) if menubar.type(i) == "cascade"]
        self.assertIn("View", labels)
        self.assertIn("Tools", labels)
        self.assertEqual(labels.index("Tools"), labels.index("View") + 1)

        long_en_1 = "This is a very long translated English dialogue line number one that definitely exceeds fifty digit widths."
        long_en_2 = "This second box is locked and must remain completely unwrapped even when Auto Word Wrap runs across all boxes."
        long_en_3 = "This third dialogue box is unlocked and should be cleanly wrapped into multiple lines fitting within the limit."

        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", long_en_1]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", long_en_2]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", long_en_3]),
        ])
        self._attach_doc(doc, "s06_tools_undo.unity3d")

        # Seed immutable JP keys distinct from current EN text
        jp_keys = {
            doc.boxes[0].uid: "JP_ORIG_1",
            doc.boxes[1].uid: "JP_ORIG_2",
            doc.boxes[2].uid: "JP_ORIG_3",
        }
        self.app.sync_manager.unregister_jp_keys(jp_keys.keys())
        self.app._original_jp_by_uid = dict(jp_keys)
        for uid, jp in jp_keys.items():
            self.app.sync_manager.register_jp_key(uid, jp)

        # Lock Box #2 (index 1)
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        # Verify AutoWordWrapDialog opens, defaults to preserve breaks, and applies All Boxes cleanly
        dlg = self.app.on_open_auto_word_wrap()
        self.assertIsNotNone(dlg)
        self.assertTrue(dlg.var_preserve_breaks.get())
        dlg.var_scope.set("all")

        undo_before = self.app.undo_journal.get_undo_depth(self.app.current_file_path)
        dlg._on_apply()
        stats = dlg.applied_stats
        undo_after = self.app.undo_journal.get_undo_depth(self.app.current_file_path)

        self.assertEqual(undo_after, undo_before + 1, "All wrapped boxes must commit in ONE Undo batch")
        self.assertEqual(stats["wrapped"], 2)
        self.assertEqual(stats["skipped_locked"], 1)

        # Box #1 and Box #3 wrapped; Box #2 untouched
        self.assertIn("\n", doc.boxes[0].clean_text)
        self.assertEqual(doc.boxes[1].clean_text, long_en_2)
        self.assertIn("\n", doc.boxes[2].clean_text)

        # Immutable JP keys untouched
        self.assertEqual(self.app._original_jp_by_uid, jp_keys)
        for uid, jp in jp_keys.items():
            self.assertEqual(self.app.sync_manager.get_jp_key(uid), jp)

        # ONE Ctrl+Z undoes both boxes; ONE Ctrl+Y redoes both boxes
        self.app.on_undo()
        self.assertEqual(doc.boxes[0].clean_text, long_en_1)
        self.assertEqual(doc.boxes[1].clean_text, long_en_2)
        self.assertEqual(doc.boxes[2].clean_text, long_en_3)

        self.app.on_redo()
        self.assertIn("\n", doc.boxes[0].clean_text)
        self.assertEqual(doc.boxes[1].clean_text, long_en_2)
        self.assertIn("\n", doc.boxes[2].clean_text)

    def test_probe_4_multisegment_box_wrap_preserves_segments(self) -> None:
        """Probe 4: Multi-segment boxes preserve segment count and old_seg_texts/new_seg_texts across Undo/Redo."""
        seg0 = "First segment is a long English sentence that exceeds the fifty digit width limit cleanly."
        seg1 = "Second segment is also a very long English sentence that must wrap inside its own segment."
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", seg0]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", seg1]),
        ])
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(len(doc.boxes[0].segs), 2)
        p = self._attach_doc(doc, "s06_multiseg.unity3d")

        stats = self.app.apply_auto_word_wrap(scope="current", reflow_existing_breaks=False)
        self.assertEqual(stats["wrapped"], 1)
        self.assertEqual(len(doc.boxes[0].segs), 2)
        self.assertIn("\n", doc.boxes[0].segs[0].text)
        self.assertIn("\n", doc.boxes[0].segs[1].text)

        # Inspect recorded BoxEditDelta
        op = self.app.undo_journal._get_state(p).undo_stack[-1]
        delta = op.deltas[0]
        self.assertEqual(delta.source, "word_wrap")
        self.assertEqual(delta.old_seg_texts, [seg0, seg1])
        self.assertEqual(len(delta.new_seg_texts), 2)
        self.assertIn("\n", delta.new_seg_texts[0])
        self.assertIn("\n", delta.new_seg_texts[1])

        self.app.on_undo()
        self.assertEqual([s.text for s in doc.boxes[0].segs], [seg0, seg1])
        self.app.on_redo()
        self.assertIn("\n", doc.boxes[0].segs[0].text)
        self.assertIn("\n", doc.boxes[0].segs[1].text)

    def test_probe_5_import_from_xuat_opt_in_wrap_default_off(self) -> None:
        """Probe 5: ImportFromXUATDialog & ScriptPastePreviewDialog opt-in wrap default OFF; wraps in 1 Undo batch when ON."""
        proj_dir = self.tmp_dir / "xuat_proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        long_tr = (
            "This single-line XUnity AutoTranslator translation is intentionally much longer than "
            "fifty digit widths so that native rendering would overflow without word wrap."
        )
        (text_dir / "Story.txt").write_text(f"こんにちは、世界！={long_tr}\n", encoding="utf-8")
        xuat_index = build_xuat_index([text_dir])

        # 1. ImportFromXUATDialog default OFF leaves unwrapped
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "こんにちは、世界！"])])
        self._attach_doc(doc, "s06_xuat_off.unity3d")

        dlg_off = misora.ImportFromXUATDialog(self.app, xuat_index)
        self.assertFalse(dlg_off.var_auto_word_wrap.get(), "Opt-in wrap must default to False")
        self.assertTrue(dlg_off._on_apply_import())
        self.assertEqual(doc.boxes[0].clean_text, long_tr)
        self.assertNotIn("\n", doc.boxes[0].clean_text)

        # 2. ImportFromXUATDialog with opt-in ON wraps inside the single Undo batch
        doc2 = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "こんにちは、世界！"])])
        self._attach_doc(doc2, "s06_xuat_on.unity3d")
        orig_jp_uid = doc2.boxes[0].uid

        dlg_on = misora.ImportFromXUATDialog(self.app, xuat_index)
        dlg_on.var_auto_word_wrap.set(True)
        undo_before = self.app.undo_journal.get_undo_depth(self.app.current_file_path)
        self.assertTrue(dlg_on._on_apply_import())
        undo_after = self.app.undo_journal.get_undo_depth(self.app.current_file_path)

        self.assertEqual(undo_after, undo_before + 1)
        self.assertIn("\n", doc2.boxes[0].clean_text)
        self.assertEqual(self.app._original_jp_by_uid[orig_jp_uid], "こんにちは、世界！")
        self.app.on_undo()
        self.assertEqual(doc2.boxes[0].clean_text, "こんにちは、世界！")

        # 3. ScriptPastePreviewDialog default OFF and preview toggle ON
        parsed = parse(f"@@Pecorine\n{long_tr}\n")
        p_dlg = misora.ScriptPastePreviewDialog(self.app, parsed, 0, source_label="Test Script")
        self.assertFalse(p_dlg.var_auto_word_wrap.get())
        first_item = p_dlg.tree.get_children()[0]
        raw_preview = p_dlg.tree.item(first_item, "values")[4]
        self.assertNotIn("↵", raw_preview)
        p_dlg.var_auto_word_wrap.set(True)
        p_dlg._populate_tree()
        wrapped_preview = p_dlg.tree.item(p_dlg.tree.get_children()[0], "values")[4]
        self.assertIn("↵", wrapped_preview)
        p_dlg.on_cancel()

        # Verify _show_paste_preview_and_apply with auto_word_wrap=True commits wrapped text in 1 Undo batch
        self.app._show_paste_preview_and_apply(f"@@Pecorine\n{long_tr}\n", confirm=False, auto_word_wrap=True)
        self.assertIn("\n", doc2.boxes[0].clean_text)

    def test_probe_6_large_200_box_document_runtime(self) -> None:
        """Probe 6: Wrap a 200-box document with O(1) mock measure_fn in < 2.0s with lossless parity."""
        from core.word_wrap import wrap_text

        base_line = (
            "Hello {playername}, this is a [FF0000]long dialogue line[-] with [rub:Test]Sample[/rub] "
            "designed to benchmark wrapping speed across two hundred boxes cleanly."
        )
        texts = [f"Box {i:03d}: {base_line}" for i in range(200)]

        t0 = time.perf_counter()
        results = [wrap_text(txt, self._mono_measure, safe_width=500) for txt in texts]
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 2.0, f"200-box wrap took too long: {elapsed:.3f}s")
        for orig, res in zip(texts, results):
            self.assertTrue(res.changed)
            self.assertIn("\n", res.wrapped_text)
            self.assertEqual(
                self._strip_wrap_newlines_compare(orig, res.wrapped_text)[0],
                self._strip_wrap_newlines_compare(orig, res.wrapped_text)[1],
            )

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # -------------------------------------------------------------------------

    def test_guard_1_short_lines_and_speakers_untouched(self) -> None:
        """Guard 1: Short lines within 50d x 3 and speaker names remain untouched."""
        short_text = "Short line for {playername}."
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", short_text]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Brief narration."]),
        ])
        self._attach_doc(doc, "s06_guard1.unity3d")
        metrics = self.app._measure_dialogue_metrics(doc.boxes[0].clean_text)
        self.assertFalse(metrics["has_width_overflow"])
        self.assertFalse(metrics["has_line_overflow"])
        self.assertEqual(doc.boxes[0].speaker, "Pecorine")
        self.assertEqual(doc.boxes[1].speaker, "")

        # Post-patch extension check when core.word_wrap is present
        try:
            from core.word_wrap import wrap_text
        except ImportError:
            return
        res = wrap_text(short_text, self._mono_measure, safe_width=500)
        self.assertFalse(res.changed)
        self.assertEqual(res.wrapped_text, short_text)
        stats = self.app.apply_auto_word_wrap(scope="all", reflow_existing_breaks=False)
        self.assertEqual(stats["wrapped"], 0)
        self.assertEqual(doc.boxes[0].speaker, "Pecorine")
        self.assertEqual(doc.boxes[1].speaker, "")

    def test_guard_2_no_csif_headers_or_empty_binary_args(self) -> None:
        """Guard 2: Wrapped documents emit no CSIF headers or empty binary args and round-trip cleanly."""
        text_sample = "Hello {0},\nsecond line [b]bold[/b]."
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", text_sample]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=35, cmd_name="tag", args=["Narration\nline two."]),
        ])
        try:
            from core.word_wrap import wrap_text
            long_text = "First part of a long line that wraps cleanly for {playername} with [b]bold[/b] text."
            wrapped = wrap_text(long_text, self._mono_measure, safe_width=350).wrapped_text
            self.assertNotIn("@@", wrapped)
            doc.inject_box(0, "Kokkoro", wrapped)
        except ImportError:
            pass

        blob = doc.to_binary()
        rt_doc = StoryDocument.from_binary(blob)
        self.assertEqual(len(rt_doc.boxes), len(doc.boxes))
        for orig_b, rt_b in zip(doc.boxes, rt_doc.boxes):
            self.assertEqual(rt_b.speaker, orig_b.speaker)
            self.assertEqual(rt_b.kind, orig_b.kind)
            self.assertEqual(rt_b.clean_text, orig_b.clean_text)
            for seg in rt_b.segs:
                for arg in seg.record.args:
                    self.assertNotEqual(arg, "")


if __name__ == "__main__":
    unittest.main()
