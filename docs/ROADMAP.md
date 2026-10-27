# Roadmap

This file reflects the real state of the work. A box is checked only when the item was done **and
verified**, and the verification is named. "Implemented" without verification is written as such.

Legend: `[x]` done and verified · `[~]` implemented, not yet verified at run time · `[ ]` not started ·
`[!]` blocked or decided against, with the reason

The maintainer accepted all open proposals on 2026-10-26 (logo proposal, MPL-2.0 for new files,
Zen `stable` as the base, the Firefox-security-release policy in [MAINTENANCE.md](MAINTENANCE.md),
hiding Zen-service interface, tarball + PKGBUILD as the first distribution format) and asked for the
rest to be completed without further questions.

## Phase I: Foundation

### Repository and upstream

- [x] Upstream base: Zen `1.23.4b` (`541ee55`) on Firefox 158.0.1 ([ADR 0002](decisions/0002-upstream-base.md)). Verified by applying all 263 patches to a real Firefox 158.0.1 checkout.
- [x] Upstream imported as an unmodified first commit; `upstream_check.py --verify-root` proves its tree equals the Zen tag's, and that the Zen and Firefox tags still point at the pinned commits.
- [x] Zen's CI, funding manifest, code owner and issue labeler removed.
- [x] Zen-operated services neutralised in configuration (update host, share, mods injection, branding URLs, update notification) and guarded by a test.
- [x] The same, observed at run time: defaults read from the built browser (`browser_nivora_defaults.js`); host-name audit of a first start shows no Zen host (`net_audit.py`, limits in [TESTING.md](TESTING.md)). Finding: the branding file overrode the defaults until `post_import.py`.
- [x] Application identity ([ADR 0005](decisions/0005-application-identity.md)).
- [x] **Profile directory:** Zen's patch would have made Nivora use `~/.zen`; fixed (2 lines in `src/toolkit/moz-configure.patch`). Verified at run time (F-10): `~/.config/nivora` only.

### Build

- [x] Requirements for a source-restricted container ([BUILDING.md](BUILDING.md)).
- [x] `surfer import` succeeds (0 failures) with Nivora's changes.
- [x] Baseline build: completes, exit 0, 76 min on 4 cores ([BUILDING.md](BUILDING.md)); repeated after a clean re-import.
- [~] Browser starts and loads a page (`smoke.py`), and Nivora's and a subset of Zen's tab, space and urlbar tests pass. Back/forward, a PDF, media and a manual pass through F-03..F-08 are not done.
- [ ] Release configuration (LTO/PGO, `ZEN_RELEASE`) built and measured.

### Identity (Obsidian Eclipse)

- [x] Palette, roles, contrast policy; 24/24 pairs pass; negative case proven.
- [x] Tokens wired into Zen's theme; Gecko's preprocessor output inspected.
- [x] Dark mapping rendered and reviewed in screenshots: window, sidebar, address bar, command palette, settings, blank page.
- [x] Original icon set licensing fixed: Zen's 154 Nucleo icons (not redistributable) replaced by Phosphor (MIT); 7 tests; reviewed as rendered contact sheets. Seen in the command palette and settings.
- [x] Application logo and icons: generated mark, accepted by the maintainer; 7 tests. Wordmarks are text placeholders.
- [ ] Tabs: state indicators not conveyed by color alone (needs the UI to be inspected).
- [ ] Address bar hierarchy, menus, dialogs, downloads panel, new tab page, preferences panes.
- [ ] Typography decision.
- [ ] Reduced-motion handling of Nivora's own animations (it has none yet).
- [ ] Narrow-window and high-DPI checks.

### Foundation acceptance (specification section 10)

| Criterion | State |
|---|---|
| Builds with the documented procedure | `[x]` clean import, then full build, exit 0 |
| Starts, opens a page, tabs, back/forward, address bar, renders normal pages | `[ ]` |
| Essential security controls still present | `[ ]` |
| Settings persist across restart | `[ ]` |
| Identity applied coherently | `[~]` palette, icons, logo and main artwork seen rendered; tab states, menus, downloads panel, typography, new tab page unreviewed |
| No essential Zen function removed without justification | `[x]` nothing removed except Zen-service UI, hidden by preference |
| Modifications documented | `[x]` [UPSTREAM.md](UPSTREAM.md) |
| Available tests run, unrun ones recorded | `[x]` [TESTING.md](TESTING.md) |
| Reproducible reference build | `[ ]` |

## Phase II: Productivity

Principle: Zen already ships spaces, folders, split view, glance, compact mode, a library, live
folders, space routing and an address-bar actions provider. Nivora extends them; see
[PRODUCTIVITY.md](PRODUCTIVITY.md) for what Zen already covers, per area.

- [x] Command registry with stable ids, checked specs, argument validation, error containment, confirmation for sensitive commands; 31 Node tests + mutation checks. Browser integration test passes.
- [x] Eight commands added to Zen's palette (new tab, history, downloads, search open tabs, close duplicate tabs, export / import / reset settings). Seen in the palette (screenshot); Zen's `browser_ub_actions_search.js`, which iterates every action, passes.
- [x] Central settings: 25 whitelisted preferences, versioned export, validated all-or-nothing import, reset, startup repair. Node tests incl. hostile input. Browser test passes.
- [x] Duplicate tabs: detection never crosses spaces, containers, pinned or essential tabs; closing needs confirmation. Node tests. Browser test passes.
- [x] Spaces: audited against the requirements ([PRODUCTIVITY.md](PRODUCTIVITY.md) section 3). Met by Zen except recovery of a deleted space [!] left out: it needs a change to `ZenSpaceManager.mjs` (privileged, ~3,700 lines).
- [x] Zen-service UI: share hides itself without a service; donate button and mods link hidden by preference. Verified in the built browser: the Library donate button and the Mods website link are hidden by default and shown when the preference is off (`browser_nivora_ui.js`).
- [x] Profiles, privacy, Linux integration: audited and documented ([PRIVACY.md](PRIVACY.md), [LINUX.md](LINUX.md)); no new code was needed. Ryoku-specific code: none, by design.
- [!] Optional AI module: not implemented, by design ([PRODUCTIVITY.md](PRODUCTIVITY.md) section 8).
- [ ] A settings page in `about:preferences` and a user-assignable shortcut for Nivora commands (not done; judged not worth the upgrade cost yet).
- [ ] Inactive-tab detection and memory indicators (need measured data).

## Phase III: Stable

- [x] Update procedure and `tools/nivora/upstream_check.py` with a weekly read-only workflow; run live.
- [x] CI: static checks on every push (palette, icons, Python and Node tests, `ffprefs`); upstream check weekly. A full browser build per push is deliberately not run.
- [x] License inventory with the real texts; Nucleo icons removed from the tree ([LICENSES.md](LICENSES.md)). [ ] Items marked "review" in LICENSES.md need a human decision (Motion notice, Junicode, emoji data, site logos, welcome/Library artwork).
- [x] Security review of Nivora's changes; five findings fixed (profile directory, container-crossing close, size check, branding prefs override, stale branding in the build) ([SECURITY_REVIEW.md](SECURITY_REVIEW.md)). Independent review: [ ] not done.
- [x] Distribution: tarball + Arch `PKGBUILD`, `.desktop`, AppStream, update-disabling policy; 11 tests simulating `makepkg`; produced from the real build and its policy verified in the running browser. [ ] Not installed on Arch.
- [x] Maintenance and recovery documented ([MAINTENANCE.md](MAINTENANCE.md)).
- [~] Regression suite: Nivora's 120 checks and 760 checks of 7 of Zen's 26 groups pass, 0 fail; the other 19 groups and an unmodified-Zen baseline were not run.
- [~] Performance baseline measured for startup, memory and idle CPU (one tab, dev build); many-tab and UI-latency measurements and a Zen comparison not done.
- [ ] An update channel (none exists by decision; packages are the channel).
- [ ] Final report separating verified from unverified.
