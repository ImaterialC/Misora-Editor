# Misora — Project State (Layer 0 Dashboard)

**Last reconciled:** 2026-11-28 DOCS-01 on `v1.4.15`, HEAD `3edf43e11b3479ac6ab1b20adb03a6e6ad8abfcd`  
**Repository:** `ImaterialC/Misora-Editor` · **Branch:** `main`  
**Historical ENV-01 baseline:** `648cb52b0fccda5e46e26eecf90e3f1dbd719a75` (ENV-01 on S11e)  
**Current product version:** `1.4.15` (root `__init__.py` is authoritative)

## 1. Release and roadmap authority

- **v1.5.0 release campaign: CANCELLED.** Release status: **NOT RELEASED**. Version promotion: **NOT AUTHORIZED**.
- Old S12 release audit: **PAUSED / SUPERSEDED**. Do not execute its historical plan as-is.
- Future S15 work proposal: **CANCELLED**. The completed historical milestone `S15 Select Box Both Views + Reserved Lock Slot, Collapsible Left Drawer, Empty State & Batched Multi-Open` (2026-11-25) remains **HISTORICAL-REFERENCE**.
- DOCS-01 is the current authorized documentation/context-hygiene task. It does not authorize product changes, defect fixes, release actions, commits, or pushes.

## 2. Verification baseline (at `3edf43e`)

Monolithic discovery completed cleanly with `countTestCases() == 494` (`486` post-T-01 baseline + `8` in `tests/test_t02_next_tooltip.py`):

| Result | Count |
|---|---:|
| Total tests | 494 |
| PASS | 451 |
| SKIP | 35 |
| FAIL | 6 |
| ERROR | 2 |
| New T-02 regressions | 0 |

**494 is the total discovered/executed count, not 494 passing tests.** The 6 failures and 2 errors are unchanged pre-existing S11e baseline debt: 3 non-fixture hygiene failures + 3 fixture failures and 2 fixture errors in `test_s8b2_memory_guards` (plus 35 fixture skips) due to unavailable `storydata_1001005.unity3d`.

### T-01 (`BUG-UI-EMPTY-STATE-01`) status

- **Automated fix & TDD:** `PASS` (`8	8	misora.py` in `_update_empty_state_visibility()`, `tests/test_t01_empty_state_overlay.py` `11/11 OK`).
- **Windows Manual QA (`M-1..M-12`):** `PASS` (`v1.4.15` @ `33b6f7dc10dcb86b853aa71ab833864eeb843dfa`, Windows 11 `10.0.26100.6725`, `1920x1080`, `125% DPI`, Project Lead).
- **Lifecycle:** `HISTORICAL-REFERENCE` (closed).

### T-02 (`u-08`) status

- **Automated fix & TDD:** `PASS` (`5	5	misora.py` in `lbl_char_overflow` tooltip + 3 docstrings, `tests/test_t02_next_tooltip.py` `8/8 OK`).
- **Windows Manual QA (`M-1..M-4`):** `PASS` (`v1.4.15` @ `3edf43e11b3479ac6ab1b20adb03a6e6ad8abfcd`, Windows 11 `10.0.26100.6725`, `1920x1080` 100% & 125% DPI, Project Lead). M-1/M-2 (tooltip text) confirmed at both DPI scales; M-3 (Next/Prev tooltips unaffected) confirmed; M-4 (label dynamic update) confirmed `54/54d · 1/3L` with red indicator on overflow.
- **Lifecycle:** `HISTORICAL-REFERENCE` (closed). T-02 addressed the stale tooltip/docstring only; it is not the same scope as T-08a (window position/DPI layout).

Three non-fixture test-hygiene failures recorded:
1. `tests/test_phase3_performance_config.py::test_05` — local `misora_config.json` isolation hygiene.
2. `tests/test_s9c_workspace_safety.py::test_04` — default config template contract hygiene.
3. `tests/test_v15_s01_stability_remediation.py::test_probe_8` — hard-coded expected version `1.4.1` conflicts with `1.4.15`.

Fixture-related debt: `tests/test_s8b2_memory_guards.py::test_01..test_05` depend on missing `storydata_1001005.unity3d` (recorded as 3 FAIL + 2 ERROR); 35 fixture-dependent skips are also recorded. Do not invent fixture outcomes or weaken tests.

## 3. Current issue and QA posture

- **T-01:** `HISTORICAL-REFERENCE` (closed). **T-02:** `HISTORICAL-REFERENCE` (closed).
- **T-03:** `CONFIRMED` (Windows 8 reproductions with 4 screenshots) + `ROOT-CAUSE: NEEDS-CODE-VERIFY`. `ACTIVE`.
- **T-04:** `REPORTED` + `NEEDS-REPRO`. `ACTIVE`.
- T-05..T-10 are configuration/UX/UI proposals requiring triage or design sign-off.
- T-11..T-14 are future/unscheduled proposals or deferred work; none is authorized by this dashboard.
- MANUAL-PENDING/revalidation items are tracked in `docs/project/OPEN_ISSUES.md`, including legacy Ribbon Cut/Paste Box checks, S11c/S11d undo/redo and MTL/Box 0 checks, DPI/snapped layout, and Import from XUAT smoke test.
- `Tcl_AsyncDelete` cross-test teardown is a watch item: seen in earlier S11c/S11d runs, while S11e monolithic discovery completed. Do not report it as a current confirmed failure without reproduction.
- DEF-01 single-space sentinel is an accepted/deferred compatibility limitation; do not change without a new decision.
- `tools/generate_symbol_index.py --check` → `CHECK PASS` at `3edf43e`.

## 4. Layer 0 structure

Keep Layer 0 lean: this file plus `AGENTS.md` only. Route deeper questions through `docs/ai/CONTEXT_ROUTER.md`. Detailed issue evidence, decisions, migration proof, symbol navigation, and history belong in on-demand documents. Before replacement, copy old root docs as raw bytes and verify SHA-256 plus byte equality; never add a header/TOC or normalize archives.

Hard size caps: `AGENTS.md` <= 6 KiB (6144 bytes); `PROJECT_STATE.md` <= 15 KiB (15360 bytes). Preferred targets: AGENTS 3–5 KiB; Project State 8–10 KiB. Byte counts, not token estimates, are the acceptance measure.

## 5. Next planned task

**T-08a** (window position / screen-edge clamp / DPI), followed by **T-04** (overflow line-count boundary) — **NOT AUTHORIZED**. A new task requires exact baseline, scope, evidence/repro, affected symbols/tests, acceptance criteria, rollback, and explicit Project Lead approval.
