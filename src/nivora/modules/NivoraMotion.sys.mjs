/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * The parts of Nivora's motion that CSS cannot do on its own (docs/ANIMATIONS.md).
 *
 * - The command palette's highlight. CSS draws a bar behind the selected row and springs it from
 *   row to row; this module only tells the stylesheet where the selected row is, in two custom
 *   properties. The rows keep their own layout and selection: if this script does not run, or
 *   motion is off, the selected row keeps its normal background and nothing else changes.
 * - The palette's exit. Zen takes the palette away in one step (the same element goes back to being the
 *   address field), so a copy of what was on screen is left behind for a moment and fades away.
 * - The off switch for the animations that scripts start. Zen and Firefox ask `gReduceMotion` before
 *   they animate, and it honours the `gReduceMotionOverride` hook, so turning `nivora.ui.animations`
 *   off puts the window in the same state as the system's "reduce motion" setting.
 * - Helpers for the animations that scripts start (tabs opening and closing): whether motion is on
 *   in a window, and the same spring curves the stylesheets use, so a scripted animation moves
 *   like a styled one.
 *
 * Importing this module must never throw.
 */

const ANIMATIONS_PREF = "nivora.ui.animations";
const XHTML_NS = "http://www.w3.org/1999/xhtml";
const STARTUP_TOPIC = "browser-delayed-startup-finished";
// The window assembles itself over about half a second; after this the start-up animation is spent.
const BOOT_SETTLED_MS = 1200;
// The ghost removes itself when its animation ends; this is only for a window that never paints it.
const GHOST_LIMIT_MS = 600;

const log = {
  error: (...args) => console.error("[Nivora]", ...args),
};

/**
 * Where the highlight bar goes: the area a selected row paints its background on, which is its
 * padding box (the row has a transparent border), measured inside the results list. Layout offsets
 * are used, not bounding boxes, so a row that is still sliding in by its entrance animation is
 * measured where it will rest.
 *
 * @param {{ offsetTop: number, clientTop: number, clientHeight: number } | null} row
 * @returns {{ y: number, height: number, opacity: number }}
 */
export function highlightFor(row) {
  if (!row) {
    return { y: 0, height: 0, opacity: 0 };
  }
  return { y: row.offsetTop + row.clientTop, height: row.clientHeight, opacity: 1 };
}

class PaletteHighlight {
  #window;
  #urlbar;
  #observer;
  #prefObserver;
  #pending = false;
  #visible = false;

  constructor(window) {
    this.#window = window;
    this.#urlbar = window.document.getElementById("urlbar");
    if (!this.#urlbar) {
      return;
    }
    this.#observer = new window.MutationObserver(() => this.#schedule());
    this.#observer.observe(this.#urlbar, {
      attributes: true,
      attributeFilter: ["selected", "open", "zen-floating-urlbar"],
      subtree: true,
      childList: true,
    });
    // Turning motion off (or on) while the palette is open takes effect at once.
    this.#prefObserver = () => this.#schedule();
    Services.prefs.addObserver(ANIMATIONS_PREF, this.#prefObserver);
    window.addEventListener(
      "unload",
      () => {
        this.#observer.disconnect();
        Services.prefs.removeObserver(ANIMATIONS_PREF, this.#prefObserver);
      },
      { once: true }
    );
  }

  get #motionOn() {
    return (
      Services.prefs.getBoolPref(ANIMATIONS_PREF, true) &&
      !this.#window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  #schedule() {
    if (this.#pending) {
      return;
    }
    this.#pending = true;
    this.#window.requestAnimationFrame(() => {
      this.#pending = false;
      try {
        this.#update();
      } catch (e) {
        log.error("palette highlight", e);
      }
    });
  }

  #update() {
    const urlbar = this.#urlbar;
    const active =
      this.#motionOn &&
      urlbar.getAttribute("zen-floating-urlbar") === "true" &&
      urlbar.hasAttribute("open");
    if (!active) {
      this.#visible = false;
      urlbar.removeAttribute("nivora-glide");
      urlbar.removeAttribute("nivora-glide-snap");
      return;
    }
    const results = urlbar.querySelector(".urlbarView-results");
    if (!results) {
      return;
    }
    // The bar is positioned relative to the list, which the stylesheet makes positioned while gliding.
    urlbar.setAttribute("nivora-glide", "");
    const row = results.querySelector(".urlbarView-row[selected]");
    const box = highlightFor(row);
    const first = box.opacity === 1 && !this.#visible;
    if (first) {
      urlbar.setAttribute("nivora-glide-snap", "");
    }
    results.style.setProperty("--nivora-sel-y", `${box.y}px`);
    results.style.setProperty("--nivora-sel-h", `${box.height}px`);
    results.style.setProperty("--nivora-sel-o", String(box.opacity));
    if (row) {
      results.style.setProperty("--nivora-sel-r", this.#window.getComputedStyle(row).borderTopLeftRadius);
    }
    this.#visible = box.opacity === 1;
    if (first) {
      this.#window.requestAnimationFrame(() => urlbar.removeAttribute("nivora-glide-snap"));
    }
  }
}

/**
 * Leaves a fading copy of the palette behind when it closes.
 *
 * The close is a single synchronous step: the view loses `open`, the urlbar loses its floating
 * attributes and its popover. A MutationObserver callback runs after that step but before the next
 * frame is painted, and the rows are still in the DOM (they are cleared by the next query), so a clone
 * with the three attributes put back is styled exactly as the palette was. It is shown as a popover of
 * its own, in the top layer like the original, so it needs no positioning of its own.
 */
class PaletteExit {
  #window;
  #urlbar;
  #observer;
  #ghost = null;
  #timer = 0;

  constructor(window) {
    this.#window = window;
    this.#urlbar = window.document.getElementById("urlbar");
    if (!this.#urlbar) {
      return;
    }
    this.#observer = new window.MutationObserver(records => {
      try {
        this.#onMutations(records);
      } catch (e) {
        log.error("palette exit", e);
      }
    });
    this.#observer.observe(this.#urlbar, {
      attributes: true,
      attributeFilter: ["open", "zen-floating-urlbar"],
      attributeOldValue: true,
    });
    window.addEventListener(
      "unload",
      () => {
        this.#observer.disconnect();
        this.#remove();
      },
      { once: true }
    );
  }

  #onMutations(records) {
    const urlbar = this.#urlbar;
    if (urlbar.hasAttribute("open")) {
      this.#remove();
      return;
    }
    const wasOpen = records.some(r => r.attributeName === "open" && r.oldValue !== null);
    const wasFloating =
      records.some(r => r.attributeName === "zen-floating-urlbar" && r.oldValue === "true") ||
      urlbar.getAttribute("zen-floating-urlbar") === "true";
    if (wasOpen && wasFloating && motionOn(this.#window)) {
      this.#leave();
    }
  }

  #leave() {
    this.#remove();
    const urlbar = this.#urlbar;
    // A plain element, not a clone of the urlbar: the urlbar is a custom element, and a clone of it
    // would be a second, uninitialised address field. The styles are written for `#urlbar` and its
    // attributes, which the copy keeps, and its children are ordinary markup.
    const ghost = urlbar.ownerDocument.createElementNS(XHTML_NS, "div");
    for (const { name, value } of urlbar.attributes) {
      ghost.setAttribute(name, value);
    }
    ghost.classList.add("nivora-palette-ghost");
    ghost.setAttribute("open", "");
    ghost.setAttribute("zen-floating-urlbar", "true");
    ghost.setAttribute("breakout-extend", "true");
    ghost.setAttribute("popover", "manual");
    ghost.setAttribute("inert", "");
    ghost.setAttribute("aria-hidden", "true");
    for (const child of urlbar.children) {
      ghost.append(child.cloneNode(true));
    }
    const source = urlbar.inputField;
    const input = ghost.querySelector(".urlbar-input");
    if (source && input) {
      input.value = source.value;
    }
    urlbar.after(ghost);
    ghost.showPopover();
    this.#ghost = ghost;
    ghost.addEventListener("animationend", () => this.#remove(), { once: true });
    this.#timer = this.#window.setTimeout(() => this.#remove(), GHOST_LIMIT_MS);
  }

  #remove() {
    this.#window.clearTimeout(this.#timer);
    this.#ghost?.remove();
    this.#ghost = null;
  }
}

/** Motion is on in `window`: the setting is on and the system does not ask for reduced motion. */
function motionOn(window) {
  return (
    Services.prefs.getBoolPref(ANIMATIONS_PREF, true) &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * The easing of a spring token (`smooth`, `snappy`, `settle`, `bouncy`, `elastic`) as `linear(...)`, ready
 * for Element.animate. Falls back to a plain ease-out when the stylesheet does not provide it.
 *
 * @param {Window} window
 * @param {string} name
 */
function springEasing(window, name) {
  try {
    const value = window
      .getComputedStyle(window.document.documentElement)
      .getPropertyValue(`--nivora-spring-${name}`)
      .trim();
    return value.startsWith("linear(") ? value : "ease-out";
  } catch (e) {
    return "ease-out";
  }
}

/**
 * Mirrors the `nivora.ui.animations` setting into the window's reduce-motion state. It only ever
 * undoes what it did itself, so a window that asked for reduced motion some other way keeps it.
 */
class MotionSwitch {
  #window;
  #owned = false;
  #observer = () => this.#apply();

  constructor(window) {
    this.#window = window;
    this.#apply();
    Services.prefs.addObserver(ANIMATIONS_PREF, this.#observer);
    window.addEventListener("unload", () => Services.prefs.removeObserver(ANIMATIONS_PREF, this.#observer), {
      once: true,
    });
  }

  #apply() {
    const off = !Services.prefs.getBoolPref(ANIMATIONS_PREF, true);
    if (off) {
      this.#owned = true;
      this.#window.gReduceMotionOverride = true;
    } else if (this.#owned) {
      this.#owned = false;
      this.#window.gReduceMotionOverride = undefined;
    }
  }
}

const attached = new WeakSet();

function attach(window) {
  if (attached.has(window) || window.closed) {
    return;
  }
  attached.add(window);
  for (const Feature of [PaletteHighlight, PaletteExit, MotionSwitch]) {
    try {
      new Feature(window);
    } catch (e) {
      log.error(`could not attach ${Feature.name}`, e);
    }
  }
  // The start-up animation is only for the first assembly of a window: leaving full screen must not
  // play it again.
  window.setTimeout(() => window.document.documentElement?.setAttribute("nivora-booted", ""), BOOT_SETTLED_MS);
}

let started = false;

export const NivoraMotion = {
  motionOn,
  springEasing,

  /** Attach to every browser window, now and later. Safe to call more than once. */
  init() {
    if (started) {
      return;
    }
    started = true;
    Services.obs.addObserver({ observe: subject => attach(subject) }, STARTUP_TOPIC);
    for (const window of Services.wm.getEnumerator("navigator:browser")) {
      if (window.gBrowserInit?.delayedStartupFinished) {
        attach(window);
      }
    }
  },
};
