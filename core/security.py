#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
misora.core.security — Credential protection, DPAPI encryption, and secret redaction.

Protects sensitive API keys and secrets in local configuration (AGENTS.md Rule 17).
"""
from __future__ import annotations

import base64
import sys
import warnings
from typing import Optional

class DPAPISecurityError(RuntimeError):
    """Raised when Windows DPAPI cryptographic operations fail (BUG-33 / Rule 17)."""
    pass

# Windows Data Protection API (DPAPI) via ctypes
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]
else:
    ctypes = None  # type: ignore


def protect_secret(plaintext: str) -> str:
    """
    Encrypt a secret string using Windows DPAPI (CryptProtectData).
    Returns 'dpapi:<base64>' or the plaintext if encryption is unavailable on non-Windows.
    Fails closed with DPAPISecurityError on Windows DPAPI encryption failure (BUG-33 / Rule 17).
    """
    if not plaintext or not isinstance(plaintext, str):
        return ""
    if plaintext.startswith("dpapi:"):
        return plaintext
    if sys.platform != "win32" or ctypes is None:
        return plaintext

    try:
        raw_bytes = plaintext.encode("utf-8")
        in_blob = _DATA_BLOB(
            len(raw_bytes),
            ctypes.cast(ctypes.create_string_buffer(raw_bytes), ctypes.POINTER(ctypes.c_byte))
        )
        out_blob = _DATA_BLOB()

        # CryptProtectData(pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "Misora Secret",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if ok:
            encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
            return "dpapi:" + base64.b64encode(encrypted).decode("ascii")
        raise DPAPISecurityError(
            "Windows DPAPI encryption failed (CryptProtectData returned 0). "
            "Refusing to store secret in plaintext."
        )
    except DPAPISecurityError:
        raise
    except Exception as exc:
        raise DPAPISecurityError(
            f"Windows DPAPI encryption failed: {exc}. Refusing to store secret in plaintext."
        ) from exc


def unprotect_secret(ciphertext: str) -> str:
    """
    Decrypt a DPAPI-encrypted secret string ('dpapi:<base64>').
    Returns the decrypted plaintext, or the original string if not encrypted (legacy config).
    On decryption failure, emits RuntimeWarning and preserves ciphertext to prevent key wiping (BUG-33).
    """
    if not ciphertext or not isinstance(ciphertext, str):
        return ""
    if not ciphertext.startswith("dpapi:"):
        return ciphertext
    if sys.platform != "win32" or ctypes is None:
        return ciphertext

    try:
        raw_b64 = ciphertext[len("dpapi:"):]
        encrypted_bytes = base64.b64decode(raw_b64)
        in_blob = _DATA_BLOB(
            len(encrypted_bytes),
            ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte))
        )
        out_blob = _DATA_BLOB()

        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if ok:
            decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
            return decrypted.decode("utf-8")
        warnings.warn(
            "Failed to decrypt DPAPI-protected secret (CryptUnprotectData returned 0); "
            "preserving encrypted value.",
            RuntimeWarning,
            stacklevel=2,
        )
        return ciphertext
    except Exception:
        warnings.warn(
            "Failed to decrypt DPAPI-protected secret; preserving encrypted value.",
            RuntimeWarning,
            stacklevel=2,
        )
        return ciphertext


def redact_secret(secret: str) -> str:
    """
    Redact a secret string for safe display and logging (e.g., 'sk-...1234' or '****').
    """
    if not secret or not isinstance(secret, str):
        return ""
    s = secret.strip()
    if len(s) <= 8:
        return "****"
    return f"{s[:3]}...{s[-4:]}"
