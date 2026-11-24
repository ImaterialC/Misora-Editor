#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 Session S19: Whole-File Editable Raw Commands (FEAT-11)."""

import shutil
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import misora
from core.story_ast import Record, StoryDocument


class TestP3S19RawCommandsEdit(unittest.TestCase):
    """Failing-first defect probes and regression guard for S19 (FEAT-11)."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s19_test_"))
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

    def tearDown(self):
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

    def _create_sample_v2_file(self, name: str = "s19_sample.v2.txt") -> Path:
        doc = StoryDocument(
            [
                Record(cmd_id=0, cmd_name="title", args=["Episode 1"]),
                Record(cmd_id=9, cmd_name="voice", args=["vo_old_001"]),
                Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Original JP 1"]),
                Record(cmd_id=10, cmd_name="touch", args=[]),
                Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Original JP 2"]),
            ]
        )
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        return p

    # =========================================================================
    # DEFECT PROBES (MUST FAIL BEFORE PATCH, PASS AFTER PATCH)
    # =========================================================================

    def test_probe_1_edit_vo_cue_confirm_yes_remap_locks_and_undo(self):
        """[Probe 1] Editing vo_ cue in Raw Commands -> Yes updates AST, preserves locks/JP keys, and Undo restores exact Records."""
        story_path = self._create_sample_v2_file()
        self.app.open_file(story_path)

        # Lock Box 0 and translate it so clean_text != immutable JP key
        self.app.current_box_idx = 0
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(0))
        b0_uid = self.app.current_doc.boxes[0].segs[0].record.uid
        self.app._original_jp_by_uid[b0_uid] = "Original JP 1"
        self.app.current_doc.inject_box(0, "Pecorine", "Translated EN 1")
        self.app._update_views()

        prior_records = [
            (r.cmd_id, r.cmd_name, list(r.args), r.category)
            for r in self.app.current_doc.records
        ]

        # Enter Raw Commands edit mode
        self.app.on_enter_raw_edit_mode()
        self.assertEqual(self.app.txt_raw.cget("state"), "normal")
        raw_content = self.app.txt_raw.get("1.0", "end-1c")
        self.assertIn("#!priconne-story v2", raw_content)
        self.assertIn("vo_old_001", raw_content)

        # Edit voice cue in txt_raw
        edited_v2 = raw_content.replace("vo_old_001", "vo_new_999")
        self.app.txt_raw.delete("1.0", tk.END)
        self.app.txt_raw.insert("1.0", edited_v2)

        with patch.object(misora.messagebox, "askyesno", return_value=True) as mock_confirm:
            self.app.on_apply_raw_commands()
            self.assertTrue(mock_confirm.called)

        # AST updated, views refreshed, txt_raw returned to read-only
        self.assertEqual(self.app.txt_raw.cget("state"), "disabled")
        self.assertTrue(self.app.is_dirty)
        self.assertEqual(self.app.current_doc.boxes[0].voice_cue, "vo_new_999")
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, "Translated EN 1")

        # Lock and immutable JP key preserved via stable key remap
        self.assertTrue(self.app.is_box_locked(0))
        new_b0_uid = self.app.current_doc.boxes[0].segs[0].record.uid
        self.assertEqual(self.app._original_jp_by_uid.get(new_b0_uid), "Original JP 1")

        # Undo (DocumentRecordsDelta) restores exact prior Record list & lock/JP state
        self.app.on_undo()
        restored_records = [
            (r.cmd_id, r.cmd_name, list(r.args), r.category)
            for r in self.app.current_doc.records
        ]
        self.assertEqual(restored_records, prior_records)
        self.assertEqual(self.app.current_doc.boxes[0].voice_cue, "vo_old_001")
        self.assertTrue(self.app.is_box_locked(0))
        restored_b0_uid = self.app.current_doc.boxes[0].segs[0].record.uid
        self.assertEqual(self.app._original_jp_by_uid.get(restored_b0_uid), "Original JP 1")

    def test_probe_2_corrupted_v2_aborts_reverts_and_leaves_state_unchanged(self):
        """[Probe 2] Corrupted v2 text -> Confirm Yes aborts cleanly, reverts txt_raw, and leaves doc/dirty/undo unchanged."""
        story_path = self._create_sample_v2_file("s19_corrupt.v2.txt")
        self.app.open_file(story_path)

        orig_records = [
            (r.cmd_id, r.cmd_name, list(r.args), r.category)
            for r in self.app.current_doc.records
        ]
        orig_dirty = self.app.is_dirty
        orig_undo_depth = self.app.undo_journal.get_undo_depth(str(story_path))

        self.app.on_enter_raw_edit_mode()
        self.app.txt_raw.delete("1.0", tk.END)
        self.app.txt_raw.insert("1.0", "print#notanumber\nPecorine\nBroken\nOther\n")

        with patch.object(misora.messagebox, "askyesno", return_value=True), \
             patch.object(misora.messagebox, "showerror") as mock_err:
            self.app.on_apply_raw_commands()
            self.assertTrue(mock_err.called)

        self.assertEqual(self.app.txt_raw.cget("state"), "disabled")
        self.assertNotIn("print#notanumber", self.app.txt_raw.get("1.0", "end-1c"))
        self.assertEqual(
            [(r.cmd_id, r.cmd_name, list(r.args), r.category) for r in self.app.current_doc.records],
            orig_records,
        )
        self.assertEqual(self.app.is_dirty, orig_dirty)
        self.assertEqual(self.app.undo_journal.get_undo_depth(str(story_path)), orig_undo_depth)

    def test_probe_3_confirm_no_leaves_document_unchanged(self):
        """[Probe 3] Clicking No on confirmation leaves document, dirty flag, and undo journal unchanged."""
        story_path = self._create_sample_v2_file("s19_cancel.v2.txt")
        self.app.open_file(story_path)

        orig_records = [
            (r.cmd_id, r.cmd_name, list(r.args), r.category)
            for r in self.app.current_doc.records
        ]
        self.app.on_enter_raw_edit_mode()
        raw_content = self.app.txt_raw.get("1.0", "end-1c").replace("vo_old_001", "vo_should_not_apply")
        self.app.txt_raw.delete("1.0", tk.END)
        self.app.txt_raw.insert("1.0", raw_content)

        with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_confirm:
            self.app.on_apply_raw_commands()
            self.assertTrue(mock_confirm.called)

        self.assertEqual(
            [(r.cmd_id, r.cmd_name, list(r.args), r.category) for r in self.app.current_doc.records],
            orig_records,
        )
        self.assertFalse(self.app.is_dirty)
        self.assertEqual(self.app.undo_journal.get_undo_depth(str(story_path)), 0)

    # =========================================================================
    # REGRESSION GUARDS (MUST PASS BEFORE AND AFTER PATCH)
    # =========================================================================

    def test_guard_1_v2_codec_and_readonly_raw_contracts(self):
        """[Guard 1] Lossless v2 preserves cmd_id 35 & 32 through binary roundtrip; txt_raw stays disabled outside Edit Raw."""
        doc = StoryDocument(
            [
                Record(cmd_id=32, cmd_name="cmd_32", args=["Subtitle A"]),
                Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
                Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello"]),
            ]
        )
        v2_txt = doc.to_v2_text()
        parsed = StoryDocument.from_v2_text(v2_txt)
        rt = StoryDocument.from_binary(parsed.to_binary())
        self.assertEqual([r.cmd_id for r in rt.records], [32, 35, 6])
        self.assertEqual(rt.records[0].args, ["Subtitle A"])
        self.assertEqual(rt.records[1].args, ["Narration line"])

        story_path = self._create_sample_v2_file("s19_guard.v2.txt")
        self.app.open_file(story_path)
        self.assertEqual(self.app.txt_raw.cget("state"), "disabled")
        self.app._update_raw_view()
        self.assertEqual(self.app.txt_raw.cget("state"), "disabled")


if __name__ == "__main__":
    unittest.main()
