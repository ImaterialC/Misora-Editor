#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5 Session S02: Font Policy, Custom Loader, Constant Ruler, Gutter Sync & Fast Metrics."""

import json
import shutil
import sys
import tempfile
import tkinter as tk
import tkinter.font as tkfont
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core.ngui_tags import strip_tags
from core.story_ast import Record, StoryDocument
import misora


def _find_comboboxes(widget: tk.Widget):
    found = []
    for child in widget.winfo_children():
        if child.winfo_class() == "TCombobox":
            found.append(child)
        found.extend(_find_comboboxes(child))
    return found


def _collect_label_texts(widget: tk.Widget):
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            try:
                texts.append(str(child.cget("text")))
            except Exception:
                pass
        texts.extend(_collect_label_texts(child))
    return texts


class TestV15S02FontsRulerMetrics(unittest.TestCase):
    """Failing-first probes and regression guards for S02 (v1.4.2)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s02_"))
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

    def _load_doc(self, text: str, include_box0: bool = False) -> None:
        recs = []
        if include_box0:
            recs.append(Record(cmd_id=32, cmd_name="subtitle", args=["Title", "Sub", text]))
        recs.append(Record(cmd_id=6, cmd_name="print", args=["Pecorine", text]))
        doc = StoryDocument(recs)
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "s02_test.txt"
        self.app.current_box_idx = 0
        self.app.is_box0_active = bool(include_box0)
        self.app._locked_boxes = set()
        self.app._modified_boxes = set()
        self.app.var_continuous_view.set(False)
        self.app.var_preview_compiled.set(False)
        self.app._update_views()
        self.app.update_idletasks()

    def test_probe_1_dialogue_font_presets_only_global_and_jp(self):
        """Probe 1: Strictly 2 built-in font presets, tooltip/help mentions both, legacy config migrates."""
        cbs = _find_comboboxes(self.app.tab_customize_frame)
        self.assertGreaterEqual(len(cbs), 2)
        font_cb = cbs[0]
        vals = tuple(font_cb.cget("values"))
        self.assertEqual(
            vals,
            ("Global — Nunito Bold", "Japanese — nintendoP_Humming-E_002pr"),
        )
        labels = " ".join(_collect_label_texts(self.app.tab_customize_frame))
        self.assertIn("Nunito Bold", labels)
        self.assertIn("nintendoP_Humming-E_002pr", labels)

        # Legacy config migration
        legacy_cfg = {"dialogue_font_family": "Consolas", "dialogue_font_size": 14}
        self.config_path.write_text(json.dumps(legacy_cfg), encoding="utf-8")
        migrated_prefs = self.app._load_user_prefs()
        self.assertEqual(migrated_prefs["dialogue_font_family"], "Global — Nunito Bold")
        self.assertEqual(migrated_prefs["dialogue_font_size"], 14)

    def test_probe_2_custom_font_manager_discovers_and_reports_invalid(self):
        """Probe 2: core.font_manager discovers .ttf/.otf + custom_fonts.txt, reports invalid cleanly, disposes."""
        from core.font_manager import FontManager

        fonts_dir = Path(tempfile.mkdtemp(prefix="misora_fonts_"))
        try:
            (fonts_dir / "broken.ttf").write_bytes(b"not-a-valid-ttf")
            (fonts_dir / "custom_fonts.txt").write_text("# comment\nCustom Family One\n", encoding="utf-8")
            nunito_sys = Path(r"C:\Windows\Fonts\Nunito-Bold.ttf")
            if nunito_sys.is_file():
                shutil.copy2(nunito_sys, fonts_dir / "Nunito-Bold.ttf")

            fm = FontManager(fonts_dir, logger=self.app.logger)
            self.assertIn("Custom Family One", fm.custom_families)
            self.assertTrue(any("broken.ttf" in err for err in fm.load_errors))
            fm.dispose()
        finally:
            shutil.rmtree(fonts_dir, ignore_errors=True)

    def test_probe_3_measure_font_uses_prefs_and_ruler_stays_constant(self):
        """Probe 3: _get_dialogue_measure_font follows prefs; ruler safe_w stays constant; 54d vs >54d non-overlapping."""
        self.app.var_dlg_font_sz.set(14)
        self.app.var_font_family.set("Global — Nunito Bold")
        self.app._on_font_pref_changed()
        f_global = self.app._get_dialogue_measure_font()
        self.assertEqual(int(f_global.cget("size")), 14)
        self.assertEqual(f_global.cget("family"), self.app.dialogue_font_family)
        safe_w_global = self.app._measure_dialogue_metrics("")["safe_w"]

        self.app.var_font_family.set("Japanese — nintendoP_Humming-E_002pr")
        self.app._on_font_pref_changed()
        f_jp = self.app._get_dialogue_measure_font()
        self.assertEqual(int(f_jp.cget("size")), 14)
        self.assertEqual(f_jp.cget("family"), self.app.dialogue_font_family)
        safe_w_jp = self.app._measure_dialogue_metrics("")["safe_w"]

        # Horizontal ruler 54d limit stays constant across Global & JP font switches
        self.assertEqual(safe_w_global, safe_w_jp)

        # Ruler labels 54d and >54d must not overlap
        self.app.ruler_clean.configure(width=800, height=22)
        self.app.update_idletasks()
        self.app._draw_single_pixel_ruler(self.app.ruler_clean, 40)
        items_54d = [
            item for item in self.app.ruler_clean.find_all()
            if self.app.ruler_clean.type(item) == "text" and self.app.ruler_clean.itemcget(item, "text") == "54d"
        ]
        items_gt = [
            item for item in self.app.ruler_clean.find_all()
            if self.app.ruler_clean.type(item) == "text" and ">54d" in self.app.ruler_clean.itemcget(item, "text")
        ]
        self.assertEqual(len(items_54d), 1)
        self.assertEqual(len(items_gt), 1)
        bbox_54d = self.app.ruler_clean.bbox(items_54d[0])
        bbox_gt = self.app.ruler_clean.bbox(items_gt[0])
        self.assertIsNotNone(bbox_54d)
        self.assertIsNotNone(bbox_gt)
        self.assertLessEqual(bbox_54d[2], bbox_gt[0])

    def test_probe_4_gutter_updates_font_size_on_pref_change(self):
        """Probe 4: gutter_clean updates font size and spacing in lockstep when dialogue_font_size changes."""
        self.app.var_dlg_font_sz.set(11)
        self.app._on_font_pref_changed()
        self.app.var_dlg_font_sz.set(16)
        self.app._on_font_pref_changed()
        self.app.update_idletasks()

        g_font = tkfont.Font(root=self.app, font=self.app.gutter_clean.cget("font"))
        t_font = tkfont.Font(root=self.app, font=self.app.txt_dialogue.cget("font"))
        self.assertEqual(int(g_font.cget("size")), 16)
        self.assertEqual(int(g_font.cget("size")), int(t_font.cget("size")))
        self.assertEqual(int(self.app.gutter_clean.cget("spacing1")), int(self.app.txt_dialogue.cget("spacing1")))
        self.assertEqual(int(self.app.gutter_clean.cget("spacing3")), int(self.app.txt_dialogue.cget("spacing3")))

    def test_probe_5_char_overflow_indicator_turns_red_and_no_max_label(self):
        """Probe 5: lbl_char_overflow has no '(max)', stays normal on 54d/tags, turns red on >54d or 4+ lines."""
        self.assertTrue(hasattr(self.app, "lbl_char_overflow"))
        self.app.var_font_family.set("Global — Nunito Bold")
        self.app.var_dlg_font_sz.set(11)
        self.app._on_font_pref_changed()

        self._load_doc("Hello")
        txt_short = str(self.app.lbl_char_overflow.cget("text"))
        self.assertNotIn("(max)", txt_short.lower())
        self.assertNotIn(str(self.app.lbl_char_overflow.cget("fg")).lower(), ("#c9184a", "#ff5c7c"))

        # NGUI tags do not inflate rendered width
        fifty_four_digits = "1234567890" * 5 + "1234"
        self._load_doc(f"[b][FF0000]{fifty_four_digits}[-][/b]")
        self.assertNotIn(str(self.app.lbl_char_overflow.cget("fg")).lower(), ("#c9184a", "#ff5c7c"))

        # >54d without linebreak turns red
        self._load_doc("W" * 60)
        self.assertIn(str(self.app.lbl_char_overflow.cget("fg")).lower(), ("#c9184a", "#ff5c7c"))

        # 4 lines turns red
        self._load_doc("L1\nL2\nL3\nL4")
        self.assertIn(str(self.app.lbl_char_overflow.cget("fg")).lower(), ("#c9184a", "#ff5c7c"))

    def test_probe_6_measure_dialogue_metrics_fast_path_and_exact_index(self):
        """Probe 6: Fast-path skips overflow on short lines; binary search finds exact overflow_raw_start."""
        m_short = self.app._measure_dialogue_metrics("Short line")
        self.assertFalse(m_short["has_width_overflow"])
        self.assertIsNone(m_short["lines"][0]["overflow_raw_start"])

        long_line = "[b][rub:あ]漢[/rub][/b]{playername}" + ("1234567890" * 6)
        m_long = self.app._measure_dialogue_metrics(long_line)
        self.assertTrue(m_long["has_width_overflow"])
        ov_idx = m_long["lines"][0]["overflow_raw_start"]
        self.assertIsNotNone(ov_idx)
        self.assertGreater(ov_idx, 0)
        # Prefix before ov_idx (with tags stripped) must fit <= safe_w, while including ov_idx exceeds safe_w
        f = self.app._get_dialogue_measure_font()
        safe_w = m_long["safe_w"]
        prefix_before = strip_tags(long_line[:ov_idx].replace("{playername}", "PlayerName"))
        prefix_at = strip_tags(long_line[: ov_idx + 1].replace("{playername}", "PlayerName"))
        self.assertLessEqual(f.measure(prefix_before), safe_w)
        self.assertGreater(f.measure(prefix_at), safe_w)

    def test_guard_1_ngui_tags_strip_and_ruby_base_preserved(self):
        """Guard 1: strip_tags and _measure_dialogue_metrics preserve ruby base text and non-zero {playername}."""
        self.assertEqual(strip_tags("[rub:ruby]base[/rub][b]hi[/b]{playername}"), "basehi")
        m_ruby = self.app._measure_dialogue_metrics("[rub:ruby]base[/rub]")
        self.assertGreater(m_ruby["lines"][0]["pixel_width"], 0)
        m_player = self.app._measure_dialogue_metrics("{playername}")
        self.assertGreater(m_player["lines"][0]["pixel_width"], 0)

    def test_guard_2_box0_summary_stays_unmeasured(self):
        """Guard 2: Box 0 Summary does not trigger dialogue 50x3 red overflow violation (DEF-04)."""
        self._load_doc(("1234567890" * 6) + "\n2\n3\n4", include_box0=True)
        self.assertTrue(self.app.is_box0_active)
        self.assertEqual(self.app.txt_box0_summary.tag_ranges("line_overflow"), ())
        if hasattr(self.app, "lbl_char_overflow"):
            self.assertNotIn(str(self.app.lbl_char_overflow.cget("fg")).lower(), ("#c9184a", "#ff5c7c"))


if __name__ == "__main__":
    unittest.main()
