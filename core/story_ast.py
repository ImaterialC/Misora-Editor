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
_INV_CMD_MAP = {v: k for k, v in _CMD_MAP.items()}

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


def norm_search(s: str) -> str:
    """
    Produce a completely whitespace-collapsed and placeholder-normalized string
    for matching XUnity's IgnoreWhitespaceInDialogue behavior.
    """
    if not s:
        return ""
    s = game_to_xuat(s)
    s = unicodedata.normalize("NFKC", s).translate(DASH_MAP)
    return re.sub(r"-{2,}", "-", ALL_WS_RE.sub("", s)).casefold()


def escape_arg(s: str) -> str:
    """Escape an argument for v2 text representation, preserving all Unicode line breaks."""
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
    return out


def unescape_arg(s: str) -> str:
    """Unescape an argument from v2 text representation."""
    if s.startswith("\\b64:"):
        return base64.b64decode(s[5:]).decode("utf-8", "surrogateescape")
    out = []
    i = 0
    m = {
        "n": "\n", "r": "\r", "t": "\t", "\\": "\\", "=": "=",
        "f": "\x0c", "v": "\x0b"
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
        # Include numeric command ID in header line if cmd_name is ambiguous or numeric
        if self.cmd_name in _CMD_MAP and _CMD_MAP[self.cmd_id] == self.cmd_name:
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
            elif r.cmd_name in DEFAULT_BREAKERS:
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

    def set_box_kind(self, box_index: int, new_kind: str) -> None:
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
            sp = box.speaker or "Narrator"
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

        # Verify record ownership
        doc_record_uids = {r.uid for r in self.records}
        for seg in box.segs:
            if seg.record.uid not in doc_record_uids:
                raise ValueError("Cannot inject into box containing records not owned by this document.")

        # Speaker update & automatic narration/dialogue kind conversion
        if new_speaker is not None:
            norm_sp = PLAYER_PLACEHOLDER_RE.sub("{0}", new_speaker)
            if not norm_sp and box.kind == "print":
                self.set_box_kind(box_index, "tag")
                box = self.boxes[box_index]
            elif norm_sp and box.kind == "tag":
                self.set_box_kind(box_index, "print")
                box = self.boxes[box_index]
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

    # -------------------------------------------------------------------------
    # Structural AST Mutation APIs
    # -------------------------------------------------------------------------
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
            extra = snapshot.get("extra_args")
            snap = BoxSnapshot(speaker=sp, voice_cue=vc, kind=kd, seg_texts=texts, extra_args=extra)
        else:
            snap = snapshot

        # Build records for the new box
        new_records: List[Record] = []
        is_print = (snap.kind == "print" and bool(snap.speaker))

        for k, seg_tx in enumerate(snap.seg_texts):
            norm_tx = xuat_to_game(seg_tx, self.break_char)
            ext = (snap.extra_args[k] if snap.extra_args and k < len(snap.extra_args) else [])
            if is_print:
                r = Record(cmd_id=6, cmd_name="print", args=[snap.speaker, norm_tx] + ext)
            else:
                r = Record(cmd_id=35, cmd_name="tag", args=[norm_tx] + ext)
            new_records.append(r)

        if not self.boxes:
            # Document has no boxes yet: append records
            self.records.extend(new_records)
        elif index <= 0:
            # Insert at beginning: find insertion point before first box segment
            first_rec = self.boxes[0].segs[0].record
            insert_pos = next((i for i, r in enumerate(self.records) if r.uid == first_rec.uid), 0)
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[insert_pos:insert_pos] = new_records + [breaker_rec]
        elif index >= len(self.boxes):
            # Append after last box: find last record of last box
            last_rec = self.boxes[-1].segs[-1].record
            last_pos = next((i for i, r in enumerate(self.records) if r.uid == last_rec.uid), len(self.records) - 1)
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[last_pos + 1:last_pos + 1] = [breaker_rec] + new_records
        else:
            # Insert between boxes: find last record of previous box
            prev_last_rec = self.boxes[index - 1].segs[-1].record
            prev_pos = next((i for i, r in enumerate(self.records) if r.uid == prev_last_rec.uid), 0)
            breaker_rec = Record(cmd_id=10, cmd_name=breaker_cmd, args=[])
            self.records[prev_pos + 1:prev_pos + 1] = [breaker_rec] + new_records

        self._rebuild_boxes()
        target_box_idx = max(0, min(index, len(self.boxes) - 1))
        return self.boxes[target_box_idx]

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
                for seg in box.segs:
                    uids_to_remove.add(seg.record.uid)

        self.records = [r for r in self.records if r.uid not in uids_to_remove]
        self.removed_records.update(uids_to_remove)
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
        move_uids = {seg.record.uid for seg in box_to_move.segs}
        move_recs = [r for r in self.records if r.uid in move_uids]

        # Remove records from current location
        self.records = [r for r in self.records if r.uid not in move_uids]
        self._rebuild_boxes()

        # Insert before or after target box
        target_box = self.boxes[to_index if to_index < from_index else to_index - 1]
        if to_index < from_index:
            target_pos = next(i for i, r in enumerate(self.records) if r.uid == target_box.segs[0].record.uid)
            self.records[target_pos:target_pos] = move_recs
        else:
            last_target_uid = target_box.segs[-1].record.uid
            target_pos = next(i for i, r in enumerate(self.records) if r.uid == last_target_uid)
            self.records[target_pos + 1:target_pos + 1] = move_recs

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
                break
            cid = struct.unpack_from(">H", raw, pos)[0]
            pos += 2
            args = []
            while True:
                if pos + 4 > n:
                    break
                ln = struct.unpack_from(">I", raw, pos)[0]
                pos += 4
                if ln == 0:
                    break
                if pos + ln > n:
                    break
                arg_bytes = raw[pos:pos + ln]
                pos += ln
                args.append(decode_arg(arg_bytes))

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

            # Command ID resolution without legacy relabeling special-case bug
            cid = r.cmd_id
            if cid == 0 and r.cmd_name != "fade" and r.cmd_name in _INV_CMD_MAP:
                cid = _INV_CMD_MAP[r.cmd_name]

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
