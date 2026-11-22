"""
S5 — Multi-File Replace-All & BulkFileDelta Disk Safety
========================================================
TDD tests verifying:
  - BULK-DELTA-NONATOMIC: _apply_delta(BulkFileDelta) uses write_atomic_utf8 for undo and redo.
  - on_replace_all() multi-file plain-text replacement uses write_atomic_utf8.
  - Transaction rollback: if writing fails mid-batch during BulkFileDelta undo/redo,
    all previously applied files in that batch are restored to their prior state.
  - In-memory cache synchronization: open documents in self.open_documents have their
    plain_text cache and saved-state checkpoints updated when modified by BulkFileDelta or on_replace_all().
  - Backup creation is verified before atomic write during on_replace_all().

All tests use temporary directories and headless app fixtures without GUI popups.
"""

import sys
import os
import shutil
import tempfile
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402
from core.undo_journal import BulkFileDelta  # noqa: E402


# ---------------------------------------------------------------------------
# HeadlessApp fixture
# ---------------------------------------------------------------------------
def _build_headless_app() -> tuple[misora.MisoraApp, tk.Tk]:
    """Return a MisoraApp instance with Tk internals stubbed out for headless testing."""
    root = tk.Tk()
    root.withdraw()

    app = misora.MisoraApp.__new__(misora.MisoraApp)

    # Minimal tk.Tk infrastructure
    app.tk = root.tk
    app._w = root._w
    app.children = {}
    app._tclCommands = set()

    # Core state
    app.open_documents = {}
    app.current_file_path = None
    app.current_doc = None
    app.current_unity_env = None
    app.current_text_obj = None
    app.is_bundle_file = False
    app.is_dirty = False
    app._plain_text_content = ""
    app.current_box_idx = 0
    app.is_box0_active = False
    app._suppress_continuous_events = False
    app._card_widgets = {}
    app._modified_boxes = set()
    app._selected_boxes = set()
    app._locked_boxes = set()
    app._saved_state_checkpoints = {}
    app.selected_search_folder = None
    app.xuat_search_roots = []
    app.undo_journal = MagicMock()
    app.logger = MagicMock()
    app.prefs = {}
    app.theme = {
        "highlight_bg": "#aabbcc",
        "bg_panel": "#ffffff",
        "fg_text": "#000000",
        "fg_muted": "#888888",
        "misora_pink": "#ff69b4",
        "bg_editor": "#ffffff",
        "border": "#cccccc",
    }

    # Tk variables
    app.var_continuous_view = tk.BooleanVar(master=root, value=False)
    app.var_preview_compiled = tk.BooleanVar(master=root, value=False)
    app.var_select_box_mode = tk.BooleanVar(master=root, value=False)
    app.var_sync_xuat = tk.BooleanVar(master=root, value=False)
    app.var_inc_bundles = tk.BooleanVar(master=root, value=False)
    app.var_inc_text = tk.BooleanVar(master=root, value=True)
    app.search_var = tk.StringVar(master=root, value="")
    app.replace_var = tk.StringVar(master=root, value="")
    app.scope_var = tk.StringVar(master=root, value="folder")
    app.folder_path_var = tk.StringVar(master=root, value="")

    # Widgets
    app.txt_dialogue = tk.Text(root)
    app.txt_continuous = tk.Text(root)
    app.lbl_status = MagicMock()

    # Mocked methods
    app._update_views = MagicMock()
    app._refresh_opened_files_list = MagicMock()
    app._flush_active_widget = MagicMock(return_value=True)
    app._dirty_state_changed = MagicMock()
    app._update_raw_view = MagicMock()
    app._sync_clean_view_to_current_box = MagicMock()
    app._get_active_text_widget = MagicMock(return_value=app.txt_dialogue)
    app.show_toast = MagicMock()
    app.after = MagicMock()
    app.open_file = MagicMock()

    # Real helpers from MisoraApp
    app._record_saved_checkpoint = misora.MisoraApp._record_saved_checkpoint.__get__(app)
    app._mark_document_dirty = misora.MisoraApp._mark_document_dirty.__get__(app)
    app._apply_delta = misora.MisoraApp._apply_delta.__get__(app)
    app.on_replace_all = misora.MisoraApp.on_replace_all.__get__(app)

    app._root = root
    return app, root


class S5TestBase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="misora_s5_test_")
        self.app, self.root = _build_headless_app()
        def _get_test_bak_dir():
            d = Path(self.temp_dir) / "backups"
            d.mkdir(parents=True, exist_ok=True)
            return d
        self.app._get_backup_dir = _get_test_bak_dir

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


# ===========================================================================
# Test Cases
# ===========================================================================

class TestS5BulkDeltaAtomicAndSync(S5TestBase):
    """Verify BulkFileDelta undo/redo uses atomic writes and synchronizes cache."""

    def test_01_bulk_delta_undo_uses_atomic_write(self):
        """Undoing BulkFileDelta (reverse=True) must call write_atomic_utf8."""
        f1 = Path(self.temp_dir) / "doc1.txt"
        f1.write_text("modified_text_1", encoding="utf-8")

        delta = BulkFileDelta(
            description="Replace test",
            per_file=[(str(f1), "original_text_1", "modified_text_1")]
        )

        with patch("misora.write_atomic_utf8") as mock_atomic_write:
            self.app._apply_delta(delta, reverse=True, refresh_ui=False)
            mock_atomic_write.assert_called_once_with(f1.resolve(), "original_text_1", encoding="utf-8")

    def test_02_bulk_delta_redo_uses_atomic_write(self):
        """Redoing BulkFileDelta (reverse=False) must call write_atomic_utf8."""
        f1 = Path(self.temp_dir) / "doc1.txt"
        f1.write_text("original_text_1", encoding="utf-8")

        delta = BulkFileDelta(
            description="Replace test",
            per_file=[(str(f1), "original_text_1", "modified_text_1")]
        )

        with patch("misora.write_atomic_utf8") as mock_atomic_write:
            self.app._apply_delta(delta, reverse=False, refresh_ui=False)
            mock_atomic_write.assert_called_once_with(f1.resolve(), "modified_text_1", encoding="utf-8")

    def test_03_bulk_delta_undo_syncs_open_documents_cache(self):
        """Undoing BulkFileDelta updates open_documents cache and checkpoint for open files."""
        f1 = (Path(self.temp_dir) / "doc1.txt").resolve()
        f1.write_text("modified_text_1", encoding="utf-8")

        self.app.open_documents[f1] = {
            "dirty": True,
            "plain_text": "modified_text_1",
            "doc": None
        }

        delta = BulkFileDelta(
            description="Replace test",
            per_file=[(str(f1), "original_text_1", "modified_text_1")]
        )

        self.app._apply_delta(delta, reverse=True, refresh_ui=False)

        # In-memory plain_text cache must be updated to the undone text
        self.assertEqual(self.app.open_documents[f1]["plain_text"], "original_text_1")
        # Checkpoint hash must match original_text_1
        import hashlib
        expected_hash = hashlib.sha256("original_text_1".encode("utf-8")).hexdigest()
        self.assertEqual(self.app._saved_state_checkpoints.get(str(f1)), expected_hash)

    def test_04_bulk_delta_redo_syncs_open_documents_cache(self):
        """Redoing BulkFileDelta updates open_documents cache and checkpoint for open files."""
        f1 = (Path(self.temp_dir) / "doc1.txt").resolve()
        f1.write_text("original_text_1", encoding="utf-8")

        self.app.open_documents[f1] = {
            "dirty": False,
            "plain_text": "original_text_1",
            "doc": None
        }

        delta = BulkFileDelta(
            description="Replace test",
            per_file=[(str(f1), "original_text_1", "modified_text_1")]
        )

        self.app._apply_delta(delta, reverse=False, refresh_ui=False)

        # In-memory plain_text cache must be updated to the redone text
        self.assertEqual(self.app.open_documents[f1]["plain_text"], "modified_text_1")
        import hashlib
        expected_hash = hashlib.sha256("modified_text_1".encode("utf-8")).hexdigest()
        self.assertEqual(self.app._saved_state_checkpoints.get(str(f1)), expected_hash)


class TestS5BulkDeltaRollback(S5TestBase):
    """Verify transaction rollback during BulkFileDelta execution on mid-batch failure."""

    def test_05_bulk_delta_transaction_rollback_on_write_failure(self):
        """If writing file 2 fails during bulk undo, file 1 must be rolled back to its pre-undo text."""
        f1 = (Path(self.temp_dir) / "f1.txt").resolve()
        f2 = (Path(self.temp_dir) / "f2.txt").resolve()
        f1.write_text("new_1", encoding="utf-8")
        f2.write_text("new_2", encoding="utf-8")

        self.app.open_documents[f1] = {"dirty": False, "plain_text": "new_1", "doc": None}
        self.app.open_documents[f2] = {"dirty": False, "plain_text": "new_2", "doc": None}

        delta = BulkFileDelta(
            description="Batch replace",
            per_file=[(str(f1), "old_1", "new_1"), (str(f2), "old_2", "new_2")]
        )

        # Simulate write failure on f2
        real_write_atomic = misora.write_atomic_utf8

        def write_side_effect(path, content, encoding="utf-8"):
            if Path(path).resolve() == f2:
                raise OSError("Simulated disk error on f2")
            return real_write_atomic(path, content, encoding=encoding)

        with patch("misora.write_atomic_utf8", side_effect=write_side_effect), \
             patch("misora.messagebox.showerror") as mock_err:
            with self.assertRaises(OSError):
                self.app._apply_delta(delta, reverse=True, refresh_ui=False)
            mock_err.assert_called_once()

        # Transaction rollback must have restored f1 to "new_1"
        self.assertEqual(f1.read_text(encoding="utf-8"), "new_1")
        self.assertEqual(self.app.open_documents[f1]["plain_text"], "new_1")


class TestS5ReplaceAllSafety(S5TestBase):
    """Verify multi-file Replace All uses atomic write, backups, and cache sync."""

    def test_06_replace_all_text_uses_atomic_write(self):
        """on_replace_all() multi-file text replacement calls write_atomic_utf8."""
        folder = Path(self.temp_dir) / "texts"
        folder.mkdir(parents=True, exist_ok=True)
        f1 = folder / "dialogue_a.txt"
        f1.write_text("apple orange apple", encoding="utf-8")

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(folder))
        self.app.search_var.set("apple")
        self.app.replace_var.set("banana")

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"), \
             patch("misora.write_atomic_utf8") as mock_atomic:
            self.app.on_replace_all()
            mock_atomic.assert_called_once_with(f1.resolve(), "banana orange banana", encoding="utf-8")

    def test_07_replace_all_syncs_open_documents_cache(self):
        """on_replace_all() updates in-memory plain_text cache for open files."""
        folder = Path(self.temp_dir) / "texts"
        folder.mkdir(parents=True, exist_ok=True)
        f1 = (folder / "open_note.txt").resolve()
        f1.write_text("Hello world", encoding="utf-8")

        self.app.open_documents[f1] = {
            "dirty": False,
            "plain_text": "Hello world",
            "doc": None
        }

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(folder))
        self.app.search_var.set("world")
        self.app.replace_var.set("Misora")

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        self.assertEqual(f1.read_text(encoding="utf-8"), "Hello Misora")
        self.assertEqual(self.app.open_documents[f1]["plain_text"], "Hello Misora")

    def test_08_replace_all_backup_created_before_atomic_write(self):
        """on_replace_all() creates .bak copy in backup dir before atomic replacement."""
        folder = Path(self.temp_dir) / "texts"
        folder.mkdir(parents=True, exist_ok=True)
        f1 = folder / "sample.txt"
        f1.write_text("target text", encoding="utf-8")

        self.app.scope_var.set("folder")
        self.app.folder_path_var.set(str(folder))
        self.app.search_var.set("target")
        self.app.replace_var.set("updated")

        with patch("misora.messagebox.askyesno", return_value=True), \
             patch("misora.messagebox.showinfo"):
            self.app.on_replace_all()

        # A .bak file must exist in the backup directory
        bak_dir = Path(self.temp_dir) / "backups"
        bak_files = list(bak_dir.glob("sample.bak_*.txt"))
        self.assertTrue(len(bak_files) >= 1, "Backup file should be created in backup_dir")
        self.assertEqual(bak_files[0].read_text(encoding="utf-8"), "target text")


if __name__ == "__main__":
    unittest.main(verbosity=2)
