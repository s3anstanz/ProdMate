import copy
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "report" / "crumbly.json"
sys.path.insert(0, str(SCRIPTS))

import report


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def app_with(statuses):
    """An app whose items have the given (tier, status) pairs."""
    items = []
    for i, (tier, status) in enumerate(statuses):
        item = {"id": f"common.item-{i}", "tier": tier, "status": status, "title": f"Item {i}"}
        if status == "Not applicable":
            item["na_reason"] = "doesn't apply here."
        items.append(item)
    return {"name": "App", "path": ".", "types": ["web-app"], "verdict": "v", "summary": "s", "items": items}


class ReportDataTest(unittest.TestCase):
    def test_validate_fixture_is_clean(self):
        self.assertEqual(report.validate(load()), [])

    def test_validate_reports_missing_keys_and_bad_status(self):
        data = load()
        item = data["apps"][0]["items"][0]
        del item["title"]
        item["status"] = "Fine"
        errors = report.validate(data)
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any("title" in e for e in errors))
        self.assertTrue(any("Fine" in e for e in errors))

    def test_validate_requires_na_reason(self):
        data = {"version": 1, "checked": "2026-11-02", "apps": [app_with([("grow", "Not applicable")])]}
        del data["apps"][0]["items"][0]["na_reason"]
        errors = report.validate(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("na_reason", errors[0])

    def test_score_gives_half_credit_for_partial(self):
        # Sean, 2026-11-02: partly done items count half; Can't verify counts zero.
        self.assertEqual(report.score(load()["apps"][0]), {"done": 12, "partial": 14, "applicable": 47, "percent": 40})
        app = app_with([("blocker", "Done"), ("grow", "Partial"), ("grow", "Can't verify"), ("polish", "Missing")])
        self.assertEqual(report.score(app)["percent"], 38)  # (1 + 0.5) / 4

    def test_score_with_no_applicable_items(self):
        app = app_with([("grow", "Not applicable"), ("polish", "Not applicable")])
        self.assertEqual(report.score(app), {"done": 0, "partial": 0, "applicable": 0, "percent": 0})
        self.assertEqual(report.score(app_with([])), {"done": 0, "partial": 0, "applicable": 0, "percent": 0})

    def test_pick_first_prefers_missing_blocker(self):
        item, good_shape = report.pick_first(load()["apps"][0])
        self.assertEqual(item["id"], "common.secrets-in-repo")
        self.assertFalse(good_shape)

    def test_pick_first_cant_verify_blocker_blocks_good_shape(self):
        app = app_with([("blocker", "Done"), ("blocker", "Can't verify"), ("grow", "Missing")])
        item, good_shape = report.pick_first(app)
        self.assertEqual(item["id"], "common.item-1")
        self.assertFalse(good_shape)

    def test_pick_first_good_shape_when_no_open_blocker(self):
        app = app_with([("blocker", "Done"), ("grow", "Partial"), ("grow", "Missing"), ("polish", "Missing")])
        item, good_shape = report.pick_first(app)
        self.assertEqual(item["id"], "common.item-2")
        self.assertTrue(good_shape)

    def test_pick_first_when_everything_is_done(self):
        item, good_shape = report.pick_first(app_with([("blocker", "Done"), ("grow", "Not applicable")]))
        self.assertIsNone(item)
        self.assertTrue(good_shape)

    def test_ring_order(self):
        app = app_with([("blocker", "Missing"), ("grow", "Done"), ("grow", "Can't verify"), ("polish", "Partial"), ("polish", "Not applicable")])
        self.assertEqual(report.ring_order(app), ["Done", "Partial", "Can't verify", "Missing"])


def single(app):
    return {"version": 1, "checked": "2026-11-02", "last_update": None, "apps": [app]}


class MarkdownTest(unittest.TestCase):
    def test_markdown_sections_in_order(self):
        md = report.render_markdown(load())
        headings = [
            "# Production readiness: Crumbly",
            "## What I checked and what I couldn't",
            "## Promises honored",
            "## Launch blockers",
            "## Before you grow",
            "## Polish",
            "## Other things I noticed",
            "## You do",
            "<summary>Not applicable (3)</summary>",
        ]
        positions = [md.index(h) for h in headings]
        self.assertEqual(positions, sorted(positions))

    def test_markdown_summary_line(self):
        md = report.render_markdown(load())
        self.assertIn("Checked 2026-11-02 with ProdMate.", md)
        # open items per tier in the fixture: blocker 10, grow 20, polish 5
        self.assertIn("10 launch blockers, 20 before you grow, 5 polish.", md)

    def test_markdown_good_shape(self):
        md = report.render_markdown(single(app_with([("blocker", "Done"), ("grow", "Missing")])))
        body = md.split("\n", 1)[1].lstrip()
        self.assertTrue(body.startswith("You're in good shape."), body[:80])

    def test_markdown_confirmed_label(self):
        app = app_with([("blocker", "Done")])
        app["items"][0]["confirmed"] = "2026-11-03"
        self.assertIn("you confirmed 2026-11-03", report.render_markdown(single(app)))

    def test_markdown_no_applicable_items(self):
        md = report.render_markdown(single(app_with([("grow", "Not applicable")])))
        self.assertIn("Nothing on the checklist applies to this app.", md)


class HtmlTest(unittest.TestCase):
    def html(self, data=None):
        return report.render_html(data or load())

    def test_html_is_self_contained(self):
        page = self.html()
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        for banned in ("<link", 'src="http', "src='http", "@import", "url(http"):
            self.assertNotIn(banned, page)

    def test_html_ring_has_one_segment_per_applicable_item(self):
        page = self.html()
        self.assertEqual(page.count('class="seg '), 47)
        self.assertIn("40%", page)

    def test_html_escapes_repo_text(self):
        app = app_with([("blocker", "Missing")])
        app["items"][0]["title"] = "<script>alert(1)</script>"
        app["items"][0]["found"] = 'In `app/x.ts`: "><img src=x onerror=alert(1)>'
        page = self.html(single(app))
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("<code>app/x.ts</code>", page)

    def test_html_do_this_first(self):
        page = self.html()
        first = page.split('class="first"', 1)[1].split('<section class="tier"', 1)[0]
        self.assertIn("Replace the Stripe key saved in your code", first)
        self.assertEqual(first.count("<li>"), 5)

    def test_html_fixed_and_confirmed(self):
        app = app_with([("blocker", "Done"), ("grow", "Done"), ("grow", "Missing")])
        app["items"][0]["fixed"] = "2026-11-02"
        app["items"][1]["confirmed"] = "2026-11-03"
        page = self.html(single(app))
        self.assertIn('class="row fixed"', page)
        self.assertIn("Fixed just now", page)
        self.assertIn("you confirmed 2026-11-03", page)

    def test_html_multi_app_sections(self):
        web = app_with([("blocker", "Done"), ("grow", "Missing")])
        api = app_with([("blocker", "Missing"), ("grow", "Partial")])
        web["name"], web["path"], api["name"], api["path"] = "Web", "apps/web", "API", "apps/api"
        data = single(web)
        data["apps"].append(api)
        page = self.html(data)
        self.assertIn('class="overview"', page)
        overview = page.split('class="overview"', 1)[1].split("</nav>", 1)[0]
        self.assertIn("Web", overview)
        self.assertIn("API", overview)
        self.assertIn("50%", overview)
        self.assertIn("25%", overview)
        self.assertEqual(page.count('class="app-section"'), 2)
        self.assertEqual(page.count('class="ring"'), 2)

    def test_html_no_visible_ids(self):
        import re

        page = self.html()
        body = page.split("<body>", 1)[1].split("<script>", 1)[0]
        text = re.sub(r"<[^>]+>", " ", body)
        self.assertNotRegex(text, r"\b(web|common|macos|llm)\.[a-z]")


if __name__ == "__main__":
    unittest.main()
