/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * The parts of Nivora's motion that CSS cannot do on its own (docs/ANIMATIONS.md).
 *
 * Today: the command palette's highlight. CSS draws a bar behind the selected row and springs it
 * from row to row; this module only tells the stylesheet where the selected row is, in two custom
 * properties. The rows keep their own layout and selection: if this script does not run, or motion
 * is off, the selected row keeps its normal background and nothing else changes.
 *
 * Importing this module must never throw.
 */

const ANIMATIONS_PREF = "nivora.ui.animations";
const STARTUP_TOPIC = "browser-delayed-startup-finished";

const log = {
  error: (...args) => console.error("[Nivora]", ...args),
};

/**
 * Where the highlight bar goes: the selected row's offset and height inside the results list.
 * Layout offsets are used, not bounding boxes, so a row that is still sliding in by its entrance
 * animation is measured where it will rest.
 *
 * @param {{ offsetTop: number, offsetHeight: number } | null} row
 * @returns {{ y: number, height: number, opacity: number }}
 */
export function highlightFor(row) {
  if (!row) {
    return { y: 0, height: 0, opacity: 0 };
  }
  return { y: row.offsetTop, height: row.offsetHeight, opacity: 1 };
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
    const row = results.querySelector(".urlbarView-row-inner[selected]")?.closest(".urlbarView-row");
    const box = highlightFor(row);
    const first = box.opacity === 1 && !this.#visible;
    if (first) {
      urlbar.setAttribute("nivora-glide-snap", "");
    }
    results.style.setProperty("--nivora-sel-y", `${box.y}px`);
    results.style.setProperty("--nivora-sel-h", `${box.height}px`);
    results.style.setProperty("--nivora-sel-o", String(box.opacity));
    this.#visible = box.opacity === 1;
    if (first) {
      this.#window.requestAnimationFrame(() => urlbar.removeAttribute("nivora-glide-snap"));
    }
  }
}

const attached = new WeakSet();

function attach(window) {
  if (attached.has(window) || window.closed) {
    return;
  }
  attached.add(window);
  try {
    new PaletteHighlight(window);
  } catch (e) {
    log.error("could not attach the palette highlight", e);
  }
}

let started = false;

export const NivoraMotion = {
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
