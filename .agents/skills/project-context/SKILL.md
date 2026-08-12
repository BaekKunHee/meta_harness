---
name: project-context
description: Initialize, refresh, route, and validate evidence-based context for a software repository through its root `.harness/harness.py`. Use when starting or onboarding a service, when manifests, architecture, CI, data boundaries, or canonical commands change, when agent documentation is missing or stale, or when an implementation task needs a small path- or topic-specific context packet. Supports Node/TypeScript, Python, web/API/database, AI, Docker/GitHub, and detected infrastructure profiles without inventing product facts.
---

# Project Context

Build useful repository context from inspected evidence, keep it synchronized, and load only the subset needed for the current task. Treat `.harness/project.json` as the machine-readable source of truth and `.harness/context-map.json` as the routing index.

## Use the repository harness

Run commands from the repository root with Python 3.11 or newer:

```bash
python3 .harness/harness.py scan
python3 .harness/harness.py init
python3 .harness/harness.py init --write
python3 .harness/harness.py refresh
python3 .harness/harness.py refresh --write
python3 .harness/harness.py context
python3 .harness/harness.py check harness
```

Inspect `python3 .harness/harness.py <command> --help` before adding selectors or options not shown above. Do not reimplement detection in ad hoc scripts when the root harness supports it.

## Select the operation

- Use `scan` to inspect stacks, components, manifests, tooling, and risk signals without writing.
- Use `init` for a new or newly adopted service. Run the dry-run first; use `--write` only when repository changes are authorized by the task.
- Use `refresh` after manifest, component, CI, architecture, data-boundary, or canonical-command changes. Preview first, then write only managed regions.
- Use `context` before focused implementation or review. Supply only supported path/topic selectors and keep the returned packet within its 6,000-character contract.
- Use `check harness` for harness integrity, `check affected` for changed components, `check full` for all required project gates, and `check security` for security gates.

## Initialize or refresh

1. Read the closest `AGENTS.md`, then inspect `.harness/project.json` and `.harness/context-map.json` if present.
2. Check Git status and preserve unrelated changes. Never overwrite human-authored content outside explicit managed markers.
3. Run `scan`. Verify important claims against manifests, lockfiles, workspace definitions, tests, CI, containers, schemas/migrations, and relevant source entrypoints.
4. Load only the detected profile references listed below.
5. Classify every generated statement as **Confirmed facts**, **Inferences**, or **User decisions required**. Never promote an inference to a fact.
6. Ask only for material product intent that repository evidence cannot answer: purpose, users, sensitive data, external effects, deployment boundary, or an unresolved high-impact tradeoff.
7. Preview `init` or `refresh`, examine the proposed changes, then apply with `--write` when in scope.
8. Re-run the same write command and require an empty diff from the second run. Run `check harness` and the narrowest relevant project check.

Create a nested `AGENTS.md` only when a real component has materially different commands, ownership, safety boundaries, or conventions. Do not create one merely because a directory exists.

## Route profile references

Read a reference only when `scan` or direct evidence activates the profile:

- Node, TypeScript, JavaScript, workspaces: [references/node-typescript.md](references/node-typescript.md)
- Python applications or packages: [references/python.md](references/python.md)
- Browser UI, HTTP APIs, authentication, databases, or migrations: [references/web-api-db.md](references/web-api-db.md)
- Prompts, models, retrieval, agents, tools, or evals: [references/ai-service.md](references/ai-service.md)
- Docker, Compose, or GitHub Actions: [references/docker-github.md](references/docker-github.md)
- Terraform, Kubernetes, or Helm: [references/infra.md](references/infra.md)

Load multiple references for a mixed repository, but do not load profiles that are only hypothetical.

## Preserve evidence and safety

- Never read `.env` files. From `.env.example`, use variable names only; never copy or print assigned values.
- Exclude secrets, credentials, personal absolute paths, generated artifacts, dependency trees, and caches from generated context.
- Record each validation as `required`, `optional`, or `not_applicable` with a concrete reason. Never silently omit a missing gate.
- Prefer existing repository scripts and lockfile-selected package managers. Do not invent a command because a tool is common for the language.
- Keep production deployment, external communication, real personal data, paid resources, irreversible migrations, and broad deletion behind explicit human confirmation.
- Report repository settings that files cannot enforce—branch rulesets, required checks, CODEOWNERS coverage, and protected production environments—as unresolved setup, not completed work.

## Return a compact result

Report:

1. detected components and active profiles;
2. files or managed regions changed;
3. canonical commands and their validation status;
4. checks run with exact outcomes;
5. inferences, unresolved decisions, and repository-host settings still required.

Do not claim project readiness when a required gate was skipped, unavailable, or failed.
