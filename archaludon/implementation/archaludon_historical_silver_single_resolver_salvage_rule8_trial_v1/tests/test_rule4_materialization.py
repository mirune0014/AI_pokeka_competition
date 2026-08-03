from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys
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
from cg.api import AreaType, LogType, OptionType, SelectContext, SelectType


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(
    card_id,
    serial,
    seat,
    *,
    hp=None,
    max_hp=None,
    appear=False,
    energy_serials=(),
    energy_ids=None,
    pre=(),
):
    data = main._parent.CARD_DB[card_id]
    ids = tuple(main._METAL_ENERGY for _ in energy_serials) if energy_ids is None else tuple(energy_ids)
    energies = [int(main._parent.CARD_DB[value].energyType) for value in ids]
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp if hp is None else hp,
        "maxHp": data.hp if max_hp is None else max_hp,
        "appearThisTurn": appear,
        "energies": energies,
        "energyCards": [
            card(value, energy_serial, seat)
            for value, energy_serial in zip(ids, energy_serials)
        ],
        "tools": [],
        "preEvolution": list(pre),
    }


def player(seat, hand, active, bench=(), *, prizes=4, bench_max=5):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": bench_max,
        "deckCount": 40,
        "discard": [],
        "prize": [None] * prizes,
        "handCount": len(hand) if hand is not None else 0,
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def play(index, seat):
    return {
        "type": int(OptionType.PLAY),
        "index": index,
        "playerIndex": seat,
    }


def evolve(index, seat, bench_index=0):
    return {
        "type": int(OptionType.EVOLVE),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.BENCH),
        "inPlayIndex": bench_index,
    }


def attach(index, seat):
    return {
        "type": int(OptionType.ATTACH),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.ACTIVE),
        "inPlayIndex": 0,
    }


def attack(attack_id):
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def end():
    return {"type": int(OptionType.END)}


def observation(
    seat,
    ours,
    theirs,
    options,
    *,
    turn=8,
    action_count=3,
    supporter=False,
    stadium=(),
    energy_attached=False,
    context=SelectContext.MAIN,
    select_type=None,
    effect=None,
    logs=(),
):
    players = [ours, theirs] if seat == 0 else [theirs, ours]
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
            "turn": turn,
            "turnActionCount": action_count,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": supporter,
            "stadiumPlayed": bool(stadium),
            "energyAttached": energy_attached,
            "retreated": False,
            "result": -1,
            "stadium": list(stadium),
            "looking": None,
            "players": players,
        },
        "search_begin_input": None,
    }


def opponent(seat, *, metal=False, prizes=4):
    active_id = main._DURALUDON if metal else 57
    return player(
        1 - seat,
        None,
        pokemon(active_id, 900 + seat, 1 - seat),
        prizes=prizes,
    )


def route_fixture(route, seat, *, ex=False, multiple=False):
    lillie = card(main._LILLIE, 100 + seat * 1000, seat)
    opp = opponent(seat)
    if route == main._ROUTE_DURALUDON:
        selected = card(main._DURALUDON, 110 + seat * 1000, seat)
        hand = [lillie, selected]
        active = pokemon(main._CINDERACE, 200 + seat * 1000, seat)
        ours = player(seat, hand, active)
        pre = observation(seat, ours, opp, [play(0, seat), play(1, seat), end()])
        post_ours = player(
            seat,
            [lillie],
            copy.deepcopy(active),
            [pokemon(main._DURALUDON, selected["serial"], seat, appear=True)],
        )
        post = observation(seat, post_ours, opp, [play(0, seat), end()], action_count=4)
        return pre, post, 1, selected["serial"]
    if route == main._ROUTE_EVOLUTION:
        evolution_id = main._ARCHALUDON_EX if ex else main._ARCHALUDON
        selected = card(evolution_id, 120 + seat * 1000, seat)
        base_serial = 210 + seat * 1000
        energy_serials = (510 + seat * 1000, 511 + seat * 1000, 512 + seat * 1000)
        active = pokemon(main._CINDERACE, 200 + seat * 1000, seat)
        base = pokemon(main._DURALUDON, base_serial, seat, energy_serials=energy_serials)
        ours = player(seat, [lillie, selected], active, [base])
        pre = observation(seat, ours, opp, [play(0, seat), evolve(1, seat), end()])
        evolved = pokemon(
            evolution_id,
            selected["serial"],
            seat,
            energy_serials=energy_serials,
            pre=[card(main._DURALUDON, base_serial, seat)],
        )
        post_ours = player(seat, [lillie], copy.deepcopy(active), [evolved])
        post = observation(seat, post_ours, opp, [play(0, seat), end()], action_count=4)
        return pre, post, 1, selected["serial"]
    if route == main._ROUTE_THIRD_METAL:
        low = card(main._METAL_ENERGY, 130 + seat * 1000, seat)
        high = card(main._METAL_ENERGY, 140 + seat * 1000, seat)
        active = pokemon(
            main._DURALUDON,
            220 + seat * 1000,
            seat,
            energy_serials=(520 + seat * 1000, 521 + seat * 1000),
        )
        hand = [lillie, high, low] if multiple else [lillie, low]
        options = [play(0, seat), attach(1, seat)]
        expected = 1
        if multiple:
            options.append(attach(2, seat))
            expected = 2
        options.extend([attack(223), end()])
        ours = player(seat, hand, active)
        pre = observation(seat, ours, opp, options)
        selected = low
        after = pokemon(
            main._DURALUDON,
            active["serial"],
            seat,
            energy_serials=(520 + seat * 1000, 521 + seat * 1000, selected["serial"]),
        )
        remaining = [lillie, high] if multiple else [lillie]
        post_ours = player(seat, remaining, after)
        post = observation(
            seat,
            post_ours,
            opp,
            [play(0, seat), attack(223), attack(224), end()],
            action_count=4,
            energy_attached=True,
        )
        return pre, post, expected, selected["serial"]
    if route == main._ROUTE_LAB:
        low = card(main._FULL_METAL_LAB, 150 + seat * 1000, seat)
        high = card(main._FULL_METAL_LAB, 160 + seat * 1000, seat)
        active = pokemon(
            main._DURALUDON,
            230 + seat * 1000,
            seat,
            energy_serials=(530 + seat * 1000, 531 + seat * 1000, 532 + seat * 1000),
        )
        hand = [lillie, high, low] if multiple else [lillie, low]
        options = [play(0, seat), play(1, seat)]
        expected = 1
        if multiple:
            options.append(play(2, seat))
            expected = 2
        options.extend([attack(223), attack(224), end()])
        ours = player(seat, hand, active)
        pre = observation(seat, ours, opp, options)
        remaining = [lillie, high] if multiple else [lillie]
        post_ours = player(seat, remaining, copy.deepcopy(active))
        post = observation(
            seat,
            post_ours,
            opp,
            [play(0, seat), attack(223), attack(224), end()],
            action_count=4,
            stadium=[low],
        )
        return pre, post, expected, low["serial"]
    raise AssertionError(route)


class Rule4MaterializationTests(unittest.TestCase):
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

    def test_both_seats_all_four_routes_then_return_to_current_parent(self):
        routes = (
            main._ROUTE_DURALUDON,
            main._ROUTE_EVOLUTION,
            main._ROUTE_THIRD_METAL,
            main._ROUTE_LAB,
        )
        for seat in (0, 1):
            for route in routes:
                with self.subTest(seat=seat, route=route):
                    self.setUp()
                    pre, post, expected, selected_serial = route_fixture(
                        route, seat, ex=(route == main._ROUTE_EVOLUTION and seat == 1),
                        multiple=route in {main._ROUTE_THIRD_METAL, main._ROUTE_LAB},
                    )
                    self.assertEqual(self.call(pre, [0]), [expected])
                    self.assertEqual(main._last_proposal["purpose"], route)
                    self.assertEqual(
                        main._last_proposal["exact_proof"]["selected_ref"][1],
                        selected_serial,
                    )
                    self.assertIsNotNone(main._materialization_owner)
                    self.assertEqual(self.call(post, [0]), [0])
                    self.assertIsNone(main._last_proposal)
                    self.assertIsNone(main._materialization_owner)
                    self.assertEqual(
                        main._last_telemetry["rejection_reason"],
                        "materialization_confirmed:" + route,
                    )

    def test_all_routes_same_prompt_retry_rebinds_after_option_reversal(self):
        routes = (
            main._ROUTE_DURALUDON,
            main._ROUTE_EVOLUTION,
            main._ROUTE_THIRD_METAL,
            main._ROUTE_LAB,
        )
        for seat in (0, 1):
            for route in routes:
                with self.subTest(seat=seat, route=route):
                    self.setUp()
                    pre, _post, expected, selected_serial = route_fixture(route, seat)
                    self.assertEqual(self.call(pre, [0]), [expected])
                    retry = copy.deepcopy(pre)
                    retry["select"]["option"].reverse()
                    lillie_position = next(
                        index
                        for index, option in enumerate(retry["select"]["option"])
                        if option.get("type") == int(OptionType.PLAY)
                        and retry["current"]["players"][seat]["hand"][option["index"]]["id"]
                        == main._LILLIE
                    )
                    action = self.call(retry, [lillie_position])
                    selected_position = action[0]
                    selected_option = retry["select"]["option"][selected_position]
                    selected_card = retry["current"]["players"][seat]["hand"][selected_option["index"]]
                    self.assertEqual(selected_card["serial"], selected_serial)
                    self.assertTrue(main._last_telemetry["duplicate_retry"])
                    self.assertTrue(main._last_telemetry["option_permuted"])
                    self.assertEqual(
                        main._materialization_owner["stage"], "MATERIALIZATION_EMITTED"
                    )

    def test_route_one_multiplicity_unknown_metadata_and_illegal_option_reject(self):
        pre, _post, _expected, _serial = route_fixture(main._ROUTE_DURALUDON, 0)
        duplicate = copy.deepcopy(pre)
        duplicate_card = card(main._DURALUDON, 111, 0)
        duplicate["current"]["players"][0]["hand"].append(duplicate_card)
        duplicate["current"]["players"][0]["handCount"] += 1
        duplicate["select"]["option"].insert(2, play(2, 0))
        self.assertEqual(self.call(duplicate, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        with mock.patch.dict(main._parent.CARD_DB, {main._DURALUDON: None}):
            self.assertEqual(self.call(pre, [0]), [0])
        illegal = copy.deepcopy(pre)
        illegal["select"]["option"] = [play(0, 0), end()]
        self.assertEqual(self.call(illegal, [0]), [0])

    def test_route_two_negatives(self):
        pre, _post, _expected, _serial = route_fixture(main._ROUTE_EVOLUTION, 0, ex=True)
        appeared = copy.deepcopy(pre)
        appeared["current"]["players"][0]["bench"][0]["appearThisTurn"] = True
        self.assertEqual(self.call(appeared, [0]), [0])

        low_prize = copy.deepcopy(pre)
        low_prize["current"]["players"][1]["prize"] = [None, None]
        self.assertEqual(self.call(low_prize, [0]), [0])

        illegal = copy.deepcopy(pre)
        illegal["select"]["option"] = [play(0, 0), end()]
        self.assertEqual(self.call(illegal, [0]), [0])

        multiple_option = copy.deepcopy(pre)
        second = card(main._ARCHALUDON, 121, 0)
        multiple_option["current"]["players"][0]["hand"].append(second)
        multiple_option["current"]["players"][0]["handCount"] += 1
        multiple_option["select"]["option"].insert(2, evolve(2, 0))
        self.assertEqual(self.call(multiple_option, [0]), [0])

        multiple_ready = copy.deepcopy(pre)
        multiple_ready["current"]["players"][0]["bench"].append(
            pokemon(main._DURALUDON, 211, 0, energy_serials=(513, 514, 515))
        )
        self.assertEqual(self.call(multiple_ready, [0]), [0])

        with mock.patch.dict(main._parent.CARD_DB, {main._ARCHALUDON_EX: None}):
            self.assertEqual(self.call(pre, [0]), [0])

    def test_route_three_negatives_and_lowest_serial(self):
        pre, _post, expected, serial = route_fixture(
            main._ROUTE_THIRD_METAL, 0, multiple=True
        )
        self.assertEqual(self.call(pre, [0]), [expected])
        self.assertEqual(main._last_proposal["exact_proof"]["selected_ref"][1], serial)

        self.setUp()
        used = copy.deepcopy(pre)
        used["current"]["energyAttached"] = True
        self.assertEqual(self.call(used, [0]), [0])

        illegal = copy.deepcopy(pre)
        illegal["select"]["option"] = [play(0, 0), attack(223), end()]
        self.assertEqual(self.call(illegal, [0]), [0])

        unknown = copy.deepcopy(pre)
        active = unknown["current"]["players"][0]["active"][0]
        active["energyCards"][0] = card(13, active["energyCards"][0]["serial"], 0)
        active["energies"][0] = int(main._parent.CARD_DB[13].energyType)
        self.assertEqual(self.call(unknown, [0]), [0])

        with mock.patch.dict(main._parent.ALL_ATTACKS, {224: None}):
            self.assertEqual(self.call(pre, [0]), [0])

    def test_route_four_negatives_and_lowest_serial(self):
        pre, _post, expected, serial = route_fixture(main._ROUTE_LAB, 0, multiple=True)
        self.assertEqual(self.call(pre, [0]), [expected])
        self.assertEqual(main._last_proposal["exact_proof"]["selected_ref"][1], serial)

        self.setUp()
        stadium = copy.deepcopy(pre)
        stadium_card = card(main._FULL_METAL_LAB, 700, 0)
        stadium["current"]["stadium"] = [stadium_card]
        stadium["current"]["stadiumPlayed"] = True
        self.assertEqual(self.call(stadium, [0]), [0])

        metal_opponent = copy.deepcopy(pre)
        metal_opponent["current"]["players"][1]["active"] = [
            pokemon(main._DURALUDON, 901, 1)
        ]
        self.assertEqual(self.call(metal_opponent, [0]), [0])

        illegal = copy.deepcopy(pre)
        illegal["select"]["option"] = [play(0, 0), attack(223), end()]
        self.assertEqual(self.call(illegal, [0]), [0])

        with mock.patch.dict(main._parent.CARD_DB, {main._FULL_METAL_LAB: None}):
            self.assertEqual(self.call(pre, [0]), [0])

    def test_common_parent_and_callback_negatives(self):
        pre, _post, _expected, _serial = route_fixture(main._ROUTE_DURALUDON, 0)
        self.assertEqual(self.call(pre, [2]), [2])

        supporter = copy.deepcopy(pre)
        supporter["current"]["supporterPlayed"] = True
        self.assertEqual(self.call(supporter, [0]), [0])

        effect = copy.deepcopy(pre)
        effect["select"]["effect"] = card(main._LILLIE, 100, 0)
        self.assertEqual(self.call(effect, [0]), [0])

        mandatory = copy.deepcopy(pre)
        mandatory["select"]["context"] = int(SelectContext.TO_HAND)
        mandatory["select"]["type"] = int(SelectType.CARD)
        self.assertEqual(self.call(mandatory, [0]), [0])

        after_attack = copy.deepcopy(pre)
        after_attack["logs"] = [
            {"type": int(LogType.ATTACK), "playerIndex": 0, "attackId": 965}
        ]
        self.assertEqual(self.call(after_attack, [0]), [0])

    def test_stale_turn_owner_conflict_and_failed_postcondition_clear_to_parent(self):
        pre, _post, expected, _serial = route_fixture(main._ROUTE_DURALUDON, 0)
        self.assertEqual(self.call(pre, [0]), [expected])
        stale = copy.deepcopy(pre)
        stale["current"]["turn"] += 1
        self.assertEqual(self.call(stale, [0]), [0])
        self.assertIsNone(main._materialization_owner)

        self.assertEqual(self.call(pre, [0]), [expected])
        main._materialization_owner["owner"] = "OTHER_OWNER"
        self.assertEqual(self.call(pre, [0]), [0])
        self.assertEqual(main._last_telemetry["rejection_reason"], "owner_conflict")
        self.assertIsNone(main._materialization_owner)

        self.assertEqual(self.call(pre, [0]), [expected])
        failed = copy.deepcopy(pre)
        failed["current"]["turnActionCount"] += 1
        self.assertEqual(self.call(failed, [0]), [0])
        self.assertTrue(
            main._last_telemetry["rejection_reason"].startswith(
                "materialization_confirmation_failed:"
            )
        )
        self.assertIsNone(main._materialization_owner)

    def test_single_agent_single_resolver_one_static_parent_call(self):
        tree = ast.parse((CANDIDATE / "main.py").read_text(encoding="utf-8"))
        top_functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(sum(node.name == "agent" for node in top_functions), 1)
        self.assertEqual(sum(node.name == "_resolve" for node in top_functions), 1)
        agent_node = next(node for node in top_functions if node.name == "agent")
        parent_calls = [
            node
            for node in ast.walk(agent_node)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "_parent"
            and node.func.attr == "agent"
        ]
        self.assertEqual(len(parent_calls), 1)
        self.assertEqual(top_functions[-1].name, "agent")


if __name__ == "__main__":
    unittest.main()
