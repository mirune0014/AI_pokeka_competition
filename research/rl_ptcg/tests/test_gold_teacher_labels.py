from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from research.rl_ptcg.gold_oracle_states import canonical_sha256
from research.rl_ptcg.gold_teacher_labels import build_teacher_labels


def option(card: str) -> dict:
    return {"action_type": "play", "selection_context": "choose", "source_card_id": card,
            "source_zone": "hand", "source_relation": "self", "target_card_id": None}


def semantic_id(value: dict) -> str:
    from hashlib import blake2b
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return blake2b(raw, digest_size=32).hexdigest()


class GoldTeacherLabelsTest(unittest.TestCase):
    def _fixture(self, root: Path, *, split: str = "train", action: str | None = None) -> tuple[Path, Path, Path]:
        corpus, oracle, output = root / "corpus", root / "oracle", root / "labels"
        corpus.mkdir(parents=True); oracle.mkdir()
        left, right = option("a"), option("b")
        canonical = {"selection_context": "choose", "minimum_count": 1, "maximum_count": 1, "selections": [left]}
        oracle_action = semantic_id(canonical)
        state = {"state_id": "s1", "decision_id": "d1", "split": split,
                 "legal_semantic_options": [left, right],
                 "candidates": [{"semantic_id": oracle_action, "canonical": canonical}],
                 "current_metadata": {"own_archetype": "arch"},
                 "own_deck": {"decklist": [1] * 60, "sha256": canonical_sha256([1] * 60)}}
        (corpus / "states.jsonl").write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
        (corpus / "manifest.json").write_text(
            '{"schema_version":"gold_oracle_states.v1"}\n', encoding="ascii",
        )
        (corpus / "selection_manifest.json").write_text("{}\n", encoding="ascii")
        binding = {"path": "corpus", "selection_manifest_sha256": sha256((corpus / "selection_manifest.json").read_bytes()).hexdigest(),
                   "states_sha256": sha256((corpus / "states.jsonl").read_bytes()).hexdigest(),
                   "manifest_sha256": sha256((corpus / "manifest.json").read_bytes()).hexdigest()}
        run = {"manifest_sha256": "runhash", "corpus": binding}
        report = {"manifest_sha256": "reporthash", "run_manifest_sha256": "runhash",
                  "posterior_weighted_teacher_statistics": {"stable_labels": [{"state_id": "s1", "action": action or oracle_action, "batch_ids": [0, 1]}]}}
        (oracle / "run_manifest.json").write_text(json.dumps(run, sort_keys=True) + "\n", encoding="ascii")
        (oracle / "report.json").write_text(json.dumps(report, sort_keys=True) + "\n", encoding="ascii")
        return corpus, oracle, output

    def _build(self, corpus: Path, oracle: Path, output: Path, *, oracle_verified=None, receipt_result=None, **kwargs) -> dict:
        verified = oracle_verified or {"complete": True, "report_recomputed": True}
        with patch("research.rl_ptcg.gold_teacher_labels.verify_oracle_output", return_value=verified), \
             patch("research.rl_ptcg.gold_teacher_labels.verify_gold_oracle_states", return_value={}), \
             patch("research.rl_ptcg.gold_teacher_labels.verify_kaggle_rollout_source_receipt", return_value=receipt_result), \
             patch("research.rl_ptcg.gold_teacher_labels.verify_teacher_labels", return_value={"labels": 1}):
            return build_teacher_labels(corpus, oracle, output, workspace_root=corpus.parent, **kwargs)

    def test_reproducible_and_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, oracle, output = self._fixture(Path(directory))
            self._build(corpus, oracle, output)
            first = (output / "labels.jsonl").read_bytes()
            self._build(corpus, oracle, output)
            self.assertEqual(first, (output / "labels.jsonl").read_bytes())
            (output / "labels.jsonl").write_bytes(b'{"tampered":true}\n')
            with self.assertRaises(FileExistsError):
                self._build(corpus, oracle, output)

    def test_rejects_empty_stable_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, oracle, output = self._fixture(Path(directory))
            (oracle / "report.json").write_text(json.dumps({"manifest_sha256": "reporthash", "run_manifest_sha256": "runhash", "posterior_weighted_teacher_statistics": {"stable_labels": []}}) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                self._build(corpus, oracle, output)

    def test_rejects_illegal_or_blind_or_duplicate_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, oracle, output = self._fixture(root, action="not-legal")
            with self.assertRaisesRegex(ValueError, "stable label"):
                self._build(corpus, oracle, output)
            corpus, oracle, output = self._fixture(root / "blind", split="blind")
            with self.assertRaisesRegex(ValueError, "blind"):
                self._build(corpus, oracle, output)
            corpus, oracle, output = self._fixture(root / "duplicate")
            report_path = oracle / "report.json"
            report = json.loads(report_path.read_text(encoding="ascii"))
            report["posterior_weighted_teacher_statistics"]["stable_labels"].append(copy.deepcopy(report["posterior_weighted_teacher_statistics"]["stable_labels"][0]))
            report_path.write_text(json.dumps(report) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                self._build(corpus, oracle, output)

    def test_rejects_corpus_hash_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, oracle, output = self._fixture(Path(directory))
            run = json.loads((oracle / "run_manifest.json").read_text(encoding="ascii"))
            run["corpus"]["states_sha256"] = "0" * 64
            (oracle / "run_manifest.json").write_text(json.dumps(run) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "hash binding drift"):
                self._build(corpus, oracle, output)

    def test_rejects_target_actor_applicability_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, oracle, output = self._fixture(Path(directory))
            with self.assertRaisesRegex(ValueError, "applicability drift"):
                self._build(corpus, oracle, output, target_archetype="other_arch")

    def test_target_deck_requires_exact_valid_actor_deck_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, oracle, output = self._fixture(root)
            target = root / "target_deck.csv"
            target.write_text("".join("1\n" for _ in range(60)), encoding="ascii")
            self._build(corpus, oracle, output, target_deck_path=target)
            corpus, oracle, output = self._fixture(root / "mismatch")
            target = root / "mismatch" / "target_deck.csv"
            target.write_text("".join("2\n" for _ in range(60)), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "target deck/actor"):
                self._build(corpus, oracle, output, target_deck_path=target)
            corpus, oracle, output = self._fixture(root / "missing")
            state_path = corpus / "states.jsonl"
            state = json.loads(state_path.read_text(encoding="ascii"))
            del state["own_deck"]
            state_path.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
            run_path = oracle / "run_manifest.json"
            run = json.loads(run_path.read_text(encoding="ascii"))
            run["corpus"]["states_sha256"] = sha256(state_path.read_bytes()).hexdigest()
            run_path.write_text(json.dumps(run) + "\n", encoding="ascii")
            target = root / "missing" / "target_deck.csv"
            target.write_text("".join("1\n" for _ in range(60)), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "actor deck"):
                self._build(corpus, oracle, output, target_deck_path=target)

    def test_target_archetype_requires_present_exact_source_archetype(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, oracle, output = self._fixture(Path(directory))
            state_path = corpus / "states.jsonl"
            state = json.loads(state_path.read_text(encoding="ascii"))
            state["current_metadata"] = {}
            state_path.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
            run_path = oracle / "run_manifest.json"
            run = json.loads(run_path.read_text(encoding="ascii"))
            run["corpus"]["states_sha256"] = sha256(state_path.read_bytes()).hexdigest()
            run_path.write_text(json.dumps(run) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "archetype/actor"):
                self._build(corpus, oracle, output, target_archetype="arch")

    def test_runtime_drift_requires_matching_source_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus, oracle, output = self._fixture(root)
            drifted = {"complete": True, "report_recomputed": False}
            with self.assertRaisesRegex(ValueError, "source receipt"):
                self._build(corpus, oracle, output, oracle_verified=drifted)
            receipt = root / "receipt.json"; receipt.write_text("{}\n", encoding="ascii")
            matching = {"manifest_sha256": "receipt", "run_output": str(oracle.resolve()),
                        "run_manifest_sha256": "runhash", "report_manifest_sha256": "reporthash"}
            self._build(corpus, oracle, output, oracle_verified=drifted,
                        source_receipt_path=receipt, receipt_result=matching)
            mismatched = dict(matching); mismatched["run_manifest_sha256"] = "other"
            with self.assertRaisesRegex(ValueError, "does not bind"):
                self._build(corpus, oracle, root / "mismatch_labels", oracle_verified=drifted,
                            source_receipt_path=receipt, receipt_result=mismatched)

    def test_nested_source_workspace_is_bound_separately_from_audit_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source_workspace = workspace / "download" / "ptcg_gold_workspace"
            corpus, oracle, _unused = self._fixture(source_workspace)
            output = workspace  / "_local_generated" / "analysis_outputs" / "labels"
            with patch(
                "research.rl_ptcg.gold_teacher_labels.verify_oracle_output",
                return_value={"complete": True, "report_recomputed": True},
            ) as verify_oracle, patch(
                "research.rl_ptcg.gold_teacher_labels.verify_gold_oracle_states",
                return_value={},
            ) as verify_states, patch(
                "research.rl_ptcg.gold_teacher_labels.verify_teacher_labels",
                return_value={"labels": 1},
            ):
                build_teacher_labels(
                    "corpus", "oracle", output,
                    workspace_root=workspace,
                    source_workspace_root=source_workspace,
                )
            verify_oracle.assert_called_once_with(oracle.resolve(), source_workspace.resolve())
            verify_states.assert_called_once_with(corpus.resolve(), source_workspace.resolve())
            manifest = json.loads((output / "manifest.json").read_text(encoding="ascii"))
            self.assertEqual("download/ptcg_gold_workspace", manifest["source_workspace_path"])
            self.assertEqual(
                "download/ptcg_gold_workspace/corpus/states.jsonl",
                manifest["inputs"]["corpus_states"]["path"],
            )

    def test_teacher_split_overrides_source_split_and_binds_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus, oracle, output = self._fixture(root)
            split_path = root / "teacher_split.json"
            split_path.write_text(json.dumps({
                "items": [{"decision_id": "d1", "state_id": "s1", "split": "train"}],
            }) + "\n", encoding="ascii")
            verified = {"states": 1, "manifest_sha256": "split-hash"}
            with patch(
                "research.rl_ptcg.gold_teacher_labels.verify_teacher_state_split",
                return_value=verified,
            ):
                self._build(corpus, oracle, output, teacher_split_path=split_path)
            row = json.loads((output / "labels.jsonl").read_text(encoding="ascii"))
            manifest = json.loads((output / "manifest.json").read_text(encoding="ascii"))
            self.assertEqual("train", row["split"])
            self.assertEqual("split-hash", manifest["inputs"]["teacher_split"]["manifest_sha256"])
            split_path.write_text(json.dumps({
                "items": [{"decision_id": "d1", "state_id": "other", "split": "train"}],
            }) + "\n", encoding="ascii")
            with patch(
                "research.rl_ptcg.gold_teacher_labels.verify_teacher_state_split",
                return_value=verified,
            ):
                with self.assertRaisesRegex(ValueError, "does not bind"):
                    self._build(corpus, oracle, root / "mismatch", teacher_split_path=split_path)

    def test_cli_is_available_as_a_subprocess(self):
        root = Path(__file__).resolve().parents[3]
        result = subprocess.run([sys.executable, "infrastructure/tools/build_gold_teacher_labels.py", "--help"], cwd=root,
                                capture_output=True, text=True, check=True)
        self.assertIn("--verify-only", result.stdout)
        self.assertIn("--source-workspace-root", result.stdout)
        self.assertIn("--teacher-split", result.stdout)


if __name__ == "__main__":
    unittest.main()
