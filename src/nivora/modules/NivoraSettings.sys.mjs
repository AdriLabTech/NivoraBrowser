/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Browser-side binding of the Nivora central settings: preferences as the
 * backend, a file picker for export and import, native dialogs for results.
 * All decisions (what is valid, what may be exported) live in
 * NivoraSettingsCore.mjs; this file only connects them to Firefox.
 */

import {
  MAX_SETTINGS_BYTES,
  SETTINGS_SCHEMA,
  applySettings,
  exportSettings,
  parseSettings,
  repairSettings,
  resetSettings,
} from "resource:///modules/nivora/NivoraSettingsCore.mjs";
import { t } from "resource:///modules/nivora/NivoraL10n.sys.mjs";

export const prefsBackend = {
  hasUserValue: pref => Services.prefs.prefHasUserValue(pref),
  get(pref, type) {
    switch (type) {
      case "bool":
        return Services.prefs.getBoolPref(pref);
      case "int":
        return Services.prefs.getIntPref(pref);
      case "string":
        return Services.prefs.getStringPref(pref);
    }
    throw new Error(`unsupported type ${type}`);
  },
  set(pref, type, value) {
    switch (type) {
      case "bool":
        return Services.prefs.setBoolPref(pref, value);
      case "int":
        return Services.prefs.setIntPref(pref, value);
      case "string":
        return Services.prefs.setStringPref(pref, value);
    }
    throw new Error(`unsupported type ${type}`);
  },
  clear: pref => Services.prefs.clearUserPref(pref),
};

function pickFile(window, mode, title, defaultName) {
  const nsIFilePicker = Ci.nsIFilePicker;
  const picker = Cc["@mozilla.org/filepicker;1"].createInstance(nsIFilePicker);
  picker.init(window.browsingContext, title, mode);
  if (defaultName) {
    picker.defaultString = defaultName;
    picker.defaultExtension = "json";
  }
  picker.appendFilters(nsIFilePicker.filterAll);
  return new Promise(resolve => {
    picker.open(result => {
      resolve(result === nsIFilePicker.returnOK && picker.file ? picker.file.path : null);
    });
  });
}

export const NivoraSettings = {
  schema: SETTINGS_SCHEMA,

  /** The settings the user changed, as text in the exchange format. */
  exportText() {
    return JSON.stringify(exportSettings(SETTINGS_SCHEMA, prefsBackend), null, 2) + "\n";
  },

  /** Validate exchange-format text without applying it. */
  parseText(text) {
    return parseSettings(text, SETTINGS_SCHEMA);
  },

  /** Apply settings returned by `parseText`. */
  apply(settings) {
    return applySettings(settings, SETTINGS_SCHEMA, prefsBackend);
  },

  /** Return every managed setting to its default. */
  reset() {
    return resetSettings(SETTINGS_SCHEMA, prefsBackend);
  },

  /** Drop user values that are no longer valid. Safe to call at startup. */
  repair() {
    return repairSettings(SETTINGS_SCHEMA, prefsBackend);
  },

  /**
   * Ask where to save, then write the settings.
   *
   * @param {Window} window
   * @returns {Promise<{ ok: boolean, count?: number }>} ok is false when the
   *   user cancelled or the file could not be written.
   */
  async exportToFile(window) {
    const path = await pickFile(
      window,
      Ci.nsIFilePicker.modeSave,
      t("nivora-settings-export-title"),
      "nivora-settings"
    );
    if (!path) {
      return { ok: false };
    }
    try {
      const text = this.exportText();
      await IOUtils.writeUTF8(path, text);
      const count = Object.keys(JSON.parse(text).settings).length;
      Services.prompt.alert(window, t("nivora-dialog-title"), t("nivora-settings-export-done", { count }));
      return { ok: true, count };
    } catch (e) {
      console.error("[Nivora] settings export failed", e);
      Services.prompt.alert(window, t("nivora-dialog-title"), t("nivora-settings-export-failed"));
      return { ok: false };
    }
  },

  /**
   * Ask which file to read, read it (size-limited) and validate it. Problems
   * are shown to the user. Nothing is applied.
   *
   * @param {Window} window
   * @returns {Promise<object|null>} The parse result, or null when cancelled
   *   or invalid.
   */
  async readFromFile(window) {
    const path = await pickFile(window, Ci.nsIFilePicker.modeOpen, t("nivora-settings-import-title"));
    if (!path) {
      return null;
    }
    let text;
    try {
      const { size } = await IOUtils.stat(path);
      if (size > MAX_SETTINGS_BYTES) {
        Services.prompt.alert(window, t("nivora-dialog-title"), t("nivora-settings-import-too-large"));
        return null;
      }
      text = await IOUtils.readUTF8(path);
    } catch (e) {
      console.error("[Nivora] settings import: file unreadable", e);
      Services.prompt.alert(window, t("nivora-dialog-title"), t("nivora-settings-import-unreadable"));
      return null;
    }
    const parsed = this.parseText(text);
    if (!parsed.ok) {
      const reasons = parsed.errors.map(error => `\n- ${error}`).join("");
      Services.prompt.alert(window, t("nivora-dialog-title"), t("nivora-settings-import-invalid", { reasons }));
      return null;
    }
    return parsed;
  },
};
