/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

// The values Nivora ships. They come from prefs/ and are read from the default
// branch, so a value changed by another test or by the profile cannot hide a
// wrong default.
const DEFAULTS = {
  "zen.theme.accent-color": "#858585",
  "zen.view.window.scheme": 0,
  "zen.share.base-url": "",
  "zen.updates.show-update-notification": false,
  "zen.mods.auto-update": false,
  "startup.homepage_override_url": "",
  "startup.homepage_welcome_url": "",
  "startup.homepage_welcome_url.additional": "",
  "app.update.auto": false,
  "app.update.url.manual": "https://github.com/AdriLabTech/nivoraBrowser/releases",
  "app.releaseNotesURL": "https://github.com/AdriLabTech/nivoraBrowser/releases",
  "app.releaseNotesURL.prompt": "https://github.com/AdriLabTech/nivoraBrowser/releases",
  "nivora.ui.hide-zen-services": true,
  "xpinstall.signatures.required": true,
};

function defaultValue(name) {
  const branch = Services.prefs.getDefaultBranch("");
  try {
    switch (branch.getPrefType(name)) {
      case Ci.nsIPrefBranch.PREF_BOOL:
        return branch.getBoolPref(name);
      case Ci.nsIPrefBranch.PREF_INT:
        return branch.getIntPref(name);
      case Ci.nsIPrefBranch.PREF_STRING:
        return branch.getStringPref(name);
    }
  } catch (e) {
    // A preference with no default value (only a user value): nothing to compare.
  }
  return undefined;
}

add_task(async function test_nivora_default_preferences() {
  for (const [name, expected] of Object.entries(DEFAULTS)) {
    Assert.strictEqual(defaultValue(name), expected, `default of ${name}`);
  }
});

add_task(async function test_mods_injection_is_limited_to_preferences_in_official_builds() {
  const { AppConstants } = ChromeUtils.importESModule("resource://gre/modules/AppConstants.sys.mjs");
  // Zen's own development builds allow localhost; official builds (what Nivora ships) must not.
  const expected = AppConstants.MOZILLA_OFFICIAL ? "about:preferences" : "http://localhost/*";
  Assert.strictEqual(defaultValue("zen.injections.match-urls"), expected);
});

add_task(async function test_no_default_points_at_a_zen_service() {
  const zenHost = /zen-browser\.(app|github\.io)/;
  for (const name of Services.prefs.getDefaultBranch("").getChildList("")) {
    if (!/^(app\.|startup\.|zen\.|services\.)/.test(name)) {
      continue;
    }
    const value = defaultValue(name);
    if (typeof value === "string") {
      Assert.ok(!zenHost.test(value), `${name} must not point at a Zen service (${value})`);
    }
  }
});

add_task(async function test_share_ui_hides_itself_without_a_share_service() {
  Assert.ok(!gZenShareManager.enabled, "sharing is disabled while no share service is configured");
  for (const id of ["context_zenShareWorkspace", "context_zenShareFolder"]) {
    const item = document.getElementById(id);
    Assert.ok(!item || item.hidden, `${id} is hidden`);
  }
});

add_task(async function test_zen_service_controls_are_hidden() {
  Assert.ok(
    window.matchMedia('(-moz-pref("nivora.ui.hide-zen-services"))').matches,
    "the hide-zen-services media query matches"
  );
});
