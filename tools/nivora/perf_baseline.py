#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""A small performance baseline of the built browser (docs/TESTING.md, section 5).

For each run it starts the browser under Xvfb with a page served from this machine and records:
  - start-up: seconds from launching the process until the page's title is on screen;
  - memory: proportional set size (PSS) of the whole process tree after the page has settled;
  - idle CPU: CPU time of the whole tree over a window with nothing happening, as a share of one core.
A "first" run uses an empty profile (what a new user pays once); a "warm" run reuses the profile
left by the first.

These numbers describe one build (development configuration, no LTO/PGO) in one environment. They
are only useful as a reference to compare a later build of Nivora with, on the same machine. They
say nothing about Zen: no equivalent Zen build was measured.

Usage: perf_baseline.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out FILE.json [--runs 3] [--idle 30]
"""

import argparse
import http.server
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import smoke  # noqa: E402

TICKS = os.sysconf("SC_CLK_TCK")


def children_of(root):
    """PIDs of `root` and all its descendants."""
    parents = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
        except (OSError, IndexError, ValueError):
            continue
    found, queue = {root}, [root]
    while queue:
        current = queue.pop()
        for pid, parent in parents.items():
            if parent == current and pid not in found:
                found.add(pid)
                queue.append(pid)
    return found


def pss_kib(pids):
    total = 0
    for pid in pids:
        try:
            for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
                if line.startswith("Pss:"):
                    total += int(line.split()[1])
        except OSError:
            pass
    return total


def cpu_ticks(pids):
    total = 0
    for pid in pids:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            total += int(fields[11]) + int(fields[12])
        except (OSError, IndexError, ValueError):
            pass
    return total


def run_once(binary, home, display, idle):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), smoke.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    started = time.monotonic()
    browser = subprocess.Popen([str(binary), "--no-remote", url], env=env, cwd=home,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        seen = None
        while time.monotonic() - started < 120:
            if any("Nivora smoke test page" in n for n in smoke.window_names(display)):
                seen = time.monotonic() - started
                break
            time.sleep(0.1)
        if seen is None:
            raise RuntimeError("the page title never appeared")
        time.sleep(10)  # let start-up work settle
        tree = children_of(browser.pid)
        before, t0 = cpu_ticks(tree), time.monotonic()
        time.sleep(idle)
        tree = children_of(browser.pid)
        after, t1 = cpu_ticks(tree), time.monotonic()
        return {
            "startup_seconds": round(seen, 2),
            "processes": len(tree),
            "pss_mib": round(pss_kib(tree) / 1024, 1),
            "idle_cpu_percent_of_one_core": round(100 * (after - before) / TICKS / (t1 - t0), 2),
        }
    finally:
        if browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
        server.shutdown()


def summarize(runs):
    keys = ("startup_seconds", "pss_mib", "idle_cpu_percent_of_one_core")
    return {k: {"median": statistics.median(r[k] for r in runs), "min": min(r[k] for r in runs),
                "max": max(r[k] for r in runs)} for k in keys}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--idle", type=int, default=30)
    parser.add_argument("--display", default=":95")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    if not binary.is_file() or not shutil.which("Xvfb") or not shutil.which("xdotool"):
        print("error: needs the built binary, Xvfb and xdotool", file=sys.stderr)
        return 2
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1400x900x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = {"environment": {"cpus": os.cpu_count(),
                              "memory_mib": int(next(l for l in Path("/proc/meminfo").read_text().splitlines()
                                                      if l.startswith("MemTotal")).split()[1]) // 1024},
              "runs": {"first": [], "warm": []}}
    try:
        time.sleep(2)
        for _ in range(args.runs):
            home = Path(tempfile.mkdtemp(prefix="nivora-perf-home-"))
            try:
                result["runs"]["first"].append(run_once(binary, home, args.display, args.idle))
                result["runs"]["warm"].append(run_once(binary, home, args.display, args.idle))
            finally:
                shutil.rmtree(home, ignore_errors=True)
    finally:
        xvfb.terminate()
    result["summary"] = {kind: summarize(runs) for kind, runs in result["runs"].items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
