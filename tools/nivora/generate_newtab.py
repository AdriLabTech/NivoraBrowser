#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Generate the default background of Nivora's new tab.

A total eclipse: a black disc on an obsidian field with a soft corona around its rim and one thin ring
further out, and the whole image darkening toward the edges so the command palette, which opens in the
middle of it, keeps its contrast. It uses only the neutral palette (src/nivora/theme/nivora-tokens.inc.css),
and the geometry is original. A one-level noise dither keeps the long dark gradients from banding on an
8-bit display.

Usage: generate_newtab.py [--out FILE] [--width N]
       (default: src/nivora/theme/images/nivora-newtab.webp, 2560 wide, 16:9, and next to it nivora-newtab-glass.webp,
       the same picture blurred, 1280 wide)
Requires Pillow.
"""

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import check_contrast as cc  # noqa: E402

TOKENS = ROOT / "src" / "nivora" / "theme" / "nivora-tokens.inc.css"
DEFAULT_OUT = ROOT / "src" / "nivora" / "theme" / "images" / "nivora-newtab.webp"
# The same picture, blurred. The command palette over the new tab and the cards of the settings page use it as
# the "glass": the browser cannot blur the page behind a surface (see docs/ANIMATIONS.md section 10), but the
# picture is ours, so a surface can show its own blurred copy, aligned with the original.
GLASS_OUT = DEFAULT_OUT.with_name("nivora-newtab-glass.webp")
def lut(fn):
    """A 256-entry table from a function of the normalised value 0..1 to 0..255."""
    return [max(0, min(255, round(255 * fn(i / 255)))) for i in range(256)]


def radial(size, radius):
    """An 'L' image of `size` whose value is the distance from its centre in units of `radius`, 0..255 (clipped)."""
    side = max(2, round(radius * 2))
    disc = Image.radial_gradient("L").resize((side, side), Image.BICUBIC)
    canvas = Image.new("L", size, 255)
    canvas.paste(disc, ((size[0] - side) // 2, (size[1] - side) // 2))
    return canvas


def light_at(d):
    """How bright the sky is at `d` disc radii from the centre of the eclipse, 0..1."""
    d = max(d, 1.0)
    # Every term fades to 0 before 4 radii, so nothing ends in a visible border.
    edge = max(0.0, 1 - (d / 4) ** 2) ** 2
    corona = 0.62 * math.exp(-(d - 1) / 0.42)  # strongest at the rim, falls off quickly
    halo = 0.3 * math.exp(-(d - 1) / 1.2)  # wider and much fainter, so the glow has depth
    ring = 0.15 * math.exp(-(((d - 2.1) / 0.018) ** 2))  # one thin ring, the "corona ring" of the application icon
    return min(1.0, (corona + halo) * edge + ring)


def render(width):
    tokens = cc.parse_tokens(TOKENS.read_text(encoding="utf-8"))
    color = lambda name: cc.resolve(name, tokens)  # noqa: E731
    height = round(width * 9 / 16)
    cx, cy = width / 2, height * 0.46
    disc_r = height * 0.19

    # The sky is drawn as concentric one-pixel rings, from the outside in, at the final size: the brightness
    # is a smooth function of the distance, with none of the steps a lookup table of the distance would leave.
    light = Image.new("L", (width, height), 0)
    pen = ImageDraw.Draw(light)
    for r in range(int(disc_r * 4), 0, -1):
        pen.ellipse([cx - r, cy - r, cx + r, cy + r], fill=round(255 * light_at(r / disc_r)))

    base = Image.new("RGB", (width, height), color("obsidian-950"))
    # Light on the field: from the quiet graphite to the bright rim, never pure white.
    lit = ImageOps.colorize(
        light, black=color("obsidian-950"), mid=color("graphite-700"), white=color("white-100"), midpoint=96
    )
    # The disc is drawn twice as large and scaled down, so its rim is smooth. It is the darkest thing.
    ss = 2
    disc = Image.new("L", (width * ss, height * ss), 0)
    ImageDraw.Draw(disc).ellipse(
        [(cx - disc_r) * ss, (cy - disc_r) * ss, (cx + disc_r) * ss, (cy + disc_r) * ss], fill=255
    )
    disc = disc.resize((width, height), Image.LANCZOS)
    out = Image.composite(base, lit, disc)

    # Vignette: the corners fall to the base colour. A slow gradient, drawn small and scaled up.
    vw, vh = width // 4, height // 4
    vig = radial((vw, vh), vh * 1.15).point(lut(lambda v: 0.85 * min(1.0, max(0.0, v**2.2))))
    out = Image.composite(base, out, vig.resize((width, height), Image.BICUBIC))

    # One level of noise so the long dark ramps do not band.
    noise = Image.effect_noise((width, height), 5).convert("RGB")
    out = ImageChops.add(out, ImageChops.subtract(noise.point(lambda v: 127 + (v - 128) // 40), Image.new("RGB", (width, height), (127, 127, 127))))
    return out


def render_glass(width):
    """The picture, blurred hard and darker (it sits behind text), at `width` (it has no detail left, so it can be small)."""
    image = render(width)
    return ImageEnhance.Brightness(image.filter(ImageFilter.GaussianBlur(width * 0.014))).enhance(0.7)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--width", type=int, default=2560)
    args = parser.parse_args(argv)
    image = render(args.width)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out, "WEBP", quality=88, method=6)
    print(f"wrote {args.out} ({image.size[0]}x{image.size[1]}, {args.out.stat().st_size // 1024} KiB)")
    glass = render_glass(1280)
    glass_out = args.out.with_name(GLASS_OUT.name)
    glass.save(glass_out, "WEBP", quality=90, method=6)
    print(f"wrote {glass_out} ({glass.size[0]}x{glass.size[1]}, {glass_out.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
