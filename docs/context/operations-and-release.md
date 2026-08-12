# Operations, release, and rollback context

Keep build success, deployment authorization, production health, and recovery as
separate claims. A local green check never proves a live rollout.

## Confirmed facts

### Detected repository facts

<!-- harness:managed:start -->
#### Harness-managed facts

- Active profiles: agent-harness, github-actions
- Risk tags: none detected
- Deployment and rollback details require human confirmation.
- Repository branch rules, required checks, CODEOWNERS, and production environments remain external setup until verified.
<!-- harness:managed:end -->

### Human-confirmed facts

- _Add confirmed environments, owners, release gates, signals, and recovery procedures here._

## Inferences

- _Add inferred operational dependencies with evidence and a verification path._

## Decisions needed

- What environments exist, who owns them, and what requires explicit approval?
- Which artifacts and migrations form one release boundary?
- What pre-deploy checks and post-deploy signals prove success?
- What rollback or roll-forward action is safe for code, schema, and queued work?
- What user impact, alert threshold, or error budget triggers recovery?

## Release evidence contract

Before an authorized release, record the exact artifact, configuration and
migration scope, approval, expected signals, observation window, rollback
trigger, and recovery owner. Afterward report separately:

- build and deterministic check status;
- migration/apply status;
- deployment convergence status;
- health, error, latency, and user-impact observations;
- rollback or follow-up status.

Use `docs/templates/release-and-rollback.md`. Never deploy or mutate production
because a template was filled in; explicit confirmation is still required at
the point of effect.
