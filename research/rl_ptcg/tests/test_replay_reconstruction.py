import copy
import unittest

from research.rl_ptcg.canonical_actions import resolve_prompt_action
from research.rl_ptcg.replay_reconstruction import (
    group_replay_transactions,
    iter_replay_decisions,
    project_public_event,
    public_history_before,
)


def observation(*, seat=0, turn=1, main=True, context=7):
    select = {
        "context": 0 if main else context,
        "type": 0 if main else 2,
        "minCount": 1,
        "maxCount": 1,
        "option": [{"type": 14 if main else 7, "area": 2, "index": 0, "playerIndex": seat}],
    }
    return {
        "current": {
            "yourIndex": seat,
            "turn": turn,
            "result": -1,
            "players": [
                {"hand": [{"id": "seat-0-card"}], "active": [], "bench": [], "discard": []},
                {"hand": [{"id": "seat-1-card"}], "active": [], "bench": [], "discard": []},
            ],
        },
        "select": select,
    }


class TrapFrame(dict):
    def get(self, key, default=None):
        if key in {"current", "obs", "select", "selected"}:
            raise AssertionError(f"hidden visualizer field accessed: {key}")
        return super().get(key, default)


def replay():
    steps = [[{}, {}] for _ in range(7)]
    # Labels are deliberately stored on the following step.
    decisions = [
        (0, observation(main=True), [0]),
        (1, observation(main=False, context=7), [0]),
        (2, observation(main=True), [0]),
        (4, observation(main=False, context=21), [0]),  # gap => orphan
        (5, observation(seat=1, turn=2, main=True), [0]),
    ]
    for step, obs, _action in decisions:
        seat = obs["current"]["yourIndex"]
        steps[step][seat]["observation"] = obs
        steps[step][seat]["action"] = [999]  # same-step decoy
    for step, obs, action in decisions:
        seat = obs["current"]["yourIndex"]
        steps[step + 1][seat]["action"] = action
    visual = [
        TrapFrame(logs=[
            {"type": "Draw", "playerIndex": 0, "cardId": "secret-draw", "serial": 1},
            {"type": "MoveCard", "playerIndex": 0, "cardId": "private", "fromArea": 1, "toArea": 2, "serial": 2},
            {"type": "MoveCard", "playerIndex": 0, "cardId": "public-play", "fromArea": 2, "toArea": 5, "serial": 3},
        ]),
        TrapFrame(logs=[{"type": "Play", "playerIndex": 0, "cardId": "future-sentinel", "serial": 4}]),
        TrapFrame(logs=[]),
        TrapFrame(logs=[]),
        TrapFrame(logs=[]),
        TrapFrame(logs=[]),
    ]
    steps[0][0]["visualize"] = visual
    return {"info": {"EpisodeId": 123}, "steps": steps, "rewards": [1, -1]}


class ReplayReconstructionTests(unittest.TestCase):
    def test_decision_iterator_uses_following_action_and_resolves_semantics(self):
        decisions = list(iter_replay_decisions(replay()))
        self.assertEqual([0, 1, 2, 4, 5], [decision.replay_step for decision in decisions])
        self.assertTrue(all(decision.action_step == decision.replay_step + 1 for decision in decisions))
        self.assertTrue(all(decision.raw_action == (0,) for decision in decisions))
        for decision in decisions:
            self.assertEqual([0], resolve_prompt_action(decision.observation, decision.canonical_action))

    def test_invalid_duplicate_action_is_not_emitted(self):
        value = replay()
        obs = observation(main=False)
        obs["select"]["maxCount"] = 2
        value["steps"][3][0]["observation"] = obs
        value["steps"][4][0]["action"] = [0, 0]
        self.assertNotIn(3, [decision.replay_step for decision in iter_replay_decisions(value)])

    def test_history_reads_only_prior_logs_and_never_visual_hidden_state(self):
        value = replay()
        history0 = public_history_before(value, 0, 0)
        history1 = public_history_before(value, 1, 0)
        self.assertEqual((), history0)
        encoded = repr(history1)
        self.assertIn("Draw", encoded)
        self.assertNotIn("secret-draw", encoded)
        self.assertNotIn("private", encoded)
        self.assertIn("public-play", encoded)
        self.assertNotIn("future-sentinel", encoded)
        self.assertIn("future-sentinel", repr(public_history_before(value, 2, 0)))

    def test_public_event_projection_is_actor_relative_and_fail_closed(self):
        play = {"type": "Play", "playerIndex": 1, "cardId": 44, "serial": 700}
        self.assertEqual("opponent", project_public_event(play, 0)["player"])
        self.assertEqual("self", project_public_event(play, 1)["player"])
        self.assertNotIn("serial", project_public_event(play, 0))
        self.assertIsNone(project_public_event({"type": "InternalRng", "seed": 9}, 0))
        self.assertIsNone(project_public_event(
            {"type": "MoveCard", "playerIndex": 0, "cardId": 99, "fromArea": 1, "toArea": 12}, 0,
        ))

    def test_transactions_follow_root_contiguity_turn_and_seat_boundaries(self):
        transactions = group_replay_transactions(iter_replay_decisions(replay()))
        self.assertEqual([(0, 1), (2,), (4,), (5,)], [item.replay_steps for item in transactions])
        self.assertEqual([False, False, True, False], [item.orphan_prompt_transaction for item in transactions])
        self.assertEqual([2, 1, 1, 1], [len(item.canonical_transaction.steps) for item in transactions])
        self.assertEqual(len({item.transaction_id for item in transactions}), 4)

    def test_frame_at_current_decision_is_future_and_does_not_enter_record_history(self):
        decisions = list(iter_replay_decisions(replay()))
        first, second = decisions[0], decisions[1]
        self.assertEqual((), first.public_history)
        self.assertNotIn("future-sentinel", repr(second.public_history))
        self.assertIn("future-sentinel", repr(decisions[2].public_history))

    def test_private_action_history_contains_only_prior_actions_for_that_seat(self):
        decisions = list(iter_replay_decisions(replay()))
        by_step = {decision.replay_step: decision for decision in decisions}
        self.assertEqual((), by_step[0].private_action_history)
        self.assertEqual(
            (by_step[0].canonical_action,),
            by_step[1].private_action_history,
        )
        self.assertEqual(2, len(by_step[2].private_action_history))
        self.assertEqual((), by_step[5].private_action_history)


if __name__ == "__main__":
    unittest.main()
