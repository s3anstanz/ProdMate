# Audits

How to run each free audit through `scripts/audits.py`, and how to turn its result into an item status. Paths are relative to the skill folder.

## Contents

- Before any audit: consent
- Result status → item status
- lighthouse
- osv-scanner
- gitleaks
- http-observatory
- checkdmarc
- codesign
- Noise rules
- Audits ProdMate doesn't run for you

## Before any audit: consent

Run `python3 scripts/audits.py available` first. It prints, for each audit, whether it can run now and how (`path`, `npx`, `pipx`, `builtin`).

Ask once per run, in one message, before anything that installs or starts something: an audit that would run through `npx` or `pipx` (it downloads the tool into a cache; nothing is installed globally), building a macOS app, or starting the app's dev server. Name each one. Pass `--allow-install` only after a yes.

If the user says no, don't run it. The items it would have checked are **Can't verify**, with the reason and the steps to check it yourself (each section below has them).

## Result status → item status

| AuditResult `status` | Item status |
|---|---|
| `ok` | **Done** for the part the audit checks. The item may still be Partial if its `check` asks for more than the audit measures. |
| `issues` | **Missing**, or **Partial** when only medium or low findings remain. Quote the finding messages as evidence. |
| `missing` | **Can't verify**. Reason: the tool isn't available or the user declined the install. Use `summary` as the reason. |
| `error` | **Can't verify**. Reason: the tool ran and failed. Use `summary` as the reason. |
| `skipped` | **Can't verify**. Reason: the audit doesn't run on this platform. Use `summary` as the reason. |
| not run | **Can't verify**. Say why it wasn't run. |

Never mark an item Done from an audit that didn't return `ok`.

## lighthouse

- **Items:** `web.seo`, `common.accessibility`, `web.slow-networks`
- **When:** web apps with pages to load.
- **Needs:** a URL. Use the deployed URL when the user gives one. Otherwise, with consent, start the dev server (the repo's `dev` or `start` script) and use its localhost URL; stop the server afterwards. Also needs Google Chrome.
- **Ask first:** yes, it runs through `npx` (and starting a dev server runs the repo's code).
- **Run:** `python3 scripts/audits.py run lighthouse <url> --allow-install`
- **Read:** the summary gives the median of 3 runs for each category. A category below 0.9 is a finding (below 0.5 is high). Scores from localhost miss hosting effects (compression, CDN caching); say so.
- **Check it yourself:** open the site in Chrome, open DevTools, choose the Lighthouse tab, and run it with Mobile selected.

## osv-scanner

- **Items:** `common.dependency-audit`
- **When:** always.
- **Needs:** the repo on disk. Reads lockfiles; it doesn't install or run the project.
- **Ask first:** only to install it (it's a PATH tool: `brew install osv-scanner`). Running it reads files only.
- **Run:** `python3 scripts/audits.py run osv-scanner <repo>`
- **Read:** each finding is one vulnerability group with its CVSS score: 7 or more is high, 4 or more is medium. "No package sources found" means there's no lockfile or manifest it reads. That counts as Done only if the manifest really has no third-party dependencies (e.g. an empty `dependencies` in Package.swift); if it has dependencies but no lockfile, the item is Partial: add a lockfile.
- **Check it yourself:** run `npm audit --omit=dev` (Node), `pip-audit` (Python), or open the repo's GitHub Security tab and turn on Dependabot alerts.

## gitleaks

- **Items:** `common.secrets-in-repo`, and `common.leaked-key-rotation` when it finds a real secret
- **When:** always.
- **Needs:** the repo on disk. On a git repo it scans the history and the current files.
- **Ask first:** only to install it (PATH tool: `brew install gitleaks`).
- **Run:** `python3 scripts/audits.py run gitleaks <repo>`. It always runs with `--redact`; results never contain a secret value. Never print, quote or log a secret's value yourself, even when you open the file to check a finding: cite `file:line` and the rule name.
- **Read:** every finding is high until you check it. A finding whose location says `(commit <sha>)` is in **git history**: the line may look safe today because the secret was removed later, but anyone with the repo can still read it. Judge it by its rule, file and commit; if it looks like a real key, it's Missing and needs `common.leaked-key-rotation`. Don't run `git show` on it, which would print the value. For a finding with no commit, open the file at that line and decide:
  - a real secret (a server key, a password, a token that grants access) → Missing
  - publishable by design (Supabase anon or publishable key, Stripe `pk_` key, Firebase web config, a JWT whose payload role is `anon`) → not a leak. Check the protection behind it (e.g. row-level security on Supabase tables) and report that instead.
  - a test fixture or example value that grants nothing → not a leak; say why.
- **Check it yourself:** search your code for `secret`, `key`, `token` and `password` and look at each value; on GitHub, turn on secret scanning in Settings → Code security.

## http-observatory

- **Items:** `web.security-headers`
- **When:** deployed web apps only.
- **Needs:** the live host name (e.g. `example.com`, no `https://`).
- **Ask first:** yes, it runs through `npx`.
- **Run:** `python3 scripts/audits.py run http-observatory <host> --allow-install`
- **Read:** grade A or B is ok, C or D medium, E or F high. Info findings list the failed tests by name (e.g. `content-security-policy`). Not deployed → Can't verify, "run again after launch".
- **Check it yourself:** enter your site at developer.mozilla.org/en-US/observatory.

## checkdmarc

- **Items:** `web.email-auth`
- **When:** only when the app sends email from its own domain.
- **Needs:** the sending domain.
- **Ask first:** yes, it runs through `pipx`.
- **Run:** `python3 scripts/audits.py run checkdmarc <domain> --allow-install`
- **Read:** a missing or invalid SPF or DMARC record is high; DMARC `p=none` is medium. DKIM can't be confirmed from DNS without the email provider's selector: report DKIM as Can't verify unless the user names the selector.
- **Check it yourself:** enter your domain at a DMARC checker such as mxtoolbox.com/dmarc.aspx, and check your email provider's Domains page for verified records.

## codesign

- **Items:** `macos.developer-id-signing`, `macos.notarization`
- **When:** macOS apps, on a Mac.
- **Needs:** a built `.app` bundle. Look for one in the repo's build output first (e.g. `build/`, `.build/`, `dist/`); ask before building one.
- **Ask first:** only to build the app.
- **Run:** `python3 scripts/audits.py run codesign <path/to/App.app>`
- **Read:** `ok` means signed and accepted by Gatekeeper. An spctl "rejected" finding means other people's Macs will block it: Missing for both items unless the signature is Developer ID (then only notarization is Missing). For detail, run `codesign -dvv <app>` and look for `Authority=Developer ID Application` or `Signature=adhoc`. `skipped` off macOS.
- **Check it yourself:** download your app on another Mac and open it; a warning that Apple can't check it means it isn't notarized.

## Noise rules

- **Dev-only dependencies:** a vulnerability in a package that never ships (test runners, build tools, linters) is noise for launch. For each osv finding, say whether the package ships to production (Node: is it in `dependencies` or only `devDependencies`?). Dev-only findings make the item Partial at most, never a launch blocker.
- **Lighthouse varies run to run:** always use the median of 3 (the script does this); never quote a single run.
- **DKIM:** can't be confirmed without a selector. Never mark it Done or Missing from DNS alone.
- **Audits that run code:** `pip-audit -r requirements.txt` installs packages, and `osv-scanner fix` and `npm install` can run package scripts. On a repo you don't know, ask before any of them. ProdMate's own osv-scanner and gitleaks runs only read files.
- **Accounts you can't see:** spend caps, uptime monitors, backups and alert settings live in outside dashboards. No audit here checks them; they're Can't verify unless the user shows you.

## Audits ProdMate doesn't run for you

These help but aren't in `audits.py` yet. Mention them under "You do" when they fit, with the command to run:

- `npx @axe-core/cli <url>` or `npx pa11y <url>` for deeper accessibility checks
- `testssl.sh <host>` for TLS configuration on a deployed site
- `npx promptfoo eval` for LLM evals once an eval config exists
