# 0005. Application identity

Status: accepted, partly unverified · Date: 2026-10-26

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

## Not verified

- That the profile directory is separate from Zen's (`~/.zen`) and from Firefox's. Expected from the
  differing application name; to be confirmed by running the build with a fresh `HOME`.
- That nothing in the inherited Zen code assumes the binary is called `zen`.
- The distribution id is a naming choice, not a registered domain. Replace it if the project
  acquires a domain.

## Consequences

- Application id for desktop integration will be derived from these (`.desktop`, Flatpak id); to be
  settled in Phase III together with the packaging format.
