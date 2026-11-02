#!/usr/bin/env python3
"""Validate prodmate checklist files.

Each checklist item is a `### <id>` heading followed by one `- field: value`
line per field. Usage:

    python3 scripts/lint_checklists.py [references_dir]

Prints one error per line and exits 1 if any file has an error.
"""
import re
import sys
from pathlib import Path

from audits import AUDITS

FIELDS = ("tier", "why", "applies-when", "check", "agent-fix", "audit", "you-do")
TIERS = {"blocker", "grow", "polish"}
PREFIXES = {
    "common.md": "common.",
    "web-app.md": "web.",
    "macos-app.md": "macos.",
    "llm-app.md": "llm.",
}
KNOWN_AUDITS = set(AUDITS.keys())

HEADING = re.compile(r"^###\s+(\S+)\s*$")
FIELD = re.compile(r"^-\s+([a-z-]+):\s*(.*)$")


def parse_checklist(text):
    """Return one dict per `### id` item, with `id` plus every field found."""
    items = []
    current = None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            current = {"id": heading.group(1)}
            items.append(current)
            continue
        if line.startswith("#"):
            current = None
            continue
        if current is not None:
            field = FIELD.match(line)
            if field:
                current[field.group(1)] = field.group(2).strip()
    return items


def lint(paths, known_audits):
    errors = []
    seen = {}
    for path in paths:
        path = Path(path)
        prefix = PREFIXES.get(path.name)
        if prefix is None:
            errors.append(f"{path}: unknown checklist file name (expected one of {', '.join(sorted(PREFIXES))})")
        for item in parse_checklist(path.read_text(encoding="utf-8")):
            item_id = item["id"]
            where = f"{path}: {item_id}"
            if item_id in seen:
                errors.append(f"{where}: duplicate id, also in {seen[item_id]}")
            else:
                seen[item_id] = path
            if prefix and not item_id.startswith(prefix):
                errors.append(f"{where}: id must start with '{prefix}' in {path.name}")
            for name in FIELDS:
                if not item.get(name):
                    errors.append(f"{where}: missing field '{name}'")
            tier = item.get("tier")
            if tier and tier not in TIERS:
                errors.append(f"{where}: tier '{tier}' is not one of {', '.join(sorted(TIERS))}")
            audit = item.get("audit")
            if audit and audit != "none" and audit not in known_audits:
                errors.append(f"{where}: unknown audit '{audit}'")
    return errors


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1] / "references"
    paths = sorted(p for p in root.rglob("*.md") if p.name in PREFIXES)
    errors = lint(paths, KNOWN_AUDITS)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
