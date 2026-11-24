"""
Unit and regression test suite for Phase 2.5 S04:
Kind-Conversion Box Separation, Voice/Breaker Ownership, Multi-Segment Undo/Paste,
UID Coalesce & Tombstones (BUG-02, BUG-05, BUG-06, BUG-17, HYG-04).

Defect Probes (failing-first):
- Probe 1 (BUG-02): [tag A][print B][tag C] -> inject_box(1, '', 'new B') keeps 3 separate
  boxes without IndexError; survives binary roundtrip and Undo/Redo.
- Probe 2 (BUG-05): move_box() moves attached cmd_id=12 vo_ cue with its box, anchors before
  destination vo_ cue, preserves unknown interstitial commands, never merges same-speaker boxes;
  delete_boxes() removes only empty tap-breaker without double touch stacking in binary.
- Probe 3 (BUG-06): Editing 2-segment box then Undo restores BOTH original segments verbatim;
  internal on_box_paste() preserves seg_texts, voice_cue, extra_args.
- Probe 4 (BUG-17): Two BoxEditDelta ops with different non-None box_uid at same box_index do
  not coalesce; coalescing propagates new_seg_texts.
- Probe 5 (HYG-04): Repeated insert/delete cycles do not grow doc.removed_records unboundedly.

Regression Guard:
- Guard 1: Direct cmd_id 35 (narration) & 32 (subtitle) invariance + basic AST roundtrip.
"""

import copy
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import List, Optional

import misora
from core.story_ast import Box, BoxSnapshot, Record, Seg, StoryDocument
from core.undo_journal import BoxEditDelta, BoxStructuralDelta, MasterUndoJournal


class TestP3S04AstMutations(unittest.TestCase):
    """Test suite for S04 AST mutations, voice/breaker ownership, multi-segment undo/paste, UID coalesce & tombstones."""

    def setUp(self):
        self._orig_config_path = misora.CONFIG_PATH
        self.tmp_dir = tempfile.TemporaryDirectory()
        misora.CONFIG_PATH = Path(self.tmp_dir.name) / "misora_config.json"
        misora.CONFIG_PATH.write_text("{}", encoding="utf-8")

    def tearDown(self):
        misora.CONFIG_PATH = self._orig_config_path
        self.tmp_dir.cleanup()

    # -------------------------------------------------------------------------
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # -------------------------------------------------------------------------
    def test_probe_1_bug02_kind_conversion_box_separation_no_collapse(self):
        """[Probe 1 — BUG-02] [tag A][print B][tag C] -> inject_box(1, '', 'new B')

        Keeps 3 separate boxes with zero IndexError, surviving binary round-trip and Undo/Redo.
        """
        doc = StoryDocument()
        r_tag_a = Record(cmd_id=35, cmd_name="tag", args=["Text A"])
        r_pr_b = Record(cmd_id=6, cmd_name="print", args=["Hero", "Text B"])
        r_tag_c = Record(cmd_id=35, cmd_name="tag", args=["Text C"])
        doc.records = [r_tag_a, r_pr_b, r_tag_c]
        doc._rebuild_boxes()

        self.assertEqual(len(doc.boxes), 3, "Baseline document should project 3 distinct boxes.")
        self.assertEqual(doc.boxes[0].kind, "tag")
        self.assertEqual(doc.boxes[1].kind, "print")
        self.assertEqual(doc.boxes[2].kind, "tag")

        # Mutate Box 1 to empty speaker (converts print -> tag)
        doc.inject_box(1, "", "New Text B")

        # Assertion 1: Must retain exactly 3 separate boxes (no collapse into 1 multi-segment box)
        self.assertEqual(len(doc.boxes), 3, "Clearing speaker adjacent to narration must NOT collapse boxes.")
        self.assertEqual(doc.boxes[0].clean_text, "Text A")
        self.assertEqual(doc.boxes[1].clean_text, "New Text B")
        self.assertEqual(doc.boxes[1].kind, "tag")
        self.assertEqual(doc.boxes[2].clean_text, "Text C")

        # Assertion 2: Survives binary serialization and rebuild round-trip
        bin_data = doc.to_binary()
        doc_reloaded = StoryDocument.from_binary(bin_data)
        self.assertEqual(len(doc_reloaded.boxes), 3, "Binary roundtrip must preserve 3 separate boxes.")
        self.assertEqual(doc_reloaded.boxes[0].clean_text, "Text A")
        self.assertEqual(doc_reloaded.boxes[1].clean_text, "New Text B")
        self.assertEqual(doc_reloaded.boxes[2].clean_text, "Text C")

        # Assertion 3: Undo / Redo keeps 3 boxes throughout
        # Simulating Undo: restore speaker "Hero" and text "Text B" on Box 1
        doc.inject_box(1, "Hero", "Text B")
        self.assertEqual(len(doc.boxes), 3, "Undo restoring speaker must preserve 3 boxes.")
        self.assertEqual(doc.boxes[1].kind, "print")
        self.assertEqual(doc.boxes[1].speaker, "Hero")
        self.assertEqual(doc.boxes[1].clean_text, "Text B")

        # Simulating Redo: clear speaker again
        doc.inject_box(1, "", "New Text B")
        self.assertEqual(len(doc.boxes), 3, "Redo clearing speaker must preserve 3 boxes.")
        self.assertEqual(doc.boxes[1].kind, "tag")
        self.assertEqual(doc.boxes[1].clean_text, "New Text B")

    def test_probe_2_bug05_structural_ownership_voice_and_breakers(self):
        """[Probe 2 — BUG-05] Structural ownership across move_box and delete_boxes.

        move_box() moves attached cmd_id=12 vo_ cue with its box, anchors before destination vo_ cue,
        preserves unknown interstitial commands, never merges same-speaker boxes;
        delete_boxes() removes only empty tap-breaker (no double touch stacking across binary round-trip).
        """
        doc = StoryDocument()
        # Box 0: Hero with attached voice cue "vo_001"
        r_vc0 = Record(cmd_id=12, cmd_name="touch", args=["vo_001"])
        r_b0 = Record(cmd_id=6, cmd_name="print", args=["Hero", "Box Zero"])
        r_br0 = Record(cmd_id=10, cmd_name="touch", args=[])

        # Box 1: Hero with unknown interstitial command (cmd_id 999) + voice cue "vo_002"
        r_unk = Record(cmd_id=999, cmd_name="cmd_999", args=["param_x"])
        r_vc1 = Record(cmd_id=12, cmd_name="touch", args=["vo_002"])
        r_b1 = Record(cmd_id=6, cmd_name="print", args=["Hero", "Box One"])
        r_br1 = Record(cmd_id=10, cmd_name="touch", args=[])

        # Box 2: Alice with no voice cue
        r_b2 = Record(cmd_id=6, cmd_name="print", args=["Alice", "Box Two"])
        r_br2 = Record(cmd_id=10, cmd_name="touch", args=[])

        doc.records = [r_vc0, r_b0, r_br0, r_unk, r_vc1, r_b1, r_br1, r_b2, r_br2]
        doc._rebuild_boxes()

        self.assertEqual(len(doc.boxes), 3)
        self.assertEqual(doc.boxes[0].voice_cue, "vo_001")
        self.assertEqual(doc.boxes[1].voice_cue, "vo_002")

        # Move Box 0 to index 1 (between Box 1 and Box 2)
        doc.move_box(0, 1)
        self.assertEqual(len(doc.boxes), 3)
        # Verify Box 0's voice cue moved with it to index 1
        self.assertEqual(doc.boxes[0].clean_text, "Box One")
        self.assertEqual(doc.boxes[0].voice_cue, "vo_002", "Box One retained its voice cue.")
        self.assertEqual(doc.boxes[1].clean_text, "Box Zero")
        self.assertEqual(doc.boxes[1].voice_cue, "vo_001", "Box Zero brought its voice cue along.")

        # Verify unknown interstitial command was preserved in document records
        has_unk = any(r.cmd_id == 999 and r.args == ["param_x"] for r in doc.records)
        self.assertTrue(has_unk, "Unknown interstitial command cmd_999 must be preserved.")

        # Delete Box 0 (which is now Box One)
        doc.delete_boxes([0])
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].clean_text, "Box Zero")
        self.assertEqual(doc.boxes[0].voice_cue, "vo_001")

        # Verify binary serialization does not contain stacked duplicate empty tap-breakers (touch#10 touch#10)
        bin_out = doc.to_binary()
        doc_re = StoryDocument.from_binary(bin_out)
        self.assertEqual(len(doc_re.boxes), 2)

        # Check for adjacent touch#10 empty breakers in records
        active = [r for r in doc_re.records if r.cmd_id == 10 and not r.args]
        # In a 2-box script, there should only be at most 2 tap breakers, never stacked
        for i in range(len(doc_re.records) - 1):
            cur_r = doc_re.records[i]
            nxt_r = doc_re.records[i + 1]
            if cur_r.cmd_id == 10 and not cur_r.args and nxt_r.cmd_id == 10 and not nxt_r.args:
                self.fail("Found stacked duplicate empty tap breakers (touch#10 touch#10) in records.")

    def test_probe_3_bug06_multisegment_undo_and_internal_box_paste(self):
        """[Probe 3 — BUG-06] Multi-segment editing, undo split restoration & on_box_paste preservation.

        Editing a 2-segment box then Undo restores BOTH original segments verbatim;
        internal on_box_paste() preserves seg_texts, voice_cue, and extra_args.
        """
        doc = StoryDocument()
        r_seg1 = Record(cmd_id=6, cmd_name="print", args=["Hero", "First Segment", "extra_1"])
        r_seg2 = Record(cmd_id=6, cmd_name="print", args=["Hero", "Second Segment", "extra_2"])
        doc.records = [r_seg1, r_seg2]
        doc._rebuild_boxes()

        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(len(doc.boxes[0].segs), 2)
        box = doc.boxes[0]

        # 1. Edit multi-segment box via inject_box
        old_segments = [s.text for s in box.segs]
        self.assertEqual(old_segments, ["First Segment", "Second Segment"])

        delta = BoxEditDelta(
            box_index=0,
            old_speaker="Hero",
            new_speaker="Hero",
            old_text=box.clean_text,
            new_text="Entirely New Dialogue",
            box_uid=box.segs[0].record.uid,
            old_seg_texts=old_segments,
        )

        # Apply edit (flattens dialogue text across segments)
        doc.inject_box(0, None, "Entirely New Dialogue")
        self.assertEqual(doc.boxes[0].clean_text, "Entirely New Dialogue")

        # Now simulate Undo using seg_texts restore
        doc.inject_box(0, delta.old_speaker, delta.old_text, seg_texts=delta.old_seg_texts)
        self.assertEqual(len(doc.boxes[0].segs), 2, "Undo must restore 2 segments.")
        self.assertEqual(doc.boxes[0].segs[0].text, "First Segment")
        self.assertEqual(doc.boxes[0].segs[1].text, "Second Segment")
        self.assertEqual(doc.boxes[0].segs[0].record.args[2:], ["extra_1"], "Preserved extra_1.")
        self.assertEqual(doc.boxes[0].segs[1].record.args[2:], ["extra_2"], "Preserved extra_2.")

        # 2. Test misora.py on_box_paste() preservation
        app = misora.MisoraApp(restore_session=False)
        app.withdraw()
        try:
            app.current_doc = StoryDocument()
            app.current_doc.records = [
                Record(cmd_id=6, cmd_name="print", args=["Hero", "Existing Box"]),
                Record(cmd_id=10, cmd_name="touch", args=[]),
            ]
            app.current_doc._rebuild_boxes()
            app.current_box_idx = 0

            # Prepare internal box clipboard snapshot with 2 segments and voice cue
            snap = BoxSnapshot(
                speaker="Hero",
                voice_cue="vo_paste_01",
                kind="print",
                seg_texts=["Pasted Seg A", "Pasted Seg B"],
                extra_args=[["exA"], ["exB"]],
            )
            app._box_clipboard = [snap]
            app._box_clipboard_text = snap.clean_text
            # Mock safe_clipboard_get to match _box_clipboard_text
            app.safe_clipboard_get = lambda: snap.clean_text

            # Call verified live method: on_box_paste(confirm=False)
            app.on_box_paste(confirm=False)

            self.assertEqual(len(app.current_doc.boxes), 2, "Pasted box inserted into document.")
            pasted_box = app.current_doc.boxes[1]
            self.assertEqual(len(pasted_box.segs), 2, "Pasted box must retain 2 segments.")
            self.assertEqual(pasted_box.segs[0].text, "Pasted Seg A")
            self.assertEqual(pasted_box.segs[1].text, "Pasted Seg B")
            self.assertEqual(pasted_box.voice_cue, "vo_paste_01", "Pasted box must retain voice cue.")
            self.assertEqual(pasted_box.segs[0].record.args[2:], ["exA"], "Retained extra_args.")
        finally:
            app.destroy()

    def test_probe_4_bug17_uid_coalesce_and_seg_texts_propagation(self):
        """[Probe 4 — BUG-17] Undo coalescing requires box_uid match when both non-None and propagates seg_texts.

        Two BoxEditDelta ops with different non-None box_uid at the same box_index within 2s MUST NOT coalesce;
        coalesced multi-seg edits keep initial old_seg_texts and final new_seg_texts.
        """
        journal = MasterUndoJournal()
        key = "test_doc.txt"

        # 1. Two edits at same box_index=0 but with different box_uid
        d1 = BoxEditDelta(
            box_index=0,
            old_speaker="Alice",
            new_speaker="Alice",
            old_text="Hello",
            new_text="Hello World",
            file_path=key,
            box_uid=101,
            source="keyboard",
        )
        journal.record(d1)

        d2 = BoxEditDelta(
            box_index=0,
            old_speaker="Bob",
            new_speaker="Bob",
            old_text="Start",
            new_text="Start Now",
            file_path=key,
            box_uid=102,  # Different box_uid!
            source="keyboard",
        )
        journal.record(d2)

        # In BUG-17, d1 and d2 MUST NOT coalesce because box_uid 101 != 102
        state = journal._get_state(key)
        self.assertEqual(
            len(state.undo_stack),
            2,
            "Different box_uid at same box_index must NOT coalesce."
        )

        # 2. Multi-segment coalescing: keep initial old_seg_texts and propagate new_seg_texts
        journal_multi = MasterUndoJournal()
        d_m1 = BoxEditDelta(
            box_index=0,
            old_speaker="Hero",
            new_speaker="Hero",
            old_text="A B",
            new_text="A B1",
            file_path=key,
            box_uid=200,
            source="keyboard",
            old_seg_texts=["A", "B"],
            new_seg_texts=["A", "B1"],
        )
        journal_multi.record(d_m1)

        # Subsequent keystroke coalescing for same box_uid
        d_m2 = BoxEditDelta(
            box_index=0,
            old_speaker="Hero",
            new_speaker="Hero",
            old_text="A B1",
            new_text="A B12",
            file_path=key,
            box_uid=200,
            source="keyboard",
            old_seg_texts=["A", "B1"],
            new_seg_texts=["A", "B12"],
        )
        journal_multi.record(d_m2)

        state_m = journal_multi._get_state(key)
        self.assertEqual(len(state_m.undo_stack), 1, "Same box_uid should coalesce.")
        coalesced_delta = state_m.undo_stack[0].deltas[0]
        self.assertEqual(coalesced_delta.old_seg_texts, ["A", "B"], "Retained initial pre-coalesce old_seg_texts.")
        self.assertEqual(coalesced_delta.new_seg_texts, ["A", "B12"], "Propagated final new_seg_texts.")

    def test_probe_5_hyg04_bounded_removed_records(self):
        """[Probe 5 — HYG-04] Repeated insert/delete cycles do not grow doc.removed_records unboundedly."""
        doc = StoryDocument()
        snap = BoxSnapshot(speaker="Hero", voice_cue="", kind="print", seg_texts=["Test"])

        for _ in range(500):
            doc.insert_box(0, snap)
            doc.delete_boxes([0])

        self.assertLessEqual(
            len(doc.removed_records),
            100,
            f"removed_records ({len(doc.removed_records)}) must be bounded and not leak memory indefinitely."
        )

    # -------------------------------------------------------------------------
    # Regression Guards (MUST PASS both before AND after patch)
    # -------------------------------------------------------------------------
    def test_guard_1_lightweight_ast_binary_invariance(self):
        """[Guard 1] cmd_id 35 (narration) & 32 (subtitle) invariance + basic AST roundtrip."""
        doc = StoryDocument()
        doc.set_metadata(title="Title Ep", subtitle="Sub Ep", summary="Sum Ep")
        snap_pr = BoxSnapshot(speaker="Hero", voice_cue="", kind="print", seg_texts=["Spoken Text"])
        snap_tag = BoxSnapshot(speaker="", voice_cue="", kind="tag", seg_texts=["Narration Text"])
        doc.insert_box(0, snap_pr)
        doc.insert_box(1, snap_tag)

        # Verify command IDs in records
        meta_32 = next((r for r in doc.records if r.cmd_id == 32), None)
        self.assertIsNotNone(meta_32, "Subtitle record retains cmd_id == 32.")

        tag_35 = next((r for r in doc.records if r.cmd_id == 35), None)
        self.assertIsNotNone(tag_35, "Narration record retains cmd_id == 35.")

        # Binary roundtrip check
        raw_bin = doc.to_binary()
        doc_re = StoryDocument.from_binary(raw_bin)
        self.assertEqual(len(doc_re.boxes), 2)
        self.assertEqual(doc_re.boxes[0].clean_text, "Spoken Text")
        self.assertEqual(doc_re.boxes[1].clean_text, "Narration Text")


if __name__ == "__main__":
    unittest.main()
