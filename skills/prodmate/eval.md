# prodmate report self-check

Use this after writing the report. Answer each check with pass or fail. If any check fails, fix the report before showing it.

## Triage

1. Is every Not applicable item only in the collapsed list, each with a one-line reason?
2. Is every item skipped for a promise quoting that promise, with its `file:line`?
3. For an app type with no v1 checklist, does the report say so and say the common items were checked?
4. If the user said the app is personal, are public-launch items (SEO, domain, privacy pages, uptime, release process and the rest) Not applicable rather than gaps?
5. Does every reported item meet its `applies-when` line as written (no web items for a macOS app, no API-call items for a prompt-only repo, no item stretched to cover a related risk)? Risks no item covers belong only under "Other things I noticed".

## Evidence

6. Does every Done have a `file:line` or an audit result that returned `ok`?
7. Is every audit that returned `missing`, `error` or `skipped`, or wasn't run, marked Can't verify, with the reason?
8. Are no DKIM, spend-cap, uptime, backup or alerting items marked Done without proof you actually saw?
9. Is every Missing backed by where you looked (the file, route or command that shows the gap)?
10. For an app meant for other people, is nothing marked Done or Partial only because of a path that needs developer tools (git clone, build from source, git pull)?
11. Is every publishable-by-design key (Supabase anon, Stripe `pk_`, Firebase web config) left out of the leaks, with the protection behind it checked instead?

## Safety

12. Does no recommendation break a stated promise (no hosted analytics, tracking, error tracking or auto-updater for an app that promises no network or no tracking)?
13. Does the report contain no secret value, not even part of one?
14. Is every account, DNS, spend, deploy, publish, tag or push step under You do, or gated on an explicit yes?
15. Did nothing run that needed consent without getting it (installs, builds, dev servers, the repo's scripts)?

## Report

16. Are tiers ordered Launch blockers → Before you grow → Polish, with Missing first inside each tier?
17. Does every item show its ID, status, evidence, next step and who acts?
18. Does every You do item have exact steps a non-engineer could follow?
19. With zero blockers, does it open with "You're in good shape." and list at most 5 items before the collapsed sections?
20. Is every jargon term explained the first time it's used?
21. Do the summary line's counts match the items in each tier?
