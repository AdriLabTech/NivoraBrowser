# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""The parsing and classification used by the F-09 network audit (no browser needed)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import net_audit  # noqa: E402


def line(host):
    return (f"2026-10-27 02:32:58.751078 UTC - [Parent 7118: Socket Thread]: D/nsHostResolver "
            f"Resolving host [{host}]<> type 0. [this=7f79f75298a0]")


class HostsTest(unittest.TestCase):
    def test_extracts_each_host_once_in_order(self):
        text = "\n".join([line("b.example.net"), "noise", line("A.mozilla.org"), line("b.example.net")])
        self.assertEqual(net_audit.hosts_in(text), ["b.example.net", "a.mozilla.org"])

    def test_ignores_lines_that_only_mention_a_host(self):
        text = "No usable record in cache for host [zen-browser.app] type 0."
        self.assertEqual(net_audit.hosts_in(text), [])


class ClassifyTest(unittest.TestCase):
    def test_zen_hosts_are_zen(self):
        for host in ("zen-browser.app", "updates.zen-browser.app", "share.zen-browser.app",
                     "zen-browser.github.io", "links.zen-browser.app"):
            self.assertEqual(net_audit.classify(host), "zen", host)

    def test_mozilla_hosts(self):
        for host in ("firefox.settings.services.mozilla.com", "firefox-portal-detection.com",
                     "mozilla.cloudflare-dns.com", "cloudflare-dns.com", "content-signature-2.cdn.mozilla.net"):
            self.assertEqual(net_audit.classify(host), "mozilla", host)

    def test_local_and_probe_names(self):
        for host in ("localhost", "127.0.0.1", "ipv4only.arpa", "example.org", "printer.local"):
            self.assertEqual(net_audit.classify(host), "local", host)

    def test_lookalikes_are_not_trusted(self):
        for host in ("mozilla.com.evil.test", "notzen-browser.app.evil.test", "fakefirefox.com", "evil.test"):
            self.assertEqual(net_audit.classify(host), "unknown", host)

    def test_zen_lookalike_suffix_is_still_zen_only_when_it_is_the_registrable_name(self):
        self.assertEqual(net_audit.classify("zen-browser.app.evil.test"), "unknown")


class AuditTest(unittest.TestCase):
    def test_clean_log_passes(self):
        result = net_audit.audit("\n".join([line("firefox.settings.services.mozilla.com"), line("localhost")]))
        self.assertTrue(result["ok"])

    def test_zen_host_fails(self):
        result = net_audit.audit("\n".join([line("firefox.settings.services.mozilla.com"), line("updates.zen-browser.app")]))
        self.assertFalse(result["ok"])
        self.assertEqual(result["hosts"]["updates.zen-browser.app"], "zen")

    def test_unexplained_host_fails(self):
        self.assertFalse(net_audit.audit(line("tracker.example.invalid"))["ok"])

    def test_empty_log_is_ok_but_empty(self):
        self.assertEqual(net_audit.audit(""), {"hosts": {}, "ok": True})


if __name__ == "__main__":
    unittest.main()
