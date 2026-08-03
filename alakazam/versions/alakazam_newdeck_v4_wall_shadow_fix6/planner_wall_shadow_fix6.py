"""Action-identical C4 wall-value shadow analysis.

The module owns only diagnostic state.  It never calls an action-producing
analyzer and never returns an executable action.  Unsupported public semantics
are preserved as explicit chance/rejection evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import _cumulative_parent as policy
import planner_public_damage_continuity as public_damage


SCHEMA_VERSION = 6
RULE_VERSION = "V4_WALL_SHADOW_FIX6"
PARENT_CLOSURE_SHA256 = (
    "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
)
ANALYZER_SHA256 = (
    "AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201"
)

FORCED_PROMOTION = "A_FORCED_PROMOTION"
RUN_AWAY_POINT = "B_ACTIVE_DUDUNSPARCE_RUN_AWAY"
TRADING_CHILD = "C_DUNSPARCE_TRADING_PLACES_CHILD"
DELAY_ONE_ATTACK_BRANCH = "ATTACK"
DELAY_ONE_REFUSAL_BRANCH = "REFUSAL"

RUN_AWAY = "RUN_AWAY_ACCELERATION"
REUSABLE = "CERTIFIED_REUSABLE_WALL"
SACRIFICE = "CERTIFIED_SACRIFICE_WALL"
NO_WALL = "NO_WALL_OR_UNKNOWN"
CANDIDATE_KINDS = (RUN_AWAY, REUSABLE, SACRIFICE, NO_WALL)

STRICT = "STRICT_CERTIFIED_WALL"
CHANCE = "PRESERVE_CHANCE_WALL"
REJECTED = "REJECTED"

REPEATABLE_READY = "REPEATABLE_READY"
RECHARGE_REQUIRED = "RECHARGE_REQUIRED"
NO_READY_ATTACK = "NO_READY_ATTACK"
UNKNOWN = "UNKNOWN"

ABRA = 741
KADABRA = 742
ALAKAZAM = 743
DUNSPARCE = 305
DUDUNSPARCE = 66
ALAKAZAM_LINE = frozenset({ABRA, KADABRA, ALAKAZAM})
TRADING_PLACES_ATTACK = 423
POWERFUL_HAND_ATTACK = 1072
SUPER_PSY_BOLT_ATTACK = 1071
PREMIUM_POWER_PRO = 1141
POWER_PRO_FAMILY = frozenset({673, 674, 675, 676, 677, 678})

PLAY = 7
EVOLVE = 9
ABILITY = 10
ATTACK = 13
END_TURN = 14
PROMOTION_OPTION = 3
ACTIVE_AREA = 4
BENCH_AREA = 5
MAIN_CONTEXT = 0
FORCED_PROMOTION_CONTEXT = 4
ATTACK_LOG = 15
MIST_ENERGY = 11
ROCK_FIGHTING_ENERGY = 20
BASIC_PSYCHIC_ENERGY = 5
TEAM_ROCKETS_ARTICUNO = 414
TEAM_ROCKET_NAME_PREFIX = "Team Rocket's "
REPELLING_VEIL_TEXT = (
    "Prevent all effects of attacks used by your opponent’s Pokémon done to "
    "your Basic Team Rocket’s Pokémon. (Existing effects are not removed. "
    "Damage is not an effect.)"
)

STATE_MACHINE = (
    "CAPTURE",
    "VALIDATE_PUBLIC_STATE",
    "BUILD_COUNTERFACTUAL_PAIR",
    "CLASSIFY_PROTECTED_LINE",
    "CLASSIFY_EXPOSE_THREAT",
    "ENUMERATE_FOUR_ALTERNATIVES",
    "CERTIFY_STRICT_OR_CHANCE",
    "PARETO_ARBITRATE",
    "EMIT_SHADOW",
    "RETURN_EXACT_PARENT_ACTION",
)

CHANCE_CODES = frozenset(
    {
        "CAP_ONLY",
        "RECHARGE_REQUIRED",
        "CONTINUITY_UNKNOWN",
        "REVEALED_POSSIBLE_BYPASS",
        "PROGRESS_POSSIBLE_ONLY",
        "RELEASE_POSSIBLE_ONLY",
        "IMPORTANCE_UNKNOWN",
        "SAFETY_CAP_UNKNOWN",
    }
)


def policy_closure_sha256() -> str | None:
    """Return the standard checked policy closure without embedding itself."""
    try:
        root = Path(__file__).resolve().parent
        paths = [
            path
            for path in root.glob("*.py")
            if not path.name.startswith("test")
        ]
        paths.extend((root / "runtime" / "main.py", root / "deck.csv"))
        if any(not path.is_file() for path in paths):
            return None
        rows = []
        for path in paths:
            payload = path.read_bytes()
            rows.append(
                f"{path.relative_to(root).as_posix()}\0"
                f"{hashlib.sha256(payload).hexdigest().upper()}\0"
                f"{len(payload)}\n"
            )
        return hashlib.sha256(
            "".join(sorted(rows)).encode("utf-8")
        ).hexdigest().upper()
    except Exception:
        return None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=repr,
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _safe(value: Any) -> Any:
    try:
        return json.loads(_canonical(value))
    except Exception:
        return repr(value)


def _action_type(value: Any) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def fresh_state() -> dict[str, Any]:
    return {
        "boundary_fingerprint": None,
        "last_turn": None,
        "last_result": None,
        "last_step": None,
        "last_turn_action_count": None,
        "last_deck_counts": None,
        "last_truncated": False,
        "last_observation_fingerprint": None,
        "callback_ordinal": 0,
        "trading_pending": None,
        "holds": {},
        "closed_holds": {},
        "open_outcomes": {},
        "power_pro_seen_serials": set(),
        "power_pro_unavailable_serials": set(),
        "family_marker_ids": set(),
        "revealed_boss": False,
    }


SHADOW_STATE = fresh_state()


def reset() -> None:
    SHADOW_STATE.clear()
    SHADOW_STATE.update(fresh_state())


def _players(raw: dict[str, Any]):
    current = raw.get("current")
    players = current.get("players") if isinstance(current, dict) else None
    owner = _int(current.get("yourIndex")) if isinstance(current, dict) else None
    if (
        not isinstance(players, list)
        or len(players) != 2
        or owner not in (0, 1)
        or not all(isinstance(player, dict) for player in players)
    ):
        return None
    return current, players[owner], players[1 - owner], owner, 1 - owner


def _public_structure_reasons(raw: dict[str, Any]) -> list[str]:
    parsed = _players(raw)
    if parsed is None:
        return ["PUBLIC_STATE_INVALID"]
    current, mine, theirs, _, _ = parsed
    reasons = []
    current_int_rules = {
        "turn": lambda value: value >= 0,
        "turnActionCount": lambda value: value >= 0,
        "result": lambda value: value in (-1, 0, 1),
        "firstPlayer": lambda value: value in (0, 1),
        "yourIndex": lambda value: value in (0, 1),
    }
    for field, valid in current_int_rules.items():
        value = current.get(field)
        if type(value) is not int or not valid(value):
            reasons.append(f"CURRENT_{field.upper()}_INVALID")
    if not isinstance(current.get("stadium"), list):
        reasons.append("CURRENT_STADIUM_INVALID")
    for field in (
        "energyAttached",
        "retreated",
        "stadiumPlayed",
        "supporterPlayed",
    ):
        if type(current.get(field)) is not bool:
            reasons.append(f"CURRENT_{field.upper()}_INVALID")
    in_play_serials = []
    for label, player, owner in (
        ("OWN", mine, parsed[3]),
        ("OPPONENT", theirs, parsed[4]),
    ):
        for field in ("active", "bench", "discard", "prize"):
            if not isinstance(player.get(field), list) or (
                field in ("active", "bench", "discard")
                and not all(
                    isinstance(card, dict) for card in player.get(field, [])
                )
            ):
                reasons.append(f"{label}_{field.upper()}_INVALID")
        for field in ("deckCount", "handCount"):
            value = player.get(field)
            if type(value) is not int or value < 0:
                reasons.append(f"{label}_{field.upper()}_INVALID")
        bench_max = player.get("benchMax")
        if type(bench_max) is not int or bench_max < 0:
            reasons.append(f"{label}_BENCHMAX_INVALID")
        elif isinstance(player.get("bench"), list) and len(player["bench"]) > bench_max:
            reasons.append(f"{label}_BENCH_EXCEEDS_MAX")
        active = player.get("active")
        if isinstance(active, list) and len(active) > 1:
            reasons.append(f"{label}_ACTIVE_CARDINALITY_INVALID")
        for field in (
            "asleep",
            "burned",
            "confused",
            "paralyzed",
            "poisoned",
        ):
            if type(player.get(field)) is not bool:
                reasons.append(f"{label}_{field.upper()}_INVALID")
        for zone_name in ("active", "bench"):
            zone = player.get(zone_name)
            if not isinstance(zone, list):
                continue
            for index, card in enumerate(zone):
                if not isinstance(card, dict):
                    continue
                prefix = f"{label}_{zone_name.upper()}_{index}"
                card_id = card.get("id")
                serial = card.get("serial")
                hp = card.get("hp")
                max_hp = card.get("maxHp")
                if type(card_id) is not int or card_id < 0:
                    reasons.append(f"{prefix}_ID_INVALID")
                if type(serial) is not int or serial < 0:
                    reasons.append(f"{prefix}_SERIAL_INVALID")
                else:
                    in_play_serials.append(serial)
                if (
                    type(card.get("playerIndex")) is not int
                    or card["playerIndex"] != owner
                ):
                    reasons.append(f"{prefix}_OWNER_INVALID")
                if type(hp) is not int or hp <= 0:
                    reasons.append(f"{prefix}_HP_INVALID")
                if (
                    type(max_hp) is not int
                    or type(hp) is not int
                    or max_hp < hp
                ):
                    reasons.append(f"{prefix}_MAXHP_INVALID")
                if type(card.get("appearThisTurn")) is not bool:
                    reasons.append(f"{prefix}_APPEAR_INVALID")
                energies = card.get("energies")
                energy_cards = card.get("energyCards")
                if (
                    not isinstance(energies, list)
                    or any(
                        type(unit) is not int or unit < 0 for unit in energies
                    )
                ):
                    reasons.append(f"{prefix}_ENERGIES_INVALID")
                if (
                    not isinstance(energy_cards, list)
                    or not isinstance(energies, list)
                    or len(energy_cards) != len(energies)
                ):
                    reasons.append(f"{prefix}_ENERGYCARDS_INVALID")
                components = (
                    ("ENERGY", energy_cards),
                    ("PRE_EVOLUTION", card.get("preEvolution")),
                    ("TOOL", card.get("tools")),
                )
                for component_name, components_value in components:
                    if not isinstance(components_value, list):
                        reasons.append(
                            f"{prefix}_{component_name}_LIST_INVALID"
                        )
                        continue
                    for component_index, component in enumerate(
                        components_value
                    ):
                        component_prefix = (
                            f"{prefix}_{component_name}_{component_index}"
                        )
                        if not isinstance(component, dict):
                            reasons.append(
                                f"{component_prefix}_INVALID"
                            )
                            continue
                        component_id = component.get("id")
                        component_serial = component.get("serial")
                        if (
                            type(component_id) is not int
                            or component_id < 0
                        ):
                            reasons.append(
                                f"{component_prefix}_ID_INVALID"
                            )
                        if (
                            type(component_serial) is not int
                            or component_serial < 0
                        ):
                            reasons.append(
                                f"{component_prefix}_SERIAL_INVALID"
                            )
                        else:
                            in_play_serials.append(component_serial)
                        if (
                            type(component.get("playerIndex")) is not int
                            or component["playerIndex"] != owner
                        ):
                            reasons.append(
                                f"{component_prefix}_OWNER_INVALID"
                            )
    if len(in_play_serials) != len(set(in_play_serials)):
        reasons.append("PUBLIC_IN_PLAY_SERIAL_DUPLICATE")
    return sorted(set(reasons))


def _zone(player: dict[str, Any], name: str) -> list[dict[str, Any]] | None:
    value = player.get(name)
    if not isinstance(value, list) or not all(isinstance(card, dict) for card in value):
        return None
    return value


def _card_id(card: Any) -> int | None:
    if not isinstance(card, dict):
        return None
    return _int(card.get("id", card.get("cardId")))


def _serial(card: Any) -> int | None:
    return _int(card.get("serial")) if isinstance(card, dict) else None


def _card_snapshot(card: Any) -> dict[str, Any] | None:
    if not isinstance(card, dict):
        return None
    energies = card.get("energies")
    energy_cards = card.get("energyCards")
    tools = card.get("tools")
    pre_evolution = card.get("preEvolution")
    return {
        "card_id": _card_id(card),
        "serial": _serial(card),
        "player_index": _int(card.get("playerIndex")),
        "hp": _int(card.get("hp")),
        "max_hp": _int(card.get("maxHp")),
        "appear_this_turn": card.get("appearThisTurn"),
        "energies": list(energies) if isinstance(energies, list) else None,
        "energy_card_ids": [
            _card_id(energy) for energy in energy_cards
        ]
        if isinstance(energy_cards, list)
        else None,
        "energy_serials": [
            _serial(energy) for energy in energy_cards
        ]
        if isinstance(energy_cards, list)
        else None,
        "tool_card_ids": [_card_id(tool) for tool in tools]
        if isinstance(tools, list)
        else None,
        "tool_serials": [
            _serial(tool) for tool in tools
        ]
        if isinstance(tools, list)
        else None,
        "pre_evolution_card_ids": [
            _card_id(stage) for stage in pre_evolution
        ]
        if isinstance(pre_evolution, list)
        else None,
        "pre_evolution_serials": [
            _serial(stage) for stage in pre_evolution
        ]
        if isinstance(pre_evolution, list)
        else None,
    }


def _all_visible_cards(raw: dict[str, Any]) -> Iterable[dict[str, Any]]:
    parsed = _players(raw)
    if parsed is None:
        return
    current, mine, theirs, _, _ = parsed
    for player, own in ((mine, True), (theirs, False)):
        for zone_name in ("active", "bench", "discard", "hand"):
            if zone_name == "hand" and not own:
                continue
            zone = player.get(zone_name)
            if not isinstance(zone, list):
                continue
            for card in zone:
                if isinstance(card, dict):
                    yield card
                    for nested in ("preEvolution", "energyCards", "tools"):
                        children = card.get(nested)
                        if isinstance(children, list):
                            for child in children:
                                if isinstance(child, dict):
                                    yield child
    stadium = current.get("stadium")
    if isinstance(stadium, list):
        for card in stadium:
            if isinstance(card, dict):
                yield card


def _public_board_material(raw: dict[str, Any]) -> dict[str, Any]:
    parsed = _players(raw)
    if parsed is None:
        return {"invalid": True}
    current, mine, theirs, owner, _ = parsed

    def player_material(player: dict[str, Any], own: bool) -> dict[str, Any]:
        return {
            "active": [_card_snapshot(card) for card in (player.get("active") or [])],
            "bench": [_card_snapshot(card) for card in (player.get("bench") or [])],
            "discard": [
                (_card_id(card), _serial(card))
                for card in (player.get("discard") or [])
                if isinstance(card, dict)
            ],
            "hand": (
                [
                    (_card_id(card), _serial(card))
                    for card in (player.get("hand") or [])
                    if isinstance(card, dict)
                ]
                if own and isinstance(player.get("hand"), list)
                else None
            ),
            "hand_count": _int(player.get("handCount")),
            "deck_count": _int(player.get("deckCount")),
            "bench_max": _int(player.get("benchMax")),
            "prize_count": len(player.get("prize") or [])
            if isinstance(player.get("prize"), list)
            else None,
            "status": [
                player.get(name)
                for name in ("asleep", "paralyzed", "confused", "poisoned", "burned")
            ],
        }

    return {
        "turn": _int(current.get("turn")),
        "turn_action_count": _int(current.get("turnActionCount")),
        "your_index": owner,
        "first_player": _int(current.get("firstPlayer")),
        "result": _int(current.get("result")),
        "turn_flags": {
            name: current.get(name)
            for name in (
                "energyAttached",
                "retreated",
                "stadiumPlayed",
                "supporterPlayed",
            )
        },
        "mine": player_material(mine, True),
        "theirs": player_material(theirs, False),
        "stadium": [
            (_card_id(card), _serial(card))
            for card in (current.get("stadium") or [])
            if isinstance(card, dict)
        ],
    }


def _public_state_material(
    raw: dict[str, Any], option_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Mirror the checked metric writer's canonical CALL_START snapshot."""
    del option_rows
    current = raw.get("current") if isinstance(raw.get("current"), dict) else {}
    select = raw.get("select") if isinstance(raw.get("select"), dict) else {}
    players = current.get("players")
    owner = _int(current.get("yourIndex"))
    mine = (
        players[owner]
        if isinstance(players, list)
        and owner in (0, 1)
        and owner < len(players)
        and isinstance(players[owner], dict)
        else {}
    )
    opponent_index = 1 - owner if owner in (0, 1) else -1
    theirs = (
        players[opponent_index]
        if isinstance(players, list)
        and 0 <= opponent_index < len(players)
        and isinstance(players[opponent_index], dict)
        else {}
    )
    own_active = (
        mine["active"][0]
        if isinstance(mine.get("active"), list)
        and mine["active"]
        and isinstance(mine["active"][0], dict)
        else None
    )
    opponent_active = (
        theirs["active"][0]
        if isinstance(theirs.get("active"), list)
        and theirs["active"]
        and isinstance(theirs["active"][0], dict)
        else None
    )
    options = (
        select.get("option")
        if isinstance(select.get("option"), list)
        else []
    )

    def pair(card: Any) -> list[int | None] | None:
        if not isinstance(card, dict):
            return None
        return [_card_id(card), _serial(card)]

    def pairs(cards: Any) -> list[list[int | None] | None]:
        return [pair(card) for card in cards] if isinstance(cards, list) else []

    def attached(card: Any) -> list[list[int | None] | None]:
        if not isinstance(card, dict):
            return []
        energy_cards = card.get("energyCards")
        if isinstance(energy_cards, list):
            return pairs(energy_cards)
        energies = card.get("energies")
        if isinstance(energies, list):
            return [[_int(unit), None] for unit in energies]
        return []

    def option_source(option: dict[str, Any]) -> dict[str, Any] | None:
        option_owner = _int(option.get("playerIndex"))
        if option_owner not in (0, 1):
            option_owner = owner
        index = _int(option.get("index"))
        area = _int(option.get("area"))
        option_type = _int(option.get("type"))
        if index is None or index < 0:
            return None
        if option_type in (PLAY, 8, EVOLVE):
            area = 2
            option_owner = owner
        player = (
            players[option_owner]
            if isinstance(players, list)
            and option_owner in (0, 1)
            and option_owner < len(players)
            and isinstance(players[option_owner], dict)
            else {}
        )
        sources = None
        if area == 2:
            sources = player.get("hand")
        elif area == 3:
            sources = player.get("discard")
        elif area == ACTIVE_AREA:
            sources = player.get("active")
        elif area == BENCH_AREA:
            sources = player.get("bench")
        elif area == 6:
            sources = player.get("prize")
        elif area == 7:
            sources = current.get("stadium")
        elif area == 12:
            sources = current.get("looking")
        elif area == 1:
            sources = select.get("deck")
        if (
            isinstance(sources, list)
            and 0 <= index < len(sources)
            and isinstance(sources[index], dict)
        ):
            return sources[index]
        return None

    option_identities = []
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            continue
        source = option_source(option)
        card_id = _int(option.get("cardId"))
        serial = _int(option.get("serial"))
        if source is not None:
            card_id = _card_id(source) or card_id
            serial = _serial(source) or serial
        option_identities.append(
            {
                "type": _int(option.get("type")),
                "area": _int(option.get("area")),
                "index": _int(option.get("index")),
                "player_index": _int(option.get("playerIndex")),
                "card_id": card_id,
                "serial": serial,
                "attack_id": _int(option.get("attackId")),
                "in_play_area": _int(option.get("inPlayArea")),
                "in_play_index": _int(option.get("inPlayIndex")),
            }
        )
    option_identities.sort(key=_canonical)
    logs = [
        {str(key): _safe(value) for key, value in log.items()}
        for log in (raw.get("logs") or [])
        if isinstance(log, dict)
    ] if isinstance(raw.get("logs"), list) else []
    serial_fields = (
        "type",
        "playerIndex",
        "cardId",
        "cardIdActive",
        "cardIdBench",
        "cardIdBefore",
        "cardIdAfter",
        "cardIdTarget",
        "attackId",
        "serial",
        "serialActive",
        "serialBench",
        "serialBefore",
        "serialAfter",
        "serialTarget",
        "fromArea",
        "toArea",
        "value",
        "putDamageCounter",
    )
    select = raw.get("select") if isinstance(raw.get("select"), dict) else {}
    return {
        "turn": _int(current.get("turn")),
        "turn_action_count": _int(current.get("turnActionCount")),
        "your_index": owner,
        "first_player": _int(current.get("firstPlayer")),
        "result": _int(current.get("result")),
        "context": _int(select.get("context")),
        "select_type": _int(select.get("type")),
        "min_count": _int(select.get("minCount")),
        "max_count": _int(select.get("maxCount")),
        "option_count": len(options),
        "options": option_identities,
        "own_hand": pairs(mine.get("hand")),
        "own_active": pair(own_active),
        "own_active_hp": (
            _int(own_active.get("hp")) if own_active else None
        ),
        "own_active_energy": attached(own_active),
        "own_bench": pairs(mine.get("bench")),
        "own_discard": pairs(mine.get("discard")),
        "opponent_active": pair(opponent_active),
        "opponent_active_hp": (
            _int(opponent_active.get("hp")) if opponent_active else None
        ),
        "opponent_active_energy": attached(opponent_active),
        "logs_raw": logs,
        "log_serial_fields": [
            {
                field: _safe(log[field])
                for field in serial_fields
                if field in log
            }
            for log in logs
            if any(field in log for field in serial_fields[9:15])
        ],
    }


def _resolve_option_card(
    raw: dict[str, Any], option: dict[str, Any]
) -> dict[str, Any] | None:
    parsed = _players(raw)
    if parsed is None:
        return None
    current, mine, theirs, owner, _ = parsed
    option_type = _int(option.get("type"))
    area = _int(option.get("area"))
    index = _int(option.get("index"))
    player_index = _int(option.get("playerIndex"))
    if player_index not in (0, 1):
        player_index = owner
    player = current["players"][player_index]
    zone_name = None
    if option_type in (PLAY, EVOLVE) or area == 2:
        zone_name = "hand"
    elif area == BENCH_AREA or (
        option_type == PROMOTION_OPTION and area == BENCH_AREA
    ):
        zone_name = "bench"
    elif area == ACTIVE_AREA:
        zone_name = "active"
    zone = player.get(zone_name) if zone_name else None
    if (
        isinstance(zone, list)
        and index is not None
        and 0 <= index < len(zone)
        and isinstance(zone[index], dict)
    ):
        return zone[index]
    card_id = _int(option.get("cardId"))
    serial = _int(option.get("serial"))
    if card_id is not None or serial is not None:
        return {
            "id": card_id,
            "serial": serial,
            "playerIndex": player_index,
        }
    return None


def semantic_option_key(
    raw: dict[str, Any], option: Any
) -> dict[str, Any] | None:
    if not isinstance(option, dict):
        return None
    card = _resolve_option_card(raw, option)
    return {
        "type": _int(option.get("type")),
        "area": _int(option.get("area")),
        "card_id": _card_id(card),
        "serial": _serial(card),
        "attack_id": _int(option.get("attackId")),
        "ability_id": _int(option.get("abilityId")),
        "number": _int(option.get("number")),
        "player_index": _int(option.get("playerIndex")),
        "in_play_area": _int(option.get("inPlayArea")),
        "in_play_index": _int(option.get("inPlayIndex")),
    }


def _option_rows(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    select = raw.get("select")
    options = select.get("option") if isinstance(select, dict) else None
    if not isinstance(options, list):
        return [], ["OPTION_LIST_INVALID"]
    reasons = []
    if not isinstance(select, dict) or any(
        _int(select.get(field)) is None
        for field in ("context", "type", "minCount", "maxCount")
    ):
        reasons.append("SELECT_REQUIRED_FIELD_INVALID")
    rows = []
    seen: dict[str, int] = {}
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            reasons.append("OPTION_NOT_OBJECT")
            continue
        key = semantic_option_key(raw, option)
        option_type = _int(option.get("type"))
        if key is None or option_type is None:
            reasons.append("OPTION_SEMANTIC_KEY_UNKNOWN")
            continue
        card = _resolve_option_card(raw, option)
        if option_type == PROMOTION_OPTION and (
            _int(option.get("area")) != BENCH_AREA
            or _int(option.get("index")) is None
            or _int(option.get("playerIndex")) not in (0, 1)
            or card is None
            or _serial(card) is None
        ):
            reasons.append("PROMOTION_OPTION_REQUIRED_FIELD_INVALID")
        elif option_type == ABILITY and (
            _int(option.get("area")) != ACTIVE_AREA
            or _int(option.get("index")) is None
            or card is None
            or _serial(card) is None
        ):
            reasons.append("ABILITY_OPTION_REQUIRED_FIELD_INVALID")
        elif option_type == ATTACK and _int(option.get("attackId")) is None:
            reasons.append("ATTACK_OPTION_REQUIRED_FIELD_INVALID")
        elif option_type in (PLAY, EVOLVE) and (
            _int(option.get("index")) is None
            or card is None
            or _serial(card) is None
        ):
            reasons.append("CARD_OPTION_REQUIRED_FIELD_INVALID")
        canonical = _canonical(key)
        if canonical in seen:
            reasons.append("DUPLICATE_SEMANTIC_OPTION")
        seen[canonical] = index
        rows.append({"index": index, "key": key, "option": option})
    return rows, sorted(set(reasons))


def semantic_action_keys(
    raw: dict[str, Any], action: Any, option_rows: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    if not isinstance(action, (list, tuple)):
        return None
    keys = []
    by_index = {row["index"]: row["key"] for row in option_rows}
    for value in action:
        if type(value) is not int or value not in by_index:
            return None
        keys.append(copy.deepcopy(by_index[value]))
    return keys


def _public_state_fingerprint(
    raw: dict[str, Any], option_rows: list[dict[str, Any]]
) -> str:
    return fingerprint(_public_state_material(raw, option_rows))


def _initialize_boundary(
    raw: dict[str, Any], state: dict[str, Any], observation_fp: str
) -> str:
    parsed = _players(raw)
    if parsed is None:
        return fingerprint({"invalid": True})
    current, _, _, owner, _ = parsed
    turn = _int(current.get("turn"))
    result = _int(current.get("result"))
    step = _int(raw.get("step"))
    action_count = _int(current.get("turnActionCount"))
    deck_counts = tuple(
        _int(player.get("deckCount")) for player in current.get("players", [])
    )
    last_turn = _int(state.get("last_turn"))
    last_result = _int(state.get("last_result"))
    last_step = _int(state.get("last_step"))
    last_action_count = _int(state.get("last_turn_action_count"))
    last_decks = state.get("last_deck_counts")
    reset_needed = state.get("boundary_fingerprint") is None
    if last_turn is not None and turn is not None and turn < last_turn:
        reset_needed = True
    if last_result is not None and last_result != -1 and result == -1:
        reset_needed = True
    if last_step is not None and step is not None and step < last_step:
        reset_needed = True
    if (
        last_turn is not None
        and turn is not None
        and turn <= last_turn
        and last_action_count is not None
        and action_count is not None
        and action_count < last_action_count
    ):
        reset_needed = True
    if (
        isinstance(last_decks, tuple)
        and len(last_decks) == len(deck_counts)
        and any(
            before is not None
            and after is not None
            and after > before + 10
            for before, after in zip(last_decks, deck_counts)
        )
    ):
        reset_needed = True
    if state.get("last_truncated") is True:
        reset_needed = True
    if reset_needed:
        visible = sorted(
            (
                _int(card.get("playerIndex")),
                _card_id(card),
                _serial(card),
            )
            for card in _all_visible_cards(raw)
            if _serial(card) is not None
        )
        boundary = {
            "first_player": _int(current.get("firstPlayer")),
            "your_index": owner,
            "entry_turn": turn,
            "entry_step": step,
            "entry_turn_action_count": action_count,
            "entry_deck_counts": deck_counts,
            "entry_truncated": raw.get("truncated") is True,
            "entry_visible_serials": visible,
            "entry_public_fingerprint": observation_fp,
        }
        state.clear()
        state.update(fresh_state())
        state["boundary_fingerprint"] = fingerprint(boundary)
    state["last_turn"] = turn
    state["last_result"] = result
    state["last_step"] = step
    state["last_turn_action_count"] = action_count
    state["last_deck_counts"] = deck_counts
    state["last_truncated"] = raw.get("truncated") is True
    return str(state["boundary_fingerprint"])


def _update_callback_ordinal(
    state: dict[str, Any], observation_fp: str
) -> int:
    if state.get("last_observation_fingerprint") != observation_fp:
        state["callback_ordinal"] = int(state.get("callback_ordinal", 0)) + 1
        state["last_observation_fingerprint"] = observation_fp
    return int(state["callback_ordinal"])


def _metadata_name(card_id: int | None) -> str:
    data = getattr(policy, "card_table", {}).get(card_id)
    return str(getattr(data, "name", "") or "")


def _update_public_evidence(raw: dict[str, Any], state: dict[str, Any]) -> None:
    parsed = _players(raw)
    if parsed is None:
        return
    _, _, theirs, _, _ = parsed
    current_unavailable = set()
    for card in _all_visible_cards(raw):
        card_id = _card_id(card)
        serial = _serial(card)
        if card_id in POWER_PRO_FAMILY:
            state["family_marker_ids"].add(card_id)
        if card_id == PREMIUM_POWER_PRO and serial is not None:
            state["power_pro_seen_serials"].add(serial)
    discard = theirs.get("discard")
    if isinstance(discard, list):
        for card in discard:
            card_id = _card_id(card)
            serial = _serial(card)
            if card_id == PREMIUM_POWER_PRO and serial is not None:
                current_unavailable.add(serial)
            if "boss" in _metadata_name(card_id).lower():
                state["revealed_boss"] = True
    state["power_pro_unavailable_serials"] = current_unavailable


def _position_for_serial(
    player: dict[str, Any], serial: int | None
) -> tuple[str | None, dict[str, Any] | None]:
    if serial is None:
        return None, None
    for zone_name in ("active", "bench", "discard", "hand"):
        zone = player.get(zone_name)
        if not isinstance(zone, list):
            continue
        for card in zone:
            if not isinstance(card, dict):
                continue
            if _serial(card) == serial:
                return zone_name.upper(), card
            for nested_name in ("preEvolution", "energyCards", "tools"):
                nested = card.get(nested_name)
                if not isinstance(nested, list):
                    continue
                if any(
                    isinstance(child, dict) and _serial(child) == serial
                    for child in nested
                ):
                    return f"{zone_name.upper()}_{nested_name.upper()}", card
    return None, None


def _event_once(
    outcome: dict[str, Any], event: str, **fields: Any
) -> None:
    row = {
        "event": event,
        "decision_id": outcome["decision_id"],
        **fields,
    }
    key = _canonical(row)
    seen = outcome.setdefault("event_keys", set())
    if key not in seen:
        seen.add(key)
        outcome.setdefault("events", []).append(row)


def _prize_count(player: dict[str, Any]) -> int | None:
    prize = player.get("prize")
    return len(prize) if isinstance(prize, list) else None


def _attack_logs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    logs = raw.get("logs")
    if not isinstance(logs, list):
        return []
    return [
        row
        for row in logs
        if isinstance(row, dict)
        and _int(row.get("type")) == 15
        and _int(row.get("attackId")) is not None
    ]


def _advance_outcomes(
    raw: dict[str, Any],
    c2_trace: Any,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Advance natural-agreement outcomes from later public callbacks."""
    parsed = _players(raw)
    if parsed is None:
        return []
    current, mine, theirs, owner, _ = parsed
    turn = _int(current.get("turn"))
    result = _int(current.get("result"))
    current_distance = None
    if isinstance(c2_trace, dict):
        current_distance = _distance_quality(c2_trace.get("best_primary_route"))
    emitted: list[dict[str, Any]] = []

    for outcome in state.get("open_outcomes", {}).values():
        if not isinstance(outcome, dict):
            continue
        wall_serial = _int(outcome.get("wall_serial"))
        protected_serials = {
            serial
            for serial in outcome.get("protected_serials", [])
            if type(serial) is int
        }
        wall_zone, wall_card = _position_for_serial(mine, wall_serial)
        protected_positions = [
            _position_for_serial(mine, serial)
            for serial in sorted(protected_serials)
        ]
        protected_cards = [
            card for _, card in protected_positions if isinstance(card, dict)
        ]
        protected_card = protected_cards[0] if protected_cards else None
        active = mine.get("active")
        active_card = (
            active[0]
            if isinstance(active, list)
            and len(active) == 1
            and isinstance(active[0], dict)
            else None
        )
        active_serial = _serial(active_card)
        wall_hp = _int(wall_card.get("hp")) if wall_card is not None else None
        previous_hp = _int(outcome.get("last_wall_hp"))
        wall_was_active = outcome.get("wall_was_active") is True

        if wall_zone == "ACTIVE":
            _event_once(
                outcome,
                "WALL_ACTIVE",
                wall_serial=wall_serial,
                turn=turn,
            )
            outcome["wall_was_active"] = True
            if (
                previous_hp is not None
                and wall_hp is not None
                and wall_hp < previous_hp
            ):
                _event_once(
                    outcome,
                    "WALL_ATTACKED",
                    wall_serial=wall_serial,
                    hp_before=previous_hp,
                    hp_after=wall_hp,
                    turn=turn,
                )
                _event_once(
                    outcome,
                    "WALL_SURVIVED",
                    wall_serial=wall_serial,
                    hp=wall_hp,
                    turn=turn,
                )
            elif (
                wall_was_active
                and turn is not None
                and _int(outcome.get("last_turn")) is not None
                and turn > int(outcome["last_turn"])
            ):
                _event_once(
                    outcome,
                    "OPPONENT_REFUSED",
                    wall_serial=wall_serial,
                    turn=turn,
                )
                _event_once(
                    outcome,
                    "WALL_SURVIVED",
                    wall_serial=wall_serial,
                    hp=wall_hp,
                    turn=turn,
                )
        elif wall_zone == "DISCARD" and wall_was_active:
            _event_once(
                outcome,
                "WALL_ATTACKED",
                wall_serial=wall_serial,
                hp_before=previous_hp,
                hp_after=0,
                turn=turn,
            )
            _event_once(
                outcome,
                "WALL_KO",
                wall_serial=wall_serial,
                turn=turn,
            )

        kind = outcome.get("kind")
        released = wall_was_active and wall_zone != "ACTIVE"
        if kind == RUN_AWAY and wall_zone != "ACTIVE":
            released = True
        if released and wall_zone != "DISCARD":
            release_event = (
                "TRADING_PLACES_RELEASED"
                if kind == SACRIFICE
                else "RUN_AWAY_RELEASED"
            )
            _event_once(
                outcome,
                release_event,
                source_serial=wall_serial,
                turn=turn,
            )
            if active_serial is not None and active_serial != wall_serial:
                _event_once(
                    outcome,
                    "PROMOTION_DESTINATION",
                    destination_serial=active_serial,
                    destination_card_id=_card_id(active_card),
                    protected_destination=(
                        active_serial in protected_serials
                        or any(
                            _serial(stage) in protected_serials
                            for stage in (active_card.get("preEvolution") or [])
                            if isinstance(stage, dict)
                        )
                    ),
                    turn=turn,
                )

        previous_protected = outcome.get("last_protected_snapshot")
        current_protected = _card_snapshot(protected_card)
        if (
            isinstance(previous_protected, dict)
            and isinstance(current_protected, dict)
            and (
                current_protected.get("card_id")
                != previous_protected.get("card_id")
                or len(current_protected.get("energy_serials") or [])
                > len(previous_protected.get("energy_serials") or [])
                or len(current_protected.get("pre_evolution_serials") or [])
                > len(previous_protected.get("pre_evolution_serials") or [])
            )
        ):
            _event_once(
                outcome,
                "PROTECTED_LINE_PROGRESS",
                protected_serials=sorted(protected_serials),
                turn=turn,
            )
        previous_distance = outcome.get("last_distance")
        if (
            previous_distance is not None
            and current_distance is not None
            and current_distance < previous_distance
        ):
            _event_once(
                outcome,
                "DISTANCE_IMPROVED",
                distance_before=_safe(previous_distance),
                distance_after=_safe(current_distance),
                turn=turn,
            )

        previous_protected_hp = _int(
            (previous_protected or {}).get("hp")
            if isinstance(previous_protected, dict)
            else None
        )
        current_protected_hp = _int(
            (current_protected or {}).get("hp")
            if isinstance(current_protected, dict)
            else None
        )
        protected_discarded = any(
            zone == "DISCARD" for zone, _ in protected_positions
        )
        if wall_zone == "ACTIVE" and (
            (
                previous_protected_hp is not None
                and current_protected_hp is not None
                and current_protected_hp < previous_protected_hp
            )
            or protected_discarded
        ):
            _event_once(
                outcome,
                "GUST_OR_SNIPE_BYPASS",
                protected_serials=sorted(protected_serials),
                turn=turn,
            )

        protected_top_serials = {
            _serial(card) for card in protected_cards if _serial(card) is not None
        }
        protected_top_serials.update(protected_serials)
        for attack in _attack_logs(raw):
            if (
                _int(attack.get("playerIndex")) == owner
                and _int(attack.get("serial")) in protected_top_serials
            ):
                _event_once(
                    outcome,
                    "PROTECTED_ATTACKER_ATTACKED",
                    attacker_serial=_int(attack.get("serial")),
                    attack_id=_int(attack.get("attackId")),
                    turn=turn,
                )
                outcome["protected_attack_turn"] = turn

        opponent_active = _zone(theirs, "active")
        opponent_card = (
            opponent_active[0]
            if opponent_active is not None
            and len(opponent_active) == 1
            else None
        )
        protected_attack_turn = _int(outcome.get("protected_attack_turn"))
        if (
            protected_attack_turn is not None
            and turn is not None
            and turn > protected_attack_turn
            and outcome.get("opponent_continuity") == REPEATABLE_READY
            and _serial(opponent_card)
            == _int(outcome.get("opponent_attacker_serial"))
        ):
            _event_once(
                outcome,
                "OPPONENT_CONTINUITY_OBSERVED",
                attacker_serial=_serial(opponent_card),
                turn=turn,
            )

        own_prizes = _prize_count(mine)
        previous_prizes = _int(outcome.get("last_own_prizes"))
        if (
            own_prizes is not None
            and previous_prizes is not None
            and own_prizes != previous_prizes
        ):
            _event_once(
                outcome,
                "PRIZE_DELTA",
                player_index=owner,
                before=previous_prizes,
                after=own_prizes,
                delta=own_prizes - previous_prizes,
                turn=turn,
            )
        if result is not None and result != -1:
            _event_once(outcome, "GAME_END", result=result, turn=turn)
            outcome["complete"] = True
        if raw.get("truncated") is True:
            _event_once(outcome, "TRUNCATION", turn=turn)
            outcome["complete"] = True

        outcome["last_turn"] = turn
        if wall_hp is not None:
            outcome["last_wall_hp"] = wall_hp
        if current_protected is not None:
            outcome["last_protected_snapshot"] = current_protected
        if current_distance is not None:
            outcome["last_distance"] = current_distance
        if own_prizes is not None:
            outcome["last_own_prizes"] = own_prizes
        emitted.extend(_safe(outcome.get("events") or []))
    return emitted


def _open_outcome(
    state: dict[str, Any],
    trace: dict[str, Any],
    chosen_kind: str,
    chosen: dict[str, Any],
    active: dict[str, Any] | None,
    mine: dict[str, Any],
    turn: int | None,
) -> None:
    decision_id = trace.get("decision_id")
    if not isinstance(decision_id, str):
        return
    wall_serial = (
        _serial(active)
        if chosen_kind == RUN_AWAY
        else _int((chosen.get("wall") or {}).get("serial"))
    )
    protected = trace.get("protected_line")
    protected_serials = set()
    if isinstance(protected, dict):
        protected_serials.update(
            serial
            for serial in protected.get("stack_serials", [])
            if type(serial) is int
        )
        top_serial = _int(protected.get("top_serial"))
        if top_serial is not None:
            protected_serials.add(top_serial)
    _, protected_card = (
        _position_for_serial(mine, min(protected_serials))
        if protected_serials
        else (None, None)
    )
    wall_zone, wall_card = _position_for_serial(mine, wall_serial)
    outcome = {
        "decision_id": decision_id,
        "kind": chosen_kind,
        "wall_serial": wall_serial,
        "protected_serials": sorted(protected_serials),
        "entry_turn": turn,
        "last_turn": turn,
        "last_wall_hp": (
            _int(wall_card.get("hp")) if wall_card is not None else None
        ),
        "wall_was_active": wall_zone == "ACTIVE",
        "last_protected_snapshot": _card_snapshot(protected_card),
        "last_distance": _distance_quality(trace.get("distance_before")),
        "last_own_prizes": _prize_count(mine),
        "opponent_attacker_serial": _int(
            (trace.get("threat") or {}).get("attacker_serial")
            if isinstance(trace.get("threat"), dict)
            else None
        ),
        "opponent_continuity": trace.get("continuity"),
        "events": [],
        "event_keys": set(),
        "complete": False,
    }
    _event_once(outcome, "PARENT_AGREEMENT", turn=turn)
    if wall_zone == "ACTIVE" and chosen_kind != RUN_AWAY:
        _event_once(
            outcome,
            "WALL_ACTIVE",
            wall_serial=wall_serial,
            turn=turn,
        )
    state.setdefault("open_outcomes", {})[decision_id] = outcome
    trace.setdefault("outcome_events", []).extend(_safe(outcome["events"]))


def _power_pro_ledger(
    raw: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    current = raw.get("current") if isinstance(raw, dict) else {}
    return {
        "boundary_certified": state.get("boundary_fingerprint") is not None,
        "ambiguous": False,
        "same_battle_power_pro_seen": bool(state["power_pro_seen_serials"]),
        "family_marker_ids": sorted(state["family_marker_ids"]),
        "power_pro_seen_serials": sorted(state["power_pro_seen_serials"]),
        "committed_current_turn": [],
        "unavailable": sorted(state["power_pro_unavailable_serials"]),
        "last_attack_by_serial": {},
        "turn": _int(current.get("turn")),
    }


def _attack_continuity(
    attack_id: int,
    text: str,
    attacker: dict[str, Any],
    attacker_state: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    exact = public_damage.ATTACK_ROWS.get(attack_id)
    continuity = (
        str(exact["continuity"]) if exact is not None else UNKNOWN
    )
    self_damage = (
        _int(exact.get("self_damage")) if exact is not None else None
    )
    normalized = (text or "").lower().replace("’", "'")
    if any(
        marker in normalized
        for marker in (
            "can't use this attack during your next turn",
            "cannot use this attack during your next turn",
            "can't attack during your next turn",
        )
    ):
        continuity = RECHARGE_REQUIRED
    details = {
        "self_damage": self_damage,
        "attacker_hp_before": _int(attacker.get("hp")),
        "poisoned": attacker_state.get("poisoned"),
        "burned": attacker_state.get("burned"),
        "next_turn_hp_floor": None,
    }
    if continuity != REPEATABLE_READY:
        return continuity, details
    hp = _int(attacker.get("hp"))
    if hp is None or self_damage is None:
        return UNKNOWN, details
    next_hp = hp - self_damage
    if next_hp <= 0:
        details["next_turn_hp_floor"] = next_hp
        return NO_READY_ATTACK, details
    poisoned = attacker_state.get("poisoned")
    burned = attacker_state.get("burned")
    if type(poisoned) is not bool or type(burned) is not bool:
        return UNKNOWN, details
    base_checkup_damage = (10 if poisoned else 0) + (20 if burned else 0)
    next_hp -= base_checkup_damage
    details["next_turn_hp_floor"] = next_hp
    if next_hp <= 0:
        return NO_READY_ATTACK, details
    # Public modifiers can raise Checkup damage. A statused survivor is kept
    # UNKNOWN instead of being over-certified as repeatably ready.
    if poisoned or burned:
        return UNKNOWN, details
    return REPEATABLE_READY, details


def _public_bypass_kind(text: str) -> str | None:
    normalized = " ".join(
        str(text or "")
        .replace("’", "'")
        .replace("é", "e")
        .replace("\xa0", " ")
        .lower()
        .split()
    )
    if (
        "switch out your opponent's active pokemon to the bench."
        in normalized
        or "switch in 1 of your opponent's benched pokemon to the active spot"
        in normalized
    ):
        return "CERTIFIED_GUST"
    opponent_bench = (
        "opponent's benched pokemon" in normalized
        or "opponent's pokemon" in normalized
    )
    damage_effect = any(
        marker in normalized
        for marker in (" damage ", "damage counter", "knock out")
    )
    conditional = any(
        marker in normalized
        for marker in (
            "flip a coin",
            " if ",
            "you may",
            "up to",
            "for each",
            "discard",
            "choose 2",
            "choose 3",
        )
    )
    if opponent_bench and damage_effect and not conditional:
        return "CERTIFIED_BENCH_SNIPE"
    if (
        "opponent's benched pokemon" in normalized
        or ("benched pokemon" in normalized and damage_effect)
        or "switch out your opponent's active pokemon" in normalized
        or "switch in 1 of your opponent's benched pokemon" in normalized
    ):
        return "POSSIBLE_PUBLIC_BYPASS"
    return None


def _damage_with_premium(
    primitive: dict[str, Any], premium: int
) -> int:
    damage = int(primitive["printed_damage"]) + premium
    if primitive.get("damage_counter_placement") is True:
        return damage
    if not primitive["ignores_weakness_resistance"]:
        if primitive["weakness"] == primitive["attack_type"]:
            damage *= 2
        if primitive["resistance"] == primitive["attack_type"]:
            damage = max(0, damage - 30)
    return damage


def _lunatone_prerequisite_state(
    opponent_field: dict[str, Any], opponent: int
) -> bool | None:
    bench = _zone(opponent_field, "bench")
    if bench is None:
        return None
    lunatones = [card for card in bench if _card_id(card) == 675]
    if not lunatones:
        return False
    data = getattr(policy, "card_table", {}).get(675)
    if (
        data is None
        or _int(getattr(data, "cardId", None)) != 675
        or getattr(data, "name", None) != "Lunatone"
        or _int(getattr(data, "cardType", None)) != 0
        or getattr(data, "basic", None) is not True
        or getattr(data, "stage1", None) is not False
        or getattr(data, "stage2", None) is not False
        or any(
            not _public_pokemon_complete(card, opponent)
            for card in lunatones
        )
    ):
        return None
    return True


def _threat_analysis(
    raw: dict[str, Any],
    defender: dict[str, Any] | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "status": UNKNOWN,
        "attack_id": None,
        "attacker_serial": None,
        "damage_floor": None,
        "damage_cap": None,
        "final_safety_cap": None,
        "continuity": UNKNOWN,
        "floor_ko": False,
        "cap_ko": False,
        "parser_source": (
            "_cumulative_parent._bridge_retaliation_attack_damage"
        ),
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "unsupported_reasons": [],
        "attack_text": None,
        "next_turn_survival": None,
        "bypass_capability": "NONE",
        "bypass_attacks": [],
    }
    parsed = _players(raw)
    if parsed is None or defender is None:
        base["unsupported_reasons"].append("PUBLIC_STATE_INVALID")
        return base
    current, _, theirs, _, opponent = parsed
    opponent_active = _zone(theirs, "active")
    if opponent_active is None or len(opponent_active) != 1:
        base["unsupported_reasons"].append("OPPONENT_ACTIVE_INVALID")
        return base
    attacker_raw = opponent_active[0]
    if _serial(attacker_raw) is None or _int(attacker_raw.get("playerIndex")) != opponent:
        base["unsupported_reasons"].append("OPPONENT_ACTIVE_IDENTITY_INVALID")
        return base
    defender_id = _card_id(defender)
    attacker_id = _card_id(attacker_raw)
    defender_data = getattr(policy, "card_table", {}).get(defender_id)
    attacker_data = getattr(policy, "card_table", {}).get(attacker_id)
    if defender_data is None or attacker_data is None:
        base["unsupported_reasons"].append("CARD_METADATA_UNKNOWN")
        return base
    if any(bool(theirs.get(flag)) for flag in ("asleep", "paralyzed")):
        base.update({"status": "SUPPORTED", "continuity": NO_READY_ATTACK})
        return base
    if bool(theirs.get("confused")):
        base["unsupported_reasons"].append("CONFUSION_COIN_UNSUPPORTED")
        return base
    if current.get("stadium"):
        base["unsupported_reasons"].append("STADIUM_MODIFIER_UNSUPPORTED")
        return base
    if any(
        type(theirs.get(field)) is not bool
        for field in (
            "asleep",
            "burned",
            "confused",
            "paralyzed",
            "poisoned",
        )
    ):
        base["unsupported_reasons"].append(
            "OPPONENT_STATUS_FIELDS_INVALID"
        )
        return base
    tools = attacker_raw.get("tools")
    if not isinstance(tools, list) or any(_card_id(tool) != 1159 for tool in tools):
        base["unsupported_reasons"].append("ATTACKER_TOOL_MODIFIER_UNSUPPORTED")
        return base
    energy_units = _public_energy_units(attacker_raw)
    if energy_units is None:
        base["unsupported_reasons"].append("ATTACK_ENERGY_METADATA_UNSUPPORTED")
        return base

    premium_cap = 0
    premium_details = None
    if attacker_id in POWER_PRO_FAMILY:
        envelope = public_damage.premium_power_pro_envelope(
            _power_pro_ledger(raw, state),
            phase="future",
        )
        premium_details = envelope.get("premium_power_pro_multiplicity")
        if envelope.get("status") != "CERTIFIED":
            base["unsupported_reasons"].append("SAFETY_CAP_UNKNOWN")
            return base
        premium_cap = int(envelope.get("premium_cap") or 0)

    rows = []
    bypass_rows = []
    attack_ids = getattr(attacker_data, "attacks", None)
    if not isinstance(attack_ids, list) or len(attack_ids) != len(set(attack_ids)):
        base["unsupported_reasons"].append("ATTACK_LIST_UNSUPPORTED")
        return base
    for attack_id in attack_ids:
        attack = getattr(policy, "attack_table", {}).get(attack_id)
        if attack is None:
            base["unsupported_reasons"].append("ATTACK_METADATA_UNKNOWN")
            continue
        payable = policy._bridge_retaliation_can_pay(
            energy_units, tuple(int(unit) for unit in attack.energies)
        )
        if payable is not True:
            continue
        bypass_kind = _public_bypass_kind(str(attack.text or ""))
        if bypass_kind is not None:
            bypass_rows.append(
                {
                    "attack_id": int(attack_id),
                    "kind": bypass_kind,
                    "text": str(attack.text or ""),
                    "payment": "EXACT_PUBLIC",
                }
            )
        primitive, failure = policy._bridge_retaliation_attack_damage(
            attacker_data, attack, defender_data
        )
        exact_public_row = public_damage.ATTACK_ROWS.get(int(attack_id))
        prerequisite_zero = False
        if (
            exact_public_row is not None
            and exact_public_row.get("requires_lunatone") is True
        ):
            prerequisite = _lunatone_prerequisite_state(
                theirs, opponent
            )
            if prerequisite is None:
                base["unsupported_reasons"].append(
                    "LUNATONE_PREREQUISITE_UNSUPPORTED"
                )
                continue
            prerequisite_zero = prerequisite is False
        if int(attack_id) == POWERFUL_HAND_ATTACK:
            hand_count = _int(theirs.get("handCount"))
            effect_blocked = _powerful_hand_target_blocked(raw, defender)
            if (
                hand_count is not None
                and effect_blocked is not None
                and int(attack.damage) == 0
                and "damage counter" in str(attack.text or "").lower()
            ):
                exact_damage = 0 if effect_blocked else 20 * hand_count
                primitive = {
                    "printed_damage": exact_damage,
                    "attack_type": None,
                    "weakness": None,
                    "resistance": None,
                    "ignores_weakness_resistance": True,
                    "certified_damage": exact_damage,
                    "damage_counter_placement": True,
                }
                failure = None
        elif (
            primitive is None
            and exact_public_row is not None
            and int(exact_public_row["base"]) == int(attack.damage)
        ):
            attack_type = int(attacker_data.energyType)
            weakness = (
                None
                if getattr(defender_data, "weakness", None) is None
                else int(defender_data.weakness)
            )
            resistance = (
                None
                if getattr(defender_data, "resistance", None) is None
                else int(defender_data.resistance)
            )
            damage = int(attack.damage)
            ignores = bool(exact_public_row["ignore_wr"])
            if not ignores:
                if weakness == attack_type:
                    damage *= 2
                if resistance == attack_type:
                    damage = max(0, damage - 30)
            primitive = {
                "printed_damage": int(attack.damage),
                "attack_type": attack_type,
                "weakness": weakness,
                "resistance": resistance,
                "ignores_weakness_resistance": ignores,
                "certified_damage": damage,
                "damage_counter_placement": False,
            }
            failure = None
        if primitive is None:
            base["unsupported_reasons"].append(
                str(failure or "FIXED_DAMAGE_UNSUPPORTED")
            )
            continue
        if prerequisite_zero:
            floor = 0
            primitive = {
                "printed_damage": 0,
                "attack_type": None,
                "weakness": None,
                "resistance": None,
                "ignores_weakness_resistance": True,
                "certified_damage": 0,
                "damage_counter_placement": False,
            }
        elif int(attack_id) == POWERFUL_HAND_ATTACK:
            hand_count = _int(theirs.get("handCount"))
            effect_blocked = _powerful_hand_target_blocked(raw, defender)
            if (
                hand_count is None
                or effect_blocked is None
                or int(attack.damage) != 0
                or "damage counter" not in str(attack.text or "").lower()
            ):
                base["unsupported_reasons"].append(
                    "POWERFUL_HAND_FORMULA_OR_BLOCKER_UNSUPPORTED"
                )
                continue
            floor = 0 if effect_blocked else 20 * hand_count
            primitive = {
                "printed_damage": floor,
                "attack_type": None,
                "weakness": None,
                "resistance": None,
                "ignores_weakness_resistance": True,
                "certified_damage": floor,
                "damage_counter_placement": True,
            }
        else:
            floor = int(primitive["certified_damage"])
        cap = (
            0
            if prerequisite_zero
            else _damage_with_premium(primitive, premium_cap)
        )
        continuity, survival = _attack_continuity(
            int(attack_id),
            str(attack.text or ""),
            attacker_raw,
            theirs,
        )
        if continuity == UNKNOWN:
            base["unsupported_reasons"].append(
                f"ATTACK_CONTINUATION_UNKNOWN:{int(attack_id)}"
            )
        rows.append(
            {
                "attack_id": int(attack_id),
                "floor": floor,
                "cap": cap,
                "continuity": continuity,
                "next_turn_survival": survival,
                "text": str(attack.text or ""),
            }
        )
    base["bypass_capability"] = (
        "EXACT_ARMED"
        if any(
            row["kind"] in ("CERTIFIED_GUST", "CERTIFIED_BENCH_SNIPE")
            for row in bypass_rows
        )
        else "POSSIBLE_PUBLIC"
        if bypass_rows
        else "NONE"
    )
    base["bypass_attacks"] = _safe(bypass_rows)
    if not rows:
        if not base["unsupported_reasons"]:
            base.update({"status": "SUPPORTED", "continuity": NO_READY_ATTACK})
        return base
    hp = _int(defender.get("hp"))
    chosen = sorted(
        rows,
        key=lambda row: (
            -int(
                hp is not None
                and row["continuity"] == REPEATABLE_READY
                and row["floor"] >= hp
            ),
            -int(row["continuity"] == REPEATABLE_READY),
            -row["floor"],
            -row["cap"],
            row["attack_id"],
        ),
    )[0]
    final_safety_cap = max(row["cap"] for row in rows)
    base.update(
        {
            "status": "SUPPORTED",
            "attack_id": chosen["attack_id"],
            "attacker_serial": _serial(attacker_raw),
            "damage_floor": chosen["floor"],
            "damage_cap": chosen["cap"],
            "final_safety_cap": final_safety_cap,
            "continuity": chosen["continuity"],
            "floor_ko": hp is not None and chosen["floor"] >= hp,
            "cap_ko": hp is not None and final_safety_cap >= hp,
            "attack_text": chosen["text"],
            "next_turn_survival": _safe(
                chosen.get("next_turn_survival")
            ),
            "premium_power_pro_multiplicity": premium_details,
            "evidenced_policy_cap": final_safety_cap,
            "unsupported_reasons": sorted(set(base["unsupported_reasons"])),
        }
    )
    return base


def _line_from_c2(
    c2_trace: Any, exposed: dict[str, Any] | None
) -> dict[str, Any]:
    result = {
        "protected_line": None,
        "importance": "UNKNOWN_IMPORTANCE",
        "distance_before": None,
        "distance_without_line": None,
        "unsupported_reasons": [],
    }
    if not isinstance(c2_trace, dict):
        result["unsupported_reasons"].append("C2_TRACE_MISSING")
        return result
    if c2_trace.get("metric_exception") is not None:
        result["unsupported_reasons"].append("C2_METRIC_EXCEPTION")
        return result
    exposed_serial = _serial(exposed)
    rows = c2_trace.get("route_rows")
    importance_rows = c2_trace.get("line_importance_rows")
    if not isinstance(rows, list) or not isinstance(importance_rows, list):
        result["unsupported_reasons"].append("C2_DISTANCE_ROWS_INVALID")
        return result
    selected = None
    if exposed_serial is not None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            if exposed_serial == row.get("top_serial") or exposed_serial in (
                row.get("stack_serials") or []
            ):
                selected = row
                break
    if selected is None:
        live = [
            row
            for row in rows
            if isinstance(row, dict) and row.get("location") != "VIRTUAL"
        ]
        if len(live) == 1:
            selected = live[0]
    if selected is None:
        result["unsupported_reasons"].append("NO_LIVE_PROTECTED_LINE")
        return result
    importance = next(
        (
            row
            for row in importance_rows
            if isinstance(row, dict)
            and row.get("line_id") == selected.get("line_id")
        ),
        None,
    )
    live_rows = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("location") != "VIRTUAL"
    ]
    selected_quality = _distance_quality(selected.get("primary_distance"))
    if selected_quality is None:
        result["unsupported_reasons"].append(
            "C2_DISTANCE_TUPLE_INVALID"
        )
    structural_importance = "UNKNOWN_IMPORTANCE"
    structural_reason = "IMPORTANCE_UNPROVEN"
    if len(live_rows) == 1 and selected_quality is not None:
        structural_importance = "UNIQUE"
        structural_reason = "ONLY_LIVE_ALAKAZAM_LINE"
    elif isinstance(importance, dict):
        reported = importance.get("importance")
        before_quality = _distance_quality(selected.get("primary_distance"))
        after_quality = _distance_quality(
            importance.get("after_removal_primary")
        )
        if reported == "REDUNDANT":
            ready_other = any(
                row is not selected
                and (
                    quality := _distance_quality(
                        row.get("primary_distance")
                    )
                )
                is not None
                and quality[0] == 0
                and quality[1] == 0
                for row in live_rows
            )
            nonworsening = (
                before_quality is not None
                and after_quality is not None
                and after_quality <= before_quality
            )
            if ready_other and nonworsening:
                structural_importance = "REDUNDANT"
                structural_reason = "PUBLIC_READY_BACKUP_EXISTS"
        elif reported == "IMPORTANT":
            if (
                before_quality is not None
                and after_quality is not None
                and after_quality > before_quality
            ):
                structural_importance = "IMPORTANT"
                structural_reason = "REMOVAL_WORSENS_PUBLIC_ROUTE"
    result.update(
        {
            "protected_line": {
                key: _safe(selected.get(key))
                for key in (
                    "line_id",
                    "location",
                    "top_card_id",
                    "top_serial",
                    "stack_serials",
                    "stack_card_ids",
                    "energy_units",
                )
            },
            "importance": structural_importance,
            "importance_reason": structural_reason,
            "distance_before": _safe(selected.get("primary_distance")),
            "distance_without_line": _safe(
                importance.get("after_removal_primary")
                if isinstance(importance, dict)
                else None
            ),
            "_row": selected,
        }
    )
    return result


def _distance_quality(distance: Any) -> tuple[Any, ...] | None:
    if not isinstance(distance, dict):
        return None
    rank = {"CERTIFIED": 0, "POSSIBLE": 1, "IMPOSSIBLE": 2}.get(
        distance.get("route_class")
    )
    numeric_fields = (
        distance.get("turn_delay"),
        distance.get("main_actions"),
        distance.get("forced_prompts"),
    )
    if (
        rank is None
        or any(type(value) is not int or value < 0 for value in numeric_fields)
    ):
        return None
    witness = distance.get("witness")
    if not isinstance(witness, dict):
        return None
    template = witness.get("template")
    steps = witness.get("steps")
    missing = witness.get("missing_requirements")
    unsupported = witness.get("unsupported_reasons")
    if (
        not isinstance(template, str)
        or not template
        or not isinstance(steps, list)
        or not isinstance(missing, list)
        or not isinstance(unsupported, list)
        or any(not isinstance(value, str) or not value for value in missing)
        or any(
            not isinstance(value, str) or not value
            for value in unsupported
        )
        or len(missing) != len(set(missing))
        or len(unsupported) != len(set(unsupported))
        or (
            distance.get("route_class") == "CERTIFIED"
            and (missing or unsupported)
        )
    ):
        return None
    return (
        rank,
        numeric_fields[0],
        numeric_fields[1],
        numeric_fields[2],
        len(missing),
        len(unsupported),
        _canonical(witness),
    )


def _exact_prize_value(raw: dict[str, Any], card: dict[str, Any]) -> int | None:
    data = getattr(policy, "card_table", {}).get(_card_id(card))
    energy_cards = card.get("energyCards")
    tools = card.get("tools")
    if (
        data is None
        or not isinstance(energy_cards, list)
        or not isinstance(tools, list)
    ):
        return None
    value = 3 if bool(getattr(data, "megaEx", False)) else 2 if bool(
        getattr(data, "ex", False)
    ) else 1
    value -= sum(1 for energy in energy_cards if _card_id(energy) == 12)
    if (
        any(_card_id(tool) == 1172 for tool in tools)
        and "Lillie" in str(getattr(data, "name", ""))
    ):
        value -= 1
    return max(0, value)


def _public_energy_units(card: dict[str, Any]) -> tuple[int, ...] | None:
    energies = card.get("energies")
    energy_cards = card.get("energyCards")
    owner = _int(card.get("playerIndex"))
    if (
        not isinstance(energies, list)
        or not isinstance(energy_cards, list)
        or len(energies) != len(energy_cards)
        or not all(isinstance(energy, dict) for energy in energy_cards)
        or owner not in (0, 1)
        or any(
            _card_id(energy) is None
            or _serial(energy) is None
            or _int(energy.get("playerIndex")) != owner
            for energy in energy_cards
        )
        or len({_serial(energy) for energy in energy_cards})
        != len(energy_cards)
    ):
        return None
    units = tuple(_int(unit) for unit in energies)
    if any(unit is None for unit in units):
        return None
    return tuple(int(unit) for unit in units)


def _public_pokemon_complete(
    card: dict[str, Any], owner: int
) -> bool:
    energies = card.get("energies")
    energy_cards = card.get("energyCards")
    pre_evolution = card.get("preEvolution")
    tools = card.get("tools")
    components = (
        list(energy_cards)
        + list(pre_evolution)
        + list(tools)
        if all(
            isinstance(value, list)
            for value in (energy_cards, pre_evolution, tools)
        )
        else None
    )
    return bool(
        _card_id(card) is not None
        and _serial(card) is not None
        and _int(card.get("playerIndex")) == owner
        and _int(card.get("hp")) is not None
        and int(card["hp"]) > 0
        and _int(card.get("maxHp")) is not None
        and int(card["maxHp"]) >= int(card["hp"])
        and type(card.get("appearThisTurn")) is bool
        and isinstance(energies, list)
        and isinstance(energy_cards, list)
        and len(energies) == len(energy_cards)
        and all(type(unit) is int and unit >= 0 for unit in energies)
        and isinstance(pre_evolution, list)
        and isinstance(tools, list)
        and components is not None
        and all(
            isinstance(component, dict)
            and _card_id(component) is not None
            and _serial(component) is not None
            and _int(component.get("playerIndex")) == owner
            for component in components
        )
        and len(
            [_serial(card)]
            + [_serial(component) for component in components]
        )
        == len(
            set(
                [_serial(card)]
                + [_serial(component) for component in components]
            )
        )
    )


def _repelling_veil_state(
    raw: dict[str, Any], target: dict[str, Any]
) -> bool | None:
    parsed = _players(raw)
    target_owner = _int(target.get("playerIndex"))
    if parsed is None or target_owner not in (0, 1):
        return None
    current = parsed[0]
    target_field = current["players"][target_owner]
    active = _zone(target_field, "active")
    bench = _zone(target_field, "bench")
    if active is None or bench is None:
        return None
    sources = [
        card
        for card in active + bench
        if _card_id(card) == TEAM_ROCKETS_ARTICUNO
    ]
    if not sources:
        return False
    source_data = getattr(policy, "card_table", {}).get(
        TEAM_ROCKETS_ARTICUNO
    )
    skills = getattr(source_data, "skills", None)
    if (
        source_data is None
        or _int(getattr(source_data, "cardId", None))
        != TEAM_ROCKETS_ARTICUNO
        or getattr(source_data, "name", None)
        != "Team Rocket's Articuno"
        or _int(getattr(source_data, "cardType", None)) != 0
        or getattr(source_data, "basic", None) is not True
        or getattr(source_data, "stage1", None) is not False
        or getattr(source_data, "stage2", None) is not False
        or not isinstance(skills, list)
        or len(skills) != 1
        or getattr(skills[0], "name", None) != " Repelling Veil"
        or getattr(skills[0], "text", None) != REPELLING_VEIL_TEXT
        or any(
            not _public_pokemon_complete(source, target_owner)
            for source in sources
        )
    ):
        return None
    target_data = getattr(policy, "card_table", {}).get(_card_id(target))
    if (
        not _public_pokemon_complete(target, target_owner)
        or target_data is None
        or _int(getattr(target_data, "cardId", None)) != _card_id(target)
        or _int(getattr(target_data, "cardType", None)) != 0
        or type(getattr(target_data, "basic", None)) is not bool
        or type(getattr(target_data, "stage1", None)) is not bool
        or type(getattr(target_data, "stage2", None)) is not bool
        or sum(
            (
                target_data.basic,
                target_data.stage1,
                target_data.stage2,
            )
        )
        != 1
        or not isinstance(getattr(target_data, "name", None), str)
    ):
        return None
    if target_data.basic:
        pre_evolution = target.get("preEvolution")
        suffix = target_data.name[len(TEAM_ROCKET_NAME_PREFIX) :]
        if (
            getattr(target_data, "evolvesFrom", None) is not None
            or pre_evolution
        ):
            return None
        return bool(
            target_data.name.startswith(TEAM_ROCKET_NAME_PREFIX)
            and suffix
        )
    return False


def _powerful_hand_target_blocked(
    raw: dict[str, Any],
    target: dict[str, Any],
) -> bool | None:
    energy_cards = target.get("energyCards")
    if not isinstance(energy_cards, list):
        return None
    energy_ids = {_card_id(card) for card in energy_cards}
    if None in energy_ids:
        return None
    energy_blocked = MIST_ENERGY in energy_ids
    target_data = getattr(policy, "card_table", {}).get(_card_id(target))
    target_type = _int(getattr(target_data, "energyType", None))
    energy_blocked = energy_blocked or (
        ROCK_FIGHTING_ENERGY in energy_ids and target_type == 6
    )
    veil = _repelling_veil_state(raw, target)
    if veil is None:
        return None
    return energy_blocked or veil


def _route_binds_attack(
    distance: Any,
    *,
    attack_id: int,
    serial: int | None,
    location: str | None,
) -> bool:
    if not isinstance(distance, dict):
        return False
    witness = distance.get("witness")
    steps = witness.get("steps") if isinstance(witness, dict) else None
    if not isinstance(steps, list):
        return False
    exact_attack = any(
        isinstance(step, dict)
        and step.get("kind") == "ATTACK_READY"
        and _int(step.get("attack_id", step.get("attackId"))) == attack_id
        for step in steps
    )
    exact_promotion = any(
        isinstance(step, dict)
        and step.get("kind") == "EXACT_PROMOTION"
        and _int(step.get("serial")) == serial
        for step in steps
    )
    run_away_promotion = (
        any(
            isinstance(step, dict)
            and step.get("kind") == "RUN_AWAY_DRAW"
            and _int(step.get("draw_count")) == 3
            and isinstance(step.get("option_key"), (tuple, list, dict))
            for step in steps
        )
        and any(
            isinstance(step, dict)
            and step.get("kind") == "UNIQUE_POST_RUN_AWAY_PROMOTION"
            and _int(step.get("target_serial")) == serial
            for step in steps
        )
    )
    return exact_attack or (
        location == "BENCH"
        and (exact_promotion or run_away_promotion)
        and attack_id in (SUPER_PSY_BOLT_ATTACK, POWERFUL_HAND_ATTACK)
    )


def _exact_attack_conversion(
    raw: dict[str, Any],
    card: dict[str, Any] | None,
    distance: Any,
    *,
    location: str | None,
    hand_bonus: int = 0,
) -> dict[str, Any]:
    result = {
        "certified": False,
        "reason": "RELEASE_ATTACK_UNSUPPORTED",
        "attacker_serial": _serial(card),
        "attacker_card_id": _card_id(card),
        "attacker_current_hp": (
            _int(card.get("hp")) if isinstance(card, dict) else None
        ),
        "attack_id": None,
        "damage": None,
        "target_serial": None,
        "target_current_hp": None,
        "target_prize_value": None,
        "attack_binding": None,
    }
    parsed = _players(raw)
    if parsed is None or not isinstance(card, dict):
        return result
    _, mine, theirs, owner, _ = parsed
    opponent_active = _zone(theirs, "active")
    if opponent_active is None or len(opponent_active) != 1:
        result["reason"] = "RELEASE_TARGET_NOT_EXACT"
        return result
    target = opponent_active[0]
    target_hp = _int(target.get("hp"))
    if _serial(target) is None or target_hp is None or target_hp <= 0:
        result["reason"] = "RELEASE_TARGET_IDENTITY_OR_HP_INVALID"
        return result
    card_id = _card_id(card)
    data = getattr(policy, "card_table", {}).get(card_id)
    attacks = getattr(data, "attacks", None)
    if not isinstance(attacks, list) or len(attacks) != 1:
        result["reason"] = "RELEASE_ATTACK_NOT_UNIQUE"
        return result
    attack_id = _int(attacks[0])
    attack = getattr(policy, "attack_table", {}).get(attack_id)
    if attack_id not in (SUPER_PSY_BOLT_ATTACK, POWERFUL_HAND_ATTACK) or attack is None:
        result["reason"] = "RELEASE_ATTACK_NOT_ALLOWLISTED"
        return result
    units = _public_energy_units(card)
    try:
        payable = (
            units is not None
            and policy._bridge_retaliation_can_pay(units, attack.energies)
            is True
        )
    except Exception:
        payable = False
    if not payable:
        result["reason"] = "RELEASE_ATTACK_PAYMENT_UNCERTIFIED"
        return result
    if not _route_binds_attack(
        distance,
        attack_id=attack_id,
        serial=_serial(card),
        location=location,
    ):
        result["reason"] = "RELEASE_ATTACK_OPTION_UNBOUND"
        return result

    if attack_id == POWERFUL_HAND_ATTACK:
        blocked = _powerful_hand_target_blocked(raw, target)
        hand_count = _int(mine.get("handCount"))
        if blocked is not False or hand_count is None:
            result["reason"] = (
                "POWERFUL_HAND_EFFECT_BLOCKED"
                if blocked is True
                else "POWERFUL_HAND_BLOCKER_OR_HAND_UNKNOWN"
            )
            return result
        if type(hand_bonus) is not int or hand_bonus < 0:
            result["reason"] = "POWERFUL_HAND_DRAW_BONUS_INVALID"
            return result
        damage = 20 * (hand_count + hand_bonus)
        binding = "DAMAGE_COUNTER_FORMULA_AND_UNIQUE_ATTACK"
    else:
        target_data = getattr(policy, "card_table", {}).get(_card_id(target))
        if target_data is None or int(attack.damage) != 30:
            result["reason"] = "SUPER_PSY_BOLT_METADATA_UNSUPPORTED"
            return result
        damage = 30
        attack_type = _int(getattr(data, "energyType", None))
        weakness = _int(getattr(target_data, "weakness", None))
        resistance = _int(getattr(target_data, "resistance", None))
        if weakness == attack_type:
            damage *= 2
        if resistance == attack_type:
            damage = max(0, damage - 30)
        binding = "FIXED_DAMAGE_UNIQUE_ATTACK"
    target_prizes = _exact_prize_value(raw, target)
    result.update(
        {
            "certified": damage >= target_hp and target_prizes is not None,
            "reason": (
                "EXACT_CURRENT_TARGET_KO"
                if damage >= target_hp and target_prizes is not None
                else "RELEASE_ATTACK_NOT_EXACT_KO"
            ),
            "attack_id": attack_id,
            "damage": damage,
            "target_serial": _serial(target),
            "target_current_hp": target_hp,
            "target_prize_value": target_prizes,
            "attack_binding": binding,
        }
    )
    return result


def _validated_release_candidates(
    raw: dict[str, Any],
    line: dict[str, Any],
    c2_trace: Any,
) -> list[dict[str, Any]]:
    parsed = _players(raw)
    if parsed is None:
        return []
    _, mine, _, _, _ = parsed
    rows = c2_trace.get("route_rows") if isinstance(c2_trace, dict) else None
    if not isinstance(rows, list):
        return []
    protected_id = (line.get("protected_line") or {}).get("line_id")
    candidates = []
    for row in rows:
        if not isinstance(row, dict) or row.get("location") == "VIRTUAL":
            continue
        distance = row.get("primary_distance")
        quality = _distance_quality(distance)
        if (
            quality is None
            or quality[0] != 0
            or quality[1] != 0
        ):
            continue
        serial = _int(row.get("top_serial"))
        matches = [
            card
            for zone_name in ("active", "bench")
            for card in (mine.get(zone_name) or [])
            if isinstance(card, dict) and _serial(card) == serial
        ]
        if len(matches) != 1 or _card_id(matches[0]) != _int(row.get("top_card_id")):
            continue
        conversion = _exact_attack_conversion(
            raw,
            matches[0],
            distance,
            location=str(row.get("location")),
        )
        if conversion["certified"]:
            conversion["line_id"] = row.get("line_id")
            conversion["is_protected_line"] = row.get("line_id") == protected_id
            candidates.append(conversion)
    return candidates


def _attachments_enable_or_strengthen_attack(
    attacker: dict[str, Any],
    max_attachments: int,
) -> tuple[bool | None, int | None, int | None]:
    if type(max_attachments) is not int or max_attachments < 0:
        return None, None, None
    data = getattr(policy, "card_table", {}).get(_card_id(attacker))
    attacks = getattr(data, "attacks", None)
    units = _public_energy_units(attacker)
    if data is None or not isinstance(attacks, list) or units is None:
        return None, None, None
    enabled = []
    try:
        for attack_id in attacks:
            attack = getattr(policy, "attack_table", {}).get(_int(attack_id))
            costs = getattr(attack, "energies", None)
            if attack is None or not isinstance(costs, list):
                return None, None, None
            payable_now = policy._bridge_retaliation_can_pay(
                units, costs
            )
            if payable_now is None:
                return None, None, None
            text = " ".join(
                str(getattr(attack, "text", "") or "").lower().split()
            )
            energy_scaled = any(
                marker in text
                for marker in (
                    "for each energy attached to this pokémon",
                    "for each energy attached to this pokemon",
                    "more damage for each energy",
                    "additional energy attached",
                )
            )
            if payable_now is True:
                if energy_scaled and max_attachments > 0:
                    enabled.append(
                        (
                            1,
                            -int(getattr(attack, "damage", 0) or 0),
                            int(attack_id),
                        )
                    )
                continue
            frontier = {tuple(units)}
            for attachment_count in range(1, max_attachments + 1):
                frontier = {
                    existing + (energy_type,)
                    for existing in frontier
                    for energy_type in range(0, 11)
                }
                if any(
                    policy._bridge_retaliation_can_pay(
                        candidate_units, costs
                    )
                    is True
                    for candidate_units in frontier
                ):
                    enabled.append(
                        (
                            attachment_count,
                            -int(getattr(attack, "damage", 0) or 0),
                            int(attack_id),
                        )
                    )
                    break
    except Exception:
        return None, None, None
    if not enabled:
        return False, None, None
    attachment_count, _, attack_id = sorted(enabled)[0]
    return True, attack_id, attachment_count


def _one_attachment_enables_attack(
    attacker: dict[str, Any],
) -> tuple[bool | None, int | None]:
    enabled, attack_id, _ = _attachments_enable_or_strengthen_attack(
        attacker, 1
    )
    return enabled, attack_id


def _attack_has_board_or_energy_effect(
    threat: dict[str, Any],
) -> bool | None:
    attack_id = _int(threat.get("attack_id"))
    attack = getattr(policy, "attack_table", {}).get(attack_id)
    if attack is None:
        return None
    text = " ".join(str(getattr(attack, "text", "") or "").lower().split())
    if not text:
        return False
    board_or_energy_markers = (
        "attach ",
        "attached energy",
        "discard an energy",
        "discard 1 energy",
        "move an energy",
        "move 1 energy",
        "switch ",
        "to your bench",
        "to the bench",
        "from your discard pile",
    )
    return any(marker in text for marker in board_or_energy_markers)


def _future_opponent_attack(
    raw: dict[str, Any],
    defender: dict[str, Any],
    state: dict[str, Any],
    *,
    mandatory_draws: int,
    prior_attachment_turns: int = 0,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    parsed = _players(raw)
    if (
        parsed is None
        or type(mandatory_draws) is not int
        or mandatory_draws < 0
        or type(prior_attachment_turns) is not int
        or prior_attachment_turns < 0
    ):
        return None, None, "FUTURE_OPPONENT_STATE_INVALID"
    _, _, theirs, _, opponent = parsed
    active = _zone(theirs, "active")
    if active is None or len(active) != 1:
        return None, None, "FUTURE_OPPONENT_ACTIVE_INVALID"
    attachment_turns = prior_attachment_turns + (
        1 if mandatory_draws > 0 else 0
    )
    enables, attack_id, attachment_count = (
        _attachments_enable_or_strengthen_attack(
            active[0], attachment_turns
        )
    )
    if enables is None:
        return None, None, "FUTURE_ATTACHMENT_ENVELOPE_UNKNOWN"
    if enables:
        return (
            None,
            None,
            "FUTURE_CUMULATIVE_ATTACHMENTS_ENABLE_ATTACK:"
            f"{attack_id}:{attachment_count}",
        )
    hand_count = theirs.get("handCount")
    deck_count = theirs.get("deckCount")
    if (
        type(hand_count) is not int
        or hand_count < 0
        or type(deck_count) is not int
        or deck_count < mandatory_draws
    ):
        return None, None, "FUTURE_MANDATORY_DRAW_UNCERTIFIED"
    projected = copy.deepcopy(raw)
    projected_theirs = projected["current"]["players"][opponent]
    projected_theirs["handCount"] = hand_count + mandatory_draws
    projected_theirs["deckCount"] = deck_count - mandatory_draws
    threat = _threat_analysis(projected, defender, state)
    effect = _attack_has_board_or_energy_effect(threat)
    if effect is None:
        return None, None, "FUTURE_ATTACK_EFFECT_UNKNOWN"
    if effect:
        return (
            None,
            None,
            f"FUTURE_ATTACK_ALTERS_BOARD_OR_ENERGY:{threat.get('attack_id')}",
        )
    return projected, threat, None


def _project_delay_one_protected_line(
    raw: dict[str, Any],
    line: dict[str, Any],
    c2_trace: Any,
    state: dict[str, Any],
    wall: dict[str, Any],
    *,
    branch: str,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    str | None,
]:
    distance = line.get("distance_before")
    quality = _distance_quality(distance)
    if quality is None or quality[0] != 0 or quality[1] != 1:
        return None, None, None, "TRADING_DELAY_ONE_DISTANCE_INVALID"
    if branch not in (
        DELAY_ONE_ATTACK_BRANCH,
        DELAY_ONE_REFUSAL_BRANCH,
    ):
        return None, None, None, "TRADING_DELAY_ONE_BRANCH_INVALID"
    row = line.get("_row")
    witness = distance.get("witness") if isinstance(distance, dict) else None
    steps = witness.get("steps") if isinstance(witness, dict) else None
    if not isinstance(row, dict) or not isinstance(steps, list):
        return None, None, None, "TRADING_DELAY_ONE_WITNESS_INVALID"
    parsed = _players(raw)
    if parsed is None:
        return None, None, None, "PUBLIC_STATE_INVALID"
    _, mine, theirs, owner, opponent = parsed
    serial = _int(row.get("top_serial"))
    matches = [
        card
        for zone_name in ("active", "bench")
        for card in (mine.get(zone_name) or [])
        if isinstance(card, dict) and _serial(card) == serial
    ]
    if len(matches) != 1 or not _public_pokemon_complete(matches[0], owner):
        return None, None, None, "TRADING_DELAY_ONE_LINE_INVALID"
    wall_serial = _serial(wall)
    wall_hp = _int(wall.get("hp"))
    if (
        wall_serial is None
        or wall_hp is None
        or not _public_pokemon_complete(wall, owner)
    ):
        return None, None, None, "TRADING_DELAY_ONE_WALL_INVALID"

    details = {
        "branch": branch,
        "wall_serial": wall_serial,
        "wall_ko": False,
        "wall_attack_id": None,
        "wall_attack_damage": None,
        "opponent_prizes_before": None,
        "opponent_prizes_after": None,
        "forced_promotion_serial": None,
        "mandatory_draw_count": 1,
        "opponent_mandatory_draw_count": 0,
        "prior_attachment_turns": 0,
        "consumed_serials": [],
    }
    if branch == DELAY_ONE_ATTACK_BRANCH:
        projected = _project_wall_state(raw, wall)
        if projected is None:
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_WALL_PROJECTION_INVALID",
            )
        wall_threat = _threat_analysis(projected, wall, state)
        floor = _int(wall_threat.get("damage_floor"))
        cap = _int(wall_threat.get("damage_cap"))
        effect = _attack_has_board_or_energy_effect(wall_threat)
        if effect is None:
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_EFFECT_UNKNOWN",
            )
        if effect:
            return (
                None,
                None,
                None,
                f"FUTURE_ATTACK_ALTERS_BOARD_OR_ENERGY:{wall_threat.get('attack_id')}",
            )
        if (
            wall_threat.get("status") != "SUPPORTED"
            or wall_threat.get("unsupported_reasons")
            or floor is None
            or cap is None
            or floor < wall_hp
            or cap < wall_hp
        ):
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_WALL_KO_NOT_EXACT",
            )
        survival = wall_threat.get("next_turn_survival")
        target_hp_after = (
            _int(survival.get("next_turn_hp_floor"))
            if isinstance(survival, dict)
            else None
        )
        if target_hp_after is None or target_hp_after <= 0:
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_TARGET_NOT_STABLE",
            )
        projected_theirs = projected["current"]["players"][opponent]
        opponent_active = _zone(projected_theirs, "active")
        prizes = projected_theirs.get("prize")
        if (
            opponent_active is None
            or len(opponent_active) != 1
            or not isinstance(prizes, list)
        ):
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_PUBLIC_STATE_INVALID",
            )
        if len(prizes) <= 1:
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_FINAL_PRIZE_DONATION",
            )
        opponent_active[0]["hp"] = target_hp_after
        prizes.pop()
        projected_mine = projected["current"]["players"][owner]
        projected_wall_rows = _zone(projected_mine, "active")
        discard = projected_mine.get("discard")
        if (
            projected_wall_rows is None
            or len(projected_wall_rows) != 1
            or _serial(projected_wall_rows[0]) != wall_serial
            or not isinstance(discard, list)
            or any(not isinstance(card, dict) for card in discard)
        ):
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_WALL_REMOVAL_INVALID",
            )
        projected_wall = projected_wall_rows[0]
        discarded = [
            {
                "id": _card_id(projected_wall),
                "playerIndex": owner,
                "serial": wall_serial,
            }
        ]
        for nested_name in ("preEvolution", "energyCards", "tools"):
            nested = projected_wall.get(nested_name)
            if not isinstance(nested, list) or any(
                not isinstance(card, dict) for card in nested
            ):
                return (
                    None,
                    None,
                    None,
                    "TRADING_ATTACK_BRANCH_WALL_PAYLOAD_INVALID",
                )
            discarded.extend(copy.deepcopy(nested))
        projected_mine["discard"] = [*discard, *discarded]
        projected_mine["active"] = []
        bench = _zone(projected_mine, "bench")
        if (
            bench is None
            or len(bench) != 1
            or _serial(bench[0]) != serial
        ):
            return (
                None,
                None,
                None,
                "TRADING_ATTACK_BRANCH_FORCED_PROMOTION_UNCERTIFIED",
            )
        projected_mine["active"] = [copy.deepcopy(bench[0])]
        projected_mine["bench"] = []
        details.update(
            {
                "wall_ko": True,
                "wall_attack_id": wall_threat.get("attack_id"),
                "wall_attack_damage": floor,
                "opponent_prizes_before": len(prizes) + 1,
                "opponent_prizes_after": len(prizes),
                "forced_promotion_serial": serial,
            }
        )
        line_location = "active"
    else:
        projected = copy.deepcopy(raw)
        projected_mine = projected["current"]["players"][owner]
        active = _zone(projected_mine, "active")
        bench = _zone(projected_mine, "bench")
        wall_matches = [
            card
            for zone in (active or [], bench or [])
            for card in zone
            if _serial(card) == wall_serial
        ]
        if (
            active is None
            or bench is None
            or len(wall_matches) != 1
            or active
        ):
            return (
                None,
                None,
                None,
                "TRADING_REFUSAL_BRANCH_PROMOTION_UNCERTIFIED",
            )
        projected_mine["active"] = [copy.deepcopy(wall_matches[0])]
        projected_mine["bench"] = [
            copy.deepcopy(card)
            for card in bench
            if _serial(card) != wall_serial
        ]
        if sum(
            1
            for card in projected_mine["bench"]
            if _serial(card) == serial
        ) != 1:
            return (
                None,
                None,
                None,
                "TRADING_REFUSAL_BRANCH_LINE_INVALID",
            )
        projected_theirs = projected["current"]["players"][opponent]
        opponent_hand_count = projected_theirs.get("handCount")
        opponent_deck_count = projected_theirs.get("deckCount")
        if (
            type(opponent_hand_count) is not int
            or opponent_hand_count < 0
            or type(opponent_deck_count) is not int
            or opponent_deck_count < 1
        ):
            return (
                None,
                None,
                None,
                "TRADING_REFUSAL_MANDATORY_DRAW_UNCERTIFIED",
            )
        projected_theirs["handCount"] = opponent_hand_count + 1
        projected_theirs["deckCount"] = opponent_deck_count - 1
        details["opponent_mandatory_draw_count"] = 1
        details["prior_attachment_turns"] = 1
        line_location = "bench"

    projected_mine = projected["current"]["players"][owner]
    hand_count = projected_mine.get("handCount")
    deck_count = projected_mine.get("deckCount")
    if (
        type(hand_count) is not int
        or hand_count < 0
        or type(deck_count) is not int
        or deck_count < 1
    ):
        return (
            None,
            None,
            None,
            "TRADING_DELAY_ONE_MANDATORY_DRAW_UNCERTIFIED",
        )
    projected_mine["handCount"] = hand_count + 1
    projected_mine["deckCount"] = deck_count - 1
    current = projected.get("current")
    turn = _int(current.get("turn")) if isinstance(current, dict) else None
    if turn is None:
        return None, None, None, "TRADING_DELAY_ONE_TURN_INVALID"
    current.update(
        {
            "turn": turn + 1,
            "turnActionCount": 0,
            "energyAttached": False,
            "retreated": False,
            "stadiumPlayed": False,
            "supporterPlayed": False,
        }
    )
    hand = projected_mine.get("hand")
    if not isinstance(hand, list) or not all(
        isinstance(card, dict) for card in hand
    ):
        return None, None, None, "TRADING_DELAY_ONE_HAND_INVALID"
    projected_matches = [
        card
        for zone_name in ("active", "bench")
        for card in (projected_mine.get(zone_name) or [])
        if isinstance(card, dict) and _serial(card) == serial
    ]
    if len(projected_matches) != 1:
        return None, None, None, "TRADING_DELAY_ONE_LINE_POSITION_INVALID"
    projected_line = copy.deepcopy(projected_matches[0])
    projected_line["appearThisTurn"] = False
    consumed_serials = set()
    action_count = 0
    prompt_count = 0
    evolution_count = 0
    attach_count = 0

    def consume(source_serial: int) -> dict[str, Any] | None:
        found = [
            card
            for card in hand
            if _serial(card) == source_serial
            and source_serial not in consumed_serials
        ]
        if len(found) != 1:
            return None
        consumed_serials.add(source_serial)
        return found[0]

    for step in steps:
        if not isinstance(step, dict):
            return None, None, None, "TRADING_DELAY_ONE_STEP_INVALID"
        kind = step.get("kind")
        if kind == "EVOLVE_FUTURE_SELF_TURN":
            source_serial = _int(step.get("source_serial"))
            if _int(step.get("turn_delay")) != 1 or source_serial is None:
                return None, None, None, "TRADING_DELAY_ONE_EVOLUTION_INVALID"
            source = consume(source_serial)
            expected = {
                ABRA: KADABRA,
                KADABRA: ALAKAZAM,
            }.get(_card_id(projected_line))
            if (
                source is None
                or _card_id(source) != expected
                or _int(source.get("playerIndex")) != owner
                or evolution_count != 0
            ):
                return None, None, None, "TRADING_DELAY_ONE_EVOLUTION_MISSING"
            data = getattr(policy, "card_table", {}).get(expected)
            max_hp = _int(getattr(data, "hp", None))
            old_hp = _int(projected_line.get("hp"))
            old_max = _int(projected_line.get("maxHp"))
            if max_hp is None or old_hp is None or old_max is None:
                return (
                    None,
                    None,
                    None,
                    "TRADING_DELAY_ONE_EVOLUTION_METADATA_UNKNOWN",
                )
            damage = old_max - old_hp
            prior = {
                "id": _card_id(projected_line),
                "serial": _serial(projected_line),
                "playerIndex": owner,
            }
            projected_line["preEvolution"] = [
                *copy.deepcopy(projected_line.get("preEvolution") or []),
                prior,
            ]
            projected_line.update(
                {
                    "id": expected,
                    "serial": source_serial,
                    "hp": max_hp - damage,
                    "maxHp": max_hp,
                    "appearThisTurn": True,
                }
            )
            evolution_count += 1
            action_count += 1
            prompt_count += 1
        elif kind == "ATTACH_PSYCHIC_FUTURE_SELF_TURN":
            source_serial = _int(step.get("source_serial"))
            source_id = _int(step.get("source_card_id"))
            if (
                _int(step.get("turn_delay")) != 1
                or source_serial is None
                or source_id != BASIC_PSYCHIC_ENERGY
                or attach_count != 0
            ):
                return None, None, None, "TRADING_DELAY_ONE_ENERGY_INVALID"
            source = consume(source_serial)
            if (
                source is None
                or _card_id(source) != BASIC_PSYCHIC_ENERGY
                or _int(source.get("playerIndex")) != owner
            ):
                return None, None, None, "TRADING_DELAY_ONE_ENERGY_MISSING"
            projected_line["energies"] = [
                *copy.deepcopy(projected_line.get("energies") or []),
                BASIC_PSYCHIC_ENERGY,
            ]
            projected_line["energyCards"] = [
                *copy.deepcopy(projected_line.get("energyCards") or []),
                copy.deepcopy(source),
            ]
            attach_count += 1
            action_count += 1
        elif kind == "ATTACK_READY":
            if _int(step.get("attack_id", step.get("attackId"))) != POWERFUL_HAND_ATTACK:
                return (
                    None,
                    None,
                    None,
                    "TRADING_DELAY_ONE_ATTACK_BINDING_INVALID",
                )
        else:
            return (
                None,
                None,
                None,
                f"TRADING_DELAY_ONE_STEP_UNSUPPORTED:{kind}",
            )
    if (
        action_count != distance.get("main_actions")
        or prompt_count != distance.get("forced_prompts")
        or _card_id(projected_line) != ALAKAZAM
        or not _public_pokemon_complete(projected_line, owner)
    ):
        return None, None, None, "TRADING_DELAY_ONE_COMPLETION_MISMATCH"
    data = getattr(policy, "attack_table", {}).get(POWERFUL_HAND_ATTACK)
    units = _public_energy_units(projected_line)
    try:
        payable = (
            data is not None
            and units is not None
            and policy._bridge_retaliation_can_pay(units, data.energies)
            is True
        )
    except Exception:
        payable = False
    if not payable:
        return None, None, None, "TRADING_DELAY_ONE_ATTACK_NOT_PAYABLE"
    projected_mine["hand"] = [
        card
        for card in hand
        if _serial(card) not in consumed_serials
    ]
    projected_hand_count = projected_mine.get("handCount")
    if (
        type(projected_hand_count) is not int
        or projected_hand_count < len(consumed_serials)
    ):
        return None, None, None, "TRADING_DELAY_ONE_HAND_COUNT_INVALID"
    projected_mine["handCount"] = (
        projected_hand_count - len(consumed_serials)
    )
    current["turnActionCount"] = action_count
    current["energyAttached"] = attach_count == 1
    if line_location == "active":
        projected_mine["active"] = [projected_line]
    else:
        projected_mine["bench"] = [
            projected_line
            if _serial(card) == serial
            else copy.deepcopy(card)
            for card in (projected_mine.get("bench") or [])
        ]
    projected_distance = copy.deepcopy(distance)
    ready_steps = [
        {
            "kind": "ATTACK_READY",
            "attack_id": POWERFUL_HAND_ATTACK,
        }
    ]
    if line_location == "bench":
        ready_steps.insert(
            0,
            {
                "kind": "EXACT_PROMOTION",
                "serial": _serial(projected_line),
            },
        )
    projected_distance.update(
        {
            "turn_delay": 0,
            "main_actions": 0,
            "forced_prompts": 0 if line_location == "active" else 1,
            "projected_hand_count": projected_mine["handCount"],
            "projected_powerful_hand_damage": (
                20 * projected_mine["handCount"]
            ),
            "witness": {
                "template": (
                    "C4_EXACT_DELAY_ONE_WALL_KO_ATTACK"
                    if branch == DELAY_ONE_ATTACK_BRANCH
                    else "C4_EXACT_DELAY_ONE_TRADING_RELEASE"
                ),
                "steps": ready_steps,
                "missing_requirements": [],
                "unsupported_reasons": [],
            },
        }
    )
    projected_trace = copy.deepcopy(c2_trace)
    rows = projected_trace.get("route_rows")
    if not isinstance(rows, list):
        return None, None, None, "TRADING_DELAY_ONE_C2_ROWS_INVALID"
    selected = [
        candidate
        for candidate in rows
        if isinstance(candidate, dict)
        and candidate.get("line_id") == row.get("line_id")
    ]
    if len(selected) != 1:
        return None, None, None, "TRADING_DELAY_ONE_C2_LINE_AMBIGUOUS"
    selected[0].update(
        {
            "location": line_location.upper(),
            "top_card_id": ALAKAZAM,
            "top_serial": _serial(projected_line),
            "stack_serials": [
                *[
                    _serial(stage)
                    for stage in projected_line.get("preEvolution") or []
                ],
                _serial(projected_line),
            ],
            "stack_card_ids": [
                *[
                    _card_id(stage)
                    for stage in projected_line.get("preEvolution") or []
                ],
                ALAKAZAM,
            ],
            "energy_units": list(projected_line.get("energies") or []),
            "primary_distance": projected_distance,
        }
    )
    details["consumed_serials"] = sorted(consumed_serials)
    details["completed_attacker_serial"] = _serial(projected_line)
    details["completed_attacker_hp"] = _int(projected_line.get("hp"))
    details["projected_hand_count"] = projected_mine["handCount"]
    return projected, projected_trace, details, None


def _post_release_opponent_envelope(
    raw: dict[str, Any],
    defender: dict[str, Any],
    state: dict[str, Any],
    *,
    mandatory_draws: int = 0,
    prior_attachment_turns: int = 0,
) -> dict[str, Any]:
    result = {
        "status": UNKNOWN,
        "continuity": UNKNOWN,
        "final_safety_cap": None,
        "terminal_after_ko": False,
        "promotion_threats": [],
        "unsupported_reasons": [],
    }
    parsed = _players(raw)
    if (
        parsed is None
        or type(mandatory_draws) is not int
        or mandatory_draws < 0
        or type(prior_attachment_turns) is not int
        or prior_attachment_turns < 0
    ):
        result["unsupported_reasons"].append("PUBLIC_STATE_INVALID")
        return result
    _, _, theirs, _, opponent = parsed
    bench = _zone(theirs, "bench")
    if bench is None:
        result["unsupported_reasons"].append(
            "OPPONENT_BENCH_STRUCTURE_INVALID"
        )
        return result
    if not bench:
        result.update(
            {
                "status": "SUPPORTED",
                "continuity": NO_READY_ATTACK,
                "final_safety_cap": 0,
                "terminal_after_ko": True,
            }
        )
        return result
    if any(
        _serial(card) is None
        or _int(card.get("playerIndex")) != opponent
        for card in bench
    ):
        result["unsupported_reasons"].append(
            "OPPONENT_PROMOTION_IDENTITY_INVALID"
        )
        return result

    caps = []
    continuities = []
    threats = []
    attachment_turns = prior_attachment_turns + (
        1 if mandatory_draws > 0 else 0
    )
    for index, attacker in enumerate(bench):
        projected = copy.deepcopy(raw)
        projected_theirs = projected["current"]["players"][opponent]
        hand_count = projected_theirs.get("handCount")
        deck_count = projected_theirs.get("deckCount")
        if attachment_turns > 0:
            enables, attack_id, attachment_count = (
                _attachments_enable_or_strengthen_attack(
                    attacker, attachment_turns
                )
            )
            if enables is None:
                result["unsupported_reasons"].append(
                    f"POST_RELEASE_ATTACHMENT_ENVELOPE_UNKNOWN:{_serial(attacker)}"
                )
                continue
            if enables:
                result["unsupported_reasons"].append(
                    "POST_RELEASE_CUMULATIVE_ATTACHMENTS_ENABLE_ATTACK:"
                    f"{_serial(attacker)}:{attack_id}:{attachment_count}"
                )
                continue
        if (
            type(hand_count) is not int
            or hand_count < 0
            or type(deck_count) is not int
            or deck_count < mandatory_draws
        ):
            result["unsupported_reasons"].append(
                f"POST_RELEASE_MANDATORY_DRAW_UNCERTIFIED:{_serial(attacker)}"
            )
            continue
        projected_theirs["handCount"] = hand_count + mandatory_draws
        projected_theirs["deckCount"] = deck_count - mandatory_draws
        projected_theirs["active"] = [copy.deepcopy(attacker)]
        projected_theirs["bench"] = [
            copy.deepcopy(card)
            for bench_index, card in enumerate(bench)
            if bench_index != index
        ]
        for field in (
            "asleep",
            "burned",
            "confused",
            "paralyzed",
            "poisoned",
        ):
            projected_theirs[field] = False
        threat = _threat_analysis(projected, defender, state)
        if (
            mandatory_draws > 0
            and threat.get("continuity") != NO_READY_ATTACK
        ):
            effect = _attack_has_board_or_energy_effect(threat)
            if effect is None or effect:
                result["unsupported_reasons"].append(
                    f"POST_RELEASE_ATTACK_EFFECT_UNCERTIFIED:{_serial(attacker)}"
                )
                continue
        threats.append(threat)
        if (
            threat.get("status") != "SUPPORTED"
            or threat.get("unsupported_reasons")
            or threat.get("continuity")
            not in (REPEATABLE_READY, NO_READY_ATTACK)
        ):
            result["unsupported_reasons"].append(
                f"POST_RELEASE_PROMOTION_THREAT_UNCERTIFIED:{_serial(attacker)}"
            )
            continue
        continuity = threat.get("continuity")
        continuities.append(continuity)
        cap = (
            0
            if continuity == NO_READY_ATTACK
            else _int(threat.get("final_safety_cap"))
        )
        if cap is None:
            result["unsupported_reasons"].append(
                f"POST_RELEASE_PROMOTION_CAP_UNKNOWN:{_serial(attacker)}"
            )
        else:
            caps.append(cap)
    result["promotion_threats"] = _safe(threats)
    if result["unsupported_reasons"] or len(caps) != len(bench):
        result["unsupported_reasons"] = sorted(
            set(result["unsupported_reasons"])
        )
        return result
    result.update(
        {
            "status": "SUPPORTED",
            "continuity": (
                REPEATABLE_READY
                if REPEATABLE_READY in continuities
                else NO_READY_ATTACK
            ),
            "final_safety_cap": max(caps, default=0),
        }
    )
    return result


def _safe_release(
    line: dict[str, Any],
    threat: dict[str, Any],
    c2_trace: Any,
    raw: dict[str, Any],
    state: dict[str, Any],
    *,
    wall_kind: str,
) -> dict[str, Any]:
    result = {
        "class": "POSSIBLE",
        "reason": "POST_RELEASE_EXCHANGE_UNPROVEN",
        "release_target": None,
        "backup_certified": False,
        "opponent_continuation": UNKNOWN,
        "opponent_safety_cap": None,
        "post_release_opponent_envelope": None,
        "prize_exchange_non_worsening": False,
    }
    if (
        threat.get("status") != "SUPPORTED"
        or threat.get("continuity") != REPEATABLE_READY
        or threat.get("unsupported_reasons")
    ):
        result["reason"] = "CURRENT_TARGET_THREAT_UNCERTIFIED"
        return result
    candidates = _validated_release_candidates(raw, line, c2_trace)
    safe = []
    for candidate in candidates:
        matches = [
            card
            for player in (raw.get("current") or {}).get("players", [])
            if isinstance(player, dict)
            for zone_name in ("active", "bench")
            for card in (player.get(zone_name) or [])
            if isinstance(card, dict)
            and _serial(card) == candidate.get("attacker_serial")
        ]
        if len(matches) != 1:
            continue
        envelope = _post_release_opponent_envelope(
            raw, matches[0], state
        )
        candidate["post_release_opponent_envelope"] = envelope
        cap = _int(envelope.get("final_safety_cap"))
        if (
            envelope.get("status") == "SUPPORTED"
            and not envelope.get("unsupported_reasons")
            and envelope.get("continuity")
            in (REPEATABLE_READY, NO_READY_ATTACK)
            and cap is not None
            and _int(candidate.get("attacker_current_hp")) is not None
            and int(candidate["attacker_current_hp"]) > cap
        ):
            safe.append(candidate)
    if not safe:
        result["reason"] = (
            "POST_RELEASE_PROMOTION_CAP_OR_CONTINUITY_UNSAFE"
            if candidates
            else "POST_RELEASE_TARGET_OR_ATTACK_UNCERTIFIED"
        )
        return result
    safe.sort(
        key=lambda row: (
            -int(row.get("is_protected_line") is True),
            -int(row.get("target_prize_value") or 0),
            int(row.get("attacker_serial") or -1),
        )
    )
    chosen = safe[0]
    wall_prize_risk = 0 if wall_kind == REUSABLE else 1
    prize_non_worsening = (
        _int(chosen.get("target_prize_value")) is not None
        and int(chosen["target_prize_value"]) >= wall_prize_risk
    )
    backup = any(
        candidate.get("attacker_serial") != chosen.get("attacker_serial")
        for candidate in safe
    )
    if not backup:
        result["reason"] = "POST_RELEASE_DISTINCT_BACKUP_UNCERTIFIED"
        return result
    if not prize_non_worsening:
        result["reason"] = "POST_RELEASE_PRIZE_EXCHANGE_WORSENS"
        return result
    result.update(
        {
            "class": "CERTIFIED",
            "reason": "EXACT_SAFE_RELEASE_AND_EXCHANGE",
            "release_target": _safe(chosen),
            "backup_certified": backup,
            "opponent_continuation": (
                chosen["post_release_opponent_envelope"]["continuity"]
            ),
            "opponent_safety_cap": (
                chosen["post_release_opponent_envelope"][
                    "final_safety_cap"
                ]
            ),
            "post_release_opponent_envelope": _safe(
                chosen["post_release_opponent_envelope"]
            ),
            "prize_exchange_non_worsening": True,
        }
    )
    return result


def _safe_attack_branch_release(
    line: dict[str, Any],
    c2_trace: Any,
    raw: dict[str, Any],
    state: dict[str, Any],
    projection: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "class": "POSSIBLE",
        "reason": "SACRIFICE_WALL_KO_EXCHANGE_UNPROVEN",
        "release_mode": "SACRIFICE_WALL_KO_THEN_ATTACK",
        "release_target": None,
        "backup_certified": False,
        "backup_reason": "NOT_EVALUATED",
        "next_attack_certified": False,
        "opponent_continuation": UNKNOWN,
        "opponent_safety_cap": None,
        "immediate_opponent_threat": None,
        "post_release_opponent_envelope": None,
        "prize_exchange_non_worsening": False,
        "delay_one_projection": _safe(projection),
    }
    parsed = _players(raw)
    if parsed is None:
        result["reason"] = "TRADING_PROJECTED_STATE_INVALID"
        return result
    _, mine, _, owner, _ = parsed
    candidates = [
        candidate
        for candidate in _validated_release_candidates(
            raw, line, c2_trace
        )
        if candidate.get("is_protected_line") is True
        and candidate.get("attack_id") == POWERFUL_HAND_ATTACK
    ]
    safe = []
    for candidate in candidates:
        matches = [
            card
            for zone_name in ("active", "bench")
            for card in (mine.get(zone_name) or [])
            if isinstance(card, dict)
            and _serial(card) == candidate.get("attacker_serial")
        ]
        if (
            len(matches) != 1
            or not _public_pokemon_complete(matches[0], owner)
            or _int(candidate.get("target_prize_value")) is None
            or int(candidate["target_prize_value"]) < 1
        ):
            continue
        attacker = matches[0]
        post_ko = _post_release_opponent_envelope(
            raw,
            attacker,
            state,
            mandatory_draws=1,
        )
        cap = _int(post_ko.get("final_safety_cap"))
        hp = _int(attacker.get("hp"))
        if (
            post_ko.get("status") == "SUPPORTED"
            and not post_ko.get("unsupported_reasons")
            and post_ko.get("continuity")
            in (REPEATABLE_READY, NO_READY_ATTACK)
            and cap is not None
            and hp is not None
            and hp > cap
        ):
            candidate["post_release_opponent_envelope"] = _safe(post_ko)
            candidate["combined_safety_cap"] = cap
            safe.append(candidate)
    if not safe:
        result["reason"] = (
            "SACRIFICE_PROMOTED_ATTACKER_CAP_CONTINUITY_OR_PRIZE_UNSAFE"
            if candidates
            else "SACRIFICE_PROMOTED_ATTACKER_UNCERTIFIED"
        )
        return result
    safe.sort(key=lambda candidate: int(candidate["attacker_serial"]))
    chosen = safe[0]
    post_ko = chosen["post_release_opponent_envelope"]
    result.update(
        {
            "class": "CERTIFIED",
            "reason": "EXACT_WALL_KO_PROMOTION_DRAW_ATTACK_EXCHANGE",
            "release_target": _safe(chosen),
            "backup_reason": (
                "NO_DISTINCT_BACKUP_AFTER_EXACT_FORCED_PROMOTION"
            ),
            "next_attack_certified": True,
            "opponent_continuation": post_ko.get("continuity"),
            "opponent_safety_cap": chosen["combined_safety_cap"],
            "post_release_opponent_envelope": _safe(post_ko),
            "prize_exchange_non_worsening": True,
        }
    )
    return result


def _safe_trading_release(
    line: dict[str, Any],
    threat: dict[str, Any],
    c2_trace: Any,
    raw: dict[str, Any],
    state: dict[str, Any],
    wall: dict[str, Any],
    *,
    decision_point: str,
) -> dict[str, Any]:
    result = {
        "class": "POSSIBLE",
        "reason": "TRADING_POST_ATTACK_EXCHANGE_UNPROVEN",
        "release_mode": "TRADING_PLACES_POST_ATTACK",
        "release_target": None,
        "backup_certified": False,
        "opponent_continuation": UNKNOWN,
        "opponent_safety_cap": None,
        "immediate_opponent_threat": None,
        "post_release_opponent_envelope": None,
        "prize_exchange_non_worsening": False,
        "delay_one_projection": None,
    }
    branch = (
        DELAY_ONE_ATTACK_BRANCH
        if decision_point == FORCED_PROMOTION
        else DELAY_ONE_REFUSAL_BRANCH
        if decision_point == TRADING_CHILD
        else None
    )
    if branch is None:
        result["reason"] = "TRADING_DELAY_ONE_DECISION_TIMING_INVALID"
        return result
    if (
        branch == DELAY_ONE_REFUSAL_BRANCH
        and not _wall_self_release_certified(raw, wall)
    ):
        result["reason"] = "TRADING_PLACES_SELF_RELEASE_UNCERTIFIED"
        return result
    if (
        threat.get("status") != "SUPPORTED"
        or threat.get("continuity") != REPEATABLE_READY
        or threat.get("unsupported_reasons")
    ):
        result["reason"] = "CURRENT_TARGET_THREAT_UNCERTIFIED"
        return result
    parsed = _players(raw)
    if parsed is None:
        result["reason"] = "PUBLIC_STATE_INVALID"
        return result
    working_raw = raw
    working_trace = c2_trace
    projection = None
    distance_quality = _distance_quality(line.get("distance_before"))
    if (
        distance_quality is not None
        and distance_quality[0] == 0
        and distance_quality[1] == 1
    ):
        (
            working_raw,
            working_trace,
            projection,
            projection_error,
        ) = (
            _project_delay_one_protected_line(
                raw,
                line,
                c2_trace,
                state,
                wall,
                branch=branch,
            )
        )
        if (
            projection_error is not None
            or working_raw is None
            or working_trace is None
        ):
            result["reason"] = (
                projection_error
                or "TRADING_DELAY_ONE_PROJECTION_UNCERTIFIED"
            )
            return result
        result["delay_one_projection"] = _safe(projection)
        if branch == DELAY_ONE_ATTACK_BRANCH:
            return _safe_attack_branch_release(
                line,
                working_trace,
                working_raw,
                state,
                projection or {},
            )
    working_parsed = _players(working_raw)
    if working_parsed is None:
        result["reason"] = "TRADING_PROJECTED_STATE_INVALID"
        return result
    _, mine, _, owner, _ = working_parsed
    candidates = _validated_release_candidates(
        working_raw, line, working_trace
    )
    safe = []
    timeline_rejections = []
    prior_attachment_turns = (
        _int((projection or {}).get("prior_attachment_turns"))
        if branch == DELAY_ONE_REFUSAL_BRANCH
        and projection is not None
        else 0
    )
    if prior_attachment_turns is None:
        result["reason"] = "TRADING_ATTACHMENT_TIMELINE_INVALID"
        return result
    for candidate in candidates:
        matches = [
            card
            for zone_name in ("active", "bench")
            for card in (mine.get(zone_name) or [])
            if isinstance(card, dict)
            and _serial(card) == candidate.get("attacker_serial")
        ]
        if len(matches) != 1 or not _public_pokemon_complete(
            matches[0], owner
        ):
            continue
        attacker = matches[0]
        immediate_raw, immediate, immediate_error = _future_opponent_attack(
            working_raw,
            attacker,
            state,
            mandatory_draws=1,
            prior_attachment_turns=prior_attachment_turns,
        )
        if (
            immediate_error is not None
            or immediate_raw is None
            or immediate is None
        ):
            candidate["timeline_rejection"] = immediate_error
            if immediate_error is not None:
                timeline_rejections.append(immediate_error)
            continue
        post_ko = _post_release_opponent_envelope(
            immediate_raw,
            attacker,
            state,
            mandatory_draws=1,
            prior_attachment_turns=prior_attachment_turns,
        )
        timeline_rejections.extend(
            reason
            for reason in post_ko.get("unsupported_reasons") or []
            if isinstance(reason, str)
        )
        immediate_cap = _int(immediate.get("final_safety_cap"))
        post_ko_cap = _int(post_ko.get("final_safety_cap"))
        attacker_hp = _int(attacker.get("hp"))
        attacker_prizes = _exact_prize_value(raw, attacker)
        target_prizes = _int(candidate.get("target_prize_value"))
        if (
            immediate.get("status") == "SUPPORTED"
            and not immediate.get("unsupported_reasons")
            and immediate.get("continuity") == REPEATABLE_READY
            and immediate_cap is not None
            and post_ko.get("status") == "SUPPORTED"
            and not post_ko.get("unsupported_reasons")
            and post_ko.get("continuity")
            in (REPEATABLE_READY, NO_READY_ATTACK)
            and post_ko_cap is not None
            and attacker_hp is not None
            and attacker_hp > immediate_cap + post_ko_cap
            and attacker_prizes is not None
            and target_prizes is not None
            and target_prizes >= attacker_prizes
        ):
            candidate["own_prize_value"] = attacker_prizes
            candidate["immediate_opponent_threat"] = _safe(immediate)
            candidate["post_release_opponent_envelope"] = _safe(post_ko)
            candidate["combined_safety_cap"] = (
                immediate_cap + post_ko_cap
            )
            safe.append(candidate)
    if not safe:
        cumulative_rejection = next(
            (
                reason
                for reason in timeline_rejections
                if "CUMULATIVE_ATTACHMENTS_ENABLE_ATTACK" in reason
                and (
                    _int(reason.rsplit(":", 1)[-1]) or 0
                )
                > 1
            ),
            None,
        )
        result["reason"] = cumulative_rejection or (
            "TRADING_PROMOTED_ATTACKER_CAP_CONTINUITY_OR_PRIZE_UNSAFE"
            if candidates
            else "TRADING_PROMOTED_ATTACKER_UNCERTIFIED"
        )
        return result
    safe.sort(
        key=lambda row: (
            -int(row.get("is_protected_line") is True),
            -int(row.get("target_prize_value") or 0),
            int(row.get("attacker_serial") or -1),
        )
    )
    chosen = safe[0]
    ready_candidate_backups = [
        candidate
        for candidate in safe[1:]
        if candidate.get("attacker_serial")
        != chosen.get("attacker_serial")
    ]
    projected_wall = next(
        (
            card
            for zone_name in ("active", "bench")
            for card in (mine.get(zone_name) or [])
            if isinstance(card, dict)
            and _serial(card) == _serial(wall)
        ),
        None,
    )
    wall_backup = bool(
        isinstance(projected_wall, dict)
        and _serial(projected_wall) != chosen.get("attacker_serial")
        and _public_pokemon_complete(projected_wall, owner)
        and _wall_self_release_certified(working_raw, projected_wall)
    )
    if not ready_candidate_backups and not wall_backup:
        result["reason"] = "TRADING_DISTINCT_READY_BACKUP_UNCERTIFIED"
        return result
    immediate = chosen["immediate_opponent_threat"]
    post_ko = chosen["post_release_opponent_envelope"]
    result.update(
        {
            "class": "CERTIFIED",
            "reason": "EXACT_TRADING_POST_ATTACK_SAFE_EXCHANGE",
            "release_target": _safe(chosen),
            "backup_certified": True,
            "backup_serial": (
                ready_candidate_backups[0].get("attacker_serial")
                if ready_candidate_backups
                else _serial(projected_wall)
            ),
            "opponent_continuation": post_ko.get("continuity"),
            "opponent_safety_cap": chosen["combined_safety_cap"],
            "immediate_opponent_threat": _safe(immediate),
            "post_release_opponent_envelope": _safe(post_ko),
            "prize_exchange_non_worsening": True,
        }
    )
    return result


def _bypass_class(
    state: dict[str, Any],
    threat: dict[str, Any],
    protected_stays_bench: bool,
) -> str:
    capability = threat.get("bypass_capability")
    if capability is None:
        inferred = _public_bypass_kind(
            str(threat.get("attack_text") or "")
        )
        capability = (
            "EXACT_ARMED"
            if inferred in ("CERTIFIED_GUST", "CERTIFIED_BENCH_SNIPE")
            else "POSSIBLE_PUBLIC"
            if inferred is not None
            else "NONE"
        )
    if protected_stays_bench and capability == "EXACT_ARMED":
        if threat.get("status") == "SUPPORTED":
            return "CERTIFIED_ARMED_BYPASS"
        return "UNSUPPORTED_POSSIBLE_BYPASS"
    if protected_stays_bench and capability == "POSSIBLE_PUBLIC":
        return "UNSUPPORTED_POSSIBLE_BYPASS"
    if state.get("revealed_boss"):
        return "REVEALED_POSSIBLE_GUST"
    if threat.get("status") != "SUPPORTED" or threat.get("unsupported_reasons"):
        return "BYPASS_UNKNOWN"
    return "NO_PUBLIC_ARMED_BYPASS"


def _project_wall_state(
    raw: dict[str, Any], wall: dict[str, Any]
) -> dict[str, Any] | None:
    parsed = _players(raw)
    wall_serial = _serial(wall)
    if parsed is None or wall_serial is None:
        return None
    _, _, _, owner, _ = parsed
    projected = copy.deepcopy(raw)
    mine = projected["current"]["players"][owner]
    matches = [
        card
        for zone_name in ("active", "bench")
        for card in (mine.get(zone_name) or [])
        if isinstance(card, dict) and _serial(card) == wall_serial
    ]
    if len(matches) != 1:
        return None
    mine["active"] = [copy.deepcopy(matches[0])]
    mine["bench"] = [
        card
        for card in (mine.get("bench") or [])
        if _serial(card) != wall_serial
    ]
    return projected


def _wall_self_release_certified(raw: dict[str, Any], wall: dict[str, Any]) -> bool:
    if _card_id(wall) != DUNSPARCE:
        return True
    data = policy.card_table.get(DUNSPARCE)
    attack = policy.attack_table.get(TRADING_PLACES_ATTACK)
    units = _public_energy_units(wall)
    try:
        return (
            data is not None
            and list(data.attacks or []).count(TRADING_PLACES_ATTACK) == 1
            and attack is not None
            and units is not None
            and policy._bridge_retaliation_can_pay(units, attack.energies)
            is True
        )
    except Exception:
        return False


def _row_template(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "decision_point": None,
        "wall_class": REJECTED,
        "certification": "UNAVAILABLE",
        "legality": "UNAVAILABLE",
        "option_index": None,
        "semantic_action_key": None,
        "wall": None,
        "rejection_codes": [],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "metrics": {},
        "pareto_vector": None,
    }


def _wall_row(
    kind: str,
    *,
    raw: dict[str, Any],
    option_index: int | None,
    option_key: dict[str, Any] | None,
    wall: dict[str, Any] | None,
    line: dict[str, Any],
    expose_threat: dict[str, Any],
    wall_threat: dict[str, Any],
    bypass: str,
    c2_trace: Any,
    public_state: dict[str, Any],
    turn: int,
    decision_point: str,
    global_structural_reasons: Iterable[str] = (),
    hold_codes: Iterable[str] = (),
    existing_hold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = _row_template(kind)
    row.update(
        {
            "decision_point": decision_point,
            "legality": "EXACT" if option_index is not None else "UNAVAILABLE",
            "option_index": option_index,
            "semantic_action_key": _safe(option_key),
            "wall": _card_snapshot(wall),
        }
    )
    reasons = list(global_structural_reasons)
    chance = []
    unsupported = list(line.get("unsupported_reasons") or [])
    unsupported.extend(expose_threat.get("unsupported_reasons") or [])
    unsupported.extend(wall_threat.get("unsupported_reasons") or [])
    if unsupported:
        chance.extend(unsupported)
    reasons.extend(hold_codes)
    importance = line.get("importance")
    if line.get("protected_line") is None:
        reasons.append("NO_LIVE_PROTECTED_LINE")
    elif importance == "UNKNOWN_IMPORTANCE":
        chance.append("IMPORTANCE_UNKNOWN")
    elif importance not in ("UNIQUE", "IMPORTANT"):
        reasons.append("PROTECTED_LINE_REDUNDANT")
    if option_index is None or wall is None:
        reasons.append("WALL_OPTION_NOT_EXACT_LEGAL")

    floor = _int(expose_threat.get("damage_floor"))
    protected_hp = None
    protected = line.get("_row")
    if isinstance(protected, dict):
        protected_hp = _int(
            (_card_snapshot_from_line(raw, protected) or {}).get("hp")
        )
    if expose_threat.get("status") != "SUPPORTED":
        if "SAFETY_CAP_UNKNOWN" in expose_threat.get("unsupported_reasons", []):
            chance.append("SAFETY_CAP_UNKNOWN")
        else:
            reasons.append("EXPOSE_THREAT_UNSUPPORTED")
    elif expose_threat.get("continuity") == RECHARGE_REQUIRED:
        chance.append("RECHARGE_REQUIRED")
    elif expose_threat.get("continuity") == UNKNOWN:
        chance.append("CONTINUITY_UNKNOWN")
    elif expose_threat.get("continuity") != REPEATABLE_READY:
        reasons.append("NO_REPEATABLE_READY_THREAT")
    if protected_hp is None:
        reasons.append("PROTECTED_HP_UNKNOWN")
    elif floor is None or floor < protected_hp:
        if expose_threat.get("cap_ko"):
            chance.append("CAP_ONLY")
        else:
            reasons.append("EXPOSE_FLOOR_NOT_KO")

    if bypass in ("CERTIFIED_ARMED_BYPASS",):
        reasons.append("PUBLIC_ARMED_BYPASS")
    elif bypass in (
        "REVEALED_POSSIBLE_GUST",
        "UNSUPPORTED_POSSIBLE_BYPASS",
        "BYPASS_UNKNOWN",
    ):
        chance.append("REVEALED_POSSIBLE_BYPASS")

    distance = line.get("distance_before")
    quality = _distance_quality(distance)
    initial_delay = quality[1] if quality is not None else None
    if not isinstance(distance, dict) or distance.get("route_class") == "UNKNOWN":
        reasons.append("PROGRESS_UNKNOWN")
    elif distance.get("route_class") != "CERTIFIED":
        chance.append("PROGRESS_POSSIBLE_ONLY")
    elif initial_delay is None or initial_delay <= 0:
        reasons.append("NO_HOLD_PROGRESS_REQUIRED")

    release = (
        _safe_trading_release(
            line,
            expose_threat,
            c2_trace,
            raw,
            public_state,
            wall or {},
            decision_point=decision_point,
        )
        if kind == SACRIFICE
        else _safe_release(
            line,
            expose_threat,
            c2_trace,
            raw,
            public_state,
            wall_kind=kind,
        )
    )
    if release["class"] == UNKNOWN:
        reasons.append("RELEASE_UNKNOWN")
    elif release["class"] != "CERTIFIED":
        chance.append("RELEASE_POSSIBLE_ONLY")

    parsed = _players(raw)
    opponent_prizes = None
    deck_count = None
    if parsed is not None:
        _, mine, theirs, _, _ = parsed
        opponent_prizes = (
            len(theirs.get("prize"))
            if isinstance(theirs.get("prize"), list)
            else None
        )
        deck_count = _int(mine.get("deckCount"))
    if opponent_prizes is None:
        reasons.append("OPPONENT_PRIZE_COUNT_UNKNOWN")
    elif opponent_prizes <= 1:
        reasons.append("FINAL_PRIZE_DONATION")

    remaining_hp = _int(wall.get("hp")) if isinstance(wall, dict) else None
    safety_cap = _int(wall_threat.get("final_safety_cap"))
    if kind == REUSABLE:
        if _card_id(wall) != DUDUNSPARCE:
            reasons.append("REUSABLE_NOT_DUDUNSPARCE_66")
        if safety_cap is None:
            chance.append("SAFETY_CAP_UNKNOWN")
        elif remaining_hp is None or remaining_hp <= safety_cap:
            reasons.append("REUSABLE_WALL_NOT_ABOVE_FINAL_SAFETY_CAP")
        if deck_count is None or deck_count < 3:
            reasons.append("RUN_AWAY_DRAW3_NOT_AVAILABLE")
    else:
        if _card_id(wall) != DUNSPARCE:
            reasons.append("SACRIFICE_NOT_DUNSPARCE_305")
        if initial_delay != 1:
            reasons.append("SACRIFICE_DOES_NOT_BUY_EXACT_READY_TURN")
        if not _wall_self_release_certified(raw, wall or {}):
            reasons.append("TRADING_PLACES_SELF_RELEASE_UNCERTIFIED")

    if wall_threat.get("status") != "SUPPORTED":
        if "SAFETY_CAP_UNKNOWN" in wall_threat.get("unsupported_reasons", []):
            chance.append("SAFETY_CAP_UNKNOWN")
        else:
            reasons.append("WALL_THREAT_UNSUPPORTED")

    reasons = sorted(set(reasons))
    chance = sorted(set(chance))
    row["unsupported_reasons"] = sorted(set(unsupported))
    row["structural_reasons"] = sorted(set(reasons))
    row["rejection_codes"] = reasons + chance
    hold_turns = initial_delay if isinstance(initial_delay, int) else 10**6
    resource_loss = (
        len((wall or {}).get("energyCards") or [])
        + len((wall or {}).get("tools") or [])
        + len((wall or {}).get("preEvolution") or [])
    )
    lost_draw = min(3, deck_count or 0) if kind == REUSABLE else 0
    prize_loss = 0 if kind == REUSABLE else 1
    row["metrics"] = {
        "protected_readiness": distance.get("route_class")
        if isinstance(distance, dict)
        else UNKNOWN,
        "hold_turns": None if hold_turns == 10**6 else hold_turns,
        "own_prize_loss": prize_loss,
        "gust_exposure": None if hold_turns == 10**6 else hold_turns,
        "resource_loss": resource_loss,
        "lost_draw3": lost_draw,
        "safe_release": release,
        "final_prize_outcome": opponent_prizes == 1,
        "remaining_hp": remaining_hp,
        "final_safety_cap": safety_cap,
        "survival_margin": (
            remaining_hp - safety_cap
            if remaining_hp is not None and safety_cap is not None
            else None
        ),
        "hold_entry_turn": (
            existing_hold.get("entry_turn")
            if isinstance(existing_hold, dict)
            else turn
        ),
        "hold_deadline": (
            existing_hold.get("deadline")
            if isinstance(existing_hold, dict)
            else turn + initial_delay
            if isinstance(initial_delay, int)
            and initial_delay > 0
            else None
        ),
    }
    row["pareto_vector"] = {
        "protected_readiness": 1
        if isinstance(distance, dict) and distance.get("route_class") == "CERTIFIED"
        else 0,
        "attacker_backup_continuity": 1
        if release.get("class") == "CERTIFIED"
        else 0,
        "own_prize_loss": -prize_loss,
        "hold_turns": -hold_turns,
        "gust_exposure": -hold_turns,
        "resource_loss": -resource_loss,
        "lost_draw3": -lost_draw,
        "safe_release": 1 if release.get("class") == "CERTIFIED" else 0,
        "final_prize_outcome": 0 if opponent_prizes == 1 else 1,
    }
    if reasons:
        row["wall_class"] = REJECTED
        row["certification"] = "REJECTED"
    elif chance:
        row["wall_class"] = CHANCE
        row["certification"] = "PRESERVE_CHANCE"
    else:
        row["wall_class"] = STRICT
        row["certification"] = "STRICT"
    return row


def _card_snapshot_from_line(
    raw: dict[str, Any], line_row: dict[str, Any]
) -> dict[str, Any] | None:
    parsed = _players(raw)
    if parsed is None:
        return None
    _, mine, _, _, _ = parsed
    serial = line_row.get("top_serial")
    for zone_name in ("active", "bench"):
        for card in mine.get(zone_name) or []:
            if isinstance(card, dict) and _serial(card) == serial:
                return _card_snapshot(card)
    return None


def _own_attack_after_run_away(
    raw: dict[str, Any],
    draw_count: int,
    c2_trace: Any,
    state: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "conversion": "NONE",
        "promotion_serial": None,
        "damage": None,
        "ko": False,
        "terminal_win": False,
        "safe_prize_exchange": False,
        "safe_exchange_reason": "DISTINCT_BACKUP_OR_ENVELOPE_UNPROVEN",
        "distinct_backup_serial": None,
        "post_release_opponent_envelope": None,
        "reason": "NO_EXACT_POST_RUN_AWAY_ATTACK",
    }
    parsed = _players(raw)
    if parsed is None:
        return result
    _, mine, theirs, _, _ = parsed
    opponent_active = _zone(theirs, "active")
    if opponent_active is None or len(opponent_active) != 1:
        return result
    target = opponent_active[0]
    target_hp = _int(target.get("hp"))
    if target_hp is None:
        return result
    route_rows = (
        c2_trace.get("route_rows")
        if isinstance(c2_trace, dict)
        else None
    )
    if not isinstance(route_rows, list):
        result["reason"] = "C2_ROUTE_ROWS_INVALID"
        return result
    candidates = []
    for card in mine.get("bench") or []:
        if not isinstance(card, dict):
            continue
        matching_rows = [
            row
            for row in route_rows
            if isinstance(row, dict)
            and _int(row.get("top_serial")) == _serial(card)
            and _int(row.get("top_card_id")) == _card_id(card)
            and row.get("location") == "BENCH"
        ]
        if len(matching_rows) != 1:
            continue
        distance = matching_rows[0].get("primary_distance")
        quality = _distance_quality(distance)
        if (
            quality is None
            or quality[0] != 0
            or quality[1] != 0
        ):
            continue
        conversion = _exact_attack_conversion(
            raw,
            card,
            distance,
            location="BENCH",
            hand_bonus=draw_count,
        )
        if conversion["certified"]:
            candidates.append(conversion)
    if not candidates:
        return result
    candidates.sort(
        key=lambda row: (
            -int(row.get("damage") or 0),
            int(row.get("attacker_serial") or -1),
        )
    )
    best_damage = candidates[0]["damage"]
    best = [row for row in candidates if row["damage"] == best_damage]
    if len(best) != 1:
        result["reason"] = "POST_RUN_AWAY_PROMOTION_NOT_UNIQUE"
        return result
    chosen = best[0]
    damage = int(chosen["damage"])
    serial = chosen["attacker_serial"]
    ko = damage >= target_hp
    terminal = ko and (
        (
            isinstance(mine.get("prize"), list)
            and len(mine["prize"]) == 1
        )
        or len(theirs.get("bench") or []) == 0
    )
    mine_cards = [
        card
        for zone_name in ("active", "bench")
        for card in (mine.get(zone_name) or [])
        if isinstance(card, dict)
    ]
    chosen_card = next(
        (
            card
            for card in mine_cards
            if _serial(card) == chosen.get("attacker_serial")
        ),
        None,
    )
    chosen_envelope = (
        _post_release_opponent_envelope(raw, chosen_card, state)
        if isinstance(chosen_card, dict)
        else None
    )
    chosen_cap = _int(
        chosen_envelope.get("final_safety_cap")
        if isinstance(chosen_envelope, dict)
        else None
    )
    chosen_safe = bool(
        isinstance(chosen_envelope, dict)
        and chosen_envelope.get("status") == "SUPPORTED"
        and not chosen_envelope.get("unsupported_reasons")
        and chosen_envelope.get("continuity")
        in (REPEATABLE_READY, NO_READY_ATTACK)
        and chosen_cap is not None
        and _int(chosen.get("attacker_current_hp")) is not None
        and int(chosen["attacker_current_hp"]) > chosen_cap
    )
    safe_backups = []
    for candidate in candidates:
        if candidate.get("attacker_serial") == chosen.get("attacker_serial"):
            continue
        backup_card = next(
            (
                card
                for card in mine_cards
                if _serial(card) == candidate.get("attacker_serial")
            ),
            None,
        )
        if not isinstance(backup_card, dict):
            continue
        backup_envelope = _post_release_opponent_envelope(
            raw, backup_card, state
        )
        backup_cap = _int(backup_envelope.get("final_safety_cap"))
        if (
            backup_envelope.get("status") == "SUPPORTED"
            and not backup_envelope.get("unsupported_reasons")
            and backup_envelope.get("continuity")
            in (REPEATABLE_READY, NO_READY_ATTACK)
            and backup_cap is not None
            and _int(candidate.get("attacker_current_hp")) is not None
            and int(candidate["attacker_current_hp"]) > backup_cap
        ):
            safe_backups.append(candidate)
    safe_backups.sort(key=lambda row: int(row["attacker_serial"]))
    safe_exchange = bool(
        ko
        and int(chosen.get("target_prize_value") or 0) >= 1
        and chosen_safe
        and safe_backups
    )
    conversion = (
        "TERMINAL_WIN"
        if terminal
        else "EXACT_SAFE_PRIZE_EXCHANGE"
        if safe_exchange
        else "CURRENT_TARGET_KO_UNCERTIFIED_CONTINUITY"
        if ko
        else "NONE"
    )
    result.update(
        {
            "conversion": conversion,
            "promotion_serial": serial,
            "damage": damage,
            "ko": ko,
            "terminal_win": terminal,
            "safe_prize_exchange": safe_exchange,
            "safe_exchange_reason": (
                "EXACT_DISTINCT_BACKUP_AND_POST_KO_ENVELOPE"
                if safe_exchange
                else "DISTINCT_BACKUP_OR_ENVELOPE_UNPROVEN"
            ),
            "distinct_backup_serial": (
                safe_backups[0]["attacker_serial"]
                if safe_backups
                else None
            ),
            "post_release_opponent_envelope": _safe(chosen_envelope),
            "reason": "EXACT_ANONYMOUS_DRAW_COUNT_CONVERSION"
            if terminal or ko or safe_exchange
            else "NON_KO_DAMAGE_ONLY",
            "attack_id": chosen.get("attack_id"),
            "attack_binding": chosen.get("attack_binding"),
            "target_serial": chosen.get("target_serial"),
            "target_prize_value": chosen.get("target_prize_value"),
        }
    )
    return result


def _run_away_row(
    raw: dict[str, Any],
    *,
    option_index: int | None,
    option_key: dict[str, Any] | None,
    c2_trace: Any,
    threat: dict[str, Any],
    public_state: dict[str, Any],
    decision_point: str,
    global_structural_reasons: Iterable[str] = (),
    global_unsupported_reasons: Iterable[str] = (),
) -> dict[str, Any]:
    row = _row_template(RUN_AWAY)
    parsed = _players(raw)
    active = None
    deck_count = None
    if parsed is not None:
        _, mine, _, _, _ = parsed
        active_rows = _zone(mine, "active")
        active = active_rows[0] if active_rows and len(active_rows) == 1 else None
        deck_count = _int(mine.get("deckCount"))
    draw_count = min(3, deck_count) if isinstance(deck_count, int) and deck_count >= 0 else 0
    conversion = _own_attack_after_run_away(
        raw, draw_count, c2_trace, public_state
    )
    reasons = list(global_structural_reasons)
    independent_exact_conversion = bool(
        conversion["terminal_win"] or conversion["safe_prize_exchange"]
    )
    unsupported = []
    if not independent_exact_conversion:
        unsupported.extend(global_unsupported_reasons)
        unsupported.extend(threat.get("unsupported_reasons") or [])
    chance = sorted(set(unsupported))
    if _card_id(active) != DUDUNSPARCE:
        reasons.append("RUN_AWAY_SOURCE_NOT_DUDUNSPARCE_66")
    if option_index is None:
        reasons.append("RUN_AWAY_OPTION_NOT_EXACT_LEGAL")
    if draw_count <= 0:
        reasons.append("RUN_AWAY_EMPTY_DECK")
    repeatable_threat_ko = bool(
        conversion["ko"]
        and threat.get("status") == "SUPPORTED"
        and threat.get("continuity") == REPEATABLE_READY
        and not threat.get("unsupported_reasons")
    )
    if repeatable_threat_ko and not conversion["terminal_win"]:
        conversion["conversion"] = "CURRENT_REPEATABLE_THREAT_KO"
    exact = (
        conversion["terminal_win"]
        or repeatable_threat_ko
        or conversion["safe_prize_exchange"]
    )
    if not exact:
        chance.append(
            "RUN_AWAY_NO_EXACT_TERMINAL_THREAT_KO_OR_SAFE_EXCHANGE"
        )
    reasons = sorted(set(reasons))
    chance = sorted(set(chance))
    row.update(
        {
            "decision_point": decision_point,
            "legality": "EXACT" if option_index is not None else "UNAVAILABLE",
            "option_index": option_index,
            "semantic_action_key": _safe(option_key),
            "wall": _card_snapshot(active),
            "rejection_codes": reasons + chance,
            "unsupported_reasons": sorted(set(unsupported)),
            "structural_reasons": reasons,
            "wall_class": (
                REJECTED if reasons else CHANCE if chance else STRICT
            ),
            "certification": (
                "REJECTED"
                if reasons
                else "PRESERVE_CHANCE"
                if chance
                else "STRICT"
            ),
            "metrics": {
                "certified_draw_count": draw_count,
                "certified_draw_damage_delta": 20 * draw_count,
                "drawn_card_identities": "POSSIBLE",
                "conversion": conversion,
            },
            "pareto_vector": None,
        }
    )
    return row


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_vector = left.get("pareto_vector")
    right_vector = right.get("pareto_vector")
    if not isinstance(left_vector, dict) or not isinstance(right_vector, dict):
        return False
    if set(left_vector) != set(right_vector):
        return False
    values = [
        (left_vector[key], right_vector[key]) for key in sorted(left_vector)
    ]
    return all(a >= b for a, b in values) and any(a > b for a, b in values)


def pareto_arbitrate(rows: list[dict[str, Any]]) -> tuple[str, str]:
    by_kind = {row.get("kind"): row for row in rows}
    run_away = by_kind.get(RUN_AWAY)
    if isinstance(run_away, dict) and run_away.get("certification") == "STRICT":
        return RUN_AWAY, "RUN_AWAY_EXACT_CONVERSION"
    reusable = by_kind.get(REUSABLE)
    sacrifice = by_kind.get(SACRIFICE)
    strict_rows = [
        row
        for row in (reusable, sacrifice)
        if isinstance(row, dict) and row.get("certification") == "STRICT"
    ]
    if len(strict_rows) == 1:
        return str(strict_rows[0]["kind"]), "ONLY_STRICT_WALL"
    if len(strict_rows) == 2:
        if _dominates(strict_rows[0], strict_rows[1]):
            return str(strict_rows[0]["kind"]), "PARETO_DOMINANCE"
        if _dominates(strict_rows[1], strict_rows[0]):
            return str(strict_rows[1]["kind"]), "PARETO_DOMINANCE"
        return NO_WALL, "NO_CERTIFIED_DOMINANCE"
    return NO_WALL, "NO_STRICT_ALTERNATIVE"


def _find_decision(
    raw: dict[str, Any],
    parent_keys: list[dict[str, Any]] | None,
    option_rows: list[dict[str, Any]],
    state: dict[str, Any],
    observation_fp: str,
    callback_ordinal: int,
) -> dict[str, Any]:
    parsed = _players(raw)
    select = raw.get("select") if isinstance(raw.get("select"), dict) else {}
    context = _int(select.get("context"))
    turn = _int((raw.get("current") or {}).get("turn"))
    if parsed is None:
        return {"decision_point": None, "rejection": "PUBLIC_STATE_INVALID"}
    _, mine, _, _, _ = parsed
    owner = parsed[3]
    active_rows = _zone(mine, "active")
    active = active_rows[0] if active_rows and len(active_rows) == 1 else None

    pending = state.get("trading_pending")
    if isinstance(pending, dict):
        expired = (
            pending.get("boundary") != state.get("boundary_fingerprint")
            or raw.get("truncated") is True
            or (
                turn is not None
                and pending.get("turn") is not None
                and turn > pending["turn"] + 1
            )
            or callback_ordinal > pending.get("created_ordinal", 0) + 2
        )
        if expired:
            state["trading_pending"] = None
            pending = None
        elif pending.get("child_observation_fingerprint") in (
            None,
            observation_fp,
        ):
            select_type = _int(select.get("type"))
            min_count = _int(select.get("minCount"))
            max_count = _int(select.get("maxCount"))
            action_count = _int((raw.get("current") or {}).get("turnActionCount"))
            effect = select.get("effect")
            context_card = select.get("contextCard")
            effect_rows = [
                row
                for row in (effect, context_card)
                if isinstance(row, dict)
            ]
            effect_exact = any(
                _int(row.get("attackId")) == TRADING_PLACES_ATTACK
                and _int(row.get("sourceSerial", row.get("serial")))
                == pending.get("source_serial")
                for row in effect_rows
            )
            logs = raw.get("logs")
            attack_log_exact = (
                isinstance(logs, list)
                and sum(
                    1
                    for row in logs
                    if isinstance(row, dict)
                    and _int(row.get("type")) == ATTACK_LOG
                    and _int(row.get("attackId")) == TRADING_PLACES_ATTACK
                    and _int(row.get("serial"))
                    == pending.get("source_serial")
                    and _int(row.get("playerIndex")) == owner
                )
                == 1
            )
            prompt_exact = (
                context == FORCED_PROMOTION_CONTEXT
                and select_type == 1
                and min_count == 1
                and max_count == 1
                and effect_exact
                and attack_log_exact
                and action_count is not None
                and pending.get("turn_action_count") is not None
                and action_count > pending["turn_action_count"]
                and action_count <= pending["turn_action_count"] + 2
                and turn == pending.get("turn")
                and len(parent_keys or []) == 1
            )
            if not prompt_exact:
                state["trading_pending"] = None
                return {
                    "decision_point": None,
                    "rejection": "TRADING_PLACES_CHILD_SEMANTICS_INVALID",
                }
            selected_card = _selected_card(raw, parent_keys, option_rows)
            source_rows = [
                row
                for row in option_rows
                if _serial(_resolve_option_card(raw, row["option"]))
                == pending.get("source_serial")
                and row["key"].get("type") == PROMOTION_OPTION
                and row["key"].get("area") == BENCH_AREA
                and row["key"].get("player_index") == owner
            ]
            if len(source_rows) != 1 or selected_card is None:
                state["trading_pending"] = None
                return {
                    "decision_point": None,
                    "rejection": "TRADING_PLACES_CHILD_OPTION_INVALID",
                }
            pending["child_observation_fingerprint"] = observation_fp
            pending["child_serial"] = _serial(selected_card)
            expose_card = (
                _unique_post_removal_card(mine)
                if _serial(selected_card) == pending.get("source_serial")
                else selected_card
            )
            return {
                "decision_point": TRADING_CHILD,
                "expose_card": expose_card,
                "wall_cards": [
                    (
                        source_rows[0]["index"],
                        source_rows[0]["key"],
                        _resolve_option_card(raw, source_rows[0]["option"]),
                    )
                ],
                "pending": _safe(pending),
            }

    if context == FORCED_PROMOTION_CONTEXT:
        selected = _selected_card(raw, parent_keys, option_rows)
        walls = []
        for row in option_rows:
            card = _resolve_option_card(raw, row["option"])
            if _card_id(card) in (DUDUNSPARCE, DUNSPARCE):
                walls.append((row["index"], row["key"], card))
        return {
            "decision_point": FORCED_PROMOTION,
            "expose_card": selected,
            "wall_cards": walls,
        }

    ability_row = next(
        (
            row
            for row in option_rows
            if row["key"].get("type") == ABILITY
            and row["key"].get("area") == ACTIVE_AREA
        ),
        None,
    )
    if (
        context == MAIN_CONTEXT
        and _card_id(active) == DUDUNSPARCE
        and ability_row is not None
    ):
        selected_index = (
            _selected_index(parent_keys, option_rows)
            if parent_keys is not None
            else None
        )
        selected_row = next(
            (
                row
                for row in option_rows
                if row["index"] == selected_index
            ),
            None,
        )
        hold_options = [
            row
            for row in option_rows
            if row is not ability_row
            and row["key"].get("type") == END_TURN
        ]
        hold_rows = [
            (row["index"], row["key"], active)
            for row in hold_options
        ]
        if (
            isinstance(selected_row, dict)
            and selected_row is not ability_row
            and selected_row["key"].get("type") == END_TURN
            and all(
                row["index"] != selected_row["index"]
                for row in hold_options
            )
        ):
            hold_rows.append(
                (selected_row["index"], selected_row["key"], active)
            )
        return {
            "decision_point": RUN_AWAY_POINT,
            "expose_card": _unique_post_removal_card(mine),
            "wall_cards": hold_rows,
            "run_away_option": ability_row,
        }

    selected_attack = (
        parent_keys[0]
        if parent_keys and len(parent_keys) == 1
        else None
    )
    if (
        context == MAIN_CONTEXT
        and _card_id(active) == DUNSPARCE
        and isinstance(selected_attack, dict)
        and selected_attack.get("type") == ATTACK
        and selected_attack.get("attack_id") == TRADING_PLACES_ATTACK
    ):
        state["trading_pending"] = {
            "source_serial": _serial(active),
            "source_card": copy.deepcopy(active),
            "attack_id": TRADING_PLACES_ATTACK,
            "turn": turn,
            "turn_action_count": _int(
                (raw.get("current") or {}).get("turnActionCount")
            ),
            "entry_context": context,
            "entry_effect_fingerprint": fingerprint(select.get("effect")),
            "entry_logs_fingerprint": fingerprint(raw.get("logs")),
            "boundary": state.get("boundary_fingerprint"),
            "created_ordinal": callback_ordinal,
            "parent_semantic_key": _safe(selected_attack),
            "child_observation_fingerprint": None,
        }
        return {
            "decision_point": None,
            "rejection": "TRADING_PLACES_CHILD_PENDING",
        }
    return {"decision_point": None, "rejection": "NOT_C4_DECISION_POINT"}


def _selected_index(
    parent_keys: list[dict[str, Any]], option_rows: list[dict[str, Any]]
) -> int | None:
    if len(parent_keys) != 1:
        return None
    target = _canonical(parent_keys[0])
    matches = [
        row["index"] for row in option_rows if _canonical(row["key"]) == target
    ]
    return matches[0] if len(matches) == 1 else None


def _selected_card(
    raw: dict[str, Any],
    parent_keys: list[dict[str, Any]] | None,
    option_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not parent_keys:
        return None
    selected = _selected_index(parent_keys, option_rows)
    row = next((row for row in option_rows if row["index"] == selected), None)
    return _resolve_option_card(raw, row["option"]) if row else None


def _unique_post_removal_card(mine: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        card
        for card in (mine.get("bench") or [])
        if isinstance(card, dict) and _card_id(card) in ALAKAZAM_LINE
    ]
    if len(candidates) == 1:
        return candidates[0]
    immature = [
        card for card in candidates if _card_id(card) in (ABRA, KADABRA)
    ]
    return immature[0] if len(immature) == 1 else None


def _base_trace(
    raw: Any,
    parent_action: Any,
    c2_trace: Any,
) -> dict[str, Any]:
    option_rows = []
    if isinstance(raw, dict):
        try:
            option_rows, _ = _option_rows(raw)
        except Exception:
            option_rows = []
    public_material = (
        _public_state_material(raw, option_rows)
        if isinstance(raw, dict)
        else None
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "rule_version": RULE_VERSION,
        "parent_closure_sha256": PARENT_CLOSURE_SHA256,
        "candidate_closure_sha256": policy_closure_sha256(),
        "analyzer_component_sha256": ANALYZER_SHA256,
        "state_machine": ["CAPTURE"],
        "decision_point": None,
        "pair_id": None,
        "decision_id": None,
        "raw_parent_action": parent_action,
        "parent_action": _safe(parent_action),
        "proposed_action": _safe(parent_action),
        "applied_action": parent_action,
        "action_python_type": _action_type(parent_action),
        "action_identity": {
            "value_equal": True,
            "type_equal": True,
            "order_equal": True,
            "returned_parent_object_unchanged": True,
        },
        "semantic_option_keys": (
            sorted(
                [_safe(row["key"]) for row in option_rows],
                key=_canonical,
            )
            if isinstance(public_material, dict)
            else None
        ),
        "semantic_parent_action_keys": None,
        "semantic_proposed_action_keys": None,
        "public_state_material": _safe(public_material),
        "public_state_fingerprint": (
            fingerprint(public_material)
            if isinstance(public_material, dict)
            else None
        ),
        "pair_material": None,
        "game_boundary_fingerprint": None,
        "parent_post_fingerprint": None,
        "candidate_post_fingerprint": None,
        "expose_state_fingerprint": None,
        "wall_state_fingerprint": None,
        "expose_projection": None,
        "wall_projection": None,
        "protected_line": None,
        "importance": "UNKNOWN_IMPORTANCE",
        "distance_before": None,
        "distance_without_line": None,
        "threat": None,
        "damage_floor": None,
        "damage_cap": None,
        "continuity": UNKNOWN,
        "wall_candidates": [],
        "candidate_rows": [_row_template(kind) for kind in CANDIDATE_KINDS],
        "run_away_value": None,
        "reusable_wall_value": None,
        "sacrifice_wall_value": None,
        "bypass": UNKNOWN,
        "refusal_progress": UNKNOWN,
        "safe_release": None,
        "gust_exposure_turns": 0,
        "wall_class": REJECTED,
        "arbitration_reason": "UNANALYZED",
        "outcome_status": "COUNTERFACTUAL_UNOBSERVED",
        "outcome_events": [],
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "safety_cap": None,
        "hold_entry_turn": None,
        "hold_deadline": None,
        "distance_progress_by_turn": [],
        "rejection_codes": [],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "parser_source": (
            "_cumulative_parent._bridge_retaliation_attack_damage"
        ),
        "metric_exception": None,
        "c2_trace_rule_version": (
            c2_trace.get("rule_version")
            if isinstance(c2_trace, dict)
            else None
        ),
    }


def rejection_trace(
    raw: Any,
    parent_action: Any,
    error: BaseException | str,
    *,
    c2_trace: Any = None,
) -> dict[str, Any]:
    trace = _base_trace(raw, parent_action, c2_trace)
    code = error if isinstance(error, str) else type(error).__name__
    trace.update(
        {
            "state_machine": [
                "CAPTURE",
                "EMIT_REJECTION",
                "RETURN_EXACT_PARENT_ACTION",
            ],
            "arbitration_reason": "FAIL_CLOSED_REJECTION",
            "rejection_codes": ["METRIC_EXCEPTION"],
            "metric_exception": code,
        }
    )
    return trace


def emergency_trace(
    parent_action: Any,
    error: BaseException | str,
) -> dict[str, Any]:
    """Build the full fail-closed schema without calling another C4 helper."""
    code = error if isinstance(error, str) else type(error).__name__
    rows = [
        {
            "kind": kind,
            "decision_point": None,
            "wall_class": "REJECTED",
            "certification": "UNAVAILABLE",
            "legality": "UNAVAILABLE",
            "option_index": None,
            "semantic_action_key": None,
            "wall": None,
            "rejection_codes": [],
            "unsupported_reasons": [],
            "structural_reasons": [],
            "metrics": {},
            "pareto_vector": None,
        }
        for kind in (
            "RUN_AWAY_ACCELERATION",
            "CERTIFIED_REUSABLE_WALL",
            "CERTIFIED_SACRIFICE_WALL",
            "NO_WALL_OR_UNKNOWN",
        )
    ]
    return {
        "schema_version": 6,
        "rule_version": "V4_WALL_SHADOW_FIX6",
        "parent_closure_sha256": (
            "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
        ),
        "candidate_closure_sha256": None,
        "analyzer_component_sha256": (
            "AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201"
        ),
        "state_machine": [
            "CAPTURE",
            "EMIT_REJECTION",
            "RETURN_EXACT_PARENT_ACTION",
        ],
        "decision_point": None,
        "pair_id": None,
        "decision_id": None,
        "raw_parent_action": parent_action,
        "parent_action": parent_action,
        "proposed_action": parent_action,
        "applied_action": parent_action,
        "action_python_type": (
            f"{type(parent_action).__module__}."
            f"{type(parent_action).__qualname__}"
        ),
        "action_identity": {
            "value_equal": True,
            "type_equal": True,
            "order_equal": True,
            "returned_parent_object_unchanged": True,
        },
        "semantic_option_keys": None,
        "semantic_parent_action_keys": None,
        "semantic_proposed_action_keys": None,
        "public_state_material": None,
        "public_state_fingerprint": None,
        "pair_material": None,
        "game_boundary_fingerprint": None,
        "parent_post_fingerprint": None,
        "candidate_post_fingerprint": None,
        "expose_state_fingerprint": None,
        "wall_state_fingerprint": None,
        "expose_projection": None,
        "wall_projection": None,
        "protected_line": None,
        "importance": "UNKNOWN_IMPORTANCE",
        "distance_before": None,
        "distance_without_line": None,
        "threat": None,
        "damage_floor": None,
        "damage_cap": None,
        "continuity": "UNKNOWN",
        "wall_candidates": [],
        "candidate_rows": rows,
        "run_away_value": None,
        "reusable_wall_value": None,
        "sacrifice_wall_value": None,
        "bypass": "UNKNOWN",
        "refusal_progress": "UNKNOWN",
        "safe_release": None,
        "gust_exposure_turns": 0,
        "wall_class": "REJECTED",
        "arbitration_reason": "ABSOLUTE_EMERGENCY_REJECTION",
        "outcome_status": "COUNTERFACTUAL_UNOBSERVED",
        "outcome_events": [],
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "safety_cap": None,
        "hold_entry_turn": None,
        "hold_deadline": None,
        "distance_progress_by_turn": [],
        "rejection_codes": ["METRIC_EXCEPTION"],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "parser_source": (
            "_cumulative_parent._bridge_retaliation_attack_damage"
        ),
        "metric_exception": code,
        "c2_trace_rule_version": None,
    }


def _advance_hold_progress(
    trace: dict[str, Any],
    state: dict[str, Any],
    wall_serial: int | None,
    distance: Any,
    turn: int | None,
) -> list[str]:
    codes = []
    if wall_serial is None or turn is None:
        return codes
    hold = state["holds"].get(wall_serial)
    quality = _distance_quality(distance)
    if not isinstance(hold, dict):
        closed = state.get("closed_holds", {}).get(wall_serial)
        if isinstance(closed, dict):
            trace["hold_entry_turn"] = closed.get("entry_turn")
            trace["hold_deadline"] = closed.get("deadline")
            codes.append(str(closed.get("reason") or "HOLD_CLOSED"))
        return codes
    trace["hold_entry_turn"] = hold["entry_turn"]
    trace["hold_deadline"] = hold["deadline"]
    if turn > hold.get("last_checked_turn", hold["entry_turn"]):
        previous = hold.get("last_quality")
        improved = (
            previous is not None and quality is not None and quality < previous
        )
        hold["distance_progress_by_turn"].append(
            {
                "turn": turn,
                "previous": previous,
                "current": quality,
                "strictly_improved": improved,
            }
        )
        hold["last_checked_turn"] = turn
        hold["last_quality"] = quality
        if not improved:
            codes.append("HOLD_PROGRESS_STALLED")
        if turn >= hold["deadline"]:
            codes.append("HOLD_DEADLINE_REACHED")
    trace["distance_progress_by_turn"] = _safe(
        hold["distance_progress_by_turn"]
    )
    if codes:
        reason = (
            "HOLD_DEADLINE_REACHED"
            if "HOLD_DEADLINE_REACHED" in codes
            else "HOLD_PROGRESS_STALLED"
        )
        state.setdefault("closed_holds", {})[wall_serial] = {
            "entry_turn": hold["entry_turn"],
            "deadline": hold["deadline"],
            "reason": reason,
            "decision_id": hold.get("decision_id"),
        }
        state["holds"].pop(wall_serial, None)
    trace["rejection_codes"].extend(codes)
    return codes


def analyze(
    raw: Any,
    parent_action: Any,
    *,
    c2_trace: Any = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the frozen C4 state machine and return diagnostic evidence only."""
    trace = _base_trace(raw, parent_action, c2_trace)
    owned_state = SHADOW_STATE if state is None else state
    try:
        if not isinstance(raw, dict):
            raise TypeError("raw observation must be a dict")
        option_rows, option_reasons = _option_rows(raw)
        trace["state_machine"].append("VALIDATE_PUBLIC_STATE")
        if _players(raw) is None:
            owned_state["trading_pending"] = None
            trace["rejection_codes"].append("PUBLIC_STATE_INVALID")
            trace["state_machine"].extend(
                ("EMIT_REJECTION", "RETURN_EXACT_PARENT_ACTION")
            )
            return trace
        parent_keys = semantic_action_keys(raw, parent_action, option_rows)
        trace["semantic_parent_action_keys"] = _safe(parent_keys)
        trace["semantic_option_keys"] = sorted(
            [_safe(row["key"]) for row in option_rows],
            key=_canonical,
        )
        if parent_keys is None:
            trace["rejection_codes"].append("PARENT_ACTION_SEMANTIC_UNKNOWN")
        trace["rejection_codes"].extend(option_reasons)
        trace["structural_reasons"].extend(option_reasons)
        public_material = _public_state_material(raw, option_rows)
        public_fp = fingerprint(public_material)
        trace["public_state_material"] = _safe(public_material)
        trace["public_state_fingerprint"] = public_fp
        common_structural = list(option_reasons)
        common_structural.extend(_public_structure_reasons(raw))
        if parent_keys is None:
            common_structural.append("PARENT_ACTION_SEMANTIC_UNKNOWN")
        if common_structural:
            common_structural = sorted(set(common_structural))
            trace["structural_reasons"] = common_structural
            trace["rejection_codes"] = sorted(
                set(trace["rejection_codes"]) | set(common_structural)
            )
            owned_state["trading_pending"] = None
            trace["state_machine"].extend(
                ("EMIT_REJECTION", "RETURN_EXACT_PARENT_ACTION")
            )
            return trace
        boundary = _initialize_boundary(raw, owned_state, public_fp)
        trace["game_boundary_fingerprint"] = boundary
        callback_ordinal = _update_callback_ordinal(owned_state, public_fp)
        _update_public_evidence(raw, owned_state)
        trace["outcome_events"] = _advance_outcomes(
            raw,
            c2_trace,
            owned_state,
        )

        decision = _find_decision(
            raw,
            parent_keys,
            option_rows,
            owned_state,
            public_fp,
            callback_ordinal,
        )
        if decision.get("decision_point") is None:
            trace["rejection_codes"].append(
                str(decision.get("rejection") or "NOT_C4_DECISION_POINT")
            )
            trace["state_machine"].extend(
                ("EMIT_REJECTION", "RETURN_EXACT_PARENT_ACTION")
            )
            return trace
        trace["decision_point"] = decision["decision_point"]
        trace["state_machine"].append("BUILD_COUNTERFACTUAL_PAIR")

        expose_card = decision.get("expose_card")
        line = _line_from_c2(c2_trace, expose_card)
        trace["state_machine"].append("CLASSIFY_PROTECTED_LINE")
        trace.update(
            {
                "protected_line": _safe(line.get("protected_line")),
                "importance": line.get("importance"),
                "distance_before": _safe(line.get("distance_before")),
                "distance_without_line": _safe(
                    line.get("distance_without_line")
                ),
            }
        )
        trace["rejection_codes"].extend(line.get("unsupported_reasons") or [])
        trace["unsupported_reasons"].extend(
            line.get("unsupported_reasons") or []
        )

        expose_threat = _threat_analysis(raw, expose_card, owned_state)
        trace["state_machine"].append("CLASSIFY_EXPOSE_THREAT")
        trace.update(
            {
                "threat": _safe(expose_threat),
                "damage_floor": expose_threat.get("damage_floor"),
                "damage_cap": expose_threat.get("damage_cap"),
                "continuity": expose_threat.get("continuity"),
                "premium_power_pro_multiplicity": expose_threat.get(
                    "premium_power_pro_multiplicity"
                ),
                "evidenced_policy_cap": expose_threat.get(
                    "evidenced_policy_cap"
                ),
                "safety_cap": expose_threat.get("final_safety_cap"),
            }
        )
        trace["unsupported_reasons"].extend(
            expose_threat.get("unsupported_reasons") or []
        )
        trace["rejection_codes"].extend(
            expose_threat.get("unsupported_reasons") or []
        )

        parsed = _players(raw)
        current, mine, _, _, _ = parsed
        turn = _int(current.get("turn"))
        active_rows = _zone(mine, "active")
        active = active_rows[0] if active_rows and len(active_rows) == 1 else None
        active_serial = _serial(active)
        hold_codes = _advance_hold_progress(
            trace,
            owned_state,
            active_serial,
            trace.get("distance_before"),
            turn,
        )
        global_structural_reasons = []
        global_unsupported_reasons = list(
            line.get("unsupported_reasons") or []
        )
        semantic_sorted = sorted(
            [_safe(row["key"]) for row in option_rows], key=_canonical
        )
        wall_serials = sorted(
            _serial(card)
            for _, _, card in decision.get("wall_cards") or []
            if _serial(card) is not None
        )
        protected_serial = (
            (line.get("protected_line") or {}).get("top_serial")
        )
        pair_material = {
            "public_state_fingerprint": public_fp,
            "decision_point": trace["decision_point"],
            "semantic_action_keys": semantic_sorted,
            "protected_serial": protected_serial,
            "wall_serials": wall_serials,
        }
        trace["pair_material"] = _safe(pair_material)
        pair_id = fingerprint(pair_material)
        trace["pair_id"] = pair_id
        trace["decision_id"] = fingerprint(
            {
                "pair_id": pair_id,
                "game_boundary_fingerprint": boundary,
                "turn": turn,
                "transaction_stage": "SHADOW_ONLY",
            }
        )

        expose_state = {
            "projection": "EXPOSE_STATE",
            "decision_point": trace["decision_point"],
            "public_board": _public_board_material(raw),
            "semantic_parent_action_keys": _safe(parent_keys),
            "active": _card_snapshot(expose_card),
            "protected_line": trace["protected_line"],
            "distance_before": trace["distance_before"],
            "distance_without_line": trace["distance_without_line"],
            "threat": expose_threat,
            "resource_state": {
                "own_deck_count": _int(mine.get("deckCount")),
                "own_hand_count": _int(mine.get("handCount")),
                "own_prize_count": _prize_count(mine),
            },
        }
        trace["expose_projection"] = _safe(expose_state)
        trace["expose_state_fingerprint"] = fingerprint(expose_state)
        trace["parent_post_fingerprint"] = trace["expose_state_fingerprint"]

        rows = []
        run_option = decision.get("run_away_option")
        run_row = _run_away_row(
            raw,
            option_index=run_option.get("index")
            if isinstance(run_option, dict)
            else None,
            option_key=run_option.get("key")
            if isinstance(run_option, dict)
            else None,
            c2_trace=c2_trace,
            threat=expose_threat,
            public_state=owned_state,
            decision_point=trace["decision_point"],
            global_structural_reasons=global_structural_reasons,
            global_unsupported_reasons=global_unsupported_reasons,
        )
        rows.append(run_row)

        reusable_rows = []
        sacrifice_rows = []
        wall_projection_rows = []
        for option_index, option_key, wall in decision.get("wall_cards") or []:
            if wall is None:
                continue
            projected_wall_raw = _project_wall_state(raw, wall)
            wall_threat = _threat_analysis(
                projected_wall_raw or {},
                wall,
                owned_state,
            )
            protected_stays_bench = _serial(wall) != protected_serial
            bypass = _bypass_class(
                owned_state, wall_threat, protected_stays_bench
            )
            trace["unsupported_reasons"].extend(
                wall_threat.get("unsupported_reasons") or []
            )
            candidate_row = None
            if _card_id(wall) == DUDUNSPARCE:
                candidate_row = _wall_row(
                        REUSABLE,
                        raw=raw,
                        option_index=option_index,
                        option_key=option_key,
                        wall=wall,
                        line=line,
                        expose_threat=expose_threat,
                        wall_threat=wall_threat,
                        bypass=bypass,
                        c2_trace=c2_trace,
                        public_state=owned_state,
                        turn=turn or 0,
                        decision_point=trace["decision_point"],
                        global_structural_reasons=global_structural_reasons,
                        hold_codes=(
                            hold_codes
                            if _serial(wall) == active_serial
                            else ()
                        ),
                        existing_hold=owned_state["holds"].get(
                            _serial(wall)
                        ),
                    )
                reusable_rows.append(candidate_row)
            elif _card_id(wall) == DUNSPARCE:
                candidate_row = _wall_row(
                        SACRIFICE,
                        raw=raw,
                        option_index=option_index,
                        option_key=option_key,
                        wall=wall,
                        line=line,
                        expose_threat=expose_threat,
                        wall_threat=wall_threat,
                        bypass=bypass,
                        c2_trace=c2_trace,
                        public_state=owned_state,
                        turn=turn or 0,
                        decision_point=trace["decision_point"],
                        global_structural_reasons=global_structural_reasons,
                        hold_codes=(
                            hold_codes
                            if _serial(wall) == active_serial
                            else ()
                        ),
                        existing_hold=owned_state["holds"].get(
                            _serial(wall)
                        ),
                    )
                sacrifice_rows.append(candidate_row)
            if candidate_row is not None:
                metrics = candidate_row.get("metrics") or {}
                wall_projection_rows.append(
                    {
                        "kind": candidate_row["kind"],
                        "option_index": option_index,
                        "semantic_action_key": _safe(option_key),
                        "wall": _card_snapshot(wall),
                        "public_board": _public_board_material(
                            projected_wall_raw or {}
                        ),
                        "threat": wall_threat,
                        "bypass": bypass,
                        "resource_state": {
                            "resource_loss": metrics.get("resource_loss"),
                            "lost_draw3": metrics.get("lost_draw3"),
                            "own_prize_loss": metrics.get(
                                "own_prize_loss"
                            ),
                        },
                        "refusal_state": {
                            "protected_readiness": metrics.get(
                                "protected_readiness"
                            ),
                            "hold_entry_turn": metrics.get(
                                "hold_entry_turn"
                            ),
                            "hold_deadline": metrics.get(
                                "hold_deadline"
                            ),
                            "distance": _safe(
                                line.get("distance_before")
                            ),
                            "progress_events": _safe(
                                trace.get("distance_progress_by_turn")
                            ),
                        },
                        "release_state": _safe(
                            metrics.get("safe_release")
                        ),
                        "certification": candidate_row.get(
                            "certification"
                        ),
                    }
                )

        def best_wall(
            candidates: list[dict[str, Any]], kind: str
        ) -> dict[str, Any]:
            if not candidates:
                return _row_template(kind)
            nondominated = [
                row
                for row in candidates
                if not any(
                    other is not row and _dominates(other, row)
                    for other in candidates
                )
            ]
            order = {"STRICT": 0, "PRESERVE_CHANCE": 1, "REJECTED": 2}
            return sorted(
                nondominated,
                key=lambda row: (
                    order.get(row.get("certification"), 3),
                    len(row.get("rejection_codes") or []),
                    -int(
                        ((row.get("pareto_vector") or {}).get(
                            "safe_release"
                        ))
                        or 0
                    ),
                    _canonical(row.get("semantic_action_key")),
                ),
            )[0]

        reusable = best_wall(reusable_rows, REUSABLE)
        sacrifice = best_wall(sacrifice_rows, SACRIFICE)
        no_wall = _row_template(NO_WALL)
        no_wall.update(
            {
                "wall_class": "PARENT_FALLBACK",
                "certification": "AVAILABLE",
                "semantic_action_key": _safe(parent_keys),
                "rejection_codes": [],
            }
        )
        rows = [run_row, reusable, sacrifice, no_wall]
        trace["state_machine"].append("ENUMERATE_FOUR_ALTERNATIVES")
        trace["candidate_rows"] = _safe(rows)
        trace["wall_candidates"] = _safe(
            [row for row in rows if row["kind"] in (REUSABLE, SACRIFICE)]
        )
        trace["run_away_value"] = _safe(run_row)
        trace["reusable_wall_value"] = _safe(reusable)
        trace["sacrifice_wall_value"] = _safe(sacrifice)
        trace["state_machine"].append("CERTIFY_STRICT_OR_CHANCE")

        chosen_kind, reason = pareto_arbitrate(rows)
        trace["state_machine"].append("PARETO_ARBITRATE")
        trace["arbitration_reason"] = reason
        chosen = next(row for row in rows if row["kind"] == chosen_kind)
        if chosen_kind == NO_WALL:
            trace["rejection_codes"] = sorted(
                set(trace.get("rejection_codes") or [])
                | {
                    code
                    for row in rows[:-1]
                    for code in (row.get("rejection_codes") or [])
                }
            )
        else:
            trace["rejection_codes"] = sorted(
                set(option_reasons)
                | set(chosen.get("rejection_codes") or [])
            )
        if chosen_kind == RUN_AWAY:
            trace["unsupported_reasons"] = sorted(
                set(chosen.get("unsupported_reasons") or [])
            )
        elif chosen_kind == NO_WALL:
            trace["unsupported_reasons"] = sorted(
                set(line.get("unsupported_reasons") or [])
                | set(expose_threat.get("unsupported_reasons") or [])
                | {
                    code
                    for row in rows[:-1]
                    for code in (row.get("unsupported_reasons") or [])
                }
            )
        else:
            trace["unsupported_reasons"] = sorted(
                set(line.get("unsupported_reasons") or [])
                | set(expose_threat.get("unsupported_reasons") or [])
                | set(chosen.get("unsupported_reasons") or [])
            )
        trace["structural_reasons"] = sorted(
            set(option_reasons)
            | (
                {
                    code
                    for row in rows[:-1]
                    for code in (row.get("structural_reasons") or [])
                }
                if chosen_kind == NO_WALL
                else set(chosen.get("structural_reasons") or [])
            )
        )
        proposed_action = parent_action
        proposed_keys = parent_keys
        if chosen_kind != NO_WALL and type(chosen.get("option_index")) is int:
            proposed_action = [chosen["option_index"]]
            proposed_keys = [chosen["semantic_action_key"]]
        trace["proposed_action"] = _safe(proposed_action)
        trace["semantic_proposed_action_keys"] = _safe(proposed_keys)
        trace["wall_class"] = chosen.get("wall_class")
        trace["safe_release"] = _safe(
            (chosen.get("metrics") or {}).get("safe_release")
        )
        chosen_hold_entry = (chosen.get("metrics") or {}).get(
            "hold_entry_turn"
        )
        chosen_hold_deadline = (chosen.get("metrics") or {}).get(
            "hold_deadline"
        )
        if chosen_hold_entry is not None:
            trace["hold_entry_turn"] = chosen_hold_entry
        if chosen_hold_deadline is not None:
            trace["hold_deadline"] = chosen_hold_deadline
        trace["gust_exposure_turns"] = (
            chosen.get("metrics") or {}
        ).get("gust_exposure") or 0
        trace["refusal_progress"] = (
            "CERTIFIED"
            if chosen.get("certification") == "STRICT"
            else "POSSIBLE"
            if chosen.get("certification") == "PRESERVE_CHANCE"
            else UNKNOWN
        )
        trace["certified_draw_count"] = (
            run_row.get("metrics") or {}
        ).get("certified_draw_count", 0)
        trace["certified_draw_damage_delta"] = (
            run_row.get("metrics") or {}
        ).get("certified_draw_damage_delta", 0)
        chosen_projection = next(
            (
                projection
                for projection in wall_projection_rows
                if projection.get("kind") == chosen_kind
                and _canonical(projection.get("semantic_action_key"))
                == _canonical(chosen.get("semantic_action_key"))
            ),
            None,
        )
        trace["bypass"] = (
            chosen_projection.get("bypass")
            if isinstance(chosen_projection, dict)
            else "NO_CHOSEN_WALL_BYPASS"
        )
        wall_state = {
            "projection": "WALL_STATE",
            "decision_point": trace["decision_point"],
            "expose_state_fingerprint": trace[
                "expose_state_fingerprint"
            ],
            "alternatives": wall_projection_rows,
            "chosen_kind": chosen_kind,
            "chosen_semantic_action_key": _safe(
                chosen.get("semantic_action_key")
            ),
            "chosen": _safe(chosen_projection),
        }
        trace["wall_projection"] = _safe(wall_state)
        trace["wall_state_fingerprint"] = fingerprint(wall_state)
        trace["candidate_post_fingerprint"] = trace["wall_state_fingerprint"]

        parent_agreement = (
            proposed_keys is not None
            and parent_keys is not None
            and _canonical(proposed_keys) == _canonical(parent_keys)
            and chosen_kind != NO_WALL
        )
        if parent_agreement:
            trace["outcome_status"] = "PARENT_AGREEMENT"
            _open_outcome(
                owned_state,
                trace,
                chosen_kind,
                chosen,
                active,
                mine,
                turn,
            )
            if chosen_kind in (REUSABLE, SACRIFICE):
                wall_serial = (chosen.get("wall") or {}).get("serial")
                deadline = trace.get("hold_deadline")
                quality = _distance_quality(trace.get("distance_before"))
                if (
                    wall_serial is not None
                    and turn is not None
                    and deadline is not None
                    and wall_serial
                    not in owned_state.get("closed_holds", {})
                ):
                    owned_state["holds"].setdefault(
                        wall_serial,
                        {
                            "entry_turn": turn,
                            "deadline": deadline,
                            "last_checked_turn": turn,
                            "last_quality": quality,
                            "distance_progress_by_turn": [],
                            "decision_id": trace["decision_id"],
                        },
                    )

        trace["rejection_codes"] = sorted(set(trace["rejection_codes"]))
        trace["unsupported_reasons"] = sorted(
            set(trace["unsupported_reasons"])
        )
        trace["structural_reasons"] = sorted(
            set(trace["structural_reasons"])
        )
        trace["state_machine"].extend(
            ("EMIT_SHADOW", "RETURN_EXACT_PARENT_ACTION")
        )
        return trace
    except Exception as error:
        return rejection_trace(
            raw,
            parent_action,
            error,
            c2_trace=c2_trace,
        )


__all__ = [
    "ANALYZER_SHA256",
    "CANDIDATE_KINDS",
    "CHANCE",
    "PARENT_CLOSURE_SHA256",
    "REJECTED",
    "RULE_VERSION",
    "SCHEMA_VERSION",
    "SHADOW_STATE",
    "STATE_MACHINE",
    "STRICT",
    "analyze",
    "emergency_trace",
    "fingerprint",
    "fresh_state",
    "pareto_arbitrate",
    "policy_closure_sha256",
    "rejection_trace",
    "reset",
    "semantic_action_keys",
    "semantic_option_key",
]
