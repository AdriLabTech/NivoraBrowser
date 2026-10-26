# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import upstream_check as uc  # noqa: E402

PIN = {
    "zen": {"repo": "z", "tag": "1.23.4b", "commit": "aaa", "firefox": "158.0.1"},
    "firefox": {"repo": "f", "tag": "FIREFOX_158_0_1_RELEASE", "commit": "bbb"},
}


class TagTest(unittest.TestCase):
    def test_release_tags_parse(self):
        self.assertEqual(uc.parse_zen_tag("1.23.4b"), (1, 23, 4))
        self.assertEqual(uc.parse_zen_tag("1.23b"), (1, 23, 0))
        self.assertIsNone(uc.parse_zen_tag("twilight-1"))
        self.assertIsNone(uc.parse_zen_tag("1.23.4"))

    def test_versions_compare_numerically_not_as_text(self):
        self.assertGreater(uc.parse_zen_tag("1.100b"), uc.parse_zen_tag("1.23.4b"))
        self.assertGreater(uc.parse_zen_tag("1.23.10b"), uc.parse_zen_tag("1.23.9b"))

    def test_firefox_tag_name(self):
        self.assertEqual(uc.firefox_tag("158.0.1"), "FIREFOX_158_0_1_RELEASE")
        self.assertEqual(uc.firefox_tag("159.0"), "FIREFOX_159_0_RELEASE")

    def test_newer_releases_are_sorted_and_exclude_current_and_non_releases(self):
        tags = {"1.23.4b": "a", "1.23.10b": "b", "1.23.5b": "c", "1.22b": "d", "twilight-1": "e"}
        self.assertEqual(uc.newer_releases("1.23.4b", tags), ["1.23.5b", "1.23.10b"])
        self.assertEqual(uc.newer_releases("1.23.10b", tags), [])

    def test_a_pin_that_is_not_a_release_is_an_error(self):
        with self.assertRaises(uc.CheckError):
            uc.newer_releases("twilight-1", {})


class ReportTest(unittest.TestCase):
    def test_up_to_date(self):
        report = uc.build_report(PIN, {"1.23.4b": "aaa"}, {"FIREFOX_158_0_1_RELEASE": "bbb"}, {})
        self.assertTrue(report["zen_tag_commit_matches_pin"])
        self.assertTrue(report["firefox_tag_commit_matches_pin"])
        self.assertEqual(report["candidates"], [])
        self.assertIn("No newer Zen release", uc.render(report))

    def test_a_moved_tag_is_flagged(self):
        report = uc.build_report(PIN, {"1.23.4b": "zzz"}, {"FIREFOX_158_0_1_RELEASE": "bbb"}, {})
        self.assertFalse(report["zen_tag_commit_matches_pin"])
        self.assertIn("the tag was moved", uc.render(report))

    def test_candidate_reports_the_firefox_it_needs(self):
        remote = {"1.23.4b": "aaa", "1.24b": "ccc"}
        firefox = {"FIREFOX_158_0_1_RELEASE": "bbb", "FIREFOX_159_0_RELEASE": "ddd"}
        report = uc.build_report(PIN, remote, firefox, {"1.24b": "159.0"})
        (candidate,) = report["candidates"]
        self.assertEqual(candidate["firefox_tag"], "FIREFOX_159_0_RELEASE")
        self.assertTrue(candidate["firefox_tag_exists"])
        self.assertTrue(candidate["firefox_changes"])
        self.assertIn("`1.24b`", uc.render(report))

    def test_candidate_without_its_firefox_tag_is_visible(self):
        report = uc.build_report(PIN, {"1.23.4b": "aaa", "1.24b": "c"}, {"FIREFOX_158_0_1_RELEASE": "bbb"}, {"1.24b": "159.0"})
        self.assertFalse(report["candidates"][0]["firefox_tag_exists"])

    def test_root_check_line(self):
        report = uc.build_report(PIN, {"1.23.4b": "aaa"}, {"FIREFOX_158_0_1_RELEASE": "bbb"}, {})
        self.assertIn("byte for byte: yes", uc.render(report, True))
        self.assertIn("byte for byte: **NO**", uc.render(report, False))


class PinFileTest(unittest.TestCase):
    def test_pin_file_is_consistent_with_surfer_json(self):
        pin = json.loads(uc.PIN_FILE.read_text(encoding="utf-8"))
        surfer = json.loads((uc.ROOT / "surfer.json").read_text(encoding="utf-8"))
        self.assertEqual(pin["zen"]["firefox"], surfer["version"]["version"])
        self.assertEqual(uc.firefox_tag(pin["zen"]["firefox"]), pin["firefox"]["tag"])
        self.assertIsNotNone(uc.parse_zen_tag(pin["zen"]["tag"]))


if __name__ == "__main__":
    unittest.main()
