# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The heuristic and the size reader of tools/nivora/scan_mozilla_artwork.py, on small SVG files."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scan_mozilla_artwork as scan  # noqa: E402

COLORFUL = '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60" viewBox="0 0 80 60">' + "".join(
    f'<path fill="{c}" d="M0 0h1v1z"/>' for c in ("#ff6a00", "#ff0080", "#6a00ff", "#00c8ff")
) + "<!--" + "x" * 2600 + "--></svg>"
GRAY = '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60"><path fill="#777777" d="M0 0h1v1z"/>' + "<!--" + "x" * 2600 + "--></svg>"


class HeuristicTest(unittest.TestCase):
    def test_colorful_large_file_is_a_candidate(self):
        self.assertTrue(scan.is_candidate("browser/x/a.svg", COLORFUL))

    def test_gray_file_is_not(self):
        self.assertFalse(scan.is_candidate("browser/x/a.svg", GRAY))

    def test_small_file_is_not(self):
        self.assertFalse(scan.is_candidate("browser/x/a.svg", COLORFUL[:900] + "</svg>"))

    def test_exclusions_win(self):
        for path in ("browser/themes/shared/urlbar/engine-wordmarks/Bing.svg", "browser/themes/shared/weather/sunny.svg"):
            self.assertFalse(scan.is_candidate(path, COLORFUL), path)

    def test_dimensions_from_viewbox_and_attributes(self):
        self.assertEqual(scan.dimensions(COLORFUL), {"vw": 80, "vh": 60, "width": 80, "height": 60})
        self.assertEqual(scan.dimensions('<svg xmlns="http://www.w3.org/2000/svg" height="96px" viewBox="0 0 216 164"/>'),
                         {"vw": 216, "vh": 164, "width": None, "height": 96})
        self.assertEqual(scan.dimensions('<svg xmlns="http://www.w3.org/2000/svg" viewBox="28 15 162 159"/>'),
                         {"vw": 162, "vh": 159, "width": None, "height": None})

    def test_unreadable_or_sizeless_file(self):
        self.assertIsNone(scan.dimensions("<svg"))
        self.assertIsNone(scan.dimensions('<svg xmlns="http://www.w3.org/2000/svg"/>'))


class ScanTest(unittest.TestCase):
    def test_finds_uncovered_candidates_and_skips_symlinks_and_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            for rel, text in (("browser/themes/a.svg", COLORFUL), ("browser/themes/b.svg", COLORFUL),
                              ("browser/themes/tests/c.svg", COLORFUL), ("browser/themes/gray.svg", GRAY)):
                path = engine / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            (engine / "browser/themes/link.svg").symlink_to(engine / "browser/themes/a.svg")
            found = scan.scan(engine, covered={"browser/themes/b.svg"})
        self.assertEqual([f["path"] for f in found], ["browser/themes/a.svg"])


if __name__ == "__main__":
    unittest.main()
