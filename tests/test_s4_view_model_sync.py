"""
S4 — View/Model Synchronization & Widget Caret Decoupling
==========================================================
TDD tests verifying:
  - STALE-CARD-REGISTRY is cleared in close_file() empty-state and _update_views() plain-text paths.
  - Re-entrancy guard (_suppress_continuous_events) resets to False even after a render exception.
  - Ribbon helpers (on_text_cut/copy/paste) fall back to txt_dialogue on stale / missing card widgets.
  - _focus_continuous_box() does not raise on a missing card index.
  - _on_card_focus_in() and _on_card_text_edited() are no-ops during _suppress_continuous_events=True.

All tests use the HeadlessApp fixture established by prior slices (S1–S3).
"""

import sys
import os
import types
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Path bootstrap (identical to other slice test files)
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import misora  # noqa: E402


# ---------------------------------------------------------------------------
# HeadlessApp fixture
# ---------------------------------------------------------------------------
class HeadlessApp(misora.MisoraApp):
    """MisoraApp subclass that suppresses all real Tk window operations."""

    def __init__(self):
        # Redirect __init_subclass__ before super().__init__
        pass  # do NOT call super().__init__ — we monkey-patch below


def _build_headless_app() -> misora.MisoraApp:
    """Return a MisoraApp instance with Tk internals stubbed out for headless testing."""
    root = tk.Tk()
    root.withdraw()

    app = misora.MisoraApp.__new__(misora.MisoraApp)

    # Minimal tk.Tk infrastructure
    app.tk = root.tk
    app._w = root._w
    app.children = {}
    app._tclCommands = set()

    # ---- Core state mirrors (from MisoraApp.__init__) ----
    app.open_documents: dict = {}
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
    app._card_widgets: dict = {}
    app._modified_boxes: set = set()
    app._selected_boxes: set = set()
    app._locked_boxes: set = set()
    app._saved_state_checkpoints: dict = {}
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

    # Tk BooleanVars
    app.var_continuous_view = tk.BooleanVar(master=root, value=False)
    app.var_preview_compiled = tk.BooleanVar(master=root, value=False)
    app.var_select_box_mode = tk.BooleanVar(master=root, value=False)
    app.var_sync_xuat = tk.BooleanVar(master=root, value=False)

    # Stub widgets used by the methods under test
    app.txt_dialogue = tk.Text(root)
    app.txt_continuous = tk.Text(root)
    app.lbl_status = MagicMock()

    # Minimal stubs for methods we don't want to invoke
    app._update_views = MagicMock()
    app._refresh_opened_files_list = MagicMock()
    app._flush_active_widget = MagicMock(return_value=True)
    app._dirty_state_changed = MagicMock()
    app._update_raw_view = MagicMock()
    app._highlight_active_card_header = MagicMock()
    app._sync_header_controls_for_card = MagicMock()
    app._flush_continuous_card_edits = MagicMock()
    app._is_widget_packed = MagicMock(return_value=False)
    app._is_light_theme = MagicMock(return_value=True)
    app.on_save = MagicMock(return_value=True)
    app.open_file = MagicMock()
    app.show_toast = MagicMock()
    app.after = MagicMock()
    app.after_idle = MagicMock()
    app.update_idletasks = MagicMock()
    app.focus_get = MagicMock(return_value=None)
    app.grab_current = MagicMock(return_value=None)
    app._install_shortcuts_bindtag = MagicMock()
    app._on_card_paste_caret = MagicMock(return_value=None)
    app._mark_document_dirty = MagicMock()
    app._commit_widget_edit = MagicMock()

    app._root = root
    return app, root


# ---------------------------------------------------------------------------
# Base test case
# ---------------------------------------------------------------------------
class S4TestBase(unittest.TestCase):
    def setUp(self):
        self.app, self.root = _build_headless_app()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _make_mock_doc_with_boxes(self, n: int = 3):
        """Return a minimal stub StoryDocument with n dialogue boxes."""
        doc = MagicMock()
        doc.boxes = [MagicMock() for _ in range(n)]
        for i, b in enumerate(doc.boxes):
            b.clean_text = f"Box {i} text"
            b.speaker = f"Speaker{i}"
        doc.has_metadata.return_value = False
        doc.get_metadata.return_value = {}
        return doc

    def _register_live_cards(self, app, indices):
        """Install real Tk.Text card stubs for the given indices."""
        for idx in indices:
            txt = tk.Text(self.root)
            frame = tk.Frame(self.root)
            app._card_widgets[idx] = {"txt": txt, "card": frame, "hdr": tk.Frame(self.root)}

    def _register_dead_cards(self, app, indices):
        """Install destroyed Tk.Text card stubs (stale references)."""
        for idx in indices:
            txt = tk.Text(self.root)
            frame = tk.Frame(self.root)
            stub = {"txt": txt, "card": frame, "hdr": tk.Frame(self.root)}
            app._card_widgets[idx] = stub
        # Destroy the root window so all widgets are dead
        # Instead: destroy each widget individually
        for idx in indices:
            try:
                app._card_widgets[idx]["card"].destroy()
                app._card_widgets[idx]["txt"].destroy()
            except Exception:
                pass


# ===========================================================================
# Tests
# ===========================================================================

class TestS4StaleCardRegistry(S4TestBase):
    """STALE-CARD-REGISTRY defect: _clear_card_registry() called in the right places."""

    def test_01_card_registry_cleared_after_close_to_empty(self):
        """
        After closing the last open file (_card_widgets was populated),
        close_file() must call _clear_card_registry() so _card_widgets is empty.
        """
        app = self.app

        # Set up: one open document (the current file)
        fake_path = Path("D:/fake/story.unity3d").resolve()
        app.current_file_path = fake_path
        app.is_bundle_file = True
        doc = self._make_mock_doc_with_boxes(3)
        app.current_doc = doc
        app.open_documents[fake_path] = {"dirty": False, "doc": doc}

        # Populate _card_widgets with live cards
        self._register_live_cards(app, [0, 1, 2])
        self.assertEqual(len(app._card_widgets), 3)

        # Act: close the last file
        result = app.close_file(fake_path)

        # Assert: close succeeded and card registry is empty
        self.assertTrue(result)
        self.assertEqual(
            app._card_widgets, {},
            "_card_widgets must be {} after closing the last open file"
        )

    def test_02_card_registry_cleared_on_plain_text_switch(self):
        """
        _update_views() must clear _card_widgets when current_doc is None
        (plain-text file or empty state).
        Calls the REAL _update_views() after removing the stub.
        """
        app = self.app

        # Un-stub _update_views so the real one runs
        del app._update_views

        # Populate stale cards
        self._register_live_cards(app, [0, 1, 2])
        self.assertEqual(len(app._card_widgets), 3)

        # Set state: no document (plain text mode)
        app.current_doc = None
        app.current_file_path = None
        app._plain_text_content = "hello"
        app.var_continuous_view.set(False)

        # Stub all Tk widget attribute accesses the real _update_views needs
        app.speaker_var = MagicMock()
        app.lbl_box_counter = MagicMock()
        app.lbl_voice_cue = MagicMock()
        app._auto_resize_dialogue_box = MagicMock()
        app._highlight_ngui_tags = MagicMock()
        app._highlight_dialogue_matches = MagicMock()
        app._highlight_continuous_matches = MagicMock()
        app._insert_compiled_ngui_text = MagicMock()
        app.txt_raw = MagicMock()

        # Act
        app._update_views()

        # Assert
        self.assertEqual(
            app._card_widgets, {},
            "_card_widgets must be {} after _update_views() with no current_doc"
        )


class TestS4ReEntrancy(S4TestBase):
    """Re-entrancy guard: _suppress_continuous_events resets to False even on exception."""

    def test_06_suppress_events_reset_after_render_exception(self):
        """
        If _render_continuous_view() raises mid-render, _suppress_continuous_events
        must still be False after the call returns (try/finally contract).
        """
        app = self.app
        app.current_doc = self._make_mock_doc_with_boxes(2)
        app.is_bundle_file = True
        app.current_file_path = Path("D:/fake/story.unity3d")
        app.var_continuous_view.set(True)

        # Stub the frame that gets iterated — make it raise
        mock_frame = MagicMock()
        mock_frame.winfo_children.side_effect = RuntimeError("simulated render crash")
        app.cont_stream_frame = mock_frame
        # Stub other attributes needed before the crash point
        app.cont_canvas = MagicMock()
        app.cont_scroll_y = MagicMock()
        app.txt_continuous = MagicMock()
        app.gutter_cont = MagicMock()
        app.var_font_family = MagicMock()
        app.var_font_family.get = MagicMock(return_value="Segoe UI")

        self.assertFalse(app._suppress_continuous_events)

        try:
            app._render_continuous_view()
        except Exception:
            pass

        self.assertFalse(
            app._suppress_continuous_events,
            "_suppress_continuous_events must be False after _render_continuous_view() raises"
        )


class TestS4RibbonGuard(S4TestBase):
    """Ribbon methods must not raise on stale card widget references."""

    def _setup_continuous_view_with_stale_card(self, box_idx: int = 0):
        """Put app in Continuous View with a stale card at box_idx."""
        app = self.app
        app.current_doc = self._make_mock_doc_with_boxes(3)
        app.current_box_idx = box_idx
        app.is_bundle_file = True
        app.var_continuous_view.set(True)

        # Register a stale (destroyed) widget
        self._register_dead_cards(app, [box_idx])

    def test_05_ribbon_cut_on_stale_card_does_not_raise(self):
        """on_text_cut() must not raise TclError when card widget is stale."""
        self._setup_continuous_view_with_stale_card()
        try:
            self.app.on_text_cut()
        except Exception as exc:
            self.fail(f"on_text_cut() raised {exc!r} on stale card")

    def test_05b_ribbon_copy_on_stale_card_does_not_raise(self):
        """on_text_copy() must not raise TclError when card widget is stale."""
        self._setup_continuous_view_with_stale_card()
        try:
            self.app.on_text_copy()
        except Exception as exc:
            self.fail(f"on_text_copy() raised {exc!r} on stale card")

    def test_05c_ribbon_paste_on_stale_card_does_not_raise(self):
        """on_text_paste() must not raise TclError when card widget is stale."""
        self._setup_continuous_view_with_stale_card()
        try:
            self.app.on_text_paste()
        except Exception as exc:
            self.fail(f"on_text_paste() raised {exc!r} on stale card")

    def test_05d_get_card_text_widget_returns_txt_dialogue_on_missing_idx(self):
        """_get_card_text_widget() must return txt_dialogue when index not in registry."""
        app = self.app
        app._card_widgets = {}  # empty registry
        result = app._get_card_text_widget(99)
        self.assertIs(result, app.txt_dialogue)

    def test_05e_get_card_text_widget_returns_txt_dialogue_on_dead_widget(self):
        """_get_card_text_widget() must return txt_dialogue when card widget is destroyed."""
        app = self.app
        self._register_dead_cards(app, [0])
        result = app._get_card_text_widget(0)
        self.assertIs(result, app.txt_dialogue)


class TestS4FocusSafety(S4TestBase):
    """_focus_continuous_box() must not raise on out-of-range or missing card index."""

    def test_07_focus_continuous_box_missing_idx_safe(self):
        """_focus_continuous_box(999) with no card at that index must not raise."""
        app = self.app
        app.current_doc = self._make_mock_doc_with_boxes(3)
        app._card_widgets = {}  # no cards rendered
        app.current_file_path = Path("D:/fake/story.unity3d")
        try:
            app._focus_continuous_box(999)
        except Exception as exc:
            self.fail(f"_focus_continuous_box(999) raised {exc!r}")

    def test_07b_focus_continuous_box_minus1_safe(self):
        """_focus_continuous_box(-1) with no box-0 card must not raise."""
        app = self.app
        app.current_doc = self._make_mock_doc_with_boxes(3)
        app._card_widgets = {}
        app.current_file_path = Path("D:/fake/story.unity3d")
        try:
            app._focus_continuous_box(-1)
        except Exception as exc:
            self.fail(f"_focus_continuous_box(-1) raised {exc!r}")


class TestS4SuppressGuard(S4TestBase):
    """During _suppress_continuous_events=True, focus/edit handlers must be no-ops."""

    def test_08_card_focus_in_during_suppress_is_noop(self):
        """_on_card_focus_in() must do nothing when _suppress_continuous_events is True."""
        app = self.app
        app.current_doc = self._make_mock_doc_with_boxes(3)
        app._suppress_continuous_events = True
        original_box_idx = app.current_box_idx

        app._on_card_focus_in(2)

        # current_box_idx must NOT have changed
        self.assertEqual(
            app.current_box_idx, original_box_idx,
            "_on_card_focus_in() must not mutate current_box_idx during suppress"
        )
        # Highlight / sync must NOT have been called
        app._highlight_active_card_header.assert_not_called()
        app._sync_header_controls_for_card.assert_not_called()

    def test_08b_card_text_edited_during_suppress_is_noop(self):
        """_on_card_text_edited() must do nothing when _suppress_continuous_events is True."""
        app = self.app
        doc = self._make_mock_doc_with_boxes(3)
        app.current_doc = doc
        app._suppress_continuous_events = True
        app.current_file_path = Path("D:/fake/story.unity3d")

        txt_w = tk.Text(self.root)
        txt_w.insert("1.0", "changed text")

        app._on_card_text_edited(0, txt_w)

        # inject_box must NOT have been called
        doc.inject_box.assert_not_called()
        # _mark_document_dirty must NOT have been called
        app._mark_document_dirty.assert_not_called()


class TestS4ViewToggle(S4TestBase):
    """Toggle between Page and Continuous view must preserve current_box_idx."""

    def test_03_toggle_to_continuous_preserves_active_box(self):
        """
        Switching from Page View to Continuous View must preserve current_box_idx.
        Uses the stub _update_views so no real render happens.
        """
        app = self.app
        doc = self._make_mock_doc_with_boxes(5)
        app.current_doc = doc
        app.current_file_path = Path("D:/fake/story.unity3d")
        app.current_box_idx = 3
        app.is_box0_active = False

        # Stub layout widgets so toggle doesn't crash
        app.gd_scroll_wrap = MagicMock()
        app.continuous_wrap = MagicMock()
        app.lbl_gd_title = MagicMock()
        app.txt_box0_summary = MagicMock()
        app.txt_dialogue = MagicMock()
        app.txt_dialogue.count = MagicMock(return_value=(5,))

        # Switch to Continuous View
        app.var_continuous_view.set(True)
        app._on_toggle_continuous_view()

        self.assertEqual(
            app.current_box_idx, 3,
            "current_box_idx must be preserved after toggle to Continuous View"
        )

    def test_04_toggle_to_page_preserves_active_box(self):
        """
        Switching from Continuous View to Page View must preserve current_box_idx.
        """
        app = self.app
        doc = self._make_mock_doc_with_boxes(5)
        app.current_doc = doc
        app.current_file_path = Path("D:/fake/story.unity3d")
        app.current_box_idx = 2
        app.is_box0_active = False
        app.var_continuous_view.set(True)

        # Register a live card for box 2
        self._register_live_cards(app, [2])

        # Stub layout widgets
        app.gd_scroll_wrap = MagicMock()
        app.continuous_wrap = MagicMock()
        app.lbl_gd_title = MagicMock()
        app.txt_box0_summary = MagicMock()
        app.txt_dialogue = MagicMock()

        # Switch to Page View
        app.var_continuous_view.set(False)
        app._on_toggle_continuous_view()

        self.assertEqual(
            app.current_box_idx, 2,
            "current_box_idx must be preserved after toggle to Page View"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
