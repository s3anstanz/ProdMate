#!/usr/bin/env python3
"""Run audits.py against the real gitleaks and osv-scanner, not recorded output.

The unit tests use recorded tool output and mocks; this catches a tool changing its
output or behavior in a new version. It needs gitleaks and osv-scanner on PATH and
network access (osv-scanner queries osv.dev). CI runs it in its own job:

    python3 tests/prodmate/integration_check.py

Every value it plants is random and generated at run time; nothing real is committed.
"""
import json
import secrets
import string
import subprocess
import sys
import tempfile
from pathlib import Path

AUDITS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts" / "audits.py"
failures = []


def fake_key():
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))


def audit(name, target):
    out = subprocess.run([sys.executable, str(AUDITS), "run", name, str(target)], capture_output=True, text=True)
    if out.returncode != 0:
        failures.append(f"{name}: audits.py exited {out.returncode}: {out.stderr.strip()[-200:]}")
        return {}
    return json.loads(out.stdout)


def check(condition, message):
    print(("ok   " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    # gitleaks: one secret only in history, one only in an uncommitted file.
    repo = tmp / "leaky"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "ci@example.com")
    git(repo, "config", "user.name", "ci")
    history_key, working_key = fake_key(), fake_key()
    (repo / "config.ts").write_text(f'export const PAYMENTS_API_SECRET = "{history_key}";\n')
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "add config")
    (repo / "config.ts").write_text("export const PAYMENTS_API_SECRET = process.env.PAYMENTS_API_SECRET;\n")
    git(repo, "commit", "-qam", "read the key from the environment")
    (repo / "local.ts").write_text(f'const SERVICE_API_SECRET = "{working_key}";\n')

    result = audit("gitleaks", repo)
    dumped = json.dumps(result)
    messages = [f["message"] for f in result.get("findings", [])]
    check(result.get("status") == "issues", f"gitleaks finds the planted keys (status {result.get('status')!r})")
    check(any("git history (commit" in m and "config.ts" in m for m in messages), "gitleaks reports the history-only key with its commit")
    check(any("local.ts" in m for m in messages), "gitleaks reports the uncommitted key")
    check(history_key not in dumped and working_key not in dumped, "no secret value appears in the result")

    # osv-scanner: a lockfile with a known-vulnerable package, and a folder with nothing to scan.
    app = tmp / "app"
    app.mkdir()
    (app / "package-lock.json").write_text(json.dumps({
        "name": "app", "version": "1.0.0", "lockfileVersion": 3, "requires": True,
        "packages": {
            "": {"name": "app", "version": "1.0.0", "dependencies": {"lodash": "4.17.20"}},
            # osv-scanner only checks entries resolved from the registry, so keep npm's resolved/integrity fields.
            "node_modules/lodash": {
                "version": "4.17.20",
                "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.20.tgz",
                "integrity": "sha512-PlhdFcillOINfeV7Ni6oF1TAEayyZBoZ8bcshTHqOYJYlrqzRK5hagpagky5o4HfCzzd1TRkXPMFq6cKk9rGmA==",
            },
        },
    }))
    result = audit("osv-scanner", app)
    check(result.get("status") == "issues", f"osv-scanner flags lodash@4.17.20 (status {result.get('status')!r})")
    check(any("lodash@4.17.20" in f["message"] for f in result.get("findings", [])), "the finding names the package and version")

    empty = tmp / "empty"
    empty.mkdir()
    (empty / "README.md").write_text("# nothing to scan\n")
    result = audit("osv-scanner", empty)
    check(result.get("status") == "ok" and "No package sources found" in result.get("summary", ""),
          f"osv-scanner with nothing to scan says so (status {result.get('status')!r})")

if failures:
    print(f"\n{len(failures)} check(s) failed")
    sys.exit(1)
print("\nall real-tool checks passed")
