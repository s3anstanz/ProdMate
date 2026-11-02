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

    # Manifests are written at test time so the repo holds no pinned dependency files for scanners to flag.

    def test_monorepo_two_apps(self):
        self.make("package.json", '{"name": "mono", "private": true, "workspaces": ["apps/*"]}')
        self.make("apps/web/package.json", '{"dependencies": {"next": "15.0.0", "react-dom": "19.0.0"}}')
        self.make("apps/api/package.json", '{"dependencies": {"express": "4.21.0"}}')
        result = detect.detect(self.tmpdir)
        apps = {app["path"]: app["types"] for app in result["apps"]}
        self.assertEqual(apps, {"apps/web": ["web-app"], "apps/api": ["api-backend"]})

    def test_llm_overlay(self):
        self.make("requirements.txt", "flask==3.0.3\nanthropic>=0.40\n")
        result = detect.detect(self.tmpdir)
        self.assertEqual(result["apps"][0]["types"], ["api-backend"])
        self.assertEqual([o["id"] for o in result["overlays"]], ["llm-app"])
        self.assertEqual(result["overlays"][0]["path"], ".")
        self.assertIn("requirements.txt: anthropic", result["overlays"][0]["evidence"])
        self.assertIn("requirements.txt", result["apps"][0]["lockfiles"])

    def test_static_site(self):
        result = detect.detect(FIXTURES / "static-site")
        self.assertEqual(result["apps"][0]["types"], ["web-app"])

    def test_static_site_built_for_github_pages(self):
        course = self.tmpdir / "course"
        course.mkdir()
        (course / "package.json").write_text('{"devDependencies": {"playwright": "1.50.0"}}')
        (course / "template.html").write_text("<!doctype html><title>Course</title>")
        workflows = self.tmpdir / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "pages.yml").write_text("jobs:\n  deploy:\n    steps:\n      - uses: actions/deploy-pages@v4\n")
        result = detect.detect(self.tmpdir)
        apps = {app["path"]: app for app in result["apps"]}
        self.assertEqual(apps["course"]["types"], ["web-app"])
        self.assertIn(".github/workflows/pages.yml", apps["course"]["deploy"])

    def test_html_without_pages_deploy_is_not_web_app(self):
        tool = self.tmpdir / "tool"
        tool.mkdir()
        (tool / "package.json").write_text('{"bin": "tool"}')
        (tool / "report.html").write_text("<!doctype html>")
        result = detect.detect(self.tmpdir)
        self.assertEqual(result["apps"][0]["types"], ["cli"])

    def test_nothing_leaves_your_machine_is_a_promise(self):
        (self.tmpdir / "package.json").write_text('{"bin": "x"}')
        (self.tmpdir / "README.md").write_text("# X\n\nA local dashboard. Nothing leaves your machine.\n")
        result = detect.detect(self.tmpdir)
        self.assertEqual([p["line"] for p in result["promises"]], [3])

    def make(self, rel, text=""):
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_react_native_ios_folder_is_part_of_the_app(self):
        self.make("package.json", '{"dependencies": {"react-native": "0.76.0"}}')
        self.make("ios/App.xcodeproj/project.pbxproj", "SDKROOT = iphoneos;")
        self.make("android/build.gradle", "")
        result = detect.detect(self.tmpdir)
        self.assertEqual([(a["path"], a["types"]) for a in result["apps"]], [(".", ["ios-android"])])

    def test_flutter_platform_folders_are_part_of_the_app(self):
        self.make("pubspec.yaml", "name: app\nflutter:\n  uses-material-design: true\n")
        self.make("ios/Runner.xcodeproj/project.pbxproj", "SDKROOT = iphoneos;")
        self.make("macos/Runner.xcodeproj/project.pbxproj", "SDKROOT = macosx;")
        result = detect.detect(self.tmpdir)
        self.assertEqual([a["path"] for a in result["apps"]], ["."])
        self.assertIn("ios-android", result["apps"][0]["types"])

    def test_xcode_project_in_subfolder_is_one_app(self):
        self.make("Mac/Mac.xcodeproj/project.pbxproj", "SDKROOT = macosx;")
        result = detect.detect(self.tmpdir)
        self.assertEqual([(a["path"], a["types"]) for a in result["apps"]], [("Mac", ["macos-app"])])

    def test_ignores_dot_dirs_examples_and_git_ignored_dirs(self):
        self.make("package.json", '{"dependencies": {"next": "15.0.0"}}')
        for rel in (".worktrees/feat", ".output/server", ".yarn/sdks/typescript", "examples/demo", "generated/site"):
            self.make(f"{rel}/package.json", '{"dependencies": {"next": "15.0.0"}, "main": "x.js"}')
        self.make(".gitignore", "generated/\n")
        subprocess.run(["git", "-C", str(self.tmpdir), "init", "-q"], check=True)
        result = detect.detect(self.tmpdir)
        self.assertEqual([a["path"] for a in result["apps"]], ["."])

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
