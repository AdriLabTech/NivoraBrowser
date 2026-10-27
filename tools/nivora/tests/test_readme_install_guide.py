# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The Arch install guide in README.md must keep naming things that exist."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = (ROOT / "README.md").read_text(encoding="utf-8")
PKGBUILD = (ROOT / "packaging" / "arch" / "PKGBUILD").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "nivora-build-linux.yml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "tools" / "nivora" / "build_linux.sh").read_text(encoding="utf-8")


def guide():
    start = README.index("## Install on Arch Linux and Ryoku Arch")
    return README[start:README.index("\n## ", start + 5)]


def pkgbuild_value(name):
    return re.search(rf"^{name}=(.+)$", PKGBUILD, re.MULTILINE).group(1).strip("\"'")


class GuideTest(unittest.TestCase):
    def test_every_repository_path_in_the_guide_exists(self):
        for path in set(re.findall(r"\(((?:tools|packaging|docs)/[^)#\s]+)\)", guide())):
            self.assertTrue((ROOT / path).exists(), path)
        for path in set(re.findall(r"`((?:tools|packaging)/[\w./-]+)`", guide())):
            self.assertTrue((ROOT / path).exists(), path)

    def test_the_script_options_the_guide_uses_are_options_of_the_script(self):
        used = set(re.findall(r"build_linux\.sh ((?:--[\w-]+ ?)+)", guide()))
        self.assertTrue(used)
        for options in used:
            for option in options.split():
                self.assertIn(f"{option})", SCRIPT, option)

    def test_the_artifact_and_workflow_names_are_the_real_ones(self):
        self.assertIn("name: nivora-arch-package", WORKFLOW)
        self.assertIn("nivora-arch-package", guide())
        self.assertIn("nivora-build-linux.yml", guide())
        self.assertTrue((ROOT / ".github" / "workflows" / "nivora-build-linux.yml").is_file())

    def test_the_package_name_and_version_match_the_pkgbuild(self):
        name, version, rel = pkgbuild_value("pkgname"), pkgbuild_value("pkgver"), pkgbuild_value("pkgrel")
        self.assertIn(f"{name}-{version}-{rel}-x86_64.pkg.tar.zst", guide())
        self.assertIn(f"sudo pacman -Rns {name}", guide())
        self.assertIn(f"pacman -Qi {name}", guide())

    def test_the_desktop_file_the_guide_names_is_the_packaged_one(self):
        self.assertIn("nivora.desktop", guide())
        self.assertTrue((ROOT / "packaging" / "linux" / "nivora.desktop").is_file())

    def test_the_guide_says_what_was_and_was_not_tested(self):
        text = " ".join(guide().split())
        self.assertIn("Not tested: any other real Arch or Ryoku Arch system", text)
        self.assertIn("the owner installed the package", text)
        self.assertIn("were not recorded", text)

    def test_the_guide_is_only_about_this_project_branch_and_repository(self):
        self.assertIn("github.com/AdriLabTech/nivoraBrowser", guide())
        self.assertNotIn("zen-browser.app", guide())


if __name__ == "__main__":
    unittest.main()
