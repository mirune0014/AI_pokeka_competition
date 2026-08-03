from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest
from unittest import mock


AUTO = Path(__file__).resolve().parents[3]
CANDIDATE = AUTO / "candidates" / "archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1"
sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, OptionType, SelectContext, SelectType


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, hp, max_hp, energy_ids=(), pre=(), tools=()):
    energy_types = []
    energies = []
    for offset, energy_id in enumerate(energy_ids):
        energy_types.append(int(main._parent.CARD_DB[energy_id].energyType))
        energies.append(card(energy_id, 400 + serial * 10 + offset, seat))
    return {
        "id": card_id,
        "serial": serial,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": energy_types,
        "energyCards": energies,
        "tools": list(tools),
        "preEvolution": list(pre),
    }


def player(seat, hand, active, bench=(), *, discard=(), prizes=4, deck_count=40,
           hand_count=None, statuses=None):
    status = statuses or (False, False, False, False, False)
    return {
        "active": list(active),
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": deck_count,
        "discard": list(discard),
        "prize": [None] * prizes,
        "handCount": len(hand) if hand_count is None and hand is not None else hand_count,
        "hand": hand,
        "poisoned": status[0],
        "burned": status[1],
        "asleep": status[2],
        "paralyzed": status[3],
        "confused": status[4],
    }


def attack_option(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def play_option(hand_index, seat):
    return {"type": int(OptionType.PLAY), "index": hand_index, "playerIndex": seat}


def evolve_option(hand_index, seat):
    return {
        "type": int(OptionType.EVOLVE),
        "area": int(AreaType.HAND),
        "index": hand_index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.ACTIVE),
        "inPlayIndex": 0,
    }


def card_option(area, index, seat):
    return {
        "type": int(OptionType.CARD),
        "area": int(area),
        "index": index,
        "playerIndex": seat,
    }


def obs(seat, ours, theirs, options, *, context=SelectContext.MAIN,
        turn=8, action_count=3, effect=None, stadium=(), min_count=1, max_count=1):
    players = [ours, theirs] if seat == 0 else [theirs, ours]
    return {
        "select": {
            "type": int(SelectType.MAIN if context == SelectContext.MAIN else SelectType.CARD),
            "context": int(context),
            "minCount": min_count,
            "maxCount": max_count,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": list(options),
            "deck": None,
            "contextCard": None,
            "effect": effect,
        },
        "logs": [],
        "current": {
            "turn": turn,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": list(stadium),
            "looking": None,
            "players": players,
        },
        "search_begin_input": None,
    }


class Rule2Tests(unittest.TestCase):
    def setUp(self):
        main._setup_ledger = None
        main._continuity_owner = None
        main._last_proposal = None

    def invoke(self, raw, parent_action):
        calls = []
        with mock.patch.object(main._parent, "agent", side_effect=lambda value: calls.append(value) or parent_action):
            action = main.agent(raw)
        self.assertEqual(len(calls), 1)
        self.assertEqual(main._last_telemetry["parent_call_count"], 1)
        if main._last_proposal is not None:
            self.assertEqual(
                set(main._last_proposal),
                {"rule_id", "action", "category", "purpose", "exact_proof", "transaction"},
            )
        return action

    def metal_reply_state(self, seat, hand, *, own_bench=(), discard=(),
                          own_active=None, opponent_active=None, opp_prizes=4,
                          opp_deck=40, opp_hand=3, statuses=None):
        own_active = own_active or pokemon(666, 10, seat, hp=160, max_hp=160, energy_ids=(8,))
        opponent_active = opponent_active or pokemon(190, 90, 1 - seat, hp=300, max_hp=300, energy_ids=(8, 8, 8))
        ours = player(seat, hand, [own_active], own_bench, discard=discard, prizes=4, statuses=statuses)
        theirs = player(1 - seat, None, [opponent_active], (), prizes=opp_prizes,
                        deck_count=opp_deck, hand_count=opp_hand)
        return ours, theirs

    def test_direct_basic_both_seats_reverse_and_retry_then_attack(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                basic = card(169, 21, seat)
                ours, theirs = self.metal_reply_state(seat, [basic])
                raw = obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)])
                action = self.invoke(raw, [0])
                self.assertEqual(action, [1])
                self.assertEqual(main._last_proposal["purpose"], "DIRECT_BASIC_BEFORE_NONTERMINAL_ATTACK")

                retry = obs(seat, ours, theirs, [play_option(0, seat), attack_option(965)])
                action = self.invoke(retry, [1])
                self.assertEqual(action, [0])
                self.assertTrue(main._last_telemetry["duplicate_retry"])

                ours2, theirs2 = self.metal_reply_state(seat, [], own_bench=[
                    pokemon(169, 21, seat, hp=130, max_hp=130)
                ])
                ready = obs(seat, ours2, theirs2, [attack_option(965)], action_count=4)
                action = self.invoke(ready, [0])
                self.assertEqual(action, [0])
                self.assertIsNone(main._continuity_owner)
                self.assertEqual(main._last_proposal["transaction"]["stage"], "CLEAR")

    def test_night_stretcher_full_route_both_seats(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                stretcher = card(1097, 31, seat)
                target = card(57, 41, seat)
                spare_energy = card(8, 42, seat)
                ours, theirs = self.metal_reply_state(
                    seat, [stretcher], discard=[target, spare_energy]
                )
                start = obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)])
                self.assertEqual(self.invoke(start, [0]), [1])
                self.assertEqual(main._last_proposal["purpose"], "NIGHT_STRETCHER_BASIC_CONTINUITY")

                ours1, theirs1 = self.metal_reply_state(
                    seat, [], discard=[target, spare_energy, stretcher]
                )
                recovery = obs(
                    seat, ours1, theirs1,
                    [card_option(AreaType.DISCARD, 0, seat), card_option(AreaType.DISCARD, 1, seat)],
                    context=SelectContext.TO_HAND,
                    action_count=4,
                    effect=stretcher,
                )
                self.assertEqual(self.invoke(recovery, [0]), [0])
                recovery_retry = obs(
                    seat, ours1, theirs1,
                    [card_option(AreaType.DISCARD, 1, seat), card_option(AreaType.DISCARD, 0, seat)],
                    context=SelectContext.TO_HAND,
                    action_count=4,
                    effect=stretcher,
                )
                self.assertEqual(self.invoke(recovery_retry, [1]), [1])

                ours2, theirs2 = self.metal_reply_state(
                    seat, [target], discard=[spare_energy, stretcher]
                )
                play = obs(seat, ours2, theirs2, [attack_option(965), play_option(0, seat)], action_count=5)
                self.assertEqual(self.invoke(play, [0]), [1])
                play_retry = obs(
                    seat, ours2, theirs2,
                    [play_option(0, seat), attack_option(965)], action_count=5,
                )
                self.assertEqual(self.invoke(play_retry, [1]), [0])

                ours3, theirs3 = self.metal_reply_state(
                    seat, [], discard=[spare_energy, stretcher],
                    own_bench=[pokemon(57, 41, seat, hp=100, max_hp=100)],
                )
                attack = obs(seat, ours3, theirs3, [attack_option(965)], action_count=6)
                self.assertEqual(self.invoke(attack, [0]), [0])
                self.assertIsNone(main._continuity_owner)

    def test_nonex_evolution_survival_route(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                evolution = card(840, 20, seat)
                active = pokemon(169, 10, seat, hp=50, max_hp=130, energy_ids=(8, 8, 8))
                opponent = pokemon(169, 90, 1 - seat, hp=130, max_hp=130, energy_ids=(8, 8, 8))
                ours, theirs = self.metal_reply_state(
                    seat, [evolution], own_active=active, opponent_active=opponent
                )
                start = obs(seat, ours, theirs, [attack_option(223), evolve_option(0, seat)])
                self.assertEqual(self.invoke(start, [0]), [1])
                self.assertEqual(main._last_proposal["purpose"], "NONEX_EVOLUTION_SURVIVAL_CONTINUITY")
                start_retry = obs(
                    seat, ours, theirs, [evolve_option(0, seat), attack_option(223)]
                )
                self.assertEqual(self.invoke(start_retry, [1]), [0])

                evolved = pokemon(
                    840, 20, seat, hp=100, max_hp=180, energy_ids=(8, 8, 8),
                    pre=[card(169, 10, seat)],
                )
                ours2, theirs2 = self.metal_reply_state(
                    seat, [], own_active=evolved, opponent_active=opponent
                )
                ready = obs(seat, ours2, theirs2, [attack_option(1212)], action_count=4)
                self.assertEqual(self.invoke(ready, [0]), [0])
                self.assertIsNone(main._continuity_owner)

    def test_powerful_hand_reply_certificate(self):
        seat = 0
        basic = card(169, 21, seat)
        own = pokemon(666, 10, seat, hp=160, max_hp=160, energy_ids=(8,))
        alakazam = pokemon(743, 90, 1, hp=140, max_hp=140, energy_ids=(5,))
        ours, theirs = self.metal_reply_state(
            seat, [basic], own_active=own, opponent_active=alakazam, opp_hand=8
        )
        raw = obs(seat, ours, theirs, [play_option(0, seat), attack_option(965)])
        self.assertEqual(self.invoke(raw, [1]), [0])
        self.assertEqual(main._last_proposal["exact_proof"]["reply_attack_id"], 1072)
        self.assertEqual(main._last_proposal["exact_proof"]["reply_damage_lower"], 160)

    def test_negative_boundaries_return_exact_parent(self):
        seat = 0
        basic = card(169, 21, seat)
        cases = []

        ours, theirs = self.metal_reply_state(seat, [basic])
        cases.append((obs(seat, ours, theirs, [play_option(0, seat), attack_option(965)]), [0], "parent nonattack"))

        ours, theirs = self.metal_reply_state(
            seat, [basic], opponent_active=pokemon(190, 90, 1, hp=40, max_hp=300, energy_ids=(8, 8, 8))
        )
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "parent KO"))

        ours, theirs = self.metal_reply_state(
            seat, [basic], own_bench=[pokemon(57, 30, seat, hp=100, max_hp=100)]
        )
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "bench nonempty"))

        ours, theirs = self.metal_reply_state(
            seat, [basic], opponent_active=pokemon(190, 90, 1, hp=300, max_hp=300, energy_ids=(8, 8))
        )
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "reply unpaid"))

        ours, theirs = self.metal_reply_state(seat, [basic], opp_prizes=1)
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "reply final prizes"))

        tool = card(1159, 55, seat)
        own = pokemon(666, 10, seat, hp=260, max_hp=260, energy_ids=(8,), tools=[tool])
        ours, theirs = self.metal_reply_state(seat, [basic], own_active=own)
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "tool modifier"))

        ours, theirs = self.metal_reply_state(seat, [basic], statuses=(False, False, False, False, True))
        cases.append((obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)]), [0], "status"))

        ours, theirs = self.metal_reply_state(seat, [basic])
        cases.append((obs(seat, ours, theirs, [attack_option(99999), play_option(0, seat)]), [0], "unregistered"))

        for raw, parent_action, label in cases:
            with self.subTest(label=label):
                main._continuity_owner = None
                returned = self.invoke(raw, parent_action)
                self.assertIs(returned, parent_action)
                self.assertIsNone(main._last_proposal)

    def test_coated_basic_reply_and_unknown_stadium_fail_closed(self):
        seat = 0
        basic = card(57, 21, seat)
        own = pokemon(840, 10, seat, hp=50, max_hp=180, energy_ids=(8, 8, 8))
        opposing_basic = pokemon(169, 90, 1, hp=130, max_hp=130, energy_ids=(8, 8, 8))
        ours, theirs = self.metal_reply_state(
            seat, [basic], own_active=own, opponent_active=opposing_basic
        )
        raw = obs(seat, ours, theirs, [attack_option(1212), play_option(0, seat)])
        parent = [0]
        self.assertIs(self.invoke(raw, parent), parent)

        ours, theirs = self.metal_reply_state(seat, [basic])
        raw = obs(
            seat, ours, theirs, [attack_option(965), play_option(0, seat)],
            stadium=[card(1152, 99, 0)],
        )
        parent = [0]
        self.assertIs(self.invoke(raw, parent), parent)

    def test_multiple_routes_and_recovery_targets_reject(self):
        seat = 0
        hand = [card(169, 21, seat), card(57, 22, seat)]
        ours, theirs = self.metal_reply_state(seat, hand)
        raw = obs(seat, ours, theirs, [attack_option(965), play_option(0, seat), play_option(1, seat)])
        parent = [0]
        self.assertIs(self.invoke(raw, parent), parent)

        stretcher = card(1097, 31, seat)
        discard = [card(169, 41, seat), card(57, 42, seat)]
        ours, theirs = self.metal_reply_state(seat, [stretcher], discard=discard)
        raw = obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)])
        parent = [0]
        self.assertIs(self.invoke(raw, parent), parent)

    def test_transaction_abort_clears_and_returns_parent(self):
        seat = 0
        basic = card(169, 21, seat)
        ours, theirs = self.metal_reply_state(seat, [basic])
        start = obs(seat, ours, theirs, [attack_option(965), play_option(0, seat)])
        self.assertEqual(self.invoke(start, [0]), [1])
        broken_ours, broken_theirs = self.metal_reply_state(seat, [])
        broken = obs(seat, broken_ours, broken_theirs, [attack_option(965)], action_count=4)
        parent = [0]
        returned = self.invoke(broken, parent)
        self.assertIs(returned, parent)
        self.assertIsNone(main._continuity_owner)

    def test_rule1_still_operates_and_structure_is_single(self):
        source = (CANDIDATE / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(functions.count("agent"), 1)
        self.assertEqual(functions.count("_resolve"), 1)
        agent_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "agent")
        calls = [
            node for node in ast.walk(agent_node)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "_parent"
            and node.func.attr == "agent"
        ]
        self.assertEqual(len(calls), 1)

        seat = 0
        hand = [card(666, 30, seat), card(169, 20, seat)]
        ours = player(seat, hand, [], prizes=6)
        theirs = player(1, None, [], prizes=6, hand_count=0)
        active_raw = obs(
            seat, ours, theirs,
            [card_option(AreaType.HAND, 0, seat), card_option(AreaType.HAND, 1, seat)],
            context=SelectContext.SETUP_ACTIVE_POKEMON,
            turn=0,
        )
        self.assertEqual(self.invoke(active_raw, [0]), [0])
        bench_raw = obs(
            seat, ours, theirs,
            [card_option(AreaType.HAND, 0, seat), card_option(AreaType.HAND, 1, seat)],
            context=SelectContext.SETUP_BENCH_POKEMON,
            turn=0,
            min_count=0,
            max_count=2,
        )
        self.assertEqual(self.invoke(bench_raw, []), [1])


if __name__ == "__main__":
    unittest.main()
