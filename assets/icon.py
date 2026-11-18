#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misora Theme Palette & Window Icon
====================================
Official Misora Purple & White UI palette.
Window icon uses the real Misora chibi head (assets/misora.ico) with a
procedural PhotoImage fallback for platforms that don't support .ico files.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from typing import Dict

THEME: Dict[str, str] = {
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
}

# Path to the real Misora chibi-head .ico (multi-size: 16/24/32/48/64/128/256 px)
_ICO_PATH: Path = Path(__file__).resolve().parent / "misora.ico"


def _create_fallback_icon(size: int = 32) -> tk.PhotoImage:
    """Generate a procedural Purple & White 'M' PhotoImage (fallback only)."""
    img = tk.PhotoImage(width=size, height=size)
    bg_outer = "#612ea0"
    bg_inner = "#7b42bc"
    border_hi = "#d4c4ec"
    fg_white = "#ffffff"

    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            if (x in (0, size - 1) and y in (0, 1, size - 2, size - 1)) or (
                y in (0, size - 1) and x in (0, 1, size - 2, size - 1)
            ):
                row.append(bg_outer)
                continue
            if x in (1, size - 2) or y in (1, size - 2):
                row.append(border_hi)
                continue
            in_left_stem = 7 <= x <= 10 and 8 <= y <= 23
            in_right_stem = 21 <= x <= 24 and 8 <= y <= 23
            in_left_diag = (11 <= x <= 15) and (abs((y - 9) - (x - 10) * 2) <= 1) and (8 <= y <= 19)
            in_right_diag = (16 <= x <= 20) and (abs((y - 9) - (21 - x) * 2) <= 1) and (8 <= y <= 19)
            if in_left_stem or in_right_stem or in_left_diag or in_right_diag:
                row.append(fg_white)
            else:
                row.append(bg_inner)
        rows.append("{" + " ".join(row) + "}")

    img.put(" ".join(rows))
    return img


# Keep old name as an alias so any code that calls create_misora_icon() still works
create_misora_icon = _create_fallback_icon


def apply_window_icon(window: tk.Tk) -> None:
    """Attach the Misora chibi-head icon to *window*.

    Strategy (Windows):
      1. iconbitmap() with the real .ico file — gives the best taskbar / Alt-Tab icon.
      2. iconphoto() with a PhotoImage — works on all platforms as a fallback.
    """
    # --- Windows: use the real .ico for crisp taskbar / Alt-Tab icon ---
    if sys.platform == "win32" and _ICO_PATH.is_file():
        try:
            window.iconbitmap(default=str(_ICO_PATH))
            return  # iconbitmap handles all sizes; no need for iconphoto as well
        except Exception:
            pass  # fall through to PhotoImage fallback

    # --- Cross-platform fallback: PhotoImage (also used if .ico is missing) ---
    try:
        # Try loading the .ico via Pillow/ImageTk for a nicer result
        try:
            from PIL import Image, ImageTk  # type: ignore
            if _ICO_PATH.is_file():
                pil_img = Image.open(_ICO_PATH)
                # Pick the best available size (prefer 32, fall back to first)
                sizes = getattr(pil_img, "n_frames", 1)
                best = None
                if hasattr(pil_img, "size"):
                    pil_img.seek(0)
                    best = pil_img
                    for frame in range(sizes):
                        pil_img.seek(frame)
                        if pil_img.size == (32, 32):
                            best = pil_img.copy()
                            break
                tk_img = ImageTk.PhotoImage(best.resize((32, 32)).convert("RGBA"))
                window.iconphoto(True, tk_img)
                setattr(window, "_misora_icon_ref", tk_img)
                return
        except Exception:
            pass

        # Last resort: draw the procedural 'M' emblem
        icon_img = _create_fallback_icon(32)
        window.iconphoto(True, icon_img)
        setattr(window, "_misora_icon_ref", icon_img)
    except Exception:
        pass