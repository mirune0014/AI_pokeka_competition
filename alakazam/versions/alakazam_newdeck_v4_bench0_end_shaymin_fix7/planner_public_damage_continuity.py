"""Pure public-damage and Bench-0 survival analysis for C3 FIX5.

The functions in this module are deliberately stateless.  They consume only
the current public observation, a caller-owned physical-copy ledger snapshot,
and the complete parent's semantic action.  Unsupported formulae and
continuations fail closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 5
RULE_VERSION = "V4_PUBLIC_SURVIVAL_BENCH0_FIX5"
PARENT_CLOSURE_SHA256 = (
    "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
)

PLAY = 7
ATTACK = 13
END = 14
MAIN = 0

FIGHTING = 6
PSYCHIC = 5
RAINBOW = 10

PREMIUM_POWER_PRO = 1141
POWER_PRO_LIMIT = 4
FIGHTING_FAMILY = frozenset({673, 674, 675, 676, 677, 678})
LUNATONE = 675

SHAYMIN = 343
ABRA = 741
DUNSPARCE = 305
KADABRA = 742
DUDUNSPARCE = 66
PSYCHIC_ENERGY_IDS = frozenset({5, 19})
CANDIDATE_BASICS = frozenset({SHAYMIN, ABRA, DUNSPARCE})

SUPER_PSY_BOLT = 1071
POWERFUL_HAND = 1072

UNKNOWN = "UNKNOWN"
REPEATABLE_READY = "REPEATABLE_READY"
RECHARGE_REQUIRED = "RECHARGE_REQUIRED"
NO_READY_ATTACK = "NO_READY_ATTACK"

# Frozen exact metadata from attacks 976--983.
ATTACK_ROWS = {
    976: {
        "pokemon_id": 673,
        "base": 10,
        "cost": (FIGHTING,),
        "continuity": REPEATABLE_READY,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
    977: {
        "pokemon_id": 673,
        "base": 30,
        "cost": (FIGHTING, FIGHTING),
        "continuity": REPEATABLE_READY,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
    978: {
        "pokemon_id": 674,
        "base": 210,
        "cost": (FIGHTING, FIGHTING, FIGHTING),
        "continuity": REPEATABLE_READY,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 70,
    },
    979: {
        "pokemon_id": 675,
        "base": 50,
        "cost": (FIGHTING, FIGHTING),
        "continuity": REPEATABLE_READY,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
    980: {
        "pokemon_id": 676,
        "base": 70,
        "cost": (FIGHTING,),
        "continuity": REPEATABLE_READY,
        "ignore_wr": True,
        "requires_lunatone": True,
        "self_damage": 0,
    },
    981: {
        "pokemon_id": 677,
        "base": 30,
        "cost": (FIGHTING,),
        "continuity": RECHARGE_REQUIRED,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
    982: {
        "pokemon_id": 678,
        "base": 130,
        "cost": (FIGHTING,),
        "continuity": REPEATABLE_READY,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
    983: {
        "pokemon_id": 678,
        "base": 270,
        "cost": (FIGHTING, FIGHTING),
        "continuity": RECHARGE_REQUIRED,
        "ignore_wr": False,
        "requires_lunatone": False,
        "self_damage": 0,
    },
}

ATTACKS_BY_POKEMON = {
    card_id: tuple(
        attack_id
        for attack_id, row in ATTACK_ROWS.items()
        if row["pokemon_id"] == card_id
    )
    for card_id in FIGHTING_FAMILY
}

# Weakness/resistance for every own Basic/evolution the exact deck can expose.
# The comparison uses the current HP from the public observation, not printed HP.
OWN_DEFENSE = {
    66: {"weakness": FIGHTING, "resistance": None},
    305: {"weakness": FIGHTING, "resistance": None},
    343: {"weakness": 2, "resistance": None},
    741: {"weakness": 7, "resistance": FIGHTING},
    742: {"weakness": 7, "resistance": FIGHTING},
    743: {"weakness": 7, "resistance": FIGHTING},
}

OPPONENT_PSYCHIC_DEFENSE = {
    673: {"weakness": PSYCHIC, "resistance": None},
    674: {"weakness": PSYCHIC, "resistance": None},
    675: {"weakness": 1, "resistance": None},
    676: {"weakness": 1, "resistance": None},
    677: {"weakness": PSYCHIC, "resistance": None},
    678: {"weakness": PSYCHIC, "resistance": None},
}

KNOWN_NON_DAMAGE_TOOLS = frozenset({1159})  # Hero's Cape; current HP is public.


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


def semantic_action(obs: dict[str, Any], action: Any) -> tuple[str, int | None] | None:
    select = obs.get("select") if isinstance(obs, dict) else None
    options = select.get("option") if isinstance(select, dict) else None
    if (
        not isinstance(action, (list, tuple))
        or len(action) != 1
        or not isinstance(options, list)
    ):
        return None
    index = _int(action[0])
    if index is None or not 0 <= index < len(options):
        return None
    option = options[index]
    if not isinstance(option, dict):
        return None
    option_type = _int(option.get("type"))
    if option_type == ATTACK:
        attack_id = _int(option.get("attackId"))
        return ("ATTACK", attack_id) if attack_id is not None else None
    if option_type == END:
        return ("END", None)
    return ("OTHER", option_type)


def _promotion_removal_context(
    obs: dict[str, Any], action: Any
) -> str | None:
    select = obs.get("select") if isinstance(obs, dict) else None
    options = select.get("option") if isinstance(select, dict) else None
    if not isinstance(select, dict) or not isinstance(options, list):
        return None
    if _int(select.get("context")) == 4:
        return "FORCED_ACTIVE_PROMOTION"
    if (
        isinstance(action, (list, tuple))
        and len(action) == 1
        and type(action[0]) is int
        and 0 <= action[0] < len(options)
    ):
        option = options[action[0]]
        if (
            isinstance(option, dict)
            and _int(option.get("type")) == 10
            and _int(option.get("area")) == 4
        ):
            return "ACTIVE_ABILITY_REMOVAL"
    return None


def rebind_semantic_action(
    obs: dict[str, Any], semantic: tuple[str, int | None]
) -> list[int] | None:
    select = obs.get("select") if isinstance(obs, dict) else None
    options = select.get("option") if isinstance(select, dict) else None
    if not isinstance(options, list):
        return None
    matches = []
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            continue
        option_type = _int(option.get("type"))
        if semantic[0] == "ATTACK":
            if option_type == ATTACK and _int(option.get("attackId")) == semantic[1]:
                matches.append(index)
        elif semantic[0] == "END" and option_type == END:
            matches.append(index)
    return [matches[0]] if len(matches) == 1 else None


def _players(obs: dict[str, Any]):
    current = obs.get("current") if isinstance(obs, dict) else None
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


def _card_id(card: Any) -> int | None:
    return _int(card.get("id", card.get("cardId"))) if isinstance(card, dict) else None


def _serial(card: Any) -> int | None:
    return _int(card.get("serial")) if isinstance(card, dict) else None


def _owner(card: Any) -> int | None:
    return _int(card.get("playerIndex")) if isinstance(card, dict) else None


def _valid_card(card: Any, owner: int) -> bool:
    serial = _serial(card)
    return (
        isinstance(card, dict)
        and (_card_id(card) or 0) > 0
        and serial is not None
        and serial >= 0
        and _owner(card) == owner
    )


def _zone(player: dict[str, Any], name: str) -> list[dict[str, Any]] | None:
    value = player.get(name)
    if not isinstance(value, list) or not all(isinstance(card, dict) for card in value):
        return None
    return value


def _strict_nonnegative_int_set(value: Any) -> set[int] | None:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return None
    if any(type(item) is not int or item < 0 for item in value):
        return None
    return set(value)


def premium_power_pro_envelope(
    ledger: dict[str, Any],
    *,
    phase: str,
) -> dict[str, Any]:
    """Compute the amended physical-copy floor/cap for one attack phase."""
    base = {
        "status": UNKNOWN,
        "phase": phase,
        "family_marker_ids": [],
        "power_pro_seen_serials": [],
        "committed_serials": [],
        "unavailable_serials": [],
        "premium_floor": None,
        "premium_cap": None,
        "premium_power_pro_multiplicity": None,
        "provenance": [],
        "unsupported_reasons": [],
    }
    if not isinstance(ledger, dict) or not ledger.get("boundary_certified"):
        base["unsupported_reasons"].append("PUBLIC_LEDGER_BOUNDARY_AMBIGUOUS")
        return base
    if ledger.get("ambiguous"):
        base["unsupported_reasons"].append("PUBLIC_LEDGER_AMBIGUOUS")
        return base
    marker_ids = _strict_nonnegative_int_set(
        ledger.get("family_marker_ids")
    )
    power_pro_serials = _strict_nonnegative_int_set(
        ledger.get("power_pro_seen_serials")
    )
    if (
        ledger.get("same_battle_power_pro_seen") is not True
        or power_pro_serials is None
        or not power_pro_serials
    ):
        base["unsupported_reasons"].append(
            "ARCHETYPE_COMMON_UNCONFIRMED"
        )
        return base
    if (
        marker_ids is None
        or len(marker_ids) < 3
        or 676 not in marker_ids
        or not marker_ids <= FIGHTING_FAMILY
    ):
        base["unsupported_reasons"].append("FIGHTING_FAMILY_MARKER_MISSING")
        return base

    committed = _strict_nonnegative_int_set(
        ledger.get("committed_current_turn")
    )
    unavailable = _strict_nonnegative_int_set(ledger.get("unavailable"))
    if committed is None or unavailable is None:
        base["unsupported_reasons"].append("POWER_PRO_SERIAL_INVALID")
        return base
    if (
        len(power_pro_serials) > POWER_PRO_LIMIT
        or len(committed) > POWER_PRO_LIMIT
        or len(unavailable) > POWER_PRO_LIMIT
        or len(committed | unavailable) > POWER_PRO_LIMIT
    ):
        base["unsupported_reasons"].append("POWER_PRO_COPY_LIMIT_EXCEEDED")
        return base
    if not (committed | unavailable) <= power_pro_serials:
        base["unsupported_reasons"].append(
            "POWER_PRO_SERIAL_EVIDENCE_INCONSISTENT"
        )
        return base
    if phase == "current":
        additional = max(
            0, POWER_PRO_LIMIT - len(committed | unavailable)
        )
        stack_max = len(committed) + additional
        premium_floor = 30 * len(committed)
        premium_cap = 30 * stack_max
    elif phase == "future":
        stack_max = max(0, POWER_PRO_LIMIT - len(unavailable))
        premium_floor = 0
        premium_cap = 30 * stack_max
    else:
        base["unsupported_reasons"].append("POWER_PRO_PHASE_UNKNOWN")
        return base
    base.update(
        {
            "status": "CERTIFIED",
            "family_marker_ids": sorted(marker_ids),
            "power_pro_seen_serials": sorted(power_pro_serials),
            "committed_serials": sorted(committed),
            "unavailable_serials": sorted(unavailable),
            "premium_floor": premium_floor,
            "premium_cap": premium_cap,
            "premium_power_pro_multiplicity": {
                "deck_limit": POWER_PRO_LIMIT,
                "committed_count": len(committed),
                "unavailable_count": len(unavailable),
                "stack_max": stack_max,
            },
            "provenance": (
                ["PUBLIC_COMMITTED"] if committed else []
            )
            + ["REVEALED_AND_ARCHETYPE_COMMON_POSSIBLE"],
        }
    )
    return base


def _energy_missing(pokemon: dict[str, Any], cost: tuple[int, ...]) -> int | None:
    energies = pokemon.get("energies")
    energy_cards = pokemon.get("energyCards")
    if (
        not isinstance(energies, list)
        or not isinstance(energy_cards, list)
        or len(energies) != len(energy_cards)
        or not all(isinstance(card, dict) for card in energy_cards)
    ):
        return None
    available = []
    for energy in energies:
        energy_type = _int(energy)
        if energy_type not in (FIGHTING, RAINBOW):
            return None
        available.append(energy_type)
    needed = list(cost)
    for energy_type in available:
        if FIGHTING in needed and energy_type in (FIGHTING, RAINBOW):
            needed.remove(FIGHTING)
    return len(needed)


def _damage_after_wr(
    damage: int,
    *,
    weakness: int | None,
    resistance: int | None,
    ignore_wr: bool,
) -> tuple[int, list[dict[str, Any]]]:
    steps = [{"kind": "base_plus_modifier", "damage": damage}]
    if ignore_wr:
        steps.append({"kind": "ignore_weakness_resistance", "damage": damage})
        return damage, steps
    if weakness == FIGHTING:
        damage *= 2
        steps.append({"kind": "weakness_x2", "damage": damage})
    if resistance == FIGHTING:
        damage = max(0, damage - 30)
        steps.append({"kind": "resistance_minus_30", "damage": damage})
    return damage, steps


def _previously_disabled(
    ledger: dict[str, Any], pokemon: dict[str, Any], attack_id: int
) -> bool | None:
    if ATTACK_ROWS[attack_id]["continuity"] != RECHARGE_REQUIRED:
        return False
    last_attack = ledger.get("last_attack_by_serial")
    serial = _serial(pokemon)
    if not isinstance(last_attack, dict) or serial is None:
        return None
    value = last_attack.get(str(serial), last_attack.get(serial))
    if value is None:
        return False
    if (
        not isinstance(value, dict)
        or _int(value.get("attack_id")) is None
        or _int(value.get("turn")) is None
        or _int(ledger.get("turn")) is None
    ):
        return None
    # The current callback is our turn; the immediately preceding turn is the
    # opposing player's previous turn.
    return (
        _int(value.get("attack_id")) == attack_id
        and _int(value.get("turn")) == _int(ledger.get("turn")) - 1
    )


def _inactive_damage_row(
    pokemon: dict[str, Any],
    *,
    zone_name: str,
    attack_id: int,
    active_hp: int,
    continuity: str,
    reason: str,
) -> dict[str, Any]:
    attack = ATTACK_ROWS[attack_id]
    return {
        "pokemon_id": _card_id(pokemon),
        "serial": _serial(pokemon),
        "zone": zone_name,
        "attack_id": attack_id,
        "damage_floor": None,
        "damage_cap": None,
        "damage_formula": None,
        "modifier_provenance": [],
        "activation_class": (
            UNKNOWN if continuity == UNKNOWN else "NO_SUPPORTED_ACTIVATION"
        ),
        "hidden_requirements": [],
        "continuity": continuity,
        "stochastic_effects": [],
        "unsupported_reasons": [reason],
        "active_hp": active_hp,
        "floor_ko": False,
        "cap_ko": False,
        "self_damage": attack["self_damage"],
    }


def opponent_damage_rows(
    obs: dict[str, Any], ledger: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    parsed = _players(obs)
    if parsed is None:
        return [], ["PUBLIC_PLAYER_STATE_INVALID"]
    current, mine, theirs, _, opponent = parsed
    own_active = _zone(mine, "active")
    opponent_active = _zone(theirs, "active")
    opponent_bench = _zone(theirs, "bench")
    if (
        own_active is None
        or len(own_active) != 1
        or opponent_active is None
        or len(opponent_active) != 1
        or opponent_bench is None
    ):
        return [], ["ACTIVE_OR_BENCH_SHAPE_UNSUPPORTED"]
    defender = own_active[0]
    if not _valid_card(defender, _int(current.get("yourIndex"))):
        return [], ["OWN_ACTIVE_IDENTITY_INVALID"]
    defense = OWN_DEFENSE.get(_card_id(defender))
    tools = defender.get("tools")
    if defense is None or not isinstance(tools, list) or tools:
        return [], ["OWN_DEFENSE_METADATA_UNSUPPORTED"]
    hp = _int(defender.get("hp"))
    if hp is None or hp <= 0:
        return [], ["OWN_ACTIVE_HP_INVALID"]
    stadium = current.get("stadium")
    if not isinstance(stadium, list) or stadium:
        return [], ["STADIUM_DAMAGE_EFFECT_UNSUPPORTED"]

    power = premium_power_pro_envelope(ledger, phase="future")
    if power["status"] != "CERTIFIED":
        return [], list(power["unsupported_reasons"])

    rows = []
    for zone_name, pokemon_rows in (
        ("ACTIVE", opponent_active),
        ("BENCH", opponent_bench),
    ):
        for pokemon in pokemon_rows:
            card_id = _card_id(pokemon)
            if card_id not in FIGHTING_FAMILY or not _valid_card(pokemon, opponent):
                continue
            tools = pokemon.get("tools")
            unsupported_tools = not isinstance(tools, list) or any(
                _card_id(tool) not in KNOWN_NON_DAMAGE_TOOLS for tool in tools
            )
            for attack_id in ATTACKS_BY_POKEMON.get(card_id, ()):
                attack = ATTACK_ROWS[attack_id]
                if unsupported_tools:
                    rows.append(
                        _inactive_damage_row(
                            pokemon,
                            zone_name=zone_name,
                            attack_id=attack_id,
                            active_hp=hp,
                            continuity=UNKNOWN,
                            reason="ATTACKING_TOOL_EFFECT_UNSUPPORTED",
                        )
                    )
                    continue
                missing = _energy_missing(pokemon, attack["cost"])
                disabled = _previously_disabled(ledger, pokemon, attack_id)
                if missing is None or disabled is None:
                    rows.append(
                        _inactive_damage_row(
                            pokemon,
                            zone_name=zone_name,
                            attack_id=attack_id,
                            active_hp=hp,
                            continuity=UNKNOWN,
                            reason=(
                                "ATTACK_ENERGY_METADATA_UNSUPPORTED"
                                if missing is None
                                else "ATTACK_RESTRICTION_LEDGER_UNKNOWN"
                            ),
                        )
                    )
                    continue
                if missing > 1 or disabled:
                    rows.append(
                        _inactive_damage_row(
                            pokemon,
                            zone_name=zone_name,
                            attack_id=attack_id,
                            active_hp=hp,
                            continuity=NO_READY_ATTACK,
                            reason=(
                                "MORE_THAN_ONE_ATTACHMENT_REQUIRED"
                                if missing > 1
                                else "ATTACK_CURRENTLY_RESTRICTED"
                            ),
                        )
                    )
                    continue
                if attack["requires_lunatone"] and not any(
                    _card_id(card) == LUNATONE for card in opponent_bench
                ):
                    rows.append(
                        _inactive_damage_row(
                            pokemon,
                            zone_name=zone_name,
                            attack_id=attack_id,
                            active_hp=hp,
                            continuity=NO_READY_ATTACK,
                            reason="LUNATONE_REQUIREMENT_UNMET",
                        )
                    )
                    continue
                hidden_requirements = []
                if missing == 1:
                    hidden_requirements.append("ONE_FIGHTING_ATTACHMENT")
                if zone_name == "BENCH":
                    hidden_requirements.append("BENCH_TO_ACTIVE_SWITCH")
                if zone_name == "ACTIVE":
                    if any(bool(theirs.get(flag)) for flag in ("asleep", "paralyzed")):
                        rows.append(
                            _inactive_damage_row(
                                pokemon,
                                zone_name=zone_name,
                                attack_id=attack_id,
                                active_hp=hp,
                                continuity=NO_READY_ATTACK,
                                reason="ACTIVE_ATTACK_PREVENTED_BY_STATUS",
                            )
                        )
                        continue
                    if bool(theirs.get("confused")):
                        rows.append(
                            _inactive_damage_row(
                                pokemon,
                                zone_name=zone_name,
                                attack_id=attack_id,
                                active_hp=hp,
                                continuity=UNKNOWN,
                                reason="CONFUSION_COIN_UNSUPPORTED",
                            )
                        )
                        continue
                activation_class = (
                    "ACTIVE_READY"
                    if zone_name == "ACTIVE" and missing == 0
                    else "ACTIVE_ONE_ATTACHMENT_POSSIBLE"
                    if zone_name == "ACTIVE"
                    else "BENCH_READY_EXACT_SWITCH"
                    if missing == 0
                    else "BENCH_ONE_ATTACHMENT_AND_SWITCH_POSSIBLE"
                )
                floor_modifier = (
                    power["premium_floor"]
                    if not hidden_requirements
                    else None
                )
                floor = None
                floor_steps = []
                if floor_modifier is not None:
                    floor, floor_steps = _damage_after_wr(
                        attack["base"] + floor_modifier,
                        weakness=defense["weakness"],
                        resistance=defense["resistance"],
                        ignore_wr=attack["ignore_wr"],
                    )
                cap, cap_steps = _damage_after_wr(
                    attack["base"] + power["premium_cap"],
                    weakness=defense["weakness"],
                    resistance=defense["resistance"],
                    ignore_wr=attack["ignore_wr"],
                )
                continuity = attack["continuity"]
                if attack["self_damage"]:
                    attacker_hp = _int(pokemon.get("hp"))
                    if attacker_hp is None or attacker_hp <= 0:
                        continuity = UNKNOWN
                    elif attacker_hp <= attack["self_damage"]:
                        continuity = NO_READY_ATTACK
                rows.append(
                    {
                        "pokemon_id": card_id,
                        "serial": _serial(pokemon),
                        "zone": zone_name,
                        "attack_id": attack_id,
                        "damage_floor": floor,
                        "damage_cap": cap,
                        "damage_formula": {
                            "base": attack["base"],
                            "premium_floor": floor_modifier,
                            "premium_cap": power["premium_cap"],
                            "floor_steps": floor_steps,
                            "cap_steps": cap_steps,
                        },
                        "modifier_provenance": list(power["provenance"]),
                        "activation_class": activation_class,
                        "hidden_requirements": hidden_requirements,
                        "continuity": continuity,
                        "stochastic_effects": [],
                        "unsupported_reasons": [],
                        "active_hp": hp,
                        "floor_ko": floor is not None and floor >= hp,
                        "cap_ko": cap >= hp,
                        "self_damage": attack["self_damage"],
                    }
                )
    return rows, []


def _own_attack_projection(
    obs: dict[str, Any],
    semantic: tuple[str, int | None],
    *,
    hand_delta: int,
) -> dict[str, Any] | None:
    parsed = _players(obs)
    if parsed is None:
        return None
    current, mine, theirs, owner, opponent = parsed
    own_active = _zone(mine, "active")
    opponent_active = _zone(theirs, "active")
    opponent_bench = _zone(theirs, "bench")
    hand = _zone(mine, "hand")
    if (
        own_active is None
        or len(own_active) != 1
        or opponent_active is None
        or len(opponent_active) != 1
        or opponent_bench is None
        or hand is None
    ):
        return None
    attacker = own_active[0]
    target = opponent_active[0]
    if not _valid_card(attacker, owner) or not _valid_card(target, opponent):
        return None
    if semantic[0] == "END":
        return {
            "semantic": ["END", None],
            "damage": 0,
            "outcome": "END",
            "ko": False,
            "terminal_win": False,
            "last_prize_win": False,
            "threat_active_removed": False,
        }
    attack_id = semantic[1]
    if attack_id not in (SUPER_PSY_BOLT, POWERFUL_HAND):
        return None
    if attack_id == SUPER_PSY_BOLT and _card_id(attacker) != KADABRA:
        return None
    if attack_id == POWERFUL_HAND and _card_id(attacker) != 743:
        return None
    if any(bool(mine.get(flag)) for flag in ("asleep", "paralyzed", "confused")):
        return None
    energies = attacker.get("energies")
    if not isinstance(energies, list) or PSYCHIC not in {
        _int(value) for value in energies
    }:
        return None
    target_id = _card_id(target)
    defense = OPPONENT_PSYCHIC_DEFENSE.get(target_id)
    target_tools = target.get("tools")
    if (
        defense is None
        or not isinstance(target_tools, list)
        or any(_card_id(tool) not in KNOWN_NON_DAMAGE_TOOLS for tool in target_tools)
    ):
        return None
    target_hp = _int(target.get("hp"))
    if target_hp is None or target_hp <= 0:
        return None
    if attack_id == SUPER_PSY_BOLT:
        damage = 30
        if defense["weakness"] == PSYCHIC:
            damage *= 2
        if defense["resistance"] == PSYCHIC:
            damage = max(0, damage - 30)
    else:
        hand_count = len(hand) + hand_delta
        if hand_count < 0:
            return None
        damage = 20 * hand_count
    ko = damage >= target_hp
    prizes = mine.get("prize")
    if not isinstance(prizes, list):
        return None
    last_prize = ko and len(prizes) == 1
    terminal = ko and (last_prize or len(opponent_bench) == 0)
    return {
        "semantic": [semantic[0], attack_id],
        "attack_id": attack_id,
        "damage": damage,
        "outcome": "KO" if ko else "NON_KO",
        "ko": ko,
        "terminal_win": terminal,
        "last_prize_win": last_prize,
        "threat_active_removed": ko,
        "target_id": target_id,
        "target_serial": _serial(target),
        "target_hp": target_hp,
        "opponent_bench_count": len(opponent_bench),
    }


def _play_options(
    obs: dict[str, Any], owner: int, hand: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    select = obs.get("select")
    options = select.get("option") if isinstance(select, dict) else None
    if not isinstance(options, list):
        return []
    rows = []
    seen = set()
    for option_index, option in enumerate(options):
        if not isinstance(option, dict) or _int(option.get("type")) != PLAY:
            continue
        hand_index = _int(option.get("index"))
        if hand_index is None or not 0 <= hand_index < len(hand):
            return []
        card = hand[hand_index]
        card_id = _card_id(card)
        serial = _serial(card)
        if (
            card_id not in CANDIDATE_BASICS
            or serial is None
            or _owner(card) != owner
        ):
            continue
        key = (card_id, serial)
        if key in seen:
            return []
        seen.add(key)
        rows.append(
            {
                "option_index": option_index,
                "hand_index": hand_index,
                "card_id": card_id,
                "serial": serial,
                "canonical_option_key": [PLAY, card_id, serial],
            }
        )
    return rows


def _rank_candidates(
    rows: list[dict[str, Any]], hand: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    hand_ids = {_card_id(card) for card in hand}
    exact_abra_route = (
        KADABRA in hand_ids and bool(PSYCHIC_ENERGY_IDS & hand_ids)
    )
    ranked = []
    for row in rows:
        card_id = row["card_id"]
        independent = (
            "CERTIFIED_NEXT_ATTACKER_DISTANCE"
            if card_id == ABRA and exact_abra_route
            else "FLOWER_CURTAIN_BENCH_PROTECTION"
            if card_id == SHAYMIN
            else "TRADING_PLACES_FUTURE_WALL"
            if card_id == DUNSPARCE
            else None
        )
        if independent is None:
            continue
        rank = 0 if card_id == ABRA else 1 if card_id == SHAYMIN else 2
        enriched = dict(row)
        enriched.update(
            {
                "survival_coverage": True,
                "independent_board_value": independent,
                "next_attacker_distance_delta": (
                    -1 if card_id == ABRA else 0
                ),
                "prize_liability": 1,
                "lost_hand_scaling_value": 20,
                "bench_snipe_exposure": "FLOWER_CURTAIN_PROTECTED"
                if card_id == SHAYMIN
                else "PUBLIC",
                "_rank": rank,
            }
        )
        ranked.append(enriched)
    return sorted(
        ranked,
        key=lambda row: (
            row["_rank"],
            row["prize_liability"],
            tuple(row["canonical_option_key"]),
        ),
    )


def evaluate_survival_decision(
    obs: dict[str, Any],
    parent_action: Any,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    """Return a complete fail-closed decision record for the outer wrapper."""
    candidate_closure = policy_closure_sha256()
    base = {
        "schema_version": SCHEMA_VERSION,
        "rule_version": RULE_VERSION,
        "parent_closure_sha256": PARENT_CLOSURE_SHA256,
        "candidate_closure_sha256": candidate_closure,
        "raw_parent_action": parent_action,
        "proposed_action": list(parent_action)
        if isinstance(parent_action, (list, tuple))
        else parent_action,
        "applied_action": list(parent_action)
        if isinstance(parent_action, (list, tuple))
        else parent_action,
        "decision_id": None,
        "damage_rows": [],
        "modifier_ledger": [],
        "active_hp": None,
        "bench_count": None,
        "basic_candidates": [],
        "selected_basic": None,
        "selected_threat": None,
        "current_attack_before": None,
        "current_attack_after": None,
        "guard_class": "SAFE_NO_ACTION",
        "guard_failure": None,
        "transaction_stage": "NO_ACTION",
        "outcome_linkage": None,
        "parent_post_fingerprint": None,
        "candidate_post_fingerprint": None,
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "safety_cap": None,
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "expose_state_fingerprint": None,
        "wall_state_fingerprint": None,
        "hold_entry_turn": None,
        "hold_deadline": None,
        "distance_progress_by_turn": [],
        "promotion_removal_context": _promotion_removal_context(
            obs, parent_action
        ),
    }

    parsed = _players(obs)
    select = obs.get("select") if isinstance(obs, dict) else None
    if parsed is None or not isinstance(select, dict):
        base["guard_class"] = "UNSUPPORTED_NO_ACTION"
        base["guard_failure"] = "PUBLIC_STATE_INVALID"
        return base
    current, mine, _, owner, _ = parsed
    if _int(select.get("context")) != MAIN or _int(select.get("type")) != 0:
        base["guard_failure"] = "NOT_NORMAL_MAIN"
        return base
    active = _zone(mine, "active")
    bench = _zone(mine, "bench")
    hand = _zone(mine, "hand")
    if active is None or bench is None or hand is None:
        base["guard_class"] = "UNSUPPORTED_NO_ACTION"
        base["guard_failure"] = "OWN_ZONE_INVALID"
        return base
    base["bench_count"] = len(bench)
    base["active_hp"] = _int(active[0].get("hp")) if len(active) == 1 else None
    if len(active) != 1 or len(bench) != 0:
        base["guard_failure"] = "NOT_EXACTLY_ONE_ACTIVE_BENCH0"
        return base
    if not _valid_card(active[0], owner):
        base["guard_class"] = "UNSUPPORTED_NO_ACTION"
        base["guard_failure"] = "OWN_ACTIVE_IDENTITY_INVALID"
        return base
    semantic = semantic_action(obs, parent_action)
    if semantic is None or semantic[0] not in ("ATTACK", "END"):
        base["guard_failure"] = "PARENT_NOT_ATTACK_OR_END"
        return base
    before = _own_attack_projection(obs, semantic, hand_delta=0)
    after = _own_attack_projection(obs, semantic, hand_delta=-1)
    base["current_attack_before"] = before
    base["current_attack_after"] = after
    if before is None or after is None:
        base["guard_class"] = "UNSUPPORTED_NO_ACTION"
        base["guard_failure"] = "PARENT_OR_CANDIDATE_PROJECTION_UNKNOWN"
        return base
    if any(
        before[key] != after[key]
        for key in ("outcome", "ko", "terminal_win", "last_prize_win")
    ):
        base["guard_class"] = "HIGH_COUNTERMEASURE_COST_NO_ACTION"
        base["guard_failure"] = "PARENT_TACTICAL_OUTCOME_DEGRADED"
        return base

    damage_rows, damage_failures = opponent_damage_rows(obs, ledger)
    base["damage_rows"] = damage_rows
    power = premium_power_pro_envelope(ledger, phase="future")
    base["modifier_ledger"] = [power]
    base["premium_power_pro_multiplicity"] = power.get(
        "premium_power_pro_multiplicity"
    )
    if damage_failures:
        base["guard_class"] = "UNSUPPORTED_NO_ACTION"
        base["guard_failure"] = damage_failures[0]
        return base
    threats = [row for row in damage_rows if row["cap_ko"]]
    if not threats:
        base["guard_failure"] = "NO_SUPPORTED_BOARDOUT_THREAT"
        return base
    removed_active = [
        row
        for row in threats
        if (
            row["zone"] == "ACTIVE"
            and before["threat_active_removed"]
            and before.get("target_serial") == row["serial"]
        )
    ]
    remaining_threats = [
        row for row in threats if row not in removed_active
    ]
    if removed_active:
        base["promotion_removal_context"] = (
            "PARENT_ACTIVE_THREAT_REMOVAL_WITH_RESIDUAL"
            if remaining_threats
            else "PARENT_ACTIVE_THREAT_REMOVAL"
        )
    if not remaining_threats:
        base["guard_failure"] = "THREAT_REMOVED_BY_PARENT"
        return base
    residual_cap = max(
        row["damage_cap"]
        for row in remaining_threats
        if isinstance(row.get("damage_cap"), int)
    )
    base["evidenced_policy_cap"] = residual_cap
    base["safety_cap"] = residual_cap
    # Highest residual supported cap, then floor, then stable identity.
    threat = sorted(
        remaining_threats,
        key=lambda row: (
            -(row["damage_cap"] or -1),
            -(row["damage_floor"] or -1),
            row["attack_id"],
            row["serial"],
        ),
    )[0]
    base["selected_threat"] = {
        "pokemon_id": threat["pokemon_id"],
        "serial": threat["serial"],
        "zone": threat["zone"],
        "attack_id": threat["attack_id"],
        "damage_floor": threat["damage_floor"],
        "damage_cap": threat["damage_cap"],
    }

    parent_post = {
        "same_threat_serial": threat["serial"],
        "same_threat_attack": threat["attack_id"],
        "threat_remains": True,
        "own_active_serial": _serial(active[0]),
        "own_bench_count": 0,
        "boardout_on_active_ko": True,
        "parent_outcome": before,
    }
    candidate_post = {
        "same_threat_serial": threat["serial"],
        "same_threat_attack": threat["attack_id"],
        "threat_remains": True,
        "own_active_serial": _serial(active[0]),
        "own_bench_count": 1,
        "boardout_on_active_ko": False,
        "parent_outcome": after,
    }
    base["parent_post_fingerprint"] = fingerprint(parent_post)
    base["candidate_post_fingerprint"] = fingerprint(candidate_post)
    base["outcome_linkage"] = {
        "semantic_parent_action": list(semantic),
        "same_threat_in_both_projections": True,
        "parent_boardout": True,
        "candidate_boardout_prevented": True,
        "tactical_outcome_equal": True,
        "removed_active_threat_count": len(removed_active),
        "residual_threat_count": len(remaining_threats),
    }

    options = _play_options(obs, owner, hand)
    ranked = _rank_candidates(options, hand)
    for row in ranked:
        row["current_attack_damage_delta"] = (
            after["damage"] - before["damage"]
        )
        row["current_attack_outcome_before"] = before["outcome"]
        row["current_attack_outcome_after"] = after["outcome"]
        row.pop("_rank", None)
    base["basic_candidates"] = ranked
    if not ranked:
        base["guard_class"] = (
            "HIGH_COUNTERMEASURE_COST_NO_ACTION"
            if threat["damage_floor"] is None
            or threat["damage_floor"] < base["active_hp"]
            else "UNSUPPORTED_NO_ACTION"
        )
        base["guard_failure"] = "NO_INDEPENDENT_LOW_COST_BASIC"
        return base
    selected = dict(ranked[0])
    base["selected_basic"] = selected
    base["proposed_action"] = [selected["option_index"]]
    base["applied_action"] = [selected["option_index"]]
    floor_ko = bool(threat["floor_ko"])
    base["guard_class"] = (
        "FLOOR_BOARDOUT_AVOIDANCE"
        if floor_ko
        else "CAP_LOW_COST_BOARDOUT_AVOIDANCE"
    )
    decision_material = {
        "turn": _int(current.get("turn")),
        "action_count": _int(current.get("turnActionCount")),
        "owner": owner,
        "active_serial": _serial(active[0]),
        "threat_serial": threat["serial"],
        "threat_attack": threat["attack_id"],
        "semantic": semantic,
        "selected": selected["canonical_option_key"],
        "parent_post": base["parent_post_fingerprint"],
        "candidate_post": base["candidate_post_fingerprint"],
    }
    base["decision_id"] = fingerprint(decision_material)
    base["transaction_stage"] = "PROPOSED"
    return base


__all__ = [
    "ATTACK",
    "CANDIDATE_BASICS",
    "END",
    "MAIN",
    "PLAY",
    "POWERFUL_HAND",
    "PREMIUM_POWER_PRO",
    "RULE_VERSION",
    "SCHEMA_VERSION",
    "SUPER_PSY_BOLT",
    "evaluate_survival_decision",
    "fingerprint",
    "opponent_damage_rows",
    "policy_closure_sha256",
    "premium_power_pro_envelope",
    "rebind_semantic_action",
    "semantic_action",
]
