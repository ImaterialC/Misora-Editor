#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora/tests/test_misora_ui_integration.py - Unit test suite for UI integration,
Project Folder linking, multi-framework discovery, and DnD scope workflows.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import importlib.util

from core.story_ast import Record, StoryDocument
from core.search_engine import SearchOptions

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

misora_script = MISORA_DIR / "misora.py"
spec = importlib.util.spec_from_file_location("misora_main", misora_script)
misora_app = importlib.util.module_from_spec(spec)
sys.modules["misora_main"] = misora_app
spec.loader.exec_module(misora_app)


class TestMisoraUIIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_ui_test_"))
        self.app = misora_app.MisoraApp(restore_session=False)
        self.app.withdraw()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_two_way_project_folder_linking(self):
        """Find UI folder_path_var under scope: project and self.project_folder must stay in sync."""
        test_project_dir = self.tmp_dir / "MyModProject"
        test_project_dir.mkdir(parents=True, exist_ok=True)

        # 1. Setting project_folder reflects in folder_path_var under project scope
        self.app.scope_var.set("project")
        self.app.project_folder = test_project_dir
        self.app.bepinex_project_folder = test_project_dir
        self.app._sync_scope_widgets()
        self.assertEqual(self.app.folder_path_var.get(), str(test_project_dir))

        # 2. Typing into folder_path_var under project scope immediately updates self.project_folder
        updated_dir = self.tmp_dir / "AnotherModProject"
        updated_dir.mkdir(parents=True, exist_ok=True)
        self.app.folder_path_var.set(str(updated_dir))
        self.assertEqual(self.app.project_folder, updated_dir)
        self.assertEqual(self.app.bepinex_project_folder, updated_dir)

    def test_02_scope_switch_preserves_project_and_folder_paths(self):
        """Switching between Project and Folder scopes preserves each scope's distinct directory."""
        proj_dir = self.tmp_dir / "ProjectRoot"
        folder_dir = self.tmp_dir / "SingleFolder"
        proj_dir.mkdir(parents=True, exist_ok=True)
        folder_dir.mkdir(parents=True, exist_ok=True)

        self.app.project_folder = proj_dir
        self.app.bepinex_project_folder = proj_dir
        self.app.selected_search_folder = folder_dir

        # Switch to Folder scope
        self.app.scope_var.set("folder")
        self.app._sync_scope_widgets()
        self.assertEqual(self.app.folder_path_var.get(), str(folder_dir))

        # Switch to Project scope
        self.app.scope_var.set("project")
        self.app._sync_scope_widgets()
        self.assertEqual(self.app.folder_path_var.get(), str(proj_dir))

        # Switch to Current File(s) scope
        self.app.scope_var.set("current")
        self.app._sync_scope_widgets()
        self.assertEqual(self.app.folder_path_entry.cget("state"), "readonly")
        self.assertEqual(str(self.app.btn_browse_search_folder.cget("state")), "disabled")

    def test_03_config_backward_compatibility(self):
        """misora_config.json stores and loads both project_folder and bepinex_project_folder."""
        custom_dir = self.tmp_dir / "MelonLoaderMod"
        custom_dir.mkdir(parents=True, exist_ok=True)

        self.app.project_folder = custom_dir
        self.app.bepinex_project_folder = custom_dir
        self.app._save_user_prefs(silent=True)

        # Read config file directly
        with open(misora_app.CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.assertIn("project_folder", cfg)
        self.assertIn("bepinex_project_folder", cfg)
        self.assertEqual(cfg["project_folder"], str(custom_dir))
        self.assertEqual(cfg["bepinex_project_folder"], str(custom_dir))

    def test_04_framework_agnostic_folder_resolution(self):
        """Framework-agnostic helpers discover Text and RedirectedResources across structures."""
        # Create MelonLoader / custom style hierarchy
        ml_proj = self.tmp_dir / "MelonProject"
        ml_user_data = ml_proj / "UserData"
        ml_text = ml_user_data / "Text"
        ml_redirect = ml_user_data / "RedirectedResources"
        ml_text.mkdir(parents=True, exist_ok=True)
        ml_redirect.mkdir(parents=True, exist_ok=True)

        self.app.project_folder = ml_proj
        self.app.bepinex_project_folder = ml_proj

        # Check candidate search logic for text folder
        candidates_text = [
            ml_proj / "Text",
            ml_proj if ml_proj.name.lower() == "text" else None,
            ml_proj / "Translation" / "en" / "Text",
            ml_proj / "UserData" / "Text",
        ]
        found_text = next((c for c in candidates_text if c and c.is_dir()), None)
        self.assertEqual(found_text, ml_text)

        # Check candidate search logic for redirected resources
        candidates_res = [
            ml_proj / "RedirectedResources",
            ml_proj.parent / "RedirectedResources",
            ml_proj / "Translation" / "en" / "RedirectedResources",
            ml_proj / "UserData" / "RedirectedResources",
            ml_proj / "Mods" / "RedirectedResources",
        ]
        found_res = next((c for c in candidates_res if c and c.is_dir()), None)
        self.assertEqual(found_res, ml_redirect)

    def test_05_dnd_folder_scope_actions(self):
        """DnD folder actions: setting folder scope sets selected_search_folder and updates UI."""
        folder_a = self.tmp_dir / "FolderA"
        folder_a.mkdir(parents=True, exist_ok=True)

        # Simulate user choosing 'No' (set search scope only)
        self.app.selected_search_folder = folder_a
        self.app.folder_path_var.set(str(folder_a))
        self.app.scope_var.set("folder")
        self.app._sync_scope_widgets()

        self.assertEqual(self.app.scope_var.get(), "folder")
        self.assertEqual(self.app.folder_path_var.get(), str(folder_a))
        self.assertEqual(self.app.folder_path_entry.cget("state"), "normal")

    def test_06_process_opened_folder_empty(self):
        """Opening a folder with no story files sets search scope without opening files."""
        empty_folder = self.tmp_dir / "EmptyFolder"
        empty_folder.mkdir(parents=True, exist_ok=True)

        self.app._process_opened_folder(empty_folder, source_label="Test")
        self.assertEqual(self.app.scope_var.get(), "folder")
        self.assertEqual(self.app.selected_search_folder, empty_folder)
        self.assertEqual(self.app.folder_path_var.get(), str(empty_folder))

    def test_07_process_opened_folder_single_file(self):
        """Opening a folder with exactly 1 story file opens it and sets scope to current."""
        one_folder = self.tmp_dir / "OneStoryFolder"
        one_folder.mkdir(parents=True, exist_ok=True)
        txt_file = one_folder / "test_story.txt"
        txt_file.write_text("Test line=Translated\n", encoding="utf-8")

        self.app._process_opened_folder(one_folder, source_label="Test")
        self.assertEqual(self.app.scope_var.get(), "current")
        self.assertEqual(self.app.current_file_path, txt_file)

    def test_08_line_numbers_and_ruler_toggles(self):
        """Line numbers gutter and horizontal column ruler toggle visibility correctly."""
        # Toggle line numbers OFF
        self.app.var_show_line_numbers.set(False)
        self.app._on_toggle_line_numbers()
        self.assertFalse(self.app.show_line_numbers)
        self.assertFalse(self.app._is_widget_packed(self.app.gutter_clean))

        # Toggle line numbers ON
        self.app.var_show_line_numbers.set(True)
        self.app._on_toggle_line_numbers()
        self.assertTrue(self.app.show_line_numbers)
        self.assertTrue(self.app._is_widget_packed(self.app.gutter_clean))

        # Toggle column ruler OFF
        self.app.var_show_column_ruler.set(False)
        self.app._on_toggle_column_ruler()
        self.assertFalse(self.app.show_column_ruler)
        self.assertFalse(self.app._is_widget_packed(self.app.ruler_clean))

        # Toggle column ruler ON
        self.app.var_show_column_ruler.set(True)
        self.app._on_toggle_column_ruler()
        self.assertTrue(self.app.show_column_ruler)
        self.assertTrue(self.app._is_widget_packed(self.app.ruler_clean))

    def test_09_undo_redo_shortcuts_and_dialogue_binding(self):
        """Ctrl+Z and Ctrl+Y are intercepted by _shortcut_undo and _shortcut_redo on dialogue."""
        res_undo = self.app._shortcut_undo()
        self.assertEqual(res_undo, "break")
        res_redo = self.app._shortcut_redo()
        self.assertEqual(res_redo, "break")

    def test_10_theme_swatches_and_commit_hex(self):
        """Theme swatches and hex entries reflect updated color on commit."""
        test_color = "#334455"
        self.app._theme_hex_vars["bg_dark"].set(test_color)
        self.app._commit_theme_hex("bg_dark")
        self.assertEqual(self.app.theme["bg_dark"], test_color)
        self.assertEqual(self.app._theme_swatch_buttons["bg_dark"].cget("bg"), test_color)

    def test_11_ribbon_compact_buttons_and_undo_redo(self):
        """Ribbon buttons are compact (<= 500px total) and explicit Undo/Redo buttons exist."""
        self.assertTrue(hasattr(self.app, "btn_ribbon_undo"))
        self.assertTrue(hasattr(self.app, "btn_ribbon_redo"))
        self.assertEqual(self.app.btn_ribbon_undo.cget("text"), "↶")
        self.assertEqual(self.app.btn_ribbon_redo.cget("text"), "↷")

        ribbon = self.app.btn_ribbon_swatch.master
        self.app.update_idletasks()
        total_w = ribbon.winfo_reqwidth()
        self.assertLessEqual(total_w, 550, f"Ribbon width {total_w}px exceeded 550px limit")

    def test_12_inject_box_no_trailing_spaces(self):
        """Injecting text into multi-segment box does not add trailing spaces."""
        recs = [
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "First line"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "\n"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Second line"]),
        ]
        doc = StoryDocument(recs)
        self.assertEqual(len(doc.boxes), 1)
        self.assertEqual(len(doc.boxes[0].segs), 3)

        doc.inject_box(0, "Pecorine", "New Dialogue Text")
        clean = doc.boxes[0].clean_text
        self.assertEqual(clean, "New Dialogue Text")
        self.assertFalse(clean.endswith(" "), "clean_text should not end with trailing space")

    def test_13_editor_clean_one_pixel_borders(self):
        """Text editors have highlightthickness=0 for clean 1px border."""
        self.assertEqual(int(self.app.txt_dialogue.cget("highlightthickness")), 0)
        self.assertEqual(int(self.app.txt_continuous.cget("highlightthickness")), 0)
        self.assertEqual(int(self.app.txt_raw.cget("highlightthickness")), 0)
        self.assertEqual(int(self.app.txt_dialogue.cget("bd")), 1)

    def test_14_box0_metadata_navigation_and_ui(self):
        """Navigating < Prev from Box 1 enters Box 0 (Story Metadata) with populated fields."""
        bundle_path = Path(__file__).resolve().parent.parent / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            self.skipTest(f"Bundle not found: {bundle_path}")

        self.app.open_file(bundle_path)
        self.assertEqual(self.app.current_box_idx, 0)
        self.assertFalse(self.app.is_box0_active)
        self.assertIn("Box: 1 / 39", self.app.lbl_box_counter.cget("text"))

        # Navigate to Box 0 via Prev button
        self.app.on_prev_box()
        self.assertTrue(self.app.is_box0_active)
        self.assertIn("Box: 0 / 39 (Story Metadata)", self.app.lbl_box_counter.cget("text"))
        self.assertEqual(self.app.speaker_var.get(), "")
        self.assertEqual(str(self.app.entry_speaker.cget("state")), "disabled")

        # Check fields populated
        self.assertEqual(self.app.var_box0_title.get(), "Hiyori Episode 5")
        self.assertEqual(self.app.var_box0_subtitle.get(), "The Tail's Off-Limits!")
        self.assertIn("sparring partner", self.app.txt_box0_summary.get("1.0", "end-1c"))

        # Navigate back to Box 1 via Next button
        self.app.on_next_box()
        self.assertFalse(self.app.is_box0_active)
        self.assertEqual(self.app.current_box_idx, 0)
        self.assertIn("Box: 1 / 39", self.app.lbl_box_counter.cget("text"))

    def test_15_box0_metadata_editing_and_undo_redo(self):
        """Editing Box 0 metadata records undo operations and correctly reverts/re-applies."""
        bundle_path = Path(__file__).resolve().parent.parent / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            self.skipTest(f"Bundle not found: {bundle_path}")

        self.app.open_file(bundle_path)
        self.app.on_prev_box()
        self.assertTrue(self.app.is_box0_active)

        orig_title = self.app.var_box0_title.get()
        orig_summary = self.app.txt_box0_summary.get("1.0", "end-1c")

        # Edit Title
        self.app.var_box0_title.set("Custom Episode 5 Title")
        self.app._on_box0_metadata_edited()
        self.assertTrue(self.app.is_dirty)
        self.assertEqual(self.app.current_doc.get_metadata()["title"], "Custom Episode 5 Title")

        # Edit Summary
        self.app.txt_box0_summary.delete("1.0", "end")
        self.app.txt_box0_summary.insert("1.0", "Brand new summary text.")
        self.app._on_box0_metadata_edited()
        self.assertEqual(self.app.current_doc.get_metadata()["summary"], "Brand new summary text.")

        # Undo Summary edit
        self.app.on_undo()
        self.assertEqual(self.app.current_doc.get_metadata()["summary"], orig_summary)

        # Undo Title edit
        self.app.on_undo()
        self.assertEqual(self.app.current_doc.get_metadata()["title"], orig_title)

        # Redo Title edit
        self.app.on_redo()
        self.assertEqual(self.app.current_doc.get_metadata()["title"], "Custom Episode 5 Title")

    def test_16_box0_continuous_view_rendering(self):
        """Continuous View renders Box #000 at top and allows selection."""
        bundle_path = Path(__file__).resolve().parent.parent / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            self.skipTest(f"Bundle not found: {bundle_path}")

        self.app.open_file(bundle_path)
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()

        # In Box Card Stream, Box 0 is rendered in its dedicated metadata card (-1)
        self.assertIn(-1, self.app._card_widgets)
        card0 = self.app._card_widgets[-1]
        self.assertEqual(card0["lbl_badge"].cget("text"), "◆ [BOX #000]")
        self.assertEqual(card0["lbl_title"].cget("text"), "[STORY METADATA & SYNOPSIS]")
        self.assertIn("sparring partner", card0["txt"].get("1.0", "end-1c"))

        # Test selecting Box 0 in Continuous View
        self.app._focus_continuous_box(-1, move_cursor=True)
        self.assertTrue(self.app.is_box0_active)
        self.assertIn("Box: 0 / 39 (Story Metadata)", self.app.lbl_box_counter.cget("text"))

        # Switch back to Page View
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()

    def test_17_search_finds_metadata_and_jumps_to_box0(self):
        """Search engine finds matches in Title/Summary and jumping activates Box 0."""
        bundle_path = Path(__file__).resolve().parent.parent / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            self.skipTest(f"Bundle not found: {bundle_path}")

        self.app.open_file(bundle_path)
        opts = SearchOptions(query="martial arts")
        results = self.app.search_engine.search_file(bundle_path, opts)

        meta_results = [r for r in results if r.box_index == -1]
        self.assertGreaterEqual(len(meta_results), 1)
        r = meta_results[0]
        self.assertEqual(r.speaker, "[Metadata: Summary]")

        # Simulate selecting result
        self.app.active_search_results = [r]
        self.app._selected_result_idx = 0
        self.app._select_result_index(0, jump=True)

        self.assertTrue(self.app.is_box0_active)
        self.assertIn("Box: 0 / 39 (Story Metadata)", self.app.lbl_box_counter.cget("text"))

    def test_18_custom_theme_apply(self):
        """Setting preset to Custom and clicking apply commits custom colors properly."""
        self.app.var_preset.set("Custom")
        self.app._apply_theme_preset("Custom")
        self.assertIn("Applied custom theme colors", self.app.lbl_status.cget("text"))

    def test_19_opened_files_context_menu_close_others_and_all(self):
        """Right-click actions Close Others, Close All Unmodified, Close All work cleanly."""
        f1 = Path(tempfile.gettempdir()) / "test_doc1.txt"
        f2 = Path(tempfile.gettempdir()) / "test_doc2.txt"
        f3 = Path(tempfile.gettempdir()) / "test_doc3.txt"
        f1.write_text("Doc 1 content", encoding="utf-8")
        f2.write_text("Doc 2 content", encoding="utf-8")
        f3.write_text("Doc 3 content", encoding="utf-8")

        try:
            self.app.open_file(f1)
            self.app.open_file(f2)
            self.app.open_file(f3)
            self.assertEqual(len(self.app.open_documents), 3)

            # Close Others keeping f2
            self.app.close_others(f2)
            self.assertEqual(len(self.app.open_documents), 1)
            self.assertIn(f2, self.app.open_documents)

            # Re-open f1 and mark it dirty
            self.app.open_file(f1)
            self.app.is_dirty = True
            self.app.open_documents[f1]["dirty"] = True

            # Close all unmodified (should close f2, keep dirty f1)
            self.app.close_all_unmodified()
            self.assertEqual(len(self.app.open_documents), 1)
            self.assertIn(f1, self.app.open_documents)

            # Clean up dirty flag to avoid blocking prompt
            self.app.is_dirty = False
            self.app.open_documents[f1]["dirty"] = False
            self.app.close_file(f1)
            self.assertEqual(len(self.app.open_documents), 0)
        finally:
            for f in (f1, f2, f3):
                if f.exists():
                    f.unlink()

    def test_20_seamless_cursor_and_box_sync(self):
        """Switching between Page View and Continuous View preserves exact box and character offset."""
        bundle_path = Path(__file__).resolve().parent.parent / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            self.skipTest(f"Bundle not found: {bundle_path}")

        self.app.open_file(bundle_path)
        # Select Box 2 (0-indexed 1)
        self.app.current_box_idx = 1
        self.app._update_views()

        # Position caret at character 5 in Page View
        self.app.txt_dialogue.mark_set("insert", "1.0 + 5c")

        # Toggle to Continuous View
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()

        self.assertEqual(self.app.current_box_idx, 1)

        # Toggle back to Page View
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()

        self.assertEqual(self.app.current_box_idx, 1)
        ins = self.app.txt_dialogue.index("insert")
        self.assertTrue(ins.startswith("1.") or ins.startswith("2."))

    def test_21_plain_text_editing_and_save_continuous_and_page(self):
        """Plain text files track dirty state in Continuous and Page View and save with backup."""
        txt_path = Path(tempfile.gettempdir()) / "test_plain_edit.txt"
        txt_path.write_text("Hello World\nLine 2\n", encoding="utf-8")

        try:
            self.app.open_file(txt_path)
            self.assertFalse(self.app.is_dirty)

            # Edit in Page View
            self.app.txt_dialogue.insert("end-1c", "Extra Page Text\n")
            self.app._on_dialogue_edited()
            self.assertTrue(self.app.is_dirty)

            # Save in Page View
            self.app.on_save()
            self.assertFalse(self.app.is_dirty)
            saved_content = txt_path.read_text(encoding="utf-8")
            self.assertIn("Extra Page Text", saved_content)

            # Toggle Continuous View
            self.app.var_continuous_view.set(True)
            self.app._on_toggle_continuous_view()

            # Edit in Continuous View
            self.app.txt_continuous.insert("end-1c", "Extra Continuous Text\n")
            self.app._sync_continuous_box_from_widget()
            self.assertTrue(self.app.is_dirty)

            # Save in Continuous View
            self.app.on_save()
            self.assertFalse(self.app.is_dirty)
            saved_content = txt_path.read_text(encoding="utf-8")
            self.assertIn("Extra Continuous Text", saved_content)

            # Revert to Page View
            self.app.var_continuous_view.set(False)
            self.app._on_toggle_continuous_view()
        finally:
            if txt_path.exists():
                txt_path.unlink()

    def test_22_single_root_splash_speaker_and_continuous_binding(self):
        """Single-root Toplevel splash architecture preserves StringVar and BooleanVar bindings."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return

        splash_app = misora_app.MisoraApp(restore_session=False, show_splash=True)
        splash_app.withdraw()
        try:
            splash_app.open_file(bundle_path)
            # The speaker entry widget must NOT be empty string!
            self.assertEqual(splash_app.entry_speaker.get(), "Narration")
            self.assertEqual(splash_app.speaker_var.get(), "Narration")

            # Navigating next must update entry widget
            splash_app.on_next_box()
            self.assertEqual(splash_app.entry_speaker.get(), "Hiyori")
            self.assertEqual(splash_app.speaker_var.get(), "Hiyori")

            # Continuous View checkbox must toggle and render correctly
            splash_app.var_continuous_view.set(True)
            splash_app._on_toggle_continuous_view()
            self.assertGreater(len(splash_app.txt_continuous.get("1.0", "end-1c")), 10)
            self.assertEqual(len(splash_app._card_widgets), 40)
        finally:
            splash_app.destroy()

    def test_23_paste_cross_box_smart_plain_text(self):
        """Smart Plain Text paste updates consecutive boxes and preserves character speaker names."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return
        self.app.open_file(bundle_path)

        orig_spk0 = self.app.current_doc.boxes[0].speaker
        orig_spk1 = self.app.current_doc.boxes[1].speaker
        orig_spk2 = self.app.current_doc.boxes[2].speaker

        # Mock clipboard and confirmation dialogs
        clip_content = "Translated paragraph 1\n\nTranslated paragraph 2\n\nTranslated paragraph 3"
        self.app.clipboard_get = lambda: clip_content
        orig_ask = misora_app.messagebox.askyesno
        orig_info = misora_app.messagebox.showinfo
        misora_app.messagebox.askyesno = lambda *args, **kwargs: True
        misora_app.messagebox.showinfo = lambda *args, **kwargs: None

        try:
            self.app.on_paste_cross_box()
            doc = self.app.current_doc
            self.assertEqual(doc.boxes[0].clean_text, "Translated paragraph 1")
            self.assertEqual(doc.boxes[1].clean_text, "Translated paragraph 2")
            self.assertEqual(doc.boxes[2].clean_text, "Translated paragraph 3")
            # Original speakers MUST be preserved
            self.assertEqual(doc.boxes[0].speaker, orig_spk0)
            self.assertEqual(doc.boxes[1].speaker, orig_spk1)
            self.assertEqual(doc.boxes[2].speaker, orig_spk2)

            # Undo reverts all 3 boxes simultaneously
            self.app.on_undo()
            self.assertNotEqual(doc.boxes[0].clean_text, "Translated paragraph 1")
            self.assertNotEqual(doc.boxes[1].clean_text, "Translated paragraph 2")
            self.assertNotEqual(doc.boxes[2].clean_text, "Translated paragraph 3")

            # Redo restores all 3 boxes simultaneously
            self.app.on_redo()
            self.assertEqual(doc.boxes[0].clean_text, "Translated paragraph 1")
            self.assertEqual(doc.boxes[1].clean_text, "Translated paragraph 2")
            self.assertEqual(doc.boxes[2].clean_text, "Translated paragraph 3")
        finally:
            misora_app.messagebox.askyesno = orig_ask
            misora_app.messagebox.showinfo = orig_info

    def test_24_paste_cross_box_delimited(self):
        """Delimited script paste updates both speaker and dialogue across boxes."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return
        self.app.open_file(bundle_path)

        clip_content = (
            "=== [BOX:0|Speaker:Kokkoro] ===\n"
            "Master, breakfast is ready!\n\n"
            "=== [BOX:1|Speaker:Yuuki] ===\n"
            "Thank you Kokkoro!"
        )
        self.app.clipboard_get = lambda: clip_content
        orig_ask = misora_app.messagebox.askyesno
        orig_info = misora_app.messagebox.showinfo
        misora_app.messagebox.askyesno = lambda *args, **kwargs: True
        misora_app.messagebox.showinfo = lambda *args, **kwargs: None

        try:
            self.app.on_paste_cross_box()
            doc = self.app.current_doc
            self.assertEqual(doc.boxes[0].speaker, "Kokkoro")
            self.assertEqual(doc.boxes[0].clean_text, "Master, breakfast is ready!")
            self.assertEqual(doc.boxes[1].speaker, "Yuuki")
            self.assertEqual(doc.boxes[1].clean_text, "Thank you Kokkoro!")
        finally:
            misora_app.messagebox.askyesno = orig_ask
            misora_app.messagebox.showinfo = orig_info


    def test_25_continuous_card_stream_edit_sync_and_retention(self):
        """Edits in Card 5 are committed and view focus/caret are retained when toggling views."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return
        self.app.open_file(bundle_path)

        # Switch to Continuous View
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()

        # Focus Card 5 and insert extra text
        card5_txt = self.app._card_widgets[5]["txt"]
        card5_txt.insert("end-1c", " [Tested Card Edit]")
        self.app._on_card_text_edited(5, card5_txt)
        self.assertTrue(self.app.is_dirty)

        # Focus Card 5 at char offset 10
        self.app._focus_continuous_box(5, move_cursor=True, char_offset=10)
        self.assertEqual(self.app.current_box_idx, 5)

        # Toggle back to Single Box View
        self.app.var_continuous_view.set(False)
        self.app._on_toggle_continuous_view()

        # View must remain on Box 5 and contain the edit
        self.assertEqual(self.app.current_box_idx, 5)
        self.assertIn("Box: 6 / 39", self.app.lbl_box_counter.cget("text"))
        self.assertIn("[Tested Card Edit]", self.app.txt_dialogue.get("1.0", "end-1c"))

        # Toggle back to Continuous View
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.assertEqual(self.app.current_box_idx, 5)

    def test_26_paste_script_triple_enter(self):
        """Triple-enter script copy and paste distributes cleanly across boxes preserving character names."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return
        self.app.open_file(bundle_path)

        orig_spk0 = self.app.current_doc.boxes[0].speaker
        orig_spk1 = self.app.current_doc.boxes[1].speaker
        orig_spk2 = self.app.current_doc.boxes[2].speaker

        # Copy all boxes separated by triple enter
        self.app.on_copy_script_triple_enter()
        copied = self.app.clipboard_get()
        self.assertIn("\n\n\n", copied)
        self.assertNotIn("=== [BOX:", copied)

        # Paste 3 triple-enter blocks
        clip_content = "Triple Block 1\n\n\nTriple Block 2 with\ninternal newline\n\n\nTriple Block 3"
        self.app.clipboard_get = lambda: clip_content
        orig_ask = misora_app.messagebox.askyesno
        orig_info = misora_app.messagebox.showinfo
        misora_app.messagebox.askyesno = lambda *args, **kwargs: True
        misora_app.messagebox.showinfo = lambda *args, **kwargs: None

        try:
            self.app.current_box_idx = 0
            self.app.on_paste_cross_box()

            doc = self.app.current_doc
            self.assertEqual(doc.boxes[0].speaker, orig_spk0)
            self.assertEqual(doc.boxes[0].clean_text, "Triple Block 1")
            self.assertEqual(doc.boxes[1].speaker, orig_spk1)
            self.assertEqual(doc.boxes[1].clean_text, "Triple Block 2 with\ninternal newline")
            self.assertEqual(doc.boxes[2].speaker, orig_spk2)
            self.assertEqual(doc.boxes[2].clean_text, "Triple Block 3")
        finally:
            misora_app.messagebox.askyesno = orig_ask
            misora_app.messagebox.showinfo = orig_info

    def test_27_box0_speaker_disabled_and_protected(self):
        """On Box 0, speaker controls are disabled and dropdown menu cannot alter story text."""
        bundle_path = MISORA_DIR / "storydata_1001005.unity3d"
        if not bundle_path.exists():
            return
        self.app.open_file(bundle_path)

        # Navigate to Box 0
        self.app.on_prev_box()
        self.assertTrue(self.app.is_box0_active)
        self.assertEqual(self.app.speaker_var.get(), "")
        self.assertEqual(str(self.app.entry_speaker.cget("state")), "disabled")
        self.assertEqual(str(self.app.btn_speaker_dropdown.cget("state")), "disabled")

        # Attempt to click speaker dropdown or assign speaker
        self.app._on_speaker_dropdown_clicked()
        self.app._assign_speaker_to_current_box("Kokkoro")
        self.assertEqual(self.app.speaker_var.get(), "")

        # Box 1 speaker must not have changed
        self.app.on_next_box()
        self.assertFalse(self.app.is_box0_active)
        self.assertEqual(self.app.speaker_var.get(), "Narration")


if __name__ == "__main__":
    unittest.main()
