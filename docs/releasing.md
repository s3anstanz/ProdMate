# Releasing ProdMate

Versions follow `MAJOR.MINOR.PATCH`: a patch for fixes, a minor version for new checklist items or features, a major version when the workflow or report changes in a way people would notice.

## Steps

1. **Bump the version** in `.claude-plugin/marketplace.json` (`plugins[0].version`). Claude Code plugin users only get an update when this number changes.
2. **Make sure `main` is green.** The Tests workflow must pass on every OS and Python in its matrix.
3. **Run the checks locally** if you changed scripts or checklists:
   ```
   python3 -m unittest discover -s tests/prodmate -t .
   python3 skills/prodmate/scripts/lint_checklists.py skills/prodmate/references
   ```
4. **Tag and push the tag:**
   ```
   git tag v<version>
   git push origin v<version>
   ```
5. **Publish the release:** `gh release create v<version> --generate-notes`, or on GitHub open Releases, choose **Draft a new release**, pick the tag, click **Generate release notes**, then **Publish release**.
6. **Check an install:** in a scratch folder, `npx skills add s3anstanz/prodmate --list` should show `prodmate`.

If a release turns out to be broken, see [runbooks/rollback.md](runbooks/rollback.md).
