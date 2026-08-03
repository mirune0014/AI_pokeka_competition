from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .config import HUMAN_VIEW_SCHEMA_VERSION
from .models import MatchPhase


class ProjectionError(RuntimeError):
    pass


FORBIDDEN_KEYS = {
    "serial",
    "deck",
    "search_begin_input",
    "selected",
    "raw_observation",
    "visualize_data",
    "score",
    "reason",
    "ai_options",
}

PUBLIC_LOG_CARD_TYPES = {
    "Switch",
    "Change",
    "Play",
    "Attach",
    "Evolve",
    "Devolve",
    "MoveAttached",
    "Attack",
    "HpChange",
    "Poisoned",
    "Burned",
    "Asleep",
    "Paralyzed",
    "Confused",
}

LOG_TYPE_NAMES = {
    0: "Shuffle",
    1: "HasBasicPokemon",
    2: "TurnStart",
    3: "TurnEnd",
    4: "Draw",
    5: "DrawReverse",
    6: "MoveCard",
    7: "MoveCardReverse",
    8: "Switch",
    9: "Change",
    10: "Play",
    11: "Attach",
    12: "Evolve",
    13: "Devolve",
    14: "MoveAttached",
    15: "Attack",
    16: "HpChange",
    17: "Poisoned",
    18: "Burned",
    19: "Asleep",
    20: "Paralyzed",
    21: "Confused",
    22: "Coin",
    23: "Result",
}


def _as_int(value: Any, field: str) -> int:
    if type(value) is not int:
        raise ProjectionError(f"{field} must be int")
    return value


def _as_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ProjectionError(f"{field} must be bool")
    return value


def _as_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProjectionError(f"{field} must be list")
    return value


def _as_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectionError(f"{field} must be object")
    return value


@dataclass(frozen=True)
class HumanViewProjector:
    match_id: str
    human_seat: int
    secret: bytes
    card_names: Mapping[int, str]

    def __post_init__(self) -> None:
        if self.human_seat not in (0, 1):
            raise ValueError("human seat must be 0 or 1")
        if len(self.secret) < 16:
            raise ValueError("projection secret must be at least 16 bytes")

    def _token(self, seat: int, zone: str, serial: int) -> str:
        # Stable card identity links board shortcuts to the generic legal panel.
        message = f"{self.match_id}:{seat}:{serial}".encode("utf-8")
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()[:32]

    def state_token_for_card(self, card: dict[str, Any], *, seat: int | None = None, zone: str = "option") -> str | None:
        serial = card.get("serial")
        owner = card.get("playerIndex", seat)
        if type(serial) is not int or type(owner) is not int or owner not in (0, 1):
            return None
        return self._token(owner, zone, serial)

    def _card(self, card: Any, *, seat: int, zone: str, require_owner: bool = False) -> dict[str, Any]:
        value = _as_dict(card, f"{zone} card")
        card_id = _as_int(value.get("id"), f"{zone}.id")
        serial = _as_int(value.get("serial"), f"{zone}.serial")
        owner = value.get("playerIndex")
        if require_owner and owner != seat:
            raise ProjectionError(f"{zone} card owner mismatch")
        if owner is not None and (type(owner) is not int or owner not in (0, 1)):
            raise ProjectionError(f"{zone} card owner is invalid")
        return {
            "card_id": card_id,
            "state_token": self._token(seat if owner is None else owner, zone, serial),
            "fallback_name": self.card_names.get(card_id, f"Card {card_id}"),
        }

    def _pokemon(self, pokemon: Any, *, seat: int, zone: str) -> dict[str, Any] | None:
        if pokemon is None:
            return None
        value = _as_dict(pokemon, f"{zone} pokemon")
        base = self._card(value, seat=seat, zone=zone)
        energy_types = []
        for item in _as_list(value.get("energies", []), f"{zone}.energies"):
            if type(item) not in (int, str):
                raise ProjectionError(f"{zone}.energies contains an invalid value")
            energy_types.append(item)
        return {
            **base,
            "hp": _as_int(value.get("hp"), f"{zone}.hp"),
            "max_hp": _as_int(value.get("maxHp"), f"{zone}.maxHp"),
            "appear_this_turn": _as_bool(value.get("appearThisTurn"), f"{zone}.appearThisTurn"),
            "energies": energy_types,
            "energy_cards": [
                self._card(card, seat=seat, zone=f"{zone}.energy")
                for card in _as_list(value.get("energyCards", []), f"{zone}.energyCards")
            ],
            "tools": [
                self._card(card, seat=seat, zone=f"{zone}.tool")
                for card in _as_list(value.get("tools", []), f"{zone}.tools")
            ],
            "pre_evolution": [
                self._card(card, seat=seat, zone=f"{zone}.preEvolution")
                for card in _as_list(value.get("preEvolution", []), f"{zone}.preEvolution")
            ],
        }

    def _public_player(self, player: dict[str, Any], *, seat: int, mask_setup: bool) -> dict[str, Any]:
        active = _as_list(player.get("active", []), f"player {seat}.active")
        bench = _as_list(player.get("bench", []), f"player {seat}.bench")
        if mask_setup:
            # Setup choices are simultaneously revealed; even their interim counts
            # remain private until turn one begins.
            active_view: list[dict[str, Any] | None] = []
            bench_view: list[dict[str, Any] | None] = []
        else:
            active_view = [self._pokemon(card, seat=seat, zone="active") for card in active]
            bench_view = [self._pokemon(card, seat=seat, zone=f"bench.{index}") for index, card in enumerate(bench)]
        conditions = {
            "poisoned": _as_bool(player.get("poisoned", False), "poisoned"),
            "burned": _as_bool(player.get("burned", False), "burned"),
            "asleep": _as_bool(player.get("asleep", False), "asleep"),
            "paralyzed": _as_bool(player.get("paralyzed", False), "paralyzed"),
            "confused": _as_bool(player.get("confused", False), "confused"),
        }
        prize = _as_list(player.get("prize", []), f"player {seat}.prize")
        discard = _as_list(player.get("discard", []), f"player {seat}.discard")
        return {
            "seat": seat,
            "active": active_view,
            "bench": bench_view,
            "bench_max": _as_int(player.get("benchMax"), f"player {seat}.benchMax"),
            "deck_count": _as_int(player.get("deckCount"), f"player {seat}.deckCount"),
            "discard": [self._card(card, seat=seat, zone="discard") for card in discard],
            "prize_count": len(prize),
            "hand_count": _as_int(player.get("handCount"), f"player {seat}.handCount"),
            "conditions": conditions,
        }

    def _human_hand(self, player: dict[str, Any]) -> list[dict[str, Any]]:
        hand = _as_list(player.get("hand"), "human hand")
        hand_count = _as_int(player.get("handCount"), "human handCount")
        if len(hand) != hand_count:
            raise ProjectionError("human hand length does not match handCount")
        return [
            self._card(card, seat=self.human_seat, zone="hand", require_owner=True)
            for card in hand
        ]

    def _looking(self, normal_observation: dict[str, Any], acting_seat: int) -> list[dict[str, Any] | None]:
        if acting_seat != self.human_seat:
            return []
        normal_current = normal_observation.get("current")
        if not isinstance(normal_current, dict) or normal_current.get("yourIndex") != self.human_seat:
            return []
        looking = normal_current.get("looking")
        if looking is None:
            return []
        values = _as_list(looking, "normal looking")
        result: list[dict[str, Any] | None] = []
        for index, card in enumerate(values):
            result.append(None if card is None else self._card(card, seat=self.human_seat, zone=f"looking.{index}"))
        return result

    def project(
        self,
        full_frame: dict[str, Any],
        normal_observation: dict[str, Any],
        *,
        revision: int,
        phase: MatchPhase | str,
    ) -> dict[str, Any]:
        full_current = _as_dict(full_frame.get("current"), "full current")
        players = _as_list(full_current.get("players"), "full current.players")
        if len(players) != 2 or not all(isinstance(player, dict) for player in players):
            raise ProjectionError("full current must contain exactly two players")
        acting_seat = _as_int(full_current.get("yourIndex"), "current.yourIndex")
        if acting_seat not in (0, 1):
            raise ProjectionError("current.yourIndex must be 0 or 1")
        turn = _as_int(full_current.get("turn"), "current.turn")
        first_player = _as_int(full_current.get("firstPlayer"), "current.firstPlayer")
        turn_player = -1 if turn <= 0 or first_player not in (0, 1) else (first_player + turn - 1) % 2
        result = _as_int(full_current.get("result"), "current.result")
        phase_value = phase.value if isinstance(phase, MatchPhase) else MatchPhase(phase).value
        opponent_seat = 1 - self.human_seat
        human_player = _as_dict(players[self.human_seat], "human player")
        opponent_player = _as_dict(players[opponent_seat], "opponent player")
        human = self._public_player(human_player, seat=self.human_seat, mask_setup=False)
        human["hand"] = self._human_hand(human_player)
        opponent = self._public_player(opponent_player, seat=opponent_seat, mask_setup=turn == 0)
        stadium = _as_list(full_current.get("stadium", []), "stadium")
        view = {
            "schema_version": HUMAN_VIEW_SCHEMA_VERSION,
            "match_id": self.match_id,
            "revision": revision,
            "state_revision": revision,
            "step_id": revision,
            "phase": phase_value,
            "human_seat": self.human_seat,
            "acting_seat": acting_seat,
            "turn_player": turn_player,
            "can_act": result == -1 and acting_seat == self.human_seat,
            "turn": turn,
            "first_player": first_player,
            "result": result,
            "turn_flags": {
                "supporter_played": _as_bool(full_current.get("supporterPlayed"), "supporterPlayed"),
                "stadium_played": _as_bool(full_current.get("stadiumPlayed"), "stadiumPlayed"),
                "energy_attached": _as_bool(full_current.get("energyAttached"), "energyAttached"),
                "retreated": _as_bool(full_current.get("retreated"), "retreated"),
            },
            "stadium": None if not stadium else self._card(stadium[0], seat=acting_seat, zone="stadium"),
            "human": human,
            "opponent": opponent,
            "looking": self._looking(normal_observation, acting_seat),
        }
        assert_no_forbidden_keys(view)
        return view


def _log_type(value: Any) -> str:
    if type(value) is int:
        return LOG_TYPE_NAMES.get(value, "Unknown")
    if isinstance(value, str) and value in set(LOG_TYPE_NAMES.values()):
        return value
    return "Unknown"


def sanitize_public_logs(logs: Any, *, human_seat: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if not isinstance(logs, list):
        return output
    for raw in logs:
        if not isinstance(raw, dict):
            continue
        kind = _log_type(raw.get("type"))
        if kind == "Unknown":
            continue
        player = raw.get("playerIndex")
        item: dict[str, Any] = {"type": kind}
        if type(player) is int and player in (0, 1):
            item["player_index"] = player
        if kind == "Draw":
            item["count"] = 1
            if player == human_seat and type(raw.get("cardId")) is int:
                item["card_id"] = raw["cardId"]
        elif kind in {"MoveCard", "MoveCardReverse"}:
            for source, target in (("fromArea", "from_area"), ("toArea", "to_area")):
                if type(raw.get(source)) in (int, str):
                    item[target] = raw[source]
        elif kind in PUBLIC_LOG_CARD_TYPES:
            for source, target in (
                ("cardId", "card_id"),
                ("cardIdActive", "active_card_id"),
                ("cardIdBench", "bench_card_id"),
                ("cardIdBefore", "before_card_id"),
                ("cardIdAfter", "after_card_id"),
                ("cardIdTarget", "target_card_id"),
                ("attackId", "attack_id"),
                ("value", "value"),
                ("isRecover", "is_recover"),
            ):
                if type(raw.get(source)) in (int, bool):
                    item[target] = raw[source]
        elif kind == "Coin" and type(raw.get("head")) is bool:
            item["heads"] = raw["head"]
        elif kind == "Result":
            if type(raw.get("result")) is int:
                item["result"] = raw["result"]
            if type(raw.get("reason")) is int:
                item["result_reason"] = raw["reason"]
        output.append(item)
    assert_no_forbidden_keys(output)
    return output


def assert_no_forbidden_keys(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                raise ProjectionError(f"forbidden key at {path}.{key}")
            assert_no_forbidden_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_forbidden_keys(item, path=f"{path}[{index}]")


def assert_canaries_absent(value: Any, canaries: list[str | int]) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for canary in canaries:
        needle = json.dumps(canary, ensure_ascii=False)
        if needle in encoded:
            raise ProjectionError(f"secret canary leaked: {canary!r}")
