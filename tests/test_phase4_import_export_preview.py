"""Phase 4 Automated Verification Suite: Import/Export, Paste Preview Dialog, Version Unification, and Safe Tooltip.

Part of Misora Editor test suite.
"""

import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import tkinter as tk
from tkinter import ttk

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import importlib.util
import assets.splash as splash
from core.story_ast import StoryDocument, Record
from core.script_codec import parse, serialize
import misora


class TestPhase4ImportExportPreview(unittest.TestCase):
    """Automated tests for Phase 4 deliverables."""

    @classmethod
    def setUpClass(cls):
        # Create a single root app for GUI tests
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_p4_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        # Mock out messageboxes
        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warn = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_err = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warn.start()
        cls.patch_err.start()

        with patch.object(misora, "CONFIG_PATH", cls.config_path):
            cls.app = misora.MisoraApp(restore_session=False, show_splash=False)
            cls.app._test_bypass_dialogs = True
            cls.app.withdraw()
            cls.app.backup_folder = str(cls.tmp_dir / "backups")

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warn.stop()
        cls.patch_err.stop()

        try:
            cls.app.destroy()
        except Exception:
            pass
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _create_sample_doc(self) -> StoryDocument:
        """Create a mock 3-box StoryDocument with metadata."""
        recs = [
            Record(cmd_id=0, cmd_name="title", args=["Story Title"]),
            Record(cmd_id=1, cmd_name="outline", args=["Story Summary"]),
            Record(cmd_id=6, cmd_name="print", args=["Pecorine", "Initial Box 1"]),
            Record(cmd_id=7, cmd_name="tag", args=["Initial Narration Box 2"]),
            Record(cmd_id=6, cmd_name="print", args=["Kokkoro", "Initial Box 3"]),
        ]
        return StoryDocument(recs)

    def test_01_version_unification(self):
        """Single source of truth for version in root __init__.__version__ (Rule 21 / MF-S24)."""
        root_init_path = SCRIPT_DIR / "__init__.py"
        self.assertTrue(root_init_path.is_file())
        spec = importlib.util.spec_from_file_location("misora_root", str(root_init_path))
        root_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_mod)

        expected_version = getattr(root_mod, "__version__", None)
        self.assertIsInstance(expected_version, str)
        self.assertRegex(expected_version, r"^\d+\.\d+\.\d+$")

        self.assertEqual(misora.__version__, expected_version)
        self.assertEqual(misora._get_app_version(), expected_version)
        self.assertEqual(splash._load_app_version(), expected_version)
        self.assertEqual(splash._VERSION, expected_version)

        # Test modal About dialog (U05)
        self.app.on_about()
        about_dlg = getattr(self.app, "_about_dialog", None)
        self.assertIsNotNone(about_dlg)
        self.assertIsInstance(about_dlg, tk.Toplevel)
        self.assertTrue(about_dlg.winfo_exists())

        def _gather_texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    out.append(str(ch.cget("text")))
                except Exception:
                    pass
                out.extend(_gather_texts(ch))
            return out

        about_txt = "\n".join(_gather_texts(about_dlg))
        self.assertIn("Misora: Story Editor", about_txt)
        self.assertIn(f"v{expected_version}", about_txt)
        about_dlg.destroy()

    def test_02_tooltip_lifecycle_safe(self):
        """ToolTip handles delayed hover, cancels timers on Leave/Destroy, and avoids leaks."""
        dummy_btn = tk.Button(self.app, text="Test Button")
        dummy_btn.pack()
        tip = misora.ToolTip(dummy_btn, "Helpful Hint", delay_ms=80)

        self.assertTrue(tip.widget_exists())
        self.assertIsNone(tip._after_id)
        self.assertIsNone(tip.tip_window)

        # Enter schedules timer
        tip.on_enter()
        self.assertIsNotNone(tip._after_id)

        # Leave cancels timer before it fires
        tip.on_leave()
        self.assertIsNone(tip._after_id)
        self.assertIsNone(tip.tip_window)

        # Re-enter and trigger show_tip directly
        tip.show_tip()
        self.assertIsNotNone(tip.tip_window)
        self.assertTrue(tip.tip_window.winfo_exists())

        # Leave hides tip
        tip.on_leave()
        self.assertIsNone(tip.tip_window)

        # Destruction safety: schedule timer then destroy widget
        tip.on_enter()
        timer_id = tip._after_id
        self.assertIsNotNone(timer_id)
        dummy_btn.destroy()

        # Calling show_tip or on_destroy on destroyed widget must not raise
        tip.show_tip()
        tip.on_destroy()
        self.assertFalse(tip.widget_exists())
        self.assertIsNone(tip.tip_window)

    def test_03_csif_export(self):
        """CSIF export generates valid CSIF with headers, narration, and metadata."""
        doc = self._create_sample_doc()
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "export_test.unity3d"
        self.app.current_box_idx = 0
        self.app._update_views()

        target_export = self.tmp_dir / "exported_script.csif.txt"
        exported_path = self.app.on_export_script(target_export)
        self.assertIsNotNone(exported_path)
        self.assertTrue(exported_path.is_file())

        content = exported_path.read_text(encoding="utf-8")
        self.assertIn("@@!title\nStory Title", content)
        self.assertIn("@@!summary\nStory Summary", content)
        self.assertIn("@@Pecorine", content)
        self.assertIn("Initial Box 1", content)
        self.assertIn("@@_", content)
        self.assertIn("Initial Narration Box 2", content)
        self.assertIn("@@Kokkoro", content)
        self.assertIn("Initial Box 3", content)

        # Ensure content roundtrips cleanly through parse()
        parsed = parse(content)
        self.assertEqual(len(parsed.blocks), 3)
        self.assertEqual(parsed.blocks[0].speaker, "Pecorine")
        self.assertEqual(parsed.blocks[1].speaker, "")
        self.assertTrue(parsed.blocks[1].is_narration)
        self.assertEqual(parsed.blocks[2].speaker, "Kokkoro")

    def test_04_csif_import_and_preview_dialog(self):
        """ScriptPastePreviewDialog displays before/after comparison and toggles options cleanly."""
        doc = self._create_sample_doc()
        self.app.current_doc = doc
        self.app.current_box_idx = 0

        incoming_script = (
            "@@!title New Title\n"
            "@@Karyl\n"
            "Incoming Replacement 1\n\n"
            "@@_\n"
            "Incoming Narration 2\n"
        )
        parsed = parse(incoming_script)
        self.assertEqual(len(parsed.blocks), 2)

        # Direct instantiation of dialog
        dlg = misora.ScriptPastePreviewDialog(self.app, parsed, start_idx=0, source_label="Test Suite")
        self.assertFalse(dlg.confirmed)
        self.assertTrue(dlg.apply_speakers)
        self.assertTrue(dlg.apply_metadata)

        # Verify Treeview columns and row count
        items = dlg.tree.get_children()
        self.assertEqual(len(items), 2)

        # Row 1 check
        val1 = dlg.tree.item(items[0], "values")
        self.assertEqual(val1[0], "Box 1")
        self.assertEqual(val1[1], "Pecorine")
        self.assertEqual(val1[2], "Karyl")
        self.assertIn("Initial Box 1", val1[3])
        self.assertIn("Incoming Replacement 1", val1[4])

        # Row 2 check (Narration)
        val2 = dlg.tree.item(items[1], "values")
        self.assertEqual(val2[0], "Box 2")
        self.assertEqual(val2[1], "(narration)")
        self.assertEqual(val2[2], "(narration)")

        # Toggle apply_speakers -> False and refresh
        dlg.var_apply_speakers.set(False)
        dlg._populate_tree()
        val1_updated = dlg.tree.item(dlg.tree.get_children()[0], "values")
        self.assertIn("(keep)", val1_updated[2])

        # Test Apply action
        dlg.on_apply()
        self.assertTrue(dlg.confirmed)
        self.assertFalse(dlg.apply_speakers)
        self.assertTrue(dlg.apply_metadata)

    def test_05_menu_interchange_bindings_and_roundtrip(self):
        """File menu contains Import/Export entries, shortcuts are bound, and import round-trips with undo."""
        # Check menu existence
        menu_labels = []
        file_menu = self.app.file_menu
        for i in range(file_menu.index("end") + 1):
            try:
                label = file_menu.entrycget(i, "label")
                if label:
                    menu_labels.append(label)
            except Exception:
                pass

        self.assertIn("Import Script (CSIF / Text)...", menu_labels)
        self.assertIn("Export Script (CSIF)...", menu_labels)

        # Test import file round-trip
        doc = self._create_sample_doc()
        self.app.current_doc = doc
        self.app.current_file_path = self.tmp_dir / "roundtrip_test.unity3d"
        self.app.current_box_idx = 0
        self.app.is_dirty = False
        self.app._update_views()

        import_file = self.tmp_dir / "script_to_import.csif.txt"
        import_file.write_text(
            "@@!title\nImported Title\n"
            "@@Yuuki\n"
            "Imported Box 1 Dialogue\n"
            "@@Sheffy\n"
            "Imported Box 2 Dialogue\n",
            encoding="utf-8",
        )

        # Apply import without confirmation prompt
        self.app.on_import_script(import_file, confirm=False)

        # Verify applied changes
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Yuuki")
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, "Imported Box 1 Dialogue")
        self.assertEqual(self.app.current_doc.boxes[1].speaker, "Sheffy")
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, "Imported Box 2 Dialogue")
        self.assertEqual(self.app.current_doc.boxes[2].speaker, "Kokkoro")  # Box 3 unchanged
        self.assertTrue(self.app.is_dirty)

        # Verify metadata applied to Box 0
        meta = self.app.current_doc.get_metadata()
        self.assertEqual(meta.get("title"), "Imported Title")

        # Verify atomic undo restores original state
        self.app.on_undo()
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Pecorine")
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, "Initial Box 1")
        self.assertEqual(self.app.current_doc.boxes[1].speaker, "")
        self.assertEqual(self.app.current_doc.boxes[1].clean_text, "Initial Narration Box 2")

        # Verify redo re-applies
        self.app.on_redo()
        self.assertEqual(self.app.current_doc.boxes[0].speaker, "Yuuki")
        self.assertEqual(self.app.current_doc.boxes[0].clean_text, "Imported Box 1 Dialogue")


if __name__ == "__main__":
    unittest.main()
