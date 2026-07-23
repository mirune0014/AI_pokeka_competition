from __future__ import annotations

from hashlib import blake2b, sha256
import json
from pathlib import Path
import tempfile
import unittest

from rl_ptcg.gold_disagreement_verify import verify_gold_disagreement_audit


def _json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


class GoldDisagreementVerifyTests(unittest.TestCase):
    def _fixture(self, root):
        root = Path(root)
        output, dataset, workspace = root / "audit", root / "dataset", root / "workspace"
        output.mkdir(); dataset.mkdir(); workspace.mkdir()
        (dataset / "dataset_manifest.json").write_text("{\"dataset\":true}\n", encoding="ascii")
        (dataset / "split_manifest.json").write_text("{\"split\":true}\n", encoding="ascii")
        agent = workspace / "agent"; agent.mkdir()
        (agent / "main.py").write_text("x = 1\n", encoding="ascii")
        (agent / "deck.csv").write_text("card,count\na,1\n", encoding="ascii")
        implementation = workspace / "rl_ptcg" / "module.py"; implementation.parent.mkdir()
        implementation.write_text("VALUE = 1\n", encoding="ascii")
        baseline_map = {"*": "agent"}
        sample = {"schema_version": "gold_disagreement_audit.v1", "source_splits": ["train"], "seed": "0", "target_count": 1,
                  "dataset_sha256": "a" * 64, "split_manifest_sha256": "b" * 64, "baseline_map_canonical_sha256": sha256(_json(baseline_map)).hexdigest(),
                  "strata": ["neutral"], "quotas": {"selected": 1}, "decision_ids": ["d1"]}
        sample["manifest_blake2b"] = blake2b(_json(sample), digest_size=32).hexdigest()
        sample["manifest_sha256"] = sha256(_json(sample)).hexdigest()
        (output / "sample_manifest.json").write_bytes(_json(sample))
        rows = _json({"decision_id": "d1", "rule_rank_available": False})
        (output / "rows.jsonl").write_bytes(rows)
        report = {"schema_version": "gold_disagreement_audit.v1", "rows": 1, "errors": {}, "truncated": 0,
                  "overall": {"errors": 0, "unranked_count": 1}, "sample_manifest_blake2b": sample["manifest_blake2b"], "rows_sha256": sha256(rows).hexdigest()}
        (output / "report.json").write_bytes(_json(report))
        binding = {"schema_version": "gold_disagreement_audit.v1", "sample_manifest_sha256": _hash(output / "sample_manifest.json"),
                   "rows_sha256": _hash(output / "rows.jsonl"), "report_sha256": _hash(output / "report.json"),
                   "dataset_manifest_sha256": _hash(dataset / "dataset_manifest.json"), "split_manifest_sha256": _hash(dataset / "split_manifest.json"),
                   "baseline_map_canonical_sha256": sha256(_json(baseline_map)).hexdigest(),
                   "baseline_files": {"*": {"main.py": _hash(agent / "main.py"), "deck.csv": _hash(agent / "deck.csv")}},
                   "implementation_files_sha256": {"rl_ptcg/module.py": _hash(implementation)}, "python": "test", "platform": "test", "command": [], "config": {}}
        binding["manifest_blake2b"] = blake2b(_json(binding), digest_size=32).hexdigest()
        (output / "checksum_manifest.json").write_bytes(_json(binding))
        return output, dataset, workspace, baseline_map

    def test_valid_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            output, dataset, workspace, mapping = self._fixture(directory)
            self.assertEqual({"sampled": 1, "rows": 1, "errors": 0, "unranked": 1, "truncated": 0, "output_dir": str(output.resolve())},
                             verify_gold_disagreement_audit(output, dataset, mapping, workspace))

    def test_rows_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, dataset, workspace, mapping = self._fixture(directory)
            (output / "rows.jsonl").write_text('{"decision_id":"other"}\n', encoding="ascii")
            with self.assertRaises(ValueError):
                verify_gold_disagreement_audit(output, dataset, mapping, workspace)

    def test_blind_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, dataset, workspace, mapping = self._fixture(directory)
            sample = json.loads((output / "sample_manifest.json").read_text(encoding="ascii"))
            sample["source_splits"] = ["blind"]
            (output / "sample_manifest.json").write_bytes(_json(sample))
            with self.assertRaises(ValueError):
                verify_gold_disagreement_audit(output, dataset, mapping, workspace)

    def test_implementation_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, dataset, workspace, mapping = self._fixture(directory)
            binding = json.loads((output / "checksum_manifest.json").read_text(encoding="ascii"))
            binding["implementation_files_sha256"] = {"../outside.py": "a" * 64}
            unsigned = {key: value for key, value in binding.items() if key != "manifest_blake2b"}
            binding["manifest_blake2b"] = blake2b(_json(unsigned), digest_size=32).hexdigest()
            (output / "checksum_manifest.json").write_bytes(_json(binding))
            with self.assertRaises(ValueError):
                verify_gold_disagreement_audit(output, dataset, mapping, workspace)


if __name__ == "__main__":
    unittest.main()
