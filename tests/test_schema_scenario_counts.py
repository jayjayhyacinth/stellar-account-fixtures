#!/usr/bin/env python3
"""Refuse numeric counts and digit groups in sidecar scenario prose (task 0.6).

A scenario is free prose explaining why an account shape exists in the corpus.
Quantitative counts belong to shape labels and account bytes rather than free
prose, where hardcoded numbers can silently drift from ledger state.
"""

from __future__ import annotations

import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402
import validate  # noqa: E402

WHERE = "fixtures/plain"
COUNT_PROBLEM = validate.SCENARIO_COUNT_PROBLEM


class SchemaScenarioCountsTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_scenario_with_digit_counts_is_rejected(self) -> None:
        bad_scenarios = [
            "an issuer account with auth_required set, two signers at weight 1 and 150 sponsored entries",
            "an issuer account with auth_required set, two signers at weight 1 and 152 sponsorships",
            "37 trustlines and a home domain, the account shape that makes a naive response body large",
            "nine signers with the master key at weight 0 and all three thresholds at 2",
            "num_sponsored 17 against num_sponsoring 0: seventeen balances",
            "six signers on testnet, master weight 0 and all three thresholds at 3",
            "two signers, master weight 2 and nonzero thresholds",
        ]
        for sc in bad_scenarios:
            with self.subTest(scenario=sc):
                err = validate.scenario_error(sc)
                self.assertEqual(err, COUNT_PROBLEM)

    def test_scenario_in_plain_words_is_accepted(self) -> None:
        good_scenarios = [
            "an issuer account with auth_required set, two signers at weight one and sponsored entries",
            "many trustlines and a home domain, the account shape that makes a naive response body large",
            "one signer which is the master key at weight one, all thresholds zero and no optional fields",
            "home_domain lobstr.co with an inflation destination and sponsorships, a well-formed SEP candidate",
            "two signers, master weight two and nonzero thresholds, the shape a shared custody account leaves on chain",
            "synthetic: fabricated empty balances list to exercise offline rule logic without live capture",
        ]
        for sc in good_scenarios:
            with self.subTest(scenario=sc):
                err = validate.scenario_error(sc)
                self.assertIsNone(err)

    def test_all_shipped_fixture_scenarios_have_no_numeric_counts(self) -> None:
        fixtures_dir = REPO_ROOT / "fixtures"
        for directory in sorted(p for p in fixtures_dir.iterdir() if p.is_dir()):
            sidecar_path = directory / "fixture.toml"
            self.assertTrue(sidecar_path.is_file(), f"Missing sidecar in {directory.name}")
            with sidecar_path.open("rb") as f:
                data = tomllib.load(f)
            scenario = data.get("scenario")
            with self.subTest(fixture=directory.name):
                self.assertIsInstance(scenario, str)
                err = validate.scenario_error(scenario)
                self.assertIsNone(err, f"{directory.name} has invalid scenario: {err}")

    def test_capture_tool_refuses_count_in_scenario_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(capture.Refused) as caught:
                capture.capture(
                    fixture_id="fresh",
                    account_id="GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75",
                    scenario="account with 150 sponsorships",
                    network="public",
                    root=Path(tmp_dir),
                    update=False,
                )
            self.assertEqual(str(caught.exception), COUNT_PROBLEM)


if __name__ == "__main__":
    unittest.main()
