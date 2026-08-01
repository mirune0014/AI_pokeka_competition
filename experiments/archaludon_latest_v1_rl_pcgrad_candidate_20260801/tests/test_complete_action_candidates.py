from __future__ import annotations

import unittest

import torch

from archaludon_rl.complete_action import (
    complete_action_logits,
    enumerate_complete_actions,
    observation_complete_actions,
)
from archaludon_rl.model import ResidualActorCritic

from .helpers import observation


def option(index: int, identity: str, option_type: int = 3) -> dict:
    return {
        "engine_index": index,
        "identity": identity,
        "payload": {
            "option_type": option_type,
            "fields": {"area": 2},
            "source_card_id": 100 + index,
            "target_card_id": None,
        },
    }


class CompleteActionCandidateTests(unittest.TestCase):
    def test_optional_and_multiple_actions_are_complete_candidates(self):
        options = [option(0, "A"), option(1, "B"), option(2, "C")]
        result = enumerate_complete_actions(
            options,
            minimum=0,
            maximum=2,
            context=7,
        )
        self.assertEqual(len(result.candidates), 7)
        self.assertEqual(result.raw_candidate_count, 7)
        self.assertIn((), {row.action for row in result.candidates})
        self.assertIn((0, 2), {row.action for row in result.candidates})
        self.assertEqual(result.candidate_index_for(options, (2, 0)), result.candidate_index_for(options, (0, 2)))

    def test_semantic_duplicates_are_canonicalized(self):
        options = [option(0, "SAME"), option(1, "SAME"), option(2, "OTHER")]
        result = enumerate_complete_actions(
            options,
            minimum=1,
            maximum=1,
            context=8,
        )
        self.assertEqual(result.raw_candidate_count, 3)
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(result.duplicate_canonical_action_count, 1)
        self.assertEqual(result.candidate_index_for(options, (0,)), result.candidate_index_for(options, (1,)))

    def test_order_sensitive_context_keeps_distinct_orders(self):
        options = [option(0, "A"), option(1, "B")]
        result = enumerate_complete_actions(
            options,
            minimum=2,
            maximum=2,
            context=34,
        )
        self.assertEqual({row.action for row in result.candidates}, {(0, 1), (1, 0)})
        self.assertNotEqual(result.candidate_index_for(options, (0, 1)), result.candidate_index_for(options, (1, 0)))

    def test_live_candidates_contain_execution_payload_and_are_engine_valid(self):
        obs = observation(
            options=[
                {"type": 3, "area": 2, "index": 0, "playerIndex": 0},
                {"type": 3, "area": 2, "index": 1, "playerIndex": 0},
            ],
            minimum=0,
            maximum=2,
            select_context=7,
        )
        result = observation_complete_actions(obs)
        self.assertEqual(len(result.candidates), 4)
        selected = next(row for row in result.candidates if row.action == (1,))
        payload = selected.selected_options[0]["execution_payload"]
        self.assertEqual(payload["fields"]["index"], 1)
        self.assertEqual(payload["source_card_id"], 101)

    def test_set_pooling_scores_one_logit_per_complete_candidate(self):
        torch.manual_seed(7)
        model = ResidualActorCritic()
        options = [option(0, "A"), option(1, "B"), option(2, "C")]
        candidates = enumerate_complete_actions(
            options,
            minimum=0,
            maximum=2,
            context=7,
        )
        state = torch.randn(model.config.state_dim)
        option_vectors = torch.randn(3, model.config.action_dim)
        logits = complete_action_logits(model, state, option_vectors, candidates)
        self.assertEqual(tuple(logits.shape), (7,))
        self.assertTrue(bool(torch.isfinite(logits).all()))


if __name__ == "__main__":
    unittest.main()
