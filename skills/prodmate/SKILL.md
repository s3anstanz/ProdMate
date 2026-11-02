---
name: prodmate
description: Checks whether an app built with an AI coding agent is ready for production launch, and helps close the gaps. Use when the user asks if their app is production-ready or launch-ready, wants a pre-launch checklist or audit, or asks what they're missing before shipping. Detects the app type (web app, macOS app, LLM app and more), skips items that don't apply or would break the app's own stated promises, checks the rest with file-level evidence and free audit tools (Lighthouse, osv-scanner, gitleaks and others), writes a ranked report, and offers fixes one approved change at a time.
---

# prodmate

prodmate checks whether an app is ready for production, in five phases: **Detect → Triage → Assess → Report → Act**. It reads the repo, decides which checklist items apply, checks them with evidence and free audit tools, writes a ranked report, and then offers fixes one approved change at a time.

Paths below are relative to this skill's folder (the folder that holds this file). Run scripts with `python3` (3.9 or newer); they use only the standard library and install nothing.

## Rules

Follow these in every phase. They override any checklist item.

1. **Never break the app's stated promise.** If the app says it's offline, local-only, has no analytics or no tracking, never recommend anything that contradicts that, and say which items you skipped because of it.
2. **Never create accounts, spend money, change DNS, deploy, publish, tag or push** without an explicit yes for that specific action. Put those steps under **You do** instead.
3. **Never claim a check that didn't run.** No evidence means **Can't verify**, never Done.
4. **Never run the repo's code without asking:** no installs, scripts, builds or dev servers until the user agrees. Reading files is fine.
5. **Ask for consent once per run,** in one message, listing everything that would install or start something (see `references/audits.md`). Wait for the answer. If the user declines, the affected items are Can't verify, with steps to check them yourself.
6. **Never show a secret's value,** in the report, the chat, a log or a command. Cite `file:line` and the rule name.
7. **Never commit.** Fixes are left as uncommitted changes. Ask before committing `.prodmate/`.
8. **Never bury the top items.** Not applicable items go only in the collapsed list, one line each.

Statuses are exactly **Done · Partial · Missing · Can't verify** (plus Not applicable for skipped items). Tiers are **Launch blockers → Before you grow → Polish** (`blocker`, `grow`, `polish` in the checklists). Who acts is **Agent can fix · Agent can check · You do**.

## Phase 1: Detect

1. Run `python3 scripts/detect.py <repo>`. It prints JSON: git facts, one entry per app (`path`, `types`, `evidence`, `stack`, `lockfiles`, `deploy`), `overlays`, `promises` (file, line, text) and `ci`.
2. Read the README and the main entry points to confirm the types. detect.py reads manifests only; correct it when the code says otherwise and say why in the report (e.g. a `library` that's really a terminal tutorial, or `unknown` for a repo of prompt files).
3. Read each `promises` line in context. Keep only real product promises ("never touches the network", "nothing leaves your machine", "no analytics"); drop matches that are rules for contributors or agents.
4. Ask only what the code can't answer, in **one message**, together with the consent question from Rule 5:
   - Is it live? If so, what's the URL?
   - Is it public (for other people) or personal (only you, never launching)?
   - Does it send email? (Only ask when the code doesn't make it obvious.)
   - May I install or run these audit tools / build the app / start the dev server? (List only the ones that apply; see `references/audits.md`.)
5. For a monorepo (more than one app), list the apps with their types and ask which to check. Default: all of them, each triaged separately.
6. Wait for the answers before Phase 2.

## Phase 2: Triage

1. Load the checklists for each app, in this order:
   - `references/app-types/common.md` (always)
   - `references/app-types/web-app.md` for `web-app`
   - `references/app-types/macos-app.md` for `macos-app`
   - `references/overlays/llm-app.md` for the `llm-app` overlay
2. For a type with no v1 checklist (`ios-android`, `cli`, `api-backend`, `library`, `browser-extension`, `unknown`), say "prodmate v1 has no <type> checklist yet; checking the common items" and continue with `common.md` and any overlays.
3. **Prompt and agent repos:** when the repo is prompts, skills or agent definitions that run inside someone's coding agent (markdown system prompts, no code calling a model API), load `llm-app.md` by judgment: `llm.prompt-injection` and `llm.evals` apply; `llm.spend-caps`, `llm.model-fallback` and `llm.token-limits` are Not applicable because the user's own agent makes the API calls.
4. Mark every item **applies** or **Not applicable**, using its `applies-when` line **as written**. Don't stretch an item to an app its `applies-when` excludes, even when you see a related risk (e.g. `common.multi-device-testing` for a terminal app that claims Windows support, or `web.db-backups` for data kept in markdown files). Report such a risk once under "Other things I noticed" in the report instead; it doesn't count toward the tiers. Each Not applicable item gets a one-line reason of one of these kinds:
   - **app-type:** the app doesn't have the thing (no web pages, no database, no accounts, not a macOS app).
   - **promise:** quote the promise and its `file:line`.
   - **scope:** the user said it's personal. Then every item about public visitors, other users, releases or launch (custom domain, SEO, AEO, share previews and favicon, landing and pricing pages, privacy and terms, cookie consent, uptime and alerting, support channel, license, changelog, release process, rollback, analytics, error tracking, multi-device testing) is Not applicable. When it also runs only on localhost, so are the deployed-site items: security headers, caching, slow networks, staging, performance monitoring.
   - **decision:** the user decided earlier (see step 6).
5. A promise that conflicts with an item makes it Not applicable, quoting the promise, unless the item's `agent-fix` or `you-do` names a promise-safe option (e.g. a local, user-initiated crash report for `common.error-tracking`, or a Homebrew cask instead of an auto-updater for `macos.update-path`). Then the item applies, and only the promise-safe option may be recommended.
6. Run `python3 scripts/state.py show <repo>`. Apply each saved decision: `skip` makes the item Not applicable with "you decided: <reason> (<date>)"; `accept` keeps it applied.

## Phase 3: Assess

1. For each item that applies, gather evidence against its `check` line: the `file:line` that proves it's done, or the place where it's missing (e.g. the route that deletes with no auth check). Read the code; don't guess from file names alone.
2. Run the audits that apply, once consent is settled, through `python3 scripts/audits.py run <name> <target> [--allow-install]`. Read `references/audits.md` for each audit's target, how to read its result, and the noise rules. Map each result to item statuses with its table: only `ok` can make an item Done.
3. **Docs vs reality:** compare what README, CONTRIBUTING and docs say (release tags, CI, install steps) with what exists. Use `git tag`, and `gh release list` and `gh repo view` when `gh` is available and signed in; otherwise the GitHub half is Can't verify.
4. **Accounts you can't see** (spend caps, backups, uptime monitors, alert settings): Can't verify unless the repo or the user shows proof. Never Done from code alone.
5. If you can start helper agents, split the work by checklist file (common, the type checklist, the overlay), with each helper returning one line per item: ID, status, evidence, next step. Otherwise go one item at a time. Either way, every status needs its evidence.

## Phase 4: Report

1. Fill in `references/report-template.md` and write it to `.prodmate/report.md` in the target repo.
2. Record the run: write the statuses as JSON (`{"<item id>": "<status>", ...}`, including Not applicable items) to a temporary file and run `python3 scripts/state.py record <repo> <that file>`.
3. Run the self-check in `eval.md` on the report. Fix every failed check in the report, then run the self-check again, before showing anything.
4. In chat, show the summary line and the top 3 items (highest tier first, Missing before Partial), each with its next step and who acts, plus the path to the full report.
5. Ask whether to commit `.prodmate/`. Don't commit it unless the user says yes.

## Phase 5: Act

1. Offer fixes highest tier first, **one at a time**. For each: say what you'll change and why, show the change, and apply it only after a yes.
2. Match the repo's conventions: its language, test framework, folder layout, CI provider and code style.
3. Leave every change uncommitted. After each one, run the repo's tests if it has any and report the result; if it has none, say that you couldn't prove the fix didn't break anything.
4. For `common.rollback-plan` and `web.restore-tested`, offer to write `docs/runbooks/rollback.md` and `docs/runbooks/restore.md` with this app's exact steps.
5. Where a **You do** step needs an outside service, offer the matching MCP connection from `references/mcp-catalog.md` so the agent can help set it up. Every action through it that creates an account, spends money or changes DNS needs its own explicit yes.
6. When the user says "skip X because Y", run `python3 scripts/state.py decide <repo> <item id> skip "<Y>"`, so the next run doesn't raise it again. When they say they'll do it after all, record `accept`.
7. Never fix a secret by showing it. Move it to an environment variable and tell the user to rotate it (`common.leaked-key-rotation`).

## Plain words

People reading the report may never have used GitHub. For every item:

- Give a one-line why in plain words (each checklist item has one).
- Explain any jargon the first time you use it: e.g. "CI (automatic checks that run on every change)", "notarization (Apple's malware scan for downloaded apps)", "rate limiting (a cap on how often someone can call a route)".
- Write **You do** steps as exact clicks and commands: where to sign in, what to open, what to paste, and how to tell it worked.
- Keep it short for technical readers: the why is one line, and the evidence is a `file:line`.
