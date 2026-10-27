#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Take screenshots of the built browser for the visual review (docs/TESTING.md, section 3.2).

Each scenario starts the browser with an empty home directory and a profile whose preferences it
sets, opens pages served from this machine, replays a few keyboard and mouse actions, waits and saves
one PNG. Screenshots are evidence for a person to look at; nothing here judges them. Needs Xvfb,
xdotool and ImageMagick's `import`.

A scenario may also set `prefs` (written to the profile's user.js) and `env`. Actions: ("key", "ctrl+l"), ("type", "text"), ("click", x, y), ("rclick", x, y), ("size", w, h),
("wait", seconds). A page is `/<name>`, served with that name as its title; `urls` are paths or
about: pages.

Usage: screenshots.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR [--only NAME ...]
"""

import argparse
import http.server
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PAGES = "/Alpha /Beta /Gamma /Delta".split()

TAB_KEYS = [("wait", 6), ("key", "ctrl+Tab"), ("wait", 1), ("key", "ctrl+shift+d"), ("wait", 2)]

SCENARIOS = {
    "newtab": {"urls": ["about:blank"], "actions": [("wait", 8)]},
    "preferences": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "about:preferences"), ("key", "Return"), ("wait", 8)]},
    "preferences-zen": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "about:preferences#zenLooks"), ("key", "Return"), ("wait", 8)]},
    "downloads": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "about:downloads"), ("key", "Return"), ("wait", 6)]},
    "policies": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "about:policies"), ("key", "Return"), ("wait", 6)]},
    "support": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "about:support"), ("key", "Return"), ("wait", 8)]},
    "palette-nivora": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "nivora"), ("wait", 4)]},
    "palette-tabs": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "tab"), ("wait", 4)]},
    "palette-settings": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+l"), ("type", "settings"), ("wait", 4)]},
    "tabs": {"urls": PAGES, "actions": TAB_KEYS},
    "tabs-hover": {"urls": PAGES, "actions": TAB_KEYS + [("move", 90, 206), ("wait", 2)]},
    "app-menu": {"urls": PAGES[:2], "actions": [("wait", 7), ("click", 18, 21), ("wait", 3)]},
    "tab-context-menu": {"urls": PAGES, "actions": [("wait", 7), ("rclick", 90, 206), ("wait", 3)]},
    "private-window": {"urls": ["about:blank"], "actions": [("wait", 8), ("key", "ctrl+shift+p"), ("wait", 8)]},
    "narrow": {"urls": PAGES[:2], "actions": [("wait", 7), ("size", 420, 700), ("wait", 4)]},
    "hidpi": {"urls": PAGES[:2], "env": {"GDK_SCALE": "2"}, "actions": [("wait", 9)]},
    "reduced-motion": {"urls": PAGES[:2], "prefs": {"ui.prefersReducedMotion": 1}, "actions": [("wait", 8)]},
    "light-scheme": {"urls": PAGES[:2], "prefs": {"zen.view.window.scheme": 1}, "actions": [("wait", 8)]},
}


class Pages(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.strip("/") or "page"
        body = f"<!doctype html><title>{name}</title><body style='font:20px sans-serif;padding:2em'><h1>{name}</h1>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def pref_line(name, value):
    if isinstance(value, str):
        value = f'"{value}"' if not value.replace(".", "", 1).isdigit() else value
    return f"user_pref(\"{name}\", {str(value).lower() if isinstance(value, bool) else value});"


def act(env, display, pid, action):
    kind = action[0]
    if kind == "wait":
        time.sleep(action[1])
    elif kind == "key":
        subprocess.run(["xdotool", "key", action[1]], env=env, timeout=30)
    elif kind == "type":
        subprocess.run(["xdotool", "type", "--delay", "70", action[1]], env=env, timeout=60)
    elif kind in ("click", "rclick", "move"):
        subprocess.run(["xdotool", "mousemove", str(action[1]), str(action[2])], env=env, timeout=30)
        if kind != "move":
            subprocess.run(["xdotool", "click", "1" if kind == "click" else "3"], env=env, timeout=30)
    elif kind == "size":
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(pid)], env=env,
                               capture_output=True, text=True, timeout=30).stdout.split()
        for window in found:
            subprocess.run(["xdotool", "windowsize", window, str(action[1]), str(action[2])], env=env, timeout=30)


def shot(binary, out, name, scenario, port, display):
    home = Path(tempfile.mkdtemp(prefix="nivora-shot-home-"))
    profile = home / "profile"
    profile.mkdir()
    prefs = scenario.get("prefs", {})
    (profile / "user.js").write_text("".join(pref_line(k, v) + "\n" for k, v in prefs.items()))
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"), **scenario.get("env", {})}
    urls = [u if u.startswith("about:") else f"http://127.0.0.1:{port}{u}" for u in scenario["urls"]]
    browser = subprocess.Popen([str(binary), "--no-remote", "--profile", str(profile), *urls], env=env, cwd=home,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for action in scenario["actions"]:
            act(env, display, browser.pid, action)
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
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1400x900x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failed = 0
    try:
        time.sleep(2)
        for name in args.only or SCENARIOS:
            try:
                shot(binary, out, name, SCENARIOS[name], server.server_address[1], args.display)
                print(f"saved {out / (name + '.png')}")
            except Exception as e:  # keep going: one failing scenario should not hide the others
                failed += 1
                print(f"FAILED {name}: {e}", file=sys.stderr)
    finally:
        server.shutdown()
        xvfb.terminate()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
