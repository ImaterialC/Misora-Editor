import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import misora
from core.story_ast import Record, StoryDocument
from misora import MisoraApp


def _write_synthetic_v2(path: Path, speaker: str = "Alice", text: str = "Hello world") -> Path:
    doc = StoryDocument()
    doc.records = [
        Record(cmd_id=35, cmd_name="tag", args=["Box 0 Summary"]),
        Record(cmd_id=6, cmd_name="print", args=[speaker, text]),
    ]
    path.write_text(doc.to_v2_text(), encoding="utf-8")
    return path


class _T01AppTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_config_path = misora.CONFIG_PATH
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_path = self.temp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")
        misora.CONFIG_PATH = self.config_path
        self.fp1 = _write_synthetic_v2(self.temp_dir / "story1.v2.txt", "Alice", "Line one")
        self.fp2 = _write_synthetic_v2(self.temp_dir / "story2.v2.txt", "Bob", "Line two")
        self.app = None

    def tearDown(self):
        try:
            if self.app is not None:
                try:
                    self.app.destroy()
                except Exception:
                    pass
        finally:
            misora.CONFIG_PATH = self._orig_config_path
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _assert_top_view_order(self, active_widget):
        top_view = self.app.gd_scroll_wrap.master
        self.assertIs(self.app.empty_state_frame.master, top_view)
        self.assertIs(self.app.continuous_wrap.master, top_view)
        slaves = top_view.pack_slaves()
        self.assertIn(self.app.speaker_view_row, slaves)
        if hasattr(self.app, "ribbon_actions_row") and self.app.ribbon_actions_row.winfo_manager() == "pack":
            self.assertIn(self.app.ribbon_actions_row, slaves)
            self.assertGreater(slaves.index(active_widget), slaves.index(self.app.ribbon_actions_row))
        self.assertIs(slaves[-1], active_widget)
        self.assertGreater(slaves.index(active_widget), slaves.index(self.app.speaker_view_row))
        for other in (self.app.empty_state_frame, self.app.gd_scroll_wrap, self.app.continuous_wrap):
            if other is not active_widget:
                self.assertNotIn(other, slaves)


class TestT01DefectProbes(_T01AppTestBase):
    def test_probe_1_state1_startup_zero_docs_no_dual_pack(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "pack")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.app.deiconify()
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 1)
            self.assertGreater(self.app.empty_state_frame.winfo_height(), 1)
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 0)
            self.assertEqual(self.app.continuous_wrap.winfo_ismapped(), 0)

    def test_probe_2_state4_deferred_restore_splash_two_docs(self):
        self.config_path.write_text(
            json.dumps({"saved_opened_files": [str(self.fp1), str(self.fp2)], "saved_active_file": str(self.fp1)}),
            encoding="utf-8",
        )
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=True, restore_session=True)
            for _ in range(20):
                self.app.update()
                if len(self.app.open_documents) == 2 and getattr(self.app, "_rpt_done", False):
                    break
            self.app.deiconify()
            self.app.update()
            self.assertEqual(len(self.app.open_documents), 2)
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "pack")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 0)
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 1)
            self.assertGreater(self.app.gd_scroll_wrap.winfo_height(), 1)

    def test_probe_3_withdrawn_open_file_unpacks_empty_state(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.withdraw()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "pack")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.app.deiconify()
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 0)
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 1)

    def test_probe_4_withdrawn_continuous_mode_open_file_unpacks_both(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.withdraw()
            self.app.update()
            self.app.var_continuous_view.set(True)
            self.app.open_file(self.fp1)
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "pack")
            self.app.deiconify()
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 0)
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 0)
            self.assertEqual(self.app.continuous_wrap.winfo_ismapped(), 1)


class TestT01RegressionGuards(_T01AppTestBase):
    def test_guard_1_state2_open_one_doc_box1_dialogue(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "pack")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 1)
            self.assertGreater(self.app.gd_scroll_wrap.winfo_height(), 1)
            self._assert_top_view_order(self.app.gd_scroll_wrap)

    def test_guard_2_state3_two_open_docs_switch_and_close_one(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.open_file(self.fp2)
            self.app.open_file(self.fp1)
            self.app.update()
            self.assertEqual(len(self.app.open_documents), 2)
            self.assertTrue(self.app.close_file(self.fp1))
            self.app.update()
            self.assertEqual(len(self.app.open_documents), 1)
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "pack")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_ismapped(), 1)

    def test_guard_3_state5_close_last_doc_restores_empty_state(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self.assertTrue(self.app.close_file(self.fp1))
            self.app.update()
            self.assertEqual(len(self.app.open_documents), 0)
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "pack")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 1)
            self.assertGreater(self.app.empty_state_frame.winfo_height(), 1)

    def test_guard_4_state6_close_last_doc_from_continuous_view(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self.app.var_continuous_view.set(True)
            self.app._on_toggle_continuous_view()
            self.app.update()
            self.assertTrue(self.app.close_file(self.fp1))
            self.app.update()
            self.assertEqual(self.app.empty_state_frame.winfo_manager(), "pack")
            self.assertEqual(self.app.continuous_wrap.winfo_manager(), "")
            self.assertEqual(self.app.gd_scroll_wrap.winfo_manager(), "")
            self.assertEqual(self.app.empty_state_frame.winfo_ismapped(), 1)

    def test_guard_5_state7_view_toggles_and_mutual_exclusion(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self._assert_top_view_order(self.app.gd_scroll_wrap)
            self.app.var_continuous_view.set(True)
            self.app._on_toggle_continuous_view()
            self.app.update()
            self._assert_top_view_order(self.app.continuous_wrap)
            self.app.var_continuous_view.set(False)
            self.app._on_toggle_continuous_view()
            self.app.update()
            self._assert_top_view_order(self.app.gd_scroll_wrap)

    def test_guard_6_top_view_ordering_and_clean_scroll_x(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            self.app.open_file(self.fp1)
            self.app.update()
            self._assert_top_view_order(self.app.gd_scroll_wrap)
            self.assertIs(self.app.clean_scroll_x.master, self.app.clean_editor_row)
            self.assertEqual(self.app.clean_scroll_x.winfo_manager(), "pack")
            self.assertEqual(self.app.clean_scroll_x.winfo_ismapped(), 1)

    def test_guard_7_pack_only_invariant(self):
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(show_splash=False, restore_session=False)
            self.app.deiconify()
            self.app.update()
            for w in (self.app.empty_state_frame, self.app.gd_scroll_wrap, self.app.continuous_wrap):
                self.assertIn(w.winfo_manager(), ("", "pack"))
            self.app.open_file(self.fp1)
            self.app.update()
            for w in (self.app.empty_state_frame, self.app.gd_scroll_wrap, self.app.continuous_wrap):
                self.assertIn(w.winfo_manager(), ("", "pack"))
