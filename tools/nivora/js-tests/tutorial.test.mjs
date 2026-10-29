/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  ANIMS,
  SPRITE,
  STEPS,
  after,
  argsFor,
  before,
  framePosition,
  keyName,
  placeBubble,
  spotlightFor,
  typedLength,
} from "../../../src/nivora/modules/NivoraTutorialCore.mjs";

const FTL = readFileSync(new URL("../../../locales/en-US/browser/browser/nivora.ftl", import.meta.url), "utf8");

test("every step has a title and a text in nivora.ftl, and ids are unique", () => {
  const ids = STEPS.map(step => step.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ids) {
    assert.match(FTL, new RegExp(`^tour-${id}-title = .+`, "m"), `title of ${id}`);
    assert.match(FTL, new RegExp(`^tour-${id}-body = .+`, "m"), `body of ${id}`);
  }
  for (const key of ["tour-next", "tour-back", "tour-skip", "tour-finish", "tour-step-of", "nivora-action-take-tour"]) {
    assert.match(FTL, new RegExp(`^${key} = .+`, "m"), key);
  }
});

test("the strings use only the variables the code passes", () => {
  for (const step of STEPS) {
    const given = Object.keys(argsFor(step.id, { glanceKey: "alt", platform: "linux" }));
    const text = FTL.split("\n").filter(line => line.startsWith(`tour-${step.id}-`)).join("\n");
    const used = [...text.matchAll(/\{ \$(\w+) \}/g)].map(match => match[1]);
    for (const name of used) {
      assert.ok(given.includes(name), `${step.id} uses $${name} but is not given it`);
    }
  }
});

test("the tour starts with a welcome and ends with a goodbye, neither pointing at anything", () => {
  assert.equal(STEPS[0].id, "hello");
  assert.equal(STEPS[0].target, null);
  assert.equal(STEPS.at(-1).id, "done");
  assert.equal(STEPS.at(-1).target, null);
});

test("moving between steps stops at both ends", () => {
  assert.equal(before(0), null);
  assert.equal(before(3), 2);
  assert.equal(after(STEPS.length - 1), null);
  assert.equal(after(0), 1);
});

test("the key that triggers Glance is named for the platform", () => {
  assert.equal(keyName("alt", "linux"), "Alt");
  assert.equal(keyName("meta", "macosx"), "⌘");
  assert.equal(keyName("nonsense", "linux"), "Alt");
  assert.equal(argsFor("palette", { glanceKey: "alt", platform: "macosx" }).shortcut, "⌘L");
  assert.equal(argsFor("glance", { glanceKey: "shift", platform: "linux" }).key, "Shift");
});

test("the spotlight grows the target by the padding and can be cropped", () => {
  assert.equal(spotlightFor(null), null);
  assert.equal(spotlightFor({ x: 0, y: 0, width: 0, height: 20 }), null);
  assert.deepEqual(spotlightFor({ x: 10, y: 20, width: 100, height: 400 }), { x: 4, y: 14, width: 112, height: 412 });
  assert.deepEqual(spotlightFor({ x: 10, y: 20, width: 100, height: 400 }, { height: 96 }, 4), {
    x: 6,
    y: 16,
    width: 108,
    height: 104,
  });
  assert.equal(spotlightFor({ x: 0, y: 0, width: 50, height: 30 }, { height: 96 }, 0).height, 30);
});

test("the bubble goes to the right of the spotlight when there is room, and stays inside the window", () => {
  const viewport = { width: 1000, height: 700 };
  const bubble = { width: 460, height: 200 };
  const spot = { x: 5, y: 60, width: 190, height: 900 };
  const placed = placeBubble(spot, bubble, viewport);
  assert.equal(placed.side, "right");
  assert.equal(placed.left, 5 + 190 + 20);
  assert.ok(placed.top >= 12 && placed.top + bubble.height <= viewport.height - 12);
});

test("with no room on the right it goes to the left, then below, then above", () => {
  const bubble = { width: 460, height: 200 };
  assert.equal(placeBubble({ x: 700, y: 100, width: 250, height: 60 }, bubble, { width: 1000, height: 700 }).side, "left");
  assert.equal(placeBubble({ x: 100, y: 100, width: 800, height: 60 }, bubble, { width: 1000, height: 700 }).side, "below");
  assert.equal(placeBubble({ x: 100, y: 500, width: 800, height: 60 }, bubble, { width: 1000, height: 700 }).side, "above");
});

test("with nothing lit the bubble is in the middle of the window", () => {
  const placed = placeBubble(null, { width: 400, height: 200 }, { width: 1000, height: 600 });
  assert.deepEqual(placed, { left: 300, top: 200, side: "center" });
});

test("a window smaller than the bubble still puts it on screen", () => {
  const placed = placeBubble(null, { width: 460, height: 200 }, { width: 300, height: 150 });
  assert.equal(placed.left, 12);
  assert.equal(placed.top, 12);
});

test("the text is typed at the given pace, all at once when the pace is zero", () => {
  assert.equal(typedLength("hello", 0, 16), 0);
  assert.equal(typedLength("hello", 40, 16), 2);
  assert.equal(typedLength("hello", 10000, 16), 5);
  assert.equal(typedLength("hello", 0, 0), 5);
  assert.equal(typedLength("hello", -5, 16), 0);
});

test("every step asks for an animation the guide has", () => {
  for (const step of STEPS) {
    assert.ok(ANIMS[step.pose], `${step.id} asks for ${step.pose}`);
  }
});

test("every cell of every animation exists in the sheet, and each frame lasts a visible time", () => {
  for (const [name, animation] of Object.entries(ANIMS)) {
    assert.ok(animation.frames.length > 0, name);
    for (const [cell, ms] of animation.frames) {
      assert.ok(Number.isInteger(cell) && cell >= 0 && cell < SPRITE.count, `${name}: cell ${cell}`);
      assert.ok(ms >= 50 && ms <= 2000, `${name}: ${ms} ms`);
    }
  }
});

test("a cell is found in the sheet by column and row, at the sprite's scale", () => {
  assert.deepEqual(framePosition(0), { x: -0, y: -0 });
  assert.deepEqual(framePosition(1), { x: -120, y: -0 });
  assert.deepEqual(framePosition(10), { x: -0, y: -138 });
  assert.deepEqual(framePosition(52), { x: -240, y: -690 });
});

test("the Spanish tour names the interface's own labels as they are on screen", () => {
  assert.match(FTL, /tour-tabs-body = .*New Tab/);
  assert.match(FTL, /tour-essentials-body = .*Add to Essentials/);
  assert.match(FTL, /tour-split-body = .*Join 2 Tabs/);
  assert.match(FTL, /tour-done-body = .*«tutorial»/);
});
