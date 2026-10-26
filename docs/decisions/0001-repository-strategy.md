# 0001. Repository strategy

Status: accepted · Date: 2026-10-26

## Context

Nivora needs Zen's build system (`surfer`, patches, `ffprefs`), changes only a small part of it,
and must absorb upstream updates repeatedly. The target GitHub repository was empty.

## Decision

Keep the whole Zen tree in this repository, as the **first commit, unmodified** (its git tree hash
equals the upstream tag's). Every Nivora change is a later commit. Nivora's own code goes into
dedicated locations (`src/nivora/`, `prefs/nivora/`, `tools/nivora/`); edits to inherited files are
kept to the minimum and listed in [UPSTREAM.md](../UPSTREAM.md).

Upstream updates are imported as snapshots on a separate `vendor/zen-<tag>` branch rooted at the
first commit and merged, so git has a correct merge base (procedure in UPSTREAM.md).

## Alternatives

- **Overlay repository** (only Nivora files, plus a script that applies them to a Zen checkout):
  cleanest separation, but patches against Zen files are brittle (no three-way merge), the
  official build flow (`npm run init`) would not work unmodified, and the result is unverifiable
  without assembling it first.
- **Git fork with Zen's real history:** the checkout available was shallow (depth 1), and pushing
  a shallow history to a repository that lacks the parent commits is normally refused (not tried
  here). Provenance is preserved by the tag, commit and tree hash recorded instead.
- **Submodule or subtree:** adds tooling and hides the diff.

## Consequences

- Repository size is that of the Zen tree (about 50 MB working tree).
- `git diff <root>..HEAD` is the complete, authoritative list of changes.
- Zen's file layout stays; Nivora must not reorganise inherited directories.
- The root commit must never be amended or rebased once published.
