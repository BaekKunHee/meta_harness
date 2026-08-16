---
name: systematic-debugging
description: Diagnose a defect to its proven root cause with a reproduction-first, evidence-driven workflow. Use when behavior is wrong and the cause is unknown, including failing or intermittent tests, incorrect output, crashes, regressions, performance cliffs, or environment-dependent behavior. Do not activate when the root cause is already demonstrated, for building new functionality, or for a question answerable by reading code directly.
---

# Systematic Debugging

Find the proven cause before changing production code. One verified observation
outranks any number of plausible theories.

## Reproduce first

1. Read the closest `AGENTS.md` and load routed context when the harness is
   available.
2. Build the cheapest deterministic reproduction: the exact command, input, and
   observed failure output, plus the expected behavior it violates.
3. Record the baseline verbatim. When flakiness is suspected, rerun it several
   times and report the observed failure rate instead of pretending determinism.
4. If no reproduction is possible yet, collect evidence first: logs, failing
   inputs, versions, configuration, and the last known-good state. Do not ship a
   speculative fix for an unreproduced defect; state what evidence is missing.

## Isolate the cause

1. Shrink the reproduction: smaller input, fewer components, and the lowest
   boundary — unit over integration over end-to-end — that still fails.
2. Binary-search the suspect space: the recent diff, commit history, configuration,
   data, and dependency changes. Use the `historian` subagent to establish when
   the behavior changed.
3. Change one variable per experiment, and restore each instrumentation or
   experiment edit before the next. Probes never belong in the final diff.
4. Prefer reading the failing path and adding targeted assertions or logging
   over shotgun edits across the codebase.

## Test one hypothesis at a time

1. State a falsifiable hypothesis and the observation it predicts.
2. Run the smallest experiment that can confirm or kill it.
3. A failed prediction kills the hypothesis, not the evidence. Back out the
   failed attempt before trying the next; do not stack speculative fixes.

## Fix the root cause

1. Fix the cause, not the symptom that made it visible.
2. Keep the reproduction as a regression test when the contract qualifies under
   risk-based TDD; otherwise run the smallest existing check that proves the fix.
3. Search for sibling defects produced by the same mistake pattern.
4. Record latent or unrelated defects discovered along the way as findings
   instead of fixing them silently in the same change.

## Verify and report

Rerun the original reproduction and the affected checks. Report the root cause
with its evidence chain, the fix, the checks run with observed results, and the
remaining unknowns. Never report a defect as fixed without rerunning the
reproduction that proved it.
