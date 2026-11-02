import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "detect"
sys.path.insert(0, str(SCRIPTS))

import detect


class DetectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def copy_fixture(self, name):
        dest = self.tmpdir / name
        shutil.copytree(FIXTURES / name, dest)
        return dest

    def test_macos_spm_app(self):
        result = detect.detect(FIXTURES / "macos-spm")
        self.assertEqual(len(result["apps"]), 1)
        self.assertEqual(result["apps"][0]["path"], ".")
        self.assertEqual(result["apps"][0]["types"], ["macos-app"])
        self.assertIn("swift", result["apps"][0]["stack"])
        promises = [p for p in result["promises"] if "never touches the network" in p["text"]]
        self.assertEqual(len(promises), 1)
        self.assertEqual(promises[0]["file"], "README.md")
        self.assertEqual(promises[0]["line"], 5)

    def test_ignores_worktree_copies(self):
        repo = self.copy_fixture("macos-spm")
        copy = repo / ".claude" / "worktrees" / "x"
        copy.mkdir(parents=True)
        (copy / "package.json").write_text('{"dependencies": {"next": "15.0.0"}}')
        module = repo / "node_modules" / "foo"
        module.mkdir(parents=True)
        (module / "package.json").write_text('{"dependencies": {"express": "4.0.0"}, "bin": "foo"}')
        result = detect.detect(repo)
        self.assertEqual(len(result["apps"]), 1)
        self.assertEqual(result["apps"][0]["types"], ["macos-app"])

    def test_monorepo_two_apps(self):
        result = detect.detect(FIXTURES / "monorepo")
        apps = {app["path"]: app["types"] for app in result["apps"]}
        self.assertEqual(apps, {"apps/web": ["web-app"], "apps/api": ["api-backend"]})

    def test_llm_overlay(self):
        result = detect.detect(FIXTURES / "llm-flask")
        self.assertEqual(result["apps"][0]["types"], ["api-backend"])
        self.assertEqual([o["id"] for o in result["overlays"]], ["llm-app"])
        self.assertEqual(result["overlays"][0]["path"], ".")
        self.assertIn("requirements.txt: anthropic", result["overlays"][0]["evidence"])
        self.assertIn("requirements.txt", result["apps"][0]["lockfiles"])

    def test_static_site(self):
        result = detect.detect(FIXTURES / "static-site")
        self.assertEqual(result["apps"][0]["types"], ["web-app"])

    def test_no_git_no_readme(self):
        (self.tmpdir / "package.json").write_text('{"bin": "x"}')
        result = detect.detect(self.tmpdir)
        self.assertEqual(result["git"], {"is_repo": False, "has_remote": False, "tag_count": 0})
        self.assertEqual(result["promises"], [])
        self.assertEqual(result["apps"][0]["types"], ["cli"])

    def test_git_tags_and_remote_counted(self):
        repo = self.copy_fixture("static-site")
        run = lambda *args: subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
        run("init", "-q")
        run("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "init")
        run("tag", "v0.1.0")
        run("remote", "add", "origin", "https://example.com/x.git")
        result = detect.detect(repo)
        self.assertEqual(result["git"], {"is_repo": True, "has_remote": True, "tag_count": 1})

    def test_cli_outputs_json(self):
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "detect.py"), str(FIXTURES / "macos-spm")],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(out.stdout)
        self.assertEqual(data["apps"][0]["types"], ["macos-app"])


if __name__ == "__main__":
    unittest.main()
