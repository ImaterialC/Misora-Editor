#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.bundle_io - In-memory loading, extraction, and verified atomic saving of Unity3D bundles.
Self-contained module utilizing UnityPy for verified asset modification.
"""
from __future__ import annotations

import hashlib
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


def dispose_unity_env(env: Any) -> None:
    """Explicitly break circular reference cycles and release UnityPy Environment resources (S8b-2)."""
    if env is None:
        return
    try:
        if hasattr(env, "files") and isinstance(env.files, dict):
            for f in list(env.files.values()):
                try:
                    if hasattr(f, "files") and isinstance(f.files, dict):
                        for sf in list(f.files.values()):
                            if hasattr(sf, "objects") and isinstance(sf.objects, dict):
                                sf.objects.clear()
                            if hasattr(sf, "reader"):
                                sf.reader = None
                            if hasattr(sf, "environment"):
                                sf.environment = None
                            if hasattr(sf, "parent"):
                                sf.parent = None
                        f.files.clear()
                    if hasattr(f, "environment"):
                        f.environment = None
                    if hasattr(f, "parent"):
                        f.parent = None
                except Exception:
                    pass
            env.files.clear()
        if hasattr(env, "assets") and isinstance(env.assets, (list, dict)):
            if hasattr(env.assets, "clear"):
                env.assets.clear()
        if hasattr(env, "cabs") and isinstance(env.cabs, dict):
            env.cabs.clear()
        if hasattr(env, "container") and isinstance(env.container, dict):
            env.container.clear()
        if hasattr(env, "file"):
            env.file = None
    except Exception:
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

    try:
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
        try:
            doc = StoryDocument.from_binary(raw_bytes)
        except ValueError as ex:
            raise BundleIOError(f"Corrupted or invalid binary story data: {ex}") from ex
        return doc, env, target_obj, target_name
    except Exception:
        dispose_unity_env(env)
        raise


def _obj_key(o: Any) -> Any:
    """Derive stable object identity key for bundle object verification."""
    af = getattr(o, "assets_file", None)
    af_name = getattr(af, "name", "") if af else ""
    pid = getattr(o, "path_id", None)
    return (af_name, pid) if af_name else pid


def _get_raw_bytes(o: Any) -> bytes:
    """Extract raw bytes from UnityPy object reader or mock container."""
    if hasattr(o, "get_raw_data"):
        try:
            return bytes(o.get_raw_data())
        except Exception:
            pass
    if hasattr(o, "raw_data"):
        try:
            return bytes(o.raw_data)
        except Exception:
            pass
    return b""


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
    verify object count and non-target bytes -> fingerprint check -> bounded retry os.replace.
    Never overwrites original before verification succeeds.
    """
    global _is_saving

    with _save_lock:
        if _is_saving:
            raise BundleIOError("A bundle save operation is already in progress.")
        _is_saving = True

    tmp_path: Optional[Path] = None

    try:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_name(f"{out_path.name}.{os.getpid()}_{id(doc)}.tmp")

        source_stat = out_path.stat() if out_path.is_file() else None
        source_fingerprint = (source_stat.st_mtime_ns, source_stat.st_size) if source_stat else None
        target_path_id = getattr(text_asset_obj, "path_id", None)
        target_name = getattr(text_asset_obj.read(), "m_Name", "")
        source_obj_count = len(list(env.objects))

        # Record pre-save SHA-256 hashes of all non-target objects for integrity verification
        non_target_hashes = {}
        for o in env.objects:
            pid = getattr(o, "path_id", None)
            if pid is not None and pid != target_path_id:
                key = _obj_key(o)
                non_target_hashes[key] = hashlib.sha256(_get_raw_bytes(o)).hexdigest()

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
                try:
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

                    # Verify all non-target objects are preserved identically without modifications or drops
                    seen_non_target_keys = set()
                    for o in env_check.objects:
                        pid = getattr(o, "path_id", None)
                        if pid is not None and pid != target_path_id:
                            key = _obj_key(o)
                            if key not in non_target_hashes:
                                raise BundleIOError(f"Verification failed: Unexpected non-target object {key} in repacked bundle.")
                            h = hashlib.sha256(_get_raw_bytes(o)).hexdigest()
                            if h != non_target_hashes[key]:
                                raise BundleIOError(f"Verification failed: Non-target object {key} raw data modified during save.")
                            seen_non_target_keys.add(key)

                    missing_keys = set(non_target_hashes.keys()) - seen_non_target_keys
                    if missing_keys:
                        raise BundleIOError(f"Verification failed: Non-target objects missing in repacked bundle: {missing_keys}")

                    success = True
                    break
                finally:
                    dispose_unity_env(env_check)
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
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        with _save_lock:
            _is_saving = False
