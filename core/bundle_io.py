#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.bundle_io - In-memory loading, extraction, and verified atomic saving of Unity3D bundles.
Self-contained module utilizing UnityPy for verified asset modification.
"""
from __future__ import annotations

import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .story_ast import StoryDocument

_unitypy: Any = None
_unitypy_lock = threading.Lock()


def get_unitypy() -> Any:
    """Lazy-load UnityPy under lock with Priconne fallback version (Rule 22)."""
    global _unitypy
    if _unitypy is None:
        with _unitypy_lock:
            if _unitypy is None:
                try:
                    import UnityPy  # type: ignore
                    UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.20f1"
                    _unitypy = UnityPy
                except ImportError as e:
                    raise BundleIOError(
                        f"UnityPy is required to load and save Unity3D bundles: {e}"
                    ) from e
    return _unitypy


# Module-level save guard to prevent re-entrant saves
_save_lock = threading.Lock()
_is_saving = False


class BundleIOError(Exception):
    pass


def _script_attr_of(asset_data: Any) -> Tuple[str, Union[str, bytes]]:
    """Determine the text/script attribute name on a TextAsset."""
    for attr in ("m_Script", "script", "text"):
        val = getattr(asset_data, attr, None)
        if val is not None:
            return attr, val
    raise BundleIOError("TextAsset has no valid script or m_Script attribute.")


def extract_raw_story_bytes(text_asset_obj: Any) -> bytes:
    """Extract binary story script bytes from a TextAsset object."""
    d = text_asset_obj.read()
    _, val = _script_attr_of(d)
    if isinstance(val, str):
        return val.encode("utf-8", "surrogateescape")
    return bytes(val)


def load_bundle_story(path: Union[str, Path]) -> Tuple[StoryDocument, Any, Any, str]:
    """
    Load a .unity3d bundle file directly into memory.
    Locks onto the story TextAsset with its path_id.
    Returns:
        (StoryDocument, UnityPy.Environment, TextAsset_Object, asset_name)
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        raw_bundle_bytes = path.read_bytes()
        env = get_unitypy().load(raw_bundle_bytes)
    except Exception as e:
        raise BundleIOError(f"Failed to open Unity3D bundle '{path.name}': {e}")

    target_obj = None
    target_name = ""

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                data = obj.read()
                nm = getattr(data, "m_Name", "") or ""
                if nm.startswith("storydata") or "story" in nm.lower() or not target_obj:
                    target_obj = obj
                    target_name = nm
            except Exception:
                pass

    if not target_obj:
        raise BundleIOError(f"No TextAsset found inside bundle '{path.name}'.")

    raw_bytes = extract_raw_story_bytes(target_obj)
    doc = StoryDocument.from_binary(raw_bytes)
    return doc, env, target_obj, target_name


def save_bundle_story(
    env: Any,
    text_asset_obj: Any,
    doc: StoryDocument,
    out_path: Union[str, Path],
    backup_dir: Optional[Path] = None,
) -> int:
    """
    Repack the modified StoryDocument back into the Unity3D bundle file in-place.
    Follows verified atomic save pipeline:
    same-dir .tmp -> reopen tmp -> verify exact target TextAsset by path_id/name ->
    verify object count -> fingerprint check -> bounded retry os.replace.
    Never overwrites original before verification succeeds.
    """
    global _is_saving

    with _save_lock:
        if _is_saving:
            raise BundleIOError("A bundle save operation is already in progress.")
        _is_saving = True

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f"{out_path.name}.{os.getpid()}_{id(doc)}.tmp")

    try:
        source_stat = out_path.stat() if out_path.is_file() else None
        source_fingerprint = (source_stat.st_mtime_ns, source_stat.st_size) if source_stat else None
        target_path_id = getattr(text_asset_obj, "path_id", None)
        target_name = getattr(text_asset_obj.read(), "m_Name", "")
        source_obj_count = len(list(env.objects))

        new_data = doc.to_binary()
        d = text_asset_obj.read()
        attr, cur_val = _script_attr_of(d)

        modes = ["str", "bytes"] if isinstance(cur_val, str) else ["bytes", "str"]
        success = False
        last_err = ""

        for mode in modes:
            try:
                val_to_set = new_data.decode("utf-8", "surrogateescape") if mode == "str" else new_data
                setattr(d, attr, val_to_set)
                d.save()

                saved_bytes = env.file.save(packer="original")
                tmp_path.write_bytes(saved_bytes)

                # Reopen tmp bytes and verify exact target asset & object count
                check_tmp_bytes = tmp_path.read_bytes()
                env_check = get_unitypy().load(check_tmp_bytes)
                target_in_check = None

                for o in env_check.objects:
                    if o.type.name == "TextAsset":
                        if target_path_id is not None and getattr(o, "path_id", None) == target_path_id:
                            target_in_check = o
                            break
                        elif getattr(o.read(), "m_Name", "") == target_name:
                            target_in_check = o
                            break

                if not target_in_check:
                    raise BundleIOError("Verification failed: Target TextAsset not found in repacked bundle.")

                check_bytes = extract_raw_story_bytes(target_in_check)
                if check_bytes != new_data:
                    raise BundleIOError("Verification failed: Repacked bytes do not match expected binary output.")

                if len(list(env_check.objects)) != source_obj_count:
                    raise BundleIOError(
                        f"Verification failed: Object count mismatch ({len(list(env_check.objects))} != {source_obj_count})."
                    )

                success = True
                break
            except Exception as ex:
                last_err = str(ex)

        if not success:
            raise BundleIOError(f"Bundle write verification failed for '{out_path.name}': {last_err}")

        # Verification succeeded! Perform backup if requested
        if backup_dir is not None and out_path.is_file():
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_path = backup_dir / f"{out_path.stem}.bak_{ts}{out_path.suffix}"
            shutil.copy2(out_path, bak_path)

        # Atomic replace with fingerprint check and bounded retry for Windows sharing violations
        for attempt in range(5):
            try:
                if source_fingerprint and out_path.is_file():
                    current_stat = out_path.stat()
                    current_fingerprint = (current_stat.st_mtime_ns, current_stat.st_size)
                    if current_fingerprint != source_fingerprint:
                        raise BundleIOError(
                            f"Source file '{out_path.name}' was modified concurrently on disk during save."
                        )
                os.replace(tmp_path, out_path)
                break
            except (PermissionError, OSError) as e:
                if attempt == 4:
                    raise BundleIOError(
                        f"Failed to replace bundle '{out_path.name}' after 5 attempts (Windows sharing violation): {e}"
                    )
                time.sleep(0.05 * (2 ** attempt))

        return out_path.stat().st_size

    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        with _save_lock:
            _is_saving = False
