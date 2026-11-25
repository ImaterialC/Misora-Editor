#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 Session S18: Code-Drawn Game-Style Dialogue Preview & All Script Preview (FEAT-10)."""

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


def _find_widgets_of_type(root: tk.Widget, cls_type):
    found = []
    for child in root.winfo_children():
        if isinstance(child, cls_type):
            found.append(child)
        found.extend(_find_widgets_of_type(child, cls_type))
    return found


class TestP3S18GamePreview(unittest.TestCase):
    """Failing-first probes and regression guard for S18 (FEAT-10)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s18_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patches = [
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=True),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora, "CONFIG_PATH", cls.config_path),
        ]
        for p in cls.patches:
            p.start()

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
        for p in reversed(cls.patches):
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()

    def _load_v2_story(self, boxes):
        doc = StoryDocument()
        records = [Record(cmd_id=0, cmd_name="title", args=["Preview Title"])]
        for idx, (sp, txt) in enumerate(boxes):
            if idx > 0:
                records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            records.append(Record(cmd_id=6, cmd_name="print", args=[sp, txt]))
        doc.records = records
        doc._rebuild_boxes()
        p = self.tmp_dir / "s18_story.v2.txt"
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p, reload_from_disk=True)
        self.app.update_idletasks()
        return p

    def test_01_probe_dialogue_preview_frame_bleed_restore_and_cstyle_sweep(self):
        """[Probe 1 — FEAT-10] Dialogue Preview: single Canvas + embedded read-only Text, wrap='none',
        no font auto-shrinking, visible bleed, caret/selection/yview restore, cstyle_* sweep, pure presentation.
        """
        overwide = "1234567890" * 6  # 60 digits > 50d safe_w
        four_lines = f"[FF0000]Line1[-]\nLine2\nLine3\n{overwide}"
        box1_text = "[00FF00][b]Box Two[/b][-]\nShort line."
        self._load_v2_story([("Pecorine", four_lines), ("Kokkoro", box1_text)])

        # Set caret & selection on txt_dialogue before toggling Preview ON
        self.app.txt_dialogue.focus_set()
        self.app.txt_dialogue.mark_set("insert", "2.3")
        self.app.txt_dialogue.tag_add("sel", "2.1", "2.4")
        self.app.txt_dialogue.yview_moveto(0.0)
        self.app.update_idletasks()

        # Toggle Preview ON
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        # 1. Single tk.Canvas + embedded read-only tk.Text
        self.assertTrue(hasattr(self.app, "dialogue_preview_canvas"))
        self.assertIsInstance(self.app.dialogue_preview_canvas, tk.Canvas)
        self.assertTrue(hasattr(self.app, "txt_dialogue_preview"))
        self.assertIsInstance(self.app.txt_dialogue_preview, tk.Text)
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("state")), "disabled")

        # 2. Canvas draws Priconne-style frame primitives (border, name plate, static ▼)
        frame_items = self.app.dialogue_preview_canvas.find_withtag("preview_frame")
        self.assertGreaterEqual(len(frame_items), 3)

        # 3. No auto-shrinking: base cstyle_* font size matches active dialogue_font_size
        d_sz = int(self.app.prefs.get("dialogue_font_size", 11))
        cstyle_tags = [t for t in self.app.txt_dialogue_preview.tag_names() if t.startswith("cstyle_")]
        self.assertTrue(len(cstyle_tags) > 0)
        # Ensure normal text tag uses full d_sz (not shrunk)
        self.assertTrue(any(t.endswith(f"_{d_sz}") for t in cstyle_tags))

        # 4. Visible bleed: embedded text widget is NOT clipped to 3 lines
        self.assertGreaterEqual(int(self.app.txt_dialogue_preview.cget("height")), 4)

        # 5. Pure presentation: zero dirty / undo mutation
        self.assertFalse(self.app.is_dirty)
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

        # 6. Switch to Box 1 while Preview ON -> sweeps old cstyle_* tags from Box 0
        self.app.current_box_idx = 1
        self.app._update_views()
        self.app.update_idletasks()
        cstyle_after_switch = [t for t in self.app.txt_dialogue_preview.tag_names() if t.startswith("cstyle_")]
        self.assertFalse(any("#ff0000" in t for t in cstyle_after_switch))

        # Switch back to Box 0 and toggle Preview OFF -> restores caret & selection safely
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        self.assertEqual(self.app.txt_dialogue.index("insert"), "2.3")
        self.assertEqual(self.app.txt_dialogue.get("sel.first", "sel.last"), "ine")
        self.assertFalse(self.app.is_dirty)
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

    def test_02_probe_all_script_preview_lightweight_frames_no_canvas(self):
        """[Probe 2 — FEAT-10 / Technique A] All Script Preview renders in single read-only txt_all_script
        with wrap='none', overflow bleed, and zero per-card tk.Canvas widgets.
        """
        four_lines = "Line 1\nLine 2\nLine 3\n" + ("1234567890" * 6)
        self._load_v2_story([("Pecorine", four_lines), ("", "Narration line.")])

        self.app.var_continuous_view.set(True)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        # Zero per-card tk.Canvas widgets inside cont_stream_frame
        canvases = _find_widgets_of_type(self.app.cont_stream_frame, tk.Canvas)
        self.assertEqual(len(canvases), 0)
        self.assertEqual(self.app._card_widgets, {})

        # Single read-only txt_all_script uses wrap='none' and marks overflow bleed
        self.assertEqual(str(self.app.txt_all_script.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_all_script.cget("state")), "disabled")
        self.assertTrue(len(self.app.txt_all_script.tag_ranges("line_overflow")) >= 2)
        self.assertTrue(len(self.app.txt_all_script.tag_ranges("gutter_overflow")) >= 2)

        # Pure presentation: zero dirty / undo mutation
        self.assertFalse(self.app.is_dirty)
        self.assertEqual(self.app.undo_journal.undo_depth, 0)

    def test_03_guard_plain_text_preview_save_and_pixel_measure_intact(self):
        """[Guard 1] Lightweight regression guard for BUG-11 plain-text preview save & S17 pixel-measure helper."""
        # S17 shared pixel-measure helper intact
        m = self.app._measure_dialogue_metrics("1234567890" * 5 + "1")
        self.assertTrue(m["has_width_overflow"])
        self.assertEqual(m["lines"][0]["overflow_raw_start"], 50)

        # BUG-11 plain-text save preserves NGUI tags while Preview ON
        raw_content = "[FF0000]Red Text[-] and [00FF00]Green[-]"
        plain_path = self.tmp_dir / "s18_guard_plain.txt"
        plain_path.write_text(raw_content, encoding="utf-8")
        self.app.open_file(plain_path, reload_from_disk=True)
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.app.update_idletasks()

        self.assertTrue(self.app.on_save())
        self.assertEqual(plain_path.read_text(encoding="utf-8"), raw_content)


if __name__ == "__main__":
    unittest.main()
