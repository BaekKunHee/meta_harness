---
name: dependency-upgrade
description: Change third-party dependencies with changelog evidence, lockfile integrity, and staged verification. Use for version bumps, security-advisory responses, Dependabot or Renovate pull requests, lockfile conflicts, and adding or removing a package. Do not activate for internal module changes or when a dependency file merely appears unchanged inside a wider diff.
---

# Dependency Upgrade

Treat a dependency change as third-party code crossing the trust boundary.
Evidence comes from changelogs, lockfile diffs, and observed checks — not from
optimism about semantic versioning.

## Assess before changing

1. Read the closest `AGENTS.md`; take manifests and canonical commands from
   `.harness/project.json` when available.
2. Identify the current and target versions from the manifest and lockfile.
3. Read the release notes or changelog between those versions, using the
   `docs_researcher` subagent for authoritative sources. Classify the jump:
   patch, minor, or major; breaking changes; and any security advisory it
   resolves.
4. For a new package, verify the exact name against typosquatting and check
   maintenance signals, the license, and install-time scripts before adding it.

## Upgrade in reviewable units

1. Change one dependency, or one intentionally coupled group, per unit of work.
2. Regenerate the lockfile with the ecosystem's canonical tool. Never hand-edit
   a lockfile.
3. Read the lockfile diff and confirm it matches intent: no unexpected new
   packages, surprise major transitive jumps, or registry changes.

## Migrate deliberately

1. Apply the migration steps the changelog documents, not guessed equivalents.
2. Search the repository for usage of changed or removed APIs and update every
   call site.
3. Treat new deprecation warnings as recorded follow-ups, never as noise to
   silence.

## Verify and report

Run affected checks; run the full gate when a widely consumed dependency
changed, and the security gate for advisories, lockfile integrity, and other
supply-chain-sensitive changes. Report the old and new versions, breaking
changes handled, advisory status, exact check results, and residual risk the
checks cannot observe. Adding a dependency that requires a paid or external
service needs explicit confirmation before any sign-up or provisioning.
