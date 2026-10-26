#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Generate Nivora's application icons from one geometric definition.

The mark is an eclipse: a bright disc partly covered by a dark disc, leaving a crescent, inside
a thin corona ring, on a dark rounded plate. Small sizes drop the ring so the crescent stays
legible. Colors come from the design tokens (src/nivora/theme/nivora-tokens.inc.css), so the icon
cannot drift from the palette. The geometry is original; nothing is traced or copied from another
project. It is a proposal: replace it by changing this file's geometry and re-running it.

Usage: generate_branding.py [--out DIR]   (default: configs/branding/release)
Requires Pillow.
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import check_contrast as cc  # noqa: E402

TOKENS = cc.parse_tokens((ROOT / "src/nivora/theme/nivora-tokens.inc.css").read_text(encoding="utf-8"))


def color(name):
    return cc.resolve(name, TOKENS)


# Geometry on a 1024 grid.
PLATE = {"inset": 64, "radius": 208, "stroke": 8}
DISC = {"cx": 512, "cy": 512, "r": 250}
OCCLUDER = {"cx": 592, "cy": 440, "r": 232}
RING = {"cx": 512, "cy": 512, "r": 330, "width": 12}
SUPERSAMPLE = 4
RING_MIN_SIZE = 48  # below this the ring is only noise


def svg(ring=True):
    """The master vector drawing."""
    side = 1024 - 2 * PLATE["inset"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">',
        "  <title>Nivora</title>",
        f'  <rect x="{PLATE["inset"]}" y="{PLATE["inset"]}" width="{side}" height="{side}" '
        f'rx="{PLATE["radius"]}" fill="{color("surface-base")}" '
        f'stroke="{color("separator")}" stroke-width="{PLATE["stroke"]}"/>',
    ]
    if ring:
        parts.append(
            f'  <circle cx="{RING["cx"]}" cy="{RING["cy"]}" r="{RING["r"]}" fill="none" '
            f'stroke="{color("text-muted")}" stroke-width="{RING["width"]}"/>'
        )
    parts.append(f'  <circle cx="{DISC["cx"]}" cy="{DISC["cy"]}" r="{DISC["r"]}" fill="{color("text-primary")}"/>')
    # The occluder is painted in the plate color, so it also trims the ring where they overlap.
    parts.append(
        f'  <circle cx="{OCCLUDER["cx"]}" cy="{OCCLUDER["cy"]}" r="{OCCLUDER["r"]}" fill="{color("surface-base")}"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _rgba(hex_color):
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


def render(size, ring=None):
    """Rasterise the mark at `size` px (square), with supersampled anti-aliasing."""
    if ring is None:
        ring = size >= RING_MIN_SIZE
    big = size * SUPERSAMPLE
    scale = big / 1024
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def circle(spec, fill=None, outline=None, width=0):
        box = [
            (spec["cx"] - spec["r"]) * scale,
            (spec["cy"] - spec["r"]) * scale,
            (spec["cx"] + spec["r"]) * scale,
            (spec["cy"] + spec["r"]) * scale,
        ]
        draw.ellipse(box, fill=fill, outline=outline, width=max(1, round(width * scale)))

    inset = PLATE["inset"] * scale
    draw.rounded_rectangle(
        [inset, inset, big - inset, big - inset],
        radius=PLATE["radius"] * scale,
        fill=_rgba(color("surface-base")),
        outline=_rgba(color("separator")),
        width=max(1, round(PLATE["stroke"] * scale)),
    )
    if ring:
        circle(RING, outline=_rgba(color("text-muted")), width=RING["width"])
    circle(DISC, fill=_rgba(color("text-primary")))
    circle(OCCLUDER, fill=_rgba(color("surface-base")))
    return image.resize((size, size), Image.LANCZOS)


def png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def wordmark_svg(fill):
    """A plain-text wordmark. It relies on the viewer's sans-serif font: a placeholder."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 160" width="560" height="160">\n'
        "  <title>Nivora</title>\n"
        f'  <text x="0" y="118" fill="{fill}" font-family="system-ui, sans-serif" font-size="128" '
        'font-weight="600" letter-spacing="2">Nivora</text>\n'
        "</svg>\n"
    )


ICO_SIZES = [(s, s) for s in (16, 32, 48, 64, 128, 256)]


def generate(out):
    """Write every branding file into `out`; return the list of file names written."""
    out = Path(out)
    (out / "content").mkdir(parents=True, exist_ok=True)
    written = []

    def write(name, data):
        path = out / name
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        written.append(name)

    for size in (16, 22, 24, 32, 48, 64, 128, 256, 512, 1024):
        write(f"logo{size}.png", png_bytes(render(size)))
    write("logo.png", png_bytes(render(1024)))
    write("logo-mac.png", png_bytes(render(1024)))

    for name in ("firefox.ico", "firefox64.ico", "pbmode.ico", "document.ico", "document_pdf.ico"):
        buffer = io.BytesIO()
        render(256).save(buffer, "ICO", sizes=ICO_SIZES)
        write(name, buffer.getvalue())

    for name, size in (
        ("PrivateBrowsing_70.png", 126),
        ("PrivateBrowsing_150.png", 270),
        ("VisualElements_70.png", 1024),
        ("VisualElements_150.png", 1024),
        ("content/about-logo.png", 512),
        ("content/about-logo@2x.png", 1024),
        ("content/about-logo-private.png", 192),
        ("content/about-logo-private@2x.png", 384),
    ):
        write(name, png_bytes(render(size)))

    write("nivora-mark.svg", svg())
    write("MacOSInstaller.svg", svg())
    write("content/about-logo.svg", svg())
    write("content/about-logo-private.svg", svg())
    write("content/about-wordmark.svg", wordmark_svg(color("text-primary")))
    write("content/firefox-wordmark.svg", wordmark_svg(color("text-primary")))

    # Windows installer side art: plain obsidian with the mark. Not used on Linux.
    watermark = Image.new("RGB", (164, 314), color("surface-base"))
    mark = render(120)
    watermark.paste(mark, (22, 97), mark)
    buffer = io.BytesIO()
    watermark.save(buffer, "BMP")
    write("wizWatermark.bmp", buffer.getvalue())
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "configs" / "branding" / "release")
    args = parser.parse_args(argv)
    written = generate(args.out)
    print(f"wrote {len(written)} files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
