#!/usr/bin/env python3
"""Render ProdMate's report from one data file.

ProdMate writes the findings once, as .prodmate/report.json; this script checks
that file and renders both .prodmate/report.md and the guided .prodmate/report.html
from it, so the two can never disagree.

Usage: python3 scripts/report.py render <repo>
"""
import datetime
import html
import json
import math
import os
import re
import sys
from pathlib import Path

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


def section_errors(app, where, key, required):
    """Problems in an optional list section (notes, promises): null or absent is fine."""
    value = app.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{where}.{key} must be a list"]
    errors = []
    for n, entry in enumerate(value):
        if not isinstance(entry, dict):
            errors.append(f"{where}.{key}[{n}] must be an object")
            continue
        errors += [f"{where}.{key}[{n}] is missing '{k}'" for k in required if entry.get(k) in (None, "")]
    return errors


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
        if "items" in app and not isinstance(items, list):
            errors.append(f"{where}.items must be a list")
        errors += section_errors(app, where, "notes", ("title", "text"))
        errors += section_errors(app, where, "promises", ("quote", "file", "line"))
        cc = app.get("couldnt_check")
        if cc is not None and not isinstance(cc, dict):
            errors.append(f"{where}.couldnt_check must be an object with 'summary' and 'details'")
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


def couldnt_summary(app):
    """The "couldn't check" line: the agent's own, or a count of Can't verify items, or None."""
    cc = app.get("couldnt_check") or {}
    if cc.get("summary"):
        return cc["summary"]
    cant = sum(1 for i in applicable(app) if i.get("status") == "Can't verify")
    if not cant:
        return None
    return f"{cant} thing{'s' if cant != 1 else ''} I couldn't check. Each one is marked below, with the steps to check it yourself."


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
    out += [couldnt_summary(app) or "Everything on the checklist was checked.", ""]
    if cc.get("details"):
        out += [cc["details"], ""]

    out += ["## Promises honored", ""]
    promises = app.get("promises") or []
    for p in promises:
        out.append(f'- "{p["quote"]}" (`{p["file"]}:{p["line"]}`). {p.get("effect") or ""}'.rstrip())
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


ASSETS = Path(__file__).resolve().parents[1] / "assets"
SEG_CLASS = {"Done": "seg-done", "Partial": "seg-partial", "Can't verify": "seg-cant", "Missing": "seg-todo"}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def t(value):
    """Escape text from report.json for HTML, then turn `backtick spans` into <code>."""
    escaped = html.escape(str(value), quote=True)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def nice_date(iso):
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return t(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def ring_svg(app):
    statuses = ring_order(app)
    n = len(statuses)
    if not n:
        return '<svg viewBox="0 0 120 120" aria-hidden="true"></svg>'
    r, c, gap = 50, 60, 2.4 if n > 24 else 3.2
    paths = []
    for i, status in enumerate(statuses):
        a0 = math.radians(i / n * 360 + gap / 2)
        a1 = math.radians((i + 1) / n * 360 - gap / 2)
        x0, y0 = c + r * math.cos(a0), c + r * math.sin(a0)
        x1, y1 = c + r * math.cos(a1), c + r * math.sin(a1)
        large = 1 if (a1 - a0) > math.pi else 0
        paths.append(f'<path class="seg {SEG_CLASS[status]}" d="M {x0:.2f} {y0:.2f} A {r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}"/>')
    return '<svg viewBox="0 0 120 120" aria-hidden="true">' + "".join(paths) + "</svg>"


def who_block(item):
    rows = []
    if item.get("you"):
        rows.append(f"<dt>You</dt><dd>{t(item['you'])}</dd>")
    if item.get("prodmate"):
        rows.append(f"<dt>{'Then ProdMate' if item.get('you') else 'ProdMate'}</dt><dd>{t(item['prodmate'])}</dd>")
    return f'<dl class="who">{"".join(rows)}</dl>' if rows else ""


def steps_block(item):
    if not item.get("steps"):
        return ""
    lis = "".join(f"<li>{t(s)}</li>" for s in item["steps"])
    return f'<details class="howto"><summary>Show me how</summary><div><ol class="steps">{lis}</ol></div></details>'


def nudge(item):
    if not item.get("say"):
        return ""
    lead = "When you’re done, tell ProdMate" if item.get("you") and not item.get("prodmate") else "To start, tell ProdMate"
    if item.get("you") and item.get("prodmate"):
        lead = "When you’re done, tell ProdMate"
    return f'<p class="nudge">{lead} <q>{t(item["say"])}</q>.</p>'


def row_body(item):
    if item["status"] == "Done":
        out = f"<p>{t(item.get('evidence') or 'Checked and done.')}</p>"
        if item.get("confirmed"):
            out += f'<p class="confirmed">you confirmed {t(item["confirmed"])}</p>'
        return out
    out = ""
    if item.get("why"):
        out += f"<p>{t(item['why'])}</p>"
    if item.get("found"):
        out += f'<p><span class="lbl">What I found:</span> {t(item["found"])}</p>'
    return out + who_block(item) + steps_block(item) + nudge(item)


def row(item):
    fixed = item["status"] == "Done" and item.get("fixed")
    glyph = {"Done": "d", "Partial": "p", "Can't verify": "c", "Missing": ""}[item["status"]]
    if fixed:
        when = "just now" if item["fixed"] == datetime.date.today().isoformat() else nice_date(item["fixed"])
        by = f'<span class="badge">Fixed {when}</span>'
    elif item["status"] == "Done":
        by = '<span class="by">Checked</span>'
    elif item["status"] == "Can't verify" and not str(item.get("by") or "").startswith("You"):
        by = '<span class="by">You check this</span>'
    else:
        by = f'<span class="by">{t(item.get("by") or "")}</span>'
    return (f'<details class="row{" fixed" if fixed else ""}" data-id="{t(item["id"])}">'
            f'<summary><span class="glyph {glyph}"></span><span class="t">{t(item["title"])}</span>{by}</summary>'
            f'<div class="body">{row_body(item)}</div></details>')


def first_panel(item, good_shape):
    if not item:
        return ""
    tag = "Check this first" if item["status"] == "Can't verify" else ("Next up" if good_shape else "Do this first")
    body = f'<p>{t(item["why"])}</p>' if item.get("why") else ""
    if item.get("found"):
        body += f'<p><span class="lbl">What I found:</span> {t(item["found"])}</p>'
    return (f'<div class="first"><div class="tag">{tag}</div><h2>{t(item["title"])}</h2>'
            f"{body}{who_block(item)}{steps_block(item)}{nudge(item)}</div>")


def tier_section(app, tier, first):
    rows = [i for _, i in items_in(app, tier) if i is not first]
    if not rows:
        return ""
    open_n = sum(1 for i in rows if is_open(i))
    done_n = len(rows) - open_n
    more = first is not None and first.get("tier") == tier
    label = f"{open_n} more, {done_n} done" if more else f"{open_n} to do, {done_n} done"
    opened = " open" if tier == "blocker" else ""
    return (f'<section class="tier"><details{opened}><summary><h2>{TIER_HEADINGS[tier] if tier != "blocker" else "Must do before launch"}</h2>'
            f'<span class="count">{label}</span></summary>{"".join(row(i) for i in rows)}</details></section>')


def folded(title, count, inner):
    return (f'<section class="tier"><details><summary><h2>{title}</h2><span class="count">{count}</span></summary>'
            f'<div style="padding-top:12px">{inner}</div></details></section>')


def app_html(app, checked, index, last_update):
    s = score(app)
    first, good_shape = pick_first(app)
    desc = f", {t(app['description'])}" if app.get("description") else ""
    good = f'<p class="good">{GOOD_SHAPE}</p>' if good_shape and applicable(app) else ""
    summary = t(app["summary"]) if applicable(app) else NOTHING_APPLIES
    meta = t(last_update) if last_update else "Nothing has changed since the last check."
    parts = [
        f'<div class="app">{t(app["name"])}{desc}. Checked by ProdMate on {nice_date(checked)}.</div>',
        '<div class="hero">',
        f'<div class="ring" role="img" aria-label="{s["percent"]}% ready">{ring_svg(app)}'
        f'<div class="num"><b>{s["percent"]}%</b><span>{s["done"]} of {s["applicable"]} done</span></div></div>',
        f'<div>{good}<h1>{t(app["verdict"])}</h1><p class="lede">{summary}</p><p class="meta">{meta}</p>'
        '<div class="key"><span><i style="background:var(--moss)"></i>done</span>'
        '<span><i style="border:2px solid var(--indigo)"></i>to do</span>'
        '<span><i style="border:2px dashed var(--amber)"></i>couldn&#x27;t check</span></div></div>',
        "</div>",
    ]
    cc = app.get("couldnt_check") or {}
    caveat = couldnt_summary(app)
    if caveat:
        details = f'<p>{t(cc["details"])}</p>' if cc.get("details") else ""
        parts.append(f'<details class="caveat"><summary>{t(caveat)}</summary>{details}</details>')
    parts.append(first_panel(first, good_shape))
    parts += [tier_section(app, tier, first) for tier in TIERS]
    notes = app.get("notes") or []
    if notes:
        inner = "".join(f'<p><b>{t(n["title"])}</b> {t(n["text"])}</p>' for n in notes)
        parts.append(folded("Other things I noticed", f"{len(notes)} note{'s' if len(notes) != 1 else ''}", f'<div class="notice">{inner}</div>'))
    promises = app.get("promises") or []
    if promises:
        inner = "".join(
            f'<blockquote>&ldquo;{t(p["quote"])}&rdquo; (<code>{t(p["file"])}</code>, line {t(p["line"])})</blockquote>'
            + (f'<p>{t(p["effect"])}</p>' if p.get("effect") else "")
            for p in promises
        )
        parts.append(folded("Promises I kept", f"{len(promises)} promise{'s' if len(promises) != 1 else ''}", inner))
    na = [i for i in app.get("items", []) if i.get("status") == "Not applicable"]
    if na:
        lis = "".join(f'<li>{t(i["title"])} <span class="why">{t(i["na_reason"])}</span></li>' for i in na)
        parts.append(folded(f"Doesn&#x27;t apply to {t(app['name'])}", f"{len(na)} item{'s' if len(na) != 1 else ''}", f'<ul class="na">{lis}</ul>'))
    return f'<div class="app-section" id="app-{index}">' + "".join(parts) + "</div>"


def render_html(report):
    """The guided report as one self-contained HTML page (inline CSS and JS, no network)."""
    apps = report["apps"]
    css = (ASSETS / "report.css").read_text(encoding="utf-8")
    js = (ASSETS / "report.js").read_text(encoding="utf-8")
    title = f"{t(apps[0]['name'])} launch readiness" if len(apps) == 1 else "Launch readiness"
    overview = ""
    if len(apps) > 1:
        lis = "".join(f'<li><a href="#app-{n}">{t(a["name"])}</a><span class="pct">{score(a)["percent"]}% ready</span></li>'
                      for n, a in enumerate(apps, 1))
        overview = f'<nav class="overview"><h2>Apps in this repo</h2><ul>{lis}</ul></nav>'
    sections = "".join(app_html(a, report["checked"], n, report.get("last_update")) for n, a in enumerate(apps, 1))
    footer = ('<footer>This page updates itself while ProdMate is working. '
              'The same report is saved as <code>.prodmate/report.md</code>.</footer>')
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>\n{css}</style>\n</head>\n<body>\n<main>\n"
            f"{overview}{sections}{footer}\n</main>\n<script>\n{js}</script>\n</body>\n</html>\n")


def write_atomic(path, text):
    """Write via a temp file and rename, so a live page never reloads into a half-written file."""
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def render(repo):
    """Validate <repo>/.prodmate/report.json and write report.md and report.html. Returns (paths, errors)."""
    folder = Path(repo) / ".prodmate"
    source = folder / "report.json"
    if not source.is_file():
        return None, [f"no report.json at {source}"]
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, [f"{source} isn't valid JSON: {exc}"]
    errors = validate(data)
    if errors:
        return None, errors
    markdown, page = render_markdown(data), render_html(data)
    md_path, html_path = folder / "report.md", folder / "report.html"
    write_atomic(md_path, markdown)
    write_atomic(html_path, page)
    return {"markdown": str(md_path), "html": str(html_path)}, []


def main(argv):
    if len(argv) != 3 or argv[1] != "render":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    paths, errors = render(argv[2])
    if errors:
        print("report.json has problems, so nothing was written:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(json.dumps(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
