---
name: prepare-handoff
description: Convert completed local work into clean commits and an evidence-backed handoff or pull request. Use when a task is ready to hand off, commit, or open for review, or when pausing work that another person or agent will resume. Do not activate in the middle of implementation, for a quick informational answer, or to summarize work whose required checks have not been run.
---

# Prepare Handoff

A handoff is complete when the next person can act on observed evidence instead
of trust. Unverified work is reported as unverified, never rounded up to done.

## Close out the work

1. Check the result against `docs/agent/definition-of-done.md` and the original
   task intent.
2. Rerun the checks the change requires — affected gates at minimum — and record
   the exact commands and observed results.
3. Update durable context or an ADR when the work changed a contract, trust
   boundary, or operational policy.
4. Remove leftover instrumentation, debug output, dead experiments, and stray
   files introduced during the work.

## Shape the change history

1. Review the entire working tree, including untracked files, before staging
   anything.
2. Stage only files that belong to the task. Leave unrelated changes untouched
   and report that they exist.
3. Group the work into coherent commits whose messages state intent and effect,
   not file lists.
4. Never commit secrets, environment files, credentials, or local machine
   configuration.

## Write the handoff

Use `docs/templates/handoff.md`. Separate explicitly:

- completed and verified, with the observed evidence;
- completed but unverified, with the reason verification was unavailable;
- not done, and what remains;
- decisions needed from the owner;
- external settings, deployments, or migrations that were not performed.

When a pull request is requested, derive its description from the same evidence
rather than rewriting reality for reviewers.

## Respect the boundary

Committing locally is reversible and autonomous when the task calls for it.
Pushing, opening a pull request, deploying, migrating, or messaging people are
external effects: perform them only when the task explicitly authorizes them,
and report exactly which were performed and which remain.
