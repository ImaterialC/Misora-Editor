# Misora — Open Issues, Test Debt & Manual QA Ledger

**Baseline context:** S11e `v1.4.15`, HEAD `ead65077a2a6cf3a664543cfb50f855268a29e2a`; DOCS-01 reconciled at `v1.4.15` HEAD `3edf43e11b3479ac6ab1b20adb03a6e6ad8abfcd`  
**Purpose:** Preserve reports, proposals, test debt, fixture blockers, manual QA, and deferred limitations without conflating them.

## Status model — separate axes

**Evidence labels:** `REPORTED` (not independently reproduced); `SOURCE-OBSERVED` (seen in source/recorded evidence, runtime may be unverified); `CONFIRMED` (current reproducible or direct verified evidence); `NEEDS-REPRO` (requires a current-version repro); `PROPOSAL` (suggested feature/design, not a proven defect); `DEFERRED` (intentionally unscheduled or not implemented).

**Lifecycle labels:** `ACTIVE`, `SUPERSEDED`, `DEFERRED`, `RETRACTED`, `HISTORICAL-REFERENCE`.

An item may carry multiple evidence notes, e.g. `REPORTED + NEEDS-REPRO`. Do not promote evidence based on repetition in documents. Lifecycle is not an evidence grade.

## A. T-01..T-04 — reported behavior

| ID | Legacy ref | Evidence | Lifecycle | Description / closure criteria |
|---|---|---|---|---|
| **T-01** | `BUG-UI-EMPTY-STATE-01` | `CONFIRMED` | `HISTORICAL-REFERENCE` | **Closed (automated TDD `11/11 PASS` + Windows Manual QA `M-1..M-12 PASS` on `v1.4.15`).** Root cause: `_update_empty_state_visibility()` (`misora.py:9763-9786`) used `winfo_ismapped()` across 8 checks, returning `0` while root `Tk()` was withdrawn (startup / splash / `_deferred_restore()`), leaving `gd_scroll_wrap` and `empty_state_frame` dual-packed. Fixed via 8 `winfo_manager() == "pack"` / `!= "pack"` checks (`8	8	misora.py`, `23912` lines preserved), protected by `tests/test_t01_empty_state_overlay.py`. **Manual QA (`T-01_Walkthrough.md` M-1..M-11 PASS, noting Plan-vs-Walkthrough M-11/M-12 remap; M-12 operator sign-off):** OS Windows 11 (`Microsoft Windows [Version 10.0.26100.6725]`), Display/DPI `1920x1080`, `125% DPI`, Build/HEAD `v1.4.15` @ `33b6f7dc10dcb86b853aa71ab833864eeb843dfa`, Operator Project Lead. |
| **T-02** | `u-08` | `CONFIRMED` | `HISTORICAL-REFERENCE` | **Closed (automated TDD `8/8 PASS` + Windows Manual QA `M-1..M-4 PASS` on `v1.4.15`).** Overflow indicator tooltip (`lbl_char_overflow`, adjacent to `btn_next`; `btn_next` tooltip was already correct) displayed stale `"50 x 3"` / `"50 digit-widths"` instead of `"54d x 3"` / `"54 digit-widths"` after S09 calibration changed `DIALOGUE_MAX_DIGITS` from `50` to `54`. Fixed (`5	5	misora.py`, `23912` lines preserved): `misora.py:5577` converted to dynamic f-string (`DIALOGUE_MAX_DIGITS`/`DIALOGUE_MAX_LINES`), `misora.py:5578` updated to describe dual-font measurement (`active editor font` line widths against `fixed reference boundary`), and 3 stale docstrings (`_get_ruler_measure_font`, `_update_char_overflow_indicator`, `_draw_single_pixel_ruler`) updated from `50d`/`50` to `54d`/`54`. Protected by `tests/test_t02_next_tooltip.py` (`4` Probes + `4` Guards). **Windows Manual QA (`M-1..M-4 PASS`):** `v1.4.15` @ `3edf43e11b3479ac6ab1b20adb03a6e6ad8abfcd`, Windows 11 `10.0.26100.6725`, `1920x1080` 100% & 125% DPI, Project Lead. M-1/M-2 (tooltip text `"Native 54d x 3 dialogue rule..."`) confirmed at both DPI scales; M-3 (Next/Prev tooltips unaffected) confirmed; M-4 (label dynamic update) confirmed `54/54d · 1/3L` with red indicator on overflow. **T-02 addressed the stale tooltip/docstring only; it is not the same scope as T-08a (window position/DPI layout).** `tools/generate_symbol_index.py --check` → `CHECK PASS` at `3edf43e`. |
| **T-03** | `u-05` | `CONFIRMED` + `ROOT-CAUSE: NEEDS-CODE-VERIFY` | `ACTIVE` | **Report:** Pin in All Script turns speaker jumps into multi-select, leaving orphaned purple highlight cards. **Windows 8 reproductions (4 screenshots) on `v1.4.15` @ `3edf43e`, Windows 11 `10.0.26100.6725`, `1920x1080` 100% DPI, Project Lead.** RAW observations (Dialogue → All Script then back): (i) Initial Dialogue → All Script switch renders 1 active card cleanly. (ii) Switching Dialogue and back clears accumulated highlights. **Repro 1:** `#004` active/white, `#003`/`#005`/`#007` orphaned purple. **Repro 5:** `#003` active/white, `#002`/`#004`/`#005`/`#006` orphaned purple. **Repro 6/7:** Clicking `#003` then `#006` turns ONLY the immediately-previous active `#003` white while earlier orphans `#002`/`#004`/`#005` remain purple. **Repro 8:** Shortcuts navigate `#006..#010` purple with Pin OFF & Select Box OFF while `[ ]` checkbox stays empty. **Suspected root cause:** `_selected_boxes` corruption — UNPROVEN; requires source verification of card highlight/cleanup logic and `_selected_boxes` mutation path. |
| **T-04** | `u-02` | `REPORTED` + `NEEDS-REPRO` | `ACTIVE` | **Report:** Red overflow marker may not cover line 4+ (>3L) as well as horizontal >54d. M-4 observation during T-02 QA: label shows red `54/54d · 1/3L`; numerator appears clamped. **Open question:** does the label numerator track actual line count beyond 3, or is it clamped at the threshold boundary? Verify the current contract and visual behavior. Do not confuse raw newline count with visual wrapping; retain hard-linebreak and rendered-width rules. |

## B. T-05..T-10 — proposals requiring triage/design sign-off

| ID | Legacy ref | Evidence | Lifecycle | Summary / gate |
|---|---|---|---|---|
| **T-05** | `u-01` | `PROPOSAL` | `ACTIVE` | Path/naming redesign: rename Project Folder to Game Folder; expose separate Game Folder, RedirectedResources folder, and XUnity.AutoTranslator Text Folder paths; avoid hardcoded framework assumptions. BepInEx/Daring Tact are possible frameworks; XUnity.AutoTranslator is a plugin, not a framework. Validate auto-detection and multi-language/multi-framework behavior first. |
| **T-06** | `u-03a` | `PROPOSAL` | `ACTIVE` | Remember separate default Save directories for `.misora` project save vs Save/Patch Bundle (`Ctrl+Shift+S`). Confirm UX and persistence semantics. |
| **T-06b** | (split from T-06) | `REPORTED` + `NEEDS-REPRO` / `PROPOSAL` | `ACTIVE` | **Close behavior:** Current close (×) closes individual file without offering `.misora` Save Project — `REPORTED + NEEDS-REPRO` (verify whether this is current behavior). **Unified `.misora` Save Project prompt on close:** `PROPOSAL` — if closing the last file or the window, prompt to save the `.misora` project state. Requires design sign-off on UX flow and dirty-state semantics. |
| **T-07** | `u-07` | `PROPOSAL` | `ACTIVE` | Extend lazy 350 ms tooltips to selected informative labels/panels: voice cue filename, segment count, Opened Files drawer, Box count, Customize/NGUI Glossary, Search Results, Import from XUAT. Avoid noisy blanket coverage. |
| **T-08** | `u-11` | `PROPOSAL` | `ACTIVE` | Ribbon redesign: stabilize Prev/Next positions; evaluate four rows (Info / View Nav / MTL-AI-Edit / NGUI), including select/lock/count/title/subtitle/char-line/selection controls. View-type label default OFF; Title/Subtitle visibility is coupled (turning Title off also hides Subtitle, Title-only remains allowed). Consider removing ribbon Select Box toggle because card checkboxes remain available and can be hidden in View. Measure impact at 768p / 125% DPI. Requires approved mockup and usability sign-off. |
| **T-08a** | (split from T-08/`BUG-39`/`FEAT-04` / `BUG-UI-TOOLTIP-CLIP-01`) | `CONFIRMED` + `ROOT-CAUSE: SOURCE-OBSERVED` | `ACTIVE` | **ToolTip screen-edge clamping (automated fix + TDD `10/10 PASS`; Windows Manual QA `M-1..M-6` `MANUAL-PENDING`).** Root cause: `ToolTip.show_tip()` (`misora.py`) called `wm_geometry(f"+{x}+{y}")` before packing/measuring tooltip dimensions and without clamping to monitor work-area bounds (`lbl_char_overflow` 702×34px clipped off right edge when maximized at 100%/125% DPI). Fixed (`92	3	misora.py`, `24,001` lines): added `_get_work_area()` (Win32 `MonitorFromPoint`/`GetMonitorInfoW` via `WinDLL("user32", use_last_error=True)` with explicit `ctypes` prototypes + Tk primary-screen fallback, zero DPI mutation) and updated `ToolTip.show_tip()` (`withdraw()` → pack → `update_idletasks()` → 4-edge clamp & bottom flip → `wm_geometry` → `deiconify()`). Protected by `tests/test_t08a_tooltip_clamping.py` (`7` Probes + `3` Guards, `10/10 OK`; full suite `504 = 461 PASS + 35 SKIP + 6 FAIL + 2 ERROR`, `0` new regressions). **Manual QA `M-1..M-6`:** `MANUAL-PENDING` (note: if only 1 monitor is present, `M-5` must be marked `NOT RUN` / `UNVERIFIED`, never `PASS`). **Preserved open sub-item:** initial main-window off-screen title-bar clipping at 100% DPI (`_deferred_restore()` / `sanitize_window_geometry` — `CONFIRMED` + `NEEDS-CODE-VERIFY`) remains open within T-08a scope. **N-4 note:** `tools/generate_symbol_index.py --check` is transiently stale until Project Lead post-commit regeneration. |
| **T-08b** | (split from T-08/snapped layout) | `CONFIRMED` + `ROOT-CAUSE: NEEDS-CODE-VERIFY` | `ACTIVE` | **Snapped half-screen layout (~960px).** Confirmed on `v1.4.15` @ `3edf43e`, Windows 11 `10.0.26100.6725`, `1920x1080`, Project Lead. When window is snapped to half-screen (~960px width), layout has usability issues. **Suspected root cause:** Minimum-width constraints or responsive breakpoints not accounting for snapped window geometry — `NEEDS-CODE-VERIFY`. |
| **T-09** | `u-12` | `PROPOSAL` | `ACTIVE` | Explicit Insert Box / Replace Box / tri-state Select All Box controls. Check overlap with shipped S11e controls before suggesting duplicates. |
| **T-10** | `u-06` | `PROPOSAL` | `ACTIVE` | Selected-box card-level visual highlight in All Script, alongside active-box highlight; measure virtualized card-pool impact. |

## C. T-11..T-14 — future / unscheduled proposals

| ID | Legacy ref | Evidence | Lifecycle | Summary / constraint |
|---|---|---|---|---|
| **T-11** | `u-03b` | `PROPOSAL` + `DEFERRED` | `DEFERRED` | Read-only Original Data panel beside Raw Commands, preserving original speaker/actor/text as durable reference across save/reopen. Not yet an approved "Master Undo" design. Requires identity, provenance, snapshot persistence, and restore semantics. |
| **T-12** | `U-04` / S11b2 | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | XUnity.AutoTranslator sync disk scan/write was recorded at ~2.899 s on 1,814 files / 243k lines and accepted via S11b2 Option A waiver. Async worker IO is deferred; do not promise 0 ms without measurement. Any worker must obey Tk/main-thread and immutable-snapshot rules. |
| **T-13** | `u-10` | `PROPOSAL` + `DEFERRED` | `DEFERRED` | Human-readable XUAT-format backup/revert with provenance, source attribution, encoding/fingerprint, path mapping, preview, and selective re-import. Do not confuse datamine and plugin-generated backups. **Track B dependency:** Strictly after `T-11`, which provides the persistent snapshot model, capture-time provenance, and durable non-uid key required for reliable backup/restore identity. |
| **T-14** | `u-09` / `u-13` | `PROPOSAL` + `DEFERRED` | `DEFERRED` | GitHub Actions release `.zip` + `.exe` pipeline. Deferred because current v1.5.0 campaign is cancelled. Reconsider only with a new release charter covering build, signing, licensing, AV, reproducibility, and rollback. |

## D. Revalidation and MANUAL-PENDING QA

### D.1 Legacy release-blocker observations — current status must be rechecked

- **AGENTS.md §29 Ribbon Cut:** legacy user verification on Windows v1.4.0 reported Ribbon Cut reverted after navigation. Current v1.4.15 status: `NEEDS-REPRO`; explicit manual Windows test required.
- **AGENTS.md §29 Paste Box:** legacy user verification on Windows v1.4.0 reported Paste Box did nothing in Dialogue and All Script. Current v1.4.15 status: `NEEDS-REPRO`; test both views and Insert/Replace semantics.
- **Q-04.1.2 / Q-04.1.3:** `NEEDS-REPRO`; Project Lead reproduction confirmation needed if still applicable.
- **T-01:** `HISTORICAL-REFERENCE` (closed) — automated fix + TDD (`11/11 PASS`) and Windows manual QA `M-1..M-12` (`PASS` on `v1.4.15` @ `33b6f7dc10dcb86b853aa71ab833864eeb843dfa`, Windows 11 `10.0.26100.6725`, `1920x1080`, `125% DPI`, Project Lead).
- **T-02:** `HISTORICAL-REFERENCE` (closed) — automated fix + TDD (`8/8 PASS`) and Windows manual QA `M-1..M-4` (`PASS` on `v1.4.15` @ `3edf43e11b3479ac6ab1b20adb03a6e6ad8abfcd`, Windows 11 `10.0.26100.6725`, `1920x1080` 100% & 125% DPI, Project Lead).

### D.2 MANUAL-PENDING

- S11c: Ctrl+Z Undo after Import from XUAT following a Quick Edit change.
- S11d Q-08: post-import Synopsis Undo/Redo.
- S11d Q-11: DeepL Globe check on the DeepL card and while Box 0 is active.
- Import from XUAT smoke test on `BepInEx\Translation\en\Text` or the approved equivalent real local layout.
- Ribbon Cut after navigation and Paste Box in both Dialogue and All Script views.
- Q-04.1.2 / Q-04.1.3 Project Lead reproduction confirmation.

Manual results must record exact version, OS/DPI, steps, expected vs actual, fixture/path context, and operator confirmation. Unit tests alone do not close manual QA.

## E. Automated test hygiene debt — recorded S11e baseline

**Three non-fixture failures recorded:**
1. `tests/test_phase3_performance_config.py::test_05` — local `misora_config.json` isolation hygiene.
2. `tests/test_s9c_workspace_safety.py::test_04` — default config template contract hygiene.
3. `tests/test_v15_s01_stability_remediation.py::test_probe_8` — hard-coded expected version `1.4.1` vs current `1.4.15`.

**Fixture-dependent failures/errors and skips:**
- Missing proprietary `storydata_1001005.unity3d` was recorded as causing 3 failures + 2 errors in `tests/test_s8b2_memory_guards.py::test_01..test_05`, and 35 skips across fixture-gated tests.
- These are recorded S11e findings, not a fresh reproduction in this ledger. Recheck fixture availability/current environment. Never invent a fixture result or weaken tests.

**Recorded S11e totals:** 475 total = 432 PASS + 35 SKIP + 6 FAIL + 2 ERROR. Post-T-01/T-02 totals: 494 total = 451 PASS + 35 SKIP + 6 FAIL + 2 ERROR. This is not a clean suite and not 494 passing tests.

### E.1 Cross-test Tk teardown watch

`Tcl_AsyncDelete` cross-test GC/teardown abort was observed during older S11c/S11d monolithic discovery, while S11e monolithic discovery completed cleanly. Evidence: `SOURCE-OBSERVED` historically + `NEEDS-REPRO` current. Lifecycle: `ACTIVE` watch item. Do not call it a current deterministic failure without reproducing on the current environment.

### E.2 Phase 6 test hygiene — `tests/test_v15_s02_fonts_ruler_metrics.py:253`

Recorded test at line 253 uses a hardcoded font-metric expectation that may drift if system fonts or DPI differ across machines. Watch item — not a current failure, but a fragility note for future cross-environment runs.

## F. DEF-01..DEF-10 — deferred core limitations / blocked definitions

| ID | Evidence | Lifecycle | Recorded definition / constraint |
|---|---|---|---|
| **DEF-01** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | `core/story_ast.py:to_binary()` preserves empty binary-argument arity with a sentinel containing exactly one ASCII space (`" "`). Accepted under S11c Option A. Do not change, strip, or replace without a new decision and live-client evidence. |
| **DEF-02** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | Numeric command IDs 35/32 have synthetic binary/v2 test coverage, but real production bundle verification remains blocked by unavailable `storydata_1001005.unity3d`. Require the real fixture or written Project Lead waiver. |
| **DEF-03** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | Multi-TextAsset target selector remains deferred; recorded `load_bundle_story` behavior selects a single primary story TextAsset. Requires fixture-backed specification. |
| **DEF-04** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | Box 0 Summary overflow was unmeasured/deferred in the recorded ledger. Do not assume ordinary dialogue overflow rules apply without a specific decision/test. |
| **DEF-05** | `SOURCE-OBSERVED` + `NEEDS-REPRO` | `DEFERRED` | Definition unavailable because `Phase_2.5_Canonical_Ledger_LOCKED.md` was missing from recorded disk/Git object store. Do not invent meaning; search authoritative source/history. |
| **DEF-06** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | `_is_speaker_pinned` was recorded as preserved/untouched. Keep behavior until named scope authorizes change; confirm current implementation before acting. |
| **DEF-07** | `SOURCE-OBSERVED` + `NEEDS-REPRO` | `DEFERRED` | Definition unavailable in the recorded missing Phase 2.5 canonical ledger. Do not guess. |
| **DEF-08** | `SOURCE-OBSERVED` + `NEEDS-REPRO` | `DEFERRED` | Definition unavailable in the recorded missing Phase 2.5 canonical ledger. Do not guess. |
| **DEF-09** | `SOURCE-OBSERVED` + `NEEDS-REPRO` | `DEFERRED` | Definition unavailable in the recorded missing Phase 2.5 canonical ledger. Do not guess. |
| **DEF-10** | `SOURCE-OBSERVED` + `DEFERRED` | `DEFERRED` | Modular decomposition of the ~1.03 MB / ~17k-line `misora.py` was deferred. Cancellation of v1.5.0 removes any implied "after release" date. Future refactor is unscheduled and requires a separate architecture charter. |

## G. Priority Watch — open questions at `3edf43e`

| ID | Evidence | Risk | Note |
|---|---|---|---|
| **F-GPT-07** | `UNVERIFIED` at `3edf43e` | P1 escalation for `T-11` | JP-key drift: If Japanese keys in XUAT files can change between saves (e.g., via speaker edits that alter the original JP text), the stable-key lock `(box_ordinal, sha256(original_jp_text))` used by `.misora` v1 may silently lose lock associations. Unverified — requires source trace of JP key mutation paths before T-11 design. |
| **T-12** | `SOURCE-OBSERVED` | Watch | UI-thread sync at `3edf43e`: Confirm that XUAT disk I/O worker results are marshalled to the UI thread via `queue.Queue` + `after_idle`, not direct Tk calls, per AGENTS.md §6. |

## H. Consensus Roadmap (Planning Order Only — NOT AUTHORIZED)

**Option A** (audit-validated consensus across Gemini, GPT-6, Qwen):

1. **T-08a** — Window position / screen-edge clamp / DPI (source verify + fix)
2. **T-04** — Overflow line-count boundary (verify + fix if needed)
3. **T-03** — All Script highlight orphan cleanup (source verify + fix)
4. **T-08b** — Snapped half-screen layout (source verify + fix)
5. **T-06b** — Close behavior verification + `.misora` Save Project prompt (verify + design)

This is a **planning order only**. Each task requires a separate execution charter with exact baseline, scope, acceptance criteria, independent review, and explicit Project Lead `Proceed`.

## I. Historical and retracted claims

Preserve the full canonical defect ledger, B1–B20, BUG-01..BUG-41, FEAT-01..FEAT-14, HYG-01..HYG-08, NO-01..NO-12, and retracted claims in the verbatim archive + `HISTORY_INDEX.md`. The compact active ledger must not repeat every resolved issue as current work. Keep retractions as `RETRACTED` / `HISTORICAL-REFERENCE`; never reopen without new evidence.

## J. Triage rule

No issue in this ledger authorizes implementation. A new task requires exact baseline, scope, evidence/repro, affected symbols/tests, acceptance criteria, rollback, and explicit Project Lead approval. Track B is unscheduled; "deferred" does not mean automatically queued.
