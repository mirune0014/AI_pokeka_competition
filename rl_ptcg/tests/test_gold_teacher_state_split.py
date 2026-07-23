from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_oracle_states import canonical_sha256
from rl_ptcg.gold_teacher_state_split import (
    verify_teacher_state_split,
    write_teacher_state_split,
)


class GoldTeacherStateSplitTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        corpus = root / "corpus"
        corpus.mkdir()
        states = [
            {"state_id": "s1", "decision_id": "d1", "episode_id": "e1", "split": "development",
             "current_metadata": {"opponent_archetype": "marnie"}},
            {"state_id": "s2", "decision_id": "d2", "episode_id": "e2", "split": "development",
             "current_metadata": {"opponent_archetype": "alakazam"}},
        ]
        (corpus / "states.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in states), encoding="ascii",
        )
        manifest = {"schema_version": "gold_upper_tier_states.v2"}
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        (corpus / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="ascii")
        (corpus / "selection_manifest.json").write_text("{}\n", encoding="ascii")
        return corpus

    def write(self, corpus: Path, output: Path, assignments=None):
        with patch("rl_ptcg.gold_teacher_state_split.verify_gold_upper_tier_states", return_value={}):
            return write_teacher_state_split(
                corpus, assignments or {"e1": "train", "e2": "development"},
                output, corpus.parent,
            )

    def test_success_is_grouped_reproducible_and_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.fixture(root); output = root / "split.json"
            result = self.write(corpus, output)
            self.assertTrue(result["verified"])
            self.assertEqual({"d1": "train", "d2": "development"}, result["split_by_decision_id"])
            value = json.loads(output.read_text(encoding="ascii"))
            self.assertEqual(["episode_id"], value["assignment_policy"]["allowed_signals"])
            self.assertFalse(value["assignment_policy"]["blind_split_allowed"])
            self.write(corpus, output)

    def test_rejects_missing_invalid_or_blind_assignments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "cover the corpus exactly"):
                self.write(corpus, root / "missing.json", {"e1": "train"})
            with self.assertRaisesRegex(ValueError, "explicitly non-blind"):
                self.write(corpus, root / "blind.json", {"e1": "train", "e2": "blind"})
            rows = [json.loads(line) for line in (corpus / "states.jsonl").read_text().splitlines()]
            rows[1]["split"] = "blind"
            (corpus / "states.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "blind"):
                self.write(corpus, root / "source_blind.json")

    def test_verify_rejects_self_hashed_assignment_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.fixture(root); output = root / "split.json"
            self.write(corpus, output)
            value = json.loads(output.read_text(encoding="ascii"))
            value["counts"]["states"] = 99
            unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
            value["manifest_sha256"] = canonical_sha256(unsigned)
            output.write_text(json.dumps(value) + "\n", encoding="ascii")
            with patch("rl_ptcg.gold_teacher_state_split.verify_gold_upper_tier_states", return_value={}):
                with self.assertRaisesRegex(ValueError, "does not reproduce"):
                    verify_teacher_state_split(output, root)

    def test_cli_is_available(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "tools/build_gold_teacher_state_split.py", "--help"],
            cwd=root, capture_output=True, text=True, check=True,
        )
        self.assertIn("--episode-split", result.stdout)


if __name__ == "__main__":
    unittest.main()

