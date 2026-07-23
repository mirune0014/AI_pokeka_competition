from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import torch

from rl_ptcg.gold_prompt_ranker import PromptExample, PromptRanker, RankerConfig, _load_allowed_records
from rl_ptcg.gold_prompt_safety_gate import (apply_gate, decision_diagnostics, evaluate_gate,
    select_rules, validate_ranker_evaluation_report, validate_thresholds, wilson_lower_bound,
    validate_wilson_settings, write_once)


class ConstantRanker(PromptRanker):
    def __init__(self, scores):
        super().__init__(RankerConfig(feature_dim=2, hidden_dim=2, style_dim=1), {"__unknown_style__": 0})
        self.scores = torch.tensor(scores, dtype=torch.float32)

    def score(self, state, actions, style_id):
        return self.scores[:len(actions)].clone()


def example(decision_id, target="a", action_type="play", split="development"):
    return PromptExample(decision_id, split, "style", "arch", torch.zeros(2), torch.zeros((2, 2)),
                         ("a", "b"), target, action_type)


def row(identifier, *, improvement=False, regression=False, action_type="play", delta=1.0):
    return {"decision_id": identifier, "split": "development", "style_id": "style",
            "action_type": action_type, "mapped": True, "model_differs_from_mapped_rule": True,
            "model_vs_rule_score_delta": delta, "baseline_correct": regression,
            "model_correct": improvement}


class GoldPromptSafetyGateTests(unittest.TestCase):
    def test_wilson_lower_bound_is_conservative(self):
        self.assertAlmostEqual(0.0, wilson_lower_bound(0, 10))
        self.assertGreater(wilson_lower_bound(10, 10), 0.5)
        self.assertLess(wilson_lower_bound(6, 10), 0.6)

    def test_entropy_diagnostic_stays_finite_for_extreme_scores(self):
        diagnostics = decision_diagnostics(ConstantRanker([1000.0, -1000.0]), [example("d")], {
            "d": {"rule_action_id": "b", "baseline_correct": False},
        })
        self.assertTrue(torch.isfinite(torch.tensor(diagnostics[0]["normalized_entropy"])))

    def test_selection_is_per_type_and_deterministic(self):
        rows = [row("i%d" % index, improvement=True, delta=1.0) for index in range(10)]
        rows += [row("low%d" % index, improvement=True, action_type="retreat", delta=0.1) for index in range(10)]
        selected, sweep = select_rules(rows, thresholds=(0.0, 0.5), min_discordant=10)
        self.assertEqual(0.5, selected["play"]["threshold"])
        self.assertEqual(0.0, selected["retreat"]["threshold"])
        self.assertEqual(["play", "play", "retreat", "retreat"], [item["action_type"] for item in sweep])

    def test_unmapped_falls_back_to_recorded_baseline(self):
        diagnostics = decision_diagnostics(ConstantRanker([0.0, 1.0]), [example("d")], {
            "d": {"rule_action_id": None, "baseline_correct": True},
        })
        rows = apply_gate(diagnostics, {"play": {"threshold": 0.0}})
        self.assertFalse(rows[0]["override"])
        self.assertTrue(rows[0]["gated_correct"])
        self.assertEqual(1.0, evaluate_gate(rows)["overall:overall"]["gated_accuracy"])

    def test_development_fit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation_report.json"
            path.write_text(json.dumps({"fit_splits": ["train", "development"]}), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "in-sample"):
                validate_ranker_evaluation_report(path)

    def test_bad_thresholds_are_rejected(self):
        for values in ((-1.0,), (float("nan"),), (0.0, 0.0)):
            with self.assertRaises(ValueError):
                validate_thresholds(values)
        with self.assertRaises(ValueError):
            validate_wilson_settings(1.5, 1.0, 0.5)

    def test_non_allowlisted_blind_payload_stays_unparsed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text('{"decision_id":"blind",not-json}\n{"decision_id":"allowed"}\n', encoding="ascii")
            self.assertEqual(["allowed"], [item["decision_id"] for item in _load_allowed_records(path, {"allowed": "development"})])

    def test_write_once_rejects_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            write_once(path, b"first\n")
            write_once(path, b"first\n")
            with self.assertRaises(FileExistsError):
                write_once(path, b"second\n")


if __name__ == "__main__":
    unittest.main()
