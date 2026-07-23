import random
import sys
import types
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from rl_ptcg.rollout_expert import (
    _coin_action, _deck_hypothesis_signature, _hidden_world_id, _paired_delta, choose_with_rollout,
)
from rl_ptcg.belief import SearchGuess
from rl_ptcg.probe_rollout import AgentChooser


class Obj:
    def __init__(self, **kw): self.__dict__.update(kw)


class RolloutTests(unittest.TestCase):
    def setUp(self):
        self.obs = Obj(
            current=Obj(yourIndex=0, result=-1, players=[{}, {}]),
            select=Obj(minCount=1, maxCount=1, option=[Obj(), Obj()]),
        )
        self.states = []
        self.api = types.SimpleNamespace(to_observation_class=lambda x: x, search_begin=self.begin,
                                         search_step=self.step, search_end=self.end)

    def begin(self, *args, **kw): return Obj(searchId=1, observation=self.obs)
    def step(self, sid, action): return self.states.pop(0)
    def end(self): self.ended = True

    def test_terminal_is_from_root_perspective_and_cleanup_runs(self):
        self.ended = False
        terminal = Obj(observation=Obj(current=Obj(yourIndex=1, result=0)))
        self.states = [terminal, terminal]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch("rl_ptcg.rollout_expert.sample_search_guess", return_value=guess):
            d = choose_with_rollout(self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1), determinizations=1)
        self.assertEqual(1.0, d.evaluations[0].values[0]); self.assertTrue(self.ended)

    def test_agent_chooser_falls_back_to_submission_entrypoint(self):
        calls = []

        @dataclass
        class Observation:
            value: int

        class SubmissionAgent:
            module = types.SimpleNamespace()
            agent_dir = "."

            def __call__(self, observation):
                calls.append(observation)
                return [1]

        observation = Observation(7)
        self.assertEqual([1], AgentChooser(SubmissionAgent()).choose_options(observation))
        self.assertEqual([{"value": 7}], calls)

    def test_common_seed_makes_branch_coin_path_identical(self):
        coin = Obj(searchId=2, observation=Obj(
            current=Obj(yourIndex=0, result=-1),
            select=Obj(context=46, option=[Obj(), Obj()]),
        ))
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [coin, terminal, coin, terminal]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch("rl_ptcg.rollout_expert.sample_search_guess", return_value=guess):
            d = choose_with_rollout(self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(4), determinizations=1, max_steps=1)
        self.assertEqual(2, len(d.evaluations)); self.assertEqual(d.evaluations[0].values, d.evaluations[1].values)

    def test_coin_selection_uses_yes_no_types_not_option_order(self):
        select = Obj(option=[Obj(type=9), Obj(type=2), Obj(type=1)])
        seen = {_coin_action(select, random.Random(seed))[0] for seed in range(20)}
        self.assertEqual({1, 2}, seen)

    def test_paired_delta_uses_common_determinization_difference(self):
        mean, lower = _paired_delta([1, 1, -1, 1], [-1, 1, -1, -1], 1.0)
        self.assertEqual(1.0, mean)
        self.assertGreater(lower, 0.0)

    def test_incomplete_branch_discards_the_whole_determinization(self):
        self.ended = False
        incomplete = Obj(observation=Obj(
            current=Obj(yourIndex=0, result=-1),
            select=Obj(context=0, option=[]),
        ))
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, incomplete]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1,
            )
        self.assertEqual(0, decision.determinizations)
        self.assertTrue(all(not evaluation.values for evaluation in decision.evaluations))
        self.assertTrue(self.ended)

    def test_opponent_policy_ensemble_uses_worst_scenario(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        policy_a, policy_b = object(), object()

        def search_step(_search_id, action):
            return Obj(action=list(action), observation=self.obs)

        def rollout(state, modules, *_args):
            action = state.action[0]
            if modules[1] is policy_a:
                return 1.0 if action == 1 else -1.0
            return 0.0 if action == 1 else 1.0

        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=self.begin,
            search_step=search_step,
            search_end=self.end,
        )
        with patch.dict(sys.modules, {"cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ), patch("rl_ptcg.rollout_expert._rollout", side_effect=rollout):
            decision = choose_with_rollout(
                self.obs, {1: policy_a}, [1] * 60, [1] * 60, [1, 0], [0],
                random.Random(9), determinizations=4, confidence_z=0.0,
                improvement_margin=0.1,
                opponent_policy_modules=[policy_a, policy_b],
            )
        self.assertFalse(decision.changed)
        self.assertEqual([0], decision.selected)

    def test_continuation_policy_ensemble_is_recorded(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        continuation_a, continuation_b = object(), object()

        def search_step(_search_id, action):
            return Obj(action=list(action), observation=self.obs)

        def rollout(state, modules, *_args):
            return 1.0 if modules[0] is continuation_a else -1.0

        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=self.begin,
            search_step=search_step,
            search_end=self.end,
        )
        with patch.dict(sys.modules, {"cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ), patch("rl_ptcg.rollout_expert._rollout", side_effect=rollout):
            decision = choose_with_rollout(
                self.obs, {0: continuation_a}, [1] * 60, [1] * 60,
                [1, 0], [0], random.Random(9), determinizations=2,
                your_policy_modules=[continuation_a, continuation_b],
                return_scenario_values=True,
            )
        self.assertEqual({0, 1}, {
            row["continuation_policy_index"] for row in decision.scenario_values
        })

    def test_complete_mode_can_include_action_outside_ranked_pool(self):
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, terminal]
        guess = SearchGuess([1], [1], [2], [3], [4], [], [5], [6])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [10, 0], [0], random.Random(1),
                determinizations=1, candidate_mode="complete", max_complete_actions=2,
            )
        self.assertEqual({(0,), (1,)}, {tuple(value.action) for value in decision.evaluations})

    def test_scenario_values_are_complete_and_use_stable_ids(self):
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, terminal]
        guess = SearchGuess([1], [2], [3], [4], [5], [6], [7], [8])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, return_scenario_values=True,
            )
        self.assertEqual(2, len(decision.scenario_values))
        self.assertEqual({(0,), (1,)}, {tuple(row["action"]) for row in decision.scenario_values})
        self.assertEqual({0}, {row["particle_index"] for row in decision.scenario_values})
        self.assertEqual({0}, {row["determination_index"] for row in decision.scenario_values})
        self.assertEqual(1, len({row["hidden_world_id"] for row in decision.scenario_values}))
        self.assertTrue(all(row["hidden_world_id"].startswith("world:") for row in decision.scenario_values))
        self.assertTrue(all(row["deck_hypothesis_signature"].startswith("deck:") for row in decision.scenario_values))
        self.assertEqual(
            {row["hypothesis_signature"] for row in decision.scenario_values},
            {row["deck_hypothesis_signature"] for row in decision.scenario_values},
        )
        self.assertTrue(all(row["terminal_utility"] == 1.0 for row in decision.scenario_values))

    def test_provenance_ids_are_deterministic(self):
        guess = SearchGuess([1], [2], [3], [4], [5], [6], [7], [8])
        self.assertEqual(_hidden_world_id(guess), _hidden_world_id(guess))
        self.assertEqual(_deck_hypothesis_signature([3, 1, 2]), _deck_hypothesis_signature([2, 3, 1]))

    def test_failed_determination_emits_no_partial_scenario_rows(self):
        incomplete = Obj(observation=Obj(
            current=Obj(yourIndex=0, result=-1), select=Obj(context=0, option=[]),
        ))
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, incomplete]
        guess = SearchGuess([1], [2], [3], [4], [5], [6], [7], [8])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, return_scenario_values=True,
            )
        self.assertEqual([], decision.scenario_values)

    def test_explicit_actions_are_the_only_actions_evaluated(self):
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, terminal]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [10, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[1], [0]],
            )
        self.assertEqual([(1,), (0,)], [tuple(value.action) for value in decision.evaluations])

    def test_explicit_actions_reject_invalid_and_missing_baseline(self):
        kwargs = dict(determinizations=1, explicit_candidate_actions=[[1]])
        with patch.dict(sys.modules, {"cg.api": self.api}):
            with self.assertRaisesRegex(ValueError, "include rule action"):
                choose_with_rollout(
                    self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                    **kwargs,
                )
            for actions in ([[0, 0]], [[2]], [["0"]], []):
                with self.subTest(actions=actions), self.assertRaises(ValueError):
                    choose_with_rollout(
                        self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                        determinizations=1, explicit_candidate_actions=actions,
                    )

    def test_explicit_actions_normalize_and_deduplicate_order(self):
        self.obs.select = Obj(minCount=1, maxCount=2, option=[Obj(), Obj(), Obj()])
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, terminal, terminal]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0, 0], [1, 0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[1, 0], [0, 1], [2]],
            )
        self.assertEqual([(0, 1), (2,)], [tuple(value.action) for value in decision.evaluations])

    def test_reverse_only_reverses_root_search_order(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])

        def run(order):
            calls = []
            terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
            api = types.SimpleNamespace(
                to_observation_class=lambda value: value,
                search_begin=self.begin,
                search_step=lambda _sid, action: (calls.append(list(action)) or terminal),
                search_end=self.end,
            )
            with patch.dict(sys.modules, {"cg.api": api}), patch(
                "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
            ):
                decision = choose_with_rollout(
                    self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                    determinizations=1, explicit_candidate_actions=[[0], [1]],
                    branch_order=order, return_scenario_values=True,
                )
            return calls, decision

        forward_calls, forward = run("forward")
        reverse_calls, reverse = run("reverse")
        self.assertEqual([[0], [1]], forward_calls)
        self.assertEqual([[1], [0]], reverse_calls)
        self.assertEqual([value.action for value in forward.evaluations], [value.action for value in reverse.evaluations])
        self.assertEqual(
            {tuple(row["action"]) for row in forward.scenario_values},
            {tuple(row["action"]) for row in reverse.scenario_values},
        )

    def test_explicit_partial_failure_has_no_scenario_rows(self):
        incomplete = Obj(observation=Obj(
            current=Obj(yourIndex=0, result=-1), select=Obj(context=0, option=[]),
        ))
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        self.states = [terminal, incomplete]
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        with patch.dict(sys.modules, {"cg.api": self.api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[0], [1]],
                return_scenario_values=True,
            )
        self.assertEqual([], decision.scenario_values)

    def test_fresh_root_per_branch_restarts_search_for_every_action(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        begins = []
        ends = []
        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=lambda *_args, **_kwargs: (
                begins.append(len(begins)) or Obj(searchId=len(begins))
            ),
            search_step=lambda _sid, _action: terminal,
            search_end=lambda: ends.append(len(ends)),
        )
        with patch.dict(sys.modules, {"cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            decision = choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[0], [1]],
                fresh_root_per_branch=True, return_scenario_values=True,
            )
        self.assertEqual(2, len(begins))
        self.assertEqual(2, len(ends))
        self.assertEqual(2, len(decision.scenario_values))

    def test_fresh_root_per_branch_copies_mutable_search_inputs(self):
        guess = SearchGuess([1], [2], [3], [4], [5], [], [], [])
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        seen = []
        self.obs.select.context = 0

        def begin(observation, your_deck, *_args, **_kwargs):
            seen.append((observation.select.context, list(your_deck)))
            observation.select.context = 99
            your_deck.append(999)
            return Obj(searchId=len(seen))

        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=begin,
            search_step=lambda _sid, _action: terminal,
            search_end=self.end,
        )
        with patch.dict(sys.modules, {"cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[0], [1]],
                fresh_root_per_branch=True,
            )
        self.assertEqual([(0, [1]), (0, [1])], seen)
        self.assertEqual([1], guess.your_deck)

    def test_rollout_module_factory_is_called_for_each_branch(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        calls = []
        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=self.begin,
            search_step=lambda _sid, _action: terminal,
            search_end=self.end,
        )

        def factory(determination, policy, continuation, action):
            calls.append((determination, policy, continuation, tuple(action)))
            return {}

        with patch.dict(sys.modules, {"cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[0], [1]],
                rollout_modules_factory=factory,
            )
        self.assertEqual([(0, 0, 0, (0,)), (0, 0, 0, (1,))], calls)

    def test_native_search_seed_is_reset_for_every_fresh_branch(self):
        guess = SearchGuess([1], [1], [1], [1], [1], [], [], [])
        terminal = Obj(observation=Obj(current=Obj(yourIndex=0, result=0)))
        seeds = []
        api = types.SimpleNamespace(
            to_observation_class=lambda value: value,
            search_begin=self.begin,
            search_step=lambda _sid, _action: terminal,
            search_end=self.end,
            search_seed=lambda value: seeds.append(value),
        )
        with patch.dict(sys.modules, {"cg": types.SimpleNamespace(api=api), "cg.api": api}), patch(
            "rl_ptcg.rollout_expert.sample_search_guess", return_value=guess
        ):
            choose_with_rollout(
                self.obs, {}, [1] * 60, [1] * 60, [1, 0], [0], random.Random(1),
                determinizations=1, explicit_candidate_actions=[[0], [1]],
                fresh_root_per_branch=True, seed_native_search=True,
            )
        self.assertEqual(2, len(seeds))
        self.assertEqual(1, len(set(seeds)))


if __name__ == "__main__": unittest.main()
