# Foundation: analysis and preparation report

Date: 2026-10-26 · Scope: specification section 35 (first task). Nothing from the Productivity or
Stable phases is implemented. Every statement is tagged **verified** (executed, with the command
or evidence named) or **unverified**.

## 1. Repository state

- The target repository (`AdriLabTech/nivoraBrowser`) was empty: no commits, no files, no remote
  refs. Nothing existed to preserve or overwrite.
- It now contains: the unmodified Zen `1.23.4b` tree as the first commit, followed by Nivora
  commits ([UPSTREAM.md](UPSTREAM.md) lists every difference).
- Working branch: `ccr-182bc877-hru910`. No pull request has been opened.
- One process slip, disclosed: while importing the Zen tree I copied Zen's `.git` directory over the
  empty repository's `.git`. The repository had no commits, so no work was lost; I restored the
  same remote (`origin`) and branch name and verified both. The repository's original
  `.git/config` could not be compared byte for byte.

## 2. Architecture identified

Summary (details and component map in [ARCHITECTURE.md](ARCHITECTURE.md)):

- Zen is not a Firefox fork. It is **263 patches** plus a tree of new files (`src/zen/**`) that
  `surfer` applies onto a Firefox source checkout (`engine/`).
- Preferences are YAML compiled by a Rust tool (`ffprefs`) into the engine.
- Theming is CSS custom properties derived from one accent color, assembled by Gecko's
  preprocessor, delivered to every chrome page through a patched design-system token file.
- Zen **already contains** workspaces ("spaces"), folders, split view, glance, compact mode, a
  library, live folders, space routing, a mods system and an address-bar actions provider that is
  a command palette in all but name.
- 530 mochitests in 26 groups ship with it.

Where the requested elements are implemented (section 35 item 10):

| Element | Implementation |
|---|---|
| Address bar | Firefox urlbar + 12 patches + `src/zen/urlbar/*` providers (`ZenUBGlobalActions`, `ZenUBActionsProvider`, ...) + `zen-omnibox.css` |
| Tabs | Vertical tabs: patches to `Tabbrowser`, `tab`, `tabs`, `tabgroup`, drag-and-drop; `src/zen/tabs/**`, `zen-tabs.css`, `zen-tabs/vertical-tabs*.css` |
| Panels / sidebar | `navigator-toolbox-inc-xhtml.patch` reshapes the window; `zen-sidebar.css`; `zen-panel-ui.css`; `zen-panels/` |
| Menus | `ZenMenubar.mjs`, patches to `nsContextMenu` and the tab context menu, `zen-popup.css` |
| Preferences | Firefox preferences patched; Zen panes in `src/browser/components/preferences/zen*.inc.xhtml` |
| Dialogs | `zen-panels/dialog.css`, per-feature `.inc.xhtml` windows |
| Spaces | `src/zen/spaces/**`, `src/zen/sessionstore/**`, `src/zen/sync/**` |
| Compact mode | `src/zen/compact-mode/**` (JS + C++ mouse tracker) |

## 3. Technologies and versions (verified)

| | Version | Source |
|---|---|---|
| Zen | 1.23.4b, `541ee55` | git tag, `surfer.json` |
| Firefox | 158.0.1, `9378fbc` | tag `FIREFOX_158_0_1_RELEASE`, `browser/config/version.txt` |
| surfer | 1.14.9 | `package-lock.json` |
| Node / Python / Rust (repo pins) | 22 / 3.11 / 1.95.0 | `.nvmrc`, `.python-version`, `rust-toolchain.toml` |
| Used in the reference environment | Node 22.22, Python 3.13.17, rustc 1.95.0 (pinned) and 1.97, clang 19.1.1 | executed |
| Languages in the tree | JavaScript (ES modules), CSS, XHTML/XUL, Fluent (`.ftl`), C++/IDL (small), Rust (`ffprefs`), YAML, Python | read |

## 4. Build procedure

Official route: `npm ci`, `npm run init` (download Firefox, import, bootstrap), `npm run build`,
`npm start`. The route actually executed, with the reasons for each deviation, is in
[BUILDING.md](BUILDING.md). The deviations come from the environment (blocked
`archive.mozilla.org` and Mozilla CI), not from the project.

## 5. Result of the initial build

- **Verified:** `surfer import` succeeds (273 steps, 0 failures) on unmodified upstream; with Nivora's
  changes, 264 git patches (Zen's 263 and Nivora's one) apply, from a clean engine, twice.
- **Verified:** `mach configure` passes with clang 19 and the options in BUILDING.md.
- **Verified:** the compile completes (`mach build`, exit 0; about 76-79 minutes on four cores, a 4.7 GB
  object directory), and `mach package` makes a 97 MB tarball ([BUILDING.md](BUILDING.md) section 5).
- **Verified:** the browser starts, opens a window, loads a local page, uses `~/.config/nivora`, and
  resolves no Zen-operated host on a first start ([TESTING.md](TESTING.md) section 2.2).
- Pre-existing problems found before any Nivora change (not attributable to Nivora): the
  `stdc++compat` shim does not compile on GCC 13; `dev` and `stable` are tied to different Firefox
  versions; `surfer` hardcodes Zen URLs; `ffprefs` mishandled digit-only hex values.
- Problems found by running the build, which a build alone does not show: the branding file
  overrode Nivora's endpoint defaults; `.ftl` files were not packaged without an extra step; Firefox's
  logo, its mascot and Zen's screenshots were still shown in settings; pages without a background
  were violet-tinted. All fixed and covered by tests ([SECURITY_REVIEW.md](SECURITY_REVIEW.md), findings 7 and 8).

## 6. Customization points

Safest first: preferences (`prefs/`), Zen theme variables, new files under `src/nivora/`, user
mods. See ARCHITECTURE.md section 2.3 for the ranking and 2.4 for the impact class of each
planned change.

## 7. Technical risks

1. **Firefox security currency.** Zen's patches are bound to an exact Firefox. Nivora gets Firefox
   fixes when Zen releases, or by re-basing 263 patches itself. High.
2. **No update channel.** Removed deliberately (Zen's would replace Nivora). Medium now, high at release.
3. **Build resources.** ~30 GB disk, hours of CPU. A full build per CI event is not viable.
4. **Visual result unproven.** The dark mapping rests on Zen's `color-mix()` chains; no render yet.
5. **Hidden Zen coupling.** Names, links, binary name assumptions inside 263 patches and `src/zen`.
6. **Third-party assets of unknown license** inherited from Zen (UPSTREAM.md section 3).
7. **Environment-specific toolchain** (distribution clang, no PGO, no wasm sandbox) differs from
   release builds. Not representative for performance numbers.

## 8. Proposed architecture

Implemented as described in ARCHITECTURE.md section 2: new code in `src/nivora/`, prefs in
`prefs/nivora/`, tooling in `tools/nivora/`, and a short, listed set of hooks into Zen files.
Productivity features extend Zen's existing managers and the existing actions provider rather than
re-implementing them.

## 9. Foundation plan

State at the end of the Foundation work. Order follows dependency, then impact.

| # | Task | State |
|---|---|---|
| 1 | Import base, record provenance | done, verified |
| 2 | Identity and service detachment | done; checked at run time (defaults, host-name audit, profile directory) |
| 3 | Tokens, contrast policy, wiring | done; seen rendered |
| 4 | Documentation set and decisions | done |
| 5 | Baseline build and first launch | done |
| 6 | Verify config-level changes at runtime (F-07, F-09, F-10, F-11 default) | done, with the limits recorded in TESTING.md |
| 7 | Screenshot review of the dark mapping; fix the mapping | done for window, sidebar, address bar, palette, settings, blank page; fixes made (in-content pages, canvas) |
| 8 | Tabs: states not conveyed by color alone | **open** (needs the tab states to be inspected) |
| 9 | Address bar, menus, dialogs, downloads panel restyle | **open** beyond the token mapping |
| 10 | New tab page, preferences panes | partly: settings recolored; new tab is Zen's, unreviewed |
| 11 | Original logo, icons, remove Zen's and Mozilla's | done, accepted by the owner; 12 Mozilla artwork files and Zen's layout screenshots replaced; a few rarely shown mascot files remain (UPSTREAM.md) |
| 12 | Typography and icon decisions | icons done (Phosphor); typography **open** |
| 13 | Zen baseline run of the mochitest suite, then Nivora's; compare | Nivora's run (123 checks pass); all 26 Zen groups run (26,288 browser checks pass, 31 fail, none traced to Nivora); **no unmodified-Zen baseline** |
| 14 | Foundation acceptance check and phase report | this document and [ROADMAP.md](ROADMAP.md) |

## 10. Tests needed

[TESTING.md](TESTING.md) has the results. Still needed: an unmodified-Zen
baseline, a manual pass through F-03..F-08 and the identity table, a packet capture over time, an
independent security review and performance measurements against a release-like build.

## 11. Decisions

All proposals in the first version of this report were accepted by the owner on 2026-10-26, who
asked for the remaining work to be done without further questions. How each was settled:

| Decision | Outcome |
|---|---|
| Logo and application icon | The generated eclipse mark is accepted as the logo |
| License of new files | MPL-2.0 (the header they already carry) |
| Base line | Zen `stable` 1.23.4b on Firefox 158.0.1 ([ADR 0002](decisions/0002-upstream-base.md)) |
| Firefox security releases ahead of Zen | Wait for Zen by default; rebase the patches only for a critical, exploited vulnerability; warn users otherwise ([MAINTENANCE.md](MAINTENANCE.md)) |
| Hide Zen-service interface | Done: share (until a share service is configured), donate button and mods link; About-dialog links to Zen and Firefox stay, as attribution |
| Private vulnerability reporting, code owner | **Needs the owner**: a repository setting that cannot be changed from here. `SECURITY.md` points to it; no `CODEOWNERS` exists (Zen's entry named a Zen maintainer) |
| Distribution identifiers | `io.github.adrilabtech.nivora` kept |
| Packaging for Arch / Ryoku Arch | Tarball + binary `PKGBUILD` ([DISTRIBUTION.md](DISTRIBUTION.md)) |

## 12. Blockers needing intervention

None that stop progress (see the list of human-only items in [ROADMAP.md](ROADMAP.md)). Two would improve it: allowing `archive.mozilla.org` and Mozilla's CI
artifact host through the network policy would make the stock `npm run init` / `bootstrap` route
work and give release-equivalent toolchains for performance work; and a persistent machine would
avoid rebuilding after the container is reclaimed.
