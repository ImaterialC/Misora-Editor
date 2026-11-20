#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.undo_journal - Bounded coalescing undo/redo journal for Misora.
Tracks box edits, structural operations (insert/delete), plain-text edits, and bulk operations.
Thread-safe, exception-safe batches, and source-aware coalescing.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

from .story_ast import BoxSnapshot

MAX_HISTORY = 50
COALESCE_WINDOW_SECS = 2.0


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


@dataclass
class BoxStructuralDelta:
    """Structural dialogue box mutation (insert, delete, clone) using BoxSnapshot."""
    op_type: str  # "insert", "delete"
    box_index: int
    snapshots: List[BoxSnapshot]
    file_path: str = ""
    source: str = "user"


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
class UndoOperation:
    """One undoable unit that may contain multiple deltas."""
    label: str                    # shown in Edit > Undo <label>
    timestamp: float              # time.monotonic() at creation
    deltas: List[Any] = field(default_factory=list)
    coalesced: bool = False


class MasterUndoJournal:
    """
    Thread-safe bounded coalescing undo/redo journal.
    - Max MAX_HISTORY operations; oldest dropped on overflow.
    - Consecutive BoxEditDelta ops for the same box and same source within COALESCE_WINDOW_SECS are merged.
    - begin_batch()/end_batch() and contextmanager batch() group multiple deltas into one UndoOperation.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._undo_stack: List[UndoOperation] = []
        self._redo_stack: List[UndoOperation] = []
        self._batch: Optional[UndoOperation] = None
        self._batch_depth: int = 0
        self._revision: int = 0
        self._saved_revision: int = 0

    # ------------------------------------------------------------------
    # Batch API
    # ------------------------------------------------------------------
    def begin_batch(self, label: str) -> None:
        with self._lock:
            if self._batch_depth == 0:
                self._batch = UndoOperation(label=label, timestamp=time.monotonic())
            self._batch_depth += 1

    def end_batch(self) -> None:
        with self._lock:
            if self._batch_depth <= 0:
                return
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._batch is not None:
                if self._batch.deltas:
                    self._push(self._batch)
                self._batch = None

    @contextmanager
    def batch(self, label: str) -> Generator[MasterUndoJournal, None, None]:
        """Exception-safe batch context manager: guarantees end_batch() in finally."""
        self.begin_batch(label)
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
                return

            now = time.monotonic()
            # Coalescing: merge consecutive BoxEditDelta for same box, same source within window
            if (
                isinstance(delta, BoxEditDelta)
                and self._undo_stack
                and len(self._undo_stack[-1].deltas) == 1
                and isinstance(self._undo_stack[-1].deltas[0], BoxEditDelta)
            ):
                prev_delta = self._undo_stack[-1].deltas[0]
                same_box = (
                    (prev_delta.box_uid is not None and prev_delta.box_uid == delta.box_uid)
                    or (prev_delta.box_index == delta.box_index)
                )
                same_source = (prev_delta.source == delta.source)
                same_file = (prev_delta.file_path == delta.file_path)

                if same_box and same_source and same_file and (now - self._undo_stack[-1].timestamp) <= COALESCE_WINDOW_SECS:
                    prev_delta.new_text = delta.new_text
                    prev_delta.new_speaker = delta.new_speaker
                    self._undo_stack[-1].timestamp = now
                    self._undo_stack[-1].coalesced = True
                    return

            op = UndoOperation(
                label=label or _auto_label(delta),
                timestamp=now,
                deltas=[delta],
            )
            self._push(op)

    def _push(self, op: UndoOperation) -> None:
        """Push op to undo stack, clear redo stack, enforce MAX_HISTORY."""
        self._redo_stack.clear()
        self._undo_stack.append(op)
        self._revision += 1
        if len(self._undo_stack) > MAX_HISTORY:
            self._undo_stack = self._undo_stack[-MAX_HISTORY:]

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def can_undo(self) -> bool:
        with self._lock:
            return bool(self._undo_stack)

    def can_redo(self) -> bool:
        with self._lock:
            return bool(self._redo_stack)

    def undo_label(self) -> str:
        with self._lock:
            return self._undo_stack[-1].label if self._undo_stack else ""

    def redo_label(self) -> str:
        with self._lock:
            return self._redo_stack[-1].label if self._redo_stack else ""

    def pop_undo(self) -> Optional[UndoOperation]:
        with self._lock:
            if not self._undo_stack:
                return None
            op = self._undo_stack.pop()
            self._redo_stack.append(op)
            self._revision -= 1
            return op

    def pop_redo(self) -> Optional[UndoOperation]:
        with self._lock:
            if not self._redo_stack:
                return None
            op = self._redo_stack.pop()
            self._undo_stack.append(op)
            self._revision += 1
            return op

    def mark_saved(self) -> None:
        """Mark the current revision as clean/saved (AGENTS.md Rule 13)."""
        with self._lock:
            self._saved_revision = self._revision

    def is_clean(self) -> bool:
        """Check if current revision matches the last saved revision."""
        with self._lock:
            return self._revision == self._saved_revision

    def prune_file(self, file_path: str) -> None:
        """Prune undo/redo deltas associated with a closed file path (AGENTS.md Rule 16)."""
        with self._lock:
            def keep_op(op: UndoOperation) -> bool:
                return any(getattr(d, "file_path", "") != file_path for d in op.deltas)

            self._undo_stack = [op for op in self._undo_stack if keep_op(op)]
            self._redo_stack = [op for op in self._redo_stack if keep_op(op)]

    def clear(self) -> None:
        with self._lock:
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._batch = None
            self._batch_depth = 0

    @property
    def undo_depth(self) -> int:
        with self._lock:
            return len(self._undo_stack)

    @property
    def redo_depth(self) -> int:
        with self._lock:
            return len(self._redo_stack)


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
    if isinstance(delta, PlainTextDelta):
        import os
        return f"Edit {os.path.basename(delta.file_path)}"
    if isinstance(delta, BulkFileDelta):
        return delta.description
    if isinstance(delta, MetadataDelta):
        return "Edit Story Metadata"
    return "Edit"
