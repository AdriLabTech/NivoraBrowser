# Animations

Motion is part of what Nivora is for. Zen already animates a lot, but most of it is short (80-200 ms) and
tuned to stay out of the way. Nivora's rule is the opposite: **every state change is shown, with a motion
that has character** - things arrive with a spring, settle, and leave quickly - and the whole interface
uses one motion language, so it reads as one product.

This page is the inventory, the language, the way to turn it off, and what was measured. Statuses follow
the rest of the documentation: *implemented* (in the tree), *built* (in the binary), *tested* (a test or
measurement ran), *looked at* (a person, or Claude, viewed the frames).

## 1. The language

Everything comes from tokens in [`nivora-tokens.inc.css`](../src/nivora/theme/nivora-tokens.inc.css); no
rule hard-codes a duration or a curve.

| Token | Value | Used for |
|---|---|---|
| `--nivora-d-micro` | 140 ms | a hover, a pressed state |
| `--nivora-d-fast` | 220 ms | a color or opacity change, a menu item |
| `--nivora-d-base` | 420 ms | a spring that settles: rows, tabs, buttons, panels |
| `--nivora-d-slow` | 640 ms | a surface arriving: the palette, a dialog, a settings pane |
| `--nivora-d-cinematic` | 1100 ms | the window assembling itself at start |
| `--nivora-stagger` / `-tight` | 34 ms / 15 ms | the step between items of a cascade |
| `--nivora-ease-out` / `-in` / `-in-out` | expo-out, in, in-out | arrivals, departures, symmetric moves |
| `--nivora-spring-smooth` | damping 1.0, **0 %** overshoot | large surfaces: no bounce |
| `--nivora-spring-snappy` | damping 0.8, **1.5 %** | buttons, rows, selection |
| `--nivora-spring-bouncy` | damping 0.55, **12.6 %** | menus, the palette, dialogs |
| `--nivora-spring-elastic` | damping 0.38, **27.4 %** | rare confirmations (defined, unused so far) |

The spring curves are **generated**, not guessed: [`tools/nivora/generate_motion.py`](../tools/nivora/generate_motion.py)
solves the step response of a damped spring and writes 48 samples as a CSS `linear()` easing into
`nivora-springs.inc.css`. The duration of a transition that uses one is the time the spring takes to settle
(within 0.5 %). A unit test checks the shape (starts at 0, ends at exactly 1, never overshoots when critically
damped, overshoots more as damping falls) and CI fails if the generated file is stale.

Two more tokens make motion switchable without every rule knowing about it: `--nivora-motion-scale`
multiplies every duration and `--nivora-lift` every travel distance. Both are **0** when the setting is off
(section 3), so a stylesheet rule needs no media query of its own.

Rules of construction:

- Only `transform`, `opacity` and `filter` are animated, so a compositor can do it without layout.
  Layout-affecting properties (margins, heights) are used in two places only, where the neighbors have to
  move: a tab opening or closing in the sidebar, and a folder expanding; both are Zen's design.
- Blur is used on the *arrival* of the three biggest surfaces (window, palette, dialog) and clears within
  the first half of the motion, so the blurred area is large only for a few frames.
- An element that arrives in a list waits for the one before it (a cascade of 15-34 ms steps), capped so a
  long list still finishes in well under half a second.
- Selectors start with `:root` so they win over Zen's and Firefox's own transitions without `!important`.

## 2. Inventory

"Before" is what Zen 1.23.4b / Firefox 158 does; "Now" is Nivora. Durations are the animation's own length,
not the measured screen time (section 4).

| Surface | Before | Now | Where |
|---|---|---|---|
| Window at start | appears | chrome slides in from the left, content rises, both from blur, 1.1 s smooth spring | CSS `nivora-boot-*` |
| Command palette opens | 0.15-0.2 s fade | drops in from above with a bouncy spring and blur (640 ms); rows follow one by one | CSS `nivora-palette-in`, `nivora-row-in` |
| Palette selection | row background changes | **a highlight bar glides between rows on a snappy spring**; the row leans in 5 px and its icon pops | CSS + `NivoraMotion.sys.mjs` |
| Palette closes | instant (Zen hides the popover at once) | unchanged - see section 6 | |
| Menus, app menu, context menus | 70 px slide, items static | softer arrival on a snappy spring; items cascade in from the top, 15 ms apart | CSS `nivora-item-in` |
| Panels (downloads, doorhangers) | slide | same spring as menus | CSS |
| Dialogs and tab prompts | 0.3 s fade | drops in on the bouncy spring with blur; the overlay fades separately | CSS `nivora-dialog-in` |
| Tab selected | background switches | background pops (scale and brightness) on the bouncy spring | CSS `nivora-tab-select` |
| Tab hover | background | background and label slide 2 px; close button springs in | CSS |
| Tab opens / closes | 0.12 s / 0.1 s ease-out | 560 ms spring in from the side / 200 ms out; the space opens and closes on its own curve | `ZenVerticalTabsManager.mjs` |
| Toolbar buttons | 0.1 s | hover and press on the bouncy spring | CSS |
| Settings pane | none | header then each group rises in, 34 ms apart, every time a category is opened | CSS `nivora-card-in` |
| Compact-mode sidebar | 0.25 s reveal, 0.15 s hide, 0.1 s toggle | 420 ms spring reveal, 220 ms hide, 340 ms toggle | `sidebar.inc.css`, `ZenCompactMode.mjs` |
| Folder expand / collapse | 0.18 s | 0.34 s | `ZenFolders.mjs` |
| Space switch | 250 ms | 420 ms | pref |
| Glance | 350 ms | 520 ms | pref |
| Library | 0.3 s | 420 ms | token |
| Toasts, downloads arc, split view, media controls, boosts editor | Zen's own | unchanged: already springs, or short on purpose (drag feedback) | |

## 3. Turning it off

- **Settings:** `nivora.ui.animations` = false (also in the settings schema, so it is exported and imported
  with the rest), or **Toggle Animations** in the command palette. It takes effect in every open window at once.
- **System:** the "reduce motion" setting (`prefers-reduced-motion`) does the same for the stylesheets.

With either, the scale and the lift are 0: every Nivora duration is 0 s and no element travels. For scripted
animations, `NivoraMotion.sys.mjs` sets the window's `gReduceMotionOverride`, the hook Firefox provides for
tests, so Firefox's and Zen's own scripted animations (`gReduceMotion`) stop too. It only undoes what it set.

What stays when motion is off: Zen's and Firefox's CSS micro-transitions of 80-200 ms (hover colors, focus
rings). They are not decoration and some of them hide a state change; they are not touched.

## 4. What was measured

Method ([`tools/nivora/motion_probe.py`](../tools/nivora/motion_probe.py)): the built browser runs under
Xvfb at 1260x810 with a fresh profile; `ffmpeg` records the screen at 30 frames per second while an
interaction is replayed with `xdotool`; the recording is decoded to small gray frames and, from the
difference between consecutive frames, the tool reports when the picture first changes, how long the motion
lasts, how many different frames were shown, and the longest time it stood still inside the motion. A
contact sheet of the frames is saved for looking at.

Measured on 2026-10-27, one run per cell. "Duration" is the time from the first to the last visible change,
"frames" the number of distinct frames shown inside it, "still" the longest stretch inside the motion in
which the picture did not change.

| Interaction | Baseline (Zen as inherited) | Nivora | Nivora, animations off |
|---|---|---|---|
| Palette opens | 233 ms, 3 frames, still ≤ 167 ms | 900 ms, 16 frames, still ≤ 200 ms | 233 ms, 2 frames, still ≤ 200 ms |
| Palette closes | 67 ms, 2 frames, still ≤ 33 ms | 33 ms, 1 frames, still ≤ 33 ms | not measured |
| Tab selected (click) | 133 ms, 4 frames, still ≤ 33 ms | 233 ms, 6 frames, still ≤ 67 ms | not measured |
| Tab closed (Ctrl+W) | 133 ms, 4 frames, still ≤ 33 ms | 233 ms, 7 frames, still ≤ 33 ms | 33 ms, 1 frames, still ≤ 33 ms |
| Tab opened (Enter in the palette) | not measured | 267 ms, 7 frames, still ≤ 67 ms | 67 ms, 2 frames, still ≤ 33 ms |
| Main menu | 167 ms, 4 frames, still ≤ 67 ms | 500 ms, 11 frames, still ≤ 133 ms | 200 ms, 4 frames, still ≤ 67 ms |
| Tab context menu | 133 ms, 3 frames, still ≤ 67 ms | 500 ms, 14 frames, still ≤ 67 ms | not measured |
| Settings category switched | not measured | 1367 ms, 29 frames, still ≤ 300 ms | 1367 ms, 13 frames, still ≤ 900 ms |
| Sidebar toggled (Ctrl+B) | 167 ms, 4 frames, still ≤ 67 ms | 167 ms, 3 frames, still ≤ 100 ms | not measured |
| Window starting | not measured | 1933 ms, 26 frames, still ≤ 800 ms | not measured |

What the numbers say, and what they do not:

- The palette, the menus and tab closing last two to four times longer than the baseline and show several
  times as many distinct frames: that is the added motion, and it is what the contact sheets show (the
  palette dropping in from blur, its rows arriving one by one; a menu opening top to bottom; a settings pane
  assembling card by card; the tab fading and stepping aside).
- With the setting off, the same interactions go back to Zen's own timing (palette 233 ms and 2 frames, the
  same as the baseline; the main menu 200 ms against 167 ms; a closed tab 33 ms; a settings pane switches in
  one step and stays still). Nivora's motion is gone, not just shorter.
- **The palette closing is not animated** (33 ms, one frame) and **the sidebar toggle is unchanged** (167 ms,
  as in the baseline): both are listed as not done in section 6.
- The settings and boot rows include loading and painting, not only the animation, so their durations are
  upper bounds. The baseline of the settings switch was not measured (the first scenario did not load the page).
- The window-start recording shows the motion over about 1.9 s, with a still stretch of 0.8 s inside it:
  the window is painted in steps while the browser starts, so a software-rendered start does not look like
  the 1.1 s spring the stylesheet describes.
- Changes to compact mode, folders, space switching, glance and the Library are implemented, and Zen's test
  groups for them pass (section 5), but **their motion was not measured**.


"Baseline" is the same build before Nivora's motion went in (measured earlier in the same session);
"off" repeats the interaction with `nivora.ui.animations` = false. Differences of one frame (33 ms) are noise.

**Caveats, all of them real.** The browser is software-rendered in this environment, so absolute frame
counts are far lower than a GPU would show and nothing here is a claim about smoothness on real hardware;
the numbers compare two builds on one machine. A screen recording at 30 fps cannot see a 150 ms motion in
more than four or five frames. A page whose content changes (a tab switch) is dominated by that change. The
probe does not measure how an animation *feels*; the contact sheets were looked at by Claude, not by a
designer.

## 5. How it is checked

| Check | What it covers |
|---|---|
| `tools/nivora/tests/test_generate_motion.py` (8) | shape of every spring, the generated file equals the generator's output |
| `tools/nivora/js-tests/nivora-motion.test.mjs` (3) | where the palette highlight goes |
| `tools/nivora/tests/test_check_contrast.py` | the token parser ignores the `@media` overrides of the motion tokens |
| `tools/nivora/tests/test_motion_probe.py` (7) | the probe's frame arithmetic and scenarios (each "off" scenario repeats one with the setting off) |
| `browser_nivora_motion.js` (11 tests) | tokens defined; setting off zeroes durations and travel; the system's reduced motion does too; tab springs; the palette's entrance and gliding highlight (position, height, **color equals Zen's selected row**, row background hidden); the glide stops when the setting is turned off while the palette is open; the off switch reaches `gReduceMotion`; tabs open and close with the right animations and clean up after themselves; a settings pane cascades |
| `browser_nivora_commands.js` | Toggle Animations flips the setting and back |
| Zen's own groups touched by the changes | `compact_mode` 13, `folders` 135, `tabs` 32, `urlbar` 97, `ub-actions` 92 (it formats every palette action, which is how a missing translation was caught), `ui` 59, `glance` 27, `library` 224, `spaces` 112, `pinned` 70: **all pass** (one run of `library` failed 7 checks in two timing-sensitive tests while the machine was busy with other work; two clean reruns passed; see [TESTING.md](TESTING.md)). Under test automation Zen skips its tab animations, so the tab tests do not exercise the new ones; `browser_nivora_motion.js` does |
| CI | `generate_motion.py --check` |

A visual check caught what none of these tests would have: the first version of the highlight took its color
from a Firefox variable that is blue in this theme. The test that compares it with Zen's selected row now
exists because of that.

## 6. Not done, and why

- **The palette does not animate out.** Zen hides the palette's popover synchronously and removes the
  floating layout in the same step, so there is nothing left to animate. A real exit needs a change inside
  Firefox's urlbar close path (`UrlbarInputBase-mjs.patch`) or a clone of the palette; both are invasive and
  would put Zen's urlbar tests at risk. Left as it is.
- **Exiting full screen replays the window's boot motion of the toolbox** (the rule is keyed on the
  full-screen attribute not being set). It is short enough to read as the toolbar coming back.
- **No measurement on a GPU, and no comparison with unmodified Zen** (the same limits as the performance
  baseline in [TESTING.md](TESTING.md)).
- **Blur cost** was not measured separately. If a low-end GPU struggles with the palette, lower the blur in
  the `nivora-palette-in` and `nivora-dialog-in` keyframes first.
- **Zen's own JavaScript animations** (toasts, the download arc, the Library's media preview, boosts, drag
  and drop, split view) were reviewed and left alone except where listed; changing them would diverge from
  upstream for little gain.
