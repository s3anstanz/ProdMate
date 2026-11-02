# Report template

Fill this in for `.prodmate/report.md`. Keep the section order. Leave out a tier section that has no items, but keep the summary line's count of 0.

## Rules

- **Statuses:** Done · Partial · Missing · Can't verify. Not applicable items go only in the collapsed list at the end.
- **Who acts:** **Agent can fix** (ProdMate can write the change) · **Agent can check** (ProdMate can run or re-run a check) · **You do** (needs an account, money, DNS, a device or a decision).
- **Every item shows:** its ID, status, evidence (`file:line`, or the audit summary), the next step, and who acts. Add a one-line why in plain words.
- **Order inside a tier:** Missing, then Partial, then Can't verify, then Done. Done items in the Before you grow and Polish tiers can be one line each.
- **Zero blockers:** open with "You're in good shape." and list at most 5 items before the collapsed sections. Put the rest in a `<details>` block titled "Everything else".
- **Plain words:** explain any jargon the first time it appears (e.g. "notarization (Apple's malware scan for downloaded apps)").
- **Never** include a secret value, a hosted service that breaks a stated promise, or a Done without evidence.

## Template

```markdown
# Production readiness: <app name>

<N> launch blockers, <N> before you grow, <N> polish. Checked <YYYY-MM-DD> with ProdMate.

<One or two sentences on the most important thing to do first.>

## What I checked and what I couldn't

- **App:** <type(s)> at `<path>` (<evidence from detect.py>). <For a type with no v1 checklist: "ProdMate v1 has no <type> checklist yet; I checked the common items.">
- **Ran:** <audit> (<summary>), ...
- **Couldn't run:** <audit>: <reason, e.g. "not deployed yet, run again after launch" or "you declined the install">.
- **Couldn't see:** <accounts or dashboards ProdMate has no access to, e.g. "your Supabase backup settings">.

## Promises honored

- "<quoted promise>" (`<file>:<line>`). Because of this I skipped: <item IDs>.

## Launch blockers

### <item id>: <Status>
<One-line why.>
- **Evidence:** `<file>:<line>` <what it shows> | <audit summary>
- **Next step:** <exact change or check>
- **Who:** Agent can fix | Agent can check | You do

## Before you grow

<same item format>

## Polish

<same item format>

## Other things I noticed

<Only real risks that no checklist item covers (e.g. a supported OS that CI never tests, data with no backup outside git, a broken promise). One short paragraph each, with evidence and a next step. Not counted in the tiers. Leave the section out when there's nothing.>

## You do

1. **<item id>: <short title>.** <Exact steps a non-engineer can follow: where to sign in, what to click, what to paste, how to know it worked.>
2. ...

<details>
<summary>Not applicable (<N>)</summary>

- `<item id>`: <one-line reason, e.g. "app-type: macOS app, no web pages" or "promise: 'never touches the network' (README.md:11)">
- ...

</details>
```
