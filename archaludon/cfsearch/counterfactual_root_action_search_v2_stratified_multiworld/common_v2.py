"""V2-only public-root stratification and world-bank helpers."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STRATA = (
    "attack_vs_develop",
    "boss_vs_attack",
    "draw_vs_attack",
    "energy_target",
    "bench_active_formation",
    "recovery_vs_search",
    "resource_discard",
    "defense_ko_avoidance",
)

ACTION_TRANSFORMATIONS = (
    "T1_ATTACK_TO_DEVELOP",
    "T2_DEVELOP_TO_ATTACK",
    "T3_BOSS_TO_FRONT_ATTACK",
    "T4_FRONT_ATTACK_TO_BOSS",
    "T5_DRAW_TO_ATTACK",
    "T6_ATTACK_TO_DRAW",
    "T7_ATTACH_TARGET_CHANGE",
    "T8_BENCH_OR_EVOLVE_CHANGE",
    "T9_RECOVERY_TO_SEARCH",
    "T10_SEARCH_TO_RECOVERY",
    "T11_END_TO_ACTION",
    "T12_ACTION_TO_END",
    "T13_OTHER",
)

CONTEXT_TAGS = (
    "C_IMMEDIATE_KO_RISK",
    "C_BOARD_OUT_RISK",
    "C_BENCH_EMPTY",
    "C_READY_SUCCESSOR",
    "C_NO_READY_SUCCESSOR",
    "C_CURRENT_KO_AVAILABLE",
    "C_BOSS_KO_AVAILABLE",
    "C_PRIZE_OPENING",
    "C_PRIZE_MIDDLE",
    "C_PRIZE_CLOSING",
    "C_MILL_PRESSURE",
    "C_IMMUNITY_OR_ZERO_DAMAGE",
    "C_LOW_DECK",
    "C_ACTIVE_DAMAGED",
    "C_MULTI_ATTACH_TARGET",
    "C_SUPPORTER_UNUSED",
    "C_RETREAT_UNUSED",
)

# These IDs are legal engine cards used only to complete hidden zones.  The
# parent callback sees the recorded public observation, never this bank.
SAFE_ENERGY_ID = 8
SAFE_BASIC_ID = 1072


def canonical_sha256(value: Any) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    return sha256(payload).hexdigest()


# The engine exposes a search-internal continuation token in observations.
# It is not a public zone, option, or action identity and can differ when the
# same seeded prefix is reconstructed in a fresh process.  Formal realized
# worlds therefore hash the normalized public observation with this volatile
# field removed.  No hidden card/effect fields are synthesized or inferred.
_VOLATILE_PUBLIC_KEYS = frozenset({"search_begin_input"})


def normalized_public_observation(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): normalized_public_observation(item)
            for key, item in value.items()
            if str(key) not in _VOLATILE_PUBLIC_KEYS
        }
    if isinstance(value, list):
        return [normalized_public_observation(item) for item in value]
    return value


def normalized_public_hash(observation: Mapping[str, Any]) -> str:
    return canonical_sha256(normalized_public_observation(observation))


def _option_type(option: Mapping[str, Any]) -> int | None:
    value = option.get("type")
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def option_families(observation: Mapping[str, Any]) -> set[str]:
    """Classify only visible prompt options, never replay visualize/hidden state."""
    select = observation.get("select") or {}
    options = select.get("option") or []
    families: set[str] = set()
    for option in options:
        if not isinstance(option, Mapping):
            continue
        option_type = _option_type(option)
        if option_type == 14:
            families.add("attack")
        elif option_type == 12:
            families.add("draw")
        elif option_type == 8:
            families.add("energy")
        elif option_type == 7:
            families.add("develop")
        elif option_type == 3:
            # Target prompts expose area/playerIndex, which is all public.
            if option.get("playerIndex") in (0, 1):
                families.add("target_opponent")
            families.add("target")
        elif option_type == 13:
            families.add("recovery")
        elif option_type == 11:
            families.add("search")
        elif option_type == 10:
            families.add("defense")
        elif option_type == 1:
            families.add("setup")
    context = select.get("context")
    if context in (5, 7, 8):
        families.add("target_opponent")
    return families


def action_family(observation: Mapping[str, Any], action: Sequence[int]) -> str:
    """Return a conservative family from the visible selected option(s)."""
    options = (observation.get("select") or {}).get("option") or []
    selected = [options[index] for index in action if isinstance(index, int) and 0 <= index < len(options)]
    types = {_option_type(option) for option in selected if isinstance(option, Mapping)}
    if 14 in types:
        return "attack"
    if 12 in types:
        return "draw"
    if 8 in types:
        return "attach"
    if 13 in types:
        return "recovery"
    if 11 in types:
        return "search"
    if 10 in types:
        return "defense"
    if 7 in types or 1 in types:
        return "develop"
    if 3 in types:
        return "boss" if any(option.get("playerIndex") in (0, 1) for option in selected if isinstance(option, Mapping)) else "target"
    if not action:
        return "end"
    return "action"


def action_transformation(observation: Mapping[str, Any], parent_action: Sequence[int], alternative_action: Sequence[int]) -> str:
    parent = action_family(observation, parent_action)
    alternative = action_family(observation, alternative_action)
    pair = (parent, alternative)
    mapping = {
        ("attack", "develop"): "T1_ATTACK_TO_DEVELOP",
        ("develop", "attack"): "T2_DEVELOP_TO_ATTACK",
        ("boss", "attack"): "T3_BOSS_TO_FRONT_ATTACK",
        ("attack", "boss"): "T4_FRONT_ATTACK_TO_BOSS",
        ("draw", "attack"): "T5_DRAW_TO_ATTACK",
        ("attack", "draw"): "T6_ATTACK_TO_DRAW",
        ("attach", "attach"): "T7_ATTACH_TARGET_CHANGE",
        ("develop", "attach"): "T8_BENCH_OR_EVOLVE_CHANGE",
        ("recovery", "search"): "T9_RECOVERY_TO_SEARCH",
        ("search", "recovery"): "T10_SEARCH_TO_RECOVERY",
        ("end", "action"): "T11_END_TO_ACTION",
        ("action", "end"): "T12_ACTION_TO_END",
    }
    return mapping.get(pair, "T13_OTHER")


def _card_damage(card: Any) -> int:
    if not isinstance(card, Mapping):
        return 0
    try:
        hp = int(card.get("hp"))
        max_hp = int(card.get("maxHp"))
        if max_hp > hp:
            return max_hp - hp
    except (TypeError, ValueError):
        pass
    for key in ("damageCounter", "damage", "damage_counter"):
        value = card.get(key)
        try:
            if value is not None and int(value) > 0:
                return int(value)
        except (TypeError, ValueError):
            pass
    return 0


def public_context_tags(observation: Mapping[str, Any]) -> list[str]:
    """Conservative tags from callback-visible state only."""
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    if not isinstance(seat, int) or seat not in (0, 1) or len(players) != 2:
        return []
    mine = players[seat] or {}
    opponent = players[1 - seat] or {}
    tags: set[str] = set()
    bench = mine.get("bench") or []
    if not bench:
        tags.add("C_BENCH_EMPTY")
    active = mine.get("active") or []
    if any(_card_damage(card) > 0 for card in active):
        tags.add("C_ACTIVE_DAMAGED")
    prizes = len(mine.get("prize") or [])
    if prizes >= 5:
        tags.add("C_PRIZE_OPENING")
    elif prizes >= 3:
        tags.add("C_PRIZE_MIDDLE")
    else:
        tags.add("C_PRIZE_CLOSING")
    if int(mine.get("deckCount") or 0) <= 5:
        tags.add("C_LOW_DECK")
    if int(opponent.get("deckCount") or 0) <= 5:
        tags.add("C_MILL_PRESSURE")
    options = (observation.get("select") or {}).get("option") or []
    attach_targets = {
        (option.get("inPlayArea"), option.get("inPlayIndex"))
        for option in options
        if isinstance(option, Mapping) and _option_type(option) == 8
    }
    if len(attach_targets) >= 2:
        tags.add("C_MULTI_ATTACH_TARGET")
    if not bool(current.get("supporterPlayed")):
        tags.add("C_SUPPORTER_UNUSED")
    return [tag for tag in CONTEXT_TAGS if tag in tags]


def energy_target_eligibility(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Exact public MAIN-callback eligibility for T7 attach-target changes."""
    select = observation.get("select") or {}
    reasons: list[str] = []
    if select.get("context") != 0 or select.get("type") != 0:
        reasons.append("not_main_callback")
    if bool((observation.get("current") or {}).get("energyAttached")):
        reasons.append("energy_already_attached")
    options = select.get("option") or []
    energy_options = [option for option in options if isinstance(option, Mapping) and _option_type(option) == 8]
    serial_targets: dict[Any, set[tuple[Any, Any]]] = {}
    for option in energy_options:
        serial = option.get("index")
        target = (option.get("inPlayArea"), option.get("inPlayIndex"))
        serial_targets.setdefault(serial, set()).add(target)
    eligible_serials = sorted(str(serial) for serial, targets in serial_targets.items() if serial is not None and len(targets) >= 2)
    if not eligible_serials:
        reasons.append("no_energy_serial_with_two_distinct_targets")
    return {
        "eligible": not reasons,
        "eligible_energy_serials": eligible_serials,
        "energy_option_count": len(energy_options),
        "reasons": reasons,
    }


def _stratum_from_families(families: set[str], semantic_ids: Sequence[str]) -> tuple[str, str]:
    if "attack" in families and ("develop" in families or "setup" in families or "energy" in families):
        return "attack_vs_develop", "visible_option_types"
    if "target_opponent" in families and "attack" in families:
        return "boss_vs_attack", "visible_target_and_attack"
    if "draw" in families and "attack" in families:
        return "draw_vs_attack", "visible_draw_and_attack"
    if "energy" in families:
        return "energy_target", "visible_energy_option"
    if "develop" in families or "setup" in families or "target" in families:
        return "bench_active_formation", "visible_setup_or_target"
    if "recovery" in families or "search" in families:
        return "recovery_vs_search", "visible_recovery_or_search"
    if "discard" in families or "resource" in families:
        return "resource_discard", "visible_resource_option"
    if "defense" in families:
        return "defense_ko_avoidance", "visible_defense_option"
    # A deterministic coverage bucket is allowed only as a labeled fallback;
    # it is not a claim about strategy and cannot be used to infer a rule.
    digest = sha256("|".join(sorted(semantic_ids)).encode("ascii")).digest()
    return STRATA[digest[0] % len(STRATA)], "semantic_hash_fallback"


def classify_root(observation: Mapping[str, Any], semantic_ids: Sequence[str]) -> tuple[str, str, list[str]]:
    families = option_families(observation)
    stratum, basis = _stratum_from_families(families, semantic_ids)
    return stratum, basis, sorted(families)


def public_count_summary(observation: Mapping[str, Any]) -> dict[str, Any]:
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    if not isinstance(seat, int) or seat not in (0, 1) or len(players) != 2:
        raise ValueError("public observation lacks two-player current state")
    mine = players[seat] or {}
    opponent = players[1 - seat] or {}
    active = opponent.get("active") or []
    visible_active_ids = [int(card["id"]) for card in active if isinstance(card, Mapping) and card.get("id") is not None]
    return {
        "your_deck_count": int(mine.get("deckCount") or 0),
        "your_hand_count": int(mine.get("handCount") or 0),
        "your_prize_count": len(mine.get("prize") or []),
        "opponent_deck_count": int(opponent.get("deckCount") or 0),
        "opponent_hand_count": int(opponent.get("handCount") or 0),
        "opponent_prize_count": len(opponent.get("prize") or []),
        "opponent_active_count": len(active),
        "opponent_visible_active_ids": visible_active_ids,
    }


def _fill(count: int, values: Sequence[int]) -> list[int]:
    if count < 0:
        raise ValueError(f"negative public count: {count}")
    if count == 0:
        return []
    values = tuple(int(value) for value in values if int(value) > 0) or (SAFE_ENERGY_ID,)
    return [values[index % len(values)] for index in range(count)]


def build_world_bank(observation: Mapping[str, Any], parent_deck: Sequence[int], world_count: int = 4) -> list[dict[str, Any]]:
    """Build deterministic legal-card worlds from public counts only."""
    if len(parent_deck) != 60:
        raise ValueError("parent deck must have 60 cards")
    counts = public_count_summary(observation)
    worlds: list[dict[str, Any]] = []
    parent_values = [int(card) for card in parent_deck if int(card) > 0]
    for index in range(world_count):
        if index % 2 == 0:
            hidden_values = (SAFE_ENERGY_ID, SAFE_BASIC_ID)
        else:
            hidden_values = tuple(parent_values[:2]) or (SAFE_ENERGY_ID, SAFE_BASIC_ID)
        opponent_active = list(counts["opponent_visible_active_ids"])
        if counts["opponent_active_count"] and not opponent_active:
            opponent_active = [SAFE_BASIC_ID]
        world = {
            "world_id": f"world_{index:02d}",
            "method": "CONSISTENT_WORLD_BANK",
            "public_counts": counts,
            "your_deck": list(parent_deck),
            "your_prize": _fill(counts["your_prize_count"], hidden_values),
            "opponent_deck": _fill(counts["opponent_deck_count"], hidden_values),
            "opponent_prize": _fill(counts["opponent_prize_count"], hidden_values),
            "opponent_hand": _fill(counts["opponent_hand_count"], hidden_values),
            "opponent_active": opponent_active,
        }
        validate_world(observation, world)
        worlds.append(world)
    return worlds


def validate_world(observation: Mapping[str, Any], world: Mapping[str, Any]) -> None:
    counts = public_count_summary(observation)
    if len(world.get("your_deck") or []) != 60:
        raise ValueError("world your_deck is not 60 cards")
    checks = (
        ("your_prize", counts["your_prize_count"]),
        ("opponent_deck", counts["opponent_deck_count"]),
        ("opponent_prize", counts["opponent_prize_count"]),
        ("opponent_hand", counts["opponent_hand_count"]),
    )
    for key, expected in checks:
        values = world.get(key)
        if not isinstance(values, list) or len(values) != expected:
            raise ValueError(f"world {key} length contradicts public count: {len(values or [])} != {expected}")
        if any(not isinstance(card, int) or isinstance(card, bool) or card <= 0 for card in values):
            raise ValueError(f"world {key} contains an invalid card id")
    active = world.get("opponent_active")
    if not isinstance(active, list) or len(active) != counts["opponent_active_count"]:
        raise ValueError("world opponent_active contradicts public active count")
    if any(not isinstance(card, int) or card <= 0 for card in active):
        raise ValueError("world opponent_active contains an invalid card id")
    visible = counts["opponent_visible_active_ids"]
    if visible and active != visible:
        raise ValueError("world changed a visible opponent active identity")


def validate_public_zone_contract(observation: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    """Report whether a world has enough visible-zone evidence for formal use.

    The engine can still run a count-consistent diagnostic world when the
    callback omits a zone.  Such a world is explicitly *not* formal
    multiworld evidence; it is never silently upgraded.
    """
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    missing: list[str] = []
    violations: list[str] = []
    if not isinstance(seat, int) or seat not in (0, 1) or len(players) != 2:
        return {"formal_eligible": False, "missing_public_fields": ["current.players"], "violations": []}
    public_serials: dict[str, str] = {}
    for index, player in enumerate(players):
        if not isinstance(player, Mapping):
            missing.append(f"players[{index}]")
            continue
        for key in ("active", "bench", "discard", "hand", "deckCount", "prize"):
            if key not in player:
                missing.append(f"players[{index}].{key}")
        for zone in ("active", "bench", "discard", "hand", "prize"):
            values = player.get(zone)
            if values is None:
                continue
            if not isinstance(values, list):
                violations.append(f"players[{index}].{zone}_not_list")
                continue
            for card_index, card in enumerate(values):
                if not isinstance(card, Mapping):
                    continue
                serial = card.get("serial")
                if serial is None:
                    continue
                key = str(serial)
                previous = public_serials.get(key)
                if previous is not None:
                    violations.append(f"duplicate_public_serial:{key}:{previous}:players[{index}].{zone}[{card_index}]")
                else:
                    public_serials[key] = f"players[{index}].{zone}[{card_index}]"
    if "stadium" not in current:
        missing.append("current.stadium")
    # Formal multiworld use also requires explicit world mirrors for all
    # public zones.  The current diagnostic bank intentionally contains only
    # hidden-count fillers and the visible opponent Active, so it must never
    # be silently promoted to a formal world.
    required_world_keys = (
        "your_active", "your_bench", "your_discard", "your_hand",
        "your_stadium", "your_tools", "your_attached_energy", "your_pre_evolution",
        "opponent_bench", "opponent_discard", "opponent_stadium", "opponent_tools",
        "opponent_attached_energy", "opponent_pre_evolution", "public_log",
    )
    for key in required_world_keys:
        if key not in world:
            missing.append(f"world.{key}")
    if len(world.get("your_deck") or []) != 60:
        violations.append("world.your_deck_not_60")
    if world.get("deck_multiset") is None:
        missing.append("world.deck_multiset")
    if world.get("public_log") is not None and not isinstance(world.get("public_log"), list):
        violations.append("world.public_log_not_list")
    return {
        "formal_eligible": not missing and not violations,
        "missing_public_fields": sorted(set(missing)),
        "violations": sorted(set(violations)),
        "diagnostic_only_reason": None if not missing and not violations else "public_zone_or_world_contract_incomplete",
    }
