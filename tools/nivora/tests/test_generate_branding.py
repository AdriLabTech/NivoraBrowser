# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from PIL import Image
    import generate_branding as gb
except ImportError:  # Pillow is only needed to regenerate icons
    gb = None

# What `surfer import` insists on, from node_modules/@zen-browser/surfer branding-patch.js.
REQUIRED = ["logo.png", "logo-mac.png", "firefox.ico", "firefox64.ico"] + [
    f"logo{size}.png" for size in (16, 22, 24, 32, 48, 64, 128, 256, 512)
]


@unittest.skipIf(gb is None, "Pillow is not installed")
class BrandingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.out = Path(cls.directory.name)
        cls.written = gb.generate(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_files_surfer_requires_exist(self):
        for name in REQUIRED:
            self.assertTrue((self.out / name).is_file(), name)

    def test_png_dimensions_match_their_names(self):
        for size in (16, 22, 24, 32, 48, 64, 128, 256, 512, 1024):
            with Image.open(self.out / f"logo{size}.png") as image:
                self.assertEqual(image.size, (size, size))

    def test_svgs_are_well_formed(self):
        for name in self.written:
            if name.endswith(".svg"):
                xml.dom.minidom.parse(str(self.out / name))

    def test_icons_use_only_palette_colors_and_transparency(self):
        palette = {gb.color(n) for n in ("surface-base", "separator", "text-muted", "text-primary")}
        with Image.open(self.out / "logo512.png").convert("RGBA") as image:
            # Anti-aliasing blends neighbours, so check the flat regions: center of the disc and the plate corner.
            disc = "#%02x%02x%02x" % image.getpixel((200, 256))[:3]
            plate = "#%02x%02x%02x" % image.getpixel((120, 120))[:3]
            self.assertIn(disc, palette)
            self.assertIn(plate, palette)
            self.assertEqual(image.getpixel((2, 2))[3], 0, "outside the plate must be transparent")


if __name__ == "__main__":
    unittest.main()
