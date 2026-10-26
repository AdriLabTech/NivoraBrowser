# Project vision

Nivora is a browser for people who value precision, concentration, privacy, productivity and
control over their working environment. Its motto is _Less noise. More control._

It is a refinement of an existing, mature stack, not a new engine. The product principle:

> Offer a carefully designed browsing experience on top of an existing, proven infrastructure.

## What Nivora combines

- The maturity of Firefox (Gecko, security updates, web compatibility, extensions).
- The features and interaction model of Zen Browser (vertical tabs, spaces, compact mode,
  split view, glance, folders, library).
- A monochrome, dark, sober visual identity: **Obsidian Eclipse** ([DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)).
- A compact, configurable interface with persistent, recoverable settings.
- Keyboard-first operation where it helps.
- Integration with Linux, with particular care for Arch-based systems and Ryoku Arch, without
  becoming dependent on any one distribution.
- An architecture that keeps Nivora's changes separable from inherited code so that upstream
  updates stay affordable.

## Design principles

1. **Functional simplicity.** Every element has a clear job. Remove visual redundancy, not
   capability. Do not bury essential functions in deep menus.
2. **User control.** Important preferences are explicit, understandable and persistent. No need
   to edit internal files.
3. **Performance.** No avoidable main-thread work, costly animation, repeated queries or
   always-on background work.
4. **Privacy.** Core features never depend on external services. No telemetry, activity tracking
   or third-party data transfer without an explicit, documented decision.
5. **Maintainability.** Own changes live apart from inherited code. No brittle selectors, no
   duplicated modifications, no edits to generated files.
6. **Visual coherence.** One identity across navigation, tabs, menus, dialogs, preferences,
   notifications and empty states.
7. **Compatibility.** Customization never compromises web pages, extensions, authentication,
   downloads, forms or media.

## Non-goals

- A new rendering engine, or replacing Gecko.
- Re-implementing features Zen or Firefox already do adequately.
- Accounts, cloud sync, or hosted services of Nivora's own.
- A permanently visible AI assistant. Any AI feature is an optional module, off by default, with
  explicit disclosure of what leaves the machine.
- Promising anonymity, fingerprinting resistance or network-leak protection that has not been
  demonstrated.

## Phases

| Phase | Goal |
|---|---|
| Foundation | A reproducible build, a coherent visual identity, a separable code structure |
| Productivity | Features that make Nivora different from Zen: workspaces, tab management, command palette, central settings |
| Stable | Security, quality, distribution and a maintainable upstream update process |

All three extend the same code base. See [ROADMAP.md](ROADMAP.md) for the real state.

## Success criteria

Identity, functionality, productivity, privacy, performance, maintainability, stability,
distribution, recoverability and transparency (relationship to Zen and Firefox, licenses). A
good-looking build is not enough, and neither is a build that merely compiles.
