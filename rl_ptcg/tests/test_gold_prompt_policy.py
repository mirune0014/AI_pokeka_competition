import unittest

import torch

from rl_ptcg.canonical_actions import canonicalize_option
from rl_ptcg.gold_prompt_policy import GoldPromptHybridPolicy, rank_single_selection
from rl_ptcg.gold_prompt_ranker import RankerConfig, _semantic_id


class DummyModel:
    def __init__(self):
        self.config = RankerConfig(
            feature_dim=16, include_known_private=True,
            include_public_history=False, use_style_embedding=False,
        )

    def eval(self):
        return self

    def score(self, state, actions, style_id):
        del state, style_id
        return torch.arange(actions.shape[0], dtype=torch.float32)


def observation(*, minimum=1, maximum=1):
    return {
        "current": {"yourIndex": 0, "result": -1, "players": [{}, {}]},
        "select": {
            "context": 7, "minCount": minimum, "maxCount": maximum,
            "option": [{"type": 1}, {"type": 2}],
        },
    }


class GoldPromptPolicyTests(unittest.TestCase):
    def test_ranker_selects_highest_scored_semantic_option(self):
        prompt = observation()
        identifiers = [
            _semantic_id(canonicalize_option(prompt, option).to_dict())
            for option in prompt["select"]["option"]
        ]
        expected = max(range(len(identifiers)), key=lambda index: identifiers[index])
        self.assertEqual([expected], rank_single_selection(DummyModel(), prompt))

    def test_hybrid_falls_back_for_multi_selection_prompt(self):
        calls = []

        def fallback(value):
            calls.append(value)
            return [0]

        policy = GoldPromptHybridPolicy(DummyModel(), fallback)
        prompt = observation(minimum=0, maximum=2)
        self.assertEqual([0], policy(prompt))
        self.assertEqual([prompt], calls)


if __name__ == "__main__":
    unittest.main()
