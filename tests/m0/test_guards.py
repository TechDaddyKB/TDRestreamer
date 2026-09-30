"""Regression tests for qualification checks, including optimized Python."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from m0_protocols import require


class GuardTests(unittest.TestCase):
    def test_failed_requirement_is_fatal(self):
        with self.assertRaisesRegex(RuntimeError, "missing track"):
            require(False, "missing track")

    def test_passed_requirement_returns(self):
        self.assertIsNone(require(True, "unused message"))

    def test_optimization_does_not_remove_checks(self):
        result = subprocess.run(
            [
                sys.executable,
                "-O",
                "-c",
                'from m0_protocols import require; require(False, "guard rejected")',
            ],
            cwd=ROOT / "scripts",
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RuntimeError: guard rejected", result.stderr)


if __name__ == "__main__":
    unittest.main()
