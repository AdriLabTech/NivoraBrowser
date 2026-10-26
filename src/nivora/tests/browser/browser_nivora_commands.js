/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const { nivoraRegistry, nivoraGlobalActions, contextFor } = ChromeUtils.importESModule(
  "resource:///modules/nivora/NivoraCommands.sys.mjs"
);
const { globalActions } = ChromeUtils.importESModule(
  "resource:///modules/ZenUBGlobalActions.sys.mjs"
);

const EXPECTED_IDS = [
  "nivora:new-tab",
  "nivora:open-history",
  "nivora:open-downloads",
  "nivora:search-open-tabs",
  "nivora:close-duplicate-tabs",
  "nivora:export-settings",
  "nivora:import-settings",
  "nivora:reset-settings",
];

add_task(async function test_commands_are_registered_with_stable_ids() {
  Assert.deepEqual(nivoraRegistry.all().map(c => c.id), EXPECTED_IDS);
  Assert.equal(nivoraGlobalActions.length, EXPECTED_IDS.length);
});

add_task(async function test_commands_appear_in_zens_palette_with_real_labels() {
  for (const id of EXPECTED_IDS) {
    const action = globalActions.find(a => a.commandId === id);
    Assert.ok(action, `${id} is in Zen's global actions`);
    Assert.ok(action.label && action.label !== action.l10nId, `${id} has a translated label (${action.label})`);
  }
  // Zen's own actions are still there.
  Assert.ok(globalActions.some(a => a.l10nId === "zen-action-close-tab"), "Zen's actions survive");
});

add_task(async function test_unknown_and_bad_calls_never_throw() {
  const ctx = contextFor(window);
  Assert.equal((await nivoraRegistry.execute("nivora:nope", ctx)).error, "unknown-command");
  Assert.equal((await nivoraRegistry.execute("nivora:new-tab", ctx, { surprise: 1 })).error, "invalid-args");
});

add_task(async function test_search_open_tabs_restricts_the_address_bar() {
  const result = await nivoraRegistry.execute("nivora:search-open-tabs", contextFor(window));
  Assert.ok(result.ok, result.message);
  await TestUtils.waitForCondition(() => gURLBar.value.startsWith("%") || gURLBar.searchMode, "the address bar entered tab search");
  gURLBar.handleRevert?.();
  gURLBar.blur();
});

add_task(async function test_duplicate_tabs_need_confirmation_and_keep_one() {
  const url = "https://example.com/browser/nivora-duplicate";
  const tabs = [];
  for (let i = 0; i < 3; i++) {
    tabs.push(await BrowserTestUtils.openNewForegroundTab(gBrowser, url));
  }
  const before = gBrowser.tabs.length;
  Assert.ok(nivoraRegistry.isAvailable("nivora:close-duplicate-tabs", contextFor(window)), "duplicates are detected");

  const declined = await nivoraRegistry.execute("nivora:close-duplicate-tabs", { window, confirm: () => false });
  Assert.equal(declined.error, "declined");
  Assert.equal(gBrowser.tabs.length, before, "declining closes nothing");

  let asked = null;
  const accepted = await nivoraRegistry.execute("nivora:close-duplicate-tabs", {
    window,
    confirm: (spec, args) => {
      asked = args;
      return true;
    },
  });
  Assert.ok(accepted.ok, accepted.message);
  Assert.equal(asked.count, 2, "the user is told how many tabs would close");
  Assert.equal(gBrowser.tabs.length, before - 2, "two of three duplicates were closed");
  Assert.ok(!nivoraRegistry.isAvailable("nivora:close-duplicate-tabs", contextFor(window)), "no duplicates left");

  for (const tab of gBrowser.tabs) {
    if (tab.linkedBrowser.currentURI.spec === url) {
      BrowserTestUtils.removeTab(tab);
    }
  }
});

add_task(async function test_pinned_tabs_are_never_proposed() {
  const url = "https://example.com/browser/nivora-pinned";
  const first = await BrowserTestUtils.openNewForegroundTab(gBrowser, url);
  const second = await BrowserTestUtils.openNewForegroundTab(gBrowser, url);
  gBrowser.pinTab(first);
  Assert.ok(!nivoraRegistry.isAvailable("nivora:close-duplicate-tabs", contextFor(window)), "a pinned tab is not a duplicate");
  gBrowser.unpinTab(first);
  BrowserTestUtils.removeTab(first);
  BrowserTestUtils.removeTab(second);
});

add_task(async function test_reset_settings_asks_first() {
  Services.prefs.setIntPref("zen.view.window.scheme", 1);
  const declined = await nivoraRegistry.execute("nivora:reset-settings", { window, confirm: () => false });
  Assert.equal(declined.error, "declined");
  Assert.ok(Services.prefs.prefHasUserValue("zen.view.window.scheme"), "nothing reset without confirmation");
  const originalAlert = Services.prompt.alert;
  Services.prompt.alert = () => {};
  try {
    const accepted = await nivoraRegistry.execute("nivora:reset-settings", { window, confirm: () => true });
    Assert.ok(accepted.ok, accepted.message);
  } finally {
    Services.prompt.alert = originalAlert;
  }
  Assert.ok(!Services.prefs.prefHasUserValue("zen.view.window.scheme"), "reset after confirmation");
});
