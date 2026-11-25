#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.story_ast - AST Parser, Record & Box Representation, and Byte Serializer.
Self-contained module handling Princess Connect! Re:Dive ADV story binary & v2 text formats.
"""
from __future__ import annotations

import base64
import binascii
import copy
import itertools
import re
import struct
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# -----------------------------------------------------------------------------
# Regex & Normalization Constants
# -----------------------------------------------------------------------------
PLAYER_PLACEHOLDER_RE = re.compile(r"\{(?:player_?name|0)\}", re.IGNORECASE)
ALL_WS_RE = re.compile(r"[\s\u3000\u200b\u00a0\ufeff]+")
WS_RE = re.compile(r"\s+")
DASH_MAP = {c: "-" for c in "─—―–−‐‑"}
BREAK_RE = re.compile(r"\r\n|[\r\n\v\f\x85\u2028\u2029]")
BREAK_TAIL_RE = re.compile(r"(?:\r\n|[\r\n\v\f\x85\u2028\u2029])+$")

# Default command names & categories in Priconne ADV
DEFAULT_TEXT_CMDS = ("print", "tag")
NO_SPEAKER_CMDS = ("tag",)
DEFAULT_BREAKERS = ("touch", "page", "next_page")
DEFAULT_BREAKER_IDS = frozenset({0, 1, 4, 10, 36})
DEFAULT_CATEGORIES = (
    "System", "Foreground", "Background", "Screen", "Sound",
    "Movie", "Motion", "Effect", "Camera", "Face", "Animation",
    "Volume", "Other",
)

_CMD_MAP = {
    0: "fade", 1: "log", 2: "bg", 3: "chara", 4: "motion", 5: "face",
    6: "print", 7: "bgm", 8: "se", 9: "voice", 10: "touch", 11: "wait",
    12: "touch", 13: "wait", 14: "movie", 15: "fade", 16: "color",
    17: "chara_motion", 18: "motion", 20: "effect", 21: "fade_in",
    22: "fade_out", 23: "eye", 24: "lip", 25: "shake", 26: "flash",
    30: "title", 31: "outline", 32: "cmd_32", 35: "tag", 40: "shake_screen",
    41: "bloom", 42: "blur", 43: "fade_bg", 45: "bust", 50: "scale",
    51: "depth", 52: "wipe", 53: "mask", 55: "play_se", 56: "stop_se",
    57: "play_bgm", 58: "stop_bgm", 59: "effect", 60: "chara_visible",
    61: "chara_color", 62: "chara_layer", 63: "chara_flip", 64: "chara_scale",
    65: "chara_pos", 66: "chara_fade", 67: "chara_shake", 68: "unknown_68",
    70: "camera_move", 71: "camera_zoom", 72: "camera_rotate", 73: "camera_reset",
    80: "window_visible", 81: "window_size", 82: "window_pos",
    90: "next_page", 91: "choice", 92: "choice_jump", 100: "volume",
    110: "speed", 120: "flag_set", 121: "flag_check", 122: "flag_jump",
    125: "end"
}
# Canonical inverse mapping from command names to numeric IDs for v2 text resolution.
# Ambiguous names explicitly resolve to canonical IDs rather than dict-comprehension last-wins.
_INV_CMD_MAP = {
    "fade": 0, "log": 1, "bg": 2, "chara": 3, "motion": 4, "face": 5,
    "print": 6, "bgm": 7, "se": 8, "voice": 9, "touch": 10, "wait": 11,
    "movie": 14, "color": 16, "chara_motion": 17, "effect": 20,
    "fade_in": 21, "fade_out": 22, "eye": 23, "lip": 24, "shake": 25, "flash": 26,
    "title": 30, "outline": 31, "cmd_32": 32, "tag": 35, "situation": 36,
    "shake_screen": 40, "bloom": 41, "blur": 42, "fade_bg": 43, "bust": 45,
    "scale": 50, "depth": 51, "wipe": 52, "mask": 53, "play_se": 55, "stop_se": 56,
    "play_bgm": 57, "stop_bgm": 58, "chara_visible": 60, "chara_color": 61,
    "chara_layer": 62, "chara_flip": 63, "chara_scale": 64, "chara_pos": 65,
    "chara_fade": 66, "chara_shake": 67, "unknown_68": 68, "camera_move": 70,
    "camera_zoom": 71, "camera_rotate": 72, "camera_reset": 73, "window_visible": 80,
    "window_size": 81, "window_pos": 82, "next_page": 90, "choice": 91,
    "choice_jump": 92, "volume": 100, "speed": 110, "flag_set": 120,
    "flag_check": 121, "flag_jump": 122, "end": 125,
}

# Monotonic atomic ID counter for runtime Record identity
_next_rec_uid = itertools.count(1)


# -----------------------------------------------------------------------------
# Binary Bit-Inversion Codec for Priconne ADV
# -----------------------------------------------------------------------------
def _invert3(b: bytes) -> bytes:
    """Invert every 3rd byte (~b[i] & 0xFF) as required by Priconne ADV protocol."""
    o = bytearray(b)
    for i in range(0, len(o), 3):
        o[i] = ~o[i] & 0xFF
    return bytes(o)


def decode_arg(raw: bytes) -> str:
    """Decode raw binary argument: invert -> base64 decode -> utf-8 text."""
    inv = _invert3(raw)
    try:
        payload = base64.b64decode(inv, validate=True)
    except (binascii.Error, ValueError):
        payload = base64.b64decode(inv)
    return payload.decode("utf-8", "surrogateescape")


def encode_arg(text: str) -> bytes:
    """Encode text argument: utf-8 text -> base64 encode -> invert."""
    return _invert3(base64.b64encode(text.encode("utf-8", "surrogateescape")))


# -----------------------------------------------------------------------------
# String Utility Functions
# -----------------------------------------------------------------------------
def game_to_xuat(s: str) -> str:
    """Convert raw in-game text breaks to standard newlines and normalizes player placeholder."""
    if not s:
        return s
    s = s.replace(chr(92) + "n", "\n")
    s = BREAK_RE.sub("\n", s)
    return PLAYER_PLACEHOLDER_RE.sub("{playername}", s)


def xuat_to_game(s: str, br: str = "\n") -> str:
    """Convert XUAT translation to game engine format, replacing {playername} with {0}."""
    if not s:
        return s
    s = PLAYER_PLACEHOLDER_RE.sub("{0}", s)
    if br in (chr(92) + "n", "\\n"):
        return BREAK_RE.sub(chr(92) + "n", s)
    return BREAK_RE.sub(br, s)


def norm_search(s: str, match_case: bool = False) -> str:
    """
    Produce a completely whitespace-collapsed and placeholder-normalized string
    for matching XUnity's IgnoreWhitespaceInDialogue behavior.
    """
    if not s:
        return ""
    s = game_to_xuat(s)
    s = unicodedata.normalize("NFKC", s).translate(DASH_MAP)
    collapsed = re.sub(r"-{2,}", "-", ALL_WS_RE.sub("", s))
    return collapsed if match_case else collapsed.casefold()


def escape_arg(s: str) -> str:
    """Escape an argument for v2 text representation, preserving whitespace, categories, and non-UTF8 bytes."""
    # 1. Non-UTF-8 surrogateescape bytes -> \b64:<base64>
    if any(0xDC80 <= ord(c) <= 0xDCFF for c in s):
        raw = s.encode("utf-8", "surrogateescape")
        return f"\\b64:{base64.b64encode(raw).decode('ascii')}"

    # 2. Collision with default category names -> prefix with \
    if s in DEFAULT_CATEGORIES:
        return f"\\{s}"

    # 3. Escape backslashes first, then control and Unicode line breaks
    out = (
        s.replace("\\", "\\\\")
        .replace("\r\n", "\\r\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
        .replace("\x85", "\\x85")
        .replace("\x0c", "\\f")
        .replace("\x0b", "\\v")
    )

    # 4. Escape trailing and whitespace-only spaces (\s for ASCII space, \S for U+3000)
    trailing_len = 0
    while trailing_len < len(out) and out[-(trailing_len + 1)] in (" ", "\u3000"):
        trailing_len += 1
    if trailing_len > 0:
        head = out[:-trailing_len]
        tail = out[-trailing_len:]
        escaped_tail = "".join("\\s" if c == " " else "\\S" for c in tail)
        out = head + escaped_tail

    return out


def unescape_arg(s: str) -> str:
    """Unescape an argument from v2 text representation."""
    if s.startswith("\\b64:"):
        return base64.b64decode(s[5:]).decode("utf-8", "surrogateescape")
    if s.startswith("\\") and s[1:] in DEFAULT_CATEGORIES:
        return s[1:]
    out = []
    i = 0
    m = {
        "n": "\n", "r": "\r", "t": "\t", "\\": "\\", "=": "=",
        "f": "\x0c", "v": "\x0b", "s": " ", "S": "\u3000"
    }
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            if s[i + 1] in m:
                out.append(m[s[i + 1]])
                i += 2
                continue
            elif s[i:i + 6] == "\\u2028":
                out.append("\u2028")
                i += 6
                continue
            elif s[i:i + 6] == "\\u2029":
                out.append("\u2029")
                i += 6
                continue
            elif s[i:i + 4] == "\\x85":
                out.append("\x85")
                i += 4
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


# -----------------------------------------------------------------------------
# Record, Segment, Box, and Snapshot Data Classes
# -----------------------------------------------------------------------------
@dataclass
class Record:
    cmd_id: int
    cmd_name: str
    args: List[str]
    category: str = "Other"
    uid: int = field(default_factory=lambda: next(_next_rec_uid), init=True)

    def render_v2(self) -> List[str]:
        # Include numeric command ID in header line if cmd_name is ambiguous, non-canonical, or unknown/numeric
        if (
            _INV_CMD_MAP.get(self.cmd_name) == self.cmd_id
            and _CMD_MAP.get(self.cmd_id) == self.cmd_name
            and list(_CMD_MAP.values()).count(self.cmd_name) == 1
        ):
            header = self.cmd_name
        else:
            header = f"{self.cmd_name}#{self.cmd_id}"

        lines = [header]
        for a in self.args:
            lines.append(escape_arg(a))
        lines.append(self.category)
        lines.append("")
        return lines


@dataclass
class Seg:
    record: Record
    text: str
    raw: str


@dataclass
class BoxSnapshot:
    """
    Self-contained, immutable snapshot of a Box projection.
    Carries segment-level breakdown to avoid flattening multi-segment dialogue.
    """
    speaker: str
    voice_cue: str
    kind: str  # "print" or "tag"
    seg_texts: List[str]
    raw_breaks: Optional[List[str]] = None
    extra_args: Optional[List[List[str]]] = None

    @classmethod
    def from_box(cls, box: Box) -> BoxSnapshot:
        return cls(
            speaker=box.speaker,
            voice_cue=box.voice_cue,
            kind=box.kind,
            seg_texts=[s.text for s in box.segs],
            raw_breaks=[s.raw for s in box.segs],
            extra_args=[
                s.record.args[2:] if box.kind == "print" else s.record.args[1:]
                for s in box.segs
            ]
        )

    @property
    def clean_text(self) -> str:
        parts = [s for s in self.seg_texts if s]
        return game_to_xuat("".join(parts))


@dataclass
class Box:
    speaker: str
    voice_cue: str
    segs: List[Seg]
    kind: str  # "print" or "tag"

    @property
    def text(self) -> str:
        """Continuous concatenated dialogue text across all segments."""
        parts = [s.text for s in self.segs if s.text]
        return "".join(parts)

    @property
    def clean_text(self) -> str:
        """Game display text with {playername} placeholder formatted cleanly."""
        return game_to_xuat(self.text)

    @property
    def raw(self) -> str:
        """Concatenated raw segment text."""
        return "".join(s.raw for s in self.segs)

    @property
    def uid(self) -> int:
        """Stable runtime uid of the box's primary record."""
        return self.segs[0].record.uid if self.segs else 0

    def snapshot(self) -> BoxSnapshot:
        return BoxSnapshot.from_box(self)

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError(
            "Direct deepcopy of Box is forbidden (AGENTS.md Rule 5). "
            "Use Box.snapshot() / BoxSnapshot instead."
        )


# -----------------------------------------------------------------------------
# Story Document AST Representation
# -----------------------------------------------------------------------------
class StoryDocument:
    """
    Canonical AST representation of a Priconne ADV cutscene script.
    StoryDocument.records is the source of truth; Box is a high-level projection.
    """

    def __init__(self, records: Optional[List[Record]] = None):
        self.records: List[Record] = records or []
        self.boxes: List[Box] = []
        self.removed_records: Set[int] = set()  # Keyed by Record.uid
        self.break_char: str = "\n"
        if self.records:
            self._rebuild_boxes()

    def _rebuild_boxes(self) -> None:
        """Project sequential print/tag command segments into user-facing dialogue boxes."""
        boxes: List[Box] = []
        cur: Optional[Box] = None
        cur_voice: str = ""

        # Detect line break style
        counter = Counter()
        active_records = [r for r in self.records if r.uid not in self.removed_records]

        for r in active_records:
            if r.cmd_name == "voice" and r.args:
                cur_voice = r.args[0]
            # touch(cmd_id=12) with a voice filename argument is the character
            # voice-clip cue in PriConne story format.  touch(cmd_id=10) with no
            # args is the tap-to-advance wait; ignore that one.
            elif r.cmd_id == 12 and r.args and r.args[0].startswith("vo_"):
                cur_voice = r.args[0]
            for a in r.args:
                for m in BREAK_RE.finditer(a):
                    counter[m.group()] += 1

            if r.cmd_name in DEFAULT_TEXT_CMDS:
                if r.cmd_name == "print" and len(r.args) >= 2:
                    sp, tx = r.args[0], r.args[1]
                elif r.cmd_name == "tag" and len(r.args) >= 1:
                    sp, tx = "", r.args[0]
                else:
                    # Empty or malformed text command: do not create phantom box
                    continue

                if cur is None or cur.speaker != sp or cur.kind != r.cmd_name:
                    cur = Box(speaker=sp, voice_cue=cur_voice, segs=[], kind=r.cmd_name)
                    boxes.append(cur)
                    cur_voice = ""
                cur.segs.append(Seg(record=r, text=tx, raw=tx))
            elif r.cmd_id in DEFAULT_BREAKER_IDS:
                cur = None
                cur_voice = ""

        self.boxes = [b for b in boxes if b.segs]
        self.break_char = counter.most_common(1)[0][0] if counter else "\n"

    def actors(self) -> List[str]:
        """Return unique speaker names in chronological appearance order."""
        seen = []
        for b in self.boxes:
            if b.speaker and b.speaker not in seen:
                seen.append(b.speaker)
        return seen

    def has_metadata(self) -> bool:
        """Check if cutscene has metadata records (title, summary, or subtitle)."""
        return any(
            r.cmd_id in (0, 1, 32) and r.args and r.uid not in self.removed_records
            for r in self.records
        )

    def get_metadata(self) -> Dict[str, str]:
        """Extract chapter title, subtitle, and synopsis summary from cutscene records."""
        title = ""
        subtitle = ""
        summary = ""
        for r in self.records:
            if r.uid in self.removed_records:
                continue
            if r.cmd_id == 0 and r.args and not title:
                title = r.args[0]
            elif r.cmd_id == 1 and r.args and not summary:
                summary = game_to_xuat(r.args[0])
            elif r.cmd_id == 32 and r.args and not subtitle:
                subtitle = r.args[0]
        return {"title": title, "subtitle": subtitle, "summary": summary}

    def set_metadata(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        summary: Optional[str] = None
    ) -> None:
        """
        Inject updated title, subtitle, and summary back into underlying binary records.
        Preserves unmanaged extra arguments and rebases box projection immediately.
        """
        active_records = [r for r in self.records if r.uid not in self.removed_records]

        if title is not None:
            r0 = next((r for r in active_records if r.cmd_id == 0), None)
            if r0:
                r0.args = [title] + r0.args[1:]
            else:
                self.records.insert(0, Record(cmd_id=0, cmd_name="fade", args=[title]))

        if summary is not None:
            active_records = [r for r in self.records if r.uid not in self.removed_records]
            r1 = next((r for r in active_records if r.cmd_id == 1), None)
            game_summary = xuat_to_game(summary, self.break_char)
            if r1:
                r1.args = [game_summary] + r1.args[1:]
            else:
                idx = 1 if self.records and self.records[0].cmd_id == 0 else 0
                self.records.insert(idx, Record(cmd_id=1, cmd_name="log", args=[game_summary]))

        if subtitle is not None:
            active_records = [r for r in self.records if r.uid not in self.removed_records]
            r32 = next((r for r in active_records if r.cmd_id == 32), None)
            if r32:
                r32.args = [subtitle] + r32.args[1:]
            else:
                self.records.append(Record(cmd_id=32, cmd_name="cmd_32", args=[subtitle]))

        # Rebase box projection so segment pointers remain strictly valid
        self._rebuild_boxes()

    def _get_box_record_span(self, box: Box) -> Tuple[int, int, Optional[Record]]:
        """
        Return (start_idx, end_idx, voice_record) in self.records for box.
        start_idx points to the attached preceding voice cue (if present) or first segment record.
        end_idx points to the last segment record (inclusive).
        """
        if not box.segs:
            return 0, 0, None
        first_seg_uid = box.segs[0].record.uid
        last_seg_uid = box.segs[-1].record.uid
        first_seg_idx = next((i for i, r in enumerate(self.records) if r.uid == first_seg_uid), 0)
        last_seg_idx = next((i for i, r in enumerate(self.records) if r.uid == last_seg_uid), first_seg_idx)

        start_idx = first_seg_idx
        voice_rec = None
        for i in range(first_seg_idx - 1, -1, -1):
            r = self.records[i]
            if r.uid in self.removed_records:
                continue
            if (r.cmd_id == 12 and r.args and r.args[0].startswith("vo_")) or (r.cmd_name == "voice" and r.args):
                start_idx = i
                voice_rec = r
            break

        return start_idx, last_seg_idx, voice_rec

    def _collapse_duplicate_breakers(self) -> None:
        """Prune consecutive duplicate empty tap-breakers (cmd_id == 10 and not args)."""
        collapsed: List[Record] = []
        last_was_empty_tap = False
        for r in self.records:
            is_empty_tap = (r.cmd_id == 10 and not r.args)
            if is_empty_tap and last_was_empty_tap:
                continue
            collapsed.append(r)
            if r.cmd_id in DEFAULT_BREAKER_IDS:
                last_was_empty_tap = is_empty_tap
            elif r.cmd_name in DEFAULT_TEXT_CMDS:
                last_was_empty_tap = False
        self.records = collapsed

    def prune_removed_records(self) -> None:
        """Prune dead record UIDs from removed_records against active records (HYG-04)."""
        self.removed_records &= {r.uid for r in self.records}

    def set_box_kind(self, box_index: int, new_kind: str, rebuild: bool = True) -> None:
        """
        Convert a dialogue box between 'print' (spoken dialogue) and 'tag' (narration).
        'tag' records have no speaker argument (args=[text, ...extra]).
        'print' records have a speaker argument (args=[speaker, text, ...extra]).
        """
        if not (0 <= box_index < len(self.boxes)):
            raise IndexError(f"Box index {box_index} out of range (0-{len(self.boxes)-1})")
        box = self.boxes[box_index]
        if box.kind == new_kind:
            return

        target_uid = box.segs[0].record.uid
        start_idx, end_idx, voice_rec = self._get_box_record_span(box)

        target_sp = "" if new_kind == "tag" else (box.speaker or "Narrator")

        # Check preceding active text command in self.records before start_idx
        prec_text_cmd = None
        has_breaker_before = False
        for i in range(start_idx - 1, -1, -1):
            r = self.records[i]
            if r.uid in self.removed_records:
                continue
            if r.cmd_id in DEFAULT_BREAKER_IDS:
                has_breaker_before = True
                break
            if r.cmd_name in DEFAULT_TEXT_CMDS:
                prec_text_cmd = r
                break

        need_breaker_before = False
        if prec_text_cmd is not None and not has_breaker_before:
            prec_kind = prec_text_cmd.cmd_name
            prec_sp = prec_text_cmd.args[0] if prec_kind == "print" and len(prec_text_cmd.args) >= 2 else ""
            if prec_kind == new_kind and prec_sp == target_sp:
                need_breaker_before = True

        # Check following active text command in self.records after end_idx
        foll_text_cmd = None
        has_breaker_after = False
        for i in range(end_idx + 1, len(self.records)):
            r = self.records[i]
            if r.uid in self.removed_records:
                continue
            if r.cmd_id in DEFAULT_BREAKER_IDS:
                has_breaker_after = True
                break
            if r.cmd_name in DEFAULT_TEXT_CMDS:
                foll_text_cmd = r
                break

        need_breaker_after = False
        if foll_text_cmd is not None and not has_breaker_after:
            foll_kind = foll_text_cmd.cmd_name
            foll_sp = foll_text_cmd.args[0] if foll_kind == "print" and len(foll_text_cmd.args) >= 2 else ""
            if foll_kind == new_kind and foll_sp == target_sp:
                need_breaker_after = True

        # Insert breakers if needed (anchoring strictly before start_idx, i.e. before voice cue)
        if need_breaker_after:
            self.records.insert(end_idx + 1, Record(cmd_id=10, cmd_name="touch", args=[]))
        if need_breaker_before:
            self.records.insert(start_idx, Record(cmd_id=10, cmd_name="touch", args=[]))

        if new_kind == "tag":
            box.kind = "tag"
            box.speaker = ""
            for seg in box.segs:
                rec = seg.record
                rec.cmd_name = "tag"
                rec.cmd_id = 35
                if len(rec.args) >= 2:
                    rec.args = [rec.args[1]] + rec.args[2:]
                elif len(rec.args) == 1:
                    rec.args = [rec.args[0]]
                else:
                    rec.args = [""]
        elif new_kind == "print":
            box.kind = "print"
            sp = target_sp
            box.speaker = sp
            for seg in box.segs:
                rec = seg.record
                rec.cmd_name = "print"
                rec.cmd_id = 6
                if len(rec.args) >= 1:
                    rec.args = [sp, rec.args[0]] + rec.args[1:]
                else:
                    rec.args = [sp, ""]
        else:
            raise ValueError(f"Unknown box kind: {new_kind}. Expected 'print' or 'tag'.")

        if rebuild:
            self._rebuild_boxes()

    def inject_box(
        self,
        box_index: int,
        new_speaker: Optional[str],
        new_text: str,
        fill: str = "",
        seg_texts: Optional[List[str]] = None
    ) -> None:
        """
        Update a dialogue box in-place, redistributing text across underlying binary segments.
        Preserves unmanaged command arguments, updates seg.raw, and enforces narration rules.
        Rejects records not owned by this document.
        """
        if not (0 <= box_index < len(self.boxes)):
            raise IndexError(f"Box index {box_index} out of range (0-{len(self.boxes)-1})")

        box = self.boxes[box_index]
        target_uid = box.segs[0].record.uid

        # Verify record ownership
        doc_record_uids = {r.uid for r in self.records}
        for seg in box.segs:
            if seg.record.uid not in doc_record_uids:
                raise ValueError("Cannot inject into box containing records not owned by this document.")

        # Speaker update & automatic narration/dialogue kind conversion
        if new_speaker is not None:
            norm_sp = PLAYER_PLACEHOLDER_RE.sub("{0}", new_speaker)
            if not norm_sp and box.kind == "print":
                self.set_box_kind(box_index, "tag", rebuild=False)
                box = next((b for b in self.boxes if b.segs and b.segs[0].record.uid == target_uid), box)
            elif norm_sp and box.kind == "tag":
                self.set_box_kind(box_index, "print", rebuild=False)
                box = next((b for b in self.boxes if b.segs and b.segs[0].record.uid == target_uid), box)
                box.speaker = norm_sp
            else:
                box.speaker = norm_sp

        # Normalize text for game engine
        converted_text = xuat_to_game(new_text, self.break_char)

        segs = box.segs
        if seg_texts is not None and len(seg_texts) == len(segs):
            for k, seg in enumerate(segs):
                rec = seg.record
                st = xuat_to_game(seg_texts[k], self.break_char)
                seg.text = st
                seg.raw = st
                if box.kind == "print":
                    rec.args = [box.speaker, st] + rec.args[2:]
                else:
                    rec.args = [st] + rec.args[1:]
        elif len(segs) == 1:
            seg = segs[0]
            rec = seg.record
            seg.text = converted_text
            seg.raw = converted_text
            if box.kind == "print":
                rec.args = [box.speaker, converted_text] + rec.args[2:]
            else:
                rec.args = [converted_text] + rec.args[1:]
        else:
            core = converted_text.rstrip("\r\n\v\f\x85\u2028\u2029")
            m = BREAK_TAIL_RE.search(converted_text)
            tail = m.group() if m else ""

            target_idx = next((k for k, s in enumerate(segs) if s.raw.strip()), 0)
            for k, seg in enumerate(segs):
                rec = seg.record
                seg_text = (core if k == target_idx else fill) + (tail if k == len(segs) - 1 else "")
                seg.text = seg_text
                seg.raw = seg_text
                if box.kind == "print":
                    rec.args = [box.speaker, seg_text] + rec.args[2:]
                else:
                    rec.args = [seg_text] + rec.args[1:]

        # Rebuild projection ONLY after full speaker + text record write
        self._rebuild_boxes()

    # -------------------------------------------------------------------------
    # Structural AST Mutation APIs
    # -------------------------------------------------------------------------
    def _records_from_snapshot(self, snap: BoxSnapshot) -> Tuple[List[Record], str, str]:
        """Build Record list from all 6 fields of BoxSnapshot without mutating the document."""
        norm_sp = PLAYER_PLACEHOLDER_RE.sub("{0}", snap.speaker) if snap.speaker else ""
        is_print = (snap.kind == "print" and bool(norm_sp))
        target_kind = "print" if is_print else "tag"
        target_sp = norm_sp if is_print else ""

        new_records: List[Record] = []
        if snap.voice_cue:
            if snap.voice_cue.startswith("vo_"):
                new_records.append(Record(cmd_id=12, cmd_name="touch", args=[snap.voice_cue]))
            else:
                new_records.append(Record(cmd_id=9, cmd_name="voice", args=[snap.voice_cue]))

        seg_texts = snap.seg_texts if snap.seg_texts else [""]
        for k, seg_tx in enumerate(seg_texts):
            if snap.raw_breaks is not None and k < len(snap.raw_breaks) and snap.raw_breaks[k] is not None:
                rb = snap.raw_breaks[k]
                if rb in ("\n", "\r\n", "\r", "\\n"):
                    norm_tx = xuat_to_game(seg_tx, rb)
                else:
                    norm_tx = PLAYER_PLACEHOLDER_RE.sub("{0}", rb)
            else:
                norm_tx = xuat_to_game(seg_tx, self.break_char)
            ext = list(snap.extra_args[k]) if (snap.extra_args and k < len(snap.extra_args)) else []
            if is_print:
                r = Record(cmd_id=6, cmd_name="print", args=[target_sp, norm_tx] + ext)
            else:
                r = Record(cmd_id=35, cmd_name="tag", args=[norm_tx] + ext)
            new_records.append(r)

        return new_records, target_kind, target_sp

    def insert_box(
        self,
        index: int,
        snapshot: Union[BoxSnapshot, Dict[str, Any]],
        breaker_cmd: str = "touch"
    ) -> Box:
        """
        Insert a new Box into the document at the specified box index.
        Mutates underlying StoryDocument.records and rebuilds projection.
        """
        if isinstance(snapshot, dict):
            sp = snapshot.get("speaker", "")
            vc = snapshot.get("voice_cue", "")
            kd = snapshot.get("kind", "print" if sp else "tag")
            texts = snapshot.get("seg_texts") or [snapshot.get("clean_text", "")]
            raw_b = snapshot.get("raw_breaks")
            extra = snapshot.get("extra_args")
            snap = BoxSnapshot(
                speaker=sp,
                voice_cue=vc,
                kind=kd,
                seg_texts=texts,
                raw_breaks=raw_b,
                extra_args=extra,
            )
        else:
            snap = snapshot

        new_records, _, _ = self._records_from_snapshot(snap)

        if not self.boxes:
            # Document has no boxes yet: append records
            self.records.extend(new_records)
        elif index <= 0:
            # Insert at beginning: anchor BEFORE destination box's start_idx (including its vo_ cue)
            dest_start, _, _ = self._get_box_record_span(self.boxes[0])
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[dest_start:dest_start] = new_records + [breaker_rec]
        elif index >= len(self.boxes):
            # Append after last box: find last record of last box
            _, dest_end, _ = self._get_box_record_span(self.boxes[-1])
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[dest_end + 1:dest_end + 1] = [breaker_rec] + new_records
        else:
            # Insert between boxes: anchor BEFORE destination box's start_idx
            dest_start, _, _ = self._get_box_record_span(self.boxes[index])
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[dest_start:dest_start] = new_records + [breaker_rec]

        self._collapse_duplicate_breakers()
        self._rebuild_boxes()
        target_box_idx = max(0, min(index, len(self.boxes) - 1))
        return self.boxes[target_box_idx]

    def replace_box(self, box_index: int, snapshot: BoxSnapshot) -> BoxSnapshot:
        """
        Replace the box at `box_index` in-place from all 6 fields of `snapshot`,
        preserving surrounding interstitial commands and box separation (QW-B01).
        Returns the complete original BoxSnapshot captured prior to mutation.
        """
        if not (0 <= box_index < len(self.boxes)):
            raise IndexError(f"Box index {box_index} out of range (0-{len(self.boxes)-1})")
        if not isinstance(snapshot, BoxSnapshot):
            raise TypeError("snapshot must be a BoxSnapshot")
        if snapshot.kind not in ("print", "tag"):
            raise ValueError(f"Unknown snapshot kind: {snapshot.kind!r}")
        if not snapshot.seg_texts:
            raise ValueError("BoxSnapshot.seg_texts must not be empty")

        old_box = self.boxes[box_index]
        doc_record_uids = {r.uid for r in self.records}
        for seg in old_box.segs:
            if seg.record.uid not in doc_record_uids:
                raise ValueError("Cannot replace box containing records not owned by this document.")

        old_snapshot = BoxSnapshot.from_box(old_box)
        start_idx, end_idx, _ = self._get_box_record_span(old_box)
        new_records, target_kind, target_sp = self._records_from_snapshot(snapshot)

        # Preserve separation from preceding/following same-kind/same-speaker boxes (QW-B01)
        prec_text_cmd = None
        has_breaker_before = False
        for i in range(start_idx - 1, -1, -1):
            r = self.records[i]
            if r.uid in self.removed_records:
                continue
            if r.cmd_id in DEFAULT_BREAKER_IDS:
                has_breaker_before = True
                break
            if r.cmd_name in DEFAULT_TEXT_CMDS:
                prec_text_cmd = r
                break

        if prec_text_cmd is not None and not has_breaker_before:
            prec_kind = prec_text_cmd.cmd_name
            prec_sp = prec_text_cmd.args[0] if prec_kind == "print" and len(prec_text_cmd.args) >= 2 else ""
            if prec_kind == target_kind and prec_sp == target_sp:
                new_records.insert(0, Record(cmd_id=10, cmd_name="touch", args=[]))

        foll_text_cmd = None
        has_breaker_after = False
        for i in range(end_idx + 1, len(self.records)):
            r = self.records[i]
            if r.uid in self.removed_records:
                continue
            if r.cmd_id in DEFAULT_BREAKER_IDS:
                has_breaker_after = True
                break
            if r.cmd_name in DEFAULT_TEXT_CMDS:
                foll_text_cmd = r
                break

        if foll_text_cmd is not None and not has_breaker_after:
            foll_kind = foll_text_cmd.cmd_name
            foll_sp = foll_text_cmd.args[0] if foll_kind == "print" and len(foll_text_cmd.args) >= 2 else ""
            if foll_kind == target_kind and foll_sp == target_sp:
                new_records.append(Record(cmd_id=10, cmd_name="touch", args=[]))

        self.records[start_idx : end_idx + 1] = new_records
        self.prune_removed_records()
        self._collapse_duplicate_breakers()
        self._rebuild_boxes()
        return old_snapshot

    def delete_boxes(self, indices: List[int]) -> List[BoxSnapshot]:
        """
        Delete specified boxes from the document.
        Removes underlying records and rebuilds projection. Returns snapshots of deleted boxes.
        """
        if not indices:
            return []

        sorted_indices = sorted(set(indices), reverse=True)
        snapshots: List[BoxSnapshot] = []
        uids_to_remove: Set[int] = set()

        for idx in sorted_indices:
            if 0 <= idx < len(self.boxes):
                box = self.boxes[idx]
                snapshots.append(BoxSnapshot.from_box(box))
                start_idx, end_idx, voice_rec = self._get_box_record_span(box)
                for r in self.records[start_idx : end_idx + 1]:
                    uids_to_remove.add(r.uid)

                # Check if immediately followed by an empty tap-breaker (cmd_id == 10 and not args)
                if end_idx + 1 < len(self.records):
                    nxt = self.records[end_idx + 1]
                    if nxt.cmd_id == 10 and not nxt.args:
                        # Check surviving neighbor before start_idx and after end_idx+1
                        prec_cmd = next((self.records[i] for i in range(start_idx - 1, -1, -1) if self.records[i].uid not in uids_to_remove and self.records[i].cmd_name in DEFAULT_TEXT_CMDS), None)
                        foll_cmd = next((self.records[i] for i in range(end_idx + 2, len(self.records)) if self.records[i].uid not in uids_to_remove and self.records[i].cmd_name in DEFAULT_TEXT_CMDS), None)
                        # If surviving neighbors would merge (same kind and speaker), keep the breaker
                        neighbors_would_merge = False
                        if prec_cmd and foll_cmd:
                            p_sp = prec_cmd.args[0] if prec_cmd.cmd_name == "print" and len(prec_cmd.args) >= 2 else ""
                            f_sp = foll_cmd.args[0] if foll_cmd.cmd_name == "print" and len(foll_cmd.args) >= 2 else ""
                            if prec_cmd.cmd_name == foll_cmd.cmd_name and p_sp == f_sp:
                                neighbors_would_merge = True
                        if not neighbors_would_merge:
                            uids_to_remove.add(nxt.uid)

        self.records = [r for r in self.records if r.uid not in uids_to_remove]
        self.removed_records &= {r.uid for r in self.records}
        self._collapse_duplicate_breakers()
        self._rebuild_boxes()
        snapshots.reverse()
        return snapshots

    def move_box(self, from_index: int, to_index: int) -> None:
        """
        Move a dialogue box from from_index to to_index.
        Rearranges underlying records and rebuilds projection.
        """
        if from_index == to_index:
            return
        if not (0 <= from_index < len(self.boxes)):
            raise IndexError(f"from_index {from_index} out of range")
        if not (0 <= to_index < len(self.boxes)):
            raise IndexError(f"to_index {to_index} out of range")

        box_to_move = self.boxes[from_index]
        dest_box = self.boxes[to_index]
        dest_primary_uid = dest_box.segs[0].record.uid

        # Owned span includes attached voice cue
        start_idx, end_idx, voice_rec = self._get_box_record_span(box_to_move)
        move_recs = self.records[start_idx : end_idx + 1]
        move_uids = {r.uid for r in move_recs}

        # Check neighbors left in the gap at source
        prec_active = next((self.records[i] for i in range(start_idx - 1, -1, -1) if self.records[i].uid not in move_uids and self.records[i].uid not in self.removed_records and self.records[i].cmd_name in DEFAULT_TEXT_CMDS), None)
        foll_active = next((self.records[i] for i in range(end_idx + 1, len(self.records)) if self.records[i].uid not in move_uids and self.records[i].uid not in self.removed_records and self.records[i].cmd_name in DEFAULT_TEXT_CMDS), None)
        need_gap_breaker = False
        if prec_active and foll_active:
            p_sp = prec_active.args[0] if prec_active.cmd_name == "print" and len(prec_active.args) >= 2 else ""
            f_sp = foll_active.args[0] if foll_active.cmd_name == "print" and len(foll_active.args) >= 2 else ""
            if prec_active.cmd_name == foll_active.cmd_name and p_sp == f_sp:
                prec_idx = next(i for i, r in enumerate(self.records) if r.uid == prec_active.uid)
                foll_idx = next(i for i, r in enumerate(self.records) if r.uid == foll_active.uid)
                has_brk = any(self.records[i].cmd_id in DEFAULT_BREAKER_IDS for i in range(prec_idx + 1, foll_idx) if self.records[i].uid not in move_uids)
                if not has_brk:
                    need_gap_breaker = True

        # Remove records from current location
        self.records = [r for r in self.records if r.uid not in move_uids]
        if need_gap_breaker:
            insert_gap_pos = min(start_idx, len(self.records))
            self.records.insert(insert_gap_pos, Record(cmd_id=10, cmd_name="touch", args=[]))

        self._collapse_duplicate_breakers()
        self._rebuild_boxes()

        # Locate destination box in rebuilt document
        dest_box_in_doc = next((b for b in self.boxes if b.segs and b.segs[0].record.uid == dest_primary_uid), None)
        if not dest_box_in_doc:
            return

        d_start, d_end, _ = self._get_box_record_span(dest_box_in_doc)
        if to_index < from_index:
            # Insert before destination box: anchor BEFORE d_start (before dest box's voice cue)
            breaker_rec = Record(cmd_id=10, cmd_name="touch", args=[])
            self.records[d_start:d_start] = move_recs + [breaker_rec]
        else:
            # Insert after destination box: anchor AFTER d_end
            breaker_rec = Record(cmd_id=10, cmd_name="touch", args=[])
            self.records[d_end + 1:d_end + 1] = [breaker_rec] + move_recs

        self._collapse_duplicate_breakers()
        self._rebuild_boxes()

    def clone_boxes(self, indices: List[int], target_index: int) -> List[Box]:
        """
        Clone specified boxes and insert them immediately after target_index.
        Preserves segment counts and multi-segment structure.
        """
        if not indices:
            return []

        sorted_indices = sorted(set(indices))
        snapshots = [BoxSnapshot.from_box(self.boxes[i]) for i in sorted_indices if 0 <= i < len(self.boxes)]
        cloned_boxes: List[Box] = []

        curr_ins = target_index + 1
        for snap in snapshots:
            b = self.insert_box(curr_ins, snap)
            cloned_boxes.append(b)
            curr_ins += 1

        return cloned_boxes

    # -------------------------------------------------------------------------
    # Binary Parser & Serializer
    # -------------------------------------------------------------------------
    @classmethod
    def from_binary(cls, raw: bytes) -> StoryDocument:
        """Parse Priconne proprietary binary ADV story script bytes into a StoryDocument."""
        records: List[Record] = []
        pos, n = 0, len(raw)

        while pos < n:
            if pos + 2 > n:
                raise ValueError(f"Truncated command header at offset {pos} (expected 2 bytes, got {n - pos})")
            cid = struct.unpack_from(">H", raw, pos)[0]
            pos += 2
            args = []
            terminated = False
            while True:
                if pos + 4 > n:
                    raise ValueError(f"Partial argument length header at offset {pos} (expected 4 bytes, got {n - pos})")
                ln = struct.unpack_from(">I", raw, pos)[0]
                pos += 4
                if ln == 0:
                    terminated = True
                    break
                if pos + ln > n:
                    raise ValueError(f"Argument payload overrun at offset {pos} (expected {ln} bytes, got {n - pos})")
                arg_bytes = raw[pos:pos + ln]
                pos += ln
                args.append(decode_arg(arg_bytes))

            if not terminated:
                raise ValueError(f"Missing terminating length-0 argument marker for command {cid} at offset {pos}")

            cmd_name = _CMD_MAP.get(cid, f"cmd_{cid}")
            records.append(Record(cmd_id=cid, cmd_name=cmd_name, args=args))

        return cls(records)

    def to_binary(self) -> bytes:
        """
        Serialize StoryDocument records back into exact Priconne proprietary binary format.
        Preserves command IDs, enforces non-empty arguments, and prevents arity changes.
        """
        out = bytearray()
        for r in self.records:
            if r.uid in self.removed_records:
                continue

            # Command ID resolution
            cid = r.cmd_id

            # Enforce narration: print with blank speaker must be serialized as tag (cmd 35)
            cmd_name = r.cmd_name
            args = list(r.args)
            if cmd_name == "print" and len(args) >= 2 and args[0] == "":
                cid = 35
                args = args[1:]

            out += struct.pack(">H", cid)
            for a in args:
                # In binary ADV protocol, length 0 terminates the record argument list.
                # Never emit length 0; represent empty text as single space to preserve arity.
                raw_arg = encode_arg(a if a != "" else " ")
                out += struct.pack(">I", len(raw_arg)) + raw_arg
            out += struct.pack(">I", 0)

        return bytes(out)

    # -------------------------------------------------------------------------
    # V2 Text Parser & Serializer
    # -------------------------------------------------------------------------
    @classmethod
    def from_v2_text(cls, text: str) -> StoryDocument:
        """
        Parse readable v2 script text into a StoryDocument.
        Losslessly recovers command IDs, categories, whitespace args, and line breaks.
        """
        lines = [l.rstrip("\r\n") for l in text.splitlines()]
        if lines and lines[0].startswith("#!priconne-story"):
            lines.pop(0)

        records: List[Record] = []
        i = 0
        while i < len(lines):
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines):
                break

            header = lines[i].strip()
            i += 1

            # Parse command name and optional explicit command ID (e.g. "fade#0" or "cmd_32")
            if "#" in header:
                cmd_name, cid_str = header.split("#", 1)
                cmd_id = int(cid_str) if cid_str.isdigit() else _INV_CMD_MAP.get(cmd_name, 0)
            elif header.startswith("cmd_") and header[4:].isdigit():
                cmd_name = header
                cmd_id = int(header[4:])
            else:
                cmd_name = header
                cmd_id = _INV_CMD_MAP.get(cmd_name, 0)

            args = []
            category = "Other"
            while i < len(lines):
                l = lines[i]
                i += 1
                if not l.strip():
                    break
                if l in DEFAULT_CATEGORIES and not l.startswith("\\"):
                    category = l
                    break
                args.append(unescape_arg(l))

            records.append(Record(cmd_id=cmd_id, cmd_name=cmd_name, args=args, category=category))

        return cls(records)

    def to_v2_text(self) -> str:
        """Serialize StoryDocument into human-readable v2 script format."""
        out = ["#!priconne-story v2", ""]
        for r in self.records:
            if r.uid not in self.removed_records:
                out.extend(r.render_v2())
        return "\n".join(out)
