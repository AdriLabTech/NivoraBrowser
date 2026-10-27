/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Nivora's commands for the command palette.
 *
 * Zen already provides the palette itself (the address bar's global actions,
 * ZenUBGlobalActions.sys.mjs). Nivora adds a central registry with checked
 * definitions (NivoraCommandsCore.mjs) and the commands that Zen does not have.
 * `nivoraGlobalActions` is the same list in the shape Zen's palette expects;
 * ZenUBGlobalActions appends it to its own.
 *
 * Importing this module must never throw: a problem in Nivora's commands may
 * remove Nivora's commands from the palette, but never Zen's.
 */

import { createCommandRegistry } from "resource:///modules/nivora/NivoraCommandsCore.mjs";
import { findDuplicateTabs } from "resource:///modules/nivora/NivoraTabsCore.mjs";
import { NivoraSettings } from "resource:///modules/nivora/NivoraSettings.sys.mjs";
import { t } from "resource:///modules/nivora/NivoraL10n.sys.mjs";

const ICONS = "chrome://browser/skin/zen-icons/";

const log = {
  error: (...args) => console.error("[Nivora]", ...args),
};

export const nivoraRegistry = createCommandRegistry(log);

/**
 * What a command receives: the window it acts on, the way to ask the user
 * (`confirm`) and the way to tell the user a result (`notify`). Both are
 * replaceable, which is how the tests run commands without a modal dialog.
 *
 * @param {Window} window
 */
export function contextFor(window) {
  return {
    window,
    confirm: (spec, args) =>
      Services.prompt.confirm(window, t("nivora-dialog-title"), t(spec.confirmL10nId, args)),
    notify: text => Services.prompt.alert(window, t("nivora-dialog-title"), text),
  };
}

function describeTabs(window) {
  const tabs = [...window.gBrowser.tabs];
  const described = tabs.map((tab, index) => ({
    id: String(index),
    url: tab.linkedBrowser?.currentURI?.spec ?? "",
    pinned: !!tab.pinned,
    essential: tab.hasAttribute("zen-essential"),
    empty: tab.hasAttribute("zen-empty-tab"),
    selected: !!tab.selected,
    spaceId: tab.getAttribute("zen-workspace-id") ?? "",
    containerId: tab.userContextId ?? 0,
  }));
  return { tabs, described };
}

function duplicatesIn(window) {
  const { tabs, described } = describeTabs(window);
  const { closeIds } = findDuplicateTabs(described);
  return closeIds.map(id => tabs[Number(id)]);
}

/** The commands. `zenCommand` names a native <command> to run when one exists. */
const SPECS = [
  {
    id: "nivora:new-tab",
    l10nId: "nivora-action-new-tab",
    category: "tabs",
    shortcut: "Ctrl+T",
    icon: `${ICONS}plus.svg`,
    zenCommand: "cmd_newNavigatorTab",
    run: ({ window }) => window.document.getElementById("cmd_newNavigatorTab").doCommand(),
  },
  {
    id: "nivora:open-history",
    l10nId: "nivora-action-open-history",
    category: "navigation",
    shortcut: "Ctrl+Shift+H",
    icon: `${ICONS}history.svg`,
    zenCommand: "Browser:ShowAllHistory",
    run: ({ window }) => window.document.getElementById("Browser:ShowAllHistory").doCommand(),
  },
  {
    id: "nivora:open-downloads",
    l10nId: "nivora-action-open-downloads",
    category: "navigation",
    shortcut: "Ctrl+Shift+Y",
    icon: `${ICONS}downloads.svg`,
    zenCommand: "Tools:Downloads",
    run: ({ window }) => window.document.getElementById("Tools:Downloads").doCommand(),
  },
  {
    id: "nivora:search-open-tabs",
    l10nId: "nivora-action-search-open-tabs",
    category: "tabs",
    icon: `${ICONS}search-glass.svg`,
    // "% " restricts the address bar to the tabs that are open.
    run: ({ window }) => {
      window.gURLBar.focus();
      window.gURLBar.search("% ");
    },
  },
  {
    id: "nivora:close-duplicate-tabs",
    l10nId: "nivora-action-close-duplicate-tabs",
    category: "tabs",
    icon: `${ICONS}duplicate-tab.svg`,
    sensitive: true,
    confirmL10nId: "nivora-confirm-close-duplicates",
    isAvailable: ({ window }) => duplicatesIn(window).length > 0,
    // Looks only; closes nothing until the user confirms.
    prepare: ({ window }) => {
      const toClose = duplicatesIn(window);
      return toClose.length ? { toClose, confirmArgs: { count: toClose.length } } : null;
    },
    run: ({ window }, args, state) => {
      window.gBrowser.removeTabs(state.toClose);
    },
  },
  {
    id: "nivora:export-settings",
    l10nId: "nivora-action-export-settings",
    category: "settings",
    icon: `${ICONS}save.svg`,
    run: ({ window }) => NivoraSettings.exportToFile(window),
  },
  {
    id: "nivora:import-settings",
    l10nId: "nivora-action-import-settings",
    category: "settings",
    icon: `${ICONS}folder.svg`,
    sensitive: true,
    confirmL10nId: "nivora-settings-import-confirm",
    // Reading and validating changes nothing; applying waits for the confirmation.
    prepare: async ({ window, notify }) => {
      const parsed = await NivoraSettings.readFromFile(window);
      if (!parsed) {
        return null;
      }
      const count = Object.keys(parsed.settings).length;
      if (!count) {
        notify(t("nivora-settings-import-nothing"));
        return null;
      }
      return { settings: parsed.settings, confirmArgs: { count } };
    },
    run: ({ notify }, args, state) => {
      const { applied } = NivoraSettings.apply(state.settings);
      notify(t("nivora-settings-import-done", { count: applied.length }));
    },
  },
  {
    id: "nivora:reset-settings",
    l10nId: "nivora-action-reset-settings",
    category: "settings",
    icon: `${ICONS}arrow-rotate-anticlockwise.svg`,
    sensitive: true,
    confirmL10nId: "nivora-confirm-reset-settings",
    run: ({ notify }) => {
      const cleared = NivoraSettings.reset();
      notify(t("nivora-settings-reset-done", { count: cleared.length }));
    },
  },
];

const ICON_BY_ID = new Map();
for (const spec of SPECS) {
  try {
    const { icon, zenCommand, ...definition } = spec;
    nivoraRegistry.register(definition);
    ICON_BY_ID.set(spec.id, { icon, zenCommand });
  } catch (e) {
    log.error("command not registered", e);
  }
}

try {
  const repaired = NivoraSettings.repair();
  if (repaired.length) {
    console.warn("[Nivora] reset invalid settings to their defaults:", repaired.join(", "));
  }
} catch (e) {
  log.error("settings repair failed", e);
}

/**
 * The registry in the shape of Zen's palette actions:
 * `{ l10nId, command, icon, isAvailable, commandId }`.
 */
export const nivoraGlobalActions = nivoraRegistry.all().map(spec => {
  const { icon, zenCommand } = ICON_BY_ID.get(spec.id);
  return {
    l10nId: spec.l10nId,
    commandId: spec.id,
    icon,
    // A native command id lets Zen show the real keyboard shortcut and run it
    // as it runs its own actions; everything else goes through the registry.
    command: zenCommand ?? (window => nivoraRegistry.execute(spec.id, contextFor(window))),
    isAvailable: window => nivoraRegistry.isAvailable(spec.id, contextFor(window)),
  };
});
