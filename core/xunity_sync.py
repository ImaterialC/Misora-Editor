#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.xunity_sync - Bi-directional synchronization between Unity3D story corrections
and plain-text XUnity Auto Translator (XUAT) dictionary files.
Strictly preserves BOM, line endings, key whitespace, and escapes newlines in values.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .story_ast import norm_search
from .text_encoding import detect_encoding_and_decode, encode_with_metadata


@dataclass
class SyncMatch:
    file_path: Path
    line_number: int
    raw_key: str
    old_translation: str
    new_translation: str
    success: bool = False
    is_conflict: bool = False


def split_xuat_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Split an XUAT dictionary line into (key, value) on the first unescaped '='.
    Respects comments starting with #, //, ;, r:, sr:.
    Preserves key whitespace exactly as written.
    """
    trimmed = line.lstrip()
    if not trimmed or trimmed.startswith(("#", "//", ";", "r:", "sr:")):
        return None

    # Search for first '=' not preceded by an unescaped backslash
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "=":
            # Check how many backslashes precede '='
            bs_count = 0
            k = i - 1
            while k >= 0 and line[k] == "\\":
                bs_count += 1
                k -= 1
            if bs_count % 2 == 0:
                return line[:i], line[i + 1:]
        i += 1

    return None


def escape_xuat_value(val: str) -> str:
    """
    Escape real newlines in translated values so each translation remains
    strictly on a single physical dictionary line.
    """
    return val.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


class XUnitySyncManager:
    """
    Locates and updates corresponding translation lines inside XUAT text files
    with strict encoding, newline escaping, BOM preservation, and immutable JP source keys.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else None
        # Cache of immutable Japanese source keys per box uid / identity
        self.jp_source_cache: Dict[int, str] = {}

    def register_jp_key(self, box_uid: int, jp_text: str) -> None:
        """Register an immutable Japanese source key for a box to prevent English overwrite."""
        if box_uid not in self.jp_source_cache and jp_text:
            self.jp_source_cache[box_uid] = jp_text

    def get_jp_key(self, box_uid: int, fallback: str = "") -> str:
        """Retrieve original Japanese source key, falling back to current text if untracked."""
        return self.jp_source_cache.get(box_uid, fallback)

    def preview_matches(
        self,
        japanese_key: str,
        search_roots: List[Path]
    ) -> List[SyncMatch]:
        """
        Preview matching lines across search_roots without writing any changes to disk.
        Flags duplicate or conflicting translations for user inspection.
        """
        norm_target = norm_search(japanese_key)
        matches: List[SyncMatch] = []
        seen_translations: Set[str] = set()

        for root in search_roots:
            root = Path(root)
            if not root.exists():
                continue

            txt_files = list(root.rglob("*.txt")) if root.is_dir() else [root]
            for tf in txt_files:
                if tf.name.endswith((".missing.txt", ".report.txt", "_SUMMARY.txt", "_warnings.txt")):
                    continue

                try:
                    raw_bytes = tf.read_bytes()
                    decoded = detect_encoding_and_decode(raw_bytes)
                    text = decoded.text
                except Exception:
                    continue

                newline = decoded.newline or ("\r\n" if "\r\n" in text else "\n")
                lines = text.split(newline)

                for idx, line in enumerate(lines, 1):
                    pair = split_xuat_line(line)
                    if not pair:
                        continue
                    k_part, v_part = pair
                    if norm_search(k_part) == norm_target:
                        is_conf = (bool(seen_translations) and v_part not in seen_translations)
                        seen_translations.add(v_part)
                        m = SyncMatch(
                            file_path=tf,
                            line_number=idx,
                            raw_key=k_part,
                            old_translation=v_part,
                            new_translation="",
                            success=False,
                            is_conflict=is_conf
                        )
                        matches.append(m)

        return matches

    def find_and_update(
        self,
        japanese_key: str,
        new_english_text: str,
        search_roots: List[Path],
        backup: bool = True,
        backup_dir: Optional[Path] = None,
    ) -> List[SyncMatch]:
        """
        Search for matching translation entries and update them with atomic write.
        Strictly preserves BOM, CRLF/LF line endings, key whitespace, and escapes newlines.
        """
        norm_target = norm_search(japanese_key)
        matches: List[SyncMatch] = []
        escaped_new_val = escape_xuat_value(new_english_text)

        for root in search_roots:
            root = Path(root)
            if not root.exists():
                continue

            txt_files = list(root.rglob("*.txt")) if root.is_dir() else [root]
            for tf in txt_files:
                if tf.name.endswith((".missing.txt", ".report.txt", "_SUMMARY.txt", "_warnings.txt")):
                    continue

                try:
                    raw_bytes = tf.read_bytes()
                    decoded = detect_encoding_and_decode(raw_bytes)
                    text = decoded.text
                except Exception:
                    continue

                # Preserve native line endings
                newline = decoded.newline or ("\r\n" if "\r\n" in text else "\n")
                lines = text.split(newline)
                file_modified = False
                new_lines = []

                for idx, line in enumerate(lines, 1):
                    pair = split_xuat_line(line)
                    if pair:
                        k_part, v_part = pair
                        if norm_search(k_part) == norm_target:
                            m = SyncMatch(
                                file_path=tf,
                                line_number=idx,
                                raw_key=k_part,
                                old_translation=v_part,
                                new_translation=escaped_new_val,
                                success=True
                            )
                            # Preserve exact key whitespace, escape value newlines
                            line = f"{k_part}={escaped_new_val}"
                            file_modified = True
                            matches.append(m)
                    new_lines.append(line)

                if file_modified:
                    if backup:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if backup_dir is not None:
                            bd = Path(backup_dir)
                            bd.mkdir(parents=True, exist_ok=True)
                            bak_path = bd / f"{tf.stem}.bak_{ts}{tf.suffix}"
                        else:
                            bak_path = tf.with_suffix(f".bak_{ts}")
                        shutil.copy2(tf, bak_path)

                    # Reassemble with preserved BOM, encoding, and native line endings
                    updated_text = newline.join(new_lines)
                    out_bytes = encode_with_metadata(
                        updated_text,
                        encoding=decoded.encoding,
                        has_bom=decoded.has_bom,
                        newline=decoded.newline,
                    )

                    # Atomic write via same-directory tmp file
                    tmp_file = tf.with_name(f"{tf.name}.{os.getpid()}.tmp")
                    try:
                        tmp_file.write_bytes(out_bytes)
                        os.replace(tmp_file, tf)
                    finally:
                        if tmp_file.exists():
                            try:
                                tmp_file.unlink()
                            except Exception:
                                pass

        return matches
