from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from archaludon_rl.teacher_adapter import TeacherDecision


def card(card_id: int, serial: int, owner: int) -> dict[str, Any]:
    return {"id": card_id, "serial": serial, "playerIndex": owner}


def pokemon(
    card_id: int,
    serial: int,
    owner: int,
    *,
    hp: int = 100,
    max_hp: int = 100,
    energies: list[int] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": owner,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": list(energies or []),
        "energyCards": [],
        "tools": list(tools or []),
        "preEvolution": [],
    }


def player(
    owner: int,
    *,
    hand_ids: list[int],
    active_id: int,
    bench_ids: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "active": [pokemon(active_id, 10 + owner, owner, energies=[8, 8, 8])],
        "bench": [
            pokemon(value, 30 + index + 10 * owner, owner, energies=[8])
            for index, value in enumerate(bench_ids or [])
        ],
        "benchMax": 5,
        "deckCount": 30,
        "discard": [card(900 + owner, 40 + owner, owner)],
        "prize": [None] * 6,
        "handCount": len(hand_ids),
        "hand": [
            card(value, 100 + index + owner * 20, owner)
            for index, value in enumerate(hand_ids)
        ],
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def observation(
    *,
    options: list[dict[str, Any]] | None = None,
    your_index: int = 0,
    minimum: int = 1,
    maximum: int = 1,
    select_type: int = 0,
    select_context: int = 0,
) -> dict[str, Any]:
    default_options = [
        {"type": 7, "index": 0},
        {"type": 14},
    ]
    players = [
        player(0, hand_ids=[100, 101], active_id=200, bench_ids=[201]),
        player(1, hand_ids=[], active_id=300, bench_ids=[301]),
    ]
    # Deliberately expose fake hidden fields to test whitelisting.
    players[1]["hand"] = [card(777, 777, 1)]
    players[1]["handCount"] = 1
    players[0]["prize"] = [card(600 + i, 600 + i, 0) for i in range(6)]
    players[1]["prize"] = [card(700 + i, 700 + i, 1) for i in range(6)]
    return {
        "select": {
            "type": select_type,
            "context": select_context,
            "minCount": minimum,
            "maxCount": maximum,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": deepcopy(options or default_options),
            "deck": [card(500, 500, your_index), card(501, 501, your_index)],
            "contextCard": None,
            "effect": None,
        },
        "logs": [
            {
                "type": 10,
                "playerIndex": your_index,
                "cardId": 100,
                "serial": 999,
            }
        ],
        "current": {
            "turn": 3,
            "turnActionCount": 1,
            "yourIndex": your_index,
            "firstPlayer": your_index,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [card(1244, 88, your_index)],
            "looking": None,
            "players": players,
        },
        "search_begin_input": "opaque-engine-snapshot",
        "rng_state": [1, 2, 3],
        "unknown_future_hidden_field": {"secret": True},
    }


def exact_telemetry(**overrides: Any) -> dict[str, Any]:
    row = {
        "active_owner_before": None,
        "active_owner_after": None,
        "active_transaction_owner": None,
        "eligible_rule_ids": [],
        "precedence_reason": "rank17_exact_parent",
        "winning_rule_id": "exact_historical_silver",
        "rollback_reason": None,
        "caught_exceptions": [],
        "invalid_or_emergency_fallback": False,
        "option_binding_result": "BOUND",
        "duplicate_or_reset_state": None,
        "final_action": [{"type": 7, "card_id": 100}],
    }
    row.update(overrides)
    return row


class StubTeacher:
    def __init__(self, action: tuple[int, ...] = (0,), telemetry=None):
        self.action = action
        self.telemetry = telemetry or (exact_telemetry(),)
        self.calls = 0

    def decide(self, observation: Any) -> TeacherDecision:
        self.calls += 1
        return TeacherDecision(self.action, tuple(self.telemetry), 1)


class FakeModel:
    def __init__(self, residuals: list[float], value: float = 0.0):
        self.residuals = residuals
        self.value = value
        self.calls = 0

    def predict(self, state, actions):
        self.calls += 1
        return list(self.residuals), self.value
