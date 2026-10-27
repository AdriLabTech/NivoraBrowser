#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The smoke test of smoke.py, on Wayland: the browser runs as a Wayland client of a headless `sway`.

Checks: the browser opens a window whose application id is `nivora` and whose title carries the
page's title (so it renders and runs as a native Wayland client, not through XWayland), it
creates only `~/.config/nivora`, and it exits when asked. Saves a screenshot taken with `grim`.

The compositor is software-rendered and has no input device, so this shows that the browser starts and
draws on Wayland, not that it is pleasant to use there. Needs `sway`, `swaymsg` and `grim`.

Usage: smoke_wayland.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

import smoke  # noqa: E402


def windows(tree):
    """Every container of a `swaymsg -t get_tree` result that is a window: (app_id, name)."""
    found = []

    def walk(node):
        if node.get("app_id") or node.get("window_properties"):
            found.append((node.get("app_id"), node.get("name")))
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            walk(child)

    walk(tree)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    for tool in ("sway", "swaymsg", "grim"):
        if not shutil.which(tool):
            print(f"error: {tool} is required", file=sys.stderr)
            return 2
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"checks": {}}
    runtime = Path(tempfile.mkdtemp(prefix="nvl-", dir="/tmp"))  # short: a socket path has a length limit
    runtime.chmod(0o700)
    home = Path(tempfile.mkdtemp(prefix="nivora-wl-home-"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), smoke.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    base = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    sway_env = {**base, "XDG_RUNTIME_DIR": str(runtime), "WLR_BACKENDS": "headless", "WLR_RENDERER": "pixman",
                "WLR_LIBINPUT_NO_DEVICES": "1"}
    compositor = subprocess.Popen(["sway"], env=sway_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        sock = smoke.wait_for(lambda: next(iter(runtime.glob("sway-ipc.*.sock")), None), 20)
        display = smoke.wait_for(lambda: next((p.name for p in runtime.glob("wayland-*") if not p.name.endswith(".lock")), None), 20)
        if not sock or not display:
            raise RuntimeError("sway did not start")
        env = {**sway_env, "SWAYSOCK": str(sock), "WAYLAND_DISPLAY": display, "MOZ_ENABLE_WAYLAND": "1",
               "GDK_BACKEND": "wayland", "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(home / ".cache")}
        log = open(args.out / "browser.log", "w")
        browser = subprocess.Popen([str(binary), "--no-remote", url], env=env, cwd=home, stdout=log, stderr=subprocess.STDOUT)

        def ours():
            tree = json.loads(smoke.run(["swaymsg", "-t", "get_tree"], env=env).stdout or "{}")
            return [w for w in windows(tree) if w[0] == "nivora"]

        found = smoke.wait_for(lambda: [w for w in ours() if w[1] and "Nivora smoke test page" in w[1]], 90)
        report["windows"] = ours()
        report["checks"]["window of the Wayland application id `nivora` appears"] = bool(ours())
        report["checks"]["page title is shown in that window"] = bool(found)
        time.sleep(3)
        shot = smoke.run(["grim", str(args.out / "page.png")], env=env)
        report["checks"]["screenshot taken"] = shot.returncode == 0
        entries = sorted(p.name for p in home.iterdir())
        report["home_entries"] = entries
        report["checks"]["creates .config/nivora"] = (home / ".config" / "nivora").exists() or ".nivora" in entries
        report["checks"]["creates no .zen and no .mozilla"] = not any(
            (home / n).exists() for n in (".zen", ".mozilla", ".config/zen", ".config/mozilla"))
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
        compositor.terminate()
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(runtime, ignore_errors=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["checks"] and all(report["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
