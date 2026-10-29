/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * The first-run tour, without the browser: the steps, where the speech bubble goes and how much of the
 * text has been typed. Plain JavaScript so it can be unit tested under Node (tools/nivora/js-tests).
 * The window, the overlay and the strings are in NivoraTutorial.sys.mjs and browser/nivora.ftl.
 */

/**
 * The steps, in order. `target` is the selector of what the spotlight lights up (the first one that is
 * on screen); a step without one is told in the middle of the window. `crop` limits the spotlight to the top
 * `height` pixels of the target (the part of the tab list where Essentials sit). The title and the text of a
 * step are the strings `tour-<id>-title` and `tour-<id>-body`.
 */
export const STEPS = Object.freeze([
  { id: "hello", target: null, pose: "wave" },
  { id: "tabs", target: "#tabbrowser-tabs", pose: "idle" },
  { id: "palette", target: "#urlbar-container", pose: "working" },
  { id: "essentials", target: "#tabbrowser-tabs", crop: { height: 96 }, pose: "thinking" },
  { id: "spaces", target: ".zen-current-workspace-indicator", pose: "idle" },
  { id: "sidebar", target: "#zen-toggle-compact-mode", pose: "idle" },
  { id: "glance", target: null, pose: "listening" },
  { id: "split", target: null, pose: "idle" },
  { id: "library", target: "#zen-library-button", pose: "listening" },
  { id: "settings", target: "#PanelUI-menu-button", pose: "idle" },
  { id: "done", target: null, pose: "success" },
]);

/**
 * The guide is the pixel-art character of the Claude Code plugin for Ryoku (assets/sprites.png there): a sheet of 53
 * cells of 40 x 46 pixels in 10 columns, shown at an integer scale with no smoothing. `ANIMS` is its table of
 * animations as that plugin defines them (a cell index and how long it stays, in milliseconds), plus `talk`, a
 * mouth opening and closing that is used while the text is being typed.
 */
export const SPRITE = Object.freeze({ cellW: 40, cellH: 46, cols: 10, count: 53, scale: 3 });

const frames = (first, last, ms) => Array.from({ length: last - first + 1 }, (_, i) => [first + i, ms]);

export const ANIMS = Object.freeze({
  idle: { loop: true, frames: [[0, 900], [1, 700], [2, 900], [1, 700], [0, 1400], [3, 130], [0, 1800], [4, 700], [0, 1200]] },
  talk: { loop: true, frames: [[0, 120], [12, 120], [13, 120], [12, 120]] },
  wave: { loop: true, frames: frames(47, 52, 110) },
  thinking: { loop: true, frames: frames(15, 20, 500) },
  working: { loop: true, frames: frames(21, 28, 110) },
  listening: { loop: true, frames: [[29, 900], [30, 700], [31, 140], [32, 900]] },
  success: { loop: false, frames: [[33, 140], [34, 90], [35, 90], [36, 160], [37, 120], [38, 100], [39, 160], [40, 700]] },
});

/** The `background-position` (in pixels) that shows cell `index` of the sheet at the sprite's scale. */
export function framePosition(index, sprite = SPRITE) {
  const column = index % sprite.cols;
  const row = Math.floor(index / sprite.cols);
  return { x: -column * sprite.cellW * sprite.scale, y: -row * sprite.cellH * sprite.scale };
}

/** The name a key goes by on screen, for the strings that name the key that triggers Glance. */
export function keyName(pref, platform) {
  const names = { ctrl: "Ctrl", alt: "Alt", shift: "Shift", meta: platform === "macosx" ? "⌘" : "Meta" };
  return names[pref] ?? "Alt";
}

/** The arguments of a step's strings. */
export function argsFor(stepId, { glanceKey, platform }) {
  const shortcut = platform === "macosx" ? "⌘L" : "Ctrl+L";
  switch (stepId) {
    case "palette":
    case "done":
      return { shortcut };
    case "glance":
      return { key: keyName(glanceKey, platform) };
    default:
      return {};
  }
}

/**
 * The box the spotlight lights up: the target's, cropped when the step asks for it, grown by `pad`.
 *
 * @param {{ x: number, y: number, width: number, height: number } | null} rect
 * @param {{ height: number } | undefined} crop
 */
export function spotlightFor(rect, crop, pad = 6) {
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    return null;
  }
  const height = crop ? Math.min(crop.height, rect.height) : rect.height;
  return { x: rect.x - pad, y: rect.y - pad, width: rect.width + pad * 2, height: height + pad * 2 };
}

/**
 * Where the speech bubble goes: to the right of the spotlight when there is room, else to its left, else below
 * it, else above it; always inside the window; in the middle of the window when nothing is lit.
 *
 * @returns {{ left: number, top: number, side: "right" | "left" | "below" | "above" | "center" }}
 */
export function placeBubble(spot, bubble, viewport, gap = 20, margin = 12) {
  const clamp = (value, min, max) => Math.max(min, Math.min(value, Math.max(min, max)));
  const within = (left, top) => ({
    left: clamp(left, margin, viewport.width - bubble.width - margin),
    top: clamp(top, margin, viewport.height - bubble.height - margin),
  });
  if (!spot) {
    return { ...within((viewport.width - bubble.width) / 2, (viewport.height - bubble.height) / 2), side: "center" };
  }
  const middleY = spot.y + spot.height / 2 - bubble.height / 2;
  const middleX = spot.x + spot.width / 2 - bubble.width / 2;
  if (viewport.width - (spot.x + spot.width) >= bubble.width + gap + margin) {
    return { ...within(spot.x + spot.width + gap, middleY), side: "right" };
  }
  if (spot.x >= bubble.width + gap + margin) {
    return { ...within(spot.x - bubble.width - gap, middleY), side: "left" };
  }
  if (viewport.height - (spot.y + spot.height) >= bubble.height + gap + margin) {
    return { ...within(middleX, spot.y + spot.height + gap), side: "below" };
  }
  return { ...within(middleX, spot.y - bubble.height - gap), side: "above" };
}

/** How many characters of a text are typed `elapsed` milliseconds after it started; all of them when `perChar` is 0. */
export function typedLength(text, elapsed, perChar) {
  if (!perChar || perChar <= 0) {
    return text.length;
  }
  return Math.max(0, Math.min(text.length, Math.floor(elapsed / perChar)));
}

/** The step after `index`, or `null` after the last one; `before` does the same backwards. */
export function after(index, count = STEPS.length) {
  return index + 1 < count ? index + 1 : null;
}

export function before(index) {
  return index > 0 ? index - 1 : null;
}
