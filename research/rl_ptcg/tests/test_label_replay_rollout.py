import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research.rl_ptcg.label_replay_rollout import (
    exact_search_guess, nearest_agent_dir, nearest_agent_dirs, replay_decisions, replay_decks, replay_result,
    should_label_decision, target_seat_for_deck,
)


def record(observation=None, action=None):
    return {"observation": observation, "action": action or []}


class ReplayLabelTests(unittest.TestCase):
    def test_decks_and_target_seat_use_card_multisets(self):
        deck0 = list(range(60))
        deck1 = [9] * 60
        replay = {"steps": [[record(action=deck0), record(action=deck1)]]}
        self.assertEqual(replay_decks(replay), {0: deck0, 1: deck1})
        self.assertEqual(target_seat_for_deck(replay, list(reversed(deck0))), 0)

    def test_action_is_aligned_to_previous_observation(self):
        observation = {
            "current": {"yourIndex": 0, "result": -1},
            "select": {"option": [{}, {}, {}], "minCount": 1, "maxCount": 1},
        }
        replay = {"steps": [
            [record(observation=observation), record()],
            [record(action=[2]), record()],
        ]}
        self.assertEqual(list(replay_decisions(replay, 0)), [(0, observation, [2])])

    def test_invalid_or_inactive_action_is_skipped(self):
        observation = {
            "current": {"yourIndex": 1, "result": -1},
            "select": {"option": [{}], "minCount": 1, "maxCount": 1},
        }
        replay = {"steps": [
            [record(observation=observation), record()],
            [record(action=[4]), record()],
        ]}
        self.assertEqual(list(replay_decisions(replay, 0)), [])

    def test_replay_result_returns_winner_or_draw(self):
        self.assertEqual(replay_result({"rewards": [-1, 1]}), 1)
        self.assertEqual(replay_result({"rewards": [0, 0]}), 2)

    def test_exact_guess_uses_pre_action_visualizer_zones(self):
        def card(value):
            return {"id": value}
        full = {"players": [
            {"deck": [card(1)], "prize": [card(2)]},
            {"deck": [card(3)], "prize": [card(4)], "hand": [card(5)],
             "active": [card(6)]},
        ]}
        replay = {"steps": [[{"visualize": [{"current": full}, {"current": full}]}]]}
        observation = {"current": {"players": [
            {"deckCount": 1, "prize": [None]},
            {"deckCount": 1, "prize": [None], "handCount": 1, "active": [None]},
        ]}}
        guess = exact_search_guess(replay, 1, 0, observation)
        self.assertEqual(guess.your_deck, [1])
        self.assertEqual(guess.opponent_hand, [5])
        self.assertEqual(guess.opponent_active, [6])

    def test_nearest_agent_uses_deck_multiset_overlap(self):
        with TemporaryDirectory() as root:
            for name, deck in (("near", [1] * 59 + [2]), ("far", [1] * 30 + [3] * 30)):
                directory = Path(root) / name
                directory.mkdir()
                (directory / "main.py").write_text("", encoding="ascii")
                (directory / "deck.csv").write_text("\n".join(map(str, deck)), encoding="ascii")
            directory, metrics = nearest_agent_dir(Path(root), [1] * 60)
            self.assertEqual(directory.name, "near")
            self.assertEqual(metrics, {"overlap": 59, "distance": 2})

    def test_nearest_agents_return_ranked_population(self):
        with TemporaryDirectory() as root:
            for name, deck in (("near", [1] * 59 + [2]), ("mid", [1] * 50 + [3] * 10), ("far", [4] * 60)):
                directory = Path(root) / name
                directory.mkdir()
                (directory / "main.py").write_text("", encoding="ascii")
                (directory / "deck.csv").write_text("\n".join(map(str, deck)), encoding="ascii")
            ranked = nearest_agent_dirs(Path(root), [1] * 60, 2)
            self.assertEqual(["near", "mid"], [directory.name for directory, _ in ranked])

    def test_decision_filter_supports_exact_steps_and_contexts(self):
        self.assertTrue(should_label_decision(22, 7, [], [7]))
        self.assertTrue(should_label_decision(22, 7, [22], [7]))
        self.assertFalse(should_label_decision(21, 7, [22], [7]))
        self.assertFalse(should_label_decision(22, 0, [22], [7]))


if __name__ == "__main__":
    unittest.main()
