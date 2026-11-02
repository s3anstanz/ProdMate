# ProdMate

**ProdMate** checks whether an app you built with an AI coding agent is ready for production launch, then helps you close the gaps.

You point your agent (Claude Code, Codex, Cursor) at a repo and say "Run ProdMate on this repo." ProdMate:

1. **Detects** what kind of app it is (web app, macOS app, LLM app and more) and reads the app's own promises, like "never touches the network".
2. **Triages** a checklist, skipping items that don't apply or would break those promises.
3. **Assesses** the rest with `file:line` evidence and free audit tools (Lighthouse, osv-scanner, gitleaks, MDN HTTP Observatory, checkdmarc, codesign). It asks before installing or running anything.
4. **Reports** a ranked list: launch blockers, then before you grow, then polish. Each item says who acts: the agent can fix it, the agent can check it, or you do it, with exact steps.
5. **Acts**: it offers fixes one approved change at a time and never commits, deploys or pushes on its own.

## Install

With the [skills CLI](https://www.npmjs.com/package/skills), into any supported agent:

```
npx skills add s3anstanz/prodmate
```

As a Claude Code plugin:

```
/plugin marketplace add s3anstanz/prodmate
/plugin install prodmate@prodmate
```

Or copy the folder by hand:

- Claude Code: copy `skills/prodmate` to `.claude/skills/prodmate` in your repo (or `~/.claude/skills/prodmate` for every repo).
- Codex, Cursor and other agents that read `.agents/skills/`: copy `skills/prodmate` to `.agents/skills/prodmate`.

ProdMate checks what you have before it starts and works with it. Python 3.9 or newer makes it faster and more consistent (it runs ProdMate's helper scripts); without it, the agent does the same steps by hand. The audit tools are optional too: ProdMate explains what each one adds, asks before running any through `npx` or `pipx`, and marks an item "Can't verify" when a tool isn't there, with steps to check it yourself.

## What's in this repo

- `skills/prodmate/`: the skill itself. This is the only folder an install copies.
- `tests/prodmate/`: unit tests for the skill's scripts. Run them with `python3 -m unittest discover -s tests/prodmate -t .`
- `docs/prodmate/`: design notes.
- `.claude-plugin/marketplace.json`: the Claude Code plugin listing.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
