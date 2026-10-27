#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Take screenshots of the built browser for the visual review (docs/TESTING.md, section 3.2).

Each scenario starts the browser with an empty home directory, opens a page, optionally types into
the address bar (to show the command palette), waits and saves one PNG. Screenshots are evidence
for a person to look at; nothing here judges them. Needs Xvfb, xdotool and ImageMagick's `import`.

Usage: screenshots.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR [--only NAME ...]
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# name -> (url the browser is started with, text typed in the address bar, press Enter?, seconds to wait).
# Zen replaces some start pages with its own new tab, so pages are reached by typing, as a person would.
SCENARIOS = {
    "newtab": ("about:blank", None, False, 8),
    "preferences": ("about:blank", "about:preferences", True, 10),
    "preferences-zen": ("about:blank", "about:preferences#zenLooks", True, 10),
    "about-dialog-page": ("about:blank", "about:about", True, 8),
    "downloads": ("about:blank", "about:downloads", True, 8),
    "policies": ("about:blank", "about:policies", True, 8),
    "support": ("about:blank", "about:support", True, 10),
    "palette-nivora": ("about:blank", "nivora", False, 6),
    "palette-tabs": ("about:blank", "tab", False, 6),
    "palette-settings": ("about:blank", "settings", False, 6),
}


def shot(binary, out, name, url, typed, submit, wait, display):
    home = Path(tempfile.mkdtemp(prefix="nivora-shot-home-"))
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    browser = subprocess.Popen([str(binary), "--no-remote", url], env=env, cwd=home,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(wait)
        if typed:
            subprocess.run(["xdotool", "key", "ctrl+l"], env=env, timeout=30)
            time.sleep(1)
            subprocess.run(["xdotool", "type", "--delay", "80", typed], env=env, timeout=30)
            if submit:
                subprocess.run(["xdotool", "key", "Return"], env=env, timeout=30)
            time.sleep(4)
        subprocess.run(["import", "-window", "root", str(out / f"{name}.png")], env=env, timeout=60, check=True)
    finally:
        if browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
        shutil.rmtree(home, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only", nargs="*", choices=sorted(SCENARIOS))
    parser.add_argument("--display", default=":96")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    for tool in ("Xvfb", "xdotool", "import"):
        if not shutil.which(tool):
            print(f"error: {tool} is required", file=sys.stderr)
            return 2
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1400x900x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failed = 0
    try:
        time.sleep(2)
        for name in args.only or SCENARIOS:
            url, typed, submit, wait = SCENARIOS[name]
            try:
                shot(binary, out, name, url, typed, submit, wait, args.display)
                print(f"saved {out / (name + '.png')}")
            except Exception as e:  # keep going: one failing scenario should not hide the others
                failed += 1
                print(f"FAILED {name}: {e}", file=sys.stderr)
    finally:
        xvfb.terminate()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
