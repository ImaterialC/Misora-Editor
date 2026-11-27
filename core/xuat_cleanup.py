#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.xuat_cleanup — Pure-Python per-file transactional XUAT cleanup & archival engine (U01).

Zero Tkinter dependencies and zero imports from misora.py.
Provides:
  - SHA-256 stale source fingerprint verification (StaleSourceError)
  - Conservative, auditable 3-tier classification (applied / duplicate / already_translated_unique / uncertain)
  - Mandatory archive-first execution with two explicit encoding contracts:
      * per_source_file: raw byte-for-byte original encoding, BOM, and newline preservation (no mid-file BOM on append)
      * combined: canonical UTF-8 (no BOM) + LF with structured original encoding/bom/newline metadata headers
  - Atomic per-file transactions (.tmp -> strict reopen & verify -> os.replace)
  - Non-auto-deleting meaningfully-empty file detection and explicit confirmation-gated deletion
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from .story_ast import game_to_xuat
from .text_encoding import (
    BOM_UTF8,
    BOM_UTF16_BE,
    BOM_UTF16_LE,
    DecodedText,
    detect_encoding_and_decode,
    encode_with_metadata,
)
from .xuat_index import (
    XuatEntry,
    XuatIndex,
    _to_long_path,
    compute_file_sha256,
    normalize_xuat_key,
)
from .xunity_sync import split_xuat_line

DEFAULT_ARCHIVE_EXT = ".xuat.old"
VALID_ARCHIVE_STRATEGIES = ("combined", "per_source_file")
VALID_LINEBREAK_POLICIES = ("remove_line_break", "keep_blank_line")
VALID_DUPLICATE_SCOPES = ("selected_only", "all_duplicates")
MIN_UNIQUE_RIGHT_SIDE_CHARS = 6


class StaleSourceError(RuntimeError):
    """Raised when one or more targeted XUAT source files changed on disk since import/preview."""

    def __init__(
        self,
        changed_files: List[Tuple[Path, str, Optional[str]]],
        message: str = "",
    ) -> None:
        self.changed_files = changed_files
        if not message:
            names = ", ".join(p.name for p, _, _ in changed_files)
            message = (
                f"XUAT source file(s) changed on disk since import/preview: {names}. "
                "Refresh preview before cleaning."
            )
        super().__init__(message)


class ArchiveTargetError(ValueError):
    """Raised when an archive destination is invalid or collides with a source file."""


@dataclass(frozen=True)
class AppliedXuatRecord:
    """Exact (file_path, line_number) entry confirmed applied during Import from XUAT."""
    file_path: Path
    line_number: int
    raw_key: str
    value: str
    box_index: int = -1


@dataclass
class CleanupCandidate:
    """Single classified XUAT dictionary line candidate for cleanup/archival."""
    file_path: Path
    rel_path: str
    line_number: int
    raw_key: str
    raw_value: str
    value: str
    tier: str  # "applied", "duplicate", "already_translated_unique", "uncertain"
    selected: bool
    reason: str
    norm_key: str = ""
    matched_box_indices: Tuple[int, ...] = ()


@dataclass
class CleanupAnalysis:
    """Result of classifying XUAT entries against an active story / import run."""
    candidates: List[CleanupCandidate]
    source_fingerprints: Dict[Path, str]
    has_duplicates: bool
    counts_by_tier: Dict[str, int] = field(default_factory=dict)

    def selected_candidates(self) -> List[CleanupCandidate]:
        return [c for c in self.candidates if c.selected]


@dataclass(frozen=True)
class ArchiveTargetValidation:
    """Validation result for archive directory, extension, and target paths."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    resolved_targets: List[Path] = field(default_factory=list)


@dataclass(frozen=True)
class EmptyFileInfo:
    """Metadata for a modified XUAT file that contains no remaining meaningful entries."""
    file_path: Path
    safety_backup_path: Optional[Path]


@dataclass
class CleanupReport:
    """Granular per-file execution outcome for XUAT cleanup & archival."""
    operation_id: str
    archived_files: List[Path] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    rolled_back_files: List[Path] = field(default_factory=list)
    untouched_files: List[Path] = field(default_factory=list)
    safety_backups: Dict[Path, Optional[Path]] = field(default_factory=dict)
    empty_files: List[EmptyFileInfo] = field(default_factory=list)
    removed_count: int = 0
    errors: List[Tuple[Path, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unarchived: bool = False


def _norm_path_key(path: Union[str, Path]) -> str:
    p = Path(path)
    try:
        return os.path.normcase(os.path.normpath(str(p.resolve())))
    except Exception:
        return os.path.normcase(os.path.normpath(os.path.abspath(str(p))))


def _default_backup_path(source_path: Path, backup_dir: Path, tag: str = "xuat_cleanup") -> Path:
    """Pure-Python collision-resistant backup path generator."""
    src_p = Path(source_path)
    b_dir = Path(backup_dir)
    b_dir.mkdir(parents=True, exist_ok=True)
    norm_str = _norm_path_key(src_p)
    path_hash = hashlib.sha256(norm_str.encode("utf-8")).hexdigest()[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    candidate = b_dir / f"{src_p.stem}.{tag}_{ts}_{path_hash}{src_p.suffix}"
    counter = 1
    while candidate.exists():
        candidate = b_dir / f"{src_p.stem}.{tag}_{ts}_{path_hash}_{counter}{src_p.suffix}"
        counter += 1
    return candidate


def default_archive_dir(base_dir: Union[str, Path]) -> Path:
    """Return default XUAT archive folder outside BepInEx\\Translation\\en\\Text."""
    return Path(base_dir) / "backups" / "xuat_archive"


def _eol_label(nl: str) -> str:
    if nl == "\r\n":
        return "CRLF"
    if nl == "\r":
        return "CR"
    return "LF"


def _bom_prefix_for_encoding(encoding: str, has_bom: bool) -> bytes:
    if not has_bom:
        return b""
    norm_enc = encoding.lower().replace("_", "-")
    if norm_enc in ("utf-8", "utf-8-sig"):
        return BOM_UTF8
    if norm_enc == "utf-16-le":
        return BOM_UTF16_LE
    if norm_enc == "utf-16-be":
        return BOM_UTF16_BE
    return b""


def capture_source_fingerprints(paths: Iterable[Union[str, Path]]) -> Dict[Path, str]:
    """Capture SHA-256 hex digests for all existing source paths."""
    fps: Dict[Path, str] = {}
    seen: Set[str] = set()
    for raw_p in paths:
        if not raw_p:
            continue
        p = Path(raw_p)
        key = _norm_path_key(p)
        if key in seen:
            continue
        seen.add(key)
        if _to_long_path(p).is_file():
            fps[p] = compute_file_sha256(p)
    return fps


def verify_source_fingerprints(
    target_files: Iterable[Path],
    expected_fingerprints: Dict[Path, str],
) -> None:
    """Verify every targeted XUAT file still matches its captured SHA-256 fingerprint."""
    norm_expected: Dict[str, str] = {
        _norm_path_key(p): digest for p, digest in (expected_fingerprints or {}).items()
    }
    changed: List[Tuple[Path, str, Optional[str]]] = []
    seen: Set[str] = set()
    for p in target_files:
        key = _norm_path_key(p)
        if key in seen:
            continue
        seen.add(key)
        expected = norm_expected.get(key)
        if expected is None:
            changed.append((p, "<missing-fingerprint>", None))
            continue
        lp = _to_long_path(p)
        if not lp.is_file():
            changed.append((p, expected, None))
            continue
        actual = compute_file_sha256(p)
        if actual != expected:
            changed.append((p, expected, actual))
    if changed:
        raise StaleSourceError(changed)


def _normalize_ext(ext: str) -> str:
    cleaned = (ext or "").strip()
    if not cleaned:
        return DEFAULT_ARCHIVE_EXT
    if not cleaned.startswith("."):
        cleaned = "." + cleaned
    return cleaned


def _resolve_per_file_archive_targets(
    archive_dir: Path,
    archive_ext: str,
    source_paths: Sequence[Path],
) -> Dict[Path, Path]:
    """Resolve <archive_dir>/<source_stem><ext> per source file, disambiguating only stem collisions."""
    ext = _normalize_ext(archive_ext)
    stem_groups: Dict[str, List[Path]] = {}
    unique_sources: List[Path] = []
    seen: Set[str] = set()
    for sp in source_paths:
        k = _norm_path_key(sp)
        if k not in seen:
            seen.add(k)
            unique_sources.append(sp)
            stem_groups.setdefault(sp.stem.lower(), []).append(sp)

    mapping: Dict[Path, Path] = {}
    for sp in unique_sources:
        group = stem_groups[sp.stem.lower()]
        if len(group) == 1:
            mapping[sp] = archive_dir / f"{sp.stem}{ext}"
        else:
            short_hash = hashlib.sha256(_norm_path_key(sp).encode("utf-8")).hexdigest()[:6]
            mapping[sp] = archive_dir / f"{sp.stem}_{short_hash}{ext}"
    return mapping


def _is_path_inside(candidate: Path, parent: Path) -> bool:
    c_key = _norm_path_key(candidate)
    p_key = _norm_path_key(parent)
    if c_key == p_key:
        return True
    p_prefix = p_key.rstrip("\\/") + os.sep
    return c_key.startswith(p_prefix)


def validate_archive_target(
    archive_dir: Union[str, Path],
    archive_ext: str,
    strategy: str,
    source_paths: Sequence[Union[str, Path]],
    xuat_roots: Optional[Sequence[Union[str, Path]]] = None,
) -> ArchiveTargetValidation:
    """Validate archive destination against source files and BepInEx\\Translation\\en\\Text roots."""
    errors: List[str] = []
    warnings: List[str] = []

    if strategy not in VALID_ARCHIVE_STRATEGIES:
        errors.append(f"Unsupported archive strategy: {strategy!r}")

    dir_str = str(archive_dir or "").strip()
    if not dir_str:
        errors.append("Archive directory must not be empty.")
        return ArchiveTargetValidation(is_valid=False, errors=errors, warnings=warnings)

    arch_dir = Path(dir_str)
    ext = _normalize_ext(archive_ext)
    src_list = [Path(p) for p in source_paths]
    src_keys = {_norm_path_key(p) for p in src_list}

    resolved_targets: List[Path] = []
    if strategy == "per_source_file":
        per_map = _resolve_per_file_archive_targets(arch_dir, ext, src_list)
        resolved_targets = list(per_map.values())
    else:
        resolved_targets = [arch_dir / f"xuat_removed_archive{ext}"]

    for tgt in resolved_targets:
        if _norm_path_key(tgt) in src_keys:
            errors.append(
                f"Archive target '{tgt}' resolves to an active XUAT source file; "
                "choose a different archive directory or extension."
            )

    if ext.lower() == ".txt":
        warnings.append(
            "Archive extension '.txt' can be re-scanned by XUnity.AutoTranslator! "
            "Use '.xuat.old' (recommended) so archived lines are not loaded back."
        )

    in_xuat_tree = False
    for root in xuat_roots or ():
        if _is_path_inside(arch_dir, Path(root)):
            in_xuat_tree = True
            break
    if not in_xuat_tree:
        parts_lower = [part.lower() for part in arch_dir.parts]
        for idx in range(len(parts_lower) - 3):
            if parts_lower[idx : idx + 4] == ["bepinex", "translation", "en", "text"]:
                in_xuat_tree = True
                break
        if not in_xuat_tree and len(parts_lower) >= 2 and parts_lower[-2:] == ["en", "text"]:
            in_xuat_tree = True

    if in_xuat_tree:
        warnings.append(
            "Archive folder is inside a BepInEx\\Translation\\en\\Text folder; "
            "move archives outside Text/ (e.g., backups/xuat_archive) to prevent XUAT scanning."
        )

    return ArchiveTargetValidation(
        is_valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        resolved_targets=resolved_targets,
    )


def is_xuat_file_meaningfully_empty(path_or_text: Union[str, Path]) -> bool:
    """Return True if an XUAT file contains no meaningful key=value entries.

    Blank lines, whitespace, comments (#, //, ;), and regex directives (r:, sr:)
    do NOT count as meaningful entries.
    """
    if isinstance(path_or_text, Path):
        raw_bytes = _to_long_path(path_or_text).read_bytes()
        decoded = detect_encoding_and_decode(raw_bytes)
        text = decoded.text
        nl = decoded.newline or "\n"
        lines = text.split(nl)
    else:
        lines = re.split(r"\r\n|\r|\n", str(path_or_text))

    for line in lines:
        pair = split_xuat_line(line)
        if pair and pair[0].strip():
            return False
    return True


def _non_space_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def apply_duplicate_scope(candidates: Sequence[CleanupCandidate], duplicate_scope: str) -> None:
    """Update selection state of 'duplicate' candidates according to duplicate_scope."""
    select_dups = (duplicate_scope == "all_duplicates")
    for cand in candidates:
        if cand.tier == "duplicate":
            cand.selected = select_dups


def _build_protected_actor_sets(
    xuat_index: XuatIndex,
    doc: Any,
    protected_actors: Iterable[str] = (),
) -> Tuple[Set[str], Set[str]]:
    """Build deterministic protected Actor normalized key & value sets BEFORE Pass 1 (U-11).

    Sources:
      1. Document box speakers (box.speaker & game_to_xuat(box.speaker)).
      2. Caller-provided actor names / immutable JP speaker keys (protected_actors).
      3. Forward XUAT index matches for known actor keys + conservative reverse fallback
         (xuat_index.lookup_by_value) so JP actor keys remain protected even after
         box.speaker was already translated in-session.
    """
    raw_actor_strings: Set[str] = set()
    if doc and getattr(doc, "boxes", None):
        for box in doc.boxes:
            sp = getattr(box, "speaker", "") or ""
            if sp:
                raw_actor_strings.add(sp)
                gx = game_to_xuat(sp)
                if gx:
                    raw_actor_strings.add(gx)
    for extra_sp in protected_actors or ():
        if extra_sp:
            s = str(extra_sp)
            raw_actor_strings.add(s)
            gx = game_to_xuat(s)
            if gx:
                raw_actor_strings.add(gx)

    protected_keys: Set[str] = set()
    protected_values: Set[str] = set()
    for s in raw_actor_strings:
        protected_values.add(s)
        nk = normalize_xuat_key(s, strip_ngui=True)
        if nk:
            protected_keys.add(nk)
        for cand in xuat_index.lookup_all_by_norm_key(s):
            if cand.value:
                protected_values.add(cand.value)
        for rev_entry in xuat_index.lookup_by_value(s):
            rev_nk = normalize_xuat_key(rev_entry.raw_key, strip_ngui=True)
            if rev_nk:
                protected_keys.add(rev_nk)

    return protected_keys, protected_values


def classify_cleanup_candidates(
    xuat_index: XuatIndex,
    doc: Any,
    applied_records: Sequence[AppliedXuatRecord] = (),
    duplicate_scope: str = "selected_only",
    protected_actors: Iterable[str] = (),
    cancel_event: Optional[threading.Event] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> CleanupAnalysis:
    """Classify XUAT dictionary entries conservatively into 3+1 auditable tiers.

    U-11: Global Actor/Speaker dictionary entries are COMPLETELY EXCLUDED (0 rows)
    across Pass 1 (Applied), Pass 2 (Duplicate), and Pass 3 (Right-Side Matching).

    Tiers:
      - applied: exact (file_path, line_number) confirmed applied in Import from XUAT.
      - duplicate: extra occurrences sharing exact normalize_xuat_key() (never substring).
      - already_translated_unique: asset dialogue / title / subtitle / summary text matches unescaped
        right-side value mapping to strictly 1 unique key across xuat_index AND >= 6 non-space chars.
      - uncertain: short (<6 non-space chars) or multi-key ambiguous; always default selected=False.
    """
    protected_actor_keys, protected_actor_values = _build_protected_actor_sets(
        xuat_index,
        doc,
        protected_actors=protected_actors,
    )

    def _is_protected_actor_entry(entry: XuatEntry, norm_key: str) -> bool:
        if norm_key and norm_key in protected_actor_keys:
            return True
        if entry.value in protected_actor_values:
            return True
        return False

    applied_loc_map: Dict[Tuple[str, int], AppliedXuatRecord] = {}
    applied_norm_keys: Set[str] = set()
    for rec in applied_records or ():
        rec_nk = normalize_xuat_key(rec.raw_key, strip_ngui=True)
        if (rec_nk and rec_nk in protected_actor_keys) or (rec.value in protected_actor_values):
            continue
        loc = (_norm_path_key(rec.file_path), int(rec.line_number))
        applied_loc_map[loc] = rec
        if rec_nk:
            applied_norm_keys.add(rec_nk)

    dialogue_val_to_boxes: Dict[str, List[int]] = {}
    meta_val_to_labels: Dict[str, List[str]] = {}
    if doc and getattr(doc, "boxes", None):
        for b_idx, box in enumerate(doc.boxes):
            for val in (getattr(box, "clean_text", ""), getattr(box, "text", "")):
                if val:
                    lst = dialogue_val_to_boxes.setdefault(val, [])
                    if b_idx not in lst:
                        lst.append(b_idx)
    if doc and callable(getattr(doc, "get_metadata", None)):
        try:
            meta = doc.get_metadata() or {}
        except Exception:
            meta = {}
        for field_key, field_lbl in (
            ("title", "Box #0 (Title)"),
            ("subtitle", "Box #0 (Subtitle)"),
            ("summary", "Box #0 (Synopsis)"),
        ):
            mval = meta.get(field_key, "") or ""
            if mval:
                lbls = meta_val_to_labels.setdefault(mval, [])
                if field_lbl not in lbls:
                    lbls.append(field_lbl)

    entries = getattr(xuat_index, "entries", ())
    total_steps = max(1, len(entries) * 3)
    processed_steps = 0

    def _tick(step_idx: int) -> bool:
        nonlocal processed_steps
        processed_steps += 1
        if cancel_event is not None and cancel_event.is_set():
            return True
        if progress_cb is not None and (step_idx == 0 or (processed_steps % 100 == 0)):
            try:
                progress_cb(processed_steps, total_steps)
            except Exception:
                pass
        return False

    candidates: List[CleanupCandidate] = []
    classified_locs: Set[Tuple[str, int]] = set()
    unique_primary_keys: Set[str] = set()

    # Pass 1: Applied entries (exact file_path + line_number)
    for i, entry in enumerate(entries):
        if _tick(i):
            break
        nk = normalize_xuat_key(entry.raw_key, strip_ngui=True)
        if _is_protected_actor_entry(entry, nk):
            continue
        loc = (_norm_path_key(entry.file_path), int(entry.line_number))
        if loc in applied_loc_map:
            rec = applied_loc_map[loc]
            box_tup = (rec.box_index,) if rec.box_index >= 0 else ()
            reason = f"Applied to Box #{rec.box_index + 1}" if rec.box_index >= 0 else "Confirmed applied in import"
            candidates.append(
                CleanupCandidate(
                    file_path=entry.file_path,
                    rel_path=entry.rel_path,
                    line_number=entry.line_number,
                    raw_key=entry.raw_key,
                    raw_value=entry.raw_value,
                    value=entry.value,
                    tier="applied",
                    selected=True,
                    reason=reason,
                    norm_key=nk,
                    matched_box_indices=box_tup,
                )
            )
            classified_locs.add(loc)

    # Pass 2: Duplicate key occurrences of applied keys (exact normalized key, no substring)
    dup_selected = (duplicate_scope == "all_duplicates")
    if cancel_event is None or not cancel_event.is_set():
        for i, entry in enumerate(entries):
            if _tick(i):
                break
            loc = (_norm_path_key(entry.file_path), int(entry.line_number))
            if loc in classified_locs:
                continue
            nk = normalize_xuat_key(entry.raw_key, strip_ngui=True)
            if _is_protected_actor_entry(entry, nk):
                continue
            if nk and nk in applied_norm_keys:
                candidates.append(
                    CleanupCandidate(
                        file_path=entry.file_path,
                        rel_path=entry.rel_path,
                        line_number=entry.line_number,
                        raw_key=entry.raw_key,
                        raw_value=entry.raw_value,
                        value=entry.value,
                        tier="duplicate",
                        selected=dup_selected,
                        reason="Duplicate key occurrence of applied entry",
                        norm_key=nk,
                    )
                )
                classified_locs.add(loc)

    # Pass 3: Conservative right-side matches (dialogue / title / subtitle / summary; zero speaker rows)
    if cancel_event is None or not cancel_event.is_set():
        for i, entry in enumerate(entries):
            if _tick(i):
                break
            loc = (_norm_path_key(entry.file_path), int(entry.line_number))
            if loc in classified_locs:
                continue
            nk = normalize_xuat_key(entry.raw_key, strip_ngui=True)
            if _is_protected_actor_entry(entry, nk):
                continue
            if nk and nk in unique_primary_keys:
                candidates.append(
                    CleanupCandidate(
                        file_path=entry.file_path,
                        rel_path=entry.rel_path,
                        line_number=entry.line_number,
                        raw_key=entry.raw_key,
                        raw_value=entry.raw_value,
                        value=entry.value,
                        tier="duplicate",
                        selected=dup_selected,
                        reason="Duplicate key occurrence of already-translated entry",
                        norm_key=nk,
                    )
                )
                classified_locs.add(loc)
                continue

            has_dlg = entry.value in dialogue_val_to_boxes
            has_meta = entry.value in meta_val_to_labels
            if has_dlg or has_meta:
                matched_boxes = tuple(dialogue_val_to_boxes.get(entry.value, ()))
                all_for_val = xuat_index.lookup_by_value(entry.value)
                unique_keys = {
                    normalize_xuat_key(e.raw_key, strip_ngui=True)
                    for e in all_for_val
                    if normalize_xuat_key(e.raw_key, strip_ngui=True)
                }
                ns_len = _non_space_len(entry.value)
                if len(unique_keys) == 1 and ns_len >= MIN_UNIQUE_RIGHT_SIDE_CHARS:
                    if nk:
                        unique_primary_keys.add(nk)
                    if matched_boxes:
                        box_label = ", ".join(f"#{b + 1}" for b in matched_boxes[:3])
                        if len(matched_boxes) > 3:
                            box_label += f" (+{len(matched_boxes) - 3})"
                        reason_txt = f"Unique right-side match in Box {box_label}"
                    else:
                        meta_lbls = meta_val_to_labels.get(entry.value, [])
                        reason_txt = f"Unique right-side match in {', '.join(meta_lbls)}"
                    candidates.append(
                        CleanupCandidate(
                            file_path=entry.file_path,
                            rel_path=entry.rel_path,
                            line_number=entry.line_number,
                            raw_key=entry.raw_key,
                            raw_value=entry.raw_value,
                            value=entry.value,
                            tier="already_translated_unique",
                            selected=True,
                            reason=reason_txt,
                            norm_key=nk,
                            matched_box_indices=matched_boxes,
                        )
                    )
                else:
                    reasons = []
                    if len(unique_keys) > 1:
                        reasons.append(f"mapped by {len(unique_keys)} keys")
                    if ns_len < MIN_UNIQUE_RIGHT_SIDE_CHARS:
                        reasons.append(f"short ({ns_len} < {MIN_UNIQUE_RIGHT_SIDE_CHARS} chars)")
                    candidates.append(
                        CleanupCandidate(
                            file_path=entry.file_path,
                            rel_path=entry.rel_path,
                            line_number=entry.line_number,
                            raw_key=entry.raw_key,
                            raw_value=entry.raw_value,
                            value=entry.value,
                            tier="uncertain",
                            selected=False,
                            reason=f"Uncertain ({'; '.join(reasons) or 'ambiguous'})",
                            norm_key=nk,
                            matched_box_indices=matched_boxes,
                        )
                    )
                classified_locs.add(loc)

    if progress_cb is not None and (cancel_event is None or not cancel_event.is_set()):
        try:
            progress_cb(total_steps, total_steps)
        except Exception:
            pass

    counts = {
        "applied": sum(1 for c in candidates if c.tier == "applied"),
        "duplicate": sum(1 for c in candidates if c.tier == "duplicate"),
        "already_translated_unique": sum(1 for c in candidates if c.tier == "already_translated_unique"),
        "uncertain": sum(1 for c in candidates if c.tier == "uncertain"),
    }
    fingerprints = dict(getattr(xuat_index, "file_fingerprints", {}) or {})
    if not fingerprints:
        fingerprints = capture_source_fingerprints(getattr(xuat_index, "files_indexed", ()))

    return CleanupAnalysis(
        candidates=candidates,
        source_fingerprints=fingerprints,
        has_duplicates=(counts["duplicate"] > 0),
        counts_by_tier=counts,
    )


def _atomic_write_verified_bytes(
    target_path: Path,
    data: bytes,
    verify_fn: Optional[Callable[[bytes], None]] = None,
) -> None:
    """Write raw bytes to same-directory .tmp, verify, then os.replace() with Windows retry."""
    lp_target = _to_long_path(target_path)
    lp_target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = lp_target.with_name(f"{lp_target.name}.{os.getpid()}_{time.time_ns()}.tmp")
    try:
        tmp_path.write_bytes(data)
        read_back = tmp_path.read_bytes()
        if read_back != data:
            raise IOError(f"Temp verification byte mismatch for {target_path}")
        if verify_fn is not None:
            verify_fn(read_back)

        last_err: Optional[Exception] = None
        for attempt in range(5):
            try:
                os.replace(tmp_path, lp_target)
                last_err = None
                break
            except (PermissionError, OSError) as exc:
                last_err = exc
                time.sleep(0.05 * (2 ** attempt))
        if last_err is not None:
            raise last_err
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def _build_archive_header(
    ts_str: str,
    op_id: str,
    source_label: str,
    decoded: DecodedText,
    story_name: str,
    reason: str,
) -> str:
    nl_label = _eol_label(decoded.newline or "\n")
    bom_label = "true" if decoded.has_bom else "false"
    story_lbl = story_name or "unknown"
    reason_lbl = reason or "xuat_cleanup"
    return (
        f"# [{ts_str}] op={op_id} | source={source_label} | "
        f"encoding={decoded.encoding} | bom={bom_label} | newline={nl_label} | "
        f"story={story_lbl} | reason={reason_lbl}"
    )


def _write_combined_archive(
    archive_path: Path,
    sections: Sequence[Tuple[Path, str, DecodedText, List[str]]],
    op_id: str,
    ts_str: str,
    story_name: str,
    reason: str,
) -> Path:
    """Write/append combined archive in canonical UTF-8 (no BOM) with LF newlines."""
    existing_text = ""
    lp_arch = _to_long_path(archive_path)
    if lp_arch.is_file() and lp_arch.stat().st_size > 0:
        existing_decoded = detect_encoding_and_decode(lp_arch.read_bytes())
        existing_text = existing_decoded.text.replace("\r\n", "\n").replace("\r", "\n")

    blocks: List[str] = []
    for _src_p, rel_lbl, dec, raw_lines in sections:
        hdr = _build_archive_header(ts_str, op_id, rel_lbl, dec, story_name, reason)
        blocks.append("\n".join([hdr] + list(raw_lines)) + "\n")

    addition = "\n".join(blocks)
    if existing_text:
        if not existing_text.endswith("\n"):
            existing_text += "\n"
        combined_text = existing_text + "\n" + addition
    else:
        combined_text = addition

    data = encode_with_metadata(combined_text, encoding="utf-8", has_bom=False, newline="\n")

    def _verify(raw: bytes) -> None:
        if raw.startswith(BOM_UTF8):
            raise ValueError("Combined archive must not emit UTF-8 BOM")
        if b"\r" in raw:
            raise ValueError("Combined archive must use LF newlines only")
        raw.decode("utf-8")

    _atomic_write_verified_bytes(archive_path, data, verify_fn=_verify)
    return archive_path


def _write_per_source_archive(
    archive_path: Path,
    rel_lbl: str,
    dec: DecodedText,
    raw_lines: Sequence[str],
    op_id: str,
    ts_str: str,
    story_name: str,
    reason: str,
) -> Path:
    """Write/append per-source archive preserving original encoding, BOM, and newline byte-for-byte."""
    src_nl = dec.newline or "\n"
    src_enc = dec.encoding or "utf-8"
    src_bom = bool(dec.has_bom)
    bom_bytes = _bom_prefix_for_encoding(src_enc, src_bom)

    hdr = _build_archive_header(ts_str, op_id, rel_lbl, dec, story_name, reason)
    block_text = src_nl.join([hdr] + list(raw_lines)) + src_nl

    lp_arch = _to_long_path(archive_path)
    if lp_arch.is_file() and lp_arch.stat().st_size > 0:
        existing_bytes = lp_arch.read_bytes()
        # Verify existing archive compatibility; never emit a duplicate BOM mid-file (Guardrail 3)
        existing_dec = detect_encoding_and_decode(existing_bytes)
        if (
            existing_dec.encoding.lower().replace("_", "-") != src_enc.lower().replace("_", "-")
            or bool(existing_dec.has_bom) != src_bom
        ):
            raise ArchiveTargetError(
                f"Existing per-file archive '{archive_path}' encoding ({existing_dec.encoding}, bom={existing_dec.has_bom}) "
                f"does not match source ({src_enc}, bom={src_bom})."
            )
        nl_bytes = src_nl.encode(src_enc)
        sep_bytes = b""
        if not existing_bytes.endswith(nl_bytes):
            # Also check generic LF/CR byte endings in source encoding
            if not (existing_bytes.endswith(b"\n") or existing_bytes.endswith(b"\r")):
                sep_bytes = nl_bytes
        chunk_bytes = encode_with_metadata(block_text, encoding=src_enc, has_bom=False, newline=src_nl)
        data = existing_bytes + sep_bytes + chunk_bytes
    else:
        data = encode_with_metadata(block_text, encoding=src_enc, has_bom=src_bom, newline=src_nl)

    def _verify(raw: bytes) -> None:
        check_dec = detect_encoding_and_decode(raw)
        if check_dec.encoding.lower().replace("_", "-") != src_enc.lower().replace("_", "-"):
            raise ValueError(f"Archive encoding mismatch: expected {src_enc}, got {check_dec.encoding}")
        if bool(check_dec.has_bom) != src_bom:
            raise ValueError(f"Archive BOM mismatch: expected {src_bom}, got {check_dec.has_bom}")
        if bom_bytes and raw.count(bom_bytes) > 1 and src_enc.lower().replace("_", "-") == "utf-8":
            raise ValueError("Duplicate UTF-8 BOM detected inside per-file archive")
        if bom_bytes and raw.startswith(bom_bytes) and src_enc.lower().startswith("utf-16"):
            # Ensure no UTF-16 BOM U+FEFF inside decoded text body
            if "\ufeff" in check_dec.text:
                raise ValueError("Duplicate UTF-16 BOM detected inside per-file archive")

    _atomic_write_verified_bytes(archive_path, data, verify_fn=_verify)
    return archive_path


def execute_cleanup(
    candidates: Sequence[CleanupCandidate],
    source_fingerprints: Dict[Path, str],
    archive_dir: Union[str, Path],
    archive_ext: str = DEFAULT_ARCHIVE_EXT,
    archive_strategy: str = "combined",
    linebreak_policy: str = "remove_line_break",
    safety_backup_enabled: bool = True,
    safety_backup_dir: Optional[Union[str, Path]] = None,
    backup_path_fn: Optional[Callable[[Path, Path, str], Path]] = None,
    allow_unarchived_deletion: bool = False,
    story_name: str = "",
    reason: str = "xuat_cleanup",
    xuat_roots: Optional[Sequence[Union[str, Path]]] = None,
    per_file_validator: Optional[Callable[[Path, str], None]] = None,
) -> CleanupReport:
    """Execute archive-first, per-file transactional XUAT cleanup.

    Order:
      1. Validate archive destination (unless allow_unarchived_deletion=True).
      2. Re-verify SHA-256 fingerprints of ALL targeted source files (raises StaleSourceError on mismatch).
      3. Strictly read & prepare per-file edits and extract exact raw physical lines for archival.
      4. Write & verify Archive Backup(s) FIRST before modifying any source file.
      5. Modify each source file transactionally (safety backup -> .tmp -> strict verify -> os.replace).
      6. Check modified files with is_xuat_file_meaningfully_empty() without auto-deleting.
    """
    if linebreak_policy not in VALID_LINEBREAK_POLICIES:
        raise ValueError(f"Invalid linebreak_policy: {linebreak_policy!r}")
    if archive_strategy not in VALID_ARCHIVE_STRATEGIES:
        raise ValueError(f"Invalid archive_strategy: {archive_strategy!r}")

    op_id = uuid.uuid4().hex[:10]
    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    selected = [c for c in candidates if c.selected]
    report = CleanupReport(operation_id=op_id, unarchived=bool(allow_unarchived_deletion))
    if not selected:
        return report

    # Group selected candidates deterministically by normalized source file
    grouped: Dict[str, Tuple[Path, List[CleanupCandidate]]] = {}
    ordered_keys: List[str] = []
    for c in selected:
        k = _norm_path_key(c.file_path)
        if k not in grouped:
            grouped[k] = (c.file_path, [])
            ordered_keys.append(k)
        grouped[k][1].append(c)

    target_files = [grouped[k][0] for k in ordered_keys]

    # Step 1: Archive target validation (unless explicitly unarchived)
    arch_dir_path = Path(archive_dir)
    if not allow_unarchived_deletion:
        validation = validate_archive_target(
            arch_dir_path,
            archive_ext,
            archive_strategy,
            target_files,
            xuat_roots=xuat_roots,
        )
        report.warnings.extend(validation.warnings)
        if not validation.is_valid:
            raise ArchiveTargetError("; ".join(validation.errors))

    # Step 2: Re-verify SHA-256 fingerprints of ALL targeted source files BEFORE any disk write
    verify_source_fingerprints(target_files, source_fingerprints)

    # Step 3: Strictly read & prepare edits + extract exact raw physical lines (Guardrails 3 & 4)
    prepared: List[Tuple[Path, str, bytes, DecodedText, List[str], str, int]] = []
    for k in ordered_keys:
        src_path, file_cands = grouped[k]
        raw_bytes = _to_long_path(src_path).read_bytes()
        decoded = detect_encoding_and_decode(raw_bytes)
        nl = decoded.newline or "\n"
        had_trailing_nl = bool(decoded.text) and decoded.text.endswith(nl)
        raw_split = decoded.text.split(nl)
        content_lines = raw_split[:-1] if had_trailing_nl else raw_split
        if decoded.text == "":
            content_lines = []

        line_nums = sorted(
            {int(c.line_number) for c in file_cands if 1 <= int(c.line_number) <= len(content_lines)}
        )
        if not line_nums:
            report.untouched_files.append(src_path)
            continue

        archived_raw_lines = [content_lines[ln - 1] for ln in line_nums]
        remove_set = set(line_nums)

        if linebreak_policy == "keep_blank_line":
            new_lines = list(content_lines)
            for ln in sorted(remove_set, reverse=True):
                new_lines[ln - 1] = ""
        else:
            new_lines = [
                line for idx, line in enumerate(content_lines, start=1) if idx not in remove_set
            ]

        updated_text = (nl.join(new_lines) + (nl if had_trailing_nl else "")) if new_lines else ""
        rel_lbl = file_cands[0].rel_path or src_path.name
        prepared.append((src_path, rel_lbl, raw_bytes, decoded, archived_raw_lines, updated_text, len(line_nums)))

    if not prepared:
        return report

    # Step 4: Write & verify Archive Backup(s) FIRST (when mandatory archiving is active)
    if not allow_unarchived_deletion:
        if archive_strategy == "combined":
            comb_target = arch_dir_path / f"xuat_removed_archive{_normalize_ext(archive_ext)}"
            sections = [(sp, rel_lbl, dec, raw_lines) for sp, rel_lbl, _, dec, raw_lines, _, _ in prepared]
            _write_combined_archive(comb_target, sections, op_id, ts_str, story_name, reason)
            report.archived_files.append(comb_target)
        else:
            per_map = _resolve_per_file_archive_targets(
                arch_dir_path, _normalize_ext(archive_ext), [p[0] for p in prepared]
            )
            for sp, rel_lbl, _, dec, raw_lines, _, _ in prepared:
                tgt = per_map[sp]
                _write_per_source_archive(tgt, rel_lbl, dec, raw_lines, op_id, ts_str, story_name, reason)
                report.archived_files.append(tgt)

    # Step 5: Per-file transactional edit (safety backup -> .tmp -> strict verify -> os.replace)
    bak_gen = backup_path_fn or _default_backup_path
    resolved_safety_dir = (
        Path(safety_backup_dir)
        if safety_backup_dir is not None
        else arch_dir_path.parent / "xuat_safety_backups"
    )

    for idx, (src_path, _rel_lbl, orig_bytes, dec, _raw_lines, updated_text, removed_n) in enumerate(prepared):
        bak_path: Optional[Path] = None
        try:
            if safety_backup_enabled:
                bak_path = bak_gen(src_path, resolved_safety_dir, "xuat_cleanup")
                _to_long_path(bak_path).parent.mkdir(parents=True, exist_ok=True)
                _to_long_path(bak_path).write_bytes(orig_bytes)
            report.safety_backups[src_path] = bak_path

            encoded_bytes = encode_with_metadata(
                updated_text,
                encoding=dec.encoding,
                has_bom=dec.has_bom,
                newline=dec.newline,
            )

            def _verify_source_tmp(raw_tmp: bytes) -> None:
                check_dec = detect_encoding_and_decode(raw_tmp)
                if check_dec.encoding.lower().replace("_", "-") != dec.encoding.lower().replace("_", "-"):
                    raise ValueError(f"Encoding verification failed for {src_path.name}")
                if bool(check_dec.has_bom) != bool(dec.has_bom):
                    raise ValueError(f"BOM verification failed for {src_path.name}")
                if per_file_validator is not None:
                    per_file_validator(src_path, updated_text)

            _atomic_write_verified_bytes(src_path, encoded_bytes, verify_fn=_verify_source_tmp)
            report.modified_files.append(src_path)
            report.removed_count += removed_n
        except Exception as exc:
            # Ensure src_path is preserved intact with orig_bytes
            try:
                lp_src = _to_long_path(src_path)
                if not lp_src.exists() or lp_src.read_bytes() != orig_bytes:
                    _atomic_write_verified_bytes(src_path, orig_bytes)
            except Exception:
                pass
            report.rolled_back_files.append(src_path)
            report.errors.append((src_path, str(exc)))
            for rem_item in prepared[idx + 1 :]:
                report.untouched_files.append(rem_item[0])
            break

    # Step 6: Meaningfully-empty check on modified files ONLY (never auto-delete)
    for mod_path in report.modified_files:
        try:
            if is_xuat_file_meaningfully_empty(mod_path):
                report.empty_files.append(
                    EmptyFileInfo(
                        file_path=mod_path,
                        safety_backup_path=report.safety_backups.get(mod_path),
                    )
                )
        except Exception as exc:
            report.errors.append((mod_path, f"Empty check failed: {exc}"))

    return report


def delete_empty_xuat_files(
    file_paths: Iterable[Union[str, Path]],
) -> Tuple[List[Path], List[Tuple[Path, str]]]:
    """Delete ONLY user-confirmed empty XUAT files cleanly."""
    deleted: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    for raw_p in file_paths:
        p = Path(raw_p)
        try:
            lp = _to_long_path(p)
            if lp.is_file():
                lp.unlink()
            deleted.append(p)
        except Exception as exc:
            errors.append((p, str(exc)))
    return deleted, errors
