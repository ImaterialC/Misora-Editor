# Misora Editor — AI Engineering Workflow

## Purpose

This document defines the repeatable workflow for AI-assisted engineering in Misora Editor. Its purpose is to make each task self-contained in the repository so that execution does not depend on recovering instructions from an earlier chat.

## Repository authority

Read these sources in this order before every engineering task:

1. `AGENTS.md` — permanent architecture, safety, and engineering invariants. Do not duplicate or casually rewrite these rules.
2. `PROJECT_STATE.md` — canonical current state, confirmed defects, design invariants, retractions, roadmap, and measured verification history.
3. The current task brief under `docs/copilot-prompts/` — exact task scope, allowed files, implementation requirements, tests, stop conditions, and deliverables.
4. Source files and tests on the current checkout — the actual code is authoritative over any historical prose.

If these sources conflict, do not silently reconcile them. Explain the conflict and stop before risky edits. Never treat an old AI transcript or a historical prompt pack as more authoritative than the current source tree.

## Project workflow phases

- **Phase 0 — Independent research and audit:** inspect the current repository and identify candidate issues. Do not modify code.
- **Phase 1 — Cross-review and decision:** compare findings, challenge assumptions, classify confirmed versus conditional claims, and obtain the user's decision. Do not implement code.
- **Phase 2 — Prompt engineering:** produce a bounded, testable engineering brief for each approved slice. Cross-review the prompt, resolve objections, and save the final approved prompt in `docs/copilot-prompts/`. A prompt is not final until its scope, allowed files, acceptance tests, verification commands, and stop conditions are explicit.
- **Phase 3 — Copilot execution:** run only the approved prompt in GitHub Copilot Desktop against the verified local checkout. Copilot performs the work; it must not silently continue into later slices.
- **Post-execution review:** inspect the changed files and diff, verify test claims against actual output, check scope and data integrity, and record only verified results in `PROJECT_STATE.md`. Obtain user approval before the next engineering slice.

## Required behavior for each engineering prompt

Every task brief must specify:

- The problem and evidence from the current source tree.
- Dependencies and prerequisite gates.
- Exact allowed files and forbidden files.
- Required behavior and explicit out-of-scope behavior.
- Regression tests, including expected behavior before and after the fix where meaningful.
- Exact verification commands and honest handling of unavailable dependencies or fixtures.
- Data-preservation and rollback constraints.
- Required delivery report and a clear stop condition.

Prefer a single coherent execution brief over a chain of vague chat instructions. Use task-specific prompts only after they have been cross-reviewed and approved.

## Local execution policy

- Expected local repository: `D:\Misora-Editor`.
- Use GitHub Copilot Desktop with the **This computer** environment and **Current checkout** workspace.
- At the start of a task, verify the working directory, Git root, remote, branch, HEAD, and working-tree status.
- Do not work in an automatically generated Copilot worktree when the approved task requires the existing local checkout.
- Keep tool permissions interactive. Review terminal commands and file writes before approving them.
- Do not commit or push unless the user explicitly requests it.

## Language and reporting

- Engineering guides, issue descriptions, test names, and Copilot prompts should be written in English.
- User-facing explanations and operational walkthroughs may be in Indonesian.
- Report actual results. Distinguish automated tests, manual Windows checks, conditional fixture tests, and unverified assumptions.

## Current execution target

The approved engineering task prompt for the staged open-file safety work is:

`docs/copilot-prompts/PHASE2_S0_S1.md`

Read that complete brief and execute it exactly. It contains S0 preflight and S1 implementation requirements. Complete S0 before touching `misora.py`. Stop only when an explicit stop condition in the task brief is reached, or after S0+S1 verification and delivery. Do not start S2 or any later slice without explicit user approval.
