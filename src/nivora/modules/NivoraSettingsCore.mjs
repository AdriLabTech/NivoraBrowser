/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Nivora central settings: a typed, whitelisted view over preferences, with
 * versioned export, validated import, reset and repair.
 *
 * This module is pure: it touches no Firefox global, so it loads both in the
 * browser and under Node (see tools/nivora/js-tests). Everything that reads or
 * writes a preference goes through the `backend` object the caller passes in.
 *
 * Design rules (docs/SECURITY.md, section 6):
 *  - Only preferences listed in the schema can be exported, imported or reset.
 *  - Imported text is parsed as JSON and never evaluated. Size is limited.
 *  - A schema entry whose name looks like a secret is refused outright.
 *  - Import is all-or-nothing: one invalid value rejects the whole file.
 *  - Nothing here runs at startup except `repairSettings`, which only ever
 *    removes a user value that is no longer valid, so a corrupt profile cannot
 *    stop the browser from starting.
 */

export const SETTINGS_FORMAT = "nivora-settings";
export const SETTINGS_VERSION = 1;
export const MAX_SETTINGS_BYTES = 64 * 1024;

const TYPES = new Set(["bool", "int", "string"]);
const SECRET_NAME =
  /(password|passwd|secret|token|api[-_.]?key|credential|cookie|private|session)/i;

export class SettingsSchemaError extends Error {}

/**
 * Check and freeze a list of schema entries.
 *
 * An entry is `{ pref, type, group, min?, max?, values?, pattern?, maxLength? }`.
 * `values` is an allow-list for int and string entries; `pattern` is a RegExp
 * source a string must match entirely.
 *
 * @param {object[]} entries
 * @returns {{ entries: object[], byPref: Map<string, object> }}
 */
export function defineSchema(entries) {
  const byPref = new Map();
  for (const entry of entries) {
    if (!entry || typeof entry.pref !== "string" || !entry.pref) {
      throw new SettingsSchemaError("every entry needs a pref name");
    }
    if (!TYPES.has(entry.type)) {
      throw new SettingsSchemaError(`${entry.pref}: unknown type '${entry.type}'`);
    }
    if (typeof entry.group !== "string" || !entry.group) {
      throw new SettingsSchemaError(`${entry.pref}: missing group`);
    }
    if (SECRET_NAME.test(entry.pref)) {
      throw new SettingsSchemaError(
        `${entry.pref}: looks like a secret; secrets are never part of the settings`
      );
    }
    if (byPref.has(entry.pref)) {
      throw new SettingsSchemaError(`${entry.pref}: defined twice`);
    }
    if (entry.type === "int") {
      const hasValues = Array.isArray(entry.values);
      const hasRange = Number.isInteger(entry.min) && Number.isInteger(entry.max);
      if (!hasValues && !hasRange) {
        throw new SettingsSchemaError(`${entry.pref}: an int needs values or min/max`);
      }
    }
    if (entry.type === "string") {
      const hasValues = Array.isArray(entry.values);
      const hasPattern = typeof entry.pattern === "string";
      if (!hasValues && !hasPattern) {
        throw new SettingsSchemaError(`${entry.pref}: a string needs values or a pattern`);
      }
      if (hasPattern) {
        new RegExp(`^(?:${entry.pattern})$`); // throws on a bad pattern
      }
    }
    byPref.set(entry.pref, Object.freeze({ ...entry }));
  }
  return Object.freeze({ entries: Object.freeze([...byPref.values()]), byPref });
}

/**
 * @param {object} entry A schema entry.
 * @param {unknown} value
 * @returns {string|null} A reason the value is not acceptable, or null.
 */
export function validateValue(entry, value) {
  switch (entry.type) {
    case "bool":
      return typeof value === "boolean" ? null : "must be true or false";
    case "int":
      if (!Number.isInteger(value)) {
        return "must be a whole number";
      }
      if (Array.isArray(entry.values)) {
        return entry.values.includes(value)
          ? null
          : `must be one of ${entry.values.join(", ")}`;
      }
      return value >= entry.min && value <= entry.max
        ? null
        : `must be between ${entry.min} and ${entry.max}`;
    case "string": {
      if (typeof value !== "string") {
        return "must be text";
      }
      if (value.length > (entry.maxLength ?? 64)) {
        return "is too long";
      }
      if (Array.isArray(entry.values)) {
        return entry.values.includes(value)
          ? null
          : `must be one of ${entry.values.join(", ")}`;
      }
      return new RegExp(`^(?:${entry.pattern})$`).test(value)
        ? null
        : "is not in the expected format";
    }
    default:
      return "has an unknown type";
  }
}

function utf8Length(text) {
  return new TextEncoder().encode(text).length;
}

function isPlainObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    (Object.getPrototypeOf(value) === Object.prototype ||
      Object.getPrototypeOf(value) === null)
  );
}

/**
 * Describe the settings the user has changed, in the exchange format.
 * Only whitelisted preferences that have a user value are included, so a
 * file made on one version stays meaningful on another whose defaults moved.
 *
 * @param {{ entries: object[] }} schema
 * @param {object} backend `{ hasUserValue(pref), get(pref, type) }`
 * @returns {{ format: string, version: number, settings: object }}
 */
export function exportSettings(schema, backend) {
  const settings = {};
  for (const entry of schema.entries) {
    if (!backend.hasUserValue(entry.pref)) {
      continue;
    }
    let value;
    try {
      value = backend.get(entry.pref, entry.type);
    } catch {
      continue; // unreadable (wrong type in the profile): leave it out
    }
    if (validateValue(entry, value) === null) {
      settings[entry.pref] = value;
    }
  }
  return { format: SETTINGS_FORMAT, version: SETTINGS_VERSION, settings };
}

/**
 * Parse and validate exchange-format text. Nothing is applied.
 *
 * @param {string} text
 * @param {{ byPref: Map<string, object> }} schema
 * @returns {{ ok: boolean, errors: string[], warnings: string[], settings: object }}
 */
export function parseSettings(text, schema) {
  const result = { ok: false, errors: [], warnings: [], settings: {} };
  if (typeof text !== "string") {
    result.errors.push("the settings file is not text");
    return result;
  }
  if (utf8Length(text) > MAX_SETTINGS_BYTES) {
    result.errors.push(`the settings file is larger than ${MAX_SETTINGS_BYTES} bytes`);
    return result;
  }
  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    result.errors.push("the settings file is not valid JSON");
    return result;
  }
  if (!isPlainObject(data)) {
    result.errors.push("the settings file must contain a JSON object");
    return result;
  }
  if (data.format !== SETTINGS_FORMAT) {
    result.errors.push(`the file is not a Nivora settings file (format must be '${SETTINGS_FORMAT}')`);
    return result;
  }
  if (!Number.isInteger(data.version) || data.version < 1) {
    result.errors.push("the settings file has no valid version");
    return result;
  }
  if (data.version > SETTINGS_VERSION) {
    result.errors.push(
      `the file was made by a newer version of Nivora (format version ${data.version}, this one reads up to ${SETTINGS_VERSION})`
    );
    return result;
  }
  if (!isPlainObject(data.settings)) {
    result.errors.push("'settings' must be an object");
    return result;
  }
  for (const pref of Object.keys(data.settings)) {
    const entry = schema.byPref.get(pref);
    if (!entry) {
      result.warnings.push(`'${pref}' is not a setting Nivora manages; ignored`);
      continue;
    }
    const value = data.settings[pref];
    const problem = validateValue(entry, value);
    if (problem) {
      result.errors.push(`'${pref}' ${problem}`);
      continue;
    }
    result.settings[pref] = value;
  }
  result.ok = result.errors.length === 0;
  if (!result.ok) {
    result.settings = {};
  }
  return result;
}

/**
 * Write validated settings through the backend.
 *
 * @param {object} settings Output of `parseSettings`.
 * @param {{ byPref: Map<string, object> }} schema
 * @param {object} backend `{ set(pref, type, value) }`
 * @returns {{ applied: string[], failed: string[] }}
 */
export function applySettings(settings, schema, backend) {
  const applied = [];
  const failed = [];
  for (const [pref, value] of Object.entries(settings)) {
    const entry = schema.byPref.get(pref);
    if (!entry || validateValue(entry, value) !== null) {
      failed.push(pref); // never write what the schema does not vouch for
      continue;
    }
    try {
      backend.set(pref, entry.type, value);
      applied.push(pref);
    } catch {
      failed.push(pref);
    }
  }
  return { applied, failed };
}

/**
 * Return every whitelisted preference to its default.
 *
 * @param {{ entries: object[] }} schema
 * @param {object} backend `{ hasUserValue(pref), clear(pref) }`
 * @returns {string[]} The preferences that had a user value.
 */
export function resetSettings(schema, backend) {
  const cleared = [];
  for (const entry of schema.entries) {
    if (backend.hasUserValue(entry.pref)) {
      backend.clear(entry.pref);
      cleared.push(entry.pref);
    }
  }
  return cleared;
}

/**
 * Remove user values that are no longer valid (hand-edited profile, older or
 * newer version, wrong type), so the default applies instead.
 *
 * @param {{ entries: object[] }} schema
 * @param {object} backend `{ hasUserValue(pref), get(pref, type), clear(pref) }`
 * @returns {string[]} The preferences that were repaired.
 */
export function repairSettings(schema, backend) {
  const repaired = [];
  for (const entry of schema.entries) {
    if (!backend.hasUserValue(entry.pref)) {
      continue;
    }
    let valid = false;
    try {
      valid = validateValue(entry, backend.get(entry.pref, entry.type)) === null;
    } catch {
      valid = false;
    }
    if (!valid) {
      backend.clear(entry.pref);
      repaired.push(entry.pref);
    }
  }
  return repaired;
}

/**
 * The preferences Nivora manages. Names are real Zen / Nivora preferences
 * (prefs/zen/*.yaml, prefs/nivora/*.yaml); defaults are never repeated here,
 * the preference system owns them.
 */
export const SETTINGS_SCHEMA = defineSchema([
  // Appearance
  { pref: "zen.view.window.scheme", type: "int", group: "appearance", values: [0, 1, 2] },
  { pref: "zen.theme.accent-color", type: "string", group: "appearance", pattern: "AccentColor|#[0-9a-fA-F]{6}", maxLength: 12 },
  { pref: "zen.theme.content-element-separation", type: "int", group: "appearance", min: 0, max: 12 },
  { pref: "zen.theme.border-radius", type: "int", group: "appearance", min: -1, max: 24 },
  { pref: "nivora.ui.hide-zen-services", type: "bool", group: "appearance" },
  { pref: "nivora.ui.newtab-background", type: "bool", group: "appearance" },
  // Layout and density
  { pref: "zen.view.sidebar-expanded", type: "bool", group: "layout" },
  { pref: "zen.view.use-single-toolbar", type: "bool", group: "layout" },
  { pref: "zen.view.compact.hide-tabbar", type: "bool", group: "layout" },
  { pref: "zen.view.compact.hide-toolbar", type: "bool", group: "layout" },
  { pref: "zen.view.compact.enable-at-startup", type: "bool", group: "layout" },
  { pref: "zen.tabs.vertical", type: "bool", group: "layout" },
  { pref: "zen.tabs.vertical.right-side", type: "bool", group: "layout" },
  { pref: "zen.urlbar.behavior", type: "string", group: "layout", values: ["normal", "floating-on-type", "float"] },
  // Tabs and spaces
  { pref: "zen.tabs.select-recently-used-on-close", type: "bool", group: "tabs" },
  { pref: "zen.tabs.show-newtab-vertical", type: "bool", group: "tabs" },
  { pref: "zen.workspaces.continue-where-left-off", type: "bool", group: "spaces" },
  { pref: "zen.workspaces.wrap-around-navigation", type: "bool", group: "spaces" },
  { pref: "zen.workspaces.separate-essentials", type: "bool", group: "spaces" },
  { pref: "zen.workspaces.swipe-actions", type: "bool", group: "spaces" },
  // Glance and address bar
  { pref: "zen.glance.enabled", type: "bool", group: "behavior" },
  { pref: "zen.glance.activation-method", type: "string", group: "behavior", values: ["ctrl", "alt", "shift"] },
  { pref: "zen.urlbar.suggestions.quick-actions", type: "bool", group: "behavior" },
  // Animations (milliseconds; 0 turns the animation off). The first one is the master switch of
  // Nivora's own motion (docs/ANIMATIONS.md).
  { pref: "nivora.ui.animations", type: "bool", group: "animation" },
  { pref: "zen.workspaces.switch-animation-duration", type: "int", group: "animation", min: 0, max: 2000 },
  { pref: "zen.glance.animation-duration", type: "int", group: "animation", min: 0, max: 2000 },
  { pref: "zen.downloads.download-animation", type: "bool", group: "animation" },
  { pref: "zen.view.compact.animate-sidebar", type: "bool", group: "animation" },
]);
