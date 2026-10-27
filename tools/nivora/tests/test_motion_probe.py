# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The frame arithmetic of tools/nivora/motion_probe.py, on synthetic frames (no browser, no ffmpeg)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import motion_probe as mp  # noqa: E402

SIZE = mp.SMALL_W * mp.SMALL_H


def frame(value, changed=0):
    """A flat frame of `value`, with `changed` leading pixels set to 255."""
    return bytes([255] * changed + [value] * (SIZE - changed))


class AnalyseTest(unittest.TestCase):
    def test_still_picture_has_no_motion(self):
        self.assertIsNone(mp.analyse([frame(10)] * 10, 30))

    def test_motion_is_measured_from_first_to_last_change(self):
        frames = [frame(10)] * 4 + [frame(10, 2000), frame(10, 8000), frame(10, 12000)] + [frame(10, 12000)] * 5
        result = mp.analyse(frames, 30)
        self.assertEqual(result["first_change_frame"], 4)
        self.assertEqual(result["frames"], 3)
        self.assertEqual(result["duration_ms"], round(3 * 1000 / 30))
        self.assertGreater(result["peak_change"], 0.1)

    def test_a_stall_inside_the_motion_is_reported(self):
        frames = [frame(10, 0), frame(10, 4000)] + [frame(10, 4000)] * 3 + [frame(10, 9000)]
        result = mp.analyse(frames, 30)
        self.assertEqual(result["frames"], 2)
        self.assertGreaterEqual(result["max_gap_ms"], round(3 * 1000 / 30))

    def test_change_ignores_tiny_differences(self):
        a = bytes([100] * SIZE)
        b = bytes([103] * SIZE)
        self.assertEqual(mp.change(a, b), 0)
        self.assertEqual(mp.change(a, bytes([120] * SIZE)), 1)


class ScenarioTest(unittest.TestCase):
    def test_every_scenario_can_be_replayed(self):
        for name, scenario in mp.SCENARIOS.items():
            for key in ("urls", "settle", "actions", "record"):
                self.assertIn(key, scenario, f"{name} lacks {key}")

    def test_each_off_scenario_repeats_an_interaction_with_the_setting_off(self):
        off = {name: s for name, s in mp.SCENARIOS.items() if name.endswith("-off")}
        self.assertGreaterEqual(len(off), 4)
        for name, scenario in off.items():
            base = mp.SCENARIOS[name[: -len("-off")]]
            self.assertEqual(scenario["prefs"], {"nivora.ui.animations": False}, name)
            self.assertEqual(scenario["actions"], base["actions"], name)
            self.assertNotIn("nivora.ui.animations", base.get("prefs", {}), name)

    def test_the_boot_scenario_records_from_before_the_browser_starts(self):
        self.assertTrue(mp.SCENARIOS["boot"]["boot"])


if __name__ == "__main__":
    unittest.main()
