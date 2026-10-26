# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Exercise the Arch packaging files without Arch.

`makepkg` is not available here, so this runs the same steps by hand: the script that assembles
the sources, then the PKGBUILD's `package()` function against a throw-away `srcdir` and `pkgdir`.
It proves the file layout and checksums; it does not prove that `makepkg` or `pacman` accept the
package.
"""

import configparser
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "nivora" / "make_arch_package.sh"
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ArchPackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        dist = base / "dist"
        icons = dist / "browser" / "chrome" / "icons" / "default"
        icons.mkdir(parents=True)
        for size in SIZES:
            (icons / f"default{size}.png").write_bytes(b"\x89PNG fake")
        (dist / "nivora").write_text("#!/bin/sh\necho nivora\n")
        (dist / "nivora").chmod(0o755)
        (dist / "omni.ja").write_bytes(b"fake")
        cls.out = base / "out"
        result = subprocess.run([str(SCRIPT), str(dist), str(cls.out)], capture_output=True, text=True)
        cls.assemble = result
        cls.version = next(
            line.split("=", 1)[1].strip()
            for line in (ROOT / "packaging/arch/PKGBUILD").read_text().splitlines()
            if line.startswith("pkgver=")
        )

        # What makepkg does: extract the sources into srcdir, then run package().
        cls.srcdir = base / "src"
        cls.pkgdir = base / "pkg"
        cls.srcdir.mkdir()
        cls.pkgdir.mkdir()
        for name in (f"nivora-{cls.version}.linux-x86_64.tar.xz", f"nivora-licenses-{cls.version}.tar.xz"):
            with tarfile.open(cls.out / name) as archive:
                archive.extractall(cls.srcdir)
        for name in ("nivora.desktop", "io.github.adrilabtech.nivora.metainfo.xml", "policies.json"):
            (cls.srcdir / name).write_bytes((cls.out / name).read_bytes())
        env = dict(os.environ, srcdir=str(cls.srcdir), pkgdir=str(cls.pkgdir))
        cls.package = subprocess.run(
            ["bash", "-c", f"set -e; source '{cls.out / 'PKGBUILD'}'; package"],
            capture_output=True, text=True, env=env,
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_assembling_succeeds(self):
        self.assertEqual(self.assemble.returncode, 0, self.assemble.stderr)

    def test_pkgbuild_checksums_match_the_tarballs(self):
        text = (self.out / "PKGBUILD").read_text()
        self.assertNotIn("REPLACE_WITH", text)
        self.assertIn(sha256(self.out / f"nivora-{self.version}.linux-x86_64.tar.xz"), text)
        self.assertIn(sha256(self.out / f"nivora-licenses-{self.version}.tar.xz"), text)

    def test_package_function_succeeds_under_set_e(self):
        self.assertEqual(self.package.returncode, 0, self.package.stderr)

    def test_executable_and_launcher_symlink(self):
        self.assertTrue((self.pkgdir / "opt/nivora/nivora").is_file())
        link = self.pkgdir / "usr/bin/nivora"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "/opt/nivora/nivora")

    def test_updates_are_disabled_by_policy(self):
        policy = json.loads((self.pkgdir / "opt/nivora/distribution/policies.json").read_text())
        self.assertIs(policy["policies"]["DisableAppUpdate"], True)

    def test_desktop_file_is_complete(self):
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.optionxform = str
        parser.read(self.pkgdir / "usr/share/applications/nivora.desktop")
        entry = parser["Desktop Entry"]
        self.assertEqual(entry["Type"], "Application")
        self.assertEqual(entry["Exec"], "nivora %u")
        self.assertEqual(entry["Icon"], "nivora")
        self.assertEqual(entry["StartupWMClass"], "nivora")
        self.assertIn("x-scheme-handler/https;", entry["MimeType"])
        self.assertIn("x-scheme-handler/http;", entry["MimeType"])
        for action in entry["Actions"].strip(";").split(";"):
            self.assertIn(f"Desktop Action {action}", parser)

    def test_icons_for_every_size_are_installed(self):
        for size in SIZES:
            self.assertTrue((self.pkgdir / f"usr/share/icons/hicolor/{size}x{size}/apps/nivora.png").is_file(), size)

    def test_licenses_are_installed(self):
        base = self.pkgdir / "usr/share/licenses/nivora-browser-bin"
        self.assertTrue((base / "LICENSE").is_file())
        self.assertTrue((base / "LICENSES.md").is_file())
        self.assertTrue((base / "licenses" / "MIT-phosphor-icons.txt").is_file())

    def test_appstream_metadata_is_installed(self):
        self.assertTrue((self.pkgdir / "usr/share/metainfo/io.github.adrilabtech.nivora.metainfo.xml").is_file())

    def test_nothing_outside_the_expected_prefixes(self):
        top = {p.name for p in self.pkgdir.iterdir()}
        self.assertEqual(top, {"opt", "usr"})

    def test_a_directory_that_is_not_a_dist_is_refused(self):
        with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as out:
            result = subprocess.run([str(SCRIPT), empty, out], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
