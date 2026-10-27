#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Replace Firefox's logo and mascot artwork inside the interface with Nivora's mark.

Firefox draws its logo (the "About" entry in settings, the window and share icons) and its
mascot, Kit, in several places of the interface. Those are Mozilla trademarks and have no place in
Nivora. `surfer import` replaces a Firefox file with a file of the same path under `src/`, so this
script writes the replacements there, with the same dimensions so no layout changes.

Glyphs (the logo) become a flat eclipse; illustrations (the mascot) become the eclipse mark of
`generate_branding.py`, drawn from the same tokens. The three window-layout previews of the
Look and Feel pane (Zen's screenshots, with Zen's name and a stock wallpaper in them) become
schematic drawings in the palette. Everything is derived from
src/nivora/theme/nivora-tokens.inc.css.

    python3 tools/nivora/generate_ui_artwork.py            # write
    python3 tools/nivora/generate_ui_artwork.py --check    # exit 1 if src/ differs from the generator
"""

import argparse
import io
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import generate_branding as gb  # noqa: E402

LICENSE = (
    "<!-- This Source Code Form is subject to the terms of the Mozilla Public\n"
    "   - License, v. 2.0. If a copy of the MPL was not distributed with this\n"
    "   - file, You can obtain one at http://mozilla.org/MPL/2.0/. -->\n"
)

# Path in the Firefox tree -> (kind, width, height, fill[, display_height]). `fill` None means "the
# context's fill color". Width and height are those of the viewBox; `display_height` is for files whose
# original carried only a `height` attribute (the width then follows from the viewBox).
ARTWORK = {
    # Firefox logo
    "browser/themes/shared/sidebar/firefox.svg": ("glyph", 26, 26, None),
    "browser/themes/shared/icons/window-firefox.svg": ("glyph", 16, 14, None),
    "browser/themes/shared/fxa/avatar-fox.svg": ("glyph", 16, 16, None),
    "browser/base/content/logos/share-firefox.svg": ("glyph", 16, 16, "text-secondary"),
    # Kit, the mascot
    "toolkit/themes/shared/illustrations/kit-concerned.svg": ("emblem", 50, 40, None),
    "toolkit/themes/shared/illustrations/kit-confetti.svg": ("emblem", 80, 60, None),
    "toolkit/themes/shared/illustrations/kit-happy.svg": ("emblem", 50, 40, None),
    "toolkit/themes/shared/illustrations/kit-holding-lock.svg": ("emblem", 80, 100, None),
    "toolkit/themes/shared/illustrations/kit-in-circle.svg": ("emblem", 120, 120, None),
    "toolkit/themes/shared/illustrations/kit-sympathetic.svg": ("emblem", 250, 250, None),
    "browser/themes/shared/preferences/fox-ai.svg": ("emblem", 62, 63, None),
    "browser/themes/shared/sidebar/foxy.svg": ("emblem", 52, 64, None),
    "browser/themes/shared/fxa/avatar-fox-circle.svg": ("glyph", 16, 16, None),
    "browser/themes/shared/privatebrowsing/fox-tail.svg": ("corona", 1398, 840, None),
    "browser/components/asrouter/content/assets/smiling-fox-icon.svg": ("emblem", 22, 22, None),
    "browser/components/asrouter/content/assets/fox-with-devices.svg": ("emblem", 216, 164, None, 96),
    "browser/components/asrouter/content/assets/fox-with-locked-box.svg": ("emblem", 206, 216, None, 96),
    "browser/components/asrouter/content/assets/fox-with-checkmark.svg": ("emblem", 106, 97, None),
    "browser/components/asrouter/content/assets/fox-with-box-on-cloud.svg": ("emblem", 216, 185, None, 96),
    "browser/components/asrouter/content/assets/fox-with-mobile.svg": ("emblem", 158, 98, None, 96),
    "browser/components/asrouter/content/assets/fox-with-profiles.svg": ("emblem", 352, 215, None),
    "browser/components/controlcenter/content/assets/fox-concern.svg": ("emblem", 72, 76, None),
}


def _num(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def glyph(width, height, fill):
    """A disc with an offset hole: a thick crescent, readable at 14 px. One path, even-odd."""
    cx, cy = width / 2, height / 2
    r = min(width, height) * 0.46
    hr, dx, dy = r * 0.74, r * 0.15, -r * 0.15

    def circle(x, y, radius):
        return (f"M{_num(x - radius)} {_num(y)}a{_num(radius)} {_num(radius)} 0 1 0 {_num(2 * radius)} 0"
                f"a{_num(radius)} {_num(radius)} 0 1 0 {_num(-2 * radius)} 0Z")

    paint = f'fill="{gb.color(fill)}"' if fill else 'fill="context-fill" fill-opacity="context-fill-opacity"'
    return (
        f'{LICENSE}<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" {paint}>\n'
        f'  <path fill-rule="evenodd" d="{circle(cx, cy, r)}{circle(cx + dx, cy + dy, hr)}"/>\n'
        "</svg>\n"
    )


def crescent_path():
    """The bright disc minus the dark occluder of the mark, as one closed path on the 1024 grid.

    A path rather than a mask: an SVG that uses <mask> drew nothing when shown as an <img> in the network
    error page of the built browser, and a plain path is cheaper to draw as well.
    """
    (x1, y1, r1), (x2, y2, r2) = [(c["cx"], c["cy"], c["r"]) for c in (gb.DISC, gb.OCCLUDER)]
    d = math.hypot(x2 - x1, y2 - y1)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(r1 * r1 - a * a)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    mx, my = x1 + a * ux, y1 + a * uy
    p1 = (mx + h * uy, my - h * ux)
    p2 = (mx - h * uy, my + h * ux)
    # Outer edge: the long way round the disc, away from the occluder; inner edge: the occluder's arc back.
    return (f"M{_num(p1[0])} {_num(p1[1])}A{r1} {r1} 0 1 0 {_num(p2[0])} {_num(p2[1])}"
            f"A{r2} {r2} 0 0 1 {_num(p1[0])} {_num(p1[1])}Z")


def emblem(width, height, display_height=None, attrs=None):
    """The eclipse mark without its plate, centered, using the grid of generate_branding.

    `width` and `height` are those of the viewBox. The size attributes follow the original file:
    both by default, only the height when `display_height` is given, and exactly `attrs` (a dict,
    possibly empty) when that is given.
    """
    scale = 0.8 * min(width, height) / 700
    ox, oy = width / 2 - 512 * scale, height / 2 - 512 * scale
    disc, occ, ring = gb.DISC, gb.OCCLUDER, gb.RING
    if attrs is not None:
        size = " ".join(f'{k}="{v}"' for k, v in attrs.items() if v is not None)
    elif display_height:
        size = f'height="{display_height}"'
    else:
        size = f'width="{width}" height="{height}"'
    size = (size + " ") if size else ""
    return (
        f'{LICENSE}<svg xmlns="http://www.w3.org/2000/svg" {size}'
        f'viewBox="0 0 {width} {height}" fill="none">\n'
        f'  <g transform="translate({_num(ox)} {_num(oy)}) scale({_num(scale)})">\n'
        f'    <circle cx="{ring["cx"]}" cy="{ring["cy"]}" r="{ring["r"]}" stroke="{gb.color("text-muted")}" '
        f'stroke-width="{ring["width"]}"/>\n'
        f'    <path fill="{gb.color("text-primary")}" d="{crescent_path()}"/>\n'
        "  </g>\n"
        "</svg>\n"
    )


def corona(width, height):
    """A quiet decoration for the corner of a page: the corona ring and the dark disc, mostly off the page."""
    cx, cy = width, height
    outer, inner = 0.5 * width, 0.34 * width
    return (
        f'{LICENSE}<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none">\n'
        f'  <circle cx="{cx}" cy="{cy}" r="{_num(outer)}" stroke="{gb.color("separator")}" stroke-width="6"/>\n'
        f'  <circle cx="{cx}" cy="{cy}" r="{_num(inner)}" fill="{gb.color("surface-raised")}" '
        f'stroke="{gb.color("separator-strong")}" stroke-width="4"/>\n'
        "</svg>\n"
    )


PREVIEW_SIZE = (822, 571)
PREVIEWS = {
    "zen/images/layouts/single-toolbar.png": "sidebar",
    "zen/images/layouts/multiple-toolbar.png": "sidebar-and-toolbar",
    "zen/images/layouts/collapsed.png": "collapsed",
}


def preview(layout):
    """A schematic window for the Look and Feel pane: the palette, no screenshot, no text."""
    scale = 2
    width, height = (n * scale for n in PREVIEW_SIZE)
    image = Image.new("RGB", (width, height), gb.color("surface-base"))
    draw = ImageDraw.Draw(image)

    def box(x0, y0, x1, y1, fill, radius=14):
        draw.rounded_rectangle([x0 * scale, y0 * scale, x1 * scale, y1 * scale], radius=radius * scale, fill=fill)

    w, h = PREVIEW_SIZE
    surface, raised, line = gb.color("surface-2"), gb.color("surface-raised"), gb.color("separator-strong")
    page, text = gb.color("text-primary"), gb.color("text-muted")
    pad = 20
    if layout == "collapsed":
        side = 64
        box(pad, pad, pad + side, h - pad, surface)
        for i in range(5):
            box(pad + 16, pad + 24 + i * 44, pad + side - 16, pad + 52 + i * 44, line if i == 1 else raised, 8)
        box(pad + side + 14, pad, w - pad, pad + 56, surface)
        box(pad + side + 30, pad + 12, w - pad - 16, pad + 44, raised, 10)
        box(pad + side + 14, pad + 70, w - pad, h - pad, page)
    else:
        side = 230
        box(pad, pad, pad + side, h - pad, surface)
        box(pad + 14, pad + 14, pad + side - 14, pad + 56, raised, 10)
        for i in range(5):
            box(pad + 14, pad + 84 + i * 50, pad + side - 14, pad + 122 + i * 50, line if i == 1 else raised, 10)
            box(pad + 26, pad + 96 + i * 50, pad + 52, pad + 110 + i * 50, text, 4)
        top = pad
        if layout == "sidebar-and-toolbar":
            box(pad + side + 14, pad, w - pad, pad + 56, surface)
            box(pad + side + 30, pad + 12, w - pad - 16, pad + 44, raised, 10)
            top = pad + 70
        box(pad + side + 14, top, w - pad, h - pad, page)
    return image.resize(PREVIEW_SIZE, Image.LANCZOS)


def preview_bytes(layout):
    buffer = io.BytesIO()
    preview(layout).save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


TARGETS = HERE / "artwork_targets.json"


def scanned_targets():
    """The illustrations found by scan_mozilla_artwork.py: [{path, vw, vh, width, height}]."""
    return json.loads(TARGETS.read_text(encoding="utf-8")) if TARGETS.exists() else []


def build():
    """-> {path in the Firefox tree: file content}"""
    files = {}
    for entry in scanned_targets():
        if entry["path"] not in ARTWORK:
            files[entry["path"]] = emblem(entry["vw"], entry["vh"], attrs={"width": entry["width"], "height": entry["height"]})
    for path, (kind, width, height, fill, *rest) in ARTWORK.items():
        if kind == "glyph":
            files[path] = glyph(width, height, fill)
        elif kind == "corona":
            files[path] = corona(width, height)
        else:
            files[path] = emblem(width, height, *rest)
    return files


def same_image(a, b):
    """Pixel equality: the encoded bytes of a PNG depend on the PIL and zlib versions."""
    first, second = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    return first.size == second.size and first.tobytes() == second.tobytes()


def build_previews():
    """-> {path under src/: PNG bytes}"""
    return {path: preview_bytes(layout) for path, layout in PREVIEWS.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--src", type=Path, default=ROOT / "src")
    args = parser.parse_args(argv)
    stale = []
    for path, content in build().items():
        target = args.src / path
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                stale.append(path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    for path, data in build_previews().items():
        target = args.src / path
        if args.check:
            if not target.is_file() or not same_image(target.read_bytes(), data):
                stale.append(path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if args.check:
        for path in stale:
            print(f"stale or missing: {path}")
        print("OK" if not stale else f"{len(stale)} file(s) differ; run without --check")
        return 1 if stale else 0
    print(f"wrote {len(build()) + len(PREVIEWS)} files under {args.src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
