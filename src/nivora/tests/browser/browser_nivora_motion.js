/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const ANIMATIONS = "nivora.ui.animations";

function declared(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

add_task(async function test_motion_tokens_are_defined() {
  Assert.equal(declared("--nivora-motion-scale"), "1", "motion is on by default");
  for (const token of ["--nivora-d-micro", "--nivora-d-fast", "--nivora-d-base", "--nivora-d-slow", "--nivora-d-cinematic"]) {
    Assert.ok(declared(token), `${token} is defined`);
  }
  for (const spring of ["smooth", "snappy", "bouncy", "elastic"]) {
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
  Assert.equal(entrance.animationName, "nivora-palette-in", "the palette has its entrance");
  Assert.ok(parseFloat(entrance.animationDuration) >= 0.5, "which is not a flash");

  await TestUtils.waitForCondition(() => gURLBar.hasAttribute("nivora-glide"), "the highlight starts to glide");
  const results = gURLBar.querySelector(".urlbarView-results");
  const y = () => parseFloat(results.style.getPropertyValue("--nivora-sel-y"));
  const selectedRow = () => results.querySelector(".urlbarView-row-inner[selected]")?.closest(".urlbarView-row");

  // The first arrow press selects the first row, the second the next one: the bar follows each.
  EventUtils.synthesizeKey("KEY_ArrowDown");
  await TestUtils.waitForCondition(() => selectedRow() && results.style.getPropertyValue("--nivora-sel-o") === "1", "a row is highlighted");
  const first = selectedRow();
  Assert.equal(y(), first.offsetTop, "the bar sits where the first row is");
  Assert.equal(parseFloat(results.style.getPropertyValue("--nivora-sel-h")), first.offsetHeight, "with its height");

  EventUtils.synthesizeKey("KEY_ArrowDown");
  await TestUtils.waitForCondition(() => selectedRow() && selectedRow() !== first && y() === selectedRow().offsetTop, "the bar moves to the next row");
  Assert.greater(y(), first.offsetTop, "downwards");

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
