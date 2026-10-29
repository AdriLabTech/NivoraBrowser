# Animations

Motion is part of what Nivora is for. Zen already animates a lot, but most of it is short (80-200 ms) and
tuned to stay out of the way. Nivora's rule is the opposite: **every state change is shown, with a motion
that has character** - things arrive on a spring, settle, and leave quickly - and the whole interface
uses one motion language, so it reads as one product.

Character does not mean length. The first version of this language (v1) was long, blurred and bouncy, and
an audit that read the real animations frame by frame found it slower and louder than it needed to be. This
page describes **v2**: the same ideas, shorter, cleaner and measured against budgets that a test enforces.

This page is the language, the inventory, the budgets, the way to turn it off, and what was measured.
Statuses follow the rest of the documentation: *implemented* (in the tree), *built* (in the binary),
*tested* (a test or measurement ran), *looked at* (a person, or Claude, viewed the frames).

## 1. The language

Everything comes from tokens in [`nivora-tokens.inc.css`](../src/nivora/theme/nivora-tokens.inc.css); no
stylesheet rule hard-codes a duration or a curve.

| Token | v1 | v2 | Used for |
|---|---|---|---|
| `--nivora-d-micro` | 140 ms | **110 ms** | a hover, a press |
| `--nivora-d-fast` | 220 ms | **170 ms** | a color or opacity change, the fade of an arrival |
| `--nivora-d-base` | 420 ms | **260 ms** | a spring that settles: rows, tabs, buttons, a popup arriving |
| `--nivora-d-slow` | 640 ms | **340 ms** | a surface arriving: the palette, a dialog, a settings pane |
| `--nivora-d-cinematic` | 1100 ms | **520 ms** | the window assembling itself at start |
| `--nivora-d-exit` | (none) | **130 ms** | anything leaving: popups, the palette |
| `--nivora-stagger` / `-tight` | 34 / 15 ms | **22 / 7 ms** | the step between items of a cascade |
| `--nivora-ease-out` / `-in` / `-in-out` | expo-out, in, in-out | expo-out, **a gentler in**, in-out | arrivals, departures, symmetric moves |

| Spring | Damping | Overshoot | Used for |
|---|---|---|---|
| `--nivora-spring-smooth` | 1.0 | **0 %** | large surfaces, no bounce: the window at start, settings groups |
| `--nivora-spring-snappy` | 0.8 | **1.5 %** | rows, selection, the highlight bar, buttons, menu items |
| `--nivora-spring-settle` | 0.7 | **4.6 %** | the palette, dialogs, popups arriving, a tab arriving or selected, the close button |
| `--nivora-spring-bouncy` | 0.55 | 12.6 % | defined, **unused** in v2 (v1 used it for the palette, dialogs and tabs) |
| `--nivora-spring-elastic` | 0.38 | 27.4 % | defined, unused: reserved for a rare confirmation |

The spring curves are **generated**, not guessed: [`tools/nivora/generate_motion.py`](../tools/nivora/generate_motion.py)
solves the step response of a damped spring and writes 48 samples as a CSS `linear()` easing into
`nivora-springs.inc.css`. The duration of a transition that uses one is the time the spring takes to settle
(within 0.5 %). A unit test checks the shape (starts at 0, ends at exactly 1, never overshoots when critically
damped, overshoots more as damping falls, each spring inside its overshoot band) and CI fails if the
generated file is stale.

Two more tokens make motion switchable without every rule knowing about it: `--nivora-motion-scale`
multiplies every duration and `--nivora-lift` every travel distance. Both are **0** when the setting is off
(section 3), so a stylesheet rule needs no media query of its own.

### What v2 changed, and why

| Principle | v1 | v2 |
|---|---|---|
| **Fade and move are two animations.** A surface should be opaque well before it has stopped moving: that is what makes it feel quick, and the spring still lands softly | one animation did both, so a surface was still half transparent while it overshot | the fade takes 150-200 ms, the movement 260-340 ms (palette, dialog, rows, settings, tabs) |
| **Short, honest travel** | 26-34 px drops and 70 px popups, scales of 0.88-0.93 | 8-18 px and 0.94-0.97; popups 14 px instead of Firefox's 70 |
| **Overshoot you can feel, not see** | 12.6 % on the palette, dialogs and tabs | at most 4.6 % (the `settle` spring) |
| **No blur on anything large** | 10-14 px blur on the window, the palette and dialogs, rows blurred | no blur anywhere; a blur of a large area is the most expensive thing a compositor is asked to do |
| **Leave faster than you arrived** | a popup left in the time it took to arrive; the palette did not animate out | popups leave in 130 ms (arrive in 260 / 170 ms); the palette fades and lifts away in 130 ms; a tab leaves in 140 ms |
| **Cascades are short** | 34 ms steps, up to 11 steps | 22 ms steps, 6-7 steps; no cascade at all on context menus |
| **Press feedback springs back** | a press shrank and released in Zen's 0.1-0.2 s `ease` | the press is 110 ms, the release is a spring (toolbar buttons, tabs, the close button) |
| **The start-up plays once** | leaving full screen replayed it | the window records `nivora-booted` when it has assembled |

Rules of construction:

- Only `transform`, `opacity` and the individual `scale` property are animated (plus a brightness filter
  on the tab that was just selected), which a compositor can do without layout. Layout-affecting properties (margins, heights) are used in two places only, where the neighbors
  have to move: a tab opening or closing in the sidebar, and a folder expanding; both are Zen's design.
- An element that arrives in a list waits for the one before it, capped so a long list still finishes in
  well under half a second.
- Selectors start with `:root` (and repeat an id where Zen's selector has one) so they win over Zen's and
  Firefox's own transitions without `!important`. A test (`test_the_motion_rules_are_the_ones_that_apply`)
  checks that the rules which replace Zen's are the ones that apply: v1 had two rules, for toolbar buttons
  and for the tab close button, that never did.

## 2. Inventory

"Zen" is what Zen 1.23.4b / Firefox 158 does; "v1" and "v2" are Nivora's two versions. Durations are the
animation's own length (a delay is included where there is one), not the measured screen time (section 4).

| Surface | Zen | v1 | v2 | Where |
|---|---|---|---|---|
| Window at start | appears | 1.1 s, blurred, from the side | 520 ms (chrome) and 564 ms (content, 44 ms later), fade 340 / 384 ms, no blur; once per window | CSS `nivora-boot-*`, `nivora-booted` |
| Palette opens | 0.15-0.2 s fade | 640 ms, bouncy, blurred, 26 px | **340 ms** settle spring, 14 px, scale 0.965, fade 170 ms; rows follow, 22 ms apart, 260 ms | CSS `nivora-palette-in`, `nivora-row-in` |
| Palette selection | row background changes | a bar glides on a snappy spring; row leans 5 px; icon pops 1.16 | the same bar; row leans **3 px**; icon pops **1.1** | CSS + `NivoraMotion.sys.mjs` |
| Palette closes | instant | instant | **fades and lifts away in 130 ms** (a copy of the palette; the page is usable at once) | `NivoraMotion.sys.mjs` `PaletteExit`, CSS `nivora-palette-out` |
| App-menu panels, doorhangers | 70 px slide, 0.18 s both ways | 420 ms in and out | **260 / 170 ms in on a spring, 130 ms out**, 14 px travel; items of a menu view cascade 7 ms apart | CSS |
| Context menus | appear at once | every item cascaded in (a right-click menu took about 500 ms to open) | **appear at once, as in Zen**: a menu the user is waiting on, many times a day, gets no choreography | |
| Dialogs and tab prompts | 0.3 s fade | 640 ms bouncy, blurred | **340 ms** settle, 18 px, scale 0.96, fade 170 ms; the overlay fades in 260 ms | CSS `nivora-dialog-in` |
| Tab selected | background switches | pops (scale 0.955, brightness 1.35) on the bouncy spring | pops (scale 0.97, brightness 1.2) on the settle spring, 260 ms | CSS `nivora-tab-select` |
| Tab hover | background | label slides 2 px; close button springs in | the label slides 2 px on a plain ease-out (a spring jitters as the pointer crosses a list) | CSS |
| Tab pressed | shrinks 0.98 in 0.1 s | (Zen's) | shrinks in 110 ms, springs back in 260 ms; same for the icon and the close button | CSS |
| Tab opens / closes | 0.12 s / 0.1 s | 560 ms bouncy in / 200 ms out | **340 ms** settle in (fade 150 ms after 30 ms, the room opens in 240 ms) / **140 ms** out (the room closes in 170 ms after 40 ms): the item never overlaps its neighbour | `ZenVerticalTabsManager.mjs` |
| Toolbar buttons | 0.1 s hover, 0.2 s press | (never applied) | colour 170 ms; press 110 ms; release a 260 ms spring | CSS |
| Settings pane | none | 640 ms, 34 ms steps, 22 px | **340 ms** smooth, 12 px, fade 260 ms, 22 ms steps, every time a category is opened | CSS `nivora-card-in` |
| Compact-mode sidebar | 0.25 s reveal, 0.15 s hide, 0.1 s toggle | 420 ms, 220 ms, 340 ms | **340 ms** reveal, 170 ms hide, 340 ms toggle | `sidebar.inc.css`, `ZenCompactMode.mjs` |
| Folder expand / collapse | 0.18 s | 0.34 s | 0.34 s | `ZenFolders.mjs` |
| Space switch | 250 ms | 420 ms | **340 ms** | pref |
| Glance | 350 ms | 520 ms | **420 ms** | pref |
| Library | 0.3 s | 420 ms | **340 ms** | token |
| Toasts, downloads arc, split view, media controls, boosts editor | Zen's own | unchanged | unchanged: already springs, or short on purpose (drag feedback) | |

## 3. Budgets

The numbers above are held in place by [`browser_nivora_motion_budget.js`](../src/nivora/tests/browser/browser_nivora_motion_budget.js).
It reads the real animations out of the running window, scrubs each one frame by frame the way a 60 Hz
display would show it (pausing it and setting its time, then reading the computed transform, opacity and
filter), and measures. A number that drifts out of its budget fails the build instead of being noticed in a
screenshot months later.

| Budget | Limit |
|---|---|
| The palette's movement / its fade | 400 ms / 200 ms, and the fade ends before the movement |
| The palette's rows | each finishes within 520 ms, in order, one after the other, none blurred |
| A popup arriving | within 300 ms, on a spring; leaving takes at most 0.7 times as long |
| A tab opening / closing | within 400 ms / 220 ms; the close at most 0.7 times the open |
| A dialog | within 400 ms, no blur |
| A settings pane | the last group finishes within 600 ms |
| The start-up | about half a second (at most 600 ms), once per window |
| **Overshoot** of any scale or translation | at most **6 %** of the distance travelled |
| **Blur** | none |
| The palette's copy on its first frame | at most 1 % of its pixels differ from the palette (measured: 0.67 %) |

Other things it checks: the palette is a copy in the top layer, inert, hidden from assistive technology and
without the rows' entrance animations; typing in the palette starts no new animation on the palette; with
animations off there is no copy; a pressed toolbar button is smaller, by less than 10 %, and presses faster
than it releases.

## 4. Turning it off

- **Settings:** `nivora.ui.animations` = false (also in the settings schema, so it is exported and imported
  with the rest), or **Toggle Animations** in the command palette. It takes effect in every open window at once.
- **System:** the "reduce motion" setting (`prefers-reduced-motion`) does the same for the stylesheets.

With either, the scale and the lift are 0: every Nivora duration is 0 s and no element travels. For scripted
animations, `NivoraMotion.sys.mjs` sets the window's `gReduceMotionOverride`, the hook Firefox provides for
tests, so Firefox's and Zen's own scripted animations (`gReduceMotion`) stop too. It only undoes what it set.
The palette leaves no copy behind.

What stays when motion is off: Zen's and Firefox's CSS micro-transitions of 80-200 ms (hover colors, focus
rings). They are not decoration and some of them hide a state change; they are not touched.

## 5. What was measured

### 5.1 Scrubbed frames (v2)

The animations were paused and set to a chosen time at 60 Hz steps and the frames drawn with `drawWindow`,
which renders the window synchronously, so the frames do not depend on how fast the machine is. Contact sheets of the palette (opening and closing), a tab (opening and
closing), the window at start and a settings pane were looked at by Claude (they are not committed; they
come from a scratch test).

What the frames showed, and what was changed because of it:

- **Palette:** blank at 0 ms, the container and the first row visible at 50 ms, all rows in by 160 ms, still
  by 240 ms. In v1 the last rows were still arriving at about 800 ms.
- **Palette leaving:** the copy starts identical to the palette (0.67 % of the pixels differ by more than
  12/255 in a channel; probably the focus state) and is gone in 130 ms.
- **Tab opening:** the first version of v2 faded the tab in while its space was still opening, so for two
  frames it overlapped the tab below. The fade now starts 30 ms late and the space opens faster; the frames
  show no overlap. The same was done for closing (the space collapses 40 ms in, when the tab is nearly gone).
- **Settings:** header and first group at 60 ms, the rest cascading, complete by 300 ms.

### 5.2 Screen recording

Method ([`tools/nivora/motion_probe.py`](../tools/nivora/motion_probe.py)): the built browser runs under
Xvfb at 1260x810 with a fresh profile; `ffmpeg` records the screen at 30 frames per second while an
interaction is replayed with `xdotool`; the recording is decoded to small gray frames and, from the
difference between consecutive frames, the tool reports when the picture first changes, how long the motion
lasts, how many different frames were shown, and the longest time it stood still inside the motion.

Measured on 2026-10-27, one run per cell. "Duration" is the time from the first to the last visible change,
"frames" the number of distinct frames shown inside it, "still" the longest stretch inside the motion in
which the picture did not change. v1 and Zen's baseline are the earlier measurements.

| Interaction | Zen (baseline) | v1 | **v2** | v2, animations off |
|---|---|---|---|---|
| Palette opens | 233 ms, 3 frames, still ≤ 167 ms | 900 ms, 16 frames, still ≤ 200 ms | **567 ms, 10 frames, still ≤ 233 ms** | 233 ms, 3 frames, still ≤ 167 ms |
| Palette closes | 67 ms, 2 frames, still ≤ 33 ms | 33 ms, 1 frame, still ≤ 33 ms | **100 ms, 3 frames, still ≤ 33 ms** (new: it animates out) | not measured |
| Tab selected (click) | 133 ms, 4 frames, still ≤ 33 ms | 233 ms, 6 frames, still ≤ 67 ms | **200 ms, 5 frames, still ≤ 67 ms** | not measured |
| Tab closed (Ctrl+W) | 133 ms, 4 frames, still ≤ 33 ms | 233 ms, 7 frames, still ≤ 33 ms | **200 ms, 6 frames, still ≤ 33 ms** | 33 ms, 1 frame, still ≤ 33 ms |
| Tab opened (Enter in the palette) | not measured | 267 ms, 7 frames, still ≤ 67 ms | **100 ms, 2 frames, still ≤ 67 ms** | 33 ms, 1 frame, still ≤ 33 ms |
| New tab (Ctrl+T: the tab and the palette) | not measured | not measured | 567 ms, 14 frames, still ≤ 133 ms | not measured |
| Main menu | 167 ms, 4 frames, still ≤ 67 ms | 500 ms, 11 frames, still ≤ 133 ms | **300 ms, 7 frames, still ≤ 67 ms** | 167 ms, 4 frames, still ≤ 67 ms |
| Tab context menu | 133 ms, 3 frames, still ≤ 67 ms | 500 ms, 14 frames, still ≤ 67 ms | **200 ms, 5 frames, still ≤ 67 ms** | not measured |
| Settings category switched | not measured | 1367 ms, 29 frames, still ≤ 300 ms | 1367 ms, 21 frames, still ≤ 633 ms | 1400 ms, 14 frames, still ≤ 867 ms |
| Sidebar toggled (Ctrl+B) | 167 ms, 4 frames, still ≤ 67 ms | 167 ms, 3 frames, still ≤ 100 ms | 167 ms, 4 frames, still ≤ 67 ms | not measured |
| Window starting | not measured | 1933 ms, 26 frames, still ≤ 800 ms | 2267 ms, 24 frames, still ≤ 1200 ms | not measured |

What the numbers say, and what they do not:

- **Shorter, as intended.** The palette opening went from 900 to 567 ms, a tab opening from 267 to 100 ms, the
  main menu from 500 to 300 ms and a right-click menu from 500 to 200 ms; closing and selecting a tab went from
  233 to 200 ms. v2 still shows several times as many distinct frames as Zen's own motion (the palette 10 against 3,
  the main menu 7 against 4): the motion is shorter than v1, not absent.
- **The palette now animates out** (100 ms, 3 frames, against 33 ms and one frame in v1). That is the 130 ms
  exit of section 2, seen by the recorder.
- **The context menu is slower than Zen's own** (200 against 133 ms) although v2 adds nothing to it; a
  difference of two frames is above the noise of this method and is not explained. Nothing in v2 touches a
  context menu's items.
- **Not better by this measure:** the settings category switch (1367 ms either way) and the window start (2267
  against 1933 ms). Both recordings are dominated by loading and painting a page in software rendering, and the
  still stretches inside them are longer in v2, so these rows say nothing for or against v2's animations.
  The animations themselves are shorter (340 ms for a pane, 520 ms for the start-up, section 2) and were
  checked frame by frame instead (section 5.1).
- With the setting off, the same interactions go back to Zen's own timing (palette 233 ms and 3 frames, the main
  menu 167 ms, a closed or opened tab 33 ms, one frame). Nivora's motion is gone, not just shorter.
- One run per cell; differences of one frame (33 ms) are noise. Changes to compact mode, folders, space
  switching, glance and the Library are implemented, and Zen's test groups for them pass (section 6), but
  **their motion was not measured**.

**Caveats, all of them real.** The browser is software-rendered in this environment, so absolute frame
counts are far lower than a GPU would show and nothing here is a claim about smoothness on real hardware;
the numbers compare builds on one machine. A screen recording at 30 fps cannot see a 130 ms motion in more
than four frames. A page whose content changes (a tab switch) is dominated by that change. Neither the
probe nor the scrubbing measures how an animation *feels*; the contact sheets were looked at by Claude, not
by a designer.

## 6. How it is checked

| Check | What it covers |
|---|---|
| `tools/nivora/tests/test_generate_motion.py` (8) | shape of every spring, each inside its overshoot band, the generated file equals the generator's output |
| `tools/nivora/js-tests/nivora-motion.test.mjs` (3) | where the palette highlight goes |
| `tools/nivora/tests/test_check_contrast.py` | the token parser ignores the `@media` overrides of the motion tokens |
| `tools/nivora/tests/test_motion_probe.py` (7) | the probe's frame arithmetic and scenarios |
| `browser_nivora_motion.js` (11 tests) | tokens defined; setting off zeroes durations and travel; the system's reduced motion does too; the palette's entrance and gliding highlight (position, height, **color equals Zen's selected row**); the glide stops when the setting is turned off while the palette is open; the off switch reaches `gReduceMotion`; tabs open and close with the right animations and clean up after themselves; a settings pane cascades |
| `browser_nivora_motion_budget.js` (11 tests) | section 3, plus: every rule that replaces one of Zen's applies; the start-up is not replayed |
| `browser_nivora_commands.js` | Toggle Animations flips the setting and back |
| Zen's own groups touched by the changes | `compact_mode` 13, `folders` 135, `tabs` 32, `urlbar` 97, `ub-actions` 92, `ui` 59, `glance` 27, `library` 224, `spaces` 112, `pinned` 70, `split_view` 124: **all pass** (`spaces` needs an Xvfb screen of 1600x1000: `browser_overflow_scrollbox.js` fails at the default size and at 1280x1024, on the committed v1 as well, see [TESTING.md](TESTING.md)). Under test automation Zen skips its tab animations, so those tests do not exercise the tab animations; the budget test does |
| CI | `generate_motion.py --check` |

Two visual checks caught what no test would have: the first version of the highlight took its color from a
Firefox variable that is blue in this theme (a test now compares it with Zen's selected row), and the first
version of the v2 tab animation overlapped the tab below it for two frames.

## 7. Not done, and why

- **Context menus are deliberately not animated** (v1 cascaded their items and a right-click menu took about
  half a second to open). Firefox's arrow panels (the app menu, the downloads panel, doorhangers) are. Where
  the platform cannot move a panel, only the fade runs (`-moz-panel-animations` is false in the test
  environment, so the 14 px of travel was **not exercised in a test**; it was not established on which real
  sessions that media feature is true).
- **No measurement on a GPU, and no comparison with unmodified Zen** (the same limits as the performance
  baseline in [TESTING.md](TESTING.md)). Nothing here says how the motion looks at 144 Hz.
- **Zen's own JavaScript animations** (toasts, the download arc, the Library's media preview, boosts, drag
  and drop, split view) were reviewed and left alone except where listed; changing them would diverge from
  upstream for little gain.
- **The palette's copy** is a plain element holding clones of the urlbar's children, not a clone of the urlbar:
  the urlbar is a custom element and a clone of it would be a second, uninitialised address field (the first
  attempt did exactly that and logged an exception). It differs from the palette in 0.67 % of its first
  frame's pixels; the focus ring is the likely cause and is not reproduced.
- **A flake in the browsing tests:** one full run of `browser_nivora_browsing.js` lost characters typed into a
  form ("N" instead of "Nivora"); the file passed in two reruns. It does not touch animations, but the run
  was under the new motion, so it is recorded here.

## 8. Visual polish (still part of v2, not yet built or looked at)

[`nivora-polish.inc.css`](../src/nivora/theme/nivora-polish.inc.css) adds what things look like at rest and
under the pointer. Same rules as the motion file: roles and motion tokens only, `:root` first, nothing
that depends on the structure of Zen's UI beyond class and id names Zen styles itself. The new tokens
(`--nivora-hairline`, `-strong`, `--nivora-sheen`, `--nivora-glow`, `--nivora-hover-fill`, `--nivora-press-fill`,
`--nivora-elevation`, `--nivora-d-ambient`) are in `nivora-tokens.inc.css`.

| Surface | What changed |
|---|---|
| Scrollbars | thin, graphite thumb, no track (`scrollbar-width`, `scrollbar-color`) |
| Tabs | a 1 px outline (no layout) in `hairline` on hover and `hairline-strong` when selected, faded in 260 ms; the favicon grows 8 % under the pointer; a loading tab's icon breathes on an 1800 ms loop (`[busy]`) |
| Tab close / new tab | the close button turns a quarter into place on a settle spring; the new-tab plus turns 90 degrees on hover |
| Essentials | rise 1 px on hover, sink on press |
| Space icons | grow 10 % on hover, shrink 6 % on press (springs); the active one has a dot |
| Address bar | hairline on hover, a brighter one plus a 3 px halo when focused |
| Command palette | a light edge on top and `--nivora-elevation`, the system's only shadow |
| Palette rows | the row under the pointer, not just the keyboard, gets `hover-fill` |
| Toolbar buttons | the icon grows 10 % on hover and shrinks 6 % on press, apart from the button's own press |
| Menus | the icon of the entry under the pointer or keyboard nudges 2 px |
| Keyboard focus | the ring draws itself in over 170 ms (`nivora-focus-in`) |

With the animations setting off, `--nivora-lift` and `--nivora-motion-scale` are 0: nothing moves, the loop
has no length, and the hairlines and fills stay.

Second round, same file: `--zen-big-shadow` (used by the glance, the split-view panes, the compact sidebar and
the download arc) takes `--nivora-elevation`; sidebar notifications and the media controls wear a hairline; split-view
panes move on the smooth spring (340 ms) and the panes without the keyboard get a hairline; the drop preview of a
split and the Essentials drop zone become dashed hairlines that fade in; the tab list of a folder highlights on
hover and cascades in.

**Status.** Built and looked at (2026-10-29): the first build was run on a laptop screen and screenshots of the main window,
the palette, the settings and a page were looked at; the tab outline, the palette's hairline and the settings changes showed
as intended, and the palette's exit was caught half way in a frame. **Not seen** (a still image cannot show motion): the
close button's turn, the new-tab plus, the hover growth of icons, the favicon growth, the spaces' hover and the focus ring
drawing in. The static checks (unit tests, contrast, spring generator) pass; no browser test was written for these rules.
Two defects the screenshots found: a black shadow cannot be seen on this dark page (fixed in section 9), and the
"managed by your organization" notice in the settings, caused by the update policy of `policies.json`, is not fixed.

## 9. Third round: settings, new tab, loading

- **Settings page** ([`nivora-settings.inc.css`](../src/nivora/theme/nivora-settings.inc.css)). Not shown: the *Account and
  sync* and *Mods* categories (their buttons are hidden by CSS: the settings redesign forces the Sync button visible, so no
  preference hides it) and, inside the Sync pane, the account, sync, backup, profiles and referrals groups. The pane stays
  reachable as `about:preferences#sync` with only *Import data* and the default-browser prompt, which is the one place the import
  wizard is offered. Shown: cards and boxes with a hairline and a light top edge; links in the text color, underlined; the
  navigation highlights from the roles and its categories arrive one after another; switches are a graphite track with a white
  "on" state, their dot slides on the `settle` spring and stretches while pressed; buttons press on a spring.
- **New tab background** (`nivora-polish.inc.css`, `tools/nivora/generate_newtab.py`). An original image, a total eclipse (black
  disc, thin corona, one faint ring, vignette), generated from the neutral palette, 2560 x 1440 WebP, about 20 KiB. Zen's new tab
  is a blank page (`about:blank`) over Zen's own background of the `browser` element, so the image is that element's background
  while the selected tab is the empty one (`:root[zen-has-empty-tab="true"]`), and it fades in when the tab opens.
  Firefox's own new tab was not used: it is a built bundle and its wallpapers come from Mozilla's servers. A user sheet was tried
  first and dropped: it is registered per document and `about:blank` is shared by many frames. `nivora.ui.newtab-background` =
  false takes it away (it is in the settings schema).
- **Loading.** A band of light sweeps across a loading tab (`[busy]`) on a 2.5 s loop, together with the icon's breathing.
- **Elevation** carries a hairline and a faint outer glow: the first build showed that a black shadow cannot be seen on a page
  this dark.

**Status of this round.** Built and looked at on the same laptop screen, through Marionette: the settings navigation without
Account/Sync/Mods, Look and Feel as the landing pane, the cards of Zen's panes, the dimmed layout thumbnails, the new tab with its
background and the palette over it, and a loading tab being swept (the sweep was seen in three frames, with the color of
`--nivora-glow`; the first version, with `--nivora-sheen`, was too faint to see). **Not seen:** the settings navigation's
entrance, the switches' dot spring and stretch, the buttons' press, because a still image cannot show them. Switches were not
on screen in any pane that was opened.
