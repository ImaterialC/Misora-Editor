#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misora: Unity3D Revision Tool & Story Editor
=============================================
A specialized GUI text editor for inspecting, searching, and in-place patching
of Princess Connect! Re:Dive Unity3D story bundles (.unity3d) and XUAT translation files.
"""
from __future__ import annotations

import collections
import colorsys
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
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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
    from misora.assets.splash import MisoraSplashScreen
    from misora.core import (
        ALWAYS_ON_CATEGORY, LOG_CATEGORIES, LOG_LEVELS, Box, BoxSnapshot, BundleIOError,
        BoxEditDelta, BoxStructuralDelta, BulkFileDelta, MetadataDelta, LogEntry, MasterUndoJournal, MisoraLogger,
        PlainTextDelta, ProjectSearchEngine, Record, SearchOptions, SearchResult,
        StoryDocument, UndoOperation, XUnitySyncManager, load_bundle_story,
        save_bundle_story, dispose_unity_env,
        MTLConfig, MTLEngine, TagMasker, translate_async, MTL_ENGINES, DEFAULT_LLM_PROMPT,
        serialize, parse, sniff_format, apply_to_document, sanitize_speaker,
        DialogueBlock, MetadataBlock, ParseResult,
        NGUI_TAG_RE, NGUI_TOKEN_RE, normalize_gradient_syntax, strip_tags, get_rendered_length, measure_line_lengths,
        protect_secret, unprotect_secret, redact_secret,
        DecodedText, detect_encoding_and_decode, encode_with_metadata,
        read_text_file_strictly, write_atomic_encoded,
    )
except ImportError:
    from assets.icon import THEME, apply_window_icon, get_icon, prune_icon_cache
    from assets.splash import MisoraSplashScreen
    from core import (
        ALWAYS_ON_CATEGORY, LOG_CATEGORIES, LOG_LEVELS, Box, BoxSnapshot, BundleIOError,
        BoxEditDelta, BoxStructuralDelta, BulkFileDelta, MetadataDelta, LogEntry, MasterUndoJournal, MisoraLogger,
        PlainTextDelta, ProjectSearchEngine, Record, SearchOptions, SearchResult,
        StoryDocument, UndoOperation, XUnitySyncManager, load_bundle_story,
        save_bundle_story, dispose_unity_env,
        MTLConfig, MTLEngine, TagMasker, translate_async, MTL_ENGINES, DEFAULT_LLM_PROMPT,
        serialize, parse, sniff_format, apply_to_document, sanitize_speaker,
        DialogueBlock, MetadataBlock, ParseResult,
        NGUI_TAG_RE, NGUI_TOKEN_RE, normalize_gradient_syntax, strip_tags, get_rendered_length, measure_line_lengths,
        protect_secret, unprotect_secret, redact_secret,
        DecodedText, detect_encoding_and_decode, encode_with_metadata,
        read_text_file_strictly, write_atomic_encoded,
    )

try:
    from misora.core.security import DPAPISecurityError
except ImportError:
    from core.security import DPAPISecurityError

CONFIG_PATH = SCRIPT_DIR / "misora_config.json"
DEBUG_LOG_PATH = SCRIPT_DIR / "misora_debug.log"
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

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
    return "1.4.0"

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

DEFAULT_PREFS: Dict[str, Any] = {
    "dialogue_font_family": "Segoe UI",
    "dialogue_font_size": 11,
    "raw_font_size": 9,
    "ui_font_size": 9,
    "theme": dict(THEME_PRESETS["Misora Purple & White"]),
    "debug": {
        "console_visible": False,
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
            with open("picker_error.log", "w", encoding="utf-8") as f:
                f.write(err)
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
        self.btn_insert_grad.configure(text=f"Insert [{c0_code},{c1_code}]")

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
    """Main Application Window for Misora: Unity3D Revision Tool."""

    def __init__(self, initial_path: Optional[str] = None, show_splash: bool = True, _progress_callback=None, restore_session: bool = True):
        super().__init__()
        self.title("Misora Editor: Unity3D Revision Tool & Story Editor")
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

        _rpt(0.25, "Loading saved preferences…")
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
        self.var_select_box_mode: tk.BooleanVar = tk.BooleanVar(master=self, value=False)
        self._selected_boxes: Set[int] = set()
        self._locked_boxes: Set[int] = set()
        self._locked_box_uids: Set[int] = set()
        self._modified_box_uids: Set[int] = set()
        self._original_jp_by_uid: Dict[int, str] = {}
        self._box_clipboard: List[Any] = []
        self._is_speaker_pinned: bool = False
        self._icon_cache: dict = {}
        self._cont_resize_job: Optional[str] = None

        # S8b-1: Toast & Status Notification Manager state
        self._toast_queue: collections.deque = collections.deque()
        self._toast_active: bool = False
        self._toast_after_id: Optional[str] = None
        self._status_after_id: Optional[str] = None
        self._default_status_text: str = "Ready. Drag & Drop or open a .unity3d bundle or folder to begin."
        self._toast_widget: Optional[tk.Label] = None

        # Side Drawer (Customization & NGUI Glossary) state
        self._side_drawer_visible: bool = False
        self._side_drawer_tab: str = "customize"
        self._theme_swatch_buttons: Dict[str, tk.Button] = {}
        self._theme_hex_vars: Dict[str, tk.StringVar] = {}
        self._glossary_line_map: Dict[int, int] = {}
        self._selected_glossary_idx: int = 0
        self._filtered_glossary_items: List[Dict[str, str]] = list(NGUI_GLOSSARY_ITEMS)

        # Native Win32 Drag & Drop references (kept alive to prevent GC)
        self._wndprocs: Dict[int, Tuple[Any, Any]] = {}
        self._drop_hwnd: Any = None
        self._dnd_in_progress: bool = False

        # Debug Console state
        self._console_visible: bool = bool(dbg_cfg.get("console_visible", False))
        self.var_console_visible = tk.BooleanVar(master=self, value=self._console_visible)
        self.var_log_to_file = tk.BooleanVar(master=self, value=bool(dbg_cfg.get("log_to_file", False)))
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
        self.search_queue: queue.Queue = queue.Queue()
        self.search_cancel_flag: bool = False
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

        # Start periodic poll for background tasks
        self._search_poll_job = self.after(100, self._process_search_queue)
        self._mtl_poll_job = self.after(50, self._poll_mtl_queue)

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

        # Defer session file restoration to idle loop so startup never hangs (BUG-35)
        def _deferred_restore() -> None:
            if not self.winfo_exists():
                return
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
            self._cleanup_drag_and_drop()

    def destroy(self) -> None:
        self._destroyed = True
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
        except Exception:
            pass

        self._cleanup_drag_and_drop()
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
            "console_visible": False,
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
                        prefs["dialogue_font_family"] = raw["dialogue_font_family"].strip()
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
                        if isinstance(saved_dbg.get("console_visible"), bool):
                            merged_debug["console_visible"] = saved_dbg["console_visible"]
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
            dbg_snapshot["console_visible"] = (
                bool(self.var_console_visible.get())
                if hasattr(self, "var_console_visible")
                else self._console_visible
            )
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
                "show_ngui_ribbon": bool(self.var_show_ngui_ribbon.get()) if hasattr(self, "var_show_ngui_ribbon") else getattr(self, "_saved_show_ngui_ribbon", True),
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

    def _apply_theme_and_fonts_live(self, save: bool = True) -> None:
        """Re-apply current theme colors (with WCAG contrast) and font sizes across all active widgets."""
        THEME.update(self.theme)
        self._apply_styles()

        t = self.theme
        d_fam = self.prefs["dialogue_font_family"]
        d_sz = int(self.prefs["dialogue_font_size"])
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
                    w.configure(
                        bg=t["bg_panel"],
                        fg=panel_fg,
                        selectcolor=t["bg_dark"],
                        activebackground=t["bg_panel"],
                        activeforeground=panel_fg,
                        font=("Segoe UI", u_sz),
                    )
                elif role == "check_accent":
                    w.configure(
                        bg=t["bg_panel"],
                        fg=panel_fg,
                        selectcolor=t["bg_dark"],
                        activebackground=t["bg_panel"],
                        activeforeground=t["misora_pink"],
                        font=("Segoe UI", max(8, u_sz - 1), "bold"),
                    )
                elif role == "check_ribbon":
                    w.configure(
                        bg=t["bg_editor"],
                        fg=editor_fg,
                        selectcolor=t["bg_panel"],
                        activebackground=t["bg_editor"],
                        activeforeground=t["misora_pink"],
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
            self.gutter_clean.configure(bg=gutter_bg, fg=gutter_fg)
        if hasattr(self, "gutter_cont"):
            self.gutter_cont.configure(bg=gutter_bg, fg=gutter_fg)
        if hasattr(self, "ruler_clean"):
            self.ruler_clean.configure(bg=gutter_bg, fg=gutter_fg)
        if hasattr(self, "ruler_cont"):
            self.ruler_cont.configure(bg=gutter_bg, fg=gutter_fg)

        self.txt_dialogue.configure(
            font=(d_fam, d_sz),
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

        self.txt_continuous.configure(
            font=(d_fam, d_sz),
            bg=t["bg_editor"],
            fg=editor_fg,
            insertbackground=t["misora_pink"],
            selectbackground=t["highlight_bg"],
            selectforeground=hl_fg,
            highlightthickness=0,
            bd=1,
            relief="solid",
        )
        if hasattr(self, "txt_box0_summary"):
            self.txt_box0_summary.configure(
                font=(d_fam, d_sz),
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
                font=(d_fam, d_sz),
                bg=t["bg_editor"],
                fg=editor_fg,
                insertbackground=t["misora_pink"],
            )
        if hasattr(self, "entry_box0_subtitle"):
            self.entry_box0_subtitle.configure(
                font=(d_fam, d_sz),
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
        widget.tag_configure(
            "search_hit",
            background=t["highlight_bg"],
            foreground=hl_fg,
            underline=True,
        )
        for tag_name in list(widget.tag_names()):
            if tag_name.startswith("cstyle_"):
                widget.tag_delete(tag_name)
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

        style.configure("TCheckbutton", background=t["bg_dark"], foreground=fg_on_dark, font=("Segoe UI", u_sz))
        style.configure("Panel.TCheckbutton", background=t["bg_panel"], foreground=fg_on_panel, font=("Segoe UI", u_sz))
        style.map("Panel.TCheckbutton",
            background=[("active", t["bg_panel"]), ("!active", t["bg_panel"])],
            foreground=[("active", t["misora_pink"]), ("!active", fg_on_panel)],
        )
        style.configure("Accent.TCheckbutton", background=t["bg_panel"], foreground=t["misora_pink"], font=("Segoe UI", max(8, u_sz - 1), "bold"))
        style.map("Accent.TCheckbutton",
            background=[("active", t["bg_panel"]), ("!active", t["bg_panel"])],
            foreground=[("active", t["misora_pink_hover"]), ("!active", t["misora_pink"])],
        )
        style.configure("TRadiobutton", background=t["bg_dark"], foreground=fg_on_dark, font=("Segoe UI", u_sz))
        style.configure("Panel.TRadiobutton", background=t["bg_panel"], foreground=fg_on_panel, font=("Segoe UI", u_sz))
        style.map("Panel.TRadiobutton",
            background=[("active", t["bg_panel"]), ("!active", t["bg_panel"])],
            foreground=[("active", fg_on_panel), ("!active", fg_on_panel)],
        )

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

        # Distinct Box Navigation Buttons (< Prev / Next >) (#4)
        style.configure(
            "Nav.TButton",
            background=btn_bg,
            foreground=fg_btn,
            bordercolor=t["misora_pink"],
            darkcolor=t["border"],
            lightcolor=t["misora_pink"],
            borderwidth=1,
            relief="raised",
            font=("Segoe UI", u_sz, "bold"),
            padding=(9, 3),
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
        self.var_show_ngui_ribbon = tk.BooleanVar(master=self, value=getattr(self, "_saved_show_ngui_ribbon", True))
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
        file_menu.add_command(label="Save & Patch Bundle", command=self.on_save, accelerator="Ctrl+S")
        file_menu.add_command(label="Reload Current File", command=self.on_reload, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Import Script (CSIF / Text)...", command=self.on_import_script, accelerator="Ctrl+Shift+I")
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
        translator_menu = tk.Menu(
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

        menubar.add_cascade(label="Debug", menu=self.debug_menu)
        self._all_menus.append(self.debug_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=accent_fg)
        help_menu.add_command(label="NGUI & Ruby Glossary", command=lambda: self._open_side_drawer("glossary"), accelerator="F1")
        help_menu.add_separator()
        help_menu.add_command(label="About Misora", command=self.on_about)
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
            text="📌",
            style="Small.TButton",
            command=self._toggle_dock_collapse,
            width=3,
        )
        self.btn_dock_pin.pack(side="right", padx=(2, 2))
        self._dock_pin_tooltip = create_tooltip(self.btn_dock_pin, "Collapse Left Panel")

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
        self.h_paned.add(right_frame, minsize=420, stretch="always")

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
        self.v_paned.pack(fill="both", expand=True)

        # TOP VIEW: Game Display View (Page-by-Page OR Continuous Dialog Stream)
        top_view = self._tag_role(tk.Frame(self.v_paned, bg=t["bg_panel"]), "panel")
        self.top_view = top_view
        self.v_paned.add(top_view, minsize=140, height=400, stretch="always")

        gd_header = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        gd_header.pack(fill="x", padx=8, pady=(4, 2))

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

        self.lbl_box_counter = self._tag_role(
            tk.Label(gd_header, text="Box: 0 / 0", font=("Segoe UI", u_sz), bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        )
        self.lbl_box_counter.pack(side="right", padx=(6, 0))

        self.ico_next = self.get_icon("nav_next", (14, 14))
        self.btn_next = ttk.Button(gd_header, text="Next ", image=self.ico_next, compound="right", style="Nav.TButton", command=self.on_next_box)
        self.btn_next.pack(side="right", padx=(2, 0))
        create_tooltip(self.btn_next, "Next Dialogue Box (Alt+Right / Alt+Down)")

        self.ico_prev = self.get_icon("nav_prev", (14, 14))
        self.btn_prev = ttk.Button(gd_header, text=" Prev", image=self.ico_prev, compound="left", style="Nav.TButton", command=self.on_prev_box)
        self.btn_prev.pack(side="right", padx=(4, 2))
        create_tooltip(self.btn_prev, "Previous Dialogue Box (Alt+Left / Alt+Up)")

        self.ico_ai = self.get_icon("ai", (16, 16))
        self.btn_ai_prompt = ttk.Button(gd_header, text=" AI Prompt", image=self.ico_ai, compound="left", style="Small.TButton", command=self.on_copy_ai_prompt)
        self.btn_ai_prompt.pack(side="right", padx=(4, 2))
        create_tooltip(self.btn_ai_prompt, "Copy AI Translation Prompt (Ctrl+Shift+T)")

        self.ico_mtl = self.get_icon("mtl", (16, 16))
        self.btn_translate = ttk.Button(gd_header, text=" MTL", image=self.ico_mtl, compound="left", style="Small.TButton", command=self.on_open_translator_assistant)
        self.btn_translate.pack(side="right", padx=(2, 2))
        create_tooltip(self.btn_translate, "Open Translator Assistant (Ctrl+T)")

        # Row 1: Speaker Controls (Left) + Unified VIEW Group (Right) (#7, #10, FEAT-02, FEAT-03, BUG-39)
        self.speaker_view_row = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        self.speaker_view_row.pack(fill="x", padx=8, pady=(2, 4))

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
                width=14
            ),
            "entry_speaker"
        )
        self.entry_speaker.pack(side="left")
        self.entry_speaker.bind("<KeyRelease>", lambda e: self._on_speaker_edited())
        self.entry_speaker.bind("<<Cut>>", lambda e: self.after_idle(self._commit_speaker_edit))
        self.entry_speaker.bind("<<Paste>>", lambda e: self.after_idle(self._commit_speaker_edit))

        self.btn_speaker_dropdown = ttk.Button(
            self.speaker_view_row,
            text="▼",
            style="Small.TButton",
            width=2,
            command=self._on_speaker_dropdown_clicked,
        )
        self.btn_speaker_dropdown.pack(side="left", padx=(2, 2))
        create_tooltip(self.btn_speaker_dropdown, "Select Speaker from Recent List")

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
        create_tooltip(self.btn_pin_speaker, "Pin Speaker (locks current speaker across box navigation)")

        # Player Button: icon-only (player.png), moved out of NGUI ribbon into speaker row (FEAT-02)
        dark_p = self._is_dark_color(t["bg_panel"])
        btn_bg = self._shift_hex(t["bg_panel"], 10 if dark_p else -8)
        btn_hover = self._shift_hex(t["bg_panel"], 22 if dark_p else -16)
        btn_fg = best_contrast_fg(btn_bg, t["fg_text"], "#ffffff")
        accent_bg = t["misora_pink"]
        accent_hover = t["misora_pink_hover"]
        fg_accent = best_contrast_fg(accent_bg)

        self.ico_player = self.get_icon("player", (14, 14))
        self.btn_player = self._tag_role(
            tk.Button(
                self.speaker_view_row,
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
        self.btn_player.pack(side="left", padx=(1, 4))
        create_tooltip(self.btn_player, "Insert Player Name tag ({0} / {playername}) (Ctrl+P)")

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

        # Translation Lock Toggle Button (Rule 20 D8 / TRANSLATION-LOCK)
        self.btn_lock_box = tk.Button(
            self.speaker_view_row,
            text="🔓",
            font=("Segoe UI", max(8, u_sz - 1)),
            bg=t["bg_panel"],
            activebackground=t["highlight_bg"],
            bd=1,
            relief="solid",
            cursor="hand2",
            command=self.on_toggle_lock_current_box,
            padx=3,
            pady=0,
        )
        self.btn_lock_box.pack(side="left", padx=(2, 4))
        create_tooltip(self.btn_lock_box, "Translation Lock (Ctrl+L) — Protect box from batch/paste/replace")

        # Rendered Character Count & Game Box Overflow Warning (Rule 19, Rule 20 D13 / GAME-BOX-PREVIEW)
        self.lbl_char_count = self._tag_role(
            tk.Label(self.speaker_view_row, text="", bg=t["bg_panel"], fg=t["fg_muted"], font=("Segoe UI", max(8, u_sz - 1))),
            "label_char_count"
        )
        self.lbl_char_count.pack(side="left", padx=(2, 6))
        create_tooltip(self.lbl_char_count, "Rendered dialogue length (excluding NGUI tags). Warns on overflow (>45 chars/line).")

        # Unified VIEW Group (Select Box, All Script, Preview) docked on right side of Speaker row (FEAT-03)
        self.view_group = self._tag_role(
            tk.Frame(self.speaker_view_row, bg=t["bg_editor"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "ribbon"
        )
        self.view_group.pack(side="right", padx=(4, 0))

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
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_sel_box.pack(side="left", padx=2, pady=1)
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
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_cont.pack(side="left", padx=2, pady=1)
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
                cursor="hand2",
            ),
            "check_ribbon"
        )
        self.cb_compiled.pack(side="left", padx=2, pady=1)
        create_tooltip(self.cb_compiled, "Toggle Compiled Attribute Preview (read-only)")

        # Row 2: Collapsible NGUI Ribbon (Left) + Text & Box Actions Toolbar (Right) (BUG-39, FEAT-04)
        self.ribbon_actions_row = self._tag_role(tk.Frame(top_view, bg=t["bg_panel"]), "panel")
        self.ribbon_actions_row.pack(fill="x", padx=8, pady=(0, 4))

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

        self._tag_role(tk.Label(self.ribbon_frame, text="|", bg=t["bg_editor"], fg=t["border"]), "label_ribbon_sep").pack(side="left", padx=1)

        # History: Undo & Redo with illustrated icons
        self.ico_undo = self.get_icon("undo", (16, 16))
        self.btn_ribbon_undo = self._tag_role(
            tk.Button(
                self.ribbon_frame,
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
                self.ribbon_frame,
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

        # Text & Box Actions Toolbar (docked on right side of ribbon_actions_row)
        self.actions_bar = self._tag_role(
            tk.Frame(self.ribbon_actions_row, bg=t["bg_editor"], bd=1, relief="solid", highlightbackground=t["border"], highlightthickness=1),
            "actions_toolbar"
        )
        self.actions_bar.pack(side="right", padx=(2, 0))

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

        # Respect initial ribbon visibility toggle without triggering premature preferences save
        if hasattr(self, "var_show_ngui_ribbon") and not self.var_show_ngui_ribbon.get():
            self.ribbon_frame.pack_forget()

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

        # Horizontal Column Ruler for Clean View (#12)
        self.ruler_clean = tk.Text(
            text_container,
            height=1,
            font=("Consolas", max(8, d_sz - 2)),
            bg=gutter_bg,
            fg=gutter_fg,
            bd=0,
            relief="flat",
            wrap="none",
            takefocus=0,
            cursor="arrow",
        )
        self.ruler_clean.insert("1.0", "     ....5...10...15...20...25...30...35...40...45...50...55...60...65...70...75...80")
        self.ruler_clean.config(state="disabled")
        if self.show_column_ruler:
            self.ruler_clean.pack(side="top", fill="x", pady=(0, 2))

        self.clean_editor_row = tk.Frame(text_container, bg=t["bg_panel"])
        self.clean_editor_row.pack(fill="both", expand=True)

        # Vertical Line Numbers Gutter for Clean View (#12)
        self.gutter_clean = tk.Text(
            self.clean_editor_row,
            width=3,
            font=("Consolas", d_sz),
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

        # Horizontal Column Ruler for Continuous View (#12)
        self.ruler_cont = tk.Text(
            self.continuous_wrap,
            height=1,
            font=("Consolas", max(8, d_sz - 2)),
            bg=gutter_bg,
            fg=gutter_fg,
            bd=0,
            relief="flat",
            wrap="none",
            takefocus=0,
            cursor="arrow",
        )
        self.ruler_cont.insert("1.0", "      ....5...10...15...20...25...30...35...40...45...50...55...60...65...70...75...80")
        self.ruler_cont.config(state="disabled")
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
        self.lbl_raw_title = self._tag_role(
            tk.Label(raw_header, text="Raw Commands", font=("Segoe UI", u_sz, "bold"), bg=t["bg_panel"], fg=t["fg_muted"]),
            "label_muted"
        )
        self.lbl_raw_title.pack(side="left")

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
    # Speaker Attributes & Actor Quick Assignment
    # -------------------------------------------------------------------------
    def _on_speaker_dropdown_clicked(self) -> None:
        """Display a clean popup menu of story actors and tools (#18)."""
        if getattr(self, "is_box0_active", False):
            return

        t = self.theme
        panel_fg = best_contrast_fg(t["bg_panel"], t["fg_text"], "#ffffff")
        menu = tk.Menu(self, tearoff=0, bg=t["bg_panel"], fg=panel_fg, activebackground=t["misora_pink"], activeforeground=best_contrast_fg(t["misora_pink"]))

        # Known Story Actors listed directly at top level
        if self.current_doc:
            actors = [a for a in sorted(self.current_doc.actors()) if a]
            for act in actors:
                menu.add_command(
                    label=act,
                    command=lambda a=act: self._assign_speaker_to_current_box(a),
                )
            if actors:
                menu.add_separator()

        menu.add_command(label="Insert {playername}", command=lambda: self._assign_speaker_to_current_box("{playername}"))
        menu.add_command(label="Clear Speaker (Narration)", command=lambda: self._assign_speaker_to_current_box(""))

        try:
            x = self.btn_speaker_dropdown.winfo_rootx()
            y = self.btn_speaker_dropdown.winfo_rooty() + self.btn_speaker_dropdown.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _assign_speaker_to_current_box(self, new_speaker: str) -> None:
        if getattr(self, "is_box0_active", False):
            return
        self.speaker_var.set(new_speaker)
        self._on_speaker_edited()
        self.show_toast(f"Assigned speaker: {new_speaker or '(Narration)'}")

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
            self.gutter_clean.config(state="disabled")
        except Exception:
            pass

    def _update_gutter_cont(self, line_num_list: List[str]) -> None:
        """Update repeating per-box line numbers in continuous view gutter."""
        if not hasattr(self, "gutter_cont"):
            return
        try:
            self.gutter_cont.config(state="normal")
            self.gutter_cont.delete("1.0", tk.END)
            self.gutter_cont.insert("1.0", "\n".join(line_num_list))
            self.gutter_cont.config(state="disabled")
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
        """Toggle visibility of the NGUI formatting ribbon docked in ribbon_actions_row (FEAT-04)."""
        if not hasattr(self, "ribbon_frame"):
            return
        if self.var_show_ngui_ribbon.get():
            if hasattr(self, "actions_bar") and self.actions_bar.winfo_manager():
                self.ribbon_frame.pack(side="left", padx=(0, 4), before=self.actions_bar)
            else:
                self.ribbon_frame.pack(side="left", padx=(0, 4))
        else:
            self.ribbon_frame.pack_forget()
        self._save_user_prefs(silent=True)

    def _on_toggle_preview_compiled(self) -> None:
        """Toggle between editable raw NGUI tags and compiled visual preview."""
        if self.var_preview_compiled.get():
            self.lbl_status.config(
                text="Compiled Attribute Preview ON (read-only) — uncheck 'Compiled' to edit raw tags."
            )
        else:
            self.lbl_status.config(
                text="Raw NGUI Tag Edit Mode active."
            )
        self._update_top_header_title()
        self._update_views()

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
        d_fam = self.prefs.get("dialogue_font_family", "Segoe UI")
        d_sz = int(self.prefs.get("dialogue_font_size", 12))
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

        self.var_font_family = tk.StringVar(master=self, value=self.prefs["dialogue_font_family"])
        cb_font = ttk.Combobox(
            fam_row,
            textvariable=self.var_font_family,
            values=["Segoe UI", "Meiryo UI", "Yu Gothic UI", "Consolas", "Arial"],
            state="readonly",
            width=15,
        )
        cb_font.pack(side="right")
        cb_font.bind("<<ComboboxSelected>>", lambda _e: self._on_font_pref_changed())

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
        if not self._side_drawer_visible:
            self.h_paned.add(self.side_drawer, minsize=260, width=330, stretch="never")
            self._side_drawer_visible = True
        self._switch_side_drawer_tab(tab)

    def _close_side_drawer(self) -> None:
        if self._side_drawer_visible:
            self.h_paned.forget(self.side_drawer)
            self._side_drawer_visible = False

    def _toggle_side_drawer(self, tab: str) -> None:
        if self._side_drawer_visible and self._side_drawer_tab == tab:
            self._close_side_drawer()
        else:
            self._open_side_drawer(tab)

    def _switch_side_drawer_tab(self, tab: str) -> None:
        self._side_drawer_tab = tab
        if tab == "customize":
            self.tab_glossary_frame.pack_forget()
            self.tab_customize_frame.pack(fill="both", expand=True)
            self.btn_tab_customize.configure(style="Pink.TButton")
            self.btn_tab_glossary.configure(style="TButton")
        else:
            self.tab_customize_frame.pack_forget()
            self.tab_glossary_frame.pack(fill="both", expand=True)
            self.btn_tab_customize.configure(style="TButton")
            self.btn_tab_glossary.configure(style="Pink.TButton")

    def _on_font_pref_changed(self) -> None:
        """Apply updated font family / size values from Customize panel."""
        fam = self.var_font_family.get().strip() or self.prefs["dialogue_font_family"]
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
        """Switch Game Display between Page-by-Page mode and Continuous Dialog Stream with seamless box & caret sync."""
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
            # 1. Flush any uncommitted card edits
            self._flush_continuous_card_edits()

            # 2. Extract char offset from active card's text editor
            char_offset = 0
            active_idx = -1 if getattr(self, "is_box0_active", False) else self.current_box_idx
            if hasattr(self, "_card_widgets") and active_idx in self._card_widgets:
                try:
                    txt_w = self._card_widgets[active_idx].get("txt")
                    if txt_w:
                        diff = txt_w.count("1.0", "insert", "chars")
                        char_offset = max(0, diff[0] if diff else 0)
                except Exception:
                    char_offset = 0
            elif hasattr(self, "txt_continuous"):
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

    def _toggle_console_shortcut(self) -> None:
        """Inform user that diagnostic logs stream live to the standard Windows console."""
        self.show_toast("Logs stream to the persistent Windows console.")

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
        self.bind("<F12>", lambda e: self._toggle_console_shortcut())
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
            if getattr(self, "is_box0_active", False) and -1 in cards:
                candidate = cards[-1].get("txt")
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate
            elif getattr(self, "current_box_idx", -1) in cards:
                candidate = cards[self.current_box_idx].get("txt")
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate
            elif getattr(self, "current_doc", None) is None:
                candidate = getattr(self, "txt_continuous", None)
                if candidate is not None and candidate.winfo_exists():
                    widget = candidate
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
            if hasattr(self, "focus_get") and self.focus_get() == getattr(self, "entry_speaker", None):
                self._commit_speaker_edit()
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

        doc = staged["doc"]
        is_bundle = staged["is_bundle"]
        plain_text = staged["plain_text"]

        self.current_file_path = file_path
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
        self.title(f"Misora Editor - {file_path.name}")

        if staged["kind"] == "cache":
            entry = staged["entry"]
            self.is_dirty = bool(entry.get("dirty", False))
        else:
            # Dispose prior UnityPy environment and clear prior entry on reload (BUG-34)
            if reload_from_disk and file_path in self.open_documents:
                prior_entry = self.open_documents.get(file_path)
                if isinstance(prior_entry, dict):
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
        """Show centered empty-state frame when 0 documents are open; hide when >=1 document opens."""
        has_docs = bool(self.open_documents) or bool(self.current_doc) or bool(self.current_file_path)
        if not has_docs:
            if hasattr(self, "gd_scroll_wrap") and self.gd_scroll_wrap.winfo_ismapped():
                self.gd_scroll_wrap.pack_forget()
            if hasattr(self, "empty_state_frame") and not self.empty_state_frame.winfo_ismapped():
                self.empty_state_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        else:
            if hasattr(self, "empty_state_frame") and self.empty_state_frame.winfo_ismapped():
                self.empty_state_frame.pack_forget()
            if hasattr(self, "gd_scroll_wrap") and not self.gd_scroll_wrap.winfo_ismapped():
                self.gd_scroll_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _update_views(self) -> None:
        """Update Game Display View (Page or Continuous, Raw or Compiled Preview) and Raw AST View."""
        self._update_empty_state_visibility()
        self._update_dialogue_select_box_ui()
        compiled = self.var_preview_compiled.get()

        if not self.current_doc:
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
            return

        if not self.current_doc.boxes:
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
                if hasattr(self, "_translator_dialog") and self._translator_dialog and self._translator_dialog.winfo_exists():
                    self._translator_dialog.refresh_box()
                return

        if hasattr(self, "panel_box0_metadata") and self._is_widget_packed(self.panel_box0_metadata):
            self.panel_box0_metadata.pack_forget()
        if hasattr(self, "clean_editor_row") and not self._is_widget_packed(self.clean_editor_row):
            if self.show_column_ruler and hasattr(self, "ruler_clean") and not self._is_widget_packed(self.ruler_clean):
                try:
                    self.ruler_clean.pack(before=self.clean_editor_row, side="top", fill="x", pady=(0, 2))
                except Exception:
                    self.ruler_clean.pack(side="top", fill="x", pady=(0, 2))
            self.clean_editor_row.pack(fill="both", expand=True)

        total_boxes = len(self.current_doc.boxes)
        self.current_box_idx = max(0, min(self.current_box_idx, total_boxes - 1))
        box = self.current_doc.boxes[self.current_box_idx]

        if hasattr(self, "entry_speaker"):
            self.entry_speaker.config(state="normal")
        if hasattr(self, "btn_speaker_dropdown"):
            self.btn_speaker_dropdown.config(state="normal")
        self.speaker_var.set(box.speaker)
        self.lbl_box_counter.config(text=f"Box: {self.current_box_idx + 1} / {total_boxes}")
        self.lbl_voice_cue.config(text=f"Voice Cue: {box.voice_cue}" if box.voice_cue else "")

        if hasattr(self, "btn_lock_box"):
            is_locked = self.current_box_idx in self._locked_boxes
            self.btn_lock_box.config(
                text="🔒" if is_locked else "🔓",
                bg=self.theme["accent_yellow"] if is_locked else self.theme["bg_panel"]
            )
        self._update_rendered_char_count(box.clean_text)

        if hasattr(self, "btn_prev"):
            can_prev = (self.current_box_idx > 0) or (self.current_doc and self.current_doc.has_metadata())
            self.btn_prev.config(state="normal" if can_prev else "disabled")
        if hasattr(self, "btn_next"):
            self.btn_next.config(state="normal" if self.current_box_idx < total_boxes - 1 else "disabled")

        if self.var_continuous_view.get():
            self._render_continuous_view()
            self._focus_continuous_box(self.current_box_idx, move_cursor=True)
        else:
            self.txt_dialogue.config(state="normal")
            self.txt_dialogue.delete("1.0", tk.END)
            if compiled:
                self._insert_compiled_ngui_text(self.txt_dialogue, "1.0", box.clean_text)
                self.txt_dialogue.config(state="disabled")
            else:
                self.txt_dialogue.insert("1.0", box.clean_text)
                self._highlight_ngui_tags()
                self._highlight_dialogue_matches()
                self._highlight_secret_whitespace(self.txt_dialogue)
            self._update_gutter_clean()
            self.gd_canvas.yview_moveto(0.0)
            self._auto_resize_dialogue_box()

        self._update_raw_view()
        if hasattr(self, "_translator_dialog") and self._translator_dialog and self._translator_dialog.winfo_exists():
            self._translator_dialog.refresh_box()

    def _update_raw_view(self) -> None:
        """Render Raw AST View and highlight records associated with current_box_idx or Box 0."""
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
                if box_idx == getattr(self, "current_box_idx", -1):
                    self._update_rendered_char_count(new_tx)
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
            if not (self._is_speaker_pinned and self.speaker_var.get()):
                self.speaker_var.set("")
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
            if not (self._is_speaker_pinned and self.speaker_var.get()):
                self.speaker_var.set(box.speaker)
            self.lbl_box_counter.config(text=f"Box: {box_idx + 1} / {total}")
            self.lbl_voice_cue.config(text=f"Voice Cue: {box.voice_cue}" if box.voice_cue else "")
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
        """Syntax-color NGUI tags within a specific Text widget."""
        if self.var_preview_compiled.get() or not w.winfo_exists():
            return
        w.tag_remove("ngui_tag", "1.0", tk.END)
        tx = w.get("1.0", "end-1c")
        for m in NGUI_TAG_RE.finditer(tx):
            w.tag_add("ngui_tag", f"1.0 + {m.start()}c", f"1.0 + {m.end()}c")
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

    def _on_toggle_pin_speaker(self) -> None:
        """Toggle persistent speaker pinning across box navigation."""
        self._is_speaker_pinned = not self._is_speaker_pinned
        t = self.theme
        if self._is_speaker_pinned:
            if hasattr(self, "btn_pin_speaker"):
                self.btn_pin_speaker.config(bg=t["highlight_bg"], relief="sunken")
            sp = self.speaker_var.get()
            self.show_toast(f"📌 Speaker Pinned: '{sp}' locked across navigation")
        else:
            if hasattr(self, "btn_pin_speaker"):
                btn_bg = t.get("bg_editor", "#faf8fe")
                self.btn_pin_speaker.config(bg=btn_bg, relief="raised")
            self.show_toast("Speaker Unpinned")

    def on_select_whole_story(self) -> None:
        """Select whole story / all text across document."""
        if self.var_continuous_view.get():
            if hasattr(self, "_card_widgets") and self._card_widgets:
                first_card = self._card_widgets.get(0) or self._card_widgets.get(-1)
                if first_card and "txt" in first_card:
                    txt = first_card["txt"]
                    txt.focus_set()
                    txt.tag_add("sel", "1.0", "end-1c")
            self.show_toast("Selected active story")
        else:
            if hasattr(self, "txt_dialogue"):
                self.txt_dialogue.focus_set()
                self.txt_dialogue.tag_add("sel", "1.0", "end-1c")
                self.show_toast("Selected all text in current box")

    def on_text_cut(self) -> None:
        """Cut text in active editor to clipboard."""
        target = self.txt_dialogue
        if self.var_continuous_view.get() and hasattr(self, "_card_widgets") and self.current_box_idx in self._card_widgets:
            target = self._get_card_text_widget(self.current_box_idx)
        self._current_edit_source = "cut"
        try:
            target.event_generate("<<Cut>>")
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
            self.title(f"Misora Editor - {file_name}{dirty_marker}")
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

        cur_sp = self.speaker_var.get() if (self._is_speaker_pinned and self.speaker_var.get()) else ""
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
        self._sync_clean_view_to_current_box()
        self.show_toast(f"✂📦 Cut {len(targets)} box(es)")

    def on_box_paste(self, confirm: bool = True) -> None:
        """Paste box(es) from clipboard as new boxes after current box (Part C.2)."""
        if not self.current_doc:
            self.show_toast("No story document loaded")
            return

        clip_text = self.safe_clipboard_get()
        if getattr(self, "_box_clipboard_text", None) != clip_text:
            self._box_clipboard = None
            self._box_clipboard_text = None

        snaps_to_ins: List[BoxSnapshot] = []
        if getattr(self, "_box_clipboard", None):
            snaps_to_ins = [
                BoxSnapshot(
                    speaker=snap.speaker,
                    voice_cue=snap.voice_cue,
                    kind=snap.kind,
                    seg_texts=list(snap.seg_texts),
                    extra_args=[list(ea) for ea in snap.extra_args] if snap.extra_args else None,
                )
                for snap in self._box_clipboard
            ]
        elif clip_text.strip():
            result = parse(clip_text)
            parsed_blocks = result.blocks
            if parsed_blocks:
                snaps_to_ins = [
                    BoxSnapshot(
                        speaker="" if b.is_narration else b.speaker,
                        voice_cue="",
                        kind="tag" if (b.is_narration or not b.speaker) else "print",
                        seg_texts=[b.text]
                    )
                    for b in parsed_blocks
                ]

        if not snaps_to_ins:
            self.show_toast("Box clipboard is empty")
            return

        ins_idx = self.current_box_idx + 1 if self.current_doc.boxes else 0
        block_count = len(snaps_to_ins)
        first_speakers = [
            (s.speaker if s.speaker else "(Narration)")
            for s in snaps_to_ins[:3]
        ]
        sp_desc = ", ".join(first_speakers)
        if block_count > 3:
            sp_desc += f", ... (+{block_count - 3} more)"

        if confirm:
            ins_desc = f"after Box #{self.current_box_idx + 1}" if self.current_doc.boxes else "at beginning"
            msg = f"Insert {block_count} box(es) {ins_desc}?\n\nSpeakers: {sp_desc}"
            ans = messagebox.askyesno("Paste Box(es)", msg, parent=self)
            if not ans:
                return

        self.undo_journal.begin_batch(f"Paste {block_count} Box(es)")
        try:
            for offset, snap in enumerate(snaps_to_ins):
                target_idx = ins_idx + offset
                self.current_doc.insert_box(target_idx, snap)
                self._modified_boxes.add(target_idx)

            self.undo_journal.record(
                BoxStructuralDelta(
                    op_type="insert",
                    box_index=ins_idx,
                    snapshots=snaps_to_ins,
                    file_path=str(self.current_file_path or ""),
                )
            )
        finally:
            self.undo_journal.end_batch()

        self.current_box_idx = ins_idx + len(snaps_to_ins) - 1
        self._mark_document_dirty(self.current_file_path)
        self._dirty_state_changed()
        self._update_views()
        self._sync_clean_view_to_current_box()
        self.show_toast(f"📥📦 Pasted {len(snaps_to_ins)} box(es)")

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

    def _render_continuous_view(self) -> None:
        """Render all dialogue boxes sequentially as a Box Card Stream."""
        compiled = self.var_preview_compiled.get()
        self._suppress_continuous_events = True
        t = self.theme
        d_fam = self.var_font_family.get() if hasattr(self, "var_font_family") else "Segoe UI"
        d_sz = int(self.prefs.get("dialogue_font_size", 12))

        try:
            self._card_widgets.clear()
            # If plain text file: keep legacy txt_continuous view
            if not self.is_bundle_file and not self.current_doc:
                if hasattr(self, "cont_canvas") and self._is_widget_packed(self.cont_canvas):
                    self.cont_canvas.pack_forget()
                    self.cont_scroll_y.pack_forget()
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

            # Multi-Box Story Documents: Box Card Stream
            if hasattr(self, "txt_continuous") and self._is_widget_packed(self.txt_continuous):
                self.txt_continuous.pack_forget()
            if hasattr(self, "gutter_cont") and self._is_widget_packed(self.gutter_cont):
                self.gutter_cont.pack_forget()

            if hasattr(self, "cont_scroll_y") and not self._is_widget_packed(self.cont_scroll_y):
                self.cont_scroll_y.pack(side="right", fill="y")
            if hasattr(self, "cont_canvas") and not self._is_widget_packed(self.cont_canvas):
                self.cont_canvas.pack(side="left", fill="both", expand=True)

            # Clear existing cards
            if hasattr(self, "cont_stream_frame"):
                for child in self.cont_stream_frame.winfo_children():
                    child.destroy()

            if not self.current_doc or not self.current_doc.boxes:
                return

            gutter_bg = "#e8e8e8" if self._is_light_theme() else "#2d2d30"
            gutter_fg = "#707070" if self._is_light_theme() else "#858585"

            # 1. Card #0: Story Metadata Card
            if self.current_doc.has_metadata():
                meta = self.current_doc.get_metadata()
                is_active_0 = getattr(self, "is_box0_active", False)
                box0_bg = t["highlight_bg"] if is_active_0 else ("#dfd1f5" if self._is_light_theme() else "#2d1d29")
                box0_border = "#bca0e8" if self._is_light_theme() else "#4a3556"
                card_0 = tk.Frame(self.cont_stream_frame, bg=box0_bg, highlightbackground=box0_border, highlightthickness=1)
                hdr_0 = tk.Frame(card_0, bg=box0_bg, padx=4, pady=1)

                slot_cb_0 = tk.Frame(hdr_0, width=22, height=18, bg=box0_bg)
                slot_cb_0.pack_propagate(False)
                slot_cb_0.pack(side="left", padx=(0, 2))
                cb_sel_0 = None
                if self.var_select_box_mode.get():
                    var_box0_sel = tk.BooleanVar(master=self, value=(-1 in self._selected_boxes))
                    def _make_box0_sel_cmd(v):
                        def _cmd():
                            if v.get():
                                self._selected_boxes.add(-1)
                            else:
                                self._selected_boxes.discard(-1)
                        return _cmd
                    cb_sel_0 = tk.Checkbutton(
                        slot_cb_0,
                        variable=var_box0_sel,
                        command=_make_box0_sel_cmd(var_box0_sel),
                        bg=box0_bg,
                        activebackground=box0_bg,
                        selectcolor=t["bg_panel"],
                        bd=0,
                        cursor="hand2",
                    )
                    cb_sel_0.pack(fill="both", expand=True)
                    cb_sel_0.bind("<MouseWheel>", self._on_cont_mousewheel)

                slot_lock_0 = tk.Frame(hdr_0, width=18, height=18, bg=box0_bg)
                slot_lock_0.pack_propagate(False)
                slot_lock_0.pack(side="left", padx=(0, 2))

                lbl_badge_0 = tk.Label(hdr_0, text="◆ [BOX #000]", font=("Consolas", max(8, d_sz - 3), "bold"), fg=t["misora_pink"], bg=box0_bg)
                lbl_badge_0.pack(side="left")
                lbl_title_0 = tk.Label(hdr_0, text="[STORY METADATA & SYNOPSIS]", font=(d_fam, max(8, d_sz - 3), "bold"), fg=t["fg_text"], bg=box0_bg)
                lbl_title_0.pack(side="left", padx=(6, 4))
                hdr_0.pack(fill="x")

                meta_body = tk.Frame(card_0, bg=box0_bg, padx=4, pady=1)
                tk.Label(meta_body, text=f"Title: {meta.get('title', '')}   |   Subtitle: {meta.get('subtitle', '')}", font=(d_fam, max(7, d_sz - 3)), fg=t["fg_muted"], bg=box0_bg).pack(anchor="w")
                summary_lines = max(2, min(8, meta.get("summary", "").count("\n") + 1))
                txt_summary = tk.Text(
                    meta_body,
                    wrap="word",
                    undo=False,
                    height=summary_lines,
                    font=(d_fam, d_sz),
                    bg=t["bg_editor"],
                    fg=t["fg_text"],
                    insertbackground=t["misora_pink"],
                    selectbackground=t["highlight_bg"],
                    selectforeground=t["misora_pink"],
                    bd=1,
                    relief="solid",
                    highlightthickness=0,
                    padx=8,
                    pady=3,
                    spacing1=2,
                    spacing3=2
                )
                txt_summary.insert("1.0", meta.get("summary", ""))
                txt_summary.pack(fill="x", pady=(1, 2))
                meta_body.pack(fill="x")

                # Bindings for Card #0
                self._install_shortcuts_bindtag(txt_summary)
                txt_summary.bind("<FocusIn>", lambda e: self._on_card_focus_in(-1))
                txt_summary.bind("<KeyRelease>", lambda e, w=txt_summary: self._commit_widget_edit(w))
                txt_summary.bind("<<Cut>>", lambda e, w=txt_summary: self.after_idle(lambda: self._commit_widget_edit(w)))
                txt_summary.bind("<<Paste>>", lambda e, w=txt_summary: self.after_idle(lambda: self._commit_widget_edit(w)))
                txt_summary.bind("<Control-a>", lambda e, w=txt_summary: (w.tag_add("sel", "1.0", "end-1c"), "break")[1])
                txt_summary.bind("<Control-A>", lambda e, w=txt_summary: (w.tag_add("sel", "1.0", "end-1c"), "break")[1])

                for w in (card_0, hdr_0, lbl_badge_0, lbl_title_0, meta_body, txt_summary):
                    w.bind("<MouseWheel>", self._on_cont_mousewheel)

                card_0.pack(fill="x", padx=6, pady=(1, 2))

                self._card_widgets[-1] = {
                    "card": card_0,
                    "hdr": hdr_0,
                    "txt": txt_summary,
                    "lbl_badge": lbl_badge_0,
                    "lbl_title": lbl_title_0,
                    "slot_cb": slot_cb_0,
                    "cb_sel": cb_sel_0,
                }

            # 2. Cards #1..N: Dialogue Box Cards
            for i, box in enumerate(self.current_doc.boxes):
                is_active = (not getattr(self, "is_box0_active", False) and i == self.current_box_idx)
                hdr_bg = t["highlight_bg"] if is_active else t["bg_panel"]
                card_frame = tk.Frame(self.cont_stream_frame, bg=t["bg_panel"])
                hdr = tk.Frame(card_frame, bg=hdr_bg, padx=4, pady=0)

                # Fixed reserved checkbox slot (prevents header shift when Select Box toggles)
                slot_cb = tk.Frame(hdr, width=22, height=18, bg=hdr_bg)
                slot_cb.pack_propagate(False)
                slot_cb.pack(side="left", padx=(0, 2))

                if self.var_select_box_mode.get():
                    var_box_sel = tk.BooleanVar(master=self, value=(i in self._selected_boxes))
                    def _make_box_sel_cmd(b_idx, v):
                        def _cmd():
                            if v.get():
                                self._selected_boxes.add(b_idx)
                            else:
                                self._selected_boxes.discard(b_idx)
                        return _cmd
                    cb_sel = tk.Checkbutton(
                        slot_cb,
                        variable=var_box_sel,
                        command=_make_box_sel_cmd(i, var_box_sel),
                        bg=hdr_bg,
                        activebackground=hdr_bg,
                        selectcolor=t["bg_panel"],
                        bd=0,
                        cursor="hand2",
                    )
                    cb_sel.pack(fill="both", expand=True)
                    cb_sel.bind("<MouseWheel>", self._on_cont_mousewheel)

                # Translation Lock indicator immediately to the RIGHT of checkbox slot (fixed width=2)
                is_locked = i in getattr(self, "_locked_boxes", set())
                lbl_lock = tk.Label(
                    hdr,
                    text="🔒" if is_locked else "",
                    font=("Segoe UI", max(7, d_sz - 4)),
                    fg=t["accent_yellow"],
                    bg=hdr_bg,
                    width=2,
                    cursor="hand2",
                )
                lbl_lock.pack(side="left", padx=(0, 2))
                lbl_lock.bind("<Button-1>", lambda e, b_idx=i: self._on_toggle_card_lock(b_idx))
                lbl_lock.bind("<MouseWheel>", self._on_cont_mousewheel)
                create_tooltip(lbl_lock, "Click to toggle Translation Lock (Ctrl+L)")

                lbl_badge = tk.Label(hdr, text=f"◆ [BOX #{i+1:03d}]", font=("Consolas", max(8, d_sz - 3), "bold"), fg=t["misora_pink"], bg=hdr_bg)
                lbl_badge.pack(side="left")

                sp_text = box.speaker if box.speaker else "(Narration)"
                sp_fg = t["fg_text"] if box.speaker else t["fg_muted"]
                sp_font = (d_fam, max(8, d_sz - 3), "bold" if box.speaker else "italic")
                lbl_sp = tk.Label(hdr, text=sp_text, font=sp_font, fg=sp_fg, bg=hdr_bg)
                lbl_sp.pack(side="left", padx=(6, 4))

                vc_text = f"♪ {box.voice_cue}" if box.voice_cue else ""
                lbl_vc = tk.Label(hdr, text=vc_text, font=("Segoe UI", max(7, d_sz - 4)), fg=t["accent_blue"], bg=hdr_bg)
                lbl_vc.pack(side="left", padx=(2, 4))

                if len(box.segs) > 1:
                    lbl_segs = tk.Label(hdr, text=f"{len(box.segs)} segs", font=("Segoe UI", max(7, d_sz - 4), "bold"), fg=t["misora_pink"], bg=hdr_bg)
                    lbl_segs.pack(side="left", padx=(2, 4))

                # Rendered character count (Rule 19 / GAME-BOX-PREVIEW)
                char_len = get_rendered_length(box.clean_text)
                lbl_chars = tk.Label(hdr, text=f"({char_len} chars)", font=("Segoe UI", max(7, d_sz - 4)), fg=t["fg_muted"], bg=hdr_bg)
                lbl_chars.pack(side="right", padx=(4, 6))

                hdr.pack(fill="x", pady=0)

                # Editor Row with dynamic line-number gutter
                editor_row = tk.Frame(card_frame, bg=t["bg_panel"])
                editor_row.pack(fill="x", padx=0, pady=0)

                line_count = max(1, box.clean_text.count("\n") + 1)
                eff_height = max(2, min(10, line_count))

                gutter = tk.Text(
                    editor_row,
                    width=2,
                    height=eff_height,
                    font=("Consolas", max(8, d_sz - 2)),
                    bg=gutter_bg,
                    fg=gutter_fg,
                    bd=0,
                    relief="flat",
                    wrap="none",
                    takefocus=0,
                    cursor="arrow",
                    padx=1,
                    pady=3,
                    spacing1=2,
                    spacing3=2,
                )
                gutter.insert("1.0", "\n".join(str(n) for n in range(1, line_count + 1)))
                gutter.config(state="disabled")
                if self.show_line_numbers:
                    gutter.pack(side="left", fill="y", padx=(0, 2))

                txt = tk.Text(
                    editor_row,
                    wrap="word",
                    undo=False,
                    height=eff_height,
                    font=(d_fam, d_sz),
                    bg=t["bg_editor"],
                    fg=t["fg_text"],
                    insertbackground=t["misora_pink"],
                    selectbackground=t["highlight_bg"],
                    selectforeground=t["misora_pink"],
                    bd=1,
                    relief="solid",
                    highlightthickness=0,
                    padx=8,
                    pady=3,
                    spacing1=2,
                    spacing3=2
                )
                self._configure_editor_rich_tags(txt, d_fam, d_sz)
                if compiled:
                    self._insert_compiled_ngui_text(txt, "1.0", box.clean_text)
                    txt.config(state="disabled")
                else:
                    txt.insert("1.0", box.clean_text)
                    self._highlight_ngui_tags_for_widget(txt)

                txt.pack(side="left", fill="x", expand=True)

                # Bindings on card widgets
                for w in (card_frame, hdr, lbl_badge, lbl_sp, lbl_vc, editor_row, gutter, txt):
                    w.bind("<MouseWheel>", self._on_cont_mousewheel)

                self._install_shortcuts_bindtag(txt)
                txt.bind("<KeyRelease>", lambda e, idx=i, w=txt, g=gutter: self._commit_widget_edit(w))
                txt.bind("<<Cut>>", lambda e, w=txt: self.after_idle(lambda: self._commit_widget_edit(w)))
                txt.bind("<FocusIn>", lambda e, idx=i: self._on_card_focus_in(idx))
                txt.bind("<Control-a>", lambda e, w=txt: (w.tag_add("sel", "1.0", "end-1c"), "break")[1])
                txt.bind("<Control-A>", lambda e, w=txt: (w.tag_add("sel", "1.0", "end-1c"), "break")[1])
                txt.bind("<Control-Shift-C>", lambda e: (self.on_copy_script(), "break")[1])
                txt.bind("<Control-Shift-c>", lambda e: (self.on_copy_script(), "break")[1])
                txt.bind("<Control-v>", lambda e, idx=i, w=txt: self._on_card_paste_caret(idx, w))
                txt.bind("<<Paste>>", lambda e, idx=i, w=txt: (self._on_card_paste_caret(idx, w) or self.after_idle(lambda: self._commit_widget_edit(w))))
                txt.bind("<Control-Shift-V>", lambda e: (self.on_paste_cross_box(), "break")[1])
                txt.bind("<Control-Shift-v>", lambda e: (self.on_paste_cross_box(), "break")[1])
                txt.bind("<Control-b>", lambda e, w=txt: (self._card_shortcut_wrap(w, "[b]", "[/b]"), "break")[1])
                txt.bind("<Control-i>", lambda e, w=txt: (self._card_shortcut_wrap(w, "[i]", "[/i]"), "break")[1])
                txt.bind("<Control-u>", lambda e, w=txt: (self._card_shortcut_wrap(w, "[u]", "[/u]"), "break")[1])

                card_frame.pack(fill="x", padx=6, pady=(1, 2))

                self._card_widgets[i] = {
                    "card": card_frame,
                    "hdr": hdr,
                    "editor_row": editor_row,
                    "gutter": gutter,
                    "txt": txt,
                    "lbl_badge": lbl_badge,
                    "lbl_sp": lbl_sp,
                    "lbl_vc": lbl_vc,
                    "slot_cb": slot_cb,
                    "lbl_lock": lbl_lock,
                }

            self._highlight_continuous_matches()
        finally:
            self._suppress_continuous_events = False

    def _focus_continuous_box(
        self,
        box_idx: int,
        move_cursor: bool = True,
        char_offset: int = 0,
        explicit_span: Optional[Tuple[int, int]] = None
    ) -> None:
        """Scroll Continuous View to `box_idx`, highlight its card header, and sync metadata."""
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

        self._highlight_active_card_header(target_idx)
        self._sync_header_controls_for_card(target_idx)
        self._update_raw_view()

        if hasattr(self, "_card_widgets") and target_idx in self._card_widgets:
            card_info = self._card_widgets[target_idx]
            card = card_info["card"]
            self.update_idletasks()
            try:
                total_h = self.cont_stream_frame.winfo_height()
                if total_h > 0:
                    card_y = card.winfo_y()
                    fraction = max(0.0, min(1.0, card_y / total_h))
                    self.cont_canvas.yview_moveto(fraction)
            except Exception:
                pass

            txt_w = card_info["txt"]
            if move_cursor and str(txt_w.cget("state")) != "disabled":
                try:
                    target_pos = f"1.0 + {max(0, char_offset)}c"
                    txt_w.mark_set("insert", target_pos)
                    txt_w.see("insert")
                    txt_w.focus_set()
                except Exception:
                    pass

            if explicit_span is not None and not self.var_preview_compiled.get():
                s, e = explicit_span
                if e > s:
                    txt_w.tag_remove("search_hit", "1.0", tk.END)
                    txt_w.tag_add("search_hit", f"1.0 + {s}c", f"1.0 + {e}c")
                    txt_w.see(f"1.0 + {s}c")

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
        """Highlight active search keyword spans across all cards in Continuous View."""
        if self.var_preview_compiled.get():
            return
        if not hasattr(self, "_card_widgets") or not self._card_widgets:
            return

        matcher = None
        if self.active_search_options and self.active_search_options.query.strip():
            try:
                matcher = self.search_engine._compile_matcher(self.active_search_options)
            except Exception:
                matcher = None

        for b_idx, card_info in self._card_widgets.items():
            txt_w = card_info.get("txt")
            if not txt_w:
                continue
            try:
                txt_w.tag_remove("search_hit", "1.0", tk.END)
                if matcher:
                    box_tx = txt_w.get("1.0", "end-1c")
                    for s, e, _ in matcher(box_tx):
                        if e > s:
                            txt_w.tag_add("search_hit", f"1.0 + {s}c", f"1.0 + {e}c")
            except Exception:
                pass

    def _commit_speaker_edit(self) -> bool:
        """Central edit commit path for speaker entry edits (Rule 11, F20).
        Returns True if a mutation occurred, False if no-op or aborted.
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

        self.undo_journal.record(
            BoxEditDelta(
                box_index=idx,
                old_speaker=old_sp,
                new_speaker=new_sp,
                old_text=box.clean_text,
                new_text=cur_tx,
                file_path=str(self.current_file_path or ""),
                box_uid=box.uid,
                source="keyboard",
            ),
            label=f"Rename speaker #{idx + 1}"
        )

        try:
            self.current_doc.inject_box(idx, new_sp, cur_tx)
        except Exception as ex:
            self.logger.error("AST", f"Failed to inject speaker rename: {ex}")
            return False

        self._modified_boxes.add(idx)
        self._mark_document_dirty(self.current_file_path)

        if hasattr(self, "_refresh_continuous_box_header"):
            self._refresh_continuous_box_header(idx)
        elif hasattr(self, "_card_widgets") and idx in self._card_widgets:
            lbl_sp = self._card_widgets[idx].get("lbl_sp")
            if lbl_sp and lbl_sp.winfo_exists():
                lbl_sp.config(text=new_sp if new_sp else "(Narration)")

        self._update_raw_view()
        self._dirty_state_changed()
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
            self._update_rendered_char_count(new_tx)
            self._update_gutter_clean()
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

    def on_prev_box(self) -> None:
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

    def _update_rendered_char_count(self, text: str) -> None:
        """Update live rendered character counter and warn if text overflows dialogue frame (Rule 19 / GAME-BOX-PREVIEW)."""
        if not hasattr(self, "lbl_char_count") or not self.lbl_char_count.winfo_exists():
            return
        t = self.theme
        lines_info = measure_line_lengths(text)
        total_len = sum(l[1] for l in lines_info)
        max_line = max((l[1] for l in lines_info), default=0)
        if max_line > 45:
            self.lbl_char_count.config(
                text=f"Chars: {total_len} (Max: {max_line}) ⚠ Overflow",
                fg=t["misora_pink"]
            )
        else:
            self.lbl_char_count.config(
                text=f"Chars: {total_len} (Max: {max_line})",
                fg=t["fg_muted"]
            )

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
                    new_sp = self.speaker_var.get()
                    cur_tx = self.current_doc.boxes[self.current_box_idx].clean_text
                    self.current_doc.inject_box(self.current_box_idx, new_sp, cur_tx)
            elif self.var_continuous_view.get():
                self._sync_continuous_box_from_widget()
                if 0 <= self.current_box_idx < len(self.current_doc.boxes):
                    new_sp = self.speaker_var.get()
                    cur_tx = self.current_doc.boxes[self.current_box_idx].clean_text
                    self.current_doc.inject_box(self.current_box_idx, new_sp, cur_tx)
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

            if has_varargs or len(params) >= 6:
                t_args = (target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped)
                t_kwargs = {}
            elif has_varkw:
                t_args = (target_paths, opts, mem_docs)
                t_kwargs = {"search_seq": current_seq, "skip_paths": skip_paths, "initial_skipped": initial_skipped}
            else:
                avail_args = [target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped]
                t_args = tuple(avail_args[:len(params)])
                t_kwargs = {}
        except Exception:
            t_args = (target_paths, opts, mem_docs, current_seq, skip_paths, initial_skipped)
            t_kwargs = {}

        t = threading.Thread(
            target=target_fn,
            args=t_args,
            kwargs=t_kwargs,
            daemon=True
        )
        self._search_thread = t
        t.start()

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
    ) -> None:
        """Executed inside a background daemon thread (Rule 15, Part B.8)."""
        total_found = 0
        skipped_entries: List[Tuple[Path, str]] = list(initial_skipped or [])

        def on_prog(cur, tot, filename):
            self.search_queue.put(("progress", cur, tot, filename, search_seq))

        def on_err(fp, reason):
            skipped_entries.append((Path(fp), str(reason)))

        try:
            for target in paths:
                if self.search_cancel_flag:
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
                        results = self.search_engine.search_file(target, options, doc=mem_doc, on_error=on_err)
                    else:
                        results = self.search_engine.search_directory(
                            target, options, recursive=True,
                            on_progress=on_prog,
                            should_cancel=lambda: self.search_cancel_flag,
                            in_memory_docs=mem_docs,
                            on_error=on_err,
                            skip_paths=skip_paths,
                        )
                    total_found += len(results)
                    self.search_queue.put(("batch", results, search_seq))
                except Exception as ex:
                    skipped_entries.append((Path(target), str(ex)))
        finally:
            self.search_queue.put(("finished", total_found, skipped_entries, search_seq))

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
                    is_cancelled = getattr(self, "search_cancel_flag", False)

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

        try:
            if getattr(self, "_destroyed", False) or not self.winfo_exists():
                return
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

                        # S9b & S09: Synchronize in-memory cache using canonical keys 'env' and 'obj'
                        open_k = self._find_open_doc_key(fp)
                        if open_k and open_k in self.open_documents:
                            try:
                                b_doc, b_env, b_obj, _ = load_bundle_story(fp)
                                old_env = self.open_documents[open_k].get("env")
                                if old_env is not None and old_env is not b_env:
                                    dispose_unity_env(old_env)
                                self.open_documents[open_k]["doc"] = b_doc
                                self.open_documents[open_k]["env"] = b_env
                                self.open_documents[open_k]["obj"] = b_obj
                                self.open_documents[open_k]["dirty"] = False
                                self._record_saved_checkpoint(open_k, b_doc)
                                if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                    self.current_doc = b_doc
                                    self.current_unity_env = b_env
                                    self.current_text_obj = b_obj
                                    self.is_dirty = False
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
                            self.open_documents[open_k]["plain_text"] = text_to_set
                            self.open_documents[open_k]["dirty"] = False
                            self._record_saved_checkpoint(open_k, None, plain_text=text_to_set)
                            if open_k == (Path(self.current_file_path).resolve() if self.current_file_path else None):
                                self._plain_text_content = text_to_set
                                self.is_dirty = False
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

            if self.current_file_path and self._find_open_doc_key(self.current_file_path) is not None:
                self.open_file(self.current_file_path, reload_from_disk=True)

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

    def _toggle_dock_collapse(self) -> None:
        """Toggle left dock between collapsed and expanded width strictly via h_paned."""
        if getattr(self, "_dock_collapsed", False):
            # Expand dock
            self._dock_collapsed = False
            target_w = getattr(self, "_left_dock_width", 340) or 340
            if hasattr(self, "btn_dock_pin") and self.btn_dock_pin.winfo_exists():
                self.btn_dock_pin.pack_forget()
            if hasattr(self, "btn_tab_search") and self.btn_tab_search.winfo_exists():
                self.btn_tab_search.pack(side="left", padx=(2, 2))
            if hasattr(self, "btn_tab_files") and self.btn_tab_files.winfo_exists():
                self.btn_tab_files.pack(side="left", padx=(2, 2))
            if hasattr(self, "btn_dock_pin") and self.btn_dock_pin.winfo_exists():
                self.btn_dock_pin.pack(side="right", padx=(2, 2))
                self.btn_dock_pin.configure(text="📌")
            if hasattr(self, "_dock_pin_tooltip"):
                self._dock_pin_tooltip.text = "Collapse Left Panel"
            if getattr(self, "_left_dock_tab", "search") == "files":
                if hasattr(self, "tab_files_frame") and not self.tab_files_frame.winfo_ismapped():
                    self.tab_files_frame.pack(fill="both", expand=True)
            else:
                if hasattr(self, "tab_search_frame") and not self.tab_search_frame.winfo_ismapped():
                    self.tab_search_frame.pack(fill="both", expand=True)
            self.h_paned.paneconfigure(self.left_frame, minsize=160)
            self.h_paned.sash_place(0, target_w, 0)
        else:
            # Collapse dock
            current_w = self.left_frame.winfo_width()
            if current_w >= 100:
                self._left_dock_width = current_w
            self._dock_collapsed = True
            if hasattr(self, "btn_tab_search") and self.btn_tab_search.winfo_exists():
                self.btn_tab_search.pack_forget()
            if hasattr(self, "btn_tab_files") and self.btn_tab_files.winfo_exists():
                self.btn_tab_files.pack_forget()
            if hasattr(self, "tab_search_frame") and self.tab_search_frame.winfo_ismapped():
                self.tab_search_frame.pack_forget()
            if hasattr(self, "tab_files_frame") and self.tab_files_frame.winfo_ismapped():
                self.tab_files_frame.pack_forget()
            if hasattr(self, "btn_dock_pin") and self.btn_dock_pin.winfo_exists():
                self.btn_dock_pin.pack_forget()
                self.btn_dock_pin.pack(side="left", padx=2, pady=2)
                self.btn_dock_pin.configure(text="▶")
            if hasattr(self, "_dock_pin_tooltip"):
                self._dock_pin_tooltip.text = "Expand Left Panel"
            self.h_paned.paneconfigure(self.left_frame, minsize=0)
            self.h_paned.sash_place(0, 36, 0)

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

        closed_env = None
        if file_path in self.open_documents:
            closed_env = self.open_documents[file_path].get("env") if isinstance(self.open_documents[file_path], dict) else None
            del self.open_documents[file_path]
            self.undo_journal.prune_file(str(file_path))
            if closed_env is not None:
                dispose_unity_env(closed_env)

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
        """Open or focus the floating Translator Assistant workspace window."""
        if hasattr(self, "_translator_dialog") and self._translator_dialog and self._translator_dialog.winfo_exists():
            self._translator_dialog.lift()
            self._translator_dialog.focus_force()
            self._translator_dialog.refresh_box()
            return
        self._translator_dialog = TranslatorAssistantDialog(self)

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

        translate_async(
            orig_text,
            self.mtl_config,
            on_success=on_success,
            on_error=on_error,
            xuat_cache=getattr(self, "xuat_entries", None),
        )

    def _poll_mtl_queue(self) -> None:
        """Poll queued machine translation results on the main UI thread (Rule 15 / BUG-27)."""
        if not self.winfo_exists():
            return

        try:
            while True:
                msg = self._mtl_queue.get_nowait()
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
            if self.winfo_exists():
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

        # Atomic commit via batch undo
        self._commit_widget_edit()
        locked_set = getattr(self, "_locked_boxes", set())
        skipped_locked = 0

        self.undo_journal.begin_batch(f"Apply Script ({source_label})")
        try:
            # Apply metadata if requested and present
            if apply_meta and not result.metadata.is_empty():
                old_meta = self.current_doc.get_metadata()
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

            # Record box-level deltas in undo journal
            for b_idx, new_blk in targets:
                if b_idx in locked_set:
                    skipped_locked += 1
                    continue
                old_box = self.current_doc.boxes[b_idx]
                new_sp = new_blk.speaker if (apply_speakers and new_blk.speaker) else old_box.speaker
                old_uid = old_box.segs[0].record.uid if old_box.segs and old_box.segs[0].record else old_box.uid
                old_segs = [s.text for s in old_box.segs] if len(old_box.segs) > 1 else None
                new_segs = [new_blk.text] if len(old_box.segs) > 1 else None
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
                result,
                mode="replace",
                start_box_index=start_idx if not result.is_sparse else 0,
                apply_speakers=apply_speakers,
                apply_metadata=apply_meta,
                locked_indices=locked_set,
            )
            for b_idx, _ in targets:
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
        """Show application information dialog."""
        about_text = (
            "Misora: Unity3D Revision Tool & Story Editor\n"
            f"Version {__version__}\n\n"
            "A specialized GUI text editor for Princess Connect! Re:Dive\n"
            "Unity3D story bundles (.unity3d) and XUAT translation files.\n\n"
            "MIT License — Created for the Priconne Modding Community."
        )
        messagebox.showinfo("About Misora", about_text)


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

        self.apply_speakers = has_speakers
        self.apply_metadata = has_meta

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
            cb_meta.pack(side="left")

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
                new_txt = " ".join(new_blk.text.splitlines())[:80]

                self.tree.insert("", "end", values=(f"Box {b_idx + 1}", cur_spk, new_spk, cur_txt, new_txt))

    def on_apply(self) -> None:
        self.apply_speakers = self.var_apply_speakers.get()
        self.apply_metadata = self.var_apply_metadata.get()
        self.confirmed = True
        safe_grab_release(self)
        self.destroy()

    def on_cancel(self) -> None:
        self.confirmed = False
        safe_grab_release(self)
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
        self.app.mtl_config = self._get_draft_config()
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
            text="Include Speaker Names in Box delimiters (=== [BOX:0|Speaker:コッコロ] ===)",
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

    def _toggle_pin_top(self):
        self._is_pinned_top = not getattr(self, "_is_pinned_top", False)
        self.wm_attributes("-topmost", self._is_pinned_top)
        self.btn_pin.configure(text="📌" if self._is_pinned_top else "📍")
        self.app.show_toast(f"Translator Assistant {'pinned on top' if self._is_pinned_top else 'unpinned'}")

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