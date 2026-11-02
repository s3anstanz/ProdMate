# MCP catalog

Official MCP (Model Context Protocol) servers that let the agent help set up a tool the report recommends. Every server below was checked on the vendor's own docs on 2026-11-02. With web access, re-check the docs URL before suggesting one; without it, say "may be out of date, checked 2026-11-02".

## Contents

- Rules for every MCP action
- Catalog: Sentry, Vercel, Supabase, Amplitude, Stripe, Cloudflare, GitHub
- Which items each server helps with

## Rules for every MCP action

- **Suggest, don't connect.** Offer the server, say what it would let you do, and let the user add it to their agent. prodmate v1 never configures one itself.
- **Every outward action needs its own explicit yes:** anything that creates an account, project or resource, spends money, changes DNS, deploys, or pushes. One yes covers one action, not a session.
- **Prefer read-only and narrow scopes** where the server offers them (listed below).
- **Never suggest a server that breaks a stated promise** (no analytics or error-tracking server for an app that promises no tracking).
- These servers act with the user's own account permissions. Say so when you suggest one.

## Catalog

### Sentry
- **Docs:** https://mcp.sentry.dev/ (checked 2026-11-02)
- **Server:** remote `https://mcp.sentry.dev/mcp`, or local `npx @sentry/mcp-server@latest`. Auth: OAuth, or a Sentry user auth token.
- **Can set up:** create a project and get its DSN (`create_project`, `find_dsns`), create alert rules and uptime monitors, look up releases and issues.
- **Needs a yes:** creating projects, teams, DSNs, alerts and monitors.
- **Scope it:** org or project in the URL (`/mcp/{org}/{project}`); turn off the `project-management` skill to remove project creation.

### Vercel
- **Docs:** https://vercel.com/docs/mcp/vercel-mcp (checked 2026-11-02)
- **Server:** remote `https://mcp.vercel.com`. Auth: OAuth, for clients Vercel has reviewed.
- **Can set up:** environment variables, deployments (promote, roll back), runtime logs and errors, domains and DNS records, firewall, Web Analytics.
- **Needs a yes:** `buy_domain` (spends money; auto-renew defaults on), DNS record changes, deploys, promotions and rollbacks.
- **Scope it:** grant only the teams you need in OAuth. No read-only mode is documented; it has your account's access.

### Supabase
- **Docs:** https://supabase.com/docs/guides/getting-started/mcp (checked 2026-11-02)
- **Server:** remote `https://mcp.supabase.com/mcp`. Auth: OAuth in the browser, or a personal access token.
- **Can check or set up:** list tables and migrations, run the security and performance advisors (`get_advisors`, which flags tables without row-level security), read logs, get the project URL and keys, deploy Edge Functions. No backup tool is listed; backups stay under You do.
- **Needs a yes:** applying migrations or running SQL that writes, creating projects or branches (these can cost money; the server asks for a cost confirmation).
- **Scope it:** `read_only=true` (read-only database user), `project_ref=<id>` (one project, no account tools), `features=<groups>`.

### Amplitude
- **Docs:** https://amplitude.com/docs/amplitude-ai/amplitude-mcp (checked 2026-11-02)
- **Server:** remote `https://mcp.amplitude.com/mcp` (EU: `https://mcp.eu.amplitude.com/mcp`). Auth: OAuth.
- **Can set up:** a tracking plan (events and properties), charts, dashboards, cohorts. It isn't an ingestion endpoint: the app still needs Amplitude's SDK in code.
- **Needs a yes:** creating or deleting events, properties, dashboards, cohorts, experiments or flags.
- **Scope it:** per-project "Use MCP (read)" and "Use MCP (write)" permissions.

### Stripe
- **Docs:** https://docs.stripe.com/mcp (checked 2026-11-02)
- **Server:** remote `https://mcp.stripe.com`. Auth: OAuth, or a Stripe agent API key.
- **Can set up:** products, prices, payment links, Checkout, customer portal, webhook endpoints, tax settings (useful for `web.pricing-page`).
- **Needs a yes:** everything that writes, and always for refunds, money movement, invoices, subscriptions, or company formation. Use a sandbox first; it works in live mode too.
- **Scope it:** grant the sandbox environment only, or an agent key with the fewest permissions.

### Cloudflare
- **Docs:** https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/ (checked 2026-11-02)
- **Server:** remote `https://mcp.cloudflare.com/mcp`. Auth: OAuth (pick permissions at sign-in), or an API token.
- **Can set up:** DNS records, Workers, R2, KV, Zero Trust settings (useful for `web.custom-domain-ssl` and `web.email-auth` records).
- **Needs a yes:** every DNS change and every write.
- **Scope it:** choose the narrowest permissions at OAuth time or on the token. No read-only mode is documented.

### GitHub
- **Docs:** https://github.com/github/github-mcp-server (checked 2026-11-02)
- **Server:** remote `https://api.githubcopilot.com/mcp/`, or local Docker image `ghcr.io/github/github-mcp-server`. Auth: OAuth or a personal access token.
- **Can check or set up:** list releases and tags (docs-vs-reality for `common.release-process`), Dependabot and secret-scanning alerts, issues (an issue template for `common.support-channel`), Actions runs, repository rulesets.
- **Needs a yes:** creating repos, branches, files or issues, pushing, triggering workflows. No create-release tool was listed; releases stay under You do.
- **Scope it:** read-only with the `/readonly` URL suffix (remote) or `--read-only` (local); limit toolsets with `X-MCP-Toolsets` or `--toolsets`.

## Which items each server helps with

| Item | Server |
|---|---|
| `common.error-tracking`, `web.alerting`, `web.uptime-monitoring` | Sentry (only for apps with no privacy promise) |
| `common.analytics` | Amplitude (only for apps with no privacy promise) |
| `common.secrets-in-repo` follow-up (env vars), `web.staging-env`, `web.custom-domain-ssl` | Vercel |
| `web.auth-on-endpoints` (row-level security check), `web.db-backups` (project facts only) | Supabase |
| `web.pricing-page` | Stripe |
| `web.custom-domain-ssl`, `web.email-auth` (DNS records) | Cloudflare or Vercel, wherever the domain's DNS lives |
| `common.release-process`, `common.dependency-audit`, `common.support-channel` | GitHub |
