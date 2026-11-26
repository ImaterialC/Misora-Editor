#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean-Room Priconne-Style Preview Frame Generator & Bounded PhotoImage Cache.

Generates anti-aliased rounded dialogue capsules, nameplates, pink triangle
indicators, All Script card caps, pale-blue dotted rules, and voice badges
purely via Pillow (zero copyrighted AtlasAdv sprites; NO-02).
"""
from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, Optional, Tuple

MAX_PREVIEW_CACHE: int = 128
_PREVIEW_CACHE: Dict[Tuple[Any, ...], tk.PhotoImage] = {}


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    s = (hex_color or "#ffffff").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return (255, 255, 255, alpha)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), alpha)


def _resolve_root(master: Optional[tk.Widget]) -> Optional[tk.Misc]:
    root: Optional[tk.Misc] = master
    if root is not None:
        try:
            root = root.winfo_toplevel()
        except Exception:
            pass
    if root is None:
        root = getattr(tk, "_default_root", None)
    return root


def _cache_get(key: Tuple[Any, ...], root: Optional[tk.Misc]) -> Optional[tk.PhotoImage]:
    if key not in _PREVIEW_CACHE:
        return None
    img = _PREVIEW_CACHE[key]
    try:
        target_tk = root.tk if root else getattr(getattr(tk, "_default_root", None), "tk", None)
        if target_tk:
            target_tk.call("image", "type", img._name)
            return img
    except Exception:
        pass
    _PREVIEW_CACHE.pop(key, None)
    return None


def _cache_put(key: Tuple[Any, ...], pil_img: Any, root: Optional[tk.Misc]) -> Optional[tk.PhotoImage]:
    from PIL import ImageTk

    tk_img = ImageTk.PhotoImage(pil_img, master=root) if root else ImageTk.PhotoImage(pil_img)
    while len(_PREVIEW_CACHE) >= MAX_PREVIEW_CACHE:
        try:
            oldest_key = next(iter(_PREVIEW_CACHE))
            _PREVIEW_CACHE.pop(oldest_key, None)
        except (StopIteration, KeyError):
            break
    _PREVIEW_CACHE[key] = tk_img
    return tk_img


def get_dialogue_capsule_image(
    width: int,
    height: int,
    fill_hex: str = "#F8F6F0",
    border_hex: str = "#C8A86B",
    inner_rim_hex: str = "#FFFFFF",
    radius: int = 16,
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate a crisp anti-aliased rounded cream-white capsule with champagne-gold border."""
    w = max(40, int(width))
    h = max(30, int(height))
    r = max(4, min(int(radius), min(w, h) // 2 - 2))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "dlg_capsule", w, h, fill_hex, border_hex, inner_rim_hex, r)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        sw, sh, sr = w * scale, h * scale, r * scale
        im = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)

        pad = scale
        draw.rounded_rectangle(
            [pad, pad, sw - pad - 1, sh - pad - 1],
            radius=sr,
            fill=_hex_to_rgba(fill_hex),
            outline=_hex_to_rgba(border_hex),
            width=max(2, int(1.5 * scale)),
        )
        inset = pad + max(3, int(2 * scale))
        draw.rounded_rectangle(
            [inset, inset, sw - inset - 1, sh - inset - 1],
            radius=max(2, sr - 2 * scale),
            outline=_hex_to_rgba(inner_rim_hex, 210),
            width=max(1, scale),
        )
        out = im.resize((w, h), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def get_dialogue_nameplate_image(
    width: int,
    height: int,
    fill_hex: str = "#C24270",
    border_hex: str = "#C8A86B",
    radius: int = 10,
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate a rounded pill nameplate for spoken Dialogue Preview lines."""
    w = max(40, int(width))
    h = max(18, int(height))
    r = max(4, min(int(radius), min(w, h) // 2 - 1))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "dlg_plate", w, h, fill_hex, border_hex, r)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        sw, sh, sr = w * scale, h * scale, r * scale
        im = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        pad = scale // 2
        draw.rounded_rectangle(
            [pad, pad, sw - pad - 1, sh - pad - 1],
            radius=sr,
            fill=_hex_to_rgba(fill_hex),
            outline=_hex_to_rgba(border_hex),
            width=max(2, int(1.25 * scale)),
        )
        out = im.resize((w, h), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def get_dialogue_triangle_image(
    size: int = 16,
    fill_hex: str = "#FF6B9E",
    outline_hex: str = "#FFFFFF",
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate an anti-aliased pink downward triangle with crisp white outline."""
    sz = max(10, int(size))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "dlg_tri", sz, fill_hex, outline_hex)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        ssz = sz * scale
        im = Image.new("RGBA", (ssz, ssz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)

        # Outer white outline triangle
        outer_pts = [
            (2 * scale, 3 * scale),
            (ssz - 2 * scale, 3 * scale),
            (ssz // 2, ssz - 2 * scale),
        ]
        draw.polygon(outer_pts, fill=_hex_to_rgba(outline_hex))

        # Inner pink fill triangle
        inner_pts = [
            (3.4 * scale, 4.1 * scale),
            (ssz - 3.4 * scale, 4.1 * scale),
            (ssz / 2.0, ssz - 3.8 * scale),
        ]
        draw.polygon(inner_pts, fill=_hex_to_rgba(fill_hex))

        out = im.resize((sz, sz), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def get_all_script_card_top_image(
    width: int,
    height: int = 10,
    radius: int = 10,
    canvas_bg: str = "#F4F2ED",
    card_bg: str = "#FFFFFF",
    border_hex: str = "#B8BCCA",
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate top rounded cap for an All Script Preview card."""
    w = max(80, int(width))
    h = max(6, int(height))
    r = max(4, min(int(radius), h))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "as_top", w, h, r, canvas_bg, card_bg, border_hex)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        sw, sh, sr = w * scale, h * scale, r * scale
        im = Image.new("RGBA", (sw, sh * 2), _hex_to_rgba(canvas_bg))
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle(
            [0, 0, sw - 1, sh * 2 - 1],
            radius=sr,
            fill=_hex_to_rgba(card_bg),
            outline=_hex_to_rgba(border_hex),
            width=max(2, scale),
        )
        top_half = im.crop((0, 0, sw, sh))
        out = top_half.resize((w, h), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def get_all_script_card_bottom_image(
    width: int,
    height: int = 10,
    radius: int = 10,
    canvas_bg: str = "#F4F2ED",
    card_bg: str = "#FFFFFF",
    border_hex: str = "#B8BCCA",
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate bottom rounded cap for an All Script Preview card."""
    w = max(80, int(width))
    h = max(6, int(height))
    r = max(4, min(int(radius), h))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "as_bot", w, h, r, canvas_bg, card_bg, border_hex)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        sw, sh, sr = w * scale, h * scale, r * scale
        im = Image.new("RGBA", (sw, sh * 2), _hex_to_rgba(canvas_bg))
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle(
            [0, 0, sw - 1, sh * 2 - 1],
            radius=sr,
            fill=_hex_to_rgba(card_bg),
            outline=_hex_to_rgba(border_hex),
            width=max(2, scale),
        )
        bot_half = im.crop((0, sh, sw, sh * 2))
        out = bot_half.resize((w, h), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def get_all_script_dotted_rule_image(
    width: int,
    height: int = 5,
    dot_hex: str = "#B8CCE8",
    bg_hex: str = "#FFFFFF",
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate pale-blue dotted horizontal divider rule for All Script Preview cards."""
    w = max(40, int(width))
    h = max(3, int(height))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "as_dot", w, h, dot_hex, bg_hex)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        im = Image.new("RGBA", (w, h), _hex_to_rgba(bg_hex))
        draw = ImageDraw.Draw(im)
        y = h // 2
        dot_rgba = _hex_to_rgba(dot_hex)
        for x in range(0, w - 2, 5):
            draw.line([(x, y), (x + 2, y)], fill=dot_rgba, width=1)
        return _cache_put(key, im, root)
    except Exception:
        return None


def get_voice_badge_image(
    size: int = 20,
    bg_hex: str = "#4E8DF5",
    border_hex: str = "#2D599E",
    fg_hex: str = "#FFFFFF",
    master: Optional[tk.Widget] = None,
) -> Optional[tk.PhotoImage]:
    """Generate a clean-room blue circular speaker badge for voiced lines."""
    sz = max(14, int(size))
    root = _resolve_root(master)
    key = (id(root) if root else 0, "voice_badge", sz, bg_hex, border_hex, fg_hex)
    cached = _cache_get(key, root)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageDraw

        scale = 4
        ssz = sz * scale
        im = Image.new("RGBA", (ssz, ssz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        pad = scale
        draw.ellipse(
            [pad, pad, ssz - pad - 1, ssz - pad - 1],
            fill=_hex_to_rgba(bg_hex),
            outline=_hex_to_rgba(border_hex),
            width=max(2, scale),
        )
        # Speaker cone + sound waves
        fg = _hex_to_rgba(fg_hex)
        cx, cy = ssz * 0.42, ssz * 0.50
        cone = [
            (cx - 3.2 * scale, cy - 2.0 * scale),
            (cx - 1.0 * scale, cy - 2.0 * scale),
            (cx + 1.8 * scale, cy - 4.2 * scale),
            (cx + 1.8 * scale, cy + 4.2 * scale),
            (cx - 1.0 * scale, cy + 2.0 * scale),
            (cx - 3.2 * scale, cy + 2.0 * scale),
        ]
        draw.polygon(cone, fill=fg)
        draw.arc(
            [cx + 1.2 * scale, cy - 3.2 * scale, cx + 5.0 * scale, cy + 3.2 * scale],
            start=-55,
            end=55,
            fill=fg,
            width=max(2, int(1.1 * scale)),
        )
        out = im.resize((sz, sz), Image.Resampling.LANCZOS)
        return _cache_put(key, out, root)
    except Exception:
        return None


def prune_preview_cache(root_widget: Optional[tk.Widget] = None) -> int:
    """Evict cached preview PhotoImages associated with destroyed widgets or a specific root."""
    pruned = 0
    target_id = id(root_widget) if root_widget is not None else None
    dead_keys = []
    for key, img in list(_PREVIEW_CACHE.items()):
        rid = key[0]
        if target_id is not None and rid == target_id:
            dead_keys.append(key)
        else:
            try:
                target_tk = (
                    getattr(root_widget, "tk", None)
                    if root_widget
                    else getattr(getattr(tk, "_default_root", None), "tk", None)
                )
                if target_tk and hasattr(img, "_name"):
                    target_tk.call("image", "type", img._name)
            except Exception:
                dead_keys.append(key)
    for k in dead_keys:
        if _PREVIEW_CACHE.pop(k, None) is not None:
            pruned += 1
    return pruned


def clear_preview_cache() -> None:
    """Clear all cached preview PhotoImage references."""
    _PREVIEW_CACHE.clear()
