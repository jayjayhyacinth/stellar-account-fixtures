#!/usr/bin/env python3
"""Verify the --root CLI parameter for validating a corpus outside the repository checkout."""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402


class TestValidateRootOption(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="external-root-test-")
        self.addCleanup(self.stage.cleanup)
        self.external_root = Path(self.stage.name).resolve() / "external_corpus"
        self.external_root.mkdir()
        shutil.copytree(REPO_ROOT / "fixtures", self.external_root / "fixtures")
        shutil.copytree(REPO_ROOT / "corpus", self.external_root / "corpus")

    def test_external_root_validates_cleanly_via_main(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = validate.main(["--root", str(self.external_root)])

        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertIn("validate: corpus agrees with itself", out.getvalue())

    def test_external_root_report_retains_relative_fixture_prefixes(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = validate.main(["--root", str(self.external_root), "--report"])

        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        stdout_lines = [
            line for line in out.getvalue().splitlines() if line.startswith("fixtures/")
        ]
        self.assertGreater(len(stdout_lines), 0)
        for line in stdout_lines:
            self.assertTrue(line.startswith("fixtures/"))
            self.assertNotIn(str(self.external_root), line)

    def test_external_root_relative_path_resolves_and_exits_zero(self) -> None:
        cwd = Path.cwd().resolve()
        try:
            rel_path = self.external_root.relative_to(cwd)
        except ValueError:
            rel_path = Path(os.path.relpath(self.external_root, cwd))

        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = validate.main(["--root", str(rel_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertIn("validate: corpus agrees with itself", out.getvalue())


if __name__ == "__main__":
    unittest.main()
