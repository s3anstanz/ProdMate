# LLM app overlay

Added on top of the app-type checklist when detect.py finds an `llm-app` overlay (a model SDK such as openai, anthropic or the ai package).

## Launch blockers

### llm.prompt-injection
- tier: blocker
- why: Text from users or web pages can carry instructions that trick the model into leaking data or misusing its tools.
- applies-when: user input, uploaded files or fetched web content reach a model prompt
- check: Missing when user text is inserted into the system prompt (e.g. an f-string or template into system=), or when the model can call tools with broad power (reading any file, running shell commands, sending email) without an allow-list or a human confirmation. Cite file:line. Done when user text goes only in user messages, tools are narrow (allow-listed paths or actions), and model output is never executed as code or SQL.
- agent-fix: move user text out of the system prompt into a user message, restrict tools to an allow-list (e.g. one directory, read-only), and require confirmation for actions with side effects
- audit: none
- you-do: none

### llm.spend-caps
- tier: blocker
- why: Every model call costs money; one bug or abusive user with no cap can run up a huge bill overnight.
- applies-when: the app calls a paid model API
- check: Provider spending limits live in the provider's console, which the agent can't see. Can't verify unless the user shows the setting. Per-user quotas in code are a separate safeguard; cite them if present.
- agent-fix: none
- audit: none
- you-do: 1) Sign in to the model provider's console (e.g. console.anthropic.com or platform.openai.com). 2) Open Billing or Limits. 3) Set a monthly spend limit and an email alert below it. 4) Use a separate API key for this app so you can revoke it alone.

## Before you grow

### llm.model-fallback
- tier: grow
- why: Model APIs go down and rate-limit; without a fallback, your app breaks whenever they do.
- applies-when: the app calls a model API
- check: Done when model calls handle errors with retries and backoff, and fall back to another model or show a clear message (cite the try/except or catch). Missing when the call has no error handling.
- agent-fix: wrap model calls in error handling with retry and backoff (the SDK's max_retries setting where it has one), and return a friendly error or a fallback model on failure
- audit: none
- you-do: none

### llm.token-limits
- tier: grow
- why: Without limits, one huge input or a runaway answer can be slow, fail, or cost far more than it should.
- applies-when: the app calls a model API
- check: Done when calls set max_tokens (or the SDK's equivalent) and user input is length-checked before it's sent (cite both). Partial when only one is set. Missing when neither is.
- agent-fix: add an input length check that rejects or trims oversized input, and set max_tokens on every call
- audit: none
- you-do: none

### llm.evals
- tier: grow
- why: Evals are tests for the model's answers; they tell you whether a prompt or model change made things better or worse.
- applies-when: the app's behavior depends on model output
- check: Done when the repo has evals: fixed inputs with expected properties of the output, run by a script or test (e.g. an evals/ dir, promptfoo config, or tests that call the model). Missing otherwise.
- agent-fix: add an evals/ dir with five to ten representative cases and a script that runs them and reports pass or fail
- audit: none
- you-do: add real examples from your users to the eval cases over time
