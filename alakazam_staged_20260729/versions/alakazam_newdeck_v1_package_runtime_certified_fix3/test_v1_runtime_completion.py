from __future__ import annotations

import copy
import unittest

from cg.api import (
    AreaType,
    Card,
    EnergyType,
    Log,
    LogType,
    Observation,
    Option,
    OptionType,
    Pokemon,
    SelectContext,
    SelectData,
    SelectType,
    State,
)

import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model
import test_v1_compliance_patch as compliance_tests


class V1RuntimeCompletionTests(unittest.TestCase):
    """Seeded-engine API fixtures for exact v1 transaction ownership."""

    def setUp(self):
        self.fx = compliance_tests.V1CompliancePatchTests(methodName="runTest")
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    @property
    def policy(self):
        return __import__("_cumulative_parent")

    def invoke(self, obs, fallback, expected_calls):
        raw = self.fx.raw(obs)
        calls = []
        action = v1.agent(
            self.policy,
            lambda value: calls.append(value) or fallback,
            raw,
        )
        self.assertEqual(len(calls), expected_calls)
        self.assertEqual(
            v1.LAST_V1_PACKAGE_TRACE["removed_rule_hit_status"], "KNOWN"
        )
        self.assertIsInstance(
            v1.LAST_V1_PACKAGE_TRACE["removed_rule_hits"], list
        )
        return action

    def assert_complete(self, expected_action):
        self.assertEqual(
            v1.LAST_V1_PACKAGE_TRACE["selected_action"], expected_action
        )
        tags = v1.LAST_V1_PACKAGE_TRACE["reason_tags"]
        self.assertIn("V1_TRANSACTION_COMPLETE", tags)
        self.assertNotIn("V1_TRANSACTION_ABORT", tags)
        self.assertNotIn("V1_IRREVERSIBLE_ABORT_FAULT", tags)
        self.assertIsNone(v1.V1_TRANSACTION)

    def assert_fault(self):
        tags = v1.LAST_V1_PACKAGE_TRACE["reason_tags"]
        self.assertIn("V1_IRREVERSIBLE_ABORT_FAULT", tags)
        self.assertNotIn("V1_TRANSACTION_ABORT", tags)
        self.assertNotIn("V1_TRANSACTION_COMPLETE", tags)
        self.assertIsNone(v1.V1_TRANSACTION)

    def boss_evolved_full_sequence(self):
        start, child, main = self.fx.boss_ready_full_sequence()
        target = self.fx.kadabra(False)
        target.serial = 7201
        target.energyCards = [self.fx.card(5, 1, 7202)]
        target.energies = [EnergyType.PSYCHIC]
        target.preEvolution = [self.fx.card(741, 1, 7203)]
        start.current.players[1].bench[0] = copy.deepcopy(target)
        child.current.players[1].bench[0] = copy.deepcopy(target)
        main.current.players[1].active[0] = copy.deepcopy(target)
        return start, child, main

    def boss_live_alakazam_full_stack_sequence(self):
        start, child, main = self.fx.boss_ready_full_sequence()
        target = Pokemon(
            743,
            72,
            100,
            140,
            True,
            [EnergyType.PSYCHIC],
            [self.fx.card(5, 1, 119)],
            [],
            [self.fx.card(741, 1, 65), self.fx.card(742, 1, 69)],
        )
        old_active = Pokemon(743, 20, 140, 140, True, [], [], [], [])
        start.current.players[1].active[0] = copy.deepcopy(old_active)
        start.current.players[1].bench[0] = copy.deepcopy(target)
        child.current.players[1].active[0] = copy.deepcopy(old_active)
        child.current.players[1].bench[0] = copy.deepcopy(target)
        main.current.players[1].active[0] = copy.deepcopy(target)
        main.current.players[1].bench[0] = copy.deepcopy(old_active)
        for observation in (start, child, main):
            observation.current.players[0].prize = [None]
        return start, child, main

    def ko_verification(
        self, main, target_serial, *, reverse_pre_evolution=True
    ):
        verify = copy.deepcopy(main)
        owner = verify.current.yourIndex
        mine = verify.current.players[owner]
        theirs = verify.current.players[1 - owner]
        target = next(
            pokemon for pokemon in theirs.active if pokemon.serial == target_serial
        )
        target_prizes = self.policy.prize_count(target)
        pre_evolutions = (
            reversed(target.preEvolution)
            if reverse_pre_evolution
            else target.preEvolution
        )
        target_moves = (
            (target.id, target.serial, AreaType.ACTIVE),
            *((card.id, card.serial, AreaType.PRE_EVOLUTION) for card in pre_evolutions),
            *((card.id, card.serial, AreaType.ENERGY) for card in target.energyCards),
            *((card.id, card.serial, AreaType.TOOL) for card in target.tools),
        )
        theirs.active = []
        theirs.poisoned = False
        theirs.burned = False
        theirs.asleep = False
        theirs.paralyzed = False
        theirs.confused = False
        theirs.discard.extend(
            Card(card_id, serial, 1 - owner)
            for card_id, serial, _ in target_moves
        )
        verify.current.turnActionCount += 1
        expected_taken = min(target_prizes, len(mine.prize))
        verify.select = SelectData(
            SelectType.CARD, SelectContext.TO_HAND,
            expected_taken, expected_taken, 0, 0,
            [
                Option(OptionType.CARD, area=AreaType.PRIZE, index=index, playerIndex=owner)
                for index in range(len(mine.prize))
            ],
            None, None, None,
        )
        damage = 20 * mine.handCount
        verify.logs = [
            Log(
                LogType.ATTACK, playerIndex=owner,
                cardId=mine.active[0].id, serial=mine.active[0].serial,
                attackId=1072,
            ),
            Log(
                LogType.HP_CHANGE, playerIndex=1 - owner,
                cardId=target.id, serial=target.serial,
                value=-damage, putDamageCounter=True,
            ),
            *(
                Log(
                    LogType.MOVE_CARD, playerIndex=1 - owner,
                    cardId=card_id, serial=serial, fromArea=area,
                    toArea=AreaType.DISCARD,
                )
                for card_id, serial, area in target_moves
            ),
        ]
        return verify

    def mine_chain(self):
        start, hand = self.fx.main_obs(
            hand_ids=[1152, 1266, 1152, 1152, 1152, 1152],
            target_hp=100,
            options_card_ids=[1266],
        )
        target = self.fx.tera_target(3)
        target.serial = 9601
        for index, card in enumerate(target.energyCards):
            card.serial = 9602 + index
        start.current.players[1].active = [copy.deepcopy(target)]
        start.current.players[0].prize = [None] * 3
        start.current.players[1].prize = [None] * 3
        mine_card = hand[1]
        own = self.fx.player(
            active=start.current.players[0].active,
            hand=[hand[0]] + hand[2:],
            discard=[],
            hand_count=5,
        )
        own.prize = [None] * 3
        opponent = self.fx.player(
            active=[copy.deepcopy(target)], hand=None, hand_count=5
        )
        opponent.prize = [None] * 3
        main_state = State(
            4, 3, 0, 0, False, True, False, False, -1,
            [mine_card], None, [own, opponent],
        )
        main_select = SelectData(
            SelectType.MAIN, SelectContext.MAIN,
            1, 1, 0, 0,
            [Option(OptionType.END), Option(OptionType.ATTACK, attackId=1072)],
            None, None, None,
        )
        return start, Observation(main_select, [], main_state)

    def lana_chain(self):
        recovered = [
            self.fx.card(743, 0, 9301),
            self.fx.card(741, 0, 9302),
            self.fx.card(5, 0, 9303),
        ]
        start, hand = self.fx.main_obs(
            hand_ids=[1184, 1152, 1152, 1152],
            target_hp=120,
            discard=recovered,
            options_card_ids=[1184],
        )
        lana = hand[0]
        mine = self.fx.player(
            active=start.current.players[0].active,
            hand=hand[1:],
            discard=recovered,
            hand_count=3,
        )
        child_state = State(
            4, 3, 0, 0, True, False, False, False, -1, [], None,
            [mine, start.current.players[1]],
        )
        child = Observation(
            SelectData(
                SelectType.CARD,
                SelectContext.TO_HAND,
                1,
                3,
                0,
                0,
                [
                    Option(OptionType.CARD, area=AreaType.DISCARD, index=index, playerIndex=0)
                    for index in (2, 0, 1)
                ],
                None,
                None,
                lana,
            ),
            [],
            child_state,
        )
        resolved = self.fx.player(
            active=start.current.players[0].active,
            hand=hand[1:] + recovered,
            discard=[lana],
            hand_count=6,
        )
        verify_state = State(
            4, 4, 0, 0, True, False, False, False, -1, [], None,
            [resolved, start.current.players[1]],
        )
        verify = Observation(
            SelectData(
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
            ),
            [
                Log(
                    LogType.MOVE_CARD,
                    playerIndex=0,
                    cardId=card.id,
                    serial=card.serial,
                    fromArea=AreaType.DISCARD,
                    toArea=AreaType.HAND,
                )
                for card in (recovered[0], recovered[2], recovered[1])
            ],
            verify_state,        )
        return start, child, verify

    def hammer_chain(self):
        energy = self.fx.card(11, 1, 9401)
        start, hand = self.fx.main_obs(
            hand_ids=[1081, 1152, 1152, 1152, 1152, 1152],
            target_hp=100,
            target_energy=[(EnergyType.COLORLESS, energy)],
            options_card_ids=[1081],
        )
        hammer = hand[0]
        mine = self.fx.player(
            active=start.current.players[0].active,
            hand=hand[1:],
            discard=[],
            hand_count=5,
        )
        child_state = State(
            4, 3, 0, 0, False, False, False, False, -1, [], None,
            [mine, start.current.players[1]],
        )
        child = Observation(
            SelectData(
                SelectType.ENERGY,
                SelectContext.DISCARD_ENERGY,
                1,
                1,
                0,
                1,
                [
                    Option(
                        OptionType.ENERGY,
                        area=AreaType.ACTIVE,
                        index=0,
                        playerIndex=1,
                        energyIndex=0,
                        count=1,
                    )
                ],
                None,
                None,
                hammer,
            ),
            [],
            child_state,
        )
        target = copy.deepcopy(start.current.players[1].active[0])
        target.energies = []
        target.energyCards = []
        opponent = self.fx.player(
            active=[target],
            hand=None,
            hand_count=5,
            discard=[energy],
        )
        resolved = self.fx.player(
            active=start.current.players[0].active,
            hand=hand[1:],
            discard=[hammer],
            hand_count=5,
        )
        verify_state = State(
            4, 4, 0, 0, False, False, False, False, -1, [], None,
            [resolved, opponent],
        )
        verify = Observation(
            SelectData(
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
            ),
            [
                Log(
                    LogType.MOVE_CARD,
                    playerIndex=1,
                    cardId=energy.id,
                    serial=energy.serial,
                    fromArea=AreaType.ENERGY,
                    toArea=AreaType.DISCARD,
                )
            ],
            verify_state,        )
        return start, child, verify

    def grow_grass_hammer_verification(
        self,
        before_hp,
        before_max_hp,
        post_hp,
        post_max_hp,
        *,
        area=AreaType.ACTIVE,
        energy_rows=None,
        energy_index=0,
    ):
        if energy_rows is None:
            energy_rows = [
                (EnergyType.GRASS, self.fx.card(18, 1, 9401)),
            ]
        hammer = self.fx.card(1081, 0, 9402)
        hand = [self.fx.card(1152, 0, 9500 + index) for index in range(8)]
        target = Pokemon(
            345,
            9450,
            before_hp,
            before_max_hp,
            False,
            [unit for unit, _ in energy_rows],
            [card for _, card in energy_rows],
            [],
            [],
        )
        other_active = self.fx.target(60)
        if area == AreaType.ACTIVE:
            opponent_active = [target]
            opponent_bench = []
            hammer_mode = "ENABLE_COUNTER_KO"
        else:
            opponent_active = [other_active]
            opponent_bench = [target]
            hammer_mode = "STOP_SOLE_BACKUP"
        mine_before = self.fx.player(
            active=[self.fx.alakazam()], hand=hand, discard=[], hand_count=8
        )
        theirs_before = self.fx.player(
            active=opponent_active,
            bench=opponent_bench,
            hand=None,
            hand_count=5,
        )
        before_state = State(
            4, 3, 0, 0, False, False, False, False, -1, [], None,
            [mine_before, theirs_before],
        )
        before = Observation(
            SelectData(
                SelectType.ENERGY,
                SelectContext.DISCARD_ENERGY,
                1,
                1,
                0,
                1,
                [],
                None,
                None,
                hammer,
            ),
            [],
            before_state,
        )
        post_play = v1._public_state(self.policy, before)
        self.assertIsNotNone(post_play)

        selected = energy_rows[energy_index][1]
        resolved_target = copy.deepcopy(target)
        resolved_target.hp = post_hp
        resolved_target.maxHp = post_max_hp
        resolved_target.energies.pop(energy_index)
        resolved_target.energyCards.pop(energy_index)
        if area == AreaType.ACTIVE:
            resolved_active = [resolved_target]
            resolved_bench = []
        else:
            resolved_active = [other_active]
            resolved_bench = [resolved_target]
        mine_after = self.fx.player(
            active=[self.fx.alakazam()], hand=hand, discard=[hammer], hand_count=8
        )
        theirs_after = self.fx.player(
            active=resolved_active,
            bench=resolved_bench,
            hand=None,
            hand_count=5,
            discard=[selected],
        )
        after_state = State(
            4, 4, 0, 0, False, False, False, False, -1, [], None,
            [mine_after, theirs_after],
        )
        verify = Observation(
            SelectData(
                SelectType.MAIN,
                SelectContext.MAIN,
                1,
                1,
                0,
                0,
                [
                    Option(OptionType.ATTACK, attackId=1072),
                    Option(OptionType.END),
                ],
                None,
                None,
                None,
            ),
            [
                Log(
                    LogType.MOVE_CARD,
                    playerIndex=1,
                    cardId=selected.id,
                    serial=selected.serial,
                    fromArea=AreaType.ENERGY,
                    toArea=AreaType.DISCARD,
                )
            ],
            after_state,
        )
        transaction = {
            "owner": 0,
            "pokemon_serial": target.serial,
            "pokemon_index": 0,
            "energy_area": int(area),
            "energy_index": energy_index,
            "energy_row": (selected.id, selected.serial, selected.playerIndex),
            "card_row": (hammer.id, hammer.serial, hammer.playerIndex),
            "hammer_mode": hammer_mode,
            "post_play": post_play,
        }
        return verify, transaction
    def xerosic_chain(self):
        start, hand = self.fx.main_obs(
            hand_ids=[1197, 1152, 1152, 1152, 1152, 1152],
            target_hp=100,
            options_card_ids=[1197],
        )
        xerosic = hand[0]
        discarded = [
            self.fx.card(1152, 1, 9501),
            self.fx.card(1152, 1, 9502),
        ]
        opponent = self.fx.player(
            active=start.current.players[1].active,
            hand=None,
            hand_count=3,
            discard=discarded,
        )
        resolved = self.fx.player(
            active=start.current.players[0].active,
            hand=hand[1:],
            discard=[xerosic],
            hand_count=5,
        )
        verify_state = State(
            4, 4, 0, 0, True, False, False, False, -1, [], None,
            [resolved, opponent],
        )
        verify = Observation(
            SelectData(
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
            ),
            [
                Log(
                    LogType.PLAY,
                    playerIndex=0,
                    cardId=xerosic.id,
                    serial=xerosic.serial,
                ),
                *(
                    Log(
                        LogType.MOVE_CARD,
                        playerIndex=1,
                        cardId=card.id,
                        serial=card.serial,
                        fromArea=AreaType.HAND,
                        toArea=AreaType.DISCARD,
                    )
                    for card in discarded
                ),
            ],
            verify_state,        )
        return start, verify

    def test_mine_positive_play_attack_prize_chain_completes(self):
        start, main = self.mine_chain()
        self.assertEqual(self.invoke(start, [2], 1), [0])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE["selected_rule"], v1.RULE_MINE)
        self.assertEqual(self.invoke(main, [0], 0), [1])
        target_serial = main.current.players[1].active[0].serial
        final = self.ko_verification(main, target_serial)
        self.assertEqual(self.invoke(final, [0, 1], 1), [0, 1])
        self.assert_complete([0, 1])

    def test_mine_attack_verifier_rejects_exact_mutations(self):
        for mutation in (
            "hp_zero_active",
            "attack_log",
            "action_count",
            "prize_prompt",
            "physical_move",
        ):
            with self.subTest(mutation=mutation):
                v1.reset()
                start, main = self.mine_chain()
                self.assertEqual(self.invoke(start, [2], 1), [0])
                self.assertEqual(self.invoke(main, [0], 0), [1])
                target_serial = main.current.players[1].active[0].serial
                final = self.ko_verification(main, target_serial)
                if mutation == "hp_zero_active":
                    target = copy.deepcopy(main.current.players[1].active[0])
                    target.hp = 0
                    final.current.players[1].active = [target]
                elif mutation == "attack_log":
                    final.logs[0].attackId += 1
                elif mutation == "action_count":
                    final.current.turnActionCount -= 1
                elif mutation == "prize_prompt":
                    final.select.maxCount += 1
                else:
                    final.current.players[1].discard[-1].serial += 1
                action = self.invoke(final, [0, 1], 0)
                parsed = self.policy.to_observation_class(self.fx.raw(final))
                self.assertTrue(v1.model.action_is_valid(parsed, action))
                self.assert_fault()
    def test_five_positive_full_chains_complete(self):
        start, child, main = self.boss_evolved_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        target_serial = start.current.players[1].bench[0].serial
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(self.invoke(main, [0], 0), [1])
        final = self.ko_verification(main, target_serial)
        self.assertEqual(self.invoke(final, [0], 1), [0])
        self.assert_complete([0])

        v1.reset()
        start, child, verify = self.hammer_chain()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(self.invoke(verify, [0], 1), [0])
        self.assert_complete([0])

        v1.reset()
        start, child, verify = self.lana_chain()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [1, 0, 2])
        self.assertEqual(self.invoke(verify, [0], 1), [0])
        self.assert_complete([0])

        v1.reset()
        start, verify = self.xerosic_chain()
        self.assertEqual(self.invoke(start, [2], 1), [0])
        self.assertEqual(self.invoke(verify, [0], 1), [0])
        self.assert_complete([0])

        v1.reset()
        start, ability, main = self.fx.ready_bench_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(ability, [0], 0), [1])
        self.assertEqual(self.invoke(main, [0], 0), [1])
        target_serial = start.current.players[1].active[0].serial
        final = self.ko_verification(main, target_serial)
        self.assertEqual(self.invoke(final, [0], 1), [0, 1])
        self.assert_complete([0, 1])

    def test_five_malformed_owned_envelopes_fault_without_v0(self):
        cases = []

        boss_start, boss_child, _ = self.fx.boss_ready_full_sequence()
        boss_child.select.remainDamageCounter = 1
        cases.append((boss_start, boss_child, [1], "V1_PREDICATE_SELECT_REMAIN_DAMAGE"))

        hammer_start, hammer_child, _ = self.hammer_chain()
        hammer_child.select.effect = None
        cases.append((hammer_start, hammer_child, [1], "V1_PREDICATE_SELECT_EFFECT"))

        lana_start, lana_child, _ = self.lana_chain()
        lana_child.select.remainEnergyCost = 1
        cases.append((lana_start, lana_child, [1], "V1_PREDICATE_SELECT_REMAIN_ENERGY"))

        xerosic_start, xerosic_verify = self.xerosic_chain()
        xerosic_verify.current.turnActionCount -= 1
        cases.append((xerosic_start, xerosic_verify, [2], "V1_PREDICATE_EXACT_PUBLIC_DELTA_OR_RULE_POSTCONDITION"))

        alakazam_start, alakazam_child, _ = self.fx.ready_bench_full_sequence()
        alakazam_child.select.context = SelectContext.MAIN
        cases.append((alakazam_start, alakazam_child, [1], "V1_PREDICATE_SELECT_CONTEXT"))

        for start, malformed, start_fallback, diagnostic in cases:
            with self.subTest(rule=start.select.option[0].type):
                v1.reset()
                self.assertEqual(self.invoke(start, start_fallback, 1), [0])
                action = self.invoke(malformed, [0], 0)
                self.assertTrue(action)
                self.assert_fault()
                self.assertIn(
                    diagnostic, v1.LAST_V1_PACKAGE_TRACE["reason_tags"]
                )

    def test_owned_child_supersedes_old_always_one_v0_assertion(self):
        start, child, _ = self.hammer_chain()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(v1.V1_TRANSACTION["stage"], "await_hammer_verify")

    def test_hammer_child_live_remaining_energy_one_is_accepted(self):
        start, child, _ = self.hammer_chain()
        self.assertEqual(child.select.remainEnergyCost, 1)
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(v1.V1_TRANSACTION["stage"], "await_hammer_verify")

    def test_hammer_child_remaining_energy_zero_is_rejected(self):
        start, child, _ = self.hammer_chain()
        child.select.remainEnergyCost = 0
        self.assertEqual(self.invoke(start, [1], 1), [0])
        action = self.invoke(child, [0], 0)
        parsed = self.policy.to_observation_class(self.fx.raw(child))
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assert_fault()
        self.assertIn(
            "V1_PREDICATE_SELECT_REMAIN_ENERGY",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_hammer_child_remaining_energy_two_is_rejected(self):
        start, child, _ = self.hammer_chain()
        child.select.remainEnergyCost = 2
        self.assertEqual(self.invoke(start, [1], 1), [0])
        action = self.invoke(child, [0], 0)
        parsed = self.policy.to_observation_class(self.fx.raw(child))
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assert_fault()
        self.assertIn(
            "V1_PREDICATE_SELECT_REMAIN_ENERGY",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_hammer_grow_grass_damaged_live_fingerprint_is_accepted(self):
        verify, transaction = self.grow_grass_hammer_verification(
            140, 170, 120, 150
        )
        self.assertTrue(v1._verify_hammer(self.policy, verify, transaction))

    def test_hammer_grow_grass_full_live_fingerprint_is_accepted(self):
        verify, transaction = self.grow_grass_hammer_verification(
            170, 170, 150, 150
        )
        self.assertTrue(v1._verify_hammer(self.policy, verify, transaction))

    def test_hammer_grow_grass_wrong_hp_deltas_are_rejected(self):
        mutations = {
            "wrong_current_hp": (119, 150),
            "wrong_max_hp": (120, 149),
            "minus_10": (130, 160),
            "minus_40": (100, 130),
        }
        for name, (post_hp, post_max_hp) in mutations.items():
            with self.subTest(mutation=name):
                verify, transaction = self.grow_grass_hammer_verification(
                    140, 170, post_hp, post_max_hp
                )
                self.assertFalse(
                    v1._verify_hammer(self.policy, verify, transaction)
                )

    def test_hammer_non_grow_energy_preserves_hp_exactly(self):
        energy = self.fx.card(11, 1, 9401)
        target = Pokemon(
            345,
            9450,
            140,
            170,
            False,
            [EnergyType.COLORLESS],
            [energy],
            [],
            [],
        )
        before = self.policy._bridge_pokemon_fingerprint(target)
        after = v1._fingerprint_without_energy(
            before, 0, (energy.id, energy.serial, energy.playerIndex)
        )
        self.assertEqual(after[2:4], (140, 170))
        self.assertEqual(after[6:8], ((), ()))

    def test_hammer_grow_grass_malformed_fingerprints_fail_closed(self):
        energy = self.fx.card(18, 1, 9401)
        target = Pokemon(
            345,
            9450,
            140,
            170,
            False,
            [EnergyType.GRASS],
            [energy],
            [],
            [],
        )
        fingerprint = self.policy._bridge_pokemon_fingerprint(target)
        row = (energy.id, energy.serial, energy.playerIndex)
        malformed_units = list(fingerprint)
        malformed_units[6] = list(malformed_units[6])
        misaligned_cards = list(fingerprint)
        misaligned_cards[7] = ()
        too_low = list(fingerprint)
        too_low[2] = 20
        cases = (
            (list(fingerprint), 0, row),
            (fingerprint[:-1], 0, row),
            (tuple(malformed_units), 0, row),
            (tuple(misaligned_cards), 0, row),
            (fingerprint, True, row),
            (fingerprint, 0, (18, energy.serial + 1, 1)),
            (tuple(too_low), 0, row),
        )
        for candidate, energy_index, selected_row in cases:
            with self.subTest(
                fingerprint_type=type(candidate).__name__,
                energy_index=energy_index,
                selected_row=selected_row,
            ):
                self.assertIsNone(
                    v1._fingerprint_without_energy(
                        candidate, energy_index, selected_row
                    )
                )

    def test_hammer_grow_grass_multiple_energy_binds_index_and_serial(self):
        basic = self.fx.card(1, 1, 9400)
        grow = self.fx.card(18, 1, 9401)
        target = Pokemon(
            345,
            9450,
            140,
            170,
            False,
            [EnergyType.GRASS, EnergyType.GRASS],
            [basic, grow],
            [],
            [],
        )
        fingerprint = self.policy._bridge_pokemon_fingerprint(target)
        grow_row = (grow.id, grow.serial, grow.playerIndex)
        after = v1._fingerprint_without_energy(fingerprint, 1, grow_row)
        self.assertEqual(after[2:4], (120, 150))
        self.assertEqual(after[6], (int(EnergyType.GRASS),))
        self.assertEqual(
            after[7], ((basic.id, basic.serial, basic.playerIndex),)
        )
        self.assertIsNone(
            v1._fingerprint_without_energy(fingerprint, 0, grow_row)
        )
        self.assertIsNone(
            v1._fingerprint_without_energy(
                fingerprint, 1, (grow.id, grow.serial + 1, grow.playerIndex)
            )
        )

    def test_hammer_grow_grass_bench_target_is_accepted(self):
        verify, transaction = self.grow_grass_hammer_verification(
            170, 170, 150, 150, area=AreaType.BENCH
        )
        self.assertTrue(v1._verify_hammer(self.policy, verify, transaction))
    def test_removed_rule_audit_is_known_for_empty_and_blocked_hits(self):
        ordinary, _ = self.fx.main_obs(
            hand_ids=[1152, 1152, 1152, 1152], options_card_ids=[]
        )
        self.invoke(ordinary, [0], 1)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE["removed_rule_hits"], [])

        removed, _ = self.fx.main_obs(
            hand_ids=[142, 1152, 1152, 1152], options_card_ids=[142]
        )
        self.invoke(removed, [0], 1)
        hits = v1.LAST_V1_PACKAGE_TRACE["removed_rule_hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["card_id"], 142)
        self.assertEqual(hits[0]["owner"], 0)
        self.assertTrue(hits[0]["blocked_route"])

    def test_preirreversible_malformed_rejects_to_v0_once(self):
        start, _, _ = self.fx.boss_ready_full_sequence()
        raw = self.fx.raw(start)
        calls = []
        original = runtime_model.raw_parsed_agree
        runtime_model.raw_parsed_agree = lambda raw_value, parsed: False
        try:
            action = v1.agent(
                self.policy,
                lambda value: calls.append(value) or [1],
                raw,
            )
        finally:
            runtime_model.raw_parsed_agree = original
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 1)
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertIn("RAW_PARSED_MISMATCH", v1.LAST_V1_PACKAGE_TRACE["reason_tags"])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE["removed_rule_hit_status"], "KNOWN")

    def test_active_v1_precedes_stale_integrated_duplicate(self):
        start, child, _ = self.fx.boss_ready_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        snap = runtime_model.public_snapshot(self.policy, child)
        self.assertIsNotNone(snap)
        core.INTEGRATED_DUPLICATE_CACHE[snap.sha256] = (
            runtime_model.stable_option_key(self.policy, child, child.select.option[0]),
        )
        core._DUPLICATE_ORDER.append(snap.sha256)
        self.assertEqual(self.invoke(child, [99], 0), [0])
        self.assertEqual(v1.V1_TRANSACTION["stage"], "await_boss_attack")
        self.assertNotIn("INHERITED_DUPLICATE_OWNER", v1.LAST_V1_PACKAGE_TRACE["reason_tags"])

    def test_delegate_probe_side_effects_rollback_before_candidate(self):
        start, _, _ = self.fx.boss_ready_full_sequence()
        sentinel_latest = {"classification": "PRE_V0_SENTINEL"}
        core.INTEGRATED_DUPLICATE_CACHE["PRE"] = (("PRE",),)
        core._DUPLICATE_ORDER[:] = ["PRE"]
        core.INTEGRATED_TRACE_LOG[:] = [{"classification": "PRE"}]
        core.INTEGRATED_LATEST_TRACE = sentinel_latest
        parent_before = core.parent_state_snapshot(self.policy)
        cache_before = copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        order_before = list(core._DUPLICATE_ORDER)
        log_before = copy.deepcopy(core.INTEGRATED_TRACE_LOG)
        calls = []

        def delegate(raw):
            calls.append(raw)
            self.policy.pre_turn = {"mutated": True}
            core.INTEGRATED_DUPLICATE_CACHE["MUTATED"] = (("MUTATED",),)
            core._DUPLICATE_ORDER.append("MUTATED")
            core.INTEGRATED_TRACE_LOG.append({"classification": "MUTATED"})
            core.INTEGRATED_LATEST_TRACE = {"classification": "MUTATED"}
            return [1]

        action = v1.agent(self.policy, delegate, self.fx.raw(start))
        self.assertEqual(action, [0])
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(v1.V1_TRANSACTION)
        self.assertEqual(core.parent_state_snapshot(self.policy), parent_before)
        self.assertEqual(core.INTEGRATED_DUPLICATE_CACHE, cache_before)
        self.assertEqual(core._DUPLICATE_ORDER, order_before)
        self.assertEqual(core.INTEGRATED_TRACE_LOG, log_before)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, sentinel_latest)

    def test_removed_substitution_rolls_back_delegate_side_effects(self):
        obs, _ = self.fx.main_obs(
            hand_ids=[142, 1152, 1152, 1152], options_card_ids=[142]
        )
        sentinel_latest = {"classification": "REMOVED_PRE"}
        core.INTEGRATED_DUPLICATE_CACHE["PRE"] = (("PRE",),)
        core._DUPLICATE_ORDER[:] = ["PRE"]
        core.INTEGRATED_TRACE_LOG[:] = [{"classification": "PRE"}]
        core.INTEGRATED_LATEST_TRACE = sentinel_latest
        parent_before = core.parent_state_snapshot(self.policy)
        cache_before = copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        order_before = list(core._DUPLICATE_ORDER)
        log_before = copy.deepcopy(core.INTEGRATED_TRACE_LOG)

        def delegate(raw):
            self.policy.pre_turn = {"mutated": True}
            core.INTEGRATED_DUPLICATE_CACHE["MUTATED"] = (("MUTATED",),)
            core._DUPLICATE_ORDER.append("MUTATED")
            core.INTEGRATED_TRACE_LOG.append({"classification": "MUTATED"})
            core.INTEGRATED_LATEST_TRACE = {"classification": "MUTATED"}
            return [0]

        action = v1.agent(self.policy, delegate, self.fx.raw(obs))
        parsed = self.policy.to_observation_class(self.fx.raw(obs))
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assertNotEqual(action, [0])
        self.assertEqual(core.parent_state_snapshot(self.policy), parent_before)
        self.assertEqual(core.INTEGRATED_DUPLICATE_CACHE, cache_before)
        self.assertEqual(core._DUPLICATE_ORDER, order_before)
        self.assertEqual(core.INTEGRATED_TRACE_LOG, log_before)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, sentinel_latest)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE["removed_rule_hit_status"], "KNOWN")

    def test_completion_removed_only_restores_all_delegate_side_effects(self):
        start, verify = self.xerosic_chain()
        removed = self.fx.card(142, 0, 9701)
        start.current.players[0].hand[1] = copy.deepcopy(removed)
        verify.current.players[0].hand[0] = copy.deepcopy(removed)
        verify.select.option = [
            Option(OptionType.PLAY, area=AreaType.HAND, index=0),
            Option(OptionType.ATTACK, attackId=1072),
            Option(OptionType.END),
        ]
        self.assertEqual(self.invoke(start, [2], 1), [0])

        sentinel_latest = {"classification": "COMPLETE_REMOVED_PRE"}
        core.INTEGRATED_TRANSACTION = {"kind": "PRE_EXISTING_OTHER"}
        core.INTEGRATED_DUPLICATE_CACHE["PRE"] = (("PRE",),)
        core._DUPLICATE_ORDER[:] = ["PRE"]
        core.INTEGRATED_TRACE_LOG[:] = [{"classification": "PRE"}]
        core.INTEGRATED_LATEST_TRACE = sentinel_latest
        parent_before = core.parent_state_snapshot(self.policy)
        transaction_before = copy.deepcopy(core.INTEGRATED_TRANSACTION)
        cache_before = copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        order_before = list(core._DUPLICATE_ORDER)
        log_before = copy.deepcopy(core.INTEGRATED_TRACE_LOG)

        def delegate(raw):
            self.policy.pre_turn = {"mutated": True}
            core.INTEGRATED_TRANSACTION = {"kind": "MUTATED_OTHER"}
            core.INTEGRATED_DUPLICATE_CACHE["MUTATED"] = (("MUTATED",),)
            core._DUPLICATE_ORDER.append("MUTATED")
            core.INTEGRATED_TRACE_LOG.append({"classification": "MUTATED"})
            core.INTEGRATED_LATEST_TRACE = {"classification": "MUTATED"}
            return [0]

        action = v1.agent(self.policy, delegate, self.fx.raw(verify))
        parsed = self.policy.to_observation_class(self.fx.raw(verify))
        self.assertEqual(action, [1])
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assertEqual(core.parent_state_snapshot(self.policy), parent_before)
        self.assertEqual(core.INTEGRATED_TRANSACTION, transaction_before)
        self.assertEqual(core.INTEGRATED_DUPLICATE_CACHE, cache_before)
        self.assertEqual(core._DUPLICATE_ORDER, order_before)
        self.assertEqual(core.INTEGRATED_TRACE_LOG, log_before)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, sentinel_latest)
        self.assert_complete([1])
    def test_mismatch_unrecoverable_invalid_v0_and_double_exception(self):
        start, child, _ = self.fx.boss_ready_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        raw = self.fx.raw(child)
        calls = []
        original_agreement = runtime_model.raw_parsed_agree
        runtime_model.raw_parsed_agree = lambda raw_value, parsed: False
        try:
            action = v1.agent(
                self.policy, lambda value: calls.append(value) or [99], raw
            )
        finally:
            runtime_model.raw_parsed_agree = original_agreement
        parsed = self.policy.to_observation_class(raw)
        self.assertEqual(action, [0])
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assertEqual(calls, [])
        self.assert_fault()
        self.assertIn("RAW_PARSED_MISMATCH", v1.LAST_V1_PACKAGE_TRACE["reason_tags"])

        v1.reset()
        start, child, _ = self.fx.boss_ready_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        raw_missing = self.fx.raw(child)
        raw_missing["select"] = None
        calls = []
        with self.assertRaises(v1.UnrecoverableObservationFault):
            v1.agent(
                self.policy, lambda value: calls.append(value) or [0], raw_missing
            )
        self.assertEqual(calls, [])
        self.assert_fault()
        self.assertIn(
            "V1_UNRECOVERABLE_OBSERVATION_FAULT",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

        v1.reset()
        start, child, _ = self.fx.boss_ready_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        raw = self.fx.raw(child)
        calls = []
        original_parser = self.policy.to_observation_class
        self.policy.to_observation_class = lambda value: (_ for _ in ()).throw(
            RuntimeError("parse failure")
        )
        try:
            action = v1.agent(
                self.policy, lambda value: calls.append(value) or [0], raw
            )
        finally:
            self.policy.to_observation_class = original_parser
        parsed = self.policy.to_observation_class(raw)
        self.assertEqual(action, [0])
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assertEqual(calls, [])
        self.assert_fault()
        self.assertIn(
            "V1_RAW_SELECT_STRUCTURAL_CERTIFICATE",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

        v1.reset()
        ordinary, _ = self.fx.main_obs(
            hand_ids=[1152, 1152, 1152, 1152], options_card_ids=[]
        )
        raw = self.fx.raw(ordinary)
        calls = []
        action = v1.agent(self.policy, lambda value: calls.append(value) or [99], raw)
        parsed = self.policy.to_observation_class(raw)
        self.assertEqual(len(calls), 1)
        self.assertTrue(action)
        self.assertTrue(v1.model.action_is_valid(parsed, action))

        v1.reset()
        start, child, _ = self.fx.boss_ready_full_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        original_advance = v1._advance_boss
        original_fault = v1._irreversible_fault_action
        v1._advance_boss = lambda *args: (_ for _ in ()).throw(RuntimeError())
        v1._irreversible_fault_action = lambda *args: (_ for _ in ()).throw(RuntimeError())
        try:
            action = self.invoke(child, [99], 0)
        finally:
            v1._advance_boss = original_advance
            v1._irreversible_fault_action = original_fault
        parsed = self.policy.to_observation_class(self.fx.raw(child))
        self.assertTrue(action)
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assert_fault()
    def test_live_full_stack_ko_uses_reverse_pre_evolution_order(self):
        start, child, main = self.boss_live_alakazam_full_stack_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(self.invoke(main, [0], 0), [1])
        final = self.ko_verification(main, 72)
        expected_serials = (72, 69, 65, 119)
        self.assertEqual(
            tuple(card.serial for card in final.current.players[1].discard[-4:]),
            expected_serials,
        )
        self.assertEqual(
            tuple(log.serial for log in final.logs[2:]), expected_serials
        )
        self.assertEqual(self.invoke(final, [0], 1), [0])
        self.assert_complete([0])

        v1.reset()
        start, child, main = self.boss_live_alakazam_full_stack_sequence()
        self.assertEqual(self.invoke(start, [1], 1), [0])
        self.assertEqual(self.invoke(child, [0], 0), [0])
        self.assertEqual(self.invoke(main, [0], 0), [1])
        forward = self.ko_verification(
            main, 72, reverse_pre_evolution=False
        )
        self.assertEqual(
            tuple(card.serial for card in forward.current.players[1].discard[-4:]),
            (72, 65, 69, 119),
        )
        action = self.invoke(forward, [0], 0)
        parsed = self.policy.to_observation_class(self.fx.raw(forward))
        self.assertTrue(v1.model.action_is_valid(parsed, action))
        self.assert_fault()

    def test_real_attack_resolution_rejects_synthetic_and_log_mutations(self):
        for mutation in ("hp_zero_active", "move_log_order"):
            with self.subTest(mutation=mutation):
                v1.reset()
                start, child, main = self.boss_evolved_full_sequence()
                self.assertEqual(self.invoke(start, [1], 1), [0])
                self.assertEqual(self.invoke(child, [0], 0), [0])
                self.assertEqual(self.invoke(main, [0], 0), [1])
                target_serial = main.current.players[1].active[0].serial
                final = self.ko_verification(main, target_serial)
                if mutation == "hp_zero_active":
                    target = copy.deepcopy(main.current.players[1].active[0])
                    target.hp = 0
                    final.current.players[1].active = [target]
                else:
                    final.logs[2], final.logs[3] = final.logs[3], final.logs[2]
                action = self.invoke(final, [99], 0)
                parsed = self.policy.to_observation_class(self.fx.raw(final))
                self.assertTrue(action)
                self.assertTrue(v1.model.action_is_valid(parsed, action))
                self.assert_fault()

    def test_lana_hammer_xerosic_real_log_mutations_fault(self):
        cases = (
            (self.lana_chain, "lana"),
            (self.hammer_chain, "hammer"),
            (self.xerosic_chain, "xerosic"),
        )
        for builder, name in cases:
            with self.subTest(route=name):
                v1.reset()
                chain = builder()
                start = chain[0]
                self.assertEqual(
                    self.invoke(start, [2] if name == "xerosic" else [1], 1),
                    [0],
                )
                if name == "xerosic":
                    verify = chain[1]
                    verify.logs.pop(0)
                else:
                    self.invoke(chain[1], [0], 0)
                    verify = chain[2]
                    if name == "lana":
                        verify.logs[0], verify.logs[1] = verify.logs[1], verify.logs[0]
                    else:
                        verify.logs[0].serial += 1
                action = self.invoke(verify, [99], 0)
                parsed = self.policy.to_observation_class(self.fx.raw(verify))
                self.assertTrue(action)
                self.assertTrue(v1.model.action_is_valid(parsed, action))
                self.assert_fault()

if __name__ == "__main__":
    unittest.main()