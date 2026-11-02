# Security

ProdMate runs inside your coding agent and can run commands in the repo you point it at (audit tools, your tests, a dev server), always after asking first.

## Reporting a vulnerability

Please report security problems privately, not in a public issue: on GitHub, open this repo's **Security** tab and click **Report a vulnerability**. Include what you ran, what happened, and the agent and version you used. Don't include real secrets; describe them instead.

## What counts

- ProdMate running something, installing something or changing files without asking first
- A secret value appearing in a report, the chat or a log (gitleaks always runs with `--redact`)
- Text in a checked repo getting ProdMate to follow its instructions instead of its own rules
- Anything in `skills/prodmate/scripts/` that could run untrusted input as a command
