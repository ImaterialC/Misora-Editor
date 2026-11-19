=====================================================================
MISORA EDITOR — ANTIGRAVITY PROMPT PACK (FINAL CANONICAL)
=====================================================================
Last consolidated: 2026-11-20
Target release: v1.4.0
Repository: ImaterialC/Misora-Editor (local: D:\Misora-Editor)

HOW TO USE
1. Run these prompts IN ORDER. Do not skip Prompt 0.
2. Each prompt is self-contained. Paste one at a time into Antigravity.
3. Use /plan for audit/design prompts, /goal only for bounded execution.
4. Wait for the gate to pass before moving to the next phase.
5. After every phase, manually verify on Windows with real bundles.
6. Never hardcode a claimed 38/38 test baseline. Measure it dynamically.
7. The source files on disk are the only authority, never chat transcripts.

EXECUTION ORDER
  [optional] Prompt H   -> emergency hotfix for two machine-confirmed bugs
  Prompt 0              -> audit-only reconciliation
  Prompt 1              -> Phase 1: core, binary & save safety
  Prompt 2              -> Phase 2: GUI integrity + CSIF codec + box clipboard
  Prompt 3              -> Phase 3: fast startup & deferred session restore
  Prompt 4              -> Phase 4: import/export, preview, empty state, polish
  Prompt 5              -> Phase 5: shared NGUI, MTL providers, Prompt Studio

Do NOT start Prompt 2 until Prompt 1 gate passes.
Do NOT start Prompt 3 until Prompt 2 gate passes.
Do NOT start Prompt 5 until Prompt 4 gate passes.
Prompt 3 may run in parallel with Prompt 4 only after Prompt 2 passes.


=====================================================================
PROMPT H — OPTIONAL EMERGENCY HOTFIX
(run only if Ctrl+H or ribbon Cut is actively hurting your daily work;
Phase 2 will replace this properly)
=====================================================================
```
Apply a minimal emergency hotfix for two machine-confirmed defects.
Do NOT refactor architecture. Do NOT touch core/. Do NOT add new files.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @misora.py

FIX 1 — Tk class bindings mutate the buffer before app shortcuts.
User confirmed Ctrl+H deletes text in the dialogue editor.
On txt_dialogue, txt_box0_summary, txt_continuous, and every card Text
created in _render_continuous_view, bind these widget-level handlers and
return "break":
  <Control-h> -> self.on_show_replace()
  <Control-o> -> self.on_open_file()
  <Control-t> -> self.on_open_translator_assistant()
Widget-level bind runs before the Text class binding. Do not intercept
Ctrl+C/V/X/A. This is a stopgap; Prompt 2 will install the real bindtag
router and remove these individual bindings.

FIX 2 — Ribbon Cut/Paste never reach the model.
User confirmed ribbon Cut is reverted after navigation.
In on_text_cut and on_text_paste, after event_generate, explicitly commit
using EXISTING handlers:
  - Page mode:       self._on_dialogue_edited()
  - Continuous mode: self._on_card_text_edited(self.current_box_idx, target, card_info.get("gutter"))
  - Box 0 active:    self._on_box0_metadata_edited()
Do not create a new commit API in this hotfix.

FIX 3 — Make silent failures visible.
In report_callback_exception, in addition to the logger call, set
self.lbl_status text to a short error message and call self.show_toast(...).
Keep the existing logger call.

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v
Manual on Windows:
- Ctrl+H in a card leaves the buffer byte-identical and opens Replace.
- Ribbon Cut, navigate away, navigate back: the deletion persists.
- Ribbon Paste then Ctrl+S writes the new text into the bundle.

DELIVER changed lines, test output, manual observations.
Do not mark any other ledger row resolved by this hotfix.
```

=====================================================================
PROMPT 0 — AUDIT-ONLY RECONCILIATION (RUN FIRST)
=====================================================================
```
/plan Audit the current Misora workspace and reconcile the canonical
defect ledger. Make NO application code changes.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @misora.py @core/story_ast.py @core/bundle_io.py
@core/xunity_sync.py @core/mtl_engine.py @core/search_engine.py
@core/undo_journal.py @core/logger.py @assets/splash.py @misora.bat @tests/

GOAL
Verify the ledger in PROJECT_STATE.md against the actual files on disk.
Produce a corrected audit report and a proposed PROJECT_STATE.md update.
Do not implement fixes yet.

RULES
1. The source on disk is authority. Chat transcripts and legacy
   PROJECT_STATE variants are claims to verify.
2. Use stable slugs, not new B-numbers.
3. Classify each item as CONFIRMED / CONDITIONAL / DESIGN INVARIANT / RETRACTED.
4. Provide file:line evidence and the smallest reproducible test.
5. Do not invent fixture outcomes or Windows/Tk behavior.
6. Do not edit application source code in this pass.

VERIFY THESE HIGH-PRIORITY ITEMS (existing-code defects)
AST-INDEX-SHIFT, BOX-STRUCTURAL-OPS, BOX-PASTE-DEAD,
BUNDLE-SAVE-WRITES-BEFORE-VERIFY, BOX0-SAVE-CORRUPTION, V2-ROUNDTRIP-LOSS,
XUAT-SYNC-LINE-CORRUPTION, EMPTY-ARG-ARITY, NARRATION-EMPTY-PHANTOM,
PLAINTEXT-SAVE-FALLTHROUGH, PAGE-BREAK-NOT-SPLIT, RAW-TAIL-FROZEN,
CMD0-SPECIAL-CASE, DIRTY-EXIT-DROPS-EDITS, RELOAD-REVERT-HIT-CACHE,
REPLACE-ALL-BUNDLE-PREFILTER, REPLACE-ALL-UNDO-GAP,
TLS-VERIFICATION-DISABLED, API-KEYS-PLAINTEXT, TAGMASKER-INCOMPLETE,
SIZE-RIBBON-NO-COMMIT, CONTINUOUS-RIBBON-TARGET-STALE,
TRANSLATOR-SOURCE-SEED, UNDO-STORM, SEARCH-RACE, CLIP-SHADOW,
FOLDER-DROP-EXTRA-IGNORED, DEEPL-TEST-COST, CORE-IMPORT-COUPLING,
CONFIG-RECOVERY-OVERWRITE, STALE-CARD-REGISTRY, SHORTCUT-BINDTAG-ORDER,
RIBBON-CUT-PASTE-NO-COMMIT, GRADIENT-COMMA-EMITTER, MULTI-TEXTASSET-TARGET,
TEXTASSET-STR-DECODE-FIDELITY, SPAN-NFKC-PER-CHAR, UNDO-COALESCE-CROSS-SOURCE,
GENERIC-PLACEHOLDER-GAP, LOGGER-SYNC-IO, BULK-DELTA-NONATOMIC,
HARDCODED-PROJECT-PATH.

ALSO VERIFY THESE RETRACTIONS (do NOT hunt them again)
- Double paste dispatch: NOT PRESENT, on_text_paste returns "break".
- Internal box clipboard CLIP-SHADOW is currently LATENT because
  on_box_paste aborts at the missing _push_undo before reaching it.
- Lowercase hex rejection: NOT PRESENT, patterns already accept a-f.
- translate_async location: NOT PRESENT, it is module-level.
- Uploaded config JSON malformed: RETRACTED as paste artifact;
  CONFIG-RECOVERY-OVERWRITE remains valid.
- SEG-TARGET-STALE: treat as DESIGN INVARIANT until fixture proves otherwise.

MACHINE-CONFIRMED BY THE USER (record as evidence, do not re-test blindly)
- Ctrl+H inside a card deletes a character (SHORTCUT-BINDTAG-ORDER).
- Ribbon Cut then navigate away and back restores the text
  (RIBBON-CUT-PASTE-NO-COMMIT).
- Paste Box does nothing in either Page or Continuous view (BOX-PASTE-DEAD).
- Copy Box works and round-trips through Notepad++ (copy path is healthy).

FIXTURE / PLATFORM QUESTIONS (list, do not assume)
metadata command semantics and extra args, narration record kind,
break convention (real newline vs escaped), choice command args,
TextAsset str decode fidelity, base64 raw preservation, Windows clipboard
CRLF, Tk class bindings on installed Windows/Tk, game/AV file locks,
large-story render and search performance.

BASELINE
Run:
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v
Record actual count/failures/errors/skips, Python version, OS,
dependency availability, and fixture availability.
If UnityPy is missing, report an environment blocker; do not invent results.

DELIVER
1. Reconciliation table: slug / verdict / file:line evidence / correction.
2. Updated prioritized defect ledger using stable slugs.
3. Explicit disagreements with prior audits, if any.
4. Proposed PROJECT_STATE.md update (separate Existing Bugs from Design
   Invariants from Retracted claims).
5. Unresolved fixture/platform tests.
Wait for my approval before writing PROJECT_STATE.md.
```

=====================================================================
PROMPT 1 — PHASE 1: CORE STRUCTURAL API, BINARY & SAVE SAFETY
=====================================================================
```
/goal Execute Phase 1: core structural API, binary/save/XUAT integrity,
and migrate the three box-structure handlers so no build is left broken.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @core/story_ast.py @core/bundle_io.py
@core/undo_journal.py @core/xunity_sync.py @misora.py @tests/

SCOPE IN
core/story_ast.py, core/bundle_io.py, core/undo_journal.py,
core/xunity_sync.py, tests/, and misora.py ONLY for: _push_undo,
_dirty_state_changed, _sync_clean_view_to_current_box, on_box_new,
on_box_copy, on_box_cut, on_box_paste, _on_card_paste_caret.

SCOPE OUT
Shortcut router, central commit API, CSIF codec, clipboard format,
startup, MTL, UI polish. Those belong to Phase 2 and later.

INVARIANTS
- doc.records is the source of truth; Box is a projection.
- Seg.record references Record directly. No stale rec_index field,
  no Document back-reference.
- Runtime Record.uid is never serialized into binary or v2 output.
- Preserve unknown records and command-specific extra args.
- Never emit an empty binary argument. Narration uses a tag record,
  not print with a blank speaker.
- Save is same-directory tmp -> exact target verify -> fingerprint check
  -> os.replace.
- XUAT stays one key=value per physical line.

TASKS
1. AST identity: Seg.record direct reference; Record.uid; rebuild the Box
   projection after every structural mutation and after structural
   undo/redo; reject foreign Records. Migrate the three readers of
   rec_index (construction, inject_box, _update_raw_view) in this phase.
2. Cheap corruption fix first: call _rebuild_boxes() at the end of
   set_metadata so record insertion rebases segment targeting. Add a
   regression test proving a dialogue edit after a metadata insertion
   writes the CORRECT record.
3. Argument integrity: inject_box and set_metadata replace only the
   arguments they own. Scan fixtures for arg-count distributions before
   defining preservation rules.
4. Arity and narration: implement the empty-text representation proven by
   fixtures; add set_box_kind so narration converts print -> tag.
5. Break integrity: fix the "page" vs "next_page" breaker mismatch; update
   seg.raw alongside seg.text so a deleted trailing break stays deleted.
6. v2 lossless: preserve numeric cmd IDs, categories, unknown commands,
   whitespace-only args, and Unicode line separators. Remove the cmd_id==0
   special case BEFORE any _CMD_MAP relabeling.
7. Structural API: insert_box, delete_boxes, move_box, clone_boxes,
   set_box_kind. Add BoxSnapshot carrying seg_texts (never flatten
   multi-segment boxes).
8. Atomic save: lock target path_id/name; verify exact target TextAsset,
   object count, non-target bytes, and source fingerprint; bounded retry
   for Windows sharing violations; _is_saving guard.
9. XUAT: strict decode, preserve BOM/CRLF/key whitespace, escape value
   newlines, split on the first unescaped '=', immutable JP source keys
   per Box uid, duplicate/conflict preview, atomic write. Do NOT block
   short Japanese keys.
10. Undo core: doc/box identity in deltas; exception-safe batches; resolve
    identity at apply time.
11. GUI migration (required to avoid a broken build): implement the three
    missing helpers; rewrite on_box_new / on_box_cut / on_box_paste /
    _on_card_paste_caret to use the structural API and BoxSnapshot. Never
    construct Box(clean_text=...) and never deepcopy a Box. Keep the
    CURRENT triple-enter clipboard format in this phase; CSIF arrives in
    Phase 2.

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v
Record the actual baseline (count/failures/errors/skips, Python, OS,
UnityPy availability). Never assume 38/38.

REQUIRED TESTS
metadata insertion then dialogue edit writes the correct record;
structural insert/delete/move/clone round-trips through binary;
multi-segment clone preserves segment count; empty text and narration
preserve arity and create no phantom box; v2 round-trip preserves
cmd_32/category/unknown IDs/whitespace-only args; unmodified fixture
load->save is byte-exact; forced verification failure leaves the original
unchanged; multiline XUAT sync stays one dictionary line; a second save of
the same box still syncs.

MANUAL WINDOWS TESTS (mandatory)
New Box, Cut Box, Paste Box and Ctrl+V multi-box each work in BOTH Page and
Continuous view, each undone by ONE Ctrl+Z, and each persists after Ctrl+S
and reload from disk.

DELIVER changed files, real test output, fixture limitations, rollback
notes, updated PROJECT_STATE.md. Mark BOX-PASTE-DEAD and
BOX-STRUCTURAL-OPS resolved only with the manual evidence above.
```

=====================================================================
PROMPT 2 — PHASE 2: GUI INTEGRITY + CSIF CODEC + BOX CLIPBOARD
=====================================================================
```
/goal Execute Phase 2: CSIF codec, central edit commit, shortcut router,
undo identity, and a box clipboard that speaks CSIF.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @misora.py @core/story_ast.py
@core/undo_journal.py @core/search_engine.py @tests/
DEPENDS ON: Prompt 1 gate passed.

SCOPE IN
new core/script_codec.py, new docs/SCRIPT_FORMAT.md, new
tests/test_script_codec.py, misora.py, core/search_engine.py
(snapshot/normalization only), tests/.

SCOPE OUT
Import/Export menus, importer registry, full preview dialog, empty state,
ribbon removal, tooltips, version bump (Phase 4). Startup (Phase 3).
MTL/Prompt Studio (Phase 5).

PART A — CSIF codec (pure module, zero Tkinter, do this first)
Grammar: header occupies a whole line.
  "@@Speaker"        -> speaker
  "@@_"              -> narration (import also accepts a bare "@@")
  "@@{playername}"   -> literal player token
  "@@!title" / "@@!subtitle" / "@@!summary" -> Box 0, only before the
      first dialogue header
  "@@#N|Speaker"     -> sparse, 1-based, ONLY for non-contiguous export
Body: lines until the next header or EOF. Escape a body line starting with
@@ as \@@. Exactly one LF before the next header is a delimiter; all other
newlines are content. Accept LF/CRLF/CR, strip BOM, emit LF. Strip only an
OUTER Markdown code fence, with a warning.
API: serialize(doc, *, scope, box_indices, include_metadata="auto"),
parse(text), sniff_format(text), apply_to_document(doc, result, *, mode,
start_box_index, overflow, apply_speakers).
Modes: "insert" (create boxes), "replace" (overwrite from start). Never a
silent positional fallback in sparse mode. Reject mixed, duplicate,
missing, or out-of-range sparse addressing. Sanitize speakers (strip
zero-width/format/control chars, map NBSP/ideographic space to space).
Legacy INPUT adapters: "=== [BOX:n|Speaker:x] ===", triple-enter,
paragraphs, lines. Output is always CSIF.

PART B — GUI integrity
1. One shared _commit_widget_edit(widget) used by typing, ribbon, menu,
   Cut/Paste, size insertion, metadata and every virtual event. Replace
   the Prompt H stopgap.
2. Box 0: dedicated flush/save path; never call inject_box while
   is_box0_active; make the Continuous metadata card editable.
3. Plain-text save: return after a successful plain-text save; do not fall
   through into current_doc branches.
4. Remove txt_continuous aliasing; resolve the active card safely; clear
   the card registry on every render path.
5. MisoraShortcuts bindtag FIRST on editor widgets; whitelist only; return
   "break"; keysym.lower() with explicit Shift bit and Lock masked; skip
   IME composition and modal grabs; never intercept Ctrl+C/V/X/A; bind or
   remove every advertised accelerator.
6. Undo: flush pending edits at the TOP of on_undo/on_redo and before
   save/close/navigation/rebuild; try/finally batches; apply the whole
   batch to the model then refresh UI ONCE; revision-based dirty state.
7. Clipboard helper: retry on TclError, normalize CRLF/CR on read.
   Invalidate the internal box snapshot when the system clipboard differs
   (fixes latent CLIP-SHADOW).
8. Search/Replace: immutable snapshots for the worker; always reset the UI
   in finally; report skipped paths; Replace All uses the decoded model
   with preview and atomic bulk undo; fix the per-character NFKC span
   divergence.
9. Lifecycle: dirty exit/close prompts, reload_from_disk, per-document
   state, prune undo on close.
10. Gradients: emit HYPHEN [RRGGBB-RRGGBB]; accept comma on input with a
    normalization warning.
11. Translation Lock foundation: add a per-box lock flag persisted in a sidecar
    next to the config (never inside the bundle). Batch translate, clipboard
    paste, and Replace All must skip locked boxes and report the skipped count.
    Locked boxes show a small lock glyph on their card header and in the dock.

PART C — box clipboard speaks CSIF (the user's request)
1. on_box_copy emits CSIF via serialize(). Contiguous selection ->
   numberless. Non-contiguous (Select Box mode) -> sparse @@#N|Speaker.
   Box 0 selected -> @@! metadata headers. Store a BoxSnapshot plus the
   emitted CSIF text as the internal snapshot.
2. on_box_paste parses the clipboard with sniff_format/parse and applies
   mode="insert" after the active box, preserving speakers, converting
   narration to tag records, in ONE undo batch. Show a minimal confirm
   dialog: block count, first three speakers, insertion point. Never
   insert headers into dialogue text.
3. on_copy_script / on_paste_cross_box use the SAME codec with
   mode="replace" from the active box. Remove every triple-enter and
   "=== [BOX:" emitter.
4. Plain Ctrl+V inside an editor: if sniff_format reports CSIF, show a
   chooser (paste as text / paste across boxes / insert as new boxes /
   cancel). Default to cancel on ambiguity.
5. on_copy_ai_prompt emits the same CSIF body with a short header:
   "Translate JA->EN. Keep lines starting @@ unchanged. Preserve NGUI tags,
   {playername}, {0}. Same block count and order. Never begin a line with
   @@; escape it as \@@. Output only the script."

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v

REQUIRED TESTS
CSIF round-trip lossless including EOF without trailing newline, blank
lines inside bodies, escaped \@@, CRLF, code-fence stripping, sparse
rejection; copy->paste insert produces the expected new boxes and speakers;
copy->paste replace is a content no-op on the same document; a @@! payload
routes to Box 0 regardless of focus; one Ctrl+Z undoes a whole multi-box
insert; ribbon Cut/Paste and Ctrl+B/I/U and size insertion persist and
undo; Ctrl+H/O/T leave the buffer byte-identical; Box 0 save leaves
dialogue speaker/text byte-identical; undo back to the saved revision
clears the dirty marker; batch undo refreshes the UI once; a stale internal
box snapshot is discarded.
a locked box is skipped by paste and Replace All, and the skipped count is reported.

MANUAL WINDOWS TESTS (mandatory)
Copy Box -> paste into Notepad++ -> copy back -> Paste Box: speakers and
text round-trip with zero drift. Paste Box inserts correctly in BOTH views.
Ctrl+H does not delete text. Ribbon Cut survives navigation.

DELIVER codec spec, changed files, real test output, manual round-trip
evidence, updated PROJECT_STATE.md.
```

=====================================================================
PROMPT 3 — PHASE 3: FAST STARTUP & DEFERRED SESSION RESTORE
=====================================================================
```
/goal Execute Phase 3: fast startup, lazy imports, deferred session
restore, config recovery, and logger safety.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @misora.py @misora.bat @assets/splash.py
@core/bundle_io.py @core/logger.py @tests/
DEPENDS ON: Prompt 2 gate passed.

SCOPE IN
misora.bat, misora.py bootstrap/import/session-restore paths,
assets/splash.py, core/bundle_io.py lazy import only, core/logger.py,
tests/.

SCOPE OUT
New editor features, CSIF, MTL drawer, Prompt Studio.

CONSTRAINT
ONE process only. Do NOT spawn a second OS process for the splash. The
single tk.Tk() invariant holds.

TASKS
1. Read actual assets/splash.py and measure baseline before changing it.
2. Remove UnityPy probes from misora.bat; keep interpreter detection safe
   for paths containing brackets and spaces.
3. Lazy-load UnityPy under a module-level threading.Lock with
   double-checked caching; set FALLBACK_UNITY_VERSION inside the lock
   before returning; decouple core package imports so pure AST tests do
   not require UnityPy.
4. Paint splash before heavy imports; keep ONE process and ONE tk.Tk root.
5. Defer session restore until after main window visible; restore one file
   per after() tick with status-bar progress.
6. Validate saved window geometry against the virtual screen before
   deiconify; clamp into the work area while allowing legitimate negative
   coordinates.
7. Preserve a recovery copy of a parse-failed config before using
   defaults; never silently overwrite recoverable settings.
8. Move logger file writes to a background writer queue; make stdout
   printing conditional on console_visible.
9. Benchmark large-story rendering before adding virtualization or LRU.

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v
Run startup with a --perf flag three times and report actual millisecond
traces.

ACCEPTANCE
- No second Tk root or splash subprocess.
- Session restore still opens saved files and the active file.
- Config parse failure creates a recovery copy.
- Pure AST import does not require UnityPy.
- Startup claims are backed by measured traces, not assumptions.

DELIVER before/after trace table, changed files, test output, limitations,
updated PROJECT_STATE.md.
```

=====================================================================
PROMPT 4 — PHASE 4: IMPORT/EXPORT, PREVIEW, EMPTY STATE, POLISH
=====================================================================
```
/goal Execute Phase 4: File Import/Export, importer registry, full Paste
Preview, empty state, ribbon polish, tooltips and version unification.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @core/script_codec.py @docs/SCRIPT_FORMAT.md
@misora.py @assets/splash.py @__init__.py @tests/
DEPENDS ON: Prompt 2 gate passed. The codec already exists; do NOT
rewrite it.

SCOPE IN
new core/importers/, misora.py, root __init__.py, assets/splash.py
(version consumption only), tests/.

SCOPE OUT
MTL providers, Prompt Studio, termbase/TM, Xuat2Raw implementation,
further AST changes.

TASKS
1. File menu Interchange group: Import Script (Ctrl+Shift+I), Export
   Script (Ctrl+Shift+E), Export AI Prompt, Import Translation
   (apply_speakers=False), Export/Import XUAT Dictionary.
2. core/importers/ registry: ScriptImporter protocol (name, extensions,
   sniff, parse) with CSIFImporter, LegacyImporter, XUATDictionaryImporter.
   Menu code iterates the registry.
3. core/importers/xuat2raw.py: documented stub raising NotImplementedError,
   an xuat2raw_path config field, and a disabled menu slot "Import from
   Xuat2Raw (coming soon)".
4. Upgrade the Phase 2 minimal confirm into a full Paste Preview: detected
   format, block count, target range, per-box old->new diff with
   checkboxes, speaker toggle, explicit Box 0 routing indicator, codec
   warnings, integrity warnings, overflow Create/Ignore/Cancel, and a
   sparse remap dialog when addressing is invalid.
5. Scoped export: whole story, checked boxes in Select Box mode, or dock
   right-click selection.
6. Empty-state overlay in files_container: "No files open", Open File /
   Open Folder buttons, "Drag & drop .unity3d files here"; auto-hide; must
   not intercept HWND drag-and-drop.
7. Remove the redundant [-] ribbon button; keep the capability in NGUI
   Glossary and the Edit menu.
8. Player button icon-only with a tooltip and a text fallback when
   get_icon returns None.
9. ToolTip: 450 ms delay, theme contrast via best_contrast_fg, cancel the
   pending after_id on Destroy, check winfo_exists; attach to every
   icon-only control.
10. Version: __version__ = "1.4.0" in root __init__.py with a
    backward-compatible alias; consumed by splash, About, window title and
    the color picker. Remove every hardcoded version string.
11. Re-measure the ribbon: <= 425 px, no clipping at ui_font_size 8
    through 16.

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v

REQUIRED TESTS
export->import identity; registry discovery; sparse remap rejection;
empty-state visibility; no version string outside __version__; no legacy
emitter outside the legacy adapter.

MANUAL
Screenshots of the empty dock, the new File menu, the ribbon at font 8 and
16, and About plus splash both showing 1.4.0.

DELIVER changed files, test output, screenshots, updated PROJECT_STATE.md.
```

=====================================================================
PROMPT 5 — PHASE 5: SHARED NGUI, MTL PROVIDERS, PROMPT STUDIO
=====================================================================
```
/goal Execute Phase 5: shared NGUI integrity, MTL provider safety,
Translate drawer, and Prompt Studio.

CONTEXT
@AGENTS.md @PROJECT_STATE.md @core/mtl_engine.py @core/script_codec.py @misora.py @tests/
NOTE: core/ngui_tags.py does not exist yet; Task 1 creates it as the single source of NGUI patterns.
DEPENDS ON: Prompt 4 gate passed.

SCOPE IN
core/ngui_tags.py, core/mtl_engine.py, new local provider modules,
misora.py MTL/Prompt Studio UI, tests/.

SCOPE OUT
Further AST structural changes unless a regression is found.

TASKS
1. Central NGUI patterns: hyphen gradients, comma input normalization,
   rendered_length, integrity checker.
2. TagMasker covers every emitted tag: size, color/gradient, multiline
   ruby, placeholders; use a per-call random nonce to avoid literal
   placeholder collision.
3. TLS verified; support CA configuration safely; no insecure checkbox.
4. Protect API secrets outside ordinary config; redact logs.
5. DeepL connection test uses a usage endpoint when available.
6. Local provider registry: Google, DeepL, Local/Sugoi, LLM/OpenAI, XUAT
   Cache; language maps; usage meter; disabled providers never queried.
7. Translate side drawer: Live Translate default OFF, 400 ms debounce,
   Japanese-only filter, cache, stale cancellation, per-engine
   Apply/Refresh/Copy.
8. Prompt Studio: purpose templates, variables, live final preview,
   token/char estimate, per-engine override, import/export, chunk stepper.
9. Termbase: glossary/post-check for LLM; opt-in masking only for
   providers without glossary; DeepL glossary when supported.
10. Translation Memory = XUAT cache index; provenance sidecar only.
11. XUAT-lines mode and speaker map.
12. Game Box Preview and measured overflow indicator.
13. QA reports and proofreading workflow.

VERIFY
py -3.12 -m compileall -q misora.py core assets tests
py -3.12 -m unittest discover -s tests -v

REQUIRED TESTS
mask/unmask identity for every glossary tag; multiline ruby protected; TLS
verified for remote providers; secrets absent from config/logs/exports;
disabled providers never instantiated; Live Translate debounced and stale
results discarded; Apply is undoable and does not change speaker; Prompt
preview equals copied payload; termbase mask/unmask identity where masking
is enabled; XUAT-lines round-trip lossless; Game Box Preview measures
rendered length, not raw markup.

DELIVER changed files, test output, drawer screenshot, prompt preview
screenshot, limitations, updated PROJECT_STATE.md.
```
