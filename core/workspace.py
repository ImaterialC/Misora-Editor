#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.workspace - Pure-Python .misora v1 Workspace Session Manager
========================================================================
Implements atomic JSON serialization/deserialization for `.misora` v1 workspace
files storing STRICTLY file references, workspace UI state, and composite
stable-key Translation Locks `(box_ordinal, jp_sha256)` ONLY.

Invariants (NO-01 / NO-12 / FEAT-08):
  - NEVER store unsaved story drafts, `.unity3d` binary blobs, or runtime `Record.uid`.
  - Use `write_atomic_encoded(..., newline="\\n")` and `read_text_file_strictly(...)`.
  - Guard Windows cross-drive `os.path.relpath` against `ValueError`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from .text_encoding import read_text_file_strictly, write_atomic_encoded

WORKSPACE_SCHEMA_VERSION: int = 1
MISORA_WORKSPACE_EXT: str = ".misora"

_VALID_VIEW_MODES = {"dialogue", "continuous"}
_VALID_SEARCH_SCOPES = {"project", "folder", "current"}


class WorkspaceError(ValueError):
    """Raised when a .misora workspace file is invalid or unsupported."""


@dataclass(frozen=True)
class LockedKeyEntry:
    """Stable composite lock key for a single dialogue box (NO-12)."""
    box_ordinal: int
    jp_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box_ordinal": int(self.box_ordinal),
            "jp_sha256": str(self.jp_sha256),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LockedKeyEntry":
        if not isinstance(data, dict):
            raise WorkspaceError("locked_keys entry must be an object.")
        if "box_ordinal" not in data or "jp_sha256" not in data:
            raise WorkspaceError("locked_keys entry requires 'box_ordinal' and 'jp_sha256'.")
        ordinal = data["box_ordinal"]
        sha = data["jp_sha256"]
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise WorkspaceError(f"Invalid box_ordinal in locked_keys: {ordinal!r}")
        if not isinstance(sha, str) or not sha:
            raise WorkspaceError("Invalid jp_sha256 in locked_keys.")
        return cls(box_ordinal=ordinal, jp_sha256=sha)


@dataclass
class WorkspaceFileEntry:
    """Reference to an open story file and its stable Translation Lock keys."""
    rel_path: str
    abs_path: str
    locked_keys: List[LockedKeyEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rel_path": str(self.rel_path),
            "abs_path": str(self.abs_path),
            "locked_keys": [lk.to_dict() for lk in self.locked_keys],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceFileEntry":
        if not isinstance(data, dict):
            raise WorkspaceError("Workspace file entry must be an object.")
        rel_path = data.get("rel_path", "")
        abs_path = data.get("abs_path", "")
        if not isinstance(rel_path, str) or not isinstance(abs_path, str):
            raise WorkspaceError("Workspace file entry 'rel_path' and 'abs_path' must be strings.")
        if not rel_path and not abs_path:
            raise WorkspaceError("Workspace file entry must include 'rel_path' or 'abs_path'.")
        raw_locks = data.get("locked_keys", [])
        if not isinstance(raw_locks, list):
            raise WorkspaceError("'locked_keys' must be a list.")
        locks = [LockedKeyEntry.from_dict(item) for item in raw_locks]
        return cls(rel_path=rel_path, abs_path=abs_path, locked_keys=locks)


@dataclass(frozen=True)
class WorkspaceDiffEntry:
    """Single row in the U-B18 Project Difference Mapping dialog."""
    path: Path
    status: str  # "added" | "removed" | "kept"
    is_dirty: bool
    display_name: str


@dataclass
class WorkspaceSession:
    """Complete .misora v1 workspace session (references + state + stable locks only)."""
    files: List[WorkspaceFileEntry] = field(default_factory=list)
    active_file: Optional[str] = None
    active_box_idx: int = 0
    is_box0_active: bool = False
    view_mode: str = "dialogue"
    search_scope: str = "project"
    schema_version: int = WORKSPACE_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        view_mode = self.view_mode if self.view_mode in _VALID_VIEW_MODES else "dialogue"
        search_scope = self.search_scope if self.search_scope in _VALID_SEARCH_SCOPES else "project"
        return {
            "schema_version": WORKSPACE_SCHEMA_VERSION,
            "files": [f.to_dict() for f in self.files],
            "active_file": str(self.active_file) if self.active_file else None,
            "active_box_idx": max(0, int(self.active_box_idx)),
            "is_box0_active": bool(self.is_box0_active),
            "view_mode": view_mode,
            "search_scope": search_scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceSession":
        if not isinstance(data, dict):
            raise WorkspaceError("Workspace JSON root must be an object.")
        schema_ver = data.get("schema_version")
        if schema_ver != WORKSPACE_SCHEMA_VERSION:
            raise WorkspaceError(
                f"Unsupported .misora schema_version: {schema_ver!r} (expected {WORKSPACE_SCHEMA_VERSION})."
            )
        raw_files = data.get("files")
        if not isinstance(raw_files, list):
            raise WorkspaceError("Workspace 'files' must be a list.")
        files = [WorkspaceFileEntry.from_dict(item) for item in raw_files]

        active_file = data.get("active_file")
        if active_file is not None and not isinstance(active_file, str):
            raise WorkspaceError("Workspace 'active_file' must be a string or null.")

        active_box_idx = data.get("active_box_idx", 0)
        if isinstance(active_box_idx, bool) or not isinstance(active_box_idx, int) or active_box_idx < 0:
            active_box_idx = 0

        is_box0_active = bool(data.get("is_box0_active", False))

        view_mode = data.get("view_mode", "dialogue")
        if view_mode not in _VALID_VIEW_MODES:
            view_mode = "dialogue"

        search_scope = data.get("search_scope", "project")
        if search_scope not in _VALID_SEARCH_SCOPES:
            search_scope = "project"

        return cls(
            schema_version=WORKSPACE_SCHEMA_VERSION,
            files=files,
            active_file=active_file,
            active_box_idx=active_box_idx,
            is_box0_active=is_box0_active,
            view_mode=view_mode,
            search_scope=search_scope,
        )


def safe_relpath(file_path: Union[str, Path], workspace_dir: Union[str, Path]) -> str:
    """Compute relative path from workspace_dir to file_path, returning '' across Windows drives."""
    try:
        return os.path.relpath(str(Path(file_path).resolve()), str(Path(workspace_dir).resolve()))
    except ValueError:
        return ""


def resolve_workspace_file_path(
    workspace_dir: Union[str, Path],
    rel_path: str,
    abs_path: str,
) -> Optional[Path]:
    """Resolve a workspace file entry (rel_path relative to workspace_dir first, then abs_path)."""
    ws_dir = Path(workspace_dir).resolve()
    if rel_path:
        try:
            candidate = (ws_dir / rel_path).resolve()
            if candidate.is_file():
                return candidate
        except OSError:
            pass
    if abs_path:
        try:
            candidate = Path(abs_path).resolve()
            if candidate.is_file():
                return candidate
        except OSError:
            pass
    return None


def match_active_file(
    active_file: Optional[str],
    workspace_dir: Union[str, Path],
    resolved_entries: Iterable[Tuple[WorkspaceFileEntry, Optional[Path]]],
) -> Optional[Path]:
    """Match persisted active_file against both rel_path and abs_path of resolved entries."""
    if not active_file:
        return None
    ws_dir = Path(workspace_dir).resolve()
    active_norm = os.path.normcase(active_file)
    try:
        active_rel_resolved_norm = os.path.normcase(str((ws_dir / active_file).resolve()))
    except OSError:
        active_rel_resolved_norm = ""

    for entry, resolved in resolved_entries:
        if resolved is None:
            continue
        resolved_norm = os.path.normcase(str(resolved.resolve()))
        if entry.rel_path and os.path.normcase(entry.rel_path) == active_norm:
            return resolved
        if entry.abs_path and os.path.normcase(entry.abs_path) == active_norm:
            return resolved
        if active_rel_resolved_norm and resolved_norm == active_rel_resolved_norm:
            return resolved
        if resolved_norm == active_norm:
            return resolved
    return None


def compute_workspace_diff(
    open_documents: Dict[Path, Dict[str, Any]],
    target_paths: Iterable[Union[str, Path]],
    current_file_path: Optional[Path] = None,
    current_is_dirty: bool = False,
) -> List[WorkspaceDiffEntry]:
    """Compute sorted Added / Removed / Kept + Dirty diff entries for U-B18 ProjectDiffDialog."""
    current_map: Dict[str, Tuple[Path, bool]] = {}
    cur_norm = (
        os.path.normcase(str(Path(current_file_path).resolve()))
        if current_file_path is not None
        else ""
    )
    for raw_p, info in (open_documents or {}).items():
        p = Path(raw_p).resolve()
        norm_p = os.path.normcase(str(p))
        dirty = bool(info.get("dirty", False)) if isinstance(info, dict) else False
        if norm_p == cur_norm:
            dirty = dirty or bool(current_is_dirty)
        current_map[norm_p] = (p, dirty)

    target_map: Dict[str, Path] = {}
    for raw_t in target_paths:
        p = Path(raw_t).resolve()
        target_map[os.path.normcase(str(p))] = p

    entries: List[WorkspaceDiffEntry] = []
    for norm_p, (p, dirty) in current_map.items():
        status = "kept" if norm_p in target_map else "removed"
        entries.append(
            WorkspaceDiffEntry(
                path=p,
                status=status,
                is_dirty=dirty,
                display_name=p.name or str(p),
            )
        )
    for norm_p, p in target_map.items():
        if norm_p not in current_map:
            entries.append(
                WorkspaceDiffEntry(
                    path=p,
                    status="added",
                    is_dirty=False,
                    display_name=p.name or str(p),
                )
            )

    order = {"removed": 0, "kept": 1, "added": 2}
    entries.sort(key=lambda e: (order.get(e.status, 9), e.display_name.lower(), str(e.path).lower()))
    return entries


def save_workspace(workspace_path: Union[str, Path], session: WorkspaceSession) -> None:
    """Atomically write a .misora v1 workspace JSON file (UTF-8, LF)."""
    target = Path(workspace_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = session.to_dict()
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    write_atomic_encoded(target, serialized, encoding="utf-8", has_bom=False, newline="\n")


def load_workspace(workspace_path: Union[str, Path]) -> WorkspaceSession:
    """Strictly read and validate a .misora v1 workspace JSON file."""
    decoded = read_text_file_strictly(Path(workspace_path))
    try:
        data = json.loads(decoded.text)
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"Invalid .misora JSON: {exc}") from exc
    return WorkspaceSession.from_dict(data)
