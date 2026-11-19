# Misora Editor — Canonical Project State

Last updated: 2026-11-20
Repository: `ImaterialC/Misora-Editor`
Local working path: `D:\Misora-Editor`
Target release: v1.4.0
Current code baseline: root `__init__.py` reports `version = "1.1.0"`; UI labels still drift.

This file is the single canonical journal. It replaces legacy roadmap variants.
Historical B1–B20 progress is preserved below, but older root-cause claims are corrected
against the current source snapshot and the independent audit.

---

## 1. How to use this document

1. Read `AGENTS.md` for permanent invariants.
2. Use the defect ledger below as the audit baseline.
3. Use stable slugs, not new B-numbers.
4. Classify every claim as:
   - CONFIRMED: proven from current code or a minimal repro.
   - CONDITIONAL: requires real bundle / Windows Tk / fixture evidence.
   - DESIGN INVARIANT: rule for a feature not yet built.
   - RETRACTED: withdrawn claim; do not hunt it again.
5. Do not implement features before Phase 1–2 integrity gates pass.
6. Record test baseline dynamically. Do not assume 38/38.

---

## 2. Historical baseline B1–B20 (preserved, corrected)

| ID | Area | Historical status | Canonical note |
|----|------|-------------------|----------------|
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
| B16 | Plain text save/backups | RESOLVED historically | Plain-text save fallthrough still defective; see PLAINTEXT-SAVE-FALLTHROUGH. |
| B17 | Cross-box paste | RESOLVED historically | Legacy delimiter paste is fragile; CSIF replaces it later. |
| B18 | Box Card Stream | RESOLVED | Keep card architecture; fix aliasing and commit paths. |
| B19 | Triple-enter workflow | RESOLVED historically | Superseded by CSIF; keep legacy input only. |
| B20 | Speaker dropdown / Box 0 protection | RESOLVED | Narration must convert record kind, not blank a print speaker. |

---

## 3. Superseded roadmap claims

Do not execute these older directions:

| Old claim | Final decision |
|---|---|
| `core/script_exchange.py` with `{{meta}}/{{speaker}}` | Superseded by `core/script_codec.py` with CSIF `@@` headers. |
| `{{speaker}}` / `{{{0}}}` format | Rejected: brace nesting and EOF fragility. |
| Out-of-process splash subprocess | Rejected: single-process bootstrap. |
| “Fast Mode / Planning Mode” as commands | Not real Antigravity commands. Use `/plan`, `/goal`, or direct instructions. |
| `.agent/` as the primary customization path | Use `AGENTS.md` and `.agents/` conventions; verify local surface. |
| `inject_box` does not update `clean_text` | Incorrect. `clean_text` derives from `seg.text`; real defects are identity/structural/Box0/silent failures. |
| App already v1.4.0 | Incorrect. v1.4.0 is the target. |
| Fixed 38/38 test baseline | Must be measured dynamically. |

---

## 4. Current defect ledger

### P0 — data integrity blockers

| Slug | Status | Evidence / impact | Phase |
|---|---|---|---|
| AST-INDEX-SHIFT | CONFIRMED | `set_metadata` inserts records without rebasing `Seg.rec_index`; later `inject_box` writes the wrong record. | 1 |
| BOX-STRUCTURAL-OPS | CONFIRMED | `Box(clean_text=...)` invalid; undefined helpers; handlers mutate only `doc.boxes` while serializer writes `doc.records`. | 1 |
| BUNDLE-SAVE-WRITES-BEFORE-VERIFY | CONFIRMED | Destination written before verification; verification accepts any matching TextAsset. | 1 |
| BOX0-SAVE-CORRUPTION | CONFIRMED | Box 0 flush incomplete; `on_save` can inject stale dialogue/empty speaker into active box. | 2 |
| V2-ROUNDTRIP-LOSS | CONFIRMED | `cmd_32` becomes 0; category lost; duplicate command names collapse; whitespace/exotic separators unsafe. | 1 |
| XUAT-SYNC-LINE-CORRUPTION | CONFIRMED | Multiline translation becomes orphan physical dictionary lines; whitespace/encoding rewritten. | 1 |
| EMPTY-ARG-ARITY | CONFIRMED | `to_binary` skips empty args; `inject_box(fill="")` changes record arity. | 1 |
| NARRATION-EMPTY-PHANTOM | CONFIRMED | Empty speaker on `print` makes text reload as speaker; empty `tag` can create phantom box. | 1 |
| PLAINTEXT-SAVE-FALLTHROUGH | CONFIRMED | Successful plain-text save falls through into `current_doc` branches. | 2 |
| PAGE-BREAK-NOT-SPLIT | CONFIRMED | `DEFAULT_BREAKERS` has `page`, but map defines `next_page`; same-speaker pages merge. | 1 |
| RAW-TAIL-FROZEN | CONFIRMED | `seg.raw` never updated; trailing break restored/stripped from frozen snapshot. | 1 |
| CMD0-SPECIAL-CASE | CONFIRMED | Relabeling cmd 0 while `to_binary` special case exists rewrites cmd 0 as cmd 30. | 1 |
| BOX-PASTE-DEAD | CONFIRMED ON MACHINE | `_push_undo` is called by on_box_paste / on_box_cut / _on_card_paste_caret but never defined; on_box_new also calls `Box(clean_text=...)` which is a read-only property. report_callback_exception only logs, so every failure is a silent no-op. Copy Box works because it calls no missing helper. Even with the helpers added, mutating only doc.boxes cannot persist because to_binary serializes doc.records. | 1 |
| CSIF-BOX-CLIPBOARD | FEATURE (user request) | Copy Box currently emits bare triple-enter with no speaker or identity. Adopt CSIF for the box clipboard so any payload carrying `@@` headers is recognized and round-trips across programs. Insert mode for Paste Box, replace mode for Paste Script, ask mode for plain Ctrl+V. | 2 |

### P1 — serious functional / security issues

| Slug | Status | Evidence / impact | Phase |
|---|---|---|---|
| DIRTY-EXIT-DROPS-EDITS | CONFIRMED | Window close does not prompt for dirty documents. | 2 |
| RELOAD-REVERT-HIT-CACHE | CONFIRMED | Reload/Revert call `open_file` without `reload_from_disk=True`. | 2 |
| REPLACE-ALL-BUNDLE-PREFILTER | CONFIRMED | Raw UTF-8 prefilter cannot see encoded bundle text. | 2 |
| REPLACE-ALL-UNDO-GAP | CONFIRMED | Bundle replacements not recorded in undo; bulk text undo non-atomic. | 2 |
| INJECT-EXTRA-ARGS | CONDITIONAL | Code replaces full args; real 3+ arg fixtures required to define schema preservation. | 1 |
| TLS-VERIFICATION-DISABLED | CONFIRMED | `CERT_NONE` used for DeepL/LLM requests carrying keys. | 5 |
| API-KEYS-PLAINTEXT | CONFIRMED | Keys serialized into ordinary config. | 5 |
| TAGMASKER-INCOMPLETE | CONFIRMED | Size tags unmasked; multiline ruby pair not protected; color/gradient gaps. | 5 |
| SIZE-RIBBON-NO-COMMIT | CONFIRMED | Size insertion mutates widget without model commit. | 2 |
| CONTINUOUS-RIBBON-TARGET-STALE | CONFIRMED | Alias/index shim can target wrong card. | 2 |
| TRANSLATOR-SOURCE-SEED | CONFIRMED | Assistant seeds target pane with source text; Apply can overwrite EN with JP. | 2 |
| UNDO-STORM | CONFIRMED | Per-delta full view rebuild inside batch undo. | 2 |
| SEARCH-RACE | CONFIRMED | Worker receives live mutable document references. | 2 |
| CLIP-SHADOW | LATENT (unreachable until BOX-PASTE-DEAD is fixed) | Internal box clipboard always wins over newer system clipboard. | 2 |
| FOLDER-DROP-EXTRA-IGNORED | CONFIRMED | Only first dropped folder processed. | 2 |
| FOLDER-TXT-CLASSIFICATION | CONDITIONAL | Folder scanner treats every `.txt` as story; impact depends on folder convention. | 2 |
| DEEPL-TEST-COST | CONFIRMED | Connection test calls translation endpoint. | 5 |
| CORE-IMPORT-COUPLING | CONFIRMED | Importing pure AST pulls UnityPy through `core/__init__`. | 3 |
| CONFIG-RECOVERY-OVERWRITE | CONFIRMED | Parse-failed config can be overwritten by defaults on exit. | 3 |
| STALE-CARD-REGISTRY | CONFIRMED | Plain-text render path can leave destroyed card widgets registered. | 2 |
| SHORTCUT-BINDTAG-ORDER | CONFIRMED ON MACHINE (P0) | Root/bind_all shortcuts run after Tk Text class bindings; Ctrl+O/T/H can mutate buffer. | 2 |
| RIBBON-CUT-PASTE-NO-COMMIT | CONFIRMED ON MACHINE (P0) | Virtual Cut/Paste may bypass KeyRelease commit. Verify interactively. | 2 |
| GRADIENT-COMMA-EMITTER | CONFIRMED | Glossary says hyphen required; ribbon/picker emit comma. | 2 |
| MULTI-TEXTASSET-TARGET | CONFIRMED | Last story-like TextAsset can win; no path_id lock. | 1 |
| TEXTASSET-STR-DECODE-FIDELITY | CONDITIONAL | Must verify UnityPy str decode error handler against raw bytes. | 1 |
| SPAN-NFKC-PER-CHAR | CONFIRMED | Span normalizer applies NFKC per token/char, diverging from whole-string `norm_search`. | 2 |
| UNDO-COALESCE-CROSS-SOURCE | CONFIRMED | Coalescing ignores source and refreshes timestamp indefinitely. | 2 |
| GENERIC-PLACEHOLDER-GAP | CONFIRMED | `{1}` highlighted but not masked/compiled like `{0}`. | 5 |
| LOGGER-SYNC-IO | CONFIRMED | File write and stdout flush occur synchronously under lock. | 3 |
| BULK-DELTA-NONATOMIC | CONFIRMED | Bulk undo writes files without tmp/backup. | 2 |
| HARDCODED-PROJECT-PATH | CONFIRMED | Machine-specific path enters default search/replace roots. | 3 |

### P2 — performance / QoL / measured risks

| Slug | Status | Note | Phase |
|---|---|---|---|
| THEME-RAW-PERF | MEASURE FIRST | Benchmark 50/150/300 boxes before virtualization. | 3 |
| SEARCH-CACHE | DESIGN | LRU keyed by path/mtime/size; must include metadata. | 3 |
| ICON-CACHE-GROWTH | CONFIRMED LOW | Cache keyed per toplevel; clear/bound it. | 3 |
| OFFSCREEN-GEOMETRY | CONFIRMED | Validate saved geometry against virtual screen. | 3 |
| TOOLTIP-LIFECYCLE | DESIGN | Delayed tooltip must cancel timers and check existence. | 4 |
| GAME-BOX-PREVIEW | DESIGN | Needed for faithful display simulation and measured overflow. | 5 |
| TRANSLATION-LOCK | DESIGN | Protect proofread boxes from batch/paste/replace. | 2 |
| PROMPT-STUDIO | DESIGN | Upgrade existing prompt dialog; token budget; templates. | 5 |
| TERMBASE / TM | DESIGN | TM = XUAT cache index; provenance sidecar only. | 5 |
| XUAT2RAW | DESIGN | Adapter stub only until tool output spec exists. | 4 |

---

## 5. Retracted claims

Do not spend time hunting these as current bugs:

| Claim | Final status |
|---|---|
| Double paste dispatch B30 | NOT PRESENT: `"break"` prevents double handling. |
| Span drift for literal `\n` B135 | NOT PRESENT: tokenizer already handles escaped `\n`. The real issue is SPAN-NFKC-PER-CHAR. |
| Lowercase hex rejected | NOT PRESENT: patterns already accept a-f and lower-case tokens. |
| `translate_async` location breaks import | NOT PRESENT: module-level function. |
| Uploaded config JSON is malformed | RETRACTED as paste artifact. CONFIG-RECOVERY-OVERWRITE remains valid. |
| SEG-TARGET-STALE as bug | DESIGN INVARIANT until fixture proves otherwise. |
| `choice` misclassified as speaker | NOT PRESENT: choice records remain unprojected. Future support is a feature question. |
| Minimum XUAT key length block | REJECTED: short Japanese lines are valid. Use duplicate/conflict preview. |
| Ctrl+Y is universally yank | RETRACTED: platform/Tk dependent. Bindtag router makes it moot. |
| Immediate `Box.__deepcopy__` TypeError | REJECTED until Copy/Paste migrated to snapshot API. |
| Insecure TLS checkbox | REJECTED: fix CA trust, not bypass. |
| `Seg.rec_index` as property/cache | REJECTED: migrate the few call sites to `Seg.record`; no dual state. |
| `[-]` as default empty fill | REJECTED as default: pollutes clean_text/CSIF/search/XUAT. Test only as candidate. |

---

## 6. Design invariants for future features

| ID | Invariant |
|----|-----------|
| D1 | CSIF export uses `@@Speaker`, `@@_` narration, `@@!title/@@!subtitle/@@!summary`. |
| D2 | Sparse CSIF uses 1-based `@@#N|Speaker`; only for filtered/non-contiguous export. |
| D3 | Sparse import rejects mixed/duplicate/missing/out-of-range addressing; no positional fallback. |
| D4 | Metadata paste routes to Box 0 and warns if target lacks metadata records. |
| D5 | Outer Markdown code fences may be stripped with a warning; inner fences are content. |
| D6 | Clipboard helper retries and normalizes CRLF/CR before parsing. |
| D7 | Shortcut router is whitelist-only, IME/grab/CapsLock/AltGr safe. |
| D8 | Translation Lock excludes boxes from batch/paste/replace and reports skipped count. |
| D9 | Provider registry is local-only; no marketplace/network install/auto-update. |
| D10 | Termbase names are glossary/post-check for LLM, not masked by default. |
| D11 | Translation Memory is the XUAT cache index; provenance lives in sidecar metadata. |
| D12 | Prompt Studio templates are data, never executable code. |
| D13 | Game Box Preview measures rendered overflow; raw character count is only a fallback. |
| D14 | XUAT-lines mode escapes value newlines and preserves keys. |
| D15 | NGUI patterns are case-insensitive and centralized in `core/ngui_tags.py`. |
| D16 | Delayed tooltips cancel pending timers and check widget existence. |

---

## 7. Five-phase execution roadmap

### Phase 1 — Core structural API, binary & save safety
Scope: `core/story_ast.py`, `core/bundle_io.py`, `core/undo_journal.py`, `core/xunity_sync.py`, tests.
Non-goals: GUI redesign, CSIF, MTL drawer, startup redesign, Prompt Studio.

Tasks:
- [ ] Replace `Seg.rec_index` with `Seg.record`; add runtime Record uid; rebuild projection after structural changes.
- [ ] Add structural APIs: insert/delete/move/clone with BoxSnapshot preserving seg_texts.
- [ ] Preserve extra args; define command schema from fixture scan.
- [ ] Fix empty-arg arity and narration kind conversion.
- [ ] Fix raw tail freshness and page-break splitting.
- [ ] Make v2 text lossless; remove cmd0 special case before relabeling.
- [ ] Atomic same-directory tmp save with exact target verification and fingerprint check.
- [ ] XUAT one-line serialization, strict encoding, immutable JP keys, duplicate preview.
- [ ] Add regression tests and fixture scans.

Acceptance:
- Compile gate passes.
- Unit baseline measured and non-regressing.
- Unmodified fixture load→save is byte-exact.
- Metadata insertion followed by dialogue edit writes the correct record.
- Multiline XUAT sync remains one physical dictionary line.
- Failed verification leaves original bundle unchanged.

### Phase 2 — GUI integrity, central commit, shortcuts, undo identity & CSIF codec
Scope: `misora.py`, new `core/script_codec.py`, new `docs/SCRIPT_FORMAT.md`, new `tests/test_script_codec.py`, `core/search_engine.py` (snapshot/normalization only), tests.
Non-goals: Import/Export menus, importer registry, full preview dialog, empty state, ribbon removal, tooltips, version bump (Phase 4). Startup (Phase 3). MTL/Prompt Studio (Phase 5).
Tasks:
- [ ] Implement pure `core/script_codec.py` (CSIF v1): @@Speaker, @@_ narration, @@!meta, sparse @@#N|Speaker, legacy input adapters, serialize/parse/sniff_format/apply_to_document.
- [ ] Implement shared _commit_widget_edit for every mutation source.
- [ ] Fix Box 0 flush/save; never inject dialogue while Box 0 active.
- [ ] Fix plain-text save fallthrough.
- [ ] Remove widget aliasing; resolve active card safely.
- [ ] Install first-position shortcut bindtag router.
- [ ] Flush before undo/redo/save/close/navigation/rebuild.
- [ ] Batch undo applies model first, refreshes once; try/finally everywhere.
- [ ] Revision-based dirty state; doc/box identity in deltas.
- [ ] Clipboard helper (retry + CRLF normalization) + internal clipboard invalidation.
- [ ] Rewire Copy Box (insert mode), Paste Script (replace mode), AI prompt and plain Ctrl+V chooser to the codec.
- [ ] Search worker snapshots and queue completion; Replace All preview/undo safety.
- [ ] Dirty exit/close prompts; reload from disk; per-document state.
- [ ] Fix gradient comma emitter.
- [ ] Add Translation Lock foundation.
Acceptance:
- CSIF round-trip property tests pass.
- Ribbon Cut/Paste, Ctrl+B/I/U, size insertion all persist and undo.
- Ctrl+H/O/T do not mutate editor buffers.
- Box 0 save leaves dialogue speaker/text byte-identical.
- Undo back to saved revision clears dirty marker.
- Copy Box round-trips through Notepad++ with zero drift.
- Search UI always resets after error/cancel.

### Phase 3 — Fast startup & deferred session restore
Scope: `misora.bat`, `misora.py` bootstrap, `assets/splash.py`, `core/bundle_io.py` lazy import, logger, tests.
Non-goals: new editor features.

Tasks:
- [ ] Read actual `assets/splash.py`; measure baseline.
- [ ] Remove UnityPy probes from launcher.
- [ ] Lazy-load UnityPy under lock; decouple core imports.
- [ ] Paint splash before heavy imports; keep one process.
- [ ] Defer session restore after window visible.
- [ ] Validate saved geometry against virtual screen.
- [ ] Preserve corrupt config recovery copy.
- [ ] Move logger file writes to background queue.
- [ ] Benchmark large-story rendering before optimizing.

Acceptance:
- Actual millisecond trace before/after.
- No second Tk root or splash subprocess.
- Session restore still opens saved files.
- Config recovery copy created on parse failure.

### Phase 4 — Import/export, paste preview, empty state & polish
Scope: new `core/importers/`, `misora.py`, root `__init__.py`, `assets/splash.py` (version consumption only), tests.
The CSIF codec already exists from Phase 2; do NOT rewrite it.
Non-goals: MTL provider rewrite, Prompt Studio.
Tasks:
- [ ] File Import/Export menus (Interchange group) and importer registry.
- [ ] Xuat2Raw documented stub only.
- [ ] Upgrade the Phase 2 minimal confirm into the full Paste Preview (diff, routing indicator, overflow, sparse remap).
- [ ] Scoped export.
- [ ] Empty-state overlay.
- [ ] Remove redundant [-] ribbon button; player icon-only with fallback.
- [ ] Tooltips, version unification, ribbon measurement.
Acceptance:
- Export→import identity holds.
- Sparse mangled addressing is rejected.
- Registry discovery works.
- No legacy delimiter emitter remains outside the legacy adapter.
- Empty state appears/disappears correctly.
- No version string outside __version__.

### Phase 5 — Shared NGUI, MTL providers, drawer & Prompt Studio
Scope: `core/ngui_tags.py`, `core/mtl_engine.py`, provider modules, `misora.py`, tests.
Non-goals: further AST changes unless a regression is found.

Tasks:
- [ ] Central NGUI patterns; hyphen gradients; rendered length; integrity checker.
- [ ] TagMasker covers all emitted tags, multiline ruby, size, placeholders.
- [ ] TLS verified; secrets protected; DeepL usage test.
- [ ] Local provider registry; language maps; usage meter.
- [ ] Translate side drawer: Live OFF default, debounce, cache, stale cancellation, Apply/Refresh per engine.
- [ ] Prompt Studio: templates, variables, preview, token estimate, chunk stepper.
- [ ] Termbase and XUAT cache TM; speaker map; XUAT-lines mode.
- [ ] Game Box Preview and measured overflow.
- [ ] QA reports and proofreading workflow.

Acceptance:
- Mask/unmask identity for every glossary tag.
- Disabled providers never queried.
- Live translate does not freeze UI.
- Prompt preview equals copied payload.
- Game Box Preview measures colored text correctly.

---

## 8. Verification protocol

Every phase must run:

```text
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v
```

Record:
- Python version
- OS
- UnityPy/Pillow availability
- test count / failures / errors / skips
- fixture availability
- manual Windows Tk checks performed

Manual checks that matter:
- Ctrl+H/O/T inside a card do not mutate text.
- Ribbon Cut then navigation does not restore deleted text.
- Copy Box → external clipboard copy → Paste Box uses the newer payload.
- Box 0 edit/save does not alter Box #1.
- Multiline XUAT sync stays one dictionary line.
- Failed bundle verification leaves original unchanged.

---

## 9. Unresolved fixture / platform questions

These require real bundles or Windows Tk:

1. Exact metadata command semantics and extra args.
2. Narration record kind and empty-text representation.
3. Break convention: real newline vs escaped `\n`.
4. `choice` command support and argument shapes.
5. TextAsset str decode fidelity.
6. Non-canonical base64 raw preservation need.
7. Windows clipboard CRLF behavior.
8. Tk class binding behavior on the installed Windows/Tk version.
9. Game/AV file locks during replace.
10. Large-story render and search performance.

Do not convert these into confirmed bugs without evidence.