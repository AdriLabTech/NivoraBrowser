#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fix what `surfer import` writes that Nivora cannot configure any other way.

`surfer import` generates browser/branding/<brand>/pref/firefox-branding.js with URLs hardcoded in
the surfer package (welcome page, "what's new" tab, release notes, manual update page), all pointing
at zen-browser.app. That file is read *after* the preference files compiled from prefs/*.yaml, so
overriding those preferences in prefs/nivora/endpoints.yaml does not work (observed in a browser
test: the defaults were still Zen's). This script removes from the generated file every preference
that prefs/nivora/endpoints.yaml defines, so the yaml is the only definition, and then checks that no
reference to zen-browser.app is left.

Run from the repository root after `surfer import` (`npm run import` does it).
Exit status: 0 ok, 1 a Zen URL is still present, 2 files not found.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = ROOT / "prefs" / "nivora" / "endpoints.yaml"
ENGINE_BRANDING = ROOT / "engine" / "browser" / "branding"
SURFER_JSON = ROOT / "surfer.json"

NAME = re.compile(r"^- name:\s*(\S+)\s*$", re.MULTILINE)
ZEN_HOST = re.compile(r"zen-browser\.(app|github\.io)")


def defined_names(yaml_text):
    return set(NAME.findall(yaml_text))


def strip_preferences(js_text, names):
    """Return (new text, removed names). Only whole `pref("name", ...);` statements are removed."""
    removed = []
    kept = []
    for line in js_text.splitlines(keepends=True):
        match = re.match(r'^\s*pref\("([^"]+)"', line)
        if match and match.group(1) in names:
            removed.append(match.group(1))
            continue
        kept.append(line)
    return "".join(kept), removed


def main(argv=None):
    if not ENDPOINTS.is_file():
        print(f"error: {ENDPOINTS} not found", file=sys.stderr)
        return 2
    names = defined_names(ENDPOINTS.read_text(encoding="utf-8"))
    # Only the brands surfer generates from this repository (the keys of "brands" in surfer.json);
    # Mozilla's own brandings in the engine are none of our business.
    brands = sorted(json.loads(SURFER_JSON.read_text(encoding="utf-8"))["brands"])
    files = [ENGINE_BRANDING / brand / "pref" / "firefox-branding.js" for brand in brands]
    files = [path for path in files if path.is_file()]
    if not files:
        print(f"error: no generated firefox-branding.js for {brands} under {ENGINE_BRANDING} (run surfer import first)", file=sys.stderr)
        return 2
    status = 0
    for path in files:
        text, removed = strip_preferences(path.read_text(encoding="utf-8"), names)
        path.write_text(text, encoding="utf-8")
        left = [line.strip() for line in text.splitlines() if ZEN_HOST.search(line) and not line.lstrip().startswith("//")]
        print(f"{path.relative_to(ROOT)}: removed {len(removed)} preference(s); {len(left)} Zen URL(s) left")
        for line in left:
            print(f"  still present: {line}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
