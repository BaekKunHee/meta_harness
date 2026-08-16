# Agentic Service Working Agreement

This repository is a framework-neutral agentic development layer. It does not
define the product; it defines how agents discover, change, test, review, and
hand off the product safely.

## Start here

1. Read this file.
2. Read `.harness/project.json` for components, risk tags, and canonical commands.
3. Use `.harness/context-map.json` or `scripts/context` to load only task-relevant
   context.
4. Read the relevant files in `docs/context/` and any accepted ADRs.
5. Load a skill from `.agents/skills/` when its trigger matches the task.
6. Read a nested `AGENTS.md` only when working in its subtree.

If generated inventory is missing or stale, run the project-context workflow
before relying on it. Do not invent product facts to fill gaps.

## Repository map

- `.harness/`: machine-readable inventory, context routing, and deterministic gates
- `.agents/skills/`: reusable project-context, TDD, debugging, refactoring,
  dependency-upgrade, review, and handoff workflows
- `.codex/`: Codex project configuration and read-only specialist agents
- `.claude/`: Claude Code settings plus adapters to the canonical rules and skills
- `docs/agent/`: operating rules, source precedence, and definition of done
- `docs/context/`: product, architecture, domain, trust, testing, and release context
- `docs/decisions/`: accepted architecture decision records
- `docs/templates/`: task, handoff, and release/rollback templates
- `scripts/`: stable human and CI entrypoints

## Working protocol

- Inspect before editing. Separate confirmed facts, inferences, and decisions needed.
- Preserve unrelated changes and existing human-authored content.
- Prefer the smallest coherent change that satisfies the product contract.
- Update context or an ADR when a durable contract or decision changes.
- Never claim a check, deployment, or recovery that was not observed.
- When instructions conflict, follow `docs/agent/source-of-truth.md` and surface
  unresolved product choices instead of silently guessing.

## Safety boundary

Agents may autonomously inspect and modify repository files, add local
dependencies, and run local checks when the work is reversible and scoped to
the requested task.

Get explicit confirmation immediately before any production deployment,
external message, use of real personal or production data, paid resource,
privilege expansion, irreversible migration, broad deletion, or other external
side effect. Treat secret files and values as sensitive; do not print, copy into
artifacts, or commit them.

## Risk-based TDD

- Start bug fixes with a failing reproduction.
- Use Red-Green-Refactor for public APIs, authorization or tenant boundaries,
  persisted state, payments, security controls, idempotency, and lifecycle changes.
- For ordinary UI composition, internal wiring, documentation, and tooling, run
  the smallest existing check that proves the affected contract.
- Choose the cheapest meaningful boundary: unit, then integration/API, then a
  focused end-to-end test.
- Do not hide failures with sleeps, broad retries, implementation-detail
  assertions, or snapshot churn. No universal coverage percentage is required.

## Subagents and review

- Use `explorer` for repository evidence, `historian` for Git-history context,
  `docs_researcher` for authoritative references, and `reviewer` for independent
  risk review.
- Specialist agents are read-only. The main agent owns edits, decisions,
  integration, and final claims.
- Parallelize independent questions only. Give each subagent a bounded scope and
  reconcile its result against the actual repository.
- Re-verify every high-severity finding before acting on it. AI review is evidence,
  never the deterministic merge gate.

## Verification and completion

Run checks in proportion to risk: focused checks, affected-component gates,
full required gates, then security or release checks when relevant. Use
`scripts/check` so local and CI behavior stays aligned.

Before handing off, satisfy `docs/agent/definition-of-done.md`. Report exactly
what passed, failed, or was unavailable; note remaining decisions and external
settings. Do not deploy, push, message, or create paid resources unless the task
explicitly authorizes that side effect.
