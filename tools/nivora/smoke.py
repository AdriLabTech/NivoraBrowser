#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Start the browser you built under a virtual display and check the basics.

What it checks (docs/TESTING.md, F-01, F-02, F-10):
  - the browser starts and opens a window;
  - it loads a page served from this machine and shows its title;
  - with an empty HOME it creates `.nivora` and nothing named `.zen` or `.mozilla`;
  - it exits when asked to.
It saves screenshots and a JSON report in the output directory.

It only ever runs the browser built from this repository, with a throw-away HOME, so it cannot touch
a real profile. Needs Xvfb, xdotool and ImageMagick's `import`.

Usage: smoke.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR
"""

import argparse
import http.server
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PAGE = b"<!doctype html><title>Nivora smoke test page</title><h1>Hello from a local page</h1>"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


def window_names(display):
    result = run(["xdotool", "search", "--onlyvisible", "--name", "."], env={**os.environ, "DISPLAY": display})
    names = []
    for window in result.stdout.split():
        name = run(["xdotool", "getwindowname", window], env={**os.environ, "DISPLAY": display}).stdout.strip()
        if name:
            names.append(name)
    return names


def wait_for(predicate, seconds, step=1.0):
    end = time.time() + seconds
    while time.time() < end:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True, help="the dist/bin directory containing `nivora`")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--display", default=":98")
    args = parser.parse_args(argv)
    binary = args.dist / "nivora"
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    for tool in ("Xvfb", "xdotool", "import"):
        if not shutil.which(tool):
            print(f"error: {tool} is required", file=sys.stderr)
            return 2
    args.out.mkdir(parents=True, exist_ok=True)

    report = {"checks": {}}
    home = Path(tempfile.mkdtemp(prefix="nivora-smoke-home-"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1400x900x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {**os.environ, "HOME": str(home), "DISPLAY": args.display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    browser = None
    try:
        time.sleep(2)
        log = open(args.out / "browser.log", "w")
        browser = subprocess.Popen([str(binary), "--no-remote", url], env=env, stdout=log, stderr=subprocess.STDOUT, cwd=home)
        names = wait_for(lambda: [n for n in window_names(args.display) if "Nivora smoke test page" in n], 90)
        report["checks"]["F-01 starts and opens a window"] = bool(window_names(args.display))
        report["checks"]["F-02 loads a local page and shows its title"] = bool(names)
        report["window_names"] = window_names(args.display)
        time.sleep(3)
        run(["import", "-window", "root", str(args.out / "page.png")], env=env)

        entries = sorted(p.name for p in home.iterdir())
        report["home_entries"] = entries
        report["checks"]["F-10 creates .nivora"] = ".nivora" in entries or (home / ".config" / "nivora").exists()
        report["checks"]["F-10 creates no .zen"] = ".zen" not in entries and not (home / ".config" / "zen").exists()
        report["checks"]["F-10 creates no .mozilla"] = ".mozilla" not in entries and not (home / ".config" / "mozilla").exists()
    finally:
        if browser and browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
                report["checks"]["exits cleanly when asked"] = True
            except subprocess.TimeoutExpired:
                browser.kill()
                report["checks"]["exits cleanly when asked"] = False
        server.shutdown()
        xvfb.terminate()
        shutil.rmtree(home, ignore_errors=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
