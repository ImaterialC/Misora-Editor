# Misora Editor — Canonical Project State

Last updated: 2026-11-24
Repository: `ImaterialC/Misora-Editor`
Local working path: `D:\Misora-Editor`
Target release: v1.4.1 (Phase 2.5 Track 1)
Current code baseline: root `__init__.py` reports `version = "1.4.0"`; unified across UI, splash, dialogs, and tests.
Starting baseline pinned at commit `683724edaf2afac89d2695a80e30a471a0da9195`.

This file is the single canonical ledger and roadmap. It replaces legacy variants.
Historical B1–B20 progress is preserved, while defect root-causes, test baselines,
and platform observations reflect direct verification against disk and user-machine tests.

---

## 1. How to use this document

1. Read `AGENTS.md` for permanent invariants.
2. Use the defect ledger below as the canonical baseline.
3. Use stable slugs, not new B-numbers.
4. Classify every item as:
   - CONFIRMED: proven from current code, minimal repro, or user machine test.
   - CONDITIONAL: requires specific fixture or platform evidence to trigger.
   - DESIGN INVARIANT: permanent rule or requirement for future capabilities.
   - RETRACTED: withdrawn claim; do not hunt it again.
5. Do not implement features before Phase 1–2 integrity gates pass.
6. Record test baselines dynamically. Never hardcode a 38/38 claim.

---

## 2. Measured Verification Baseline

```text
OS: Windows 10 / 11 (AMD64)
Python Version: Python 3.12.10
UnityPy Availability: AVAILABLE (installed in Python 3.12 environment)
Pillow Availability: Available
Fixture Availability: storydata_1001005.unity3d intentionally excluded from repository root; local docs/ intentionally removed and excluded via .gitignore.

Compile Check:
py -3.12 -m compileall -q misora.py core assets tests
Result: PASS (Exit code 0, 0 syntax/compilation errors)

Unit Test Suite (S04 Verification Baseline — 2026-11-24):
py -3.12 -m unittest discover -s tests -v
Result: Ran 254 tests across 26 modules (214 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture storydata_1001005.unity3d)

Test suites included in the 254 tests (exact disk discovery):
  tests/test_p3_s04_ast_mutations.py        — 6 S04 AST mutation, voice cue/breaker ownership, multi-segment undo/paste, UID coalesce & tombstone tests (all pass)
  tests/test_p3_s03_binary_v2.py            — 9 S03 strict binary parse, lossless v2, command map/breakers, and synthetic bundle verify tests (all pass)
  tests/test_p3_s02_hygiene.py              — 5 S02 hygiene, single-version User-Agent, and backup isolation tests (all pass)
  tests/test_misora_core.py                 — 20 core AST, binary, search, and sync tests (18 pass, 2 skipped)
  tests/test_misora_ui_integration.py       — 27 UI integration, Box 0, DnD, and editing tests (15 pass, 12 skipped)
  tests/test_phase1_manual_verification.py  — 8 Page and Continuous view verified workflows (all pass)
  tests/test_phase2_required.py             — 13 GUI-level required tests (all pass)
  tests/test_phase3_performance_config.py   — 6 startup, lazy-load, async logger, config tests (all pass)
  tests/test_phase4_import_export_preview.py— 5 import/export, paste preview, tooltip, version tests (all pass)
  tests/test_phase5_mtl_security_preview.py — 7 NGUI tag, DPAPI, TLS verify, DeepL usage, lock, preview tests (all pass)
  tests/test_script_codec.py                — 14 CSIF codec unit tests (all pass)
  tests/test_s1_open_file_safety.py         — 7 staged open-file & multi-format tests (all pass)
  tests/test_s2_dirty_contract.py           — 12 per-document dirty contract tests (all pass)
  tests/test_s3_document_close.py           — 16 clean close & dirty lifecycle tests (all pass)
  tests/test_s4_view_model_sync.py          — 14 dynamic view & ribbon synchronization tests (all pass)
  tests/test_s5_bulk_replace_safety.py      — 8 atomic bulk replace & transaction rollback tests (all pass)
  tests/test_s6_threading_decoupling.py     — 8 background search & worker thread queue tests (all pass)
  tests/test_s7_undo_speaker_safety.py      — 10 speaker commit & undo integrity tests (all pass)
  tests/test_s8a_dialog_grab_safety.py      — 10 modal dialog grab & lifecycle safety tests (all pass)
  tests/test_s8b1_notification_manager.py   — 10 status bar & toast notification tests (all pass)
  tests/test_s8b2_memory_guards.py          — 8 asset disposal & memory leak tests (3 pass, 3 fail, 2 error due to missing root fixture)
  tests/test_s8b3_encoding_detection.py     — 10 encoding detection, BOM & CP932 fallback tests (all pass)
  tests/test_s8b4_ui_polishing.py           — 8 dock collapse, DPI & tooltip tests (all pass)
  tests/test_s9a_search_unicode.py          — 6 Japanese Unicode & combining character search tests (all pass)
  tests/test_s9b_replace_all_bundle_safety.py — 3 bundle replace-all extraction & undo tests (all pass)
  tests/test_s9c_workspace_safety.py        — 4 workspace protection, geometry & undo isolation tests (all pass)
```

### Current Test Environment Blockers
- **Fixture Blockers:** 3 failures and 2 errors in `tests/test_s8b2_memory_guards.py` occur because `storydata_1001005.unity3d` was intentionally excluded from the repository. In addition, 35 tests across `test_misora_core` (2 tests) and `test_misora_ui_integration` (12 tests) report `skipped` when the root fixture is not present. Per `AGENTS.md` §2, missing production fixtures remain environment blockers (`BLOCKED`), never faked or skipped into false passes.

### Reference Audit Provenance & Document Exclusions
- **Reference Dossier Provenance:**
  - `Phase_1_Gemini.md`: Gemini's dossier covering initial Phase 1 codebase review, defect taxonomy, and AST mapping.
  - `Phase_1_Claude.md`: Claude's dossier detailing Phase 1 codebase review, architecture, and candidate fixes.
  - `Phase_2R1_Claude.md`: Valid 22,852-byte technical specification and Phase 2 review.
- **Intentional Removals & `.gitignore` Exclusions:**
  - `docs/`: Local legacy documentation directory intentionally removed and excluded via `.gitignore` to prevent documentation drift.
  - `storydata_1001005.unity3d`: Proprietary binary test fixture intentionally removed from repository root and tracked files; excluded via `.gitignore`.

### S04 Kind-Conversion Box Separation, Voice/Breaker Ownership, Multi-Segment Undo/Paste, UID Coalesce & Tombstones (2026-11-24)
- **Session Scope:** BUG-02, BUG-05, BUG-06, BUG-17, HYG-04 (Track 1 · Group B2 / DEP-5 part 2).
- **BUG-02 (`core/story_ast.py:inject_box()`, `core/story_ast.py:set_box_kind()`):**
  - In `inject_box()` and `set_box_kind()`, target primary `Record.uid` is captured before mutation.
  - Whenever converting `print <-> tag` (e.g. clearing speaker adjacent to narration) would cause adjacent boxes to collapse, minimal valid empty boundary breaker (`Record(cmd_id=10, cmd_name="touch", args=[])`) is inserted before and/or after so they remain separate boxes (Lead Ruling (b) — never implicitly merge).
  - Preceding boundary breaker is inserted strictly before the target box's owned record span (anchored before any attached preceding `cmd_id == 12 vo_` cue, never between voice cue and dialogue).
  - Deferred `_rebuild_boxes()` until after both speaker and dialogue records are updated in `inject_box()`, preventing stale intermediate projections. Target box resolved by captured UID.
- **BUG-05 (`core/story_ast.py:insert_box()`, `core/story_ast.py:delete_boxes()`, `core/story_ast.py:move_box()`):**
  - Unified structural ownership via `_get_box_record_span()`: a `cmd_id == 12` (`vo_...`) record immediately preceding a box's first segment is owned by that box.
  - In `insert_box()` and `move_box()`, insertions before an existing box anchor strictly before that box's owned span (`start_idx`), never stealing the destination box's voice cue.
  - In `move_box()`, the owned voice cue moves with the box; gap neighbors are separated with a boundary breaker if they would merge; duplicate empty breakers are collapsed via `_collapse_duplicate_breakers()`.
  - In `delete_boxes()`, attached voice cue records are deleted; redundant empty tap-breakers (`cmd_id == 10 and not args`) are removed unless surviving neighbors would merge; duplicate breakers are collapsed. Unknown interstitial commands (`cmd_id == 999`) and voice cues belonging to other boxes are strictly preserved.
- **BUG-06 (`core/story_ast.py`, `core/undo_journal.py`, `misora.py`):**
  - Multi-segment editing is non-blocking: allows normal continuous editing on multi-segment boxes.
  - Added small non-blocking `'N segs'` badge to Continuous View card header and Page View `speaker_ribbon_row` (`self.lbl_segs_badge`) configured dynamically in `_sync_clean_view_to_current_box()`.
  - Extended `BoxEditDelta` with `old_seg_texts: Optional[List[str]] = None` and `new_seg_texts: Optional[List[str]] = None`. Populated at dialogue keystroke and flush sites (`_flush_continuous_card_edits`, `_on_card_text_edited`, `_on_dialogue_edited`), propagating `new_seg_texts` to stack-top delta on coalesce.
  - `_apply_delta` (`BoxEditDelta`) resolves target box by `delta.box_uid` first (falling back to `delta.box_index`), restoring original segment splits losslessly via `inject_box(..., seg_texts=...)`.
  - In `on_box_paste()`, deep-copies `_box_clipboard` `BoxSnapshot`s directly when internal clipboard text matches system clipboard, preserving multi-segment structures.
- **BUG-17 (`core/undo_journal.py:MasterUndoJournal.record()`):**
  - Fixed undo coalescing: requires matching `prev_delta.box_uid == delta.box_uid` when both are non-None, preventing edits on different boxes with the same box index from coalescing.
- **HYG-04 (`core/story_ast.py:delete_boxes()`):**
  - Deterministic tombstone pruning against active records (`self.removed_records &= {r.uid for r in self.records}`) upon physical deletion in `delete_boxes()`, eliminating unbounded memory growth while maintaining full compatibility. Added `prune_removed_records()` helper.
- **New Test Suite:** Added `tests/test_p3_s04_ast_mutations.py` with 5 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 254 tests across 26 modules (214 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/undo_journal.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s04_ast_mutations.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/script_codec.py`, `core/bundle_io.py`, `core/search_engine.py`, `assets/*.py`.

### S03 Strict Binary Parse, Lossless v2, Command Map/Breakers & Bundle Verify (2026-11-24)
- **Session Scope:** BUG-01, BUG-03, BUG-04, BUG-09 (Track 1 · Group B1 / DEP-5 part 1).
- **BUG-01 (`core/story_ast.py:from_binary()`, `core/bundle_io.py:load_bundle_story()`):** Enforced strict binary validation on 2-byte header, 4-byte length, payload bytes, and terminating length-0 argument marker; replaced silent `break` with explicit `ValueError` (wrapped as `BundleIOError` in `load_bundle_story()`).
- **BUG-03 (`core/story_ast.py`, `misora.py:_update_raw_view()`):** Removed legacy `cmd_id == 0` remapping in `to_binary()`. Added surrogateescape `\b64:<base64>` emission, category collision prefixing (`\<Cat>`), backslash-first escaping, and trailing/whitespace-only space escaping (`\s` for ASCII space, `\S` for `U+3000`) in `escape_arg()` with lossless reversal in `unescape_arg()`. Fixed dead `Record.render_v2()` check to emit unambiguous `name#id` headers (`touch#10` vs `touch#12`). Fixed `_update_raw_view()` line 6825 to check `len(r.args) > 0 and r.args[0]` matching `get_metadata()`.
- **BUG-04 (`core/story_ast.py`):** Decoupled `_CMD_MAP` display labels from canonical inverse mapping `_INV_CMD_MAP` (resolving `"touch": 10`, `"wait": 11`, `"motion": 4`, `"effect": 20`, `"fade": 0` without last-wins corruption). Maintained permanent invariant (Lead Ruling (a)): `cmd_id == 35` and `cmd_id == 32` untouched byte-exact. Preserved `DEFAULT_BREAKERS = ("touch", "page", "next_page")` for backward compatibility while defining `DEFAULT_BREAKER_IDS = frozenset({0, 1, 4, 10, 36})` (`0=title`, `1=outline`, `4=type`, `10=goto`, `36=situation`); `_rebuild_boxes()` classifies breakers strictly by numeric ID, never splitting on voice cue `cmd_id == 12` and cleanly projecting dialogue `cmd_id == 6`.
- **BUG-09 (`core/bundle_io.py:save_bundle_story()`):** Pre-save SHA-256 capture of non-target objects keyed by `(assets_file_name, path_id)` (or `path_id`) and verified in `env_check` tracking `seen_non_target_keys` to detect modified, dropped, or unexpected objects before `os.replace()`. Production `.unity3d` bundle compatibility status: `BLOCKED (no local production .unity3d fixture)`.
- **New Test Suite:** Added `tests/test_p3_s03_binary_v2.py` with 6 Defect Probes (failing-first) and 3 Regression Guards (passing). Full test suite discovered count: 248 tests across 25 modules (208 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/bundle_io.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s03_binary_v2.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/script_codec.py`, `core/undo_journal.py`, `core/search_engine.py`, `assets/*.py`.

### S02 Hygiene & Single-Source Verification (2026-11-24)
- **Session Scope:** HYG-02, HYG-05, HYG-06 (Track 1 · Group A).
- **HYG-05 (`core/search_engine.py`):** Added `Any` and `Dict` from `typing`, resolving runtime `typing.get_type_hints(ProjectSearchEngine.search_directory)` cleanly without `NameError`.
- **HYG-06 (`core/mtl_engine.py`):** Replaced hardcoded DeepL User-Agent strings (`1.3`) with dynamic `f"Misora-Story-Editor/{APP_VERSION}"` read from single version source in `__init__.py`. Verified no circular import of `misora.py` occurs in an isolated process. `__version__ = "1.4.0"` untouched.
- **HYG-02 (`tests/*.py`):** Redirected `app.backup_folder = str(self.tmp_dir / "backups")` in `setUp()` and cleaned up in `tearDown()` across all UI/save/replace test suites. Confirmed zero new files written to repo root `backups/` across full discovery run (file count remained exactly 936).
- **New Test Suite:** Added `tests/test_p3_s02_hygiene.py` with 3 Defect Probes (failing-first) and 2 Regression Guards (passing).
- **Discovered Test Count:** 239 tests (199 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### S0/S1 Open-File Safety Verification (2026-11-21)
- Pre-edit `misora.py`: 510,461 raw bytes; SHA-256 `2188eab968e031d4d5469f117f3cfb8403dc27622b5b6009d38b3880dd97babe`; LF-normalized 499,293 bytes.
- Exact interpreter: `C:\Users\Cornelia\AppData\Local\Programs\Python\Python312\python.exe`, Python 3.12.10, Windows AMD64.
- Workspace: `D:\Misora-Editor`; branch `main`; HEAD `c3c666ef7c205005091ff7135865376e19e7b991`.
- `misora_config.json` is confirmed untracked and excluded by `.gitignore`.
- Added `.gitattributes` with `*.py text`, `*.bat text eol=crlf`, `*.unity3d binary`, and `*.asset binary`.
- Removed unresolved Git conflict markers from `PROJECT_STATE.md`; no mass line-ending churn occurred.
- `py -3.12 -m compileall -q misora.py core assets tests`: PASS, exit code 0.
- Failing-first focused suite: 5 failures and 1 pass under the unpatched `open_file()` implementation.
- Handover Review & Target A Fix: Resolved critical Continuous View Box 0 synopsis commit routing and widget resolution in `open_file()`, preventing silent document synopsis overwrites and preserving pending edits on file switch.
- Handover Review & Target C Fix: Restored `misora.CONFIG_PATH` in `tests/test_s1_open_file_safety.py:tearDown()`.
- Final focused suite: `py -3.12 -m unittest tests.test_s1_open_file_safety -v`: 7 tests run, 7 pass.
- Final full suite: `py -3.12 -m unittest discover -s tests -v`: 107 tests run, 106 pass, 1 failure, 0 skips.
- The remaining full-suite failure is the local runtime config test described above.

### S1 staged open-file implementation
- `MisoraApp.open_file()` stages bundle, v2, and ordinary text loads in local variables before mutating active state.
- Ordinary text now uses strict UTF-8 decoding; `UnicodeDecodeError`, v2 parse errors, and bundle load errors fail without replacing the active document.
- Cache-hit switches retain the existing cache architecture and flush pending edits only after the target is ready.
- Pending edits are flushed through the explicitly resolved previous editor widget across both Page View and Continuous View (including Card #0 synopsis and dialogue cards), without relying on focus.
- Active state and `open_documents` are committed together only after successful loading or cache resolution.

### S2 Per-Document Dirty Contract & Explicit `on_save() -> bool` (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- `open_documents[path]["dirty"]` is established as the single authoritative unsaved dirty flag per document.
- Flag-only helper `_mark_document_dirty(path)` mutates flags ONLY (`open_documents[p]["dirty"] = True`, mirrors `self.is_dirty = True` if active); contains zero Tk calls and zero dock/title rebuilds, eliminating Rule 13 UNDO-STORM risk and safely handling pre-existing background thread calls.
- Pure-UI `_dirty_state_changed()` mirrors `self.is_dirty` strictly from `open_documents[path]["dirty"]` for open documents; never queries or derives dirty state from global `undo_journal.is_clean()`, completely eliminating the multi-file cross-file false-clean clobber bug.
- True no-op `<KeyRelease>` guards added to dialogue editor (`_on_dialogue_edited() -> bool`) and speaker editor (`_on_speaker_edited()`), preventing navigation keypresses, arrow keys, and unmodified focus changes from dirtying clean documents or triggering premature UI sync.
- Plain-text cache content synchronization (`open_documents[path]["plain_text"]`) enforced across Page View commits, Continuous card commits, pre-switch flushes, and PlainTextDelta undo/redo.
- Deterministic per-document saved-state checkpoint map `_saved_state_checkpoints` stores SHA-256 content hashes (via `doc.to_v2_text()` or plain text) upon save/load, enabling undo-to-clean restoration for each file independently without cross-document interference.
- Uncached / test-only synthetic paths (e.g. `test_34`) gracefully fall back to `undo_journal.is_clean(p)` during undo evaluation when not registered in `open_documents`.
- Explicit `on_save() -> bool` contract: returns `True` strictly on successful primary persistence, `False` on pre-save preparation failure, missing file path, or disk write exception. Outer `try...except` catches all I/O errors and preserves `dirty=True`. Secondary XUAT sync failure logs a warning, retains `_modified_boxes`, and returns `True` (primary save succeeded).
- Pre-existing Rule 15 note: `BatchTranslateDialog.worker()` currently mutates document and UndoJournal state from a background worker thread. S2 uses flag-only `_mark_document_dirty(target_path)` with zero Tk calls and defers the full worker queue redesign to S6.
- Latent defect note: S7 / F20 latent issue noted for `_commit_widget_edit()` speaker branch calling `inject_box(..., None)` (handled safely by AST `inject_box`, full speaker central commit unification deferred to S7).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s2_dirty_contract -v`: 12/12 pass (18.1s).
  - `py -3.12 -m unittest tests.test_s1_open_file_safety -v`: 7/7 pass (10.9s).
  - `py -3.12 -m unittest tests.test_phase2_required -v`: 13/13 pass (37.0s, including `test_34` and `test_39`).
  - `py -3.12 -m unittest discover -s tests -v`: 119 tests run, 118 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips.
- Handoff note: S3 (`close_file()` abort on dirty cancel, `_on_app_exit()` Save-All loop, atomic writer) is now unblocked.

### S3 Safe Document Close & Atomic Persistence (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- Module-level helper `write_atomic_utf8(path, content, encoding="utf-8")` introduces robust atomic write pattern: same-directory `.tmp` write, 5-attempt bounded exponential backoff on Windows file sharing violations (`PermissionError` / `OSError`), and cleanup in `finally`.
- `on_save()` atomic persistence: Replaced direct, non-atomic `Path.write_text()` calls across both plain-text scripts and v2 story scripts (`to_v2_text()`) with `write_atomic_utf8()`, resolving data-loss and file corruption risks during unexpected shutdown.
- Central active widget flush helper `_flush_active_widget() -> bool` extracted and shared between `open_file()`, `close_file()`, and `_on_app_exit()`, ensuring uncommitted keystrokes across dialogue cards, continuous stream, or Box 0 synopsis are reliably committed before dirty evaluation or close.
- Safe `close_file(file_path) -> bool` contract:
  - Aborts immediately and returns `False` if user clicks Cancel on unsaved changes prompt (`messagebox.askyesnocancel`).
  - Aborts and returns `False` if `on_save()` fails during close, preserving document in `open_documents` and preventing memory/data loss.
  - Returns `True` and cleanly removes document from `open_documents`, prunes `self.undo_journal`, and purges `_saved_state_checkpoints` entry upon successful close or user-confirmed Discard.
  - Propagates cancellation cleanly to `close_all_files()`, `close_others()`, and `close_all_unmodified()`.
- Complete multi-document `_on_app_exit()` Save-All loop:
  - Evaluates all open documents for dirty status after flushing active widget.
  - Prompts per-dirty-file (`messagebox.askyesnocancel`) allowing granular Save/Discard/Cancel decisions.
  - Aborts application termination if user chooses Cancel on any document or if `on_save()` fails.
  - Saves user preferences and destroys app cleanly only when all dirty documents have been successfully resolved or discarded.
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s3_document_close -v`: 16/16 pass (17.3s).
  - `py -3.12 -m unittest tests.test_s2_dirty_contract -v`: 12/12 pass (17.9s).
  - `py -3.12 -m unittest tests.test_s1_open_file_safety -v`: 7/7 pass (10.2s).
  - `py -3.12 -m unittest tests.test_phase2_required -v`: 13/13 pass (31.8s).
  - `py -3.12 -m unittest discover -s tests -v`: 135 tests run, 134 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips.
- Handoff note: S4 (View/Model Synchronization & Widget Caret Decoupling) is now unblocked.

### S4 View/Model Synchronization & Widget Caret Decoupling (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **STALE-CARD-REGISTRY (CONFIRMED → RESOLVED)**: `_card_widgets` now pruned in all code paths where the document that produced the cards is unloaded:
  - New `_clear_card_registry()` helper: iterates `_card_widgets`, destroys any live card frames with `winfo_exists()` guard, then calls `_card_widgets.clear()`. Safe to call with already-destroyed widgets.
  - `close_file()` empty-state branch (no open documents remain): calls `_clear_card_registry()` before `_update_views()`.
  - `_update_views()` `not self.current_doc` branch (plain-text switch or empty state): calls `_clear_card_registry()` as first action before resetting any other view state.
  - `_render_continuous_view()` already called `self._card_widgets.clear()` at render start (inside `try:`) for the bundle→bundle case — left unchanged (correct).
- **Ribbon stale-widget guard**: New `_get_card_text_widget(box_idx) -> tk.Text` helper performs `winfo_exists()` check on the registered card Text widget before returning it, falling back to `txt_dialogue` on stale or absent entries. Used in `on_text_cut()`, `on_text_copy()`, `on_text_paste()` replacing the unguarded `_card_widgets[idx].get("txt", self.txt_dialogue)` pattern.
- **Re-entrancy guard verified**: `_render_continuous_view()` already wraps `_suppress_continuous_events = True` in `try/finally` — no code change required; invariant verified by test_06.
- **Focus / caret safety verified**: `_focus_continuous_box()` already guards missing `target_idx` with `if target_idx in self._card_widgets` — no code change required; invariant verified by test_07/07b.
- **Suppress-guard verified**: `_on_card_focus_in()` and `_on_card_text_edited()` already guard with `_suppress_continuous_events` — no code change required; invariants verified by test_08/08b.
- **View toggle caret preservation verified**: `_on_toggle_continuous_view()` preserves `current_box_idx` on both directions — no code change required; verified by test_03/04.
- New test file: `tests/test_s4_view_model_sync.py` — 14 tests (8 planned + 6 parametric sub-cases).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s4_view_model_sync -v`: 14/14 pass (0.5s).
  - `py -3.12 -m unittest discover -s tests -v`: 149 tests run, 148 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (194.3s).
- Handoff note: S5 (Multi-File Replace-All & BulkFileDelta Disk Safety) is complete.

### S5 Multi-File Replace-All & BulkFileDelta Disk Safety (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **BULK-DELTA-NONATOMIC (CONFIRMED → RESOLVED)**:
  - Replaced raw, non-atomic `fpath.write_text()` in `on_replace_all()` and `fp.write_text()` in `_apply_delta()` (`BulkFileDelta` branch) with shared `write_atomic_utf8()` helper (same-dir `.tmp` -> bounded Windows retry `os.replace()`), eliminating risk of truncated/corrupted files during unexpected termination or sharing violations.
- **Transaction Rollback**:
  - Implemented all-or-nothing transactional tracking in `_apply_delta(BulkFileDelta)`: if an error occurs while applying changes to any file in a batch, all previously applied files in that batch are automatically rolled back to their prior state via `write_atomic_utf8()`, alerting the user with an error dialog and re-raising to maintain journal consistency.
- **In-Memory Cache & Checkpoint Synchronization**:
  - Both `on_replace_all()` and `_apply_delta(BulkFileDelta)` synchronize `open_documents[fp]["plain_text"]` and `_saved_state_checkpoints` for all open files modified in the batch, preventing subsequent tab switches or saves from overwriting disk modifications with stale cache data.
  - Enhanced `_evaluate_checkpoints_for_op(op)` to inspect `delta.per_file` for `BulkFileDelta`, accurately clearing dirty state when files are undone back to their checkpoint fingerprint.
- New test file: `tests/test_s5_bulk_replace_safety.py` — 8 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s5_bulk_replace_safety -v`: 8/8 pass (0.3s).
  - `py -3.12 -m unittest tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 62/62 pass (71.0s).
  - `py -3.12 -m unittest discover -s tests -v`: 157 tests run, 156 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (224.1s).
- Handoff note: S6 (Threading Architecture Decoupling - Rule 15) is complete.

### S6 Threading Architecture Decoupling — Rule 15 (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **SEARCH-RACE (CONFIRMED → RESOLVED)**:
  - `on_start_search()` captures an independent immutable snapshot of every open in-memory `StoryDocument` on the UI thread before background worker thread delegation. Search iterations run strictly on detached copies, preventing concurrent editing, box additions, or box deletions on the UI thread from causing collection-mutation races.
- **BatchTranslateDialog Queue Decoupling (Rule 15)**:
  - Re-architected `BatchTranslateDialog.worker()` to eliminate direct mutations to `StoryDocument` and `MasterUndoJournal`, and eliminated cross-thread Tkinter calls (`self.after_idle`).
  - Background worker thread only handles translation I/O (`engine.translate`), posting translation result and error tuples through `self.worker_queue = queue.Queue()`.
  - Main UI thread polls the queue via `_poll_worker_queue()` (`self.after(50, ...)`), applying AST injections (`doc.inject_box`), recording undo deltas (`undo_journal.record`), and updating progress strictly on the main thread.
  - Safe lifecycle management: `_on_close()` and `_start_batch()` guarantee matching `undo_journal.end_batch()` calls even upon cancellation or window close.
- New test file: `tests/test_s6_threading_decoupling.py` — 8 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s6_threading_decoupling -v`: 8/8 pass (6.3s).
  - `py -3.12 -m unittest tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 70/70 pass (67.4s).
  - `py -3.12 -m unittest discover -s tests -v`: 165 tests run, 164 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (179.4s).
- Handoff note: S7 (Per-File MasterUndoJournal Revision Rewrite & Speaker Commit Unification) is complete.

### S7 Per-File MasterUndoJournal Revision Rewrite & Speaker Commit Unification (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Per-File MasterUndoJournal Revision Rewrite (F16 / Rule 13 / Rule 16)**:
  - Re-architected `MasterUndoJournal` with internal `_FileJournalState` encapsulation: independent `undo_stack`, `redo_stack`, `revision`, and `saved_revision` per file path.
  - Windows path normalization helper `_norm_path` ensures consistent case-insensitive mapping.
  - `set_active_file()` synchronizes active document context from `open_file()` and `close_file()`.
  - Calling `on_undo()` or `on_redo()` operates strictly on the active file's isolated journal stack; undoing in File B never switches to File A or clobbers File A's edits.
  - Document close via `close_file()` calls `prune_file(file_path)` which completely purges that file's journal state, ensuring undo never silently reopens closed files (Rule 16).
  - Edit menu states and labels (`can_undo()`, `undo_label()`, `can_redo()`, `redo_label()`) dynamically synchronize to the active file.
  - Full backward-compatibility: zero-argument calls (`pop_undo()`, `can_undo()`, `is_clean()`, `mark_saved()`, `undo_depth`, `redo_depth`) operate seamlessly on the active or default context.
- **Central Speaker Edit Commit Unification (F20 / Rule 11)**:
  - Eliminated the critical latent defect in `_commit_widget_edit()` where the speaker branch called `inject_box(self.current_box_idx, new_sp, None)` (which raised `AttributeError: 'NoneType' object has no attribute 'rstrip'` on multi-segment boxes and corrupted binary record args on single-segment boxes).
  - Introduced central helper `_commit_speaker_edit() -> bool` that resolves current dialogue text from the active view widget (`_card_widgets[idx]["txt"]`, `txt_dialogue`, or `box.clean_text`), always passing valid text to `inject_box`.
  - Unified `_on_speaker_edited()`, `_commit_widget_edit(self.entry_speaker)`, and `entry_speaker` virtual events (`<<Cut>>`/`<<Paste>>`) to delegate to `_commit_speaker_edit()`.
  - Added Box 0 protection (aborts immediately when `is_box0_active` is True) and true no-op `<KeyRelease>` guard (`old_sp == new_sp` returns `False` without marking dirty or recording deltas).
- New test file: `tests/test_s7_undo_speaker_safety.py` — 10 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s7_undo_speaker_safety -v`: 10/10 pass (7.5s).
  - `py -3.12 -m unittest tests.test_s7_undo_speaker_safety tests.test_s6_threading_decoupling tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 88/88 pass (90.9s).
  - `py -3.12 -m unittest discover -s tests -v`: 175 tests run, 174 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (189.6s).
- Handoff note: S8a (Dialog Architecture & Modal Grab Hardening) is complete.

### S8a Dialog Architecture & Modal Grab Hardening (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Modal Grab Safety Helper (`safe_grab_release`)**:
  - Implemented module-level `safe_grab_release(dialog)` helper guarded with `dialog and dialog.winfo_exists()` to safely call `dialog.grab_release()` inside a `try...except tk.TclError: pass` block.
  - Safely handles `None`, destroyed widgets, and active grabs without raising exceptions, preventing Windows Tkinter orphan grab deadlocks.
- **Audit & Hardening of All Modal Dialogs**:
  - **`_on_dnd_settings_dialog`**: Added `_safe_close()`, wired `WM_DELETE_WINDOW` protocol, `<Escape>` binding, and grab release in save handler.
  - **`_prompt_append_speaker_attribute`**: Added `_safe_close()`, wired `WM_DELETE_WINDOW`, `<Escape>`, and grab release on commit.
  - **`on_insert_ruby`**: Added `_safe_close()`, wired `WM_DELETE_WINDOW`, `<Escape>`, grab release on insert, and aliased `_prompt_insert_ruby = on_insert_ruby`.
  - **`on_launch_datamine`**: Wired `safe_grab_release(dlg)` in `_cancel()` and `_ok()`, wired `WM_DELETE_WINDOW`, and bound `<Escape>`.
  - **`on_open_paths_dialog`**: Added `_safe_close()`, wired `WM_DELETE_WINDOW`, `<Escape>`, Cancel button, and grab release in `_save_and_close()`.
  - **`ScriptPastePreviewDialog`**: Hardened `on_apply()` and `on_cancel()` with `safe_grab_release(self)`, wired `WM_DELETE_WINDOW` and `<Escape>`.
  - **`MTLSettingsDialog`**:
    - Replaced 13 unparented Tk variables with explicit `master=self` (`var_engine`, `var_src`, `var_tgt`, `var_deepl_key`, `var_show_key`, `var_deepl_pro`, `var_local_url`, `var_llm_url`, `var_llm_model`, `var_llm_key`, `var_protect`, `var_xuat_cache`, `var_timeout`) fulfilling Rule 3.
    - Added `_on_cancel()`, wired `WM_DELETE_WINDOW`, `<Escape>`, Cancel button, and grab release in `_on_save()`.
  - **`AIPromptSettingsDialog`**:
    - Added explicit `master=self` to `var_include_hdr` and `var_include_spk` (Rule 3).
    - Added `_on_cancel()`, wired `WM_DELETE_WINDOW`, `<Escape>`, Cancel button, and grab release in `_save_and_close()`.
  - **`TranslatorAssistantDialog`**:
    - Added explicit `master=self` to `var_engine` (Rule 3).
    - Hardened `_on_close()` with `safe_grab_release(self)` and `winfo_exists()` guard; wired `<Escape>` and Close button.
  - **`BatchTranslateDialog`**:
    - Added explicit `master=self` to `var_engine`, `var_scope`, and `var_delay` (Rule 3).
    - Hardened `_on_close()` to cancel background thread, cleanly end undo batch, and call `safe_grab_release(self)` before destruction.
    - Wired `WM_DELETE_WINDOW` protocol and `<Escape>` binding.
- New test file: `tests/test_s8a_dialog_grab_safety.py` — 10 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s8a_dialog_grab_safety -v`: 10/10 pass (10.8s).
  - `py -3.12 -m unittest tests.test_s8a_dialog_grab_safety tests.test_s7_undo_speaker_safety tests.test_s6_threading_decoupling tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety -v`: 85/85 pass (43.9s).
  - `py -3.12 -m unittest discover -s tests -v`: 185 tests run, 184 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (164.5s).
- Handoff note: S8b-1 (Status-Bar & Toast Notification Manager) is complete.

### S8b-1 Status-Bar & Toast Notification Manager (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Status Bar Management (`set_status`, `_reset_status`)**:
  - Implemented `set_status(message, is_error=False, timeout_ms=None)` with `winfo_exists()` guards, cancelling existing timeout timers before updating text.
  - Distinctive contrast error styling: `#d94862` (Crimson Alert) for errors vs `fg_muted` for normal status.
  - Optional auto-reset timer restoring `lbl_status` to `_default_status_text` after `timeout_ms`.
  - Added `_reset_status()` helper to safely restore default label text and normal styling.
- **Toast Notification Architecture (`show_toast`, `_display_toast`, `_dismiss_toast`)**:
  - Maintained 100% backward-compatibility for all existing `show_toast(message, ...)` callers across `misora.py`.
  - Enabled status-bar synchronization by default (`status_bar=True`), mirroring toast notifications to the persistent status bar.
  - Sequential FIFO toast queue (`_toast_queue = collections.deque()`) prevents rapid notifications from clobbering each other; accelerates duration if queue backlog > 2.
  - Coalesces consecutive duplicate toast messages by resetting duration timer rather than bloating queue.
  - Interactive click-to-dismiss (`<Button-1>`) immediately unmaps active toast and advances queue.
  - Fixed geometric occlusion: positioned toast at `relx=1.0, rely=1.0, x=-16, y=-52, anchor="se"` floating ~12-16px cleanly above the action bar without obscuring `Save & Patch Bundle` or `Revert Box` buttons.
- **Callback Exception Surfacing (Rule 28)**:
  - Updated `report_callback_exception()` to surface both a status bar error (`set_status(f"Error: {val}", is_error=True)`) and a prominent error toast (`show_toast(f"Error: {val}", duration_ms=4000, is_accent=False, is_error=True, status_bar=False)`).
- **Teardown & Timer Safety**:
  - `destroy()` and `_on_root_destroy()` cancel `_toast_after_id` and `_status_after_id`, clear `_toast_queue`, destroy `_toast_widget`, and cancel all dangling `after()` jobs, eliminating Tcl teardown error `invalid command name "...hide" ("after" script)`.
- New test file: `tests/test_s8b1_notification_manager.py` — 10 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s8b1_notification_manager -v`: 10/10 pass (11.5s).
  - `py -3.12 -m unittest tests.test_s8b1_notification_manager tests.test_s8a_dialog_grab_safety tests.test_s7_undo_speaker_safety tests.test_s6_threading_decoupling tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 108/108 pass (75.6s).
  - `py -3.12 -m unittest discover -s tests -v`: 195 tests run, 194 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (168.0s).
- Handoff note: S8b-2 (Asset & Bundle Memory Leak Guards) is complete.

### S8b-2 Asset & Bundle Memory Leak Guards (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **UnityPy Environment Cycle-Breaking Disposal (`dispose_unity_env`)**:
  - Identified and resolved the critical multi-layered circular reference cycles in UnityPy (`Environment <-> BundleFile <-> SerializedFile <-> ObjectReader`) that previously prevented Python's reference counting from reclaiming loaded bundle buffers without cyclic GC.
  - Implemented `dispose_unity_env(env)` in `core/bundle_io.py` (re-exported in `core/__init__.py`), explicitly clearing `env.files`, `env.assets`, `env.cabs`, `env.container`, nullifying `reader` buffers, and unlinking all cross-environment back-references.
  - Verified with `weakref.ref(env)`: refcount drops to 0 immediately upon disposal, freeing memory buffers without delay.
- **Search Engine & Replace-All Leak Prevention**:
  - In `core/search_engine.py:search_file()`: Disposes the loaded `env` immediately after extracting the pure AST `StoryDocument`, preventing project searches across 100+ bundles from retaining megabytes of leaked environments in RAM.
  - In `misora.py:on_replace_all()`: Wraps bundle modifications in `try...finally: dispose_unity_env(bundle_env)`, ensuring each matched bundle's environment is cleanly released as the replacement loop proceeds across folders.
  - In `core/bundle_io.py:save_bundle_story()`: Wraps repacked verification check environment (`env_check`) in `try...finally: dispose_unity_env(env_check)`, preventing every save from leaking verification environments.
- **Document Close & App Teardown Lifecycle Disposal**:
  - In `misora.py:close_file()`: Retrieves `closed_env = self.open_documents[file_path].get("env")` and calls `dispose_unity_env(closed_env)` before dictionary deletion; clears and disposes `self.current_unity_env = None`.
  - In `misora.py:destroy()`: Sweeps and disposes all remaining environments in `self.open_documents`, disposes `self.current_unity_env`, and calls `prune_icon_cache(self)`.
- **Bounded Icon & PhotoImage Cache (`assets/icon.py`)**:
  - Enforced `MAX_ICON_CACHE = 128` capacity bounding via FIFO eviction in `get_icon()`.
  - Added `prune_icon_cache(root_widget=None)` helper to evict stale icons belonging to destroyed `tk.Toplevel` dialogs and purge unreferenced Tcl photo images.
  - In `NguiColorPickerPopup._on_close()`: Resets `self.app._color_picker_win = None` and nullifies canvas photo attributes (`_sv_photo`, `_hue_photo`, `_grad_photo`).
- New test file: `tests/test_s8b2_memory_guards.py` — 8 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s8b2_memory_guards -v`: 8/8 pass (10.7s).
  - `py -3.12 -m unittest tests.test_s8b2_memory_guards tests.test_s8b1_notification_manager tests.test_s8a_dialog_grab_safety tests.test_s7_undo_speaker_safety tests.test_s6_threading_decoupling tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 116/116 pass (86.5s).
  - `py -3.12 -m unittest discover -s tests -v`: 203 tests run, 202 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (192.1s).
- Handoff note: S8b-3 (Encoding Detection & Strict Fallback Architecture) is now complete; S8b-4 is unblocked.

### S8b-3 Encoding Detection & Strict Fallback Architecture (2026-11-22)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Centralized Text Encoding Engine (`core/text_encoding.py`)**:
  - Implemented immutable `DecodedText` dataclass (`text`, `encoding`, `has_bom`, `newline`, `bom_bytes`).
  - Implemented `detect_encoding_and_decode(raw_bytes)` with deterministic BOM detection (`utf-8-sig`, `utf-16-le`, `utf-16-be`), strict UTF-8 decoding, and strict CP932 / Windows-31J Japanese fallback.
  - Implemented `_is_plausible_cp932(text)` validation: rejects binary noise where stray bytes decode to unassigned C1 control codes (`\x80-\x9f`) or private use characters without any actual Japanese CJK characters (Hiragana, Katakana, CJK Unified Ideographs, CJK symbols, Halfwidth Katakana).
  - Implemented `encode_with_metadata(text, encoding, has_bom, newline)`: strictly round-trips encoding, BOM prefix, and native CRLF/LF line endings.
  - Implemented `read_text_file_strictly(path)` and `write_atomic_encoded(path, content, encoding, has_bom, newline)` (.tmp -> bounded Windows retry `os.replace`).
  - Re-exported all encoding primitives in `core/__init__.py`.
- **Elimination of Silent Corruption via `errors="replace"` (Rule 10)**:
  - In `misora.py:on_replace_all()`: Replaced `read_text(encoding="utf-8", errors="replace")` with `read_text_file_strictly(fpath)`. Preserves Japanese CP932, UTF-8 BOM, and native CRLF line endings on save without injecting replacement characters (`\ufffd`).
  - In `core/search_engine.py:search_file()`: Replaced `read_text(encoding="utf-8", errors="replace")` with `read_text_file_strictly(file_path)`, enabling project searches to match Japanese text in CP932 files without unhandled decode errors on binary files.
  - In `misora.py:open_file()`: Replaced `file_path.read_text(encoding="utf-8")` with `read_text_file_strictly(file_path)`. Leading BOM bytes are stripped cleanly so they never corrupt Box 0 or script headers; `has_bom`, `encoding`, and `newline` are cached in `open_documents[file_path]`.
  - In `misora.py:on_save()`: Plain-text files and v2 story scripts save with preserved encoding, BOM, and line endings retrieved from `open_documents`.
  - In `misora.py:on_import_script()`: Replaced fragile ad-hoc try/except with `read_text_file_strictly(target_file)`.
  - In `misora.py:_apply_delta(BulkFileDelta)`: Undo and redo operations preserve each file's original encoding and BOM.
  - In `core/xunity_sync.py`: Integrated `detect_encoding_and_decode` and `encode_with_metadata` in `preview_matches()` and `find_and_update()`.
- New test file: `tests/test_s8b3_encoding_detection.py` — 10 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s8b3_encoding_detection -v`: 10/10 pass (12.2s).
  - `py -3.12 -m unittest tests.test_s8b3_encoding_detection tests.test_s8b2_memory_guards tests.test_s8b1_notification_manager tests.test_s8a_dialog_grab_safety tests.test_s7_undo_speaker_safety tests.test_s6_threading_decoupling tests.test_s5_bulk_replace_safety tests.test_s4_view_model_sync tests.test_s3_document_close tests.test_s2_dirty_contract tests.test_s1_open_file_safety tests.test_phase2_required -v`: 126/126 pass (99.2s).
  - `py -3.12 -m unittest discover -s tests -v`: 213 tests run, 212 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (221.6s).

### S8b-4 Remaining UI Polishing & Responsive Scaling (2026-11-23)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Process DPI Awareness Invariant (Rule 23)**:
  - Eliminated runtime `ctypes.windll.shcore.SetProcessDpiAwareness(1)` call from `NguiColorPickerPopup._toggle_eyedropper()`, adhering strictly to Rule 23 (*"Do not change process DPI awareness at runtime"*).
  - Authored centralized module-level `init_process_dpi_awareness()` called once at application launch in `main()` before creating `MisoraApp` / Tk root window.
  - Negotiates `SetProcessDpiAwarenessContext` (-2 SYSTEM_AWARE) on Win 10/11 with graceful fallbacks to `SetProcessDpiAwareness(1)` (Win 8.1+) and `SetProcessDPIAware()` (Vista+).
- **Responsive Paned-Window Constraints & Dock Collapse Architecture**:
  - Resolved the geometry lock bug in `_toggle_dock_collapse()`: previously `sash_place(0, 20, 0)` failed because `minsize=160` on `left_frame` prevented shrinking below 160px, causing `current_w > 50` to stay true permanently and locking the dock in an un-expandable state.
  - Implemented explicit state tracking (`self._dock_collapsed: bool = False`) and dynamic minsize configuration (`paneconfigure(self.left_frame, minsize=0)` during collapse; `paneconfigure(self.left_frame, minsize=160)` during expansion).
  - Verified minsize bounds across `h_paned` (`left_frame >= 160`, `right_frame >= 420`, `side_drawer >= 260`) and `v_paned` (`top_view >= 140`, `bottom_view >= 80`) preventing pane squishing or widget collapse.
- **Icon Rendering Polish, Accessible Fallback Text & Tooltip Audit (Rule 21)**:
  - Equipped all icon-only buttons with unicode fallback text and theme-contrasting foregrounds (`fg=btn_fg`, `activeforeground=btn_fg` via `best_contrast_fg`):
    - `btn_sel_story` (`text="🗎"`), `btn_cut` (`text="✂"`), `btn_copy` (`text="📋"`), `btn_paste` (`text="📥"`), `btn_box_new` (`text="➕"`), `btn_box_cut` (`text="✂📦"`), `btn_box_copy` (`text="📋📦"`), `btn_box_paste` (`text="📥📦"`), `btn_eyedropper` (`text="🎨"`), `btn_pin_speaker` (`text="📌"`), `btn_close_search` (`text="✕"`), `btn_ribbon_undo` (`fg=btn_fg`), `btn_ribbon_redo` (`fg=btn_fg`).
  - Added accessible tooltips (`create_tooltip`):
    - `btn_close_search` ("Close Search Bar (Esc)"), `btn_dock_pin` ("Collapse Left Panel"), `btn_ribbon_swatch` ("Active NGUI Color (Click to open Color Picker)"), `btn_speaker_dropdown` ("Select Speaker from Recent List"), `btn_clear_res` ("Clear Search Results"), `btn_close_drawer` ("Close Side Panel"), `btn_drawer_pin` ("Pin / Unpin Side Panel").
  - Enhanced `ToolTip.__init__` to store `setattr(self.widget, "_tooltip", self)` enabling clean programmatic introspection and verification.
- New test file: `tests/test_s8b4_ui_polishing.py` — 8 tests (all pass).
- Verification Suites:
  - `py -3.12 -m compileall -q misora.py core assets tests`: PASS (exit code 0).
  - `py -3.12 -m unittest tests.test_s8b4_ui_polishing -v`: 8/8 pass (22.5s).
  - S-series regression (S1–S8b-4): 134/134 pass (155.9s).
  - Full discovery: 221 tests run, 220 pass, 1 failure (`test_05_clean_committed_config_has_no_machine_paths` pre-existing local runtime config issue), 0 skips (260.6s).
- Milestone: **Phase 6 (S-Series: S0 through S8b-4) is 100% COMPLETE**.

### Phase 7 New Deliverables — S9 Series (complete)

#### S9a Japanese Unicode Normalization & Combining Character Search (2026-11-23)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Combining Character Tokenization (`SPAN-NFKC-PER-CHAR`)**:
  - In `core/search_engine.py`: Extended `_TOKEN_RE` to include half-width katakana voiced and semi-voiced marks (`[\uff9e\uff9f]`):
    `r"\{(?:player_?name|0)\}|\\n|\r\n|[\r\n\v\f\x85\u2028\u2029]|.[\u0300-\u036f\u3099\u309a\uff9e\uff9f]*"`
  - Grapheme clusters containing combining dakuten/handakuten (`\u3099`, `\u309a`) and half-width marks (`\uff9e`, `\uff9f`) are now grouped into single multi-code-point tokens before normalizing via `unicodedata.normalize("NFKC", ...)`.
  - Normalizes half-width katakana (`ｶﾞ` -> `ガ`, `ﾊﾟ` -> `パ`) and decomposed hiragana (`か\u3099` -> `が`, `は\u309a` -> `ぱ`) into canonical precomposed characters while maintaining exact 1:1 token-to-span mapping (`spans` list).
  - Added public API aliases `normalize_with_spans` and `norm_search_with_spans` on `ProjectSearchEngine`.
  - Verified 100% equivalence between `normalize_with_spans(s)[0]` and `story_ast.norm_search(s)`.
- New test file: `tests/test_s9a_search_unicode.py` — 6 tests (all pass in 0.001s).

#### S9b Multi-File Replace-All Bundle Extraction & Transactional Undo (2026-11-23)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Candidate Bundle Story Decoding (`REPLACE-ALL-BUNDLE-PREFILTER`)**:
  - In `misora.py:on_replace_all()`: Replaced raw byte scanning on `.unity3d` / `.asset` files with structured story extraction via `load_bundle_story(cf)` (with strict `finally: dispose_unity_env(bundle_env)` cleanup).
  - Searches and counts query matches directly in `box.clean_text` across decoded dialogue boxes, completely eliminating false negatives from compressed UnityFS / LZ4 archives and false positives from binary metadata.
- **Bundle Backup & Transactional Undo (`REPLACE-ALL-UNDO-GAP`)**:
  - When saving modified bundles in multi-file Replace-All:
    - Snapshots original bundle to `_get_backup_dir()` via `shutil.copy2` (`orig_bak_path`).
    - Repacks story via `save_bundle_story(bundle_env, obj, doc, fpath, backup_dir=bak_dir)`.
    - Snapshots post-modification bundle to `_get_backup_dir()` (`mod_bak_path`).
    - Appends 4-tuple `(str(fpath), str(orig_bak_path), str(mod_bak_path), True)` to `per_file_deltas` in `BulkFileDelta`.
  - In `misora.py:_apply_delta(BulkFileDelta)`:
    - Symmetrically supports both text tuples (3-element) and bundle tuples (4-element with `is_bundle=True`).
    - Added `@staticmethod _restore_bundle_atomic(src_bak_path, dst_path)` using atomic `.tmp` copy with bounded retry for Windows sharing violations.
    - Reverse (Undo): atomically restores `orig_bak_path` to bundle file; updates `open_documents` cache and checkpoints if open.
    - Forward (Redo): atomically restores `mod_bak_path` to bundle file; updates `open_documents` cache and checkpoints.
    - Rollback: if any write fails mid-batch during undo/redo, safely rolls back all applied files in reverse order across both text and binary bundles.
  - In `misora.py:_evaluate_checkpoints_for_op()`:
    - Safely unpacks `item[0]` from `delta.per_file` to support both 3-tuples and 4-tuples without `ValueError`.
- New test file: `tests/test_s9b_replace_all_bundle_safety.py` — 3 tests (all pass).

#### S9c Workspace Protection, Window Geometry Safety & Test Hygiene (2026-11-23)
- Workspace: `D:\Misora-Editor`; branch `main`; Python 3.12.10 (AMD64).
- **Multi-Folder Drag-and-Drop Warning (`FOLDER-DROP-EXTRA-IGNORED`)**:
  - In `misora.py:_handle_dropped_paths()`: When multiple folders are dropped (`len(dirs) > 1`), opens the first folder and explicitly alerts the user via status bar warning, toast notification, and logger entry informing that the remaining folders were ignored.
- **Virtual Screen Window Geometry Clamping (`OFFSCREEN-GEOMETRY`)**:
  - Added module-level `sanitize_window_geometry(geom_str, screen_w, screen_h)` helper.
  - Validates saved geometry strings (`WIDTHxHEIGHT+X+Y`) against the current display's virtual screen dimensions (`winfo_screenwidth()`, `winfo_screenheight()`).
  - Clamps X and Y coordinates and window dimensions into visible bounds, preventing windows from opening off-screen when launching after disconnecting an external monitor.
- **Undo Coalescing Cross-Source Isolation (`UNDO-COALESCE-CROSS-SOURCE`)**:
  - Audited all 13 `BoxEditDelta` instantiation sites in `misora.py`:
    - Contextual source tracking: `self._current_edit_source = "format"` in `_insert_text_wrapper()`, `self._current_edit_source = "cut"` in `on_text_cut()`.
    - Explicit sources passed for `on_replace_next` (`"replace"`), `on_replace_all` (`"replace"`), `_show_paste_preview_and_apply` (`"paste_script"`), `on_clear_dialogue_skeleton` (`"clear"`), and MTL translation (`"mtl"`).
    - `core/undo_journal.py` checks `(prev_delta.source == delta.source)`. Typing (`"keyboard"`) only coalesces with typing, never with ribbon formatting, cut, replace, or translation.
- **Test Hygiene & Config Isolation**:
  - Authored clean default configuration template `misora_config.default.json` in repository root.
  - Updated `tests/test_phase3_performance_config.py:test_05` to check `misora_config.default.json` rather than untracked local developer session state, eliminating the 1 pre-existing failure.
- New test file: `tests/test_s9c_workspace_safety.py` — 4 tests (all pass).
- Milestone: **Phase 7 (S9-Series: S9a through S9c) is 100% COMPLETE**.
- Full Project Verification Gate: **234/234 tests PASS (100% clean, 0 failures, 0 errors, 0 skips in 247.764s)**.

### Phase 5 New Deliverables (complete)
- **`core/ngui_tags.py`** (5,760 bytes): Central single source of truth for NGUI rich-text patterns (bold, italic, underline, strikethrough, size, vertical hyphen gradients `[c0-c1]`, multiline ruby `[rub:...]` with `re.DOTALL`, placeholders `{playername}`, `{0}`..`{n}`). Utilities: `strip_tags()`, `get_rendered_length()`, `measure_line_lengths()`, `normalize_gradient_syntax()`, and `TagMasker`.
- **`core/security.py`** (3,320 bytes): Windows DPAPI credential encryption (`protect_secret` / `unprotect_secret` with `dpapi:` prefix) and secret redaction (`redact_secret` for logs/UI).
- **`core/mtl_engine.py`**:
  - Enforced default valid TLS certificate and hostname verification on outbound requests (Rule 18 / `TLS-VERIFICATION-DISABLED`).
  - Optimized DeepL connection test to query free `/v2/usage` status endpoint instead of billable `/v2/translate` (Rule 18 / `DEEPL-TEST-COST`).
  - Integrated DPAPI secret protection in `MTLConfig.to_dict(secure=True)` and decryption in `from_dict()`.
- **`misora.py`**:
  - Translation Lock (`Ctrl+L` / `btn_lock_box`) protects boxes from batch translation, script paste, and replace all, accurately reporting preserved counts (Rule 20 D8 / `TRANSLATION-LOCK`).
  - Aligned Find/Replace dialog buttons ('Find in Files', 'Cancel', 'Replace', 'Replace All') in a symmetrical 2x2 column block with matching widths and illustrated Twemoji icons (`search.png`, `cancel.png`, `replace.png`, `replace_all.png`).
  - Live rendered character count counter (`lbl_char_count`) measuring text excluding tags, with warning badges `⚠ Overflow` for lines exceeding 45 characters (Rule 20 D13 / `GAME-BOX-PREVIEW`).
  - Continuous View cards display lock badges `🔒` and rendered character counts in card headers.
- **`tests/test_phase5_mtl_security_preview.py`**: 7 automated tests covering all Phase 5 requirements (all pass).

### Phase 4 New Deliverables (complete)
- **`misora.py` File Import / Export menus & handlers**:
  - `File -> Import Script (CSIF / Text)...` (`Ctrl+Shift+I`) and `File -> Export Script (CSIF)...` (`Ctrl+Shift+E`).
  - Added `on_import_script()` and `on_export_script()` handlers with full UTF-8/BOM/CP932 decoding and atomic write.
  - Bound accelerators to `MisoraShortcuts` bindtag and global root window.
- **`ScriptPastePreviewDialog` (interactive modal `tk.Toplevel`)**:
  - Comprehensive before/after dialogue comparison in scrollable `ttk.Treeview`.
  - Format sniffer, block count, target range, excess block warning, and metadata presence banners.
  - Interactive checkboxes to toggle speaker name application and Box 0 metadata injection with live table updates.
  - Preserves 100% backwards compatibility with headless/mocked unit tests.
- **Version unification (Rule 21)**:
  - Single source of truth `__version__ = "1.3.3"` in root `__init__.py`.
  - Dynamically read by `misora.py` (`_get_app_version()`), `assets/splash.py` (`_load_app_version()`), `on_about()`, and `NguiColorPickerPopup`.
- **Safe tooltip lifecycle management (`TOOLTIP-LIFECYCLE` RESOLVED)**:
  - Delayed hover timer (350ms), `widget_exists()` guards, timer cancellation on `<Leave>` / `<Destroy>`, and safe `tip_window.winfo_exists()` checks.
- **`tests/test_phase4_import_export_preview.py`**:
  - 5 comprehensive automated tests covering all Phase 4 deliverables (all pass).

### Phase 3 New Deliverables (complete)
- **`core/bundle_io.py`**: Decoupled `UnityPy` at module level; implemented `get_unitypy()` with double-checked locking (`_unitypy_lock`) and fallback version `2021.3.20f1`. Reduced `import core` execution time from 1.03s to 0.14s.
- **`misora.bat`**: Eliminated redundant/slow `py -%V -c "import UnityPy"` probe loops on launch.
- **`core/logger.py`**: Added `_file_queue: queue.Queue`, background `_writer_thread`, and `flush(timeout)` / `close()` lifecycle to decouple disk writes from the UI thread.
- **`misora.py`**:
  - Implemented corrupt config recovery: auto-generates `.bak_<timestamp>.json` before applying defaults.
  - Deferred session file restore (`_saved_opened_files` and `initial_path`) until after root window is displayed using `after_idle` (Rule 22).
  - Aligned Find/Replace dialog buttons in a 2x2 grid and wired modern icons (`cancel.png`, `replace.png`, `replace_all.png`).
- **`tests/test_phase3_performance_config.py`**: 6 automated verification tests covering all Phase 3 requirements (all pass).
- **`tests/test_misora_ui_integration.py`**: Patched `CONFIG_PATH` in `setUp`/`tearDown` to ensure tests never pollute the root `misora_config.json`.

### Phase 2 New Deliverables (complete)
- **`core/script_codec.py`** (18,860 bytes): CSIF codec — `serialize`, `parse`, `sniff_format`, `apply_to_document`, `sanitize_speaker`; sparse addressing; legacy input adapters (triple-enter, paragraph, `[BOX:n]`); code-fence stripping; CRLF/BOM normalization; `@@!` metadata routing.
- **`docs/SCRIPT_FORMAT.md`** (3,504 bytes): CSIF v1 spec with grammar, examples, modes, legacy compat.
- **`tests/test_script_codec.py`** (8,192 bytes): 14 codec unit tests (all pass).
- **`tests/test_phase2_required.py`** (22,892 bytes): 13 GUI required tests 28–40 (all pass).

### Phase 2 Runtime Fixes Applied (all RESOLVED)
- **Test suite hang** (`messagebox.askyesno` blocking headless mainloop): `tests/test_phase1_manual_verification.py` fully rewritten with global messagebox mocking; `on_box_paste(confirm=False)` in all test calls.
- **Uncancelled `after()` teardown errors** (`invalid command name "...<lambda>"`): `MisoraApp.destroy()` now cancels all pending `after()` jobs (`_search_poll_job`, `_cont_resize_job`, `_toast_after_id`, `_eyedropper_after_id`) plus a full anonymous sweep via `self.tk.call("after", "info")`.
- **`mark_saved()` TypeError**: Fixed calls from `mark_saved(str(path))` → `mark_saved()`.
- **`is_clean()` TypeError**: Fixed call from `is_clean(self.current_file_path)` → `is_clean()`.
- **`result.source_format` AttributeError**: Fixed to `result.format` in `on_paste_cross_box`.
- **Speaker reset in `on_paste_cross_box()`** (test_23, test_26): Fixed by computing `any_speaker = any(b.speaker for b in result.blocks[:count])` and passing `apply_speakers=any_speaker` to `apply_to_document()`. Plain-text paste now preserves original box speakers; CSIF paste still applies speaker names.
- **`@@!` metadata-only routing** (test_29): When `result.blocks` is empty but `result.metadata` non-empty, `on_paste_cross_box` applies metadata to Box 0 via `MetadataDelta` regardless of active box.
- **test_21 session-state contamination**: Forced page view explicitly in test with `var_continuous_view.set(False)` + `_on_toggle_continuous_view()`.
- **test_26 CSIF assertion**: Updated test to check for `@@` headers (Phase 2 `on_copy_script` now emits CSIF, not triple-enter).

### Manual Windows Tests Still Required (Rule 29 — cannot be automated headlessly)
1. **Copy Box → Notepad++ → Paste Box round-trip**: speakers and text must survive with zero drift.
2. **Paste Box in both views**: must insert correctly in Page view AND Continuous view.
3. **Ctrl+H must not delete text**: confirmed by test_31 (automated) but needs real keyboard test.
4. **Ribbon Cut must survive navigation**: needs real keyboard test.

### Baseline Before This Session (for comparison)
```text
Result: Ran 38 tests in 28.601s — FAILED (failures=4, errors=1)
```
(Suite was also hanging indefinitely before the hang fix.)

---

## 3. Historical Baseline B1–B20 (Preserved)

| ID | Area | Historical status | Canonical note |
|---|---|---|---|
| B1 | Open Folder flow | RESOLVED | Keep unified folder prompt and scope protection. |
| B2 | Search across segments/metadata | RESOLVED | Keep metadata search; future cache must not regress it. |
| B3 | Checkbox contrast | RESOLVED | Keep native ttk checkbuttons. |
| B4 | DnD scope protection | RESOLVED | Keep invalid-drop scope protection. |
| B5 | Speaker variable orphaning | RESOLVED | Single-root + explicit master remains mandatory. |
| B6 | Continuous View variable orphaning | RESOLVED | Same invariant. |
| B7 | Undo caret teleport | RESOLVED | Caret preservation still required after batch refresh. |
| B8 | Startup splash freeze | RESOLVED historically | Re-measure; do not assume current startup is instant. |
| B9 | Folder opening crash | RESOLVED | Keep WNDPROC unwind delay and cleanup. |
| B10 | Box 0 metadata | RESOLVED historically | Box 0 save/flush path is still defective; see BOX0-SAVE-CORRUPTION. |
| B11 | View menu toggles | RESOLVED | Keep visible menu checkmarks. |
| B12 | Custom themes | RESOLVED | Keep live custom theme commit. |
| B13 | Ribbon dimensions | RESOLVED | Re-measure after ribbon changes. |
| B14 | Pink multi-segment artifact | RESOLVED historically | The `fill=""` change introduced arity risk; see EMPTY-ARG-ARITY. |
| B15 | Editor border | RESOLVED | Keep 1px border. |
| B16 | Plain text save/backups | RESOLVED historically | Plain-text view routing still defective; see PLAINTEXT-SAVE-ROUTING. |
| B17 | Cross-box paste | RESOLVED historically | Legacy delimiter paste is fragile; CSIF replaces it later. |
| B18 | Box Card Stream | RESOLVED | Keep card architecture; fix aliasing and commit paths. |
| B19 | Triple-enter workflow | RESOLVED historically | Superseded by CSIF; keep legacy input only. |
| B20 | Speaker dropdown / Box 0 protection | RESOLVED | Narration must convert record kind, not blank a print speaker. |

---

## 4. Canonical Defect Ledger

### P0 — Data Integrity & Release Blockers (Phase 1 & Phase 2)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **AST-INDEX-SHIFT** | RESOLVED | `core/story_ast.py:279, 288` | `Seg.record` direct reference replaces stale positional indexing. Covered by `test_12`. | 1 |
| **BOX-STRUCTURAL-OPS** | RESOLVED | `core/story_ast.py:181` | Document-level structural APIs (`insert_box`, `delete_box`, `move_box`, `clone_box`) with `BoxSnapshot`. Covered by `test_13, test_14`. | 1 |
| **BOX-PASTE-DEAD** | RESOLVED | `misora.py` | Missing helpers `_push_undo`, `_dirty_state_changed`, and `_sync_clean_view_to_current_box` implemented. Covered by `test_28`. | 2 |
| **BUNDLE-SAVE-WRITES-BEFORE-VERIFY** | RESOLVED | `core/bundle_io.py:117-128` | Staged `.tmp` save with target `path_id` verification, fingerprint validation, and `os.replace`. Covered by `test_17, test_18`. | 1 |
| **BOX0-SAVE-CORRUPTION** | RESOLVED | `misora.py` | Dedicated Box 0 metadata flush/save path. Prevents dialogue injection while Box 0 is active. Covered by `test_33`. | 2 |
| **V2-ROUNDTRIP-LOSS** | RESOLVED (2026-11-24: S03 / BUG-03) | `core/story_ast.py` | Lossless v2 text roundtrip with `\b64:<base64>` surrogateescape, category collision prefixing (`\<Cat>`), backslash-first escaping, and `\s`/`\S` trailing/whitespace-only space escaping. Covered by `test_p3_s03_binary_v2:test_probe_3`. | 1 |
| **XUAT-SYNC-LINE-CORRUPTION** | RESOLVED | `core/xunity_sync.py` | Strict UTF-8 with BOM preservation, multiline `\n` escaping in values, CRLF/LF line ending preservation. Covered by `test_19`. | 1 |
| **EMPTY-ARG-ARITY** | RESOLVED | `core/story_ast.py` | Binary serialization retains empty string arguments, preventing arity reduction. Covered by `test_15`. | 1 |
| **NARRATION-EMPTY-PHANTOM** | RESOLVED | `core/story_ast.py` | Narration emits `tag` records instead of `print` with empty speaker. Covered by `test_15`. | 1 |
| **PAGE-BREAK-NOT-SPLIT** | RESOLVED (2026-11-24: S03 / BUG-04) | `core/story_ast.py` | Breakers classified strictly by numeric `DEFAULT_BREAKER_IDS = frozenset({0, 1, 4, 10, 36})`. Covered by `test_p3_s03_binary_v2:test_probe_4`. | 1 |
| **RAW-TAIL-FROZEN** | RESOLVED | `core/story_ast.py` | `inject_box` updates `seg.raw` alongside `seg.text`. | 1 |
| **CMD0-SPECIAL-CASE** | RESOLVED (2026-11-24: S03 / BUG-03) | `core/story_ast.py` | Removed legacy `cmd_id == 0` remapping in `to_binary()`. `cmd_id == 0` titles serialize strictly as 0 (not 30). Covered by `test_p3_s03_binary_v2:test_probe_2`. | 1 |
| **SHORTCUT-BINDTAG-ORDER** | RESOLVED | `misora.py` | Installed first-position `MisoraShortcuts` bindtag router. Ctrl+H opens replace dialog without mutating dialogue text. Covered by `test_31`. | 2 |
| **RIBBON-CUT-PASTE-NO-COMMIT** | RESOLVED | `misora.py` | Virtual `<<Cut>>` and `<<Paste>>` explicitly invoke central `_commit_widget_edit`. Covered by `test_30`. | 2 |
| **MULTI-TEXTASSET-TARGET** | PARTIALLY RESOLVED (2026-11-24: S03 / BUG-09) | `core/bundle_io.py` | Pre-save SHA-256 non-target object verification in `save_bundle_story` detects modified or dropped non-target objects. Covered by `test_p3_s03_binary_v2:test_probe_5`; production fixture compatibility remains BLOCKED. | 1 |
| **INJECT-EXTRA-ARGS** | RESOLVED | `core/story_ast.py` | `inject_box` and `set_metadata` preserve unmanaged trailing args. | 1 |
| **KIND-CONVERSION-COLLAPSE** | RESOLVED (2026-11-24: S04 / BUG-02) | `core/story_ast.py:set_box_kind()`, `inject_box()` | Minimal valid boundary breaker (`cmd_id=10`) inserted before/after kind-converted boxes when adjacent boxes would merge; target UID resolved before/after write. Covered by `test_p3_s04_ast_mutations:test_probe_1`. | 1 |
| **STRUCTURAL-VOICE-BREAKER-OWNERSHIP** | RESOLVED (2026-11-24: S04 / BUG-05) | `core/story_ast.py:insert_box()`, `delete_boxes()`, `move_box()` | Preceding `cmd_id == 12 vo_` cue owned by box across moves/deletes; boundary insertions anchor before destination voice cues; redundant tap-breakers cleaned up without neighbor merge. Covered by `test_p3_s04_ast_mutations:test_probe_2`. | 1 |

### P0 (new, from manual testing 2026-11-20)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **BOX0-NO-SELECT-CHECKBOX** | REOPENED (2026-11-24: BUG-41) | `misora.py:_render_continuous_view` | Historically added Checkbutton to Box 0 card header (`hdr_0`). Reopened for selection mode routing and Box 0 copy integrity under BUG-41. | 2 |
| **BOX1-COPIES-BOX0-METADATA** | RESOLVED | `core/script_codec.py:serialize()` | Removed `0 in box_indices` auto-emission branch in `serialize()`. Auto-emission now only emits metadata when `scope in ("all", "metadata")` or when Box 0 (`-1`) is explicitly selected. | 2 |
| **CTRL-ALT-HOTKEYS-BLOCKED** | REOPENED (2026-11-24: BUG-29) | `misora.py:_on_misora_shortcut()` | Historically fixed Windows Alt modifier bitmask. Reopened for AltGr/Ctrl+Alt keyboard shortcut router resolution under BUG-29. | 2 |
| **CONTINUOUS-EDIT-NO-COMMIT** | RESOLVED | `misora.py:_commit_widget_edit()` | Decoupled Page View Box 0 widgets and Continuous View Card -1 from `is_box0_active` boolean guard. Edits to continuous cards and Box 0 synopsis now commit directly to AST document. | 2 |
| **BOX0-SWITCH-LOCKS-EDITOR** | RESOLVED | `misora.py:_on_toggle_continuous_view`, `on_prev_box`, `on_next_box` | Restores caret and keyboard focus immediately and via `after_idle` upon view toggles and box navigation. Guarded `_cont_focus_job` against stale cross-view firing. | 2 |
| **VOICE-CUE-DISPLAY-MISSING** | RESOLVED | `core/story_ast.py:_rebuild_boxes` | Captured `cmd_id == 12` voice cues with `"vo_"` prefix; guarded breaker loop `elif r.cmd_id != 12 and r.cmd_name in DEFAULT_BREAKERS:` so voice cues are never skipped or discarded. | 2 |
| **FIND-REPLACE-UI-ASYMMETRY** | REOPENED (2026-11-24: BUG-38) | `misora.py:_build_search_panel` | Historically converted Find/Replace rows to 5-column grid and 2x2 buttons. Reopened for layout symmetry and coordinate alignment under BUG-38. | 2 |

### P1 — Functional, UI, & Security Issues (Phases 2, 3, 5)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **DIRTY-EXIT-DROPS-EDITS** | RESOLVED | `misora.py:1302-1312` | `_on_app_exit` prompts Save/Discard/Cancel with `askyesnocancel` on dirty state before window close. | 2 |
| **RELOAD-REVERT-HIT-CACHE** | RESOLVED | `misora.py:7838-7841, 7949-7952` | `on_revert_box` and `on_reload` call `open_file(..., reload_from_disk=True)`. | 2 |
| **REPLACE-ALL-BUNDLE-PREFILTER** | RESOLVED | `misora.py:on_replace_all()` | Candidate discovery decodes structured story TextAssets instead of raw byte scanning. Covered by `test_s9b_replace_all_bundle_safety.py:test_01`. | 2 |
| **REPLACE-ALL-UNDO-GAP** | RESOLVED | `misora.py:on_replace_all(), _apply_delta()` | Bundle changes recorded in BulkFileDelta with atomic backup snapshots; fully undoable/redoable with transaction rollback. Covered by `test_s9b:test_02, test_03`. | 2 |
| **TLS-VERIFICATION-DISABLED** | RESOLVED | `core/mtl_engine.py:142-144` | Outbound HTTPS requests strictly enforce valid TLS certificate and hostname verification. Covered by `test_phase5_mtl_security_preview.py:test_03`. | 5 |
| **API-KEYS-PLAINTEXT** | REOPENED (2026-11-24: BUG-33) | `core/security.py:20-65`; `core/mtl_engine.py:52-78`; `misora.py` | Historically encrypted keys via Windows DPAPI (`dpapi:...` prefix) in config (test_phase5:test_02). Reopened for comprehensive secrets redaction and plain text leakage audit under BUG-33. | 5 |
| **TAGMASKER-INCOMPLETE** | RESOLVED | `core/ngui_tags.py:15-161` | Central single source of truth for NGUI markup, hyphen gradients, multiline ruby, placeholders, and full shielding/unshielding. Covered by `test_phase5:test_01`. | 5 |
| **SIZE-RIBBON-NO-COMMIT** | REOPENED (2026-11-24: BUG-28) | `misora.py:6374-6394` | Historically routed font size insertion to central commit (test_37). Reopened for Continuous View ribbon commit target desync under BUG-28. | 2 |
| **CONTINUOUS-RIBBON-TARGET-STALE** | REOPENED (2026-11-24: BUG-28) | `misora.py` | Historically resolved active card dynamically. Reopened for Continuous View ribbon formatting desync under BUG-28. | 2 |
| **UNDO-STORM** | RESOLVED | `misora.py` | Batch undo applies all deltas to model first, then refreshes UI once in `finally`. | 2 |
| **SEARCH-RACE** | RESOLVED | `misora.py` | UI thread snapshot isolation via `on_start_search()`; covered by `test_s6_threading_decoupling`. | 2 |
| **CLIP-SHADOW** | RESOLVED | `misora.py` | If system clipboard differs from internal box snapshot text, internal snapshot is discarded. Covered by `test_35`. | 2 |
| **FOLDER-DROP-EXTRA-IGNORED** | RESOLVED | `misora.py:_handle_dropped_paths()` | Multi-folder drop opens first folder and warns user via status bar and toast about ignored extra folders. Covered by `test_s9c:test_01`. | 2 |
| **DEEPL-TEST-COST** | RESOLVED | `core/mtl_engine.py:299-316` | Connection test queries free `/v2/usage` status endpoint instead of billable `/v2/translate`. Covered by `test_phase5:test_04`. | 5 |
| **CORE-IMPORT-COUPLING** | RESOLVED | `core/bundle_io.py:23-45`; `tests/test_phase3_performance_config.py:33-53` | `core` decoupled from `UnityPy` at import time via double-checked lazy load under lock; `import core` dropped from 1.03s to 0.14s. | 3 |
| **CONFIG-RECOVERY-OVERWRITE** | RESOLVED | `misora.py:1456-1473`; `tests/test_phase3_performance_config.py:82-106` | Corrupted config preserved as `.bak_<timestamp>.json` recovery copy before using defaults. | 3 |
| **STALE-CARD-REGISTRY** | RESOLVED | `misora.py` | `_card_widgets` cleared in `close_file()` empty-state and `_update_views()` plain-text path via `_clear_card_registry()`; `_get_card_text_widget()` guards ribbon targets with `winfo_exists()`. Covered by `test_s4_view_model_sync`. | 2 |
| **GRADIENT-COMMA-EMITTER** | RESOLVED | `misora.py:1014, 4608` | Gradient insertion strictly emits hyphen syntax `[c0-c1]`. Comma syntax rejected by NGUI is avoided. | 2 |
| **SPAN-NFKC-PER-CHAR** | RESOLVED | `core/search_engine.py:46, 88-124` | Combining dakuten/handakuten and half-width marks tokenized as clusters before NFKC normalization; 100% equivalent to `norm_search()`. Covered by `test_s9a:test_01-06`. | 2 |
| **UNDO-COALESCE-CROSS-SOURCE** | RESOLVED | `misora.py`, `core/undo_journal.py` | BoxEditDelta explicitly tracks source ("keyboard", "format", "cut", "replace", "mtl", "paste_script", "clear"); typing only coalesces with typing. Covered by `test_s9c:test_03`. | 2 |
| **GENERIC-PLACEHOLDER-GAP** | RESOLVED | `core/ngui_tags.py:48-52` | Placeholders `{playername}` and all `{n}` placeholders shielded in translation and highlighted in preview. Covered by `test_phase5:test_01`. | 5 |
| **LOGGER-SYNC-IO** | RESOLVED | `core/logger.py:27-145`; `tests/test_phase3_performance_config.py:54-81` | Asynchronous background worker queue for file logging disk I/O; clean flush and thread termination. | 3 |
| **BULK-DELTA-NONATOMIC** | RESOLVED | `misora.py` | Multi-file text replacement in `on_replace_all()` and undo/redo in `_apply_delta()` use `write_atomic_utf8()` with transaction rollback and `open_documents` cache sync. Covered by `test_s5_bulk_replace_safety`. | 2 |
| **HARDCODED-PROJECT-PATH** | RESOLVED | `misora_config.json`; `tests/test_misora_ui_integration.py:34-45` | Committed config reset to empty defaults; UI integration tests isolated from root config. | 3 |
| **PLAINTEXT-SAVE-ROUTING** | REOPENED (2026-11-24: BUG-11) | `misora.py` | Historically routed between Plain Text (Page/Continuous) and Story Bundle AST. Reopened for edge-case plain text save routing under BUG-11. | 2 |
| **MULTI-SEGMENT-UNDO-PASTE** | RESOLVED (2026-11-24: S04 / BUG-06) | `core/story_ast.py`, `core/undo_journal.py`, `misora.py` | Non-blocking multi-segment editing with `'N segs'` badge; `BoxEditDelta.old_seg_texts`/`new_seg_texts` segment preservation; lossless `BoxSnapshot` paste. Covered by `test_p3_s04_ast_mutations:test_probe_3`. | 2 |
| **UNDO-UID-COALESCE** | RESOLVED (2026-11-24: S04 / BUG-17) | `core/undo_journal.py:MasterUndoJournal.record()` | Coalescing requires matching `box_uid` when non-None, preventing edits on distinct boxes with identical index from coalescing. Covered by `test_p3_s04_ast_mutations:test_probe_4`. | 2 |
| **TOMBSTONE-UNBOUNDED-GROWTH** | RESOLVED (2026-11-24: S04 / HYG-04) | `core/story_ast.py:delete_boxes()` | Dead record UIDs deterministically pruned against active records in `self.records`. Covered by `test_p3_s04_ast_mutations:test_probe_5`. | 2 |

### P2 — Performance, QoL, & Measured Risks (Phases 3, 4, 5)

| Slug | Status | Note | Phase |
|---|---|---|---|
| **THEME-RAW-PERF** | MEASURED | 1 file (142 boxes) = 160MB RAM; 135 files test showed workable switching on i7-13700KF. Benchmark lower-spec targets. | 3 |
| **SEARCH-CACHE** | DESIGN | LRU keyed by path/mtime/size; must include metadata. | 3 |
| **ICON-CACHE-GROWTH** | RESOLVED | `assets/icon.py:prune_icon_cache()`; `misora.py:destroy()` | Bounded icon cache; explicitly pruned on toplevel destruction and app teardown. Covered by `test_s8b2:test_05`. | 3 |
| **OFFSCREEN-GEOMETRY** | RESOLVED | `misora.py:sanitize_window_geometry()` | Window coordinates validated against virtual display bounds; off-screen coordinates safely clamped to visible screen. Covered by `test_s9c:test_02`. | 3 |
| **TOOLTIP-LIFECYCLE** | RESOLVED | Delayed tooltip cancels pending `after()` timers on `<Leave>` / `<Destroy>`, checks `widget_exists()`, and safely destroys `tip_window`. Covered by `test_phase4_import_export_preview.py:test_02`. | 4 |
| **GAME-BOX-PREVIEW** | REOPENED (2026-11-24: FEAT-09 / FEAT-10) | Rendered dialogue length counter ignoring tags; live warning badge. Reopened for native overflow ruler emulation (50 digit-widths or 3+ linebreaks) planned for S17 under FEAT-09/FEAT-10. | 5 |
| **TRANSLATION-LOCK** | REOPENED (2026-11-24: BUG-12 / BUG-16) | Translation Lock (`Ctrl+L`) excludes protected boxes from batch translation, script paste, and replace all (test_phase5:test_05). Reopened for model/application layer lock enforcement under BUG-12/BUG-16. | 5 |
| **PROMPT-STUDIO** | DESIGN | Upgrade prompt dialog; token budget; templates as data. | 5 |
| **TERMBASE / TM** | DESIGN | TM = XUAT cache index; provenance sidecar only. | 5 |
| **XUAT2RAW** | DESIGN | Adapter stub only until tool output spec exists. | 4 |

---

## 5. Retracted Claims

Do not spend time investigating these as current bugs:

| Claim | Final status |
|---|---|
| **PLAINTEXT-SAVE-FALLTHROUGH** (as missing return) | RETRACTED: [misora.py:7064](file:///d:/Misora-Editor/misora.py#L7064) terminates with explicit `return`. Real defect is view routing in line 7052 (`PLAINTEXT-SAVE-ROUTING`). |
| **TRANSLATOR-SOURCE-SEED** | RETRACTED: Target pane is not pre-seeded with Japanese text. `orig_text` is captured solely for diffing baseline. |
| **TEXTASSET-STR-DECODE-FIDELITY** | RETRACTED: `bundle_io.py` strictly uses `utf-8` with `errors="surrogateescape"`, which is bidirectional and byte-preserving. |
| **Double paste dispatch (B30)** | RETRACTED: `on_text_paste` returns `"break"` to suppress secondary default dispatch. |
| **Span drift for literal `\n` (B135)** | RETRACTED: Tokenizer correctly handles escaped `\n`. Real defect is `SPAN-NFKC-PER-CHAR`. |
| **Lowercase hex rejected** | RETRACTED: Regex patterns accept case-insensitive `[a-f0-9]`. |
| **`translate_async` location** | RETRACTED: Function is defined at module level. |
| **Uploaded config JSON malformed** | RETRACTED: Root cause was paste artifact; `CONFIG-RECOVERY-OVERWRITE` remains valid. |
| **`choice` misclassified as speaker** | RETRACTED: Choice records are unprojected command records, not speaker text. |
| **Minimum XUAT key length block** | REJECTED: Short Japanese keys are valid. Use duplicate/conflict preview. |
| **Ctrl+Y is universally yank** | RETRACTED: Platform/Tk dependent. Bindtag router makes it moot. |
| **Immediate `Box.__deepcopy__` TypeError** | REJECTED: Migrate to explicit `BoxSnapshot` API instead. |
| **Insecure TLS checkbox** | REJECTED: Fix CA trust verification, do not add insecure bypass. |

---

## 6. Design Invariants for Future Capabilities

| ID | Invariant |
|---|---|
| D1 | CSIF export uses `@@Speaker`, `@@_` narration, and `@@!title/@@!subtitle/@@!summary`. |
| D2 | Sparse CSIF uses 1-based `@@#N|Speaker`; emitted only for filtered/non-contiguous export. |
| D3 | Sparse import rejects mixed, duplicate, missing, or out-of-range addressing; no positional fallback. |
| D4 | Metadata paste routes to Box 0 and warns if target document lacks metadata records. |
| D5 | Outer Markdown code fences may be stripped with a warning; inner fences are dialogue content. |
| D6 | Clipboard helper retries on `TclError` and normalizes CRLF/CR before parsing. |
| D7 | Shortcut router is whitelist-only, IME/grab/CapsLock/AltGr safe via first-position bindtag. |
| D8 | Translation Lock excludes protected boxes from batch/paste/replace and reports skipped count. |
| D9 | Provider registry is local-only; no remote code execution, auto-update, or unverified sockets. |
| D10 | Termbase names are glossary/post-check hints for translation, not masked tokens by default. |
| D11 | Translation Memory is the XUAT cache index; provenance lives in sidecar metadata. |
| D12 | Prompt Studio templates are structured data, never executable scripts. |
| D13 | Game Box Preview measures rendered text width; hard line breaks must be preserved to prevent overflow in non-NGUI scenes. |
| D14 | XUAT sync escapes real newlines as `\n` to maintain the strict one-key-per-line dictionary format. |
| D15 | NGUI tag patterns are centralized in `core/ngui_tags.py`. Vertical gradients emit hyphens `[c0-c1]`. |
| D16 | Delayed tooltips cancel pending `after` timers and check widget existence before display. |

---

## 7. Five-Phase Execution Roadmap

### Phase 1 — Core Structural AST, Binary & Save Safety
Scope: `core/story_ast.py`, `core/bundle_io.py`, `core/undo_journal.py`, `core/xunity_sync.py`, tests.
Non-goals: GUI redesign, CSIF, MTL drawer, startup redesign.

Tasks:
- [x] Replace `Seg.rec_index` with `Seg.record`; add runtime Record uid; rebuild projection after mutations.
- [x] Add structural AST mutation APIs: `insert_box`, `delete_box`, `move_box`, `clone_box` with `BoxSnapshot`.
- [x] Preserve unmanaged extra args in `inject_box` and `set_metadata`.
- [x] Fix empty-arg arity dropping in `to_binary`; convert narration to `tag` records.
- [x] Fix raw tail freshness (`seg.raw`) and page-break splitting (`next_page` breaker token).
- [x] Make v2 text lossless: preserve `cmd_32`, category, duplicate commands, and line breaks.
- [x] Remove `cmd_id == 0` special case in `to_binary`.
- [x] Implement atomic same-directory `.tmp` save with target `path_id` verification, fingerprint check, and bounded retry.
- [x] Enforce strict XUAT encoding, escape newlines in values, preserve BOM and CRLF.
- [x] Add regression test suite for AST structural mutations and bundle round-trip.

### Phase 2 — GUI Integrity, Central Commit, Shortcuts, Undo & CSIF Codec
Scope: `misora.py`, new `core/script_codec.py`, `core/search_engine.py` (snapshots), tests.
Non-goals: Importer registry (Phase 4), startup optimization (Phase 3), MTL drawer (Phase 5).

Tasks:
- [x] Implement pure `core/script_codec.py` (CSIF v1): `@@Speaker`, `@@_`, `@@!meta`, sparse addressing.
- [x] Implement shared `_commit_widget_edit` path for keyboard, ribbon, cut/paste, and font size.
- [x] Fix Box 0 flush/save path; prevent dialogue injection while Box 0 is active.
- [x] Fix plain-text view routing in `on_save()`.
- [x] Remove widget aliasing; resolve active card dynamically.
- [x] Install first-position `MisoraShortcuts` bindtag router on all text/entry widgets.
- [x] Fix missing `_push_undo`, `_sync_clean_view_to_current_box`, and `_dirty_state_changed` helpers.
- [x] Batch undo: apply all deltas to model first, refresh UI once in `finally`.
- [x] Pass immutable snapshots to background search workers; protect Replace All bundle changes in undo.
- [x] Add Save/Discard/Cancel prompts on dirty close and app exit; add `reload_from_disk=True` to revert.
- [x] Fix gradient comma emitter to emit hyphen syntax.

### Phase 3 — Startup Performance & Configuration Safety
Scope: `misora.bat`, `misora.py` bootstrap, `assets/splash.py`, `core/bundle_io.py` lazy import, `core/logger.py`, tests.

Tasks:
- [x] Remove `UnityPy` probe loops from `misora.bat`.
- [x] Lazy-load `bundle_io` and `UnityPy` under lock; decouple `core/__init__.py`.
- [x] Maintain single-process architecture for splash.
- [x] Defer session restore until root window is displayed.
- [x] Preserve corrupt config recovery copy (`.bak`) before falling back to defaults.
- [x] Clean machine-specific paths from repository `misora_config.json`.
- [x] Move logger file writes and flushes to background queue.

### Phase 4 — Import/Export, Paste Preview, & UI Polish
Scope: `misora.py`, root `__init__.py`, `assets/splash.py` (version source), tests.

Tasks:
- [x] File Import/Export menus for CSIF interchange (`Ctrl+Shift+I`, `Ctrl+Shift+E`).
- [x] Upgrade paste confirmation into full Paste Preview dialog (`ScriptPastePreviewDialog`).
- [x] Remove redundant ribbon buttons; unify version string to root `__version__ = "1.3.3"`.
- [x] Add safe tooltip lifecycle management with `winfo_exists` checks.

### Phase 5 — Shared NGUI, MTL Engine, & Preview Safety
Scope: `core/ngui_tags.py`, `core/mtl_engine.py`, `misora.py`, tests.

Tasks:
- [x] Create central `core/ngui_tags.py` with complete tag patterns, size, ruby, and hyphen gradients.
- [x] Enable TLS certificate verification on all outbound requests; store API keys in DPAPI/keyring.
- [x] Use DeepL `/v2/usage` status endpoint for connection test.
- [x] Implement Game Box Preview with rendered text overflow measurement.
- [x] Add Translation Lock protection for proofread boxes.

### Phase 6 — Safety & Multi-Document Architecture Roadmap (S-Series)

- [x] **S0 — Preflight Baseline & Repository Hygiene (2026-11-21)**: Baseline verification, `.gitattributes`, conflict marker resolution, preflight gate.
- [x] **S1 — Staged `open_file()` Loading & Safety (2026-11-21)**: Local variable staging before state mutation, strict UTF-8 validation, pending edit flush routing across Page/Continuous views, zero document corruption on load failure.
- [x] **S2 — Minimum Per-Document Dirty Contract & Explicit `on_save() -> bool` (2026-11-22)**:
  - Single authoritative dirty flag per document in `open_documents[path]["dirty"]`.
  - Flag-only `_mark_document_dirty(path)` with zero Tk calls / zero dock/title rebuilds (Rule 13 / Rule 15 safe).
  - Pure-UI `_dirty_state_changed()` decoupled from `undo_journal.is_clean()` (eliminates cross-file false-clean clobber).
  - True no-op `<KeyRelease>` guards on dialogue and speaker editors.
  - Plain-text cache content synchronization (`open_documents[path]["plain_text"]`).
  - Deterministic per-document saved-state checkpoints (`_saved_state_checkpoints`) with uncached fallback to `undo_journal.is_clean()`.
  - Explicit `on_save() -> bool` return value with outer `try...except`, secondary XUAT sync failure isolation (`_modified_boxes` retained, warning logged, returns `True`).
- [x] **S3 — Safe Document Close & Atomic Persistence (2026-11-22)**:
  - `close_file()` aborts on Save/Discard/Cancel cancel or save failure; returns explicit `bool`; prunes checkpoints.
  - `_on_app_exit()` multi-document Save-All loop with cancellation and per-file prompt support.
  - Raw plain-text and v2 story script saves unified under shared `write_atomic_utf8()` helper.
  - Central active widget flush helper `_flush_active_widget() -> bool`.
- [x] **S4 — View/Model Synchronization & Widget Caret Decoupling (2026-11-22)**:
  - Pruned stale card widgets via `_clear_card_registry()` in `close_file()` empty-state and `_update_views()` plain-text switch (`STALE-CARD-REGISTRY` resolved).
  - Hardened ribbon targets (`on_text_cut/copy/paste`) via `_get_card_text_widget()` with `winfo_exists()` guard and `txt_dialogue` fallback.
  - Verified re-entrancy (`try/finally` in `_render_continuous_view`), caret preservation across view toggles, and suppress-guard invariants.
- [x] **S5 — Multi-File Replace-All & BulkFileDelta Disk Safety (2026-11-22)**:
  - Atomic file replacement via `write_atomic_utf8()` in `on_replace_all()` and `_apply_delta(BulkFileDelta)` (`BULK-DELTA-NONATOMIC` resolved).
  - All-or-nothing transaction rollback in `_apply_delta(BulkFileDelta)` if any file fails mid-batch.
  - In-memory `open_documents` cache & checkpoints synchronization for open files modified in bulk.
  - Checkpoint evaluation for `BulkFileDelta` paths in `_evaluate_checkpoints_for_op()`.
- [x] **S6 — Threading Architecture Decoupling (Rule 15) (2026-11-22)**:
  - UI thread snapshot isolation in `on_start_search()` resolves `SEARCH-RACE`.
  - Redesigned `BatchTranslateDialog.worker()` to communicate strictly via thread-safe `queue.Queue` with main-thread polling pump `_poll_worker_queue()`.
  - Eliminated pre-existing Rule 15 violation where background threads mutate Tkinter or `UndoJournal` state directly.
- [x] **S7 — Per-File MasterUndoJournal Revision Rewrite (F16) & Speaker Commit Unification (F20) (2026-11-22)**:
  - Isolated per-file undo/redo stacks and independent per-file revision tracking (`_FileJournalState`).
  - Active document synchronization on file open, switch, and close.
  - Closed document journal purging via `prune_file()` prevents silent reopen on undo (Rule 16).
  - Central speaker edit commit unification: `_commit_speaker_edit()` resolves valid text (never `None`), eliminating multi-segment crash risk.
  - Speaker Box 0 protection and no-op `<KeyRelease>` guards.
- [x] **S8a — Dialog Architecture & Modal Grab Hardening (2026-11-22)**:
  - Added robust `safe_grab_release(dialog)` helper handling active grabs, destroyed widgets, and `None` arguments without throwing `TclError`.
  - Audited and hardened all `tk.Toplevel` modal dialogs (`_on_dnd_settings_dialog`, `_prompt_append_speaker_attribute`, `on_insert_ruby`, `on_launch_datamine`, `on_open_paths_dialog`, `ScriptPastePreviewDialog`, `MTLSettingsDialog`, `AIPromptSettingsDialog`, `TranslatorAssistantDialog`, `BatchTranslateDialog`):
    - All modal dialogs release grab cleanly via `safe_grab_release()` before `destroy()`.
    - All modal dialogs register explicit `WM_DELETE_WINDOW` protocol handlers.
    - All modal dialogs bind `<Escape>` with optional parameter default (`lambda _e=None: ...`) for keyboard dismissal and grab release.
  - Enforced Tk variable ownership per Rule 3 (`master=self` / `master=dlg`) across all dialogs, validated via AST inspection in test suite.
  - Hardened `BatchTranslateDialog` window close to abort background worker thread, end undo batch, and release modal grab.
  - Covered by new test suite `tests/test_s8a_dialog_grab_safety.py` (10/10 PASS).
- [x] **S8b-1 — Status-Bar & Toast Notification Manager (2026-11-22)**:
  - Unified status/toast architecture with sequential FIFO queue (`_toast_queue = collections.deque()`).
  - Safe dismissal (`_dismiss_toast`) and interactive click-to-dismiss (`<Button-1>`).
  - High-contrast error styling and optional auto-reset timeout in `set_status()`.
  - Non-occluding geometry (`relx=1.0, rely=1.0, x=-16, y=-52, anchor="se"`), floating above action buttons.
  - Exception surfacing in `report_callback_exception()` per Rule 28.
  - Safe timer teardown in `destroy()` eliminating `invalid command name "...hide"` errors.
  - Covered by new test suite `tests/test_s8b1_notification_manager.py` (10/10 PASS).
- [x] **S8b-2 — Asset & Bundle Memory Leak Guards (2026-11-22)**:
  - Cycle-breaking `dispose_unity_env` helper in `core/bundle_io.py` releases circular UnityPy object/buffer cycles.
  - Search engine and multi-file replace-all immediately dispose loaded bundle environments.
  - Repacked verification environment in `save_bundle_story` cleanly disposed in `finally`.
  - Document close and application teardown lifecycle disposals in `close_file()` and `destroy()`.
  - Bounded icon cache (`MAX_ICON_CACHE = 128`), dead widget icon pruning (`prune_icon_cache`), and color picker buffer cleanup.
  - Covered by new test suite `tests/test_s8b2_memory_guards.py` (8/8 PASS).
- [x] **S8b-3 — Encoding Detection & Strict Fallback Architecture (2026-11-22)**:
  - Centralized encoding engine in `core/text_encoding.py` (`DecodedText`, `detect_encoding_and_decode`, `encode_with_metadata`, `read_text_file_strictly`, `write_atomic_encoded`).
  - Deterministic BOM detection (`utf-8-sig`, `utf-16-le`, `utf-16-be`) and strict CP932 / Windows-31J Japanese fallback with CJK plausibility validation.
  - Complete elimination of silent corruption via `errors="replace"` across text importers, multi-file replacement, and search engine (Rule 10).
  - Preservation of BOM, native CRLF/LF line endings, and key whitespace across all text write operations.
  - Covered by new test suite `tests/test_s8b3_encoding_detection.py` (10/10 PASS).
- [x] **S8b-4 — Remaining UI Polishing & Responsive Scaling (2026-11-23)**:
  - Eliminated runtime DPI awareness mutations in `NguiColorPickerPopup._toggle_eyedropper()`, fulfilling Rule 23; added one-time `init_process_dpi_awareness()` at startup in `main()`.
  - Resolved dock collapse geometry lock bug via explicit `self._dock_collapsed` state tracking and dynamic minsize switching (`paneconfigure(minsize=0)` / `paneconfigure(minsize=160)`).
  - Enforced minsize constraints on `h_paned` (`left_frame >= 160`, `right_frame >= 420`, `side_drawer >= 260`) and `v_paned` (`top_view >= 140`, `bottom_view >= 80`).
  - Added unicode fallback text, theme-contrasting foregrounds (`best_contrast_fg`), and accessible tooltips across all ribbon and toolbar icon-only buttons (Rule 21).
  - Enhanced `ToolTip.__init__` to store `setattr(self.widget, "_tooltip", self)` for inspection.
  - Covered by new test suite `tests/test_s8b4_ui_polishing.py` (8/8 PASS).
  - **Milestone**: Phase 6 (S-Series: S0 through S8b-4) is 100% COMPLETE.

---

## 8. Fixture & Platform Observations

Direct verification on disk and user platform testing have resolved key platform assumptions:

1. **Line Break & Word Wrap Convention**:
   - In raw scripts, narration contains no hard breaks; NGUI auto-wraps it in-game. XUAT exports contain `\n` because XUAT captures text post-render.
   - Dialogue contains explicit line breaks. While NGUI dialogue boxes can auto-wrap clean text, non-NGUI dialogue scenes do **not** auto-wrap and bleed outside box bounds.
   - **Rule**: Never strip explicit breaks from dialogue. Multiline XUAT values must escape newlines (`\n`) to preserve single-line dictionary structure.
2. **File Locks & Anti-Virus (Windows Defender)**:
   - No overt blocking notifications reported. Bounded retry backoff on `os.replace()` handles transient background scanner locks during atomic saves.
3. **Memory & UI Scaling**:
   - 1 story file (142 boxes) consumes ~160 MB RAM. 135 concurrent files show responsive switching on modern hardware (i7-13700KF).
   - Card virtualization remains a valid P2 optimization for lower-spec targets.
4. **Remaining Open Questions**:
   - Exact command arities for chapters using 3+ arguments in metadata or choice branches.
   - Presence of multiple story TextAssets within a single production `.unity3d` bundle.

## 9. GitHub Documentation Audit (2026-11-21)

- `HEAD` matches `origin/main`; both GitHub API and the tracked tree contain `docs/ANTIGRAVITY_PROMPTS.md` and `docs/SCRIPT_FORMAT.md`.
- The reviewed `README.md` and `docs/` history contains no documentation deletions or detected renames. Every local image/link reference in `README.md` resolves.
- The README's Project Structure list is stale: it omits `docs/`, newer files under `core/` and `tests/`, and `assets/Splash_4.jpg` through `Splash_8.jpg`. This is a README accuracy issue, not missing repository content.
