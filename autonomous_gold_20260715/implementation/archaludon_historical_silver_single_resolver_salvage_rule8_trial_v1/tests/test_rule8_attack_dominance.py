from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


AUTO = Path(__file__).resolve().parents[3]
CANDIDATE = (
    AUTO
    / "candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1"
)
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import OptionType, SelectContext, SelectType


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
        "energies": [int(main._EnergyType.METAL)] * len(energy_serials),
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


def attack(attack_id, **extra):
    option = {"type": int(OptionType.ATTACK), "attackId": attack_id}
    option.update(extra)
    return option


def end():
    return {"type": int(OptionType.END)}


def observation(seat, ours, theirs, options, *, stadium=(), effect=None):
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
            "effect": effect,
        },
        "logs": [],
        "current": {
            "turn": 8,
            "turnActionCount": 3,
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


def dominance_state(
    seat=0,
    *,
    attacker_hp=None,
    target_id=24,
    target_hp=None,
    prizes=4,
    options=None,
):
    if options is None:
        options = [end(), attack(223), attack(224)]
    base = 1000 * seat
    ours = player(
        seat,
        [],
        pokemon(
            main._DURALUDON,
            10 + base,
            seat,
            hp=attacker_hp,
            energy_serials=(31 + base, 32 + base, 33 + base),
        ),
        prizes=prizes,
    )
    theirs = player(
        1 - seat,
        None,
        pokemon(target_id, 20 + base, 1 - seat, hp=target_hp),
    )
    return observation(seat, ours, theirs, options)


def option_position(raw, attack_id):
    matches = [
        index
        for index, option in enumerate(raw["select"]["option"])
        if option.get("type") == int(OptionType.ATTACK)
        and option.get("attackId") == attack_id
    ]
    if len(matches) != 1:
        raise AssertionError((attack_id, matches))
    return matches[0]


def selected_attack(raw, action):
    if not isinstance(action, list) or len(action) != 1:
        return None
    return raw["select"]["option"][action[0]].get("attackId")


class Rule8AttackDominanceTests(unittest.TestCase):
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
                {
                    "rule_id",
                    "action",
                    "category",
                    "purpose",
                    "exact_proof",
                    "transaction",
                },
            )
        return result

    def assert_parent(self, raw, parent_action):
        result = self.call(raw, parent_action)
        self.assertEqual(result, parent_action)
        return result

    def test_positive_both_seats_reverse_order_and_identical_retry(self):
        cases = (
            ("undamaged_non_ko", None, 24, None, 30, 80, 0, 0),
            ("damaged_non_ko", 100, 24, None, 30, 110, 0, 0),
            ("exact_ko", None, 22, 80, 30, 80, 0, 1),
            ("higher_prize", None, 99, 80, 30, 80, 0, 2),
        )
        for seat in (0, 1):
            for name, attacker_hp, target_id, target_hp, left, right, left_take, right_take in cases:
                for reverse in (False, True):
                    with self.subTest(seat=seat, case=name, reverse=reverse):
                        self.setUp()
                        raw = dominance_state(
                            seat,
                            attacker_hp=attacker_hp,
                            target_id=target_id,
                            target_hp=target_hp,
                        )
                        if reverse:
                            raw["select"]["option"].reverse()
                        parent_action = [option_position(raw, 223)]
                        first = self.call(raw, parent_action)
                        self.assertEqual(selected_attack(raw, first), 224)
                        self.assertIsNone(main._materialization_owner)
                        proposal = main._last_proposal
                        self.assertEqual(proposal["rule_id"], main._RULE8_ID)
                        self.assertIsNone(proposal["transaction"])
                        outcomes = proposal["exact_proof"]["outcomes"]
                        self.assertEqual(outcomes["parent"]["final_damage"], left)
                        self.assertEqual(outcomes["candidate"]["final_damage"], right)
                        self.assertEqual(outcomes["parent"]["prizes_taken"], left_take)
                        self.assertEqual(outcomes["candidate"]["prizes_taken"], right_take)
                        self.assertEqual(proposal["exact_proof"]["parent_semantic"][-1], 223)
                        self.assertEqual(proposal["exact_proof"]["selected_semantic"][-1], 224)
                        retry = self.call(raw, parent_action)
                        self.assertEqual(retry, first)
                        self.assertIsNone(main._materialization_owner)

    def test_parent_active_presence_duplicate_and_binding_negatives(self):
        base = dominance_state()
        cases = []

        parent_raging = copy.deepcopy(base)
        cases.append(("parent_not_hammer", parent_raging, [option_position(parent_raging, 224)]))

        wrong_active = copy.deepcopy(base)
        wrong_active["current"]["players"][0]["active"] = [
            pokemon(main._ARCHALUDON_EX, 10, 0, energy_serials=(31, 32, 33))
        ]
        cases.append(("wrong_active", wrong_active, [option_position(wrong_active, 223)]))

        absent = dominance_state(options=[end(), attack(223)])
        cases.append(("raging_absent", absent, [option_position(absent, 223)]))

        duplicate_hammer = dominance_state(
            options=[end(), attack(223), attack(223), attack(224)]
        )
        cases.append(("duplicate_hammer", duplicate_hammer, [1]))

        duplicate_raging = dominance_state(
            options=[end(), attack(223), attack(224), attack(224)]
        )
        cases.append(("duplicate_raging", duplicate_raging, [1]))

        bound_elsewhere = dominance_state(
            options=[
                end(),
                attack(223),
                attack(224, area=5, index=0, playerIndex=0),
            ]
        )
        bound_elsewhere["current"]["players"][0]["bench"] = [
            pokemon(main._DURALUDON, 40, 0)
        ]
        cases.append(("different_active_binding", bound_elsewhere, [1]))

        duplicate_serial = copy.deepcopy(base)
        duplicate_serial["current"]["players"][1]["active"][0]["serial"] = 10
        cases.append(("duplicate_serial", duplicate_serial, [1]))

        for name, raw, parent_action in cases:
            with self.subTest(case=name):
                self.setUp()
                self.assert_parent(raw, parent_action)
                self.assertNotEqual(
                    getattr(main, "_last_proposal", None) and main._last_proposal.get("rule_id"),
                    main._RULE8_ID,
                )

    def test_public_metadata_modifier_energy_and_effect_negatives(self):
        raw = dominance_state()
        parent_action = [option_position(raw, 223)]

        active_tool = copy.deepcopy(raw)
        active_tool["current"]["players"][0]["active"][0]["tools"] = [
            card(1159, 70, 0)
        ]
        unsupported_stadium = copy.deepcopy(raw)
        unsupported_stadium["current"]["stadium"] = [card(1242, 71, 0)]
        unsupported_stadium["current"]["stadiumPlayed"] = True
        status = copy.deepcopy(raw)
        status["current"]["players"][1]["poisoned"] = True
        mismatched_energy = copy.deepcopy(raw)
        active = mismatched_energy["current"]["players"][0]["active"][0]
        active["energies"][2] = int(main._EnergyType.COLORLESS)
        active["energyCards"][2] = card(9, 33, 0)

        for name, candidate in (
            ("tool", active_tool),
            ("stadium", unsupported_stadium),
            ("status_modifier", status),
            ("energy", mismatched_energy),
        ):
            with self.subTest(case=name):
                self.setUp()
                self.assert_parent(candidate, parent_action)

        with mock.patch.object(main._parent.CARD_DB[24], "weakness", "UNKNOWN"):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(main._parent.CARD_DB[24], "resistance", 999):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(main._parent.ALL_ATTACKS[224], "damage", 81):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(
            main._parent.ALL_ATTACKS[224],
            "text",
            "This attack also does 20 damage to itself.",
        ):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(
            main._parent.ALL_ATTACKS[223],
            "text",
            "Discard an Energy from this Pokemon.",
        ):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(
            main._parent.ALL_ATTACKS[224],
            "text",
            "The Defending Pokemon is now Confused.",
        ):
            self.assert_parent(raw, parent_action)
        with mock.patch.object(main, "_rule8_zero_consequences_exact", return_value=None):
            self.assert_parent(raw, parent_action)

    def test_owner_terminal_malformed_and_equal_outcome_fail_closed(self):
        raw = dominance_state()
        parent_action = [option_position(raw, 223)]

        main._materialization_owner = {
            "owner": main._RULE5_ID,
            "stage": "STALE",
        }
        self.assert_parent(raw, parent_action)
        self.assertIsNone(main._materialization_owner)

        self.setUp()
        terminal = dominance_state(target_id=160, target_hp=30, prizes=1)
        terminal_parent = [option_position(terminal, 223)]
        self.assert_parent(terminal, terminal_parent)
        self.assertEqual(main._last_proposal["rule_id"], main._RULE5_ID)
        self.assertEqual(main._last_proposal["purpose"], "DIRECT_EXACT_CURRENT_WIN")

        self.setUp()
        malformed = copy.deepcopy(raw)
        malformed["select"]["effect"] = card(1182, 99, 0)
        self.assert_parent(malformed, parent_action)

        self.assertIsNone(
            main._rule8_pareto_proof(
                (80, 1, 0),
                (80, 1, 0),
                SimpleNamespace(hp=200),
            )
        )


if __name__ == "__main__":
    unittest.main()
