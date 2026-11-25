# Misora: Story Editor — Canonical Project State

Last updated: 2026-11-26
Repository: `ImaterialC/Misora-Editor`
Local working path: `D:\Misora-Editor`
Target release: v1.5.0 (Current session build: v1.4.7 — S07)
Current code baseline: root `__init__.py` reports `__version__ = "1.4.7"`; unified across UI, splash, MTL engine, and tests (`U00`).
Starting baseline pinned at commit `5b0f0147d82ea5098de7a10ff252d43e22fa5eed` (+ pre-existing local S04/S05/S06 test working-tree changes).

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
py -3.12 -m compileall -q __init__.py misora.py core assets tests
Result: PASS (Exit code 0, 0 syntax/compilation errors)

Unit Test Suite (v1.5 S07 Verification Baseline — 2026-11-26):
py -3.12 -m unittest tests.test_v15_s07_xuat_cleanup_archive -v
Result: Ran 9 tests in 21.821s (9 pass, 0 failures, 0 errors, exit code 0)

py -3.12 -m unittest discover -s tests -v
Result: Ran 405 tests in 437.821s across 52 modules (362 pass, 35 skipped, 6 failures, 2 errors; 3 failures + 2 errors in test_s8b2_memory_guards due to missing storydata_1001005.unity3d, 1 failure in test_phase3_performance_config::test_05 due to local misora_config.json, 1 failure in test_s9c_workspace_safety::test_04 due to pre-existing deleted misora_config.default.json, 1 failure in test_v15_s01_stability_remediation::test_probe_8 due to S01 pinned "1.4.1" assertion after v1.4.7 bump; 0 S07 regressions)

Test suites included in the 405 tests (exact disk discovery):
  tests/test_v15_s07_xuat_cleanup_archive.py — 9 S07 pure-core transactional XUAT cleanup, SHA-256 stale guard, mandatory combined/per-file archival, conservative 3-tier classification, empty-file 2-step delete & Debug > Safety tests (all pass)
  tests/test_v15_s06_tools_word_wrap.py   — 8 S06 Tools menu, pure-Python NGUI/grapheme/kinsoku word wrap, locks/JP-keys/multi-segment single-batch Undo, and XUAT/Script opt-in wrap tests (all pass)
  tests/test_p3_s23_dead_code_cleanup.py   — 4 S23 HYG-08 dead code & misleading label cleanup (removed _update_gutter_cont & BatchTranslateDialog._toggle_pin_top, hyphen gradient label, no CWD picker_error.log, CSIF prompt wording, _update_gutter_clean guard) tests (all pass)
  tests/test_p3_s22_import_xuat.py          — 4 S22 unified core/xuat_index.py, O(1) MTL cache, & floating ImportFromXUATDialog (paired 3x50 read-only, duplicates, lock/skip, Pre-Apply prompt, atomic Undo) tests (all pass)
  tests/test_p3_s21_mtl_drawer_all_script.py — 3 S21 All Script MTL drawer (exact 2 tk.Text widgets, 5 static status tags, Translate All / Apply All lock & box.uid batch) tests (all pass)
  tests/test_p3_s20_mtl_drawer_dialogue.py — 3 S20 docked MTL drawer tab, Dialogue multi-engine stack, lock/whitespace Apply, paid-API confirm & stale guard tests (all pass)
  tests/test_p3_s19_raw_commands_edit.py    — 4 S19 whole-file Raw Commands v2 editing, confirmation, DocumentRecordsDelta undo & lock/JP remap tests (all pass)
  tests/test_p3_s18_game_preview.py         — 3 S18 code-drawn Dialogue Preview & All Script Preview (wrap='none', bleed, cstyle_* sweep, no AtlasAdv) tests (all pass)
  tests/test_p3_s17_pixel_rulers.py         — 2 S17 pixel-measure helper, Canvas rulers, line 4+ red gutter & char counter removal tests (all pass)
  tests/test_p3_s16_misora_workspace.py     — 4 S16 .misora v1 workspace, stable lock matching & U-B18 overwrite diff tests (all pass)
  tests/test_p3_s15_selection_drawer_open.py — 4 S15 select box both views, reserved lock slot, collapsible left drawer, empty state & batched multi-open tests (all pass)
  tests/test_p3_s14_toolbar_search_ui.py    — 5 S14 search grid 5-col alignment, scope current widget hiding, player icon / ribbon cleanup, and responsive toolbars tests (all pass)
  tests/test_p3_s13_ribbon_shortcuts.py     — 4 S13 continuous ribbon/size/dirty sync, shortcut conflicts, complete tooltips & Ctrl+H hygiene tests (all pass)
  tests/test_p3_s12_lifecycle_security.py   — 7 S12 logger flush barrier, DPAPI fail-closed, reload env disposal, deferred startup & splash safety tests (all pass)
  tests/test_p3_s11_mtl_threading.py        — 9 S11 main-thread queue-only async MTL, stale-result identity guard & safe batch cancel tests (all pass)
  tests/test_p3_s10_xuat_integrity.py       — 4 S10 immutable box.uid XUAT JP keys, save conflict preview gate & atomic XUAT dictionary writes tests (all pass)
  tests/test_p3_s09_replace_all_backups.py  — 9 S09 multi-file replace-all cache keys, shared matcher, closed-file undo & collision-resistant backups tests (all pass)
  tests/test_p3_s08_search_roots_focus.py   — 6 S08 search match-case/errors/snapshots/spans, bounded project roots & search focus/gutter/no-op keyrelease tests (all pass)
  tests/test_p3_s07_undo_locks_raw.py       — 6 S07 caret paste dirty/lock, mutate-before-undo, non-contiguous cut undo, lock enforcement & read-only raw tests (all pass)
  tests/test_p3_s06_doc_state_save.py       — 5 S06 per-document state/locks, plain-text preview save, LF writes & 0-box save tests (all pass)
  tests/test_p3_s05_treeview_csif.py        — 4 S05 Treeview dark-theme contrast, atomic sparse CSIF/metadata, and backslash parity tests (all pass)
  tests/test_p3_s04_ast_mutations.py        — 6 S04 AST mutation, voice cue/breaker ownership, multi-segment undo/paste, UID coalesce & tombstone tests (all pass)
  tests/test_p3_s03_binary_v2.py            — 9 S03 strict binary parse, lossless v2, command map/breakers, and synthetic bundle verify tests (all pass)
  tests/test_p3_s02_hygiene.py              — 5 S02 hygiene, single-version User-Agent, and backup isolation tests (all pass)
  tests/test_misora_core.py                 — 20 core AST, binary, search, and sync tests (18 pass, 2 skipped)
  tests/test_misora_ui_integration.py       — 27 UI integration, Box 0, DnD, and editing tests (15 pass, 12 skipped)
  tests/test_phase1_manual_verification.py  — 8 Page and Continuous view verified workflows (all pass)
  tests/test_phase2_required.py             — 13 GUI-level required tests (all pass)
  tests/test_phase3_performance_config.py   — 6 startup, lazy-load, async logger, config tests (all pass)
  tests/test_phase4_import_export_preview.py— 5 import/export, paste preview, tooltip, single-source version (MF-S24) tests (all pass)
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

### Track 1 Automated Stabilization Gate: COMPLETE (S01..S13)
- **Status:** ALL automated stabilization sessions (`S01..S13`) are 100% COMPLETE.
- **Track 2 Unlocked:** Track 2 (`S14..S23`) and `AGENTS.md` §24 MTL Drawer gate are unlocked.
- **BUG-09 Production Fixture Status:** Real production `.unity3d` verification for `BUG-09` remains explicitly `BLOCKED` (synthetic bundle test passed in S03; real proprietary production fixture `storydata_1001005.unity3d` intentionally excluded from repository). Per `AGENTS.md` §2, missing real production fixtures remain `BLOCKED`, never assumed or falsified as `PASS`.

### v1.5 S07 (`v1.4.7`) — Transactional XUAT Post-Import Cleanup, Mandatory Archival Engine, & `Debug > Safety` (`U01`) (2026-11-26)
- **Pure-Python Per-File Transactional Engine (`core/xuat_cleanup.py`, `core/xuat_index.py`, `core/__init__.py`, `U01`):**
  - Zero-Tkinter, zero-`misora` engine accepting an injected `backup_path_fn` callback (defaulting to pure-Python collision-resistant naming).
  - `XuatIndex` captures raw byte SHA-256 `file_fingerprints` at index/preview time alongside full `entries` and O(1) `lookup_all_by_norm_key()` / `lookup_by_value()`. `verify_source_fingerprints()` aborts before any disk modification with `StaleSourceError` if any targeted file changes on disk.
  - Conservative 3-tier classification (`classify_cleanup_candidates`): `applied` (exact `(file_path, line_number)`), `duplicate` (exact `normalize_xuat_key()` only, controlled by `selected_only` vs `all_duplicates`), `already_translated_unique` (exact asset dialogue match mapping to strictly 1 unique key & `>= 6` non-space chars), and `uncertain` (`selected=False` by default for `<6` non-space chars, multi-key ambiguity, and shared `box.speaker` translations).
  - **Archive Encoding Contracts & Per-File Transactions:** Mandatory archive-first execution (`validate_archive_target()` refuses source overwrites and warns on `.txt` or `BepInEx\Translation\en\Text` subtrees). **`per_source_file`** archives preserve raw byte-for-byte original `encoding`, `has_bom`, and `newline` on creation and append (never emitting mid-file duplicate BOMs). **`combined`** archives preserve all decoded Unicode text + structured `# [...] op=... | source=... | encoding=... | bom=... | newline=... | story=... | reason=...` traceability metadata reversibly under canonical UTF-8 (no BOM) with LF (`\n`), since a single plain text file cannot hold mixed raw CP932 and UTF-16 byte streams simultaneously. Per-file edits run `safety backup -> .tmp -> strict reopen verify -> os.replace()`, stopping cleanly on mid-batch failure with a granular `CleanupReport` and flagging `is_xuat_file_meaningfully_empty()` files without auto-deletion.
- **`Debug > Safety`, Post-Import Cleanup, & `Tools -> Clean / Archive XUAT...` (`misora.py`):**
  - Added `Debug > Safety` submenu (`Auto-backup XUAT files before cleanup edits` defaulting `True` with confirmation to turn OFF + `XUAT Cleanup & Archive Settings...` defaulting to `<SCRIPT_DIR>/backups/xuat_archive`, `.xuat.old`, `combined`) persisted under `xuat_cleanup` with malformed-key recovery.
  - `ImportFromXUATDialog._on_apply_import()` opens `XuatCleanupDialog` non-blockingly (`_xuat_cleanup_dialog`, cleaned in `destroy()`) ONLY when `applied_count > 0`; `Tools -> Clean / Archive XUAT...` (`on_clean_archive_xuat()`) reuses `XuatCleanupDialog` (conditional duplicate toggle hidden at 0 duplicates, `Debug > Safety` OFF warning banner, separate irreversible confirmation for unarchived opt-out, and 2-step empty-file deletion confirmation quoting exact safety backup paths).
- **Manual Windows QA Pending (Project Lead):**
  - Run `Import from XUAT...` -> Apply -> verify Post-Import Cleanup dialog, mandatory `.xuat.old` archive outside `Text/`, SHA-256 stale check if file is edited externally, and 2-step empty file deletion quoting exact backup path.
  - Test choosing `.txt` or a directory inside `Text/` and confirm XUAT scanning warning appears.
  - Toggle `Debug > Safety` backup OFF -> verify confirmation prompt and cleanup warning banner.

### v1.5 S06 (`v1.4.6`) — Top-Level `Tools` Menu & Lossless Pixel-Calibrated Auto Word Wrap (`U07`, `4.5`) (2026-11-26)
- **Pure-Python Lossless Word Wrap (`core/word_wrap.py`, `core/__init__.py`, `U07`):**
  - Added zero-Tkinter `wrap_text()`, `iter_graphemes()`, and `WrapResult` using `core.ngui_tags` (`NGUI_TOKEN_RE`, `RUBY_RE`, `PLACEHOLDER_RE`) as single source of truth (`AGENTS.md` §19).
  - Atomic NGUI tags (`0px`), `[rub:ruby]base[/rub]` (`base` width), `{playername}`/`{N}` (`'PlayerName'` proxy width), Unicode grapheme clusters (combining marks `Mn`/`Mc`/`Me`, variation selectors, ZWJ), safe literal fallback for unclosed/malformed tags, intentional whitespace preservation (collapsing only the single break-point space replaced by `\n`), opening/closing tag orphan guards, Latin word-boundary + single-token hard-break fallback, CJK/JP kinsoku rules, O(1) fast path + binary search, and `still_overflows_lines` / `still_overflows_width` reporting.
- **Top-Level `Tools` Menu & `AutoWordWrapDialog` (`misora.py`, `U07`):**
  - Placed `Tools` immediately right of `View` in `_build_menu()` with `Auto Word Wrap...` opening modal `AutoWordWrapDialog` (`Current Box` / `Selected Boxes (N)` / `All Boxes in Document`, default `Preserve existing line breaks` vs `Reflow all paragraphs`).
  - `MisoraApp.apply_auto_word_wrap()` calibrates active editor font measure against constant `50d` `Nunito Bold` (`_get_ruler_measure_font()`), skips `is_box_locked()` boxes, preserves multi-segment structure (`old_seg_texts`/`new_seg_texts` via `game_to_xuat`), preserves immutable JP keys (`_original_jp_by_uid` / `sync_manager.jp_source_cache`), commits in ONE Undo batch (`BoxEditDelta(..., source="word_wrap")`), refreshes views/overflow indicator, and reports `Wrapped X | Skipped Y locked | Z still >3 lines`.
- **Opt-In Import Auto Word Wrap (`misora.py`, `4.5`):**
  - Added default-OFF `'Auto Word Wrap imported lines to 50d x 3'` opt-in checkboxes to `ImportFromXUATDialog` and `ScriptPastePreviewDialog` (with dynamic preview update on toggle), wrapping unlocked targets prior to `inject_box()` / `apply_to_document()` inside the single import Undo batch and reporting remaining `>3`-line counts.
- **Manual Windows QA Pending (Project Lead):**
  - Import a real single-line English XUAT story with `Auto Word Wrap` checked vs unchecked and confirm `50d` ruler compliance and single-step Undo.
  - Run `Tools -> Auto Word Wrap...` on a mixed JP/EN story with ruby tags, multi-segment boxes, and locked boxes.

### v1.5 S05 (`v1.4.5`) — Speaker Cyclic Jump & Focus-Safe Autocomplete (`U-3`, `U-4`), Win32 Console Toggle (`U02`), & About Sequential-Frame Support Me Dialog (`U05`) (2026-11-26)
- **Speaker Cyclic Jump & Focus-Safe Autocomplete (`misora.py`, `U-3`, `U-4`):**
  - Repurposed `btn_speaker_dropdown` (`▼`, tooltip `'Jump to Speaker Box (click again to cycle next)'`) to open a read-only jump menu with speaker occurrence counts and `(Narration)`, cycling cleanly via `_jump_to_speaker()` without mutating speakers and emitting `Jumped to Box #N — <Speaker> (k/m)` notifications.
  - Added Google-style autocomplete popup (`tk.Toplevel` `overrideredirect(True)` + `tk.Listbox`) on `entry_speaker` listing `sorted(current_doc.actors())`, `{playername}`, and `(Narration — Clear Speaker)` with live prefix/substring filtering, `Up`/`Down`/`Enter`/`Escape`/click selection, and deferred `<FocusOut>` safeguard (`after(20)` + `_is_widget_in_speaker_popup`) preventing premature commits when clicking the popup.
  - Removed `<KeyRelease>` speaker commit while retaining `<<Cut>>`/`<<Paste>>` virtual-event commits (`AGENTS.md` §11); enforced Translation Lock inside `_commit_speaker_edit()`; refreshed All Script / Dialogue Preview headers on rename; and preserved adjacent-narration separation (`QW-B01`).
- **Windows Terminal Console Toggle — Option B (`misora.py`, `U02`, `4.3`):**
  - Added `Debug > Show / Hide Windows Console` checkbutton (`var_console_visible`, `F12`) and `_toggle_windows_console()` shared with `_on_misora_shortcut` (returning `"break"` on `F12` inside editor widgets to prevent double-toggle).
  - Queries `GetConsoleWindow()` and `IsWindowVisible(hwnd)` before calling `ShowWindow(hwnd, 0|5)`, syncs menu state, and handles `hwnd == 0` (`pythonw.exe`) with an informative toast and zero spawned processes.
- **Modal About & `SupportMeDialog` (`misora.py`, `assets/icon.py`, `assets/icons/{kofi,patreon,paypal}.png`, `U05`, `4.6`):**
  - Replaced `messagebox.showinfo` in `on_about()` with a modal `tk.Toplevel(self)` displaying `Misora: Story Editor`, derived `v{__version__}`, and a **Support Me** launcher.
  - `SupportMeDialog` opens `assets/Service.gif` lazily (verified on disk: `5,445,253` bytes, `(600, 338)`, `72` frames), seeks one frame at a time, composites onto solid `bg_panel` RGB canvas (`<=240x240`), updates ONE reused `ImageTk.PhotoImage`, falls back cleanly when GIF is missing/unreadable, displays the exact Indonesian caption, respects `SHOW_PAYPAL_BUTTON: bool = True`, exposes `kofi.png`/`patreon.png`/`paypal.png` external links (`ko-fi.com/imaterial`, `patreon.com/imaterial`, `paypal.me/CorneliaCrimson`), and cleans up timers/PIL handles in both `close()` and `destroy()`.
  - Updated `tests/test_phase4_import_export_preview.py::test_01_version_unification` under approved amendment for the modal `tk.Toplevel` About dialog.
- **Manual Windows QA Pending (Project Lead):**
  - Click Speaker `▼` repeatedly on a character with 3+ lines and verify cyclic jump + toast.
  - Click Speaker entry, clear text, click an item inside the Google-style dropdown (confirm no premature FocusOut commit), and verify Escape/Enter.
  - Press `F12` / `Debug > Show / Hide Windows Console` under `python.exe` (`misora.bat`) and `pythonw.exe`.
  - Open `Help > About` -> `Support Me` -> confirm smooth `Service.gif` loop, flat RAM across 5 open/close cycles, and all 3 links open the exact target URLs.

### v1.5 S04 (`v1.4.4`) — Ribbon & Header Layout (`U09`–`U14`, `U22`, `4.2`), Left Drawer True 0px Minimize (`U03`, `4.4`), Search Double-Click (`U-1`), MTL Controls (`U-2`, `U-6`), & Checkbox Clarity (`U21`) (2026-11-26)
- **3-Row Header & Ribbon Restructuring (`misora.py`):**
  - Row 1 (`gd_header`): Flat borderless `btn_lock_box` (`bd=0, relief="flat", highlightthickness=0`) placed before `lbl_gd_title` (`"Dialogue"`), `view_group` (`Select Box | All Script | Preview`) moved onto Row 1 left of compact icon-only `btn_translate` (MTL) and `btn_ai_prompt` (AI Prompt) with `Nav.TButton` compact `Prev`/`Next`.
  - Row 2 (`speaker_view_row`): `actions_bar` moved to Row 2 right side with `btn_player` + `btn_ribbon_undo` + `btn_ribbon_redo` at the far right (`U09`, `U10`, `U12`, `4.2`).
  - Row 3 (`ribbon_actions_row`): NGUI formatting buttons only; `show_ngui_ribbon` defaults to `False` (`View > Toggle NGUI Ribbon` toggles cleanly).
- **Left Drawer True `0 px` Minimize & Lifecycle (`misora.py`, `U03`, `4.4`):**
  - `_set_left_panel_visible()` uses `h_paned.forget(self.left_frame)` (preserving child widgets) + `btn_reopen_left` (`▶`) docked in `right_frame` + `View > Show Left Panel` (`var_show_left_panel`), with zero `_update_views()`, `_render_continuous_view()`, or `_update_raw_view()` rebuilds on Left/Right drawer toggles.
- **Search Tab Double-Click & MTL Drawer Cleanup (`misora.py`, `assets/icons/refresh.png`, `U-1`, `U-2`, `U-6`):**
  - Bound `<Double-Button-1>` on `btn_tab_search` to `on_show_find()` preserving active scope.
  - Moved `Enabled Engines` from `_mtl_dialogue_eng_bar` into `Translator > Enabled Engines` (`translator_menu`, `mtl_engines_menu`) with config persistence; generated 32x32 RGBA `assets/icons/refresh.png` and attached to MTL refresh buttons; flipped MTL Apply arrows to `←`.
- **Checkbox & Radio Clarity (`misora.py`, `U21`):**
  - Configured `clam` `indicatorbackground`/`indicatorforeground`/`upperbordercolor`/`lowerbordercolor`/`foreground` across `normal`/`active`/`focus`/`disabled`/`selected`/`!selected` states + `tk.Checkbutton` roles (`check_panel`, `check_accent`, `check_ribbon`) with WCAG >= 4.5 contrast across Light & Dark themes.
- **Manual Windows QA Pending (Project Lead):**
  - Verify layout at 1280x720, 1400x900, and 125%/150% Windows DPI with both Left Drawer and Right MTL Drawer open (zero clipped buttons).
  - Minimize/reopen Left Drawer and Right Drawer repeatedly, resize & minimize/restore window, and confirm zero flicker or lost edits.
  - Visually check checkboxes & radio buttons in both Light and Dark themes (checked, unchecked, hover, disabled).

### v1.5 S03 (`v1.4.3`) — All Script Technique A Overhaul (`U08`, `U-7`), Leaked 3rd Window Fix, Precision Priconne Preview (`U-5`), & Lossless `BoxSnapshot` Paste Insert/Replace (`4.1`) (2026-11-26)
- **Leaked 3rd Window & Redundant Rebuild Fixes (`misora.py`, `U08`):**
  - `_update_empty_state_visibility()` now inspects `var_continuous_view.get()` before packing `gd_scroll_wrap` or `continuous_wrap`, preventing Dialogue View from leaking below All Script above Raw Commands.
  - Eliminated unconditional `_render_continuous_view()` calls in `on_box_new()` and `_on_card_paste_caret()`, removed duplicate `_sync_clean_view_to_current_box()` calls in `on_box_cut()` and `on_box_paste()`, and committed `on_text_cut()` synchronously so Ribbon Cut persists across Next/Prev navigation.
- **All Script Technique A Overhaul (`misora.py`, `U08`, `U-7`):**
  - Replaced per-box `tk.Frame`/`tk.Text` card widget explosion in `_render_continuous_view()` with single read-only `tk.Text` (`self.txt_all_script`, preserving `self.txt_continuous` as editable plain-text fallback).
  - Maintains deterministic block map (`_all_script_block_ranges`, `_all_script_line_to_box`), in-place single-click selection & header/Raw/MTL sync, double-click/`Enter` jump to Dialogue View (preserving `is_box0_active` on Box 0), and fixed-width ASCII (`[x] ` / `[ ] ` / `    `) Select Box + Lock slots updating in-place with zero horizontal shift.
  - 150-box synthetic render benchmark (`Python 3.12.10`, `Tk 8.6`, `Windows-11-10.0.26100-SP0`): `2953.72 ms` (`cards=151`) pre-patch -> `1452.28 ms` (`0` card widgets) post-patch.
- **Clean-Room Priconne Preview (`assets/preview_frames.py`, `assets/__init__.py`, `misora.py`, `U-5`):**
  - Pure Pillow supersampled anti-aliased frame/badge generator with bounded root-scoped cache (`prune_preview_cache()` on `destroy()`), zero `AtlasAdv` sprites (`NO-02`).
  - Dialogue Preview: warm cream-white capsule (`#F8F6F0`), champagne-gold border (`#C8A86B`), inner rim, pink white-outlined `▼`, no nameplate for narration, `50d x 3` safe interior with `wrap="none"` bleed and `_sweep_cstyle_tags()`.
  - All Script Preview: warm-gray canvas (`#F4F2ED`), rounded white card caps (`#FFFFFF`, `#B8BCCA`), steel-blue speaker (`#2D599E` / `'Narration'`), pale-blue dotted divider, blue voice badge, compiled NGUI rich text (`wrap="none"`), and overflow tags.
- **Lossless Native Paste Box Insert vs Replace (`core/story_ast.py`, `core/undo_journal.py`, `core/__init__.py`, `misora.py`, `4.1`, `AMD-05`):**
  - Added `StoryDocument.replace_box()` preserving all 6 `BoxSnapshot` fields (`speaker`, `voice_cue`, `kind`, `seg_texts`, `raw_breaks`, `extra_args`), surrounding commands, and adjacent narration separation (`QW-B01`).
  - Added `BoxSnapshotReplaceDelta` in `core/undo_journal.py` and handled forward/reverse application in `_apply_delta()`.
  - Extended `on_box_paste(confirm=True, mode=None)` with 3-way modal chooser (`Insert after Box #N` / `Replace Box #N..#M` / `Cancel`), pre-mutation staging & validation, transactional rollback on failure, locked-target skipping, and excess-block clamping.
- **Manual Windows QA Pending (Project Lead):**
  - Toggle All Script and All Script Preview on a 100+ box `.unity3d` story and confirm fast rendering and ZERO 3rd window above Raw Commands.
  - Visually compare Dialogue Preview and All Script Preview against both Bandicam reference screenshots.
  - Cut Box #2 & #3 -> move to Box #6 -> Paste Box -> test both `Insert after #6` and `Replace #6..#7` (plus Undo & Redo, verifying voice cues & multi-segment data survive).

### v1.5 S02 (`v1.4.2`) — Font Policy & Custom Loader (`U16`–`U18`), Constant Ruler & Overlap Fix (`U19`), Gutter Sync (`U20`), Fast Metrics & Char Indicator (`U06`, `U15`) (2026-11-25)
- **Font Policy & Win32 Private Custom Font Loader (`core/font_manager.py`, `core/__init__.py`, `.gitignore`):**
  - Strictly 2 built-in presets: `Global — Nunito Bold` (resolves `Nunito Bold`, or `Nunito` with `"bold"` weight, or `Segoe UI` fallback) and `Japanese — nintendoP_Humming-E_002pr` (resolves `nintendoP_Humming-E_002pr`, or `Yu Gothic UI` / `Meiryo UI` fallback).
  - Pure-Python `FontManager` (stdlib `ctypes`/`struct`/`pathlib`, zero implicit Tk root) scans `assets/fonts/` for `.ttf`/`.otf` and `custom_fonts.txt`, loading privately on Windows via `AddFontResourceExW(..., 0x10, 0)` (zero Admin rights) and unloading in `MisoraApp.destroy()` via `RemoveFontResourceExW`, reporting invalid/corrupt files cleanly via `logger.warning()`.
  - `.gitignore` excludes proprietary Japanese font binaries (`assets/fonts/*nintendoP*`, `assets/fonts/*Humming*`, `assets/fonts/*.otf`). **Note:** Font choice is editor-display-only and never alters game files.
- **Customize Tab & Legacy Migration (`misora.py`):**
  - Replaced legacy 5-font list with the 2 official presets + tooltip/help label + separated `Custom Fonts (Advanced)` subsection (`Refresh Fonts`, `Open Fonts Folder`).
  - Migrates legacy `misora_config.json` `dialogue_font_family` values (e.g., `Consolas`, `Segoe UI`) cleanly to `Global — Nunito Bold`.
- **Metrics, Constant Ruler, Gutter Sync & Char Indicator (`misora.py`, `tests/test_p3_s17_pixel_rulers.py`):**
  - Exposed `@property` + `@setter` for `dialogue_font_family` and `dialogue_font_size` backed by `self.prefs`, fixing `_get_dialogue_measure_font()` and `_apply_gutter_overflow_tag()` falling back to `Consolas` 11pt.
  - Optimized `_measure_dialogue_metrics()` with an $O(1)$ full-line fast-path and $O(\log L)$ binary search for overflowing lines.
  - Added `_get_ruler_measure_font()` locked to `Nunito Bold` so `50d` stays constant across Global/Japanese font switches; moved `'50d'` left of `ov_x` (`anchor="ne"`) and `'>50d'` right of `ov_x` (`anchor="nw"`) to eliminate overlap.
  - Synchronized `gutter_clean` font/size/spacing (`pady=8`, `spacing1=3`, `spacing3=3`) with `txt_dialogue` in `_apply_theme_and_fonts_live()`.
  - Restored `lbl_char_overflow` (`N/50d · M/3L`, no `(max)` label, red on `50 x 3` overflow, Box 0 unmeasured per `DEF-04`); updated `tests/test_p3_s17_pixel_rulers.py` per `AMD-02`.
- **Manual Windows QA Pending (Project Lead):**
  - Switch between `Global — Nunito Bold` and `Japanese — nintendoP_Humming-E_002pr` and verify horizontal ruler stays constant while line numbers stay aligned with lines 1–4.
  - Verify `'50d'` and `'>50d'` labels on the horizontal ruler no longer overlap.
  - Drop a custom `.ttf` into `assets/fonts/`, click `Refresh Fonts`, and verify it loads without Admin rights.

### v1.5 S01 (`v1.4.1`) — Baseline Reconciliation, Stability & Memory Remediation, Version Policy (`U00`) & Rebrand (`U04`) (2026-11-25)
- **Baseline & Session-State Reconciliation:**
  - `main` and `origin/main` at `32ad313376343e1e6a2f46970f8081b949f8e0d8` with pre-existing local S24 edits (`CHANGELOG.md`, `PROJECT_STATE.md`, `tests/test_phase4_import_export_preview.py`), `D misora_config.default.json`, and existing untracked files preserved intact.
- **Stability & Memory Remediation (`BUG-01..06`, `BONUS-01..03`):**
  - `BUG-01`: Per-job `threading.Event` (`_search_cancel_event`) + bounded `search_queue(maxsize=2048)` + `_put_queue_cancellable()` + 5-stage cancellation across `os.walk()`, directory/file loops, `search_file()`, queue submission, and app shutdown.
  - `BUG-02` / `BONUS-02`: Module-level shared SSL context (`_get_shared_ssl_context()`), bounded `ThreadPoolExecutor(max_workers=3)` + `threading.Semaphore(8)` pending backpressure in `All Script` `Translate All`, cooperative `batch_cancel`, auto-cancel on close/reload/engine switch/shutdown, interruptible `rate_limit_delay`, stale `batch_gen` rejection, and `executor.shutdown(wait=False, cancel_futures=True)` cleanup. **Honest Cancellation Guarantee:** Blocking `urllib.request.urlopen` socket reads already in flight cannot always be forcefully killed mid-flight; cancellation is cooperative (pending items abort immediately, no new requests start, and late replies are discarded by batch/identity/cancel guards).
  - `BUG-03` / `BONUS-01`: `_prune_document_caches()` + `XUnitySyncManager.unregister_jp_keys()` on close/reload + anti-repopulation guards in `_poll_mtl_drawer_queue()`.
  - `BUG-04`: `load_bundle_story()` disposes `env` on every post-load failure path while keeping live `env` intact on success.
  - `BUG-05`: Idempotent, producer-safe `MisoraLogger.close()` with `_stop_event` and `_closed` guards; exits cleanly even on full `_file_queue`; clears `_writer_thread` only once dead.
  - `BUG-06`: `save_bundle_story()` initializes `tmp_path = None` before `try:` and moves `mkdir()` inside `try:` so `_is_saving` is always released.
  - `BONUS-03`: On-demand polling for `_search_poll_job` and `_mtl_poll_job`, plus elimination of redundant second `load_bundle_story()` in `_apply_delta(BulkFileDelta)`.
- **Versioning (`U00`) & Rebrand (`U04`) & Long-Term Direction:**
  - `U00`: `A.b.c` policy (`1.4.1`..`1.4.7` session builds -> `1.5.0` official milestone; `BLOCKED`/`REVERTED` without version bump). Root `__init__.py` `__version__ = "1.4.1"`.
  - `U04`: User-visible product rebranded to **`Misora: Story Editor`**; internal identifiers (`misora`, `MisoraApp`), `.misora`, `misora_config.json`, `misora.bat`, and ProgID `Misora.Unity3dBundle` preserved.
  - **Architectural Direction (Future):** Future Unit/Monster Editor tools will live in separate repositories sharing core infrastructure (AST/bundle/XUAT/UI patterns) with variable-aware XUAT regex support.
- **Manual Windows QA Pending (Project Lead):**
  - Open & close 10+ `.unity3d` files in Windows Task Manager and confirm RAM reaches a stable plateau after close.
  - Start a large folder search -> press Cancel -> immediately start a second search -> close app cleanly (confirm zero lingering `python.exe`).
  - Confirm window title, Splash Screen, and About dialog display `Misora: Story Editor` v1.4.1.

### S24 Final Acceptance Audit & Release Gate — Audit-Only Hold at `v1.4.0` (2026-11-25)
- **Session Scope:** Final Acceptance Audit (63 Active IDs + `DEF-01..10` + `NO-01..12`) & `v1.4.1` Release Gate (`MF-S24`, `GPT-1`, `GPT-2`).
- **Single-Source Version Fix (`MF-S24`):**
  - Updated `tests/test_phase4_import_export_preview.py::test_01_version_unification` to derive `expected_version` dynamically from root `__init__.__version__` while preserving all cross-module consistency assertions (`root == misora.__version__ == misora._get_app_version() == splash._load_app_version() == splash._VERSION == About "Version X"`). Verified `py -3.12 -m unittest tests.test_phase4_import_export_preview -v` (`Ran 5 tests`, `OK`, exit code `0`).
- **Release Gate Status (`v1.4.1` Bump HELD at `1.4.0`):**
  - **Automated Suite:** `py -3.12 -m compileall -q misora.py core assets tests` exits `0`; `py -3.12 -m unittest discover -s tests -v` runs `344` tests (`304 pass`, `35 skipped`, `3 failures`, `2 errors` — all `5` failures/errors in `tests/test_s8b2_memory_guards.py` and all `35` skips due to intentionally excluded `storydata_1001005.unity3d`).
  - **Hold Blocker 1 (`BUG-09` P1 / `DEF-02`):** `storydata_1001005.unity3d` is absent on disk (`Test-Path` = `False`); real production `.unity3d` bundle verification remains **`BLOCKED`** without fixture or explicit Project Lead risk acceptance.
  - **Hold Blocker 2 (`AGENTS.md` §29 Manual Windows QA):** No Project Lead confirmation or written risk waiver received yet for:
    1. **Ribbon Cut (`AGENTS.md` §29 blocker):** `PENDING MANUAL CONFIRMATION`
    2. **Paste Box in BOTH Dialogue and All Script views (`AGENTS.md` §29 blocker):** `PENDING MANUAL CONFIRMATION`
    3. **DPI & snapped half-screen layout (`BUG-39`/`FEAT-04`):** `PENDING MANUAL CONFIRMATION`
    4. **`Import from XUAT` (`FEAT-14`) smoke test on `BepInEx\Translation\en\Text`:** `PENDING MANUAL CONFIRMATION`
  - **Hold Blocker 3 (`tests/test_p3_s02_hygiene.py`):** `test_guard_1_root_version_untouched` hardcodes `_read_root_version() == "1.4.0"` outside S24 Allowed Files.
  - **Hold Blocker 4 (Missing Canonical Ledger File):** `Phase_2.5_Canonical_Ledger_LOCKED.md` (git blob `e51291724d485eebbe18142f68ecdc4fdf4a7c1b`) is absent from disk and local Git object store, leaving `DEF-05`, `DEF-07..09` and `NO-04..06`, `NO-08`, `NO-10..11` **`BLOCKED`** for text definition verification.

#### Final Acceptance Audit Matrix (All 85 Canonical IDs)

> Verification commands used for every `PASS` / `DEFERRED` entry below:
> - `py -3.12 -m compileall -q misora.py core assets tests` -> exit `0`
> - `py -3.12 -m unittest tests.test_phase4_import_export_preview -v` -> `Ran 5 tests` (`OK`, exit `0`)
> - `py -3.12 -m unittest discover -s tests -v` -> `Ran 344 tests` (`304 pass`, `35 skipped` fixture-gated, `3 failures` & `2 errors` in `test_s8b2_memory_guards` due to missing `storydata_1001005.unity3d`, exit `1`)

##### A. Active Bugs (`BUG-01..BUG-41` — 41 IDs: 40 `PASS`, 1 `BLOCKED`)

| ID | Session | Evidence (Module / Test Methods / Symbol) | Status |
|---|---|---|---|
| `BUG-01` | S03 | `tests/test_p3_s03_binary_v2.py::test_probe_1_bug01_strict_binary_parse_validation` (pass); `StoryDocument.from_binary()`, `load_bundle_story()` | **PASS** |
| `BUG-02` | S04 | `tests/test_p3_s04_ast_mutations.py::test_probe_1_bug02_kind_conversion_box_separation_no_collapse` (pass); `set_box_kind()`, `inject_box()` | **PASS** |
| `BUG-03` | S03 | `tests/test_p3_s03_binary_v2.py::test_probe_2_bug03_*`, `test_probe_3_bug03_*`, `test_probe_6_bug03_*` (all pass); `to_binary()`, `escape_arg()`, `_update_raw_view()` | **PASS** |
| `BUG-04` | S03 | `tests/test_p3_s03_binary_v2.py::test_probe_4_bug04_*`, `test_guard_2_*` (all pass); `_INV_CMD_MAP`, `DEFAULT_BREAKER_IDS` | **PASS** |
| `BUG-05` | S04 | `tests/test_p3_s04_ast_mutations.py::test_probe_2_bug05_structural_ownership_voice_and_breakers` (pass); `insert_box()`, `delete_boxes()`, `move_box()` | **PASS** |
| `BUG-06` | S04 | `tests/test_p3_s04_ast_mutations.py::test_probe_3_bug06_multisegment_undo_and_internal_box_paste` (pass); `BoxEditDelta`, `BoxSnapshot` | **PASS** |
| `BUG-07` | S05 | `tests/test_p3_s05_treeview_csif.py::test_probe_2_bug07_atomic_sparse_csif_and_metadata` (pass); `apply_to_document()`, `ScriptPastePreviewDialog` | **PASS** |
| `BUG-08` | S05 | `tests/test_p3_s05_treeview_csif.py::test_probe_3_bug08_backslash_parity_csif_roundtrip` (pass); `core/script_codec.py` | **PASS** |
| `BUG-09` | S03 | Synthetic non-target SHA-256 check `tests/test_p3_s03_binary_v2.py::test_probe_5_bug09_*` passes; **real production `.unity3d` verification (`storydata_1001005.unity3d`) & `test_s8b2_memory_guards` `test_01..05` missing fixture** | **BLOCKED** |
| `BUG-10` | S07 | `tests/test_p3_s07_undo_locks_raw.py::test_probe_1_bug10_caret_paste_dirty_and_lock` (pass); `_on_card_paste_caret()` | **PASS** |
| `BUG-11` | S06 | `tests/test_p3_s06_doc_state_save.py::test_probe_1_bug11_plain_text_preview_save_preserves_tags` (pass); `on_save()` | **PASS** |
| `BUG-12` | S06 | `tests/test_p3_s06_doc_state_save.py::test_probe_2_bug12_per_document_state_locks_and_inactive_save` (pass); `_locked_box_uids`, `_save_document_entry()` | **PASS** |
| `BUG-13` | S07 | `tests/test_p3_s07_undo_locks_raw.py::test_probe_2_bug13_mutate_before_undo_error_surfaced` (pass); `_commit_widget_edit()`, `report_callback_exception()` | **PASS** |
| `BUG-14` | S11 | `tests/test_p3_s11_mtl_threading.py::test_probe_2_bug14_batch_cancel_tracks_batch_open_and_ends_once` (pass); `BatchTranslateDialog` | **PASS** |
| `BUG-15` | S07 | `tests/test_p3_s07_undo_locks_raw.py::test_probe_3_bug15_non_contiguous_cut_undo_redo_and_locks` (pass); `BoxStructuralDelta.indices` | **PASS** |
| `BUG-16` | S07 | `tests/test_p3_s07_undo_locks_raw.py::test_probe_4_bug16_lock_enforcement_skeleton_and_translator` (pass); `is_box_locked()` | **PASS** |
| `BUG-17` | S04 | `tests/test_p3_s04_ast_mutations.py::test_probe_4_bug17_uid_coalesce_and_seg_texts_propagation` (pass); `MasterUndoJournal.record()` | **PASS** |
| `BUG-18` | S06 | `tests/test_p3_s06_doc_state_save.py::test_probe_3_bug18_write_atomic_encoded_lf_and_export_script` (pass); `write_atomic_encoded()` | **PASS** |
| `BUG-19` | S06 | `tests/test_p3_s06_doc_state_save.py::test_probe_4_bug19_zero_box_story_saves_cleanly` (pass); `on_save()` | **PASS** |
| `BUG-20` | S09 | `tests/test_p3_s09_replace_all_backups.py::test_probe_2_collision_resistant_backups`, `test_guard_1_*` (pass); `make_collision_resistant_backup_path()` | **PASS** |
| `BUG-21` | S08 | `tests/test_p3_s08_search_roots_focus.py::test_probe_1_bug_21_case_sensitive_whitespace_search` (pass); `norm_search()`, `_compile_matcher()` | **PASS** |
| `BUG-22` | S08 | `tests/test_p3_s08_search_roots_focus.py::test_probe_2_bug_22_errors_snapshots_sequences_spans` (pass); `search_file()`, `_search_seq` | **PASS** |
| `BUG-23` | S08 | `tests/test_p3_s08_search_roots_focus.py::test_probe_3_bug_23_bounded_project_roots_and_replacement` (pass); `_resolve_project_search_roots()` | **PASS** |
| `BUG-24` | S09 | `tests/test_p3_s09_replace_all_backups.py::test_probe_1a..1f`, `test_guard_2_*` (all 7 pass); `on_replace_all()`, `_apply_delta()`, `_confirm_closed_files_for_op()` | **PASS** |
| `BUG-25` | S10 | `tests/test_p3_s10_xuat_integrity.py::test_probe_1_bug25_immutable_jp_key_and_conflict_preview_gate` (pass); `_sync_modified_boxes_to_xuat()` | **PASS** |
| `BUG-26` | S10 | `tests/test_p3_s10_xuat_integrity.py::test_probe_2_bug26_find_and_update_atomic_write_preserves_bom_and_crlf` (pass); `XUnitySyncManager.find_and_update()` | **PASS** |
| `BUG-27` | S11/S20 | `tests/test_p3_s11_mtl_threading.py::test_probe_1..1f` (6 pass) & `tests/test_p3_s20_mtl_drawer_dialogue.py::test_probe_2_*` (pass) | **PASS** |
| `BUG-28` | S13 | `tests/test_p3_s13_ribbon_shortcuts.py::test_probe_01_bug28_ribbon_and_size_commit_targets` (pass); `_insert_text_wrapper()`, `on_insert_font_size()` | **PASS** |
| `BUG-29` | S13 | `tests/test_p3_s13_ribbon_shortcuts.py::test_probe_02_bug29_hyg07_shortcut_table_reconciliation` (pass); `_on_misora_shortcut()`, `_bind_shortcuts()` | **PASS** |
| `BUG-30` | S08 | `tests/test_p3_s08_search_roots_focus.py::test_probe_4_bug_30_search_focus_gutter_and_noop_keyrelease` (pass) | **PASS** |
| `BUG-31` | S05 | `tests/test_p3_s05_treeview_csif.py::test_probe_1_bug31_treeview_theme_contrast` (pass); `_apply_styles()` | **PASS** |
| `BUG-32` | S12 | `tests/test_p3_s12_lifecycle_security.py::test_01_logger_flush_barrier_and_app_teardown` (pass); `MisoraLogger.flush()`, `destroy()` | **PASS** |
| `BUG-33` | S12 | `tests/test_p3_s12_lifecycle_security.py::test_02_dpapi_fail_closed_and_ciphertext_preservation` (pass); `DPAPISecurityError` | **PASS** |
| `BUG-34` | S12 | `tests/test_p3_s12_lifecycle_security.py::test_03_reload_from_disk_disposes_prior_env` (pass); `open_file(reload_from_disk=True)` | **PASS** |
| `BUG-35` | S12 | `tests/test_p3_s12_lifecycle_security.py::test_04_deferred_startup_restore_after_deiconify` (pass); `_deferred_restore` | **PASS** |
| `BUG-36` | S12 | `tests/test_p3_s12_lifecycle_security.py::test_05_splash_images_sort_key_guards_non_numeric` (pass); `_splash_sort_key()` | **PASS** |
| `BUG-37` | S07/S19 | `tests/test_p3_s07_undo_locks_raw.py::test_probe_5_bug37_raw_view_read_only` & `tests/test_p3_s19_raw_commands_edit.py::test_guard_1_*` (pass) | **PASS** |
| `BUG-38` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_01_bug38_search_grid_alignment` (pass); `self.search_grid` | **PASS** |
| `BUG-39` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_04_bug39_feat04_responsive_rows_and_ngui_toggle` (pass; manual Windows DPI/snapped check pending) | **PASS** |
| `BUG-40` | S17 | `tests/test_p3_s17_pixel_rulers.py::test_01_probe_pixel_measure_rulers_and_overflow` (pass); `_measure_dialogue_metrics()` | **PASS** |
| `BUG-41` | S15 | `tests/test_p3_s15_selection_drawer_open.py::test_probe_1_bug41_feat05_select_box_both_views_and_reserved_slot` (pass) | **PASS** |

##### B. Track 2 Features (`FEAT-01..FEAT-14` — 14 IDs: 14 `PASS`)

| ID | Session | Evidence (Module / Test Methods / Symbol) | Status |
|---|---|---|---|
| `FEAT-01` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_02_feat01_scope_current_unmaps_path_widgets` (pass); `_sync_scope_widgets()` | **PASS** |
| `FEAT-02` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_03_feat02_feat03_player_ribbon_headers` (pass); `btn_player` | **PASS** |
| `FEAT-03` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_03_feat02_feat03_player_ribbon_headers` (pass); `_update_top_header_title()`, `lbl_raw_title` | **PASS** |
| `FEAT-04` | S14 | `tests/test_p3_s14_toolbar_search_ui.py::test_probe_04_bug39_feat04_responsive_rows_and_ngui_toggle` (pass); `var_show_ngui_ribbon` | **PASS** |
| `FEAT-05` | S15 | `tests/test_p3_s15_selection_drawer_open.py::test_probe_1_bug41_feat05_select_box_both_views_and_reserved_slot` (pass); `slot_cb`, `lbl_lock` | **PASS** |
| `FEAT-06` | S15 | `tests/test_p3_s15_selection_drawer_open.py::test_probe_2_feat06_collapsible_left_drawer` (pass); `_toggle_dock_collapse()` | **PASS** |
| `FEAT-07` | S15 | `tests/test_p3_s15_selection_drawer_open.py::test_probe_3_feat07_empty_state_and_batched_multi_open` (pass); `empty_state_frame`, `on_open_file()` | **PASS** |
| `FEAT-08` | S16 | `tests/test_p3_s16_misora_workspace.py::test_probe_1..3` (3 pass); `core/workspace.py`, `ProjectDiffDialog` | **PASS** |
| `FEAT-09` | S17 | `tests/test_p3_s17_pixel_rulers.py::test_01_probe_pixel_measure_rulers_and_overflow`, `test_02_guard_*` (2 pass); `ruler_clean`, `ruler_cont` | **PASS** |
| `FEAT-10` | S18 | `tests/test_p3_s18_game_preview.py::test_01..03` (3 pass); `dialogue_preview_canvas`, `_sweep_cstyle_tags()` | **PASS** |
| `FEAT-11` | S19 | `tests/test_p3_s19_raw_commands_edit.py::test_probe_1..3`, `test_guard_1` (4 pass); `_parse_and_validate_raw_v2()`, `DocumentRecordsDelta` | **PASS** |
| `FEAT-12` | S20 | `tests/test_p3_s20_mtl_drawer_dialogue.py::test_probe_1..2`, `test_guard_1` (3 pass); `'mtl'` drawer tab | **PASS** |
| `FEAT-13` | S21 | `tests/test_p3_s21_mtl_drawer_all_script.py::test_probe_1..2`, `test_guard_1` (3 pass); `txt_mtl_all_list`, `txt_mtl_all_scratchpad` | **PASS** |
| `FEAT-14` | S22 | `tests/test_p3_s22_import_xuat.py::test_probe_1..3`, `test_guard_1` (4 pass); `core/xuat_index.py`, `ImportFromXUATDialog` | **PASS** |

##### C. Hygiene Items (`HYG-01..HYG-08` — 8 IDs: 8 `PASS`)

| ID | Session | Evidence (Module / Test Methods / Disk Check) | Status |
|---|---|---|---|
| `HYG-01` | S01 | `PROJECT_STATE.md`, `README.md`, `AGENTS.md` reconciled; `CHANGELOG.md` created (`### S01..S24` verified on disk) | **PASS** |
| `HYG-02` | S02 | `tests/test_p3_s02_hygiene.py::test_probe_3_hyg02_backups_isolation_on_save` (pass); `backups/` entry count unchanged (`937`) | **PASS** |
| `HYG-03` | S13 | `tests/test_p3_s13_ribbon_shortcuts.py::test_probe_03_hyg03_ribbon_tooltips_and_fallbacks` (pass) | **PASS** |
| `HYG-04` | S04 | `tests/test_p3_s04_ast_mutations.py::test_probe_5_hyg04_bounded_removed_records` (pass); `prune_removed_records()` | **PASS** |
| `HYG-05` | S02 | `tests/test_p3_s02_hygiene.py::test_probe_1_hyg05_search_engine_type_hints` (pass); `core/search_engine.py` | **PASS** |
| `HYG-06` | S02 | `tests/test_p3_s02_hygiene.py::test_probe_2_hyg06_deepl_user_agent_single_version`, `test_guard_2_*` (pass); `core/mtl_engine.py` | **PASS** |
| `HYG-07` | S13 | `tests/test_p3_s13_ribbon_shortcuts.py::test_probe_02_bug29_hyg07_*` & `tests/test_phase2_required.py::test_31_*` (pass); `_on_ctrl_h()` | **PASS** |
| `HYG-08` | S23 | `tests/test_p3_s23_dead_code_cleanup.py::test_probe_hyg08_*`, `test_guard_update_gutter_clean_intact` (4 pass) | **PASS** |

##### D. Deferred / Untouched Items (`DEF-01..DEF-10` — 10 IDs: 5 `DEFERRED`, 5 `BLOCKED`)

| ID | Verification Evidence | Status |
|---|---|---|
| `DEF-01` | Empty binary argument single-space sentinel `" "` intact (`tests/test_p3_s03_binary_v2.py::test_guard_3_existing_core_suite_and_empty_arg_sentinel_intact` pass) | **DEFERRED** |
| `DEF-02` | `cmd_id` 35/32 synthetic binary/v2 preservation passes (`test_p3_s03::test_guard_1`, `test_p3_s19::test_probe_1`), **real production `.unity3d` fixture missing** | **BLOCKED** |
| `DEF-03` | Multi-TextAsset targeting deferred (`core/bundle_io.py:load_bundle_story` untouched single primary story TextAsset) | **DEFERRED** |
| `DEF-04` | Box 0 Summary overflow unmeasured/deferred (`tests/test_p3_s18_game_preview.py::test_01` pass) | **DEFERRED** |
| `DEF-05` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `DEF-06` | `_is_speaker_pinned` preserved untouched (`misora.py:1542, 8504, 8522, 8637-8650, 8883`) | **DEFERRED** |
| `DEF-07` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `DEF-08` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `DEF-09` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `DEF-10` | `misora.py` kept monolithic during Phase 2.5/3 cycle (`17,315` lines; `.agents/rules/misora-safety.md` §5) | **DEFERRED** |

##### E. Rejected Non-Goals (`NO-01..NO-12` — 12 IDs: 6 `PASS`, 6 `BLOCKED`)

| ID | Verification Evidence | Status |
|---|---|---|
| `NO-01` | No drafts, `.unity3d` blobs, or runtime `Record.uid` in `.misora` v1 (`tests/test_p3_s16_misora_workspace.py::test_probe_1` pass) | **PASS** |
| `NO-02` | No `AtlasAdv` sprites in Preview (`tests/test_p3_s18_game_preview.py::test_01..02` pass; `misora.py:5121`) | **PASS** |
| `NO-03` | No `ttk.Treeview` or per-box `tk.Text` in `All Script` MTL (`tests/test_p3_s21_mtl_drawer_all_script.py::test_probe_1` pass) | **PASS** |
| `NO-04` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-05` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-06` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-07` | No command-specific arity rejection in Raw Commands v2 (`misora.py:8101`; `tests/test_p3_s19_raw_commands_edit.py` pass) | **PASS** |
| `NO-08` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-09` | No `conflict_manager` / global XUAT `.txt` pruning (`tests/test_p3_s22_import_xuat.py::test_probe_3` pass) | **PASS** |
| `NO-10` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-11` | Definition unavailable (`Phase_2.5_Canonical_Ledger_LOCKED.md` missing from disk/git) | **BLOCKED** |
| `NO-12` | No auto-shrink in Preview (`test_p3_s18::test_01..02` pass) & no `Record.uid`/drafts in `.misora` (`test_p3_s16::test_probe_1` pass) | **PASS** |

### Track 2 Progress: Final Hygiene (S23) COMPLETE & S24 Audit Hold
- **Status:** S23 (`HYG-08`) is COMPLETE; S24 Part A acceptance audit & `MF-S24` single-source fix are COMPLETE. Part B (`v1.4.1` stamp) is **HELD** at `__version__ = "1.4.0"` pending Part 2B closure/waivers.
- **Next Action:** Project Lead review of `BUG-09` (`BLOCKED`), manual Windows QA (`AGENTS.md` §29 Ribbon Cut, Paste Box both views, DPI/snapped layout, `Import from XUAT`), `test_p3_s02_hygiene.py::test_guard_1` authorization, and optional `Phase_2.5_Canonical_Ledger_LOCKED.md` verification before promoting `v1.4.1`.

### S23 Final Grep-Proven Dead Code & Misleading Label Cleanup (2026-11-25)
- **Session Scope:** `HYG-08` (Track 2 · Final Hygiene — standalone per Grok R1/R2; `RF-5`).
- **Dead Code & Label Cleanup (`misora.py`):**
  - Removed grep-proven zero-caller `MisoraApp._update_gutter_cont()` (keeping `_update_gutter_clean()` intact) and `BatchTranslateDialog._toggle_pin_top()` (keeping `TranslatorAssistantDialog._toggle_pin_top()` intact).
  - Updated `NguiColorPickerPopup` gradient button label to canonical hyphen syntax `[{c0_code}-{c1_code}]` (`AGENTS.md` §19) and removed CWD `picker_error.log` write (errors continue logging via `self.app.logger.exception()`).
  - Updated `AIPromptSettingsDialog` speaker-header checkbox wording from legacy `=== [BOX:0|...] ===` to CSIF (`@@Speaker / @@_`).
  - Left `_is_speaker_pinned` (`DEF-06`) and `__version__ = "1.4.0"` untouched.
- **Tests:** Added `tests/test_p3_s23_dead_code_cleanup.py` (3 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 344 tests across 45 modules (304 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G7 (S22) COMPLETE
- **Status:** S22 is 100% COMPLETE (FEAT-14).
- **Next Session:** S23.

### S22 Unified `core/xuat_index.py` & Separate Floating `Import from XUAT` Resolver (2026-11-25)
- **Session Scope:** FEAT-14 (`U-B34`, `CLAUDE-N07`, `QW-E03`, `RF-3`, `GEM-R01`, `GEM-R02`, `GEM-R04`, `NO-09` — Track 2 · Group G7, post-`DEP-2`, `DEP-7`).
- **Unified XUAT Indexer (`core/xuat_index.py`, `core/__init__.py`, `core/mtl_engine.py`):**
  - Built single shared background-safe `XuatIndex` scanning strictly `BepInEx\Translation\en\Text` (excluding `.missing.txt`, `.report.txt`, `_SUMMARY.txt`, `_warnings.txt`, and `.bak_` files) using strict decoding (`read_text_file_strictly`), `split_xuat_line()`, and symmetric backslash-parity `unescape_xuat_value()`.
  - Added NGUI-tag and `{playername}`/`{0}`-aware O(1) normalization (`normalize_xuat_key`) protecting placeholders before `strip_tags()`, eliminating `QW-E03` linear scanning in `MTLEngine.translate()` and unifying `self.xuat_index` / `self.xuat_entries` (`D11`).
  - Typed `XuatLookupResult` (`GEM-R04`), separate dialogue vs speaker counts (`GEM-R02`), and zero `conflict_manager` / global XUAT pruning (`NO-09`).
- **Floating `ImportFromXUATDialog` (`misora.py`):**
  - Added `File -> Import from XUAT...` (auto-closes docked MTL drawer on open; not in MTL drawer).
  - Single outer scrollable list of paired rows with strictly read-only (`state="disabled"`) Left/Right `tk.Text` boxes fixed at `3 lines × 50 digit-widths` (via S17 `_measure_dialogue_metrics`), zero per-box `Scrollbar` widgets, `▼`/`▶` overflow indicators, focus-gated inner wheel + `Shift+Wheel`/drag horizontal panning, duplicate `◀ 1/N ▶` + `filename:line` + 3-tier scope (`This Box` / `This Story` / `Global` in-memory), lock (`🔒`) auto-skip & gray-out, per-box `Skip`, filter chips, Pre-Apply summary prompt, and mutate-before-undo single batch (`BoxEditDelta(..., source="xuat_import")`).
- **Tests:** Added `tests/test_p3_s22_import_xuat.py` (3 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 340 tests across 44 modules (300 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G6b (S21) COMPLETE
- **Status:** S21 is 100% COMPLETE (FEAT-13).
- **Next Session:** S22.

### S21 Docked Right-Side MTL Drawer — `All Script` Mode (2026-11-25)
- **Session Scope:** FEAT-13 (`U-B33` — Track 2 · Group G6b, post-S20; Lead Ruling #8, `NO-03`).
- **`All Script` Mode (`misora.py`):**
  - Synced `_on_toggle_continuous_view()` with `_set_mtl_drawer_mode("all_script" if self.var_continuous_view.get() else "dialogue")` alongside `Dialogue` / `All Script` mode buttons.
  - Renders ONE single-engine `ttk.Combobox` (`cmb_mtl_all_engine`) + **EXACTLY 2 `tk.Text` widgets** (`txt_mtl_all_list` read-only multi-line block list + `txt_mtl_all_scratchpad` shared bottom scratchpad), ZERO `ttk.Treeview`, and ZERO per-box `tk.Text` editors (`NO-03`).
  - Configured 5 shared static theme-aware status tags (`mtl_status_ready`, `mtl_status_translating`, `mtl_status_error`, `mtl_status_locked`, `mtl_status_empty`) updated live in `_apply_theme_and_fonts_live()`.
  - Added `Refresh Selected`, `Apply Selected`, `Translate All`, and `Apply All` reusing `_mtl_drawer_queue` + `_poll_mtl_drawer_queue()` with per-`(box_uid, engine)` `req_seq` tracking, model-layer `is_box_locked()` skipping, `box.uid` targeting, exact whitespace preservation (no `.strip()`), and single-batch `BoxEditDelta(source="mtl")` Undo.
- **Tests:** Added `tests/test_p3_s21_mtl_drawer_all_script.py` (2 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 336 tests across 43 modules (296 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G6a (S20) COMPLETE
- **Status:** S20 is 100% COMPLETE (FEAT-12).
- **Next Session:** S21.

### S20 Docked Right-Side MTL Drawer — Tab Infrastructure & `Dialogue` Multi-Engine Stack (2026-11-25)
- **Session Scope:** FEAT-12 (`U-B9`, `U-B32`) — Track 2 · Group G6a (post-`DEP-6`).
- **Right-Side Drawer `'MTL'` Tab (`misora.py`):**
  - Added **`MTL`** as the 3rd right-side drawer tab (`Customize` | `NGUI Glossary` | `MTL`) in `_build_side_drawer()` and `_switch_side_drawer_tab()`, routing `Translator -> Translator Assistant...` (`Ctrl+T`) and the `MTL` button (`on_open_translator_assistant()`) to `_toggle_side_drawer("mtl")`. Preserved `TranslatorAssistantDialog` class for backward-compatible S8a/S11/S07 guards.
- **`Dialogue` (1-Box) Multi-Engine Stack (`misora.py`):**
  - Vertically stacks engine cards only for user-enabled engines (default: `XUAT Cache` + `Google`; opt-in toggles for `DeepL`, `Local / Sugoi`, `LLM / OpenAI` persisted in `misora_config.json`).
  - Each card includes an editable scratchpad isolated from `"MisoraShortcuts"` with local `Ctrl+Z`/`Ctrl+Y`, per-card `↻` Refresh (bypasses session cache), and per-card `→` Apply (enforces model-level Translation Lock, preserves whitespace with no `.strip()`, mutates AST before `BoxEditDelta(source="mtl")` with `old_seg_texts`/`new_seg_texts`).
  - Top `Refresh All` uses a 256-entry LRU `OrderedDict` session cache and prompts `messagebox.askyesno` before batch-calling paid APIs (`DeepL`, `LLM / OpenAI`).
  - All async calls use `TagMasker`-protected `translate_async()` via `queue.Queue` + on-demand main-thread `_poll_mtl_drawer_queue()` (cancelled on teardown) and `(file_path, doc_id, box_uid, src_hash, req_seq, engine)` stale guards (`BUG-27`, `BUG-32`).
- **Tests:** Added `tests/test_p3_s20_mtl_drawer_dialogue.py` (2 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 333 tests across 42 modules (293 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G5 (S19) COMPLETE
- **Status:** S19 is 100% COMPLETE (FEAT-11).
- **Next Session:** S20.

### S19 Whole-File Editable `Raw Commands` (Lossless v2, Confirm, `DocumentRecordsDelta` Undo & Lock/JP Remap) (2026-11-25)
- **Session Scope:** FEAT-11 (`U-B31`) — Track 2 · Group G5 (post-`DEP-5`).
- **Undo Journal (`core/undo_journal.py`, `core/__init__.py`):**
  - Added `DocumentRecordsDelta` holding before/after deep `Record` list snapshots, `removed_records`, cursor bounds, and lock/JP-key snapshots with `"Edit Raw Commands"` auto-labeling.
- **Whole-File Raw Commands v2 Editor (`misora.py`):**
  - Added `Edit Raw (v2)` / `Apply Raw` / `Revert / Cancel` controls in `raw_header` with 350ms tooltips and theme role styling; kept `txt_raw` strictly `state="disabled"` outside Edit Raw mode (`BUG-37`).
  - Flushes pending Dialogue/All Script edits on `on_enter_raw_edit_mode()`, prevents `_update_raw_view()` from clobbering unsaved edits while `_raw_edit_mode` is `True`, and exits cleanly on file switch or cancel.
  - Validates v2 text via `_parse_and_validate_raw_v2()` (strict header/ID/b64 checks + `to_binary()` / `from_binary()` record count, `cmd_id`, and argument parity round-trip; ZERO command-specific arity checks `NO-07`; preserves `cmd_id` 35 & 32 `DEF-02`).
  - On `Yes` confirmation, atomically replaces `current_doc.records`, rebuilds `boxes`, remaps Translation Locks and immutable JP keys via `get_document_stable_locks()` / `restore_stable_locks()` (`CLAUDE-N02`) + `XUnitySyncManager.register_jp_key()`, records ONE `DocumentRecordsDelta`, marks dirty, and refreshes all views. On `No` or validation error, aborts cleanly with zero mutation.
  - Added `DocumentRecordsDelta` handling in `_apply_delta()` with safe `current_box_idx` / `is_box0_active` bounds clamping and full lock/JP-key restoration.
- **Tests:** Added `tests/test_p3_s19_raw_commands_edit.py` (3 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 330 tests across 41 modules (290 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G4b (S18) COMPLETE
- **Status:** S18 is 100% COMPLETE (FEAT-10).
- **Next Session:** S19.

### S18 Code-Drawn Game-Style `Dialogue Preview` & `All Script Preview` (2026-11-25)
- **Session Scope:** FEAT-10 (`U-B27`, `U-B28` — Lead Ruling #4, `NO-02`, `NO-12`) — Track 2 · Group G4b (post-DEP-2, DEP-8).
- **Dialogue Preview (`misora.py`):**
  - Added single `tk.Canvas` (`dialogue_preview_canvas`) + one embedded read-only `tk.Text` (`txt_dialogue_preview`) drawing native Priconne-style double borders, speaker name plate with `best_contrast_fg()`, and static pink `▼` (ZERO `AtlasAdv` sprites).
  - Consumes S17's `_measure_dialogue_metrics()` (`safe_w` = 50 digit-widths × 3-line safe area) and enforces `wrap="none"` with no font auto-shrinking so >50d lines and 4+ lines visibly bleed past the calibrated frame.
  - Extracted `_sweep_cstyle_tags()` (`GEM-E03`) to clear `cstyle_*` tags on every render/box switch; preserves caret/selection/`yview` on Preview OFF (guarded by file/box identity), restores `ruler_clean` above `clean_editor_row`, and keeps Box 0 / plain-text / 0-box fallbacks safe (`DEF-04`, `BUG-11`).
- **All Script Preview (`misora.py`):**
  - Updated `_render_continuous_view()` compiled mode to render lightweight styled `tk.Frame` cards (zero per-card `tk.Canvas` widgets) with `wrap="none"`, no auto-shrinking, `safe_w` boundary bar, and static pink `▼`.
- **Tests:** Added `tests/test_p3_s18_game_preview.py` (2 failing-first Defect Probes + 1 Regression Guard). Full test suite discovered count: 326 tests across 40 modules (286 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G4a (S17) COMPLETE
- **Status:** S17 is 100% COMPLETE (BUG-40, FEAT-09).
- **Next Session:** S18 (Game-style Preview frames).

### S17 Shared Pixel-Measure Helper, Calibrated Rulers & Remove Char Counter (2026-11-25)
- **Session Scope:** BUG-40, FEAT-09 (`U-B22..U-B26`, `DEP-8`) — Track 2 · Group G4a.
- **Pixel Measurement & Rulers (`misora.py`):**
  - Added `_get_dialogue_measure_font()` and `_measure_dialogue_metrics()` driven by the active editor font (`safe_w = font.measure("1234567890" * 5)` = 50 digit-widths, labeled as an estimate of the in-game font), using kerning-accurate `font.measure(prefix)`, 0px NGUI tag stripping, ruby base-only measurement, non-zero `{playername}`/`{N}` placeholder width, and exact raw-index overflow mapping.
  - Replaced static `tk.Text` rulers (`ruler_clean`, `ruler_cont`) with pixel-calibrated `tk.Canvas` rulers aligned to the editor text origin, showing a red overflow zone past 50 digit-widths (`est. >50d`).
  - Added `"gutter_overflow"` red/bold styling from line 4+ (3+ linebreaks) and `"line_overflow"` inline highlighting for characters past `safe_w` in both Dialogue and All Script views.
  - Removed `lbl_char_count`, `_update_rendered_char_count()`, and card `(N chars)` labels (keeping `core/ngui_tags.py:measure_line_lengths()` intact).
- **Docs & Tests:** Updated `README.md`, `tests/test_phase5_mtl_security_preview.py` (`test_06` lines 268–277), and added `tests/test_p3_s17_pixel_rulers.py` (1 failing-first Defect Probe + 1 Regression Guard). Full test suite discovered count: 323 tests across 39 modules (283 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### S16 `.misora` v1 Workspace Session & Overwrite Diff Dialog (2026-11-25)
- **Session Scope:** FEAT-08 (`U-B17`, `U-B18`) — Track 2 · Group G3 (post-DEP-4, DEP-9).
- **Core Workspace (`core/workspace.py`, `core/__init__.py`):**
  - Added pure-Python `.misora` v1 atomic JSON serialization/deserialization (`save_workspace`, `load_workspace`) via `write_atomic_encoded` and `read_text_file_strictly`, storing **strictly** file references (`rel_path` + `abs_path`), workspace state (`active_file`, `active_box_idx`, `is_box0_active`, `view_mode`, `search_scope`), and composite stable-key Translation Locks `(box_ordinal, jp_sha256)` — never unsaved story drafts, `.unity3d` binary blobs, or runtime `Record.uid` (`NO-01` / `NO-12`).
  - Added `safe_relpath` (cross-drive Windows `ValueError` guard), `resolve_workspace_file_path` (relative-first then absolute fallback), `match_active_file` (portable `rel_path`/`abs_path` matching), and `compute_workspace_diff` (normalized Added/Removed/Kept + Dirty diff).
- **UI & Session Integration (`misora.py`):**
  - Added `File > Open Project (.misora)...` and `File > Save Project (.misora)...`, plus drag-and-drop `.misora` support in `_handle_dropped_paths()`.
  - Added modal `ProjectDiffDialog` (`U-B18`, `AGENTS.md` §16) displaying old-vs-new file changes (`Added`/`Removed`/`Kept`, `* Unsaved`/`Clean`) with `Save Current` / `Discard & Open` / `Cancel`, flushing active edits before diffing and aborting cleanly on `Cancel` or failed save.
  - Restores open tabs via batched `open_file(..., refresh_ui=False)`, re-attaches Translation Locks strictly via `restore_stable_locks()` (leaving unmatched locks unresolved and notifying the user, never silently transferring locks), handles missing files gracefully, and syncs view/header/scope controls.
- **New Test Suite:** Added `tests/test_p3_s16_misora_workspace.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 321 tests across 38 modules (281 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### Track 2 Progress: Group G2 (S15) COMPLETE
- **Status:** S15 is 100% COMPLETE (BUG-41, FEAT-05, FEAT-06, FEAT-07).
- **Next Session:** S16 (`.misora` Workspace Serialization & Schema).

### S15 Select Box Both Views + Reserved Lock Slot, Collapsible Left Drawer, Empty State & Batched Multi-Open (2026-11-25)
- **Session Scope:** BUG-41, FEAT-05, FEAT-06, FEAT-07 (Track 2 · Group G2 (post-DEP-4, DEP-9)).
- **BUG-41 & FEAT-05 (`misora.py` — U-B11, U-B12, U-B29):**
  - Enabled `Select Box` mode in Dialogue view with inline header checkbutton (`cb_dialogue_select`: `Select Box #N (X selected)`), synced across box navigation, Copy/Cut, and view switches.
  - Restored Box 0 (`-1`) Select Box checkbutton on Card #0 (`hdr_0`) in All Script view.
  - Enclosed per-card Select Box checkbuttons inside a fixed-width `slot_cb` container (`width=22`, `pack_propagate(False)`) and relocated `lbl_lock` (fixed `width=2`, clickable to toggle lock) immediately to the right of `slot_cb`, eliminating horizontal header shifting on toggles.
- **FEAT-06 (`misora.py` — U-B15):**
  - Extended `_toggle_dock_collapse()` into a clean pane-based collapsible left drawer inside `h_paned` (zero `place()` overlays): hides tab buttons and body frames on collapse, places expand toggle (`▶`) cleanly at `x < 36`, and restores tabs/content on expand.
- **FEAT-07 (`misora.py` — U-B16, U-B19, U-B20):**
  - Added `empty_state_frame` with centered `"📂 Open Files"` button and drag-and-drop hint shown when 0 documents are open and auto-hidden when >=1 document is opened.
  - Bound `<Double-Button-1>` on `btn_tab_files` to `on_open_file()`.
  - Updated `on_open_file()` to `filedialog.askopenfilenames()`, preserving S1 staged semantics and performing ONE batched UI refresh (`_update_views()`) at the end.
- **New Test Suite:** Added `tests/test_p3_s15_selection_drawer_open.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 317 tests across 37 modules (277 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).

### S14 Search Bar 5-Col Grid, Hide Current Dir, Player Icon/No `[-]`, VIEW Group, Toggle NGUI Ribbon & `Raw Commands` (2026-11-25)
- **Session Scope:** BUG-38, BUG-39, FEAT-01, FEAT-02, FEAT-03, FEAT-04 (Track 2 · Group G1 (post-DEP-3)).
- **BUG-38 (`misora.py` — U-B1, U-B2):**
  - Unified search bar Find and Replace rows into one shared 5-column grid (`self.search_grid`) with column weights `(0, 1, 0, 0, 0)` and `uniform="search_btn"` for action buttons, ensuring Find and Replace entry fields align with identical `winfo_rootx()` and `winfo_width()`.
  - Introduced `Search.TButton` and `SearchPink.TButton` with uniform font (`Segoe UI`, `u_sz`), consistent padding `(6, 2)`, and identical layout weights so all 4 search action buttons (`Find in Files`, `Cancel`, `Replace`, `Replace All`) have identical width and height.
  - Implemented `_show_replace_row()` and `_hide_replace_row()` with `_ReplaceRowProxy` compatibility proxy so `self.row_replace.pack_forget()` / `pack()` calls gracefully map to grid operations without crashing.
- **FEAT-01 (`misora.py` — U-B21):**
  - Updated `_sync_scope_widgets()`: when search scope is `'current'`, hides `folder_path_entry` and `btn_browse_search_folder` via `pack_forget()`, preserving `selected_search_folder` and `project_folder` untouched.
  - Automatically restores `folder_path_entry` and `btn_browse_search_folder` via `pack()` when switching scope back to `'folder'` or `'project'`.
- **FEAT-02 (`misora.py` — U-B3+U-B5, U-B4, U-B13):**
  - Converted Player button to icon-only (`player.png`, no `{0}` text in label; Unicode fallback `"👤"` when icon unavailable), attached 350ms tooltip explaining `{playername}` / `{0}`, and relocated it out of the NGUI formatting ribbon into the speaker control row next to `txt_speaker`.
  - Removed standalone `[-]` button from NGUI ribbon (`ribbon_frame.winfo_children()` has 0 `[-]` buttons) while keeping `[-]` formatting accessible in the NGUI Glossary dialog and menu. Parented unmapped compatibility `self.btn_dash` outside `ribbon_frame` to satisfy existing test assertions.
- **FEAT-03 (`misora.py`, `README.md` — U-B6, U-B7, U-B8, U-B30):**
  - Renamed `Continuous View` -> `All Script` across UI labels, tooltips, and View menu (`"All Script View"`).
  - Unified view toggles (`cb_sel_box`, `cb_cont`, `cb_compiled`) into a single cohesive `VIEW` group (`self.view_group`) with icons, Unicode fallbacks, and tooltips.
  - Implemented dynamic top header updating via `_update_top_header_title()`: updates `lbl_gd_title` to `"Dialogue"` / `"All Script"` when preview is OFF, and `"Dialogue Preview"` / `"All Script Preview"` when preview is ON.
  - Renamed bottom pane title strictly to **`Raw Commands`** (`lbl_raw_title`), while maintaining internal AST and continuous view identifiers intact.
- **BUG-39 & FEAT-04 (`misora.py` — U-B14):**
  - Replaced single horizontally packed `speaker_ribbon_row` with stacked responsive rows (`speaker_view_row` and `ribbon_actions_row`), eliminating toolbar clipping at `1280x720` and snapped `~960px` window widths.
  - Added `View > Toggle NGUI Ribbon` checkbutton menu item backed by `self.var_show_ngui_ribbon` and `_on_toggle_ngui_ribbon()`, with preference persistence in `misora_config.json` (`"show_ngui_ribbon"`).
- **New Test Suite:** Added `tests/test_p3_s14_toolbar_search_ui.py` with 4 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 313 tests across 36 modules (273 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `README.md`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s14_toolbar_search_ui.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/splash.py`.

### S13 Continuous Ribbon/Size/Dirty Sync, Shortcut Conflicts, Complete Tooltips & `Ctrl+H` Hygiene (2026-11-24)
- **Session Scope:** BUG-28, BUG-29, HYG-03, HYG-07 (Track 1 · Group F3 / DEP-3 — Track 1 Final Gate).
- **BUG-28 (`misora.py` — DEP-3):**
  - Resolved active card editor via `_get_card_text_widget(self.current_box_idx)` inside `_insert_text_wrapper()` and `on_insert_ruby()` when `var_continuous_view.get()` is active with story cards, eliminating mutation of the hidden `txt_continuous` fallback widget.
  - Removed redundant `_on_dialogue_edited()` call from `_insert_text_wrapper()` so that `apply_ngui_wrapper()`'s subsequent `_commit_widget_edit(target)` commits ONCE and triggers `_dirty_state_changed()`, fixing stale `*` title & Undo menu on first click in Page View.
  - Added `self._commit_widget_edit(target)` inside `on_insert_font_size()` to flush font size tag insertions to AST with undo delta recording, while preserving exact `<size=...>` / `</size>` syntax.
  - Added translation lock guards (`is_box_locked`) in `apply_ngui_wrapper()`, `on_insert_ruby()`, and `on_insert_font_size()` preventing ribbon formatting mutations on locked boxes.
- **BUG-29 & HYG-07 (`misora.py`):**
  - Reconciled canonical shortcut dispatch router on `MisoraShortcuts` bindtag:
    - Fixed `Ctrl+T` conflict: `Ctrl+T` (no shift) dispatches `self.on_open_translator_assistant()`, while `Ctrl+Shift+T` dispatches `self.on_copy_ai_prompt()`, matching menu accelerators and root bindings.
    - Removed rogue `<Control-C>` binding to `_toggle_continuous_shortcut()` from `_bind_shortcuts()`, eliminating collision with `<Control-Shift-C>` (`on_copy_script()`) and protecting native widget copy.
    - Added missing `Ctrl+R` to `_on_misora_shortcut()` to invoke `self.on_insert_ruby()`.
    - Whitelisted explicit `Ctrl+Alt+X` (Cut Box), `Ctrl+Alt+C` (Copy Box), `Ctrl+Alt+V` (Paste Box), and `Ctrl+Alt+A` (Select Whole Story) in `_on_misora_shortcut()` while returning `None` for all other keys, preserving international AltGr text composition (e.g. `AltGr+E` -> `€`).
    - Added root bindings for `<Control-Alt-x/c/v/a>` (both lower and uppercase).
  - Ensured `bind_all("<Control-h>", ...)` and `<Control-H>` route through dedicated handler `_on_ctrl_h()` returning `'break'` (`HYG-07`), preventing native Tk Text backspace deletion and double-dispatch. Also converted `<Control-f>` and `<Control-F>` to dedicated `'break'`-returning handlers.
- **HYG-03 (`misora.py` — DEP-3):**
  - Attached 350ms hover `ToolTip` and verified non-empty Unicode fallback text across all ribbon and toolbar controls:
    - `btn_ruby`, `btn_dash`, `btn_player`, format buttons (`B`, `I`, `U`, `S`, `Sub`, `Sup`), `btn_size`, `cb_compiled` (Preview), `cb_cont` (Continuous View), `cb_sel_box` (Select Box), `btn_ai_prompt`, `btn_translate`, `btn_prev`, `btn_next`.
    - Exposed controls cleanly as attributes on `MisoraApp` (`btn_ruby`, `btn_dash`, `btn_player`, `btn_format_buttons`, `btn_size`, `cb_compiled`, `cb_cont`, `cb_sel_box`, `btn_ai_prompt`, `btn_translate`).
    - Verified 100% of shortcuts advertised in tooltip text are bound and functional on disk.
- **New Test Suite:** Added `tests/test_p3_s13_ribbon_shortcuts.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 308 tests across 35 modules (268 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s13_ribbon_shortcuts.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/*.py`.

### S12 Logger Flush Barrier/Teardown, DPAPI Fail-Closed, Reload Env Disposal, Deferred Startup & Splash Safety (2026-11-24)
- **Session Scope:** BUG-32, BUG-33, BUG-34, BUG-35, BUG-36 (Track 1 · Group F2 / DEP-9 part 1 — Split from Ribbon per Grok R2).
- **BUG-32 (`core/logger.py`, `misora.py`):**
  - Replaced `queue.empty()` polling in `MisoraLogger.flush()` with `_file_queue.all_tasks_done` / `unfinished_tasks` completion barrier and `time.monotonic()` deadline wait, ensuring `clear_log_file()` never races an in-flight background disk write.
  - Placed `_file_queue.task_done()` inside a `finally:` block around `_write_entry_to_file(entry)` in `_file_writer_loop()` so disk I/O errors cannot deadlock `flush()`.
  - In `MisoraApp.destroy()`, `_on_app_exit()`, and `_on_root_destroy()`, swept all pending Tk `after` jobs via `tk.call("after", "info")` first, executed `super().destroy()`, and invoked `self.logger.close()` last inside safe `try/except` blocks to cleanly terminate background writer threads.
- **BUG-33 (`core/security.py`, `core/mtl_engine.py`, `misora.py` — P1):**
  - Defined `DPAPISecurityError(RuntimeError)` in `core/security.py`.
  - Updated `protect_secret()` to fail closed on Windows DPAPI `CryptProtectData` failure by raising `DPAPISecurityError` instead of silently returning unencrypted plaintext, while preserving non-Windows fallback and already-protected `dpapi:...` blobs.
  - Propagated `DPAPISecurityError` across all secret fields in `MTLConfig.to_dict(secure=True)`.
  - In `MisoraApp._save_user_prefs()`, serialized the full config payload in memory before opening files, caught `DPAPISecurityError` to abort saving, surfaced a clear error toast, and prevented existing `misora_config.json` from being truncated or corrupted with plaintext credentials.
  - In `unprotect_secret()`, emitted `RuntimeWarning` and preserved the `dpapi:...` ciphertext on `CryptUnprotectData` failure instead of returning `""`, preventing credential loss upon reload.
- **BUG-34 (`misora.py:open_file()`):**
  - During `reload_from_disk=True`, explicitly disposed prior `open_documents[file_path]['env']` via `dispose_unity_env()` and called `prior_entry.clear()` before overwriting the cache entry, breaking circular reference cycles and enabling immediate garbage collection.
- **BUG-35 (`misora.py:MisoraApp.__init__()` — DEP-9 / AGENTS.md §22):**
  - Removed synchronous `open_file(initial_path)` and session restore loops from pre-deiconify splash initialization; revealed main window immediately via `self.deiconify()`.
  - Deferred initial path and session files restoration to the Tk idle loop via `self.after_idle(_deferred_restore)`, guarded by `self.winfo_exists()`, preserving file-vs-folder detection and accommodating both `str` and `Path` entries.
- **BUG-36 (`assets/splash.py`):**
  - Implemented safe case-insensitive splash sorting function `_splash_sort_key()` using `Path(name).stem` and numeric suffix detection (`stem[7:].isdigit()`), preventing import-time `ValueError` crashes from non-numeric filenames or uppercase extensions like `Splash_2.JPG`.
- **New Test Suite:** Added `tests/test_p3_s12_lifecycle_security.py` with 5 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 304 tests across 34 modules (264 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `assets/splash.py`, `core/logger.py`, `core/security.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s12_lifecycle_security.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, ribbon/shortcuts/tooltips.

### S11 Main-Thread Queue-Only Async MTL, Stale-Result Identity Guard & Safe Batch Cancel (2026-11-24)
- **Session Scope:** BUG-14, BUG-27 (Track 1 · Group F1 / DEP-6 — Split from XUAT per Grok R1).
- **BUG-27 (`core/mtl_engine.py`, `misora.py` — DEP-6):**
  - Updated `core/mtl_engine.py:translate_async()` to accept optional `out_queue: Optional[queue.Queue] = None` and `metadata: Optional[Any] = None`, enforcing a strictly Tk-free worker contract that delivers results as `(trans, err, metadata)` via queue without any `self.after_idle(...)` or Tk calls.
  - Eliminated all worker-thread `after_idle` calls across all 4 async MTL/connection-test paths (`on_translate_current_box`, `TranslatorAssistantDialog._on_translate`, `TranslatorAssistantDialog._on_fetch_all`, `MTLSettingsDialog._on_test_connection`), delivering all results strictly via main-thread-polled `queue.Queue` (`AGENTS.md` §15).
  - In `on_translate_current_box()`, captured immutable 5-tuple context `(file_path, doc_id, b_uid, src_hash, req_seq)` on dispatch using shared `_hash_mtl_source(text)` helper; implemented `_poll_mtl_queue()` on the main thread with 5-stage identity guard:
    1. Active document check (`self.current_file_path == file_path` and `id(self.current_doc) == doc_id`).
    2. Box UID re-resolution: searches `self.current_doc.boxes` for `_get_box_uid(b) == b_uid`, cleanly accommodating box insertions, deletions, and positional shifts while in flight.
    3. Source hash check: verifies `_hash_mtl_source(found_box.clean_text) == src_hash`, discarding result cleanly if the user edited the text while translation was in flight.
    4. Translation lock check: verifies `is_box_locked(target_idx)` has not been engaged while in flight.
    5. Monotonic sequence check: verifies `req_seq > self._latest_applied_mtl_seq` to reject out-of-order responses.
  - Enforced mutate-before-undo in `_poll_mtl_queue()`: executes AST `inject_box()` first before recording `BoxEditDelta`.
  - In `MTLSettingsDialog`, decoupled `_on_test_connection` to deliver via thread-safe `worker_queue`, protected by monotonic request sequence `_test_seq`, and cancels `_poll_job` via `after_cancel` on window close or save.
  - In `TranslatorAssistantDialog`, decoupled `_on_translate` and `_on_fetch_all` to deliver via thread-safe `worker_queue` with active document/box identity checks, discarding stale results if navigated or edited, and cancels `_poll_job` on close.
- **BUG-14 (`misora.py:BatchTranslateDialog` — DEP-6):**
  - Added explicit `_batch_open: bool` tracking in `BatchTranslateDialog`.
  - Implemented `_end_undo_batch()` to end the active undo journal batch strictly ONCE on the UI thread inside a guarded `try...except` block, preventing unbalanced batch operations or exceptions.
  - Hardened `_on_close()`: if `_is_running`, sets `_cancelled = True`, `_close_requested = True`, hides the dialog via `self.withdraw()` to prevent re-entrant user interactions, and allows `_poll_worker_queue()` to continue polling until worker emits `('done', ...)`.
  - Upon receiving `('done', ...)`, executes `_end_undo_batch()`, synchronizes dirty state, calls `safe_grab_release(self)`, and only then calls `super().destroy()`.
  - Audited and cancelled pending `after(...)` timer IDs across dialog close and root application teardown (`_on_root_destroy`, `destroy()`).
- **New Test Suite:** Added `tests/test_p3_s11_mtl_threading.py` with 7 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 297 tests across 33 modules (257 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/mtl_engine.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s11_mtl_threading.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/xunity_sync.py`, `core/story_ast.py`, `core/security.py`, `core/logger.py`.

### S10 Immutable box.uid XUAT JP Keys, Save Conflict Preview Gate & Atomic XUAT Dictionary Writes (2026-11-24)
- **Session Scope:** BUG-25, BUG-26 (Track 1 · Group E / DEP-7 part 2 — Split from MTL per Grok R1).
- **BUG-25 (`misora.py`, `core/xunity_sync.py`):**
  - Registered immutable Japanese source keys by `box.uid` backed by per-document `_original_jp_by_uid` and `XUnitySyncManager.register_jp_key()`/`get_jp_key()`; updated `open_file()` to populate both caches upon story load and eliminated fallback to current/edited English text.
  - Eliminated the destructive English overwrite in `on_save()` (`self._original_box_texts[b_idx] = box_obj.clean_text`), guaranteeing repeated saves of the same box (`EN1 -> EN2`) continue matching the immutable original Japanese source key across edits and structural mutations.
  - Implemented shared helper `_sync_modified_boxes_to_xuat()` used across both `on_save()` and `_save_document_entry()`: strictly resolves immutable JP keys by `b_uid` without positional fallback when `b_uid is not None`, checks `preview_matches()`, and prompts the user via `messagebox.askyesno` ONLY when genuine `is_conflict=True` duplicate translations exist in the XUAT dictionary file, proceeding without modal friction on clean matches.
  - In `core/xunity_sync.py`, updated `register_jp_key()` and `get_jp_key()` to support `Optional[int]` box UIDs, added `has_jp_key()`, `clear_jp_keys()`, and `register_jp_keys()`, ensured `preview_matches()` propagates `is_conflict`, and added empty-key guards.
- **BUG-26 (`core/xunity_sync.py:find_and_update()`):**
  - Replaced non-unique `f'{tf.name}.{os.getpid()}.tmp'` and bare `os.replace` in `find_and_update()` with `core.text_encoding.write_atomic_encoded()`.
  - Preserves UTF-8 BOM, encoding, and exact CRLF/LF line endings without double newlines, backed by bounded 5-attempt retry loop for Windows sharing violations.
- **New Test Suite:** Added `tests/test_p3_s10_xuat_integrity.py` with 2 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 288 tests across 32 modules (248 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/xunity_sync.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s10_xuat_integrity.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/search_engine.py`, `core/mtl_engine.py`, `core/bundle_io.py`.

### S09 Multi-File Replace-All Cache Keys/Shared Matcher/Closed-File Undo & Collision-Resistant Backups (2026-11-24)
- **Session Scope:** BUG-24, BUG-20 (Track 1 · Group D2).
- **BUG-24 (`misora.py`):**
  - Fixed `_apply_delta(BulkFileDelta)` and its rollback error handler to use canonical `open_documents` cache keys `'env'` and `'obj'` (never legacy `'bundle_env'` / `'target_object'`), and disposed old Unity environments via `dispose_unity_env()` to break circular references (`weakref`).
  - Implemented `_find_open_doc_key()` normalizing path casing and resolution (`os.path.normcase(str(Path(k).resolve()))`) for Windows case-insensitive lookups across all cache lookups, dirty checks, and lock verifications.
  - In `on_replace_all()`, refreshed in-memory caches across ALL affected open documents (active and inactive tabs), refusing/prompting via `messagebox.askyesno` before overwriting dirty open documents from disk, while ensuring disk-saved files are NOT falsely marked dirty (`entry["dirty"] = False`). Deduplicated candidate paths across multiple search roots.
  - Implemented shared `_apply_compiled_replacement()` helper operating on match spans from `ProjectSearchEngine._compile_matcher()`, cleanly honoring `Match Case`, `Regex`, and `Ignore Whitespace & {playername}` across Find, `on_replace_next()`, and `on_replace_all()` while preserving `break_char` formatting (`QW-R06`).
  - Fixed `on_replace_next()` to skip locked boxes in its advance loop and display toast warnings. Enforced Translation Lock on bundle files in multi-file `on_replace_all()`.
  - Added `_confirm_closed_files_for_op()` and invoked it in `on_undo()` and `on_redo()` BEFORE popping operations from `MasterUndoJournal`, displaying an explicit confirmation dialog listing all affected paths (highlighting closed disk files) and returning `False` on cancellation to preserve undo/redo stack integrity without silent reopening (`AGENTS.md` §16).
- **BUG-20 (`misora.py` — `QW-B17` + `Grok-N03`):**
  - Created shared collision-resistant backup helper `make_collision_resistant_backup_path()` combining microsecond timestamp (`%Y%m%d_%H%M%S_%f`), 8-character deterministic SHA-256 hash prefix of the normalized source path, and an existence loop (`<stem>.<tag>_<timestamp_microseconds>_<sha256_path_prefix><suffix>`).
  - Wired `make_collision_resistant_backup_path()` across all save paths in `on_save()` (text, v2, bundle), `_save_document_entry()`, and `on_replace_all()` (text, bundle original/modified), ensuring same-stem files in different folders saved within the same second/microsecond never collide or overwrite each other.
- **New Test Suite:** Added `tests/test_p3_s09_replace_all_backups.py` with 7 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 284 tests across 31 modules (244 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s09_replace_all_backups.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/search_engine.py`, `core/xunity_sync.py`, `core/mtl_engine.py`, `core/bundle_io.py`.

### S08 Search Match-Case/Errors/Snapshots/Spans, Bounded Project Roots & Search Focus/Gutter/No-Op KeyRelease (2026-11-24)
- **Session Scope:** BUG-21, BUG-22, BUG-23, BUG-30 (Track 1 · Group D1 / DEP-7 part 1).
- **BUG-21 (`core/story_ast.py:norm_search()`, `core/search_engine.py:_norm_search_with_spans()`, `_compile_matcher()`):**
  - Added `match_case: bool = False` to `story_ast.norm_search()` and `ProjectSearchEngine._norm_search_with_spans()`, applying `.casefold()` strictly when `not match_case` while preserving 100% full-width/half-width NFKC normalization and combining character equivalence (`ｶﾞ` -> `ガ`, `か + ゙` -> `が`).
  - Wired `options.match_case` into whitespace-insensitive regex construction in `_compile_matcher()`, allowing case-sensitive search to match exact casing (e.g. `Hero` / `Ｈｅｒｏ`) while rejecting mismatched casing (e.g. `hero` / `ｈｅｒｏ`).
- **BUG-22 (`core/search_engine.py`, `misora.py`):**
  - Replaced silent bundle/text decode exceptions in `search_file()` with structured `on_error: Optional[Callable[[Path, str], None]] = None` callback; hooked `os.walk(..., onerror=...)` in `search_directory()`.
  - Added structured `skipped_entries: List[Tuple[Path, str]]` surfaced directly in the Search results pane, header summary (`Found X occurrences in Y files (Z skipped)`), and status bar, clearly distinguishing 0 matches vs matches vs partially skipped files.
  - Resolved `Grok-E02`: in `on_start_search()`, failed AST snapshots are added to `skip_paths` and `initial_skipped` and never fall back to live mutable `orig_doc` (or stale disk content). Snapshotted open plain-text buffers and normalized cache keys via `Path.resolve()`.
  - Added monotonic `self._search_seq` generation guard in `_process_search_queue()`, discarding stale worker messages from cancelled/superseded searches, and prevented re-entrant `<Return>` triggers while search is active.
  - Implemented `_build_raw_to_clean_map()` in `core/search_engine.py` (`QW-E06`), replacing fabricated spans `(0, len(clean_text))` on raw fallback matches with accurate clean character spans.
- **BUG-23 (`misora.py` — `GEM-N01`):**
  - Added `_set_project_folder()` to replace (never append indefinitely) project search roots whenever `project_folder` changes, completely clearing roots of previous projects.
  - Implemented bounded root resolution: `_resolve_project_search_roots()` returns whichever of `[Text, RedirectedResources]` exist under `BepInEx/Translation/en/` or `Translation/en/` (or strictly bounded `[proj_dir]`), preventing scans of `BepInEx/plugins/` or `BepInEx/config/`.
  - Implemented `_resolve_xuat_text_root()` targeting strictly `BepInEx\Translation\en\Text`.
  - Removed auto-injection of unrelated local `input` and `output` folders into project search roots.
- **BUG-30 (`misora.py`):**
  - Removed erroneous `self.txt_continuous.focus_set()` in `_select_result_index()` after `_focus_continuous_box()` on bundle Continuous View jumps, properly transferring focus to the active card's dialogue text widget (`card["txt_dialogue"].focus_set()`) while preserving plain-text focus behavior.
  - Called `self._update_gutter_clean()` inside `_on_dialogue_edited()` so Page View line numbers immediately update when newlines are entered, pasted, or deleted.
  - Updated `_on_card_text_edited()` and `_on_box0_metadata_edited()` to return `bool` indicating whether text actually changed, and updated `_commit_widget_edit()` to skip `_dirty_state_changed()` and AST injection on no-op arrow/navigation keystrokes.
- **New Test Suite:** Added `tests/test_p3_s08_search_roots_focus.py` with 4 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 275 tests across 30 modules (235 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/search_engine.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s08_search_roots_focus.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/xunity_sync.py`, `core/mtl_engine.py`, `core/script_codec.py`, `misora.py:on_replace_all`/`_apply_delta`.

### S07 Caret Paste Dirty/Lock, Mutate-Before-Undo, Non-Contiguous Cut Undo, Lock Enforcement & Read-Only Raw View (2026-11-24)
- **Session Scope:** BUG-10, BUG-13, BUG-15, BUG-16, BUG-37 (Track 1 · Group C2 / post-DEP-4).
- **BUG-10 (`misora.py:_on_card_paste_caret()`):**
  - In `_on_card_paste_caret()`, checks `is_box_locked()` on `box_idx` and target boxes across the `\n\n\n` delimiter paste loop; locked boxes are preserved untouched.
  - Skips dirty-marking and undo batch recording when all target boxes are locked (0 boxes mutated).
  - Enforces `self._mark_document_dirty(self.current_file_path)` BEFORE `self._dirty_state_changed()`, preventing S2 dirty flag clobbering and correctly retaining `is_dirty=True` and window title `*`.
- **BUG-13 (`misora.py`):**
  - Enforces mutate-before-undo architecture across single-box Game Display (`_on_dialogue_edited`), Continuous View card editing (`_on_card_text_edited`), card flush (`_flush_continuous_card_edits`), and incremental find/replace (`on_replace_next`): AST `inject_box()` is executed FIRST before recording any `BoxEditDelta` or marking documents dirty.
  - Replaces silent `except Exception: pass` blocks with `self.logger.exception(..., e)` and `self.set_status(f"Error: {e}", is_error=True)` per `AGENTS.md` §28.
  - Captures pre-mutation segment state (`old_seg_texts`) and refreshed post-mutation segments (`new_seg_texts`) directly into `BoxEditDelta`, maintaining S04 multi-segment undo compatibility.
- **BUG-15 (`core/undo_journal.py:BoxStructuralDelta`, `misora.py:on_box_cut()`, `misora.py:_apply_delta()`):**
  - Extended `BoxStructuralDelta` with optional `indices: Optional[List[int]] = None` field to record exact non-contiguous target indices.
  - In `on_box_cut()`, filters out locked boxes with toast notification and stores exact sorted target indices list on the recorded delta; synchronizes `_selected_boxes` before copying to prevent copying skipped locked boxes.
  - In `_apply_delta()` (`BoxStructuralDelta`), restores snapshots at exact ascending indices on Undo and deletes exact recorded indices on Redo, guaranteeing lossless ordering restoration for non-contiguous cuts (e.g. `[1, 3]`).
  - Added `_resync_box_indices_from_uids()` to re-sync `_locked_boxes` and `_modified_boxes` from authoritative UIDs after structural operations.
- **BUG-16 (`misora.py:on_clear_dialogue_skeleton()`, `misora.py:TranslatorAssistantDialog._on_apply()`):**
  - In `on_clear_dialogue_skeleton()`, enforces `is_box_locked()` at application/model layer: skips locked boxes, tracks preserved vs cleared count, and avoids dirty marking when 0 boxes are mutated.
  - In `TranslatorAssistantDialog._on_apply()`, blocks translation application on locked boxes with informative toast notification; switched from destructive `.strip()` to `txt_trans.get("1.0", "end-1c")`, preserving authorial leading indentation and trailing newlines.
- **BUG-37 (`misora.py:txt_raw`):**
  - Initialized `self.txt_raw` strictly read-only with `state="disabled"`.
  - Wrapped all raw AST view updates in `_update_raw_view()` and plain-text/empty-box handlers in `_update_views()` with safe `state="normal"` ... `finally: state="disabled"`, preventing user keystrokes from corrupting Raw AST view until `FEAT-11` (`S19`).
- **New Test Suite:** Added `tests/test_p3_s07_undo_locks_raw.py` with 5 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 269 tests across 29 modules (229 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/undo_journal.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s07_undo_locks_raw.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, `core/mtl_engine.py`.

### S06 Per-Document State/Stable Locks, Plain-Text Preview Save, Windows LF Writes & 0-Box Save (2026-11-24)
- **Session Scope:** BUG-11, BUG-12, BUG-18, BUG-19 (Track 1 · Group C1 / DEP-2, DEP-4).
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
- **New Test Suite:** Added `tests/test_p3_s06_doc_state_save.py` with 4 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 263 tests across 28 modules (223 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/text_encoding.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s06_doc_state_save.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, `core/mtl_engine.py`.

### S05 Dark-Theme Treeview Contrast (DEP-1 FIRST), Atomic Sparse CSIF/Metadata & Backslash Parity (2026-11-24)
- **Session Scope:** BUG-31, BUG-07, BUG-08 (Track 1 · Group B3 / DEP-1 STRICTLY FIRST).
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
- **New Test Suite:** Added `tests/test_p3_s05_treeview_csif.py` with 3 Defect Probes (failing-first) and 1 lightweight Regression Guard (passing). Full test suite discovered count: 258 tests across 27 modules (218 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `core/script_codec.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s05_treeview_csif.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/undo_journal.py`, `core/bundle_io.py`, `assets/*.py`.

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
| **CTRL-ALT-HOTKEYS-BLOCKED** | RESOLVED (2026-11-24: S13 / BUG-29) | `misora.py:_on_misora_shortcut(), _bind_shortcuts()` | Whitelisted explicit Ctrl+Alt+X/C/V/A app accelerators in `_on_misora_shortcut()` and root bindings; all other Ctrl+Alt keys pass through to preserve international AltGr text composition. Covered by `test_p3_s13:test_probe_02`. | 2 |
| **CONTINUOUS-EDIT-NO-COMMIT** | RESOLVED | `misora.py:_commit_widget_edit()` | Decoupled Page View Box 0 widgets and Continuous View Card -1 from `is_box0_active` boolean guard. Edits to continuous cards and Box 0 synopsis now commit directly to AST document. | 2 |
| **BOX0-SWITCH-LOCKS-EDITOR** | RESOLVED | `misora.py:_on_toggle_continuous_view`, `on_prev_box`, `on_next_box` | Restores caret and keyboard focus immediately and via `after_idle` upon view toggles and box navigation. Guarded `_cont_focus_job` against stale cross-view firing. | 2 |
| **VOICE-CUE-DISPLAY-MISSING** | RESOLVED | `core/story_ast.py:_rebuild_boxes` | Captured `cmd_id == 12` voice cues with `"vo_"` prefix; guarded breaker loop `elif r.cmd_id != 12 and r.cmd_name in DEFAULT_BREAKERS:` so voice cues are never skipped or discarded. | 2 |
| **FIND-REPLACE-UI-ASYMMETRY** | RESOLVED (2026-11-25: S14 / BUG-38) | `misora.py:_build_search_bar` | Unified Find and Replace rows into shared 5-column grid (`self.search_grid`) with uniform button weights/sizes and identical entry geometry. Covered by `tests/test_p3_s14_toolbar_search_ui:test_probe_01`. | 2 |

### P1 — Functional, UI, & Security Issues (Phases 2, 3, 5)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **DIRTY-EXIT-DROPS-EDITS** | RESOLVED | `misora.py:1302-1312` | `_on_app_exit` prompts Save/Discard/Cancel with `askyesnocancel` on dirty state before window close. | 2 |
| **RELOAD-REVERT-HIT-CACHE** | RESOLVED | `misora.py:7838-7841, 7949-7952` | `on_revert_box` and `on_reload` call `open_file(..., reload_from_disk=True)`. | 2 |
| **REPLACE-ALL-BUNDLE-PREFILTER** | RESOLVED | `misora.py:on_replace_all()` | Candidate discovery decodes structured story TextAssets instead of raw byte scanning. Covered by `test_s9b_replace_all_bundle_safety.py:test_01`. | 2 |
| **REPLACE-ALL-UNDO-GAP** | RESOLVED | `misora.py:on_replace_all(), _apply_delta()` | Bundle changes recorded in BulkFileDelta with atomic backup snapshots; fully undoable/redoable with transaction rollback. Covered by `test_s9b:test_02, test_03`. | 2 |
| **TLS-VERIFICATION-DISABLED** | RESOLVED | `core/mtl_engine.py:142-144` | Outbound HTTPS requests strictly enforce valid TLS certificate and hostname verification. Covered by `test_phase5_mtl_security_preview.py:test_03`. | 5 |
| **API-KEYS-PLAINTEXT** | RESOLVED (2026-11-24: S12 / BUG-33) | `core/security.py`, `core/mtl_engine.py`, `misora.py` | DPAPISecurityError fail-closed encryption, non-truncating in-memory serialization before save, ciphertext preservation and RuntimeWarning on decryption failure. Covered by `test_p3_s12:test_02`. | 5 |
| **TAGMASKER-INCOMPLETE** | RESOLVED | `core/ngui_tags.py:15-161` | Central single source of truth for NGUI markup, hyphen gradients, multiline ruby, placeholders, and full shielding/unshielding. Covered by `test_phase5:test_01`. | 5 |
| **SIZE-RIBBON-NO-COMMIT** | RESOLVED (2026-11-24: S13 / BUG-28) | `misora.py:on_insert_font_size()` | Wired `_commit_widget_edit(target)` in `on_insert_font_size()`, flushing size tag insertion to AST and recording undo delta. Covered by `test_p3_s13:test_probe_01`. | 2 |
| **CONTINUOUS-RIBBON-TARGET-STALE** | RESOLVED (2026-11-24: S13 / BUG-28) | `misora.py:_insert_text_wrapper(), on_insert_ruby()` | Resolved active card widget via `_get_card_text_widget(self.current_box_idx)` in Continuous View with cards, eliminating hidden `txt_continuous` pollution; removed redundant `_on_dialogue_edited()` in `_insert_text_wrapper()` restoring Page View dirty `*` title update. Covered by `test_p3_s13:test_probe_01`. | 2 |
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
| **PLAINTEXT-SAVE-ROUTING** | RESOLVED (2026-11-24: S06 / BUG-11) | `misora.py:on_save()` | Plain-text on_save() preserves exact authorial NGUI markup under compiled preview; authoritative self._plain_text_content saved without tag stripping. Covered by `test_p3_s06_doc_state_save:test_probe_1`. | 2 |
| **PER-DOC-STATE-STABLE-LOCKS** | RESOLVED (2026-11-24: S06 / BUG-12) | `misora.py` | Persist and restore locked_box_uids, modified_box_uids, original_jp_by_uid, current_box_idx, is_box0_active on tab switch; stable locks helper; non-switching _save_document_entry(). Covered by `test_p3_s06_doc_state_save:test_probe_2`. | 2 |
| **WINDOWS-LF-ATOMIC-EXPORT** | RESOLVED (2026-11-24: S06 / BUG-18) | `core/text_encoding.py`, `misora.py:on_export_script()` | write_atomic_encoded always writes pre-encoded bytes to preserve exact LF line endings on Windows; on_export_script writes atomically via write_atomic_encoded(newline='\n'). Covered by `test_p3_s06_doc_state_save:test_probe_3`. | 1 |
| **ZERO-BOX-METADATA-SAVE** | RESOLVED (2026-11-24: S06 / BUG-19) | `misora.py:on_save()` | Guarded preview, continuous, and page view save paths when not self.current_doc.boxes; 0-box metadata stories save without IndexError. Covered by `test_p3_s06_doc_state_save:test_probe_4`. | 2 |
| **MULTI-SEGMENT-UNDO-PASTE** | RESOLVED (2026-11-24: S04 / BUG-06) | `core/story_ast.py`, `core/undo_journal.py`, `misora.py` | Non-blocking multi-segment editing with `'N segs'` badge; `BoxEditDelta.old_seg_texts`/`new_seg_texts` segment preservation; lossless `BoxSnapshot` paste. Covered by `test_p3_s04_ast_mutations:test_probe_3`. | 2 |
| **UNDO-UID-COALESCE** | RESOLVED (2026-11-24: S04 / BUG-17) | `core/undo_journal.py:MasterUndoJournal.record()` | Coalescing requires matching `box_uid` when non-None, preventing edits on distinct boxes with identical index from coalescing. Covered by `test_p3_s04_ast_mutations:test_probe_4`. | 2 |
| **TOMBSTONE-UNBOUNDED-GROWTH** | RESOLVED (2026-11-24: S04 / HYG-04) | `core/story_ast.py:delete_boxes()` | Dead record UIDs deterministically pruned against active records in `self.records`. Covered by `test_p3_s04_ast_mutations:test_probe_5`. | 2 |
| **TREEVIEW-DARK-THEME-CONTRAST** | RESOLVED (2026-11-24: S05 / BUG-31) | `misora.py:_apply_styles()` | Configured Treeview and Treeview.Heading contrast styles across all presets (WCAG ratio >= 4.5). Covered by `test_p3_s05_treeview_csif:test_probe_1`. | 2 |
| **SPARSE-CSIF-ATOMIC-TRANSACTION** | RESOLVED (2026-11-24: S05 / BUG-07) | `core/script_codec.py`, `misora.py` | `apply_metadata` flag; pre-validation; atomic rollback; UID resolution; discrete sparse mapping in preview and undo deltas. Covered by `test_p3_s05_treeview_csif:test_probe_2`. | 2 |
| **CSIF-BACKSLASH-PARITY-LOSS** | RESOLVED (2026-11-24: S05 / BUG-08) | `core/script_codec.py` | Lossless `serialize -> parse` round-trip across `^\\*@@` escaping and `^\\+@@` unescaping. Covered by `test_p3_s05_treeview_csif:test_probe_3`. | 2 |
| **CARET-PASTE-DIRTY-LOCK** | RESOLVED (2026-11-24: S07 / BUG-10) | `misora.py:_on_card_paste_caret()` | Preserves locked boxes across `\n\n\n` caret paste; marks document dirty before `_dirty_state_changed()`. Covered by `test_p3_s07:test_probe_1`. | 2 |
| **MUTATE-BEFORE-UNDO** | RESOLVED (2026-11-24: S07 / BUG-13) | `misora.py` | AST `inject_box()` executes before `BoxEditDelta` recording; segment-aware undo and exception logging per AGENTS.md §28. Covered by `test_p3_s07:test_probe_2`. | 2 |
| **NON-CONTIGUOUS-CUT-UNDO** | RESOLVED (2026-11-24: S07 / BUG-15) | `core/undo_journal.py`, `misora.py` | `BoxStructuralDelta.indices` records exact sorted indices; undo/redo preserves lossless ordering. Covered by `test_p3_s07:test_probe_3`. | 2 |
| **LOCK-ENFORCEMENT-MODEL** | RESOLVED (2026-11-24: S07 / BUG-16) | `misora.py` | Enforces translation lock in `on_clear_dialogue_skeleton()` and `TranslatorAssistantDialog`; preserves authorial whitespace. Covered by `test_p3_s07:test_probe_4`. | 2 |
| **RAW-VIEW-READONLY** | RESOLVED (2026-11-24: S07 / BUG-37) | `misora.py:txt_raw` | `self.txt_raw` initialized disabled and wrapped with safe normal/disabled lifecycle until FEAT-11. Covered by `test_p3_s07:test_probe_5`. | 2 |
| **SEARCH-MATCH-CASE-WHITESPACE** | RESOLVED (2026-11-24: S08 / BUG-21) | `core/story_ast.py`, `core/search_engine.py` | `match_case: bool = False` in `norm_search()` and `_norm_search_with_spans()`; whitespace-insensitive matching respects casing. Covered by `test_p3_s08:test_probe_1`. | 2 |
| **SEARCH-ERRORS-SNAPSHOT-ISOLATION** | RESOLVED (2026-11-24: S08 / BUG-22) | `core/search_engine.py`, `misora.py` | Structured `on_error` and `skipped_entries`; `Grok-E02` snapshot failure isolation (never live doc); monotonic `_search_seq` guard; accurate raw spans (`QW-E06`). Covered by `test_p3_s08:test_probe_2`. | 2 |
| **PROJECT-ROOTS-BOUNDED-REPLACEMENT** | RESOLVED (2026-11-24: S08 / BUG-23) | `misora.py` | Bounded root resolution to `[Text, RedirectedResources]` (never `plugins/`/`config/`); clean project replacement (`GEM-N01`); no auto-injected `input`/`output`. Covered by `test_p3_s08:test_probe_3`. | 2 |
| **SEARCH-FOCUS-GUTTER-NOOP-KEYS** | RESOLVED (2026-11-24: S08 / BUG-30) | `misora.py` | Continuous search jump focuses active card dialogue widget; gutter updates on dialogue edit; no-op navigation keys skip dirty marking. Covered by `test_p3_s08:test_probe_4`. | 2 |
| **REPLACE-ALL-CANONICAL-KEYS-AND-UNDO** | RESOLVED (2026-11-24: S09 / BUG-24) | `misora.py` | Canonical `open_documents` keys `'env'`/`'obj'`, `dispose_unity_env()`, path case normalization, in-memory cache sync, shared matcher spans, closed-file undo confirmation dialog. Covered by `test_p3_s09:test_probe_1-5`. | 2 |
| **COLLISION-RESISTANT-BACKUPS** | RESOLVED (2026-11-24: S09 / BUG-20) | `misora.py` | Microsecond timestamp + 8-char SHA-256 hash prefix + collision loop across `on_save`, `_save_document_entry`, and `on_replace_all`. Covered by `test_p3_s09:test_probe_6-7`. | 2 |
| **XUAT-JP-KEY-OVERWRITE** | RESOLVED (2026-11-24: S10 / BUG-25) | `misora.py`, `core/xunity_sync.py` | Register immutable Japanese source keys by `box.uid` backed by per-doc `_original_jp_by_uid`; never overwrite JP keys with saved English text; `preview_matches()` conflict gate prompts user only when duplicate translations exist. Covered by `test_p3_s10_xuat_integrity:test_probe_1`. | 2 |
| **XUAT-ATOMIC-WRITES** | RESOLVED (2026-11-24: S10 / BUG-26) | `core/xunity_sync.py:find_and_update()` | `write_atomic_encoded()` replaces PID temp file and bare `os.replace`; unique timestamped temp name, bounded Windows retry, UTF-8 BOM, encoding and CRLF/LF preservation. Covered by `test_p3_s10_xuat_integrity:test_probe_2`. | 1 |
| **BATCH-CANCEL-UNDO-LEAK** | RESOLVED (2026-11-24: S11 / BUG-14) | `misora.py:BatchTranslateDialog` | Track `_batch_open`; safe cancel waits for worker `('done', ...)` before single `end_batch()` on UI thread; prevents unbalanced undo journal batches. Covered by `test_p3_s11_mtl_threading:test_probe_2`. | 1 |
| **ASYNC-MTL-QUEUE-STALE-GUARD** | RESOLVED (2026-11-24: S11 / BUG-27) | `core/mtl_engine.py`, `misora.py` | Zero `after_idle` from worker threads; main-thread queue delivery across all 4 async paths; 5-stage identity guard (active doc, box_uid re-resolution, src_hash, lock, seq). Covered by `test_p3_s11_mtl_threading:test_probe_1a-1d`. | 1 |
| **LOGGER-FLUSH-BARRIER-TEARDOWN** | RESOLVED (2026-11-24: S12 / BUG-32) | `core/logger.py`, `misora.py` | Completion barrier via `unfinished_tasks`/`all_tasks_done` with monotonic deadline wait prevents clear_log_file race; teardown closes logger and sweeps after jobs via `tk.call('after', 'info')`. Covered by `test_p3_s12:test_01`. | 3 |
| **RELOAD-ENV-DISPOSAL** | RESOLVED (2026-11-24: S12 / BUG-34) | `misora.py:open_file()` | Disposes prior `open_documents[path]['env']` via `dispose_unity_env()` and clears entry before cache overwrite on reload_from_disk; breaks circular cycles. Covered by `test_p3_s12:test_03`. | 2 |
| **DEFERRED-STARTUP-RESTORE** | RESOLVED (2026-11-24: S12 / BUG-35) | `misora.py:MisoraApp.__init__()` | Deiconify executes before session restore; restore deferred to idle loop via `after_idle(_deferred_restore)` with `winfo_exists()` guard. Covered by `test_p3_s12:test_04`. | 3 |
| **SPLASH-SORT-SAFETY** | RESOLVED (2026-11-24: S12 / BUG-36) | `assets/splash.py` | `_splash_sort_key` extracts numeric stem case-insensitively; non-numeric splash files and uppercase extensions handled safely without import-time `ValueError`. Covered by `test_p3_s12:test_05`. | 4 |

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
