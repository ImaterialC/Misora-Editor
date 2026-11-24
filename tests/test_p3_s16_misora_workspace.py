"""Test Suite for Misora Editor Session S16: .misora v1 Workspace & ProjectDiffDialog.

Scope: FEAT-08 (U-B17, U-B18) — Track 2 · Group G3.
Failing-first defect probes:
- Probe 1: Saved .misora JSON has schema_version == 1, rel_path + abs_path,
  view_mode/search_scope state, and (box_ordinal, jp_sha256) lock keys — with
  ZERO Record.uid, ZERO story text drafts, and ZERO binary blobs.
- Probe 2: Reopening .misora restores open tabs, active box, and matched locks;
  unmatched lock (changed JP text on disk) stays unresolved (not transferred) and
  notifies the user; missing files are reported cleanly without crashing.
- Probe 3 (U-B18): Opening another .misora while dirty files exist computes exact
  added/removed/kept/dirty diff and aborts cleanly on Cancel.
Regression guard:
- Guard 1: Direct lightweight assertions for S06 stable lock helpers and S15 UI
  attributes (no nested unittest suite runs).
"""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import misora
from misora import MisoraApp
from core.story_ast import Record, StoryDocument


class TestP3S16MisoraWorkspace(unittest.TestCase):
    """S16: .misora v1 workspace serialization, restore, and U-B18 overwrite diff."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s16_"))
        self.tmp_config = self.tmp_dir / "misora_config.json"
        self.tmp_config.write_text("{}", encoding="utf-8")
        self.tmp_backup_dir = self.tmp_dir / "backups"
        self.tmp_backup_dir.mkdir(parents=True, exist_ok=True)

        self._orig_config_path = misora.CONFIG_PATH
        misora.CONFIG_PATH = self.tmp_config

        self._patches = [
            mock.patch.object(misora.messagebox, "showinfo", return_value=None),
            mock.patch.object(misora.messagebox, "showwarning", return_value=None),
            mock.patch.object(misora.messagebox, "showerror", return_value=None),
            mock.patch.object(misora.messagebox, "askyesno", return_value=False),
            mock.patch.object(misora.messagebox, "askokcancel", return_value=True),
            mock.patch.object(misora.messagebox, "askyesnocancel", return_value=False),
        ]
        for p in self._patches:
            p.start()

        self.app = None

    def tearDown(self) -> None:
        if self.app is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
            self.app = None

        misora.CONFIG_PATH = self._orig_config_path
        for p in self._patches:
            try:
                p.stop()
            except Exception:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_v2_script(self, rel_path: str, lines_data: list[tuple[str, str]]) -> Path:
        doc = StoryDocument()
        records = [
            Record(cmd_id=0, cmd_name="title", args=["Test Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Test Outline"]),
        ]
        for idx, (speaker, text) in enumerate(lines_data):
            if idx > 0:
                records.append(Record(cmd_id=10, cmd_name="touch", args=[]))
            records.append(Record(cmd_id=6, cmd_name="print", args=[speaker, text]))
        doc.records = records
        doc._rebuild_boxes()
        target = self.tmp_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(doc.to_v2_text(), encoding="utf-8")
        return target

    # -------------------------------------------------------------------------
    # DEFECT PROBE 1: .misora v1 schema (refs + state + stable locks ONLY)
    # -------------------------------------------------------------------------
    def test_probe_1_save_misora_v1_schema_refs_state_locks_only(self) -> None:
        """Probe 1: Saved .misora JSON has schema_version==1, paths, state, stable locks, and NO drafts/UIDs/blobs."""
        from core.workspace import load_workspace

        file_a = self._make_v2_script(
            "scripts/ep01.v2.txt",
            [("Peco", "お腹すいたー！"), ("Kokkoro", "主さま、お弁当です。")],
        )
        file_b = self._make_v2_script(
            "scripts/ep02.v2.txt",
            [("Kyaru", "ちょっと待ちなさいよ！")],
        )

        self.app = MisoraApp(restore_session=False, show_splash=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_backup_dir)

        self.app.open_file(file_a)
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()
        # Type an unsaved draft into box 0 to verify drafts are NEVER serialized
        self.app.current_box_idx = 0
        self.app._update_views()
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "UNSAVED_DRAFT_SECRET_TEXT")
        self.app._on_dialogue_edited()

        self.app.open_file(file_b)
        self.app.current_box_idx = 0
        self.app.var_continuous_view.set(True)
        self.app.scope_var.set("folder")
        self.app._sync_scope_widgets()
        self.app._update_views()

        ws_path = self.tmp_dir / "project.misora"
        self.app.save_project(ws_path)

        self.assertTrue(ws_path.is_file(), ".misora file must be created on disk")
        raw_text = ws_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)

        self.assertEqual(payload.get("schema_version"), 1)
        self.assertEqual(payload.get("view_mode"), "continuous")
        self.assertEqual(payload.get("search_scope"), "folder")
        self.assertEqual(payload.get("active_box_idx"), 0)
        self.assertFalse(payload.get("is_box0_active", True))
        self.assertEqual(len(payload.get("files", [])), 2)

        # Strict NO-01 / NO-12 checks: zero drafts, zero Record.uid, zero binary blobs
        self.assertNotIn("UNSAVED_DRAFT_SECRET_TEXT", raw_text)
        self.assertNotIn("Record.uid", raw_text)
        for f_entry in payload["files"]:
            self.assertIn("rel_path", f_entry)
            self.assertIn("abs_path", f_entry)
            self.assertIn("locked_keys", f_entry)
            self.assertNotIn("uid", f_entry)
            self.assertNotIn("draft", f_entry)
            self.assertNotIn("records", f_entry)

        # Verify file_a's lock on box_ordinal 1 survived even though file_b was active
        ep01_entry = next(f for f in payload["files"] if "ep01.v2.txt" in f["abs_path"])
        self.assertEqual(len(ep01_entry["locked_keys"]), 1)
        lk = ep01_entry["locked_keys"][0]
        self.assertEqual(lk["box_ordinal"], 1)
        expected_sha = hashlib.sha256("主さま、お弁当です。".encode("utf-8")).hexdigest()
        self.assertEqual(lk["jp_sha256"], expected_sha)

        # Round-trip parse via core.workspace.load_workspace
        session = load_workspace(ws_path)
        self.assertEqual(session.schema_version, 1)
        self.assertEqual(len(session.files), 2)

    # -------------------------------------------------------------------------
    # DEFECT PROBE 2: Restore tabs/state/locks + unmatched lock & missing file
    # -------------------------------------------------------------------------
    def test_probe_2_open_misora_restores_state_and_rejects_unmatched_locks(self) -> None:
        """Probe 2: Reopening .misora restores tabs, active box, matched locks; unmatched lock is NOT transferred."""
        file_a = self._make_v2_script(
            "scripts/story_a.v2.txt",
            [("Peco", "Box Zero JP"), ("Kokkoro", "Box One JP")],
        )
        file_b = self._make_v2_script(
            "scripts/story_b.v2.txt",
            [("Kyaru", "Story B Box 0"), ("Yuuki", "Story B Box 1")],
        )
        file_missing = self._make_v2_script(
            "scripts/story_missing.v2.txt",
            [("Peco", "Will be deleted")],
        )

        self.app = MisoraApp(restore_session=False, show_splash=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_backup_dir)

        # Open A (lock box 0 and box 1), open B (set active box 1), open missing
        self.app.open_file(file_a)
        self.app.current_box_idx = 0
        self.app.on_toggle_lock_current_box()
        self.app.current_box_idx = 1
        self.app.on_toggle_lock_current_box()

        self.app.open_file(file_missing)
        self.app.open_file(file_b)
        self.app.current_box_idx = 1
        self.app.var_continuous_view.set(True)
        self.app.scope_var.set("current")

        ws_path = self.tmp_dir / "restore_test.misora"
        self.app.save_project(ws_path)

        # Close everything, delete file_missing, and modify box 1 JP text in file_a on disk
        self.app.close_all_files()
        file_missing.unlink()

        doc_a_mod = StoryDocument.from_v2_text(file_a.read_text(encoding="utf-8"))
        doc_a_mod.inject_box(1, "Kokkoro", "MODIFIED_ON_DISK_JP")
        file_a.write_text(doc_a_mod.to_v2_text(), encoding="utf-8")

        # Reopen project — must notify about missing file & unresolved lock, and NOT crash
        with mock.patch.object(misora.messagebox, "showwarning") as mock_warn:
            opened = self.app.open_project(ws_path)

        self.assertTrue(opened)
        self.assertTrue(mock_warn.called, "User must be notified about missing file / unresolved lock")
        self.assertIn(file_a.resolve(), self.app.open_documents)
        self.assertIn(file_b.resolve(), self.app.open_documents)
        self.assertNotIn(file_missing.resolve(), self.app.open_documents)

        # Active file & cursor & view/scope restored
        self.assertEqual(self.app.current_file_path.resolve(), file_b.resolve())
        self.assertEqual(self.app.current_box_idx, 1)
        self.assertTrue(self.app.var_continuous_view.get())
        self.assertEqual(self.app.scope_var.get(), "current")

        # Switch to file_a: box 0 lock MUST be restored, box 1 lock MUST remain unlocked (unresolved)
        self.app.open_file(file_a)
        self.assertTrue(self.app.is_box_locked(0), "Matched lock on box 0 must be restored")
        self.assertFalse(self.app.is_box_locked(1), "Unmatched lock on box 1 must NOT be transferred")

    # -------------------------------------------------------------------------
    # DEFECT PROBE 3 (U-B18): ProjectDiffDialog diff & Cancel abort
    # -------------------------------------------------------------------------
    def test_probe_3_ub18_project_diff_and_cancel_abort(self) -> None:
        """Probe 3: Opening another .misora while dirty files exist computes exact diff and aborts cleanly on Cancel."""
        from core.workspace import compute_workspace_diff

        file_keep = self._make_v2_script("scripts/keep.v2.txt", [("Peco", "Keep me")])
        file_old = self._make_v2_script("scripts/old.v2.txt", [("Kokkoro", "Old file")])
        file_new = self._make_v2_script("scripts/new.v2.txt", [("Kyaru", "New file")])

        self.app = MisoraApp(restore_session=False, show_splash=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_backup_dir)

        # Save a target workspace containing file_keep + file_new
        self.app.open_file(file_keep)
        self.app.open_file(file_new)
        target_ws = self.tmp_dir / "target.misora"
        self.app.save_project(target_ws)
        self.app.close_all_files()

        # Now open file_keep and file_old, and make file_old dirty
        self.app.open_file(file_keep)
        self.app.open_file(file_old)
        self.app.txt_dialogue.delete("1.0", "end")
        self.app.txt_dialogue.insert("1.0", "Dirty unsaved edit")
        self.app._on_dialogue_edited()
        self.assertTrue(self.app.is_dirty)

        # Verify compute_workspace_diff directly
        self.app._flush_active_widget()
        self.app._save_active_document_state()
        diff = compute_workspace_diff(
            self.app.open_documents,
            [file_keep, file_new],
            current_file_path=self.app.current_file_path,
            current_is_dirty=self.app.is_dirty,
        )
        by_name = {d.path.name: d for d in diff}
        self.assertEqual(by_name["keep.v2.txt"].status, "kept")
        self.assertFalse(by_name["keep.v2.txt"].is_dirty)
        self.assertEqual(by_name["old.v2.txt"].status, "removed")
        self.assertTrue(by_name["old.v2.txt"].is_dirty)
        self.assertEqual(by_name["new.v2.txt"].status, "added")

        # Cancel in ProjectDiffDialog must abort open_project cleanly
        with mock.patch.object(misora, "ProjectDiffDialog") as mock_dlg_cls:
            mock_dlg_cls.return_value.result = "cancel"
            res = self.app.open_project(target_ws)

        self.assertFalse(res, "open_project must return False when user cancels ProjectDiffDialog")
        self.assertIn(file_old.resolve(), self.app.open_documents)
        self.assertNotIn(file_new.resolve(), self.app.open_documents)
        self.assertTrue(self.app.is_dirty)

    # -------------------------------------------------------------------------
    # REGRESSION GUARD 1: Lightweight S06 + S15 contracts
    # -------------------------------------------------------------------------
    def test_guard_1_s06_locks_and_s15_ui_contracts(self) -> None:
        """Guard 1: Direct lightweight checks for S06 stable lock helpers and S15 UI attributes."""
        doc = StoryDocument()
        doc.insert_box(0, {"speaker": "Peco", "clean_text": "JP Line 0"})
        uid0 = doc.boxes[0].uid
        orig_map = {uid0: "JP Line 0"}
        locks = misora.get_document_stable_locks(doc, {uid0}, orig_map)
        self.assertEqual(len(locks), 1)
        matched, unresolved = misora.restore_stable_locks(doc, locks, orig_map)
        self.assertEqual(matched, {uid0})
        self.assertEqual(unresolved, [])

        self.app = MisoraApp(restore_session=False, show_splash=False)
        self.app.withdraw()
        self.app.backup_folder = str(self.tmp_backup_dir)
        self.assertTrue(hasattr(self.app, "cb_dialogue_select"))
        self.assertTrue(hasattr(self.app, "empty_state_frame"))
        self.assertTrue(hasattr(self.app, "btn_dock_pin"))


if __name__ == "__main__":
    unittest.main()
