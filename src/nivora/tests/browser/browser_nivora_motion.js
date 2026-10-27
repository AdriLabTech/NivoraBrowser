/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const ANIMATIONS = "nivora.ui.animations";

function declared(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

add_task(async function test_motion_tokens_are_defined() {
  Assert.equal(declared("--nivora-motion-scale"), "1", "motion is on by default");
  for (const token of ["--nivora-d-micro", "--nivora-d-fast", "--nivora-d-base", "--nivora-d-slow", "--nivora-d-cinematic", "--nivora-d-exit"]) {
    Assert.ok(declared(token), `${token} is defined`);
  }
  for (const spring of ["smooth", "snappy", "settle", "bouncy", "elastic"]) {
    Assert.ok(declared(`--nivora-spring-${spring}`).startsWith("linear("), `a ${spring} spring is defined`);
  }
});

add_task(async function test_turning_animations_off_zeroes_every_duration_and_distance() {
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  await TestUtils.waitForCondition(() => declared("--nivora-motion-scale") === "0", "the scale drops to 0");
  Assert.equal(declared("--nivora-lift"), "0", "no travel either");
  const probe = document.createElement("div");
  probe.style.transitionDuration = "var(--nivora-d-base)";
  document.documentElement.appendChild(probe);
  Assert.equal(getComputedStyle(probe).transitionDuration, "0s", "a duration taken from the tokens is 0");
  probe.remove();
  await SpecialPowers.popPrefEnv();
  await TestUtils.waitForCondition(() => declared("--nivora-motion-scale") === "1", "and comes back");
});

add_task(async function test_the_tab_selection_animation_is_applied_and_follows_the_scale() {
  const tab = gBrowser.selectedTab;
  const background = tab.querySelector(".tab-background");
  const style = getComputedStyle(background);
  Assert.ok(style.transitionDuration.split(",").some(d => parseFloat(d) > 0.1), "tab backgrounds transition");
  Assert.ok(style.transitionTimingFunction.includes("linear("), "with a spring curve");
});

/** Open tabs whose titles match one query: they are the palette's rows without needing a network. */
async function openRows(count) {
  const tabs = [];
  for (let i = 0; i < count; i++) {
    tabs.push(await BrowserTestUtils.openNewForegroundTab(gBrowser, `data:text/html,<title>nvmotion ${i}</title>${i}`));
  }
  return tabs;
}

async function openPalette() {
  gURLBar.focus();
  gURLBar.value = "% nvmotion";
  gURLBar.startQuery({ searchString: "% nvmotion" });
  await TestUtils.waitForCondition(
    () => gURLBar.hasAttribute("open") && gURLBar.getAttribute("zen-floating-urlbar") === "true",
    "the palette opens"
  );
  await TestUtils.waitForCondition(
    () => gURLBar.querySelectorAll(".urlbarView-row").length >= 2,
    "the palette lists the tabs"
  );
}

function closePalette() {
  gURLBar.view.close();
  gURLBar.blur();
}

const nextFrames = n =>
  new Promise(resolve => {
    const step = left => (left ? requestAnimationFrame(() => step(left - 1)) : resolve());
    step(n);
  });

add_task(async function test_the_palette_enters_with_a_choreography_and_a_gliding_highlight() {
  const tabs = await openRows(3);
  await openPalette();
  const entrance = getComputedStyle(gURLBar);
  Assert.equal(entrance.animationName, "nivora-fade-in, nivora-palette-in", "the palette fades in while it settles");
  const [fade, settle] = entrance.animationDuration.split(",").map(parseFloat);
  Assert.ok(settle >= 0.3, "its movement is not a flash");
  Assert.less(fade, settle, "and it is fully visible before it has finished moving");

  await TestUtils.waitForCondition(() => gURLBar.hasAttribute("nivora-glide"), "the highlight starts to glide");
  const results = gURLBar.querySelector(".urlbarView-results");
  const y = () => parseFloat(results.style.getPropertyValue("--nivora-sel-y"));
  const selectedRow = () => results.querySelector(".urlbarView-row[selected]");

  // The first arrow press selects the first row, the second the next one: the bar follows each.
  EventUtils.synthesizeKey("KEY_ArrowDown");
  await TestUtils.waitForCondition(() => selectedRow() && results.style.getPropertyValue("--nivora-sel-o") === "1", "a row is highlighted");
  const first = selectedRow();
  const placed = row => row.offsetTop + row.clientTop;
  Assert.equal(y(), placed(first), "the bar sits where the first row paints its background");
  Assert.equal(parseFloat(results.style.getPropertyValue("--nivora-sel-h")), first.clientHeight, "with its height");

  // The bar is the selected row's own colour, not a colour of its own: Zen's mix of its accent.
  const reference = document.createElement("div");
  reference.style.background = "color-mix(in srgb, var(--zen-accent-button-background), transparent 40%)";
  document.documentElement.append(reference);
  Assert.equal(
    getComputedStyle(results, "::before").backgroundColor,
    getComputedStyle(reference).backgroundColor,
    "and the colour Zen gives a selected row"
  );
  reference.remove();
  Assert.equal(getComputedStyle(first).backgroundColor, "rgba(0, 0, 0, 0)", "while the row's own background is hidden");

  EventUtils.synthesizeKey("KEY_ArrowDown");
  await TestUtils.waitForCondition(() => selectedRow() && selectedRow() !== first && y() === placed(selectedRow()), "the bar moves to the next row");
  Assert.greater(y(), placed(first), "downwards");

  closePalette();
  await TestUtils.waitForCondition(() => !gURLBar.hasAttribute("nivora-glide"), "the glide ends with the palette");
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

add_task(async function test_the_palette_has_no_choreography_when_animations_are_off() {
  const tabs = await openRows(3);
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  await openPalette();
  Assert.equal(parseFloat(getComputedStyle(gURLBar).animationDuration), 0, "its entrance lasts 0 s");
  EventUtils.synthesizeKey("KEY_ArrowDown");
  await nextFrames(3);
  Assert.ok(!gURLBar.hasAttribute("nivora-glide"), "and the highlight does not glide");
  closePalette();
  await SpecialPowers.popPrefEnv();
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

add_task(async function test_turning_animations_off_while_the_palette_is_open_stops_the_glide() {
  const tabs = await openRows(3);
  await openPalette();
  await TestUtils.waitForCondition(() => gURLBar.hasAttribute("nivora-glide"), "the highlight glides");
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  await TestUtils.waitForCondition(() => !gURLBar.hasAttribute("nivora-glide"), "and stops when the setting is turned off");
  closePalette();
  await SpecialPowers.popPrefEnv();
  tabs.forEach(tab => BrowserTestUtils.removeTab(tab));
});

add_task(async function test_tabs_spring_in_and_step_aside_when_they_close() {
  const tab = await BrowserTestUtils.openNewForegroundTab(gBrowser, "data:text/html,<title>nvmotion tab</title>");
  // Zen skips the animation under test automation, so the animation is started directly.
  gZenVerticalTabsManager._startItemOpenAnimation(tab, ["-40px", "0px"]);
  const opening = tab.getAnimations();
  Assert.equal(opening.length, 3, "an item that opens has a fade, an arrival and a room animation");
  const arrival = opening.find(a => a.effect.getKeyframes().some(k => "transform" in k));
  Assert.equal(arrival.effect.getTiming().duration, 340, "the arrival lasts as long as the settle spring");
  Assert.ok(String(arrival.effect.getTiming().easing).startsWith("linear("), "and uses the spring curve");
  const fadeIn = opening.find(a => a.effect.getKeyframes().some(k => "opacity" in k));
  Assert.less(fadeIn.effect.getTiming().duration, arrival.effect.getTiming().duration, "the item is visible before it has settled");
  await Promise.all(opening.map(a => a.finished));
  await TestUtils.waitForCondition(() => !tab.getAnimations().length, "the animations are cleaned up");
  Assert.equal(tab.style.marginBottom, "", "no margin is left behind");
  Assert.equal(tab.style.opacity, "", "nor opacity");

  const closing = gZenVerticalTabsManager.animateItemClose(tab);
  const departure = tab.getAnimations();
  Assert.greaterOrEqual(departure.length, 1, "an item that closes departs with an animation");
  Assert.ok(
    departure.some(a => a.effect.getKeyframes().some(k => "opacity" in k) && a.effect.getTiming().duration === 140),
    "which fades it out in 140 ms"
  );
  await closing;
  Assert.equal(getComputedStyle(tab).opacity, "0", "and keeps it gone until it is removed");
  BrowserTestUtils.removeTab(tab);
});

add_task(async function test_tabs_do_not_animate_when_animations_are_off() {
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  const tab = await BrowserTestUtils.openNewForegroundTab(gBrowser, "data:text/html,<title>nvmotion off</title>");
  await gZenVerticalTabsManager.animateItemClose(tab);
  Assert.equal(tab.getAnimations().length, 0, "closing a tab starts no animation");
  BrowserTestUtils.removeTab(tab);
  await SpecialPowers.popPrefEnv();
});

add_task(async function test_turning_animations_off_puts_the_window_in_reduced_motion() {
  const before = gReduceMotion;
  await SpecialPowers.pushPrefEnv({ set: [[ANIMATIONS, false]] });
  await TestUtils.waitForCondition(() => gReduceMotion === true, "scripted animations (Zen's and Firefox's) are off too");
  await SpecialPowers.popPrefEnv();
  await TestUtils.waitForCondition(() => gReduceMotion === before, "and the window goes back to what it was");
});

add_task(async function test_a_settings_pane_assembles_itself_when_it_is_shown() {
  await BrowserTestUtils.withNewTab("about:preferences#general", async browser => {
    await SpecialPowers.spawn(browser, [], async () => {
      const doc = content.document;
      await ContentTaskUtils.waitForCondition(() => doc.querySelector("setting-pane:not([hidden]) > section > setting-group"), "the pane is shown");
      const groups = [...doc.querySelectorAll("setting-pane:not([hidden]) > section > setting-group")];
      const style = content.getComputedStyle(groups[0]);
      Assert.equal(style.animationName, "nivora-fade-in, nivora-card-in", "its groups have the entrance");
      Assert.ok(parseFloat(style.animationDuration.split(",")[1]) >= 0.3, "which is not a flash");
      const delays = groups.slice(0, 5).map(g => parseFloat(content.getComputedStyle(g).animationDelay));
      Assert.deepEqual([...delays].sort((a, b) => a - b), delays, "and each waits for the one before it");
      Assert.greater(delays[delays.length - 1], delays[0], "so they arrive one after another");
    });
  });
});

add_task(async function test_the_systems_reduced_motion_setting_zeroes_the_scale_too() {
  await SpecialPowers.pushPrefEnv({ set: [["ui.prefersReducedMotion", 1]] });
  await TestUtils.waitForCondition(() => declared("--nivora-motion-scale") === "0", "the scale is 0");
  Assert.equal(declared("--nivora-lift"), "0", "and so is the travel");
  const probe = document.createElement("div");
  probe.style.transitionDuration = "var(--nivora-d-slow)";
  document.documentElement.append(probe);
  Assert.equal(getComputedStyle(probe).transitionDuration, "0s", "a duration taken from the tokens is 0 s");
  probe.remove();
  await SpecialPowers.popPrefEnv();
  await TestUtils.waitForCondition(() => declared("--nivora-motion-scale") === "1", "and the scale comes back");
});
