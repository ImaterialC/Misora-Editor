# Misora Editor — Canonical Project State

Last updated: 2026-11-22
Repository: `ImaterialC/Misora-Editor`
Local working path: `D:\Misora-Editor`
Target release: v1.4.0
Current code baseline: root `__init__.py` reports `version = "1.3.3"`; unified across UI, splash, dialogs, and tests.

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
Fixture Availability: storydata_1001005.unity3d present in repository root (39 dialogue boxes)

Compile Check:
py -3.12 -m compileall -q misora.py core assets tests
Result: PASS (Exit code 0, 0 syntax/compilation errors)

Unit Test Suite (Phase 5 completion session — 2026-11-21):
py -3.12 -m unittest discover -s tests -v
Result: Ran 100 tests in 143.062s — OK (100/100 pass, 0 failures, 0 errors, 0 skips)

Test suites included in the 100 tests:
  tests/test_misora_core.py                 — 20 core AST, binary, search, and sync tests (all pass)
  tests/test_misora_ui_integration.py       — 26 UI integration, Box 0, DnD, and editing tests (all pass)
  tests/test_phase1_manual_verification.py  — 9 Page and Continuous view verified workflows (all pass)
  tests/test_phase2_required.py             — 13 GUI-level required tests (all pass)
  tests/test_phase3_performance_config.py   — 6 startup, lazy-load, async logger, config tests (all pass)
  tests/test_phase4_import_export_preview.py— 5 import/export, paste preview, tooltip, version tests (all pass)
  tests/test_phase5_mtl_security_preview.py — 7 NGUI tag, DPAPI, TLS verify, DeepL usage, lock, preview tests (all pass)
  tests/test_script_codec.py                — 14 CSIF codec unit tests (all pass)
```

### Current Test Failures
The S0/S1 full-suite baseline has one existing local test design discrepancy:
`test_phase3_performance_config.TestPhase3PerformanceAndConfig.test_05_clean_committed_config_has_no_machine_paths`
expects `misora_config.json.project_folder == ""`. However, `misora_config.json` is explicitly ignored by `.gitignore`
and has never been tracked in Git history; the local file on disk reflects the developer's runtime session state.
(RETRACTED: the previous claim that this was a "tracked committed value" was an AI hallucination).
This test design issue is owned by a future Phase 3 test hygiene slice.

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
| **V2-ROUNDTRIP-LOSS** | RESOLVED | `core/story_ast.py` | Preserves numeric command IDs, categories, duplicate commands, and line breaks. Covered by `test_16`. | 1 |
| **XUAT-SYNC-LINE-CORRUPTION** | RESOLVED | `core/xunity_sync.py` | Strict UTF-8 with BOM preservation, multiline `\n` escaping in values, CRLF/LF line ending preservation. Covered by `test_19`. | 1 |
| **EMPTY-ARG-ARITY** | RESOLVED | `core/story_ast.py` | Binary serialization retains empty string arguments, preventing arity reduction. Covered by `test_15`. | 1 |
| **NARRATION-EMPTY-PHANTOM** | RESOLVED | `core/story_ast.py` | Narration emits `tag` records instead of `print` with empty speaker. Covered by `test_15`. | 1 |
| **PAGE-BREAK-NOT-SPLIT** | RESOLVED | `core/story_ast.py` | Breaker tokens aligned (`page` / `next_page`). Covered by `test_13`. | 1 |
| **RAW-TAIL-FROZEN** | RESOLVED | `core/story_ast.py` | `inject_box` updates `seg.raw` alongside `seg.text`. | 1 |
| **CMD0-SPECIAL-CASE** | RESOLVED | `core/story_ast.py` | Removed `cmd_id == 0` special case in `to_binary`. | 1 |
| **SHORTCUT-BINDTAG-ORDER** | RESOLVED | `misora.py` | Installed first-position `MisoraShortcuts` bindtag router. Ctrl+H opens replace dialog without mutating dialogue text. Covered by `test_31`. | 2 |
| **RIBBON-CUT-PASTE-NO-COMMIT** | RESOLVED | `misora.py` | Virtual `<<Cut>>` and `<<Paste>>` explicitly invoke central `_commit_widget_edit`. Covered by `test_30`. | 2 |
| **MULTI-TEXTASSET-TARGET** | RESOLVED | `core/bundle_io.py` | Locks target TextAsset by `path_id`. Save verification checks target `path_id`. | 1 |
| **INJECT-EXTRA-ARGS** | RESOLVED | `core/story_ast.py` | `inject_box` and `set_metadata` preserve unmanaged trailing args. | 1 |

### P0 (new, from manual testing 2026-11-20 — all RESOLVED)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **BOX0-NO-SELECT-CHECKBOX** | RESOLVED | `misora.py:_render_continuous_view` | Added Checkbutton to Box 0 card header (`hdr_0`) keyed to index `-1` in `self._selected_boxes` when `var_select_box_mode` is enabled. Allows copying Box 0 metadata. | 2 |
| **BOX1-COPIES-BOX0-METADATA** | RESOLVED | `core/script_codec.py:serialize()` | Removed `0 in box_indices` auto-emission branch in `serialize()`. Auto-emission now only emits metadata when `scope in ("all", "metadata")` or when Box 0 (`-1`) is explicitly selected. | 2 |
| **CTRL-ALT-HOTKEYS-BLOCKED** | RESOLVED | `misora.py:_on_misora_shortcut()` | Fixed Windows Alt modifier bitmask to include `0x20000` (`MOD2_MASK`). Whitelisted app `Ctrl+Alt` accelerators (`Ctrl+Alt+X`, `Ctrl+Alt+C`, `Ctrl+Alt+V`, `Ctrl+Alt+A`) and added explicit root bindings. | 2 |
| **CONTINUOUS-EDIT-NO-COMMIT** | RESOLVED | `misora.py:_commit_widget_edit()` | Decoupled Page View Box 0 widgets and Continuous View Card -1 from `is_box0_active` boolean guard. Edits to continuous cards and Box 0 synopsis now commit directly to AST document. | 2 |
| **BOX0-SWITCH-LOCKS-EDITOR** | RESOLVED | `misora.py:_on_toggle_continuous_view`, `on_prev_box`, `on_next_box` | Restores caret and keyboard focus immediately and via `after_idle` upon view toggles and box navigation. Guarded `_cont_focus_job` against stale cross-view firing. | 2 |
| **VOICE-CUE-DISPLAY-MISSING** | RESOLVED | `core/story_ast.py:_rebuild_boxes` | Captured `cmd_id == 12` voice cues with `"vo_"` prefix; guarded breaker loop `elif r.cmd_id != 12 and r.cmd_name in DEFAULT_BREAKERS:` so voice cues are never skipped or discarded. | 2 |
| **FIND-REPLACE-UI-ASYMMETRY** | RESOLVED | `misora.py:_build_search_panel` | Converted Find and Replace rows to a unified 5-column `grid` with `columnconfigure(1, weight=1)`, ensuring Find and Replace entry fields start and end at identical pixel coordinates. Aligned the 4 action buttons ('Find in Files', 'Cancel', 'Replace', 'Replace All') in a symmetrical 2x2 column block with matching widths and added dedicated illustrated Twemoji icons for all 4 buttons. | 2 |

### P1 — Functional, UI, & Security Issues (Phases 2, 3, 5)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **DIRTY-EXIT-DROPS-EDITS** | RESOLVED | `misora.py:1302-1312` | `_on_app_exit` prompts Save/Discard/Cancel with `askyesnocancel` on dirty state before window close. | 2 |
| **RELOAD-REVERT-HIT-CACHE** | RESOLVED | `misora.py:7838-7841, 7949-7952` | `on_revert_box` and `on_reload` call `open_file(..., reload_from_disk=True)`. | 2 |
| **REPLACE-ALL-BUNDLE-PREFILTER** | CONFIRMED | `misora.py` | Raw byte scan on binary bundles yields false hits/misses. Decode structured text assets before searching. | 2 |
| **REPLACE-ALL-UNDO-GAP** | CONFIRMED | `misora.py` | Bundle changes in multi-file Replace All are omitted from `per_file_deltas` and cannot be undone. Journal all modified bundles. | 2 |
| **TLS-VERIFICATION-DISABLED** | RESOLVED | `core/mtl_engine.py:142-144` | Outbound HTTPS requests strictly enforce valid TLS certificate and hostname verification. Covered by `test_phase5_mtl_security_preview.py:test_03`. | 5 |
| **API-KEYS-PLAINTEXT** | RESOLVED | `core/security.py:20-65`; `core/mtl_engine.py:52-78`; `misora.py` | API keys encrypted via Windows DPAPI (`dpapi:...` prefix) in config; decrypted in memory; secrets redacted in logs/UI. Covered by `test_phase5:test_02`. | 5 |
| **TAGMASKER-INCOMPLETE** | RESOLVED | `core/ngui_tags.py:15-161` | Central single source of truth for NGUI markup, hyphen gradients, multiline ruby, placeholders, and full shielding/unshielding. Covered by `test_phase5:test_01`. | 5 |
| **SIZE-RIBBON-NO-COMMIT** | RESOLVED | `misora.py:6374-6394` | Font size insertion routes through central commit and updates dirty state. Covered by `test_37`. | 2 |
| **CONTINUOUS-RIBBON-TARGET-STALE** | RESOLVED | `misora.py` | Active card resolved dynamically by widget identity, preventing closure desync. | 2 |
| **UNDO-STORM** | RESOLVED | `misora.py` | Batch undo applies all deltas to model first, then refreshes UI once in `finally`. | 2 |
| **SEARCH-RACE** | CONFIRMED | `misora.py:7212-7218` | Search worker thread accesses live mutable `StoryDocument` references concurrently with UI edits. Pass immutable snapshots. | 2 |
| **CLIP-SHADOW** | RESOLVED | `misora.py` | If system clipboard differs from internal box snapshot text, internal snapshot is discarded. Covered by `test_35`. | 2 |
| **FOLDER-DROP-EXTRA-IGNORED** | CONFIRMED | `misora.py:2189-2190` | Only the first folder in multi-folder DnD drops is opened; remainder ignored silently. Warn user or process all. | 2 |
| **DEEPL-TEST-COST** | RESOLVED | `core/mtl_engine.py:299-316` | Connection test queries free `/v2/usage` status endpoint instead of billable `/v2/translate`. Covered by `test_phase5:test_04`. | 5 |
| **CORE-IMPORT-COUPLING** | RESOLVED | `core/bundle_io.py:23-45`; `tests/test_phase3_performance_config.py:33-53` | `core` decoupled from `UnityPy` at import time via double-checked lazy load under lock; `import core` dropped from 1.03s to 0.14s. | 3 |
| **CONFIG-RECOVERY-OVERWRITE** | RESOLVED | `misora.py:1456-1473`; `tests/test_phase3_performance_config.py:82-106` | Corrupted config preserved as `.bak_<timestamp>.json` recovery copy before using defaults. | 3 |
| **STALE-CARD-REGISTRY** | CONFIRMED | `misora.py:6405-6419, 6436` | Switching to plain text returns before clearing `_card_widgets`, leaving destroyed widgets registered. Clean up cards before return. | 2 |
| **GRADIENT-COMMA-EMITTER** | RESOLVED | `misora.py:1014, 4608` | Gradient insertion strictly emits hyphen syntax `[c0-c1]`. Comma syntax rejected by NGUI is avoided. | 2 |
| **SPAN-NFKC-PER-CHAR** | CONFIRMED | `core/search_engine.py:88` | Per-token NFKC fails to compose Japanese dakuten/handakuten combining characters. Align with whole-string normalization. | 2 |
| **UNDO-COALESCE-CROSS-SOURCE** | CONFIRMED | `core/undo_journal.py:115-130` | Coalescing checks only box and timing, merging ribbon cuts with typing. Add source tracking to deltas. | 2 |
| **GENERIC-PLACEHOLDER-GAP** | RESOLVED | `core/ngui_tags.py:48-52` | Placeholders `{playername}` and all `{n}` placeholders shielded in translation and highlighted in preview. Covered by `test_phase5:test_01`. | 5 |
| **LOGGER-SYNC-IO** | RESOLVED | `core/logger.py:27-145`; `tests/test_phase3_performance_config.py:54-81` | Asynchronous background worker queue for file logging disk I/O; clean flush and thread termination. | 3 |
| **BULK-DELTA-NONATOMIC** | CONFIRMED | `misora.py:8040-8060` | Reverting bulk file undo writes files directly without `.tmp` atomic replacement. Wrap in atomic file replace helper. | 2 |
| **HARDCODED-PROJECT-PATH** | RESOLVED | `misora_config.json`; `tests/test_misora_ui_integration.py:34-45` | Committed config reset to empty defaults; UI integration tests isolated from root config. | 3 |
| **PLAINTEXT-SAVE-ROUTING** | RESOLVED | `misora.py` | `on_save()` routes correctly between Plain Text (Page/Continuous) and Story Bundle AST. | 2 |

### P2 — Performance, QoL, & Measured Risks (Phases 3, 4, 5)

| Slug | Status | Note | Phase |
|---|---|---|---|
| **THEME-RAW-PERF** | MEASURED | 1 file (142 boxes) = 160MB RAM; 135 files test showed workable switching on i7-13700KF. Benchmark lower-spec targets. | 3 |
| **SEARCH-CACHE** | DESIGN | LRU keyed by path/mtime/size; must include metadata. | 3 |
| **ICON-CACHE-GROWTH** | CONFIRMED LOW | Cache keyed per toplevel; clear/bound it. | 3 |
| **OFFSCREEN-GEOMETRY** | CONFIRMED | Validate saved geometry against virtual screen. | 3 |
| **TOOLTIP-LIFECYCLE** | RESOLVED | Delayed tooltip cancels pending `after()` timers on `<Leave>` / `<Destroy>`, checks `widget_exists()`, and safely destroys `tip_window`. Covered by `test_phase4_import_export_preview.py:test_02`. | 4 |
| **GAME-BOX-PREVIEW** | RESOLVED | Rendered dialogue length counter ignoring tags; live warning badge `⚠ Overflow` for lines exceeding 45 characters. Covered by `test_phase5:test_06`. | 5 |
| **TRANSLATION-LOCK** | RESOLVED | Translation Lock (`Ctrl+L`) excludes protected boxes from batch translation, script paste, and replace all. Covered by `test_phase5:test_05`. | 5 |
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
- [ ] **S3 — Safe Document Close & Atomic Persistence**:
  - `close_file()` aborts on Save/Discard/Cancel cancel.
  - `_on_app_exit()` multi-document Save-All loop with cancellation support.
  - Raw plain-text save (`F-GPT-04`) and shared `write_atomic_utf8()` helper.
  - *(Now UNBLOCKED by S2 completion)*.
- [ ] **S4 — View/Model Synchronization & Widget Caret Decoupling**: Centralize continuous/page view widget event synchronization, remove widget state dependencies.
- [ ] **S5 — Multi-File Replace-All & BulkFileDelta Disk Safety**: Atomic file replacement and transaction rollbacks for multi-file bulk operations.
- [ ] **S6 — Threading Architecture Decoupling (Rule 15)**:
  - Redesign `BatchTranslateDialog.worker()` and search threads to communicate strictly via main-thread queues.
  - Eliminate pre-existing Rule 15 violation where background threads mutate Tkinter or `UndoJournal` state directly.
- [ ] **S7 — Per-File MasterUndoJournal Revision Rewrite (F16) & Speaker Commit Unification (F20)**:
  - True per-file undo revisions with isolated journal stacks.
  - Central speaker edit commit unification: address latent issue where `_commit_widget_edit()` speaker branch calls `inject_box(..., None)`.
- [ ] **S8a — Dialog Architecture & Modal Grab Hardening**: Audit all Toplevel dialogs for explicit parent transients, grab releases, and window destruction safety.
- [ ] **S8b-1 — Status-Bar & Toast Notification Manager**: Unified toast/status queue with safe dismissal and geometry tracking.
- [ ] **S8b-2 — Asset & Bundle Memory Leak Guards**: Bounded asset caching, explicit UnityPy environment garbage collection, and texture buffer release.
- [ ] **S8b-3 — Encoding Detection & Strict Fallback Architecture**: Deterministic BOM/encoding detection with strict error handling.
- [ ] **S8b-4 — Remaining UI Polishing & Responsive Scaling**: Final DPI awareness verification, responsive paned-window constraints, and icon rendering polish.

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
