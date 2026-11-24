"""
Unit tests for S03: Strict Binary Parse, Lossless v2 + \\b64:, Command Map/Breakers & Fixture-Gated Bundle Verify.
Canonical authority: Phase_2.5_Canonical_Ledger_LOCKED.md.
Scope: BUG-01, BUG-03, BUG-04, BUG-09.
"""

import base64
import hashlib
import os
import shutil
import struct
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import misora
from core.bundle_io import BundleIOError, save_bundle_story
from core.story_ast import (
    Record,
    StoryDocument,
    escape_arg,
    unescape_arg,
    _CMD_MAP,
    _INV_CMD_MAP,
)


class TestP3S03BinaryV2(unittest.TestCase):
    """Failing-first defect probes and regression guards for S03."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_path / "misora_config.json"
        self.root = None

    def tearDown(self):
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
        misora.CONFIG_PATH = self.orig_config_path
        self.tmp_dir.cleanup()

    # =========================================================================
    # DEFECT PROBES (MUST FAIL BEFORE PATCH, PASS AFTER PATCH)
    # =========================================================================

    def test_probe_1_bug01_strict_binary_parse_validation(self):
        """[Probe 1 — BUG-01] from_binary() raises ValueError on malformed/truncated input."""
        # a. Truncated command header (1 byte, expected 2)
        with self.assertRaises(ValueError, msg="Expected ValueError on 1-byte truncated header"):
            StoryDocument.from_binary(b"\x00")

        # b. Partial argument length header (2 bytes of command + 2 bytes of length, expected 4)
        partial_len = struct.pack(">H", 6) + b"\x00\x01"
        with self.assertRaises(ValueError, msg="Expected ValueError on partial arg length"):
            StoryDocument.from_binary(partial_len)

        # c. Argument payload overrun (declared length 10, but only 3 bytes payload)
        payload_overrun = struct.pack(">H", 6) + struct.pack(">I", 10) + b"abc"
        with self.assertRaises(ValueError, msg="Expected ValueError on payload overrun"):
            StoryDocument.from_binary(payload_overrun)

        # d. Missing length-0 terminating marker (valid command and arg, but EOF without length-0 marker)
        arg_bytes = b"hello"
        missing_term = struct.pack(">H", 6) + struct.pack(">I", len(arg_bytes)) + arg_bytes
        with self.assertRaises(ValueError, msg="Expected ValueError on missing length-0 terminator"):
            StoryDocument.from_binary(missing_term)

    def test_probe_2_bug03_cmd0_binary_serialization_not_remapped(self):
        """[Probe 2 — BUG-03] Record(cmd_id=0, cmd_name='title', args=['Ep1']) serializes with cmd_id == 0 (NOT 30)."""
        rec = Record(cmd_id=0, cmd_name="title", args=["Ep1"])
        doc = StoryDocument([rec])
        binary_data = doc.to_binary()

        self.assertGreaterEqual(len(binary_data), 2, "Binary output must contain at least 2-byte header")
        serialized_cid = struct.unpack_from(">H", binary_data, 0)[0]
        self.assertEqual(
            serialized_cid,
            0,
            f"cmd_id == 0 was remapped to {serialized_cid} (legacy cmd0 special case bug still active)"
        )

    def test_probe_3_bug03_lossless_v2_whitespace_categories_literal_b64(self):
        """[Probe 3 — BUG-03] binary -> v2 -> binary roundtrip preserves whitespace, categories, literal slashes, and b64."""
        surrogate_arg = b"\xff\xfe".decode("utf-8", "surrogateescape")
        recs = [
            # Whitespace-only argument
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", " "], category="System"),
            # Ideographic whitespace U+3000
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "\u3000"], category="System"),
            # Category name collision arguments
            Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Sound"], category="Other"),
            Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Other"], category="Effect"),
            # Literal backslash prefix arguments (must not strip category or turn \\s into space)
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", r"\Sound"], category="Foreground"),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", r"\s"], category="Background"),
            # Non-UTF-8 surrogate-escaped bytes
            Record(cmd_id=6, cmd_name="print", args=["Sheffy", surrogate_arg], category="System"),
            # Ambiguous headers: touch#10 vs touch#12 must emit explicit #id
            Record(cmd_id=10, cmd_name="touch", args=[], category="System"),
            Record(cmd_id=12, cmd_name="touch", args=["vo_1001"], category="System"),
        ]

        doc = StoryDocument(recs)
        v2_text = doc.to_v2_text()

        # Check v2 representation details
        self.assertIn(r"\s", v2_text, "Whitespace-only ' ' must escape to \\s")
        self.assertIn(r"\S", v2_text, "Ideographic whitespace must escape to \\S")
        self.assertIn(r"\Sound", v2_text, "Category collision 'Sound' must prefix with backslash \\Sound")
        self.assertIn(r"\\Sound", v2_text, "Literal '\\Sound' must escape to \\\\Sound")
        self.assertIn(r"\\s", v2_text, "Literal '\\s' must escape to \\\\s")
        self.assertIn(r"\b64:", v2_text, "Surrogateescape bytes must emit \\b64: prefix")
        self.assertIn("touch#10", v2_text, "Ambiguous touch (cmd 10) must emit explicit touch#10")
        self.assertIn("touch#12", v2_text, "Ambiguous touch (cmd 12) must emit explicit touch#12")

        # Roundtrip from v2
        doc_from_v2 = StoryDocument.from_v2_text(v2_text)
        self.assertEqual(len(doc_from_v2.records), len(recs), "Record count mismatch after v2 parse")

        # Verify exact round-trip argument restoration
        self.assertEqual(doc_from_v2.records[0].args[1], " ", "Whitespace-only ' ' was lost")
        self.assertEqual(doc_from_v2.records[1].args[1], "\u3000", "Ideographic whitespace U+3000 was lost")
        self.assertEqual(doc_from_v2.records[2].args[1], "Sound", "Category collision 'Sound' was misparsed")
        self.assertEqual(doc_from_v2.records[3].args[1], "Other", "Category collision 'Other' was misparsed")
        self.assertEqual(doc_from_v2.records[4].args[1], r"\Sound", "Literal '\\Sound' was corrupted")
        self.assertEqual(doc_from_v2.records[5].args[1], r"\s", "Literal '\\s' was corrupted")
        self.assertEqual(doc_from_v2.records[6].args[1], surrogate_arg, "Surrogateescape bytes were corrupted")
        self.assertEqual(doc_from_v2.records[7].cmd_id, 10, "touch#10 cmd_id was corrupted")
        self.assertEqual(doc_from_v2.records[8].cmd_id, 12, "touch#12 cmd_id was corrupted")

        # Roundtrip binary serialization byte-exact match
        b_orig = doc.to_binary()
        b_rt = doc_from_v2.to_binary()
        self.assertEqual(b_orig, b_rt, "Binary representation differed after v2 roundtrip")

    def test_probe_4_bug04_midscript_breakers_split_same_speaker_boxes(self):
        """[Probe 4 — BUG-04] Mid-script cmd_id in (0, 1, 4, 36) splits adjacent same-speaker boxes."""
        breaker_ids = [0, 1, 4, 36]  # 0=title, 1=outline, 4=type, 36=situation
        for bid in breaker_ids:
            recs = [
                Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Line 1"]),
                Record(cmd_id=bid, cmd_name=_CMD_MAP.get(bid, f"cmd_{bid}"), args=["param"]),
                Record(cmd_id=6, cmd_name="print", args=["Yuuki", "Line 2"]),
            ]
            doc = StoryDocument(recs)
            self.assertEqual(
                len(doc.boxes),
                2,
                f"cmd_id {bid} failed to split adjacent same-speaker boxes (got {len(doc.boxes)} box(es))"
            )

    def test_probe_5_bug09_synthetic_multi_object_non_target_verification(self):
        """[Probe 5 — BUG-09] save_bundle_story fails if non-target object is modified or dropped."""
        # Create a mock UnityPy environment and objects
        class MockTextAssetData:
            def __init__(self, name="storydata", script=b""):
                self.m_Name = name
                self.m_Script = script
            def save(self):
                pass

        class MockAssetObj:
            def __init__(self, path_id, type_name, data_bytes, name="asset", assets_file_name="archive"):
                self.path_id = path_id
                self.type = MagicMock()
                self.type.name = type_name
                self.raw_data = data_bytes
                self.assets_file = MagicMock()
                self.assets_file.name = assets_file_name
                self._data = MockTextAssetData(name=name, script=data_bytes)
            def read(self):
                return self._data
            def get_raw_data(self):
                return self.raw_data

        target_bytes = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["A", "B"])]).to_binary()
        target_obj = MockAssetObj(path_id=1, type_name="TextAsset", data_bytes=target_bytes, name="storydata_target")
        non_target_obj = MockAssetObj(path_id=2, type_name="MonoBehaviour", data_bytes=b"untouched_original_data", name="non_target")

        env = MagicMock()
        env.objects = [target_obj, non_target_obj]
        env.file.save.return_value = b"synthetic_bundle_bytes"

        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["A", "Modified"])])
        out_path = self.tmp_path / "bundle.unity3d"
        out_path.write_bytes(b"initial_bundle")

        # Scenario A: Non-target object modified during repack
        modified_non_target = MockAssetObj(path_id=2, type_name="MonoBehaviour", data_bytes=b"CORRUPTED_MODIFIED_DATA", name="non_target")
        check_env_modified = MagicMock()
        target_in_check = MockAssetObj(path_id=1, type_name="TextAsset", data_bytes=doc.to_binary(), name="storydata_target")
        check_env_modified.objects = [target_in_check, modified_non_target]

        with patch("core.bundle_io.get_unitypy") as mock_unitypy:
            mock_unitypy.return_value.load.return_value = check_env_modified
            with self.assertRaises(BundleIOError, msg="Expected BundleIOError when non-target object is modified"):
                save_bundle_story(env, target_obj, doc, out_path)

        # Scenario B: Non-target object dropped/missing after repack
        check_env_dropped = MagicMock()
        check_env_dropped.objects = [target_in_check]  # non_target missing!

        with patch("core.bundle_io.get_unitypy") as mock_unitypy:
            mock_unitypy.return_value.load.return_value = check_env_dropped
            with self.assertRaises(BundleIOError, msg="Expected BundleIOError when non-target object is dropped"):
                save_bundle_story(env, target_obj, doc, out_path)

        # Scenario C: Non-target object preserved identically -> success
        check_env_clean = MagicMock()
        preserved_non_target = MockAssetObj(path_id=2, type_name="MonoBehaviour", data_bytes=b"untouched_original_data", name="non_target")
        check_env_clean.objects = [target_in_check, preserved_non_target]

        with patch("core.bundle_io.get_unitypy") as mock_unitypy:
            mock_unitypy.return_value.load.return_value = check_env_clean
            save_bundle_story(env, target_obj, doc, out_path)
            self.assertTrue(out_path.is_file(), "Bundle file must be replaced upon verification success")

    def test_probe_6_bug03_raw_view_highlights_single_arg_title_cmd0(self):
        """[Probe 6 — BUG-03 / UI] _update_raw_view() highlights 1-arg cmd_id == 0 title record when Box 0 active."""
        self.root = tk.Tk()
        self.root.withdraw()

        # Minimal dummy container mimicking MisoraApp attributes used by _update_raw_view
        class DummyApp:
            pass

        app = DummyApp()
        app.txt_raw = tk.Text(self.root)
        app.is_box0_active = True
        app.current_box_idx = 0
        app.current_doc = StoryDocument([
            Record(cmd_id=0, cmd_name="title", args=["Episode 1: The Gourmet Guild"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Delicious!"]),
        ])

        # Call unbound _update_raw_view from MisoraApp
        misora.MisoraApp._update_raw_view(app)

        raw_text = app.txt_raw.get("1.0", tk.END)
        # Line 0 should be marked with active marker " >> [000]"
        self.assertIn(
            ">> [000] title",
            raw_text,
            "Box 0 active failed to highlight 1-arg cmd_id == 0 title record (line 6825 bug)"
        )

    # =========================================================================
    # REGRESSION GUARDS (MUST PASS BOTH BEFORE AND AFTER PATCH)
    # =========================================================================

    def test_guard_1_lead_ruling_a_commands_35_and_32_invariance(self):
        """[Guard 1 — Lead Ruling (a)] cmd_id 35 (narration) and 32 (subtitle) retain numeric IDs."""
        recs = [
            Record(cmd_id=35, cmd_name="tag", args=["Narration line"]),
            Record(cmd_id=32, cmd_name="cmd_32", args=["Subtitle line"]),
        ]
        doc = StoryDocument(recs)

        # 1. Binary roundtrip
        b = doc.to_binary()
        doc_bin = StoryDocument.from_binary(b)
        self.assertEqual(doc_bin.records[0].cmd_id, 35)
        self.assertEqual(doc_bin.records[1].cmd_id, 32)

        # 2. V2 text roundtrip
        v2 = doc.to_v2_text()
        doc_v2 = StoryDocument.from_v2_text(v2)
        self.assertEqual(doc_v2.records[0].cmd_id, 35)
        self.assertEqual(doc_v2.records[1].cmd_id, 32)

    def test_guard_2_tap_breaker_and_voice_cue_and_dialogue_projection(self):
        """[Guard 2] cmd_id == 10 tap-breaker splits boxes, cmd_id == 12 voice cue attaches voice, cmd 6 projects cleanly."""
        recs = [
            Record(cmd_id=12, cmd_name="touch", args=["vo_adv_1001001"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello world!"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Welcome!"]),
        ]
        doc = StoryDocument(recs)
        self.assertEqual(len(doc.boxes), 2, "Expected 2 boxes (cmd 10 split, cmd 12 voice attached)")
        self.assertEqual(doc.boxes[0].speaker, "Pecorine")
        self.assertEqual(doc.boxes[0].voice_cue, "vo_adv_1001001")
        self.assertEqual(doc.boxes[1].speaker, "Kokkoro")
        self.assertEqual(doc.boxes[1].voice_cue, "")

    def test_guard_3_existing_core_suite_and_empty_arg_sentinel_intact(self):
        """[Guard 3] Empty string argument in to_binary preserves arity via single-space sentinel (DEF-01)."""
        rec = Record(cmd_id=6, cmd_name="print", args=["Pecorine", ""])
        doc = StoryDocument([rec])
        b = doc.to_binary()
        # Binary ADV terminator is 0-length arg, so empty text MUST be serialized as ' '
        doc_restored = StoryDocument.from_binary(b)
        self.assertEqual(len(doc_restored.records[0].args), 2)
        self.assertEqual(doc_restored.records[0].args[1], " ")


if __name__ == "__main__":
    unittest.main()
