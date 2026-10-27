# Productivity features

For each area: what the requirement says, what Zen already provides (read from the code, Zen
`1.23.4b`), what Nivora added, what is not done, and how it was checked. "Verified" always names
the check. Items that need the built browser are marked and tracked in
[TESTING.md](TESTING.md).

Principle: Zen already implements most of this. Nivora adds a checked layer where something was
missing or ungoverned, and does not duplicate the rest.

## 1. Command palette

| Requirement | State |
|---|---|
| Opens with a shortcut, search field, keyboard navigation, shows shortcuts, Escape closes, focus returns | **Zen provides it**: the address bar in "actions" mode (`ZenUBGlobalActions.sys.mjs`, `ZenUBActionsProvider.sys.mjs`): fuzzy matching, learned ordering, ~50 actions, switching to a space by name, extension actions, shortcut hints |
| Central registry: stable id, name, description, category, shortcut, parameters, availability, action, error handling | **Added by Nivora**: `src/nivora/modules/NivoraCommandsCore.mjs` |
| No arbitrary code; sensitive actions confirm | **Added**: a command is data plus functions; `run` must be a function (a string is rejected at registration); arguments are validated against a declared schema and unknown ones rejected; `sensitive` commands run only after `context.confirm()`; `prepare()` lets a command look (pick a file, count tabs) before asking |
| Initial actions list | Zen already has: close tab, switch space (next/previous and by name), preferences, compact mode, private window, reopen closed tab. **Nivora adds**: new tab, open history, open downloads, search open tabs, close duplicate tabs, export / import / reset Nivora settings |
| A failing command must not break the palette | Errors are caught and reported through `console.error`; the result is `{ ok: false, error }`. Nivora's module is imported inside a `try/catch` by Zen's actions file, so a Nivora fault cannot remove Zen's actions |

How it is wired: `ZenUBGlobalActions.sys.mjs` loads `NivoraCommands.sys.mjs` and appends its list
(`nivoraGlobalActions`) to Zen's template. Labels come from `locales/en-US/browser/browser/nivora.ftl`.

Verified: 31 Node unit tests cover the registry (spec validation, argument validation, availability,
confirmation, prepare, error containment) and three mutation checks confirmed the tests fail when
the safeguards are removed. `src/nivora/tests/browser/browser_nivora_commands.js` covers the browser
integration (palette entries registered, close-duplicates with and without confirmation, reset with
confirmation, error codes); **passes** in the built browser (2026-10-27, [TESTING.md](TESTING.md)).
The commands are visible in the palette in a screenshot.

Not done: a user-configurable shortcut for opening the palette (Zen's own shortcut editor handles
Zen's commands; Nivora's commands appear in the palette but have no assignable key), and command
parameters are supported by the registry but no shipped command uses one.

## 2. Central settings

| Requirement | State |
|---|---|
| Theme, density, visibility, tab behavior, animations, spaces behavior | A schema of **25 real preferences** (Zen's plus `nivora.ui.hide-zen-services`) in 6 groups: appearance, layout, tabs, spaces, behavior, animation. Defaults stay in the preference system; the schema holds types and limits only |
| Persistent | Preferences persist in the profile as usual |
| Validation, safe fallback, corrupt configuration never blocks startup | `repairSettings` runs when Nivora's commands load: a managed preference whose value is out of range or of the wrong type is cleared, so the default applies. Import is parsed as JSON, never evaluated, size-limited to 64 KiB, all-or-nothing |
| Export / import: documented, versioned, validated, no secrets | Format `nivora-settings` version 1 (section below). Only managed preferences that the user changed are exported. Any schema entry whose name looks like a secret (`password`, `token`, `cookie`, `session`, `private`, ...) is refused when the schema is defined. Unknown keys in an imported file are ignored with a warning, never applied. A file from a newer version is rejected |
| Restore defaults | Command "Reset Nivora Settings to Defaults" (confirms first) |
| Do not promise to export all of Firefox's settings | Only the 25 listed preferences are covered, and the export dialog says so; Firefox's own settings, bookmarks, passwords and history are untouched |

Format:

```json
{
  "format": "nivora-settings",
  "version": 1,
  "settings": { "zen.view.window.scheme": 0, "zen.theme.accent-color": "#858585" }
}
```

Verified: Node tests for export, import, round trip, rejection of oversized / malformed / newer /
mis-typed input, `__proto__` keys, secrets, unknown preferences, reset and repair;
`browser_nivora_settings.js` repeats the key cases against the real preference service (**passes** in
the built browser). The export and import **file pickers** were not driven by a test: they need a person.

Not done: a settings page in `about:preferences`. Settings are reachable through the palette and
Zen's existing preference panes; adding a Nivora pane is a markup change in privileged preference
files and was judged not worth its upgrade cost yet.

## 3. Spaces (workspaces)

| Requirement | Zen |
|---|---|
| Create | `createAndSaveWorkspace`, creation panel, command "New space" |
| Rename, change icon | Edit panel; `changeWorkspaceIcon` |
| Position | `reorderWorkspace`, drag and drop |
| Switch | `changeWorkspace*`, next/previous, by name in the palette, swipe, shortcuts; `zen.workspaces.wrap-around-navigation` |
| Close / delete | `contextDeleteWorkspace`, with a confirmation; "unload" a space without closing it |
| Recover | **Not available**: deleting a space has no undo. Closed tabs can be reopened through the session store |
| Initial behavior, persistence | `zen.workspaces.continue-where-left-off`; spaces live in Zen's session store and survive restarts |
| Safe switching | Switching only changes which tabs are shown |

Not a security boundary: **spaces share cookies, storage and credentials with each other.** A space
can be bound to a Firefox container (`containerTabId`), which does separate cookies and storage;
that is the mechanism to use when isolation is needed. Nivora does not claim more.

Nivora added: nothing. The requirement is met by Zen except recovery, which needs a change in
`ZenSpaceManager.mjs` (about 3,700 lines of privileged code) and is left out deliberately.

## 4. Tabs

| Requirement | State |
|---|---|
| Search by title, address, space, state | **Zen / Firefox provide it**: the address bar's tab search (`%`), workspace search. Nivora adds the command "Search Open Tabs" that opens it. Nothing is sent anywhere: matching is local |
| Grouping | Zen provides folders and Firefox tab groups; no second representation was added |
| Pinning | Unchanged; pinned and essential tabs keep Zen's behavior |
| Restoration | Unchanged: Firefox session store (`History:RestoreLastClosedTabOrWindowOrSession`, already in the palette) |
| Clutter | **Added**: "Close Duplicate Tabs". The pure function `findDuplicateTabs` compares pages by address without the fragment, within one space; it never proposes pinned, essential or empty tabs or blank pages; it keeps the selected tab, otherwise the first. Closing happens **only after the user confirms**, and the dialog says how many tabs will close |
| Indicators | No new indicators; nothing invented about memory or activity |
| No automatic closing or discarding | Nivora closes nothing on its own |

Not done: detection of inactive tabs (needs real timing data) and memory indicators (not measured,
so not shown).

## 5. Profiles and sessions

Firefox's own profile machinery is used unchanged. In this build `browser.profiles.enabled` is
`false` (Zen's choice): the multi-profile UI is off and profiles are selected with the command line
(`-P`, `--profile`) or the Profile Manager. Nivora does not copy credentials or cookies between
profiles and does not add password synchronisation. Session restore is Firefox's, extended by Zen's
window sync (`zen.window-sync.*`). The application name `nivora` is expected to give Nivora its own
default profile directory, separate from Zen's; this is checked by test F-10 in TESTING.md.

## 6. Linux and Ryoku Arch

See [LINUX.md](LINUX.md).

## 7. Privacy

See [PRIVACY.md](PRIVACY.md).

## 8. Optional AI features

Not implemented, by design. The specification makes this an optional module that must not delay
essentials. If it is built later it must: be off by default; show what would be sent before
sending; never send history, cookies, credentials or whole pages automatically; treat page content
as untrusted; and have no autonomous access to the browser or the system. The command registry's
rules (no code from data, confirmation for sensitive actions) are the foundation that module would
sit on.

## 9. Hiding Zen-service interface

`nivora.ui.hide-zen-services` (default true) hides, by CSS gated on the preference, the Library's
donate button and the preferences link to the Zen mods website. Sharing hides itself because
`gZenShareManager.enabled` now requires a configured `zen.share.base-url`. The About dialog keeps
its links to Zen and Firefox on purpose: that is attribution, not a service.
