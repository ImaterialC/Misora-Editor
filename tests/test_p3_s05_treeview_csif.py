"""
Unit and regression test suite for Phase 2.5 S05:
Dark-Theme Treeview Contrast (DEP-1 FIRST), Atomic Sparse CSIF/Metadata & Backslash Parity
(BUG-31, BUG-07, BUG-08).

Defect Probes (failing-first):
- Probe 1 (BUG-31 - DEP-1 FIRST): Treeview and Treeview.Heading WCAG contrast >= 4.5 across all presets.
- Probe 2 (BUG-07): Atomic sparse CSIF application, apply_metadata flag, preview tree mapping,
  BoxEditDelta & _modified_boxes sparse mapping, and rollback on error.
- Probe 3 (BUG-08): Backslash parity serialize -> parse round-trip across @@x, \\@@x, \\\\@@x, \\\\\\@@x,
  and multiline metadata.

Regression Guard:
- Guard 1: Basic non-sparse CSIF serialize / parse / apply contracts.
"""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

import misora
from core.script_codec import apply_to_document, parse, serialize
from core.story_ast import BoxSnapshot, StoryDocument
from core.undo_journal import BoxEditDelta


class TestP3S05TreeviewCsif(unittest.TestCase):
    """Test suite for S05: Treeview dark theme contrast, atomic sparse CSIF & backslash parity."""

    def setUp(self):
        self._orig_config_path = misora.CONFIG_PATH
        self.tmp_dir = tempfile.TemporaryDirectory()
        misora.CONFIG_PATH = Path(self.tmp_dir.name) / "misora_config.json"
        misora.CONFIG_PATH.write_text("{}", encoding="utf-8")
        self._warn_patcher = patch("tkinter.messagebox.showwarning", return_value=True)
        self._ask_patcher = patch("tkinter.messagebox.askyesno", return_value=True)
        self._warn_patcher.start()
        self._ask_patcher.start()

    def tearDown(self):
        self._ask_patcher.stop()
        self._warn_patcher.stop()
        misora.CONFIG_PATH = self._orig_config_path
        self.tmp_dir.cleanup()

    # -------------------------------------------------------------------------
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # -------------------------------------------------------------------------
    def test_probe_1_bug31_treeview_theme_contrast(self):
        """[Probe 1 — BUG-31 (DEP-1 FIRST)] Treeview and Treeview.Heading contrast.

        For EVERY preset in THEME_PRESETS, Treeview foreground vs background/fieldbackground
        and Treeview.Heading foreground vs background must satisfy WCAG contrast ratio >= 4.5.
        Pre-patch: Fails on dark themes where Treeview background defaults to #ffffff and
        foreground is #ffffff (contrast 1.0 < 4.5).
        """
        app = misora.MisoraApp()
        app.withdraw()
        app.backup_folder = str(Path(self.tmp_dir.name) / "backups")
        try:
            for theme_name, preset in misora.THEME_PRESETS.items():
                app.theme = preset
                app._apply_styles()
                style = ttk.Style(app)

                bg = style.lookup("Treeview", "background")
                fg = style.lookup("Treeview", "foreground")
                fbg = style.lookup("Treeview", "fieldbackground")
                s_bg = style.lookup("Treeview", "background", ["selected"])
                s_fg = style.lookup("Treeview", "foreground", ["selected"])
                h_bg = style.lookup("Treeview.Heading", "background")
                h_fg = style.lookup("Treeview.Heading", "foreground")

                self.assertTrue(bg, f"Treeview background missing in theme '{theme_name}'")
                self.assertTrue(fg, f"Treeview foreground missing in theme '{theme_name}'")
                self.assertTrue(fbg, f"Treeview fieldbackground missing in theme '{theme_name}'")

                cr_bg = misora.wcag_contrast_ratio(bg, fg)
                cr_fbg = misora.wcag_contrast_ratio(fbg, fg)
                self.assertGreaterEqual(
                    cr_bg,
                    4.5,
                    f"Treeview normal contrast bg vs fg failed in theme '{theme_name}': {cr_bg:.2f} < 4.5 (bg={bg}, fg={fg})"
                )
                self.assertGreaterEqual(
                    cr_fbg,
                    4.5,
                    f"Treeview fieldbackground contrast failed in theme '{theme_name}': {cr_fbg:.2f} < 4.5 (fieldbg={fbg}, fg={fg})"
                )

                if s_bg and s_fg:
                    cr_sel = misora.wcag_contrast_ratio(s_bg, s_fg)
                    self.assertGreaterEqual(
                        cr_sel,
                        4.5,
                        f"Treeview selected contrast failed in theme '{theme_name}': {cr_sel:.2f} < 4.5"
                    )

                if h_bg and h_fg:
                    cr_head = misora.wcag_contrast_ratio(h_bg, h_fg)
                    self.assertGreaterEqual(
                        cr_head,
                        4.5,
                        f"Treeview heading contrast failed in theme '{theme_name}': {cr_head:.2f} < 4.5"
                    )
        finally:
            app.destroy()

    def test_probe_2_bug07_atomic_sparse_csif_and_metadata(self):
        """[Probe 2 — BUG-07] Atomic sparse CSIF application, metadata flag & preview mapping.

        - apply_metadata=False leaves Box 0 metadata untouched.
        - ScriptPastePreviewDialog._populate_tree() maps sparse blocks to exact b.index - 1 (Box 1 and Box 3).
        - sparse @@#1|Kokkoro + @@#3|Pecorine applied while current_box_idx == 5 previews, mutates,
          records undo for boxes 0 and 2 (NOT 5 and 6), and undoes cleanly.
        - sparse kind-conversion (@@#2|_ + @@#4|Kyou) keeps boxes separate and resolves target UID.
        - invalid out-of-range sparse payload with @@!title raises and leaves BOTH Box 0 and all
          dialogue untouched (atomic transaction rollback).
        """
        # Part A: apply_metadata=False contract on apply_to_document
        doc_a = StoryDocument([])
        doc_a.set_metadata(title="Original Title", subtitle="Original Sub", summary="Original Sum")
        doc_a.insert_box(0, BoxSnapshot(speaker="S1", voice_cue="", kind="print", seg_texts=["Original Text"]))
        parsed_a = parse("@@!title Modified Title\n@@S1\nModified Text")

        apply_to_document(doc_a, parsed_a, apply_metadata=False)
        self.assertEqual(doc_a.get_metadata()["title"], "Original Title")
        self.assertEqual(doc_a.boxes[0].clean_text, "Modified Text")

        # Part B & C: UI sparse mapping and atomic application in MisoraApp
        app = misora.MisoraApp()
        app.withdraw()
        app.backup_folder = str(Path(self.tmp_dir.name) / "backups")
        try:
            doc_b = StoryDocument([])
            for i in range(8):
                doc_b.insert_box(i, BoxSnapshot(speaker=f"Hero_{i}", voice_cue="", kind="print", seg_texts=[f"Text {i}"]))

            file_path = Path(self.tmp_dir.name) / "test_story.unity3d"
            app.current_doc = doc_b
            app.current_file_path = file_path
            app.undo_journal.set_active_file(file_path)
            app.current_box_idx = 5
            app._update_views()
            app._modified_boxes.clear()

            sparse_csif = "@@#1|Kokkoro\nKokoText\n@@#3|Pecorine\nPecoText\n"
            parsed_sparse = parse(sparse_csif)

            # Direct check of ScriptPastePreviewDialog._populate_tree()
            dlg = misora.ScriptPastePreviewDialog(app, parsed_sparse, start_idx=5, source_label="Test")
            items = dlg.tree.get_children()
            self.assertEqual(len(items), 2, "Preview dialog should contain exactly 2 sparse rows")
            val0 = dlg.tree.item(items[0], "values")
            val1 = dlg.tree.item(items[1], "values")
            self.assertEqual(val0[0], "Box 1", f"First sparse row must be 'Box 1', got {val0[0]}")
            self.assertEqual(val1[0], "Box 3", f"Second sparse row must be 'Box 3', got {val1[0]}")
            dlg.destroy()

            # Apply sparse script with current_box_idx == 5
            applied = app._show_paste_preview_and_apply(sparse_csif, confirm=False)
            self.assertTrue(applied)

            # Verify boxes 0 and 2 are mutated, while boxes 5 and 6 remain untouched
            self.assertEqual(app.current_doc.boxes[0].clean_text, "KokoText")
            self.assertEqual(app.current_doc.boxes[0].speaker, "Kokkoro")
            self.assertEqual(app.current_doc.boxes[2].clean_text, "PecoText")
            self.assertEqual(app.current_doc.boxes[2].speaker, "Pecorine")
            self.assertEqual(app.current_doc.boxes[5].clean_text, "Text 5")
            self.assertEqual(app.current_doc.boxes[6].clean_text, "Text 6")

            # Verify _modified_boxes contains {0, 2} and NOT {5, 6}
            self.assertEqual(app._modified_boxes, {0, 2}, f"_modified_boxes expected {{0, 2}}, got {app._modified_boxes}")

            # Verify recorded deltas in undo journal
            state = app.undo_journal._get_state(file_path)
            self.assertIsNotNone(state, "File state must be registered in undo journal")
            self.assertGreaterEqual(len(state.undo_stack), 1)
            last_op = state.undo_stack[-1]
            box_deltas = [d for d in last_op.deltas if isinstance(d, BoxEditDelta)]
            self.assertEqual(len(box_deltas), 2)
            self.assertEqual([d.box_index for d in box_deltas], [0, 2])
            self.assertIsNotNone(box_deltas[0].box_uid)
            self.assertIsNotNone(box_deltas[1].box_uid)

            # Undo reverts Box 0 and Box 2 cleanly
            app.on_undo()
            self.assertEqual(app.current_doc.boxes[0].clean_text, "Text 0")
            self.assertEqual(app.current_doc.boxes[0].speaker, "Hero_0")
            self.assertEqual(app.current_doc.boxes[2].clean_text, "Text 2")
            self.assertEqual(app.current_doc.boxes[2].speaker, "Hero_2")

            # Part D: Sparse kind-conversion test (@@#2|_ + @@#4|Kyou)
            uid_1 = app.current_doc.boxes[1].segs[0].record.uid
            uid_3 = app.current_doc.boxes[3].segs[0].record.uid
            app._modified_boxes.clear()
            app._show_paste_preview_and_apply("@@#2|_\nNarrText\n@@#4|Kyou\nKyouText\n", confirm=False)

            self.assertEqual(app.current_doc.boxes[1].kind, "tag")
            self.assertEqual(app.current_doc.boxes[1].speaker, "")
            self.assertEqual(app.current_doc.boxes[1].clean_text, "NarrText")
            self.assertEqual(app.current_doc.boxes[1].segs[0].record.uid, uid_1)

            self.assertEqual(app.current_doc.boxes[3].kind, "print")
            self.assertEqual(app.current_doc.boxes[3].speaker, "Kyou")
            self.assertEqual(app.current_doc.boxes[3].clean_text, "KyouText")
            self.assertEqual(app.current_doc.boxes[3].segs[0].record.uid, uid_3)
            self.assertEqual(app._modified_boxes, {1, 3})
        finally:
            app.destroy()

        # Part E: Atomic rollback on invalid sparse index
        doc_err = StoryDocument([])
        doc_err.set_metadata(title="Safe Title", subtitle="Safe Sub", summary="Safe Sum")
        doc_err.insert_box(0, BoxSnapshot(speaker="S0", voice_cue="", kind="print", seg_texts=["T0"]))
        doc_err.insert_box(1, BoxSnapshot(speaker="S1", voice_cue="", kind="print", seg_texts=["T1"]))
        orig_records = copy.deepcopy(doc_err.records)

        bad_sparse = parse("@@!title Hacked Title\n@@#999|Nobody\nBad Text\n")
        with self.assertRaises(IndexError):
            apply_to_document(doc_err, bad_sparse)

        # Confirm Box 0 metadata and dialogue are 100% untouched
        self.assertEqual(doc_err.get_metadata()["title"], "Safe Title")
        self.assertEqual(doc_err.get_metadata()["subtitle"], "Safe Sub")
        self.assertEqual(doc_err.boxes[0].clean_text, "T0")
        self.assertEqual(doc_err.boxes[1].clean_text, "T1")

    def test_probe_3_bug08_backslash_parity_csif_roundtrip(self):
        """[Probe 3 — BUG-08] Exact serialize -> parse round-trip across backslash prefixes.

        Tests 4 distinct inputs: @@x, \\@@x, \\\\@@x, \\\\\\@@x, plus ordinary \\text and multiline metadata.
        Pre-patch: Fails on \\@@x which serializes as \\@@x and unescapes to @@x on parse.
        """
        cases = [
            ("@@x", r"\@@x"),
            (r"\@@x", r"\\@@x"),
            (r"\\@@x", r"\\\@@x"),
            (r"\\\@@x", r"\\\\@@x"),
            (r"\text", r"\text"),
        ]

        for input_text, expected_escaped in cases:
            doc = StoryDocument([])
            doc.insert_box(0, BoxSnapshot(speaker="Speaker", voice_cue="", kind="print", seg_texts=[input_text]))
            csif = serialize(doc)

            # Check that serialize produced the expected escaped body line
            lines = csif.splitlines()
            self.assertIn(expected_escaped, lines, f"serialize() failed to escape {input_text!r} as {expected_escaped!r}")

            # Check that parse restores the exact input text
            parsed = parse(csif)
            self.assertEqual(len(parsed.blocks), 1)
            self.assertEqual(
                parsed.blocks[0].text,
                input_text,
                f"Backslash round-trip failed: expected {input_text!r}, got {parsed.blocks[0].text!r}"
            )

        # Multiline metadata round-trip check
        doc_meta = StoryDocument([])
        doc_meta.set_metadata(title="Title Line 1\n\\@@meta_escaped")
        csif_meta = serialize(doc_meta)
        parsed_meta = parse(csif_meta)
        self.assertEqual(
            parsed_meta.metadata.title,
            "Title Line 1\n\\@@meta_escaped",
            "Multiline metadata backslash round-trip failed"
        )

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both before and after patch)
    # -------------------------------------------------------------------------
    def test_guard_1_lightweight_csif_contracts(self):
        """[Guard 1] Lightweight verification of standard non-sparse CSIF contracts."""
        doc = StoryDocument([])
        doc.set_metadata(title="Test Story", subtitle="Chapter 1", summary="A peaceful morning")
        doc.insert_box(0, BoxSnapshot(speaker="Kokkoro", voice_cue="vo_101", kind="print", seg_texts=["Good morning, Lord Knight."]))
        doc.insert_box(1, BoxSnapshot(speaker="", voice_cue="", kind="tag", seg_texts=["The sun shines through the window."]))

        csif = serialize(doc)
        parsed = parse(csif)

        self.assertEqual(parsed.metadata.title, "Test Story")
        self.assertEqual(parsed.metadata.subtitle, "Chapter 1")
        self.assertEqual(len(parsed.blocks), 2)
        self.assertEqual(parsed.blocks[0].speaker, "Kokkoro")
        self.assertEqual(parsed.blocks[0].text, "Good morning, Lord Knight.")
        self.assertTrue(parsed.blocks[1].is_narration)
        self.assertEqual(parsed.blocks[1].text, "The sun shines through the window.")


if __name__ == "__main__":
    unittest.main()
