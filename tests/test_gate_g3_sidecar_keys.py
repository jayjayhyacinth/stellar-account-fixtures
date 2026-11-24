#!/usr/bin/env python3
"""Gate G3 contract test: every sidecar key has a test that fails on contradiction (gate G3).

The purpose of Gate G3 is to prove coverage of the sidecar claim set itself: for every key
defined in SCHEMA.md Section 3, there must be a test that goes red when a fixture states
something that contradicts the account record, schema, or disk bytes.

Comparison Table: Sidecar Key to Failing Test Matrix (SCHEMA.md Section 3)
| Key | Schema Status | Contradiction / Lie Tested | Expected Failure Diagnostic | Test Method |
|---|---|---|---|---|
| `schema_version` | Required | Declares schema version 2 | schema_version 2, this tool reads 1 | `test_key_schema_version_contradiction_fails` |
| `id` | Required | ID differs from directory name | does not match its directory name | `test_key_id_contradiction_fails` |
| `kind` | Required | Synthetic kind claiming provenance | synthetic fixture carries provenance it cannot have | `test_key_kind_contradiction_fails` |
| `scenario` | Required | Prose containing numeric count | scenario must not contain numeric counts | `test_key_scenario_contradiction_fails` |
| `account_id` | Required | Sidecar account id differs from account.json | account.json describes ... sidecar says ... | `test_key_account_id_contradiction_fails` |
| `network` | Required | Network host differs from source_url | source_url ... should be ... | `test_key_network_contradiction_fails` |
| `shape` | Required | Shape claims not_sponsored when sponsored | declared shape 'not_sponsored' is not what account.json shows | `test_key_shape_contradiction_fails` |
| `source_url` | Required | Points to wrong endpoint/resource | source_url ... should be ... | `test_key_source_url_contradiction_fails` |
| `captured_at` | Required | Future timestamp | captured_at ... is in the future | `test_key_captured_at_contradiction_fails` |
| `ledger` | Required | Ledger predates last_modified_ledger | sidecar ledger ... predates last_modified_ledger | `test_key_ledger_contradiction_fails` |
| `horizon_version` | Required | Empty horizon version | horizon_version is empty; the capture must say what served it | `test_key_horizon_version_contradiction_fails` |
| `sha256` | Required | Hash does not match account.json bytes | sha256 does not match account.json | `test_key_sha256_contradiction_fails` |
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ALL_TWELVE_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "id",
        "kind",
        "scenario",
        "account_id",
        "network",
        "shape",
        "source_url",
        "captured_at",
        "ledger",
        "horizon_version",
        "sha256",
    }
)

ACCOUNT_ID = "GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75"
PEER_ID = "GCI76XDVHDGJMZGP5EWQYCZCYIBNBVABLPHWCKEZWJF2K4Z5SD74A4AV"
WHERE = "fixtures/plain"


class GateG3SidecarKeysTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="gate-g3-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name)
        (self.root / "corpus").mkdir()
        (self.root / "corpus" / "root-public.json").write_text(
            json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n",
            encoding="utf-8",
        )
        (self.root / "corpus" / "root-testnet.json").write_text(
            json.dumps({"network_passphrase": validate.NETWORKS["testnet"][1]}) + "\n",
            encoding="utf-8",
        )
        self.account: dict[str, object] = {
            "account_id": ACCOUNT_ID,
            "sequence": "100",
            "last_modified_ledger": 1000,
            "balances": [{"asset_type": "native", "balance": "100.0000000"}],
            "signers": [{"key": ACCOUNT_ID, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
            "num_sponsored": 0,
            "num_sponsoring": 0,
        }
        self.fixture_dir = self.root / "fixtures" / "plain"
        self.fixture_dir.mkdir(parents=True)
        self.write_fixture()

    def write_fixture(self, sidecar_overrides: dict[str, object] | None = None) -> None:
        body_bytes = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (self.fixture_dir / "account.json").write_bytes(body_bytes)
        digest = hashlib.sha256(body_bytes).hexdigest()
        derived_shapes = sorted(validate.shapes_of(self.account))

        data: dict[str, object] = {
            "schema_version": 1,
            "id": "plain",
            "kind": "captured",
            "scenario": "a plain account used to verify sidecar key failure contract",
            "account_id": ACCOUNT_ID,
            "network": "public",
            "shape": derived_shapes,
            "source_url": f"{validate.NETWORKS['public'][0]}/accounts/{ACCOUNT_ID}",
            "captured_at": "2026-11-02T12:00:00Z",
            "ledger": 1050,
            "horizon_version": "30.0.0",
            "sha256": digest,
        }
        if sidecar_overrides:
            data.update(sidecar_overrides)

        lines: list[str] = [
            "# Written by test fixture helper.",
            f"schema_version = {data['schema_version']}",
            f'id = "{data["id"]}"',
            f'kind = "{data["kind"]}"',
            f'scenario = "{data["scenario"]}"',
            f'account_id = "{data["account_id"]}"',
            f'network = "{data["network"]}"',
            f"shape = {json.dumps(data['shape'])}",
        ]
        if "source_url" in data:
            lines.append(f'source_url = "{data["source_url"]}"')
        if "captured_at" in data:
            lines.append(f'captured_at = "{data["captured_at"]}"')
        if "ledger" in data:
            lines.append(f"ledger = {data['ledger']}")
        if "horizon_version" in data:
            lines.append(f'horizon_version = "{data["horizon_version"]}"')
        if "sha256" in data:
            lines.append(f'sha256 = "{data["sha256"]}"')

        (self.fixture_dir / "fixture.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def problems(self) -> list[str]:
        return validate.validate(self.root)[0]

    def assert_problem(self, fragment: str) -> None:
        probs = self.problems()
        self.assertTrue(
            any(fragment in p for p in probs),
            f"Expected diagnostic fragment {fragment!r} not found in problems: {probs}",
        )

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_comparison_table_covers_all_twelve_keys(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        for key in ALL_TWELVE_KEYS:
            pattern = re.compile(rf"\|\s*`{re.escape(key)}`\s*\|")
            self.assertTrue(
                pattern.search(content),
                f"Key {key!r} must be documented in comparison table",
            )

    def test_clean_fixture_passes_validation(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_key_schema_version_contradiction_fails(self) -> None:
        self.write_fixture({"schema_version": 2})
        self.assert_problem("schema_version 2, this tool reads 1")

    def test_key_id_contradiction_fails(self) -> None:
        self.write_fixture({"id": "wrong-id"})
        self.assert_problem("does not match its directory name")

    def test_key_kind_contradiction_fails(self) -> None:
        self.write_fixture({"kind": "synthetic", "scenario": "synthetic: a plain synthetic"})
        self.assert_problem("synthetic fixture carries provenance it cannot have: captured_at")

    def test_key_scenario_contradiction_fails(self) -> None:
        self.write_fixture({"scenario": "an account with 100 sponsorships"})
        self.assert_problem("scenario must not contain numeric counts; describe intent in plain words")

    def test_key_account_id_contradiction_fails(self) -> None:
        self.write_fixture({"account_id": PEER_ID})
        self.assert_problem(f"account.json describes {ACCOUNT_ID!r}, sidecar says {PEER_ID!r}")

    def test_key_network_contradiction_fails(self) -> None:
        self.write_fixture({"network": "testnet"})
        self.assert_problem("should be 'https://horizon-testnet.stellar.org/accounts/")

    def test_key_shape_contradiction_fails(self) -> None:
        self.write_fixture({"shape": ["not_sponsored", "thresholds_nonzero"]})
        self.assert_problem("declared shape 'thresholds_nonzero' is not what account.json shows")

    def test_key_source_url_contradiction_fails(self) -> None:
        self.write_fixture({"source_url": "https://horizon.stellar.org/accounts/GA_WRONG"})
        self.assert_problem("should be 'https://horizon.stellar.org/accounts/")

    def test_key_captured_at_contradiction_fails(self) -> None:
        future_time = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.write_fixture({"captured_at": future_time})
        self.assert_problem(f"captured_at {future_time} is in the future")

    def test_key_ledger_contradiction_fails(self) -> None:
        self.write_fixture({"ledger": 500})
        self.assert_problem("sidecar ledger 500 predates last_modified_ledger 1000")

    def test_key_horizon_version_contradiction_fails(self) -> None:
        self.write_fixture({"horizon_version": ""})
        self.assert_problem("horizon_version is empty; the capture must say what served it")

    def test_key_sha256_contradiction_fails(self) -> None:
        self.write_fixture({"sha256": "0" * 64})
        self.assert_problem("sha256 does not match account.json")


if __name__ == "__main__":
    unittest.main()
