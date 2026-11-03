# Toolkit check

ProdMate works with whatever the person has. Each tool below makes some checks possible or more reliable. A missing tool never stops the run: the items it would have checked become **Can't verify**, and the report says how to check them by hand.

## Contents

- How to run the check
- How much to explain
- The tools
- Without Python

## How to run the check

Run this once, at the start, before anything else. It only looks for programs; it doesn't run or install anything:

```
for t in python3 git gh node npx pipx gitleaks osv-scanner brew; do printf '%s: ' "$t"; command -v "$t" || echo missing; done
python3 --version; gh auth status 2>&1 | head -1
```

On macOS also check `ls -d "/Applications/Google Chrome.app"` and `command -v codesign spctl`. Show only the rows that matter for the app you detected (no Lighthouse row for a macOS app, no codesign row for a web app).

## How much to explain

In the first message, ask one short question to gauge how much detail the person wants, then match it for the rest of the run:

> How comfortable are you with the terminal and GitHub? **New** (I mostly let the agent do it), **Some** (I can run commands I'm given), or **Comfortable**.

- **New:** for each missing tool, one sentence on what it checks and why that matters for *their* app, then what you'll do without it. Offer to walk them through installing only the one or two that matter most, one command at a time. Never list more than three missing tools at once; say the rest are optional.
- **Some:** a short table of what's there and what's missing, with the install command for each, and a recommendation of which to add.
- **Comfortable:** one line per tool. Skip the explanations.

If they don't answer, assume **Some**. Never treat the answer as a gate: whatever they choose, run with what's there.

## The tools

| Tool | What it unlocks | Without it | How to get it |
|---|---|---|---|
| `python3` (3.9 or newer) | ProdMate's helper scripts: consistent app detection, audit runs with clean results, and remembering decisions between runs | You follow the same steps by hand (see "Without Python"). Slower, less consistent, and decisions aren't remembered. | macOS: `xcode-select --install` (Apple's Command Line Tools include it), or python.org. Linux: `sudo apt install python3` (or your distro's package manager). |
| `git` | Scanning the whole history for leaked secrets, and checking release tags | Only the current files are scanned; release checks are Can't verify | Comes with Apple's Command Line Tools; Linux: `sudo apt install git` |
| `gh`, signed in | Docs-vs-reality checks against GitHub: releases, CI results, whether Issues are on | Those halves are Can't verify | `brew install gh`, then `gh auth login` |
| `node` / `npx` | Runs **lighthouse** (page speed, accessibility, SEO) and **http-observatory** (security headers) without installing them globally | Those web checks are Can't verify | nodejs.org, or `brew install node` |
| Google Chrome | Lighthouse needs a browser to load the page | Lighthouse is Can't verify | google.com/chrome |
| `pipx` | Runs **checkdmarc** (email DNS records) without installing it globally | Email-record checks are Can't verify | `brew install pipx` |
| **gitleaks** | Finds passwords and keys saved in the code or its history (values always hidden) | `common.secrets-in-repo` is Can't verify; you can still read the code for obvious keys, but say it's partial | `brew install gitleaks` |
| **osv-scanner** | Finds known security holes in the packages the app uses | `common.dependency-audit` is Can't verify, unless the app has no third-party packages at all | `brew install osv-scanner` |
| **codesign** / `spctl` | Checks a macOS app's signature and whether Apple's download check would block it | Built into macOS; off a Mac, signing is judged from the build scripts only | Nothing to install on a Mac |

`brew` (Homebrew, a package manager for Mac and Linux) is the easiest way to get most of these: brew.sh. Installing anything is the person's choice; ask first, and prefer `npx` and `pipx`, which don't install globally.

## Without Python

If `python3` is missing or older than 3.9, don't stop. Say so in plain words, offer the install command from the table, and carry on by hand if they'd rather not:

- **Detect:** read `scripts/detect.py` as the rulebook (which files mark an app root, which dependencies mean which type, the promise phrases to look for) and apply it yourself with file reads and searches.
- **Audits:** read `scripts/audits.py` for each tool's exact command and severity rules, run the tool directly, and read its output the same way. gitleaks must still run with `--redact`.
- **State:** skip `state.json`. Tell the person their skip decisions won't be remembered for the next run.
- **Report:** write `report.md` by hand, following "Without Python" in `references/report-template.md`. There's no guided page without Python: say so, and in "What I checked and what I couldn't" say the run was done without Python and what that cost.
