from __future__ import annotations

import ast
import inspect
from pathlib import Path
import sys
import unittest
from unittest import mock


AUTONOMOUS_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = (
    AUTONOMOUS_ROOT
    / "candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1"
)
sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, OptionType, SelectContext, SelectType


EXPECTED_TELEMETRY_FIELDS = {
    "rule_id",
    "selected_source",
    "parent_semantic",
    "proposal_semantic",
    "setup_active_card_id",
    "setup_active_serial",
    "setup_bench_serial",
    "proof_gates",
    "rejection_reason",
    "duplicate_retry",
    "option_permuted",
    "owner_before",
    "owner_after",
    "parent_call_count",
}


def card(card_id: int, serial: int, seat: int) -> dict:
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id: int, serial: int) -> dict:
    return {
        "id": card_id,
        "serial": serial,
        "hp": 130,
        "maxHp": 130,
        "appearThisTurn": False,
        "energies": [],
        "energyCards": [],
        "tools": [],
        "preEvolution": [],
    }


def player(
    hand: list[dict] | None,
    *,
    active: list[dict | None] | None = None,
    bench: list[dict] | None = None,
    bench_max: int = 5,
) -> dict:
    return {
        "active": [] if active is None else active,
        "bench": [] if bench is None else bench,
        "benchMax": bench_max,
        "deckCount": 53,
        "discard": [],
        "prize": [],
        "handCount": len(hand or []),
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def hand_option(index: int, seat: int, **overrides) -> dict:
    option = {
        "type": int(OptionType.CARD),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
    }
    option.update(overrides)
    return option


def observation(
    context: SelectContext,
    ours: dict,
    options: list[dict],
    *,
    seat: int = 0,
    turn: int = 0,
    result: int = -1,
    min_count: int = 1,
    max_count: int = 1,
    select_type: SelectType = SelectType.CARD,
) -> dict:
    opponent = player(None)
    players = [ours, opponent] if seat == 0 else [opponent, ours]
    return {
        "select": {
            "type": int(select_type),
            "context": int(context),
            "minCount": min_count,
            "maxCount": max_count,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": options,
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": turn,
            "turnActionCount": 0,
            "yourIndex": seat,
            "firstPlayer": -1,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": result,
            "stadium": [],
            "looking": None,
            "players": players,
        },
        "search_begin_input": None,
    }


def deck_request() -> dict:
    return {
        "select": None,
        "logs": [],
        "current": None,
        "search_begin_input": None,
    }


class Rule1SetupTests(unittest.TestCase):
    def setUp(self) -> None:
        main._setup_ledger = None
        main._last_proposal = None

    def call_parent(self, raw: dict, parent_action: list[int]):
        calls = []

        def parent(arg):
            calls.append(arg)
            return parent_action

        with mock.patch.object(main._parent, "agent", side_effect=parent):
            action = main.agent(raw)
        self.assertEqual(len(calls), 1)
        self.assertEqual(main._last_telemetry["parent_call_count"], 1)
        self.assertEqual(set(main._last_telemetry), EXPECTED_TELEMETRY_FIELDS)
        return action

    def commit_active(
        self,
        hand: list[dict],
        *,
        seat: int = 0,
        selected_hand_index: int | None = None,
        option_indices: list[int] | None = None,
    ) -> dict:
        indices = list(range(len(hand))) if option_indices is None else option_indices
        raw = observation(
            SelectContext.SETUP_ACTIVE_POKEMON,
            player(hand),
            [hand_option(index, seat) for index in indices],
            seat=seat,
        )
        if selected_hand_index is None:
            selected_hand_index = next(
                index for index, value in enumerate(hand)
                if value["id"] == main._CINDERACE
            )
        selected_position = indices.index(selected_hand_index)
        parent_action = [selected_position]
        action = self.call_parent(raw, parent_action)
        self.assertIs(action, parent_action)
        return raw

    def bench_raw(
        self,
        hand: list[dict],
        *,
        seat: int = 0,
        option_indices: list[int] | None = None,
        active: list[dict | None] | None = None,
        bench: list[dict] | None = None,
        bench_max: int = 5,
        turn: int = 0,
        result: int = -1,
        min_count: int = 0,
        max_count: int | None = None,
    ) -> dict:
        indices = list(range(len(hand))) if option_indices is None else option_indices
        return observation(
            SelectContext.SETUP_BENCH_POKEMON,
            player(
                hand,
                active=[None] if active is None else active,
                bench=bench,
                bench_max=bench_max,
            ),
            [hand_option(index, seat) for index in indices],
            seat=seat,
            turn=turn,
            result=result,
            min_count=min_count,
            max_count=len(indices) if max_count is None else max_count,
        )

    def selected_serial(self, raw: dict, action: list[int]) -> int:
        option = raw["select"]["option"][action[0]]
        seat = raw["current"]["yourIndex"]
        return raw["current"]["players"][seat]["hand"][option["index"]]["serial"]

    def test_both_seats_one_and_multiple_duraludon_choose_minimum_serial(self) -> None:
        for seat in (0, 1):
            for hand, order, expected in (
                (
                    [card(main._CINDERACE, 30, seat), card(main._DURALUDON, 20, seat)],
                    [0, 1],
                    20,
                ),
                (
                    [
                        card(main._DURALUDON, 22, seat),
                        card(main._CINDERACE, 30, seat),
                        card(main._DURALUDON, 11, seat),
                    ],
                    [2, 1, 0],
                    11,
                ),
            ):
                with self.subTest(seat=seat, expected=expected):
                    main._setup_ledger = None
                    self.commit_active(hand, seat=seat, option_indices=order)
                    raw = self.bench_raw(hand, seat=seat, option_indices=order)
                    action = self.call_parent(raw, [])
                    self.assertEqual(len(action), 1)
                    self.assertEqual(self.selected_serial(raw, action), expected)
                    self.assertEqual(main._last_proposal["transaction"], None)
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
                    self.assertIsNone(main._last_telemetry["owner_before"])
                    self.assertIsNone(main._last_telemetry["owner_after"])

    def test_identical_and_reversed_retry_rebind_same_serial(self) -> None:
        hand = [
            card(main._DURALUDON, 22, 0),
            card(main._CINDERACE, 30, 0),
            card(main._DURALUDON, 11, 0),
        ]
        self.commit_active(hand)
        raw = self.bench_raw(hand, option_indices=[0, 1, 2])
        first = self.call_parent(raw, [])
        same = self.call_parent(raw, [])
        self.assertEqual(self.selected_serial(raw, first), 11)
        self.assertEqual(self.selected_serial(raw, same), 11)
        self.assertTrue(main._last_telemetry["duplicate_retry"])
        self.assertFalse(main._last_telemetry["option_permuted"])

        reversed_raw = self.bench_raw(hand, option_indices=[2, 1, 0])
        reversed_action = self.call_parent(reversed_raw, [])
        self.assertEqual(self.selected_serial(reversed_raw, reversed_action), 11)
        self.assertTrue(main._last_telemetry["duplicate_retry"])
        self.assertTrue(main._last_telemetry["option_permuted"])

    def test_retry_never_substitutes_a_replacement_serial(self) -> None:
        hand = [
            card(main._CINDERACE, 30, 0),
            card(main._DURALUDON, 11, 0),
            card(main._DURALUDON, 22, 0),
        ]
        self.commit_active(hand)
        first_raw = self.bench_raw(hand)
        self.assertEqual(self.selected_serial(first_raw, self.call_parent(first_raw, [])), 11)

        changed_hand = [hand[0], hand[2]]
        changed_raw = self.bench_raw(changed_hand)
        parent_action = []
        action = self.call_parent(changed_raw, parent_action)
        self.assertIs(action, parent_action)
        self.assertEqual(main._last_telemetry["rejection_reason"], "already_emitted")

    def test_non_cinderace_or_unknown_active_commit_returns_parent(self) -> None:
        for active_id in (main._DURALUDON, 57, 9999):
            with self.subTest(active_id=active_id):
                main._setup_ledger = None
                hand = [card(active_id, 40, 0), card(main._DURALUDON, 11, 0)]
                self.commit_active(hand, selected_hand_index=0)
                raw = self.bench_raw(hand)
                parent_action = []
                action = self.call_parent(raw, parent_action)
                self.assertIs(action, parent_action)
                self.assertEqual(
                    main._last_telemetry["rejection_reason"],
                    "committed_active_not_cinderace",
                )

    def test_visible_duraludon_active_mismatch_bench_presence_and_full_bench_reject(self) -> None:
        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        cases = (
            ({"active": [pokemon(main._DURALUDON, 99)]}, "visible_active_mismatch"),
            ({"bench": [pokemon(main._DURALUDON, 99)]}, "visible_duraludon"),
            (
                {
                    "bench": [pokemon(57, value) for value in range(100, 105)],
                    "bench_max": 5,
                },
                "bench_full",
            ),
            (
                {"bench": [pokemon(57, 99), pokemon(57, 99)]},
                "duplicate_visible_serial",
            ),
        )
        for kwargs, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                main._setup_ledger = None
                self.commit_active(hand)
                raw = self.bench_raw(hand, **kwargs)
                parent_action = []
                action = self.call_parent(raw, parent_action)
                self.assertIs(action, parent_action)
                self.assertEqual(
                    main._last_telemetry["rejection_reason"], expected_reason
                )

    def test_no_duraludon_and_count_bounds_reject(self) -> None:
        base_hand = [card(main._CINDERACE, 30, 0)]
        self.commit_active(base_hand)
        raw = self.bench_raw(base_hand)
        parent_action = []
        self.assertIs(self.call_parent(raw, parent_action), parent_action)
        self.assertEqual(main._last_telemetry["rejection_reason"], "no_duraludon_option")

        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        for min_count, max_count in ((1, 2), (0, 0), (0, 3)):
            with self.subTest(min_count=min_count, max_count=max_count):
                main._setup_ledger = None
                self.commit_active(hand)
                raw = self.bench_raw(
                    hand, min_count=min_count, max_count=max_count
                )
                parent_action = []
                self.assertIs(self.call_parent(raw, parent_action), parent_action)
                self.assertEqual(
                    main._last_telemetry["rejection_reason"], "invalid_count_bounds"
                )

    def test_hand_owner_serial_and_duplicate_invalidity_reject(self) -> None:
        valid = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        invalid_hands = (
            [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 1)],
            [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 0, 0)],
            [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 30, 0)],
        )
        for invalid in invalid_hands:
            with self.subTest(invalid=invalid):
                main._setup_ledger = None
                self.commit_active(valid)
                raw = self.bench_raw(invalid)
                parent_action = []
                self.assertIs(self.call_parent(raw, parent_action), parent_action)
                self.assertIn(
                    main._last_telemetry["rejection_reason"],
                    {"invalid_hand_card_binding", "duplicate_hand_serial"},
                )

    def test_option_owner_index_card_id_and_serial_invalidity_reject(self) -> None:
        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        option_mutations = (
            {"playerIndex": 1},
            {"index": 9},
            {"cardId": 999},
            {"serial": 999},
        )
        for mutation in option_mutations:
            with self.subTest(mutation=mutation):
                main._setup_ledger = None
                self.commit_active(hand)
                raw = self.bench_raw(hand)
                raw["select"]["option"][1].update(mutation)
                parent_action = []
                self.assertIs(self.call_parent(raw, parent_action), parent_action)
                self.assertIsNone(main._last_proposal)

    def test_turn_result_seat_and_visible_active_serial_mismatch_reject(self) -> None:
        hand0 = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        for kwargs, expected in (
            ({"turn": 1}, "bench_turn_mismatch"),
            ({"result": 0}, "bench_result_mismatch"),
            ({"active": [pokemon(main._CINDERACE, 31)]}, "visible_active_mismatch"),
        ):
            with self.subTest(expected=expected):
                main._setup_ledger = None
                self.commit_active(hand0)
                raw = self.bench_raw(hand0, **kwargs)
                parent_action = []
                self.assertIs(self.call_parent(raw, parent_action), parent_action)
                self.assertEqual(main._last_telemetry["rejection_reason"], expected)

        main._setup_ledger = None
        self.commit_active(hand0, seat=0)
        hand1 = [card(main._CINDERACE, 30, 1), card(main._DURALUDON, 11, 1)]
        raw = self.bench_raw(hand1, seat=1)
        parent_action = []
        self.assertIs(self.call_parent(raw, parent_action), parent_action)
        self.assertEqual(main._last_telemetry["rejection_reason"], "seat_mismatch")

    def test_parent_nonempty_and_already_emitted_new_prompt_return_exact_parent(self) -> None:
        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        self.commit_active(hand)
        raw = self.bench_raw(hand)
        parent_nonempty = [0]
        self.assertIs(self.call_parent(raw, parent_nonempty), parent_nonempty)
        self.assertEqual(main._last_telemetry["rejection_reason"], "parent_not_empty")

        self.assertEqual(self.selected_serial(raw, self.call_parent(raw, [])), 11)
        changed_board = self.bench_raw(hand, bench=[pokemon(57, 90)])
        parent_empty = []
        self.assertIs(self.call_parent(changed_board, parent_empty), parent_empty)
        self.assertEqual(main._last_telemetry["rejection_reason"], "already_emitted")

    def test_active_mulligan_is_first_and_deck_request_preserve_parent_identity(self) -> None:
        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        active_raw = observation(
            SelectContext.SETUP_ACTIVE_POKEMON,
            player(hand),
            [hand_option(0, 0), hand_option(1, 0)],
        )
        active_parent = [0]
        self.assertIs(self.call_parent(active_raw, active_parent), active_parent)

        for context in (SelectContext.MULLIGAN, SelectContext.IS_FIRST):
            raw = observation(
                context,
                player(hand),
                [{"type": int(OptionType.YES)}, {"type": int(OptionType.NO)}],
                select_type=SelectType.YES_NO,
            )
            parent_action = [1]
            self.assertIs(self.call_parent(raw, parent_action), parent_action)
            self.assertEqual(
                main._last_telemetry["rejection_reason"], "outside_rule_surface"
            )

        parent_deck = [value for value in range(60)]
        self.assertIs(self.call_parent(deck_request(), parent_deck), parent_deck)
        self.assertEqual(main._last_telemetry["rejection_reason"], "deck_request")

    def test_invalid_active_parent_binding_preserves_parent_and_clears_ledger(self) -> None:
        hand = [card(main._CINDERACE, 30, 0), card(main._DURALUDON, 11, 0)]
        raw = observation(
            SelectContext.SETUP_ACTIVE_POKEMON,
            player(hand),
            [hand_option(0, 0), hand_option(1, 0)],
        )
        for parent_action in ([], [0, 1], [9]):
            with self.subTest(parent_action=parent_action):
                main._setup_ledger = {"stale": True}
                action = self.call_parent(raw, parent_action)
                self.assertIs(action, parent_action)
                self.assertIsNone(main._setup_ledger)

        duplicate_raw = observation(
            SelectContext.SETUP_ACTIVE_POKEMON,
            player(hand),
            [hand_option(0, 0), hand_option(0, 0), hand_option(1, 0)],
        )
        duplicate_parent = [0]
        self.assertIs(
            self.call_parent(duplicate_raw, duplicate_parent), duplicate_parent
        )
        self.assertIsNone(main._setup_ledger)

    def test_single_public_agent_single_resolver_and_last_callable_loader(self) -> None:
        tree = ast.parse((CANDIDATE / "main.py").read_text(encoding="utf-8"))
        function_names = [
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        ]
        self.assertEqual(function_names.count("agent"), 1)
        self.assertEqual(function_names.count("_resolve"), 1)
        self.assertNotIn("score_option", function_names)
        self.assertNotIn("choose_options", function_names)
        public_functions = [name for name in function_names if not name.startswith("_")]
        self.assertEqual(public_functions, ["agent"])

        local_functions = [
            (name, value)
            for name, value in main.__dict__.items()
            if inspect.isfunction(value) and value.__module__ == main.__name__
        ]
        self.assertEqual(local_functions[-1][0], "agent")


if __name__ == "__main__":
    unittest.main()
