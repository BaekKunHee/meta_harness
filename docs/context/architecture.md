# Architecture context

Keep this page at the component and dependency level. Detailed implementation
belongs in code; durable architectural choices belong in ADRs.

## Confirmed facts

### Detected repository facts

<!-- harness:managed:start -->
#### Harness-managed facts

- Active profiles: agent-harness, github-actions
- Risk tags: none detected

### Components

- `agent-harness-root` at `.`: agent-harness

### Canonical commands

- `agent-harness-root:agent-evals` (required): `python3 -I -S -B -m unittest discover -s evals/agent -p test_*.py -v`
<!-- harness:managed:end -->

### Human-confirmed facts

- _Add confirmed component responsibilities and dependency boundaries here._

## Inferences

- _Add plausible topology interpretations, their evidence, and how to verify them._

## Decisions needed

- What are the deployable components and their owned responsibilities?
- Which calls are synchronous, asynchronous, or event-driven?
- Where are retry, timeout, idempotency, and consistency boundaries?
- Which shared abstractions are stable contracts rather than implementation convenience?

## Diagram guidance

Add a diagram only when it clarifies three or more components, a stateful flow,
or a non-obvious trust boundary. Keep it consistent with `.harness/project.json`.
