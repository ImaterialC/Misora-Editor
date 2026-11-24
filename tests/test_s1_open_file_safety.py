#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
MISORA_DIR = TESTS_DIR.parent
if str(MISORA_DIR) not in sys.path:
    sys.path.insert(0, str(MISORA_DIR))

spec = importlib.util.spec_from_file_location("misora_s1", MISORA_DIR / "misora.py")
misora = importlib.util.module_from_spec(spec)
sys.modules["misora_s1"] = misora
spec.loader.exec_module(misora)

from core.story_ast import Record, StoryDocument


BUNDLE = MISORA_DIR / "storydata_1001005.unity3d"


class TestS1OpenFileSafety(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s1_"))
        self._patches = [
            patch.object(misora.messagebox, "askyesno", return_value=True),
            patch.object(misora.messagebox, "showinfo", return_value=None),
            patch.object(misora.messagebox, "showwarning", return_value=None),
            patch.object(misora.messagebox, "showerror", return_value=None),
            patch.object(misora.messagebox, "askokcancel", return_value=True),
        ]
        for p in self._patches:
            p.start()
        self._orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_dir / "misora_config.json"
        self.app = misora.MisoraApp(restore_session=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        for p in self._patches:
            p.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        misora.CONFIG_PATH = self._orig_config_path

    def _open_a_bundle(self):
        if not BUNDLE.exists():
            self.skipTest("Bundle fixture not found")
        try:
            import UnityPy  # noqa: F401
        except Exception:
            self.skipTest("UnityPy unavailable")
        self.app.open_file(BUNDLE)
        self.assertIsNotNone(self.app.current_doc)

    def _make_plain_text(self, name, content="hello"):
        path = self.tmp_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_1_failed_bundle_load_preserves_document_a(self):
        self._open_a_bundle()
        path_a = self.app.current_file_path
        doc_a = self.app.current_doc
        env_a = self.app.current_unity_env
        obj_a = self.app.current_text_obj

        self.app.is_dirty = True
        self.app._locked_boxes.add(3)
        self.app._modified_boxes.add(4)
        self.app._original_box_texts = {77: "source-cache"}
        self.app._plain_text_content = "nondefault"
        self.app.title("A Custom Title")
        title_a = str(self.app.title())
        recent_a = list(self.app.recent_files)
        open_documents_a = dict(self.app.open_documents)

        path_b = self.tmp_dir / "failure.unity3d"
        path_b.write_bytes(b"existing bundle bytes")

        with patch.object(misora, "load_bundle_story", side_effect=RuntimeError("forced bundle failure")):
            self.app.open_file(path_b)

        self.assertEqual(self.app.current_file_path, path_a)
        self.assertIs(self.app.current_doc, doc_a)
        self.assertIs(self.app.current_unity_env, env_a)
        self.assertIs(self.app.current_text_obj, obj_a)
        self.assertTrue(self.app.is_dirty)
        self.assertEqual(self.app._locked_boxes, {3})
        self.assertEqual(self.app._modified_boxes, {4})
        self.assertEqual(self.app._original_box_texts, {77: "source-cache"})
        self.assertEqual(self.app._plain_text_content, "nondefault")
        self.assertEqual(str(self.app.title()), title_a)
        self.assertEqual(self.app.recent_files, recent_a)
        self.assertEqual(self.app.open_documents, open_documents_a)
        self.assertNotIn(path_b, self.app.open_documents)

    def test_2_invalid_utf8_real_bytes_preserves_document_a(self):
        self._open_a_bundle()
        path_a = self.app.current_file_path
        doc_a = self.app.current_doc
        env_a = self.app.current_unity_env
        obj_a = self.app.current_text_obj
        dirty_a = self.app.is_dirty
        locked_a = set(self.app._locked_boxes)
        modified_a = set(self.app._modified_boxes)
        source_a = dict(self.app._original_box_texts)
        title_a = str(self.app.title())
        recent_a = list(self.app.recent_files)
        cache_a = dict(self.app.open_documents)

        path_b = self.tmp_dir / "invalid.txt"
        path_b.write_bytes(b"hello\x80\xffworld")
        self.app.open_file(path_b)

        self.assertEqual(self.app.current_file_path, path_a)
        self.assertIs(self.app.current_doc, doc_a)
        self.assertIs(self.app.current_unity_env, env_a)
        self.assertIs(self.app.current_text_obj, obj_a)
        self.assertEqual(self.app.is_dirty, dirty_a)
        self.assertEqual(self.app._locked_boxes, locked_a)
        self.assertEqual(self.app._modified_boxes, modified_a)
        self.assertEqual(self.app._original_box_texts, source_a)
        self.assertEqual(str(self.app.title()), title_a)
        self.assertEqual(self.app.recent_files, recent_a)
        self.assertEqual(self.app.open_documents, cache_a)
        self.assertNotIn(path_b, self.app.open_documents)

    def test_3_malformed_v2_parse_failure_preserves_document_a(self):
        self._open_a_bundle()
        path_a = self.app.current_file_path
        doc_a = self.app.current_doc
        title_a = str(self.app.title())
        recent_a = list(self.app.recent_files)
        cache_a = dict(self.app.open_documents)

        path_b = self.tmp_dir / "broken.story.txt"
        path_b.write_text("#!priconne-story v2\nmalformed", encoding="utf-8")

        with patch.object(misora.StoryDocument, "from_v2_text", side_effect=ValueError("forced v2 parse failure")):
            self.app.open_file(path_b)

        self.assertEqual(self.app.current_file_path, path_a)
        self.assertIs(self.app.current_doc, doc_a)
        self.assertEqual(str(self.app.title()), title_a)
        self.assertEqual(self.app.recent_files, recent_a)
        self.assertEqual(self.app.open_documents, cache_a)
        self.assertNotIn(path_b, self.app.open_documents)

    def test_4_successful_load_regression(self):
        plain = self._make_plain_text("valid.txt", "ordinary utf-8")
        self.app.open_file(plain)
        self.assertEqual(self.app.current_file_path, plain)
        self.assertIsNone(self.app.current_doc)
        self.assertEqual(self.app._plain_text_content, "ordinary utf-8")

        doc = StoryDocument([
            Record("print", "N", ["valid-v2"]),
        ])
        v2 = self.tmp_dir / "valid.v2.txt"
        v2.write_text(doc.to_v2_text(), encoding="utf-8")
        self.app.open_file(v2)
        self.assertEqual(self.app.current_file_path, v2)
        self.assertIsNotNone(self.app.current_doc)

        if BUNDLE.exists():
            try:
                import UnityPy  # noqa: F401
            except Exception:
                pass
            else:
                self.app.open_file(BUNDLE)
                self.assertEqual(self.app.current_file_path, BUNDLE)
                self.assertIsNotNone(self.app.current_doc)

    def test_5_pending_edit_flush_on_fresh_cache_and_failure(self):
        self._open_a_bundle()
        path_a = self.app.current_file_path
        doc_a = self.app.current_doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = False
        self.app._sync_clean_view_to_current_box()

        old_text = doc_a.boxes[0].clean_text
        edited_text = old_text + " [fresh edit]"
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", edited_text)

        path_b = self._make_plain_text("fresh-b.txt", "fresh target")
        self.app.open_file(path_b)
        self.assertEqual(doc_a.boxes[0].clean_text, edited_text)
        self.assertEqual(self.app.current_file_path, path_b)

        self.app.open_file(path_a)
        self.assertIs(self.app.current_doc, doc_a)
        self.assertEqual(doc_a.boxes[0].clean_text, edited_text)

        cache_doc_a = self.app.current_doc
        self.app.current_box_idx = 0
        self.app.is_box0_active = False
        self.app._sync_clean_view_to_current_box()
        cache_edited_text = edited_text + " [cache edit]"
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", cache_edited_text)

        path_c = self._make_plain_text("cache-c.txt", "cache target")
        self.app.open_file(path_c)
        self.assertEqual(cache_doc_a.boxes[0].clean_text, cache_edited_text)

        self.app.open_file(path_a)
        self.assertIs(self.app.current_doc, cache_doc_a)
        self.assertEqual(cache_doc_a.boxes[0].clean_text, cache_edited_text)

        self.app._sync_clean_view_to_current_box()
        failure_text = cache_edited_text + " [pending failure]"
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", failure_text)
        failure_path = self.tmp_dir / "failure.story.txt"
        failure_path.write_text("#!priconne-story v2\nbad", encoding="utf-8")

        with patch.object(misora.StoryDocument, "from_v2_text", side_effect=ValueError("failure")):
            self.app.open_file(failure_path)

        self.assertIs(self.app.current_doc, cache_doc_a)
        self.assertEqual(self.app.current_file_path, path_a)
        self.assertEqual(self.app.txt_dialogue.get("1.0", "end-1c"), failure_text)
        self.assertEqual(cache_doc_a.boxes[0].clean_text, cache_edited_text)

    def test_6_failed_open_keeps_save_target_a(self):
        path_a = self._make_plain_text("save-target-a.txt", "document A")
        self.app.open_file(path_a)
        path_b = self.tmp_dir / "invalid-save-target.txt"
        path_b.write_bytes(b"bad\x80bytes")
        b_before = path_b.read_bytes()

        self.app.open_file(path_b)

        self.assertEqual(self.app.current_file_path, path_a)
        self.app.on_save()
        self.assertEqual(self.app.current_file_path, path_a)
        self.assertEqual(path_b.read_bytes(), b_before)

    def test_7_continuous_view_box0_edit_flush_on_switch(self):
        self._open_a_bundle()
        path_a = self.app.current_file_path
        doc_a = self.app.current_doc
        self.assertTrue(doc_a.has_metadata())

        # Switch to Continuous View and focus Box 0
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        self.assertIn(-1, self.app._card_widgets)
        c0_txt = self.app._card_widgets[-1]["txt"]
        self.app._on_card_focus_in(-1)
        self.assertTrue(self.app.is_box0_active)

        # Edit synopsis in Continuous View card without triggering KeyRelease
        updated_synopsis = "Updated Continuous Synopsis Before Switch"
        c0_txt.delete("1.0", "end")
        c0_txt.insert("1.0", updated_synopsis)

        # Switch to a different file (fresh plain text)
        path_b = self._make_plain_text("fresh-target.txt", "target content")
        self.app.open_file(path_b)

        # Assert document A was flushed with updated synopsis before switch
        self.assertEqual(doc_a.get_metadata().get("summary"), updated_synopsis)
        self.assertEqual(self.app.current_file_path, path_b)

        # Switch back to document A from cache
        self.app.open_file(path_a)
        self.assertIs(self.app.current_doc, doc_a)
        self.assertEqual(doc_a.get_metadata().get("summary"), updated_synopsis)


if __name__ == "__main__":
    unittest.main()
