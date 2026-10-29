# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_newtab as gn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


class NewTabBackgroundTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = gn.render(640).convert("L")

    def test_it_is_sixteen_by_nine(self):
        self.assertEqual(self.image.size, (640, 360))

    def test_it_is_dark_enough_for_the_palette_to_open_over_it(self):
        pixels = list(self.image.getdata())
        self.assertLess(sum(pixels) / len(pixels), 40)
        # The corona is the brightest thing, and it is never pure white.
        self.assertLess(max(pixels), 235)

    def test_the_eclipse_is_a_dark_disc_in_the_middle_with_light_around_it(self):
        w, h = self.image.size
        centre = self.image.getpixel((w // 2, round(h * 0.46)))
        rim = max(self.image.getpixel((w // 2 + dx, round(h * 0.46))) for dx in range(int(h * 0.19), int(h * 0.19) + 12))
        corner = self.image.getpixel((2, 2))
        self.assertLess(centre, 15)
        self.assertGreater(rim, 90)
        self.assertLess(corner, 25)


class ShippedBackgroundTest(unittest.TestCase):
    def test_the_committed_image_is_the_size_the_stylesheet_expects(self):
        with Image.open(gn.DEFAULT_OUT) as image:
            self.assertEqual(image.size, (2560, 1440))
        self.assertLess(gn.DEFAULT_OUT.stat().st_size, 200 * 1024)

    def test_the_rule_names_the_image_the_package_ships(self):
        jar = (ROOT / "src" / "zen" / "common" / "jar.inc.mn").read_text(encoding="utf-8")
        css = (ROOT / "src" / "nivora" / "theme" / "nivora-polish.inc.css").read_text(encoding="utf-8")
        self.assertIn("content/browser/nivora/nivora-newtab.webp", jar)
        self.assertIn("chrome://browser/content/nivora/nivora-newtab.webp", css)

    def test_the_preference_that_gates_it_is_defined_and_in_the_settings_schema(self):
        yaml = (ROOT / "prefs" / "nivora" / "nivora.yaml").read_text(encoding="utf-8")
        schema = (ROOT / "src" / "nivora" / "modules" / "NivoraSettingsCore.mjs").read_text(encoding="utf-8")
        css = (ROOT / "src" / "nivora" / "theme" / "nivora-polish.inc.css").read_text(encoding="utf-8")
        self.assertIn("- name: nivora.ui.newtab-background", yaml)
        self.assertIn('pref: "nivora.ui.newtab-background"', schema)
        self.assertIn('-moz-pref("nivora.ui.newtab-background")', css)


if __name__ == "__main__":
    unittest.main()
