# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] (Target: v1.4.1)

### S03 — Strict Binary Parse, Lossless v2 + \b64:, Command Map/Breakers & Fixture-Gated Bundle Verify
- **Session Scope:** BUG-01, BUG-03, BUG-04, BUG-09 (Track 1 · Group B1 (DEP-5 part 1)).
- **BUG-01 (`core/story_ast.py:from_binary()`, `core/bundle_io.py:load_bundle_story()`):**
  - Enforced strict binary validation on every 2-byte command header, 4-byte argument length, payload byte slice, and terminating length-0 argument marker.
  - Replaced silent `break` with explicit `ValueError` on truncated headers, partial length markers, payload overruns, and missing length-0 terminators.
  - Wrapped `ValueError` as `BundleIOError` in `load_bundle_story()`, ensuring corrupt or truncated files never produce incomplete documents.
- **BUG-03 (`core/story_ast.py`, `misora.py:_update_raw_view()`):**
  - Removed legacy `cmd_id == 0` remapping branch in `to_binary()`, ensuring `cmd_id == 0` titles serialize strictly as `cmd_id == 0` (not 30).
  - Enhanced `escape_arg()` to detect non-UTF-8 surrogate-escaped bytes (`0xDC80..0xDCFF`) and emit `\b64:<base64>`, prefix a backslash on category collisions (`\<Cat>`), escape backslashes first, and escape trailing/whitespace-only spaces (`\s` for ASCII space, `\S` for `U+3000`).
  - Updated `unescape_arg()` to reverse `\b64:` via base64 surrogateescape decoding, reverse category collision prefixes, and restore `\s`/`\S`.
  - Fixed dead `if self.cmd_name in _CMD_MAP:` condition in `Record.render_v2()` so ambiguous and unknown commands consistently emit unambiguous `name#id` headers (`touch#10` vs `touch#12`).
  - Fixed Box 0 active highlight condition in `misora.py:_update_raw_view()` line 6825 to check `len(r.args) > 0 and r.args[0]` (matching `get_metadata()`), properly highlighting 1-arg title records.
- **BUG-04 (`core/story_ast.py`):**
  - Decoupled `_CMD_MAP` display labels from canonical inverse mapping `_INV_CMD_MAP`, resolving ambiguous names to canonical IDs (`"touch": 10`, `"wait": 11`, `"motion": 4`, `"effect": 20`, `"fade": 0`) instead of dictionary-comprehension last-wins (`touch` no longer maps to voice cue 12).
  - Maintained permanent invariant (Lead Ruling (a)): `cmd_id == 35` (`tag` narration) and `cmd_id == 32` (`cmd_32` subtitle) preserved byte-exact across all serialization paths.
  - Preserved backward compatibility for `DEFAULT_BREAKERS = ("touch", "page", "next_page")` while defining dedicated `DEFAULT_BREAKER_IDS = frozenset({0, 1, 4, 10, 36})` (`0=title`, `1=outline`, `4=type`, `10=goto`, `36=situation`).
  - Updated `_rebuild_boxes()` to classify breakers by numeric ID `r.cmd_id in DEFAULT_BREAKER_IDS`, never splitting on voice cue `cmd_id == 12` and cleanly preserving dialogue projection `cmd_id == 6`.
- **BUG-09 (`core/bundle_io.py:save_bundle_story()`):**
  - Implemented pre-save non-target object SHA-256 hash capture keyed by `(assets_file_name, path_id)` (or `path_id`).
  - Enforced verification check in `env_check` comparing raw data hashes and tracking `seen_non_target_keys`. Raises `BundleIOError` if any non-target object is modified, missing, or unexpectedly present before `os.replace()`.
  - Production Bundle Fixture Status: **`BLOCKED (no local production .unity3d fixture)`** (retained honestly, never fabricated).
- **Test Suite:** Added `tests/test_p3_s03_binary_v2.py` with 6 Defect Probes (failing-first) and 3 Regression Guards (passing). Full test suite discovered count: 248 tests across 25 modules (208 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/bundle_io.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s03_binary_v2.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/script_codec.py`, `core/undo_journal.py`, `core/search_engine.py`, `assets/*.py`.

### S02 — Test `backups/` Isolation, `search_engine.py` `Any` Import & Single-Version DeepL User-Agent
- **Session Scope:** HYG-02, HYG-05, HYG-06 (Track 1 · Group A).
- **HYG-05 (`core/search_engine.py`):** Added `Any` and `Dict` to `from typing import ...` so runtime `typing.get_type_hints(ProjectSearchEngine.search_directory)` resolves cleanly without `NameError`.
- **HYG-06 (`core/mtl_engine.py`):** Replaced hardcoded `Misora-Story-Editor/1.3` User-Agent strings in `_translate_deepl()` and `_test_deepl_usage()` with dynamic `f"Misora-Story-Editor/{APP_VERSION}"` read from single version source in root `__init__.py`. Verified no circular import of `misora.py` occurs in an isolated process. Root `__version__ = "1.4.0"` preserved untouched.
- **HYG-02 (`tests/*.py`):** Redirected `app.backup_folder = str(self.tmp_dir / "backups")` in `setUp()` and cleaned up in `tearDown()` across all UI/save/replace test modules (`test_misora_ui_integration.py`, `test_phase1_manual_verification.py`, `test_phase2_required.py`, `test_phase3_performance_config.py`, `test_phase4_import_export_preview.py`, `test_phase5_mtl_security_preview.py`, `test_s1_open_file_safety.py`, `test_s2_dirty_contract.py`, `test_s3_document_close.py`, `test_s5_bulk_replace_safety.py`, `test_s6_threading_decoupling.py`, `test_s7_undo_speaker_safety.py`, `test_s8a_dialog_grab_safety.py`, `test_s8b1_notification_manager.py`, `test_s8b2_memory_guards.py`, `test_s8b3_encoding_detection.py`, `test_s8b4_ui_polishing.py`, `test_s9b_replace_all_bundle_safety.py`, `test_s9c_workspace_safety.py`). Verified full discovery run generates zero new files in repo root `backups/`.
- **Test Suite:** Added `tests/test_p3_s02_hygiene.py` with 3 Defect Probes (failing-first) and 2 Regression Guards (passing). Full test suite discovered count: 239 tests (199 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/search_engine.py`, `core/mtl_engine.py`, `tests/*.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s02_hygiene.py`.
- **Forbidden Files Untouched:** `misora.py`, `__init__.py`, `core/story_ast.py`, `core/bundle_io.py`, `assets/*.py`.

### S01 — Docs, Ledger & AGENTS.md Reconciliation
- **Session Scope:** HYG-01 (Track 1 · Group A (DEP-10)).
- **Reconciliation Baseline:** Reconciled `PROJECT_STATE.md`, `README.md`, and `AGENTS.md` against pinned starting commit `683724edaf2afac89d2695a80e30a471a0da9195`.
- **Defect Ledger Downgrades:** Downgraded 12 contradicted `RESOLVED` slugs to `REOPENED` with canonical Phase 2.5 IDs:
  - `CMD0-SPECIAL-CASE` $\rightarrow$ `BUG-03`
  - `V2-ROUNDTRIP-LOSS` $\rightarrow$ `BUG-03`
  - `FIND-REPLACE-UI-ASYMMETRY` $\rightarrow$ `BUG-38`
  - `CONTINUOUS-RIBBON-TARGET-STALE` $\rightarrow$ `BUG-28`
  - `SIZE-RIBBON-NO-COMMIT` $\rightarrow$ `BUG-28`
  - `TRANSLATION-LOCK` $\rightarrow$ `BUG-12 / BUG-16`
  - `CTRL-ALT-HOTKEYS-BLOCKED` $\rightarrow$ `BUG-29`
  - `BOX0-NO-SELECT-CHECKBOX` $\rightarrow$ `BUG-41`
  - `PLAINTEXT-SAVE-ROUTING` $\rightarrow$ `BUG-11`
  - `GAME-BOX-PREVIEW` $\rightarrow$ `FEAT-09 / FEAT-10`
  - `MULTI-TEXTASSET-TARGET` $\rightarrow$ `BUG-09 / DEF-03`
  - `API-KEYS-PLAINTEXT` $\rightarrow$ `BUG-33`
  Historical progress records and resolution notes preserved intact.
- **Test Arithmetic & Naming Fixes:** Corrected §2 test suite arithmetic from 238 to actual disk count 234 across 23 test modules; fixed test filenames for `test_s8b2_memory_guards.py` and `test_s8b3_encoding_detection.py`.
- **Reference Provenance & Exclusions:** Recorded audit provenance for `Phase_1_Gemini.md`, `Phase_1_Claude.md`, and `Phase_2R1_Claude.md`. Recorded intentional removal and `.gitignore` exclusion of local `docs/` and `storydata_1001005.unity3d`.
- **Invariants & Safety Rules:** Updated `AGENTS.md` to document pixel-calibrated length measurement, shipped CSIF format, native overflow rule (50 digit-widths without a linebreak OR 3 or more linebreaks / 4+ lines), MTL drawer gating (Track 1 S01..S13), and machine-verified `Ctrl+H` status.
- **Environment Status:** Observed baseline: 234 unit tests (194 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `PROJECT_STATE.md`, `README.md`, `AGENTS.md`.
- **Files Created:** `CHANGELOG.md`.
- **Code Modifications:** None (zero `.py` files changed; `__version__ = "1.4.0"` untouched).
