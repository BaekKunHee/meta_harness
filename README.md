# Agentic Service Harness

A framework-neutral development layer for starting and operating services with
coding agents. It supplies repository context, risk-aware testing, independent
review, deterministic quality gates, and explicit human approval boundaries. It
intentionally contains no application code.

## What this gives a new service

- A concise `AGENTS.md` router instead of one oversized prompt
- Machine-readable component, command, risk, and context inventories
- Progressive context loading for product, architecture, data, testing, and release
- Reusable project-context, product-contract TDD, and change-review skills
- Codex and Claude Code adapters over one canonical working agreement and skill set
- Read-only specialist subagents with main-agent ownership of implementation
- One local/CI verification interface through `scripts/check`
- Safe defaults for secrets, production changes, real data, cost, and destructive work

The deterministic scripts and CI checks are the merge gates. Agent review is
supplemental evidence and is never treated as an automatic pass.

## Bootstrap a service

For a greenfield service, create a repository from this one as a Git-host
template so symlinks and executable bits are preserved. For an existing
service, overlay the files with an archive-aware copier such as `rsync -a`,
preserve its `.git/`, and review conflicts in existing `AGENTS.md`, `CLAUDE.md`,
`.gitignore`, CI, and documentation instead of replacing product-owned content.

Then run from the service root:

```sh
python3 .harness/harness.py scan
python3 .harness/harness.py init
python3 .harness/harness.py init --write
scripts/context
scripts/check harness
```

`init` previews changes by default. Use `--write` only after reviewing the
detected components and commands. The project-context skill should then ask only
for product facts that code cannot reveal: purpose, users, sensitive data,
external effects, and deployment boundaries.

### Agent client adapters

`AGENTS.md` and `.agents/skills/` are the canonical, client-neutral sources.
Codex reads its project configuration from `.codex/`. Claude Code reads
`CLAUDE.md`, which imports `AGENTS.md`, and its adapter from `.claude/`:

- `.claude/settings.json` loads the same bounded harness context at session and
  subagent start;
- `.claude/agents/` defines the read-only explorer, reviewer, and documentation
  researcher;
- each `.claude/skills/<name>` entry is a relative symlink to the matching
  canonical `.agents/skills/<name>` directory.

Do not duplicate or edit skill content through the adapter path. Edit the
canonical `.agents/skills/` source and let both clients consume it. On first use,
review and trust the repository-local settings before allowing hooks to run.
`scripts/check harness` rejects missing, broken, absolute, external, or
misdirected Claude skill links.

After manifests, CI, or component boundaries change, preview and apply a refresh:

```sh
python3 .harness/harness.py refresh
python3 .harness/harness.py refresh --write
```

Generated context updates are limited to explicit
`<!-- harness:managed:start -->` / `<!-- harness:managed:end -->` regions.
The detected Dependabot ecosystems use the equivalent
`# harness:managed:start` / `# harness:managed:end` YAML block. Human-authored
text outside managed regions must remain intact, and repeating a write with
unchanged inputs should produce no diff.

## Daily workflow

1. Start with `AGENTS.md` and load routed context with `scripts/context`.
2. State the product contract and risk before choosing a test boundary.
3. For bugs and high-risk contracts, use Red-Green-Refactor.
4. Implement the smallest coherent change and update durable context or an ADR.
5. Run `scripts/check affected`; use `full` and `security` when their risk applies.
6. Run an independent change review and verify serious findings in the repository.
7. Hand off using the evidence fields in `docs/templates/handoff.md`.

Useful gates:

```sh
scripts/check harness
scripts/check affected
scripts/check full
scripts/check security
```

`security` performs the repository-local secret, personal-path, workflow-policy,
and harness-integrity checks. GitHub's security workflow runs the same gate plus
an OSV lockfile vulnerability scan. When a supported application ecosystem is
detected, `refresh --write` also updates only the managed Dependabot ecosystem
entries.

## Context and source of truth

`.harness/project.json` is the single inventory for components, manifests,
profiles, risk tags, and canonical commands. `.harness/context-map.json` routes a
path or topic to the minimum relevant documents and checks. Product intent and
decisions stay human-readable in `docs/context/` and `docs/decisions/`.

Every context page separates:

- **Confirmed facts**: observed in code/config or explicitly confirmed by a human
- **Inferences**: plausible but unverified interpretations, with their evidence
- **Decisions needed**: choices that materially change the product or risk posture

See `docs/agent/source-of-truth.md` for conflict handling.

## Human approval boundary

Local, reversible development is autonomous. Explicit confirmation is required
immediately before production deployment, external communication, real personal
or production data use, paid resources, privilege expansion, irreversible
migration, broad deletion, or comparable external side effects. More detail is
in `SECURITY.md` and `docs/context/operations-and-release.md`.

## Repository settings still required

Files in this template cannot enforce host-level repository policy. After the
repository is hosted, explicitly configure and verify:

- required status checks and a protected default branch or ruleset
- production environments, reviewers, and scoped deployment secrets
- CODEOWNERS when ownership boundaries are known
- CodeQL and dependency review when supported by the repository and plan

Record incomplete setup as incomplete; do not imply that committed workflow
files enabled these controls.

## Requirements

- macOS or Linux
- Python 3.11 or newer for the harness
- The package managers and runtimes detected for the service itself

Lockfiles and application manifests remain owned by the service. The harness
does not make live AI-provider calls part of the default deterministic gate.

## Design references

- [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  [Skills](https://learn.chatgpt.com/docs/build-skills), and
  [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code memory](https://code.claude.com/docs/en/memory),
  [directory structure](https://code.claude.com/docs/en/claude-directory),
  [skills](https://code.claude.com/docs/en/slash-commands), and
  [hooks](https://code.claude.com/docs/en/hooks)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [GitHub protected branches and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [OSV-Scanner GitHub Actions integration](https://google.github.io/osv-scanner/github-action/)
