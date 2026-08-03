import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.rl_ptcg.gold_oracle_states import canonical_sha256
from research.rl_ptcg.gold_upper_tier_allroots_audit import (
    _self_hash,
    build_allroots_audit,
    verify_allroots_audit,
    write_allroots_audit,
)


class AllRootsAuditTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[3]
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        self.screen = self.root / "screen.json"
        self.reference = self.root / "reference"
        self.expanded = self.root / "expanded"
        self.output = self.root / "audit.json"
        self.cli = self.root / "audit_cli.py"
        self.cli.write_text("# synthetic cli\n", encoding="ascii")
        specs = [("episode", 0, step) for step in range(86)]
        screen = {
            "schema_version": "synthetic.screen",
            "base_state_specs": [list(item) for item in specs[:5]],
            "candidate_pool": [
                {"episode_id": episode, "acting_seat": seat, "replay_step": step}
                for episode, seat, step in specs[5:]
            ],
        }
        screen["manifest_sha256"] = canonical_sha256(screen)
        self.screen.write_text(json.dumps(screen, sort_keys=True) + "\n", encoding="ascii")
        reference_rows = [self.state(*item) for item in specs[:23]]
        self.write_corpus(self.reference, reference_rows)
        self.write_corpus(self.expanded, reference_rows + [self.state(*item) for item in specs[23:]])

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def state(episode, seat, step):
        return {
            "episode_id": episode,
            "acting_seat": seat,
            "replay_step": step,
            "state_id": "state-%03d" % step,
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
        with patch("research.rl_ptcg.gold_upper_tier_allroots_audit.verify_screen", return_value={"verified": True}), patch(
            "research.rl_ptcg.gold_upper_tier_allroots_audit.verify_gold_upper_tier_states", return_value={"verified": True},
        ):
            return build_allroots_audit(self.screen, self.reference, self.expanded, self.workspace, self.cli)

    def test_success_and_write_once_verification(self):
        with patch("research.rl_ptcg.gold_upper_tier_allroots_audit.verify_screen", return_value={"verified": True}), patch(
            "research.rl_ptcg.gold_upper_tier_allroots_audit.verify_gold_upper_tier_states", return_value={"verified": True},
        ):
            result = write_allroots_audit(self.screen, self.reference, self.expanded, self.output, self.workspace, self.cli)
        self.assertTrue(result["verified"])
        self.assertEqual(86, result["expanded_states"])

    def test_screen_verifier_uses_original_screen_cli_binding(self):
        with patch(
            "research.rl_ptcg.gold_upper_tier_allroots_audit.verify_screen",
            return_value={"verified": True},
        ) as verify, patch(
            "research.rl_ptcg.gold_upper_tier_allroots_audit.verify_gold_upper_tier_states",
            return_value={"verified": True},
        ):
            build_allroots_audit(
                self.screen, self.reference, self.expanded, self.workspace, self.cli,
            )
        self.assertEqual(
            (self.workspace / "infrastructure" / "tools" / "build_gold_upper_tier_screen.py").resolve(),
            verify.call_args.args[2],
        )

    def test_rejects_missing_or_extra_screen_spec(self):
        screen = json.loads(self.screen.read_text(encoding="ascii"))
        screen["candidate_pool"].pop()
        self.screen.write_text(json.dumps(screen, sort_keys=True) + "\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "specs do not exactly"):
            self.build()
        screen["candidate_pool"].append({"episode_id": "extra", "acting_seat": 0, "replay_step": 99})
        self.screen.write_text(json.dumps(screen, sort_keys=True) + "\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "specs do not exactly"):
            self.build()

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

    def test_rejects_self_hash_valid_nonreproducible_audit(self):
        value = self.build()
        self.output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="ascii")
        value["counts"]["expanded_states"] = 85
        value["manifest_sha256"] = _self_hash(value)
        self.output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="ascii")
        with patch("research.rl_ptcg.gold_upper_tier_allroots_audit.verify_screen", return_value={"verified": True}), patch(
            "research.rl_ptcg.gold_upper_tier_allroots_audit.verify_gold_upper_tier_states", return_value={"verified": True},
        ):
            with self.assertRaisesRegex(ValueError, "does not reproduce"):
                verify_allroots_audit(self.output, self.workspace, self.cli)


if __name__ == "__main__":
    unittest.main()
