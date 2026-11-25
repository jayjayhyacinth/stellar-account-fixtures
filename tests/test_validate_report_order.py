#!/usr/bin/env python3
"""Ensure validator report line ordering is deterministic regardless of directory creation order."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_account_id(seed_byte: int) -> str:
    body = bytes([validate.VERSION_ACCOUNT]) + bytes([seed_byte] * 32)
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


FIXTURE_NAMES = ("alpha", "bravo", "charlie", "delta", "echo")
ACCOUNT_IDS = {name: generate_account_id(index + 1) for index, name in enumerate(FIXTURE_NAMES)}


def build_corpus(root: Path, creation_order: tuple[str, ...]) -> None:
    (root / "corpus").mkdir(parents=True, exist_ok=True)
    write_root_public(root / "corpus")
    for name in creation_order:
        account_id = ACCOUNT_IDS[name]
        fixture_dir = root / "fixtures" / name
        fixture_dir.mkdir(parents=True, exist_ok=True)
        account: dict[str, object] = {
            "account_id": account_id,
            "sequence": "1",
            "balances": [],
            "signers": [{"key": account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
        }
        (fixture_dir / "account.json").write_text(
            json.dumps(account, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        labels = "".join(f'  "{label}",\n' for label in sorted(validate.shapes_of(account)))
        (fixture_dir / "fixture.toml").write_text(
            "schema_version = 1\n"
            f'id = "{name}"\n'
            'kind = "synthetic"\n'
            'scenario = "synthetic: report line order stability specimen"\n'
            f'account_id = "{account_id}"\n'
            'network = "public"\n'
            "shape = [\n"
            f"{labels}"
            "]\n",
            encoding="utf-8",
        )


def write_root_public(corpus_dir: Path) -> None:
    """Write the public root document and the sha256 sidecar validate.py requires."""
    document = json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n"
    path = corpus_dir / "root-public.json"
    path.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(document.encode()).hexdigest()
    (corpus_dir / "root-public.toml").write_text(
        'url = "https://horizon.stellar.org/"\n'
        'captured_at = "2026-11-25T00:00:00Z"\n'
        f'sha256 = "{digest}"\n',
        encoding="utf-8",
    )


class TestValidateReportOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="report-order-test-")
        self.addCleanup(self.stage.cleanup)
        self.base = Path(self.stage.name)

    def test_reverse_creation_order_yields_identical_alphabetical_report(self) -> None:
        forward_dir = self.base / "forward"
        reverse_dir = self.base / "reverse"

        build_corpus(forward_dir, FIXTURE_NAMES)
        build_corpus(reverse_dir, tuple(reversed(FIXTURE_NAMES)))

        problems_fwd, report_fwd = validate.validate(forward_dir, report=True)
        problems_rev, report_rev = validate.validate(reverse_dir, report=True)

        self.assertEqual(problems_fwd, [])
        self.assertEqual(problems_rev, [])
        self.assertEqual(report_fwd, report_rev)

        reported_names = [line.split(":")[0].removeprefix("fixtures/") for line in report_rev]
        self.assertEqual(reported_names, list(FIXTURE_NAMES))
        self.assertEqual(reported_names, sorted(reported_names))

    def test_scrambled_creation_orders_yield_identical_alphabetical_reports(self) -> None:
        canonical_dir = self.base / "canonical"
        build_corpus(canonical_dir, FIXTURE_NAMES)
        problems_canonical, report_canonical = validate.validate(canonical_dir, report=True)
        self.assertEqual(problems_canonical, [])

        scrambled_orders = (
            ("charlie", "echo", "alpha", "delta", "bravo"),
            ("delta", "alpha", "echo", "bravo", "charlie"),
            ("bravo", "delta", "charlie", "alpha", "echo"),
            ("echo", "alpha", "bravo", "delta", "charlie"),
        )

        for idx, order in enumerate(scrambled_orders):
            test_dir = self.base / f"scrambled_{idx}"
            build_corpus(test_dir, order)
            problems, report = validate.validate(test_dir, report=True)

            self.assertEqual(problems, [], f"failed on scrambled order {order}")
            self.assertEqual(
                report,
                report_canonical,
                f"report lines diverged on order {order}",
            )
            reported_names = [line.split(":")[0].removeprefix("fixtures/") for line in report]
            self.assertEqual(reported_names, sorted(reported_names))


if __name__ == "__main__":
    unittest.main()
