#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Measure the animations of the built browser by recording the screen (docs/ANIMATIONS.md).

For each scenario it starts the browser, lets it settle, starts `ffmpeg` recording the virtual
display at 30 frames per second, replays an interaction, and decodes the recording to small gray
frames. From the difference between consecutive frames it reports:

  start_ms      from the interaction until the first visible change
  duration_ms   from the first to the last visible change (how long the motion lasts)
  frames        distinct frames shown during the motion
  max_gap_ms    the longest time the picture stood still inside the motion (stutter)
  peak_change   the largest share of pixels that changed between two frames

Under Xvfb the browser is software-rendered, so absolute frame rates are far below a real GPU's.
The numbers are for comparing two builds on the same machine; they are not a claim about smoothness
on real hardware. A contact sheet of the motion is saved so a person can look at it.

Usage: motion_probe.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR [--only NAME ...] [--fps 30]
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import screenshots as shots  # noqa: E402

W, H = 1260, 810
SMALL_W, SMALL_H = 252, 162  # 1/5 scale: enough to see a panel move, cheap to compare
THRESHOLD = 0.0004  # share of changed pixels below which two frames count as the same picture

SCENARIOS = {
    "palette-open": {"urls": ["/Alpha", "/Beta"], "prefs": {}, "settle": 8, "actions": [("key", "ctrl+l")], "record": 2.5},
    "palette-close": {"urls": ["/Alpha", "/Beta"], "settle": 8, "pre": [("key", "ctrl+l"), ("wait", 2)], "actions": [("key", "Escape")], "record": 2.5},
    "tab-select": {"urls": ["/Alpha", "/Beta", "/Gamma"], "settle": 9, "actions": [("click", 90, 286)], "record": 2.5},
    "new-tab": {"urls": ["/Alpha"], "settle": 8, "actions": [("key", "ctrl+t")], "record": 2.5},
    "close-tab": {"urls": ["/Alpha", "/Beta"], "settle": 9, "actions": [("key", "ctrl+w")], "record": 2.5},
    "sidebar-toggle": {"urls": ["/Alpha"], "settle": 8, "actions": [("key", "ctrl+b")], "record": 3},
    "app-menu": {"urls": ["/Alpha"], "settle": 8, "actions": [("click", 18, 21)], "record": 2.5},
    "tab-context-menu": {"urls": ["/Alpha", "/Beta"], "settle": 8, "actions": [("rclick", 90, 206)], "record": 2.5},
    # about:preferences cannot be passed on the command line, so it is opened from the address bar; the
    # click then switches to the "Privacy and security" category (the icon column of the narrow layout).
    "settings-pane": {"urls": ["about:blank"], "settle": 8,
                      "pre": [("key", "ctrl+l"), ("type", "about:preferences"), ("key", "Return"), ("wait", 9),
                              ("move", 1200, 400), ("wait", 3)],
                      "keep_mouse": True, "actions": [("click", 242, 342)], "record": 2.5},
    # A tab opens in the sidebar: the address is typed first, so only Enter is inside the recording.
    "open-tab": {"urls": ["/Alpha"], "settle": 8, "pre": [("key", "ctrl+t"), ("wait", 2), ("type", "about:blank"), ("wait", 1.5)],
                 "actions": [("key", "Return")], "record": 2.5},
    # The window assembling itself: recording starts before the browser does.
    "boot": {"urls": ["/Alpha"], "boot": True, "settle": 0, "actions": [], "record": 9},
}

# The same interactions with the setting off: the motion must be gone, not just shorter.
for _name in ("palette-open", "app-menu", "close-tab", "settings-pane", "open-tab"):
    SCENARIOS[f"{_name}-off"] = {**SCENARIOS[_name], "prefs": {"nivora.ui.animations": False}}


def decode(path):
    """Gray frames of the recording, each SMALL_W x SMALL_H bytes."""
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={SMALL_W}:{SMALL_H}:flags=area,format=gray",
                           "-f", "rawvideo", "-"], capture_output=True, timeout=120)
    size = SMALL_W * SMALL_H
    data = proc.stdout
    return [data[i:i + size] for i in range(0, len(data) - size + 1, size)]


def change(a, b):
    """Share of pixels that differ visibly between two frames."""
    return sum(1 for x, y in zip(a, b) if abs(x - y) > 6) / len(a)


def analyse(frames, fps):
    """-> metrics of the motion in a list of frames (see the module docstring), or None if nothing moved."""
    steps = [change(frames[i - 1], frames[i]) for i in range(1, len(frames))]
    moving = [i for i, c in enumerate(steps) if c > THRESHOLD]
    if not moving:
        return None
    first, last = moving[0], moving[-1]
    window = steps[first:last + 1]
    gap = longest = 0
    for c in window:
        gap = gap + 1 if c <= THRESHOLD else 0
        longest = max(longest, gap)
    return {
        "first_change_frame": first + 1,
        "duration_ms": round((last - first + 1) * 1000 / fps),
        "frames": sum(1 for c in window if c > THRESHOLD),
        "max_gap_ms": round((longest + 1) * 1000 / fps) if longest else round(1000 / fps),
        "peak_change": round(max(window), 3),
    }


def record(binary, out, name, scenario, port, display, fps):
    home = Path(tempfile.mkdtemp(prefix="nivora-motion-home-"))
    profile = home / "profile"
    profile.mkdir()
    (profile / "user.js").write_text("".join(shots.pref_line(k, v) + "\n" for k, v in scenario.get("prefs", {}).items()))
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    urls = [u if u.startswith("about:") else f"http://127.0.0.1:{port}{u}" for u in scenario["urls"]]
    browser_cmd = [str(binary), "--no-remote", "--profile", str(profile), *urls]
    browser = None
    video = out / f"{name}.mkv"

    def start_grab():
        return subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "x11grab", "-framerate", str(fps), "-video_size", f"{W}x{H}",
                                 "-i", f"{display}+0,0", "-t", str(scenario["record"] + 1), "-c:v", "libx264", "-preset", "ultrafast",
                                 "-crf", "18", "-pix_fmt", "yuv420p", str(video)], env=env)

    try:
        if scenario.get("boot"):
            return boot(browser_cmd, env, home, scenario, start_grab, video)
        browser = subprocess.Popen(browser_cmd, env=env, cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(scenario["settle"])
        for action in scenario.get("pre", []):
            shots.act(env, display, browser.pid, action)
        if not scenario.get("keep_mouse"):
            subprocess.run(["xdotool", "mousemove", "700", "500"], env=env, timeout=30)
        time.sleep(1)
        grab = start_grab()
        time.sleep(0.7)  # ffmpeg needs a moment before the first frame
        for action in scenario["actions"]:
            shots.act(env, display, browser.pid, action)
        grab.wait(timeout=60)
    finally:
        if browser and browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
        shutil.rmtree(home, ignore_errors=True)
    return video


def boot(browser_cmd, env, home, scenario, start_grab, video):
    """Record the screen from before the browser starts until `record` seconds later."""
    grab = start_grab()
    time.sleep(0.7)
    browser = subprocess.Popen(browser_cmd, env=env, cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        grab.wait(timeout=60)
    finally:
        if browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
        shutil.rmtree(home, ignore_errors=True)
    return video


def sheet(video, frames_dir, target, start=0):
    """A contact sheet: every other frame of the recording from frame `start`, 6 per row."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    pick = f"select='gte(n\\,{start})*not(mod(n-{start}\\,2))'"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"{pick},scale=420:-1,tile=6x5",
                    "-frames:v", "1", str(target)], timeout=120)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only", nargs="*", choices=sorted(SCENARIOS))
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--display", default=":93")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    for tool in ("Xvfb", "xdotool", "ffmpeg"):
        if not shutil.which(tool):
            print(f"error: {tool} is required", file=sys.stderr)
            return 2
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    import http.server
    import threading

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), shots.Pages)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", f"{W}x{H}x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {}
    try:
        time.sleep(2)
        for name in args.only or SCENARIOS:
            try:
                video = record(binary, out, name, SCENARIOS[name], server.server_address[1], args.display, args.fps)
                report[name] = analyse(decode(video), args.fps)
                first = (report[name] or {}).get("first_change_frame", 0)
                sheet(video, out / "frames", out / f"{name}.png", start=max(0, first - 3))
                print(f"{name:18} {report[name]}")
            except Exception as e:  # keep going: one failing scenario should not hide the others
                report[name] = {"error": str(e)}
                print(f"FAILED {name}: {e}", file=sys.stderr)
    finally:
        server.shutdown()
        xvfb.terminate()
    (out / "motion.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
