/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const PREF = "nivora.ui.hide-zen-services";
const DONATE = 'toolbarbutton[data-l10n-id="library-footer-donate-button"]';

function waitForLibrary(open) {
  const lib = document.querySelector("zen-library");
  const Library = customElements.get("zen-library");
  return TestUtils.waitForCondition(
    () =>
      !lib.hasAttribute("transitioning") &&
      (open
        ? Library.libraryProgress === 1 && !lib.hidden
        : Library.libraryProgress === 0 && lib.hidden),
    `library settles ${open ? "open" : "closed"}`
  );
}

add_task(async function test_donate_button_follows_the_preference() {
  const Library = customElements.get("zen-library");
  Library.toggle();
  await waitForLibrary(true);

  const button = await TestUtils.waitForCondition(
    () => document.querySelector(DONATE),
    "the Library footer has a donate button"
  );

  await SpecialPowers.pushPrefEnv({ set: [[PREF, true]] });
  await TestUtils.waitForCondition(
    () => getComputedStyle(button).display === "none",
    "hidden by default"
  );

  await SpecialPowers.pushPrefEnv({ set: [[PREF, false]] });
  await TestUtils.waitForCondition(
    () => getComputedStyle(button).display !== "none",
    "shown when the preference is off"
  );

  await SpecialPowers.popPrefEnv();
  await SpecialPowers.popPrefEnv();
  Library.toggle();
  await waitForLibrary(false);
});

add_task(async function test_mods_website_link_follows_the_preference() {
  await BrowserTestUtils.withNewTab("about:preferences#zenMarketplace", async browser => {
    const display = () =>
      SpecialPowers.spawn(browser, [], () => {
        const link = content.document.getElementById("zenThemeMarketplaceLink");
        return link ? content.getComputedStyle(link).display : "missing";
      });

    await TestUtils.waitForCondition(async () => (await display()) !== "missing", "the link exists in the pane");
    is(await display(), "none", "hidden by default");

    await SpecialPowers.pushPrefEnv({ set: [[PREF, false]] });
    await TestUtils.waitForCondition(async () => (await display()) !== "none", "shown when the preference is off");
    await SpecialPowers.popPrefEnv();
  });
});

add_task(async function test_dark_mapping_reaches_the_browser_window() {
  const expected = {
    "--background-color-information": "rgb(24, 24, 24)",
    "--promo-background-color-vibrant": "rgb(24, 24, 24)",
    "--color-gray-90": "rgb(16, 16, 16)",
    "--color-gray-80": "rgb(24, 24, 24)",
    "--color-gray-100": "rgb(10, 10, 10)",
  };
  const probe = document.createElement("div");
  document.documentElement.appendChild(probe);
  try {
    for (const [name, rgb] of Object.entries(expected)) {
      probe.style.backgroundColor = `var(${name})`;
      is(getComputedStyle(probe).backgroundColor, rgb, `${name} is the neutral surface`);
    }
  } finally {
    probe.remove();
  }
});
