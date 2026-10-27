/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const { NivoraSettings, prefsBackend } = ChromeUtils.importESModule(
  "resource:///modules/nivora/NivoraSettings.sys.mjs"
);

// Preferences that change nothing visible when toggled (some Zen layout preferences rebuild the
// address bar and make Firefox log unrelated l10n errors in this build).
const PREFS = ["zen.view.window.scheme", "zen.theme.border-radius", "zen.glance.animation-duration", "zen.glance.enabled"];

registerCleanupFunction(() => {
  for (const pref of PREFS) {
    Services.prefs.clearUserPref(pref);
  }
});

add_task(async function test_export_contains_only_changed_managed_prefs() {
  for (const pref of PREFS) {
    Services.prefs.clearUserPref(pref);
  }
  Services.prefs.setIntPref("zen.view.window.scheme", 1);
  Services.prefs.setStringPref("zen.share.secret-key", "must-never-leak");
  const exported = JSON.parse(NivoraSettings.exportText());
  Assert.equal(exported.format, "nivora-settings");
  Assert.equal(exported.version, 1);
  Assert.equal(exported.settings["zen.view.window.scheme"], 1);
  Assert.ok(!("zen.share.secret-key" in exported.settings), "unmanaged prefs are not exported");
  Assert.ok(!NivoraSettings.exportText().includes("must-never-leak"), "no secret in the file");
  Services.prefs.clearUserPref("zen.share.secret-key");
});

add_task(async function test_round_trip_through_real_preferences() {
  Services.prefs.setIntPref("zen.view.window.scheme", 1);
  Services.prefs.setIntPref("zen.theme.border-radius", 12);
  const text = NivoraSettings.exportText();
  Services.prefs.clearUserPref("zen.view.window.scheme");
  Services.prefs.clearUserPref("zen.theme.border-radius");
  const parsed = NivoraSettings.parseText(text);
  Assert.ok(parsed.ok, parsed.errors.join("; "));
  const { applied, failed } = NivoraSettings.apply(parsed.settings);
  Assert.deepEqual(failed, []);
  Assert.ok(applied.includes("zen.view.window.scheme"));
  Assert.equal(Services.prefs.getIntPref("zen.view.window.scheme"), 1);
  Assert.equal(Services.prefs.getIntPref("zen.theme.border-radius"), 12);
});

add_task(async function test_invalid_import_changes_nothing() {
  Services.prefs.clearUserPref("zen.view.window.scheme");
  const parsed = NivoraSettings.parseText(
    JSON.stringify({
      format: "nivora-settings",
      version: 1,
      settings: { "zen.view.window.scheme": 1, "zen.theme.border-radius": 9999 },
    })
  );
  Assert.ok(!parsed.ok, "an out-of-range value rejects the file");
  Assert.deepEqual(parsed.settings, {});
  Assert.ok(!Services.prefs.prefHasUserValue("zen.view.window.scheme"), "nothing was applied");
});

add_task(async function test_reset_returns_managed_prefs_to_defaults() {
  Services.prefs.setBoolPref("zen.glance.enabled", false);
  const cleared = NivoraSettings.reset();
  Assert.ok(cleared.includes("zen.glance.enabled"));
  Assert.ok(!Services.prefs.prefHasUserValue("zen.glance.enabled"));
});

add_task(async function test_repair_removes_a_corrupt_user_value() {
  // A hand-edited profile: right name, value out of range. (A wrong *type* cannot be set on a
  // preference that already has a default; the Node tests cover it with a fake store.)
  Services.prefs.setIntPref("zen.view.window.scheme", 42);
  Services.prefs.setIntPref("zen.glance.animation-duration", -5);
  Assert.ok(prefsBackend.hasUserValue("zen.view.window.scheme"));
  const repaired = NivoraSettings.repair();
  Assert.ok(repaired.includes("zen.view.window.scheme"));
  Assert.ok(repaired.includes("zen.glance.animation-duration"));
  Assert.ok(!Services.prefs.prefHasUserValue("zen.view.window.scheme"));
  Assert.ok(!Services.prefs.prefHasUserValue("zen.glance.animation-duration"));
});
