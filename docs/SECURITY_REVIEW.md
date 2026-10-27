# Review of Nivora's own changes

Scope: everything Nivora added or changed (not Firefox, not Zen's code). Method: read each change as
an attacker would (what input can it be given, what can it make the browser do), run what can be
run, and fix what is wrong. Reviewer: the author of the code, so this is a self-review; it does not
replace an independent one. Date: 2026-10-26, on commit `f91e906` and earlier.

## 1. Surface added

| Component | Privilege | Input it accepts | Reaches |
|---|---|---|---|
| `NivoraCommands.sys.mjs` and the registry | Chrome (privileged) | Commands chosen by the user in the palette; nothing from web content | Tabs, address bar, native commands, dialogs |
| `NivoraSettings.sys.mjs` | Chrome | A JSON file the user picks | A fixed list of 25 preferences |
| `ZenUBGlobalActions` hook | Chrome | none | Appends the Nivora commands to Zen's list |
| `ZenShareManager.enabled` change | Chrome | A preference | Hides share UI when no service is set |
| `nivora-ui.inc.css`, `nivora-dark.inc.css` | Chrome CSS | A preference (media query) | Hides two controls; remaps color variables (both verified by `browser_nivora_ui.js`) |
| Token CSS | Chrome CSS | none | Variables |
| `src/widget/nsXPLookAndFeel-cpp.patch` | Native (parent and content processes) | none | Six color constants of the dark system palette; no logic changed |
| Replacement SVG and PNG artwork (`generate_ui_artwork.py`, 25 SVG and 3 PNG files) | Chrome resources | none | Static drawings; a test refuses `<script>`, `<style>`, `<use>`, `<image>`, `href` and external `url()` in them |
| `tools/`, packaging | Developer machine / package build | repository files | none at run time. `smoke.py`, `net_audit.py` and `screenshots.py` start the built browser with a throw-away `HOME` and only open local pages |

No Nivora code runs in a content process, accepts a URL, a web message or a network response, or opens
a socket.

## 2. Findings

| # | Finding | Severity | State |
|---|---|---|---|
| 1 | **The profile directory was Zen's.** Zen's configure patch defaults `MOZ_APP_PROFILE` and `MOZ_USER_DIR` to `zen`, so a Nivora build would have used `~/.zen` (shared cookies, passwords, session; one browser could corrupt the other's profile) | High (privacy, data integrity) | **Fixed** in `src/toolkit/moz-configure.patch`; configuration verified; runtime check F-10 pending |
| 2 | "Close duplicate tabs" treated the same address in two **containers** as a duplicate. Closing one could lose a separate login session | Medium (data loss, with confirmation) | **Fixed**: the container id is part of the key; unit test added |
| 3 | The settings import checked the size with `stat()` and then read the whole file: a file that grew in between would be read in full | Low (local file chosen by the user) | **Fixed**: `IOUtils.read` with `maxBytes` (a first attempt used `readUTF8`, whose options do not include `maxBytes`; caught by reading `IOUtils.webidl`), strict UTF-8 decoding |
| 4 | Zen's build does not enforce extension signing; the default preference is `true` but can be turned off | Medium, inherited | **Documented**; decision left for the release configuration |
| 5 | A first draft of this work claimed Zen "loses" the signing default; it does not (Zen sets it). The mistaken preference file was removed before publication | n/a | Corrected |
| 6 | Zen-operated hosts in defaults (update, share, injection, welcome pages) | Medium (privacy, supply chain) | **Fixed**; test fails if a default points at a Zen host |
| 7 | **The branding file overrode the endpoint defaults.** `surfer import` writes Zen's update, release-notes and homepage URLs into `browser/branding/<brand>/pref/firefox-branding.js`, which Firefox loads after `zen.js`, so finding 6's fix was silently ineffective at run time (found by `browser_nivora_defaults.js` on the first real run; the static test only reads the YAML) | Medium (privacy) | **Fixed**: `tools/nivora/post_import.py` removes those prefs and fails the import if a Zen URL remains; the browser test now passes |
| 8 | A build made earlier in the session still carried Zen's logo in the settings page: the engine had been imported before the branding was regenerated (found by looking at a screenshot) | Low (identity) | **Fixed** by a clean re-import; `npm run import` always regenerates it |

## 3. What was checked, per component

**Command registry.** A command is data plus functions; `register` rejects a spec whose `run` is not a
function (so a string can never be executed), whose id is malformed or duplicated, whose category is
unknown. `execute` validates arguments against the declared parameters and rejects unknown ones,
contains every exception, and never runs a `sensitive` command without `context.confirm()`
returning true. `prepare` is read-only by contract. Mutation checks: removing the confirmation gate,
the version check or the secret-name guard each made tests fail.

**Settings.** Whitelist of 25 preferences with types and bounds; import is JSON only, 64 KiB, all or
nothing, ignores unknown keys, refuses newer versions; `__proto__` keys do not pollute (tested);
the schema refuses names that look like secrets; export lists only changed whitelisted values.
`repair()` only ever deletes an invalid user value.

**Tabs.** The duplicate finder never proposes pinned, essential, empty or blank tabs, nor tabs of
another space or container; closing needs a confirmation that states the count; Firefox's own
`removeTabs` still asks about unsaved pages.

**Hooks into Zen.** The actions hook is inside `try/catch`, so a Nivora fault cannot remove Zen's
actions; the share gate only ever hides UI.

## 4. Not reviewed or not possible here

- Anything inside Firefox or Zen, including the 263 patches, the native code, the session store.
- Interaction effects in a running browser beyond what the Nivora browser tests, the smoke test and
  the network audit exercise (results in [TESTING.md](TESTING.md)).
- `makepkg`/`pacman` behaviour of the package, and the installed file permissions on a real system.
- Fuzzing, dependency scanning beyond `npm audit`, reproducibility of builds.
- Whether another process can write the profile's preferences between `repair()` and use (it can; the
  consequence is the same as editing the profile by hand).
