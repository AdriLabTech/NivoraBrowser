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
| 2026-10-27 | Nivora Python tests (114) | **pass** | `python3 -I -m unittest discover -s tools/nivora/tests`: contrast, prefs vs tokens, icons, branding, artwork, spring curves, motion probe, upstream check, Arch packaging (simulated `makepkg`), post-import, network-audit parsing |
| 2026-10-27 | Command registry, settings and palette-highlight geometry, Node (34) | **pass** | `node --test tools/nivora/js-tests/*.test.mjs`; mutation checks done when written |
| 2026-10-27 | Contrast, shipped palette | **24/24 pass** | The original `#777777` proposal fails 3 pairs (4.42, 4.25, 3.97): why ADR 0003 exists |
| 2026-10-27 | `ffprefs` unit tests (3) | **pass** | the hex-quoting test failed before the fix |
| 2026-10-27 | Icons are Phosphor-only; interface artwork equals the generator | **pass** | `generate_icons.py --check`, `generate_ui_artwork.py --check` |
| 2026-10-26 | Zen `1.23.4b` patches on Firefox 158.0.1 | **263/263 apply** | and 264/264 with Nivora's widget patch (clean re-import, 2026-10-27) |
| 2026-10-26 | Zen `dev` (`fc54449`) patches on Firefox 158.0.1 | **fail** (`browser-js.patch`) | reason for ADR 0002 |

### 2.2 In the built browser (clean import, then a full build, 2026-10-27)

| Check | Result | Notes |
|---|---|---|
| Build | **completed**, exit 0 | 76 min wall time on 4 cores; [BUILDING.md](BUILDING.md) |
| Nivora browser tests: commands, defaults, settings, hidden Zen-service controls, dark mapping, motion | **166 checks pass, 0 fail** (5 files; the last full run, after the motion work; the 123 before it passed twice in a row) | `cd engine && xvfb-run -a ./mach test nivora/tests/browser`. A test that read a computed style straight after a preference change failed once in a full run and now waits for the restyle. The first run (before fixes, three files) had 41 pass and 28 fail; the failures were two real defects (finding 7 in [SECURITY_REVIEW.md](SECURITY_REVIEW.md), missing `.ftl` packaging) and test mistakes |
| F-01, F-02: starts, shows a window, loads and titles a local page | **pass** | `tools/nivora/smoke.py` |
| Wayland: window, page title, profile directory, clean exit | **pass** | `tools/nivora/smoke_wayland.py` under headless `sway`: a window with application id `nivora` shows the page title; only `~/.config/nivora` created; exits when asked |
| F-10: profile directory | **pass** | With an empty `HOME`, only `~/.config/nivora` is created; no `.zen`, `.config/zen` or `.mozilla`. Not checked: behaviour when a `~/.zen` already exists |
| F-09: host names resolved by a fresh profile, 5 minutes | **pass** (limited) | `tools/nivora/net_audit.py` (no proxy, one local page): no Zen host. Mozilla services, Cisco and Google media-component downloads and the default search engine are contacted; the table is in [PRIVACY.md](PRIVACY.md) section 4. The first version of the audit (60 s, no page, proxy variables inherited) **missed the Google and Cisco hosts**; the run behind this row is the corrected one. Limits: a lookup log, not a packet capture; nothing after a failed lookup is seen |
| F-07: defaults of the managed prefs | **pass** | `browser_nivora_defaults.js` reads the default branch (accent, scheme, share base URL, update and release-notes URLs, hide-Zen-services, signature requirement) |
| F-11: unsigned extension with the shipped defaults | **refused** | `tools/nivora/check_signatures.py`: an unsigned `.xpi` in a fresh profile's `extensions/` is not loaded; with `xpinstall.signatures.required` off it is loaded and active (the control). The default is also read by `browser_nivora_defaults.js`. Not tried: installing through the add-ons page or from a web page; it cannot be a mochitest because the harness's own extensions are unsigned |
| Dark `Canvas` is the neutral surface (widget patch) | **pass** | `browser_nivora_defaults.js`, `test_blank_dark_pages_use_the_neutral_canvas` |
| Nivora commands in the command palette | **pass** | seen in a screenshot (Export, Import, Reset Nivora Settings; new tab, close tab and others from Zen) and by `browser_nivora_commands.js` |
| Close duplicate tabs, reset settings with confirmation | **pass** | `browser_nivora_commands.js` |
| Settings export/import/repair | **pass** (prefs backend) | `browser_nivora_settings.js`. The **file pickers** were not driven: the dialogs need a person |
| Visual review (screenshots, `tools/nivora/screenshots.py`) | **done** for the screens in section 3.2 | One defect found and fixed (a violet banner in the main menu); the rest is grayscale, with no Firefox or Zen logo or mascot. Not reviewed: loading, audio and warning tab states; compact mode; dialogs; the downloads panel with a download; the Library; `about:privatebrowsing` |
| Dark mapping reaches the window | **pass** | `browser_nivora_ui.js` (computed values of five mapped variables) |
| Motion language ([ANIMATIONS.md](ANIMATIONS.md)) | **pass** | `browser_nivora_motion.js` (11 tests): tokens, off switch, the system's reduced motion, palette entrance and gliding highlight (including its color), tabs, settings cascade, reaching `gReduceMotion`. Measured with `tools/nivora/motion_probe.py` (screen recording, software rendering): the numbers are in [ANIMATIONS.md](ANIMATIONS.md) section 4. A first version of the highlight was blue; a screenshot showed it, and a test now guards the color |
| Zen's groups touched by the motion changes | **pass**: `compact_mode` 13, `folders` 135, `tabs` 32, `urlbar` 97, `ub-actions` 92, `ui` 59, `glance` 27, `library` 224, `spaces` 112, `pinned` 70 | `python3 scripts/run_tests.py <group>`. `ub-actions` failed once with 6 checks when the new palette command's translation was not yet packaged (`python3 scripts/update_en_US_packs.py` must run after editing a `.ftl`); it passes after packaging. `library` failed once (7 checks in `browser_library_rapid_toggle.js` and `browser_library_toggle_sidebar_width.js`: "settles" timed out) in a run that overlapped other CPU work on the machine, and passed (224, 0 failures) in the two clean reruns that followed; the Library's open duration went from 0.3 s to 0.42 s in this work, so a timing sensitivity of those two tests to it is possible and not ruled out |
| Zen's own tests (all 26 groups) | **26,288 browser checks pass, 31 fail**; xpcshell: Sync and remote-settings fail for inherited reasons | see 2.3 for each failure |
| `npm run lint` | **not run** | needs node modules inside `engine/` |
| Performance baseline of Nivora itself | **measured, one environment** | `tools/nivora/perf_baseline.py`, 3 runs each, raw data in `docs/perf-baseline-2026-10-27.json`. Fresh profile: start-up 2.3 s (2.2-2.3), memory 533 MiB PSS (529-536), idle CPU 1.9 % of one core. Existing profile: 1.4 s (1.3-1.4), 512 MiB (508-514), idle 0.6 %. One local page open, software rendering, development build without LTO/PGO, 4 cores, 30 s idle window. Useful only to compare a later Nivora build on the same machine |
| Comparison with Zen | **not done** | no unmodified Zen build exists here, and an official Zen binary was deliberately not run in this environment; so "no regression against Zen" is not established for speed or memory |
| `./mach package`, Arch package inputs from the real build | **done**, not installed on Arch | `mach package` (3 min 49 s) and `make_arch_package.sh` on the real tree; the `PKGBUILD`'s `package()` was run against it; the unpacked copy with the policy starts and `about:policies` shows `DisableAppUpdate: true`. `makepkg`, `pacman`, `desktop-file-validate`, `appstreamcli` not available here |

### 2.3 Zen's own mochitests and xpcshell tests

Run with `python3 scripts/run_tests.py <group>` under `xvfb-run` on the build of 2026-10-27, which carries
all of Nivora's changes. All 26 groups were run (`migration` contains no tests). `ub-actions` matters
most for Nivora: `browser_ub_actions_search.js` iterates every global action, Nivora's eight included.

**Browser tests: 26,288 checks pass, 31 fail, 83 marked `todo` by Zen.** Groups with no failure: `ub-actions` 90,
`urlbar` 97, `tabs` 32, `spaces` 112, `pinned` 70, `folders` 135, `library` 224, `live-folders` 77,
`compact_mode` 13, `container_essentials` 29, `ui` 59, `device_sync` 82, `site_control` 21,
`split_view` 124, `glance` 27, `window_sync` 29, `space_routing` 23,276, and the Firefox groups Zen includes:
`alerts`, `backforward`, `caps`, `gesture`, `linkHandling`, `metaTags`, `mousepostracker`, `pageStyle`,
`pageinfo`, `readermode`, `scroll-to-text-fragment`, `tabdialogs`, `tooltiptext`, `zoom`.

The 31 failures, and what is known about each. **No run of unmodified Zen `1.23.4b` was possible**, so
"inherited" below means: explained by the test or the environment, or reproduced with Nivora's
preference changes switched off, not compared with a Zen build.

| Group (failures) | Cause | Evidence |
|---|---|---|
| `welcome` (1) | No window manager: the window is maximized | **Passes** under `openbox` |
| `sessionstore` (2 of 540) | One needs a window manager (minimize); one tests an unreadable backup file and the tests run as root | The first **passes** under `openbox`; the second is root-related (not re-run unprivileged) |
| `popover` (1) | A macOS-only fix (`NSPopover`); Zen's manifest says `run-if os == 'mac'` but the runner executed it | Manifest |
| `window_drag` (4) | Needs a native window-drag that Xvfb with or without a window manager does not produce | Fails under `openbox` too |
| `media` (6), `tabMediaIndicator` (1) | The tabs never report `soundplaying`: no audio device in the container | Log |
| `shell` (1) | `setDesktopBackground` needs the GNOME shell service | Log |
| `outOfProcess` (1), `plugins` (1 file, 2 checks) | "Found an unexpected tab at the end of test run: about:blank": Zen keeps an empty tab | Log |
| `boosts` (4) | The test calls `BrowserTestUtils.waitForCondition`, which does not exist | Test bug in Zen's file |
| `performance` (4) | `ZenBoostsChild.sys.mjs` is not in the startup-module allow-list; panel vsync and tab-close timing in a container without a GPU | Log |
| `share` (4, all in `test_import_space`) | Not explained. **Not caused by Nivora's preferences or its share gating**: the same four fail with every preference Nivora changed set back to Zen's value (`zen.share.base-url`, accent, scheme, mods auto-update, update notification) | Rerun with `--setpref`. CSS, locale strings and artwork were not reverted |

**xpcshell:** `services-crypto` 5 of 5 pass. `sync`: 83 of 272 checks fail, 162 crash lines: every crash is
`MOZ_CRASH: Missing chrome or resource URLs: resource:///modules/zen/ZenSpacesSync.sys.mjs` (read with `gdb`): a Zen
patch makes Sync import a browser module that xpcshell's application directory does not map. Inherited.
`remote-settings`: 10 of 140 fail because Zen's `update_service_dumps.py` ships dumps with 2 records where the
tests expect more than 20. Inherited. **Sync itself was not exercised in the browser.**

What this does and does not show: no failure was traced to a Nivora change, and the ones that could
be (preferences, share gating) were checked. It is not a proof of "no regression against Zen": that needs the
baseline run. Nothing was disabled to obtain these results.

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

### 3.3 Results of the screen review (2026-10-27)

`python3 -I tools/nivora/screenshots.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR` produces them; four are in
[screenshots/](screenshots/).

| ID | Result |
|---|---|
| I-01 | **Pass** for the new tab, a page, settings (two panes), the command palette, the main menu, a tab context menu, a private window and `about:policies`/`about:support`'s frame: grayscale surfaces stepping from `#050505` to `#181818`. Exceptions kept on purpose: the yellow warning triangle in settings (a status color), web favicons, and the Mozilla account logo. `about:support` has its own light-blue table headers (not mapped) |
| I-02 | **Partly.** Active tab: lighter fill; inactive: transparent; pinned: a separate section above the divider; hover: a lighter fill. Loading, audio and warning states were **not** exercised, so "not by color alone" is not shown for them |
| I-03 | **Not done** beyond seeing the white focus ring on the settings search field |
| I-04 | **Pass for width**: at 420 px the sidebar keeps its width and the page narrows; nothing clipped. Compact mode not tried |
| I-05 | **Pass for Nivora's own motion**: with `ui.prefersReducedMotion` or `nivora.ui.animations` off, every Nivora duration and distance is 0 (`browser_nivora_motion.js`) and a settings pane switches in one step (screen recording). Zen's own CSS micro-transitions of 80-200 ms remain; the system setting was tried through its preference, not through a desktop environment |
| I-06 | **Pass**: at 2x (`GDK_SCALE=2`) icons and text are crisp and targets large |
| I-07 | **Partly**: the main menu and a tab context menu are consistent and readable; dialogs and the downloads panel with a download were not seen |

The light scheme (`zen.view.window.scheme=1`) renders Zen's own light theme, unthemed by Nivora, as documented.

Automated screenshot comparison is a goal for Stable; until then these steps are executed by hand
and the result with screenshots is attached to the phase report.

## 4. What the Zen suite is for

`npm test` runs Zen's own mochitests against the build. They guard inherited behaviour
(spaces, folders, split view, glance, library, urlbar actions, ...). The Foundation expectation is
that **the number of failures does not increase compared with a build of unmodified Zen
`1.23.4b`**; that requires one baseline run of each, which has not happened yet. Failing tests are
never disabled to obtain a green result.

## 5. Known gaps

- No visual regression tooling: screenshots are taken by `tools/nivora/screenshots.py` and judged by a person.
- Performance: one environment, one tab, a development build, no comparison with Zen (section 2.2).
- CI runs only the static checks ([nivora-checks.yml](../.github/workflows/nivora-checks.yml): contrast,
  icons, artwork, Python and Node tests, `ffprefs`), green on GitHub's runners since 2026-10-27. The
  first runs skipped the icon, branding and artwork tests silently because Pillow was missing
  (and `python -I` ignores `pip install --user`); that is fixed with a virtual environment. No browser
  build or browser test runs in CI: a build needs about 80 minutes, 5 GB of object files and the
  patched Firefox source.
- Zen's own CI workflows were removed because they run Zen's release pipeline.
