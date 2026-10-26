# Architecture

This document describes the architecture Nivora inherits, the layer Nivora adds, and where the two
meet. Everything about the inherited side was read from the actual tree (Zen `1.23.4b`, commit
`541ee55`, on Firefox `158.0.1`) and, where marked **verified**, exercised in a real build
environment. It is updated when the architecture changes.

## 1. Inherited architecture

### 1.1 Three source trees

```
Firefox source (engine/)         Zen repository (this repo, src/ prefs/ configs/)        Nivora additions
mozilla-firefox/firefox          zen-browser/desktop                                       src/nivora, prefs/nivora, tools/nivora
tag FIREFOX_158_0_1_RELEASE      tag 1.23.4b
```

Zen does not fork Firefox. It keeps the Firefox source out of its repository and describes its
changes in two forms under `src/`, which mirrors the Firefox tree layout:

1. **Patches.** `src/<path>/<file>-<ext>.patch` is a `git` patch against `<path>/<file>.<ext>` in
   Firefox. There are **263**. They are applied with `git apply --ignore-space-change
   --ignore-whitespace`. **Verified:** the 263 patches of Zen `1.23.4b` apply cleanly to Firefox 158.0.1. The
   272 patches of Zen's `dev` branch (commit `fc54449`) apply cleanly to Firefox 159.0 and do
   not apply to 158.0.1 (first failure: `browser-js.patch`). A Zen revision is only valid for
   its own Firefox version.
2. **New files.** Everything else under `src/` (notably `src/zen/**` and `zen-*` files next to
   Firefox files) is symlinked into `engine/` one file at a time by `surfer import`.
   Consequence: `engine/zen/...` points back into the repository's `src/`, so editing a file in
   `src/` changes the engine immediately. Adding a **new** file requires re-running the import
   (or creating the link by hand).

`surfer` (npm package `@zen-browser/surfer`, MPL-2.0) is the orchestrator: `download`, `import`,
`build`, `package`, `export`, `reset`. It reads `surfer.json`. **Verified:** `surfer import` also
writes `engine/browser/branding/<brand>` from `configs/branding/<brand>` and the pref file
`firefox-branding.js`, which contains URLs hardcoded in surfer itself.

### 1.2 Build

`surfer build` assembles `engine/mozconfig` from `configs/common/mozconfig`, `configs/<os>/mozconfig`,
an optional git-ignored `mozconfig` at the repository root, and surfer's internal options, then
runs Firefox's `mach build`. The compiler toolchain, `cbindgen`, and system libraries come from
`mach bootstrap` in Zen's flow (see [BUILDING.md](BUILDING.md) for what was needed without it).

### 1.3 Preferences

`prefs/**/*.yaml` are compiled by `tools/ffprefs` (Rust) into two files inside the engine:

- `modules/libpref/init/zen-static-prefs.inc`: prefs with `type: static` (C++ mirrors).
- `browser/app/profile/zen.js`: every pref as `pref("name", value);`, `#include`d at the end of
  Firefox's `firefox.js`, so it overrides Firefox's defaults and branding defaults.

`prefs/firefox/` overrides Firefox defaults, `prefs/zen/` configures Zen features,
`prefs/privatefox/` and `prefs/fastfox/` import selected Betterfox settings, and Nivora adds
`prefs/nivora/`. `ffprefs` discovers `*.yaml` files recursively, sorts by name and does not
de-duplicate, so a pref must be defined in exactly one place.

### 1.4 User interface

Firefox's browser UI is XHTML/XUL plus JavaScript modules and CSS, registered with `jar.mn`
manifests and served as `chrome://browser/content/...`. Zen adds:

| Area | Where it lives | How it hooks into Firefox |
|---|---|---|
| Window skeleton | `src/browser/base/content/zen-*.inc.xhtml`, `browser-xhtml.patch`, `navigator-toolbox-inc-xhtml.patch` | `#include`s into `browser.xhtml`; wraps content in `#zen-main-app-wrapper` |
| Theme variables | `src/zen/common/styles/zen-theme.css`, `schemes/{dark,light}.inc.css`, `zenThemeModifier.js` | CSS custom properties derived from `--zen-primary-color` (pref `zen.theme.accent-color`) with `color-mix()` and `light-dark()`; `tokens-shared-css.patch` imports `zen-theme.css` into the design-system tokens, so every chrome page gets it |
| Vertical tabs, sidebar | `src/zen/tabs/**`, `src/zen/common/styles/zen-sidebar.css`, patches under `tabbrowser/` | Patches to `Tabbrowser`, `tab`, `tabs`, `tabgroup`, drag-and-drop |
| Spaces (workspaces) | `src/zen/spaces/**` (`ZenSpaceManager.mjs` alone is ~3,700 lines), `src/zen/sessionstore/**`, `src/zen/sync/**` | Patched Firefox session store; Firefox Sync engine for spaces |
| Compact mode | `src/zen/compact-mode/**` | JS + a C++ mouse tracker (`nsIZenMouseTracker`) |
| Address bar | `src/zen/urlbar/**`, `zen-omnibox.css`, patches to 12 files under `urlbar/` | Extra urlbar providers, including a **global actions provider that is already a command palette** (`ZenUBGlobalActions`, `zen-command-palette.ftl`) |
| Other features | `src/zen/{folders,split-view,glance,boosts,library,live-folders,space-routing,share,mods,media,downloads,welcome}` | Each has its own `jar.inc.mn`, `moz.build`, `.ftl` strings and tests |
| Preferences UI | `src/browser/components/preferences/zen*.inc.xhtml` + patches | Pages: Looks and Feel, Tabs Management, Keyboard Shortcuts, Marketplace |
| Native integration | patches to `widget/gtk`, `widget/cocoa`, `widget/windows`, `layout`, `gfx` | C++ patches; the highest-impact part of the tree |

### 1.5 Tests

`src/zen/tests/**` holds **530** `browser_*.js` mochitests in 26 groups. `manifest.toml` also pulls
selected Firefox browser tests into the Zen suite, with per-test `disable` and manifest rewrites.
`scripts/run_tests.py` copies `ignorePrefs.json` into the engine and calls `mach mochitest`. They
need a finished build. `npm run lint` runs `mach lint zen`.

### 1.6 Services the inherited code talks to

Nothing in a stock Zen build is Nivora's. See [SECURITY.md](SECURITY.md) section 4 for the full list
and Nivora's treatment of each. In short: update server (`updates.zen-browser.app`), share service
(`share.zen-browser.app`), mods store (`zen-browser.github.io/theme-store`), welcome and release
pages (`zen-browser.app`), donation links, plus Firefox's own services (Sync, Remote Settings,
add-ons, Safe Browsing, search engines).

## 2. Nivora architecture

### 2.1 Principles

- **Prefer configuration over code, and code over patches.** In order: a preference, a token, a
  new file under `src/nivora/`, a one-line hook in a Zen file, a patch to Firefox. Each step costs
  more at every upstream update.
- **Zero parallel infrastructure.** Nivora reuses `prefs/*.yaml`, the `%include` preprocessor,
  jar manifests and `moz.build`, because Zen already does. No new framework, no second UI.
- **Every touch of inherited code is listed** in [UPSTREAM.md](UPSTREAM.md) and can be listed by
  `git diff <root commit>..HEAD --stat -- . ':!src/nivora' ':!prefs/nivora' ':!tools/nivora' ':!docs'`.

### 2.2 Layers

| Concern | Nivora location | Mechanism |
|---|---|---|
| Visual tokens | `src/nivora/theme/nivora-tokens.inc.css` | Preprocessed into `zen-theme.css` `:root` by one `%include` |
| Dark scheme mapping | `src/nivora/theme/nivora-dark.inc.css` | Included from Zen's `schemes/dark.inc.css` and, for in-content pages, under `prefers-color-scheme: dark` |
| User-facing defaults | `prefs/nivora/*.yaml` and in-place edits of `prefs/zen/*.yaml` for prefs Zen already defines | Compiled by `ffprefs` |
| Identity | `surfer.json`, `configs/common/mozconfig`, `configs/branding/` | Read by surfer |
| Tooling and checks | `tools/nivora/` | Python standard library only |
| Features (Productivity) | `src/nivora/<feature>/` | Own `jar.inc.mn` and `moz.build`, registered by one `DIRS` entry |
| Linux integration (optional) | `src/nivora/linux/` | Feature-detected at runtime, never required |

### 2.3 Extension points, ranked by safety

1. **Preferences** (`prefs/`). Lowest risk; survives upstream changes unless the pref is renamed.
2. **Zen theme variables.** `--zen-*` names are Zen's public-ish API for theming. Nivora only
   assigns to them; it never restyles by selector.
3. **New modules in `src/nivora/`.** Independent files; the risk is limited to the registration
   hook.
4. **Zen mods** (`ZenMods`): user-level CSS themes. Appropriate for users, not for product code.
5. **Patches to Zen's own files** (small hooks). Medium risk.
6. **Patches to Firefox** (new `.patch` files). High risk; justify in an ADR.

### 2.4 Impact classification

| Planned change | Impact | Why |
|---|---|---|
| Pref defaults, endpoint neutralisation | Low | Data only |
| Obsidian Eclipse tokens and dark mapping | Low | Two include lines in Zen CSS, rest in new files |
| Branding strings and icons | Low | Generated from `configs/branding/` by surfer |
| Restyling tabs, urlbar, menus | Medium | Touches Zen UI CSS; depends on Zen markup |
| New tab page | Medium | Needs a decision between Zen's empty tab and Firefox's `about:newtab` (ActivityStream is patched) |
| Command palette | Medium | Extends `ZenUBGlobalActions` rather than duplicating it |
| Spaces, tab search, central settings | Medium | New code in `src/nivora/`, reading Zen's managers |
| Hiding Zen-service UI (share, marketplace) | Medium | Small hooks in preferences/library markup |
| Anything under `widget/`, `layout/`, `gfx/`, session store internals | High | C++ or core logic; avoid |

### 2.5 Fragile dependencies

- Zen patches are tied to an exact Firefox version. A Firefox bump re-bases 263 patches.
- `engine/zen/**` symlinks target absolute paths into the repository. Moving or deleting the
  repository directory breaks the engine silently (build fails on a missing `moz.build`).
- `ffprefs` quoting: a value is quoted only if it has letters, spaces or quotes. A hex color made
  of digits only was emitted bare and would have corrupted `zen.js`. Nivora fixed this
  (`tools/ffprefs`, with tests) and should offer the fix upstream.
- `light-dark()` and `color-mix()` chains: overriding one variable can shift many derived ones.
- Zen's JS globals (`gZenCompactModeManager`, `gZenFolders`, `gZenGlanceManager`, `gZenPinnedTabManager`, ...) are
  internal and have been renamed before (see `src/zen/zen.globals.mjs`).
- surfer hardcodes Zen URLs (Windows installer, `firefox-branding.js`). Nivora overrides the
  preferences it can; the Windows installer files are not addressed.

### 2.6 Information flow

```
prefs/*.yaml --ffprefs--> engine/browser/app/profile/zen.js --> Services.prefs
                                                                   |
        zenThemeModifier.js  <-- zen.theme.accent-color, border-radius, separation
              |  sets --zen-primary-color, --zen-border-radius on :root
              v
zen-theme.css  :root vars  <-- nivora-tokens.inc.css (palette, roles)
  schemes/dark.inc.css     <-- nivora-dark.inc.css (re-points --zen-* at roles)
              |
              v
   every chrome page (via tokens-shared.css) and the browser window
```

User input in the address bar goes through Firefox's `UrlbarController`, which asks the registered
providers (Firefox's plus Zen's) for results; Zen's actions provider turns matching text into
`cmd_zen*` commands, which are declared in `zen-commands.inc.xhtml` (51 of them).

## 3. Decisions

See [decisions/](decisions/): repository strategy, upstream base, theming mechanism and palette,
upstream service isolation, application identity.
