"""
S20 — Docked Right-Side MTL Drawer: Tab Infrastructure & Dialogue Multi-Engine Stack (FEAT-12)
===============================================================================================
Verification suite for:
  - Probe 1 (FEAT-12):
    * Opening MTL via on_open_translator_assistant() opens the 3rd right-side drawer tab
      ('mtl') without spawning a floating TranslatorAssistantDialog Toplevel.
    * Dialogue mode stacks ONLY user-enabled engines (default: XUAT Cache + Google).
    * Opt-in toggle adds DeepL card; Refresh All prompts messagebox.askyesno before
      batch-calling paid APIs (DeepL / LLM / OpenAI), and 'No' dispatches zero paid calls.
    * Per-card Apply enforces model-level Translation Lock and preserves whitespace (no .strip()).
  - Probe 2 (BUG-27):
    * Switching files while an MTL drawer request is in flight discards the stale result cleanly.
  - Guard 1:
    * Lightweight direct check that TranslatorAssistantDialog keeps its S11/S8a contract
      (importable, worker_queue, zero after_idle in _on_translate/_on_fetch_all).
"""

import ast
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.mtl_engine import MTLConfig, MTLEngine  # noqa: E402
from core.story_ast import Record, StoryDocument  # noqa: E402


class S20TestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s20_test_"))
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
    def _create_sample_doc(num_boxes=2, prefix="Box") -> StoryDocument:
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
        ]
        for i in range(num_boxes):
            recs.append(Record(cmd_id=6, cmd_name="print", args=[f"Speaker{i+1}", f"{prefix} {i+1} テスト"]))
        return StoryDocument(recs)


class TestP3S20MTLDrawerDialogue(S20TestBase):
    """S20 TDD verification suite for FEAT-12."""

    def test_probe_1_mtl_drawer_tab_dialogue_stack_lock_whitespace_and_paid_confirm(self):
        """[Probe 1 — FEAT-12] Docked MTL tab, enabled-only stack, lock/whitespace Apply, paid API confirm."""
        doc = self._create_sample_doc(2, prefix="Original")
        path = self.tmp_dir / "s20_story.unity3d"
        self.app.open_documents[path] = {"doc": doc, "plain_text": ""}
        self.app.current_file_path = path
        self.app.current_doc = doc
        self.app.current_box_idx = 0
        self.app._update_views()

        # 1. Opening MTL opens right-side drawer 3rd tab (no floating Toplevel)
        self.app.on_open_translator_assistant()
        self.app.update_idletasks()

        self.assertTrue(self.app._side_drawer_visible, "Side drawer must become visible on MTL open")
        self.assertEqual(self.app._side_drawer_tab, "mtl", "Active side drawer tab must be 'mtl'")
        self.assertTrue(hasattr(self.app, "btn_tab_mtl"), "Right-side drawer must have 3rd tab button btn_tab_mtl")
        self.assertTrue(hasattr(self.app, "tab_mtl_frame"), "Right-side drawer must have tab_mtl_frame")
        self.assertIsNone(
            getattr(self.app, "_translator_dialog", None),
            "Opening MTL must NOT spawn floating TranslatorAssistantDialog Toplevel",
        )

        # 2. Dialogue mode stacks ONLY enabled engines (default: XUAT Cache + Google)
        cards = getattr(self.app, "_mtl_drawer_cards", {})
        self.assertEqual(
            set(cards.keys()),
            {"XUAT Cache", "Google"},
            f"Default Dialogue mode must stack only XUAT Cache and Google, got: {set(cards.keys())}",
        )

        # 3. Enable DeepL -> DeepL card appears; Refresh All prompts paid API confirmation
        self.app._set_mtl_drawer_engine_enabled("DeepL", True)
        self.assertIn("DeepL", self.app._mtl_drawer_cards, "Enabling DeepL must add DeepL card to stack")

        dispatched_engines = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            dispatched_engines.append(config.active_engine)
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")
            if out_queue is not None:
                out_queue.put(("success", metadata, f"TR:{config.active_engine}:{text}"))
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch.object(misora.messagebox, "askyesno", return_value=False) as mock_ask, \
             patch("misora.translate_async", side_effect=fake_translate_async):
            self.app._on_mtl_drawer_refresh_all()
            mock_ask.assert_called_once()
            self.assertNotIn(
                "DeepL",
                dispatched_engines,
                "Declining paid API confirmation must dispatch ZERO DeepL worker calls",
            )

        # 4. Per-card Apply enforces model-level Translation Lock and preserves whitespace
        google_card = self.app._mtl_drawer_cards["Google"]
        scratch = google_card["scratchpad"]
        scratch.delete("1.0", "end")
        scratch.insert("1.0", "  Leading and trailing  \n")

        # Lock Box 0 at model level
        self.app.on_toggle_lock_current_box()
        self.assertTrue(self.app.is_box_locked(0))

        applied_locked = self.app._on_mtl_drawer_apply_engine("Google")
        self.assertFalse(applied_locked, "Per-card Apply must refuse locked box at model level")
        self.assertEqual(doc.boxes[0].clean_text, "Original 1 テスト")

        # Unlock Box 0 and Apply -> preserves exact whitespace, records source='mtl'
        self.app.on_toggle_lock_current_box()
        self.assertFalse(self.app.is_box_locked(0))

        applied_ok = self.app._on_mtl_drawer_apply_engine("Google")
        self.assertTrue(applied_ok, "Per-card Apply must succeed on unlocked box")
        self.assertEqual(
            doc.boxes[0].clean_text,
            "  Leading and trailing  \n",
            "Per-card Apply must preserve leading/trailing whitespace and newlines (no .strip())",
        )
        self.assertTrue(self.app.undo_journal.can_undo())
        last_entry = self.app.undo_journal.pop_undo()
        self.assertIsNotNone(last_entry)
        self.assertEqual(getattr(last_entry.deltas[0], "source", None), "mtl")

    def test_probe_2_mtl_drawer_stale_file_switch_discards_result(self):
        """[Probe 2 — BUG-27] Switching files while an MTL drawer request is in flight discards stale result."""
        doc1 = self._create_sample_doc(2, prefix="DocOne")
        doc2 = self._create_sample_doc(2, prefix="DocTwo")
        path1 = self.tmp_dir / "s20_doc1.unity3d"
        path2 = self.tmp_dir / "s20_doc2.unity3d"

        self.app.open_documents[path1] = {"doc": doc1, "plain_text": ""}
        self.app.open_documents[path2] = {"doc": doc2, "plain_text": ""}
        self.app.current_file_path = path1
        self.app.current_doc = doc1
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app._open_side_drawer("mtl")

        intercepted = []

        def fake_translate_async(text, config, on_success=None, on_error=None, xuat_cache=None, **kwargs):
            out_queue = kwargs.get("out_queue")
            metadata = kwargs.get("metadata")

            def finish():
                if out_queue is not None:
                    out_queue.put(("success", metadata, "STALE_DOC1_TRANSLATION"))

            intercepted.append(finish)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch("misora.translate_async", side_effect=fake_translate_async):
            self.app._on_mtl_drawer_refresh_engine("Google")
            self.assertEqual(len(intercepted), 1, "Per-card Refresh must dispatch translate_async")

            # Switch to doc2 while request is in flight
            self.app.current_file_path = path2
            self.app.current_doc = doc2
            self.app.current_box_idx = 0
            self.app._update_views()

            # Deliver stale reply from doc1
            intercepted[0]()
            for _ in range(5):
                self.app.update()
                time.sleep(0.02)
            if hasattr(self.app, "_poll_mtl_drawer_queue"):
                self.app._poll_mtl_drawer_queue()

        scratch_text = self.app._mtl_drawer_cards["Google"]["scratchpad"].get("1.0", "end-1c")
        self.assertNotIn(
            "STALE_DOC1_TRANSLATION",
            scratch_text,
            "Stale MTL drawer result after file switch must be discarded cleanly",
        )
        self.assertEqual(doc2.boxes[0].clean_text, "DocTwo 1 テスト")

    def test_guard_1_translator_assistant_dialog_import_and_queue_contract(self):
        """[Guard 1] Lightweight check preserving TranslatorAssistantDialog S11/S8a contract."""
        src = (_REPO / "misora.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        found_cls = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TranslatorAssistantDialog":
                found_cls = node
                break
        self.assertIsNotNone(found_cls, "TranslatorAssistantDialog must remain importable for S11/S8a guards")
        methods = {item.name: ast.get_source_segment(src, item) or "" for item in found_cls.body if isinstance(item, ast.FunctionDef)}
        self.assertIn("_on_translate", methods)
        self.assertIn("_on_fetch_all", methods)
        self.assertNotIn("after_idle", methods["_on_translate"])
        self.assertNotIn("after_idle", methods["_on_fetch_all"])

        cfg = MTLConfig(active_engine="Google", protect_tags=True)
        engine = MTLEngine(cfg)
        self.assertEqual(engine.translate(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
