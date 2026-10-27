#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Check that the PKGBUILD's `depends` cover the system libraries the browser links against.

It reads the NEEDED entries of the executables and shared libraries of a packaged build
(`readelf -d`), drops what the build ships itself (NSS, NSPR, SQLite, ...) and what glibc provides,
maps each remaining soname to the Arch package that owns it with the table below, and compares the
packages with the `depends` array of `packaging/arch/PKGBUILD`.

The mapping is written from knowledge of Arch's packages, not queried from a pacman database (Arch's
hosts are not reachable from the build environment): the check proves that *every hard link-time
need has a named package*, not that the package names are right. A soname that is not in the table
fails the check, so a new dependency can never slip in unnoticed.

Libraries the browser loads with dlopen at run time (PulseAudio, libnotify, VA-API, ...) are not
NEEDED entries; they belong in `optdepends` and are listed by hand in the PKGBUILD.

Usage: check_arch_deps.py --dist DIR [--pkgbuild FILE]
Exit status: 0 when covered, 1 when a package is missing or a soname is unknown, 2 on bad input.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PKGBUILD = ROOT / "packaging" / "arch" / "PKGBUILD"

# soname -> the Arch package that provides it. "gtk3" is the owner of what GTK 3 itself depends on
# (ATK, Wayland client library, ...): naming it here means "present whenever gtk3 is".
SONAME_PACKAGE = {
    "libgtk-3.so.0": "gtk3",
    "libgdk-3.so.0": "gtk3",
    "libatk-1.0.so.0": "gtk3",
    "libasound.so.2": "alsa-lib",
    "libdbus-1.so.3": "dbus",
    "libX11.so.6": "libx11",
    "libX11-xcb.so.1": "libx11",
    "libxcb.so.1": "libxcb",
    "libxcb-shm.so.0": "libxcb",
    "libXcomposite.so.1": "libxcomposite",
    "libXdamage.so.1": "libxdamage",
    "libXext.so.6": "libxext",
    "libXfixes.so.3": "libxfixes",
    "libXrandr.so.2": "libxrandr",
    "libXrender.so.1": "libxrender",
    "libXcursor.so.1": "libxcursor",
    "libXi.so.6": "libxi",
    "libXt.so.6": "libxt",
    "libfreetype.so.6": "freetype2",
    "libfontconfig.so.1": "fontconfig",
    "libharfbuzz.so.0": "harfbuzz",
    "libpango-1.0.so.0": "pango",
    "libpangocairo-1.0.so.0": "pango",
    "libcairo.so.2": "cairo",
    "libcairo-gobject.so.2": "cairo",
    "libgdk_pixbuf-2.0.so.0": "gdk-pixbuf2",
    "libgio-2.0.so.0": "glib2",
    "libgobject-2.0.so.0": "glib2",
    "libglib-2.0.so.0": "glib2",
    "libz.so.1": "zlib",
    "libstdc++.so.6": "gcc-libs",
    "libgcc_s.so.1": "gcc-libs",
}

# Provided by glibc (package `glibc`, always present).
GLIBC = {
    "libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1", "libresolv.so.2",
    "libutil.so.1", "ld-linux-x86-64.so.2", "libnsl.so.1", "libanl.so.1",
}

# What each package already pulls in, so a PKGBUILD may name only gtk3 for ATK and the like.
IMPLIED = {
    "gtk3": {"glib2", "gdk-pixbuf2", "pango", "cairo", "harfbuzz", "fontconfig", "freetype2",
             "libx11", "libxcomposite", "libxdamage", "libxext", "libxfixes", "libxrandr",
             "libxrender", "libxcursor", "libxi", "libxcb"},
}

NEEDED = re.compile(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]")


def parse_needed(readelf_output):
    """The sonames a `readelf -d` listing says the file needs."""
    return NEEDED.findall(readelf_output)


def parse_depends(pkgbuild_text):
    """The package names in the `depends=( ... )` array, without version constraints."""
    match = re.search(r"^depends=\((.*?)\)", pkgbuild_text, re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError("no depends array in the PKGBUILD")
    names = re.findall(r"'([^']+)'", match.group(1))
    return {re.split(r"[<>=]", n)[0] for n in names}


def check(needed, bundled, depends):
    """-> (missing {package: [sonames]}, unknown [sonames]) for a set of NEEDED sonames."""
    covered = set(depends)
    for package in list(covered):
        covered |= IMPLIED.get(package, set())
    missing, unknown = {}, []
    for soname in sorted(set(needed)):
        if soname in bundled or soname in GLIBC:
            continue
        package = SONAME_PACKAGE.get(soname)
        if package is None:
            unknown.append(soname)
        elif package not in covered:
            missing.setdefault(package, []).append(soname)
    return missing, unknown


def needed_by_tree(dist):
    """(needed sonames, bundled file names) of every ELF file directly in the dist directory."""
    needed, bundled = set(), {p.name for p in dist.iterdir() if p.is_file()}
    for path in sorted(dist.iterdir()):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix not in ("", ".so") and ".so." not in path.name:
            continue
        out = subprocess.run(["readelf", "-d", str(path)], capture_output=True, text=True)
        if out.returncode == 0:
            needed |= set(parse_needed(out.stdout))
    return needed, bundled


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True, help="the packaged application directory (contains `nivora`)")
    parser.add_argument("--pkgbuild", type=Path, default=DEFAULT_PKGBUILD)
    args = parser.parse_args(argv)
    if not (args.dist / "nivora").is_file():
        print(f"error: {args.dist}/nivora not found", file=sys.stderr)
        return 2
    try:
        depends = parse_depends(args.pkgbuild.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    needed, bundled = needed_by_tree(args.dist)
    missing, unknown = check(needed, bundled, depends)
    system = sorted(n for n in needed if n not in bundled and n not in GLIBC)
    print(f"{len(system)} system libraries are linked; depends names {len(depends)} packages")
    for package, sonames in sorted(missing.items()):
        print(f"MISSING  {package}: needed for {', '.join(sonames)}")
    for soname in unknown:
        print(f"UNKNOWN  {soname}: not in the soname table; add its Arch package to this tool")
    if not missing and not unknown:
        print("OK: every linked system library has a package in depends")
    return 1 if missing or unknown else 0


if __name__ == "__main__":
    sys.exit(main())
