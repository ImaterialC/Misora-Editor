#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.script_codec - Cutscene Script Interchange Format (CSIF) Codec.

Pure module (zero Tkinter dependency) implementing serialization, parsing, format
sniffing, and AST document application for CSIF and legacy script formats.
Governed by AGENTS.md Rules 20 and 26.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.story_ast import (
    BoxSnapshot,
    PLAYER_PLACEHOLDER_RE,
    StoryDocument,
    game_to_xuat,
    xuat_to_game,
)

# -----------------------------------------------------------------------------
# Constants & Regexes
# -----------------------------------------------------------------------------
OUTER_FENCE_START_RE = re.compile(r"^\s*(?:```|~~~)[a-zA-Z0-9_-]*\s*$")
OUTER_FENCE_END_RE = re.compile(r"^\s*(?:```|~~~)\s*$")

HEADER_PREFIX = "@@"
ESCAPE_PREFIX = r"\@@"
CSIF_BODY_ESCAPE_RE = re.compile(r"^\\*@@")
CSIF_BODY_UNESCAPE_RE = re.compile(r"^\\+@@")

# CSIF header matching
SPARSE_HEADER_RE = re.compile(r"^@@#(\d+)\|(.*)$")
META_HEADER_RE = re.compile(r"^@@!(title|subtitle|summary)(?:[:\s]+(.*))?$", re.IGNORECASE)

# Legacy input adapters
LEGACY_BOX_RE = re.compile(
    r"(?:=== )?\[BOX:(\d+)(?:\|Speaker:([^\]]*))?\]\s*(?:===)?\s*\n(.*?)(?=\n(?:=== )?\[BOX:|\Z)",
    re.DOTALL
)


def sanitize_speaker(sp: str) -> str:
    """
    Sanitize speaker names:
    - Strip Cf (format, e.g. zero-width spaces) and Cc (control) characters.
    - Map NBSP (\\u00a0) and ideographic space (\\u3000) to regular spaces.
    - Strip leading and trailing whitespace.
    """
    if not sp:
        return ""
    # Map NBSP and ideographic space
    s = sp.replace("\u00a0", " ").replace("\u3000", " ")
    # Filter Cf (format) and Cc (control)
    cleaned = "".join(c for c in s if unicodedata.category(c) not in ("Cf", "Cc"))
    cleaned = cleaned.strip()
    if cleaned == "_":
        return ""
    return cleaned


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
@dataclass
class MetadataBlock:
    title: Optional[str] = None
    subtitle: Optional[str] = None
    summary: Optional[str] = None

    def is_empty(self) -> bool:
        return self.title is None and self.subtitle is None and self.summary is None


@dataclass
class DialogueBlock:
    speaker: str
    text: str
    is_narration: bool = False
    index: Optional[int] = None  # 1-based index for sparse addressing (@@#N|Speaker)
    raw_header: str = ""


@dataclass
class ParseResult:
    blocks: List[DialogueBlock] = field(default_factory=list)
    metadata: MetadataBlock = field(default_factory=MetadataBlock)
    is_sparse: bool = False
    format: str = "csif"
    warnings: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Format Sniffer
# -----------------------------------------------------------------------------
def sniff_format(text: str) -> str:
    """
    Detect whether text is CSIF, legacy box delimiters, triple-enter, paragraphs, or plain lines.
    """
    if not text:
        return "plain"

    # Normalize line breaks for inspection
    s = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()
    if not s:
        return "plain"

    # Strip outer markdown code fence for inspection if present
    lines = s.split("\n")
    if len(lines) >= 2 and OUTER_FENCE_START_RE.match(lines[0]) and OUTER_FENCE_END_RE.match(lines[-1]):
        lines = lines[1:-1]
        s = "\n".join(lines).strip()

    # Check for CSIF headers (lines starting with @@)
    for line in lines:
        lstrip = line.strip()
        if lstrip.startswith("@@"):
            return "csif"

    # Check for legacy [BOX: or === [BOX:
    if "[BOX:" in s:
        return "legacy_box"

    # Check for triple-enter
    if "\n\n\n" in s or re.search(r"\n\s*\n\s*\n+", s):
        return "triple_enter"

    # Check for double-enter paragraphs
    if "\n\n" in s or re.search(r"\n\s*\n", s):
        return "paragraphs"

    return "plain"


# -----------------------------------------------------------------------------
# CSIF Parser
# -----------------------------------------------------------------------------
def parse(text: str, format: Optional[str] = None) -> ParseResult:
    """
    Parse CSIF or legacy input formats into a normalized ParseResult.
    Accepts LF/CRLF/CR, strips BOM, strips outer Markdown code fence with a warning.
    Enforces CSIF grammar, rejects mixed/duplicate/invalid sparse addressing.
    """
    if format is None:
        format = sniff_format(text)

    result = ParseResult(format=format)
    if not text:
        return result

    # Normalize newlines and strip BOM
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")

    # Strip only outer Markdown code fence if present
    lines = normalized.split("\n")
    if len(lines) >= 2 and OUTER_FENCE_START_RE.match(lines[0]) and OUTER_FENCE_END_RE.match(lines[-1]):
        result.warnings.append("Outer Markdown code fence stripped.")
        lines = lines[1:-1]
        normalized = "\n".join(lines)

    # Strip exactly one trailing newline at EOF if present (the EOF delimiter)
    if normalized.endswith("\n"):
        normalized = normalized[:-1]

    lines = normalized.split("\n")

    if format == "csif":
        _parse_csif(lines, result)
    elif format == "legacy_box":
        _parse_legacy_box(normalized, result)
    elif format == "triple_enter":
        _parse_triple_enter(normalized, result)
    elif format == "paragraphs":
        _parse_paragraphs(normalized, result)
    else:
        _parse_plain(normalized, result)

    return result


def _parse_csif(lines: List[str], result: ParseResult) -> None:
    """Parse pure CSIF lines."""
    seen_dialogue = False
    seen_sparse_indices: Set[int] = set()
    has_sparse = False
    has_non_sparse = False

    current_meta_key: Optional[str] = None
    current_block: Optional[DialogueBlock] = None
    current_body_lines: List[str] = []

    def flush_current():
        nonlocal current_meta_key, current_block, current_body_lines
        body_text = "\n".join(current_body_lines)
        if current_meta_key:
            if current_meta_key == "title":
                result.metadata.title = body_text
            elif current_meta_key == "subtitle":
                result.metadata.subtitle = body_text
            elif current_meta_key == "summary":
                result.metadata.summary = body_text
            current_meta_key = None
        elif current_block:
            current_block.text = body_text
            result.blocks.append(current_block)
            current_block = None
        current_body_lines = []

    for line_idx, line in enumerate(lines):
        # Check if line is a header
        if line.startswith(HEADER_PREFIX):
            # Check for metadata header: @@!title, @@!subtitle, @@!summary
            m_meta = META_HEADER_RE.match(line)
            if m_meta:
                if seen_dialogue:
                    raise ValueError("Metadata headers (@@!) are only allowed before the first dialogue header.")
                flush_current()
                key = m_meta.group(1).lower()
                inline_val = m_meta.group(2)
                current_meta_key = key
                if inline_val is not None:
                    if CSIF_BODY_UNESCAPE_RE.match(inline_val):
                        current_body_lines.append(inline_val[1:])
                    else:
                        current_body_lines.append(inline_val)
                continue

            # It is a dialogue header
            seen_dialogue = True
            flush_current()

            # Check for sparse header: @@#N|Speaker
            m_sparse = SPARSE_HEADER_RE.match(line)
            if m_sparse:
                has_sparse = True
                idx_str = m_sparse.group(1)
                idx_num = int(idx_str)
                if idx_num < 1:
                    raise ValueError(f"Sparse index must be >= 1, got #{idx_num}")
                if idx_num in seen_sparse_indices:
                    raise ValueError(f"Duplicate sparse index: #{idx_num}")
                seen_sparse_indices.add(idx_num)

                raw_sp = m_sparse.group(2)
                is_narr = (raw_sp == "_" or not raw_sp)
                sp = "" if is_narr else sanitize_speaker(raw_sp)
                current_block = DialogueBlock(
                    speaker=sp,
                    text="",
                    is_narration=is_narr,
                    index=idx_num,
                    raw_header=line,
                )
            elif line.startswith("@@#"):
                # Malformed sparse header
                raise ValueError(f"Invalid sparse header: {line}")
            else:
                has_non_sparse = True
                # Standard header: @@Speaker or @@_ or @@
                raw_sp = line[2:]
                is_narr = (raw_sp == "_" or not raw_sp)
                sp = "" if is_narr else sanitize_speaker(raw_sp)
                current_block = DialogueBlock(
                    speaker=sp,
                    text="",
                    is_narration=is_narr,
                    index=None,
                    raw_header=line,
                )
        else:
            # Body line: check for escaped header \@@
            if CSIF_BODY_UNESCAPE_RE.match(line):
                unescaped = line[1:]  # Strip exactly ONE leading \
                current_body_lines.append(unescaped)
            else:
                current_body_lines.append(line)

    flush_current()

    # Validation: reject mixed sparse & non-sparse
    if has_sparse and has_non_sparse:
        raise ValueError("Mixed sparse and non-sparse addressing is forbidden (Rule 20).")

    result.is_sparse = has_sparse


def _parse_legacy_box(text: str, result: ParseResult) -> None:
    """Parse legacy === [BOX:n|Speaker:x] === format."""
    matches = list(LEGACY_BOX_RE.finditer(text))
    if not matches:
        _parse_plain(text, result)
        return

    for m in matches:
        idx = int(m.group(1)) + 1  # Convert 0-based to 1-based
        raw_sp = m.group(2) or ""
        body = m.group(3).rstrip("\n")
        is_narr = not bool(raw_sp.strip())
        sp = "" if is_narr else sanitize_speaker(raw_sp)
        result.blocks.append(
            DialogueBlock(
                speaker=sp,
                text=body,
                is_narration=is_narr,
                index=idx,
                raw_header=m.group(0).splitlines()[0],
            )
        )
    result.is_sparse = True


def _parse_triple_enter(text: str, result: ParseResult) -> None:
    """Parse legacy triple-enter blocks."""
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n\s*\n+", text) if b.strip()]
    for b in blocks:
        result.blocks.append(DialogueBlock(speaker="", text=b, is_narration=True))


def _parse_paragraphs(text: str, result: ParseResult) -> None:
    """Parse paragraphs separated by double enters."""
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n", text) if b.strip()]
    for b in blocks:
        result.blocks.append(DialogueBlock(speaker="", text=b, is_narration=True))


def _parse_plain(text: str, result: ParseResult) -> None:
    """Parse plain text line-by-line."""
    lines = [l for l in text.split("\n") if l.strip()]
    for l in lines:
        result.blocks.append(DialogueBlock(speaker="", text=l, is_narration=True))


# -----------------------------------------------------------------------------
# CSIF Serializer
# -----------------------------------------------------------------------------
def serialize(
    doc: StoryDocument,
    *,
    scope: str = "all",
    box_indices: Optional[List[int]] = None,
    include_metadata: Union[str, bool] = "auto",
) -> str:
    """
    Serialize a StoryDocument (or a slice of boxes) into canonical CSIF text.

    - Contiguous box range -> numberless '@@Speaker' or '@@_'
    - Non-contiguous selection -> sparse '@@#N|Speaker' (1-based N)
    - Metadata -> '@@!title', '@@!subtitle', '@@!summary'
    - Escapes body lines starting with '@@' as '\\@@'
    - Emits LF delimiters strictly
    """
    out_lines: List[str] = []

    # 1. Metadata serialization
    emit_meta = False
    if include_metadata is True:
        emit_meta = True
    elif include_metadata == "auto":
        # Include metadata only when exporting the whole document or when the
        # caller explicitly scopes to metadata.  A plain dialogue selection that
        # happens to include box index 0 (the first dialogue box, NOT Box 0 /
        # story metadata) must NOT bleed metadata into the clipboard.
        if scope in ("all", "metadata") and doc.has_metadata():
            emit_meta = True

    if emit_meta:
        meta = doc.get_metadata()
        if meta.get("title"):
            out_lines.append("@@!title")
            for l in meta["title"].splitlines():
                out_lines.append(f"\\{l}" if CSIF_BODY_ESCAPE_RE.match(l) else l)
        if meta.get("subtitle"):
            out_lines.append("@@!subtitle")
            for l in meta["subtitle"].splitlines():
                out_lines.append(f"\\{l}" if CSIF_BODY_ESCAPE_RE.match(l) else l)
        if meta.get("summary"):
            out_lines.append("@@!summary")
            for l in meta["summary"].splitlines():
                out_lines.append(f"\\{l}" if CSIF_BODY_ESCAPE_RE.match(l) else l)

    if scope == "metadata":
        return "\n".join(out_lines) + ("\n" if out_lines else "")

    # 2. Dialogue serialization
    total_boxes = len(doc.boxes)
    if box_indices is None:
        target_indices = list(range(total_boxes))
    else:
        target_indices = [i for i in box_indices if 0 <= i < total_boxes]

    if not target_indices:
        return "\n".join(out_lines) + ("\n" if out_lines else "")

    # Check if target_indices are contiguous
    sorted_targets = sorted(target_indices)
    is_contiguous = (
        len(sorted_targets) <= 1
        or (
            sorted_targets == list(range(min(sorted_targets), max(sorted_targets) + 1))
            and target_indices == sorted_targets
        )
    )

    for idx in target_indices:
        box = doc.boxes[idx]
        is_narration = (box.kind == "tag" or not box.speaker.strip())

        if is_narration:
            sp_name = "_"
        else:
            # Normalize player placeholder to {playername} in export
            sp_name = PLAYER_PLACEHOLDER_RE.sub("{playername}", box.speaker)
            sp_name = sanitize_speaker(sp_name)
            if not sp_name:
                sp_name = "_"

        if is_contiguous:
            header = f"@@{sp_name}"
        else:
            # Sparse 1-based index
            header = f"@@#{idx + 1}|{sp_name}"

        out_lines.append(header)

        # Body: escape lines starting with @@ as \@@
        clean_text = box.clean_text
        if clean_text:
            body_lines = clean_text.split("\n")
            for bl in body_lines:
                if CSIF_BODY_ESCAPE_RE.match(bl):
                    out_lines.append(f"\\{bl}")
                else:
                    out_lines.append(bl)
        else:
            out_lines.append("")

    return "\n".join(out_lines) + "\n"


# -----------------------------------------------------------------------------
# Document Application API
# -----------------------------------------------------------------------------
def apply_to_document(
    doc: StoryDocument,
    result: ParseResult,
    *,
    mode: str = "insert",
    start_box_index: int = 0,
    overflow: str = "create",
    apply_speakers: bool = True,
    apply_metadata: bool = True,
    locked_indices: Optional[Set[int]] = None,
) -> int:
    """
    Apply a ParseResult to a StoryDocument.

    - Sparse mode: writes directly to target 1-based box indices (rejects missing/out-of-range).
    - mode="insert": inserts new boxes starting at start_box_index.
    - mode="replace": overwrites boxes sequentially starting from start_box_index.
      If overflow="create", appends new boxes when exceeding document length.
    - Preserves metadata if present in result and apply_metadata is True.
    - Never falls back to positional addressing silently when sparse.
    - Atomic rollback: if any step raises, restores document state completely.
    """
    # Pre-validation for sparse mode before modifying anything
    if result.is_sparse:
        total_boxes = len(doc.boxes)
        for b in result.blocks:
            if b.index is None:
                raise ValueError("Encountered un-indexed block in sparse result.")
            if not (1 <= b.index <= total_boxes):
                raise IndexError(
                    f"Sparse index #{b.index} is out of range. Document has {total_boxes} boxes."
                )

    # Atomic rollback snapshot (covering both sparse and non-sparse failure paths)
    saved_records = copy.deepcopy(doc.records)
    saved_removed = set(doc.removed_records)

    try:
        # 1. Apply metadata if requested and present
        if apply_metadata and not result.metadata.is_empty():
            doc.set_metadata(
                title=result.metadata.title,
                subtitle=result.metadata.subtitle,
                summary=result.metadata.summary,
            )

        if not result.blocks:
            return 0

        applied_count = 0

        # 2. Sparse application
        if result.is_sparse:
            # Capture target UIDs:
            # b.index is 1-based, box_idx is 0-based
            targets = []
            for b in result.blocks:
                box_idx = b.index - 1
                box = doc.boxes[box_idx]
                uid = box.segs[0].record.uid if box.segs and box.segs[0].record else None
                targets.append((b, uid, box_idx))

            for b, uid, orig_idx in targets:
                # Resolve target box by UID
                curr_idx = None
                if uid is not None:
                    for idx, bx in enumerate(doc.boxes):
                        if bx.segs and bx.segs[0].record and bx.segs[0].record.uid == uid:
                            curr_idx = idx
                            break
                if curr_idx is None:
                    curr_idx = orig_idx

                if locked_indices and curr_idx in locked_indices:
                    continue

                old_box = doc.boxes[curr_idx]
                if apply_speakers:
                    sp = "" if b.is_narration else sanitize_speaker(b.speaker)
                else:
                    sp = old_box.speaker

                doc.inject_box(curr_idx, new_speaker=sp, new_text=b.text)
                applied_count += 1

            return applied_count

        # 3. Non-sparse application
        if mode == "insert":
            insert_pos = max(0, min(start_box_index, len(doc.boxes)))
            for b in result.blocks:
                sp = "" if b.is_narration else sanitize_speaker(b.speaker)
                kd = "tag" if b.is_narration or not sp else "print"
                snap = BoxSnapshot(
                    speaker=sp,
                    voice_cue="",
                    kind=kd,
                    seg_texts=[b.text],
                )
                doc.insert_box(insert_pos, snap)
                insert_pos += 1
                applied_count += 1
        elif mode == "replace":
            curr_idx = max(0, start_box_index)
            for b in result.blocks:
                if curr_idx < len(doc.boxes):
                    if locked_indices and curr_idx in locked_indices:
                        curr_idx += 1
                        continue
                    old_box = doc.boxes[curr_idx]
                    sp = ("" if b.is_narration else sanitize_speaker(b.speaker)) if apply_speakers else old_box.speaker
                    doc.inject_box(curr_idx, new_speaker=sp, new_text=b.text)
                    curr_idx += 1
                    applied_count += 1
                elif overflow == "create":
                    sp = "" if b.is_narration else sanitize_speaker(b.speaker)
                    kd = "tag" if b.is_narration or not sp else "print"
                    snap = BoxSnapshot(
                        speaker=sp,
                        voice_cue="",
                        kind=kd,
                        seg_texts=[b.text],
                    )
                    doc.insert_box(len(doc.boxes), snap)
                    curr_idx += 1
                    applied_count += 1
                else:
                    break
        else:
            raise ValueError(f"Unknown application mode: {mode}. Expected 'insert' or 'replace'.")

        return applied_count
    except Exception:
        doc.records = saved_records
        doc.removed_records = saved_removed
        doc._rebuild_boxes()
        raise
