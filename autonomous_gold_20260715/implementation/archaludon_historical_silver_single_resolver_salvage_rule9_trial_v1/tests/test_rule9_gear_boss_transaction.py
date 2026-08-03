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
    / "archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1"
)
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, LogType, OptionType, SelectContext, SelectType


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, hp=None, energy_count=0, tools=()):
    data = main._parent.CARD_DB[card_id]
    energy_serials = tuple(10000 + seat * 1000 + serial * 4 + i for i in range(energy_count))
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": seat,
        "hp": data.hp if hp is None else hp,
        "maxHp": data.hp,
        "appearThisTurn": False,
        "energies": [int(main._EnergyType.METAL)] * energy_count,
        "energyCards": [card(main._METAL_ENERGY, value, seat) for value in energy_serials],
        "tools": list(tools),
        "preEvolution": [],
    }


def player(seat, hand, active, bench=(), *, prizes=1, deck=20, discard=(), hand_count=None):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": deck,
        "discard": list(discard),
        "prize": [None] * prizes,
        "handCount": len(hand) if hand_count is None and hand is not None else (hand_count or 0),
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def play(index):
    return {"type": int(OptionType.PLAY), "index": index}


def attack(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def end():
    return {"type": int(OptionType.END)}


def looking_card(index, seat):
    return {
        "type": int(OptionType.CARD),
        "area": int(AreaType.LOOKING),
        "index": index,
        "playerIndex": seat,
    }


def bench_card(index, seat):
    return {
        "type": int(OptionType.CARD),
        "area": int(AreaType.BENCH),
        "index": index,
        "playerIndex": seat,
    }


def observation(seat, ours, theirs, options, *, action_count=4, supporter=False):
    return {
        "select": {
            "type": int(SelectType.MAIN),
            "context": int(SelectContext.MAIN),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": list(options),
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": 9,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": supporter,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": [ours, theirs] if seat == 0 else [theirs, ours],
        },
        "search_begin_input": None,
    }


CASES = (
    (main._DURALUDON, 223, 1, 21, None, 160, 30),
    (main._DURALUDON, 224, 3, 21, None, 21, 80),
    (main._ARCHALUDON_EX, 253, 3, 24, None, 24, 220),
    (main._ARCHALUDON, 1212, 3, 23, None, 21, 120),
)


def transaction_start(seat, case=CASES[2], *, extra_bench=False):
    attacker_id, attack_id, energy_count, current_id, current_hp, target_id, target_hp = case
    gear = card(main._GEAR, 100 + seat * 1000, seat)
    attacker = pokemon(
        attacker_id, 200 + seat * 1000, seat, energy_count=energy_count
    )
    current = pokemon(
        current_id, 300 + seat * 1000, 1 - seat, hp=current_hp
    )
    target = pokemon(target_id, 400 + seat * 1000, 1 - seat, hp=target_hp)
    bench = [target]
    if extra_bench:
        bench.append(pokemon(24, 450 + seat * 1000, 1 - seat))
    ours = player(seat, [gear], attacker)
    theirs = player(1 - seat, None, current, bench)
    raw = observation(seat, ours, theirs, [play(0), attack(attack_id), end()])
    return raw, gear, attacker, current, target


def reveal_prompt(start, support_ids, *, serials=None, reverse_looking=False, reverse_options=False):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    gear = ours["hand"][0]
    support_ids = list(support_ids)
    if serials is None:
        serials = [5000 + seat * 1000 + i for i in range(len(support_ids))]
    looking = [card(card_id, serial, seat) for card_id, serial in zip(support_ids, serials)]
    filler_ids = (8, 169, 190, 1121, 1122, 1147, 1152)
    for offset in range(7 - len(looking)):
        looking.append(card(filler_ids[offset], 6000 + seat * 1000 + offset, seat))
    if reverse_looking:
        looking.reverse()
    ours["hand"] = []
    ours["handCount"] = 0
    ours["deckCount"] -= 7
    raw["current"]["turnActionCount"] += 1
    raw["current"]["looking"] = looking
    options = [
        looking_card(index, seat)
        for index, value in enumerate(looking)
        if main._parent.CARD_DB[value["id"]].cardType == main._CardType.SUPPORTER
    ]
    if reverse_options:
        options.reverse()
    raw["select"].update(
        type=int(SelectType.CARD),
        context=int(SelectContext.TO_HAND),
        minCount=0,
        maxCount=1,
        option=options,
        effect=gear,
    )
    raw["logs"] = [
        {
            "type": int(LogType.PLAY),
            "playerIndex": seat,
            "cardId": main._GEAR,
            "serial": gear["serial"],
        }
    ] + [
        {
            "type": int(LogType.MOVE_CARD),
            "playerIndex": seat,
            "cardId": value["id"],
            "serial": value["serial"],
            "fromArea": int(AreaType.DECK),
            "toArea": int(AreaType.LOOKING),
        }
        for value in looking
    ]
    return raw


def reveal_position(raw, card_id, *, minimum_serial=False):
    looking = raw["current"]["looking"]
    options = raw["select"]["option"]
    matches = []
    for position, option in enumerate(options):
        value = looking[option["index"]]
        if value["id"] == card_id:
            matches.append((value["serial"], position))
    if not matches:
        return None
    return min(matches)[1] if minimum_serial else matches[0][1]


def post_reveal_main(reveal, *, boss_hit):
    raw = copy.deepcopy(reveal)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    gear = raw["select"]["effect"]
    looking = list(raw["current"]["looking"])
    bosses = sorted(
        (value for value in looking if value["id"] == main._BOSS),
        key=lambda value: value["serial"],
    )
    selected = bosses[0] if boss_hit else None
    ours["hand"] = [] if selected is None else [selected]
    ours["handCount"] = len(ours["hand"])
    ours["discard"] = list(ours["discard"]) + [gear]
    ours["deckCount"] += len(looking) - (1 if selected is not None else 0)
    raw["current"]["looking"] = None
    attack_id = main._materialization_owner["attack_id"]
    options = [attack(attack_id)]
    if selected is not None:
        options.append(play(0))
    options.append(end())
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        minCount=1,
        maxCount=1,
        option=options,
        effect=None,
    )
    raw["logs"] = [
        {
            "type": int(LogType.MOVE_CARD),
            "playerIndex": seat,
            "cardId": value["id"],
            "serial": value["serial"],
            "fromArea": int(AreaType.LOOKING),
            "toArea": int(AreaType.HAND if value == selected else AreaType.DECK),
        }
        for value in reversed(looking)
    ] + [{"type": int(LogType.SHUFFLE), "playerIndex": seat}]
    return raw, selected


def transaction_attack_options(raw):
    active_id = raw["current"]["players"][raw["current"]["yourIndex"]]["active"][0]["id"]
    selected = [
        option
        for option in raw["select"]["option"]
        if option.get("type") == int(OptionType.ATTACK)
        and option.get("attackId") in main._ATTACKER_ATTACKS[active_id]
    ]
    return selected


def target_prompt(post, boss):
    raw = copy.deepcopy(post)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    ours["hand"] = []
    ours["handCount"] = 0
    raw["current"]["supporterPlayed"] = True
    raw["current"]["turnActionCount"] += 1
    raw["select"].update(
        type=int(SelectType.CARD),
        context=int(SelectContext.SWITCH),
        option=[
            bench_card(index, 1 - seat)
            for index in range(len(raw["current"]["players"][1 - seat]["bench"]))
        ],
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


def attack_prompt(target_raw, boss, current, target, attack_id):
    raw = copy.deepcopy(target_raw)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    theirs = raw["current"]["players"][1 - seat]
    target_index = next(
        index for index, value in enumerate(theirs["bench"]) if value["serial"] == target["serial"]
    )
    theirs["active"] = [target]
    theirs["bench"][target_index] = current
    ours["discard"] = list(ours["discard"]) + [boss]
    raw["current"]["turnActionCount"] += 1
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        option=[attack(attack_id), end()],
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


class Rule9GearBossTransactionTests(unittest.TestCase):
    def setUp(self):
        main._setup_ledger = None
        main._materialization_owner = None
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

    def arm(self, seat=0, case=CASES[2], *, extra_bench=False):
        start, gear, attacker, current, target = transaction_start(
            seat, case, extra_bench=extra_bench
        )
        self.assertEqual(self.call(start, [0]), [0])
        self.assertEqual(main._last_proposal["rule_id"], main._RULE9_ID)
        self.assertEqual(
            main._last_proposal["purpose"], "RULE9_PARENT_GEAR_ENTRY_SAME_ACTION"
        )
        return start, gear, attacker, current, target

    def test_both_seats_all_supported_attacks_complete(self):
        for seat in (0, 1):
            for case in CASES:
                with self.subTest(seat=seat, attack_id=case[1]):
                    self.setUp()
                    start, _gear, attacker, current, target = self.arm(seat, case)
                    reveal = reveal_prompt(
                        start, [main._EXPLORER, main._BOSS, main._LILLIE]
                    )
                    boss_position = reveal_position(reveal, main._BOSS, minimum_serial=True)
                    self.assertEqual(self.call(reveal, []), [boss_position])
                    self.assertEqual(
                        main._last_proposal["purpose"], "RULE9_REVEAL_BOUND_BOSS"
                    )
                    post, boss = post_reveal_main(reveal, boss_hit=True)
                    self.assertEqual(self.call(post, [0]), [1])
                    self.assertEqual(
                        main._last_proposal["purpose"],
                        "RULE9_POST_ACQUISITION_BOSS_PLAY",
                    )
                    target_raw = target_prompt(post, boss)
                    self.assertEqual(self.call(target_raw, [0]), [0])
                    self.assertEqual(
                        main._last_proposal["purpose"], "RULE9_BOUND_BOSS_TARGET"
                    )
                    attack_raw = attack_prompt(
                        target_raw, boss, current, target, case[1]
                    )
                    self.assertEqual(self.call(attack_raw, [1]), [0])
                    self.assertEqual(
                        main._last_proposal["purpose"], "RULE9_BOUND_SAME_ATTACK"
                    )
                    final = copy.deepcopy(attack_raw)
                    final["select"].update(
                        type=int(SelectType.CARD),
                        context=int(SelectContext.TO_HAND),
                        minCount=0,
                        maxCount=0,
                        option=[],
                    )
                    final["logs"] = [
                        {
                            "type": int(LogType.ATTACK),
                            "playerIndex": seat,
                            "cardId": attacker["id"],
                            "serial": attacker["serial"],
                            "attackId": case[1],
                        }
                    ]
                    self.assertEqual(self.call(final, []), [])
                    self.assertIsNone(main._materialization_owner)
                    self.assertEqual(
                        main._last_telemetry["rejection_reason"],
                        "rule9_attack_dispatched",
                    )

    def test_all_reveal_subsets_both_seats_and_miss_confirmation(self):
        subsets = (
            (),
            (main._BOSS,),
            (main._EXPLORER,),
            (main._LILLIE,),
            (main._BOSS, main._EXPLORER),
            (main._BOSS, main._LILLIE),
            (main._EXPLORER, main._LILLIE),
            (main._BOSS, main._EXPLORER, main._LILLIE),
        )
        for seat in (0, 1):
            for subset in subsets:
                with self.subTest(seat=seat, subset=subset):
                    self.setUp()
                    start, *_ = self.arm(seat)
                    reveal = reveal_prompt(start, subset)
                    result = self.call(reveal, [0] if reveal["select"]["option"] else [])
                    if main._BOSS in subset:
                        self.assertEqual(
                            result, [reveal_position(reveal, main._BOSS, minimum_serial=True)]
                        )
                        self.assertEqual(
                            main._last_proposal["purpose"], "RULE9_REVEAL_BOUND_BOSS"
                        )
                    else:
                        self.assertEqual(result, [])
                        self.assertEqual(
                            main._last_proposal["purpose"],
                            "RULE9_REVEAL_UNSUPPORTED_EMPTY",
                        )
                        post, _boss = post_reveal_main(reveal, boss_hit=False)
                        self.assertEqual(self.call(post, [0]), [0])
                        self.assertIsNone(main._materialization_owner)
                        self.assertEqual(
                            main._last_telemetry["rejection_reason"],
                            "rule9_miss_confirmed",
                        )

    def test_lowest_boss_reversal_and_identical_retries(self):
        start, _gear, _attacker, current, target = self.arm(0, extra_bench=True)
        retry_start = copy.deepcopy(start)
        retry_start["select"]["option"].reverse()
        self.assertEqual(self.call(retry_start, [2]), [2])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        reveal = reveal_prompt(
            start,
            [main._BOSS, main._EXPLORER, main._BOSS, main._LILLIE],
            serials=[5100, 5101, 5099, 5102],
            reverse_looking=True,
            reverse_options=True,
        )
        expected = reveal_position(reveal, main._BOSS, minimum_serial=True)
        self.assertEqual(self.call(reveal, []), [expected])
        retry_reveal = reveal_prompt(
            start,
            [main._BOSS, main._EXPLORER, main._BOSS, main._LILLIE],
            serials=[5100, 5101, 5099, 5102],
            reverse_looking=False,
            reverse_options=False,
        )
        expected_retry = reveal_position(retry_reveal, main._BOSS, minimum_serial=True)
        self.assertEqual(self.call(retry_reveal, []), [expected_retry])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        post, boss = post_reveal_main(retry_reveal, boss_hit=True)
        self.assertEqual(self.call(post, [0]), [1])
        retry_post = copy.deepcopy(post)
        retry_post["select"]["option"].reverse()
        self.assertEqual(self.call(retry_post, [2]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        target_raw = target_prompt(post, boss)
        target_raw["select"]["option"].reverse()
        self.assertEqual(self.call(target_raw, [0]), [1])
        retry_target = copy.deepcopy(target_raw)
        retry_target["select"]["option"].reverse()
        self.assertEqual(self.call(retry_target, [0]), [0])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        attack_raw = attack_prompt(target_raw, boss, current, target, 253)
        self.assertEqual(self.call(attack_raw, [1]), [0])
        retry_attack = copy.deepcopy(attack_raw)
        retry_attack["select"]["option"].reverse()
        self.assertEqual(self.call(retry_attack, [0]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

    def test_entry_fail_closed_boundaries_and_hidden_hand_invariance(self):
        cases = []
        non_gear, *_ = transaction_start(0)
        cases.append((non_gear, [1]))
        boss_hand, *_ = transaction_start(0)
        boss_hand["current"]["players"][0]["hand"].append(card(main._BOSS, 999, 0))
        boss_hand["current"]["players"][0]["handCount"] = 2
        cases.append((boss_hand, [0]))
        one_above, *_ = transaction_start(0)
        one_above["current"]["players"][1]["bench"][0]["hp"] = 221
        cases.append((one_above, [0]))
        zero_attacks, *_ = transaction_start(0)
        zero_attacks["select"]["option"] = [play(0), end()]
        cases.append((zero_attacks, [0]))
        multiple_attacks, *_ = transaction_start(0)
        multiple_attacks["select"]["option"].insert(2, attack(253))
        cases.append((multiple_attacks, [0]))
        multiple_targets, *_ = transaction_start(0)
        multiple_targets["current"]["players"][1]["bench"].append(
            pokemon(24, 401, 1, hp=220)
        )
        cases.append((multiple_targets, [0]))
        supporter_used, *_ = transaction_start(0)
        supporter_used["current"]["supporterPlayed"] = True
        cases.append((supporter_used, [0]))
        no_bench, *_ = transaction_start(0)
        no_bench["current"]["players"][1]["bench"] = []
        cases.append((no_bench, [0]))
        zero_deck, *_ = transaction_start(0)
        zero_deck["current"]["players"][0]["deckCount"] = 0
        cases.append((zero_deck, [0]))
        status, *_ = transaction_start(0)
        status["current"]["players"][1]["poisoned"] = True
        cases.append((status, [0]))
        tool, *_ = transaction_start(0)
        tool["current"]["players"][1]["bench"][0]["tools"] = [
            card(1159, 800, 1)
        ]
        cases.append((tool, [0]))
        stadium, *_ = transaction_start(0)
        stadium["current"]["stadium"] = [card(1242, 900, 0)]
        cases.append((stadium, [0]))
        ability, *_ = transaction_start(0)
        ability["current"]["players"][1]["bench"] = [pokemon(28, 400, 1)]
        cases.append((ability, [0]))
        for raw, parent_action in cases:
            with self.subTest(index=cases.index((raw, parent_action))):
                self.setUp()
                self.assertEqual(self.call(raw, parent_action), parent_action)
                self.assertFalse(
                    main._last_proposal is not None
                    and main._last_proposal["rule_id"] == main._RULE9_ID
                )
                self.assertIsNone(main._materialization_owner)

        terminal, *_ = transaction_start(0)
        terminal["current"]["players"][1]["active"][0]["hp"] = 220
        self.setUp()
        self.call(terminal, [0])
        self.assertNotEqual(
            None if main._last_proposal is None else main._last_proposal["purpose"],
            "RULE9_PARENT_GEAR_ENTRY_SAME_ACTION",
        )

        first, *_ = transaction_start(0)
        first["current"]["players"][1]["hand"] = [card(8, 700, 1)]
        first["current"]["players"][1]["handCount"] = 1
        second = copy.deepcopy(first)
        second["current"]["players"][1]["hand"] = [card(main._BOSS, 701, 1)]
        self.setUp()
        left = self.call(first, [0])
        left_proof = copy.deepcopy(main._last_proposal["exact_proof"])
        self.setUp()
        right = self.call(second, [0])
        right_proof = copy.deepcopy(main._last_proposal["exact_proof"])
        self.assertEqual(left, right)
        self.assertEqual(left_proof, right_proof)

    def test_reveal_malformed_or_duplicate_semantics_abort(self):
        mutations = (
            lambda raw: raw["select"].update(effect=card(main._GEAR, 9999, 0)),
            lambda raw: raw["select"]["option"].append(
                copy.deepcopy(raw["select"]["option"][0])
            ),
            lambda raw: raw["select"]["option"][0].update(index=6),
            lambda raw: raw["current"].update(turn=10),
            lambda raw: raw["current"]["players"][0].update(deckCount=12),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.setUp()
                start, *_ = self.arm(0)
                reveal = reveal_prompt(start, [main._BOSS, main._EXPLORER])
                mutation(reveal)
                self.assertEqual(self.call(reveal, []), [])
                self.assertIsNone(main._materialization_owner)
                self.assertTrue(
                    main._last_telemetry["rejection_reason"].startswith(
                        "rule9_irreversible_abort:"
                    )
                )

    def test_post_acquisition_and_continuation_drift_abort(self):
        self.arm(0)
        start, _gear, _attacker, current, target = transaction_start(0)
        reveal = reveal_prompt(start, [main._BOSS])
        self.assertEqual(self.call(reveal, []), [0])
        stale, boss = post_reveal_main(reveal, boss_hit=True)
        stale["current"]["players"][0]["deckCount"] += 1
        self.assertEqual(self.call(stale, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, *_ = self.arm(0)
        reveal = reveal_prompt(start, [main._BOSS])
        self.call(reveal, [])
        post, boss = post_reveal_main(reveal, boss_hit=True)
        self.call(post, [0])
        duplicate_target = target_prompt(post, boss)
        duplicate_target["select"]["option"].append(
            copy.deepcopy(duplicate_target["select"]["option"][0])
        )
        self.assertEqual(self.call(duplicate_target, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, *_gear, current, target = self.arm(0)
        reveal = reveal_prompt(start, [main._BOSS])
        self.call(reveal, [])
        post, boss = post_reveal_main(reveal, boss_hit=True)
        self.call(post, [0])
        target_raw = target_prompt(post, boss)
        self.call(target_raw, [0])
        changed_attack = attack_prompt(target_raw, boss, current, target, 253)
        changed_attack["select"]["option"][0]["attackId"] = 224
        self.assertEqual(self.call(changed_attack, [1]), [1])
        self.assertIsNone(main._materialization_owner)

    def test_owner_collision_and_metadata_drift_fail_closed(self):
        start, *_ = transaction_start(0)
        main._materialization_owner = {
            "owner": main._RULE4_ID,
            "stage": "MATERIALIZATION_EMITTED",
        }
        self.assertEqual(self.call(start, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, *_ = self.arm(0)
        reveal = reveal_prompt(start, [main._BOSS])
        with mock.patch.object(main._parent.CARD_DB[main._GEAR], "name", "drift"):
            self.assertEqual(self.call(reveal, []), [])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(
            main._last_telemetry["rejection_reason"],
            "rule9_irreversible_abort:metadata_drift",
        )


if __name__ == "__main__":
    unittest.main()
