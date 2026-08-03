from __future__ import annotations

import unittest

import torch

from research.rl_ptcg.gold_prompt_ranker import PromptExample, PromptRanker, RankerConfig
from research.rl_ptcg.gold_prompt_rule_blend import build_rule_prior_map, evaluate_blend, select_alpha


def option(card):
    return {
        "action_type": 7,
        "selection_context": 0,
        "source_card_id": card,
        "source_zone": "hand",
        "source_relation": "self",
        "target_card_id": None,
    }


def complete(selection):
    return {
        "selection_context": 0,
        "minimum_count": 1,
        "maximum_count": 1,
        "selections": [selection],
    }


class ConstantRanker(PromptRanker):
    def __init__(self, values):
        super().__init__(RankerConfig(feature_dim=2, hidden_dim=2, style_dim=1), {"__unknown_style__": 0})
        self.values = torch.tensor(values, dtype=torch.float32)

    def score(self, state, actions, style_id):
        return self.values[:len(actions)].clone()


class GoldPromptRuleBlendTests(unittest.TestCase):
    def test_build_prior_maps_complete_action_to_semantic_option(self):
        from research.rl_ptcg.gold_prompt_ranker import _semantic_id
        from research.rl_ptcg.gold_prompt_rule_blend import _complete_action_id
        left, right = option(1), option(2)
        record = {
            "decision_id": "d",
            "chosen_canonical_action": complete(left),
            "legal_semantic_options": [right, left],
        }
        audit = {"d": {
            "gold_semantic_id": _complete_action_id(complete(left)),
            "baseline_semantic_id": _complete_action_id(complete(right)),
            "semantic_equal": False,
        }}
        prior = build_rule_prior_map([record], audit)["d"]
        self.assertEqual(_semantic_id(right), prior["rule_action_id"])
        self.assertFalse(prior["baseline_correct"])

    def test_unmapped_prior_falls_back_to_recorded_rule_correctness(self):
        example = PromptExample(
            "d", "development", "s", "a", torch.zeros(2), torch.zeros((2, 2)),
            ("a", "b"), "a", "7",
        )
        result = evaluate_blend(
            ConstantRanker([0.0, 1.0]), [example],
            {"d": {"rule_action_id": None, "baseline_correct": True}}, alpha=1.0,
        )["overall:overall"]
        self.assertEqual(1.0, result["blend_top1_accuracy"])
        self.assertEqual(0, result["mapped_rule_prior"])

    def test_rule_bonus_can_correct_model_and_alpha_ties_choose_smaller(self):
        example = PromptExample(
            "d", "development", "s", "a", torch.zeros(2), torch.zeros((2, 2)),
            ("a", "b"), "a", "7",
        )
        priors = {"d": {"rule_action_id": "a", "baseline_correct": True}}
        selected, sweep = select_alpha(ConstantRanker([0.0, 1.0]), [example], priors, [0, 1, 2])
        self.assertEqual(1.0, selected)
        self.assertEqual([0.0, 1.0, 1.0], [row["blend_top1_accuracy"] for row in sweep])

    def test_negative_alpha_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_blend(ConstantRanker([0.0]), [], {}, alpha=-1)


if __name__ == "__main__":
    unittest.main()
