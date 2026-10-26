# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Guards for values that exist both as a preference and as a design token."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "nivora"))

import check_contrast as cc  # noqa: E402


def pref_value(path, name):
    """Return the raw value of the first `- name: <name>` entry of a prefs YAML file."""
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"^- name: " + re.escape(name) + r"\s*\n(?:  [a-z]+:.*\n)*?  value: (.+)$", text, re.MULTILINE
    )
    if not match:
        raise AssertionError(f"{name} not found in {path}")
    return match.group(1).strip().strip('"')


class PrefsMatchTokensTest(unittest.TestCase):
    def setUp(self):
        css = (ROOT / "src" / "nivora" / "theme" / "nivora-tokens.inc.css").read_text(encoding="utf-8")
        self.tokens = cc.parse_tokens(css)

    def test_accent_color_pref_is_the_neutral_token(self):
        accent = pref_value(ROOT / "prefs" / "zen" / "theme.yaml", "zen.theme.accent-color")
        self.assertEqual(accent.lower(), cc.resolve("ash-500", self.tokens))

    def test_default_scheme_is_dark(self):
        self.assertEqual(pref_value(ROOT / "prefs" / "zen" / "view.yaml", "zen.view.window.scheme"), "0")

    def test_no_zen_operated_endpoint_is_a_pref_default(self):
        """Prefs must not point Nivora at services run by the Zen project."""
        offenders = []
        for path in (ROOT / "prefs").rglob("*.yaml"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if re.search(r"https?://[^\s\"']*zen-browser\.(app|github\.io)", line):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
