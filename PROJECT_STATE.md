# Misora Editor — Canonical Project State

Last updated: 2026-11-21
Repository: `ImaterialC/Misora-Editor`
Local working path: `D:\Misora-Editor`
Target release: v1.4.0
Current code baseline: root `__init__.py` reports `version = "1.1.0"`; UI labels drift.

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
UnityPy Availability: MISSING (ModuleNotFoundError: No module named 'unitypy') — Environment blocker for bundle operations
Pillow Availability: Available
Fixture Availability: storydata_1001005.unity3d present in repository root (39 dialogue boxes)

Compile Check:
py -3.12 -m compileall -q misora.py core assets tests
Result: PASS (Exit code 0, 0 syntax/compilation errors)

Unit Test Suite:
py -3.12 -m unittest discover -s tests -v
Result: Ran 38 tests in 28.601s — FAILED (failures=4, errors=1)
```

### Baseline Test Failures
1. `test_11_ribbon_compact_buttons_and_undo_redo` (FAIL): Ribbon undo button has no text fallback (`'' != '↶'`).
2. `test_14_box0_metadata_navigation_and_ui` (FAIL): `var_box0_title` unpopulated due to `"continuous_view": true` leaked from committed `misora_config.json`.
3. `test_15_box0_metadata_editing_and_undo_redo` (FAIL): Box 0 undo/redo test fails due to `"continuous_view": true` config leak.
4. `test_21_plain_text_editing_and_save_continuous_and_page` (FAIL): Plain-text page edit dropped on save because `misora_config.json` forces Continuous View routing in `on_save()`.
5. `test_22_single_root_splash_speaker_and_continuous_binding` (ERROR): `TclError: image "pyimage555" doesn't exist` when second `MisoraApp` is created in test runner.

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
| **AST-INDEX-SHIFT** | CONFIRMED | `core/story_ast.py:279, 288` | `set_metadata` inserts records without rebasing `Seg.rec_index`. Later `inject_box` writes to shifted, wrong records. Replace with `Seg.record` reference. | 1 |
| **BOX-STRUCTURAL-OPS** | CONFIRMED | `misora.py:6280, 6282, 6348`; `core/story_ast.py:181` | `Box.clean_text` is read-only `@property`. Constructing `Box(clean_text=...)` raises `TypeError`. GUI ops mutate `doc.boxes` while serializer writes `doc.records`. Add document-level AST structural APIs. | 1 |
| **BOX-PASTE-DEAD** | CONFIRMED ON MACHINE | `misora.py:6219, 6255, 6289, 6297-6298` | Release blocker. `_push_undo`, `_sync_clean_view_to_current_box`, and `_dirty_state_changed` are undefined. Paste Box fails silently via `report_callback_exception`. Implement missing helpers. | 2 |
| **BUNDLE-SAVE-WRITES-BEFORE-VERIFY** | CONFIRMED | `core/bundle_io.py:117-128` | Direct overwrite of destination bundle before reload/verify. Target destroyed if save or verification crashes. Implement same-directory `.tmp` staging + verification + `os.replace`. | 1 |
| **BOX0-SAVE-CORRUPTION** | CONFIRMED | `misora.py:7066-7080` | `on_save()` calls `inject_box` unconditionally. When Box 0 is active, `speaker_var` is empty and dialogue is stale, corrupting active box. Add dedicated Box 0 flush path. | 2 |
| **V2-ROUNDTRIP-LOSS** | CONFIRMED | `core/story_ast.py:56, 155, 401, 404-405` | `cmd_32` mapped to 0; categories discarded; duplicate commands collapsed in `_INV_CMD_MAP`. Preserve numeric IDs, categories, and Unicode line separators. | 1 |
| **XUAT-SYNC-LINE-CORRUPTION** | CONFIRMED | `core/xunity_sync.py:65, 86, 102` | Multiline translations split into orphan physical lines; `errors="replace"` on read; BOM/CRLF lost. Enforce strict decoding, escape `\n` in values, preserve BOM/CRLF. | 1 |
| **EMPTY-ARG-ARITY** | CONFIRMED | `core/story_ast.py:319, 368-369` | `to_binary` skips `a == ""`; `inject_box(fill="")` alters record arity and crashes engine. Retain empty args in binary or prohibit empty filler. | 1 |
| **NARRATION-EMPTY-PHANTOM** | CONFIRMED | `core/story_ast.py:224-229, 238`; `misora.py:6840` | Narration emits `print` with empty speaker, reloading text into speaker slot. Convert narration to `tag` records per Rule 7. | 1 |
| **PAGE-BREAK-NOT-SPLIT** | CONFIRMED | `core/story_ast.py:31, 52` | `DEFAULT_BREAKERS` has `"page"` while `_CMD_MAP` defines `"next_page"`. Page breaks never split boxes. Align breaker tokens. | 1 |
| **RAW-TAIL-FROZEN** | CONFIRMED | `core/story_ast.py:317-324` | `inject_box` updates `seg.text` but not `seg.raw`. `Box.raw` returns stale parse snapshot. Update `seg.raw` alongside `seg.text`. | 1 |
| **CMD0-SPECIAL-CASE** | CONFIRMED | `core/story_ast.py:365` | `to_binary` special case remaps cmd 0 to cmd 15/30 on relabeling. Remove special case before modifying command mappings. | 1 |
| **SHORTCUT-BINDTAG-ORDER** | CONFIRMED ON MACHINE | `misora.py:5566-5599` | Release blocker. Standard Tk `Text` class bindings execute before root `bind_all`. Ctrl+H deletes text before replace dialog opens. Install first-position `MisoraShortcuts` bindtag. | 2 |
| **RIBBON-CUT-PASTE-NO-COMMIT** | CONFIRMED ON MACHINE | `misora.py:6181, 6204` | Release blocker. Virtual `<<Cut>>`/`<<Paste>>` produces no `<KeyRelease>`, bypassing edit commit. Text reverts on navigation. Explicitly call commit in virtual event handlers. | 2 |
| **MULTI-TEXTASSET-TARGET** | CONFIRMED | `core/bundle_io.py:67-69, 121-126` | Asset loading selects last matching TextAsset without locking `path_id`. Save verification matches any asset. Lock target by `path_id`. | 1 |
| **INJECT-EXTRA-ARGS** | CONFIRMED | `core/story_ast.py:321-323` | `inject_box` replaces `rec.args` wholesale, permanently discarding extra args in 3+ argument commands. Preserve unmanaged trailing args. | 1 |

### P1 — Functional, UI, & Security Issues (Phases 2, 3, 5)

| Slug | Status | File & Line Evidence | Impact & Resolution | Phase |
|---|---|---|---|---|
| **DIRTY-EXIT-DROPS-EDITS** | CONFIRMED | `misora.py:1192, 1268-1274, 5570` | Window close (`WM_DELETE_WINDOW`) and Ctrl+Q exit immediately without prompting for dirty files. Add Save/Discard/Cancel flow. | 2 |
| **RELOAD-REVERT-HIT-CACHE** | CONFIRMED | `misora.py:5624, 7030, 7142` | `on_revert_box` and `on_reload` call `open_file` without `reload_from_disk=True`, returning in-memory cached document. Pass flag. | 2 |
| **REPLACE-ALL-BUNDLE-PREFILTER** | CONFIRMED | `misora.py:7881-7883` | Raw byte scan on binary bundles yields false hits/misses. Decode structured text assets before searching. | 2 |
| **REPLACE-ALL-UNDO-GAP** | CONFIRMED | `misora.py:7919-7952` | Bundle changes in multi-file Replace All are omitted from `per_file_deltas` and cannot be undone. Journal all modified bundles. | 2 |
| **TLS-VERIFICATION-DISABLED** | CONFIRMED | `core/mtl_engine.py:142-144` | Outbound HTTPS requests set `check_hostname=False` and `verify_mode=CERT_NONE`. Enforce valid certificate verification. | 5 |
| **API-KEYS-PLAINTEXT** | CONFIRMED | `core/mtl_engine.py:52-70`; `misora.py:1439` | API keys serialized in plaintext JSON config. Migrate to OS credential storage (DPAPI/Keyring). | 5 |
| **TAGMASKER-INCOMPLETE** | CONFIRMED | `core/mtl_engine.py:98-106` | Size, color/gradient, and numbered placeholders unshielded; lacks `re.DOTALL` for multiline ruby. Create centralized `core/ngui_tags.py`. | 5 |
| **SIZE-RIBBON-NO-COMMIT** | CONFIRMED | `misora.py:6374-6394` | Font size insertion edits widget directly without calling edit commit or updating dirty state. Route through central commit. | 2 |
| **CONTINUOUS-RIBBON-TARGET-STALE** | CONFIRMED | `misora.py:5241, 5281, 6005-6017, 6681` | Clicking a card does not reassign `txt_continuous`; index closures desync. Resolve active card dynamically. | 2 |
| **UNDO-STORM** | CONFIRMED | `misora.py:7970-8036` | Batch undo destroys and recreates all Card widgets for every single delta. Apply batch to model first, refresh UI once in `finally`. | 2 |
| **SEARCH-RACE** | CONFIRMED | `misora.py:7212-7218` | Search worker thread accesses live mutable `StoryDocument` references concurrently with UI edits. Pass immutable snapshots. | 2 |
| **CLIP-SHADOW** | CONFIRMED (Latent) | `misora.py:6274-6284` | Internal box clipboard permanently shadows OS clipboard until restart. Check OS clipboard freshness on paste. | 2 |
| **FOLDER-DROP-EXTRA-IGNORED** | CONFIRMED | `misora.py:2189-2190` | Only the first folder in multi-folder DnD drops is opened; remainder ignored silently. Warn user or process all. | 2 |
| **DEEPL-TEST-COST** | CONFIRMED | `core/mtl_engine.py:332-342` | Connection test queries billable `/v2/translate` instead of free `/v2/usage`. | 5 |
| **CORE-IMPORT-COUPLING** | CONFIRMED | `core/__init__.py:5`; `core/bundle_io.py:15` | Importing `core` drags in `UnityPy` at module level, breaking standalone AST usage. Lazy-load `bundle_io` / `UnityPy`. | 3 |
| **CONFIG-RECOVERY-OVERWRITE** | CONFIRMED | `misora.py:1397-1398, 1452` | Corrupted config overwritten with defaults on exit without saving a `.bak` recovery copy. Preserve recovery copy before loading defaults. | 3 |
| **STALE-CARD-REGISTRY** | CONFIRMED | `misora.py:6405-6419, 6436` | Switching to plain text returns before clearing `_card_widgets`, leaving destroyed widgets registered. Clean up cards before return. | 2 |
| **GRADIENT-COMMA-EMITTER** | CONFIRMED | `misora.py:857, 1010, 4518` | Gradient insertion emits comma syntax `[c0,c1]` instead of hyphen syntax `[c0-c1]`. Emit hyphen syntax per Rule 19. | 2 |
| **SPAN-NFKC-PER-CHAR** | CONFIRMED | `core/search_engine.py:88` | Per-token NFKC fails to compose Japanese dakuten/handakuten combining characters. Align with whole-string normalization. | 2 |
| **UNDO-COALESCE-CROSS-SOURCE** | CONFIRMED | `core/undo_journal.py:115-130` | Coalescing checks only box and timing, merging ribbon cuts with typing. Add source tracking to deltas. | 2 |
| **GENERIC-PLACEHOLDER-GAP** | CONFIRMED | `misora.py:4710-4713`; `core/mtl_engine.py:100` | Placeholders `{1}`, `{2}`, etc. unshielded in translation and unhighlighted in preview. Support all `{n}` placeholders. | 5 |
| **LOGGER-SYNC-IO** | CONFIRMED | `core/logger.py:110-145` | Synchronous disk I/O and `flush=True` on UI thread under lock. Move file writes to background writer queue. | 3 |
| **BULK-DELTA-NONATOMIC** | CONFIRMED | `misora.py:8040-8060` | Reverting bulk file undo writes files directly without `.tmp` atomic replacement. Wrap in atomic file replace helper. | 2 |
| **HARDCODED-PROJECT-PATH** | CONFIRMED | `misora_config.json:36-37, 40-41` | Machine-specific paths and user session flags (`continuous_view: true`) committed in repo, breaking tests. Clean committed config. | 3 |
| **PLAINTEXT-SAVE-ROUTING** | CONFIRMED | `misora.py:7052` | `on_save()` reads from `txt_continuous` when `continuous_view` is true, ignoring Page View edits. Route save based on active view. | 2 |

### P2 — Performance, QoL, & Measured Risks (Phases 3, 4, 5)

| Slug | Status | Note | Phase |
|---|---|---|---|
| **THEME-RAW-PERF** | MEASURED | 1 file (142 boxes) = 160MB RAM; 135 files test showed workable switching on i7-13700KF. Benchmark lower-spec targets. | 3 |
| **SEARCH-CACHE** | DESIGN | LRU keyed by path/mtime/size; must include metadata. | 3 |
| **ICON-CACHE-GROWTH** | CONFIRMED LOW | Cache keyed per toplevel; clear/bound it. | 3 |
| **OFFSCREEN-GEOMETRY** | CONFIRMED | Validate saved geometry against virtual screen. | 3 |
| **TOOLTIP-LIFECYCLE** | DESIGN | Delayed tooltip must cancel timers and check existence. | 4 |
| **GAME-BOX-PREVIEW** | DESIGN | Crucial for non-NGUI dialogue scenes where text overflows rather than wrapping automatically. | 5 |
| **TRANSLATION-LOCK** | DESIGN | Protect proofread boxes from batch/paste/replace. | 2 |
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
- [ ] Replace `Seg.rec_index` with `Seg.record`; add runtime Record uid; rebuild projection after mutations.
- [ ] Add structural AST mutation APIs: `insert_box`, `delete_box`, `move_box`, `clone_box` with `BoxSnapshot`.
- [ ] Preserve unmanaged extra args in `inject_box` and `set_metadata`.
- [ ] Fix empty-arg arity dropping in `to_binary`; convert narration to `tag` records.
- [ ] Fix raw tail freshness (`seg.raw`) and page-break splitting (`next_page` breaker token).
- [ ] Make v2 text lossless: preserve `cmd_32`, category, duplicate commands, and line breaks.
- [ ] Remove `cmd_id == 0` special case in `to_binary`.
- [ ] Implement atomic same-directory `.tmp` save with target `path_id` verification, fingerprint check, and bounded retry.
- [ ] Enforce strict XUAT encoding, escape newlines in values, preserve BOM and CRLF.
- [ ] Add regression test suite for AST structural mutations and bundle round-trip.

### Phase 2 — GUI Integrity, Central Commit, Shortcuts, Undo & CSIF Codec
Scope: `misora.py`, new `core/script_codec.py`, `core/search_engine.py` (snapshots), tests.
Non-goals: Importer registry (Phase 4), startup optimization (Phase 3), MTL drawer (Phase 5).

Tasks:
- [ ] Implement pure `core/script_codec.py` (CSIF v1): `@@Speaker`, `@@_`, `@@!meta`, sparse addressing.
- [ ] Implement shared `_commit_widget_edit` path for keyboard, ribbon, cut/paste, and font size.
- [ ] Fix Box 0 flush/save path; prevent dialogue injection while Box 0 is active.
- [ ] Fix plain-text view routing in `on_save()`.
- [ ] Remove widget aliasing; resolve active card dynamically.
- [ ] Install first-position `MisoraShortcuts` bindtag router on all text/entry widgets.
- [ ] Fix missing `_push_undo`, `_sync_clean_view_to_current_box`, and `_dirty_state_changed` helpers.
- [ ] Batch undo: apply all deltas to model first, refresh UI once in `finally`.
- [ ] Pass immutable snapshots to background search workers; protect Replace All bundle changes in undo.
- [ ] Add Save/Discard/Cancel prompts on dirty close and app exit; add `reload_from_disk=True` to revert.
- [ ] Fix gradient comma emitter to emit hyphen syntax.

### Phase 3 — Startup Performance & Configuration Safety
Scope: `misora.bat`, `misora.py` bootstrap, `assets/splash.py`, `core/bundle_io.py` lazy import, `core/logger.py`, tests.

Tasks:
- [ ] Remove `UnityPy` probe loops from `misora.bat`.
- [ ] Lazy-load `bundle_io` and `UnityPy` under lock; decouple `core/__init__.py`.
- [ ] Maintain single-process architecture for splash.
- [ ] Defer session restore until root window is displayed.
- [ ] Preserve corrupt config recovery copy (`.bak`) before falling back to defaults.
- [ ] Clean machine-specific paths from repository `misora_config.json`.
- [ ] Move logger file writes and flushes to background queue.

### Phase 4 — Import/Export, Paste Preview, & UI Polish
Scope: `misora.py`, root `__init__.py`, `assets/splash.py` (version source), tests.

Tasks:
- [ ] File Import/Export menus for CSIF interchange.
- [ ] Upgrade paste confirmation into full Paste Preview dialog.
- [ ] Remove redundant ribbon buttons; unify version string to root `__version__`.
- [ ] Add safe tooltip lifecycle management with `winfo_exists` checks.

### Phase 5 — Shared NGUI, MTL Engine, & Preview Safety
Scope: `core/ngui_tags.py`, `core/mtl_engine.py`, `misora.py`, tests.

Tasks:
- [ ] Create central `core/ngui_tags.py` with complete tag patterns, size, ruby, and hyphen gradients.
- [ ] Enable TLS certificate verification on all outbound requests; store API keys in DPAPI/keyring.
- [ ] Use DeepL `/v2/usage` status endpoint for connection test.
- [ ] Implement Game Box Preview with rendered text overflow measurement.
- [ ] Add Translation Lock protection for proofread boxes.

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
