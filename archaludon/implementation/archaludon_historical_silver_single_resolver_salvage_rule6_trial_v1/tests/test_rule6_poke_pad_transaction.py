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
    / "archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1"
)
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, LogType, OptionType, SelectContext, SelectType


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, energy_serials=(), appear=False, hp=None):
    data = main._parent.CARD_DB[card_id]
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp if hp is None else hp,
        "maxHp": data.hp,
        "appearThisTurn": appear,
        "energies": [int(main._EnergyType.METAL)] * len(energy_serials),
        "energyCards": [
            card(main._METAL_ENERGY, energy_serial, seat)
            for energy_serial in energy_serials
        ],
        "tools": [],
        "preEvolution": [],
    }


def player(seat, hand, active, bench=(), *, deck_count=3, discard=(), prizes=4):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": deck_count,
        "discard": list(discard),
        "prize": [None] * prizes,
        "handCount": len(hand) if hand is not None else 0,
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def attack(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def end():
    return {"type": int(OptionType.END)}


def play(index, seat=None):
    value = {"type": int(OptionType.PLAY), "index": index}
    if seat is not None:
        value["playerIndex"] = seat
    return value


def attach(index, seat, bench_index=0):
    return {
        "type": int(OptionType.ATTACH),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.BENCH),
        "inPlayIndex": bench_index,
    }


def deck_option(index, seat):
    return {
        "type": int(OptionType.CARD),
        "area": int(AreaType.DECK),
        "index": index,
        "playerIndex": seat,
    }


def observation(
    seat,
    ours,
    theirs,
    options,
    *,
    action_count=4,
    energy_attached=False,
    context=SelectContext.MAIN,
    select_type=None,
    minimum=1,
    maximum=1,
    effect=None,
    deck=None,
    logs=(),
    turn=8,
    result=-1,
):
    if select_type is None:
        select_type = SelectType.MAIN if context == SelectContext.MAIN else SelectType.CARD
    return {
        "select": {
            "type": int(select_type),
            "context": int(context),
            "minCount": minimum,
            "maxCount": maximum,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": list(options),
            "deck": deck,
            "contextCard": None,
            "effect": effect,
        },
        "logs": list(logs),
        "current": {
            "turn": turn,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": energy_attached,
            "retreated": False,
            "result": result,
            "stadium": [],
            "looking": None,
            "players": [ours, theirs] if seat == 0 else [theirs, ours],
        },
        "search_begin_input": None,
    }


def start_prompt(seat, *, metal_serials=(70, 60), deck_count=3):
    pad = card(main._POKE_PAD, 20 + seat * 1000, seat)
    metals = [card(main._METAL_ENERGY, serial + seat * 1000, seat) for serial in metal_serials]
    hand = (
        [metals[0], pad] + metals[1:]
        if metals
        else [card(main._BOSS, 80 + seat * 1000, seat), pad]
    )
    active = pokemon(main._DURALUDON, 10 + seat * 1000, seat, energy_serials=(501 + seat * 1000,))
    target = pokemon(21, 90 + seat * 1000, 1 - seat)
    ours = player(seat, hand, active, deck_count=deck_count)
    theirs = player(1 - seat, None, target, deck_count=40)
    raw = observation(seat, ours, theirs, [attack(223), end(), play(1)])
    return raw, pad, metals, active, target


def pad_target_prompt(start, pad, deck_cards, *, option_indices=None):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    mine = raw["current"]["players"][seat]
    mine["hand"].remove(next(value for value in mine["hand"] if value["serial"] == pad["serial"]))
    mine["handCount"] = len(mine["hand"])
    raw["current"]["turnActionCount"] += 1
    if option_indices is None:
        option_indices = list(range(len(deck_cards)))
    raw["select"].update(
        type=int(SelectType.CARD),
        context=int(SelectContext.TO_HAND),
        minCount=0,
        maxCount=1,
        effect=pad,
        deck=list(deck_cards),
        option=[deck_option(index, seat) for index in option_indices],
    )
    raw["logs"] = [{
        "type": int(LogType.PLAY),
        "playerIndex": seat,
        "cardId": main._POKE_PAD,
        "serial": pad["serial"],
    }]
    return raw


def target_in_hand_prompt(start, pad, selected):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    mine = raw["current"]["players"][seat]
    mine["hand"].remove(next(value for value in mine["hand"] if value["serial"] == pad["serial"]))
    mine["hand"].append(selected)
    mine["handCount"] = len(mine["hand"])
    mine["discard"].append(pad)
    mine["deckCount"] -= 1
    raw["current"]["turnActionCount"] += 2
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        minCount=1,
        maxCount=1,
        effect=None,
        deck=None,
        option=[end(), play(len(mine["hand"]) - 1), attack(223)],
    )
    raw["logs"] = [
        {
            "type": int(LogType.MOVE_CARD),
            "playerIndex": seat,
            "cardId": main._DURALUDON,
            "serial": selected["serial"],
            "fromArea": int(AreaType.DECK),
            "toArea": int(AreaType.HAND),
        },
        {"type": int(LogType.SHUFFLE), "playerIndex": seat},
    ]
    return raw


def duraludon_on_bench_prompt(start, pad, selected, metal_serial):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    mine = raw["current"]["players"][seat]
    mine["hand"].remove(next(value for value in mine["hand"] if value["serial"] == pad["serial"]))
    mine["handCount"] = len(mine["hand"])
    mine["discard"].append(pad)
    mine["deckCount"] -= 1
    mine["bench"] = [pokemon(main._DURALUDON, selected["serial"], seat, appear=True)]
    raw["current"]["turnActionCount"] += 3
    metal_index = next(index for index, value in enumerate(mine["hand"]) if value["serial"] == metal_serial)
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        minCount=1,
        maxCount=1,
        effect=None,
        deck=None,
        option=[end(), attach(metal_index, seat), attack(223)],
    )
    raw["logs"] = [{
        "type": int(LogType.PLAY),
        "playerIndex": seat,
        "cardId": main._DURALUDON,
        "serial": selected["serial"],
    }]
    return raw


def ready_prompt(start, pad, selected, metal_serial):
    raw = duraludon_on_bench_prompt(start, pad, selected, metal_serial)
    seat = raw["current"]["yourIndex"]
    mine = raw["current"]["players"][seat]
    metal = next(value for value in mine["hand"] if value["serial"] == metal_serial)
    mine["hand"].remove(metal)
    mine["handCount"] = len(mine["hand"])
    mine["bench"] = [
        pokemon(
            main._DURALUDON,
            selected["serial"],
            seat,
            appear=True,
            energy_serials=(metal_serial,),
        )
    ]
    raw["current"]["turnActionCount"] += 1
    raw["current"]["energyAttached"] = True
    raw["select"]["option"] = [end(), attack(223)]
    raw["logs"] = [{
        "type": int(LogType.ATTACH),
        "playerIndex": seat,
        "cardId": main._METAL_ENERGY,
        "serial": metal_serial,
        "cardIdTarget": main._DURALUDON,
        "serialTarget": selected["serial"],
    }]
    return raw


def whiff_recovery_prompt(start, pad):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    mine = raw["current"]["players"][seat]
    mine["hand"].remove(next(value for value in mine["hand"] if value["serial"] == pad["serial"]))
    mine["handCount"] = len(mine["hand"])
    mine["discard"].append(pad)
    raw["current"]["turnActionCount"] += 2
    raw["select"]["option"] = [end(), attack(223)]
    raw["logs"] = [{"type": int(LogType.SHUFFLE), "playerIndex": seat}]
    return raw


class Rule6PokePadTransactionTests(unittest.TestCase):
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
        return result

    def complete(self, seat):
        start, pad, metals, _active, _target = start_prompt(seat)
        selected = card(main._DURALUDON, 30 + seat * 1000, seat)
        deck_cards = [card(main._CINDERACE, 40 + seat * 1000, seat), selected, card(main._ARCHALUDON, 50 + seat * 1000, seat)]
        self.assertEqual(self.call(start, [2]), [2])
        self.assertEqual(main._materialization_owner["stage"], "PAD_PLAY_EMITTED")
        target = pad_target_prompt(start, pad, deck_cards)
        self.assertEqual(self.call(target, [0]), [1])
        self.assertEqual(main._last_proposal["purpose"], main._RULE6_PAD_TARGET)
        in_hand = target_in_hand_prompt(start, pad, selected)
        self.assertEqual(self.call(in_hand, [0]), [1])
        self.assertEqual(main._last_proposal["purpose"], main._RULE6_DURALUDON_BENCH)
        metal_serial = min(value["serial"] for value in metals)
        on_bench = duraludon_on_bench_prompt(start, pad, selected, metal_serial)
        self.assertEqual(self.call(on_bench, [0]), [1])
        self.assertEqual(main._last_proposal["purpose"], main._RULE6_READY_ATTACH)
        ready = ready_prompt(start, pad, selected, metal_serial)
        self.assertEqual(self.call(ready, [0]), [0])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._last_telemetry["rejection_reason"], "rule6_ready_complete")

    def test_complete_both_seat_path(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                self.setUp()
                self.complete(seat)

    def test_identical_retries_and_option_permutation_at_every_stage(self):
        start, pad, metals, _active, _target = start_prompt(0)
        selected = card(main._DURALUDON, 30, 0)
        deck_cards = [card(main._CINDERACE, 40, 0), selected, card(main._ARCHALUDON, 50, 0)]
        self.assertEqual(self.call(start, [2]), [2])
        retry_start = copy.deepcopy(start)
        retry_start["select"]["option"] = [play(1), attack(223), end()]
        self.assertEqual(self.call(retry_start, [0]), [0])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        target = pad_target_prompt(start, pad, deck_cards, option_indices=[2, 1, 0, 1])
        self.assertEqual(self.call(target, [0]), [1])
        retry_target = copy.deepcopy(target)
        retry_target["select"]["option"].reverse()
        self.assertEqual(self.call(retry_target, [0]), [0])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        in_hand = target_in_hand_prompt(start, pad, selected)
        in_hand["select"]["option"].insert(0, play(len(in_hand["current"]["players"][0]["hand"]) - 1))
        self.assertEqual(self.call(in_hand, [0]), [0])
        retry_hand = copy.deepcopy(in_hand)
        retry_hand["select"]["option"].reverse()
        self.assertEqual(self.call(retry_hand, [0]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        metal_serial = min(value["serial"] for value in metals)
        on_bench = duraludon_on_bench_prompt(start, pad, selected, metal_serial)
        on_bench["select"]["option"].insert(0, copy.deepcopy(on_bench["select"]["option"][1]))
        self.assertEqual(self.call(on_bench, [0]), [0])
        retry_bench = copy.deepcopy(on_bench)
        retry_bench["select"]["option"].reverse()
        self.assertEqual(self.call(retry_bench, [0]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

    def test_lowest_physical_serial_and_equivalent_duplicate_position(self):
        start, pad, _metals, _active, _target = start_prompt(0)
        low = card(main._DURALUDON, 30, 0)
        high = card(main._DURALUDON, 31, 0)
        deck_cards = [high, card(main._CINDERACE, 40, 0), low]
        self.assertEqual(self.call(start, [2]), [2])
        target = pad_target_prompt(start, pad, deck_cards, option_indices=[0, 2, 2])
        self.assertEqual(self.call(target, [0]), [1])
        self.assertEqual(main._materialization_owner["selected_ref"][1], 30)

    def test_whiff_cinderace_and_nonex_only_retry_then_parent_recovery(self):
        start, pad, _metals, _active, _target = start_prompt(0, deck_count=2)
        deck_cards = [card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)]
        self.assertEqual(self.call(start, [2]), [2])
        target = pad_target_prompt(start, pad, deck_cards)
        self.assertEqual(self.call(target, [0]), [])
        self.assertEqual(main._last_proposal["purpose"], main._RULE6_WHIFF_EMPTY)
        retry = copy.deepcopy(target)
        retry["select"]["option"].reverse()
        self.assertEqual(self.call(retry, [1]), [])
        self.assertTrue(main._last_telemetry["duplicate_retry"])
        recovery = whiff_recovery_prompt(start, pad)
        self.assertEqual(self.call(recovery, [1]), [1])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._last_telemetry["rejection_reason"], "rule6_whiff_complete")

    def test_conflicting_duplicate_wrong_effect_and_failed_target_movement_fail_closed(self):
        start, pad, _metals, _active, _target = start_prompt(0, deck_count=2)
        self.assertEqual(self.call(start, [2]), [2])
        conflict_cards = [card(main._DURALUDON, 30, 0), card(main._ARCHALUDON, 30, 0)]
        conflict = pad_target_prompt(start, pad, conflict_cards)
        self.assertEqual(self.call(conflict, [1]), [1])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, pad, _metals, _active, _target = start_prompt(0)
        self.assertEqual(self.call(start, [2]), [2])
        wrong_effect = pad_target_prompt(
            start,
            pad,
            [card(main._DURALUDON, 30, 0), card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)],
        )
        wrong_effect["select"]["effect"] = card(main._POKE_PAD, pad["serial"] + 1, 0)
        self.assertEqual(self.call(wrong_effect, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, pad, _metals, _active, _target = start_prompt(0)
        self.assertEqual(self.call(start, [2]), [2])
        wrong_source = pad_target_prompt(
            start,
            pad,
            [card(main._DURALUDON, 30, 0), card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)],
        )
        wrong_source["logs"][0]["serial"] = pad["serial"] + 1
        self.assertEqual(self.call(wrong_source, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        start, pad, _metals, _active, _target = start_prompt(0)
        selected = card(main._DURALUDON, 30, 0)
        self.assertEqual(self.call(start, [2]), [2])
        target = pad_target_prompt(start, pad, [selected, card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)])
        self.assertEqual(self.call(target, [0]), [0])
        failed = target_in_hand_prompt(start, pad, selected)
        mine = failed["current"]["players"][0]
        mine["hand"].remove(selected)
        mine["handCount"] -= 1
        self.assertEqual(self.call(failed, [0]), [0])
        self.assertIsNone(main._materialization_owner)

    def test_failed_attachment_and_identity_changes_fail_closed(self):
        start, pad, metals, _active, _target = start_prompt(0)
        selected = card(main._DURALUDON, 30, 0)
        self.assertEqual(self.call(start, [2]), [2])
        self.assertEqual(self.call(pad_target_prompt(start, pad, [selected, card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)]), [0]), [0])
        self.assertEqual(self.call(target_in_hand_prompt(start, pad, selected), [0]), [1])
        metal_serial = min(value["serial"] for value in metals)
        self.assertEqual(self.call(duraludon_on_bench_prompt(start, pad, selected, metal_serial), [0]), [1])
        failed = ready_prompt(start, pad, selected, metal_serial)
        failed["current"]["players"][0]["bench"][0] = pokemon(main._DURALUDON, selected["serial"], 0, appear=True)
        self.assertEqual(self.call(failed, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        for field in ("turn", "result", "yourIndex"):
            with self.subTest(field=field):
                self.setUp()
                start, pad, _metals, _active, _target = start_prompt(0)
                self.assertEqual(self.call(start, [2]), [2])
                callback = pad_target_prompt(start, pad, [card(main._DURALUDON, 30, 0), card(main._CINDERACE, 40, 0), card(main._ARCHALUDON, 50, 0)])
                callback["current"][field] = 1 if field != "turn" else 9
                self.assertEqual(self.call(callback, [0]), [0])
                self.assertIsNone(main._materialization_owner)

    def test_start_boundaries_do_not_arm(self):
        cases = []
        parent_non_pad, *_ = start_prompt(0)
        cases.append((parent_non_pad, [1]))
        nonempty, *_ = start_prompt(0)
        nonempty["current"]["players"][0]["bench"] = [pokemon(main._DURALUDON, 30, 0)]
        cases.append((nonempty, [2]))
        full, *_ = start_prompt(0)
        full["current"]["players"][0]["benchMax"] = 0
        cases.append((full, [2]))
        no_metal, *_ = start_prompt(0, metal_serials=())
        cases.append((no_metal, [2]))
        energy_used, *_ = start_prompt(0)
        energy_used["current"]["energyAttached"] = True
        cases.append((energy_used, [2]))
        in_hand, *_ = start_prompt(0)
        in_hand["current"]["players"][0]["hand"].append(card(main._DURALUDON, 30, 0))
        in_hand["current"]["players"][0]["handCount"] += 1
        cases.append((in_hand, [2]))
        no_attack, *_ = start_prompt(0)
        no_attack["select"]["option"] = [end(), play(1)]
        cases.append((no_attack, [1]))
        multiple_attacks, *_ = start_prompt(0)
        multiple_attacks["select"]["option"].insert(1, attack(224))
        cases.append((multiple_attacks, [3]))
        terminal, *_ = start_prompt(0)
        terminal["current"]["players"][0]["prize"] = [None]
        terminal["current"]["players"][1]["active"][0]["hp"] = 20
        cases.append((terminal, [0]))
        for index, (raw, parent_action) in enumerate(cases):
            with self.subTest(index=index):
                self.setUp()
                self.assertEqual(self.call(raw, parent_action), parent_action)
                self.assertIsNone(main._materialization_owner)

        start, *_ = start_prompt(0)
        main._materialization_owner = {"owner": main._RULE4_ID, "stage": "bad"}
        self.assertEqual(self.call(start, [2]), [2])
        self.assertIsNone(main._materialization_owner)


if __name__ == "__main__":
    unittest.main()
