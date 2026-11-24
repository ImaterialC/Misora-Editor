"""
S21 — Docked Right-Side MTL Drawer: All Script Mode (FEAT-13)
===============================================================
Verification suite for:
  - Probe 1 (FEAT-13):
    * Switching to All Script mode (including via var_continuous_view toggle) renders
      ONE single-engine selector at top + EXACTLY 2 tk.Text widgets inside tab_mtl_frame
      (1 read-only multi-line list + 1 bottom editable scratchpad), ZERO ttk.Treeview,
      and ZERO per-box Text widgets.
    * Configures 5 static theme-aware status tags:
      mtl_status_ready (✓), mtl_status_translating (⏳), mtl_status_error (⚠),
      mtl_status_locked (🔒, fg_muted), mtl_status_empty (-, fg_muted).
    * Preserves multi-line (2-3 line) text without single-line truncation.
  - Probe 2 (FEAT-13):
    * Translate All skips locked boxes at model layer, dispatches unlocked boxes
      by box.uid without self-stale req_seq discard, and discards stale file-switch replies.
    * Apply All skips locked boxes at model layer, targets unlocked boxes by stable
      box.uid, preserves exact whitespace (no .strip()), and records a single Undo batch
      with source='mtl'.
  - Guard 1:
    * Lightweight direct contract check for S20 Dialogue mode & S11 MTLEngine/queue.
"""

import shutil
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.mtl_engine import MTLConfig, MTLEngine  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402


def _collect_descendants(widget):
    out = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(_collect_descendants(child))
    return out


class S21TestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s21_test_"))
        self.config_path = self.tmp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")

        self.patch_cfg = patch.object(misora, "CONFIG_PATH", self.config_path)
        self.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        self.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        self.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        self.patch_cfg.start()
        self.patch_info.start()
        self.patch_warn.start()
        self.patch_err.start()

        self.app = misora.MisoraApp(restore_session=False, show_splash=False)
        self.app._test_bypass_dialogs = True
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_dir / "backups")

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.patch_err.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.patch_cfg.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @staticmethod
    def _create_multiline_doc() -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "おはよう！\n今日もいい天気ですね。\n冒険に出かけましょう！"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "主さま、準備は整っております。"]),
            Record(cmd_id=6, cmd_name="print", args=["Kyaru", "ちょっと待ちなさいよ！\n勝手に行かないでよね。"]),
        ]
        return StoryDocument(recs)


class TestP3S21MTLDrawerAllScript(S21TestBase):
    """S21 TDD verification suite for FEAT-13."""

    def test_probe_1_all_script_mode_exact_2_text_widgets_and_5_static_tags(self):
        """[Probe 1 — FEAT-13] Exact 2 tk.Text widgets, 0 Treeview, 5 static tags, multiline preserved."""
        doc = self._create_multiline_doc()
        path = self.tmp_dir / "s21_story.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._update_views()

        self.app._open_side_drawer("mtl")
        self.app.var_continuous_view.set(True)
        self.app._on_toggle_continuous_view()
        self.app.update_idletasks()

        self.assertEqual(
            self.app._mtl_drawer_mode,
            "all_script",
            "Toggling var_continuous_view ON must switch MTL drawer to 'all_script' mode",
        )

        descendants = _collect_descendants(self.app.tab_mtl_frame)
        text_widgets = [w for w in descendants if isinstance(w, tk.Text)]
        treeviews = [w for w in descendants if isinstance(w, ttk.Treeview)]

        self.assertEqual(len(treeviews), 0, "All Script MTL drawer must contain ZERO ttk.Treeview widgets")
        self.assertEqual(
            len(text_widgets),
            2,
            f"All Script MTL drawer must contain EXACTLY 2 tk.Text widgets, got {len(text_widgets)}",
        )

        list_widget = getattr(self.app, "txt_mtl_all_list", None)
        scratch_widget = getattr(self.app, "txt_mtl_all_scratchpad", None)
        self.assertIsNotNone(list_widget, "txt_mtl_all_list must exist")
        self.assertIsNotNone(scratch_widget, "txt_mtl_all_scratchpad must exist")
        self.assertIn(list_widget, text_widgets)
        self.assertIn(scratch_widget, text_widgets)
        self.assertEqual(str(list_widget.cget("state")), "disabled", "txt_mtl_all_list must be read-only")
        self.assertEqual(str(scratch_widget.cget("state")), "normal", "txt_mtl_all_scratchpad must be editable")

        # Single engine selector at top
        cmb = getattr(self.app, "cmb_mtl_all_engine", None)
        self.assertIsInstance(cmb, ttk.Combobox, "All Script mode must have a single-engine ttk.Combobox selector")

        # 5 static status tags with fg_muted on locked and empty
        tags = set(list_widget.tag_names())
        expected_tags = {
            "mtl_status_ready",
            "mtl_status_translating",
            "mtl_status_error",
            "mtl_status_locked",
            "mtl_status_empty",
        }
        self.assertTrue(
            expected_tags.issubset(tags),
            f"Missing static status tags: {expected_tags - tags}",
        )
        fg_muted = self.app.theme["fg_muted"]
        self.assertEqual(list_widget.tag_cget("mtl_status_locked", "foreground"), fg_muted)
        self.assertEqual(list_widget.tag_cget("mtl_status_empty", "foreground"), fg_muted)

        # Multi-line dialogue preserved without single-line truncation
        list_content = list_widget.get("1.0", "end-1c")
        self.assertIn("おはよう！\n今日もいい天気ですね。\n冒険に出かけましょう！", list_content)

    def test_probe_2_translate_all_and_apply_all_lock_uid_and_whitespace(self):
        """[Probe 2 — FEAT-13] Translate All & Apply All skip locked boxes, target by box.uid, preserve whitespace."""
        doc = self._create_multiline_doc()
        path = self.tmp_dir / "s21_batch.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 1  # Lock Box 1 (Kokkoro)
        self.app._update_views()
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(1))

        self.app._open_side_drawer("mtl")
        self.app._set_mtl_drawer_mode("all_script")
        self.app.var_mtl_all_engine.set("Google")

        dispatched_texts = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            dispatched_texts.append(text)
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")
            if out_queue is not None:
                if "おはよう" in text:
                    res = "Good morning!\nNice weather today."
                else:
                    res = "  Wait a second!\nDon't go alone.  "
                out_queue.put(("success", metadata, res))
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            self.app._on_mtl_all_script_translate_all()
            for _ in range(6):
                self.app.update()
                time.sleep(0.02)
            self.app._poll_mtl_drawer_queue()

        # Locked Box 1 must NOT have been dispatched
        self.assertEqual(len(dispatched_texts), 2, f"Expected 2 unlocked dispatches, got {len(dispatched_texts)}")
        self.assertNotIn("主さま、準備は整っております。", dispatched_texts)

        # Apply All -> skips locked Box 1, applies Box 0 and Box 2 with exact whitespace
        applied_count = self.app._on_mtl_all_script_apply_all()
        self.assertEqual(applied_count, 2, "Apply All must apply exactly the 2 unlocked translated boxes")

        self.assertEqual(doc.boxes[0].clean_text, "Good morning!\nNice weather today.")
        self.assertEqual(doc.boxes[1].clean_text, "主さま、準備は整っております。", "Locked box must remain untouched")
        self.assertEqual(
            doc.boxes[2].clean_text,
            "  Wait a second!\nDon't go alone.  ",
            "Apply All must preserve leading/trailing whitespace (no .strip())",
        )

        self.assertTrue(self.app.undo_journal.can_undo())
        entry = self.app.undo_journal.pop_undo()
        self.assertIsNotNone(entry)
        self.assertEqual(len(entry.deltas), 2)
        self.assertTrue(all(getattr(d, "source", None) == "mtl" for d in entry.deltas))

    def test_guard_1_dialogue_mode_and_mtl_engine_contract(self):
        """[Guard 1] Lightweight check preserving S20 Dialogue mode & S11 MTLEngine contract."""
        self.app._open_side_drawer("mtl")
        self.app._set_mtl_drawer_mode("dialogue")
        self.assertEqual(self.app._mtl_drawer_mode, "dialogue")
        self.assertEqual(set(self.app._mtl_drawer_cards.keys()), {"XUAT Cache", "Google"})

        cfg = MTLConfig(active_engine="Google", protect_tags=True)
        engine = MTLEngine(cfg)
        self.assertEqual(engine.translate(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
