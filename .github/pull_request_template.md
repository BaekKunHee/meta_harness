## Goal

<!-- What user or system outcome does this change deliver? -->

## Change summary

<!-- Describe the smallest meaningful behavior change. Link the issue or decision when one exists. -->

## Risk and contracts

- [ ] Public API or compatibility contract reviewed
- [ ] Authentication, authorization, tenant, and sensitive-data boundaries reviewed
- [ ] Persistent state, migration, idempotency, and rollback behavior reviewed
- [ ] External side effects, production operations, and cost impact reviewed
- [ ] None of the above apply; reason recorded below

<!-- Record applicable risks, mitigations, and any decision that still needs a human. -->

## Verification evidence

<!-- List exact commands and results. For high-risk contracts include happy, negative, conflict/retry, and recovery evidence as applicable. -->

- [ ] `python3 .harness/harness.py check affected`
- [ ] Relevant focused tests
- [ ] Manual or unavailable verification is explained

## Data, rollout, and recovery

<!-- Describe data/migration impact, rollout order, monitoring, and rollback/recovery. Write "Not applicable" when appropriate. -->

## Context and documentation

- [ ] Product, architecture, operations, or decision docs updated where behavior changed
- [ ] Harness context refreshed if manifests, commands, components, or risk boundaries changed
- [ ] No documentation change is needed; reason recorded above

## Human approval gates

<!-- Identify any production deployment, external message, real personal data, paid resource, irreversible migration, or broad destructive action that remains pending explicit approval. -->
