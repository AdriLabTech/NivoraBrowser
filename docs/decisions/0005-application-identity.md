# 0005. Application identity

Status: accepted, corrected the same day; profile directory verified at run time · Date: 2026-10-26

## Context

Compile-time identity (application name, vendor, branding, distribution id) is baked into many
Firefox build outputs; changing it after a long build forces a near-complete rebuild. Profiles are
located from the application name, and Nivora must not interfere with an existing Zen profile.

## Decision

| Item | Value | Where |
|---|---|---|
| Product name | Nivora Browser (short: Nivora) | `surfer.json` |
| Binary / app name | `nivora` | `surfer.json` `binaryName`, `--with-app-name` |
| Base name | `Nivora` | `configs/common/mozconfig` |
| Vendor | AdriLabTech | `surfer.json` |
| Distribution id | `io.github.adrilabtech.nivora` | `configs/common/mozconfig` |
| Version | `0.1.0a1` | `surfer.json` `displayVersion` |
| Channel / brand key | `release` (Zen's `twilight` removed) | `surfer.json` |
| Background color | `#050505` | `surfer.json` |

The identity was fixed **before** the first long compile so that the object directory is reusable.

## Correction: the profile directory was Zen's

The first version of this record expected the profile to be separate from Zen's "from the differing
application name". That was wrong, and was found by reading `config.status` of the first build:
Zen's patch to `toolkit/moz.configure` sets the defaults of `MOZ_APP_PROFILE` and of the user
directory (`MOZ_USER_DIR`) to `zen`, and its patch to `nsXREDirProvider.cpp` builds the profile path
from `MOZ_APP_PROFILE`. A Nivora build would therefore have read and written `~/.zen`, Zen's real
profile, which the specification forbids (section 9.1).

`MOZ_APP_PROFILE` cannot be set from a mozconfig (configure refuses: "can not be set by mozconfig;
values are accepted from: implied"), so the fix is in Zen's own patch, `src/toolkit/moz-configure.patch`:
both defaults are now `nivora`. Verified: the patch applies cleanly to Firefox 158.0.1, and
`config.status` and `mozilla-config.h` of the rebuilt tree show `MOZ_APP_PROFILE = nivora` and
`#define MOZ_USER_DIR "nivora"`. `MOZ_USER_DIR` is a compile-time define, so the build in progress was
stopped and restarted; changing it later costs a full rebuild.

Independent evidence for the cause: the `application.ini` inside the official Zen 1.23.4b release
tarball (downloaded, extracted, **not run**) reads `Vendor=Mozilla`, `Name=Zen`, `RemotingName=zen`,
`Profile=zen`, `SourceStamp=541ee55...`. The binary was not executed: the environment's safety policy
declined running a downloaded executable, so the profile directory of the official Zen was inferred
from this file and from the source, not observed.

Verified at run time (2026-10-27, `tools/nivora/smoke.py`, test F-10): with an empty `HOME`, the
built browser creates `~/.config/nivora` (Firefox 158 follows the XDG layout unless
`MOZ_LEGACY_HOME=1`, which selects `~/.nivora`) and nothing named `.zen`, `.config/zen` or
`.mozilla`; `about:support` shows the profile under `.config/nivora`. `MOZ_APP_VENDOR` stays `Mozilla`
(`application.ini` of the packaged build says `Vendor=Mozilla`): Firefox's `browser/moz.configure`
implies it, so changing it needs a patch of its own and a full rebuild; on Linux the vendor is not
part of the profile path. Left for the release build.

## Not verified

- What happens when a `~/.zen` already exists: the empty-`HOME` run shows Nivora does not create or
  use one, but a checksum comparison against a populated Zen profile was not made.
- That nothing in the inherited Zen code assumes the binary is called `zen`.
- The distribution id is a naming choice, not a registered domain. Replace it if the project
  acquires a domain.

## Consequences

- Application id for desktop integration will be derived from these (`.desktop`, Flatpak id); to be
  settled in Phase III together with the packaging format.
