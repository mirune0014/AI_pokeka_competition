"""Side-effect-free C2 next-attacker-distance analysis.

This module is deliberately downstream of the complete inherited policy.  It
never proposes, ranks, validates, caches, or returns an engine action.  Its
only product is a callback-local, JSON-safe diagnostic trace.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import _cumulative_parent as parent
import planner_model as model
import planner_runtime_model as runtime_model


SCHEMA_VERSION = 4
RULE_VERSION = "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B"
PARENT_CLOSURE_SHA256 = (
    "DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47"
)

ABRA = 741
KADABRA = 742
ALAKAZAM = 743
DUDUNSPARCE = 66
PSYCHIC_ENERGY_IDS = frozenset({5, 19})
SUPPORTED_LINE_IDS = frozenset({ABRA, KADABRA, ALAKAZAM})
EXPECTED_STACK = {
    ABRA: (ABRA,),
    KADABRA: (ABRA, KADABRA),
    ALAKAZAM: (ABRA, KADABRA, ALAKAZAM),
}
DECK_COUNTS = {ABRA: 4, KADABRA: 4, ALAKAZAM: 4}
RECOVERY_CARD_IDS = frozenset({1097, 1129, 1184})

ATTACK_SUPER_PSY_BOLT = 1071
ATTACK_POWERFUL_HAND = 1072

CERTIFIED = "CERTIFIED"
POSSIBLE = "POSSIBLE"
IMPOSSIBLE = "IMPOSSIBLE"
UNKNOWN = "UNKNOWN"
ROUTE_CLASS_CODE = {
    CERTIFIED: 0,
    POSSIBLE: 1,
    IMPOSSIBLE: 2,
    UNKNOWN: 3,
}

# This is the amendment's reduction order.  It intentionally differs from
# sorting the frozen numeric class codes: unresolved UNKNOWN must dominate an
# unproven IMPOSSIBLE.
REDUCTION_PRECEDENCE = (CERTIFIED, POSSIBLE, UNKNOWN, IMPOSSIBLE)

NONE_CURRENT_TURN = "NONE_CURRENT_TURN"
ONE_OPPONENT_TURN = "ONE_OPPONENT_TURN"
TWO_OPPONENT_TURNS = "TWO_OPPONENT_TURNS"


def _policy_closure_sha256() -> str | None:
    """Compute the checked local closure without embedding a circular hash."""
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
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest().upper()
            rows.append(
                f"{relative}\0{digest}\0{len(payload)}\n"
            )
        material = "".join(sorted(rows)).encode("utf-8")
        return hashlib.sha256(material).hexdigest().upper()
    except Exception:
        return None


CANDIDATE_CLOSURE_SHA256 = _policy_closure_sha256()


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_key(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=repr,
    )


def _safe_copy(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:
        return repr(value)


def _action_type(value: Any) -> str:
    kind = type(value)
    return f"{kind.__module__}.{kind.__qualname__}"


def _distance(
    route_class: str,
    turn_delay: int | None,
    main_actions: int | None,
    forced_prompts: int | None,
    template: str,
    *,
    witness_steps: Iterable[dict[str, Any] | str] = (),
    missing_requirements: Iterable[str] = (),
    unsupported_reasons: Iterable[str] = (),
    interruption_exposure: str | None = None,
    certified_draw_count: int = 0,
    certified_draw_damage_delta: int = 0,
    deterministic_hand_expenditures: int = 0,
    current_hand_count: int | None = None,
) -> dict[str, Any]:
    if interruption_exposure is None:
        interruption_exposure = {
            0: NONE_CURRENT_TURN,
            1: ONE_OPPONENT_TURN,
            2: TWO_OPPONENT_TURNS,
        }.get(turn_delay, UNKNOWN)
    projected_hand_count = None
    projected_powerful_hand_damage = None
    if (
        isinstance(current_hand_count, int)
        and isinstance(certified_draw_count, int)
        and isinstance(deterministic_hand_expenditures, int)
    ):
        projected_hand_count = (
            current_hand_count
            + certified_draw_count
            - deterministic_hand_expenditures
        )
        if projected_hand_count >= 0:
            projected_powerful_hand_damage = 20 * projected_hand_count
        else:
            projected_hand_count = None
    witness = {
        "template": template,
        "steps": list(witness_steps),
        "missing_requirements": sorted(set(missing_requirements)),
        "unsupported_reasons": sorted(set(unsupported_reasons)),
    }
    canonical_witness_key = _json_key(witness)
    return {
        "route_class": route_class,
        "route_class_code": ROUTE_CLASS_CODE[route_class],
        "turn_delay": turn_delay,
        "main_actions": main_actions,
        "forced_prompts": forced_prompts,
        "witness": witness,
        "canonical_witness_key": canonical_witness_key,
        "interruption_exposure": interruption_exposure,
        "certified_draw_count": certified_draw_count,
        "certified_draw_damage_delta": certified_draw_damage_delta,
        "deterministic_hand_expenditures": deterministic_hand_expenditures,
        "projected_hand_count": projected_hand_count,
        "projected_powerful_hand_damage": projected_powerful_hand_damage,
        "route_tuple": [
            route_class,
            turn_delay,
            main_actions,
            forced_prompts,
            witness,
        ],
    }


def _route_sort_key(route: dict[str, Any]) -> tuple[Any, ...]:
    large = 10**9
    return (
        route.get("turn_delay")
        if isinstance(route.get("turn_delay"), int)
        else large,
        route.get("main_actions")
        if isinstance(route.get("main_actions"), int)
        else large,
        route.get("forced_prompts")
        if isinstance(route.get("forced_prompts"), int)
        else large,
        route.get("canonical_witness_key", ""),
    )


def reduce_routes(
    routes: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Apply the binding UNKNOWN-before-IMPOSSIBLE reduction."""
    rows = list(routes)
    for route_class in REDUCTION_PRECEDENCE:
        matching = [
            route
            for route in rows
            if route.get("route_class") == route_class
        ]
        if matching:
            return min(matching, key=_route_sort_key)
    return _distance(
        UNKNOWN,
        None,
        None,
        None,
        "NO_COMPLETE_SUPPORTED_ROUTE_ENUMERATION",
        unsupported_reasons=("NO_ROUTE_ROWS",),
    )


def _normalized_transaction_flags(
    transaction_state: Any,
) -> dict[str, bool]:
    """Return only transaction booleans that can change C2 routing."""
    state = (
        transaction_state
        if isinstance(transaction_state, dict)
        else {}
    )
    return {
        "integrated_transaction_active": bool(
            state.get("integrated_transaction_active", False)
        ),
        "v1_transaction_active": bool(
            state.get("v1_transaction_active", False)
        ),
    }


def _observation_fingerprint(
    raw: dict[str, Any],
    transaction_state: Any = None,
) -> str | None:
    """Fingerprint callback-visible state and C2-relevant policy flags."""
    try:
        current = raw["current"]
        owner = current["yourIndex"]
        mine = current["players"][owner]
        select = raw["select"]
        options = sorted(
            (_safe_copy(row) for row in select["option"]),
            key=_json_key,
        )
        payload = {
            "owner": owner,
            "turn": current["turn"],
            "turnActionCount": current["turnActionCount"],
            "result": current["result"],
            "energyAttached": current["energyAttached"],
            "retreated": current["retreated"],
            "supporterPlayed": current["supporterPlayed"],
            "stadiumPlayed": current["stadiumPlayed"],
            "stadium": _safe_copy(current["stadium"]),
            "active": _safe_copy(mine["active"]),
            "bench": _safe_copy(mine["bench"]),
            "hand": _safe_copy(mine["hand"]),
            "discard": _safe_copy(mine["discard"]),
            "prize_count": len(mine["prize"]),
            "deckCount": mine["deckCount"],
            "handCount": mine["handCount"],
            "benchMax": mine["benchMax"],
            "status": {
                key: mine[key]
                for key in (
                    "asleep",
                    "paralyzed",
                    "confused",
                    "poisoned",
                    "burned",
                )
            },
            "select": {
                key: _safe_copy(select.get(key))
                for key in (
                    "type",
                    "context",
                    "minCount",
                    "maxCount",
                    "remainEnergyCost",
                    "remainDamageCounter",
                    "contextCard",
                    "effect",
                )
            },
            "options": options,
            "transaction_flags": _normalized_transaction_flags(
                transaction_state
            ),
        }
        canonical = _json_key(payload)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
    except Exception:
        return None


def _base_trace(
    raw: Any,
    action: Any,
    *,
    parent_trace: Any = None,
    transaction_state: Any = None,
) -> dict[str, Any]:
    raw_action = _safe_copy(action)
    applied_action = _safe_copy(action)
    value_equal = raw_action == applied_action
    type_equal = type(raw_action) is type(applied_action)
    return {
        "schema_version": SCHEMA_VERSION,
        "rule_version": RULE_VERSION,
        "parent_closure_sha256": PARENT_CLOSURE_SHA256,
        "candidate_closure_sha256": CANDIDATE_CLOSURE_SHA256,
        "raw_parent_action": raw_action,
        "applied_action": applied_action,
        "action_python_type": _action_type(action),
        "action_identity": {
            "value_equal": value_equal,
            "type_equal": type_equal,
            "order_equal": value_equal,
            "returned_parent_object_unchanged": True,
        },
        "observation_fingerprint": (
            _observation_fingerprint(raw, transaction_state)
            if isinstance(raw, dict)
            else None
        ),
        "route_rows": [],
        "best_primary_route": None,
        "best_fallback_route": None,
        "line_importance_rows": [],
        "unsupported_reasons": [],
        "metric_exception": None,
        "parent_trace": _safe_copy(parent_trace),
        "transaction_state": _safe_copy(transaction_state),
        # Binding-amendment trace fields.  C3-C5 projections are explicitly
        # deferred; C2 must not invent them from the current state.
        "parent_post_fingerprint": None,
        "candidate_post_fingerprint": None,
        "expose_state_fingerprint": None,
        "wall_state_fingerprint": None,
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "safety_cap": None,
        "hold_entry_turn": None,
        "hold_deadline": None,
        "distance_progress_by_turn": [],
    }


def metric_exception_trace(
    raw: Any,
    action: Any,
    error: BaseException,
    *,
    parent_trace: Any = None,
    transaction_state: Any = None,
) -> dict[str, Any]:
    trace = _base_trace(
        raw,
        action,
        parent_trace=parent_trace,
        transaction_state=transaction_state,
    )
    trace["metric_exception"] = type(error).__name__
    trace["unsupported_reasons"] = ["METRIC_EXCEPTION"]
    unknown = _distance(
        UNKNOWN,
        None,
        None,
        None,
        "METRIC_EXCEPTION_FAIL_CLOSED",
        unsupported_reasons=(type(error).__name__,),
    )
    trace["best_primary_route"] = unknown
    trace["best_fallback_route"] = copy.deepcopy(unknown)
    return trace


def _card_owner_and_serial_exact(card: Any, owner: int) -> bool:
    observed_owner = getattr(card, "playerIndex", None)
    # The engine's parsed Pokemon value omits playerIndex even though the raw
    # in-play row carries it.  Its owner is certified by the containing
    # active/bench zone and raw_parsed_agree; nested Card values retain owner.
    owner_exact = (
        observed_owner == owner
        or (
            observed_owner is None
            and hasattr(card, "hp")
            and hasattr(card, "maxHp")
        )
    )
    return (
        card is not None
        and type(getattr(card, "id", None)) is int
        and type(getattr(card, "serial", None)) is int
        and card.serial > 0
        and owner_exact
    )


def _line_stack(
    pokemon: Any,
    owner: int,
) -> tuple[tuple[int, ...], tuple[int, ...], list[str]]:
    reasons: list[str] = []
    top_id = getattr(pokemon, "id", None)
    expected = EXPECTED_STACK.get(top_id)
    components = list(getattr(pokemon, "preEvolution", None) or [])
    stack = components + [pokemon]
    card_ids = tuple(getattr(card, "id", None) for card in stack)
    serials = tuple(getattr(card, "serial", None) for card in stack)
    if expected is None or card_ids != expected:
        reasons.append("MALFORMED_ALAKAZAM_STACK")
    if any(
        not _card_owner_and_serial_exact(card, owner)
        for card in stack
    ):
        reasons.append("STACK_OWNER_OR_SERIAL_UNKNOWN")
    if len(serials) != len(set(serials)):
        reasons.append("DUPLICATE_STACK_SERIAL")
    return card_ids, serials, reasons


def _pokemon_complete(
    pokemon: Any,
    owner: int,
) -> list[str]:
    reasons: list[str] = []
    if not _card_owner_and_serial_exact(pokemon, owner):
        reasons.append("POKEMON_OWNER_OR_SERIAL_UNKNOWN")
        return reasons
    data = parent.card_table.get(pokemon.id)
    if (
        data is None
        or data.cardType != parent.CardType.POKEMON
        or getattr(pokemon, "maxHp", None) != data.hp
        or type(getattr(pokemon, "hp", None)) is not int
        or not 0 < pokemon.hp <= pokemon.maxHp
    ):
        reasons.append("POKEMON_METADATA_INCOMPLETE")
    if type(getattr(pokemon, "appearThisTurn", None)) is not bool:
        reasons.append("APPEAR_THIS_TURN_UNKNOWN")
    energies = list(getattr(pokemon, "energies", None) or [])
    energy_cards = list(getattr(pokemon, "energyCards", None) or [])
    if len(energies) != len(energy_cards):
        reasons.append("ENERGY_CARD_UNIT_MISMATCH")
    for card in energy_cards:
        if not _card_owner_and_serial_exact(card, owner):
            reasons.append("ENERGY_OWNER_OR_SERIAL_UNKNOWN")
        data = parent.card_table.get(getattr(card, "id", None))
        if data is None or data.cardType not in (
            parent.CardType.BASIC_ENERGY,
            parent.CardType.SPECIAL_ENERGY,
        ):
            reasons.append("ENERGY_METADATA_UNKNOWN")
    for card in list(getattr(pokemon, "tools", None) or []):
        if not _card_owner_and_serial_exact(card, owner):
            reasons.append("TOOL_OWNER_OR_SERIAL_UNKNOWN")
        reasons.append("UNSUPPORTED_POKEMON_TOOL")
    return reasons


def _fixed_metadata_reasons() -> list[str]:
    reasons: list[str] = []
    try:
        if not parent._two_prize_powerful_hand_metadata_is_exact():
            reasons.append("POWERFUL_HAND_METADATA_UNKNOWN")
    except Exception:
        reasons.append("POWERFUL_HAND_METADATA_UNKNOWN")
    try:
        abra = parent.card_table.get(ABRA)
        kadabra = parent.card_table.get(KADABRA)
        super_psy = parent.attack_table.get(ATTACK_SUPER_PSY_BOLT)
        if not (
            abra is not None
            and abra.name == "Abra"
            and abra.evolvesFrom is None
            and tuple(abra.attacks or ()) == (1070,)
            and kadabra is not None
            and kadabra.name == "Kadabra"
            and kadabra.evolvesFrom == abra.name
            and tuple(kadabra.attacks or ()) == (ATTACK_SUPER_PSY_BOLT,)
            and super_psy is not None
            and super_psy.name == "Super Psy Bolt"
            and super_psy.damage == 30
            and super_psy.text == ""
            and tuple(int(unit) for unit in super_psy.energies)
            == (int(parent.EnergyType.PSYCHIC),)
        ):
            reasons.append("KADABRA_ATTACK_METADATA_UNKNOWN")
    except Exception:
        reasons.append("KADABRA_ATTACK_METADATA_UNKNOWN")
    try:
        dudunsparce = parent.card_table.get(DUDUNSPARCE)
        if not (
            dudunsparce is not None
            and len(dudunsparce.skills or ()) == 1
            and dudunsparce.skills[0].name.strip() == "Run Away Draw"
            and "draw 3 cards"
            in parent._normalized_skill_text(dudunsparce.skills[0].text)
            and "shuffle this pok"
            in parent._normalized_skill_text(dudunsparce.skills[0].text)
            and "coin"
            not in parent._normalized_skill_text(dudunsparce.skills[0].text)
        ):
            reasons.append("RUN_AWAY_METADATA_UNKNOWN")
    except Exception:
        reasons.append("RUN_AWAY_METADATA_UNKNOWN")
    return reasons


def _all_component_serials(mine: Any) -> list[int | None]:
    serials: list[int | None] = []

    def add_card(card: Any) -> None:
        serials.append(getattr(card, "serial", None))

    for card in list(mine.hand) + list(mine.discard):
        add_card(card)
    for pokemon in list(mine.active) + list(mine.bench):
        add_card(pokemon)
        for card in (
            list(getattr(pokemon, "preEvolution", None) or [])
            + list(getattr(pokemon, "energyCards", None) or [])
            + list(getattr(pokemon, "tools", None) or [])
        ):
            add_card(card)
    return serials


def _zone_integrity_reasons(raw: dict[str, Any], obs: Any) -> list[str]:
    reasons: list[str] = []
    current = raw.get("current")
    if not isinstance(current, dict):
        return ["CURRENT_MISSING"]
    owner = current.get("yourIndex")
    if owner not in (0, 1):
        return ["OWNER_UNKNOWN"]
    players = current.get("players")
    if not isinstance(players, list) or len(players) != 2:
        return ["PLAYERS_MALFORMED"]
    mine_raw = players[owner]
    if not isinstance(mine_raw, dict):
        return ["OWNER_PLAYER_MALFORMED"]
    for key in (
        "active",
        "bench",
        "hand",
        "discard",
        "prize",
    ):
        if not isinstance(mine_raw.get(key), list):
            reasons.append(f"{key.upper()}_ZONE_MALFORMED")
    if reasons:
        return reasons
    if mine_raw.get("handCount") != len(mine_raw["hand"]):
        reasons.append("HAND_COUNT_MISMATCH")
    deck_count = _int(mine_raw.get("deckCount"))
    bench_max = _int(mine_raw.get("benchMax"))
    if deck_count is None or not 0 <= deck_count <= 60:
        reasons.append("DECK_COUNT_INVALID")
    if (
        bench_max is None
        or not 0 <= bench_max <= 5
        or len(mine_raw["bench"]) > bench_max
    ):
        reasons.append("BENCH_LIMIT_INVALID")
    if not 0 <= len(mine_raw["prize"]) <= 6:
        reasons.append("PRIZE_COUNT_INVALID")
    for key in (
        "energyAttached",
        "retreated",
        "supporterPlayed",
        "stadiumPlayed",
    ):
        if type(current.get(key)) is not bool:
            reasons.append(f"{key.upper()}_FLAG_UNKNOWN")
    for key in (
        "asleep",
        "paralyzed",
        "confused",
        "poisoned",
        "burned",
    ):
        if type(mine_raw.get(key)) is not bool:
            reasons.append(f"{key.upper()}_STATUS_UNKNOWN")
        elif mine_raw.get(key):
            reasons.append("UNSUPPORTED_SPECIAL_CONDITION")
    context = _int((raw.get("select") or {}).get("context"))
    result = _int(current.get("result"))
    if (
        context == int(parent.SelectContext.MAIN)
        and result == -1
        and len(mine_raw["active"]) != 1
    ):
        reasons.append("NORMAL_MAIN_REQUIRES_ONE_ACTIVE")
    for stadium in current.get("stadium") or []:
        card_id = stadium.get("id") if isinstance(stadium, dict) else None
        data = parent.card_table.get(card_id)
        normalized = (
            parent._normalized_skill_text(data.skills[0].text)
            if (
                data is not None
                and len(data.skills or ()) == 1
            )
            else ""
        )
        # These exact effects do not change evolution, Energy payment, legal
        # switching, or active attack availability for the non-Tera Abra line.
        supported_irrelevant = (
            card_id == 1266
            and normalized
            == (
                "attacks used by each tera pokemon in play (both yours "
                "and your opponent's) cost {c} more."
            )
        ) or (
            card_id == 1264
            and normalized.startswith(
                "prevent all damage counters from being placed on benched "
                "pokemon"
            )
        )
        if not supported_irrelevant:
            reasons.append("UNSUPPORTED_STADIUM")
    if current.get("looking"):
        reasons.append("UNSUPPORTED_LOOKING_TRANSACTION")

    for zone_name in ("active", "bench"):
        for pokemon in mine_raw[zone_name]:
            if (
                not isinstance(pokemon, dict)
                or pokemon.get("playerIndex") != owner
            ):
                reasons.append("IN_PLAY_OWNER_UNKNOWN")
                continue
            for component_name in (
                "preEvolution",
                "energyCards",
                "tools",
            ):
                for card in pokemon.get(component_name) or []:
                    if (
                        not isinstance(card, dict)
                        or card.get("playerIndex") != owner
                    ):
                        reasons.append(
                            "IN_PLAY_COMPONENT_OWNER_UNKNOWN"
                        )

    mine = obs.current.players[owner]
    serials = _all_component_serials(mine)
    if any(type(serial) is not int or serial <= 0 for serial in serials):
        reasons.append("VISIBLE_SERIAL_UNKNOWN")
    if len(serials) != len(set(serials)):
        reasons.append("DUPLICATE_VISIBLE_SERIAL")
    for card in list(mine.hand) + list(mine.discard):
        if not _card_owner_and_serial_exact(card, owner):
            reasons.append("VISIBLE_CARD_OWNER_OR_SERIAL_UNKNOWN")
        if parent.card_table.get(getattr(card, "id", None)) is None:
            reasons.append("VISIBLE_CARD_METADATA_UNKNOWN")
    for pokemon in list(mine.active) + list(mine.bench):
        reasons.extend(_pokemon_complete(pokemon, owner))
    return reasons


def _option_key_rows(obs: Any) -> tuple[list[Any], list[str]]:
    reasons: list[str] = []
    keys: list[Any] = []
    if obs.select is None:
        return [], ["SELECT_MISSING"]
    for option in obs.select.option:
        key = runtime_model.stable_option_key(parent, obs, option)
        keys.append(key)
        if key is None:
            reasons.append("OPTION_SEMANTIC_UNKNOWN")
    usable = [key for key in keys if key is not None]
    if len(usable) != len(set(usable)):
        reasons.append("DUPLICATE_OPTION_SEMANTIC")
    return keys, reasons


def _option_result(
    obs: Any,
    predicate: Any,
) -> tuple[str, dict[str, Any] | None]:
    matches = []
    for index, option in enumerate(obs.select.option):
        try:
            if predicate(option):
                matches.append(
                    (
                        index,
                        runtime_model.stable_option_key(
                            parent, obs, option
                        ),
                    )
                )
        except Exception:
            return "UNKNOWN", None
    if len(matches) == 1 and matches[0][1] is not None:
        # Positional option indexes are intentionally excluded from the
        # witness. Equivalent option reorderings must retain one canonical
        # semantic trace and observation fingerprint.
        return "EXACT", {"option_key": matches[0][1]}
    if len(matches) > 1:
        return "AMBIGUOUS", None
    return "ABSENT", None


def _option_card(obs: Any, option: Any) -> Any:
    try:
        return model._option_card(parent, obs, option)
    except Exception:
        return None


def _target_pokemon(obs: Any, option: Any) -> Any:
    try:
        owner = obs.current.yourIndex
        return model._pokemon_for_area(
            parent,
            obs,
            option.inPlayArea,
            option.inPlayIndex,
            owner,
        )
    except Exception:
        return None


def _evolve_option(
    obs: Any,
    source_serial: int,
    target_serial: int,
) -> tuple[str, dict[str, Any] | None]:
    return _option_result(
        obs,
        lambda option: (
            option.type == parent.OptionType.EVOLVE
            and getattr(_option_card(obs, option), "serial", None)
            == source_serial
            and getattr(_target_pokemon(obs, option), "serial", None)
            == target_serial
        ),
    )


def _attach_option(
    obs: Any,
    source_serial: int,
    target_serial: int,
) -> tuple[str, dict[str, Any] | None]:
    return _option_result(
        obs,
        lambda option: (
            option.type == parent.OptionType.ATTACH
            and getattr(_option_card(obs, option), "serial", None)
            == source_serial
            and getattr(_target_pokemon(obs, option), "serial", None)
            == target_serial
        ),
    )


def _ability_option(
    obs: Any,
    source_serial: int,
) -> tuple[str, dict[str, Any] | None]:
    owner = obs.current.yourIndex

    def predicate(option: Any) -> bool:
        if option.type != parent.OptionType.ABILITY:
            return False
        pokemon = model._pokemon_for_area(
            parent,
            obs,
            option.area,
            option.index,
            owner,
        )
        return getattr(pokemon, "serial", None) == source_serial

    return _option_result(obs, predicate)


def _promotion_option(
    obs: Any,
    source_serial: int,
) -> tuple[str, dict[str, Any] | None]:
    if obs.select.context != parent.SelectContext.TO_ACTIVE:
        return "ABSENT", None
    return _option_result(
        obs,
        lambda option: (
            option.type == parent.OptionType.CARD
            and option.area == parent.AreaType.BENCH
            and getattr(_option_card(obs, option), "serial", None)
            == source_serial
        ),
    )


def _attack_option(
    obs: Any,
    attack_id: int,
) -> tuple[str, dict[str, Any] | None]:
    return _option_result(
        obs,
        lambda option: (
            option.type == parent.OptionType.ATTACK
            and option.attackId == attack_id
        ),
    )


def _retreat_option(
    obs: Any,
) -> tuple[str, dict[str, Any] | None]:
    return _option_result(
        obs,
        lambda option: option.type == parent.OptionType.RETREAT,
    )


def _hand_cards(mine: Any, card_id: int) -> list[Any]:
    return sorted(
        [card for card in mine.hand if card.id == card_id],
        key=lambda card: card.serial,
    )


def _energy_units(pokemon: Any) -> tuple[int, ...] | None:
    try:
        return parent._bridge_retaliation_energy_units(pokemon)
    except Exception:
        return None


def _can_pay(pokemon: Any, attack_id: int) -> bool | None:
    units = _energy_units(pokemon)
    attack = parent.attack_table.get(attack_id)
    if units is None or attack is None:
        return None
    try:
        return parent._bridge_retaliation_can_pay(
            units, attack.energies
        )
    except Exception:
        return None


def _status_clear(mine: Any) -> bool | None:
    values = [
        getattr(mine, key, None)
        for key in (
            "asleep",
            "paralyzed",
            "confused",
            "poisoned",
            "burned",
        )
    ]
    if any(type(value) is not bool for value in values):
        return None
    # The initial C2 implementation does not project special-condition
    # recovery, coin flips, or between-turn damage.
    return not any(values)


def _missing_component_class(
    mine: Any,
    card_ids: Iterable[int],
) -> tuple[str, list[str]]:
    missing = sorted(set(card_ids))
    if not missing:
        return CERTIFIED, []
    requirements = [
        {
            ABRA: "NEEDS_ABRA",
            KADABRA: "NEEDS_KADABRA",
            ALAKAZAM: "NEEDS_ALAKAZAM",
        }.get(card_id, f"NEEDS_CARD_{card_id}")
        for card_id in missing
    ]
    requirements.append("NEEDS_SEARCH_OR_DRAW")
    if any(card.id in RECOVERY_CARD_IDS for card in mine.hand):
        requirements.append("NEEDS_RECOVERY")
        return POSSIBLE, requirements
    # With no drawable cards, absent evolution components cannot enter the
    # hand in the supported two-turn templates.  Hidden Prizes remain
    # inaccessible without an additional, unsupported prize-taking route.
    if mine.deckCount == 0:
        return IMPOSSIBLE, requirements
    return POSSIBLE, requirements


def _active_transfer_route(
    obs: Any,
    line: dict[str, Any],
    *,
    ready_delay: int,
    ready_actions: int,
    ready_prompts: int,
    hand_expenditures: int,
    target_attack_id: int,
    target_name: str,
) -> dict[str, Any]:
    mine = obs.current.players[obs.current.yourIndex]
    current_hand = mine.handCount
    location = line["location"]
    top = line["pokemon"]
    future_top_serial = line.get("future_top_serial", top.serial)
    base_steps = list(line.get("pending_steps", []))
    if location == "ACTIVE":
        if (
            ready_delay == 0
            and ready_actions == 0
            and obs.select.context == parent.SelectContext.MAIN
        ):
            attack_status, attack_witness = _attack_option(
                obs, target_attack_id
            )
            if attack_status != "EXACT":
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    f"ACTIVE_{target_name}_ATTACK_OPTION_UNRESOLVED",
                    witness_steps=base_steps,
                    unsupported_reasons=(
                        "ATTACK_OPTION_AMBIGUOUS_OR_ABSENT",
                    ),
                    current_hand_count=current_hand,
                )
            base_steps.append(
                {"kind": "ATTACK_READY", **attack_witness}
            )
        return _distance(
            CERTIFIED,
            ready_delay,
            ready_actions,
            ready_prompts,
            f"ACTIVE_{target_name}_READY",
            witness_steps=base_steps,
            deterministic_hand_expenditures=hand_expenditures,
            current_hand_count=current_hand,
        )

    promotion_status, promotion_witness = _promotion_option(
        obs, top.serial
    )
    if ready_delay == 0 and promotion_status == "EXACT":
        return _distance(
            CERTIFIED,
            0,
            ready_actions,
            ready_prompts + 1,
            f"BENCH_{target_name}_READY_AFTER_EXACT_PROMOTION",
            witness_steps=base_steps
            + [{"kind": "EXACT_PROMOTION", **promotion_witness}],
            deterministic_hand_expenditures=hand_expenditures,
            current_hand_count=current_hand,
        )
    if ready_delay == 0 and promotion_status == "AMBIGUOUS":
        return _distance(
            UNKNOWN,
            None,
            None,
            None,
            f"BENCH_{target_name}_PROMOTION_AMBIGUOUS",
            witness_steps=base_steps,
            unsupported_reasons=("PROMOTION_OPTION_AMBIGUOUS",),
            current_hand_count=current_hand,
        )

    active = list(mine.active)
    if ready_delay == 0 and len(active) == 1:
        active_pokemon = active[0]
        if (
            active_pokemon.id == DUDUNSPARCE
            and mine.deckCount >= 3
            and len(mine.bench) == 1
            and mine.bench[0].serial == top.serial
        ):
            ability_status, ability_witness = _ability_option(
                obs, active_pokemon.serial
            )
            if ability_status == "EXACT":
                return _distance(
                    CERTIFIED,
                    0,
                    ready_actions + 1,
                    ready_prompts + 1,
                    (
                        f"BENCH_{target_name}_READY_AFTER_RUN_AWAY"
                    ),
                    witness_steps=base_steps
                    + [
                        {
                            "kind": "RUN_AWAY_DRAW",
                            "draw_count": 3,
                            "hand_count_damage_delta": 60,
                            **ability_witness,
                        },
                        {
                            "kind": "UNIQUE_POST_RUN_AWAY_PROMOTION",
                            "target_serial": future_top_serial,
                        },
                    ],
                    certified_draw_count=3,
                    certified_draw_damage_delta=60,
                    deterministic_hand_expenditures=hand_expenditures,
                    current_hand_count=current_hand,
                )
            if ability_status == "AMBIGUOUS":
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    "RUN_AWAY_OPTION_AMBIGUOUS",
                    unsupported_reasons=(
                        "RUN_AWAY_OPTION_AMBIGUOUS",
                    ),
                    current_hand_count=current_hand,
                )

        if obs.select.context == parent.SelectContext.MAIN:
            retreat_status, retreat_witness = _retreat_option(obs)
            active_units = _energy_units(active_pokemon)
            active_data = parent.card_table.get(active_pokemon.id)
            status = _status_clear(mine)
            retreat_cost = getattr(active_data, "retreatCost", None)
            can_retreat = (
                active_units is not None
                and type(retreat_cost) is int
                and len(active_units) >= retreat_cost
                and status is True
                and obs.current.retreated is False
            )
            if retreat_status == "EXACT" and can_retreat:
                return _distance(
                    CERTIFIED,
                    0,
                    ready_actions + 1,
                    ready_prompts + 1,
                    (
                        f"BENCH_{target_name}_READY_AFTER_EXACT_RETREAT"
                    ),
                    witness_steps=base_steps
                    + [
                        {
                            "kind": "EXACT_RETREAT",
                            "retreat_cost": retreat_cost,
                            **retreat_witness,
                        },
                        {
                            "kind": "PROMOTE_SERIAL",
                            "target_serial": future_top_serial,
                        },
                    ],
                    deterministic_hand_expenditures=hand_expenditures,
                    current_hand_count=current_hand,
                )
            if retreat_status == "AMBIGUOUS" or status is None:
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    f"BENCH_{target_name}_SWITCH_UNKNOWN",
                    unsupported_reasons=(
                        "RETREAT_OR_STATUS_SEMANTIC_UNKNOWN",
                    ),
                    current_hand_count=current_hand,
                )

    return _distance(
        POSSIBLE,
        ready_delay,
        ready_actions,
        ready_prompts,
        f"BENCH_{target_name}_NEEDS_SAFE_SWITCH",
        witness_steps=base_steps,
        missing_requirements=("NEEDS_SAFE_SWITCH",),
        deterministic_hand_expenditures=hand_expenditures,
        current_hand_count=current_hand,
    )


def _maturation_route(
    obs: Any,
    line: dict[str, Any],
    *,
    target_id: int,
    attack_id: int,
    target_name: str,
) -> dict[str, Any]:
    mine = obs.current.players[obs.current.yourIndex]
    pokemon = line["pokemon"]
    stage_ids = {
        ABRA: (KADABRA, ALAKAZAM),
        KADABRA: (ALAKAZAM,),
        ALAKAZAM: (),
    } if target_id == ALAKAZAM else {
        ABRA: (KADABRA,),
        KADABRA: (),
    }
    needed_stages = stage_ids.get(pokemon.id)
    if needed_stages is None:
        return _distance(
            IMPOSSIBLE,
            2,
            0,
            0,
            f"{target_name}_NOT_REACHABLE_FROM_TOP_STAGE",
            missing_requirements=("CANNOT_DEVOLVE",),
            current_hand_count=mine.handCount,
        )

    chosen_stage_cards: list[Any] = []
    missing_stage_ids: list[int] = []
    for card_id in needed_stages:
        candidates = _hand_cards(mine, card_id)
        if candidates:
            chosen_stage_cards.append(candidates[0])
        else:
            missing_stage_ids.append(card_id)
    if missing_stage_ids:
        route_class, requirements = _missing_component_class(
            mine, missing_stage_ids
        )
        return _distance(
            route_class,
            2 if pokemon.id == ABRA else 1,
            len(needed_stages),
            len(needed_stages),
            f"{target_name}_MISSING_EVOLUTION_COMPONENT",
            missing_requirements=requirements,
            current_hand_count=mine.handCount,
        )

    current_main = (
        obs.select.context == parent.SelectContext.MAIN
        and obs.current.result == -1
    )
    first_evolve_delay = 0
    steps: list[dict[str, Any]] = []
    if needed_stages:
        if pokemon.appearThisTurn:
            first_evolve_delay = 1
        elif current_main:
            status, witness = _evolve_option(
                obs,
                chosen_stage_cards[0].serial,
                pokemon.serial,
            )
            if status == "EXACT":
                steps.append(
                    {
                        "kind": "EVOLVE",
                        "source_serial": chosen_stage_cards[0].serial,
                        "target_serial": pokemon.serial,
                        **witness,
                    }
                )
            elif status == "AMBIGUOUS":
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    f"{target_name}_EVOLUTION_OPTION_AMBIGUOUS",
                    unsupported_reasons=(
                        "EVOLUTION_OPTION_AMBIGUOUS",
                    ),
                    current_hand_count=mine.handCount,
                )
            else:
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    f"{target_name}_EXPECTED_EVOLUTION_OPTION_ABSENT",
                    unsupported_reasons=(
                        "EXPECTED_EVOLUTION_OPTION_ABSENT",
                    ),
                    current_hand_count=mine.handCount,
                )
        elif (
            obs.select.context == parent.SelectContext.TO_ACTIVE
            and line["location"] == "BENCH"
        ):
            first_evolve_delay = 0
            steps.append(
                {
                    "kind": "EVOLVE_AFTER_CURRENT_PROMOTION",
                    "source_serial": chosen_stage_cards[0].serial,
                    "target_serial": pokemon.serial,
                }
            )
        else:
            return _distance(
                UNKNOWN,
                None,
                None,
                None,
                f"{target_name}_TRANSACTION_INTERMEDIATE",
                unsupported_reasons=(
                    "FUTURE_MAIN_REENTRY_NOT_UNIQUE",
                ),
                current_hand_count=mine.handCount,
            )

    evolution_delay = (
        first_evolve_delay + max(0, len(needed_stages) - 1)
    )
    for index, card in enumerate(chosen_stage_cards):
        if index == 0 and steps:
            continue
        steps.append(
            {
                "kind": "EVOLVE_FUTURE_SELF_TURN",
                "source_serial": card.serial,
                "turn_delay": first_evolve_delay + index,
            }
        )

    payable = _can_pay(pokemon, attack_id)
    if payable is None:
        return _distance(
            UNKNOWN,
            None,
            None,
            None,
            f"{target_name}_ENERGY_SEMANTIC_UNKNOWN",
            unsupported_reasons=("ENERGY_SEMANTIC_UNKNOWN",),
            current_hand_count=mine.handCount,
        )

    attach_count = 0
    attach_prompt_count = 0
    attach_delay = 0
    hand_expenditures = len(chosen_stage_cards)
    if not payable:
        energy_cards = sorted(
            [
                card
                for card in mine.hand
                if card.id in PSYCHIC_ENERGY_IDS
            ],
            key=lambda card: (
                0 if card.id == 5 else 1,
                card.serial,
            ),
        )
        if not energy_cards:
            route_class = (
                IMPOSSIBLE if mine.deckCount == 0 else POSSIBLE
            )
            return _distance(
                route_class,
                max(evolution_delay, 1),
                len(needed_stages) + 1,
                len(needed_stages),
                f"{target_name}_MISSING_PSYCHIC_ENERGY",
                missing_requirements=(
                    "NEEDS_PSYCHIC_ENERGY",
                    "NEEDS_SEARCH_OR_DRAW",
                ),
                current_hand_count=mine.handCount,
            )
        energy = energy_cards[0]
        attach_count = 1
        attach_prompt_count = 1 if energy.id == 19 else 0
        hand_expenditures += 1
        if current_main and obs.current.energyAttached is False:
            status, witness = _attach_option(
                obs, energy.serial, pokemon.serial
            )
            if status == "EXACT":
                steps.append(
                    {
                        "kind": "ATTACH_PSYCHIC",
                        "source_serial": energy.serial,
                        "source_card_id": energy.id,
                        "target_serial": pokemon.serial,
                        "unknown_search_identities_not_used": (
                            energy.id == 19
                        ),
                        **witness,
                    }
                )
            elif status == "AMBIGUOUS":
                return _distance(
                    UNKNOWN,
                    None,
                    None,
                    None,
                    f"{target_name}_ATTACH_OPTION_AMBIGUOUS",
                    unsupported_reasons=(
                        "ATTACH_OPTION_AMBIGUOUS",
                    ),
                    current_hand_count=mine.handCount,
                )
            else:
                if evolution_delay > 0:
                    attach_delay = 1
                    steps.append(
                        {
                            "kind": "ATTACH_PSYCHIC_FUTURE_SELF_TURN",
                            "source_serial": energy.serial,
                            "source_card_id": energy.id,
                            "turn_delay": 1,
                        }
                    )
                else:
                    return _distance(
                        UNKNOWN,
                        None,
                        None,
                        None,
                        f"{target_name}_EXPECTED_ATTACH_OPTION_ABSENT",
                        unsupported_reasons=(
                            "EXPECTED_ATTACH_OPTION_ABSENT",
                        ),
                        current_hand_count=mine.handCount,
                    )
        else:
            attach_delay = 1
            steps.append(
                {
                    "kind": "ATTACH_PSYCHIC_FUTURE_SELF_TURN",
                    "source_serial": energy.serial,
                    "source_card_id": energy.id,
                    "turn_delay": 1,
                }
            )

    line_with_steps = dict(line)
    line_with_steps["pending_steps"] = steps
    if chosen_stage_cards:
        line_with_steps["future_top_serial"] = (
            chosen_stage_cards[-1].serial
        )
    return _active_transfer_route(
        obs,
        line_with_steps,
        ready_delay=max(evolution_delay, attach_delay),
        ready_actions=len(needed_stages) + attach_count,
        # Each supported evolution produces an exact optional Psychic Draw
        # callback.  It is a child prompt even if NO is selected.
        ready_prompts=len(needed_stages) + attach_prompt_count,
        hand_expenditures=hand_expenditures,
        target_attack_id=attack_id,
        target_name=target_name,
    )


def _unknown_line_route(
    template: str,
    reasons: Iterable[str],
) -> dict[str, Any]:
    return _distance(
        UNKNOWN,
        None,
        None,
        None,
        template,
        unsupported_reasons=reasons,
    )


def _line_row(
    obs: Any,
    pokemon: Any,
    location: str,
    index: int,
    global_reasons: list[str],
) -> dict[str, Any]:
    owner = obs.current.yourIndex
    card_ids, serials, stack_reasons = _line_stack(pokemon, owner)
    reasons = sorted(set(global_reasons + stack_reasons))
    line_id: int | str = (
        serials[0]
        if serials and type(serials[0]) is int
        else f"UNKNOWN:{location}:{index}"
    )
    energy_units = _energy_units(pokemon)
    if energy_units is None:
        reasons.append("ENERGY_SEMANTIC_UNKNOWN")
    line = {
        "line_id": line_id,
        "location": location,
        "location_index": index,
        "top_card_id": getattr(pokemon, "id", None),
        "top_serial": getattr(pokemon, "serial", None),
        "stack_serials": list(serials),
        "stack_card_ids": list(card_ids),
        "energy_units": (
            list(energy_units) if energy_units is not None else None
        ),
        "pokemon": pokemon,
        "pending_steps": [],
    }
    if reasons:
        primary = _unknown_line_route(
            "LINE_FAIL_CLOSED", reasons
        )
        fallback = copy.deepcopy(primary)
        primary_routes = [primary]
        fallback_routes = [fallback]
    else:
        primary_routes = [
            _maturation_route(
                obs,
                line,
                target_id=ALAKAZAM,
                attack_id=ATTACK_POWERFUL_HAND,
                target_name="ALAKAZAM_POWERFUL_HAND",
            )
        ]
        fallback_routes = [
            _maturation_route(
                obs,
                line,
                target_id=KADABRA,
                attack_id=ATTACK_SUPER_PSY_BOLT,
                target_name="KADABRA_DAMAGE_ATTACK",
            )
        ]
        primary = reduce_routes(primary_routes)
        fallback = reduce_routes(fallback_routes)
    return {
        "line_id": line_id,
        "location": location,
        "location_index": index,
        "top_card_id": getattr(pokemon, "id", None),
        "top_serial": getattr(pokemon, "serial", None),
        "stack_serials": list(serials),
        "stack_card_ids": list(card_ids),
        "energy_units": (
            list(energy_units) if energy_units is not None else None
        ),
        "primary_distance": primary,
        "fallback_attack_distance": fallback,
        "next_attacker_action_distance": copy.deepcopy(primary),
        "missing_requirements": sorted(
            set(
                primary["witness"]["missing_requirements"]
                + fallback["witness"]["missing_requirements"]
            )
        ),
        "interruption_exposure": primary[
            "interruption_exposure"
        ],
        "witness_steps": _safe_copy(
            primary["witness"]["steps"]
        ),
        "primary_route_witnesses": primary_routes,
        "fallback_route_witnesses": fallback_routes,
        "unsupported_reasons": sorted(set(reasons)),
    }


def _reconstruct_row(
    obs: Any,
    global_reasons: list[str],
) -> dict[str, Any]:
    mine = obs.current.players[obs.current.yourIndex]
    if global_reasons:
        primary = _unknown_line_route(
            "RECONSTRUCT_FAIL_CLOSED", global_reasons
        )
        fallback = copy.deepcopy(primary)
    else:
        hand_by_id = {
            card_id: _hand_cards(mine, card_id)
            for card_id in (ABRA, KADABRA, ALAKAZAM)
        }
        energy_cards = sorted(
            [
                card
                for card in mine.hand
                if card.id in PSYCHIC_ENERGY_IDS
            ],
            key=lambda card: (
                0 if card.id == 5 else 1,
                card.serial,
            ),
        )
        missing = [
            card_id
            for card_id, rows in hand_by_id.items()
            if not rows
        ]
        if missing or not energy_cards:
            route_class, requirements = _missing_component_class(
                mine, missing
            )
            if not energy_cards:
                requirements.extend(
                    (
                        "NEEDS_PSYCHIC_ENERGY",
                        "NEEDS_SEARCH_OR_DRAW",
                    )
                )
                energy_class = (
                    IMPOSSIBLE
                    if mine.deckCount == 0
                    else POSSIBLE
                )
                route_class = reduce_routes(
                    (
                        _distance(
                            route_class,
                            2,
                            0,
                            0,
                            "MISSING_EVOLUTION_PARTS",
                        ),
                        _distance(
                            energy_class,
                            2,
                            0,
                            0,
                            "MISSING_PSYCHIC_ENERGY",
                        ),
                    )
                )["route_class"]
            primary = _distance(
                route_class,
                2,
                4,
                2,
                "RECONSTRUCT_MISSING_COMPONENT",
                missing_requirements=requirements,
                current_hand_count=mine.handCount,
            )
            fallback = _distance(
                route_class,
                1,
                3,
                1,
                "RECONSTRUCT_KADABRA_MISSING_COMPONENT",
                missing_requirements=requirements,
                current_hand_count=mine.handCount,
            )
        elif len(mine.bench) >= mine.benchMax:
            primary = _distance(
                POSSIBLE,
                2,
                4,
                2,
                "RECONSTRUCT_NEEDS_BENCH_SPACE",
                missing_requirements=(
                    "NEEDS_BENCH_SPACE",
                    "NEEDS_SAFE_SWITCH",
                ),
                current_hand_count=mine.handCount,
            )
            fallback = copy.deepcopy(primary)
        else:
            abra = hand_by_id[ABRA][0]
            energy = energy_cards[0]
            play_status, play_witness = _option_result(
                obs,
                lambda option: (
                    option.type == parent.OptionType.PLAY
                    and getattr(_option_card(obs, option), "serial", None)
                    == abra.serial
                ),
            )
            route_class = (
                CERTIFIED if play_status == "EXACT" else UNKNOWN
            )
            unsupported = (
                ()
                if route_class == CERTIFIED
                else ("ABRA_PLAY_OPTION_NOT_EXACT",)
            )
            steps = (
                [
                    {
                        "kind": "PLAY_ABRA",
                        "source_serial": abra.serial,
                        **play_witness,
                    },
                    {
                        "kind": "EVOLVE_FUTURE_SELF_TURN",
                        "source_serial": hand_by_id[KADABRA][0].serial,
                        "turn_delay": 1,
                    },
                    {
                        "kind": "EVOLVE_FUTURE_SELF_TURN",
                        "source_serial": hand_by_id[ALAKAZAM][0].serial,
                        "turn_delay": 2,
                    },
                    {
                        "kind": "ATTACH_PSYCHIC_FUTURE_SELF_TURN",
                        "source_serial": energy.serial,
                        "source_card_id": energy.id,
                        "turn_delay": 1,
                        "unknown_search_identities_not_used": (
                            energy.id == 19
                        ),
                    },
                ]
                if play_witness is not None
                else []
            )
            primary_steps = list(steps)
            fallback_steps = [
                step
                for step in steps
                if not (
                    step.get("kind") == "EVOLVE_FUTURE_SELF_TURN"
                    and step.get("source_serial")
                    == hand_by_id[ALAKAZAM][0].serial
                )
            ]
            transfer_certified = False
            if (
                route_class == CERTIFIED
                and len(mine.active) == 1
                and mine.active[0].id == DUDUNSPARCE
                and len(mine.bench) == 0
                and mine.deckCount >= 5
            ):
                ability_status, ability_witness = _ability_option(
                    obs, mine.active[0].serial
                )
                if ability_status == "EXACT":
                    transfer_certified = True
                    primary_steps.append(
                        {
                            "kind": "RUN_AWAY_AFTER_MATURATION",
                            "turn_delay": 2,
                            "draw_count": 3,
                            "hand_count_damage_delta": 60,
                            **ability_witness,
                        }
                    )
                    fallback_steps.append(
                        {
                            "kind": "RUN_AWAY_AFTER_MATURATION",
                            "turn_delay": 1,
                            "draw_count": 3,
                            "hand_count_damage_delta": 60,
                            **ability_witness,
                        }
                    )
            final_class = (
                CERTIFIED
                if transfer_certified
                else (
                    POSSIBLE
                    if route_class == CERTIFIED
                    else route_class
                )
            )
            switch_requirement = (
                () if transfer_certified else ("NEEDS_SAFE_SWITCH",)
            )
            transfer_actions = 1 if transfer_certified else 0
            transfer_prompts = 1 if transfer_certified else 0
            energy_prompts = 1 if energy.id == 19 else 0
            primary = _distance(
                final_class,
                2,
                4 + transfer_actions,
                2 + energy_prompts + transfer_prompts,
                "PLAY_ABRA_FROM_HAND_AND_MATURE",
                witness_steps=primary_steps,
                missing_requirements=switch_requirement,
                unsupported_reasons=unsupported,
                certified_draw_count=3 if transfer_certified else 0,
                certified_draw_damage_delta=(
                    60 if transfer_certified else 0
                ),
                deterministic_hand_expenditures=4,
                current_hand_count=mine.handCount,
            )
            fallback = _distance(
                final_class,
                1,
                3 + transfer_actions,
                1 + energy_prompts + transfer_prompts,
                "PLAY_ABRA_FROM_HAND_AND_MATURE_KADABRA",
                witness_steps=fallback_steps,
                missing_requirements=switch_requirement,
                unsupported_reasons=unsupported,
                certified_draw_count=3 if transfer_certified else 0,
                certified_draw_damage_delta=(
                    60 if transfer_certified else 0
                ),
                deterministic_hand_expenditures=3,
                current_hand_count=mine.handCount,
            )
    return {
        "line_id": "RECONSTRUCT",
        "location": "VIRTUAL",
        "location_index": None,
        "top_card_id": None,
        "top_serial": None,
        "stack_serials": [],
        "stack_card_ids": [],
        "energy_units": [],
        "primary_distance": primary,
        "fallback_attack_distance": fallback,
        "next_attacker_action_distance": copy.deepcopy(primary),
        "missing_requirements": sorted(
            set(
                primary["witness"]["missing_requirements"]
                + fallback["witness"]["missing_requirements"]
            )
        ),
        "interruption_exposure": primary[
            "interruption_exposure"
        ],
        "witness_steps": _safe_copy(
            primary["witness"]["steps"]
        ),
        "primary_route_witnesses": [primary],
        "fallback_route_witnesses": [fallback],
        "unsupported_reasons": sorted(set(global_reasons)),
    }


def _best_route(
    rows: Iterable[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    candidates = []
    for row in rows:
        route = row[field]
        candidate = copy.deepcopy(route)
        candidate["line_id"] = row["line_id"]
        candidate["location"] = row["location"]
        candidates.append(candidate)
    return reduce_routes(candidates)


def _distance_comparable_quality(
    distance: dict[str, Any],
) -> tuple[int, int] | None:
    route_class = distance.get("route_class")
    if route_class == UNKNOWN:
        return None
    class_rank = {
        CERTIFIED: 0,
        POSSIBLE: 1,
        IMPOSSIBLE: 2,
    }.get(route_class)
    delay = distance.get("turn_delay")
    if class_rank is None or not isinstance(delay, int):
        return None
    return class_rank, delay


def _line_importance(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    live = [row for row in rows if row["location"] != "VIRTUAL"]
    result = []
    if len(live) == 1:
        row = live[0]
        importance = (
            "UNKNOWN_IMPORTANCE"
            if row["primary_distance"]["route_class"] == UNKNOWN
            else "UNIQUE"
        )
        return [
            {
                "line_id": row["line_id"],
                "importance": importance,
                "reason": (
                    "ONLY_LIVE_ALAKAZAM_LINE"
                    if importance == "UNIQUE"
                    else "ONLY_LINE_IS_UNRESOLVED"
                ),
            }
        ]

    baseline = _best_route(live, "primary_distance")
    baseline_quality = _distance_comparable_quality(baseline)
    for removed in live:
        remaining = [
            row for row in live if row is not removed
        ]
        if not remaining:
            result.append(
                {
                    "line_id": removed["line_id"],
                    "importance": "UNIQUE",
                    "reason": "ONLY_LIVE_ALAKAZAM_LINE",
                }
            )
            continue
        after = _best_route(remaining, "primary_distance")
        after_quality = _distance_comparable_quality(after)
        if baseline_quality is None or after_quality is None:
            importance = "UNKNOWN_IMPORTANCE"
            reason = "UNKNOWN_DOMINATES_REMOVAL_REDUCTION"
        elif after_quality > baseline_quality:
            importance = "IMPORTANT"
            reason = "BEST_PRIMARY_DISTANCE_WORSENS"
        else:
            removed_energy = len(removed.get("energy_units") or [])
            max_other_energy = max(
                len(row.get("energy_units") or [])
                for row in remaining
            )
            removed_stage = {
                ABRA: 0,
                KADABRA: 1,
                ALAKAZAM: 2,
            }.get(removed["top_card_id"], -1)
            max_other_stage = max(
                {
                    ABRA: 0,
                    KADABRA: 1,
                    ALAKAZAM: 2,
                }.get(row["top_card_id"], -1)
                for row in remaining
            )
            if (
                removed_energy > 0
                and max_other_energy == 0
            ):
                importance = "IMPORTANT"
                reason = "ONLY_ENERGIZED_LINE"
            elif removed_stage > max_other_stage:
                importance = "IMPORTANT"
                reason = "SOLE_MOST_EVOLVED_LINE"
            else:
                importance = "REDUNDANT"
                reason = "REMOVAL_DOES_NOT_WORSEN_SUPPORTED_DISTANCE"
        result.append(
            {
                "line_id": removed["line_id"],
                "importance": importance,
                "reason": reason,
                "baseline_primary": _safe_copy(baseline),
                "after_removal_primary": _safe_copy(after),
            }
        )
    return result


def _global_unknown_analysis(
    reasons: Iterable[str],
) -> dict[str, Any]:
    resolved = sorted(set(reasons)) or ["RAW_OBSERVATION_MALFORMED"]
    primary = _unknown_line_route(
        "GLOBAL_FAIL_CLOSED", resolved
    )
    fallback = copy.deepcopy(primary)
    row = {
        "line_id": "GLOBAL_UNKNOWN",
        "location": "UNKNOWN",
        "location_index": None,
        "top_card_id": None,
        "top_serial": None,
        "stack_serials": [],
        "stack_card_ids": [],
        "energy_units": None,
        "primary_distance": primary,
        "fallback_attack_distance": fallback,
        "next_attacker_action_distance": copy.deepcopy(primary),
        "missing_requirements": [],
        "interruption_exposure": UNKNOWN,
        "witness_steps": [],
        "primary_route_witnesses": [primary],
        "fallback_route_witnesses": [fallback],
        "unsupported_reasons": resolved,
    }
    return {
        "route_rows": [row],
        "best_primary_route": {
            **copy.deepcopy(primary),
            "line_id": "GLOBAL_UNKNOWN",
            "location": "UNKNOWN",
        },
        "best_fallback_route": {
            **copy.deepcopy(fallback),
            "line_id": "GLOBAL_UNKNOWN",
            "location": "UNKNOWN",
        },
        "line_importance_rows": [
            {
                "line_id": "GLOBAL_UNKNOWN",
                "importance": "UNKNOWN_IMPORTANCE",
                "reason": "GLOBAL_FAIL_CLOSED",
            }
        ],
        "unsupported_reasons": resolved,
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
    }


def _raw_preflight_reasons(raw: dict[str, Any]) -> list[str]:
    try:
        current = raw["current"]
        select = raw["select"]
        owner = current["yourIndex"]
        players = current["players"]
        mine = players[owner]
    except (KeyError, TypeError, IndexError):
        return ["RAW_OBSERVATION_MALFORMED"]
    reasons = []
    if owner not in (0, 1):
        reasons.append("OWNER_UNKNOWN")
    if not isinstance(players, list) or len(players) != 2:
        reasons.append("PLAYERS_MALFORMED")
    if not isinstance(select, dict) or not isinstance(
        select.get("option"), list
    ):
        reasons.append("SELECT_MALFORMED")
    for key in (
        "energyAttached",
        "retreated",
        "supporterPlayed",
        "stadiumPlayed",
    ):
        if type(current.get(key)) is not bool:
            reasons.append(f"{key.upper()}_FLAG_UNKNOWN")
    for key in (
        "asleep",
        "paralyzed",
        "confused",
        "poisoned",
        "burned",
    ):
        if type(mine.get(key)) is not bool:
            reasons.append(f"{key.upper()}_STATUS_UNKNOWN")
    return reasons


def _analyze_impl(
    raw: dict[str, Any],
    *,
    external_reasons: Iterable[str] = (),
) -> dict[str, Any]:
    preflight = _raw_preflight_reasons(raw)
    if preflight:
        return _global_unknown_analysis(preflight)
    try:
        obs = parent.to_observation_class(copy.deepcopy(raw))
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        return _global_unknown_analysis(
            ("RAW_OBSERVATION_PARSE_UNSUPPORTED",)
        )
    reasons: list[str] = []
    if not runtime_model.raw_parsed_agree(raw, obs):
        reasons.append("RAW_PARSED_MISMATCH")
    reasons.extend(external_reasons)
    reasons.extend(_fixed_metadata_reasons())
    reasons.extend(_zone_integrity_reasons(raw, obs))
    _, option_reasons = _option_key_rows(obs)
    reasons.extend(option_reasons)
    reasons = sorted(set(reasons))

    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    context = _int((raw.get("select") or {}).get("context"))
    if not list(mine.active) and context in (2, 38):
        return _global_unknown_analysis(
            (
                *external_reasons,
                "PRE_SETUP_ACTIVE_IDENTITY_UNKNOWN",
            )
        )
    if any(
        pokemon is None or not hasattr(pokemon, "id")
        for zone in (mine.active, mine.bench)
        for pokemon in list(zone)
    ):
        return _global_unknown_analysis(
            (
                *external_reasons,
                "FACE_DOWN_IN_PLAY_IDENTITY_UNKNOWN",
            )
        )
    rows = []
    for location, zone in (
        ("ACTIVE", list(mine.active)),
        ("BENCH", list(mine.bench)),
    ):
        for index, pokemon in enumerate(zone):
            if pokemon.id in SUPPORTED_LINE_IDS:
                rows.append(
                    _line_row(
                        obs,
                        pokemon,
                        location,
                        index,
                        reasons,
                    )
                )
    if not rows:
        rows.append(_reconstruct_row(obs, reasons))

    best_primary = _best_route(rows, "primary_distance")
    best_fallback = _best_route(
        rows, "fallback_attack_distance"
    )
    importance = _line_importance(rows)
    certified_draw_count = max(
        [
            route.get("certified_draw_count", 0)
            for row in rows
            for key in (
                "primary_route_witnesses",
                "fallback_route_witnesses",
            )
            for route in row[key]
        ]
        or [0]
    )
    certified_draw_damage_delta = max(
        [
            route.get("certified_draw_damage_delta", 0)
            for row in rows
            for key in (
                "primary_route_witnesses",
                "fallback_route_witnesses",
            )
            for route in row[key]
        ]
        or [0]
    )
    return {
        "route_rows": rows,
        "best_primary_route": best_primary,
        "best_fallback_route": best_fallback,
        "line_importance_rows": importance,
        "unsupported_reasons": reasons,
        "certified_draw_count": certified_draw_count,
        "certified_draw_damage_delta": certified_draw_damage_delta,
    }


def analyze(
    raw: Any,
    action: Any,
    *,
    parent_trace: Any = None,
    transaction_state: Any = None,
) -> dict[str, Any]:
    """Return one fail-closed trace while preserving the supplied action."""
    trace = _base_trace(
        raw,
        action,
        parent_trace=parent_trace,
        transaction_state=transaction_state,
    )
    try:
        if not isinstance(raw, dict):
            raise TypeError("raw observation must be a dict")
        transaction_reasons = []
        transaction_flags = _normalized_transaction_flags(
            transaction_state
        )
        if any(transaction_flags.values()):
            transaction_reasons.append(
                "PARENT_TRANSACTION_IN_PROGRESS"
            )
        trace.update(
            _analyze_impl(
                raw,
                external_reasons=transaction_reasons,
            )
        )
        return trace
    except Exception as error:
        return metric_exception_trace(
            raw,
            action,
            error,
            parent_trace=parent_trace,
            transaction_state=transaction_state,
        )


__all__ = [
    "ALAKAZAM",
    "CERTIFIED",
    "IMPOSSIBLE",
    "KADABRA",
    "POSSIBLE",
    "RULE_VERSION",
    "UNKNOWN",
    "analyze",
    "metric_exception_trace",
    "reduce_routes",
]
