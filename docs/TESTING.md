# Testing

Nothing is reported as passing unless it was run. Each result below names the command and the date
it was last run. "Not run" means exactly that.

## 1. Test layers

| Layer | What it covers | Needs a build | Command |
|---|---|---|---|
| Nivora static checks | Palette contrast, token parsing, pref/token consistency, no Zen endpoint in pref defaults | No | `python3 -I -m unittest discover -s tools/nivora/tests` |
| Palette report | Every contrast pair with its ratio | No | `python3 -I tools/nivora/check_contrast.py --list` |
| `ffprefs` unit tests | Pref value quoting | No (needs Rust) | `cd tools/ffprefs && cargo test` |
| Build-time checks | Preprocessing of Nivora's CSS includes, `surfer import`, configure | Partly | see [BUILDING.md](BUILDING.md) |
| Zen browser tests | 530 mochitests in 26 groups, plus selected Firefox tests | Yes | `npm test` (`scripts/run_tests.py`) |
| Lint | Mozilla's linters over Zen's tree | Engine + node modules | `npm run lint` |
| Manual UI procedure | What automation cannot judge: look, focus, narrow windows | Yes | section 3 |

## 2. Results log

Reference environment: Ubuntu 24.04 container, 4 cores, no GPU, Xvfb 1400x900 (X11), no network beyond a
proxy allow-list, development build (no LTO/PGO). Dates are when the command last ran.

### 2.1 Without a browser

| Date | Check | Result | Notes |
|---|---|---|---|
| 2026-10-27 | Nivora Python tests (74) | **pass** | `python3 -I -m unittest discover -s tools/nivora/tests`: contrast, prefs vs tokens, icons, branding, artwork, upstream check, Arch packaging (simulated `makepkg`), post-import, network-audit parsing |
| 2026-10-27 | Command registry and settings, Node (31) | **pass** | `node --test tools/nivora/js-tests/*.test.mjs`; mutation checks done when written |
| 2026-10-27 | Contrast, shipped palette | **24/24 pass** | The original `#777777` proposal fails 3 pairs (4.42, 4.25, 3.97): why ADR 0003 exists |
| 2026-10-27 | `ffprefs` unit tests (3) | **pass** | the hex-quoting test failed before the fix |
| 2026-10-27 | Icons are Phosphor-only; interface artwork equals the generator | **pass** | `generate_icons.py --check`, `generate_ui_artwork.py --check` |
| 2026-10-26 | Zen `1.23.4b` patches on Firefox 158.0.1 | **263/263 apply** | and 264/264 with Nivora's widget patch (clean re-import, 2026-10-27) |
| 2026-10-26 | Zen `dev` (`fc54449`) patches on Firefox 158.0.1 | **fail** (`browser-js.patch`) | reason for ADR 0002 |

### 2.2 In the built browser (clean import, then a full build, 2026-10-27)

| Check | Result | Notes |
|---|---|---|
| Build | **completed**, exit 0 | 76 min wall time on 4 cores; [BUILDING.md](BUILDING.md) |
| Nivora browser tests: commands, defaults, settings | **117 checks pass, 0 fail** | `cd engine && xvfb-run -a ./mach test nivora/tests/browser`. The first run (before fixes) had 41 pass and 28 fail; the failures were two real defects (finding 7 in [SECURITY_REVIEW.md](SECURITY_REVIEW.md), missing `.ftl` packaging) and test mistakes |
| F-01, F-02: starts, shows a window, loads and titles a local page | **pass** | `tools/nivora/smoke.py` |
| F-10: profile directory | **pass** | With an empty `HOME`, only `~/.config/nivora` is created; no `.zen`, `.config/zen` or `.mozilla`. Not checked: behaviour when a `~/.zen` already exists |
| F-09: host names resolved on a first start, 60 s idle | **pass** (limited) | `tools/nivora/net_audit.py`: `firefox.settings.services.mozilla.com`, `firefox-portal-detection.com`, `cloudflare-dns.com` and loopback/probe names. No Zen host. Limits: a lookup log, not a packet capture; no network beyond the proxy, so nothing after a failed lookup is seen; 60 s, not 5 minutes |
| F-07: defaults of the managed prefs | **pass** | `browser_nivora_defaults.js` reads the default branch (accent, scheme, share base URL, update and release-notes URLs, hide-Zen-services, signature requirement) |
| F-11: `xpinstall.signatures.required` default | **pass** | default only; installing an unsigned `.xpi` was **not** tried |
| Dark `Canvas` is the neutral surface (widget patch) | **pass** | `browser_nivora_defaults.js`, `test_blank_dark_pages_use_the_neutral_canvas` |
| Nivora commands in the command palette | **pass** | seen in a screenshot (Export, Import, Reset Nivora Settings; new tab, close tab and others from Zen) and by `browser_nivora_commands.js` |
| Close duplicate tabs, reset settings with confirmation | **pass** | `browser_nivora_commands.js` |
| Settings export/import/repair | **pass** (prefs backend) | `browser_nivora_settings.js`. The **file pickers** were not driven: the dialogs need a person |
| Visual review (screenshots, `tools/nivora/screenshots.py`) | **done for** window, sidebar, address bar, command palette, settings (two panes), blank page | Palette is grayscale; no Firefox or Zen logo or mascot in these screens. Not reviewed: tab states, menus, downloads panel, private window, high-DPI, narrow windows |
| Zen mochitest subset | ZEN_SUBSET_PLACEHOLDER | see 2.3 |
| `npm run lint` | **not run** | needs node modules inside `engine/` |
| Performance baselines | **not done** | needs a release-like build and an equivalent Zen build; an official Zen binary was deliberately not run in this environment |
| `./mach package`, Arch package from a real build | **not done** | the packaging script is tested against a simulated build only |

### 2.3 Zen's own mochitests (subset)

ZEN_TABLE_PLACEHOLDER

## 3. Manual procedure (reproducible)

Use a disposable profile: `./engine/mach run --temp-profile` (add `xvfb-run -a` on a headless
machine). Record the build id from `about:support`.

### 3.1 Foundation acceptance

| ID | Step | Expected |
|---|---|---|
| F-01 | Start the browser | A window appears, no crash, no error dialog |
| F-02 | Enter a URL in the address bar | Page loads; padlock/identity indicator shown for HTTPS |
| F-03 | Open 5 tabs, close 3, reopen one with Ctrl+Shift+T | Counts correct, closed tab restored |
| F-04 | Back and forward | History respected |
| F-05 | Load a media-heavy page, a form page, a PDF | Renders and works |
| F-06 | Change a setting in preferences, restart | Setting persists (use a named profile for this step) |
| F-07 | `about:config`: `zen.theme.accent-color`, `zen.view.window.scheme`, `zen.share.base-url`, `app.update.auto`, `startup.homepage_override_url` | `#858585`, `0`, empty, `false`, empty |
| F-08 | `about:preferences`, `about:addons`, `about:downloads`, `about:history`, new private window | Open without visual breakage |
| F-10 | Start with `HOME` set to an empty directory, then list it | `.config/nivora` (or `.nivora` when `MOZ_LEGACY_HOME` is set) appears; no `.zen`, `.config/zen` or `.mozilla`. With a pre-existing `~/.zen`, Nivora does not read or modify it (compare a checksum of the directory before and after) |
| F-11 | `about:config`: `xpinstall.signatures.required`; try installing an unsigned `.xpi` | `true`; the install is refused |
| F-09 | Network: start with a packet capture or a proxy log, browse nothing for 5 minutes | No connection to `zen-browser.app`, `updates.zen-browser.app`, `share.zen-browser.app`, `zen-browser.github.io` |

### 3.2 Identity

| ID | Step | Expected |
|---|---|---|
| I-01 | Compare window, sidebar, toolbar, address bar, popups with the palette | Grayscale only; surfaces step as in the design system |
| I-02 | Tab states: active, inactive, pinned, loading, playing audio, with a warning | Each distinguishable without color |
| I-03 | Keyboard: Tab through toolbar and sidebar | Focus ring visible on every stop |
| I-04 | Resize to 400 px wide, then to compact mode | No clipped or overlapping controls |
| I-05 | System setting "reduce motion" on | Nivora animations off |
| I-06 | 2x display scale | Icons and text crisp, targets large enough |
| I-07 | Menus, context menus, dialogs, downloads panel | Consistent surfaces and readable text |

Automated screenshot comparison is a goal for Stable; until then these steps are executed by hand
and the result with screenshots is attached to the phase report.

## 4. What the Zen suite is for

`npm test` runs Zen's own mochitests against the build. They guard inherited behaviour
(spaces, folders, split view, glance, library, urlbar actions, ...). The Foundation expectation is
that **the number of failures does not increase compared with a build of unmodified Zen
`1.23.4b`**; that requires one baseline run of each, which has not happened yet. Failing tests are
never disabled to obtain a green result.

## 5. Known gaps

- No visual regression tooling.
- No performance harness yet (section 23.3 of the specification: startup, RAM, idle CPU, UI
  latency, many tabs, compared with Zen under equal conditions).
- No CI. The Zen workflows were removed because they run Zen's release pipeline.
