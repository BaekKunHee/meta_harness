# Agent start sequence

Use this sequence at the beginning of a task so context grows only as needed.

1. Read the root `AGENTS.md`.
2. Inspect working-tree state and preserve unrelated changes.
3. Read `.harness/project.json` for the affected component, risks, and commands.
4. Route the task through `.harness/context-map.json` or `scripts/context`.
5. Read only the returned context pages and relevant accepted ADRs.
6. Read a nested `AGENTS.md` only if the affected subtree has genuinely distinct rules.
7. Load the matching skill and define the verification boundary before editing.

## Before implementation

Write a small task brief when the request spans multiple components, contains an
external side effect, changes a durable contract, or is otherwise ambiguous.
Use `docs/templates/task-brief.md`.

Confirm these items from evidence:

- requested outcome and acceptance signal;
- affected component and consumer boundary;
- current behavior, including the failing case for a bug;
- relevant risk tags and approval gates;
- smallest meaningful test and required follow-up gates.

If a product choice cannot be learned from the repository, record it under
**Decisions needed** and ask the owner. Do not turn an inference into a requirement.

## At handoff

Use `docs/agent/definition-of-done.md` and report observed evidence. Separate
completed local work from unperformed deployment, host settings, or external
verification. `docs/templates/handoff.md` provides the expected shape.
