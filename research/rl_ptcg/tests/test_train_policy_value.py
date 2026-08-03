import unittest

from research.rl_ptcg.train_policy_value import deck_signature, validation_record
from research.rl_ptcg.encoding import SCHEMA
from research.rl_ptcg.trajectory import TrajectoryRecord


def record(episode_id, opponent, deck):
    return TrajectoryRecord(
        episode_id=episode_id, step=0, seat=0,
        state_vector=[0.0] * len(SCHEMA.state_feature_names),
        option_vectors=[[0.0] * len(SCHEMA.option_feature_names)], rule_scores=[0.0],
        rule_action=0, selected_action=0, opponent=opponent,
        opponent_deck=deck,
    )


class PolicyValueSplitTests(unittest.TestCase):
    def test_deck_signature_ignores_card_order_and_opponent_label(self):
        left = record("left", "alice", [3, 1, 3, 2])
        right = record("right", "bob", [2, 3, 1, 3])
        self.assertEqual(deck_signature(left), deck_signature(right))
        self.assertEqual(
            validation_record(left, 0.25, "deck"),
            validation_record(right, 0.25, "deck"),
        )

    def test_episode_split_can_separate_same_deck(self):
        values = {
            validation_record(record("episode-%d" % index, "same", [1, 2]), 0.5, "episode")
            for index in range(20)
        }
        self.assertEqual(values, {False, True})


if __name__ == "__main__":
    unittest.main()
