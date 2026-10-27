# Distribution

## 1. Decision

The first distribution format is a **portable tarball produced by `mach package`, installed on Arch
Linux by a `PKGBUILD` that consumes it** (`packaging/arch/PKGBUILD`, assembled by
`tools/nivora/make_arch_package.sh`).

Why this one, and not the others:

| Option | Verdict |
|---|---|
| Tarball + binary `PKGBUILD` (chosen) | One build, many installs; the checksum in the `PKGBUILD` pins exactly the artifact; pacman is the update channel, which matches [ADR 0004](decisions/0004-upstream-service-isolation.md) (no in-app updater); uninstall is `pacman -R` and leaves user data alone; no new infrastructure |
| `PKGBUILD` that builds from source | Honest but impractical: about 30 GB of disk, hours of CPU and a toolchain bootstrap per install. Possible later, once the build is reproducible; not the first target |
| Flatpak | Zen's template exists (`build/flatpak/`), but it is Zen's identity and its sandbox changes how file dialogs, portals and profiles behave; a second thing to verify. Later |
| AppImage | Zen's `build/AppDir/` skeleton exists. Self-updating archives conflict with the "pacman is the update channel" rule. Not chosen |
| `.deb` / `.rpm` | Not the target platform |

Not done here: publishing. No release has been made and no package has been uploaded to GitHub
Releases or the AUR. Publishing is the maintainer's action.

## 2. What the package contains

| Path | Content |
|---|---|
| `/opt/nivora/` | The application exactly as `mach package` leaves it, including Firefox's own license notices |
| `/opt/nivora/distribution/policies.json` | `DisableAppUpdate: true` and the related policies: no in-app updating |
| `/usr/bin/nivora` | Symlink to `/opt/nivora/nivora` |
| `/usr/share/applications/nivora.desktop` | Launcher; handles `http`, `https` and the usual document and media types; "New Window" and "New Private Window" actions |
| `/usr/share/icons/hicolor/<size>/apps/nivora.png` | 16 to 512 px, from the generated mark |
| `/usr/share/metainfo/io.github.adrilabtech.nivora.metainfo.xml` | AppStream description for software centers |
| `/usr/share/licenses/nivora-browser-bin/` | `LICENSE`, `LICENSES.md` and `licenses/` |

Nothing is written outside `/opt` and `/usr`. Dependencies are the system libraries the build **links against**
(`readelf -d` of the executables and shared libraries, minus what the tarball ships itself and
glibc), mapped to Arch package names in [`check_arch_deps.py`](../tools/nivora/check_arch_deps.py), which
fails on any linked library without a package. NSS, NSPR and SQLite are bundled, so `nss` and
`dbus-glib` are not dependencies; `libpulse` is loaded at run time and is a dependency anyway. The
package *names* are written from knowledge of Arch's repositories (its hosts are not reachable from the
build environment): **unverified until `pacman` resolves them on Arch**.

## 3. Where user data lives

| Kind | Location | Notes |
|---|---|---|
| Application | `/opt/nivora` | owned by the package; replaced on upgrade |
| Profile (settings, bookmarks, history, cookies, passwords, extensions) | `~/.config/nivora/` (or `~/.nivora/` with `MOZ_LEGACY_HOME=1`) | Verified by test F-10: separate from Zen's and Firefox's |
| Caches | the profile's cache directory under `~/.cache` | disposable |
| Logs | none persistent by default | `MOZ_LOG` for debugging |

Neither installing, upgrading nor removing the package touches profile data. Upgrading never runs
anything against the profile; first start after an upgrade is the browser's normal profile upgrade.
**Before a major version, back up the profile directory.**

## 4. Updates

There is no in-app updater. `app.update.auto` is `false`, `surfer.json` has no update host, and the
packaged policy disables updating. A new version reaches users as a new package. The consequence,
recorded in [SECURITY.md](SECURITY.md) section 5, is that **security fixes depend on the maintainer
building and publishing a new package**. Rolling back is `pacman -U` on the previous package file.

## 5. Making a package (maintainer)

The one-command way, which is also what CI runs (`.github/workflows/nivora-build-linux.yml`, started by
hand, about two hours on a four-core runner, artifact kept 14 days, nothing published):

```sh
tools/nivora/build_linux.sh --apt --bootstrap    # Debian/Ubuntu; leaves out/ with the package inputs
```

By hand:

```sh
npx surfer build                      # or the release configuration, see BUILDING.md
./engine/mach package                 # leaves engine/obj-*/dist/nivora
tools/nivora/make_arch_package.sh engine/obj-x86_64-pc-linux-gnu/dist/nivora out/
cd out && makepkg -si                 # on Arch
```

Never package a development build as if it were a release: the sandbox configuration in
[BUILDING.md](BUILDING.md) disables the updater and the wasm sandbox and does no LTO or PGO.
A release package needs the release configuration, and the decisions listed there.

## 6. Verified and not verified

| | State |
|---|---|
| Assembly script, checksums, `package()` layout, desktop file, policy, icons, licenses | **Verified** by 11 tests that simulate `makepkg` (and fail when the symlink or the policy is wrong) |
| `makepkg` (Ubuntu's 6.0.2, as a non-root user), `desktop-file-validate`, `appstreamcli validate` | **Pass** (2026-10-27): the sources' checksums verify, `package()` runs, a `.pkg.tar.gz` (129 MB) is produced with the expected `.PKGINFO`; the desktop file validates; the AppStream file validates after a `<developer>` element was added. The package was then extracted into the container's `/`, `/usr/bin/nivora` pointed at `/opt/nivora/nivora`, and `tools/nivora/smoke.py --dist /opt/nivora` passed (starts, loads a page, creates only `~/.config/nivora`, exits). The X11 window class is `nivora`, matching `StartupWMClass` |
| Install and run on Ryoku Arch | **Reported working by the owner** (2026-10-27, the CI-built package, `pacman -U`); no details were recorded (session, GPU, uninstall, upgrade) |
| `pacman` dependency resolution as a test, `namcap`, uninstall on Arch Linux | **Not run.** `pacman` itself cannot resolve dependencies without Arch's databases; `namcap` is not packaged for Ubuntu. The README's install guide is the procedure for that first test |
| Build and package in CI | **Pass** (2026-10-27): the build job took 80 to 102 minutes on a GitHub runner (two runs); the package job (a real `makepkg`, the dependency check, a start-up smoke test of the packaged browser) takes under a minute and produced a 125 MB `.pkg.tar.zst`. One failure on the way and its cause are in [TESTING.md](TESTING.md). The CI-built package itself was not downloaded and run here |
| A package built from the real build | **Done** (2026-10-27): `./mach package` made `nivora-0.1.0a1.en-US.linux-x86_64.tar.xz` (3 min 49 s); `make_arch_package.sh` turned it into a 97 MB tarball (319 MB unpacked) with real checksums; the `package()` function of the `PKGBUILD` was run against that tree and produced the expected `/opt`, `/usr/bin`, desktop, icons (the real tree has 16, 32, 48, 64 and 128 px), metainfo and license files; the unpacked, policy-equipped copy starts and `about:policies` lists `DisableAppUpdate: true` |
| Reproducibility of the tarball | **Not verified** |
