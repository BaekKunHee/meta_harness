---
name: product-contract-tdd
description: Apply risk-based test-driven development to observable product contracts. Use when fixing a bug or changing public APIs, authorization or tenant isolation, persistent data, payments, security controls, idempotency, concurrency, lifecycle or state transitions, retries, or recovery behavior. Do not activate for a low-risk documentation edit, visual-only UI assembly, internal wiring, or behavior-preserving tooling change.
---

# Product Contract TDD

Protect consequential behavior with a failing contract test before implementation. Optimize for evidence at the real consumer boundary, not test count or coverage percentage.

## Classify the change

Use Red-Green-Refactor when any of these apply:

- reproduce and fix a defect;
- add or alter a public API, event, CLI, schema, or compatibility promise;
- change authentication, authorization, tenant isolation, sensitive-data handling, payments, or another security boundary;
- change persistent state, a migration contract, idempotency, concurrency, retry semantics, or a lifecycle transition.

For internal wiring, presentational UI, docs, harness work, or behavior-preserving refactors, use the smallest relevant existing checks. Add a new test only when it protects an observable promise or prevents a plausible regression.

## Define the contract

Before editing production code:

1. Read the closest repository instructions and obtain task context from the project harness when available.
2. State the actor or consumer, preconditions, input or trigger, observable result, and durable side effects.
3. Identify the highest-risk negative case and any applicable retry/conflict/recovery behavior.
4. Preserve existing precedence, error shape, status codes, events, and side effects unless the requested contract intentionally changes them.
5. Choose the cheapest test boundary that can distinguish a correct implementation from a plausible wrong one.

Use:

- a unit test for deterministic domain logic with no meaningful boundary behavior;
- an integration or API test for routing, serialization, authorization, persistence, transactions, or service composition;
- a focused end-to-end test only when browser/runtime integration is itself the product promise.

Prefer the real consumer entrypoint over testing a helper that the consumer could bypass.

## Run Red-Green-Refactor

### Red

1. Add one focused test for the contract or defect.
2. Run only that test and observe it fail for the intended behavioral reason.
3. If it passes before the implementation, strengthen or relocate it. If it fails because of setup, repair the test setup before changing production code.

### Green

1. Implement the smallest complete behavior that satisfies the contract.
2. Run the focused test until it passes.
3. Add the minimum high-value cases: one negative boundary plus retry/conflict/recovery only where the contract supports them.

### Refactor

1. Improve structure without changing the proven behavior.
2. Re-run the focused tests after each meaningful refactor.
3. Run affected-component checks, then broader required checks in proportion to risk.

## Protect test integrity

- Do not add arbitrary sleeps, blanket retries, weakened assertions, implementation-detail assertions, or broad snapshot churn to obtain green.
- Do not mock the subject under test or bypass the route, permission check, transaction, or adapter that defines the contract.
- Use deterministic clocks, IDs, fakes, and fixtures. Required gates must not call live AI, payment, email, calendar, or other external providers.
- Assert externally visible output and durable side effects. Also assert forbidden side effects for authorization and failure cases.
- Keep fixtures minimal and avoid sharing mutable state across tests.
- Treat an unavailable environment or flaky dependency as an explicit verification gap, never as a pass.

## Verify and report

Run the repository's canonical commands from `.harness/project.json` when present. Report:

- the contract and why it qualified for test-first work;
- the test boundary selected and why it is the cheapest meaningful one;
- the observed Red failure and Green result;
- affected and full checks run, with exact pass/fail/skip status;
- residual risks or unverified production behavior.

Do not claim the service or deployment is recovered solely because a focused test passes.
