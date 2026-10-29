/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * The first-run tour: the pixel-art guide (the character of the Claude Code plugin for Ryoku) walks through the sections of the browser, lighting up each one
 * in turn and talking in a speech bubble. It starts by itself in the first window of a profile that has not seen
 * it (`nivora.tutorial.seen`), and can be started again from Settings (Look and Feel), from the command palette or
 * by notifying `nivora-start-tour`. Escape leaves it. The steps and the layout maths are in
 * NivoraTutorialCore.mjs; the look is nivora-tutorial.inc.css; the words are browser/nivora.ftl.
 *
 * Importing this module must never throw.
 */

import {
  ANIMS,
  STEPS,
  after,
  argsFor,
  before,
  framePosition,
  placeBubble,
  spotlightFor,
  typedLength,
} from "resource:///modules/nivora/NivoraTutorialCore.mjs";
import { t } from "resource:///modules/nivora/NivoraL10n.sys.mjs";
import { NivoraMotion } from "resource:///modules/nivora/NivoraMotion.sys.mjs";

const XHTML_NS = "http://www.w3.org/1999/xhtml";
const SEEN_PREF = "nivora.tutorial.seen";
const START_TOPIC = "nivora-start-tour";
const STARTUP_TOPIC = "browser-delayed-startup-finished";
// The window assembles itself over half a second; the tour waits for that and a moment more.
const FIRST_RUN_DELAY_MS = 2200;
// How long a character takes to type.
const TYPE_MS = 16;

const log = {
  error: (...args) => console.error("[Nivora]", ...args),
};

const { AppConstants } = ChromeUtils.importESModule("resource://gre/modules/AppConstants.sys.mjs");

function make(doc, tag, className, text) {
  const node = doc.createElementNS(XHTML_NS, tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

/** The tour in one window. */
class Tour {
  #window;
  #doc;
  #onEnd;
  #index = 0;
  #typing = 0;
  #animating = 0;
  #root;
  #spot;
  #bubble;
  #mascot;
  #title;
  #body;
  #count;
  #back;
  #next;
  #skip;

  constructor(window, onEnd) {
    this.#window = window;
    this.#doc = window.document;
    this.#onEnd = onEnd;
    this.#build();
  }

  #build() {
    const doc = this.#doc;
    this.#root = make(doc, "div", "nivora-tour");
    this.#root.setAttribute("role", "dialog");
    this.#root.setAttribute("aria-modal", "true");
    this.#spot = make(doc, "div", "nivora-tour-spot");
    this.#bubble = make(doc, "div", "nivora-tour-bubble");
    this.#mascot = make(doc, "div", "nivora-tour-mascot");
    this.#mascot.setAttribute("aria-hidden", "true");
    const text = make(doc, "div", "nivora-tour-text");
    this.#title = make(doc, "h2", "nivora-tour-title");
    this.#body = make(doc, "p", "nivora-tour-body");
    text.append(this.#title, this.#body);
    const foot = make(doc, "div", "nivora-tour-foot");
    this.#count = make(doc, "span", "nivora-tour-count");
    this.#skip = make(doc, "button", "nivora-tour-button nivora-tour-skip", t("tour-skip"));
    this.#back = make(doc, "button", "nivora-tour-button", t("tour-back"));
    this.#next = make(doc, "button", "nivora-tour-button nivora-tour-primary", t("tour-next"));
    for (const button of [this.#skip, this.#back, this.#next]) {
      button.type = "button";
    }
    this.#skip.addEventListener("click", () => this.end());
    this.#back.addEventListener("click", () => this.#go(before(this.#index)));
    this.#next.addEventListener("click", () => this.#go(after(this.#index)));
    foot.append(this.#count, this.#skip, this.#back, this.#next);
    this.#bubble.append(this.#mascot, text, foot);
    this.#root.append(this.#spot, this.#bubble);
  }

  get window() {
    return this.#window;
  }

  /** Whether this tour is still on screen: its window is open and its overlay is in the document. */
  get alive() {
    return !this.#window.closed && this.#root.isConnected;
  }

  start() {
    this.#doc.documentElement.append(this.#root);
    this.#doc.documentElement.setAttribute("nivora-touring", "");
    this.#window.addEventListener("keydown", this, true);
    this.#window.addEventListener("resize", this);
    // A window closed in the middle of the tour must not leave a tour behind that blocks every later request.
    this.#window.addEventListener("unload", this.#onUnload, { once: true });
    this.#go(0);
  }

  /** Back to the first step, for a request made while the tour is already showing. */
  restart() {
    this.#go(0);
  }

  #onUnload = () => this.end(false);

  /** Take the tour away. `markSeen` is false when it was not finished by the user (the window was closed). */
  end(markSeen = true) {
    this.#window.clearInterval(this.#typing);
    this.#window.clearTimeout(this.#animating);
    this.#window.removeEventListener("keydown", this, true);
    this.#window.removeEventListener("resize", this);
    this.#window.removeEventListener("unload", this.#onUnload);
    this.#root.remove();
    this.#doc.documentElement?.removeAttribute("nivora-touring");
    this.#onEnd(markSeen);
  }

  handleEvent(event) {
    if (event.type === "resize") {
      this.#place(false);
      return;
    }
    switch (event.key) {
      case "Escape":
        event.preventDefault();
        event.stopPropagation();
        this.end();
        break;
      case "ArrowRight":
        event.preventDefault();
        event.stopPropagation();
        this.#go(after(this.#index));
        break;
      case "ArrowLeft":
        event.preventDefault();
        event.stopPropagation();
        this.#go(before(this.#index));
        break;
    }
  }

  /** Go to a step; past the last one the tour is over. */
  #go(index) {
    if (index === null) {
      this.end();
      return;
    }
    this.#index = index;
    const step = STEPS[index];
    const args = argsFor(step.id, {
      glanceKey: Services.prefs.getStringPref("zen.glance.activation-method", "alt"),
      platform: AppConstants.platform,
    });
    this.#title.textContent = t(`tour-${step.id}-title`, args);
    this.#full = t(`tour-${step.id}-body`, args);
    this.#bubble.setAttribute("aria-label", `${this.#title.textContent}. ${this.#full}`);
    this.#count.textContent = t("tour-step-of", { n: index + 1, total: STEPS.length });
    this.#back.disabled = index === 0;
    this.#next.textContent = t(index === STEPS.length - 1 ? "tour-finish" : "tour-next");
    // The bubble is measured with all its text so it does not change size while it is being typed.
    this.#body.textContent = this.#full;
    this.#place(true);
    this.#next.focus();
  }

  /** The animation a step asks for; the guide talks while an idle step's text is being typed. */
  get #pose() {
    return STEPS[this.#index].pose ?? "idle";
  }

  #full = "";

  /** Light up the target and put the bubble next to it. */
  #place(retype) {
    const step = STEPS[this.#index];
    const doc = this.#doc;
    let rect = null;
    for (const selector of step.target ? [step.target] : []) {
      const element = doc.querySelector(selector);
      const box = element?.getBoundingClientRect();
      if (box && box.width > 0 && box.height > 0) {
        rect = box;
        break;
      }
    }
    const spot = spotlightFor(rect, step.crop);
    const root = doc.documentElement;
    const viewport = { width: root.clientWidth, height: root.clientHeight };
    if (spot) {
      Object.assign(this.#spot.style, {
        left: `${spot.x}px`,
        top: `${spot.y}px`,
        width: `${spot.width}px`,
        height: `${spot.height}px`,
      });
      this.#spot.dataset.lit = "true";
    } else {
      // Nothing to light: the spotlight closes to a point in the middle, which dims the whole window.
      Object.assign(this.#spot.style, {
        left: `${viewport.width / 2}px`,
        top: `${viewport.height / 2}px`,
        width: "0px",
        height: "0px",
      });
      this.#spot.dataset.lit = "false";
    }
    this.#bubble.style.width = "";
    const size = { width: this.#bubble.offsetWidth, height: this.#bubble.offsetHeight };
    const { left, top, side } = placeBubble(spot, size, viewport);
    this.#bubble.style.left = `${left}px`;
    this.#bubble.style.top = `${top}px`;
    this.#bubble.style.minHeight = `${size.height}px`;
    this.#bubble.dataset.side = side;
    if (retype) {
      this.#type();
    }
  }

  /** Type the step's text, a letter at a time, while the guide talks. */
  #type() {
    const window = this.#window;
    window.clearInterval(this.#typing);
    const text = this.#full;
    const perChar = NivoraMotion.motionOn(window) ? TYPE_MS : 0;
    if (!perChar) {
      this.#body.textContent = text;
      this.#play(this.#pose);
      return;
    }
    const started = window.performance.now();
    this.#body.textContent = "";
    const tick = () => {
      const length = typedLength(text, window.performance.now() - started, perChar);
      this.#body.textContent = text.slice(0, length);
      if (length >= text.length) {
        window.clearInterval(this.#typing);
        this.#play(this.#pose);
      }
    };
    this.#typing = window.setInterval(tick, perChar);
    // An idle step talks while its text is typed; a step with a pose of its own just plays it.
    this.#play(this.#pose === "idle" ? "talk" : this.#pose);
    tick();
  }

  /**
   * Play one of the guide's animations, or just show its first cell when motion is off. A `talk` request becomes
   * `idle` for a step whose own pose is not idle, and when a one-shot animation ends the guide goes back to idle.
   */
  #play(name) {
    const window = this.#window;
    window.clearTimeout(this.#animating);
    const animation = ANIMS[name] ?? ANIMS.idle;
    const show = index => {
      const [cell, ms] = animation.frames[index];
      const { x, y } = framePosition(cell);
      this.#mascot.style.backgroundPosition = `${x}px ${y}px`;
      if (!NivoraMotion.motionOn(window)) {
        return;
      }
      const next = index + 1;
      if (next < animation.frames.length) {
        this.#animating = window.setTimeout(() => show(next), ms);
      } else if (animation.loop) {
        this.#animating = window.setTimeout(() => show(0), ms);
      } else {
        this.#animating = window.setTimeout(() => this.#play("idle"), ms);
      }
    };
    show(0);
  }
}

let active = null;
let started = false;

function isNormalWindow(window) {
  const { PrivateBrowsingUtils } = ChromeUtils.importESModule("resource://gre/modules/PrivateBrowsingUtils.sys.mjs");
  return !window.closed && window.toolbar?.visible && !PrivateBrowsingUtils.isWindowPrivate(window);
}

function maybeStartFirstRun(window) {
  try {
    if (
      Services.prefs.getBoolPref(SEEN_PREF, false) ||
      active ||
      // Tests and headless runs must not meet a tour.
      Cu.isInAutomation ||
      Services.env.get("MOZ_HEADLESS") ||
      !isNormalWindow(window)
    ) {
      return;
    }
    window.setTimeout(() => {
      // The first window won: another one, or a tour started by hand, may have come in the meantime.
      if (!Services.prefs.getBoolPref(SEEN_PREF, false) && !active && isNormalWindow(window)) {
        NivoraTutorial.start(window);
      }
    }, FIRST_RUN_DELAY_MS);
  } catch (e) {
    log.error("tour first run", e);
  }
}

export const NivoraTutorial = {
  /** Start the tour in `window` (the most recent browser window by default); it does nothing if one is running. */
  start(window = Services.wm.getMostRecentWindow("navigator:browser")) {
    try {
      if (!window || window.closed) {
        return;
      }
      if (active) {
        if (active.alive && active.window === window) {
          // Asked for again while it is showing: begin again, do not stack a second one.
          active.restart();
          return;
        }
        // A tour that is gone from the screen (or is in another window) must not block this one.
        active.end(false);
        active = null;
      }
      const tour = new Tour(window, markSeen => {
        active = null;
        if (markSeen) {
          Services.prefs.setBoolPref(SEEN_PREF, true);
        }
      });
      active = tour;
      tour.start();
    } catch (e) {
      active = null;
      log.error("tour could not start", e);
    }
  },

  /**
   * Watch for the first window, and for a request to see the tour again: a notification `nivora-start-tour` whose
   * subject is the browser window that asked (Settings sends its own), or nothing for the most recent one. Safe to call
   * more than once.
   */
  init() {
    if (started) {
      return;
    }
    started = true;
    Services.obs.addObserver({ observe: subject => maybeStartFirstRun(subject) }, STARTUP_TOPIC);
    Services.obs.addObserver(
      {
        observe: subject => NivoraTutorial.start(subject?.document?.documentElement ? subject : undefined),
      },
      START_TOPIC
    );
    for (const window of Services.wm.getEnumerator("navigator:browser")) {
      if (window.gBrowserInit?.delayedStartupFinished) {
        maybeStartFirstRun(window);
      }
    }
  },
};
