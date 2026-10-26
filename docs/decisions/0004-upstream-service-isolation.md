# 0004. Detach from Zen-operated services; no update channel yet

Status: accepted · Date: 2026-10-26

## Context

A stock Zen build contacts services run by the Zen project: the update server, a share service, a
mods marketplace and store, welcome and release pages, donation pages. `surfer` also writes these
URLs into generated files (`firefox-branding.js`, installer scripts). Nivora is a different
product, with different users, binaries and privacy commitments. Principle D forbids undocumented
data transfer to third parties.

The most serious item is updates: a Nivora build configured with Zen's update host would be offered
Zen's binaries, replacing Nivora with Zen.

## Decision

1. Remove `updateHostname` from `surfer.json`. Surfer then exports a non-resolving placeholder as
   `MOZ_APPUPDATE_HOST`. Also set `app.update.auto=false`.
2. Empty `zen.share.base-url`; restrict `zen.injections.match-urls` to `about:preferences`; turn off
   `zen.mods.auto-update` and the update/donate sidebar notification.
3. Override the URLs surfer writes into `firefox-branding.js` with preferences in
   `prefs/nivora/endpoints.yaml`. This relies on `zen.js` being loaded after `firefox-branding.js`
   (it is `#include`d at the end of `firefox.js`); **to be confirmed in a running build** (test F-07).
4. Remove Zen's CI workflows, funding manifest and code owners from the repository.
5. Add tests that fail if a preference default points at a Zen host.
6. Record every remaining reference in [SECURITY.md](../SECURITY.md) section 4.

## Alternatives

- Patch `node_modules/@zen-browser/surfer` or fork it: another dependency to maintain; the
  preferences achieve the same effect for what runs on Linux.
- Run our own update server now: infrastructure, signing keys and operations that the project does
  not have and the specification says not to invent (section 33).
- Leave Zen's defaults and document them: contradicts the privacy principle.

## Consequences

- **No automatic updates.** Security fixes depend on rebuilding and redistributing. Unacceptable
  for a stable release; decided in Phase III.
- Share and marketplace UI entry points remain visible and do nothing useful. Hiding them is
  tracked in the roadmap.
- Packaging should ship `distribution/policies.json` with `DisableAppUpdate: true`, as Zen's AppImage
  skeleton (`build/AppDir/distribution/policies.json`) already does, until an update service exists.
- A future Nivora update service needs: signing keys, a host in `surfer.json`, `app.update.auto`
  reconsidered, and a threat model.
