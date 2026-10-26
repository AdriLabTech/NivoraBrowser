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

- **Verified:** `surfer import` succeeds (273 steps, 0 failures) — also for the unmodified upstream.
- **Verified:** `mach configure` passes with clang 19 and the options in BUILDING.md.
- **In progress at time of writing:** the compile (`mach build -j4`). The outcome, duration and
  disk/RAM figures are recorded in BUILDING.md section 5 when it completes. Until then this report
  makes no claim that Nivora compiles, starts or browses.
- Pre-existing problems found before any Nivora change (not attributable to Nivora): the
  `stdc++compat` shim does not compile on GCC 13; `dev` and `stable` are tied to different Firefox
  versions; `surfer` hardcodes Zen URLs; `ffprefs` mishandled digit-only hex values.

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

Status as of this report. Order follows dependency, then impact.

| # | Task | State |
|---|---|---|
| 1 | Import base, record provenance | done, verified |
| 2 | Identity and service detachment (config level) | done; runtime check pending |
| 3 | Tokens, contrast policy, wiring | done; render check pending |
| 4 | Documentation set and decisions | done (this set) |
| 5 | **Baseline build and first launch** | in progress |
| 6 | Verify config-level changes at runtime (F-07, F-09 in TESTING.md) | blocked on 5 |
| 7 | Screenshot review of the dark mapping; fix the mapping | blocked on 5 |
| 8 | Tabs: states not conveyed by color alone | blocked on 7 |
| 9 | Address bar, menus, dialogs, downloads panel restyle | blocked on 7 |
| 10 | New tab page, preferences panes | blocked on 7 |
| 11 | Original logo, icons, remove Zen's | done as a proposal (all Zen icons replaced); needs the owner's approval |
| 12 | Typography and icon decisions | blocked on 7 |
| 13 | Zen baseline run of the mochitest suite, then Nivora's; compare | blocked on 5 |
| 14 | Foundation acceptance check and phase report | after 5–13 |

## 10. Tests needed

[TESTING.md](TESTING.md): static checks (running), manual Foundation and identity procedures
(written, not yet run), Zen's mochitests (not run), a network audit (F-09, not run), performance
baselines (not started).

## 11. Decisions pending for the owner

1. **Logo and application icon.** A proposal exists (eclipse crescent in a ring, generated from the
   palette). Approve it, or give a direction for another. It is generic enough to resemble many
   crescent icons.
2. **License for entirely new Nivora files.** Currently MPL-2.0 headers, which is the safe default
   next to MPL code; the choice is yours.
3. **Base line.** Confirm Zen `stable`/1.23.4b (recommended, ADR 0002) rather than `dev`.
4. **Policy for Firefox security releases that Zen has not yet shipped:** wait for Zen, or maintain
   a re-based patch set. (Needed before the Stable phase.)
5. **Hide Zen-service UI** (share, marketplace link, donate button, About links) now, or leave until
   the Productivity UI pass.
6. **Repository settings:** enable GitHub private vulnerability reporting (the root `SECURITY.md`
   points to it); decide a code owner for `CODEOWNERS` (removed because it named a Zen maintainer).
7. **Distribution name identifiers** (`io.github.adrilabtech.nivora`): keep, or give a domain.
8. **Packaging format for Arch / Ryoku Arch** (Stable phase): source `PKGBUILD`, binary package, or
   portable tarball.

## 12. Blockers needing intervention

None that stop progress. Two would improve it: allowing `archive.mozilla.org` and Mozilla's CI
artifact host through the network policy would make the stock `npm run init` / `bootstrap` route
work and give release-equivalent toolchains for performance work; and a persistent machine would
avoid rebuilding after the container is reclaimed.
