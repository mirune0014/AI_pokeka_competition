from __future__ import annotations

import copy
import unittest

from cg.api import (
    Card,
    EnergyType,
    Observation,
    Option,
    OptionType,
    Pokemon,
    SelectContext,
    SelectData,
    SelectType,
    State,
)

import _cumulative_parent as policy
import planner_deck_adaptation_v1 as v1
import planner_policy as core
import test_v1_compliance_patch as compliance_tests


class PsychicDrawOptionalFix1Tests(unittest.TestCase):
    def setUp(self):
        self.fx = compliance_tests.V1CompliancePatchTests(
            methodName="runTest"
        )
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def invoke(self, obs, baseline_action):
        raw = self.fx.raw(obs)
        calls = []
        action = v1.agent(
            policy,
            lambda value: calls.append(value) or baseline_action,
            raw,
        )
        self.assertEqual(len(calls), 1)
        return action

    def invoke_establishing_owner(self, obs, baseline_action, owner):
        raw = self.fx.raw(obs)
        calls = []
        established_parent_state = []

        def delegate(value):
            calls.append(value)
            core.INTEGRATED_TRANSACTION = owner
            policy.pre_turn = 987654321
            established_parent_state.append(
                core.parent_state_snapshot(policy)
            )
            return baseline_action

        action = v1.agent(policy, delegate, raw)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            core.parent_state_snapshot(policy),
            established_parent_state[0],
        )
        self.assertIs(core.INTEGRATED_TRANSACTION, owner)
        return action

    def psychic_prompt(
        self,
        card_id,
        deck_count,
        *,
        options=None,
        context=SelectContext.ACTIVATE,
        context_owner=0,
        context_serial=None,
    ):
        pokemon = (
            self.fx.kadabra(False)
            if card_id == v1.KADABRA
            else self.fx.alakazam()
        )
        if context_serial is None:
            context_serial = pokemon.serial
        mine = self.fx.player(
            active=[pokemon],
            hand=[self.fx.card(1152, 0, 8101)],
            hand_count=1,
        )
        mine.deckCount = deck_count
        theirs = self.fx.player(
            active=[self.fx.target(100)],
            hand=None,
            hand_count=4,
        )
        state = State(
            4,
            2,
            0,
            0,
            False,
            False,
            False,
            False,
            -1,
            [],
            None,
            [mine, theirs],
        )
        select = SelectData(
            SelectType.YES_NO,
            context,
            1,
            1,
            0,
            0,
            options
            if options is not None
            else [Option(OptionType.YES), Option(OptionType.NO)],
            None,
            Card(card_id, context_serial, context_owner),
            None,
        )
        return Observation(select, [], state)

    def test_kadabra_and_alakazam_boundaries_and_option_order(self):
        for card_id, draw_count in ((v1.KADABRA, 2), (v1.ALAKAZAM, 3)):
            for reversed_order in (False, True):
                options = (
                    [Option(OptionType.NO), Option(OptionType.YES)]
                    if reversed_order
                    else [Option(OptionType.YES), Option(OptionType.NO)]
                )
                yes_index = 1 if reversed_order else 0
                no_index = 0 if reversed_order else 1

                v1.reset()
                unsafe = self.psychic_prompt(
                    card_id, draw_count, options=options
                )
                self.assertEqual(self.invoke(unsafe, [yes_index]), [no_index])
                self.assertEqual(
                    v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
                    v1.RULE_PSYCHIC_DRAW_OPTIONAL,
                )
                self.assertIn(
                    "V3_PSYCHIC_DRAW_OPTIONAL_NO",
                    v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                )

                v1.reset()
                safe = self.psychic_prompt(
                    card_id, draw_count + 1, options=copy.deepcopy(options)
                )
                baseline = [yes_index]
                self.assertIs(self.invoke(safe, baseline), baseline)
                self.assertIn(
                    "V3_PSYCHIC_DRAW_BASELINE_YES_PRESERVED",
                    v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                )

    def test_baseline_no_and_malformed_unknown_prompts_preserve_identity(self):
        baseline_no = [1]
        self.assertIs(
            self.invoke(
                self.psychic_prompt(v1.ALAKAZAM, 3),
                baseline_no,
            ),
            baseline_no,
        )
        self.assertNotEqual(
            v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
            v1.RULE_PSYCHIC_DRAW_OPTIONAL,
        )

        cases = [
            self.psychic_prompt(
                v1.ALAKAZAM,
                3,
                options=[Option(OptionType.YES), Option(OptionType.YES)],
            ),
            self.psychic_prompt(
                v1.ALAKAZAM,
                3,
                options=[Option(OptionType.YES)],
            ),
            self.psychic_prompt(
                v1.ALAKAZAM,
                3,
                options=[
                    Option(OptionType.YES),
                    Option(OptionType.NO),
                    Option(OptionType.END),
                ],
            ),
            self.psychic_prompt(v1.ALAKAZAM, 3, context_owner=1),
            self.psychic_prompt(v1.ALAKAZAM, 3, context_serial=99991),
            self.psychic_prompt(
                v1.ALAKAZAM, 3, context=SelectContext.MAIN
            ),
            self.psychic_prompt(140, 3),
        ]
        for obs in cases:
            with self.subTest(select=obs.select):
                v1.reset()
                baseline = [0]
                self.assertIs(self.invoke(obs, baseline), baseline)
                self.assertNotEqual(
                    v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
                    v1.RULE_PSYCHIC_DRAW_OPTIONAL,
                )

    def test_owner_active_at_entry_unsafe_overrides_and_preserves_owner(self):
        owner = {
            "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
            "stage": "reserved_until_exposure",
        }
        core.INTEGRATED_TRANSACTION = owner
        parent_before = core.parent_state_snapshot(policy)
        obs = self.psychic_prompt(v1.ALAKAZAM, 3)

        self.assertEqual(self.invoke(obs, [0]), [1])
        self.assertIs(core.INTEGRATED_TRANSACTION, owner)
        self.assertEqual(core.parent_state_snapshot(policy), parent_before)
        self.assertIn(
            "V3_PSYCHIC_DRAW_INHERITED_OWNER_PRESERVED",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )
        first_trace = copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE)

        self.assertEqual(self.invoke(copy.deepcopy(obs), [0]), [1])
        self.assertIs(core.INTEGRATED_TRANSACTION, owner)
        self.assertEqual(core.parent_state_snapshot(policy), parent_before)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE, first_trace)

    def test_delegate_established_owner_unsafe_overrides_and_is_preserved(self):
        owner = {
            "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
            "stage": "reserved_until_exposure",
        }
        obs = self.psychic_prompt(v1.ALAKAZAM, 3)
        self.assertEqual(
            self.invoke_establishing_owner(obs, [0], owner),
            [1],
        )
        self.assertIn(
            "V3_PSYCHIC_DRAW_INHERITED_OWNER_PRESERVED",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )
        self.assertIn(
            "V3_PSYCHIC_DRAW_OWNER_ESTABLISHED_BY_DELEGATE",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_safe_boundary_preserves_yes_under_both_owner_paths(self):
        entry_owner = {
            "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
            "stage": "reserved_until_exposure",
        }
        core.INTEGRATED_TRANSACTION = entry_owner
        entry_baseline = [0]
        self.assertIs(
            self.invoke(self.psychic_prompt(v1.ALAKAZAM, 4), entry_baseline),
            entry_baseline,
        )
        self.assertIs(core.INTEGRATED_TRANSACTION, entry_owner)

        core.INTEGRATED_TRANSACTION = None
        delegate_owner = {
            "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
            "stage": "reserved_until_exposure",
        }
        delegate_baseline = [0]
        self.assertIs(
            self.invoke_establishing_owner(
                self.psychic_prompt(v1.ALAKAZAM, 4),
                delegate_baseline,
                delegate_owner,
            ),
            delegate_baseline,
        )
        self.assertIs(core.INTEGRATED_TRANSACTION, delegate_owner)

    def test_owner_paths_preserve_no_malformed_and_nonpsychic_actions(self):
        cases = (
            (self.psychic_prompt(v1.ALAKAZAM, 3), [1]),
            (
                self.psychic_prompt(
                    v1.ALAKAZAM,
                    3,
                    options=[
                        Option(OptionType.YES),
                        Option(OptionType.YES),
                    ],
                ),
                [0],
            ),
            (self.psychic_prompt(140, 3), [0]),
        )
        for index, (obs, baseline) in enumerate(cases):
            with self.subTest(index=index, branch="entry"):
                v1.reset()
                owner = {
                    "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
                    "stage": "reserved_until_exposure",
                }
                core.INTEGRATED_TRANSACTION = owner
                self.assertIs(self.invoke(obs, baseline), baseline)
                self.assertIs(core.INTEGRATED_TRANSACTION, owner)
            with self.subTest(index=index, branch="delegate"):
                v1.reset()
                core.INTEGRATED_TRANSACTION = None
                owner = {
                    "kind": "PSYCHIC_ATTACK_READINESS_RESERVATION_V1",
                    "stage": "reserved_until_exposure",
                }
                self.assertIs(
                    self.invoke_establishing_owner(obs, baseline, owner),
                    baseline,
                )

    def test_owned_active_route_accepts_synthetic_no_without_draw_delta(self):
        start, hand = self.fx.alakazam_evolution_main()
        extras = [
            self.fx.card(1152, 0, serial)
            for serial in (8201, 8202, 8203, 8204)
        ]
        start.current.players[0].hand.extend(extras)
        start.current.players[0].handCount += len(extras)
        self.assertEqual(self.fx.call(start, [1]), [0])
        transaction = v1.V1_TRANSACTION
        transaction["start"]["own_deck"] = 3
        transaction["start_deck"] = 3

        card = hand[0]
        evolved = Pokemon(
            743,
            card.serial,
            140,
            140,
            True,
            [EnergyType.PSYCHIC],
            [self.fx.card(5, 0, 16)],
            [],
            [self.fx.card(741, 0, 17), self.fx.card(742, 0, 15)],
        )
        own = self.fx.player(
            active=[evolved],
            hand=start.current.players[0].hand[1:],
            discard=[],
            hand_count=start.current.players[0].handCount - 1,
        )
        own.deckCount = 3
        ability_state = State(
            4,
            3,
            0,
            0,
            False,
            False,
            False,
            False,
            -1,
            [],
            None,
            [own, start.current.players[1]],
        )
        ability = SelectData(
            SelectType.YES_NO,
            SelectContext.ACTIVATE,
            1,
            1,
            0,
            0,
            [Option(OptionType.YES), Option(OptionType.NO)],
            None,
            card,
            None,
        )
        self.assertEqual(
            self.fx.call(Observation(ability, [], ability_state), [0]),
            [1],
        )
        self.assertEqual(v1.V1_TRANSACTION["psychic_draw_choice"], "NO")
        self.assertNotIn(
            "V1_IRREVERSIBLE_ABORT_FAULT",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

        main_state = copy.deepcopy(ability_state)
        main_state.turnActionCount += 1
        main = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            [Option(OptionType.END), Option(OptionType.ATTACK, attackId=1072)],
            None,
            None,
            None,
        )
        self.assertEqual(
            self.fx.call(Observation(main, [], main_state), [0]),
            [1],
        )
        self.assertEqual(
            v1.V1_TRANSACTION["stage"], "await_added_attack_verify"
        )

    def test_owned_ready_bench_route_accepts_synthetic_no_without_draw_delta(self):
        start, ability, _ = self.fx.ready_bench_full_sequence()
        self.assertEqual(self.fx.call(start, [1]), [0])
        transaction = v1.V1_TRANSACTION
        transaction["start"]["own_deck"] = 3
        transaction["start_deck"] = 3
        ability.current.players[0].deckCount = 3

        self.assertEqual(self.fx.call(ability, [0]), [0])
        self.assertEqual(v1.V1_TRANSACTION["psychic_draw_choice"], "NO")
        self.assertNotIn(
            "V1_IRREVERSIBLE_ABORT_FAULT",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

        main = copy.deepcopy(ability)
        main.current.turnActionCount += 1
        main.select = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            [Option(OptionType.END), Option(OptionType.ATTACK, attackId=1072)],
            None,
            None,
            None,
        )
        self.assertEqual(self.fx.call(main, [0]), [1])
        self.assertEqual(
            v1.V1_TRANSACTION["stage"], "await_added_attack_verify"
        )

    def test_owned_no_rejects_hand_permutation_before_attack(self):
        start, ability, _ = self.fx.ready_bench_full_sequence()
        self.assertEqual(self.fx.call(start, [1]), [0])
        transaction = v1.V1_TRANSACTION
        transaction["start"]["own_deck"] = 3
        transaction["start_deck"] = 3
        ability.current.players[0].deckCount = 3
        self.assertEqual(self.fx.call(ability, [0]), [0])
        self.assertEqual(v1.V1_TRANSACTION["psychic_draw_choice"], "NO")

        mutated = copy.deepcopy(ability)
        mutated.current.turnActionCount += 1
        mutated.current.players[0].hand.reverse()
        mutated.select = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            [Option(OptionType.END), Option(OptionType.ATTACK, attackId=1072)],
            None,
            None,
            None,
        )
        self.assertEqual(self.fx.call(mutated, [1], expected_calls=0), [0])
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertIn(
            "V1_IRREVERSIBLE_ABORT_FAULT",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )
        self.assertNotIn(
            "V1_TRANSACTION_COMPLETE",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )


if __name__ == "__main__":
    unittest.main()
