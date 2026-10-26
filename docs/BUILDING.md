# Building Nivora

Nivora builds with Zen's tooling on the Firefox source. This document records the procedure that
was actually executed, the problems met and their fixes, and the resources used. Anything not
executed is marked **unverified**.

Reference environment (the only one used so far): Ubuntu 24.04 container, 4 cores, 15 GB RAM,
about 30 GB free disk, root user, outbound access through an allow-list proxy. Linux x86_64 only.

## 1. Requirements

| Item | Needed | Notes |
|---|---|---|
| Disk | ~30 GB free | Firefox source 5 GB + its `.git` 1 GB + object directory (see section 5) |
| RAM | 8 GB minimum | linking `libxul` is the peak |
| Node.js | 22 (`.nvmrc`) | for `surfer` |
| Python | 3.11 (`.python-version`); 3.13 worked | `mach` creates its own virtualenvs |
| Rust | `rust-toolchain.toml` pins 1.95.0; Firefox 158 needs >= 1.90 | |
| clang / LLVM | **>= 19** | Firefox 158 refuses 18 |
| cbindgen | >= 0.29.4 | |
| System libraries | GTK 3, dbus-glib, PulseAudio, ALSA, libXt, startup-notification, libdrm and the X11 development packages | |
| Tools | `nasm`, `yasm`, `m4`, `autoconf2.13`, `lld`, `unzip`, `zip`, `git` | |

Zen's normal route to all of this is `npm run bootstrap` (`mach bootstrap`), which downloads
prebuilt toolchains from Mozilla's CI. In the reference environment that host is blocked, so the
toolchain came from the distribution instead (section 2). On a normal machine use `bootstrap`.

## 2. Procedure that was executed

### 2.1 System packages (Ubuntu 24.04, as root)

```sh
apt-get install -y --no-install-recommends \
  libgtk-3-dev libdbus-glib-1-dev libdbus-1-dev libpulse-dev libasound2-dev libxt-dev \
  libstartup-notification0-dev libx11-xcb-dev libdrm-dev libcurl4-openssl-dev \
  libxcomposite-dev libxdamage-dev libxrandr-dev libxcursor-dev libxi-dev libgbm-dev \
  libxkbcommon-dev yasm autoconf2.13 unzip zip python3-venv \
  clang-19 libclang-19-dev llvm-19-dev lld-19 \
  xvfb x11-apps x11-utils xdotool imagemagick fonts-dejavu-core fonts-liberation
cargo install cbindgen --version 0.29.4 --locked
```

`clang-19` comes from `noble-updates/universe`. The last line (Xvfb and friends) is only for
running the browser without a display. Arch Linux: install the equivalent packages with `pacman`
(**unverified**; Arch's `firefox` package lists the build dependencies).

### 2.2 Repository, dependencies, Firefox source

```sh
npm ci
git clone --depth 1 --branch FIREFOX_158_0_1_RELEASE \
  https://github.com/mozilla-firefox/firefox engine
```

The normal route is `npm run download`, which fetches the source tarball from
`archive.mozilla.org`. That host was unreachable, so the GitHub mirror of Mozilla's repository was
used at the release tag. The tag matches `surfer.json` (`version.version` is `158.0.1`, and so is
`browser/config/version.txt` in the checkout). A byte-for-byte comparison with
the official tarball was **not** done; the evidence of equivalence is that all 263 Zen patches apply.

### 2.3 Configure and import

```sh
npx surfer set brand release
npx surfer set buildMode dev
(cd tools/ffprefs && cargo run --bin ffprefs -- ../../)   # prefs/*.yaml -> engine/.../zen.js
python3 scripts/update_service_dumps.py                   # merges configs/dumps into the engine
npx surfer import                                         # patches, new files, branding
```

`npm run import` runs exactly these three steps. They were run individually.
Result: `surfer import` reported 273 steps, 0 failures.

### 2.4 Local `mozconfig` (git-ignored, reference environment only)

```sh
# mozconfig at the repository root; surfer appends it to the generated engine/mozconfig
ac_add_options --disable-tests
ac_add_options --disable-crashreporter
ac_add_options --disable-debug-symbols
ac_add_options --disable-geckodriver
ac_add_options --disable-rust-tests
ac_add_options --disable-updater
ac_add_options --without-wasm-sandboxed-libraries
ac_add_options --enable-linker=lld
mk_add_options MOZ_MAKE_FLAGS="-j4"
export CC=clang-19
export CXX=clang++-19
export HOST_CC=clang-19
export HOST_CXX=clang++-19
ac_add_options --with-libclang-path=/usr/lib/llvm-19/lib
ac_add_options --with-clang-path=/usr/bin/clang-19
unset MOZ_STDCXX_COMPAT
```

This is not the release configuration (that is `configs/common/mozconfig` with `ZEN_RELEASE=1`,
which enables LTO, PGO on x86_64 and Widevine, and needs `mach bootstrap` toolchains).
`--disable-updater` and `--without-wasm-sandboxed-libraries` exist only because the matching
toolchain downloads were unreachable; a release build must make a deliberate decision on both.

### 2.5 Build and run

```sh
npx surfer build --jobs 4        # = mach configure + mach build, Nivora mozconfig applied
npm start                        # cd engine && ./mach run --noprofile  (uses the app's default profile directory)
# disposable profile, recommended for testing; on a headless machine add xvfb-run:
xvfb-run -a ./engine/mach run --temp-profile
```

After the first full build, interface-only changes (CSS, JS, prefs, `.ftl`) do not need a rebuild
of C++: `npx surfer build --ui` (`mach build faster`) repackages them in seconds to minutes.

## 3. Problems met and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Only clang/llvm 19.0 or newer is supported (found version 18.1.3)` | Distribution default is clang 18 | Install `clang-19`, set `CC`/`CXX`, `--with-libclang-path` |
| `stdc++compat.cpp: '_State' is a private member of 'std::thread'` | Zen's `configs/linux/mozconfig` sets `MOZ_STDCXX_COMPAT=1` (an old-glibc compatibility shim) which does not compile against GCC 13 headers | `unset MOZ_STDCXX_COMPAT` for local builds. Arch ships newer libstdc++ and does not need the shim; the release configuration is a Stable-phase decision |
| `FileNotFoundError: .../modules/libpref/init/zen-static-prefs.inc` | The pref files are generated by `ffprefs`, which `surfer import` alone does not run | Run `ffprefs` (or `npm run import`) |
| `FileNotFoundError: engine/zen/moz.build` | `engine/zen/**` are absolute symlinks into the `src/` of the checkout that ran the import; that checkout had been deleted | Re-run `surfer import` from the current checkout (after `git checkout` + `git clean` inside `engine/`), or re-point the links |
| `You have not imported all of your patches` then a yes/no prompt | `surfer build` compares the number of imported patches with `.surfer/patchCount`; non-interactive runs abort | Import first. `--skip-patch-check` bypasses it |
| `surfer import` fails on `browser-js.patch` | Patches belong to a different Firefox version (Zen `dev` targets 159.0) | Use the Firefox version in `surfer.json` for the Zen revision you imported |
| Two builds in one object directory | A second `surfer build` was started while the first was still unwinding | One build per object directory; wait for `gmake` to exit |

## 4. Not verified yet

- `npm run download` and `npm run bootstrap` (blocked hosts).
- Building on Arch Linux or Ryoku Arch.
- A release configuration build, `npm run package`, the Windows and macOS targets.
- Reproducibility across two builds.

## 5. Build results

_Recorded when the baseline build finishes._

| Measure | Value |
|---|---|
| Result | pending |
| Wall time (4 cores, `-j4`) | pending |
| Object directory size | pending |
| Peak RAM | pending |

## 6. Cleaning

`engine/obj-x86_64-pc-linux-gnu/` holds all build output and is safe to delete between experiments
(`./mach clobber`). Never delete `engine/` while a build is running. Test with `mach run --temp-profile`, which creates and discards a profile. `npm start` passes
`--noprofile`, which means the browser's normal profile directory is used; this is expected to be
separate from Zen's (`~/.zen`) because the binary and application name differ, but that has not
been verified yet ([ADR 0005](decisions/0005-application-identity.md)).
