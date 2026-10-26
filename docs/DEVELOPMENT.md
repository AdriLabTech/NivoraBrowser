# Development guide

## Repository map

| Path | What | Who owns it |
|---|---|---|
| `src/zen/**`, `src/browser/**`, `src/**/*.patch`, `prefs/{firefox,zen,privatefox,fastfox}`, `build/`, `scripts/`, `configs/` | Inherited from Zen | Upstream. Change minimally and list in [UPSTREAM.md](UPSTREAM.md) |
| `src/nivora/` | Nivora's interface code and styles | Nivora |
| `prefs/nivora/` | Nivora's new preferences | Nivora |
| `tools/nivora/` | Nivora's checks and helper scripts (Python standard library only) | Nivora |
| `tools/ffprefs/` | Zen's pref compiler (one Nivora fix) | Upstream + Nivora fix |
| `docs/` | Documentation; `docs/decisions/` has the ADRs | Nivora (`contribute.md`, `live-folders-specs.md` are Zen's) |
| `engine/`, `.surfer/`, `node_modules/`, `mozconfig` | Git-ignored working state | Local |

## The rules that matter

1. **Edit `src/`, never `engine/`.** `engine/zen/**` and other new-file entries are symlinks into
   `src/`, and `engine/` is rebuilt from `src/` on import. A change made only in `engine/` is lost.
2. **A new file needs a link.** `surfer import` creates the links. After adding a file, either
   re-import into a clean engine or create the link by hand
   (for a new directory under `src/`: `ln -s ../src/<dir> engine/<dir>`).
3. **Prefer, in this order:** a preference, a design token, a new file in `src/nivora/`, a one-line
   hook in a Zen file, a patch to Firefox ([ARCHITECTURE.md](ARCHITECTURE.md) section 2.3).
4. **One definition per preference.** `ffprefs` does not de-duplicate. If Zen already defines it,
   edit that line; otherwise add it under `prefs/nivora/`.
5. **Colors only through roles.** No hex values outside `nivora-tokens.inc.css`.
6. **Do not select Zen elements by structure.** Assign to Zen's variables instead.
7. **No new runtime dependency** (library, framework, service) without an ADR.
8. **Never reduce a protection** to make development easier.

## Daily loop

```sh
# 1. edit under src/ or prefs/
# 2. static checks (seconds)
python3 -I -m unittest discover -s tools/nivora/tests
python3 -I tools/nivora/check_contrast.py
(cd tools/ffprefs && cargo test)

# 3. regenerate prefs after any prefs/*.yaml change
(cd tools/ffprefs && cargo run --bin ffprefs -- ../../)

# 4. UI-only rebuild (no C++), then run
npx surfer build --ui
./engine/mach run --temp-profile
```

Preview what Gecko's preprocessor makes of a stylesheet (from `engine/`):

```python
import io, sys
sys.path.insert(0, "python/mozbuild")
from mozbuild.preprocessor import Preprocessor
pp = Preprocessor(); pp.setMarker("%"); out = io.StringIO()
pp.processFile(open("zen/common/styles/zen-theme.css", encoding="utf-8"), out)
print(out.getvalue())
```

## Commits

- Small, one purpose each, imperative subject, a body that says *why*.
- Prefixes used so far: `vendor:` (only the root commit), `nivora:` (identity, config),
  `theme:`, `docs:`, `tools:`.
- Run the static checks first. Say in the message what was and was not verified.
- Never rewrite or amend published commits; never touch the root commit.

## Adding a tested Python check

Put it in `tools/nivora/`, use only the standard library, add a `unittest` in
`tools/nivora/tests/`, and run it with `python3 -I` (isolated mode) so that a stray module in the
working directory cannot be imported.

## Getting unstuck

[BUILDING.md](BUILDING.md) section 3 lists every build failure met so far with its cause.
