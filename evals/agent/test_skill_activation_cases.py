from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
CASES_PATH = HERE / "skill_activation_cases.json"
EXPECTED_SKILLS = {
    "project-context",
    "product-contract-tdd",
    "change-review",
}
EXPECTED_KINDS = {"direct", "indirect", "incomplete", "should_not_trigger"}
EXPECTED_BEHAVIORS = {
    "inspect_then_preview",
    "inspect_before_questions",
    "red_green_refactor",
    "define_contract_before_editing",
    "read_only_scoped_review",
    "resolve_scope_then_review",
    "do_not_activate",
}


class SkillActivationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.payload["cases"]

    def test_case_file_has_stable_schema_and_unique_ids(self) -> None:
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertIsInstance(self.cases, list)
        self.assertTrue(self.cases)

        ids: list[str] = []
        for case in self.cases:
            self.assertEqual(
                set(case),
                {
                    "id",
                    "skill",
                    "kind",
                    "prompt",
                    "expected_activation",
                    "expected_behavior",
                },
            )
            self.assertRegex(case["id"], r"^[a-z0-9-]+$")
            self.assertIn(case["skill"], EXPECTED_SKILLS)
            self.assertIn(case["kind"], EXPECTED_KINDS)
            self.assertIsInstance(case["prompt"], str)
            self.assertGreaterEqual(len(case["prompt"]), 24)
            self.assertIs(type(case["expected_activation"]), bool)
            self.assertIn(case["expected_behavior"], EXPECTED_BEHAVIORS)
            ids.append(case["id"])

        self.assertEqual(len(ids), len(set(ids)))

    def test_each_skill_covers_every_activation_kind(self) -> None:
        for skill in EXPECTED_SKILLS:
            cases = [case for case in self.cases if case["skill"] == skill]
            self.assertEqual({case["kind"] for case in cases}, EXPECTED_KINDS)
            self.assertEqual(len(cases), len(EXPECTED_KINDS))

            for case in cases:
                expected = case["kind"] != "should_not_trigger"
                self.assertEqual(case["expected_activation"], expected)
                if not expected:
                    self.assertEqual(case["expected_behavior"], "do_not_activate")

    def test_direct_cases_explicitly_name_the_skill(self) -> None:
        for case in self.cases:
            if case["kind"] == "direct":
                self.assertIn(f"${case['skill']}", case["prompt"])
            else:
                self.assertNotIn(f"${case['skill']}", case["prompt"])

    def test_case_skills_exist_and_frontmatter_names_match(self) -> None:
        for skill in EXPECTED_SKILLS:
            skill_file = REPOSITORY_ROOT / ".agents" / "skills" / skill / "SKILL.md"
            agent_card = (
                REPOSITORY_ROOT
                / ".agents"
                / "skills"
                / skill
                / "agents"
                / "openai.yaml"
            )
            text = skill_file.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill)
            match = re.search(r"^name:\s*([^\n]+)$", text, flags=re.MULTILINE)
            self.assertIsNotNone(match, skill)
            self.assertEqual(match.group(1).strip(), skill)
            self.assertRegex(
                text,
                r"(?m)^description:\s*\S.+$",
                msg=f"{skill} needs a non-empty one-line description",
            )
            card_text = agent_card.read_text(encoding="utf-8")
            self.assertRegex(card_text, r"(?m)^interface:\s*$")
            self.assertRegex(card_text, r"(?m)^\s+display_name:\s*\".+\"\s*$")
            self.assertRegex(card_text, r"(?m)^\s+short_description:\s*\".+\"\s*$")
            self.assertRegex(card_text, r"(?m)^\s+default_prompt:\s*\".+\"\s*$")


if __name__ == "__main__":
    unittest.main()
