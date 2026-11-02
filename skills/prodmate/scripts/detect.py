#!/usr/bin/env python3
"""Detect what kind of app a repo holds.

Usage: python3 scripts/detect.py <repo>

Prints JSON: git facts, one entry per app root (types, evidence, stack,
lockfiles, deploy files), overlays, stated promises and CI files.
Reads files only; runs nothing but read-only git commands.
"""
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from xml.parsers.expat import ExpatError

MAX_DEPTH = 3
IGNORED_DIRS = {
    "node_modules", ".git", ".build", "build", "dist", ".next", "out", "vendor", ".venv", "venv",
    "__pycache__", "target", "DerivedData", "Pods", ".claude", ".agents", ".cursor",
}
ROOT_MARKERS = {
    "package.json", "Package.swift", "pyproject.toml", "requirements.txt", "Cargo.toml",
    "go.mod", "manifest.json", "pubspec.yaml",
}
LOCKFILES = [
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "poetry.lock",
    "uv.lock", "Pipfile.lock", "requirements.txt", "Cargo.lock", "go.sum", "Package.resolved",
    "Gemfile.lock",
]
DEPLOY_FILES = [
    "vercel.json", "netlify.toml", "fly.toml", "render.yaml", "railway.json", "wrangler.toml",
    "Procfile", "Dockerfile", "app.yaml",
]
WEB_DEPS = {"next", "react-dom", "vue", "svelte", "@sveltejs/kit", "astro", "nuxt", "@remix-run/react", "vite"}
API_DEPS = {"express", "fastify", "hono", "koa", "@nestjs/core", "fastapi", "flask", "django"}
MOBILE_DEPS = {"expo", "react-native"}
LLM_DEPS = {
    "openai", "anthropic", "@anthropic-ai/sdk", "ai", "llamaindex", "google-generativeai",
    "@google/genai", "ollama", "cohere", "mistralai", "groq-sdk",
}
LLM_PREFIXES = ("@ai-sdk/", "langchain", "@langchain/")
PROMISE_FILES = re.compile(r"^(README.*|AGENTS\.md|CLAUDE\.md|PRIVACY.*|SECURITY\.md)$", re.IGNORECASE)
PROMISE = re.compile(
    r"no network|never touches the network|offline|no analytics|no tracking|no telemetry|never uploads"
    r"|(does not|doesn't|never) (collect|track|upload|send)|local[- ]only|no third-party",
    re.IGNORECASE,
)


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def walk(root, max_depth):
    """Yield (dir, dirnames, filenames) under root, skipping ignored dirs, up to max_depth levels."""
    for current, dirnames, filenames in os.walk(root):
        depth = len(Path(current).relative_to(root).parts)
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
        if depth >= max_depth:
            dirnames[:] = []
        yield Path(current), dirnames, filenames


def find_app_roots(repo):
    roots = [repo]
    for current, dirnames, filenames in walk(repo, MAX_DEPTH):
        if current == repo:
            continue
        if ROOT_MARKERS.intersection(filenames) or any(d.endswith(".xcodeproj") for d in dirnames):
            roots.append(current)
    return roots


def load_package_json(app):
    path = app / "package.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(read(path))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def requirement_name(spec):
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return match.group(1).lower() if match else None


def python_deps(app):
    """Return {name: source_file} for requirements.txt and pyproject.toml dependencies."""
    deps = {}
    req = app / "requirements.txt"
    if req.is_file():
        for line in read(req).splitlines():
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                name = requirement_name(line)
                if name:
                    deps.setdefault(name, "requirements.txt")
    pyproject = app / "pyproject.toml"
    if pyproject.is_file():
        text = read(pyproject)
        optional = re.search(r"(?ms)^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)", text)
        blocks = re.findall(r"(?ms)^\s*dependencies\s*=\s*\[(.*?)\]", text)
        if optional:
            blocks += re.findall(r"(?ms)=\s*\[(.*?)\]", optional.group(1))
        for block in blocks:
            for spec in re.findall(r"[\"']([^\"']+)[\"']", block):
                name = requirement_name(spec)
                if name:
                    deps.setdefault(name, "pyproject.toml")
        poetry = re.search(r"(?ms)^\[tool\.poetry\.dependencies\]\s*$(.*?)(?=^\[|\Z)", text)
        if poetry:
            for name in re.findall(r"(?m)^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*=", poetry.group(1)):
                deps.setdefault(name.lower(), "pyproject.toml")
    return deps


def js_deps(pkg):
    deps = {}
    for key in ("dependencies", "devDependencies"):
        section = pkg.get(key)
        if isinstance(section, dict):
            for name in section:
                deps.setdefault(name, "package.json")
    return deps


def is_llm_dep(name):
    return name in LLM_DEPS or name.startswith(LLM_PREFIXES)


def find_files(app, name_pattern, max_depth=4):
    for current, _dirnames, filenames in walk(app, max_depth):
        for filename in filenames:
            if re.fullmatch(name_pattern, filename):
                yield current / filename


def pbxproj_files(app):
    for current, dirnames, _filenames in walk(app, 2):
        for d in dirnames:
            if d.endswith(".xcodeproj"):
                path = current / d / "project.pbxproj"
                if path.is_file():
                    yield path


def plist_is_app(path):
    try:
        with path.open("rb") as handle:
            data = plistlib.load(handle)
    except (OSError, ValueError, ExpatError):
        return False
    return isinstance(data, dict) and data.get("CFBundlePackageType") == "APPL"


def classify(repo, app):
    rel = lambda p: p.relative_to(repo).as_posix()
    types, evidence, stack = [], [], []
    pkg = load_package_json(app)
    deps = {}
    if pkg is not None:
        deps.update(js_deps(pkg))
    deps.update(python_deps(app))
    package_swift = app / "Package.swift"
    swift_text = read(package_swift) if package_swift.is_file() else ""
    pbx = {path: read(path) for path in pbxproj_files(app)}

    # macos-app
    macos = False
    macos_platform = re.search(r"\.macOS\([^)]*\)", swift_text)
    if macos_platform:
        for plist in find_files(app, r"Info\.plist"):
            if plist_is_app(plist):
                macos = True
                evidence += [f"{rel(package_swift)}: {macos_platform.group(0)}", f"{rel(plist)}: CFBundlePackageType APPL"]
                break
    for path, text in pbx.items():
        if "SDKROOT = macosx" in text:
            macos = True
            evidence.append(f"{rel(path)}: SDKROOT = macosx")
    if macos:
        types.append("macos-app")

    # ios-android
    mobile = []
    mobile += [f"{rel(p)}: SDKROOT = iphoneos" for p, t in pbx.items() if "SDKROOT = iphoneos" in t]
    mobile += [f"{rel(p)}" for p in sorted((app / "android").glob("build.gradle*"))] if (app / "android").is_dir() else []
    mobile += [f"package.json: {d}" for d in sorted(MOBILE_DEPS & deps.keys())]
    pubspec = app / "pubspec.yaml"
    if pubspec.is_file() and re.search(r"(?m)^\s*flutter:", read(pubspec)):
        mobile.append(f"{rel(pubspec)}: flutter")
    if mobile:
        types.append("ios-android")
        evidence += mobile

    # browser-extension
    manifest = app / "manifest.json"
    if manifest.is_file() and "manifest_version" in read(manifest):
        types.append("browser-extension")
        evidence.append(f"{rel(manifest)}: manifest_version")

    # web-app
    web = sorted(WEB_DEPS & deps.keys())
    if web:
        types.append("web-app")
        evidence += [f"package.json: {d}" for d in web]
    elif pkg is None and (app / "index.html").is_file():
        types.append("web-app")
        evidence.append(f"{rel(app / 'index.html')}: static site")

    # api-backend
    api = sorted(API_DEPS & deps.keys())
    if api:
        types.append("api-backend")
        evidence += [f"{deps[d]}: {d}" for d in api]

    # cli
    cli = []
    if pkg and pkg.get("bin"):
        cli.append("package.json: bin")
    pyproject_text = read(app / "pyproject.toml") if (app / "pyproject.toml").is_file() else ""
    if re.search(r"(?m)^\[project\.scripts\]", pyproject_text):
        cli.append("pyproject.toml: [project.scripts]")
    if (app / "Cargo.toml").is_file() and re.search(r"(?m)^\[\[bin\]\]", read(app / "Cargo.toml")):
        cli.append("Cargo.toml: [[bin]]")
    if not macos and ".executableTarget(" in swift_text:
        cli.append("Package.swift: executableTarget")
    if cli:
        types.append("cli")
        evidence += cli

    # library
    if not types:
        if pkg and (pkg.get("main") or pkg.get("exports")):
            types.append("library")
            evidence.append("package.json: main/exports")
        elif re.search(r"(?m)^\[project\]", pyproject_text):
            types.append("library")
            evidence.append("pyproject.toml: [project]")

    if swift_text or pbx:
        stack.append("swift")
    if pkg is not None:
        stack.append("typescript" if (app / "tsconfig.json").is_file() or "typescript" in deps else "javascript")
    if (app / "requirements.txt").is_file() or pyproject_text:
        stack.append("python")
    if (app / "Cargo.toml").is_file():
        stack.append("rust")
    if (app / "go.mod").is_file():
        stack.append("go")
    if pubspec.is_file():
        stack.append("dart")
    if not stack and (app / "index.html").is_file():
        stack.append("html")

    llm = [f"{deps[d]}: {d}" for d in sorted(deps) if is_llm_dep(d)]
    return {"types": types, "evidence": evidence, "stack": stack, "llm": llm}


def git_facts(repo):
    def git(*args):
        try:
            out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout if out.returncode == 0 else None

    inside = git("rev-parse", "--is-inside-work-tree")
    if not inside or inside.strip() != "true":
        return {"is_repo": False, "has_remote": False, "tag_count": 0}
    remotes = git("remote") or ""
    tags = git("tag") or ""
    return {
        "is_repo": True,
        "has_remote": bool(remotes.strip()),
        "tag_count": len([t for t in tags.splitlines() if t.strip()]),
    }


def find_promises(repo, app_dirs):
    promises, seen = [], set()
    for directory in [repo] + [d for d in app_dirs if d != repo]:
        for path in sorted(directory.iterdir()) if directory.is_dir() else []:
            if not path.is_file() or not PROMISE_FILES.match(path.name) or path in seen:
                continue
            seen.add(path)
            for number, line in enumerate(read(path).splitlines(), start=1):
                if PROMISE.search(line):
                    promises.append({"file": path.relative_to(repo).as_posix(), "line": number, "text": line.strip()})
    return promises


def find_ci(repo):
    ci = sorted(
        p.relative_to(repo).as_posix()
        for p in (repo / ".github" / "workflows").glob("*")
        if p.suffix in (".yml", ".yaml")
    )
    for name in (".gitlab-ci.yml", ".circleci/config.yml"):
        if (repo / name).is_file():
            ci.append(name)
    return ci


def detect(repo):
    repo = Path(repo).resolve()
    workflow_deploys = sorted(
        p.relative_to(repo).as_posix() for p in (repo / ".github" / "workflows").glob("*deploy*")
    )
    apps, overlays = [], []
    for root in find_app_roots(repo):
        info = classify(repo, root)
        path = root.relative_to(repo).as_posix() or "."
        if not info["types"]:
            continue
        apps.append({
            "path": path,
            "types": info["types"],
            "evidence": info["evidence"],
            "stack": info["stack"],
            "lockfiles": [name for name in LOCKFILES if (root / name).is_file()],
            "deploy": [
                (root / name).relative_to(repo).as_posix() for name in DEPLOY_FILES if (root / name).is_file()
            ] + workflow_deploys,
        })
        if info["llm"]:
            overlays.append({"id": "llm-app", "path": path, "evidence": info["llm"]})
    if not apps:
        info = classify(repo, repo)
        apps.append({
            "path": ".", "types": ["unknown"], "evidence": [], "stack": info["stack"],
            "lockfiles": [name for name in LOCKFILES if (repo / name).is_file()],
            "deploy": [name for name in DEPLOY_FILES if (repo / name).is_file()] + workflow_deploys,
        })
    app_dirs = [repo / a["path"] for a in apps]
    return {
        "repo": str(repo),
        "git": git_facts(repo),
        "apps": apps,
        "overlays": overlays,
        "promises": find_promises(repo, app_dirs),
        "ci": find_ci(repo),
    }


def main(argv):
    if len(argv) != 2:
        print("usage: detect.py <repo>", file=sys.stderr)
        return 2
    print(json.dumps(detect(argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
