#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 Session S17: Shared Pixel-Measure Helper, Calibrated Rulers & Char Counter Removal."""

import re
import sys
import tempfile
import shutil
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core.ngui_tags import measure_line_lengths
from core.story_ast import Record, StoryDocument
import misora


def _collect_all_label_texts(widget: tk.Widget):
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            try:
                texts.append(str(child.cget("text")))
            except Exception:
                pass
        texts.extend(_collect_all_label_texts(child))
    return texts


class TestS17PixelRulers(unittest.TestCase):
    """Failing-first probes and regression guards for S17 (BUG-40, FEAT-09)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s17_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)
        cls.patch_cfg = patch.object(misora, "CONFIG_PATH", cls.config_path)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warn.start()
        cls.patch_err.start()
        cls.patch_cfg.start()

        cls.app = misora.MisoraApp(restore_session=False, show_splash=False)
        cls.app._test_bypass_dialogs = True
        cls.app.withdraw()
        cls.app.backup_folder = str(cls.tmp_dir / "backups")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.destroy()
        except Exception:
            pass
        cls.patch_cfg.stop()
        cls.patch_err.stop()
        cls.patch_warn.stop()
        cls.patch_info.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_yesno.stop()
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _load_doc(self, text: str) -> None:
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", text]),
        ])
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "s17_test.txt"
        self.app.current_box_idx = 0
        self.app.is_box0_active = False
        self.app._locked_boxes = set()
        self.app._modified_boxes = set()
        self.app._update_views()
        self.app.update_idletasks()

    def test_01_probe_pixel_measure_rulers_and_overflow(self):
        """Probe 1 (BUG-40 & FEAT-09): 50 digit-widths safe_w, Kanji overflow, line 4+ red gutter, Canvas rulers, no char counter."""
        # 1. Char counter UI removed
        self.assertFalse(hasattr(self.app, "lbl_char_count"))
        self.assertFalse(hasattr(self.app, "_update_rendered_char_count"))

        # 2. Pixel-calibrated Canvas rulers
        self.assertIsInstance(self.app.ruler_clean, tk.Canvas)
        self.assertIsInstance(self.app.ruler_cont, tk.Canvas)

        # 3. Shared pixel-measure helper
        self.assertTrue(hasattr(self.app, "_measure_dialogue_metrics"))
        fifty_digits = "1234567890" * 5
        m_50 = self.app._measure_dialogue_metrics(fifty_digits)
        self.assertFalse(m_50["has_width_overflow"])
        self.assertIsNone(m_50["lines"][0]["overflow_raw_start"])

        fifty_one_digits = fifty_digits + "1"
        m_51 = self.app._measure_dialogue_metrics(fifty_one_digits)
        self.assertTrue(m_51["has_width_overflow"])
        self.assertEqual(m_51["lines"][0]["overflow_raw_start"], 50)

        # NGUI tags contribute 0px width, {playername} contributes >0px width, raw index maps accurately
        tagged_50 = f"[b][FF0000]{fifty_digits}[/][/b]"
        m_tagged_50 = self.app._measure_dialogue_metrics(tagged_50)
        self.assertFalse(m_tagged_50["has_width_overflow"])

        tagged_51 = f"[b][FF0000]{fifty_digits}[/][/b]1"
        m_tagged_51 = self.app._measure_dialogue_metrics(tagged_51)
        self.assertTrue(m_tagged_51["has_width_overflow"])
        ov_idx = m_tagged_51["lines"][0]["overflow_raw_start"]
        self.assertEqual(tagged_51[ov_idx:], "1")

        m_player = self.app._measure_dialogue_metrics("{playername}")
        self.assertGreater(m_player["lines"][0]["pixel_width"], 0)

        # Wide Japanese Kanji (< 50 chars) still exceeds 50 digit-widths
        kanji_line = "漢" * 40
        m_kanji = self.app._measure_dialogue_metrics(kanji_line)
        self.assertTrue(m_kanji["has_width_overflow"])
        self.assertIsNotNone(m_kanji["lines"][0]["overflow_raw_start"])

        # 4. Inline overflow highlight & line 4+ red gutter in Dialogue view
        self.app.var_continuous_view.set(False)
        self._load_doc(fifty_digits + "\nLine 2\nLine 3")
        self.assertEqual(self.app.txt_dialogue.tag_ranges("line_overflow"), ())
        self.assertEqual(self.app.gutter_clean.tag_ranges("gutter_overflow"), ())

        self._load_doc(kanji_line + "\nLine 2\nLine 3\nLine 4")
        self.assertTrue(len(self.app.txt_dialogue.tag_ranges("line_overflow")) >= 2)
        self.assertTrue(len(self.app.gutter_clean.tag_ranges("gutter_overflow")) >= 2)

        # 5. All Script view: no (N chars) label, card gutter_overflow + line_overflow active
        self.app.var_continuous_view.set(True)
        self._load_doc(fifty_one_digits + "\nL2\nL3\nL4")
        labels = _collect_all_label_texts(self.app.cont_stream_frame)
        char_labels = [t for t in labels if re.search(r"\(\d+\s+chars\)", t)]
        self.assertEqual(char_labels, [])
        card = self.app._card_widgets[0]
        self.assertTrue(len(card["txt"].tag_ranges("line_overflow")) >= 2)
        self.assertTrue(len(card["gutter"].tag_ranges("gutter_overflow")) >= 2)

    def test_02_guard_measure_line_lengths_intact(self):
        """Guard 1: core.ngui_tags.measure_line_lengths remains importable and functional."""
        res = measure_line_lengths("[b]Hello[/b]\nWorld")
        self.assertEqual(res, [(1, 5, "Hello"), (2, 5, "World")])


if __name__ == "__main__":
    unittest.main()
