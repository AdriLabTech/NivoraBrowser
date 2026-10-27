# Security

Nivora inherits a large attack surface from Firefox and Zen, and its own changes can add to it.
This document says what is trusted, what changed, what is known to be weak, and what has and has
not been verified. It never claims the browser is "secure".

Reporting a vulnerability: see the root [SECURITY.md](../SECURITY.md).

## 1. Trust boundaries

| Boundary | Trusted side | Untrusted side |
|---|---|---|
| Content process sandbox | Parent (chrome) process | Web content, extensions' content scripts |
| Privileged UI (`chrome://`, `resource://`, JS modules) | Code shipped in the build (Firefox, Zen, Nivora) | Everything loaded from the web or the profile |
| Preferences | Defaults compiled into the build | User profile files, `about:config` edits, policies |
| Profile directory | The user | Other local users and processes |
| Build inputs | Pinned source: Firefox tag, Zen tag, npm lockfile, Cargo lockfiles | Anything fetched at build time without a lockfile or hash |

## 2. Inherited components

Gecko and all of Firefox's security machinery (site isolation, sandboxing, TLS, Safe Browsing,
extension signing policy, Remote Settings) are used unmodified except where Zen's 263 patches
change them. Zen's patches touch widget, layout, session store, urlbar and tab code, which are
privileged. Nivora has **not** audited them; it relies on Zen's review and on the unmodified
upstream state being the reference.

### Inherited reductions found in Zen's build configuration

| Item | Where | Effect | Nivora |
|---|---|---|---|
| Extension signing not enforced by the build | `src/toolkit/moz-configure.patch` (`require_signing` returns False), `configs/common/mozconfig` (`MOZ_REQUIRE_SIGNING=`) | The preference `xpinstall.signatures.required` is `true` by default (Zen sets it in `prefs/firefox/extensions.yaml`), but because the build does not enforce signing, the user (or anything that can change preferences) can turn it off | Left as is; a release must decide whether to restore build-level enforcement (a change to Zen's patch). `browser_nivora_defaults.js` and `check_signatures.py` (F-11) check it: an unsigned extension is refused with the shipped default and loaded when the preference is off, which shows that the preference, not the build, is what protects |
| Unsigned add-ons accepted in the application and system scopes | `--with-unsigned-addon-scopes=app,system` | Only matters to someone who can already write to the installation directory | Left as is |
| Default profile and user directory named `zen` | `src/toolkit/moz-configure.patch` | A Nivora build would have used Zen's `~/.zen` profile | Fixed: `nivora` ([ADR 0005](decisions/0005-application-identity.md)); runtime check F-10 pending |

## 3. Nivora's changes and their security relevance

| Change | Relevance |
|---|---|
| `surfer.json`, `mozconfig`: names, update host removed, distribution id | Update channel; see section 5 |
| Pref defaults (`prefs/zen/{share,mods,updates}.yaml`, `prefs/nivora/endpoints.yaml`) | Removes outbound traffic to Zen-operated hosts; reduces the privileged-page match list for the mods actor |
| `tools/ffprefs` hex quoting | Prevents a malformed `zen.js`. A malformed pref file can silently drop later prefs |
| Theme CSS includes | Style only; no script, no new privileges |
| Removal of Zen CI, funding and code-owner files | Prevents this repository from running Zen's signing/release workflows or notifying Zen maintainers |

No Nivora code runs with privileges yet. Productivity-phase code will (urlbar provider, command
registry) and must be reviewed against section 6.

## 4. External services in the inherited code

| Service | Used for | Nivora treatment | State |
|---|---|---|---|
| `updates.zen-browser.app` | Application updates (MAR) | Host removed from `surfer.json`; surfer writes a non-resolving placeholder (`localhost:7648`). `app.update.auto=false`; the distribution policy `DisableAppUpdate` is verified active in the packaged build (`about:policies`) | Verified: not in the build, not resolved on first start |
| `share.zen-browser.app` | Sharing spaces/folders/boosts | `zen.share.base-url` set to empty | Feature has no backend; UI entry points still visible |
| `zen-browser.app/*` injection | Mods marketplace site talks to the browser | `zen.injections.match-urls` = `about:preferences` only | Default checked in the built browser (`browser_nivora_defaults.js`; development builds of Zen use `http://localhost/*`, so the test accepts that outside official builds) |
| `zen-browser.github.io/theme-store` | Fetching installed mods and updates | `zen.mods.auto-update=false`; requests only happen for mods the user installs | Residual: user-initiated installs still contact it |
| `zen-browser.app/whatsnew`, `/welcome`, `/privacy-policy`, `/about`, `/download` | Opened tabs and links | Welcome and what's-new prefs emptied. About-dialog links and the donate link in Library remain as visible, user-clicked links to Zen | Open item |
| `zen-browser.app/donate` | Sidebar "updated" notification | Notification disabled (`zen.updates.show-update-notification=false`) | Config verified |
| Mozilla: Sync, Remote Settings, AMO, Safe Browsing, search, captive portal, telemetry endpoints | Standard Firefox services | Unchanged. Zen's mozconfig already disables telemetry/data reporting at build time | Host-name audit of a fresh profile done (5 minutes): Remote Settings, update service, region, push, captive portal, **Cisco OpenH264 and Google Widevine downloads, the default search engine**; listed with their switches in [PRIVACY.md](PRIVACY.md) section 4. **No packet capture** and no long-running audit |
| Windows installer URLs (`links.zen-browser.app`, etc.) | Windows only | Not addressed | Out of scope for now |

**Audit of the shipped build (2026-10-27).** The packaged build's `omni.ja` archives were unpacked and
searched for Zen URLs. Not present: `updates.zen-browser.app`, `share.zen-browser.app`, any
`links.zen-browser.app`. Present: `www.zen-browser.app/donate` (2; the About/Library donation entry
and the update notification, both hidden or disabled by preference), `zen-browser.app/mods/` and
`zen-browser.github.io/theme-store/themes/` (the mods marketplace: contacted only when the user
installs or updates a mod), `zen-browser.app/about`, `www.zen-browser.app/privacy-policy/`,
`docs.zen-browser.app/user-manual/window-sync` (links the user may click), and about 20 GitHub issue
URLs inside code comments of Zen's files. A runtime host-name audit of a fresh profile
([TESTING.md](TESTING.md)) agrees: no Zen host.

The accountability for this table is the manual test F-09 in [TESTING.md](TESTING.md): it must be
run on the first working build and again before every release.

## 5. Updates

Nivora currently has **no update channel**. Removing the update host was necessary: pointing a
Nivora build at Zen's server would let Zen's binaries replace Nivora's. The consequence is that
security fixes only reach users when a new Nivora build is made and installed, for example through
a distribution package. This is a real risk, accepted for pre-alpha and not acceptable for a
stable release. [ROADMAP.md](ROADMAP.md) puts the decision in Phase III. Until then Nivora must not
be presented as safe for daily use.

### Test packages built in CI

`.github/workflows/nivora-build-linux.yml` (started by hand) builds the browser on a GitHub-hosted runner
and keeps a package as a 14-day artifact. What that means for trust: the package is **unsigned**; the
`SHA256SUMS` file next to it detects a damaged download, not a compromised build; the build is not
reproducible (it was not checked); the runner downloads Firefox's source from Mozilla's GitHub mirror at a
release tag, the npm packages in `package-lock.json`, the crates Firefox vendors, and the Rust toolchain
pinned in `rust-toolchain.toml`. The workflow has read-only permissions and publishes nothing. It is a way
for the owner to obtain a test build, not a release channel. The package is a development build: no LTO or
PGO, and `--without-wasm-sandboxed-libraries` (the libraries that Firefox sandboxes with RLBox/wasm run
natively), so it should not be used for anything that needs Firefox's full hardening.

## 6. Rules for new code

- Treat web content, page titles, URLs, filenames, imported settings and any model output as
  untrusted input. Validate before use; never `eval`, never build code from strings.
- The command palette executes commands from a registry with stable ids. It never runs
  user-supplied code or shell commands. Operating-system actions need an explicit allow-list,
  argument validation and confirmation.
- Settings import is schema-validated, versioned, size-limited, and never contains secrets
  (passwords, cookies, tokens, keys).
- No new third-party dependency without recording its origin, license, maintenance state and why a
  built-in alternative does not do. Pin versions and hashes.
- No API keys, tokens or credentials in the repository. Zen's `~/.zen-keys` mechanism is renamed
  `~/.nivora-keys`; Nivora builds do not use Zen's keys and ship without Google API keys unless the
  maintainer supplies their own.
- Do not weaken a Firefox protection to make development easier. A preference that lowers
  protection must say so in its description.

## 7. Dependencies

| Dependency | Origin | Pinned by | Note |
|---|---|---|---|
| Firefox 158.0.1 | `mozilla-firefox/firefox` tag `FIREFOX_158_0_1_RELEASE` | `surfer.json` | Not yet compared byte-for-byte with the official tarball |
| `@zen-browser/surfer` 1.14.9 | npm | `package-lock.json` | Hardcodes Zen URLs in generated branding files |
| `formal-git`, `husky`, `typescript`, prettier plugin | npm | `package-lock.json` | Dev tooling. `npm audit --omit=dev`: 0 findings. Full tree: 5 (1 low, 1 moderate, 3 high), including `sharp`/libvips CVEs; `sharp` only resizes the repository's own logo files in `surfer import`. Not triaged further |
| `serde`, `serde_yaml` | crates.io | `tools/ffprefs/Cargo.lock` | `serde_yaml` is archived upstream; only used at build time |
| cbindgen 0.29.4 | crates.io | `--locked` | Build tool |
| Pillow 12.3.0 | PyPI | `tools/nivora/requirements.txt` (version only, no hash) | Draws icons, branding and artwork; build-time only. Hash pinning is open |

## 8. Pending and out of scope

- No audit of Zen's native patches, of Firefox itself, or of the build output.
- No fuzzing, no dependency scanning beyond the above, no reproducible-build check.
- A traffic audit beyond the 60-second host-name log of a first start (a capture over days, with real network access, with the features the user turns on).
- Secret scanning: a one-off pattern scan (cloud and GitHub tokens, private keys, JWTs, `password=`-style
  assignments) over everything Nivora added since the first commit found nothing (2026-10-27). It is a
  regex scan, not a dedicated scanner, and it did not cover Zen's inherited files; the inherited
  `.pem`/`.der` files are public certificates and test fixtures. GitHub's own secret scanning for
  the repository is a setting for the owner to enable.
- Legal compliance is not reviewed. See [UPSTREAM.md](UPSTREAM.md) for the license items that need
  specialist review.
