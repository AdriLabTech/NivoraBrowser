# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The /proc readers of tools/nivora/perf_baseline.py, tried on real processes (no browser needed)."""

import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import perf_baseline as pb  # noqa: E402


class ProcessTreeTest(unittest.TestCase):
    def test_finds_a_grandchild(self):
        child = subprocess.Popen(["sh", "-c", "sleep 30 & wait"])
        try:
            time.sleep(0.5)
            tree = pb.children_of(child.pid)
            self.assertIn(child.pid, tree)
            self.assertGreaterEqual(len(tree), 2, "the background sleep is a descendant")
            self.assertNotIn(os.getpid(), tree)
        finally:
            child.kill()
            subprocess.run(["pkill", "-f", "^sleep 30$"], check=False)
            child.wait()

    def test_memory_and_cpu_readers_see_this_process(self):
        self.assertGreater(pb.pss_kib({os.getpid()}), 1000)
        busy = sum(i * i for i in range(2_000_000))
        self.assertGreater(busy, 0)
        self.assertGreater(pb.cpu_ticks({os.getpid()}), 0)

    def test_missing_pid_counts_as_zero(self):
        self.assertEqual(pb.pss_kib({2**22 + 12345}), 0)
        self.assertEqual(pb.cpu_ticks({2**22 + 12345}), 0)

    def test_summary_uses_the_median(self):
        runs = [{"startup_seconds": s, "pss_mib": 100.0, "idle_cpu_percent_of_one_core": 1.0} for s in (3.0, 1.0, 2.0)]
        summary = pb.summarize(runs)
        self.assertEqual(summary["startup_seconds"], {"median": 2.0, "min": 1.0, "max": 3.0})


if __name__ == "__main__":
    unittest.main()
