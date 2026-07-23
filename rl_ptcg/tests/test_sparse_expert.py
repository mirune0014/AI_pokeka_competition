import tempfile
from pathlib import Path
import unittest

from rl_ptcg.sparse_expert import (
    evaluate, load_weights, make_example, make_observation_example, predict, save_weights, train,
)


def example(changed=False):
    return make_example([
        {"features": {"good": 1}, "normalized_score": 0},
        {"features": {"good": 0}, "normalized_score": 0},
    ], [1], [0] if changed else [1], matchup="synthetic", opponent="x")


class SparseExpertTests(unittest.TestCase):
    def test_observation_example_preserves_global_action_mapping(self):
        class Obj:
            def __init__(self, **values):
                self.__dict__.update(values)
        observation = Obj(
            current=Obj(yourIndex=0, turn=2, players=[{}, {}]),
            select=Obj(context=0, option=[Obj(type=1), Obj(type=2), Obj(type=3)]),
        )
        row = make_observation_example(
            observation, [10, 9, 8], [0], [2],
            score_option=lambda _obs, _option: 0,
            option_card=lambda _obs, _option: None,
            option_target=lambda _obs, _option: None,
            detect_matchup=lambda _obs: "archaludon",
            top_n=2,
        )
        self.assertEqual([0, 1, 2], row["metadata"]["global_option_indices"])
        self.assertEqual([2], row["metadata"]["global_expert_action"])
        self.assertEqual([2], row["expert_action"])

    def test_training_improves_changed_label_agreement(self):
        rows = [example(True)] * 8
        before = evaluate(rows, {})
        result = train(rows, epochs=40, learning_rate=0.4, l2=0, changed_weight=1)
        self.assertLess(result["metrics"]["loss"], before["loss"])
        self.assertEqual([0], predict(rows[0], result["weights"]))
        self.assertEqual(1.0, result["metrics"]["changed_label_agreement"])

    def test_explicit_pool_does_not_append_required_actions(self):
        class Obj:
            def __init__(self, **values):
                self.__dict__.update(values)
        observation = Obj(
            current=Obj(yourIndex=0, turn=2, players=[{}, {}]),
            select=Obj(context=0, option=[Obj(type=1), Obj(type=2), Obj(type=3)]),
        )
        with self.assertRaisesRegex(ValueError, "outside the safe option pool"):
            make_observation_example(
                observation, [10, 9, 8], [0], [2],
                score_option=lambda _obs, _option: 0,
                option_card=lambda _obs, _option: None,
                option_target=lambda _obs, _option: None,
                detect_matchup=lambda _obs: "archaludon",
                pool_indices=[0, 1],
            )

    def test_multiselect_and_json_round_trip(self):
        row = make_example([
            {"features": {"a": 1}, "normalized_score": 0},
            {"features": {"b": 1}, "normalized_score": 0},
            {"features": {}, "normalized_score": 0},
        ], [2, 1], [0, 1])
        result = train([row] * 5, epochs=30, learning_rate=.4, l2=0)
        self.assertEqual({0, 1}, set(predict(row, result["weights"])))
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "weights.json")
            save_weights(result["weights"], path)
            self.assertEqual(result["weights"], load_weights(path))

    def test_empty_and_zero_data_are_safe(self):
        self.assertEqual({}, train([])["weights"])
        self.assertEqual(0.0, evaluate([])["loss"])
        self.assertEqual([], predict({"options": [], "expert_action": []}))


if __name__ == "__main__":
    unittest.main()
