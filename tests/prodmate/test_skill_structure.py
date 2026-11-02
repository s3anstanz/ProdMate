import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "skills" / "prodmate"
SKILL_MD = SKILL_DIR / "SKILL.md"


def read_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            fields[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return fields


class SkillStructureTest(unittest.TestCase):
    def skill_text(self):
        self.assertTrue(SKILL_MD.is_file(), f"missing {SKILL_MD}")
        return SKILL_MD.read_text(encoding="utf-8")

    def test_frontmatter_name_matches_folder(self):
        fields = read_frontmatter(self.skill_text())
        self.assertEqual(fields.get("name"), "prodmate")
        self.assertEqual(fields.get("name"), SKILL_DIR.name)

    def test_description_limits(self):
        description = read_frontmatter(self.skill_text()).get("description", "")
        self.assertGreater(len(description), 0)
        self.assertLessEqual(len(description), 1024)
        self.assertIn("production", description)

    def test_skill_md_under_500_lines(self):
        self.assertLess(len(self.skill_text().splitlines()), 500)

    def test_references_one_level_deep(self):
        text = self.skill_text()
        for rel in sorted(set(re.findall(r"references/[\w./-]+\.md", text))):
            with self.subTest(path=rel):
                self.assertTrue((SKILL_DIR / rel).is_file(), f"{rel} linked from SKILL.md does not exist")

    def test_eval_md_referenced(self):
        self.assertTrue((SKILL_DIR / "eval.md").is_file(), "missing eval.md")
        self.assertIn("eval.md", self.skill_text())

    def test_eval_md_under_60_lines(self):
        self.assertLess(len((SKILL_DIR / "eval.md").read_text(encoding="utf-8").splitlines()), 60)

    def test_scripts_named_in_skill_md_exist(self):
        for rel in sorted(set(re.findall(r"scripts/[\w-]+\.py", self.skill_text()))):
            with self.subTest(path=rel):
                self.assertTrue((SKILL_DIR / rel).is_file(), f"{rel} named in SKILL.md does not exist")

    def test_toolkit_reference_covers_every_tool(self):
        toolkit = SKILL_DIR / "references" / "toolkit.md"
        self.assertTrue(toolkit.is_file(), "missing references/toolkit.md")
        self.assertIn("references/toolkit.md", self.skill_text())
        text = toolkit.read_text(encoding="utf-8")
        sys.path.insert(0, str(SKILL_DIR / "scripts"))
        import audits

        for tool in ["python3", "git", "gh", "npx", "Chrome", "pipx", *audits.AUDITS]:
            with self.subTest(tool=tool):
                self.assertIn(tool, text)

    def test_skill_md_has_no_python_fallback(self):
        self.assertIn("Without Python", self.skill_text())

    def test_long_references_have_toc(self):
        for path in sorted((SKILL_DIR / "references").rglob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > 100:
                with self.subTest(path=str(path.relative_to(SKILL_DIR))):
                    self.assertIn("## Contents", lines[:15])


if __name__ == "__main__":
    unittest.main()
