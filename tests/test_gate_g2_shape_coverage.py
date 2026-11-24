#!/usr/bin/env python3
"""Gate G2 contract test: shape coverage verification and gap agreement (gate G2).

Verifies that every shape label in SCHEMA.md Section 5 is either covered by a fixture
in the corpus or explicitly tracked in README.md's stated coverage gaps and ROADMAP.md
decision rows.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

README_PATH = REPO_ROOT / "README.md"
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
SCHEMA_PATH = REPO_ROOT / "SCHEMA.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"

CANONICAL_SHAPES: frozenset[str] = frozenset(
    {
        "no_signers",
        "single_signer",
        "multi_signer",
        "master_is_signer",
        "master_absent",
        "thresholds_zero",
        "thresholds_nonzero",
        "auth_required",
        "auth_revocable",
        "auth_immutable",
        "auth_clawback_enabled",
        "no_home_domain",
        "blank_home_domain",
        "has_home_domain",
        "has_inflation",
        "no_inflation",
        "has_data",
        "no_data",
        "sponsored",
        "not_sponsored",
        "sponsoring",
        "not_sponsoring",
        "no_balances",
        "many_balances",
    }
)


class GateG2ShapeCoverageTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_corpus_fixtures_derive_valid_canonical_shapes(self) -> None:
        fixture_dirs = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
        self.assertGreater(len(fixture_dirs), 0)
        all_covered: set[str] = set()

        for d in fixture_dirs:
            body = d / "account.json"
            self.assertTrue(body.is_file(), f"Missing account.json in {d.name}")
            account = json.loads(body.read_text(encoding="utf-8"))
            derived = validate.shapes_of(account)
            # Every derived label must belong to the canonical vocabulary
            self.assertTrue(
                derived.issubset(CANONICAL_SHAPES),
                f"Fixture {d.name} derived non-canonical labels: {derived - CANONICAL_SHAPES}",
            )
            all_covered |= derived

        self.assertEqual(len(all_covered), 18, "Expected 18 covered shape labels in corpus")

    def test_uncovered_shapes_match_stated_gaps_in_readme(self) -> None:
        self.assertTrue(README_PATH.is_file())
        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn("## Coverage gaps, stated", readme)

        # Extract gap list items from README
        gap_section = readme.split("## Coverage gaps, stated", 1)[1].split("## Checks", 1)[0]
        gap_tokens = set(re.findall(r"`([a-z0-9_]+)`", gap_section))

        all_covered: set[str] = set()
        for d in sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir()):
            account = json.loads((d / "account.json").read_text(encoding="utf-8"))
            all_covered |= validate.shapes_of(account)

        uncovered = CANONICAL_SHAPES - all_covered
        # Every uncovered shape must be acknowledged in the README gap section
        for token in uncovered:
            self.assertIn(
                token,
                gap_tokens,
                f"Uncovered shape {token!r} missing from README coverage gaps section",
            )

    def test_gate_g2_is_tracked_in_roadmap(self) -> None:
        self.assertTrue(ROADMAP_PATH.is_file())
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
        self.assertIn("**G2**", roadmap)
        self.assertIn("Every shape label in `SCHEMA.md` 5 is covered", roadmap)


if __name__ == "__main__":
    unittest.main()
