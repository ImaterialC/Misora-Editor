# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] (Target: v1.4.1)

### S20 — Docked Right-Side MTL Drawer: Tab Infrastructure & `Dialogue` Multi-Engine Stack
- **Session Scope:** FEAT-12 (`U-B9`, `U-B32` — Track 2 · Group G6a, post-`DEP-6`).
- **Right-Side Drawer `'MTL'` Tab (`misora.py`):**
  - Added **`MTL`** as the 3rd tab in the right-side drawer (`Customize` | `NGUI Glossary` | `MTL`) via `_build_side_drawer()` and `_switch_side_drawer_tab()`, and routed `Translator -> Translator Assistant...` (`Ctrl+T`) and the `MTL` toolbar button (`on_open_translator_assistant()`) to toggle the docked `'mtl'` drawer tab (retiring the floating `TranslatorAssistantDialog` entry point while keeping the class intact for backward-compatible test guards).
- **`Dialogue` (1-Box) Multi-Engine Stack (`misora.py`):**
  - Vertically stacks engine cards **only** for user-enabled engines (default: `XUAT Cache` + `Google`; opt-in toggles for `DeepL`, `Local / Sugoi`, `LLM / OpenAI` persisted in `misora_config.json`).
  - Each card features an editable scratchpad isolated from `"MisoraShortcuts"` story-widget routing with local `Ctrl+Z` / `Ctrl+Y` (`tk.TclError`-safe), per-card `↻` Refresh (bypasses session cache), and per-card `→` Apply (enforces model-level Translation Lock, preserves whitespace with zero `.strip()`, mutates AST before recording `BoxEditDelta(source="mtl")` with `old_seg_texts`/`new_seg_texts`).
  - Top `Refresh All` refreshes enabled engines only, uses a 256-entry LRU `OrderedDict` session cache, and prompts `messagebox.askyesno` confirmation before batch-calling paid APIs (`DeepL`, `LLM / OpenAI`).
  - All async worker calls run `TagMasker`-protected `translate_async()` via `queue.Queue` and main-thread on-demand `_poll_mtl_drawer_queue()` (`after(50, ...)` cancelled on teardown) with `(file_path, doc_id, box_uid, src_hash, req_seq, engine)` stale guards (`BUG-27`, `BUG-32`).
- **Tests:** Added `tests/test_p3_s20_mtl_drawer_dialogue.py` (2 failing-first Defect Probes + 1 Regression Guard).

### S19 — Whole-File Editable `Raw Commands` (Lossless v2, Confirm, `DocumentRecordsDelta` Undo & Lock/JP Remap)
- **Session Scope:** FEAT-11 (`U-B31` — Track 2 · Group G5, post-`DEP-5`).
- **Undo Journal (`core/undo_journal.py`, `core/__init__.py`):**
  - Added `DocumentRecordsDelta` holding before/after deep `Record` list snapshots, `removed_records`, cursor bounds, and lock/JP-key state, with `"Edit Raw Commands"` auto-labeling.
- **Whole-File Raw Commands v2 Editor (`misora.py`):**
  - Added explicit `Edit Raw (v2)` / `Apply Raw` / `Revert / Cancel` controls in the `Raw Commands` header (`raw_header`) with 350ms tooltips and theme role styling; kept `txt_raw` strictly read-only (`state="disabled"`) outside Edit Raw mode (`BUG-37`).
  - Flushes pending Dialogue/All Script edits before entering Edit Raw mode, prevents `_update_raw_view()` from clobbering unsaved v2 text while editing, and exits cleanly on file switch or cancel.
  - Validates v2 text via `_parse_and_validate_raw_v2()` (strict header/ID/b64 checks + `to_binary()` / `from_binary()` record count, `cmd_id`, and argument parity round-trip; ZERO command-specific arity checks `NO-07`; preserves `cmd_id` 35 & 32 `DEF-02`).
  - On `Yes` confirmation, atomically replaces `current_doc.records`, rebuilds `boxes`, remaps Translation Locks and immutable JP keys via `get_document_stable_locks()` / `restore_stable_locks()` (`CLAUDE-N02`) + `XUnitySyncManager.register_jp_key()`, records ONE `DocumentRecordsDelta`, marks dirty, and refreshes all views. On `No` or validation error, aborts with zero mutation.
  - Added `DocumentRecordsDelta` handling in `_apply_delta()` with safe `current_box_idx` / `is_box0_active` bounds clamping and full lock/JP-key restoration.
- **Tests:** Added `tests/test_p3_s19_raw_commands_edit.py` (3 failing-first Defect Probes + 1 Regression Guard).

### S18 — Code-Drawn Game-Style `Dialogue Preview` & `All Script Preview`
- **Session Scope:** FEAT-10 (`U-B27`, `U-B28` — Lead Ruling #4, `NO-02`, `NO-12`) — Track 2 · Group G4b (post-DEP-2, DEP-8).
- **Code-Drawn Priconne-Style Dialogue Preview (`misora.py`):**
  - Added single `tk.Canvas` (`dialogue_preview_canvas`) + one embedded read-only `tk.Text` (`txt_dialogue_preview`) drawing native Tk Priconne-style double borders (`#d4af37`/`#e6c875`/`#fffcf4`), speaker name plate with `best_contrast_fg()`, and static pink `▼`, with ZERO copyrighted `AtlasAdv` sprites (`NO-02`).
  - Consumes S17's `_measure_dialogue_metrics()` (`safe_w` = 50 digit-widths × 3-line safe area) and enforces `wrap="none"` with NO font auto-shrinking (`NO-12`) so >50d lines and 4+ lines visibly bleed past the calibrated frame.
  - Extracted `_sweep_cstyle_tags()` (`GEM-E03`) to sweep `cstyle_*` tags on every render/box switch; preserves caret, selection, and `yview` on Preview OFF (guarded by file/box identity), restores `ruler_clean` above `clean_editor_row`, and keeps Box 0 / plain-text / 0-box fallbacks safe (`DEF-04`, `BUG-11`).
- **All Script Preview (`misora.py`):**
  - Updated `_render_continuous_view()` compiled mode to render lightweight styled `tk.Frame` cards (zero per-card `tk.Canvas` widgets) with `wrap="none"`, no auto-shrinking, `safe_w` boundary bar, and static pink `▼`.
- **Tests:** Added `tests/test_p3_s18_game_preview.py` (2 failing-first Defect Probes + 1 Regression Guard).
- **Files Created:** `tests/test_p3_s18_game_preview.py`.
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/`.

### S17 — Shared Pixel-Measure Helper, Calibrated Rulers (50 Digit-Widths / Line 4+) & Remove Char Counter
- **Session Scope:** BUG-40, FEAT-09 (`U-B22..U-B26`, `DEP-8` — Lead Ruling #4) — Track 2 · Group G4a.
- **Pixel-Calibrated Measurement & Overflow Highlighting (`misora.py`):**
  - Added `_get_dialogue_measure_font()` and `_measure_dialogue_metrics()` driven by the active editor font (`safe_w = font.measure("1234567890" * 5)` = 50 digit-widths, labeled as an estimate of the in-game font), using kerning-accurate prefix measurement (`font.measure(prefix)`), 0px NGUI tag stripping, ruby base-only measurement, non-zero `{playername}`/`{N}` placeholder width, and exact raw-character overflow index mapping.
  - Replaced static `Consolas 9pt` `tk.Text` rulers (`ruler_clean`, `ruler_cont`) with pixel-calibrated `tk.Canvas` rulers aligned to the editor text origin, showing a red overflow zone past 50 digit-widths (`est. >50d`).
  - Added `"gutter_overflow"` red/bold styling on vertical line-number gutters from line 4+ (3 or more linebreaks) in both Dialogue and All Script views.
  - Added theme-legible `"line_overflow"` inline highlighting (`_apply_overflow_highlights()`) for characters past `safe_w` on each logical line.
  - Removed inaccurate `lbl_char_count`, `_update_rendered_char_count()`, and card `(N chars)` labels (keeping `core/ngui_tags.py:measure_line_lengths()` intact).
- **Docs & Tests:** Updated `README.md` and `tests/test_phase5_mtl_security_preview.py` (`test_06` lines 268–277); added `tests/test_p3_s17_pixel_rulers.py` (1 failing-first Defect Probe + 1 Regression Guard).
- **Files Created:** `tests/test_p3_s17_pixel_rulers.py`.
- **Files Modified:** `misora.py`, `README.md`, `tests/test_phase5_mtl_security_preview.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/ngui_tags.py`, `core/story_ast.py`, `assets/`.

### S16 — `.misora` v1 Workspace Session & Overwrite Diff Dialog
- **Session Scope:** FEAT-08 (`U-B17`, `U-B18`) — Track 2 · Group G3 (post-DEP-4, DEP-9).
- **Core Workspace (`core/workspace.py`, `core/__init__.py`):**
  - Added pure-Python `.misora` v1 atomic JSON serialization/deserialization (`save_workspace`, `load_workspace`) via `write_atomic_encoded` and `read_text_file_strictly`, storing **strictly** file references (`rel_path` + `abs_path`), workspace state (`active_file`, `active_box_idx`, `is_box0_active`, `view_mode`, `search_scope`), and composite stable-key Translation Locks `(box_ordinal, jp_sha256)` — never unsaved story drafts, `.unity3d` binary blobs, or runtime `Record.uid` (`NO-01` / `NO-12`).
  - Added `safe_relpath` (cross-drive Windows `ValueError` guard), `resolve_workspace_file_path` (relative-first then absolute fallback), `match_active_file` (portable `rel_path`/`abs_path` matching), and `compute_workspace_diff` (normalized Added/Removed/Kept + Dirty diff).
- **UI & Session Integration (`misora.py`):**
  - Added `File > Open Project (.misora)...` and `File > Save Project (.misora)...` menu commands, plus drag-and-drop `.misora` support in `_handle_dropped_paths()`.
  - Added modal `ProjectDiffDialog` (`U-B18`, `AGENTS.md` §16) displaying old-vs-new file changes (`Added`/`Removed`/`Kept`, `* Unsaved`/`Clean`) with `Save Current` / `Discard & Open` / `Cancel`, flushing active edits before diffing and aborting cleanly on `Cancel` or failed save.
  - Restores open tabs via batched `open_file(..., refresh_ui=False)`, re-attaches Translation Locks strictly via `restore_stable_locks()` (leaving unmatched locks unresolved and notifying the user, never silently transferring locks), handles missing files gracefully, and syncs view/header/scope controls.
- **Test Suite:** Added `tests/test_p3_s16_misora_workspace.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing).
- **Files Created:** `core/workspace.py`, `tests/test_p3_s16_misora_workspace.py`.
- **Files Modified:** `core/__init__.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/bundle_io.py`, `core/script_codec.py`.

### S15 — Select Box Both Views + Reserved Lock Slot, Collapsible Left Drawer, Empty State & Batched Multi-Open
- **Session Scope:** BUG-41, FEAT-05, FEAT-06, FEAT-07 (Track 2 · Group G2 (post-DEP-4, DEP-9)).
- **BUG-41 & FEAT-05 (`misora.py` — U-B11, U-B12, U-B29):**
  - Enabled `Select Box` mode in Dialogue view with inline header checkbutton (`cb_dialogue_select`: `Select Box #N (X selected)`), synced across box navigation, Copy/Cut operations, and view switches.
  - Restored Box 0 (`-1`) Select Box checkbutton on Card #0 (`hdr_0`) in All Script view.
  - Enclosed per-card Select Box checkbuttons inside a fixed-width `slot_cb` container (`width=22`, `pack_propagate(False)`) and relocated the Translation Lock indicator (`lbl_lock`, fixed `width=2`, clickable to toggle lock) immediately to the right of `slot_cb`, eliminating horizontal header shifting when toggling `Select Box` mode or Translation Lock.
- **FEAT-06 (`misora.py` — U-B15):**
  - Extended `_toggle_dock_collapse()` into a clean pane-based collapsible left drawer inside `h_paned` (zero `place()` overlays): hides tab buttons and body frames on collapse, places expand toggle (`▶`) cleanly at `x < 36` within the collapsed width, and restores tabs and content on expand.
- **FEAT-07 (`misora.py` — U-B16, U-B19, U-B20):**
  - Added `empty_state_frame` with centered `"📂 Open Files"` button and drag-and-drop workspace hint shown when 0 documents are open and auto-hidden when >=1 document is opened.
  - Bound `<Double-Button-1>` on `btn_tab_files` (`Opened Files` tab) to `on_open_file()`.
  - Updated `on_open_file()` to `filedialog.askopenfilenames()`, preserving S1 staged semantics and performing ONE batched UI refresh (`_update_views()`) at the end.
- **Test Suite:** Added `tests/test_p3_s15_selection_drawer_open.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing).
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s15_selection_drawer_open.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/*.py`.

### S14 — Search Bar 5-Col Grid, Hide Current Dir, Player Icon/No `[-]`, VIEW Group, Toggle NGUI Ribbon & `Raw Commands`
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
- **Test Suite:** Added `tests/test_p3_s14_toolbar_search_ui.py` with 4 Defect Probes (failing-first) and 1 Regression Guard (passing).
- **Files Modified:** `misora.py`, `README.md`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s14_toolbar_search_ui.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/splash.py`.

### S13 — Continuous Ribbon/Size/Dirty Sync, Shortcut Conflicts, Complete Tooltips & `Ctrl+H` Hygiene
- **Session Scope:** BUG-28, BUG-29, HYG-03, HYG-07 (Track 1 · Group F3 (DEP-3 — Completes all non-fixture Track 1 P0/P1 bugs)).
- **Milestone Note:** **Track 1 Automated Stabilization Gate (S01..S13) COMPLETE** (unlocks Track 2 `S14..S23` and `AGENTS.md` §24 MTL Drawer gate).
- **Production Fixture Status:** Real production `.unity3d` verification for `BUG-09` remains explicitly `BLOCKED` (synthetic bundle test passed in S03; real proprietary production fixture `storydata_1001005.unity3d` intentionally excluded from repository).
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
- **Test Suite:** Added `tests/test_p3_s13_ribbon_shortcuts.py` with 3 Defect Probes (failing-first) and 1 Regression Guard (passing). Full test suite discovered count: 308 tests across 35 modules (268 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s13_ribbon_shortcuts.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/*.py`, `assets/*.py`.

### S12 — Logger Flush Barrier/Teardown, DPAPI Fail-Closed, Reload Env Disposal, Deferred Startup & Splash Safety
- **Session Scope:** BUG-32, BUG-33, BUG-34, BUG-35, BUG-36 (Track 1 · Group F2 (DEP-9 part 1 — Split from Ribbon per Grok R2)).
- **BUG-32 (`core/logger.py`, `misora.py`):**
  - Replaced `queue.empty()` polling in `MisoraLogger.flush()` with a true completion barrier using `_file_queue.all_tasks_done` / `unfinished_tasks` and `time.monotonic()` deadline wait, ensuring `clear_log_file()` never races an in-flight background disk write.
  - Placed `_file_queue.task_done()` inside a `finally:` block around `_write_entry_to_file(entry)` in `_file_writer_loop()` so disk I/O exceptions cannot deadlock `flush()`.
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
- **Test Suite:** Added `tests/test_p3_s12_lifecycle_security.py` with 5 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 304 tests across 34 modules (264 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `assets/splash.py`, `core/logger.py`, `core/security.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s12_lifecycle_security.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/script_codec.py`, `core/search_engine.py`, ribbon/shortcuts/tooltips.

### S11 — Main-Thread Queue-Only Async MTL, Stale-Result Identity Guard & Safe Batch Cancel
- **Session Scope:** BUG-14, BUG-27 (Track 1 · Group F1 (DEP-6 — Split from XUAT per Grok R1)).
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
- **Test Suite:** Added `tests/test_p3_s11_mtl_threading.py` with 7 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 297 tests across 33 modules (257 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/mtl_engine.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s11_mtl_threading.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/xunity_sync.py`, `core/story_ast.py`, `core/security.py`, `core/logger.py`.

### S10 — Immutable box.uid XUAT JP Keys, Save Conflict Preview Gate & Atomic XUAT Dictionary Writes
- **Session Scope:** BUG-25, BUG-26 (Track 1 · Group E (DEP-7 part 2 — Split from MTL per Grok R1)).
- **BUG-25 (`misora.py`, `core/xunity_sync.py`):**
  - Registered immutable Japanese source keys by `box.uid` backed by per-document `_original_jp_by_uid` and `XUnitySyncManager.register_jp_key()`/`get_jp_key()`; updated `open_file()` to populate both caches upon story load and eliminated fallback to current/edited English text.
  - Eliminated the destructive English overwrite in `on_save()` (`self._original_box_texts[b_idx] = box_obj.clean_text`), guaranteeing repeated saves of the same box (`EN1 -> EN2`) continue matching the immutable original Japanese source key across edits and structural mutations.
  - Implemented shared helper `_sync_modified_boxes_to_xuat()` used across both `on_save()` and `_save_document_entry()`: strictly resolves immutable JP keys by `b_uid` without positional fallback when `b_uid is not None`, checks `preview_matches()`, and prompts the user via `messagebox.askyesno` ONLY when genuine `is_conflict=True` duplicate translations exist in the XUAT dictionary file, proceeding without modal friction on clean matches.
  - In `core/xunity_sync.py`, updated `register_jp_key()` and `get_jp_key()` to support `Optional[int]` box UIDs, added `has_jp_key()`, `clear_jp_keys()`, and `register_jp_keys()`, ensured `preview_matches()` propagates `is_conflict`, and added empty-key guards.
- **BUG-26 (`core/xunity_sync.py:find_and_update()`):**
  - Replaced non-unique `f'{tf.name}.{os.getpid()}.tmp'` and bare `os.replace` in `find_and_update()` with `core.text_encoding.write_atomic_encoded()`.
  - Preserves UTF-8 BOM, encoding, and exact CRLF/LF line endings without double newlines, backed by bounded 5-attempt retry loop for Windows sharing violations.
- **Test Suite:** Added `tests/test_p3_s10_xuat_integrity.py` with 2 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 288 tests across 32 modules (248 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/xunity_sync.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s10_xuat_integrity.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/search_engine.py`, `core/mtl_engine.py`, `core/bundle_io.py`.

### S09 — Multi-File Replace-All Cache Keys/Shared Matcher/Closed-File Undo & Collision-Resistant Backups
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
- **Test Suite:** Added `tests/test_p3_s09_replace_all_backups.py` with 7 Defect Probes and 2 Regression Guards. Full test suite discovered count: 284 tests across 31 modules (244 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s09_replace_all_backups.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/story_ast.py`, `core/search_engine.py`, `core/xunity_sync.py`, `core/mtl_engine.py`, `core/bundle_io.py`.

### S08 — Search Match-Case/Errors/Snapshots/Spans, Bounded Project Roots & Search Focus/Gutter/No-Op KeyRelease
- **Session Scope:** BUG-21, BUG-22, BUG-23, BUG-30 (Track 1 · Group D1 (DEP-7 part 1)).
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
- **Test Suite:** Added `tests/test_p3_s08_search_roots_focus.py` with 4 Defect Probes (failing-first) and 2 lightweight Regression Guards (passing). Full test suite discovered count: 275 tests across 30 modules (235 pass, 35 skipped, 3 failures, 2 errors due to intentionally excluded root fixture `storydata_1001005.unity3d`).
- **Files Modified:** `core/story_ast.py`, `core/search_engine.py`, `misora.py`, `CHANGELOG.md`, `PROJECT_STATE.md`.
- **Files Created:** `tests/test_p3_s08_search_roots_focus.py`.
- **Forbidden Files Untouched:** `__init__.py` (`__version__ = "1.4.0"` untouched), `core/xunity_sync.py`, `core/mtl_engine.py`, `core/script_codec.py`, `misora.py:on_replace_all`/`_apply_delta`.

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
