# Design system: Obsidian Eclipse

Obsidian Eclipse is Nivora's visual identity: a monochrome, dark, quiet interface whose depth
comes from small differences in luminance, not from color, shadow or glass. It is inspired by the
Low Noise philosophy and a customized Linux desktop. It is an original system: no third-party
logos, icons or illustrations are copied.

Source of truth: [`src/nivora/theme/nivora-tokens.inc.css`](../src/nivora/theme/nivora-tokens.inc.css).
Colors are written there and nowhere else. Components use **roles**, not raw palette values.

## Palette

| Token | Value | Role |
|---|---|---|
| `obsidian-950` | `#050505` | `surface-base`: window background |
| `obsidian-900` | `#0a0a0a` | `surface-1`: main surfaces (also Zen's `--zen-branding-dark`) |
| `obsidian-850` | `#101010` | `surface-2`: secondary panels, address bar, toolbar |
| `graphite-800` | `#181818` | `surface-raised`: menus, popups, dialogs |
| `graphite-700` | `#242424` | `separator`: quiet dividers |
| `graphite-600` | `#353535` | `separator-strong`: visible dividers, input borders |
| `ash-500` | `#858585` | `text-muted`, `control-border` |
| `silver-300` | `#b8b8b8` | `text-secondary` |
| `white-100` | `#f0f0f0` | `text-primary` |
| `pure-white` | `#ffffff` | `selected`, `focus-ring` |

`ash-500` differs from the first proposal (`#777777`). That value fails WCAG AA for text on three
of the four surfaces (4.42:1, 4.25:1 and 3.97:1 against a 4.5:1 minimum). `#858585` passes on all
four (lowest 4.81:1). See [ADR 0003](decisions/0003-theming-mechanism-and-palette.md).

## Validated contrast

`python3 tools/nivora/check_contrast.py --list` (24 pairs, all pass at the time of writing):

| Foreground (role) | on `surface-base` | `surface-1` | `surface-2` | `surface-raised` | Minimum |
|---|---|---|---|---|---|
| `text-primary` | 17.88 | 17.37 | 16.70 | 15.58 | 7.0 |
| `text-secondary` | 10.27 | 9.98 | 9.59 | 8.95 | 4.5 |
| `text-muted` | 5.52 | 5.37 | 5.16 | 4.81 | 4.5 |
| `selected`, `focus-ring` | 20.38 | 19.80 | 19.03 | 17.76 | 3.0 |
| `control-border` | 5.52 | 5.37 | 5.16 | 4.81 | 3.0 (WCAG 1.4.11) |

`separator` and `separator-strong` are deliberately low contrast (about 1.2:1 to 1.7:1): they
are decorative. The edge of anything interactive uses `control-border`, never a separator. This is
the one rule that keeps "quiet" from becoming "unusable".

The check covers the palette. It does not cover how Zen's derived colors (`color-mix()` chains)
come out in the running UI; that needs rendered screenshots and is tracked in
[TESTING.md](TESTING.md).

## How the tokens reach the interface

Zen builds its palette from `--zen-primary-color` (the accent, pref `zen.theme.accent-color`) and
`--zen-branding-dark` with `color-mix()`. Nivora uses that, rather than fighting it:

1. The accent defaults to the neutral `#858585`, so every derived color is gray.
2. `nivora-dark.inc.css` re-points a handful of Zen variables at roles
   (`--zen-main-browser-background`, `--zen-dialog-background`, `--arrowpanel-background`, ...).
3. The window defaults to the dark scheme (`zen.view.window.scheme = 0`). The light scheme remains
   available and unthemed.

4. Pages inside the browser (settings, errors, dialogs) take their colors from Firefox's design
   system, which builds the dark theme from a gray ramp with a violet tint. `nivora-dark.inc.css`
   re-points the three surface steps (`--color-gray-100`, `-90`, `-80`) at neutral surface tokens.
5. A page with no background of its own is painted with the dark system color `Canvas`, which Gecko
   compiles in (`widget/nsXPLookAndFeel.cpp`). A six-line patch makes it, and the other dark
   surfaces it defines, neutral (see [UPSTREAM.md](UPSTREAM.md)).

Nothing selects Zen elements by structure. Adding a variable mapping is one line.

### Artwork

Firefox's logo and its mascot, Kit, appear in the interface (the "About" entry in settings, the
default-browser banner, several dialogs). They are Mozilla's marks, so `generate_ui_artwork.py`
replaces them, at the same size, with a flat eclipse glyph (logo) or the eclipse mark (mascot).
Zen's three window-layout screenshots in the Look and Feel pane are replaced by schematic drawings.

## Status of the identity

| Element | State |
|---|---|
| Palette, roles, contrast validation | Implemented and checked (static) |
| Variable mapping into Zen's dark scheme | Implemented and **seen rendered** in a real build: window, sidebar, urlbar, command palette (screenshots via `tools/nivora/screenshots.py`) |
| In-content pages (settings), blank pages, informational banners | Mapped to the neutral surfaces; see the list above. Seen: new tab, settings (two panes), main menu, tab context menu, private window. `about:support` keeps light-blue table headers |
| Firefox logo and mascot in the interface | Replaced (22 files); seen in settings and the default-browser banner. The private-window background, onboarding-message art and a few rarely shown files are replaced but not yet looked at |
| Typography | Not decided. Candidates: the system UI font stack Zen already uses; evaluate once a build runs |
| Iconography | Not started. Zen ships its own monochrome set (`zen-icons/`) that can be reused |
| Logo and application icon | **Proposal** generated from the palette (`tools/nivora/generate_branding.py`): an eclipse crescent in a corona ring on an obsidian plate; ring dropped below 48 px. Needs the owner's approval; it resembles generic crescent-moon icons, so a more distinctive mark may be preferable. Wordmark SVGs are plain text placeholders |
| Tab states, menus | Reviewed in screenshots (active, inactive, pinned, hover; main and context menus): consistent with the palette; loading/audio/warning states and dialogs not yet |
| New tab page, dialogs | New tab is Zen's search overlay on the neutral canvas; dialogs not reviewed |
| Reduced motion | Not started; Zen has a `gReduceMotion` flag to build on |

## Rules for contributors

- Use a role (`var(--nivora-text-secondary)`), not a hex value or a raw palette token.
- No saturated colors as decoration. Semantic status colors (errors, warnings, security) only where
  luminance alone cannot carry the meaning.
- Never communicate state with color alone: pair it with shape, weight, an icon or position.
- Depth is a step in the surface ladder (`base` < `1` < `2` < `raised`), not a shadow.
- Animations are short, explain a state change, and respect the reduced-motion preference.
