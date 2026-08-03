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


def pokemon(card_id, serial, seat, energy_serials=(), tools=()):
    data = main._parent.CARD_DB[card_id]
    hero = sum(tool["id"] == main._HERO_CAPE for tool in tools)
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp + 100 * hero,
        "maxHp": data.hp + 100 * hero,
        "appearThisTurn": False,
        "energies": [int(main._EnergyType.METAL)] * len(energy_serials),
        "energyCards": [card(main._METAL_ENERGY, value, seat) for value in energy_serials],
        "tools": list(tools),
        "preEvolution": [],
    }


def player(seat, active, bench=(), hand=()):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": [],
        "prize": [None] * 4,
        "handCount": len(hand) if hand is not None else 0,
        "hand": None if hand is None else list(hand),
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def end():
    return {"type": int(OptionType.END)}


def attack(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def turbo_start(seat, bench, energy_serials=(501, 502, 503), extra_deck=()):
    source = pokemon(main._CINDERACE, 100 + seat * 1000, seat, (490 + seat,))
    opponent = pokemon(main._DURALUDON, 900 + seat * 1000, 1 - seat)
    deck = [card(main._METAL_ENERGY, value, seat) for value in energy_serials]
    deck.extend(extra_deck)
    options = [
        {
            "type": int(OptionType.CARD),
            "area": int(AreaType.DECK),
            "index": index,
            "playerIndex": seat,
        }
        for index in range(len(energy_serials))
    ]
    return {
        "select": {
            "type": int(SelectType.CARD),
            "context": int(SelectContext.ATTACH_TO),
            "minCount": 0,
            "maxCount": min(3, len(energy_serials)),
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": options,
            "deck": deck,
            "contextCard": None,
            "effect": card(main._CINDERACE, source["serial"], seat),
        },
        "logs": [
            {
                "type": int(LogType.ATTACK),
                "playerIndex": seat,
                "cardId": main._CINDERACE,
                "serial": source["serial"],
                "attackId": main._TURBO_FLARE,
            }
        ],
        "current": {
            "turn": 3,
            "turnActionCount": 4,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": (
                [player(seat, source, bench), player(1 - seat, opponent, hand=None)]
                if seat == 0
                else [player(1 - seat, opponent, hand=None), player(seat, source, bench)]
            ),
        },
        "search_begin_input": None,
    }


def add_energy(raw, target_serial, energy_serial):
    seat = raw["current"]["yourIndex"]
    target = next(
        pokemon
        for pokemon in raw["current"]["players"][seat]["bench"]
        if pokemon["serial"] == target_serial
    )
    target["energies"].append(int(main._EnergyType.METAL))
    target["energyCards"].append(card(main._METAL_ENERGY, energy_serial, seat))


def attach_prompt(start, energy_serial, confirmed=None, reverse=False, duplicate=False):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    raw["current"]["turnActionCount"] += 1
    if confirmed is not None:
        previous_energy, target_serial = confirmed
        add_energy(raw, target_serial, previous_energy)
        raw["logs"] = [
            {
                "type": int(LogType.ATTACH),
                "playerIndex": seat,
                "cardId": main._METAL_ENERGY,
                "serial": previous_energy,
                "cardIdTarget": next(
                    pokemon["id"]
                    for pokemon in raw["current"]["players"][seat]["bench"]
                    if pokemon["serial"] == target_serial
                ),
                "serialTarget": target_serial,
            }
        ]
    else:
        raw["logs"] = []
    attached = {
        card["serial"]
        for pokemon in raw["current"]["players"][seat]["bench"]
        for card in pokemon["energyCards"]
    }
    raw["select"]["deck"] = [
        card for card in raw["select"]["deck"] if card["serial"] not in attached
    ]
    options = [
        {
            "type": int(OptionType.CARD),
            "area": int(AreaType.BENCH),
            "index": index,
            "playerIndex": seat,
        }
        for index in range(len(raw["current"]["players"][seat]["bench"]))
    ]
    if duplicate and options:
        options.insert(0, copy.deepcopy(options[-1]))
    if reverse:
        options.reverse()
    raw["select"].update(
        type=int(SelectType.CARD),
        context=int(SelectContext.ATTACH_FROM),
        minCount=1,
        maxCount=1,
        option=options,
        contextCard=card(main._METAL_ENERGY, energy_serial, seat),
    )
    return raw


def rule5_direct_prompt(seat):
    raw = turbo_start(seat, [])
    mine = raw["current"]["players"][seat]
    theirs = raw["current"]["players"][1 - seat]
    mine["active"] = [
        pokemon(main._ARCHALUDON_EX, 300 + seat * 1000, seat, (701, 702, 703))
    ]
    mine["prize"] = [None]
    target = pokemon(23, 400 + seat * 1000, 1 - seat)
    target["hp"] = 100
    theirs["active"] = [target]
    raw["select"].update(
        type=int(SelectType.MAIN),
        context=int(SelectContext.MAIN),
        minCount=1,
        maxCount=1,
        option=[end(), attack(253)],
        deck=None,
        contextCard=None,
        effect=None,
    )
    raw["logs"] = []
    return raw


class Rule7TurboTransactionTests(unittest.TestCase):
    def setUp(self):
        main._setup_ledger = None
        main._materialization_owner = None
        main._rule7_passive_token = None
        main._last_proposal = None
        main._parent._opp_last_attack_id = None
        main._parent._cur_turn_logs.clear()

    def call(self, raw, parent_action):
        with mock.patch.object(main._parent, "agent", return_value=parent_action) as parent:
            action = main.agent(copy.deepcopy(raw))
        self.assertEqual(parent.call_count, 1)
        self.assertEqual(main._last_telemetry["parent_call_count"], 1)
        if main._last_proposal is not None:
            self.assertEqual(
                set(main._last_proposal),
                {"rule_id", "action", "category", "purpose", "exact_proof", "transaction"},
            )
        return action

    def complete_single(self, card_id, initial, seat=0):
        target_serial = 200 + card_id
        existing = tuple(range(600, 600 + initial))
        start = turbo_start(seat, [pokemon(card_id, target_serial, seat, existing)])
        selected = self.call(start, [0, 1, 2])
        deficit = 3 - initial
        self.assertEqual(len(selected), deficit)
        energy_serials = tuple(main._materialization_owner["selected_energy_serials"])
        current = start
        previous = None
        for index, energy_serial in enumerate(energy_serials):
            current = attach_prompt(current, energy_serial, previous)
            self.assertEqual(self.call(current, [0]), [0])
            previous = (energy_serial, target_serial)
            if index + 1 < len(energy_serials):
                self.assertIsNotNone(main._materialization_owner)
            else:
                self.assertEqual(main._last_proposal["rule_id"], main._RULE7_RELEASE_ID)
                proof = main._last_proposal["exact_proof"]
                self.assertTrue(proof["final_target_emitted"])
                self.assertEqual(
                    proof["resolution_status"],
                    "UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY",
                )
                self.assertEqual(
                    proof["owner_release_reason"],
                    "turbo_final_target_emitted_unconfirmed",
                )
                self.assertEqual(proof["expected_post_allocation_counts"][target_serial], 3)
                transaction = main._last_proposal["transaction"]
                self.assertTrue(transaction["final_target_emitted"])
                self.assertEqual(
                    transaction["resolution_status"],
                    "UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY",
                )
                self.assertEqual(transaction["energy_serial"], energy_serial)
                self.assertEqual(transaction["target_serial"], target_serial)
                self.assertEqual(
                    transaction["expected_post_allocation_counts"][target_serial],
                    3,
                )
                self.assertEqual(transaction["allocation_cap"], 3)
                self.assertTrue(transaction["at_most_one_backup"])
                self.assertTrue(transaction["no_third_recipient"])
                self.assertEqual(
                    transaction["owner_release_reason"],
                    "turbo_final_target_emitted_unconfirmed",
                )
                for forbidden in (
                    "ATTACH_CONFIRMED",
                    "transaction_complete",
                    "confirmed",
                    "resolved",
                    "complete",
                ):
                    self.assertNotIn(forbidden, proof)
                    self.assertNotIn(forbidden, transaction)
                self.assertIsNone(main._last_telemetry["owner_after"])
        self.assertIsNone(main._materialization_owner)
        self.assertIsNotNone(main._rule7_passive_token)

    def test_all_three_roles_zero_one_two_to_exact_three_each_seat(self):
        for card_id in (main._ARCHALUDON_EX, main._ARCHALUDON, main._DURALUDON):
            for initial in (0, 1, 2):
                for seat in (0, 1):
                    with self.subTest(card_id=card_id, initial=initial, seat=seat):
                        self.setUp()
                        self.complete_single(card_id, initial, seat=seat)

    def test_primary_then_one_backup_never_third_or_over_ready(self):
        bench = [
            pokemon(main._ARCHALUDON_EX, 210, 0, (601, 602)),
            pokemon(main._ARCHALUDON, 220, 0, (603,)),
            pokemon(main._DURALUDON, 230, 0),
        ]
        start = turbo_start(0, bench)
        self.assertEqual(self.call(start, [0, 1, 2]), [0, 1, 2])
        owner = main._materialization_owner
        self.assertEqual(owner["primary_serial"], 210)
        self.assertEqual(owner["backup_serial"], 220)
        self.assertEqual(list(owner["energy_to_target"].values()), [210, 220, 220])
        self.assertNotIn(230, owner["energy_to_target"].values())

        self.setUp()
        tied = turbo_start(
            0,
            [
                pokemon(main._ARCHALUDON_EX, 210, 0, (601, 602)),
                pokemon(main._ARCHALUDON, 220, 0, (603, 604)),
                pokemon(main._DURALUDON, 230, 0, (605, 606)),
            ],
        )
        self.assertEqual(self.call(tied, [0, 1, 2]), [0, 1])
        self.assertEqual(set(main._materialization_owner["energy_to_target"].values()), {210, 220})

    def test_zero_empty_and_all_ready_retry_then_resolve(self):
        for bench in (
            [],
            [pokemon(main._ARCHALUDON_EX, 210, 0, (601, 602, 603))],
        ):
            with self.subTest(bench=len(bench)):
                self.setUp()
                start = turbo_start(0, bench)
                self.assertEqual(self.call(start, [0, 1, 2]), [])
                self.assertEqual(main._materialization_owner["stage"], "ZERO_EMITTED")
                self.assertEqual(self.call(start, [2, 1, 0]), [])
                resolved = copy.deepcopy(start)
                resolved["select"].update(
                    type=int(SelectType.MAIN),
                    context=int(SelectContext.MAIN),
                    minCount=1,
                    maxCount=1,
                    option=[end()],
                    deck=None,
                    effect=None,
                )
                self.assertEqual(self.call(resolved, [0]), [0])
                self.assertIsNone(main._materialization_owner)

    def test_insufficient_unsupported_special_and_unknown_modifier_return_parent(self):
        insufficient = turbo_start(0, [pokemon(main._DURALUDON, 210, 0)], (501, 502))
        self.assertEqual(self.call(insufficient, [0, 1]), [0, 1])
        self.assertIsNone(main._materialization_owner)

        cases = []
        cases.append(turbo_start(0, [pokemon(main._CINDERACE, 210, 0)]))
        unsupported = turbo_start(0, [pokemon(main._DURALUDON, 210, 0)])
        unsupported["select"]["deck"][0] = card(9, 501, 0)
        cases.append(unsupported)
        modified = turbo_start(
            0,
            [pokemon(main._DURALUDON, 210, 0, tools=(card(1152, 700, 0),))],
        )
        cases.append(modified)
        for raw in cases:
            with self.subTest(case=len(cases)):
                self.setUp()
                self.assertEqual(self.call(raw, [0, 1, 2]), [0, 1, 2])
                self.assertIsNone(main._materialization_owner)

    def test_evolution_cards_do_not_change_duraludon_allocation(self):
        base = turbo_start(0, [pokemon(main._DURALUDON, 210, 0, (601,))])
        with_evolution = turbo_start(
            0,
            [pokemon(main._DURALUDON, 210, 0, (601,))],
            extra_deck=(card(main._ARCHALUDON_EX, 800, 0), card(main._ARCHALUDON, 801, 0)),
        )
        self.assertEqual(self.call(base, [0, 1, 2]), [0, 1])
        mapping = dict(main._materialization_owner["energy_to_target"])
        self.setUp()
        self.assertEqual(self.call(with_evolution, [0, 1, 2]), [0, 1])
        self.assertEqual(main._materialization_owner["energy_to_target"], mapping)

    def test_energy_and_target_permutation_retry_rebinds_lowest_duplicate(self):
        start = turbo_start(0, [pokemon(main._DURALUDON, 210, 0)])
        self.assertEqual(self.call(start, [0, 1, 2]), [0, 1, 2])
        permuted = copy.deepcopy(start)
        permuted["select"]["option"].reverse()
        self.assertEqual(self.call(permuted, [0, 1, 2]), [2, 1, 0])
        self.assertTrue(main._last_telemetry["option_permuted"])

        first = attach_prompt(start, 503, reverse=True, duplicate=True)
        self.assertEqual(self.call(first, [0]), [0])
        retry = copy.deepcopy(first)
        retry["select"]["option"].reverse()
        self.assertEqual(self.call(retry, [0]), [0])

    def test_final_target_release_retry_permutation_and_rule5_same_callback(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                self.setUp()
                start = turbo_start(
                    seat,
                    [
                        pokemon(main._ARCHALUDON_EX, 210 + seat * 1000, seat, (601, 602, 603)),
                        pokemon(main._DURALUDON, 220 + seat * 1000, seat, (604, 605)),
                    ],
                )
                self.assertEqual(self.call(start, [0, 1, 2]), [0])
                final = attach_prompt(start, 501)
                self.assertEqual(self.call(final, [0]), [1])
                self.assertIsNone(main._materialization_owner)
                self.assertIsNotNone(main._rule7_passive_token)

                retry = copy.deepcopy(final)
                retry["select"]["option"].reverse()
                self.assertEqual(self.call(retry, [0]), [0])
                self.assertTrue(main._last_telemetry["duplicate_retry"])
                self.assertTrue(main._last_telemetry["option_permuted"])
                self.assertIsNone(main._materialization_owner)

                direct = rule5_direct_prompt(seat)
                self.assertEqual(self.call(direct, [0]), [1])
                self.assertEqual(main._last_proposal["rule_id"], main._RULE5_ID)
                self.assertIsNone(main._rule7_passive_token)

    def test_confirmation_wrong_source_target_loss_turn_result_clear_to_parent(self):
        start = turbo_start(0, [pokemon(main._DURALUDON, 210, 0)])
        wrong_source = copy.deepcopy(start)
        wrong_source["select"]["effect"] = card(main._ARCHALUDON_EX, 999, 0)
        self.assertEqual(self.call(wrong_source, [2]), [2])

        for mutation in ("no_confirmation", "target_loss", "turn", "result"):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.assertEqual(self.call(start, [0, 1, 2]), [0, 1, 2])
                first = attach_prompt(start, 501)
                self.assertEqual(self.call(first, [0]), [0])
                next_prompt = attach_prompt(first, 502)
                if mutation == "target_loss":
                    next_prompt["current"]["players"][0]["bench"] = []
                elif mutation == "turn":
                    next_prompt["current"]["turn"] += 1
                elif mutation == "result":
                    next_prompt["current"]["result"] = 0
                self.assertEqual(self.call(next_prompt, [0]), [0])
                self.assertIsNone(main._materialization_owner)


if __name__ == "__main__":
    unittest.main()
