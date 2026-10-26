#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Look for a newer Zen release and check that the vendored tree is still pristine.

This is step 1 of the update procedure in docs/UPSTREAM.md ("detect a candidate"). It only reads:
it never changes the repository and never updates anything.

  upstream_check.py                 report the pinned revisions and any newer Zen release
  upstream_check.py --verify-root   also prove the first commit is byte-for-byte the pinned Zen tag
  upstream_check.py --json          machine-readable output

Exit status: 0 up to date, 10 a newer Zen release exists, 1 the vendored tree differs from the pin,
2 the check itself failed (network, malformed data).
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN_FILE = HERE / "upstream.json"

ZEN_TAG = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?b$")


class CheckError(Exception):
    pass


def parse_zen_tag(tag):
    """'1.23.4b' -> (1, 23, 4); 'twilight-1' and other non-release tags -> None."""
    match = ZEN_TAG.match(tag)
    if not match:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def firefox_tag(version):
    """'158.0.1' -> 'FIREFOX_158_0_1_RELEASE'."""
    return "FIREFOX_" + version.replace(".", "_") + "_RELEASE"


def newer_releases(pinned_tag, tags):
    """Release tags newer than `pinned_tag`, oldest first."""
    pinned = parse_zen_tag(pinned_tag)
    if pinned is None:
        raise CheckError(f"the pinned tag '{pinned_tag}' is not a Zen release tag")
    found = [(parse_zen_tag(tag), tag) for tag in tags]
    return [tag for version, tag in sorted(t for t in found if t[0] is not None) if version > pinned]


def git(*args, cwd=None):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise CheckError(f"git {' '.join(args[:2])} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def ls_remote_tags(repo, pattern=None):
    """{tag: commit} for a remote repository. Annotated tags report the commit they point at."""
    args = ["ls-remote", "--tags", repo]
    if pattern:
        args.append(pattern)
    tags = {}
    for line in git(*args).splitlines():
        sha, ref = line.split("\t")
        name = ref[len("refs/tags/") :]
        if name.endswith("^{}"):
            tags[name[:-3]] = sha
        else:
            tags.setdefault(name, sha)
    return tags


def fetch_tag(repo, tag, directory):
    """Fetch one tag, depth 1, into a scratch repository; return the commit and tree hashes."""
    git("init", "-q", directory)
    git("fetch", "-q", "--depth", "1", repo, f"refs/tags/{tag}:refs/tags/{tag}", cwd=directory)
    commit = git("rev-parse", f"{tag}^{{commit}}", cwd=directory).strip()
    tree = git("rev-parse", f"{tag}^{{tree}}", cwd=directory).strip()
    return commit, tree


def surfer_json_at(repo, tag):
    with tempfile.TemporaryDirectory() as directory:
        fetch_tag(repo, tag, directory)
        return json.loads(git("show", f"{tag}:surfer.json", cwd=directory))


def root_tree():
    root = git("rev-list", "--max-parents=0", "HEAD", cwd=ROOT).split()[0]
    return root, git("rev-parse", f"{root}^{{tree}}", cwd=ROOT).strip()


def build_report(pin, remote_tags, firefox_tags, candidate_info):
    """The facts, as a dict. `candidate_info` maps a Zen tag to the Firefox version it needs."""
    zen = pin["zen"]
    candidates = newer_releases(zen["tag"], remote_tags)
    report = {
        "pinned": {
            "zen": zen["tag"],
            "zen_commit": zen["commit"],
            "firefox": zen["firefox"],
            "firefox_tag": pin["firefox"]["tag"],
        },
        "zen_tag_commit_matches_pin": remote_tags.get(zen["tag"]) == zen["commit"],
        "firefox_tag_commit_matches_pin": firefox_tags.get(pin["firefox"]["tag"]) == pin["firefox"]["commit"],
        "candidates": [],
    }
    for tag in candidates:
        needs = candidate_info.get(tag)
        report["candidates"].append(
            {
                "zen": tag,
                "zen_commit": remote_tags[tag],
                "firefox": needs,
                "firefox_tag": firefox_tag(needs) if needs else None,
                "firefox_tag_exists": bool(needs) and firefox_tag(needs) in firefox_tags,
                "firefox_changes": needs is not None and needs != zen["firefox"],
            }
        )
    return report


def render(report, root_check=None):
    pinned = report["pinned"]
    lines = [
        "# Upstream check",
        "",
        f"Pinned: Zen `{pinned['zen']}` (`{pinned['zen_commit'][:7]}`) on Firefox `{pinned['firefox']}` (`{pinned['firefox_tag']}`).",
        "",
        f"- Zen tag still points at the pinned commit: {'yes' if report['zen_tag_commit_matches_pin'] else '**NO** (the tag was moved)'}",
        f"- Firefox tag still points at the pinned commit: {'yes' if report['firefox_tag_commit_matches_pin'] else '**NO**'}",
    ]
    if root_check is not None:
        lines.append(f"- First commit equals the pinned Zen tag, byte for byte: {'yes' if root_check else '**NO**'}")
    lines.append("")
    if not report["candidates"]:
        lines.append("No newer Zen release.")
    else:
        lines.append("## Newer Zen releases")
        lines.append("")
        lines.append("| Zen | Needs Firefox | Firefox tag exists | Firefox version changes |")
        lines.append("|---|---|---|---|")
        for c in report["candidates"]:
            lines.append(
                f"| `{c['zen']}` | `{c['firefox'] or 'unknown'}` | {'yes' if c['firefox_tag_exists'] else 'no'} | {'yes' if c['firefox_changes'] else 'no'} |"
            )
        lines += [
            "",
            "Nothing was changed. To evaluate a candidate follow docs/UPSTREAM.md section 4: import the",
            "snapshot on a vendor branch, merge, run `surfer import` against the Firefox tag above, run the",
            "checks, build, run the regression suite and write the compatibility report.",
        ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify-root", action="store_true", help="compare the first commit with the pinned Zen tag")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = parser.parse_args(argv)
    try:
        pin = json.loads(PIN_FILE.read_text(encoding="utf-8"))
        remote_tags = ls_remote_tags(pin["zen"]["repo"])
        firefox_tags = ls_remote_tags(pin["firefox"]["repo"], "refs/tags/FIREFOX_1*_RELEASE")
        info = {}
        for tag in newer_releases(pin["zen"]["tag"], remote_tags):
            info[tag] = surfer_json_at(pin["zen"]["repo"], tag)["version"]["version"]
        report = build_report(pin, remote_tags, firefox_tags, info)
        root_ok = None
        if args.verify_root:
            with tempfile.TemporaryDirectory() as directory:
                _, upstream_tree = fetch_tag(pin["zen"]["repo"], pin["zen"]["tag"], directory)
            root_ok = root_tree()[1] == upstream_tree
    except (CheckError, OSError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({**report, "root_matches_pinned_tag": root_ok}, indent=2))
    else:
        print(render(report, root_ok), end="")
    if root_ok is False or not report["zen_tag_commit_matches_pin"]:
        return 1
    return 10 if report["candidates"] else 0


if __name__ == "__main__":
    sys.exit(main())
