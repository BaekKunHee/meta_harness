#!/usr/bin/env python3
"""Portable, standard-library-only service development harness.

The harness deliberately separates observed repository facts from product claims.
It never reads .env files and only records variable names from .env.example files.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - compatibility for OS wrapper Python
    tomllib = None  # type: ignore[assignment]


SCHEMA_VERSION = "1.0"
MAX_CONTEXT_CHARS = 6000
MANAGED_START = "<!-- harness:managed:start -->"
MANAGED_END = "<!-- harness:managed:end -->"
YAML_MANAGED_START = "# harness:managed:start"
YAML_MANAGED_END = "# harness:managed:end"

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".output",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "coverage",
    "dist",
    "build",
    "target",
}

# These are valid repository assets, but their prose/source must not activate a
# runtime profile. This prevents tests, docs, and agent instructions from being
# mistaken for application code.
RUNTIME_SOURCE_EXCLUDED = IGNORED_DIRECTORIES | {
    ".agents",
    ".claude",
    ".codex",
    ".github",
    ".harness",
    "docs",
    "evals",
    "tests",
    "test",
    "fixtures",
    "examples",
}

TEXT_SUFFIXES = {
    ".cjs",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".tf",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

PROFILE_ORDER = [
    "agent-harness",
    "node",
    "typescript",
    "python",
    "web",
    "api",
    "database",
    "ai",
    "docker",
    "github-actions",
    "terraform",
    "kubernetes",
    "infra",
]

RISK_ORDER = [
    "public-contract",
    "authorization",
    "persistent-data",
    "migration",
    "nondeterminism",
    "paid-provider",
    "external-effect",
    "container-runtime",
    "infrastructure",
]

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\b"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9/+_.-]{16,}"
    ),
)
PERSONAL_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home)/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._~@+-]+)+"
)


def _relative(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        return "<outside-repository>"
    return value or "."


def _is_ignored(path: Path, root: Path, exclusions: set[str] = IGNORED_DIRECTORIES) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in exclusions for part in parts)


def _safe_files(root: Path, *, runtime_only: bool = False) -> Iterable[Path]:
    exclusions = RUNTIME_SOURCE_EXCLUDED if runtime_only else IGNORED_DIRECTORIES
    try:
        candidates = root.rglob("*")
    except OSError:
        return
    for path in candidates:
        if _is_ignored(path, root, exclusions):
            continue
        try:
            if path.is_symlink() or not path.is_file():
                continue
        except OSError:
            continue
        yield path


def _contained_path(root: Path, path: Path) -> bool:
    """Return whether a resolved path stays within the resolved repository."""
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _safe_regular_file(root: Path, path: Path) -> bool:
    """Return whether path is a non-symlinked file contained by the repository."""
    try:
        return not path.is_symlink() and path.is_file() and _contained_path(root, path)
    except OSError:
        return False


def _safe_directory(root: Path, path: Path) -> bool:
    """Return whether path is a non-symlinked directory inside the repository."""
    try:
        return not path.is_symlink() and path.is_dir() and _contained_path(root, path)
    except OSError:
        return False


def _repository_path(root: Path, relative: str) -> Path | None:
    candidate_value = Path(relative)
    if candidate_value.is_absolute() or ".." in candidate_value.parts:
        return None
    candidate = root / candidate_value
    return candidate if _contained_path(root, candidate) else None


def _safe_write_target(root: Path, relative: str) -> Path | None:
    candidate = _repository_path(root, relative)
    if candidate is None:
        return None
    try:
        relative_parts = candidate.relative_to(root).parts
    except ValueError:
        return None
    current = root
    for part in relative_parts:
        current = current / part
        try:
            if current.is_symlink():
                return None
        except OSError:
            return None
    return candidate


def _read_text(path: Path, limit: int = 1_000_000) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _read_toml(path: Path) -> dict[str, Any] | None:
    if tomllib is None:
        # Python 3.11+ is the supported runtime. This conservative fallback keeps
        # wrapper diagnostics useful on older OS-provided Python installations;
        # it extracts dependency names only and never evaluates TOML values.
        text = _read_text(path)
        if text is None:
            return None
        dependencies: list[str] = []
        for match in re.finditer(r"(?ms)^dependencies\s*=\s*\[(.*?)\]", text):
            dependencies.extend(
                item[1:-1]
                for item in re.findall(r"['\"][^'\"]+['\"]", match.group(1))
            )
        tool_names = {
            match.group(1).split(".", 1)[0]: {}
            for match in re.finditer(r"(?m)^\[tool\.([A-Za-z0-9_.-]+)\]\s*$", text)
        }
        return {"project": {"dependencies": dependencies}, "tool": tool_names}
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(65_536):
                digest.update(chunk)
    except OSError:
        return "unreadable"
    return digest.hexdigest()


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _component_id(kind: str, relative_root: str) -> str:
    location = "root" if relative_root == "." else relative_root
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", location).strip("-").lower()
    return f"{kind}-{normalized or 'root'}"


def _dependency_names(pyproject: dict[str, Any]) -> set[str]:
    dependencies: list[str] = []
    project = pyproject.get("project")
    if isinstance(project, dict):
        raw = project.get("dependencies", [])
        if isinstance(raw, list):
            dependencies.extend(str(item) for item in raw)
    groups = pyproject.get("dependency-groups")
    if isinstance(groups, dict):
        for raw in groups.values():
            if isinstance(raw, list):
                dependencies.extend(str(item) for item in raw)
    tool = pyproject.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            for section in (poetry.get("dependencies"), poetry.get("dev-dependencies")):
                if isinstance(section, dict):
                    dependencies.extend(str(name) for name in section)
    names: set[str] = set()
    for dependency in dependencies:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", dependency)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def _node_dependencies(package: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for section_name in ("dependencies", "devDependencies", "peerDependencies"):
        section = package.get(section_name)
        if isinstance(section, dict):
            names.update(str(name).lower() for name in section)
    return names


def _node_manager(
    package: dict[str, Any], directory: Path, root: Path
) -> tuple[str, list[str], Path | None]:
    declared = str(package.get("packageManager", "")).split("@", 1)[0].lower()
    ancestors: list[Path] = []
    current = directory.resolve()
    resolved_root = root.resolve()
    while _contained_path(resolved_root, current):
        ancestors.append(current)
        if current == resolved_root:
            break
        current = current.parent
    lock_names = {
        "pnpm": ("pnpm-lock.yaml",),
        "yarn": ("yarn.lock",),
        "bun": ("bun.lockb", "bun.lock"),
        "npm": ("package-lock.json", "npm-shrinkwrap.json"),
    }
    discovered: dict[str, Path] = {}
    for ancestor in ancestors:
        for manager_name, names in lock_names.items():
            if manager_name in discovered:
                continue
            match = next((ancestor / name for name in names if (ancestor / name).is_file()), None)
            if match is not None:
                discovered[manager_name] = match
        if not declared:
            parent_package = _read_json(ancestor / "package.json")
            parent_declared = (
                str(parent_package.get("packageManager", "")).split("@", 1)[0].lower()
                if parent_package
                else ""
            )
            if parent_declared in lock_names:
                declared = parent_declared
    if declared in {"pnpm", "yarn", "npm", "bun"}:
        manager = declared
    elif discovered:
        manager = next(
            name for name in ("pnpm", "yarn", "bun", "npm") if name in discovered
        )
    elif any((ancestor / "pnpm-workspace.yaml").is_file() for ancestor in ancestors):
        manager = "pnpm"
    else:
        manager = "npm"
    installs = {
        "pnpm": ["pnpm", "install", "--frozen-lockfile"],
        "yarn": ["yarn", "install", "--immutable"],
        "bun": ["bun", "install", "--frozen-lockfile"],
        "npm": ["npm", "ci"],
    }
    return manager, installs[manager], discovered.get(manager)


def _command(
    command_id: str,
    *,
    argv: Sequence[str] | None,
    cwd: str,
    status: str,
    category: str,
    component: str,
    reason: str = "",
) -> tuple[str, dict[str, Any]]:
    value: dict[str, Any] = {
        "status": status,
        "category": category,
        "component": component,
        "cwd": cwd,
    }
    if argv:
        value["argv"] = list(argv)
    if reason:
        value["reason"] = reason
    if status == "not_applicable" and not reason:
        value["reason"] = "No repository evidence activates this validation."
    return command_id, value


def _runtime_source_evidence(root: Path) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {"ai": [], "auth": [], "external": []}
    ai_patterns = (
        re.compile(r"\b(?:OpenAI|Anthropic|AsyncOpenAI|AsyncAnthropic)\s*\("),
        re.compile(r"\b(?:responses|chat\.completions|messages)\.create\s*\("),
        re.compile(r"\b(?:generateContent|invoke_model|converse)\s*\("),
    )
    auth_pattern = re.compile(
        r"(?i)\b(?:authorization|oauth|jwt|tenant[_-]?id|permission|current_user)\b"
    )
    external_pattern = re.compile(
        r"(?i)\b(?:send_email|send_message|webhook|stripe\.|slack\.|publish\()"
    )
    runtime_suffixes = {
        ".cjs", ".go", ".java", ".js", ".jsx", ".mjs", ".py", ".rb",
        ".rs", ".swift", ".ts", ".tsx",
    }
    for path in _safe_files(root, runtime_only=True):
        if path.suffix.lower() not in runtime_suffixes:
            continue
        text = _read_text(path, limit=500_000)
        if text is None:
            continue
        relative = _relative(path, root)
        if any(pattern.search(text) for pattern in ai_patterns):
            evidence["ai"].append(relative)
        if auth_pattern.search(text):
            evidence["auth"].append(relative)
        if external_pattern.search(text):
            evidence["external"].append(relative)
    return {key: sorted(set(values)) for key, values in evidence.items()}


def scan_repository(root: Path) -> dict[str, Any]:
    """Return deterministic, value-safe repository facts."""
    root = root.resolve()
    manifests: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    commands: dict[str, dict[str, Any]] = {}
    profile_evidence: dict[str, set[str]] = {}
    risk_evidence: dict[str, set[str]] = {}

    def profile(name: str, evidence: str) -> None:
        profile_evidence.setdefault(name, set()).add(evidence)

    def risk(name: str, evidence: str) -> None:
        risk_evidence.setdefault(name, set()).add(evidence)

    package_paths = sorted(
        path
        for path in _safe_files(root)
        if path.name == "package.json"
        and not _is_ignored(path, root, RUNTIME_SOURCE_EXCLUDED)
    )
    pyproject_paths = sorted(
        path
        for path in _safe_files(root)
        if path.name == "pyproject.toml"
        and not _is_ignored(path, root, RUNTIME_SOURCE_EXCLUDED)
    )
    python_manifest_paths = sorted(
        path
        for path in _safe_files(root)
        if not _is_ignored(path, root, RUNTIME_SOURCE_EXCLUDED)
        and (
            fnmatch.fnmatch(path.name, "requirements*.txt")
            or path.name in {"Pipfile", "Pipfile.lock", "setup.cfg", "setup.py"}
        )
        and path.parent not in {item.parent for item in pyproject_paths}
    )

    for path in package_paths:
        package = _read_json(path)
        if package is None:
            continue
        directory = path.parent
        relative_root = _relative(directory, root)
        component_id = _component_id("node", relative_root)
        dependencies = _node_dependencies(package)
        manager, install_argv, lockfile = _node_manager(package, directory, root)
        has_lockfile = lockfile is not None
        component_profiles = {"node"}
        profile("node", _relative(path, root))
        typescript_config = any(directory.glob("tsconfig*.json"))
        typescript_source = any(
            source.suffix.lower() in {".ts", ".tsx"}
            and not _is_ignored(source, directory, RUNTIME_SOURCE_EXCLUDED)
            for source in _safe_files(directory, runtime_only=True)
        )
        if "typescript" in dependencies or typescript_config or typescript_source:
            component_profiles.add("typescript")
            profile("typescript", _relative(path, root))
        if dependencies & {"next", "react", "vue", "nuxt", "svelte", "@sveltejs/kit"}:
            component_profiles.add("web")
            profile("web", _relative(path, root))
        if dependencies & {"express", "fastify", "hono", "koa", "@nestjs/core"}:
            component_profiles.add("api")
            profile("api", _relative(path, root))
            risk("public-contract", _relative(path, root))
        if dependencies & {
            "prisma",
            "@prisma/client",
            "typeorm",
            "sequelize",
            "drizzle-orm",
            "pg",
        }:
            component_profiles.add("database")
            profile("database", _relative(path, root))
            risk("persistent-data", _relative(path, root))
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        command_prefix = component_id
        command_id, value = _command(
            f"{command_prefix}:install",
            argv=install_argv,
            cwd=_relative(lockfile.parent, root) if lockfile is not None else relative_root,
            status="required" if has_lockfile else "not_applicable",
            category="install",
            component=component_id,
            reason=(
                "Frozen installation is activated by the detected lockfile."
                if has_lockfile
                else f"No {manager} lockfile was detected; create one before relying on CI."
            ),
        )
        commands[command_id] = value
        script_categories = (
            (("format:check", "format-check", "check:format"), "format"),
            (("lint",), "lint"),
            (("typecheck", "type-check", "check:types"), "typecheck"),
            (("test:unit", "unit"), "unit"),
            (("test:integration", "integration", "test:api"), "integration"),
            (("test:e2e", "e2e"), "e2e"),
            (("test",), "test"),
            (("build",), "build"),
        )
        seen_scripts: set[str] = set()
        for candidates, category in script_categories:
            selected = next(
                (name for name in candidates if name in scripts and name not in seen_scripts),
                None,
            )
            if selected is None:
                continue
            seen_scripts.add(selected)
            argv = [manager, "run", selected]
            command_id, value = _command(
                f"{command_prefix}:{category}",
                argv=argv,
                cwd=relative_root,
                status="required",
                category=category,
                component=component_id,
            )
            value["source"] = f"package.json#scripts.{selected}"
            commands[command_id] = value
        for category in ("format", "lint", "typecheck", "unit", "integration", "e2e", "test", "build"):
            command_id = f"{component_id}:{category}"
            if command_id in commands:
                continue
            _, value = _command(
                command_id,
                argv=None,
                cwd=relative_root,
                status="not_applicable",
                category=category,
                component=component_id,
                reason=f"No canonical package script was detected for {category}.",
            )
            commands[command_id] = value
        manifests.append(
            {
                "path": _relative(path, root),
                "kind": "node",
                "component": component_id,
                "sha256": _sha256_file(path),
                "package_manager": manager,
            }
        )
        if lockfile is not None:
            manifests.append(
                {
                    "path": _relative(lockfile, root),
                    "kind": "node-lockfile",
                    "component": component_id,
                    "sha256": _sha256_file(lockfile),
                    "package_manager": manager,
                }
            )
        components.append(
            {
                "id": component_id,
                "path": relative_root,
                "kind": "node",
                "profiles": sorted(component_profiles),
                "manifests": [
                    _relative(item, root)
                    for item in (path, lockfile)
                    if item is not None
                ],
                "validations": sorted(
                    key for key in commands if key.startswith(f"{command_prefix}:")
                ),
            }
        )

    # Conservative adapters for Python repositories without pyproject.toml.
    # They activate only commands proven by manifest content or tool config.
    python_manifests_by_directory: dict[Path, list[Path]] = {}
    for path in python_manifest_paths:
        python_manifests_by_directory.setdefault(path.parent, []).append(path)
    for directory, paths in sorted(python_manifests_by_directory.items()):
        relative_root = _relative(directory, root)
        component_id = _component_id("python", relative_root)
        manifest_names = {_relative(path, root) for path in paths}
        dependency_text = "\n".join(
            (_read_text(path, limit=250_000) or "")
            for path in paths
            if path.name != "Pipfile.lock"
        ).lower()
        package_manager = "pipenv" if any(path.name == "Pipfile.lock" for path in paths) else "pip"
        profile("python", sorted(manifest_names)[0])
        component_profiles = {"python"}
        if re.search(r"(?m)^\s*(?:fastapi|flask|django|litestar|starlette)(?:\b|[<>=])", dependency_text):
            component_profiles.add("api")
            profile("api", sorted(manifest_names)[0])
            risk("public-contract", sorted(manifest_names)[0])
        if re.search(r"(?m)^\s*(?:sqlalchemy|alembic|psycopg|asyncpg)(?:\b|[<>=])", dependency_text):
            component_profiles.add("database")
            profile("database", sorted(manifest_names)[0])
            risk("persistent-data", sorted(manifest_names)[0])
        if package_manager == "pipenv":
            install_argv = ["pipenv", "sync", "--dev"]
        else:
            requirement = next(
                (path for path in paths if fnmatch.fnmatch(path.name, "requirements*.txt")),
                None,
            )
            install_argv = (
                ["python3", "-m", "pip", "install", "-r", requirement.name]
                if requirement is not None
                else ["python3", "-m", "pip", "install", "-e", ".[dev]"]
            )
        command_id, value = _command(
            f"{component_id}:install",
            argv=install_argv,
            cwd=relative_root,
            status="required",
            category="install",
            component=component_id,
            reason="Install from the detected Python manifest before validation.",
        )
        commands[command_id] = value
        for tool_name, category, argv in (
            ("ruff", "lint", ["python3", "-m", "ruff", "check", "."]),
            ("mypy", "typecheck", ["python3", "-m", "mypy", "."]),
            ("pytest", "test", ["python3", "-m", "pytest"]),
        ):
            if not re.search(rf"(?m)^\s*{tool_name}(?:\b|[<>=])", dependency_text):
                continue
            command_id, value = _command(
                f"{component_id}:{category}",
                argv=(
                    ["pipenv", "run", *argv[2:]]
                    if package_manager == "pipenv"
                    else argv
                ),
                cwd=relative_root,
                status="required",
                category=category,
                component=component_id,
            )
            commands[command_id] = value
        for category in ("format", "lint", "typecheck", "test", "integration", "build"):
            command_id = f"{component_id}:{category}"
            if command_id in commands:
                continue
            _, value = _command(
                command_id,
                argv=None,
                cwd=relative_root,
                status="not_applicable",
                category=category,
                component=component_id,
                reason=f"No declared Python tool activates {category} validation.",
            )
            commands[command_id] = value
        for path in paths:
            manifests.append(
                {
                    "path": _relative(path, root),
                    "kind": "python",
                    "component": component_id,
                    "sha256": _sha256_file(path),
                    "package_manager": package_manager,
                }
            )
        components.append(
            {
                "id": component_id,
                "path": relative_root,
                "kind": "python",
                "profiles": sorted(component_profiles),
                "manifests": sorted(manifest_names),
                "validations": sorted(
                    key for key in commands if key.startswith(f"{component_id}:")
                ),
            }
        )

    for path in pyproject_paths:
        pyproject = _read_toml(path)
        if pyproject is None:
            continue
        directory = path.parent
        relative_root = _relative(directory, root)
        component_id = _component_id("python", relative_root)
        dependencies = _dependency_names(pyproject)
        tool = pyproject.get("tool") if isinstance(pyproject.get("tool"), dict) else {}
        component_profiles = {"python"}
        profile("python", _relative(path, root))
        if dependencies & {"fastapi", "flask", "django", "litestar", "starlette"}:
            component_profiles.add("api")
            profile("api", _relative(path, root))
            risk("public-contract", _relative(path, root))
        if dependencies & {
            "sqlalchemy",
            "alembic",
            "django",
            "psycopg",
            "psycopg2",
            "asyncpg",
        } or (directory / "alembic.ini").is_file():
            component_profiles.add("database")
            profile("database", _relative(path, root))
            risk("persistent-data", _relative(path, root))
        runner: list[str]
        install_argv: list[str]
        package_manager: str
        if (directory / "uv.lock").is_file():
            package_manager = "uv"
            runner = ["uv", "run"]
            install_argv = ["uv", "sync", "--frozen"]
        elif (directory / "poetry.lock").is_file():
            package_manager = "poetry"
            runner = ["poetry", "run"]
            install_argv = ["poetry", "install", "--no-interaction"]
        else:
            package_manager = "pip"
            runner = ["python3", "-m"]
            install_argv = ["python3", "-m", "pip", "install", "-e", ".[dev]"]
        command_id, value = _command(
            f"{component_id}:install",
            argv=install_argv,
            cwd=relative_root,
            status="required" if package_manager in {"uv", "poetry"} else "optional",
            category="install",
            component=component_id,
            reason=(
                "Install the locked environment before stack validations."
                if package_manager in {"uv", "poetry"}
                else "No supported Python lockfile was detected; review the pip install target before using it."
            ),
        )
        commands[command_id] = value
        if "ruff" in dependencies or "ruff" in tool:
            for category, args in (
                ("format", ["ruff", "format", "--check", "."]),
                ("lint", ["ruff", "check", "."]),
            ):
                command_id, value = _command(
                    f"{component_id}:{category}",
                    argv=runner + args,
                    cwd=relative_root,
                    status="required",
                    category=category,
                    component=component_id,
                )
                commands[command_id] = value
        type_checker = "mypy" if "mypy" in dependencies or "mypy" in tool else None
        if type_checker:
            command_id, value = _command(
                f"{component_id}:typecheck",
                argv=runner + [type_checker, "."],
                cwd=relative_root,
                status="required",
                category="typecheck",
                component=component_id,
            )
            commands[command_id] = value
        pytest_active = "pytest" in dependencies or "pytest" in tool
        if pytest_active:
            pytest_argv = runner + ["pytest"]
            command_id, value = _command(
                f"{component_id}:test",
                argv=pytest_argv,
                cwd=relative_root,
                status="required",
                category="test",
                component=component_id,
            )
            commands[command_id] = value
        for category in ("format", "lint", "typecheck", "test", "integration", "build"):
            command_id = f"{component_id}:{category}"
            if command_id in commands:
                continue
            _, value = _command(
                command_id,
                argv=None,
                cwd=relative_root,
                status="not_applicable",
                category=category,
                component=component_id,
                reason=f"No declared Python tool activates {category} validation.",
            )
            commands[command_id] = value
        manifests.append(
            {
                "path": _relative(path, root),
                "kind": "python",
                "component": component_id,
                "sha256": _sha256_file(path),
                "package_manager": package_manager,
            }
        )
        python_lockfile = next(
            (
                candidate
                for candidate in (directory / "uv.lock", directory / "poetry.lock")
                if candidate.is_file()
            ),
            None,
        )
        if python_lockfile is not None:
            manifests.append(
                {
                    "path": _relative(python_lockfile, root),
                    "kind": "python-lockfile",
                    "component": component_id,
                    "sha256": _sha256_file(python_lockfile),
                    "package_manager": package_manager,
                }
            )
        components.append(
            {
                "id": component_id,
                "path": relative_root,
                "kind": "python",
                "profiles": sorted(component_profiles),
                "manifests": [
                    _relative(item, root)
                    for item in (path, python_lockfile)
                    if item is not None
                ],
                "validations": sorted(
                    key for key in commands if key.startswith(f"{component_id}:")
                ),
            }
        )

    # The boilerplate verifies itself as a first-class component. These paths
    # are intentionally explicit so fixture prose cannot activate the profile.
    harness_entrypoint = root / ".harness/harness.py"
    harness_eval = root / "evals/agent/test_harness_contract.py"
    if _safe_regular_file(root, harness_entrypoint) and _safe_regular_file(
        root, harness_eval
    ):
        component_id = "agent-harness-root"
        control_paths: list[Path] = [harness_entrypoint]
        for pattern in (
            ".harness/schemas/*.json",
            ".agents/skills/*/SKILL.md",
            ".agents/skills/*/agents/openai.yaml",
            ".claude/settings.json",
            ".claude/hooks/*.py",
            ".claude/agents/*.md",
            ".codex/*.json",
            ".codex/*.toml",
            ".codex/agents/*.toml",
            "evals/agent/*.py",
            "evals/agent/*.json",
            "scripts/*",
        ):
            control_paths.extend(
                path
                for path in root.glob(pattern)
                if _safe_regular_file(root, path)
            )
        claude_skill_links = [
            root / ".claude/skills" / skill_name
            for skill_name in sorted(
                path.parent.name
                for path in root.glob(".agents/skills/*/SKILL.md")
                if _safe_regular_file(root, path)
            )
            if (root / ".claude/skills" / skill_name).is_symlink()
        ]
        relative_controls = sorted(
            {
                *(_relative(path, root) for path in control_paths),
                *(_relative(path, root) for path in claude_skill_links),
            }
        )
        profile("agent-harness", ".harness/harness.py")
        for path in sorted(set(control_paths)):
            manifests.append(
                {
                    "path": _relative(path, root),
                    "kind": "harness-control",
                    "component": component_id,
                    "sha256": _sha256_file(path),
                }
            )
        for path in sorted(claude_skill_links):
            link_target = os.readlink(path)
            expected_target = f"../../.agents/skills/{path.name}"
            manifests.append(
                {
                    "path": _relative(path, root),
                    "kind": "harness-control-symlink",
                    "component": component_id,
                    "sha256": hashlib.sha256(link_target.encode("utf-8")).hexdigest(),
                    "target": (
                        link_target if link_target == expected_target else "<invalid>"
                    ),
                }
            )
        command_id, value = _command(
            f"{component_id}:agent-evals",
            argv=[
                "python3",
                "-I",
                "-S",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "evals/agent",
                "-p",
                "test_*.py",
                "-v",
            ],
            cwd=".",
            status="required",
            category="test",
            component=component_id,
        )
        commands[command_id] = value
        components.append(
            {
                "id": component_id,
                "path": ".",
                "kind": "agent-harness",
                "profiles": ["agent-harness"],
                "manifests": relative_controls,
                "impact_paths": [
                    ".harness/**",
                    ".agents/skills/**",
                    ".claude/**",
                    ".codex/**",
                    ".github/**",
                    "evals/agent/**",
                    "scripts/**",
                    "AGENTS.md",
                    "CLAUDE.md",
                    "README.md",
                    "SECURITY.md",
                    "docs/agent/**",
                ],
                "validations": [command_id],
            }
        )

    # Non-language manifests and their hashes are repository facts too.
    special_files: list[tuple[Path, str]] = []
    for path in _safe_files(root):
        relative = _relative(path, root)
        lower_name = path.name.lower()
        if lower_name in {"dockerfile", "compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"}:
            special_files.append((path, "docker"))
            profile("docker", relative)
            risk("container-runtime", relative)
        elif path.suffix == ".tf":
            special_files.append((path, "terraform"))
            profile("terraform", relative)
            profile("infra", relative)
            risk("infrastructure", relative)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            text = _read_text(path, limit=250_000) or ""
            if re.search(r"(?m)^kind:\s*(?:Deployment|StatefulSet|DaemonSet|Job|CronJob)\s*$", text):
                special_files.append((path, "kubernetes"))
                profile("kubernetes", relative)
                profile("infra", relative)
                risk("infrastructure", relative)
        if relative.startswith(".github/workflows/") and path.suffix.lower() in {".yaml", ".yml"}:
            special_files.append((path, "github-actions"))
            profile("github-actions", relative)
    seen_special: set[str] = set()
    for path, kind in sorted(special_files, key=lambda item: (_relative(item[0], root), item[1])):
        key = f"{_relative(path, root)}:{kind}"
        if key in seen_special:
            continue
        seen_special.add(key)
        manifests.append(
            {
                "path": _relative(path, root),
                "kind": kind,
                "sha256": _sha256_file(path),
            }
        )

    source_evidence = _runtime_source_evidence(root)
    if source_evidence["ai"]:
        for evidence in source_evidence["ai"]:
            profile("ai", evidence)
        risk("nondeterminism", source_evidence["ai"][0])
        risk("paid-provider", source_evidence["ai"][0])
    if source_evidence["auth"]:
        risk("authorization", source_evidence["auth"][0])
    if source_evidence["external"]:
        risk("external-effect", source_evidence["external"][0])

    migration_files = [
        path
        for path in _safe_files(root, runtime_only=True)
        if "migration" in {part.lower() for part in path.parts}
        or "migrations" in {part.lower() for part in path.parts}
        or path.name.lower().startswith("alembic")
    ]
    if migration_files:
        evidence = _relative(sorted(migration_files)[0], root)
        profile("database", evidence)
        risk("persistent-data", evidence)
        risk("migration", evidence)

    environment_variables: list[str] = []
    for path in _safe_files(root):
        if path.name not in {".env.example", ".env.sample"}:
            continue
        text = _read_text(path, limit=100_000)
        if text is None:
            continue
        for line in text.splitlines():
            match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if match:
                environment_variables.append(match.group(1))

    # Explicitly classify high-risk adapters even when the repository has not
    # yet provided a deterministic command. This prevents silent "not tested"
    # states from looking like successful coverage.
    active_names = set(profile_evidence)
    adapter_expectations = (
        ("api-contract", "api", "No deterministic API contract command was detected."),
        ("authorization", "api", "No deterministic authorization boundary command was detected."),
        ("migration", "database", "No deterministic migration validation command was detected."),
        ("agent-eval", "ai", "No deterministic provider-free agent eval command was detected."),
        ("container", "docker", "No deterministic container build or scan command was detected."),
        ("infrastructure", "infra", "No deterministic infrastructure validation command was detected."),
    )
    for category, required_profile, reason in adapter_expectations:
        if required_profile not in active_names:
            continue
        command_id, value = _command(
            f"adapter:{category}",
            argv=None,
            cwd=".",
            status="not_applicable",
            category=category,
            component="repository",
            reason=reason,
        )
        commands.setdefault(command_id, value)

    profiles = [
        {"id": name, "active": True, "evidence": sorted(profile_evidence[name])}
        for name in PROFILE_ORDER
        if name in profile_evidence
    ]
    profiles.extend(
        {"id": name, "active": True, "evidence": sorted(values)}
        for name, values in sorted(profile_evidence.items())
        if name not in PROFILE_ORDER
    )
    risks = [
        {"id": name, "active": True, "evidence": sorted(risk_evidence[name])}
        for name in RISK_ORDER
        if name in risk_evidence
    ]
    risks.extend(
        {"id": name, "active": True, "evidence": sorted(values)}
        for name, values in sorted(risk_evidence.items())
        if name not in RISK_ORDER
    )
    manifests.sort(key=lambda item: (str(item.get("path")), str(item.get("kind"))))
    components.sort(key=lambda item: str(item.get("id")))
    commands = {key: commands[key] for key in sorted(commands)}
    facts: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "components": components,
        "manifests": manifests,
        "profiles": profiles,
        "risk_tags": risks,
        "commands": commands,
        "environment_variables": sorted(set(environment_variables)),
    }
    facts["source_fingerprint"] = _stable_digest(facts)
    return facts


def build_project(root: Path) -> dict[str, Any]:
    scan = scan_repository(root)
    return {
        **scan,
        "generated_by": "agentic-service-harness",
        "safety_boundary": {
            "local_reversible_work": "autonomous",
            "external_or_irreversible_effects": "explicit_confirmation_required",
        },
    }


def build_context_map(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "agentic-service-harness",
        "source_fingerprint": project["source_fingerprint"],
        "defaults": {
            "documents": [
                "docs/agent/start-here.md",
                "docs/agent/source-of-truth.md",
                "docs/context/architecture.md",
                "docs/context/data-and-trust.md",
                "docs/context/testing.md",
            ],
            "checks": ["harness", "affected"],
            "review_lenses": ["regression", "test-integrity"],
        },
        "routes": [
            {
                "id": "testing",
                "topics": ["test", "testing", "tdd", "contract", "regression"],
                "paths": ["app/**", "src/**", "services/**", "packages/**", "tests/**"],
                "documents": ["docs/context/testing.md"],
                "checks": ["affected", "full"],
                "review_lenses": ["regression", "test-integrity", "public-contract"],
            },
            {
                "id": "product",
                "topics": ["product", "user", "behavior", "scope"],
                "paths": ["app/**", "src/**", "apps/**"],
                "documents": ["docs/context/product.md", "docs/context/domain.md"],
                "checks": ["affected"],
                "review_lenses": ["product-contract", "regression"],
            },
            {
                "id": "architecture",
                "topics": ["architecture", "component", "dependency", "api"],
                "paths": ["app/**", "src/**", "apps/**", "services/**", "packages/**"],
                "documents": ["docs/context/architecture.md", "docs/context/domain.md"],
                "checks": ["harness", "affected"],
                "review_lenses": ["regression", "public-contract"],
            },
            {
                "id": "data-and-trust",
                "topics": ["security", "auth", "authorization", "data", "database", "migration", "ai"],
                "paths": ["**/migrations/**", "**/auth/**", "infra/**", "deploy/**"],
                "documents": ["docs/context/data-and-trust.md", "SECURITY.md"],
                "checks": ["security", "full"],
                "review_lenses": ["security", "authorization", "migration", "privacy"],
            },
            {
                "id": "operations",
                "topics": ["operations", "release", "deploy", "rollback", "docker", "infra"],
                "paths": [".github/**", "infra/**", "deploy/**", "Dockerfile", "**/Dockerfile"],
                "documents": ["docs/context/operations-and-release.md"],
                "checks": ["full", "security"],
                "review_lenses": ["operability", "rollback", "security"],
            },
        ],
    }


def _profile_ids(project: dict[str, Any]) -> list[str]:
    return [
        str(item.get("id"))
        for item in project.get("profiles", [])
        if isinstance(item, dict) and item.get("active", True)
    ]


def _risk_ids(project: dict[str, Any]) -> list[str]:
    return [
        str(item.get("id"))
        for item in project.get("risk_tags", [])
        if isinstance(item, dict) and item.get("active", True)
    ]


def _managed_sections(project: dict[str, Any]) -> dict[str, str]:
    profiles = _profile_ids(project)
    risks = _risk_ids(project)
    components = project.get("components", [])
    commands = project.get("commands", {})
    component_lines = [
        f"- `{item.get('id')}` at `{item.get('path')}`: {', '.join(item.get('profiles', [])) or 'no active runtime profile'}"
        for item in components
        if isinstance(item, dict)
    ] or ["- No application component has been detected yet."]
    command_lines = [
        f"- `{command_id}` ({value.get('status')}): `{' '.join(value.get('argv', []))}`"
        for command_id, value in commands.items()
        if isinstance(value, dict)
    ] or ["- No stack-specific command has been activated yet."]
    shared_facts = [
        "#### Harness-managed facts",
        "",
        f"- Active profiles: {', '.join(profiles) if profiles else 'none detected'}",
        f"- Risk tags: {', '.join(risks) if risks else 'none detected'}",
    ]
    return {
        "docs/context/product.md": "\n".join(
            shared_facts
            + [
                "- Repository scanning cannot confirm users, product purpose, or desired outcomes.",
                "- Record those product facts in the human-owned section after confirmation.",
            ]
        ),
        "docs/context/architecture.md": "\n".join(
            shared_facts
            + ["", "### Components", "", *component_lines, "", "### Canonical commands", "", *command_lines]
        ),
        "docs/context/domain.md": "\n".join(
            shared_facts
            + [
                "- Domain entities and lifecycle rules are not inferred from filenames.",
                "- Confirm public contracts and state transitions before documenting them here.",
            ]
        ),
        "docs/context/data-and-trust.md": "\n".join(
            shared_facts
            + [
                "- Secret values and `.env` contents are never inventory inputs.",
                "- External, paid, production-data, destructive, and irreversible effects require explicit confirmation.",
            ]
        ),
        "docs/context/testing.md": "\n".join(
            shared_facts
            + ["", "### Activated validations", "", *command_lines]
        ),
        "docs/context/operations-and-release.md": "\n".join(
            shared_facts
            + [
                "- Deployment and rollback details require human confirmation.",
                "- Repository branch rules, required checks, CODEOWNERS, and production environments remain external setup until verified.",
            ]
        ),
    }


def _replace_managed_block(
    original: str,
    replacement: str,
    *,
    start_marker: str = MANAGED_START,
    end_marker: str = MANAGED_END,
) -> str:
    start_count = original.count(start_marker)
    end_count = original.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise ValueError("expected exactly one managed start and end marker")
    start = original.index(start_marker) + len(start_marker)
    end = original.index(end_marker)
    if end < start:
        raise ValueError("managed end marker occurs before start marker")
    return original[:start] + "\n" + replacement.rstrip() + "\n" + original[end:]


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _dependabot_block(project: dict[str, Any]) -> str:
    ecosystems: set[tuple[str, str]] = {("github-actions", "/")}
    for component in project.get("components", []):
        if not isinstance(component, dict):
            continue
        path = str(component.get("path", "."))
        directory = "/" if path == "." else f"/{path.strip('/')}"
        kind = component.get("kind")
        if kind == "node":
            ecosystems.add(("npm", directory))
        elif kind == "python":
            ecosystems.add(("pip", directory))
    for manifest in project.get("manifests", []):
        if not isinstance(manifest, dict):
            continue
        kind = str(manifest.get("kind", ""))
        relative = Path(str(manifest.get("path", "")))
        directory = "/" if str(relative.parent) == "." else f"/{relative.parent.as_posix()}"
        if kind == "docker":
            ecosystems.add(("docker", directory))
        elif kind == "terraform":
            ecosystems.add(("terraform", directory))
    lines = ["updates:"]
    for ecosystem, directory in sorted(ecosystems):
        lines.extend(
            [
                f"  - package-ecosystem: {ecosystem}",
                f'    directory: "{directory}"',
                "    schedule:",
                "      interval: weekly",
                "      day: monday",
                '      time: "12:17"',
                "      timezone: Asia/Seoul",
                "    open-pull-requests-limit: 5",
            ]
        )
    return "\n".join(lines)


def desired_files(root: Path) -> tuple[dict[str, str], list[str]]:
    project = build_project(root)
    context_map = build_context_map(project)
    desired = {
        ".harness/project.json": _json_text(project),
        ".harness/context-map.json": _json_text(context_map),
    }
    errors: list[str] = []
    for relative, replacement in _managed_sections(project).items():
        path = _safe_write_target(root, relative)
        if path is None:
            errors.append(f"{relative}: unsafe symlink or out-of-repository target")
            continue
        if not path.is_file():
            continue
        original = _read_text(path)
        if original is None:
            errors.append(f"{relative}: unreadable managed document")
            continue
        try:
            desired[relative] = _replace_managed_block(original, replacement)
        except ValueError as error:
            errors.append(f"{relative}: {error}")
    dependabot_relative = ".github/dependabot.yml"
    dependabot_path = _safe_write_target(root, dependabot_relative)
    if dependabot_path is None:
        errors.append(f"{dependabot_relative}: unsafe symlink or out-of-repository target")
    elif dependabot_path.is_file():
        original = _read_text(dependabot_path)
        if original is None:
            errors.append(f"{dependabot_relative}: unreadable managed configuration")
        elif YAML_MANAGED_START in original or YAML_MANAGED_END in original:
            try:
                desired[dependabot_relative] = _replace_managed_block(
                    original,
                    _dependabot_block(project),
                    start_marker=YAML_MANAGED_START,
                    end_marker=YAML_MANAGED_END,
                )
            except ValueError as error:
                errors.append(f"{dependabot_relative}: {error}")
    return desired, errors


def _write_if_changed(root: Path, relative: str, content: str) -> bool:
    path = _safe_write_target(root, relative)
    if path is None:
        raise ValueError(f"unsafe write target: {relative}")
    current = _read_text(path) if path.is_file() else None
    if current == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def run_generation(root: Path, operation: str, write: bool) -> int:
    desired, errors = desired_files(root)
    changes: list[str] = []
    for relative, content in desired.items():
        target = _safe_write_target(root, relative)
        if target is None:
            errors.append(f"{relative}: unsafe symlink or out-of-repository target")
            continue
        if not target.is_file() or _read_text(target) != content:
            changes.append(relative)
    written: list[str] = []
    if write and not errors:
        for relative in changes:
            try:
                if _write_if_changed(root, relative, desired[relative]):
                    written.append(relative)
            except ValueError as error:
                errors.append(str(error))
    payload = {
        "operation": operation,
        "mode": "write" if write else "dry-run",
        "changes": changes,
        "written": written,
        "errors": errors,
    }
    print(_json_text(payload), end="")
    return 1 if errors else 0


def _load_json_object(path: Path) -> dict[str, Any] | None:
    return _read_json(path)


def _validate_project(project: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, expected_type in (
        ("components", list),
        ("manifests", list),
        ("profiles", list),
        ("risk_tags", list),
        ("commands", dict),
    ):
        if not isinstance(project.get(key), expected_type):
            errors.append(f"project.json: {key} must be {expected_type.__name__}")
    commands = project.get("commands", {})
    if isinstance(commands, dict):
        for command_id, command in commands.items():
            if not isinstance(command, dict):
                errors.append(f"project.json: command {command_id} must be an object")
                continue
            status = command.get("status")
            if status not in {"required", "optional", "not_applicable"}:
                errors.append(f"project.json: command {command_id} has invalid status")
            if status == "not_applicable" and not str(command.get("reason", "")).strip():
                errors.append(f"project.json: command {command_id} needs a reason")
            argv = command.get("argv")
            if argv is not None and (
                not isinstance(argv, list) or not all(isinstance(item, str) for item in argv)
            ):
                errors.append(f"project.json: command {command_id} argv must be a string array")
    return errors


def _validate_context_map(context_map: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(context_map.get("defaults"), dict):
        errors.append("context-map.json: defaults must be an object")
    routes = context_map.get("routes")
    if not isinstance(routes, list):
        errors.append("context-map.json: routes must be an array")
    else:
        for index, route in enumerate(routes):
            if not isinstance(route, dict):
                errors.append(f"context-map.json: route {index} must be an object")
                continue
            for key in ("id", "topics", "paths", "documents"):
                if key not in route:
                    errors.append(f"context-map.json: route {index} missing {key}")
    return errors


def _validate_meta_assets(root: Path) -> list[str]:
    """Validate shipped control-plane assets without third-party packages."""
    if not _safe_regular_file(root, root / ".harness/harness.py"):
        return []
    errors: list[str] = []
    for relative in (
        ".harness/schemas/project.schema.json",
        ".harness/schemas/context-map.schema.json",
        "scripts/check",
        "scripts/context",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/settings.json",
        ".claude/hooks/context.py",
        ".claude/agents/explorer.md",
        ".claude/agents/reviewer.md",
        ".claude/agents/docs-researcher.md",
        ".codex/config.toml",
        ".codex/hooks.json",
        ".codex/agents/explorer.toml",
        ".codex/agents/reviewer.toml",
        ".codex/agents/docs-researcher.toml",
    ):
        if not _safe_regular_file(root, root / relative):
            errors.append(f"required harness asset is missing: {relative}")
    for relative in (
        ".harness/schemas/project.schema.json",
        ".harness/schemas/context-map.schema.json",
        ".claude/settings.json",
        ".codex/hooks.json",
    ):
        path = root / relative
        if _safe_regular_file(root, path) and _read_json(path) is None:
            errors.append(f"required JSON object is invalid: {relative}")

    claude_entrypoint_path = root / "CLAUDE.md"
    claude_entrypoint = (
        _read_text(claude_entrypoint_path)
        if _safe_regular_file(root, claude_entrypoint_path)
        else None
    )
    if claude_entrypoint is not None and not re.search(
        r"(?m)^\s*@AGENTS\.md\s*$", claude_entrypoint
    ):
        errors.append("CLAUDE.md must import the canonical AGENTS.md with @AGENTS.md")

    claude_skills_directory = root / ".claude/skills"
    if not _safe_directory(root, claude_skills_directory):
        errors.append("Claude skills directory must be a repository-local directory")

    claude_settings_path = root / ".claude/settings.json"
    claude_settings = (
        _read_json(claude_settings_path)
        if _safe_regular_file(root, claude_settings_path)
        else None
    )
    if claude_settings is not None:
        hooks = claude_settings.get("hooks")
        if not isinstance(hooks, dict):
            errors.append("Claude settings hooks must be an object")
        else:
            expected_hook_argument = "${CLAUDE_PROJECT_DIR}/.claude/hooks/context.py"
            for event_name in ("SessionStart", "SubagentStart"):
                groups = hooks.get(event_name)
                handlers = (
                    [
                        handler
                        for group in groups
                        if isinstance(group, dict)
                        and isinstance(group.get("hooks"), list)
                        for handler in group["hooks"]
                        if isinstance(handler, dict)
                    ]
                    if isinstance(groups, list)
                    else []
                )
                if not any(
                    handler.get("type") == "command"
                    and handler.get("command") == "python3"
                    and isinstance(handler.get("args"), list)
                    and expected_hook_argument in handler["args"]
                    for handler in handlers
                ):
                    errors.append(
                        f"Claude settings must load bounded context on {event_name}"
                    )

    claude_hook_path = root / ".claude/hooks/context.py"
    claude_hook = (
        _read_text(claude_hook_path)
        if _safe_regular_file(root, claude_hook_path)
        else None
    )
    if claude_hook is not None:
        try:
            compile(claude_hook, ".claude/hooks/context.py", "exec")
        except SyntaxError:
            errors.append("Claude context hook has invalid Python syntax")

    for agent_path in sorted(root.glob(".claude/agents/*.md")):
        agent_name = agent_path.stem
        agent_text = (
            _read_text(agent_path) if _safe_regular_file(root, agent_path) else None
        )
        if agent_text is None:
            continue
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", agent_text, re.DOTALL)
        frontmatter = match.group(1) if match else ""
        if not match or not re.search(
            rf"(?m)^name:\s*{re.escape(agent_name)}\s*$", frontmatter
        ):
            errors.append(f"Claude subagent frontmatter name is invalid: {agent_name}")
        if not match or not re.search(r"(?m)^description:\s*\S", frontmatter):
            errors.append(f"Claude subagent description is missing: {agent_name}")
        if not re.search(r"(?m)^model:\s*inherit\s*$", frontmatter):
            errors.append(f"Claude subagent must inherit the selected model: {agent_name}")
        if not re.search(r"(?m)^permissionMode:\s*plan\s*$", frontmatter):
            errors.append(f"Claude subagent must remain read-only: {agent_name}")
        tools_match = re.search(r"(?m)^tools:\s*(.+)$", frontmatter)
        if not tools_match or any(
            tool in {item.strip() for item in tools_match.group(1).split(",")}
            for tool in ("Write", "Edit", "NotebookEdit")
        ):
            errors.append(f"Claude subagent tools are not read-only: {agent_name}")

    for relative in ("scripts/check", "scripts/context"):
        path = root / relative
        if _safe_regular_file(root, path) and not os.access(path, os.X_OK):
            errors.append(f"shell entrypoint is not executable: {relative}")
    required_skill_names = ("project-context", "product-contract-tdd", "change-review")
    discovered_skill_names = {
        path.parent.name
        for path in root.glob(".agents/skills/*/SKILL.md")
        if _safe_regular_file(root, path)
    }
    for skill_name in sorted({*required_skill_names, *discovered_skill_names}):
        skill_path = root / ".agents/skills" / skill_name / "SKILL.md"
        metadata_path = root / ".agents/skills" / skill_name / "agents/openai.yaml"
        skill_text = (
            _read_text(skill_path) if _safe_regular_file(root, skill_path) else None
        )
        if skill_text is None:
            errors.append(f"required skill is missing: .agents/skills/{skill_name}/SKILL.md")
        else:
            match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", skill_text, re.DOTALL)
            if not match or not re.search(
                rf"(?m)^name:\s*{re.escape(skill_name)}\s*$", match.group(1)
            ):
                errors.append(f"skill frontmatter name is invalid: {skill_name}")
            if not match or not re.search(r"(?m)^description:\s*\S", match.group(1)):
                errors.append(f"skill frontmatter description is missing: {skill_name}")
        metadata = (
            _read_text(metadata_path)
            if _safe_regular_file(root, metadata_path)
            else None
        )
        if metadata is None or "display_name:" not in metadata or "default_prompt:" not in metadata:
            errors.append(f"skill UI metadata is invalid: {skill_name}")

        claude_skill = root / ".claude/skills" / skill_name
        expected = root / ".agents/skills" / skill_name
        expected_target = f"../../.agents/skills/{skill_name}"
        if not _safe_directory(root, claude_skills_directory):
            continue
        if not claude_skill.is_symlink():
            errors.append(f"required Claude skill symlink is missing: {skill_name}")
            continue
        try:
            target = os.readlink(claude_skill)
            resolved = claude_skill.resolve(strict=True)
            expected_resolved = expected.resolve(strict=True)
        except (OSError, RuntimeError):
            errors.append(f"Claude skill symlink is broken or unsafe: {skill_name}")
            continue
        if Path(target).is_absolute() or target != expected_target:
            errors.append(f"Claude skill symlink target is invalid: {skill_name}")
        if not _contained_path(root, resolved) or resolved != expected_resolved:
            errors.append(f"Claude skill symlink leaves its canonical skill: {skill_name}")
    return errors


def check_harness(root: Path, *, quiet: bool = False) -> tuple[bool, list[str]]:
    desired, generation_errors = desired_files(root)
    errors = list(generation_errors)
    project_path = root / ".harness/project.json"
    context_path = root / ".harness/context-map.json"
    project = _load_json_object(project_path)
    context_map = _load_json_object(context_path)
    if project is None:
        errors.append("drift: .harness/project.json is missing or invalid")
    else:
        errors.extend(_validate_project(project))
    if context_map is None:
        errors.append("drift: .harness/context-map.json is missing or invalid")
    else:
        errors.extend(_validate_context_map(context_map))
    errors.extend(_validate_meta_assets(root))
    for relative, expected in desired.items():
        target = _safe_write_target(root, relative)
        if target is None:
            errors.append(f"unsafe symlink or out-of-repository target: {relative}")
            continue
        actual = _read_text(target) if target.is_file() else None
        if actual != expected:
            errors.append(f"drift: {relative} is out of date; run `scripts/check` after `harness.py refresh --write`")
    errors = sorted(set(errors))
    if not quiet:
        if errors:
            print("Harness gate: FAIL")
            for error in errors:
                print(f"- {error}")
        else:
            print("Harness gate: PASS")
    return not errors, errors


def _security_candidate(path: Path, root: Path) -> bool:
    relative = _relative(path, root)
    if _is_ignored(path, root):
        return False
    if path.name.startswith(".env"):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        "AGENTS.md",
        "CLAUDE.md",
        "Dockerfile",
    }


def _workflow_findings(root: Path) -> list[str]:
    findings: list[str] = []
    workflow_dir = root / ".github/workflows"
    if not workflow_dir.is_dir():
        return findings
    for path in sorted(workflow_dir.glob("*.y*ml")):
        text = _read_text(path) or ""
        relative = _relative(path, root)
        if not re.search(r"(?m)^permissions:\s*(?:\{\}|read-all|$)", text):
            findings.append(f"workflow permissions missing or not least-privilege: {relative}")
        if re.search(r"(?m)^\s+[A-Za-z][A-Za-z0-9-]*:\s*write\s*$", text):
            findings.append(f"workflow grants write permission and needs explicit review: {relative}")
        if "timeout-minutes:" not in text:
            findings.append(f"workflow timeout missing: {relative}")
        for match in re.finditer(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", text):
            reference = match.group(1).strip("'\"")
            if reference.startswith("./"):
                continue
            revision = reference.rsplit("@", 1)[-1] if "@" in reference else ""
            if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
                findings.append(f"workflow action is not pinned to a full commit SHA: {relative}")
    return findings


def check_security(root: Path, *, quiet: bool = False) -> tuple[bool, list[str]]:
    findings: list[str] = []
    for path in _safe_files(root):
        if not _security_candidate(path, root):
            continue
        text = _read_text(path, limit=2_000_000)
        if text is None:
            continue
        relative = _relative(path, root)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                findings.append(f"secret or credential pattern: {relative}:{line_number}")
            if PERSONAL_PATH_PATTERN.search(line):
                findings.append(f"personal absolute path: {relative}:{line_number}")
    findings.extend(_workflow_findings(root))
    findings = sorted(set(findings))
    if not quiet:
        if findings:
            print("Security gate: FAIL")
            for finding in findings:
                print(f"- {finding}")
        else:
            print("Security gate: PASS")
    return not findings, findings


def _git_ref_exists(root: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    return result.returncode == 0


def _changed_paths(
    root: Path,
    *,
    base: str | None = None,
    head: str = "HEAD",
) -> list[str] | None:
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if inside.returncode != 0:
        return None
    commands = (
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    )
    changed: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            changed.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    comparison_base = base or os.environ.get("HARNESS_BASE_SHA") or os.environ.get("GITHUB_BASE_SHA")
    if comparison_base and not _git_ref_exists(root, comparison_base):
        print("Affected gate: FAIL (the requested base ref is unavailable)", file=sys.stderr)
        return None
    if not comparison_base:
        for candidate in ("refs/remotes/origin/main", "refs/remotes/origin/master", "main", "master"):
            if not _git_ref_exists(root, candidate):
                continue
            same = subprocess.run(
                ["git", "rev-parse", candidate, head],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            revisions = [line for line in same.stdout.splitlines() if line]
            if same.returncode == 0 and len(revisions) == 2 and revisions[0] != revisions[1]:
                comparison_base = candidate
                break
    if not comparison_base and _git_ref_exists(root, f"{head}^"):
        comparison_base = f"{head}^"
    if comparison_base and _git_ref_exists(root, head):
        separator = "..." if not comparison_base.endswith("^") else ".."
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{comparison_base}{separator}{head}"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            print("Affected gate: FAIL (unable to compare committed changes)", file=sys.stderr)
            return None
        changed.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    return sorted(changed)


def _command_is_affected(command: dict[str, Any], components: dict[str, dict[str, Any]], paths: list[str] | None) -> bool:
    if paths is None:
        return True
    component = components.get(str(command.get("component")), {})
    impact_paths = component.get("impact_paths", [])
    if isinstance(impact_paths, list) and impact_paths:
        return any(
            fnmatch.fnmatch(path, str(pattern))
            for path in paths
            for pattern in impact_paths
        )
    component_path = str(component.get("path", "."))
    if component_path == ".":
        runtime_prefixes = ("app/", "src/", "lib/", "tests/", "test/")
        manifest_names = {"package.json", "pyproject.toml", "tsconfig.json", "uv.lock", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"}
        return any(path in manifest_names or path.startswith(runtime_prefixes) for path in paths)
    prefix = component_path.rstrip("/") + "/"
    return any(path == component_path or path.startswith(prefix) for path in paths)


def _run_project_commands(
    root: Path,
    project: dict[str, Any],
    mode: str,
    *,
    base: str | None = None,
    head: str = "HEAD",
) -> bool:
    commands = project.get("commands", {})
    components = {
        str(item.get("id")): item
        for item in project.get("components", [])
        if isinstance(item, dict)
    }
    changed = _changed_paths(root, base=base, head=head) if mode == "affected" else None
    selected: list[tuple[str, dict[str, Any]]] = []
    category_order = {
        "install": 0,
        "format": 10,
        "lint": 20,
        "typecheck": 30,
        "unit": 40,
        "integration": 50,
        "test": 60,
        "e2e": 70,
        "build": 80,
    }
    if isinstance(commands, dict):
        ordered_commands = sorted(
            commands.items(),
            key=lambda item: (
                category_order.get(
                    str(item[1].get("category", "")) if isinstance(item[1], dict) else "",
                    100,
                ),
                str(item[0]),
            ),
        )
        for command_id, command in ordered_commands:
            if not isinstance(command, dict) or command.get("status") != "required":
                continue
            if mode == "affected" and not _command_is_affected(command, components, changed):
                continue
            selected.append((str(command_id), command))
    if not selected:
        print(f"{mode.capitalize()} gate: PASS (no required stack command selected)")
        return True
    success = True
    for command_id, command in selected:
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv:
            print(f"- {command_id}: FAIL (missing argv)")
            success = False
            continue
        cwd_value = str(command.get("cwd", "."))
        cwd = _repository_path(root, cwd_value)
        if cwd is None or not cwd.is_dir():
            print(f"- {command_id}: FAIL (unsafe or missing working directory)")
            success = False
            continue
        print(f"- {command_id}: RUN")
        try:
            result = subprocess.run(
                argv,
                cwd=cwd,
                timeout=900,
                check=False,
                env=os.environ.copy(),
            )
        except FileNotFoundError:
            print(f"  FAIL: executable is unavailable; install declared tooling first")
            success = False
            continue
        except subprocess.TimeoutExpired:
            print("  FAIL: command exceeded 900 seconds")
            success = False
            continue
        if result.returncode != 0:
            print(f"  FAIL: exit {result.returncode}")
            success = False
        else:
            print("  PASS")
    print(f"{mode.capitalize()} gate: {'PASS' if success else 'FAIL'}")
    return success


def run_check(
    root: Path,
    gate: str,
    *,
    base: str | None = None,
    head: str = "HEAD",
) -> int:
    if gate == "harness":
        success, _ = check_harness(root)
        return 0 if success else 1
    if gate == "security":
        harness_ok, _ = check_harness(root, quiet=True)
        security_ok, _ = check_security(root)
        if not harness_ok:
            print("- harness drift must be refreshed before security completion")
        return 0 if harness_ok and security_ok else 1
    harness_ok, _ = check_harness(root)
    if not harness_ok:
        return 1
    project = _load_json_object(root / ".harness/project.json") or {}
    commands_ok = _run_project_commands(root, project, gate, base=base, head=head)
    return 0 if commands_ok else 1


def _matches_route(route: dict[str, Any], topic: str | None, path_value: str | None) -> bool:
    if topic:
        needle = topic.lower()
        topics = [str(item).lower() for item in route.get("topics", [])]
        return any(needle == item or needle in item or item in needle for item in topics)
    if path_value:
        normalized = path_value.lstrip("./")
        return any(fnmatch.fnmatch(normalized, str(pattern)) for pattern in route.get("paths", []))
    return False


def _sanitize_output(text: str) -> str:
    value = text
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED SECRET]", value)
    value = PERSONAL_PATH_PATTERN.sub("[REDACTED PERSONAL PATH]", value)
    return value


def render_context(
    root: Path,
    topic: str | None,
    path_value: str | None,
    *,
    summary: bool = False,
) -> str:
    project = _load_json_object(root / ".harness/project.json") or build_project(root)
    context_map = _load_json_object(root / ".harness/context-map.json") or build_context_map(project)
    documents: list[str] = []
    checks: list[str] = []
    lenses: list[str] = []
    routes = context_map.get("routes", [])
    matched = [
        route
        for route in routes
        if isinstance(route, dict) and _matches_route(route, topic, path_value)
    ]
    if matched:
        for route in matched:
            documents.extend(str(item) for item in route.get("documents", []))
            checks.extend(str(item) for item in route.get("checks", []))
            lenses.extend(str(item) for item in route.get("review_lenses", []))
    else:
        defaults = context_map.get("defaults", {})
        if isinstance(defaults, dict):
            documents.extend(str(item) for item in defaults.get("documents", []))
            checks.extend(str(item) for item in defaults.get("checks", []))
            lenses.extend(str(item) for item in defaults.get("review_lenses", []))
    documents = list(dict.fromkeys(documents))
    checks = list(dict.fromkeys(checks))
    lenses = list(dict.fromkeys(lenses))
    header = [
        "Agentic service context",
        f"Active profiles: {', '.join(_profile_ids(project)) or 'none detected'}",
        f"Risk tags: {', '.join(_risk_ids(project)) or 'none detected'}",
        f"Relevant checks: {', '.join(checks) or 'harness'}",
        f"Review lenses: {', '.join(lenses) or 'regression'}",
        "Safety: external, paid, production-data, destructive, and irreversible effects require explicit confirmation.",
    ]
    sections: list[str] = ["\n".join(header)]
    for relative in documents:
        path = _repository_path(root, relative)
        if path is None:
            sections.append(f"--- blocked unsafe context path: {relative!r} ---")
            continue
        text = _read_text(path, limit=1_000_000)
        if text is None:
            continue
        if summary and len(text) > 1800:
            text = text[:1760].rstrip() + "\n[document excerpt truncated]"
        sections.append(f"--- {relative} ---\n{text.rstrip()}")
    output = _sanitize_output("\n\n".join(sections).rstrip() + "\n")
    if len(output) > MAX_CONTEXT_CHARS:
        marker = "\n[context truncated at 6000 characters]\n"
        output = output[: MAX_CONTEXT_CHARS - len(marker)].rstrip() + marker
    return output


def _extract_root(argv: list[str]) -> tuple[list[str], str | None]:
    cleaned: list[str] = []
    root_value: str | None = None
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--root":
            if index + 1 >= len(argv):
                raise SystemExit("--root requires a path")
            root_value = argv[index + 1]
            index += 2
            continue
        if argument.startswith("--root="):
            root_value = argument.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(argument)
        index += 1
    return cleaned, root_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect, route, and verify an agentic service repository."
    )
    parser.add_argument(
        "--root",
        metavar="PATH",
        help="repository root (accepted before or after the subcommand)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan", help="read-only stack and repository fact detection")
    for name in ("init", "refresh"):
        generation = subparsers.add_parser(name, help=f"{name} managed inventory and context")
        generation.add_argument(
            "--write",
            action="store_true",
            help="apply the preview; without this flag no files are changed",
        )
    context = subparsers.add_parser("context", help="print routed context, bounded to 6000 characters")
    context.add_argument("--summary", action="store_true", help="emit the bounded context summary")
    context.add_argument("--topic", help="route by topic")
    context.add_argument("--path", dest="path_value", help="route by repository-relative path")
    check = subparsers.add_parser("check", help="run a deterministic repository gate")
    check.add_argument("gate", choices=("harness", "affected", "full", "security"))
    check.add_argument("--base", help="base Git ref for the affected gate")
    check.add_argument("--head", default="HEAD", help="head Git ref for the affected gate")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    cleaned, extracted_root = _extract_root(raw)
    parser = build_parser()
    args = parser.parse_args(cleaned)
    default_root = Path(__file__).resolve().parent.parent
    root = Path(extracted_root or args.root or default_root).resolve()
    if not root.is_dir():
        parser.error("repository root must be an existing directory")
    if args.command == "scan":
        print(_json_text(scan_repository(root)), end="")
        return 0
    if args.command in {"init", "refresh"}:
        return run_generation(root, args.command, bool(args.write))
    if args.command == "context":
        print(
            render_context(
                root,
                args.topic,
                args.path_value,
                summary=bool(args.summary),
            ),
            end="",
        )
        return 0
    if args.command == "check":
        return run_check(root, args.gate, base=args.base, head=args.head)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
