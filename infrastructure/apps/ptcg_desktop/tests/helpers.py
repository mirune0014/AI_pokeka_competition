from __future__ import annotations

from typing import Any


def card(card_id: int, serial: int, owner: int, name: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"id": card_id, "serial": serial, "playerIndex": owner}
    if name is not None:
        value["name"] = name
    return value


def pokemon(card_id: int, serial: int, owner: int) -> dict[str, Any]:
    return {
        **card(card_id, serial, owner, f"Pokemon {card_id}"),
        "hp": 100,
        "maxHp": 120,
        "appearThisTurn": False,
        "energies": [8],
        "energyCards": [card(8, serial + 1000, owner, "Energy")],
        "tools": [],
        "preEvolution": [],
    }


def player(owner: int, *, hand_ids: list[int], deck_ids: list[int], prize_ids: list[int]) -> dict[str, Any]:
    return {
        "active": [pokemon(100 + owner, 10 + owner, owner)],
        "bench": [pokemon(200 + owner, 20 + owner, owner)],
        "benchMax": 5,
        "deckCount": len(deck_ids),
        "discard": [card(300 + owner, 30 + owner, owner)],
        "prize": [card(value, 2000 + index + owner * 100, owner) for index, value in enumerate(prize_ids)],
        "handCount": len(hand_ids),
        "hand": [card(value, 1000 + index + owner * 100, owner) for index, value in enumerate(hand_ids)],
        "deck": [card(value, 3000 + index + owner * 100, owner) for index, value in enumerate(deck_ids)],
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def full_frame(*, acting: int = 0, turn: int = 1, result: int = -1) -> dict[str, Any]:
    return {
        "select": {
            "type": "YesNo",
            "context": "Activate",
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [{"type": "Yes"}, {"type": "No"}],
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": turn,
            "turnActionCount": 1,
            "yourIndex": acting,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": result,
            "stadium": [],
            "lookingCount": 0,
            "looking": None,
            "players": [
                player(0, hand_ids=[401, 402], deck_ids=[910001, 910002], prize_ids=[920001]),
                player(1, hand_ids=[990001, 990002], deck_ids=[991001, 991002], prize_ids=[992001]),
            ],
        },
        "selected": None,
    }


def normal_observation(*, acting: int = 0) -> dict[str, Any]:
    frame = full_frame(acting=acting)
    current = frame["current"]
    current["players"][1 - acting]["hand"] = None
    current["players"][1 - acting].pop("deck", None)
    current["players"][acting].pop("deck", None)
    current["players"][0]["prize"] = [None]
    current["players"][1]["prize"] = [None]
    frame.pop("selected", None)
    frame["select"] = {
        "type": 9,
        "context": 43,
        "minCount": 1,
        "maxCount": 1,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "option": [{"type": 1}, {"type": 2}],
        "deck": None,
        "contextCard": None,
        "effect": None,
    }
    return frame
