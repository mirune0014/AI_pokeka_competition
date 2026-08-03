from __future__ import annotations

from dataclasses import asdict
import copy
import json
import unittest

from cg.api import (
    AreaType, Card, EnergyType, Observation, Option, OptionType, PlayerState,
    Pokemon, SelectContext, SelectData, SelectType, State,
)

import main as entrypoint
import _cumulative_parent as policy
import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model


class V1PackageTests(unittest.TestCase):
    def setUp(self):
        self.parent_state = core.parent_state_snapshot(policy)
        self.saved_transaction = core.INTEGRATED_TRANSACTION
        self.saved_duplicate = copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        self.saved_latest = core.INTEGRATED_LATEST_TRACE
        self.saved_duplicate_order = list(core._DUPLICATE_ORDER)
        self.saved_trace_log = copy.deepcopy(core.INTEGRATED_TRACE_LOG)
        core.INTEGRATED_TRANSACTION = None
        core.INTEGRATED_DUPLICATE_CACHE.clear()
        core._DUPLICATE_ORDER.clear()
        core.INTEGRATED_TRACE_LOG.clear()
        v1.reset()
        self.serial = 100

    def tearDown(self):
        core.restore_parent_state(policy, self.parent_state)
        core.INTEGRATED_TRANSACTION = self.saved_transaction
        core.INTEGRATED_DUPLICATE_CACHE.clear()
        core.INTEGRATED_DUPLICATE_CACHE.update(self.saved_duplicate)
        core._DUPLICATE_ORDER[:] = self.saved_duplicate_order
        core.INTEGRATED_TRACE_LOG[:] = self.saved_trace_log
        core.INTEGRATED_LATEST_TRACE = self.saved_latest
        v1.reset()

    def card(self, card_id, owner=0, serial=None):
        if serial is None:
            self.serial += 1
            serial = self.serial
        return Card(card_id, serial, owner)

    def alakazam(self):
        return Pokemon(
            743, 10, 140, 140, False, [EnergyType.PSYCHIC],
            [self.card(5, 0, 11)], [],
            [self.card(741, 0, 12), self.card(742, 0, 13)],
        )

    def target(self, hp=100, energies=(), energy_cards=()):
        return Pokemon(140, 20, hp, 210, False, list(energies), list(energy_cards), [], [])

    def player(self, *, active, bench=(), hand=None, discard=(), hand_count=None, supporter_status=False):
        if hand_count is None:
            hand_count = len(hand) if hand is not None else 5
        return PlayerState(
            list(active), list(bench), 5, 30, list(discard), [], hand_count,
            None if hand is None else list(hand), False, False, False, False, False,
        )

    def main_obs(self, *, hand_ids, target_hp=100, discard=(), opponent_bench=(), target_energy=None, options_card_ids=None):
        hand = [self.card(card_id) for card_id in hand_ids]
        target_energy = target_energy or ()
        energies = tuple(row[0] for row in target_energy)
        energy_cards = tuple(row[1] for row in target_energy)
        mine = self.player(active=[self.alakazam()], hand=hand, discard=discard)
        theirs = self.player(
            active=[self.target(target_hp, energies, energy_cards)],
            bench=opponent_bench, hand=None, hand_count=5,
        )
        state = State(4, 2, 0, 0, False, False, False, False, -1, [], None, [mine, theirs])
        options = []
        selected_ids = options_card_ids if options_card_ids is not None else hand_ids
        for wanted in selected_ids:
            index = next(index for index, card in enumerate(hand) if card.id == wanted)
            options.append(Option(OptionType.PLAY, index=index))
        options.append(Option(OptionType.ATTACK, attackId=1072))
        options.append(Option(OptionType.END))
        select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, options, None, None, None)
        return Observation(select, [], state), hand

    def raw(self, obs):
        return json.loads(json.dumps(asdict(obs)))

    def call(self, obs, fallback, expected_calls=None):
        raw = self.raw(obs)
        self.assertTrue(runtime_model.raw_parsed_agree(raw, policy.to_observation_class(raw)))
        owned_at_entry = v1.V1_TRANSACTION is not None
        calls = []
        action = v1.agent(policy, lambda value: calls.append(value) or fallback, raw)
        self.assertEqual(
            v1.LAST_V1_PACKAGE_TRACE["removed_rule_hit_status"], "KNOWN"
        )
        for hit in v1.LAST_V1_PACKAGE_TRACE["removed_rule_hits"]:
            self.assertIn(hit["owner"], (0, 1))
            self.assertTrue(hit["blocked_route"])
        completed = "V1_TRANSACTION_COMPLETE" in v1.LAST_V1_PACKAGE_TRACE["reason_tags"]
        if expected_calls is None:
            expected_calls = 1 if not owned_at_entry or completed else 0
        self.assertEqual(len(calls), expected_calls)
        faulted = (
            "V1_IRREVERSIBLE_ABORT_FAULT"
            in v1.LAST_V1_PACKAGE_TRACE["reason_tags"]
        )
        if faulted:
            parsed = policy.to_observation_class(raw)
            self.assertTrue(v1.model.action_is_valid(parsed, action))
            self.assertEqual(calls, [])
        return action

    def test_xerosic_positive_h_minus_1(self):
        obs, _ = self.main_obs(hand_ids=[1197, 1152, 1152, 1152, 1152, 1152], options_card_ids=[1197])
        self.assertEqual(self.call(obs, [2]), [0])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_XEROSIC)
        self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_xerosic_verify')

    def test_xerosic_negative_h_floor(self):
        obs, _ = self.main_obs(hand_ids=[1197, 1152, 1152, 1152, 1152], target_hp=100, options_card_ids=[1197])
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_current_exact_ko_attack_precedes_xerosic(self):
        obs, _ = self.main_obs(hand_ids=[1197, 1152, 1152, 1152, 1152, 1152], options_card_ids=[1197])
        fallback = [1]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIn('CURRENT_EXACT_KO_PRECEDENCE', v1.LAST_V1_PACKAGE_TRACE['reason_tags'])

    def test_lana_positive_first_enables_ko(self):
        recovered = [self.card(743), self.card(741), self.card(5)]
        obs, _ = self.main_obs(
            hand_ids=[1184, 1152, 1152, 1152], target_hp=120,
            discard=recovered, options_card_ids=[1184],
        )
        self.assertEqual(self.call(obs, [2]), [0])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_LANA)
        self.assertEqual(v1.V1_TRANSACTION['recovery_count'], 3)
        self.assertEqual({row[0] for row in v1.V1_TRANSACTION['selected_rows']}, {743, 741, 5})

    def test_lana_negative_excluded_cards(self):
        excluded = [self.card(140), self.card(13), self.card(19)]
        obs, _ = self.main_obs(
            hand_ids=[1184, 1152, 1152, 1152], target_hp=120,
            discard=excluded, options_card_ids=[1184],
        )
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_lana_child_reorders_and_uses_only_allowlist(self):
        recovered = [self.card(743), self.card(741), self.card(5)]
        obs, hand = self.main_obs(
            hand_ids=[1184, 1152, 1152, 1152], target_hp=120,
            discard=recovered, options_card_ids=[1184],
        )
        self.assertEqual(self.call(obs, [2]), [0])
        lana = hand[0]
        mine = self.player(
            active=[obs.current.players[0].active[0]], hand=hand[1:],
            discard=recovered, hand_count=3,
        )
        theirs = obs.current.players[1]
        state = State(4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, theirs])
        # Option order is deliberately 5, 743, 741 rather than discard order.
        order = [2, 0, 1]
        options = [Option(OptionType.CARD, area=AreaType.DISCARD, index=index, playerIndex=0) for index in order]
        select = SelectData(SelectType.CARD, SelectContext.TO_HAND, 1, 3, 0, 0, options, None, None, lana)
        child = Observation(select, [], state)
        self.assertEqual(self.call(child, [0]), [1, 0, 2])
        self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_lana_verify')

    def test_hammer_positive_unique_special_energy(self):
        special = self.card(11, 1, 30)
        obs, _ = self.main_obs(
            hand_ids=[1081, 1152, 1152, 1152, 1152, 1152],
            target_energy=[(EnergyType.COLORLESS, special)], options_card_ids=[1081],
        )
        self.assertEqual(self.call(obs, [2]), [0])
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_HAMMER)
        self.assertEqual(v1.V1_TRANSACTION['hammer_mode'], 'ENABLE_COUNTER_KO')
        self.assertEqual(v1.V1_TRANSACTION['energy_row'], (11, 30, 1))

    def test_hammer_negative_unique_nondefensive_energy(self):
        special = self.card(19, 1, 30)
        obs, _ = self.main_obs(
            hand_ids=[1081, 1152, 1152, 1152, 1152, 1152],
            target_energy=[(EnergyType.PSYCHIC, special)],
            options_card_ids=[1081],
        )
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_hammer_negative_two_special_targets(self):
        special1 = self.card(19, 1, 30)
        special2 = self.card(13, 1, 31)
        obs, _ = self.main_obs(
            hand_ids=[1081, 1152, 1152, 1152, 1152, 1152],
            target_energy=[(EnergyType.PSYCHIC, special1), (EnergyType.COLORLESS, special2)],
            options_card_ids=[1081],
        )
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_hammer_child_binds_area_owner_index_energy_index_and_serial(self):
        special = self.card(11, 1, 30)
        obs, hand = self.main_obs(
            hand_ids=[1081, 1152, 1152, 1152, 1152, 1152],
            target_energy=[(EnergyType.COLORLESS, special)], options_card_ids=[1081],
        )
        self.assertEqual(self.call(obs, [2]), [0])
        hammer = hand[0]
        mine = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=[], hand_count=5)
        state = State(4, 3, 0, 0, False, False, False, False, -1, [], None, [mine, obs.current.players[1]])
        option = Option(OptionType.ENERGY, area=AreaType.ACTIVE, index=0, playerIndex=1, energyIndex=0, count=1)
        select = SelectData(SelectType.ENERGY, SelectContext.DISCARD_ENERGY, 1, 1, 0, 0, [option], None, None, hammer)
        child = Observation(select, [], state)
        self.assertEqual(self.call(child, [0]), [0])
        self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_hammer_verify')

    def test_child_serial_ambiguity_fails_closed(self):
        recovered = [self.card(743), self.card(741), self.card(5)]
        obs, hand = self.main_obs(hand_ids=[1184, 1152, 1152, 1152], target_hp=120, discard=recovered, options_card_ids=[1184])
        self.assertEqual(self.call(obs, [2]), [0])
        lana = hand[0]
        mine = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=recovered, hand_count=3)
        state = State(4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, obs.current.players[1]])
        duplicate = Option(OptionType.CARD, area=AreaType.DISCARD, index=0, playerIndex=0)
        select = SelectData(SelectType.CARD, SelectContext.TO_HAND, 1, 2, 0, 0, [duplicate, duplicate], None, None, lana)
        child = Observation(select, [], state)
        fallback = [0]
        self.assertEqual(self.call(child, fallback), [0])
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_snapshot_mutation_aborts_child(self):
        special = self.card(11, 1, 30)
        obs, hand = self.main_obs(hand_ids=[1081, 1152, 1152, 1152, 1152, 1152], target_energy=[(EnergyType.COLORLESS, special)], options_card_ids=[1081])
        self.assertEqual(self.call(obs, [2]), [0])
        hammer = hand[0]
        mutated_target = copy.deepcopy(obs.current.players[1].active[0])
        mutated_target.hp -= 10
        mine = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=[], hand_count=5)
        theirs = self.player(active=[mutated_target], hand=None, hand_count=5)
        state = State(4, 3, 0, 0, False, False, False, False, -1, [], None, [mine, theirs])
        option = Option(OptionType.ENERGY, area=AreaType.ACTIVE, index=0, playerIndex=1, energyIndex=0, count=1)
        select = SelectData(SelectType.ENERGY, SelectContext.DISCARD_ENERGY, 1, 1, 0, 0, [option], None, None, hammer)
        fallback = [0]
        self.assertEqual(self.call(Observation(select, [], state), fallback), [0])
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_boss_mine_alakazam_ambiguous_states_fail_closed(self):
        for card_id, option_type in ((1182, OptionType.PLAY), (1266, OptionType.PLAY), (743, OptionType.EVOLVE)):
            v1.reset()
            obs, _ = self.main_obs(hand_ids=[card_id, 1152, 1152, 1152], options_card_ids=[])
            obs.select.option.insert(0, Option(option_type, area=AreaType.HAND if option_type == OptionType.EVOLVE else None, index=0, inPlayArea=AreaType.ACTIVE if option_type == OptionType.EVOLVE else None, inPlayIndex=0 if option_type == OptionType.EVOLVE else None))
            fallback = [len(obs.select.option) - 1]
            self.assertIs(self.call(obs, fallback), fallback)
            self.assertIn('UNKNOWN_NOT_IMPLEMENTED_FAIL_CLOSED', v1.LAST_V1_PACKAGE_TRACE['reason_tags'])

    def test_parent_transaction_and_raw_mismatch_precede_v1(self):
        obs, _ = self.main_obs(hand_ids=[1197, 1152, 1152, 1152, 1152, 1152], options_card_ids=[1197])
        core.INTEGRATED_TRANSACTION = {'kind': 'PARENT'}
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertIn('INHERITED_TRANSACTION_OWNER', v1.LAST_V1_PACKAGE_TRACE['reason_tags'])
        core.INTEGRATED_TRANSACTION = None
        original = runtime_model.raw_parsed_agree
        runtime_model.raw_parsed_agree = lambda raw, parsed: False
        try:
            raw = self.raw(obs)
            result = v1.agent(policy, lambda value: fallback, raw)
        finally:
            runtime_model.raw_parsed_agree = original
        self.assertIs(result, fallback)
        self.assertIn('RAW_PARSED_MISMATCH', v1.LAST_V1_PACKAGE_TRACE['reason_tags'])

    def test_nonfire_preserves_action_parent_state_reason_and_no_transaction(self):
        obs, _ = self.main_obs(hand_ids=[1152, 1152, 1152, 1152], options_card_ids=[])
        fallback = [1]
        parent_before = core.parent_state_snapshot(policy)
        reason = {'classification': 'SENTINEL', 'reason': 'v0'}
        core.INTEGRATED_LATEST_TRACE = reason
        returned = self.call(obs, fallback)
        self.assertIs(returned, fallback)
        self.assertEqual(core.parent_state_snapshot(policy), parent_before)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, reason)
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_action'], fallback)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['added_rule_hits'], [])

    def test_stale_duplicate_cache_cannot_cross_transaction_boundary(self):
        obs, _ = self.main_obs(
            hand_ids=[1152, 1152, 1152, 1152, 1152],
            options_card_ids=[1152],
        )
        snapshot = runtime_model.public_snapshot(policy, obs)
        self.assertIsNotNone(snapshot)
        v1.V1_DUPLICATES[snapshot.sha256] = (
            runtime_model.stable_option_key(policy, obs, obs.select.option[0]),
        )
        fallback = [2]
        self.assertIs(self.call(obs, fallback), fallback)
        self.assertEqual(v1.V1_DUPLICATES, {})
        self.assertIn("V0_FALLBACK", v1.LAST_V1_PACKAGE_TRACE["reason_tags"])
    def test_main_exposes_required_trace(self):
        sentinel = {
            'public_snapshot_hash': 'A', 'context': 0, 'selected_action': [1],
            'selected_rule': None, 'reason_tags': ['V0_FALLBACK'], 'added_rule_hits': [],
        }
        original = entrypoint._deck_v1.agent
        entrypoint._deck_v1.agent = lambda parent, delegate, raw: (setattr(entrypoint._deck_v1, 'LAST_V1_PACKAGE_TRACE', sentinel) or [1])
        try:
            self.assertEqual(entrypoint.agent({'select': {}}), [1])
        finally:
            entrypoint._deck_v1.agent = original
        self.assertEqual(entrypoint.LAST_V1_PACKAGE_TRACE, sentinel)


if __name__ == '__main__':
    unittest.main()


# Additional strict-corridor tests are defined after the script guard; unittest
# discovery imports the module and sees them normally.
def _v1_boss_target(self, serial, hp):
    return Pokemon(140, serial, hp, 210, False, [], [], [], [])
V1PackageTests.boss_target = _v1_boss_target


def _test_boss_terminal_positive_child_reorder_and_verified_attack(self):
    terminal, distractor = self.boss_target(21, 100), self.boss_target(22, 200)
    obs, hand = self.main_obs(hand_ids=[1182, 1152, 1152, 1152, 1152, 1152], target_hp=200, opponent_bench=[terminal, distractor], options_card_ids=[1182])
    obs.current.players[0].prize = [None]
    self.assertEqual(self.call(obs, [2]), [0])
    self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_BOSS)
    boss = hand[0]
    mine = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=[], hand_count=5); mine.prize = [None]
    theirs = self.player(active=obs.current.players[1].active, bench=[terminal, distractor], hand=None, hand_count=5)
    state = State(4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, theirs])
    options = [Option(OptionType.CARD, area=AreaType.BENCH, index=1, playerIndex=1), Option(OptionType.CARD, area=AreaType.BENCH, index=0, playerIndex=1)]
    select = SelectData(SelectType.CARD, SelectContext.SWITCH, 1, 1, 0, 0, options, None, None, boss)
    self.assertEqual(self.call(Observation(select, [], state), [0]), [1])
    switched = self.player(active=[terminal], bench=[obs.current.players[1].active[0], distractor], hand=None, hand_count=5)
    resolved_mine = copy.deepcopy(mine); resolved_mine.discard = [boss]
    main_state = State(4, 4, 0, 0, True, False, False, False, -1, [], None, [resolved_mine, switched])
    main_select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    self.assertEqual(self.call(Observation(main_select, [], main_state), [1]), [0])
    self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_added_attack_verify')
V1PackageTests.test_boss_terminal_positive_child_reorder_and_verified_attack = _test_boss_terminal_positive_child_reorder_and_verified_attack


def _test_boss_terminal_negative_multiple_targets(self):
    obs, _ = self.main_obs(hand_ids=[1182, 1152, 1152, 1152, 1152, 1152], target_hp=200, opponent_bench=[self.boss_target(21, 100), self.boss_target(22, 100)], options_card_ids=[1182])
    obs.current.players[0].prize = [None]
    fallback = [2]
    self.assertIs(self.call(obs, fallback), fallback); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_boss_terminal_negative_multiple_targets = _test_boss_terminal_negative_multiple_targets


def _test_boss_switch_mutation_aborts_before_attack(self):
    terminal = self.boss_target(21, 100)
    obs, hand = self.main_obs(hand_ids=[1182, 1152, 1152, 1152, 1152, 1152], target_hp=200, opponent_bench=[terminal], options_card_ids=[1182])
    obs.current.players[0].prize = [None]; self.assertEqual(self.call(obs, [2]), [0])
    boss = hand[0]
    mine = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=[], hand_count=5); mine.prize = [None]
    state = State(4, 3, 0, 0, True, False, False, False, -1, [], None, [mine, obs.current.players[1]])
    child = SelectData(SelectType.CARD, SelectContext.SWITCH, 1, 1, 0, 0, [Option(OptionType.CARD, area=AreaType.BENCH, index=0, playerIndex=1)], None, None, boss)
    self.assertEqual(self.call(Observation(child, [], state), [0]), [0])
    main_select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    fallback = [1]
    self.assertEqual(self.call(Observation(main_select, [], state), fallback), [0]); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_boss_switch_mutation_aborts_before_attack = _test_boss_switch_mutation_aborts_before_attack


def _v1_tera_target(self, energy_count=3):
    cards = [self.card(1, 1, 31 + index) for index in range(energy_count)]
    return Pokemon(96, 20, 100, 210, False, [EnergyType.GRASS] * energy_count, cards, [], [])
V1PackageTests.tera_target = _v1_tera_target


def _test_mine_positive_reordered_main_and_verified_stadium_attack(self):
    obs, hand = self.main_obs(hand_ids=[1152, 1266, 1152, 1152, 1152, 1152], target_hp=100, options_card_ids=[1266])
    obs.current.players[1].active = [self.tera_target(3)]
    play = obs.select.option[0]; obs.select.option = [Option(OptionType.END), play, Option(OptionType.ATTACK, attackId=1072)]
    self.assertEqual(self.call(obs, [0]), [1]); self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_MINE)
    mine_card = hand[1]
    own = self.player(active=[obs.current.players[0].active[0]], hand=[hand[0]] + hand[2:], discard=[], hand_count=5)
    state = State(4, 3, 0, 0, False, True, False, False, -1, [mine_card], None, [own, obs.current.players[1]])
    select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    self.assertEqual(self.call(Observation(select, [], state), [1]), [0]); self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_added_attack_verify')
V1PackageTests.test_mine_positive_reordered_main_and_verified_stadium_attack = _test_mine_positive_reordered_main_and_verified_stadium_attack


def _test_mine_negative_nontera_or_extra_payable_energy(self):
    for target in (self.target(100), self.tera_target(4)):
        v1.reset(); obs, _ = self.main_obs(hand_ids=[1266, 1152, 1152, 1152, 1152, 1152], options_card_ids=[1266]); obs.current.players[1].active = [target]
        fallback = [2]; self.assertIs(self.call(obs, fallback), fallback); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_mine_negative_nontera_or_extra_payable_energy = _test_mine_negative_nontera_or_extra_payable_energy


def _test_mine_stadium_mutation_aborts(self):
    obs, hand = self.main_obs(hand_ids=[1266, 1152, 1152, 1152, 1152, 1152], options_card_ids=[1266]); obs.current.players[1].active = [self.tera_target(3)]
    self.assertEqual(self.call(obs, [2]), [0])
    own = self.player(active=[obs.current.players[0].active[0]], hand=hand[1:], discard=[hand[0]], hand_count=5)
    state = State(4, 3, 0, 0, False, True, False, False, -1, [], None, [own, obs.current.players[1]])
    select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    fallback = [1]; self.assertEqual(self.call(Observation(select, [], state), fallback), [0]); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_mine_stadium_mutation_aborts = _test_mine_stadium_mutation_aborts


def _v1_kadabra(self, appear=False):
    return Pokemon(742, 15, 80, 80, appear, [EnergyType.PSYCHIC], [self.card(5, 0, 16)], [], [self.card(741, 0, 17)])
V1PackageTests.kadabra = _v1_kadabra


def _v1_alakazam_evolution_main(self, appear=False, duplicate=False):
    obs, hand = self.main_obs(hand_ids=[743, 1152, 1152, 1152], target_hp=120, options_card_ids=[])
    obs.current.players[0].active = [self.kadabra(appear)]
    evolve = Option(OptionType.EVOLVE, area=AreaType.HAND, index=0, inPlayArea=AreaType.ACTIVE, inPlayIndex=0)
    obs.select.option = [evolve] + ([copy.deepcopy(evolve)] if duplicate else []) + [Option(OptionType.END)]
    return obs, hand
V1PackageTests.alakazam_evolution_main = _v1_alakazam_evolution_main


def _test_alakazam_positive_yes_reorder_draw_guard_and_attack(self):
    obs, hand = self.alakazam_evolution_main(); self.assertEqual(self.call(obs, [1]), [0]); self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'], v1.RULE_ALAKAZAM)
    card = hand[0]
    evolved = Pokemon(743, card.serial, 140, 140, True, [EnergyType.PSYCHIC], [self.card(5, 0, 16)], [], [self.card(741, 0, 17), self.card(742, 0, 15)])
    own = self.player(active=[evolved], hand=hand[1:], discard=[], hand_count=3)
    state = State(4, 3, 0, 0, False, False, False, False, -1, [], None, [own, obs.current.players[1]])
    ability = SelectData(SelectType.YES_NO, SelectContext.ACTIVATE, 1, 1, 0, 0, [Option(OptionType.NO), Option(OptionType.YES)], None, card, None)
    self.assertEqual(self.call(Observation(ability, [], state), [0]), [1])
    draws = [self.card(1152, 0, 201), self.card(1086, 0, 202), self.card(1231, 0, 203)]
    own_drawn = self.player(active=[evolved], hand=hand[1:] + draws, discard=[], hand_count=6); own_drawn.deckCount = 27
    main_state = State(4, 4, 0, 0, False, False, False, False, -1, [], None, [own_drawn, obs.current.players[1]])
    select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    self.assertEqual(self.call(Observation(select, [], main_state), [1]), [0]); self.assertEqual(v1.V1_TRANSACTION['stage'], 'await_added_attack_verify')
V1PackageTests.test_alakazam_positive_yes_reorder_draw_guard_and_attack = _test_alakazam_positive_yes_reorder_draw_guard_and_attack


def _test_alakazam_negative_immature_duplicate_or_unsafe_deck(self):
    for appear, duplicate, deck_count in ((True, False, 30), (False, True, 30), (False, False, 3)):
        v1.reset(); obs, _ = self.alakazam_evolution_main(appear, duplicate); obs.current.players[0].deckCount = deck_count
        fallback = [len(obs.select.option) - 1]; self.assertIs(self.call(obs, fallback), fallback); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_alakazam_negative_immature_duplicate_or_unsafe_deck = _test_alakazam_negative_immature_duplicate_or_unsafe_deck


def _test_alakazam_draw_snapshot_mutation_aborts(self):
    obs, hand = self.alakazam_evolution_main(); self.assertEqual(self.call(obs, [1]), [0]); card = hand[0]
    evolved = Pokemon(743, card.serial, 140, 140, True, [EnergyType.PSYCHIC], [self.card(5, 0, 16)], [], [self.card(741, 0, 17), self.card(742, 0, 15)])
    own = self.player(active=[evolved], hand=hand[1:], discard=[], hand_count=3)
    state = State(4, 3, 0, 0, False, False, False, False, -1, [], None, [own, obs.current.players[1]])
    ability = SelectData(SelectType.YES_NO, SelectContext.ACTIVATE, 1, 1, 0, 0, [Option(OptionType.YES), Option(OptionType.NO)], None, card, None)
    self.assertEqual(self.call(Observation(ability, [], state), [1]), [0])
    draws = [self.card(1152, 0, 211), self.card(1086, 0, 212), self.card(1231, 0, 213)]
    mutated = self.player(active=[evolved], hand=hand[1:] + draws, discard=[], hand_count=6); mutated.deckCount = 28
    main_state = State(4, 4, 0, 0, False, False, False, False, -1, [], None, [mutated, obs.current.players[1]])
    select = SelectData(SelectType.MAIN, SelectContext.MAIN, 1, 1, 0, 0, [Option(OptionType.ATTACK, attackId=1072), Option(OptionType.END)], None, None, None)
    fallback = [1]; self.assertEqual(self.call(Observation(select, [], main_state), fallback), [0]); self.assertIsNone(v1.V1_TRANSACTION)
V1PackageTests.test_alakazam_draw_snapshot_mutation_aborts = _test_alakazam_draw_snapshot_mutation_aborts

if __name__ == '__main__':
    unittest.main()


