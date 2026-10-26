/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Pure helpers for tab housekeeping (no Firefox globals; testable under Node).
 *
 * Nothing here closes a tab. These functions only *describe* what could be
 * closed; closing needs the user's confirmation (see NivoraCommands.sys.mjs).
 */

/**
 * A comparison key for a page address: the URL without its fragment, so that
 * `https://a.example/x#top` and `https://a.example/x` count as the same page.
 * Addresses that cannot be parsed are compared as written.
 *
 * @param {string} url
 * @returns {string}
 */
export function normalizeUrl(url) {
  try {
    const parsed = new URL(url);
    parsed.hash = "";
    return parsed.href;
  } catch {
    return String(url);
  }
}

const IGNORED_URLS = new Set(["about:blank", "about:newtab", "about:home", ""]);

/**
 * Find tabs that show the same page as another tab in the same space.
 *
 * Pinned and essential tabs are never proposed, and neither are empty tabs or
 * blank pages. In each group the selected tab is kept, otherwise the first.
 * Tabs in different containers are never duplicates of each other: the same
 * address in two containers is two separate sessions (two logins), and closing
 * one would lose the other's state.
 *
 * @param {{ id: string, url: string, pinned?: boolean, essential?: boolean,
 *           selected?: boolean, empty?: boolean, spaceId?: string,
 *           containerId?: number }[]} tabs
 * @returns {{ groups: { url: string, keep: string, close: string[] }[], closeIds: string[] }}
 */
export function findDuplicateTabs(tabs) {
  const buckets = new Map();
  for (const tab of tabs) {
    if (tab.pinned || tab.essential || tab.empty || IGNORED_URLS.has(tab.url)) {
      continue;
    }
    const key = [tab.spaceId ?? "", tab.containerId ?? 0, normalizeUrl(tab.url)].join("\u0000");
    if (!buckets.has(key)) {
      buckets.set(key, []);
    }
    buckets.get(key).push(tab);
  }
  const groups = [];
  for (const members of buckets.values()) {
    if (members.length < 2) {
      continue;
    }
    const keep = members.find(tab => tab.selected) ?? members[0];
    groups.push({
      url: normalizeUrl(keep.url),
      keep: keep.id,
      close: members.filter(tab => tab !== keep).map(tab => tab.id),
    });
  }
  return { groups, closeIds: groups.flatMap(group => group.close) };
}
