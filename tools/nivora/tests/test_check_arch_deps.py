# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_arch_deps as cad  # noqa: E402

READELF = """
Dynamic section at offset 0x1000 contains 3 entries:
  Tag        Type                         Name/Value
 0x0000000000000001 (NEEDED)             Shared library: [libgtk-3.so.0]
 0x0000000000000001 (NEEDED)             Shared library: [libasound.so.2]
 0x0000000000000001 (NEEDED)             Shared library: [libnss3.so]
 0x000000000000000e (SONAME)             Library soname: [libxul.so]
"""

PKGBUILD = """pkgname=x
depends=('gtk3' 'alsa-lib>=1.2' 'dbus'
         'mime-types')
optdepends=('libnotify: notifications')
"""


class ParsingTest(unittest.TestCase):
    def test_needed_entries_are_read_and_soname_is_not(self):
        self.assertEqual(cad.parse_needed(READELF), ["libgtk-3.so.0", "libasound.so.2", "libnss3.so"])

    def test_depends_are_read_without_versions_and_optdepends_are_not(self):
        self.assertEqual(cad.parse_depends(PKGBUILD), {"gtk3", "alsa-lib", "dbus", "mime-types"})

    def test_a_pkgbuild_without_depends_is_an_error(self):
        with self.assertRaises(ValueError):
            cad.parse_depends("pkgname=x\n")


class CheckTest(unittest.TestCase):
    NEEDED = {"libgtk-3.so.0", "libasound.so.2", "libnss3.so", "libc.so.6", "libatk-1.0.so.0"}

    def test_bundled_and_glibc_libraries_need_no_package(self):
        missing, unknown = cad.check(self.NEEDED, {"libnss3.so"}, {"gtk3", "alsa-lib"})
        self.assertEqual((missing, unknown), ({}, []))

    def test_a_missing_package_is_named_with_its_libraries(self):
        missing, _ = cad.check(self.NEEDED, {"libnss3.so"}, {"gtk3"})
        self.assertEqual(missing, {"alsa-lib": ["libasound.so.2"]})

    def test_gtk3_covers_what_it_depends_on(self):
        missing, _ = cad.check({"libpango-1.0.so.0", "libX11.so.6", "libatk-1.0.so.0"}, set(), {"gtk3"})
        self.assertEqual(missing, {})

    def test_a_library_that_is_not_in_the_table_fails_loudly(self):
        _, unknown = cad.check({"libnewthing.so.1"}, set(), {"gtk3"})
        self.assertEqual(unknown, ["libnewthing.so.1"])

    def test_every_table_entry_names_a_plausible_package(self):
        for soname, package in cad.SONAME_PACKAGE.items():
            self.assertRegex(package, r"^[a-z0-9][a-z0-9+._-]*$", soname)


class ShippedPackageTest(unittest.TestCase):
    def test_the_shipped_pkgbuild_names_the_packages_the_table_requires_for_gtk3_and_audio(self):
        depends = cad.parse_depends(cad.DEFAULT_PKGBUILD.read_text(encoding="utf-8"))
        for required in ("gtk3", "alsa-lib", "libpulse", "mime-types", "ttf-font"):
            self.assertIn(required, depends)
        # NSS and NSPR are bundled in the application directory, so the system packages are not needed.
        self.assertNotIn("nss", depends)
        self.assertNotIn("dbus-glib", depends)


if __name__ == "__main__":
    unittest.main()
