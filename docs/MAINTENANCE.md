# Maintenance

## Routine

| When | Task | How |
|---|---|---|
| Weekly (automated) | Look for a new Zen release and confirm the vendored tree is unchanged | `.github/workflows/upstream-check.yml`; locally `python3 tools/nivora/upstream_check.py --verify-root` |
| Continuously | Watch Mozilla's security advisories for the Firefox version in `surfer.json` | https://www.mozilla.org/security/advisories/ |
| Every change | Static checks | `python3 -I -m unittest discover -s tools/nivora/tests`, `node --test tools/nivora/js-tests/*.test.mjs`, `python3 -I tools/nivora/check_contrast.py`, `python3 -I tools/nivora/generate_icons.py --check`, `cargo test` in `tools/ffprefs` (all run by CI) |
| New Zen release | Update procedure | [UPSTREAM.md](UPSTREAM.md) section 4 |
| Before a release | Full build, regression suite, traffic audit (F-09), profile-directory check (F-10) | [TESTING.md](TESTING.md) |
| Before a release | Licensing items marked "review" | [LICENSES.md](LICENSES.md) |
| After a release | Update the changelog and the roadmap | [CHANGELOG.md](CHANGELOG.md), [ROADMAP.md](ROADMAP.md) |

## When Firefox publishes a security release before Zen does

Zen's patches are tied to an exact Firefox version, so the options are:

1. **Wait for the matching Zen release** (default). Acceptable for medium and low severity.
2. **Rebase the patches** onto the new Firefox tag: fetch the tag, run `surfer import`, fix the patches
   that fail, build, run the regression suite. Expensive (263 patches); reserve for a critical
   vulnerability that is being exploited and for which Zen has announced no date.
3. **Warn users** in the release notes and the repository that the build is behind, with the
   advisory numbers, until one of the above is done.

The decision for each advisory is recorded in the changelog. There is no silent third state.

## Recovery

| Problem | What to do |
|---|---|
| A setting made the browser unusable | Start with `nivora --safe-mode`; or use the palette command "Reset Nivora Settings to Defaults"; or start with a new profile (`nivora --profile <new dir>`) and import a settings export |
| A corrupt preference value | Nivora clears managed preferences whose value is invalid when its commands load; other preferences are Firefox's to handle |
| A bad package | Install the previous one: `pacman -U <previous package>`. The profile is not touched by package changes |
| A bad upstream merge | The merge is a separate branch and is not distributed until the checks pass; abandon the branch. The first commit is never edited |
| Lost profile | Restore the backup taken before the last major version. Nivora has no sync or cloud copy |

## Keeping the project maintainable

- All Nivora changes stay listed in [UPSTREAM.md](UPSTREAM.md); the tree answers
  `git diff $(git rev-list --max-parents=0 HEAD)..HEAD --stat`.
- A new upstream icon is added to `tools/nivora/icons/map.json`, otherwise CI fails.
- A new pref default that points at a Zen host fails the pref tests.
- Decisions go into `docs/decisions/`; a decision is superseded, not edited.
