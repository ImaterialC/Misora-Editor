"""
S8b-3 — Encoding Detection & Strict Fallback Architecture Tests
===============================================================
TDD tests verifying:
  - detect_encoding_and_decode deterministically detects UTF-8 BOM, UTF-16 LE/BE BOM,
    standard UTF-8, and Japanese CP932 / Windows-31J strictly.
  - Corrupt or arbitrary binary data raises UnicodeDecodeError without silent corruption.
  - encode_with_metadata strictly preserves BOM, encoding, and CRLF / LF line endings.
  - open_file() strips leading BOM so it never pollutes Box 0 or text buffers,
    while remembering has_bom and encoding for round-trip persistence.
  - on_replace_all() operates strictly on CP932 and UTF-8 BOM files without injecting \ufffd.
  - ProjectSearchEngine accurately matches Japanese text inside CP932 and UTF-16 files.
"""

import tempfile
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
import sys
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora
from core import (
    DecodedText,
    detect_encoding_and_decode,
    encode_with_metadata,
    read_text_file_strictly,
    write_atomic_encoded,
    ProjectSearchEngine,
    SearchOptions,
)


class S8b3TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s8b3_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warning = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_error = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warning.start()
        cls.patch_error.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warning.stop()
        cls.patch_error.stop()

    def setUp(self):
        with patch.object(misora, "CONFIG_PATH", self.config_path):
            self.app = misora.MisoraApp()
        self.app.withdraw()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass


class TestS8b3EncodingDetection(S8b3TestBase):
    """S8b-3 Encoding Detection & Strict Fallback Architecture Tests."""

    def test_01_detect_utf8_with_bom(self):
        """detect_encoding_and_decode strips UTF-8 BOM, records has_bom=True and utf-8 encoding."""
        raw = b"\xef\xbb\xbfHello world\r\nLine 2"
        res = detect_encoding_and_decode(raw)
        self.assertEqual(res.text, "Hello world\r\nLine 2")
        self.assertEqual(res.encoding, "utf-8")
        self.assertTrue(res.has_bom)
        self.assertEqual(res.newline, "\r\n")
        self.assertEqual(res.bom_bytes, b"\xef\xbb\xbf")

    def test_02_detect_utf8_without_bom(self):
        """detect_encoding_and_decode decodes clean UTF-8 text with has_bom=False."""
        raw = "こんにちは世界\nLine 2".encode("utf-8")
        res = detect_encoding_and_decode(raw)
        self.assertEqual(res.text, "こんにちは世界\nLine 2")
        self.assertEqual(res.encoding, "utf-8")
        self.assertFalse(res.has_bom)
        self.assertEqual(res.newline, "\n")
        self.assertEqual(res.bom_bytes, b"")

    def test_03_detect_utf16_le_and_be_bom(self):
        """detect_encoding_and_decode identifies UTF-16 Little-Endian and Big-Endian BOMs."""
        sample = "Priconne Story Text\r\n"

        # UTF-16 LE
        raw_le = sample.encode("utf-16-le")
        raw_le_with_bom = b"\xff\xfe" + raw_le
        res_le = detect_encoding_and_decode(raw_le_with_bom)
        self.assertEqual(res_le.text, sample)
        self.assertEqual(res_le.encoding, "utf-16-le")
        self.assertTrue(res_le.has_bom)
        self.assertEqual(res_le.bom_bytes, b"\xff\xfe")

        # UTF-16 BE
        raw_be = sample.encode("utf-16-be")
        raw_be_with_bom = b"\xfe\xff" + raw_be
        res_be = detect_encoding_and_decode(raw_be_with_bom)
        self.assertEqual(res_be.text, sample)
        self.assertEqual(res_be.encoding, "utf-16-be")
        self.assertTrue(res_be.has_bom)
        self.assertEqual(res_be.bom_bytes, b"\xfe\xff")

    def test_04_detect_cp932_japanese(self):
        """detect_encoding_and_decode falls back strictly to CP932 when non-UTF8 Japanese bytes occur."""
        # 'こんにちは' in CP932 is b'\x82\xb1\x82\xf1\x82\xc9\x82\xbf\x82\xcd', which is invalid UTF-8
        raw_cp932 = "ペコリーヌ=ヤバいですね☆\r\nキャル=ぶっ殺すわよ！".encode("cp932")
        res = detect_encoding_and_decode(raw_cp932)
        self.assertIn("ペコリーヌ=ヤバいですね☆", res.text)
        self.assertIn("キャル=ぶっ殺すわよ！", res.text)
        self.assertEqual(res.encoding, "cp932")
        self.assertFalse(res.has_bom)
        self.assertEqual(res.newline, "\r\n")

    def test_05_strict_decode_raises_on_corrupt_bytes(self):
        """detect_encoding_and_decode raises UnicodeDecodeError on invalid bytes; never errors='replace'."""
        # Incomplete / invalid bytes that fail both UTF-8 and CP932
        corrupt_bytes = b"\xff\xff\xff\x00\x01\x02\x80\x81"
        with self.assertRaises(UnicodeDecodeError):
            detect_encoding_and_decode(corrupt_bytes)

    def test_06_encode_with_metadata_preserves_bom_and_crlf(self):
        """encode_with_metadata round-trips encoding, BOM prefix, and CRLF / LF line endings."""
        text = "Line 1\nLine 2\nLine 3"

        # UTF-8 with BOM and CRLF
        encoded_crlf = encode_with_metadata(text, encoding="utf-8", has_bom=True, newline="\r\n")
        self.assertTrue(encoded_crlf.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"\r\n", encoded_crlf)
        self.assertNotIn(b"[^\r]\n", encoded_crlf)

        # CP932 with LF
        jp_text = "コッコロの笑顔\n"
        encoded_cp = encode_with_metadata(jp_text, encoding="cp932", has_bom=False, newline="\n")
        self.assertEqual(encoded_cp.decode("cp932"), "コッコロの笑顔\n")
        self.assertFalse(encoded_cp.startswith(b"\xef\xbb\xbf"))

    def test_07_open_file_strips_bom_and_remembers_encoding(self):
        """open_file() strips leading BOM so it never pollutes Box 0 or script, and stores metadata."""
        fpath = self.tmp_dir / "bom_script.txt"
        v2_content = (
            "#!priconne-story v2\r\n\r\n"
            "print#1\r\n"
            "Speaker\r\n"
            "Hello from BOM script\r\n"
            "Dialogue\r\n"
        )
        fpath.write_bytes(b"\xef\xbb\xbf" + v2_content.encode("utf-8"))

        self.app.open_file(fpath)
        self.assertIsNotNone(self.app.current_doc)
        self.assertEqual(len(self.app.current_doc.boxes), 1)

        # The clean text must NOT start with \ufeff
        box_text = self.app.current_doc.boxes[0].clean_text
        self.assertFalse(box_text.startswith("\ufeff"), "BOM character \\ufeff must not leak into dialogue text")
        self.assertEqual(box_text, "Hello from BOM script")

        # In-memory document entry must remember has_bom=True
        entry = self.app.open_documents[fpath.resolve()]
        self.assertTrue(entry.get("has_bom"), "open_documents must record has_bom=True")
        self.assertEqual(entry.get("encoding"), "utf-8")

    def test_08_replace_all_preserves_cp932_without_corrupting(self):
        """Multi-file Replace All on a CP932 Japanese file preserves encoding and does not inject \\ufffd."""
        fpath = self.tmp_dir / "cp932_dict.txt"
        original_cp932_text = "ペコリーヌ=おいしいごはん\r\n美食殿=最高\r\n"
        fpath.write_bytes(original_cp932_text.encode("cp932"))

        self.app.selected_search_folder = self.tmp_dir
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.scope_var.set("folder")
        self.app.var_inc_text.set(True)
        self.app.var_inc_bundles.set(False)
        self.app.search_var.set("おいしいごはん")
        self.app.replace_var.set("至福のごちそう")

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # Read back bytes directly
        res_bytes = fpath.read_bytes()
        self.assertNotIn("\ufffd".encode("utf-8"), res_bytes, "Must not contain replacement characters \\ufffd")

        # Decode strictly with CP932
        res_text = res_bytes.decode("cp932")
        self.assertIn("ペコリーヌ=至福のごちそう", res_text)
        self.assertIn("美食殿=最高", res_text)
        self.assertTrue(res_text.endswith("\r\n"))

    def test_09_replace_all_preserves_utf8_bom(self):
        """Multi-file Replace All on a UTF-8 BOM file preserves the leading BOM on disk."""
        fpath = self.tmp_dir / "utf8_bom_dict.txt"
        fpath.write_bytes(b"\xef\xbb\xbfKey1=OldValue\r\nKey2=SecondValue\r\n")

        self.app.selected_search_folder = self.tmp_dir
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.scope_var.set("folder")
        self.app.var_inc_text.set(True)
        self.app.var_inc_bundles.set(False)
        self.app.search_var.set("OldValue")
        self.app.replace_var.set("NewValue")

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        res_bytes = fpath.read_bytes()
        self.assertTrue(res_bytes.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM must be preserved on disk")
        res_text = res_bytes.decode("utf-8-sig")
        self.assertIn("Key1=NewValue", res_text)

    def test_10_search_engine_finds_cp932_matches(self):
        """ProjectSearchEngine successfully finds Japanese text inside CP932 encoded files."""
        fpath = self.tmp_dir / "cp932_story.txt"
        fpath.write_bytes("騎士君=いつもありがとう\r\nユウキ=どういたしまして\r\n".encode("cp932"))

        engine = ProjectSearchEngine()
        opts = SearchOptions(query="いつもありがとう", include_bundles=False)

        results = engine.search_file(fpath, opts)
        self.assertEqual(len(results), 1, "Search engine must match Japanese text in CP932 file")
        self.assertEqual(results[0].line_number, 1)
        self.assertIn("騎士君=いつもありがとう", results[0].full_text)


if __name__ == "__main__":
    unittest.main()
