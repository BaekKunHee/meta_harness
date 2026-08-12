# Docker and GitHub Actions profile

Load this reference when Docker/Compose files or GitHub Actions workflows are present.

## Docker and Compose

- Inspect every active `Dockerfile*`, Compose file, ignore file, entrypoint, health check, build context, and CI invocation.
- Record build/test commands only when their context, target, and required build arguments are known.
- Flag root containers, copied secrets, mutable base tags, missing ignore coverage, unsafe health checks, and development-only mounts as review concerns; do not silently rewrite them during context discovery.
- Never connect a required check to a Compose service that needs production credentials or external state.

## GitHub Actions

- Derive canonical CI commands from actual job steps and compare them with `.harness/project.json` for drift.
- Require least-privilege `permissions`, bounded `timeout-minutes`, and concurrency cancellation where appropriate.
- Record whether third-party actions are pinned to full commit SHAs. Do not claim a tag or branch is immutable.
- Treat untrusted pull-request data, script interpolation, caches, artifacts, OIDC, and secret-bearing jobs as trust boundaries.
- Keep local `scripts/check` and CI on the same harness command rather than maintaining two validation definitions.

Record branch rulesets, required checks, CODEOWNERS, repository secrets, and protected environments as external repository settings unless verified through an authorized source. Files alone do not prove those controls are enabled.
