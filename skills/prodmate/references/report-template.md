# Report: report.json fields and content rules

Write the findings once, as `.prodmate/report.json`, then run `python3 scripts/report.py render <repo>`. It checks the file and writes both `.prodmate/report.md` and the guided page `.prodmate/report.html` from it, so the two always agree. If it prints problems, fix `report.json` and run it again; it writes nothing until the file is valid.

## Contents

- Content rules
- report.json fields
- Updating as things get fixed
- Without Python: write report.md by hand

## Content rules

- **Statuses:** `Done`, `Partial`, `Missing`, `Can't verify`, `Not applicable`. Tiers: `blocker` (launch blockers), `grow` (before you grow), `polish`.
- **Plain words:** every item has a plain title ("Lock the refund page to admins", not the item ID) and a one-sentence `why`. Explain any jargon the first time it appears (e.g. "notarization (Apple's malware scan for downloaded apps)").
- **Every open item says who does what:** `you` says what the person does and where ("in Stripe", "in your domain settings"); `prodmate` says what ProdMate will change. Anything the person does gets `steps`: exact clicks and commands a non-engineer can follow, ending with how to tell it worked.
- **`say`** is the short phrase the person tells ProdMate in the chat: when they're done ("rotated the Stripe key"), or to start ProdMate's part ("fix the refund page").
- **Evidence:** `found` cites `file:line` or the audit summary. A Done item's `evidence` says what was checked. Never mark Done without it.
- **Never** include a secret value, a hosted service that breaks a stated promise, or a Done that nothing checked.
- The renderer handles order, counts, the score, "Do this first" and "You're in good shape."; don't write those yourself.

## report.json fields

```json
{
  "version": 1,
  "checked": "YYYY-MM-DD",
  "last_update": null,
  "apps": [{
    "name": "Crumbly", "path": ".", "types": ["web-app"],
    "description": "a web app for taking bakery preorders",
    "verdict": "Not ready for launch yet, but close.",
    "summary": "One or two plain sentences on where the app stands and what's in the way.",
    "couldnt_check": {"summary": "6 things I couldn't check, mostly ...", "details": "What ran, what couldn't, and why."},
    "promises": [{"quote": "...", "file": "README.md", "line": 11, "effect": "So ProdMate won't suggest ..."}],
    "notes": [{"title": "One-line headline.", "text": "A risk no checklist item covers, or repo text that tried to steer the run."}],
    "items": [{
      "id": "web.email-auth", "tier": "grow", "status": "Partial",
      "title": "Prove your emails are really from you",
      "by": "You, in Resend and your domain settings",
      "why": "...", "found": "... `file:line` ...",
      "you": "...", "prodmate": null,
      "steps": ["...", "..."], "say": "email records are updated",
      "evidence": null, "confirmed": null, "fixed": null, "na_reason": null
    }]
  }]
}
```

- **Required:** `version`, `checked`, `apps`; on each app `name`, `path`, `types`, `verdict`, `summary`, `items`; on each item `id`, `tier`, `status`, `title`. A `Not applicable` item needs `na_reason` (a plain reason that quotes the promise when there is one).
- **Optional:** everything else. Leave a field `null` or out when it doesn't apply.
- One entry in `apps` per app checked (a monorepo gets one each). Include every checklist item for that app, Not applicable ones too.
- Text may use `backticks` for file names and commands; nothing else is formatted. Everything is escaped on the page.

## Updating as things get fixed

When a change makes an item's own `check` pass, set its `status` to `Done`, its `evidence`, and `fixed` to today, then set the top-level `last_update` to one plain sentence ("Just now: ProdMate locked the refund page to admins, and your tests still pass.") and run `report.py render` again. The open page reloads by itself. When the checklist accepts the person's word (a rotated key, backups turned on), set `confirmed` to today instead of claiming ProdMate checked it. Never set `Done` for anything that wasn't re-checked or confirmed.

## Without Python: write report.md by hand

Use these sections, in order, with the content rules above:

1. `# Production readiness: <app name>`, then "You're in good shape." when no launch blocker is open, then `<N> launch blockers, <N> before you grow, <N> polish. Checked <YYYY-MM-DD> with ProdMate.` (open items per tier), then the verdict and summary.
2. `## What I checked and what I couldn't`, including that the run was done without Python.
3. `## Promises honored`: each quoted promise with `file:line` and what it ruled out.
4. `## Launch blockers`, `## Before you grow`, `## Polish`: open items as `### <title>: <Status>` with why, what I found, next step, who and what to tell ProdMate; Done items one line each.
5. `## Other things I noticed`, only when there's something.
6. `## You do`: numbered, each with its steps.
7. `<details><summary>Not applicable (<N>)</summary>` with one line per item and its reason.
