#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.font_manager — Dialogue font preset policy and Win32 private font loader.

Editor-display-only: font selection and private font loading never modify game files
or story ASTs. Pure Python + stdlib (ctypes/struct/pathlib) with zero implicit Tk root.
"""
from __future__ import annotations

import ctypes
import struct
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

PRESET_GLOBAL = "Global — Nunito Bold"
PRESET_JP = "Japanese — nintendoP_Humming-E_002pr"
BUILTIN_FONT_PRESETS: Tuple[str, str] = (PRESET_GLOBAL, PRESET_JP)

_FR_PRIVATE = 0x10
_VALID_SFNT_TAGS = {b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"}
_FONT_EXTS = {".ttf", ".otf"}


def _read_sfnt_family_name(path: Path) -> Optional[str]:
    """Validate SFNT header and extract Font Family (nameID 16 or 1) using stdlib struct."""
    data = path.read_bytes()
    if len(data) < 12 or data[:4] not in _VALID_SFNT_TAGS:
        return None
    num_tables = struct.unpack(">H", data[4:6])[0]
    if len(data) < 12 + num_tables * 16:
        return None

    name_offset = None
    name_length = None
    for i in range(num_tables):
        off = 12 + i * 16
        tag = data[off : off + 4]
        if tag == b"name":
            name_offset, name_length = struct.unpack(">II", data[off + 8 : off + 16])
            break
    if name_offset is None or name_length is None or name_offset + 6 > len(data):
        return None

    table = data[name_offset : name_offset + name_length]
    if len(table) < 6:
        return None
    _, count, str_offset = struct.unpack(">HHH", table[:6])
    if len(table) < 6 + count * 12:
        return None

    candidates: Dict[Tuple[int, int], str] = {}
    for i in range(count):
        rec_off = 6 + i * 12
        plat_id, enc_id, lang_id, name_id, length, offset = struct.unpack(
            ">HHHHHH", table[rec_off : rec_off + 12]
        )
        if name_id not in (1, 16):
            continue
        s_start = str_offset + offset
        s_end = s_start + length
        if s_end > len(table):
            continue
        raw = table[s_start:s_end]
        try:
            if plat_id == 3 or (plat_id == 0):
                val = raw.decode("utf-16-be", errors="strict").strip("\x00 ").strip()
            else:
                val = raw.decode("latin-1", errors="strict").strip("\x00 ").strip()
        except Exception:
            continue
        if val:
            candidates.setdefault((plat_id, name_id), val)

    for key in ((3, 16), (3, 1), (0, 16), (0, 1), (1, 16), (1, 1)):
        if key in candidates:
            return candidates[key]
    return ""


class FontManager:
    """Manages built-in dialogue font presets and private custom fonts in assets/fonts/."""

    def __init__(self, fonts_dir: Optional[Path] = None, logger: Optional[Any] = None) -> None:
        self.fonts_dir: Optional[Path] = Path(fonts_dir) if fonts_dir else None
        self.logger = logger
        self._loaded_paths: List[Path] = []
        self.custom_families: List[str] = []
        self.load_errors: List[str] = []
        self._disposed: bool = False
        self.refresh()

    def _warn(self, msg: str) -> None:
        self.load_errors.append(msg)
        if self.logger is not None:
            try:
                self.logger.warning("UI / Theme / Config", msg)
            except Exception:
                pass

    def refresh(self) -> List[str]:
        """Unload any previously loaded private fonts and rescan fonts_dir."""
        self._unload_loaded_paths()
        self.custom_families = []
        self.load_errors = []
        seen: Set[str] = set()

        if self.fonts_dir is None or not self.fonts_dir.is_dir():
            return []

        # 1. Scan .ttf / .otf files
        try:
            entries = sorted(self.fonts_dir.iterdir(), key=lambda p: p.name.lower())
        except Exception as exc:
            self._warn(f"Failed to scan custom fonts directory {self.fonts_dir}: {exc}")
            entries = []

        for path in entries:
            if not path.is_file() or path.suffix.lower() not in _FONT_EXTS:
                continue
            try:
                family = _read_sfnt_family_name(path)
                if family is None:
                    self._warn(f"Invalid or corrupt font file '{path.name}': unrecognized SFNT header.")
                    continue
                if sys.platform == "win32":
                    added = ctypes.windll.gdi32.AddFontResourceExW(str(path), _FR_PRIVATE, 0)
                    if added <= 0:
                        self._warn(f"Win32 AddFontResourceExW failed for '{path.name}'.")
                        continue
                    self._loaded_paths.append(path)
                fam_name = family or path.stem
                if fam_name not in seen:
                    seen.add(fam_name)
                    self.custom_families.append(fam_name)
            except Exception as exc:
                self._warn(f"Unreadable font file '{path.name}': {exc}")

        # 2. Optional custom_fonts.txt manifest
        manifest = self.fonts_dir / "custom_fonts.txt"
        if manifest.is_file():
            try:
                for raw_line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line not in seen:
                        seen.add(line)
                        self.custom_families.append(line)
            except Exception as exc:
                self._warn(f"Failed to read custom_fonts.txt: {exc}")

        return list(self.custom_families)

    def _unload_loaded_paths(self) -> None:
        if sys.platform == "win32":
            for path in self._loaded_paths:
                try:
                    ctypes.windll.gdi32.RemoveFontResourceExW(str(path), _FR_PRIVATE, 0)
                except Exception:
                    pass
        self._loaded_paths.clear()

    def dispose(self) -> None:
        """Release all privately loaded Win32 font resources."""
        if not self._disposed:
            self._unload_loaded_paths()
            self._disposed = True

    def resolve_font_parts(
        self,
        selection: Optional[str],
        available_families: Optional[Iterable[str]] = None,
    ) -> Tuple[str, Optional[str]]:
        """Resolve a preset or custom font selection to (tk_family, optional_weight).

        Never creates an implicit Tk root; uses available_families only when supplied.
        """
        fam_map: Dict[str, str] = {}
        if available_families is not None:
            for f in available_families:
                if isinstance(f, str) and f.strip():
                    fam_map.setdefault(f.strip().lower(), f.strip())

        def _match(candidate: str) -> Optional[str]:
            if not fam_map:
                return None
            return fam_map.get(candidate.strip().lower())

        sel = (selection or "").strip() or PRESET_GLOBAL

        if sel == PRESET_GLOBAL or sel.lower() == "nunito bold":
            if fam_map:
                exact = _match("Nunito Bold")
                if exact:
                    return (exact, None)
                nunito = _match("Nunito")
                if nunito:
                    return (nunito, "bold")
                segoe = _match("Segoe UI")
                if segoe:
                    return (segoe, None)
            return ("Segoe UI", None) if fam_map else ("Nunito Bold", None)

        if sel == PRESET_JP or sel.lower() == "nintendop_humming-e_002pr":
            if fam_map:
                for cand in ("nintendoP_Humming-E_002pr", "Yu Gothic UI", "Meiryo UI", "Segoe UI"):
                    m = _match(cand)
                    if m:
                        return (m, None)
            return ("nintendoP_Humming-E_002pr", None)

        if fam_map:
            m = _match(sel)
            if m:
                return (m, None)
            segoe = _match("Segoe UI")
            if segoe:
                return (segoe, None)
        return (sel, None)

    def resolve_font_family(
        self,
        selection: Optional[str],
        available_families: Optional[Iterable[str]] = None,
    ) -> str:
        """Resolve a preset or custom font selection to a Tk font family string."""
        fam, _ = self.resolve_font_parts(selection, available_families=available_families)
        return fam

    def migrate_legacy_font(self, saved_value: Optional[str]) -> Tuple[str, bool]:
        """Keep valid presets or listed custom fonts; migrate legacy families to PRESET_GLOBAL."""
        val = (saved_value or "").strip()
        if not val:
            return (PRESET_GLOBAL, False)
        if val in BUILTIN_FONT_PRESETS:
            return (val, False)
        if val in self.custom_families:
            return (val, False)
        return (PRESET_GLOBAL, True)
