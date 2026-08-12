# Agent harness evaluations

This directory contains deterministic, standard-library-only contract tests for
the repository harness and machine-readable cases for skill activation checks.
The tests exercise the public CLI against isolated temporary repositories; they
do not call a model, install dependencies, access the network, or use real
credentials.

Run the suite from the repository root:

```bash
python3 -m unittest discover -s evals/agent -p 'test_*.py'
```

The harness contract under test is:

- a common `--root` option and the `scan`, `init`, `refresh`, `context`, and
  `check` commands;
- `init` and `refresh` preview changes unless `--write` is supplied;
- generated inventory lives in `.harness/project.json` and routing in
  `.harness/context-map.json`;
- context packets are routed and never exceed 6,000 characters;
- managed blocks are idempotent and preserve surrounding human text;
- environment files, secret-like values, and personal absolute paths never
  enter generated artifacts;
- the Claude Code adapter imports `AGENTS.md`, loads bounded context, exposes
  read-only subagents, and uses only safe internal relative skill symlinks;
- stale inventory and leaked sensitive material fail deterministic checks.

`skill_activation_cases.json` is evaluation input, not an assertion that a model
was invoked. Each skill has direct, indirect, incomplete, and negative cases so
an external forward-evaluation runner can compare activation decisions without
changing this test suite.

For a release evaluation, give the case file and the three local skill folders
to an independent read-only agent. Record activation and workflow mismatches;
do not turn that advisory model judgment into a deterministic merge pass. Skill
package structure remains covered here, while the installed skill-creator
validator is run separately against each skill during full repository verification.
