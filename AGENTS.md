# Misora Editor — Agent Rules

## 1. Source of truth
- Read `PROJECT_STATE.md` before every task. It is the canonical ledger and roadmap.
- Read source files from disk. Never reason from chat-pasted code; chat paste loses indentation and escapes.
- Older transcripts, `Google4_*.txt`, and legacy `PROJECT_STATE` variants are claims to verify, not authority.
- Separate CONFIRMED defects, CONDITIONAL claims, DESIGN INVARIANTS, and RETRACTED claims.

## 2. Verification gate
- Run `py -3.12 -m compileall -q misora.py core assets tests` and `py -3.12 -m unittest discover -s tests -v`.
- Record the actual baseline: test count, failures, errors, skips, Python version, OS, dependency availability.
- Never hardcode a claimed 38/38 baseline. Never delete, skip, or weaken tests to pass.
- If UnityPy or fixtures are missing, report an environment blocker; do not invent results.

## 3. Tkinter architecture
- Exactly one `tk.Tk()` root (`MisoraApp`). Splash and dialogs are `tk.Toplevel(parent=...)`.
- Every Tk variable passes an explicit `master=`.
- Never reassign a widget attribute to another widget. `self.txt_continuous` remains the fallback widget; cards live in `_card_widgets`.
- Guard dynamic widget access with `winfo_exists()`.

## 4. AST identity
- `StoryDocument.records` is the source of truth. `Box` is a projection.
- `Seg.record` must reference its `Record` directly. Do not keep a stale `rec_index` field and do not add a Document back-reference to `Seg`.
- Runtime `Record.uid` may be used for undo/identity, but never serialized into binary/v2 output.
- Rebuild the Box projection after every structural mutation and after structural undo/redo.
- `inject_box` must reject a Record not owned by the document.

## 5. Box model safety
- `Box.clean_text`, `.text`, and `.raw` are read-only properties. Never assign to them.
- Never construct `Box(clean_text=...)`.
- Do not ship a global `Box.__deepcopy__` failure before migrating Copy/Paste Box to an explicit snapshot API.
- `BoxSnapshot` must preserve `seg_texts`, not flatten multi-segment boxes.

## 6. Structural edits
- New/Cut/Paste/Move/Clone must call StoryDocument structural APIs that mutate records, not only `doc.boxes`.
- Preserve unknown commands even when they are not projected into dialogue Boxes.
- `removed_records` is keyed by Record uid, not positional index.

## 7. Argument integrity
- `inject_box` and `set_metadata` replace only the arguments they own. Preserve command-specific extra args.
- Never emit an empty binary argument; `to_binary` skips empty args and changes arity.
- Narration must use a `tag` record, not a `print` record with an empty speaker.
- Normalize `{playername}` to `{0}` in both speaker and text before writing records.
- Update `seg.raw` alongside `seg.text`; never derive trailing breaks from a frozen original snapshot.

## 8. v2 text safety
- v2 text must preserve numeric command IDs, categories, unknown commands, whitespace-only args, and all Unicode line separators.
- Remove the `cmd_id == 0` special case before any `_CMD_MAP` relabeling.
- Do not claim v2 is lossless until round-trip tests pass.

## 9. Bundle save safety
- `save_bundle_story` already uses `packer="original"`; do not pretend to add it.
- Save flow: same-directory `.tmp` → reopen tmp → verify exact target TextAsset by path_id/name → verify object count and non-target bytes → check source fingerprint → `os.replace`.
- Never overwrite the original before verification succeeds.
- Guard re-entrant saves with `_is_saving`; use bounded retry for Windows sharing violations, but report failure honestly.

## 10. XUAT dictionary safety
- Dictionary format is one `key=value` per physical line. Escape real newlines in values.
- Preserve BOM, CRLF/LF, key whitespace, and unchanged lines.
- Decode strictly; never `errors="replace"` then rewrite the whole file.
- Split on the first unescaped `=` according to verified XUAT rules.
- Keep immutable Japanese source keys per Box uid. Never overwrite them with English text.
- Preview duplicate/conflicting keys. Do not block short Japanese keys.

## 11. Central edit commit
- Every widget mutation (typing, ribbon, menu, Cut/Paste, size, metadata, virtual events) must end in one shared commit path.
- Virtual events such as `<<Cut>>`/`<<Paste>>` produce no KeyRelease; they must explicitly commit.
- Box 0 has a dedicated metadata flush/save path. Never call `inject_box` while `is_box0_active`.

## 12. Shortcut router
- Install a first-position bindtag (`MisoraShortcuts`) on editor widgets.
- Handle only an explicit whitelist of app shortcuts and return `"break"`.
- Never intercept standard Ctrl+C/V/X/A inside Text/Entry.
- Normalize `keysym.lower()`, read Shift explicitly, mask Caps Lock, avoid AltGr/Ctrl+Alt conflicts, respect IME composition and modal grabs.
- Every advertised accelerator must have a real binding.

## 13. Undo and dirty state
- Flush pending edits before undo, redo, save, close, navigation, and view rebuild.
- Every `begin_batch()` needs `end_batch()` in `finally`.
- Apply a batch to the model first, then refresh UI once.
- Deltas use document identity and stable box/record identity, not only positional index.
- Dirty state is revision-based: undo back to the saved revision becomes clean.

## 14. Clipboard
- All clipboard access uses a helper with retry on `TclError` and CRLF/CR normalization on read.
- Internal box clipboard must not shadow a newer system clipboard payload.

## 15. Workers and search
- Workers never call Tk methods and never mutate the document or undo journal.
- Search uses immutable snapshots captured on the UI thread.
- Worker completion/error is posted through a main-thread queue; search UI always resets in `finally`.
- Report skipped/inaccessible paths instead of silently under-reporting results.

## 16. Document lifecycle
- Save and restore per-document view state, selection, modified boxes, and JP snapshots on file switch.
- Closing a document prunes its undo deltas. Undo must not silently reopen a closed file.
- Dirty exit and dirty close prompt Save/Discard/Cancel. Failed save aborts close.
- Reload/Revert uses `reload_from_disk=True`.

## 17. Config and secrets
- A parse-failed config is preserved as a recovery copy before defaults are used.
- API keys do not live in ordinary config. Prefer OS credential storage / DPAPI; redact secrets from logs and exports.

## 18. Network safety
- TLS certificate and hostname verification stay enabled.
- Do not add an ordinary “ignore SSL errors” checkbox.
- DeepL connection tests should use a non-translation usage endpoint when available.

## 19. NGUI single source
- `core/ngui_tags.py` is the only definition of NGUI tag patterns.
- Vertical gradients emit hyphen `[RRGGBB-RRGGBB]`; comma syntax is accepted on input and flagged/normalized.
- TagMasker must cover every tag the editor emits, including size and multiline ruby.
- User-visible length counters measure rendered text, not raw markup.

## 20. CSIF rules
- CSIF is a future interchange format, not a substitute for AST repair.
- Export uses `@@Speaker`, explicit narration `@@_`, and metadata `@@!title/@@!subtitle/@@!summary`.
- Sparse addressing `@@#N|Speaker` is 1-based and only for filtered/non-contiguous export.
- Reject mixed, duplicate, missing, or out-of-range sparse addressing; never silently remap positionally.
- Strip only an outer Markdown code fence; never alter fences inside dialogue bodies.

## 21. UI safety
- Colors use theme + `best_contrast_fg()`.
- Icon-only controls have tooltips and text fallback when icons are unavailable.
- `__version__` in root `__init__.py` is the single version source.

## 22. Startup
- One process only. Do not spawn a second OS process for splash.
- Remove UnityPy probes from `misora.bat`; lazy-load UnityPy under a lock; defer session restore.
- Measure before claiming performance improvements.

## 23. Disk and logging
- Use a Windows long-path helper for deep Priconne paths.
- Logger file writes happen on a background writer queue, not synchronously under lock on the UI thread.
- Do not change process DPI awareness at runtime.

## 24. Scope discipline
- Do not implement CSIF, MTL drawer, Prompt Studio, Xuat2Raw, LRU eviction, or splash redesign before Phase 1–2 data-integrity gates pass.
- Do not invent fixture outcomes or platform behavior. Mark conditional claims explicitly.

## 25. Delivery
- Every task ends with: changed files, tests run, actual output, limitations, rollback notes, and an updated `PROJECT_STATE.md`.

## 26. Box clipboard contract
- Copy Box emits CSIF (`@@Speaker`, `@@_` narration, `@@!meta`), never bare triple-enter.
- Paste Box INSERTS new boxes after the active box. Paste Script REPLACES text from the active box forward. Same format, different mode.
- Plain Ctrl+V on a payload containing CSIF headers must ask the user (text / across boxes / insert boxes / cancel).
- A CSIF header must NEVER end up inside Box.clean_text or any binary argument.
- Sparse `@@#N|Speaker` is 1-based and only emitted for non-contiguous selections; reject mixed, duplicate, missing or out-of-range addressing.

## 27. No broken intermediate state
- Any phase that changes Seg/Box internals MUST migrate on_box_copy, on_box_paste and _on_card_paste_caret in the SAME phase.
- Never ship a phase in which Copy Box raises. Do not add a Box.__deepcopy__ failure before those handlers use BoxSnapshot.

## 28. Helpers before callers, and visible failures
- _push_undo, _dirty_state_changed and _sync_clean_view_to_current_box must exist before any handler calls them.
- report_callback_exception must surface a status-bar error, not only a log line. A silently dead button is a defect, not acceptable behavior.

## 29. Machine-confirmed release blockers
Verified by the user on Windows: Ctrl+H mutates the dialogue buffer; ribbon Cut is reverted by navigation; Paste Box does nothing in either view.
These three are release blockers and each needs an explicit manual Windows test in addition to unit tests.