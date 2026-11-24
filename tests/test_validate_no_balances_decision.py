#!/usr/bin/env python3
"""Contract test for no_balances shape coverage and decision D-06 (task 2.3).

Stellar protocol rules mandate a minimum reserve in native lumens for an account entry
to exist on the ledger. Consequently, live Horizon /accounts/<id> endpoints always return
at least one balance entry (asset_type: native). Task 2.3 records decision D-06 that
no_balances stays uncovered by captured fixtures on live networks and is verified by
offline validator rules.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
README_PATH = REPO_ROOT / "README.md"


class NoBalancesDecisionTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_roadmap_contains_decision_d06(self) -> None:
        self.assertTrue(ROADMAP_PATH.is_file())
        content = ROADMAP_PATH.read_text(encoding="utf-8")
        self.assertIn("D-06", content)
        self.assertIn("minimum native lumen reserve", content)
        self.assertIn("cannot be captured from a live network", content)

    def test_roadmap_task_2_3_is_marked_done(self) -> None:
        self.assertTrue(ROADMAP_PATH.is_file())
        content = ROADMAP_PATH.read_text(encoding="utf-8")
        self.assertIn("- [x] **2.3**", content)
        self.assertIn("D-06 records that Stellar protocol minimum reserve", content)

    def test_readme_documents_reserve_constraint_for_no_balances(self) -> None:
        self.assertTrue(README_PATH.is_file())
        content = README_PATH.read_text(encoding="utf-8")
        self.assertIn("D-06", content)
        self.assertIn("protocol reserve requirements", content)

    def test_shapes_of_derives_no_balances_when_balances_list_is_empty(self) -> None:
        account_with_empty_balances = {
            "account_id": "GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75",
            "balances": [],
        }
        derived = validate.shapes_of(account_with_empty_balances)
        self.assertIn("no_balances", derived)

    def test_shapes_of_does_not_derive_no_balances_when_native_balance_present(self) -> None:
        account_with_native = {
            "account_id": "GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75",
            "balances": [{"asset_type": "native", "balance": "100.0000000"}],
        }
        derived = validate.shapes_of(account_with_native)
        self.assertNotIn("no_balances", derived)


if __name__ == "__main__":
    unittest.main()
