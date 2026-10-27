#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Validate the Obsidian Eclipse palette against WCAG 2.x contrast minimums.

The palette lives in src/nivora/theme/nivora-tokens.inc.css, which is the only
place where colors are written. This script reads it, resolves the semantic
roles (`--nivora-text-primary: var(--nivora-white-100)`), and checks every pair
listed in tools/nivora/contrast-pairs.json.

Usage: check_contrast.py [--tokens PATH] [--pairs PATH] [--list]
Exit status: 0 when every pair passes, 1 when a pair fails, 2 on malformed input.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOKENS = ROOT / "src" / "nivora" / "theme" / "nivora-tokens.inc.css"
DEFAULT_PAIRS = Path(__file__).resolve().parent / "contrast-pairs.json"

DECLARATION = re.compile(r"--nivora-([a-z0-9-]+)\s*:\s*([^;]+);")
HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{6})$")
VAR_REFERENCE = re.compile(r"^var\(--nivora-([a-z0-9-]+)\)$")
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# A flat `@media (...) { --nivora-x: y; }` block. Its declarations override a base declaration for a
# condition (motion is zeroed when the user asks for reduced motion), so they are not a second
# definition of the token. Colors are never overridden this way.
MEDIA_BLOCK = re.compile(r"@media[^{;]*\{[^{}]*\}")


class TokenError(Exception):
    pass


def parse_tokens(css):
    """Return {name: raw value} for every base `--nivora-*` declaration (not those inside @media)."""
    tokens = {}
    for name, value in DECLARATION.findall(MEDIA_BLOCK.sub("", COMMENT.sub("", css))):
        value = value.strip()
        if name in tokens and tokens[name] != value:
            raise TokenError(f"--nivora-{name} is declared twice with different values")
        tokens[name] = value
    return tokens


def resolve(name, tokens, seen=()):
    """Resolve a token to a '#rrggbb' string, following var() references."""
    if name in seen:
        raise TokenError(f"--nivora-{name}: circular reference ({' -> '.join(seen)})")
    if name not in tokens:
        raise TokenError(f"--nivora-{name} is not defined")
    value = tokens[name]
    reference = VAR_REFERENCE.match(value)
    if reference:
        return resolve(reference.group(1), tokens, seen + (name,))
    if not HEX_COLOR.match(value):
        raise TokenError(f"--nivora-{name}: '{value}' is not a #rrggbb color or a var() reference")
    return value.lower()


def channel(value):
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(color):
    red, green, blue = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast_ratio(first, second):
    bright, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def check(tokens, spec):
    """Return a list of (fg, bg, ratio, minimum, ok, note) rows."""
    surfaces = spec["surfaces"]
    rows = []
    for pair in spec["pairs"]:
        backgrounds = surfaces if pair["on"] == "surfaces" else [pair["on"]]
        foreground = resolve(pair["fg"], tokens)
        for background_name in backgrounds:
            ratio = contrast_ratio(foreground, resolve(background_name, tokens))
            rows.append(
                (pair["fg"], background_name, ratio, pair["min"], ratio >= pair["min"], pair.get("note", ""))
            )
    for name in spec.get("decorative", []):
        resolve(name, tokens)  # must at least exist and be a valid color
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tokens", type=Path, default=DEFAULT_TOKENS)
    parser.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--list", action="store_true", help="print every checked pair")
    args = parser.parse_args(argv)

    try:
        tokens = parse_tokens(args.tokens.read_text(encoding="utf-8"))
        spec = json.loads(args.pairs.read_text(encoding="utf-8"))
        rows = check(tokens, spec)
    except (OSError, json.JSONDecodeError, KeyError, TokenError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    failures = [row for row in rows if not row[4]]
    for fg, bg, ratio, minimum, ok, note in rows:
        if args.list or not ok:
            status = "ok  " if ok else "FAIL"
            print(f"{status} {fg:<15} on {bg:<15} {ratio:6.2f}:1 (min {minimum:.1f})  {note}")
    print(f"{len(rows) - len(failures)}/{len(rows)} pairs pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
