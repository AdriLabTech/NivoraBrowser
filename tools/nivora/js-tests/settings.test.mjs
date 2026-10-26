// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_SETTINGS_BYTES,
  SETTINGS_FORMAT,
  SETTINGS_SCHEMA,
  SETTINGS_VERSION,
  SettingsSchemaError,
  applySettings,
  defineSchema,
  exportSettings,
  parseSettings,
  repairSettings,
  resetSettings,
  validateValue,
} from "../../../src/nivora/modules/NivoraSettingsCore.mjs";

/** An in-memory preference store with the shape the core expects. */
function fakeBackend(user = {}) {
  const values = new Map(Object.entries(user));
  return {
    values,
    hasUserValue: pref => values.has(pref),
    get(pref, type) {
      const value = values.get(pref);
      const ok =
        (type === "bool" && typeof value === "boolean") ||
        (type === "int" && Number.isInteger(value)) ||
        (type === "string" && typeof value === "string");
      if (!ok) {
        throw new Error("wrong pref type");
      }
      return value;
    },
    set: (pref, type, value) => values.set(pref, value),
    clear: pref => values.delete(pref),
  };
}

const text = object => JSON.stringify(object);
const file = settings => text({ format: SETTINGS_FORMAT, version: SETTINGS_VERSION, settings });

test("the shipped schema is valid and has no secret-looking names", () => {
  assert.ok(SETTINGS_SCHEMA.entries.length >= 20);
  for (const entry of SETTINGS_SCHEMA.entries) {
    assert.doesNotMatch(entry.pref, /password|secret|token|cookie|session|private/i);
  }
});

test("schema definition refuses secrets, duplicates and unconstrained values", () => {
  assert.throws(
    () => defineSchema([{ pref: "zen.share.secret-key", type: "string", group: "x", pattern: ".*" }]),
    SettingsSchemaError
  );
  assert.throws(
    () => defineSchema([
      { pref: "a.b", type: "bool", group: "x" },
      { pref: "a.b", type: "bool", group: "x" },
    ]),
    /defined twice/
  );
  assert.throws(() => defineSchema([{ pref: "a.b", type: "int", group: "x" }]), /min\/max/);
  assert.throws(() => defineSchema([{ pref: "a.b", type: "string", group: "x" }]), /values or a pattern/);
  assert.throws(() => defineSchema([{ pref: "a.b", type: "string", group: "x", pattern: "(" }]));
});

test("validateValue enforces types, ranges, allow-lists and patterns", () => {
  const byPref = SETTINGS_SCHEMA.byPref;
  assert.equal(validateValue(byPref.get("zen.view.window.scheme"), 0), null);
  assert.ok(validateValue(byPref.get("zen.view.window.scheme"), 3));
  assert.ok(validateValue(byPref.get("zen.view.window.scheme"), "0"));
  assert.ok(validateValue(byPref.get("zen.view.sidebar-expanded"), 1));
  assert.equal(validateValue(byPref.get("zen.theme.accent-color"), "#a1B2c3"), null);
  assert.equal(validateValue(byPref.get("zen.theme.accent-color"), "AccentColor"), null);
  assert.ok(validateValue(byPref.get("zen.theme.accent-color"), "#12345"));
  assert.ok(validateValue(byPref.get("zen.theme.accent-color"), "red; background: url(x)"));
  assert.ok(validateValue(byPref.get("zen.theme.content-element-separation"), 13));
  assert.equal(validateValue(byPref.get("zen.theme.border-radius"), -1), null);
  assert.ok(validateValue(byPref.get("zen.theme.border-radius"), 1.5));
  assert.ok(validateValue(byPref.get("zen.urlbar.behavior"), "evil"));
});

test("export lists only whitelisted prefs that the user changed", () => {
  const backend = fakeBackend({
    "zen.view.window.scheme": 1,
    "zen.share.secret-key": "hunter2", // not in the schema
    "browser.startup.homepage": "https://example.com", // not in the schema
  });
  const exported = exportSettings(SETTINGS_SCHEMA, backend);
  assert.deepEqual(exported, {
    format: SETTINGS_FORMAT,
    version: SETTINGS_VERSION,
    settings: { "zen.view.window.scheme": 1 },
  });
  assert.doesNotMatch(JSON.stringify(exported), /hunter2|example\.com/);
});

test("export skips values of the wrong type instead of failing", () => {
  const backend = fakeBackend({ "zen.view.window.scheme": "dark", "zen.tabs.vertical": false });
  assert.deepEqual(exportSettings(SETTINGS_SCHEMA, backend).settings, { "zen.tabs.vertical": false });
});

test("export then import round-trips", () => {
  const source = fakeBackend({
    "zen.view.window.scheme": 0,
    "zen.theme.accent-color": "#858585",
    "zen.workspaces.switch-animation-duration": 0,
  });
  const parsed = parseSettings(text(exportSettings(SETTINGS_SCHEMA, source)), SETTINGS_SCHEMA);
  assert.equal(parsed.ok, true, parsed.errors.join("; "));
  const target = fakeBackend();
  const result = applySettings(parsed.settings, SETTINGS_SCHEMA, target);
  assert.deepEqual(result.failed, []);
  assert.deepEqual(Object.fromEntries(target.values), Object.fromEntries(source.values));
});

test("import rejects non-text, oversized, malformed and non-object input", () => {
  assert.equal(parseSettings(undefined, SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings("{not json", SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings("[]", SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings("null", SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings("42", SETTINGS_SCHEMA).ok, false);
  const big = "x".repeat(MAX_SETTINGS_BYTES + 1);
  const result = parseSettings(big, SETTINGS_SCHEMA);
  assert.equal(result.ok, false);
  assert.match(result.errors[0], /larger than/);
});

test("import checks format and version, and refuses newer files", () => {
  assert.equal(parseSettings(text({ version: 1, settings: {} }), SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings(text({ format: "other", version: 1, settings: {} }), SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings(text({ format: SETTINGS_FORMAT, version: "1", settings: {} }), SETTINGS_SCHEMA).ok, false);
  assert.equal(parseSettings(text({ format: SETTINGS_FORMAT, version: 0, settings: {} }), SETTINGS_SCHEMA).ok, false);
  const newer = parseSettings(text({ format: SETTINGS_FORMAT, version: SETTINGS_VERSION + 1, settings: {} }), SETTINGS_SCHEMA);
  assert.equal(newer.ok, false);
  assert.match(newer.errors[0], /newer version/);
  assert.equal(parseSettings(text({ format: SETTINGS_FORMAT, version: 1, settings: [] }), SETTINGS_SCHEMA).ok, false);
});

test("import is all-or-nothing: one bad value rejects the file", () => {
  const result = parseSettings(
    file({ "zen.view.window.scheme": 1, "zen.theme.border-radius": 999 }),
    SETTINGS_SCHEMA
  );
  assert.equal(result.ok, false);
  assert.deepEqual(result.settings, {});
  assert.match(result.errors.join(), /zen\.theme\.border-radius/);
});

test("unknown preferences are ignored with a warning, never applied", () => {
  const result = parseSettings(
    file({ "zen.view.window.scheme": 1, "app.update.auto": true, "zen.share.secret-key": "x" }),
    SETTINGS_SCHEMA
  );
  assert.equal(result.ok, true);
  assert.deepEqual(result.settings, { "zen.view.window.scheme": 1 });
  assert.equal(result.warnings.length, 2);
  const backend = fakeBackend();
  applySettings(result.settings, SETTINGS_SCHEMA, backend);
  assert.deepEqual([...backend.values.keys()], ["zen.view.window.scheme"]);
});

test("a __proto__ key cannot pollute anything", () => {
  const hostile = '{"format":"nivora-settings","version":1,"settings":{"__proto__":{"polluted":true},"zen.tabs.vertical":true}}';
  const result = parseSettings(hostile, SETTINGS_SCHEMA);
  assert.equal(result.ok, true);
  assert.deepEqual(result.settings, { "zen.tabs.vertical": true });
  assert.equal({}.polluted, undefined);
});

test("applySettings never writes a value the schema does not accept", () => {
  const backend = fakeBackend();
  const result = applySettings(
    { "zen.view.window.scheme": 9, "unknown.pref": true, "zen.tabs.vertical": true },
    SETTINGS_SCHEMA,
    backend
  );
  assert.deepEqual(result.applied, ["zen.tabs.vertical"]);
  assert.deepEqual(result.failed.sort(), ["unknown.pref", "zen.view.window.scheme"]);
});

test("applySettings reports a backend that throws", () => {
  const backend = { ...fakeBackend(), set() { throw new Error("locked"); } };
  const result = applySettings({ "zen.tabs.vertical": true }, SETTINGS_SCHEMA, backend);
  assert.deepEqual(result, { applied: [], failed: ["zen.tabs.vertical"] });
});

test("reset clears only whitelisted prefs", () => {
  const backend = fakeBackend({ "zen.tabs.vertical": false, "browser.startup.homepage": "x" });
  assert.deepEqual(resetSettings(SETTINGS_SCHEMA, backend), ["zen.tabs.vertical"]);
  assert.ok(backend.values.has("browser.startup.homepage"));
});

test("repair removes invalid user values and keeps valid ones", () => {
  const backend = fakeBackend({
    "zen.view.window.scheme": 42, // out of range
    "zen.theme.border-radius": "round", // wrong type
    "zen.tabs.vertical": true, // fine
    "zen.urlbar.behavior": "float", // fine
  });
  const repaired = repairSettings(SETTINGS_SCHEMA, backend).sort();
  assert.deepEqual(repaired, ["zen.theme.border-radius", "zen.view.window.scheme"]);
  assert.deepEqual([...backend.values.keys()].sort(), ["zen.tabs.vertical", "zen.urlbar.behavior"]);
});
