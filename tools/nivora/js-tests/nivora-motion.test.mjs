/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import test from "node:test";
import assert from "node:assert/strict";

import { highlightFor } from "../../../src/nivora/modules/NivoraMotion.sys.mjs";

test("no selected row: the bar is invisible and takes no space", () => {
  assert.deepEqual(highlightFor(null), { y: 0, height: 0, opacity: 0 });
});

test("the bar covers the padding box of the row, inside its transparent border", () => {
  // A 49 px tall row with a 2 px border above and below paints its background on 45 px.
  const row = { offsetTop: 10, clientTop: 2, clientHeight: 45 };
  assert.deepEqual(highlightFor(row), { y: 12, height: 45, opacity: 1 });
});

test("a row without a border is covered edge to edge", () => {
  assert.deepEqual(highlightFor({ offsetTop: 59, clientTop: 0, clientHeight: 49 }), { y: 59, height: 49, opacity: 1 });
});
