#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Find Firefox's saturated illustration files that Nivora has not replaced yet.

Firefox ships its mascot (Kit, the fox) and many colorful illustrations as SVG files in the interface.
They are Mozilla's artwork and do not fit a monochrome identity. `generate_ui_artwork.py` replaces
the ones listed in its table and in `artwork_targets.json`. This script scans a Firefox source tree
for the rest, with a heuristic (an SVG of at least 2.5 KB with three or more saturated colors), skipping
files that are already replaced (symlinks into `src/`), test files and a short list of exclusions.

    python3 tools/nivora/scan_mozilla_artwork.py --engine engine            # list what is not covered
    python3 tools/nivora/scan_mozilla_artwork.py --engine engine --write    # add it to artwork_targets.json

Run it after every Firefox upgrade ([docs/UPSTREAM.md](../../docs/UPSTREAM.md)): new releases add new
illustrations.
"""

import argparse
import colorsys
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = HERE / "artwork_targets.json"
sys.path.insert(0, str(HERE))

ROOTS = ("toolkit/themes", "toolkit/content", "toolkit/components", "browser/themes", "browser/components", "browser/base/content")
MIN_BYTES = 2500
MIN_SATURATED = 3
HEX = re.compile(r"#([0-9a-fA-F]{6})\b")

# Files the heuristic flags that are not Mozilla's interface artwork, with the reason.
EXCLUDED = {
    "browser/components/topsites/content/tippytop/": "logos of third-party websites used as shortcut icons",
    "browser/themes/shared/urlbar/engine-wordmarks/": "the brand marks of the search engines, shown with their results",
    "browser/components/genai/assets/brands/": "logos of third-party chatbot services",
    "browser/themes/shared/weather/": "weather icons: information, not decoration",
    "browser/components/asrouter/docs/": "documentation images",
    "browser/themes/shared/preferences/thunderbird-color-16.svg": "a Mozilla product logo in a hidden pane (More from Mozilla)",
    "browser/themes/addons/": "previews of Firefox's built-in color themes",
    "toolkit/themes/shared/extensions/line.svg": "a decorative rule, no mascot",
}


def saturated_count(text):
    count = 0
    for value in set(HEX.findall(text)):
        r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
        _, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s > 0.6 and v > 0.5:
            count += 1
    return count


def _number(value):
    match = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*(px)?\s*", value or "")
    return float(match.group(1)) if match else None


def dimensions(text):
    """-> {"vw", "vh", "width", "height"} of an SVG's root element, or None if it cannot be read."""
    try:
        root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", text))
    except ET.ParseError:
        return None
    width, height = _number(root.get("width")), _number(root.get("height"))
    box = root.get("viewBox")
    if box:
        parts = [float(p) for p in re.split(r"[ ,]+", box.strip())]
        vw, vh = parts[2], parts[3]
    elif width and height:
        vw, vh = width, height
    else:
        return None

    def fmt(x):
        return None if x is None else (int(x) if x == int(x) else round(x, 3))

    return {"vw": fmt(vw), "vh": fmt(vh), "width": fmt(width), "height": fmt(height)}


def is_candidate(relative, text):
    if any(relative.startswith(prefix) for prefix in EXCLUDED):
        return False
    return len(text) >= MIN_BYTES and saturated_count(text) >= MIN_SATURATED


def scan(engine, covered):
    """-> sorted list of {"path", **dimensions} for uncovered candidates in the tree at `engine`."""
    found = []
    for root in ROOTS:
        for directory, _, files in os.walk(engine / root):
            if "/test" in directory or "node_modules" in directory:
                continue
            for name in files:
                path = Path(directory) / name
                relative = str(path.relative_to(engine))
                if not name.endswith(".svg") or path.is_symlink() or relative in covered:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if not is_candidate(relative, text):
                    continue
                dims = dimensions(text)
                if dims:
                    found.append({"path": relative, **dims})
    return sorted(found, key=lambda entry: entry["path"])


def covered_paths():
    import generate_ui_artwork as art

    listed = {entry["path"] for entry in json.loads(TARGETS.read_text())} if TARGETS.exists() else set()
    return set(art.ARTWORK) | listed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--write", action="store_true", help="add what is found to artwork_targets.json")
    args = parser.parse_args(argv)
    found = scan(args.engine.resolve(), covered_paths())
    for entry in found:
        print(entry["path"])
    print(f"{len(found)} uncovered candidate(s)")
    if args.write and found:
        existing = json.loads(TARGETS.read_text()) if TARGETS.exists() else []
        merged = sorted(existing + found, key=lambda entry: entry["path"])
        TARGETS.write_text(json.dumps(merged, indent=1) + "\n")
        print(f"wrote {len(merged)} entries to {TARGETS}")
    return 1 if found and not args.write else 0


if __name__ == "__main__":
    sys.exit(main())
