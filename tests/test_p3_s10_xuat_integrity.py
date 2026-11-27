#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.test_p3_s10_xuat_integrity — Failing-first regression test suite for Session S10:
Immutable box.uid XUAT JP Keys, Save Conflict Preview Gate & Atomic XUAT Dictionary Writes.

Defects tested:
- BUG-25: Immutable Japanese source keys by box.uid (never overwritten with English,
          never fall back to current edited text), no positional shift on box insertion,
          and save conflict preview gate with messagebox.askyesno prompt.
- BUG-26: find_and_update() delegates to write_atomic_encoded() preserving UTF-8 BOM,
          CRLF/LF line endings, and bounded retry.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import misora
from core.story_ast import StoryDocument, Record, Box
from core.xunity_sync import XUnitySyncManager, split_xuat_line, escape_xuat_value


class TestP3S10XuatIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name).resolve()

        # Isolate config and redirect backups away from repo root backups/
        self.orig_config_path = misora.CONFIG_PATH
        self.test_config = self.tmp_dir / "misora_config.json"
        misora.CONFIG_PATH = self.test_config

        self.backup_dir = self.tmp_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.app = None

    def tearDown(self):
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None

        misora.CONFIG_PATH = self.orig_config_path
        self.tmp_dir_obj.cleanup()

    def _init_app(self) -> misora.MisoraApp:
        app = misora.MisoraApp(show_splash=False, restore_session=False)
        app.withdraw()
        app.backup_folder = str(self.backup_dir)
        self.app = app
        return app

    # =========================================================================
    # Defect Probes (MUST FAIL before patch, PASS after patch)
    # =========================================================================

    def test_probe_1_bug25_immutable_jp_key_and_conflict_preview_gate(self):
        """
        [Probe 1 — BUG-25]
        Part A: Consecutive saves (EN1 -> EN2) still match original JP key (never EN1).
        Part B: Inserting a box before target does not shift JP key to the inserted box.
        Part C: Conflicting XUAT translations trigger confirmation prompt; clean entries do not.
        """
        app = self._init_app()

        # Setup mock XUAT dictionary inside canonical Translation\en\Text (S11b2 Q-02b)
        xuat_dir = self.tmp_dir / "Translation" / "en" / "Text"
        xuat_dir.mkdir(parents=True, exist_ok=True)
        xuat_file = xuat_dir / "Dialogue.txt"
        xuat_content = (
            "\ufeffわたし、お腹が空きました！=Old Hungry Translation\r\n"
            "キャル、早く来て！=Old Kyaru Translation\r\n"
        )
        xuat_file.write_bytes(xuat_content.encode("utf-8"))

        app.xuat_search_roots = [xuat_dir]
        app.var_sync_xuat.set(True)

        # Create v2 story file with 2 boxes
        story_file = self.tmp_dir / "story.v2.txt"
        init_doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "わたし、お腹が空きました！"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "キャル、早く来て！"]),
        ])
        story_file.write_text(init_doc.to_v2_text(), encoding="utf-8")

        # Open file
        app.open_file(story_file)
        self.assertEqual(len(app.current_doc.boxes), 2)
        box0_uid = misora._get_box_uid(app.current_doc.boxes[0])
        box1_uid = misora._get_box_uid(app.current_doc.boxes[1])
        self.assertIsNotNone(box0_uid)
        self.assertIsNotNone(box1_uid)

        # ---------------------------------------------------------------------
        # Part A: First edit EN1 -> Save -> Second edit EN2 -> Save
        # ---------------------------------------------------------------------
        with patch.object(misora.messagebox, "askyesno", return_value=True) as mock_ask:
            # 1st edit: EN1
            app.current_box_idx = 0
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "I am starving!")
            save_ok1 = app.on_save()
            self.assertTrue(save_ok1)

            # Check XUAT updated to EN1
            raw1 = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertIn("わたし、お腹が空きました！=I am starving!", raw1)

            # 2nd edit: EN2
            app.current_box_idx = 0
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "I want a huge feast now!")
            save_ok2 = app.on_save()
            self.assertTrue(save_ok2)

            # In unpatched code, self._original_box_texts[0] was overwritten with "I am starving!"
            # causing the 2nd save to search for "I am starving!=" in XUAT (which fails).
            # Patched code must still use the immutable JP key "わたし、お腹が空きました！".
            raw2 = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertIn(
                "わたし、お腹が空きました！=I want a huge feast now!",
                raw2,
                "Second save must still match original JP key, not EN1 from first save"
            )

        # ---------------------------------------------------------------------
        # Part B: Box insertion before target does not shift JP key
        # ---------------------------------------------------------------------
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            # Insert a new box at index 0
            app.current_doc.insert_box(0, {"kind": "print", "speaker": "NewSpeaker", "clean_text": "Inserted Box Text"})
            app._resync_box_indices_from_uids()

            # Now:
            # Box 0 is the newly inserted box
            # Box 1 is the original Box 0 (Pecorine)
            # Box 2 is the original Box 1 ("キャル、早く来て！")
            self.assertEqual(len(app.current_doc.boxes), 3)
            self.assertEqual(misora._get_box_uid(app.current_doc.boxes[2]), box1_uid)

            # Edit Box 2 (original Box 1)
            app.current_box_idx = 2
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "Kyaru, hurry up!")
            save_ok3 = app.on_save()
            self.assertTrue(save_ok3)

            # XUAT dictionary must update "キャル、早く来て！"
            raw3 = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertIn(
                "キャル、早く来て！=Kyaru, hurry up!",
                raw3,
                "Shifted box must match by b_uid, not shifted positional index"
            )

        # ---------------------------------------------------------------------
        # Part C: Conflict preview gate triggers prompt on conflict, skips when clean
        # ---------------------------------------------------------------------
        # Create a conflicting XUAT dictionary
        conflict_file = xuat_dir / "Conflict.txt"
        conflict_file.write_bytes(
            "キャル、早く来て！=Alternative Kyaru Translation\r\n".encode("utf-8")
        )

        with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_ask_conflict:
            # Edit Box 2 again
            app.current_box_idx = 2
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "Kyaru, please come quickly!")
            app.on_save()

            # In unpatched code, preview_matches() was never called, so askyesno was never invoked.
            # In patched code, askyesno MUST be called because "キャル、早く来て！" has 2 conflicting translations.
            self.assertTrue(
                mock_ask_conflict.called,
                "Conflicting XUAT entries must trigger conflict confirmation prompt"
            )
            # Since user clicked 'No' (return_value=False), XUAT files should NOT be updated with new text
            raw_no = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertNotIn("Kyaru, please come quickly!", raw_no)

        with patch.object(misora.messagebox, "askyesno", return_value=True) as mock_ask_conflict_yes:
            # User confirms overwrite
            app.current_box_idx = 2
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "Kyaru, please come quickly!")
            app.on_save()
            self.assertTrue(mock_ask_conflict_yes.called)
            raw_yes1 = xuat_file.read_bytes().decode("utf-8-sig")
            raw_yes2 = conflict_file.read_bytes().decode("utf-8")
            self.assertIn("キャル、早く来て！=Kyaru, please come quickly!", raw_yes1)
            self.assertIn("キャル、早く来て！=Kyaru, please come quickly!", raw_yes2)

        # Now test clean entry: Box 1 ("わたし、お腹が空きました！") has only 1 translation across dictionaries
        with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_ask_clean:
            app.current_box_idx = 1
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "I am completely full now!")
            app.on_save()
            # Clean match must NOT trigger modal conflict prompt (zero friction)
            self.assertFalse(
                mock_ask_clean.called,
                "Clean non-conflicting match must sync without modal prompt"
            )
            raw_clean = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertIn("わたし、お腹が空きました！=I am completely full now!", raw_clean)

        # ---------------------------------------------------------------------
        # Part D: Tab switching A -> B -> A preserves immutable JP keys & inactive save
        # ---------------------------------------------------------------------
        # Create doc B
        story_b = self.tmp_dir / "story_b.v2.txt"
        doc_b = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "主さま、お帰りなさいませ。"]),
        ])
        story_b.write_text(doc_b.to_v2_text(), encoding="utf-8")
        xuat_content_b = "主さま、お帰りなさいませ。=Welcome home, my Lord.\r\n"
        (xuat_dir / "Kokkoro.txt").write_bytes(xuat_content_b.encode("utf-8"))

        # Switch to doc B
        app.open_file(story_b)
        self.assertEqual(app.current_file_path, story_b)
        box_b_uid = misora._get_box_uid(app.current_doc.boxes[0])
        self.assertIsNotNone(box_b_uid)
        self.assertNotEqual(box_b_uid, box0_uid)

        # Edit doc B Box 0
        app.txt_dialogue.delete("1.0", "end")
        app.txt_dialogue.insert("1.0", "Welcome back, my Master.")
        # Mark dirty and modify
        app._modified_boxes.add(0)
        app._modified_box_uids.add(box_b_uid)

        # Switch back to doc A (cache-hit switch A -> B -> A)
        app.open_file(story_file)
        self.assertEqual(app.current_file_path, story_file)

        # Verify doc A's original JP keys remain 100% intact
        self.assertEqual(app._original_jp_by_uid.get(box0_uid), "わたし、お腹が空きました！")
        self.assertEqual(app.sync_manager.get_jp_key(box0_uid), "わたし、お腹が空きました！")

        # Edit Box 1 in doc A (original Box 0) again
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            app.current_box_idx = 1
            app.txt_dialogue.delete("1.0", "end")
            app.txt_dialogue.insert("1.0", "Pecorine is hungry once again!")
            app.on_save()
            raw_a_after = xuat_file.read_bytes().decode("utf-8-sig")
            self.assertIn("わたし、お腹が空きました！=Pecorine is hungry once again!", raw_a_after)

        # Inactive document save of doc B while doc A is still active
        with patch.object(misora.messagebox, "askyesno", return_value=True):
            save_b_ok = app._save_document_entry(story_b)
            self.assertTrue(save_b_ok)
            raw_b_after = (xuat_dir / "Kokkoro.txt").read_bytes().decode("utf-8")
            self.assertIn("主さま、お帰りなさいませ。=Welcome back, my Master.", raw_b_after)

    def test_probe_2_bug26_find_and_update_atomic_write_preserves_bom_and_crlf(self):
        """
        [Probe 2 — BUG-26]
        find_and_update() delegates to write_atomic_encoded() preserving UTF-8 BOM,
        CRLF/LF line endings, and bounded retry.
        """
        # Test file with UTF-8 BOM and CRLF
        xuat_file = self.tmp_dir / "AtomicTest.txt"
        original_bytes = (
            b"\xef\xbb\xbf"
            b"Line1_Key=Line1_Val\r\n"
            b"\xe3\x82\x86\xe3\x81\x84\xe3\x81\x95\xe3\x82\x93=Old Yui\r\n"
            b"Line3_Key=Line3_Val\r\n"
        )
        xuat_file.write_bytes(original_bytes)

        mgr = XUnitySyncManager()

        # In unpatched code, write_atomic_encoded is not imported or called in core.xunity_sync.
        # Patch write_atomic_encoded in core.xunity_sync: if missing, AttributeError will fail the probe.
        import core.xunity_sync as xsync
        self.assertTrue(
            hasattr(xsync, "write_atomic_encoded"),
            "core.xunity_sync must import and delegate to write_atomic_encoded"
        )

        with patch.object(xsync, "write_atomic_encoded", wraps=xsync.write_atomic_encoded) as spy_write:
            matches = mgr.find_and_update(
                japanese_key="ゆいさん",
                new_english_text="Dearest Yui",
                search_roots=[self.tmp_dir],
                backup=False,
            )
            self.assertEqual(len(matches), 1)
            self.assertTrue(spy_write.called, "find_and_update must call write_atomic_encoded")

            # Check spy call args: path, updated_text, encoding, has_bom, newline
            call_args = spy_write.call_args
            self.assertEqual(call_args[0][0], xuat_file)
            self.assertIn("ゆいさん=Dearest Yui", call_args[0][1])
            self.assertEqual(call_args[1].get("has_bom") or (call_args[0][3] if len(call_args[0]) > 3 else None), True)
            self.assertEqual(call_args[1].get("newline") or (call_args[0][4] if len(call_args[0]) > 4 else None), "\r\n")

        # Verify physical disk file output has BOM and CRLF
        disk_bytes = xuat_file.read_bytes()
        self.assertTrue(disk_bytes.startswith(b"\xef\xbb\xbf"), "Written file must retain UTF-8 BOM")
        self.assertIn(b"\r\n", disk_bytes, "Written file must retain CRLF line endings")
        self.assertNotIn(b"\r\r\n", disk_bytes, "Must not introduce double carriage returns")
        self.assertTrue(disk_bytes.endswith(b"\r\n"), "Must preserve trailing newline")

    # =========================================================================
    # Regression Guards (MUST PASS both before and after patch)
    # =========================================================================

    def test_guard_1_xuat_line_parsing_and_value_escaping(self):
        """[Guard 1] Verifies split_xuat_line and escape_xuat_value core contracts."""
        # Comments
        self.assertIsNone(split_xuat_line("# comment"))
        self.assertIsNone(split_xuat_line("// comment"))
        self.assertIsNone(split_xuat_line("; comment"))
        self.assertIsNone(split_xuat_line("r:regex"))
        self.assertIsNone(split_xuat_line("sr:regex"))
        self.assertIsNone(split_xuat_line(""))

        # Normal line
        res = split_xuat_line("Key = Value")
        self.assertEqual(res, ("Key ", " Value"))

        # Escaped equals sign
        res2 = split_xuat_line(r"Key\=WithEquals=ValuePart")
        self.assertEqual(res2, (r"Key\=WithEquals", "ValuePart"))

        # Leading whitespace in key is preserved
        res3 = split_xuat_line("  SpacedKey=Value")
        self.assertEqual(res3, ("  SpacedKey", "Value"))

        # Value newline escaping
        escaped = escape_xuat_value("Line 1\r\nLine 2\nLine 3\r")
        self.assertEqual(escaped, "Line 1\\nLine 2\\nLine 3\\n")

    def test_guard_2_sync_manager_registration_contracts(self):
        """[Guard 2] Verifies XUnitySyncManager registration and lookup behavior."""
        mgr = XUnitySyncManager()
        box_uid = 9999
        mgr.register_jp_key(box_uid, "オリジナル日本語")

        # Attempting to register another key for same UID is ignored (immutable)
        mgr.register_jp_key(box_uid, "上書き不可")
        self.assertEqual(mgr.get_jp_key(box_uid), "オリジナル日本語")

        # Untracked UID returns fallback
        self.assertEqual(mgr.get_jp_key(8888, fallback="Fallback"), "Fallback")


if __name__ == "__main__":
    unittest.main()
