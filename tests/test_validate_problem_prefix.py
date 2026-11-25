#!/usr/bin/env python3
"""Pin the fixtures/<name> prefix requirement for all fixture-level problem messages."""

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


class TestValidateProblemPrefix(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="problem-prefix-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name)
        (self.root / "corpus").mkdir(parents=True, exist_ok=True)
        write_root_public(self.root / "corpus")
        self.fixtures_dir = self.root / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def write_valid_captured_fixture(self, name: str, seed_byte: int) -> Path:
        fixture_dir = self.fixtures_dir / name
        fixture_dir.mkdir(parents=True, exist_ok=True)
        account_id = generate_account_id(seed_byte)
        account: dict[str, object] = {
            "account_id": account_id,
            "sequence": "1",
            "balances": [],
            "signers": [{"key": account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
        }
        body_bytes = (json.dumps(account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (fixture_dir / "account.json").write_bytes(body_bytes)
        sha256 = hashlib.sha256(body_bytes).hexdigest()
        labels = "".join(f'  "{label}",\n' for label in sorted(validate.shapes_of(account)))
        manifest = (
            "schema_version = 1\n"
            f'id = "{name}"\n'
            'kind = "captured"\n'
            'scenario = "problem prefix test specimen"\n'
            f'account_id = "{account_id}"\n'
            'network = "public"\n'
            f'source_url = "https://horizon.stellar.org/accounts/{account_id}"\n'
            'captured_at = "2026-11-24T00:00:00Z"\n'
            "last_modified_ledger = 100\n"
            'horizon_version = "30.0.0"\n'
            f'sha256 = "{sha256}"\n'
            "shape = [\n"
            f"{labels}"
            "]\n"
        )
        (fixture_dir / "fixture.toml").write_text(manifest, encoding="utf-8")
        return fixture_dir

    def test_missing_files_prefix(self) -> None:
        name_body = "missing-body"
        dir_body = self.fixtures_dir / name_body
        dir_body.mkdir(parents=True, exist_ok=True)
        (dir_body / "fixture.toml").write_text("schema_version = 1\n", encoding="utf-8")

        name_manifest = "missing-manifest"
        dir_manifest = self.fixtures_dir / name_manifest
        dir_manifest.mkdir(parents=True, exist_ok=True)
        (dir_manifest / "account.json").write_text("{}\n", encoding="utf-8")

        problems, _ = validate.validate(self.root)
        self.assertGreater(len(problems), 0)

        for name in (name_body, name_manifest):
            fixture_problems = [p for p in problems if f"/{name}:" in p]
            self.assertGreater(len(fixture_problems), 0)
            for problem in fixture_problems:
                self.assertTrue(
                    problem.startswith(f"fixtures/{name}: "),
                    f"problem {problem!r} does not start with fixtures/{name}: ",
                )

    def test_extra_files_prefix(self) -> None:
        name = "extra-file"
        fixture_dir = self.write_valid_captured_fixture(name, 10)
        (fixture_dir / "unexpected.txt").write_text("stray file\n", encoding="utf-8")

        problems, _ = validate.validate(self.root)
        fixture_problems = [p for p in problems if f"/{name}:" in p]
        self.assertGreater(len(fixture_problems), 0)
        for problem in fixture_problems:
            self.assertTrue(
                problem.startswith(f"fixtures/{name}: "),
                f"problem {problem!r} does not start with fixtures/{name}: ",
            )
        self.assertTrue(any("unexpected file(s): unexpected.txt" in p for p in fixture_problems))

    def test_digest_mismatch_prefix(self) -> None:
        name = "digest-mismatch"
        fixture_dir = self.write_valid_captured_fixture(name, 20)
        (fixture_dir / "account.json").write_text('{\n  "corrupted": true\n}\n', encoding="utf-8")

        problems, _ = validate.validate(self.root)
        fixture_problems = [p for p in problems if f"/{name}:" in p]
        self.assertGreater(len(fixture_problems), 0)
        for problem in fixture_problems:
            self.assertTrue(
                problem.startswith(f"fixtures/{name}: "),
                f"problem {problem!r} does not start with fixtures/{name}: ",
            )
        self.assertTrue(any("sha256 does not match" in p for p in fixture_problems))

    def test_malformed_toml_manifest_prefix(self) -> None:
        name = "malformed-toml"
        fixture_dir = self.fixtures_dir / name
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "account.json").write_text("{}\n", encoding="utf-8")
        (fixture_dir / "fixture.toml").write_text("[[bad syntax unclosed", encoding="utf-8")

        problems, _ = validate.validate(self.root)
        fixture_problems = [p for p in problems if f"/{name}:" in p]
        self.assertGreater(len(fixture_problems), 0)
        for problem in fixture_problems:
            self.assertTrue(
                problem.startswith(f"fixtures/{name}: "),
                f"problem {problem!r} does not start with fixtures/{name}: ",
            )
        self.assertTrue(any("sidecar is not valid TOML:" in p for p in fixture_problems))

    def test_all_fixture_failure_modes_retain_exact_directory_prefix(self) -> None:
        f_missing = self.fixtures_dir / "mode-missing"
        f_missing.mkdir(parents=True, exist_ok=True)
        (f_missing / "fixture.toml").write_text("schema_version = 1\n", encoding="utf-8")

        f_extra = self.write_valid_captured_fixture("mode-extra", 30)
        (f_extra / "stray.log").write_text("log\n", encoding="utf-8")

        f_digest = self.write_valid_captured_fixture("mode-digest", 40)
        (f_digest / "account.json").write_bytes(b'{"mutated": true}\n')

        f_toml = self.fixtures_dir / "mode-toml"
        f_toml.mkdir(parents=True, exist_ok=True)
        (f_toml / "account.json").write_text("{}\n", encoding="utf-8")
        (f_toml / "fixture.toml").write_text("key = [broken\n", encoding="utf-8")

        problems, _ = validate.validate(self.root)
        self.assertGreaterEqual(len(problems), 4)

        for problem in problems:
            self.assertTrue(
                problem.startswith("fixtures/"),
                f"problem {problem!r} does not start with 'fixtures/'",
            )
            prefix = problem.split(":")[0]
            self.assertTrue(
                prefix.startswith("fixtures/mode-"),
                f"prefix {prefix!r} does not identify fixture directory",
            )


if __name__ == "__main__":
    unittest.main()
