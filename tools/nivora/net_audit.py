#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Which host names does a fresh Nivora profile try to resolve? (test F-09)

Starts the built browser with an empty profile, no proxy, one local page, Gecko's host-resolver
log switched on, waits, stops it and lists every name it
asked the resolver about. Every name is classified:

  zen        a Zen-operated service: the audit FAILS
  mozilla    a standard Firefox service (Remote Settings, push, region, captive portal, updates)
  component  where Firefox downloads media components: Cisco (OpenH264) and Google (Widevine)
  search     the default search engine, contacted to warm up a connection or to suggest
  local      loopback, `.local`, or the special names Gecko uses to probe the network
  unknown    anything else: the audit FAILS until the name is explained and added here

Limits, so the result is not over-read: the log shows lookups the browser
*attempted*. In an environment without general network access nothing past the
first failed lookup of a given feature is seen, and a feature that only runs
after some days (or after the user acts) is not exercised. A clean result
means "no Zen host on first start", not "no traffic of its own".

Needs Xvfb. Usage:
    python3 -I tools/nivora/net_audit.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR [--seconds 60]
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import http.server
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import smoke  # noqa: E402

RESOLVING = re.compile(r"Resolving host \[([^\]\s]+)\]")

ZEN = re.compile(r"(^|\.)(zen-browser\.[a-z]+|zenbrowser\.[a-z]+|zen-browser\.github\.io)$")
MOZILLA = re.compile(
    r"(^|\.)("
    r"mozilla\.(com|org|net)|mozgcp\.net|mozaws\.net|firefox\.com|firefox-portal-detection\.com|"
    r"cloudflare-dns\.com|services\.mozilla\.com"
    r")$"
)
COMPONENT = re.compile(r"(^|\.)(openh264\.org|gvt1\.com|update\.googleapis\.com)$")
SEARCH = re.compile(r"^(www\.)?(google\.com|duckduckgo\.com|bing\.com)$")
LOCAL = re.compile(r"^(localhost|127\.0\.0\.1|\[?::1\]?|local|ipv4only\.arpa|example\.(com|org|net)|[^.]+\.local)$")


def hosts_in(log_text):
    """The distinct host names the resolver was asked about, in first-seen order."""
    seen = {}
    for name in RESOLVING.findall(log_text):
        seen.setdefault(name.lower(), None)
    return list(seen)


def classify(host):
    if ZEN.search(host):
        return "zen"
    if MOZILLA.search(host):
        return "mozilla"
    if COMPONENT.search(host):
        return "component"
    if SEARCH.match(host):
        return "search"
    if LOCAL.match(host):
        return "local"
    return "unknown"


def audit(log_text):
    """-> {"hosts": {host: class}, "ok": bool}"""
    hosts = {h: classify(h) for h in hosts_in(log_text)}
    return {"hosts": hosts, "ok": not any(c in ("zen", "unknown") for c in hosts.values())}


def run_browser(binary, out, seconds, display):
    out.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="nivora-net-home-"))
    log_base = out / "hostresolver"
    for old in out.glob("hostresolver*"):
        old.unlink()
    xvfb = subprocess.Popen(["Xvfb", display, "-screen", "0", "1400x900x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # No proxy: with one, a browser hands host names to the proxy and the resolver log would not show them.
    clean = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy", "https_proxy", "all_proxy", "no_proxy")}
    env = {**clean, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"),
           "MOZ_LOG": "nsHostResolver:5,timestamp", "MOZ_LOG_FILE": str(log_base)}
    profile = home / "profile"
    profile.mkdir()
    (profile / "user.js").write_text('user_pref("network.proxy.type", 0);\n')
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), smoke.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    browser = None
    try:
        time.sleep(2)
        browser = subprocess.Popen([str(binary), "--no-remote", "--profile", str(profile), url], env=env, cwd=home,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(seconds)
    finally:
        if browser and browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
        server.shutdown()
        xvfb.terminate()
        shutil.rmtree(home, ignore_errors=True)
    return "\n".join(p.read_text(errors="replace") for p in sorted(out.glob("hostresolver*")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True, help="the dist/bin directory containing `nivora`")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--display", default=":97")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    if not shutil.which("Xvfb"):
        print("error: Xvfb is required", file=sys.stderr)
        return 2
    log_text = run_browser(binary, args.out.resolve(), args.seconds, args.display)
    result = audit(log_text)
    (args.out / "net-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    for host, kind in result["hosts"].items():
        print(f"{kind:8} {host}")
    print("OK" if result["ok"] else "FAIL: a Zen or unexplained host was resolved")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
