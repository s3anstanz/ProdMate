# Rolling back a bad release

Installs (`npx skills add`, the paste-this line, a hand copy) read the repo's `main` branch, so a rollback means getting `main` back to the last good state and shipping that as a new version.

1. **Find the last good version:** `gh release list`, or `git tag --sort=-v:refname | head`.
2. **Revert the bad change on `main`,** don't rewrite history:
   ```
   git revert <bad-commit>        # or a range: git revert <first-bad>^..<last-bad>
   ```
   Open a pull request with the revert so the Tests workflow runs, then merge it.
3. **Ship it as a new patch version:** follow [releasing.md](../releasing.md) with the next patch number (never reuse or move an existing tag).
4. **Tell people:** add a line to the release notes saying which version was bad and what to do, and mark the bad GitHub Release as a pre-release so "Latest" points at the fixed one.

People who want to stay on an older version can install from a tag: `npx skills add https://github.com/s3anstanz/ProdMate/tree/v<good-version>` (or copy `skills/prodmate` from that tag by hand).
