# Changelog

Notable changes per version. Nivora follows [Semantic Versioning](https://semver.org/) once it has a
release; pre-release versions carry `a<N>` (alpha). Zen's own changelog is not reproduced here:
see https://github.com/zen-browser/desktop/releases.

## [Unreleased] - 0.1.0a1 (Foundation, in progress)

### Added
- Unmodified import of Zen Browser 1.23.4b (`541ee55`, Firefox 158.0.1) as the first commit.
- Obsidian Eclipse design tokens (`src/nivora/theme/`), dark scheme mapping, neutral accent and
  dark default; contrast validation tool with unit tests (`tools/nivora/`).
- `prefs/nivora/endpoints.yaml`: overrides for the URLs `surfer` writes into the branding prefs.
- Documentation set: vision, architecture, design system, roadmap, development, building, testing,
  security, upstream tracking, Foundation analysis report, decision records 0001-0005.

### Changed
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

### Known problems
- Logo and icons are still Zen's.
- Dark mapping not yet seen rendered. No Nivora build has been started in a browser yet.
- No update channel.
