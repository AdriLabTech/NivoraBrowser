# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "src" / "nivora" / "theme" / "images" / "nivora-guide.png"


class GuideSpriteTest(unittest.TestCase):
    """The tour's guide is the pixel-art character of the Claude Code plugin for Ryoku, copied as it is."""

    def test_the_sheet_is_ten_columns_of_40_by_46_cells(self):
        with Image.open(SHEET) as image:
            self.assertEqual(image.size, (400, 276))
            self.assertEqual(image.mode, "RGBA")

    def test_it_is_pixel_art_pixels_are_fully_on_or_off(self):
        with Image.open(SHEET) as image:
            alphas = {pixel[3] for pixel in image.convert("RGBA").getdata()}
        self.assertEqual(alphas, {0, 255})

    def test_the_53_cells_are_drawn_and_the_rest_of_the_sheet_is_empty(self):
        with Image.open(SHEET) as image:
            image = image.convert("RGBA")
            for index in range(60):
                column, row = index % 10, index // 10
                cell = image.crop((column * 40, row * 46, column * 40 + 40, row * 46 + 46))
                drawn = cell.getbbox() is not None
                self.assertEqual(drawn, index < 53, f"cell {index}")

    def test_the_stylesheet_scales_it_by_an_integer_with_no_smoothing_and_the_package_ships_it(self):
        css = (ROOT / "src" / "nivora" / "theme" / "nivora-tutorial.inc.css").read_text(encoding="utf-8")
        jar = (ROOT / "src" / "zen" / "common" / "jar.inc.mn").read_text(encoding="utf-8")
        self.assertIn("chrome://browser/content/nivora/nivora-guide.png", css)
        self.assertIn("1200px 828px", css)  # 3 x 400, 3 x 276
        self.assertIn("image-rendering: pixelated", css)
        self.assertIn("content/browser/nivora/nivora-guide.png", jar)

    def test_the_tour_sheet_has_no_hex_color_and_blurs_only_the_bubble(self):
        css = (ROOT / "src" / "nivora" / "theme" / "nivora-tutorial.inc.css").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b", code), [])
        self.assertEqual(len(re.findall(r"blur\(", code)), 1)


if __name__ == "__main__":
    unittest.main()
