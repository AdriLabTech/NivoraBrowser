# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The unsigned test extension of tools/nivora/check_signatures.py (no browser needed)."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_signatures as cs  # noqa: E402


class UnsignedExtensionTest(unittest.TestCase):
    def test_the_xpi_is_a_valid_unsigned_webextension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.xpi"
            cs.make_xpi(path)
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(names, ["manifest.json"], "nothing else, so nothing that looks like a signature")
        self.assertEqual(manifest["browser_specific_settings"]["gecko"]["id"], cs.ADDON_ID)
        self.assertEqual(manifest["manifest_version"], 2)

    def test_no_signature_files_are_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.xpi"
            cs.make_xpi(path)
            with zipfile.ZipFile(path) as archive:
                self.assertFalse([n for n in archive.namelist() if n.startswith("META-INF")])


if __name__ == "__main__":
    unittest.main()
