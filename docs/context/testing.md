# Testing context

Map product risks to the cheapest tests that prove the consumer-facing contract.
Do not impose a repository-wide coverage percentage.

## Confirmed facts

### Detected repository facts

<!-- harness:managed:start -->
#### Harness-managed facts

- Active profiles: agent-harness, github-actions
- Risk tags: none detected

### Activated validations

- `agent-harness-root:agent-evals` (required): `python3 -I -S -B -m unittest discover -s evals/agent -p test_*.py -v`
<!-- harness:managed:end -->

### Human-confirmed facts

- _Add confirmed critical journeys, fixtures, environments, and known test constraints here._

## Inferences

- _Add inferred gaps or flaky boundaries with evidence and a confirmation path._

## Decisions needed

- Which product promises are high risk and at what boundary are they cheapest to prove?
- Which tests are unit, integration/API, component, and focused end-to-end?
- How are time, randomness, queues, external APIs, and concurrent writes controlled?
- Which checks are required, optional, or not applicable, and why?

## Risk-based policy

- Bugs start with a failing reproduction.
- Public API, auth, tenant, persisted-state, payment, security, idempotency,
  lifecycle, and migration changes use Red-Green-Refactor.
- Cover happy and deny/invalid paths; add retry/conflict and recovery cases when
  the contract has those states.
- Default gates must be deterministic and must not call live AI providers.
- Sleeps, broad retries, private-detail assertions, and snapshot churn are not fixes.
