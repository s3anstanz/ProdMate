import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lint_checklists

KNOWN_AUDITS = {"lighthouse", "osv-scanner", "gitleaks", "http-observatory", "checkdmarc", "codesign"}


def item(item_id, tier="polish", audit="none", drop=None):
    fields = {
        "tier": tier,
        "why": "Search engines find your pages.",
        "applies-when": "the app serves public pages",
        "check": "a sitemap route or sitemap.xml exists",
        "agent-fix": "add app/sitemap.ts",
        "audit": audit,
        "you-do": "none",
    }
    if drop:
        del fields[drop]
    lines = [f"### {item_id}"] + [f"- {k}: {v}" for k, v in fields.items()]
    return "\n".join(lines) + "\n"


class LintChecklistsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_all_fields(self):
        items = lint_checklists.parse_checklist("# Web\n\n" + item("web.sitemap", audit="lighthouse"))
        self.assertEqual(len(items), 1)
        self.assertEqual(
            set(items[0]),
            {"id", "tier", "why", "applies-when", "check", "agent-fix", "audit", "you-do"},
        )
        self.assertEqual(items[0]["id"], "web.sitemap")
        self.assertEqual(items[0]["audit"], "lighthouse")

    def test_clean_file_has_no_errors(self):
        path = self.write("web-app.md", item("web.sitemap") + "\n" + item("web.seo", audit="lighthouse"))
        self.assertEqual(lint_checklists.lint([path], KNOWN_AUDITS), [])

    def test_missing_field_is_error(self):
        path = self.write("web-app.md", item("web.sitemap", drop="why"))
        errors = lint_checklists.lint([path], KNOWN_AUDITS)
        self.assertEqual(len(errors), 1)
        self.assertIn("web.sitemap", errors[0])
        self.assertIn("why", errors[0])

    def test_bad_tier_is_error(self):
        path = self.write("web-app.md", item("web.sitemap", tier="urgent"))
        errors = lint_checklists.lint([path], KNOWN_AUDITS)
        self.assertEqual(len(errors), 1)
        self.assertIn("urgent", errors[0])

    def test_duplicate_id_across_files_is_error(self):
        sub = self.dir / "overlays"
        sub.mkdir()
        first = self.write("common.md", item("common.ci"))
        second = sub / "common.md"
        second.write_text(item("common.ci"), encoding="utf-8")
        errors = lint_checklists.lint([first, second], KNOWN_AUDITS)
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate", errors[0])
        self.assertIn("common.ci", errors[0])

    def test_prefix_must_match_file(self):
        path = self.write("macos-app.md", item("web.x"))
        errors = lint_checklists.lint([path], KNOWN_AUDITS)
        self.assertEqual(len(errors), 1)
        self.assertIn("web.x", errors[0])
        self.assertIn("macos.", errors[0])

    def test_unknown_audit_is_error(self):
        path = self.write("web-app.md", item("web.sitemap", audit="pagespeed"))
        errors = lint_checklists.lint([path], KNOWN_AUDITS)
        self.assertEqual(len(errors), 1)
        self.assertIn("pagespeed", errors[0])

    def test_cli_exits_1_on_error(self):
        import subprocess

        self.write("web-app.md", item("web.sitemap", tier="urgent"))
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "lint_checklists.py"), str(self.dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("urgent", result.stdout)


if __name__ == "__main__":
    unittest.main()
