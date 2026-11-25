#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.undo_journal - Bounded coalescing undo/redo journal for Misora.
Tracks box edits, structural operations (insert/delete), plain-text edits, and bulk operations.
Thread-safe, exception-safe batches, per-file stack isolation, and source-aware coalescing.
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from .story_ast import BoxSnapshot

MAX_HISTORY = 50
COALESCE_WINDOW_SECS = 2.0


def _norm_path(p: Optional[Any]) -> str:
    """Normalize file path for dictionary keying (case-insensitive on Windows)."""
    if p is None:
        return ""
    if isinstance(p, Path):
        p = str(p)
    s = str(p).strip()
    if not s:
        return ""
    return os.path.normcase(os.path.normpath(s))


@dataclass
class BoxEditDelta:
    """Single dialogue box text/speaker change with stable box identity and source tracking."""
    box_index: int
    old_speaker: str
    new_speaker: str
    old_text: str
    new_text: str
    file_path: str = ""
    box_uid: Optional[int] = None
    source: str = "keyboard"  # "keyboard", "ribbon", "paste", "mtl"
    old_seg_texts: Optional[List[str]] = None
    new_seg_texts: Optional[List[str]] = None


@dataclass
class BoxStructuralDelta:
    """Structural dialogue box mutation (insert, delete, clone) using BoxSnapshot."""
    op_type: str  # "insert", "delete"
    box_index: int
    snapshots: List[BoxSnapshot]
    file_path: str = ""
    source: str = "user"
    indices: Optional[List[int]] = None


@dataclass
class BoxSnapshotReplaceDelta:
    """Lossless in-place BoxSnapshot replacement (Paste Box Replace mode)."""
    box_index: int
    old_snapshot: BoxSnapshot
    new_snapshot: BoxSnapshot
    file_path: str = ""
    box_uid: Optional[int] = None
    source: str = "box_replace"


@dataclass
class PlainTextDelta:
    """Plain-text (.txt) file edit — full snapshot before/after."""
    file_path: str
    old_content: str
    new_content: str


@dataclass
class BulkFileDelta:
    """Replace-All across multiple files: list of (file_path, old_text, new_text) tuples."""
    description: str
    per_file: List[Tuple[str, str, str]] = field(default_factory=list)


@dataclass
class MetadataDelta:
    """Story Title, Subtitle, and Summary metadata change (Box 0)."""
    file_path: str
    old_title: str
    new_title: str
    old_subtitle: str
    new_subtitle: str
    old_summary: str
    new_summary: str


@dataclass
class DocumentRecordsDelta:
    """Whole-document Record list replacement (Raw Commands v2 edit) with lock/JP snapshots."""
    file_path: str
    old_records: List[Any]
    new_records: List[Any]
    old_removed_records: Set[int] = field(default_factory=set)
    new_removed_records: Set[int] = field(default_factory=set)
    old_box_idx: int = 0
    new_box_idx: int = 0
    old_is_box0: bool = False
    new_is_box0: bool = False
    old_locked_uids: Set[int] = field(default_factory=set)
    new_locked_uids: Set[int] = field(default_factory=set)
    old_jp_by_uid: Dict[int, str] = field(default_factory=dict)
    new_jp_by_uid: Dict[int, str] = field(default_factory=dict)


@dataclass
class UndoOperation:
    """One undoable unit that may contain multiple deltas."""
    label: str                    # shown in Edit > Undo <label>
    timestamp: float              # time.monotonic() at creation
    deltas: List[Any] = field(default_factory=list)
    coalesced: bool = False


@dataclass
class _FileJournalState:
    """Internal per-file undo/redo stacks and revision tracking (Rule 13)."""
    undo_stack: List[UndoOperation] = field(default_factory=list)
    redo_stack: List[UndoOperation] = field(default_factory=list)
    revision: int = 0
    saved_revision: int = 0


class MasterUndoJournal:
    """
    Thread-safe bounded coalescing undo/redo journal with per-file stack isolation (Rule 13, 16).
    - Max MAX_HISTORY operations per file; oldest dropped on overflow.
    - Consecutive BoxEditDelta ops for the same box and same source within COALESCE_WINDOW_SECS are merged.
    - begin_batch()/end_batch() and contextmanager batch() group multiple deltas into one UndoOperation.
    - Independent revision and saved_revision per file path for accurate dirty state.
    - Full backward-compatibility: parameterless methods operate on the active/default file.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._file_states: Dict[str, _FileJournalState] = {}
        self._active_file: str = ""
        self._last_active_file: str = ""
        self._batch: Optional[UndoOperation] = None
        self._batch_depth: int = 0
        self._batch_file: str = ""

    def _get_key(self, file_path: Optional[Any] = None) -> str:
        """Resolve normalized key for file_path or active/fallback file."""
        if file_path is not None:
            return _norm_path(file_path)
        if self._active_file:
            return self._active_file
        if self._last_active_file:
            return self._last_active_file
        return ""

    def _get_state(self, file_path: Optional[Any] = None) -> _FileJournalState:
        """Get or create the _FileJournalState for file_path (must be called with _lock held)."""
        key = self._get_key(file_path)
        if key not in self._file_states:
            self._file_states[key] = _FileJournalState()
        return self._file_states[key]

    def set_active_file(self, file_path: Optional[Any]) -> None:
        """Set the current active file path for subsequent default operations."""
        with self._lock:
            self._active_file = _norm_path(file_path)
            if self._active_file:
                self._last_active_file = self._active_file

    # ------------------------------------------------------------------
    # Batch API
    # ------------------------------------------------------------------
    def begin_batch(self, label: str, file_path: Optional[Any] = None) -> None:
        with self._lock:
            if self._batch_depth == 0:
                self._batch = UndoOperation(label=label, timestamp=time.monotonic())
                self._batch_file = _norm_path(file_path) if file_path is not None else self._active_file
            self._batch_depth += 1

    def end_batch(self) -> None:
        with self._lock:
            if self._batch_depth <= 0:
                return
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._batch is not None:
                if self._batch.deltas:
                    target_file = self._batch_file
                    if not target_file:
                        for d in self._batch.deltas:
                            fp = getattr(d, "file_path", "")
                            if fp:
                                target_file = _norm_path(fp)
                                break
                    if not target_file:
                        target_file = self._get_key(None)
                    self._push_to_state(self._get_state(target_file), self._batch, target_file)
                self._batch = None
                self._batch_file = ""

    @contextmanager
    def batch(self, label: str, file_path: Optional[Any] = None) -> Generator[MasterUndoJournal, None, None]:
        """Exception-safe batch context manager: guarantees end_batch() in finally."""
        self.begin_batch(label, file_path=file_path)
        try:
            yield self
        finally:
            self.end_batch()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record(self, delta: Any, label: str = "") -> None:
        """Record one delta. If inside a batch, appends to batch; otherwise creates/coalesces."""
        with self._lock:
            if self._batch is not None:
                self._batch.deltas.append(delta)
                if label and not self._batch.label:
                    self._batch.label = label
                if not self._batch_file:
                    fp = getattr(delta, "file_path", "")
                    if fp:
                        self._batch_file = _norm_path(fp)
                return

            delta_fp = getattr(delta, "file_path", "")
            key = _norm_path(delta_fp) if delta_fp else self._get_key(None)
            state = self._get_state(key)
            now = time.monotonic()

            # Coalescing: merge consecutive BoxEditDelta for same box, same source within window
            if (
                isinstance(delta, BoxEditDelta)
                and state.undo_stack
                and len(state.undo_stack[-1].deltas) == 1
                and isinstance(state.undo_stack[-1].deltas[0], BoxEditDelta)
            ):
                prev_delta = state.undo_stack[-1].deltas[0]
                if prev_delta.box_uid is not None and delta.box_uid is not None:
                    same_box = (prev_delta.box_uid == delta.box_uid)
                else:
                    same_box = (prev_delta.box_index == delta.box_index)
                same_source = (prev_delta.source == delta.source)
                same_file = (prev_delta.file_path == delta.file_path)

                if same_box and same_source and same_file and (now - state.undo_stack[-1].timestamp) <= COALESCE_WINDOW_SECS:
                    prev_delta.new_text = delta.new_text
                    prev_delta.new_speaker = delta.new_speaker
                    if delta.new_seg_texts is not None:
                        prev_delta.new_seg_texts = delta.new_seg_texts
                    state.undo_stack[-1].timestamp = now
                    state.undo_stack[-1].coalesced = True
                    return

            op = UndoOperation(
                label=label or _auto_label(delta),
                timestamp=now,
                deltas=[delta],
            )
            self._push_to_state(state, op, key)

    def _push_to_state(self, state: _FileJournalState, op: UndoOperation, key: str) -> None:
        """Push op to state's undo stack, clear redo stack, enforce MAX_HISTORY, advance revision."""
        state.redo_stack.clear()
        state.undo_stack.append(op)
        state.revision += 1
        if key:
            self._last_active_file = key
        if len(state.undo_stack) > MAX_HISTORY:
            state.undo_stack = state.undo_stack[-MAX_HISTORY:]

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def can_undo(self, file_path: Optional[Any] = None) -> bool:
        with self._lock:
            state = self._get_state(file_path)
            return bool(state.undo_stack)

    def can_redo(self, file_path: Optional[Any] = None) -> bool:
        with self._lock:
            state = self._get_state(file_path)
            return bool(state.redo_stack)

    def undo_label(self, file_path: Optional[Any] = None) -> str:
        with self._lock:
            state = self._get_state(file_path)
            return state.undo_stack[-1].label if state.undo_stack else ""

    def redo_label(self, file_path: Optional[Any] = None) -> str:
        with self._lock:
            state = self._get_state(file_path)
            return state.redo_stack[-1].label if state.redo_stack else ""

    def pop_undo(self, file_path: Optional[Any] = None) -> Optional[UndoOperation]:
        with self._lock:
            state = self._get_state(file_path)
            if not state.undo_stack:
                return None
            op = state.undo_stack.pop()
            state.redo_stack.append(op)
            state.revision -= 1
            return op

    def pop_redo(self, file_path: Optional[Any] = None) -> Optional[UndoOperation]:
        with self._lock:
            state = self._get_state(file_path)
            if not state.redo_stack:
                return None
            op = state.redo_stack.pop()
            state.undo_stack.append(op)
            state.revision += 1
            return op

    def mark_saved(self, file_path: Optional[Any] = None) -> None:
        """Mark the current revision as clean/saved for file_path (AGENTS.md Rule 13)."""
        with self._lock:
            state = self._get_state(file_path)
            state.saved_revision = state.revision

    def is_clean(self, file_path: Optional[Any] = None) -> bool:
        """Check if current revision matches the last saved revision for file_path."""
        with self._lock:
            state = self._get_state(file_path)
            return state.revision == state.saved_revision

    def prune_file(self, file_path: str) -> None:
        """Prune undo/redo deltas associated with a closed file path (AGENTS.md Rule 16)."""
        with self._lock:
            key = _norm_path(file_path)
            if key in self._file_states:
                del self._file_states[key]
            if self._active_file == key:
                self._active_file = ""
            if self._last_active_file == key:
                self._last_active_file = ""

    def clear(self, file_path: Optional[Any] = None) -> None:
        with self._lock:
            if file_path is not None:
                key = _norm_path(file_path)
                if key in self._file_states:
                    del self._file_states[key]
            else:
                self._file_states.clear()
                self._active_file = ""
                self._last_active_file = ""
                self._batch = None
                self._batch_depth = 0
                self._batch_file = ""

    @property
    def undo_depth(self) -> int:
        return self.get_undo_depth()

    @property
    def redo_depth(self) -> int:
        return self.get_redo_depth()

    def get_undo_depth(self, file_path: Optional[Any] = None) -> int:
        with self._lock:
            state = self._get_state(file_path)
            return len(state.undo_stack)

    def get_redo_depth(self, file_path: Optional[Any] = None) -> int:
        with self._lock:
            state = self._get_state(file_path)
            return len(state.redo_stack)

    @property
    def _revision(self) -> int:
        with self._lock:
            return self._get_state(None).revision

    @property
    def _saved_revision(self) -> int:
        with self._lock:
            return self._get_state(None).saved_revision


def _auto_label(delta: Any) -> str:
    if isinstance(delta, BoxEditDelta):
        return f"Edit box #{delta.box_index + 1}"
    if isinstance(delta, BoxStructuralDelta):
        count = len(delta.snapshots)
        if delta.op_type == "insert":
            return f"Insert {count} box(es)"
        elif delta.op_type == "delete":
            return f"Delete {count} box(es)"
        return f"{delta.op_type.capitalize()} box"
    if isinstance(delta, BoxSnapshotReplaceDelta):
        return f"Replace box #{delta.box_index + 1}"
    if isinstance(delta, PlainTextDelta):
        import os
        return f"Edit {os.path.basename(delta.file_path)}"
    if isinstance(delta, BulkFileDelta):
        return delta.description
    if isinstance(delta, MetadataDelta):
        return "Edit Story Metadata"
    if isinstance(delta, DocumentRecordsDelta):
        return "Edit Raw Commands"
    return "Edit"
