# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_profile as cp  # noqa: E402


class FramingTest(unittest.TestCase):
    def test_a_message_is_its_length_a_colon_and_json(self):
        self.assertEqual(cp.encode([0, 1, "x", {}]), b'15:[0, 1, "x", {}]')

    def test_non_ascii_text_is_escaped_so_the_length_is_the_same_in_bytes_and_characters(self):
        self.assertEqual(cp.encode(["é"]), b'10:["\\u00e9"]')

    def test_decode_returns_one_message_and_the_rest(self):
        data = cp.encode([1, 1, None, {"a": 1}]) + cp.encode([1, 2, None, {}])
        first, rest = cp.decode(data)
        self.assertEqual(first, [1, 1, None, {"a": 1}])
        second, rest = cp.decode(rest)
        self.assertEqual(second, [1, 2, None, {}])
        self.assertEqual(rest, b"")

    def test_an_incomplete_message_waits_for_more_data(self):
        data = cp.encode([1, 1, None, {"long": "x" * 50}])
        for cut in (0, 1, 3, len(data) - 1):
            message, rest = cp.decode(data[:cut])
            self.assertIsNone(message)
            self.assertEqual(rest, data[:cut])

    def test_the_hello_the_server_sends_first_is_a_message_too(self):
        hello = b'50:{"applicationType":"gecko","marionetteProtocol":3}'
        message, rest = cp.decode(hello)
        self.assertEqual(message["applicationType"], "gecko")
        self.assertEqual(rest, b"")


class DigestTest(unittest.TestCase):
    def test_the_digest_changes_when_a_file_is_added_removed_or_edited(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            digests = cp.plant_foreign_profiles(home)
            self.assertEqual(set(digests), set(cp.FOREIGN))
            base = home / cp.FOREIGN[0]
            same = cp.tree_digest(base)
            self.assertEqual(same, digests[cp.FOREIGN[0]])
            (base / "new.txt").write_text("x")
            self.assertNotEqual(cp.tree_digest(base), same)
            (base / "new.txt").unlink()
            self.assertEqual(cp.tree_digest(base), same)
            (base / "profiles.ini").write_text("changed")
            self.assertNotEqual(cp.tree_digest(base), same)

    def test_a_read_does_not_change_a_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            digests = cp.plant_foreign_profiles(home)
            for rel in cp.FOREIGN:
                for path in (home / rel).rglob("*"):
                    if path.is_file():
                        path.read_bytes()
                self.assertEqual(cp.tree_digest(home / rel), digests[rel])


class ConfigurationTest(unittest.TestCase):
    def test_the_preferences_it_sets_are_real_nivora_or_zen_preferences(self):
        root = Path(__file__).resolve().parents[3]
        text = "".join(p.read_text() for p in (root / "prefs").rglob("*.yaml"))
        for name in cp.SET:
            self.assertIn(f"name: {name}", text)


if __name__ == "__main__":
    unittest.main()
