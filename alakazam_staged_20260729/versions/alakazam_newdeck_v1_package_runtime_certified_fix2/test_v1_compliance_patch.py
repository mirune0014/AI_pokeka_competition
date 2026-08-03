from __future__ import annotations

import copy
from dataclasses import replace
import importlib.util
from pathlib import Path
import unittest

from cg.api import (
    AreaType,
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

from test_v1_package import V1PackageTests
import _cumulative_parent as policy
import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_integrated as integrated
import planner_final_policy as final_policy
import planner_runtime_model as runtime_model
import planner_semantics as semantics


class V1CompliancePatchTests(V1PackageTests):
    def ready_psyduck(self, serial, *, ready=True, tools=()):
        cards = (
            [self.card(5, 1), self.card(5, 1)]
            if ready
            else []
        )
        energies = [EnergyType.PSYCHIC] * len(cards)
        return Pokemon(858, serial, 50, 70, False, energies, cards, list(tools), [])

    def boss_ready_observation(self, *, hand_count=6, target_hp=50):
        hand_ids = [1182] + [1152] * (hand_count - 1)
        obs, hand = self.main_obs(
            hand_ids=hand_ids,
            target_hp=50,
            options_card_ids=[1182],
        )
        obs.current.players[0].prize = [None] * 3
        old_active = self.ready_psyduck(20, ready=False)
        target = self.ready_psyduck(21, ready=True)
        target.hp = target_hp
        obs.current.players[1].active = [old_active]
        obs.current.players[1].bench = [target]
        return obs, hand, old_active, target

    def bench_alakazam_observation(self, *, public_copies=2, appear=False):
        discard = [
            self.card(743, 0, 30 + index) for index in range(public_copies)
        ]
        obs, hand = self.main_obs(
            hand_ids=[743, 1152, 1152, 1152, 1152, 1152],
            target_hp=100,
            discard=discard,
            options_card_ids=[],
        )
        obs.current.players[0].prize = [None] * 3
        obs.current.players[0].bench = [self.kadabra(appear)]
        obs.select.option = [
            Option(
                OptionType.EVOLVE,
                area=AreaType.HAND,
                index=0,
                inPlayArea=AreaType.BENCH,
                inPlayIndex=0,
            ),
            Option(OptionType.ATTACK, attackId=1072),
            Option(OptionType.END),
        ]
        return obs, hand

    def boss_ready_full_sequence(self):
        start, hand, old_active, target = self.boss_ready_observation()
        start.current.players[1].prize = [None] * 3
        boss = hand[0]
        mine = self.player(
            active=start.current.players[0].active,
            hand=hand[1:],
            discard=[],
            hand_count=5,
        )
        mine.prize = [None] * 3
        theirs = self.player(
            active=[old_active], bench=[target], hand=None, hand_count=5
        )
        theirs.prize = [None] * 3
        child_state = State(
            4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, theirs]
        )
        child = SelectData(
            SelectType.CARD,
            SelectContext.SWITCH,
            1,
            1,
            0,
            0,
            [Option(OptionType.CARD, area=AreaType.BENCH, index=0, playerIndex=1)],
            None,
            None,
            boss,
        )
        switched = self.player(
            active=[target], bench=[old_active], hand=None, hand_count=5
        )
        switched.prize = [None] * 3
        resolved_mine = copy.deepcopy(mine)
        resolved_mine.discard = [boss]
        main_state = State(
            4, 4, 0, 0, True, False, False, False, -1, [], None,
            [resolved_mine, switched],
        )
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
        return (
            start,
            Observation(child, [], child_state),
            Observation(main, [], main_state),
        )

    def ready_bench_full_sequence(self):
        start, _ = self.bench_alakazam_observation()
        start.current.players[1].prize = [None] * 3
        card = start.current.players[0].hand[0]
        evolved = Pokemon(
            743,
            card.serial,
            140,
            140,
            True,
            [EnergyType.PSYCHIC],
            [self.card(5, 0, 16)],
            [],
            [self.card(741, 0, 17), self.card(742, 0, 15)],
        )
        own = self.player(
            active=start.current.players[0].active,
            bench=[evolved],
            hand=start.current.players[0].hand[1:],
            discard=start.current.players[0].discard,
            hand_count=5,
        )
        own.prize = [None] * 3
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
            [Option(OptionType.NO), Option(OptionType.YES)],
            None,
            card,
            None,
        )
        draws = [
            self.card(1152, 0, 601),
            self.card(1086, 0, 602),
            self.card(1231, 0, 603),
        ]
        drawn = self.player(
            active=start.current.players[0].active,
            bench=[evolved],
            hand=start.current.players[0].hand[1:] + draws,
            discard=start.current.players[0].discard,
            hand_count=8,
        )
        drawn.prize = [None] * 3
        drawn.deckCount = 27
        main_state = State(
            4,
            4,
            0,
            0,
            False,
            False,
            False,
            False,
            -1,
            [],
            None,
            [drawn, start.current.players[1]],
        )
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
        return (
            start,
            Observation(ability, [], ability_state),
            Observation(main, [], main_state),
        )

    def mutate_public_delta(self, state, mutation):
        mine, theirs = state.players[state.yourIndex], state.players[1 - state.yourIndex]
        if mutation == "turn":
            state.turn += 1
        elif mutation == "first_player":
            state.firstPlayer = 1 - state.firstPlayer
        elif mutation == "result":
            state.result = 1
        elif mutation == "action_count":
            state.turnActionCount += 1
        elif mutation == "stadium":
            state.stadium = [self.card(1253, 0, 9001)]
        elif mutation == "stadium_played":
            state.stadiumPlayed = not state.stadiumPlayed
        elif mutation == "energy_attached":
            state.energyAttached = not state.energyAttached
        elif mutation == "retreated":
            state.retreated = not state.retreated
        elif mutation == "supporter_played":
            state.supporterPlayed = not state.supporterPlayed
        elif mutation == "own_hand_count":
            mine.hand.append(self.card(1152, state.yourIndex, 9002))
            mine.handCount += 1
        elif mutation == "own_hand_content":
            mine.hand[0] = self.card(mine.hand[0].id, state.yourIndex, 9003)
        elif mutation == "opponent_hand_count":
            theirs.handCount += 1
        elif mutation == "own_deck":
            mine.deckCount += 1
        elif mutation == "opponent_deck":
            theirs.deckCount += 1
        elif mutation == "own_bench_max":
            mine.benchMax += 1
        elif mutation == "opponent_bench_max":
            theirs.benchMax += 1
        elif mutation == "own_prize_count":
            mine.prize.append(None)
        elif mutation == "opponent_prize_count":
            theirs.prize.append(None)
        elif mutation == "own_prize_public":
            mine.prize[0] = self.card(1152, state.yourIndex, 9010)
        elif mutation == "opponent_prize_public":
            theirs.prize[0] = self.card(1152, 1 - state.yourIndex, 9011)
        elif mutation == "own_discard":
            mine.discard.append(self.card(1152, state.yourIndex, 9004))
        elif mutation == "opponent_discard":
            theirs.discard.append(self.card(1152, 1 - state.yourIndex, 9005))
        elif mutation == "fields":
            theirs.active[0].hp -= 10
        elif mutation.startswith("own_status_"):
            field = mutation.removeprefix("own_status_")
            setattr(mine, field, not getattr(mine, field))
        elif mutation.startswith("opponent_status_"):
            field = mutation.removeprefix("opponent_status_")
            setattr(theirs, field, not getattr(theirs, field))
        else:
            raise AssertionError(mutation)

    def added_public_mutations(self):
        statuses = ("poisoned", "burned", "asleep", "paralyzed", "confused")
        return (
            "first_player",
            "own_bench_max",
            "opponent_bench_max",
            "own_prize_count",
            "opponent_prize_count",
            "own_prize_public",
            "opponent_prize_public",
            *(f"own_status_{field}" for field in statuses),
            *(f"opponent_status_{field}" for field in statuses),
        )

    def mutate_prompt_envelope(self, obs, mutation):
        select = obs.select
        if mutation == "type":
            select.type = (
                SelectType.CARD
                if select.type == SelectType.MAIN
                else SelectType.MAIN
            )
        elif mutation == "context":
            select.context = (
                SelectContext.MAIN
                if select.context != SelectContext.MAIN
                else SelectContext.SWITCH
            )
        elif mutation == "minCount":
            select.minCount = 0
        elif mutation == "maxCount":
            select.maxCount = 2
        elif mutation == "remainDamageCounter":
            select.remainDamageCounter = 1
        elif mutation == "remainEnergyCost":
            select.remainEnergyCost = 1
        elif mutation == "deck":
            select.deck = [self.card(1152, obs.current.yourIndex, 9020)]
        elif mutation == "contextCard":
            select.contextCard = (
                None
                if select.contextCard is not None
                else self.card(1152, obs.current.yourIndex, 9021)
            )
        elif mutation == "effect":
            select.effect = (
                None
                if select.effect is not None
                else self.card(1152, obs.current.yourIndex, 9022)
            )
        else:
            raise AssertionError(mutation)
    def assert_nonfire_preserves(self, obs, fallback):
        parent_before = core.parent_state_snapshot(policy)
        sentinel = {"classification": "COMPLIANCE_SENTINEL"}
        core.INTEGRATED_LATEST_TRACE = sentinel
        returned = self.call(obs, fallback)
        self.assertIs(returned, fallback)
        self.assertEqual(core.parent_state_snapshot(policy), parent_before)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, sentinel)
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_terminal_current_ko_precedes_all_new_routes(self):
        obs, _ = self.bench_alakazam_observation()
        obs.current.players[0].prize = [None]
        fallback = [1]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIn(
            "CURRENT_EXACT_TERMINAL_KO_PRECEDENCE",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_terminal_boss_precedes_nonterminal_current_ko(self):
        obs, hand = self.main_obs(
            hand_ids=[1182, 1152, 1152, 1152, 1152, 1152],
            target_hp=50,
            options_card_ids=[1182],
        )
        obs.current.players[0].prize = [None, None]
        obs.current.players[1].active = [self.ready_psyduck(20, ready=False)]
        obs.current.players[1].bench = [self.boss_target(23, 100)]
        self.assertEqual(self.call(obs, [1]), [0])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE["selected_rule"], v1.RULE_BOSS)
        self.assertEqual(v1.V1_TRANSACTION["mode"], "TERMINAL_PRIZE_KO")
        self.assertEqual(v1.V1_TRANSACTION["card_serial"], hand[0].serial)

    def test_boss_unique_ready_positive_is_deterministic_three_times(self):
        template, _, _, _ = self.boss_ready_observation()
        traces = []
        for _ in range(3):
            v1.reset()
            action = self.call(copy.deepcopy(template), [1])
            self.assertEqual(action, [0])
            self.assertEqual(
                v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
                v1.RULE_BOSS_READY_STOP,
            )
            traces.append(copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE))
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])

    def test_boss_unique_ready_child_reorder_and_verified_attack(self):
        obs, hand, old_active, target = self.boss_ready_observation()
        distractor = self.ready_psyduck(22, ready=False)
        obs.current.players[1].bench.append(distractor)
        self.assertEqual(self.call(obs, [1]), [0])
        boss = hand[0]
        mine = self.player(
            active=obs.current.players[0].active,
            hand=hand[1:],
            discard=[],
            hand_count=5,
        )
        mine.prize = [None] * 3
        theirs = self.player(
            active=[old_active],
            bench=[target, distractor],
            hand=None,
            hand_count=5,
        )
        child_state = State(
            4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, theirs]
        )
        child = SelectData(
            SelectType.CARD,
            SelectContext.SWITCH,
            1,
            1,
            0,
            0,
            [
                Option(
                    OptionType.CARD,
                    area=AreaType.BENCH,
                    index=1,
                    playerIndex=1,
                ),
                Option(
                    OptionType.CARD,
                    area=AreaType.BENCH,
                    index=0,
                    playerIndex=1,
                ),
            ],
            None,
            None,
            boss,
        )
        self.assertEqual(self.call(Observation(child, [], child_state), [0]), [1])
        switched = self.player(
            active=[target],
            bench=[old_active, distractor],
            hand=None,
            hand_count=5,
        )
        resolved_mine = copy.deepcopy(mine)
        resolved_mine.discard = [boss]
        main_state = State(
            4, 4, 0, 0, True, False, False, False, -1, [], None,
            [resolved_mine, switched],
        )
        main = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            [
                Option(OptionType.END),
                Option(OptionType.ATTACK, attackId=1072),
            ],
            None,
            None,
            None,
        )
        self.assertEqual(self.call(Observation(main, [], main_state), [0]), [1])
        self.assertEqual(v1.V1_TRANSACTION["stage"], "await_added_attack_verify")

    def test_boss_ready_negative_multiple_active_hfloor_and_metadata(self):
        cases = []
        multiple, _, _, _ = self.boss_ready_observation()
        multiple.current.players[1].bench.append(self.ready_psyduck(22, ready=True))
        cases.append((multiple, "V1_BOSS_READY_SET_AMBIGUOUS"))
        active_ready, _, _, _ = self.boss_ready_observation()
        active_ready.current.players[1].active = [
            self.ready_psyduck(20, ready=True)
        ]
        cases.append((active_ready, "V1_BOSS_READY_SET_AMBIGUOUS"))
        h_floor, _, _, target = self.boss_ready_observation()
        target.hp = 120
        target.maxHp = 120
        cases.append((h_floor, "V1_BOSS_H_MINUS_1_FLOOR_BLOCK"))
        ambiguous, _, _, _ = self.boss_ready_observation()
        ambiguous.current.players[1].bench[0].id = 999999
        cases.append((ambiguous, "V1_BOSS_READY_SET_AMBIGUOUS"))
        cost_modifier, _, _, _ = self.boss_ready_observation()
        cost_modifier.current.stadium = [self.card(1266, 0, 500)]
        cases.append((cost_modifier, "V1_BOSS_READY_SET_AMBIGUOUS"))
        for obs, reason_tag in cases:
            with self.subTest(reason_tag=reason_tag):
                v1.reset()
                self.assert_nonfire_preserves(obs, [1])
                self.assertIn(reason_tag, v1.LAST_V1_PACKAGE_TRACE["reason_tags"])

    def test_boss_public_three_copy_fixture_terminal_and_stop(self):
        terminal, _, _, _ = self.boss_ready_observation()
        terminal.current.players[0].discard.extend(
            [self.card(1182, 0, 501), self.card(1182, 0, 502)]
        )
        terminal.current.players[0].prize = [None, None]
        terminal.current.players[1].bench[0] = self.boss_target(23, 50)
        self.assertEqual(self.call(terminal, [1]), [0])
        self.assertEqual(v1.V1_TRANSACTION["mode"], "TERMINAL_PRIZE_KO")
        v1.reset()
        stop, _, _, _ = self.boss_ready_observation()
        stop.current.players[0].discard.extend(
            [self.card(1182, 0, 501), self.card(1182, 0, 502)]
        )
        self.assertEqual(self.call(stop, [1]), [0])
        self.assertEqual(v1.V1_TRANSACTION["mode"], "UNIQUE_READY_ATTACKER_STOP")

    def test_boss_public_mutation_aborts_before_attack(self):
        obs, hand, old_active, target = self.boss_ready_observation()
        self.assertEqual(self.call(obs, [1]), [0])
        boss = hand[0]
        mine = self.player(
            active=obs.current.players[0].active,
            hand=hand[1:],
            discard=[],
            hand_count=5,
        )
        mine.prize = [None] * 3
        child_state = State(
            4,
            3,
            0,
            0,
            True,
            False,
            False,
            False,
            -1,
            [],
            None,
            [mine, self.player(active=[old_active], bench=[target], hand=None)],
        )
        child = SelectData(
            SelectType.CARD,
            SelectContext.SWITCH,
            1,
            1,
            0,
            0,
            [
                Option(
                    OptionType.CARD,
                    area=AreaType.BENCH,
                    index=0,
                    playerIndex=1,
                )
            ],
            None,
            None,
            boss,
        )
        self.assertEqual(self.call(Observation(child, [], child_state), [0]), [0])
        mutated = copy.deepcopy(target)
        mutated.energyCards.pop()
        mutated.energies.pop()
        switched = self.player(
            active=[mutated], bench=[old_active], hand=None, hand_count=5
        )
        mine.discard = [boss]
        main_state = State(
            4, 4, 0, 0, True, False, False, False, -1, [], None, [mine, switched]
        )
        main = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)],
            None,
            None,
            None,
        )
        fallback = [1]
        self.assertEqual(self.call(Observation(main, [], main_state), fallback), [0])
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertIn(
            "V1_BOSS_PUBLIC_MUTATION_ABORT",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_active_kadabra_public_copy_attribution(self):
        obs, _ = self.alakazam_evolution_main()
        obs.current.players[0].discard = [
            self.card(743, 0, 401),
            self.card(743, 0, 402),
            self.card(743, 0, 403),
        ]
        self.assertEqual(self.call(obs, [1]), [0])
        self.assertEqual(
            v1.V1_TRANSACTION["identity_reason"],
            "V1_ALAKAZAM_4TH_PUBLICLY_PROVEN",
        )
        v1.reset()
        unknown, _ = self.alakazam_evolution_main()
        self.assertEqual(self.call(unknown, [1]), [0])
        self.assertEqual(
            v1.V1_TRANSACTION["identity_reason"], "UNKNOWN_IDENTICAL_CARD_ID"
        )

    def test_ready_bench_alakazam_positive_three_repetitions_and_children(self):
        template, hand = self.bench_alakazam_observation()
        traces = []
        for _ in range(3):
            v1.reset()
            self.assertEqual(self.call(copy.deepcopy(template), [1]), [0])
            traces.append(copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE))
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])
        v1.reset()
        obs = copy.deepcopy(template)
        self.assertEqual(self.call(obs, [1]), [0])
        card = obs.current.players[0].hand[0]
        evolved = Pokemon(
            743,
            card.serial,
            140,
            140,
            True,
            [EnergyType.PSYCHIC],
            [self.card(5, 0, 16)],
            [],
            [self.card(741, 0, 17), self.card(742, 0, 15)],
        )
        own = self.player(
            active=obs.current.players[0].active,
            bench=[evolved],
            hand=obs.current.players[0].hand[1:],
            discard=obs.current.players[0].discard,
            hand_count=5,
        )
        own.prize = [None] * 3
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
            [own, obs.current.players[1]],
        )
        ability = SelectData(
            SelectType.YES_NO,
            SelectContext.ACTIVATE,
            1,
            1,
            0,
            0,
            [Option(OptionType.NO), Option(OptionType.YES)],
            None,
            card,
            None,
        )
        self.assertEqual(self.call(Observation(ability, [], ability_state), [0]), [1])
        draws = [
            self.card(1152, 0, 601),
            self.card(1086, 0, 602),
            self.card(1231, 0, 603),
        ]
        drawn = self.player(
            active=obs.current.players[0].active,
            bench=[evolved],
            hand=obs.current.players[0].hand[1:] + draws,
            discard=obs.current.players[0].discard,
            hand_count=8,
        )
        drawn.prize = [None] * 3
        drawn.deckCount = 27
        main_state = State(
            4,
            4,
            0,
            0,
            False,
            False,
            False,
            False,
            -1,
            [],
            None,
            [drawn, obs.current.players[1]],
        )
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
        self.assertEqual(self.call(Observation(main, [], main_state), [0]), [1])

    def test_ready_bench_alakazam_negative_boundaries(self):
        shortage, _ = self.bench_alakazam_observation(public_copies=1)
        immature, _ = self.bench_alakazam_observation(appear=True)
        no_energy, _ = self.bench_alakazam_observation()
        no_energy.current.players[0].bench[0].energies = []
        no_energy.current.players[0].bench[0].energyCards = []
        duplicate, _ = self.bench_alakazam_observation()
        duplicate.select.option.insert(1, copy.deepcopy(duplicate.select.option[0]))
        thin, _ = self.bench_alakazam_observation()
        thin.current.players[0].deckCount = 3
        terminal, _ = self.bench_alakazam_observation()
        terminal.current.players[0].prize = [None]
        for obs in (shortage, immature, no_energy, duplicate, thin, terminal):
            v1.reset()
            self.assert_nonfire_preserves(obs, [len(obs.select.option) - 2])

    def test_ready_bench_rejects_public_proof_target_serial_collision(self):
        obs, _ = self.bench_alakazam_observation()
        attacker_serial = obs.current.players[0].active[0].serial
        target_serial = obs.current.players[1].active[0].serial
        original = v1._public_other_alakazam_serials
        v1._public_other_alakazam_serials = (
            lambda parent, observation, excluded: (
                attacker_serial,
                target_serial,
                31,
            )
        )
        try:
            self.assert_nonfire_preserves(obs, [1])
        finally:
            v1._public_other_alakazam_serials = original
    def test_full_boss_and_alakazam_transactions_repeat_three_times(self):
        cases = (
            ("boss", self.boss_ready_full_sequence, ([0], [0], [1])),
            ("alakazam", self.ready_bench_full_sequence, ([0], [1], [1])),
        )
        for name, builder, expected in cases:
            template = builder()
            first_trace = None
            for repetition in range(3):
                with self.subTest(route=name, repetition=repetition):
                    v1.reset()
                    core.INTEGRATED_TRANSACTION = None
                    start, child, main = copy.deepcopy(template)
                    self.assertEqual(self.call(start, [1]), expected[0])
                    route_trace = copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE)
                    self.assertEqual(self.call(child, [0]), expected[1])
                    self.assertEqual(self.call(main, [0]), expected[2])
                    self.assertEqual(
                        v1.V1_TRANSACTION["stage"], "await_added_attack_verify"
                    )
                    if first_trace is None:
                        first_trace = route_trace
                    else:
                        self.assertEqual(route_trace, first_trace)

    def test_alakazam_every_public_delta_aborts_at_both_boundaries(self):
        mutations = (
            "turn",
            "result",
            "action_count",
            "stadium",
            "stadium_played",
            "energy_attached",
            "retreated",
            "supporter_played",
            "own_hand_count",
            "own_hand_content",
            "opponent_hand_count",
            "own_deck",
            "opponent_deck",
            "own_discard",
            "opponent_discard",
            "fields",
        ) + self.added_public_mutations()
        template = self.ready_bench_full_sequence()
        for boundary in ("ability", "attack"):
            for mutation in mutations:
                with self.subTest(boundary=boundary, mutation=mutation):
                    v1.reset()
                    start, ability, main = copy.deepcopy(template)
                    self.assertEqual(self.call(start, [1]), [0])
                    if boundary == "ability":
                        target = ability
                    else:
                        self.assertEqual(self.call(ability, [0]), [1])
                        target = main
                    self.mutate_public_delta(target.current, mutation)
                    fallback = [0]
                    self.assertEqual(self.call(target, fallback), [0])
                    self.assertIsNone(v1.V1_TRANSACTION)
                    self.assertIn(
                        "V1_ALAKAZAM_PUBLIC_MUTATION_ABORT",
                        v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                    )

    def test_boss_every_post_switch_public_delta_aborts(self):
        mutations = (
            "turn",
            "result",
            "action_count",
            "stadium",
            "stadium_played",
            "energy_attached",
            "retreated",
            "supporter_played",
            "own_hand_count",
            "own_hand_content",
            "opponent_hand_count",
            "own_deck",
            "opponent_deck",
            "own_discard",
            "opponent_discard",
            "fields",
        ) + self.added_public_mutations()
        template = self.boss_ready_full_sequence()
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                v1.reset()
                start, child, main = copy.deepcopy(template)
                self.assertEqual(self.call(start, [1]), [0])
                self.assertEqual(self.call(child, [0]), [0])
                self.mutate_public_delta(main.current, mutation)
                fallback = [0]
                self.assertEqual(self.call(main, fallback), [0])
                self.assertIsNone(v1.V1_TRANSACTION)
                self.assertIn(
                    "V1_BOSS_PUBLIC_MUTATION_ABORT",
                    v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                )

    def test_public_prize_fingerprint_preserves_order_and_validates_rows(self):
        obs, _, _, _ = self.boss_ready_observation()
        obs.current.players[0].prize = [
            None,
            self.card(1152, 0, 9030),
            None,
        ]
        snapshot = v1._public_state(policy, obs)
        self.assertIsNotNone(snapshot)
        self.assertEqual(
            snapshot["own_prize"],
            (
                ("HIDDEN",),
                ("PUBLIC", 1152, 9030, 0),
                ("HIDDEN",),
            ),
        )

        wrong_owner = copy.deepcopy(obs)
        wrong_owner.current.players[0].prize[1].playerIndex = 1
        self.assertIsNone(v1._public_state(policy, wrong_owner))

        invalid_serial = copy.deepcopy(obs)
        invalid_serial.current.players[0].prize[1].serial = 0
        self.assertIsNone(v1._public_state(policy, invalid_serial))

    def test_all_added_child_prompt_envelopes_fail_closed(self):
        mutations = (
            "type",
            "context",
            "minCount",
            "maxCount",
            "remainDamageCounter",
            "remainEnergyCost",
            "deck",
            "contextCard",
            "effect",
            "option_census",
        )
        boundaries = (
            (
                "boss_switch",
                self.boss_ready_full_sequence,
                1,
                "V1_BOSS_PUBLIC_MUTATION_ABORT",
            ),
            (
                "boss_final_main",
                self.boss_ready_full_sequence,
                2,
                "V1_BOSS_PUBLIC_MUTATION_ABORT",
            ),
            (
                "alakazam_activate",
                self.ready_bench_full_sequence,
                1,
                "V1_ALAKAZAM_PUBLIC_MUTATION_ABORT",
            ),
            (
                "alakazam_final_main",
                self.ready_bench_full_sequence,
                2,
                "V1_ALAKAZAM_PUBLIC_MUTATION_ABORT",
            ),
        )
        for name, builder, boundary_index, reason_tag in boundaries:
            for mutation in mutations:
                with self.subTest(boundary=name, mutation=mutation):
                    v1.reset()
                    start, child, main = copy.deepcopy(builder())
                    self.assertEqual(self.call(start, [1]), [0])
                    target = child
                    if boundary_index == 2:
                        self.assertEqual(
                            self.call(child, [0]),
                            [0] if name.startswith("boss") else [1],
                        )
                        target = main
                    if mutation == "option_census":
                        target.select.option.append(
                            copy.deepcopy(target.select.option[0])
                        )
                    else:
                        self.mutate_prompt_envelope(target, mutation)
                    fallback = [0]
                    self.assertEqual(self.call(target, fallback), [0])
                    self.assertIsNone(v1.V1_TRANSACTION)
                    if mutation == "option_census":
                        self.assertIn(
                            "AMBIGUOUS_PUBLIC_METADATA",
                            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                        )
                    else:
                        self.assertIn(
                            reason_tag,
                            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
                        )

    def test_boss_switch_allows_exact_poison_and_burn_clearing(self):
        start, child, main = self.boss_ready_full_sequence()
        start.current.players[1].poisoned = True
        start.current.players[1].burned = True
        child.current.players[1].poisoned = True
        child.current.players[1].burned = True
        self.assertEqual(self.call(start, [1]), [0])
        self.assertEqual(self.call(child, [0]), [0])
        self.assertEqual(self.call(main, [0]), [1])
        self.assertEqual(v1.V1_TRANSACTION["stage"], "await_added_attack_verify")
    def test_boss_ready_proof_rejects_real_energy_and_tool_modifiers(self):
        special, _, _, target = self.boss_ready_observation()
        target.energyCards[0] = self.card(11, 1, 801)
        target.energies[0] = EnergyType.COLORLESS
        self.assertFalse(v1._ready_cost_environment_exact(policy, special.current))
        self.assert_nonfire_preserves(special, [1])

        tool, _, _, target = self.boss_ready_observation()
        target.tools = [self.card(1168, 1, 802)]
        self.assertFalse(v1._ready_cost_environment_exact(policy, tool.current))
        self.assert_nonfire_preserves(tool, [1])

        status, _, _, _ = self.boss_ready_observation()
        status.current.players[1].asleep = True
        self.assertIsNone(v1._opponent_ready_set(policy, status))
        self.assert_nonfire_preserves(status, [1])

    def test_removed_real_transaction_roles_and_guards_are_denied(self):
        obs, hand = self.main_obs(
            hand_ids=[1161, 1152, 1152, 1152], options_card_ids=[]
        )
        obs.current.players[0].active = [
            Pokemon(305, 10, 70, 70, False, [], [], [], [])
        ]
        obs.current.players[1].active = [self.ready_psyduck(20, ready=True)]
        obs.select.option = [
            Option(
                OptionType.ATTACH,
                area=AreaType.HAND,
                index=0,
                inPlayArea=AreaType.ACTIVE,
                inPlayIndex=0,
            ),
            Option(OptionType.END),
        ]
        snap = runtime_model.public_snapshot(policy, obs)
        self.assertIsNotNone(snap)
        source_path = (
            Path(__file__).resolve().parent.parent
            / "alakazam_newdeck_v1_package"
            / "planner_policy.py"
        )
        spec = importlib.util.spec_from_file_location(
            "legacy_real_fan_transaction_fixture", source_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        original_fan = policy.card_table[1161]
        fixture_skill = replace(
            original_fan.skills[0],
            text=(
                "If the Pokemon this card is attached to is in the Active Spot "
                "and is damaged by an attack, move an Energy from the Attacking "
                "Pokemon to 1 of your opponent's Benched Pokemon."
            ),
        )
        policy.card_table[1161] = replace(original_fan, skills=[fixture_skill])
        try:
            real = legacy._build_fan_attach(policy, obs, snap, [1])
        finally:
            policy.card_table[1161] = original_fan
        self.assertIsNotNone(real)
        transaction = real[2]["transaction"]
        self.assertEqual(transaction["kind"], "HANDHELD_FAN_RESPONSE")
        self.assertTrue(
            any(
                reservation.token == f"tool:{hand[0].serial}"
                for reservation in real[0].resource_ledger.reservations
            )
        )
        self.assertIsNone(core._build_fan_attach(policy, obs, snap, [1]))

        raw = self.raw(obs)
        calls = []

        def delegate(value):
            calls.append(value)
            core.INTEGRATED_TRANSACTION = copy.deepcopy(transaction)
            return [0]

        self.assertEqual(v1.agent(policy, delegate, raw), [1])
        self.assertEqual(len(calls), 1)
        self.assertIsNone(core.INTEGRATED_TRANSACTION)
        self.assertIn(
            "V1_REMOVED_PARENT_TRANSACTION_FILTER",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

        roles = semantics.public_roles(policy, obs)
        for card_id in (858, 142):
            source = self.card(card_id, 0)
            option = Option(OptionType.PLAY, index=0)
            allowed, _, role = integrated._bench_gate(
                policy, obs, option, source, roles
            )
            self.assertFalse(allowed)
            self.assertIsNone(role)

        own_psyduck = Pokemon(
            858,
            40,
            50,
            70,
            False,
            [EnergyType.PSYCHIC, EnergyType.PSYCHIC],
            [self.card(5, 0, 41), self.card(5, 0, 42)],
            [],
            [],
        )
        own_genesect = Pokemon(
            142,
            44,
            100,
            100,
            False,
            [EnergyType.METAL, EnergyType.PSYCHIC, EnergyType.PSYCHIC],
            [
                self.card(8, 0, 45),
                self.card(5, 0, 46),
                self.card(5, 0, 47),
            ],
            [],
            [],
        )
        for removed_pokemon in (own_psyduck, own_genesect):
            role_obs = copy.deepcopy(obs)
            role_obs.current.players[0].active = [removed_pokemon]
            own_roles = semantics.public_roles(policy, role_obs)
            self.assertIsNone(own_roles.H0)
            self.assertFalse(own_roles.ledger.roles)

        helmet_obs = copy.deepcopy(obs)
        helmet_obs.current.players[0].deckCount = 2
        helmet_obs.current.players[0].active[0].tools = [self.card(1156, 0, 43)]
        self.assertIsNone(policy._turn_guard_thin_deck_helmet_action(helmet_obs, [0]))
        events = final_policy._ordered_draw_clock(policy, helmet_obs).own.ordered_draws
        self.assertEqual(events[1], ("opponent_turn_helmet_or_fan", 0, True))
    def test_removed_own_cards_are_filtered_and_forced_prompt_is_tagged(self):
        for card_id in sorted(v1.REMOVED_OWN_CARD_IDS):
            v1.reset()
            obs, _ = self.main_obs(
                hand_ids=[card_id, 1152, 1152, 1152],
                options_card_ids=[card_id, 1152],
            )
            self.assertEqual(self.call(obs, [0]), [1])
            self.assertIn(
                "V1_REMOVED_OWN_CARD_FILTER",
                v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
            )
        forced, _ = self.main_obs(hand_ids=[142], options_card_ids=[142])
        forced.select.option = [forced.select.option[0]]
        self.assertEqual(self.call(forced, [0]), [0])
        self.assertIn(
            "V1_REMOVED_CARD_FORCED_PROMPT_ONLY",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_opponent_and_public_removed_card_semantics_remain_available(self):
        obs, _, _, _ = self.boss_ready_observation()
        genesect = Pokemon(
            142,
            31,
            100,
            100,
            False,
            [EnergyType.METAL, EnergyType.PSYCHIC, EnergyType.PSYCHIC],
            [
                self.card(8, 1, 701),
                self.card(5, 1, 702),
                self.card(5, 1, 703),
            ],
            [self.card(1156, 1, 704), self.card(1161, 1, 705)],
            [],
        )
        obs.current.players[1].bench = [genesect]
        ready = v1._opponent_ready_set(policy, obs)
        self.assertIsNotNone(ready)
        self.assertEqual(ready[0][2], genesect.serial)
        obs.current.players[1].bench = [self.ready_psyduck(32, ready=True)]
        obs.current.stadium = [self.card(1264, 1, 706)]
        ready = v1._opponent_ready_set(policy, obs)
        self.assertIsNotNone(ready)
        self.assertEqual(ready[0][2], 32)
        self.assertTrue(v1._cost_environment_clear(policy, obs.current))


if __name__ == "__main__":
    unittest.main()
