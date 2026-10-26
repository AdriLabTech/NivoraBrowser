<!--
   - This Source Code Form is subject to the terms of the Mozilla Public
   - License, v. 2.0. If a copy of the MPL was not distributed with this
   - file, You can obtain one at http://mozilla.org/MPL/2.0/.
   -->

# Nivora Browser

_Less noise. More control._

Nivora is a desktop web browser for people who value focus, privacy and control over their
working environment. It is a derivative of [Zen Browser](https://github.com/zen-browser/desktop),
which is itself a derivative of Mozilla Firefox. Nivora adds its own visual identity
(**Obsidian Eclipse**: monochrome, dark, compact) and, in later phases, its own productivity
features, while keeping the rendering engine and most of the interface of its parents.

> **Status: Foundation phase, pre-alpha (`0.1.0a1`). Nothing here is released.**
> The repository holds a verified upstream base, an isolated customization layer and the
> first visual tokens. A baseline build is being produced; the rest of the interface has not
> yet been restyled. See [docs/ROADMAP.md](docs/ROADMAP.md) for what is done, in progress and
> not started, and [docs/FOUNDATION_ANALYSIS.md](docs/FOUNDATION_ANALYSIS.md) for the evidence.

## What Nivora is built on

| Layer | Project | Version used | License |
|---|---|---|---|
| Rendering engine, platform | [Mozilla Firefox](https://www.mozilla.org/firefox/) (Gecko) | 158.0.1 | MPL-2.0 and others |
| Interface and features | [Zen Browser](https://github.com/zen-browser/desktop) | 1.23.4b (`stable`, `541ee55`) | MPL-2.0 |
| Customization layer | Nivora (this repository) | 0.1.0a1 | MPL-2.0 for modified upstream files |

Nivora is **not** an official Mozilla or Zen product and is not endorsed by either project.
It does not use their logos or branding, and it does not talk to services operated by the Zen
project (update server, share service, donation prompts, welcome pages). See
[docs/UPSTREAM.md](docs/UPSTREAM.md) and
[ADR 0004](docs/decisions/0004-upstream-service-isolation.md).

## What is in this repository

- The full Zen source tree, imported unmodified as the repository's **first commit**. Every later
  commit is a Nivora change, so `git diff $(git rev-list --max-parents=0 HEAD)..HEAD` is always
  the exact list of differences from upstream.
- `src/nivora/`, `prefs/nivora/`, `tools/nivora/`: Nivora's own code, preferences and tooling,
  kept apart from inherited code wherever the architecture allows.
- `docs/`: architecture, decisions, build and test procedures, security notes, upstream tracking.

## Building and running

Nivora is built with Zen's tooling ([surfer](https://github.com/zen-browser/surfer)) on top of the
Firefox source. A build needs roughly 30 GB of free disk, 8 GB of RAM and several hours on four
cores. The exact, verified procedure is in [docs/BUILDING.md](docs/BUILDING.md).

```sh
npm ci
npm run download        # Firefox 158.0.1 source (or see BUILDING.md for the GitHub mirror)
npm run import          # apply Zen's patches and Nivora's files
npm run build
npm start
```

## Tests

```sh
python3 -I -m unittest discover -s tools/nivora/tests   # Nivora checks, seconds
python3 -I tools/nivora/check_contrast.py --list        # palette contrast report
```

Zen's browser test suite (`npm test`) needs a finished build. What has and has not been run is
tracked honestly in [docs/TESTING.md](docs/TESTING.md).

## Known limitations

- No Nivora release exists, and no update service: the in-app updater is inert by design until
  the Stable phase defines a distribution channel ([docs/SECURITY.md](docs/SECURITY.md)).
- The logo and icons are still Zen's. They must be replaced before any distribution
  ([docs/UPSTREAM.md](docs/UPSTREAM.md)).
- Zen features that depend on Zen-operated services (sharing spaces, the mods marketplace) are
  disabled or point nowhere. Their entry points are still visible; hiding them is planned.
- Linux is the only platform being worked on. Windows and macOS packaging files are inherited and
  untouched.

## License

Nivora is distributed under the [Mozilla Public License 2.0](LICENSE), like the projects it derives
from. Files inherited from Zen and Firefox keep their original notices. Third-party attributions
are tracked in [docs/UPSTREAM.md](docs/UPSTREAM.md).
