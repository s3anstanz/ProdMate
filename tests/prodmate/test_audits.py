import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
OUTPUT = Path(__file__).resolve().parent / "fixtures" / "audit-output"
sys.path.insert(0, str(SCRIPTS))

import audits


def load(name):
    return json.loads((OUTPUT / name).read_text())


def text(name):
    return (OUTPUT / name).read_text()


class ParserTest(unittest.TestCase):
    def test_parse_lighthouse_takes_median(self):
        base = load("lighthouse.json")
        reports = []
        for seo in (0.4, 0.95, 0.92):
            report = copy.deepcopy(base)
            report["categories"]["seo"]["score"] = seo
            reports.append(report)
        result = audits.parse_lighthouse(reports)
        self.assertEqual(result["tool"], "lighthouse")
        self.assertFalse([f for f in result["findings"] if "SEO" in f["message"]])
        self.assertIn("median of 3", result["summary"])

    def test_parse_lighthouse_low_score_is_high(self):
        base = load("lighthouse.json")
        reports = []
        for perf in (0.3, 0.45, 0.6):
            report = copy.deepcopy(base)
            report["categories"]["performance"]["score"] = perf
            reports.append(report)
        result = audits.parse_lighthouse(reports)
        self.assertEqual(result["status"], "issues")
        perf = [f for f in result["findings"] if "Performance" in f["message"]]
        self.assertEqual([f["severity"] for f in perf], ["high"])

    def test_parse_lighthouse_recorded_seo_is_medium(self):
        # The recorded example.com run scored SEO 0.8.
        result = audits.parse_lighthouse([load("lighthouse.json")])
        seo = [f for f in result["findings"] if "SEO" in f["message"]]
        self.assertEqual([f["severity"] for f in seo], ["medium"])

    def test_parse_osv_maps_cvss(self):
        result = audits.parse_osv(load("osv-scanner.json"))
        self.assertEqual(result["status"], "issues")
        severities = sorted(f["severity"] for f in result["findings"])
        # Recorded postcss 8.4.31 groups: CVSS 7.5, 6.3, 6.1, 7.5.
        self.assertEqual(severities, ["high", "high", "medium", "medium"])
        self.assertTrue(all("postcss@8.4.31" in f["message"] for f in result["findings"]))

    def test_parse_osv_no_vulns_is_ok(self):
        result = audits.parse_osv({"results": []})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["findings"], [])

    def test_parse_gitleaks_never_contains_secret(self):
        data = load("gitleaks.json")
        planted = copy.deepcopy(data)
        planted[0]["Secret"] = "sk_live_should_never_appear_123"
        planted[0]["Match"] = 'PAYMENTS_API_SECRET = "sk_live_should_never_appear_123"'
        result = audits.parse_gitleaks(planted)
        self.assertEqual(result["status"], "issues")
        self.assertTrue(all(f["severity"] == "high" for f in result["findings"]))
        self.assertIn("generic-api-key in /repo/lib/config.ts:3", [f["message"] for f in result["findings"]])
        dumped = json.dumps(result)
        for record in planted:
            for value in (record["Secret"], record["Match"]):
                self.assertNotIn(value, dumped)

    def test_parse_observatory_grade(self):
        result = audits.parse_observatory(load("observatory.json"))
        self.assertEqual(result["status"], "ok")
        self.assertIn("A+", result["summary"])
        worse = load("observatory.json")
        worse["scan"]["grade"] = "C"
        self.assertEqual([f["severity"] for f in audits.parse_observatory(worse)["findings"] if "grade" in f["message"]], ["medium"])
        worse["scan"]["grade"] = "F"
        self.assertEqual([f["severity"] for f in audits.parse_observatory(worse)["findings"] if "grade" in f["message"]], ["high"])

    def test_parse_checkdmarc_recorded_is_ok(self):
        result = audits.parse_checkdmarc(load("checkdmarc.json"))
        self.assertEqual(result["status"], "ok")
        self.assertFalse([f for f in result["findings"] if f["severity"] in ("high", "medium")])

    def test_parse_checkdmarc_missing_dmarc_is_high(self):
        data = load("checkdmarc.json")
        data["dmarc"] = {"record": None, "valid": False, "error": "A DMARC record does not exist for this domain or its base domain"}
        result = audits.parse_checkdmarc(data)
        self.assertEqual(result["status"], "issues")
        self.assertEqual([f["severity"] for f in result["findings"] if "DMARC" in f["message"]], ["high"])

    def test_parse_checkdmarc_p_none_is_medium(self):
        data = load("checkdmarc.json")
        data["dmarc"]["tags"]["p"]["value"] = "none"
        result = audits.parse_checkdmarc(data)
        self.assertEqual([f["severity"] for f in result["findings"] if "p=none" in f["message"]], ["medium"])

    def test_parse_codesign_adhoc_rejected(self):
        result = audits.parse_codesign(0, text("codesign.out"), 3, text("spctl.out"))
        self.assertEqual(result["status"], "issues")
        self.assertEqual([f["severity"] for f in result["findings"]], ["high"])
        self.assertIn("rejected", result["findings"][0]["message"])


class RunTest(unittest.TestCase):
    def test_audits_registry(self):
        self.assertEqual(
            set(audits.AUDITS),
            {"lighthouse", "osv-scanner", "gitleaks", "http-observatory", "checkdmarc", "codesign"},
        )
        for entry in audits.AUDITS.values():
            self.assertIn(entry["needs"], {"local", "url", "host", "domain", "macos-app"})
            self.assertIn(entry["runner"], {"npx", "pipx", "path", "builtin-macos"})
            self.assertTrue(entry["package"] and entry["install_hint"])

    def test_missing_tool_returns_missing(self):
        with mock.patch.object(audits.shutil, "which", return_value=None):
            result = audits.run("osv-scanner", "/repo", allow_install=False)
            self.assertEqual(result["status"], "missing")
            self.assertEqual(result["summary"], audits.AUDITS["osv-scanner"]["install_hint"])
            self.assertFalse(audits.available("osv-scanner")["available"])

    def test_npx_tool_without_install_consent_is_missing(self):
        def which(name):
            return "/usr/bin/npx" if name == "npx" else None

        with mock.patch.object(audits.shutil, "which", side_effect=which), \
                mock.patch.object(audits.subprocess, "run") as run:
            result = audits.run("lighthouse", "http://localhost:3000", allow_install=False)
            self.assertEqual(result["status"], "missing")
            run.assert_not_called()
            self.assertEqual(audits.available("lighthouse")["via"], "npx")

    def test_garbage_output_returns_error(self):
        garbage = subprocess.CompletedProcess(args=[], returncode=0, stdout=text("garbage.txt"), stderr="")
        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/osv-scanner"), \
                mock.patch.object(audits.subprocess, "run", return_value=garbage):
            result = audits.run("osv-scanner", "/repo")
        self.assertEqual(result["status"], "error")
        self.assertEqual(len(result["summary"].splitlines()), 1)

    def test_unexpected_exit_code_returns_error(self):
        crashed = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="panic: boom\n")
        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/osv-scanner"), \
                mock.patch.object(audits.subprocess, "run", return_value=crashed):
            result = audits.run("osv-scanner", "/repo")
        self.assertEqual(result["status"], "error")
        self.assertIn("panic: boom", result["summary"])

    def test_osv_no_package_sources_is_ok(self):
        nothing = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="No package sources found, --help for usage information.\n"
        )
        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/osv-scanner"), \
                mock.patch.object(audits.subprocess, "run", return_value=nothing):
            result = audits.run("osv-scanner", "/repo")
        self.assertEqual(result["status"], "ok")
        self.assertIn("No package sources found", result["summary"])

    def test_osv_no_sources_but_lockfile_present_rescans_lockfile(self):
        import tempfile

        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "package-lock.json").write_text("{}")
            calls = []

            def fake_run(argv, **kwargs):
                calls.append(argv)
                if "-L" in argv:
                    return subprocess.CompletedProcess(argv, 1, stdout=text("osv-scanner.json"), stderr="")
                return subprocess.CompletedProcess(argv, 128, stdout="", stderr="No package sources found, --help for usage information.\n")

            with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/osv-scanner"), \
                    mock.patch.object(audits.subprocess, "run", side_effect=fake_run):
                result = audits.run("osv-scanner", repo)
        self.assertEqual(result["status"], "issues")
        self.assertEqual(len(calls), 2)
        self.assertIn(str(Path(repo, "package-lock.json")), calls[1])

    def test_timeout_returns_error(self):
        boom = subprocess.TimeoutExpired(cmd=["osv-scanner"], timeout=300)
        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/osv-scanner"), \
                mock.patch.object(audits.subprocess, "run", side_effect=boom):
            result = audits.run("osv-scanner", "/repo", timeout=300)
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["summary"])

    def test_gitleaks_git_repo_also_scans_uncommitted_files(self):
        leak = load("gitleaks.json")[:1]
        modes = []

        def fake_run(argv, **kwargs):
            mode = argv[1]
            modes.append(mode)
            report = argv[argv.index("--report-path") + 1]
            Path(report).write_text(json.dumps(leak if mode == "dir" else []))
            return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/gitleaks"), \
                mock.patch.object(audits, "is_git_repo", return_value=True), \
                mock.patch.object(audits.subprocess, "run", side_effect=fake_run):
            result = audits.run("gitleaks", "/repo")
        self.assertEqual(sorted(modes), ["dir", "git"])
        self.assertEqual(result["status"], "issues")
        self.assertEqual(len(result["findings"]), 1)

    def test_codesign_skipped_off_macos(self):
        with mock.patch.object(audits.sys, "platform", "linux"):
            result = audits.run("codesign", "/repo/build/App.app")
        self.assertEqual(result["status"], "skipped")

    def test_lighthouse_runs_three_times(self):
        report = subprocess.CompletedProcess(args=[], returncode=0, stdout=text("lighthouse.json"), stderr="")
        with mock.patch.object(audits.shutil, "which", return_value="/usr/local/bin/lighthouse"), \
                mock.patch.object(audits.subprocess, "run", return_value=report) as run:
            result = audits.run("lighthouse", "https://example.com")
        self.assertEqual(run.call_count, 3)
        self.assertIn("median of 3", result["summary"])

    def test_cli_available_prints_json_list(self):
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "audits.py"), "available"], capture_output=True, text=True, check=True
        )
        names = [entry["name"] for entry in json.loads(out.stdout)]
        self.assertEqual(sorted(names), sorted(audits.AUDITS))


if __name__ == "__main__":
    unittest.main()
