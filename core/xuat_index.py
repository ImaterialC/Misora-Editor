#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.xuat_index — Unified background-safe in-memory XUAT dictionary indexer.

Scans strictly BepInEx\\Translation\\en\\Text (or explicit Text roots), excluding
.missing.txt, .report.txt, _SUMMARY.txt, and _warnings.txt.
Provides:
  - Symmetric backslash-parity-aware unescape_xuat_value()
  - NGUI-tag and {playername}/{0}-aware O(1) key normalization
  - Deterministic provenance (file_path, line_number) with zero XUAT file pruning
  - Separate dialogue vs speaker match analysis (GEM-R02)
  - Tk-free background indexing via queue.Queue (Rule 15)
"""
from __future__ import annotations

import os
import queue
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from .ngui_tags import strip_tags
from .story_ast import ALL_WS_RE, DASH_MAP, PLAYER_PLACEHOLDER_RE
from .text_encoding import read_text_file_strictly
from .xunity_sync import split_xuat_line

_EXCLUDED_FILE_TAILS: Tuple[str, ...] = (
    ".missing.txt",
    ".report.txt",
    "_summary.txt",
    "_warnings.txt",
)

_PARITY_NL_RE = re.compile(r"(\\+)n")
_PARITY_EQ_RE = re.compile(r"(\\+)=")
_NUMBERED_PH_RE = re.compile(r"\{(\d+)\}")
_PLAYER_SENTINEL = "\ue000PLAYER\ue000"


def _to_long_path(path: Path) -> Path:
    """Apply Windows long-path prefix when needed (Rule 23)."""
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return path
    abs_s = os.path.abspath(s)
    if len(abs_s) >= 240:
        if abs_s.startswith("\\\\"):
            return Path("\\\\?\\UNC\\" + abs_s[2:])
        return Path("\\\\?\\" + abs_s)
    return path


def _is_excluded_xuat_file(path: Path) -> bool:
    low = path.name.lower()
    if any(low.endswith(tail) for tail in _EXCLUDED_FILE_TAILS):
        return True
    if ".bak_" in low:
        return True
    return False


def unescape_xuat_value(val: str) -> str:
    """Unescape literal \\n -> real newline using backslash parity while preserving \\\\n."""
    if not val or "\\n" not in val:
        return val

    def _repl(m: re.Match) -> str:
        bs = m.group(1)
        if len(bs) % 2 == 1:
            return bs[:-1] + "\n"
        return m.group(0)

    return _PARITY_NL_RE.sub(_repl, val)


def unescape_xuat_key(key: str) -> str:
    """Unescape literal \\n and \\= in an XUAT dictionary key using backslash parity."""
    if not key:
        return key
    s = unescape_xuat_value(key)
    if "\\=" in s:
        s = _PARITY_EQ_RE.sub(
            lambda m: (m.group(1)[:-1] + "=") if len(m.group(1)) % 2 == 1 else m.group(0),
            s,
        )
    return s


def normalize_xuat_key(text: str, strip_ngui: bool = True) -> str:
    """Normalize an XUAT key or story text with NGUI-tag and {playername}/{0} awareness.

    Canonicalizes {playername}/{0} BEFORE calling strip_tags() so NGUI_TAG_RE never
    erases player placeholders.
    """
    if not text:
        return ""
    s = unescape_xuat_key(text)
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Protect placeholders before strip_tags() (which includes PLACEHOLDER_RE in NGUI_TAG_RE)
    s = PLAYER_PLACEHOLDER_RE.sub(_PLAYER_SENTINEL, s)
    s = _NUMBERED_PH_RE.sub(lambda m: f"\ue001{m.group(1)}\ue002", s)

    if strip_ngui:
        s = strip_tags(s)

    s = s.replace(_PLAYER_SENTINEL, "{playername}")
    s = re.sub(r"\ue001(\d+)\ue002", lambda m: f"{{{m.group(1)}}}", s)

    s = unicodedata.normalize("NFKC", s).translate(DASH_MAP)
    collapsed = re.sub(r"-{2,}", "-", ALL_WS_RE.sub("", s))
    return collapsed.casefold()


def resolve_xuat_text_roots(roots: Iterable[Union[str, Path]]) -> List[Path]:
    """Resolve candidate project/folder paths strictly to BepInEx\\Translation\\en\\Text roots."""
    resolved: List[Path] = []
    seen: Set[str] = set()

    def _add(p: Path) -> None:
        try:
            key = os.path.normcase(os.path.normpath(str(p.resolve())))
        except Exception:
            key = os.path.normcase(os.path.normpath(str(p)))
        if key not in seen:
            seen.add(key)
            resolved.append(p)

    for item in roots:
        if not item:
            continue
        p = Path(item)
        lp = _to_long_path(p)
        if not lp.exists():
            continue
        if lp.is_file():
            if p.suffix.lower() == ".txt" and not _is_excluded_xuat_file(p):
                _add(p)
            continue

        # Prefer strict BepInEx\Translation\en\Text hierarchy
        candidates = [
            p / "BepInEx" / "Translation" / "en" / "Text",
            p / "Translation" / "en" / "Text",
            p / "en" / "Text",
            p / "Text",
        ]
        matched_sub = False
        for c in candidates:
            if _to_long_path(c).is_dir():
                _add(c)
                matched_sub = True
                break
        if matched_sub:
            continue

        # Accept explicit Text directory directly, but never plugins/config/RedirectedResources
        low_name = p.name.lower()
        if low_name == "text":
            _add(p)

    return resolved


@dataclass(frozen=True)
class XuatEntry:
    """Single parsed XUAT dictionary entry with file:line provenance."""
    file_path: Path
    rel_path: str
    line_number: int
    raw_key: str
    raw_value: str
    value: str

    @property
    def provenance(self) -> str:
        return f"{self.file_path.name}:{self.line_number}"


@dataclass(frozen=True)
class XuatLookupResult:
    """Typed lookup result (avoids ambiguous 3-tuple unpacking - GEM-R04)."""
    status: str  # "missing", "matched", "duplicate"
    candidates: List[XuatEntry] = field(default_factory=list)
    match_tier: str = "none"  # "none", "exact", "norm_exact", "norm_stripped"


class XuatIndex:
    """In-memory O(1) normalized XUAT dictionary index."""

    def __init__(
        self,
        roots: Optional[Sequence[Path]] = None,
    ) -> None:
        self.roots: List[Path] = list(roots or [])
        self.files_indexed: List[Path] = []
        self.skipped_files: List[Tuple[Path, str]] = []
        self.entry_count: int = 0
        self._exact_map: Dict[str, List[XuatEntry]] = {}
        self._norm_exact_map: Dict[str, List[XuatEntry]] = {}
        self._norm_stripped_map: Dict[str, List[XuatEntry]] = {}

    def add_entry(self, entry: XuatEntry) -> None:
        k_exact = unescape_xuat_key(entry.raw_key)
        k_norm_exact = normalize_xuat_key(entry.raw_key, strip_ngui=False)
        k_norm_stripped = normalize_xuat_key(entry.raw_key, strip_ngui=True)

        self._exact_map.setdefault(k_exact, []).append(entry)
        if k_norm_exact:
            self._norm_exact_map.setdefault(k_norm_exact, []).append(entry)
        if k_norm_stripped:
            self._norm_stripped_map.setdefault(k_norm_stripped, []).append(entry)
        self.entry_count += 1

    @staticmethod
    def _dedup_candidates(entries: Sequence[XuatEntry]) -> List[XuatEntry]:
        """Deduplicate entries with identical translated values while preserving deterministic order."""
        seen_vals: Set[str] = set()
        out: List[XuatEntry] = []
        for e in entries:
            if e.value not in seen_vals:
                seen_vals.add(e.value)
                out.append(e)
        return out

    def lookup_candidates(self, key_text: str) -> XuatLookupResult:
        """O(1) lookup returning typed XuatLookupResult with deterministic provenance."""
        if not key_text:
            return XuatLookupResult(status="missing", candidates=[], match_tier="none")

        k_exact = unescape_xuat_key(key_text)
        hits = self._exact_map.get(k_exact)
        tier = "exact"

        if not hits:
            k_norm_exact = normalize_xuat_key(key_text, strip_ngui=False)
            if k_norm_exact:
                hits = self._norm_exact_map.get(k_norm_exact)
                tier = "norm_exact"

        if not hits:
            k_norm_stripped = normalize_xuat_key(key_text, strip_ngui=True)
            if k_norm_stripped:
                hits = self._norm_stripped_map.get(k_norm_stripped)
                tier = "norm_stripped"

        if not hits:
            return XuatLookupResult(status="missing", candidates=[], match_tier="none")

        deduped = self._dedup_candidates(hits)
        status = "duplicate" if len(deduped) > 1 else "matched"
        return XuatLookupResult(status=status, candidates=deduped, match_tier=tier)

    def lookup_translation(self, key_text: str) -> Optional[str]:
        """Return first deterministic O(1) matched translation or None."""
        res = self.lookup_candidates(key_text)
        if not res.candidates:
            return None
        return res.candidates[0].value

    # Mapping-compatible helpers for seamless MTLEngine / xuat_cache unification (D11 / QW-E03)
    def __bool__(self) -> bool:
        return self.entry_count > 0

    def __len__(self) -> int:
        return self.entry_count

    def __contains__(self, key_text: object) -> bool:
        if not isinstance(key_text, str):
            return False
        return self.lookup_translation(key_text) is not None

    def __getitem__(self, key_text: str) -> str:
        val = self.lookup_translation(key_text)
        if val is None:
            raise KeyError(key_text)
        return val

    def get(self, key_text: str, default: Optional[str] = None) -> Optional[str]:
        val = self.lookup_translation(key_text)
        return val if val is not None else default


def build_xuat_index(
    roots: Iterable[Union[str, Path]],
    cancel_event: Optional[threading.Event] = None,
) -> XuatIndex:
    """Synchronously scan strict Text roots and build an in-memory XuatIndex."""
    strict_roots = resolve_xuat_text_roots(roots)
    idx = XuatIndex(roots=strict_roots)
    seen_files: Set[str] = set()

    for root in strict_roots:
        if cancel_event is not None and cancel_event.is_set():
            break
        lroot = _to_long_path(root)
        if lroot.is_file():
            txt_files = [root]
            base_root = root.parent
        else:
            txt_files = sorted(
                (p for p in lroot.rglob("*.txt") if not _is_excluded_xuat_file(p)),
                key=lambda p: str(p).casefold(),
            )
            base_root = root

        for tf in txt_files:
            if cancel_event is not None and cancel_event.is_set():
                break
            if _is_excluded_xuat_file(tf):
                continue
            try:
                fkey = os.path.normcase(os.path.normpath(str(tf.resolve())))
            except Exception:
                fkey = os.path.normcase(os.path.normpath(str(tf)))
            if fkey in seen_files:
                continue
            seen_files.add(fkey)

            try:
                decoded = read_text_file_strictly(_to_long_path(tf))
            except Exception as exc:
                idx.skipped_files.append((tf, str(exc)))
                continue

            try:
                rel_p = str(tf.relative_to(base_root))
            except Exception:
                rel_p = tf.name

            idx.files_indexed.append(tf)
            nl = decoded.newline or "\n"
            for line_no, raw_line in enumerate(decoded.text.split(nl), start=1):
                pair = split_xuat_line(raw_line)
                if not pair:
                    continue
                k_part, v_part = pair
                if not k_part.strip():
                    continue
                val_unescaped = unescape_xuat_value(v_part)
                idx.add_entry(
                    XuatEntry(
                        file_path=tf,
                        rel_path=rel_p,
                        line_number=line_no,
                        raw_key=k_part,
                        raw_value=v_part,
                        value=val_unescaped,
                    )
                )

    return idx


def build_xuat_index_async(
    roots: Iterable[Union[str, Path]],
    out_queue: queue.Queue,
    metadata: Optional[Any] = None,
    cancel_event: Optional[threading.Event] = None,
) -> threading.Thread:
    """Build XuatIndex in a background daemon thread (100% Tk-free - Rule 15)."""
    root_list = [Path(r) for r in roots if r]

    def worker() -> None:
        try:
            idx = build_xuat_index(root_list, cancel_event=cancel_event)
            out_queue.put(("xuat_index_ready", metadata, idx))
        except Exception as exc:
            out_queue.put(("xuat_index_error", metadata, str(exc)))

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def analyze_story_matches(
    doc: Any,
    orig_jp_map: Dict[int, str],
    xuat_index: XuatIndex,
) -> Dict[str, int]:
    """Compute separate dialogue and speaker XUAT match counts (GEM-R02)."""
    dialogue_total = 0
    dialogue_matched = 0
    dialogue_duplicates = 0
    dialogue_missing = 0
    speaker_total = 0
    speaker_matched = 0
    speaker_missing = 0

    if not doc or not getattr(doc, "boxes", None):
        return {
            "dialogue_total": 0,
            "dialogue_matched": 0,
            "dialogue_duplicates": 0,
            "dialogue_missing": 0,
            "speaker_total": 0,
            "speaker_matched": 0,
            "speaker_missing": 0,
        }

    for box in doc.boxes:
        dialogue_total += 1
        b_uid = box.segs[0].record.uid if getattr(box, "segs", None) and box.segs[0].record else getattr(box, "uid", None)
        jp_key = orig_jp_map.get(b_uid) if b_uid is not None else None
        if not jp_key:
            jp_key = box.clean_text
        res = xuat_index.lookup_candidates(jp_key)
        if res.status == "duplicate":
            dialogue_duplicates += 1
            dialogue_matched += 1
        elif res.status == "matched":
            dialogue_matched += 1
        else:
            dialogue_missing += 1

        if box.speaker:
            speaker_total += 1
            sp_res = xuat_index.lookup_candidates(box.speaker)
            if sp_res.candidates:
                speaker_matched += 1
            else:
                speaker_missing += 1

    return {
        "dialogue_total": dialogue_total,
        "dialogue_matched": dialogue_matched,
        "dialogue_duplicates": dialogue_duplicates,
        "dialogue_missing": dialogue_missing,
        "speaker_total": speaker_total,
        "speaker_matched": speaker_matched,
        "speaker_missing": speaker_missing,
    }
