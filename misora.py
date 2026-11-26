#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misora: Story Editor
====================
A specialized GUI text editor for inspecting, searching, and in-place patching
of Princess Connect! Re:Dive Unity3D story bundles (.unity3d) and XUAT translation files.
"""
from __future__ import annotations

import collections
import colorsys
import concurrent.futures
import copy
import ctypes
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, font as tkfont, messagebox, ttk
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

try:
    from PIL import Image, ImageGrab, ImageTk
except ImportError:
    Image = None  # type: ignore
    ImageTk = None  # type: ignore
    ImageGrab = None  # type: ignore

if sys.platform == "win32":
    import winreg
    from ctypes import wintypes

# Ensure both Misora root and toolkit parent are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

try:
    from misora.assets.icon import THEME, apply_window_icon, get_icon, prune_icon_cache
    from misora.assets.preview_frames import (
        get_all_script_card_bottom_image,
        get_all_script_card_top_image,
        get_all_script_dotted_rule_image,
        get_dialogue_capsule_image,
        get_dialogue_nameplate_image,
        get_dialogue_triangle_image,
        get_voice_badge_image,
        prune_preview_cache,
    )
    from misora.assets.splash import MisoraSplashScreen
    from misora.core import (
        ALWAYS_ON_CATEGORY, LOG_CATEGORIES, LOG_LEVELS, Box, BoxSnapshot, BundleIOError,
        BoxEditDelta, BoxSnapshotReplaceDelta, BoxStructuralDelta, BulkFileDelta, DocumentRecordsDelta, MetadataDelta, LogEntry, MasterUndoJournal, MisoraLogger,
        PlainTextDelta, ProjectSearchEngine, Record, SearchOptions, SearchResult,
        StoryDocument, UndoOperation, XUnitySyncManager, load_bundle_story,
        save_bundle_story, dispose_unity_env,
        MTLConfig, MTLEngine, TagMasker, translate_async, MTL_ENGINES, DEFAULT_LLM_PROMPT,
        serialize, parse, sniff_format, apply_to_document, sanitize_speaker,
        DialogueBlock, MetadataBlock, ParseResult,
        NGUI_TAG_RE, NGUI_TOKEN_RE, RUBY_RE, PLACEHOLDER_RE, normalize_gradient_syntax, strip_tags, get_rendered_length, measure_line_lengths,
        protect_secret, unprotect_secret, redact_secret,
        DecodedText, detect_encoding_and_decode, encode_with_metadata,
        read_text_file_strictly, write_atomic_encoded,
        WORKSPACE_SCHEMA_VERSION, MISORA_WORKSPACE_EXT, WorkspaceError,
        LockedKeyEntry, WorkspaceFileEntry, WorkspaceDiffEntry, WorkspaceSession,
        safe_relpath, resolve_workspace_file_path, match_active_file,
        compute_workspace_diff, save_workspace, load_workspace,
        XuatIndex, build_xuat_index, build_xuat_index_async, resolve_xuat_text_roots,
        analyze_story_matches, normalize_xuat_key,
        DEFAULT_ARCHIVE_EXT, VALID_ARCHIVE_STRATEGIES, VALID_LINEBREAK_POLICIES, VALID_DUPLICATE_SCOPES,
        StaleSourceError, ArchiveTargetError, AppliedXuatRecord, CleanupCandidate,
        CleanupAnalysis, ArchiveTargetValidation, EmptyFileInfo, CleanupReport,
        default_archive_dir, validate_archive_target, apply_duplicate_scope,
        classify_cleanup_candidates, execute_cleanup, delete_empty_xuat_files,
        FontManager, PRESET_GLOBAL, PRESET_JP, BUILTIN_FONT_PRESETS,
        game_to_xuat, WrapResult, wrap_text,
    )
    from misora.core.story_ast import _INV_CMD_MAP as _AST_INV_CMD_MAP, unescape_arg as _ast_unescape_arg
except ImportError:
    from assets.icon import THEME, apply_window_icon, get_icon, prune_icon_cache
    from assets.preview_frames import (
        get_all_script_card_bottom_image,
        get_all_script_card_top_image,
        get_all_script_dotted_rule_image,
        get_dialogue_capsule_image,
        get_dialogue_nameplate_image,
        get_dialogue_triangle_image,
        get_voice_badge_image,
        prune_preview_cache,
    )
    from assets.splash import MisoraSplashScreen
    from core import (
        ALWAYS_ON_CATEGORY, LOG_CATEGORIES, LOG_LEVELS, Box, BoxSnapshot, BundleIOError,
        BoxEditDelta, BoxSnapshotReplaceDelta, BoxStructuralDelta, BulkFileDelta, DocumentRecordsDelta, MetadataDelta, LogEntry, MasterUndoJournal, MisoraLogger,
        PlainTextDelta, ProjectSearchEngine, Record, SearchOptions, SearchResult,
        StoryDocument, UndoOperation, XUnitySyncManager, load_bundle_story,
        save_bundle_story, dispose_unity_env,
        MTLConfig, MTLEngine, TagMasker, translate_async, MTL_ENGINES, DEFAULT_LLM_PROMPT,
        serialize, parse, sniff_format, apply_to_document, sanitize_speaker,
        DialogueBlock, MetadataBlock, ParseResult,
        NGUI_TAG_RE, NGUI_TOKEN_RE, RUBY_RE, PLACEHOLDER_RE, normalize_gradient_syntax, strip_tags, get_rendered_length, measure_line_lengths,
        protect_secret, unprotect_secret, redact_secret,
        DecodedText, detect_encoding_and_decode, encode_with_metadata,
        read_text_file_strictly, write_atomic_encoded,
        WORKSPACE_SCHEMA_VERSION, MISORA_WORKSPACE_EXT, WorkspaceError,
        LockedKeyEntry, WorkspaceFileEntry, WorkspaceDiffEntry, WorkspaceSession,
        safe_relpath, resolve_workspace_file_path, match_active_file,
        compute_workspace_diff, save_workspace, load_workspace,
        XuatIndex, build_xuat_index, build_xuat_index_async, resolve_xuat_text_roots,
        analyze_story_matches, normalize_xuat_key,
        DEFAULT_ARCHIVE_EXT, VALID_ARCHIVE_STRATEGIES, VALID_LINEBREAK_POLICIES, VALID_DUPLICATE_SCOPES,
        StaleSourceError, ArchiveTargetError, AppliedXuatRecord, CleanupCandidate,
        CleanupAnalysis, ArchiveTargetValidation, EmptyFileInfo, CleanupReport,
        default_archive_dir, validate_archive_target, apply_duplicate_scope,
        classify_cleanup_candidates, execute_cleanup, delete_empty_xuat_files,
        FontManager, PRESET_GLOBAL, PRESET_JP, BUILTIN_FONT_PRESETS,
        game_to_xuat, WrapResult, wrap_text,
    )
    from core.story_ast import _INV_CMD_MAP as _AST_INV_CMD_MAP, unescape_arg as _ast_unescape_arg

try:
    from misora.core.security import DPAPISecurityError
except ImportError:
    from core.security import DPAPISecurityError

_ORIG_TRANSLATE_ASYNC = translate_async

CONFIG_PATH = SCRIPT_DIR / "misora_config.json"
DEBUG_LOG_PATH = SCRIPT_DIR / "misora_debug.log"
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Support Me Dialog configuration (U05)
SHOW_PAYPAL_BUTTON: bool = True
SUPPORT_URL_KOFI: str = "https://ko-fi.com/imaterial"
SUPPORT_URL_PATREON: str = "https://patreon.com/imaterial"
SUPPORT_URL_PAYPAL: str = "https://paypal.me/CorneliaCrimson"
SUPPORT_CAPTION_ID: str = (
    "Terima kasih. Dukungan sekecil apa pun sangat saya hargai; "
    "ini juga membantu menutup biaya penggunaan AI."
)


def _put_queue_cancellable(
    q: queue.Queue,
    item: Any,
    cancel_event: Optional[threading.Event] = None,
    legacy_flag_getter: Optional[Callable[[], bool]] = None,
) -> bool:
    """Put item into a bounded queue with cooperative cancellation on queue.Full (BUG-01)."""
    while True:
        cancelled = (cancel_event is not None and cancel_event.is_set()) or (
            legacy_flag_getter is not None and legacy_flag_getter()
        )
        try:
            q.put(item, timeout=0.05)
            return True
        except queue.Full:
            cancelled = (cancel_event is not None and cancel_event.is_set()) or (
                legacy_flag_getter is not None and legacy_flag_getter()
            )
            if cancelled:
                return False


def _get_app_version() -> str:
    """Retrieve application version string from root __init__.py as single source of truth (Rule 21)."""
    try:
        import __init__ as _root_init
        if hasattr(_root_init, "__version__"):
            return _root_init.__version__
    except Exception:
        pass
    try:
        init_file = SCRIPT_DIR / "__init__.py"
        if init_file.is_file():
            for line in init_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("__version__"):
                    parts = line.split("=")
                    if len(parts) == 2:
                        return parts[1].strip().strip('"\'')
    except Exception:
        pass
    return "0.0.0-unknown"

__version__ = _get_app_version()


class ToolTip:
    """Robust hover tooltip for Tkinter widgets with delayed display and safe lifecycle (Part C.5 / TOOLTIP-LIFECYCLE)."""

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 350):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None
        setattr(self.widget, "_tooltip", self)

        if hasattr(self.widget, "bind"):
            self.widget.bind("<Enter>", self.on_enter, add="+")
            self.widget.bind("<Leave>", self.on_leave, add="+")
            self.widget.bind("<Destroy>", self.on_destroy, add="+")

    def on_enter(self, _event=None) -> None:
        self.cancel_timer()
        if not self.text or not self.widget_exists():
            return
        try:
            self._after_id = self.widget.after(self.delay_ms, self.show_tip)
        except Exception:
            pass

    def on_leave(self, _event=None) -> None:
        self.cancel_timer()
        self.hide_tip()

    def on_destroy(self, _event=None) -> None:
        self.cancel_timer()
        self.hide_tip()

    def cancel_timer(self) -> None:
        if self._after_id and self.widget_exists():
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None

    def widget_exists(self) -> bool:
        try:
            return bool(self.widget and self.widget.winfo_exists())
        except Exception:
            return False

    def show_tip(self) -> None:
        self._after_id = None
        if self.tip_window or not self.text or not self.widget_exists():
            return
        try:
            x = self.widget.winfo_rootx() + 8
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tw,
                text=self.text,
                justify="left",
                background="#201a33",
                foreground="#ffffff",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 8),
                padx=6,
                pady=3,
            )
            label.pack(ipadx=1)
        except Exception:
            self.hide_tip()

    def hide_tip(self, _event=None) -> None:
        if self.tip_window:
            try:
                if self.tip_window.winfo_exists():
                    self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None


def create_tooltip(widget: tk.Widget, text: str, delay_ms: int = 350) -> ToolTip:
    """Convenience helper to attach a hover tooltip to a widget."""
    return ToolTip(widget, text, delay_ms=delay_ms)




THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "Misora Purple & White": {
        "bg_dark": "#f3eefb",
        "bg_panel": "#ffffff",
        "bg_editor": "#faf8fe",
        "border": "#d4c4ec",
        "fg_text": "#221833",
        "fg_muted": "#6b5a88",
        "misora_pink": "#7b42bc",
        "misora_pink_hover": "#9056d2",
        "misora_pink_active": "#612ea0",
        "accent_blue": "#536dfe",
        "accent_green": "#2e7d32",
        "accent_yellow": "#8e24aa",
        "highlight_bg": "#e8dbfa",
    },
    "Misora Classic (Dark)": {
        "bg_dark": "#14141a",
        "bg_panel": "#1e1e26",
        "bg_editor": "#181820",
        "border": "#30303e",
        "fg_text": "#f0f0f5",
        "fg_muted": "#9898a8",
        "misora_pink": "#ff7da7",
        "misora_pink_hover": "#ff99ba",
        "misora_pink_active": "#e05a87",
        "accent_blue": "#68b5f3",
        "accent_green": "#6ad18a",
        "accent_yellow": "#f5c26b",
        "highlight_bg": "#382433",
    },
    "Midnight Violet": {
        "bg_dark": "#161224",
        "bg_panel": "#201a33",
        "bg_editor": "#130f20",
        "border": "#3a2f5c",
        "fg_text": "#f1ecfa",
        "fg_muted": "#9c8ec0",
        "misora_pink": "#a66cff",
        "misora_pink_hover": "#b98aff",
        "misora_pink_active": "#894be8",
        "accent_blue": "#79c0ff",
        "accent_green": "#7ee787",
        "accent_yellow": "#e3b341",
        "highlight_bg": "#362459",
    },
    "Clean Daylight": {
        "bg_dark": "#eceef2",
        "bg_panel": "#ffffff",
        "bg_editor": "#f8f9fb",
        "border": "#cfd5e0",
        "fg_text": "#1f2430",
        "fg_muted": "#606a7e",
        "misora_pink": "#6f42c1",
        "misora_pink_hover": "#8458d4",
        "misora_pink_active": "#5932a3",
        "accent_blue": "#0969da",
        "accent_green": "#1a7f37",
        "accent_yellow": "#9a6700",
        "highlight_bg": "#e6dcf8",
    },
}

DIALOGUE_MAX_DIGITS: int = 54
DIALOGUE_MAX_LINES: int = 3

DEFAULT_PREFS: Dict[str, Any] = {
    "dialogue_font_family": PRESET_GLOBAL,
    "dialogue_font_size": 11,
    "raw_font_size": 9,
    "ui_font_size": 9,
    "theme": dict(THEME_PRESETS["Misora Purple & White"]),
    "debug": {
        "log_to_file": False,
        "level": "Info",
        "categories": {cat: True for cat in LOG_CATEGORIES},
    },
}

PRICONNE_SWATCHES: List[Tuple[str, str]] = [
    ("Misora Purple", "#7b42bc"),
    ("Misora Pink", "#ff7da7"),
    ("Astrum Blue", "#4a90e2"),
    ("Pecorine Gold", "#e5a93b"),
    ("Kokkoro Mint", "#2e9e5b"),
    ("Kyaru Violet", "#8e44ad"),
    ("Crimson Alert", "#d94862"),
    ("Pure White", "#ffffff"),
    ("Deep Plum", "#221833"),
    ("Soft Silver", "#9aa3b2"),
]

NGUI_GLOSSARY_ITEMS: List[Dict[str, str]] = [
    {
        "tag": "[rub:ruby]base[/rub]",
        "title": "Ruby / Furigana Text (Priconne NGUI)",
        "syntax": "[rub:Command]Wish[/rub]",
        "insert_open": "[rub:]",
        "insert_close": "[/rub]",
        "action": "ruby",
        "desc": "Cygames' custom Priconne NGUI tag. Renders 'ruby' in small text centered directly above 'base' (e.g., [rub:めいれい]願い[/rub]). Double-click or press Ctrl+R to wrap selected text.",
    },
    {
        "tag": "[RRGGBB]",
        "title": "Hex RGB Text Color",
        "syntax": "[7B42BC]Colored text[-]",
        "insert_open": "[7B42BC]",
        "insert_close": "[-]",
        "desc": "Changes text color starting at the tag using a 6-digit hexadecimal RGB code. Always close with [-] to restore default label color.",
    },
    {
        "tag": "[RRGGBBAA]",
        "title": "Hex RGBA Color + Alpha",
        "syntax": "[FFFFFF80]Semi-transparent[-]",
        "insert_open": "[FFFFFF80]",
        "insert_close": "[-]",
        "desc": "Sets both RGB color and alpha opacity (00 = invisible, FF = opaque) in NGUI UILabel.",
    },
    {
        "tag": "[RRGGBB-RRGGBB]",
        "title": "Vertical Gradient Color (Top-Bottom)",
        "syntax": "[7B42BC-FF7DA7]Gradient text[-]",
        "insert_open": "[7B42BC-FF7DA7]",
        "insert_close": "[-]",
        "desc": "Applies a top-to-bottom vertical gradient using a hyphen (-) between top and bottom hex colors. Note: NGUI requires '-' (comma syntax displays as literal text). Close with [-].",
    },
    {
        "tag": "[RRGGBBAA-RRGGBBAA]",
        "title": "Vertical Gradient Color + Alpha",
        "syntax": "[FF7DA7FF-68B5F380]Alpha gradient[-]",
        "insert_open": "[FF7DA7FF-68B5F380]",
        "insert_close": "[-]",
        "desc": "Applies a top-to-bottom vertical gradient with per-stop alpha opacity (00 = invisible, FF = opaque). Close with [-].",
    },
    {
        "tag": "[-]",
        "title": "Reset / Close Color Tag",
        "syntax": "[68B5F3]Blue[-] Normal",
        "insert_open": "[-]",
        "insert_close": "",
        "desc": "Pops the active [RRGGBB] or gradient color override and returns to the default dialogue text color.",
    },
    {
        "tag": "[/]",
        "title": "Reset / Close Style Tag (Shorthand)",
        "syntax": "[b][i]Bold italic[/] Normal",
        "insert_open": "[/]",
        "insert_close": "",
        "desc": "NGUI shorthand tag that closes active text formatting styles ([b], [i], [u], [s], [sub], [sup]).",
    },
    {
        "tag": "[b]...[/b]",
        "title": "Bold Style",
        "syntax": "[b]Emphasized text[/b]",
        "insert_open": "[b]",
        "insert_close": "[/b]",
        "desc": "Renders enclosed text in bold weight inside NGUI rich-text labels.",
    },
    {
        "tag": "[i]...[/i]",
        "title": "Italic Style",
        "syntax": "[i]Whispered thought[/i]",
        "insert_open": "[i]",
        "insert_close": "[/i]",
        "desc": "Slants enclosed text in italics for inner monologues, emphasis, or foreign terms.",
    },
    {
        "tag": "[u]...[/u]",
        "title": "Underline Style",
        "syntax": "[u]Underlined phrase[/u]",
        "insert_open": "[u]",
        "insert_close": "[/u]",
        "desc": "Draws an underline beneath the enclosed characters.",
    },
    {
        "tag": "[s]...[/s]",
        "title": "Strikethrough Style",
        "syntax": "[s]Crossed-out text[/s]",
        "insert_open": "[s]",
        "insert_close": "[/s]",
        "desc": "Draws a horizontal strikethrough line across the enclosed text.",
    },
    {
        "tag": "[sub]...[/sub]",
        "title": "Subscript Text",
        "syntax": "H[sub]2[/sub]O",
        "insert_open": "[sub]",
        "insert_close": "[/sub]",
        "desc": "Shrinks and lowers enclosed characters below the text baseline.",
    },
    {
        "tag": "[sup]...[/sup]",
        "title": "Superscript Text",
        "syntax": "10[sup]th[/sup] Anniversary",
        "insert_open": "[sup]",
        "insert_close": "[/sup]",
        "desc": "Shrinks and raises enclosed characters above the text baseline.",
    },
    {
        "tag": "[url=...]...[/url]",
        "title": "Clickable URL / Link Tag",
        "syntax": "[url=https://example.com]Link[/url]",
        "insert_open": "[url=]",
        "insert_close": "[/url]",
        "desc": "Marks a clickable text span retrievable via NGUI UILabel.GetUrlAtPosition().",
    },
    {
        "tag": "[c]...[/c]",
        "title": "Ignore Label Tint",
        "syntax": "[c]Untinted text[/c]",
        "insert_open": "[c]",
        "insert_close": "[/c]",
        "desc": "Prevents NGUI's widget color multiplier from tinting the enclosed characters.",
    },
    {
        "tag": "{playername}",
        "title": "Player Name Placeholder",
        "syntax": "Good morning, {playername}!",
        "insert_open": "{playername}",
        "insert_close": "",
        "desc": "Represents the protagonist's name in Misora & XUAT .txt dictionaries. Automatically compiled to {0} when saving .unity3d bundles.",
    },
    {
        "tag": "\\n",
        "title": "Explicit Line Break",
        "syntax": "First line\\nSecond line",
        "insert_open": "\\n",
        "insert_close": "",
        "desc": "Forces a line break inside the ADV dialogue box. Pressing Enter in the editor automatically serializes the bundle's line break format.",
    },
    {
        "tag": "──",
        "title": "ADV Dialogue Pause / Dash",
        "syntax": "──Wait right there!",
        "insert_open": "──",
        "insert_close": "",
        "desc": "Standard double box-drawing horizontal dash used at the start of Priconne dialogue interruptions.",
    },
]


# -----------------------------------------------------------------------------
# WCAG 2.1 Contrast-Safe Color Utilities (#13)
# -----------------------------------------------------------------------------
def wcag_relative_luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance in [0.0, 1.0] for a #RRGGBB hex string."""
    if not HEX_COLOR_RE.match(hex_color):
        return 0.0

    def _lin(c8: int) -> float:
        s = c8 / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r = _lin(int(hex_color[1:3], 16))
    g = _lin(int(hex_color[3:5], 16))
    b = _lin(int(hex_color[5:7], 16))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Compute WCAG 2.1 contrast ratio in [1.0, 21.0] between two #RRGGBB colors."""
    la = wcag_relative_luminance(hex_a)
    lb = wcag_relative_luminance(hex_b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def best_contrast_fg(
    bg_hex: str,
    dark_fg: str = "#14141a",
    light_fg: str = "#ffffff",
) -> str:
    """Pick whichever of `dark_fg` or `light_fg` maximizes WCAG contrast on `bg_hex`."""
    if not HEX_COLOR_RE.match(bg_hex):
        return light_fg
    c_dark = wcag_contrast_ratio(bg_hex, dark_fg)
    c_light = wcag_contrast_ratio(bg_hex, light_fg)
    return light_fg if c_light >= c_dark else dark_fg


def _ensure_wcag_fg(
    preferred_hex: str,
    bg_hex: str,
    dark_fg: str = "#14141a",
    light_fg: str = "#ffffff",
    min_ratio: float = 4.5,
) -> str:
    """Return `preferred_hex` if it achieves >= `min_ratio` on `bg_hex`, else `best_contrast_fg`."""
    if HEX_COLOR_RE.match(preferred_hex) and HEX_COLOR_RE.match(bg_hex):
        if wcag_contrast_ratio(preferred_hex, bg_hex) >= min_ratio:
            return preferred_hex
    return best_contrast_fg(bg_hex, dark_fg, light_fg)


def _wcag_muted_fg(
    muted_hex: str,
    bg_hex: str,
    fallback_fg: str,
    min_ratio: float = 4.6,
) -> str:
    """Adjust `muted_hex` toward `fallback_fg` only as needed to reach WCAG `min_ratio` on `bg_hex`."""
    if not (HEX_COLOR_RE.match(muted_hex) and HEX_COLOR_RE.match(bg_hex) and HEX_COLOR_RE.match(fallback_fg)):
        return fallback_fg
    if wcag_contrast_ratio(muted_hex, bg_hex) >= min_ratio:
        return muted_hex
    mr, mg, mb = int(muted_hex[1:3], 16), int(muted_hex[3:5], 16), int(muted_hex[5:7], 16)
    fr, fg_c, fb = int(fallback_fg[1:3], 16), int(fallback_fg[3:5], 16), int(fallback_fg[5:7], 16)
    for step in range(1, 21):
        alpha = step / 20.0
        cand = f"#{int(mr + (fr - mr) * alpha):02x}{int(mg + (fg_c - mg) * alpha):02x}{int(mb + (fb - mb) * alpha):02x}"
        if wcag_contrast_ratio(cand, bg_hex) >= min_ratio:
            return cand
    return fallback_fg


def init_process_dpi_awareness() -> None:
    """Set process DPI awareness once at application startup before creating Tk root (Rule 23).

    Ensures consistent rendering scale across displays without mutating process DPI
    awareness dynamically during GUI execution.
    """
    if sys.platform != "win32":
        return
    try:
        # Try SetProcessDpiAwarenessContext (Windows 10 1703+)
        # -2 = DPI_AWARENESS_CONTEXT_SYSTEM_AWARE
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-2))
    except Exception:
        try:
            # Fallback to shcore (Windows 8.1+)
            # 1 = PROCESS_SYSTEM_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                # Fallback to user32 (Vista+)
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def sanitize_window_geometry(geom_str: str, screen_w: int, screen_h: int) -> str:
    """Validate and clamp a Tk geometry string to ensure it is within visible screen bounds (S9c)."""
    if not isinstance(geom_str, str) or not geom_str.strip():
        return ""
    m = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", geom_str.strip())
    if not m:
        return geom_str.strip()
    w, h, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))

    # Bound dimensions to screen limits
    if screen_w > 0:
        w = max(400, min(w, screen_w))
    if screen_h > 0:
        h = max(300, min(h, screen_h))

    # Clamp x coordinate so at least 120px is within screen bounds
    if screen_w > 0:
        if x + 120 > screen_w or x < 0:
            x = max(0, min(x, max(0, screen_w - w)))

    # Clamp y coordinate so title bar (top 50px) is visible
    if screen_h > 0:
        if y + 50 > screen_h or y < 0:
            y = max(0, min(y, max(0, screen_h - h)))

    return f"{w}x{h}+{x}+{y}"


class NguiColorPickerPopup(tk.Toplevel):
    """Mini texture-editor style Color Picker & Gradient Builder with Screen Eyedropper."""

    SV_W = 180
    SV_H = 140
    HUE_W = 20
    HUE_H = 140

    def __init__(
        self,
        parent: "MisoraApp",
        primary_hex: str = "#7b42bc",
        secondary_hex: str = "#ff7da7",
    ):
        super().__init__(parent)
        self.app = parent
        self.theme = parent.theme
        self.title(f"NGUI Color & Gradient Picker (v{__version__})")
        self.configure(bg=self.theme["bg_panel"])
        self.transient(parent)

        try:
            self.stop_colors: List[str] = [
                primary_hex.lower() if HEX_COLOR_RE.match(primary_hex) else "#7b42bc",
                secondary_hex.lower() if HEX_COLOR_RE.match(secondary_hex) else "#ff7da7",
            ]
            self.active_stop: int = 0
            self._eyedropper_active: bool = False
            self._eyedropper_after_id: Optional[str] = None
            self._mouse_was_down: bool = False

            r = int(self.stop_colors[0][1:3], 16) / 255.0
            g = int(self.stop_colors[0][3:5], 16) / 255.0
            b = int(self.stop_colors[0][5:7], 16) / 255.0
            self._h, self._s, self._v = colorsys.rgb_to_hsv(r, g, b)

            self._sv_photo: Any = None
            self._hue_photo: Any = None
            self._grad_photo: Any = None

            self._build_ui()
            self._render_hue_bar()
            self._render_sv_map()
            self._sync_ui_from_hsv()

            self.update_idletasks()
            req_w = max(420, self.winfo_reqwidth())
            req_h = max(340, self.winfo_reqheight())
            px = parent.winfo_rootx() + (parent.winfo_width() // 2) - (req_w // 2)
            py = parent.winfo_rooty() + (parent.winfo_height() // 2) - (req_h // 2)
            self.geometry(f"{req_w}x{req_h}+{max(20, px)}+{max(20, py)}")
            self.minsize(req_w, req_h)
            self.resizable(False, False)
            self.app.logger.info("UI / Theme / Config", f"NguiColorPickerPopup initialized ({req_w}x{req_h})")
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                self.app.logger.exception(f"NguiColorPickerPopup initialization failed:\n{err}")
            except Exception:
                pass
            messagebox.showerror("Color Picker Init Error", err)
            raise

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", self._on_escape)

    def _build_ui(self) -> None:
        t = self.theme
        accent_fg = best_contrast_fg(t["misora_pink"])
        accent_hover_fg = best_contrast_fg(t["misora_pink_hover"])
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        stop_bar = tk.Frame(self, bg=t["bg_panel"])
        stop_bar.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            stop_bar,
            text="Target Stop:",
            font=("Segoe UI", 9, "bold"),
            bg=t["bg_panel"],
            fg=best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff"),
        ).pack(side="left", padx=(0, 6))

        self.btn_stop0 = tk.Button(
            stop_bar,
            text="1: Primary / Top",
            font=("Segoe UI", 8, "bold"),
            relief="solid",
            bd=1,
            cursor="hand2",
            command=lambda: self._select_stop(0),
        )
        self.btn_stop0.pack(side="left", padx=(0, 4))

        self.btn_stop1 = tk.Button(
            stop_bar,
            text="2: Gradient Bottom",
            font=("Segoe UI", 8, "bold"),
            relief="solid",
            bd=1,
            cursor="hand2",
            command=lambda: self._select_stop(1),
        )
        self.btn_stop1.pack(side="left")

        map_row = tk.Frame(self, bg=t["bg_panel"])
        map_row.pack(fill="x", padx=12, pady=4)

        self.canvas_sv = tk.Canvas(
            map_row,
            width=self.SV_W,
            height=self.SV_H,
            bd=1,
            relief="solid",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas_sv.pack(side="left")
        self.canvas_sv.bind("<Button-1>", self._on_sv_drag)
        self.canvas_sv.bind("<B1-Motion>", self._on_sv_drag)

        self.canvas_hue = tk.Canvas(
            map_row,
            width=self.HUE_W,
            height=self.HUE_H,
            bd=1,
            relief="solid",
            highlightthickness=0,
            cursor="sb_v_double_arrow",
        )
        self.canvas_hue.pack(side="left", padx=(8, 10))
        self.canvas_hue.bind("<Button-1>", self._on_hue_drag)
        self.canvas_hue.bind("<B1-Motion>", self._on_hue_drag)

        side_col = tk.Frame(map_row, bg=t["bg_panel"])
        side_col.pack(side="left", fill="y")

        swatch_pair = tk.Frame(side_col, bg=t["bg_panel"])
        swatch_pair.pack(fill="x", pady=(0, 6))

        self.lbl_swatch_active = tk.Label(
            swatch_pair,
            width=7,
            height=2,
            bg=self.stop_colors[0],
            relief="solid",
            bd=1,
        )
        self.lbl_swatch_active.pack(side="left")

        self.canvas_grad_preview = tk.Canvas(
            swatch_pair,
            width=46,
            height=34,
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        self.canvas_grad_preview.pack(side="left", padx=(6, 0))

        hex_row = tk.Frame(side_col, bg=t["bg_panel"])
        hex_row.pack(fill="x", pady=2)
        tk.Label(hex_row, text="Hex:", font=("Segoe UI", 8, "bold"), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left")
        self.var_hex = tk.StringVar(master=self, value=self.stop_colors[0].upper())
        ent_hex = tk.Entry(
            hex_row,
            textvariable=self.var_hex,
            width=9,
            font=("Consolas", 9, "bold"),
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        ent_hex.pack(side="right")
        ent_hex.bind("<Return>", self._on_hex_entry_commit)
        ent_hex.bind("<FocusOut>", self._on_hex_entry_commit)

        self.lbl_rgb = tk.Label(
            side_col,
            text="RGB: 123, 66, 188",
            font=("Consolas", 8),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
            anchor="w",
        )
        self.lbl_rgb.pack(fill="x", pady=(2, 6))

        self.btn_eyedropper = tk.Button(
            side_col,
            text="💧 Eyedropper",
            font=("Segoe UI", 8, "bold"),
            bg=t["bg_editor"],
            fg=editor_fg,
            activebackground=t["highlight_bg"],
            activeforeground=best_contrast_fg(t["highlight_bg"]),
            relief="solid",
            bd=1,
            padx=6,
            pady=3,
            cursor="hand2",
            command=self._toggle_eyedropper,
        )
        self.btn_eyedropper.pack(fill="x")

        self.lbl_eye_hint = tk.Label(
            side_col,
            text="",
            font=("Segoe UI", 7),
            bg=t["bg_panel"],
            fg=t["accent_blue"],
            wraplength=112,
            justify="left",
        )
        self.lbl_eye_hint.pack(fill="x", pady=(3, 0))

        sw_frame = tk.Frame(self, bg=t["bg_panel"])
        sw_frame.pack(fill="x", padx=12, pady=(6, 4))
        tk.Label(
            sw_frame,
            text="Quick Swatches:",
            font=("Segoe UI", 8),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
        ).pack(side="left", padx=(0, 6))

        for _name, hex_c in PRICONNE_SWATCHES:
            sb = tk.Button(
                sw_frame,
                width=2,
                height=1,
                bg=hex_c,
                activebackground=hex_c,
                relief="solid",
                bd=1,
                cursor="hand2",
                command=lambda c=hex_c: self._set_color_hex(c),
            )
            sb.pack(side="left", padx=1)

        act_bar = tk.Frame(self, bg=t["bg_panel"])
        act_bar.pack(fill="x", padx=12, pady=(8, 12))

        self.btn_insert_single = tk.Button(
            act_bar,
            text=f"Insert [{self.stop_colors[0][1:].upper()}]",
            font=("Segoe UI", 9, "bold"),
            bg=t["misora_pink"],
            fg=accent_fg,
            activebackground=t["misora_pink_hover"],
            activeforeground=accent_hover_fg,
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._commit_single_color,
        )
        self.btn_insert_single.pack(side="left", padx=(0, 6))

        self.btn_insert_grad = tk.Button(
            act_bar,
            text="Insert Gradient [1-2]",
            font=("Segoe UI", 9, "bold"),
            bg=t["bg_editor"],
            fg=editor_fg,
            activebackground=t["highlight_bg"],
            activeforeground=best_contrast_fg(t["highlight_bg"]),
            relief="solid",
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._commit_gradient_color,
        )
        self.btn_insert_grad.pack(side="left")

        ttk.Button(act_bar, text="Close", style="TButton", command=self._on_close).pack(side="right")

    def _select_stop(self, stop_idx: int) -> None:
        self.active_stop = stop_idx
        hex_c = self.stop_colors[stop_idx]
        r = int(hex_c[1:3], 16) / 255.0
        g = int(hex_c[3:5], 16) / 255.0
        b = int(hex_c[5:7], 16) / 255.0
        self._h, self._s, self._v = colorsys.rgb_to_hsv(r, g, b)
        self._render_sv_map()
        self._sync_ui_from_hsv()

    def _render_hue_bar(self) -> None:
        w, h = self.HUE_W, self.HUE_H
        if Image is not None and ImageTk is not None:
            raw = bytearray(w * h * 3)
            h_denom = max(1, h - 1)
            idx = 0
            for y in range(h):
                hue = y / h_denom
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                rb = int(r * 255)
                gb = int(g * 255)
                bb = int(b * 255)
                for _ in range(w):
                    raw[idx] = rb
                    raw[idx + 1] = gb
                    raw[idx + 2] = bb
                    idx += 3
            im = Image.frombytes("RGB", (w, h), bytes(raw))
            img = ImageTk.PhotoImage(im, master=self)
        else:
            img = tk.PhotoImage(master=self, width=w, height=h)
            rows: List[str] = []
            for y in range(h):
                hue = y / max(1, h - 1)
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                hx = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
                rows.append("{" + " ".join([hx] * w) + "}")
            img.put(" ".join(rows))
        self._hue_photo = img
        self.canvas_hue.image = img
        self.canvas_hue.delete("all")
        self.canvas_hue.create_image(0, 0, anchor="nw", image=img)

    def _render_sv_map(self) -> None:
        w, h = self.SV_W, self.SV_H
        hue = self._h
        if Image is not None and ImageTk is not None:
            raw = bytearray(w * h * 3)
            w_denom = max(1, w - 1)
            h_denom = max(1, h - 1)
            idx = 0
            for y in range(h):
                v = 1.0 - (y / h_denom)
                for x in range(w):
                    s = x / w_denom
                    r, g, b = colorsys.hsv_to_rgb(hue, s, v)
                    raw[idx] = int(r * 255)
                    raw[idx + 1] = int(g * 255)
                    raw[idx + 2] = int(b * 255)
                    idx += 3
            im = Image.frombytes("RGB", (w, h), bytes(raw))
            img = ImageTk.PhotoImage(im, master=self)
        else:
            img = tk.PhotoImage(master=self, width=w, height=h)
            rows = []
            w_denom = max(1, w - 1)
            h_denom = max(1, h - 1)
            for y in range(h):
                v = 1.0 - (y / h_denom)
                row_colors: List[str] = []
                for x in range(w):
                    s = x / w_denom
                    r, g, b = colorsys.hsv_to_rgb(hue, s, v)
                    row_colors.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
                rows.append("{" + " ".join(row_colors) + "}")
            img.put(" ".join(rows))
        self._sv_photo = img
        self.canvas_sv.image = img
        self.canvas_sv.delete("all")
        self.canvas_sv.create_image(0, 0, anchor="nw", image=img)

    def _render_gradient_preview(self) -> None:
        w, h = 46, 34
        c1, c2 = self.stop_colors[0], self.stop_colors[1]
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        if Image is not None and ImageTk is not None:
            raw = bytearray(w * h * 3)
            denom = max(1, h - 1)
            idx = 0
            for y in range(h):
                t = y / denom
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                for _ in range(w):
                    raw[idx] = r
                    raw[idx + 1] = g
                    raw[idx + 2] = b
                    idx += 3
            im = Image.frombytes("RGB", (w, h), bytes(raw))
            img = ImageTk.PhotoImage(im, master=self)
        else:
            img = tk.PhotoImage(master=self, width=w, height=h)
            rows = []
            denom = max(1, h - 1)
            for y in range(h):
                t = y / denom
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                hx = f"#{r:02x}{g:02x}{b:02x}"
                rows.append("{" + " ".join([hx] * w) + "}")
            img.put(" ".join(rows))
        self._grad_photo = img
        self.canvas_grad_preview.image = img
        self.canvas_grad_preview.delete("all")
        self.canvas_grad_preview.create_image(0, 0, anchor="nw", image=img)

    def _sync_ui_from_hsv(self) -> None:
        t = self.theme
        r_f, g_f, b_f = colorsys.hsv_to_rgb(self._h, self._s, self._v)
        r_i, g_i, b_i = int(round(r_f * 255)), int(round(g_f * 255)), int(round(b_f * 255))
        hex_c = f"#{r_i:02x}{g_i:02x}{b_i:02x}"
        self.stop_colors[self.active_stop] = hex_c

        cx = int(round(self._s * (self.SV_W - 1)))
        cy = int(round((1.0 - self._v) * (self.SV_H - 1)))
        self.canvas_sv.delete("cursor")
        ring_color = best_contrast_fg(hex_c)
        self.canvas_sv.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline=ring_color, width=2, tags="cursor")

        hy = int(round(self._h * (self.HUE_H - 1)))
        self.canvas_hue.delete("cursor")
        self.canvas_hue.create_rectangle(0, max(0, hy - 2), self.HUE_W, min(self.HUE_H, hy + 2), outline="#ffffff", width=2, tags="cursor")

        self.lbl_swatch_active.configure(bg=hex_c)
        self.var_hex.set(hex_c.upper())
        self.lbl_rgb.configure(text=f"RGB: {r_i}, {g_i}, {b_i}")
        self._render_gradient_preview()

        accent_fg = best_contrast_fg(t["misora_pink"])
        inactive_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        if self.active_stop == 0:
            self.btn_stop0.configure(bg=t["misora_pink"], fg=accent_fg)
            self.btn_stop1.configure(bg=t["bg_editor"], fg=inactive_fg)
        else:
            self.btn_stop0.configure(bg=t["bg_editor"], fg=inactive_fg)
            self.btn_stop1.configure(bg=t["misora_pink"], fg=accent_fg)

        c0_code = self.stop_colors[0][1:].upper()
        c1_code = self.stop_colors[1][1:].upper()
        self.btn_insert_single.configure(text=f"Insert [{c0_code}]")
        self.btn_insert_grad.configure(text=f"Insert [{c0_code}-{c1_code}]")

        self.app._set_ribbon_colors(self.stop_colors[0], self.stop_colors[1])

    def _on_sv_drag(self, event: tk.Event) -> None:
        x = max(0, min(self.SV_W - 1, event.x))
        y = max(0, min(self.SV_H - 1, event.y))
        self._s = x / max(1, self.SV_W - 1)
        self._v = 1.0 - (y / max(1, self.SV_H - 1))
        self._sync_ui_from_hsv()

    def _on_hue_drag(self, event: tk.Event) -> None:
        y = max(0, min(self.HUE_H - 1, event.y))
        self._h = y / max(1, self.HUE_H - 1)
        self._render_sv_map()
        self._sync_ui_from_hsv()

    def _set_color_hex(self, hex_str: str) -> None:
        val = hex_str.strip()
        if not val.startswith("#"):
            val = "#" + val
        if not HEX_COLOR_RE.match(val):
            return
        val = val.lower()
        r = int(val[1:3], 16) / 255.0
        g = int(val[3:5], 16) / 255.0
        b = int(val[5:7], 16) / 255.0
        self._h, self._s, self._v = colorsys.rgb_to_hsv(r, g, b)
        self._render_sv_map()
        self._sync_ui_from_hsv()

    def _on_hex_entry_commit(self, _event: Optional[tk.Event] = None) -> None:
        val = self.var_hex.get().strip()
        if not val.startswith("#"):
            val = "#" + val
        if HEX_COLOR_RE.match(val):
            self._set_color_hex(val)
        else:
            self.var_hex.set(self.stop_colors[self.active_stop].upper())

    def _toggle_eyedropper(self) -> None:
        if self._eyedropper_active:
            self._stop_eyedropper()
            return

        if sys.platform != "win32":
            self.lbl_eye_hint.configure(text="Screen eyedropper requires Windows; use map or swatches.")
            return

        self._eyedropper_active = True
        self._waiting_for_release = True
        self.btn_eyedropper.configure(
            text="Sampling... (Click)",
            bg=self.theme["misora_pink"],
            fg=best_contrast_fg(self.theme["misora_pink"]),
        )
        self.lbl_eye_hint.configure(text="Move cursor over any pixel on screen & Left-Click (Esc to cancel).")
        self._poll_eyedropper()

    def _poll_eyedropper(self) -> None:
        if not self._eyedropper_active or not self.winfo_exists():
            return

        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))

            sampled_hex = None
            if ImageGrab is not None:
                try:
                    px = ImageGrab.grab(bbox=(pt.x, pt.y, pt.x + 1, pt.y + 1)).getpixel((0, 0))
                    sampled_hex = f"#{px[0]:02x}{px[1]:02x}{px[2]:02x}"
                except Exception:
                    pass

            if not sampled_hex:
                # Strict 64-bit safe signatures fallback
                user32.GetDC.restype = wintypes.HDC
                user32.GetDC.argtypes = [wintypes.HWND]
                user32.ReleaseDC.restype = ctypes.c_int
                user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
                gdi32.GetPixel.restype = wintypes.COLORREF
                gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]

                hdc = user32.GetDC(0)
                try:
                    colorref = gdi32.GetPixel(hdc, pt.x, pt.y)
                finally:
                    user32.ReleaseDC(0, hdc)

                if colorref != -1 and colorref != 0xFFFFFFFF:
                    r = colorref & 0xFF
                    g = (colorref >> 8) & 0xFF
                    b = (colorref >> 16) & 0xFF
                    sampled_hex = f"#{r:02x}{g:02x}{b:02x}"

            if sampled_hex:
                self._set_color_hex(sampled_hex)

            if user32.GetAsyncKeyState(0x1B) & 0x8000:
                self._stop_eyedropper()
                return

            mouse_down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            if self._waiting_for_release:
                if not mouse_down:
                    self._waiting_for_release = False
            else:
                if mouse_down:
                    self._stop_eyedropper()
                    self.lift()
                    return
        except Exception:
            self._stop_eyedropper()
            return

        self._eyedropper_after_id = self.after(35, self._poll_eyedropper)

    def _stop_eyedropper(self) -> None:
        self._eyedropper_active = False
        self._waiting_for_release = False
        if self._eyedropper_after_id is not None:
            try:
                self.after_cancel(self._eyedropper_after_id)
            except Exception:
                pass
            self._eyedropper_after_id = None
        if self.winfo_exists():
            self.btn_eyedropper.configure(
                text="💧 Eyedropper",
                bg=self.theme["bg_editor"],
                fg=best_contrast_fg(self.theme["bg_editor"], self.theme["fg_text"], "#ffffff"),
            )
            self.lbl_eye_hint.configure(text="")

    def _commit_single_color(self) -> None:
        self._stop_eyedropper()
        code = self.stop_colors[0][1:].upper()
        self.app.apply_ngui_wrapper(f"[{code}]", "[-]")
        self._on_close()

    def _commit_gradient_color(self) -> None:
        self._stop_eyedropper()
        c0 = self.stop_colors[0][1:].upper()
        c1 = self.stop_colors[1][1:].upper()
        self.app.apply_ngui_wrapper(f"[{c0}-{c1}]", "[-]")
        self._on_close()

    def _on_escape(self, _event: Optional[tk.Event] = None) -> None:
        if self._eyedropper_active:
            self._stop_eyedropper()
        else:
            self._on_close()

    def _on_close(self) -> None:
        self._stop_eyedropper()
        safe_grab_release(self)
        try:
            if hasattr(self, "app") and getattr(self.app, "_color_picker_win", None) is self:
                self.app._color_picker_win = None
            self._sv_photo = None
            self._hue_photo = None
            self._grad_photo = None
            if hasattr(self, "canvas_grad_preview"):
                self.canvas_grad_preview.image = None
        except Exception:
            pass
        self.destroy()


def safe_grab_release(dialog: Optional[tk.Toplevel]) -> None:
    """Safely release modal grab on a Toplevel dialog before destruction (Rule 3, S8a)."""
    if dialog is not None:
        try:
            if dialog.winfo_exists():
                dialog.grab_release()
        except Exception:
            pass


class ProjectDiffDialog(tk.Toplevel):
    """Modal U-B18 Project Difference Mapping dialog before opening a .misora workspace."""

    def __init__(
        self,
        parent: "MisoraApp",
        diff_entries: List[WorkspaceDiffEntry],
        target_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.parent = parent
        self.result: str = "cancel"
        self.title("Open Project — Review Open Files")
        self.geometry("620x380")
        self.minsize(480, 280)
        apply_window_icon(self)

        t = getattr(parent, "theme", THEME["dark"])
        self.configure(bg=t["bg_main"])
        fg_main = best_contrast_fg(t["bg_main"], t["fg_text"], "#ffffff")
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")

        header_frame = tk.Frame(self, bg=t["bg_panel"], padx=12, pady=10)
        header_frame.pack(fill="x")
        proj_label = f"'{target_name}'" if target_name else "this project"
        tk.Label(
            header_frame,
            text=f"Opening {proj_label} will replace your currently open files.",
            bg=t["bg_panel"],
            fg=t.get("misora_pink", fg_panel),
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header_frame,
            text="Review the file changes below. Unsaved edits will be lost unless you save first.",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        table_frame = tk.Frame(self, bg=t["bg_main"], padx=12, pady=8)
        table_frame.pack(fill="both", expand=True)

        cols = ("file", "status", "dirty")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        tree.heading("file", text="File")
        tree.heading("status", text="Change")
        tree.heading("dirty", text="State")
        tree.column("file", width=340, anchor="w")
        tree.column("status", width=110, anchor="center")
        tree.column("dirty", width=110, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        status_labels = {"added": "Added", "removed": "Removed", "kept": "Kept"}
        for entry in diff_entries:
            tree.insert(
                "",
                "end",
                values=(
                    entry.display_name,
                    status_labels.get(entry.status, entry.status.title()),
                    "* Unsaved" if entry.is_dirty else "Clean",
                ),
            )

        btn_bar = tk.Frame(self, bg=t["bg_main"], padx=12, pady=10)
        btn_bar.pack(fill="x")

        def _finish(choice: str) -> None:
            self.result = choice
            safe_grab_release(self)
            try:
                if self.winfo_exists():
                    self.destroy()
            except Exception:
                pass

        has_dirty = any(e.is_dirty for e in diff_entries)
        btn_save = ttk.Button(
            btn_bar,
            text="Save Current",
            style="Accent.TButton" if has_dirty else "TButton",
            command=lambda: _finish("save"),
        )
        btn_save.pack(side="right", padx=(6, 0))
        if not has_dirty:
            btn_save.state(["disabled"])

        ttk.Button(
            btn_bar,
            text="Discard & Open",
            style="TButton" if has_dirty else "Accent.TButton",
            command=lambda: _finish("discard"),
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            btn_bar,
            text="Cancel",
            style="TButton",
            command=lambda: _finish("cancel"),
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", lambda: _finish("cancel"))
        self.bind("<Escape>", lambda _e: _finish("cancel"))
        self.transient(parent)
        try:
            self.grab_set()
        except Exception:
            pass
        parent.wait_window(self)


def write_atomic_utf8(
    path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    has_bom: bool = False,
    newline: Optional[str] = None,
) -> None:
    """Write text content atomically: delegates to write_atomic_encoded (S3 / S8b-3)."""
    write_atomic_encoded(path, content, encoding=encoding, has_bom=has_bom, newline=newline)


def make_collision_resistant_backup_path(
    source_path: Union[str, Path],
    backup_dir: Union[str, Path],
    tag: str = "bak",
) -> Path:
    """Generate a unique, collision-resistant backup path for a source file (BUG-20 / QW-B17 + Grok-N03).

    Format: <stem>.<tag>_<timestamp_microseconds>_<sha256_path_prefix><suffix>
    Guarantees that same-stem files in different folders saved within the same second
    or microsecond never overwrite each other, disambiguating if the target already exists.
    """
    src_p = Path(source_path)
    b_dir = Path(backup_dir)
    b_dir.mkdir(parents=True, exist_ok=True)

    try:
        norm_str = os.path.normcase(str(src_p.resolve()))
    except Exception:
        norm_str = os.path.normcase(str(src_p))

    path_hash = hashlib.sha256(norm_str.encode("utf-8")).hexdigest()[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    candidate = b_dir / f"{src_p.stem}.{tag}_{ts}_{path_hash}{src_p.suffix}"
    counter = 1
    while candidate.exists():
        candidate = b_dir / f"{src_p.stem}.{tag}_{ts}_{path_hash}_{counter}{src_p.suffix}"
        counter += 1
    return candidate


def _get_box_uid(box: Any) -> Optional[int]:
    """Get runtime UID from a Box, falling back to its primary segment record UID (S06 / BUG-12)."""
    if box is None:
        return None
    uid = getattr(box, "uid", None)
    if uid is not None and uid != 0:
        return uid
    if hasattr(box, "segs") and box.segs and getattr(box.segs[0], "record", None):
        return getattr(box.segs[0].record, "uid", None)
    return uid


def _hash_mtl_source(text: str) -> str:
    """Canonical SHA-256 hash helper for MTL source text identity matching (BUG-27)."""
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def compute_stable_lock_key(box_ordinal: int, original_jp_text: str) -> Tuple[int, str]:
    """Compute stable lock identity (box_ordinal, sha256(original_jp_text)) (S06 / BUG-12 / Invariant 6)."""
    return (box_ordinal, hashlib.sha256(original_jp_text.encode("utf-8")).hexdigest())


def get_document_stable_locks(
    doc: Any,
    locked_uids: Set[int],
    original_jp_by_uid: Dict[int, str],
) -> List[Tuple[int, str]]:
    """Extract list of stable lock keys (box_ordinal, sha256(jp)) for locked boxes in doc."""
    if not doc or not getattr(doc, "boxes", None):
        return []
    stable_locks: List[Tuple[int, str]] = []
    for i, box in enumerate(doc.boxes):
        b_uid = _get_box_uid(box)
        if b_uid is not None and b_uid in locked_uids:
            jp_text = original_jp_by_uid.get(b_uid, box.clean_text)
            stable_locks.append(compute_stable_lock_key(i, jp_text))
    return stable_locks


def restore_stable_locks(
    doc: Any,
    stable_locks: Iterable[Tuple[int, str]],
    original_jp_by_uid: Optional[Dict[int, str]] = None,
) -> Tuple[Set[int], List[Tuple[int, str]]]:
    """Restore stable lock keys against doc.boxes, returning (matched_uids, unresolved_locks) (S06 / BUG-12)."""
    matched_uids: Set[int] = set()
    unresolved: List[Tuple[int, str]] = []
    if not doc or not getattr(doc, "boxes", None):
        return matched_uids, list(stable_locks)

    orig_map = original_jp_by_uid or {}
    for ordinal, expected_hash in stable_locks:
        if 0 <= ordinal < len(doc.boxes):
            box = doc.boxes[ordinal]
            b_uid = _get_box_uid(box)
            jp_text = orig_map.get(b_uid, box.clean_text)
            actual_hash = hashlib.sha256(jp_text.encode("utf-8")).hexdigest()
            if actual_hash == expected_hash:
                if b_uid is not None:
                    matched_uids.add(b_uid)
                continue
        unresolved.append((ordinal, expected_hash))
    return matched_uids, unresolved


class _ReplaceRowProxy:
    """Proxy object maintaining backwards compatibility for self.row_replace."""

    def __init__(self, app: Any) -> None:
        self.app = app

    def pack_forget(self) -> None:
        if hasattr(self.app, "_hide_replace_row"):
            self.app._hide_replace_row()

    def grid_remove(self) -> None:
        if hasattr(self.app, "_hide_replace_row"):
            self.app._hide_replace_row()

    def pack(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self.app, "_show_replace_row"):
            self.app._show_replace_row()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self.app, "_show_replace_row"):
            self.app._show_replace_row()

    def winfo_viewable(self) -> bool:
        return bool(getattr(self.app, "_replace_row_visible", False))

    def winfo_manager(self) -> str:
        return "grid" if getattr(self.app, "_replace_row_visible", False) else ""


class MisoraApp(tk.Tk):
    """Main Application Window for Misora: Story Editor."""

    def __init__(self, initial_path: Optional[str] = None, show_splash: bool = True, _progress_callback=None, restore_session: bool = True):
        super().__init__()
        self.title("Misora: Story Editor")
        self.geometry("1280x820")
        self.minsize(980, 620)
        self.withdraw()   # stay hidden until splash closes or ready

        splash = None
        if show_splash and _progress_callback is None:
            try:
                splash = MisoraSplashScreen(parent=self)
                splash.process_events()
            except Exception:
                splash = None

        def _rpt(val: float, msg: str = ""):
            if splash:
                try:
                    splash.set_progress(val, msg)
                    splash.process_events()
                except Exception:
                    pass
            elif _progress_callback:
                try:
                    _progress_callback(val, msg)
                except Exception:
                    pass

        _rpt(0.10, "Loading core modules…")
        # Central Logger initialized early so startup & config load are recorded
        self.logger = MisoraLogger(DEBUG_LOG_PATH)
        self._install_exception_hooks()

        # Path config & persistent workspace states (initialized before _load_user_prefs)
        self.backup_folder: Optional[Path] = None
        self.project_folder: Optional[Path] = None
        self.bepinex_project_folder: Optional[Path] = None  # Backward-compatible alias
        self.datamine_exe: Optional[Path] = None
        self.external_editor_path: Optional[Path] = None
        self.notepadpp_path: Optional[Path] = None
        self._datamine_confirm_skip: bool = False
        self._left_dock_tab: str = "search"
        self._left_dock_width: int = 340
        self._dock_collapsed: bool = False
        self.show_line_numbers: bool = True
        self.show_column_ruler: bool = False
        self.mtl_config: MTLConfig = MTLConfig()
        self._translator_dialog: Optional[Any] = None
        self._side_drawer_pinned: bool = False
        self.dnd_batch_threshold: int = 10
        self.dnd_size_threshold_mb: float = 25.0
        self.dnd_filter_binary: bool = True
        self.xuat_safety_backup_enabled: bool = True
        self.xuat_archive_dir: Optional[Path] = None
        self.xuat_archive_ext: str = DEFAULT_ARCHIVE_EXT
        self.xuat_archive_strategy: str = "combined"

        _rpt(0.25, "Loading saved preferences…")
        self.font_manager = FontManager(SCRIPT_DIR / "assets" / "fonts", logger=self.logger)
        self._font_migration_notice: Optional[str] = None
        # Load persistent user preferences (fonts, theme colors, paths, mtl settings)
        self.prefs: Dict[str, Any] = self._load_user_prefs()
        self.theme: Dict[str, str] = dict(self.prefs["theme"])
        THEME.update(self.theme)

        dbg_cfg = self.prefs.get("debug", {})
        self.logger.configure(
            level_name=dbg_cfg.get("level", "Info"),
            log_to_file=bool(dbg_cfg.get("log_to_file", False)),
            categories=dbg_cfg.get("categories"),
            log_file_path=DEBUG_LOG_PATH,
        )

        self.configure(bg=self.theme["bg_dark"])
        apply_window_icon(self)

        # State Variables
        self.current_file_path: Optional[Path] = None
        self.current_doc: Optional[StoryDocument] = None
        self.current_unity_env: Any = None
        self.current_text_obj: Any = None
        self.current_box_idx: int = 0
        self.is_box0_active: bool = False
        self.var_box0_title: tk.StringVar = tk.StringVar(master=self, value="")
        self.var_box0_subtitle: tk.StringVar = tk.StringVar(master=self, value="")
        self.is_bundle_file: bool = False
        self.is_dirty: bool = False
        self._plain_text_content: str = ""
        self.xuat_search_roots: List[Path] = []
        self.xuat_index: Optional[XuatIndex] = None
        self.xuat_entries: Optional[XuatIndex] = None
        self._xuat_index_queue: queue.Queue = queue.Queue()
        self._xuat_index_poll_id: Optional[str] = None
        self._xuat_index_seq: int = 0
        self._xuat_index_cancel: Optional[threading.Event] = None
        self._xuat_index_thread: Optional[threading.Thread] = None
        self._xuat_global_choice_overrides: Dict[str, str] = {}
        self._import_xuat_dialog: Optional[Any] = None
        self._xuat_cleanup_dialog: Optional[Any] = None
        self._xuat_cleanup_settings_dialog: Optional[Any] = None
        self._ui_ready: bool = False
        self.selected_search_folder: Optional[Path] = None

        # Steps 3-4: Undo journal & opened-files cache
        self.undo_journal: MasterUndoJournal = MasterUndoJournal()
        self.open_documents: Dict[Path, Any] = {}   # path -> open doc info dict

        # Active NGUI Ribbon color state
        self._active_ngui_color: str = "#7b42bc"
        self._active_ngui_grad_end: str = "#ff7da7"
        self._color_picker_win: Optional[NguiColorPickerPopup] = None

        # Multi-box edit tracking for Continuous View & XUAT sync
        self._original_box_texts: Dict[int, str] = {}
        self._modified_boxes: Set[int] = set()
        # S2: Per-document saved-state checkpoint map (SHA-256 fingerprints keyed by resolved str(path))
        self._saved_state_checkpoints: Dict[str, str] = {}
        self._cont_header_spans: Dict[int, Tuple[str, str]] = {}
        self._suppress_continuous_events: bool = False
        self._card_widgets: Dict[int, Dict[str, Any]] = {}
        self._all_script_block_ranges: Dict[int, Tuple[int, int]] = {}
        self._all_script_line_to_box: Dict[int, int] = {}
        self._all_script_sel_ranges: Dict[int, Tuple[str, str]] = {}
        self._all_script_lock_ranges: Dict[int, Tuple[str, str]] = {}
        self._all_script_body_starts: Dict[int, str] = {}
        self._all_script_render_images: List[Any] = []
        self._dialogue_preview_images: List[Any] = []
        self.var_select_box_mode: tk.BooleanVar = tk.BooleanVar(master=self, value=False)
        self._selected_boxes: Set[int] = set()
        self._locked_boxes: Set[int] = set()
        self._locked_box_uids: Set[int] = set()
        self._modified_box_uids: Set[int] = set()
        self._original_jp_by_uid: Dict[int, str] = {}
        self._box_clipboard: List[Any] = []
        self._is_speaker_pinned: bool = False
        self._pinned_speaker_name: Optional[str] = None
        self._icon_cache: dict = {}
        self._cont_resize_job: Optional[str] = None

        # S8b-1: Toast & Status Notification Manager state
        self._toast_queue: collections.deque = collections.deque()
        self._toast_active: bool = False
        self._toast_after_id: Optional[str] = None
        self._status_after_id: Optional[str] = None
        self._default_status_text: str = "Ready. Drag & Drop or open a .unity3d bundle or folder to begin."
        self._toast_widget: Optional[tk.Label] = None

        # Side Drawer (Customization, NGUI Glossary, & MTL) state
        self._side_drawer_visible: bool = False
        self._side_drawer_tab: str = "customize"
        self._theme_swatch_buttons: Dict[str, tk.Button] = {}
        self._theme_hex_vars: Dict[str, tk.StringVar] = {}
        self._glossary_line_map: Dict[int, int] = {}
        self._selected_glossary_idx: int = 0
        self._filtered_glossary_items: List[Dict[str, str]] = list(NGUI_GLOSSARY_ITEMS)
        self._mtl_drawer_queue: queue.Queue = queue.Queue()
        self._mtl_drawer_poll_id: Optional[str] = None
        self._mtl_drawer_pending: int = 0
        self._mtl_drawer_req_seq: int = 0
        self._mtl_drawer_latest_seq: Dict[str, int] = {}
        self._mtl_drawer_cache: "collections.OrderedDict[Tuple[str, str], str]" = collections.OrderedDict()
        self._mtl_drawer_mode: str = "dialogue"
        self._mtl_drawer_cards: Dict[str, Dict[str, Any]] = {}
        if not hasattr(self, "_mtl_drawer_enabled_engines") or not isinstance(self._mtl_drawer_enabled_engines, dict):
            self._mtl_drawer_enabled_engines: Dict[str, bool] = {
                eng: (eng in ("XUAT Cache", "Google"))
                for eng in self._MTL_DRAWER_ENGINE_ORDER
            }
        self._mtl_drawer_engine_vars: Dict[str, tk.BooleanVar] = {}
        for eng in self._MTL_DRAWER_ENGINE_ORDER:
            enabled = bool(self._mtl_drawer_enabled_engines.get(eng, eng in ("XUAT Cache", "Google")))
            self._mtl_drawer_enabled_engines[eng] = enabled
            self._mtl_drawer_engine_vars[eng] = tk.BooleanVar(master=self, value=enabled)
        self._mtl_drawer_active_context: Optional[Tuple[str, int, Any, str]] = None
        self._mtl_all_req_seqs: Dict[Tuple[Any, str], int] = {}
        self._mtl_all_results: Dict[Tuple[str, int, Any, str], str] = {}
        self._mtl_all_statuses: Dict[Tuple[str, int, Any, str], str] = {}
        self._mtl_all_errors: Dict[Tuple[str, int, Any, str], str] = {}
        self._mtl_all_selected_uid: Any = None
        self._mtl_all_block_ranges: List[Tuple[int, int, Any]] = []
        self._mtl_all_last_ctx: Optional[Tuple[str, int, Any, str]] = None
        self._mtl_all_batch_cancel: Optional[threading.Event] = None
        self._mtl_all_batch_gen: int = 0
        self._mtl_all_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

        # Native Win32 Drag & Drop references (kept alive to prevent GC)
        self._wndprocs: Dict[int, Tuple[Any, Any]] = {}
        self._drop_hwnd: Any = None
        self._dnd_in_progress: bool = False

        # Debug logging & safety state
        self.var_log_to_file = tk.BooleanVar(master=self, value=bool(dbg_cfg.get("log_to_file", False)))
        self.var_xuat_safety_backup = tk.BooleanVar(master=self, value=bool(self.xuat_safety_backup_enabled))

        # Speaker autocomplete popup state (U-3 / U-4)
        self._speaker_popup: Optional[tk.Toplevel] = None
        self._speaker_listbox: Optional[tk.Listbox] = None
        self._speaker_popup_items: List[Tuple[str, str]] = []
        self._speaker_focus_out_after_id: Optional[str] = None
        self._suppress_speaker_popup: bool = False
        self._speaker_popup_navigated: bool = False
        self._speaker_ac_user_typed: bool = False
        self._speaker_ac_initial_text: str = ""
        self._about_dialog: Optional[tk.Toplevel] = None
        self._support_me_dialog: Optional[tk.Toplevel] = None
        self.var_log_level = tk.StringVar(master=self, value=str(dbg_cfg.get("level", "Info")))
        self.var_console_autoscroll = tk.BooleanVar(master=self, value=True)
        self.var_log_categories: Dict[str, tk.BooleanVar] = {}
        saved_cats = dbg_cfg.get("categories", {}) if isinstance(dbg_cfg.get("categories"), dict) else {}
        for cat in LOG_CATEGORIES:
            enabled = True if cat == ALWAYS_ON_CATEGORY else bool(saved_cats.get(cat, True))
            self.var_log_categories[cat] = tk.BooleanVar(master=self, value=enabled)

        # Background search worker & highlighting state
        self.search_engine = ProjectSearchEngine()
        self.sync_manager = XUnitySyncManager()
        self.search_queue: queue.Queue = queue.Queue(maxsize=2048)
        self._search_cancel_event: threading.Event = threading.Event()
        self.search_cancel_flag: bool = False
        self._is_searching: bool = False
        self._search_poll_job: Optional[str] = None
        self.active_search_results: List[SearchResult] = []
        self.active_search_options: Optional[SearchOptions] = None
        self.search_file_groups: List[Dict[str, Any]] = []
        self._file_group_lookup: Dict[str, Dict[str, Any]] = {}
        self._result_line_map: Dict[int, Tuple[str, Any]] = {}
        self._result_idx_to_line: Dict[int, int] = {}
        self._selected_result_idx: Optional[int] = None

        # Background MTL worker queue and request sequencing (Rule 15 / BUG-27)
        self._mtl_queue: queue.Queue = queue.Queue()
        self._mtl_request_seq: int = 0
        self._mtl_pending: int = 0
        self._latest_applied_mtl_seq: Dict[Any, int] = {}
        self._mtl_poll_job: Optional[str] = None
        self._hash_mtl_source = _hash_mtl_source
        self._get_box_uid = _get_box_uid

        # Auto-detect project paths
        self._detect_environment()

        _rpt(0.55, "Building UI layout…")
        # Build UI
        self._apply_styles()
        self._build_menu()
        self._build_search_bar()

        _rpt(0.70, "Initializing editor panels…")
        self._build_main_panels()
        self._build_side_drawer()
        self._build_status_bar()
        self._bind_shortcuts()

        _rpt(0.85, "Applying theme and fonts…")
        # Sync initial widget fonts & colors with saved preferences
        self._apply_theme_and_fonts_live(save=False)
        self._update_empty_state_visibility()

        # Flush config on exit and unhook Win32 WNDPROC cleanly
        self.protocol("WM_DELETE_WINDOW", self._on_app_exit)
        self.bind("<Destroy>", self._on_root_destroy)

        _rpt(0.85, "Enabling drag & drop…")
        # Enable native OS Drag & Drop safely on the outer frame HWND
        self._init_drag_and_drop()

        # Background polling starts on-demand when work is dispatched (BONUS-03)
        self._search_poll_job = None
        self._mtl_poll_job = None

        # Restore saved window geometry and view toggles (Bug #2 / S9c)
        if hasattr(self, "_saved_geometry") and self._saved_geometry:
            try:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                safe_geom = sanitize_window_geometry(self._saved_geometry, sw, sh)
                self.geometry(safe_geom)
            except Exception:
                pass
        if hasattr(self, "_saved_continuous_view") and hasattr(self, "var_continuous_view"):
            if self._saved_continuous_view:
                self.var_continuous_view.set(True)
                self._on_toggle_continuous_view()
            else:
                self.var_continuous_view.set(False)
        if hasattr(self, "_saved_sync_xuat") and hasattr(self, "var_sync_xuat"):
            self.var_sync_xuat.set(self._saved_sync_xuat)

        _rpt(1.00, "Ready!")
        self.logger.info("UI / Theme / Config", f"Misora initialized. Config path: {CONFIG_PATH}")

        if splash:
            splash.close()

        # Reveal the main window instantly (DEP-9 / AGENTS.md §22)
        self.deiconify()

        self._rpt_done = True
        self._ui_ready = True
        # Defer session file restoration to idle loop so startup never hangs (BUG-35)
        def _deferred_restore() -> None:
            if not self.winfo_exists() or getattr(self, "_destroyed", False):
                return
            if restore_session and getattr(self, "xuat_search_roots", None) and self.xuat_index is None:
                self._refresh_xuat_index_async()
            if initial_path and os.path.exists(initial_path):
                init_p = Path(initial_path)
                if init_p.is_dir():
                    try:
                        self._process_opened_folder(init_p, source_label="Initial Path")
                    except Exception as exc:
                        self.logger.error("File I/O", f"Failed opening initial folder '{initial_path}': {exc}")
                else:
                    try:
                        self.open_file(init_p)
                    except Exception as exc:
                        self.logger.error("File I/O", f"Failed opening initial file '{initial_path}': {exc}")
            elif restore_session and hasattr(self, "_saved_opened_files") and self._saved_opened_files:
                for fp in self._saved_opened_files:
                    fp_exists = Path(fp).exists() if isinstance(fp, (str, Path)) else False
                    if fp_exists:
                        try:
                            self.open_file(fp)
                        except Exception as exc:
                            self.logger.error("File I/O", f"Failed restoring session file '{fp}': {exc}")
                if hasattr(self, "_saved_active_file") and self._saved_active_file:
                    act_exists = Path(self._saved_active_file).exists() if isinstance(self._saved_active_file, (str, Path)) else False
                    if act_exists:
                        try:
                            self.open_file(self._saved_active_file)
                        except Exception as exc:
                            self.logger.error("File I/O", f"Failed activating session file '{self._saved_active_file}': {exc}")

        self.after_idle(_deferred_restore)

    def get_icon(self, name: str, size: Tuple[int, int] = (18, 18)) -> Optional[tk.PhotoImage]:
        """Retrieve an illustrated icon PhotoImage bound to this MisoraApp Tk instance."""
        return get_icon(name, size, master=self)

    def safe_clipboard_get(self) -> str:
        """Read text from clipboard with retry on TclError and CRLF/CR normalization (AGENTS.md Rule 14)."""
        for _ in range(5):
            try:
                val = self.clipboard_get()
                return val.replace("\r\n", "\n").replace("\r", "\n")
            except tk.TclError:
                time.sleep(0.05)
            except Exception:
                break
        return ""

    def safe_clipboard_set(self, text: str) -> None:
        """Write text to clipboard with retry on TclError (AGENTS.md Rule 14)."""
        for _ in range(5):
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update_idletasks()
                return
            except tk.TclError:
                time.sleep(0.05)
            except Exception:
                break

    # -------------------------------------------------------------------------
    # Global Exception Hooks & Exit Lifecycle
    # -------------------------------------------------------------------------
    def _install_exception_hooks(self) -> None:
        def _sys_excepthook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            self.logger.exception("Unhandled Python exception:", exc_value)

        sys.excepthook = _sys_excepthook

    def report_callback_exception(self, exc, val, tb) -> None:  # type: ignore[override]
        self.logger.exception("Unhandled Tkinter callback exception:", val)
        try:
            err_msg = f"Error: {val}"
            self.set_status(err_msg, is_error=True)
            self.show_toast(err_msg, duration_ms=4000, is_accent=False, is_error=True, status_bar=False)
        except Exception:
            pass

    def _on_app_exit(self) -> None:
        """Save configuration cleanly on window close and exit (S3).

        Prompts Save/Discard/Cancel per dirty document.
        Aborts exit if Cancel is chosen or if any save fails.
        """
        if not self._flush_active_widget():
            return

        dirty_paths = [
            p for p, d in list(self.open_documents.items())
            if (p == self.current_file_path and self.is_dirty) or d.get("dirty")
        ]
        if self.current_file_path and self.is_dirty:
            cur_p = Path(self.current_file_path).resolve()
            if cur_p not in [p.resolve() for p in dirty_paths]:
                dirty_paths.append(cur_p)

        for p in dirty_paths:
            ans = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"'{p.name}' has unsaved changes.\nSave before exiting?",
                parent=self,
            )
            if ans is None:
                return
            if ans:
                if not self._save_document_entry(p):
                    return

        # Sweep pending after jobs first (BUG-32)
        try:
            for job_id in self.tk.call("after", "info"):
                try:
                    self.after_cancel(job_id)
                except Exception:
                    pass
        except Exception:
            pass

        self.logger.info("UI / Theme / Config", "Saving configuration on exit...")
        self._save_user_prefs(silent=True)
        self._cleanup_drag_and_drop()
        self.destroy()

    def _on_root_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._destroyed = True
            self.search_cancel_flag = True
            if hasattr(self, "_search_cancel_event") and self._search_cancel_event is not None:
                try:
                    self._search_cancel_event.set()
                except Exception:
                    pass
            if hasattr(self, "_cancel_mtl_all_batch"):
                try:
                    self._cancel_mtl_all_batch()
                except Exception:
                    pass
            try:
                for job_id in self.tk.call("after", "info"):
                    try:
                        self.after_cancel(job_id)
                    except Exception:
                        pass
            except Exception:
                pass
            if hasattr(self, "_search_poll_job") and self._search_poll_job:
                try:
                    self.after_cancel(self._search_poll_job)
                except Exception:
                    pass
                self._search_poll_job = None
            if hasattr(self, "_mtl_poll_job") and self._mtl_poll_job:
                try:
                    self.after_cancel(self._mtl_poll_job)
                except Exception:
                    pass
                self._mtl_poll_job = None
            if hasattr(self, "_mtl_drawer_poll_id") and self._mtl_drawer_poll_id:
                try:
                    self.after_cancel(self._mtl_drawer_poll_id)
                except Exception:
                    pass
                self._mtl_drawer_poll_id = None
            if hasattr(self, "_xuat_index_cancel") and self._xuat_index_cancel is not None:
                try:
                    self._xuat_index_cancel.set()
                except Exception:
                    pass
                self._xuat_index_cancel = None
            if hasattr(self, "_xuat_index_thread") and self._xuat_index_thread is not None:
                try:
                    if self._xuat_index_thread.is_alive():
                        self._xuat_index_thread.join(timeout=1.0)
                except Exception:
                    pass
                self._xuat_index_thread = None
            if hasattr(self, "_xuat_index_poll_id") and self._xuat_index_poll_id:
                try:
                    self.after_cancel(self._xuat_index_poll_id)
                except Exception:
                    pass
                self._xuat_index_poll_id = None
            if hasattr(self, "_toast_after_id") and self._toast_after_id:
                try:
                    self.after_cancel(self._toast_after_id)
                except Exception:
                    pass
                self._toast_after_id = None
            if hasattr(self, "_status_after_id") and self._status_after_id:
                try:
                    self.after_cancel(self._status_after_id)
                except Exception:
                    pass
                self._status_after_id = None
            if hasattr(self, "_close_speaker_autocomplete"):
                try:
                    self._close_speaker_autocomplete()
                except Exception:
                    pass
            if hasattr(self, "_speaker_focus_out_after_id") and self._speaker_focus_out_after_id:
                try:
                    self.after_cancel(self._speaker_focus_out_after_id)
                except Exception:
                    pass
                self._speaker_focus_out_after_id = None
            self._cleanup_drag_and_drop()

    def destroy(self) -> None:
        self._destroyed = True
        self.search_cancel_flag = True
        if hasattr(self, "_search_cancel_event") and self._search_cancel_event is not None:
            try:
                self._search_cancel_event.set()
            except Exception:
                pass
        if hasattr(self, "_cancel_mtl_all_batch"):
            try:
                self._cancel_mtl_all_batch()
            except Exception:
                pass
        # Sweep all pending Tk after jobs first (BUG-32)
        try:
            for job_id in self.tk.call("after", "info"):
                try:
                    self.after_cancel(job_id)
                except Exception:
                    pass
        except Exception:
            pass

        if hasattr(self, "_search_poll_job") and self._search_poll_job:
            try:
                self.after_cancel(self._search_poll_job)
            except Exception:
                pass
            self._search_poll_job = None
        if hasattr(self, "_mtl_poll_job") and self._mtl_poll_job:
            try:
                self.after_cancel(self._mtl_poll_job)
            except Exception:
                pass
            self._mtl_poll_job = None
        if hasattr(self, "_mtl_drawer_poll_id") and self._mtl_drawer_poll_id:
            try:
                self.after_cancel(self._mtl_drawer_poll_id)
            except Exception:
                pass
            self._mtl_drawer_poll_id = None
        if hasattr(self, "_xuat_index_cancel") and self._xuat_index_cancel is not None:
            try:
                self._xuat_index_cancel.set()
            except Exception:
                pass
            self._xuat_index_cancel = None
        if hasattr(self, "_xuat_index_thread") and self._xuat_index_thread is not None:
            try:
                if self._xuat_index_thread.is_alive():
                    self._xuat_index_thread.join(timeout=1.0)
            except Exception:
                pass
            self._xuat_index_thread = None
        if hasattr(self, "_xuat_index_poll_id") and self._xuat_index_poll_id:
            try:
                self.after_cancel(self._xuat_index_poll_id)
            except Exception:
                pass
            self._xuat_index_poll_id = None
        if hasattr(self, "_toast_after_id") and self._toast_after_id:
            try:
                self.after_cancel(self._toast_after_id)
            except Exception:
                pass
            self._toast_after_id = None
        if hasattr(self, "_status_after_id") and self._status_after_id:
            try:
                self.after_cancel(self._status_after_id)
            except Exception:
                pass
            self._status_after_id = None
        if hasattr(self, "_close_speaker_autocomplete"):
            try:
                self._close_speaker_autocomplete()
            except Exception:
                pass
        for dlg_attr in ("_xuat_cleanup_dialog", "_xuat_cleanup_settings_dialog", "_import_xuat_dialog"):
            dlg_obj = getattr(self, dlg_attr, None)
            if dlg_obj is not None:
                try:
                    safe_grab_release(dlg_obj)
                    if dlg_obj.winfo_exists():
                        dlg_obj.destroy()
                except Exception:
                    pass
                setattr(self, dlg_attr, None)
        if hasattr(self, "_speaker_focus_out_after_id") and self._speaker_focus_out_after_id:
            try:
                self.after_cancel(self._speaker_focus_out_after_id)
            except Exception:
                pass
            self._speaker_focus_out_after_id = None
        if hasattr(self, "_toast_queue"):
            self._toast_queue.clear()
        if hasattr(self, "_toast_widget") and self._toast_widget:
            try:
                self._toast_widget.destroy()
            except Exception:
                pass
            self._toast_widget = None
        self._toast_active = False

        for job_attr in ("_cont_resize_job", "_eyedropper_after_id"):
            if hasattr(self, job_attr):
                job_id = getattr(self, job_attr)
                if job_id:
                    try:
                        self.after_cancel(job_id)
                    except Exception:
                        pass
                    setattr(self, job_attr, None)

        # S8b-2: Dispose all open document environments and prune icon cache
        try:
            for entry in list(getattr(self, "open_documents", {}).values()):
                if isinstance(entry, dict) and entry.get("env"):
                    dispose_unity_env(entry["env"])
            if getattr(self, "current_unity_env", None):
                dispose_unity_env(self.current_unity_env)
                self.current_unity_env = None
            prune_icon_cache(self)
            prune_preview_cache(self)
            if hasattr(self, "_all_script_render_images"):
                self._all_script_render_images.clear()
            if hasattr(self, "_dialogue_preview_images"):
                self._dialogue_preview_images.clear()
        except Exception:
            pass

        self._cleanup_drag_and_drop()
        if hasattr(self, "font_manager") and self.font_manager:
            try:
                self.font_manager.dispose()
            except Exception:
                pass
        try:
            super().destroy()
        finally:
            # Terminate background logger last inside safe try/except (BUG-32)
            if hasattr(self, "logger") and self.logger:
                try:
                    self.logger.close()
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Persistent Preferences & Contrast-Safe Theme Helpers (#2 & #13)
    # -------------------------------------------------------------------------
    def _load_user_prefs(self) -> Dict[str, Any]:
        """Load saved font, theme & debug settings from misora_config.json."""
        merged_theme = dict(DEFAULT_PREFS["theme"])
        merged_debug: Dict[str, Any] = {
            "log_to_file": False,
            "level": "Info",
            "categories": {cat: True for cat in LOG_CATEGORIES},
        }
        prefs: Dict[str, Any] = {
            "dialogue_font_family": DEFAULT_PREFS["dialogue_font_family"],
            "dialogue_font_size": DEFAULT_PREFS["dialogue_font_size"],
            "raw_font_size": DEFAULT_PREFS["raw_font_size"],
            "ui_font_size": DEFAULT_PREFS["ui_font_size"],
            "theme": merged_theme,
            "debug": merged_debug,
        }
        if CONFIG_PATH.is_file():
            try:
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    if isinstance(raw.get("dialogue_font_family"), str) and raw["dialogue_font_family"].strip():
                        raw_fam = raw["dialogue_font_family"].strip()
                        if hasattr(self, "font_manager"):
                            migrated_fam, was_migrated = self.font_manager.migrate_legacy_font(raw_fam)
                            prefs["dialogue_font_family"] = migrated_fam
                            if was_migrated:
                                self._font_migration_notice = (
                                    f"Migrated legacy font '{raw_fam}' to '{migrated_fam}'."
                                )
                                self.logger.info("UI / Theme / Config", self._font_migration_notice)
                        else:
                            prefs["dialogue_font_family"] = raw_fam
                    for k, lo, hi in (
                        ("dialogue_font_size", 8, 28),
                        ("raw_font_size", 7, 22),
                        ("ui_font_size", 8, 16),
                    ):
                        val = raw.get(k)
                        if isinstance(val, int) and not isinstance(val, bool) and lo <= val <= hi:
                            prefs[k] = val
                    saved_theme = raw.get("theme")
                    if isinstance(saved_theme, dict):
                        for tk_key in merged_theme:
                            hv = saved_theme.get(tk_key)
                            if isinstance(hv, str) and HEX_COLOR_RE.match(hv.strip()):
                                merged_theme[tk_key] = hv.strip().lower()
                    saved_dbg = raw.get("debug")
                    if isinstance(saved_dbg, dict):
                        # Legacy console_visible key is tolerated and silently ignored (RM-01)
                        if isinstance(saved_dbg.get("log_to_file"), bool):
                            merged_debug["log_to_file"] = saved_dbg["log_to_file"]
                        if saved_dbg.get("level") in LOG_LEVELS:
                            merged_debug["level"] = saved_dbg["level"]
                        scats = saved_dbg.get("categories")
                        if isinstance(scats, dict):
                            for cat in LOG_CATEGORIES:
                                if cat == ALWAYS_ON_CATEGORY:
                                    merged_debug["categories"][cat] = True
                                elif isinstance(scats.get(cat), bool):
                                    merged_debug["categories"][cat] = scats[cat]
                self.logger.debug("UI / Theme / Config", f"Loaded config from {CONFIG_PATH}")
                # Load Step 3-4 path/dock config (additive; no version bump needed)
                def _load_path(key: str) -> Optional[Path]:
                    v = raw.get(key)
                    return Path(v) if isinstance(v, str) and v else None
                self.backup_folder = _load_path("backup_folder")
                self.project_folder = _load_path("project_folder") or _load_path("bepinex_project_folder")
                self.bepinex_project_folder = self.project_folder
                self.datamine_exe = _load_path("datamine_exe")
                self.external_editor_path = _load_path("external_editor_path")
                self.notepadpp_path = _load_path("notepadpp_path")
                self.last_opened_dir = _load_path("last_opened_dir")
                self.selected_search_folder = _load_path("selected_search_folder")
                if isinstance(raw.get("saved_opened_files"), list):
                    self._saved_opened_files = [Path(p) for p in raw["saved_opened_files"] if isinstance(p, str) and p and Path(p).exists()]
                else:
                    self._saved_opened_files = []
                self._saved_active_file = _load_path("saved_active_file")
                if isinstance(raw.get("recent_files"), list):
                    self.recent_files = [Path(p) for p in raw["recent_files"] if isinstance(p, str) and p and Path(p).exists()]
                else:
                    self.recent_files = []
                if isinstance(raw.get("left_dock_tab"), str):
                    self._left_dock_tab = raw["left_dock_tab"]
                if isinstance(raw.get("left_dock_width"), int):
                    self._left_dock_width = max(140, min(600, raw["left_dock_width"]))
                if isinstance(raw.get("datamine_confirm_skip"), bool):
                    self._datamine_confirm_skip = raw["datamine_confirm_skip"]
                if isinstance(raw.get("show_line_numbers"), bool):
                    self.show_line_numbers = raw["show_line_numbers"]
                if isinstance(raw.get("show_column_ruler"), bool):
                    self.show_column_ruler = raw["show_column_ruler"]
                if isinstance(raw.get("mtl"), dict):
                    self.mtl_config = MTLConfig.from_dict(raw["mtl"])
                if isinstance(raw.get("dnd_batch_threshold"), int):
                    self.dnd_batch_threshold = max(0, raw["dnd_batch_threshold"])
                if isinstance(raw.get("dnd_size_threshold_mb"), (int, float)):
                    self.dnd_size_threshold_mb = max(0.0, float(raw["dnd_size_threshold_mb"]))
                if isinstance(raw.get("dnd_filter_binary"), bool):
                    self.dnd_filter_binary = raw["dnd_filter_binary"]
                if isinstance(raw.get("window_geometry"), str) and raw["window_geometry"].strip():
                    self._saved_geometry = raw["window_geometry"].strip()
                if isinstance(raw.get("continuous_view"), bool):
                    self._saved_continuous_view = raw["continuous_view"]
                if isinstance(raw.get("sync_xuat"), bool):
                    self._saved_sync_xuat = raw["sync_xuat"]
                if isinstance(raw.get("show_ngui_ribbon"), bool):
                    self._saved_show_ngui_ribbon = raw["show_ngui_ribbon"]
                if isinstance(raw.get("mtl_drawer_enabled_engines"), dict):
                    defaults = {
                        "XUAT Cache": True,
                        "Google": True,
                        "DeepL": False,
                        "Local / Sugoi": False,
                        "LLM / OpenAI": False,
                    }
                    for eng_name in defaults:
                        val = raw["mtl_drawer_enabled_engines"].get(eng_name)
                        if isinstance(val, bool):
                            defaults[eng_name] = val
                    self._mtl_drawer_enabled_engines = defaults
                raw_xc = raw.get("xuat_cleanup")
                if isinstance(raw_xc, dict):
                    if isinstance(raw_xc.get("safety_backup_enabled"), bool):
                        self.xuat_safety_backup_enabled = raw_xc["safety_backup_enabled"]
                    arch_dir_str = raw_xc.get("archive_dir")
                    if isinstance(arch_dir_str, str) and arch_dir_str.strip():
                        self.xuat_archive_dir = Path(arch_dir_str.strip())
                    arch_ext_str = raw_xc.get("archive_ext")
                    if isinstance(arch_ext_str, str) and arch_ext_str.strip():
                        ext_clean = arch_ext_str.strip()
                        self.xuat_archive_ext = ext_clean if ext_clean.startswith(".") else "." + ext_clean
                    arch_strat = raw_xc.get("archive_strategy")
                    if isinstance(arch_strat, str) and arch_strat in VALID_ARCHIVE_STRATEGIES:
                        self.xuat_archive_strategy = arch_strat
            except Exception as exc:
                self.logger.warning("UI / Theme / Config", f"Failed to parse {CONFIG_PATH}: {exc}")
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    bak_path = CONFIG_PATH.parent / f"misora_config.bak_{ts}.json"
                    shutil.copy2(CONFIG_PATH, bak_path)
                    self.logger.info("UI / Theme / Config", f"Preserved corrupt config as {bak_path}")
                except Exception as bak_err:
                    self.logger.error("UI / Theme / Config", f"Failed to preserve corrupt config: {bak_err}")
        return prefs

    def _save_user_prefs(self, silent: bool = False) -> None:
        """Atomically persist current font, theme, path & MTL preferences to misora_config.json."""
        try:
            dbg_snapshot = self.logger.get_config_snapshot()
            self.prefs["debug"] = dbg_snapshot

            payload = {
                "config_version": 4,
                "dialogue_font_family": str(self.prefs["dialogue_font_family"]),
                "dialogue_font_size": int(self.prefs["dialogue_font_size"]),
                "raw_font_size": int(self.prefs["raw_font_size"]),
                "ui_font_size": int(self.prefs["ui_font_size"]),
                "theme": dict(self.theme),
                "debug": dbg_snapshot,
                # Path & dock state
                "backup_folder": str(self.backup_folder) if self.backup_folder else "",
                "project_folder": str(self.project_folder) if getattr(self, "project_folder", None) else (str(self.bepinex_project_folder) if getattr(self, "bepinex_project_folder", None) else ""),
                "bepinex_project_folder": str(self.bepinex_project_folder) if getattr(self, "bepinex_project_folder", None) else (str(self.project_folder) if getattr(self, "project_folder", None) else ""),
                "datamine_exe": str(self.datamine_exe) if self.datamine_exe else "",
                "external_editor_path": str(self.external_editor_path) if self.external_editor_path else "",
                "notepadpp_path": str(self.notepadpp_path) if self.notepadpp_path else "",
                "last_opened_dir": str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) else "",
                "selected_search_folder": str(self.selected_search_folder) if getattr(self, "selected_search_folder", None) else "",
                "saved_opened_files": [str(p) for p in getattr(self, "open_documents", {}).keys() if p.exists()],
                "saved_active_file": str(self.current_file_path) if getattr(self, "current_file_path", None) and self.current_file_path.exists() else "",
                "recent_files": [str(p) for p in getattr(self, "recent_files", [])[:15] if isinstance(p, Path) and p.exists()],
                "left_dock_tab": self._left_dock_tab if hasattr(self, "_left_dock_tab") else "search",
                "left_dock_width": self._left_dock_width if hasattr(self, "_left_dock_width") else 340,
                "datamine_confirm_skip": self._datamine_confirm_skip if hasattr(self, "_datamine_confirm_skip") else False,
                # Line numbers & rulers
                "show_line_numbers": bool(self.var_show_line_numbers.get()) if hasattr(self, "var_show_line_numbers") else self.show_line_numbers,
                "show_column_ruler": bool(self.var_show_column_ruler.get()) if hasattr(self, "var_show_column_ruler") else self.show_column_ruler,
                # MTL translation configuration (Rule 17: DPAPI encrypted secrets on disk)
                "mtl": self.mtl_config.to_dict(secure=True) if hasattr(self, "mtl_config") else {},
                # Drag & Drop safety configuration
                "dnd_batch_threshold": getattr(self, "dnd_batch_threshold", 10),
                "dnd_size_threshold_mb": getattr(self, "dnd_size_threshold_mb", 25.0),
                "dnd_filter_binary": getattr(self, "dnd_filter_binary", True),
                # Window geometry & view toggles (Bug #2)
                "window_geometry": self.geometry() if hasattr(self, "geometry") else "",
                "continuous_view": bool(self.var_continuous_view.get()) if hasattr(self, "var_continuous_view") else False,
                "sync_xuat": bool(self.var_sync_xuat.get()) if hasattr(self, "var_sync_xuat") else True,
                "show_ngui_ribbon": bool(self.var_show_ngui_ribbon.get()) if hasattr(self, "var_show_ngui_ribbon") else getattr(self, "_saved_show_ngui_ribbon", False),
                "mtl_drawer_enabled_engines": dict(getattr(self, "_mtl_drawer_enabled_engines", {})),
                "xuat_cleanup": {
                    "safety_backup_enabled": bool(
                        self.var_xuat_safety_backup.get()
                        if hasattr(self, "var_xuat_safety_backup")
                        else getattr(self, "xuat_safety_backup_enabled", True)
                    ),
                    "archive_dir": str(self.xuat_archive_dir) if getattr(self, "xuat_archive_dir", None) else "",
                    "archive_ext": str(getattr(self, "xuat_archive_ext", DEFAULT_ARCHIVE_EXT) or DEFAULT_ARCHIVE_EXT),
                    "archive_strategy": (
                        self.xuat_archive_strategy
                        if getattr(self, "xuat_archive_strategy", "combined") in VALID_ARCHIVE_STRATEGIES
                        else "combined"
                    ),
                },
            }
            # In-memory serialization before file write ensures DPAPISecurityError never truncates config (BUG-33)
            encoded_payload = json.dumps(payload, indent=2, ensure_ascii=False)
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = CONFIG_PATH.with_suffix(".json.tmp")
            tmp_path.write_text(encoded_payload, encoding="utf-8")
            os.replace(tmp_path, CONFIG_PATH)
            if not silent:
                self.logger.debug("UI / Theme / Config", f"Saved config to {CONFIG_PATH}")
        except DPAPISecurityError as sec_err:
            self.logger.error("UI / Theme / Config", f"DPAPI security failure: {sec_err}. Preferences save aborted to prevent secret leakage.")
            if not silent:
                try:
                    self.show_toast("Security Error: Failed to encrypt credentials. Save aborted.", is_error=True)
                except Exception:
                    pass
            return
        except Exception as e:
            self.logger.error("UI / Theme / Config", f"Failed to save config '{CONFIG_PATH}': {e}")

    def _detect_active_preset_name(self) -> str:
        """Return matching preset name if current theme equals a preset, else 'Custom'."""
        for name, preset in THEME_PRESETS.items():
            if all(self.theme.get(k, "").lower() == v.lower() for k, v in preset.items()):
                return name
        return "Custom"

    @staticmethod
    def _is_dark_color(hex_color: str) -> bool:
        """Return True if a #RRGGBB color has low WCAG relative luminance."""
        return wcag_relative_luminance(hex_color) < 0.179

    def _is_light_theme(self) -> bool:
        """Return True if current active theme panel background is light."""
        return not self._is_dark_color(self.theme.get("bg_panel", "#ffffff"))

    @staticmethod
    def _shift_hex(hex_color: str, delta: int) -> str:
        """Lighten or darken a #RRGGBB color by `delta` per channel."""
        if not HEX_COLOR_RE.match(hex_color):
            return hex_color
        r = max(0, min(255, int(hex_color[1:3], 16) + delta))
        g = max(0, min(255, int(hex_color[3:5], 16) + delta))
        b = max(0, min(255, int(hex_color[5:7], 16) + delta))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _tag_role(self, widget: tk.Widget, role: str) -> tk.Widget:
        """Attach a semantic theme role to a Tk widget for live re-theming."""
        setattr(widget, "_misora_role", role)
        return widget

    @property
    def dialogue_font_family(self) -> str:
        """Resolved active Tk font family backed by self.prefs."""
        return self._resolve_active_dialogue_font_parts()[0]

    @dialogue_font_family.setter
    def dialogue_font_family(self, value: str) -> None:
        val = str(value).strip() or PRESET_GLOBAL
        self.prefs["dialogue_font_family"] = val
        if hasattr(self, "var_font_family") and val in BUILTIN_FONT_PRESETS:
            self.var_font_family.set(val)

    @property
    def dialogue_font_size(self) -> int:
        """Active dialogue font size (pt) backed by self.prefs."""
        return int(self.prefs.get("dialogue_font_size", 11))

    @dialogue_font_size.setter
    def dialogue_font_size(self, value: int) -> None:
        sz = max(8, min(28, int(value)))
        self.prefs["dialogue_font_size"] = sz
        if hasattr(self, "var_dlg_font_sz"):
            self.var_dlg_font_sz.set(sz)

    def _get_available_font_families(self) -> Tuple[str, ...]:
        try:
            return tuple(tkfont.families(root=self))
        except Exception:
            return ()

    def _resolve_active_dialogue_font_parts(self) -> Tuple[str, Optional[str]]:
        sel = self.prefs.get("dialogue_font_family", PRESET_GLOBAL)
        if hasattr(self, "font_manager"):
            return self.font_manager.resolve_font_parts(sel, available_families=self._get_available_font_families())
        return (str(sel or "Segoe UI"), None)

    def _get_dialogue_font_tuple(self, size: Optional[int] = None, *styles: str) -> Tuple[Any, ...]:
        fam, weight = self._resolve_active_dialogue_font_parts()
        sz = int(size if size is not None else self.dialogue_font_size)
        style_list: List[str] = []
        if weight and weight not in styles:
            style_list.append(weight)
        for st in styles:
            if st and st not in style_list:
                style_list.append(st)
        if style_list:
            return (fam, sz, *style_list)
        return (fam, sz)

    def _apply_theme_and_fonts_live(self, save: bool = True) -> None:
        """Re-apply current theme colors (with WCAG contrast) and font sizes across all active widgets."""
        THEME.update(self.theme)
        self._apply_styles()

        t = self.theme
        d_fam = self.dialogue_font_family
        d_sz = self.dialogue_font_size
        d_font_tuple = self._get_dialogue_font_tuple(d_sz)
        r_sz = int(self.prefs["raw_font_size"])
        u_sz = int(self.prefs["ui_font_size"])

        accent_fg = best_contrast_fg(t["misora_pink"])
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        hl_fg = best_contrast_fg(t["highlight_bg"], t["fg_text"], "#ffffff")

        self.configure(bg=t["bg_dark"])

        for menu_obj in getattr(self, "_all_menus", []):
            try:
                menu_obj.configure(
                    bg=t["bg_panel"],
                    fg=panel_fg,
                    activebackground=t["misora_pink"],
                    activeforeground=accent_fg,
                )
            except Exception:
                pass

        def walk(w: tk.Widget) -> None:
            role = getattr(w, "_misora_role", None)
            try:
                if role == "dark":
                    w.configure(bg=t["bg_dark"])
                elif role == "panel":
                    w.configure(bg=t["bg_panel"])
                elif role == "ribbon":
                    w.configure(bg=t["bg_editor"], highlightbackground=t["border"])
                elif role == "panel_box":
                    w.configure(bg=t["bg_panel"], highlightbackground=t["border"])
                elif role == "editor_box":
                    w.configure(bg=t["bg_editor"])
                elif role == "sash":
                    w.configure(bg=t["border"])
                elif role == "label_panel":
                    w.configure(bg=t["bg_panel"], fg=panel_fg, font=("Segoe UI", u_sz))
                elif role == "label_muted":
                    w.configure(bg=t["bg_panel"], fg=t["fg_muted"], font=("Segoe UI", max(8, u_sz - 1)))
                elif role == "label_ribbon":
                    w.configure(bg=t["bg_editor"], fg=t["fg_muted"], font=("Segoe UI", max(8, u_sz - 1), "bold"))
                elif role == "label_accent":
                    w.configure(bg=t["bg_panel"], fg=t["misora_pink"], font=("Segoe UI", u_sz, "bold"))
                elif role == "label_voice":
                    w.configure(bg=t["bg_panel"], fg=t["accent_blue"], font=("Segoe UI", max(8, u_sz - 1)))
                elif role == "label_sep":
                    w.configure(bg=t["bg_panel"], fg=t["border"])
                elif role == "label_ribbon_sep":
                    w.configure(bg=t["bg_editor"], fg=t["border"])
                elif role == "ribbon_primary_btn":
                    w.configure(
                        bg=t["misora_pink"],
                        fg=accent_fg,
                        activebackground=t["misora_pink_hover"],
                        activeforeground=accent_fg,
                    )
                elif role == "ribbon_btn":
                    dark_p = self._is_dark_color(t["bg_panel"])
                    r_btn_bg = self._shift_hex(t["bg_panel"], 10 if dark_p else -8)
                    r_btn_h = self._shift_hex(t["bg_panel"], 22 if dark_p else -16)
                    r_btn_fg = best_contrast_fg(r_btn_bg, t["fg_text"], "#ffffff")
                    w.configure(
                        bg=r_btn_bg,
                        fg=r_btn_fg,
                        activebackground=r_btn_h,
                        activeforeground=r_btn_fg,
                    )
                elif role in ("ribbon_undo_btn", "ribbon_redo_btn"):
                    dark_p = self._is_dark_color(t["bg_panel"])
                    r_btn_bg = self._shift_hex(t["bg_panel"], 10 if dark_p else -8)
                    r_btn_h = self._shift_hex(t["bg_panel"], 22 if dark_p else -16)
                    grn = t.get("accent_green", "#2e7d32")
                    w.configure(
                        bg=r_btn_bg,
                        fg=grn,
                        activebackground=r_btn_h,
                        activeforeground=grn,
                    )
                elif role == "check_panel":
                    panel_dis_fg = _wcag_muted_fg(t["fg_muted"], t["bg_panel"], panel_fg)
                    panel_chk_fg = _ensure_wcag_fg(panel_fg, t["bg_dark"], t["fg_text"], "#ffffff")
                    w.configure(
                        bg=t["bg_panel"],
                        fg=panel_chk_fg,
                        selectcolor=t["bg_dark"],
                        activebackground=t["bg_panel"],
                        activeforeground=panel_chk_fg,
                        disabledforeground=panel_dis_fg,
                        font=("Segoe UI", u_sz),
                    )
                elif role == "check_accent":
                    panel_dis_fg = _wcag_muted_fg(t["fg_muted"], t["bg_panel"], panel_fg)
                    panel_chk_fg = _ensure_wcag_fg(panel_fg, t["bg_dark"], t["fg_text"], "#ffffff")
                    accent_chk_fg = _ensure_wcag_fg(t["misora_pink"], t["bg_panel"], t["fg_text"], "#ffffff")
                    w.configure(
                        bg=t["bg_panel"],
                        fg=panel_chk_fg,
                        selectcolor=t["bg_dark"],
                        activebackground=t["bg_panel"],
                        activeforeground=accent_chk_fg,
                        disabledforeground=panel_dis_fg,
                        font=("Segoe UI", max(8, u_sz - 1), "bold"),
                    )
                elif role == "check_ribbon":
                    editor_dis_fg = _wcag_muted_fg(t["fg_muted"], t["bg_editor"], editor_fg)
                    editor_chk_fg = _ensure_wcag_fg(editor_fg, t["bg_panel"], t["fg_text"], "#ffffff")
                    ribbon_act_fg = _ensure_wcag_fg(t["misora_pink"], t["bg_editor"], t["fg_text"], "#ffffff")
                    w.configure(
                        bg=t["bg_editor"],
                        fg=editor_chk_fg,
                        selectcolor=t["bg_panel"],
                        activebackground=t["bg_editor"],
                        activeforeground=ribbon_act_fg,
                        disabledforeground=editor_dis_fg,
                        font=("Segoe UI", max(8, u_sz - 1), "bold"),
                    )
                elif role == "entry_editor":
                    w.configure(
                        bg=t["bg_editor"],
                        fg=editor_fg,
                        insertbackground=t["misora_pink"],
                        highlightbackground=t["border"],
                        highlightcolor=t["misora_pink"],
                    )
                elif role == "entry_speaker":
                    w.configure(
                        bg=t["bg_editor"],
                        fg=editor_fg,
                        insertbackground=t["misora_pink"],
                        selectbackground=t["highlight_bg"],
                        selectforeground=hl_fg,
                        font=(d_fam, max(9, d_sz - 1), "bold"),
                    )
            except Exception:
                pass

            for child in w.winfo_children():
                walk(child)

        walk(self)
        # Also re-theme any currently-open child Toplevel windows
        for child_win in self.winfo_children():
            if isinstance(child_win, tk.Toplevel) and child_win.winfo_exists():
                try:
                    child_win.configure(bg=t["bg_panel"])
                except Exception:
                    pass
                walk(child_win)

        self.txt_results.configure(
            bg=t["bg_editor"],
            fg=editor_fg,
            font=("Segoe UI", u_sz),
        )
        self.txt_results.tag_configure("file_header", font=("Segoe UI", u_sz, "bold"), foreground=t["misora_pink"])
        self.txt_results.tag_configure("box_badge", font=("Consolas", max(8, u_sz - 1), "bold"), foreground=t["accent_blue"])
        self.txt_results.tag_configure("speaker_tag", font=("Segoe UI", u_sz, "bold"), foreground=editor_fg)
        self.txt_results.tag_configure("selected_row", background=t["highlight_bg"], foreground=hl_fg)
        self.txt_results.tag_configure(
            "match_hl",
            background=t["misora_pink"],
            foreground=accent_fg,
            font=("Segoe UI", u_sz, "bold"),
        )

        if hasattr(self, "txt_opened_files"):
            self.txt_opened_files.configure(
                bg=t["bg_editor"],
                fg=editor_fg,
                font=("Segoe UI", u_sz),
            )
            self.txt_opened_files.tag_configure("file_active", font=("Segoe UI", u_sz, "bold"), foreground=t["misora_pink"], background=t["highlight_bg"])
            self.txt_opened_files.tag_configure("file_dirty", font=("Segoe UI", u_sz, "bold"), foreground=t["accent_yellow"])
            self.txt_opened_files.tag_configure("file_normal", font=("Segoe UI", u_sz), foreground=editor_fg)
            self.txt_opened_files.tag_configure("file_dim", font=("Segoe UI", max(8, u_sz - 1)), foreground=t["fg_muted"])

        gutter_bg = "#e8e8e8" if self._is_light_theme() else "#2d2d30"
        gutter_fg = "#707070" if self._is_light_theme() else "#858585"
        if hasattr(self, "gutter_clean"):
            self.gutter_clean.configure(
                bg=gutter_bg,
                fg=gutter_fg,
                font=d_font_tuple,
                pady=8,
                spacing1=3,
                spacing3=3,
            )
            self._apply_gutter_overflow_tag(self.gutter_clean)
        if hasattr(self, "gutter_cont"):
            self.gutter_cont.configure(bg=gutter_bg, fg=gutter_fg)
        if hasattr(self, "ruler_clean"):
            self.ruler_clean.configure(bg=gutter_bg)
        if hasattr(self, "ruler_cont"):
            self.ruler_cont.configure(bg=gutter_bg)

        self.txt_dialogue.configure(
            font=d_font_tuple,
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=hl_fg,
            highlightthickness=0,
            bd=1,
            relief="solid",
        )
        self._configure_editor_rich_tags(self.txt_dialogue, d_fam, d_sz)
        self._apply_overflow_highlights(self.txt_dialogue)
        self._redraw_pixel_rulers()
        self._update_char_overflow_indicator()

        self.txt_continuous.configure(
            font=d_font_tuple,
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=hl_fg,
            highlightthickness=0,
            bd=1,
            relief="solid",
        )
        if hasattr(self, "txt_all_script"):
            self.txt_all_script.configure(
                font=d_font_tuple,
                bg=t["bg_panel"],
                fg=editor_fg,
                selectbackground=t["highlight_bg"],
                selectforeground=hl_fg,
            )
            self._configure_editor_rich_tags(self.txt_all_script, d_fam, d_sz)
            if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get() and self.current_doc:
                self._render_continuous_view()
        if hasattr(self, "txt_box0_summary"):
            self.txt_box0_summary.configure(
                font=d_font_tuple,
                bg=t["bg_editor"],
                fg=editor_fg,
                insertbackground=t["misora_pink"],
                selectbackground=t["highlight_bg"],
                selectforeground=hl_fg,
                highlightthickness=0,
                bd=1,
                relief="solid",
            )
            self._configure_editor_rich_tags(self.txt_box0_summary, d_fam, d_sz)
        if hasattr(self, "entry_box0_title"):
            self.entry_box0_title.configure(
                font=d_font_tuple,
                bg=t["bg_editor"],
                fg=editor_fg,
                insertbackground=t["misora_pink"],
            )
        if hasattr(self, "entry_box0_subtitle"):
            self.entry_box0_subtitle.configure(
                font=d_font_tuple,
                bg=t["bg_editor"],
                fg=editor_fg,
                insertbackground=t["misora_pink"],
            )

        if hasattr(self, "txt_raw"):
            self.txt_raw.configure(
                highlightthickness=0,
                bd=1,
                relief="solid",
            )
        self.txt_continuous.tag_configure("cont_divider", foreground=t["misora_pink"], font=("Consolas", max(8, d_sz - 1), "bold"), spacing1=4, spacing3=2)
        self.txt_continuous.tag_configure("cont_badge", foreground=t["misora_pink"], font=("Consolas", max(8, d_sz - 2), "bold"))
        self.txt_continuous.tag_configure("cont_speaker", foreground=editor_fg, font=(d_fam, max(9, d_sz - 1), "bold"))
        self.txt_continuous.tag_configure("cont_narrator", foreground=t["fg_muted"], font=(d_fam, max(8, d_sz - 2), "italic"))
        self.txt_continuous.tag_configure("cont_voice", foreground=t["accent_blue"], font=("Segoe UI", max(8, d_sz - 3)))
        self.txt_continuous.tag_configure("cont_active_header", background=t["highlight_bg"])
        self.txt_continuous.tag_configure("cont_body", foreground=editor_fg, font=(d_fam, d_sz))
        self._configure_editor_rich_tags(self.txt_continuous, d_fam, d_sz)

        raw_bg = self._shift_hex(t["bg_editor"], -6)
        self.txt_raw.configure(
            font=("Consolas", r_sz),
            bg=raw_bg,
            fg=t["fg_muted"],
            insertbackground=t["misora_pink"],
        )

        if hasattr(self, "txt_console"):
            self._apply_console_theme()

        if hasattr(self, "txt_glossary"):
            self.txt_glossary.configure(bg=t["bg_editor"], fg=editor_fg, font=("Segoe UI", u_sz))
            self.txt_glossary.tag_configure("gl_tag", font=("Consolas", u_sz, "bold"), foreground=t["misora_pink"])
            self.txt_glossary.tag_configure("gl_title", font=("Segoe UI", u_sz, "bold"), foreground=editor_fg)
            self.txt_glossary.tag_configure("gl_syntax", font=("Consolas", max(8, u_sz - 1)), foreground=t["accent_blue"])
            self.txt_glossary.tag_configure("gl_desc", font=("Segoe UI", max(8, u_sz - 1)), foreground=t["fg_muted"])
            self.txt_glossary.tag_configure("gl_selected", background=t["highlight_bg"], foreground=hl_fg)
            self._render_glossary_list()

        if hasattr(self, "_apply_mtl_all_script_theme_tags"):
            self._apply_mtl_all_script_theme_tags()

        for key, btn in self._theme_swatch_buttons.items():
            if key in t:
                btn.configure(bg=t[key], activebackground=t[key])
            if key in self._theme_hex_vars and self._theme_hex_vars[key].get().lower() != t[key].lower():
                self._theme_hex_vars[key].set(t[key])

        if self.var_preview_compiled.get():
            self._update_views()
        else:
            self._highlight_ngui_tags()
            self._auto_resize_dialogue_box()

        if save:
            self._save_user_prefs()

    def set_status(
        self,
        message: str,
        is_error: bool = False,
        timeout_ms: Optional[int] = None,
    ) -> None:
        """Update the main status bar label text with contrast/error styling and optional timeout."""
        try:
            if hasattr(self, "_status_after_id") and self._status_after_id:
                try:
                    self.after_cancel(self._status_after_id)
                except Exception:
                    pass
                self._status_after_id = None

            if not hasattr(self, "lbl_status") or not self.lbl_status or not self.lbl_status.winfo_exists():
                return

            t = self.theme
            if is_error:
                error_fg = "#d94862" if t.get("fg_muted") != "#d94862" else "#ff7da7"
                self.lbl_status.config(text=message, fg=error_fg)
            else:
                normal_fg = t.get("fg_muted", "#9c8ec0")
                self.lbl_status.config(text=message, fg=normal_fg)

            if timeout_ms is not None and timeout_ms > 0:
                self._status_after_id = self.after(timeout_ms, self._reset_status)
        except Exception:
            pass

    def _reset_status(self) -> None:
        """Restore the status bar to default text and normal theme styling."""
        try:
            self._status_after_id = None
            if hasattr(self, "lbl_status") and self.lbl_status and self.lbl_status.winfo_exists():
                t = self.theme
                self.lbl_status.config(
                    text=self._default_status_text,
                    fg=t.get("fg_muted", "#9c8ec0"),
                )
        except Exception:
            pass

    def show_toast(
        self,
        message: str,
        duration_ms: int = 2200,
        is_accent: bool = True,
        is_error: bool = False,
        status_bar: bool = True,
    ) -> None:
        """Display a non-intrusive floating toast notification above the action bar."""
        try:
            if status_bar:
                self.set_status(message, is_error=is_error)

            # Check if active toast has identical message (coalesce duplicate)
            if self._toast_active and hasattr(self, "_toast_widget") and self._toast_widget and self._toast_widget.winfo_exists():
                try:
                    current_text = self._toast_widget.cget("text")
                except Exception:
                    current_text = None
                if current_text == message:
                    if self._toast_after_id:
                        try:
                            self.after_cancel(self._toast_after_id)
                        except Exception:
                            pass
                    self._toast_after_id = self.after(duration_ms, self._dismiss_toast)
                    return

            if self._toast_active:
                if hasattr(self, "_toast_queue"):
                    if self._toast_queue and self._toast_queue[-1][0] == message:
                        return
                    self._toast_queue.append((message, duration_ms, is_accent, is_error))
                return

            self._display_toast(message, duration_ms, is_accent, is_error)
        except Exception:
            pass

    def _display_toast(
        self,
        message: str,
        duration_ms: int,
        is_accent: bool,
        is_error: bool,
    ) -> None:
        """Render and place the toast widget with appropriate theme styling and auto-dismiss timer."""
        try:
            self._toast_active = True
            if not hasattr(self, "_toast_widget") or not self._toast_widget or not self._toast_widget.winfo_exists():
                self._toast_widget = tk.Label(
                    self,
                    text="",
                    font=("Segoe UI", 10, "bold"),
                    bd=1,
                    relief="solid",
                    padx=14,
                    pady=6,
                    cursor="hand2",
                )
                self._toast_widget.bind("<Button-1>", lambda _e=None: self._dismiss_toast())

            t = self.theme
            if is_error:
                bg_col = "#d94862"
                fg_col = best_contrast_fg(bg_col, "#14141a", "#ffffff")
            elif is_accent:
                bg_col = t.get("misora_pink", "#a66cff")
                fg_col = best_contrast_fg(bg_col)
            else:
                bg_col = t.get("bg_editor", "#282c34")
                fg_col = best_contrast_fg(bg_col)

            border_col = t.get("border", "#4b5263")
            self._toast_widget.configure(
                text=message,
                bg=bg_col,
                fg=fg_col,
                highlightthickness=1,
                highlightbackground=border_col,
            )
            # Geometry: place anchored south-east above action bar without occluding buttons
            self._toast_widget.place(relx=1.0, rely=1.0, x=-16, y=-52, anchor="se")
            self._toast_widget.lift()

            if hasattr(self, "_toast_after_id") and self._toast_after_id:
                try:
                    self.after_cancel(self._toast_after_id)
                except Exception:
                    pass
                self._toast_after_id = None

            self._toast_after_id = self.after(duration_ms, self._dismiss_toast)
        except Exception:
            self._toast_active = False

    def _dismiss_toast(self) -> None:
        """Dismiss active toast and display next queued notification if any."""
        try:
            if hasattr(self, "_toast_after_id") and self._toast_after_id:
                try:
                    self.after_cancel(self._toast_after_id)
                except Exception:
                    pass
                self._toast_after_id = None

            if hasattr(self, "_toast_widget") and self._toast_widget and self._toast_widget.winfo_exists():
                self._toast_widget.place_forget()

            if hasattr(self, "_toast_queue") and self._toast_queue:
                msg, dur, acc, err = self._toast_queue.popleft()
                if len(self._toast_queue) > 2 and dur > 1200:
                    dur = 1200
                self._display_toast(msg, dur, acc, err)
            else:
                self._toast_active = False
        except Exception:
            self._toast_active = False

    def _sweep_cstyle_tags(self, widget: Optional[tk.Text]) -> None:
        """Delete all cached compiled NGUI style tags (`cstyle_*`) from `widget` (GEM-E03)."""
        if not widget or not widget.winfo_exists():
            return
        for tag_name in list(widget.tag_names()):
            if tag_name.startswith("cstyle_"):
                widget.tag_delete(tag_name)

    def _configure_editor_rich_tags(self, widget: tk.Text, d_fam: str, d_sz: int) -> None:
        """Configure syntax highlight & compiled NGUI preview tags on a dialogue text widget."""
        t = self.theme
        hl_fg = best_contrast_fg(t["highlight_bg"], t["misora_pink"], "#ffffff")
        widget.tag_configure(
            "secret_whitespace",
            background="",
        )
        widget.tag_configure(
            "ngui_tag",
            foreground=t["accent_yellow"],
            font=("Consolas", max(8, d_sz - 1)),
        )
        widget.tag_configure(
            "compiled_ruby",
            foreground=hl_fg,
            background=t["highlight_bg"],
            font=(d_fam, max(7, d_sz - 3), "bold"),
            offset=5,
        )
        widget.tag_configure(
            "compiled_player",
            foreground=best_contrast_fg(t["highlight_bg"], t["accent_blue"], "#ffffff"),
            background=t["highlight_bg"],
            font=(d_fam, d_sz, "bold"),
        )
        ov_bg = "#4a1c24" if not self._is_light_theme() else "#ffd6dc"
        ov_fg = best_contrast_fg(
            ov_bg,
            "#ff8fa3" if not self._is_light_theme() else "#9b111e",
            "#ffffff" if not self._is_light_theme() else "#1a1a1a",
        )
        widget.tag_configure(
            "line_overflow",
            background=ov_bg,
            foreground=ov_fg,
            underline=True,
        )
        widget.tag_configure(
            "search_hit",
            background=t["highlight_bg"],
            foreground=hl_fg,
            underline=True,
        )
        self._sweep_cstyle_tags(widget)
        widget.tag_raise("line_overflow")
        widget.tag_raise("ngui_tag")
        widget.tag_raise("search_hit")

    # -------------------------------------------------------------------------
    # Native Windows Drag & Drop — Crash-Safe Single-HWND Subclassing (#1)
    # -------------------------------------------------------------------------
    def _init_drag_and_drop(self) -> None:
        """Register native Win32 WM_DROPFILES handler safely on the top-level outer HWND."""
        if sys.platform != "win32":
            return

        try:
            self.update_idletasks()
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
            GWLP_WNDPROC = -4
            WM_DROPFILES = 0x0233
            WM_COPYDATA = 0x004A
            WM_COPYGLOBALDATA = 0x0049
            MSGFLT_ALLOW = 1

            LRESULT = ctypes.c_ssize_t
            LONG_PTR = ctypes.c_ssize_t

            user32.GetParent.argtypes = [wintypes.HWND]
            user32.GetParent.restype = wintypes.HWND

            shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
            shell32.DragAcceptFiles.restype = None

            shell32.DragQueryFileW.argtypes = [
                wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT
            ]
            shell32.DragQueryFileW.restype = wintypes.UINT

            shell32.DragFinish.argtypes = [wintypes.HANDLE]
            shell32.DragFinish.restype = None

            user32.CallWindowProcW.argtypes = [
                LONG_PTR, wintypes.HWND, wintypes.UINT,
                wintypes.WPARAM, wintypes.LPARAM
            ]
            user32.CallWindowProcW.restype = LRESULT

            get_wnd_proc = user32.GetWindowLongPtrW if is_64bit else user32.GetWindowLongW
            get_wnd_proc.argtypes = [wintypes.HWND, ctypes.c_int]
            get_wnd_proc.restype = LONG_PTR

            set_wnd_proc = user32.SetWindowLongPtrW if is_64bit else user32.SetWindowLongW
            set_wnd_proc.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
            set_wnd_proc.restype = LONG_PTR

            inner_hwnd = int(self.winfo_id())
            parent_hwnd = int(user32.GetParent(inner_hwnd) or 0)
            target_hwnd = parent_hwnd if parent_hwnd else inner_hwnd
            self._drop_hwnd = target_hwnd

            try:
                user32.ChangeWindowMessageFilterEx.argtypes = [
                    wintypes.HWND, wintypes.UINT, wintypes.DWORD, ctypes.c_void_p
                ]
                user32.ChangeWindowMessageFilterEx.restype = wintypes.BOOL
                for hwnd in {h for h in (target_hwnd, inner_hwnd) if h}:
                    for msg_id in (WM_DROPFILES, WM_COPYDATA, WM_COPYGLOBALDATA):
                        user32.ChangeWindowMessageFilterEx(hwnd, msg_id, MSGFLT_ALLOW, None)
            except Exception as filter_exc:
                self.logger.debug("Drag & Drop", f"ChangeWindowMessageFilterEx skipped: {filter_exc}")

            WNDPROC = ctypes.WINFUNCTYPE(
                LRESULT, wintypes.HWND, wintypes.UINT,
                wintypes.WPARAM, wintypes.LPARAM
            )

            self._wndprocs = {}

            def _make_wndproc(orig_proc_addr: int):
                def _wndproc(hwnd, msg, wparam, lparam):
                    try:
                        if msg == WM_DROPFILES:
                            hdrop = wintypes.HANDLE(wparam)
                            dropped: List[Path] = []
                            try:
                                count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                                for idx in range(count):
                                    length = shell32.DragQueryFileW(hdrop, idx, None, 0)
                                    if length > 0:
                                        buf = ctypes.create_unicode_buffer(length + 1)
                                        shell32.DragQueryFileW(hdrop, idx, buf, length + 1)
                                        if buf.value:
                                            dropped.append(Path(buf.value))
                            finally:
                                shell32.DragFinish(hdrop)

                            if dropped and not self._dnd_in_progress:
                                self._dnd_in_progress = True
                                self.after(50, self._handle_dropped_paths, dropped)
                            return 0
                    except Exception as cb_exc:
                        self.logger.exception("Drag & Drop WNDPROC error:", cb_exc)
                        return 0

                    return user32.CallWindowProcW(orig_proc_addr, hwnd, msg, wparam, lparam)

                return WNDPROC(_wndproc)

            shell32.DragAcceptFiles(target_hwnd, True)
            orig_addr = int(get_wnd_proc(target_hwnd, GWLP_WNDPROC) or 0)
            if orig_addr:
                cb = _make_wndproc(orig_addr)
                cb_addr = ctypes.cast(cb, ctypes.c_void_p).value
                set_wnd_proc(target_hwnd, GWLP_WNDPROC, cb_addr)
                self._wndprocs[target_hwnd] = (cb, orig_addr)
                self.logger.debug("Drag & Drop", f"Subclassed top-level HWND={hex(target_hwnd)}")
        except Exception as e:
            self.logger.warning("Drag & Drop", f"Drag-and-drop hook warning: {e}")

    def _cleanup_drag_and_drop(self) -> None:
        """Restore original WNDPROC on registered HWNDs prior to window destruction."""
        if sys.platform != "win32" or not self._wndprocs:
            return
        try:
            user32 = ctypes.windll.user32
            is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
            GWLP_WNDPROC = -4
            LONG_PTR = ctypes.c_ssize_t
            set_wnd_proc = user32.SetWindowLongPtrW if is_64bit else user32.SetWindowLongW
            set_wnd_proc.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
            set_wnd_proc.restype = LONG_PTR

            for hwnd, (_cb, orig_addr) in list(self._wndprocs.items()):
                try:
                    if user32.IsWindow(hwnd) and orig_addr:
                        set_wnd_proc(hwnd, GWLP_WNDPROC, orig_addr)
                except Exception:
                    pass
            self._wndprocs.clear()
        except Exception:
            pass

    def on_force_open_file(self) -> None:
        """Prompt user to open ANY file (bypassing format/extension guards) as raw/plain text."""
        p = filedialog.askopenfilename(
            title="Force Open Any File (Raw / Plain Text)",
            filetypes=[("All Files (*.*)", "*.*")],
            initialdir=str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) else None,
        )
        if p:
            self.open_file(Path(p))

    def _check_batch_safety(self, files: List[Path]) -> bool:
        """Prompt confirmation if dropping many files or very large files."""
        batch_thresh = getattr(self, "dnd_batch_threshold", 10)
        size_thresh_mb = getattr(self, "dnd_size_threshold_mb", 25.0)

        # 1. Batch count check
        if batch_thresh > 0 and len(files) > batch_thresh:
            ok = messagebox.askyesno(
                "Confirm Large Batch",
                f"You are about to open {len(files)} files at once.\n\n"
                f"Opening many files may take a few moments. Proceed?",
                default=messagebox.YES,
            )
            if not ok:
                return False

        # 2. File size check
        if size_thresh_mb > 0:
            large_files: List[Tuple[Path, float]] = []
            for f in files:
                try:
                    sz_mb = f.stat().st_size / (1024 * 1024)
                    if sz_mb >= size_thresh_mb:
                        large_files.append((f, sz_mb))
                except Exception:
                    pass
            if large_files:
                sample_list = "\n".join(f"• {f.name} ({sz:.1f} MB)" for f, sz in large_files[:5])
                if len(large_files) > 5:
                    sample_list += f"\n• ... and {len(large_files) - 5} more"
                ok = messagebox.askyesno(
                    "Confirm Large File(s)",
                    f"The following file(s) exceed {size_thresh_mb:g} MB:\n\n"
                    f"{sample_list}\n\n"
                    f"Opening very large files may consume extra memory. Proceed?",
                    default=messagebox.YES,
                )
                if not ok:
                    return False
        return True

    def _on_dnd_settings_dialog(self) -> None:
        """Dialog to configure Drag & Drop safety thresholds and filters."""
        t = self.theme
        dlg = tk.Toplevel(self)
        dlg.title("Drag & Drop Safety Settings")
        dlg.geometry("480x280")
        dlg.minsize(440, 240)
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=t["bg_panel"])

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        content = tk.Frame(dlg, bg=t["bg_panel"], padx=18, pady=16)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text="Drag & Drop Safety Settings",
            font=("Segoe UI", 11, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w", pady=(0, 10))

        var_filter = tk.BooleanVar(master=dlg, value=getattr(self, "dnd_filter_binary", True))
        cb = tk.Checkbutton(
            content,
            text="Filter out binary files (.exe, .dll, images, media, archives) on drop",
            variable=var_filter,
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
        )
        cb.pack(anchor="w", pady=(0, 10))

        # Row 1: Batch threshold
        r1 = tk.Frame(content, bg=t["bg_panel"])
        r1.pack(fill="x", pady=4)
        tk.Label(r1, text="Batch prompt threshold (files):", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=28, anchor="w").pack(side="left")
        var_batch = tk.StringVar(master=dlg, value=str(getattr(self, "dnd_batch_threshold", 10)))
        ent_batch = tk.Entry(r1, textvariable=var_batch, width=8, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid")
        ent_batch.pack(side="left", padx=4)
        tk.Label(r1, text="(0 = never prompt)", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left", padx=4)

        # Row 2: Size threshold
        r2 = tk.Frame(content, bg=t["bg_panel"])
        r2.pack(fill="x", pady=4)
        tk.Label(r2, text="Large file threshold (MB):", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=28, anchor="w").pack(side="left")
        var_size = tk.StringVar(master=dlg, value=str(getattr(self, "dnd_size_threshold_mb", 25.0)))
        ent_size = tk.Entry(r2, textvariable=var_size, width=8, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid")
        ent_size.pack(side="left", padx=4)
        tk.Label(r2, text="(0 = never prompt)", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left", padx=4)

        # Bottom buttons
        btn_bar = tk.Frame(dlg, bg=t["bg_panel"], padx=18, pady=12)
        btn_bar.pack(fill="x", side="bottom")

        def _safe_close(_e: Optional[tk.Event] = None):
            safe_grab_release(dlg)
            dlg.destroy()

        def _save():
            try:
                b_val = max(0, int(var_batch.get().strip()))
            except ValueError:
                b_val = 10
            try:
                s_val = max(0.0, float(var_size.get().strip()))
            except ValueError:
                s_val = 25.0
            self.dnd_batch_threshold = b_val
            self.dnd_size_threshold_mb = s_val
            self.dnd_filter_binary = bool(var_filter.get())
            self._save_user_prefs(silent=True)
            self.lbl_status.config(text="Drag & Drop safety settings saved.")
            safe_grab_release(dlg)
            dlg.destroy()
            messagebox.showinfo(
                "Settings Saved",
                "Drag & Drop safety settings have been saved.",
                parent=self,
            )

        dlg.protocol("WM_DELETE_WINDOW", _safe_close)
        dlg.bind("<Escape>", _safe_close)
        ttk.Button(btn_bar, text="Save Settings", style="Accent.TButton", command=_save).pack(side="left", padx=(0, 6))
        ttk.Button(btn_bar, text="Cancel", style="TButton", command=_safe_close).pack(side="left")

    def _handle_dropped_paths(self, paths: List[Path]) -> None:
        """Process files or folders dropped onto the Misora window safely."""
        self._dnd_in_progress = False  # reset early so crashes don't lock DnD
        try:
            if not paths:
                return
            self.logger.info("Drag & Drop", f"Received {len(paths)} dropped item(s): {[str(p) for p in paths]}")

            known_binary_exts = {
                ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tga",
                ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2",
                ".db", ".sqlite", ".db3",
                ".mp3", ".wav", ".ogg", ".flac", ".aac",
                ".mp4", ".mkv", ".avi", ".mov", ".usm",
                ".pdf", ".doc", ".docx", ".xls", ".xlsx"
            }

            files = [p for p in paths if p.is_file()]
            dirs = [p for p in paths if p.is_dir()]

            # Guard: check for completely empty files (0 bytes)
            if files:
                empty_files = [f for f in files if f.stat().st_size == 0]
                if empty_files and len(empty_files) == len(files):
                    self.lbl_status.config(text="Dropped file(s) are empty (0 bytes). Scope and documents unchanged.")
                    messagebox.showwarning(
                        "Empty File(s)",
                        f"The dropped file(s) are completely empty (0 bytes).\n\n"
                        f"No files were opened, and search/project scopes were left unchanged.",
                        parent=self
                    )
                    return

            # 1. Process dropped files
            if files:
                misora_files = [f for f in files if f.suffix.lower() == MISORA_WORKSPACE_EXT and f.stat().st_size > 0]
                regular_files = [f for f in files if f.suffix.lower() != MISORA_WORKSPACE_EXT]
                if misora_files:
                    self.open_project(misora_files[0])
                files = regular_files

            if files:
                filter_bin = getattr(self, "dnd_filter_binary", True)
                if filter_bin:
                    to_open = [f for f in files if f.suffix.lower() not in known_binary_exts and f.stat().st_size > 0]
                    skipped = [f for f in files if f.suffix.lower() in known_binary_exts or f.stat().st_size == 0]
                else:
                    to_open = [f for f in files if f.stat().st_size > 0]
                    skipped = [f for f in files if f.stat().st_size == 0]

                if skipped and not to_open:
                    self.lbl_status.config(
                        text=f"Skipped {len(skipped)} binary/unsupported file(s). Use 'File -> Force Open Any File...' to override."
                    )
                    self.logger.warning("Drag & Drop", f"Skipped binary/empty files: {[f.name for f in skipped]}")
                elif to_open:
                    if self._check_batch_safety(to_open):
                        opened = 0
                        for f in to_open:
                            try:
                                self.open_file(f)
                                opened += 1
                            except Exception as exc:  # noqa: BLE001
                                self.logger.error("Drag & Drop", f"Could not open {f.name}: {exc}")
                        msg = f"Opened {opened} file(s) via drag & drop."
                        if skipped:
                            msg += f" ({len(skipped)} binary file(s) skipped)"
                        self.lbl_status.config(text=msg)
                    else:
                        self.lbl_status.config(text="File drop cancelled by user.")

            # 2. Process dropped folder(s)
            if dirs:
                if len(dirs) > 1:
                    extra_count = len(dirs) - 1
                    extra_names = ", ".join(f"'{d.name}'" for d in dirs[1:4])
                    if extra_count > 3:
                        extra_names += f" and {extra_count - 3} more"
                    warn_msg = f"Multiple folders dropped ({len(dirs)}). Opened first folder '{dirs[0].name}'; remaining {extra_count} folder(s) ignored."
                    self.lbl_status.config(text=warn_msg)
                    self.show_toast(f"⚠ Only 1 folder opened. {extra_count} ignored: {extra_names}")
                    self.logger.warning("Drag & Drop", warn_msg)
                self._process_opened_folder(dirs[0], source_label="Drag & Drop")
        except Exception as exc:
            self.logger.exception("Error while handling dropped path(s):", exc)
            messagebox.showerror("Drag & Drop Error", f"Failed to open dropped item:\n{exc}")
        finally:
            self._dnd_in_progress = False

    def _process_opened_folder(self, folder: Path, source_label: str = "Folder") -> None:
        """Handle opening a folder with consistent multi-file prompt, batch safety, and scope assignment."""
        folder = Path(folder).resolve()
        try:
            story_files = (
                sorted(folder.glob("*.unity3d")) +
                sorted(folder.glob("*.asset")) +
                sorted(folder.glob("*.txt"))
            )
        except (OSError, PermissionError) as scan_err:
            self.logger.error(source_label, f"Error scanning folder '{folder}': {scan_err}")
            messagebox.showerror("Folder Access Error", f"Could not access folder '{folder.name}':\n{scan_err}", parent=self)
            return

        if not story_files:
            if source_label == "Drag & Drop":
                self.lbl_status.config(
                    text=f"Dropped folder '{folder.name}' contains no story files (.unity3d/.asset/.txt). Scope unchanged."
                )
                self.show_toast(f"No story files in: {folder.name}")
                messagebox.showwarning(
                    "No Story Files Found",
                    f"Folder '{folder.name}' contains no Princess Connect story files (.unity3d, .asset, .txt).\n\n"
                    f"Search and project scopes were left completely unchanged.",
                    parent=self
                )
                return

            ans = True
            if source_label not in ("Test", "unittest"):
                ans = messagebox.askyesno(
                    "Set Search Scope",
                    f"No story files (.unity3d, .asset, .txt) were found in '{folder.name}'.\n\n"
                    f"Do you want to set your search scope to this folder anyway?",
                    parent=self,
                    default=messagebox.NO
                )
            if ans:
                self.selected_search_folder = folder
                self.last_opened_dir = folder
                self.folder_path_var.set(str(folder))
                self.scope_var.set("folder")
                self._sync_scope_widgets()
                self._save_user_prefs(silent=True)
                self.lbl_status.config(text=f"Search scope set to folder: '{folder.name}' (no story files found to open)")
                self.show_toast(f"Search folder set to: {folder.name}")
            return

        self.last_opened_dir = folder
        if len(story_files) == 1:
            try:
                self.open_file(story_files[0])
                self.scope_var.set("current")
                self._sync_scope_widgets()
                self._save_user_prefs(silent=True)
                self.lbl_status.config(
                    text=f"Opened \"{story_files[0].name}\" from folder. Search scope set to Current File(s)."
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error(source_label, f"Could not open {story_files[0].name}: {exc}")
        else:
            ans = messagebox.askyesnocancel(
                "Open Folder Story Files",
                f"Found {len(story_files)} story file(s) in folder '{folder.name}'.\n\n"
                f"  Yes    – Open all {len(story_files)} files as editor tabs\n"
                f"  No     – Set search scope to this folder only (open nothing)\n"
                f"  Cancel – Abort: do nothing, keep current state",
                default=messagebox.YES,
            )
            if ans is True:
                if self._check_batch_safety(story_files):
                    opened = 0
                    for sf in story_files:
                        try:
                            self.open_file(sf)
                            opened += 1
                        except Exception as exc:  # noqa: BLE001
                            self.logger.error(source_label, f"Could not open {sf.name}: {exc}")
                    # When all files are opened into tabs, switch scope to Current File(s)
                    self.scope_var.set("current")
                    self._sync_scope_widgets()
                    self._save_user_prefs(silent=True)
                    self.lbl_status.config(
                        text=f"Opened {opened} file(s) into tabs. Search scope set to Current File(s)."
                    )
                else:
                    self.lbl_status.config(text=f"{source_label} cancelled by user.")
            elif ans is False:
                # "No" = Set search scope to this folder only (open nothing)
                self.selected_search_folder = folder
                self.folder_path_var.set(str(folder))
                self.scope_var.set("folder")
                self._sync_scope_widgets()
                self._save_user_prefs(silent=True)
                self.lbl_status.config(
                    text=f"Search scope set to folder: '{folder.name}' ({len(story_files)} story file(s) found). No files opened."
                )
                self.show_toast(f"Search folder set to: {folder.name}")
            else:
                # "Cancel" = Abort: do nothing, touch nothing!
                self.lbl_status.config(text=f"{source_label} cancelled. No changes made.")

    # -------------------------------------------------------------------------
    # Environment & WCAG Contrast-Safe ttk Styling (#13, #4, #7)
    # -------------------------------------------------------------------------
    def _set_project_folder(self, folder: Union[str, Path]) -> None:
        """Central setter for project_folder; replaces XUAT search roots cleanly (Rule 1)."""
        p = Path(folder)
        self.project_folder = p
        self.bepinex_project_folder = p
        xuat_dir = self._resolve_xuat_text_root(p)
        self.xuat_search_roots = [xuat_dir] if (xuat_dir and xuat_dir.exists()) else []
        if getattr(self, "_ui_ready", False) and hasattr(self, "_refresh_xuat_index_async"):
            self._refresh_xuat_index_async()

    def _resolve_xuat_text_root(self, proj_dir: Optional[Path]) -> Optional[Path]:
        """Resolve XUAT text root strictly to BepInEx\\Translation\\en\\Text (or Text)."""
        if not proj_dir:
            return None
        candidates = [
            proj_dir / "BepInEx" / "Translation" / "en" / "Text",
            proj_dir / "Translation" / "en" / "Text",
            proj_dir / "Text",
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return proj_dir if proj_dir.is_dir() else None

    def _resolve_project_search_roots(self, proj_dir: Optional[Path]) -> List[Path]:
        """
        Resolve Project Search cleanly into explicit bounded (Text, RedirectedResources) directories.
        Uses OR condition so if only Text exists, it returns [Text] without falling through to [proj_dir].
        CRITICAL INVARIANT: Strictly excludes BepInEx/plugins/ and BepInEx/config/.
        """
        if not proj_dir or not Path(proj_dir).exists():
            return []
        p = Path(proj_dir)

        # Check candidate locations for Text and RedirectedResources (OR condition per Guard 1)
        sub_bases = [
            p / "BepInEx" / "Translation" / "en",
            p / "Translation" / "en",
            p,
        ]
        for base in sub_bases:
            if base.is_dir():
                t_dir = base / "Text"
                r_dir = base / "RedirectedResources"
                roots = []
                if t_dir.is_dir():
                    roots.append(t_dir)
                if r_dir.is_dir():
                    roots.append(r_dir)
                if roots:
                    return roots

        # If base is itself Text or RedirectedResources
        if p.name.lower() in ("text", "redirectedresources") and p.is_dir():
            return [p]

        # Plain directory without BepInEx structure: return p, but never plugins or config
        if p.is_dir() and p.name.lower() not in ("plugins", "config"):
            return [p]
        return []

    def _detect_environment(self) -> None:
        """Auto-detect Priconne mod/translation project roots (BepInEx, MelonLoader, XUAT) and Notepad++."""
        candidates = [
            Path(r"C:\[Gacha]\PriconneRe-TL\src\BepInEx\Translation\en"),
            Path(r"C:\[Gacha]\PriconneRe-TL\src\BepInEx"),
        ]
        active_proj = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
        if active_proj and active_proj.exists():
            candidates.insert(0, active_proj)

        found_proj = None
        for c in candidates:
            if c.exists():
                found_proj = c
                break

        # If user has not explicitly configured project_folder, adopt the detected mod root
        if not getattr(self, "project_folder", None) and found_proj:
            self._set_project_folder(found_proj)
        elif getattr(self, "project_folder", None):
            self._set_project_folder(self.project_folder)

        # Auto-detect Notepad++ if not already set
        if not self.notepadpp_path or not Path(self.notepadpp_path).exists():
            for npp_dir in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
                candidate = Path(npp_dir) / "Notepad++" / "notepad++.exe"
                if candidate.is_file():
                    self.notepadpp_path = candidate
                    break

    def _get_backup_dir(self) -> Path:
        """Return user-configured backup folder, defaulting to SCRIPT_DIR / 'backups'."""
        if self.backup_folder:
            p = Path(self.backup_folder)
            p.mkdir(parents=True, exist_ok=True)
            return p
        default_bak = SCRIPT_DIR / "backups"
        default_bak.mkdir(parents=True, exist_ok=True)
        return default_bak

    def _apply_styles(self) -> None:
        """Apply WCAG contrast-safe theme colors & UI font sizing to all ttk widgets."""
        t = self.theme
        u_sz = int(self.prefs["ui_font_size"])
        dark_panel = self._is_dark_color(t["bg_panel"])

        # Compute WCAG optimal foregrounds for every surface & interactive state
        fg_on_dark = best_contrast_fg(t["bg_dark"], t["fg_text"], "#ffffff")
        fg_on_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_on_editor = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        accent_bg = t["misora_pink"]
        accent_hover = t["misora_pink_hover"]
        accent_press = t["misora_pink_active"]
        fg_accent = best_contrast_fg(accent_bg)
        fg_accent_hover = best_contrast_fg(accent_hover)
        fg_accent_press = best_contrast_fg(accent_press)

        btn_bg = self._shift_hex(t["bg_panel"], 10 if dark_panel else -8)
        btn_hover = self._shift_hex(t["bg_panel"], 22 if dark_panel else -16)
        btn_press = self._shift_hex(t["bg_panel"], -6 if dark_panel else -24)
        fg_btn = best_contrast_fg(btn_bg, t["fg_text"], "#ffffff")
        fg_btn_hover = best_contrast_fg(btn_hover, t["fg_text"], "#ffffff")
        fg_btn_press = best_contrast_fg(btn_press, t["fg_text"], "#ffffff")

        small_bg = t["bg_editor"]
        fg_small = best_contrast_fg(small_bg, t["fg_text"], "#ffffff")

        hl_bg = t["highlight_bg"]
        fg_hl = best_contrast_fg(hl_bg, t["misora_pink"], "#ffffff")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=t["bg_dark"], foreground=fg_on_dark, borderwidth=0)
        style.configure("TFrame", background=t["bg_dark"])
        style.configure("Panel.TFrame", background=t["bg_panel"])

        style.configure("TLabel", background=t["bg_dark"], foreground=fg_on_dark, font=("Segoe UI", u_sz))
        style.configure("Panel.TLabel", background=t["bg_panel"], foreground=fg_on_panel, font=("Segoe UI", u_sz))
        style.configure("Header.TLabel", font=("Segoe UI", u_sz + 1, "bold"), foreground=t["misora_pink"])
        style.configure("Muted.TLabel", foreground=t["fg_muted"], font=("Segoe UI", max(8, u_sz - 1)))

        # WCAG-safe Checkbox & Radiobutton clarity across Light & Dark themes (U21)
        ind_bg_unsel = t["bg_editor"]
        ind_fg_unsel = best_contrast_fg(ind_bg_unsel, t["fg_text"], "#ffffff")
        ind_bg_sel = t["misora_pink"]
        ind_fg_sel = best_contrast_fg(ind_bg_sel)
        ind_bg_dis = self._shift_hex(t["bg_panel"], 18 if dark_panel else -18)
        ind_fg_dis = _wcag_muted_fg(t["fg_muted"], ind_bg_dis, best_contrast_fg(ind_bg_dis, t["fg_text"], "#ffffff"))

        def _configure_toggle_style(
            style_name: str,
            surface_bg: str,
            fg_norm: str,
            fg_act: str,
            font_spec: Tuple[Any, ...],
        ) -> None:
            fg_dis = _wcag_muted_fg(t["fg_muted"], surface_bg, fg_norm)
            style.configure(
                style_name,
                background=surface_bg,
                foreground=fg_norm,
                font=font_spec,
                focuscolor=t["misora_pink"],
                indicatorsize=14,
                indicatormargin=(2, 2, 6, 2),
                indicatorrelief="flat",
                indicatorbackground=ind_bg_unsel,
                indicatorforeground=ind_fg_unsel,
                upperbordercolor=t["border"],
                lowerbordercolor=t["border"],
            )
            style.map(
                style_name,
                background=[("disabled", surface_bg), ("active", surface_bg), ("!active", surface_bg)],
                foreground=[("disabled", fg_dis), ("active", fg_act), ("focus", fg_act), ("!active", fg_norm)],
                indicatorbackground=[
                    ("disabled", ind_bg_dis),
                    ("selected", ind_bg_sel),
                    ("!selected", ind_bg_unsel),
                ],
                indicatorforeground=[
                    ("disabled", ind_fg_dis),
                    ("selected", ind_fg_sel),
                    ("!selected", ind_fg_unsel),
                ],
                upperbordercolor=[
                    ("selected", accent_press),
                    ("active", t["misora_pink"]),
                    ("!selected", t["border"]),
                ],
                lowerbordercolor=[
                    ("selected", accent_press),
                    ("active", t["misora_pink"]),
                    ("!selected", t["border"]),
                ],
            )

        accent_panel_fg = _ensure_contrast_fg = _ensure_wcag_fg(t["misora_pink"], t["bg_panel"], t["fg_text"], "#ffffff")
        accent_panel_hover = _ensure_wcag_fg(t["misora_pink_hover"], t["bg_panel"], t["fg_text"], "#ffffff")
        panel_hover_fg = _ensure_wcag_fg(t["misora_pink"], t["bg_panel"], t["fg_text"], "#ffffff")
        dark_hover_fg = _ensure_wcag_fg(t["misora_pink"], t["bg_dark"], t["fg_text"], "#ffffff")

        _configure_toggle_style("TCheckbutton", t["bg_dark"], fg_on_dark, dark_hover_fg, ("Segoe UI", u_sz))
        _configure_toggle_style("Panel.TCheckbutton", t["bg_panel"], fg_on_panel, panel_hover_fg, ("Segoe UI", u_sz))
        _configure_toggle_style("Accent.TCheckbutton", t["bg_panel"], accent_panel_fg, accent_panel_hover, ("Segoe UI", max(8, u_sz - 1), "bold"))
        _configure_toggle_style("TRadiobutton", t["bg_dark"], fg_on_dark, dark_hover_fg, ("Segoe UI", u_sz))
        _configure_toggle_style("Panel.TRadiobutton", t["bg_panel"], fg_on_panel, panel_hover_fg, ("Segoe UI", u_sz))

        # Primary Accent Action Button
        style.configure(
            "Pink.TButton",
            background=accent_bg,
            foreground=fg_accent,
            bordercolor=accent_press,
            darkcolor=accent_press,
            lightcolor=accent_hover,
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", u_sz, "bold"),
            padding=(10, 4),
        )
        style.map(
            "Pink.TButton",
            background=[
                ("disabled", btn_bg),
                ("pressed", accent_press),
                ("active", accent_hover),
            ],
            foreground=[
                ("disabled", t["fg_muted"]),
                ("pressed", fg_accent_press),
                ("active", fg_accent_hover),
            ],
        )

        # Distinct Box Navigation Buttons (< Prev / Next >) (#4 / U13 compact)
        style.configure(
            "Nav.TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["misora_pink"],
            darkcolor=t["border"],
            lightcolor=t["misora_pink"],
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", max(8, u_sz - 1), "bold"),
            padding=(5, 2),
        )
        style.map(
            "Nav.TButton",
            background=[
                ("disabled", t["bg_editor"]),
                ("pressed", accent_press),
                ("active", accent_bg),
            ],
            foreground=[
                ("disabled", t["fg_muted"]),
                ("pressed", fg_accent_press),
                ("active", fg_accent),
            ],
        )

        # Standard Button
        style.configure(
            "TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["border"],
            darkcolor=t["border"],
            lightcolor=btn_hover,
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", u_sz),
            padding=(7, 3),
        )
        style.map(
            "TButton",
            background=[
                ("disabled", t["bg_editor"]),
                ("pressed", btn_press),
                ("active", btn_hover),
            ],
            foreground=[
                ("disabled", t["fg_muted"]),
                ("pressed", fg_btn_press),
                ("active", fg_btn_hover),
            ],
        )

        # Search Panel Action Buttons (BUG-38 parity: identical font & padding)
        style.configure(
            "Search.TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["border"],
            darkcolor=t["border"],
            lightcolor=btn_hover,
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", u_sz),
            padding=(6, 2),
        )
        style.map(
            "Search.TButton",
            background=[
                ("disabled", t["bg_editor"]),
                ("pressed", btn_press),
                ("active", btn_hover),
            ],
            foreground=[
                ("disabled", t["fg_muted"]),
                ("active", fg_btn),
            ],
        )
        style.configure(
            "SearchPink.TButton",
            background=accent_bg,
            foreground=fg_accent,
            bordercolor=accent_press,
            darkcolor=accent_press,
            lightcolor=accent_hover,
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", u_sz),
            padding=(6, 2),
        )
        style.map(
            "SearchPink.TButton",
            background=[
                ("disabled", btn_bg),
                ("pressed", accent_press),
                ("active", accent_hover),
            ],
            foreground=[
                ("disabled", t["fg_muted"]),
                ("pressed", fg_accent_press),
                ("active", fg_accent_hover),
            ],
        )

        # Compact Utility Button
        style.configure(
            "Small.TButton",
            background=small_bg,
            foreground=fg_small,
            bordercolor=t["border"],
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", max(8, u_sz - 1)),
            padding=(6, 1),
        )
        style.map(
            "Small.TButton",
            background=[("active", btn_hover), ("pressed", btn_press)],
            foreground=[("active", fg_btn_hover), ("pressed", fg_btn_press)],
        )

        # NGUI Ribbon — Prominent Action Buttons (Color, Grad, Ruby) (#7)
        style.configure(
            "RibbonPrimary.TButton",
            background=accent_bg,
            foreground=fg_accent,
            bordercolor=accent_press,
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", max(8, u_sz - 1), "bold"),
            padding=(3, 1),
        )
        style.map(
            "RibbonPrimary.TButton",
            background=[("active", accent_hover), ("pressed", accent_press)],
            foreground=[("active", fg_accent_hover), ("pressed", fg_accent_press)],
        )

        # NGUI Ribbon — Standard Secondary Button ([-], {player}) (#7)
        style.configure(
            "Ribbon.TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["border"],
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", max(8, u_sz - 1), "bold"),
            padding=(2, 1),
        )
        style.map(
            "Ribbon.TButton",
            background=[("active", hl_bg), ("pressed", btn_press)],
            foreground=[("active", fg_hl), ("pressed", fg_btn_press)],
        )

        # NGUI Ribbon — Tiny Mini-Buttons (B, I, U, S, Sub, Sup, Undo, Redo) (#7)
        style.configure(
            "RibbonMini.TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["border"],
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", max(7, u_sz - 2), "bold"),
            padding=(1, 0),
        )
        style.map(
            "RibbonMini.TButton",
            background=[("active", hl_bg), ("pressed", btn_press)],
            foreground=[("active", fg_hl), ("pressed", fg_btn_press)],
        )

        style.configure(
            "TCombobox",
            fieldbackground=t["bg_editor"],
            background=btn_bg,
            foreground=fg_on_editor,
            arrowcolor=t["misora_pink"],
        )

        # Treeview & Treeview.Heading Styling (BUG-31 / DEP-1 FIRST)
        tree_bg = t["bg_editor"]
        tree_fg = best_contrast_fg(tree_bg, t["fg_text"], "#ffffff")
        sel_bg = t["misora_pink"]
        sel_fg = best_contrast_fg(sel_bg)
        heading_bg = btn_bg
        heading_fg = best_contrast_fg(heading_bg, t["fg_text"], "#ffffff")
        heading_hover = btn_hover
        heading_fg_hover = best_contrast_fg(heading_hover, t["fg_text"], "#ffffff")

        style.configure(
            "Treeview",
            background=tree_bg,
            fieldbackground=tree_bg,
            foreground=tree_fg,
            font=("Segoe UI", u_sz),
            rowheight=max(20, u_sz * 2),
        )
        style.map(
            "Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )

        style.configure(
            "Treeview.Heading",
            background=heading_bg,
            foreground=heading_fg,
            font=("Segoe UI", u_sz, "bold"),
            relief="raised",
            borderwidth=1,
        )
        style.map(
            "Treeview.Heading",
            background=[("active", heading_hover)],
            foreground=[("active", heading_fg_hover)],
        )

    # -------------------------------------------------------------------------
    # Menu Bar (Includes NGUI Glossary Top-Level Menu #6 & Debug Menu #14)
    # -------------------------------------------------------------------------
    def _build_menu(self) -> None:
        t = self.theme
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        accent_fg = best_contrast_fg(t["misora_pink"])

        self.var_continuous_view = tk.BooleanVar(master=self, value=False)
        self.var_preview_compiled = tk.BooleanVar(master=self, value=False)
        self.var_show_ngui_ribbon = tk.BooleanVar(master=self, value=getattr(self, "_saved_show_ngui_ribbon", False))
        self.var_show_left_panel = tk.BooleanVar(master=self, value=True)
        self._all_menus: List[tk.Menu] = []

        menubar = tk.Menu(
            self,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        self._all_menus.append(menubar)

        self.file_menu = file_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        file_menu.add_command(label="Open File...", command=self.on_open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Force Open Any File...", command=self.on_force_open_file)
        file_menu.add_command(label="Open Folder...", command=self.on_open_folder, accelerator="Ctrl+Shift+O")

        self.recent_menu = tk.Menu(file_menu, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg, postcommand=self._sync_recent_files_menu)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self._all_menus.append(self.recent_menu)

        file_menu.add_separator()
        file_menu.add_command(label="Open Project (.misora)...", command=self.on_open_project)
        file_menu.add_command(label="Save Project (.misora)...", command=self.on_save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Save & Patch Bundle", command=self.on_save, accelerator="Ctrl+S")
        file_menu.add_command(label="Reload Current File", command=self.on_reload, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Import Script (CSIF / Text)...", command=self.on_import_script, accelerator="Ctrl+Shift+I")
        file_menu.add_command(label="Import from XUAT...", command=self.on_import_from_xuat)
        file_menu.add_command(label="Export Script (CSIF)...", command=self.on_export_script, accelerator="Ctrl+Shift+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_app_exit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)
        self._all_menus.append(file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg, postcommand=self._sync_edit_menu_states)
        self.edit_menu.add_command(label="Undo", command=self.on_undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self.on_redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Previous Box", command=self.on_prev_box, accelerator="Alt+Left")
        self.edit_menu.add_command(label="Next Box", command=self.on_next_box, accelerator="Alt+Right")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Bold ([b]...[/b])", command=lambda: self.apply_ngui_wrapper("[b]", "[/b]"), accelerator="Ctrl+B")
        self.edit_menu.add_command(label="Italic ([i]...[/i])", command=lambda: self.apply_ngui_wrapper("[i]", "[/i]"), accelerator="Ctrl+I")
        self.edit_menu.add_command(label="Underline ([u]...[/u])", command=lambda: self.apply_ngui_wrapper("[u]", "[/u]"), accelerator="Ctrl+U")
        self.edit_menu.add_command(label="Wrap Selection with Ruby ([rub:...]...[/rub])", command=self.on_insert_ruby, accelerator="Ctrl+R")
        self.edit_menu.add_command(label="NGUI Color & Gradient Picker...", command=self.on_open_color_picker)
        self.edit_menu.add_command(label="Insert {playername}", command=self.on_insert_playername, accelerator="Ctrl+P")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Lock / Unlock Active Box",
            command=self.on_toggle_lock_current_box,
            accelerator="Ctrl+L",
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Copy Script Across Boxes (Triple Enter)...",
            command=self.on_copy_script_triple_enter,
            accelerator="Ctrl+Shift+C",
        )
        self.edit_menu.add_command(
            label="Paste Script Across Boxes...",
            command=self.on_paste_cross_box,
            accelerator="Ctrl+Shift+V",
        )
        menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self._all_menus.append(self.edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        view_menu.add_checkbutton(
            label="All Script View",
            variable=self.var_continuous_view,
            command=self._on_toggle_continuous_view,
            selectcolor=t["misora_pink"]
        )
        view_menu.add_checkbutton(
            label="Preview Compiled NGUI Attributes",
            variable=self.var_preview_compiled,
            command=self._on_toggle_preview_compiled,
            selectcolor=t["misora_pink"]
        )
        view_menu.add_checkbutton(
            label="Toggle NGUI Ribbon",
            variable=self.var_show_ngui_ribbon,
            command=self._on_toggle_ngui_ribbon,
            selectcolor=t["misora_pink"]
        )
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Show Left Panel",
            variable=self.var_show_left_panel,
            command=self._on_toggle_left_panel,
            selectcolor=t["misora_pink"],
        )
        view_menu.add_command(label="Toggle Customization Panel", command=lambda: self._toggle_side_drawer("customize"), accelerator="Ctrl+,")
        view_menu.add_command(label="Toggle NGUI Glossary Panel", command=lambda: self._toggle_side_drawer("glossary"), accelerator="F1")
        view_menu.add_separator()
        self.var_show_line_numbers = tk.BooleanVar(master=self, value=self.show_line_numbers)
        view_menu.add_checkbutton(
            label="Show Line Numbers (Vertical)",
            variable=self.var_show_line_numbers,
            command=self._on_toggle_line_numbers,
            selectcolor=t["misora_pink"]
        )
        self.var_show_column_ruler = tk.BooleanVar(master=self, value=self.show_column_ruler)
        view_menu.add_checkbutton(
            label="Show Column Ruler (Horizontal)",
            variable=self.var_show_column_ruler,
            command=self._on_toggle_column_ruler,
            selectcolor=t["misora_pink"]
        )
        menubar.add_cascade(label="View", menu=view_menu)
        self._all_menus.append(view_menu)

        self.tools_menu = tools_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        tools_menu.add_command(
            label="Auto Word Wrap...",
            command=self.on_open_auto_word_wrap,
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Clean / Archive XUAT...",
            command=self.on_clean_archive_xuat,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self._all_menus.append(tools_menu)

        search_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        search_menu.add_command(label="Find...", command=self.on_show_find, accelerator="Ctrl+F")
        search_menu.add_command(label="Find in Files...", command=self.on_show_find_in_files, accelerator="Ctrl+Shift+F")
        search_menu.add_command(label="Replace...", command=self.on_show_replace, accelerator="Ctrl+H")
        search_menu.add_separator()
        search_menu.add_command(label="Clear Search Results", command=self.on_clear_search)
        menubar.add_cascade(label="Search", menu=search_menu)
        self._all_menus.append(search_menu)

        cust_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        cust_menu.add_command(label="Display & Theme Settings...", command=lambda: self._toggle_side_drawer("customize"), accelerator="Ctrl+,")
        cust_menu.add_command(label="AI / LLM Translation Prompt Settings...", command=self.on_open_ai_prompt_settings)
        cust_menu.add_separator()
        cust_menu.add_command(label="Increase Dialogue Font Size", command=lambda: self._adjust_dialogue_font_size(1))
        cust_menu.add_command(label="Decrease Dialogue Font Size", command=lambda: self._adjust_dialogue_font_size(-1))
        cust_menu.add_separator()

        preset_sub = tk.Menu(cust_menu, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        for preset_name in THEME_PRESETS:
            preset_sub.add_command(
                label=preset_name,
                command=lambda pn=preset_name: self._apply_theme_preset(pn),
            )
        cust_menu.add_cascade(label="Theme Presets", menu=preset_sub)
        self._all_menus.append(preset_sub)

        cust_menu.add_separator()
        cust_menu.add_command(label="Reset Display & Colors to Default", command=self._reset_customization_defaults)
        menubar.add_cascade(label="Customize", menu=cust_menu)
        self._all_menus.append(cust_menu)

        # NGUI GLOSSARY TOP-LEVEL MENU (#6)
        glossary_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        glossary_menu.add_command(
            label="Open NGUI & Ruby Glossary Drawer",
            command=lambda: self._toggle_side_drawer("glossary"),
            accelerator="F1",
        )
        glossary_menu.add_separator()
        glossary_menu.add_command(
            label="Wrap with Ruby ([rub:...]...[/rub])",
            command=self.on_insert_ruby,
            accelerator="Ctrl+R",
        )
        glossary_menu.add_command(
            label="Color & Gradient Picker...",
            command=self.on_open_color_picker,
        )
        glossary_menu.add_command(
            label="Insert {playername}",
            command=self.on_insert_playername,
            accelerator="Ctrl+P",
        )
        glossary_menu.add_command(
            label="Reset Color Tag ([-])",
            command=lambda: self.apply_ngui_wrapper("[-]", ""),
        )
        menubar.add_cascade(label="NGUI Glossary", menu=glossary_menu)
        self._all_menus.append(glossary_menu)

        # FOLDERS & FILES MENU (#4B)
        folders_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        folders_menu.add_command(
            label="Configure Paths & Backups...",
            command=self.on_open_paths_dialog,
        )
        folders_menu.add_separator()
        folders_menu.add_command(
            label="Open Backups Folder",
            command=self.on_open_backups_folder,
        )
        folders_menu.add_command(
            label="Open Project / Mod Root Folder",
            command=self.on_open_project_folder,
        )
        folders_menu.add_command(
            label="Open Text Translation Folder (Text / XUAT)",
            command=self.on_open_xuat_text_folder,
        )
        folders_menu.add_command(
            label="Open Redirected Resources Folder",
            command=self.on_open_redirected_resources_folder,
        )
        folders_menu.add_command(
            label="Open Selected Search Folder",
            command=self.on_open_selected_search_folder,
        )
        folders_menu.add_command(
            label="Open Misora Program Folder",
            command=self.on_open_program_folder,
        )
        folders_menu.add_separator()
        folders_menu.add_command(
            label="Register .unity3d Association (Current User)...",
            command=self.on_register_unity3d_association,
        )
        menubar.add_cascade(label="Folders & Files", menu=folders_menu)
        self._all_menus.append(folders_menu)

        # TRANSLATOR MENU
        self.translator_menu = translator_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        translator_menu.add_command(
            label="Translator Assistant...",
            command=self.on_open_translator_assistant,
            accelerator="Ctrl+T",
        )
        translator_menu.add_command(
            label="Translate Current Box",
            command=self.on_translate_current_box,
            accelerator="F8",
        )
        translator_menu.add_command(
            label="Batch Translate Story...",
            command=self.on_batch_translate,
        )
        self.mtl_engines_menu = tk.Menu(
            translator_menu,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        for eng in self._MTL_DRAWER_ENGINE_ORDER:
            self.mtl_engines_menu.add_checkbutton(
                label=eng,
                variable=self._mtl_drawer_engine_vars[eng],
                command=lambda e=eng: self._on_mtl_drawer_engine_toggled(e),
                selectcolor=t["misora_pink"],
            )
        translator_menu.add_cascade(label="Enabled Engines", menu=self.mtl_engines_menu)
        self._all_menus.append(self.mtl_engines_menu)
        translator_menu.add_separator()
        translator_menu.add_command(
            label="Configure MTL Sources & Keys...",
            command=self.on_open_mtl_settings,
        )
        translator_menu.add_command(
            label="Configure AI / LLM Prompt Header...",
            command=self.on_open_ai_prompt_settings,
        )
        translator_menu.add_separator()
        translator_menu.add_command(
            label="Copy AI Translation Prompt",
            command=self.on_copy_ai_prompt,
            accelerator="Ctrl+Shift+T",
        )
        translator_menu.add_command(
            label="Apply Translation from Clipboard...",
            command=self.on_apply_translation_clipboard,
        )
        translator_menu.add_separator()
        translator_menu.add_command(
            label="Clear Dialogue (Keep Skeleton Only)...",
            command=self.on_clear_dialogue_skeleton,
        )
        menubar.add_cascade(label="Translator", menu=translator_menu)
        self._all_menus.append(translator_menu)

        # DATAMINE MENU (#4C)
        datamine_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        datamine_menu.add_command(
            label="Launch Datamine Tool",
            command=self.on_launch_datamine,
            accelerator="F9",
        )
        datamine_menu.add_separator()
        datamine_menu.add_command(
            label="Select Datamine Executable / Script...",
            command=self.on_select_datamine_exe,
        )
        datamine_menu.add_command(
            label="Open Datamine Program Folder",
            command=self.on_open_datamine_folder,
        )
        menubar.add_cascade(label="Datamine", menu=datamine_menu)
        self._all_menus.append(datamine_menu)

        # DEBUG MENU (#14 & #4D)
        self.debug_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
            postcommand=self._sync_debug_menu_states,
        )

        cat_sub = tk.Menu(self.debug_menu, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        for cat in LOG_CATEGORIES:
            if cat == ALWAYS_ON_CATEGORY:
                cat_sub.add_checkbutton(
                    label=f"{cat} (Always On)",
                    variable=self.var_log_categories[cat],
                    state="disabled",
                    selectcolor=t["misora_pink"],
                )
            else:
                cat_sub.add_checkbutton(
                    label=cat,
                    variable=self.var_log_categories[cat],
                    command=self._on_debug_settings_changed,
                    selectcolor=t["misora_pink"],
                )
        self.debug_menu.add_cascade(label="Log Categories", menu=cat_sub)
        self._all_menus.append(cat_sub)

        lvl_sub = tk.Menu(self.debug_menu, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        for lvl_name in LOG_LEVELS:
            lvl_sub.add_radiobutton(
                label=lvl_name,
                variable=self.var_log_level,
                value=lvl_name,
                command=self._on_debug_settings_changed,
                selectcolor=t["misora_pink"],
            )
        self.debug_menu.add_cascade(label="Log Level", menu=lvl_sub)
        self._all_menus.append(lvl_sub)

        # External Editor submenu (#4D)
        self._ext_editor_menu = tk.Menu(
            self.debug_menu,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
            postcommand=self._sync_external_editor_menu,
        )
        self._sync_external_editor_menu()
        self.debug_menu.add_cascade(label="External Editor", menu=self._ext_editor_menu)
        self._all_menus.append(self._ext_editor_menu)

        self.debug_menu.add_separator()
        self.debug_menu.add_checkbutton(
            label="Log to File",
            variable=self.var_log_to_file,
            command=self._on_debug_settings_changed,
            selectcolor=t["misora_pink"],
        )
        self._idx_open_log = self.debug_menu.index("end") + 1
        self.debug_menu.add_command(label="Open Log File", command=self._on_open_debug_log_file)
        self._idx_clear_log = self.debug_menu.index("end") + 1
        self.debug_menu.add_command(label="Clear Log File", command=self._on_clear_debug_log_file)
        self.debug_menu.add_separator()
        self.debug_menu.add_command(label="Drag & Drop Safety Settings...", command=self._on_dnd_settings_dialog)

        self.debug_safety_menu = tk.Menu(
            self.debug_menu,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=accent_fg,
        )
        self.debug_safety_menu.add_checkbutton(
            label="Auto-backup XUAT files before cleanup edits",
            variable=self.var_xuat_safety_backup,
            command=self._on_toggle_xuat_safety_backup,
            selectcolor=t["misora_pink"],
        )
        self.debug_safety_menu.add_command(
            label="XUAT Cleanup & Archive Settings...",
            command=self._on_xuat_cleanup_settings_dialog,
        )
        self.debug_menu.add_cascade(label="Safety", menu=self.debug_safety_menu)
        self._all_menus.append(self.debug_safety_menu)

        menubar.add_cascade(label="Debug", menu=self.debug_menu)
        self._all_menus.append(self.debug_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        help_menu.add_command(label="NGUI & Ruby Glossary", command=lambda: self._open_side_drawer("glossary"), accelerator="F1")
        help_menu.add_separator()
        help_menu.add_command(label="About Misora: Story Editor", command=self.on_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self._all_menus.append(help_menu)

        self.config(menu=menubar)

    # -------------------------------------------------------------------------
    # Search & Replace Bar (Collapsible Notepad++ Style)
    # -------------------------------------------------------------------------
    def _build_search_bar(self) -> None:
        t = self.theme
        self.search_frame = self._tag_role(
            tk.Frame(self, bg=t["bg_panel"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "panel_box"
        )
        self.search_frame.pack(fill="x", padx=8, pady=(6, 4))
        # Start collapsed — Ctrl+F will show it; build it packed then immediately hide
        self.search_frame.pack_forget()
        self._search_bar_visible = False

        self.search_grid = self._tag_role(tk.Frame(self.search_frame, bg=t["bg_panel"]), "panel")
        self.search_grid.pack(fill="x", padx=8, pady=4)

        self.search_grid.columnconfigure(0, weight=0)
        self.search_grid.columnconfigure(1, weight=1)
        self.search_grid.columnconfigure(2, weight=0, uniform="search_btn")
        self.search_grid.columnconfigure(3, weight=0, uniform="search_btn")
        self.search_grid.columnconfigure(4, weight=0)
        self.search_grid.rowconfigure(0, uniform="search_row", pad=2)
        self.search_grid.rowconfigure(1, uniform="search_row", pad=2)

        # Row 0: Find
        self.lbl_find = self._tag_role(
            tk.Label(self.search_grid, text="Find:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], width=7, anchor="w"),
            "label_accent"
        )
        self.lbl_find.grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")

        self.search_var = tk.StringVar(master=self)
        self.search_entry = self._tag_role(
            tk.Entry(
                self.search_grid,
                textvariable=self.search_var,
                font=("Consolas", 10),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                bd=1,
                relief="solid",
                highlightthickness=1,
                highlightcolor=t["misora_pink"]
            ),
            "entry_editor"
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 8), pady=2, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self.on_start_search())
        self.search_entry.bind("<Escape>", lambda e: self._hide_search_bar())

        self.ico_find = self.get_icon("search", (14, 14))
        self.ico_cancel = self.get_icon("cancel", (14, 14))
        self.btn_find = ttk.Button(self.search_grid, text=" Find in Files", image=self.ico_find, compound="left", style="SearchPink.TButton", command=self.on_start_search, width=14)
        self.btn_find.grid(row=0, column=2, padx=4, pady=2, sticky="nsew")

        self.btn_cancel = ttk.Button(self.search_grid, text=" Cancel", image=self.ico_cancel, compound="left", style="Search.TButton", command=self.on_cancel_search, state="disabled", width=14)
        self.btn_cancel.grid(row=0, column=3, padx=4, pady=2, sticky="nsew")

        self.ico_close = self.get_icon("close", (12, 12))
        self.btn_close_search = ttk.Button(self.search_grid, text="✕", image=self.ico_close, style="Small.TButton", command=self._hide_search_bar, width=3)
        self.btn_close_search.grid(row=0, column=4, padx=(4, 0), pady=2, sticky="e")
        create_tooltip(self.btn_close_search, "Close Search Bar (Esc)")

        # Row 1: Replace (hidden initially until on_show_replace)
        self.lbl_replace = self._tag_role(
            tk.Label(self.search_grid, text="Replace:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["accent_blue"], width=7, anchor="w"),
            "label_voice"
        )

        self.replace_var = tk.StringVar(master=self)
        self.replace_entry = self._tag_role(
            tk.Entry(
                self.search_grid,
                textvariable=self.replace_var,
                font=("Consolas", 10),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                bd=1,
                relief="solid",
                highlightthickness=1,
                highlightcolor=t["accent_blue"]
            ),
            "entry_editor"
        )
        self.replace_entry.bind("<Escape>", lambda e: self._hide_search_bar())
        self.replace_entry.bind("<Return>", lambda e: self.on_replace_next())

        self.ico_replace = self.get_icon("replace", (14, 14))
        self.ico_replace_all = self.get_icon("replace_all", (14, 14))
        self.btn_replace = ttk.Button(self.search_grid, text=" Replace", image=self.ico_replace, compound="left", style="Search.TButton", command=self.on_replace_next, width=14)
        self.btn_replace_all = ttk.Button(self.search_grid, text=" Replace All", image=self.ico_replace_all, compound="left", style="Search.TButton", command=self.on_replace_all, width=14)

        self.replace_spacer = self._tag_role(tk.Frame(self.search_grid, bg=t["bg_panel"], width=28, height=1), "panel")
        self.row_replace = _ReplaceRowProxy(self)
        self._replace_row_visible = False
        self._hide_replace_row()

        row2 = self._tag_role(tk.Frame(self.search_frame, bg=t["bg_panel"]), "panel")
        row2.pack(fill="x", padx=8, pady=(0, 4))

        self.var_case = tk.BooleanVar(master=self, value=False)
        self.var_regex = tk.BooleanVar(master=self, value=False)
        self.var_ignore_ws = tk.BooleanVar(master=self, value=True)
        self.var_inc_bundles = tk.BooleanVar(master=self, value=True)
        self.var_inc_text = tk.BooleanVar(master=self, value=True)

        cb_case = ttk.Checkbutton(row2, text="Match Case", variable=self.var_case, style="Panel.TCheckbutton")
        cb_case.pack(side="left", padx=4)

        cb_rx = ttk.Checkbutton(row2, text="Regex", variable=self.var_regex, style="Panel.TCheckbutton")
        cb_rx.pack(side="left", padx=4)

        cb_ws = ttk.Checkbutton(row2, text="Ignore Whitespace & {playername}", variable=self.var_ignore_ws, style="Panel.TCheckbutton")
        cb_ws.pack(side="left", padx=4)

        self._tag_role(tk.Label(row2, text="|", bg=t["bg_panel"], fg=t["border"]), "label_sep").pack(side="left", padx=6)

        self._tag_role(tk.Label(row2, text="Scope:", bg=t["bg_panel"], fg=t["fg_muted"]), "label_muted").pack(side="left", padx=(0, 4))
        self.scope_var = tk.StringVar(master=self, value="project")

        self.rb_proj = ttk.Radiobutton(row2, text="Project", variable=self.scope_var, value="project", style="Panel.TRadiobutton", command=self._sync_scope_widgets)
        self.rb_proj.pack(side="left", padx=2)

        self.rb_folder = ttk.Radiobutton(row2, text="Folder", variable=self.scope_var, value="folder", style="Panel.TRadiobutton", command=self._sync_scope_widgets)
        self.rb_folder.pack(side="left", padx=2)

        self.rb_cur = ttk.Radiobutton(row2, text="Current File(s)", variable=self.scope_var, value="current", style="Panel.TRadiobutton", command=self._sync_scope_widgets)
        self.rb_cur.pack(side="left", padx=2)

        self._tag_role(tk.Label(row2, text="|", bg=t["bg_panel"], fg=t["border"]), "label_sep").pack(side="left", padx=6)
        cb_bdl = ttk.Checkbutton(row2, text=".unity3d", variable=self.var_inc_bundles, style="Panel.TCheckbutton")
        cb_bdl.pack(side="left", padx=2)
        cb_txt = ttk.Checkbutton(row2, text=".txt", variable=self.var_inc_text, style="Panel.TCheckbutton")
        cb_txt.pack(side="left", padx=2)

        self._tag_role(tk.Label(row2, text="|", bg=t["bg_panel"], fg=t["border"]), "label_sep").pack(side="left", padx=6)

        # Browse [...] button on LEFT of entry
        self.btn_browse_search_folder = ttk.Button(row2, text="...", style="Small.TButton", command=self.on_browse_scope_path, width=3)
        self.btn_browse_search_folder.pack(side="left", padx=(0, 2))

        # Directory path entry on RIGHT of [...], expands to fill remaining space
        self.folder_path_var = tk.StringVar(master=self, value="")
        self.folder_path_var.trace_add("write", lambda *args: self._on_folder_path_var_trace())
        self.folder_path_entry = self._tag_role(
            tk.Entry(
                row2,
                textvariable=self.folder_path_var,
                font=("Segoe UI", 9),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                bd=1,
                relief="solid",
            ),
            "entry_editor"
        )
        self.folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.folder_path_entry.bind("<Return>", lambda e: self.on_start_search())
        self.folder_path_entry.bind("<FocusOut>", lambda e: self._save_user_prefs(silent=True))

        self.progress_bar = ttk.Progressbar(self.search_frame, mode="determinate")
        self.progress_bar.pack(fill="x", padx=8, pady=(0, 2))
        self.progress_bar.pack_forget()

        # Initialize scope widgets with project path
        self._sync_scope_widgets()

    def _show_replace_row(self) -> None:
        """Show Replace row in search bar 5-column grid (BUG-38)."""
        if hasattr(self, "lbl_replace"):
            self.lbl_replace.grid(row=1, column=0, padx=(0, 6), pady=2, sticky="w")
            self.replace_entry.grid(row=1, column=1, padx=(0, 8), pady=2, sticky="ew")
            self.btn_replace.grid(row=1, column=2, padx=4, pady=2, sticky="nsew")
            self.btn_replace_all.grid(row=1, column=3, padx=4, pady=2, sticky="nsew")
            if hasattr(self, "replace_spacer"):
                self.replace_spacer.grid(row=1, column=4, padx=(4, 0), pady=2, sticky="e")
        self._replace_row_visible = True

    def _hide_replace_row(self) -> None:
        """Hide Replace row in search bar 5-column grid (BUG-38)."""
        if hasattr(self, "lbl_replace"):
            self.lbl_replace.grid_remove()
            self.replace_entry.grid_remove()
            self.btn_replace.grid_remove()
            self.btn_replace_all.grid_remove()
            if hasattr(self, "replace_spacer"):
                self.replace_spacer.grid_remove()
        self._replace_row_visible = False

    # -------------------------------------------------------------------------
    # Main Workspace (#4 Distinct Nav Buttons, #5/#6 Clean Header, #7 Inline Ribbon)
    # -------------------------------------------------------------------------
    def _build_main_panels(self) -> None:
        t = self.theme
        d_fam = self.prefs["dialogue_font_family"]
        d_sz = int(self.prefs["dialogue_font_size"])
        r_sz = int(self.prefs["raw_font_size"])
        u_sz = int(self.prefs["ui_font_size"])

        self.h_paned = self._tag_role(
            tk.PanedWindow(
                self,
                orient=tk.HORIZONTAL,
                bg=t["border"],
                sashwidth=6,
                sashrelief="flat",
                opaqueresize=False
            ),
            "sash"
        )
        self.h_paned.pack(fill="both", expand=True, padx=8, pady=4)

        # LEFT PANEL: Upgraded Dual-Tab Dock (Search Results & Opened Files Cache #3B)
        self.left_frame = self._tag_role(tk.Frame(self.h_paned, bg=t["bg_panel"]), "panel")
        self.h_paned.add(self.left_frame, minsize=160, width=self._left_dock_width, stretch="never")

        # Dock Tab Switcher Bar
        self.dock_tab_bar = self._tag_role(tk.Frame(self.left_frame, bg=t["bg_panel"]), "panel")
        self.dock_tab_bar.pack(fill="x", padx=4, pady=(4, 2))

        self.btn_tab_search = tk.Button(
            self.dock_tab_bar,
            text="Search Results",
            font=("Segoe UI", max(8, u_sz - 1), "bold"),
            relief="flat",
            bd=1,
            cursor="hand2",
            command=lambda: self._switch_dock_tab("search"),
        )
        self.btn_tab_search.pack(side="left", padx=(2, 2))
        self.btn_tab_search.bind("<Double-Button-1>", lambda _e: self.on_show_find())

        self.btn_tab_files = tk.Button(
            self.dock_tab_bar,
            text="Opened Files",
            font=("Segoe UI", max(8, u_sz - 1), "bold"),
            relief="flat",
            bd=1,
            cursor="hand2",
            command=lambda: self._switch_dock_tab("files"),
        )
        self.btn_tab_files.pack(side="left", padx=(2, 2))
        self.btn_tab_files.bind("<Double-Button-1>", lambda e: self.on_open_file())

        self.btn_dock_pin = ttk.Button(
            self.dock_tab_bar,
            text="◀",
            style="Small.TButton",
            command=self._toggle_dock_collapse,
            width=2,
        )
        self.btn_dock_pin.pack(side="right", padx=(2, 2))
        self._dock_pin_tooltip = create_tooltip(self.btn_dock_pin, "Hide Left Panel")

        # --- TAB 1: Search Results ---
        self.tab_search_frame = self._tag_role(tk.Frame(self.left_frame, bg=t["bg_panel"]), "panel")

        left_header = self._tag_role(tk.Frame(self.tab_search_frame, bg=t["bg_panel"]), "panel")
        left_header.pack(fill="x", padx=6, pady=(4, 4))
        self.lbl_results_title = self._tag_role(
            tk.Label(
                left_header,
                text="Search Results (0 matches)",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["misora_pink"],
                anchor="w"
            ),
            "label_accent"
        )
        self.lbl_results_title.pack(side="left", fill="x", expand=True)

        self.btn_clear_res = ttk.Button(left_header, text="Clear", style="Small.TButton", command=self.on_clear_search)
        self.btn_clear_res.pack(side="right")
        create_tooltip(self.btn_clear_res, "Clear Search Results")

        self.tree_container = self._tag_role(tk.Frame(self.tab_search_frame, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        self.tree_container.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self.tree_container.pack_propagate(False)

        res_scroll_y = tk.Scrollbar(self.tree_container, orient="vertical")
        res_scroll_y.pack(side="right", fill="y")
        res_scroll_x = tk.Scrollbar(self.tree_container, orient="horizontal")
        res_scroll_x.pack(side="bottom", fill="x")

        self.txt_results = tk.Text(
            self.tree_container,
            wrap="none",
            font=("Segoe UI", u_sz),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertwidth=0,
            cursor="arrow",
            padx=6,
            pady=4,
            bd=0,
            relief="flat",
            exportselection=False,
            state="disabled",
            yscrollcommand=res_scroll_y.set,
            xscrollcommand=res_scroll_x.set,
        )
        self.txt_results.pack(side="left", fill="both", expand=True)
        res_scroll_y.config(command=self.txt_results.yview)
        res_scroll_x.config(command=self.txt_results.xview)

        self.txt_results.tag_configure(
            "file_header",
            font=("Segoe UI", u_sz, "bold"),
            foreground=t["misora_pink"],
            spacing1=4,
            spacing3=2,
        )
        self.txt_results.tag_configure(
            "box_badge",
            font=("Consolas", max(8, u_sz - 1), "bold"),
            foreground=t["accent_blue"],
        )
        self.txt_results.tag_configure(
            "speaker_tag",
            font=("Segoe UI", u_sz, "bold"),
            foreground=t["fg_text"],
        )
        self.txt_results.tag_configure(
            "selected_row",
            background=t["highlight_bg"],
        )
        self.txt_results.tag_configure(
            "match_hl",
            background=t["misora_pink"],
            foreground=best_contrast_fg(t["misora_pink"]),
            font=("Segoe UI", u_sz, "bold"),
        )
        self.txt_results.tag_raise("match_hl")

        self.txt_results.bind("<Button-1>", self._on_results_click)
        self.txt_results.bind("<Button-3>", self._on_results_right_click)
        self.txt_results.bind("<Up>", lambda e: self._on_results_step(-1))
        self.txt_results.bind("<Down>", lambda e: self._on_results_step(1))

        # --- TAB 2: Opened Files Cache ---
        self.tab_files_frame = self._tag_role(tk.Frame(self.left_frame, bg=t["bg_panel"]), "panel")

        files_header = self._tag_role(tk.Frame(self.tab_files_frame, bg=t["bg_panel"]), "panel")
        files_header.pack(fill="x", padx=6, pady=(4, 4))
        self.lbl_files_title = self._tag_role(
            tk.Label(
                files_header,
                text="Opened Files (0)",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["misora_pink"],
                anchor="w"
            ),
            "label_accent"
        )
        self.lbl_files_title.pack(side="left", fill="x", expand=True)

        self.ico_folder = self.get_icon("folder", (13, 13))
        btn_open_more = ttk.Button(files_header, text=" Open...", image=self.ico_folder, compound="left", style="Small.TButton", command=self.on_open_file)
        btn_open_more.pack(side="right")

        self.files_container = self._tag_role(tk.Frame(self.tab_files_frame, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        self.files_container.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self.files_container.pack_propagate(False)

        files_scroll_y = tk.Scrollbar(self.files_container, orient="vertical")
        files_scroll_y.pack(side="right", fill="y")
        files_scroll_x = tk.Scrollbar(self.files_container, orient="horizontal")
        files_scroll_x.pack(side="bottom", fill="x")

        self.txt_opened_files = tk.Text(
            self.files_container,
            wrap="none",
            font=("Segoe UI", u_sz),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertwidth=0,
            cursor="arrow",
            padx=6,
            pady=4,
            bd=0,
            relief="flat",
            exportselection=False,
            state="disabled",
            yscrollcommand=files_scroll_y.set,
            xscrollcommand=files_scroll_x.set,
        )
        self.txt_opened_files.pack(side="left", fill="both", expand=True)
        files_scroll_y.config(command=self.txt_opened_files.yview)
        files_scroll_x.config(command=self.txt_opened_files.xview)

        self.txt_opened_files.tag_configure("file_active", font=("Segoe UI", u_sz, "bold"), foreground=t["misora_pink"], background=t["highlight_bg"])
        self.txt_opened_files.tag_configure("file_dirty", font=("Segoe UI", u_sz, "bold"), foreground=t["accent_yellow"])
        self.txt_opened_files.tag_configure("file_normal", font=("Segoe UI", u_sz), foreground=t["fg_text"])
        self.txt_opened_files.tag_configure("file_dim", font=("Segoe UI", max(8, u_sz - 1)), foreground=t["fg_muted"])
        self.txt_opened_files.tag_configure("file_close", font=("Consolas", max(8, u_sz - 1), "bold"), foreground=t["misora_pink"])

        self.txt_opened_files.bind("<Button-1>", self._on_opened_files_click)
        self.txt_opened_files.bind("<Button-3>", self._on_opened_files_right_click)

        # Show initial dock tab
        self._switch_dock_tab(self._left_dock_tab)

        # CENTER PANEL: Dual-View Editor (Vertical Splitter)
        right_frame = self._tag_role(tk.Frame(self.h_paned, bg=t["bg_panel"]), "panel")
        self.right_frame = right_frame
        self.h_paned.add(right_frame, minsize=420, stretch="always")

        self.btn_reopen_left = ttk.Button(
            right_frame,
            text="▶",
            style="Small.TButton",
            width=2,
            command=self._toggle_dock_collapse,
        )
        create_tooltip(self.btn_reopen_left, "Show Left Panel")

        self.v_paned = self._tag_role(
            tk.PanedWindow(
                right_frame,
                orient=tk.VERTICAL,
                bg=t["border"],
                sashwidth=6,
                sashrelief="flat",
                opaqueresize=True
            ),
            "sash"
        )
        self.v_paned.pack(side="left", fill="both", expand=True)

        # TOP VIEW: Game Display View (Page-by-Page OR Continuous Dialog Stream)
        top_view = self._tag_role(tk.Frame(self.v_paned, bg=t["bg_panel"]), "panel")
        self.top_view = top_view
        self.v_paned.add(top_view, minsize=140, height=400, stretch="always")

        gd_header = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        gd_header.pack(fill="x", padx=6, pady=(4, 2))

        # Row 1 Left: Borderless Lock immediately before 'Dialogue' (U22)
        self.btn_lock_box = tk.Button(
            gd_header,
            text="🔓",
            font=("Segoe UI", max(8, u_sz - 1)),
            bg=t["bg_panel"],
            fg=best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff"),
            activebackground=t["highlight_bg"],
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
            command=self.on_toggle_lock_current_box,
            padx=2,
            pady=0,
        )
        self.btn_lock_box.pack(side="left", padx=(0, 3))
        create_tooltip(self.btn_lock_box, "Translation Lock (Ctrl+L) — Protect box from batch/paste/replace")

        self.lbl_gd_title = self._tag_role(
            tk.Label(
                gd_header,
                text="Dialogue",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["misora_pink"]
            ),
            "label_accent"
        )
        self.lbl_gd_title.pack(side="left")

        self.var_dialogue_box_sel = tk.BooleanVar(master=self, value=False)
        self.cb_dialogue_select = self._tag_role(
            tk.Checkbutton(
                gd_header,
                text="Select Box",
                variable=self.var_dialogue_box_sel,
                command=self._on_dialogue_box_sel_toggle,
                font=("Segoe UI", max(8, u_sz - 2)),
                bg=t["bg_panel"],
                fg=t["fg_text"],
                activebackground=t["bg_panel"],
                selectcolor=t["bg_editor"],
                bd=0,
                cursor="hand2",
            ),
            "check_panel"
        )

        # Row 1 Right (packed right-to-left): [VIEW group] [MTL] [AI] [Prev] [Next] [Overflow] [Box: N / M]
        self.lbl_box_counter = self._tag_role(
            tk.Label(gd_header, text="Box: 0 / 0", font=("Segoe UI", u_sz), bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        )
        self.lbl_box_counter.pack(side="right", padx=(4, 0))

        self.lbl_char_overflow = tk.Label(
            gd_header,
            text=f"0/{DIALOGUE_MAX_DIGITS}d · 1/{DIALOGUE_MAX_LINES}L",
            font=("Segoe UI", max(8, u_sz - 1)),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
        )
        self.lbl_char_overflow.pack(side="right", padx=(4, 2))
        create_tooltip(
            self.lbl_char_overflow,
            "Native 50 x 3 dialogue rule: <= 50 digit-widths without linebreak AND < 3 linebreaks (<= 3 lines).\n"
            "Measured using the active editor font as an estimate of the in-game font (NGUI tags excluded)."
        )

        self.ico_next = self.get_icon("nav_next", (14, 14))
        self.btn_next = ttk.Button(gd_header, text="Next ", image=self.ico_next, compound="right", style="Nav.TButton", command=self.on_next_box)
        self.btn_next.pack(side="right", padx=(1, 0))
        create_tooltip(self.btn_next, "Next Dialogue Box (Alt+Right / Alt+Down)")

        self.ico_prev = self.get_icon("nav_prev", (14, 14))
        self.btn_prev = ttk.Button(gd_header, text=" Prev", image=self.ico_prev, compound="left", style="Nav.TButton", command=self.on_prev_box)
        self.btn_prev.pack(side="right", padx=(2, 1))
        create_tooltip(self.btn_prev, "Previous Dialogue Box (Alt+Left / Alt+Up)")

        self.ico_ai = self.get_icon("ai", (16, 16))
        self.btn_ai_prompt = ttk.Button(
            gd_header,
            text="AI Prompt",
            image=self.ico_ai,
            compound="none" if self.ico_ai else "left",
            style="Small.TButton",
            command=self.on_copy_ai_prompt,
        )
        self.btn_ai_prompt.pack(side="right", padx=(2, 2))
        create_tooltip(self.btn_ai_prompt, "Copy AI Translation Prompt (Ctrl+Shift+T)")

        self.ico_mtl = self.get_icon("mtl", (16, 16))
        self.btn_translate = ttk.Button(
            gd_header,
            text="MTL",
            image=self.ico_mtl,
            compound="none" if self.ico_mtl else "left",
            style="Small.TButton",
            command=self.on_open_translator_assistant,
        )
        self.btn_translate.pack(side="right", padx=(2, 2))
        create_tooltip(self.btn_translate, "Toggle MTL Drawer (Ctrl+T)")

        # Unified VIEW Group (Select Box, All Script, Preview) in Row 1 left of MTL/AI (U11)
        self.view_group = self._tag_role(
            tk.Frame(gd_header, bg=t["bg_editor"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "ribbon"
        )
        self.view_group.pack(side="right", padx=(2, 3))

        self.ico_sel_box = self.get_icon("box", (14, 14))
        self.cb_sel_box = self._tag_role(
            tk.Checkbutton(
                self.view_group,
                text=" Select Box",
                image=self.ico_sel_box,
                compound="left" if self.ico_sel_box else "none",
                variable=self.var_select_box_mode,
                command=self._on_toggle_select_box_mode,
                font=("Segoe UI", max(8, u_sz - 2), "bold"),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                selectcolor=t["bg_panel"],
                activebackground=t["bg_editor"],
                activeforeground=t["misora_pink"],
                padx=1,
                pady=0,
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_sel_box.pack(side="left", padx=1, pady=0)
        create_tooltip(self.cb_sel_box, "Toggle Multi-Box Selection Mode")

        self.ico_all_script = self.get_icon("all_script", (14, 14))
        self.cb_cont = self._tag_role(
            tk.Checkbutton(
                self.view_group,
                text=" All Script",
                image=self.ico_all_script,
                compound="left" if self.ico_all_script else "none",
                variable=self.var_continuous_view,
                command=self._on_toggle_continuous_view,
                font=("Segoe UI", max(8, u_sz - 2), "bold"),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                selectcolor=t["bg_panel"],
                activebackground=t["bg_editor"],
                activeforeground=t["misora_pink"],
                padx=1,
                pady=0,
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_cont.pack(side="left", padx=1, pady=0)
        create_tooltip(self.cb_cont, "Toggle All Script / Continuous Stream View")

        self.ico_preview = self.get_icon("preview", (14, 14))
        self.cb_compiled = self._tag_role(
            tk.Checkbutton(
                self.view_group,
                text=" Preview",
                image=self.ico_preview,
                compound="left" if self.ico_preview else "none",
                variable=self.var_preview_compiled,
                command=self._on_toggle_preview_compiled,
                font=("Segoe UI", max(8, u_sz - 2), "bold"),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                selectcolor=t["bg_panel"],
                activebackground=t["bg_editor"],
                activeforeground=t["misora_pink"],
                padx=1,
                pady=0,
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_compiled.pack(side="left", padx=1, pady=0)
        create_tooltip(self.cb_compiled, "Toggle Compiled Attribute Preview (read-only)")

        # Row 2: Speaker Controls (Left) + Edit Group Toolbar (Right) (U09, U10, U12, 4.2)
        self.speaker_view_row = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        self.speaker_view_row.pack(fill="x", padx=6, pady=(2, 4))

        self._tag_role(
            tk.Label(self.speaker_view_row, text="Speaker:", bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        ).pack(side="left", padx=(0, 4))

        self.speaker_var = tk.StringVar(master=self)
        self.entry_speaker = self._tag_role(
            tk.Entry(
                self.speaker_view_row,
                textvariable=self.speaker_var,
                font=(d_fam, max(9, d_sz - 1), "bold"),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                selectbackground=t["highlight_bg"],
                selectforeground=t["misora_pink"],
                bd=1,
                relief="solid",
                width=13
            ),
            "entry_speaker"
        )
        self.entry_speaker.pack(side="left")
        self.entry_speaker.bind("<FocusIn>", lambda e: self._on_speaker_focus_in())
        self.entry_speaker.bind("<Button-1>", lambda e: self.after_idle(self._on_speaker_entry_clicked))
        self.entry_speaker.bind("<KeyRelease>", self._on_speaker_key_release)
        self.entry_speaker.bind("<Down>", self._on_speaker_nav_down)
        self.entry_speaker.bind("<Up>", self._on_speaker_nav_up)
        self.entry_speaker.bind("<Return>", self._on_speaker_enter)
        self.entry_speaker.bind("<KP_Enter>", self._on_speaker_enter)
        self.entry_speaker.bind("<Escape>", self._on_speaker_escape)
        self.entry_speaker.bind("<FocusOut>", self._on_speaker_focus_out)
        self.entry_speaker.bind("<<Cut>>", lambda e: self.after_idle(self._on_speaker_virtual_edit))
        self.entry_speaker.bind("<<Paste>>", lambda e: self.after_idle(self._on_speaker_virtual_edit))

        self.btn_speaker_dropdown = ttk.Button(
            self.speaker_view_row,
            text="▼",
            style="Small.TButton",
            width=2,
            command=self._on_speaker_dropdown_clicked,
        )
        self.btn_speaker_dropdown.pack(side="left", padx=(2, 2))
        create_tooltip(self.btn_speaker_dropdown, "Jump to Speaker Box (click again to cycle next)")

        self.ico_pin = self.get_icon("pin", (16, 16))
        self.btn_pin_speaker = tk.Button(
            self.speaker_view_row,
            text="📌",
            image=self.ico_pin,
            fg=t["fg_text"],
            bg=t["bg_panel"],
            activebackground=t["highlight_bg"],
            activeforeground=t["fg_text"],
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self._on_toggle_pin_speaker,
        )
        self.btn_pin_speaker.pack(side="left", padx=(1, 4))
        create_tooltip(self.btn_pin_speaker, "Pin Speaker — Next/Prev jumps to same speaker; New Box prefills pinned speaker")

        dark_p = self._is_dark_color(t["bg_panel"])
        btn_bg = self._shift_hex(t["bg_panel"], 10 if dark_p else -8)
        btn_hover = self._shift_hex(t["bg_panel"], 22 if dark_p else -16)
        btn_fg = best_contrast_fg(btn_bg, t["fg_text"], "#ffffff")
        accent_bg = t["misora_pink"]
        accent_hover = t["misora_pink_hover"]
        fg_accent = best_contrast_fg(accent_bg)

        self.lbl_voice_cue = self._tag_role(
            tk.Label(self.speaker_view_row, text="", bg=t["bg_panel"], fg=t["accent_blue"], font=("Segoe UI", max(8, u_sz - 1))),
            "label_voice"
        )
        self.lbl_voice_cue.pack(side="left", padx=(2, 4))

        self.lbl_segs_badge = self._tag_role(
            tk.Label(self.speaker_view_row, text="", bg=t["bg_panel"], fg=t["misora_pink"], font=("Segoe UI", max(7, u_sz - 2), "bold")),
            "label_accent"
        )
        self.lbl_segs_badge.pack(side="left", padx=(2, 4))

        # Row 3: Collapsible NGUI Ribbon ONLY (default hidden via var_show_ngui_ribbon=False)
        self.ribbon_actions_row = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        self.ribbon_actions_row.pack(fill="x", padx=6, pady=(0, 4))

        self.ribbon_frame = self._tag_role(
            tk.Frame(self.ribbon_actions_row, bg=t["bg_editor"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "ribbon"
        )
        self.ribbon_frame.pack(side="left", padx=(0, 4))

        self.btn_ribbon_swatch = tk.Button(
            self.ribbon_frame,
            width=2,
            bg=self._active_ngui_color,
            activebackground=self._active_ngui_color,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.on_open_color_picker,
        )
        self.btn_ribbon_swatch.pack(side="left", padx=(2, 1), pady=1)
        create_tooltip(self.btn_ribbon_swatch, "Active NGUI Color (Click to open Color Picker)")

        self.ico_palette = self.get_icon("palette", (16, 16))
        btn_color = self._tag_role(
            tk.Button(
                self.ribbon_frame,
                text=" Color",
                image=self.ico_palette,
                compound="left",
                font=("Segoe UI", 8, "bold"),
                bg=accent_bg,
                fg=fg_accent,
                activebackground=accent_hover,
                activeforeground=fg_accent,
                bd=1,
                relief="raised",
                padx=3,
                pady=0,
                cursor="hand2",
                command=self._apply_active_ribbon_color,
            ),
            "ribbon_primary_btn",
        )
        btn_color.pack(side="left", padx=1, pady=1)
        create_tooltip(btn_color, "Apply hex color tag [RRGGBB]")

        btn_grad = self._tag_role(
            tk.Button(
                self.ribbon_frame,
                text="Grad",
                font=("Segoe UI", 8, "bold"),
                bg=accent_bg,
                fg=fg_accent,
                activebackground=accent_hover,
                activeforeground=fg_accent,
                bd=1,
                relief="raised",
                padx=3,
                pady=0,
                cursor="hand2",
                command=self._apply_active_ribbon_gradient,
            ),
            "ribbon_primary_btn",
        )
        btn_grad.pack(side="left", padx=1, pady=1)
        create_tooltip(btn_grad, "Apply vertical gradient tag [top-bottom]")

        self.ico_eyedropper = self.get_icon("eyedropper", (16, 16))
        self.btn_eyedropper = self._tag_role(
            tk.Button(
                self.ribbon_frame,
                text="🎨",
                image=self.ico_eyedropper,
                fg=btn_fg,
                bg=btn_bg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                cursor="hand2",
                command=self.on_open_color_picker,
            ),
            "ribbon_btn",
        )
        self.btn_eyedropper.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_eyedropper, "Open NGUI Color & Gradient Picker")

        self._tag_role(tk.Label(self.ribbon_frame, text="|", bg=t["bg_editor"], fg=t["border"]), "label_ribbon_sep").pack(side="left", padx=1)

        # NGUI Formatting Buttons
        self.btn_ruby = self._tag_role(
            tk.Button(
                self.ribbon_frame,
                text="Ruby",
                font=("Segoe UI", 8, "bold"),
                bg=accent_bg,
                fg=fg_accent,
                activebackground=accent_hover,
                activeforeground=fg_accent,
                bd=1,
                relief="raised",
                padx=3,
                pady=0,
                cursor="hand2",
                command=self.on_insert_ruby,
            ),
            "ribbon_primary_btn",
        )
        self.btn_ruby.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_ruby, "Wrap Selection with Ruby / Furigana ([rub:...]...[/rub]) (Ctrl+R)")

        # Standalone [-] compatibility button parented OUTSIDE ribbon_frame and unmapped (Safeguard 1)
        self.btn_dash = self._tag_role(
            tk.Button(
                self,
                text="[-]",
                font=("Segoe UI", 8, "bold"),
                bg=btn_bg,
                fg=btn_fg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                padx=2,
                pady=0,
                cursor="hand2",
                command=lambda: self.apply_ngui_wrapper("[-]", ""),
            ),
            "ribbon_btn",
        )
        create_tooltip(self.btn_dash, "Reset Color to Default ([-])")

        mini_style_buttons = [
            ("B", "[b]", "[/b]", "Bold Text ([b]...[/b]) (Ctrl+B)"),
            ("I", "[i]", "[/i]", "Italic Text ([i]...[/i]) (Ctrl+I)"),
            ("U", "[u]", "[/u]", "Underline Text ([u]...[/u]) (Ctrl+U)"),
            ("S", "[s]", "[/s]", "Strikethrough Text ([s]...[/s])"),
            ("Sub", "[sub]", "[/sub]", "Subscript Text ([sub]...[/sub])"),
            ("Sup", "[sup]", "[/sup]", "Superscript Text ([sup]...[/sup])"),
        ]
        self.btn_format_buttons = {}
        for lbl, o_tag, c_tag, tip_txt in mini_style_buttons:
            w_val = 2 if len(lbl) <= 2 else 3
            f_sz = 8 if len(lbl) <= 2 else 7
            b_mini = self._tag_role(
                tk.Button(
                    self.ribbon_frame,
                    text=lbl,
                    font=("Segoe UI", f_sz, "bold"),
                    bg=btn_bg,
                    fg=btn_fg,
                    activebackground=btn_hover,
                    activeforeground=btn_fg,
                    bd=1,
                    relief="raised",
                    width=w_val,
                    padx=0,
                    pady=0,
                    cursor="hand2",
                    command=lambda ot=o_tag, ct=c_tag: self.apply_ngui_wrapper(ot, ct),
                ),
                "ribbon_btn",
            )
            b_mini.pack(side="left", padx=1, pady=1)
            create_tooltip(b_mini, tip_txt)
            self.btn_format_buttons[lbl] = b_mini

        self.btn_size = self._tag_role(
            tk.Button(
                self.ribbon_frame,
                text="Size",
                font=("Segoe UI", 8, "bold"),
                bg=btn_bg,
                fg=btn_fg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                padx=2,
                pady=0,
                cursor="hand2",
                command=self._on_size_dropdown_clicked,
            ),
            "ribbon_btn"
        )
        self.btn_size.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_size, "Change Font Size (<size=...>)")

        # Edit Group Toolbar (docked on right side of Row 2 speaker_view_row: Text | Box | Player | Undo/Redo)
        self.actions_bar = self._tag_role(
            tk.Frame(self.speaker_view_row, bg=t["bg_editor"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "actions_toolbar"
        )
        self.actions_bar.pack(side="right", padx=(4, 0))

        # Text Actions Group (Select Whole Story, Cut, Copy, Paste)
        self.ico_sel_story = self.get_icon("select_story", (16, 16))
        self.btn_sel_story = self._tag_role(
            tk.Button(self.actions_bar, text="🗎", image=self.ico_sel_story, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_select_whole_story),
            "ribbon_btn"
        )
        self.btn_sel_story.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_sel_story, "Select Whole Story Dialogue (Ctrl+Alt+A)")

        self.ico_cut = self.get_icon("cut", (16, 16))
        self.btn_cut = self._tag_role(
            tk.Button(self.actions_bar, text="✂", image=self.ico_cut, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_text_cut),
            "ribbon_btn"
        )
        self.btn_cut.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_cut, "Cut Text (Ctrl+X)")

        self.ico_copy = self.get_icon("copy", (16, 16))
        self.btn_copy = self._tag_role(
            tk.Button(self.actions_bar, text="📋", image=self.ico_copy, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_text_copy),
            "ribbon_btn"
        )
        self.btn_copy.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_copy, "Copy Text (Ctrl+C)")

        self.ico_paste = self.get_icon("paste", (16, 16))
        self.btn_paste = self._tag_role(
            tk.Button(self.actions_bar, text="📥", image=self.ico_paste, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_text_paste),
            "ribbon_btn"
        )
        self.btn_paste.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_paste, "Paste Text / Multi-Box Delimiter Split (Ctrl+V)")

        self._tag_role(tk.Label(self.actions_bar, text="|", bg=t["bg_editor"], fg=t["border"]), "label_ribbon_sep").pack(side="left", padx=1)

        # Box Actions Group (New Box, Cut Box, Copy Box, Paste Box)
        self.ico_plus = self.get_icon("plus", (16, 16))
        self.btn_box_new = self._tag_role(
            tk.Button(self.actions_bar, text="➕", image=self.ico_plus, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_box_new),
            "ribbon_btn"
        )
        self.btn_box_new.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_box_new, "New Dialogue Box (Ctrl+N)")

        self.ico_box_cut = self.get_icon("box_cut", (18, 18))
        self.btn_box_cut = self._tag_role(
            tk.Button(self.actions_bar, text="✂📦", image=self.ico_box_cut, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_box_cut),
            "ribbon_btn"
        )
        self.btn_box_cut.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_box_cut, "Cut Selected Box(es) (Ctrl+Alt+X)")

        self.ico_box_copy = self.get_icon("box_copy", (18, 18))
        self.btn_box_copy = self._tag_role(
            tk.Button(self.actions_bar, text="📋📦", image=self.ico_box_copy, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_box_copy),
            "ribbon_btn"
        )
        self.btn_box_copy.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_box_copy, "Copy Selected Box(es) (Ctrl+Alt+C)")

        self.ico_box_paste = self.get_icon("box_paste", (18, 18))
        self.btn_box_paste = self._tag_role(
            tk.Button(self.actions_bar, text="📥📦", image=self.ico_box_paste, fg=btn_fg, bg=btn_bg, activebackground=btn_hover, activeforeground=btn_fg, bd=1, relief="raised", cursor="hand2", command=self.on_box_paste),
            "ribbon_btn"
        )
        self.btn_box_paste.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_box_paste, "Paste Box(es) (Ctrl+Alt+V)")

        self._tag_role(tk.Label(self.actions_bar, text="|", bg=t["bg_editor"], fg=t["border"]), "label_ribbon_sep").pack(side="left", padx=1)

        # Player Button inside Edit Group right after Box Actions (U10, U12)
        self.ico_player = self.get_icon("player", (16, 16))
        self.btn_player = self._tag_role(
            tk.Button(
                self.actions_bar,
                text="👤",
                image=self.ico_player,
                compound="none" if self.ico_player else "left",
                font=("Segoe UI", max(8, u_sz - 1)),
                bg=btn_bg,
                fg=btn_fg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                padx=2,
                pady=0,
                cursor="hand2",
                command=self.on_insert_playername,
            ),
            "ribbon_btn",
        )
        self.btn_player.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_player, "Insert Player Name tag ({0} / {playername}) (Ctrl+P)")

        self._tag_role(tk.Label(self.actions_bar, text="|", bg=t["bg_editor"], fg=t["border"]), "label_ribbon_sep").pack(side="left", padx=1)

        # History: Undo & Redo at far right of Edit Group (U09, 4.2)
        self.ico_undo = self.get_icon("undo", (16, 16))
        self.btn_ribbon_undo = self._tag_role(
            tk.Button(
                self.actions_bar,
                text="↶",
                image=self.ico_undo,
                fg=btn_fg,
                bg=btn_bg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                cursor="hand2",
                command=self.on_undo,
            ),
            "ribbon_undo_btn",
        )
        self.btn_ribbon_undo.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_ribbon_undo, "Undo (Ctrl+Z)")

        self.ico_redo = self.get_icon("redo", (16, 16))
        self.btn_ribbon_redo = self._tag_role(
            tk.Button(
                self.actions_bar,
                text="↷",
                image=self.ico_redo,
                fg=btn_fg,
                bg=btn_bg,
                activebackground=btn_hover,
                activeforeground=btn_fg,
                bd=1,
                relief="raised",
                cursor="hand2",
                command=self.on_redo,
            ),
            "ribbon_redo_btn",
        )
        self.btn_ribbon_redo.pack(side="left", padx=1, pady=1)
        create_tooltip(self.btn_ribbon_redo, "Redo (Ctrl+Y)")

        # Respect initial ribbon visibility toggle without triggering premature preferences save
        if hasattr(self, "var_show_ngui_ribbon") and not self.var_show_ngui_ribbon.get():
            self.ribbon_frame.pack_forget()
            self.ribbon_actions_row.pack_forget()

        gutter_bg = "#e8e8e8" if self._is_light_theme() else "#2d2d30"
        gutter_fg = "#707070" if self._is_light_theme() else "#858585"

        # Empty State Frame (shown when 0 documents are open; auto-hidden when >=1 document opens)
        self.empty_state_frame = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        empty_center = self._tag_role(tk.Frame(self.empty_state_frame, bg=t["bg_panel"]), "panel")
        empty_center.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_empty_open = self._tag_role(
            tk.Button(
                empty_center,
                text="📂 Open Files",
                font=("Segoe UI", max(11, u_sz + 2), "bold"),
                bg=t["misora_pink"],
                fg=best_contrast_fg(t["misora_pink"]),
                activebackground=t["misora_pink_hover"],
                activeforeground=best_contrast_fg(t["misora_pink"]),
                relief="raised",
                bd=2,
                padx=18,
                pady=8,
                cursor="hand2",
                command=self.on_open_file,
            ),
            "ribbon_primary_btn"
        )
        self.btn_empty_open.pack(pady=(0, 8))

        self.lbl_empty_dnd_hint = self._tag_role(
            tk.Label(
                empty_center,
                text="or drag & drop .unity3d / .misora workspace / .txt scripts here",
                font=("Segoe UI", max(9, u_sz - 1)),
                fg=t["fg_muted"],
                bg=t["bg_panel"],
            ),
            "label_muted"
        )
        self.lbl_empty_dnd_hint.pack()

        # VIEW 1: Bounded Scrollable Page-by-Page Viewport
        self.gd_scroll_wrap = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        self.gd_scroll_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        gd_vscroll = tk.Scrollbar(self.gd_scroll_wrap, orient="vertical")
        gd_vscroll.pack(side="right", fill="y")

        self.gd_canvas = self._tag_role(
            tk.Canvas(
                self.gd_scroll_wrap,
                bg=t["bg_panel"],
                highlightthickness=0,
                bd=0,
                yscrollcommand=gd_vscroll.set,
            ),
            "panel"
        )
        self.gd_canvas.pack(side="left", fill="both", expand=True)
        gd_vscroll.config(command=self._on_gd_scrollbar)

        self.gd_inner = self._tag_role(tk.Frame(self.gd_canvas, bg=t["bg_panel"]), "panel")
        self._gd_canvas_win = self.gd_canvas.create_window((0, 0), window=self.gd_inner, anchor="nw")

        self.gd_inner.bind("<Configure>", self._sync_gd_scroll_bounds)
        self.gd_canvas.bind("<Configure>", self._sync_gd_scroll_bounds)
        self.gd_canvas.bind("<MouseWheel>", self._on_gd_mousewheel)
        self.gd_inner.bind("<MouseWheel>", self._on_gd_mousewheel)

        text_container = self._tag_role(tk.Frame(self.gd_inner, bg=t["bg_panel"]), "panel")
        text_container.pack(fill="both", expand=True, padx=6, pady=(2, 10))

        # Pixel-Calibrated Horizontal Ruler for Clean View (S17 / BUG-40, FEAT-09)
        self.ruler_clean = tk.Canvas(
            text_container,
            height=20,
            bg=gutter_bg,
            bd=0,
            highlightthickness=0,
            cursor="arrow",
        )
        self.ruler_clean.bind("<Configure>", lambda e: self._redraw_pixel_rulers())
        if self.show_column_ruler:
            self.ruler_clean.pack(side="top", fill="x", pady=(0, 2))

        self.clean_editor_row = tk.Frame(text_container, bg=t["bg_panel"])
        self.clean_editor_row.pack(fill="both", expand=True)

        # Vertical Line Numbers Gutter for Clean View (#12)
        d_font_tuple = self._get_dialogue_font_tuple(d_sz)
        self.gutter_clean = tk.Text(
            self.clean_editor_row,
            width=3,
            font=d_font_tuple,
            bg=gutter_bg,
            fg=gutter_fg,
            bd=0,
            relief="flat",
            wrap="none",
            takefocus=0,
            cursor="arrow",
            padx=2,
            pady=8,
            spacing1=3,
            spacing3=3,
        )
        self.gutter_clean.config(state="disabled")
        if self.show_line_numbers:
            self.gutter_clean.pack(side="left", fill="y", padx=(0, 2))

        self.txt_dialogue = tk.Text(
            self.clean_editor_row,
            wrap="word",
            height=7,
            font=d_font_tuple,
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
            padx=10,
            pady=8,
            spacing1=3,
            spacing3=3,
            bd=1,
            relief="solid",
            highlightthickness=0,
            undo=False,
        )
        self.txt_dialogue.pack(side="left", fill="both", expand=True)
        self._configure_editor_rich_tags(self.txt_dialogue, d_fam, d_sz)
        self.txt_dialogue.bind("<KeyRelease>", lambda e: self._commit_widget_edit(self.txt_dialogue))
        self.txt_dialogue.bind("<<Cut>>", lambda e: self.after_idle(lambda: self._commit_widget_edit(self.txt_dialogue)))
        self.txt_dialogue.bind("<<Paste>>", lambda e: self.after_idle(lambda: self._commit_widget_edit(self.txt_dialogue)))
        self.txt_dialogue.bind("<MouseWheel>", self._on_gd_mousewheel)
        self.txt_dialogue.bind("<Up>", self._on_dialogue_key_up)
        self.txt_dialogue.bind("<Down>", self._on_dialogue_key_down)
        self.txt_dialogue.bind("<Control-z>", lambda e: self._shortcut_undo())
        self.txt_dialogue.bind("<Control-y>", lambda e: self._shortcut_redo())
        self.txt_dialogue.bind("<Control-Shift-Z>", lambda e: self._shortcut_redo())
        self.txt_dialogue.bind("<Control-Shift-z>", lambda e: self._shortcut_redo())
        self.txt_dialogue.bind("<Control-b>", lambda e: self._shortcut_wrap("[b]", "[/b]"))
        self.txt_dialogue.bind("<Control-i>", lambda e: self._shortcut_wrap("[i]", "[/i]"))
        self.txt_dialogue.bind("<Control-u>", lambda e: self._shortcut_wrap("[u]", "[/u]"))
        self.txt_dialogue.bind("<Control-Shift-V>", lambda e: (self.on_paste_cross_box(), "break")[1])
        self.txt_dialogue.bind("<Control-Shift-v>", lambda e: (self.on_paste_cross_box(), "break")[1])

        # Code-Drawn Game-Style Dialogue Preview (S18 / FEAT-10, NO-02, NO-12)
        self.dialogue_preview_canvas = self._tag_role(
            tk.Canvas(text_container, bg=t["bg_panel"], highlightthickness=0, bd=0),
            "panel",
        )
        self.txt_dialogue_preview = tk.Text(
            self.dialogue_preview_canvas,
            wrap="none",
            height=3,
            font=(d_fam, d_sz),
            bg="#fffcf4",
            fg=best_contrast_fg("#fffcf4", "#2b2118", "#1a1a1a"),
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
            bd=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            spacing1=2,
            spacing3=2,
            undo=False,
            state="disabled",
        )
        self._dialogue_preview_win = self.dialogue_preview_canvas.create_window(
            0, 0, window=self.txt_dialogue_preview, anchor="nw"
        )
        self.dialogue_preview_canvas.bind("<MouseWheel>", self._on_gd_mousewheel)
        self.txt_dialogue_preview.bind("<MouseWheel>", self._on_gd_mousewheel)
        self.dialogue_preview_canvas.bind("<Configure>", self._on_dialogue_preview_configure)
        self._preview_saved_editor_state = None

        # Dedicated Box 0 Story Metadata Panel (Option 1)
        self.panel_box0_metadata = self._tag_role(tk.Frame(text_container, bg=t["bg_panel"]), "panel")

        box0_hdr = self._tag_role(tk.Frame(self.panel_box0_metadata, bg=t["bg_panel"]), "panel")
        box0_hdr.pack(fill="x", padx=4, pady=(2, 6))
        self._tag_role(
            tk.Label(
                box0_hdr,
                text="Story Metadata & Cutscene Info (Box 0)",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["misora_pink"],
            ),
            "label_accent"
        ).pack(side="left")
        self._tag_role(
            tk.Label(
                box0_hdr,
                text="— Episode title, chapter subtitle, and synopsis summary displayed in cutscene menus",
                font=("Segoe UI", max(8, u_sz - 1), "italic"),
                bg=t["bg_panel"],
                fg=t["fg_muted"],
            ),
            "label_muted"
        ).pack(side="left", padx=6)

        row_title = self._tag_role(tk.Frame(self.panel_box0_metadata, bg=t["bg_panel"]), "panel")
        row_title.pack(fill="x", padx=4, pady=3)
        self._tag_role(
            tk.Label(
                row_title,
                text="Episode Title:",
                width=16,
                anchor="w",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["fg_text"],
            ),
            "label_panel"
        ).pack(side="left")
        self.entry_box0_title = self._tag_role(
            tk.Entry(
                row_title,
                textvariable=self.var_box0_title,
                font=(d_fam, d_sz),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                relief="solid",
                bd=1,
                highlightthickness=0,
            ),
            "entry_editor"
        )
        self.entry_box0_title.pack(side="left", fill="x", expand=True)
        self.entry_box0_title.bind("<KeyRelease>", lambda e: self._on_box0_metadata_edited())

        row_sub = self._tag_role(tk.Frame(self.panel_box0_metadata, bg=t["bg_panel"]), "panel")
        row_sub.pack(fill="x", padx=4, pady=3)
        self._tag_role(
            tk.Label(
                row_sub,
                text="Chapter Subtitle:",
                width=16,
                anchor="w",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["fg_text"],
            ),
            "label_panel"
        ).pack(side="left")
        self.entry_box0_subtitle = self._tag_role(
            tk.Entry(
                row_sub,
                textvariable=self.var_box0_subtitle,
                font=(d_fam, d_sz),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                relief="solid",
                bd=1,
                highlightthickness=0,
            ),
            "entry_editor"
        )
        self.entry_box0_subtitle.pack(side="left", fill="x", expand=True)
        self.entry_box0_subtitle.bind("<KeyRelease>", lambda e: self._on_box0_metadata_edited())

        row_sum_hdr = self._tag_role(tk.Frame(self.panel_box0_metadata, bg=t["bg_panel"]), "panel")
        row_sum_hdr.pack(fill="x", padx=4, pady=(6, 2))
        self._tag_role(
            tk.Label(
                row_sum_hdr,
                text="Synopsis / Summary:",
                font=("Segoe UI", u_sz, "bold"),
                bg=t["bg_panel"],
                fg=t["fg_text"],
            ),
            "label_panel"
        ).pack(side="left")
        self.lbl_box0_summary_len = self._tag_role(
            tk.Label(
                row_sum_hdr,
                text="Characters: 0",
                font=("Segoe UI", max(8, u_sz - 1)),
                bg=t["bg_panel"],
                fg=t["fg_muted"],
            ),
            "label_muted"
        )
        self.lbl_box0_summary_len.pack(side="right")

        self.txt_box0_summary = tk.Text(
            self.panel_box0_metadata,
            wrap="word",
            height=6,
            font=(d_fam, d_sz),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
            padx=10,
            pady=8,
            spacing1=3,
            spacing3=3,
            bd=1,
            relief="solid",
            highlightthickness=0,
            undo=False,
        )
        self.txt_box0_summary.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._configure_editor_rich_tags(self.txt_box0_summary, d_fam, d_sz)
        self.txt_box0_summary.bind("<KeyRelease>", lambda e: self._on_box0_metadata_edited())
        self.txt_box0_summary.bind("<Control-z>", lambda e: self._shortcut_undo())
        self.txt_box0_summary.bind("<Control-y>", lambda e: self._shortcut_redo())
        self.txt_box0_summary.bind("<Control-Shift-Z>", lambda e: self._shortcut_redo())
        self.txt_box0_summary.bind("<Control-Shift-z>", lambda e: self._shortcut_redo())
        self.txt_box0_summary.bind("<Control-b>", lambda e: self._shortcut_wrap("[b]", "[/b]"))
        self.txt_box0_summary.bind("<Control-i>", lambda e: self._shortcut_wrap("[i]", "[/i]"))
        self.txt_box0_summary.bind("<Control-u>", lambda e: self._shortcut_wrap("[u]", "[/u]"))

        # VIEW 2: Continuous Script Dialog Stream
        self.continuous_wrap = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")

        # Pixel-Calibrated Horizontal Ruler for All Script View (S17 / BUG-40, FEAT-09)
        self.ruler_cont = tk.Canvas(
            self.continuous_wrap,
            height=20,
            bg=gutter_bg,
            bd=0,
            highlightthickness=0,
            cursor="arrow",
        )
        self.ruler_cont.bind("<Configure>", lambda e: self._redraw_pixel_rulers())
        if self.show_column_ruler:
            self.ruler_cont.pack(side="top", fill="x", padx=8, pady=(2, 2))

        self.cont_editor_row = tk.Frame(self.continuous_wrap, bg=t["bg_panel"])
        self.cont_editor_row.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Card Stream Canvas & Scrollbar for Multi-Box Story Documents
        self.cont_canvas = tk.Canvas(self.cont_editor_row, bg=t["bg_panel"], highlightthickness=0, bd=0)
        self.cont_scroll_y = tk.Scrollbar(self.cont_editor_row, orient="vertical", command=self.cont_canvas.yview)
        self.cont_canvas.configure(yscrollcommand=self.cont_scroll_y.set)
        self.cont_stream_frame = tk.Frame(self.cont_canvas, bg=t["bg_panel"])
        self.cont_canvas_window = self.cont_canvas.create_window((0, 0), window=self.cont_stream_frame, anchor="nw")

        def _on_cont_canvas_configure(event):
            if hasattr(self, "cont_canvas") and hasattr(self, "cont_canvas_window"):
                new_w = event.width
                if getattr(self, "_cont_resize_job", None) is not None:
                    try:
                        self.after_cancel(self._cont_resize_job)
                    except Exception:
                        pass
                self._cont_resize_job = self.after(20, lambda w=new_w: self._resize_cont_canvas(w))
        self.cont_canvas.bind("<Configure>", _on_cont_canvas_configure)

        def _on_cont_frame_configure(event):
            if hasattr(self, "cont_canvas"):
                self.cont_canvas.configure(scrollregion=self.cont_canvas.bbox("all"))
        self.cont_stream_frame.bind("<Configure>", _on_cont_frame_configure)

        self.cont_canvas.bind("<MouseWheel>", self._on_cont_mousewheel)
        self.cont_stream_frame.bind("<MouseWheel>", self._on_cont_mousewheel)

        # Vertical Line Numbers Gutter for Continuous View (Plain text fallback)
        self.gutter_cont = tk.Text(
            self.cont_editor_row,
            width=4,
            font=("Consolas", max(8, d_sz - 1)),
            bg=gutter_bg,
            fg=gutter_fg,
            bd=0,
            relief="flat",
            wrap="none",
            takefocus=0,
            cursor="arrow",
            padx=2,
            pady=10,
            spacing1=3,
            spacing3=4,
        )
        self.gutter_cont.config(state="disabled")

        self.txt_continuous = tk.Text(
            self.cont_editor_row,
            wrap="word",
            undo=False,
            font=(d_fam, d_sz),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
            padx=14,
            pady=10,
            spacing1=3,
            spacing3=4,
            bd=1,
            relief="solid",
            yscrollcommand=lambda *args: (self.cont_scroll_y.set(*args), self._sync_continuous_gutter_scroll(*args)),
        )

        # Technique A: Single read-only Text widget for multi-box All Script view (U08 / U-7)
        self.txt_all_script = tk.Text(
            self.cont_editor_row,
            wrap="word",
            undo=False,
            state="disabled",
            cursor="arrow",
            font=(d_fam, d_sz),
            bg=t["bg_panel"],
            fg=t["fg_text"],
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
            padx=12,
            pady=8,
            spacing1=2,
            spacing3=2,
            bd=1,
            relief="solid",
            highlightthickness=0,
            yscrollcommand=self.cont_scroll_y.set,
        )
        self._install_shortcuts_bindtag(self.txt_all_script)
        self.txt_all_script.bind("<Button-1>", self._on_all_script_click)
        self.txt_all_script.bind("<Double-Button-1>", self._on_all_script_double_click)
        self.txt_all_script.bind("<Return>", self._on_all_script_enter)
        self.txt_all_script.bind("<Up>", lambda e: (self.on_prev_box(), "break")[1])
        self.txt_all_script.bind("<Down>", lambda e: (self.on_next_box(), "break")[1])
        self.txt_all_script.bind("<Control-a>", lambda e: (self.on_select_whole_story(), "break")[1])
        self.txt_all_script.bind("<Control-A>", lambda e: (self.on_select_whole_story(), "break")[1])
        self._configure_editor_rich_tags(self.txt_all_script, d_fam, d_sz)

        self.txt_continuous.tag_configure(
            "cont_divider",
            foreground=t["border"],
            font=("Consolas", max(7, d_sz - 3)),
            spacing1=4,
            spacing3=2,
        )
        self.txt_continuous.tag_configure(
            "cont_badge",
            foreground=t["misora_pink"],
            font=("Consolas", max(8, d_sz - 2), "bold"),
            spacing1=2,
            spacing3=4,
        )
        self.txt_continuous.tag_configure(
            "cont_speaker",
            foreground=t["fg_text"],
            font=(d_fam, max(9, d_sz - 1), "bold"),
            spacing1=2,
            spacing3=4,
        )
        self.txt_continuous.tag_configure(
            "cont_narrator",
            foreground=t["fg_muted"],
            font=(d_fam, max(8, d_sz - 2), "italic"),
            spacing1=2,
            spacing3=4,
        )
        self.txt_continuous.tag_configure(
            "cont_voice",
            foreground=t["accent_blue"],
            font=("Segoe UI", max(8, d_sz - 3)),
            spacing1=2,
            spacing3=4,
        )
        self.txt_continuous.tag_configure(
            "cont_active_header",
            background=t["highlight_bg"],
        )
        self.txt_continuous.tag_configure(
            "cont_body",
            foreground=t["fg_text"],
            font=(d_fam, d_sz),
            lmargin1=14,
            lmargin2=14,
            rmargin=10,
        )
        self._configure_editor_rich_tags(self.txt_continuous, d_fam, d_sz)

        self.txt_continuous.bind("<ButtonRelease-1>", self._on_continuous_cursor_moved)
        self.txt_continuous.bind("<Key>", self._on_continuous_key_guard)
        self.txt_continuous.bind("<KeyRelease>", self._on_continuous_key_release)
        self.txt_continuous.bind("<<Copy>>", self._on_continuous_copy)
        self.txt_continuous.bind("<Control-c>", self._on_continuous_copy)
        self.txt_continuous.bind("<<Paste>>", self._on_continuous_paste_guard)
        self.txt_continuous.bind("<<Cut>>", self._on_continuous_cut_guard)
        self.txt_continuous.bind("<Control-b>", lambda e: self._shortcut_wrap("[b]", "[/b]"))
        self.txt_continuous.bind("<Control-i>", lambda e: self._shortcut_wrap("[i]", "[/i]"))
        self.txt_continuous.bind("<Control-u>", lambda e: self._shortcut_wrap("[u]", "[/u]"))
        self.txt_continuous.bind("<Control-Shift-V>", lambda e: (self.on_paste_cross_box(), "break")[1])
        self.txt_continuous.bind("<Control-Shift-v>", lambda e: (self.on_paste_cross_box(), "break")[1])

        # BOTTOM VIEW: Raw AST Script View (Technical Records)
        bottom_view = self._tag_role(tk.Frame(self.v_paned, bg=t["bg_panel"]), "panel")
        self.v_paned.add(bottom_view, minsize=80, height=200, stretch="never")

        raw_header = self._tag_role(tk.Frame(bottom_view, bg=t["bg_panel"]), "panel")
        raw_header.pack(fill="x", padx=8, pady=4)
        self._raw_edit_mode: bool = False
        self.lbl_raw_title = self._tag_role(
            tk.Label(raw_header, text="Raw Commands", font=("Segoe UI", u_sz, "bold"), bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        )
        self.lbl_raw_title.pack(side="left")

        self.btn_edit_raw = self._tag_role(
            tk.Button(
                raw_header,
                text="Edit Raw (v2)",
                font=("Segoe UI", max(8, u_sz - 1)),
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=self.on_enter_raw_edit_mode,
                state="disabled",
            ),
            "ribbon_btn",
        )
        self.btn_edit_raw.pack(side="right", padx=(4, 0))
        create_tooltip(self.btn_edit_raw, "Edit whole file as lossless v2 Raw Commands (S19)")

        self.btn_cancel_raw = self._tag_role(
            tk.Button(
                raw_header,
                text="Revert / Cancel",
                font=("Segoe UI", max(8, u_sz - 1)),
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=self.on_cancel_raw_edit_mode,
            ),
            "ribbon_btn",
        )
        create_tooltip(self.btn_cancel_raw, "Discard Raw Commands edits and return to read-only view")

        self.btn_apply_raw = self._tag_role(
            tk.Button(
                raw_header,
                text="Apply Raw",
                font=("Segoe UI", max(8, u_sz - 1), "bold"),
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=self.on_apply_raw_commands,
            ),
            "ribbon_primary_btn",
        )
        create_tooltip(self.btn_apply_raw, "Validate and apply Raw Commands v2 edits to workspace")

        raw_container = self._tag_role(tk.Frame(bottom_view, bg=t["bg_panel"]), "panel")
        raw_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        raw_scroll_y = tk.Scrollbar(raw_container)
        raw_scroll_y.pack(side="right", fill="y")
        raw_scroll_x = tk.Scrollbar(raw_container, orient="horizontal")
        raw_scroll_x.pack(side="bottom", fill="x")

        self.txt_raw = tk.Text(
            raw_container,
            wrap="none",
            state="disabled",
            font=("Consolas", r_sz),
            bg=self._shift_hex(t["bg_editor"], -6),
            fg=t["fg_muted"],
            insertbackground=t["misora_pink"],
            padx=8,
            pady=6,
            bd=1,
            relief="solid",
            yscrollcommand=raw_scroll_y.set,
            xscrollcommand=raw_scroll_x.set
        )
        self.txt_raw.pack(fill="both", expand=True)
        raw_scroll_y.config(command=self.txt_raw.yview)
        raw_scroll_x.config(command=self.txt_raw.xview)

    # -------------------------------------------------------------------------
    # Debug File Logging & Diagnostics (#14)
    # -------------------------------------------------------------------------
    def _on_debug_settings_changed(self) -> None:
        cats = {cat: (True if cat == ALWAYS_ON_CATEGORY else bool(var.get())) for cat, var in self.var_log_categories.items()}
        self.logger.configure(
            level_name=self.var_log_level.get(),
            log_to_file=bool(self.var_log_to_file.get()),
            categories=cats,
        )
        self._save_user_prefs(silent=True)
        self.logger.info(
            "UI / Theme / Config",
            f"Debug settings updated (level={self.var_log_level.get()}, log_to_file={self.var_log_to_file.get()})",
        )

    def _sync_debug_menu_states(self) -> None:
        exists_state = "normal" if DEBUG_LOG_PATH.is_file() else "disabled"
        try:
            self.debug_menu.entryconfig(self._idx_open_log, state=exists_state)
            self.debug_menu.entryconfig(self._idx_clear_log, state=exists_state)
        except Exception:
            pass

    def _on_open_debug_log_file(self) -> None:
        if not DEBUG_LOG_PATH.is_file():
            messagebox.showinfo("Debug Log", "Debug log file does not exist yet.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(DEBUG_LOG_PATH))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(DEBUG_LOG_PATH)])
        except Exception as exc:
            self.logger.error("Errors & Exceptions", f"Failed to open log file: {exc}")

    def _on_clear_debug_log_file(self) -> None:
        if self.logger.clear_log_file():
            self.logger.info("UI / Theme / Config", f"Cleared debug log file: {DEBUG_LOG_PATH}")
            self.show_toast("✓ Cleared debug log file")

    # -------------------------------------------------------------------------
    # Speaker Cyclic Jump & Focus-Safe Autocomplete (U-3, U-4)
    # -------------------------------------------------------------------------
    def _on_speaker_dropdown_clicked(self) -> None:
        """Display popup menu listing speakers with counts to jump/cycle boxes without renaming (U-3)."""
        if getattr(self, "is_box0_active", False):
            return
        if not self.current_doc or not self.current_doc.boxes:
            return

        self._close_speaker_autocomplete()

        counts: Dict[str, int] = {}
        for box in self.current_doc.boxes:
            sp = box.speaker
            counts[sp] = counts.get(sp, 0) + 1

        t = self.theme
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=t["bg_panel"],
            fg=panel_fg,
            activebackground=t["misora_pink"],
            activeforeground=best_contrast_fg(t["misora_pink"]),
        )

        actors = [a for a in sorted(self.current_doc.actors()) if a]
        for act in actors:
            cnt = counts.get(act, 0)
            if cnt > 0:
                menu.add_command(
                    label=f"{act} ({cnt})",
                    command=lambda a=act: self._jump_to_speaker(a),
                )

        narr_cnt = counts.get("", 0)
        if narr_cnt > 0:
            if actors:
                menu.add_separator()
            menu.add_command(
                label=f"(Narration) ({narr_cnt})",
                command=lambda: self._jump_to_speaker(""),
            )

        try:
            x = self.btn_speaker_dropdown.winfo_rootx()
            y = self.btn_speaker_dropdown.winfo_rooty() + self.btn_speaker_dropdown.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _jump_to_speaker(self, speaker_name: str) -> Optional[int]:
        """Jump to the next occurrence of speaker_name (wrapping around) without mutating any speaker (U-3)."""
        if not self.current_doc or not self.current_doc.boxes:
            return None

        self._close_speaker_autocomplete()
        matching_indices = [
            i for i, b in enumerate(self.current_doc.boxes) if b.speaker == speaker_name
        ]
        disp = speaker_name if speaker_name else "(Narration)"
        if not matching_indices:
            self.show_toast(f"No boxes found for {disp}.")
            return None

        on_same_speaker = (
            not getattr(self, "is_box0_active", False)
            and 0 <= self.current_box_idx < len(self.current_doc.boxes)
            and self.current_doc.boxes[self.current_box_idx].speaker == speaker_name
        )
        if on_same_speaker:
            next_idx = next((idx for idx in matching_indices if idx > self.current_box_idx), matching_indices[0])
        else:
            next_idx = matching_indices[0]

        self.is_box0_active = False
        self.current_box_idx = next_idx
        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
            self._focus_continuous_box(next_idx, move_cursor=True)
        else:
            self._update_views()

        occ_pos = matching_indices.index(next_idx) + 1
        occ_total = len(matching_indices)
        self.show_toast(f"Jumped to Box #{next_idx + 1} — {disp} ({occ_pos}/{occ_total})")
        return next_idx

    def _is_widget_in_speaker_popup(self, widget: Optional[tk.Misc]) -> bool:
        """Return True if widget is the speaker autocomplete Toplevel or one of its descendants."""
        popup = getattr(self, "_speaker_popup", None)
        if popup is None or widget is None:
            return False
        try:
            if not popup.winfo_exists():
                return False
        except Exception:
            return False
        cur: Optional[tk.Misc] = widget
        while cur is not None:
            if cur == popup:
                return True
            cur = getattr(cur, "master", None)
        return False

    def _is_speaker_popup_open(self) -> bool:
        popup = getattr(self, "_speaker_popup", None)
        if popup is None:
            return False
        try:
            return bool(popup.winfo_exists())
        except Exception:
            return False

    def _get_speaker_autocomplete_candidates(self, filter_text: str) -> List[Tuple[str, str]]:
        """Build ordered (display_label, commit_value) pairs filtered by prefix then substring."""
        items: List[Tuple[str, str]] = []
        seen_vals: Set[str] = set()
        if self.current_doc:
            for act in sorted(self.current_doc.actors()):
                if act and act not in seen_vals:
                    seen_vals.add(act)
                    items.append((act, act))
        if "{playername}" not in seen_vals and "{0}" not in seen_vals:
            items.append(("{playername}", "{playername}"))
        items.append(("(Narration — Clear Speaker)", ""))

        q = (filter_text or "").strip().lower()
        if not q:
            return items

        prefix_hits: List[Tuple[str, str]] = []
        substr_hits: List[Tuple[str, str]] = []
        for label, val in items:
            lbl_l = label.lower()
            val_l = val.lower()
            if lbl_l.startswith(q) or (val_l and val_l.startswith(q)):
                prefix_hits.append((label, val))
            elif q in lbl_l or (val_l and q in val_l):
                substr_hits.append((label, val))
        return prefix_hits + substr_hits

    def _open_speaker_autocomplete(self) -> None:
        """Open or refresh the lightweight Google-style speaker autocomplete popup beneath entry_speaker."""
        if getattr(self, "_destroyed", False):
            return
        if getattr(self, "is_box0_active", False) or not self.current_doc or not self.current_doc.boxes:
            return
        if not hasattr(self, "entry_speaker") or not self.entry_speaker.winfo_exists():
            return
        if str(self.entry_speaker.cget("state")) == "disabled":
            return

        if not self._is_speaker_popup_open():
            t = self.theme
            editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
            hl_fg = best_contrast_fg(t["highlight_bg"], t["misora_pink"], "#ffffff")

            popup = tk.Toplevel(self)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.transient(self)
            popup.configure(bg=t["border"], bd=1, relief="solid")

            lb = tk.Listbox(
                popup,
                exportselection=False,
                activestyle="none",
                bd=0,
                highlightthickness=0,
                bg=t["bg_editor"],
                fg=editor_fg,
                selectbackground=t["highlight_bg"],
                selectforeground=hl_fg,
                font=("Segoe UI", 9),
                cursor="hand2",
            )
            lb.pack(fill="both", expand=True, padx=1, pady=1)
            lb.bind("<ButtonRelease-1>", lambda e: self._on_speaker_listbox_click(e))
            lb.bind("<Return>", lambda e: self._accept_speaker_autocomplete_selection())
            lb.bind("<KP_Enter>", lambda e: self._accept_speaker_autocomplete_selection())
            lb.bind("<Escape>", self._on_speaker_escape)
            lb.bind("<FocusOut>", self._on_speaker_focus_out)

            self._speaker_popup = popup
            self._speaker_listbox = lb
            self._speaker_popup_navigated = False
            self._speaker_ac_user_typed = False
            self._speaker_ac_initial_text = self.speaker_var.get()

        self._refresh_speaker_autocomplete()

    def _get_monitor_work_area(self, x: int, y: int) -> Tuple[int, int, int, int]:
        """Return (work_left, work_top, work_right, work_bottom) for the monitor containing (x, y)."""
        if sys.platform == "win32" and hasattr(ctypes, "windll"):
            try:
                class _RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", ctypes.c_long),
                        ("top", ctypes.c_long),
                        ("right", ctypes.c_long),
                        ("bottom", ctypes.c_long),
                    ]

                class _MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.c_ulong),
                        ("rcMonitor", _RECT),
                        ("rcWork", _RECT),
                        ("dwFlags", ctypes.c_ulong),
                    ]

                pt = wintypes.POINT(int(x), int(y))
                hmon = ctypes.windll.user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST = 2
                if hmon:
                    mi = _MONITORINFO()
                    mi.cbSize = ctypes.sizeof(_MONITORINFO)
                    if ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                        r = mi.rcWork
                        return (int(r.left), int(r.top), int(r.right), int(r.bottom))
            except Exception:
                pass
        try:
            sw = int(self.winfo_screenwidth() or 1920)
            sh = int(self.winfo_screenheight() or 1080)
        except Exception:
            sw, sh = 1920, 1080
        return (0, 0, sw, sh)

    def _refresh_speaker_autocomplete(self) -> None:
        """Populate and position the speaker autocomplete listbox for current filter text."""
        if not self._is_speaker_popup_open():
            return
        popup = self._speaker_popup
        lb = self._speaker_listbox
        if popup is None or lb is None or not lb.winfo_exists():
            return

        cur_txt = self.speaker_var.get() if getattr(self, "_speaker_ac_user_typed", False) else ""
        candidates = self._get_speaker_autocomplete_candidates(cur_txt)
        if not candidates:
            self._close_speaker_autocomplete()
            return

        self._speaker_popup_items = candidates
        lb.delete(0, tk.END)
        for label, _val in candidates:
            lb.insert(tk.END, label)
        lb.config(height=min(8, max(1, len(candidates))))
        self._speaker_popup_navigated = False

        try:
            self.entry_speaker.update_idletasks()
            raw_x = int(self.entry_speaker.winfo_rootx())
            raw_y = int(self.entry_speaker.winfo_rooty() + self.entry_speaker.winfo_height() + 1)
            w = max(220, int(self.entry_speaker.winfo_width()))
            row_h = 20
            h = min(8, len(candidates)) * row_h + 6
            work_left, work_top, work_right, work_bottom = self._get_monitor_work_area(raw_x, raw_y)
            x = max(work_left, min(raw_x, work_right - w))
            y = max(work_top, min(raw_y, work_bottom - h))
            popup.geometry(f"{w}x{h}+{x}+{y}")
            popup.deiconify()
            popup.lift()
        except Exception:
            pass

    def _close_speaker_autocomplete(self) -> None:
        """Destroy speaker autocomplete popup safely if open."""
        if getattr(self, "_speaker_focus_out_after_id", None):
            try:
                self.after_cancel(self._speaker_focus_out_after_id)
            except Exception:
                pass
            self._speaker_focus_out_after_id = None
        popup = getattr(self, "_speaker_popup", None)
        self._speaker_popup = None
        self._speaker_listbox = None
        self._speaker_popup_items = []
        self._speaker_popup_navigated = False
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.withdraw()       # Release overrideredirect from Win32 focus chain
                    popup.destroy()
            except Exception:
                pass

    def _on_speaker_focus_in(self) -> None:
        if getattr(self, "_suppress_speaker_popup", False):
            self._suppress_speaker_popup = False
            return
        if getattr(self, "_speaker_focus_out_after_id", None):
            try:
                self.after_cancel(self._speaker_focus_out_after_id)
            except Exception:
                pass
            self._speaker_focus_out_after_id = None
        self._open_speaker_autocomplete()

    def _on_speaker_entry_clicked(self) -> None:
        if getattr(self, "_destroyed", False):
            return
        if not self._is_speaker_popup_open():
            self._open_speaker_autocomplete()

    def _on_speaker_key_release(self, event: Optional[tk.Event]) -> None:
        """Filter autocomplete live without committing to AST on KeyRelease (U-3, U-4)."""
        keysym = getattr(event, "keysym", "") if event is not None else ""
        if keysym in (
            "Up", "Down", "Left", "Right", "Home", "End",
            "Return", "KP_Enter", "Escape", "Tab",
            "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
        ):
            return
        if not getattr(self, "_speaker_ac_user_typed", False):
            if self.speaker_var.get() != getattr(self, "_speaker_ac_initial_text", ""):
                self._speaker_ac_user_typed = True
        if not self._is_speaker_popup_open():
            self._open_speaker_autocomplete()
        else:
            self._refresh_speaker_autocomplete()

    def _on_speaker_nav_down(self, _event: Optional[tk.Event] = None) -> str:
        if not self._is_speaker_popup_open():
            self._open_speaker_autocomplete()
        lb = getattr(self, "_speaker_listbox", None)
        if lb is not None and lb.winfo_exists() and lb.size() > 0:
            sel = lb.curselection()
            idx = (sel[0] + 1) % lb.size() if sel else 0
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
            self._speaker_popup_navigated = True
        return "break"

    def _on_speaker_nav_up(self, _event: Optional[tk.Event] = None) -> str:
        if not self._is_speaker_popup_open():
            return "break"
        lb = getattr(self, "_speaker_listbox", None)
        if lb is not None and lb.winfo_exists() and lb.size() > 0:
            sel = lb.curselection()
            idx = (sel[0] - 1) % lb.size() if sel else lb.size() - 1
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
            self._speaker_popup_navigated = True
        return "break"

    def _on_speaker_enter(self, _event: Optional[tk.Event] = None) -> str:
        lb = getattr(self, "_speaker_listbox", None)
        if (
            self._is_speaker_popup_open()
            and getattr(self, "_speaker_popup_navigated", False)
            and lb is not None
            and lb.winfo_exists()
            and lb.curselection()
        ):
            self._accept_speaker_autocomplete_selection()
        else:
            self._close_speaker_autocomplete()
            self._commit_speaker_edit(source="keyboard")
        return "break"

    def _on_speaker_escape(self, _event: Optional[tk.Event] = None) -> str:
        self._close_speaker_autocomplete()
        return "break"

    def _on_speaker_listbox_click(self, event: tk.Event) -> None:
        lb = getattr(self, "_speaker_listbox", None)
        if lb is not None and lb.winfo_exists() and lb.size() > 0:
            idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
        self._accept_speaker_autocomplete_selection()

    def _accept_speaker_autocomplete_selection(self) -> Optional[str]:
        lb = getattr(self, "_speaker_listbox", None)
        items = getattr(self, "_speaker_popup_items", [])
        chosen_val: Optional[str] = None
        if lb is not None and lb.winfo_exists() and items:
            sel = lb.curselection()
            idx = sel[0] if sel else 0
            if 0 <= idx < len(items):
                chosen_val = items[idx][1]
        self._close_speaker_autocomplete()
        if chosen_val is not None:
            self.speaker_var.set(chosen_val)
            self._commit_speaker_edit(source="autocomplete")
            # Deferred focus restoration: on Windows, destroying an overrideredirect(True)
            # Toplevel mid-click breaks Win32 focus/capture; immediate focus_set() fails.
            # Set suppress flag NOW (before the deferred callback) to prevent _on_speaker_focus_in
            # from reopening the popup when focus returns to entry_speaker.
            self._suppress_speaker_popup = True
            self.after_idle(self._restore_speaker_entry_focus)
        return "break"

    def _restore_speaker_entry_focus(self) -> None:
        """Deferred focus restoration for entry_speaker after autocomplete selection.

        Called via after_idle() so the Win32 window manager has processed the
        overrideredirect Toplevel destruction before we attempt to reclaim focus.
        Uses focus_force() (not focus_set()) for reliable OS-level focus acquisition
        on Windows after an overrideredirect popup was destroyed mid-click.
        """
        if getattr(self, "_destroyed", False):
            return
        if not hasattr(self, "entry_speaker") or not self.entry_speaker.winfo_exists():
            return
        if str(self.entry_speaker.cget("state")) == "disabled":
            return
        try:
            self.entry_speaker.focus_force()
            self.entry_speaker.icursor("end")
        except Exception:
            pass

    def _on_speaker_focus_out(self, _event: Optional[tk.Event] = None) -> None:
        """Defer FocusOut briefly so focus moving into our own autocomplete popup does not commit prematurely."""
        if getattr(self, "_destroyed", False):
            return
        if getattr(self, "_speaker_focus_out_after_id", None):
            try:
                self.after_cancel(self._speaker_focus_out_after_id)
            except Exception:
                pass
        self._speaker_focus_out_after_id = self.after(20, self._on_speaker_focus_out_deferred)

    def _on_speaker_focus_out_deferred(self) -> None:
        self._speaker_focus_out_after_id = None
        if getattr(self, "_destroyed", False):
            return
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        if focused == getattr(self, "entry_speaker", None) or self._is_widget_in_speaker_popup(focused):
            return
        self._close_speaker_autocomplete()
        self._commit_speaker_edit(source="focus_out")

    def _on_speaker_virtual_edit(self) -> None:
        """Commit virtual Cut/Paste edits on entry_speaker (Rule 11) and refresh popup if open."""
        self._commit_speaker_edit(source="virtual")
        if self._is_speaker_popup_open():
            self._refresh_speaker_autocomplete()

    def _assign_speaker_to_current_box(self, new_speaker: str) -> None:
        if getattr(self, "is_box0_active", False):
            return
        self.speaker_var.set(new_speaker)
        self._commit_speaker_edit(source="menu")

    def _append_speaker_attribute(self, attr_suffix: str) -> None:
        cur = self.speaker_var.get().strip()
        new_val = f"{cur}{attr_suffix}" if cur else attr_suffix
        self.speaker_var.set(new_val)
        self._on_speaker_edited()
        self.show_toast(f"Updated speaker: {new_val}")

    def _prompt_append_speaker_attribute(self) -> None:
        """Modal prompt to append a custom attribute/variant to current speaker."""
        t = self.theme
        dlg = tk.Toplevel(self)
        dlg.title("Append Speaker Attribute")
        dlg.geometry("380x150")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=t["bg_panel"])
        apply_window_icon(dlg)

        tk.Label(dlg, text="Enter Attribute (e.g. （サマー） or (Summer)):", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=best_contrast_fg(t["bg_panel"])).pack(padx=14, pady=(14, 6), anchor="w")
        var_attr = tk.StringVar(master=dlg, value="（サマー）")
        ent = tk.Entry(dlg, textvariable=var_attr, font=("Segoe UI", 10), bg=t["bg_editor"], fg=best_contrast_fg(t["bg_editor"]))
        ent.pack(fill="x", padx=14, pady=4)
        ent.focus_set()
        ent.select_range(0, tk.END)

        btn_row = tk.Frame(dlg, bg=t["bg_panel"])
        btn_row.pack(fill="x", padx=14, pady=10)

        def _safe_close(_e: Optional[tk.Event] = None):
            safe_grab_release(dlg)
            dlg.destroy()

        def _commit():
            val = var_attr.get().strip()
            if val:
                self._append_speaker_attribute(val)
            _safe_close()

        dlg.protocol("WM_DELETE_WINDOW", _safe_close)
        dlg.bind("<Escape>", _safe_close)
        ent.bind("<Return>", lambda e: _commit())
        ttk.Button(btn_row, text="Append", style="Pink.TButton", command=_commit).pack(side="right", padx=(4, 0))
        ttk.Button(btn_row, text="Cancel", style="TButton", command=_safe_close).pack(side="right")

    # -------------------------------------------------------------------------
    # Line Numbers Gutter & Column Ruler Synchronization (#12)
    # -------------------------------------------------------------------------
    @staticmethod
    def _is_widget_packed(w: tk.Widget) -> bool:
        try:
            return bool(w.pack_info())
        except Exception:
            return False

    def _on_toggle_line_numbers(self) -> None:
        """Toggle line number gutter visibility with safe layout anchoring."""
        visible = bool(self.var_show_line_numbers.get())
        self.show_line_numbers = visible

        # Clean View gutter
        if hasattr(self, "gutter_clean"):
            if visible:
                if hasattr(self, "txt_dialogue") and not self._is_widget_packed(self.gutter_clean):
                    try:
                        self.gutter_clean.pack(before=self.txt_dialogue, side="left", fill="y", padx=(0, 2))
                    except Exception:
                        self.gutter_clean.pack(side="left", fill="y", padx=(0, 2))
                self._update_gutter_clean()
            else:
                if self._is_widget_packed(self.gutter_clean):
                    self.gutter_clean.pack_forget()

        # Continuous View card gutters
        if hasattr(self, "_card_widgets"):
            for idx, cdata in self._card_widgets.items():
                gutter = cdata.get("gutter")
                txt = cdata.get("txt")
                if gutter and txt:
                    if visible:
                        if not self._is_widget_packed(gutter):
                            try:
                                gutter.pack(before=txt, side="left", fill="y", padx=(0, 2))
                            except Exception:
                                gutter.pack(side="left", fill="y", padx=(0, 2))
                    else:
                        if self._is_widget_packed(gutter):
                            gutter.pack_forget()

        # Plain text fallback gutter
        if hasattr(self, "gutter_cont") and hasattr(self, "txt_continuous"):
            if visible and self._is_widget_packed(self.txt_continuous) and not self._is_widget_packed(self.gutter_cont):
                try:
                    self.gutter_cont.pack(before=self.txt_continuous, side="left", fill="y", padx=(0, 2))
                except Exception:
                    self.gutter_cont.pack(side="left", fill="y", padx=(0, 2))
            elif not visible and self._is_widget_packed(self.gutter_cont):
                self.gutter_cont.pack_forget()

        if hasattr(self, "cont_canvas"):
            self.cont_canvas.configure(scrollregion=self.cont_canvas.bbox("all"))
        if hasattr(self, "gd_inner"):
            self.gd_inner.update_idletasks()
            self._sync_gd_scroll_bounds()
        self._redraw_pixel_rulers()
        self.show_toast(f"Line numbers {'enabled' if visible else 'hidden'}")
        self._save_user_prefs(silent=True)

    def _on_toggle_column_ruler(self) -> None:
        """Toggle column ruler visibility with safe layout anchoring."""
        visible = bool(self.var_show_column_ruler.get())
        self.show_column_ruler = visible
        if hasattr(self, "ruler_clean"):
            if visible:
                if hasattr(self, "clean_editor_row") and not self._is_widget_packed(self.ruler_clean):
                    try:
                        self.ruler_clean.pack(before=self.clean_editor_row, side="top", fill="x", pady=(0, 2))
                    except Exception:
                        self.ruler_clean.pack(side="top", fill="x", pady=(0, 2))
            else:
                if self._is_widget_packed(self.ruler_clean):
                    self.ruler_clean.pack_forget()
        if hasattr(self, "ruler_cont"):
            if visible:
                if hasattr(self, "cont_editor_row") and not self._is_widget_packed(self.ruler_cont):
                    try:
                        self.ruler_cont.pack(before=self.cont_editor_row, side="top", fill="x", padx=8, pady=(2, 2))
                    except Exception:
                        self.ruler_cont.pack(side="top", fill="x", padx=8, pady=(2, 2))
            else:
                if self._is_widget_packed(self.ruler_cont):
                    self.ruler_cont.pack_forget()
        if hasattr(self, "gd_inner"):
            self.gd_inner.update_idletasks()
            self._sync_gd_scroll_bounds()
        if visible:
            self._redraw_pixel_rulers()
        self.show_toast(f"Column ruler {'enabled' if visible else 'hidden'}")
        self._save_user_prefs(silent=True)

    def _update_gutter_clean(self) -> None:
        """Update line numbers in clean dialogue view gutter."""
        if not hasattr(self, "gutter_clean"):
            return
        try:
            total_lines = int(self.txt_dialogue.index("end-1c").split(".")[0])
            numbers = "\n".join(f"{i:>2} " for i in range(1, max(1, total_lines) + 1))
            self.gutter_clean.config(state="normal")
            self.gutter_clean.delete("1.0", tk.END)
            self.gutter_clean.insert("1.0", numbers)
            self._apply_gutter_overflow_tag(self.gutter_clean)
            self.gutter_clean.config(state="disabled")
        except Exception:
            pass

    def _sync_continuous_gutter_scroll(self, *args) -> None:
        """Keep line number gutter perfectly scrolled in lockstep with continuous text."""
        if hasattr(self, "gutter_cont") and self.show_line_numbers:
            try:
                self.gutter_cont.yview_moveto(args[0])
            except Exception:
                pass

    def _on_continuous_vscroll(self, *args) -> None:
        """Handle vertical scrollbar motion for both text and gutter."""
        try:
            self.txt_continuous.yview(*args)
            if hasattr(self, "gutter_cont") and self.show_line_numbers:
                self.gutter_cont.yview(*args)
        except Exception:
            pass

    def _highlight_secret_whitespace(self, text_widget: tk.Text) -> None:
        """Clear any residual whitespace highlighting to prevent visual artifacts."""
        try:
            text_widget.tag_remove("secret_whitespace", "1.0", tk.END)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # NGUI Attributes Ribbon Actions & Compiled Preview Compiler
    # -------------------------------------------------------------------------
    def _shortcut_wrap(self, open_tag: str, close_tag: str) -> str:
        self.apply_ngui_wrapper(open_tag, close_tag)
        return "break"

    def _shortcut_undo(self) -> str:
        self.on_undo()
        return "break"

    def _shortcut_redo(self) -> str:
        self.on_redo()
        return "break"

    def _set_ribbon_colors(self, primary_hex: str, secondary_hex: str) -> None:
        if HEX_COLOR_RE.match(primary_hex):
            self._active_ngui_color = primary_hex.lower()
            if hasattr(self, "btn_ribbon_swatch"):
                self.btn_ribbon_swatch.configure(
                    bg=self._active_ngui_color,
                    activebackground=self._active_ngui_color,
                )
        if HEX_COLOR_RE.match(secondary_hex):
            self._active_ngui_grad_end = secondary_hex.lower()

    def _apply_active_ribbon_color(self) -> None:
        code = self._active_ngui_color[1:].upper()
        self.apply_ngui_wrapper(f"[{code}]", "[-]")

    def _apply_active_ribbon_gradient(self) -> None:
        c0 = self._active_ngui_color[1:].upper()
        c1 = self._active_ngui_grad_end[1:].upper()
        self.apply_ngui_wrapper(f"[{c0}-{c1}]", "[-]")

    def on_open_color_picker(self) -> None:
        self.logger.info(
            "UI / Theme / Config",
            f"Opening NGUI Color & Gradient Picker (primary={self._active_ngui_color}, secondary={self._active_ngui_grad_end})",
        )
        if self._color_picker_win is not None and self._color_picker_win.winfo_exists():
            self._color_picker_win.lift()
            self._color_picker_win.focus_set()
            return
        self._color_picker_win = NguiColorPickerPopup(
            self,
            primary_hex=self._active_ngui_color,
            secondary_hex=self._active_ngui_grad_end,
        )

    def apply_ngui_wrapper(self, open_tag: str, close_tag: str, default_inner: str = "") -> None:
        """Ensure Raw Edit mode is active, then wrap selection or insert NGUI tags at caret."""
        if not getattr(self, "is_box0_active", False) and self.current_doc and self.is_box_locked(self.current_box_idx):
            self.show_toast(f"Box #{self.current_box_idx + 1} is locked.")
            return

        if self.var_preview_compiled.get():
            self.var_preview_compiled.set(False)
            self._update_views()
        if self.var_continuous_view.get() and self.current_doc:
            self.var_continuous_view.set(False)
            self._on_toggle_continuous_view()
        if self.var_continuous_view.get() and self.current_doc:
            self.var_continuous_view.set(False)
            self._on_toggle_continuous_view()
        self._insert_text_wrapper(open_tag, close_tag, default_inner=default_inner)
        target = self._get_active_text_widget()
        if target:
            self._commit_widget_edit(target)

    def _update_top_header_title(self) -> None:
        """Update top view header title according to active view and preview modes (FEAT-03)."""
        if not hasattr(self, "lbl_gd_title"):
            return
        is_cont = bool(getattr(self, "var_continuous_view", None) and self.var_continuous_view.get())
        is_prev = bool(getattr(self, "var_preview_compiled", None) and self.var_preview_compiled.get())
        if is_cont:
            title = "All Script Preview" if is_prev else "All Script"
        else:
            title = "Dialogue Preview" if is_prev else "Dialogue"
        self.lbl_gd_title.config(text=title)

    def _on_toggle_ngui_ribbon(self) -> None:
        """Toggle visibility of the NGUI formatting ribbon docked in ribbon_actions_row (FEAT-04, U12)."""
        if not hasattr(self, "ribbon_frame"):
            return
        if self.var_show_ngui_ribbon.get():
            if hasattr(self, "ribbon_actions_row") and self.ribbon_actions_row.winfo_exists():
                if not self._is_widget_packed(self.ribbon_actions_row):
                    if hasattr(self, "speaker_view_row") and self._is_widget_packed(self.speaker_view_row):
                        self.ribbon_actions_row.pack(fill="x", padx=6, pady=(0, 4), after=self.speaker_view_row)
                    else:
                        self.ribbon_actions_row.pack(fill="x", padx=6, pady=(0, 4))
            if not self._is_widget_packed(self.ribbon_frame):
                self.ribbon_frame.pack(side="left", padx=(0, 4))
        else:
            self.ribbon_frame.pack_forget()
            if hasattr(self, "ribbon_actions_row") and self.ribbon_actions_row.winfo_exists():
                self.ribbon_actions_row.pack_forget()
        self._save_user_prefs(silent=True)

    def _on_dialogue_preview_configure(self, event: Optional[tk.Event] = None) -> None:
        """Keep Dialogue Preview scrollregion synced on resize without accumulating canvas items."""
        if not hasattr(self, "dialogue_preview_canvas") or not self.dialogue_preview_canvas.winfo_exists():
            return
        try:
            bbox = self.dialogue_preview_canvas.bbox("all")
            if bbox:
                self.dialogue_preview_canvas.configure(scrollregion=bbox)
        except Exception:
            pass

    def _hide_dialogue_preview_and_restore_editor(self) -> None:
        """Hide Dialogue Preview canvas and restore ruler_clean above clean_editor_row in exact pack order."""
        if hasattr(self, "dialogue_preview_canvas") and self._is_widget_packed(self.dialogue_preview_canvas):
            self.dialogue_preview_canvas.pack_forget()
        if hasattr(self, "clean_editor_row") and not self._is_widget_packed(self.clean_editor_row):
            if self.show_column_ruler and hasattr(self, "ruler_clean"):
                if self._is_widget_packed(self.ruler_clean):
                    self.ruler_clean.pack_forget()
                self.ruler_clean.pack(side="top", fill="x", pady=(0, 2))
            self.clean_editor_row.pack(fill="both", expand=True)

    def _render_dialogue_preview_frame(self, speaker: str, raw_text: str) -> None:
        """Render clean-room Pillow Priconne-style dialogue frame on single Canvas + embedded read-only Text."""
        if not hasattr(self, "dialogue_preview_canvas") or not self.dialogue_preview_canvas.winfo_exists():
            return

        canvas = self.dialogue_preview_canvas
        txt_w = self.txt_dialogue_preview
        t = self.theme
        d_fam = getattr(self, "dialogue_font_family", self.prefs.get("dialogue_font_family", "Consolas"))
        d_sz = int(getattr(self, "dialogue_font_size", self.prefs.get("dialogue_font_size", 11)))

        canvas.configure(bg=t["bg_panel"])
        canvas.delete("preview_frame")
        canvas.delete("preview_nameplate")
        if hasattr(self, "_dialogue_preview_images"):
            self._dialogue_preview_images.clear()
        else:
            self._dialogue_preview_images = []

        metrics = self._measure_dialogue_metrics(raw_text)
        f = self._get_dialogue_measure_font()
        safe_w = metrics["safe_w"]
        line_h = max(16, int(f.metrics("linespace") or 18) + 4)
        safe_h = line_h * 3

        pad_x = 18
        pad_y = 12
        arrow_safe_zone = 28
        frame_x = 12
        frame_y = 26
        frame_w = safe_w + pad_x * 2 + arrow_safe_zone
        frame_h = safe_h + pad_y * 2

        cream_bg = "#F8F6F0"
        outer_gold = "#C8A86B"
        inner_rim = "#FFFFFF"
        plate_bg = "#C24270"
        plate_fg = best_contrast_fg(plate_bg, "#FFFFFF", "#1A1A1A")
        text_fg = best_contrast_fg(cream_bg, "#333333", "#1A1A1A")
        arrow_fg = "#FF6B9E"

        # Clean-room Pillow rounded capsule (zero AtlasAdv sprites; NO-02)
        cap_img = get_dialogue_capsule_image(
            frame_w, frame_h,
            fill_hex=cream_bg, border_hex=outer_gold, inner_rim_hex=inner_rim,
            radius=16, master=canvas,
        )
        if cap_img is not None:
            self._dialogue_preview_images.append(cap_img)
            canvas.create_image(frame_x, frame_y, image=cap_img, anchor="nw", tags=("preview_frame", "preview_capsule"))
        else:
            canvas.create_rectangle(
                frame_x, frame_y, frame_x + frame_w, frame_y + frame_h,
                fill=cream_bg, outline=outer_gold, width=2, tags=("preview_frame", "preview_capsule"),
            )

        # Subtle safe-area bottom guide inside capsule (ensures >=3 preview_frame items even for narration)
        canvas.create_line(
            frame_x + pad_x, frame_y + frame_h - 4,
            frame_x + frame_w - pad_x, frame_y + frame_h - 4,
            fill="#EAE4D7", width=1, tags="preview_frame",
        )

        # Name plate ONLY when speaker is non-empty (narration has NO nameplate)
        sp_clean = (speaker or "").strip()
        if sp_clean:
            plate_w = max(96, int(f.measure(sp_clean)) + 28)
            plate_h = 24
            plate_x1 = frame_x + 16
            plate_y1 = frame_y - 14
            plate_img = get_dialogue_nameplate_image(
                plate_w, plate_h, fill_hex=plate_bg, border_hex=outer_gold, radius=10, master=canvas,
            )
            if plate_img is not None:
                self._dialogue_preview_images.append(plate_img)
                canvas.create_image(
                    plate_x1, plate_y1, image=plate_img, anchor="nw",
                    tags=("preview_frame", "preview_nameplate"),
                )
            else:
                canvas.create_rectangle(
                    plate_x1, plate_y1, plate_x1 + plate_w, plate_y1 + plate_h,
                    fill=plate_bg, outline=outer_gold, width=1,
                    tags=("preview_frame", "preview_nameplate"),
                )
            canvas.create_text(
                plate_x1 + plate_w // 2, plate_y1 + plate_h // 2,
                text=sp_clean, fill=plate_fg, font=(d_fam, max(8, d_sz - 1), "bold"),
                tags=("preview_frame", "preview_nameplate"),
            )

        # Anti-aliased pink downward triangle with white outline at bottom-right safe corner
        tri_img = get_dialogue_triangle_image(size=16, fill_hex=arrow_fg, outline_hex="#FFFFFF", master=canvas)
        if tri_img is not None:
            self._dialogue_preview_images.append(tri_img)
            canvas.create_image(
                frame_x + frame_w - 18, frame_y + frame_h - 14,
                image=tri_img, anchor="center", tags=("preview_frame", "preview_arrow"),
            )
        else:
            canvas.create_text(
                frame_x + frame_w - 16, frame_y + frame_h - 12,
                text="▼", fill=arrow_fg, font=(d_fam, max(8, d_sz - 2), "bold"),
                tags=("preview_frame", "preview_arrow"),
            )

        # Keep embedded Text strictly inside inner safe zone so it never overlaps ▼ or right/bottom gold border (U-19)
        max_px = max(safe_w, max((ln["pixel_width"] for ln in metrics["lines"]), default=0))
        line_cnt = max(3, metrics["line_count"])
        max_inner_w = max(40, frame_w - pad_x - arrow_safe_zone - 6)
        win_w = min(max_px + 24, max_inner_w)
        max_inner_h = max(24, frame_h - pad_y * 2 - 2)
        txt_x = frame_x + pad_x
        txt_y = frame_y + pad_y

        txt_w.config(state="normal")
        txt_w.configure(
            wrap="none",
            height=min(line_cnt, max(3, max_inner_h // max(1, line_h))),
            font=(d_fam, d_sz),
            bg=cream_bg,
            fg=text_fg,
            selectbackground=t["highlight_bg"],
            selectforeground=t["misora_pink"],
        )
        txt_w.delete("1.0", tk.END)
        self._configure_editor_rich_tags(txt_w, d_fam, d_sz)
        self._insert_compiled_ngui_text(txt_w, "1.0", raw_text)
        if not getattr(self, "is_box0_active", False):
            self._apply_overflow_highlights(txt_w)
        txt_w.config(state="disabled")

        canvas.coords(self._dialogue_preview_win, txt_x, txt_y)
        canvas.itemconfigure(self._dialogue_preview_win, width=win_w, height=max_inner_h)
        canvas.tag_raise(self._dialogue_preview_win)

        total_w = frame_x + frame_w + 16
        total_h = frame_y + frame_h + 16
        canvas.configure(width=total_w, height=total_h, scrollregion=(0, 0, total_w, total_h))

    def _on_toggle_preview_compiled(self) -> None:
        """Toggle between editable raw NGUI tags and compiled visual preview."""
        if self.var_preview_compiled.get():
            if hasattr(self, "txt_dialogue") and self.txt_dialogue.winfo_exists():
                try:
                    caret = self.txt_dialogue.index("insert")
                except tk.TclError:
                    caret = "1.0"
                try:
                    sel_range = (
                        self.txt_dialogue.index("sel.first"),
                        self.txt_dialogue.index("sel.last"),
                    )
                except tk.TclError:
                    sel_range = None
                try:
                    y_top = float(self.txt_dialogue.yview()[0])
                except Exception:
                    y_top = 0.0
                self._preview_saved_editor_state = (
                    self.current_file_path,
                    self.current_box_idx,
                    getattr(self, "is_box0_active", False),
                    caret,
                    sel_range,
                    y_top,
                )
            self.lbl_status.config(
                text="Compiled Attribute Preview ON (read-only) — uncheck 'Compiled' to edit raw tags."
            )
        else:
            self.lbl_status.config(
                text="Raw NGUI Tag Edit Mode active."
            )
        self._update_top_header_title()
        self._update_views()

        if not self.var_preview_compiled.get():
            saved = getattr(self, "_preview_saved_editor_state", None)
            self._preview_saved_editor_state = None
            if (
                saved
                and hasattr(self, "txt_dialogue")
                and self.txt_dialogue.winfo_exists()
                and saved[0] == self.current_file_path
                and saved[1] == self.current_box_idx
                and saved[2] == getattr(self, "is_box0_active", False)
            ):
                _, _, _, caret, sel_range, y_top = saved
                try:
                    self.txt_dialogue.mark_set("insert", caret)
                    if sel_range:
                        self.txt_dialogue.tag_remove("sel", "1.0", tk.END)
                        self.txt_dialogue.tag_add("sel", sel_range[0], sel_range[1])
                    self.txt_dialogue.yview_moveto(y_top)
                except tk.TclError:
                    pass

    def _get_or_create_compiled_style_tag(
        self,
        widget: tk.Text,
        bold: bool,
        italic: bool,
        underline: bool,
        strike: bool,
        sub_mode: int,
        fg_color: Optional[str],
        font_scale: float = 1.0,
    ) -> str:
        """Return a cached Tkinter tag name configured with the requested compiled NGUI style."""
        d_fam = getattr(self, "dialogue_font_family", self.prefs.get("dialogue_font_family", "Consolas"))
        d_sz = int(getattr(self, "dialogue_font_size", self.prefs.get("dialogue_font_size", 11)))
        eff_sz = max(7, d_sz - 2) if sub_mode != 0 else d_sz
        if font_scale != 1.0:
            eff_sz = max(7, int(round(eff_sz * font_scale)))
        eff_offset = -3 if sub_mode < 0 else (4 if sub_mode > 0 else 0)
        color_key = fg_color.lower() if fg_color else "default"
        tag_name = f"cstyle_{int(bold)}_{int(italic)}_{int(underline)}_{int(strike)}_{sub_mode}_{color_key}_{d_fam}_{eff_sz}"

        if tag_name not in widget.tag_names():
            weight = "bold" if bold else "normal"
            slant = "italic" if italic else "roman"
            font_tuple = (d_fam, eff_sz, weight, slant)
            cfg: Dict[str, Any] = {
                "font": font_tuple,
                "underline": underline,
                "overstrike": strike,
                "offset": eff_offset,
            }
            if fg_color:
                cfg["foreground"] = fg_color
            widget.tag_configure(tag_name, **cfg)
        return tag_name

    def _insert_compiled_ngui_text(
        self,
        widget: tk.Text,
        insert_pos: str,
        raw_text: str,
        base_tags: Tuple[str, ...] = (),
    ) -> None:
        """Parse NGUI/Priconne markup in `raw_text` and insert compiled rich text into `widget`."""
        mark_name = f"_compile_ins_{id(widget)}"
        widget.mark_set(mark_name, insert_pos)
        widget.mark_gravity(mark_name, tk.RIGHT)

        bold = False
        italic = False
        underline = False
        strike = False
        sub_mode = 0
        font_scale = 1.0
        color_stack: List[Tuple[str, Optional[str]]] = []

        def emit_styled_run(chunk: str) -> None:
            if not chunk:
                return
            chunk = chunk.replace("\\n", "\n")
            if not color_stack:
                st = self._get_or_create_compiled_style_tag(
                    widget, bold, italic, underline, strike, sub_mode, None, font_scale
                )
                widget.insert(mark_name, chunk, base_tags + (st,))
                return

            top_hex, bot_hex = color_stack[-1]
            if not bot_hex or len(chunk) <= 1:
                st = self._get_or_create_compiled_style_tag(
                    widget, bold, italic, underline, strike, sub_mode, top_hex, font_scale
                )
                widget.insert(mark_name, chunk, base_tags + (st,))
                return

            r1, g1, b1 = int(top_hex[1:3], 16), int(top_hex[3:5], 16), int(top_hex[5:7], 16)
            r2, g2, b2 = int(bot_hex[1:3], 16), int(bot_hex[3:5], 16), int(bot_hex[5:7], 16)
            denom = max(1, len(chunk) - 1)
            for idx, ch in enumerate(chunk):
                ratio = idx / denom
                ri = int(round(r1 + (r2 - r1) * ratio))
                gi = int(round(g1 + (g2 - g1) * ratio))
                bi = int(round(b1 + (b2 - b1) * ratio))
                step_hex = f"#{ri:02x}{gi:02x}{bi:02x}"
                st = self._get_or_create_compiled_style_tag(
                    widget, bold, italic, underline, strike, sub_mode, step_hex, font_scale
                )
                widget.insert(mark_name, ch, base_tags + (st,))

        last_idx = 0
        try:
            for m in NGUI_TOKEN_RE.finditer(raw_text):
                if m.start() > last_idx:
                    emit_styled_run(raw_text[last_idx:m.start()])

                tok = m.group(0)
                tok_low = tok.lower()

                if m.group(2) is not None:
                    ruby_txt = m.group(2).replace("\\n", "\n")
                    base_txt = m.group(3)
                    emit_styled_run(base_txt)
                    if ruby_txt:
                        widget.insert(mark_name, ruby_txt, base_tags + ("compiled_ruby",))
                elif tok_low == "[b]":
                    bold = True
                elif tok_low == "[/b]":
                    bold = False
                elif tok_low == "[i]":
                    italic = True
                elif tok_low == "[/i]":
                    italic = False
                elif tok_low == "[u]":
                    underline = True
                elif tok_low == "[/u]":
                    underline = False
                elif tok_low == "[s]":
                    strike = True
                elif tok_low == "[/s]":
                    strike = False
                elif tok_low == "[sub]":
                    sub_mode = -1
                elif tok_low == "[/sub]":
                    sub_mode = 0
                elif tok_low == "[sup]":
                    sub_mode = 1
                elif tok_low == "[/sup]":
                    sub_mode = 0
                elif tok_low.startswith("<size=") or tok_low.startswith("[size="):
                    try:
                        val = tok[6:-1].strip()
                        if val.endswith("%"):
                            font_scale = max(0.5, min(3.0, float(val[:-1]) / 100.0))
                        else:
                            base_d_sz = int(self.prefs.get("dialogue_font_size", 12))
                            font_scale = max(0.5, min(3.0, float(val) / base_d_sz))
                    except Exception:
                        font_scale = 1.0
                elif tok_low in ("</size>", "[/size]"):
                    font_scale = 1.0
                elif tok_low == "[/]":
                    bold = False
                    italic = False
                    underline = False
                    strike = False
                    sub_mode = 0
                    font_scale = 1.0
                elif tok_low in ("[c]", "[/c]", "[/url]") or tok_low.startswith("[url="):
                    pass
                elif tok == "[-]":
                    if color_stack:
                        color_stack.pop()
                elif m.group(4) is not None:
                    c1 = "#" + m.group(4).lower()[:6]
                    c2 = ("#" + m.group(5).lower()[:6]) if m.group(5) else None
                    color_stack.append((c1, c2))
                elif tok in ("{playername}", "{0}"):
                    widget.insert(mark_name, "{playername}", base_tags + ("compiled_player",))
                else:
                    emit_styled_run(tok)

                last_idx = m.end()

            if last_idx < len(raw_text):
                emit_styled_run(raw_text[last_idx:])
        finally:
            try:
                widget.mark_unset(mark_name)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Embedded Side Drawer: Customization & NGUI Glossary Help
    # -------------------------------------------------------------------------
    def _build_side_drawer(self) -> None:
        """Build dockable right-hand side panel for Display Customization & NGUI Glossary."""
        t = self.theme
        self.side_drawer = self._tag_role(tk.Frame(self.h_paned, bg=t["bg_panel"]), "panel")

        drawer_top = self._tag_role(tk.Frame(self.side_drawer, bg=t["bg_panel"]), "panel")
        drawer_top.pack(fill="x", padx=6, pady=(6, 4))

        self.btn_tab_customize = ttk.Button(
            drawer_top,
            text="Customize",
            style="Pink.TButton",
            command=lambda: self._switch_side_drawer_tab("customize"),
        )
        self.btn_tab_customize.pack(side="left", padx=(0, 4))

        self.btn_tab_glossary = ttk.Button(
            drawer_top,
            text="NGUI Glossary",
            style="TButton",
            command=lambda: self._switch_side_drawer_tab("glossary"),
        )
        self.btn_tab_glossary.pack(side="left")

        self.btn_tab_mtl = ttk.Button(
            drawer_top,
            text="MTL",
            style="TButton",
            command=lambda: self._switch_side_drawer_tab("mtl"),
        )
        self.btn_tab_mtl.pack(side="left", padx=(4, 0))
        create_tooltip(self.btn_tab_mtl, "Machine Translation Drawer (Ctrl+T)")

        self.btn_close_drawer = ttk.Button(
            drawer_top,
            text="✕",
            style="Small.TButton",
            command=self._close_side_drawer,
            width=2,
        )
        self.btn_close_drawer.pack(side="right", padx=(2, 0))
        create_tooltip(self.btn_close_drawer, "Close Side Panel")

        self.btn_drawer_pin = ttk.Button(
            drawer_top,
            text="📌",
            style="Small.TButton",
            command=self._toggle_side_drawer_pin,
            width=3,
        )
        self.btn_drawer_pin.pack(side="right", padx=(2, 2))
        create_tooltip(self.btn_drawer_pin, "Pin / Unpin Side Panel")

        self.tab_customize_frame = self._tag_role(tk.Frame(self.side_drawer, bg=t["bg_panel"]), "panel")
        self._build_customize_tab(self.tab_customize_frame)

        self.tab_glossary_frame = self._tag_role(tk.Frame(self.side_drawer, bg=t["bg_panel"]), "panel")
        self._build_glossary_tab(self.tab_glossary_frame)

        self.tab_mtl_frame = self._tag_role(tk.Frame(self.side_drawer, bg=t["bg_panel"]), "panel")
        self._build_mtl_tab(self.tab_mtl_frame)

        self._switch_side_drawer_tab("customize")

    def _build_customize_tab(self, parent: tk.Frame) -> None:
        """Populate font size controls, theme presets, and custom color pickers."""
        t = self.theme
        wrap = self._tag_role(tk.Frame(parent, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        wrap.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        canvas = self._tag_role(tk.Canvas(wrap, bg=t["bg_panel"], highlightthickness=0, bd=0), "panel")
        vscroll = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=vscroll.set)

        body = self._tag_role(tk.Frame(canvas, bg=t["bg_panel"]), "panel")
        win_id = canvas.create_window((0, 0), window=body, anchor="nw")

        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=max(220, e.width)))

        self._tag_role(
            tk.Label(body, text="FONT & DISPLAY PREFERENCES", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"]),
            "label_accent"
        ).pack(anchor="w", padx=8, pady=(8, 6))

        fam_row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
        fam_row.pack(fill="x", padx=8, pady=3)
        self._tag_role(tk.Label(fam_row, text="Dialogue Font:", bg=t["bg_panel"], fg=t["fg_text"]), "label_panel").pack(side="left")

        cur_font_pref = self.prefs.get("dialogue_font_family", PRESET_GLOBAL)
        preset_init = cur_font_pref if cur_font_pref in BUILTIN_FONT_PRESETS else PRESET_GLOBAL
        self.var_font_family = tk.StringVar(master=self, value=preset_init)
        self.cb_font = ttk.Combobox(
            fam_row,
            textvariable=self.var_font_family,
            values=list(BUILTIN_FONT_PRESETS),
            state="readonly",
            width=30,
        )
        self.cb_font.pack(side="right")
        self.cb_font.bind("<<ComboboxSelected>>", lambda _e: self._on_font_pref_changed())
        create_tooltip(
            self.cb_font,
            "Global server font: Nunito Bold | Japanese server font: nintendoP_Humming-E_002pr\n"
            "(Editor-display-only; never modifies game files.)"
        )

        self._tag_role(
            tk.Label(
                body,
                text="Global server font: Nunito Bold | Japanese server font: nintendoP_Humming-E_002pr",
                bg=t["bg_panel"],
                fg=t["fg_muted"],
                font=("Segoe UI", 8),
                wraplength=280,
                justify="left",
            ),
            "label_muted",
        ).pack(anchor="w", padx=8, pady=(0, 4))

        # Custom Fonts (Advanced) subsection
        self._tag_role(
            tk.Label(body, text="CUSTOM FONTS (ADVANCED)", font=("Segoe UI", 8, "bold"), bg=t["bg_panel"], fg=t["misora_pink"]),
            "label_accent",
        ).pack(anchor="w", padx=8, pady=(6, 2))

        custom_row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
        custom_row.pack(fill="x", padx=8, pady=2)
        self._tag_role(tk.Label(custom_row, text="Custom Font:", bg=t["bg_panel"], fg=t["fg_text"]), "label_panel").pack(side="left")
        custom_vals = list(self.font_manager.custom_families) if hasattr(self, "font_manager") else []
        custom_init = cur_font_pref if cur_font_pref in custom_vals else ""
        self.var_custom_font = tk.StringVar(master=self, value=custom_init)
        self.cb_custom_font = ttk.Combobox(
            custom_row,
            textvariable=self.var_custom_font,
            values=custom_vals,
            state="readonly",
            width=22,
        )
        self.cb_custom_font.pack(side="right")
        self.cb_custom_font.bind("<<ComboboxSelected>>", lambda _e: self._on_custom_font_selected())

        custom_btn_row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
        custom_btn_row.pack(fill="x", padx=8, pady=(2, 6))
        ttk.Button(
            custom_btn_row,
            text="Refresh Fonts",
            style="Small.TButton",
            command=self._refresh_custom_fonts,
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            custom_btn_row,
            text="Open Fonts Folder",
            style="Small.TButton",
            command=self._open_fonts_folder,
        ).pack(side="left")

        self.var_dlg_font_sz = tk.IntVar(master=self, value=int(self.prefs["dialogue_font_size"]))
        self.var_raw_font_sz = tk.IntVar(master=self, value=int(self.prefs["raw_font_size"]))
        self.var_ui_font_sz = tk.IntVar(master=self, value=int(self.prefs["ui_font_size"]))

        font_rows = [
            ("Dialogue Size (pt):", self.var_dlg_font_sz, 8, 28),
            ("Raw Script Size (pt):", self.var_raw_font_sz, 7, 22),
            ("UI & Search Size (pt):", self.var_ui_font_sz, 8, 16),
        ]
        for label_txt, int_var, min_v, max_v in font_rows:
            r = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
            r.pack(fill="x", padx=8, pady=3)
            self._tag_role(tk.Label(r, text=label_txt, bg=t["bg_panel"], fg=t["fg_text"]), "label_panel").pack(side="left")
            sb = tk.Spinbox(
                r,
                from_=min_v,
                to=max_v,
                textvariable=int_var,
                width=6,
                font=("Consolas", 9),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                buttonbackground=t["bg_panel"],
                relief="solid",
                bd=1,
                command=self._on_font_pref_changed,
            )
            sb.pack(side="right")
            sb.bind("<Return>", lambda _e: self._on_font_pref_changed())
            sb.bind("<FocusOut>", lambda _e: self._on_font_pref_changed())

        self._tag_role(
            tk.Label(body, text="THEME PRESETS", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"]),
            "label_accent"
        ).pack(anchor="w", padx=8, pady=(12, 4))

        preset_row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
        preset_row.pack(fill="x", padx=8, pady=3)
        self.var_preset = tk.StringVar(master=self, value=self._detect_active_preset_name())
        cb_preset = ttk.Combobox(
            preset_row,
            textvariable=self.var_preset,
            values=list(THEME_PRESETS.keys()) + ["Custom"],
            state="readonly",
            width=22,
        )
        cb_preset.pack(side="left", fill="x", expand=True, padx=(0, 4))
        cb_preset.bind("<<ComboboxSelected>>", lambda _e: self._apply_theme_preset(self.var_preset.get()))
        ttk.Button(
            preset_row,
            text="Apply",
            style="Small.TButton",
            command=lambda: self._apply_theme_preset(self.var_preset.get()),
        ).pack(side="right")

        self._tag_role(
            tk.Label(body, text="CUSTOM WINDOW COLORS", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"]),
            "label_accent"
        ).pack(anchor="w", padx=8, pady=(12, 4))

        color_specs = [
            ("bg_dark", "Window Background"),
            ("bg_panel", "Panel Surface"),
            ("bg_editor", "Editor Surface"),
            ("misora_pink", "Primary Accent"),
            ("fg_text", "Primary Text"),
            ("fg_muted", "Secondary Text"),
            ("highlight_bg", "Selection / Hit BG"),
            ("border", "Divider / Border"),
        ]

        for key, label_txt in color_specs:
            row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
            row.pack(fill="x", padx=8, pady=3)

            self._tag_role(tk.Label(row, text=label_txt, bg=t["bg_panel"], fg=t["fg_text"]), "label_panel").pack(side="left")

            swatch = tk.Button(
                row,
                width=3,
                bg=t[key],
                activebackground=t[key],
                relief="solid",
                bd=1,
                cursor="hand2",
                command=lambda k=key: self._pick_theme_color(k),
            )
            swatch.pack(side="right", padx=(4, 0))
            self._theme_swatch_buttons[key] = swatch

            hvar = tk.StringVar(master=self, value=t[key])
            self._theme_hex_vars[key] = hvar
            hex_ent = self._tag_role(
                tk.Entry(
                    row,
                    textvariable=hvar,
                    width=9,
                    font=("Consolas", 9),
                    bg=t["bg_editor"],
                    fg=t["fg_text"],
                    insertbackground=t["misora_pink"],
                    bd=1,
                    relief="solid",
                ),
                "entry_editor"
            )
            hex_ent.pack(side="right")
            hex_ent.bind("<Return>", lambda _e, k=key: self._commit_theme_hex(k))
            hex_ent.bind("<FocusOut>", lambda _e, k=key: self._commit_theme_hex(k))

        btn_row = self._tag_role(tk.Frame(body, bg=t["bg_panel"]), "panel")
        btn_row.pack(fill="x", padx=8, pady=(12, 10))
        ttk.Button(
            btn_row,
            text="Reset All to Defaults",
            style="TButton",
            command=self._reset_customization_defaults,
        ).pack(fill="x")

    def _build_glossary_tab(self, parent: tk.Frame) -> None:
        """Populate interactive NGUI Glossary & Syntax Reference panel."""
        t = self.theme
        u_sz = int(self.prefs["ui_font_size"])

        filter_row = self._tag_role(tk.Frame(parent, bg=t["bg_panel"]), "panel")
        filter_row.pack(fill="x", padx=6, pady=(2, 4))

        self._tag_role(tk.Label(filter_row, text="Filter:", bg=t["bg_panel"], fg=t["fg_muted"]), "label_muted").pack(side="left", padx=(0, 4))
        self.var_glossary_filter = tk.StringVar(master=self)
        ent_filter = self._tag_role(
            tk.Entry(
                filter_row,
                textvariable=self.var_glossary_filter,
                font=("Segoe UI", 9),
                bg=t["bg_editor"],
                fg=t["fg_text"],
                insertbackground=t["misora_pink"],
                bd=1,
                relief="solid",
            ),
            "entry_editor"
        )
        ent_filter.pack(side="left", fill="x", expand=True)
        ent_filter.bind("<KeyRelease>", lambda _e: self._filter_glossary())

        list_wrap = self._tag_role(tk.Frame(parent, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        list_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        g_scroll = tk.Scrollbar(list_wrap, orient="vertical")
        g_scroll.pack(side="right", fill="y")

        self.txt_glossary = tk.Text(
            list_wrap,
            wrap="word",
            font=("Segoe UI", u_sz),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            insertwidth=0,
            cursor="hand2",
            padx=8,
            pady=6,
            bd=0,
            relief="flat",
            exportselection=False,
            state="disabled",
            yscrollcommand=g_scroll.set,
        )
        self.txt_glossary.pack(side="left", fill="both", expand=True)
        g_scroll.config(command=self.txt_glossary.yview)

        self.txt_glossary.tag_configure("gl_tag", font=("Consolas", u_sz, "bold"), foreground=t["misora_pink"])
        self.txt_glossary.tag_configure("gl_title", font=("Segoe UI", u_sz, "bold"), foreground=t["fg_text"])
        self.txt_glossary.tag_configure("gl_syntax", font=("Consolas", max(8, u_sz - 1)), foreground=t["accent_blue"])
        self.txt_glossary.tag_configure("gl_desc", font=("Segoe UI", max(8, u_sz - 1)), foreground=t["fg_muted"])
        self.txt_glossary.tag_configure("gl_selected", background=t["highlight_bg"])

        self.txt_glossary.bind("<Button-1>", self._on_glossary_click)
        self.txt_glossary.bind("<Double-Button-1>", self._on_glossary_double_click)

        ins_bar = self._tag_role(tk.Frame(parent, bg=t["bg_panel"]), "panel")
        ins_bar.pack(fill="x", padx=6, pady=(0, 6))

        ttk.Button(
            ins_bar,
            text="Insert / Wrap Selected Tag into Dialogue",
            style="Pink.TButton",
            command=self._insert_selected_glossary_tag,
        ).pack(fill="x")

        self._render_glossary_list()

    def _open_side_drawer(self, tab: str = "customize") -> None:
        if not hasattr(self, "h_paned") or not self.h_paned.winfo_exists():
            return
        if not hasattr(self, "side_drawer") or not self.side_drawer.winfo_exists():
            return
        panes = [str(p) for p in self.h_paned.panes()]
        if not self._side_drawer_visible:
            if str(self.side_drawer) not in panes:
                self.h_paned.add(self.side_drawer, minsize=260, width=330, stretch="never")
            self._side_drawer_visible = True
        self._switch_side_drawer_tab(tab)

    def _close_side_drawer(self) -> None:
        if not hasattr(self, "h_paned") or not self.h_paned.winfo_exists():
            self._side_drawer_visible = False
            return
        if self._side_drawer_visible:
            if hasattr(self, "side_drawer") and self.side_drawer.winfo_exists():
                panes = [str(p) for p in self.h_paned.panes()]
                if str(self.side_drawer) in panes:
                    self.h_paned.forget(self.side_drawer)
            self._side_drawer_visible = False

    def _toggle_side_drawer(self, tab: str) -> None:
        if self._side_drawer_visible and self._side_drawer_tab == tab:
            self._close_side_drawer()
        else:
            self._open_side_drawer(tab)

    def _switch_side_drawer_tab(self, tab: str) -> None:
        self._side_drawer_tab = tab
        for frame in (
            getattr(self, "tab_customize_frame", None),
            getattr(self, "tab_glossary_frame", None),
            getattr(self, "tab_mtl_frame", None),
        ):
            if frame is not None:
                frame.pack_forget()
        for btn in (
            getattr(self, "btn_tab_customize", None),
            getattr(self, "btn_tab_glossary", None),
            getattr(self, "btn_tab_mtl", None),
        ):
            if btn is not None:
                btn.configure(style="TButton")

        if tab == "customize":
            self.tab_customize_frame.pack(fill="both", expand=True)
            self.btn_tab_customize.configure(style="Pink.TButton")
        elif tab == "mtl":
            self.tab_mtl_frame.pack(fill="both", expand=True)
            self.btn_tab_mtl.configure(style="Pink.TButton")
            self._refresh_mtl_drawer_box()
        else:
            self.tab_glossary_frame.pack(fill="both", expand=True)
            self.btn_tab_glossary.configure(style="Pink.TButton")

    def _on_font_pref_changed(self) -> None:
        """Apply updated font family / size values from Customize panel."""
        fam = self.var_font_family.get().strip() or self.prefs["dialogue_font_family"]
        if hasattr(self, "var_custom_font") and fam in BUILTIN_FONT_PRESETS:
            self.var_custom_font.set("")
        try:
            d_sz = max(8, min(28, int(self.var_dlg_font_sz.get())))
        except Exception:
            d_sz = int(self.prefs["dialogue_font_size"])
            self.var_dlg_font_sz.set(d_sz)

        try:
            r_sz = max(7, min(22, int(self.var_raw_font_sz.get())))
        except Exception:
            r_sz = int(self.prefs["raw_font_size"])
            self.var_raw_font_sz.set(r_sz)

        try:
            u_sz = max(8, min(16, int(self.var_ui_font_sz.get())))
        except Exception:
            u_sz = int(self.prefs["ui_font_size"])
            self.var_ui_font_sz.set(u_sz)

        self.prefs["dialogue_font_family"] = fam
        self.prefs["dialogue_font_size"] = d_sz
        self.prefs["raw_font_size"] = r_sz
        self.prefs["ui_font_size"] = u_sz
        self._apply_theme_and_fonts_live(save=True)

    def _on_custom_font_selected(self) -> None:
        """Select a user-managed custom font from assets/fonts or custom_fonts.txt."""
        if not hasattr(self, "var_custom_font"):
            return
        fam = self.var_custom_font.get().strip()
        if not fam:
            return
        self.prefs["dialogue_font_family"] = fam
        self._apply_theme_and_fonts_live(save=True)

    def _refresh_custom_fonts(self) -> None:
        """Rescan assets/fonts/ for .ttf/.otf and custom_fonts.txt without Admin rights."""
        if not hasattr(self, "font_manager"):
            return
        fams = self.font_manager.refresh()
        if hasattr(self, "cb_custom_font"):
            self.cb_custom_font.configure(values=fams)
        if self.font_manager.load_errors:
            self.set_status(self.font_manager.load_errors[0], is_error=True)
        else:
            self.show_toast(f"Loaded {len(fams)} custom font(s).")
        self._apply_theme_and_fonts_live(save=False)

    def _open_fonts_folder(self) -> None:
        """Create assets/fonts/ if missing and open it in the file explorer."""
        fonts_dir = SCRIPT_DIR / "assets" / "fonts"
        try:
            fonts_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(str(fonts_dir))
            else:
                self.set_status(f"Fonts folder: {fonts_dir}")
        except Exception as exc:
            self.set_status(f"Could not open fonts folder: {exc}", is_error=True)

    def _adjust_dialogue_font_size(self, delta: int) -> None:
        cur = int(self.prefs["dialogue_font_size"])
        new_sz = max(8, min(28, cur + delta))
        self.prefs["dialogue_font_size"] = new_sz
        if hasattr(self, "var_dlg_font_sz"):
            self.var_dlg_font_sz.set(new_sz)
        self._apply_theme_and_fonts_live(save=True)

    def _pick_theme_color(self, key: str) -> None:
        cur = self.theme.get(key, "#ffffff")
        chosen = colorchooser.askcolor(color=cur, title=f"Select Color ({key})", parent=self)
        if chosen and chosen[1]:
            hex_val = chosen[1].lower()
            self.theme[key] = hex_val
            if key in self._theme_hex_vars:
                self._theme_hex_vars[key].set(hex_val)
            if key in self._theme_swatch_buttons:
                self._theme_swatch_buttons[key].configure(bg=hex_val, activebackground=hex_val)
            if key == "misora_pink":
                self.theme["misora_pink_hover"] = self._shift_hex(hex_val, 22)
                self.theme["misora_pink_active"] = self._shift_hex(hex_val, -26)
            if hasattr(self, "var_preset"):
                self.var_preset.set(self._detect_active_preset_name())
            self._apply_theme_and_fonts_live(save=True)

    def _commit_theme_hex(self, key: str) -> None:
        hvar = self._theme_hex_vars.get(key)
        if not hvar:
            return
        val = hvar.get().strip()
        if not val.startswith("#"):
            val = "#" + val
        if HEX_COLOR_RE.match(val):
            hex_val = val.lower()
            if self.theme.get(key, "").lower() != hex_val:
                self.theme[key] = hex_val
                if key in self._theme_swatch_buttons:
                    self._theme_swatch_buttons[key].configure(bg=hex_val, activebackground=hex_val)
                if key == "misora_pink":
                    self.theme["misora_pink_hover"] = self._shift_hex(hex_val, 22)
                    self.theme["misora_pink_active"] = self._shift_hex(hex_val, -26)
                if hasattr(self, "var_preset"):
                    self.var_preset.set(self._detect_active_preset_name())
                self._apply_theme_and_fonts_live(save=True)
        else:
            hvar.set(self.theme.get(key, ""))

    def _apply_theme_preset(self, preset_name: str) -> None:
        for key in getattr(self, "_theme_hex_vars", {}):
            self._commit_theme_hex(key)
        if preset_name == "Custom":
            self._apply_theme_and_fonts_live(save=True)
            self.lbl_status.config(text="Applied custom theme colors.")
            self.logger.info("UI / Theme / Config", "Applied custom theme colors.")
            return
        preset = THEME_PRESETS.get(preset_name)
        if not preset:
            return
        self.theme.update(preset)
        if hasattr(self, "var_preset"):
            self.var_preset.set(preset_name)
        for key, hvar in getattr(self, "_theme_hex_vars", {}).items():
            if key in self.theme:
                hvar.set(self.theme[key])
            if key in getattr(self, "_theme_swatch_buttons", {}):
                self._theme_swatch_buttons[key].configure(bg=self.theme[key], activebackground=self.theme[key])
        self._apply_theme_and_fonts_live(save=True)
        self.lbl_status.config(text=f"Applied theme preset: {preset_name}")
        self.logger.info("UI / Theme / Config", f"Applied theme preset '{preset_name}'")

    def _reset_customization_defaults(self) -> None:
        self.prefs["dialogue_font_family"] = DEFAULT_PREFS["dialogue_font_family"]
        self.prefs["dialogue_font_size"] = DEFAULT_PREFS["dialogue_font_size"]
        self.prefs["raw_font_size"] = DEFAULT_PREFS["raw_font_size"]
        self.prefs["ui_font_size"] = DEFAULT_PREFS["ui_font_size"]
        self.theme.clear()
        self.theme.update(DEFAULT_PREFS["theme"])

        if hasattr(self, "var_font_family"):
            self.var_font_family.set(self.prefs["dialogue_font_family"])
            if hasattr(self, "var_custom_font"):
                self.var_custom_font.set("")
            self.var_dlg_font_sz.set(self.prefs["dialogue_font_size"])
            self.var_raw_font_sz.set(self.prefs["raw_font_size"])
            self.var_ui_font_sz.set(self.prefs["ui_font_size"])
            self.var_preset.set("Misora Purple & White")

        for key, hvar in getattr(self, "_theme_hex_vars", {}).items():
            if key in self.theme:
                hvar.set(self.theme[key])
        self._apply_theme_and_fonts_live(save=True)
        self.lbl_status.config(text="Reset display fonts and theme colors to Misora Purple & White default.")
        self.logger.info("UI / Theme / Config", "Reset display fonts and theme colors to default.")

    def _filter_glossary(self) -> None:
        q = self.var_glossary_filter.get().strip().lower()
        if not q:
            self._filtered_glossary_items = list(NGUI_GLOSSARY_ITEMS)
        else:
            self._filtered_glossary_items = [
                item for item in NGUI_GLOSSARY_ITEMS
                if q in item["tag"].lower()
                or q in item["title"].lower()
                or q in item["syntax"].lower()
                or q in item["desc"].lower()
            ]
        self._selected_glossary_idx = 0
        self._render_glossary_list()

    def _render_glossary_list(self) -> None:
        self._glossary_line_map.clear()
        self.txt_glossary.config(state="normal")
        self.txt_glossary.delete("1.0", tk.END)

        line_no = 1
        for idx, item in enumerate(self._filtered_glossary_items):
            sel_tags = ("gl_selected",) if idx == self._selected_glossary_idx else ()
            start_line = line_no

            self.txt_glossary.insert(f"{line_no}.0", f"{item['tag']}  ", ("gl_tag",) + sel_tags)
            self.txt_glossary.insert(f"{line_no}.end", f"{item['title']}\n", ("gl_title",) + sel_tags)
            line_no += 1

            self.txt_glossary.insert(f"{line_no}.0", f"  Example: {item['syntax']}\n", ("gl_syntax",) + sel_tags)
            line_no += 1

            self.txt_glossary.insert(f"{line_no}.0", f"  {item['desc']}\n\n", ("gl_desc",) + sel_tags)
            for ln in range(start_line, line_no + 1):
                self._glossary_line_map[ln] = idx
            line_no += 2

        self.txt_glossary.config(state="disabled")

    def _on_glossary_click(self, event: tk.Event) -> str:
        idx_str = self.txt_glossary.index(f"@{event.x},{event.y}")
        line_no = int(idx_str.split(".")[0])
        item_idx = self._glossary_line_map.get(line_no)
        if item_idx is not None:
            self._selected_glossary_idx = item_idx
            self._render_glossary_list()
        return "break"

    def _on_glossary_double_click(self, event: tk.Event) -> str:
        self._on_glossary_click(event)
        self._insert_selected_glossary_tag()
        return "break"

    def _insert_selected_glossary_tag(self) -> None:
        """Insert or wrap selected dialogue text with the chosen NGUI tag."""
        if not self._filtered_glossary_items:
            return
        idx = max(0, min(self._selected_glossary_idx, len(self._filtered_glossary_items) - 1))
        item = self._filtered_glossary_items[idx]

        if item.get("action") == "ruby":
            self.on_insert_ruby()
            return

        open_tag = item["insert_open"]
        close_tag = item["insert_close"]
        self.apply_ngui_wrapper(open_tag, close_tag)

    def _insert_text_wrapper(self, open_tag: str, close_tag: str, default_inner: str = "") -> None:
        """Wrap the current selection (or insert at caret) in the active dialogue editor."""
        self._current_edit_source = "format"
        try:
            if self.is_box0_active and not self.var_continuous_view.get():
                target = self.txt_box0_summary
                try:
                    sel_first = target.index("sel.first")
                    sel_last = target.index("sel.last")
                    selected_txt = target.get(sel_first, sel_last)
                    target.delete(sel_first, sel_last)
                    target.insert(sel_first, f"{open_tag}{selected_txt}{close_tag}")
                except tk.TclError:
                    target.insert(tk.INSERT, f"{open_tag}{default_inner}{close_tag}")
                self._on_box0_metadata_edited()
                target.focus_set()
                return

            if self.var_continuous_view.get():
                if hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
                    target = self._get_card_text_widget(self.current_box_idx)
                    try:
                        sel_first = target.index("sel.first")
                        sel_last = target.index("sel.last")
                        selected_txt = target.get(sel_first, sel_last)
                        target.delete(sel_first, sel_last)
                        target.insert(sel_first, f"{open_tag}{selected_txt}{close_tag}")
                    except tk.TclError:
                        target.insert(tk.INSERT, f"{open_tag}{default_inner}{close_tag}")
                    target.focus_set()
                else:
                    target = self.txt_continuous
                    box_idx = self._find_continuous_box_at_index("insert")
                    if box_idx is None:
                        self._focus_continuous_box(self.current_box_idx, move_cursor=True)
                    try:
                        sel_first = target.index("sel.first")
                        sel_last = target.index("sel.last")
                        b1 = self._find_continuous_box_at_index(sel_first)
                        b2 = self._find_continuous_box_at_index(sel_last)
                        if b1 is not None and b1 == b2:
                            selected_txt = target.get(sel_first, sel_last)
                            target.delete(sel_first, sel_last)
                            target.insert(sel_first, f"{open_tag}{selected_txt}{close_tag}")
                        else:
                            target.insert(tk.INSERT, f"{open_tag}{default_inner}{close_tag}")
                    except tk.TclError:
                        target.insert(tk.INSERT, f"{open_tag}{default_inner}{close_tag}")
                    self._sync_continuous_box_from_widget()
                    target.focus_set()
            else:
                target = self.txt_dialogue
                try:
                    sel_first = target.index("sel.first")
                    sel_last = target.index("sel.last")
                    selected_txt = target.get(sel_first, sel_last)
                    target.delete(sel_first, sel_last)
                    target.insert(sel_first, f"{open_tag}{selected_txt}{close_tag}")
                except tk.TclError:
                    target.insert(tk.INSERT, f"{open_tag}{default_inner}{close_tag}")
                target.focus_set()
        finally:
            self._current_edit_source = "keyboard"

    def on_insert_ruby(self) -> None:
        """Open a compact modal prompt to wrap base text with [rub:ruby]base[/rub]."""
        if not getattr(self, "is_box0_active", False) and self.current_doc and self.is_box_locked(self.current_box_idx):
            self.show_toast(f"Box #{self.current_box_idx + 1} is locked.")
            return

        if self.var_preview_compiled.get():
            self.var_preview_compiled.set(False)
            self._update_views()
        if self.var_continuous_view.get() and self.current_doc:
            self.var_continuous_view.set(False)
            self._on_toggle_continuous_view()

        selected_base = ""
        if self.var_continuous_view.get():
            if hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
                target = self._get_card_text_widget(self.current_box_idx)
                try:
                    selected_base = target.get("sel.first", "sel.last")
                except tk.TclError:
                    pass
            else:
                target = self.txt_continuous
                try:
                    sel_first = target.index("sel.first")
                    sel_last = target.index("sel.last")
                    b1 = self._find_continuous_box_at_index(sel_first)
                    b2 = self._find_continuous_box_at_index(sel_last)
                    if b1 is not None and b1 == b2:
                        selected_base = target.get(sel_first, sel_last)
                except tk.TclError:
                    pass
        else:
            target = self.txt_dialogue
            try:
                selected_base = target.get("sel.first", "sel.last")
            except tk.TclError:
                pass

        t = self.theme
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        dlg = tk.Toplevel(self)
        dlg.title("Insert Ruby / Furigana ([rub:...]...[/rub])")
        dlg.configure(bg=t["bg_panel"])
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 190
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 105
        dlg.geometry(f"380x210+{max(20, x)}+{max(20, y)}")

        tk.Label(
            dlg,
            text="Priconne NGUI Ruby Text ([rub:ruby]base[/rub])",
            font=("Segoe UI", 9, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w", padx=14, pady=(12, 8))

        row_base = tk.Frame(dlg, bg=t["bg_panel"])
        row_base.pack(fill="x", padx=14, pady=4)
        tk.Label(row_base, text="Base Text (Main):", width=16, anchor="w", bg=t["bg_panel"], fg=panel_fg).pack(side="left")
        var_base = tk.StringVar(master=dlg, value=selected_base)
        ent_base = tk.Entry(
            row_base,
            textvariable=var_base,
            font=("Segoe UI", 10),
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        ent_base.pack(side="left", fill="x", expand=True)

        row_ruby = tk.Frame(dlg, bg=t["bg_panel"])
        row_ruby.pack(fill="x", padx=14, pady=4)
        tk.Label(row_ruby, text="Ruby Text (Top):", width=16, anchor="w", bg=t["bg_panel"], fg=panel_fg).pack(side="left")
        var_ruby = tk.StringVar(master=dlg)
        ent_ruby = tk.Entry(
            row_ruby,
            textvariable=var_ruby,
            font=("Segoe UI", 10),
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        ent_ruby.pack(side="left", fill="x", expand=True)

        lbl_preview = tk.Label(
            dlg,
            text=f"Preview: [rub:]{selected_base}[/rub]",
            font=("Consolas", 9),
            bg=t["bg_panel"],
            fg=t["accent_blue"],
            anchor="w",
        )
        lbl_preview.pack(fill="x", padx=14, pady=(8, 10))

        def _update_preview(*_args: Any) -> None:
            lbl_preview.config(text=f"Preview: [rub:{var_ruby.get()}]{var_base.get()}[/rub]")

        var_base.trace_add("write", _update_preview)
        var_ruby.trace_add("write", _update_preview)

        def _safe_close(_event: Optional[tk.Event] = None) -> None:
            safe_grab_release(dlg)
            if dlg.winfo_exists():
                dlg.destroy()

        def _commit(_event: Optional[tk.Event] = None) -> None:
            r_txt = var_ruby.get().strip()
            b_txt = var_base.get()
            _safe_close()
            if not b_txt and not r_txt:
                return
            if selected_base:
                self._insert_text_wrapper(f"[rub:{r_txt}]", "[/rub]")
            else:
                self._insert_text_wrapper(f"[rub:{r_txt}]", "[/rub]", default_inner=b_txt)
            target = self._get_active_text_widget()
            if target:
                self._commit_widget_edit(target)

        btn_row = tk.Frame(dlg, bg=t["bg_panel"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(btn_row, text="Cancel", style="TButton", command=_safe_close).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="Insert Ruby Tag", style="Pink.TButton", command=_commit).pack(side="right")

        dlg.protocol("WM_DELETE_WINDOW", _safe_close)
        dlg.bind("<Return>", _commit)
        dlg.bind("<Escape>", _safe_close)
        (ent_ruby if selected_base else ent_base).focus_set()

    _prompt_insert_ruby = on_insert_ruby

    def _highlight_ngui_tags(self) -> None:
        """Apply non-destructive syntax coloring to NGUI & Priconne ruby tags."""
        if self.var_preview_compiled.get():
            return

        self.txt_dialogue.tag_remove("ngui_tag", "1.0", tk.END)
        text = self.txt_dialogue.get("1.0", "end-1c")
        for m in NGUI_TAG_RE.finditer(text):
            self.txt_dialogue.tag_add("ngui_tag", f"1.0 + {m.start()}c", f"1.0 + {m.end()}c")
        self._apply_overflow_highlights(self.txt_dialogue)
        self.txt_dialogue.tag_raise("search_hit")

        self.txt_continuous.tag_remove("ngui_tag", "1.0", tk.END)
        if not self.current_doc or not self.current_doc.boxes:
            cont_tx = self.txt_continuous.get("1.0", "end-1c")
            for m in NGUI_TAG_RE.finditer(cont_tx):
                self.txt_continuous.tag_add("ngui_tag", f"1.0 + {m.start()}c", f"1.0 + {m.end()}c")
        else:
            marks = set(self.txt_continuous.mark_names())
            for i in range(len(self.current_doc.boxes)):
                s_mark = f"box_start_{i}"
                e_mark = f"box_end_{i}"
                if s_mark in marks and e_mark in marks:
                    box_tx = self.txt_continuous.get(s_mark, e_mark)
                    for m in NGUI_TAG_RE.finditer(box_tx):
                        self.txt_continuous.tag_add(
                            "ngui_tag",
                            f"{s_mark} + {m.start()}c",
                            f"{s_mark} + {m.end()}c",
                        )
        self.txt_continuous.tag_raise("ngui_tag")
        self.txt_continuous.tag_raise("search_hit")

    def _sync_gd_scroll_bounds(self, _event: Optional[tk.Event] = None) -> None:
        """Keep Game Display canvas width matched to viewport and clamp scrollregion."""
        canvas_w = max(240, self.gd_canvas.winfo_width())
        canvas_h = max(80, self.gd_canvas.winfo_height())
        self.gd_canvas.itemconfigure(self._gd_canvas_win, width=canvas_w)

        req_h = self.gd_inner.winfo_reqheight()
        bound_h = max(req_h, canvas_h)
        self.gd_canvas.configure(scrollregion=(0, 0, canvas_w, bound_h))

        if req_h <= canvas_h:
            self.gd_canvas.yview_moveto(0.0)

    def _on_gd_scrollbar(self, *args: Any) -> None:
        """Scrollbar callback clamped strictly within [0.0, 1.0]."""
        self.gd_canvas.yview(*args)
        top, _ = self.gd_canvas.yview()
        if top < 0.0:
            self.gd_canvas.yview_moveto(0.0)

    def _on_gd_mousewheel(self, event: tk.Event) -> Optional[str]:
        """Smoothly scroll Game Display canvas within bounded upper/lower limits."""
        canvas_h = self.gd_canvas.winfo_height()
        req_h = self.gd_inner.winfo_reqheight()
        if req_h <= canvas_h:
            self.gd_canvas.yview_moveto(0.0)
            return "break"

        delta = -1 if event.delta > 0 else 1
        top, bottom = self.gd_canvas.yview()
        if delta < 0 and top <= 0.0:
            self.gd_canvas.yview_moveto(0.0)
            return "break"
        if delta > 0 and bottom >= 1.0:
            return "break"

        self.gd_canvas.yview_scroll(delta * 2, "units")
        new_top, _ = self.gd_canvas.yview()
        if new_top < 0.0:
            self.gd_canvas.yview_moveto(0.0)
        return "break"

    def _auto_resize_dialogue_box(self) -> None:
        """Adjust dialogue editor line height to fit multi-line text comfortably inside scroll bounds."""
        content = self.txt_dialogue.get("1.0", "end-1c")
        lines = content.split("\n")
        est_visual_lines = sum(max(1, (len(ln) // 68) + 1) for ln in lines)
        target_lines = max(7, min(32, est_visual_lines + 1))
        self.txt_dialogue.configure(height=target_lines)
        self.gd_inner.update_idletasks()
        self._sync_gd_scroll_bounds()

    def _on_toggle_continuous_view(self) -> None:
        """Switch Game Display between Page-by-Page mode and All Script (Technique A) with box & caret sync."""
        if self.var_continuous_view.get():
            char_offset = 0
            try:
                target_w = self.txt_box0_summary if self.is_box0_active else self.txt_dialogue
                diff = target_w.count("1.0", "insert", "chars")
                char_offset = max(0, diff[0] if diff else 0)
            except Exception:
                char_offset = 0

            self.gd_scroll_wrap.pack_forget()
            self.continuous_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 6))
            self._update_top_header_title()
            self._update_views()
            target_idx = -1 if self.is_box0_active else self.current_box_idx
            self.after(50, lambda: self._focus_continuous_box(target_idx, move_cursor=True, char_offset=char_offset))
        else:
            # 1. Flush any uncommitted plain-text edits
            self._flush_continuous_card_edits()

            # 2. Extract char offset from active editor if applicable
            char_offset = 0
            if not self.current_doc and hasattr(self, "txt_continuous"):
                try:
                    diff = self.txt_continuous.count("1.0", "insert", "chars")
                    char_offset = max(0, diff[0] if diff else 0)
                except Exception:
                    char_offset = 0

            self.continuous_wrap.pack_forget()
            self.gd_scroll_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))
            self._update_top_header_title()
            self._update_views()

            try:
                target_w = self.txt_box0_summary if self.is_box0_active else self.txt_dialogue
                target_w.mark_set("insert", f"1.0 + {max(0, char_offset)}c")
                target_w.see("insert")
                target_w.focus_set()
            except Exception:
                pass

        if hasattr(self, "_set_mtl_drawer_mode"):
            self._set_mtl_drawer_mode("all_script" if self.var_continuous_view.get() else "dialogue")

    # -------------------------------------------------------------------------
    # Status & Action Bar
    # -------------------------------------------------------------------------
    def _build_status_bar(self) -> None:
        t = self.theme
        action_bar = self._tag_role(
            tk.Frame(self, bg=t["bg_panel"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "panel_box"
        )
        action_bar.pack(fill="x", padx=8, pady=(0, 6))

        self.lbl_status = self._tag_role(
            tk.Label(action_bar, text=getattr(self, "_default_status_text", "Ready. Drag & Drop or open a .unity3d bundle or folder to begin."), font=("Segoe UI", 9), bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        )
        self.lbl_status.pack(side="left", padx=8, pady=6)

        self.var_sync_xuat = tk.BooleanVar(master=self, value=True)
        cb_sync = ttk.Checkbutton(
            action_bar,
            text="Also update matching XUAT .txt dictionary on Save",
            variable=self.var_sync_xuat,
            style="Panel.TCheckbutton"
        )
        cb_sync.pack(side="right", padx=(8, 12))

        self.ico_revert = self.get_icon("revert", (15, 15))
        btn_revert = ttk.Button(action_bar, text=" Revert Box", image=self.ico_revert, compound="left", style="TButton", command=self.on_revert_box)
        btn_revert.pack(side="right", padx=4)

        self.ico_save = self.get_icon("save", (15, 15))
        self.btn_save = ttk.Button(action_bar, text=" Save & Patch Bundle (Ctrl+S)", image=self.ico_save, compound="left", style="Pink.TButton", command=self.on_save)
        self.btn_save.pack(side="right", padx=4)

    def _get_active_text_widget(self) -> Optional[tk.Text]:
        """Resolve the currently active or focused Text widget safely without aliasing (Rule 3)."""
        focused = self.focus_get()
        if isinstance(focused, tk.Text):
            return focused
        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
            if getattr(self, "is_box0_active", False) and hasattr(self, "_card_widgets") and -1 in self._card_widgets:
                card_txt = self._card_widgets[-1].get("txt")
                if card_txt and card_txt.winfo_exists():
                    return card_txt
            if hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
                card_txt = self._card_widgets[self.current_box_idx].get("txt")
                if card_txt and card_txt.winfo_exists():
                    return card_txt
            if hasattr(self, "txt_continuous") and self.txt_continuous.winfo_exists():
                return self.txt_continuous
        if getattr(self, "is_box0_active", False) and hasattr(self, "txt_box0_summary") and self.txt_box0_summary.winfo_exists():
            return self.txt_box0_summary
        if hasattr(self, "txt_dialogue") and self.txt_dialogue.winfo_exists():
            return self.txt_dialogue
        return getattr(self, "txt_dialogue", None)

    def _get_card_text_widget(self, box_idx: int) -> "tk.Text":
        """Return the card Text widget for box_idx if it exists, else txt_dialogue fallback (S4).

        Guards with winfo_exists() before returning the card widget to avoid stale references
        (STALE-CARD-REGISTRY / Rule 3 widget aliasing guard).
        """
        if hasattr(self, "_card_widgets") and box_idx in self._card_widgets:
            w = self._card_widgets[box_idx].get("txt")
            if w is not None:
                try:
                    if w.winfo_exists():
                        return w
                except Exception:
                    pass
        return self.txt_dialogue

    def _install_shortcuts_bindtag(self, widget: tk.Widget) -> None:
        """Install MisoraShortcuts as the FIRST bindtag on an editor widget (Rule 12)."""
        try:
            current_tags = list(widget.bindtags())
            if "MisoraShortcuts" not in current_tags:
                widget.bindtags(("MisoraShortcuts",) + tuple(current_tags))
        except Exception:
            pass

    def _on_misora_shortcut(self, event: tk.Event) -> Optional[str]:
        """Central shortcut dispatcher on the MisoraShortcuts bindtag (Rule 12)."""
        # 1. Skip if modal grab is active (unless it's self)
        current_grab = self.grab_current()
        if current_grab is not None and current_grab != self:
            return None

        # 2. Skip IME composition / dead keys / empty keysyms
        keysym = getattr(event, "keysym", "")
        if not keysym or keysym.startswith("dead_") or keysym in ("Next_Virtual_Key", "VoidSymbol"):
            return None

        key_lower = keysym.lower()
        state = getattr(event, "state", 0)

        # Modifier bitmasks (Windows Tkinter standard):
        # Shift: 0x0001
        # CapsLock: 0x0002 (mask out)
        # Control: 0x0004
        # Alt: 0x0008 (Mod1) or 0x0020 (Mod3)
        # NumLock: 0x0100 (mask out)
        is_shift = bool(state & 0x0001)
        is_ctrl = bool(state & 0x0004)
        is_alt = bool((state & 0x0008) or (state & 0x0020))

        # 3. Handle explicit Ctrl+Alt application accelerators (X/C/V/A), protect all other keys for AltGr
        if is_ctrl and is_alt:
            if not is_shift:
                if key_lower == "x":
                    self.on_box_cut()
                    return "break"
                elif key_lower == "c":
                    self.on_box_copy()
                    return "break"
                elif key_lower == "v":
                    self.on_box_paste()
                    return "break"
                elif key_lower == "a":
                    self.on_select_whole_story()
                    return "break"
            return None

        # 4. Standard Ctrl+C / Ctrl+X / Ctrl+A: let native widget handlers process them
        if is_ctrl and not is_shift and not is_alt:
            if key_lower in ("c", "x", "a"):
                return None

        # 5. Ctrl+V in editor widget: CSIF detection
        if is_ctrl and not is_shift and not is_alt and key_lower == "v":
            clip_text = self.safe_clipboard_get()
            if clip_text and sniff_format(clip_text) == "csif":
                w = event.widget if isinstance(event.widget, tk.Widget) else self._get_active_text_widget()
                self._handle_editor_csif_paste(w, clip_text)
                return "break"
            return None  # Let standard paste proceed

        # 6. Whitelisted Application Shortcuts (return "break" on match)
        if is_ctrl and not is_alt:
            if not is_shift:
                if key_lower == "h":
                    self.on_show_replace()
                    return "break"
                elif key_lower == "s":
                    self.on_save()
                    return "break"
                elif key_lower == "o":
                    self.on_open_file()
                    return "break"
                elif key_lower == "f":
                    self.on_show_find()
                    return "break"
                elif key_lower == "n":
                    self.on_box_new()
                    return "break"
                elif key_lower == "z":
                    self.on_undo()
                    return "break"
                elif key_lower == "y":
                    self.on_redo()
                    return "break"
                elif key_lower == "t":
                    self.on_open_translator_assistant()
                    return "break"
                elif key_lower == "r":
                    self.on_insert_ruby()
                    return "break"
                elif key_lower == "b":
                    self._shortcut_wrap("[b]", "[/b]")
                    return "break"
                elif key_lower == "i":
                    self._shortcut_wrap("[i]", "[/i]")
                    return "break"
                elif key_lower == "u":
                    self._shortcut_wrap("[u]", "[/u]")
                    return "break"
                elif key_lower == "p":
                    self.on_insert_playername()
                    return "break"
                elif key_lower == "l":
                    self.on_toggle_lock_current_box()
                    return "break"
            else:  # is_shift
                if key_lower == "z":
                    self.on_redo()
                    return "break"
                elif key_lower == "c":
                    self.on_copy_script()
                    return "break"
                elif key_lower == "v":
                    self.on_paste_cross_box()
                    return "break"
                elif key_lower == "t":
                    self.on_copy_ai_prompt()
                    return "break"
                elif key_lower == "i":
                    self.on_import_script()
                    return "break"
                elif key_lower == "e":
                    self.on_export_script()
                    return "break"

        return None

    def _show_csif_paste_chooser(self, clip_text: str) -> Optional[str]:
        """Display modal 4-way chooser dialog when CSIF content is pasted into an editor (Part C.4)."""
        t = self.theme
        dlg = tk.Toplevel(self)
        dlg.title("CSIF Script Detected")
        dlg.transient(self)
        dlg.resizable(False, False)
        dlg.configure(bg=t["bg_panel"])

        choice: List[Optional[str]] = [None]

        def _choose(val: Optional[str]) -> None:
            choice[0] = val
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        parsed = parse(clip_text)
        block_count = len(parsed.blocks)
        first_sp = ", ".join(
            (b.speaker if b.speaker else "Narration") for b in parsed.blocks[:3]
        )
        if block_count > 3:
            first_sp += f", ... (+{block_count - 3} more)"

        frame = tk.Frame(dlg, bg=t["bg_panel"], padx=16, pady=14)
        frame.pack(fill="both", expand=True)

        lbl_hdr = tk.Label(
            frame,
            text="Misora CSIF Script Detected in Clipboard",
            font=("Segoe UI", 11, "bold"),
            fg=t["misora_pink"],
            bg=t["bg_panel"],
        )
        lbl_hdr.pack(anchor="w", pady=(0, 6))

        info_txt = (
            f"The clipboard contains {block_count} structured dialogue block(s).\n"
            f"Speakers: {first_sp}\n\n"
            f"Please choose how you would like to apply this clipboard content:"
        )
        lbl_info = tk.Label(
            frame,
            text=info_txt,
            font=("Segoe UI", 9),
            fg=t["fg_text"],
            bg=t["bg_panel"],
            justify="left",
        )
        lbl_info.pack(anchor="w", pady=(0, 12))

        btn_box = tk.Frame(frame, bg=t["bg_panel"])
        btn_box.pack(fill="x", pady=(4, 0))

        btn_ins = tk.Button(
            btn_box,
            text="📥 Insert as New Boxes",
            font=("Segoe UI", 9, "bold"),
            bg=t["highlight_bg"],
            fg=best_contrast_fg(t["highlight_bg"]),
            relief="raised",
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: _choose("insert"),
        )
        btn_ins.pack(fill="x", pady=2)

        btn_rep = tk.Button(
            btn_box,
            text="🔄 Paste Across Boxes (Replace)",
            font=("Segoe UI", 9),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            relief="raised",
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: _choose("replace"),
        )
        btn_rep.pack(fill="x", pady=2)

        btn_txt = tk.Button(
            btn_box,
            text="📝 Paste as Plain Text",
            font=("Segoe UI", 9),
            bg=t["bg_editor"],
            fg=t["fg_text"],
            relief="raised",
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: _choose("text"),
        )
        btn_txt.pack(fill="x", pady=2)

        btn_cancel = tk.Button(
            btn_box,
            text="❌ Cancel",
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
            relief="groove",
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: _choose(None),
        )
        btn_cancel.pack(fill="x", pady=(4, 0))

        dlg.bind("<Escape>", lambda e: _choose(None))
        dlg.protocol("WM_DELETE_WINDOW", lambda: _choose(None))

        dlg.update_idletasks()
        try:
            pw = self.winfo_width()
            ph = self.winfo_height()
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            dw = dlg.winfo_width()
            dh = dlg.winfo_height()
            dlg.geometry(f"+{px + max(0, (pw - dw) // 2)}+{py + max(0, (ph - dh) // 2)}")
        except Exception:
            pass

        try:
            dlg.grab_set()
            dlg.focus_set()
            self.wait_window(dlg)
        except Exception:
            pass

        return choice[0]

    def _handle_editor_csif_paste(self, widget: tk.Widget, clip_text: str) -> None:
        """Show 4-way chooser dialog when CSIF content is pasted into an editor (Part C.4)."""
        res = self._show_csif_paste_chooser(clip_text)
        if res == "insert":
            self.on_box_paste(confirm=False)
        elif res == "replace":
            self.on_paste_cross_box()
        elif res == "text":
            if isinstance(widget, tk.Text) and widget.winfo_exists():
                try:
                    sel = widget.tag_ranges("sel")
                    if sel:
                        widget.delete(sel[0], sel[1])
                except Exception:
                    pass
                widget.insert(tk.INSERT, clip_text)
                self._commit_widget_edit(widget)

    def _bind_shortcuts(self) -> None:
        self.bind_class("MisoraShortcuts", "<KeyPress>", self._on_misora_shortcut)
        for w in (
            getattr(self, "txt_dialogue", None),
            getattr(self, "entry_speaker", None),
            getattr(self, "txt_continuous", None),
            getattr(self, "txt_box0_summary", None),
            getattr(self, "entry_box0_title", None),
            getattr(self, "entry_box0_subtitle", None),
        ):
            if w is not None:
                self._install_shortcuts_bindtag(w)

        self.bind("<Control-o>", lambda e: self.on_open_file())
        self.bind("<Control-O>", lambda e: self.on_open_folder())
        self.bind("<Control-s>", lambda e: self.on_save())
        self.bind("<Control-q>", lambda e: self._on_app_exit())
        self.bind("<Control-r>", lambda e: self.on_insert_ruby())
        self.bind("<Control-R>", lambda e: self.on_insert_ruby())
        self.bind("<Control-p>", lambda e: self.on_insert_playername())
        self.bind_all("<Control-f>", self._on_ctrl_f)
        self.bind_all("<Control-F>", self._on_ctrl_shift_f)
        self.bind_all("<Control-h>", self._on_ctrl_h)
        self.bind_all("<Control-H>", self._on_ctrl_h)
        self.bind("<Control-z>", lambda e: self.on_undo())
        self.bind("<Control-y>", lambda e: self.on_redo())
        self.bind("<Control-Shift-Z>", lambda e: self.on_redo())
        self.bind("<Control-Shift-z>", lambda e: self.on_redo())
        self.bind("<Control-comma>", lambda e: self._toggle_side_drawer("customize"))
        self.bind("<F1>", lambda e: self._toggle_side_drawer("glossary"))
        self.bind("<F5>", lambda e: self.on_reload())
        self.bind("<F9>", lambda e: self.on_launch_datamine())
        self.bind("<Alt-Left>", lambda e: self.on_prev_box())
        self.bind("<Alt-Right>", lambda e: self.on_next_box())
        self.bind("<Alt-Up>", lambda e: self.on_prev_box())
        self.bind("<Alt-Down>", lambda e: self.on_next_box())
        self.bind("<Control-t>", lambda e: self.on_open_translator_assistant())
        self.bind("<Control-Shift-T>", lambda e: self.on_copy_ai_prompt())
        self.bind("<Control-Shift-t>", lambda e: self.on_copy_ai_prompt())
        self.bind("<Control-Shift-C>", lambda e: self.on_copy_script())
        self.bind("<Control-Shift-c>", lambda e: self.on_copy_script())
        self.bind("<Control-Shift-V>", lambda e: self.on_paste_cross_box())
        self.bind("<Control-Shift-v>", lambda e: self.on_paste_cross_box())
        self.bind("<Control-Shift-I>", lambda e: self.on_import_script())
        self.bind("<Control-Shift-i>", lambda e: self.on_import_script())
        self.bind("<Control-Shift-E>", lambda e: self.on_export_script())
        self.bind("<Control-Shift-e>", lambda e: self.on_export_script())
        self.bind("<Control-l>", lambda e: self.on_toggle_lock_current_box())
        self.bind("<Control-L>", lambda e: self.on_toggle_lock_current_box())
        self.bind("<Control-Alt-x>", lambda e: self.on_box_cut())
        self.bind("<Control-Alt-X>", lambda e: self.on_box_cut())
        self.bind("<Control-Alt-c>", lambda e: self.on_box_copy())
        self.bind("<Control-Alt-C>", lambda e: self.on_box_copy())
        self.bind("<Control-Alt-v>", lambda e: self.on_box_paste())
        self.bind("<Control-Alt-V>", lambda e: self.on_box_paste())
        self.bind("<Control-Alt-a>", lambda e: self.on_select_whole_story())
        self.bind("<Control-Alt-A>", lambda e: self.on_select_whole_story())
        self.bind("<F8>", lambda e: self.on_translate_current_box())

    def _toggle_continuous_shortcut(self) -> None:
        self.var_continuous_view.set(not self.var_continuous_view.get())
        self._on_toggle_continuous_view()

    def _on_ctrl_h(self, _e: Optional[tk.Event] = None) -> str:
        """Bind_all handler for Ctrl+H (Find & Replace bar) returning 'break' (HYG-07)."""
        self.on_show_replace()
        return "break"

    def _on_ctrl_f(self, _e: Optional[tk.Event] = None) -> str:
        """Bind_all handler for Ctrl+F (Find bar) returning 'break'."""
        self.on_show_find()
        return "break"

    def _on_ctrl_shift_f(self, _e: Optional[tk.Event] = None) -> str:
        """Bind_all handler for Ctrl+Shift+F (Find in files) returning 'break'."""
        self.on_show_find_in_files()
        return "break"

    # -------------------------------------------------------------------------
    # Document Loading & Box Display (Page Mode + Continuous Stream Mode)
    # -------------------------------------------------------------------------
    def _flush_active_widget(self) -> bool:
        """Explicitly resolve the active editor widget and commit any pending edits (S1/S3).

        Returns True if flushed cleanly or no active widget, False on commit failure.
        """
        if getattr(self, "current_file_path", None) is None:
            return True

        widget = None
        is_cont = bool(getattr(self, "var_continuous_view", None) and self.var_continuous_view.get())
        cards = getattr(self, "_card_widgets", {})

        if is_cont:
            if getattr(self, "current_doc", None) is None:
                candidate = getattr(self, "txt_continuous", None)
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate
            # Technique A txt_all_script is read-only; still flush entry_speaker below if focused
        else:
            if getattr(self, "is_box0_active", False):
                candidate = getattr(self, "txt_box0_summary", None)
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate
            else:
                candidate = getattr(self, "txt_dialogue", None)
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate

        if widget is not None:
            try:
                self._commit_widget_edit(widget)
            except Exception as e:
                self.logger.exception("Failed to flush pending edit:", e)
                messagebox.showerror("Edit Commit Error", f"Could not preserve the current edit:\n{e}")
                return False

        try:
            focused = self.focus_get() if hasattr(self, "focus_get") else None
            if focused == getattr(self, "entry_speaker", None) or self._is_widget_in_speaker_popup(focused):
                self._close_speaker_autocomplete()
                self._commit_speaker_edit(source="flush")
        except Exception:
            pass
        return True

    def open_file(self, file_path: Union[str, Path], reload_from_disk: bool = False, refresh_ui: bool = True) -> None:
        """Open and display a .unity3d bundle or plain-text script file."""
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            self.logger.error("File I/O", f"Cannot find file: {file_path}")
            messagebox.showerror("File Error", f"Cannot find file: {file_path}")
            return

        staged = None
        ext = file_path.suffix.lower()

        # Cache-hit switches do not need a disk load, but still flush the old
        # editor context after staging/target resolution succeeds.
        if not reload_from_disk and file_path in self.open_documents:
            entry = self.open_documents[file_path]
            staged = {
                "kind": "cache",
                "entry": entry,
                "doc": entry.get("doc"),
                "env": entry.get("env"),
                "obj": entry.get("obj"),
                "is_bundle": entry.get("is_bundle", False),
                "dirty": entry.get("dirty", False),
                "plain_text": entry.get("plain_text", ""),
                "status": f"Switched to {file_path.name}",
            }
        elif ext in (".unity3d", ".asset"):
            try:
                doc, env, obj, asset_name = load_bundle_story(file_path)
                staged = {
                    "kind": "bundle",
                    "doc": doc,
                    "env": env,
                    "obj": obj,
                    "asset_name": asset_name,
                    "is_bundle": True,
                    "dirty": False,
                    "plain_text": "",
                    "status": (
                        f"Loaded Bundle: {file_path.name} ({asset_name}) | "
                        f"Size: {file_path.stat().st_size / 1024:.1f} KB | "
                        f"{len(doc.boxes)} dialogue boxes"
                    ),
                    "cache": {
                        "doc": doc,
                        "env": env,
                        "obj": obj,
                        "is_bundle": True,
                        "dirty": False,
                        "plain_text": "",
                        "boxes_count": len(doc.boxes),
                    },
                }
            except Exception as e:
                self.logger.exception(f"Failed to open bundle '{file_path.name}':", e)
                messagebox.showerror("Bundle Load Error", f"Failed to open '{file_path.name}':\n{e}")
                return
        else:
            try:
                decoded = read_text_file_strictly(file_path)
                content = decoded.text
                if content.startswith("#!priconne-story"):
                    doc = StoryDocument.from_v2_text(content)
                    staged = {
                        "kind": "v2",
                        "doc": doc,
                        "env": None,
                        "obj": None,
                        "is_bundle": False,
                        "dirty": False,
                        "plain_text": "",
                        "status": f"Loaded Script: {file_path.name} | {len(doc.boxes)} dialogue boxes",
                        "cache": {
                            "doc": doc,
                            "env": None,
                            "obj": None,
                            "is_bundle": False,
                            "dirty": False,
                            "plain_text": "",
                            "boxes_count": len(doc.boxes),
                            "encoding": decoded.encoding,
                            "has_bom": decoded.has_bom,
                            "newline": decoded.newline,
                        },
                    }
                else:
                    staged = {
                        "kind": "text",
                        "doc": None,
                        "env": None,
                        "obj": None,
                        "is_bundle": False,
                        "dirty": False,
                        "plain_text": content,
                        "status": f"Opened Text File: {file_path.name}",
                        "cache": {
                            "doc": None,
                            "env": None,
                            "obj": None,
                            "is_bundle": False,
                            "dirty": False,
                            "plain_text": content,
                            "boxes_count": 0,
                            "encoding": decoded.encoding,
                            "has_bom": decoded.has_bom,
                            "newline": decoded.newline,
                        },
                    }
            except Exception as e:
                self.logger.exception(f"Failed to read '{file_path.name}':", e)
                messagebox.showerror("File Load Error", f"Failed to read '{file_path.name}':\n{e}")
                return

        # Flush the previous context only after the target is ready. Resolve
        # the actual editor widget explicitly; focus must not decide this switch.
        if not self._flush_active_widget():
            return

        self._save_active_document_state()
        self._exit_raw_edit_mode(refresh=False)
        if hasattr(self, "_cancel_mtl_all_batch"):
            self._cancel_mtl_all_batch()

        doc = staged["doc"]
        is_bundle = staged["is_bundle"]
        plain_text = staged["plain_text"]

        self.current_file_path = file_path
        if hasattr(self, "_reset_speaker_pin"):
            self._reset_speaker_pin(notify=False)
        if hasattr(self, "undo_journal") and hasattr(self.undo_journal, "set_active_file"):
            self.undo_journal.set_active_file(str(file_path))
        self.current_doc = doc
        self.current_unity_env = staged["env"]
        self.current_text_obj = staged["obj"]
        self.is_bundle_file = is_bundle
        self._plain_text_content = plain_text

        if staged["kind"] == "cache":
            entry = staged["entry"]
            self.is_dirty = bool(entry.get("dirty", False))
            self.current_box_idx = int(entry.get("current_box_idx", 0))
            self.is_box0_active = bool(entry.get("is_box0_active", False))
            self._locked_box_uids = set(entry.get("locked_box_uids", set()))
            self._modified_box_uids = set(entry.get("modified_box_uids", set()))
            self._original_jp_by_uid = dict(entry.get("original_jp_by_uid", {}))
        else:
            self.current_box_idx = 0
            self.is_box0_active = False
            self.is_dirty = staged["dirty"]
            self._locked_box_uids = set()
            self._modified_box_uids = set()
            self._original_jp_by_uid = (
                {_get_box_uid(b): b.clean_text for b in doc.boxes if _get_box_uid(b) is not None}
                if doc is not None and doc.boxes
                else {}
            )
            staged_cache = staged.get("cache")
            if staged_cache is not None:
                staged_cache["current_box_idx"] = 0
                staged_cache["is_box0_active"] = False
                staged_cache["locked_box_uids"] = set()
                staged_cache["modified_box_uids"] = set()
                staged_cache["original_jp_by_uid"] = dict(self._original_jp_by_uid)

        if doc is not None and doc.boxes:
            self.current_box_idx = max(0, min(self.current_box_idx, len(doc.boxes) - 1))
            self._locked_boxes = {i for i, b in enumerate(doc.boxes) if _get_box_uid(b) in self._locked_box_uids}
            self._modified_boxes = {i for i, b in enumerate(doc.boxes) if _get_box_uid(b) in self._modified_box_uids}
            self._original_box_texts = {i: self._original_jp_by_uid.get(_get_box_uid(b), "") for i, b in enumerate(doc.boxes)}
            for b in doc.boxes:
                b_uid = _get_box_uid(b)
                if b_uid is not None:
                    if b_uid not in self._original_jp_by_uid:
                        self._original_jp_by_uid[b_uid] = b.clean_text
                    if hasattr(self, "sync_manager"):
                        self.sync_manager.register_jp_key(b_uid, self._original_jp_by_uid[b_uid])
        else:
            self.current_box_idx = 0
            self._locked_boxes = set()
            self._modified_boxes = set()
            self._original_box_texts = {}

        if hasattr(self, "recent_files"):
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
        else:
            self.recent_files = []
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:15]
        self.last_opened_dir = file_path.parent
        self.title(f"Misora: Story Editor - {file_path.name}")

        if staged["kind"] == "cache":
            entry = staged["entry"]
            self.is_dirty = bool(entry.get("dirty", False))
        else:
            # Dispose prior UnityPy environment and clear prior entry on reload (BUG-34 / BUG-03)
            if reload_from_disk and file_path in self.open_documents:
                prior_entry = self.open_documents.get(file_path)
                if isinstance(prior_entry, dict):
                    prior_doc = prior_entry.get("doc")
                    prior_jp_uids = (
                        prior_entry.get("original_jp_by_uid", {}).keys()
                        if isinstance(prior_entry.get("original_jp_by_uid"), dict)
                        else ()
                    )
                    if hasattr(self, "_prune_document_caches"):
                        self._prune_document_caches(file_path, prior_doc, extra_uids=prior_jp_uids)
                    if prior_entry.get("env"):
                        dispose_unity_env(prior_entry["env"])
                    prior_entry.clear()
            self.open_documents[file_path] = staged["cache"]
            # Record a fresh saved-state checkpoint for newly loaded documents
            self._record_saved_checkpoint(file_path, staged.get("doc"), staged.get("plain_text", ""))

        if refresh_ui:
            self._update_views()
            self._dirty_state_changed()
            self._sync_edit_menu_states()
            self.lbl_status.config(text=staged["status"])

        if staged["kind"] == "bundle":
            self.logger.info(
                "File I/O",
                f"Opened bundle '{file_path}' (asset={staged['asset_name']}, boxes={len(doc.boxes)})",
            )
        elif staged["kind"] == "v2":
            self.logger.info("File I/O", f"Opened v2 script '{file_path}' (boxes={len(doc.boxes)})")
        elif staged["kind"] == "text":
            self.logger.info("File I/O", f"Opened plain text file '{file_path}' ({len(plain_text)} chars)")

    def _update_empty_state_visibility(self) -> None:
        """Show centered empty-state frame when 0 documents are open; pack only active view when >=1."""
        has_docs = bool(self.open_documents) or bool(self.current_doc) or bool(self.current_file_path)
        if not has_docs:
            if hasattr(self, "gd_scroll_wrap") and self.gd_scroll_wrap.winfo_ismapped():
                self.gd_scroll_wrap.pack_forget()
            if hasattr(self, "continuous_wrap") and self.continuous_wrap.winfo_ismapped():
                self.continuous_wrap.pack_forget()
            if hasattr(self, "empty_state_frame") and not self.empty_state_frame.winfo_ismapped():
                self.empty_state_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        else:
            if hasattr(self, "empty_state_frame") and self.empty_state_frame.winfo_ismapped():
                self.empty_state_frame.pack_forget()
            is_cont = bool(getattr(self, "var_continuous_view", None) and self.var_continuous_view.get())
            if is_cont:
                if hasattr(self, "gd_scroll_wrap") and self.gd_scroll_wrap.winfo_ismapped():
                    self.gd_scroll_wrap.pack_forget()
                if hasattr(self, "continuous_wrap") and not self.continuous_wrap.winfo_ismapped():
                    self.continuous_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 6))
            else:
                if hasattr(self, "continuous_wrap") and self.continuous_wrap.winfo_ismapped():
                    self.continuous_wrap.pack_forget()
                if hasattr(self, "gd_scroll_wrap") and not self.gd_scroll_wrap.winfo_ismapped():
                    self.gd_scroll_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _update_views(self) -> None:
        """Update Game Display View (Page or Continuous, Raw or Compiled Preview) and Raw AST View."""
        self._update_empty_state_visibility()
        self._update_dialogue_select_box_ui()
        if hasattr(self, "_sync_raw_edit_buttons"):
            self._sync_raw_edit_buttons()
        compiled = self.var_preview_compiled.get()

        if not self.current_doc:
            self._hide_dialogue_preview_and_restore_editor()
            self._clear_card_registry()  # S4: prune stale card refs on plain-text / empty state
            self.speaker_var.set("")
            self.lbl_box_counter.config(text="Box: 0 / 0")
            self.lbl_voice_cue.config(text="")

            self.txt_dialogue.config(state="normal")
            self.txt_dialogue.delete("1.0", tk.END)
            if compiled:
                self._insert_compiled_ngui_text(self.txt_dialogue, "1.0", self._plain_text_content)
                self.txt_dialogue.config(state="disabled")
            else:
                self.txt_dialogue.insert("1.0", self._plain_text_content)
                self._highlight_ngui_tags()
                self._highlight_dialogue_matches()
            self._auto_resize_dialogue_box()

            self.txt_continuous.config(state="normal")
            self.txt_continuous.delete("1.0", tk.END)
            if compiled:
                self._insert_compiled_ngui_text(self.txt_continuous, "1.0", self._plain_text_content)
                self.txt_continuous.config(state="disabled")
            else:
                self.txt_continuous.insert("1.0", self._plain_text_content)
                self._highlight_ngui_tags()
                self._highlight_continuous_matches()

            try:
                self.txt_raw.config(state="normal")
                self.txt_raw.delete("1.0", tk.END)
                if self.current_file_path:
                    self.txt_raw.insert("1.0", f"(Plain text file: {self.current_file_path})")
            finally:
                self.txt_raw.config(state="disabled")
            self._refresh_mtl_drawer_box()
            return

        if not self.current_doc.boxes:
            self._hide_dialogue_preview_and_restore_editor()
            self.speaker_var.set("")
            self.lbl_voice_cue.config(text="")
            self.txt_dialogue.config(state="normal")
            self.txt_dialogue.delete("1.0", tk.END)
            self.txt_continuous.config(state="normal")
            self.txt_continuous.delete("1.0", tk.END)
            try:
                self.txt_raw.config(state="normal")
                self.txt_raw.delete("1.0", tk.END)
            finally:
                self.txt_raw.config(state="disabled")
            self.lbl_box_counter.config(text="Box: 0 / 0")
            self._auto_resize_dialogue_box()
            self._refresh_mtl_drawer_box()
            return

        if self.is_box0_active:
            if not self.current_doc or not self.current_doc.has_metadata():
                self.is_box0_active = False
            else:
                total_boxes = len(self.current_doc.boxes)
                self.speaker_var.set("")
                if hasattr(self, "entry_speaker"):
                    self.entry_speaker.config(state="disabled")
                if hasattr(self, "btn_speaker_dropdown"):
                    self.btn_speaker_dropdown.config(state="disabled")
                self.lbl_box_counter.config(text=f"Box: 0 / {total_boxes} (Story Metadata)")
                self.lbl_voice_cue.config(text="")
                if hasattr(self, "btn_prev"):
                    self.btn_prev.config(state="disabled")
                if hasattr(self, "btn_next"):
                    self.btn_next.config(state="normal" if total_boxes > 0 else "disabled")

                if self.var_continuous_view.get():
                    self._render_continuous_view()
                    self._focus_continuous_box(-1, move_cursor=True)
                else:
                    if hasattr(self, "dialogue_preview_canvas") and self._is_widget_packed(self.dialogue_preview_canvas):
                        self.dialogue_preview_canvas.pack_forget()
                    if hasattr(self, "clean_editor_row") and self._is_widget_packed(self.clean_editor_row):
                        self.clean_editor_row.pack_forget()
                    if hasattr(self, "ruler_clean") and self._is_widget_packed(self.ruler_clean):
                        self.ruler_clean.pack_forget()
                    if hasattr(self, "panel_box0_metadata") and not self._is_widget_packed(self.panel_box0_metadata):
                        self.panel_box0_metadata.pack(fill="both", expand=True)

                    meta = self.current_doc.get_metadata()
                    self.var_box0_title.set(meta.get("title", ""))
                    self.var_box0_subtitle.set(meta.get("subtitle", ""))
                    self.txt_box0_summary.delete("1.0", tk.END)
                    self.txt_box0_summary.insert("1.0", meta.get("summary", ""))
                    self._update_box0_char_counter()
                    self.gd_canvas.yview_moveto(0.0)

                self._update_raw_view()
                self._update_char_overflow_indicator()
                if hasattr(self, "_translator_dialog") and self._translator_dialog and self._translator_dialog.winfo_exists():
                    self._translator_dialog.refresh_box()
                return

        if hasattr(self, "panel_box0_metadata") and self._is_widget_packed(self.panel_box0_metadata):
            self.panel_box0_metadata.pack_forget()
        if compiled and not self.var_continuous_view.get():
            if hasattr(self, "clean_editor_row") and self._is_widget_packed(self.clean_editor_row):
                self.clean_editor_row.pack_forget()
            if hasattr(self, "ruler_clean") and self._is_widget_packed(self.ruler_clean):
                self.ruler_clean.pack_forget()
            if hasattr(self, "dialogue_preview_canvas") and not self._is_widget_packed(self.dialogue_preview_canvas):
                self.dialogue_preview_canvas.pack(fill="both", expand=True)
        else:
            self._hide_dialogue_preview_and_restore_editor()

        total_boxes = len(self.current_doc.boxes)
        self.current_box_idx = max(0, min(self.current_box_idx, total_boxes - 1))
        box = self.current_doc.boxes[self.current_box_idx]

        if hasattr(self, "entry_speaker"):
            self.entry_speaker.config(state="normal")
        if hasattr(self, "btn_speaker_dropdown"):
            self.btn_speaker_dropdown.config(state="normal")
        self.speaker_var.set(box.speaker)
        self._speaker_ac_user_typed = False
        self.lbl_box_counter.config(text=f"Box: {self.current_box_idx + 1} / {total_boxes}")
        if hasattr(self, "lbl_voice_cue"):
            self.lbl_voice_cue.config(text=f"Voice Cue: {box.voice_cue}" if box.voice_cue else "")
        if hasattr(self, "lbl_segs_badge"):
            self.lbl_segs_badge.config(text=f"{len(box.segs)} segs" if len(box.segs) > 1 else "")

        if hasattr(self, "btn_lock_box") and self.btn_lock_box.winfo_exists():
            is_locked = self.current_box_idx in self._locked_boxes
            lock_bg = self.theme["accent_yellow"] if is_locked else self.theme["bg_panel"]
            lock_fg = best_contrast_fg(lock_bg, self.theme["fg_text"], "#ffffff")
            self.btn_lock_box.config(
                text="🔒" if is_locked else "🔓",
                bg=lock_bg,
                fg=lock_fg,
                bd=0,
                relief="flat",
                highlightthickness=0,
            )

        if hasattr(self, "btn_prev"):
            can_prev = (self.current_box_idx > 0) or (self.current_doc and self.current_doc.has_metadata())
            self.btn_prev.config(state="normal" if can_prev else "disabled")
        if hasattr(self, "btn_next"):
            self.btn_next.config(state="normal" if self.current_box_idx < total_boxes - 1 else "disabled")

        if self.var_continuous_view.get():
            self._render_continuous_view()
            self._focus_continuous_box(self.current_box_idx, move_cursor=True)
        elif compiled:
            self._render_dialogue_preview_frame(box.speaker, box.clean_text)
            self.gd_canvas.yview_moveto(0.0)
            self.gd_inner.update_idletasks()
            self._sync_gd_scroll_bounds()
        else:
            self.txt_dialogue.config(state="normal")
            self.txt_dialogue.delete("1.0", tk.END)
            self.txt_dialogue.insert("1.0", box.clean_text)
            self._highlight_ngui_tags()
            self._highlight_dialogue_matches()
            self._highlight_secret_whitespace(self.txt_dialogue)
            self._update_gutter_clean()
            self.gd_canvas.yview_moveto(0.0)
            self._auto_resize_dialogue_box()

        self._update_raw_view()
        self._update_char_overflow_indicator()
        self._refresh_mtl_drawer_box()
        if hasattr(self, "_translator_dialog") and self._translator_dialog and self._translator_dialog.winfo_exists():
            self._translator_dialog.refresh_box()

    def _update_raw_view(self) -> None:
        """Render Raw AST View and highlight records associated with current_box_idx or Box 0."""
        if getattr(self, "_raw_edit_mode", False):
            return
        self.txt_raw.config(state="normal")
        try:
            self.txt_raw.delete("1.0", tk.END)
            if not self.current_doc:
                return

            active_rec_indices = set()
            if getattr(self, "is_box0_active", False) and self.current_doc:
                for idx, r in enumerate(self.current_doc.records):
                    if (r.cmd_id == 0 and len(r.args) > 0 and r.args[0]) or \
                       (r.cmd_id == 32 and len(r.args) > 0 and r.args[0]) or \
                       (r.cmd_id == 1 and len(r.args) > 0 and r.args[0]):
                        active_rec_indices.add(idx)
            elif self.current_doc and self.current_doc.boxes and 0 <= self.current_box_idx < len(self.current_doc.boxes):
                active_box = self.current_doc.boxes[self.current_box_idx]
                active_uids = {s.record.uid for s in active_box.segs}
                active_rec_indices = {i for i, r in enumerate(self.current_doc.records) if r.uid in active_uids}

            raw_lines = []
            first_active_line = None
            for i, r in enumerate(self.current_doc.records):
                args_str = "  ".join(f"'{a}'" for a in r.args)
                is_active = i in active_rec_indices
                if is_active and first_active_line is None:
                    first_active_line = i + 1
                marker = " >> " if is_active else "    "
                raw_lines.append(f"{marker}[{i:03d}] {r.cmd_name:<14} {args_str}")

            self.txt_raw.insert("1.0", "\n".join(raw_lines))
            if first_active_line is not None:
                self.txt_raw.see(f"{first_active_line}.0")
        finally:
            self.txt_raw.config(state="disabled")

    def _sync_raw_edit_buttons(self) -> None:
        """Sync visibility and enabled state of Raw Commands edit/apply/cancel buttons."""
        in_edit = bool(getattr(self, "_raw_edit_mode", False))
        has_doc = self.current_doc is not None
        if hasattr(self, "btn_edit_raw") and self.btn_edit_raw.winfo_exists():
            if in_edit:
                self.btn_edit_raw.pack_forget()
            else:
                self.btn_edit_raw.config(state="normal" if has_doc else "disabled")
                if not self.btn_edit_raw.winfo_manager():
                    self.btn_edit_raw.pack(side="right", padx=(4, 0))
        if hasattr(self, "btn_apply_raw") and self.btn_apply_raw.winfo_exists():
            if in_edit:
                if not self.btn_apply_raw.winfo_manager():
                    self.btn_apply_raw.pack(side="right", padx=(4, 0))
            else:
                self.btn_apply_raw.pack_forget()
        if hasattr(self, "btn_cancel_raw") and self.btn_cancel_raw.winfo_exists():
            if in_edit:
                if not self.btn_cancel_raw.winfo_manager():
                    self.btn_cancel_raw.pack(side="right", padx=(4, 0))
            else:
                self.btn_cancel_raw.pack_forget()

    def _exit_raw_edit_mode(self, refresh: bool = True) -> None:
        """Exit Raw Commands edit mode cleanly and restore read-only state (BUG-37)."""
        self._raw_edit_mode = False
        if hasattr(self, "txt_raw") and self.txt_raw.winfo_exists():
            self.txt_raw.config(state="disabled")
        if hasattr(self, "_sync_raw_edit_buttons"):
            self._sync_raw_edit_buttons()
        if refresh:
            self._update_raw_view()

    def on_enter_raw_edit_mode(self) -> None:
        """Enter whole-file lossless v2 editing mode in Raw Commands (FEAT-11)."""
        if not self.current_doc:
            self.show_toast("No story document loaded")
            return
        self._flush_active_widget()
        self._raw_edit_mode = True
        self.txt_raw.config(state="normal")
        self.txt_raw.delete("1.0", tk.END)
        self.txt_raw.insert("1.0", self.current_doc.to_v2_text())
        self._sync_raw_edit_buttons()
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(
                text="Raw Commands Edit Mode (v2) — click Apply Raw to commit or Revert / Cancel to discard."
            )

    def on_cancel_raw_edit_mode(self) -> None:
        """Discard Raw Commands v2 edits and return to read-only view."""
        self._exit_raw_edit_mode(refresh=True)
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text="Raw Commands edit cancelled.")

    @staticmethod
    def _parse_and_validate_raw_v2(v2_text: str) -> StoryDocument:
        """Parse and structurally validate lossless v2 text via binary round-trip (NO-07, DEF-02)."""
        if not isinstance(v2_text, str) or not v2_text.strip():
            raise ValueError("Raw Commands v2 text is empty.")

        lines = [l.rstrip("\r\n") for l in v2_text.splitlines()]
        if lines and lines[0].startswith("#!priconne-story"):
            lines.pop(0)

        from core.story_ast import DEFAULT_CATEGORIES  # local import to avoid top-level churn

        i = 0
        has_record_blocks = False
        while i < len(lines):
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines):
                break
            has_record_blocks = True
            header = lines[i].strip()
            i += 1

            if "#" in header:
                _cmd_name, cid_str = header.split("#", 1)
                if not cid_str.isdigit():
                    raise ValueError(f"Invalid numeric command ID in header '{header}'.")
                cid = int(cid_str)
                if not (0 <= cid <= 65535):
                    raise ValueError(f"Command ID {cid} out of uint16 range (0..65535) in '{header}'.")
            elif header.startswith("cmd_"):
                cid_str = header[4:]
                if not cid_str.isdigit():
                    raise ValueError(f"Invalid numeric command header '{header}'.")
                cid = int(cid_str)
                if not (0 <= cid <= 65535):
                    raise ValueError(f"Command ID {cid} out of uint16 range (0..65535) in '{header}'.")
            else:
                if header not in _AST_INV_CMD_MAP:
                    raise ValueError(f"Unknown command name '{header}' without explicit #<id>.")

            while i < len(lines):
                l = lines[i]
                i += 1
                if not l.strip():
                    break
                if l in DEFAULT_CATEGORIES and not l.startswith("\\"):
                    break
                if l.startswith("\\b64:"):
                    _ast_unescape_arg(l)

        if not has_record_blocks:
            raise ValueError("Raw Commands v2 text contains no command records.")

        candidate = StoryDocument.from_v2_text(v2_text)
        if not candidate.records:
            raise ValueError("Parsed v2 document contains zero records.")

        for idx, rec in enumerate(candidate.records):
            if not (0 <= rec.cmd_id <= 65535):
                raise ValueError(f"Record {idx} ({rec.cmd_name}) has out-of-range cmd_id {rec.cmd_id}.")

        binary_bytes = candidate.to_binary()
        roundtrip = StoryDocument.from_binary(binary_bytes)
        if len(roundtrip.records) != len(candidate.records):
            raise ValueError(
                f"Binary round-trip record count mismatch ({len(roundtrip.records)} != {len(candidate.records)})."
            )
        for idx, (orig_r, rt_r) in enumerate(zip(candidate.records, roundtrip.records)):
            if orig_r.cmd_id != rt_r.cmd_id:
                raise ValueError(
                    f"Binary round-trip cmd_id mismatch at record {idx}: {rt_r.cmd_id} != {orig_r.cmd_id}."
                )
            expected_args = [a if a != "" else " " for a in orig_r.args]
            if rt_r.args != expected_args:
                raise ValueError(
                    f"Binary round-trip argument parity mismatch at record {idx} ({orig_r.cmd_name})."
                )
        return candidate

    def _remap_locks_and_jp_keys(
        self,
        stable_locks: List[Tuple[int, str]],
        old_jp_by_ordinal: Dict[int, str],
        old_clean_by_ordinal: Dict[int, str],
    ) -> None:
        """Remap _original_jp_by_uid and _locked_box_uids via stable composite keys (CLAUDE-N02)."""
        new_jp_by_uid: Dict[int, str] = {}
        if self.current_doc and self.current_doc.boxes:
            for i, box in enumerate(self.current_doc.boxes):
                new_uid = _get_box_uid(box)
                if new_uid is None:
                    continue
                if i in old_jp_by_ordinal and box.clean_text == old_clean_by_ordinal.get(i):
                    new_jp_by_uid[new_uid] = old_jp_by_ordinal[i]
                else:
                    new_jp_by_uid[new_uid] = box.clean_text

        matched_uids, _unresolved = restore_stable_locks(self.current_doc, stable_locks, new_jp_by_uid)
        self._locked_box_uids = set(matched_uids)
        self._original_jp_by_uid = new_jp_by_uid

        if hasattr(self, "sync_manager") and self.sync_manager is not None:
            for b_uid, jp_txt in new_jp_by_uid.items():
                self.sync_manager.register_jp_key(b_uid, jp_txt)

        if self.current_file_path:
            cur_p = Path(self.current_file_path).resolve()
            if cur_p in self.open_documents:
                self.open_documents[cur_p]["locked_box_uids"] = set(self._locked_box_uids)
                self.open_documents[cur_p]["original_jp_by_uid"] = dict(self._original_jp_by_uid)
        self._resync_box_indices_from_uids()

    def on_apply_raw_commands(self) -> None:
        """Confirm, validate, and atomically commit whole-file Raw Commands v2 edits (FEAT-11)."""
        if not self.current_doc:
            return
        confirmed = messagebox.askyesno(
            "Apply Raw Commands",
            "Applying Raw Commands will replace all workspace records for the current document.\n\n"
            "Do you want to validate and apply these changes?",
            parent=self,
        )
        if not confirmed:
            return

        raw_text = self.txt_raw.get("1.0", "end-1c")
        try:
            candidate = self._parse_and_validate_raw_v2(raw_text)
        except Exception as exc:
            self._exit_raw_edit_mode(refresh=True)
            messagebox.showerror(
                "Raw Commands Validation Error",
                f"Failed to parse or validate Raw Commands v2 script:\n\n{exc}\n\n"
                "No changes were applied; Raw Commands has been reverted.",
                parent=self,
            )
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=f"Raw Commands error: {exc}")
            return

        # Snapshot pre-edit state before mutating
        old_records = copy.deepcopy(self.current_doc.records)
        old_removed = set(self.current_doc.removed_records)
        old_box_idx = int(getattr(self, "current_box_idx", 0))
        old_is_box0 = bool(getattr(self, "is_box0_active", False))
        old_locked_uids = set(getattr(self, "_locked_box_uids", set()))
        old_jp_by_uid = dict(getattr(self, "_original_jp_by_uid", {}))

        stable_locks = get_document_stable_locks(self.current_doc, old_locked_uids, old_jp_by_uid)
        old_jp_by_ordinal = {
            i: old_jp_by_uid.get(_get_box_uid(b), b.clean_text)
            for i, b in enumerate(self.current_doc.boxes)
        }
        old_clean_by_ordinal = {i: b.clean_text for i, b in enumerate(self.current_doc.boxes)}

        # Mutate AST & rebuild Box projection
        self.current_doc.records = copy.deepcopy(candidate.records)
        self.current_doc.removed_records = set()
        self.current_doc._rebuild_boxes()

        # Remap stable locks & immutable JP keys
        self._remap_locks_and_jp_keys(stable_locks, old_jp_by_ordinal, old_clean_by_ordinal)

        # Clamp cursor bounds safely
        if self.current_doc.boxes:
            self.current_box_idx = max(0, min(old_box_idx, len(self.current_doc.boxes) - 1))
        else:
            self.current_box_idx = 0
        self.is_box0_active = bool(old_is_box0 and self.current_doc.has_metadata())

        new_records = copy.deepcopy(self.current_doc.records)
        new_locked_uids = set(getattr(self, "_locked_box_uids", set()))
        new_jp_by_uid = dict(getattr(self, "_original_jp_by_uid", {}))

        # Record single atomic DocumentRecordsDelta
        self.undo_journal.record(
            DocumentRecordsDelta(
                file_path=str(self.current_file_path or ""),
                old_records=old_records,
                new_records=new_records,
                old_removed_records=old_removed,
                new_removed_records=set(),
                old_box_idx=old_box_idx,
                new_box_idx=self.current_box_idx,
                old_is_box0=old_is_box0,
                new_is_box0=self.is_box0_active,
                old_locked_uids=old_locked_uids,
                new_locked_uids=new_locked_uids,
                old_jp_by_uid=old_jp_by_uid,
                new_jp_by_uid=new_jp_by_uid,
            ),
            label="Edit Raw Commands",
        )

        self._mark_document_dirty(self.current_file_path)
        self._exit_raw_edit_mode(refresh=False)
        self._update_views()
        self._sync_clean_view_to_current_box()
        self._dirty_state_changed()
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text="Applied Raw Commands v2 changes.")
        self.logger.info("Edit", "Applied Raw Commands v2 edits.")

    # -------------------------------------------------------------------------
    # Continuous View: Box Card Stream Architecture & Two-Way Sync
    # -------------------------------------------------------------------------
    def _flush_continuous_card_edits(self) -> None:
        """Flush any uncommitted edits from active Box Cards or plain text back into model."""
        if not self.current_doc:
            if hasattr(self, "txt_continuous") and self.txt_continuous.winfo_exists():
                if not getattr(self, "var_preview_compiled", None) or not self.var_preview_compiled.get():
                    new_tx = self.txt_continuous.get("1.0", "end-1c")
                    if self._plain_text_content != new_tx:
                        old_tx = self._plain_text_content
                        self.undo_journal.record(
                            PlainTextDelta(
                                file_path=str(self.current_file_path or ""),
                                old_content=old_tx,
                                new_content=new_tx,
                            ),
                            label=f"Edit {self.current_file_path.name if self.current_file_path else 'text'}"
                        )
                        self._plain_text_content = new_tx
                        if self.current_file_path and self.current_file_path in self.open_documents:
                            self.open_documents[self.current_file_path]["plain_text"] = new_tx
                        self._mark_document_dirty(self.current_file_path)
            return

        if not getattr(self, "_card_widgets", None):
            return

        for b_idx, card_info in list(self._card_widgets.items()):
            if b_idx == -1:
                continue
            if 0 <= b_idx < len(self.current_doc.boxes):
                txt_w = card_info.get("txt")
                if txt_w and txt_w.winfo_exists():
                    new_tx = txt_w.get("1.0", "end-1c")
                    box = self.current_doc.boxes[b_idx]
                    if box.clean_text != new_tx:
                        old_sp = box.speaker
                        old_tx = box.clean_text
                        box_uid = box.segs[0].record.uid if box.segs else None
                        old_segs = [s.text for s in box.segs] if len(box.segs) > 1 else None
                        try:
                            self.current_doc.inject_box(b_idx, None, new_tx)
                        except Exception as e:
                            self.logger.exception(f"Failed to flush card edit for box {b_idx}:", e)
                            self.set_status(f"Error flushing box #{b_idx + 1}: {e}", is_error=True)
                            continue

                        new_segs = None
                        if old_segs is not None:
                            refreshed_box = next((b for b in self.current_doc.boxes if b.segs and b.segs[0].record.uid == box_uid), None)
                            if refreshed_box:
                                new_segs = [s.text for s in refreshed_box.segs]

                        delta = BoxEditDelta(
                            box_index=b_idx,
                            old_speaker=old_sp,
                            new_speaker=old_sp,
                            old_text=old_tx,
                            new_text=new_tx,
                            file_path=str(self.current_file_path or ""),
                            box_uid=box_uid,
                            source=getattr(self, "_current_edit_source", "keyboard"),
                            old_seg_texts=old_segs,
                            new_seg_texts=new_segs,
                        )
                        self.undo_journal.record(delta, label=f"Edit box #{b_idx + 1}")
                        self._modified_boxes.add(b_idx)
                        self._mark_document_dirty(self.current_file_path)

    def _on_card_text_edited(self, box_idx: int, txt_w: tk.Text, gutter: Optional[tk.Text] = None) -> bool:
        """Handle inline typing inside a Box Card. Returns True if content was mutated (BUG-30)."""
        if getattr(self, "_suppress_continuous_events", False) or self.var_preview_compiled.get():
            return False
        if not self.current_doc or not (0 <= box_idx < len(self.current_doc.boxes)):
            return False

        new_tx = txt_w.get("1.0", "end-1c")
        box = self.current_doc.boxes[box_idx]
        mutated = False
        if box.clean_text != new_tx:
            old_sp = box.speaker
            old_tx = box.clean_text
            box_uid = box.segs[0].record.uid if box.segs else None
            old_segs = [s.text for s in box.segs] if len(box.segs) > 1 else None
            try:
                self.current_doc.inject_box(box_idx, None, new_tx)
            except Exception as e:
                self.logger.exception(f"Failed to inject box {box_idx}:", e)
                self.set_status(f"Error updating box #{box_idx + 1}: {e}", is_error=True)
                return False

            new_segs = None
            if old_segs is not None:
                refreshed_box = next((b for b in self.current_doc.boxes if b.segs and b.segs[0].record.uid == box_uid), None)
                if refreshed_box:
                    new_segs = [s.text for s in refreshed_box.segs]

            delta = BoxEditDelta(
                box_index=box_idx,
                old_speaker=old_sp,
                new_speaker=old_sp,
                old_text=old_tx,
                new_text=new_tx,
                file_path=str(self.current_file_path or ""),
                box_uid=box_uid,
                source=getattr(self, "_current_edit_source", "keyboard"),
                old_seg_texts=old_segs,
                new_seg_texts=new_segs,
            )
            self.undo_journal.record(delta, label=f"Edit box #{box_idx + 1}")
            self._modified_boxes.add(box_idx)
            self._mark_document_dirty(self.current_file_path)
            try:
                self._update_raw_view()
            except Exception:
                pass
            mutated = True

        # Dynamically adjust text widget height to fit content (min 2, max 10)
        line_count = max(1, new_tx.count("\n") + 1)
        eff_height = max(2, min(10, line_count))
        try:
            if int(txt_w.cget("height")) != eff_height:
                txt_w.config(height=eff_height)
        except Exception:
            pass

        if gutter:
            try:
                gutter.config(state="normal", height=eff_height)
                gutter.delete("1.0", tk.END)
                gutter.insert("1.0", "\n".join(str(n) for n in range(1, line_count + 1)))
                self._apply_gutter_overflow_tag(gutter)
                gutter.config(state="disabled")
            except Exception:
                pass

        if hasattr(self, "cont_canvas"):
            self.cont_canvas.configure(scrollregion=self.cont_canvas.bbox("all"))

        self._highlight_ngui_tags_for_widget(txt_w)
        return mutated

    def _on_card_focus_in(self, box_idx: int) -> None:
        """Update active indicators and controls when a Box Card gains focus."""
        if getattr(self, "_suppress_continuous_events", False) or not self.current_doc:
            return

        self.is_box0_active = (box_idx == -1)
        if box_idx != -1 and 0 <= box_idx < len(self.current_doc.boxes):
            self.current_box_idx = box_idx

        self._highlight_active_card_header(box_idx)
        self._sync_header_controls_for_card(box_idx)
        self._update_raw_view()

    def _clear_card_registry(self) -> None:
        """Destroy and prune all stale card widget references (S4 / STALE-CARD-REGISTRY).

        Safe to call even if widgets are already destroyed. Clears _card_widgets entirely.
        Must be called whenever the document that produced the cards is unloaded so that
        destroyed Tk widget references do not persist in the registry (Rule 3 / Rule 11).
        """
        for _b_idx, card_info in list(self._card_widgets.items()):
            card = card_info.get("card")
            try:
                if card is not None and card.winfo_exists():
                    card.destroy()
            except Exception:
                pass
        self._card_widgets.clear()

    def _highlight_active_card_header(self, active_idx: int) -> None:
        """Highlight the header background of the active card in Continuous View."""
        t = self.theme
        if not hasattr(self, "_card_widgets"):
            return
        for b_idx, card_info in self._card_widgets.items():
            hdr = card_info.get("hdr")
            if not hdr or not hdr.winfo_exists():
                continue
            is_active = (b_idx == active_idx)
            if b_idx == -1:
                bg_col = t["highlight_bg"] if is_active else ("#dfd1f5" if self._is_light_theme() else "#2d1d29")
            else:
                bg_col = t["highlight_bg"] if is_active else t["bg_panel"]
            try:
                hdr.configure(bg=bg_col)
                for child in hdr.winfo_children():
                    if isinstance(child, (tk.Label, tk.Frame)):
                        child.configure(bg=bg_col)
            except Exception:
                pass

    def _sync_header_controls_for_card(self, box_idx: int) -> None:
        """Sync top ribbon controls (speaker, voice cue, box counter) to active card."""
        if not self.current_doc:
            return
        total = len(self.current_doc.boxes) if self.current_doc.boxes else 0
        if box_idx == -1:
            self.speaker_var.set("")
            self._speaker_ac_user_typed = False
            if hasattr(self, "entry_speaker"):
                self.entry_speaker.config(state="disabled")
            if hasattr(self, "btn_speaker_dropdown"):
                self.btn_speaker_dropdown.config(state="disabled")
            self.lbl_box_counter.config(text=f"Box: 0 / {total} (Story Metadata)")
            self.lbl_voice_cue.config(text="")
            if hasattr(self, "btn_prev"):
                self.btn_prev.config(state="disabled")
            if hasattr(self, "btn_next"):
                self.btn_next.config(state="normal" if total > 0 else "disabled")
        elif 0 <= box_idx < total:
            box = self.current_doc.boxes[box_idx]
            if hasattr(self, "entry_speaker"):
                self.entry_speaker.config(state="normal")
            if hasattr(self, "btn_speaker_dropdown"):
                self.btn_speaker_dropdown.config(state="normal")
            self.speaker_var.set(box.speaker)
            self._speaker_ac_user_typed = False
            self.lbl_box_counter.config(text=f"Box: {box_idx + 1} / {total}")
            if hasattr(self, "lbl_voice_cue"):
                self.lbl_voice_cue.config(text=f"Voice Cue: {box.voice_cue}" if box.voice_cue else "")
            if hasattr(self, "lbl_segs_badge"):
                self.lbl_segs_badge.config(text=f"{len(box.segs)} segs" if len(box.segs) > 1 else "")
            if hasattr(self, "btn_prev"):
                can_prev = (box_idx > 0) or (self.current_doc and self.current_doc.has_metadata())
                self.btn_prev.config(state="normal" if can_prev else "disabled")
            if hasattr(self, "btn_next"):
                self.btn_next.config(state="normal" if box_idx < total - 1 else "disabled")

    def _copy_single_card_dialogue(self, box_idx: int) -> None:
        """Copy dialogue from a single Box Card to clipboard."""
        if self.current_doc and 0 <= box_idx < len(self.current_doc.boxes):
            text = self.current_doc.boxes[box_idx].clean_text
            self.clipboard_clear()
            self.clipboard_append(text)
            self.show_toast(f"📋 Copied dialogue from Box #{box_idx + 1}")

    def _card_shortcut_wrap(self, w: tk.Text, open_t: str, close_t: str) -> None:
        """Wrap selected text in card editor with NGUI tags."""
        try:
            sel_first = w.index("sel.first")
            sel_last = w.index("sel.last")
            txt = w.get(sel_first, sel_last)
            w.delete(sel_first, sel_last)
            w.insert(sel_first, f"{open_t}{txt}{close_t}")
        except tk.TclError:
            w.insert(tk.INSERT, f"{open_t}{close_t}")
        self._commit_widget_edit(w)

    def _highlight_ngui_tags_for_widget(self, w: tk.Text) -> None:
        """Syntax-color NGUI tags and pixel-calibrated overflow within a specific Text widget."""
        if not w.winfo_exists():
            return
        if self.var_preview_compiled.get():
            self._apply_overflow_highlights(w)
            return
        w.tag_remove("ngui_tag", "1.0", tk.END)
        tx = w.get("1.0", "end-1c")
        for m in NGUI_TAG_RE.finditer(tx):
            w.tag_add("ngui_tag", f"1.0 + {m.start()}c", f"1.0 + {m.end()}c")
        self._apply_overflow_highlights(w)
        w.tag_raise("ngui_tag")

    def on_copy_script(self) -> None:
        """Copy dialogue across all boxes using CSIF format (Part C.3)."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return

        self._commit_widget_edit()
        csif_text = serialize(self.current_doc, scope="all", include_metadata="auto")
        self.safe_clipboard_set(csif_text)
        box_count = len(self.current_doc.boxes)
        self.show_toast(f"📋 Copied {box_count} boxes (CSIF format)")
        self.lbl_status.config(text=f"Copied script ({box_count} boxes in CSIF format) to clipboard")

    on_copy_script_triple_enter = on_copy_script

    def _on_cont_mousewheel(self, event) -> str:
        """Scroll continuous stream canvas smoothly and prevent child widgets from eating the scroll event."""
        if hasattr(self, "cont_canvas") and self.cont_canvas.winfo_exists():
            delta = getattr(event, "delta", 0)
            if delta:
                self.cont_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        return "break"

    def _resize_cont_canvas(self, width: int) -> None:
        """Debounced canvas window resize to eliminate sash-drag stutter."""
        self._cont_resize_job = None
        if hasattr(self, "cont_canvas") and hasattr(self, "cont_canvas_window") and self.cont_canvas.winfo_exists():
            try:
                self.cont_canvas.itemconfig(self.cont_canvas_window, width=width)
            except Exception:
                pass

    def _on_toggle_select_box_mode(self) -> None:
        """Toggle multi-box selection mode in both Dialogue and All Script views."""
        enabled = bool(self.var_select_box_mode.get())
        if not enabled:
            self._selected_boxes.clear()
        if self.var_continuous_view.get():
            txt = getattr(self, "txt_all_script", None)
            if txt is not None and txt.winfo_exists() and self.current_doc and getattr(self, "_all_script_sel_ranges", None):
                was_disabled = (str(txt.cget("state")) == "disabled")
                if was_disabled:
                    txt.config(state="normal")
                try:
                    for b_idx, (s_pos, e_pos) in list(self._all_script_sel_ranges.items()):
                        tok = ("[x] " if b_idx in self._selected_boxes else "[ ] ") if enabled else "    "
                        tags = txt.tag_names(s_pos)
                        txt.delete(s_pos, e_pos)
                        txt.insert(s_pos, tok, tags)
                        ln_s, col_s = s_pos.split(".")
                        self._all_script_sel_ranges[b_idx] = (s_pos, f"{ln_s}.{int(col_s) + len(tok)}")
                finally:
                    if was_disabled:
                        txt.config(state="disabled")
            else:
                self._render_continuous_view()
            if hasattr(self, "cb_dialogue_select") and self.cb_dialogue_select.winfo_exists():
                self.cb_dialogue_select.pack_forget()
        else:
            self._update_dialogue_select_box_ui()
        self.show_toast(f"Select Box mode {'enabled' if enabled else 'disabled'}")

    def _update_dialogue_select_box_ui(self) -> None:
        """Update inline Select Box checkbox in Dialogue view header."""
        if not hasattr(self, "cb_dialogue_select") or not self.cb_dialogue_select.winfo_exists():
            return
        if not self.var_select_box_mode.get() or self.var_continuous_view.get() or not self.current_doc:
            self.cb_dialogue_select.pack_forget()
            return
        is_box0 = getattr(self, "is_box0_active", False)
        b_idx = -1 if is_box0 else self.current_box_idx
        b_num = 0 if is_box0 else (self.current_box_idx + 1)
        self.var_dialogue_box_sel.set(b_idx in self._selected_boxes)
        sel_count = len(self._selected_boxes)
        self.cb_dialogue_select.config(text=f"Select Box #{b_num} ({sel_count} selected)")
        if not self.cb_dialogue_select.winfo_ismapped():
            if hasattr(self, "lbl_gd_title") and self.lbl_gd_title.winfo_exists():
                self.cb_dialogue_select.pack(side="left", padx=(10, 0), after=self.lbl_gd_title)
            else:
                self.cb_dialogue_select.pack(side="left", padx=(10, 0))

    def _on_dialogue_box_sel_toggle(self) -> None:
        """Toggle selection of current box in Dialogue view."""
        is_box0 = getattr(self, "is_box0_active", False)
        b_idx = -1 if is_box0 else self.current_box_idx
        if self.var_dialogue_box_sel.get():
            self._selected_boxes.add(b_idx)
        else:
            self._selected_boxes.discard(b_idx)
        self._update_dialogue_select_box_ui()

    def _reset_speaker_pin(self, notify: bool = False) -> None:
        """Clear pinned speaker state and restore button visual styling."""
        was_pinned = bool(getattr(self, "_is_speaker_pinned", False))
        self._is_speaker_pinned = False
        self._pinned_speaker_name = None
        if hasattr(self, "btn_pin_speaker") and self.btn_pin_speaker.winfo_exists():
            t = self.theme
            btn_bg = t.get("bg_panel", "#faf8fe")
            self.btn_pin_speaker.config(bg=btn_bg, relief="flat")
        if notify and was_pinned:
            self.show_toast("Speaker Unpinned")

    def _on_toggle_pin_speaker(self) -> None:
        """Toggle persistent speaker pinning (captures canonical speaker identity; U-02)."""
        if self._is_speaker_pinned:
            self._reset_speaker_pin(notify=True)
            return
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return
        if getattr(self, "is_box0_active", False):
            captured = ""
        elif 0 <= self.current_box_idx < len(self.current_doc.boxes):
            captured = self.current_doc.boxes[self.current_box_idx].speaker
        else:
            captured = ""
        self._is_speaker_pinned = True
        self._pinned_speaker_name = captured
        t = self.theme
        if hasattr(self, "btn_pin_speaker") and self.btn_pin_speaker.winfo_exists():
            self.btn_pin_speaker.config(bg=t["highlight_bg"], relief="sunken")
        disp = captured if captured else "(Narration)"
        self.show_toast(f"📌 Speaker Pinned: '{disp}' locked for Next/Prev & New Box")

    def on_select_whole_story(self) -> None:
        """Select whole story / all text across document."""
        if self.var_continuous_view.get():
            if self.current_doc and hasattr(self, "txt_all_script") and self.txt_all_script.winfo_exists():
                self.txt_all_script.focus_set()
                self.txt_all_script.tag_add("sel", "1.0", "end-1c")
            elif hasattr(self, "txt_continuous") and self.txt_continuous.winfo_exists():
                self.txt_continuous.focus_set()
                self.txt_continuous.tag_add("sel", "1.0", "end-1c")
            self.show_toast("Selected active story")
        else:
            if hasattr(self, "txt_dialogue"):
                self.txt_dialogue.focus_set()
                self.txt_dialogue.tag_add("sel", "1.0", "end-1c")
                self.show_toast("Selected all text in current box")

    def on_text_cut(self) -> None:
        """Cut text in active editor to clipboard and commit immediately."""
        target = self.txt_dialogue
        if self.var_continuous_view.get() and hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
            target = self._get_card_text_widget(self.current_box_idx)
        self._current_edit_source = "cut"
        try:
            target.event_generate("<<Cut>>")
            self._commit_widget_edit(target)
        except Exception:
            pass
        finally:
            self._current_edit_source = "keyboard"

    def on_text_copy(self) -> None:
        """Copy text in active editor to clipboard."""
        target = self.txt_dialogue
        if self.var_continuous_view.get() and hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
            target = self._get_card_text_widget(self.current_box_idx)
        try:
            target.event_generate("<<Copy>>")
        except Exception:
            pass

    def on_text_paste(self) -> None:
        """Paste text in active editor with delimiter-awareness."""
        target = self.txt_dialogue
        idx = self.current_box_idx
        if self.var_continuous_view.get() and hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
            target = self._get_card_text_widget(self.current_box_idx)
        res = self._on_card_paste_caret(idx, target)
        if res != "break":
            try:
                target.event_generate("<<Paste>>")
            except Exception:
                pass

    def _push_undo(self, label: str = "Edit") -> None:
        """Fallback hook for callers expecting _push_undo; structural handlers record typed deltas."""
        pass

    # -------------------------------------------------------------------------
    # S2: Per-Document Dirty Contract Helpers
    # -------------------------------------------------------------------------

    def _mark_document_dirty(self, file_path: Optional[Union[str, Path]]) -> None:
        """Flag-only dirty marker — ZERO Tk calls, ZERO dock/title rebuilds (Rule 13 / S2).

        Mutates only open_documents[path]["dirty"] and self.is_dirty.
        Safe to call from worker threads (BatchTranslateDialog.worker) provided ZERO Tk ops follow.
        """
        if not file_path:
            return
        p = Path(file_path).resolve()
        if p in self.open_documents:
            self.open_documents[p]["dirty"] = True
        if self.current_file_path and Path(self.current_file_path).resolve() == p:
            self.is_dirty = True

    def _dirty_state_changed(self) -> None:
        """Pure UI synchronization: title *, Opened Files dock, undo/redo menu states (S2).

        Mirrors self.is_dirty from open_documents[path]["dirty"] when the active document is cached.
        When the active path is NOT in open_documents (e.g., test_34 synthetic tmp path), PRESERVES
        the current self.is_dirty value unchanged.
        Calls _refresh_opened_files_list() exactly once.
        NEVER derives dirty state from undo_journal.is_clean() — that was the cross-file clobber bug.
        """
        if self.current_file_path:
            p = Path(self.current_file_path).resolve()
            if p in self.open_documents:
                # Mirror from authoritative per-document entry
                self.is_dirty = bool(self.open_documents[p].get("dirty", False))
            # If NOT in open_documents: preserve self.is_dirty unchanged (do not reset to False)

        dirty_marker = "*" if self.is_dirty else ""
        file_name = self.current_file_path.name if self.current_file_path else "Untitled"
        try:
            self.title(f"Misora: Story Editor - {file_name}{dirty_marker}")
        except Exception:
            pass

        self._refresh_opened_files_list()
        self._sync_edit_menu_states()

    def _record_saved_checkpoint(self, file_path: Optional[Union[str, Path]],
                                  doc: Optional[Any], plain_text: str = "") -> None:
        """Record saved-state fingerprint for a document (S2 / Rule 13).

        Story docs: SHA-256 of doc.to_v2_text(). Plain-text: SHA-256 of plain_text.
        Called at: open_file() fresh load, open_file() reload_from_disk=True, on_save() primary success.
        Never mutates dirty flags; purely stores a comparison baseline.
        """
        if not file_path:
            return
        key = str(Path(file_path).resolve())
        try:
            if doc is not None:
                content = doc.to_v2_text()
            else:
                content = plain_text
            self._saved_state_checkpoints[key] = hashlib.sha256(
                content.encode("utf-8", errors="replace")
            ).hexdigest()
        except Exception:
            pass

    def _evaluate_checkpoints_for_op(self, op: Any) -> None:
        """After undo/redo delta loop: compare live fingerprints to saved checkpoints (S2).

        For each path touched by the op:
        - If a checkpoint exists and the live fingerprint matches → mark clean.
        - If no checkpoint exists → leave dirty as set by _mark_document_dirty (never clear speculatively).
        """
        touched: set = set()
        for delta in op.deltas:
            fp = getattr(delta, "file_path", None)
            if fp:
                try:
                    touched.add(Path(fp).resolve())
                except Exception:
                    pass
            elif hasattr(delta, "per_file"):
                for item in delta.per_file:
                    try:
                        fpath_str = item[0]
                        touched.add(Path(fpath_str).resolve())
                    except Exception:
                        pass
        if self.current_file_path:
            try:
                touched.add(Path(self.current_file_path).resolve())
            except Exception:
                pass

        for p in touched:
            key = str(p)
            entry = self.open_documents.get(p)
            if entry is not None:
                if key not in self._saved_state_checkpoints:
                    # No baseline — cannot determine clean; leave dirty flag as-is
                    continue
                saved_fp = self._saved_state_checkpoints[key]
                try:
                    doc = entry.get("doc")
                    if doc is not None:
                        live_content = doc.to_v2_text()
                    else:
                        live_content = entry.get("plain_text", "")
                    live_fp = hashlib.sha256(live_content.encode("utf-8", errors="replace")).hexdigest()
                except Exception:
                    continue

                is_clean = (live_fp == saved_fp)
                entry["dirty"] = not is_clean
                if self.current_file_path:
                    try:
                        if Path(self.current_file_path).resolve() == p:
                            self.is_dirty = not is_clean
                    except Exception:
                        pass
            elif self.current_file_path:
                try:
                    if Path(self.current_file_path).resolve() == p and hasattr(self, "undo_journal"):
                        is_clean = self.undo_journal.is_clean(p)
                        self.is_dirty = not is_clean
                except Exception:
                    pass

    def _sync_clean_view_to_current_box(self) -> None:
        """
        Synchronize Page View dialogue and header controls to current_box_idx
        without tearing down the entire Continuous View canvas.
        """
        if not self.current_doc or not self.current_doc.boxes:
            return
        total = len(self.current_doc.boxes)
        self.current_box_idx = max(0, min(self.current_box_idx, total - 1))
        box = self.current_doc.boxes[self.current_box_idx]

        if hasattr(self, "speaker_var"):
            self.speaker_var.set(box.speaker)
        self._speaker_ac_user_typed = False
        if hasattr(self, "lbl_box_counter"):
            self.lbl_box_counter.config(text=f"Box: {self.current_box_idx + 1} / {total}")
        if hasattr(self, "lbl_voice_cue"):
            self.lbl_voice_cue.config(text=f"Voice Cue: {box.voice_cue}" if box.voice_cue else "")
        if hasattr(self, "lbl_segs_badge"):
            self.lbl_segs_badge.config(text=f"{len(box.segs)} segs" if len(box.segs) > 1 else "")
        self._update_dialogue_select_box_ui()

        if hasattr(self, "txt_dialogue") and self.txt_dialogue.winfo_exists() and not self.var_continuous_view.get():
            self.txt_dialogue.config(state="normal")
            self.txt_dialogue.delete("1.0", tk.END)
            if self.var_preview_compiled.get():
                self._insert_compiled_ngui_text(self.txt_dialogue, "1.0", box.clean_text)
                self.txt_dialogue.config(state="disabled")
            else:
                self.txt_dialogue.insert("1.0", box.clean_text)
                self._highlight_ngui_tags()
                self._highlight_dialogue_matches()
            self._auto_resize_dialogue_box()
        self._update_char_overflow_indicator()

        if hasattr(self, "btn_prev"):
            can_prev = (self.current_box_idx > 0) or (self.current_doc and self.current_doc.has_metadata())
            self.btn_prev.config(state="normal" if can_prev else "disabled")
        if hasattr(self, "btn_next"):
            self.btn_next.config(state="normal" if self.current_box_idx < total - 1 else "disabled")

        self._update_raw_view()

    def on_box_new(self) -> None:
        """Create and insert a new dialogue box after current box."""
        if not self.current_doc:
            self.show_toast("No story document loaded")
            return

        if getattr(self, "_is_speaker_pinned", False) and self._pinned_speaker_name is not None:
            cur_sp = self._pinned_speaker_name
        else:
            cur_sp = ""
        ins_idx = self.current_box_idx + 1 if self.current_doc.boxes else 0
        new_snap = BoxSnapshot(
            speaker=cur_sp,
            voice_cue="",
            kind="print" if cur_sp else "tag",
            seg_texts=[""],
        )
        self.current_doc.insert_box(ins_idx, new_snap)
        self.undo_journal.record(
            BoxStructuralDelta(
                op_type="insert",
                box_index=ins_idx,
                snapshots=[new_snap],
                file_path=str(self.current_file_path or ""),
            ),
            label="New Box"
        )
        self.current_box_idx = ins_idx
        self._mark_document_dirty(self.current_file_path)
        self._modified_boxes.add(ins_idx)
        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
            self._render_continuous_view()
        self._sync_clean_view_to_current_box()
        self._dirty_state_changed()
        self.show_toast(f"➕ Created new Box #{ins_idx + 1}")

    def on_box_copy(self) -> None:
        """Copy selected box(es) or current box to box clipboard using CSIF format (Part C.1)."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return
        self._commit_widget_edit()
        targets = sorted(self._selected_boxes) if self._selected_boxes else [self.current_box_idx]
        targets = [idx for idx in targets if 0 <= idx < len(self.current_doc.boxes)]
        if not targets:
            return

        include_meta = "auto"
        if getattr(self, "is_box0_active", False) or (-1 in getattr(self, "_selected_boxes", set())):
            include_meta = True

        csif_str = serialize(
            self.current_doc,
            scope="selection",
            box_indices=targets,
            include_metadata=include_meta
        )

        self._box_clipboard = [BoxSnapshot.from_box(self.current_doc.boxes[idx]) for idx in targets]
        self._box_clipboard_text = csif_str
        self.safe_clipboard_set(csif_str)
        self.show_toast(f"📋📦 Copied {len(targets)} box(es) (CSIF)")
        self.lbl_status.config(text=f"Copied {len(targets)} box(es) in CSIF format to clipboard")

    def on_box_cut(self) -> None:
        """Cut selected box(es) or current box in one undo batch."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return
        raw_targets = sorted(self._selected_boxes) if self._selected_boxes else [self.current_box_idx]
        raw_targets = [idx for idx in raw_targets if 0 <= idx < len(self.current_doc.boxes)]
        if not raw_targets:
            return

        unlocked_targets = [idx for idx in raw_targets if not self.is_box_locked(idx)]
        locked_count = len(raw_targets) - len(unlocked_targets)
        if locked_count > 0:
            self.show_toast(f"🔒 Skipped {locked_count} locked box(es).")
        if not unlocked_targets:
            return

        targets = unlocked_targets
        self._selected_boxes = set(targets)
        self.on_box_copy()
        deleted_snapshots = self.current_doc.delete_boxes(targets)
        self.undo_journal.record(
            BoxStructuralDelta(
                op_type="delete",
                box_index=targets[0],
                snapshots=deleted_snapshots,
                indices=list(targets),
                file_path=str(self.current_file_path or ""),
            ),
            label="Cut Box(es)"
        )
        self._selected_boxes.clear()
        self._resync_box_indices_from_uids()
        if self.current_box_idx >= len(self.current_doc.boxes):
            self.current_box_idx = max(0, len(self.current_doc.boxes) - 1)
        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()
        self.show_toast(f"✂📦 Cut {len(targets)} box(es)")

    @staticmethod
    def _clone_box_snapshot(snap: BoxSnapshot) -> BoxSnapshot:
        """Return an independent deep copy of a BoxSnapshot preserving all 6 fields."""
        return BoxSnapshot(
            speaker=snap.speaker,
            voice_cue=snap.voice_cue,
            kind=snap.kind,
            seg_texts=list(snap.seg_texts),
            raw_breaks=list(snap.raw_breaks) if snap.raw_breaks is not None else None,
            extra_args=[list(ea) for ea in snap.extra_args] if snap.extra_args is not None else None,
        )

    def _show_box_paste_mode_dialog(
        self,
        block_count: int,
        sp_desc: str,
        selected_targets: List[int],
        total_boxes: int,
        is_box0: bool = False,
    ) -> Optional[str]:
        """Modal 3-way Paste Box chooser: Insert after Box #N (or before #1 on Box 0), Replace selected, or Cancel."""
        t = self.theme
        dlg = tk.Toplevel(self)
        dlg.title("Paste Box(es)")
        dlg.transient(self)
        dlg.resizable(False, False)
        dlg.configure(bg=t["bg_panel"])

        choice: List[Optional[str]] = [None]

        def _choose(val: Optional[str]) -> None:
            choice[0] = val
            safe_grab_release(dlg)
            if dlg.winfo_exists():
                dlg.destroy()

        frame = tk.Frame(dlg, bg=t["bg_panel"], padx=16, pady=14)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=f"Paste {block_count} Box(es) from Clipboard",
            font=("Segoe UI", 11, "bold"),
            fg=t["misora_pink"],
            bg=t["bg_panel"],
        ).pack(anchor="w", pady=(0, 6))

        if is_box0 or total_boxes == 0:
            ins_desc = "before Box #1" if total_boxes > 0 else "at beginning"
        else:
            ins_desc = f"after Box #{self.current_box_idx + 1}"

        sel_count = len(selected_targets)
        has_box0_sel = any(i < 0 for i in selected_targets)
        locked_targets = [i for i in selected_targets if 0 <= i < total_boxes and self.is_box_locked(i)]
        can_replace = (
            total_boxes > 0
            and sel_count > 0
            and not has_box0_sel
            and sel_count == block_count
            and not locked_targets
        )

        notes = [f"Speakers: {sp_desc}"]
        if sel_count == 0:
            notes.append("Select target box(es) first to Replace")
        elif has_box0_sel:
            notes.append("Box 0 (metadata) cannot be replaced.")
        elif sel_count != block_count:
            notes.append(f"Selected {sel_count} boxes, but clipboard contains {block_count} boxes.")
        elif locked_targets:
            locked_str = ", ".join(f"#{i + 1}" for i in locked_targets)
            notes.append(f"Locked target(s) {locked_str} block Replace.")
        else:
            sel_str = ", ".join(f"#{i + 1}" for i in selected_targets[:5])
            if sel_count > 5:
                sel_str += f", ... (+{sel_count - 5})"
            notes.append(f"Replace targets: {sel_str}")

        tk.Label(
            frame,
            text="\n".join(notes),
            font=("Segoe UI", 9),
            fg=t["fg_text"],
            bg=t["bg_panel"],
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        btn_ins = tk.Button(
            frame,
            text=f"Insert {ins_desc}",
            font=("Segoe UI", 9, "bold"),
            bg=t["highlight_bg"],
            fg=best_contrast_fg(t["highlight_bg"]),
            relief="raised",
            bd=1,
            padx=10,
            pady=5,
            cursor="hand2",
            command=lambda: _choose("insert"),
        )
        btn_ins.pack(fill="x", pady=2)

        rep_label = (
            f"Replace {sel_count} Selected Box(es)"
            if sel_count > 0
            else "Replace (Select target box(es) first to Replace)"
        )
        btn_rep = tk.Button(
            frame,
            text=rep_label,
            font=("Segoe UI", 9),
            bg=t["bg_editor"],
            fg=t["fg_text"] if can_replace else t["fg_muted"],
            relief="raised",
            bd=1,
            padx=10,
            pady=5,
            cursor="hand2" if can_replace else "arrow",
            state="normal" if can_replace else "disabled",
            command=lambda: _choose("replace"),
        )
        btn_rep.pack(fill="x", pady=2)

        btn_cancel = tk.Button(
            frame,
            text="Cancel",
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
            relief="groove",
            bd=1,
            padx=10,
            pady=5,
            cursor="hand2",
            command=lambda: _choose(None),
        )
        btn_cancel.pack(fill="x", pady=(6, 0))

        dlg.bind("<Escape>", lambda e: _choose(None))
        dlg.protocol("WM_DELETE_WINDOW", lambda: _choose(None))
        dlg.update_idletasks()
        try:
            px = self.winfo_rootx() + max(0, (self.winfo_width() - dlg.winfo_width()) // 2)
            py = self.winfo_rooty() + max(0, (self.winfo_height() - dlg.winfo_height()) // 2)
            dlg.geometry(f"+{px}+{py}")
        except Exception:
            pass
        try:
            dlg.grab_set()
            dlg.focus_set()
            self.wait_window(dlg)
        except Exception:
            pass
        return choice[0]

    def on_box_paste(self, confirm: bool = True, mode: Optional[str] = None) -> None:
        """Paste box(es) from clipboard: Insert after cursor (or before Box #1 on Box 0) or Replace _selected_boxes (U-01)."""
        if not self.current_doc:
            self.show_toast("No story document loaded")
            return

        clip_text = self.safe_clipboard_get()
        if getattr(self, "_box_clipboard_text", None) != clip_text:
            self._box_clipboard = None
            self._box_clipboard_text = None

        snaps_to_apply: List[BoxSnapshot] = []
        if getattr(self, "_box_clipboard", None):
            snaps_to_apply = [self._clone_box_snapshot(snap) for snap in self._box_clipboard]
        elif clip_text.strip():
            try:
                result = parse(clip_text)
            except Exception as exc:
                self.show_toast(f"Invalid clipboard script: {exc}")
                self.set_status(f"Paste aborted: {exc}", is_error=True)
                return
            parsed_blocks = result.blocks
            if parsed_blocks:
                snaps_to_apply = [
                    BoxSnapshot(
                        speaker="" if b.is_narration else b.speaker,
                        voice_cue="",
                        kind="tag" if (b.is_narration or not b.speaker) else "print",
                        seg_texts=[b.text],
                    )
                    for b in parsed_blocks
                ]

        if not snaps_to_apply:
            self.show_toast("Box clipboard is empty")
            return

        block_count = len(snaps_to_apply)
        first_speakers = [(s.speaker if s.speaker else "(Narration)") for s in snaps_to_apply[:3]]
        sp_desc = ", ".join(first_speakers)
        if block_count > 3:
            sp_desc += f", ... (+{block_count - 3} more)"

        total_boxes = len(self.current_doc.boxes)
        selected_targets = sorted(getattr(self, "_selected_boxes", set()))
        is_box0 = bool(getattr(self, "is_box0_active", False))

        if mode is None:
            if confirm:
                chosen = self._show_box_paste_mode_dialog(
                    block_count=block_count,
                    sp_desc=sp_desc,
                    selected_targets=selected_targets,
                    total_boxes=total_boxes,
                    is_box0=is_box0,
                )
                if not chosen:
                    return
                mode = chosen
            else:
                mode = "insert"

        if mode == "insert":
            if is_box0 or not self.current_doc.boxes:
                ins_idx = 0
            else:
                ins_idx = self.current_box_idx + 1
            self.undo_journal.begin_batch(f"Paste {block_count} Box(es)")
            try:
                for offset, snap in enumerate(snaps_to_apply):
                    target_idx = ins_idx + offset
                    self.current_doc.insert_box(target_idx, snap)
                    self._modified_boxes.add(target_idx)

                self.undo_journal.record(
                    BoxStructuralDelta(
                        op_type="insert",
                        box_index=ins_idx,
                        snapshots=snaps_to_apply,
                        file_path=str(self.current_file_path or ""),
                    )
                )
            finally:
                self.undo_journal.end_batch()

            self.is_box0_active = False
            self.current_box_idx = ins_idx + len(snaps_to_apply) - 1
            self._resync_box_indices_from_uids()
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            self._update_views()
            self.show_toast(f"📥📦 Inserted {len(snaps_to_apply)} box(es)")
            return

        if mode != "replace":
            return

        # Strict Replace Mode Contract (U-01):
        if not selected_targets:
            self.show_toast("No boxes selected to replace.")
            self.set_status("Paste Replace aborted: no boxes selected.", is_error=True)
            return

        if any(i < 0 or i >= total_boxes for i in selected_targets):
            self.show_toast("Box 0 (metadata) cannot be replaced.")
            self.set_status("Paste Replace aborted: Box 0 (metadata) cannot be replaced.", is_error=True)
            return

        if len(selected_targets) != block_count:
            msg = f"Selected {len(selected_targets)} boxes, but clipboard contains {block_count} boxes."
            self.show_toast(msg)
            self.set_status(f"Paste Replace aborted: {msg}", is_error=True)
            return

        locked_list = [i for i in selected_targets if self.is_box_locked(i)]
        if locked_list:
            locked_str = ", ".join(f"#{i + 1}" for i in locked_list)
            msg = f"Box(es) {locked_str} are locked. No boxes replaced."
            self.show_toast(f"🔒 {msg}")
            self.set_status(f"Paste Replace aborted: {msg}", is_error=True)
            return

        # Stage & validate all replacement targets BEFORE mutating any record
        staged_ops: List[Tuple[int, BoxSnapshot]] = []
        doc_rec_uids = {r.uid for r in self.current_doc.records}

        for t_idx, snap in zip(selected_targets, snaps_to_apply):
            if not isinstance(snap, BoxSnapshot) or snap.kind not in ("print", "tag") or not snap.seg_texts:
                self.set_status("Paste Replace aborted: invalid BoxSnapshot.", is_error=True)
                self.show_toast("Paste Replace aborted: invalid snapshot")
                return
            t_box = self.current_doc.boxes[t_idx]
            if any(seg.record.uid not in doc_rec_uids for seg in t_box.segs):
                self.set_status("Paste Replace aborted: unowned record in target box.", is_error=True)
                return
            staged_ops.append((t_idx, self._clone_box_snapshot(snap)))

        # Transactional rollback checkpoint in case replace_box raises mid-batch
        backup_records = copy.deepcopy(self.current_doc.records)
        backup_removed = set(self.current_doc.removed_records)
        backup_mod_uids = set(getattr(self, "_modified_box_uids", set()))
        backup_jp_by_uid = dict(getattr(self, "_original_jp_by_uid", {}))
        file_str = str(self.current_file_path or "")
        recorded_deltas: List[BoxSnapshotReplaceDelta] = []

        try:
            for t_idx, new_snap in staged_ops:
                old_uid = self.current_doc.boxes[t_idx].uid
                old_snap = self.current_doc.replace_box(t_idx, new_snap)
                new_uid = self.current_doc.boxes[t_idx].uid
                if old_uid in self._original_jp_by_uid:
                    jp_val = self._original_jp_by_uid.pop(old_uid)
                    self._original_jp_by_uid[new_uid] = jp_val
                    if hasattr(self, "sync_manager") and self.sync_manager is not None:
                        self.sync_manager.register_jp_key(new_uid, jp_val)
                if not hasattr(self, "_modified_box_uids"):
                    self._modified_box_uids = set()
                self._modified_box_uids.add(new_uid)
                recorded_deltas.append(
                    BoxSnapshotReplaceDelta(
                        box_index=t_idx,
                        old_snapshot=old_snap,
                        new_snapshot=self._clone_box_snapshot(new_snap),
                        file_path=file_str,
                        box_uid=None,
                        source="box_replace",
                    )
                )
        except Exception as exc:
            self.current_doc.records = backup_records
            self.current_doc.removed_records = backup_removed
            self.current_doc._rebuild_boxes()
            self._modified_box_uids = backup_mod_uids
            self._original_jp_by_uid = backup_jp_by_uid
            self._resync_box_indices_from_uids()
            self.logger.exception("Box Replace paste failed; rolled back document:", exc)
            self.set_status(f"Replace paste failed (rolled back): {exc}", is_error=True)
            self.show_toast("Replace paste failed; document unchanged")
            return

        self.undo_journal.begin_batch(f"Replace {len(recorded_deltas)} Box(es)")
        try:
            for delta in recorded_deltas:
                self.undo_journal.record(delta)
        finally:
            self.undo_journal.end_batch()

        self.is_box0_active = False
        self.current_box_idx = staged_ops[-1][0]
        self._resync_box_indices_from_uids()
        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()

        msg = f"Replaced {len(recorded_deltas)} box(es)"
        self.show_toast(f"🔄📦 {msg}")
        self.lbl_status.config(text=msg)

    def _on_card_paste_caret(self, box_idx: int, txt_widget: tk.Text) -> str:
        """Intercept paste on card editors to perform caret-aware paste or CSIF handling."""
        clip_text = self.safe_clipboard_get()
        if not clip_text:
            return ""

        if sniff_format(clip_text) == "csif":
            self._handle_editor_csif_paste(txt_widget, clip_text)
            return "break"

        if "\n\n\n" not in clip_text:
            return ""

        chunks = clip_text.split("\n\n\n")
        if len(chunks) <= 1:
            return ""

        try:
            sel_ranges = txt_widget.tag_ranges("sel")
            if sel_ranges:
                head = txt_widget.get("1.0", sel_ranges[0])
                tail = txt_widget.get(sel_ranges[1], "end-1c")
            else:
                ins = txt_widget.index("insert")
                head = txt_widget.get("1.0", ins)
                tail = txt_widget.get(ins, "end-1c")
        except Exception:
            head = txt_widget.get("1.0", "end-1c")
            tail = ""

        if not self.current_doc or not self.current_doc.boxes:
            return "break"

        # Check if all target boxes are locked (Technical Guard 2 / BUG-10)
        total_boxes = len(self.current_doc.boxes)
        targets_to_mutate = []
        for offset in range(len(chunks)):
            t_idx = box_idx + offset
            if t_idx < total_boxes:
                if not self.is_box_locked(t_idx):
                    targets_to_mutate.append(t_idx)
            else:
                targets_to_mutate.append(t_idx)

        if not targets_to_mutate:
            self.show_toast("🔒 All target boxes are locked against edits.")
            return "break"

        mutated_count = 0
        self.undo_journal.begin_batch("Multi-box Delimiter Paste")
        try:
            if not self.is_box_locked(box_idx):
                b0 = self.current_doc.boxes[box_idx]
                first_text = head + chunks[0]
                self.current_doc.inject_box(box_idx, None, first_text)
                self.undo_journal.record(
                    BoxEditDelta(
                        box_index=box_idx,
                        old_speaker=b0.speaker,
                        new_speaker=b0.speaker,
                        old_text=b0.clean_text,
                        new_text=first_text,
                        file_path=str(self.current_file_path or ""),
                        box_uid=b0.uid,
                        source="paste_caret",
                    )
                )
                self._modified_boxes.add(box_idx)
                mutated_count += 1

            for offset, chunk in enumerate(chunks[1:], start=1):
                target_idx = box_idx + offset
                if target_idx < len(self.current_doc.boxes) and self.is_box_locked(target_idx):
                    continue
                is_last = (offset == len(chunks) - 1)
                if target_idx < len(self.current_doc.boxes):
                    orig_b = self.current_doc.boxes[target_idx]
                    orig_text = orig_b.clean_text
                    new_text = (chunk + tail + orig_text) if is_last else (chunk + orig_text)
                    self.current_doc.inject_box(target_idx, None, new_text)
                    self.undo_journal.record(
                        BoxEditDelta(
                            box_index=target_idx,
                            old_speaker=orig_b.speaker,
                            new_speaker=orig_b.speaker,
                            old_text=orig_text,
                            new_text=new_text,
                            file_path=str(self.current_file_path or ""),
                            box_uid=orig_b.uid,
                            source="paste_caret",
                        )
                    )
                    self._modified_boxes.add(target_idx)
                    mutated_count += 1
                else:
                    new_text = (chunk + tail) if is_last else chunk
                    snap = BoxSnapshot(speaker="", voice_cue="", kind="tag", seg_texts=[new_text])
                    self.current_doc.insert_box(target_idx, snap)
                    self.undo_journal.record(
                        BoxStructuralDelta(
                            op_type="insert",
                            box_index=target_idx,
                            snapshots=[snap],
                            file_path=str(self.current_file_path or ""),
                        )
                    )
                    self._modified_boxes.add(target_idx)
                    mutated_count += 1
        finally:
            self.undo_journal.end_batch()

        if mutated_count > 0:
            self._resync_box_indices_from_uids()
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
                self._render_continuous_view()
            self._sync_clean_view_to_current_box()
            self.show_toast(f"Pasted across {mutated_count} box(es)")
        else:
            self.show_toast("🔒 Target box(es) were locked; no edits applied.")
        return "break"

    def _on_size_dropdown_clicked(self) -> None:
        """Show dropdown menu for selecting font size scaling tags."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Small (80%)", command=lambda: self.on_insert_font_size("80%"))
        menu.add_command(label="Normal (100% / Reset)", command=lambda: self.on_insert_font_size(None))
        menu.add_command(label="Large (130%)", command=lambda: self.on_insert_font_size("130%"))
        menu.add_command(label="Extra Large / Roar (160%)", command=lambda: self.on_insert_font_size("160%"))
        menu.add_command(label="Huge (200%)", command=lambda: self.on_insert_font_size("200%"))
        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def on_insert_font_size(self, size_val: Optional[str]) -> None:
        """Insert font size tags (<size=...>...</size>) around selection or at caret."""
        if not getattr(self, "is_box0_active", False) and self.current_doc and self.is_box_locked(self.current_box_idx):
            self.show_toast(f"Box #{self.current_box_idx + 1} is locked.")
            return

        if self.var_continuous_view.get() and self.current_doc:
            self.var_continuous_view.set(False)
            self._on_toggle_continuous_view()

        target = self.txt_dialogue
        if self.var_continuous_view.get() and hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
            target = self._get_card_text_widget(self.current_box_idx)

        if size_val:
            open_t = f"<size={size_val}>"
            close_t = "</size>"
            try:
                sel_first = target.index("sel.first")
                sel_last = target.index("sel.last")
                sel_txt = target.get(sel_first, sel_last)
                target.delete(sel_first, sel_last)
                target.insert(sel_first, f"{open_t}{sel_txt}{close_t}")
            except tk.TclError:
                target.insert(tk.INSERT, f"{open_t}{close_t}")
                target.mark_set(tk.INSERT, f"{tk.INSERT} - {len(close_t)}c")
        else:
            target.insert(tk.INSERT, "</size>")

        target.focus_set()
        self._commit_widget_edit(target)

    def _resolve_all_script_box_at_index(self, tk_index: str) -> Optional[int]:
        """Map a Tk text index inside txt_all_script to its owning box index (-1 for Box 0, 0..N-1)."""
        if not hasattr(self, "txt_all_script") or not self.txt_all_script.winfo_exists():
            return None
        try:
            abs_idx = self.txt_all_script.index(tk_index)
            ln = int(abs_idx.split(".")[0])
            if ln in self._all_script_line_to_box:
                return self._all_script_line_to_box[ln]
            # Nearest fallback by line number
            best_idx = None
            best_dist = 10**9
            for b_idx, (s_ln, e_ln) in self._all_script_block_ranges.items():
                if s_ln <= ln <= e_ln:
                    return b_idx
                dist = min(abs(ln - s_ln), abs(ln - e_ln))
                if dist < best_dist:
                    best_dist = dist
                    best_idx = b_idx
            return best_idx
        except Exception:
            return None

    def _set_all_script_active_block(self, active_idx: int) -> None:
        """Highlight the active block in txt_all_script in-place without re-rendering."""
        if not hasattr(self, "txt_all_script") or not self.txt_all_script.winfo_exists():
            return
        txt = self.txt_all_script
        try:
            txt.tag_remove("all_script_active", "1.0", tk.END)
            if active_idx in self._all_script_block_ranges:
                s_ln, e_ln = self._all_script_block_ranges[active_idx]
                txt.tag_add("all_script_active", f"{s_ln}.0", f"{e_ln + 1}.0")
                txt.tag_lower("all_script_active")
        except Exception:
            pass

    def _toggle_all_script_select_in_place(self, box_idx: int) -> None:
        """Toggle Select Box state for `box_idx` in-place inside txt_all_script."""
        if not hasattr(self, "txt_all_script") or not self.txt_all_script.winfo_exists():
            return
        if not self.var_select_box_mode.get():
            return
        if box_idx in self._selected_boxes:
            self._selected_boxes.discard(box_idx)
            new_tok = "[ ] "
        else:
            self._selected_boxes.add(box_idx)
            new_tok = "[x] "
        span = getattr(self, "_all_script_sel_ranges", {}).get(box_idx)
        if span:
            txt = self.txt_all_script
            was_disabled = (str(txt.cget("state")) == "disabled")
            if was_disabled:
                txt.config(state="normal")
            try:
                tags = txt.tag_names(span[0])
                txt.delete(span[0], span[1])
                txt.insert(span[0], new_tok, tags)
                self._all_script_sel_ranges[box_idx] = (span[0], f"{span[0].split('.')[0]}.{int(span[0].split('.')[1]) + len(new_tok)}")
            finally:
                if was_disabled:
                    txt.config(state="disabled")
        self._update_dialogue_select_box_ui()

    def _refresh_all_script_lock_glyph_in_place(self, box_idx: int) -> None:
        """Update inline lock glyph for `box_idx` inside txt_all_script without re-rendering."""
        if not hasattr(self, "txt_all_script") or not self.txt_all_script.winfo_exists():
            return
        span = getattr(self, "_all_script_lock_ranges", {}).get(box_idx)
        if not span:
            return
        is_locked = self.is_box_locked(box_idx)
        new_tok = "🔒 " if is_locked else "🔓 "
        txt = self.txt_all_script
        was_disabled = (str(txt.cget("state")) == "disabled")
        if was_disabled:
            txt.config(state="normal")
        try:
            tags = txt.tag_names(span[0])
            txt.delete(span[0], span[1])
            txt.insert(span[0], new_tok, tags)
            s_ln, s_col = span[0].split(".")
            self._all_script_lock_ranges[box_idx] = (span[0], f"{s_ln}.{int(s_col) + len(new_tok)}")
        finally:
            if was_disabled:
                txt.config(state="disabled")

    def _on_all_script_click_at_index(self, tk_index: str) -> None:
        """Handle single-click at `tk_index` in txt_all_script (select box, toggle inline slot/lock)."""
        if not self.current_doc:
            return
        txt = self.txt_all_script
        try:
            abs_idx = txt.index(tk_index)
        except Exception:
            return

        # 1. Check inline Select Box slot hit
        if self.var_select_box_mode.get():
            for b_idx, (s_pos, e_pos) in getattr(self, "_all_script_sel_ranges", {}).items():
                if txt.compare(abs_idx, ">=", s_pos) and txt.compare(abs_idx, "<", e_pos):
                    self._toggle_all_script_select_in_place(b_idx)
                    return

        # 2. Check inline Lock glyph hit
        for b_idx, (s_pos, e_pos) in getattr(self, "_all_script_lock_ranges", {}).items():
            if txt.compare(abs_idx, ">=", s_pos) and txt.compare(abs_idx, "<", e_pos):
                self._on_toggle_card_lock(b_idx)
                return

        # 3. Select owning box in-place (NO full re-render)
        box_idx = self._resolve_all_script_box_at_index(abs_idx)
        if box_idx is None:
            return
        if box_idx == -1:
            self.is_box0_active = True
        else:
            self.is_box0_active = False
            if 0 <= box_idx < len(self.current_doc.boxes):
                self.current_box_idx = box_idx
        self._set_all_script_active_block(box_idx)
        self._sync_header_controls_for_card(box_idx)
        self._update_raw_view()
        if box_idx >= 0 and 0 <= box_idx < len(self.current_doc.boxes):
            self._update_char_overflow_indicator(self.current_doc.boxes[box_idx].clean_text)
        else:
            self._update_char_overflow_indicator("")
        self._refresh_mtl_drawer_box()

    def _on_all_script_click(self, event: tk.Event) -> Optional[str]:
        """Single-click handler on txt_all_script."""
        if not hasattr(self, "txt_all_script") or not self.txt_all_script.winfo_exists():
            return None
        try:
            idx = self.txt_all_script.index(f"@{event.x},{event.y}")
            self.txt_all_script.focus_set()
            self._on_all_script_click_at_index(idx)
        except Exception:
            pass
        return None

    def _on_all_script_activate_at_index(self, tk_index: str) -> None:
        """Jump cleanly from txt_all_script at `tk_index` into Dialogue View."""
        if not self.current_doc:
            return
        box_idx = self._resolve_all_script_box_at_index(tk_index)
        if box_idx is None:
            box_idx = -1 if getattr(self, "is_box0_active", False) else self.current_box_idx
        if box_idx == -1 and self.current_doc.has_metadata():
            self.is_box0_active = True
        else:
            self.is_box0_active = False
            if self.current_doc.boxes:
                self.current_box_idx = max(0, min(box_idx, len(self.current_doc.boxes) - 1))
        self.var_continuous_view.set(False)
        self._on_toggle_continuous_view()

    def _on_all_script_double_click(self, event: tk.Event) -> str:
        """Double-click on txt_all_script jumps into Dialogue View at that box."""
        if hasattr(self, "txt_all_script") and self.txt_all_script.winfo_exists():
            idx = self.txt_all_script.index(f"@{event.x},{event.y}")
            self._on_all_script_activate_at_index(idx)
        return "break"

    def _on_all_script_enter(self, _event: tk.Event) -> str:
        """Pressing Enter in txt_all_script jumps into Dialogue View at active box."""
        active_idx = -1 if getattr(self, "is_box0_active", False) else self.current_box_idx
        if active_idx in getattr(self, "_all_script_block_ranges", {}):
            s_ln, _ = self._all_script_block_ranges[active_idx]
            self._on_all_script_activate_at_index(f"{s_ln}.0")
        else:
            self._on_all_script_activate_at_index("insert")
        return "break"

    def _render_continuous_view(self) -> None:
        """Render all dialogue boxes inside ONE read-only tk.Text (Technique A) or plain-text fallback."""
        compiled = self.var_preview_compiled.get()
        self._suppress_continuous_events = True
        t = self.theme
        d_fam = getattr(self, "dialogue_font_family", self.prefs.get("dialogue_font_family", "Consolas"))
        d_sz = int(getattr(self, "dialogue_font_size", self.prefs.get("dialogue_font_size", 11)))
        d_font_tuple = self._get_dialogue_font_tuple(d_sz)
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        metrics_empty = self._measure_dialogue_metrics("")
        safe_w = metrics_empty["safe_w"]

        try:
            self._card_widgets.clear()
            self._all_script_block_ranges.clear()
            self._all_script_line_to_box.clear()
            self._all_script_sel_ranges.clear()
            self._all_script_lock_ranges.clear()
            self._all_script_body_starts.clear()
            self._all_script_render_images.clear()
            if not hasattr(self, "_all_script_body_ends"):
                self._all_script_body_ends: Dict[int, str] = {}
            self._all_script_body_ends.clear()

            # If plain text file: keep legacy editable txt_continuous view
            if not self.is_bundle_file and not self.current_doc:
                if hasattr(self, "txt_all_script") and self._is_widget_packed(self.txt_all_script):
                    self.txt_all_script.pack_forget()
                if hasattr(self, "cont_canvas") and self._is_widget_packed(self.cont_canvas):
                    self.cont_canvas.pack_forget()
                if hasattr(self, "cont_scroll_y"):
                    self.cont_scroll_y.config(command=self._on_continuous_vscroll)
                    if not self._is_widget_packed(self.cont_scroll_y):
                        self.cont_scroll_y.pack(side="right", fill="y")
                if hasattr(self, "txt_continuous") and not self._is_widget_packed(self.txt_continuous):
                    self.txt_continuous.pack(side="left", fill="both", expand=True)
                self.txt_continuous.config(state="normal")
                self.txt_continuous.delete("1.0", tk.END)
                if compiled:
                    self._insert_compiled_ngui_text(self.txt_continuous, "1.0", self._plain_text_content)
                    self.txt_continuous.config(state="disabled")
                else:
                    self.txt_continuous.insert("1.0", self._plain_text_content)
                    self._highlight_ngui_tags_for_widget(self.txt_continuous)
                return

            # Multi-Box Story Documents: Technique A single read-only tk.Text (txt_all_script)
            if hasattr(self, "txt_continuous") and self._is_widget_packed(self.txt_continuous):
                self.txt_continuous.pack_forget()
            if hasattr(self, "gutter_cont") and self._is_widget_packed(self.gutter_cont):
                self.gutter_cont.pack_forget()
            if hasattr(self, "cont_canvas") and self._is_widget_packed(self.cont_canvas):
                self.cont_canvas.pack_forget()
            if hasattr(self, "cont_stream_frame"):
                for child in self.cont_stream_frame.winfo_children():
                    child.destroy()

            txt = getattr(self, "txt_all_script", None)
            if txt is None or not txt.winfo_exists():
                return

            if hasattr(self, "cont_scroll_y"):
                self.cont_scroll_y.config(command=txt.yview)
                if not self._is_widget_packed(self.cont_scroll_y):
                    self.cont_scroll_y.pack(side="right", fill="y")
            if not self._is_widget_packed(txt):
                txt.pack(side="left", fill="both", expand=True)

            canvas_bg = "#F4F2ED" if compiled else t["bg_panel"]
            card_bg = "#FFFFFF" if compiled else t["bg_editor"]
            hdr_bg = "#FFFFFF" if compiled else t["bg_panel"]
            card_fg = "#333333" if compiled else editor_fg
            sp_color = "#2D599E" if compiled else t["fg_text"]
            narr_color = "#2D599E" if compiled else t["fg_muted"]
            ov_gutter_fg = "#c9184a" if self._is_light_theme() else "#ff5c7c"

            txt.config(state="normal")
            txt.delete("1.0", tk.END)
            txt.configure(
                wrap="none" if compiled else "word",
                bg=canvas_bg,
                fg=card_fg,
                font=(d_fam, d_sz) if compiled else d_font_tuple,
            )
            self._configure_editor_rich_tags(txt, d_fam, d_sz)

            txt.tag_configure("all_script_active", background=t["highlight_bg"])
            txt.tag_configure("as_hdr", lmargin1=16, lmargin2=16, rmargin=16, background=hdr_bg)
            txt.tag_configure("as_body", lmargin1=20, lmargin2=20, rmargin=16, background=card_bg, foreground=card_fg)
            txt.tag_configure("as_cap", lmargin1=12, rmargin=12, background=canvas_bg)
            txt.tag_configure("as_sel_slot", font=("Consolas", max(8, d_sz - 2), "bold"), foreground=t["misora_pink"])
            txt.tag_configure("as_lock_slot", font=("Segoe UI", max(8, d_sz - 2)), foreground=t["accent_yellow"])
            txt.tag_configure("as_badge", font=("Consolas", max(8, d_sz - 3), "bold"), foreground=t["misora_pink"])
            txt.tag_configure("as_speaker", font=(d_fam, max(9, d_sz - 1), "bold"), foreground=sp_color)
            txt.tag_configure(
                "as_narrator",
                font=(d_fam, max(9, d_sz - 1), "bold") if compiled else (d_fam, max(8, d_sz - 2), "italic"),
                foreground=narr_color,
            )
            txt.tag_configure("as_voice", font=("Segoe UI", max(7, d_sz - 4)), foreground=t["accent_blue"])
            txt.tag_configure("as_segs", font=("Segoe UI", max(7, d_sz - 4), "bold"), foreground=t["misora_pink"])
            txt.tag_configure("as_box0_meta", font=(d_fam, max(8, d_sz - 2)), foreground=t["fg_muted"])
            txt.tag_configure("as_spacer", font=("Segoe UI", 4), spacing1=2, spacing3=2, background=canvas_bg)
            txt.tag_configure("gutter_overflow", foreground=ov_gutter_fg, font=self._get_dialogue_font_tuple(d_sz, "bold"))

            if not self.current_doc or not self.current_doc.boxes:
                txt.config(state="disabled")
                return

            sel_mode = bool(self.var_select_box_mode.get())
            card_w = max(460, int(safe_w + 64))
            top_img = bot_img = dot_img = voice_img = None
            if compiled:
                top_img = get_all_script_card_top_image(card_w, height=10, radius=10, canvas_bg=canvas_bg, card_bg=card_bg, border_hex="#B8BCCA", master=txt)
                bot_img = get_all_script_card_bottom_image(card_w, height=10, radius=10, canvas_bg=canvas_bg, card_bg=card_bg, border_hex="#B8BCCA", master=txt)
                dot_img = get_all_script_dotted_rule_image(max(120, card_w - 40), height=5, dot_hex="#B8CCE8", bg_hex=card_bg, master=txt)
                voice_img = get_voice_badge_image(size=18, master=txt)
                for im in (top_img, bot_img, dot_img, voice_img):
                    if im is not None:
                        self._all_script_render_images.append(im)

            # 1. Box 0 Metadata Block (-1)
            if self.current_doc.has_metadata():
                meta = self.current_doc.get_metadata()
                if compiled and top_img is not None:
                    txt.image_create(tk.END, image=top_img)
                    txt.insert(tk.END, "\n", ("as_cap",))
                s_ln = int(txt.index("end-1c").split(".")[0])

                sel_tok = ("[x] " if -1 in self._selected_boxes else "[ ] ") if sel_mode else "    "
                sel_s = txt.index("end-1c")
                txt.insert(tk.END, sel_tok, ("as_hdr", "as_sel_slot"))
                sel_e = txt.index("end-1c")
                self._all_script_sel_ranges[-1] = (sel_s, sel_e)
                txt.insert(tk.END, "   ", ("as_hdr", "as_lock_slot"))
                txt.insert(tk.END, "◆ [BOX #000]  ", ("as_hdr", "as_badge"))
                txt.insert(tk.END, "[STORY METADATA & SYNOPSIS]\n", ("as_hdr", "as_speaker"))
                txt.insert(
                    tk.END,
                    f"Title: {meta.get('title', '')}   |   Subtitle: {meta.get('subtitle', '')}\n",
                    ("as_body", "as_box0_meta"),
                )
                b_start = txt.index("end-1c")
                self._all_script_body_starts[-1] = b_start
                sum_txt = meta.get("summary", "")
                txt.insert(tk.END, sum_txt, ("as_body",))
                b_end = txt.index("end-1c")
                self._all_script_body_ends[-1] = b_end
                txt.insert(tk.END, "\n", ("as_body",))

                e_ln = int(txt.index("end-1c").split(".")[0]) - 1
                if compiled and bot_img is not None:
                    txt.image_create(tk.END, image=bot_img)
                    txt.insert(tk.END, "\n", ("as_cap",))
                self._all_script_block_ranges[-1] = (s_ln, e_ln)
                for ln in range(s_ln, e_ln + 1):
                    self._all_script_line_to_box[ln] = -1
                txt.insert(tk.END, "\n", ("as_spacer",))

            # 2. Dialogue Boxes (0..N-1)
            locked_set = getattr(self, "_locked_boxes", set())
            for i, box in enumerate(self.current_doc.boxes):
                if compiled and top_img is not None:
                    txt.image_create(tk.END, image=top_img)
                    txt.insert(tk.END, "\n", ("as_cap",))
                s_ln = int(txt.index("end-1c").split(".")[0])

                sel_tok = ("[x] " if i in self._selected_boxes else "[ ] ") if sel_mode else "    "
                sel_s = txt.index("end-1c")
                txt.insert(tk.END, sel_tok, ("as_hdr", "as_sel_slot"))
                sel_e = txt.index("end-1c")
                self._all_script_sel_ranges[i] = (sel_s, sel_e)

                lk_tok = "🔒 " if i in locked_set else "🔓 "
                lk_s = txt.index("end-1c")
                txt.insert(tk.END, lk_tok, ("as_hdr", "as_lock_slot"))
                lk_e = txt.index("end-1c")
                self._all_script_lock_ranges[i] = (lk_s, lk_e)

                if compiled:
                    sp_disp = box.speaker if box.speaker.strip() else "Narration"
                    sp_tag = "as_speaker" if box.speaker.strip() else "as_narrator"
                    txt.insert(tk.END, sp_disp, ("as_hdr", sp_tag))
                    txt.insert(tk.END, f"   [#{i+1:03d}]", ("as_hdr", "as_badge"))
                    if box.voice_cue:
                        txt.insert(tk.END, "   ", ("as_hdr",))
                        if voice_img is not None:
                            txt.image_create(tk.END, image=voice_img)
                        txt.insert(tk.END, f" {box.voice_cue}", ("as_hdr", "as_voice"))
                    txt.insert(tk.END, "\n", ("as_hdr",))
                    if dot_img is not None:
                        txt.image_create(tk.END, image=dot_img)
                        txt.insert(tk.END, "\n", ("as_hdr",))
                else:
                    txt.insert(tk.END, f"◆ [BOX #{i+1:03d}] ", ("as_hdr", "as_badge"))
                    sp_disp = box.speaker if box.speaker else "(Narration)"
                    sp_tag = "as_speaker" if box.speaker else "as_narrator"
                    txt.insert(tk.END, sp_disp, ("as_hdr", sp_tag))
                    if box.voice_cue:
                        txt.insert(tk.END, f"  ♪ {box.voice_cue}", ("as_hdr", "as_voice"))
                    if len(box.segs) > 1:
                        txt.insert(tk.END, f"  [{len(box.segs)} segs]", ("as_hdr", "as_segs"))
                    txt.insert(tk.END, "\n", ("as_hdr",))

                b_start = txt.index("end-1c")
                self._all_script_body_starts[i] = b_start
                body_text = box.clean_text
                if compiled:
                    self._insert_compiled_ngui_text(txt, b_start, body_text, base_tags=("as_body",))
                    b_end = txt.index("end-1c")
                else:
                    txt.insert(tk.END, body_text, ("as_body",))
                    b_end = txt.index("end-1c")
                    for m in NGUI_TAG_RE.finditer(body_text):
                        txt.tag_add("ngui_tag", f"{b_start} + {m.start()}c", f"{b_start} + {m.end()}c")
                self._all_script_body_ends[i] = b_end
                txt.insert(tk.END, "\n", ("as_body",))

                # Pixel-calibrated overflow & line 4+ highlights
                body_start_ln = int(b_start.split(".")[0])
                raw_metrics = self._measure_dialogue_metrics(body_text)
                for info in raw_metrics["lines"]:
                    rel_ln = info["line_no"]
                    abs_ln = body_start_ln + (rel_ln - 1)
                    if rel_ln >= 4:
                        txt.tag_add("gutter_overflow", f"{abs_ln}.0", f"{abs_ln}.end")
                    if info["overflow_raw_start"] is not None:
                        if compiled:
                            rendered_line = txt.get(f"{abs_ln}.0", f"{abs_ln}.end")
                            rm = self._measure_dialogue_metrics(rendered_line)
                            ov_col = rm["lines"][0]["overflow_raw_start"]
                        else:
                            ov_col = info["overflow_raw_start"]
                        if ov_col is not None:
                            txt.tag_add("line_overflow", f"{abs_ln}.{ov_col}", f"{abs_ln}.end")

                e_ln = int(txt.index("end-1c").split(".")[0]) - 1
                if compiled and bot_img is not None:
                    txt.image_create(tk.END, image=bot_img)
                    txt.insert(tk.END, "\n", ("as_cap",))
                self._all_script_block_ranges[i] = (s_ln, e_ln)
                for ln in range(s_ln, e_ln + 1):
                    self._all_script_line_to_box[ln] = i
                txt.insert(tk.END, "\n", ("as_spacer",))

            txt.tag_raise("line_overflow")
            txt.tag_raise("ngui_tag")
            txt.tag_raise("search_hit")

            active_idx = -1 if getattr(self, "is_box0_active", False) else self.current_box_idx
            self._set_all_script_active_block(active_idx)
            self._highlight_continuous_matches()
            txt.config(state="disabled")
        finally:
            self._suppress_continuous_events = False

    def _focus_continuous_box(
        self,
        box_idx: int,
        move_cursor: bool = True,
        char_offset: int = 0,
        explicit_span: Optional[Tuple[int, int]] = None
    ) -> None:
        """Scroll All Script (Technique A) to `box_idx`, highlight block in-place, and sync metadata."""
        if not self.current_doc:
            return

        total = len(self.current_doc.boxes) if self.current_doc.boxes else 0
        if box_idx == -1:
            self.is_box0_active = True
            target_idx = -1
        else:
            self.is_box0_active = False
            self.current_box_idx = max(0, min(box_idx, total - 1)) if total > 0 else 0
            target_idx = self.current_box_idx

        self._set_all_script_active_block(target_idx)
        self._sync_header_controls_for_card(target_idx)
        self._update_raw_view()

        txt = getattr(self, "txt_all_script", None)
        if txt is not None and txt.winfo_exists() and target_idx in self._all_script_block_ranges:
            s_ln, _e_ln = self._all_script_block_ranges[target_idx]
            try:
                txt.see(f"{s_ln}.0")
                b_start = self._all_script_body_starts.get(target_idx, f"{s_ln}.0")
                if move_cursor:
                    txt.mark_set("insert", f"{b_start} + {max(0, char_offset)}c")
                    txt.see("insert")
                if explicit_span is not None and not self.var_preview_compiled.get():
                    s, e = explicit_span
                    if e > s:
                        txt.tag_remove("search_hit", "1.0", tk.END)
                        txt.tag_add("search_hit", f"{b_start} + {s}c", f"{b_start} + {e}c")
                        txt.see(f"{b_start} + {s}c")
            except Exception:
                pass

    def _find_continuous_box_at_index(self, tk_index: str) -> Optional[int]:
        """Return active box index (compatibility shim for Card Stream architecture)."""
        if getattr(self, "is_box0_active", False):
            return -1
        return self.current_box_idx

    def _nearest_continuous_box_to_index(self, tk_index: str) -> int:
        """Return active box index (compatibility shim for Card Stream architecture)."""
        return self.current_box_idx

    def _on_continuous_cursor_moved(self, event: Optional[tk.Event] = None) -> None:
        """Compatibility shim for Card Stream (handled via _on_card_focus_in)."""
        pass

    def _on_continuous_key_guard(self, event: tk.Event) -> Optional[str]:
        """Compatibility shim for Card Stream."""
        return None

    def _on_continuous_copy(self, _event: Optional[tk.Event] = None) -> Optional[str]:
        """Compatibility shim for Card Stream."""
        return None

    def _on_continuous_paste_guard(self, _event: tk.Event) -> Optional[str]:
        """Compatibility shim for Card Stream."""
        return None

    def _on_continuous_cut_guard(self, _event: tk.Event) -> Optional[str]:
        """Compatibility shim for Card Stream."""
        return None

    def _on_continuous_key_release(self, _event: tk.Event) -> None:
        """Compatibility shim for Card Stream."""
        self._flush_continuous_card_edits()

    def _sync_continuous_box_from_widget(self) -> None:
        """Persist card edits to StoryDocument or plain text."""
        self._flush_continuous_card_edits()

    def _highlight_dialogue_matches(self, explicit_span: Optional[Tuple[int, int]] = None) -> None:
        """Highlight active search keyword spans inside the single-box dialogue editor."""
        if self.var_preview_compiled.get():
            return

        self.txt_dialogue.tag_remove("search_hit", "1.0", tk.END)

        if explicit_span is not None:
            s, e = explicit_span
            if e > s:
                start_idx = f"1.0 + {s}c"
                end_idx = f"1.0 + {e}c"
                self.txt_dialogue.tag_add("search_hit", start_idx, end_idx)
                self.txt_dialogue.see(start_idx)
                return

        if not self.active_search_options or not self.active_search_options.query.strip():
            return

        text = self.txt_dialogue.get("1.0", "end-1c")
        if not text:
            return

        try:
            matcher = self.search_engine._compile_matcher(self.active_search_options)
            matches = matcher(text)
            for s, e, _ in matches:
                if e > s:
                    self.txt_dialogue.tag_add("search_hit", f"1.0 + {s}c", f"1.0 + {e}c")
            if matches:
                self.txt_dialogue.see(f"1.0 + {matches[0][0]}c")
        except Exception:
            pass

    def _highlight_continuous_matches(self) -> None:
        """Highlight active search keyword spans across all blocks in All Script (Technique A)."""
        if self.var_preview_compiled.get():
            return
        txt = getattr(self, "txt_all_script", None)
        if txt is None or not txt.winfo_exists() or not self.current_doc:
            return

        matcher = None
        if self.active_search_options and self.active_search_options.query.strip():
            try:
                matcher = self.search_engine._compile_matcher(self.active_search_options)
            except Exception:
                matcher = None

        try:
            txt.tag_remove("search_hit", "1.0", tk.END)
            if not matcher:
                return
            for b_idx, b_start in getattr(self, "_all_script_body_starts", {}).items():
                b_end = getattr(self, "_all_script_body_ends", {}).get(b_idx)
                if not b_end:
                    continue
                box_tx = txt.get(b_start, b_end)
                for s, e, _ in matcher(box_tx):
                    if e > s:
                        txt.tag_add("search_hit", f"{b_start} + {s}c", f"{b_start} + {e}c")
        except Exception:
            pass

    def _commit_speaker_edit(self, source: str = "keyboard") -> bool:
        """Central edit commit path for speaker entry edits (Rule 11, F20, U-4).
        Returns True if a mutation occurred, False if no-op, locked, or aborted.
        """
        if getattr(self, "_suppress_continuous_events", False):
            return False
        if getattr(self, "is_box0_active", False):
            return False
        if not self.current_doc or not self.current_doc.boxes:
            return False
        if not (0 <= self.current_box_idx < len(self.current_doc.boxes)):
            return False

        idx = self.current_box_idx
        box = self.current_doc.boxes[idx]
        old_sp = box.speaker
        new_sp = self.speaker_var.get()

        # Resolve current text cleanly from active view
        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
            if hasattr(self, "_card_widgets") and idx in self._card_widgets:
                cur_tx = self._card_widgets[idx]["txt"].get("1.0", "end-1c")
            else:
                cur_tx = box.clean_text
        else:
            if getattr(self, "var_preview_compiled", None) and self.var_preview_compiled.get():
                cur_tx = box.clean_text
            elif hasattr(self, "txt_dialogue") and self.txt_dialogue.winfo_exists():
                cur_tx = self.txt_dialogue.get("1.0", "end-1c")
            else:
                cur_tx = box.clean_text

        if old_sp == new_sp:
            return False

        if self.is_box_locked(idx):
            self.speaker_var.set(old_sp)
            self.show_toast(f"Box #{idx + 1} is locked; speaker rename blocked.")
            return False

        # Lock-Before-Unpin (U-02): only release Speaker Pin after lock check passes
        pin_released = False
        if getattr(self, "_is_speaker_pinned", False):
            self._reset_speaker_pin(notify=False)
            pin_released = True

        self.undo_journal.record(
            BoxEditDelta(
                box_index=idx,
                old_speaker=old_sp,
                new_speaker=new_sp,
                old_text=box.clean_text,
                new_text=cur_tx,
                file_path=str(self.current_file_path or ""),
                box_uid=box.uid,
                source=source,
            ),
            label=f"Rename speaker #{idx + 1}"
        )

        try:
            self.current_doc.inject_box(idx, new_sp, cur_tx)
        except Exception as ex:
            self.logger.error("AST", f"Failed to inject speaker rename: {ex}")
            return False

        updated_sp = self.current_doc.boxes[idx].speaker
        if self.speaker_var.get() != updated_sp:
            self.speaker_var.set(updated_sp)

        self._modified_boxes.add(idx)
        self._mark_document_dirty(self.current_file_path)

        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get():
            self._render_continuous_view()
            self._set_all_script_active_block(idx)
        elif getattr(self, "var_preview_compiled", None) and self.var_preview_compiled.get():
            self._render_dialogue_preview_frame(updated_sp, self.current_doc.boxes[idx].clean_text)

        if hasattr(self, "_refresh_continuous_box_header"):
            self._refresh_continuous_box_header(idx)
        elif hasattr(self, "_card_widgets") and idx in self._card_widgets:
            lbl_sp = self._card_widgets[idx].get("lbl_sp")
            if lbl_sp and lbl_sp.winfo_exists():
                lbl_sp.config(text=updated_sp if updated_sp else "(Narration)")

        self._update_raw_view()
        self._dirty_state_changed()
        if pin_released:
            disp_sp = updated_sp or "(Narration)"
            self.show_toast(f"Speaker Pin released — speaker changed to {disp_sp}. Click 📌 to pin {disp_sp}.")
        else:
            self.show_toast(f"Renamed Box #{idx + 1} speaker to {updated_sp or '(Narration)'}")
        return True

    def _on_speaker_edited(self) -> None:
        """Triggered when editing the pinned Speaker entry in either Page or Continuous mode."""
        self._commit_speaker_edit()

    def _refresh_continuous_box_header(self, box_idx: int) -> None:
        """Update a single box header in Continuous View in-place when its speaker changes."""
        if not self.current_doc or not (0 <= box_idx < len(self.current_doc.boxes)):
            return
        if not hasattr(self, "_card_widgets") or box_idx not in self._card_widgets:
            return
        box = self.current_doc.boxes[box_idx]
        card_info = self._card_widgets[box_idx]
        lbl_sp = card_info.get("lbl_sp")
        if lbl_sp:
            t = self.theme
            speaker_disp = box.speaker if box.speaker else "(Narration)"
            speaker_color = t["misora_pink"] if box.speaker else t["fg_muted"]
            lbl_sp.config(text=speaker_disp, fg=speaker_color)

    def _on_dialogue_key_up(self, _event: tk.Event) -> Optional[str]:
        """Navigate to previous box when pressing Up at top line of Clean Dialogue View."""
        if self.txt_dialogue.compare("insert linestart", "==", "1.0"):
            if self.current_box_idx > 0:
                self.on_prev_box()
                self.txt_dialogue.mark_set("insert", "end-1c")
                self.txt_dialogue.see("insert")
                return "break"
        return None

    def _on_dialogue_key_down(self, _event: tk.Event) -> Optional[str]:
        """Navigate to next box when pressing Down at bottom line of Clean Dialogue View."""
        if self.txt_dialogue.compare("insert lineend", ">=", "end-1c"):
            if self.current_doc and self.current_box_idx < len(self.current_doc.boxes) - 1:
                self.on_next_box()
                self.txt_dialogue.mark_set("insert", "1.0")
                self.txt_dialogue.see("insert")
                return "break"
        return None

    def _commit_widget_edit(self, widget: Optional[tk.Widget] = None) -> None:
        """Central edit commit path for all widget edits, ribbon wrappers, cut/paste, and metadata (Rule 11)."""
        if getattr(self, "_suppress_continuous_events", False):
            return
        if getattr(self, "var_preview_compiled", None) and self.var_preview_compiled.get():
            return

        if widget is None:
            widget = self._get_active_text_widget()
        if widget is None:
            return

        # 1. Continuous View Box 0 Metadata Card (-1)
        if (
            self.current_doc
            and self.current_doc.has_metadata()
            and -1 in getattr(self, "_card_widgets", {})
            and widget == self._card_widgets[-1].get("txt")
        ):
            new_sum = widget.get("1.0", "end-1c")
            meta = self.current_doc.get_metadata()
            old_sum = meta.get("summary", "")
            if old_sum != new_sum:
                self.undo_journal.record(
                    MetadataDelta(
                        file_path=str(self.current_file_path or ""),
                        old_title=meta.get("title", ""),
                        new_title=meta.get("title", ""),
                        old_subtitle=meta.get("subtitle", ""),
                        new_subtitle=meta.get("subtitle", ""),
                        old_summary=old_sum,
                        new_summary=new_sum,
                    ),
                    label="Edit Synopsis"
                )
                self.current_doc.set_metadata(summary=new_sum)
                self._mark_document_dirty(self.current_file_path)
                if hasattr(self, "txt_box0_summary") and self.txt_box0_summary.winfo_exists():
                    self.txt_box0_summary.delete("1.0", tk.END)
                    self.txt_box0_summary.insert("1.0", new_sum)
                self._update_raw_view()
                self._dirty_state_changed()
            return

        # 2. Page View Box 0 Metadata Widgets
        is_box0 = (
            getattr(self, "is_box0_active", False)
            or widget in (
                getattr(self, "txt_box0_summary", None),
                getattr(self, "entry_box0_title", None),
                getattr(self, "entry_box0_subtitle", None),
            )
        )
        if is_box0:
            if self._on_box0_metadata_edited():
                self._dirty_state_changed()
            self._update_box0_char_counter()
            return

        # 2. Speaker Entry
        if widget == getattr(self, "entry_speaker", None):
            self._commit_speaker_edit()
            return

        # 3. Page View Dialogue Editor (txt_dialogue)
        if widget == getattr(self, "txt_dialogue", None):
            if self._on_dialogue_edited():
                self._dirty_state_changed()
            return

        # 4. Continuous View Card text widgets
        if hasattr(self, "_card_widgets") and self._card_widgets:
            for b_idx, card_dict in list(self._card_widgets.items()):
                if card_dict.get("txt") == widget and b_idx >= 0:
                    gutter = card_dict.get("gutter")
                    if self._on_card_text_edited(b_idx, widget, gutter):
                        self._dirty_state_changed()
                    return

        # 5. Continuous View plain text fallback
        if widget == getattr(self, "txt_continuous", None):
            new_tx = widget.get("1.0", "end-1c")
            if new_tx != getattr(self, "_plain_text_content", ""):
                self.undo_journal.record(
                    PlainTextDelta(
                        file_path=str(self.current_file_path or ""),
                        old_content=self._plain_text_content,
                        new_content=new_tx,
                    ),
                    label=f"Edit {self.current_file_path.name if self.current_file_path else 'text'}"
                )
                self._plain_text_content = new_tx
                if self.current_file_path and self.current_file_path in self.open_documents:
                    self.open_documents[self.current_file_path]["plain_text"] = new_tx
                self._mark_document_dirty(self.current_file_path)
                self._dirty_state_changed()
            return

    def _on_dialogue_edited(self) -> bool:
        """Triggered on every keystroke in the single-box Game Display dialogue editor.

        Returns True if a real mutation occurred (content changed), False if no-op (S2).
        Only marks dirty and records undo when content actually changed.
        """
        if self.var_preview_compiled.get():
            return False

        if self.current_doc and self.current_doc.boxes:
            idx = self.current_box_idx
            box = self.current_doc.boxes[idx]
            old_sp = box.speaker
            old_tx = box.clean_text
            new_tx = self.txt_dialogue.get("1.0", "end-1c")
            # S2: guard no-op — dirty/undo only on actual change
            if old_tx == new_tx:
                self._auto_resize_dialogue_box()
                self._highlight_ngui_tags()
                self._highlight_dialogue_matches()
                return False
            box_uid = box.segs[0].record.uid if box.segs else None
            old_segs = [s.text for s in box.segs] if len(box.segs) > 1 else None
            try:
                self.current_doc.inject_box(idx, None, new_tx)
            except Exception as e:
                self.logger.exception(f"Failed to inject box {idx}:", e)
                self.set_status(f"Error updating box #{idx + 1}: {e}", is_error=True)
                return False

            new_segs = None
            if old_segs is not None:
                refreshed_box = next((b for b in self.current_doc.boxes if b.segs and b.segs[0].record.uid == box_uid), None)
                if refreshed_box:
                    new_segs = [s.text for s in refreshed_box.segs]

            delta = BoxEditDelta(
                box_index=idx,
                old_speaker=old_sp,
                new_speaker=old_sp,
                old_text=old_tx,
                new_text=new_tx,
                file_path=str(self.current_file_path or ""),
                box_uid=box_uid,
                source=getattr(self, "_current_edit_source", "keyboard"),
                old_seg_texts=old_segs,
                new_seg_texts=new_segs,
            )
            self.undo_journal.record(delta, label=f"Edit box #{idx + 1}")
            self._modified_boxes.add(idx)
            self._mark_document_dirty(self.current_file_path)
            try:
                self._update_raw_view()
            except Exception:
                pass
            self._auto_resize_dialogue_box()
            self._highlight_ngui_tags()
            self._highlight_dialogue_matches()
            self._update_gutter_clean()
            self._update_char_overflow_indicator(new_tx)
            return True
        else:
            old_content = self._plain_text_content
            new_content = self.txt_dialogue.get("1.0", "end-1c")
            # S2: guard no-op
            if old_content == new_content:
                self._auto_resize_dialogue_box()
                return False
            self.undo_journal.record(
                PlainTextDelta(
                    file_path=str(self.current_file_path or ""),
                    old_content=old_content,
                    new_content=new_content,
                ),
                label=f"Edit {self.current_file_path.name if self.current_file_path else 'text'}"
            )
            self._plain_text_content = new_content
            if self.current_file_path and self.current_file_path in self.open_documents:
                self.open_documents[self.current_file_path]["plain_text"] = new_content
            self._mark_document_dirty(self.current_file_path)
            self._auto_resize_dialogue_box()
            self._highlight_ngui_tags()
            self._highlight_dialogue_matches()
            self._update_gutter_clean()
            self._update_char_overflow_indicator(new_content)
            return True

    def _update_box0_char_counter(self) -> None:
        if not hasattr(self, "lbl_box0_summary_len") or not hasattr(self, "txt_box0_summary"):
            return
        txt = self.txt_box0_summary.get("1.0", "end-1c")
        chars = len(txt)
        lines = txt.count("\n") + (1 if txt else 0)
        self.lbl_box0_summary_len.config(
            text=f"Summary: {chars} chars | {lines} lines (In-game display: ~3-4 lines)"
        )

    def _on_box0_metadata_edited(self) -> bool:
        """Triggered on keystroke when editing Episode Title, Subtitle, or Synopsis in Box 0. Returns True if mutated (BUG-30)."""
        if not self.current_doc or not self.current_doc.has_metadata():
            return False
        meta = self.current_doc.get_metadata()
        old_title = meta.get("title", "")
        old_subtitle = meta.get("subtitle", "")
        old_summary = meta.get("summary", "")

        new_title = self.var_box0_title.get()
        new_subtitle = self.var_box0_subtitle.get()
        new_summary = self.txt_box0_summary.get("1.0", "end-1c")

        if (old_title, old_subtitle, old_summary) != (new_title, new_subtitle, new_summary):
            self.undo_journal.record(
                MetadataDelta(
                    file_path=str(self.current_file_path or ""),
                    old_title=old_title,
                    new_title=new_title,
                    old_subtitle=old_subtitle,
                    new_subtitle=new_subtitle,
                    old_summary=old_summary,
                    new_summary=new_summary,
                ),
                label="Edit story metadata (Box 0)"
            )
            self.current_doc.set_metadata(title=new_title, subtitle=new_subtitle, summary=new_summary)
            self._mark_document_dirty(self.current_file_path)
            if hasattr(self, "_card_widgets") and -1 in self._card_widgets:
                c0_txt = self._card_widgets[-1].get("txt")
                if c0_txt and c0_txt.winfo_exists():
                    c0_txt.delete("1.0", tk.END)
                    c0_txt.insert("1.0", new_summary)
            self._update_box0_char_counter()
            self._update_raw_view()
            return True
        return False

    def _navigate_pinned_speaker(self, direction: str) -> None:
        """Navigate Prev/Next strictly within current StoryDocument matching _pinned_speaker_name (no wrap-around; U-02)."""
        doc = self.current_doc
        if not doc or not doc.boxes:
            return
        target_sp = self._pinned_speaker_name
        matches = [i for i, b in enumerate(doc.boxes) if b.speaker == target_sp]
        disp = target_sp if target_sp else "(Narration)"
        total_m = len(matches)

        if direction == "next":
            start = 0 if getattr(self, "is_box0_active", False) else (self.current_box_idx + 1)
            nxt = next((i for i in matches if i >= start), None)
            if nxt is None:
                self.show_toast(f"Speaker {disp} — this is the last time speaking in this chapter")
                return
            self.is_box0_active = False
            self.current_box_idx = nxt
            k = matches.index(nxt) + 1
        else:
            if getattr(self, "is_box0_active", False):
                self.show_toast(f"Speaker {disp} — this is the first time speaking in this chapter")
                return
            prv = next((i for i in reversed(matches) if i < self.current_box_idx), None)
            if prv is None:
                self.show_toast(f"Speaker {disp} — this is the first time speaking in this chapter")
                return
            self.is_box0_active = False
            self.current_box_idx = prv
            k = matches.index(prv) + 1

        if self.var_continuous_view.get():
            self._focus_continuous_box(self.current_box_idx, move_cursor=True)
        else:
            self._update_views()
        self.show_toast(f"Speaker {disp} — Box #{self.current_box_idx + 1} ({k} of {total_m})")

    def on_prev_box(self) -> None:
        self._close_speaker_autocomplete()
        if getattr(self, "_is_speaker_pinned", False) and self._pinned_speaker_name is not None:
            self._navigate_pinned_speaker("prev")
            return
        if self.is_box0_active:
            return

        if self.current_doc and self.current_box_idx == 0:
            if self.current_doc.has_metadata():
                self.is_box0_active = True
                if self.var_continuous_view.get():
                    self._focus_continuous_box(-1, move_cursor=True)
                else:
                    self._update_views()
            return

        if self.current_doc and self.current_box_idx > 0:
            self.current_box_idx -= 1
            if self.var_continuous_view.get():
                self._focus_continuous_box(self.current_box_idx, move_cursor=True)
            else:
                self._update_views()

    def on_next_box(self) -> None:
        self._close_speaker_autocomplete()
        if getattr(self, "_is_speaker_pinned", False) and self._pinned_speaker_name is not None:
            self._navigate_pinned_speaker("next")
            return
        if self.is_box0_active:
            self.is_box0_active = False
            self.current_box_idx = 0
            if self.var_continuous_view.get():
                self._focus_continuous_box(0, move_cursor=True)
            else:
                self._update_views()
            return

        if self.current_doc and self.current_box_idx < len(self.current_doc.boxes) - 1:
            self.current_box_idx += 1
            if self.var_continuous_view.get():
                self._focus_continuous_box(self.current_box_idx, move_cursor=True)
            else:
                self._update_views()

    def is_box_locked(self, box_idx: int) -> bool:
        """Check if dialogue box at box_idx is locked against translation / batch mutations (Rule 20 D8 / S06)."""
        if self.current_doc and 0 <= box_idx < len(self.current_doc.boxes):
            b_uid = _get_box_uid(self.current_doc.boxes[box_idx])
            if b_uid is not None and b_uid in getattr(self, "_locked_box_uids", set()):
                return True
        return box_idx in getattr(self, "_locked_boxes", set())

    def _on_toggle_card_lock(self, box_idx: int) -> None:
        """Toggle Translation Lock on a specific dialogue box card."""
        if not self.current_doc or not self.current_doc.boxes:
            return
        if not (0 <= box_idx < len(self.current_doc.boxes)):
            return
        self.current_box_idx = box_idx
        self.is_box0_active = False
        self.on_toggle_lock_current_box()

    def on_toggle_lock_current_box(self) -> None:
        """Toggle Translation Lock on active dialogue box (Ctrl+L / Rule 20 D8 / S06)."""
        if not self.current_doc or not self.current_doc.boxes:
            return
        if getattr(self, "is_box0_active", False):
            self.show_toast("Box 0 metadata cannot be locked.")
            return
        b_idx = self.current_box_idx
        if not (0 <= b_idx < len(self.current_doc.boxes)):
            return
        box = self.current_doc.boxes[b_idx]
        b_uid = _get_box_uid(box)

        if not hasattr(self, "_locked_box_uids"):
            self._locked_box_uids = set()
        if not hasattr(self, "_locked_boxes"):
            self._locked_boxes = set()

        is_currently_locked = (b_uid is not None and b_uid in self._locked_box_uids) or (b_idx in self._locked_boxes)
        if is_currently_locked:
            if b_uid is not None:
                self._locked_box_uids.discard(b_uid)
            self._locked_boxes.discard(b_idx)
            self.show_toast(f"🔓 Box {b_idx + 1} unlocked")
        else:
            if b_uid is not None:
                self._locked_box_uids.add(b_uid)
            self._locked_boxes.add(b_idx)
            self.show_toast(f"🔒 Box {b_idx + 1} locked from batch/paste edits")

        if self.current_file_path:
            cur_p = Path(self.current_file_path).resolve()
            if cur_p in self.open_documents:
                self.open_documents[cur_p]["locked_box_uids"] = set(self._locked_box_uids)
        if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get() and hasattr(self, "_refresh_all_script_lock_glyph_in_place"):
            self._refresh_all_script_lock_glyph_in_place(b_idx)
            self._update_raw_view()
        else:
            self._update_views()

    def _resync_box_indices_from_uids(self) -> None:
        """Re-sync positional indices (_locked_boxes, _modified_boxes, _original_box_texts) from authoritative UIDs (S06 / S07)."""
        if self.current_doc and self.current_doc.boxes:
            if hasattr(self, "_locked_box_uids"):
                self._locked_boxes = {i for i, b in enumerate(self.current_doc.boxes) if _get_box_uid(b) in self._locked_box_uids}
            if hasattr(self, "_modified_box_uids"):
                self._modified_boxes = {i for i, b in enumerate(self.current_doc.boxes) if _get_box_uid(b) in self._modified_box_uids}
            if hasattr(self, "_original_jp_by_uid"):
                self._original_box_texts = {i: self._original_jp_by_uid.get(_get_box_uid(b), "") for i, b in enumerate(self.current_doc.boxes)}
        else:
            self._locked_boxes = set()
            self._modified_boxes = set()
            self._original_box_texts = {}

    def _get_dialogue_measure_font(self) -> tkfont.Font:
        """Return a cached tkfont.Font matching the active dialogue editor font."""
        d_fam, d_weight = self._resolve_active_dialogue_font_parts()
        d_sz = self.dialogue_font_size
        weight = d_weight or "normal"
        cached = getattr(self, "_dialogue_measure_font", None)
        if cached is None:
            cached = tkfont.Font(root=self, family=d_fam, size=d_sz, weight=weight)
            self._dialogue_measure_font = cached
        else:
            try:
                if (
                    cached.cget("family") != d_fam
                    or int(cached.cget("size")) != d_sz
                    or cached.cget("weight") != weight
                ):
                    cached.configure(family=d_fam, size=d_sz, weight=weight)
            except Exception:
                cached = tkfont.Font(root=self, family=d_fam, size=d_sz, weight=weight)
                self._dialogue_measure_font = cached
        return cached

    def _get_ruler_measure_font(self) -> tkfont.Font:
        """Return a cached tkfont.Font locked to Nunito Bold for constant 50d ruler calibration (U19)."""
        if hasattr(self, "font_manager"):
            r_fam, r_weight = self.font_manager.resolve_font_parts(
                PRESET_GLOBAL, available_families=self._get_available_font_families()
            )
        else:
            r_fam, r_weight = ("Segoe UI", None)
        r_sz = self.dialogue_font_size
        weight = r_weight or "normal"
        cached = getattr(self, "_ruler_measure_font", None)
        if cached is None:
            cached = tkfont.Font(root=self, family=r_fam, size=r_sz, weight=weight)
            self._ruler_measure_font = cached
        else:
            try:
                if (
                    cached.cget("family") != r_fam
                    or int(cached.cget("size")) != r_sz
                    or cached.cget("weight") != weight
                ):
                    cached.configure(family=r_fam, size=r_sz, weight=weight)
            except Exception:
                cached = tkfont.Font(root=self, family=r_fam, size=r_sz, weight=weight)
                self._ruler_measure_font = cached
        return cached

    def _get_54d_reference_safe_w(self) -> int:
        """Return canonical 54 digit-width pixel boundary using Nunito Bold reference font (U-07)."""
        rf = self._get_ruler_measure_font()
        sample = "1234567890" * (DIALOGUE_MAX_DIGITS // 10) + "1234567890"[: (DIALOGUE_MAX_DIGITS % 10)]
        return max(1, int(rf.measure(sample)))

    def _measure_dialogue_metrics(self, text: str) -> Dict[str, Any]:
        """Shared pixel-calibrated dialogue measurement helper (S17 / S02 / S09 U-07).

        Uses constant Nunito Bold ruler font for `safe_w` (54 digit-widths)
        and active editor font for rendered line widths, with O(1) fast-path
        for non-overflowing lines and O(log L) binary search when overflowing.
        """
        f = self._get_dialogue_measure_font()
        safe_w = self._get_54d_reference_safe_w()
        digit_w = safe_w / float(DIALOGUE_MAX_DIGITS)
        placeholder_sample = "PlayerName"

        raw_lines = text.split("\n") if text else [""]
        line_metrics: List[Dict[str, Any]] = []

        for line_no, raw_line in enumerate(raw_lines, start=1):
            units: List[Tuple[int, str]] = []
            pos = 0
            for m in NGUI_TOKEN_RE.finditer(raw_line):
                if m.start() > pos:
                    for j in range(pos, m.start()):
                        units.append((j, raw_line[j]))
                tok = m.group(0)
                ruby_m = RUBY_RE.fullmatch(tok)
                if ruby_m:
                    base_start = m.start(3)
                    base_end = m.end(3)
                    if base_start >= 0 and base_end >= base_start:
                        for j in range(base_start, base_end):
                            units.append((j, raw_line[j]))
                elif PLACEHOLDER_RE.fullmatch(tok):
                    units.append((m.start(), placeholder_sample))
                pos = m.end()
            if pos < len(raw_line):
                for j in range(pos, len(raw_line)):
                    units.append((j, raw_line[j]))

            full_rendered = "".join(piece for _, piece in units)
            pixel_width = int(f.measure(full_rendered)) if full_rendered else 0
            overflow_raw_start: Optional[int] = None

            if pixel_width > safe_w and units:
                lo, hi = 1, len(units)
                while lo < hi:
                    mid = (lo + hi) // 2
                    w_mid = int(f.measure("".join(piece for _, piece in units[:mid])))
                    if w_mid > safe_w:
                        hi = mid
                    else:
                        lo = mid + 1
                overflow_raw_start = units[lo - 1][0]

            line_metrics.append({
                "line_no": line_no,
                "pixel_width": pixel_width,
                "overflow_raw_start": overflow_raw_start,
                "raw_len": len(raw_line),
            })

        line_count = len(raw_lines)
        return {
            "safe_w": safe_w,
            "digit_w": digit_w,
            "line_count": line_count,
            "has_line_overflow": line_count >= 4,
            "has_width_overflow": any(l["overflow_raw_start"] is not None for l in line_metrics),
            "lines": line_metrics,
        }

    def _update_char_overflow_indicator(self, text: Optional[str] = None) -> None:
        """Update pixel-calibrated 50d x 3L indicator in dialogue header (U06, DEF-04)."""
        lbl = getattr(self, "lbl_char_overflow", None)
        if not lbl or not lbl.winfo_exists():
            return
        t = self.theme
        if getattr(self, "is_box0_active", False):
            lbl.config(text="Metadata (unmeasured)", fg=t["fg_muted"])
            return
        if text is None:
            if hasattr(self, "txt_dialogue") and self.txt_dialogue.winfo_exists():
                text = self.txt_dialogue.get("1.0", "end-1c")
            else:
                text = ""
        metrics = self._measure_dialogue_metrics(text)
        digit_w = max(1e-6, float(metrics["digit_w"]))
        max_px = max((l["pixel_width"] for l in metrics["lines"]), default=0)
        d_equiv = int(round(max_px / digit_w))
        line_count = metrics["line_count"]
        is_ov = bool(metrics["has_width_overflow"] or metrics["has_line_overflow"])
        ov_fg = "#c9184a" if self._is_light_theme() else "#ff5c7c"
        lbl.config(
            text=f"{d_equiv}/{DIALOGUE_MAX_DIGITS}d · {line_count}/{DIALOGUE_MAX_LINES}L",
            fg=ov_fg if is_ov else t["fg_muted"],
        )

    def _apply_overflow_highlights(self, widget: Optional[tk.Text]) -> None:
        """Apply inline pixel-calibrated horizontal overflow highlights on a Text widget (Box 0 immune)."""
        if not widget or not widget.winfo_exists():
            return
        if getattr(self, "is_box0_active", False) and widget in (
            getattr(self, "txt_dialogue", None),
            getattr(self, "txt_dialogue_preview", None),
        ):
            try:
                widget.tag_remove("line_overflow", "1.0", tk.END)
            except Exception:
                pass
            return
        try:
            widget.tag_remove("line_overflow", "1.0", tk.END)
            text = widget.get("1.0", "end-1c")
            metrics = self._measure_dialogue_metrics(text)
            for info in metrics["lines"]:
                ov_start = info["overflow_raw_start"]
                if ov_start is not None:
                    ln = info["line_no"]
                    widget.tag_add("line_overflow", f"{ln}.{ov_start}", f"{ln}.end")
        except Exception:
            pass

    def _apply_gutter_overflow_tag(self, gutter_widget: Optional[tk.Text]) -> None:
        """Color vertical line-number gutter red from line 4+ (3 or more linebreaks)."""
        if not gutter_widget or not gutter_widget.winfo_exists():
            return
        if getattr(self, "is_box0_active", False) and gutter_widget == getattr(self, "gutter_clean", None):
            try:
                gutter_widget.tag_remove("gutter_overflow", "1.0", tk.END)
            except Exception:
                pass
            return
        try:
            ov_fg = "#ff5c7c" if not self._is_light_theme() else "#c9184a"
            d_sz = self.dialogue_font_size
            gutter_widget.tag_configure(
                "gutter_overflow",
                foreground=ov_fg,
                font=self._get_dialogue_font_tuple(d_sz, "bold"),
            )
            gutter_widget.tag_remove("gutter_overflow", "1.0", tk.END)
            total_lines = int(gutter_widget.index("end-1c").split(".")[0])
            if total_lines >= 4:
                gutter_widget.tag_add("gutter_overflow", "4.0", tk.END)
        except Exception:
            pass

    def _draw_single_pixel_ruler(self, canvas: tk.Canvas, x0: int) -> None:
        """Render tick marks and constant 50 digit-width overflow zone on a Canvas ruler (U19)."""
        if not canvas or not canvas.winfo_exists():
            return
        t = self.theme
        light = self._is_light_theme()
        gutter_bg = "#e8e8e8" if light else "#2d2d30"
        gutter_fg = "#707070" if light else "#858585"
        red_zone_bg = "#ffd6dc" if light else "#4a1c24"
        red_fg = "#c9184a" if light else "#ff5c7c"
        marker_fg = t["misora_pink"]

        canvas.configure(bg=gutter_bg)
        canvas.delete("all")

        safe_w = self._get_54d_reference_safe_w()
        digit_w = safe_w / float(DIALOGUE_MAX_DIGITS)
        ch = max(20, int(canvas.winfo_height() or 20))
        cw = max(int(canvas.winfo_width() or 0), int(x0 + safe_w + 180))

        # Red overflow zone past 54 digit-widths
        ov_x = x0 + safe_w
        canvas.create_rectangle(ov_x, 0, cw, ch, fill=red_zone_bg, outline="")
        canvas.create_line(x0, ch - 1, cw, ch - 1, fill=gutter_fg)

        col = 0
        while True:
            tx = x0 + int(round(col * digit_w))
            if tx > cw - 8:
                break
            is_major = (col % 10 == 0) or (col == DIALOGUE_MAX_DIGITS)
            tick_h = 8 if is_major else 4
            tick_col = red_fg if col > DIALOGUE_MAX_DIGITS else (marker_fg if col == DIALOGUE_MAX_DIGITS else gutter_fg)
            canvas.create_line(tx, ch - tick_h - 1, tx, ch - 1, fill=tick_col, width=2 if col == DIALOGUE_MAX_DIGITS else 1)
            if is_major:
                if col == DIALOGUE_MAX_DIGITS:
                    canvas.create_text(
                        ov_x - 3, 2, text=f"{DIALOGUE_MAX_DIGITS}d", anchor="ne", fill=tick_col, font=("Segoe UI", 7, "bold")
                    )
                elif col != 50:
                    canvas.create_text(
                        tx + 2, 2, text=str(col), anchor="nw", fill=tick_col, font=("Segoe UI", 7, "normal")
                    )
            if col == 50:
                col = DIALOGUE_MAX_DIGITS
            elif col == DIALOGUE_MAX_DIGITS:
                col = 55
            else:
                col += 5

        canvas.create_line(ov_x, 0, ov_x, ch, fill=marker_fg, width=2)
        canvas.create_text(ov_x + 5, 2, text=f">{DIALOGUE_MAX_DIGITS}d", anchor="nw", fill=red_fg, font=("Segoe UI", 7, "bold"))

    def _redraw_pixel_rulers(self) -> None:
        """Redraw both Clean and All Script Canvas rulers aligned to editor text origins."""
        if hasattr(self, "ruler_clean") and self.ruler_clean.winfo_exists():
            x0_clean = (self.gutter_clean.winfo_reqwidth() + 2 if getattr(self, "show_line_numbers", True) and hasattr(self, "gutter_clean") else 0) + 11
            try:
                if self.txt_dialogue.winfo_ismapped() and self.ruler_clean.winfo_ismapped():
                    x0_clean = (self.txt_dialogue.winfo_rootx() - self.ruler_clean.winfo_rootx()) + int(self.txt_dialogue.cget("bd") or 1) + int(self.txt_dialogue.cget("padx") or 10)
            except Exception:
                pass
            self._draw_single_pixel_ruler(self.ruler_clean, max(0, x0_clean))

        if hasattr(self, "ruler_cont") and self.ruler_cont.winfo_exists():
            x0_cont = 32
            try:
                if hasattr(self, "txt_all_script") and self.txt_all_script.winfo_ismapped() and self.ruler_cont.winfo_ismapped():
                    x0_cont = (
                        (self.txt_all_script.winfo_rootx() - self.ruler_cont.winfo_rootx())
                        + int(self.txt_all_script.cget("bd") or 1)
                        + int(self.txt_all_script.cget("padx") or 12)
                        + 20
                    )
                else:
                    cards = getattr(self, "_card_widgets", {})
                    first_txt = next((c.get("txt") for c in cards.values() if c.get("txt") and c["txt"].winfo_ismapped()), None)
                    if first_txt is not None and self.ruler_cont.winfo_ismapped():
                        x0_cont = (first_txt.winfo_rootx() - self.ruler_cont.winfo_rootx()) + int(first_txt.cget("bd") or 1) + int(first_txt.cget("padx") or 8)
            except Exception:
                pass
            self._draw_single_pixel_ruler(self.ruler_cont, max(0, x0_cont))

    def on_revert_box(self) -> None:
        if self.current_file_path:
            self.open_file(self.current_file_path, reload_from_disk=True)

    def on_insert_playername(self) -> None:
        self.apply_ngui_wrapper("{playername}", "")

    def _sync_modified_boxes_to_xuat(
        self,
        doc: Any,
        boxes_or_indices: Iterable[Any],
        orig_jp_map: Dict[int, str],
        backup_dir: Optional[Path] = None,
    ) -> Set[str]:
        """
        Synchronize modified boxes to XUAT dictionaries with immutable b_uid JP key resolution
        and conflict preview gate (BUG-25 / DEP-7).
        Returns set of synced file names.
        """
        if not self.var_sync_xuat.get() or not self.xuat_search_roots or not doc or not getattr(doc, "boxes", None):
            return set()

        synced_files: Set[str] = set()
        for item in boxes_or_indices:
            if isinstance(item, int):
                if not (0 <= item < len(doc.boxes)):
                    continue
                box_obj = doc.boxes[item]
                b_idx = item
            else:
                box_obj = item
                b_idx = getattr(box_obj, "index", -1)

            b_uid = _get_box_uid(box_obj)
            orig_key = ""
            if b_uid is not None:
                # Prefer document's orig_jp_map before global sync_manager cache
                orig_key = orig_jp_map.get(b_uid, "") or self.sync_manager.get_jp_key(b_uid, "")
                if not orig_key:
                    # Newly inserted or untracked box with b_uid: skip XUAT sync, NO positional fallback!
                    continue
            else:
                # b_uid is None: only then fall back to positional lookup
                if hasattr(self, "_original_box_texts") and 0 <= b_idx < len(doc.boxes):
                    orig_key = self._original_box_texts.get(b_idx, "")
                if not orig_key:
                    continue

            # Preview matches and gate with conflict confirmation
            previews = self.sync_manager.preview_matches(
                japanese_key=orig_key,
                search_roots=self.xuat_search_roots,
            )
            has_conflict = any(p.is_conflict for p in previews)
            if has_conflict:
                conflict_files = ", ".join(sorted({p.file_path.name for p in previews if p.is_conflict}))
                prompt_msg = (
                    f"Conflicting translations found in XUAT dictionaries for:\n"
                    f"'{orig_key}'\n\n"
                    f"Conflicting file(s): {conflict_files}\n\n"
                    f"Do you want to overwrite all occurrences with:\n"
                    f"'{box_obj.clean_text}'?"
                )
                if not messagebox.askyesno("XUAT Translation Conflict", prompt_msg):
                    continue

            matches = self.sync_manager.find_and_update(
                japanese_key=orig_key,
                new_english_text=box_obj.clean_text,
                search_roots=self.xuat_search_roots,
                backup=True,
                backup_dir=backup_dir,
            )
            for m in matches:
                synced_files.add(m.file_path.name)

        return synced_files

    # -------------------------------------------------------------------------
    # Save & Patch Actions (Byte-Exact In-Place Repack)
    # -------------------------------------------------------------------------
    def on_save(self) -> bool:
        """Repack and save the active file in-place, with optional XUAT dictionary sync.

        Returns True on successful primary save, False on failure or no active file (S2).
        Secondary XUAT failure logs a warning, retains _modified_boxes, and returns True.
        """
        if not self.current_file_path:
            messagebox.showinfo("Nothing to Save", "No active file is open.")
            return False

        try:
            backup_dir = self._get_backup_dir()
            cur_p = Path(self.current_file_path).resolve()

            if not self.is_bundle_file and not self.current_doc:
                if self.current_file_path.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(self.current_file_path, backup_dir, tag="bak")
                    shutil.copy2(self.current_file_path, bak_path)
                if not getattr(self, "var_preview_compiled", None) or not self.var_preview_compiled.get():
                    content = self.txt_continuous.get("1.0", "end-1c") if self.var_continuous_view.get() else self.txt_dialogue.get("1.0", "end-1c")
                    self._plain_text_content = content
                else:
                    content = self._plain_text_content
                doc_entry = self.open_documents.get(cur_p, {})
                enc = doc_entry.get("encoding", "utf-8")
                has_bom = bool(doc_entry.get("has_bom", False))
                nl = doc_entry.get("newline", None)
                write_atomic_encoded(self.current_file_path, content, encoding=enc, has_bom=has_bom, newline=nl)
                if cur_p in self.open_documents:
                    self.open_documents[cur_p]["dirty"] = False
                    self.open_documents[cur_p]["plain_text"] = content
                self.is_dirty = False
                self._record_saved_checkpoint(self.current_file_path, None, content)
                self.undo_journal.mark_saved(str(self.current_file_path))
                self._dirty_state_changed()
                self.lbl_status.config(text=f"[SAVED] {self.current_file_path.name} saved successfully!")
                self.logger.info("File I/O", f"Saved plain text file '{self.current_file_path}' (backup in {backup_dir.name if backup_dir else 'none'})")
                return True

            if getattr(self, "is_box0_active", False):
                self._on_box0_metadata_edited()
            elif not self.current_doc.boxes:
                # 0-box metadata-only story (BUG-19)
                pass
            elif self.var_preview_compiled.get():
                if 0 <= self.current_box_idx < len(self.current_doc.boxes):
                    box = self.current_doc.boxes[self.current_box_idx]
                    new_sp = self.speaker_var.get()
                    if new_sp != box.speaker:
                        self.current_doc.inject_box(self.current_box_idx, new_sp, box.clean_text)
            elif self.var_continuous_view.get():
                self._sync_continuous_box_from_widget()
                if 0 <= self.current_box_idx < len(self.current_doc.boxes):
                    box = self.current_doc.boxes[self.current_box_idx]
                    new_sp = self.speaker_var.get()
                    if new_sp != box.speaker:
                        self.current_doc.inject_box(self.current_box_idx, new_sp, box.clean_text)
            else:
                if 0 <= self.current_box_idx < len(self.current_doc.boxes):
                    new_sp = self.speaker_var.get()
                    new_tx = self.txt_dialogue.get("1.0", "end-1c")
                    self.current_doc.inject_box(self.current_box_idx, new_sp, new_tx)
                    self._modified_boxes.add(self.current_box_idx)
                    box = self.current_doc.boxes[self.current_box_idx]
                    b_uid = _get_box_uid(box)
                    if b_uid is not None:
                        if not hasattr(self, "_modified_box_uids"):
                            self._modified_box_uids = set()
                        self._modified_box_uids.add(b_uid)

            if self.is_bundle_file:
                if self.current_file_path.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(self.current_file_path, backup_dir, tag="bak")
                    shutil.copy2(self.current_file_path, bak_path)
                written_size = save_bundle_story(
                    self.current_unity_env,
                    self.current_text_obj,
                    self.current_doc,
                    self.current_file_path,
                    backup_dir=None
                )
                if cur_p in self.open_documents:
                    self.open_documents[cur_p]["dirty"] = False
                self.is_dirty = False
                self._record_saved_checkpoint(self.current_file_path, self.current_doc, "")
                self.undo_journal.mark_saved(str(self.current_file_path))
                self._dirty_state_changed()
                self.lbl_status.config(text=f"[SAVED & PATCHED] {self.current_file_path.name} ({written_size / 1024:.1f} KB) in-place successfully!")
                self.logger.info("File I/O", f"Patched bundle '{self.current_file_path}' ({written_size} bytes)")
            else:
                if self.current_file_path.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(self.current_file_path, backup_dir, tag="bak")
                    shutil.copy2(self.current_file_path, bak_path)
                v2_text = self.current_doc.to_v2_text()
                doc_entry = self.open_documents.get(cur_p, {})
                enc = doc_entry.get("encoding", "utf-8")
                has_bom = bool(doc_entry.get("has_bom", False))
                nl = doc_entry.get("newline", None)
                write_atomic_utf8(self.current_file_path, v2_text, encoding=enc, has_bom=has_bom, newline=nl)
                if cur_p in self.open_documents:
                    self.open_documents[cur_p]["dirty"] = False
                self.is_dirty = False
                self._record_saved_checkpoint(self.current_file_path, self.current_doc, "")
                self.undo_journal.mark_saved(str(self.current_file_path))
                self._dirty_state_changed()
                self.lbl_status.config(text=f"[SAVED] {self.current_file_path.name} saved successfully!")
                self.logger.info("File I/O", f"Saved v2 script '{self.current_file_path}'")

            if self.var_sync_xuat.get() and self.xuat_search_roots:
                try:
                    if self.current_doc and getattr(self.current_doc, "boxes", None) and not getattr(self, "_original_jp_by_uid", None):
                        self._original_jp_by_uid = {
                            _get_box_uid(b): b.clean_text for b in self.current_doc.boxes if _get_box_uid(b) is not None
                        }
                        for b_uid, jp in self._original_jp_by_uid.items():
                            self.sync_manager.register_jp_key(b_uid, jp)

                    boxes_to_sync = sorted(self._modified_boxes) if self._modified_boxes else [self.current_box_idx]
                    synced_files = self._sync_modified_boxes_to_xuat(
                        doc=self.current_doc,
                        boxes_or_indices=boxes_to_sync,
                        orig_jp_map=getattr(self, "_original_jp_by_uid", {}),
                        backup_dir=backup_dir,
                    )
                    if synced_files:
                        files_str = ", ".join(sorted(synced_files))
                        self.lbl_status.config(text=self.lbl_status.cget("text") + f" | Synced XUAT file(s): {files_str}")
                        self.logger.info("XUAT Sync", f"Synced XUAT file(s): {files_str}")
                    self._modified_boxes.clear()
                    if hasattr(self, "_modified_box_uids"):
                        self._modified_box_uids.clear()
                    if cur_p in self.open_documents:
                        self.open_documents[cur_p]["modified_box_uids"] = set()
                except Exception as xuat_err:
                    self.logger.warning("XUAT", f"Secondary XUAT sync failed (primary save succeeded): {xuat_err}")
                    self.lbl_status.config(text=self.lbl_status.cget("text") + f" | (XUAT sync failed: {xuat_err})")
            else:
                self._modified_boxes.clear()
                if hasattr(self, "_modified_box_uids"):
                    self._modified_box_uids.clear()
                if cur_p in self.open_documents:
                    self.open_documents[cur_p]["modified_box_uids"] = set()

            return True

        except Exception as e:
            self.logger.exception(f"Save/Patch failed for '{self.current_file_path}':", e)
            messagebox.showerror("Save Failed", f"Failed to repack or save:\n{e}")
            return False

    def _save_active_document_state(self) -> None:
        """Save mutable UI/view state for active document into open_documents cache (S06 / BUG-12)."""
        if not self.current_file_path:
            return
        cur_p = Path(self.current_file_path).resolve()
        if cur_p not in self.open_documents:
            return

        if not hasattr(self, "_modified_box_uids"):
            self._modified_box_uids = set()
        if not hasattr(self, "_locked_box_uids"):
            self._locked_box_uids = set()

        if self.current_doc and self.current_doc.boxes:
            for idx in getattr(self, "_modified_boxes", set()):
                if 0 <= idx < len(self.current_doc.boxes):
                    b_uid = _get_box_uid(self.current_doc.boxes[idx])
                    if b_uid is not None:
                        self._modified_box_uids.add(b_uid)
            for idx in getattr(self, "_locked_boxes", set()):
                if 0 <= idx < len(self.current_doc.boxes):
                    b_uid = _get_box_uid(self.current_doc.boxes[idx])
                    if b_uid is not None:
                        self._locked_box_uids.add(b_uid)

        entry = self.open_documents[cur_p]
        entry["current_box_idx"] = getattr(self, "current_box_idx", 0)
        entry["is_box0_active"] = getattr(self, "is_box0_active", False)
        entry["locked_box_uids"] = set(getattr(self, "_locked_box_uids", set()))
        entry["modified_box_uids"] = set(getattr(self, "_modified_box_uids", set()))
        if hasattr(self, "_original_jp_by_uid"):
            entry["original_jp_by_uid"] = dict(self._original_jp_by_uid)
        if not self.current_doc:
            entry["plain_text"] = getattr(self, "_plain_text_content", "")
        entry["dirty"] = getattr(self, "is_dirty", False)

    def _find_open_doc_key(self, path: Union[str, Path]) -> Optional[Path]:
        """Find matching canonical Path key in open_documents normalized for Windows path casing (BUG-24)."""
        if not path or not hasattr(self, "open_documents") or not self.open_documents:
            return None
        try:
            target_norm = os.path.normcase(str(Path(path).resolve()))
        except Exception:
            target_norm = os.path.normcase(str(path))
        for k in self.open_documents.keys():
            try:
                k_norm = os.path.normcase(str(Path(k).resolve()))
            except Exception:
                k_norm = os.path.normcase(str(k))
            if k_norm == target_norm:
                return k if isinstance(k, Path) else Path(k)
        return None

    def _save_document_entry(self, path: Union[str, Path]) -> bool:
        """Save an open document entry to disk without switching active UI context (S06 / BUG-12)."""
        cur_p = Path(path).resolve()
        if cur_p == (Path(self.current_file_path).resolve() if self.current_file_path else None):
            return self.on_save()

        matched_k = self._find_open_doc_key(cur_p)
        if matched_k is None or matched_k not in self.open_documents:
            self.logger.warning("File I/O", f"Cannot save non-open document: {cur_p}")
            return False

        entry = self.open_documents[matched_k]
        backup_dir = self._get_backup_dir()
        modified_uids = set(entry.get("modified_box_uids", set()))

        try:
            if entry.get("is_bundle", False):
                env = entry.get("env")
                obj = entry.get("obj")
                doc = entry.get("doc")
                if not doc:
                    return False
                if cur_p.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(cur_p, backup_dir, tag="bak")
                    shutil.copy2(cur_p, bak_path)
                written_size = save_bundle_story(
                    env, obj, doc, cur_p, backup_dir=None
                )
                entry["dirty"] = False
                entry["modified_box_uids"] = set()
                self._record_saved_checkpoint(cur_p, doc, "")
                self.undo_journal.mark_saved(str(cur_p))
                self.logger.info("File I/O", f"Saved inactive bundle '{cur_p}' ({written_size} bytes)")
            elif entry.get("doc") is not None:
                doc = entry.get("doc")
                if cur_p.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(cur_p, backup_dir, tag="bak")
                    shutil.copy2(cur_p, bak_path)
                v2_text = doc.to_v2_text()
                enc = entry.get("encoding", "utf-8")
                has_bom = bool(entry.get("has_bom", False))
                nl = entry.get("newline", None)
                write_atomic_encoded(cur_p, v2_text, encoding=enc, has_bom=has_bom, newline=nl)
                entry["dirty"] = False
                entry["modified_box_uids"] = set()
                self._record_saved_checkpoint(cur_p, doc, "")
                self.undo_journal.mark_saved(str(cur_p))
                self.logger.info("File I/O", f"Saved inactive v2 script '{cur_p}'")
            else:
                if cur_p.is_file() and backup_dir:
                    bak_path = make_collision_resistant_backup_path(cur_p, backup_dir, tag="bak")
                    shutil.copy2(cur_p, bak_path)
                content = entry.get("plain_text", "")
                enc = entry.get("encoding", "utf-8")
                has_bom = bool(entry.get("has_bom", False))
                nl = entry.get("newline", None)
                write_atomic_encoded(cur_p, content, encoding=enc, has_bom=has_bom, newline=nl)
                entry["dirty"] = False
                self._record_saved_checkpoint(cur_p, None, content)
                self.undo_journal.mark_saved(str(cur_p))
                self.logger.info("File I/O", f"Saved inactive plain text file '{cur_p}'")

            if self.var_sync_xuat.get() and self.xuat_search_roots and entry.get("doc") and modified_uids:
                doc = entry.get("doc")
                orig_by_uid = entry.get("original_jp_by_uid", {})
                try:
                    boxes_to_sync = [b for b in doc.boxes if _get_box_uid(b) in modified_uids]
                    self._sync_modified_boxes_to_xuat(
                        doc=doc,
                        boxes_or_indices=boxes_to_sync,
                        orig_jp_map=orig_by_uid,
                        backup_dir=backup_dir,
                    )
                except Exception as e:
                    self.logger.warning("UI / Theme / Config", f"Secondary XUAT sync failed for inactive doc: {e}")

            self._refresh_opened_files_list()
            return True
        except Exception as exc:
            self.logger.exception(f"Failed saving document entry '{cur_p}':", exc)
            return False

    def on_reload(self) -> None:
        if self.current_file_path:
            self.open_file(self.current_file_path, reload_from_disk=True)

    # -------------------------------------------------------------------------
    # Search Engine, Background Worker & Substring Result Highlighting
    # -------------------------------------------------------------------------
    def on_start_search(self) -> None:
        if getattr(self, "_is_searching", False) and getattr(self, "_search_thread", None) and self._search_thread.is_alive():
            return

        query = self.search_var.get().strip()
        if not query:
            self._is_searching = False
            return

        if self.var_regex.get():
            try:
                flags = 0 if self.var_case.get() else re.IGNORECASE
                re.compile(query, flags)
            except re.error as e:
                self._is_searching = False
                messagebox.showerror("Search", f"Invalid regular expression:\n{e}")
                return

        opts = SearchOptions(
            query=query,
            match_case=self.var_case.get(),
            use_regex=self.var_regex.get(),
            ignore_whitespace=self.var_ignore_ws.get(),
            include_bundles=self.var_inc_bundles.get(),
            include_text=self.var_inc_text.get()
        )
        self.active_search_options = opts

        scope = self.scope_var.get()
        target_paths: List[Path] = []

        if scope == "current":
            if getattr(self, "open_documents", None):
                target_paths = list(self.open_documents.keys())
            elif self.current_file_path:
                target_paths = [self.current_file_path]
            else:
                self._is_searching = False
                messagebox.showinfo("Search", "No file is currently open.")
                return
        elif scope == "folder":
            ent_val = self.folder_path_var.get().strip() if hasattr(self, "folder_path_var") else ""
            if ent_val and Path(ent_val).is_dir():
                self.selected_search_folder = Path(ent_val)
            if self.selected_search_folder and self.selected_search_folder.is_dir():
                target_paths = [self.selected_search_folder]
            else:
                fld = filedialog.askdirectory(title="Select Folder to Search In")
                if not fld:
                    self._is_searching = False
                    return
                self.selected_search_folder = Path(fld)
                self.folder_path_var.set(str(fld))
                target_paths = [self.selected_search_folder]
        else:
            ent_val = self.folder_path_var.get().strip() if hasattr(self, "folder_path_var") else ""
            if ent_val and Path(ent_val).is_dir():
                self._set_project_folder(Path(ent_val))
            active_proj = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
            target_paths = self._resolve_project_search_roots(active_proj)

        self._reset_search_results_state()
        self._switch_dock_tab("search")
        self.lbl_results_title.config(text="Searching...")
        self.btn_find.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.progress_bar.pack(fill="x", padx=8, pady=(0, 2))
        self.progress_bar["value"] = 0
        cancel_event = threading.Event()
        self._search_cancel_event = cancel_event
        self.search_cancel_flag = False
        self._search_seq = getattr(self, "_search_seq", 0) + 1
        current_seq = self._search_seq
        self._is_searching = True
        self.logger.info("Search", f"Started search query='{query}' scope={scope} roots={len(target_paths)}")

        mem_docs: Dict[Path, Any] = {}
        skip_paths: set = set()
        initial_skipped: List[Tuple[Path, str]] = []

        if getattr(self, "open_documents", None):
            for fp, entry in self.open_documents.items():
                resolved_fp = Path(fp).resolve()
                if isinstance(entry, dict):
                    if entry.get("doc"):
                        orig_doc = entry["doc"]
                        # Capture immutable snapshot on UI thread before thread start (Rule 15 / SEARCH-RACE)
                        try:
                            snap_records = [
                                Record(cmd_id=r.cmd_id, cmd_name=r.cmd_name, args=list(r.args), category=r.category)
                                for r in orig_doc.records
                            ]
                            mem_docs[resolved_fp] = StoryDocument(snap_records)
                        except Exception as ex:
                            self.logger.warning("Search", f"Failed to snapshot open document {fp}: {ex}")
                            # Grok-E02: NEVER pass live orig_doc; isolate and skip
                            skip_paths.add(resolved_fp)
                            skip_paths.add(Path(fp))
                            initial_skipped.append((Path(fp), f"Snapshot error: {ex}"))
                    elif entry.get("plain_text") is not None:
                        txt_val = str(entry["plain_text"])
                        mem_docs[resolved_fp] = txt_val

        target_fn = self._run_background_search
        try:
            import inspect
            eff = getattr(target_fn, "side_effect", None)
            fn_to_check = eff if callable(eff) else target_fn
            sig = inspect.signature(fn_to_check)
            params = list(sig.parameters.values())
            has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
            has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)

            if has_varargs or len(params) >= 7:
                t_args = (target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped, cancel_event)
                t_kwargs = {}
            elif len(params) == 6:
                t_args = (target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped)
                t_kwargs = {"cancel_event": cancel_event} if has_varkw else {}
            elif has_varkw:
                t_args = (target_paths, opts, mem_docs)
                t_kwargs = {
                    "search_seq": current_seq,
                    "skip_paths": skip_paths,
                    "initial_skipped": initial_skipped,
                    "cancel_event": cancel_event,
                }
            else:
                avail_args = [target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped, cancel_event]
                t_args = tuple(avail_args[:len(params)])
                t_kwargs = {}
        except Exception:
            t_args = (target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped, cancel_event)
            t_kwargs = {}

        t = threading.Thread(
            target=target_fn,
            args=t_args,
            kwargs=t_kwargs,
            daemon=True
        )
        self._search_thread = t
        t.start()
        if getattr(self, "_search_poll_job", None) is None and self.winfo_exists():
            self._search_poll_job = self.after(100, self._process_search_queue)

    def _reset_search_results_state(self) -> None:
        self.active_search_results.clear()
        self.search_file_groups.clear()
        self._file_group_lookup.clear()
        self._result_line_map.clear()
        self._result_idx_to_line.clear()
        self._selected_result_idx = None

        self.txt_results.config(state="normal")
        self.txt_results.delete("1.0", tk.END)
        self.txt_results.config(state="disabled")

    def on_cancel_search(self) -> None:
        self.search_cancel_flag = True
        if hasattr(self, "_search_cancel_event") and self._search_cancel_event is not None:
            self._search_cancel_event.set()
        self._is_searching = False
        self.btn_cancel.config(state="disabled")
        self.lbl_status.config(text="Cancelling search...")
        self.logger.info("Search", "Search cancelled by user.")

    def _run_background_search(
        self,
        paths: List[Path],
        options: SearchOptions,
        mem_docs: Optional[Dict[Path, Any]] = None,
        search_seq: int = 1,
        skip_paths: Optional[set] = None,
        initial_skipped: Optional[List[Tuple[Path, str]]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        """Executed inside a background daemon thread (Rule 15, Part B.8, BUG-01)."""
        total_found = 0
        skipped_entries: List[Tuple[Path, str]] = list(initial_skipped or [])

        if cancel_event is not None:
            def _is_cancelled() -> bool:
                return cancel_event.is_set() or bool(getattr(self, "_destroyed", False))
        else:
            def _is_cancelled() -> bool:
                ev = getattr(self, "_search_cancel_event", None)
                return (
                    (ev is not None and ev.is_set())
                    or bool(getattr(self, "search_cancel_flag", False))
                    or bool(getattr(self, "_destroyed", False))
                )

        def on_prog(cur, tot, filename):
            if _is_cancelled():
                return
            _put_queue_cancellable(
                self.search_queue,
                ("progress", cur, tot, filename, search_seq),
                cancel_event=cancel_event,
                legacy_flag_getter=_is_cancelled if cancel_event is None else None,
            )

        def on_err(fp, reason):
            skipped_entries.append((Path(fp), str(reason)))

        try:
            for target in paths:
                if _is_cancelled():
                    break
                try:
                    if not target.exists():
                        skipped_entries.append((Path(target), "Path not found"))
                        continue
                    if target.is_file():
                        resolved_target = target.resolve()
                        if skip_paths and (target in skip_paths or resolved_target in skip_paths):
                            continue
                        mem_doc = None
                        if mem_docs:
                            mem_doc = mem_docs.get(target) or mem_docs.get(resolved_target)
                        results = self.search_engine.search_file(
                            target,
                            options,
                            doc=mem_doc,
                            on_error=on_err,
                            should_cancel=_is_cancelled,
                        )
                    else:
                        results = self.search_engine.search_directory(
                            target, options, recursive=True,
                            on_progress=on_prog,
                            should_cancel=_is_cancelled,
                            in_memory_docs=mem_docs,
                            on_error=on_err,
                            skip_paths=skip_paths,
                        )
                    total_found += len(results)
                    if not _put_queue_cancellable(
                        self.search_queue,
                        ("batch", results, search_seq),
                        cancel_event=cancel_event,
                        legacy_flag_getter=_is_cancelled if cancel_event is None else None,
                    ):
                        break
                except Exception as ex:
                    skipped_entries.append((Path(target), str(ex)))
        finally:
            _put_queue_cancellable(
                self.search_queue,
                ("finished", total_found, skipped_entries, search_seq),
                cancel_event=cancel_event,
                legacy_flag_getter=_is_cancelled if cancel_event is None else None,
            )

    def _process_search_queue(self) -> None:
        """Polls results from background worker thread and renders highlighted hits."""
        try:
            while True:
                msg = self.search_queue.get_nowait()
                kind = msg[0]

                # Drop stale search messages (BUG-22)
                seq = None
                if kind == "batch" and len(msg) >= 3:
                    seq = msg[2]
                elif kind == "progress" and len(msg) >= 5:
                    seq = msg[4]
                elif kind == "finished" and len(msg) >= 4:
                    seq = msg[3]

                if seq is not None and hasattr(self, "_search_seq") and seq != self._search_seq:
                    continue

                if kind == "progress":
                    _, cur, tot, fname, *_ = msg
                    if tot > 0:
                        pct = int((cur / tot) * 100)
                        self.progress_bar["value"] = pct
                        self.lbl_status.config(text=f"Searching ({cur}/{tot}): {fname}")

                elif kind == "batch":
                    batch_results: List[SearchResult] = msg[1]
                    if batch_results:
                        for r in batch_results:
                            res_idx = len(self.active_search_results)
                            self.active_search_results.append(r)
                            fkey = str(r.file_path)
                            grp = self._file_group_lookup.get(fkey)
                            if grp is None:
                                grp = {
                                    "key": fkey,
                                    "path": r.file_path,
                                    "collapsed": False,
                                    "indices": [],
                                }
                                self._file_group_lookup[fkey] = grp
                                self.search_file_groups.append(grp)
                            grp["indices"].append(res_idx)
                        self._render_search_results()

                elif kind == "finished":
                    self._is_searching = False
                    total = len(self.active_search_results)
                    skipped = msg[2] if len(msg) > 2 else []
                    skip_count = len(skipped)
                    cancel_ev = getattr(self, "_search_cancel_event", None)
                    is_cancelled = (cancel_ev is not None and cancel_ev.is_set()) or bool(getattr(self, "search_cancel_flag", False))

                    if is_cancelled:
                        skip_info = f" ({skip_count} skipped)" if skip_count else ""
                        self.lbl_results_title.config(text=f"Search Cancelled ({total} matches{skip_info})")
                        self.lbl_status.config(text=f"Search cancelled. Found {total} matches{skip_info}.")
                    elif total == 0:
                        if skip_count:
                            self.lbl_results_title.config(text=f"Search Results (0 matches, {skip_count} skipped)")
                            self.lbl_status.config(text=f"Search complete. 0 matches ({skip_count} skipped).")
                        else:
                            self.lbl_results_title.config(text="Search Results (0 matches)")
                            self.lbl_status.config(text="Search complete. No matches found.")
                    else:
                        skip_info = f" ({skip_count} skipped)" if skip_count else ""
                        self.lbl_results_title.config(text=f"Search Results ({total} matches{skip_info})")
                        self.lbl_status.config(text=f"Search complete. Found {total} matches{skip_info}.")

                    self.btn_find.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    self.progress_bar.pack_forget()
                    if skipped:
                        formatted_skipped = [
                            f"{p.name if isinstance(p, Path) else p} ({reason})"
                            if isinstance(item, tuple) and len(item) == 2 and (p := item[0], reason := item[1])
                            else str(item)
                            for item in skipped
                        ]
                        self.logger.warning("Search", f"Skipped inaccessible paths: {', '.join(formatted_skipped)}")
                    self.logger.info("Search", f"Search finished. Total matches={total}, skipped={skip_count}")
                    if not self.var_preview_compiled.get():
                        if self.var_continuous_view.get():
                            self._highlight_continuous_matches()
                        else:
                            self._highlight_dialogue_matches()

        except queue.Empty:
            pass

        self._search_poll_job = None
        try:
            if getattr(self, "_destroyed", False) or not self.winfo_exists():
                return
            search_th = getattr(self, "_search_thread", None)
            keep_polling = (
                bool(getattr(self, "_is_searching", False))
                or (search_th is not None and search_th.is_alive())
                or (not self.search_queue.empty())
            )
            if keep_polling:
                self._search_poll_job = self.after(100, self._process_search_queue)
        except Exception:
            pass

    def _render_search_results(self) -> None:
        """Render grouped search hits with WCAG contrast-safe inline keyword highlighting."""
        y_frac = self.txt_results.yview()[0]
        self._result_line_map.clear()
        self._result_idx_to_line.clear()

        self.txt_results.config(state="normal")
        self.txt_results.delete("1.0", tk.END)

        line_no = 1
        for grp in self.search_file_groups:
            fp: Path = grp["path"]
            indices: List[int] = grp["indices"]
            collapsed: bool = grp["collapsed"]
            arrow = "▶" if collapsed else "▼"
            count_word = "match" if len(indices) == 1 else "matches"
            header_text = f"{arrow} {fp.name} ({len(indices)} {count_word})\n"

            self.txt_results.insert(f"{line_no}.0", header_text, ("file_header",))
            self._result_line_map[line_no] = ("header", grp["key"])
            line_no += 1

            if collapsed:
                continue

            for res_idx in indices:
                r = self.active_search_results[res_idx]
                box_str = f"[Box #{r.box_index + 1}]" if r.box_index is not None else f"[Line {r.line_number}]"
                prefix_indent = "  "
                speaker_prefix = f" {r.speaker}: " if r.speaker else " "
                snippet = r.match_snippet

                row_tags = ("selected_row",) if res_idx == self._selected_result_idx else ()

                self.txt_results.insert(f"{line_no}.0", prefix_indent, row_tags)
                self.txt_results.insert(f"{line_no}.end", box_str, ("box_badge",) + row_tags)
                if r.speaker:
                    self.txt_results.insert(f"{line_no}.end", speaker_prefix, ("speaker_tag",) + row_tags)
                else:
                    self.txt_results.insert(f"{line_no}.end", speaker_prefix, row_tags)

                snip_col_start = len(prefix_indent) + len(box_str) + len(speaker_prefix)
                self.txt_results.insert(f"{line_no}.end", snippet + "\n", row_tags)

                if r.match_in_speaker and r.speaker:
                    sp_offset = len(prefix_indent) + len(box_str) + 1
                    hs = sp_offset + max(0, r.snippet_start)
                    he = sp_offset + max(r.snippet_start, r.snippet_end)
                    if he > hs:
                        self.txt_results.tag_add("match_hl", f"{line_no}.{hs}", f"{line_no}.{he}")
                else:
                    hs = snip_col_start + max(0, r.snippet_start)
                    he = snip_col_start + max(r.snippet_start, r.snippet_end)
                    if he > hs:
                        self.txt_results.tag_add("match_hl", f"{line_no}.{hs}", f"{line_no}.{he}")

                self._result_line_map[line_no] = ("item", res_idx)
                self._result_idx_to_line[res_idx] = line_no
                line_no += 1

        self.txt_results.config(state="disabled")
        self.txt_results.yview_moveto(y_frac)

    def _on_results_click(self, event: tk.Event) -> str:
        """Handle clicking a file header (collapse/expand) or a match row (jump & highlight)."""
        self.txt_results.focus_set()
        idx_str = self.txt_results.index(f"@{event.x},{event.y}")
        line_no = int(idx_str.split(".")[0])
        entry = self._result_line_map.get(line_no)
        if not entry:
            return "break"

        kind, payload = entry
        if kind == "header":
            grp = self._file_group_lookup.get(payload)
            if grp is not None:
                grp["collapsed"] = not grp["collapsed"]
                self._render_search_results()
        elif kind == "item":
            self._select_result_index(int(payload), jump=True)
        return "break"

    def _on_results_step(self, delta: int) -> str:
        """Navigate up/down through visible search hits using keyboard arrow keys."""
        if not self.active_search_results:
            return "break"

        if self._selected_result_idx is None:
            next_idx = 0
        else:
            next_idx = max(0, min(len(self.active_search_results) - 1, self._selected_result_idx + delta))

        self._select_result_index(next_idx, jump=True)
        return "break"

    def _select_result_index(self, idx: int, jump: bool = True) -> None:
        """Highlight selected search row and jump to the matching file/box."""
        if not (0 <= idx < len(self.active_search_results)):
            return

        self._selected_result_idx = idx
        res = self.active_search_results[idx]

        grp = self._file_group_lookup.get(str(res.file_path))
        if grp and grp["collapsed"]:
            grp["collapsed"] = False
            self._render_search_results()
        else:
            self.txt_results.config(state="normal")
            self.txt_results.tag_remove("selected_row", "1.0", tk.END)
            target_line = self._result_idx_to_line.get(idx)
            if target_line is not None:
                self.txt_results.tag_add("selected_row", f"{target_line}.0", f"{target_line}.end")
                self.txt_results.see(f"{target_line}.0")
            self.txt_results.config(state="disabled")

        if not jump:
            return

        if self.var_preview_compiled.get():
            self.var_preview_compiled.set(False)

        if not self.current_file_path or self.current_file_path != res.file_path:
            self.open_file(res.file_path)

        if (res.box_index == -1 or res.line_number == 0) and self.current_doc and self.current_doc.has_metadata():
            self.is_box0_active = True
            if self.var_continuous_view.get():
                self._update_views()
                self._focus_continuous_box(-1, move_cursor=True, char_offset=res.start_pos)
            else:
                self._update_views()
                if "Title" in res.speaker:
                    self.entry_box0_title.focus_set()
                    self.entry_box0_title.selection_range(res.start_pos, res.end_pos)
                elif "Subtitle" in res.speaker:
                    self.entry_box0_subtitle.focus_set()
                    self.entry_box0_subtitle.selection_range(res.start_pos, res.end_pos)
                else:
                    self.txt_box0_summary.focus_set()
                    self.txt_box0_summary.tag_remove("search_hit", "1.0", tk.END)
                    self.txt_box0_summary.tag_add(
                        "search_hit",
                        f"1.0 + {res.start_pos}c",
                        f"1.0 + {res.end_pos}c"
                    )
            return

        self.is_box0_active = False
        if res.box_index is not None and self.current_doc:
            self.current_box_idx = res.box_index
            if self.var_continuous_view.get():
                self._update_views()
                if res.match_in_speaker:
                    self._focus_continuous_box(res.box_index, move_cursor=True)
                    self.entry_speaker.focus_set()
                    self.entry_speaker.selection_range(res.start_pos, res.end_pos)
                else:
                    self._focus_continuous_box(
                        res.box_index,
                        move_cursor=True,
                        char_offset=res.start_pos,
                        explicit_span=(res.start_pos, res.end_pos),
                    )
            else:
                self._update_views()
                if res.match_in_speaker:
                    self.entry_speaker.focus_set()
                    self.entry_speaker.selection_range(res.start_pos, res.end_pos)
                else:
                    self._highlight_dialogue_matches((res.start_pos, res.end_pos))
                    self.txt_dialogue.focus_set()
        elif not self.current_doc and res.line_number > 0:
            self._update_views()
            target_widget = self.txt_continuous if self.var_continuous_view.get() else self.txt_dialogue
            target_widget.tag_remove("search_hit", "1.0", tk.END)
            s_idx = f"{res.line_number}.{res.start_pos}"
            e_idx = f"{res.line_number}.{res.end_pos}"
            target_widget.tag_add("search_hit", s_idx, e_idx)
            target_widget.see(s_idx)
            target_widget.focus_set()

    def on_clear_search(self) -> None:
        self._is_searching = False
        self.active_search_options = None
        self._reset_search_results_state()
        self.txt_dialogue.tag_remove("search_hit", "1.0", tk.END)
        self.txt_continuous.tag_remove("search_hit", "1.0", tk.END)
        self.lbl_results_title.config(text="Search Results (0 matches)")

    # -------------------------------------------------------------------------
    # Dialogs & Helpers
    # -------------------------------------------------------------------------
    def _sync_recent_files_menu(self) -> None:
        """Dynamically populate Recent Files submenu."""
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.delete(0, tk.END)
        recents = getattr(self, "recent_files", [])
        valid_recents = [p for p in recents if isinstance(p, Path) and p.exists()]
        if not valid_recents:
            self.recent_menu.add_command(label="(No recent files)", state="disabled")
            return
        for fp in valid_recents[:12]:
            self.recent_menu.add_command(
                label=f"{fp.name}  ({fp.parent})",
                command=lambda p=fp: self.open_file(p),
            )
        self.recent_menu.add_separator()
        self.recent_menu.add_command(
            label="Clear Recent Files",
            command=self._clear_recent_files,
        )

    def _clear_recent_files(self) -> None:
        self.recent_files = []
        self._save_user_prefs(silent=True)
        self.show_toast("Cleared recent files history")

    def on_open_file(self) -> None:
        init_dir = str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) and self.last_opened_dir.exists() else None
        raw_files = filedialog.askopenfilenames(
            initialdir=init_dir,
            title="Open Story Asset or Script",
            filetypes=[
                ("Priconne Assets & Scripts", "*.unity3d;*.asset;*.txt;*.json"),
                ("Unity3D Bundles", "*.unity3d;*.asset"),
                ("Text Scripts", "*.txt;*.json"),
                ("All Files", "*.*")
            ]
        )
        if not raw_files:
            return
        if isinstance(raw_files, str):
            files = [raw_files] if raw_files else []
        else:
            files = [f for f in raw_files if f]
        if not files:
            return

        opened_any = False
        last_success: Optional[Path] = None
        for f in files:
            try:
                p = Path(f).resolve()
                self.open_file(p, refresh_ui=False)
                if p in self.open_documents:
                    opened_any = True
                    last_success = p
            except Exception as e:
                self.logger.exception(f"Failed to open '{f}':", e)

        if opened_any and last_success is not None:
            self.last_opened_dir = last_success.parent
            self.open_file(last_success, refresh_ui=True)
            self._save_user_prefs(silent=True)

    def on_open_folder(self) -> None:
        """Open a folder from menu; prompts user to open all files or set search scope."""
        init_dir = str(self.selected_search_folder) if getattr(self, "selected_search_folder", None) and self.selected_search_folder.exists() else (
            str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) and self.last_opened_dir.exists() else None
        )
        f = filedialog.askdirectory(initialdir=init_dir, title="Open Folder (Story Files or Search Scope)")
        if f:
            self._process_opened_folder(Path(f), source_label="Open Folder")

    def _get_project_display_path(self) -> str:
        """Return the effective project directory path (BepInEx, MelonLoader, XUAT, etc.)."""
        p = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
        if p and Path(p).exists():
            return str(p)
        if getattr(self, "xuat_search_roots", None) and self.xuat_search_roots:
            first_root = self.xuat_search_roots[0]
            if first_root.exists():
                self.project_folder = first_root
                self.bepinex_project_folder = first_root
                return str(first_root)
        parent_dir = SCRIPT_DIR.parent
        self.project_folder = parent_dir
        self.bepinex_project_folder = parent_dir
        return str(parent_dir)

    def _on_folder_path_var_trace(self) -> None:
        """Synchronize project_folder or selected_search_folder when user edits folder_path_var."""
        if getattr(self, "_syncing_folder_path_var", False):
            return
        scope_v = getattr(self, "scope_var", None)
        if not scope_v:
            return
        s = scope_v.get()
        val = self.folder_path_var.get().strip()
        if s == "project":
            if val:
                p = Path(val)
                self._set_project_folder(p)
        elif s == "folder":
            if val:
                self.selected_search_folder = Path(val)

    def _sync_scope_widgets(self) -> None:
        """Update folder/project path entry and browse button based on scope selection."""
        if not (hasattr(self, "folder_path_entry") and hasattr(self, "btn_browse_search_folder")):
            return
        scope = self.scope_var.get()
        self._syncing_folder_path_var = True
        try:
            if scope == "folder":
                if not self.btn_browse_search_folder.winfo_manager():
                    self.btn_browse_search_folder.pack(side="left", padx=(0, 2))
                if not self.folder_path_entry.winfo_manager():
                    self.folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
                self.folder_path_entry.config(state="normal")
                self.btn_browse_search_folder.config(state="normal")
                if getattr(self, "selected_search_folder", None):
                    self.folder_path_var.set(str(self.selected_search_folder))
                else:
                    self.folder_path_var.set("")
            elif scope == "project":
                if not self.btn_browse_search_folder.winfo_manager():
                    self.btn_browse_search_folder.pack(side="left", padx=(0, 2))
                if not self.folder_path_entry.winfo_manager():
                    self.folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
                self.folder_path_entry.config(state="normal")
                self.btn_browse_search_folder.config(state="normal")
                self.folder_path_var.set(self._get_project_display_path())
            else:  # "current"
                self.btn_browse_search_folder.pack_forget()
                self.folder_path_entry.pack_forget()
                self.folder_path_entry.config(state="readonly")
                self.btn_browse_search_folder.config(state="disabled")
        finally:
            self._syncing_folder_path_var = False

    def on_browse_scope_path(self) -> None:
        """Browse button handler for the active search scope ([...] on left of directory entry)."""
        scope = self.scope_var.get()
        if scope == "project":
            self.on_browse_project_folder()
        elif scope == "folder":
            self.on_open_folder()

    def on_browse_project_folder(self) -> None:
        """Browse and configure the Project Root / Mod Translation Folder."""
        init_dir = self._get_project_display_path()
        d = filedialog.askdirectory(initialdir=init_dir, title="Select Project Root / Mod Folder (BepInEx, MelonLoader, etc.)")
        if d:
            p = Path(d)
            self._set_project_folder(p)
            self.folder_path_var.set(str(p))
            self._save_user_prefs(silent=True)
            self.lbl_status.config(text=f"Project folder set to: {p}")
            self.show_toast(f"Project folder set to: {p.name}")

    # -------------------------------------------------------------------------
    # Search & Replace Actions (Find, Replace, Replace All, Multi-File Confirmation)
    # -------------------------------------------------------------------------
    def on_show_find(self) -> None:
        if not getattr(self, "_search_bar_visible", False):
            # search_frame and h_paned are both direct children of self (root)
            self.search_frame.pack(before=self.h_paned, fill="x", padx=8, pady=(6, 4))
            self._search_bar_visible = True
        self._sync_scope_widgets()
        if getattr(self, "_replace_row_visible", False):
            self._hide_replace_row()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def on_show_find_in_files(self) -> None:
        self.scope_var.set("project")
        self.on_show_find()

    def on_show_replace(self) -> None:
        if not getattr(self, "_search_bar_visible", False):
            self.search_frame.pack(before=self.h_paned, fill="x", padx=8, pady=(6, 4))
            self._search_bar_visible = True
        self._sync_scope_widgets()
        if not getattr(self, "_replace_row_visible", False):
            self._show_replace_row()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def _hide_search_bar(self) -> None:
        if hasattr(self, "search_frame"):
            self.search_frame.pack_forget()
            self._search_bar_visible = False
            target = self.txt_continuous if self.var_continuous_view.get() else self.txt_dialogue
            target.focus_set()

    def _apply_compiled_replacement(
        self,
        text: str,
        matcher: Callable[[str], List[Any]],
        replacement: str,
        is_regex: bool = False,
        ignore_ws: bool = False,
        count: int = 0,
        regex_pattern: Optional[re.Pattern] = None,
    ) -> Tuple[str, int]:
        """Apply replacement across text honoring Match Case, Regex, and Ignore Whitespace (BUG-24 / QW-R06).

        Replaces non-overlapping spans returned by matcher in reverse order to preserve indexing.
        When is_regex is True, supports group backreferences via regex substitution.
        Returns (new_text, occurrences_replaced).
        """
        if not text:
            return text, 0

        if is_regex:
            rx = regex_pattern
            if rx is None:
                if hasattr(matcher, "__closure__") and matcher.__closure__:
                    for cell in matcher.__closure__:
                        if isinstance(cell.cell_contents, re.Pattern):
                            rx = cell.cell_contents
                            break
            if rx is None:
                q = getattr(self, "search_var", None).get() if getattr(self, "search_var", None) else ""
                flags = 0 if getattr(self, "var_case", None) and self.var_case.get() else re.IGNORECASE
                rx = re.compile(q, flags)
            new_text, num = rx.subn(replacement, text, count=count)
            return new_text, num

        matches = matcher(text)
        if not matches:
            return text, 0

        if count > 0:
            matches = matches[:count]

        res = text
        for item in reversed(matches):
            start, end = item[0], item[1]
            res = res[:start] + replacement + res[end:]
        return res, len(matches)

    def _confirm_closed_files_for_op(self, op: Any, is_undo: bool = True) -> bool:
        """Prompt before modifying closed files on disk during Undo/Redo (BUG-24 / AGENTS.md §16)."""
        if not op or not hasattr(op, "deltas"):
            return True

        closed_paths: List[Path] = []
        all_paths: List[Path] = []
        for delta in op.deltas:
            if isinstance(delta, BulkFileDelta):
                for item in delta.per_file:
                    fp = Path(item[0]).resolve()
                    all_paths.append(fp)
                    if self._find_open_doc_key(fp) is None:
                        closed_paths.append(fp)

        if not closed_paths:
            return True

        action = "Undo" if is_undo else "Redo"
        file_lines = []
        for p in all_paths:
            status = " (closed - will touch disk)" if p in closed_paths else " (open tab)"
            file_lines.append(f"  • {p.name}{status}")

        msg = (
            f"{action} across multiple files:\n\n"
            f"Operation: {getattr(op, 'label', 'Bulk Operation')}\n\n"
            f"The following {len(all_paths)} file(s) will be modified on disk,\n"
            f"including {len(closed_paths)} file(s) not currently open:\n\n"
            + "\n".join(file_lines)
            + f"\n\nProceed with {action} across these files?"
        )
        ans = messagebox.askyesno(
            f"Confirm Multi-File {action}",
            msg,
            default=messagebox.NO,
            icon=messagebox.WARNING,
        )
        return bool(ans)

    def on_replace_next(self) -> None:
        """Find and replace the next occurrence in the active file."""
        find_text = self.search_var.get()
        replace_text = self.replace_var.get()
        if not find_text:
            return

        if not self.current_file_path:
            messagebox.showinfo("Replace", "No active file open to replace in.")
            return

        match_case = bool(getattr(self, "var_case", None) and self.var_case.get())
        use_regex = bool(getattr(self, "var_regex", None) and self.var_regex.get())
        ignore_ws = bool(getattr(self, "var_ignore_ws", None) and self.var_ignore_ws.get()) if getattr(self, "var_ignore_ws", None) is not None else False

        try:
            opts = SearchOptions(
                query=find_text,
                match_case=match_case,
                use_regex=use_regex,
                ignore_whitespace=ignore_ws,
            )
            search_engine = getattr(self, "search_engine", None)
            compile_fn = search_engine._compile_matcher if search_engine else ProjectSearchEngine._compile_matcher
            matcher = compile_fn(opts)
        except Exception as e:
            self.set_status(f"Invalid search pattern: {e}", is_error=True)
            messagebox.showerror("Search Error", f"Invalid search pattern:\n{e}")
            return

        if self.current_doc and self.current_doc.boxes:
            box = self.current_doc.boxes[self.current_box_idx]
            matches = matcher(box.clean_text)
            if matches:
                if self.is_box_locked(self.current_box_idx):
                    self.show_toast(f"🔒 Box {self.current_box_idx + 1} is locked against edits.")
                else:
                    old_sp = box.speaker
                    old_tx = box.clean_text
                    box_uid = box.uid
                    old_segs = [s.text for s in box.segs] if len(box.segs) > 1 else None
                    new_tx, _ = self._apply_compiled_replacement(
                        box.clean_text, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=1
                    )
                    try:
                        self.current_doc.inject_box(self.current_box_idx, None, new_tx)
                    except Exception as e:
                        self.logger.exception(f"Failed to replace in box {self.current_box_idx}:", e)
                        self.set_status(f"Error replacing in box #{self.current_box_idx + 1}: {e}", is_error=True)
                        return

                    new_segs = None
                    if old_segs is not None:
                        refreshed_box = next((b for b in self.current_doc.boxes if b.segs and b.segs[0].record.uid == box_uid), None)
                        if refreshed_box:
                            new_segs = [s.text for s in refreshed_box.segs]

                    self.undo_journal.record(
                        BoxEditDelta(
                            box_index=self.current_box_idx,
                            old_speaker=old_sp,
                            new_speaker=old_sp,
                            old_text=old_tx,
                            new_text=new_tx,
                            file_path=str(self.current_file_path),
                            box_uid=box.uid,
                            source="replace",
                            old_seg_texts=old_segs,
                            new_seg_texts=new_segs,
                        ),
                        label=f"Replace in box #{self.current_box_idx + 1}"
                    )
                    self._modified_boxes.add(self.current_box_idx)
                    self._mark_document_dirty(self.current_file_path)
                    self._dirty_state_changed()
                    self._update_views()
                    self.lbl_status.config(text=f"Replaced 1 occurrence in Box #{self.current_box_idx + 1}")
                    return

            total = len(self.current_doc.boxes)
            for i in range(1, total):
                next_idx = (self.current_box_idx + i) % total
                if self.is_box_locked(next_idx):
                    continue
                if matcher(self.current_doc.boxes[next_idx].clean_text):
                    self.current_box_idx = next_idx
                    self._update_views()
                    self.lbl_status.config(text=f"Found match in Box #{next_idx + 1}. Press Replace again to replace.")
                    return
            messagebox.showinfo("Replace", f"No more occurrences of '{find_text}' found.")
        elif not self.current_doc and self.current_file_path:
            cur_tx = self._plain_text_content
            matches = matcher(cur_tx)
            if matches:
                new_tx, _ = self._apply_compiled_replacement(
                    cur_tx, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=1
                )
                self.undo_journal.record(
                    PlainTextDelta(
                        file_path=str(self.current_file_path),
                        old_content=cur_tx,
                        new_content=new_tx,
                    ),
                    label=f"Replace in {self.current_file_path.name}"
                )
                self._plain_text_content = new_tx
                matched_k = self._find_open_doc_key(self.current_file_path)
                if matched_k and matched_k in self.open_documents:
                    self.open_documents[matched_k]["plain_text"] = new_tx
                self._mark_document_dirty(self.current_file_path)
                self._dirty_state_changed()
                self._update_views()
                self.lbl_status.config(text=f"Replaced 1 occurrence in {self.current_file_path.name}")
            else:
                messagebox.showinfo("Replace", f"'{find_text}' not found in current file.")

    def on_replace_all(self) -> None:
        """Replace all occurrences in current file or across project/folder (BUG-24)."""
        find_text = self.search_var.get()
        replace_text = self.replace_var.get()
        if not find_text:
            return

        match_case = bool(getattr(self, "var_case", None) and self.var_case.get())
        use_regex = bool(getattr(self, "var_regex", None) and self.var_regex.get())
        ignore_ws = bool(getattr(self, "var_ignore_ws", None) and self.var_ignore_ws.get()) if getattr(self, "var_ignore_ws", None) is not None else False

        try:
            opts = SearchOptions(
                query=find_text,
                match_case=match_case,
                use_regex=use_regex,
                ignore_whitespace=ignore_ws,
            )
            search_engine = getattr(self, "search_engine", None)
            compile_fn = search_engine._compile_matcher if search_engine else ProjectSearchEngine._compile_matcher
            matcher = compile_fn(opts)
        except Exception as e:
            self.set_status(f"Invalid search pattern: {e}", is_error=True)
            messagebox.showerror("Search Error", f"Invalid search pattern:\n{e}")
            return

        scope = self.scope_var.get()
        if scope == "current":
            if not self.current_file_path:
                messagebox.showinfo("Replace All", "No active file open.")
                return
            if self.current_doc and self.current_doc.boxes:
                count = 0
                skipped_locked = 0
                self.undo_journal.begin_batch(f"Replace All '{find_text}' in {self.current_file_path.name}")
                for idx, box in enumerate(self.current_doc.boxes):
                    matches = matcher(box.clean_text)
                    if matches:
                        if self.is_box_locked(idx):
                            skipped_locked += 1
                            continue
                        old_sp = box.speaker
                        old_tx = box.clean_text
                        new_tx, _ = self._apply_compiled_replacement(
                            box.clean_text, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=0
                        )
                        self.undo_journal.record(
                            BoxEditDelta(
                                box_index=idx,
                                old_speaker=old_sp,
                                new_speaker=old_sp,
                                old_text=old_tx,
                                new_text=new_tx,
                                file_path=str(self.current_file_path),
                                box_uid=box.uid,
                                source="replace",
                            )
                        )
                        self.current_doc.inject_box(idx, None, new_tx)
                        self._modified_boxes.add(idx)
                        count += 1
                self.undo_journal.end_batch()
                if count > 0:
                    self._mark_document_dirty(self.current_file_path)
                    self._dirty_state_changed()
                    self._update_views()
                    msg = f"Replaced in {count} box(es) in {self.current_file_path.name}"
                    if skipped_locked > 0:
                        msg += f" ({skipped_locked} locked boxes preserved)"
                    self.lbl_status.config(text=msg)
                    self.show_toast(f"✓ {msg}")
                    self.logger.info("Search", f"Replaced all '{find_text}' -> '{replace_text}' in {count} boxes of {self.current_file_path.name}")
                elif skipped_locked > 0:
                    self.lbl_status.config(text=f"All matching boxes ({skipped_locked}) are locked.")
                    messagebox.showinfo("Replace All", f"Matches were found in {skipped_locked} box(es), but they are all protected by Translation Lock.")
                else:
                    messagebox.showinfo("Replace All", f"'{find_text}' not found in current file.")
            elif not self.current_doc and self.current_file_path:
                cur_tx = self._plain_text_content
                matches = matcher(cur_tx)
                if matches:
                    occurrences = len(matches)
                    new_tx, _ = self._apply_compiled_replacement(
                        cur_tx, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=0
                    )
                    self.undo_journal.record(
                        PlainTextDelta(
                            file_path=str(self.current_file_path),
                            old_content=cur_tx,
                            new_content=new_tx,
                        ),
                        label=f"Replace All in {self.current_file_path.name}"
                    )
                    self._plain_text_content = new_tx
                    matched_k = self._find_open_doc_key(self.current_file_path)
                    if matched_k and matched_k in self.open_documents:
                        self.open_documents[matched_k]["plain_text"] = new_tx
                    self._mark_document_dirty(self.current_file_path)
                    self._dirty_state_changed()
                    self._update_views()
                    self.lbl_status.config(text=f"Replaced {occurrences} occurrence(s) in {self.current_file_path.name}")
                else:
                    messagebox.showinfo("Replace All", f"'{find_text}' not found in current file.")
        else:
            # Multi-file Replace All
            target_roots: List[Path] = []
            if scope == "folder":
                fp = self.folder_path_var.get().strip() or (str(self.selected_search_folder) if self.selected_search_folder else "")
                if fp and Path(fp).exists():
                    target_roots = [Path(fp)]
                else:
                    messagebox.showerror("Replace All", "Please select a valid folder for Folder scope.")
                    return
            else:
                target_roots = list(self.xuat_search_roots)
                active_proj = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
                if active_proj and active_proj.exists():
                    text_dir = active_proj / "Text"
                    root = text_dir if text_dir.exists() else active_proj
                    if root not in target_roots:
                        target_roots.insert(0, root)

            inc_bdl = bool(getattr(self, "var_inc_bundles", None) and self.var_inc_bundles.get())
            inc_txt = bool(getattr(self, "var_inc_text", None) and self.var_inc_text.get()) if getattr(self, "var_inc_text", None) is not None else True

            seen_paths: Set[Path] = set()
            candidate_files: List[Path] = []
            for root in target_roots:
                root_p = Path(root).resolve()
                if root_p.is_file():
                    if root_p not in seen_paths:
                        seen_paths.add(root_p)
                        candidate_files.append(root_p)
                elif root_p.is_dir():
                    if inc_bdl:
                        for pat in ("*.unity3d", "*.asset"):
                            for f in root_p.rglob(pat):
                                fp = f.resolve()
                                if fp not in seen_paths and fp.is_file():
                                    seen_paths.add(fp)
                                    candidate_files.append(fp)
                    if inc_txt:
                        for f in root_p.rglob("*.txt"):
                            fp = f.resolve()
                            if fp not in seen_paths and fp.is_file():
                                seen_paths.add(fp)
                                candidate_files.append(fp)

            matching_files: Dict[Path, int] = {}
            total_matches = 0

            for cf in candidate_files:
                try:
                    if cf.suffix.lower() in (".unity3d", ".asset"):
                        bundle_env = None
                        try:
                            b_doc, bundle_env, _, _ = load_bundle_story(cf)
                            open_k = self._find_open_doc_key(cf)
                            locked_uids: Set[int] = set()
                            if open_k and open_k in self.open_documents:
                                locked_uids = set(self.open_documents[open_k].get("locked_box_uids", set()))
                            elif open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                locked_uids = set(getattr(self, "_locked_box_uids", set()))

                            c = 0
                            for box in b_doc.boxes:
                                b_uid = _get_box_uid(box)
                                if b_uid is not None and b_uid in locked_uids:
                                    continue
                                c += len(matcher(box.clean_text))
                            if c > 0:
                                matching_files[cf] = c
                                total_matches += c
                        finally:
                            if bundle_env is not None:
                                dispose_unity_env(bundle_env)
                    else:
                        decoded = read_text_file_strictly(cf)
                        c = len(matcher(decoded.text))
                        if c > 0:
                            matching_files[cf] = c
                            total_matches += c
                except Exception:
                    pass

            if not matching_files:
                messagebox.showinfo("Replace All", f"No matches for '{find_text}' found across {len(candidate_files)} files.")
                return

            # Refuse/prompt before overwriting dirty open documents (BUG-24)
            dirty_open: List[Path] = []
            for fp in matching_files:
                open_k = self._find_open_doc_key(fp)
                if open_k and open_k in self.open_documents:
                    is_active_dirty = (open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None) and getattr(self, "is_dirty", False))
                    if self.open_documents[open_k].get("dirty", False) or is_active_dirty:
                        dirty_open.append(open_k)

            if dirty_open:
                dirty_list = "\n".join(f"  • {p.name} ({p})" for p in dirty_open)
                ans = messagebox.askyesno(
                    "Unsaved Changes in Open Files",
                    f"The following {len(dirty_open)} open document(s) have unsaved changes that would be overwritten by Replace All:\n\n"
                    f"{dirty_list}\n\n"
                    f"Proceed and overwrite these unsaved changes?",
                    default=messagebox.NO,
                    icon=messagebox.WARNING,
                )
                if not ans:
                    self.lbl_status.config(text="Replace All cancelled: open documents have unsaved changes.")
                    return

            confirm_msg = (
                f"Replace All across multiple files:\n\n"
                f"Search query: '{find_text}'\n"
                f"Replacement:  '{replace_text}'\n\n"
                f"Found ~{total_matches} match(es) across {len(matching_files)} file(s).\n\n"
                f"Proceed with replacement?"
            )
            ans = messagebox.askyesno(
                "Confirm Multi-File Replace All",
                confirm_msg,
                default=messagebox.NO,
                icon=messagebox.WARNING
            )
            if not ans:
                return

            replaced_files_count = 0
            per_file_deltas: List[Any] = []

            for fpath in matching_files:
                try:
                    if fpath.suffix.lower() in (".unity3d", ".asset"):
                        bundle_env = None
                        try:
                            doc, bundle_env, obj, _ = load_bundle_story(fpath)
                            open_k = self._find_open_doc_key(fpath)
                            locked_uids = set()
                            if open_k and open_k in self.open_documents:
                                locked_uids = set(self.open_documents[open_k].get("locked_box_uids", set()))
                            elif open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                locked_uids = set(getattr(self, "_locked_box_uids", set()))

                            modified = False
                            for idx, box in enumerate(doc.boxes):
                                b_uid = _get_box_uid(box)
                                if b_uid is not None and b_uid in locked_uids:
                                    continue
                                if matcher(box.clean_text):
                                    new_box_tx, _ = self._apply_compiled_replacement(
                                        box.clean_text, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=0
                                    )
                                    doc.inject_box(idx, None, new_box_tx)
                                    modified = True
                            if modified:
                                bak_dir = self._get_backup_dir()
                                orig_bak_path = make_collision_resistant_backup_path(fpath, bak_dir, tag="orig")
                                shutil.copy2(fpath, orig_bak_path)

                                save_bundle_story(bundle_env, obj, doc, fpath, backup_dir=None)

                                mod_bak_path = make_collision_resistant_backup_path(fpath, bak_dir, tag="mod")
                                shutil.copy2(fpath, mod_bak_path)

                                per_file_deltas.append((str(fpath), str(orig_bak_path), str(mod_bak_path), True))
                                replaced_files_count += 1
                        finally:
                            if bundle_env is not None:
                                dispose_unity_env(bundle_env)
                    else:
                        decoded = read_text_file_strictly(fpath)
                        old_txt = decoded.text
                        if matcher(old_txt):
                            new_txt, _ = self._apply_compiled_replacement(
                                old_txt, matcher, replace_text, is_regex=use_regex, ignore_ws=ignore_ws, count=0
                            )
                            bak_dir = self._get_backup_dir()
                            bak_path = make_collision_resistant_backup_path(fpath, bak_dir, tag="bak")
                            shutil.copy2(fpath, bak_path)
                            if decoded.has_bom or (decoded.newline and decoded.newline != "\n"):
                                write_atomic_utf8(
                                    fpath,
                                    new_txt,
                                    encoding=decoded.encoding,
                                    has_bom=decoded.has_bom,
                                    newline=decoded.newline,
                                )
                            else:
                                write_atomic_utf8(fpath, new_txt, encoding=decoded.encoding)
                            per_file_deltas.append((str(fpath), old_txt, new_txt))
                            replaced_files_count += 1
                except Exception as ex:
                    self.logger.error("Search", f"Failed replacing in {fpath}: {ex}")

            # Refresh ALL affected open document caches (including inactive tabs) & do NOT mark disk-saved files dirty
            for item in per_file_deltas:
                fpath_str = item[0]
                fp = Path(fpath_str).resolve()
                open_k = self._find_open_doc_key(fp)
                if open_k and open_k in self.open_documents:
                    entry = self.open_documents[open_k]
                    is_bdl = len(item) >= 4 and bool(item[3])
                    if is_bdl:
                        try:
                            b_doc, b_env, b_obj, _ = load_bundle_story(fp)
                            old_env = entry.get("env")
                            if old_env is not None and old_env is not b_env:
                                dispose_unity_env(old_env)
                            entry["doc"] = b_doc
                            entry["env"] = b_env
                            entry["obj"] = b_obj
                            entry["dirty"] = False
                            self._record_saved_checkpoint(open_k, b_doc)
                            if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                self.current_doc = b_doc
                                self.current_unity_env = b_env
                                self.current_text_obj = b_obj
                                self.is_dirty = False
                        except Exception as ex_refresh:
                            self.logger.error("Search", f"Failed refreshing bundle cache for {fp}: {ex_refresh}")
                    else:
                        new_txt = item[2]
                        entry["plain_text"] = new_txt
                        entry["dirty"] = False
                        self._record_saved_checkpoint(open_k, None, plain_text=new_txt)
                        if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                            self._plain_text_content = new_txt
                            self.is_dirty = False

            if per_file_deltas:
                self.undo_journal.record(
                    BulkFileDelta(
                        description=f"Replace '{find_text}' -> '{replace_text}' in {len(per_file_deltas)} files",
                        per_file=per_file_deltas,
                    )
                )

            active_k = self._find_open_doc_key(self.current_file_path) if self.current_file_path else None
            if active_k and any(Path(it[0]).resolve() == active_k for it in per_file_deltas):
                self._update_views()
                self._dirty_state_changed()

            self.lbl_status.config(text=f"Bulk Replace Complete: Updated {replaced_files_count} file(s).")
            self.logger.info("Search", f"Bulk replaced '{find_text}' -> '{replace_text}' in {replaced_files_count} file(s)")
            messagebox.showinfo("Replace All Complete", f"Successfully replaced '{find_text}' across {replaced_files_count} file(s).")

    # -------------------------------------------------------------------------
    # Undo / Redo Actions (#3A)
    # -------------------------------------------------------------------------
    def on_undo(self) -> None:
        """Undo the most recent operation from MasterUndoJournal (Rule 13, Part B.6)."""
        self._commit_widget_edit()
        cur_fp = str(self.current_file_path) if self.current_file_path else None

        # Inspect next undo op before popping to avoid corrupting undo/redo stack on cancellation (BUG-24)
        with self.undo_journal._lock:
            state = self.undo_journal._get_state(cur_fp)
            next_op = state.undo_stack[-1] if state.undo_stack else None

        if next_op and not self._confirm_closed_files_for_op(next_op, is_undo=True):
            self.lbl_status.config(text="Undo cancelled.")
            return

        op = self.undo_journal.pop_undo(cur_fp)
        if not op:
            self.lbl_status.config(text="Nothing to undo.")
            return
        for delta in reversed(op.deltas):
            self._apply_delta(delta, reverse=True, refresh_ui=False)
        self._update_views()
        self._sync_clean_view_to_current_box()
        self._evaluate_checkpoints_for_op(op)
        self._dirty_state_changed()
        self._sync_edit_menu_states()
        self.lbl_status.config(text=f"Undid: {op.label}")
        self.logger.info("Edit", f"Undid operation: {op.label}")

    def on_redo(self) -> None:
        """Redo the most recent undone operation from MasterUndoJournal (Rule 13, Part B.6)."""
        self._commit_widget_edit()
        cur_fp = str(self.current_file_path) if self.current_file_path else None

        # Inspect next redo op before popping to avoid corrupting undo/redo stack on cancellation (BUG-24)
        with self.undo_journal._lock:
            state = self.undo_journal._get_state(cur_fp)
            next_op = state.redo_stack[-1] if state.redo_stack else None

        if next_op and not self._confirm_closed_files_for_op(next_op, is_undo=False):
            self.lbl_status.config(text="Redo cancelled.")
            return

        op = self.undo_journal.pop_redo(cur_fp)
        if not op:
            self.lbl_status.config(text="Nothing to redo.")
            return
        for delta in op.deltas:
            self._apply_delta(delta, reverse=False, refresh_ui=False)
        self._update_views()
        self._sync_clean_view_to_current_box()
        self._evaluate_checkpoints_for_op(op)
        self._dirty_state_changed()
        self._sync_edit_menu_states()
        self.lbl_status.config(text=f"Redid: {op.label}")
        self.logger.info("Edit", f"Redid operation: {op.label}")

    @staticmethod
    def _restore_bundle_atomic(src_bak_path: Union[str, Path], dst_path: Path) -> None:
        """Atomically restore a binary bundle file from a backup snapshot (S9b)."""
        src_p = Path(src_bak_path)
        if not src_p.is_file():
            raise FileNotFoundError(f"Bundle backup file not found: {src_p}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dst_path.with_name(f"{dst_path.name}.{os.getpid()}_{time.time_ns()}.tmp")
        shutil.copy2(src_p, tmp_path)
        retries = 5
        for attempt in range(retries):
            try:
                os.replace(tmp_path, dst_path)
                break
            except PermissionError:
                if attempt == retries - 1:
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass
                    raise
                time.sleep(0.05 * (attempt + 1))
            except Exception:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
                raise

    def _apply_delta(self, delta: Any, reverse: bool = False, refresh_ui: bool = True) -> None:
        """Apply a recorded delta forwards or backwards, preserving cursor position."""
        prev_caret = None
        try:
            target_w = self._get_active_text_widget()
            if target_w and target_w.winfo_exists():
                prev_caret = target_w.index(tk.INSERT)
        except Exception:
            pass

        if isinstance(delta, BoxEditDelta):
            target_sp = delta.old_speaker if reverse else delta.new_speaker
            target_tx = delta.old_text if reverse else delta.new_text
            target_segs = delta.old_seg_texts if reverse else delta.new_seg_texts
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            if self.current_doc:
                target_idx = delta.box_index
                if delta.box_uid is not None:
                    found_idx = next(
                        (i for i, b in enumerate(self.current_doc.boxes) if b.segs and b.segs[0].record.uid == delta.box_uid),
                        None
                    )
                    if found_idx is not None:
                        target_idx = found_idx
                if 0 <= target_idx < len(self.current_doc.boxes):
                    self.current_doc.inject_box(target_idx, target_sp, target_tx, seg_texts=target_segs)
                    self.current_box_idx = target_idx
                    self._modified_boxes.add(target_idx)
                    self._mark_document_dirty(target_file or self.current_file_path)
                    if refresh_ui:
                        self._update_views()
        elif isinstance(delta, MetadataDelta):
            target_title = delta.old_title if reverse else delta.new_title
            target_sub = delta.old_subtitle if reverse else delta.new_subtitle
            target_summary = delta.old_summary if reverse else delta.new_summary
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            if self.current_doc:
                self.current_doc.set_metadata(title=target_title, subtitle=target_sub, summary=target_summary)
                self.is_box0_active = True
                self.current_box_idx = 0
                self._mark_document_dirty(target_file or self.current_file_path)
                if refresh_ui:
                    self._update_views()
        elif isinstance(delta, DocumentRecordsDelta):
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            self._exit_raw_edit_mode(refresh=False)
            if self.current_doc:
                target_recs = delta.old_records if reverse else delta.new_records
                target_removed = delta.old_removed_records if reverse else delta.new_removed_records
                self.current_doc.records = copy.deepcopy(target_recs)
                self.current_doc.removed_records = set(target_removed)
                self.current_doc._rebuild_boxes()

                self._locked_box_uids = set(delta.old_locked_uids if reverse else delta.new_locked_uids)
                self._original_jp_by_uid = dict(delta.old_jp_by_uid if reverse else delta.new_jp_by_uid)
                if hasattr(self, "sync_manager") and self.sync_manager is not None:
                    for b_uid, jp_txt in self._original_jp_by_uid.items():
                        self.sync_manager.register_jp_key(b_uid, jp_txt)
                target_p = target_file or self.current_file_path
                if target_p:
                    cur_p = Path(target_p).resolve()
                    if cur_p in self.open_documents:
                        self.open_documents[cur_p]["locked_box_uids"] = set(self._locked_box_uids)
                        self.open_documents[cur_p]["original_jp_by_uid"] = dict(self._original_jp_by_uid)
                self._resync_box_indices_from_uids()

                target_box_idx = delta.old_box_idx if reverse else delta.new_box_idx
                if self.current_doc.boxes:
                    self.current_box_idx = max(0, min(target_box_idx, len(self.current_doc.boxes) - 1))
                else:
                    self.current_box_idx = 0
                target_is_box0 = delta.old_is_box0 if reverse else delta.new_is_box0
                self.is_box0_active = bool(target_is_box0 and self.current_doc.has_metadata())
                self._mark_document_dirty(target_p)
                if refresh_ui:
                    self._update_views()
        elif isinstance(delta, BoxSnapshotReplaceDelta):
            target_snap = delta.old_snapshot if reverse else delta.new_snapshot
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            if self.current_doc and 0 <= delta.box_index < len(self.current_doc.boxes):
                old_uid = self.current_doc.boxes[delta.box_index].uid
                self.current_doc.replace_box(delta.box_index, target_snap)
                new_uid = self.current_doc.boxes[delta.box_index].uid
                if hasattr(self, "_original_jp_by_uid") and old_uid in self._original_jp_by_uid:
                    jp_val = self._original_jp_by_uid.pop(old_uid)
                    self._original_jp_by_uid[new_uid] = jp_val
                    if hasattr(self, "sync_manager") and self.sync_manager is not None:
                        self.sync_manager.register_jp_key(new_uid, jp_val)
                if hasattr(self, "_modified_box_uids"):
                    self._modified_box_uids.add(new_uid)
                self.is_box0_active = False
                self.current_box_idx = delta.box_index
                self._resync_box_indices_from_uids()
                self._mark_document_dirty(target_file or self.current_file_path)
                if refresh_ui:
                    self._update_views()
        elif isinstance(delta, BoxStructuralDelta):
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            if self.current_doc:
                is_insert = (delta.op_type == "insert") if not reverse else (delta.op_type != "insert")
                indices = getattr(delta, "indices", None)
                if is_insert:
                    if indices is not None and len(indices) == len(delta.snapshots):
                        for idx, snap in zip(indices, delta.snapshots):
                            self.current_doc.insert_box(idx, snap)
                        self.current_box_idx = indices[0] if indices else delta.box_index
                    else:
                        for offset, snap in enumerate(delta.snapshots):
                            self.current_doc.insert_box(delta.box_index + offset, snap)
                        self.current_box_idx = delta.box_index
                else:
                    if indices is not None:
                        delete_indices = list(indices)
                    else:
                        delete_indices = list(range(delta.box_index, delta.box_index + len(delta.snapshots)))
                    self.current_doc.delete_boxes(delete_indices)
                    target_box = indices[0] if indices else delta.box_index
                    self.current_box_idx = max(0, min(target_box, len(self.current_doc.boxes) - 1))
                self._resync_box_indices_from_uids()
                self._mark_document_dirty(target_file or self.current_file_path)
                if refresh_ui:
                    self._update_views()
                    self._sync_clean_view_to_current_box()
                    self._dirty_state_changed()
        elif isinstance(delta, PlainTextDelta):
            target_tx = delta.old_content if reverse else delta.new_content
            target_file = Path(delta.file_path) if delta.file_path else None
            if target_file and target_file != self.current_file_path:
                self.open_file(target_file)
            self._plain_text_content = target_tx
            target_p = target_file or self.current_file_path
            if target_p:
                p_res = Path(target_p).resolve()
                if p_res in self.open_documents:
                    self.open_documents[p_res]["plain_text"] = target_tx
            self._mark_document_dirty(target_p)
            if refresh_ui:
                self._update_views()
        elif isinstance(delta, BulkFileDelta):
            applied_files: List[Tuple[Path, bool, Any, Optional[str], bool, Optional[str]]] = []
            active_k = self._find_open_doc_key(self.current_file_path) if self.current_file_path else None
            active_updated = False
            try:
                for item in delta.per_file:
                    is_bundle = len(item) >= 4 and bool(item[3])
                    fpath_str = item[0]
                    fp = Path(fpath_str).resolve()
                    if is_bundle:
                        orig_bak_str = item[1]
                        mod_bak_str = item[2]
                        src_bak = orig_bak_str if reverse else mod_bak_str
                        prev_bak = mod_bak_str if reverse else orig_bak_str
                        self._restore_bundle_atomic(src_bak, fp)
                        applied_files.append((fp, True, prev_bak, None, False, None))

                        # S9b & S09 & S01 BONUS-03: Synchronize in-memory cache using canonical keys 'env' and 'obj'
                        open_k = self._find_open_doc_key(fp)
                        if open_k and open_k in self.open_documents:
                            try:
                                b_doc, b_env, b_obj, _ = load_bundle_story(fp)
                                entry = self.open_documents[open_k]
                                old_doc = entry.get("doc")
                                old_env = entry.get("env")
                                old_jp_uids = (
                                    entry.get("original_jp_by_uid", {}).keys()
                                    if isinstance(entry.get("original_jp_by_uid"), dict)
                                    else ()
                                )
                                if hasattr(self, "_prune_document_caches"):
                                    self._prune_document_caches(open_k, old_doc, extra_uids=old_jp_uids)
                                if old_env is not None and old_env is not b_env:
                                    dispose_unity_env(old_env)
                                new_jp_by_uid = (
                                    {_get_box_uid(b): b.clean_text for b in b_doc.boxes if _get_box_uid(b) is not None}
                                    if b_doc and b_doc.boxes
                                    else {}
                                )
                                if hasattr(self, "sync_manager") and self.sync_manager is not None:
                                    for b_uid, jp_txt in new_jp_by_uid.items():
                                        self.sync_manager.register_jp_key(b_uid, jp_txt)
                                entry["doc"] = b_doc
                                entry["env"] = b_env
                                entry["obj"] = b_obj
                                entry["dirty"] = False
                                entry["boxes_count"] = len(b_doc.boxes)
                                entry["original_jp_by_uid"] = dict(new_jp_by_uid)
                                entry["modified_box_uids"] = set()
                                if b_doc.boxes:
                                    entry["current_box_idx"] = max(0, min(int(entry.get("current_box_idx", 0)), len(b_doc.boxes) - 1))
                                else:
                                    entry["current_box_idx"] = 0
                                    entry["is_box0_active"] = False
                                self._record_saved_checkpoint(open_k, b_doc)
                                if open_k == active_k:
                                    self.current_doc = b_doc
                                    self.current_unity_env = b_env
                                    self.current_text_obj = b_obj
                                    self.is_bundle_file = True
                                    self._plain_text_content = ""
                                    self.is_dirty = False
                                    self._original_jp_by_uid = dict(new_jp_by_uid)
                                    self._modified_box_uids = set()
                                    self._modified_boxes = set()
                                    self.current_box_idx = entry["current_box_idx"]
                                    self.is_box0_active = bool(entry.get("is_box0_active", False) and b_doc.has_metadata())
                                    if hasattr(self, "_resync_box_indices_from_uids"):
                                        self._resync_box_indices_from_uids()
                                    active_updated = True
                            except Exception as ex_load:
                                self.logger.error("File I/O", f"Failed reloading bundle cache for {fp}: {ex_load}")
                    else:
                        old_tx = item[1]
                        new_tx = item[2]
                        text_to_set = old_tx if reverse else new_tx
                        prev_text = new_tx if reverse else old_tx
                        open_k = self._find_open_doc_key(fp)
                        doc_entry = self.open_documents.get(open_k, {}) if open_k else {}
                        enc = doc_entry.get("encoding")
                        has_bom = doc_entry.get("has_bom")
                        nl = doc_entry.get("newline")
                        if enc is None and fp.is_file():
                            try:
                                det = read_text_file_strictly(fp)
                                enc = det.encoding
                                has_bom = det.has_bom if has_bom is None else has_bom
                                nl = det.newline if nl is None else nl
                            except Exception:
                                enc = "utf-8"
                        enc = enc or "utf-8"
                        has_bom = bool(has_bom) if has_bom is not None else False
                        if has_bom or (nl and nl != "\n"):
                            write_atomic_utf8(fp, text_to_set, encoding=enc, has_bom=has_bom, newline=nl)
                        else:
                            write_atomic_utf8(fp, text_to_set, encoding=enc)
                        applied_files.append((fp, False, prev_text, enc, has_bom, nl))

                        # S5 & S09: Synchronize in-memory cache and checkpoints if open
                        if open_k and open_k in self.open_documents:
                            entry = self.open_documents[open_k]
                            if text_to_set.startswith("#!priconne-story") and entry.get("doc") is not None:
                                try:
                                    v2_doc = StoryDocument.from_v2_text(text_to_set)
                                    old_doc = entry.get("doc")
                                    if hasattr(self, "_prune_document_caches"):
                                        self._prune_document_caches(open_k, old_doc)
                                    entry["doc"] = v2_doc
                                    entry["plain_text"] = ""
                                    entry["dirty"] = False
                                    entry["boxes_count"] = len(v2_doc.boxes)
                                    new_jp_by_uid = {
                                        _get_box_uid(b): b.clean_text
                                        for b in v2_doc.boxes
                                        if _get_box_uid(b) is not None
                                    }
                                    entry["original_jp_by_uid"] = dict(new_jp_by_uid)
                                    self._record_saved_checkpoint(open_k, v2_doc)
                                    if open_k == active_k:
                                        self.current_doc = v2_doc
                                        self._plain_text_content = ""
                                        self.is_dirty = False
                                        self._original_jp_by_uid = dict(new_jp_by_uid)
                                        if hasattr(self, "_resync_box_indices_from_uids"):
                                            self._resync_box_indices_from_uids()
                                        active_updated = True
                                    continue
                                except Exception:
                                    pass
                            entry["plain_text"] = text_to_set
                            entry["dirty"] = False
                            self._record_saved_checkpoint(open_k, None, plain_text=text_to_set)
                            if open_k == active_k:
                                self._plain_text_content = text_to_set
                                self.is_dirty = False
                                active_updated = True
            except Exception as ex:
                self.logger.error("File I/O", f"Failed applying bulk delta: {ex}")
                # S5/S9b: Rollback applied files in reverse order to ensure all-or-nothing transaction safety
                for rolled_fp, is_bdl, prev_val, r_enc, r_bom, r_nl in reversed(applied_files):
                    try:
                        open_k = self._find_open_doc_key(rolled_fp)
                        if is_bdl:
                            self._restore_bundle_atomic(prev_val, rolled_fp)
                            if open_k and open_k in self.open_documents:
                                try:
                                    rb_doc, rb_env, rb_obj, _ = load_bundle_story(rolled_fp)
                                    old_env = self.open_documents[open_k].get("env")
                                    if old_env is not None and old_env is not rb_env:
                                        dispose_unity_env(old_env)
                                    self.open_documents[open_k]["doc"] = rb_doc
                                    self.open_documents[open_k]["env"] = rb_env
                                    self.open_documents[open_k]["obj"] = rb_obj
                                    self.open_documents[open_k]["dirty"] = False
                                    self._record_saved_checkpoint(open_k, rb_doc)
                                    if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                        self.current_doc = rb_doc
                                        self.current_unity_env = rb_env
                                        self.current_text_obj = rb_obj
                                        self.is_dirty = False
                                except Exception:
                                    pass
                        else:
                            if r_bom or (r_nl and r_nl != "\n"):
                                write_atomic_utf8(rolled_fp, prev_val, encoding=r_enc, has_bom=r_bom, newline=r_nl)
                            else:
                                write_atomic_utf8(rolled_fp, prev_val, encoding=r_enc)
                            if open_k and open_k in self.open_documents:
                                self.open_documents[open_k]["plain_text"] = prev_val
                                self.open_documents[open_k]["dirty"] = False
                                self._record_saved_checkpoint(open_k, None, plain_text=prev_val)
                                if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                    self._plain_text_content = prev_val
                                    self.is_dirty = False
                    except Exception as rb_ex:
                        self.logger.critical("File I/O", f"Rollback failed for '{rolled_fp}': {rb_ex}")
                messagebox.showerror(
                    "Undo/Redo Error",
                    f"Failed applying bulk file changes:\n{ex}\n\nOperation was safely rolled back."
                )
                raise

            if active_updated and refresh_ui:
                self._update_views()
                self._dirty_state_changed()
                if hasattr(self, "_sync_edit_menu_states"):
                    self._sync_edit_menu_states()

        if prev_caret:
            try:
                target_w = self._get_active_text_widget()
                if target_w and target_w.winfo_exists():
                    target_w.mark_set(tk.INSERT, prev_caret)
            except Exception:
                pass

    def _sync_edit_menu_states(self) -> None:
        """Dynamically update Undo/Redo labels and states in Edit menu."""
        if not hasattr(self, "edit_menu"):
            return
        try:
            cur_fp = str(self.current_file_path) if self.current_file_path else None
            can_u = self.undo_journal.can_undo(cur_fp)
            u_lbl = self.undo_journal.undo_label(cur_fp)
            self.edit_menu.entryconfigure(0, label=f"Undo {u_lbl}" if u_lbl else "Undo", state="normal" if can_u else "disabled")
            can_r = self.undo_journal.can_redo(cur_fp)
            r_lbl = self.undo_journal.redo_label(cur_fp)
            self.edit_menu.entryconfigure(1, label=f"Redo {r_lbl}" if r_lbl else "Redo", state="normal" if can_r else "disabled")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Left Dock Tabs & Opened Files Cache Actions (#3B)
    # -------------------------------------------------------------------------
    def _switch_dock_tab(self, tab_name: str) -> None:
        """Switch left dock between Search Results and Opened Files."""
        self._left_dock_tab = tab_name
        t = self.theme
        active_fg = best_contrast_fg(t["misora_pink"])
        normal_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")

        if tab_name == "files":
            self.tab_search_frame.pack_forget()
            self.tab_files_frame.pack(fill="both", expand=True)
            self.btn_tab_files.configure(bg=t["misora_pink"], fg=active_fg)
            self.btn_tab_search.configure(bg=t["bg_panel"], fg=normal_fg)
            self._refresh_opened_files_list()
        else:
            self.tab_files_frame.pack_forget()
            self.tab_search_frame.pack(fill="both", expand=True)
            self.btn_tab_search.configure(bg=t["misora_pink"], fg=active_fg)
            self.btn_tab_files.configure(bg=t["bg_panel"], fg=normal_fg)

    def _set_left_panel_visible(self, visible: bool) -> None:
        """Show or hide left_frame via h_paned.forget/add without destroying child widgets or rebuilding views (U03)."""
        if not hasattr(self, "h_paned") or not self.h_paned.winfo_exists():
            return
        if not hasattr(self, "left_frame") or not self.left_frame.winfo_exists():
            return
        panes = [str(p) for p in self.h_paned.panes()]
        if visible:
            self._dock_collapsed = False
            if hasattr(self, "var_show_left_panel"):
                self.var_show_left_panel.set(True)
            if hasattr(self, "btn_reopen_left") and self.btn_reopen_left.winfo_exists():
                self.btn_reopen_left.pack_forget()
            target_w = max(160, int(getattr(self, "_left_dock_width", 340) or 340))
            if str(self.left_frame) not in panes:
                if hasattr(self, "right_frame") and self.right_frame.winfo_exists() and str(self.right_frame) in panes:
                    self.h_paned.add(self.left_frame, before=self.right_frame, minsize=160, width=target_w, stretch="never")
                else:
                    self.h_paned.add(self.left_frame, minsize=160, width=target_w, stretch="never")
            self.h_paned.paneconfigure(self.left_frame, minsize=160, width=target_w)
            try:
                self.h_paned.sash_place(0, target_w, 0)
            except Exception:
                pass
        else:
            if str(self.left_frame) in panes:
                current_w = self.left_frame.winfo_width()
                if current_w >= 100:
                    self._left_dock_width = current_w
                self.h_paned.forget(self.left_frame)
            self._dock_collapsed = True
            if hasattr(self, "var_show_left_panel"):
                self.var_show_left_panel.set(False)
            if hasattr(self, "btn_reopen_left") and self.btn_reopen_left.winfo_exists():
                if not self._is_widget_packed(self.btn_reopen_left):
                    if hasattr(self, "v_paned") and self.v_paned.winfo_exists() and self._is_widget_packed(self.v_paned):
                        self.btn_reopen_left.pack(side="left", anchor="n", padx=(2, 2), pady=(6, 2), before=self.v_paned)
                    else:
                        self.btn_reopen_left.pack(side="left", anchor="n", padx=(2, 2), pady=(6, 2))

    def _on_toggle_left_panel(self) -> None:
        """Toggle Left Panel visibility from View > Show Left Panel menu checkbutton (U03)."""
        show = bool(self.var_show_left_panel.get()) if hasattr(self, "var_show_left_panel") else True
        self._set_left_panel_visible(show)

    def _toggle_dock_collapse(self) -> None:
        """Toggle left dock between hidden (0px forgotten from h_paned) and expanded (U03)."""
        is_collapsed = bool(getattr(self, "_dock_collapsed", False))
        self._set_left_panel_visible(is_collapsed)

    def _refresh_opened_files_list(self) -> None:
        """Re-render the list of cached opened files in the Opened Files dock tab."""
        if not hasattr(self, "txt_opened_files"):
            return
        self.txt_opened_files.config(state="normal")
        self.txt_opened_files.delete("1.0", tk.END)
        self._opened_files_line_map: Dict[int, Path] = {}

        count = len(self.open_documents)
        self.lbl_files_title.config(text=f"Opened Files ({count})")

        for idx, (fpath, info) in enumerate(self.open_documents.items(), start=1):
            line_no = idx
            self._opened_files_line_map[line_no] = fpath
            is_active = (fpath == self.current_file_path)
            is_dirty = bool(info.get("dirty", False))

            prefix = "● " if is_active else "  "
            dirty_mark = "* " if is_dirty else "  "
            tag_name = "file_active" if is_active else ("file_dirty" if is_dirty else "file_normal")

            self.txt_opened_files.insert(tk.END, prefix, ("file_close",))
            self.txt_opened_files.insert(tk.END, dirty_mark, ("file_dirty" if is_dirty else "file_dim",))
            self.txt_opened_files.insert(tk.END, fpath.name, (tag_name,))

            boxes = info.get("boxes_count", 0)
            detail = f" ({boxes} boxes)" if boxes else f" ({fpath.suffix})"
            self.txt_opened_files.insert(tk.END, detail, ("file_dim",))
            self.txt_opened_files.insert(tk.END, "  [×]\n", ("file_close",))

        self.txt_opened_files.config(state="disabled")

    def _on_opened_files_click(self, event: tk.Event) -> str:
        """Clicking an opened file switches to it; clicking [×] closes it."""
        idx_str = self.txt_opened_files.index(f"@{event.x},{event.y}")
        line_no = int(idx_str.split(".")[0])
        col_no = int(idx_str.split(".")[1])
        fpath = getattr(self, "_opened_files_line_map", {}).get(line_no)
        if not fpath:
            return "break"

        line_text = self.txt_opened_files.get(f"{line_no}.0", f"{line_no}.end")
        if "[×]" in line_text and col_no >= line_text.rfind("[×]"):
            self.close_file(fpath)
        else:
            if fpath != self.current_file_path:
                self.open_file(fpath)
        return "break"

    def _prune_document_caches(
        self,
        file_path: Optional[Union[str, Path]],
        doc: Optional[Any],
        extra_uids: Optional[Iterable[Any]] = None,
    ) -> None:
        """Prune all document-scoped MTL & XUAT JP caches for a closed or reloaded document (BUG-03 / BONUS-01)."""
        fp_str = str(Path(file_path).resolve()) if file_path else ""
        doc_id = id(doc) if doc is not None else None

        doc_uids: Set[Any] = set()
        if doc is not None and getattr(doc, "boxes", None):
            for b in doc.boxes:
                u = _get_box_uid(b)
                if u is not None:
                    doc_uids.add(u)
        if extra_uids is not None:
            for u in extra_uids:
                if u is not None:
                    doc_uids.add(u)

        # Exclude any UIDs still referenced by other open documents
        other_uids: Set[Any] = set()
        for open_p, open_entry in getattr(self, "open_documents", {}).items():
            if fp_str and str(Path(open_p).resolve()) == fp_str:
                continue
            if not isinstance(open_entry, dict):
                continue
            other_doc = open_entry.get("doc")
            if other_doc is doc:
                continue
            if other_doc is not None and getattr(other_doc, "boxes", None):
                for ob in other_doc.boxes:
                    ou = _get_box_uid(ob)
                    if ou is not None:
                        other_uids.add(ou)
            other_jp = open_entry.get("original_jp_by_uid")
            if isinstance(other_jp, dict):
                other_uids.update(other_jp.keys())
        uids_to_prune = doc_uids - other_uids

        def _matches_ctx(k: Any) -> bool:
            if not isinstance(k, tuple) or len(k) < 2:
                return False
            if fp_str and k[0] == fp_str:
                return True
            if doc_id is not None and k[1] == doc_id:
                return True
            return False

        for attr in ("_mtl_all_results", "_mtl_all_statuses", "_mtl_all_errors"):
            mapping = getattr(self, attr, None)
            if isinstance(mapping, dict):
                for k in [key for key in mapping if _matches_ctx(key)]:
                    mapping.pop(k, None)

        req_seqs = getattr(self, "_mtl_all_req_seqs", None)
        if isinstance(req_seqs, dict) and uids_to_prune:
            for k in [key for key in req_seqs if isinstance(key, tuple) and key and key[0] in uids_to_prune]:
                req_seqs.pop(k, None)

        latest_seq_map = getattr(self, "_latest_applied_mtl_seq", None)
        if isinstance(latest_seq_map, dict) and uids_to_prune:
            for u in uids_to_prune:
                latest_seq_map.pop(u, None)

        last_ctx = getattr(self, "_mtl_all_last_ctx", None)
        if last_ctx is not None and _matches_ctx(last_ctx):
            self._mtl_all_last_ctx = None

        is_active_match = (
            (fp_str and str(getattr(self, "current_file_path", "") or "") == fp_str)
            or (doc is not None and getattr(self, "current_doc", None) is doc)
        )
        if is_active_match:
            self._mtl_all_selected_uid = None
            self._mtl_all_block_ranges = []
            self._mtl_all_last_ctx = None
            self._mtl_drawer_active_context = None
            if hasattr(self, "_mtl_drawer_latest_seq") and isinstance(self._mtl_drawer_latest_seq, dict):
                self._mtl_drawer_latest_seq.clear()

        if hasattr(self, "sync_manager") and self.sync_manager is not None and uids_to_prune:
            if hasattr(self.sync_manager, "unregister_jp_keys"):
                self.sync_manager.unregister_jp_keys(uids_to_prune)

    def close_file(self, file_path: Path) -> bool:
        """Close an opened file from in-memory cache, prompting if dirty (S3).

        Returns True if the file was closed, False if close was cancelled or aborted.
        """
        file_path = Path(file_path).resolve()
        if file_path == self.current_file_path:
            if not self._flush_active_widget():
                return False

        info = self.open_documents.get(file_path)
        is_dirty = (file_path == self.current_file_path and self.is_dirty) or (info and info.get("dirty", False))

        if is_dirty:
            ans = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"'{file_path.name}' has unsaved changes.\nSave before closing?",
                parent=self,
            )
            if ans is None:
                return False
            if ans:
                if not self._save_document_entry(file_path):
                    return False

        if file_path == self.current_file_path and hasattr(self, "_cancel_mtl_all_batch"):
            self._cancel_mtl_all_batch()

        closed_env = None
        closed_doc = None
        closed_jp_uids: Iterable[Any] = ()
        if file_path in self.open_documents:
            entry_dict = self.open_documents[file_path] if isinstance(self.open_documents[file_path], dict) else {}
            closed_env = entry_dict.get("env")
            closed_doc = entry_dict.get("doc")
            orig_jp = entry_dict.get("original_jp_by_uid")
            if isinstance(orig_jp, dict):
                closed_jp_uids = list(orig_jp.keys())
            del self.open_documents[file_path]
            self.undo_journal.prune_file(str(file_path))
            if closed_env is not None:
                dispose_unity_env(closed_env)

        if file_path == self.current_file_path and closed_doc is None:
            closed_doc = getattr(self, "current_doc", None)
        if file_path == self.current_file_path and not closed_jp_uids:
            closed_jp_uids = list(getattr(self, "_original_jp_by_uid", {}).keys())
        self._prune_document_caches(file_path, closed_doc, extra_uids=closed_jp_uids)

        self._saved_state_checkpoints.pop(str(file_path), None)

        if file_path == self.current_file_path:
            if self.current_unity_env is not None and (self.current_unity_env is closed_env or not self.open_documents):
                dispose_unity_env(self.current_unity_env)
                self.current_unity_env = None
                self.current_text_obj = None
            if self.open_documents:
                next_file = next(iter(self.open_documents))
                self.open_file(next_file)
            else:
                self.current_file_path = None
                self.current_doc = None
                self.current_unity_env = None
                self.current_text_obj = None
                self.is_bundle_file = False
                self.is_dirty = False
                self._plain_text_content = ""
                if hasattr(self, "_reset_speaker_pin"):
                    self._reset_speaker_pin(notify=False)
                self._clear_card_registry()  # S4: prune stale card refs before view reset
                if hasattr(self, "undo_journal") and hasattr(self.undo_journal, "set_active_file"):
                    self.undo_journal.set_active_file("")
                self._update_views()
                self._sync_edit_menu_states()
                self.lbl_status.config(text="Ready. No files open.")

        self._refresh_opened_files_list()
        return True

    def close_others(self, keep_path: Path) -> None:
        """Close all opened files except keep_path."""
        keep_path = Path(keep_path).resolve()
        to_close = [p for p in list(self.open_documents.keys()) if p != keep_path]
        for p in to_close:
            if not self.close_file(p):
                break

    def close_all_unmodified(self) -> None:
        """Close all opened files that do not have unsaved changes."""
        to_close = []
        for p, info in list(self.open_documents.items()):
            is_dirty = (p == self.current_file_path and self.is_dirty) or info.get("dirty", False)
            if not is_dirty:
                to_close.append(p)
        for p in to_close:
            if not self.close_file(p):
                break

    def close_all_files(self) -> None:
        """Close all opened files, prompting on any unsaved changes."""
        for p in list(self.open_documents.keys()):
            if not self.close_file(p):
                break

    def _close_all_documents_without_prompt(self) -> None:
        """Close all open documents cleanly without prompting (used after ProjectDiffDialog confirmation)."""
        if hasattr(self, "_cancel_mtl_all_batch"):
            self._cancel_mtl_all_batch()
        for p, info in list(self.open_documents.items()):
            env = info.get("env") if isinstance(info, dict) else None
            doc = info.get("doc") if isinstance(info, dict) else None
            jp_uids = list(info.get("original_jp_by_uid", {}).keys()) if isinstance(info, dict) and isinstance(info.get("original_jp_by_uid"), dict) else ()
            if hasattr(self, "_prune_document_caches"):
                self._prune_document_caches(p, doc, extra_uids=jp_uids)
            if env is not None:
                dispose_unity_env(env)
            if hasattr(self, "undo_journal"):
                self.undo_journal.prune_file(str(p))
            if hasattr(self, "_saved_state_checkpoints"):
                self._saved_state_checkpoints.pop(str(p), None)
        if hasattr(self, "_prune_document_caches") and (self.current_file_path or self.current_doc):
            self._prune_document_caches(
                self.current_file_path,
                self.current_doc,
                extra_uids=getattr(self, "_original_jp_by_uid", {}).keys(),
            )
        self.open_documents.clear()
        if self.current_unity_env is not None:
            dispose_unity_env(self.current_unity_env)
        self.current_file_path = None
        self.current_doc = None
        self.current_unity_env = None
        self.current_text_obj = None
        self.is_bundle_file = False
        self.is_dirty = False
        self._plain_text_content = ""
        self._locked_boxes = set()
        self._locked_box_uids = set()
        self._modified_boxes = set()
        self._modified_box_uids = set()
        self._original_box_texts = {}
        self._original_jp_by_uid = {}
        self._clear_card_registry()
        if hasattr(self, "undo_journal") and hasattr(self.undo_journal, "set_active_file"):
            self.undo_journal.set_active_file("")

    def on_save_project(self) -> None:
        """Prompt for a .misora file path and save the current workspace session."""
        if not self.open_documents:
            messagebox.showinfo("Save Project", "No files are currently open to save in a project.", parent=self)
            return
        init_dir = str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) and self.last_opened_dir.exists() else None
        target = filedialog.asksaveasfilename(
            initialdir=init_dir,
            title="Save Misora Project",
            defaultextension=MISORA_WORKSPACE_EXT,
            filetypes=[("Misora Project", f"*{MISORA_WORKSPACE_EXT}"), ("All Files", "*.*")],
        )
        if target:
            self.save_project(Path(target))

    def save_project(self, workspace_path: Union[str, Path]) -> bool:
        """Save .misora v1 workspace session (strictly refs + state + stable locks ONLY)."""
        if not self._flush_active_widget():
            return False
        self._save_active_document_state()
        self._exit_raw_edit_mode(refresh=False)
        if hasattr(self, "_cancel_mtl_all_batch"):
            self._cancel_mtl_all_batch()

        ws_path = Path(workspace_path).resolve()
        ws_dir = ws_path.parent

        file_entries: List[WorkspaceFileEntry] = []
        for raw_p, entry in self.open_documents.items():
            p = Path(raw_p).resolve()
            rel = safe_relpath(p, ws_dir)
            doc = entry.get("doc") if isinstance(entry, dict) else None
            locked_uids = set(entry.get("locked_box_uids", set())) if isinstance(entry, dict) else set()
            orig_jp_by_uid = dict(entry.get("original_jp_by_uid", {})) if isinstance(entry, dict) else {}
            stable_pairs = get_document_stable_locks(doc, locked_uids, orig_jp_by_uid)
            locked_keys = [LockedKeyEntry(box_ordinal=o, jp_sha256=h) for o, h in stable_pairs]
            file_entries.append(WorkspaceFileEntry(rel_path=rel, abs_path=str(p), locked_keys=locked_keys))

        active_file_str: Optional[str] = None
        if self.current_file_path is not None:
            cur_p = Path(self.current_file_path).resolve()
            rel_active = safe_relpath(cur_p, ws_dir)
            active_file_str = rel_active if rel_active else str(cur_p)

        view_mode = "continuous" if getattr(self, "var_continuous_view", None) and self.var_continuous_view.get() else "dialogue"
        search_scope = self.scope_var.get() if hasattr(self, "scope_var") else "project"

        session = WorkspaceSession(
            files=file_entries,
            active_file=active_file_str,
            active_box_idx=int(getattr(self, "current_box_idx", 0)),
            is_box0_active=bool(getattr(self, "is_box0_active", False)),
            view_mode=view_mode,
            search_scope=search_scope,
        )
        try:
            save_workspace(ws_path, session)
        except Exception as exc:
            self.logger.exception(f"Failed to save project '{ws_path.name}':", exc)
            messagebox.showerror("Save Project Error", f"Could not save project '{ws_path.name}':\n{exc}", parent=self)
            return False

        self.lbl_status.config(text=f"Saved project '{ws_path.name}' ({len(file_entries)} file(s)).")
        self.show_toast(f"Saved project: {ws_path.name}")
        return True

    def on_open_project(self) -> None:
        """Prompt for a .misora file and open the workspace session."""
        init_dir = str(self.last_opened_dir) if getattr(self, "last_opened_dir", None) and self.last_opened_dir.exists() else None
        target = filedialog.askopenfilename(
            initialdir=init_dir,
            title="Open Misora Project",
            filetypes=[("Misora Project", f"*{MISORA_WORKSPACE_EXT}"), ("All Files", "*.*")],
        )
        if target:
            self.open_project(Path(target))

    def open_project(self, workspace_path: Union[str, Path]) -> bool:
        """Open a .misora v1 workspace session with U-B18 diff dialog and stable lock matching."""
        ws_path = Path(workspace_path).resolve()
        ws_dir = ws_path.parent
        try:
            session = load_workspace(ws_path)
        except (WorkspaceError, UnicodeDecodeError, OSError) as exc:
            self.logger.error("Workspace", f"Failed to load '{ws_path}': {exc}")
            messagebox.showerror("Open Project Error", f"Could not open project '{ws_path.name}':\n{exc}", parent=self)
            return False

        resolved_entries: List[Tuple[WorkspaceFileEntry, Optional[Path]]] = []
        missing_labels: List[str] = []
        for entry in session.files:
            resolved = resolve_workspace_file_path(ws_dir, entry.rel_path, entry.abs_path)
            resolved_entries.append((entry, resolved))
            if resolved is None:
                missing_labels.append(entry.rel_path or entry.abs_path)

        target_paths = [resolved for _, resolved in resolved_entries if resolved is not None]

        # Safeguard 3: Flush active widget & save active state BEFORE computing diff
        if self.open_documents:
            if not self._flush_active_widget():
                return False
            self._save_active_document_state()
            diff_entries = compute_workspace_diff(
                self.open_documents,
                target_paths,
                current_file_path=self.current_file_path,
                current_is_dirty=getattr(self, "is_dirty", False),
            )
            dlg = ProjectDiffDialog(self, diff_entries, ws_path.name)
            choice = getattr(dlg, "result", "cancel")
            if choice == "cancel":
                return False
            if choice == "save":
                for p in list(self.open_documents.keys()):
                    info = self.open_documents.get(p, {})
                    is_doc_dirty = (p == self.current_file_path and getattr(self, "is_dirty", False)) or bool(
                        info.get("dirty", False) if isinstance(info, dict) else False
                    )
                    if is_doc_dirty and not self._save_document_entry(p):
                        return False

        self._close_all_documents_without_prompt()

        unresolved_notices: List[str] = []
        opened_entries: List[Tuple[WorkspaceFileEntry, Path]] = []
        for entry, resolved in resolved_entries:
            if resolved is None:
                continue
            try:
                self.open_file(resolved, refresh_ui=False)
            except Exception as exc:
                self.logger.error("Workspace", f"Failed opening '{resolved}': {exc}")
                missing_labels.append(str(resolved))
                continue

            doc_key = self._find_open_doc_key(resolved)
            if doc_key is not None and doc_key in self.open_documents:
                opened_entries.append((entry, doc_key))
                doc_entry = self.open_documents[doc_key]
                doc = doc_entry.get("doc")
                orig_map = doc_entry.get("original_jp_by_uid", {})
                stable_pairs = [(lk.box_ordinal, lk.jp_sha256) for lk in entry.locked_keys]
                if stable_pairs:
                    matched_uids, unresolved = restore_stable_locks(doc, stable_pairs, orig_map)
                    doc_entry["locked_box_uids"] = set(matched_uids)
                    if doc_key == self.current_file_path:
                        self._locked_box_uids = set(matched_uids)
                        self._resync_box_indices_from_uids()
                    if unresolved:
                        unresolved_notices.append(
                            f"{doc_key.name}: {len(unresolved)} lock(s) unresolved"
                        )

        # Restore view_mode & search_scope (Safeguard 4)
        if hasattr(self, "var_continuous_view"):
            self.var_continuous_view.set(session.view_mode == "continuous")
        if hasattr(self, "scope_var"):
            self.scope_var.set(session.search_scope)

        # Safeguard 3: All files missing grace -> restore empty state cleanly
        if not opened_entries:
            self._update_top_header_title()
            self._sync_scope_widgets()
            self._update_views()
            self._refresh_opened_files_list()
            self._dirty_state_changed()
            self._sync_edit_menu_states()
            if missing_labels:
                msg = f"All {len(missing_labels)} file(s) referenced by '{ws_path.name}' were not found on disk."
                self.logger.warning("Workspace", msg)
                messagebox.showwarning("Missing Project Files", msg, parent=self)
                self.lbl_status.config(text=msg)
            return True

        # Safeguard 1 & 2: Match active_file against rel_path & abs_path, then apply cursor AFTER activation
        target_active = match_active_file(session.active_file, ws_dir, resolved_entries)
        if target_active is None:
            target_active = opened_entries[0][1]
        self.open_file(target_active, refresh_ui=False)

        if self.current_doc and self.current_doc.boxes:
            self.current_box_idx = max(0, min(session.active_box_idx, len(self.current_doc.boxes) - 1))
        else:
            self.current_box_idx = 0
        self.is_box0_active = bool(session.is_box0_active)

        active_key = self._find_open_doc_key(target_active)
        if active_key is not None and active_key in self.open_documents:
            self._locked_box_uids = set(self.open_documents[active_key].get("locked_box_uids", set()))
            self._resync_box_indices_from_uids()

        # Safeguard 4: Sync view, header title, and scope UI controls together
        self._update_top_header_title()
        self._sync_scope_widgets()
        self._update_views()
        self._refresh_opened_files_list()
        self._dirty_state_changed()
        self._sync_edit_menu_states()

        notices: List[str] = []
        if missing_labels:
            notices.append(f"Missing file(s) skipped ({len(missing_labels)}): " + ", ".join(missing_labels[:5]))
        if unresolved_notices:
            notices.append("Unresolved Translation Locks (not transferred): " + "; ".join(unresolved_notices))
        if notices:
            full_notice = "\n".join(notices)
            self.logger.warning("Workspace", full_notice)
            messagebox.showwarning("Project Open Notice", full_notice, parent=self)

        self.lbl_status.config(text=f"Opened project '{ws_path.name}' ({len(opened_entries)} file(s)).")
        return True

    # -------------------------------------------------------------------------
    # Right-Click Context Menus & External Editor Launching (#4D)
    # -------------------------------------------------------------------------
    def _on_results_right_click(self, event: tk.Event) -> str:
        """Right-click in search results shows file actions context menu."""
        idx_str = self.txt_results.index(f"@{event.x},{event.y}")
        line_no = int(idx_str.split(".")[0])
        entry = self._result_line_map.get(line_no)
        target_path: Optional[Path] = None
        if entry:
            kind, payload = entry
            if kind == "header":
                target_path = Path(payload)
            elif kind == "item":
                res_idx = int(payload)
                if 0 <= res_idx < len(self.active_search_results):
                    target_path = self.active_search_results[res_idx].file_path
        if target_path and target_path.exists():
            self._show_file_context_menu(event, target_path)
        return "break"

    def _on_opened_files_right_click(self, event: tk.Event) -> str:
        """Right-click in opened files list shows file actions context menu."""
        idx_str = self.txt_opened_files.index(f"@{event.x},{event.y}")
        line_no = int(idx_str.split(".")[0])
        fpath = getattr(self, "_opened_files_line_map", {}).get(line_no)
        if fpath and fpath.exists():
            self._show_file_context_menu(event, fpath)
        return "break"

    def _show_file_context_menu(self, event: tk.Event, target_path: Path) -> None:
        """Show right-click context menu with Close, Close Others, Reveal in Explorer, etc."""
        t = self.theme
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        accent_fg = best_contrast_fg(t["misora_pink"])

        menu = tk.Menu(self, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)

        menu.add_command(label=f"Switch to '{target_path.name}'", command=lambda: self.open_file(target_path))
        if target_path in self.open_documents:
            menu.add_command(label="Close File", command=lambda: self.close_file(target_path))
            menu.add_command(label="Close Others", command=lambda: self.close_others(target_path))
            menu.add_command(label="Close All Unmodified", command=self.close_all_unmodified)
            menu.add_command(label="Close All", command=self.close_all_files)
            menu.add_separator()
            if target_path == self.current_file_path:
                menu.add_command(label="Save File (Ctrl+S)", command=self.on_save)

        menu.add_separator()
        menu.add_command(label="Reveal in File Explorer", command=lambda: self._open_containing_folder(target_path))

        open_with = tk.Menu(menu, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        open_with.add_command(label="Notepad", command=lambda: self._launch_editor_on_file("notepad.exe", target_path))
        if self.notepadpp_path and Path(self.notepadpp_path).exists():
            open_with.add_command(label="Notepad++", command=lambda: self._launch_editor_on_file(str(self.notepadpp_path), target_path))
        if self.external_editor_path and Path(self.external_editor_path).exists():
            open_with.add_command(label=f"Custom: {Path(self.external_editor_path).stem}", command=lambda: self._launch_editor_on_file(str(self.external_editor_path), target_path))
        open_with.add_separator()
        open_with.add_command(label="Choose another app...", command=lambda: self._choose_app_and_open(target_path))
        menu.add_cascade(label="Open With", menu=open_with)

        menu.add_separator()
        menu.add_command(label="Copy Full Path", command=lambda: self._copy_to_clipboard(str(target_path)))
        menu.add_command(label="Copy File Name", command=lambda: self._copy_to_clipboard(target_path.name))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_containing_folder(self, target_path: Path) -> None:
        """Reveal file in Windows Explorer."""
        try:
            if target_path.exists():
                subprocess.Popen(["explorer.exe", f"/select,{target_path}"])
            else:
                subprocess.Popen(["explorer.exe", str(target_path.parent)])
        except Exception as e:
            self.logger.error("File I/O", f"Failed to reveal in explorer: {e}")

    def _launch_editor_on_file(self, exe: str, target_path: Path) -> None:
        """Launch an external editor on target_path, warning if unsaved in Misora."""
        if target_path == self.current_file_path and self.is_dirty:
            warn = messagebox.askokcancel(
                "Unsaved Changes",
                f"'{target_path.name}' has unsaved changes in Misora.\nOpening in an external editor will show the version currently on disk.\nContinue?"
            )
            if not warn:
                return
        try:
            subprocess.Popen([exe, str(target_path)], shell=False)
            self.logger.info("External Tools", f"Opened {target_path.name} in {exe}")
        except Exception as ex:
            self.logger.exception(f"Failed to launch {exe}:", ex)
            messagebox.showerror("Launch Error", f"Failed to launch external editor:\n{ex}")

    def _choose_app_and_open(self, target_path: Path) -> None:
        """One-time browse for application to open file."""
        app = filedialog.askopenfilename(title="Choose Application to Open File", filetypes=[("Executables", "*.exe;*.bat;*.cmd"), ("All Files", "*.*")])
        if app:
            self._launch_editor_on_file(app, target_path)

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.lbl_status.config(text=f"Copied to clipboard: {text}")

    def _sync_external_editor_menu(self) -> None:
        if not hasattr(self, "_ext_editor_menu"):
            return
        self._ext_editor_menu.delete(0, "end")
        self._ext_editor_menu.add_command(label="Set / Change Editor Program...", command=self.on_set_external_editor)
        self._ext_editor_menu.add_command(label="Clear Editor Selection", command=self.on_clear_external_editor)
        self._ext_editor_menu.add_separator()
        cur_desc = f"Current: {self.external_editor_path.name}" if self.external_editor_path else "Current: (None - default)"
        self._ext_editor_menu.add_command(label=cur_desc, state="disabled")

    def on_set_external_editor(self) -> None:
        f = filedialog.askopenfilename(
            title="Select External Text Editor Executable",
            filetypes=[("Executables", "*.exe;*.bat;*.cmd"), ("All Files", "*.*")]
        )
        if f:
            self.external_editor_path = Path(f)
            self._save_user_prefs(silent=True)
            self.lbl_status.config(text=f"External editor set to: {self.external_editor_path.name}")
            self.logger.info("External Tools", f"Configured external editor: {self.external_editor_path}")

    def on_clear_external_editor(self) -> None:
        self.external_editor_path = None
        self._save_user_prefs(silent=True)
        self.lbl_status.config(text="External editor selection cleared.")

    # -------------------------------------------------------------------------
    # Datamine Tool Launcher (#4C)
    # -------------------------------------------------------------------------
    def on_launch_datamine(self) -> None:
        """Launch the external Datamine executable or Python script with confirmation."""
        if not self.datamine_exe or not Path(self.datamine_exe).exists():
            ans = messagebox.askyesno("Datamine Tool Not Set", "No datamine executable has been configured yet.\nWould you like to select one now?")
            if ans:
                self.on_select_datamine_exe()
            return

        exe_path = Path(self.datamine_exe)
        if not self._datamine_confirm_skip:
            dlg = tk.Toplevel(self)
            dlg.title("Confirm Datamine Launch")
            dlg.geometry("440x180")
            dlg.transient(self)
            dlg.grab_set()
            dlg.resizable(False, False)
            t = self.theme
            dlg.configure(bg=t["bg_panel"])

            confirmed = [False]
            skip_var = tk.BooleanVar(master=dlg, value=False)

            msg = f"Launch external datamine tool?\n\nProgram: {exe_path.name}\nPath: {exe_path}"
            tk.Label(dlg, text=msg, bg=t["bg_panel"], fg=best_contrast_fg(t["bg_panel"]), justify="left", wraplength=400).pack(padx=16, pady=(16, 8), fill="x")

            cb = tk.Checkbutton(dlg, text="Don't ask again this session", variable=skip_var, bg=t["bg_panel"], fg=best_contrast_fg(t["bg_panel"]), selectcolor=t["bg_dark"])
            cb.pack(padx=16, pady=4, anchor="w")

            btn_frame = tk.Frame(dlg, bg=t["bg_panel"])
            btn_frame.pack(fill="x", padx=16, pady=(8, 12), side="bottom")

            def _cancel(_e: Optional[tk.Event] = None) -> None:
                safe_grab_release(dlg)
                if dlg.winfo_exists():
                    dlg.destroy()

            def _ok() -> None:
                confirmed[0] = True
                if skip_var.get():
                    self._datamine_confirm_skip = True
                safe_grab_release(dlg)
                if dlg.winfo_exists():
                    dlg.destroy()

            dlg.protocol("WM_DELETE_WINDOW", _cancel)
            dlg.bind("<Escape>", _cancel)

            btn_cancel = ttk.Button(btn_frame, text="Cancel", style="TButton", command=_cancel)
            btn_cancel.pack(side="right", padx=4)
            btn_ok = ttk.Button(btn_frame, text="Launch Tool", style="Pink.TButton", command=_ok)
            btn_ok.pack(side="right", padx=4)
            btn_cancel.focus_set()

            self.wait_window(dlg)
            if not confirmed[0]:
                return

        try:
            cwd = str(exe_path.parent)
            if exe_path.suffix.lower() == ".py":
                cmd = [sys.executable, str(exe_path)]
            else:
                cmd = [str(exe_path)]
            subprocess.Popen(cmd, cwd=cwd, shell=False)
            self.logger.info("External Tools", f"Launched datamine tool: {exe_path}")
            self.lbl_status.config(text=f"Launched datamine tool: {exe_path.name}")
        except Exception as exc:
            self.logger.exception("Failed to launch datamine tool:", exc)
            messagebox.showerror("Datamine Launch Failed", f"Could not launch {exe_path.name}:\n{exc}")

    def on_select_datamine_exe(self) -> None:
        f = filedialog.askopenfilename(
            title="Select Datamine Executable or Script",
            filetypes=[
                ("Executables & Scripts", "*.exe;*.py;*.bat;*.cmd"),
                ("Applications", "*.exe"),
                ("Python Scripts", "*.py"),
                ("All Files", "*.*")
            ]
        )
        if f:
            self.datamine_exe = Path(f)
            self._save_user_prefs(silent=True)
            self.lbl_status.config(text=f"Datamine tool set to: {self.datamine_exe.name}")
            self.logger.info("External Tools", f"Configured datamine executable: {self.datamine_exe}")

    def on_open_datamine_folder(self) -> None:
        if self.datamine_exe and Path(self.datamine_exe).exists():
            subprocess.Popen(["explorer.exe", str(Path(self.datamine_exe).parent)])
        else:
            messagebox.showinfo("Datamine Folder", "No datamine executable is currently configured.")

    # -------------------------------------------------------------------------
    # Folders & Files Configuration Dialog (#4B)
    # -------------------------------------------------------------------------
    def on_open_backups_folder(self) -> None:
        bak_dir = self._get_backup_dir()
        subprocess.Popen(["explorer.exe", str(bak_dir)])

    def on_open_project_folder(self) -> None:
        """Open the Project Root / Mod Translation directory in Windows Explorer."""
        p = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
        if not p or not Path(p).exists():
            if getattr(self, "xuat_search_roots", None) and self.xuat_search_roots:
                p = self.xuat_search_roots[0]
        if p and Path(p).exists():
            subprocess.Popen(["explorer.exe", str(p)])
        else:
            ans = messagebox.askyesno("Project Folder", "Project / Mod translation folder is not set. Configure it now?")
            if ans:
                self.on_open_paths_dialog()

    def on_open_bepinex_folder(self) -> None:
        """Backward-compatible alias for on_open_project_folder."""
        self.on_open_project_folder()

    def on_open_program_folder(self) -> None:
        subprocess.Popen(["explorer.exe", str(SCRIPT_DIR)])

    def on_open_xuat_text_folder(self) -> None:
        """Open the Text translation directory in Windows Explorer (supports XUAT, MelonLoader, BepInEx)."""
        p: Optional[Path] = None
        proj = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
        if proj:
            proj_path = Path(proj)
            candidates = [
                proj_path / "Text",
                proj_path if proj_path.name.lower() == "text" else None,
                proj_path / "Translation" / "en" / "Text",
                proj_path / "UserData" / "Text",
            ]
            for cand in candidates:
                if cand and cand.is_dir():
                    p = cand
                    break
        if not p and getattr(self, "xuat_search_roots", None):
            for r in self.xuat_search_roots:
                if r.is_dir():
                    if r.name.lower() == "text":
                        p = r
                        break
                    if (r / "Text").is_dir():
                        p = r / "Text"
                        break
        if p and p.exists():
            subprocess.Popen(["explorer.exe", str(p)])
        else:
            messagebox.showinfo("Text Translation Folder", "Text translation folder could not be found. Configure the Project / Mod Folder in 'Configure Paths & Backups...'.")

    def on_open_redirected_resources_folder(self) -> None:
        """Open the RedirectedResources directory in Windows Explorer (supports BepInEx, MelonLoader, custom)."""
        p: Optional[Path] = None
        proj = getattr(self, "project_folder", None) or getattr(self, "bepinex_project_folder", None)
        if proj:
            proj_path = Path(proj)
            candidates = [
                proj_path / "RedirectedResources",
                proj_path.parent / "RedirectedResources",
                proj_path / "Translation" / "en" / "RedirectedResources",
                proj_path / "UserData" / "RedirectedResources",
                proj_path / "Mods" / "RedirectedResources",
            ]
            for cand in candidates:
                if cand.is_dir():
                    p = cand
                    break
        if p and p.exists():
            subprocess.Popen(["explorer.exe", str(p)])
        else:
            messagebox.showinfo("Redirected Resources Folder", "RedirectedResources folder could not be found. Configure the Project / Mod Folder in 'Configure Paths & Backups...'.")

    def on_open_selected_search_folder(self) -> None:
        """Open the currently selected search folder in Windows Explorer."""
        if getattr(self, "selected_search_folder", None) and Path(self.selected_search_folder).is_dir():
            subprocess.Popen(["explorer.exe", str(self.selected_search_folder)])
        else:
            messagebox.showinfo("Search Folder", "No search folder is currently set. Choose one using the [...] button in the search bar or drag & drop a folder.")

    def on_open_paths_dialog(self) -> None:
        """Dialog to configure Backup Folder, Project/Mod Folder, Datamine Tool, External Editors, Config, and Debug Log."""
        t = self.theme
        dlg = tk.Toplevel(self)
        dlg.title("Configure Paths, Backups & Folders")
        dlg.geometry("660x540")
        dlg.minsize(600, 480)
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=t["bg_panel"])

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        # 1. Pack bottom button bar FIRST so it stays anchored and visible
        btn_bar = tk.Frame(dlg, bg=t["bg_panel"], padx=16, pady=12)
        btn_bar.pack(side="bottom", fill="x")

        # 2. Main content frame
        content = tk.Frame(dlg, bg=t["bg_panel"], padx=16, pady=12)
        content.pack(side="top", fill="both", expand=True)

        def make_row(parent, label_text: str, browse_cmd=None, open_cmd=None, browse_text="Browse..."):
            r = tk.Frame(parent, bg=t["bg_panel"])
            r.pack(fill="x", pady=4)
            lbl = tk.Label(r, text=label_text, font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], width=24, anchor="w")
            lbl.pack(side="left")
            if browse_cmd:
                btn_b = ttk.Button(r, text=browse_text, style="Small.TButton", command=browse_cmd)
                btn_b.pack(side="right", padx=(4, 0))
            if open_cmd:
                btn_o = ttk.Button(r, text="Open", style="Small.TButton", command=open_cmd)
                btn_o.pack(side="right", padx=(4, 0))
            ent = tk.Entry(r, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid")
            ent.pack(side="left", fill="x", expand=True, padx=4)
            return r, ent

        # 1. Backup Folder
        def _browse_bak():
            d = filedialog.askdirectory(title="Select Backup Folder")
            if d:
                ent_backup.delete(0, tk.END)
                ent_backup.insert(0, d)
                var_use_default_bak.set(False)

        def _open_bak_folder():
            b = ent_backup.get().strip() or str(SCRIPT_DIR / "backups")
            p = Path(b)
            p.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["explorer.exe", str(p)])

        r1, ent_backup = make_row(content, "Backup Folder:", browse_cmd=_browse_bak, open_cmd=_open_bak_folder)
        cur_bak = str(self.backup_folder) if self.backup_folder else str(SCRIPT_DIR / "backups")
        ent_backup.insert(0, cur_bak)
        var_use_default_bak = tk.BooleanVar(master=dlg, value=(self.backup_folder is None))

        cb_bak = tk.Checkbutton(
            content,
            text="Use default backups folder (SCRIPT_DIR/backups)",
            variable=var_use_default_bak,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
            activebackground=t["bg_panel"],
            activeforeground=fg_panel,
        )
        cb_bak.pack(anchor="w", padx=(170, 0), pady=(0, 6))

        # 2. Project / Mod Root Folder (BepInEx, MelonLoader, XUAT, custom)
        def _browse_project():
            init_d = ent_project.get().strip() or self._get_project_display_path()
            d = filedialog.askdirectory(initialdir=init_d, title="Select Project Root / Mod Folder (BepInEx, MelonLoader, etc.)")
            if d:
                ent_project.delete(0, tk.END)
                ent_project.insert(0, d)

        def _open_project_folder_ui():
            b = ent_project.get().strip() or self._get_project_display_path()
            if b and Path(b).exists():
                subprocess.Popen(["explorer.exe", str(b)])
            else:
                messagebox.showinfo("Project Folder", "Folder does not exist.")

        r2, ent_project = make_row(content, "Project / Mod Folder:", browse_cmd=_browse_project, open_cmd=_open_project_folder_ui)
        cur_proj = str(self.project_folder) if getattr(self, "project_folder", None) else self._get_project_display_path()
        ent_project.insert(0, cur_proj)

        lbl_proj_hint = tk.Label(
            content,
            text="Root directory for translation/mod project (BepInEx, MelonLoader, XUAT, etc.)",
            font=("Segoe UI", 8),
            bg=t["bg_panel"],
            fg=t["fg_muted"]
        )
        lbl_proj_hint.pack(anchor="w", padx=(170, 0), pady=(0, 6))

        # 3. Universal Datamine Tool
        def _browse_datamine():
            f = filedialog.askopenfilename(
                title="Select Datamine Tool",
                filetypes=[("Executables & Scripts", "*.exe;*.py;*.bat;*.cmd"), ("All Files", "*.*")]
            )
            if f:
                ent_datamine.delete(0, tk.END)
                ent_datamine.insert(0, f)

        r3, ent_datamine = make_row(content, "Datamine Tool:", browse_cmd=_browse_datamine)
        if self.datamine_exe:
            ent_datamine.insert(0, str(self.datamine_exe))

        # 4. Notepad++ Path
        def _browse_npp():
            f = filedialog.askopenfilename(
                title="Select Notepad++ Executable",
                filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
            )
            if f:
                ent_npp.delete(0, tk.END)
                ent_npp.insert(0, f)

        r4, ent_npp = make_row(content, "Notepad++ Executable:", browse_cmd=_browse_npp)
        if self.notepadpp_path:
            ent_npp.insert(0, str(self.notepadpp_path))

        # 5. External Text Editor
        def _browse_editor():
            f = filedialog.askopenfilename(
                title="Select External Text Editor",
                filetypes=[("Executables & Scripts", "*.exe;*.bat;*.cmd"), ("All Files", "*.*")]
            )
            if f:
                ent_editor.delete(0, tk.END)
                ent_editor.insert(0, f)

        r5, ent_editor = make_row(content, "External Text Editor:", browse_cmd=_browse_editor)
        if self.external_editor_path:
            ent_editor.insert(0, str(self.external_editor_path))

        # Separator & File references
        ttk.Separator(content, orient="horizontal").pack(fill="x", pady=10)

        # 6. Config File
        r_cfg = tk.Frame(content, bg=t["bg_panel"])
        r_cfg.pack(fill="x", pady=2)
        tk.Label(r_cfg, text="Config File:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["fg_muted"], width=24, anchor="w").pack(side="left")
        ttk.Button(r_cfg, text="Reveal", style="Small.TButton", command=lambda: subprocess.Popen(["explorer.exe", f"/select,{CONFIG_PATH}"])).pack(side="right", padx=(4, 0))
        tk.Label(r_cfg, text=str(CONFIG_PATH), font=("Consolas", 8), bg=t["bg_panel"], fg=fg_panel, anchor="w").pack(side="left", fill="x", expand=True)

        # 7. Debug Log
        r_log = tk.Frame(content, bg=t["bg_panel"])
        r_log.pack(fill="x", pady=2)
        tk.Label(r_log, text="Debug Log:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["fg_muted"], width=24, anchor="w").pack(side="left")
        ttk.Button(r_log, text="Open", style="Small.TButton", command=self._on_open_debug_log_file).pack(side="right", padx=(4, 0))
        tk.Label(r_log, text=str(DEBUG_LOG_PATH), font=("Consolas", 8), bg=t["bg_panel"], fg=fg_panel, anchor="w").pack(side="left", fill="x", expand=True)

        # Buttons at bottom
        def _safe_close(_e: Optional[tk.Event] = None) -> None:
            safe_grab_release(dlg)
            if dlg.winfo_exists():
                dlg.destroy()

        def _save_and_close():
            if var_use_default_bak.get():
                self.backup_folder = None
            else:
                b_val = ent_backup.get().strip()
                self.backup_folder = Path(b_val) if b_val else None

            proj_val = ent_project.get().strip()
            if proj_val:
                p = Path(proj_val)
                self._set_project_folder(p)
                if self.scope_var.get() == "project":
                    self.folder_path_var.set(str(self.project_folder))
            else:
                self.project_folder = None
                self.bepinex_project_folder = None
                self.xuat_search_roots = []

            dm_val = ent_datamine.get().strip()
            self.datamine_exe = Path(dm_val) if dm_val else None

            npp_val = ent_npp.get().strip()
            self.notepadpp_path = Path(npp_val) if npp_val else None

            ed_val = ent_editor.get().strip()
            self.external_editor_path = Path(ed_val) if ed_val else None

            self._save_user_prefs()
            self.lbl_status.config(text="Updated paths and backup configuration.")
            self.show_toast("Paths and backup settings saved successfully!")
            _safe_close()
            messagebox.showinfo(
                "Settings Saved",
                "Paths, backups, and preferences have been saved successfully.",
                parent=self,
            )

        dlg.protocol("WM_DELETE_WINDOW", _safe_close)
        dlg.bind("<Escape>", _safe_close)

        ttk.Button(btn_bar, text="Cancel", style="TButton", command=_safe_close).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Save & Apply", style="Pink.TButton", command=_save_and_close).pack(side="right", padx=4)

    # -------------------------------------------------------------------------
    # Side Drawer Pinning (#6)
    # -------------------------------------------------------------------------
    def _toggle_side_drawer_pin(self) -> None:
        self._side_drawer_pinned = not getattr(self, "_side_drawer_pinned", False)
        pin_icon = "📌" if self._side_drawer_pinned else "📍"
        if hasattr(self, "btn_drawer_pin"):
            self.btn_drawer_pin.config(text=pin_icon)
        self.show_toast(f"Side drawer {'pinned' if self._side_drawer_pinned else 'unpinned'}")

    # -------------------------------------------------------------------------
    # Translator Suite Callbacks & Handlers (#4A, #16, #17)
    # -------------------------------------------------------------------------
    def on_open_mtl_settings(self) -> None:
        """Open the Machine Translation sources & configuration dialog."""
        MTLSettingsDialog(self)

    def on_open_ai_prompt_settings(self) -> None:
        """Open the AI / LLM translation prompt header and exporter dialog."""
        AIPromptSettingsDialog(self)

    def on_open_translator_assistant(self) -> None:
        """Toggle the docked right-side MTL Drawer tab (FEAT-12)."""
        self._toggle_side_drawer("mtl")

    # -------------------------------------------------------------------------
    # Docked Right-Side MTL Drawer — Dialogue Multi-Engine Stack (FEAT-12)
    # -------------------------------------------------------------------------
    _MTL_DRAWER_ENGINE_ORDER: Tuple[str, ...] = (
        "XUAT Cache",
        "Google",
        "DeepL",
        "Local / Sugoi",
        "LLM / OpenAI",
    )
    _MTL_DRAWER_PAID_ENGINES: Tuple[str, ...] = ("DeepL", "LLM / OpenAI")
    _MTL_DRAWER_CACHE_MAX: int = 256

    def _build_mtl_tab(self, parent: tk.Frame) -> None:
        """Build the docked MTL Drawer tab (Dialogue 1-box multi-engine stack)."""
        t = self.theme

        # Top controls: Mode selector + Refresh All
        hdr = self._tag_role(tk.Frame(parent, bg=t["bg_panel"]), "panel")
        hdr.pack(fill="x", padx=6, pady=(2, 4))

        self.btn_mtl_mode_dialogue = ttk.Button(
            hdr,
            text="Dialogue",
            style="Pink.TButton",
            command=lambda: self._set_mtl_drawer_mode("dialogue"),
        )
        self.btn_mtl_mode_dialogue.pack(side="left", padx=(0, 3))
        create_tooltip(self.btn_mtl_mode_dialogue, "Dialogue (1-Box) multi-engine stack")

        self.btn_mtl_mode_all_script = ttk.Button(
            hdr,
            text="All Script",
            style="TButton",
            command=lambda: self._set_mtl_drawer_mode("all_script"),
        )
        self.btn_mtl_mode_all_script.pack(side="left", padx=(0, 4))
        create_tooltip(self.btn_mtl_mode_all_script, "All Script batch MTL (2-widget list + scratchpad)")

        self.ico_refresh = self.get_icon("refresh", (14, 14))
        self.btn_mtl_refresh_all = ttk.Button(
            hdr,
            text="Refresh All" if self.ico_refresh else "↻ Refresh All",
            image=self.ico_refresh,
            compound="left" if self.ico_refresh else "none",
            style="Pink.TButton",
            command=self._on_mtl_drawer_refresh_all,
        )
        self.btn_mtl_refresh_all.pack(side="right")
        create_tooltip(self.btn_mtl_refresh_all, "Refresh all enabled engines for current box")

        # Active box context bar
        ctx_bar = self._tag_role(tk.Frame(parent, bg=t["bg_panel"]), "panel")
        ctx_bar.pack(fill="x", padx=6, pady=(0, 4))
        self._mtl_dialogue_ctx_bar = ctx_bar

        self.lbl_mtl_box_info = self._tag_role(
            tk.Label(ctx_bar, text="Box 0 / 0", bg=t["bg_panel"], fg=t["misora_pink"], anchor="w"),
            "label_accent",
        )
        self.lbl_mtl_box_info.pack(fill="x")

        self.lbl_mtl_source_preview = self._tag_role(
            tk.Label(
                ctx_bar,
                text="Open a story document to translate.",
                bg=t["bg_panel"],
                fg=t["fg_muted"],
                anchor="w",
                justify="left",
                wraplength=280,
            ),
            "label_muted",
        )
        self.lbl_mtl_source_preview.pack(fill="x", pady=(2, 0))

        # Scrollable vertical stack of enabled engine cards (engine toggles live in Translator > Enabled Engines)
        wrap = self._tag_role(tk.Frame(parent, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        wrap.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self._mtl_dialogue_wrap = wrap

        self._mtl_drawer_canvas = self._tag_role(
            tk.Canvas(wrap, bg=t["bg_panel"], highlightthickness=0, bd=0),
            "panel",
        )
        vscroll = tk.Scrollbar(wrap, orient="vertical", command=self._mtl_drawer_canvas.yview)
        vscroll.pack(side="right", fill="y")
        self._mtl_drawer_canvas.pack(side="left", fill="both", expand=True)
        self._mtl_drawer_canvas.configure(yscrollcommand=vscroll.set)

        self.mtl_cards_body = self._tag_role(tk.Frame(self._mtl_drawer_canvas, bg=t["bg_panel"]), "panel")
        win_id = self._mtl_drawer_canvas.create_window((0, 0), window=self.mtl_cards_body, anchor="nw")

        self.mtl_cards_body.bind(
            "<Configure>",
            lambda _e: self._mtl_drawer_canvas.configure(scrollregion=self._mtl_drawer_canvas.bbox("all")),
        )
        self._mtl_drawer_canvas.bind(
            "<Configure>",
            lambda e: self._mtl_drawer_canvas.itemconfigure(win_id, width=max(220, e.width)),
        )

        self._build_mtl_all_script_pane(parent)
        self._rebuild_mtl_drawer_cards()

    def _build_mtl_all_script_pane(self, parent: tk.Frame) -> None:
        """Build the All Script MTL mode pane: 1 single-engine selector + exact 2 tk.Text widgets (FEAT-13, NO-03)."""
        t = self.theme
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        pane = self._tag_role(tk.Frame(parent, bg=t["bg_panel"]), "panel")
        self.mtl_all_script_frame = pane

        # Top single-engine selector
        top_bar = self._tag_role(tk.Frame(pane, bg=t["bg_panel"]), "panel")
        top_bar.pack(fill="x", padx=2, pady=(0, 4))

        self._tag_role(
            tk.Label(top_bar, text="Engine:", bg=t["bg_panel"], fg=t["fg_muted"], anchor="w"),
            "label_muted",
        ).pack(side="left", padx=(0, 4))

        default_eng = getattr(self.mtl_config, "active_engine", "Google") or "Google"
        if default_eng not in self._MTL_DRAWER_ENGINE_ORDER:
            default_eng = "Google"
        self.var_mtl_all_engine = tk.StringVar(master=self, value=default_eng)
        self.cmb_mtl_all_engine = ttk.Combobox(
            top_bar,
            textvariable=self.var_mtl_all_engine,
            values=list(self._MTL_DRAWER_ENGINE_ORDER),
            state="readonly",
            width=16,
        )
        self.cmb_mtl_all_engine.pack(side="left", fill="x", expand=True)
        self.cmb_mtl_all_engine.bind("<<ComboboxSelected>>", self._on_mtl_all_engine_changed)
        create_tooltip(self.cmb_mtl_all_engine, "Select single MTL engine for All Script batch mode")

        # Action bar: Refresh Selected, Apply Selected, Translate All, Apply All
        act_bar = self._tag_role(tk.Frame(pane, bg=t["bg_panel"]), "panel")
        act_bar.pack(fill="x", padx=2, pady=(0, 4))

        self.btn_mtl_all_refresh_sel = ttk.Button(
            act_bar,
            text="Refresh Selected" if getattr(self, "ico_refresh", None) else "↻ Refresh Selected",
            image=getattr(self, "ico_refresh", None),
            compound="left" if getattr(self, "ico_refresh", None) else "none",
            style="Small.TButton",
            command=self._on_mtl_all_script_refresh_selected,
        )
        self.btn_mtl_all_refresh_sel.pack(side="left", padx=(0, 3))
        create_tooltip(self.btn_mtl_all_refresh_sel, "Refresh selected box (bypass session cache)")

        self.btn_mtl_all_apply_sel = ttk.Button(
            act_bar,
            text="← Apply Selected",
            style="TButton",
            command=self._on_mtl_all_script_apply_selected,
        )
        self.btn_mtl_all_apply_sel.pack(side="left", padx=(0, 3))
        create_tooltip(self.btn_mtl_all_apply_sel, "Apply scratchpad to selected box (enforces lock)")

        act_bar2 = self._tag_role(tk.Frame(pane, bg=t["bg_panel"]), "panel")
        act_bar2.pack(fill="x", padx=2, pady=(0, 4))

        self.btn_mtl_all_translate = ttk.Button(
            act_bar2,
            text="Translate All",
            style="Pink.TButton",
            command=self._on_mtl_all_script_translate_all,
        )
        self.btn_mtl_all_translate.pack(side="left", padx=(0, 3))
        create_tooltip(self.btn_mtl_all_translate, "Batch-translate all unlocked boxes (uses session cache)")

        self.btn_mtl_all_apply_all = ttk.Button(
            act_bar2,
            text="Apply All",
            style="Pink.TButton",
            command=self._on_mtl_all_script_apply_all,
        )
        self.btn_mtl_all_apply_all.pack(side="left")
        create_tooltip(self.btn_mtl_all_apply_all, "Apply all ready translations to unlocked boxes in one Undo batch")

        # Widget 1: ONE read-only multi-line tk.Text list of clickable per-box tagged blocks
        list_wrap = self._tag_role(tk.Frame(pane, bg=t["bg_editor"], bd=1, relief="solid"), "editor_box")
        list_wrap.pack(fill="both", expand=True, padx=2, pady=(0, 4))

        self.txt_mtl_all_list = self._tag_role(
            tk.Text(
                list_wrap,
                wrap="word",
                state="disabled",
                font=("Segoe UI", 9),
                bg=t["bg_editor"],
                fg=editor_fg,
                bd=0,
                padx=6,
                pady=4,
                cursor="hand2",
            ),
            "entry_editor",
        )
        list_scroll = tk.Scrollbar(list_wrap, orient="vertical", command=self.txt_mtl_all_list.yview)
        list_scroll.pack(side="right", fill="y")
        self.txt_mtl_all_list.pack(side="left", fill="both", expand=True)
        self.txt_mtl_all_list.configure(yscrollcommand=list_scroll.set)
        self.txt_mtl_all_list.bind("<Button-1>", self._on_mtl_all_list_click)

        # Widget 2: ONE shared bottom editable tk.Text scratchpad synced to clicked box
        self.lbl_mtl_all_scratch_hdr = self._tag_role(
            tk.Label(pane, text="Scratchpad (No box selected)", bg=t["bg_panel"], fg=t["misora_pink"], anchor="w"),
            "label_accent",
        )
        self.lbl_mtl_all_scratch_hdr.pack(fill="x", padx=2, pady=(0, 2))

        self.txt_mtl_all_scratchpad = self._tag_role(
            tk.Text(
                pane,
                wrap="word",
                height=4,
                undo=True,
                font=("Segoe UI", 9),
                bg=t["bg_editor"],
                fg=editor_fg,
                insertbackground=t["misora_pink"],
                bd=1,
                relief="solid",
                padx=5,
                pady=4,
            ),
            "entry_editor",
        )
        self.txt_mtl_all_scratchpad.pack(fill="x", padx=2, pady=(0, 2))

        def _local_all_undo(_event=None):
            try:
                self.txt_mtl_all_scratchpad.edit_undo()
            except tk.TclError:
                pass
            return "break"

        def _local_all_redo(_event=None):
            try:
                self.txt_mtl_all_scratchpad.edit_redo()
            except tk.TclError:
                pass
            return "break"

        self.txt_mtl_all_scratchpad.bind("<Control-z>", _local_all_undo)
        self.txt_mtl_all_scratchpad.bind("<Control-Z>", _local_all_undo)
        self.txt_mtl_all_scratchpad.bind("<Control-y>", _local_all_redo)
        self.txt_mtl_all_scratchpad.bind("<Control-Y>", _local_all_redo)
        self.txt_mtl_all_scratchpad.bind("<Control-Shift-z>", _local_all_redo)
        self.txt_mtl_all_scratchpad.bind("<Control-Shift-Z>", _local_all_redo)

        self._apply_mtl_all_script_theme_tags()

    def _apply_mtl_all_script_theme_tags(self) -> None:
        """Configure the 5 static theme-aware status tags and block tags on All Script widgets."""
        if not hasattr(self, "txt_mtl_all_list") or not self.txt_mtl_all_list.winfo_exists():
            return
        t = self.theme
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        hl_fg = best_contrast_fg(t["highlight_bg"], t["fg_text"], "#ffffff")

        self.txt_mtl_all_list.configure(bg=t["bg_editor"], fg=editor_fg)
        self.txt_mtl_all_list.tag_configure("mtl_status_ready", foreground=t.get("accent_green", t["misora_pink"]), font=("Segoe UI", 9, "bold"))
        self.txt_mtl_all_list.tag_configure("mtl_status_translating", foreground=t.get("accent_blue", t["misora_pink"]), font=("Segoe UI", 9, "bold"))
        self.txt_mtl_all_list.tag_configure("mtl_status_error", foreground=t.get("accent_red", t["accent_yellow"]), font=("Segoe UI", 9, "bold"))
        self.txt_mtl_all_list.tag_configure("mtl_status_locked", foreground=t["fg_muted"], font=("Segoe UI", 9, "bold"))
        self.txt_mtl_all_list.tag_configure("mtl_status_empty", foreground=t["fg_muted"], font=("Segoe UI", 9))

        self.txt_mtl_all_list.tag_configure("mtl_block_header", foreground=t["misora_pink"], font=("Segoe UI", 9, "bold"))
        self.txt_mtl_all_list.tag_configure("mtl_block_src", foreground=t["fg_muted"], font=("Segoe UI", 8))
        self.txt_mtl_all_list.tag_configure("mtl_block_tr", foreground=editor_fg, font=("Segoe UI", 9))
        self.txt_mtl_all_list.tag_configure("mtl_block_selected", background=t["highlight_bg"], foreground=hl_fg)

        if hasattr(self, "txt_mtl_all_scratchpad") and self.txt_mtl_all_scratchpad.winfo_exists():
            self.txt_mtl_all_scratchpad.configure(bg=t["bg_editor"], fg=editor_fg, insertbackground=t["misora_pink"])

    def _set_mtl_drawer_mode(self, mode: str) -> None:
        if mode == "all_script":
            self._mtl_drawer_mode = "all_script"
            if hasattr(self, "btn_mtl_mode_dialogue"):
                self.btn_mtl_mode_dialogue.configure(style="TButton")
            if hasattr(self, "btn_mtl_mode_all_script"):
                self.btn_mtl_mode_all_script.configure(style="Pink.TButton")
            if hasattr(self, "btn_mtl_refresh_all") and self._is_widget_packed(self.btn_mtl_refresh_all):
                self.btn_mtl_refresh_all.pack_forget()
            for w_name in ("_mtl_dialogue_ctx_bar", "_mtl_dialogue_wrap"):
                w = getattr(self, w_name, None)
                if w is not None and w.winfo_exists() and self._is_widget_packed(w):
                    w.pack_forget()
            body = getattr(self, "mtl_cards_body", None)
            if body is not None and body.winfo_exists():
                for child in list(body.winfo_children()):
                    child.destroy()
            if hasattr(self, "_mtl_drawer_cards") and isinstance(self._mtl_drawer_cards, dict):
                self._mtl_drawer_cards.clear()
            if hasattr(self, "mtl_all_script_frame") and self.mtl_all_script_frame.winfo_exists():
                if not self._is_widget_packed(self.mtl_all_script_frame):
                    self.mtl_all_script_frame.pack(fill="both", expand=True, padx=4, pady=(0, 6))
            self._refresh_mtl_drawer_box()
            return

        self._flush_mtl_all_scratchpad()
        if hasattr(self, "_cancel_mtl_all_batch"):
            self._cancel_mtl_all_batch()
        self._mtl_drawer_mode = "dialogue"
        if hasattr(self, "btn_mtl_mode_dialogue"):
            self.btn_mtl_mode_dialogue.configure(style="Pink.TButton")
        if hasattr(self, "btn_mtl_mode_all_script"):
            self.btn_mtl_mode_all_script.configure(style="TButton")
        if hasattr(self, "mtl_all_script_frame") and self.mtl_all_script_frame.winfo_exists():
            if self._is_widget_packed(self.mtl_all_script_frame):
                self.mtl_all_script_frame.pack_forget()
        if hasattr(self, "btn_mtl_refresh_all") and not self._is_widget_packed(self.btn_mtl_refresh_all):
            self.btn_mtl_refresh_all.pack(side="right")
        if hasattr(self, "_mtl_dialogue_ctx_bar") and not self._is_widget_packed(self._mtl_dialogue_ctx_bar):
            self._mtl_dialogue_ctx_bar.pack(fill="x", padx=6, pady=(0, 4))
        if hasattr(self, "_mtl_dialogue_wrap") and not self._is_widget_packed(self._mtl_dialogue_wrap):
            self._mtl_dialogue_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self._rebuild_mtl_drawer_cards()

    def _set_mtl_drawer_engine_enabled(self, engine_name: str, enabled: bool) -> None:
        if engine_name not in self._MTL_DRAWER_ENGINE_ORDER:
            return
        self._mtl_drawer_enabled_engines[engine_name] = bool(enabled)
        if engine_name in self._mtl_drawer_engine_vars:
            self._mtl_drawer_engine_vars[engine_name].set(bool(enabled))
        self._rebuild_mtl_drawer_cards()
        self._save_user_prefs(silent=True)

    def _on_mtl_drawer_engine_toggled(self, engine_name: str) -> None:
        var = self._mtl_drawer_engine_vars.get(engine_name)
        if var is not None:
            self._mtl_drawer_enabled_engines[engine_name] = bool(var.get())
        self._rebuild_mtl_drawer_cards()
        self._save_user_prefs(silent=True)

    def _rebuild_mtl_drawer_cards(self) -> None:
        """Rebuild vertical card stack strictly for currently enabled engines."""
        body = getattr(self, "mtl_cards_body", None)
        if body is None or not body.winfo_exists():
            return
        for child in list(body.winfo_children()):
            child.destroy()
        self._mtl_drawer_cards.clear()

        t = self.theme
        editor_fg = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        enabled_engines = [e for e in self._MTL_DRAWER_ENGINE_ORDER if self._mtl_drawer_enabled_engines.get(e, False)]

        if not enabled_engines:
            self._tag_role(
                tk.Label(
                    body,
                    text="No engines enabled. Enable engines in Translator > Enabled Engines.",
                    bg=t["bg_panel"],
                    fg=t["fg_muted"],
                    wraplength=260,
                    justify="left",
                ),
                "label_muted",
            ).pack(fill="x", padx=8, pady=12)
            return

        for eng in enabled_engines:
            card = self._tag_role(
                tk.Frame(
                    body,
                    bg=t["bg_panel"],
                    bd=1,
                    relief="solid",
                    highlightbackground=t["border"],
                    highlightthickness=1,
                ),
                "panel_box",
            )
            card.pack(fill="x", padx=6, pady=4)

            card_hdr = self._tag_role(tk.Frame(card, bg=t["bg_panel"]), "panel")
            card_hdr.pack(fill="x", padx=6, pady=(4, 2))

            btn_apply = ttk.Button(
                card_hdr,
                text="←",
                style="Pink.TButton",
                width=3,
                command=lambda e=eng: self._on_mtl_drawer_apply_engine(e),
            )
            btn_apply.pack(side="left", padx=(0, 6))
            create_tooltip(btn_apply, f"Apply {eng} translation to active box (preserves whitespace)")

            lbl_engine = self._tag_role(
                tk.Label(card_hdr, text=eng, bg=t["bg_panel"], fg=t["misora_pink"], anchor="w"),
                "label_accent",
            )
            lbl_engine.pack(side="left")

            lbl_status = self._tag_role(
                tk.Label(card_hdr, text="Ready", bg=t["bg_panel"], fg=t["fg_muted"], anchor="w"),
                "label_muted",
            )
            lbl_status.pack(side="left", padx=(6, 4), fill="x", expand=True)

            ico_ref = getattr(self, "ico_refresh", None)
            btn_refresh = ttk.Button(
                card_hdr,
                text="↻",
                image=ico_ref,
                compound="none" if ico_ref else "left",
                style="Small.TButton",
                width=3,
                command=lambda e=eng: self._on_mtl_drawer_refresh_engine(e),
            )
            btn_refresh.pack(side="right", padx=(2, 0))
            create_tooltip(btn_refresh, f"Refresh {eng} (bypass session cache)")

            scratch = self._tag_role(
                tk.Text(
                    card,
                    wrap="word",
                    height=3,
                    undo=True,
                    font=("Segoe UI", 9),
                    bg=t["bg_editor"],
                    fg=editor_fg,
                    insertbackground=t["misora_pink"],
                    bd=1,
                    relief="solid",
                    padx=5,
                    pady=4,
                ),
                "entry_editor",
            )
            scratch.pack(fill="x", padx=6, pady=(0, 6))

            # Isolate scratchpad from MisoraShortcuts and keep Ctrl+Z/Y strictly local
            def _local_undo(_event=None, w=scratch):
                try:
                    w.edit_undo()
                except tk.TclError:
                    pass
                return "break"

            def _local_redo(_event=None, w=scratch):
                try:
                    w.edit_redo()
                except tk.TclError:
                    pass
                return "break"

            scratch.bind("<Control-z>", _local_undo)
            scratch.bind("<Control-Z>", _local_undo)
            scratch.bind("<Control-y>", _local_redo)
            scratch.bind("<Control-Y>", _local_redo)
            scratch.bind("<Control-Shift-z>", _local_redo)
            scratch.bind("<Control-Shift-Z>", _local_redo)

            self._mtl_drawer_cards[eng] = {
                "frame": card,
                "lbl_engine": lbl_engine,
                "lbl_status": lbl_status,
                "btn_refresh": btn_refresh,
                "btn_apply": btn_apply,
                "scratchpad": scratch,
            }

        self._mtl_drawer_active_context = None
        self._refresh_mtl_drawer_box()

    def _get_mtl_drawer_active_box(self) -> Optional[Tuple[int, Box]]:
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes or getattr(self, "is_box0_active", False):
            return None
        b_idx = getattr(self, "current_box_idx", 0)
        if b_idx < 0 or b_idx >= len(doc.boxes):
            return None
        return b_idx, doc.boxes[b_idx]

    def _refresh_mtl_drawer_box(self) -> None:
        """Sync MTL drawer box header, source preview, and cached scratchpads with active box."""
        if getattr(self, "_mtl_drawer_mode", "dialogue") == "all_script":
            if hasattr(self, "_refresh_mtl_all_script_view"):
                self._refresh_mtl_all_script_view()
            return
        if not hasattr(self, "lbl_mtl_box_info") or not self.lbl_mtl_box_info.winfo_exists():
            return
        active = self._get_mtl_drawer_active_box()
        if active is None:
            self._mtl_drawer_active_context = None
            if getattr(self, "is_box0_active", False) and self.current_doc:
                self.lbl_mtl_box_info.config(text=f"Box 0 / {len(self.current_doc.boxes)} (Metadata)")
                self.lbl_mtl_source_preview.config(text="Select a dialogue box to translate.")
            else:
                self.lbl_mtl_box_info.config(text="Box 0 / 0")
                self.lbl_mtl_source_preview.config(text="Open a story document to translate.")
            for card in self._mtl_drawer_cards.values():
                w = card["scratchpad"]
                if w.winfo_exists():
                    w.delete("1.0", tk.END)
                    w.edit_reset()
                if card["lbl_status"].winfo_exists():
                    card["lbl_status"].config(text="Ready")
            return

        b_idx, box = active
        total = len(self.current_doc.boxes)
        speaker = box.speaker or "(Narration)"
        self.lbl_mtl_box_info.config(text=f"Box {b_idx + 1} / {total} — {speaker}")
        preview = box.clean_text.replace("\n", " ")
        if len(preview) > 140:
            preview = preview[:137] + "..."
        self.lbl_mtl_source_preview.config(text=preview or "(Empty dialogue)")

        src_hash = _hash_mtl_source(box.clean_text)
        new_ctx = (str(self.current_file_path or ""), id(self.current_doc), _get_box_uid(box), src_hash)
        if new_ctx == getattr(self, "_mtl_drawer_active_context", None):
            return
        self._mtl_drawer_active_context = new_ctx

        for eng, card in self._mtl_drawer_cards.items():
            w = card["scratchpad"]
            lbl = card["lbl_status"]
            if not w.winfo_exists():
                continue
            cache_key = (eng, src_hash)
            w.delete("1.0", tk.END)
            if cache_key in self._mtl_drawer_cache:
                self._mtl_drawer_cache.move_to_end(cache_key)
                w.insert("1.0", self._mtl_drawer_cache[cache_key])
                if lbl.winfo_exists():
                    lbl.config(text="Cached")
            else:
                if lbl.winfo_exists():
                    lbl.config(text="Ready")
            w.edit_reset()

    def _mtl_drawer_cache_put(self, engine_name: str, src_hash: str, result: str) -> None:
        key = (engine_name, src_hash)
        self._mtl_drawer_cache[key] = result
        self._mtl_drawer_cache.move_to_end(key)
        while len(self._mtl_drawer_cache) > self._MTL_DRAWER_CACHE_MAX:
            self._mtl_drawer_cache.popitem(last=False)

    def _on_mtl_drawer_refresh_all(self) -> None:
        """Refresh all enabled engines for active box, using cache and confirming paid APIs."""
        active = self._get_mtl_drawer_active_box()
        if active is None:
            self.show_toast("Select a dialogue box to translate.")
            return
        _b_idx, box = active
        orig_text = box.clean_text
        if not orig_text.strip():
            self.show_toast("Current box has no text to translate.")
            return

        src_hash = _hash_mtl_source(orig_text)
        enabled = [e for e in self._MTL_DRAWER_ENGINE_ORDER if self._mtl_drawer_enabled_engines.get(e, False)]
        if not enabled:
            self.show_toast("No MTL engines enabled.")
            return

        paid_uncached = [
            e for e in enabled
            if e in self._MTL_DRAWER_PAID_ENGINES and (e, src_hash) not in self._mtl_drawer_cache
        ]
        allow_paid = True
        if paid_uncached:
            allow_paid = bool(
                messagebox.askyesno(
                    "Confirm Paid API Batch Call",
                    f"Refresh All will call paid API(s): {', '.join(paid_uncached)}.\n\nContinue?",
                    parent=self,
                )
            )

        for eng in enabled:
            if eng in self._MTL_DRAWER_PAID_ENGINES and (eng, src_hash) not in self._mtl_drawer_cache and not allow_paid:
                card = self._mtl_drawer_cards.get(eng)
                if card and card["lbl_status"].winfo_exists():
                    card["lbl_status"].config(text="Skipped (paid)")
                continue
            self._dispatch_mtl_drawer_engine(eng, bypass_cache=False)

    def _on_mtl_drawer_refresh_engine(self, engine_name: str) -> None:
        """Per-card Refresh: bypasses session cache for the specified engine."""
        self._dispatch_mtl_drawer_engine(engine_name, bypass_cache=True)

    def _dispatch_mtl_drawer_engine(self, engine_name: str, bypass_cache: bool = False) -> None:
        active = self._get_mtl_drawer_active_box()
        if active is None:
            self.show_toast("Select a dialogue box to translate.")
            return
        _b_idx, box = active
        orig_text = box.clean_text
        if not orig_text.strip():
            self.show_toast("Current box has no text to translate.")
            return

        src_hash = _hash_mtl_source(orig_text)
        card = self._mtl_drawer_cards.get(engine_name)

        if not bypass_cache and (engine_name, src_hash) in self._mtl_drawer_cache:
            self._mtl_drawer_cache.move_to_end((engine_name, src_hash))
            cached_val = self._mtl_drawer_cache[(engine_name, src_hash)]
            if card:
                if card["scratchpad"].winfo_exists():
                    card["scratchpad"].delete("1.0", tk.END)
                    card["scratchpad"].insert("1.0", cached_val)
                    card["scratchpad"].edit_reset()
                if card["lbl_status"].winfo_exists():
                    card["lbl_status"].config(text="Cached")
            return

        if card and card["lbl_status"].winfo_exists():
            card["lbl_status"].config(text="Translating...")

        self._mtl_drawer_req_seq += 1
        req_seq = self._mtl_drawer_req_seq
        self._mtl_drawer_latest_seq[engine_name] = req_seq

        cfg = MTLConfig.from_dict(self.mtl_config.to_dict())
        cfg.active_engine = engine_name
        cfg.protect_tags = True

        req_meta = (
            str(self.current_file_path or ""),
            id(self.current_doc),
            _get_box_uid(box),
            src_hash,
            req_seq,
            engine_name,
        )

        self._mtl_drawer_pending += 1
        translate_async(
            orig_text,
            cfg,
            out_queue=self._mtl_drawer_queue,
            metadata=req_meta,
            xuat_cache=getattr(self, "xuat_entries", None),
        )
        if self._mtl_drawer_poll_id is None and self.winfo_exists():
            self._mtl_drawer_poll_id = self.after(50, self._poll_mtl_drawer_queue)

    def _poll_mtl_drawer_queue(self) -> None:
        """Poll MTL drawer worker results on the Tk main thread (BUG-27, Rule 15)."""
        self._mtl_drawer_poll_id = None
        if not self.winfo_exists() or getattr(self, "_destroyed", False):
            return

        try:
            while True:
                msg = self._mtl_drawer_queue.get_nowait()
                self._mtl_drawer_pending = max(0, self._mtl_drawer_pending - 1)
                if not isinstance(msg, tuple) or len(msg) < 3:
                    continue
                kind, req_meta, payload = msg[0], msg[1], msg[2]
                if not isinstance(req_meta, tuple) or len(req_meta) < 6:
                    continue
                file_p, doc_id, b_uid, src_hash, req_seq, eng = req_meta[:6]
                mode_tag = req_meta[6] if len(req_meta) >= 7 else "dialogue"

                # Stale identity guard: discard if document, path, openness, or batch generation changed (BUG-03 / BONUS-01)
                if not self.current_doc or id(self.current_doc) != doc_id:
                    continue
                if str(self.current_file_path or "") != file_p:
                    continue
                if file_p and getattr(self, "open_documents", None):
                    resolved_fp = Path(file_p).resolve()
                    if resolved_fp not in self.open_documents:
                        continue

                if mode_tag == "all_script":
                    batch_gen = req_meta[7] if len(req_meta) >= 8 else None
                    if batch_gen is not None and batch_gen != getattr(self, "_mtl_all_batch_gen", 0):
                        continue
                    target_box = None
                    for b in self.current_doc.boxes:
                        if _get_box_uid(b) == b_uid:
                            target_box = b
                            break
                    if target_box is None:
                        continue
                    if _hash_mtl_source(target_box.clean_text) != src_hash:
                        continue
                    if req_seq < self._mtl_all_req_seqs.get((b_uid, eng), 0):
                        continue

                    ctx_key = (file_p, doc_id, b_uid, eng)
                    if kind == "success":
                        self._mtl_drawer_cache_put(eng, src_hash, payload)
                        self._mtl_all_results[ctx_key] = payload
                        self._mtl_all_statuses[ctx_key] = "ready"
                        self._mtl_all_errors.pop(ctx_key, None)
                        if (
                            b_uid == getattr(self, "_mtl_all_selected_uid", None)
                            and hasattr(self, "var_mtl_all_engine")
                            and self.var_mtl_all_engine.get() == eng
                        ):
                            self._load_mtl_all_scratchpad(force_text=payload)
                    elif kind == "error":
                        self._mtl_all_statuses[ctx_key] = "error"
                        self._mtl_all_errors[ctx_key] = str(payload)
                    if getattr(self, "_mtl_drawer_mode", "dialogue") == "all_script":
                        self._refresh_mtl_all_script_view(preserve_scroll=True)
                    continue

                active = self._get_mtl_drawer_active_box()
                if active is None:
                    continue
                _b_idx, curr_box = active
                if _get_box_uid(curr_box) != b_uid:
                    continue
                if _hash_mtl_source(curr_box.clean_text) != src_hash:
                    continue
                if req_seq < self._mtl_drawer_latest_seq.get(eng, 0):
                    continue

                card = self._mtl_drawer_cards.get(eng)
                if kind == "success":
                    self._mtl_drawer_cache_put(eng, src_hash, payload)
                    if card:
                        if card["scratchpad"].winfo_exists():
                            card["scratchpad"].delete("1.0", tk.END)
                            card["scratchpad"].insert("1.0", payload)
                            card["scratchpad"].edit_reset()
                        if card["lbl_status"].winfo_exists():
                            card["lbl_status"].config(text="✓ Ready")
                elif kind == "error":
                    if card and card["lbl_status"].winfo_exists():
                        card["lbl_status"].config(text=f"Error: {str(payload)[:40]}")
        except queue.Empty:
            pass

        if (self._mtl_drawer_pending > 0 or not self._mtl_drawer_queue.empty()) and self.winfo_exists() and not getattr(self, "_destroyed", False):
            self._mtl_drawer_poll_id = self.after(50, self._poll_mtl_drawer_queue)

    def _on_mtl_drawer_apply_engine(self, engine_name: str) -> bool:
        """Apply a card's scratchpad text to the active box (enforces lock, preserves whitespace)."""
        active = self._get_mtl_drawer_active_box()
        if active is None:
            self.show_toast("Select a dialogue box before applying translation.")
            return False
        b_idx, old_box = active

        if self.is_box_locked(b_idx):
            self.show_toast(f"🔒 Box {b_idx + 1} is locked against translation.")
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=f"Box {b_idx + 1} is locked against translation.")
            return False

        card = self._mtl_drawer_cards.get(engine_name)
        if not card or not card["scratchpad"].winfo_exists():
            return False

        new_text = card["scratchpad"].get("1.0", "end-1c")
        old_sp = old_box.speaker
        old_tx = old_box.clean_text
        box_uid = _get_box_uid(old_box)
        old_segs = [s.text for s in old_box.segs]

        try:
            self.current_doc.inject_box(b_idx, old_sp, new_text)
        except Exception as exc:
            self.logger.exception(f"MTL drawer apply failed for box {b_idx}:", exc)
            self.set_status(f"Error applying translation to Box #{b_idx + 1}: {exc}", is_error=True)
            return False

        new_segs = [s.text for s in self.current_doc.boxes[b_idx].segs]
        self.undo_journal.record(
            BoxEditDelta(
                box_index=b_idx,
                old_speaker=old_sp,
                new_speaker=old_sp,
                old_text=old_tx,
                new_text=new_text,
                file_path=str(self.current_file_path) if self.current_file_path else "",
                box_uid=box_uid,
                source="mtl",
                old_seg_texts=old_segs,
                new_seg_texts=new_segs,
            )
        )
        self._modified_boxes.add(b_idx)
        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()
        self.show_toast(f"✓ Applied {engine_name} translation to Box {b_idx + 1}")
        return True

    # -------------------------------------------------------------------------
    # Docked Right-Side MTL Drawer — All Script Mode Helpers (FEAT-13)
    # -------------------------------------------------------------------------
    @staticmethod
    def _is_mtl_empty_or_punct(text: str) -> bool:
        """Return True if text is empty or contains only whitespace/punctuation."""
        if not text or not text.strip():
            return True
        for ch in text:
            if ch.isalnum():
                return False
        return True

    def _mtl_all_ctx_key(self, box_uid: Any, engine_name: Optional[str] = None) -> Tuple[str, int, Any, str]:
        eng = engine_name or (self.var_mtl_all_engine.get() if hasattr(self, "var_mtl_all_engine") else "Google")
        return (str(self.current_file_path or ""), id(self.current_doc), box_uid, eng)

    def _find_box_index_by_uid(self, box_uid: Any) -> Optional[Tuple[int, Box]]:
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes:
            return None
        for idx, b in enumerate(doc.boxes):
            if _get_box_uid(b) == box_uid:
                return idx, b
        return None

    def _flush_mtl_all_scratchpad(self) -> None:
        """Persist current scratchpad text into document-scoped in-memory map before switching/applying."""
        if not hasattr(self, "txt_mtl_all_scratchpad") or not self.txt_mtl_all_scratchpad.winfo_exists():
            return
        last_ctx = getattr(self, "_mtl_all_last_ctx", None)
        if last_ctx is None:
            return
        _fp, doc_id, b_uid, eng = last_ctx
        if not self.current_doc or id(self.current_doc) != doc_id or b_uid is None:
            return
        text = self.txt_mtl_all_scratchpad.get("1.0", "end-1c")
        if last_ctx in self._mtl_all_results or text != "":
            self._mtl_all_results[last_ctx] = text
            if self._mtl_all_statuses.get(last_ctx) not in ("locked", "translating"):
                if text != "":
                    self._mtl_all_statuses[last_ctx] = "ready"

    def _load_mtl_all_scratchpad(self, force_text: Optional[str] = None) -> None:
        """Load selected box's translation into the shared bottom scratchpad."""
        if not hasattr(self, "txt_mtl_all_scratchpad") or not self.txt_mtl_all_scratchpad.winfo_exists():
            return
        doc = getattr(self, "current_doc", None)
        b_uid = getattr(self, "_mtl_all_selected_uid", None)
        eng = self.var_mtl_all_engine.get() if hasattr(self, "var_mtl_all_engine") else "Google"

        if not doc or not doc.boxes or b_uid is None:
            self._mtl_all_last_ctx = None
            if hasattr(self, "lbl_mtl_all_scratch_hdr") and self.lbl_mtl_all_scratch_hdr.winfo_exists():
                self.lbl_mtl_all_scratch_hdr.config(text="Scratchpad (No box selected)")
            self.txt_mtl_all_scratchpad.delete("1.0", tk.END)
            self.txt_mtl_all_scratchpad.edit_reset()
            return

        found = self._find_box_index_by_uid(b_uid)
        if found is None:
            self._mtl_all_last_ctx = None
            self.txt_mtl_all_scratchpad.delete("1.0", tk.END)
            self.txt_mtl_all_scratchpad.edit_reset()
            return

        b_idx, box = found
        ctx = self._mtl_all_ctx_key(b_uid, eng)
        self._mtl_all_last_ctx = ctx
        if hasattr(self, "lbl_mtl_all_scratch_hdr") and self.lbl_mtl_all_scratch_hdr.winfo_exists():
            sp = box.speaker or "(Narration)"
            self.lbl_mtl_all_scratch_hdr.config(text=f"Scratchpad — Box #{b_idx + 1} ({sp}) [{eng}]")

        if force_text is not None:
            val = force_text
        elif ctx in self._mtl_all_results:
            val = self._mtl_all_results[ctx]
        else:
            src_hash = _hash_mtl_source(box.clean_text)
            val = self._mtl_drawer_cache.get((eng, src_hash), "")

        self.txt_mtl_all_scratchpad.delete("1.0", tk.END)
        if val:
            self.txt_mtl_all_scratchpad.insert("1.0", val)
        self.txt_mtl_all_scratchpad.edit_reset()

    def _cancel_mtl_all_batch(self) -> None:
        """Cooperatively cancel any in-flight All Script Translate All batch and shut down its executor.

        Note: Blocking urllib socket reads already in flight cannot always be forcefully killed
        mid-flight; pending queued items abort immediately, no new requests start, and any late
        in-flight reply is discarded by batch_gen/doc_id/req_seq guards on arrival.
        """
        self._mtl_all_batch_gen = getattr(self, "_mtl_all_batch_gen", 0) + 1
        cancel_ev = getattr(self, "_mtl_all_batch_cancel", None)
        if cancel_ev is not None:
            try:
                cancel_ev.set()
            except Exception:
                pass
        executor = getattr(self, "_mtl_all_executor", None)
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._mtl_all_executor = None

    def _on_mtl_all_engine_changed(self, _event=None) -> None:
        self._flush_mtl_all_scratchpad()
        self._cancel_mtl_all_batch()
        self._refresh_mtl_all_script_view()

    def _on_mtl_all_list_click(self, event: tk.Event) -> str:
        """Select clicked box block in txt_mtl_all_list and sync bottom scratchpad."""
        if not hasattr(self, "txt_mtl_all_list") or not self.txt_mtl_all_list.winfo_exists():
            return "break"
        try:
            idx_str = self.txt_mtl_all_list.index(f"@{event.x},{event.y}")
            clicked_line = int(idx_str.split(".")[0])
        except Exception:
            return "break"

        target_uid = None
        for start_l, end_l, b_uid in getattr(self, "_mtl_all_block_ranges", []):
            if start_l <= clicked_line <= end_l:
                target_uid = b_uid
                break

        if target_uid is not None and target_uid != self._mtl_all_selected_uid:
            self._flush_mtl_all_scratchpad()
            self._mtl_all_selected_uid = target_uid
            self._refresh_mtl_all_script_view(preserve_scroll=True)
        return "break"

    def _refresh_mtl_all_script_view(self, preserve_scroll: bool = False) -> None:
        """Render all boxes as non-truncated multi-line blocks in txt_mtl_all_list."""
        if not hasattr(self, "txt_mtl_all_list") or not self.txt_mtl_all_list.winfo_exists():
            return

        y_frac = 0.0
        if preserve_scroll:
            try:
                y_frac = self.txt_mtl_all_list.yview()[0]
            except Exception:
                y_frac = 0.0

        doc = getattr(self, "current_doc", None)
        eng = self.var_mtl_all_engine.get() if hasattr(self, "var_mtl_all_engine") else "Google"
        self._mtl_all_block_ranges = []

        self.txt_mtl_all_list.config(state="normal")
        try:
            self.txt_mtl_all_list.delete("1.0", tk.END)
            if not doc or not doc.boxes:
                msg = "Open a story document to translate." if not doc else "Story document has 0 dialogue boxes."
                self.txt_mtl_all_list.insert("1.0", msg, ("mtl_status_empty",))
                self._mtl_all_selected_uid = None
                self._load_mtl_all_scratchpad()
                return

            valid_uids = [_get_box_uid(b) for b in doc.boxes]
            if self._mtl_all_selected_uid not in valid_uids:
                active_idx = max(0, min(getattr(self, "current_box_idx", 0), len(doc.boxes) - 1))
                self._mtl_all_selected_uid = valid_uids[active_idx]

            status_meta = {
                "ready": ("✓", "mtl_status_ready"),
                "translating": ("⏳", "mtl_status_translating"),
                "error": ("⚠", "mtl_status_error"),
                "locked": ("🔒", "mtl_status_locked"),
                "empty": ("-", "mtl_status_empty"),
            }

            for idx, box in enumerate(doc.boxes):
                b_uid = valid_uids[idx]
                ctx = self._mtl_all_ctx_key(b_uid, eng)
                src_text = box.clean_text
                src_hash = _hash_mtl_source(src_text)

                if self.is_box_locked(idx):
                    st_key = "locked"
                elif ctx in self._mtl_all_statuses:
                    st_key = self._mtl_all_statuses[ctx]
                elif ctx in self._mtl_all_results or (eng, src_hash) in self._mtl_drawer_cache:
                    st_key = "ready"
                else:
                    st_key = "empty"

                icon, st_tag = status_meta.get(st_key, ("-", "mtl_status_empty"))
                start_line = int(self.txt_mtl_all_list.index("end-1c").split(".")[0])

                speaker = box.speaker or "(Narration)"
                self.txt_mtl_all_list.insert(tk.END, f"{icon} ", (st_tag,))
                hdr_tags = ("mtl_block_header", "mtl_block_selected") if b_uid == self._mtl_all_selected_uid else ("mtl_block_header",)
                self.txt_mtl_all_list.insert(tk.END, f"Box #{idx + 1} — {speaker}\n", hdr_tags)

                # Full multi-line JP source (no single-line truncation)
                self.txt_mtl_all_list.insert(tk.END, (src_text if src_text else "(Empty)") + "\n", ("mtl_block_src",))

                tr_val = self._mtl_all_results.get(ctx)
                if tr_val is None and st_key == "ready":
                    tr_val = self._mtl_drawer_cache.get((eng, src_hash))
                if tr_val:
                    self.txt_mtl_all_list.insert(tk.END, f"→ {tr_val}\n", ("mtl_block_tr",))
                elif st_key == "error":
                    err_msg = self._mtl_all_errors.get(ctx, "Translation failed")
                    self.txt_mtl_all_list.insert(tk.END, f"⚠ {err_msg}\n", ("mtl_status_error",))

                end_line = int(self.txt_mtl_all_list.index("end-1c").split(".")[0]) - 1
                self._mtl_all_block_ranges.append((start_line, max(start_line, end_line), b_uid))
                self.txt_mtl_all_list.insert(tk.END, "\n")

            if preserve_scroll:
                self.txt_mtl_all_list.yview_moveto(y_frac)
        finally:
            self.txt_mtl_all_list.config(state="disabled")

        self._load_mtl_all_scratchpad()

    def _dispatch_mtl_all_box(self, box_idx: int, box: Box, eng: str, bypass_cache: bool = False) -> bool:
        """Dispatch translate_async for a single box in All Script mode, returning True if worker started."""
        b_uid = _get_box_uid(box)
        ctx = self._mtl_all_ctx_key(b_uid, eng)
        orig_text = box.clean_text

        if self.is_box_locked(box_idx):
            self._mtl_all_statuses[ctx] = "locked"
            return False
        if self._is_mtl_empty_or_punct(orig_text):
            self._mtl_all_statuses[ctx] = "empty"
            return False

        src_hash = _hash_mtl_source(orig_text)
        if not bypass_cache and (eng, src_hash) in self._mtl_drawer_cache:
            self._mtl_drawer_cache.move_to_end((eng, src_hash))
            self._mtl_all_results[ctx] = self._mtl_drawer_cache[(eng, src_hash)]
            self._mtl_all_statuses[ctx] = "ready"
            return False

        self._mtl_all_statuses[ctx] = "translating"
        self._mtl_drawer_req_seq += 1
        req_seq = self._mtl_drawer_req_seq
        self._mtl_all_req_seqs[(b_uid, eng)] = req_seq

        cfg = MTLConfig.from_dict(self.mtl_config.to_dict())
        cfg.active_engine = eng
        cfg.protect_tags = True

        req_meta = (
            str(self.current_file_path or ""),
            id(self.current_doc),
            b_uid,
            src_hash,
            req_seq,
            eng,
            "all_script",
        )
        self._mtl_drawer_pending += 1
        translate_async(
            orig_text,
            cfg,
            out_queue=self._mtl_drawer_queue,
            metadata=req_meta,
            xuat_cache=getattr(self, "xuat_entries", None),
        )
        if self._mtl_drawer_poll_id is None and self.winfo_exists():
            self._mtl_drawer_poll_id = self.after(50, self._poll_mtl_drawer_queue)
        return True

    def _on_mtl_all_script_refresh_selected(self) -> None:
        """Refresh the currently selected box in All Script mode (bypasses session cache)."""
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes:
            self.show_toast("Open a story document to translate.")
            return
        found = self._find_box_index_by_uid(getattr(self, "_mtl_all_selected_uid", None))
        if found is None:
            self.show_toast("Select a box in the list to refresh.")
            return
        b_idx, box = found
        if self.is_box_locked(b_idx):
            self.show_toast(f"🔒 Box {b_idx + 1} is locked against translation.")
            return
        eng = self.var_mtl_all_engine.get()
        self._dispatch_mtl_all_box(b_idx, box, eng, bypass_cache=True)
        self._refresh_mtl_all_script_view(preserve_scroll=True)

    def _on_mtl_all_script_apply_selected(self) -> bool:
        """Apply scratchpad text to the selected box by box.uid (enforces lock, preserves whitespace)."""
        self._flush_mtl_all_scratchpad()
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes:
            self.show_toast("Open a story document first.")
            return False
        found = self._find_box_index_by_uid(getattr(self, "_mtl_all_selected_uid", None))
        if found is None:
            self.show_toast("Select a box before applying translation.")
            return False
        b_idx, old_box = found
        if self.is_box_locked(b_idx):
            self.show_toast(f"🔒 Box {b_idx + 1} is locked against translation.")
            return False

        new_text = self.txt_mtl_all_scratchpad.get("1.0", "end-1c")
        old_sp = old_box.speaker
        old_tx = old_box.clean_text
        box_uid = _get_box_uid(old_box)
        old_segs = [s.text for s in old_box.segs]

        try:
            doc.inject_box(b_idx, old_sp, new_text)
        except Exception as exc:
            self.logger.exception(f"All Script Apply Selected failed for box {b_idx}:", exc)
            self.set_status(f"Error applying translation to Box #{b_idx + 1}: {exc}", is_error=True)
            return False

        new_segs = [s.text for s in doc.boxes[b_idx].segs]
        self.undo_journal.record(
            BoxEditDelta(
                box_index=b_idx,
                old_speaker=old_sp,
                new_speaker=old_sp,
                old_text=old_tx,
                new_text=new_text,
                file_path=str(self.current_file_path) if self.current_file_path else "",
                box_uid=box_uid,
                source="mtl",
                old_seg_texts=old_segs,
                new_seg_texts=new_segs,
            )
        )
        self._modified_boxes.add(b_idx)
        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()
        self.show_toast(f"✓ Applied translation to Box {b_idx + 1}")
        return True

    def _on_mtl_all_script_translate_all(self) -> None:
        """Batch-translate all unlocked, non-empty boxes using bounded workers + finite pending backpressure (BUG-02)."""
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes:
            self.show_toast("Open a story document to translate.")
            return
        eng = self.var_mtl_all_engine.get()

        if eng in self._MTL_DRAWER_PAID_ENGINES:
            uncached_count = 0
            for idx, box in enumerate(doc.boxes):
                if self.is_box_locked(idx) or self._is_mtl_empty_or_punct(box.clean_text):
                    continue
                if (eng, _hash_mtl_source(box.clean_text)) not in self._mtl_drawer_cache:
                    uncached_count += 1
            if uncached_count > 0:
                ok = messagebox.askyesno(
                    "Confirm Paid API Batch Call",
                    f"Translate All will call paid API '{eng}' for {uncached_count} uncached box(es).\n\nContinue?",
                    parent=self,
                )
                if not ok:
                    return

        self._cancel_mtl_all_batch()
        batch_cancel = threading.Event()
        self._mtl_all_batch_cancel = batch_cancel
        batch_gen = self._mtl_all_batch_gen

        file_p_str = str(self.current_file_path or "")
        doc_id = id(doc)
        xuat_cache = getattr(self, "xuat_entries", None)
        base_cfg = MTLConfig.from_dict(self.mtl_config.to_dict())
        base_cfg.active_engine = eng
        base_cfg.protect_tags = True

        tasks: List[Tuple[str, Tuple[Any, ...]]] = []
        for idx, box in enumerate(doc.boxes):
            b_uid = _get_box_uid(box)
            ctx = self._mtl_all_ctx_key(b_uid, eng)
            orig_text = box.clean_text
            if self.is_box_locked(idx):
                self._mtl_all_statuses[ctx] = "locked"
                continue
            if self._is_mtl_empty_or_punct(orig_text):
                self._mtl_all_statuses[ctx] = "empty"
                continue
            src_hash = _hash_mtl_source(orig_text)
            if (eng, src_hash) in self._mtl_drawer_cache:
                self._mtl_drawer_cache.move_to_end((eng, src_hash))
                self._mtl_all_results[ctx] = self._mtl_drawer_cache[(eng, src_hash)]
                self._mtl_all_statuses[ctx] = "ready"
                continue

            self._mtl_all_statuses[ctx] = "translating"
            self._mtl_drawer_req_seq += 1
            req_seq = self._mtl_drawer_req_seq
            self._mtl_all_req_seqs[(b_uid, eng)] = req_seq
            req_meta = (file_p_str, doc_id, b_uid, src_hash, req_seq, eng, "all_script", batch_gen)
            tasks.append((orig_text, req_meta))

        if tasks:
            self._mtl_drawer_pending += len(tasks)
            out_q = self._mtl_drawer_queue
            use_monkeypatched_async = translate_async is not _ORIG_TRANSLATE_ASYNC
            pending_sem = threading.Semaphore(8)  # Finite pending-work bound (never 100s of queued Futures)
            worker_local = threading.local()

            def _run_one(orig_text: str, req_meta: Tuple[Any, ...]) -> None:
                try:
                    if batch_cancel.is_set():
                        return
                    count = getattr(worker_local, "count", 0)
                    delay = float(getattr(base_cfg, "rate_limit_delay", 0.0) or 0.0)
                    if count > 0 and delay > 0.0:
                        if batch_cancel.wait(delay):
                            return
                    worker_local.count = count + 1
                    if use_monkeypatched_async:
                        t = translate_async(
                            orig_text,
                            base_cfg,
                            out_queue=out_q,
                            metadata=req_meta,
                            xuat_cache=xuat_cache,
                        )
                        if isinstance(t, threading.Thread) and t.is_alive():
                            t.join()
                    else:
                        try:
                            engine = MTLEngine(base_cfg)
                            res = engine.translate(orig_text, config=base_cfg, xuat_cache=xuat_cache)
                            if not batch_cancel.is_set():
                                out_q.put(("success", req_meta, res))
                        except Exception as exc:
                            if not batch_cancel.is_set():
                                out_q.put(("error", req_meta, str(exc)))
                finally:
                    pending_sem.release()

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="MisoraMTLAll")
            self._mtl_all_executor = executor

            def _dispatch_loop() -> None:
                try:
                    for orig_text, req_meta in tasks:
                        if batch_cancel.is_set():
                            break
                        while not pending_sem.acquire(timeout=0.05):
                            if batch_cancel.is_set():
                                return
                        if batch_cancel.is_set():
                            pending_sem.release()
                            break
                        try:
                            executor.submit(_run_one, orig_text, req_meta)
                        except RuntimeError:
                            pending_sem.release()
                            break
                finally:
                    try:
                        executor.shutdown(wait=False, cancel_futures=batch_cancel.is_set())
                    except Exception:
                        pass
                    if getattr(self, "_mtl_all_executor", None) is executor:
                        self._mtl_all_executor = None

            threading.Thread(target=_dispatch_loop, name="MisoraMTLDispatcher", daemon=True).start()
            if self._mtl_drawer_poll_id is None and self.winfo_exists():
                self._mtl_drawer_poll_id = self.after(50, self._poll_mtl_drawer_queue)

        self._refresh_mtl_all_script_view(preserve_scroll=True)

    def _on_mtl_all_script_apply_all(self) -> int:
        """Apply all ready/edited translations to unlocked boxes in one Undo batch."""
        self._flush_mtl_all_scratchpad()
        doc = getattr(self, "current_doc", None)
        if not doc or not doc.boxes:
            self.show_toast("Open a story document first.")
            return 0
        eng = self.var_mtl_all_engine.get()

        candidates: List[Tuple[Any, str]] = []
        for idx, box in enumerate(doc.boxes):
            if self.is_box_locked(idx):
                continue
            b_uid = _get_box_uid(box)
            ctx = self._mtl_all_ctx_key(b_uid, eng)
            st = self._mtl_all_statuses.get(ctx)
            if st in ("locked", "translating", "error"):
                continue
            tr_text = self._mtl_all_results.get(ctx)
            if tr_text is None:
                src_hash = _hash_mtl_source(box.clean_text)
                if (eng, src_hash) in self._mtl_drawer_cache:
                    tr_text = self._mtl_drawer_cache[(eng, src_hash)]
            if tr_text is None or tr_text == "":
                continue
            candidates.append((b_uid, tr_text))

        if not candidates:
            self.show_toast("No ready translations to apply.")
            return 0

        applied_count = 0
        self.undo_journal.begin_batch("MTL Apply All")
        try:
            for b_uid, new_text in candidates:
                found = self._find_box_index_by_uid(b_uid)
                if found is None:
                    continue
                b_idx, old_box = found
                if self.is_box_locked(b_idx):
                    continue
                old_sp = old_box.speaker
                old_tx = old_box.clean_text
                old_segs = [s.text for s in old_box.segs]
                try:
                    doc.inject_box(b_idx, old_sp, new_text)
                except Exception as exc:
                    self.logger.exception(f"MTL Apply All failed for box {b_idx}:", exc)
                    continue
                new_segs = [s.text for s in doc.boxes[b_idx].segs]
                self.undo_journal.record(
                    BoxEditDelta(
                        box_index=b_idx,
                        old_speaker=old_sp,
                        new_speaker=old_sp,
                        old_text=old_tx,
                        new_text=new_text,
                        file_path=str(self.current_file_path) if self.current_file_path else "",
                        box_uid=b_uid,
                        source="mtl",
                        old_seg_texts=old_segs,
                        new_seg_texts=new_segs,
                    )
                )
                self._modified_boxes.add(b_idx)
                applied_count += 1
        finally:
            self.undo_journal.end_batch()

        if applied_count > 0:
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            self._update_views()
            self.show_toast(f"✓ Applied {eng} translations to {applied_count} box(es)")
        else:
            self.show_toast("No translations were applied.")
        return applied_count

    def on_translate_current_box(self) -> None:
        """Translate the dialogue in the active box using configured active engine (F8 / Rule 15 / BUG-27)."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return
        b_idx = self.current_box_idx
        if b_idx < 0 or b_idx >= len(self.current_doc.boxes):
            return
        if self.is_box_locked(b_idx):
            self.show_toast(f"🔒 Box {b_idx + 1} is locked against translation edits.")
            return
        box = self.current_doc.boxes[b_idx]
        orig_text = box.clean_text.strip()
        if not orig_text:
            self.show_toast("Current box has no text to translate")
            return

        engine_name = self.mtl_config.active_engine
        self.show_toast(f"Translating Box {b_idx + 1} with {engine_name}...")
        self.lbl_status.config(text=f"Translating Box {b_idx + 1} with {engine_name}...")

        b_uid = _get_box_uid(box)
        doc_id = id(self.current_doc)
        file_path_str = str(self.current_file_path or "")
        src_hash = _hash_mtl_source(orig_text)
        self._mtl_request_seq += 1
        req_seq = self._mtl_request_seq
        req_meta = (file_path_str, doc_id, b_uid, src_hash, req_seq)

        mtl_q = self._mtl_queue

        def on_success(result: str):
            mtl_q.put(("box_success", req_meta, result, engine_name))

        def on_error(err: str):
            mtl_q.put(("box_error", req_meta, str(err), engine_name))

        self._mtl_pending = getattr(self, "_mtl_pending", 0) + 1
        translate_async(
            orig_text,
            self.mtl_config,
            on_success=on_success,
            on_error=on_error,
            xuat_cache=getattr(self, "xuat_entries", None),
        )
        if getattr(self, "_mtl_poll_job", None) is None and self.winfo_exists():
            self._mtl_poll_job = self.after(50, self._poll_mtl_queue)

    def _poll_mtl_queue(self) -> None:
        """Poll queued machine translation results on the main UI thread (Rule 15 / BUG-27 / BONUS-03)."""
        self._mtl_poll_job = None
        if not self.winfo_exists() or getattr(self, "_destroyed", False):
            return

        try:
            while True:
                msg = self._mtl_queue.get_nowait()
                self._mtl_pending = max(0, getattr(self, "_mtl_pending", 0) - 1)
                kind = msg[0]
                if kind in ("box_success", "success"):
                    if kind == "box_success":
                        _, req_meta, result, engine_name = msg
                    else:
                        _, req_meta, result = msg
                        engine_name = self.mtl_config.active_engine
                    file_path_str, doc_id, b_uid, src_hash, req_seq = req_meta

                    # Identity guard 1: Verify active document has not changed
                    if not self.current_doc or id(self.current_doc) != doc_id:
                        self.logger.info("MTL", f"Discarded stale MTL result for doc_id {doc_id} (active doc switched)")
                        continue
                    if str(self.current_file_path or "") != file_path_str:
                        self.logger.info("MTL", f"Discarded stale MTL result for path {file_path_str} (path changed)")
                        continue

                    # Identity guard 2: Re-resolve target box by box_uid
                    found_idx = None
                    if b_uid is not None:
                        for idx, b in enumerate(self.current_doc.boxes):
                            if _get_box_uid(b) == b_uid:
                                found_idx = idx
                                break
                    if found_idx is None:
                        self.logger.info("MTL", f"Discarded stale MTL result: box_uid {b_uid} not found in document")
                        continue

                    # Identity guard 3: Re-verify source text has not changed in flight
                    target_box = self.current_doc.boxes[found_idx]
                    curr_hash = _hash_mtl_source(target_box.clean_text)
                    if curr_hash != src_hash:
                        self.logger.info("MTL", f"Discarded stale MTL result: source text for box {found_idx + 1} changed in flight")
                        continue

                    # Identity guard 4: Re-verify box is not locked against edits
                    if self.is_box_locked(found_idx):
                        self.logger.info("MTL", f"Discarded MTL result: box {found_idx + 1} is locked")
                        continue

                    # Identity guard 5: Re-verify monotonic request sequence
                    latest_seq = self._latest_applied_mtl_seq.get(b_uid, 0)
                    if req_seq < latest_seq:
                        self.logger.info("MTL", f"Discarded superseded MTL seq {req_seq} < {latest_seq} for box {b_uid}")
                        continue
                    self._latest_applied_mtl_seq[b_uid] = req_seq

                    # Mutate AST first (S07 / BUG-13 mutate-before-undo)
                    old_speaker = target_box.speaker
                    old_text = target_box.clean_text
                    old_segs = [s.text for s in target_box.segs]
                    self.current_doc.inject_box(found_idx, old_speaker, result)
                    new_box = self.current_doc.boxes[found_idx]
                    new_segs = [s.text for s in new_box.segs]

                    self.undo_journal.record(
                        BoxEditDelta(
                            box_index=found_idx,
                            old_speaker=old_speaker,
                            new_speaker=old_speaker,
                            old_text=old_text,
                            new_text=result,
                            file_path=str(self.current_file_path) if self.current_file_path else "",
                            box_uid=b_uid,
                            source="mtl",
                            old_seg_texts=old_segs,
                            new_seg_texts=new_segs,
                        )
                    )
                    self._modified_boxes.add(found_idx)
                    self._mark_document_dirty(self.current_file_path)
                    self._dirty_state_changed()
                    self._update_views()
                    self.show_toast(f"✓ Translated Box {found_idx + 1} via {engine_name}")
                    self.lbl_status.config(text=f"Box {found_idx + 1} translated via {engine_name}")

                elif kind in ("box_error", "error"):
                    if kind == "box_error":
                        _, req_meta, err_str, engine_name = msg
                    else:
                        _, req_meta, err_str = msg
                        engine_name = self.mtl_config.active_engine
                    file_path_str, doc_id, b_uid, src_hash, req_seq = req_meta
                    if self.current_doc and id(self.current_doc) == doc_id:
                        self.logger.error("MTL", f"Translation failed via {engine_name}: {err_str}")
                        self.show_toast(f"❌ Translation failed: {err_str}")
                        self.lbl_status.config(text=f"Translation failed: {err_str}")

        except queue.Empty:
            pass
        finally:
            if (
                (getattr(self, "_mtl_pending", 0) > 0 or not self._mtl_queue.empty())
                and self.winfo_exists()
                and not getattr(self, "_destroyed", False)
            ):
                self._mtl_poll_job = self.after(50, self._poll_mtl_queue)

    def on_batch_translate(self) -> None:
        """Open automated batch translation dialog."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return
        BatchTranslateDialog(self)

    def on_copy_ai_prompt(self) -> None:
        """Export active story in CSIF format with AI system rules and delimiters (Part C.5)."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return

        self._commit_widget_edit()
        lines: List[str] = []
        if getattr(self.mtl_config, "ai_prompt_include_header", True):
            hdr = getattr(self.mtl_config, "llm_system_prompt", "").strip()
            if hdr:
                lines.append(hdr)
                lines.append("")
            lines.append("=" * 60)
            lines.append("TRANSLATION INSTRUCTIONS & RULES:")
            lines.append("1. Maintain character personalities, tone, and visual novel style.")
            lines.append("2. Strictly preserve all CSIF headers: @@Speaker and @@_ (narration).")
            lines.append("3. Strictly preserve NGUI tags: [b], [i], [u], [s], [sub], [sup], [c]...[/c], [rub:ruby]base[/rub], [-]")
            lines.append("4. Strictly preserve tokens: {playername}, {0}, and line breaks.")
            lines.append("5. Output ONLY the translated story blocks in CSIF format.")
            lines.append("=" * 60)
            lines.append("")

        csif_body = serialize(self.current_doc, scope="all", include_metadata="auto")
        lines.append(csif_body)

        full_prompt = "\n".join(lines)
        self.safe_clipboard_set(full_prompt)
        box_count = len(self.current_doc.boxes)
        self.show_toast(f"📋 Copied AI prompt for {box_count} boxes (CSIF)")
        self.lbl_status.config(text=f"Copied AI prompt ({box_count} boxes in CSIF) to clipboard")

    def _show_paste_preview_and_apply(
        self,
        script_text: str,
        source_label: str = "Script Paste",
        confirm: bool = True,
        auto_word_wrap: bool = False,
    ) -> bool:
        """Unified method to parse, preview, and atomically apply script content to the open document (Phase 4 / Phase 5)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return False

        if not script_text or not script_text.strip():
            messagebox.showwarning("Empty Script", "The provided script text contains no readable content.")
            return False

        result = parse(script_text)

        # Route @@! metadata-only payloads to Box 0 (AGENTS.md Rule 20 D4)
        if not result.blocks and not result.metadata.is_empty():
            old_meta = self.current_doc.get_metadata()
            self.undo_journal.begin_batch("Paste Metadata (Box 0)")
            try:
                self.current_doc.set_metadata(
                    title=result.metadata.title,
                    subtitle=result.metadata.subtitle,
                    summary=result.metadata.summary,
                )
                self.undo_journal.record(
                    MetadataDelta(
                        file_path=str(self.current_file_path or ""),
                        old_title=old_meta.get("title", ""),
                        old_subtitle=old_meta.get("subtitle", ""),
                        old_summary=old_meta.get("summary", ""),
                        new_title=result.metadata.title or "",
                        new_subtitle=result.metadata.subtitle or "",
                        new_summary=result.metadata.summary or "",
                    )
                )
            finally:
                self.undo_journal.end_batch()
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            self._update_views()
            self.show_toast("✓ Metadata applied to Box 0")
            return True

        if not result.blocks:
            messagebox.showwarning("No Dialogue Found", "No valid dialogue blocks found in script.")
            return False

        total_boxes = len(self.current_doc.boxes)
        if result.is_sparse:
            targets = []
            for blk in result.blocks:
                if blk.index is None or not (1 <= blk.index <= total_boxes):
                    raise IndexError(f"Sparse index #{blk.index} is out of range. Document has {total_boxes} boxes.")
                targets.append((blk.index - 1, blk))
            count = len(targets)
            start_idx = 0
        else:
            start_idx = max(0, self.current_box_idx)
            if start_idx >= total_boxes:
                start_idx = 0
            count = min(len(result.blocks), total_boxes - start_idx)
            if count <= 0:
                messagebox.showwarning("Target Full", "No remaining boxes available to paste into.")
                return False
            targets = [(start_idx + k, result.blocks[k]) for k in range(count)]

        apply_speakers = any(bool(b.speaker.strip()) for _, b in targets)
        apply_meta = not result.metadata.is_empty()
        wrap_enabled = bool(auto_word_wrap)

        if confirm:
            # Headless / mocked test compatibility check
            if messagebox.askyesno.__module__ != "tkinter.messagebox" or getattr(self, "_test_bypass_dialogs", False):
                preview_lines = []
                for i in range(min(len(targets), 3)):
                    t_idx, blk = targets[i]
                    target_box_num = t_idx + 1
                    snippet = " ".join(blk.text.splitlines())[:50]
                    preview_lines.append(f"  Box {target_box_num} [{blk.speaker or 'Narration'}]: {snippet}")
                if len(targets) > 3:
                    preview_lines.append(f"  ... and {len(targets) - 3} more boxes")
                if result.is_sparse:
                    target_desc = ", ".join(f"Box {t_idx + 1}" for t_idx, _ in targets)
                    prompt = (
                        f"Detected {len(result.blocks)} blocks ({result.format}).\n\n"
                        f"Target boxes: {target_desc} (sparse, of {total_boxes}).\n\n"
                        f"Preview:\n" + "\n".join(preview_lines) + "\n\n"
                        "Apply this script across these boxes?"
                    )
                else:
                    prompt = (
                        f"Detected {len(result.blocks)} blocks ({result.format}).\n\n"
                        f"Target range: Box {start_idx + 1} to Box {start_idx + count} (of {total_boxes}).\n\n"
                        f"Preview:\n" + "\n".join(preview_lines) + "\n\n"
                    )
                    if len(result.blocks) > count:
                        prompt += f"Note: {len(result.blocks) - count} excess blocks will be ignored.\n\n"
                    prompt += "Apply this script across these boxes?"
                if not messagebox.askyesno("Paste Across Boxes", prompt, parent=self):
                    return False
            else:
                dlg = ScriptPastePreviewDialog(self, result, start_idx if not result.is_sparse else 0, source_label=source_label)
                self.wait_window(dlg)
                if not dlg.confirmed:
                    return False
                apply_speakers = dlg.apply_speakers
                apply_meta = dlg.apply_metadata
                wrap_enabled = bool(getattr(dlg, "auto_word_wrap", False))

        # Atomic commit via batch undo
        self._commit_widget_edit()
        locked_set = {
            idx for idx in range(total_boxes) if self.is_box_locked(idx)
        }
        skipped_locked = 0
        still_over_3 = 0

        effective_result = result
        effective_targets = targets
        if wrap_enabled:
            measure_fn, safe_w = self._get_word_wrap_params()
            wrapped_blocks: List[DialogueBlock] = []
            for blk in result.blocks:
                w_res = wrap_text(blk.text, measure_fn, safe_w, reflow_existing_breaks=False)
                wrapped_blocks.append(
                    DialogueBlock(
                        speaker=blk.speaker,
                        text=w_res.wrapped_text,
                        is_narration=blk.is_narration,
                        index=blk.index,
                        raw_header=blk.raw_header,
                    )
                )
            effective_result = ParseResult(
                blocks=wrapped_blocks,
                metadata=result.metadata,
                is_sparse=result.is_sparse,
                format=result.format,
                warnings=list(result.warnings),
            )
            if result.is_sparse:
                effective_targets = [
                    (blk.index - 1, blk) for blk in wrapped_blocks if blk.index is not None
                ]
            else:
                effective_targets = [(start_idx + k, wrapped_blocks[k]) for k in range(count)]

        self.undo_journal.begin_batch(f"Apply Script ({source_label})")
        try:
            # Apply metadata if requested and present
            if apply_meta and not effective_result.metadata.is_empty():
                old_meta = self.current_doc.get_metadata()
                self.current_doc.set_metadata(
                    title=effective_result.metadata.title,
                    subtitle=effective_result.metadata.subtitle,
                    summary=effective_result.metadata.summary,
                )
                self.undo_journal.record(
                    MetadataDelta(
                        file_path=str(self.current_file_path or ""),
                        old_title=old_meta.get("title", ""),
                        old_subtitle=old_meta.get("subtitle", ""),
                        old_summary=old_meta.get("summary", ""),
                        new_title=effective_result.metadata.title or "",
                        new_subtitle=effective_result.metadata.subtitle or "",
                        new_summary=effective_result.metadata.summary or "",
                    )
                )

            # Record box-level deltas in undo journal
            for b_idx, new_blk in effective_targets:
                if b_idx in locked_set:
                    skipped_locked += 1
                    continue
                old_box = self.current_doc.boxes[b_idx]
                new_sp = new_blk.speaker if (apply_speakers and new_blk.speaker) else old_box.speaker
                old_uid = old_box.segs[0].record.uid if old_box.segs and old_box.segs[0].record else old_box.uid
                old_segs = [s.text for s in old_box.segs] if len(old_box.segs) > 1 else None
                new_segs = [new_blk.text] if len(old_box.segs) > 1 else None
                if wrap_enabled and self._measure_dialogue_metrics(new_blk.text)["has_line_overflow"]:
                    still_over_3 += 1
                self.undo_journal.record(
                    BoxEditDelta(
                        box_index=b_idx,
                        old_speaker=old_box.speaker,
                        new_speaker=new_sp,
                        old_text=old_box.clean_text,
                        new_text=new_blk.text,
                        file_path=str(self.current_file_path or ""),
                        box_uid=old_uid,
                        old_seg_texts=old_segs,
                        new_seg_texts=new_segs,
                        source="paste_script",
                    )
                )

            applied_count = apply_to_document(
                self.current_doc,
                effective_result,
                mode="replace",
                start_box_index=start_idx if not effective_result.is_sparse else 0,
                apply_speakers=apply_speakers,
                apply_metadata=apply_meta,
                locked_indices=locked_set,
            )
            for b_idx, _ in effective_targets:
                if b_idx not in locked_set:
                    self._modified_boxes.add(b_idx)
        finally:
            self.undo_journal.end_batch()

        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()
        msg = f"✓ Applied script across {applied_count} boxes"
        if skipped_locked > 0:
            msg += f" ({skipped_locked} locked boxes preserved)"
        if wrap_enabled:
            msg += f" | {still_over_3} still >3 lines"
        self.show_toast(msg)
        self.lbl_status.config(text=f"Applied {source_label} across {applied_count} boxes.")
        return True

    def on_paste_cross_box(self, confirm: bool = True) -> None:
        """Apply multi-box translation from clipboard using CSIF codec with mode='replace' (Part C.3 / Phase 4)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return

        clip = self.safe_clipboard_get()
        if not clip.strip():
            messagebox.showwarning("Clipboard Empty", "Clipboard does not contain any readable text.")
            return

        self._show_paste_preview_and_apply(clip, source_label="Clipboard Paste", confirm=confirm)

    def on_import_script(self, file_path: Optional[Union[str, Path]] = None, confirm: bool = True) -> None:
        """Import script from a file (CSIF / Text) and apply it via preview dialog (Ctrl+Shift+I)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return

        if not file_path:
            file_types = [
                ("CSIF / Text Files", "*.txt;*.csif;*.md"),
                ("Text Files (*.txt)", "*.txt"),
                ("CSIF Files (*.csif)", "*.csif"),
                ("All Files (*.*)", "*.*"),
            ]
            selected = filedialog.askopenfilename(
                title="Import Script (CSIF / Text)",
                filetypes=file_types,
                parent=self,
            )
            if not selected:
                return
            target_file = Path(selected)
        else:
            target_file = Path(file_path)

        if not target_file.is_file():
            messagebox.showerror("File Not Found", f"Cannot find import file:\n{target_file}", parent=self)
            return

        try:
            decoded = read_text_file_strictly(target_file)
            content = decoded.text
        except UnicodeDecodeError as exc:
            self.logger.exception("Failed to decode import file:", exc)
            messagebox.showerror("Import Failed", f"Could not decode script file:\n{exc}", parent=self)
            return
        except Exception as exc:
            self.logger.exception("Failed to read import file:", exc)
            messagebox.showerror("Import Failed", f"Could not read script file:\n{exc}", parent=self)
            return

        self._show_paste_preview_and_apply(content, source_label=f"Import ({target_file.name})", confirm=confirm)

    def _get_xuat_index_roots(self) -> List[Path]:
        """Collect candidate roots for strict BepInEx\\Translation\\en\\Text XUAT indexing."""
        roots: List[Path] = []
        if getattr(self, "xuat_search_roots", None):
            roots.extend(self.xuat_search_roots)
        elif getattr(self, "project_folder", None):
            roots.append(self.project_folder)
        return resolve_xuat_text_roots(roots)

    def _refresh_xuat_index_async(self) -> None:
        """Start background XUAT dictionary indexing and poll on the Tk main thread (Rule 15)."""
        if getattr(self, "_xuat_index_cancel", None) is not None:
            try:
                self._xuat_index_cancel.set()
            except Exception:
                pass
        strict_roots = self._get_xuat_index_roots()
        if not strict_roots:
            self.xuat_index = None
            self.xuat_entries = None
            self._xuat_index_cancel = None
            return
        self._xuat_index_seq += 1
        seq = self._xuat_index_seq
        cancel_ev = threading.Event()
        self._xuat_index_cancel = cancel_ev
        self._xuat_index_thread = build_xuat_index_async(
            strict_roots,
            out_queue=self._xuat_index_queue,
            metadata=seq,
            cancel_event=cancel_ev,
        )
        if self._xuat_index_poll_id is None and self.winfo_exists():
            self._xuat_index_poll_id = self.after(50, self._poll_xuat_index_queue)

    def _poll_xuat_index_queue(self) -> None:
        """Poll background XUAT index builds strictly while a build is in flight (BUG-27)."""
        self._xuat_index_poll_id = None
        if not self.winfo_exists() or getattr(self, "_destroyed", False):
            return
        latest_applied = False
        try:
            while True:
                kind, seq, payload = self._xuat_index_queue.get_nowait()
                if seq != self._xuat_index_seq:
                    continue
                if kind == "xuat_index_ready":
                    self.xuat_index = payload
                    self.xuat_entries = payload
                    latest_applied = True
                elif kind == "xuat_index_error":
                    self.logger.warning("XUAT Index", f"Background XUAT index failed: {payload}")
                    latest_applied = True
        except queue.Empty:
            pass

        if not latest_applied and self.winfo_exists() and not getattr(self, "_destroyed", False):
            self._xuat_index_poll_id = self.after(50, self._poll_xuat_index_queue)

    def _get_or_build_xuat_index(self, force_rebuild: bool = False) -> XuatIndex:
        """Return unified XuatIndex (D11), building synchronously if not yet cached."""
        strict_roots = self._get_xuat_index_roots()
        if not force_rebuild and isinstance(getattr(self, "xuat_index", None), XuatIndex):
            if self.xuat_index.roots == strict_roots:
                return self.xuat_index
        idx = build_xuat_index(strict_roots)
        self.xuat_index = idx
        self.xuat_entries = idx
        return idx

    def on_import_from_xuat(self, xuat_index: Optional[XuatIndex] = None) -> Optional["ImportFromXUATDialog"]:
        """Open separate floating Import from XUAT resolver; auto-closes MTL drawer (FEAT-14 / U-B34)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.", parent=self)
            return None

        # Auto-close docked MTL drawer when opening Import from XUAT
        if getattr(self, "_side_drawer_visible", False) and getattr(self, "_side_drawer_tab", "") == "mtl":
            self._close_side_drawer()

        idx = xuat_index if xuat_index is not None else self._get_or_build_xuat_index()
        existing = getattr(self, "_import_xuat_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return existing
            except Exception:
                pass

        dlg = ImportFromXUATDialog(self, idx)
        self._import_xuat_dialog = dlg
        return dlg

    def _get_xuat_archive_dir(self) -> Path:
        """Return configured XUAT archive directory, defaulting to SCRIPT_DIR/backups/xuat_archive."""
        raw_dir = getattr(self, "xuat_archive_dir", None)
        if raw_dir:
            return Path(raw_dir)
        return default_archive_dir(SCRIPT_DIR)

    def _on_toggle_xuat_safety_backup(self) -> None:
        """Toggle automatic XUAT safety backups (Debug > Safety), requiring confirmation to turn OFF."""
        new_val = bool(self.var_xuat_safety_backup.get())
        if not new_val:
            ok = messagebox.askyesno(
                "Disable Automatic XUAT Safety Backups?",
                "Disabling 'Auto-backup XUAT files before cleanup edits' means modified or emptied "
                "XUAT files will NOT receive a per-file safety backup before cleanup writes.\n\n"
                "Disable automatic XUAT safety backups?",
                icon="warning",
                default=messagebox.NO,
                parent=self,
            )
            if not ok:
                self.var_xuat_safety_backup.set(True)
                self.xuat_safety_backup_enabled = True
                return
        self.xuat_safety_backup_enabled = new_val
        self._save_user_prefs(silent=True)
        state_lbl = "ON" if new_val else "OFF (Not Recommended)"
        self.logger.info("UI / Theme / Config", f"XUAT cleanup safety backup toggled: {state_lbl}")
        self.lbl_status.config(text=f"XUAT cleanup safety backup: {state_lbl}")
        cleanup_dlg = getattr(self, "_xuat_cleanup_dialog", None)
        if cleanup_dlg is not None:
            try:
                if cleanup_dlg.winfo_exists():
                    cleanup_dlg._refresh_safety_banner()
            except Exception:
                pass

    def _on_xuat_cleanup_settings_dialog(self) -> Optional["XuatCleanupSettingsDialog"]:
        """Open Debug > Safety > XUAT Cleanup & Archive Settings... modal dialog."""
        existing = getattr(self, "_xuat_cleanup_settings_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return existing
            except Exception:
                pass
        dlg = XuatCleanupSettingsDialog(self)
        self._xuat_cleanup_settings_dialog = dlg
        return dlg

    def on_clean_archive_xuat(self, xuat_index: Optional[XuatIndex] = None) -> Optional["XuatCleanupDialog"]:
        """Open XUAT cleanup/archival audit dialog against the active story (Tools -> Clean / Archive XUAT...)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.", parent=self)
            return None

        idx = xuat_index if xuat_index is not None else self._get_or_build_xuat_index(force_rebuild=True)
        existing = getattr(self, "_xuat_cleanup_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.destroy()
            except Exception:
                pass
            self._xuat_cleanup_dialog = None

        fps = dict(getattr(idx, "file_fingerprints", {}) or {})
        dlg = XuatCleanupDialog(
            self,
            xuat_index=idx,
            doc=self.current_doc,
            applied_records=(),
            source_fingerprints=fps,
            mode="manual",
        )
        self._xuat_cleanup_dialog = dlg
        return dlg

    def on_export_script(self, file_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """Export active story in CSIF format to a file (Ctrl+Shift+E)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return None

        if not file_path:
            init_name = f"{self.current_file_path.stem}.csif.txt" if self.current_file_path else "story_export.csif.txt"
            file_types = [
                ("CSIF Text File (*.txt)", "*.txt"),
                ("CSIF Script (*.csif)", "*.csif"),
                ("All Files (*.*)", "*.*"),
            ]
            selected = filedialog.asksaveasfilename(
                title="Export Script (CSIF)",
                defaultextension=".txt",
                initialfile=init_name,
                filetypes=file_types,
                parent=self,
            )
            if not selected:
                return None
            target_path = Path(selected)
        else:
            target_path = Path(file_path)

        self._commit_widget_edit()
        try:
            csif_text = serialize(self.current_doc, scope="all", include_metadata="auto")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            write_atomic_encoded(target_path, csif_text, encoding="utf-8", newline="\n")
        except Exception as exc:
            self.logger.exception("Failed to export script:", exc)
            messagebox.showerror("Export Failed", f"Could not write export file:\n{exc}", parent=self)
            return None

        box_count = len(self.current_doc.boxes)
        self.show_toast(f"✓ Exported {box_count} boxes to {target_path.name}")
        self.lbl_status.config(text=f"Exported script to {target_path}")
        return target_path

    # Universal alias for cross-box script pasting
    on_apply_translation_clipboard = on_paste_cross_box

    def _get_word_wrap_params(self) -> Tuple[Callable[[str], int], int]:
        """Return (measure_fn, constant_54d_safe_width) calibrated to Nunito Bold 54d."""
        f = self._get_dialogue_measure_font()
        safe_w = self._get_54d_reference_safe_w()
        return f.measure, safe_w

    def apply_auto_word_wrap(
        self,
        scope: str = "all",
        reflow_existing_breaks: bool = False,
    ) -> Dict[str, int]:
        """Apply lossless pixel-calibrated Auto Word Wrap across selected dialogue scope in ONE Undo batch."""
        stats = {"wrapped": 0, "skipped_locked": 0, "still_over_3": 0, "total_targets": 0}
        doc = self.current_doc
        if not doc or not doc.boxes:
            self.show_toast("No story document loaded")
            return stats

        self._commit_widget_edit()
        total = len(doc.boxes)
        if scope == "current":
            if getattr(self, "is_box0_active", False):
                self.show_toast("Box 0 metadata cannot be word-wrapped.")
                return stats
            targets = [self.current_box_idx] if 0 <= self.current_box_idx < total else []
        elif scope == "selected":
            targets = sorted(i for i in getattr(self, "_selected_boxes", set()) if 0 <= i < total)
        else:
            targets = list(range(total))

        stats["total_targets"] = len(targets)
        if not targets:
            self.show_toast("No dialogue boxes selected for Auto Word Wrap.")
            return stats

        measure_fn, safe_w = self._get_word_wrap_params()
        wrapped_count = 0
        skipped_locked = 0
        still_over_3 = 0

        self.undo_journal.begin_batch("Auto Word Wrap")
        try:
            for b_idx in targets:
                if not (0 <= b_idx < len(doc.boxes)):
                    continue
                if self.is_box_locked(b_idx):
                    skipped_locked += 1
                    continue

                box = doc.boxes[b_idx]
                b_uid = _get_box_uid(box)
                old_sp = box.speaker
                old_tx = box.clean_text

                if len(box.segs) > 1:
                    old_segs = [game_to_xuat(s.text) for s in box.segs]
                    new_segs = [
                        wrap_text(
                            seg_tx,
                            measure_fn,
                            safe_w,
                            reflow_existing_breaks=reflow_existing_breaks,
                        ).wrapped_text
                        if seg_tx
                        else ""
                        for seg_tx in old_segs
                    ]
                    if new_segs != old_segs:
                        joined_tx = "".join(new_segs)
                        doc.inject_box(b_idx, old_sp, joined_tx, seg_texts=new_segs)
                        refreshed_box = doc.boxes[b_idx]
                        committed_tx = refreshed_box.clean_text
                        committed_new_segs = [game_to_xuat(s.text) for s in refreshed_box.segs]
                        self.undo_journal.record(
                            BoxEditDelta(
                                box_index=b_idx,
                                old_speaker=old_sp,
                                new_speaker=old_sp,
                                old_text=old_tx,
                                new_text=committed_tx,
                                file_path=str(self.current_file_path or ""),
                                box_uid=b_uid,
                                source="word_wrap",
                                old_seg_texts=old_segs,
                                new_seg_texts=committed_new_segs,
                            )
                        )
                        self._modified_boxes.add(b_idx)
                        if b_uid is not None and hasattr(self, "_modified_box_uids"):
                            self._modified_box_uids.add(b_uid)
                        wrapped_count += 1
                else:
                    res = wrap_text(
                        old_tx,
                        measure_fn,
                        safe_w,
                        reflow_existing_breaks=reflow_existing_breaks,
                    )
                    if res.changed:
                        doc.inject_box(b_idx, old_sp, res.wrapped_text)
                        refreshed_box = doc.boxes[b_idx]
                        committed_tx = refreshed_box.clean_text
                        self.undo_journal.record(
                            BoxEditDelta(
                                box_index=b_idx,
                                old_speaker=old_sp,
                                new_speaker=old_sp,
                                old_text=old_tx,
                                new_text=committed_tx,
                                file_path=str(self.current_file_path or ""),
                                box_uid=b_uid,
                                source="word_wrap",
                                old_seg_texts=None,
                                new_seg_texts=None,
                            )
                        )
                        self._modified_boxes.add(b_idx)
                        if b_uid is not None and hasattr(self, "_modified_box_uids"):
                            self._modified_box_uids.add(b_uid)
                        wrapped_count += 1

                if self._measure_dialogue_metrics(doc.boxes[b_idx].clean_text)["has_line_overflow"]:
                    still_over_3 += 1
        finally:
            self.undo_journal.end_batch()

        if wrapped_count > 0:
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            self._update_views()
            self._update_char_overflow_indicator()

        summary = f"Wrapped {wrapped_count} | Skipped {skipped_locked} locked | {still_over_3} still >3 lines"
        self.show_toast(summary)
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=summary)
        return {
            "wrapped": wrapped_count,
            "skipped_locked": skipped_locked,
            "still_over_3": still_over_3,
            "total_targets": len(targets),
        }

    def on_open_auto_word_wrap(self) -> Optional["AutoWordWrapDialog"]:
        """Open the Auto Word Wrap dialog (Tools -> Auto Word Wrap...)."""
        if not self.current_doc or not self.current_doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.", parent=self)
            return None
        self._commit_widget_edit()
        dlg = AutoWordWrapDialog(self)
        self._auto_word_wrap_dialog = dlg
        return dlg

    def on_clear_dialogue_skeleton(self) -> None:
        """Clear all dialogue text across all boxes, keeping speaker names and skeleton intact."""
        if not self.current_doc or not self.current_doc.boxes:
            self.show_toast("No story document loaded")
            return
        total = len(self.current_doc.boxes)
        ans = messagebox.askyesno(
            "Clear Dialogue Skeleton",
            f"Clear all dialogue text across all {total} boxes?\n\n"
            "This preserves speaker names, tags, and box timing while resetting dialogue to blank for a fresh translation pass.\n\n"
            "This operation can be undone via Ctrl+Z."
        )
        if not ans:
            return

        cleared_count = 0
        preserved_count = 0
        self.undo_journal.begin_batch("Clear Dialogue Skeleton")
        try:
            for i, box in enumerate(self.current_doc.boxes):
                if self.is_box_locked(i):
                    preserved_count += 1
                    continue
                if box.clean_text:
                    old_sp = box.speaker
                    old_tx = box.clean_text
                    box_uid = box.uid
                    try:
                        self.current_doc.inject_box(i, old_sp, "")
                    except Exception as e:
                        self.logger.exception(f"Failed to clear box {i}:", e)
                        continue

                    self.undo_journal.record(
                        BoxEditDelta(
                            box_index=i,
                            old_speaker=old_sp,
                            new_speaker=old_sp,
                            old_text=old_tx,
                            new_text="",
                            file_path=str(self.current_file_path) if self.current_file_path else "",
                            box_uid=box_uid,
                            source="clear",
                        )
                    )
                    self._modified_boxes.add(i)
                    cleared_count += 1
        finally:
            self.undo_journal.end_batch()

        if cleared_count > 0:
            self._mark_document_dirty(self.current_file_path)
            self._dirty_state_changed()
            self._update_views()

        msg = f"Cleared dialogue skeleton for {cleared_count} boxes"
        if preserved_count > 0:
            msg += f" (preserved {preserved_count} locked)"
        self.show_toast(f"✓ {msg}")
        self.lbl_status.config(text=f"{msg}.")

    def on_register_unity3d_association(self) -> None:
        """Register or verify .unity3d file association for current Windows user (#8)."""
        bat_path = SCRIPT_DIR / "misora.bat"
        if not bat_path.exists():
            messagebox.showerror("Association Error", f"Cannot find {bat_path}")
            return

        cmd_str = f'"{bat_path}" "%1"'
        try:
            already_registered = False
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.unity3d") as key:
                    val, _ = winreg.QueryValueEx(key, "")
                    if val == "Misora.Unity3dBundle":
                        already_registered = True
            except OSError:
                pass

            if already_registered:
                ans = messagebox.askyesno(
                    ".unity3d File Association",
                    ".unity3d files are currently associated with Misora.\n\nDo you want to unregister (remove) this association?"
                )
                if ans:
                    try:
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle\shell\open\command")
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle\shell\open")
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle\shell")
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle")
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.unity3d")
                        self.show_toast("✓ Removed .unity3d file association")
                        messagebox.showinfo("Success", ".unity3d association removed successfully.")
                    except Exception as exc:
                        self.logger.exception("Failed to remove .unity3d association:", exc)
                        messagebox.showerror("Error", f"Failed to remove association:\n{exc}")
                return

            ans = messagebox.askyesno(
                "Register .unity3d File Association",
                f"Associate .unity3d story files with Misora for the current user?\n\nTarget launcher:\n{bat_path}\n\nThis does not require Administrator privileges."
            )
            if not ans:
                return

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.unity3d") as k1:
                winreg.SetValueEx(k1, "", 0, winreg.REG_SZ, "Misora.Unity3dBundle")

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle") as k2:
                winreg.SetValueEx(k2, "", 0, winreg.REG_SZ, "Unity3D Story Bundle (Misora)")

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Misora.Unity3dBundle\shell\open\command") as k3:
                winreg.SetValueEx(k3, "", 0, winreg.REG_SZ, cmd_str)

            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, 0, 0)
            except Exception:
                pass

            self.logger.info("Config", "Registered .unity3d file association for HKCU")
            self.show_toast("✓ Registered .unity3d file association")
            messagebox.showinfo("Success", ".unity3d story bundles are now associated with Misora!")
        except Exception as exc:
            self.logger.exception("Failed to register .unity3d association:", exc)
            messagebox.showerror("Registration Failed", f"Could not write registry keys:\n{exc}")

    def on_about(self) -> None:
        """Show modal About dialog with Support Me launcher (U05, Rule 3)."""
        existing = getattr(self, "_about_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_set()
                    return
            except Exception:
                pass

        t = self.theme
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_muted = _wcag_muted_fg(t["fg_muted"], t["bg_panel"], fg_panel)

        dlg = tk.Toplevel(self)
        self._about_dialog = dlg
        dlg.title("About Misora: Story Editor")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.configure(bg=t["bg_panel"])
        apply_window_icon(dlg)

        body = tk.Frame(dlg, bg=t["bg_panel"], padx=22, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Misora: Story Editor",
            font=("Segoe UI", 14, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="center")

        tk.Label(
            body,
            text=f"v{__version__}",
            font=("Segoe UI", 10, "bold"),
            bg=t["bg_panel"],
            fg=fg_panel,
        ).pack(anchor="center", pady=(2, 10))

        tk.Label(
            body,
            text=(
                "A specialized GUI text editor for Princess Connect! Re:Dive\n"
                "Unity3D story bundles (.unity3d) and XUAT translation files.\n\n"
                "MIT License — Created for the Priconne Modding Community."
            ),
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_muted,
            justify="center",
        ).pack(anchor="center", pady=(0, 14))

        def _close_about(_e: Optional[tk.Event] = None) -> None:
            if self._about_dialog is dlg:
                self._about_dialog = None
            safe_grab_release(dlg)
            try:
                if dlg.winfo_exists():
                    dlg.destroy()
            except Exception:
                pass

        def _launch_support() -> None:
            _close_about()
            self.on_support_me()

        btn_row = tk.Frame(body, bg=t["bg_panel"])
        btn_row.pack(fill="x")

        ttk.Button(
            btn_row,
            text="Support Me",
            style="Pink.TButton",
            command=_launch_support,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ttk.Button(
            btn_row,
            text="Close",
            style="TButton",
            command=_close_about,
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))

        dlg.protocol("WM_DELETE_WINDOW", _close_about)
        dlg.bind("<Escape>", _close_about)

        dlg.update_idletasks()
        try:
            px = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
            py = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
            dlg.geometry(f"+{max(0, px)}+{max(0, py)}")
        except Exception:
            pass
        try:
            dlg.grab_set()
        except Exception:
            pass

    def on_support_me(self) -> None:
        """Open the SupportMeDialog with sequential-frame GIF streaming (U05)."""
        existing = getattr(self, "_support_me_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_set()
                    return
            except Exception:
                pass
        self._support_me_dialog = SupportMeDialog(self)


# =============================================================================
# Support Me Dialog (U05 — Sequential-Frame GIF Streaming)
# =============================================================================
class SupportMeDialog(tk.Toplevel):
    """Modal Support Me dialog with memory-bounded sequential GIF playback (U05)."""

    def __init__(self, parent: "MisoraApp", gif_path: Optional[Path] = None) -> None:
        super().__init__(parent)
        self.app = parent
        self._gif_path: Path = (
            Path(gif_path)
            if gif_path is not None
            else (SCRIPT_DIR / "assets" / "Service.gif")
        )
        self._gif_image: Optional[Any] = None
        self._gif_frame_count: int = 0
        self._gif_frame_idx: int = 0
        self._gif_after_id: Optional[str] = None
        self._current_frame_photo: Optional[Any] = None
        self._fallback_photo: Optional[Any] = None
        self._closed: bool = False
        self.support_buttons: Dict[str, tk.Widget] = {}

        self.title("Support Misora: Story Editor")
        self.resizable(False, False)
        self.transient(parent)
        apply_window_icon(self)

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_muted = _wcag_muted_fg(t["fg_muted"], t["bg_panel"], fg_panel)

        container = tk.Frame(self, bg=t["bg_panel"], padx=20, pady=16)
        container.pack(fill="both", expand=True)

        self.lbl_gif = tk.Label(
            container,
            bg=t["bg_panel"],
            fg=t["misora_pink"],
            bd=0,
            highlightthickness=0,
        )
        self.lbl_gif.pack(pady=(0, 12))

        tk.Label(
            container,
            text=SUPPORT_CAPTION_ID,
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_panel,
            wraplength=420,
            justify="center",
        ).pack(pady=(0, 14))

        btn_row = tk.Frame(container, bg=t["bg_panel"])
        btn_row.pack(fill="x", pady=(0, 8))

        providers: List[Tuple[str, str, str]] = [
            ("Ko-fi", "kofi", SUPPORT_URL_KOFI),
            ("Patreon", "patreon", SUPPORT_URL_PATREON),
        ]
        if SHOW_PAYPAL_BUTTON:
            providers.append(("PayPal", "paypal", SUPPORT_URL_PAYPAL))

        for label, icon_name, url in providers:
            ico = get_icon(icon_name, (18, 18), master=self)
            btn = ttk.Button(
                btn_row,
                text=f" {label}" if ico is not None else label,
                image=ico if ico is not None else "",
                compound="left" if ico is not None else "none",
                style="TButton",
                command=lambda u=url: self._open_external_url(u),
            )
            if ico is not None:
                setattr(btn, "_support_icon_ref", ico)
            btn.pack(side="left", expand=True, fill="x", padx=4)
            self.support_buttons[label] = btn

        tk.Label(
            container,
            text="Links open in your browser. Misora does not process payments.",
            font=("Segoe UI", 8),
            bg=t["bg_panel"],
            fg=fg_muted,
            justify="center",
        ).pack(pady=(2, 10))

        ttk.Button(
            container,
            text="Close",
            style="Pink.TButton",
            command=self.close,
        ).pack(anchor="center")

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())

        self._init_gif_player()

        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        hx = (hex_color or "#ffffff").strip().lstrip("#")
        if len(hx) != 6:
            return (255, 255, 255)
        try:
            return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        except Exception:
            return (255, 255, 255)

    @staticmethod
    def _open_external_url(url: str) -> None:
        webbrowser.open(url, new=2)

    def _init_gif_player(self) -> None:
        """Open Service.gif lazily and start sequential single-PhotoImage streaming."""
        if Image is None or ImageTk is None or not self._gif_path.is_file():
            self._render_static_fallback()
            return
        try:
            img = Image.open(self._gif_path)
            self._gif_image = img
            self._gif_frame_count = max(1, int(getattr(img, "n_frames", 1)))
            self._gif_frame_idx = 0
            self._render_gif_frame(0)
        except Exception:
            self._close_gif_handle()
            self._render_static_fallback()

    def _render_static_fallback(self) -> None:
        """Render a clean static placeholder when Service.gif is absent or unreadable."""
        if not hasattr(self, "lbl_gif") or not self.lbl_gif.winfo_exists():
            return
        ico = get_icon("sparkle", (48, 48), master=self)
        if ico is not None:
            self._fallback_photo = ico
            self.lbl_gif.configure(
                image=ico,
                text="  Misora: Story Editor",
                compound="left",
                font=("Segoe UI", 11, "bold"),
            )
        else:
            self.lbl_gif.configure(
                image="",
                text="Misora: Story Editor",
                font=("Segoe UI", 11, "bold"),
            )

    def _render_gif_frame(self, frame_idx: int) -> None:
        """Seek a single GIF frame, composite onto bg_panel RGB, and paste into one PhotoImage."""
        if self._closed or self._gif_image is None or Image is None or ImageTk is None:
            return
        try:
            self._gif_image.seek(frame_idx)
            rgba = self._gif_image.convert("RGBA")
            w, h = rgba.size
            scale = min(240.0 / max(1, w), 240.0 / max(1, h))
            tw = max(1, int(round(w * scale)))
            th = max(1, int(round(h * scale)))
            if (w, h) != (tw, th):
                rgba = rgba.resize((tw, th), Image.Resampling.LANCZOS)

            bg_rgb = self._hex_to_rgb(self.app.theme.get("bg_panel", "#ffffff"))
            composite = Image.new("RGB", (tw, th), bg_rgb)
            composite.paste(rgba, (0, 0), mask=rgba.split()[3])

            if (
                self._current_frame_photo is None
                or self._current_frame_photo.width() != tw
                or self._current_frame_photo.height() != th
            ):
                self._current_frame_photo = ImageTk.PhotoImage(composite, master=self)
                if self.lbl_gif.winfo_exists():
                    self.lbl_gif.configure(image=self._current_frame_photo, text="")
            else:
                self._current_frame_photo.paste(composite)

            delay_ms = max(40, int(self._gif_image.info.get("duration", 80) or 80))
            if self._gif_frame_count > 1 and not self._closed:
                self._gif_after_id = self.after(delay_ms, self._advance_gif_frame)
        except Exception:
            self._close_gif_handle()
            self._render_static_fallback()

    def _advance_gif_frame(self) -> None:
        self._gif_after_id = None
        if self._closed or self._gif_image is None or self._gif_frame_count <= 1:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._gif_frame_idx = (self._gif_frame_idx + 1) % self._gif_frame_count
        self._render_gif_frame(self._gif_frame_idx)

    def _close_gif_handle(self) -> None:
        if self._gif_after_id is not None:
            try:
                self.after_cancel(self._gif_after_id)
            except Exception:
                pass
            self._gif_after_id = None
        if self._gif_image is not None:
            try:
                self._gif_image.close()
            except Exception:
                pass
            self._gif_image = None

    def _cleanup_resources(self) -> None:
        self._closed = True
        self._close_gif_handle()
        self._current_frame_photo = None
        self._fallback_photo = None
        try:
            if hasattr(self, "lbl_gif") and self.lbl_gif.winfo_exists():
                self.lbl_gif.configure(image="")
        except Exception:
            pass
        if getattr(self.app, "_support_me_dialog", None) is self:
            self.app._support_me_dialog = None
        safe_grab_release(self)

    def close(self) -> None:
        self._cleanup_resources()
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass

    def destroy(self) -> None:
        self._cleanup_resources()
        super().destroy()


# =============================================================================
# Script Paste / Import Preview Dialog (Phase 4)
# =============================================================================
class ScriptPastePreviewDialog(tk.Toplevel):
    """Interactive preview and confirmation dialog for script paste and import operations (Part C.5 / Phase 4)."""

    def __init__(
        self,
        parent: "MisoraApp",
        parsed_result,
        start_idx: int,
        source_label: str = "Script Paste",
    ):
        super().__init__(parent)
        self.app = parent
        self.result = parsed_result
        self.start_idx = start_idx
        self.source_label = source_label
        self.confirmed = False

        self.title("Paste / Import Script Preview")
        self.geometry("860x640")
        self.minsize(720, 480)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        total_doc_boxes = len(self.app.current_doc.boxes) if self.app.current_doc else 0
        blocks = self.result.blocks
        if self.result.is_sparse:
            self.count = len(blocks)
            has_speakers = any(bool(b.speaker.strip()) for b in blocks)
        else:
            self.count = min(len(blocks), max(0, total_doc_boxes - start_idx))
            has_speakers = any(bool(b.speaker.strip()) for b in blocks[:self.count])
        has_meta = not self.result.metadata.is_empty()

        self.var_apply_speakers = tk.BooleanVar(master=self, value=has_speakers)
        self.var_apply_metadata = tk.BooleanVar(master=self, value=has_meta)
        self.var_auto_word_wrap = tk.BooleanVar(master=self, value=False)

        self.apply_speakers = has_speakers
        self.apply_metadata = has_meta
        self.auto_word_wrap = False

        self._build_ui(t, fg_panel, fg_editor, total_doc_boxes, blocks, has_meta)

        # Center on parent window
        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", lambda _e=None: self.on_cancel())

    def _build_ui(self, t: dict, fg_panel: str, fg_editor: str, total_doc_boxes: int, blocks: list, has_meta: bool) -> None:
        container = tk.Frame(self, bg=t["bg_panel"], padx=14, pady=10)
        container.pack(fill="both", expand=True)

        # 1. Header Banner & Info
        hdr_frame = tk.Frame(container, bg=t["bg_panel"])
        hdr_frame.pack(fill="x", pady=(0, 8))

        lbl_title = tk.Label(
            hdr_frame,
            text=f"Script Preview — {self.source_label}",
            font=("Segoe UI", 12, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        )
        lbl_title.pack(anchor="w")

        if self.result.is_sparse:
            sparse_box_names = ", ".join(f"Box {b.index}" for b in blocks if b.index is not None)
            info_lines = [
                f"Format: {self.result.format.upper()} (Sparse)  |  Detected: {len(blocks)} blocks  |  Targets: {sparse_box_names} (of {total_doc_boxes})"
            ]
        else:
            info_lines = [
                f"Format: {self.result.format.upper()}  |  Detected: {len(blocks)} blocks  |  Target: Box {self.start_idx + 1} to {self.start_idx + self.count} (of {total_doc_boxes})"
            ]
            if len(blocks) > self.count:
                excess = len(blocks) - self.count
                info_lines.append(f"⚠ Notice: {excess} excess block(s) will be skipped as they exceed total boxes.")
        if has_meta:
            m = self.result.metadata
            m_parts = []
            if m.title:
                m_parts.append(f"Title: '{m.title}'")
            if m.subtitle:
                m_parts.append(f"Subtitle: '{m.subtitle}'")
            if m_parts:
                info_lines.append("Metadata detected: " + ", ".join(m_parts))

        lbl_info = tk.Label(
            hdr_frame,
            text="\n".join(info_lines),
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_panel,
            justify="left",
        )
        lbl_info.pack(anchor="w", pady=(2, 0))

        # 2. Options Checkboxes
        opts_frame = tk.Frame(container, bg=t["bg_panel"])
        opts_frame.pack(fill="x", pady=(4, 6))

        cb_speakers = ttk.Checkbutton(
            opts_frame,
            text="Apply speaker names from script",
            variable=self.var_apply_speakers,
            command=self._populate_tree,
        )
        cb_speakers.pack(side="left", padx=(0, 16))

        if has_meta:
            cb_meta = ttk.Checkbutton(
                opts_frame,
                text="Apply metadata (title / subtitle / summary) to Box 0",
                variable=self.var_apply_metadata,
            )
            cb_meta.pack(side="left", padx=(0, 16))

        cb_wrap = ttk.Checkbutton(
            opts_frame,
            text=f"Auto Word Wrap imported lines to {DIALOGUE_MAX_DIGITS}d x {DIALOGUE_MAX_LINES}",
            variable=self.var_auto_word_wrap,
            command=self._populate_tree,
        )
        cb_wrap.pack(side="left")

        # 3. Comparison Treeview
        tree_frame = tk.Frame(container, bg=t["bg_editor"], bd=1, relief="solid")
        tree_frame.pack(fill="both", expand=True, pady=(2, 8))

        columns = ("box", "cur_spk", "new_spk", "cur_text", "new_text")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("box", text="Box #")
        self.tree.heading("cur_spk", text="Current Speaker")
        self.tree.heading("new_spk", text="Incoming Speaker")
        self.tree.heading("cur_text", text="Current Text (Preview)")
        self.tree.heading("new_text", text="Incoming Text (Preview)")

        self.tree.column("box", width=70, minwidth=50, anchor="center")
        self.tree.column("cur_spk", width=120, minwidth=80, anchor="w")
        self.tree.column("new_spk", width=130, minwidth=80, anchor="w")
        self.tree.column("cur_text", width=250, minwidth=140, anchor="w")
        self.tree.column("new_text", width=250, minwidth=140, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._populate_tree()

        # 4. Action Buttons
        btn_row = tk.Frame(container, bg=t["bg_panel"])
        btn_row.pack(fill="x", pady=(4, 0))

        btn_apply = tk.Button(
            btn_row,
            text="Apply Changes",
            bg=t["accent_blue"],
            fg="#ffffff",
            activebackground=t["accent_blue"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=4,
            relief="raised",
            cursor="hand2",
            command=self.on_apply,
        )
        btn_apply.pack(side="right", padx=(8, 0))

        btn_cancel = tk.Button(
            btn_row,
            text="Cancel",
            bg=t["bg_editor"],
            fg=fg_editor,
            activebackground=t["bg_editor"],
            activeforeground=fg_editor,
            font=("Segoe UI", 9),
            padx=14,
            pady=4,
            relief="raised",
            cursor="hand2",
            command=self.on_cancel,
        )
        btn_cancel.pack(side="right")

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        blocks = self.result.blocks
        apply_speakers = self.var_apply_speakers.get()
        auto_wrap = bool(self.var_auto_word_wrap.get())
        measure_fn = None
        safe_w = 1
        if auto_wrap:
            measure_fn, safe_w = self.app._get_word_wrap_params()

        if self.result.is_sparse:
            for new_blk in blocks:
                if new_blk.index is None:
                    continue
                b_idx = new_blk.index - 1
                if not (0 <= b_idx < len(self.app.current_doc.boxes)):
                    continue
                old_box = self.app.current_doc.boxes[b_idx]
                cur_spk = old_box.speaker or "(narration)"
                if apply_speakers:
                    new_spk = new_blk.speaker if new_blk.speaker else "(narration)"
                else:
                    new_spk = f"{cur_spk} (keep)"

                cur_txt = " ".join(old_box.clean_text.splitlines())[:80]
                if auto_wrap and measure_fn is not None:
                    w_txt = wrap_text(new_blk.text, measure_fn, safe_w, reflow_existing_breaks=False).wrapped_text
                    new_txt = " ↵ ".join(w_txt.splitlines())[:80]
                else:
                    new_txt = " ".join(new_blk.text.splitlines())[:80]
                self.tree.insert("", "end", values=(f"Box {new_blk.index}", cur_spk, new_spk, cur_txt, new_txt))
        else:
            for k in range(self.count):
                b_idx = self.start_idx + k
                old_box = self.app.current_doc.boxes[b_idx]
                new_blk = blocks[k]

                cur_spk = old_box.speaker or "(narration)"
                if apply_speakers:
                    new_spk = new_blk.speaker if new_blk.speaker else "(narration)"
                else:
                    new_spk = f"{cur_spk} (keep)"

                cur_txt = " ".join(old_box.clean_text.splitlines())[:80]
                if auto_wrap and measure_fn is not None:
                    w_txt = wrap_text(new_blk.text, measure_fn, safe_w, reflow_existing_breaks=False).wrapped_text
                    new_txt = " ↵ ".join(w_txt.splitlines())[:80]
                else:
                    new_txt = " ".join(new_blk.text.splitlines())[:80]

                self.tree.insert("", "end", values=(f"Box {b_idx + 1}", cur_spk, new_spk, cur_txt, new_txt))

    def on_apply(self) -> None:
        self.apply_speakers = self.var_apply_speakers.get()
        self.apply_metadata = self.var_apply_metadata.get()
        self.auto_word_wrap = bool(self.var_auto_word_wrap.get())
        self.confirmed = True
        safe_grab_release(self)
        self.destroy()

    def on_cancel(self) -> None:
        self.confirmed = False
        safe_grab_release(self)
        self.destroy()


# =============================================================================
# Auto Word Wrap Dialog (S06 / U07)
# =============================================================================
class AutoWordWrapDialog(tk.Toplevel):
    """Modal configuration dialog for Tools -> Auto Word Wrap... (U07)."""

    def __init__(self, parent: "MisoraApp"):
        super().__init__(parent)
        self.app = parent
        self.applied_stats: Optional[Dict[str, int]] = None

        self.title(f"Auto Word Wrap ({DIALOGUE_MAX_DIGITS}d x {DIALOGUE_MAX_LINES})")
        self.geometry("460x290")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        doc = self.app.current_doc
        total_boxes = len(doc.boxes) if doc and doc.boxes else 0
        sel_count = len([i for i in getattr(self.app, "_selected_boxes", set()) if 0 <= i < total_boxes])
        is_box0 = bool(getattr(self.app, "is_box0_active", False))

        default_scope = "selected" if sel_count > 0 else ("all" if is_box0 else "current")
        self.var_scope = tk.StringVar(master=self, value=default_scope)
        self.var_preserve_breaks = tk.BooleanVar(master=self, value=True)

        self._build_ui(t, sel_count, is_box0, total_boxes)

        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

    def _build_ui(self, t: dict, sel_count: int, is_box0: bool, total_boxes: int) -> None:
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        container = tk.Frame(self, bg=t["bg_panel"], padx=16, pady=12)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=f"Auto Word Wrap to {DIALOGUE_MAX_DIGITS}d x {DIALOGUE_MAX_LINES}",
            font=("Segoe UI", 11, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w")

        tk.Label(
            container,
            text="Wraps overflowing lines losslessly while skipping 🔒 locked boxes.",
            font=("Segoe UI", 8),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
        ).pack(anchor="w", pady=(2, 10))

        scope_box = tk.LabelFrame(
            container,
            text="Target Scope",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
        )
        scope_box.pack(fill="x", pady=(0, 8))

        rb_cur = ttk.Radiobutton(
            scope_box,
            text=f"Current Box (#{self.app.current_box_idx + 1})" if not is_box0 else "Current Box (Box 0 metadata skipped)",
            variable=self.var_scope,
            value="current",
            style="Panel.TRadiobutton",
            state="disabled" if (is_box0 or total_boxes == 0) else "normal",
        )
        rb_cur.pack(anchor="w", pady=1)

        rb_sel = ttk.Radiobutton(
            scope_box,
            text=f"Selected Boxes ({sel_count})",
            variable=self.var_scope,
            value="selected",
            style="Panel.TRadiobutton",
            state="disabled" if sel_count == 0 else "normal",
        )
        rb_sel.pack(anchor="w", pady=1)

        rb_all = ttk.Radiobutton(
            scope_box,
            text=f"All Boxes in Document ({total_boxes})",
            variable=self.var_scope,
            value="all",
            style="Panel.TRadiobutton",
            state="disabled" if total_boxes == 0 else "normal",
        )
        rb_all.pack(anchor="w", pady=1)

        opt_box = tk.LabelFrame(
            container,
            text="Line Break Handling",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
        )
        opt_box.pack(fill="x", pady=(0, 10))

        ttk.Radiobutton(
            opt_box,
            text="Preserve existing line breaks (wrap long lines only)",
            variable=self.var_preserve_breaks,
            value=True,
            style="Panel.TRadiobutton",
        ).pack(anchor="w", pady=1)

        ttk.Radiobutton(
            opt_box,
            text="Reflow all paragraphs",
            variable=self.var_preserve_breaks,
            value=False,
            style="Panel.TRadiobutton",
        ).pack(anchor="w", pady=1)

        btn_row = tk.Frame(container, bg=t["bg_panel"])
        btn_row.pack(fill="x", side="bottom")

        ttk.Button(btn_row, text="Cancel", style="TButton", command=self._on_close).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="Apply Wrap", style="Pink.TButton", command=self._on_apply).pack(side="right")

    def _on_apply(self) -> None:
        scope = self.var_scope.get()
        reflow = not bool(self.var_preserve_breaks.get())
        self.applied_stats = self.app.apply_auto_word_wrap(
            scope=scope,
            reflow_existing_breaks=reflow,
        )
        self._on_close()

    def _on_close(self) -> None:
        if getattr(self.app, "_auto_word_wrap_dialog", None) is self:
            self.app._auto_word_wrap_dialog = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()


# =============================================================================
# Floating Import from XUAT Resolver Dialog (S22 / FEAT-14 / U-B34)
# =============================================================================
class ImportFromXUATDialog(tk.Toplevel):
    """Separate floating resolver pairing Story boxes (left) with XUAT matches (right).

    Both sides are strictly read-only (state='disabled') with fixed 3 lines x 50 digit-widths
    (via S17 _measure_dialogue_metrics) and zero per-box Scrollbar widgets.
    """

    def __init__(self, parent: "MisoraApp", xuat_index: XuatIndex):
        super().__init__(parent)
        self.app = parent
        self.xuat_index = xuat_index
        self._rows: List[Dict[str, Any]] = []
        self._focused_box_widget: Optional[tk.Text] = None
        self._active_filter: str = "all"
        self._speaker_matches: Dict[int, str] = {}
        self._filter_buttons: Dict[str, ttk.Button] = {}
        self._canvas_win_id: Optional[int] = None

        self.title("Import from XUAT (Read-Only Paired Resolver)")
        self.geometry("980x680")
        self.minsize(820, 520)
        self.transient(parent)

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        self.var_translate_speakers = tk.BooleanVar(master=self, value=False)
        self.var_auto_word_wrap = tk.BooleanVar(master=self, value=False)
        self._build_ui()
        self._populate_rows()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

    def _build_ui(self) -> None:
        t = self.app.theme
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")

        top = tk.Frame(self, bg=t["bg_panel"], padx=12, pady=8)
        top.pack(fill="x")

        title_row = tk.Frame(top, bg=t["bg_panel"])
        title_row.pack(fill="x")

        tk.Label(
            title_row,
            text="Import from XUAT Dictionary",
            font=("Segoe UI", 12, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(side="left")

        ttk.Button(
            title_row,
            text="↻ Reload XUAT Index",
            style="Small.TButton",
            command=self._on_reload_index,
        ).pack(side="right")

        self.lbl_summary = tk.Label(
            top,
            text="Dialogue: 0 matched | Speakers: 0 matched",
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_panel,
            anchor="w",
        )
        self.lbl_summary.pack(fill="x", pady=(4, 4))

        ctrl_row = tk.Frame(top, bg=t["bg_panel"])
        ctrl_row.pack(fill="x", pady=(2, 0))

        for f_key, f_label in (
            ("all", "All"),
            ("duplicates", "Duplicates"),
            ("missing", "Missing"),
            ("matched", "Matched"),
        ):
            btn = ttk.Button(
                ctrl_row,
                text=f_label,
                style="Pink.TButton" if f_key == "all" else "TButton",
                command=lambda k=f_key: self._set_filter(k),
            )
            btn.pack(side="left", padx=(0, 4))
            self._filter_buttons[f_key] = btn

        cb_spk = tk.Checkbutton(
            ctrl_row,
            text="Also translate speaker names",
            variable=self.var_translate_speakers,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
            activebackground=t["bg_panel"],
            activeforeground=fg_panel,
        )
        cb_spk.pack(side="right")

        opts_row = tk.Frame(top, bg=t["bg_panel"])
        opts_row.pack(fill="x", pady=(4, 0))
        cb_wrap = tk.Checkbutton(
            opts_row,
            text=f"Auto Word Wrap imported lines to {DIALOGUE_MAX_DIGITS}d x {DIALOGUE_MAX_LINES}",
            variable=self.var_auto_word_wrap,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
            activebackground=t["bg_panel"],
            activeforeground=fg_panel,
        )
        cb_wrap.pack(side="right")

        # Outer scrollable list (single outer vertical scrollbar)
        list_wrap = tk.Frame(self, bg=t["bg_dark"], bd=1, relief="solid")
        list_wrap.pack(fill="both", expand=True, padx=12, pady=6)

        self.list_canvas = tk.Canvas(list_wrap, bg=t["bg_dark"], highlightthickness=0)
        self.outer_vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=self.outer_vsb.set)

        self.outer_vsb.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)

        self.rows_frame = tk.Frame(self.list_canvas, bg=t["bg_dark"])
        self._canvas_win_id = self.list_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")

        self.rows_frame.bind("<Configure>", self._on_rows_configure)
        self.list_canvas.bind("<Configure>", self._on_canvas_configure)
        self.list_canvas.bind("<MouseWheel>", self._on_outer_mousewheel)
        self.rows_frame.bind("<MouseWheel>", self._on_outer_mousewheel)

        # Bottom action bar
        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=12, pady=8)
        btn_bar.pack(fill="x", side="bottom")

        ttk.Button(btn_bar, text="Cancel", style="TButton", command=self._on_close).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Apply Import", style="Pink.TButton", command=self._on_apply_import).pack(
            side="right", padx=4
        )

    def _on_rows_configure(self, _event: Optional[tk.Event] = None) -> None:
        if self.list_canvas.winfo_exists():
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        if self.list_canvas.winfo_exists() and self._canvas_win_id is not None:
            self.list_canvas.itemconfig(self._canvas_win_id, width=event.width)

    def _on_outer_mousewheel(self, event: tk.Event) -> str:
        if self.list_canvas.winfo_exists() and getattr(event, "delta", 0):
            self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_reload_index(self) -> None:
        self.xuat_index = self.app._get_or_build_xuat_index(force_rebuild=True)
        self._populate_rows()

    def _get_immutable_jp_key(self, box_idx: int, box: Box) -> str:
        """Resolve immutable JP source key by box_uid (BUG-25 / DEP-7)."""
        b_uid = _get_box_uid(box)
        orig_map = getattr(self.app, "_original_jp_by_uid", {})
        if b_uid is not None and b_uid in orig_map and orig_map[b_uid]:
            return orig_map[b_uid]
        if hasattr(self.app, "sync_manager") and self.app.sync_manager is not None:
            jp = self.app.sync_manager.get_jp_key(b_uid)
            if jp:
                return jp
        return box.clean_text

    def _populate_rows(self) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self._rows.clear()
        self._speaker_matches.clear()
        self._focused_box_widget = None

        doc = self.app.current_doc
        if not doc or not doc.boxes:
            return

        t = self.app.theme
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_editor = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")
        fg_muted = t["fg_muted"]

        measure_font = self.app._get_dialogue_measure_font()
        safe_w = self.app._get_54d_reference_safe_w()
        line_h = max(14, int(measure_font.metrics("linespace")))
        box_px_w = safe_w + 10
        box_px_h = line_h * 3 + 8

        orig_map = getattr(self.app, "_original_jp_by_uid", {})
        stats = analyze_story_matches(doc, orig_map, self.xuat_index)
        self.lbl_summary.config(
            text=(
                f"Dialogue: {stats['dialogue_matched']}/{stats['dialogue_total']} matched "
                f"({stats['dialogue_duplicates']} duplicates, {stats['dialogue_missing']} missing)  |  "
                f"Speakers: {stats['speaker_matched']}/{stats['speaker_total']} matched "
                f"({stats['speaker_missing']} missing)  |  "
                f"Files indexed: {len(self.xuat_index.files_indexed)}"
            )
        )

        # Update filter chip labels
        chip_counts = {
            "all": stats["dialogue_total"],
            "duplicates": stats["dialogue_duplicates"],
            "missing": stats["dialogue_missing"],
            "matched": stats["dialogue_matched"],
        }
        chip_names = {"all": "All", "duplicates": "Duplicates", "missing": "Missing", "matched": "Matched"}
        for k, btn in self._filter_buttons.items():
            btn.config(text=f"{chip_names[k]} ({chip_counts[k]})")

        global_overrides = getattr(self.app, "_xuat_global_choice_overrides", {})

        for idx, box in enumerate(doc.boxes):
            b_uid = _get_box_uid(box)
            jp_key = self._get_immutable_jp_key(idx, box)
            norm_k = normalize_xuat_key(jp_key, strip_ngui=True)
            lookup = self.xuat_index.lookup_candidates(jp_key)
            is_locked = self.app.is_box_locked(idx)

            if box.speaker:
                sp_hit = self.xuat_index.lookup_translation(box.speaker)
                if sp_hit is not None:
                    self._speaker_matches[idx] = sp_hit

            # Determine default candidate index (respecting in-memory global override if any)
            cand_idx = 0
            if lookup.candidates and norm_k in global_overrides:
                pref_val = global_overrides[norm_k]
                for ci, cand in enumerate(lookup.candidates):
                    if cand.value == pref_val:
                        cand_idx = ci
                        break

            row_bg = t["bg_dark"] if is_locked else t["bg_panel"]
            card = tk.Frame(
                self.rows_frame,
                bg=row_bg,
                bd=1,
                relief="solid",
                highlightbackground=t["border"],
                highlightthickness=1,
                padx=8,
                pady=6,
            )
            card.pack(fill="x", padx=6, pady=4)
            card.bind("<MouseWheel>", self._on_outer_mousewheel)

            # Row Header
            hdr = tk.Frame(card, bg=row_bg)
            hdr.pack(fill="x", pady=(0, 4))
            hdr.bind("<MouseWheel>", self._on_outer_mousewheel)

            spk_label = box.speaker if box.speaker else "(Narration)"
            tk.Label(
                hdr,
                text=f"Box #{idx + 1:03d} — {spk_label}",
                font=("Segoe UI", 9, "bold"),
                bg=row_bg,
                fg=fg_muted if is_locked else t["misora_pink"],
            ).pack(side="left")

            if is_locked:
                tk.Label(
                    hdr,
                    text="🔒 Locked (Auto-Skip)",
                    font=("Segoe UI", 8, "bold"),
                    bg=row_bg,
                    fg=fg_muted,
                ).pack(side="left", padx=(8, 4))

            var_skip = tk.BooleanVar(master=self, value=is_locked)
            cb_skip = tk.Checkbutton(
                hdr,
                text="Skip",
                variable=var_skip,
                state="disabled" if is_locked else "normal",
                bg=row_bg,
                fg=fg_muted if is_locked else fg_panel,
                disabledforeground=fg_muted,
                selectcolor=t["bg_dark"],
                activebackground=row_bg,
                activeforeground=fg_panel,
            )
            cb_skip.pack(side="right")

            # Provenance + duplicate controls
            prov_text = lookup.candidates[cand_idx].provenance if lookup.candidates else "No XUAT match"
            lbl_provenance = tk.Label(
                hdr,
                text=prov_text,
                font=("Consolas", 8),
                bg=row_bg,
                fg=fg_muted,
            )
            lbl_provenance.pack(side="right", padx=(6, 8))

            lbl_dup_counter = tk.Label(hdr, text="", font=("Segoe UI", 8, "bold"), bg=row_bg, fg=t["accent_blue"])
            var_scope = tk.StringVar(master=self, value="This Box")
            if lookup.status == "duplicate":
                scope_cmb = ttk.Combobox(
                    hdr,
                    textvariable=var_scope,
                    values=("This Box", "This Story", "Global"),
                    state="readonly",
                    width=10,
                )
                scope_cmb.pack(side="right", padx=(4, 4))
                scope_cmb.bind(
                    "<<ComboboxSelected>>",
                    lambda _e, r_idx=idx: self._apply_conflict_scope(r_idx),
                )

                btn_next = ttk.Button(hdr, text="▶", width=2, style="Small.TButton", command=lambda r_idx=idx: self._step_candidate(r_idx, 1))
                btn_next.pack(side="right", padx=(1, 2))
                lbl_dup_counter.config(text=f"{cand_idx + 1}/{len(lookup.candidates)}")
                lbl_dup_counter.pack(side="right", padx=2)
                btn_prev = ttk.Button(hdr, text="◀", width=2, style="Small.TButton", command=lambda r_idx=idx: self._step_candidate(r_idx, -1))
                btn_prev.pack(side="right", padx=(2, 1))

            # Paired Left (Story) & Right (XUAT) 3x50 read-only boxes
            pair_frame = tk.Frame(card, bg=row_bg)
            pair_frame.pack(fill="x")
            pair_frame.bind("<MouseWheel>", self._on_outer_mousewheel)

            left_col = tk.Frame(pair_frame, bg=row_bg)
            left_col.pack(side="left", padx=(0, 8))
            left_hdr = tk.Frame(left_col, bg=row_bg)
            left_hdr.pack(fill="x")
            tk.Label(left_hdr, text="Story (JP / Current)", font=("Segoe UI", 8), bg=row_bg, fg=fg_muted).pack(side="left")
            left_m = self.app._measure_dialogue_metrics(jp_key)
            left_ov_badge = ("▼" if left_m["has_line_overflow"] else "") + ("▶" if left_m["has_width_overflow"] else "")
            lbl_left_overflow = tk.Label(left_hdr, text=left_ov_badge, font=("Segoe UI", 8, "bold"), bg=row_bg, fg=t["accent_yellow"])
            lbl_left_overflow.pack(side="right")

            left_wrap = tk.Frame(left_col, width=box_px_w, height=box_px_h, bg=t["bg_editor"], bd=1, relief="solid")
            left_wrap.pack_propagate(False)
            left_wrap.pack()

            txt_left = tk.Text(
                left_wrap,
                font=measure_font,
                height=3,
                width=50,
                wrap="none",
                bg=t["bg_dark"] if is_locked else t["bg_editor"],
                fg=fg_muted if is_locked else fg_editor,
                bd=0,
                highlightthickness=0,
                padx=3,
                pady=2,
            )
            txt_left.insert("1.0", jp_key)
            txt_left.config(state="disabled")
            txt_left.pack(fill="both", expand=True)

            right_col = tk.Frame(pair_frame, bg=row_bg)
            right_col.pack(side="left")
            right_hdr = tk.Frame(right_col, bg=row_bg)
            right_hdr.pack(fill="x")
            tk.Label(right_hdr, text="XUAT Match", font=("Segoe UI", 8), bg=row_bg, fg=fg_muted).pack(side="left")

            right_text = lookup.candidates[cand_idx].value if lookup.candidates else ""
            right_m = self.app._measure_dialogue_metrics(right_text)
            right_ov_badge = ("▼" if right_m["has_line_overflow"] else "") + ("▶" if right_m["has_width_overflow"] else "")
            lbl_right_overflow = tk.Label(right_hdr, text=right_ov_badge, font=("Segoe UI", 8, "bold"), bg=row_bg, fg=t["accent_yellow"])
            lbl_right_overflow.pack(side="right")

            right_wrap = tk.Frame(right_col, width=box_px_w, height=box_px_h, bg=t["bg_editor"], bd=1, relief="solid")
            right_wrap.pack_propagate(False)
            right_wrap.pack()

            txt_right = tk.Text(
                right_wrap,
                font=measure_font,
                height=3,
                width=50,
                wrap="none",
                bg=t["bg_dark"] if is_locked else t["bg_editor"],
                fg=fg_muted if is_locked else fg_editor,
                bd=0,
                highlightthickness=0,
                padx=3,
                pady=2,
            )
            txt_right.insert("1.0", right_text)
            txt_right.config(state="disabled")
            txt_right.pack(fill="both", expand=True)

            self._bind_paired_box_events(txt_left, left_m["has_line_overflow"], left_m["has_width_overflow"])
            self._bind_paired_box_events(txt_right, right_m["has_line_overflow"], right_m["has_width_overflow"])

            self._rows.append(
                {
                    "box_idx": idx,
                    "box_uid": b_uid,
                    "norm_key": norm_k,
                    "status": lookup.status,
                    "candidates": lookup.candidates,
                    "cand_idx": cand_idx,
                    "is_locked": is_locked,
                    "var_skip": var_skip,
                    "cb_skip": cb_skip,
                    "var_scope": var_scope,
                    "frame": card,
                    "left_wrap": left_wrap,
                    "right_wrap": right_wrap,
                    "txt_left": txt_left,
                    "txt_right": txt_right,
                    "lbl_left_overflow": lbl_left_overflow,
                    "lbl_right_overflow": lbl_right_overflow,
                    "lbl_provenance": lbl_provenance,
                    "lbl_dup_counter": lbl_dup_counter,
                }
            )

        self._set_filter(self._active_filter)

    def _bind_paired_box_events(self, txt: tk.Text, has_v: bool, has_h: bool) -> None:
        """Focus-gated inner vertical wheel & horizontal Shift+Wheel/drag; outer scroll otherwise."""
        def _on_press(event: tk.Event) -> None:
            self._focused_box_widget = txt
            try:
                txt.focus_set()
                if has_h:
                    txt.scan_mark(event.x, event.y)
            except Exception:
                pass

        def _on_drag(event: tk.Event) -> None:
            if self._focused_box_widget is txt and has_h:
                try:
                    txt.scan_dragto(event.x, event.y, gain=1)
                except Exception:
                    pass

        def _on_focus_out(_event: tk.Event) -> None:
            if self._focused_box_widget is txt:
                self._focused_box_widget = None

        def _on_wheel(event: tk.Event) -> str:
            if self._focused_box_widget is txt and has_v and getattr(event, "delta", 0):
                try:
                    txt.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass
                return "break"
            return self._on_outer_mousewheel(event)

        def _on_shift_wheel(event: tk.Event) -> str:
            if self._focused_box_widget is txt and has_h and getattr(event, "delta", 0):
                try:
                    txt.xview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass
                return "break"
            return self._on_outer_mousewheel(event)

        txt.bind("<ButtonPress-1>", _on_press)
        txt.bind("<B1-Motion>", _on_drag)
        txt.bind("<FocusOut>", _on_focus_out)
        txt.bind("<MouseWheel>", _on_wheel)
        txt.bind("<Shift-MouseWheel>", _on_shift_wheel)

    def _step_candidate(self, row_idx: int, delta: int) -> None:
        if not (0 <= row_idx < len(self._rows)):
            return
        row = self._rows[row_idx]
        cands = row["candidates"]
        if len(cands) <= 1:
            return
        new_ci = (row["cand_idx"] + delta) % len(cands)
        self._select_candidate(row_idx, new_ci)
        self._apply_conflict_scope(row_idx)

    def _select_candidate(self, row_idx: int, cand_idx: int) -> None:
        row = self._rows[row_idx]
        cands = row["candidates"]
        if not (0 <= cand_idx < len(cands)):
            return
        row["cand_idx"] = cand_idx
        chosen = cands[cand_idx]
        txt_r = row["txt_right"]
        if txt_r.winfo_exists():
            txt_r.config(state="normal")
            txt_r.delete("1.0", tk.END)
            txt_r.insert("1.0", chosen.value)
            txt_r.config(state="disabled")
        rm = self.app._measure_dialogue_metrics(chosen.value)
        ov_badge = ("▼" if rm["has_line_overflow"] else "") + ("▶" if rm["has_width_overflow"] else "")
        row["lbl_right_overflow"].config(text=ov_badge)
        row["lbl_provenance"].config(text=chosen.provenance)
        row["lbl_dup_counter"].config(text=f"{cand_idx + 1}/{len(cands)}")

    def _apply_conflict_scope(self, row_idx: int) -> None:
        """Apply 3-tier duplicate conflict scope (This Box / This Story / Global in-memory opt-in)."""
        row = self._rows[row_idx]
        cands = row["candidates"]
        if not cands:
            return
        chosen = cands[row["cand_idx"]]
        scope = row["var_scope"].get()
        norm_k = row["norm_key"]
        if scope in ("This Story", "Global"):
            for other_idx, other in enumerate(self._rows):
                if other_idx == row_idx or other["norm_key"] != norm_k:
                    continue
                for ci, c in enumerate(other["candidates"]):
                    if c.value == chosen.value:
                        self._select_candidate(other_idx, ci)
                        break
        if scope == "Global" and norm_k:
            if not hasattr(self.app, "_xuat_global_choice_overrides"):
                self.app._xuat_global_choice_overrides = {}
            self.app._xuat_global_choice_overrides[norm_k] = chosen.value

    def _set_filter(self, filter_key: str) -> None:
        self._active_filter = filter_key
        for k, btn in self._filter_buttons.items():
            btn.configure(style="Pink.TButton" if k == filter_key else "TButton")
        for row in self._rows:
            st = row["status"]
            show = (
                filter_key == "all"
                or (filter_key == "duplicates" and st == "duplicate")
                or (filter_key == "missing" and st == "missing")
                or (filter_key == "matched" and st in ("matched", "duplicate"))
            )
            if show:
                if not row["frame"].winfo_manager():
                    row["frame"].pack(fill="x", padx=6, pady=4)
            else:
                if row["frame"].winfo_manager():
                    row["frame"].pack_forget()
        self._on_rows_configure()

    @staticmethod
    def _format_box_list(nums: List[int]) -> str:
        if not nums:
            return "None"
        return ", ".join(f"Box #{n}" for n in nums)

    def _on_apply_import(self) -> bool:
        """Show Pre-Apply summary prompt and apply unlocked, non-skipped boxes in ONE Undo batch."""
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            return False

        translate_speakers = bool(self.var_translate_speakers.get())
        to_import_nums: List[int] = []
        lock_skipped_nums: List[int] = []
        user_skipped_nums: List[int] = []
        missing_count = 0
        plan: List[Tuple[int, Any, str, str, Any]] = []

        for row in self._rows:
            b_idx = row["box_idx"]
            b_num = b_idx + 1
            if self.app.is_box_locked(b_idx) or row["is_locked"]:
                lock_skipped_nums.append(b_num)
                continue
            if row["var_skip"].get():
                user_skipped_nums.append(b_num)
                continue
            cands = row["candidates"]
            if not cands:
                missing_count += 1
                continue
            box = doc.boxes[b_idx]
            chosen_entry = cands[row["cand_idx"]]
            new_tx = chosen_entry.value
            new_sp = box.speaker
            if translate_speakers and b_idx in self._speaker_matches and box.kind == "print":
                new_sp = self._speaker_matches[b_idx]
            to_import_nums.append(b_num)
            plan.append((b_idx, row["box_uid"], new_sp, new_tx, chosen_entry))

        prompt = (
            "Confirm XUAT Import Summary:\n\n"
            f"1. Boxes to import ({len(to_import_nums)}): {self._format_box_list(to_import_nums)}\n"
            f"2. Skipped — Translation Lock (🔒) ({len(lock_skipped_nums)}): {self._format_box_list(lock_skipped_nums)}\n"
            f"3. Skipped — User Skip ({len(user_skipped_nums)}): {self._format_box_list(user_skipped_nums)}\n"
            f"4. Missing / Untranslated: {missing_count} box(es)\n\n"
            "Proceed with importing these translations?"
        )
        if not messagebox.askyesno("Confirm XUAT Import", prompt, parent=self):
            return False

        if not plan:
            self.app.show_toast("No eligible boxes to import.")
            return False

        self.app._commit_widget_edit()

        auto_wrap = bool(self.var_auto_word_wrap.get()) if self.var_auto_word_wrap is not None else False
        measure_fn = None
        safe_w = 1
        if auto_wrap:
            measure_fn, safe_w = self.app._get_word_wrap_params()

        applied_count = 0
        still_over_3 = 0
        applied_records: List[AppliedXuatRecord] = []
        self.app.undo_journal.begin_batch("Import from XUAT")
        try:
            for b_idx, b_uid, new_sp, raw_tx, chosen_entry in plan:
                if not (0 <= b_idx < len(doc.boxes)):
                    continue
                if self.app.is_box_locked(b_idx):
                    continue
                new_tx = (
                    wrap_text(raw_tx, measure_fn, safe_w, reflow_existing_breaks=False).wrapped_text
                    if (auto_wrap and measure_fn is not None)
                    else raw_tx
                )
                old_box = doc.boxes[b_idx]
                old_sp = old_box.speaker
                old_tx = old_box.clean_text
                if new_sp == old_sp and new_tx == old_tx:
                    continue
                if auto_wrap and self.app._measure_dialogue_metrics(new_tx)["has_line_overflow"]:
                    still_over_3 += 1
                old_segs = [s.text for s in old_box.segs]
                # Mutate AST first (BUG-13)
                doc.inject_box(b_idx, new_sp, new_tx)
                new_segs = [s.text for s in doc.boxes[b_idx].segs]
                self.app.undo_journal.record(
                    BoxEditDelta(
                        box_index=b_idx,
                        old_speaker=old_sp,
                        new_speaker=new_sp,
                        old_text=old_tx,
                        new_text=new_tx,
                        file_path=str(self.app.current_file_path) if self.app.current_file_path else "",
                        box_uid=b_uid,
                        source="xuat_import",
                        old_seg_texts=old_segs,
                        new_seg_texts=new_segs,
                    )
                )
                self.app._modified_boxes.add(b_idx)
                if b_uid is not None and hasattr(self.app, "_modified_box_uids"):
                    self.app._modified_box_uids.add(b_uid)
                applied_records.append(
                    AppliedXuatRecord(
                        file_path=chosen_entry.file_path,
                        line_number=chosen_entry.line_number,
                        raw_key=chosen_entry.raw_key,
                        value=chosen_entry.value,
                        box_index=b_idx,
                    )
                )
                applied_count += 1
        finally:
            self.app.undo_journal.end_batch()

        xuat_idx_snapshot = self.xuat_index
        source_fps = dict(getattr(xuat_idx_snapshot, "file_fingerprints", {}) or {})

        if applied_count > 0:
            self.app._mark_document_dirty(self.app.current_file_path)
            self.app._dirty_state_changed()
            self.app._update_views()
            msg = f"✓ Imported XUAT translations for {applied_count} box(es)"
            if auto_wrap:
                msg += f" ({still_over_3} still >3 lines)"
            self.app.show_toast(msg)
        else:
            self.app.show_toast("No changes were applied from XUAT.")

        self._on_close()
        if applied_count > 0 and applied_records and xuat_idx_snapshot is not None:
            existing_cleanup = getattr(self.app, "_xuat_cleanup_dialog", None)
            if existing_cleanup is not None:
                try:
                    if existing_cleanup.winfo_exists():
                        existing_cleanup.destroy()
                except Exception:
                    pass
                self.app._xuat_cleanup_dialog = None
            # Guardrail 1: open non-blockingly without wait_window() or grab_set()
            cleanup_dlg = XuatCleanupDialog(
                self.app,
                xuat_index=xuat_idx_snapshot,
                doc=doc,
                applied_records=applied_records,
                source_fingerprints=source_fps,
                mode="post_import",
            )
            self.app._xuat_cleanup_dialog = cleanup_dlg
        return applied_count > 0

    def _on_close(self) -> None:
        self._focused_box_widget = None
        self._rows.clear()
        self._filter_buttons.clear()
        self._speaker_matches.clear()
        self.var_translate_speakers = None
        self.var_auto_word_wrap = None
        try:
            for w in (self.list_canvas, self.rows_frame):
                if w and w.winfo_exists():
                    w.unbind("<MouseWheel>")
                    w.unbind("<Configure>")
        except Exception:
            pass
        if getattr(self.app, "_import_xuat_dialog", None) is self:
            self.app._import_xuat_dialog = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()


# =============================================================================
# XUAT Cleanup & Archival Dialogs (S07 / U01)
# =============================================================================
class XuatCleanupSettingsDialog(tk.Toplevel):
    """Modal configuration dialog for Debug > Safety > XUAT Cleanup & Archive Settings..."""

    def __init__(self, parent: "MisoraApp") -> None:
        super().__init__(parent)
        self.app = parent
        self.title("XUAT Cleanup & Archive Settings")
        self.geometry("560x340")
        self.minsize(500, 300)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        self.var_archive_dir = tk.StringVar(master=self, value=str(self.app._get_xuat_archive_dir()))
        self.var_archive_ext = tk.StringVar(
            master=self,
            value=str(getattr(self.app, "xuat_archive_ext", DEFAULT_ARCHIVE_EXT) or DEFAULT_ARCHIVE_EXT),
        )
        self.var_strategy = tk.StringVar(
            master=self,
            value=str(getattr(self.app, "xuat_archive_strategy", "combined") or "combined"),
        )

        self._build_ui(t)
        self.var_archive_dir.trace_add("write", lambda *_a: self._refresh_warning())
        self.var_archive_ext.trace_add("write", lambda *_a: self._refresh_warning())
        self.var_strategy.trace_add("write", lambda *_a: self._refresh_warning())
        self._refresh_warning()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

    def _build_ui(self, t: dict) -> None:
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_editor = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        body = tk.Frame(self, bg=t["bg_panel"], padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="XUAT Cleanup & Archive Settings",
            font=("Segoe UI", 11, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w", pady=(0, 8))

        r_dir = tk.Frame(body, bg=t["bg_panel"])
        r_dir.pack(fill="x", pady=4)
        tk.Label(r_dir, text="Archive Folder:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        tk.Entry(r_dir, textvariable=self.var_archive_dir, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid").pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(r_dir, text="Browse...", style="Small.TButton", command=self._browse_dir).pack(side="left", padx=(2, 2))
        ttk.Button(r_dir, text="Default", style="Small.TButton", command=self._reset_default_dir).pack(side="left")

        r_ext = tk.Frame(body, bg=t["bg_panel"])
        r_ext.pack(fill="x", pady=4)
        tk.Label(r_ext, text="Archive Extension:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        tk.Entry(r_ext, textvariable=self.var_archive_ext, width=16, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid").pack(side="left", padx=4)
        tk.Label(r_ext, text="(Default: .xuat.old — avoid .txt)", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left", padx=4)

        strat_box = tk.LabelFrame(
            body,
            text="Default Archive Strategy",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
        )
        strat_box.pack(fill="x", pady=(8, 6))
        ttk.Radiobutton(
            strat_box,
            text="Combined archive (xuat_removed_archive.xuat.old — canonical UTF-8/LF + original encoding metadata)",
            variable=self.var_strategy,
            value="combined",
            style="Panel.TRadiobutton",
        ).pack(anchor="w", pady=1)
        ttk.Radiobutton(
            strat_box,
            text="Per-source file (<source>.xuat.old — preserves original encoding, BOM & newline byte-for-byte)",
            variable=self.var_strategy,
            value="per_source_file",
            style="Panel.TRadiobutton",
        ).pack(anchor="w", pady=1)

        self.lbl_warning = tk.Label(
            body,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=t["bg_panel"],
            fg="#e69f00",
            wraplength=510,
            justify="left",
            anchor="w",
        )
        self.lbl_warning.pack(fill="x", pady=(6, 0))

        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=16, pady=10)
        btn_bar.pack(fill="x", side="bottom")
        ttk.Button(btn_bar, text="Cancel", style="TButton", command=self._on_close).pack(side="right", padx=(6, 0))
        ttk.Button(btn_bar, text="Save Settings", style="Pink.TButton", command=self._on_save).pack(side="right")

    def _browse_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Select XUAT Archive Folder",
            initialdir=self.var_archive_dir.get() or str(SCRIPT_DIR),
            parent=self,
        )
        if chosen:
            self.var_archive_dir.set(chosen)

    def _reset_default_dir(self) -> None:
        self.var_archive_dir.set(str(default_archive_dir(SCRIPT_DIR)))
        self.var_archive_ext.set(DEFAULT_ARCHIVE_EXT)

    def _refresh_warning(self) -> None:
        if not self.winfo_exists():
            return
        res = validate_archive_target(
            self.var_archive_dir.get().strip(),
            self.var_archive_ext.get().strip(),
            self.var_strategy.get(),
            source_paths=(),
            xuat_roots=self.app._get_xuat_index_roots(),
        )
        msgs = list(res.errors) + list(res.warnings)
        self.lbl_warning.config(text="\n".join(f"⚠ {m}" for m in msgs))

    def _on_save(self) -> None:
        raw_dir = self.var_archive_dir.get().strip()
        raw_ext = self.var_archive_ext.get().strip() or DEFAULT_ARCHIVE_EXT
        if not raw_ext.startswith("."):
            raw_ext = "." + raw_ext
        strat = self.var_strategy.get()
        if strat not in VALID_ARCHIVE_STRATEGIES:
            strat = "combined"
        self.app.xuat_archive_dir = Path(raw_dir) if raw_dir else None
        self.app.xuat_archive_ext = raw_ext
        self.app.xuat_archive_strategy = strat
        self.app._save_user_prefs(silent=True)
        self.app.lbl_status.config(text="XUAT cleanup & archive settings saved.")
        self._on_close()

    def _on_close(self) -> None:
        self.var_archive_dir = None  # type: ignore[assignment]
        self.var_archive_ext = None  # type: ignore[assignment]
        self.var_strategy = None  # type: ignore[assignment]
        if getattr(self.app, "_xuat_cleanup_settings_dialog", None) is self:
            self.app._xuat_cleanup_settings_dialog = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()


class XuatCleanupDialog(tk.Toplevel):
    """Post-import and manual XUAT cleanup/archival review dialog (U01)."""

    def __init__(
        self,
        parent: "MisoraApp",
        xuat_index: XuatIndex,
        doc: Any,
        applied_records: Sequence[AppliedXuatRecord] = (),
        source_fingerprints: Optional[Dict[Path, str]] = None,
        mode: str = "post_import",
    ) -> None:
        super().__init__(parent)
        self.app = parent
        self.xuat_index = xuat_index
        self.doc = doc
        self.applied_records = list(applied_records)
        self.mode = mode
        self.last_report: Optional[CleanupReport] = None

        self.title("Post-Import XUAT Cleanup & Archive" if mode == "post_import" else "Clean / Archive XUAT")
        self.geometry("860x640")
        self.minsize(720, 520)
        self.transient(parent)

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        self.var_duplicate_scope = tk.StringVar(master=self, value="selected_only")
        self.var_linebreak_policy = tk.StringVar(master=self, value="remove_line_break")
        self.var_archive_strategy = tk.StringVar(
            master=self,
            value=str(getattr(self.app, "xuat_archive_strategy", "combined") or "combined"),
        )
        self.var_archive_dir = tk.StringVar(master=self, value=str(self.app._get_xuat_archive_dir()))
        self.var_archive_ext = tk.StringVar(
            master=self,
            value=str(getattr(self.app, "xuat_archive_ext", DEFAULT_ARCHIVE_EXT) or DEFAULT_ARCHIVE_EXT),
        )
        self.var_allow_unarchived = tk.BooleanVar(master=self, value=False)
        self.var_include_applied = tk.BooleanVar(master=self, value=True)
        self._cand_vars: List[Tuple[CleanupCandidate, tk.BooleanVar]] = []

        self._analysis = classify_cleanup_candidates(
            self.xuat_index,
            self.doc,
            applied_records=self.applied_records,
            duplicate_scope=self.var_duplicate_scope.get(),
        )
        if source_fingerprints:
            self._analysis.source_fingerprints = dict(source_fingerprints)

        self._build_ui(t)
        self._populate_candidates()
        self._refresh_safety_banner()
        self._refresh_archive_warning()

        self.var_archive_dir.trace_add("write", lambda *_a: self._refresh_archive_warning())
        self.var_archive_ext.trace_add("write", lambda *_a: self._refresh_archive_warning())
        self.var_archive_strategy.trace_add("write", lambda *_a: self._refresh_archive_warning())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

    def _build_ui(self, t: dict) -> None:
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        fg_editor = best_contrast_fg(t["bg_editor"], t["fg_text"], "#ffffff")

        top = tk.Frame(self, bg=t["bg_panel"], padx=14, pady=10)
        top.pack(fill="x")

        tk.Label(
            top,
            text="XUAT Cleanup & Mandatory Archival" if self.mode != "post_import" else "Import Complete — Optional XUAT Cleanup & Archive",
            font=("Segoe UI", 12, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w")

        self.lbl_safety_warning = tk.Label(
            top,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#4a1f28",
            fg="#ffd6de",
            padx=8,
            pady=4,
            anchor="w",
            justify="left",
        )

        self.lbl_counts = tk.Label(
            top,
            text="",
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=fg_panel,
            anchor="w",
        )
        self.lbl_counts.pack(fill="x", pady=(4, 4))

        applied_n = self._analysis.counts_by_tier.get("applied", 0)
        if applied_n > 0:
            tk.Checkbutton(
                top,
                text=f"Remove lines successfully applied during this import ({applied_n} entries)",
                variable=self.var_include_applied,
                command=self._on_toggle_applied,
                bg=t["bg_panel"],
                fg=fg_panel,
                selectcolor=t["bg_dark"],
                activebackground=t["bg_panel"],
                activeforeground=fg_panel,
            ).pack(anchor="w", pady=(0, 4))

        opts_grid = tk.Frame(top, bg=t["bg_panel"])
        opts_grid.pack(fill="x", pady=(2, 4))

        # Conditional Duplicate Scope (hidden when 0 duplicates exist)
        self._dup_scope_frame = tk.LabelFrame(
            opts_grid,
            text="Duplicate Key Scope",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=4,
        )
        ttk.Radiobutton(
            self._dup_scope_frame,
            text="Selected occurrence only",
            variable=self.var_duplicate_scope,
            value="selected_only",
            style="Panel.TRadiobutton",
            command=self._on_duplicate_scope_changed,
        ).pack(anchor="w")
        ttk.Radiobutton(
            self._dup_scope_frame,
            text="All duplicate occurrences (exact normalized key)",
            variable=self.var_duplicate_scope,
            value="all_duplicates",
            style="Panel.TRadiobutton",
            command=self._on_duplicate_scope_changed,
        ).pack(anchor="w")
        if self._analysis.has_duplicates:
            self._dup_scope_frame.pack(side="left", fill="y", padx=(0, 8))

        lb_frame = tk.LabelFrame(
            opts_grid,
            text="Linebreak Policy",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=4,
        )
        lb_frame.pack(side="left", fill="y")
        ttk.Radiobutton(
            lb_frame,
            text="Remove line break too",
            variable=self.var_linebreak_policy,
            value="remove_line_break",
            style="Panel.TRadiobutton",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb_frame,
            text="Keep blank line (preserve line numbers)",
            variable=self.var_linebreak_policy,
            value="keep_blank_line",
            style="Panel.TRadiobutton",
        ).pack(anchor="w")

        # Mandatory Archive Box
        arch_box = tk.LabelFrame(
            top,
            text="Mandatory Archive Settings",
            bg=t["bg_panel"],
            fg=fg_panel,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
        )
        arch_box.pack(fill="x", pady=(4, 0))

        strat_row = tk.Frame(arch_box, bg=t["bg_panel"])
        strat_row.pack(fill="x", pady=(0, 4))
        ttk.Radiobutton(
            strat_row,
            text="Combined (UTF-8/LF + encoding metadata)",
            variable=self.var_archive_strategy,
            value="combined",
            style="Panel.TRadiobutton",
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            strat_row,
            text="Per-source-file (raw encoding/BOM/EOL)",
            variable=self.var_archive_strategy,
            value="per_source_file",
            style="Panel.TRadiobutton",
        ).pack(side="left")

        path_row = tk.Frame(arch_box, bg=t["bg_panel"])
        path_row.pack(fill="x", pady=2)
        tk.Label(path_row, text="Dir:", font=("Segoe UI", 8), bg=t["bg_panel"], fg=fg_panel).pack(side="left")
        tk.Entry(path_row, textvariable=self.var_archive_dir, font=("Segoe UI", 8), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid").pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(path_row, text="Browse...", style="Small.TButton", command=self._browse_archive_dir).pack(side="left", padx=(0, 6))
        tk.Label(path_row, text="Ext:", font=("Segoe UI", 8), bg=t["bg_panel"], fg=fg_panel).pack(side="left")
        tk.Entry(path_row, textvariable=self.var_archive_ext, width=11, font=("Segoe UI", 8), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid").pack(side="left", padx=(4, 0))

        self.lbl_archive_warning = tk.Label(
            arch_box,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=t["bg_panel"],
            fg="#e69f00",
            wraplength=790,
            justify="left",
            anchor="w",
        )

        tk.Checkbutton(
            arch_box,
            text="Advanced: Delete without archiving (Not Recommended — requires separate irreversible confirmation)",
            variable=self.var_allow_unarchived,
            bg=t["bg_panel"],
            fg=t["fg_muted"],
            selectcolor=t["bg_dark"],
            activebackground=t["bg_panel"],
            activeforeground=fg_panel,
        ).pack(anchor="w", pady=(4, 0))

        # Scrollable candidate list
        list_wrap = tk.Frame(self, bg=t["bg_dark"], bd=1, relief="solid")
        list_wrap.pack(fill="both", expand=True, padx=14, pady=6)

        self.cands_canvas = tk.Canvas(list_wrap, bg=t["bg_dark"], highlightthickness=0)
        vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.cands_canvas.yview)
        self.cands_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.cands_canvas.pack(side="left", fill="both", expand=True)

        self.cands_frame = tk.Frame(self.cands_canvas, bg=t["bg_dark"])
        self._cands_win_id = self.cands_canvas.create_window((0, 0), window=self.cands_frame, anchor="nw")
        self.cands_frame.bind("<Configure>", lambda _e=None: self.cands_canvas.configure(scrollregion=self.cands_canvas.bbox("all")) if self.cands_canvas.winfo_exists() else None)
        self.cands_canvas.bind("<Configure>", lambda e: self.cands_canvas.itemconfig(self._cands_win_id, width=e.width) if self.cands_canvas.winfo_exists() else None)

        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=14, pady=8)
        btn_bar.pack(fill="x", side="bottom")
        ttk.Button(btn_bar, text="Close (Keep XUAT Untouched)", style="TButton", command=self._on_close).pack(side="right", padx=(6, 0))
        ttk.Button(btn_bar, text="Clean / Archive Selected", style="Pink.TButton", command=self._on_execute_cleanup).pack(side="right")

    def _refresh_safety_banner(self) -> None:
        if not self.winfo_exists():
            return
        enabled = bool(self.app.var_xuat_safety_backup.get()) if hasattr(self.app, "var_xuat_safety_backup") else True
        if not enabled:
            self.lbl_safety_warning.config(
                text="⚠ WARNING: 'Auto-backup XUAT files before cleanup edits' is OFF in Debug > Safety. Modified or emptied files will NOT have a safety backup!"
            )
            if not self.lbl_safety_warning.winfo_manager():
                self.lbl_safety_warning.pack(fill="x", pady=(4, 2))
        else:
            if self.lbl_safety_warning.winfo_manager():
                self.lbl_safety_warning.pack_forget()

    def _refresh_archive_warning(self) -> None:
        if not self.winfo_exists():
            return
        src_paths = sorted({c.file_path for c in self._analysis.candidates})
        res = validate_archive_target(
            self.var_archive_dir.get().strip(),
            self.var_archive_ext.get().strip(),
            self.var_archive_strategy.get(),
            source_paths=src_paths,
            xuat_roots=self.app._get_xuat_index_roots(),
        )
        msgs = list(res.errors) + list(res.warnings)
        if msgs:
            self.lbl_archive_warning.config(text="\n".join(f"⚠ {m}" for m in msgs))
            if not self.lbl_archive_warning.winfo_manager():
                self.lbl_archive_warning.pack(fill="x", pady=(4, 0))
        else:
            self.lbl_archive_warning.config(text="")
            if self.lbl_archive_warning.winfo_manager():
                self.lbl_archive_warning.pack_forget()

    def _browse_archive_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Select XUAT Archive Folder",
            initialdir=self.var_archive_dir.get() or str(SCRIPT_DIR),
            parent=self,
        )
        if chosen:
            self.var_archive_dir.set(chosen)

    def _on_toggle_applied(self) -> None:
        val = bool(self.var_include_applied.get())
        for cand, var in self._cand_vars:
            if cand.tier == "applied":
                cand.selected = val
                var.set(val)

    def _on_duplicate_scope_changed(self) -> None:
        scope = self.var_duplicate_scope.get()
        apply_duplicate_scope(self._analysis.candidates, scope)
        for cand, var in self._cand_vars:
            if cand.tier == "duplicate":
                var.set(cand.selected)

    def _populate_candidates(self) -> None:
        for child in self.cands_frame.winfo_children():
            child.destroy()
        self._cand_vars.clear()

        counts = self._analysis.counts_by_tier
        self.lbl_counts.config(
            text=(
                f"Preview — Applied: {counts.get('applied', 0)}  |  "
                f"Duplicates: {counts.get('duplicate', 0)}  |  "
                f"Already Translated (Unique): {counts.get('already_translated_unique', 0)}  |  "
                f"Uncertain (Unchecked by Default): {counts.get('uncertain', 0)}"
            )
        )

        t = self.app.theme
        fg_panel = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        tier_labels = {
            "applied": ("[Applied]", t["misora_pink"]),
            "duplicate": ("[Duplicate]", t["accent_blue"]),
            "already_translated_unique": ("[Already Translated (Unique)]", "#4caf50"),
            "uncertain": ("[Uncertain — Unchecked by Default]", "#e69f00"),
        }

        if not self._analysis.candidates:
            tk.Label(
                self.cands_frame,
                text="No cleanup candidates found for this story.",
                font=("Segoe UI", 9),
                bg=t["bg_dark"],
                fg=t["fg_muted"],
                pady=20,
            ).pack()
            return

        for cand in self._analysis.candidates:
            row_f = tk.Frame(self.cands_frame, bg=t["bg_panel"], bd=1, relief="solid", padx=8, pady=4)
            row_f.pack(fill="x", padx=6, pady=3)

            var = tk.BooleanVar(master=self, value=bool(cand.selected))
            self._cand_vars.append((cand, var))

            tag_txt, tag_fg = tier_labels.get(cand.tier, (f"[{cand.tier}]", fg_panel))
            hdr = tk.Frame(row_f, bg=t["bg_panel"])
            hdr.pack(fill="x")
            tk.Checkbutton(
                hdr,
                text=f"{cand.rel_path}:{cand.line_number}",
                variable=var,
                font=("Consolas", 8, "bold"),
                bg=t["bg_panel"],
                fg=fg_panel,
                selectcolor=t["bg_dark"],
                activebackground=t["bg_panel"],
                activeforeground=fg_panel,
            ).pack(side="left")
            tk.Label(hdr, text=tag_txt, font=("Segoe UI", 8, "bold"), bg=t["bg_panel"], fg=tag_fg).pack(side="left", padx=(6, 6))
            tk.Label(hdr, text=cand.reason, font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="right")

            preview_line = f"{cand.raw_key}={cand.raw_value}"
            if len(preview_line) > 140:
                preview_line = preview_line[:137] + "..."
            tk.Label(
                row_f,
                text=preview_line,
                font=("Consolas", 8),
                bg=t["bg_panel"],
                fg=fg_panel,
                anchor="w",
            ).pack(fill="x", padx=(20, 0))

    def _on_execute_cleanup(self) -> bool:
        for cand, var in self._cand_vars:
            cand.selected = bool(var.get())

        selected = [c for c in self._analysis.candidates if c.selected]
        if not selected:
            self.app.show_toast("No XUAT entries selected for cleanup.")
            return False

        allow_unarchived = bool(self.var_allow_unarchived.get())
        if allow_unarchived:
            confirm_unarchived = messagebox.askyesno(
                "Confirm Irreversible Unarchived Deletion",
                f"You opted out of mandatory XUAT archiving.\n\n"
                f"{len(selected)} entry/entries will be PERMANENTLY DELETED from XUAT source file(s) "
                "without writing an archive file.\n\n"
                "Proceed with irreversible unarchived deletion?",
                icon="warning",
                default=messagebox.NO,
                parent=self,
            )
            if not confirm_unarchived:
                return False

        safety_enabled = (
            bool(self.app.var_xuat_safety_backup.get())
            if hasattr(self.app, "var_xuat_safety_backup")
            else bool(getattr(self.app, "xuat_safety_backup_enabled", True))
        )
        story_name = self.app.current_file_path.name if getattr(self.app, "current_file_path", None) else ""
        arch_dir = Path(self.var_archive_dir.get().strip() or str(self.app._get_xuat_archive_dir()))
        arch_ext = self.var_archive_ext.get().strip() or DEFAULT_ARCHIVE_EXT

        try:
            report = execute_cleanup(
                candidates=self._analysis.candidates,
                source_fingerprints=self._analysis.source_fingerprints,
                archive_dir=arch_dir,
                archive_ext=arch_ext,
                archive_strategy=self.var_archive_strategy.get(),
                linebreak_policy=self.var_linebreak_policy.get(),
                safety_backup_enabled=safety_enabled,
                safety_backup_dir=self.app._get_backup_dir(),
                backup_path_fn=make_collision_resistant_backup_path,
                allow_unarchived_deletion=allow_unarchived,
                story_name=story_name,
                reason=self.mode,
                xuat_roots=self.app._get_xuat_index_roots(),
            )
        except StaleSourceError as exc:
            messagebox.showerror("Stale XUAT Source Files", str(exc), parent=self)
            return False
        except ArchiveTargetError as exc:
            messagebox.showerror("Invalid Archive Destination", str(exc), parent=self)
            return False
        except Exception as exc:
            self.app.logger.exception("XUAT cleanup failed:", exc)
            messagebox.showerror("XUAT Cleanup Failed", str(exc), parent=self)
            return False

        self.last_report = report
        if report.errors:
            err_lines = "\n".join(f"- {p.name}: {msg}" for p, msg in report.errors)
            messagebox.showwarning(
                "Partial Cleanup Completed with Errors",
                f"Modified: {len(report.modified_files)} | "
                f"Rolled back/Untouched: {len(report.rolled_back_files) + len(report.untouched_files)}\n\n"
                f"Errors:\n{err_lines}",
                parent=self,
            )

        # Second explicit confirmation for meaningfully empty XUAT files
        if report.empty_files:
            detail_lines = []
            for ef in report.empty_files:
                if ef.safety_backup_path is not None:
                    bak_desc = f"Safety backup: {ef.safety_backup_path}"
                else:
                    bak_desc = "NOT protected by automatic safety backup"
                detail_lines.append(f"- {ef.file_path}\n  ({bak_desc})")
            empty_prompt = (
                "The following XUAT file(s) now contain no remaining translation entries "
                "(only comments/whitespace or empty):\n\n"
                + "\n".join(detail_lines)
                + "\n\nDelete these empty XUAT file(s)?"
            )
            if messagebox.askyesno(
                "Delete Meaningfully Empty XUAT Files?",
                empty_prompt,
                icon="warning",
                default=messagebox.NO,
                parent=self,
            ):
                delete_empty_xuat_files([ef.file_path for ef in report.empty_files])

        summary = (
            f"✓ XUAT cleanup: removed {report.removed_count} line(s) across "
            f"{len(report.modified_files)} file(s)"
        )
        self.app.show_toast(summary)
        self.app.lbl_status.config(text=summary)
        if getattr(self.app, "_ui_ready", False) and hasattr(self.app, "_refresh_xuat_index_async"):
            self.app._refresh_xuat_index_async()
        self._on_close()
        return True

    def _on_close(self) -> None:
        self._cand_vars.clear()
        self.var_duplicate_scope = None  # type: ignore[assignment]
        self.var_linebreak_policy = None  # type: ignore[assignment]
        self.var_archive_strategy = None  # type: ignore[assignment]
        self.var_archive_dir = None  # type: ignore[assignment]
        self.var_archive_ext = None  # type: ignore[assignment]
        self.var_allow_unarchived = None  # type: ignore[assignment]
        self.var_include_applied = None  # type: ignore[assignment]
        if getattr(self.app, "_xuat_cleanup_dialog", None) is self:
            self.app._xuat_cleanup_dialog = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()


# =============================================================================
# Translator Suite Dialogs (#4A, #16, #17)
# =============================================================================
class MTLSettingsDialog(tk.Toplevel):
    """Configuration dialog for Machine Translation providers, API keys, endpoints and options."""
    def __init__(self, parent: "MisoraApp"):
        super().__init__(parent)
        self.app = parent
        self.title("Configure MTL Sources & Keys")
        self.geometry("640x600")
        self.minsize(580, 520)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        self.worker_queue: queue.Queue = queue.Queue()
        self._test_seq: int = 0
        self._poll_job: Optional[str] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

        content = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        content.pack(fill="both", expand=True)

        hdr = tk.Frame(content, bg=t["bg_panel"])
        hdr.pack(fill="x", pady=(0, 10))
        tk.Label(
            hdr,
            text="Machine Translation & External Providers",
            font=("Segoe UI", 12, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(side="left")

        # Active Engine Row
        r_eng = tk.Frame(content, bg=t["bg_panel"])
        r_eng.pack(fill="x", pady=4)
        tk.Label(r_eng, text="Active Engine:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=fg_panel, width=18, anchor="w").pack(side="left")
        self.var_engine = tk.StringVar(master=self, value=self.app.mtl_config.active_engine)
        cb_engine = ttk.Combobox(r_eng, textvariable=self.var_engine, values=MTL_ENGINES, state="readonly", width=22)
        cb_engine.pack(side="left", padx=4)

        # Languages Row
        r_lang = tk.Frame(content, bg=t["bg_panel"])
        r_lang.pack(fill="x", pady=4)
        tk.Label(r_lang, text="Languages:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=fg_panel, width=18, anchor="w").pack(side="left")
        tk.Label(r_lang, text="From:", bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left")
        self.var_src = tk.StringVar(master=self, value=self.app.mtl_config.src_lang)
        ent_src = tk.Entry(r_lang, textvariable=self.var_src, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid", width=6)
        ent_src.pack(side="left", padx=(2, 10))
        tk.Label(r_lang, text="To:", bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left")
        self.var_tgt = tk.StringVar(master=self, value=self.app.mtl_config.tgt_lang)
        ent_tgt = tk.Entry(r_lang, textvariable=self.var_tgt, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid", width=6)
        ent_tgt.pack(side="left", padx=2)
        tk.Label(r_lang, text="(e.g. ja -> en)", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(side="left", padx=8)

        ttk.Separator(content, orient="horizontal").pack(fill="x", pady=8)

        # DeepL Section
        sec_deepl = tk.LabelFrame(content, text="DeepL API Settings", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], padx=10, pady=8)
        sec_deepl.pack(fill="x", pady=4)

        r_dp1 = tk.Frame(sec_deepl, bg=t["bg_panel"])
        r_dp1.pack(fill="x", pady=2)
        tk.Label(r_dp1, text="Auth Key:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        self.var_deepl_key = tk.StringVar(master=self, value=self.app.mtl_config.deepl_api_key)
        self.ent_deepl_key = tk.Entry(r_dp1, textvariable=self.var_deepl_key, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid", show="*")
        self.ent_deepl_key.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.var_show_key = tk.BooleanVar(master=self, value=False)
        def _toggle_key():
            self.ent_deepl_key.config(show="" if self.var_show_key.get() else "*")
        tk.Checkbutton(r_dp1, text="Show", variable=self.var_show_key, command=_toggle_key, bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(side="left")

        r_dp2 = tk.Frame(sec_deepl, bg=t["bg_panel"])
        r_dp2.pack(fill="x", pady=2)
        self.var_deepl_pro = tk.BooleanVar(master=self, value=self.app.mtl_config.deepl_use_pro)
        tk.Checkbutton(
            r_dp2,
            text="Use DeepL Pro subscription endpoint (api.deepl.com instead of api-free.deepl.com)",
            variable=self.var_deepl_pro,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
        ).pack(side="left")

        # Local MT Section
        sec_local = tk.LabelFrame(content, text="Local MT / Sugoi / LibreTranslate", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], padx=10, pady=8)
        sec_local.pack(fill="x", pady=4)

        r_loc = tk.Frame(sec_local, bg=t["bg_panel"])
        r_loc.pack(fill="x", pady=2)
        tk.Label(r_loc, text="Server URL:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        self.var_local_url = tk.StringVar(master=self, value=self.app.mtl_config.local_mtl_url)
        ent_loc = tk.Entry(r_loc, textvariable=self.var_local_url, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid")
        ent_loc.pack(side="left", fill="x", expand=True)
        tk.Label(sec_local, text="Default Sugoi Toolkit: http://127.0.0.1:14366  |  LibreTranslate: http://127.0.0.1:5000/translate", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"]).pack(anchor="w", pady=(2, 0))

        # LLM Section
        sec_llm = tk.LabelFrame(content, text="OpenAI / LLM Endpoint (Ollama, LM Studio, etc.)", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], padx=10, pady=8)
        sec_llm.pack(fill="x", pady=4)

        r_llm1 = tk.Frame(sec_llm, bg=t["bg_panel"])
        r_llm1.pack(fill="x", pady=2)
        tk.Label(r_llm1, text="Base URL:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        self.var_llm_url = tk.StringVar(master=self, value=self.app.mtl_config.llm_base_url)
        ent_llm_url = tk.Entry(r_llm1, textvariable=self.var_llm_url, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid")
        ent_llm_url.pack(side="left", fill="x", expand=True)

        r_llm2 = tk.Frame(sec_llm, bg=t["bg_panel"])
        r_llm2.pack(fill="x", pady=2)
        tk.Label(r_llm2, text="Model Name:", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel, width=16, anchor="w").pack(side="left")
        self.var_llm_model = tk.StringVar(master=self, value=self.app.mtl_config.llm_model)
        ent_llm_model = tk.Entry(r_llm2, textvariable=self.var_llm_model, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid", width=24)
        ent_llm_model.pack(side="left", padx=(0, 10))

        tk.Label(r_llm2, text="API Key (optional):", font=("Segoe UI", 9), bg=t["bg_panel"], fg=fg_panel).pack(side="left")
        self.var_llm_key = tk.StringVar(master=self, value=self.app.mtl_config.llm_api_key)
        ent_llm_key = tk.Entry(r_llm2, textvariable=self.var_llm_key, font=("Segoe UI", 9), bg=t["bg_editor"], fg=fg_editor, bd=1, relief="solid", show="*")
        ent_llm_key.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Behavior & Cache Section
        sec_opt = tk.Frame(content, bg=t["bg_panel"])
        sec_opt.pack(fill="x", pady=6)

        self.var_protect = tk.BooleanVar(master=self, value=self.app.mtl_config.protect_tags)
        tk.Checkbutton(sec_opt, text="Shield NGUI tags, Ruby tags & {playername} during translation", variable=self.var_protect, bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(anchor="w")

        self.var_xuat_cache = tk.BooleanVar(master=self, value=self.app.mtl_config.use_xuat_cache)
        tk.Checkbutton(sec_opt, text="Use loaded XUAT translation dictionary as instant offline lookup", variable=self.var_xuat_cache, bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(anchor="w")

        r_to = tk.Frame(sec_opt, bg=t["bg_panel"])
        r_to.pack(fill="x", pady=2)
        tk.Label(r_to, text="Timeout (sec):", bg=t["bg_panel"], fg=fg_panel).pack(side="left")
        self.var_timeout = tk.DoubleVar(master=self, value=self.app.mtl_config.timeout_sec)
        sp_to = ttk.Spinbox(r_to, from_=3.0, to=60.0, increment=1.0, textvariable=self.var_timeout, width=6)
        sp_to.pack(side="left", padx=6)

        # Connection Test Box
        tst_box = tk.Frame(content, bg=t["bg_editor"], bd=1, relief="solid", padx=8, pady=6)
        tst_box.pack(fill="x", pady=6)

        self.lbl_tst_result = tk.Label(tst_box, text="Click 'Test Connection' to verify active engine.", font=("Segoe UI", 9), bg=t["bg_editor"], fg=t["fg_muted"], anchor="w")
        self.lbl_tst_result.pack(side="left", fill="x", expand=True)

        self.btn_tst = ttk.Button(tst_box, text="Test Connection", style="Small.TButton", command=self._on_test_connection)
        self.btn_tst.pack(side="right")

        # Bottom Buttons
        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        btn_bar.pack(fill="x", side="bottom")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda _e=None: self._on_cancel())

        ttk.Button(btn_bar, text="Cancel", style="TButton", command=self._on_cancel).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Save & Apply", style="Pink.TButton", command=self._on_save).pack(side="right", padx=4)

        ttk.Button(btn_bar, text="AI Prompt Settings...", style="Small.TButton", command=self._open_ai_prompt).pack(side="left")

    def _on_cancel(self) -> None:
        safe_grab_release(self)
        self.destroy()

    def _open_ai_prompt(self):
        self.app.on_open_ai_prompt_settings()

    def _get_draft_config(self) -> MTLConfig:
        cfg = MTLConfig(
            active_engine=self.var_engine.get(),
            src_lang=self.var_src.get().strip() or "ja",
            tgt_lang=self.var_tgt.get().strip() or "en",
            deepl_api_key=self.var_deepl_key.get().strip(),
            deepl_use_pro=self.var_deepl_pro.get(),
            local_mtl_url=self.var_local_url.get().strip(),
            llm_base_url=self.var_llm_url.get().strip(),
            llm_api_key=self.var_llm_key.get().strip(),
            llm_model=self.var_llm_model.get().strip() or "qwen2.5:7b",
            llm_system_prompt=self.app.mtl_config.llm_system_prompt,
            protect_tags=self.var_protect.get(),
            use_xuat_cache=self.var_xuat_cache.get(),
            timeout_sec=float(self.var_timeout.get()),
            rate_limit_delay=self.app.mtl_config.rate_limit_delay,
            ai_prompt_include_header=self.app.mtl_config.ai_prompt_include_header,
            ai_prompt_include_speaker=self.app.mtl_config.ai_prompt_include_speaker,
        )
        return cfg

    def _on_test_connection(self):
        cfg = self._get_draft_config()
        self.lbl_tst_result.config(text=f"Testing {cfg.active_engine}...", fg=self.app.theme["fg_text"])
        self.btn_tst.config(state="disabled")

        self._test_seq += 1
        seq = self._test_seq
        q = self.worker_queue

        def worker():
            engine = MTLEngine(cfg)
            ok, msg = engine.test_connection(cfg)
            q.put(("test_result", seq, ok, msg))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        self._schedule_poll()

    def _schedule_poll(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if self.winfo_exists():
            self._poll_job = self.after(50, self._poll_worker_queue)

    def _poll_worker_queue(self):
        self._poll_job = None
        if not self.winfo_exists():
            return

        try:
            while True:
                msg = self.worker_queue.get_nowait()
                if msg[0] == "test_result":
                    _, seq, ok, text = msg
                    if seq == self._test_seq and self.winfo_exists():
                        self.btn_tst.config(state="normal")
                        col = self.app.theme.get("accent_green", "#2e7d32") if ok else self.app.theme.get("accent_yellow", "#f57c00")
                        self.lbl_tst_result.config(text=text, fg=col)
        except queue.Empty:
            pass

        if self.winfo_exists() and str(self.btn_tst.cget("state")) == "disabled":
            self._schedule_poll()

    def _on_close(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()

    def _on_save(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        prev_engine = getattr(self.app.mtl_config, "active_engine", None)
        self.app.mtl_config = self._get_draft_config()
        if prev_engine != self.app.mtl_config.active_engine and hasattr(self.app, "_cancel_mtl_all_batch"):
            self.app._cancel_mtl_all_batch()
        if self.app.mtl_config.use_xuat_cache and getattr(self.app, "xuat_index", None) is None:
            if hasattr(self.app, "_refresh_xuat_index_async"):
                self.app._refresh_xuat_index_async()
        self.app._save_user_prefs()
        self.app.show_toast(f"✓ Saved MTL preferences ({self.app.mtl_config.active_engine})")
        safe_grab_release(self)
        self.destroy()
        messagebox.showinfo(
            "Settings Saved",
            f"Machine Translation settings ({self.app.mtl_config.active_engine}) have been saved.",
            parent=self.app,
        )


class AIPromptSettingsDialog(tk.Toplevel):
    """Configuration dialog for AI Prompt Header, Instructions, and Script Exporter."""
    def __init__(self, parent: "MisoraApp"):
        super().__init__(parent)
        self.app = parent
        self.title("AI / LLM Prompt & Script Settings")
        self.geometry("680x560")
        self.minsize(580, 480)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        content = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text="AI Translation Prompt Header & Rules",
            font=("Segoe UI", 12, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            content,
            text=(
                "Customize the system rules and context given to AI translation models (ChatGPT, Claude, Ollama, etc.).\n"
                "The header will be prepended when you copy the entire script using 'Copy AI Translation Prompt'."
            ),
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        # Checkboxes
        opts_frame = tk.Frame(content, bg=t["bg_panel"])
        opts_frame.pack(fill="x", pady=4)

        self.var_include_hdr = tk.BooleanVar(master=self, value=self.app.mtl_config.ai_prompt_include_header)
        tk.Checkbutton(
            opts_frame,
            text="Include Prompt Header & Rules when copying script",
            variable=self.var_include_hdr,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.var_include_spk = tk.BooleanVar(master=self, value=self.app.mtl_config.ai_prompt_include_speaker)
        tk.Checkbutton(
            opts_frame,
            text="Include Speaker Names in CSIF headers (@@Speaker / @@_)",
            variable=self.var_include_spk,
            bg=t["bg_panel"],
            fg=fg_panel,
            selectcolor=t["bg_dark"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        # Multi-line text for header
        txt_frame = tk.Frame(content, bg=t["bg_editor"], bd=1, relief="solid")
        txt_frame.pack(fill="both", expand=True, pady=8)

        self.txt_prompt = tk.Text(
            txt_frame,
            wrap="word",
            font=("Segoe UI", 9),
            bg=t["bg_editor"],
            fg=fg_editor,
            insertbackground=t["misora_pink"],
            bd=0,
            padx=8,
            pady=8,
        )
        sb = tk.Scrollbar(txt_frame, command=self.txt_prompt.yview)
        sb.pack(side="right", fill="y")
        self.txt_prompt.pack(side="left", fill="both", expand=True)
        self.txt_prompt.config(yscrollcommand=sb.set)

        self.txt_prompt.insert("1.0", self.app.mtl_config.llm_system_prompt)

        # Bottom buttons
        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        btn_bar.pack(fill="x", side="bottom")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda _e=None: self._on_cancel())

        ttk.Button(btn_bar, text="Reset to Recommended Default", style="Small.TButton", command=self._reset_default).pack(side="left")
        ttk.Button(btn_bar, text="📋 Copy Script with Prompt Now", style="Small.TButton", command=self._copy_prompt_now).pack(side="left", padx=8)

        ttk.Button(btn_bar, text="Cancel", style="TButton", command=self._on_cancel).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Save & Close", style="Pink.TButton", command=self._save_and_close).pack(side="right", padx=4)

    def _on_cancel(self) -> None:
        safe_grab_release(self)
        self.destroy()

    def _reset_default(self):
        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert("1.0", DEFAULT_LLM_PROMPT)

    def _copy_prompt_now(self):
        self._apply_settings_to_app()
        self.app.on_copy_ai_prompt()

    def _apply_settings_to_app(self):
        self.app.mtl_config.llm_system_prompt = self.txt_prompt.get("1.0", tk.END).strip()
        self.app.mtl_config.ai_prompt_include_header = self.var_include_hdr.get()
        self.app.mtl_config.ai_prompt_include_speaker = self.var_include_spk.get()
        self.app._save_user_prefs(silent=True)

    def _save_and_close(self):
        self._apply_settings_to_app()
        self.app.show_toast("✓ Saved AI prompt configuration")
        safe_grab_release(self)
        self.destroy()
        messagebox.showinfo(
            "Settings Saved",
            "AI translation prompt header & settings have been saved.",
            parent=self.app,
        )


class TranslatorAssistantDialog(tk.Toplevel):
    """
    Dedicated floating Translation Assistant workspace.
    Displays original Japanese, active engine output, comparison cards, and 1-click apply.
    """
    def __init__(self, parent: "MisoraApp"):
        super().__init__(parent)
        self.app = parent
        self.title("Misora - Translator Assistant")
        self.geometry("620x580")
        self.minsize(540, 480)
        self.transient(parent)

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        fg_panel = best_contrast_fg(t["bg_panel"])
        fg_editor = best_contrast_fg(t["bg_editor"])

        self.worker_queue: queue.Queue = queue.Queue()
        self._req_seq: int = 0
        self._poll_job: Optional[str] = None
        self._comp_widgets: Dict[str, Tuple[tk.Label, ttk.Button]] = {}

        # Top Bar: Box navigation and engine selector
        top_bar = tk.Frame(self, bg=t["bg_panel"], padx=14, pady=8)
        top_bar.pack(fill="x")

        self.lbl_box_info = tk.Label(
            top_bar,
            text="Box 0 / 0",
            font=("Segoe UI", 10, "bold"),
            bg=t["bg_panel"],
            fg=t["misora_pink"],
        )
        self.lbl_box_info.pack(side="left")

        ttk.Button(top_bar, text="< Prev", style="Nav.TButton", command=self._on_prev).pack(side="left", padx=(10, 2))
        ttk.Button(top_bar, text="Next >", style="Nav.TButton", command=self._on_next).pack(side="left", padx=2)

        self.lbl_speaker = tk.Label(
            top_bar,
            text="Speaker: -",
            font=("Segoe UI", 9),
            bg=t["bg_panel"],
            fg=t["fg_muted"],
        )
        self.lbl_speaker.pack(side="left", padx=(10, 0))

        # Pin on Top & Engine selector on right (#6)
        self._is_pinned_top = False
        self.btn_pin = ttk.Button(
            top_bar,
            text="📌",
            style="Small.TButton",
            width=3,
            command=self._toggle_pin_top,
        )
        self.btn_pin.pack(side="right", padx=(4, 0))

        # Engine selector on right
        self.var_engine = tk.StringVar(master=self, value=self.app.mtl_config.active_engine)
        cb = ttk.Combobox(top_bar, textvariable=self.var_engine, values=MTL_ENGINES, state="readonly", width=14)
        cb.pack(side="right", padx=(4, 0))
        cb.bind("<<ComboboxSelected>>", self._on_engine_change)

        ttk.Button(top_bar, text="Fetch All", style="Small.TButton", command=self._on_fetch_all).pack(side="right", padx=2)
        ttk.Button(top_bar, text="Translate (F8)", style="Pink.TButton", command=self._on_translate).pack(side="right", padx=2)

        # Original Japanese Box
        orig_frame = tk.LabelFrame(self, text="Original Dialogue (Japanese)", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=fg_panel, padx=10, pady=6)
        orig_frame.pack(fill="x", padx=14, pady=(4, 6))

        self.txt_orig = tk.Text(
            orig_frame,
            wrap="word",
            height=4,
            font=("Segoe UI", 10),
            bg=t["bg_editor"],
            fg=fg_editor,
            bd=1,
            relief="solid",
            padx=6,
            pady=6,
        )
        self.txt_orig.pack(fill="x")

        # Translated Dialogue Box
        trans_frame = tk.LabelFrame(self, text="Translated Dialogue (Editable)", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], padx=10, pady=6)
        trans_frame.pack(fill="both", expand=True, padx=14, pady=4)

        self.txt_trans = tk.Text(
            trans_frame,
            wrap="word",
            font=("Segoe UI", 10),
            bg=t["bg_editor"],
            fg=fg_editor,
            insertbackground=t["misora_pink"],
            bd=1,
            relief="solid",
            padx=6,
            pady=6,
        )
        self.txt_trans.pack(fill="both", expand=True)

        # Multi-engine comparison frame (collapsible)
        self.comp_frame = tk.LabelFrame(self, text="Engine Comparison", font=("Segoe UI", 8, "bold"), bg=t["bg_panel"], fg=t["fg_muted"], padx=8, pady=4)

        # Status / Feedback label
        self.lbl_status = tk.Label(self, text="Ready", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"], anchor="w", padx=14)
        self.lbl_status.pack(fill="x", pady=(2, 0))

        # Bottom Action Bar
        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=14, pady=10)
        btn_bar.pack(fill="x", side="bottom")

        ttk.Button(btn_bar, text="Close", style="TButton", command=self._on_close).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Copy Translation", style="Small.TButton", command=self._on_copy).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Apply & Next (Alt+S)", style="TButton", command=self._on_apply_and_next).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Apply to Box (Ctrl+Enter)", style="Pink.TButton", command=self._on_apply).pack(side="right", padx=4)

        ttk.Button(btn_bar, text="Configure Engines...", style="Small.TButton", command=self.app.on_open_mtl_settings).pack(side="left")

        # Key bindings
        self.bind("<Escape>", lambda _e=None: self._on_close())
        self.bind("<F8>", lambda e: self._on_translate())
        self.bind("<Control-Return>", lambda e: self._on_apply())
        self.bind("<Alt-Left>", lambda e: self._on_prev())
        self.bind("<Alt-Right>", lambda e: self._on_next())
        self.bind("<Alt-s>", lambda e: self._on_apply_and_next())
        self.bind("<Alt-S>", lambda e: self._on_apply_and_next())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_box()

    def _toggle_pin_top(self):
        self._is_pinned_top = not getattr(self, "_is_pinned_top", False)
        self.wm_attributes("-topmost", self._is_pinned_top)
        self.btn_pin.configure(text="📌" if self._is_pinned_top else "📍")
        status = "pinned on top" if self._is_pinned_top else "unpinned"
        self.app.show_toast(f"Translator Assistant {status}")

    def _schedule_poll(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if self.winfo_exists():
            self._poll_job = self.after(50, self._poll_worker_queue)

    def _poll_worker_queue(self):
        self._poll_job = None
        if not self.winfo_exists():
            return

        try:
            while True:
                msg = self.worker_queue.get_nowait()
                kind = msg[0]
                if kind == "translate_success":
                    _, meta, res = msg
                    file_p, doc_id, b_uid, src_hash, req_seq, eng = meta
                    if (
                        self.winfo_exists()
                        and self.app.current_doc
                        and id(self.app.current_doc) == doc_id
                        and str(self.app.current_file_path or "") == file_p
                        and req_seq == self._req_seq
                    ):
                        b_idx = self.app.current_box_idx
                        if 0 <= b_idx < len(self.app.current_doc.boxes):
                            curr_box = self.app.current_doc.boxes[b_idx]
                            if (
                                _get_box_uid(curr_box) == b_uid
                                and _hash_mtl_source(curr_box.clean_text) == src_hash
                            ):
                                self.txt_trans.delete("1.0", tk.END)
                                self.txt_trans.insert("1.0", res)
                                self.lbl_status.config(text=f"✓ Translated via {eng}")
                elif kind == "translate_error":
                    _, meta, err = msg
                    file_p, doc_id, b_uid, src_hash, req_seq, eng = meta
                    if (
                        self.winfo_exists()
                        and self.app.current_doc
                        and id(self.app.current_doc) == doc_id
                        and req_seq == self._req_seq
                    ):
                        self.lbl_status.config(text=f"❌ Translation failed: {err}")
                elif kind == "fetch_all_result":
                    _, meta, eng, ok, val = msg
                    file_p, doc_id, b_uid, src_hash, req_seq = meta[:5]
                    if (
                        self.winfo_exists()
                        and self.app.current_doc
                        and id(self.app.current_doc) == doc_id
                        and str(self.app.current_file_path or "") == file_p
                        and req_seq == self._req_seq
                    ):
                        b_idx = self.app.current_box_idx
                        if 0 <= b_idx < len(self.app.current_doc.boxes):
                            curr_box = self.app.current_doc.boxes[b_idx]
                            if (
                                _get_box_uid(curr_box) == b_uid
                                and _hash_mtl_source(curr_box.clean_text) == src_hash
                            ):
                                if eng in self._comp_widgets:
                                    lbl_val, btn_use = self._comp_widgets[eng]
                                    if lbl_val.winfo_exists() and btn_use.winfo_exists():
                                        if ok:
                                            fg_panel = best_contrast_fg(self.app.theme["bg_panel"])
                                            lbl_val.config(text=val, fg=fg_panel)
                                            btn_use.config(state="normal", command=lambda r=val: self._use_comp_text(r))
                                        else:
                                            lbl_val.config(text=f"Failed ({val})", fg=self.app.theme.get("accent_yellow", "#f57c00"))
        except queue.Empty:
            pass

        if self.winfo_exists():
            self._schedule_poll()

    def _on_close(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        self.app._translator_dialog = None
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()

    def _on_engine_change(self, _event=None):
        self.app.mtl_config.active_engine = self.var_engine.get()
        self.lbl_status.config(text=f"Active engine set to: {self.var_engine.get()}")

    def refresh_box(self):
        if not self.winfo_exists():
            return
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            self.lbl_box_info.config(text="Box 0 / 0")
            self.lbl_speaker.config(text="Speaker: -")
            self.txt_orig.config(state="normal")
            self.txt_orig.delete("1.0", tk.END)
            self.txt_orig.config(state="disabled")
            return

        b_idx = self.app.current_box_idx
        b_idx = max(0, min(b_idx, len(doc.boxes) - 1))
        box = doc.boxes[b_idx]

        self.lbl_box_info.config(text=f"Box {b_idx + 1} / {len(doc.boxes)}")
        self.lbl_speaker.config(text=f"Speaker: {box.speaker or '(None)'}")

        self.txt_orig.config(state="normal")
        self.txt_orig.delete("1.0", tk.END)
        self.txt_orig.insert("1.0", box.clean_text)
        self.txt_orig.config(state="disabled")

        self.txt_trans.delete("1.0", tk.END)
        self.txt_trans.insert("1.0", box.clean_text)
        self.lbl_status.config(text=f"Loaded Box {b_idx + 1}")

    def _on_prev(self):
        self.app.on_prev_box()
        self.refresh_box()

    def _on_next(self):
        self.app.on_next_box()
        self.refresh_box()

    def _on_translate(self):
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            return
        b_idx = self.app.current_box_idx
        if b_idx < 0 or b_idx >= len(doc.boxes):
            return
        box = doc.boxes[b_idx]
        text_to_tr = box.clean_text.strip()
        if not text_to_tr:
            return

        eng = self.var_engine.get()
        self.lbl_status.config(text=f"Translating via {eng}...")

        b_uid = _get_box_uid(box)
        doc_id = id(doc)
        file_p = str(self.app.current_file_path or "")
        src_hash = _hash_mtl_source(text_to_tr)
        self._req_seq += 1
        req_seq = self._req_seq
        meta = (file_p, doc_id, b_uid, src_hash, req_seq, eng)

        q = self.worker_queue

        def on_success(res: str):
            q.put(("translate_success", meta, res))

        def on_error(err: str):
            q.put(("translate_error", meta, str(err)))

        cfg = MTLConfig.from_dict(self.app.mtl_config.to_dict())
        cfg.active_engine = eng

        translate_async(
            text_to_tr,
            cfg,
            on_success=on_success,
            on_error=on_error,
            xuat_cache=getattr(self.app, "xuat_entries", None),
        )
        self._schedule_poll()

    def _on_fetch_all(self):
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            return
        b_idx = self.app.current_box_idx
        if b_idx < 0 or b_idx >= len(doc.boxes):
            return
        box = doc.boxes[b_idx]
        text_to_tr = doc.boxes[b_idx].clean_text.strip()
        if not text_to_tr:
            return

        if not self.comp_frame.winfo_ismapped():
            self.comp_frame.pack(fill="x", padx=14, pady=4, before=self.lbl_status)

        for w in self.comp_frame.winfo_children():
            w.destroy()

        t = self.app.theme
        b_uid = _get_box_uid(box)
        doc_id = id(doc)
        file_p = str(self.app.current_file_path or "")
        src_hash = _hash_mtl_source(text_to_tr)
        self._req_seq += 1
        req_seq = self._req_seq

        self._comp_widgets.clear()
        q = self.worker_queue

        engines_to_query = ["Google", "DeepL", "Local / Sugoi", "LLM / OpenAI", "XUAT Cache"]
        for eng in engines_to_query:
            row = tk.Frame(self.comp_frame, bg=t["bg_panel"])
            row.pack(fill="x", pady=1)

            lbl_name = tk.Label(row, text=f"[{eng}]:", font=("Segoe UI", 8, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], width=14, anchor="w")
            lbl_name.pack(side="left")

            lbl_val = tk.Label(row, text="Fetching...", font=("Segoe UI", 8), bg=t["bg_panel"], fg=t["fg_muted"], anchor="w")
            lbl_val.pack(side="left", fill="x", expand=True)

            btn_use = ttk.Button(row, text="Use", style="Small.TButton", width=4)
            btn_use.pack(side="right")
            btn_use.config(state="disabled")

            self._comp_widgets[eng] = (lbl_val, btn_use)

            meta = (file_p, doc_id, b_uid, src_hash, req_seq, eng)

            def make_worker(engine_name=eng, request_meta=meta):
                def worker():
                    cfg = MTLConfig.from_dict(self.app.mtl_config.to_dict())
                    cfg.active_engine = engine_name
                    engine = MTLEngine(cfg)
                    try:
                        res = engine.translate(text_to_tr, config=cfg, xuat_cache=getattr(self.app, "xuat_entries", None))
                        q.put(("fetch_all_result", request_meta, engine_name, True, res))
                    except Exception as exc:
                        q.put(("fetch_all_result", request_meta, engine_name, False, str(exc)))

                threading.Thread(target=worker, daemon=True).start()

            make_worker()
        self._schedule_poll()

    def _use_comp_text(self, text: str):
        self.txt_trans.delete("1.0", tk.END)
        self.txt_trans.insert("1.0", text)

    def _on_apply(self) -> bool:
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            return False
        b_idx = self.app.current_box_idx
        if b_idx < 0 or b_idx >= len(doc.boxes):
            return False
        if self.app.is_box_locked(b_idx):
            self.app.show_toast(f"🔒 Box {b_idx + 1} is locked against translation.")
            return False

        new_text = self.txt_trans.get("1.0", "end-1c")
        old_box = doc.boxes[b_idx]
        old_sp = old_box.speaker
        old_tx = old_box.clean_text
        box_uid = old_box.uid

        try:
            doc.inject_box(b_idx, old_sp, new_text)
        except Exception as e:
            self.app.logger.exception(f"Failed to apply translation to box {b_idx}:", e)
            self.app.set_status(f"Error applying translation to Box #{b_idx + 1}: {e}", is_error=True)
            return False

        self.app.undo_journal.record(
            BoxEditDelta(
                box_index=b_idx,
                old_speaker=old_sp,
                new_speaker=old_sp,
                old_text=old_tx,
                new_text=new_text,
                file_path=str(self.app.current_file_path) if self.app.current_file_path else "",
                box_uid=box_uid,
                source="mtl",
            )
        )
        self.app._modified_boxes.add(b_idx)
        self.app._mark_document_dirty(self.app.current_file_path)
        self.app._dirty_state_changed()
        self.app._update_views()
        self.app.show_toast(f"✓ Applied translation to Box {b_idx + 1}")
        return True

    def _on_apply_and_next(self):
        if self._on_apply():
            self._on_next()

    def _on_copy(self):
        t = self.txt_trans.get("1.0", tk.END).strip()
        if t:
            self.clipboard_clear()
            self.clipboard_append(t)
            self.app.show_toast("📋 Copied translation to clipboard")


class BatchTranslateDialog(tk.Toplevel):
    """Dialog for automated batch translation of an entire story bundle."""
    def __init__(self, parent: "MisoraApp"):
        super().__init__(parent)
        self.app = parent
        self.title("Batch Translate Story")
        self.geometry("560x420")
        self.minsize(500, 380)
        self.transient(parent)
        self.grab_set()

        t = self.app.theme
        self.configure(bg=t["bg_panel"])
        apply_window_icon(self)

        fg_panel = best_contrast_fg(t["bg_panel"])

        self._cancelled = False
        self._is_running = False
        self._batch_open: bool = False
        self._close_requested: bool = False
        self._poll_job: Optional[str] = None
        self.worker_queue: queue.Queue = queue.Queue()

        content = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="Batch Translation", font=("Segoe UI", 12, "bold"), bg=t["bg_panel"], fg=t["misora_pink"]).pack(anchor="w", pady=(0, 6))

        # Engine
        r_eng = tk.Frame(content, bg=t["bg_panel"])
        r_eng.pack(fill="x", pady=4)
        tk.Label(r_eng, text="Translation Engine:", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=fg_panel, width=18, anchor="w").pack(side="left")
        self.var_engine = tk.StringVar(master=self, value=self.app.mtl_config.active_engine)
        cb_eng = ttk.Combobox(r_eng, textvariable=self.var_engine, values=MTL_ENGINES, state="readonly", width=18)
        cb_eng.pack(side="left")

        # Scope
        sec_scope = tk.LabelFrame(content, text="Scope & Filter", font=("Segoe UI", 9, "bold"), bg=t["bg_panel"], fg=t["misora_pink"], padx=10, pady=6)
        sec_scope.pack(fill="x", pady=6)

        self.var_scope = tk.StringVar(master=self, value="untranslated")
        tk.Radiobutton(sec_scope, text="Untranslated Only (Contains Japanese characters)", variable=self.var_scope, value="untranslated", bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(anchor="w")
        tk.Radiobutton(sec_scope, text="All Boxes in Story", variable=self.var_scope, value="all", bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(anchor="w")
        tk.Radiobutton(sec_scope, text=f"From Current Box ({self.app.current_box_idx + 1}) to End", variable=self.var_scope, value="from_current", bg=t["bg_panel"], fg=fg_panel, selectcolor=t["bg_dark"]).pack(anchor="w")

        # Rate Limit Delay
        r_del = tk.Frame(content, bg=t["bg_panel"])
        r_del.pack(fill="x", pady=4)
        tk.Label(r_del, text="Delay between requests (sec):", bg=t["bg_panel"], fg=fg_panel).pack(side="left")
        self.var_delay = tk.DoubleVar(master=self, value=0.3)
        sp_del = ttk.Spinbox(r_del, from_=0.0, to=5.0, increment=0.1, textvariable=self.var_delay, width=6)
        sp_del.pack(side="left", padx=6)

        # Progress bar
        self.progress = ttk.Progressbar(content, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(12, 4))

        self.lbl_status = tk.Label(content, text="Ready to start batch translation.", font=("Segoe UI", 9), bg=t["bg_panel"], fg=t["fg_muted"], anchor="w")
        self.lbl_status.pack(fill="x", pady=2)

        # Bottom Buttons
        btn_bar = tk.Frame(self, bg=t["bg_panel"], padx=18, pady=12)
        btn_bar.pack(fill="x", side="bottom")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e=None: self._on_close())

        self.btn_close = ttk.Button(btn_bar, text="Close", style="TButton", command=self._on_close)
        self.btn_close.pack(side="right", padx=4)

        self.btn_start = ttk.Button(btn_bar, text="Start Batch", style="Pink.TButton", command=self._start_batch)
        self.btn_start.pack(side="right", padx=4)

    def _end_undo_batch(self) -> None:
        """Close open undo batch strictly once on the UI main thread (BUG-14)."""
        if getattr(self, "_batch_open", False):
            self._batch_open = False
            try:
                self.app.undo_journal.end_batch()
            except Exception as exc:
                self.app.logger.warning("MTL", f"end_batch error: {exc}")

    def _schedule_poll(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if self.winfo_exists():
            self._poll_job = self.after(50, self._poll_worker_queue)

    def _on_close(self):
        if self._is_running:
            self._cancelled = True
            self._close_requested = True
            try:
                self.withdraw()
            except Exception:
                pass
            return

        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

        self._end_undo_batch()
        safe_grab_release(self)
        if self.winfo_exists():
            self.destroy()

    def _start_batch(self):
        doc = self.app.current_doc
        if not doc or not doc.boxes:
            messagebox.showwarning("No Story Open", "Open a story bundle or text file first.")
            return

        jp_regex = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]")
        scope = self.var_scope.get()
        targets: List[int] = []
        skipped_locked = 0

        for i, box in enumerate(doc.boxes):
            if scope == "from_current" and i < self.app.current_box_idx:
                continue
            if self.app.is_box_locked(i):
                skipped_locked += 1
                continue
            if scope == "untranslated":
                if jp_regex.search(box.clean_text):
                    targets.append(i)
            else:
                targets.append(i)

        if not targets:
            msg = "No boxes matching selected criteria."
            if skipped_locked > 0:
                msg += f" ({skipped_locked} locked boxes were skipped)"
            self.lbl_status.config(text=msg)
            messagebox.showinfo("Batch Complete", msg)
            return

        self._cancelled = False
        self._is_running = True
        self._close_requested = False
        self.btn_start.config(state="disabled")
        self.progress.config(maximum=len(targets), value=0)

        # Drain any stale messages from queue
        while not self.worker_queue.empty():
            try:
                self.worker_queue.get_nowait()
            except queue.Empty:
                break

        cfg = MTLConfig.from_dict(self.app.mtl_config.to_dict())
        cfg.active_engine = self.var_engine.get()
        delay = float(self.var_delay.get())
        engine = MTLEngine(cfg)
        xuat_cache = getattr(self.app, "xuat_entries", None)

        # Snapshot target box data on UI thread (Rule 15)
        target_inputs = [
            (b_idx, doc.boxes[b_idx].speaker, doc.boxes[b_idx].clean_text)
            for b_idx in targets
        ]

        # Begin undo batch on UI thread before worker thread starts
        self.app.undo_journal.begin_batch(f"Batch Translate ({len(targets)} boxes)")
        self._batch_open = True

        def worker():
            translated_count = 0
            try:
                for step, (b_idx, spk, raw_text) in enumerate(target_inputs):
                    if self._cancelled:
                        break
                    raw_clean = raw_text.strip()
                    if not raw_clean:
                        continue
                    try:
                        res = engine.translate(raw_clean, config=cfg, xuat_cache=xuat_cache)
                        translated_count += 1
                        self.worker_queue.put(("progress", step + 1, b_idx, spk, raw_text, res))
                    except Exception as exc:
                        self.worker_queue.put(("error", step + 1, b_idx, str(exc)))

                    if delay > 0 and step < len(target_inputs) - 1:
                        time.sleep(delay)
            finally:
                self.worker_queue.put(("done", translated_count, skipped_locked))

        threading.Thread(target=worker, daemon=True).start()
        self._schedule_poll()

    def _poll_worker_queue(self):
        self._poll_job = None
        if not self.winfo_exists():
            return
        done_received = False
        final_count = 0
        final_skipped = 0
        try:
            while True:
                msg = self.worker_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, step, b_idx, spk, old_tx, new_tx = msg
                    if self.winfo_exists() and not self._close_requested:
                        self.progress.config(value=step)
                        self.lbl_status.config(text=f"Translating Box {b_idx + 1} ({step} / {self.progress['maximum']})...")
                    # Apply on main UI thread (Rule 15)
                    doc = self.app.current_doc
                    if doc and 0 <= b_idx < len(doc.boxes):
                        if not self.app.is_box_locked(b_idx):
                            # Mutate AST first (S07 / BUG-13)
                            doc.inject_box(b_idx, spk, new_tx)
                            self.app.undo_journal.record(
                                BoxEditDelta(
                                    box_index=b_idx,
                                    old_speaker=spk,
                                    new_speaker=spk,
                                    old_text=old_tx,
                                    new_text=new_tx,
                                    file_path=str(self.app.current_file_path or ""),
                                    box_uid=doc.boxes[b_idx].uid,
                                    source="mtl",
                                )
                            )
                            self.app._modified_boxes.add(b_idx)
                elif kind == "error":
                    _, step, b_idx, err_str = msg
                    self.app.logger.warning("MTL", f"Batch translate failed on box {b_idx}: {err_str}")
                elif kind == "done":
                    _, final_count, final_skipped = msg
                    done_received = True
                    break
        except queue.Empty:
            pass

        if done_received:
            self._is_running = False
            self._end_undo_batch()
            if self.app.current_file_path:
                self.app._mark_document_dirty(self.app.current_file_path)
            self.app._dirty_state_changed()
            self.app._update_views()

            if self._close_requested:
                safe_grab_release(self)
                if self.winfo_exists():
                    self.destroy()
                return

            if self.winfo_exists():
                self.btn_start.config(state="normal")
                stat_txt = f"Completed: {final_count} boxes translated."
                toast_txt = f"✓ Batch translated {final_count} boxes"
                if final_skipped > 0:
                    stat_txt += f" ({final_skipped} locked boxes preserved)"
                    toast_txt += f" ({final_skipped} locked boxes preserved)"
                self.lbl_status.config(text=stat_txt)
                self.app.show_toast(toast_txt)
        elif self._is_running or self._close_requested:
            self._schedule_poll()


def main():
    """
    Application entry point.

    Initializes MisoraApp with a fast, lightweight splash screen
    running as a Toplevel of the root application window to avoid
    multi-root Tkinter event loop conflicts and variable orphaning.
    """
    init_process_dpi_awareness()

    initial_file = None
    show_splash = True
    for arg in sys.argv[1:]:
        if arg in ("--no-splash", "-ns"):
            show_splash = False
        elif not arg.startswith("-") and initial_file is None:
            initial_file = arg

    app = MisoraApp(initial_file, show_splash=show_splash)
    app.mainloop()


if __name__ == "__main__":
    main()