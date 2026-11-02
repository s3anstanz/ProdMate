# macOS app checklist

Loaded when detect.py finds a `macos-app`. The codesign audit needs a built `.app`; ask before building it. When there's no built app and the user declines a build, signing and notarization are Can't verify.

## Contents

- Launch blockers: macos.developer-id-signing, macos.notarization, macos.distribution, macos.usage-descriptions
- Before you grow: macos.update-path, macos.min-os-tested
- Polish: macos.app-icon, macos.store-listing

## Launch blockers

### macos.developer-id-signing
- tier: blocker
- why: macOS blocks apps that aren't signed with an Apple Developer ID, so anyone else who downloads yours sees a warning or can't open it.
- applies-when: the app is meant for people other than its author and is distributed outside the Mac App Store
- check: Run the codesign audit on the built .app. Done when codesign shows "Authority=Developer ID Application". Missing when the signature is ad-hoc ("Signature=adhoc") or absent; also check the build or release script for a codesign --sign step (cite file:line). Without a built app, the scripts decide: Missing when the build and release scripts sign only ad-hoc (codesign --sign -) or not at all; Can't verify only when a script has a Developer ID signing step but there's no built app to confirm it.
- agent-fix: add a Developer ID signing step (codesign --sign "Developer ID Application: ..." --options runtime) to the release script or workflow, reading the identity from a secret
- audit: codesign
- you-do: 1) Join the Apple Developer Program at developer.apple.com (it costs money each year). 2) In Xcode > Settings > Accounts, create a "Developer ID Application" certificate. 3) For CI, export it as a .p12 and add it and its password as repository secrets.

### macos.notarization
- tier: blocker
- why: Apple must scan and approve (notarize) a downloaded app, or macOS refuses to open it for most people.
- applies-when: the app is distributed outside the Mac App Store
- check: Run the codesign audit. Done when spctl says "accepted" with "source=Notarized Developer ID". Missing when spctl rejects it, or when the release script has no notarytool submit and stapler staple step. Without a built app, the scripts decide: Missing when no script or workflow has a notarytool submit step; Can't verify only when one exists but there's no built app to confirm it.
- agent-fix: add xcrun notarytool submit --wait and xcrun stapler staple steps to the release script, reading credentials from a keychain profile or secrets
- audit: codesign
- you-do: create an app-specific password at appleid.apple.com, then run `xcrun notarytool store-credentials` once on your Mac (or add the values as CI secrets)

### macos.distribution
- tier: blocker
- why: People who don't use developer tools need a normal way to download and install the app.
- applies-when: the app is meant for people other than its author
- check: Done when a non-developer can install it without building from source: a signed .dmg or .zip on a GitHub Release or website, a Homebrew cask, or the Mac App Store (cite the release, cask or listing). Missing when the only install path builds from source or runs a script that needs developer tools.
- agent-fix: add a release step that builds, signs and packages the app as a .dmg or .zip and attaches it to a GitHub Release (created only after an explicit yes); draft a Homebrew cask file
- audit: none
- you-do: approve and publish the first release; submit the cask to homebrew-cask if you want `brew install --cask`

### macos.usage-descriptions
- tier: blocker
- why: macOS stops an app that uses a protected resource (camera, microphone, folders, contacts and so on) without explaining why in its Info.plist.
- applies-when: always for macOS apps
- check: List the protected APIs the code uses (camera, microphone, Desktop, Documents and Downloads folders, contacts, calendars, location, Apple Events, Bluetooth). Done when each has a matching NS*UsageDescription key in Info.plist with a plain-words reason (cite the key and the code that needs it). Missing when any is absent.
- agent-fix: add the missing NS*UsageDescription keys with a one-sentence reason each
- audit: none
- you-do: none

## Before you grow

### macos.update-path
- tier: grow
- why: People need a way to get bug fixes and new versions without reinstalling by hand from source.
- applies-when: the app is meant for people other than its author
- check: Done when a documented update path exists that a non-developer can use: a GitHub Release feed with downloadable builds, a Homebrew cask (brew upgrade), the Mac App Store, or an in-app updater. Missing when there's none. An update path that needs developer tools (git pull and rebuild, or re-running a build-from-source script) is still Missing for an app meant for other people; cite it as evidence, not as Partial.
- agent-fix: offer network-free paths first: a signed and notarized GitHub Release download with release notes, and a Homebrew cask so `brew upgrade` works; the app itself never phones home. An in-app auto-updater (e.g. Sparkle) contacts the network to check for updates, so it conflicts with a no-network promise; only suggest one when the app makes no such promise.
- audit: none
- you-do: publish each new version as a GitHub Release and bump the cask version

### macos.min-os-tested
- tier: grow
- why: The oldest macOS version you say you support should actually be tested, or users on it hit crashes you never see.
- applies-when: always for macOS apps
- check: Find the deployment target (Package.swift platforms .macOS(.vXX), or MACOSX_DEPLOYMENT_TARGET in project.pbxproj) and what the README states. Done when CI or documented manual testing covers that version (cite the CI runner list). Partial when only newer versions are tested.
- agent-fix: add the oldest macOS runner GitHub Actions offers to the CI matrix, or raise the stated minimum to match what's tested (ask which)
- audit: none
- you-do: none

## Polish

### macos.app-icon
- tier: polish
- why: A real icon makes the app look finished in Finder, Launchpad and the Dock.
- applies-when: always for macOS apps
- check: Done when an AppIcon asset catalog or .icns file is in the bundle and CFBundleIconFile or CFBundleIconName names it. Missing otherwise.
- agent-fix: wire an existing icon into the bundle; designing one needs the user
- audit: none
- you-do: provide a 1024x1024 icon image if there isn't one

### macos.store-listing
- tier: polish
- why: A product page or store listing with screenshots helps people decide to download.
- applies-when: the app is meant for people other than its author
- check: Done when there's a Mac App Store listing, or a website or README section with a description, screenshots and a download link. Partial when there's a description but no download link.
- agent-fix: draft the listing text and screenshot captions from the README
- audit: none
- you-do: take the screenshots and publish the listing
