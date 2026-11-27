#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S11e (v1.4.15) Verification Suite — UI Polish, Branding & Usability:
  - Probe 1 (Q-03): Per-widget word-wrap contract across all 22 tk.Text widgets,
                    pack-only clean_scroll_x inside clean_editor_row (Box 0 / Preview
                    mutual exclusion + line-number toggle safety), logical-line auto-resize.
  - Probe 2 (Q-05): Full non-blocking splash startup lifecycle across UI construction AND
                    slowed _deferred_restore, pumping queued Tk events via dooneevent(DONT_WAIT),
                    exception cleanup guard, external withdraw() guard, and single-root parity.
  - Probe 3 (Q-13): PriconneRe:TL (larger, bold) & Cornelia branding on Splash and About
                    ("Support the Creator" button) + __version__ == "1.4.15" parity.
  - Probe 4 (Q-14): Support the Creator EN copy (PriconneRe:TL & Cornelia, 0 Indonesian),
                    ~600px GIF scaling bounded by screen width & height, title & cleanup.
  - Probe 5 (Q-15): Verified PNG icon map, DPI-aware LANCZOS resizing & cache, BoxInsert vs
                    BoxReplace chooser icons, 3-icon selection trio (Q-07/Q-10) with
                    "Some selected" semantics, dynamic ToolTip.set_text(), filter/reload
                    stability, and get_icon -> None accessible fallback verification.
  - Probe 6 (Q-16): Main Menu inventory & NGUI Glossary deduplication (Reset Color Tag in Edit,
                    View > Toggle NGUI Glossary Panel sole entry, Help > Support the Creator...).
  - Probe 7 (Q-17): Complete 3-layer 350ms ToolTip coverage across Layer 1/2/3 controls.

Regression Guards (2 — MUST PASS both pre-patch and post-patch):
  - Guard 1: show_splash=False creates zero splash windows; dynamic single-source version parity.
  - Guard 2: S11d (Q-10/Q-11/Q-12), S04 (refresh.png), and S8b4 paned/fallback invariants intact.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import time
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import assets.icon as icon_mod  # noqa: E402
import assets.splash as splash_mod  # noqa: E402
import core.mtl_engine as mtl_mod  # noqa: E402
import misora  # noqa: E402
from core.script_codec import parse  # noqa: E402
from core.story_ast import BoxSnapshot, Record, StoryDocument  # noqa: E402
from core.xuat_index import build_xuat_index  # noqa: E402


def _collect_descendants(widget: tk.Misc) -> list[tk.Misc]:
    out: list[tk.Misc] = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


def _read_root_init_version() -> str:
    spec = importlib.util.spec_from_file_location("_misora_root_init_s11e", str(_REPO / "__init__.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return str(getattr(mod, "__version__", ""))


def _menu_items(menu: tk.Menu) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    end = menu.index("end")
    if end is None:
        return items
    for i in range(end + 1):
        mtype = menu.type(i)
        lbl = ""
        if mtype != "separator":
            try:
                lbl = str(menu.entrycget(i, "label"))
            except Exception:
                lbl = ""
        items.append((mtype, lbl))
    return items


class S11eTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_v15_s11e_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patches = [
            patch.object(misora, "CONFIG_PATH", self.config_path),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "askyesnocancel", return_value=False),
        ]
        for p in self.patches:
            p.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")
        self.app.xuat_archive_dir = self.tmp_dir / "backups" / "xuat_archive"

    def tearDown(self) -> None:
        for attr in ("_import_xuat_dialog", "_xuat_cleanup_dialog", "_about_dialog", "_support_me_dialog", "_translator_dialog"):
            try:
                dlg = getattr(self.app, attr, None)
                if dlg is not None and dlg.winfo_exists():
                    if hasattr(dlg, "_on_close"):
                        dlg._on_close()
                    elif hasattr(dlg, "close"):
                        dlg.close()
                    else:
                        dlg.destroy()
            except Exception:
                pass
        try:
            if hasattr(self.app, "logger") and self.app.logger:
                self.app.logger.close()
        except Exception:
            pass
        try:
            if self.app is not None:
                self.app.destroy()
        except Exception:
            pass
        self.app = None
        for p in reversed(self.patches):
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_xuat_tree(self) -> tuple[Path, Path]:
        proj_dir = self.tmp_dir / "proj"
        text_dir = proj_dir / "BepInEx" / "Translation" / "en" / "Text"
        text_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir, text_dir

    def _open_story(self, doc: StoryDocument, name: str = "s11e_story.v2.txt") -> Path:
        p = self.tmp_dir / name
        p.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(p)
        return p


class TestV15S11ePolishSplashMenuTooltips(S11eTestBase):
    """7 failing-first Probes + 2 Regression Guards for S11e (v1.4.15)."""

    # ------------------------------------------------------------------
    # Failing-First Defect / Behavior Probes
    # ------------------------------------------------------------------
    def test_probe_1_q03_per_widget_word_wrap_contract(self) -> None:
        """[Probe 1 — Q-03] Per-widget wrap contract (txt_dialogue='none', pack-only clean_scroll_x mutual exclusion & gutter toggle)."""
        # Core wrap='none' editors & gutters
        self.assertEqual(str(self.app.txt_dialogue.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_dialogue_preview.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_quick_edit.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_raw.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_results.cget("wrap")), "none")
        self.assertEqual(str(self.app.txt_opened_files.cget("wrap")), "none")
        self.assertEqual(str(self.app.gutter_clean.cget("wrap")), "none")

        # Core wrap='word' panes
        self.assertEqual(str(self.app.txt_box0_summary.cget("wrap")), "word")
        self.assertEqual(str(self.app.txt_glossary.cget("wrap")), "word")
        self.assertEqual(str(self.app.txt_mtl_all_list.cget("wrap")), "word")
        self.assertEqual(str(self.app.txt_mtl_all_scratchpad.cget("wrap")), "word")
        for eng, card in self.app._mtl_drawer_cards.items():
            self.assertEqual(str(card["scratchpad"].cget("wrap")), "word", f"MTL card {eng} must keep wrap='word'")

        # clean_scroll_x exists as a pack-managed child of clean_editor_row
        self.assertTrue(hasattr(self.app, "clean_scroll_x"))
        self.assertIs(self.app.clean_scroll_x.master, self.app.clean_editor_row)
        self.assertEqual(self.app.clean_scroll_x.winfo_manager(), "pack")

        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Title"]),
            Record(cmd_id=1, cmd_name="log", args=["Summary line"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "A" * 200]),
        ])
        self._open_story(doc, "q03_wrap.v2.txt")

        # Line numbers toggle OFF/ON must never raise pack-vs-grid TclError
        self.app.var_show_line_numbers.set(False)
        self.app._on_toggle_line_numbers()
        self.assertFalse(self.app._is_widget_packed(self.app.gutter_clean))
        self.app.var_show_line_numbers.set(True)
        self.app._on_toggle_line_numbers()
        self.assertTrue(self.app._is_widget_packed(self.app.gutter_clean))

        # Logical-line _auto_resize_dialogue_box: 1 long 200-char line keeps min height 7
        self.assertEqual(int(self.app.txt_dialogue.cget("height")), 7)

        # Mutual exclusion: Box 0 hides clean_editor_row (and therefore clean_scroll_x atomically)
        self.app.is_box0_active = True
        self.app._update_views()
        self.assertFalse(self.app._is_widget_packed(self.app.clean_editor_row))
        self.assertFalse(self.app.clean_scroll_x.winfo_ismapped())

        # Mutual exclusion: Dialogue Preview hides clean_editor_row atomically
        self.app.is_box0_active = False
        self.app.var_preview_compiled.set(True)
        self.app._on_toggle_preview_compiled()
        self.assertFalse(self.app._is_widget_packed(self.app.clean_editor_row))
        self.assertFalse(self.app.clean_scroll_x.winfo_ismapped())

        self.app.var_preview_compiled.set(False)
        self.app._on_toggle_preview_compiled()
        self.assertTrue(self.app._is_widget_packed(self.app.clean_editor_row))

        # Dialog tk.Text widgets retain wrap='word'
        ai_dlg = misora.AIPromptSettingsDialog(self.app)
        try:
            self.assertEqual(str(ai_dlg.txt_prompt.cget("wrap")), "word")
        finally:
            ai_dlg._on_cancel()

        ta_dlg = misora.TranslatorAssistantDialog(self.app)
        try:
            self.assertEqual(str(ta_dlg.txt_orig.cget("wrap")), "word")
            self.assertEqual(str(ta_dlg.txt_trans.cget("wrap")), "word")
        finally:
            ta_dlg._on_close()

    def test_probe_2_q05_splash_lifecycle_waits_for_deferred_restore_and_pumps_ticks(self) -> None:
        """[Probe 2 — Q-05] Splash stays open through UI build + slowed restore, pumps queued Tk events, then closes & reveals."""
        import json

        story_p = self.tmp_dir / "restore_story.v2.txt"
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Restored line"])])
        story_p.write_text(doc.to_v2_text(), encoding="utf-8")

        cfg_p = self.tmp_dir / "splash_cfg.json"
        cfg_p.write_text(
            json.dumps({"saved_opened_files": [str(story_p)], "saved_active_file": str(story_p)}),
            encoding="utf-8",
        )

        # Spy on MisoraSplashScreen.set_progress and slowed open_file
        progress_log: list[tuple[float, str, bool]] = []
        queued_events_processed: list[str] = []
        restore_observations: dict[str, object] = {}

        orig_set_progress = splash_mod.MisoraSplashScreen.set_progress

        def tracked_set_progress(self_sp, val: float, msg: str = "") -> None:
            progress_log.append((float(val), str(msg), bool(getattr(self_sp, "_closed", False))))
            orig_set_progress(self_sp, val, msg)

        orig_open_file = misora.MisoraApp.open_file

        def slowed_open_file(self_app, file_path, *args, **kwargs):
            sp = getattr(self_app, "_splash", None)
            restore_observations["splash_present"] = sp is not None
            restore_observations["splash_closed_during_restore"] = bool(getattr(sp, "_closed", True)) if sp else True
            restore_observations["splash_exists_during_restore"] = bool(sp and sp._root.winfo_exists())
            restore_observations["root_state_during_restore"] = self_app.state()
            restore_observations["max_progress_before_finish"] = max((p[0] for p in progress_log), default=0.0)
            restore_observations["ready_emitted_early"] = any("ready!" in p[1].lower() for p in progress_log)

            # Enqueue a Tk after callback during slowed restore and verify process_events() actually pumps it
            if sp is not None and sp._root.winfo_exists():
                sp._root.after(0, lambda: queued_events_processed.append("pumped_during_restore"))
                time.sleep(0.03)
                sp.process_events()

            return orig_open_file(self_app, file_path, *args, **kwargs)

        app2 = None
        with patch.object(misora, "CONFIG_PATH", cfg_p), \
             patch.object(splash_mod.MisoraSplashScreen, "set_progress", tracked_set_progress), \
             patch.object(misora.MisoraApp, "open_file", slowed_open_file):
            root_before = tk._default_root
            app2 = misora.MisoraApp(restore_session=True, show_splash=True)
            app2.backup_folder = str(self.tmp_dir / "backups2")
            try:
                # Immediately after __init__ exits (before after_idle restore completes), splash must STILL be open!
                self.assertIsNotNone(getattr(app2, "_splash", None), "Splash must stay alive until _deferred_restore completes")
                self.assertFalse(getattr(app2._splash, "_closed", True))
                self.assertTrue(app2._splash._root.winfo_exists())
                self.assertEqual(app2.state(), "withdrawn", "Main window must stay withdrawn while splash is showing")
                self.assertFalse(any("ready!" in p[1].lower() for p in progress_log), "Must not emit Ready! before restore finishes")

                # Drain after_idle -> runs slowed _deferred_restore
                app2.update()
                self.assertTrue(restore_observations.get("splash_present"))
                self.assertFalse(restore_observations.get("splash_closed_during_restore"))
                self.assertTrue(restore_observations.get("splash_exists_during_restore"))
                self.assertEqual(restore_observations.get("root_state_during_restore"), "withdrawn")
                self.assertLess(float(restore_observations.get("max_progress_before_finish", 1.0)), 1.0)
                self.assertFalse(restore_observations.get("ready_emitted_early"))
                self.assertIn(
                    "pumped_during_restore",
                    queued_events_processed,
                    "process_events() must pump queued Tk events via bounded dooneevent(DONT_WAIT) during restore",
                )

                # Once restore completes, splash closes and main window reveals
                self.assertIsNone(getattr(app2, "_splash", None))
                self.assertEqual(app2.state(), "normal")
                self.assertEqual(app2.current_file_path, story_p.resolve())
                self.assertTrue(any(p[0] == 1.0 and "ready!" in p[1].lower() for p in progress_log))
                self.assertIs(tk._default_root, root_before)
            finally:
                if app2 is not None:
                    app2.withdraw()
                    app2.destroy()

        # Verify external caller withdraw() after __init__ is NOT overridden by _deferred_restore
        app3 = None
        with patch.object(misora, "CONFIG_PATH", cfg_p):
            app3 = misora.MisoraApp(restore_session=False, show_splash=True)
            app3.backup_folder = str(self.tmp_dir / "backups3")
            try:
                app3.withdraw()
                app3.update()
                self.assertEqual(app3.state(), "withdrawn", "External withdraw() must not be undone by _deferred_restore")
            finally:
                app3.destroy()

        # Verify startup exception cleanup closes splash cleanly (no zombie splash window)
        closed_on_err = []
        orig_close = splash_mod.MisoraSplashScreen.close

        def spy_close(self_sp, callback=None):
            closed_on_err.append(True)
            orig_close(self_sp, callback=callback)

        with patch.object(splash_mod.MisoraSplashScreen, "close", spy_close), \
             patch.object(misora.MisoraApp, "_build_main_panels", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                bad_app = misora.MisoraApp(restore_session=False, show_splash=True)
                bad_app.destroy()
            self.assertTrue(closed_on_err, "Startup exception must close active splash immediately")

    def test_probe_3_q13_priconneretl_and_cornelia_branding_splash_and_about(self) -> None:
        """[Probe 3 — Q-13] Splash & About prominently display bold/larger PriconneRe:TL + Cornelia + v1.4.15 parity."""
        self.assertEqual(_read_root_init_version(), "1.4.15")
        self.assertEqual(misora.__version__, "1.4.15")
        self.assertEqual(splash_mod._VERSION, "1.4.15")
        self.assertEqual(mtl_mod.APP_VERSION, "1.4.15")

        # 1. Splash screen canvas branding
        sp = splash_mod.MisoraSplashScreen(parent=self.app)
        try:
            text_items = []
            for item_id in sp._canvas.find_all():
                if sp._canvas.type(item_id) == "text":
                    text_items.append((
                        str(sp._canvas.itemcget(item_id, "text")),
                        str(sp._canvas.itemcget(item_id, "font")),
                    ))
            joined = "\n".join(t for t, _ in text_items)
            self.assertIn("PriconneRe:TL", joined)
            self.assertIn("Cornelia", joined)
            self.assertIn("Misora: Story Editor", joined)
            self.assertIn("v1.4.15", joined)

            brand_fonts = [f for t, f in text_items if "PriconneRe:TL" in t]
            self.assertTrue(brand_fonts)
            self.assertTrue(any("bold" in f.lower() for f in brand_fonts))
        finally:
            sp.close()

        # 2. About dialog branding & "Support the Creator" button alignment
        self.app.on_about()
        about_dlg = getattr(self.app, "_about_dialog", None)
        self.assertIsNotNone(about_dlg)
        self.assertTrue(about_dlg.winfo_exists())
        desc = _collect_descendants(about_dlg)
        labels = [w for w in desc if isinstance(w, tk.Label)]
        btns = [w for w in desc if isinstance(w, (tk.Button, ttk.Button))]
        joined_lbls = "\n".join(str(w.cget("text")) for w in labels)
        joined_btns = "\n".join(str(w.cget("text")) for w in btns)

        self.assertIn("PriconneRe:TL", joined_lbls)
        self.assertIn("Cornelia", joined_lbls)
        self.assertIn("Misora: Story Editor", joined_lbls)
        self.assertIn("v1.4.15", joined_lbls)
        self.assertIn("Support the Creator", joined_btns)

        brand_lbls = [w for w in labels if "PriconneRe:TL" in str(w.cget("text"))]
        self.assertTrue(brand_lbls)
        brand_font = str(brand_lbls[0].cget("font")).lower()
        self.assertIn("bold", brand_font)
        # Ensure PriconneRe:TL label uses larger font (>= 14pt)
        import tkinter.font as tkfont
        f_obj = tkfont.Font(root=about_dlg, font=brand_lbls[0].cget("font"))
        self.assertGreaterEqual(abs(int(f_obj.cget("size"))), 14)

    def test_probe_4_q14_support_dialog_english_and_600px_gif(self) -> None:
        """[Probe 4 — Q-14] SupportMeDialog uses 100% English PriconneRe:TL/Cornelia copy and ~600px width/height clamped GIF."""
        gif_path = self.tmp_dir / "service_600.gif"
        frames = [Image.new("RGBA", (600, 338), (200, 90, 140, 255)) for _ in range(3)]
        frames[0].save(gif_path, format="GIF", save_all=True, append_images=frames[1:], duration=50, loop=0)

        # Full desktop geometry -> 600x338 renders at 600x338 (not shrunk to 240px)
        with patch.object(misora.SupportMeDialog, "winfo_screenwidth", return_value=1920), \
             patch.object(misora.SupportMeDialog, "winfo_screenheight", return_value=1080):
            dlg = misora.SupportMeDialog(self.app, gif_path=gif_path)
            try:
                self.app.update_idletasks()
                self.assertEqual(dlg.title(), "Support the Creator — Misora: Story Editor")
                all_texts = "\n".join(
                    str(w.cget("text"))
                    for w in _collect_descendants(dlg)
                    if isinstance(w, (tk.Label, tk.Button, ttk.Button))
                )
                self.assertIn("PriconneRe:TL", all_texts)
                self.assertIn("Cornelia", all_texts)
                for id_word in ("terima kasih", "dukungan", "hargai", "menutup", "biaya"):
                    self.assertNotIn(id_word, all_texts.lower())

                self.assertIsNotNone(dlg._current_frame_photo)
                self.assertEqual(dlg._current_frame_photo.width(), 600)
                self.assertEqual(dlg._current_frame_photo.height(), 338)
            finally:
                dlg.close()

        # Compact 720p @ 125% DPI logical height (576px) -> clamps GIF height so bottom buttons stay visible
        with patch.object(misora.SupportMeDialog, "winfo_screenwidth", return_value=1024), \
             patch.object(misora.SupportMeDialog, "winfo_screenheight", return_value=576):
            dlg_small = misora.SupportMeDialog(self.app, gif_path=gif_path)
            try:
                self.app.update_idletasks()
                self.assertIsNotNone(dlg_small._current_frame_photo)
                self.assertLessEqual(dlg_small._current_frame_photo.height(), 316)
                self.assertGreater(dlg_small._current_frame_photo.width(), 240)
            finally:
                dlg_small.close()

    def test_probe_5_q15_verified_icons_dpi_lanczos_and_3icon_selection_trio(self) -> None:
        """[Probe 5 — Q-15] DPI-aware LANCZOS icons, verified map, BoxInsert/BoxReplace chooser, 3-icon trio & fallback."""
        # 1. DPI-aware helper & LANCZOS scaling
        self.assertTrue(hasattr(icon_mod, "get_dpi_scale"))
        self.assertTrue(hasattr(icon_mod, "scale_icon_size"))
        with patch.object(self.app, "winfo_fpixels", return_value=144.0):  # 150% DPI
            scaled = icon_mod.scale_icon_size((20, 20), master=self.app)
            self.assertEqual(scaled, (30, 30))
            ico_scaled = self.app.get_icon("BoxD", (20, 20), dpi_aware=True)
            self.assertIsNotNone(ico_scaled)
            self.assertEqual((ico_scaled.width(), ico_scaled.height()), (30, 30))

        # 2. Verified toolbar/header icon wiring & parked BoxConversation.png check
        for attr in (
            "ico_mtl",
            "ico_all_script",
            "ico_plus",
            "ico_box_cut",
            "ico_box_copy",
            "ico_box_paste",
            "ico_box_select_all",
            "ico_box_select_none",
        ):
            self.assertIsNotNone(getattr(self.app, attr, None), f"Expected retained PhotoImage self.{attr}")

        misora_src = (_REPO / "misora.py").read_text(encoding="utf-8")
        self.assertIn('get_icon("language-translation-icon"', misora_src)
        self.assertIn('get_icon("BoxConversationList"', misora_src)
        self.assertIn('get_icon("BoxD"', misora_src)
        self.assertIn('get_icon("BoxCopy"', misora_src)
        self.assertIn('get_icon("BoxCut"', misora_src)
        self.assertIn('get_icon("BoxPaste"', misora_src)
        self.assertIn('get_icon("BoxInsert"', misora_src)
        self.assertIn('get_icon("BoxReplace"', misora_src)
        self.assertNotIn('"BoxConversation"', misora_src)
        self.assertNotIn("'BoxConversation'", misora_src)

        # Q-10 gd_header icons & fallback text
        self.assertTrue(str(self.app.btn_select_all_boxes.cget("image")))
        self.assertTrue(str(self.app.btn_deselect_all_boxes.cget("image")))
        self.assertEqual(str(self.app.btn_select_all_boxes.cget("text")), "All")
        self.assertEqual(str(self.app.btn_deselect_all_boxes.cget("text")), "None")

        # 3. _show_box_paste_mode_dialog wires BoxInsert -> btn_ins and BoxReplace -> btn_rep
        captured_chooser_btns: dict[str, str] = {}
        orig_wait = misora.MisoraApp.wait_window

        def _capture_and_cancel(self_app, win):
            for w in _collect_descendants(win):
                if isinstance(w, (tk.Button, ttk.Button)):
                    txt = str(w.cget("text"))
                    if txt.startswith("Insert"):
                        captured_chooser_btns["insert_img"] = str(w.cget("image"))
                    elif txt.startswith("Replace"):
                        captured_chooser_btns["replace_img"] = str(w.cget("image"))
            win.destroy()

        with patch.object(misora.MisoraApp, "wait_window", _capture_and_cancel):
            self.app._show_box_paste_mode_dialog(1, "Pecorine", [0], 2, is_box0=False)
        self.assertTrue(captured_chooser_btns.get("insert_img"), "Insert button must carry BoxInsert icon")
        self.assertTrue(captured_chooser_btns.get("replace_img"), "Replace button must carry BoxReplace icon")

        # 4. Q-07 ImportFromXUATDialog 3-icon selection trio, "Some selected" semantics, filter & reload stability
        proj_dir, text_dir = self._make_xuat_tree()
        (text_dir / "Main.txt").write_text(
            "セリフ1=Line 1 EN\n"
            "セリフ2=Line 2 EN\n",
            encoding="utf-8",
        )
        self.app._set_project_folder(proj_dir)
        doc = StoryDocument([
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ1"]),
            Record(cmd_id=10, cmd_name="touch", args=[]),
            Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ2"]),
        ])
        self._open_story(doc, "q15_xuat.v2.txt")
        idx = build_xuat_index([proj_dir])

        dlg = self.app.on_import_from_xuat(xuat_index=idx)
        try:
            dlg.update_idletasks()
            btn = dlg._group_select_buttons["dialogue"]
            # "all" state
            self.assertEqual(dlg._group_select_states["dialogue"], "all")
            self.assertTrue(str(btn.cget("image")))
            self.assertEqual(str(btn.cget("text")), "Deselect All")
            w_all = btn.winfo_reqwidth()
            h_all = btn.winfo_reqheight()

            # "partial" state -> MUST say "Some selected", NEVER "One selected"
            dlg._rows[0]["var_skip"].set(True)
            dlg.update_idletasks()
            self.assertEqual(dlg._group_select_states["dialogue"], "partial")
            self.assertEqual(str(btn.cget("text")), "Some selected")
            self.assertIn("some selected", btn._tooltip.text.lower())
            self.assertNotIn("one selected", str(btn.cget("text")).lower())
            self.assertNotIn("one selected", btn._tooltip.text.lower())
            self.assertEqual(btn.winfo_reqwidth(), w_all, "Tri-state button width must not shift")
            self.assertEqual(btn.winfo_reqheight(), h_all, "Tri-state button height must not shift")

            # "none" state
            dlg._rows[1]["var_skip"].set(True)
            dlg.update_idletasks()
            self.assertEqual(dlg._group_select_states["dialogue"], "none")
            self.assertEqual(str(btn.cget("text")), "Select All")
            self.assertEqual(btn.winfo_reqwidth(), w_all)

            # Filter switch & _on_reload_index() preserve icons & valid PhotoImages
            dlg._set_filter("matched")
            self.assertEqual(dlg._group_select_states["dialogue"], "none")
            self.assertTrue(str(dlg._group_select_buttons["dialogue"].cget("image")))

            with patch.object(self.app, "_refresh_xuat_index_async", side_effect=lambda on_ready=None, **_kw: on_ready(idx, None)):
                dlg._on_reload_index()
            self.assertEqual(dlg._group_select_states["dialogue"], "all")
            self.assertTrue(str(dlg._group_select_buttons["dialogue"].cget("image")))
        finally:
            dlg._on_close()

        # 5. Image-failure fallback verification: mock get_icon -> None
        with patch.object(self.app, "get_icon", return_value=None):
            dlg_fb = self.app.on_import_from_xuat(xuat_index=idx)
            try:
                dlg_fb.update_idletasks()
                btn_fb = dlg_fb._group_select_buttons["dialogue"]
                self.assertEqual(str(btn_fb.cget("image")), "")
                self.assertEqual(str(btn_fb.cget("text")), "Deselect All")
                self.assertGreater(btn_fb.winfo_reqwidth(), 20)

                dlg_fb._rows[0]["var_skip"].set(True)
                self.assertEqual(str(btn_fb.cget("text")), "Some selected")
                self.assertNotIn("one selected", str(btn_fb.cget("text")).lower())

                dlg_fb._rows[1]["var_skip"].set(True)
                self.assertEqual(str(btn_fb.cget("text")), "Select All")
            finally:
                dlg_fb._on_close()

    def test_probe_6_q16_main_menu_inventory_and_ngui_glossary_dedup(self) -> None:
        """[Probe 6 — Q-16] Top-level NGUI Glossary & duplicate glossary/customize menu entries removed; actions preserved."""
        menubar = self.app.nametowidget(self.app.cget("menu"))
        top_cascades: dict[str, tk.Menu] = {}
        top_labels: list[str] = []
        end_idx = menubar.index("end")
        if end_idx is not None:
            for i in range(end_idx + 1):
                if menubar.type(i) == "cascade":
                    lbl = str(menubar.entrycget(i, "label"))
                    top_labels.append(lbl)
                    top_cascades[lbl] = self.app.nametowidget(menubar.entrycget(i, "menu"))

        self.assertNotIn("NGUI Glossary", top_labels)
        self.assertEqual(
            top_labels,
            ["File", "Edit", "View", "Tools", "Search", "Customize", "Folders & Files", "Translator", "Datamine", "Debug", "Help"],
        )

        # Edit keeps Reset Color Tag ([-])
        edit_labels = [lbl for _, lbl in _menu_items(self.app.edit_menu) if lbl]
        self.assertIn("Reset Color Tag ([-])", edit_labels)

        # View keeps sole canonical drawer toggles
        view_labels = [lbl for _, lbl in _menu_items(self.app.view_menu) if lbl]
        self.assertIn("Toggle NGUI Glossary Panel", view_labels)
        self.assertIn("Toggle Customization Panel", view_labels)

        # Customize drops duplicates
        cust_labels = [lbl for _, lbl in _menu_items(top_cascades["Customize"]) if lbl]
        self.assertNotIn("Display & Theme Settings...", cust_labels)
        self.assertNotIn("AI / LLM Translation Prompt Settings...", cust_labels)

        # Help removes NGUI & Ruby Glossary duplicate and exposes Support the Creator... + About
        help_labels = [lbl for _, lbl in _menu_items(top_cascades["Help"]) if lbl]
        self.assertNotIn("NGUI & Ruby Glossary", help_labels)
        self.assertIn("Support the Creator...", help_labels)
        self.assertIn("About Misora: Story Editor", help_labels)

    def test_probe_7_q17_complete_3_layer_tooltips(self) -> None:
        """[Probe 7 — Q-17] Complete 350ms ToolTip coverage across Search, Left Dock, Workspace, Side Drawer, and Import/Cleanup dialogs."""
        # Layer 1: Main workspace, search bar, dock, bottom tabs, status bar
        layer1_widgets = [
            "btn_replace", "btn_replace_all", "cb_case", "cb_rx", "cb_ws",
            "rb_proj", "rb_folder", "rb_cur", "cb_bdl", "cb_txt", "btn_browse_search_folder",
            "btn_tab_search", "btn_open_more", "cb_dialogue_select", "btn_empty_open",
            "btn_tab_quick_edit", "btn_tab_raw_commands", "cb_sync_xuat", "btn_revert",
        ]
        for attr in layer1_widgets:
            w = getattr(self.app, attr, None)
            self.assertIsNotNone(w, f"Missing Layer 1 widget attr self.{attr}")
            tip = getattr(w, "_tooltip", None)
            self.assertIsNotNone(tip, f"Layer 1 widget self.{attr} missing ToolTip")
            self.assertTrue(getattr(tip, "text", "").strip(), f"Layer 1 widget self.{attr} has empty ToolTip")
            self.assertEqual(getattr(tip, "delay_ms", None), 350, f"Layer 1 self.{attr} delay_ms != 350")

        # Layer 2: Right Side Drawer (Customize & NGUI Glossary)
        layer2_widgets = [
            "cb_custom_font", "btn_refresh_fonts", "btn_open_fonts_folder",
            "cb_preset", "btn_apply_preset", "btn_reset_custom",
            "ent_glossary_filter", "btn_insert_glossary",
        ]
        for attr in layer2_widgets:
            w = getattr(self.app, attr, None)
            self.assertIsNotNone(w, f"Missing Layer 2 widget attr self.{attr}")
            tip = getattr(w, "_tooltip", None)
            self.assertIsNotNone(tip, f"Layer 2 widget self.{attr} missing ToolTip")
            self.assertTrue(getattr(tip, "text", "").strip(), f"Layer 2 widget self.{attr} has empty ToolTip")
            self.assertEqual(getattr(tip, "delay_ms", None), 350, f"Layer 2 self.{attr} delay_ms != 350")

        # Layer 3: ImportFromXUATDialog & XuatCleanupDialog
        proj_dir, text_dir = self._make_xuat_tree()
        (text_dir / "Dup.txt").write_text("セリフ=Line EN\n", encoding="utf-8")
        (text_dir / "Dup2.txt").write_text("セリフ=Line Alt\n", encoding="utf-8")
        self.app._set_project_folder(proj_dir)
        doc = StoryDocument([Record(cmd_id=6, cmd_name="print", args=["ペコリーヌ", "セリフ"])])
        self._open_story(doc, "q17_dlg.v2.txt")
        idx = build_xuat_index([proj_dir])

        dlg = self.app.on_import_from_xuat(xuat_index=idx)
        try:
            for attr in ("btn_reload_xuat", "cb_archive_xuat", "cb_auto_word_wrap", "btn_cancel", "btn_apply"):
                w = getattr(dlg, attr, None)
                self.assertIsNotNone(w, f"Missing ImportFromXUATDialog.{attr}")
                tip = getattr(w, "_tooltip", None)
                self.assertIsNotNone(tip, f"ImportFromXUATDialog.{attr} missing ToolTip")
                self.assertEqual(getattr(tip, "delay_ms", None), 350)
            for fk, btn in dlg._filter_buttons.items():
                self.assertIsNotNone(getattr(btn, "_tooltip", None), f"Filter button {fk} missing ToolTip")
            row0 = dlg._rows[0]
            for rkey in ("cb_skip", "scope_cmb", "btn_prev", "btn_next"):
                self.assertIsNotNone(getattr(row0[rkey], "_tooltip", None), f"Row control {rkey} missing ToolTip")
        finally:
            dlg._on_close()

        cdlg = misora.XuatCleanupDialog(
            self.app, xuat_index=idx, doc=doc, applied_records=(), mode="manual", xuat_roots=[text_dir]
        )
        try:
            for attr in ("cb_include_applied", "btn_select_all", "btn_deselect_all", "btn_execute", "btn_close"):
                w = getattr(cdlg, attr, None)
                self.assertIsNotNone(w, f"Missing XuatCleanupDialog.{attr}")
                tip = getattr(w, "_tooltip", None)
                self.assertIsNotNone(tip, f"XuatCleanupDialog.{attr} missing ToolTip")
                self.assertEqual(getattr(tip, "delay_ms", None), 350)
        finally:
            cdlg._on_close()

    # ------------------------------------------------------------------
    # Regression Guards (MUST PASS both pre-patch and post-patch)
    # ------------------------------------------------------------------
    def test_guard_1_headless_show_splash_false_and_single_source_version_parity(self) -> None:
        """[Guard 1] show_splash=False creates zero splash windows; dynamic single-source version parity holds."""
        with patch.object(misora, "MisoraSplashScreen") as mock_splash_cls:
            app_g = misora.MisoraApp(restore_session=False, show_splash=False)
            app_g.withdraw()
            try:
                mock_splash_cls.assert_not_called()
            finally:
                app_g.destroy()

        root_ver = _read_root_init_version()
        self.assertRegex(root_ver, r"^\d+\.\d+\.\d+$")
        self.assertEqual(misora.__version__, root_ver)
        self.assertEqual(misora._get_app_version(), root_ver)
        self.assertEqual(splash_mod._VERSION, root_ver)
        self.assertEqual(mtl_mod.APP_VERSION, root_ver)

    def test_guard_2_s11d_s04_and_s8b4_invariants_intact(self) -> None:
        """[Guard 2] S11d Q-10/Q-11/Q-12, S04 refresh.png (14,14), and S8b4 paned/fallback contracts remain intact."""
        doc = StoryDocument([
            Record(cmd_id=0, cmd_name="fade", args=["Episode Title"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Hello"]),
        ])
        self._open_story(doc, "guard2.v2.txt")

        # Q-10 Box 0 exclusion
        self.app.var_select_box_mode.set(True)
        self.app._on_toggle_select_box_mode()
        self.app._on_select_all_boxes()
        self.assertEqual(self.app._selected_boxes, {0})
        self.assertNotIn(-1, self.app._selected_boxes)

        # Q-11 MTL Globe URLs
        self.assertEqual(set(self.app._MTL_GLOBE_URLS.keys()), {"Google", "DeepL"})

        # Q-12 title metadata
        self.assertIn("Episode Title", self.app.title())

        # S04 refresh.png exact (14, 14) contract
        ico_ref = self.app.get_icon("refresh", (14, 14))
        self.assertIsNotNone(ico_ref)

        # S8b4 fallback text non-empty on primary action buttons
        for attr in ("btn_box_new", "btn_box_cut", "btn_box_copy", "btn_box_paste", "btn_translate"):
            self.assertTrue(str(getattr(self.app, attr).cget("text")).strip())


if __name__ == "__main__":
    unittest.main()
