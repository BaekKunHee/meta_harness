# Data and trust context

Describe data classes, trust boundaries, identities, and external effects. Do not
place credentials, personal data, production samples, or secret values here.

## Confirmed facts

### Detected repository facts

<!-- harness:managed:start -->
#### Harness-managed facts

- Active profiles: agent-harness, github-actions
- Risk tags: none detected
- Secret values and `.env` contents are never inventory inputs.
- External, paid, production-data, destructive, and irreversible effects require explicit confirmation.
<!-- harness:managed:end -->

### Human-confirmed facts

- _Add confirmed data classes, owners, retention rules, and authorization boundaries here._

## Inferences

- _Add inferred trust relationships with evidence and a way to verify them._

## Decisions needed

- What sensitive, personal, customer, financial, or regulated data exists?
- Which identity authenticates each request, job, and external integration?
- Where are tenant and authorization checks enforced?
- What are retention, export, correction, and deletion obligations?
- Which actions create external effects, cost, or irreversible state?

## Non-negotiable defaults

- Use synthetic or irreversibly anonymized test data.
- Never copy secret values into context, logs, fixtures, or handoffs.
- Require explicit confirmation before using real data or causing an external effect.
- Test deny paths and cross-tenant access whenever an authorization boundary changes.
