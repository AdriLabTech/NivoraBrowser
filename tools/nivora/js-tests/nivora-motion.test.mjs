/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import test from "node:test";
import assert from "node:assert/strict";

import { glassGeometry, highlightFor } from "../../../src/nivora/modules/NivoraMotion.sys.mjs";

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

test("the glass copy is placed where the page paints the picture, from the palette's corner", () => {
  // A 1600 x 1000 page at (200, 60) is wider than 16:9 allows at its height, so the picture is as wide as the
  // page (900 px tall, 100 px of it cut) and anchored at 46 % of the slack: the slack is 100 px, so 46 px up.
  const page = { x: 200, y: 60, width: 1600, height: 800 };
  const geometry = glassGeometry(page, { x: 500, y: 340 });
  assert.equal(geometry.size, "1600px 900px");
  assert.equal(geometry.position, "-300px " + (60 + (800 - 900) * 0.46 - 340) + "px");
});

test("a page taller than 16:9 gets a picture as tall as the page, centred on its width", () => {
  const geometry = glassGeometry({ x: 0, y: 0, width: 800, height: 900 }, { x: 0, y: 0 });
  assert.equal(geometry.size, "1600px 900px");
  assert.equal(geometry.position, "-400px 0px");
});
