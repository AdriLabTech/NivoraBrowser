#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Two checks of the built browser's profile handling (docs/TESTING.md, F-06 and F-10).

  F-06  settings persist across a restart: the browser is started with an empty HOME, two preferences
        are changed through its own preference service, it is quit the way a user quits it, started
        again with the same profile, and the preferences must have the values that were set (so the
        start-up repair of Nivora's settings must not touch valid values either);
  F-10  a Zen or Firefox profile that already exists is neither read nor changed: `~/.zen`,
        `~/.config/zen` and `~/.mozilla` are created with a few files before the first start, and a
        checksum of each tree is compared after the second.

The browser is driven over Marionette (its remote-control protocol, spoken here over a plain socket so
that nothing needs installing). Only the browser built from this repository runs, with a throw-away HOME.
Needs Xvfb. Usage: check_profile.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin [--out DIR]
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PORT = 2828
SET = {"nivora.ui.animations": False, "zen.glance.animation-duration": 777}
FOREIGN = [".zen", ".config/zen", ".mozilla/firefox"]


def encode(message):
    """A Marionette message: the length of the JSON text, a colon, the text."""
    body = json.dumps(message)
    return f"{len(body.encode())}:{body}".encode()


def decode(buffer):
    """-> (message, rest) for the first complete message in `buffer` (bytes), or (None, buffer)."""
    head, colon, tail = buffer.partition(b":")
    if not colon or not head.isdigit():
        return None, buffer
    size = int(head)
    if len(tail) < size:
        return None, buffer
    return json.loads(tail[:size].decode()), tail[size:]


class Marionette:
    def __init__(self, port=PORT, timeout=120):
        deadline = time.time() + timeout
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(1)
        self.buffer, self.counter = b"", 0
        self._read()  # the hello the server sends first
        self.call("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
        self.call("Marionette:SetContext", {"value": "chrome"})

    def _read(self):
        while True:
            message, self.buffer = decode(self.buffer)
            if message is not None:
                return message
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("the browser closed the connection")
            self.buffer += chunk

    def call(self, name, params=None):
        self.counter += 1
        self.sock.sendall(encode([0, self.counter, name, params or {}]))
        while True:
            message = self._read()
            if isinstance(message, list) and message[0] == 1 and message[1] == self.counter:
                if message[2]:
                    raise RuntimeError(f"{name}: {message[2]}")
                return message[3]

    def script(self, body, args=None):
        return self.call("WebDriver:ExecuteScript", {"script": body, "args": args or []})["value"]

    def quit(self):
        try:
            self.call("Marionette:Quit", {"flags": ["eAttemptQuit"]})
        except (ConnectionError, OSError):
            pass
        self.sock.close()


def tree_digest(path):
    """A digest of every file under `path` (relative name, size, content): changes if anything is added,
    removed or edited."""
    digest = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = Path(root) / name
            digest.update(str(full.relative_to(path)).encode())
            digest.update(full.read_bytes())
    return digest.hexdigest()


def plant_foreign_profiles(home):
    """Create stand-ins for a user's Zen and Firefox profiles, with a few files each."""
    digests = {}
    for rel in FOREIGN:
        base = home / rel
        (base / "Profiles" / "abc.Default").mkdir(parents=True)
        (base / "profiles.ini").write_text("[Profile0]\nName=default\nPath=Profiles/abc.Default\nDefault=1\n")
        (base / "Profiles" / "abc.Default" / "prefs.js").write_text('user_pref("marker.untouched", true);\n')
        (base / "Profiles" / "abc.Default" / "places.sqlite").write_bytes(os.urandom(4096))
        digests[rel] = tree_digest(base)
    return digests


def start(binary, home, display):
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    return subprocess.Popen([str(binary), "--no-remote", "-marionette", "-remote-allow-system-access", "about:blank"],
                            env=env, cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_prefs(client):
    return client.script(
        "return Object.fromEntries(arguments[0].map(n => [n, Services.prefs.getPrefType(n) == Services.prefs.PREF_INVALID"
        " ? null : (Services.prefs.getPrefType(n) == Services.prefs.PREF_BOOL ? Services.prefs.getBoolPref(n)"
        " : Services.prefs.getIntPref(n))]));",
        [list(SET)],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True, help="the dist/bin directory containing `nivora`")
    parser.add_argument("--out", type=Path, help="where to write report.json")
    parser.add_argument("--display", default=":94")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    if not binary.is_file():
        print(f"error: {binary} not found", file=sys.stderr)
        return 2
    if not shutil.which("Xvfb"):
        print("error: Xvfb is required", file=sys.stderr)
        return 2

    home = Path(tempfile.mkdtemp(prefix="nivora-profile-home-"))
    report = {"checks": {}}
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1280x800x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        time.sleep(2)
        before = plant_foreign_profiles(home)

        browser = start(binary, home, args.display)
        client = Marionette()
        initial = read_prefs(client)
        for name, value in SET.items():
            client.script(
                "const [n, v] = arguments; typeof v == 'boolean' ? Services.prefs.setBoolPref(n, v) : Services.prefs.setIntPref(n, v);",
                [name, value],
            )
        client.quit()
        browser.wait(timeout=120)
        report["first_run_values_before"] = initial

        profiles = sorted((home / ".config" / "nivora").glob("*"))
        prefs_files = list((home / ".config" / "nivora").glob("*/prefs.js"))
        report["profile_dirs"] = [p.name for p in profiles]
        saved = prefs_files[0].read_text() if prefs_files else ""
        for name, value in SET.items():
            wanted = f'user_pref("{name}", {json.dumps(value)});'
            report["checks"][f"F-06 {name} is written to prefs.js on quit"] = wanted in saved

        browser = start(binary, home, args.display)
        client = Marionette()
        after = read_prefs(client)
        client.quit()
        browser.wait(timeout=120)
        report["second_run_values"] = after
        for name, value in SET.items():
            report["checks"][f"F-06 {name} is {value!r} after a restart"] = after.get(name) == value

        for rel in FOREIGN:
            report["checks"][f"F-10 ~/{rel} is unchanged by two starts"] = tree_digest(home / rel) == before[rel]
        report["checks"]["F-10 Nivora used ~/.config/nivora"] = bool(prefs_files)
    finally:
        if browser and browser.poll() is None:
            browser.kill()
        xvfb.terminate()
        shutil.rmtree(home, ignore_errors=True)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "report.json").write_text(text)
    print(text)
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
