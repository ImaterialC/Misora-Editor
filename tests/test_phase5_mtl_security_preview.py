"""Phase 5 Automated Verification Suite: Shared NGUI, MTL Engine, Security, and Preview Safety.

Part of Misora Editor test suite (Rules 17, 18, 19, 20 D8, D13).
"""

import sys
import os
import ssl
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import core.ngui_tags as ngui_tags
from core.ngui_tags import (
    strip_tags,
    get_rendered_length,
    measure_line_lengths,
    normalize_gradient_syntax,
    TagMasker,
    NGUI_TAG_RE,
    NGUI_TOKEN_RE,
)
import core.security as security
from core.security import protect_secret, unprotect_secret, redact_secret
from core.mtl_engine import MTLConfig, MTLEngine
from core.story_ast import StoryDocument, Record
from core.script_codec import parse
import misora


class TestPhase5MTLSecurityPreview(unittest.TestCase):
    """Automated tests for Phase 5 deliverables."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_p5_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        # Mock out messageboxes
        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warn.start()
        cls.patch_err.start()

        with patch.object(misora, "CONFIG_PATH", cls.config_path):
            cls.app = misora.MisoraApp(restore_session=False, show_splash=False)
            cls.app._test_bypass_dialogs = True
            cls.app.withdraw()
            cls.app.backup_folder = str(cls.tmp_dir / "backups")

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warn.stop()
        cls.patch_err.stop()

        try:
            cls.app.destroy()
        except Exception:
            pass
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _create_sample_doc(self) -> StoryDocument:
        """Create a mock 4-box StoryDocument with metadata."""
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Sample Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Sample Summary"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello [b]Yuuki[/b]! Welcome to [ff5500]Landosol[/]!"]),
            Record(cmd_id=7, cmd_name="tag", args=["The wind blows gently through the fields."]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Master {playername}, breakfast is ready!"]),
            Record(cmd_id=6, cmd_name="print", args=["Karyl", "Hmph, don't get the wrong idea! [rub:ばか]Idiot[/rub]!"]),
        ]
        return StoryDocument(recs)

    def test_01_ngui_tags_central_and_tagmasker(self):
        """Central NGUI definitions, gradient normalization, and TagMasker shielding (Rule 19 / TAGMASKER-INCOMPLETE)."""
        # 1. Gradient normalization (comma -> hyphen syntax)
        self.assertEqual(normalize_gradient_syntax("[ff0000,00ff00]Text[/]"), "[ff0000-00ff00]Text[/]")
        self.assertEqual(normalize_gradient_syntax("[aabbcc-ddeeff]Already Hyphen[/]"), "[aabbcc-ddeeff]Already Hyphen[/]")

        # 2. strip_tags & rendered character length
        text_with_tags = "[b]Bold[/b] [i]Italic[/i] [size=24]Large[/size] [ff8800]Orange[/] [rub:ルビ]Ruby[/rub]"
        plain = strip_tags(text_with_tags)
        self.assertNotIn("[b]", plain)
        self.assertNotIn("[size=24]", plain)
        self.assertEqual(plain, "Bold Italic Large Orange Ruby")

        rendered_len = get_rendered_length(text_with_tags)
        self.assertEqual(rendered_len, len("Bold Italic Large Orange Ruby"))

        # Placeholders stripping
        self.assertEqual(strip_tags("Hello {playername}! Box {0}"), "Hello ! Box ")

        # 3. Multiline ruby matching with re.DOTALL
        multiline_ruby = "[rub:かん\nじ]Kan\nji[/rub]"
        self.assertEqual(strip_tags(multiline_ruby), "Kan\nji")

        # 4. TagMasker full shielding and unshielding
        masker = TagMasker()
        input_text = "Good morning {playername}! [b]Special[/b] [size=20]Offer[/size] for [ff0000-00ff00]You[/]! [rub:ふりがな]Word[/rub] {1}"
        masked, tag_map = masker.mask(input_text)

        # Tags should be replaced by placeholders (__M_0__, etc.)
        self.assertNotIn("{playername}", masked)
        self.assertNotIn("[b]", masked)
        self.assertNotIn("[ff0000-00ff00]", masked)
        self.assertIn("__M_", masked)

        # Simulate translation that keeps __M_X__ tokens
        translated_sim = masked.replace("Good morning", "Selamat pagi").replace("Offer", "Penawaran")
        unmasked = masker.unmask(translated_sim, tag_map)

        self.assertIn("{playername}", unmasked)
        self.assertIn("[b]", unmasked)
        self.assertIn("[ff0000-00ff00]", unmasked)
        self.assertIn("[rub:ふりがな]Word[/rub]", unmasked)
        self.assertIn("{1}", unmasked)
        self.assertIn("Selamat pagi", unmasked)
        self.assertIn("Penawaran", unmasked)

    def test_02_security_dpapi_and_redaction(self):
        """Windows DPAPI credential encryption, unprotect, and secret redaction (Rules 17 & 18)."""
        raw_key = "sk-antigravity-deepmind-secret-key-12345"

        # 1. Protect & Unprotect roundtrip
        encrypted = protect_secret(raw_key)
        self.assertNotEqual(encrypted, raw_key)
        self.assertTrue(encrypted.startswith("dpapi:") or encrypted.startswith("b64:"))

        decrypted = unprotect_secret(encrypted)
        self.assertEqual(decrypted, raw_key)

        # 2. Secret Redaction
        redacted = redact_secret(raw_key)
        self.assertNotIn("deepmind-secret-key", redacted)
        self.assertTrue(redacted.startswith("sk-") or redacted == "****")
        self.assertTrue(redacted.endswith("2345") or redacted == "****")

        # 3. MTLConfig DPAPI serialization
        cfg = MTLConfig(deepl_api_key="deepl-secret-key-9999", llm_api_key="openai-secret-key-8888")
        unsecured_dict = cfg.to_dict(secure=False)
        self.assertEqual(unsecured_dict["deepl_api_key"], "deepl-secret-key-9999")

        secured_dict = cfg.to_dict(secure=True)
        self.assertNotEqual(secured_dict["deepl_api_key"], "deepl-secret-key-9999")
        self.assertTrue(secured_dict["deepl_api_key"].startswith("dpapi:") or secured_dict["deepl_api_key"].startswith("b64:"))

        # Restoring from secured dict decrypts in memory
        restored = MTLConfig.from_dict(secured_dict)
        self.assertEqual(restored.deepl_api_key, "deepl-secret-key-9999")
        self.assertEqual(restored.llm_api_key, "openai-secret-key-8888")

    def test_03_tls_verification_enforced(self):
        """Outbound HTTPS requests enforce valid TLS certificate and hostname verification (Rule 18)."""
        engine = MTLEngine()
        ssl_ctx = engine._ssl_ctx

        # Verify SSL verification is NOT disabled
        self.assertNotEqual(ssl_ctx.verify_mode, ssl.CERT_NONE)
        self.assertTrue(ssl_ctx.check_hostname)

    def test_04_deepl_usage_connection_test(self):
        """DeepL connection test queries free /v2/usage endpoint without consuming billable characters (Rule 18 / DEEPL-TEST-COST)."""
        cfg = MTLConfig(active_engine="DeepL", deepl_api_key="dummy-deepl-key")
        engine = MTLEngine(cfg)

        with patch("core.mtl_engine.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"character_count": 1200, "character_limit": 500000}).encode("utf-8")
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            ok, msg = engine.test_connection(cfg)

            # Assert urlopen was called with /v2/usage
            self.assertTrue(ok, f"Expected success but got: {msg}")
            self.assertIn("1,200", msg)
            called_req = mock_urlopen.call_args[0][0]
            self.assertIn("/v2/usage", called_req.full_url)
            self.assertNotIn("/v2/translate", called_req.full_url)

    def test_05_translation_lock_operations(self):
        """Translation Lock (Ctrl+L) protects boxes from batch translation, script paste, and replace all (Rule 20 D8)."""
        doc = self._create_sample_doc()
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "lock_test.unity3d"
        self.app.current_box_idx = 1  # Box 2 (wind blows narration)
        self.app._locked_boxes.clear()
        self.app._update_views()

        # 1. Lock Box 2
        self.assertFalse(self.app.is_box_locked(1))
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))
        self.assertEqual(self.app.btn_lock_box.cget("text"), "🔒")

        # 2. on_translate_current_box on locked box must be blocked
        orig_text = doc.boxes[1].clean_text
        with patch.object(self.app, "show_toast") as mock_toast:
            self.app.on_translate_current_box()
            mock_toast.assert_called_with("🔒 Box 2 is locked against translation edits.")
        self.assertEqual(doc.boxes[1].clean_text, orig_text)

        # 3. Replace All must skip locked box and report preserved count
        self.app.search_var.set("the")
        self.app.replace_var.set("A")
        self.app.scope_var.set("current")
        self.app.on_replace_all()
        # Box 2 text must be unchanged
        self.assertEqual(doc.boxes[1].clean_text, orig_text)

        # 4. Script paste must skip locked box and preserve its content
        incoming_script = (
            "@@Pecorine\nNew Pecorine Text 1\n\n"
            "@@_\nNew Narration Text 2\n\n"
            "@@Kokkoro\nNew Kokkoro Text 3\n"
        )
        self.app.current_box_idx = 0
        self.app._show_paste_preview_and_apply(incoming_script, source_label="Test Paste", confirm=False)

        # Box 1 (Pecorine) was replaced
        self.assertEqual(doc.boxes[0].clean_text.strip(), "New Pecorine Text 1")
        # Box 2 (Locked Narration) was PRESERVED
        self.assertEqual(doc.boxes[1].clean_text, orig_text)
        # Box 3 (Kokkoro) was replaced
        self.assertEqual(doc.boxes[2].clean_text.strip(), "New Kokkoro Text 3")

        # 5. Opening a file clears locked boxes
        dummy_file = self.tmp_dir / "lock_test.txt"
        dummy_file.write_text("Hello World", encoding="utf-8")
        self.app.open_file(dummy_file)
        self.assertFalse(self.app.is_box_locked(1))
        self.assertEqual(len(self.app._locked_boxes), 0)

    def test_06_rendered_char_counter_and_overflow(self):
        """Rendered character length measurement and overflow warning for non-wrapping scenes (Rule 19 / GAME-BOX-PREVIEW)."""
        normal_text = "Short line 1\nShort line 2"
        lines_info = measure_line_lengths(normal_text)
        self.assertEqual(len(lines_info), 2)
        self.assertEqual(lines_info[0][1], len("Short line 1"))
        self.assertEqual(lines_info[1][1], len("Short line 2"))

        # Test line exceeding 45 characters
        overflow_line = "This is a very long dialogue line in Princess Connect that easily exceeds forty-five characters without wrapping."
        overflow_text = f"[b]{overflow_line}[/b]"
        ov_info = measure_line_lengths(overflow_text)
        self.assertGreater(ov_info[0][1], 45)

        # Test live character label update in UI
        self.app._update_rendered_char_count(overflow_text)
        lbl_text = self.app.lbl_char_count.cget("text")
        self.assertIn("⚠ Overflow", lbl_text)
        self.assertEqual(self.app.lbl_char_count.cget("fg"), self.app.theme["misora_pink"])

        self.app._update_rendered_char_count(normal_text)
        lbl_normal = self.app.lbl_char_count.cget("text")
        self.assertNotIn("⚠ Overflow", lbl_normal)
        self.assertEqual(self.app.lbl_char_count.cget("fg"), self.app.theme["fg_muted"])

    def test_07_find_replace_buttons_alignment_and_icons(self):
        """Find & Replace action buttons alignment, identical column widths, and illustrated icons."""
        # 1. Verify existence of the 4 buttons
        self.assertTrue(hasattr(self.app, "btn_find"))
        self.assertTrue(hasattr(self.app, "btn_cancel"))
        self.assertTrue(hasattr(self.app, "btn_replace"))
        self.assertTrue(hasattr(self.app, "btn_replace_all"))

        # 2. Verify all 4 buttons have their illustrated icons assigned
        self.assertIsNotNone(self.app.ico_find)
        self.assertIsNotNone(self.app.ico_cancel)
        self.assertIsNotNone(self.app.ico_replace)
        self.assertIsNotNone(self.app.ico_replace_all)

        # 3. Verify matching widths across the 2x2 grid columns
        self.assertEqual(self.app.btn_find.cget("width"), self.app.btn_replace.cget("width"))
        self.assertEqual(self.app.btn_cancel.cget("width"), self.app.btn_replace_all.cget("width"))


if __name__ == "__main__":
    unittest.main()
