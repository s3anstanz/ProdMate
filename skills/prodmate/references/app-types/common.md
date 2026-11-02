# Common checklist

Loaded for every app type. Each item lists when it applies, what counts as done, and who acts. Item format: see `scripts/lint_checklists.py`.

## Contents

- Launch blockers: common.dependency-audit, common.secrets-in-repo, common.leaked-key-rotation
- Before you grow: common.ci, common.unit-tests, common.smoke-tests, common.readme, common.release-process, common.rollback-plan, common.logging, common.error-tracking, common.analytics, common.accessibility, common.multi-device-testing
- Polish: common.regression-tests, common.license, common.changelog, common.support-channel

## Launch blockers

### common.dependency-audit
- tier: blocker
- why: Code you borrowed from other people can have known security holes that attackers already know how to use.
- applies-when: always; an app with no third-party dependencies (no lockfile and no dependency list in its manifest) still applies and counts as Done with that as the evidence
- check: Done when osv-scanner reports no known vulnerabilities, or the app has no third-party dependencies (cite the manifest, e.g. Package.swift with an empty dependencies list). Missing when any vulnerability ships to production; a vulnerability only in dev dependencies (test tools, build tools that don't ship) is Partial and the report says it doesn't ship. Can't verify when osv-scanner didn't run.
- agent-fix: upgrade the vulnerable packages to the fixed versions osv-scanner names, one package per change, and run the tests after each
- audit: osv-scanner
- you-do: none

### common.secrets-in-repo
- tier: blocker
- why: A password or API key saved in the code can be copied by anyone who sees the code, and costs money or data once it's found.
- applies-when: always
- check: Done when gitleaks (run with --redact) finds nothing in the files or git history, and secrets are read from environment variables or a secrets store (cite the file:line that reads them, e.g. os.environ or process.env). Missing when a real secret is committed (cite file:line, never the value). Publishable-by-design keys are not leaks: Supabase anon or publishable keys, Stripe publishable pk_ keys, Firebase web config, and other keys meant for the browser. For those, check the protection behind them instead (e.g. row-level security on every Supabase table) and report that, not the key.
- agent-fix: move the secret into an environment variable, read it from there, add the variable name to .env.example, and add .env to .gitignore; then offer common.leaked-key-rotation
- audit: gitleaks
- you-do: none

### common.leaked-key-rotation
- tier: blocker
- why: Removing a leaked key from the code doesn't help if the key still works; anyone who copied it can keep using it.
- applies-when: gitleaks or the agent found a real secret in the files or git history (it was committed at any point)
- check: Done only when the user confirms the key was revoked and replaced at the provider; the agent can't see provider accounts, so otherwise Can't verify. Missing when a leak was found and the user hasn't rotated it.
- agent-fix: none
- audit: none
- you-do: 1) Sign in to the provider that issued the key (named in the finding). 2) Create a new key. 3) Put the new key in your environment variables or hosting dashboard, not in the code. 4) Delete or revoke the old key. 5) Check the provider's usage log for activity you don't recognize.

## Before you grow

### common.ci
- tier: grow
- why: Automatic checks on every change catch mistakes before your users do.
- applies-when: always
- check: Done when a CI config exists (e.g. .github/workflows/*.yml, .gitlab-ci.yml, .circleci/config.yml) and runs the build and tests on pushes or pull requests (cite the file and the step). Partial when CI exists but only builds, or doesn't run the tests. Missing when there is no CI config.
- agent-fix: add a CI workflow in the repo's existing provider (GitHub Actions if none) that installs, builds and runs the existing tests
- audit: none
- you-do: none

### common.unit-tests
- tier: grow
- why: Small automatic tests prove each piece still works after you or an agent change it.
- applies-when: always
- check: Done when the repo has unit tests for its core logic and they run: locally (if consent allows) or in CI. Cite the test dir and the CI step that runs them, plus a passing run when you can see one (a local run, or `gh run list`). Tests that exist and that CI runs count as Done even when you can't run them yourself; say which evidence you saw. Partial when tests exist but cover only a small part of the code, nothing runs them, or the last run failed. Missing when there are none.
- agent-fix: add unit tests for the most important module using the repo's existing test framework (or the language's standard one), and a test command in the manifest
- audit: none
- you-do: none

### common.smoke-tests
- tier: grow
- why: One quick end-to-end test that the app starts and its main action works catches the worst breakages in seconds.
- applies-when: always
- check: Done when a test starts the real app (or its server, or binary) and exercises the main flow (e.g. a Playwright test, an XCUITest or a script in CI that launches the built app), and CI or a local run executes it (cite both, as for common.unit-tests). Missing when only unit tests exist.
- agent-fix: add one end-to-end test of the main flow in the repo's existing framework, and run it in CI if CI exists
- audit: none
- you-do: none

### common.readme
- tier: grow
- why: A README tells people what the app does and how to install it, run it and get help.
- applies-when: always
- check: Done when the README says what the app is, how to install or run it, and how to run its tests. Partial when one of those is missing or the install steps don't match the repo (e.g. a script it names doesn't exist). Missing when there is no README.
- agent-fix: write or fill out the README sections that are missing, using only commands that exist in the repo
- audit: none
- you-do: none

### common.release-process
- tier: grow
- why: A written, repeatable release process means each version can be found, installed and rolled back.
- applies-when: the app is meant for people other than its author (a public repo people install from, or anything deployed, published or downloadable), even before its first release; or its docs describe a release process
- check: Compare what README, CONTRIBUTING or docs say about releases (tags, version numbers, release notes, a release script) with reality: `git tag` and, when gh is available, `gh release list`. Done when the docs and the tags or releases match. Missing when the docs describe tagging or releases but none exist (cite the doc line and the empty tag list). Partial when releases exist but the process isn't written down. Can't verify the GitHub releases half when gh isn't available; say so.
- agent-fix: write the release steps into CONTRIBUTING.md or docs/releasing.md to match how the repo actually builds, and add a release script or workflow that tags the version; never create a tag or release without an explicit yes
- audit: none
- you-do: create the first tag and release once the steps are written: run the release script the agent wrote, or `git tag v<version>` then `git push --tags`

### common.rollback-plan
- tier: grow
- why: When a release breaks something, a written rollback plan gets the last good version back in minutes instead of hours.
- applies-when: the app is meant for people other than its author, even before its first release
- check: Done when docs/runbooks/rollback.md or an equivalent doc says how to return to the previous version for this app's deploy or distribution method. Missing when no such doc exists.
- agent-fix: offer to write docs/runbooks/rollback.md for this app's deploy or distribution method (e.g. promote the previous Vercel deployment, re-publish the previous GitHub Release, revert the Homebrew cask version), with the exact commands
- audit: none
- you-do: read the runbook once and try the first step on a test release so you know it works

### common.logging
- tier: grow
- why: Logs are how you find out what went wrong after a user reports a problem.
- applies-when: always
- check: Done when the app logs errors through a logger or the platform's log system (e.g. os.Logger on Apple platforms, a structured logger on servers) and the logs don't contain passwords, tokens or personal data (cite file:line). Partial when it only prints to the console or logs sensitive data. Missing when errors are swallowed silently.
- agent-fix: add logging at error points using the platform's standard logger, without personal data
- audit: none
- you-do: none

### common.error-tracking
- tier: grow
- why: Error tracking tells you about crashes your users hit but never report.
- applies-when: the app is meant for people other than its author. Under a no-network, no-tracking or no-telemetry promise it still applies, but only the local, user-initiated option below may be recommended; quote the promise.
- check: Done when an error-tracking setup exists in code (e.g. a Sentry SDK init, or a local crash-report flow) and is wired up for production. Missing when none exists.
- agent-fix: for apps with no privacy promise, add the SDK init for a tracker the user picks, reading its DSN from an environment variable; never suggest a hosted service to an app that promises no network or no tracking. For those, the only option is local and user-initiated: e.g. a "Report a problem" action that attaches the OS crash log to an email or a GitHub issue the user sends themselves.
- audit: none
- you-do: create an account with the error tracker you picked and put its DSN in your hosting environment variables (only for apps with no privacy promise)

### common.analytics
- tier: grow
- why: Analytics show which features people use, so you know what to build next.
- applies-when: the app is meant for people other than its author. Not applicable when the app promises no analytics, no tracking, no telemetry or no network; the reason quotes the promise.
- check: Done when an analytics SDK or privacy-friendly counter is set up and documented in the privacy policy. Missing when none exists.
- agent-fix: for apps with no privacy promise, add the analytics snippet or SDK the user picks and mention it in the privacy policy; never suggest a hosted analytics service to an app that promises no analytics, no tracking or no network
- audit: none
- you-do: create the analytics account you picked and paste its site ID where the agent left the placeholder (only for apps with no privacy promise)

### common.accessibility
- tier: grow
- why: People who use screen readers, keyboards or reduced motion should be able to use your app, and in many places the law requires it.
- applies-when: the app has a user interface (web pages, desktop or mobile UI). Not applicable for CLIs, libraries and APIs.
- check: Web: Lighthouse accessibility score of at least 0.9 (median of 3) and form fields have labels. Native: controls have accessibility labels, and the app respects Reduce Motion and Dynamic Type or system text size where it animates or shows text (cite file:line). Partial when some but not all are true.
- agent-fix: add missing labels, alt text and Reduce Motion handling, one screen at a time
- audit: lighthouse
- you-do: try the main flow once with the screen reader on (VoiceOver: Cmd+F5 on Mac) and note anything you can't reach

### common.multi-device-testing
- tier: grow
- why: An app that works on your laptop can still break on a phone, a small screen or another browser.
- applies-when: the app runs on more than one kind of device or browser (web apps, mobile apps). Not applicable for desktop-only apps, where macos.min-os-tested covers OS versions instead.
- check: Done when tests or CI run on more than one browser or device size (e.g. Playwright projects for chromium, webkit and a mobile viewport), or the README documents a manual device check. Missing otherwise.
- agent-fix: add browser and mobile-viewport projects to the existing end-to-end test config
- audit: none
- you-do: open the app on your own phone and one other browser and try the main flow

## Polish

### common.regression-tests
- tier: polish
- why: A test for each bug you fix stops that bug from quietly coming back.
- applies-when: always
- check: Done when fixed bugs have tests that name them (e.g. a test named after an issue number, or commit messages "fix: ... with test"). Missing when bug-fix commits never add tests.
- agent-fix: when fixing a bug in the Act phase, add a test that reproduces it first
- audit: none
- you-do: none

### common.license
- tier: polish
- why: A license tells others whether they may use, copy or change your code; without one, nobody legally can.
- applies-when: the code is public or will be shared. Not applicable for private code that isn't shared.
- check: Done when a LICENSE file exists and the README or manifest names the same license. Missing when the repo is public and has no LICENSE.
- agent-fix: add the LICENSE file for the license the user picks (MIT if they don't mind), with their name and the year
- audit: none
- you-do: pick a license (choosealicense.com explains the options in plain words)

### common.changelog
- tier: polish
- why: A changelog tells users what changed in each version, so updates don't surprise them.
- applies-when: the app has more than one release or version
- check: Done when CHANGELOG.md or release notes exist for recent versions. Missing when versions change but nothing records what changed.
- agent-fix: write CHANGELOG.md from the git history since the last tag (or the last 30 commits), grouped by version
- audit: none
- you-do: none

### common.support-channel
- tier: polish
- why: People need a way to report a bug or ask for help, or they just leave.
- applies-when: the app is meant for people other than its author
- check: Done when the README, app or site names a support path (GitHub Issues enabled, a support email, a feedback form, or an in-app "Report a problem"). Missing otherwise.
- agent-fix: add a "Getting help" section to the README and, for apps with a UI, a link to it; for GitHub repos, an issue template in .github/ISSUE_TEMPLATE
- audit: none
- you-do: decide where support requests go (an email you check, or GitHub Issues)
