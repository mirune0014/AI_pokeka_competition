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
    / "archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1"
)
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import LogType, OptionType, SelectContext, SelectType


REPLY_POKEMON = 121
REPLY_ATTACK = 153
GRASS_ENERGY = 1


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, hp=None, energy=()):
    data = main._parent.CARD_DB[card_id]
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp if hp is None else hp,
        "maxHp": data.hp,
        "appearThisTurn": False,
        "energies": [main._parent.CARD_DB[energy_id].energyType for energy_id, _ in energy],
        "energyCards": [card(energy_id, energy_serial, seat) for energy_id, energy_serial in energy],
        "tools": [],
        "preEvolution": [],
    }


def player(seat, hand, active, bench=(), *, prizes=4, status=False):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": [],
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


def play(index, seat):
    return {"type": int(OptionType.PLAY), "index": index, "playerIndex": seat}


def end():
    return {"type": int(OptionType.END)}


def observation(seat, ours, theirs, options, *, action_count=3, stadium=(), logs=()):
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
        "logs": list(logs),
        "current": {
            "turn": 8,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": bool(stadium),
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": list(stadium),
            "looking": None,
            "players": [ours, theirs] if seat == 0 else [theirs, ours],
        },
        "search_begin_input": None,
    }


def start_state(seat, attacker_id, attack_id, *, attacker_hp=60, force_promotion=False):
    fml_low = card(main._FULL_METAL_LAB, 100 + seat * 1000, seat)
    fml_high = card(main._FULL_METAL_LAB, 101 + seat * 1000, seat)
    cost_count = len(main._EXPECTED_ATTACKS[attack_id][3])
    attacker = pokemon(
        attacker_id,
        200 + seat * 1000,
        seat,
        hp=attacker_hp,
        energy=tuple(
            (main._METAL_ENERGY, 300 + seat * 1000 + index)
            for index in range(cost_count)
        ),
    )
    active_reply = pokemon(
        REPLY_POKEMON,
        400 + seat * 1000,
        1 - seat,
        hp=200 if force_promotion else None,
        energy=() if force_promotion else tuple(
            (GRASS_ENERGY, 500 + seat * 1000 + index) for index in range(1)
        ),
    )
    bench = ()
    if force_promotion:
        bench = (
            pokemon(
                REPLY_POKEMON,
                401 + seat * 1000,
                1 - seat,
                energy=tuple(
                    (GRASS_ENERGY, 500 + seat * 1000 + index) for index in range(1)
                ),
            ),
        )
    ours = player(seat, [fml_high, fml_low], attacker)
    theirs = player(1 - seat, None, active_reply, bench)
    raw = observation(
        seat,
        ours,
        theirs,
        [attack(attack_id), play(0, seat), play(1, seat), end()],
    )
    return raw, fml_low, attacker


def receipt(start, fml, attack_id, *, reverse=False):
    raw = copy.deepcopy(start)
    seat = raw["current"]["yourIndex"]
    ours = raw["current"]["players"][seat]
    ours["hand"] = [value for value in ours["hand"] if value["serial"] != fml["serial"]]
    ours["handCount"] -= 1
    raw["current"]["stadium"] = [fml]
    raw["current"]["stadiumPlayed"] = True
    raw["current"]["turnActionCount"] += 1
    raw["select"]["option"] = [attack(attack_id), end()]
    if reverse:
        raw["select"]["option"].reverse()
    raw["logs"] = [{
        "type": int(LogType.PLAY),
        "playerIndex": seat,
        "cardId": main._FULL_METAL_LAB,
        "serial": fml["serial"],
    }]
    return raw


class Rule10FmlExchangeTests(unittest.TestCase):
    def setUp(self):
        main._setup_ledger = None
        main._materialization_owner = None
        main._last_proposal = None
        main._rule10_activity.update(
            starts=0,
            completions=0,
            aborts=0,
            faults=0,
            last_event="not_started",
            last_fault=None,
        )
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

    def test_all_rule5_attack_paths_both_seats_and_forced_promotion(self):
        cases = (
            (main._DURALUDON, 223, False),
            (main._DURALUDON, 224, False),
            (main._ARCHALUDON_EX, 253, True),
            (main._ARCHALUDON, 1212, False),
        )
        for seat in (0, 1):
            for attacker_id, attack_id, promoted in cases:
                with self.subTest(seat=seat, attack_id=attack_id):
                    self.setUp()
                    raw, fml, _attacker = start_state(
                        seat, attacker_id, attack_id, force_promotion=promoted
                    )
                    self.assertEqual(self.call(raw, [0]), [2])
                    proposal = main._last_proposal
                    self.assertEqual(proposal["rule_id"], main._RULE10_ID)
                    self.assertEqual(
                        proposal["category"], "DETERMINISTIC_SAME_ATTACK_PRESERVATION"
                    )
                    self.assertEqual(
                        proposal["purpose"],
                        "EXACT_FML_PUBLIC_RETURN_KO_OR_BOARDOUT_PREVENTION",
                    )
                    self.assertEqual(
                        proposal["exact_proof"]["keep_world"]["damage"],
                        proposal["exact_proof"]["play_fml_world"]["damage"],
                    )
                    post = receipt(raw, fml, attack_id, reverse=True)
                    self.assertEqual(self.call(post, [1]), [1])
                    self.assertEqual(main._materialization_owner["stage"], "ATTACK_EMITTED")

    def test_full_lifecycle_retries_option_reversal_completion_and_telemetry(self):
        raw, fml, attacker = start_state(0, main._ARCHALUDON, 1212)
        self.assertEqual(self.call(raw, [0]), [2])
        retry = copy.deepcopy(raw)
        retry["select"]["option"].reverse()
        self.assertEqual(self.call(retry, [3]), [1])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        post = receipt(raw, fml, 1212, reverse=True)
        self.assertEqual(self.call(post, [1]), [1])
        attack_retry = copy.deepcopy(post)
        attack_retry["select"]["option"].reverse()
        self.assertEqual(self.call(attack_retry, [0]), [0])
        self.assertTrue(main._last_telemetry["duplicate_retry"])

        completed = copy.deepcopy(post)
        completed["select"].update(
            type=int(SelectType.CARD),
            context=int(SelectContext.TO_HAND),
            option=[],
        )
        completed["logs"] = [{
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": attacker["id"],
            "serial": attacker["serial"],
            "attackId": 1212,
        }]
        self.assertEqual(self.call(completed, []), [])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._rule10_activity["starts"], 1)
        self.assertEqual(main._rule10_activity["completions"], 1)
        self.assertEqual(main._rule10_activity["aborts"], 0)
        self.assertEqual(main._rule10_activity["faults"], 0)

    def test_weakness_resistance_then_fml_order(self):
        reply_type = main._parent.CARD_DB[REPLY_POKEMON].energyType
        with mock.patch.object(main._parent.CARD_DB[main._ARCHALUDON], "weakness", reply_type):
            raw, _fml, _attacker = start_state(
                0, main._ARCHALUDON, 1212, attacker_hp=120
            )
            self.assertEqual(self.call(raw, [0]), [2])
            proof = main._last_proposal["exact_proof"]
            self.assertEqual(proof["keep_replies"][0]["damage"], 140)
            self.assertEqual(proof["play_fml_replies"][0]["damage"], 110)

        self.setUp()
        with mock.patch.object(main._parent.CARD_DB[main._ARCHALUDON], "resistance", reply_type):
            raw, _fml, _attacker = start_state(
                0, main._ARCHALUDON, 1212, attacker_hp=30
            )
            self.assertEqual(self.call(raw, [0]), [2])
            proof = main._last_proposal["exact_proof"]
            self.assertEqual(proof["keep_replies"][0]["damage"], 40)
            self.assertEqual(proof["play_fml_replies"][0]["damage"], 10)

    def test_physical_copy_determinism_duplicate_binding_and_serial_remap_fault(self):
        raw, fml, _attacker = start_state(0, main._ARCHALUDON, 1212)
        self.assertEqual(self.call(raw, [0]), [2])
        self.assertEqual(main._materialization_owner["fml_ref"][1], fml["serial"])

        self.setUp()
        duplicate, _fml, _attacker = start_state(0, main._ARCHALUDON, 1212)
        duplicate["select"]["option"].insert(2, play(1, 0))
        self.assertEqual(self.call(duplicate, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        raw, fml, _attacker = start_state(0, main._ARCHALUDON, 1212)
        self.assertEqual(self.call(raw, [0]), [2])
        remapped = receipt(raw, fml, 1212)
        remapped["current"]["stadium"][0]["serial"] += 99
        self.assertEqual(self.call(remapped, [0]), [0])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._rule10_activity["aborts"], 1)
        self.assertEqual(main._rule10_activity["faults"], 1)

    def test_attack_receipt_clears_before_identical_prompt_retry(self):
        raw, fml, attacker = start_state(0, main._ARCHALUDON, 1212)
        self.assertEqual(self.call(raw, [0]), [2])
        post = receipt(raw, fml, 1212)
        self.assertEqual(self.call(post, [0]), [0])
        same_prompt_with_receipt = copy.deepcopy(post)
        same_prompt_with_receipt["logs"] = [{
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": attacker["id"],
            "serial": attacker["serial"],
            "attackId": 1212,
        }]
        self.assertEqual(self.call(same_prompt_with_receipt, [1]), [1])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._last_telemetry["rejection_reason"], "rule10_attack_dispatched")
        self.assertEqual(main._rule10_activity["completions"], 1)

    def test_required_negative_boundaries_fall_back_exactly(self):
        base, _fml, _attacker = start_state(0, main._ARCHALUDON, 1212)
        negatives = []

        no_threshold = copy.deepcopy(base)
        no_threshold["current"]["players"][0]["active"][0]["hp"] = 100
        negatives.append(no_threshold)

        status = copy.deepcopy(base)
        status["current"]["players"][1]["poisoned"] = True
        negatives.append(status)

        tool = copy.deepcopy(base)
        tool["current"]["players"][1]["active"][0]["tools"] = [card(1159, 990, 1)]
        negatives.append(tool)

        special = copy.deepcopy(base)
        special["current"]["players"][1]["active"][0]["energyCards"][0] = card(1152, 500, 1)
        negatives.append(special)

        occupied = copy.deepcopy(base)
        occupied["current"]["stadium"] = [card(main._FULL_METAL_LAB, 900, 1)]
        occupied["current"]["stadiumPlayed"] = True
        negatives.append(occupied)

        multiple_attacks = copy.deepcopy(base)
        multiple_attacks["select"]["option"].insert(1, attack(223))
        negatives.append(multiple_attacks)

        unknown_reply = copy.deepcopy(base)
        unknown_reply["current"]["players"][1]["active"] = [
            pokemon(348, 900, 1, energy=((GRASS_ENERGY, 910),))
        ]
        negatives.append(unknown_reply)

        for index, raw in enumerate(negatives):
            with self.subTest(index=index):
                self.setUp()
                self.assertEqual(self.call(raw, [0]), [0])
                self.assertIsNone(main._materialization_owner)
                self.assertIsNone(main._last_proposal)

    def test_terminal_precedence_promotion_ambiguity_and_post_spend_abort_fault(self):
        terminal, _fml, _attacker = start_state(
            0, main._ARCHALUDON_EX, 253, force_promotion=True
        )
        terminal["current"]["players"][0]["prize"] = [None]
        self.assertEqual(self.call(terminal, [0]), [0])
        self.assertEqual(main._last_proposal["purpose"], "DIRECT_EXACT_CURRENT_WIN")

        self.setUp()
        ambiguous, _fml, _attacker = start_state(
            0, main._ARCHALUDON_EX, 253, force_promotion=True
        )
        ambiguous["current"]["players"][1]["bench"].append(
            pokemon(
                REPLY_POKEMON,
                999,
                1,
                energy=tuple((GRASS_ENERGY, 920 + index) for index in range(1)),
            )
        )
        self.assertEqual(self.call(ambiguous, [0]), [0])
        self.assertIsNone(main._last_proposal)

        self.setUp()
        raw, fml, _attacker = start_state(0, main._ARCHALUDON, 1212)
        self.assertEqual(self.call(raw, [0]), [2])
        post = receipt(raw, fml, 1212)
        self.assertEqual(self.call(post, [0]), [0])
        stale = copy.deepcopy(post)
        stale["current"]["turn"] += 1
        stale["logs"] = []
        self.assertEqual(self.call(stale, [1]), [1])
        self.assertIsNone(main._materialization_owner)
        self.assertEqual(main._rule10_activity["aborts"], 1)
        self.assertEqual(main._rule10_activity["faults"], 1)
        self.assertEqual(
            main._last_telemetry["rejection_reason"], "rule10_post_spend_attack_abort"
        )


if __name__ == "__main__":
    unittest.main()
