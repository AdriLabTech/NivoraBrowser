# 0003. Theming mechanism and palette adjustment

Status: accepted · Date: 2026-10-26

## Context

Obsidian Eclipse is a monochrome dark identity with a proposed palette. Zen already themes the
interface with CSS custom properties derived from one accent color (`--zen-primary-color`) and a
base (`--zen-branding-dark`) through `color-mix()` and `light-dark()`, in `zen-theme.css` and
`schemes/{dark,light}.inc.css`. Those files are processed by Gecko's preprocessor (`%include`), and
`tokens-shared-css.patch` makes `zen-theme.css` reach every chrome page.

## Decision

1. **Mechanism.** Put the palette and semantic roles in one new file, `nivora-tokens.inc.css`,
   `%include`d inside `zen-theme.css`'s `:root`. Put the re-pointing of Zen variables in
   `nivora-dark.inc.css`, `%include`d from `schemes/dark.inc.css` (window, panels, popups) and,
   under `prefers-color-scheme: dark`, from the tokens file (in-content pages). Set the accent
   preference to a neutral gray so Zen's derived colors become gray without being overridden one
   by one. Default to the dark scheme.
2. **Palette.** Use the proposal, except `ash-500`: `#777777` -> `#858585`.

## Evidence

`tools/nivora/check_contrast.py`: with `#777777` three pairs fail (`text-muted` on `surface-1`
4.42:1, `surface-2` 4.25:1, `surface-raised` 3.97:1; AA needs 4.5:1). With `#858585` all 24 pairs
pass (lowest 4.81:1). The specification explicitly allows adjusting values for accessibility while
keeping the identity.

## Alternatives

- Override Zen components by selector: breaks on every markup change; rejected by the maintainability principle.
- Replace `zen-theme.css`: large diff, constant conflicts.
- A Zen "mod" (user CSS): meant for end users; loads late and is user-removable.
- Keep `#777777` and restrict muted text to the base surface: a rule nobody can enforce in CSS.

## Consequences

- Two include lines in Zen files; everything else is new and removable.
- Light mode is untouched and unthemed.
- The result depends on how Zen's `color-mix()` chains evaluate with a gray accent; this is
  **verified by preprocessing only, not yet visually**. Expect to adjust the mapping after the
  first rendered screenshots.
- `ffprefs` mishandled a digit-only hex color; fixed in the tool with a test.
