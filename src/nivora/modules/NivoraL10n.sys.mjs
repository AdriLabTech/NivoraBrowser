/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

const lazy = {};

ChromeUtils.defineLazyGetter(lazy, "l10n", () => {
  return new Localization(["browser/nivora.ftl"], true);
});

// Fluent wraps placeables in Unicode isolation marks; they show up as stray
// glyphs in some native dialogs.
const ISOLATION_MARKS = /[⁨⁩]/g;

/**
 * Look up a Nivora string in the language in use.
 *
 * @param {string} id A message id from browser/nivora.ftl.
 * @param {object} [args] Values for the message's variables.
 * @returns {string} The text, or the id itself when the message is missing, so
 *   a missing translation is visible instead of blank.
 */
export function t(id, args) {
  const text = lazy.l10n.formatValueSync(id, args);
  return text ? text.replace(ISOLATION_MARKS, "") : id;
}
