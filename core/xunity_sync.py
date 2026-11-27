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
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

from .story_ast import norm_search
from .text_encoding import detect_encoding_and_decode, encode_with_metadata, write_atomic_encoded


@dataclass
class SyncMatch:
    file_path: Path
    line_number: int
    raw_key: str
    old_translation: str
    new_translation: str
    success: bool = False
    is_conflict: bool = False


@dataclass
class BatchSyncTarget:
    """A single modified box's batched XUAT sync request."""
    target_token: str
    box_uid: Optional[int]
    jp_key: str
    norm_key: str
    new_english: str
    box_index: int


@dataclass
class BatchConflictItem:
    """Summary of one C1 (differing old_value) conflict passed in a single batched callback."""
    norm_key: str
    jp_key: str
    new_english: str
    old_values: List[str]
    matched_files: List[str]


@dataclass
class BatchMatchRecord:
    """A matched dictionary line inside an eligible XUAT file."""
    file_path: Path
    line_index: int
    raw_key: str
    old_value: str
    norm_key: str


@dataclass
class FileSnapshot:
    """Captured file decode state & metadata at scan time — retained ONLY for matched files."""
    decoded_text: str
    encoding: str
    has_bom: bool
    newline: Optional[str]
    mtime_ns: int
    size: int
    ino: int
    dev: int


@dataclass
class BatchSyncResult:
    """Granular per-target outcome reporting across 5 distinct categories."""
    succeeded_tokens: Set[str] = field(default_factory=set)
    unmatched_tokens: Set[str] = field(default_factory=set)
    conflict_skipped_tokens: Set[str] = field(default_factory=set)
    freshness_failed_tokens: Set[str] = field(default_factory=set)
    io_failed_tokens: Set[str] = field(default_factory=set)
    synced_files: Set[str] = field(default_factory=set)
    c3_conflict_keys: List[str] = field(default_factory=list)
    c1_declined_keys: List[str] = field(default_factory=list)
    freshness_aborted_files: List[str] = field(default_factory=list)
    io_failed_files: List[str] = field(default_factory=list)
    total_lines_scanned: int = 0
    files_scanned: int = 0
    elapsed_seconds: float = 0.0


def _default_backup_path(
    source_path: Union[str, Path],
    backup_dir: Union[str, Path],
    tag: str = "bak",
) -> Path:
    """Pure-Python collision-resistant fallback matching misora.make_collision_resistant_backup_path."""
    src_p = Path(source_path)
    bd = Path(backup_dir)
    bd.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    candidate = bd / f"{src_p.stem}.{tag}_{ts}{src_p.suffix}"
    counter = 1
    while candidate.exists():
        candidate = bd / f"{src_p.stem}.{tag}_{ts}_{counter}{src_p.suffix}"
        counter += 1
    return candidate


def _normcase_path(path: Path) -> str:
    try:
        return os.path.normcase(os.path.normpath(str(path.resolve())))
    except Exception:
        return os.path.normcase(os.path.normpath(str(path)))


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

    def register_jp_key(self, box_uid: Optional[int], jp_text: str) -> None:
        """Register an immutable Japanese source key for a box to prevent English overwrite."""
        if box_uid is not None and box_uid not in self.jp_source_cache and jp_text:
            self.jp_source_cache[box_uid] = jp_text

    def register_jp_keys(self, keys: Dict[int, str]) -> None:
        """Bulk register immutable Japanese source keys by box UID."""
        for uid, text in keys.items():
            self.register_jp_key(uid, text)

    def get_jp_key(self, box_uid: Optional[int], fallback: str = "") -> str:
        """Retrieve original Japanese source key, falling back to current text if untracked."""
        if box_uid is None:
            return fallback
        return self.jp_source_cache.get(box_uid, fallback)

    def has_jp_key(self, box_uid: Optional[int]) -> bool:
        """Check if an immutable Japanese source key is registered for box_uid."""
        return box_uid is not None and box_uid in self.jp_source_cache

    def clear_jp_keys(self) -> None:
        """Clear cached Japanese source keys."""
        self.jp_source_cache.clear()

    def unregister_jp_keys(self, box_uids: Iterable[Optional[int]]) -> int:
        """Remove only the specified box UIDs from jp_source_cache without affecting other documents."""
        removed = 0
        for uid in box_uids:
            if uid is not None and uid in self.jp_source_cache:
                self.jp_source_cache.pop(uid, None)
                removed += 1
        return removed

    def preview_matches(
        self,
        japanese_key: str,
        search_roots: List[Path]
    ) -> List[SyncMatch]:
        """
        Preview matching lines across search_roots without writing any changes to disk.
        Flags duplicate or conflicting translations for user inspection.
        """
        if not japanese_key:
            return []

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

        if len(seen_translations) > 1:
            for m in matches:
                m.is_conflict = True

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
        if not japanese_key:
            return []

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

                    # Reassemble with preserved BOM, encoding, and native line endings via atomic write (BUG-26)
                    updated_text = newline.join(new_lines)
                    write_atomic_encoded(
                        tf,
                        updated_text,
                        encoding=decoded.encoding,
                        has_bom=decoded.has_bom,
                        newline=decoded.newline,
                    )

        return matches

    def batch_sync(
        self,
        targets: List[BatchSyncTarget],
        search_roots: List[Path],
        backup: bool = True,
        backup_dir: Optional[Path] = None,
        conflict_callback: Optional[Callable[[List[BatchConflictItem]], bool]] = None,
        is_excluded_fn: Optional[Callable[[Path], bool]] = None,
        resolve_roots_fn: Optional[Callable[[Iterable[Union[str, Path]]], List[Path]]] = None,
        backup_path_fn: Optional[Callable[[Union[str, Path], Union[str, Path], str], Path]] = None,
    ) -> BatchSyncResult:
        """
        Bounded single-pass batched XUAT sync (O(F + E + B + M)).
        Validates roots strictly to Translation\\en\\Text, streams Stage 1+2 retaining
        snapshots ONLY for matched files, runs single-batched conflict confirmation (C1..C4),
        checks pre-write stat freshness, and writes each modified file atomically once.
        """
        t0 = time.perf_counter()
        result = BatchSyncResult()

        if not targets:
            result.elapsed_seconds = time.perf_counter() - t0
            return result

        # Function-scope lazy imports avoid top-level circular dependency with core.xuat_index
        if resolve_roots_fn is None:
            from .xuat_index import resolve_xuat_text_roots as resolve_roots_fn
        if is_excluded_fn is None:
            from .xuat_index import _is_excluded_xuat_file as is_excluded_fn

        valid_targets: List[BatchSyncTarget] = []
        for t in targets:
            if not t.jp_key or not t.norm_key:
                result.unmatched_tokens.add(t.target_token)
            else:
                valid_targets.append(t)

        if not valid_targets or not search_roots:
            for t in valid_targets:
                result.unmatched_tokens.add(t.target_token)
            result.elapsed_seconds = time.perf_counter() - t0
            return result

        validated_roots = resolve_roots_fn(search_roots)
        if not validated_roots:
            for t in valid_targets:
                result.unmatched_tokens.add(t.target_token)
            result.elapsed_seconds = time.perf_counter() - t0
            return result

        target_map: Dict[str, List[BatchSyncTarget]] = {}
        for t in valid_targets:
            target_map.setdefault(t.norm_key, []).append(t)

        # Stage 1+2: Streamed single-pass scan & match (retain snapshot ONLY for matched files)
        seen_paths: Set[str] = set()
        matched_snapshots: Dict[str, FileSnapshot] = {}
        canonical_paths: Dict[str, Path] = {}
        matches_by_key: Dict[str, List[BatchMatchRecord]] = {}

        def _scan_file(tf: Path) -> None:
            if tf.suffix.lower() != ".txt":
                return
            if is_excluded_fn(tf):
                return
            tf_norm = _normcase_path(tf)
            if tf_norm in seen_paths:
                return
            seen_paths.add(tf_norm)

            try:
                st = os.stat(tf)
                raw_bytes = tf.read_bytes()
                decoded = detect_encoding_and_decode(raw_bytes)
                text = decoded.text
            except Exception:
                return

            newline = decoded.newline or ("\r\n" if "\r\n" in text else "\n")
            lines = text.split(newline)
            result.files_scanned += 1
            result.total_lines_scanned += len(lines)

            file_had_match = False
            for idx, line in enumerate(lines):
                pair = split_xuat_line(line)
                if not pair:
                    continue
                k_part, v_part = pair
                nk = norm_search(k_part)
                if nk in target_map:
                    file_had_match = True
                    matches_by_key.setdefault(nk, []).append(
                        BatchMatchRecord(
                            file_path=tf,
                            line_index=idx,
                            raw_key=k_part,
                            old_value=v_part,
                            norm_key=nk,
                        )
                    )

            if file_had_match:
                matched_snapshots[tf_norm] = FileSnapshot(
                    decoded_text=text,
                    encoding=decoded.encoding,
                    has_bom=decoded.has_bom,
                    newline=decoded.newline,
                    mtime_ns=st.st_mtime_ns,
                    size=st.st_size,
                    ino=getattr(st, "st_ino", 0),
                    dev=getattr(st, "st_dev", 0),
                )
                canonical_paths[tf_norm] = tf

        for root in validated_roots:
            root_p = Path(root)
            if not root_p.exists():
                continue
            if root_p.is_file():
                # Direct .txt root inside Translation\en\Text (os.walk yields nothing for file paths)
                _scan_file(root_p)
                continue
            for dirpath, _dirnames, filenames in os.walk(root_p):
                dp = Path(dirpath)
                for fname in filenames:
                    if fname.lower().endswith(".txt"):
                        _scan_file(dp / fname)

        # Any target with zero matches in the tree is unmatched
        for nk, group_targets in target_map.items():
            if nk not in matches_by_key:
                for t in group_targets:
                    result.unmatched_tokens.add(t.target_token)

        active_keys: Set[str] = set(matches_by_key.keys())
        if not active_keys:
            result.elapsed_seconds = time.perf_counter() - t0
            return result

        # Stage 3: Conflict detection (C3 Same-JP/Diff-EN -> C1 batched -> C2/C4)
        # Pass 3a: C3 (Same-JP / Different-EN in same save batch — explicit skip, no prompt)
        for nk in list(active_keys):
            group_targets = target_map[nk]
            escaped_vals = {escape_xuat_value(t.new_english) for t in group_targets}
            if len(escaped_vals) > 1:
                result.c3_conflict_keys.append(group_targets[0].jp_key)
                for t in group_targets:
                    result.conflict_skipped_tokens.add(t.target_token)
                active_keys.discard(nk)

        # Pass 3b: Collect ALL remaining C1 differing old_value groups across the batch
        c1_conflicts: List[BatchConflictItem] = []
        for nk in sorted(active_keys):
            key_matches = matches_by_key[nk]
            old_vals = list(dict.fromkeys(m.old_value for m in key_matches))
            if len(old_vals) > 1:
                rep = target_map[nk][0]
                c1_conflicts.append(
                    BatchConflictItem(
                        norm_key=nk,
                        jp_key=rep.jp_key,
                        new_english=rep.new_english,
                        old_values=old_vals,
                        matched_files=sorted({m.file_path.name for m in key_matches}),
                    )
                )

        # Pass 3c: Single batched C1 conflict callback (at most ONCE per batch_sync call)
        if c1_conflicts:
            accepted = bool(conflict_callback(c1_conflicts)) if conflict_callback is not None else False
            if not accepted:
                for item in c1_conflicts:
                    result.c1_declined_keys.append(item.jp_key)
                    for t in target_map[item.norm_key]:
                        result.conflict_skipped_tokens.add(t.target_token)
                    active_keys.discard(item.norm_key)

        if not active_keys:
            result.elapsed_seconds = time.perf_counter() - t0
            return result

        # Group remaining active matches by file and map tokens <-> matched files
        matches_by_file: Dict[str, List[BatchMatchRecord]] = {}
        tokens_by_file: Dict[str, Set[str]] = {}
        files_by_token: Dict[str, Set[str]] = {}
        active_tokens: Set[str] = set()

        for nk in active_keys:
            group_targets = target_map[nk]
            toks = {t.target_token for t in group_targets}
            active_tokens.update(toks)
            for m in matches_by_key[nk]:
                tf_norm = _normcase_path(m.file_path)
                matches_by_file.setdefault(tf_norm, []).append(m)
                tokens_by_file.setdefault(tf_norm, set()).update(toks)
                for tok in toks:
                    files_by_token.setdefault(tok, set()).add(tf_norm)

        # Stage 4: Pre-write metadata freshness check (reduces scan-to-write stale-write window)
        for tf_norm in list(matches_by_file.keys()):
            snap = matched_snapshots[tf_norm]
            tf_path = canonical_paths[tf_norm]
            try:
                st_now = os.stat(tf_path)
                changed = (
                    st_now.st_mtime_ns != snap.mtime_ns
                    or st_now.st_size != snap.size
                    or getattr(st_now, "st_ino", 0) != snap.ino
                    or getattr(st_now, "st_dev", 0) != snap.dev
                )
            except Exception:
                changed = True

            if changed:
                result.freshness_aborted_files.append(tf_path.name)
                for tok in tokens_by_file.get(tf_norm, ()):
                    result.freshness_failed_tokens.add(tok)
                matches_by_file.pop(tf_norm, None)

        # Stage 5: Grouped per-file atomic write (1 backup + 1 write_atomic_encoded per file)
        bak_fn = backup_path_fn if backup_path_fn is not None else _default_backup_path
        written_files: Set[str] = set()

        for tf_norm, file_matches in matches_by_file.items():
            tf_path = canonical_paths[tf_norm]
            snap = matched_snapshots[tf_norm]
            newline = snap.newline or ("\r\n" if "\r\n" in snap.decoded_text else "\n")
            lines = snap.decoded_text.split(newline)

            for m in file_matches:
                # All targets in target_map[m.norm_key] agree on escaped new_english (Pass 3a C3 checked)
                escaped_val = escape_xuat_value(target_map[m.norm_key][0].new_english)
                lines[m.line_index] = f"{m.raw_key}={escaped_val}"

            updated_text = newline.join(lines)
            try:
                if backup:
                    target_backup_dir = Path(backup_dir) if backup_dir is not None else tf_path.parent
                    bak_path = bak_fn(tf_path, target_backup_dir, "bak")
                    shutil.copy2(tf_path, bak_path)
                write_atomic_encoded(
                    tf_path,
                    updated_text,
                    encoding=snap.encoding,
                    has_bom=snap.has_bom,
                    newline=snap.newline,
                )
                result.synced_files.add(tf_path.name)
                written_files.add(tf_norm)
            except Exception:
                result.io_failed_files.append(tf_path.name)
                for tok in tokens_by_file.get(tf_norm, ()):
                    result.io_failed_tokens.add(tok)

        # Cross-file success classification: succeeded ONLY if ALL matched files were written cleanly
        for tok in active_tokens:
            if tok in result.freshness_failed_tokens or tok in result.io_failed_tokens:
                continue
            req_files = files_by_token.get(tok, set())
            if req_files and req_files.issubset(written_files):
                result.succeeded_tokens.add(tok)
            else:
                result.io_failed_tokens.add(tok)

        result.elapsed_seconds = time.perf_counter() - t0
        return result
