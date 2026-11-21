#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.ngui_tags — Centralized Priconne NGUI tag definitions, masking, and validation.

Single source of truth for all NGUI rich-text patterns and placeholders (AGENTS.md Rule 19).
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


# -----------------------------------------------------------------------------
# Regular Expression Patterns (Single Source of Truth - Rule 19)
# -----------------------------------------------------------------------------

# Individual component patterns
RUBY_RE = re.compile(r"\[rub:([^\]]*)\](.*?)\[/rub\]", re.IGNORECASE | re.DOTALL)
SIZE_RE = re.compile(r"\[/?size(?:=[^\]]*)?\]|</?size(?:=[^>]*)?>", re.IGNORECASE)
STYLE_RE = re.compile(r"\[/?(?:b|i|u|s|sub|sup|c)\]|\[/\]|\[-\]", re.IGNORECASE)
COLOR_HEX_RE = re.compile(r"\[[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\]")
GRADIENT_RE = re.compile(
    r"\[([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)[-,]([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)\]"
)
PLACEHOLDER_RE = re.compile(r"\{playername\}|\{\d+\}", re.IGNORECASE)
URL_RE = re.compile(r"\[url=[^\]]*\]|\[/url\]", re.IGNORECASE)

# All NGUI tags and placeholders combined (matches any tag or placeholder token)
NGUI_TAG_RE = re.compile(
    r"(\[(?:/|/?(?:"
    r"rub(?::[^\]]*)?|"
    r"size(?:=[^\]]*)?|"
    r"b|i|u|s|sub|sup|c|"
    r"url(?:=[^\]]*)?|"
    r"-|"
    r"[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?(?:[-,][0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)?"
    r"))\]|"
    r"<(?:/|/?)size(?:=[^>]*)?>|"
    r"\{playername\}|\{\d+\})",
    re.IGNORECASE
)

# Tokenizer for UI preview rendering
NGUI_TOKEN_RE = re.compile(
    r"(\[rub:([^\]]*)\](.*?)\[/rub\]|"
    r"\[/?(?:b|i|u|s|sub|sup|c)\]|"
    r"\[/?size(?:=[^\]]*)?\]|"
    r"</?size(?:=[^>]*)?>|"
    r"\[/\]|"
    r"\[url=[^\]]*\]|\[/url\]|"
    r"\[-\]|"
    r"\[([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?(?:[-,]([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?)?\]|"
    r"\{playername\}|\{\d+\})",
    re.IGNORECASE | re.DOTALL,
)


# -----------------------------------------------------------------------------
# Tag Normalization & Render Measurement
# -----------------------------------------------------------------------------

def normalize_gradient_syntax(text: str) -> str:
    """
    Normalize comma gradient syntax [c0,c1] to canonical hyphen syntax [c0-c1] (Rule 19).
    Leaves valid hyphen gradients [c0-c1] untouched.
    """
    def repl(m: re.Match) -> str:
        return f"[{m.group(1)}-{m.group(2)}]"

    return GRADIENT_RE.sub(repl, text)


def strip_tags(text: str) -> str:
    """
    Remove all NGUI formatting tags, size tags, colors, ruby tags, and placeholders.
    For ruby tags [rub:ruby]base[/rub], preserves the base text and strips the annotation.
    """
    if not text:
        return ""

    # First collapse ruby tags to their base text
    s = RUBY_RE.sub(r"\2", text)
    # Then strip all other tags and placeholders
    s = NGUI_TAG_RE.sub("", s)
    return s


def get_rendered_length(text: str) -> int:
    """
    Calculate the rendered character count of text, ignoring all NGUI markup (Rule 19).
    Excludes newlines and carriage returns.
    """
    clean = strip_tags(text)
    clean_no_breaks = clean.replace("\r", "").replace("\n", "")
    return len(clean_no_breaks)


def measure_line_lengths(text: str) -> List[Tuple[int, int, str]]:
    """
    Measure rendered character length for each physical line in dialogue text.
    Returns list of (1-based line number, rendered length, stripped line text).
    """
    lines = text.splitlines()
    results = []
    for idx, line in enumerate(lines, start=1):
        clean_line = strip_tags(line)
        results.append((idx, len(clean_line), clean_line))
    return results


# -----------------------------------------------------------------------------
# Central TagMasker (Shields all tags & variables during MTL - Rule 19)
# -----------------------------------------------------------------------------

class TagMasker:
    """
    Protects Princess Connect NGUI tags, playername tokens, size, ruby, and control
    sequences from being translated, mangled, or dropped by translation engines.
    """

    # Comprehensive token regex covering all tags, placeholders, and line breaks
    TOKEN_REGEX = re.compile(
        r"(\{playername\}|\{\d+\}|"
        r"\[rub:[^\]]+\](?:.*?)\[/rub\]|"
        r"\[size=[^\]]*\]|\[/size\]|<size=[^>]*>|</size>|"
        r"\[[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?(?:[-,][0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)?\]|"
        r"\[c\][0-9a-fA-F]{6,8}\[/c\]|\[c\][0-9a-fA-F]{6,8}|\[/c\]|\[c\]|"
        r"\[/?(?:b|i|u|s|sub|sup)\]|\[-\]|\[/\]|"
        r"\[url=[^\]]*\]|\[/url\]|"
        r"\\n|\r?\n)",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def mask(cls, text: str) -> Tuple[str, Dict[str, str]]:
        """Replace all tags and placeholders with safe __M_n__ tokens."""
        tag_map: Dict[str, str] = {}
        counter = [0]

        def repl(match: re.Match) -> str:
            token = match.group(0)
            tag_id = str(counter[0])
            counter[0] += 1
            tag_map[tag_id] = token
            return f"__M_{tag_id}__"

        masked = cls.TOKEN_REGEX.sub(repl, text)
        return masked, tag_map

    @classmethod
    def unmask(cls, text: str, tag_map: Dict[str, str]) -> str:
        """
        Restore original tags from placeholder tokens, resilient to MT engine spacing
        variations (e.g., '__ M _ 0 __' or '__m_0__').
        """
        result = text
        for tag_id, original in tag_map.items():
            pattern = re.compile(r"__\s*[Mm]_\s*" + re.escape(tag_id) + r"\s*__")
            result = pattern.sub(lambda m, o=original: o, result)
        return result
