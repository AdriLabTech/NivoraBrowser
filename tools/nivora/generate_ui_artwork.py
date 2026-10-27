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

# Path in the Firefox tree -> (kind, width, height, fill). `fill` None means "the context's fill color".
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


def emblem(width, height):
    """The eclipse mark without its plate, centered, using the grid of generate_branding."""
    scale = 0.8 * min(width, height) / 700
    ox, oy = width / 2 - 512 * scale, height / 2 - 512 * scale
    disc, occ, ring = gb.DISC, gb.OCCLUDER, gb.RING
    return (
        f'{LICENSE}<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none">\n'
        f'  <g transform="translate({_num(ox)} {_num(oy)}) scale({_num(scale)})">\n'
        '    <mask id="eclipse"><rect width="1024" height="1024" fill="#fff"/>'
        f'<circle cx="{occ["cx"]}" cy="{occ["cy"]}" r="{occ["r"]}" fill="#000"/></mask>\n'
        f'    <circle cx="{ring["cx"]}" cy="{ring["cy"]}" r="{ring["r"]}" stroke="{gb.color("text-muted")}" '
        f'stroke-width="{ring["width"]}"/>\n'
        f'    <circle cx="{disc["cx"]}" cy="{disc["cy"]}" r="{disc["r"]}" fill="{gb.color("text-primary")}" '
        'mask="url(#eclipse)"/>\n'
        "  </g>\n"
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


def build():
    """-> {path in the Firefox tree: file content}"""
    files = {}
    for path, (kind, width, height, fill) in ARTWORK.items():
        files[path] = glyph(width, height, fill) if kind == "glyph" else emblem(width, height)
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
    print(f"wrote {len(ARTWORK) + len(PREVIEWS)} files under {args.src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
