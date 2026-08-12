from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
HARNESS = REPOSITORY_ROOT / ".harness" / "harness.py"
MANAGED_START = "<!-- harness:managed:start -->"
MANAGED_END = "<!-- harness:managed:end -->"


def write(root: Path, relative_path: str, content: str) -> Path:
    destination = root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination


def run_harness(
    root: Path,
    *arguments: str,
    expect_success: bool | None = True,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(HARNESS),
        "--root",
        str(root),
        *arguments,
    ]
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HARNESS_EVAL_SECRET": dynamic_secret("subprocess-environment"),
    }
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if expect_success is True and result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if expect_success is False and result.returncode == 0:
        raise AssertionError(
            f"command unexpectedly succeeded: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def parse_json_output(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"expected one JSON object on stdout, received:\n{result.stdout}"
        ) from error
    if not isinstance(payload, dict):
        raise AssertionError(f"expected a JSON object, received {type(payload).__name__}")
    return payload


def profile_names(payload: dict[str, Any]) -> set[str]:
    raw_profiles = payload.get("profiles", payload.get("active_profiles"))
    if raw_profiles is None:
        raise AssertionError("scan output must expose profiles or active_profiles")

    names: set[str] = set()
    if isinstance(raw_profiles, dict):
        for name, value in raw_profiles.items():
            if value is False or value is None:
                continue
            if isinstance(value, dict) and value.get("active") is False:
                continue
            names.add(str(name).lower())
    elif isinstance(raw_profiles, list):
        for value in raw_profiles:
            if isinstance(value, str):
                names.add(value.lower())
            elif isinstance(value, dict):
                name = value.get("name", value.get("id", value.get("profile")))
                if name is not None and value.get("active", True):
                    names.add(str(name).lower())
    else:
        raise AssertionError("profiles must be an object or array")
    return names


def risk_tags(payload: dict[str, Any]) -> set[str]:
    raw_tags = payload.get("risk_tags", payload.get("risks", []))
    if isinstance(raw_tags, dict):
        tags: set[str] = set()
        for name, value in raw_tags.items():
            if value is False or value is None:
                continue
            if isinstance(value, dict) and value.get("active") is False:
                continue
            tags.add(str(name).lower())
        return tags
    if isinstance(raw_tags, list):
        tags: set[str] = set()
        for value in raw_tags:
            if isinstance(value, str):
                tags.add(value.lower())
            elif isinstance(value, dict):
                name = value.get("name", value.get("id", value.get("tag")))
                if name is not None and value.get("active", True):
                    tags.add(str(name).lower())
        return tags
    raise AssertionError("risk_tags must be an object or array")


def contains_profile(names: Iterable[str], expected: str) -> bool:
    return any(expected == name or expected in name.split("-") for name in names)


def tree_snapshot(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            relative = path.relative_to(root)
            snapshot[relative.as_posix()] = (
                b"SYMLINK\0" + os.readlink(path).encode("utf-8")
            )
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or relative.name.endswith(".pyc"):
            continue
        snapshot[relative.as_posix()] = path.read_bytes()
    return snapshot


def changed_text(root: Path, before: dict[str, bytes]) -> str:
    after = tree_snapshot(root)
    changed_paths = sorted(
        relative
        for relative, content in after.items()
        if before.get(relative) != content
    )
    return "\n".join(
        after[relative].decode("utf-8", errors="replace")
        for relative in changed_paths
    )


def dynamic_secret(label: str) -> str:
    prefix = "".join((chr(115), chr(107), chr(45)))
    digest = hashlib.sha256(f"agent-harness-{label}".encode()).hexdigest()
    return f"{prefix}{digest}"


def dynamic_personal_path() -> str:
    owner = "".join(("fixture", "-", "owner"))
    return os.path.join(os.sep, "Users", owner, "private", "service")


def walk_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def create_node_fixture(root: Path) -> None:
    package = {
        "name": "web-fixture",
        "private": True,
        "packageManager": "pnpm@9.15.0",
        "scripts": {
            "format:check": "prettier --check .",
            "lint": "next lint",
            "typecheck": "tsc --noEmit",
            "test": "vitest run",
            "build": "next build",
        },
        "dependencies": {"next": "15.1.0", "react": "19.0.0"},
        "devDependencies": {"typescript": "5.7.0", "vitest": "2.1.0"},
    }
    write(root, "package.json", json.dumps(package, indent=2) + "\n")
    write(root, "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
    write(root, "next.config.mjs", "export default {};\n")
    write(root, "tsconfig.json", '{"compilerOptions":{"strict":true}}\n')
    write(root, "app/page.tsx", "export default function Page() { return <main />; }\n")


def create_python_fixture(root: Path) -> None:
    write(
        root,
        "pyproject.toml",
        """[project]
name = "api-fixture"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "uvicorn>=0.34"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.9", "mypy>=1.14"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
""",
    )
    write(root, "uv.lock", "version = 1\nrevision = 1\n")
    write(
        root,
        "src/api_fixture/main.py",
        "from fastapi import FastAPI\n\napp = FastAPI()\n",
    )
    write(root, "tests/test_health.py", "def test_health_placeholder():\n    assert True\n")


def create_control_plane_fixture(root: Path) -> None:
    """Create the smallest currently valid static harness control plane."""
    write(root, ".harness/harness.py", "# fixture harness entrypoint\n")
    for schema_name in ("project.schema.json", "context-map.schema.json"):
        write(
            root,
            f".harness/schemas/{schema_name}",
            '{"type":"object","properties":{}}\n',
        )
    for script_name in ("check", "context"):
        script = write(root, f"scripts/{script_name}", "#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
    write(root, ".codex/config.toml", "# fixture\n")
    write(root, ".codex/hooks.json", "{}\n")
    for agent_name in ("explorer", "reviewer", "docs-researcher"):
        write(root, f".codex/agents/{agent_name}.toml", "# fixture\n")
    for skill_name in ("project-context", "product-contract-tdd", "change-review"):
        write(
            root,
            f".agents/skills/{skill_name}/SKILL.md",
            (
                "---\n"
                f"name: {skill_name}\n"
                "description: Fixture skill metadata.\n"
                "---\n\n"
                "# Fixture\n"
            ),
        )
        write(
            root,
            f".agents/skills/{skill_name}/agents/openai.yaml",
            "interface:\n  display_name: Fixture\n  default_prompt: Fixture\n",
        )


def create_claude_adapter_fixture(root: Path) -> None:
    write(root, "CLAUDE.md", "# Claude fixture\n\n@AGENTS.md\n")
    settings = {
        "hooks": {
            event_name: [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3",
                            "args": [
                                "${CLAUDE_PROJECT_DIR}/.claude/hooks/context.py"
                            ],
                        }
                    ]
                }
            ]
            for event_name in ("SessionStart", "SubagentStart")
        }
    }
    write(root, ".claude/settings.json", json.dumps(settings) + "\n")
    write(root, ".claude/hooks/context.py", "# fixture hook\n")
    for agent_name in ("explorer", "reviewer", "docs-researcher"):
        write(
            root,
            f".claude/agents/{agent_name}.md",
            (
                "---\n"
                f"name: {agent_name}\n"
                "description: Fixture read-only specialist.\n"
                "tools: Read, Grep, Glob, Bash\n"
                "model: inherit\n"
                "permissionMode: plan\n"
                "---\n\n"
                "Fixture instructions.\n"
            ),
        )
    (root / ".claude/skills").mkdir(parents=True, exist_ok=True)
    for skill_name in ("project-context", "product-contract-tdd", "change-review"):
        os.symlink(
            f"../../.agents/skills/{skill_name}",
            root / ".claude/skills" / skill_name,
            target_is_directory=True,
        )


class HarnessContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="agent-harness-eval-"
        )
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def scan(self) -> dict[str, Any]:
        return parse_json_output(run_harness(self.root, "scan"))

    def assertProfiles(self, payload: dict[str, Any], *expected: str) -> None:
        names = profile_names(payload)
        for name in expected:
            self.assertTrue(
                contains_profile(names, name),
                f"expected profile {name!r}; active profiles were {sorted(names)!r}",
            )

    def test_scan_empty_repository_has_no_language_or_service_profiles(self) -> None:
        payload = self.scan()
        names = profile_names(payload)
        for unexpected in ("node", "typescript", "python", "web", "api", "database", "ai"):
            self.assertFalse(
                contains_profile(names, unexpected),
                f"empty repository unexpectedly activated {unexpected}: {sorted(names)}",
            )

        manifests = payload.get("manifests", [])
        self.assertIn(manifests, ([], {}))

    def test_harness_gate_requires_the_claude_code_adapter(self) -> None:
        create_control_plane_fixture(self.root)
        run_harness(self.root, "init", "--write")

        result = run_harness(
            self.root, "check", "harness", expect_success=False
        )

        output = (result.stdout + result.stderr).lower()
        self.assertIn("claude", output)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are required")
    def test_harness_gate_accepts_safe_claude_skill_adapters(self) -> None:
        create_control_plane_fixture(self.root)
        create_claude_adapter_fixture(self.root)
        run_harness(self.root, "init", "--write")

        result = run_harness(self.root, "check", "harness")

        self.assertIn("PASS", result.stdout)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are required")
    def test_harness_gate_rejects_misdirected_claude_skill_adapter(self) -> None:
        create_control_plane_fixture(self.root)
        create_claude_adapter_fixture(self.root)
        adapter = self.root / ".claude/skills/project-context"
        adapter.unlink()
        os.symlink(
            "../../.agents/skills/change-review",
            adapter,
            target_is_directory=True,
        )
        run_harness(self.root, "init", "--write")

        result = run_harness(
            self.root, "check", "harness", expect_success=False
        )

        output = (result.stdout + result.stderr).lower()
        self.assertIn("claude skill symlink", output)
        self.assertIn("project-context", output)

    def test_claude_adapter_prose_does_not_activate_runtime_profiles(self) -> None:
        write(
            self.root,
            ".claude/agents/fixture.md",
            "Use Next.js, FastAPI, PostgreSQL, Kubernetes, and Terraform.\n",
        )

        names = profile_names(self.scan())

        for unexpected in (
            "node",
            "typescript",
            "python",
            "web",
            "api",
            "database",
            "terraform",
            "kubernetes",
        ):
            self.assertFalse(contains_profile(names, unexpected), sorted(names))

    def test_scan_detects_pnpm_next_typescript_web_service(self) -> None:
        create_node_fixture(self.root)

        payload = self.scan()

        self.assertProfiles(payload, "node", "typescript", "web")
        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertIn("pnpm", serialized)
        self.assertIn("package.json", serialized)

    def test_scan_detects_uv_fastapi_python_service(self) -> None:
        create_python_fixture(self.root)

        payload = self.scan()

        self.assertProfiles(payload, "python", "api")
        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertIn("uv", serialized)
        self.assertIn("pyproject.toml", serialized)
        self.assertIn("pytest", serialized)

    def test_scan_detects_requirements_only_python_without_inventing_tools(self) -> None:
        write(
            self.root,
            "requirements.txt",
            "fastapi==0.115.0\npytest==8.3.0\nruff==0.9.0\n",
        )
        write(self.root, "src/service/main.py", "def health():\n    return 'ok'\n")

        payload = self.scan()

        self.assertProfiles(payload, "python", "api")
        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertIn("requirements.txt", serialized)
        self.assertIn("python3", serialized)
        self.assertIn("-m", serialized)
        self.assertIn("pytest", serialized)
        self.assertNotIn("uv run", serialized)

    def test_node_format_write_script_is_not_a_required_validation(self) -> None:
        package = {
            "name": "format-fixture",
            "private": True,
            "scripts": {"format": "prettier --write .", "test": "node --test"},
        }
        write(self.root, "package.json", json.dumps(package) + "\n")

        payload = self.scan()

        commands = payload.get("commands", {})
        format_commands = [
            command
            for command in commands.values()
            if isinstance(command, dict) and command.get("category") == "format"
        ]
        self.assertTrue(format_commands)
        self.assertTrue(
            all(command.get("status") != "required" for command in format_commands),
            format_commands,
        )

    def test_scan_detects_mixed_web_api_database_and_docker_components(self) -> None:
        write(root=self.root, relative_path="pnpm-workspace.yaml", content="packages:\n  - apps/*\n")
        create_node_fixture(self.root / "apps/web")
        create_python_fixture(self.root / "services/api")
        write(
            self.root,
            "services/api/pyproject.toml",
            """[project]
name = "mixed-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "sqlalchemy>=2", "alembic>=1.14"]

[dependency-groups]
dev = ["pytest>=8"]
""",
        )
        write(self.root, "services/api/alembic.ini", "[alembic]\nscript_location = migrations\n")
        write(
            self.root,
            "services/api/migrations/versions/0001_initial.py",
            "revision = 'fixture_revision'\ndown_revision = None\n",
        )
        write(
            self.root,
            "Dockerfile",
            "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\n",
        )

        payload = self.scan()

        self.assertProfiles(payload, "node", "python", "web", "api", "database", "docker")
        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertIn("apps/web", serialized)
        self.assertIn("services/api", serialized)
        self.assertIn("dockerfile", serialized)

    def test_workspace_child_inherits_root_pnpm_lockfile(self) -> None:
        write(self.root, "pnpm-workspace.yaml", "packages:\n  - packages/*\n")
        write(self.root, "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        write(
            self.root,
            "packages/api/package.json",
            json.dumps(
                {
                    "name": "workspace-api",
                    "scripts": {"test": "node --test"},
                }
            )
            + "\n",
        )

        payload = self.scan()

        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertIn("pnpm-lock.yaml", serialized)
        component_commands = [
            item
            for item in payload.get("commands", {}).values()
            if isinstance(item, dict) and item.get("component") == "node-packages-api"
        ]
        self.assertTrue(component_commands)
        required_argv = [
            item.get("argv", [])
            for item in component_commands
            if item.get("status") == "required"
        ]
        self.assertTrue(required_argv)
        self.assertTrue(all(argv[0] == "pnpm" for argv in required_argv), required_argv)

    def test_scan_activates_infrastructure_only_when_configuration_exists(self) -> None:
        empty = self.scan()
        empty_profiles = profile_names(empty)
        for unexpected in ("infra", "terraform", "kubernetes"):
            self.assertFalse(contains_profile(empty_profiles, unexpected))

        write(
            self.root,
            "infra/main.tf",
            'terraform { required_version = ">= 1.7" }\n',
        )
        write(
            self.root,
            "deploy/deployment.yaml",
            """apiVersion: apps/v1
kind: Deployment
metadata:
  name: fixture
spec:
  replicas: 1
""",
        )

        detected = self.scan()
        detected_profiles = profile_names(detected)
        self.assertTrue(
            contains_profile(detected_profiles, "infra")
            or (
                contains_profile(detected_profiles, "terraform")
                and contains_profile(detected_profiles, "kubernetes")
            ),
            f"expected detected infrastructure profile: {sorted(detected_profiles)}",
        )

    def test_scan_activates_ai_only_with_runtime_evidence(self) -> None:
        provider_module = "".join(("open", "ai"))
        provider_class = "".join(("Open", "AI"))
        provider_call = "".join(("responses", ".", "create"))
        write(
            self.root,
            "pyproject.toml",
            f"""[project]
name = "ai-fixture"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["{provider_module}>=1"]

[dependency-groups]
dev = ["pytest>=8"]
""",
        )
        write(self.root, "uv.lock", "version = 1\nrevision = 1\n")

        dependency_only = self.scan()
        self.assertProfiles(dependency_only, "python")
        self.assertFalse(
            contains_profile(profile_names(dependency_only), "ai"),
            "an installed provider SDK alone must not establish an AI runtime",
        )

        write(
            self.root,
            "src/ai_fixture/generate.py",
            f"""from {provider_module} import {provider_class}

client = {provider_class}()

def generate(prompt: str) -> str:
    response = client.{provider_call}(model="fixture-model", input=prompt)
    return response.output_text
""",
        )
        write(self.root, "prompts/system.txt", "Return one deterministic fixture result.\n")
        write(self.root, "evals/cases.json", '{"cases": []}\n')

        payload = self.scan()

        self.assertProfiles(payload, "python", "ai")
        tags = risk_tags(payload)
        self.assertIn("nondeterminism", tags)
        self.assertIn("paid-provider", tags)

    def test_init_and_refresh_are_preview_first_idempotent_and_preserve_human_text(self) -> None:
        create_node_fixture(self.root)
        human_before = "Human-owned architecture note."
        human_after = "Human-owned release constraint."
        architecture = write(
            self.root,
            "docs/context/architecture.md",
            "\n".join(
                (
                    "# Architecture",
                    "",
                    human_before,
                    "",
                    MANAGED_START,
                    "- Stale generated inventory.",
                    MANAGED_END,
                    "",
                    human_after,
                    "",
                )
            ),
        )
        unrelated_note = write(
            self.root,
            "notes/human-only.txt",
            "This unrelated dirty-state fixture must remain byte-for-byte stable.\n",
        )
        unrelated_content = unrelated_note.read_bytes()
        before_preview = tree_snapshot(self.root)

        run_harness(self.root, "init")
        self.assertEqual(tree_snapshot(self.root), before_preview)

        run_harness(self.root, "init", "--write")
        first_init = tree_snapshot(self.root)
        self.assertTrue((self.root / ".harness/project.json").is_file())
        self.assertTrue((self.root / ".harness/context-map.json").is_file())
        generated_architecture = architecture.read_text(encoding="utf-8")
        self.assertIn(human_before, generated_architecture)
        self.assertIn(human_after, generated_architecture)
        self.assertEqual(generated_architecture.count(MANAGED_START), 1)
        self.assertEqual(generated_architecture.count(MANAGED_END), 1)
        self.assertNotIn("Stale generated inventory", generated_architecture)
        self.assertEqual(unrelated_note.read_bytes(), unrelated_content)

        run_harness(self.root, "init", "--write")
        self.assertEqual(tree_snapshot(self.root), first_init)

        package_path = self.root / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["scripts"]["test:integration"] = "vitest run tests/integration"
        package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
        refresh_preview = tree_snapshot(self.root)

        run_harness(self.root, "refresh")
        self.assertEqual(tree_snapshot(self.root), refresh_preview)

        run_harness(self.root, "refresh", "--write")
        first_refresh = tree_snapshot(self.root)
        refreshed_architecture = architecture.read_text(encoding="utf-8")
        self.assertIn(human_before, refreshed_architecture)
        self.assertIn(human_after, refreshed_architecture)
        self.assertIn(
            "test:integration",
            (self.root / ".harness/project.json").read_text(encoding="utf-8"),
        )

        run_harness(self.root, "refresh", "--write")
        self.assertEqual(tree_snapshot(self.root), first_refresh)

    def test_generated_inventory_and_context_map_expose_machine_contracts(self) -> None:
        create_node_fixture(self.root)
        run_harness(self.root, "init", "--write")

        project = json.loads(
            (self.root / ".harness/project.json").read_text(encoding="utf-8")
        )
        context_map = json.loads(
            (self.root / ".harness/context-map.json").read_text(encoding="utf-8")
        )

        for key in ("components", "manifests", "profiles", "risk_tags", "commands"):
            self.assertIn(key, project)
        self.assertIsInstance(project["components"], (list, dict))
        self.assertIsInstance(project["manifests"], (list, dict))
        self.assertIsInstance(project["profiles"], (list, dict))
        self.assertIsInstance(project["risk_tags"], (list, dict))
        self.assertIsInstance(project["commands"], (list, dict))

        serialized_project = json.dumps(project, sort_keys=True).lower()
        for expected in ("package.json", "pnpm", "test", "build"):
            self.assertIn(expected, serialized_project)

        validation_objects = [
            item
            for item in walk_objects(project)
            if "status" in item
            and item["status"] in {"required", "optional", "not_applicable"}
        ]
        self.assertTrue(validation_objects, "inventory must classify validation gates")
        for item in validation_objects:
            if item["status"] == "not_applicable":
                self.assertTrue(
                    str(item.get("reason", "")).strip(),
                    "not_applicable validation needs a concrete reason",
                )

        self.assertIsInstance(context_map, dict)
        serialized_context_map = json.dumps(context_map, sort_keys=True).lower()
        self.assertIn("docs/context/testing.md", serialized_context_map)
        self.assertIn("testing", serialized_context_map)
        self.assertTrue(
            any(label in serialized_context_map for label in ("path", "route", "topic")),
            "context map must route by path or topic",
        )

    def test_refresh_updates_only_managed_dependabot_ecosystems(self) -> None:
        create_node_fixture(self.root)
        human_note = "# Human registry configuration remains outside this block."
        dependabot = write(
            self.root,
            ".github/dependabot.yml",
            "\n".join(
                (
                    "version: 2",
                    "# harness:managed:start",
                    "updates: []",
                    "# harness:managed:end",
                    human_note,
                    "",
                )
            ),
        )

        run_harness(self.root, "init", "--write")
        first = dependabot.read_text(encoding="utf-8")

        self.assertIn("package-ecosystem: github-actions", first)
        self.assertIn("package-ecosystem: npm", first)
        self.assertIn(human_note, first)
        run_harness(self.root, "refresh", "--write")
        self.assertEqual(dependabot.read_text(encoding="utf-8"), first)

    def test_environment_values_never_reach_output_or_generated_context(self) -> None:
        create_node_fixture(self.root)
        secret = dynamic_secret("ignored-environment")
        personal_path = dynamic_personal_path()
        example_value = dynamic_secret("ignored-example")
        write(
            self.root,
            ".env",
            f"PRIVATE_API_TOKEN={secret}\nPRIVATE_WORKTREE={personal_path}\n",
        )
        write(
            self.root,
            ".env.example",
            f"PRIVATE_API_TOKEN={example_value}\nPUBLIC_BASE_URL=https://example.invalid\n",
        )
        before_generation = tree_snapshot(self.root)

        scan_result = run_harness(self.root, "scan")
        init_result = run_harness(self.root, "init", "--write")
        environment_secret = dynamic_secret("subprocess-environment")
        observable_text = (
            scan_result.stdout
            + scan_result.stderr
            + init_result.stdout
            + init_result.stderr
            + changed_text(self.root, before_generation)
        )

        self.assertNotIn(secret, observable_text)
        self.assertNotIn(example_value, observable_text)
        self.assertNotIn(environment_secret, observable_text)
        self.assertNotIn(personal_path, observable_text)
        self.assertNotIn(str(self.root), changed_text(self.root, before_generation))

    def test_unreadable_environment_file_does_not_break_scan(self) -> None:
        create_node_fixture(self.root)
        environment_file = write(
            self.root,
            ".env",
            f"PRIVATE_API_TOKEN={dynamic_secret('unreadable-environment')}\n",
        )
        environment_file.chmod(0)
        try:
            result = run_harness(self.root, "scan")
        finally:
            environment_file.chmod(0o600)
        self.assertNotIn(
            dynamic_secret("unreadable-environment"),
            result.stdout + result.stderr,
        )

    def test_empty_repository_affected_and_full_gates_are_deterministic(self) -> None:
        run_harness(self.root, "init", "--write")
        affected = run_harness(self.root, "check", "affected")
        full = run_harness(self.root, "check", "full")
        self.assertNotIn(dynamic_secret("subprocess-environment"), affected.stdout)
        self.assertNotIn(dynamic_secret("subprocess-environment"), full.stdout)

    def test_affected_includes_changes_already_committed_on_clean_branch(self) -> None:
        package = {
            "name": "committed-change-fixture",
            "private": True,
            "scripts": {
                "test": (
                    "python3 -c \"from pathlib import Path; "
                    "Path('gate-ran').write_text('yes')\""
                )
            },
        }
        write(self.root, "package.json", json.dumps(package, indent=2) + "\n")
        write(self.root, "app/service.js", "export const value = 1;\n")
        run_harness(self.root, "init", "--write")
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Harness Eval"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "eval@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.root, check=True, capture_output=True)
        write(self.root, "app/service.js", "export const value = 2;\n")
        subprocess.run(["git", "add", "app/service.js"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "change service"], cwd=self.root, check=True, capture_output=True)

        run_harness(self.root, "check", "affected")

        self.assertEqual((self.root / "gate-ran").read_text(encoding="utf-8"), "yes")

    def test_manifest_drift_fails_until_refresh_updates_inventory(self) -> None:
        create_node_fixture(self.root)
        run_harness(self.root, "init", "--write")
        run_harness(self.root, "check", "harness")

        package_path = self.root / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["scripts"]["contract"] = "vitest run tests/contracts"
        package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

        drift = run_harness(self.root, "check", "harness", expect_success=False)
        drift_output = (drift.stdout + drift.stderr).lower()
        self.assertTrue(
            any(label in drift_output for label in ("drift", "stale", "out of date")),
            f"drift failure must explain stale inventory: {drift_output}",
        )

        run_harness(self.root, "refresh", "--write")
        run_harness(self.root, "check", "harness")

    def test_lockfile_drift_fails_until_refresh(self) -> None:
        create_node_fixture(self.root)
        run_harness(self.root, "init", "--write")

        lockfile = self.root / "pnpm-lock.yaml"
        lockfile.write_text(
            lockfile.read_text(encoding="utf-8") + "settings: {}\n",
            encoding="utf-8",
        )

        drift = run_harness(self.root, "check", "harness", expect_success=False)
        self.assertIn("drift", (drift.stdout + drift.stderr).lower())
        run_harness(self.root, "refresh", "--write")
        run_harness(self.root, "check", "harness")

    def test_context_is_topic_routed_and_bounded(self) -> None:
        create_node_fixture(self.root)
        testing_marker = "TESTING_CONTEXT_MARKER"
        product_marker = "PRODUCT_CONTEXT_MARKER"
        write(
            self.root,
            "docs/context/testing.md",
            "\n".join(
                (
                    "# Testing context",
                    "",
                    testing_marker,
                    "",
                    MANAGED_START,
                    "- Pending inventory.",
                    MANAGED_END,
                    "",
                    "x" * 7000,
                    "",
                )
            ),
        )
        write(
            self.root,
            "docs/context/product.md",
            "\n".join(
                (
                    "# Product context",
                    "",
                    product_marker,
                    "",
                    MANAGED_START,
                    "- Pending inventory.",
                    MANAGED_END,
                    "",
                )
            ),
        )
        run_harness(self.root, "init", "--write")

        result = run_harness(self.root, "context", "--summary", "--topic", "testing")

        self.assertLessEqual(len(result.stdout), 6000)
        self.assertIn(testing_marker, result.stdout)
        self.assertNotIn(product_marker, result.stdout)

        path_result = run_harness(
            self.root, "context", "--summary", "--path", "app/page.tsx"
        )
        self.assertLessEqual(len(path_result.stdout), 6000)
        self.assertIn(testing_marker, path_result.stdout)

        full_result = run_harness(self.root, "context", "--topic", "testing")
        self.assertGreater(len(full_result.stdout), len(result.stdout))

    def test_context_blocks_documents_outside_repository(self) -> None:
        run_harness(self.root, "init", "--write")
        external = self.root.parent / f"{self.root.name}-external-context.txt"
        external_marker = "EXTERNAL_CONTEXT_MUST_NOT_BE_READ"
        external.write_text(external_marker, encoding="utf-8")
        self.addCleanup(external.unlink, missing_ok=True)
        context_map_path = self.root / ".harness/context-map.json"
        context_map = json.loads(context_map_path.read_text(encoding="utf-8"))
        context_map["routes"][0]["documents"] = [str(external)]
        context_map_path.write_text(
            json.dumps(context_map, indent=2) + "\n", encoding="utf-8"
        )

        result = run_harness(self.root, "context", "--summary", "--topic", "testing")

        self.assertNotIn(external_marker, result.stdout)
        self.assertIn("blocked unsafe context path", result.stdout)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are required")
    def test_init_rejects_symlinked_managed_output_directory(self) -> None:
        external = self.root.parent / f"{self.root.name}-external-output"
        external.mkdir()
        self.addCleanup(lambda: external.rmdir() if external.exists() else None)
        os.symlink(external, self.root / ".harness", target_is_directory=True)

        result = run_harness(self.root, "init", "--write", expect_success=False)

        self.assertIn("unsafe", (result.stdout + result.stderr).lower())
        self.assertFalse((external / "project.json").exists())
        self.assertFalse((external / "context-map.json").exists())

    def test_security_gate_rejects_leaked_secret_and_personal_absolute_path(self) -> None:
        run_harness(self.root, "init", "--write")
        run_harness(self.root, "check", "security")

        leak_file = self.root / "docs" / "leak.md"
        leak_file.parent.mkdir(parents=True, exist_ok=True)

        secret = dynamic_secret("committed-document")
        leak_file.write_text(f"Leaked token: {secret}\n", encoding="utf-8")
        leaked_secret = run_harness(
            self.root, "check", "security", expect_success=False
        )
        leaked_secret_output = leaked_secret.stdout + leaked_secret.stderr
        self.assertNotIn(secret, leaked_secret_output)
        self.assertTrue(
            any(
                label in leaked_secret_output.lower()
                for label in ("secret", "credential")
            )
        )

        personal_path = dynamic_personal_path()
        leak_file.write_text(f"Local checkout: {personal_path}\n", encoding="utf-8")
        leaked_path = run_harness(
            self.root, "check", "security", expect_success=False
        )
        leaked_path_output = leaked_path.stdout + leaked_path.stderr
        self.assertNotIn(personal_path, leaked_path_output)
        self.assertIn("path", leaked_path_output.lower())
        self.assertTrue(
            any(label in leaked_path_output.lower() for label in ("absolute", "personal"))
        )

        linux_personal_path = os.path.join(
            os.sep, "home", "fixture-owner", "private", "service"
        )
        leak_file.write_text(
            f"Local checkout: {linux_personal_path}\n", encoding="utf-8"
        )
        leaked_linux_path = run_harness(
            self.root, "check", "security", expect_success=False
        )
        self.assertNotIn(
            linux_personal_path, leaked_linux_path.stdout + leaked_linux_path.stderr
        )

    def test_security_scans_agent_eval_and_harness_control_paths(self) -> None:
        run_harness(self.root, "init", "--write")
        secret = dynamic_secret("control-plane-file")
        write(self.root, "evals/fixtures/credential.txt", f"credential={secret}\n")

        result = run_harness(self.root, "check", "security", expect_success=False)

        output = result.stdout + result.stderr
        self.assertNotIn(secret, output)
        self.assertIn("secret", output.lower())


class HarnessEntrypointTests(unittest.TestCase):
    def test_shipped_claude_adapter_is_safe_and_inventoried(self) -> None:
        claude_entrypoint = (REPOSITORY_ROOT / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        self.assertRegex(claude_entrypoint, r"(?m)^@AGENTS\.md$")

        settings = json.loads(
            (REPOSITORY_ROOT / ".claude/settings.json").read_text(encoding="utf-8")
        )
        self.assertIn("SessionStart", settings["hooks"])
        self.assertIn("SubagentStart", settings["hooks"])

        for skill_name in (
            "project-context",
            "product-contract-tdd",
            "change-review",
        ):
            adapter = REPOSITORY_ROOT / ".claude/skills" / skill_name
            canonical = REPOSITORY_ROOT / ".agents/skills" / skill_name
            self.assertTrue(adapter.is_symlink(), adapter)
            self.assertEqual(
                os.readlink(adapter), f"../../.agents/skills/{skill_name}"
            )
            self.assertEqual(adapter.resolve(strict=True), canonical.resolve(strict=True))

        scan = parse_json_output(run_harness(REPOSITORY_ROOT, "scan"))
        manifests = {
            item.get("path"): item
            for item in scan.get("manifests", [])
            if isinstance(item, dict)
        }
        for relative in (
            ".claude/settings.json",
            ".claude/hooks/context.py",
            ".claude/agents/explorer.md",
            ".claude/agents/reviewer.md",
            ".claude/agents/docs-researcher.md",
            ".claude/skills/project-context",
            ".claude/skills/product-contract-tdd",
            ".claude/skills/change-review",
        ):
            self.assertIn(relative, manifests)
        self.assertEqual(
            manifests[".claude/skills/change-review"].get("kind"),
            "harness-control-symlink",
        )
        harness_component = next(
            component
            for component in scan.get("components", [])
            if component.get("id") == "agent-harness-root"
        )
        self.assertIn(".claude/**", harness_component.get("impact_paths", []))

    def test_shipped_claude_context_hook_emits_each_supported_protocol(self) -> None:
        hook = REPOSITORY_ROOT / ".claude/hooks/context.py"
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "CLAUDE_PROJECT_DIR": str(REPOSITORY_ROOT),
        }

        session = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(hook)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            input='{"hook_event_name":"SessionStart","source":"startup"}\n',
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(session.returncode, 0, session.stderr)
        self.assertIn("Agentic service context", session.stdout)
        self.assertLessEqual(len(session.stdout), 6000)

        subagent = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(hook)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            input='{"hook_event_name":"SubagentStart","agent_type":"explorer"}\n',
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(subagent.returncode, 0, subagent.stderr)
        payload = json.loads(subagent.stdout)
        hook_output = payload["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "SubagentStart")
        self.assertIn("Agentic service context", hook_output["additionalContext"])
        self.assertLessEqual(len(hook_output["additionalContext"]), 6000)

    def test_shipped_machine_schemas_are_valid_json_objects(self) -> None:
        schema_directory = REPOSITORY_ROOT / ".harness" / "schemas"
        schemas = sorted(schema_directory.glob("*.json"))
        self.assertGreaterEqual(
            len(schemas),
            2,
            "expected schemas for project inventory and context routing",
        )
        serialized_names = " ".join(path.name.lower() for path in schemas)
        self.assertIn("project", serialized_names)
        self.assertIn("context", serialized_names)
        for schema in schemas:
            payload = json.loads(schema.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, dict, schema.name)
            self.assertEqual(payload.get("type"), "object", schema.name)
            self.assertIsInstance(payload.get("properties"), dict, schema.name)

    def test_harness_is_standard_library_importable(self) -> None:
        self.assertTrue(HARNESS.is_file(), f"missing harness entrypoint: {HARNESS}")
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-m", "py_compile", str(HARNESS)],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_exposes_all_public_commands_and_common_root(self) -> None:
        help_result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HARNESS), "--help"],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        output = help_result.stdout
        for token in ("--root", "scan", "init", "refresh", "context", "check"):
            self.assertIn(token, output)

    def test_risk_tag_adapter_ignores_explicitly_inactive_entries(self) -> None:
        self.assertEqual(
            risk_tags(
                {
                    "risk_tags": {
                        "active-dict": {"active": True},
                        "inactive-dict": {"active": False},
                    }
                }
            ),
            {"active-dict"},
        )
        self.assertEqual(
            risk_tags(
                {
                    "risk_tags": [
                        {"name": "active-list", "active": True},
                        {"name": "inactive-list", "active": False},
                    ]
                }
            ),
            {"active-list"},
        )

    def test_shell_entrypoint_delegates_to_harness(self) -> None:
        script = REPOSITORY_ROOT / "scripts" / "check"
        self.assertTrue(script.is_file(), f"missing check entrypoint: {script}")
        syntax = subprocess.run(
            ["/bin/bash", "-n", str(script)],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        result = subprocess.run(
            [str(script), "harness"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"scripts/check harness failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_context_shell_entrypoint_runs_public_cli(self) -> None:
        script = REPOSITORY_ROOT / "scripts" / "context"
        self.assertTrue(script.is_file(), f"missing context entrypoint: {script}")
        syntax = subprocess.run(
            ["/bin/bash", "-n", str(script)],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        result = subprocess.run(
            [str(script), "--summary", "--topic", "testing"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"scripts/context failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertLessEqual(len(result.stdout), 6000)


if __name__ == "__main__":
    unittest.main()
