#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Is an unsigned extension refused by the browser as shipped? (docs/TESTING.md, F-11)

Puts an unsigned extension in a fresh profile's `extensions/` directory, starts the built browser with
the shipped defaults, and reads the profile's `extensions.json` after start-up. Then repeats with
`xpinstall.signatures.required` switched off as a control: the same file must then be accepted, or
the first result would prove nothing.

It cannot be a browser test: the test harness's own extensions are unsigned, so turning the requirement
on from inside a mochitest disables the harness. Needs Xvfb.

Usage: check_signatures.py --dist engine/obj-x86_64-pc-linux-gnu/dist/bin --out DIR
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
import zipfile
from pathlib import Path

ADDON_ID = "unsigned@nivora.test"
MANIFEST = {
    "manifest_version": 2,
    "name": "Nivora unsigned test",
    "version": "1.0",
    "browser_specific_settings": {"gecko": {"id": ADDON_ID}},
}


def make_xpi(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(MANIFEST))


def run(binary, display, signatures_required, wait):
    """-> (the profile recorded its extensions, the entry of the test extension or None)."""
    home = Path(tempfile.mkdtemp(prefix="nivora-sig-home-"))
    profile = home / "profile"
    (profile / "extensions").mkdir(parents=True)
    make_xpi(profile / "extensions" / f"{ADDON_ID}.xpi")
    prefs = ['user_pref("extensions.autoDisableScopes", 0);',
             'user_pref("extensions.enabledScopes", 15);']
    if not signatures_required:
        prefs.append('user_pref("xpinstall.signatures.required", false);')
    (profile / "user.js").write_text("\n".join(prefs) + "\n")
    env = {**os.environ, "HOME": str(home), "DISPLAY": display, "GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0",
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    browser = subprocess.Popen([str(binary), "--no-remote", "--profile", str(profile), "about:blank"], env=env,
                               cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(wait)
    finally:
        if browser.poll() is None:
            browser.send_signal(signal.SIGTERM)
            try:
                browser.wait(timeout=30)
            except subprocess.TimeoutExpired:
                browser.kill()
    try:
        data = json.loads((profile / "extensions.json").read_text())
        recorded = True
    except (OSError, ValueError):
        data, recorded = {}, False
    shutil.rmtree(home, ignore_errors=True)
    return recorded, next((a for a in data.get("addons", []) if a.get("id") == ADDON_ID), None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wait", type=int, default=25)
    parser.add_argument("--display", default=":94")
    args = parser.parse_args(argv)
    binary = args.dist.resolve() / "nivora"
    if not binary.is_file() or not shutil.which("Xvfb"):
        print("error: needs the built binary and Xvfb", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    xvfb = subprocess.Popen(["Xvfb", args.display, "-screen", "0", "1400x900x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(2)
        default_recorded, default = run(binary, args.display, True, args.wait)
        control_recorded, control = run(binary, args.display, False, args.wait)
    finally:
        xvfb.terminate()
    (args.out / "signatures.json").write_text(json.dumps({"shipped_default": default, "control": control}, indent=2) + "\n")
    keys = ("signedState", "appDisabled", "userDisabled", "active")
    # Refused: the profile recorded its extensions, and this one is absent or disabled by the application.
    refused = default_recorded and (default is None or bool(default.get("appDisabled")))
    accepted = control_recorded and control is not None and not control.get("appDisabled") and bool(control.get("active"))
    print(f"shipped default: {'refused' if refused else 'NOT refused'} "
          f"({'not loaded' if default is None else {k: default.get(k) for k in keys}})")
    print(f"control (requirement off): {'accepted' if accepted else 'NOT accepted'} "
          f"({'not loaded' if control is None else {k: control.get(k) for k in keys}})")
    return 0 if refused and accepted else 1


if __name__ == "__main__":
    sys.exit(main())
