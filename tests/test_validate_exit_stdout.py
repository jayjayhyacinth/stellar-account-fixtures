#!/usr/bin/env python3
"""Hold validate.py to exit code 2, empty stdout, and stderr error prefix for unreadable corpus."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE = REPO_ROOT / "validate.py"


def run_validate(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True,
        check=False,
    )


class TestValidateExitStdout(unittest.TestCase):
    def test_nonexistent_directory_exits_two_with_empty_stdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unreadable-corpus-") as tmpdir:
            absent = Path(tmpdir) / "does_not_exist"
            result = run_validate("--root", str(absent))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            expected_prefix = f"validate: no readable corpus at {absent.resolve()}".encode()
            self.assertTrue(
                result.stderr.startswith(expected_prefix),
                f"stderr does not start with {expected_prefix!r}: got {result.stderr!r}",
            )
            self.assertNotIn(b"Traceback (most recent call last)", result.stderr)
            self.assertEqual(result.stderr.count(b"\n"), 1)

    def test_directory_without_fixtures_exits_two_with_empty_stdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unreadable-corpus-") as tmpdir:
            empty_root = Path(tmpdir)
            result = run_validate("--root", str(empty_root))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            expected_prefix = f"validate: no readable corpus at {empty_root.resolve()}".encode()
            self.assertTrue(
                result.stderr.startswith(expected_prefix),
                f"stderr does not start with {expected_prefix!r}: got {result.stderr!r}",
            )
            self.assertNotIn(b"Traceback (most recent call last)", result.stderr)
            self.assertEqual(result.stderr.count(b"\n"), 1)


if __name__ == "__main__":
    unittest.main()
