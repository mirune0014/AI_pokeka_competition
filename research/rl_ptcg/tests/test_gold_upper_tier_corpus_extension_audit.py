import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.rl_ptcg.gold_upper_tier_corpus_extension_audit import (
    _self_hash,
    build_corpus_extension_audit,
    verify_corpus_extension_audit,
    write_corpus_extension_audit,
)


class CorpusExtensionAuditTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[3]
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        self.reference = self.root / "reference"
        self.expanded = self.root / "expanded"
        self.output = self.root / "audit.json"
        self.cli = self.root / "audit_cli.py"
        self.cli.write_text("# synthetic cli\n", encoding="ascii")
        self.expected = [("new", 0, 3), ("new", 0, 5)]
        reference_rows = [self.state("old", 0, 1), self.state("old", 0, 2)]
        self.write_corpus(self.reference, reference_rows)
        self.write_corpus(self.expanded, reference_rows + [self.state(*spec) for spec in self.expected])

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def state(episode, seat, step):
        return {
            "episode_id": episode,
            "acting_seat": seat,
            "replay_step": step,
            "state_id": "%s-%d-%d" % (episode, seat, step),
            "gold_incremental": False,
            "current_metadata": {"recorded_action_role": "provenance_only"},
            "candidate_sets": {"rule_diverse": ["rule"], "rule_plus_gold": ["rule"]},
            "candidates": [{"source_tags": ["rule_diverse", "rule_plus_gold"]}],
        }

    @staticmethod
    def write_corpus(path, rows):
        path.mkdir(parents=True, exist_ok=True)
        (path / "manifest.json").write_text('{"manifest_sha256":"manifest"}\n', encoding="ascii")
        (path / "selection_manifest.json").write_text('{"manifest_sha256":"selection"}\n', encoding="ascii")
        (path / "states.jsonl").write_bytes(b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
            for row in rows
        ))

    def build(self):
        with patch(
            "research.rl_ptcg.gold_upper_tier_corpus_extension_audit.verify_gold_upper_tier_states",
            return_value={"verified": True},
        ):
            return build_corpus_extension_audit(
                self.reference, self.expanded, self.expected, self.workspace, self.cli,
            )

    def test_success_and_write_once_verification(self):
        with patch(
            "research.rl_ptcg.gold_upper_tier_corpus_extension_audit.verify_gold_upper_tier_states",
            return_value={"verified": True},
        ):
            result = write_corpus_extension_audit(
                self.reference, self.expanded, self.expected, self.output, self.workspace, self.cli,
            )
        self.assertTrue(result["verified"])
        self.assertEqual(2, result["added_states"])

    def test_rejects_unexpected_addition(self):
        with self.assertRaisesRegex(ValueError, "do not match"):
            with patch(
                "research.rl_ptcg.gold_upper_tier_corpus_extension_audit.verify_gold_upper_tier_states",
                return_value={"verified": True},
            ):
                build_corpus_extension_audit(
                    self.reference, self.expanded, self.expected[:1], self.workspace, self.cli,
                )

    def test_rejects_shared_payload_drift(self):
        rows = [json.loads(line) for line in (self.expanded / "states.jsonl").read_text(encoding="ascii").splitlines()]
        rows[0]["drift"] = True
        self.write_corpus(self.expanded, rows)
        with self.assertRaisesRegex(ValueError, "shared reference state payload drift"):
            self.build()

    def test_rejects_direct_gold_contamination(self):
        rows = [json.loads(line) for line in (self.expanded / "states.jsonl").read_text(encoding="ascii").splitlines()]
        rows[-1]["candidates"][0]["source_tags"].append("direct_gold")
        self.write_corpus(self.expanded, rows)
        with self.assertRaisesRegex(ValueError, "forbidden Gold source tag"):
            self.build()

    def test_rejects_self_hashed_nonreproducible_audit(self):
        value = self.build()
        self.output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="ascii")
        value["counts"]["added_states"] = 1
        value["manifest_sha256"] = _self_hash(value)
        self.output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="ascii")
        with patch(
            "research.rl_ptcg.gold_upper_tier_corpus_extension_audit.verify_gold_upper_tier_states",
            return_value={"verified": True},
        ):
            with self.assertRaisesRegex(ValueError, "does not reproduce"):
                verify_corpus_extension_audit(self.output, self.workspace, self.cli)


if __name__ == "__main__":
    unittest.main()
