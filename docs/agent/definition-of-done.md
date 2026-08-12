# Definition of done

A change is done only when every applicable item is satisfied or explicitly
reported as incomplete.

## Product and scope

- The requested outcome and acceptance criteria are met.
- The diff is coherent, minimal, and contains no unrelated user changes.
- Confirmed facts, inferences, and unresolved decisions remain clearly separated.
- Public behavior and compatibility changes are intentional and documented.

## Evidence

- A bug has a failing-before, passing-after reproduction.
- High-risk contracts have meaningful happy, negative, conflict/retry, and
  recovery coverage where those states exist.
- Focused and affected checks pass; full and security gates pass when applicable.
- Test output, commands, and limitations are reported accurately.
- Serious independent-review findings are verified and resolved or explicitly accepted.

## Data, security, and operations

- No secret or real sensitive data is present in the diff, fixtures, logs, or handoff.
- Authorization, tenant, migration, idempotency, and external-effect boundaries
  have been tested when touched.
- Observability, migration, release, and rollback context is updated when behavior changes.
- External side effects have not occurred without the required confirmation.

## Documentation and delivery

- Durable decisions have an ADR; affected context and canonical commands are current.
- Generated inventory has no unexplained drift and repeated refresh is idempotent.
- Unconfigured host controls, unavailable checks, and remaining decisions are named.
- Commit, push, PR, deployment, or external notification occurs only when explicitly requested.
