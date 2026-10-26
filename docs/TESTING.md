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

| Date | Check | Result | Notes |
|---|---|---|---|
| 2026-10-26 | Nivora unit tests (14) | **pass** | stdlib `unittest` |
| 2026-10-26 | Contrast, shipped palette | **24/24 pass** | |
| 2026-10-26 | Contrast, original `#777777` proposal | **3 fail** (4.42, 4.25, 3.97) | proves the checker catches it; justification for ADR 0003 |
| 2026-10-26 | `ffprefs` unit tests (3) | **pass** | the hex-quoting test failed before the fix and passes after |
| 2026-10-26 | Zen `1.23.4b` patches on Firefox 158.0.1 | **263/263 apply** | `surfer import`, upstream unmodified |
| 2026-10-26 | Zen `dev` (`fc54449`) patches on Firefox 158.0.1 | **fail** (`browser-js.patch`) | reason for ADR 0002 |
| 2026-10-26 | Zen `dev` (`fc54449`) patches on Firefox 159.0 | 272/272 apply | |
| 2026-10-26 | `surfer import` with Nivora's changes | **pass**, 273 steps | |
| 2026-10-26 | Gecko preprocessor on `zen-theme.css` with Nivora includes | **pass** | 1 palette block and 5 dark-mapping blocks in the output, no leftover directive |
| 2026-10-26 | Zen mochitests | **not run** | needs a finished build |
| 2026-10-26 | `npm run lint` | **not run** | needs node modules inside `engine/` |
| 2026-10-26 | Rendered UI, screenshots | **not done** | needs a finished build |
| 2026-10-26 | Performance baselines | **not done** | needs a finished build and an equivalent Zen build |

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
