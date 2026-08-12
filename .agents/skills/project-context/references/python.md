# Python profile

Load this reference only when repository evidence contains a Python application or package.

## Detect

- Inspect `pyproject.toml` first, then `uv.lock`, `poetry.lock`, `Pipfile.lock`, `requirements*.txt`, `setup.cfg`, or `setup.py`.
- Select the environment and package workflow from committed configuration and lockfiles. Do not assume Poetry, uv, pip, Ruff, mypy, Pyright, or pytest merely because they are common.
- Detect applications and packages from configured entrypoints, framework configuration, source layout, and tests rather than directory names alone.

## Select canonical commands

Prefer project-defined scripts and CI commands. When the repository uses the tool, choose the matching environment prefix—for example `uv run`, `poetry run`, or the repository's virtual-environment wrapper.

For reproducible setup, use only a workflow supported by committed files:

- uv lockfile: `uv sync --frozen`
- Poetry lockfile: use the repository's documented non-updating install command
- hashed requirements: install with the repository's hash-enforcing command

Plain requirements without hashes are not a fully locked supply-chain gate; record that limitation.

## Record gates and context

- Connect configured format-check, lint, type-check, test, integration, and build commands.
- Treat a tool category with no configuration or dependency as missing/optional or not applicable with a reason; do not add a new tool during context discovery.
- Route API, database, task-worker, and AI details to their dedicated profiles when detected.
- Record supported Python version from configuration or CI. If sources disagree, flag drift instead of selecting one.

Exclude virtual environments, caches, coverage output, distributions, generated code, credentials, and environment values from generated context.
