#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.word_wrap — Pure-Python Lossless NGUI & Grapheme-Aware Auto Word Wrap.

Zero Tkinter imports (U07). Uses core.ngui_tags as the single source of truth
for NGUI tags, ruby annotations, and placeholders (AGENTS.md Rule 19).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .ngui_tags import NGUI_TOKEN_RE, PLACEHOLDER_RE, RUBY_RE

# Gyoto kinsoku: avoid starting a new line with closing/trailing punctuation
GYOTO_KINSOKU = frozenset(
    "。、！？）」』】〉》〕］｝・…ー～〜.,!?;:)]}"
    "っゃゅょぁぃぅぇぉッャュョァィゥェォ"
)

# Gyomatsu kinsoku: avoid ending a line with opening brackets
GYOMATSU_KINSOKU = frozenset("（「『【〈《〔［｛([{")

_PLACEHOLDER_PROXY = "PlayerName"


@dataclass(frozen=True)
class WrapResult:
    """Result summary returned by wrap_text()."""

    wrapped_text: str
    original_lines: int
    new_lines: int
    still_overflows_lines: bool
    still_overflows_width: bool
    changed: bool


@dataclass(frozen=True)
class _Token:
    raw: str
    measured: str
    kind: str  # "space", "cjk", "latin", "open_tag", "close_tag", "ruby", "placeholder"


def _is_extending_codepoint(ch: str, cp: int) -> bool:
    """Return True if codepoint attaches to the preceding base character in a grapheme cluster."""
    if unicodedata.category(ch) in ("Mn", "Mc", "Me"):
        return True
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
        return True
    if 0x1F3FB <= cp <= 0x1F3FF:
        return True
    return False


def iter_graphemes(text: str) -> List[str]:
    """Split text into Unicode grapheme clusters without breaking combining marks, variation selectors, or ZWJ."""
    if not text:
        return []
    clusters: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        cluster = [text[i]]
        i += 1
        while i < n:
            ch = text[i]
            cp = ord(ch)
            if ch == "\u200D":
                cluster.append(ch)
                i += 1
                if i < n:
                    cluster.append(text[i])
                    i += 1
                continue
            if _is_extending_codepoint(ch, cp):
                cluster.append(ch)
                i += 1
                continue
            break
        clusters.append("".join(cluster))
    return clusters


def _is_cjk_char(ch: str) -> bool:
    """Return True if ch is a CJK/fullwidth/Japanese character permitting character-level wrapping."""
    cp = ord(ch)
    return (
        (0x3000 <= cp <= 0x30FF)  # CJK symbols/punct, Hiragana, Katakana
        or (0x31F0 <= cp <= 0x31FF)
        or (0x3400 <= cp <= 0x4DBF)
        or (0x4E00 <= cp <= 0x9FFF)
        or (0xF900 <= cp <= 0xFAFF)
        or (0xFF01 <= cp <= 0xFFEF)  # Fullwidth & halfwidth katakana/punct
        or ch in ("…", "―", "—", "・", "～", "〜")
    )


def _classify_ngui_token(tok: str) -> _Token:
    """Classify a matched NGUI_TOKEN_RE token as ruby, placeholder, open_tag, or close_tag."""
    ruby_m = RUBY_RE.fullmatch(tok)
    if ruby_m:
        return _Token(raw=tok, measured=ruby_m.group(2), kind="ruby")
    if PLACEHOLDER_RE.fullmatch(tok):
        return _Token(raw=tok, measured=_PLACEHOLDER_PROXY, kind="placeholder")
    low = tok.lower()
    if low in ("[-]", "[/]") or low.startswith("[/") or low.startswith("</"):
        return _Token(raw=tok, measured="", kind="close_tag")
    return _Token(raw=tok, measured="", kind="open_tag")


def _tokenize_line(line: str) -> List[_Token]:
    """Tokenize a single logical line into atomic NGUI tags, placeholders, spaces, and grapheme clusters."""
    tokens: List[_Token] = []
    pos = 0
    for m in NGUI_TOKEN_RE.finditer(line):
        if m.start() > pos:
            for g in iter_graphemes(line[pos:m.start()]):
                if g == " ":
                    tokens.append(_Token(raw=g, measured=g, kind="space"))
                elif _is_cjk_char(g[0]):
                    tokens.append(_Token(raw=g, measured=g, kind="cjk"))
                else:
                    tokens.append(_Token(raw=g, measured=g, kind="latin"))
        tokens.append(_classify_ngui_token(m.group(0)))
        pos = m.end()
    if pos < len(line):
        for g in iter_graphemes(line[pos:]):
            if g == " ":
                tokens.append(_Token(raw=g, measured=g, kind="space"))
            elif _is_cjk_char(g[0]):
                tokens.append(_Token(raw=g, measured=g, kind="cjk"))
            else:
                tokens.append(_Token(raw=g, measured=g, kind="latin"))
    return tokens


def _prev_visible_idx(tokens: List[_Token], idx: int, start: int) -> Optional[int]:
    """Find nearest non-tag token index strictly before idx (>= start)."""
    k = idx - 1
    while k >= start:
        if tokens[k].kind not in ("open_tag", "close_tag"):
            return k
        k -= 1
    return None


def _next_visible_idx(tokens: List[_Token], idx: int) -> Optional[int]:
    """Find nearest non-tag token index at or after idx."""
    k = idx
    n = len(tokens)
    while k < n:
        if tokens[k].kind not in ("open_tag", "close_tag"):
            return k
        k += 1
    return None


def _has_only_leading_spaces_or_tags(tokens: List[_Token], start: int, idx: int) -> bool:
    """Return True if tokens[start:idx] contains no non-space visible content."""
    for k in range(start, idx):
        if tokens[k].kind not in ("space", "open_tag", "close_tag"):
            return False
    return True


def _is_tag_boundary_safe(tokens: List[_Token], idx: int) -> bool:
    """Never orphan zero-width opening tags at line end or closing tags at line start."""
    if idx <= 0 or idx >= len(tokens):
        return False
    if tokens[idx - 1].kind == "open_tag":
        return False
    if tokens[idx].kind == "close_tag":
        return False
    return True


def _collect_break_candidates(
    tokens: List[_Token], start: int
) -> Tuple[List[Tuple[int, bool]], List[Tuple[int, bool]]]:
    """
    Collect (break_idx, consume_space) candidates from start to len(tokens).

    Returns:
      primary: word-space and kinsoku-compliant CJK break points.
      fallback: tag-safe grapheme/token break points for single oversized tokens.
    """
    n = len(tokens)
    primary: List[Tuple[int, bool]] = []
    fallback: List[Tuple[int, bool]] = []

    for idx in range(start + 1, n):
        if not _is_tag_boundary_safe(tokens, idx):
            continue

        # Space break: break AT space token idx (replacing that single space with '\n')
        if tokens[idx].kind == "space":
            if not _has_only_leading_spaces_or_tags(tokens, start, idx):
                primary.append((idx, True))
                fallback.append((idx, True))
            continue

        # Right after a space token (e.g. second+ space in a multi-space run or leading indent)
        if tokens[idx - 1].kind == "space":
            continue

        if _has_only_leading_spaces_or_tags(tokens, start, idx):
            continue

        fallback.append((idx, False))

        p_vis = _prev_visible_idx(tokens, idx, start)
        n_vis = _next_visible_idx(tokens, idx)
        if p_vis is None or n_vis is None:
            continue

        p_tok = tokens[p_vis]
        n_tok = tokens[n_vis]

        if p_tok.kind == "cjk" or n_tok.kind == "cjk":
            if n_tok.raw in GYOTO_KINSOKU:
                continue
            if p_tok.raw in GYOMATSU_KINSOKU:
                continue
            primary.append((idx, False))

    return primary, fallback


def _wrap_single_line(
    line: str,
    measure_fn: Callable[[str], int],
    safe_width: int,
) -> Tuple[List[str], bool]:
    """Wrap one logical line cleanly to safe_width. Returns (output_lines, any_line_still_wide)."""
    if not line:
        return [""], False

    tokens = _tokenize_line(line)
    if not tokens:
        return [line], False

    safe_w = max(1, int(safe_width))
    full_measured = "".join(t.measured for t in tokens)
    if measure_fn(full_measured) <= safe_w:
        return [line], False

    out_lines: List[str] = []
    any_still_wide = False
    n = len(tokens)
    start = 0

    while start < n:
        rem_measured = "".join(tokens[k].measured for k in range(start, n))
        if measure_fn(rem_measured) <= safe_w:
            out_lines.append("".join(tokens[k].raw for k in range(start, n)))
            break

        # Binary search rightmost prefix tokens[start:hi_fit] with width <= safe_w
        lo, hi = start + 1, n
        hi_fit = start
        while lo <= hi:
            mid = (lo + hi) // 2
            w = measure_fn("".join(tokens[k].measured for k in range(start, mid)))
            if w <= safe_w:
                hi_fit = mid
                lo = mid + 1
            else:
                hi = mid - 1

        primary, fallback = _collect_break_candidates(tokens, start)

        chosen: Optional[Tuple[int, bool]] = None
        for brk_idx, consume_sp in reversed(primary):
            if brk_idx <= hi_fit:
                chosen = (brk_idx, consume_sp)
                break

        if chosen is None:
            for brk_idx, consume_sp in reversed(fallback):
                if brk_idx <= hi_fit:
                    chosen = (brk_idx, consume_sp)
                    break

        if chosen is None:
            # Even the smallest tag-safe unit exceeds safe_w: emit earliest safe break or remainder
            if primary and fallback:
                first_cand = primary[0] if primary[0][0] <= fallback[0][0] else fallback[0]
            elif primary:
                first_cand = primary[0]
            elif fallback:
                first_cand = fallback[0]
            else:
                first_cand = (n, False)
            chosen = first_cand
            any_still_wide = True

        brk_idx, consume_sp = chosen
        seg_text = "".join(tokens[k].raw for k in range(start, brk_idx))
        out_lines.append(seg_text)
        if not any_still_wide and brk_idx > hi_fit:
            any_still_wide = True
        start = brk_idx + (1 if consume_sp else 0)

    return out_lines, any_still_wide


def _join_paragraph_lines(lines: List[str]) -> str:
    """Join lines inside one paragraph cleanly (no space at CJK boundaries, single space otherwise)."""
    if not lines:
        return ""
    acc = lines[0]
    for nxt in lines[1:]:
        if not acc:
            acc = nxt
            continue
        if not nxt:
            continue
        prev_tokens = _tokenize_line(acc)
        nxt_tokens = _tokenize_line(nxt)
        p_vis = _prev_visible_idx(prev_tokens, len(prev_tokens), 0) if prev_tokens else None
        n_vis = _next_visible_idx(nxt_tokens, 0) if nxt_tokens else None
        need_space = True
        if acc.endswith(" ") or nxt.startswith(" "):
            need_space = False
        elif p_vis is not None and n_vis is not None:
            if prev_tokens[p_vis].kind == "cjk" or nxt_tokens[n_vis].kind == "cjk":
                need_space = False
        acc = f"{acc} {nxt}" if need_space else f"{acc}{nxt}"
    return acc


def wrap_text(
    text: str,
    measure_fn: Callable[[str], int],
    safe_width: int,
    *,
    reflow_existing_breaks: bool = False,
) -> WrapResult:
    """
    Losslessly wrap dialogue text to fit within safe_width without dropping characters,
    splitting Unicode grapheme clusters, or corrupting NGUI tags/placeholders.
    """
    if not text:
        return WrapResult(
            wrapped_text="",
            original_lines=1,
            new_lines=1,
            still_overflows_lines=False,
            still_overflows_width=False,
            changed=False,
        )

    raw_lines = text.split("\n")
    original_lines = len(raw_lines)

    if reflow_existing_breaks:
        paragraphs: List[List[str]] = []
        cur_para: List[str] = []
        for ln in raw_lines:
            if ln == "":
                if cur_para:
                    paragraphs.append(cur_para)
                    cur_para = []
                paragraphs.append([])
            else:
                cur_para.append(ln)
        if cur_para:
            paragraphs.append(cur_para)
        logical_lines = [(_join_paragraph_lines(p) if p else "") for p in paragraphs]
    else:
        logical_lines = raw_lines

    wrapped_lines: List[str] = []
    any_wide = False
    for ln in logical_lines:
        out_lns, line_wide = _wrap_single_line(ln, measure_fn, safe_width)
        wrapped_lines.extend(out_lns)
        if line_wide:
            any_wide = True

    wrapped_text = "\n".join(wrapped_lines)
    new_lines = len(wrapped_lines)
    return WrapResult(
        wrapped_text=wrapped_text,
        original_lines=original_lines,
        new_lines=new_lines,
        still_overflows_lines=(new_lines >= 4),
        still_overflows_width=any_wide,
        changed=(wrapped_text != text),
    )
