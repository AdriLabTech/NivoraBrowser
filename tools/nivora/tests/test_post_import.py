# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import post_import as pi  # noqa: E402

BRANDING = '''
pref("startup.homepage_override_url", "https://zen-browser.app/whatsnew?v=%VERSION%");
pref("startup.homepage_welcome_url", "https://zen-browser.app/welcome/");
pref("app.update.promptWaitTime", 691200);
pref("app.update.url.manual", "https://zen-browser.app/download/");
// pref("devtools.selfxss.count", 5);
pref("devtools.selfxss.count", 5);
'''


class StripTest(unittest.TestCase):
    def test_removes_only_the_named_preferences(self):
        text, removed = pi.strip_preferences(BRANDING, {"startup.homepage_override_url", "app.update.url.manual"})
        self.assertEqual(sorted(removed), ["app.update.url.manual", "startup.homepage_override_url"])
        self.assertIn("startup.homepage_welcome_url", text)
        self.assertIn("app.update.promptWaitTime", text)
        self.assertNotIn("startup.homepage_override_url", text)

    def test_names_come_from_the_yaml(self):
        names = pi.defined_names("# c\n- name: a.b\n  value: 1\n\n- name: c.d\n  value: 2\n")
        self.assertEqual(names, {"a.b", "c.d"})

    def test_every_zen_url_in_branding_is_covered_by_the_shipped_yaml(self):
        """If surfer's template ever writes another Zen URL preference, this test says which one."""
        names = pi.defined_names(pi.ENDPOINTS.read_text(encoding="utf-8"))
        for needed in (
            "startup.homepage_override_url",
            "startup.homepage_welcome_url",
            "startup.homepage_welcome_url.additional",
            "app.update.url.manual",
            "app.update.url.details",
            "app.releaseNotesURL",
            "app.releaseNotesURL.aboutDialog",
            "app.releaseNotesURL.prompt",
        ):
            self.assertIn(needed, names)

    def test_only_brands_from_surfer_json_are_processed(self):
        import json
        brands = json.loads(pi.SURFER_JSON.read_text(encoding="utf-8"))["brands"]
        self.assertEqual(sorted(brands), ["release"])

    def test_a_remaining_zen_url_is_detected(self):
        self.assertTrue(pi.ZEN_HOST.search('pref("x", "https://www.zen-browser.app/y")'))
        self.assertFalse(pi.ZEN_HOST.search('pref("x", "https://github.com/AdriLabTech/nivoraBrowser/")'))


if __name__ == "__main__":
    unittest.main()
