# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_motion as gm  # noqa: E402


def overshoot(name):
    return max(gm.curve(gm.PRESETS[name][0])) - 1


class SpringCurveTest(unittest.TestCase):
    def test_every_curve_starts_at_rest_and_ends_exactly_on_target(self):
        for name, (zeta, _) in gm.PRESETS.items():
            values = gm.curve(zeta)
            self.assertEqual(len(values), gm.SAMPLES + 1, name)
            self.assertEqual(values[0], 0.0, name)
            self.assertEqual(values[-1], 1.0, name)

    def test_the_curve_is_within_one_percent_one_sample_before_the_end(self):
        for name, (zeta, _) in gm.PRESETS.items():
            self.assertLess(abs(gm.curve(zeta)[-2] - 1), 0.01, name)

    def test_a_critically_damped_spring_never_overshoots_and_only_rises(self):
        values = gm.curve(gm.PRESETS["smooth"][0])
        self.assertLessEqual(max(values), 1.0)
        self.assertEqual(values, sorted(values))

    def test_less_damping_overshoots_more(self):
        order = ["smooth", "snappy", "bouncy", "elastic"]
        peaks = [overshoot(name) for name in order]
        self.assertEqual(peaks, sorted(peaks))
        self.assertAlmostEqual(peaks[0], 0, places=3)
        self.assertGreater(peaks[1], 0.005)
        self.assertGreater(peaks[2], 0.08)
        self.assertGreater(peaks[3], 0.2)
        # Expressive, but never a rubber band: the wildest curve stays under a third of the travel.
        self.assertLess(peaks[3], 0.34)

    def test_the_underdamped_curve_matches_the_closed_form_at_its_first_peak(self):
        zeta = gm.PRESETS["bouncy"][0]
        peak = max(gm.curve(zeta, samples=400))
        # For a step response the first peak is 1 + exp(-pi * zeta / sqrt(1 - zeta^2)).
        import math

        expected = 1 + math.exp(-math.pi * zeta / math.sqrt(1 - zeta * zeta))
        self.assertAlmostEqual(peak, expected, places=2)


class GeneratedFileTest(unittest.TestCase):
    def test_the_shipped_file_is_what_the_generator_writes(self):
        self.assertEqual(gm.OUTPUT.read_text(encoding="utf-8"), gm.build())

    def test_every_preset_is_a_custom_property_with_a_linear_easing(self):
        text = gm.build()
        for name in gm.PRESETS:
            self.assertRegex(text, rf"--nivora-spring-{name}: linear\(0, ")

    def test_the_file_has_declarations_only(self):
        body = re.sub(r"/\*.*?\*/", "", gm.build(), flags=re.DOTALL)
        for line in filter(None, (l.strip() for l in body.splitlines())):
            self.assertTrue(line.startswith("--nivora-spring-") and line.endswith(";"), line)


if __name__ == "__main__":
    unittest.main()
