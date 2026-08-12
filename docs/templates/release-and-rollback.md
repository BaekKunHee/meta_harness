# Release and rollback plan: Title

Completing this document does not authorize a deployment. Obtain explicit
confirmation immediately before changing a production or shared live system.

## Release identity

- Environment and owner:
- Commit, image digest, package, or artifact:
- Configuration change:
- Migration version and ordering:
- Approval and release window:

## Preconditions

- Required deterministic checks:
- Dependency and migration compatibility:
- Backup or recovery prerequisite:
- Capacity, feature flag, and external dependency readiness:

## Apply sequence

1. _Small, observable step._
2. _Migration or compatibility step._
3. _Traffic or feature exposure step._

## Success signals

- Deployment convergence:
- Health and readiness:
- Error, latency, saturation, and queue signals:
- User-visible or business contract check:
- Observation window and owner:

## Stop and rollback triggers

- Trigger thresholds:
- Latest safe decision point:
- Who can call rollback:

## Recovery path

- Code or artifact rollback:
- Schema/data rollback or roll-forward:
- Queue, event, cache, or external-effect reconciliation:
- User communication approval and owner:

## Final evidence

- Applied state:
- Observed signals and timestamps:
- Rollback/follow-up status:
- Unverified or unavailable checks:
