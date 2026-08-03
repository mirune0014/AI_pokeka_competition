from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.rl_ptcg.gold_teacher_advantages import (
    _aggregate_state,
    build_teacher_advantages,
    verify_teacher_advantages,
)
from research.rl_ptcg.gold_teacher_labels import _semantic_id


def complete(card_id: int) -> dict:
    return {
        "selection_context": 0,
        "minimum_count": 1,
        "maximum_count": 1,
        "selections": [{
            "action_type": 1,
            "source_card_id": card_id,
            "selection_context": 0,
        }],
    }


def action_stats(advantage: float) -> dict:
    return {
        "advantage_win_probability": advantage,
        "one_sided_lcb90_win_probability": advantage - 0.05,
        "cluster_standard_error_utility": 0.04,
        "probability_advantage_positive": 0.75 if advantage > 0 else 0.0,
        "opponent_group_advantages_utility": {
            "head-a": advantage * 2.0,
            "head-b": advantage * 1.5,
        },
    }


def fixture_values() -> tuple[dict, list[dict], dict]:
    baseline, teacher = complete(1), complete(2)
    baseline_id, teacher_id = _semantic_id(baseline), _semantic_id(teacher)
    state = {
        "state_id": "state-1",
        "decision_id": "decision-1",
        "episode_id": "episode-1",
        "split": "development",
        "current_metadata": {"own_archetype": "arch"},
        "own_deck": {"sha256": "deck-hash"},
        "candidates": [
            {"semantic_id": baseline_id, "canonical": baseline,
             "source_tags": ["baseline", "rule_diverse"], "additive_rule_score": 10.0},
            {"semantic_id": teacher_id, "canonical": teacher,
             "source_tags": ["rule_diverse"], "additive_rule_score": 1.0},
        ],
        "candidate_sets": {
            "baseline": [baseline_id],
            "rule_diverse": [baseline_id, teacher_id],
        },
    }
    units = []
    for batch_id, advantage in enumerate((0.20, 0.30)):
        units.append({
            "state_id": "state-1",
            "decision_id": "decision-1",
            "episode_id": "episode-1",
            "batch_id": batch_id,
            "baseline_action": baseline_id,
            "oracle_action": teacher_id,
            "actions": {
                baseline_id: action_stats(0.0),
                teacher_id: action_stats(advantage),
            },
        })
    selection = {
        "state_id": "state-1",
        "selected": True,
        "best_nonbaseline": {"action": teacher_id, "top_count": 2},
    }
    return state, units, selection


class GoldTeacherAdvantagesTest(unittest.TestCase):
    def test_aggregate_preserves_complete_actions_and_paired_uncertainty(self):
        state, units, selection = fixture_values()
        row = _aggregate_state(state, units, selection, split="train")
        self.assertEqual("train", row["split"])
        self.assertEqual(2, len(row["actions"]))
        selected = next(item for item in row["actions"] if item["is_selected_teacher_action"])
        self.assertAlmostEqual(0.25, selected["mean_advantage_win_probability"])
        self.assertAlmostEqual(0.20, selected["minimum_batch_advantage_win_probability"])
        self.assertEqual([0, 1], row["batch_ids"])
        self.assertEqual(selection["best_nonbaseline"], row["selection_evidence"])

    def test_top_count_and_semantic_drift_fail_closed(self):
        state, units, selection = fixture_values()
        selection["best_nonbaseline"]["top_count"] = 1
        with self.assertRaisesRegex(ValueError, "top-count"):
            _aggregate_state(state, units, selection, split="train")
        state, units, selection = fixture_values()
        state["candidates"][0]["semantic_id"] = "bad"
        with self.assertRaisesRegex(ValueError, "semantic binding"):
            _aggregate_state(state, units, selection, split="train")

    def test_write_once_artifact_reproduces_and_detects_row_tamper(self):
        state, units, selected_state = fixture_values()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            corpus = source / "corpus"
            oracle = source / "run"
            output = root / "output"
            corpus.mkdir(parents=True)
            oracle.mkdir(parents=True)
            (corpus / "states.jsonl").write_text(json.dumps(state) + "\n", encoding="ascii")
            (corpus / "manifest.json").write_text("{}\n", encoding="ascii")
            (corpus / "selection_manifest.json").write_text("{}\n", encoding="ascii")
            run = {"manifest_sha256": "run-manifest"}
            report = {
                "manifest_sha256": "report-manifest",
                "posterior_weighted_teacher_statistics": {"per_state_batch": units},
            }
            (oracle / "run_manifest.json").write_text(json.dumps(run) + "\n", encoding="ascii")
            (oracle / "report.json").write_text(json.dumps(report) + "\n", encoding="ascii")
            selection = {
                "manifest_sha256": "selection-manifest",
                "source": {
                    "workspace_path": "source",
                    "run_path": "run",
                    "run_manifest_sha256": "run-manifest",
                    "report_manifest_sha256": "report-manifest",
                },
                "next_run": {"state_ids": ["state-1"]},
                "states": [selected_state],
            }
            selection_path = root / "selection.json"
            split_path = root / "split.json"
            receipt_path = root / "receipt.json"
            selection_path.write_text(json.dumps(selection) + "\n", encoding="ascii")
            split_path.write_text("{}\n", encoding="ascii")
            receipt_path.write_text("{}\n", encoding="ascii")
            patches = (
                patch("research.rl_ptcg.gold_teacher_advantages.verify_oracle_output",
                      return_value={"complete": True, "report_recomputed": False}),
                patch("research.rl_ptcg.gold_teacher_advantages._verify_state_corpus", return_value={}),
                patch("research.rl_ptcg.gold_teacher_advantages.verify_refinement_selection",
                      return_value={"verified": True, "state_ids": ["state-1"]}),
                patch("research.rl_ptcg.gold_teacher_advantages._verify_source_receipt",
                      return_value={"manifest_sha256": "receipt-manifest"}),
                patch("research.rl_ptcg.gold_teacher_advantages._teacher_split_mapping",
                      return_value=({"decision-1": ("state-1", "train")}, "split-manifest")),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                result = build_teacher_advantages(
                    "corpus", "run", selection_path, split_path, receipt_path, output,
                    workspace_root=root, source_workspace_root=source,
                    target_archetype="arch",
                )
                self.assertEqual({"train": 1, "development": 0, "policy_family_holdout": 0}, result["splits"])
                self.assertEqual(1, result["states"])
                self.assertEqual(2, result["actions"])
                verify_teacher_advantages(output, root)
                (output / "advantages.jsonl").write_text("{}\n", encoding="ascii")
                with self.assertRaisesRegex(ValueError, "rows do not reproduce"):
                    verify_teacher_advantages(output, root)


if __name__ == "__main__":
    unittest.main()

