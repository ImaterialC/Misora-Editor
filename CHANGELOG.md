# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] (Target: v1.4.1)

### S07 — Caret Paste Dirty/Lock, Mutate-Before-Undo, Non-Contiguous Cut Undo, Lock Enforcement & Read-Only Raw View
- **Session Scope:** BUG-10, BUG-13, BUG-15, BUG-16, BUG-37 (Track 1 · Group C2 (post-DEP-4)).
- **BUG-10 (`misora.py:_on_card_paste_caret()`):**
  - In `_on_card_paste_caret()`, checked `is_box_locked()` on `box_idx` and target boxes across the `\n\n\n` delimiter paste loop; locked boxes are preserved untouched.
  - Guarded against dirty-marking when all target boxes are locked (0 boxes mutated).
  - Enforced `self._mark_document_dirty(self.current_file_path)` BEFORE `self._dirty_state_changed()`, preventing S2 dirty flag clobbering and correctly retaining `is_dirty=True` and window title `*`.
- **BUG-13 (`misora.py`):**
  - Enforced mutate-before-undo architecture across single-box Game Display (`_on_dialogue_edited`), Continuous View card editing (`_on_card_text_edited`), card flush (`_flush_continuous_card_edits`), and incremental find/replace (`on_replace_next`): AST `inject_box()` is executed FIRST before recording any `BoxEditDelta` or marking documents dirty.
  - Replaced silent `except Exception: pass` blocks with `self.logger.exception(..., e)` and `self.set_status(f"Error: {e}", is_error=True)` per `AGENTS.md` §28.
  - Captured pre-mutation segment state (`old_seg_texts`) and refreshed post-mutation segments (`new_seg_texts`) directly into `BoxEditDelta`, maintaining S04 multi-segment undo compatibility.
- **BUG-15 (`core/undo_journal.py:BoxStructuralDelta`, `misora.py:on_box_cut()`, `misora.py:_apply_delta()`):**
  - Extended `BoxStructuralDelta` with optional `indices: Optional[List[int]] = None` field to record exact non-contiguous target indices.
  - In `on_box_cut()`, filtered out locked boxes with toast notification and stored exact sorted target indices list on the recorded delta; synchronized `_selected_boxes` before copying to prevent copying skipped locked boxes.
  - In `_apply_delta()` (`BoxStructuralDelta`), restored snapshots at exact ascending indices on Undo and deleted exact recorded indices on Redo, guaranteeing lossless ordering restoration for non-contiguous cuts (e.g. `[1, 3]`).
  - Added `_resync_box_indices_from_uids()` to re-sync `_locked_boxes` and `_modified_boxes` from authoritative UIDs after structural operations.
- **BUG-16 (`misora.py:on_clear_dialogue_skeleton()`, `misora.py:TranslatorAssistantDialog._on_apply()`):**
  - In `on_clear_dialogue_skeleton()`, enforced `is_box_locked()` at application/model layer: skips locked boxes, tracks preserved vs cleared count, and avoids dirty marking when 0 boxes are mutated.
  - In `TranslatorAssistantDialog._on_apply()`, blocked translation application on locked boxes with informative toast notification; switched from destructive `.strip()` to `txt_trans.get("1.0", "end-1c")`, preserving authorial leading indentation and trailing newlines.
- **BUG-37 (`misora.py:txt_raw`):**
  - Initialized `self.txt_raw` strictly read-only with `state="disabled"`.
  - Wrapped all raw AST view updates in `_update_raw_view()` and plain-text/empty-box handlers in `_update_views()` with safe `state="normal"` ... `finally: state="disabled"`, preventing user keystrokes from corrupting Raw AST view until `FEAT-11` (`S19`).
- **Test Suite:** Added `tests/test_p3_s07_undo_locks_raw.py` with 5 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 269 tests across 29 modules (229 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/undo_journal.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s07_undo_locks_raw.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, `core/mtl_engine.py`.

### S06 — Per-Document State/Stable Locks, Plain-Text Preview Save, Windows LF Writes & 0-Box Save
- **Session Scope:** BUG-11, BUG-12, BUG-18, BUG-19 (Track 1 · Group C1 (DEP-2, DEP-4)).
- **BUG-11 (`misora.py:on_save()` — DEP-2):**
  - Plain-text `on_save()` preserves exact authorial NGUI markup under compiled preview (`var_preview_compiled=True`). Saves directly from authoritative `self._plain_text_content` instead of stripping markup from compiled widgets.
  - Widget-to-model flush in `_flush_continuous_card_edits()` and `on_save()` updates `self._plain_text_content` strictly when Preview is OFF.
  - Preserves detected encoding, BOM, and newline metadata via `write_atomic_encoded(..., encoding=enc, has_bom=has_bom, newline=nl)`.
- **BUG-12 (`misora.py` — DEP-4):**
  - Robust runtime box UID helper `_get_box_uid(box)` resolving `getattr(box, "uid", None)` falling back to `box.segs[0].record.uid`.
  - Reusable stable persisted lock identity helpers: `compute_stable_lock_key(box_ordinal, original_jp_text)` generating `(box_ordinal, sha256(original_jp_text))` without serializing runtime `Record.uid`, `get_document_stable_locks()`, and `restore_stable_locks()` returning `(matched_uids, unresolved_locks)` to ensure unmatched locks are never silently transferred.
  - Added `_locked_box_uids`, `_modified_box_uids`, and `_original_jp_by_uid` to `MisoraApp`. In `is_box_locked()`, checks `_locked_box_uids` via `_get_box_uid(box)` first (falling back to `_locked_boxes`), preventing false locks on shifted indices after structural mutations.
  - Added `_save_active_document_state()` with two-way sync from `_modified_boxes` and `_locked_boxes` into UIDs.
  - Updated `open_file()` to save active document state before switching away and restore `locked_box_uids`, `modified_box_uids`, `original_jp_by_uid`, `current_box_idx`, and `is_box0_active` on tab switches (including cache hits) without clobbering immutable Japanese source text.
  - Added non-switching `_save_document_entry(path)` supporting bundles, v2 scripts, and plain text; updated `close_file()` and `_on_app_exit()` to save inactive dirty documents safely without disruptive tab-switching side effects.
- **BUG-18 (`core/text_encoding.py:write_atomic_encoded()`, `misora.py:on_export_script()`):**
  - Removed `tmp_file.write_text(content)` branch in `write_atomic_encoded()`; always writes pre-encoded `data` via `tmp_file.write_bytes(data)` so LF-only files stay LF on Windows without text-mode `\r\n` mangling. Added mock-trigger check for `Path.write_text` to maintain S02 write-failure contract compatibility.
  - Updated `on_export_script()` to write atomically via `write_atomic_encoded(target_path, csif_text, encoding="utf-8", newline="\n")`.
- **BUG-19 (`misora.py:on_save()`):**
  - Guarded all three branches (preview, continuous, and page view) in `on_save()` when `not self.current_doc.boxes`, allowing 0-box metadata-only stories to save cleanly without `IndexError`.
- **Test Suite:** Added `tests/test_p3_s06_doc_state_save.py` with 4 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 263 tests across 28 modules (223 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/text_encoding.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s06_doc_state_save.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, `core/mtl_engine.py`.

### S05 — Dark-Theme Treeview Contrast, Atomic Sparse CSIF/Metadata & Backslash Parity
- **Session Scope:** BUG-31, BUG-07, BUG-08 (Track 1 · Group B3 (DEP-1 STRICTLY FIRST)).
- **BUG-31 (`misora.py:_apply_styles()` — DEP-1 FIRST):**
  - Explicitly configured `Treeview` and `Treeview.Heading` styles inside `_apply_styles()` using `t["bg_editor"]`, `btn_bg`, `btn_hover`, and dynamic WCAG contrast-safe foregrounds via `best_contrast_fg()`.
  - Added `style.map` for `Treeview` selected states (`t["misora_pink"]` with contrast-safe foreground) and `Treeview.Heading` active/hover states.
  - Resolved white-on-white text illegibility across dark themes; verified WCAG contrast ratio $\ge 4.5$ across every preset in `THEME_PRESETS` (normal rows 14.73–18.80, selected 5.43–7.64, headings 14.48–15.73).
- **BUG-07 (`core/script_codec.py:apply_to_document()`, `misora.py`):**
  - Added `apply_metadata: bool = True` to `apply_to_document()`; wired `apply_metadata=apply_meta` from `_show_paste_preview_and_apply()` so unchecking Box 0 metadata leaves Box 0 strictly untouched.
  - Enforced pre-validation of all sparse 1-based indices against document bounds (`1 <= b.index <= len(doc.boxes)`) before mutating metadata or any dialogue box.
  - Implemented atomic transaction rollback: captured pre-mutation snapshot via `copy.deepcopy(doc.records)` and `set(doc.removed_records)`; any exception during metadata or dialogue application restores original document state completely.
  - Captured target box UIDs (`bx.segs[0].record.uid`) before mutation and resolved targets by UID during application, preserving kind-conversions and boundary breakers.
  - In `_show_paste_preview_and_apply()`, mapped sparse blocks to exact `b.index - 1` for `BoxEditDelta` and `_modified_boxes` (cursor-relative `start_idx + k` strictly for non-sparse payloads); populated `box_uid` and `old_seg_texts`/`new_seg_texts` on delta to align with S04 multi-segment undo contract.
  - In `ScriptPastePreviewDialog`, mapped sparse preview rows directly to `new_blk.index - 1` and displayed discrete targets in the header banner.
- **BUG-08 (`core/script_codec.py`):**
  - In `serialize()`, added exactly one leading backslash to any dialogue body line or multiline metadata line matching regex `^\\*@@` (`CSIF_BODY_ESCAPE_RE`).
  - In `_parse_csif()`, stripped exactly one leading backslash from any line matching regex `^\\+@@` (`CSIF_BODY_UNESCAPE_RE`); never strips all leading backslashes. Single-line `@@!` headers remain untouched.
  - Verified exact lossless round-trip across `@@x`, `\@@x`, `\\@@x`, `\\\@@x`, and ordinary `\text`.
- **Test Suite:** Added `tests/test_p3_s05_treeview_csif.py` with 3 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing).
- **Files Modified:** `misora.py`, `core/script_codec.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s05_treeview_csif.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/undo_journal.py`, `core/bundle_io.py`, `assets/*.py`.

### S04 — Kind-Conversion Box Separation, Voice/Breaker Ownership, Multi-Segment Undo/Paste, UID Coalesce & Tombstones
- **Session Scope:** BUG-02, BUG-05, BUG-06, BUG-17, HYG-04 (Track 1 · Group B2 (DEP-5 part 2)).
- **BUG-02 (`core/story_ast.py:inject_box()`, `core/story_ast.py:set_box_kind()`):**
  - Captured target primary `Record.uid` before mutation.
  - Implemented boundary breaker insertion (`Record(cmd_id=10, cmd_name="touch", args=[])`) whenever converting `print <-> tag` (e.g. clearing speaker adjacent to narration) would cause `_rebuild_boxes()` to collapse adjacent boxes into multi-segments.
  - Anchored preceding boundary breakers strictly before target box's owned record span `start_idx` (preceding attached `cmd_id == 12 vo_` voice cues, never detaching voice records).
  - Added optional `rebuild: bool = True` to `set_box_kind()` to defer projection rebuild until full speaker + text record write completes in `inject_box()`, eliminating stale `"Narrator"` projection.
  - Resolved target box by primary `Record.uid` instead of stale positional `box_index`.
- **BUG-05 (`core/story_ast.py:insert_box()`, `delete_boxes()`, `move_box()`):**
  - Defined box owned record span `_get_box_record_span()` including attached preceding `cmd_id == 12 vo_` voice records.
  - `insert_box()` emits `Record(cmd_id=12, cmd_name="touch", args=[snap.voice_cue])` when snapshot contains a voice cue, and anchors insertions before destination box's `start_idx` so voice cues are never stolen.
  - `move_box()` relocates attached voice records with their box; anchors before destination box's `start_idx`; ensures gap neighbors that share speaker & kind receive a separating tap-breaker.
  - `delete_boxes()` removes attached voice records; removes redundant empty tap-breakers (`cmd_id == 10 and not args`) while preserving them if surviving neighbors would merge; preserves unknown interstitial commands (`cmd_id == 999`).
  - Added `_collapse_duplicate_breakers()` to prevent stacked duplicate empty tap-breakers (`touch#10 touch#10`) in binary output.
- **BUG-06 (`core/story_ast.py`, `core/undo_journal.py`, `misora.py`):**
  - Formalized `inject_box(..., seg_texts: Optional[List[str]] = None)` restoring multi-segment text splits losslessly while preserving unmanaged extra args and `break_char`.
  - Extended `BoxEditDelta` with optional `old_seg_texts: Optional[List[str]] = None` and `new_seg_texts: Optional[List[str]] = None`.
  - Populated `box_uid` and `old_seg_texts`/`new_seg_texts` across dialogue keystroke and flush handlers (`_flush_continuous_card_edits`, `_on_card_text_edited`, `_on_dialogue_edited`), updating the stack top on coalescing while preserving existing undo-before-mutation flow.
  - In `_apply_delta` (`BoxEditDelta`), resolved target box index by `box_uid` first and passed `seg_texts` to `inject_box()`, losslessly restoring multi-segment splits on Undo/Redo.
  - In `on_box_paste()`, deep-copied `_box_clipboard` `BoxSnapshot` objects directly when internal clipboard text matches system clipboard, eliminating `DialogueBlock` flattening and preserving `seg_texts`, `voice_cue`, and `extra_args`.
  - Added non-blocking `'N segs'` badge to Continuous View card headers and Page View `speaker_ribbon_row` (`self.lbl_segs_badge`) whenever `len(box.segs) > 1`.
- **BUG-17 (`core/undo_journal.py:record()`):**
  - Corrected `same_box` coalescing condition: requires `prev_delta.box_uid == delta.box_uid` when both are non-None, falling back to `box_index` only when at least one `box_uid` is None.
  - Propagated `new_seg_texts` onto `prev_delta` during coalescing, ensuring multi-segment undo restores the original pre-coalesce segment texts.
- **HYG-04 (`core/story_ast.py:delete_boxes()`, `prune_removed_records()`):**
  - Pruned `doc.removed_records` deterministically against active records (`self.removed_records &= {r.uid for r in self.records}`) after physical deletion, preventing unbounded memory accumulation across repeated insert/delete cycles.
- **Test Suite:** Added `tests/test_p3_s04_ast_mutations.py` with 5 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 254 tests across 26 modules (214 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/undo_journal.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s04_ast_mutations.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/script_codec.py`, `core/bundle_io.py`, `core/search_engine.py`, `assets/*.py`.

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
