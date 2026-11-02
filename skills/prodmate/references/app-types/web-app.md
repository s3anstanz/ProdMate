# Web app checklist

Loaded when detect.py finds a `web-app`. Items about the live site (headers, SSL, uptime) need a deployed URL; when the app isn't deployed, they are Can't verify with "run again after launch".

## Contents

- Launch blockers: web.auth-on-endpoints, web.rate-limiting, web.spend-caps, web.db-backups, web.custom-domain-ssl, web.password-reset, web.privacy-terms
- Before you grow: web.restore-tested, web.staging-env, web.security-headers, web.email-auth, web.email-verification, web.account-deletion, web.cookie-consent, web.error-pages, web.performance-monitoring, web.uptime-monitoring, web.alerting
- Polish: web.seo, web.aeo, web.og-favicon, web.image-optimization, web.caching, web.slow-networks, web.landing-page, web.pricing-page

## Launch blockers

### web.auth-on-endpoints
- tier: blocker
- why: Any server route that changes data or returns private data must check who's asking, or anyone on the internet can call it.
- applies-when: the app has server routes or functions (e.g. app/api/**/route.ts, pages/api, server actions, Express or Flask handlers, Supabase edge functions) that write, delete or return non-public data
- check: For each such route, find the session or token check before the action (cite file:line). Done when every one checks, and admin routes also check the role. Missing when any route acts without a check; cite the route file and the line where it acts. Public read-only routes are fine without auth; say which ones you treated as public.
- agent-fix: add the repo's existing auth check (its session helper or middleware) to each unprotected route, plus a role check on admin routes, one route per change
- audit: none
- you-do: none

### web.rate-limiting
- tier: blocker
- why: Without a limit, someone can guess passwords thousands of times a minute or run up your bill by hammering an endpoint.
- applies-when: the app has login, signup, password reset or contact forms, or routes that call a paid API (LLM, email, SMS)
- check: Done when those routes are rate limited in code (e.g. a limiter middleware, @upstash/ratelimit, express-rate-limit, flask-limiter) or by the auth provider (cite it). Missing when the login or paid route has no limit.
- agent-fix: add a rate limiter to the login and paid routes using a library that fits the stack and hosting
- audit: none
- you-do: none

### web.spend-caps
- tier: blocker
- why: A usage-billed service with no spending limit can turn a traffic spike or an attack into a surprise bill.
- applies-when: the app uses usage-billed hosting or services (e.g. Vercel, Netlify, Supabase, Firebase, AWS, Cloudflare, email or SMS APIs); LLM APIs are covered by llm.spend-caps
- check: Spend caps and billing alerts live in accounts the agent can't see. Can't verify unless the user shows the setting. Never mark Done from code.
- agent-fix: none
- audit: none
- you-do: For each service the report names: 1) Sign in to its dashboard. 2) Open Billing or Usage. 3) Set a monthly spending limit or a budget alert at an amount you're comfortable losing. 4) Make sure the alert goes to an email you read.

### web.db-backups
- tier: blocker
- why: If your database is deleted or corrupted with no backup, your users' data is gone for good.
- applies-when: the app has a database (e.g. Supabase, Postgres, MySQL, MongoDB, Firebase, SQLite on a server; a prisma, drizzle, pg, mongoose or supabase dependency)
- check: Backups live in the database provider's settings, which the agent can't see. Can't verify unless the repo has a backup job (e.g. a scheduled workflow running pg_dump) or the user confirms. Never mark Done without seeing proof.
- agent-fix: for self-hosted databases, add a scheduled backup job; otherwise none
- audit: none
- you-do: 1) Open your database provider's dashboard. 2) Find Backups. 3) Turn on daily backups (on Supabase this needs a paid plan; point-in-time recovery is an add-on). 4) Note how many days they're kept.

### web.custom-domain-ssl
- tier: blocker
- why: A real domain with HTTPS makes the site trustworthy and keeps logins and data private in transit.
- applies-when: the app is public or will be
- check: Needs the deployed URL. Done when the site loads over https on a custom domain and http redirects to https. Can't verify when the app isn't deployed yet.
- agent-fix: none
- audit: none
- you-do: 1) Buy a domain at a registrar. 2) In your hosting dashboard, add the domain. 3) Copy the DNS records it shows into your registrar's DNS settings. 4) Wait for the certificate to show as active.

### web.password-reset
- tier: blocker
- why: People forget passwords; without a reset flow they're locked out for good.
- applies-when: the app has its own email+password login (not only OAuth or magic links, and not a hosted auth provider whose reset flow is turned on)
- check: Done when there's a reset request route, a single-use expiring token, and a page to set the new password (cite them), or the auth provider's reset is enabled and linked from the login page. Missing when login exists with no reset path.
- agent-fix: add the reset flow with the existing auth library (or the provider's reset call), plus the "Forgot password?" link
- audit: none
- you-do: if the reset email needs an email-sending service, create that account and add its API key to your environment variables

### web.privacy-terms
- tier: blocker
- why: If you collect any personal data (even an email address), the law in most places requires a privacy policy, and terms protect you.
- applies-when: the app collects personal data from the public (accounts, emails, payments, analytics)
- check: Done when privacy and terms pages exist and are linked from the footer or signup (cite the routes). Missing otherwise.
- agent-fix: draft privacy and terms pages from what the code actually collects, with every legal claim marked for the user to review, and link them in the footer
- audit: none
- you-do: read both pages and fix anything that's not true for your business; for anything with health, payments or children's data, have a lawyer review them

## Before you grow

### web.restore-tested
- tier: grow
- why: A backup you've never restored might not work when you need it.
- applies-when: the app has a database
- check: Done when docs/runbooks/restore.md exists and records a date the restore was tried. Partial when the runbook exists but was never tried. Missing when there's no runbook.
- agent-fix: offer to write docs/runbooks/restore.md with the exact restore steps for this database provider
- audit: none
- you-do: follow the runbook once into a test database and write the date at the top

### web.staging-env
- tier: grow
- why: A place to try changes before real users see them stops broken releases.
- applies-when: the app is deployed or will be, and has a database or real users
- check: Done when preview or staging deploys exist (e.g. Vercel or Netlify preview deploys, a staging environment in the deploy config, a separate staging database URL in .env.example). Missing otherwise. Can't verify hosting-side settings the repo doesn't show.
- agent-fix: add the staging environment to the deploy config and a separate staging database variable to .env.example
- audit: none
- you-do: create the staging database or project in your provider's dashboard and add its URL to the staging environment

### web.security-headers
- tier: grow
- why: Security headers tell browsers to block common attacks like clickjacking and script injection.
- applies-when: the app serves web pages
- check: Done from an MDN HTTP Observatory grade of A or B on the deployed host. Headers set in code (e.g. next.config headers(), vercel.json, middleware) are Partial until confirmed on the live site. Can't verify when the app isn't deployed; mention any header config found in code.
- agent-fix: add Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options and Referrer-Policy in the framework's header config
- audit: http-observatory
- you-do: none

### web.email-auth
- tier: grow
- why: SPF, DKIM and DMARC records prove your emails are really from you, so they land in inboxes instead of spam.
- applies-when: the app sends email from its own domain (code that sends mail through SMTP, Resend, SendGrid, Postmark, SES, or auth emails from a custom domain). Not applicable when no code sends email.
- check: Run checkdmarc on the sending domain. Done when SPF and DMARC exist and DMARC is not p=none. DKIM can't be confirmed from DNS without a selector; mark it Can't verify unless the email provider's selector is known.
- agent-fix: none
- audit: checkdmarc
- you-do: 1) In your email provider, open Domains and add your domain. 2) Copy the SPF, DKIM and DMARC records it shows into your registrar's DNS. 3) Start DMARC at p=quarantine once mail is flowing.

### web.email-verification
- tier: grow
- why: Confirming an email address stops fake signups and makes sure password resets reach the right person.
- applies-when: people can sign up with an email address
- check: Done when signup sends a confirmation link and unconfirmed accounts are limited (or the auth provider's confirm-email setting is on and referenced). Missing otherwise.
- agent-fix: turn on or add the email confirmation step with the existing auth library
- audit: none
- you-do: none

### web.account-deletion
- tier: grow
- why: People must be able to delete their account and data; many laws and both app stores require it.
- applies-when: users can create accounts
- check: Done when a delete-account action exists that removes the user's data (cite the route and what it deletes). Missing otherwise.
- agent-fix: add a delete-account route (behind auth) and a button in settings that deletes the user's rows and auth record
- audit: none
- you-do: none

### web.cookie-consent
- tier: grow
- why: In the EU and UK, you must ask before setting tracking or advertising cookies.
- applies-when: the app loads analytics, ads or other non-essential cookies or trackers and may have EU or UK visitors. Not applicable when it only sets essential cookies (login session, preferences).
- check: Done when non-essential scripts load only after consent (cite the consent banner and where scripts are gated). Missing when trackers load on page view.
- agent-fix: add a consent banner that gates the tracking scripts, or switch to cookieless analytics so no banner is needed
- audit: none
- you-do: none

### web.error-pages
- tier: grow
- why: A friendly error, empty or loading screen tells people what happened instead of showing a blank or broken page.
- applies-when: the app serves web pages
- check: Done when a custom 404 page, a 500 or error page, and loading and empty states for data views exist (e.g. app/not-found.tsx, app/error.tsx, app/loading.tsx in Next.js; 404.html for static sites). Partial when some exist. Missing when there's no custom 404 page.
- agent-fix: add the missing not-found, error and loading pages in the framework's convention
- audit: none
- you-do: none

### web.performance-monitoring
- tier: grow
- why: Real-user speed numbers show when the site gets slow for real visitors, not just on your machine.
- applies-when: the app is deployed with real users. Not applicable when the app promises no analytics or no tracking; the reason quotes the promise.
- check: Done when real-user monitoring is set up in code (e.g. @vercel/speed-insights, web-vitals reporting, an APM SDK). Missing otherwise.
- agent-fix: add the monitoring package that matches the hosting (e.g. Vercel Speed Insights on Vercel)
- audit: none
- you-do: turn the feature on in your hosting dashboard if it needs a switch there

### web.uptime-monitoring
- tier: grow
- why: An uptime monitor tells you the site is down before your users do.
- applies-when: the app is deployed or will be
- check: Uptime monitors usually live in outside accounts. Done only when the repo shows one (e.g. a scheduled workflow that checks the URL, a checkly or Better Stack config) or the user confirms it. Can't verify otherwise, and always when the app isn't deployed yet.
- agent-fix: add a scheduled GitHub Actions workflow that requests the site's URL and fails (emailing the repo owner) when it's down
- audit: none
- you-do: or sign up for a free uptime monitor, add your URL, and set alerts to your email

### web.alerting
- tier: grow
- why: Errors and downtime only help if someone gets told about them.
- applies-when: the app is deployed with real users
- check: Done when error tracking or uptime checks send alerts to a person (email, Slack, phone) and that's documented or configured in code. Can't verify settings that live only in outside dashboards.
- agent-fix: none
- audit: none
- you-do: in your error tracker and uptime monitor, set alerts to go to an email or phone you check

## Polish

### web.seo
- tier: polish
- why: Search engines need a sitemap, a robots file and page titles to list your site.
- applies-when: the app has public pages meant to be found in search. Not applicable for apps where every page is behind a login.
- check: Done when a sitemap (e.g. app/sitemap.ts, public/sitemap.xml), a robots file (app/robots.ts, public/robots.txt) and page titles and descriptions exist, and the Lighthouse SEO median is at least 0.9. Missing when there's no sitemap and no robots file.
- agent-fix: add the sitemap and robots routes in the framework's convention, plus title and description metadata
- audit: lighthouse
- you-do: after launch, add the site in Google Search Console and submit the sitemap

### web.aeo
- tier: polish
- why: Clear page structure and descriptions help AI assistants find and quote your site correctly.
- applies-when: the app has public content meant to be found
- check: Done when pages have descriptive titles, headings in order and structured data (JSON-LD) where it fits. llms.txt is optional: Google says Search ignores it, so never mark this item Missing for lacking one.
- agent-fix: add structured data to the main pages and, only if the user wants it, an llms.txt
- audit: none
- you-do: none

### web.og-favicon
- tier: polish
- why: A favicon and a share image make your links look real in browser tabs and when shared.
- applies-when: the app serves web pages
- check: Done when a favicon and Open Graph title, description and image exist (e.g. app/icon.png, app/opengraph-image.*, og: meta tags). Partial when some exist.
- agent-fix: add the missing favicon and Open Graph metadata; the image itself may need the user
- audit: none
- you-do: provide a logo or a 1200x630 share image if you have one

### web.image-optimization
- tier: polish
- why: Big images make pages slow, especially on phones.
- applies-when: the app shows images
- check: Done when images use the framework's optimizer (e.g. next/image) or modern formats with sizes set. Missing when large raw images are served (cite files over 500 KB in public/).
- agent-fix: switch img tags to the framework's image component and compress oversized files
- audit: none
- you-do: none

### web.caching
- tier: polish
- why: Caching serves repeat visits faster and cuts hosting costs.
- applies-when: the app is deployed or will be
- check: Done when static assets get long-lived cache headers (most frameworks do this by default) and data fetching sets an explicit cache policy where it matters. Partial when dynamic pages that could be static are rendered on every request.
- agent-fix: set cache headers or the framework's revalidate options on pages that rarely change
- audit: none
- you-do: none

### web.slow-networks
- tier: polish
- why: Many people use slow or flaky connections; the app should still load and say when it's offline.
- applies-when: the app serves web pages
- check: Done when the Lighthouse performance median is at least 0.9 on its default throttled mobile profile and the app shows loading states. Partial below that.
- agent-fix: lazy-load heavy components and add loading states
- audit: lighthouse
- you-do: none

### web.landing-page
- tier: polish
- why: A landing page tells visitors what the app does and why they'd want it, in seconds.
- applies-when: the app is public and wants new users
- check: Done when the home page (for signed-out visitors) says what the app does and has one clear next step (sign up, download, try it). Missing when visitors land on a login form with no explanation.
- agent-fix: draft a simple landing page from the README's description
- audit: none
- you-do: replace the placeholder copy with your own words and a screenshot

### web.pricing-page
- tier: polish
- why: If you charge money, people want to see the price before they sign up.
- applies-when: the app charges money (e.g. a Stripe, Paddle or Lemon Squeezy dependency, or paid plans in the code)
- check: Done when a pricing page exists and matches the plans in code. Missing otherwise.
- agent-fix: draft a pricing page from the plans defined in code
- audit: none
- you-do: confirm the prices and what each plan includes
