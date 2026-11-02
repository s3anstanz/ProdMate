import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_absent_returns_empty_v1(self):
        self.assertEqual(state.load(self.repo), {"version": 1, "decisions": {}, "runs": []})

    def test_round_trip(self):
        data = state.load(self.repo)
        state.record_decision(data, "common.analytics", "skip", "no analytics, by choice")
        state.record_run(data, {"common.ci": "Done", "web.seo": "Missing"})
        path = state.save(self.repo, data)
        self.assertEqual(path, self.repo / ".prodmate" / "state.json")
        self.assertEqual(state.load(self.repo), data)
        self.assertTrue(path.read_text().startswith('{\n  "version": 1'))

    def test_record_decision_shape(self):
        data = state.record_decision(state.load(self.repo), "common.analytics", "skip", "no analytics")
        decision = data["decisions"]["common.analytics"]
        self.assertEqual(decision["decision"], "skip")
        self.assertEqual(decision["reason"], "no analytics")
        self.assertRegex(decision["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_record_decision_overwrites_same_id(self):
        data = state.load(self.repo)
        state.record_decision(data, "web.seo", "skip", "private app")
        state.record_decision(data, "web.seo", "accept", "going public")
        self.assertEqual(len(data["decisions"]), 1)
        self.assertEqual(data["decisions"]["web.seo"]["decision"], "accept")

    def test_record_decision_rejects_unknown_decision(self):
        with self.assertRaises(ValueError):
            state.record_decision(state.load(self.repo), "web.seo", "maybe", "unsure")

    def test_runs_capped_at_10(self):
        data = state.load(self.repo)
        for i in range(12):
            state.record_run(data, {"common.ci": "Done" if i % 2 else "Missing"})
        self.assertEqual(len(data["runs"]), 10)
        self.assertEqual(data["runs"][-1]["statuses"], {"common.ci": "Done"})
        self.assertRegex(data["runs"][-1]["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_rejects_unknown_status(self):
        data = state.load(self.repo)
        for status in ("Done", "Partial", "Missing", "Can't verify", "Not applicable"):
            state.record_run(data, {"common.ci": status})
        with self.assertRaises(ValueError):
            state.record_run(data, {"common.ci": "Fine"})

    def test_cli_decide_and_show(self):
        cli = [sys.executable, str(SCRIPTS / "state.py")]
        subprocess.run(cli + ["decide", str(self.repo), "common.analytics", "skip", "no analytics"], check=True, capture_output=True)
        statuses = self.repo / "statuses.json"
        statuses.write_text(json.dumps({"common.ci": "Done"}))
        subprocess.run(cli + ["record", str(self.repo), str(statuses)], check=True, capture_output=True)
        out = subprocess.run(cli + ["show", str(self.repo)], check=True, capture_output=True, text=True)
        shown = json.loads(out.stdout)
        self.assertEqual(shown["decisions"]["common.analytics"]["reason"], "no analytics")
        self.assertEqual(shown["runs"][0]["statuses"], {"common.ci": "Done"})

    def test_cli_record_bad_status_exits_nonzero(self):
        statuses = self.repo / "statuses.json"
        statuses.write_text(json.dumps({"common.ci": "Fine"}))
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "state.py"), "record", str(self.repo), str(statuses)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / ".prodmate" / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
