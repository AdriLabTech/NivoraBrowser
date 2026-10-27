# Changelog

Notable changes per version. Nivora follows [Semantic Versioning](https://semver.org/) once it has a
release; pre-release versions carry `a<N>` (alpha). Zen's own changelog is not reproduced here:
see https://github.com/zen-browser/desktop/releases.

## [Unreleased] - 0.1.0a1 (pre-alpha)

### Added
- Unmodified import of Zen Browser 1.23.4b (`541ee55`, Firefox 158.0.1) as the first commit.
- Obsidian Eclipse design tokens (`src/nivora/theme/`), dark scheme mapping, neutral accent and
  dark default; contrast validation tool with unit tests (`tools/nivora/`).
- `prefs/nivora/endpoints.yaml`: overrides for the URLs `surfer` writes into the branding prefs.
- Generated application icons (`tools/nivora/generate_branding.py`): a proposed Nivora mark replaces
  every Zen icon in `configs/branding/release/`.
- Documentation set: vision, architecture, design system, roadmap, development, building, testing,
  security, upstream tracking, Foundation analysis report, decision records 0001-0005.

- Command registry (`NivoraCommandsCore.mjs`) and eight commands for Zen's palette; central
  settings (25 managed preferences, versioned export, validated import, reset, startup repair);
  duplicate-tab detection that never crosses spaces or containers.
- Interface icons regenerated from Phosphor Icons (MIT): Zen's Nucleo icons are not redistributable.
- `tools/nivora/upstream_check.py` and a weekly read-only workflow; static-checks workflow.
- Arch Linux packaging: tarball assembly script, `PKGBUILD`, `.desktop`, AppStream metadata,
  update-disabling policy. License inventory and texts (`licenses/`).
- Documentation: productivity audit, privacy, Linux, distribution, maintenance, licenses, security review.
- Runtime tooling: `smoke.py` (starts the build, loads a page, checks the profile directory),
  `net_audit.py` (host names resolved on a first start), `screenshots.py` (visual review),
  `post_import.py` (removes branding-file prefs that override Nivora's endpoints).
- Interface artwork: Firefox's logo and mascot, and Zen's window-layout screenshots, replaced by
  generated palette-only drawings (`generate_ui_artwork.py`, 28 files).
- Nivora browser tests (4 files, 120 checks) and a CI step that checks the generated artwork.

### Changed
- In-content pages (settings, errors, dialogs) and blank dark pages use the neutral surfaces:
  gray-ramp mapping in `nivora-dark.inc.css` and a six-constant patch of
  `widget/nsXPLookAndFeel.cpp`.
- `npm run import` also runs `update_en_US_packs.py` (packages the `.ftl` files) and `post_import.py`.
- Application identity: Nivora Browser, binary `nivora`, vendor AdriLabTech, distribution id
  `io.github.adrilabtech.nivora`, version `0.1.0a1`.
- No update host is configured; `app.update.auto` is off.
- Zen-operated services detached: share service, mods injection and auto-update, update/donate
  notification.
- User-visible "Zen" replaced by "Nivora" in 11 en-US strings.
- `tools/ffprefs`: values starting with `#` are now quoted (digit-only hex colors produced an
  invalid `zen.js`); added unit tests.

### Removed
- Zen's CI workflows, funding manifest, code owner entry, issue labeler, issue statistics and logo
  assets from `docs/`.

- **The default profile and user directory were `zen`** (Zen's configure patch); they are now `nivora`,
  so a Nivora build no longer shares `~/.zen` with Zen.
- Share UI hides itself while no share service is configured; the Library donate button and the mods
  website link are hidden by `nivora.ui.hide-zen-services`.

### Known problems
- Not yet seen in a running browser: the rendering of the theme, the icons, the commands (the build
  is not finished). Browser tests are written and not run.
- No update channel: packages are the update path.
- Items marked "review" in docs/LICENSES.md.
