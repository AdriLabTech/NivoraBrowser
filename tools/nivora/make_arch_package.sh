#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Assemble the files `makepkg` needs from a built browser:
#   nivora-<ver>.linux-x86_64.tar.xz       the application (top-level directory `nivora/`)
#   nivora-licenses-<ver>.tar.xz           LICENSE, LICENSES.md, licenses/
#   PKGBUILD, nivora-browser-bin.install, nivora.desktop, io.github.adrilabtech.nivora.metainfo.xml
# with the real checksums written into the PKGBUILD. Nothing is installed or published.
#
# Usage: make_arch_package.sh <dist-directory> <output-directory>
#   <dist-directory> is the directory `mach package` leaves the application in
#   (engine/obj-*/dist/nivora), containing the `nivora` executable.
set -euo pipefail

dist=${1:?usage: make_arch_package.sh <dist-directory> <output-directory>}
out=${2:?usage: make_arch_package.sh <dist-directory> <output-directory>}
root=$(cd "$(dirname "$0")/../.." && pwd)

[ -x "$dist/nivora" ] || { echo "error: $dist/nivora is not an executable (is this the packaged dist directory?)" >&2; exit 2; }
version=$(sed -n 's/^pkgver=//p' "$root/packaging/arch/PKGBUILD")
[ -n "$version" ] || { echo "error: no pkgver in the PKGBUILD" >&2; exit 2; }

mkdir -p "$out"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

mkdir "$stage/nivora"
cp -a "$dist/." "$stage/nivora/"
tar -C "$stage" -cJf "$out/nivora-$version.linux-x86_64.tar.xz" nivora

mkdir -p "$stage/nivora-licenses"
cp "$root/LICENSE" "$root/docs/LICENSES.md" "$stage/nivora-licenses/"
cp -a "$root/licenses" "$stage/nivora-licenses/licenses"
tar -C "$stage" -cJf "$out/nivora-licenses-$version.tar.xz" nivora-licenses

cp "$root/packaging/arch/nivora-browser-bin.install" "$out/"
cp "$root/packaging/linux/nivora.desktop" \
   "$root/packaging/linux/io.github.adrilabtech.nivora.metainfo.xml" "$out/"

browser_sum=$(sha256sum "$out/nivora-$version.linux-x86_64.tar.xz" | cut -d' ' -f1)
licenses_sum=$(sha256sum "$out/nivora-licenses-$version.tar.xz" | cut -d' ' -f1)
sed -e "s/REPLACE_WITH_SHA256_OF_THE_BROWSER_TARBALL/$browser_sum/" \
    -e "s/REPLACE_WITH_SHA256_OF_THE_LICENSES_TARBALL/$licenses_sum/" \
    "$root/packaging/arch/PKGBUILD" > "$out/PKGBUILD"

echo "wrote $out"
echo "  browser tarball sha256: $browser_sum"
echo "  licenses tarball sha256: $licenses_sum"
echo "next: cd $out && makepkg -si   (on an Arch system; not run by this script)"
