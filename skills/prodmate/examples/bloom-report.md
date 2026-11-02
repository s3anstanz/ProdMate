# Production readiness: Bloom

3 launch blockers, 6 before you grow, 4 polish. Checked 2026-11-02 with prodmate.

(Counts are the open items in each tier: Missing, Partial or Can't verify. Items already Done are listed one line each under their tier.)

Bloom's code, tests and CI (automatic checks that run on every change) are in very good shape. What stands between it and other Mac users is how they get it: today the only way to install is `git clone` plus a build with Apple's developer tools, and the build is signed only "ad-hoc" (a signature with no developer identity behind it), so macOS blocks it on anyone else's Mac. Start with a signed, notarized download on a GitHub Release.

## What I checked and what I couldn't

- **App:** macos-app at `.` (Package.swift: `.macOS(.v13)`; Support/Info.plist: `CFBundlePackageType APPL`). A menu-bar utility (`LSUIElement`), Swift, no third-party packages.
- **Ran:**
  - osv-scanner, a known-vulnerability scanner for dependencies (`ok`: no lockfile or manifest with dependencies, which matches `Package.swift`'s empty dependency list).
  - gitleaks, a scanner for passwords and keys committed to the code (`ok`: no secrets in the files or the git history).
  - codesign on `build/Bloom.app`, built with the repo's own `scripts/bundle.sh release build/Bloom.app` (`issues`: "spctl: build/Bloom.app: rejected"; `codesign -dvv` shows `Signature=adhoc`, `TeamIdentifier=not set`).
  - `gh` (GitHub's command-line tool) against `s3anstanz/Bloom`, the repo named in README.md:63: public, Issues on, 0 tags, 0 releases, latest CI, E2E and CodeQL runs on `main` all `success` (including commit 64621e2, the commit checked here).
- **Didn't run:** `swift test` on this Mac. You agreed to builds and audit tools, not to running the test suite, so the unit-test evidence comes from the green GitHub CI runs instead. I didn't run `scripts/install.sh` or launch the app, as you asked.
- **Couldn't see:** your Apple Developer account, whether you have a Developer ID certificate, and any notarization credentials.

## Promises honored

- "never touches the network" (`README.md:11`), "It has no network code, no analytics and no third-party dependencies" (`README.md:142`), "has no network code" (`SECURITY.md:3`). Because of these I skipped `common.analytics`. Two items still apply, but only in a form that keeps the promise:
  - `common.error-tracking`: only a local report the person sends themselves. No hosted crash tracker.
  - `macos.update-path`: only GitHub Release downloads and a Homebrew cask. No in-app updater that checks the internet.

## Launch blockers

### macos.developer-id-signing: Missing
macOS blocks apps that aren't signed with an Apple Developer ID, so anyone who downloads Bloom sees a warning or can't open it.
- **Evidence:** the codesign audit on `build/Bloom.app` returned `Signature=adhoc`. `scripts/bundle.sh:24-25` signs with `codesign --force --sign -`, where `-` means ad-hoc. No script or workflow signs with a Developer ID.
- **Next step:** add a release workflow that signs `Bloom.app` and its helper `BloomRender` with `codesign --sign "Developer ID Application: …" --options runtime --timestamp`. Hardened runtime is what `--options runtime` turns on, and notarization requires it. The workflow reads the certificate from repository secrets. Leave `scripts/bundle.sh` ad-hoc for local builds.
- **Who:** You do (Apple Developer Program, certificate), then Agent can fix (the workflow)

### macos.notarization: Missing
Apple must scan and approve a downloaded app (notarization, Apple's malware scan for downloaded apps), or macOS refuses to open it for most people.
- **Evidence:** spctl (Gatekeeper, macOS's check on downloaded apps) says `rejected` for `build/Bloom.app`. No `notarytool` or `stapler` step exists anywhere in `scripts/` or `.github/workflows/`.
- **Next step:** in the same release workflow, add `xcrun notarytool submit Bloom.zip --wait` and then `xcrun stapler staple Bloom.app`, using credentials from repository secrets.
- **Who:** You do (app-specific password), then Agent can fix (the workflow steps)

### macos.distribution: Missing
People who don't use developer tools need a normal way to download and install the app.
- **Evidence:** the only install path is `git clone` plus `scripts/install.sh` (`README.md:58-64`), and it needs Apple's Command Line Tools (`README.md:60`, `scripts/install.sh:13-17`). GitHub has 0 releases. CI already builds a `Bloom.zip` (`.github/workflows/ci.yml:68-81`), but only as a 14-day CI artifact, which needs a GitHub login and isn't signed with a Developer ID.
- **Next step:**
  1. Add a tag-triggered release workflow that builds, signs, notarizes and zips `Bloom.app` and attaches it to a draft GitHub Release.
  2. Draft a Homebrew cask, a small recipe file that lets people run `brew install --cask bloom`.
  3. Add a "Download" route to the README's Install section, keeping the build-from-source steps for contributors.
- **Who:** Agent can fix (workflow, cask draft, README), You do (publish the release)

Done:
- `common.dependency-audit`: Done. `Package.swift:4-15` has no `dependencies:` entry, and osv-scanner returned `ok`. Next step: none. Who: Agent can check.
- `common.secrets-in-repo`: Done. gitleaks returned `ok` across the files and history, and the app uses no keys or tokens. Next step: none. Who: Agent can check.
- `macos.usage-descriptions`: Done. The only protected resources the code uses are the Desktop, Documents and Downloads folders (`Sources/BloomCore/FolderAccess.swift`, used for AirDrop), and each has a plain-words reason in `Support/Info.plist` (`NSDesktopFolderUsageDescription`, `NSDocumentsFolderUsageDescription`, `NSDownloadsFolderUsageDescription`). Terminal opens through `NSWorkspace.open` (`Sources/Bloom/QuickActions.swift:58`), which isn't an Apple Event, so it needs no key. Next step: none. Who: Agent can check.

## Before you grow

### common.release-process: Missing
A written, repeatable release process means each version can be found, installed and rolled back.
- **Evidence:** `CONTRIBUTING.md:94` says to "Tag the merge commit `v0.x.y` and publish a GitHub release". But versions 0.3.0 (`b8b55f5`) and 0.4.0 (`64621e2`) were merged with no tag: `git for-each-ref refs/tags` is empty locally, and GitHub shows 0 tags and 0 releases.
- **Next step:** fold the signing, notarizing and upload steps into the written process in `CONTRIBUTING.md`. Then you tag `v0.4.0` and publish its release. I won't create a tag or release without an explicit yes.
- **Who:** Agent can fix (docs and workflow), You do (tag and publish)

### common.rollback-plan: Missing
When a release breaks something, a written rollback plan gets the last good version back in minutes instead of hours.
- **Evidence:** there's no `docs/runbooks/`; `docs/` holds only `images/`. Nothing describes going back to a previous version.
- **Next step:** write `docs/runbooks/rollback.md`. It would cover marking the bad GitHub Release as a pre-release, so "latest" points at the previous one, and reverting the cask version. It would also give users the fallback of downloading the previous release's zip, or `git checkout v<previous>` then `scripts/install.sh`.
- **Who:** Agent can fix

### macos.update-path: Missing
People need a way to get bug fixes and new versions without reinstalling by hand from source.
- **Evidence:** the documented update is `scripts/update.sh` (`README.md:70`), which runs `git pull --ff-only` and rebuilds (`scripts/update.sh:6-7`). That needs developer tools. No releases exist and there's no cask.
- **Next step:** once releases exist, document "download the newest release" and add the Homebrew cask so `brew upgrade --cask bloom` works. Bloom itself must never check for updates over the network (that would break the README.md:11 promise).
- **Who:** Agent can fix (cask draft, README), You do (publish releases)

### macos.min-os-tested: Partial
The oldest macOS you say you support should actually be tested, or people on it hit crashes you never see.
- **Evidence:** the stated minimum is macOS 13 (`Package.swift:6`, `Support/Info.plist` `LSMinimumSystemVersion` 13.0, `README.md:60`). But CI and the E2E (end-to-end) tests run only on `macos-15` and `macos-26` (`.github/workflows/ci.yml:28`, `.github/workflows/test-plan.yml:76-78`). The manual release check (`CONTRIBUTING.md:93`) doesn't name a macOS version.
- **Next step:** pick one of three.
  - Add the oldest macOS runner GitHub Actions still offers to the CI matrix. As far as I know, macOS 13 runners have been retired, so this would be macOS 14 at best; check GitHub's runner-images list.
  - Add "try it on a macOS 13 Mac or VM" to the release checklist.
  - Raise the stated minimum to what's tested.
- **Who:** You do (decide which), then Agent can fix

### common.logging: Partial
Logs are how you find out what went wrong after someone reports a problem.
- **Evidence:** Bloom uses `os.Logger` (`Sources/Bloom/DragLog.swift:6`) and keeps file names out (`privacy: .public` only on counts and states, e.g. `Sources/Bloom/RadialController.swift:93,200,204`). But when a drop fails, the error is shown and saved for Report a Problem (`Sources/Bloom/RadialController.swift:243-255`) and never written to the log. A failed Open at Login toggle is also swallowed silently (`Sources/Bloom/BloomApp.swift:58-60`).
- **Next step:** add `dragLog.error(...)` in both catch blocks, logging the petal and the error type but not the file path.
- **Who:** Agent can fix

### common.error-tracking: Partial
Error tracking tells you about failures people hit but never report.
- **Evidence:** a local, user-sent report already exists. After a failed drop, Report a Problem pre-fills a GitHub issue with the petal, file types and error, never names (`Sources/Bloom/RadialController.swift:244`, `Sources/BloomCore/IssueReport.swift`, tested in `Tests/BloomCoreTests/IssueReportTests.swift`). Crashes aren't covered: nothing in `Sources/` looks at macOS crash reports, so a crash leaves nothing for the next Report a Problem.
- **Next step (promise-safe only):** on the next launch after a crash, Report a Problem could tell the person where their crash report is, so they can attach it themselves. The path is `~/Library/Logs/DiagnosticReports/Bloom-*.ips`. Nothing is sent automatically. No hosted crash tracker.
- **Who:** Agent can fix

Done:
- `common.ci`: Done. `.github/workflows/ci.yml:51-55` builds with warnings as errors and runs `swift test` on pull requests and `main`, and recent runs are green.
- `common.unit-tests`: Done. 13 test files in `Tests/BloomCoreTests` run every petal on generated samples. `swift test` passed in CI on 64621e2 (not run on this Mac; see above).
- `common.smoke-tests`: Done. `.github/workflows/e2e.yml:59` runs `scripts/e2e.sh`, which launches the real app and drags files out of Finder (`Sources/BloomE2E/Journeys.swift:9` onward).
- `common.readme`: Done. It says what Bloom is (`README.md:5-11`), how to install it (`README.md:58-71`) and how to test it (`README.md:138`). Every script it names exists.
- `common.accessibility`: Done (from code). Reduce Motion is respected in the flower (`Sources/BloomCore/FlowerMotion.swift:106`, `Sources/Bloom/FlowerView.swift:49`), the menu bar icon (`Sources/Bloom/MenuBarIcon.swift:41`), the key hint (`Sources/Bloom/KeyHintPanel.swift:62`) and the guide (`Sources/Bloom/FieldGuidePanel.swift:583`). Controls have labels (`Sources/Bloom/BloomApp.swift:16`, `Sources/Bloom/FieldGuidePanel.swift:374,523`, `Sources/Bloom/FloatShelf.swift:70`). I couldn't hear how VoiceOver (macOS's screen reader) reads the flower without launching the app; see You do.

## Polish

### common.changelog: Missing
A changelog tells people what changed in each version, so updates don't surprise them.
- **Evidence:** there's no `CHANGELOG.md` and there are 0 GitHub releases, though the version went 0.3.0 → 0.4.0 (`b8b55f5`, `64621e2`).
- **Next step:** write `CHANGELOG.md` for 0.3.0 and 0.4.0 from the `feat`/`fix` commits, or rely on generated release notes once releases exist (`CONTRIBUTING.md:94` already plans this).
- **Who:** Agent can fix

### macos.app-icon: Missing
A real icon makes the app look finished in Finder, Applications, Login Items and the AirDrop sheet.
- **Evidence:** `Support/Info.plist` has no `CFBundleIconFile` or `CFBundleIconName`, and the built `build/Bloom.app/Contents` has no `Resources` folder. The menu bar icon is drawn in code (`Sources/Bloom/MenuBarIcon.swift`), but that isn't the app's icon.
- **Next step:** you provide a 1024×1024 image. I convert it to `Bloom.icns`, copy it into `Contents/Resources` in `scripts/bundle.sh`, and add `CFBundleIconFile` to `Info.plist`.
- **Who:** You do (the image), then Agent can fix

### common.regression-tests: Partial
A regression test (a test for each bug you fix) stops that bug from quietly coming back.
- **Evidence:** most behavior fixes add tests: `a5dcff5` (CompressionTests), `1284b5a` (FolderAccessTests) and `0f48a04` (an E2E journey). `a554c98` ("let a drop land when the flower started folding") changed only `Sources/Bloom/RadialController.swift`, with no test.
- **Next step:** add an E2E journey that drops just as the flower starts folding.
- **Who:** Agent can fix

### macos.store-listing: Partial
A product page with screenshots helps people decide to download.
- **Evidence:** the README is a good listing, with a description, a GIF and screenshots (`README.md:5-35`). But it has no download link, only `git clone` (`README.md:63`).
- **Next step:** add the download link once a release exists (same change as `macos.distribution`).
- **Who:** Agent can fix (after You do publishes a release)

Done:
- `common.license`: Done. The `LICENSE` file is MIT, and it matches `README.md:3,146` and `Support/Info.plist` `NSHumanReadableCopyright`.
- `common.support-channel`: Done. Report a Problem and Send Feedback are in the app menu (`Sources/Bloom/BloomApp.swift:63-64`, `README.md:127-129`), there are issue forms in `.github/ISSUE_TEMPLATE/`, and GitHub Issues are enabled.

## You do

1. **macos.developer-id-signing: get a Developer ID certificate.**
   1. Go to developer.apple.com/programs and enroll in the Apple Developer Program. It costs a yearly fee; enroll as Westfall Labs LLC if you want the company name on the signature, which needs a D-U-N-S number.
   2. Once you're approved, open Xcode → Settings → Accounts, select your team, click **Manage Certificates…**, click **+** and choose **Developer ID Application**.
   3. Open Keychain Access, find "Developer ID Application: …", right-click it → **Export**, and save it as a `.p12` file with a password.
   4. On GitHub, open s3anstanz/Bloom → Settings → Secrets and variables → Actions, and add the `.p12` (base64-encoded: `base64 -i cert.p12 | pbcopy`) and its password as repository secrets.
   5. How to tell it worked: `security find-identity -v -p codesigning` lists "Developer ID Application".
2. **macos.notarization: notarization credentials.**
   1. Sign in at appleid.apple.com → Sign-In and Security → App-Specific Passwords, and create one named "Bloom notarization".
   2. On your Mac, run `xcrun notarytool store-credentials bloom --apple-id <your Apple ID> --team-id <your Team ID>` and paste the password when asked. Your Team ID is under developer.apple.com → Account → Membership.
   3. Add the same three values as repository secrets for CI.
   4. How to tell it worked: `xcrun notarytool history --keychain-profile bloom` runs without an error.
3. **common.release-process / macos.distribution: publish the first release.**
   1. Once the release workflow exists, merge it.
   2. Run `git tag v0.4.0 && git push origin v0.4.0`.
   3. On GitHub, open Releases, open the draft release, read the notes and click **Publish release**.
   4. How to tell it worked: download the zip on a different Mac, double-click Bloom, and it opens with no "Apple could not verify" warning.
4. **macos.min-os-tested: pick how macOS 13 gets tested.** Choose one:
   - a CI runner,
   - a manual check on a macOS 13 Mac or VM before each release, or
   - raising the minimum to macOS 14 or 15.

   Tell me which and I'll make the change.
5. **macos.app-icon: provide an icon.** A 1024×1024 PNG with a transparent background. Save it anywhere in the repo, e.g. `Support/AppIcon.png`.
6. **common.accessibility: one VoiceOver pass.**
   1. Turn on VoiceOver with Cmd+F5.
   2. Open Bloom's menu from the menu bar, then open What Can Bloom Do? and move through it with Control+Option+Arrow keys.
   3. Note anything VoiceOver doesn't read or you can't reach.
   4. Turn VoiceOver off with Cmd+F5.

<details>
<summary>Not applicable (3)</summary>

- `common.leaked-key-rotation`: no secret was found (gitleaks `ok`), so there's nothing to rotate.
- `common.analytics`: promise: "It has no network code, no analytics and no third-party dependencies" (README.md:142).
- `common.multi-device-testing`: app-type: desktop-only macOS app; `macos.min-os-tested` covers OS versions instead.

</details>
