from __future__ import annotations

from dataclasses import asdict, replace
import copy
import json
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
    PlayerState,
    Pokemon,
    SelectContext,
    SelectData,
    SelectType,
    State,
)

import _cumulative_parent as policy
import main as entrypoint
import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_v2_h1_unique_attach as v2


class V2H1UniqueAttachTests(unittest.TestCase):
    def setUp(self):
        self.parent_state = core.parent_state_snapshot(policy)
        self.core_transaction = copy.deepcopy(core.INTEGRATED_TRANSACTION)
        self.core_duplicates = copy.deepcopy(
            core.INTEGRATED_DUPLICATE_CACHE
        )
        self.core_order = list(core._DUPLICATE_ORDER)
        self.core_log = copy.deepcopy(core.INTEGRATED_TRACE_LOG)
        self.core_latest = core.INTEGRATED_LATEST_TRACE
        self.v1_transaction = copy.deepcopy(v1.V1_TRANSACTION)
        self.v1_duplicates = copy.deepcopy(v1.V1_DUPLICATES)
        self.v1_removed = copy.deepcopy(v1.REMOVED_RULE_HITS)
        self.v1_trace = v1.LAST_V1_PACKAGE_TRACE
        self.v1_compliance = v1.COMPLIANCE_BLOCK_TAG
        core.INTEGRATED_TRANSACTION = None
        core.INTEGRATED_DUPLICATE_CACHE.clear()
        core._DUPLICATE_ORDER.clear()
        core.INTEGRATED_TRACE_LOG.clear()
        core.INTEGRATED_LATEST_TRACE = None
        v1.reset()
        v2.reset()
        self.set_benign_v1_trace()
        self.serial = 1000
        self.calls = []
        self.next_action = None

    def tearDown(self):
        v2.reset()
        core.restore_parent_state(policy, self.parent_state)
        core.INTEGRATED_TRANSACTION = self.core_transaction
        core.INTEGRATED_DUPLICATE_CACHE.clear()
        core.INTEGRATED_DUPLICATE_CACHE.update(self.core_duplicates)
        core._DUPLICATE_ORDER[:] = self.core_order
        core.INTEGRATED_TRACE_LOG[:] = self.core_log
        core.INTEGRATED_LATEST_TRACE = self.core_latest
        v1.V1_TRANSACTION = self.v1_transaction
        v1.V1_DUPLICATES.clear()
        v1.V1_DUPLICATES.update(self.v1_duplicates)
        v1.REMOVED_RULE_HITS = self.v1_removed
        v1.LAST_V1_PACKAGE_TRACE = self.v1_trace
        v1.COMPLIANCE_BLOCK_TAG = self.v1_compliance

    def set_benign_v1_trace(self):
        v1.LAST_V1_PACKAGE_TRACE = {
            "public_snapshot_hash": None,
            "context": None,
            "selected_action": [],
            "selected_rule": None,
            "reason_tags": [],
            "added_rule_hits": [],
            "removed_rule_hit_status": "KNOWN",
            "removed_rule_hits": [],
        }

    def card(self, card_id, owner=0, serial=None):
        if serial is None:
            self.serial += 1
            serial = self.serial
        return Card(card_id, serial, owner)

    def active_alakazam(self):
        return Pokemon(
            743,
            10,
            140,
            140,
            False,
            [EnergyType.PSYCHIC],
            [self.card(5, 0, 11)],
            [],
            [self.card(741, 0, 12), self.card(742, 0, 13)],
        )

    def bench_alakazam(self, *, ready=False, serial=30):
        energies = [EnergyType.PSYCHIC] if ready else []
        cards = [self.card(5, 0, 33)] if ready else []
        return Pokemon(
            743,
            serial,
            140,
            140,
            False,
            energies,
            cards,
            [],
            [self.card(741, 0, 31), self.card(742, 0, 32)],
        )

    def basic_bench(self, serial=40, owner=0):
        return Pokemon(741, serial, 60, 60, False, [], [], [], [])

    def target(self, *, serial=20, hp=100):
        return Pokemon(140, serial, hp, 210, False, [], [], [], [])

    def player(
        self,
        *,
        active,
        bench=(),
        hand=None,
        discard=(),
        prize=(),
        hand_count=None,
        deck_count=30,
    ):
        if hand_count is None:
            hand_count = len(hand) if hand is not None else 5
        return PlayerState(
            list(active),
            list(bench),
            5,
            deck_count,
            list(discard),
            list(prize),
            hand_count,
            None if hand is None else list(hand),
            False,
            False,
            False,
            False,
            False,
        )

    def start(self, energy_id=5, *, hand_count=6, target_hp=100):
        hand = [self.card(energy_id, 0, 50)]
        hand.extend(
            self.card(1152, 0, 51 + index)
            for index in range(hand_count - 1)
        )
        mine = self.player(
            active=[self.active_alakazam()],
            bench=[self.bench_alakazam(), self.basic_bench()],
            hand=hand,
            prize=[None, None, None],
        )
        theirs = self.player(
            active=[self.target(hp=target_hp)],
            bench=[self.target(serial=21, hp=210)],
            hand=None,
            hand_count=5,
            prize=[None, None],
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
        options = [
            Option(
                OptionType.ATTACH,
                area=AreaType.HAND,
                index=0,
                inPlayArea=AreaType.BENCH,
                inPlayIndex=0,
            ),
            Option(OptionType.ATTACK, attackId=1072),
            Option(OptionType.END),
        ]
        select = SelectData(
            SelectType.MAIN,
            SelectContext.MAIN,
            1,
            1,
            0,
            0,
            options,
            None,
            None,
            None,
        )
        return Observation(select, [], state)

    def raw(self, obs):
        return json.loads(json.dumps(asdict(obs)))

    def delegate(self, raw):
        self.calls.append(raw)
        return self.next_action

    def invoke(self, obs):
        raw = self.raw(obs)
        self.assertTrue(
            runtime_model.raw_parsed_agree(
                raw, policy.to_observation_class(raw)
            )
        )
        return v2.agent(policy, self.delegate, raw)

    def attack_index(self, obs):
        return next(
            index
            for index, option in enumerate(obs.select.option)
            if option.type == OptionType.ATTACK
            and option.attackId == 1072
        )

    def begin(self, start):
        self.next_action = [self.attack_index(start)]
        expected_object = self.next_action
        action = self.invoke(start)
        self.assertEqual(
            action,
            [
                next(
                    index
                    for index, option in enumerate(start.select.option)
                    if option.type == OptionType.ATTACH
                )
            ],
        )
        self.assertIs(v2.V2_TRANSACTION["v1_attack_action_object"], expected_object)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["selected_rule"], v2.RULE
        )
        self.assertTrue(
            v2.LAST_V2_CONTINUITY_TRACE["transaction_started"]
        )
        return action

    def post_attach_main(self, start):
        post = copy.deepcopy(start)
        mine = post.current.players[0]
        energy = mine.hand.pop(0)
        mine.handCount -= 1
        mine.bench[0].energies.append(EnergyType.PSYCHIC)
        mine.bench[0].energyCards.append(energy)
        post.current.turnActionCount += 1
        post.current.energyAttached = True
        post.logs = [
            Log(
                LogType.ATTACH,
                playerIndex=0,
                cardId=energy.id,
                serial=energy.serial,
                cardIdTarget=743,
                serialTarget=mine.bench[0].serial,
            )
        ]
        post.select = SelectData(
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
        )
        return post

    def telepath_child(self, start):
        child = self.post_attach_main(start)
        deck = [self.card(741, 0, 8001), self.card(741, 0, 8002)]
        options = [
            Option(
                OptionType.CARD,
                area=AreaType.DECK,
                index=index,
                playerIndex=0,
            )
            for index in range(len(deck))
        ]
        child.select = SelectData(
            SelectType.CARD,
            SelectContext.TO_BENCH,
            0,
            2,
            0,
            0,
            options,
            deck,
            None,
            copy.deepcopy(child.current.players[0].bench[0].energyCards[-1]),
        )
        return child

    def after_telepath_child(self, child):
        main = copy.deepcopy(child)
        main.logs = []
        main.select = SelectData(
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
        )
        return main

    def ko_verify(self, attack_main):
        verify = copy.deepcopy(attack_main)
        mine = verify.current.players[0]
        theirs = verify.current.players[1]
        target = theirs.active.pop(0)
        target_moves = v1._attack_target_moves(policy, target, 1)
        target_prizes = policy.prize_count(target)
        self.assertIsNotNone(target_moves)
        theirs.discard.extend(
            Card(card_id, serial, 1)
            for card_id, serial, _ in target_moves
        )
        theirs.poisoned = False
        theirs.burned = False
        theirs.asleep = False
        theirs.paralyzed = False
        theirs.confused = False
        verify.current.turnActionCount += 1
        verify.select = SelectData(
            SelectType.CARD,
            SelectContext.TO_HAND,
            target_prizes,
            target_prizes,
            0,
            0,
            [
                Option(
                    OptionType.CARD,
                    area=AreaType.PRIZE,
                    index=index,
                    playerIndex=0,
                )
                for index in range(len(mine.prize))
            ],
            None,
            None,
            None,
        )
        verify.logs = [
            Log(
                LogType.ATTACK,
                playerIndex=0,
                cardId=743,
                serial=10,
                attackId=1072,
            ),
            Log(
                LogType.HP_CHANGE,
                playerIndex=1,
                cardId=target.id,
                serial=target.serial,
                value=-(20 * mine.handCount),
                putDamageCounter=True,
            ),
        ]
        verify.logs.extend(
            Log(
                LogType.MOVE_CARD,
                playerIndex=1,
                cardId=card_id,
                serial=serial,
                fromArea=AreaType(from_area),
                toArea=AreaType.DISCARD,
            )
            for card_id, serial, from_area in target_moves
        )
        return verify

    def dispatch_basic(self):
        start = self.start(5)
        self.begin(start)
        post = self.post_attach_main(start)
        self.next_action = [self.attack_index(post)]
        attack_object = self.next_action
        returned = self.invoke(post)
        self.assertIs(returned, attack_object)
        self.assertIn(
            v2.TAG_ATTACH_VERIFIED,
            v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
        )
        self.assertIn(
            v2.TAG_ATTACK_DISPATCHED,
            v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
        )
        return start, post

    def assert_fault(self):
        self.assertIsNone(v2.V2_TRANSACTION)
        trace = v2.LAST_V2_CONTINUITY_TRACE
        self.assertEqual(trace["transaction_outcome"], "FAULT_ABORT")
        self.assertTrue(trace["irreversible_abort_fault"])
        self.assertIn(v2.TAG_PUBLIC_ABORT, trace["reason_tags"])
        self.assertIn(v2.TAG_IRREVERSIBLE, trace["reason_tags"])

    def test_basic_full_chain_and_exact_h_floor_boundary(self):
        start, attack_main = self.dispatch_basic()
        self.assertEqual(len(start.current.players[0].hand), 6)
        self.assertEqual(v2.V2_TRANSACTION["hreq"], 5)
        verify = self.ko_verify(attack_main)
        self.next_action = [0]
        completion_object = self.next_action
        returned = self.invoke(verify)
        self.assertIs(returned, completion_object)
        self.assertIsNone(v2.V2_TRANSACTION)
        trace = v2.LAST_V2_CONTINUITY_TRACE
        self.assertEqual(trace["transaction_outcome"], "COMPLETE")
        self.assertTrue(trace["KO_resolved"])
        self.assertIn(v2.TAG_KO_RESOLVED, trace["reason_tags"])
        self.assertEqual(len(self.calls), 3)

    def test_telepath_empty_child_full_chain_without_deck_consumption(self):
        start = self.start(19)
        self.begin(start)
        child = self.telepath_child(start)
        calls_before = len(self.calls)
        returned = self.invoke(child)
        self.assertEqual(returned, [])
        self.assertEqual(len(self.calls), calls_before)
        self.assertEqual(
            child.current.players[0].deckCount,
            start.current.players[0].deckCount,
        )
        self.assertIn(
            v2.TAG_TELEPATH_EMPTY,
            v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
        )
        attack_main = self.after_telepath_child(child)
        self.next_action = [self.attack_index(attack_main)]
        attack_object = self.next_action
        self.assertIs(self.invoke(attack_main), attack_object)
        verify = self.ko_verify(attack_main)
        self.next_action = [0]
        complete_object = self.next_action
        self.assertIs(self.invoke(verify), complete_object)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["transaction_outcome"],
            "COMPLETE",
        )

    def test_h_floor_below_boundary_is_nonfire_and_preserves_identity(self):
        start = self.start(5, hand_count=5)
        self.next_action = [self.attack_index(start)]
        baseline_object = self.next_action
        returned = self.invoke(start)
        self.assertIs(returned, baseline_object)
        self.assertIsNone(v2.V2_TRANSACTION)
        self.assertIn(
            v2.TAG_H_FLOOR,
            v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
        )

    def test_terminal_ko_completely_defers(self):
        start = self.start(5)
        start.current.players[0].prize = [None]
        v1.LAST_V1_PACKAGE_TRACE = {
            **v1.LAST_V1_PACKAGE_TRACE,
            "reason_tags": ["CURRENT_EXACT_TERMINAL_KO_PRECEDENCE"],
        }
        self.next_action = [self.attack_index(start)]
        baseline_object = self.next_action
        self.assertIs(self.invoke(start), baseline_object)
        self.assertIsNone(v2.V2_TRANSACTION)
        self.assertEqual(len(self.calls), 1)
        self.assertIn(
            v2.TAG_DEFER,
            v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
        )

    def test_all_v1_rule_stages_completely_defer(self):
        rules = (
            v1.RULE_BOSS,
            v1.RULE_XEROSIC,
            v1.RULE_HAMMER,
            v1.RULE_LANA,
            v1.RULE_ALAKAZAM,
            v1.RULE_MINE,
        )
        for rule in rules:
            for stage in ("start", "child", "verify"):
                with self.subTest(rule=rule, stage=stage):
                    v2.reset()
                    self.calls.clear()
                    self.set_benign_v1_trace()
                    v1.V1_TRANSACTION = {
                        "rule": rule,
                        "stage": stage,
                    }
                    v1.LAST_V1_PACKAGE_TRACE["selected_rule"] = rule
                    start = self.start(5)
                    self.next_action = [self.attack_index(start)]
                    baseline_object = self.next_action
                    self.assertIs(self.invoke(start), baseline_object)
                    self.assertIsNotNone(v1.V1_TRANSACTION)
                    self.assertIsNone(v2.V2_TRANSACTION)
                    self.assertEqual(len(self.calls), 1)
                    self.assertIn(
                        v2.TAG_DEFER,
                        v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
                    )
                    v1.V1_TRANSACTION = None

    def test_active_v1_parent_and_duplicate_owners_completely_defer(self):
        modes = ("v1", "integrated", "parent", "v1_duplicate", "duplicate")
        for mode in modes:
            with self.subTest(mode=mode):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                start = self.start(5)
                parsed = policy.to_observation_class(self.raw(start))
                snap = runtime_model.public_snapshot(policy, parsed)
                if mode == "v1":
                    v1.V1_TRANSACTION = {"rule": "OWNER"}
                elif mode == "integrated":
                    core.INTEGRATED_TRANSACTION = {"kind": "OWNER"}
                elif mode == "parent":
                    policy._hilda_source_latch = {"owner": 0}
                elif mode == "v1_duplicate":
                    v1.V1_DUPLICATES[snap.sha256] = (("OWNER",),)
                else:
                    core.INTEGRATED_DUPLICATE_CACHE[snap.sha256] = (
                        ("OWNER",),
                    )
                self.next_action = [self.attack_index(start)]
                baseline_object = self.next_action
                self.assertIs(self.invoke(start), baseline_object)
                self.assertIsNone(v2.V2_TRANSACTION)
                self.assertEqual(len(self.calls), 1)
                self.assertIn(
                    v2.TAG_DEFER,
                    v2.LAST_V2_CONTINUITY_TRACE["reason_tags"],
                )
                v1.V1_TRANSACTION = None
                core.INTEGRATED_TRANSACTION = None
                policy._hilda_source_latch = None
                v1.V1_DUPLICATES.clear()
                core.INTEGRATED_DUPLICATE_CACHE.clear()

    def test_bench_count_ready_and_energy_count_negative_boundaries(self):
        cases = []
        zero = self.start(5)
        zero.current.players[0].bench = [
            zero.current.players[0].bench[1]
        ]
        zero.select.option[0].inPlayIndex = 0
        cases.append(("zero_alakazam", zero))
        two = self.start(5)
        two.current.players[0].bench.append(
            self.bench_alakazam(serial=35)
        )
        cases.append(("two_alakazam", two))
        ready = self.start(5)
        ready.current.players[0].bench[0] = self.bench_alakazam(ready=True)
        cases.append(("ready_alakazam", ready))
        no_energy = self.start(5)
        no_energy.current.players[0].hand.pop(0)
        no_energy.current.players[0].handCount -= 1
        no_energy.select.option = no_energy.select.option[1:]
        cases.append(("no_energy", no_energy))
        two_energy = self.start(5)
        two_energy.current.players[0].hand.insert(
            1, self.card(19, 0, 59)
        )
        two_energy.current.players[0].handCount += 1
        cases.append(("two_energy", two_energy))
        for name, obs in cases:
            with self.subTest(name=name):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                self.next_action = [self.attack_index(obs)]
                baseline_object = self.next_action
                self.assertIs(self.invoke(obs), baseline_object)
                self.assertIsNone(v2.V2_TRANSACTION)

    def test_missing_cost_zero_two_and_nonpsychic_are_negative(self):
        originals = (
            policy.attack_table[1072],
            policy.card_table[743],
        )
        zero = self.start(5)
        zero.current.players[0].bench[0] = self.bench_alakazam(ready=True)
        self.next_action = [self.attack_index(zero)]
        self.assertIs(self.invoke(zero), self.next_action)
        self.assertIsNone(v2.V2_TRANSACTION)
        try:
            for name, required, attached in (
                (
                    "two",
                    [EnergyType.PSYCHIC, EnergyType.PSYCHIC],
                    [EnergyType.PSYCHIC, EnergyType.PSYCHIC],
                ),
                (
                    "nonpsychic",
                    [EnergyType.FIGHTING],
                    [EnergyType.FIGHTING],
                ),
            ):
                with self.subTest(name=name):
                    v2.reset()
                    self.calls.clear()
                    self.set_benign_v1_trace()
                    policy.attack_table[1072] = replace(
                        originals[0], energies=required
                    )
                    obs = self.start(5)
                    active = obs.current.players[0].active[0]
                    active.energies = list(attached)
                    active.energyCards = [
                        self.card(6, 0, 901 + index)
                        for index in range(len(attached))
                    ]
                    self.next_action = [self.attack_index(obs)]
                    self.assertIs(self.invoke(obs), self.next_action)
                    self.assertIsNone(v2.V2_TRANSACTION)
        finally:
            policy.attack_table[1072] = originals[0]
            policy.card_table[743] = originals[1]

    def test_option_zero_two_and_duplicate_stable_key_are_nonfire(self):
        cases = []
        zero = self.start(5)
        zero.select.option = zero.select.option[1:]
        cases.append(("zero", zero))
        two = self.start(5)
        two.select.option.insert(1, copy.deepcopy(two.select.option[0]))
        cases.append(("two", two))
        duplicate = self.start(5)
        duplicate.select.option.append(copy.deepcopy(duplicate.select.option[2]))
        cases.append(("duplicate_stable_key", duplicate))
        for name, obs in cases:
            with self.subTest(name=name):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                self.next_action = [self.attack_index(obs)]
                baseline_object = self.next_action
                self.assertIs(self.invoke(obs), baseline_object)
                self.assertIsNone(v2.V2_TRANSACTION)

    def test_card_metadata_skill_owner_serial_and_route_indexes_fail_closed(self):
        original_basic = policy.card_table[5]
        original_telepath = policy.card_table[19]
        try:
            mutations = []
            bad_basic = self.start(5)
            policy.card_table[5] = replace(
                original_basic, name="Basic Psychic Energy"
            )
            mutations.append(("basic_metadata", bad_basic, "basic"))
            policy.card_table[5] = original_basic
            skill = replace(
                original_telepath.skills[0],
                text=original_telepath.skills[0].text + " changed",
            )
            bad_telepath = self.start(19)
            mutations.append(("telepath_skill", bad_telepath, "telepath"))
            owner = self.start(5)
            owner.current.players[0].hand[0].playerIndex = 1
            mutations.append(("owner", owner, None))
            serial = self.start(5)
            serial.current.players[0].hand[0].serial = 30
            mutations.append(("serial", serial, None))
            hand_index = self.start(5)
            hand_index.select.option[0].index = 1
            mutations.append(("hand_index", hand_index, None))
            bench_index = self.start(5)
            bench_index.select.option[0].inPlayIndex = 1
            mutations.append(("bench_index", bench_index, None))
            for name, obs, metadata_mode in mutations:
                with self.subTest(name=name):
                    v2.reset()
                    self.calls.clear()
                    self.set_benign_v1_trace()
                    if metadata_mode == "basic":
                        policy.card_table[5] = replace(
                            original_basic, name="Basic Psychic Energy"
                        )
                    elif metadata_mode == "telepath":
                        policy.card_table[19] = replace(
                            original_telepath, skills=[skill]
                        )
                    self.next_action = [self.attack_index(obs)]
                    raw = self.raw(obs)
                    parsed = policy.to_observation_class(raw)
                    returned = (
                        self.invoke(obs)
                        if runtime_model.raw_parsed_agree(raw, parsed)
                        else v2.agent(policy, self.delegate, raw)
                    )
                    self.assertIs(returned, self.next_action)
                    self.assertIsNone(v2.V2_TRANSACTION)
                    policy.card_table[5] = original_basic
                    policy.card_table[19] = original_telepath
        finally:
            policy.card_table[5] = original_basic
            policy.card_table[19] = original_telepath

    def test_attach_duplicate_callback_rebinds_reordered_options(self):
        start = self.start(5)
        first = self.begin(start)
        duplicate = copy.deepcopy(start)
        duplicate.select.option = list(reversed(duplicate.select.option))
        calls_before = len(self.calls)
        returned = self.invoke(duplicate)
        expected = next(
            index
            for index, option in enumerate(duplicate.select.option)
            if option.type == OptionType.ATTACH
        )
        self.assertEqual(returned, [expected])
        self.assertNotEqual(returned, first)
        self.assertEqual(len(self.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "ATTACH_DUPLICATE_REBOUND",
        )

    def test_attack_duplicate_callback_rebinds_reordered_options(self):
        _, attack_main = self.dispatch_basic()
        duplicate = copy.deepcopy(attack_main)
        duplicate.select.option = list(reversed(duplicate.select.option))
        calls_before = len(self.calls)
        returned = self.invoke(duplicate)
        expected = self.attack_index(duplicate)
        self.assertEqual(returned, [expected])
        self.assertEqual(len(self.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "ATTACK_DUPLICATE_REBOUND",
        )

    def test_every_post_attach_public_mutation_is_irreversible_fault(self):
        def mutate_hand(obs):
            obs.current.players[0].hand.append(self.card(1152, 0, 9100))
            obs.current.players[0].handCount += 1

        def mutate_deck(obs):
            obs.current.players[0].deckCount -= 1

        def mutate_discard(obs):
            obs.current.players[0].discard.append(self.card(1152, 0, 9101))

        def mutate_prize(obs):
            obs.current.players[0].prize.append(None)

        def mutate_active(obs):
            obs.current.players[0].active[0].hp -= 10

        def mutate_target(obs):
            obs.current.players[1].active[0].hp -= 10

        def mutate_other_bench(obs):
            obs.current.players[0].bench[1].hp -= 10

        for name, mutator in (
            ("hand", mutate_hand),
            ("deck", mutate_deck),
            ("discard", mutate_discard),
            ("prize", mutate_prize),
            ("active", mutate_active),
            ("target", mutate_target),
            ("other_bench", mutate_other_bench),
        ):
            with self.subTest(name=name):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                start = self.start(5)
                self.begin(start)
                post = self.post_attach_main(start)
                mutator(post)
                self.next_action = [self.attack_index(post)]
                returned = self.invoke(post)
                parsed = policy.to_observation_class(self.raw(post))
                self.assertTrue(model_action_valid(parsed, returned))
                self.assert_fault()

    def test_telepath_child_mutations_are_irreversible_faults(self):
        def min_count(obs):
            obs.select.minCount = 1

        def effect(obs):
            obs.select.effect = self.card(5, 0, 50)

        def context_card(obs):
            obs.select.contextCard = self.card(5, 0, 50)

        def deck(obs):
            obs.current.players[0].deckCount -= 1

        def duplicate_serial(obs):
            obs.select.deck[1].serial = obs.select.deck[0].serial

        for name, mutator in (
            ("min_count", min_count),
            ("effect", effect),
            ("context_card", context_card),
            ("deck", deck),
            ("duplicate_serial", duplicate_serial),
        ):
            with self.subTest(name=name):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                start = self.start(19)
                self.begin(start)
                child = self.telepath_child(start)
                mutator(child)
                self.next_action = [0]
                returned = self.invoke(child)
                parsed = policy.to_observation_class(self.raw(child))
                self.assertTrue(model_action_valid(parsed, returned))
                self.assert_fault()

    def test_attack_resolution_mutations_are_irreversible_faults(self):
        def attack_log(obs):
            obs.logs[0].attackId = 999

        def damage(obs):
            obs.logs[1].value += 20

        def target_movement(obs):
            obs.current.players[1].discard.pop()

        def prize_prompt(obs):
            obs.select.minCount = 0

        for name, mutator in (
            ("attack_log", attack_log),
            ("damage", damage),
            ("target_movement", target_movement),
            ("prize_prompt", prize_prompt),
        ):
            with self.subTest(name=name):
                v2.reset()
                self.calls.clear()
                self.set_benign_v1_trace()
                _, attack_main = self.dispatch_basic()
                verify = self.ko_verify(attack_main)
                mutator(verify)
                self.next_action = [0]
                returned = self.invoke(verify)
                parsed = policy.to_observation_class(self.raw(verify))
                self.assertTrue(model_action_valid(parsed, returned))
                self.assert_fault()

    def test_new_v1_owner_after_irreversible_attach_is_fault(self):
        start = self.start(5)
        self.begin(start)
        post = self.post_attach_main(start)
        v1.V1_TRANSACTION = {"rule": v1.RULE_BOSS, "stage": "child"}
        self.next_action = [self.attack_index(post)]
        self.invoke(post)
        self.assert_fault()

    def test_nonfire_preserves_action_and_all_v1_core_parent_mutable_state(self):
        obs = self.start(5, hand_count=5)
        baseline_object = [self.attack_index(obs)]
        sentinel_latest = {"classification": "SENTINEL"}
        expected = {}

        def mutating_delegate(raw):
            self.calls.append(raw)
            policy.ability_used_dudunsparce = True
            core.INTEGRATED_TRACE_LOG.append({"sentinel": 1})
            core.INTEGRATED_LATEST_TRACE = sentinel_latest
            v1.V1_DUPLICATES["UNRELATED"] = (("KEY",),)
            self.set_benign_v1_trace()
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"] = ["V0_FALLBACK"]
            expected["parent"] = core.parent_state_snapshot(policy)
            expected["transaction"] = copy.deepcopy(
                core.INTEGRATED_TRANSACTION
            )
            expected["duplicates"] = copy.deepcopy(
                core.INTEGRATED_DUPLICATE_CACHE
            )
            expected["order"] = list(core._DUPLICATE_ORDER)
            expected["log"] = copy.deepcopy(core.INTEGRATED_TRACE_LOG)
            expected["latest"] = core.INTEGRATED_LATEST_TRACE
            expected["v1_transaction"] = copy.deepcopy(v1.V1_TRANSACTION)
            expected["v1_duplicates"] = copy.deepcopy(v1.V1_DUPLICATES)
            expected["v1_removed"] = copy.deepcopy(v1.REMOVED_RULE_HITS)
            expected["v1_trace"] = copy.deepcopy(
                v1.LAST_V1_PACKAGE_TRACE
            )
            return baseline_object

        returned = v2.agent(policy, mutating_delegate, self.raw(obs))
        self.assertIs(returned, baseline_object)
        self.assertEqual(core.parent_state_snapshot(policy), expected["parent"])
        self.assertEqual(core.INTEGRATED_TRANSACTION, expected["transaction"])
        self.assertEqual(
            core.INTEGRATED_DUPLICATE_CACHE, expected["duplicates"]
        )
        self.assertEqual(core._DUPLICATE_ORDER, expected["order"])
        self.assertEqual(core.INTEGRATED_TRACE_LOG, expected["log"])
        self.assertIs(core.INTEGRATED_LATEST_TRACE, expected["latest"])
        self.assertEqual(v1.V1_TRANSACTION, expected["v1_transaction"])
        self.assertEqual(v1.V1_DUPLICATES, expected["v1_duplicates"])
        self.assertEqual(v1.REMOVED_RULE_HITS, expected["v1_removed"])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE, expected["v1_trace"])
        self.assertIsNone(v2.V2_TRANSACTION)

    def test_same_changed_fixture_is_deterministic_three_times(self):
        rows = []
        for _ in range(3):
            v2.reset()
            v1.reset()
            self.set_benign_v1_trace()
            core.INTEGRATED_TRANSACTION = None
            core.INTEGRATED_DUPLICATE_CACHE.clear()
            core._DUPLICATE_ORDER.clear()
            core.INTEGRATED_TRACE_LOG.clear()
            core.INTEGRATED_LATEST_TRACE = None
            obs = self.start(5, hand_count=5)
            self.next_action = [self.attack_index(obs)]
            action = self.invoke(obs)
            rows.append(
                (
                    list(action),
                    copy.deepcopy(v2.LAST_V2_CONTINUITY_TRACE),
                )
            )
        self.assertEqual(rows[0], rows[1])
        self.assertEqual(rows[1], rows[2])

    def test_entrypoint_exposes_v2_trace_and_preserves_v1_action_identity(self):
        original = entrypoint._deck_v1.agent
        baseline_object = [0]
        sentinel = {
            "public_snapshot_hash": None,
            "context": None,
            "selected_action": baseline_object,
            "selected_rule": None,
            "reason_tags": ["RAW_PARSED_MISMATCH", "V0_FALLBACK"],
            "added_rule_hits": [],
            "removed_rule_hit_status": "KNOWN",
            "removed_rule_hits": [],
        }

        def fake(parent, delegate, raw):
            entrypoint._deck_v1.LAST_V1_PACKAGE_TRACE = sentinel
            return baseline_object

        entrypoint._deck_v1.agent = fake
        try:
            returned = entrypoint.agent({"select": {}})
        finally:
            entrypoint._deck_v1.agent = original
        self.assertIs(returned, baseline_object)
        self.assertEqual(entrypoint.LAST_V1_PACKAGE_TRACE, sentinel)
        self.assertEqual(
            entrypoint.LAST_V2_CONTINUITY_TRACE["selected_action"],
            baseline_object,
        )


def model_action_valid(obs, action):
    return v1.model.action_is_valid(obs, action)


if __name__ == "__main__":
    unittest.main()
