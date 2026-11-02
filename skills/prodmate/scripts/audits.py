#!/usr/bin/env python3
"""Run free audit tools and normalize their output.

Usage:
    python3 scripts/audits.py available
    python3 scripts/audits.py run <name> <target> [--allow-install] [--runs N] [--timeout S]

Every result is an AuditResult:
    {"tool", "status": ok|issues|missing|error|skipped, "summary", "findings": [{"severity", "message", "location"}]}

Nothing is installed unless --allow-install is passed, and then only through
npx or pipx (never globally). gitleaks always runs with --redact, and no
parser ever copies a secret value into a result.
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

AUDITS = {
    "lighthouse": {
        "needs": "url",
        "runner": "npx",
        "package": "lighthouse@13",
        "binary": "lighthouse",
        "install_hint": "Lighthouse needs Node.js and Google Chrome; prodmate runs it with `npx --yes lighthouse@13` once you allow it.",
    },
    "osv-scanner": {
        "needs": "local",
        "runner": "path",
        "package": "osv-scanner",
        "binary": "osv-scanner",
        "install_hint": "osv-scanner isn't installed. Install it with `brew install osv-scanner` or see https://google.github.io/osv-scanner/installation/.",
    },
    "gitleaks": {
        "needs": "local",
        "runner": "path",
        "package": "gitleaks",
        "binary": "gitleaks",
        "install_hint": "gitleaks isn't installed. Install it with `brew install gitleaks` or see https://github.com/gitleaks/gitleaks#installing.",
    },
    "http-observatory": {
        "needs": "host",
        "runner": "npx",
        "package": "@mdn/mdn-http-observatory",
        "binary": "mdn-http-observatory-scan",
        "install_hint": "MDN HTTP Observatory needs Node.js; prodmate runs it with `npx --yes @mdn/mdn-http-observatory` once you allow it.",
    },
    "checkdmarc": {
        "needs": "domain",
        "runner": "pipx",
        "package": "checkdmarc",
        "binary": "checkdmarc",
        "install_hint": "checkdmarc needs pipx (`brew install pipx`); prodmate runs it with `pipx run checkdmarc` once you allow it.",
    },
    "codesign": {
        "needs": "macos-app",
        "runner": "builtin-macos",
        "package": "codesign",
        "binary": "codesign",
        "install_hint": "codesign and spctl ship with macOS; this check only runs on a Mac.",
    },
}

OSV_LOCKFILES = [
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "poetry.lock", "uv.lock", "Pipfile.lock",
    "requirements.txt", "Cargo.lock", "go.mod", "Package.resolved", "Gemfile.lock", "composer.lock", "pubspec.lock",
]
LIGHTHOUSE_CATEGORIES ="performance,accessibility,best-practices,seo"
LAUNCHERS = {"npx": ["npx", "--yes"], "pipx": ["pipx", "run"]}


class AuditError(Exception):
    """A tool ran but failed; the message is the one-line summary."""


def result(tool, status, summary, findings=None):
    return {"tool": tool, "status": status, "summary": summary, "findings": findings or []}


def one_line(text, limit=200):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    line = lines[-1] if lines else ""
    return line[:limit]


# Parsers: pure functions over already-loaded tool output.

def parse_lighthouse(reports):
    scores = {}
    titles = {}
    url = ""
    for report in reports:
        url = report.get("finalDisplayedUrl") or report.get("requestedUrl") or url
        for key, category in report.get("categories", {}).items():
            titles[key] = category.get("title", key)
            if category.get("score") is not None:
                scores.setdefault(key, []).append(category["score"])
    findings = []
    parts = []
    for key in sorted(scores):
        median = statistics.median(scores[key])
        parts.append(f"{titles[key]} {median:.2f}")
        if median < 0.5:
            severity = "high"
        elif median < 0.9:
            severity = "medium"
        else:
            continue
        findings.append({
            "severity": severity,
            "message": f"{titles[key]} score {median:.2f} (median of {len(scores[key])} runs)",
            "location": url,
        })
    summary = f"Lighthouse median of {len(reports)} runs: " + ", ".join(parts)
    return result("lighthouse", "issues" if findings else "ok", summary, findings)


def cvss_severity(score):
    if score is None:
        return "low"
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def parse_osv(data):
    if not isinstance(data, dict) or "results" not in data:
        raise AuditError("osv-scanner printed JSON without a results list")
    findings = []
    for source in data.get("results") or []:
        location = (source.get("source") or {}).get("path", "")
        for pkg in source.get("packages") or []:
            info = pkg.get("package") or {}
            name = f"{info.get('name')}@{info.get('version')}"
            groups = pkg.get("groups") or [{"ids": [v.get("id") for v in pkg.get("vulnerabilities") or []]}]
            for group in groups:
                try:
                    score = float(group.get("max_severity") or "")
                except ValueError:
                    score = None
                ids = ", ".join(i for i in group.get("ids") or [] if i)
                label = f"CVSS {score:g}" if score is not None else "severity unknown"
                findings.append({"severity": cvss_severity(score), "message": f"{name}: {ids} ({label})", "location": location})
    if not findings:
        return result("osv-scanner", "ok", "osv-scanner found no known vulnerabilities")
    packages = len({f["message"].split(":", 1)[0] for f in findings})
    return result("osv-scanner", "issues", f"osv-scanner found {len(findings)} vulnerabilities in {packages} packages", findings)


def parse_gitleaks(data):
    if not isinstance(data, list):
        raise AuditError("gitleaks report isn't a JSON list")
    findings = []
    for leak in data:
        location = f"{leak.get('File', '?')}:{leak.get('StartLine', '?')}"
        findings.append({"severity": "high", "message": f"{leak.get('RuleID', 'secret')} in {location}", "location": location})
    if not findings:
        return result("gitleaks", "ok", "gitleaks found no secrets")
    return result("gitleaks", "issues", f"gitleaks found {len(findings)} possible secrets (values redacted)", findings)


def parse_observatory(data):
    scan = data.get("scan") if isinstance(data, dict) else None
    if not isinstance(scan, dict):
        raise AuditError("HTTP Observatory output has no scan section")
    if scan.get("error"):
        raise AuditError(f"HTTP Observatory error: {one_line(str(scan['error']))}")
    grade = scan.get("grade") or "?"
    letter = grade[:1].upper()
    findings = []
    if letter in ("C", "D"):
        findings.append({"severity": "medium", "message": f"HTTP Observatory grade {grade} (score {scan.get('score')})", "location": ""})
    elif letter in ("E", "F"):
        findings.append({"severity": "high", "message": f"HTTP Observatory grade {grade} (score {scan.get('score')})", "location": ""})
    for name, test in sorted((data.get("tests") or {}).items()):
        if isinstance(test, dict) and test.get("pass") is False:
            findings.append({"severity": "info", "message": f"{name}: {test.get('result')}", "location": ""})
    status = "issues" if letter not in ("A", "B") else "ok"
    return result("http-observatory", status, f"HTTP Observatory grade {grade} ({scan.get('testsPassed')}/{scan.get('testsQuantity')} tests passed)", findings)


def parse_checkdmarc(data):
    if not isinstance(data, dict) or "domain" not in data:
        raise AuditError("checkdmarc output has no domain")
    domain = data["domain"]
    findings = []
    spf = data.get("spf") or {}
    if not spf.get("record") or spf.get("valid") is False:
        findings.append({"severity": "high", "message": f"No valid SPF record: {one_line(str(spf.get('error', 'missing')))}", "location": domain})
    dmarc = data.get("dmarc") or {}
    if not dmarc.get("record") or dmarc.get("valid") is False:
        findings.append({"severity": "high", "message": f"No valid DMARC record: {one_line(str(dmarc.get('error', 'missing')))}", "location": domain})
    else:
        policy = ((dmarc.get("tags") or {}).get("p") or {}).get("value")
        if policy == "none":
            findings.append({"severity": "medium", "message": "DMARC policy is p=none, so spoofed mail is still delivered", "location": domain})
    findings.append({"severity": "info", "message": "DKIM can't be confirmed from DNS without the email provider's selector", "location": domain})
    serious = [f for f in findings if f["severity"] in ("high", "medium")]
    summary = f"checkdmarc on {domain}: " + ("SPF and DMARC look right" if not serious else f"{len(serious)} problems")
    return result("checkdmarc", "issues" if serious else "ok", summary, findings)


def parse_codesign(codesign_rc, codesign_out, spctl_rc, spctl_out):
    findings = []
    if codesign_rc != 0:
        findings.append({"severity": "high", "message": f"codesign: {one_line(codesign_out)}", "location": ""})
    if spctl_rc != 0 or "rejected" in spctl_out:
        lines = [line.strip() for line in spctl_out.splitlines() if line.strip()]
        reason = next((line for line in lines if "rejected" in line or line.startswith("source=")), one_line(spctl_out))
        findings.append({"severity": "high", "message": f"spctl: {reason}", "location": ""})
    if findings:
        return result("codesign", "issues", "Gatekeeper would block this app for other people", findings)
    source = next((line.strip() for line in spctl_out.splitlines() if line.strip().startswith("source=")), "accepted")
    return result("codesign", "ok", f"Signed and accepted by Gatekeeper ({source})")


# Running tools.

def available(name):
    entry = AUDITS[name]
    info = {"name": name, "available": False, "via": None, "install_hint": entry["install_hint"]}
    if entry["runner"] == "builtin-macos":
        if sys.platform == "darwin" and shutil.which("codesign") and shutil.which("spctl"):
            info.update(available=True, via="builtin")
        return info
    if shutil.which(entry["binary"]):
        info.update(available=True, via="path")
    elif entry["runner"] in LAUNCHERS and shutil.which(entry["runner"]):
        info.update(available=True, via=entry["runner"])
    return info


def command_prefix(name, allow_install):
    """Return the argv prefix that runs the tool, or None when it can't run without an install."""
    entry = AUDITS[name]
    if shutil.which(entry["binary"]):
        return [entry["binary"]]
    if entry["runner"] == "path" or not allow_install:
        return None
    if shutil.which(entry["runner"]):
        return LAUNCHERS[entry["runner"]] + [entry["package"]]
    return None


def execute(name, argv, timeout, ok_codes=(0,)):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AuditError(f"{name} timed out after {timeout}s")
    except OSError as exc:
        raise AuditError(f"{name} could not start: {exc.strerror or exc}")
    if proc.returncode not in ok_codes:
        detail = one_line(proc.stderr) or one_line(proc.stdout) or "no output"
        raise AuditError(f"{name} exited with code {proc.returncode}: {detail}")
    return proc


def load_json(name, text):
    try:
        return json.loads(text)
    except ValueError:
        raise AuditError(f"{name} printed output that isn't JSON")


def run_lighthouse(prefix, target, runs, timeout):
    reports = []
    for _ in range(runs):
        argv = prefix + [target, "--output=json", "--quiet", "--chrome-flags=--headless=new", f"--only-categories={LIGHTHOUSE_CATEGORIES}"]
        reports.append(load_json("lighthouse", execute("lighthouse", argv, timeout).stdout))
    return parse_lighthouse(reports)


def osv_call(argv, timeout):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AuditError(f"osv-scanner timed out after {timeout}s")
    except OSError as exc:
        raise AuditError(f"osv-scanner could not start: {exc.strerror or exc}")
    no_sources = proc.returncode == 128 and "No package sources found" in proc.stderr
    if not no_sources and proc.returncode not in (0, 1):
        detail = one_line(proc.stderr) or "no output"
        raise AuditError(f"osv-scanner exited with code {proc.returncode}: {detail}")
    return proc, no_sources


def run_osv(prefix, target, timeout):
    proc, no_sources = osv_call(prefix + ["scan", "source", "-r", "--format", "json", target], timeout)
    if not no_sources:
        return parse_osv(load_json("osv-scanner", proc.stdout))
    # A recursive scan skips paths an enclosing repo's .gitignore hides, so scan root lockfiles directly.
    lockfiles = [str(Path(target, name)) for name in OSV_LOCKFILES if Path(target, name).is_file()]
    if not lockfiles:
        return result("osv-scanner", "ok", "No package sources found: osv-scanner found no lockfile or manifest to check")
    results = []
    for lockfile in lockfiles:
        proc, _ = osv_call(prefix + ["scan", "source", "-L", lockfile, "--format", "json"], timeout)
        data = load_json("osv-scanner", proc.stdout)
        results += data.get("results") or [] if isinstance(data, dict) else []
    return parse_osv({"results": results})


def is_git_repo(path):
    try:
        proc = subprocess.run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def gitleaks_scan(prefix, mode, target, timeout):
    fd, report = tempfile.mkstemp(suffix=".json", prefix="prodmate-gitleaks-")
    os.close(fd)
    try:
        argv = prefix + [mode, target, "--redact", "--report-format", "json", "--report-path", report, "--exit-code", "0"]
        execute("gitleaks", argv, timeout)
        data = load_json("gitleaks", Path(report).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise AuditError("gitleaks report isn't a JSON list")
        return data
    finally:
        os.unlink(report)


def run_gitleaks(prefix, target, timeout):
    # `gitleaks git` reads only commits, so a git repo also gets a `dir` scan for uncommitted files.
    modes = ["git", "dir"] if is_git_repo(target) else ["dir"]
    leaks, seen = [], set()
    for mode in modes:
        for leak in gitleaks_scan(prefix, mode, target, timeout):
            key = (leak.get("RuleID"), os.path.normpath(os.path.join(target, leak.get("File", ""))), leak.get("StartLine"))
            if key not in seen:
                seen.add(key)
                leaks.append(leak)
    return parse_gitleaks(leaks)


def run_codesign(target, timeout):
    codesign = subprocess.run(["codesign", "-vvv", "--deep", "--strict", target], capture_output=True, text=True, timeout=timeout)
    spctl = subprocess.run(["spctl", "-vvv", "--assess", "--type", "exec", target], capture_output=True, text=True, timeout=timeout)
    return parse_codesign(codesign.returncode, codesign.stdout + codesign.stderr, spctl.returncode, spctl.stdout + spctl.stderr)


def run(name, target, allow_install=False, runs=3, timeout=300):
    if name not in AUDITS:
        return result(name, "error", f"unknown audit '{name}'")
    try:
        if name == "codesign":
            if sys.platform != "darwin":
                return result(name, "skipped", "codesign only runs on macOS")
            try:
                return run_codesign(target, timeout)
            except subprocess.TimeoutExpired:
                raise AuditError(f"codesign timed out after {timeout}s")
        prefix = command_prefix(name, allow_install)
        if prefix is None:
            return result(name, "missing", AUDITS[name]["install_hint"])
        if name == "lighthouse":
            return run_lighthouse(prefix, target, runs, timeout)
        if name == "osv-scanner":
            return run_osv(prefix, target, timeout)
        if name == "gitleaks":
            return run_gitleaks(prefix, target, timeout)
        if name == "http-observatory":
            return parse_observatory(load_json(name, execute(name, prefix + [target], timeout).stdout))
        if name == "checkdmarc":
            return parse_checkdmarc(load_json(name, execute(name, prefix + [target], timeout).stdout))
    except AuditError as exc:
        return result(name, "error", str(exc))
    return result(name, "error", f"no runner for '{name}'")


def main(argv):
    parser = argparse.ArgumentParser(prog="audits.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("available")
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("name", choices=sorted(AUDITS))
    run_cmd.add_argument("target")
    run_cmd.add_argument("--allow-install", action="store_true")
    run_cmd.add_argument("--runs", type=int, default=3)
    run_cmd.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv[1:])
    if args.command == "available":
        print(json.dumps([available(name) for name in AUDITS], indent=2))
    else:
        print(json.dumps(run(args.name, args.target, args.allow_install, args.runs, args.timeout), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
