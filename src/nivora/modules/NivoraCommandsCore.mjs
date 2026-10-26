/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Nivora command registry: one central place that defines what a command is,
 * checks it when it is registered, and runs it safely.
 *
 * Pure module (no Firefox globals), so it loads in the browser and under Node.
 *
 * What the registry guarantees:
 *  - Identifiers are stable, namespaced (`nivora:<name>`), unique and validated.
 *  - A command is data plus two functions, `isAvailable` and `run`. Nothing the
 *    user types is ever evaluated; arguments are validated against a declared
 *    schema before `run` sees them.
 *  - Errors inside a command never reach the caller: `execute` always returns
 *    a result object and reports the failure through `log.error`.
 *  - A command marked `sensitive` is only run after
 *    `context.confirm(spec, confirmArgs)` resolves true.
 *  - A command may define `prepare(context, args)`, which looks at the world
 *    without changing it (pick a file, count what would be closed). It returns
 *    the state `run` will receive, or null to stop quietly (cancelled, nothing
 *    to do). `state.confirmArgs` feeds the confirmation message.
 */

export const CATEGORIES = Object.freeze([
  "tabs",
  "spaces",
  "navigation",
  "window",
  "settings",
]);

const ID_PATTERN = /^nivora:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const L10N_PATTERN = /^[a-z][a-z0-9-]*$/;
const SHORTCUT_PATTERN = /^(?:(?:Ctrl|Alt|Shift|Meta)\+)*(?:[A-Za-z0-9]|F\d{1,2})$/;
const PARAM_TYPES = new Set(["string", "int", "bool", "enum"]);
const MAX_STRING_ARG = 256;

export class CommandSpecError extends Error {
  constructor(id, problems) {
    super(`invalid command '${id}': ${problems.join("; ")}`);
    this.problems = problems;
  }
}

/**
 * @param {object} spec
 * @returns {string[]} Every problem found; empty when the spec is valid.
 */
export function validateCommandSpec(spec) {
  const problems = [];
  if (!spec || typeof spec !== "object") {
    return ["spec must be an object"];
  }
  if (typeof spec.id !== "string" || !ID_PATTERN.test(spec.id)) {
    problems.push("id must look like 'nivora:some-name'");
  }
  if (typeof spec.l10nId !== "string" || !L10N_PATTERN.test(spec.l10nId)) {
    problems.push("l10nId is required (a Fluent message id)");
  }
  if (spec.descriptionL10nId !== undefined && !L10N_PATTERN.test(spec.descriptionL10nId ?? "")) {
    problems.push("descriptionL10nId must be a Fluent message id");
  }
  if (!CATEGORIES.includes(spec.category)) {
    problems.push(`category must be one of ${CATEGORIES.join(", ")}`);
  }
  if (spec.shortcut !== undefined && !SHORTCUT_PATTERN.test(String(spec.shortcut))) {
    problems.push("shortcut must look like 'Ctrl+Shift+K'");
  }
  if (typeof spec.run !== "function") {
    problems.push("run must be a function");
  }
  if (spec.isAvailable !== undefined && typeof spec.isAvailable !== "function") {
    problems.push("isAvailable must be a function");
  }
  if (spec.sensitive !== undefined && typeof spec.sensitive !== "boolean") {
    problems.push("sensitive must be true or false");
  }
  if (spec.sensitive && typeof spec.confirmL10nId !== "string") {
    problems.push("a sensitive command needs a confirmL10nId");
  }
  if (spec.prepare !== undefined && typeof spec.prepare !== "function") {
    problems.push("prepare must be a function");
  }
  if (spec.params !== undefined) {
    if (!Array.isArray(spec.params)) {
      problems.push("params must be an array");
    } else {
      const names = new Set();
      for (const param of spec.params) {
        if (!param || typeof param.name !== "string" || !/^[a-z][A-Za-z0-9]*$/.test(param.name)) {
          problems.push("every param needs a simple name");
          continue;
        }
        if (names.has(param.name)) {
          problems.push(`param '${param.name}' is declared twice`);
        }
        names.add(param.name);
        if (!PARAM_TYPES.has(param.type)) {
          problems.push(`param '${param.name}' has an unknown type`);
        }
        if (param.type === "enum" && (!Array.isArray(param.values) || !param.values.length)) {
          problems.push(`param '${param.name}' needs a list of values`);
        }
      }
    }
  }
  return problems;
}

/**
 * Check arguments against a command's declared parameters. Unknown arguments
 * are rejected, not ignored: a command only ever sees what it declared.
 *
 * @param {object[]|undefined} params
 * @param {object|undefined} args
 * @returns {{ ok: boolean, errors: string[], value: object }}
 */
export function validateArgs(params = [], args = {}) {
  const errors = [];
  const value = {};
  if (args === null || typeof args !== "object" || Array.isArray(args)) {
    return { ok: false, errors: ["arguments must be an object"], value };
  }
  const declared = new Map(params.map(p => [p.name, p]));
  for (const name of Object.keys(args)) {
    if (!declared.has(name)) {
      errors.push(`unknown argument '${name}'`);
    }
  }
  for (const param of params) {
    const given = Object.hasOwn(args, param.name);
    if (!given) {
      if (param.required) {
        errors.push(`'${param.name}' is required`);
      }
      continue;
    }
    const raw = args[param.name];
    switch (param.type) {
      case "string":
        if (typeof raw !== "string" || raw.length > MAX_STRING_ARG) {
          errors.push(`'${param.name}' must be text of at most ${MAX_STRING_ARG} characters`);
          continue;
        }
        break;
      case "int":
        if (!Number.isInteger(raw)) {
          errors.push(`'${param.name}' must be a whole number`);
          continue;
        }
        break;
      case "bool":
        if (typeof raw !== "boolean") {
          errors.push(`'${param.name}' must be true or false`);
          continue;
        }
        break;
      case "enum":
        if (!param.values.includes(raw)) {
          errors.push(`'${param.name}' must be one of ${param.values.join(", ")}`);
          continue;
        }
        break;
    }
    value[param.name] = raw;
  }
  return { ok: errors.length === 0, errors, value: errors.length ? {} : value };
}

/**
 * @param {{ error(...a: unknown[]): void }} [log] Where failures are reported.
 */
export function createCommandRegistry(log = { error() {} }) {
  const commands = new Map();

  function safeAvailable(spec, context) {
    if (!spec.isAvailable) {
      return true;
    }
    try {
      return !!spec.isAvailable(context);
    } catch (e) {
      log.error(`${spec.id}: isAvailable threw`, e);
      return false; // a command that cannot say it is available is hidden
    }
  }

  return {
    /** Add a command. Throws CommandSpecError if it is invalid or a duplicate. */
    register(spec) {
      const problems = validateCommandSpec(spec);
      if (!problems.length && commands.has(spec.id)) {
        problems.push("id is already registered");
      }
      if (problems.length) {
        throw new CommandSpecError(spec?.id, problems);
      }
      commands.set(spec.id, Object.freeze({ params: [], sensitive: false, ...spec }));
    },

    get(id) {
      return commands.get(id);
    },

    /** Whether one command is usable in `context`; false for an unknown id. */
    isAvailable(id, context) {
      const spec = commands.get(id);
      return !!spec && safeAvailable(spec, context);
    },

    /** Commands usable in `context`, in registration order. */
    available(context) {
      return [...commands.values()].filter(spec => safeAvailable(spec, context));
    },

    all() {
      return [...commands.values()];
    },

    /**
     * Run a command. Never throws.
     *
     * @param {string} id
     * @param {object} context Passed to isAvailable / run (and `confirm`).
     * @param {object} [args]
     * @returns {Promise<{ ok: boolean, error?: string, message?: string }>}
     *   `error` is one of unknown-command, unavailable, invalid-args,
     *   cancelled, declined, failed.
     */
    async execute(id, context, args = {}) {
      const spec = commands.get(id);
      if (!spec) {
        return { ok: false, error: "unknown-command", message: `no command '${id}'` };
      }
      if (!safeAvailable(spec, context)) {
        return { ok: false, error: "unavailable", message: `'${id}' is not available now` };
      }
      const checked = validateArgs(spec.params, args);
      if (!checked.ok) {
        return { ok: false, error: "invalid-args", message: checked.errors.join("; ") };
      }
      try {
        let state;
        if (spec.prepare) {
          state = await spec.prepare(context, checked.value);
          if (state === null || state === undefined) {
            return { ok: false, error: "cancelled", message: "nothing to do" };
          }
        }
        if (spec.sensitive) {
          const confirmed =
            typeof context?.confirm === "function"
              ? await context.confirm(spec, state?.confirmArgs ?? {})
              : false;
          if (!confirmed) {
            return { ok: false, error: "declined", message: "not confirmed" };
          }
        }
        await spec.run(context, checked.value, state);
        return { ok: true };
      } catch (e) {
        log.error(`${spec.id}: run failed`, e);
        return { ok: false, error: "failed", message: String(e?.message ?? e) };
      }
    },
  };
}
