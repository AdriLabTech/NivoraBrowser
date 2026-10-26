# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_icons as gi  # noqa: E402


class ShippedIconsTest(unittest.TestCase):
    """Nivora must not ship icons it has no license to redistribute."""

    def test_every_icon_in_the_tree_comes_from_phosphor(self):
        self.assertEqual(gi.check(gi.DEFAULT_OUT), [])

    def test_icons_are_well_formed_and_theme_aware(self):
        for path in sorted(gi.DEFAULT_OUT.glob("*.svg")):
            text = path.read_text(encoding="utf-8")
            body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
            xml.dom.minidom.parseString(body)  # raises on malformed XML
            self.assertIn('fill="context-fill"', body, path.name)
            self.assertNotIn("currentColor", body, path.name)

    def test_the_license_text_ships_next_to_the_icons(self):
        text = (gi.DEFAULT_OUT / "phosphor-LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)
        self.assertIn("Phosphor Icons", text)


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        for folder, suffix in (("bold", "-bold"), ("fill", "-fill")):
            (root / folder).mkdir()
            for name in ("gear", "camera"):
                (root / folder / f"{name}{suffix}.svg").write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
                    f'<path d="M0 0h{len(name)}"/></svg>',
                    encoding="utf-8",
                )
        self.phosphor = root

    def tearDown(self):
        self.directory.cleanup()

    def test_plain_fill_slash_and_flip(self):
        plain = gi.build(self.phosphor, {"icon": "gear"})
        self.assertIn('<path d="M0 0h4"/>', plain)
        self.assertNotIn("<mask", plain)
        filled = gi.build(self.phosphor, {"icon": "gear", "weight": "fill"})
        self.assertIn('<path d="M0 0h4"/>', filled)
        slashed = gi.build(self.phosphor, {"icon": "camera", "slash": True})
        self.assertIn("<mask", slashed)
        self.assertIn(gi.SLASH, slashed)
        flipped = gi.build(self.phosphor, {"icon": "gear", "flip": True})
        self.assertIn("matrix(-1 0 0 1 256 0)", flipped)

    def test_missing_glyph_is_an_error(self):
        with self.assertRaises(gi.IconError):
            gi.build(self.phosphor, {"icon": "does-not-exist"})

    def test_output_carries_the_marker_and_is_xml(self):
        text = gi.build(self.phosphor, {"icon": "gear", "slash": True})
        self.assertIn(gi.MARKER, text)
        xml.dom.minidom.parseString("\n".join(l for l in text.splitlines() if not l.startswith("#")))

    def test_map_entries_have_an_icon(self):
        mapping = json.loads(gi.MAP_FILE.read_text(encoding="utf-8"))["icons"]
        self.assertEqual(len(mapping), 154)
        for name, spec in mapping.items():
            self.assertTrue(spec.get("icon"), name)


if __name__ == "__main__":
    unittest.main()
