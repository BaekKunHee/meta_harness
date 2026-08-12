---
name: change-review
description: Review a precisely scoped local or Git change for consequential, evidence-backed defects and missing verification. Use for working-tree, staged, branch, commit, or pull-request reviews; pre-merge risk checks; or focused regression, security, authorization, migration, API-contract, async, dependency, CI, and AI side-effect audits. Return prioritized actionable findings with tight file and line evidence, and keep the review read-only unless the user separately asks for fixes.
---

# Change Review

Find defects that materially affect users, security, data, operations, or compatibility. Treat deterministic checks as merge evidence and AI review as an advisory layer.

## Lock the review scope

1. Resolve the requested target: working tree, staged changes, branch against its merge base, named commit, or pull request.
2. Record the base and head identifiers when available. Do not silently expand a focused review to unrelated repository history.
3. Read the closest `AGENTS.md`; load routed project context when `.harness/harness.py` is available.
4. Inspect Git status before reviewing. Preserve the tree and do not modify files, stage changes, commit, or push.
5. Read the complete diff plus enough surrounding implementation, tests, schemas, and callers to validate behavior.

If the target remains ambiguous after repository inspection, state the concrete ambiguity before reviewing. Never pretend that an uninspected PR or unavailable remote was reviewed.

## Route review lenses

Always check for regressions, error handling, compatibility, and test adequacy. Add focused lenses when the diff contains the corresponding signals:

- authentication, permissions, tenant IDs, secrets, parsing, uploads, URLs, queries, or cryptography: security and trust-boundary review;
- schema, migration, ORM, transaction, cache, or persistent state: data integrity, compatibility, rollback, and concurrency review;
- routes, handlers, serializers, events, SDK types, or CLI output: public-contract and precedence review;
- queues, jobs, locks, webhooks, retries, timeouts, or idempotency keys: duplicate, ordering, retry, and recovery review;
- dependencies, Docker, workflows, permissions, or build scripts: supply-chain and CI behavior review;
- prompts, model settings, retrieval, tools, or agent actions: deterministic eval, untrusted-input, data-boundary, cost, and side-effect review.

Use independent read-only subagents only when lenses can be cleanly partitioned. Re-read the cited code yourself before accepting any high-severity finding.

## Validate candidates

For every suspected defect:

1. Trace a concrete input and execution path from reachable entrypoint to incorrect outcome.
2. Confirm the behavior against tests, schemas, types, callers, or documented contracts.
3. Check whether another guard, transaction, fallback, or invariant prevents the issue.
4. Run the narrowest non-mutating check that can confirm or falsify it when practical.
5. Keep the finding only when it is introduced or exposed by the reviewed change and has a realistic impact.

Do not report style preferences, speculative hardening, pre-existing unrelated defects, or a generic request for more tests. Report missing verification only when a specific changed behavior can regress without coverage.

## Write findings

Read [references/finding-contract.md](references/finding-contract.md) before producing the review. Follow its severity and output schema exactly.

Order findings by severity, then confidence. Use the tightest changed line range that explains the problem even when supporting evidence lives elsewhere. Describe one defect per finding and include a safe correction direction plus a concrete verification method.

If there are no actionable findings, say so explicitly and list only material residual verification gaps. A failed, timed-out, or malformed AI review is a gap, not a passing gate.

Do not implement fixes unless the user explicitly expands the task from review to remediation.
