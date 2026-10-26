# Roadmap

This file reflects the real state of the work. A box is checked only when the item was done **and
verified**, and the verification is named. "Implemented" without verification is written as such.

Legend: `[x]` done and verified · `[~]` implemented, not yet verified · `[ ]` not started ·
`[!]` blocked

## Phase I: Foundation

### Repository and upstream

- [x] Upstream base chosen and recorded: Zen `1.23.4b` (`541ee55`) on Firefox 158.0.1
      ([ADR 0002](decisions/0002-upstream-base.md)). Verified by applying all 263 patches to a
      real Firefox 158.0.1 checkout.
- [x] Upstream imported as an unmodified root commit; tree hash identical to the upstream tag.
- [x] Zen's CI, funding manifest, code owners and issue labeler removed (they would run Zen's
      release pipeline or notify Zen maintainers from this repository).
- [x] Upstream services neutralised in configuration (update host, share, mods injection,
      branding URLs, update notification). Verified in generated `zen.js` and `mozconfig`;
      [~] runtime behaviour needs the built browser ([TESTING.md](TESTING.md)).
- [x] Application identity set: name, binary `nivora`, vendor, distribution id
      ([ADR 0005](decisions/0005-application-identity.md)).

### Build

- [x] Environment requirements established for a source-restricted container
      ([BUILDING.md](BUILDING.md)): clang 19, cbindgen, GTK dev packages, Firefox via the GitHub mirror.
- [x] `surfer import` succeeds (273 steps, 0 failures) with Nivora's changes.
- [~] Baseline build: running. Result recorded in [BUILDING.md](BUILDING.md) when it finishes.
- [ ] Start the browser, load a page, open/close tabs, back/forward (acceptance criteria below).
- [ ] Release configuration (LTO/PGO, `ZEN_RELEASE`) built and measured.

### Identity (Obsidian Eclipse)

- [x] Palette, semantic roles and contrast policy; 24/24 pairs pass; negative case proven
      (`#777777` fails) ([DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)).
- [x] Tokens wired into Zen's theme through the real Gecko preprocessor (output inspected).
- [~] Dark mapping applied to the window, panels and in-content pages: needs a rendered check.
- [ ] Tabs: active / inactive / pinned / audio / loading / warning states, not color-only.
- [ ] Address bar hierarchy with all security indicators preserved.
- [ ] Menus, context menus, dialogs, downloads panel, notifications, empty states.
- [ ] New tab page (no remote content by default).
- [ ] Preferences pages.
- [ ] Typography decision, icon set audit.
- [~] Original logo and icons: proposal generated and tested (18 unit tests); needs the owner's approval; not yet seen in a build.
- [ ] Reduced-motion handling for Nivora's own animations.
- [ ] Narrow-window and high-DPI checks.

### Foundation acceptance (from the specification, section 10)

| Criterion | State |
|---|---|
| Builds with the documented procedure | `[~]` in progress |
| Starts, opens a page, tabs, back/forward, address bar, renders normal pages | `[ ]` |
| Essential security controls still present | `[ ]` (inherited; confirm in the build) |
| Settings persist across restart | `[ ]` |
| Identity applied coherently | `[ ]` (tokens only so far) |
| No essential Zen function removed without justification | `[x]` nothing removed; two prefs changed to disable Zen-operated services |
| Modifications documented | `[x]` [UPSTREAM.md](UPSTREAM.md) |
| Available tests run, unrun ones recorded | `[~]` [TESTING.md](TESTING.md) |
| Reproducible reference build | `[ ]` |

Foundation is **not complete**. Productivity does not start until it is.

## Phase II: Productivity (not started)

Principle: Zen already ships spaces, folders, split view, glance, compact mode, a library, live
folders, space routing and an address-bar actions provider. Each item starts by deciding whether
configuring or restyling what exists is enough.

- [ ] Spaces: audit Zen's implementation against the requirements (create, rename, icon, order,
      switch, close, recover, startup behaviour, persistence); document that spaces are not a
      security boundary (shared cookies and storage), and point to containers when isolation is needed.
- [ ] Tab management: search (title, URL, space, state), duplicates, inactive tabs, restoration
      through Firefox session store. No automatic closing or discarding.
- [ ] Command palette: extend `ZenUBGlobalActions` with a central command registry (stable ids,
      availability conditions, shortcuts, error handling). Allow-list only; no arbitrary code.
- [ ] Central settings: validated, versioned export/import without secrets; reset to defaults;
      a corrupt file never blocks startup.
- [ ] Profiles and sessions: use Firefox's own mechanisms.
- [ ] Linux integration: feature-detected, optional; Ryoku-specific parts strictly optional.
- [ ] Privacy surface: clearer wording over Firefox's controls; no home-made blocker.
- [ ] Optional AI module: out of the critical path; off by default.

## Phase III: Stable (not started)

- [ ] Upstream update procedure and CI levels ([UPSTREAM.md](UPSTREAM.md) has the design).
- [ ] Regression suite: Zen's mochitests that matter, plus Nivora's.
- [ ] Performance baselines against an equivalent Zen build.
- [ ] Security review of Nivora's changes; dependency and license audit.
- [ ] Distribution: one initial format for Arch Linux, chosen and justified; update path defined.
- [ ] Original identity assets, `.desktop` file, MIME types, metadata.
- [ ] Final report separating verified from unverified.
