# 0002. Upstream base: Zen `stable` 1.23.4b on Firefox 158.0.1

Status: accepted · Date: 2026-10-26

## Context

Zen publishes from two lines. `dev` (commit `fc54449` when inspected) tracks the next Firefox
release candidate (159.0); `stable` is the tagged release (1.23.4b) on a released Firefox (158.0.1).
Zen's patches are line-context diffs against one exact Firefox version.

## Evidence (all executed in the build environment)

| Zen revision | Firefox 158.0.1 | Firefox 159.0 (`BUILD1` tag) |
|---|---|---|
| `dev` `fc54449` (272 patches) | **fails** at `browser-js.patch` | all apply |
| `1.23.4b` `541ee55` (263 patches) | **all apply** | not tested |

The first import (of `dev`) was replaced by the tagged release.

## Decision

Base on tag `1.23.4b`, with Firefox from tag `FIREFOX_158_0_1_RELEASE`. Move to a newer Zen *release
tag* (and the Firefox it names) through the update procedure, not by following `dev`.

## Alternatives

- Follow `dev`/Twilight: newest features, but depends on a Firefox release candidate and on a
  moving branch; weak foundation for a product with a Stable phase.
- Pick an older Zen: more settled, but older Firefox means older security fixes.

## Consequences

- Nivora gets Firefox 158 security fixes only when Zen releases a matching version, or when Nivora
  re-bases the patches itself (UPSTREAM.md, risks). The policy for urgent Firefox fixes is an open
  decision for the Stable phase.
- A few newer Zen features (for example "Paste & Search" in the new-tab button) are not present.
