---
name: safe-refactoring
description: Restructure existing code in small verified steps while observable behavior stays identical. Use for renames, extractions, module moves, de-duplication, dead-code removal, dependency inversion, and complexity reduction when external contracts must not change. Do not activate when behavior is intended to change, for a defect fix, or for new functionality; contract-changing work belongs to risk-based TDD.
---

# Safe Refactoring

A refactor is safe only while current behavior is pinned by checks that were
actually run. Structure may change; the observable contract may not.

## Pin current behavior

1. Read the closest `AGENTS.md` and load routed context when the harness is
   available.
2. Identify the observable contract of the code being restructured: its public
   surface, callers, error shapes, ordering, side effects, and the tests that
   cover them.
3. Run the closest existing checks before editing and record the green baseline.
   A refactor started from a red baseline hides its own regressions.
4. If existing coverage cannot distinguish a correct restructuring from a broken
   one, first add a characterization test that captures current behavior —
   including behavior that looks wrong. Capture it; do not fix it here.

## Refactor in small steps

1. Apply one mechanical transformation at a time: rename, extract, inline,
   move, or delete.
2. Keep the tree buildable and the focused checks green after each meaningful
   step.
3. Checkpoint at green states so a failed step can be reverted alone instead of
   unwinding the whole effort.

## Keep behavior frozen

- No drive-by fixes. Record discovered defects or questionable behavior as
  findings for separate work.
- Preserve error shapes, status codes, event payloads, ordering, and side
  effects exactly.
- Do not change public names or signatures unless that change is the requested
  refactor and every consumer has been traced and updated.
- Do not reformat or restructure code outside the requested scope.

## Verify and report

Run affected checks, then broader gates in proportion to how widely the touched
code is consumed. Review the final diff for unintended contract deltas. Report
what was restructured, the evidence that behavior held — baseline versus final
check results — and any deferred findings.
