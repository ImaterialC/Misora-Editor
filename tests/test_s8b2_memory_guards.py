"""
S8b-2 — Asset & Bundle Memory Leak Guards Tests
================================================
TDD tests verifying:
  - dispose_unity_env breaks circular reference cycles, enabling prompt deallocation without cyclic GC.
  - save_bundle_story disposes temporary verification check environment (env_check) without leaks.
  - search_engine disposes loaded bundle environments immediately after extracting documents.
  - close_file disposes the closed bundle's environment and clears current_unity_env.
  - on_replace_all disposes bundle environments during multi-file replacement.
  - assets.icon bounds maximum cache capacity and prune_icon_cache evicts dead widget entries.
  - NguiColorPickerPopup resets parent window reference and unloads photo buffers on close.
  - MisoraApp.destroy cleanly disposes all open document environments and prunes icon cache.
"""

import gc
import tempfile
import unittest
import weakref
import tkinter as tk
from pathlib import Path
from unittest.mock import patch, MagicMock

_REPO = Path(__file__).resolve().parent.parent
import sys
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora
from assets.icon import get_icon, clear_icon_cache, prune_icon_cache, _ICON_CACHE
from core import (
    load_bundle_story,
    save_bundle_story,
    dispose_unity_env,
    ProjectSearchEngine,
    SearchOptions,
    StoryDocument,
)

FIXTURE_PATH = _REPO / "storydata_1001005.unity3d"


class S8b2TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="misora_s8b2_test_"))
        cls.config_path = cls.tmp_dir / "misora_config.json"
        cls.config_path.write_text("{}", encoding="utf-8")

        cls.patch_yesno = patch.object(misora.messagebox, "askyesno", return_value=True)
        cls.patch_yesnocancel = patch.object(misora.messagebox, "askyesnocancel", return_value=True)
        cls.patch_info = patch.object(misora.messagebox, "showinfo", return_value=None)
        cls.patch_warning = patch.object(misora.messagebox, "showwarning", return_value=None)
        cls.patch_error = patch.object(misora.messagebox, "showerror", return_value=None)

        cls.patch_yesno.start()
        cls.patch_yesnocancel.start()
        cls.patch_info.start()
        cls.patch_warning.start()
        cls.patch_error.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_yesno.stop()
        cls.patch_yesnocancel.stop()
        cls.patch_info.stop()
        cls.patch_warning.stop()
        cls.patch_error.stop()

    def setUp(self):
        clear_icon_cache()
        with patch.object(misora, "CONFIG_PATH", self.config_path):
            self.app = misora.MisoraApp()
        self.app.withdraw()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        clear_icon_cache()


class TestS8b2MemoryGuards(S8b2TestBase):
    """S8b-2 Memory Leak Guards & Resource Disposal Tests."""

    def test_01_dispose_unity_env_breaks_circular_refs(self):
        """dispose_unity_env breaks Environment circular cycles, enabling immediate deallocation."""
        self.assertTrue(FIXTURE_PATH.is_file(), f"Fixture missing: {FIXTURE_PATH}")
        doc, env, obj, name = load_bundle_story(FIXTURE_PATH)
        env_ref = weakref.ref(env)

        # Before disposal, env is alive
        self.assertIsNotNone(env_ref())

        # Calling dispose_unity_env breaks circular cycles
        dispose_unity_env(env)
        del doc, env, obj, name

        # env should be promptly freed without running full gc.collect()
        self.assertIsNone(env_ref(), "dispose_unity_env must break circular cycles so refcount drops to 0")

    def test_02_save_bundle_story_disposes_check_env(self):
        """save_bundle_story disposes the temporary env_check verification environment."""
        doc, env, obj, name = load_bundle_story(FIXTURE_PATH)
        out_bundle = self.tmp_dir / "test_saved_bundle.unity3d"

        from core.bundle_io import get_unitypy
        unitypy_mod = get_unitypy()
        orig_load = unitypy_mod.load

        check_env_refs = []

        def tracking_load(*args, **kwargs):
            loaded_env = orig_load(*args, **kwargs)
            check_env_refs.append(weakref.ref(loaded_env))
            return loaded_env

        with patch.object(unitypy_mod, "load", side_effect=tracking_load):
            save_bundle_story(env, obj, doc, out_bundle)

        dispose_unity_env(env)
        del doc, env, obj

        self.assertGreaterEqual(len(check_env_refs), 1, "At least one verification check environment must be loaded")
        for ref in check_env_refs:
            self.assertIsNone(ref(), "Verification check environment must be cleanly disposed and freed")

    def test_03_search_engine_disposes_bundle_environments(self):
        """ProjectSearchEngine searching across bundles disposes environments immediately."""
        engine = ProjectSearchEngine()
        opts = SearchOptions(query="Test", include_bundles=True)

        from core.bundle_io import get_unitypy
        unitypy_mod = get_unitypy()
        orig_load = unitypy_mod.load

        search_env_refs = []

        def tracking_load(*args, **kwargs):
            loaded_env = orig_load(*args, **kwargs)
            search_env_refs.append(weakref.ref(loaded_env))
            return loaded_env

        with patch.object(unitypy_mod, "load", side_effect=tracking_load):
            results = engine.search_file(FIXTURE_PATH, opts)

        self.assertGreaterEqual(len(search_env_refs), 1)
        for ref in search_env_refs:
            self.assertIsNone(ref(), "Search engine must immediately dispose bundle environments after extracting document")

    def test_04_close_file_disposes_environment(self):
        """close_file() disposes the closed bundle's environment and clears current_unity_env."""
        self.app.open_file(FIXTURE_PATH)
        self.assertIsNotNone(self.app.current_unity_env)
        env_ref = weakref.ref(self.app.current_unity_env)

        # Close the file
        res = self.app.close_file(FIXTURE_PATH)
        self.assertTrue(res)
        self.assertIsNone(self.app.current_unity_env)

        # The closed file's environment should be disposed
        self.assertIsNone(env_ref(), "close_file must dispose the closed bundle's UnityPy environment")

    def test_05_replace_all_disposes_environments(self):
        """on_replace_all() disposes bundle environments during multi-file replacement."""
        bundle_copy = self.tmp_dir / "replace_target.unity3d"
        bundle_copy.write_bytes(FIXTURE_PATH.read_bytes() + b" helping ")

        self.app.selected_search_folder = self.tmp_dir
        self.app.folder_path_var.set(str(self.tmp_dir))
        self.app.scope_var.set("folder")
        self.app.var_inc_bundles.set(True)
        self.app.search_var.set("helping")
        self.app.replace_var.set("aiding")

        from core.bundle_io import get_unitypy
        unitypy_mod = get_unitypy()
        orig_load = unitypy_mod.load

        replace_env_refs = []

        def tracking_load(*args, **kwargs):
            loaded_env = orig_load(*args, **kwargs)
            replace_env_refs.append(weakref.ref(loaded_env))
            return loaded_env

        with patch.object(unitypy_mod, "load", side_effect=tracking_load):
            self.app.on_replace_all()

        self.assertGreaterEqual(len(replace_env_refs), 1)
        for ref in replace_env_refs:
            self.assertIsNone(ref(), "on_replace_all must dispose bundle environments after processing")

    def test_06_icon_cache_prunes_dead_widgets(self):
        """prune_icon_cache() removes cached icons belonging to destroyed Toplevel windows."""
        dlg = tk.Toplevel(self.app)
        dlg_id = id(dlg)

        ico = get_icon("search", (16, 16), master=dlg)
        self.assertIsNotNone(ico)

        matching = [k for k in _ICON_CACHE if k[0] == dlg_id]
        self.assertGreaterEqual(len(matching), 1)

        dlg.destroy()
        self.app.update()

        pruned_count = prune_icon_cache(dlg)
        self.assertGreaterEqual(pruned_count, 1)

        remaining = [k for k in _ICON_CACHE if k[0] == dlg_id]
        self.assertEqual(len(remaining), 0, "prune_icon_cache must evict entries for destroyed widgets")

    def test_07_icon_cache_bounds_maximum_capacity(self):
        """Icon cache enforces MAX_ICON_CACHE capacity bounding via eviction."""
        from assets.icon import MAX_ICON_CACHE

        clear_icon_cache()
        # Mock ImageTk.PhotoImage and file presence to avoid requiring actual disk icons for this test
        dummy_img = tk.PhotoImage(master=self.app)
        with patch.object(Path, "is_file", return_value=True), \
             patch("PIL.ImageTk.PhotoImage", return_value=dummy_img), \
             patch("PIL.Image.open"):
            for i in range(MAX_ICON_CACHE + 25):
                get_icon(f"mock_icon_{i}", (16, 16), master=self.app)

        self.assertLessEqual(len(_ICON_CACHE), MAX_ICON_CACHE, f"Cache size must not exceed MAX_ICON_CACHE={MAX_ICON_CACHE}")

    def test_08_color_picker_resets_parent_and_buffers(self):
        """NguiColorPickerPopup resets parent reference and cleans buffers on close."""
        self.app.on_open_color_picker()
        picker = self.app._color_picker_win
        self.assertIsNotNone(picker)
        self.assertTrue(picker.winfo_exists())

        picker._on_close()
        self.app.update()

        self.assertIsNone(self.app._color_picker_win, "Parent _color_picker_win must be reset to None on close")
        self.assertIsNone(picker._sv_photo)
        self.assertIsNone(picker._hue_photo)
        self.assertIsNone(picker._grad_photo)


if __name__ == "__main__":
    unittest.main()
