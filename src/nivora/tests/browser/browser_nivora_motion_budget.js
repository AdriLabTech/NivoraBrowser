/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

/**
 * Budgets for the motion language (docs/ANIMATIONS.md, "Budgets"). Each surface's real animations are
 * read from the running window, scrubbed frame by frame the way a 60 Hz display would show them, and
 * measured: how long they take, how far they overshoot, whether anything large is blurred, whether
 * the exit is quicker than the entrance. A number that drifts out of its budget fails here, not in a
 * screenshot someone looks at months later.
 */

const ANIMATIONS = "nivora.ui.animations";
const FPS = 60;

const BUDGET = {
  // Time from the first frame to the last, in milliseconds.
  paletteMove: 400,
  paletteFade: 200,
  paletteRows: 520,
  tabOpen: 400,
  tabClose: 220,
  dialog: 400,
  settings: 600,
  // A departure takes at most this share of the matching arrival.
  exitShare: 0.7,
  // How far past its destination anything may travel, as a share of the distance it travels.
  overshoot: 0.06,
  // Of the pixels under a palette, the share that may differ between the palette and its ghost.
  ghostDifference: 0.01,
};

const nextFrames = n =>
  new Promise(resolve => {
    const step = left => (left ? requestAnimationFrame(() => step(left - 1)) : resolve());
    step(n);
  });

const endOf = animation => animation.effect.getComputedTiming().endTime;
const animates = (animation, property) => animation.effect.getKeyframes().some(k => property in k);
// A CSS animation's timing function belongs to its keyframes; a script's, to its timing.
const easingOf = animation => String(animation.effect.getKeyframes()[0]?.easing ?? animation.effect.getTiming().easing);

function readStyle(win, target) {
  const style = win.getComputedStyle(target);
  let matrix;
  try {
    matrix = new win.DOMMatrix(style.transform === "none" ? undefined : style.transform);
  } catch (e) {
    matrix = { e: 0, f: 0, a: 1, d: 1 };
  }
  const blur = /blur\(([\d.]+)px\)/.exec(style.filter || "");
  return {
    opacity: parseFloat(style.opacity),
    tx: matrix.e,
    ty: matrix.f,
    scale: matrix.a,
    blur: blur ? parseFloat(blur[1]) : 0,
  };
}

/** The values of `animation`'s target at each frame of a 60 Hz display, then at its last instant. */
async function scrub(animation, win = window) {
  const target = animation.effect.target;
  const end = endOf(animation);
  const samples = [];
  animation.pause();
  for (let t = 0; t < end; t += 1000 / FPS) {
    animation.currentTime = t;
    await new Promise(resolve => win.requestAnimationFrame(resolve));
    samples.push(readStyle(win, target));
  }
  animation.currentTime = end;
  await new Promise(resolve => win.requestAnimationFrame(resolve));
  samples.push(readStyle(win, target));
  return samples;
}

/** How far `key` goes past where it ends, as a share of the distance from where it started. */
function overshootOf(samples, key) {
  const start = samples[0][key];
  const end = samples[samples.length - 1][key];
  const span = end - start;
  if (Math.abs(span) < 1e-6) {
    return 0;
  }
  const direction = Math.sign(span);
  return Math.max(0, ...samples.map(s => (s[key] - end) * direction)) / Math.abs(span);
}

const withinBudget = (samples, label) => {
  for (const key of ["scale", "ty", "tx"]) {
    Assert.lessOrEqual(overshootOf(samples, key), BUDGET.overshoot, `${label}: ${key} stays within ${BUDGET.overshoot * 100}% overshoot`);
  }
  Assert.equal(Math.max(...samples.map(s => s.blur)), 0, `${label}: nothing is blurred`);
};

async function openRows(count) {
  const tabs = [];
  for (let i = 0; i < count; i++) {
    tabs.push(await BrowserTestUtils.openNewForegroundTab(gBrowser, `data:text/html,<title>nvbudget ${i}</title>${i}`));
  }
  return tabs;
}

async function openPalette() {
  gURLBar.focus();
  gURLBar.value = "% nvbudget";
  gURLBar.startQuery({ searchString: "% nvbudget" });
  await TestUtils.waitForCondition(
    () => gURLBar.hasAttribute("open") && gURLBar.getAttribute("zen-floating-urlbar") === "true",
    "the palette opens"
  );
  await TestUtils.waitForCondition(() => gURLBar.querySelectorAll(".urlbarView-row").length >= 3, "it lists the tabs");
}

function closePalette() {
  gURLBar.view.close();
  gURLBar.blur();
}

function finishAll(root) {
  for (const animation of root.getAnimations({ subtree: true })) {
    animation.finish();
  }
}

add_task(async function test_the_palette_entrance_meets_its_budget() {
  const tabs = await openRows(5);
  await openPalette();

  const own = gURLBar.getAnimations().filter(a => a.effect.target === gURLBar);
  const move = own.find(a => a.animationName === "nivora-palette-in");
  const fade = own.find(a => a.animationName === "nivora-fade-in");
  Assert.ok(move && fade, "the palette moves and fades in as two animations");
  Assert.lessOrEqual(endOf(move), BUDGET.paletteMove, "the movement fits its budget");
  Assert.lessOrEqual(endOf(fade), BUDGET.paletteFade, "the fade fits its budget");
  Assert.less(endOf(fade), endOf(move), "the palette is opaque before it has finished settling");
  Assert.ok(easingOf(move).startsWith("linear("), "on a spring");

  // The rows are read before the palette is scrubbed: their entrances are over in half a second.
  const rows = [...gURLBar.querySelectorAll(".urlbarView-row")];
  const rowAnimations = rows.flatMap(r => r.getAnimations().filter(a => a.effect.target === r));
  Assert.greaterOrEqual(rowAnimations.length, rows.length, "every row has an entrance");
  for (const animation of rowAnimations) {
    Assert.lessOrEqual(endOf(animation), BUDGET.paletteRows, "a row finishes inside the budget");
    Assert.ok(!animates(animation, "filter"), "and is not blurred");
  }
  const delays = rows
    .slice(0, 6)
    .map(r => r.getAnimations().find(a => animates(a, "transform"))?.effect.getTiming().delay);
  Assert.deepEqual([...delays].sort((a, b) => a - b), delays, "each row waits for the one before it");
  Assert.greater(delays[delays.length - 1], delays[0], "so they arrive one after another");

  const samples = await scrub(move);
  withinBudget(samples, "palette");
  Assert.less(samples[0].scale, 1, "it starts a little smaller");
  Assert.less(samples[0].ty, 0, "and a little higher");

  finishAll(gURLBar);
  closePalette();
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

add_task(async function test_typing_in_the_palette_does_not_replay_its_entrance() {
  const tabs = await openRows(4);
  await openPalette();
  finishAll(gURLBar);
  await nextFrames(3);
  const seen = new Set(gURLBar.getAnimations());
  for (const ch of "bu") {
    EventUtils.synthesizeKey(ch);
    await new Promise(resolve => setTimeout(resolve, 300));
    const fresh = gURLBar.getAnimations().filter(a => !seen.has(a) && a.effect.target === gURLBar);
    Assert.equal(fresh.length, 0, `typing '${ch}' starts no new animation on the palette itself`);
    gURLBar.getAnimations().forEach(a => seen.add(a));
  }
  closePalette();
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

/** The pixels of a window region, as RGBA. */
function snapshot(rect) {
  const canvas = document.createElementNS("http://www.w3.org/1999/xhtml", "canvas");
  canvas.width = Math.ceil(rect.width);
  canvas.height = Math.ceil(rect.height);
  const context = canvas.getContext("2d");
  context.drawWindow(window, rect.left, rect.top, canvas.width, canvas.height, "rgb(255,255,255)");
  return context.getImageData(0, 0, canvas.width, canvas.height).data;
}

function differingShare(a, b) {
  let differing = 0;
  for (let i = 0; i < a.length; i += 4) {
    const delta = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
    if (delta > 12) {
      differing++;
    }
  }
  return differing / (a.length / 4);
}

add_task(async function test_the_palette_leaves_as_a_copy_that_fades_away() {
  const tabs = await openRows(4);
  await openPalette();
  finishAll(gURLBar);
  await nextFrames(4);
  const rect = gURLBar.getBoundingClientRect();
  const before = snapshot(rect);
  const rowCount = gURLBar.querySelectorAll(".urlbarView-row").length;

  closePalette();
  // The observer runs before the next frame is painted: the copy exists from the first frame on.
  await Promise.resolve();
  const ghost = document.querySelector(".nivora-palette-ghost");
  Assert.ok(ghost, "a copy of the palette is left behind");
  Assert.equal(ghost.querySelectorAll(".urlbarView-row").length, rowCount, "with the rows that were on screen");
  Assert.ok(ghost.matches(":popover-open"), "in the top layer like the palette was");
  Assert.equal(ghost.getAttribute("aria-hidden"), "true", "hidden from assistive technology");
  Assert.ok(ghost.hasAttribute("inert"), "and inert");

  const exit = ghost.getAnimations().find(a => a.animationName === "nivora-palette-out");
  Assert.ok(exit, "it leaves with the exit animation");
  const entrance = 340;
  Assert.lessOrEqual(endOf(exit), entrance * BUDGET.exitShare, "which is quicker than the entrance");
  Assert.ok(!ghost.querySelector(".urlbarView-row").getAnimations().length, "and the rows of the copy do not enter again");

  exit.pause();
  exit.currentTime = 0;
  await nextFrames(2);
  const first = snapshot(rect);
  const difference = differingShare(before, first);
  info(`the copy's first frame differs from the palette in ${(difference * 100).toFixed(3)} % of its pixels`);
  Assert.less(difference, BUDGET.ghostDifference, "on its first frame the copy looks like the palette did");

  exit.currentTime = endOf(exit) / 2;
  const midway = readStyle(window, ghost);
  Assert.less(midway.opacity, 1, "it fades");
  Assert.less(midway.ty, 0, "and lifts");
  exit.play();
  await TestUtils.waitForCondition(() => !document.querySelector(".nivora-palette-ghost"), "the copy removes itself");
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

add_task(async function test_there_is_no_copy_when_animations_are_off() {
  const tabs = await openRows(4);
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  try {
    await openPalette();
    closePalette();
    await Promise.resolve();
    await nextFrames(2);
    Assert.ok(!document.querySelector(".nivora-palette-ghost"), "the palette just goes");
  } finally {
    await SpecialPowers.popPrefEnv();
    // The scale is restyled a moment after the preference changes.
    await TestUtils.waitForCondition(
      () => getComputedStyle(document.documentElement).getPropertyValue("--nivora-motion-scale").trim() === "1",
      "motion is back on"
    );
    tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
  }
});

add_task(async function test_panels_and_menus_arrive_on_a_spring_and_leave_quickly() {
  for (const [label, make] of [
    ["an arrow panel", () => Object.assign(document.createXULElement("panel"), { className: "" })],
    ["a menu", () => Object.assign(document.createXULElement("menupopup"), { className: "animatable-menupopup" })],
  ]) {
    const popup = make();
    if (label == "an arrow panel") {
      popup.setAttribute("type", "arrow");
    }
    document.documentElement.append(popup);
    const closed = getComputedStyle(popup);
    const leave = parseFloat(closed.transitionDuration);
    Assert.greater(leave, 0, `${label} leaves with a transition`);
    Assert.ok(closed.transitionTimingFunction.includes("cubic-bezier"), `${label} leaves on a plain ease-in`);

    popup.setAttribute("animate", "open");
    const open = getComputedStyle(popup);
    const [move, fade] = open.transitionDuration.split(",").map(parseFloat);
    Assert.ok(open.transitionTimingFunction.startsWith("linear("), `${label} arrives on a spring`);
    Assert.lessOrEqual(Math.max(move, fade) * 1000, 300, `${label} arrives inside its budget`);
    Assert.lessOrEqual(leave, move * BUDGET.exitShare, `${label} leaves faster than it arrives`);
    if (matchMedia("(-moz-panel-animations)").matches) {
      popup.removeAttribute("animate");
      Assert.notEqual(getComputedStyle(popup).transform, "none", `${label} starts a short way off its place`);
      const travel = Math.abs(new DOMMatrix(getComputedStyle(popup).transform).f);
      Assert.lessOrEqual(travel, 20, `${label} travels a short distance, not Firefox's 70 px`);
    }
    popup.remove();
  }
});

add_task(async function test_a_pressed_toolbar_button_dips_and_springs_back() {
  const button = document.createXULElement("toolbarbutton");
  button.className = "toolbarbutton-1";
  document.getElementById("nav-bar").append(button);
  const [colour, movement] = getComputedStyle(button).transitionDuration.split(",").map(parseFloat);
  Assert.less(colour, movement, "a colour change is quicker than a movement");
  Assert.ok(getComputedStyle(button).transitionTimingFunction.includes("linear("), "which springs back");
  InspectorUtils.addPseudoClassLock(button, ":active");
  InspectorUtils.addPseudoClassLock(button, ":hover");
  const pressed = getComputedStyle(button);
  Assert.less(parseFloat(pressed.transitionDuration.split(",").pop()), movement, "pressing is quicker than letting go");
  button.getAnimations().forEach(a => a.finish());
  const { scale } = readStyle(window, button);
  Assert.less(scale, 1, "a pressed button is a little smaller");
  Assert.greaterOrEqual(scale, 0.9, "but not by much");
  InspectorUtils.clearPseudoClassLocks(button);
  button.remove();
});

/** Every rule that sets a motion property has to win over the rule it was written to replace. */
add_task(async function test_the_motion_rules_are_the_ones_that_apply() {
  const tabs = await openRows(1);
  const tab = gBrowser.selectedTab;
  const liveTokens = style => style.transitionTimingFunction.includes("linear(") || style.transitionTimingFunction.includes("cubic-bezier(0.16");

  const label = tab.querySelector(".tab-label-container");
  Assert.equal(getComputedStyle(label).transitionDuration, "0.17s", "a tab's title moves with the fast duration");
  const close = tab.querySelector(".tab-close-button");
  Assert.ok(getComputedStyle(close).transitionProperty.includes("scale"), "the close button scales");
  Assert.ok(getComputedStyle(close).transitionTimingFunction.includes("linear("), "on a spring");
  Assert.equal(getComputedStyle(close).transitionDuration.split(",")[0], "0.26s", "that settles in the base duration");
  Assert.ok(liveTokens(getComputedStyle(tab.querySelector(".tab-background"))), "a tab's background uses Nivora's curves");
  Assert.ok(
    getComputedStyle(tab).transitionTimingFunction.includes("linear("),
    "a tab springs back when it is let go of"
  );

  const view = document.createXULElement("panelview");
  view.setAttribute("visible", "true");
  const item = document.createXULElement("toolbarbutton");
  item.className = "subviewbutton";
  view.append(item);
  document.documentElement.append(view);
  Assert.equal(getComputedStyle(item).animationName, "nivora-item-in", "the items of a menu view arrive one after another");
  Assert.equal(parseFloat(getComputedStyle(item).animationDelay), 0, "starting with the first");
  view.remove();

  tabs.forEach(t => BrowserTestUtils.removeTab(t));
});

add_task(async function test_tabs_meet_their_budget() {
  const tab = await BrowserTestUtils.openNewForegroundTab(gBrowser, "data:text/html,<title>nvbudget tab</title>");
  gZenVerticalTabsManager._startItemOpenAnimation(tab, ["-40px", "0px"]);
  const opening = tab.getAnimations();
  for (const animation of opening) {
    Assert.lessOrEqual(endOf(animation), BUDGET.tabOpen, "an opening tab's animations fit the budget");
  }
  const arrival = opening.find(a => animates(a, "transform"));
  const samples = await scrub(arrival);
  withinBudget(samples, "tab arrival");
  opening.forEach(a => a.finish());
  await TestUtils.waitForCondition(() => !tab.getAnimations().length, "the animations are cleaned up");

  const closing = gZenVerticalTabsManager.animateItemClose(tab);
  const departures = tab.getAnimations();
  for (const animation of departures) {
    Assert.lessOrEqual(endOf(animation), BUDGET.tabClose, "a closing tab's animations fit the budget");
  }
  const departure = departures.find(a => animates(a, "opacity"));
  Assert.lessOrEqual(endOf(departure), endOf(arrival) * BUDGET.exitShare, "and it leaves faster than it arrived");
  departures.forEach(a => a.finish());
  await closing;
  BrowserTestUtils.removeTab(tab);
});

add_task(async function test_a_dialog_meets_its_budget() {
  const box = document.createElement("div");
  box.className = "dialogBox";
  document.documentElement.append(box);
  const animations = box.getAnimations();
  Assert.deepEqual(animations.map(a => a.animationName), ["nivora-fade-in", "nivora-dialog-in"], "a dialog fades in while it settles");
  for (const animation of animations) {
    Assert.lessOrEqual(endOf(animation), BUDGET.dialog, "each fits the budget");
    Assert.ok(!animates(animation, "filter"), "and none blurs");
  }
  withinBudget(await scrub(animations[1]), "dialog");
  box.remove();
});

add_task(async function test_the_start_up_plays_once_per_window() {
  const toolbox = document.getElementById("navigator-toolbox");
  await TestUtils.waitForCondition(() => document.documentElement.hasAttribute("nivora-booted"), "the window records that it has assembled");
  Assert.equal(getComputedStyle(toolbox).animationName, "none", "so the start-up is not replayed (leaving full screen would)");
  document.documentElement.removeAttribute("nivora-booted");
  const names = getComputedStyle(toolbox).animationName;
  Assert.equal(names, "nivora-fade-in, nivora-boot-chrome", "without the record it is the fade and the settle");
  const boot = toolbox.getAnimations().find(a => a.animationName === "nivora-boot-chrome");
  Assert.lessOrEqual(endOf(boot), 600, "which takes about half a second");
  boot.finish();
  document.documentElement.setAttribute("nivora-booted", "");
});

add_task(async function test_a_settings_pane_meets_its_budget() {
  await BrowserTestUtils.withNewTab("about:preferences#general", async browser => {
    const result = await SpecialPowers.spawn(browser, [], async () => {
      const doc = content.document;
      await ContentTaskUtils.waitForCondition(() => doc.querySelector("setting-pane:not([hidden]) > section > setting-group"), "the pane is shown");
      const groups = [...doc.querySelectorAll("setting-pane:not([hidden]) > section > setting-group")];
      const seconds = value => value.split(",").map(parseFloat);
      let slowest = 0;
      const names = new Set();
      for (const group of groups) {
        const style = content.getComputedStyle(group);
        const durations = seconds(style.animationDuration);
        const delays = seconds(style.animationDelay);
        durations.forEach((d, i) => (slowest = Math.max(slowest, (d + delays[i % delays.length]) * 1000)));
        names.add(style.animationName);
      }
      return { count: groups.length, slowest, names: [...names] };
    });
    Assert.greater(result.count, 0, "a pane has groups");
    Assert.deepEqual(result.names, ["nivora-fade-in, nivora-card-in"], "which fade in while they settle, and nothing else");
    Assert.lessOrEqual(result.slowest, BUDGET.settings, "the last of them finishes inside the budget");
  });
});
