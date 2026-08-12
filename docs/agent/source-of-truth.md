# Source of truth and conflict handling

Different questions have different authorities. Do not use one total ordering
to hide a real disagreement between intent and implementation.

## Authority by question

### Intended product behavior

1. The user's explicit requirement or confirmed decision for the current task
2. An accepted ADR
3. Human-confirmed facts in `docs/context/`
4. Existing tests and public contracts as evidence of prior intent
5. Inferences, which never become requirements without confirmation

### Current implemented behavior

1. Executable code, schema, migrations, and effective runtime configuration
2. Tests and CI configuration
3. `.harness/project.json` generated inventory
4. Prose documentation

### Components, risks, and canonical commands

`.harness/project.json` is the repository inventory SSOT. Source manifests and
CI remain the underlying evidence. If they diverge, the inventory is stale:
refresh it, inspect the diff, and do not silently pick a convenient command.

### Context routing

`.harness/context-map.json` is the routing SSOT. It chooses what to load; it
does not override the content of the sources it routes to.

## Required labels

Context pages use three labels:

- **Confirmed facts**: directly observed or explicitly confirmed. Include a path,
  command, ADR, or owner/date when practical.
- **Inferences**: interpretations that may guide exploration but not product
  decisions. State the evidence and what would confirm them.
- **Decisions needed**: unresolved choices whose alternatives materially affect
  behavior, safety, compatibility, cost, or rollout.

Generated facts belong only inside explicit harness-managed blocks. Human facts
stay outside those blocks so refreshes cannot overwrite them.

## Conflict protocol

1. Name the conflicting sources and quote or point to the smallest relevant evidence.
2. Distinguish current behavior from intended behavior.
3. Resolve mechanical drift by refreshing generated inventory or documentation.
4. Stop and ask for a decision when resolving the conflict would change product intent,
   public compatibility, data handling, security posture, cost, or release scope.
5. Record durable decisions in an ADR and update affected context after approval.

Never rewrite history to make the sources appear consistent. A documented gap is
safer than a false certainty.
