// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  CommandSpecError,
  createCommandRegistry,
  validateArgs,
  validateCommandSpec,
} from "../../../src/nivora/modules/NivoraCommandsCore.mjs";
import { findDuplicateTabs, normalizeUrl } from "../../../src/nivora/modules/NivoraTabsCore.mjs";

const good = (over = {}) => ({
  id: "nivora:sample-command",
  l10nId: "nivora-action-sample",
  category: "tabs",
  run() {},
  ...over,
});

const quietLog = () => {
  const errors = [];
  return { errors, error: (...a) => errors.push(a) };
};

test("a well-formed spec has no problems", () => {
  assert.deepEqual(validateCommandSpec(good()), []);
  assert.deepEqual(validateCommandSpec(good({ shortcut: "Ctrl+Shift+K", params: [{ name: "count", type: "int" }] })), []);
});

test("specs are checked field by field", () => {
  const bad = [
    [good({ id: "sample" }), /id must look like/],
    [good({ id: "nivora:Bad_Name" }), /id must look like/],
    [good({ l10nId: "" }), /l10nId/],
    [good({ category: "misc" }), /category/],
    [good({ run: "alert(1)" }), /run must be a function/],
    [good({ isAvailable: true }), /isAvailable/],
    [good({ shortcut: "Control-K" }), /shortcut/],
    [good({ sensitive: true }), /confirmL10nId/],
    [good({ prepare: "x" }), /prepare must be a function/],
    [good({ params: [{ name: "x", type: "regex" }] }), /unknown type/],
    [good({ params: [{ name: "x", type: "enum" }] }), /list of values/],
    [good({ params: [{ name: "x", type: "int" }, { name: "x", type: "int" }] }), /declared twice/],
  ];
  for (const [spec, pattern] of bad) {
    assert.match(validateCommandSpec(spec).join("; "), pattern);
  }
  assert.deepEqual(validateCommandSpec(null), ["spec must be an object"]);
});

test("registering rejects invalid and duplicate commands", () => {
  const registry = createCommandRegistry();
  registry.register(good());
  assert.throws(() => registry.register(good()), CommandSpecError);
  assert.throws(() => registry.register(good({ id: "x" })), CommandSpecError);
  assert.equal(registry.all().length, 1);
});

test("arguments are validated against the declared params", () => {
  const params = [
    { name: "name", type: "string", required: true },
    { name: "level", type: "enum", values: ["low", "high"] },
    { name: "count", type: "int" },
    { name: "flag", type: "bool" },
  ];
  assert.deepEqual(validateArgs(params, { name: "a", level: "low", count: 2, flag: true }).value, {
    name: "a", level: "low", count: 2, flag: true,
  });
  assert.equal(validateArgs(params, {}).ok, false); // required
  assert.equal(validateArgs(params, { name: "a", extra: 1 }).ok, false); // unknown
  assert.equal(validateArgs(params, { name: "a", level: "mid" }).ok, false);
  assert.equal(validateArgs(params, { name: "a", count: 1.5 }).ok, false);
  assert.equal(validateArgs(params, { name: "a", flag: "yes" }).ok, false);
  assert.equal(validateArgs(params, { name: "x".repeat(300) }).ok, false);
  assert.equal(validateArgs(params, null).ok, false);
  assert.equal(validateArgs(params, ["a"]).ok, false);
  assert.deepEqual(validateArgs([], undefined), { ok: true, errors: [], value: {} });
});

test("execute runs a command and passes validated args only", async () => {
  const registry = createCommandRegistry();
  let seen;
  registry.register(good({ params: [{ name: "n", type: "int", required: true }], run: (ctx, args) => { seen = [ctx, args]; } }));
  const ctx = { window: "w" };
  assert.deepEqual(await registry.execute("nivora:sample-command", ctx, { n: 3 }), { ok: true });
  assert.deepEqual(seen, [ctx, { n: 3 }]);
  assert.equal((await registry.execute("nivora:sample-command", ctx, { n: "3" })).error, "invalid-args");
});

test("execute never throws: unknown ids, unavailable and failing commands", async () => {
  const log = quietLog();
  const registry = createCommandRegistry(log);
  registry.register(good({ id: "nivora:off", isAvailable: () => false }));
  registry.register(good({ id: "nivora:boom", run() { throw new Error("kaput"); } }));
  registry.register(good({ id: "nivora:async-boom", async run() { throw new Error("later"); } }));
  assert.equal((await registry.execute("nivora:nope", {})).error, "unknown-command");
  assert.equal((await registry.execute("nivora:off", {})).error, "unavailable");
  const failed = await registry.execute("nivora:boom", {});
  assert.deepEqual([failed.ok, failed.error, failed.message], [false, "failed", "kaput"]);
  assert.equal((await registry.execute("nivora:async-boom", {})).error, "failed");
  assert.equal(log.errors.length, 2);
});

test("a throwing isAvailable hides the command instead of breaking the list", () => {
  const log = quietLog();
  const registry = createCommandRegistry(log);
  registry.register(good({ id: "nivora:a" }));
  registry.register(good({ id: "nivora:b", isAvailable() { throw new Error("x"); } }));
  registry.register(good({ id: "nivora:c", isAvailable: () => true }));
  assert.deepEqual(registry.available({}).map(c => c.id), ["nivora:a", "nivora:c"]);
  assert.equal(log.errors.length, 1);
});

test("a sensitive command only runs after confirmation", async () => {
  const registry = createCommandRegistry();
  let ran = 0;
  registry.register(good({ sensitive: true, confirmL10nId: "nivora-confirm-sample", run() { ran++; } }));
  assert.equal((await registry.execute("nivora:sample-command", {})).error, "declined"); // no confirm function
  assert.equal((await registry.execute("nivora:sample-command", { confirm: () => false })).error, "declined");
  assert.equal((await registry.execute("nivora:sample-command", { confirm: async () => false })).error, "declined");
  assert.equal(ran, 0);
  assert.equal((await registry.execute("nivora:sample-command", { confirm: async spec => spec.confirmL10nId === "nivora-confirm-sample" })).ok, true);
  assert.equal(ran, 1);
});

test("a command that is not a function is never invoked from data", async () => {
  const registry = createCommandRegistry();
  assert.throws(() => registry.register(good({ run: "globalThis.pwned = true" })), CommandSpecError);
  assert.equal(globalThis.pwned, undefined);
});

test("normalizeUrl ignores the fragment only", () => {
  assert.equal(normalizeUrl("https://a.example/x#top"), normalizeUrl("https://a.example/x"));
  assert.notEqual(normalizeUrl("https://a.example/x?a=1"), normalizeUrl("https://a.example/x?a=2"));
  assert.equal(normalizeUrl("not a url"), "not a url");
});

test("duplicate detection keeps the selected tab, skips pinned/essential/blank, respects spaces", () => {
  const tab = (id, url, over = {}) => ({ id, url, spaceId: "s1", ...over });
  const result = findDuplicateTabs([
    tab("1", "https://a.example/#x"),
    tab("2", "https://a.example/", { selected: true }),
    tab("3", "https://a.example/"),
    tab("4", "https://b.example/"),
    tab("5", "https://b.example/", { pinned: true }),
    tab("6", "https://c.example/", { spaceId: "s1" }),
    tab("7", "https://c.example/", { spaceId: "s2" }), // other space: not a duplicate
    tab("8", "about:blank"),
    tab("9", "about:blank"),
    tab("10", "https://d.example/", { essential: true }),
    tab("11", "https://d.example/", { essential: true }),
    tab("12", "https://e.example/", { empty: true }),
    tab("13", "https://e.example/", { empty: true }),
  ]);
  assert.deepEqual(result.groups, [{ url: "https://a.example/", keep: "2", close: ["1", "3"] }]);
  assert.deepEqual(result.closeIds, ["1", "3"]);
  assert.deepEqual(findDuplicateTabs([]), { groups: [], closeIds: [] });
});

test("prepare feeds run and the confirmation; null from prepare stops quietly", async () => {
  const registry = createCommandRegistry();
  const calls = [];
  registry.register(good({
    id: "nivora:prepared",
    sensitive: true,
    confirmL10nId: "nivora-confirm-sample",
    prepare: (ctx, args) => (ctx.nothing ? null : { confirmArgs: { count: 2 }, items: ["a", "b"] }),
    run: (ctx, args, state) => calls.push(["run", state.items]),
  }));
  const asked = [];
  const ctx = { confirm: (spec, confirmArgs) => { asked.push(confirmArgs); return true; } };
  assert.deepEqual(await registry.execute("nivora:prepared", ctx), { ok: true });
  assert.deepEqual(asked, [{ count: 2 }]);
  assert.deepEqual(calls, [["run", ["a", "b"]]]);
  assert.equal((await registry.execute("nivora:prepared", { ...ctx, nothing: true })).error, "cancelled");
  assert.equal(asked.length, 1, "no confirmation when there is nothing to do");
  assert.equal(calls.length, 1);
});

test("a declined confirmation after prepare never runs the command", async () => {
  const registry = createCommandRegistry();
  let ran = false;
  registry.register(good({
    sensitive: true,
    confirmL10nId: "nivora-confirm-sample",
    prepare: () => ({}),
    run() { ran = true; },
  }));
  assert.equal((await registry.execute("nivora:sample-command", { confirm: () => false })).error, "declined");
  assert.equal(ran, false);
});

test("a prepare that throws is reported, not thrown", async () => {
  const log = quietLog();
  const registry = createCommandRegistry(log);
  registry.register(good({ prepare() { throw new Error("disk"); } }));
  const result = await registry.execute("nivora:sample-command", {});
  assert.deepEqual([result.ok, result.error], [false, "failed"]);
  assert.equal(log.errors.length, 1);
});

test("isAvailable answers per command and is false for unknown ids", () => {
  const registry = createCommandRegistry(quietLog());
  registry.register(good({ id: "nivora:yes", isAvailable: () => true }));
  registry.register(good({ id: "nivora:no", isAvailable: () => false }));
  assert.deepEqual(
    [registry.isAvailable("nivora:yes", {}), registry.isAvailable("nivora:no", {}), registry.isAvailable("nivora:zzz", {})],
    [true, false, false]
  );
});

test("the same address in different containers is not a duplicate", () => {
  const tab = (id, containerId, over = {}) => ({ id, url: "https://bank.example/", spaceId: "s1", containerId, ...over });
  const result = findDuplicateTabs([tab("1", 0), tab("2", 5), tab("3", 5), tab("4", 7)]);
  assert.deepEqual(result.groups, [{ url: "https://bank.example/", keep: "2", close: ["3"] }]);
  assert.deepEqual(findDuplicateTabs([tab("1", 0), tab("2", 5)]).closeIds, []);
  // A tab without a container id counts as the default container (0).
  assert.deepEqual(findDuplicateTabs([{ id: "1", url: "https://a.example/" }, { id: "2", url: "https://a.example/", containerId: 0 }]).closeIds, ["2"]);
});
