#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora/tests/test_misora_core.py - Unit test suite for Misora's core engine.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))
if str(MISORA_DIR.parent) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR.parent))

try:
    from misora.core import (
        StoryDocument, Box, BoxSnapshot, Record,
        game_to_xuat, xuat_to_game, norm_search,
        load_bundle_story, save_bundle_story, BundleIOError,
        ProjectSearchEngine, SearchOptions,
        XUnitySyncManager,
        MasterUndoJournal, UndoOperation, BoxEditDelta, BoxStructuralDelta, PlainTextDelta, BulkFileDelta,
        TagMasker, MTLConfig, MTLEngine,
    )
except ImportError:
    from core import (
        StoryDocument, Box, BoxSnapshot, Record,
        game_to_xuat, xuat_to_game, norm_search,
        load_bundle_story, save_bundle_story, BundleIOError,
        ProjectSearchEngine, SearchOptions,
        XUnitySyncManager,
        MasterUndoJournal, UndoOperation, BoxEditDelta, BoxStructuralDelta, PlainTextDelta, BulkFileDelta,
        TagMasker, MTLConfig, MTLEngine,
    )


class TestMisoraCore(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_story_document_creation_and_boxes(self):
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "I'm hungry!\\nLet's eat!"]),
            Record(cmd_id=10, cmd_name="touch", args=["vo_adv_1058001"]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", "Not again... {0}!"]),
        ]
        doc = StoryDocument(recs)
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].speaker, "Pecorine")
        self.assertEqual(doc.boxes[1].speaker, "Kyaru")
        # Check {0} -> {playername} in clean_text
        self.assertIn("{playername}", doc.boxes[1].clean_text)

    def test_02_inject_box_converts_playername_to_zero(self):
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Original text"]),
        ]
        doc = StoryDocument(recs)
        doc.inject_box(0, new_speaker="Hiyori", new_text="Hello, {playername}!")
        # Internal record must have converted {playername} -> {0}
        self.assertEqual(doc.records[0].args[1], "Hello, {0}!")

    def test_03_binary_roundtrip(self):
        recs = [
            Record(cmd_id=0, cmd_name="fade", args=["0"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Yabai desu ne!☆"]),
        ]
        doc = StoryDocument(recs)
        binary_bytes = doc.to_binary()
        doc_restored = StoryDocument.from_binary(binary_bytes)
        self.assertEqual(len(doc_restored.records), len(doc.records))
        self.assertEqual(doc_restored.records[1].args[0], "Pecorine")
        self.assertEqual(doc_restored.records[1].args[1], "Yabai desu ne!☆")

    def test_04_search_engine_whitespace_and_regex(self):
        sample_txt = self.tmp_dir / "sample_tl.txt"
        sample_txt.write_text(
            "そ、それもそうね……\\nあけましておめでとう{playername}！\\nよろしく！=Happy New Year!\n",
            encoding="utf-8"
        )
        engine = ProjectSearchEngine()

        # Whitespace-insensitive search
        opts = SearchOptions(
            query="あけましておめでとう{0}！",
            ignore_whitespace=True,
            include_text=True,
            include_bundles=False
        )
        results = engine.search_file(sample_txt, opts)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertGreaterEqual(res.snippet_start, 0)
        self.assertGreater(res.snippet_end, res.snippet_start)
        self.assertIn("あけましておめでとう", res.match_snippet)

        # Regex search
        opts_rx = SearchOptions(
            query=r"Happy\s+New\s+Year",
            use_regex=True,
            include_text=True,
            include_bundles=False
        )
        results_rx = engine.search_file(sample_txt, opts_rx)
        self.assertEqual(len(results_rx), 1)
        res_rx = results_rx[0]
        self.assertGreaterEqual(res_rx.snippet_start, 0)
        self.assertGreater(res_rx.snippet_end, res_rx.snippet_start)

    def test_05_xunity_sync_update(self):
        dict_file = self.tmp_dir / "Events.txt"
        dict_file.write_text(
            "Key1=Old Translation\n"
            "キャルちゃん、{playername}くん！=Old Translation With Typo\n",
            encoding="utf-8"
        )
        mgr = XUnitySyncManager()
        matches = mgr.find_and_update(
            japanese_key="キャルちゃん、{0}くん！",
            new_english_text="Fixed Translation",
            search_roots=[self.tmp_dir],
            backup=False
        )
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].success)

        # Verify content on disk
        updated_content = dict_file.read_text(encoding="utf-8")
        self.assertIn("Fixed Translation", updated_content)
        self.assertNotIn("Old Translation With Typo", updated_content)

    def test_06_undo_journal_coalescing(self):
        """MasterUndoJournal coalesces consecutive BoxEditDelta for same box."""
        journal = MasterUndoJournal()
        d1 = BoxEditDelta(box_index=0, old_speaker="A", new_speaker="A", old_text="old", new_text="v1", file_path="f.unity3d")
        d2 = BoxEditDelta(box_index=0, old_speaker="A", new_speaker="A", old_text="old", new_text="v2", file_path="f.unity3d")
        journal.record(d1, "Edit box #0")
        journal.record(d2, "Edit box #0")
        # Should coalesce -> still 1 op
        self.assertEqual(journal.undo_depth, 1)
        op = journal.pop_undo()
        self.assertIsNotNone(op)
        self.assertEqual(op.deltas[0].new_text, "v2")
        # After undo, redo stack should have 1 entry
        self.assertEqual(journal.redo_depth, 1)

    def test_07_undo_journal_batch(self):
        """MasterUndoJournal batch groups multiple deltas into one op."""
        journal = MasterUndoJournal()
        journal.begin_batch("Replace All")
        for i in range(3):
            journal.record(BoxEditDelta(box_index=i, old_speaker="X", new_speaker="X", old_text="old", new_text="new", file_path="f.unity3d"))
        journal.end_batch()
        self.assertEqual(journal.undo_depth, 1)
        op = journal.pop_undo()
        self.assertIsNotNone(op)
        self.assertEqual(len(op.deltas), 3)
        self.assertEqual(op.label, "Replace All")

    def test_08_tag_masker_roundtrip(self):
        """TagMasker shields NGUI tags and {playername} during machine translation."""
        complex_text = "[b]やあ、{playername}！[/b]\\n[rub:ルビ]漢字[/rub]と[c][ff0000]色[/c][-]だよ。"
        masked, tag_map = TagMasker.mask(complex_text)
        self.assertNotIn("{playername}", masked)
        self.assertNotIn("[rub:ルビ]", masked)
        self.assertIn("__M_", masked)
        unmasked = TagMasker.unmask(masked, tag_map)
        self.assertEqual(unmasked, complex_text)

    def test_09_mtl_config_serialization(self):
        """MTLConfig serializes to and from dict cleanly."""
        cfg = MTLConfig(
            active_engine="DeepL",
            src_lang="ja",
            tgt_lang="en",
            deepl_api_key="test_key_123",
            deepl_use_pro=True,
            timeout_sec=15.0
        )
        data = cfg.to_dict()
        self.assertEqual(data["active_engine"], "DeepL")
        self.assertEqual(data["deepl_api_key"], "test_key_123")
        restored = MTLConfig.from_dict(data)
        self.assertEqual(restored.active_engine, "DeepL")
        self.assertEqual(restored.deepl_use_pro, True)
        self.assertEqual(restored.timeout_sec, 15.0)
        self.assertEqual(restored.ai_prompt_include_header, True)
        self.assertEqual(restored.ai_prompt_include_speaker, True)

    def test_10_delimiter_parsing_and_excess_protection(self):
        """Cross-box delimiter parsing correctly groups dialogue and handles speakers."""
        sample_clip = (
            "=== [BOX:0|Speaker:コッコロ] ===\n"
            "主さま、朝でございますよ。\n\n"
            "=== [BOX:1|Speaker:ユウキ] ===\n"
            "おはよう、コッコロ。\n\n"
            "[BOX:2]\n"
            "今日も良い天気ですね。"
        )
        pattern = re.compile(
            r"(?:=== )?\[BOX:(\d+)(?:\|Speaker:([^\]]*))?\]\s*(?:===)?\s*\n(.*?)(?=\n(?:=== )?\[BOX:|\Z)",
            re.DOTALL
        )
        matches = list(pattern.finditer(sample_clip))
        self.assertEqual(len(matches), 3)
        self.assertEqual(matches[0].group(1), "0")
        self.assertEqual(matches[0].group(2), "コッコロ")
        self.assertEqual(matches[0].group(3).strip(), "主さま、朝でございますよ。")
        self.assertEqual(matches[1].group(1), "1")
        self.assertEqual(matches[1].group(2), "ユウキ")
        self.assertEqual(matches[2].group(1), "2")
        self.assertIsNone(matches[2].group(2))
        self.assertEqual(matches[2].group(3).strip(), "今日も良い天気ですね。")


    def test_11_session_preferences_and_paths(self):
        """Verify session paths and recent files schema serialization."""
        import json
        config_data = {
            "config_version": 4,
            "last_opened_dir": str(self.tmp_dir),
            "selected_search_folder": str(self.tmp_dir / "stories"),
            "saved_opened_files": [
                str(self.tmp_dir / "story_101.unity3d"),
                str(self.tmp_dir / "story_102.unity3d"),
            ],
            "saved_active_file": str(self.tmp_dir / "story_101.unity3d"),
            "recent_files": [
                str(self.tmp_dir / "story_101.unity3d"),
            ],
        }
        encoded = json.dumps(config_data)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["config_version"], 4)
        self.assertEqual(decoded["last_opened_dir"], str(self.tmp_dir))
        self.assertEqual(len(decoded["saved_opened_files"]), 2)
        self.assertEqual(decoded["saved_active_file"], str(self.tmp_dir / "story_101.unity3d"))

    def test_12_metadata_insertion_then_dialogue_edit_writes_correct_record(self):
        """AST-INDEX-SHIFT regression: set_metadata inserts records, dialogue edit writes correct record."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Initial line 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", "Initial line 2"]),
        ]
        doc = StoryDocument(recs)
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].clean_text, "Initial line 1")

        # Insert metadata at index 0/1
        doc.set_metadata(title="Episode 1", summary="A synopsis of episode 1")

        # Edit Box 0 (Pecorine)
        doc.inject_box(0, new_speaker="Pecorine", new_text="Edited line 1")

        meta = doc.get_metadata()
        self.assertEqual(meta["title"], "Episode 1")
        self.assertEqual(meta["summary"], "A synopsis of episode 1")
        self.assertEqual(doc.boxes[0].clean_text, "Edited line 1")
        self.assertEqual(doc.boxes[1].clean_text, "Initial line 2")

        pecorine_rec = doc.boxes[0].segs[0].record
        self.assertEqual(pecorine_rec.cmd_name, "print")
        self.assertEqual(pecorine_rec.args[1], "Edited line 1")

    def test_13_structural_insert_delete_move_clone_binary_roundtrip(self):
        """Structural APIs (insert, delete, move, clone) round-trip through binary serialization."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Box 1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Box 2"]),
        ]
        doc = StoryDocument(recs)
        self.assertEqual(len(doc.boxes), 2)

        # 1. Insert box
        snap_new = BoxSnapshot(speaker="Pecorine", voice_cue="", kind="print", seg_texts=["Inserted Box"])
        doc.insert_box(1, snap_new)
        self.assertEqual(len(doc.boxes), 3)
        self.assertEqual(doc.boxes[1].speaker, "Pecorine")
        self.assertEqual(doc.boxes[1].clean_text, "Inserted Box")

        # Roundtrip binary
        b1 = doc.to_binary()
        doc2 = StoryDocument.from_binary(b1)
        self.assertEqual(len(doc2.boxes), 3)
        self.assertEqual(doc2.boxes[1].clean_text, "Inserted Box")

        # 2. Clone box
        doc2.clone_boxes([1], target_index=1)
        self.assertEqual(len(doc2.boxes), 4)
        self.assertEqual(doc2.boxes[2].clean_text, "Inserted Box")

        # 3. Move box
        doc2.move_box(0, 3)
        self.assertEqual(doc2.boxes[-1].speaker, "Kokkoro")

        # 4. Delete box
        deleted = doc2.delete_boxes([1])
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0].clean_text, "Inserted Box")
        self.assertEqual(len(doc2.boxes), 3)

        # Final binary roundtrip check
        final_bytes = doc2.to_binary()
        doc_final = StoryDocument.from_binary(final_bytes)
        self.assertEqual(len(doc_final.boxes), 3)

    def test_14_multisegment_clone_preserves_segment_count(self):
        """Multi-segment clone preserves segment count and structure via BoxSnapshot."""
        r1 = Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Part 1 "])
        r2 = Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Part 2\\n"])
        r3 = Record(cmd_id=6, cmd_name="print", args=["Hiyori", "Part 3"])
        doc = StoryDocument([r1, r2, r3])
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(len(doc.boxes[0].segs), 3)

        # Clone the multi-segment box
        cloned = doc.clone_boxes([0], target_index=0)
        self.assertEqual(len(cloned), 1)
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(len(doc.boxes[1].segs), 3)
        self.assertEqual(doc.boxes[1].segs[0].text, "Part 1 ")
        self.assertEqual(doc.boxes[1].segs[1].text, "Part 2\\n")
        self.assertEqual(doc.boxes[1].segs[2].text, "Part 3")

    def test_15_empty_text_and_narration_preserve_arity_and_no_phantom(self):
        """Empty text and narration preserve arity in binary and create no phantom boxes."""
        r_narr = Record(cmd_id=35, cmd_name="tag", args=["This is narration."])
        r_empty_tx = Record(cmd_id=6, cmd_name="print", args=["Pecorine", ""])
        r_corrupt_tag = Record(cmd_id=35, cmd_name="tag", args=[])

        doc = StoryDocument([r_narr, Record(cmd_id=10, cmd_name="touch", args=[]), r_empty_tx, r_corrupt_tag])
        self.assertEqual(len(doc.boxes), 2)
        self.assertEqual(doc.boxes[0].kind, "tag")
        self.assertEqual(doc.boxes[0].speaker, "")
        self.assertEqual(doc.boxes[0].clean_text, "This is narration.")

        raw = doc.to_binary()
        doc_reloaded = StoryDocument.from_binary(raw)
        self.assertEqual(len(doc_reloaded.boxes), 2)
        self.assertEqual(doc_reloaded.boxes[0].kind, "tag")
        self.assertEqual(doc_reloaded.boxes[0].clean_text, "This is narration.")
        print_rec = doc_reloaded.records[2]
        self.assertEqual(print_rec.cmd_name, "print")
        self.assertEqual(len(print_rec.args), 2)
        self.assertEqual(print_rec.args[0], "Pecorine")

    def test_16_v2_roundtrip_lossless(self):
        """V2 text roundtrip preserves cmd_32, categories, unknown command IDs, and whitespace."""
        recs = [
            Record(cmd_id=32, cmd_name="cmd_32", args=["Subtitle Text"], category="Foreground"),
            Record(cmd_id=999, cmd_name="unknown_999", args=["  spaced  ", "\t\ttabs\t\t"], category="Effect"),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Line 1\nLine 2\u2028Line 3"], category="System"),
        ]
        doc = StoryDocument(recs)
        v2_text = doc.to_v2_text()
        doc_restored = StoryDocument.from_v2_text(v2_text)

        self.assertEqual(len(doc_restored.records), 3)
        r0 = doc_restored.records[0]
        self.assertEqual(r0.cmd_id, 32)
        self.assertEqual(r0.category, "Foreground")
        self.assertEqual(r0.args[0], "Subtitle Text")

        r1 = doc_restored.records[1]
        self.assertEqual(r1.cmd_id, 999)
        self.assertEqual(r1.category, "Effect")
        self.assertEqual(r1.args[0], "  spaced  ")
        self.assertEqual(r1.args[1], "\t\ttabs\t\t")

        r2 = doc_restored.records[2]
        self.assertEqual(r2.category, "System")
        self.assertEqual(r2.args[1], "Line 1\nLine 2\u2028Line 3")

    def test_17_unmodified_fixture_bundle_save_byte_exact(self):
        """Unmodified fixture load->save preserves 100% byte-exact story data."""
        fixture_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not fixture_path.exists():
            fixture_path = MISORA_DIR / "1001005.unity3d"
        if not fixture_path.exists():
            self.skipTest("No .unity3d fixture available")

        temp_bundle = self.tmp_dir / "test_roundtrip.unity3d"
        shutil.copy2(fixture_path, temp_bundle)

        doc, env, obj, name = load_bundle_story(temp_bundle)
        from core.bundle_io import extract_raw_story_bytes
        orig_story_bytes = extract_raw_story_bytes(obj)

        # 1. AST binary serialization must be 100% byte-exact with original fixture asset
        serialized_story_bytes = doc.to_binary()
        self.assertEqual(
            serialized_story_bytes,
            orig_story_bytes,
            "Unmodified story AST to_binary() must produce 100% byte-identical story bytes"
        )

        # 2. Save back through bundle repacker
        save_bundle_story(env, obj, doc, temp_bundle)

        # 3. Reload bundle and verify story TextAsset inside repacked bundle is 100% byte-exact
        doc_reloaded, env_reloaded, obj_reloaded, name_reloaded = load_bundle_story(temp_bundle)
        reloaded_story_bytes = extract_raw_story_bytes(obj_reloaded)
        self.assertEqual(
            reloaded_story_bytes,
            orig_story_bytes,
            "Story TextAsset inside repacked bundle must be 100% byte-exact with original"
        )

    def test_18_forced_verification_failure_leaves_original_unchanged(self):
        """Forced verification failure leaves original bundle completely untouched."""
        fixture_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not fixture_path.exists():
            fixture_path = MISORA_DIR / "1001005.unity3d"
        if not fixture_path.exists():
            self.skipTest("No .unity3d fixture available")

        temp_bundle = self.tmp_dir / "test_atomic_fail.unity3d"
        shutil.copy2(fixture_path, temp_bundle)
        orig_bytes = temp_bundle.read_bytes()

        doc, env, obj, name = load_bundle_story(temp_bundle)
        doc.inject_box(0, "TestSpeaker", "Modified text that should fail")

        from unittest.mock import patch
        with patch("core.bundle_io.extract_raw_story_bytes", return_value=b"corrupted_garbage_bytes"):
            with self.assertRaises(BundleIOError):
                save_bundle_story(env, obj, doc, temp_bundle)

        current_bytes = temp_bundle.read_bytes()
        self.assertEqual(current_bytes, orig_bytes, "Failed verification must leave original bundle completely unchanged")

    def test_19_multiline_xuat_sync_stays_one_physical_line(self):
        """Multiline XUAT sync stays one physical dictionary line and preserves BOM/CRLF."""
        xuat_file = self.tmp_dir / "Dialogue_sync.txt"
        content = "\ufeffKey1=Old Value 1\r\nペコリーヌ、{0}！=Old Translation\r\nKey3=Old Value 3\r\n"
        xuat_file.write_text(content, encoding="utf-8")

        mgr = XUnitySyncManager()
        multiline_en = "Line 1 of English\nLine 2 of English\r\nLine 3 of English"
        matches = mgr.find_and_update(
            japanese_key="ペコリーヌ、{playername}！",
            new_english_text=multiline_en,
            search_roots=[self.tmp_dir],
            backup=False
        )
        self.assertEqual(len(matches), 1)

        raw_result = xuat_file.read_bytes()
        self.assertTrue(raw_result.startswith(b"\xef\xbb\xbf"))

        text_result = raw_result[3:].decode("utf-8")
        lines = text_result.split("\r\n")
        non_empty_lines = [l for l in lines if l.strip()]
        self.assertEqual(len(non_empty_lines), 3)

        updated_line = non_empty_lines[1]
        self.assertTrue(updated_line.startswith("ペコリーヌ、{0}！="))
        self.assertIn("\\n", updated_line)
        self.assertNotIn("\n", updated_line)
        self.assertEqual(
            updated_line,
            "ペコリーヌ、{0}！=Line 1 of English\\nLine 2 of English\\nLine 3 of English"
        )

    def test_20_second_save_of_same_box_still_syncs_with_immutable_jp_key(self):
        """Second save of the same box still syncs using immutable Japanese key cache."""
        mgr = XUnitySyncManager()
        box_uid = 1042
        jp_orig = "わたし、お腹が空きました！"
        mgr.register_jp_key(box_uid, jp_orig)

        en_second = "I am completely starving!"
        resolved_key = mgr.get_jp_key(box_uid, fallback=en_second)
        self.assertEqual(resolved_key, jp_orig)


if __name__ == "__main__":
    unittest.main()
