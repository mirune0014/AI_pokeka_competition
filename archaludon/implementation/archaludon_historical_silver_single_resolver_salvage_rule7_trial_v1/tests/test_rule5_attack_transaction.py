from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock


AUTO = Path(__file__).resolve().parents[3]
CANDIDATE = (
    AUTO
    / "candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1"
)
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, LogType, OptionType, SelectContext, SelectType


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, hp=None, energy_serials=(), tools=()):
    data = main._parent.CARD_DB[card_id]
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp if hp is None else hp,
        "maxHp": data.hp,
        "appearThisTurn": False,
        "energies": [int(main._parent.CARD_DB[main._METAL_ENERGY].energyType)]
        * len(energy_serials),
        "energyCards": [
            card(main._METAL_ENERGY, energy_serial, seat)
            for energy_serial in energy_serials
        ],
        "tools": list(tools),
        "preEvolution": [],
    }


def player(seat, hand, active, bench=(), *, prizes=4, discard=(), status=False):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": list(discard),
        "prize": [None] * prizes,
        "handCount": len(hand) if hand is not None else 0,
        "hand": hand,
        "poisoned": status,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def attack(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def end():
    return {"type": int(OptionType.END)}


def play(index, seat):
    return {"type": int(OptionType.PLAY), "index": index, "playerIndex": seat}


def bench_card(index, seat):
    return {
        "type": int(OptionType.CARD),
        "area": int(AreaType.BENCH),
        "index": index,
        "playerIndex": seat,
    }


def observation(
    seat,
    ours,
    theirs,
    options,
    *,
    action_count=3,
    supporter=False,
    stadium=(),
    context=SelectContext.MAIN,
    select_type=None,
    effect=None,
    logs=(),
    result=-1,
):
    if select_type is None:
        select_type = SelectType.MAIN if context == SelectContext.MAIN else SelectType.CARD
    return {
        "select": {
            "type": int(select_type),
            "context": int(context),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": list(options),
            "deck": None,
            "contextCard": None,
            "effect": effect,
        },
        "logs": list(logs),
        "current": {
            "turn": 8,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": supporter,
            "stadiumPlayed": bool(stadium),
            "energyAttached": False,
            "retreated": False,
            "result": result,
            "stadium": list(stadium),
            "looking": None,
            "players": [ours, theirs] if seat == 0 else [theirs, ours],
        },
        "search_begin_input": None,
    }


def boss_start(seat, current_id, target_id):
    boss = card(main._BOSS, 100 + seat * 1000, seat)
    active = pokemon(main._ARCHALUDON_EX, 200 + seat * 1000, seat, energy_serials=(501, 502, 503))
    current = pokemon(current_id, 300 + seat * 1000, 1 - seat)
    target = pokemon(target_id, 400 + seat * 1000, 1 - seat)
    ours = player(seat, [boss], active)
    theirs = player(1 - seat, None, current, [target])
    return observation(seat, ours, theirs, [attack(253), play(0, seat), end()]), boss, active, current, target


def boss_target_prompt(start, boss, *, duplicate=False, reverse=False):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    ours["hand"] = []
    ours["handCount"] = 0
    raw["current"]["supporterPlayed"] = True
    raw["current"]["turnActionCount"] += 1
    options = [bench_card(0, 1 - seat)]
    if duplicate:
        options.append(bench_card(0, 1 - seat))
    if reverse:
        options.reverse()
    raw["select"].update(
        type=int(SelectType.CARD),
        context=int(SelectContext.SWITCH),
        option=options,
        effect=boss,
    )
    raw["logs"] = [
        {
            "type": int(LogType.PLAY),
            "playerIndex": seat,
            "cardId": main._BOSS,
            "serial": boss["serial"],
        }
    ]
    return raw


def boss_attack_prompt(target_prompt, boss, current, target, *, duplicate=False):
    raw = copy.deepcopy(target_prompt)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    theirs = raw["current"]["players"][1 - seat]
    ours["discard"] = [boss]
    theirs["active"] = [target]
    theirs["bench"] = [current]
    raw["current"]["turnActionCount"] += 1
    options = [attack(253), end()]
    if duplicate:
        options.insert(0, attack(253))
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        option=options,
        effect=None,
    )
    raw["logs"] = [
        {
            "type": int(LogType.SWITCH),
            "playerIndex": 1 - seat,
            "cardIdActive": current["id"],
            "serialActive": current["serial"],
            "cardIdBench": target["id"],
            "serialBench": target["serial"],
        }
    ]
    return raw


class Rule5AttackTransactionTests(unittest.TestCase):
    def setUp(self):
        main._setup_ledger = None
        main._materialization_owner = None
        main._rule7_passive_token = None
        main._last_proposal = None
        main._parent._opp_last_attack_id = None
        main._parent._cur_turn_logs.clear()

    def call(self, raw, parent_action):
        with mock.patch.object(main._parent, "agent", return_value=parent_action) as parent:
            result = main.agent(copy.deepcopy(raw))
        self.assertEqual(parent.call_count, 1)
        self.assertEqual(main._last_telemetry["parent_call_count"], 1)
        if main._last_proposal is not None:
            self.assertEqual(
                set(main._last_proposal),
                {"rule_id", "action", "category", "purpose", "exact_proof", "transaction"},
            )
        return result

    def test_all_four_registered_attacks_unique_terminal_and_parent_terminal(self):
        cases = (
            (main._DURALUDON, 223, 160, None),
            (main._DURALUDON, 224, 23, 10),
            (main._ARCHALUDON_EX, 253, 23, None),
            (main._ARCHALUDON, 1212, 21, None),
        )
        for attacker_id, attack_id, target_id, hp in cases:
            with self.subTest(attack_id=attack_id):
                self.setUp()
                ours = player(0, [], pokemon(attacker_id, 10, 0, hp=hp), prizes=1)
                theirs = player(1, None, pokemon(target_id, 20, 1))
                raw = observation(0, ours, theirs, [end(), attack(attack_id)])
                self.assertEqual(self.call(raw, [0]), [1])
                self.assertEqual(main._last_proposal["purpose"], "DIRECT_EXACT_CURRENT_WIN")
                self.setUp()
                self.assertEqual(self.call(raw, [1]), [1])

    def test_damage_order_weakness_resistance_and_full_metal_lab(self):
        ours = player(0, [], pokemon(main._ARCHALUDON_EX, 10, 0), prizes=1)
        weak = player(1, None, pokemon(723, 20, 1))
        raw = observation(0, ours, weak, [end(), attack(253)])
        self.assertEqual(self.call(raw, [0]), [1])

        self.setUp()
        resisted = player(1, None, pokemon(24, 20, 1, hp=200))
        raw = observation(0, ours, resisted, [end(), attack(253)])
        with mock.patch.object(
            main._parent.CARD_DB[24], "resistance", main._EnergyType.METAL
        ):
            self.assertEqual(self.call(raw, [0]), [0])

        self.setUp()
        lab = card(main._FULL_METAL_LAB, 700, 0)
        metal = player(1, None, pokemon(84, 20, 1, hp=210))
        raw = observation(0, ours, metal, [end(), attack(253)], stadium=[lab])
        self.assertEqual(self.call(raw, [0]), [0])

    def test_boss_prize_conversions_and_both_seat_full_transaction(self):
        cases = ((24, 21, 0, 1), (24, 99, 0, 2), (21, 99, 1, 2), (21, 723, 1, 3))
        for seat in (0, 1):
            for current_id, target_id, current_take, target_take in cases:
                with self.subTest(seat=seat, current_take=current_take, target_take=target_take):
                    self.setUp()
                    start, boss, attacker, current, target = boss_start(seat, current_id, target_id)
                    self.assertEqual(self.call(start, [0]), [1])
                    self.assertEqual(main._materialization_owner["current_take"], current_take)
                    self.assertEqual(main._materialization_owner["target_take"], target_take)
                    target_prompt = boss_target_prompt(start, boss)
                    self.assertEqual(self.call(target_prompt, [0]), [0])
                    attack_prompt = boss_attack_prompt(target_prompt, boss, current, target)
                    self.assertEqual(self.call(attack_prompt, [1]), [0])
                    final = copy.deepcopy(attack_prompt)
                    final["logs"] = [{
                        "type": int(LogType.ATTACK), "playerIndex": seat,
                        "cardId": attacker["id"], "serial": attacker["serial"], "attackId": 253,
                    }]
                    final["select"]["context"] = int(SelectContext.TO_HAND)
                    final["select"]["type"] = int(SelectType.CARD)
                    final["select"]["option"] = []
                    self.assertEqual(self.call(final, []), [])
                    self.assertIsNone(main._materialization_owner)
                    self.assertEqual(main._last_telemetry["rejection_reason"], "boss_attack_dispatched")

    def test_transaction_retries_option_permutation_and_semantic_duplicates(self):
        start, boss, _attacker, current, target = boss_start(0, 24, 99)
        start["select"]["option"].insert(1, play(0, 0))
        self.assertEqual(self.call(start, [0]), [1])
        retry = copy.deepcopy(start)
        retry["select"]["option"].reverse()
        self.assertEqual(self.call(retry, [len(retry["select"]["option"]) - 1]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        target_prompt = boss_target_prompt(start, boss, duplicate=True, reverse=True)
        self.assertEqual(self.call(target_prompt, [0]), [0])
        retry_target = copy.deepcopy(target_prompt)
        retry_target["select"]["option"].reverse()
        self.assertEqual(self.call(retry_target, [0]), [0])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        attack_prompt = boss_attack_prompt(target_prompt, boss, current, target, duplicate=True)
        self.assertEqual(self.call(attack_prompt, [2]), [0])
        retry_attack = copy.deepcopy(attack_prompt)
        retry_attack["select"]["option"].reverse()
        self.assertEqual(self.call(retry_attack, [0]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

    def test_direct_precedence_and_negative_boundaries(self):
        start, _boss, _attacker, _current, _target = boss_start(0, 21, 99)
        start["current"]["players"][0]["prize"] = [None]
        self.assertEqual(self.call(start, [0]), [0])
        self.assertEqual(main._last_proposal["purpose"], "DIRECT_EXACT_CURRENT_WIN")
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        ours = player(0, [], pokemon(main._DURALUDON, 10, 0, hp=120), prizes=1)
        theirs = player(1, None, pokemon(160, 20, 1))
        ambiguous = observation(
            0, ours, theirs, [end(), attack(223), attack(224)]
        )
        self.assertEqual(self.call(ambiguous, [0]), [0])
        self.assertEqual(
            main._last_telemetry["rejection_reason"],
            "multiple_terminal_attack_ids",
        )

        negatives = []
        equal, *_ = boss_start(0, 21, 22)
        negatives.append(equal)
        multiple, boss, active, current, target = boss_start(0, 24, 99)
        multiple["current"]["players"][1]["bench"].append(pokemon(108, 401, 1))
        negatives.append(multiple)
        supporter, *_ = boss_start(0, 24, 99)
        supporter["current"]["supporterPlayed"] = True
        negatives.append(supporter)
        status, *_ = boss_start(0, 24, 99)
        status["current"]["players"][1]["poisoned"] = True
        negatives.append(status)
        tool, *_ = boss_start(0, 24, 99)
        tool["current"]["players"][1]["bench"][0]["tools"] = [card(1159, 800, 1)]
        negatives.append(tool)
        for raw in negatives:
            with self.subTest(kind=len(negatives)):
                self.setUp()
                self.assertEqual(self.call(raw, [0]), [0])
                self.assertIsNone(main._materialization_owner)

    def test_stale_or_mismatched_transaction_clears_to_parent(self):
        start, boss, _attacker, _current, _target = boss_start(0, 24, 99)
        self.assertEqual(self.call(start, [0]), [1])
        stale = boss_target_prompt(start, boss)
        stale["current"]["turn"] += 1
        self.assertEqual(self.call(stale, [0]), [0])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._last_telemetry["rejection_reason"], "boss_confirmation_failed")


if __name__ == "__main__":
    unittest.main()
