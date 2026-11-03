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

    def test_score_counts_done_over_applicable(self):
        self.assertEqual(report.score(load()["apps"][0]), {"done": 12, "applicable": 47, "percent": 26})

    def test_score_with_no_applicable_items(self):
        app = app_with([("grow", "Not applicable"), ("polish", "Not applicable")])
        self.assertEqual(report.score(app), {"done": 0, "applicable": 0, "percent": 0})
        self.assertEqual(report.score(app_with([])), {"done": 0, "applicable": 0, "percent": 0})

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


if __name__ == "__main__":
    unittest.main()
