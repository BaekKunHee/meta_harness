# Working agreement

## Inspect and bound the change

- Resolve the requested outcome, affected component, consumers, and risk tags.
- Inspect the real entrypoints, manifests, tests, and current working tree.
- Preserve unrelated user changes; do not reformat or regenerate outside scope.
- Prefer reversible local actions and use dry runs when a tool supports them.

## Implement from the contract

- For a bug, first prove the failure with a focused reproduction.
- For high-risk contracts, follow Red-Green-Refactor and test at the cheapest
  boundary that demonstrates the promise to the consumer.
- For lower-risk wiring, documentation, or tooling, use the smallest meaningful
  existing verification rather than manufacturing a new test ceremony.
- Change durable context and an ADR in the same work when the product contract,
  trust boundary, architecture, or operational policy changes.

High-risk contracts include public APIs, authorization and tenant isolation,
persisted state, payments, security controls, idempotency, lifecycle transitions,
migrations, and irreversible external effects.

Avoid tests that pass because of sleeps, unconstrained retries, private
implementation details, or indiscriminate snapshot updates. There is no global
coverage target; coverage must protect the changed risk.

## Use subagents deliberately

- `explorer`: locate and compare repository evidence without writing.
- `historian`: reconstruct when and why behavior changed from Git history without writing.
- `docs_researcher`: consult authoritative external or internal references without writing.
- `reviewer`: independently inspect a bounded diff for regressions and risk without writing.

The main agent owns all mutations, reconciles conflicting reports, validates
high-severity findings against source, and makes final claims. Parallel work is
for independent questions, not duplicated implementations.

## Verification ladder

1. **Focused**: the smallest test, type check, parser, or reproduction for the change.
2. **Affected**: all required gates for changed components via `scripts/check affected`.
3. **Full**: every required repository gate via `scripts/check full` when integration
   risk, shared contracts, or release scope warrants it.
4. **Security**: `scripts/check security` when a trust boundary, dependency,
   workflow, infrastructure file, or security-sensitive behavior changes.
5. **Release**: migration preview, deployment/rollback readiness, and post-release
   signals when a live change is explicitly authorized.

Report pass, fail, skipped, and unavailable states separately. An unavailable
check is not a pass. A focused green check does not prove full repository health.

## Review findings

Review the defined scope: working tree, staged diff, branch diff, or commit.
Regression review is always required. Add security, migration, test-integrity,
and public-contract lenses when risk tags require them.

Each actionable finding must include severity, precise location, evidence,
user impact, a safe correction, and how to verify it. Leave style to deterministic
format and lint tools unless it creates a real correctness or maintainability risk.
