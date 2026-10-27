# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The window finder of tools/nivora/smoke_wayland.py on a recorded `swaymsg -t get_tree` shape."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smoke_wayland as sw  # noqa: E402

TREE = {
    "type": "root",
    "nodes": [
        {"type": "output", "nodes": [{"type": "workspace", "nodes": [
            {"type": "con", "app_id": "nivora", "name": "Smoke — Nivora Browser", "nodes": []},
            {"type": "con", "app_id": "foot", "name": "terminal", "nodes": []},
        ], "floating_nodes": [{"type": "floating_con", "app_id": "nivora", "name": "Library", "nodes": []}]}]}
    ],
}


class WindowsTest(unittest.TestCase):
    def test_finds_tiled_and_floating_windows(self):
        self.assertEqual(sw.windows(TREE), [("nivora", "Smoke — Nivora Browser"), ("foot", "terminal"), ("nivora", "Library")])

    def test_xwayland_windows_have_no_app_id_but_window_properties(self):
        tree = {"nodes": [{"window_properties": {"class": "Nivora"}, "name": "x", "nodes": []}]}
        self.assertEqual(sw.windows(tree), [(None, "x")])

    def test_empty_tree(self):
        self.assertEqual(sw.windows({}), [])


if __name__ == "__main__":
    unittest.main()
