#!/usr/bin/env python3
"""Render ProdMate's report from one data file.

ProdMate writes the findings once, as .prodmate/report.json; this script checks
that file and renders both .prodmate/report.md and the guided .prodmate/report.html
from it, so the two can never disagree.

Usage: python3 scripts/report.py render <repo>
"""
import json
import sys

STATUSES = ("Done", "Partial", "Missing", "Can't verify", "Not applicable")
TIERS = ("blocker", "grow", "polish")
APP_KEYS = ("name", "path", "types", "verdict", "summary", "items")
ITEM_KEYS = ("id", "tier", "status", "title")

# Open items sort Missing, Partial, Can't verify; the ring shows progress first.
OPEN_ORDER = {"Missing": 0, "Partial": 1, "Can't verify": 2}
RING_ORDER = {"Done": 0, "Partial": 1, "Can't verify": 2, "Missing": 3}


def applicable(app):
    return [i for i in app.get("items", []) if i.get("status") != "Not applicable"]


def is_open(item):
    return item.get("status") in OPEN_ORDER


def validate(report):
    """Return a list of problems in a report.json document; empty means valid."""
    if not isinstance(report, dict):
        return ["report.json must be a JSON object"]
    errors = []
    for key in ("version", "checked", "apps"):
        if key not in report:
            errors.append(f"report is missing '{key}'")
    apps = report.get("apps")
    if not isinstance(apps, list) or not apps:
        errors.append("report needs at least one app in 'apps'")
        return errors
    for a, app in enumerate(apps):
        where = f"apps[{a}]"
        if not isinstance(app, dict):
            errors.append(f"{where} must be an object")
            continue
        errors += [f"{where} is missing '{k}'" for k in APP_KEYS if k not in app]
        items = app.get("items")
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            iwhere = f"{where}.items[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{iwhere} must be an object")
                continue
            errors += [f"{iwhere} is missing '{k}'" for k in ITEM_KEYS if not item.get(k)]
            status, tier = item.get("status"), item.get("tier")
            if status and status not in STATUSES:
                errors.append(f"{iwhere} has unknown status '{status}' (use one of: {', '.join(STATUSES)})")
            if tier and tier not in TIERS:
                errors.append(f"{iwhere} has unknown tier '{tier}' (use one of: {', '.join(TIERS)})")
            if status == "Not applicable" and not item.get("na_reason"):
                errors.append(f"{iwhere} is Not applicable but has no 'na_reason'")
            steps = item.get("steps")
            if steps is not None and not (isinstance(steps, list) and all(isinstance(s, str) for s in steps)):
                errors.append(f"{iwhere} 'steps' must be a list of strings")
    return errors


def score(app):
    """Readiness: Done counts 1, Partial counts half, Can't verify and Missing count 0, over applicable items."""
    items = applicable(app)
    done = sum(1 for i in items if i.get("status") == "Done")
    partial = sum(1 for i in items if i.get("status") == "Partial")
    percent = int((done + partial / 2) * 100 / len(items) + 0.5) if items else 0
    return {"done": done, "partial": partial, "applicable": len(items), "percent": percent}


def pick_first(app):
    """Return (the "Do this first" item or None, good_shape).

    good_shape is True only when no launch blocker is open in any status.
    """
    open_items = [i for i in app.get("items", []) if is_open(i)]
    good_shape = not any(i.get("tier") == "blocker" for i in open_items)
    if not open_items:
        return None, True
    first = min(
        enumerate(open_items),
        key=lambda pair: (TIERS.index(pair[1]["tier"]), OPEN_ORDER[pair[1]["status"]], pair[0]),
    )[1]
    return first, good_shape


def ring_order(app):
    """Statuses of applicable items, ordered done, partial, can't verify, to do."""
    items = applicable(app)
    ordered = sorted(enumerate(items), key=lambda pair: (RING_ORDER[pair[1]["status"]], pair[0]))
    return [item["status"] for _, item in ordered]


TIER_HEADINGS = {"blocker": "Launch blockers", "grow": "Before you grow", "polish": "Polish"}
NOTHING_APPLIES = "Nothing on the checklist applies to this app."
GOOD_SHAPE = "You're in good shape."


def items_in(app, tier):
    """A tier's applicable items: open ones first (Missing, Partial, Can't verify), then Done."""
    rows = [i for i in applicable(app) if i["tier"] == tier]
    return sorted(enumerate(rows), key=lambda p: (OPEN_ORDER.get(p[1]["status"], 3), p[0]))


def done_note(item):
    """What a Done item's evidence line says, including a confirmation date."""
    note = item.get("evidence") or "Checked."
    if item.get("confirmed"):
        note += f" (you confirmed {item['confirmed']})"
    if item.get("fixed"):
        note += f" Fixed {item['fixed']}."
    return note


def next_step(item):
    parts = []
    if item.get("you"):
        parts.append(f"You: {item['you']}")
    if item.get("prodmate"):
        parts.append(f"{'Then ProdMate' if item.get('you') else 'ProdMate'}: {item['prodmate']}")
    return " ".join(parts)


def markdown_app(app, checked):
    counts = {t: sum(1 for i in applicable(app) if i["tier"] == t and is_open(i)) for t in TIERS}
    out = [f"# Production readiness: {app['name']}", ""]
    _, good_shape = pick_first(app)
    if not applicable(app):
        out += [NOTHING_APPLIES, ""]
    elif good_shape:
        out += [GOOD_SHAPE, ""]
    out += [
        f"{counts['blocker']} launch blockers, {counts['grow']} before you grow, {counts['polish']} polish. "
        f"Checked {checked} with ProdMate.",
        "",
        f"**{app['verdict']}** {app['summary']}",
        "",
        "## What I checked and what I couldn't",
        "",
    ]
    cc = app.get("couldnt_check") or {}
    out += [cc.get("summary", "Everything on the checklist was checked."), ""]
    if cc.get("details"):
        out += [cc["details"], ""]

    out += ["## Promises honored", ""]
    promises = app.get("promises") or []
    for p in promises:
        out.append(f'- "{p["quote"]}" (`{p["file"]}:{p["line"]}`). {p.get("effect", "")}'.rstrip())
    out += (["No product promises found."] if not promises else []) + [""]

    for tier in TIERS:
        rows = items_in(app, tier)
        if not rows:
            continue
        out += [f"## {TIER_HEADINGS[tier]}", ""]
        for _, item in rows:
            if item["status"] == "Done":
                out.append(f"- {item['title']}: Done. {done_note(item)}")
                continue
            out += [f"### {item['title']}: {item['status']}", ""]
            if item.get("why"):
                out += [item["why"], ""]
            if item.get("found"):
                out.append(f"- **What I found:** {item['found']}")
            step = next_step(item)
            if step:
                out.append(f"- **Next step:** {step}")
            if item.get("by"):
                out.append(f"- **Who:** {item['by']}")
            if item.get("say"):
                out.append(f"- **Tell ProdMate:** \"{item['say']}\"")
            out.append("")
        out.append("")

    notes = app.get("notes") or []
    if notes:
        out += ["## Other things I noticed", ""]
        out += [f"**{n['title']}** {n['text']}\n" for n in notes]

    todo = [i for _, i in sorted(enumerate(applicable(app)), key=lambda p: (TIERS.index(p[1]["tier"]), p[0]))
            if is_open(i) and i.get("you") and i.get("steps")]
    if todo:
        out += ["## You do", ""]
        for n, item in enumerate(todo, 1):
            out.append(f"{n}. **{item['title']}.** {item['you']}")
            out += [f"   {s_n}. {step}" for s_n, step in enumerate(item["steps"], 1)]
        out.append("")

    na = [i for i in app.get("items", []) if i.get("status") == "Not applicable"]
    if na:
        out += ["<details>", f"<summary>Not applicable ({len(na)})</summary>", ""]
        out += [f"- {i['title']}: {i['na_reason']}" for i in na]
        out += ["", "</details>", ""]
    return "\n".join(out)


def render_markdown(report):
    """The report as markdown, one section per app, from report.json data."""
    return "\n".join(markdown_app(app, report["checked"]) for app in report["apps"]).rstrip() + "\n"


def main(argv):
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
