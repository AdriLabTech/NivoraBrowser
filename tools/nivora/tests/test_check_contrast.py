# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_contrast as cc  # noqa: E402


class ContrastMathTest(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(cc.contrast_ratio("#000000", "#ffffff"), 21.0, places=6)

    def test_ratio_is_symmetric(self):
        self.assertAlmostEqual(
            cc.contrast_ratio("#777777", "#101010"), cc.contrast_ratio("#101010", "#777777")
        )

    def test_known_value(self):
        # #777777 on white is the textbook 4.48:1 example.
        self.assertAlmostEqual(cc.contrast_ratio("#777777", "#ffffff"), 4.48, places=2)


class TokenParsingTest(unittest.TestCase):
    def test_comments_are_ignored(self):
        tokens = cc.parse_tokens("/* --nivora-fake: #000000; */ --nivora-real: #ffffff;")
        self.assertEqual(tokens, {"real": "#ffffff"})

    def test_var_chain_resolves(self):
        tokens = cc.parse_tokens(
            "--nivora-a: #112233; --nivora-b: var(--nivora-a); --nivora-c: var(--nivora-b);"
        )
        self.assertEqual(cc.resolve("c", tokens), "#112233")

    def test_cycle_is_rejected(self):
        tokens = cc.parse_tokens("--nivora-a: var(--nivora-b); --nivora-b: var(--nivora-a);")
        with self.assertRaises(cc.TokenError):
            cc.resolve("a", tokens)

    def test_non_hex_value_is_rejected(self):
        tokens = cc.parse_tokens("--nivora-a: rgb(0 0 0);")
        with self.assertRaises(cc.TokenError):
            cc.resolve("a", tokens)

    def test_conflicting_redeclaration_is_rejected(self):
        with self.assertRaises(cc.TokenError):
            cc.parse_tokens("--nivora-a: #000000; --nivora-a: #111111;")


class ShippedPaletteTest(unittest.TestCase):
    """The palette that ships in the repository must satisfy its own policy."""

    def test_shipped_palette_passes(self):
        self.assertEqual(cc.main([]), 0)

    def test_failing_pair_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            tokens = Path(directory) / "tokens.css"
            tokens.write_text(
                "--nivora-bg: #101010; --nivora-fg: #202020;", encoding="utf-8"
            )
            pairs = Path(directory) / "pairs.json"
            pairs.write_text(
                json.dumps({"surfaces": ["bg"], "pairs": [{"fg": "fg", "on": "surfaces", "min": 4.5}]}),
                encoding="utf-8",
            )
            self.assertEqual(cc.main(["--tokens", str(tokens), "--pairs", str(pairs)]), 1)

    def test_missing_token_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as directory:
            tokens = Path(directory) / "tokens.css"
            tokens.write_text("--nivora-bg: #101010;", encoding="utf-8")
            pairs = Path(directory) / "pairs.json"
            pairs.write_text(
                json.dumps({"surfaces": ["bg"], "pairs": [{"fg": "nope", "on": "surfaces", "min": 4.5}]}),
                encoding="utf-8",
            )
            self.assertEqual(cc.main(["--tokens", str(tokens), "--pairs", str(pairs)]), 2)


if __name__ == "__main__":
    unittest.main()
