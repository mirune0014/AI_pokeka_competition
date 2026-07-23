from __future__ import annotations

import copy
from hashlib import sha256
import json
import unittest

import torch

from rl_ptcg.gold_advantage_ranker import (
    AdvantageRankerConfig,
    advantage_loss,
    build_advantage_examples,
    evaluate_advantage_ranker,
    safe_belief_projection,
    train_advantage_ranker,
)
from rl_ptcg.gold_prompt_ranker import _semantic_id


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


def belief() -> dict:
    return {
        "archetype": "marnie",
        "entropy": 0.5,
        "top1_mass": 0.6,
        "unknown_mass": 0.1,
        "synthetic_status": "accepted",
        "counts": {"selected_known_count": 2},
        "visible_requirements": {"10": 1},
        "catalog_results": [{"source_path": "secret-machine-path"}],
        "hypotheses": [
            {
                "archetype": "marnie",
                "kind": "known",
                "posterior_mass": 0.6,
                "decklist": [10] * 30 + [20] * 30,
                "deck_sha256": "a" * 64,
                "signature": "a" * 64,
                "sources": [{"source_path": "first"}],
            },
            {
                "archetype": "marnie",
                "kind": "synthetic_unknown",
                "posterior_mass": 0.4,
                "decklist": [10] * 29 + [20] * 31,
                "deck_sha256": "b" * 64,
                "signature": "b" * 64,
                "sources": [{"source_path": "second"}],
                "swap_count": 1,
            },
        ],
    }


def record(deck_tail: int = 3) -> dict:
    left, right = complete(1), complete(2)
    left_id, right_id = _semantic_id(left), _semantic_id(right)
    deck = [1] * 30 + [2] * 29 + [deck_tail]
    deck_hash = sha256((json.dumps(deck, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")).hexdigest()
    return {
        "state_id": "state-1",
        "decision_id": "decision-1",
        "safe_observation": {"turn": 4, "result": -1},
        "known_private_info": {"hand": [{"card_id": 1}]},
        "public_history": [{"event": "start"}],
        "belief": belief(),
        "current_metadata": {
            "own_archetype": "arch",
            "opponent_archetype": "marnie",
        },
        "own_deck": {"decklist": deck, "sha256": deck_hash},
        "candidates": [
            {"semantic_id": left_id, "canonical": left},
            {"semantic_id": right_id, "canonical": right},
        ],
    }


def advantage_row(value: dict) -> dict:
    candidates = value["candidates"]
    left_id, right_id = candidates[0]["semantic_id"], candidates[1]["semantic_id"]
    def item(candidate, advantage, baseline=False, selected=False):
        return {
            "semantic_id": candidate["semantic_id"],
            "canonical_complete_action": candidate["canonical"],
            "additive_rule_score": 10.0 if baseline else 1.0,
            "mean_advantage_win_probability": advantage,
            "minimum_batch_lcb90_win_probability": advantage - 0.02,
            "minimum_opponent_head_advantage_win_probability": advantage - 0.01,
            "is_baseline": baseline,
            "is_selected_teacher_action": selected,
            "batches": [
                {"cluster_standard_error_win_probability": 0.03},
                {"cluster_standard_error_win_probability": 0.04},
            ],
        }
    return {
        "state_id": "state-1",
        "decision_id": "decision-1",
        "split": "train",
        "source_actor_archetype": "arch",
        "source_actor_deck_sha256": value["own_deck"]["sha256"],
        "baseline_action": left_id,
        "selected_teacher_action": right_id,
        "actions": [
            item(candidates[0], 0.0, baseline=True),
            item(candidates[1], 0.30, selected=True),
        ],
    }


class GoldAdvantageRankerTest(unittest.TestCase):
    def test_belief_projection_drops_provenance_and_is_order_invariant(self):
        left = belief()
        right = copy.deepcopy(left)
        right["catalog_results"] = [{"source_path": "different"}]
        right["hypotheses"].reverse()
        for item in right["hypotheses"]:
            item["sources"] = [{"source_path": "changed"}]
            item["deck_sha256"] = "f" * 64
            item["signature"] = "e" * 64
        self.assertEqual(safe_belief_projection(left), safe_belief_projection(right))
        encoded = json.dumps(safe_belief_projection(left), sort_keys=True)
        self.assertNotIn("source", encoded)
        self.assertNotIn("sha256", encoded)
        self.assertNotIn("signature", encoded)

    def test_complete_actions_and_own_deck_variant_are_features(self):
        config = AdvantageRankerConfig(feature_dim=64, hidden_dim=8, epochs=1)
        first_record = record(3)
        second_record = record(4)
        first = build_advantage_examples(
            {"state-1": first_record}, [advantage_row(first_record)],
            allowed_splits=("train",), config=config,
        )[0]
        second = build_advantage_examples(
            {"state-1": second_record}, [advantage_row(second_record)],
            allowed_splits=("train",), config=config,
        )[0]
        self.assertEqual(2, first.actions.shape[0])
        self.assertFalse(torch.equal(first.state, second.state))
        self.assertAlmostEqual(0.30, float(first.advantage_targets.max()), places=6)

    def test_pairwise_advantage_training_is_deterministic(self):
        config = AdvantageRankerConfig(
            feature_dim=64,
            hidden_dim=16,
            epochs=30,
            batch_size=1,
            learning_rate=0.01,
        )
        value = record()
        example = build_advantage_examples(
            {"state-1": value}, [advantage_row(value)],
            allowed_splits=("train",), config=config,
        )[0]
        left, left_history = train_advantage_ranker([example], config=config, seed=7)
        right, right_history = train_advantage_ranker([example], config=config, seed=7)
        self.assertEqual(left_history, right_history)
        for key in left.state_dict():
            self.assertTrue(torch.equal(left.state_dict()[key], right.state_dict()[key]))
        self.assertLess(left_history[-1]["total"], left_history[0]["total"])
        report = evaluate_advantage_ranker(left, [example])
        self.assertEqual(1.0, report["overall:overall"]["top1_accuracy"])
        scores = left.score(example.state, example.actions)
        loss, parts = advantage_loss(scores, example, config)
        self.assertTrue(torch.isfinite(loss))
        self.assertGreaterEqual(float(parts["pairwise"].detach()), 0.0)

    def test_blind_and_actor_deck_drift_fail_closed(self):
        value = record()
        row = advantage_row(value)
        row["split"] = "blind"
        with self.assertRaisesRegex(ValueError, "blind"):
            build_advantage_examples(
                {"state-1": value}, [row], allowed_splits=("train",),
            )
        row = advantage_row(value)
        row["source_actor_deck_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "deck binding"):
            build_advantage_examples(
                {"state-1": value}, [row], allowed_splits=("train",),
            )


if __name__ == "__main__":
    unittest.main()
