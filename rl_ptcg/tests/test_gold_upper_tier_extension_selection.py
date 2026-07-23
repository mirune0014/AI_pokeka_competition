import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_oracle_states import canonical_sha256, file_sha256
from rl_ptcg.gold_upper_tier_extension_selection import (
    _self_hash,
    verify_upper_tier_extension_selection,
    write_upper_tier_extension_selection,
)


class UpperTierExtensionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[2]
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        self.reference = self.root / "reference"
        self.expanded = self.root / "expanded"
        self.audit = self.root / "audit.json"
        self.output = self.root / "selection.json"
        reference = [self.state("reference", 0, 1, "target", 2, 1)]
        expanded = reference + [
            self.state("later", 1, 4, "target", 3, 2),
            self.state("earlier", 0, 9, "target", 2, 3),
            self.state("other", 0, 2, "other", 4, 1),
        ]
        self.write_corpus(self.reference, reference)
        self.write_corpus(self.expanded, expanded)
        self.write_audit()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def state(episode, seat, step, archetype, candidates, hypotheses):
        return {
            "state_id": "%s-%s-%s" % (episode, seat, step),
            "episode_id": episode,
            "acting_seat": seat,
            "replay_step": step,
            "belief": {"archetype": archetype, "hypotheses": [{} for _ in range(hypotheses)]},
            "candidate_sets": {"rule_diverse": [{} for _ in range(candidates)]},
        }

    @staticmethod
    def write_corpus(path, states):
        path.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "synthetic"}
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        (path / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="ascii")
        (path / "selection_manifest.json").write_text('{"synthetic":true}\n', encoding="ascii")
        (path / "states.jsonl").write_bytes(b"".join(
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
            for state in states
        ))

    def binding(self, path):
        manifest = json.loads((path / "manifest.json").read_text(encoding="ascii"))
        return {
            "path": str(path.relative_to(self.workspace)).replace("\\", "/"),
            "manifest_file_sha256": file_sha256(path / "manifest.json"),
            "manifest_sha256": manifest["manifest_sha256"],
            "selection_manifest_file_sha256": file_sha256(path / "selection_manifest.json"),
            "states_file_sha256": file_sha256(path / "states.jsonl"),
            "verified": {"verified": True},
        }

    def write_audit(self):
        audit = {
            "schema_version": "gold_upper_tier_allroots_audit.v1",
            "reference_corpus": self.binding(self.reference),
            "expanded_corpus": self.binding(self.expanded),
        }
        audit["manifest_sha256"] = canonical_sha256(audit)
        self.audit.write_text(json.dumps(audit, sort_keys=True) + "\n", encoding="ascii")

    def write(self):
        with patch("rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit", return_value={"verified": True}):
            return write_upper_tier_extension_selection(self.audit, "target", self.output, self.workspace, opponent_heads=4)

    def test_deterministic_success_filters_and_excludes_reference(self):
        result = self.write()
        self.assertTrue(result["verified"])
        value = json.loads(self.output.read_text(encoding="ascii"))
        self.assertEqual(["earlier-0-9", "later-1-4"], value["selected_state_ids"])
        self.assertEqual([["earlier", 0, 9], ["later", 1, 4]], value["selected_state_specs"])
        self.assertEqual({"2": 1, "3": 1}, value["distributions"]["candidate_count"])
        self.assertEqual({"2": 1, "3": 1}, value["distributions"]["hypothesis_count"])
        self.assertEqual(48, value["estimated_p1_rows"])
        self.assertEqual("rule_diverse", value["selection_criteria"]["candidate_set"])
        self.assertTrue(value["selection_criteria"]["terminal_signals_forbidden"])
        self.assertNotIn("reference-0-1", value["selected_state_ids"])

    def test_rejects_empty_and_duplicate_selection_inputs(self):
        with patch("rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit", return_value={"verified": True}):
            with self.assertRaisesRegex(ValueError, "selection is empty"):
                write_upper_tier_extension_selection(self.audit, "missing", self.output, self.workspace)
        rows = [json.loads(line) for line in (self.expanded / "states.jsonl").read_text(encoding="ascii").splitlines()]
        rows.append(dict(rows[-1]))
        self.write_corpus(self.expanded, rows)
        self.write_audit()
        with patch("rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit", return_value={"verified": True}):
            with self.assertRaisesRegex(ValueError, "duplicate state ID"):
                write_upper_tier_extension_selection(self.audit, "target", self.output, self.workspace)
        rows[-1]["state_id"] = "distinct-state-id"
        self.write_corpus(self.expanded, rows)
        self.write_audit()
        with patch("rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit", return_value={"verified": True}):
            with self.assertRaisesRegex(ValueError, "duplicate state spec"):
                write_upper_tier_extension_selection(self.audit, "target", self.output, self.workspace)

    def test_uses_the_bound_allroots_audit_cli(self):
        with patch(
            "rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit",
            return_value={"verified": True},
        ) as verify:
            write_upper_tier_extension_selection(self.audit, "target", self.output, self.workspace)
        self.assertEqual(
            (self.workspace / "tools" / "build_gold_upper_tier_allroots_audit.py").resolve(),
            verify.call_args.args[2],
        )

    def test_verify_recomputes_and_rejects_self_hashed_drift(self):
        self.write()
        value = json.loads(self.output.read_text(encoding="ascii"))
        value["counts"]["selected_states"] = 99
        value["manifest_sha256"] = _self_hash(value)
        self.output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="ascii")
        with patch("rl_ptcg.gold_upper_tier_extension_selection.verify_allroots_audit", return_value={"verified": True}):
            with self.assertRaisesRegex(ValueError, "does not reproduce"):
                verify_upper_tier_extension_selection(self.output, self.workspace)


if __name__ == "__main__":
    unittest.main()
