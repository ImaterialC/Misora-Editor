#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misora Theme Palette, Window Icon & Illustrated Icon Manager
=============================================================
Official Misora Purple & White UI palette, chibi window icon, and
32-bit RGBA illustrated icon asset manager (offline Twemoji suite).
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from typing import Dict, Optional, Tuple

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
_ICONS_DIR: Path = Path(__file__).resolve().parent / "icons"
MAX_ICON_CACHE: int = 128
_ICON_CACHE: Dict[Tuple[int, str, int, int], tk.PhotoImage] = {}


def _create_fallback_icon(size: int = 32) -> tk.PhotoImage:
    """Generate a procedural Purple & White 'M' PhotoImage (fallback only)."""
    img = tk.PhotoImage(width=size, height=size)
    bg_outer = "#612ea0"
    bg_inner = "#7b42bc"
    border_hi = "#b98aff"
    fg_white = "#ffffff"

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
        img.put("{" + " ".join(row) + "}", to=(0, y))
    return img


# Keep old name as an alias so any code that calls create_misora_icon() still works
create_misora_icon = _create_fallback_icon


def apply_window_icon(window: tk.Tk) -> None:
    """Attach the Misora chibi-head icon to *window*.

    Strategy (Windows):
      1. iconbitmap() with the real .ico file — gives the best taskbar / Alt-Tab icon.
      2. iconphoto() with a PhotoImage — works on all platforms as a fallback.
    """
    if sys.platform == "win32" and _ICO_PATH.is_file():
        try:
            window.iconbitmap(default=str(_ICO_PATH))
            return
        except Exception:
            pass

    try:
        try:
            from PIL import Image, ImageTk  # type: ignore
            if _ICO_PATH.is_file():
                pil_img = Image.open(_ICO_PATH)
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

        icon_img = _create_fallback_icon(32)
        window.iconphoto(True, icon_img)
        setattr(window, "_misora_icon_ref", icon_img)
    except Exception:
        pass


def get_dpi_scale(master: Optional[tk.Misc] = None) -> float:
    """Return clamped DPI scale factor (1.0 .. 2.5) relative to standard 96 DPI."""
    root = master
    if root is not None:
        try:
            root = root.winfo_toplevel()
        except Exception:
            pass
    if root is None:
        root = getattr(tk, "_default_root", None)
    if root is not None:
        try:
            px = float(root.winfo_fpixels("1i"))
            if px > 0:
                return max(1.0, min(2.5, px / 96.0))
        except Exception:
            pass
    return 1.0


def scale_icon_size(size: Tuple[int, int], master: Optional[tk.Misc] = None) -> Tuple[int, int]:
    """Scale a logical (width, height) icon size by the active Tk DPI factor."""
    scale = get_dpi_scale(master)
    return (max(1, int(round(size[0] * scale))), max(1, int(round(size[1] * scale))))


def get_icon(
    name: str,
    size: Tuple[int, int] = (20, 20),
    master: Optional[tk.Widget] = None,
    dpi_aware: bool = False,
) -> Optional[tk.PhotoImage]:
    """Retrieve a cached Tkinter PhotoImage for the given illustrated icon name and size."""
    root = master
    if root is not None:
        try:
            root = root.winfo_toplevel()
        except Exception:
            pass
    if root is None:
        root = getattr(tk, "_default_root", None)

    eff_size = scale_icon_size(size, master=root) if dpi_aware else size
    root_id = id(root) if root else 0
    cache_key = (root_id, name, eff_size[0], eff_size[1])
    if cache_key in _ICON_CACHE:
        img = _ICON_CACHE[cache_key]
        try:
            target_tk = root.tk if root else getattr(getattr(tk, "_default_root", None), "tk", None)
            if target_tk:
                target_tk.call("image", "type", img._name)
                return img
            else:
                _ICON_CACHE.pop(cache_key, None)
        except Exception:
            _ICON_CACHE.pop(cache_key, None)

    img_path = _ICONS_DIR / f"{name}.png"
    if not img_path.is_file():
        return None

    try:
        from PIL import Image, ImageTk
        raw_im = Image.open(img_path)
        try:
            pil_im = raw_im.convert("RGBA")
        finally:
            try:
                raw_im.close()
            except Exception:
                pass
        if pil_im.size != eff_size:
            pil_im = pil_im.resize(eff_size, Image.Resampling.LANCZOS)
        tk_im = ImageTk.PhotoImage(pil_im, master=root) if root else ImageTk.PhotoImage(pil_im)

        # Enforce MAX_ICON_CACHE capacity bounding (S8b-2)
        if len(_ICON_CACHE) >= MAX_ICON_CACHE:
            while len(_ICON_CACHE) >= MAX_ICON_CACHE:
                try:
                    oldest_key = next(iter(_ICON_CACHE))
                    _ICON_CACHE.pop(oldest_key, None)
                except (StopIteration, KeyError):
                    break

        _ICON_CACHE[cache_key] = tk_im
        return tk_im
    except Exception:
        return None


def prune_icon_cache(root_widget: Optional[tk.Widget] = None) -> int:
    """Evict cached icons associated with destroyed widgets or a specific widget (S8b-2).

    Returns the number of evicted cache entries.
    """
    pruned = 0
    target_id = id(root_widget) if root_widget is not None else None

    dead_keys = []
    for key, img in list(_ICON_CACHE.items()):
        rid, name, w, h = key
        if target_id is not None and rid == target_id:
            dead_keys.append(key)
        else:
            try:
                target_tk = getattr(root_widget, "tk", None) if root_widget else getattr(getattr(tk, "_default_root", None), "tk", None)
                if target_tk and hasattr(img, "_name"):
                    target_tk.call("image", "type", img._name)
            except Exception:
                dead_keys.append(key)

    for k in dead_keys:
        if _ICON_CACHE.pop(k, None) is not None:
            pruned += 1

    return pruned


def clear_icon_cache() -> None:
    """Clear all cached PhotoImage references."""
    _ICON_CACHE.clear()
