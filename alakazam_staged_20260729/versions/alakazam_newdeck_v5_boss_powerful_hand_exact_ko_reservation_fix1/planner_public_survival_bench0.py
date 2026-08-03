"""Stateful outer transaction wrapper for C3 public Bench-0 survival."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import planner_deck_adaptation_v1 as deck_v1
import planner_integrated as integrated
import planner_policy as core
import planner_public_damage_continuity as damage
import planner_runtime_model as runtime_model


RULE_VERSION = damage.RULE_VERSION
DECK_PATH = Path(__file__).resolve().with_name("deck.csv")

PUBLIC_LEDGER: dict[str, Any] = {}
C3_TRANSACTION: dict[str, Any] | None = None
C3_DUPLICATES: dict[str, tuple[Any, ...]] = {}
C3_DUPLICATE_ORDER: list[str] = []
LAST_C3_TRACE: dict[str, Any] | None = None
_DECK_BOUNDARY_ARMED = True
_CACHE_LIMIT = 128


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def exact_deck() -> list[int]:
    with DECK_PATH.open("r", newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.reader(handle) if row]
    deck = [int(row[0]) for row in rows]
    if len(deck) != 60:
        raise RuntimeError("C3_DECK_NOT_60")
    return deck


def reset() -> None:
    global C3_TRANSACTION, LAST_C3_TRACE, _DECK_BOUNDARY_ARMED
    PUBLIC_LEDGER.clear()
    PUBLIC_LEDGER.update(
        {
            "boundary_certified": False,
            "ambiguous": False,
            "turn": None,
            "turn_actor": None,
            "owner": None,
            "opponent": None,
            "committed_current_turn": [],
            "unavailable": [],
            "same_battle_power_pro_seen": False,
            "family_marker_ids": [],
            "power_pro_seen_serials": [],
            "last_attack_by_serial": {},
            "seen_events": [],
            "last_result": None,
            "last_action_count": None,
            "last_public_serials": [],
        }
    )
    C3_TRANSACTION = None
    C3_DUPLICATES.clear()
    C3_DUPLICATE_ORDER.clear()
    LAST_C3_TRACE = None
    _DECK_BOUNDARY_ARMED = True


reset()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=repr,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _card_id(card: Any) -> int | None:
    return (
        _int(card.get("id", card.get("cardId")))
        if isinstance(card, dict)
        else None
    )


def _serial(card: Any) -> int | None:
    return _int(card.get("serial")) if isinstance(card, dict) else None


def _card_row(card: Any) -> tuple[Any, ...] | None:
    if not isinstance(card, dict):
        return None
    return (
        _card_id(card),
        _serial(card),
        _int(card.get("playerIndex")),
    )


def _pokemon_row(card: Any) -> Any:
    if not isinstance(card, dict):
        return None
    return {
        "id": _card_id(card),
        "serial": _serial(card),
        "playerIndex": _int(card.get("playerIndex")),
        "hp": _int(card.get("hp")),
        "maxHp": _int(card.get("maxHp")),
        "appearThisTurn": card.get("appearThisTurn"),
        "energies": list(card.get("energies", ()))
        if isinstance(card.get("energies"), list)
        else None,
        "energyCards": sorted(
            filter(
                lambda value: value is not None,
                (_card_row(value) for value in card.get("energyCards", ())),
            )
        )
        if isinstance(card.get("energyCards"), list)
        else None,
        "tools": sorted(
            filter(
                lambda value: value is not None,
                (_card_row(value) for value in card.get("tools", ())),
            )
        )
        if isinstance(card.get("tools"), list)
        else None,
        "preEvolution": sorted(
            filter(
                lambda value: value is not None,
                (_card_row(value) for value in card.get("preEvolution", ())),
            )
        )
        if isinstance(card.get("preEvolution"), list)
        else None,
    }


def _public_state(obs: dict[str, Any]) -> dict[str, Any] | None:
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
    if not _serial_uniqueness_valid(current, owner):
        return None
    result = {
        "turn": _int(current.get("turn")),
        "action_count": _int(current.get("turnActionCount")),
        "owner": owner,
        "first_player": _int(current.get("firstPlayer")),
        "result": _int(current.get("result")),
        "energyAttached": current.get("energyAttached"),
        "retreated": current.get("retreated"),
        "stadiumPlayed": current.get("stadiumPlayed"),
        "supporterPlayed": current.get("supporterPlayed"),
        "stadium": sorted(
            filter(
                lambda value: value is not None,
                (_card_row(value) for value in current.get("stadium", ())),
            )
        )
        if isinstance(current.get("stadium"), list)
        else None,
        "players": [],
    }
    for index, player in enumerate(players):
        active = player.get("active")
        bench = player.get("bench")
        discard = player.get("discard")
        lost = player.get("lost", [])
        prize = player.get("prize")
        hand = player.get("hand")
        if (
            not isinstance(active, list)
            or not isinstance(bench, list)
            or not isinstance(discard, list)
            or not isinstance(lost, list)
            or not isinstance(prize, list)
            or (index == owner and not isinstance(hand, list))
        ):
            return None
        result["players"].append(
            {
                "active": [_pokemon_row(card) for card in active],
                "bench": [_pokemon_row(card) for card in bench],
                "discard": sorted(
                    filter(
                        lambda value: value is not None,
                        (_card_row(value) for value in discard),
                    )
                ),
                "lost": sorted(
                    filter(
                        lambda value: value is not None,
                        (_card_row(value) for value in lost),
                    )
                ),
                "hand": sorted(
                    filter(
                        lambda value: value is not None,
                        (_card_row(value) for value in hand),
                    )
                )
                if index == owner
                else None,
                "hand_count": _int(player.get("handCount")),
                "deck_count": _int(player.get("deckCount")),
                "prize_count": len(prize),
                "bench_max": _int(player.get("benchMax")),
                "asleep": player.get("asleep"),
                "burned": player.get("burned"),
                "confused": player.get("confused"),
                "paralyzed": player.get("paralyzed"),
                "poisoned": player.get("poisoned"),
            }
        )
    return result


def _option_semantics(obs: dict[str, Any]) -> list[Any]:
    select = obs.get("select") if isinstance(obs, dict) else None
    options = select.get("option") if isinstance(select, dict) else None
    state = _public_state(obs)
    if not isinstance(options, list) or state is None:
        return []
    owner = state["owner"]
    current = obs["current"]
    hand = current["players"][owner].get("hand")
    rows = []
    for option in options:
        if not isinstance(option, dict):
            rows.append(None)
            continue
        option_type = _int(option.get("type"))
        if option_type == damage.PLAY:
            hand_index = _int(option.get("index"))
            card = (
                hand[hand_index]
                if isinstance(hand, list)
                and hand_index is not None
                and 0 <= hand_index < len(hand)
                else None
            )
            rows.append(("PLAY", _card_id(card), _serial(card)))
        elif option_type == damage.ATTACK:
            rows.append(("ATTACK", _int(option.get("attackId"))))
        elif option_type == damage.END:
            rows.append(("END",))
        else:
            rows.append(
                (
                    option_type,
                    _int(option.get("area")),
                    _int(option.get("index")),
                    _int(option.get("playerIndex")),
                )
            )
    return sorted(rows, key=repr)


def _ledger_fingerprint_evidence(obs: dict[str, Any]) -> dict[str, Any]:
    logs = obs.get("logs") if isinstance(obs, dict) else None
    normalized_logs = []
    if isinstance(logs, list):
        for log in logs:
            if not isinstance(log, dict):
                normalized_logs.append(("INVALID_LOG", repr(log)))
                continue
            card_id = _int(log.get("cardId"))
            attack_id = _int(log.get("attackId"))
            if (
                card_id != damage.PREMIUM_POWER_PRO
                and attack_id not in damage.ATTACK_ROWS
            ):
                continue
            normalized_logs.append(
                tuple(
                    (key, log.get(key))
                    for key in (
                        "type",
                        "playerIndex",
                        "cardId",
                        "serial",
                        "attackId",
                        "fromArea",
                        "toArea",
                    )
                )
            )
    return {
        "boundary_certified": PUBLIC_LEDGER.get("boundary_certified"),
        "ambiguous": PUBLIC_LEDGER.get("ambiguous"),
        "family_marker_ids": sorted(
            PUBLIC_LEDGER.get("family_marker_ids", ())
        ),
        "power_pro_seen_serials": sorted(
            PUBLIC_LEDGER.get("power_pro_seen_serials", ())
        ),
        "committed_current_turn": sorted(
            PUBLIC_LEDGER.get("committed_current_turn", ())
        ),
        "unavailable": sorted(PUBLIC_LEDGER.get("unavailable", ())),
        "last_attack_by_serial": copy.deepcopy(
            PUBLIC_LEDGER.get("last_attack_by_serial", {})
        ),
        "relevant_logs": sorted(normalized_logs, key=repr),
    }


def _callback_fingerprint(obs: dict[str, Any]) -> str | None:
    state = _public_state(obs)
    select = obs.get("select") if isinstance(obs, dict) else None
    if state is None or not isinstance(select, dict):
        return None
    return _hash(
        {
            "state": state,
            "context": _int(select.get("context")),
            "type": _int(select.get("type")),
            "min": _int(select.get("minCount")),
            "max": _int(select.get("maxCount")),
            "options": _option_semantics(obs),
            "ledger_evidence": _ledger_fingerprint_evidence(obs),
        }
    )


def _all_public_cards(current: dict[str, Any], owner: int):
    players = current.get("players")
    if not isinstance(players, list):
        return
    for player_index, player in enumerate(players):
        if not isinstance(player, dict):
            continue
        for zone in ("active", "bench", "discard", "lost"):
            cards = player.get(zone)
            if not isinstance(cards, list):
                continue
            for card in cards:
                if not isinstance(card, dict):
                    continue
                yield player_index, zone, card
                if zone in ("active", "bench"):
                    for child_zone in ("preEvolution", "tools", "energyCards"):
                        children = card.get(child_zone)
                        if isinstance(children, list):
                            for child in children:
                                if isinstance(child, dict):
                                    yield player_index, child_zone, child
        if player_index == owner:
            hand = player.get("hand")
            if isinstance(hand, list):
                for card in hand:
                    if isinstance(card, dict):
                        yield player_index, "hand", card
    stadium = current.get("stadium")
    if isinstance(stadium, list):
        for card in stadium:
            if isinstance(card, dict):
                owner = _int(card.get("playerIndex"))
                if owner in (0, 1):
                    yield owner, "stadium", card


def _serial_uniqueness_valid(current: dict[str, Any], owner: int) -> bool:
    seen: set[int] = set()
    for player_index, _, card in _all_public_cards(current, owner):
        raw_serial = card.get("serial")
        if (
            type(raw_serial) is not int
            or raw_serial < 0
            or _card_id(card) is None
            or _int(card.get("playerIndex")) != player_index
            or raw_serial in seen
        ):
            return False
        seen.add(raw_serial)
    stadium = current.get("stadium")
    if isinstance(stadium, list) and any(
        not isinstance(card, dict)
        or _int(card.get("playerIndex")) not in (0, 1)
        for card in stadium
    ):
        return False
    return True


def _ledger_boundary(current: dict[str, Any], public_serials: set[int]) -> None:
    global _DECK_BOUNDARY_ARMED
    turn = _int(current.get("turn"))
    action_count = _int(current.get("turnActionCount"))
    result = _int(current.get("result"))
    previous_result = PUBLIC_LEDGER.get("last_result")
    previous_turn = _int(PUBLIC_LEDGER.get("turn"))
    previous_action_count = _int(PUBLIC_LEDGER.get("last_action_count"))
    previous_serials = set(PUBLIC_LEDGER.get("last_public_serials", ()))
    if _DECK_BOUNDARY_ARMED or (
        previous_result is not None
        and previous_result != -1
        and result == -1
    ):
        reset()
        PUBLIC_LEDGER["boundary_certified"] = True
        _DECK_BOUNDARY_ARMED = False
    elif (
        previous_turn is not None
        and turn is not None
        and turn < previous_turn
    ):
        if (
            action_count is not None
            and previous_action_count is not None
            and action_count <= previous_action_count
            and public_serials != previous_serials
        ):
            reset()
            PUBLIC_LEDGER["boundary_certified"] = True
            _DECK_BOUNDARY_ARMED = False
        else:
            PUBLIC_LEDGER["ambiguous"] = True


def update_public_ledger(obs: dict[str, Any]) -> None:
    current = obs.get("current") if isinstance(obs, dict) else None
    if not isinstance(current, dict):
        return
    players = current.get("players")
    owner = _int(current.get("yourIndex"))
    turn = _int(current.get("turn"))
    if (
        not isinstance(players, list)
        or len(players) != 2
        or owner not in (0, 1)
        or turn is None
    ):
        PUBLIC_LEDGER["ambiguous"] = True
        return
    opponent = 1 - owner
    first_player = _int(current.get("firstPlayer"))
    if first_player not in (0, 1) or turn < 0:
        PUBLIC_LEDGER["ambiguous"] = True
        turn_actor = None
    elif turn == 0:
        turn_actor = None
    else:
        turn_actor = (
            first_player if turn % 2 == 1 else 1 - first_player
        )
    previous_turn = _int(PUBLIC_LEDGER.get("turn"))
    previous_opponent = _int(PUBLIC_LEDGER.get("opponent"))
    identities: dict[int, tuple[int, int]] = {}
    public_serials = set()
    family_marker_ids = set()
    power_pro_seen_serials = set()
    unavailable = set()
    for player_index, zone, card in _all_public_cards(current, owner):
        raw_serial = card.get("serial")
        serial = (
            raw_serial
            if type(raw_serial) is int and raw_serial >= 0
            else None
        )
        card_id = _card_id(card)
        card_owner = _int(card.get("playerIndex"))
        if serial is None or card_id is None or card_owner != player_index:
            PUBLIC_LEDGER["ambiguous"] = True
            continue
        public_serials.add(serial)
        identity = (card_id, card_owner)
        if serial in identities:
            PUBLIC_LEDGER["ambiguous"] = True
        identities[serial] = identity
        if player_index == opponent and card_id in damage.FIGHTING_FAMILY:
            family_marker_ids.add(card_id)
        if (
            player_index == opponent
            and card_id == damage.PREMIUM_POWER_PRO
        ):
            power_pro_seen_serials.add(serial)
        if (
            player_index == opponent
            and card_id == damage.PREMIUM_POWER_PRO
            and zone in ("discard", "lost")
        ):
            unavailable.add(serial)

    _ledger_boundary(current, public_serials)
    if not _serial_uniqueness_valid(current, owner):
        PUBLIC_LEDGER["ambiguous"] = True
    PUBLIC_LEDGER["owner"] = owner
    PUBLIC_LEDGER["opponent"] = opponent
    PUBLIC_LEDGER["turn"] = turn
    PUBLIC_LEDGER["turn_actor"] = turn_actor
    prior_markers = set(PUBLIC_LEDGER.get("family_marker_ids", ()))
    PUBLIC_LEDGER["family_marker_ids"] = sorted(
        prior_markers | family_marker_ids
    )
    prior_power_pro = set(
        PUBLIC_LEDGER.get("power_pro_seen_serials", ())
    )
    if power_pro_seen_serials:
        PUBLIC_LEDGER["same_battle_power_pro_seen"] = True

    seen_events = {
        tuple(value)
        for value in PUBLIC_LEDGER.get("seen_events", ())
        if isinstance(value, (list, tuple))
    }
    committed = (
        set(PUBLIC_LEDGER.get("committed_current_turn", ()))
        if previous_turn == turn and previous_opponent == opponent
        else set()
    )
    # Only a Play in the exact currently observed turn can contribute to the
    # current accumulator.  Prior-turn committed copies remain unavailable via
    # their public discard zone but leave C_t.
    logs = obs.get("logs")
    if not isinstance(logs, list):
        PUBLIC_LEDGER["ambiguous"] = True
        logs = []
    for log in logs:
        if not isinstance(log, dict):
            PUBLIC_LEDGER["ambiguous"] = True
            continue
        log_type = _int(log.get("type"))
        actor = _int(log.get("playerIndex"))
        card_id = _int(log.get("cardId"))
        raw_log_serial = log.get("serial")
        serial = (
            raw_log_serial
            if type(raw_log_serial) is int and raw_log_serial >= 0
            else None
        )
        if card_id == damage.PREMIUM_POWER_PRO:
            PUBLIC_LEDGER["same_battle_power_pro_seen"] = True
            if serial is None or actor not in (0, 1):
                PUBLIC_LEDGER["ambiguous"] = True
                continue
            if actor == opponent:
                power_pro_seen_serials.add(serial)
            event = (turn, actor, log_type, card_id, serial)
            if event not in seen_events:
                seen_events.add(event)
            if (
                log_type == 10
                and actor == opponent
                and turn_actor == opponent
            ):
                if serial not in unavailable:
                    PUBLIC_LEDGER["ambiguous"] = True
                else:
                    committed.add(serial)
            # Direct Hand -> discard is intentionally unavailable-only.
            if (
                log_type == 6
                and actor == opponent
                and _int(log.get("fromArea")) == 2
                and _int(log.get("toArea")) == 3
            ):
                unavailable.add(serial)
            if (
                log_type == 6
                and actor == opponent
                and _int(log.get("fromArea")) == 3
                and _int(log.get("toArea")) in (1, 2)
            ):
                unavailable.discard(serial)
        attack_id = _int(log.get("attackId"))
        if log_type == 15 and attack_id is not None and actor == opponent:
            serial = _int(log.get("serial"))
            if serial is None:
                PUBLIC_LEDGER["ambiguous"] = True
            else:
                event_turn = (
                    turn
                    if actor == turn_actor
                    else turn - 1
                    if turn > 0
                    else None
                )
                if event_turn is None:
                    PUBLIC_LEDGER["ambiguous"] = True
                    continue
                PUBLIC_LEDGER.setdefault("last_attack_by_serial", {})[
                    str(serial)
                ] = {"attack_id": attack_id, "turn": event_turn}

    # A previously unavailable serial disappearing without an exact public
    # recovery move makes recovery status ambiguous.  Exact recovery events
    # above remove it.  New public discard is authoritative.
    previous_unavailable = set(PUBLIC_LEDGER.get("unavailable", ()))
    disappeared = previous_unavailable - unavailable
    if disappeared:
        exact_recovered = {
            _int(log.get("serial"))
            for log in logs
            if isinstance(log, dict)
            and _int(log.get("type")) == 6
            and _int(log.get("playerIndex")) == opponent
            and _int(log.get("cardId")) == damage.PREMIUM_POWER_PRO
            and _int(log.get("fromArea")) == 3
            and _int(log.get("toArea")) in (1, 2)
        }
        if not disappeared <= exact_recovered:
            PUBLIC_LEDGER["ambiguous"] = True

    PUBLIC_LEDGER["committed_current_turn"] = sorted(committed)
    PUBLIC_LEDGER["unavailable"] = sorted(unavailable)
    PUBLIC_LEDGER["power_pro_seen_serials"] = sorted(
        prior_power_pro | power_pro_seen_serials
    )
    PUBLIC_LEDGER["seen_events"] = sorted(seen_events)
    PUBLIC_LEDGER["last_result"] = _int(current.get("result"))
    PUBLIC_LEDGER["last_action_count"] = _int(current.get("turnActionCount"))
    PUBLIC_LEDGER["last_public_serials"] = sorted(public_serials)


def _c3_state_snapshot() -> dict[str, Any]:
    return {
        "ledger": copy.deepcopy(PUBLIC_LEDGER),
        "transaction": copy.deepcopy(C3_TRANSACTION),
        "duplicates": copy.deepcopy(C3_DUPLICATES),
        "duplicate_order": list(C3_DUPLICATE_ORDER),
        "last_trace": copy.deepcopy(LAST_C3_TRACE),
        "deck_boundary_armed": _DECK_BOUNDARY_ARMED,
    }


def _restore_c3_state(snapshot: dict[str, Any]) -> None:
    global C3_TRANSACTION, LAST_C3_TRACE, _DECK_BOUNDARY_ARMED
    PUBLIC_LEDGER.clear()
    PUBLIC_LEDGER.update(copy.deepcopy(snapshot["ledger"]))
    C3_TRANSACTION = copy.deepcopy(snapshot["transaction"])
    C3_DUPLICATES.clear()
    C3_DUPLICATES.update(copy.deepcopy(snapshot["duplicates"]))
    C3_DUPLICATE_ORDER[:] = snapshot["duplicate_order"]
    LAST_C3_TRACE = copy.deepcopy(snapshot["last_trace"])
    _DECK_BOUNDARY_ARMED = bool(snapshot["deck_boundary_armed"])


def _delegate_snapshot(parent: Any, trace_snapshot: Callable[[], Any]):
    return {
        "parent": core.parent_state_snapshot(parent),
        "integrated_transaction": copy.deepcopy(core.INTEGRATED_TRANSACTION),
        "integrated_duplicate_cache": copy.deepcopy(
            core.INTEGRATED_DUPLICATE_CACHE
        ),
        "integrated_duplicate_order": list(core._DUPLICATE_ORDER),
        "integrated_trace_log": copy.deepcopy(core.INTEGRATED_TRACE_LOG),
        "integrated_latest_trace": copy.deepcopy(core.INTEGRATED_LATEST_TRACE),
        "v1_transaction": copy.deepcopy(deck_v1.V1_TRANSACTION),
        "v1_duplicates": copy.deepcopy(deck_v1.V1_DUPLICATES),
        "removed_rule_hits": copy.deepcopy(deck_v1.REMOVED_RULE_HITS),
        "last_v1_package_trace": copy.deepcopy(
            deck_v1.LAST_V1_PACKAGE_TRACE
        ),
        "compliance_block_tag": copy.deepcopy(deck_v1.COMPLIANCE_BLOCK_TAG),
        "trace_surface": copy.deepcopy(trace_snapshot()),
        "c3_state": _c3_state_snapshot(),
    }


def _restore_delegate(
    parent: Any,
    snapshot: dict[str, Any],
    trace_restore: Callable[[Any], None],
    *,
    restore_c3: bool,
) -> None:
    core.restore_parent_state(parent, snapshot["parent"])
    core.INTEGRATED_TRANSACTION = copy.deepcopy(
        snapshot["integrated_transaction"]
    )
    core.INTEGRATED_DUPLICATE_CACHE.clear()
    core.INTEGRATED_DUPLICATE_CACHE.update(
        copy.deepcopy(snapshot["integrated_duplicate_cache"])
    )
    core._DUPLICATE_ORDER[:] = snapshot["integrated_duplicate_order"]
    core.INTEGRATED_TRACE_LOG[:] = copy.deepcopy(
        snapshot["integrated_trace_log"]
    )
    core.INTEGRATED_LATEST_TRACE = copy.deepcopy(
        snapshot["integrated_latest_trace"]
    )
    deck_v1.V1_TRANSACTION = copy.deepcopy(snapshot["v1_transaction"])
    deck_v1.V1_DUPLICATES.clear()
    deck_v1.V1_DUPLICATES.update(copy.deepcopy(snapshot["v1_duplicates"]))
    deck_v1.REMOVED_RULE_HITS = copy.deepcopy(snapshot["removed_rule_hits"])
    deck_v1.LAST_V1_PACKAGE_TRACE = copy.deepcopy(
        snapshot["last_v1_package_trace"]
    )
    deck_v1.COMPLIANCE_BLOCK_TAG = copy.deepcopy(
        snapshot["compliance_block_tag"]
    )
    trace_restore(copy.deepcopy(snapshot["trace_surface"]))
    if restore_c3:
        _restore_c3_state(snapshot["c3_state"])


def _reset_delegate_game_boundary(
    parent: Any,
    trace_restore: Callable[[Any], None],
) -> None:
    """Use canonical reset hooks, then clear the parent's complete state."""
    core.reset_integrated_state()
    deck_v1.reset()
    deck_v1.REMOVED_RULE_HITS = []
    deck_v1.LAST_V1_PACKAGE_TRACE = {
        "public_snapshot_hash": None,
        "context": None,
        "selected_action": [],
        "selected_rule": None,
        "reason_tags": [],
        "added_rule_hits": [],
        "removed_rule_hit_status": "KNOWN",
        "removed_rule_hits": [],
    }
    deck_v1.COMPLIANCE_BLOCK_TAG = None
    current = core.parent_state_snapshot(parent)
    clean = {}
    for name, value in current.items():
        if isinstance(value, dict):
            clean[name] = {}
        elif isinstance(value, list):
            clean[name] = []
        elif name == "pre_turn":
            clean[name] = 0
        elif isinstance(value, bool):
            clean[name] = False
        else:
            clean[name] = None
    core.restore_parent_state(parent, clean)
    trace_restore(
        {
            "LAST_V0_PORT_TRACE": None,
            "LAST_V1_PACKAGE_TRACE": None,
            "LAST_STAGED_POLICY_TRACE": None,
        }
    )


def _merge_trace(
    parent_trace: Any,
    c3_trace: dict[str, Any],
    *,
    applied_action: Any,
    stage: str,
    failure: str | None = None,
) -> dict[str, Any]:
    merged = copy.deepcopy(parent_trace) if isinstance(parent_trace, dict) else {}
    merged.update(copy.deepcopy(c3_trace))
    merged["rule_version"] = RULE_VERSION
    merged["candidate_closure_sha256"] = damage.policy_closure_sha256()
    merged["applied_action"] = applied_action
    merged["transaction_stage"] = stage
    raw_parent_action = c3_trace.get("raw_parent_action")
    value_equal = raw_parent_action == applied_action
    type_equal = type(raw_parent_action) is type(applied_action)
    order_equal = (
        value_equal
        if isinstance(raw_parent_action, (list, tuple))
        and isinstance(applied_action, (list, tuple))
        else value_equal
    )
    merged["action_python_type"] = (
        f"{type(applied_action).__module__}."
        f"{type(applied_action).__qualname__}"
    )
    merged["action_identity"] = {
        "value_equal": value_equal,
        "type_equal": type_equal,
        "order_equal": order_equal,
        "returned_parent_object_unchanged": (
            value_equal and type_equal
        ),
    }
    if failure is not None:
        merged["guard_failure"] = failure
    return merged


def _publish(
    trace_publish: Callable[[dict[str, Any], Any], None],
    trace: dict[str, Any],
    parent_surface: Any,
) -> None:
    global LAST_C3_TRACE
    LAST_C3_TRACE = copy.deepcopy(trace)
    trace_publish(copy.deepcopy(trace), copy.deepcopy(parent_surface))


def _remember_duplicate(fingerprint: str, semantic: tuple[Any, ...]) -> None:
    C3_DUPLICATES[fingerprint] = semantic
    if fingerprint in C3_DUPLICATE_ORDER:
        C3_DUPLICATE_ORDER.remove(fingerprint)
    C3_DUPLICATE_ORDER.append(fingerprint)
    while len(C3_DUPLICATE_ORDER) > _CACHE_LIMIT:
        stale = C3_DUPLICATE_ORDER.pop(0)
        C3_DUPLICATES.pop(stale, None)


def _rebind_basic(
    obs: dict[str, Any], card_id: int, serial: int
) -> list[int] | None:
    current = obs.get("current") if isinstance(obs, dict) else None
    select = obs.get("select") if isinstance(obs, dict) else None
    players = current.get("players") if isinstance(current, dict) else None
    owner = _int(current.get("yourIndex")) if isinstance(current, dict) else None
    options = select.get("option") if isinstance(select, dict) else None
    if (
        not isinstance(players, list)
        or owner not in (0, 1)
        or not isinstance(options, list)
    ):
        return None
    hand = players[owner].get("hand")
    if not isinstance(hand, list):
        return None
    matches = []
    for option_index, option in enumerate(options):
        if not isinstance(option, dict) or _int(option.get("type")) != damage.PLAY:
            continue
        hand_index = _int(option.get("index"))
        if hand_index is None or not 0 <= hand_index < len(hand):
            return None
        card = hand[hand_index]
        if _card_id(card) == card_id and _serial(card) == serial:
            matches.append(option_index)
    return [matches[0]] if len(matches) == 1 else None


def _verify_basic_transaction(
    obs: dict[str, Any], transaction: dict[str, Any]
) -> tuple[bool, str | None]:
    before = transaction.get("public_state")
    after = _public_state(obs)
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False, "TRANSACTION_PUBLIC_STATE_INVALID"
    owner = before["owner"]
    if (
        after["owner"] != owner
        or after["turn"] != before["turn"]
        or after["action_count"] != before["action_count"] + 1
    ):
        return False, "TRANSACTION_TURN_OR_ACTION_COUNT_MISMATCH"
    selected = transaction["selected_basic"]
    expected_hand = list(before["players"][owner]["hand"])
    selected_row = (
        selected["card_id"],
        selected["serial"],
        owner,
    )
    if expected_hand.count(selected_row) != 1:
        return False, "TRANSACTION_SELECTED_HAND_IDENTITY_MISMATCH"
    expected_hand.remove(selected_row)
    if after["players"][owner]["hand"] != sorted(expected_hand):
        return False, "TRANSACTION_HAND_DELTA_MISMATCH"
    if (
        before["players"][owner]["hand_count"] is not None
        and after["players"][owner]["hand_count"]
        != before["players"][owner]["hand_count"] - 1
    ):
        return False, "TRANSACTION_HAND_COUNT_MISMATCH"
    if before["players"][owner]["bench"] != []:
        return False, "TRANSACTION_PRE_BENCH_NOT_EMPTY"
    post_bench = after["players"][owner]["bench"]
    if len(post_bench) != 1:
        return False, "TRANSACTION_BENCH_DELTA_MISMATCH"
    pokemon = post_bench[0]
    if (
        pokemon["id"] != selected["card_id"]
        or pokemon["serial"] != selected["serial"]
        or pokemon["playerIndex"] != owner
        or pokemon["energies"] != []
        or pokemon["energyCards"] != []
        or pokemon["tools"] != []
        or pokemon["preEvolution"] != []
    ):
        return False, "TRANSACTION_BENCH_IDENTITY_MISMATCH"
    if pokemon["appearThisTurn"] is not True:
        return False, "TRANSACTION_APPEAR_THIS_TURN_MISMATCH"

    # Every field other than the exact action-count and Hand->Bench delta must
    # remain byte-for-byte equal in the canonical public model.
    before_other = copy.deepcopy(before)
    after_other = copy.deepcopy(after)
    before_other["action_count"] = after_other["action_count"]
    before_other["players"][owner]["hand"] = after_other["players"][owner][
        "hand"
    ]
    before_other["players"][owner]["hand_count"] = after_other["players"][
        owner
    ]["hand_count"]
    before_other["players"][owner]["bench"] = after_other["players"][owner][
        "bench"
    ]
    if before_other != after_other:
        return False, "TRANSACTION_UNRELATED_PUBLIC_MUTATION"
    return True, None


def _abort_transaction(
    obs: dict[str, Any],
    parent: Any,
    complete_parent: Callable[[dict[str, Any]], Any],
    trace_snapshot: Callable[[], Any],
    trace_restore: Callable[[Any], None],
    trace_publish: Callable[[dict[str, Any], Any], None],
    transaction: dict[str, Any],
    reason: str,
) -> Any:
    global C3_TRANSACTION
    C3_TRANSACTION = None
    C3_DUPLICATES.clear()
    C3_DUPLICATE_ORDER.clear()
    rebound = damage.rebind_semantic_action(
        obs, tuple(transaction["parent_semantic"])
    )
    if rebound is None:
        _restore_delegate(
            parent,
            transaction["pre"],
            trace_restore,
            restore_c3=False,
        )
        rebound = complete_parent(obs)
        parent_surface = trace_snapshot()
        parent_trace = (
            parent_surface.get("LAST_STAGED_POLICY_TRACE")
            if isinstance(parent_surface, dict)
            else None
        )
    else:
        _restore_delegate(
            parent,
            transaction["original_post"],
            trace_restore,
            restore_c3=False,
        )
        parent_surface = transaction["parent_surface"]
        parent_trace = transaction["parent_trace"]
    trace = _merge_trace(
        parent_trace,
        transaction["decision"],
        applied_action=rebound,
        stage="ABORTED",
        failure=reason,
    )
    _publish(trace_publish, trace, parent_surface)
    return rebound


def agent(
    obs: dict[str, Any],
    complete_parent: Callable[[dict[str, Any]], Any],
    *,
    parent: Any,
    trace_snapshot: Callable[[], Any],
    trace_restore: Callable[[Any], None],
    trace_publish: Callable[[dict[str, Any], Any], None],
) -> Any:
    """Run C3 strictly outside the complete inherited delegate."""
    global C3_TRANSACTION, _DECK_BOUNDARY_ARMED
    if (
        isinstance(obs, dict)
        and obs.get("select") is None
        and obs.get("current") is None
    ):
        _reset_delegate_game_boundary(parent, trace_restore)
        reset()
        return exact_deck()

    update_public_ledger(obs)
    fingerprint = _callback_fingerprint(obs)
    transaction = C3_TRANSACTION
    if transaction is not None:
        if fingerprint is not None and fingerprint == transaction["fingerprint"]:
            rebound = _rebind_basic(
                obs,
                transaction["selected_basic"]["card_id"],
                transaction["selected_basic"]["serial"],
            )
            if rebound is None:
                return _abort_transaction(
                    obs,
                    parent,
                    complete_parent,
                    trace_snapshot,
                    trace_restore,
                    trace_publish,
                    transaction,
                    "DUPLICATE_BASIC_REBIND_FAILED",
                )
            trace = _merge_trace(
                transaction["parent_trace"],
                transaction["decision"],
                applied_action=rebound,
                stage="DUPLICATE_REBIND",
            )
            _publish(trace_publish, trace, transaction["parent_surface"])
            return rebound

        select = obs.get("select") if isinstance(obs, dict) else None
        if (
            not isinstance(select, dict)
            or _int(select.get("context")) != damage.MAIN
            or _int(select.get("type")) != 0
        ):
            return _abort_transaction(
                obs,
                parent,
                complete_parent,
                trace_snapshot,
                trace_restore,
                trace_publish,
                transaction,
                "TRANSACTION_EXPECTED_DISTINCT_MAIN",
            )
        verified, failure = _verify_basic_transaction(obs, transaction)
        if not verified:
            return _abort_transaction(
                obs,
                parent,
                complete_parent,
                trace_snapshot,
                trace_restore,
                trace_publish,
                transaction,
                failure or "TRANSACTION_VERIFY_FAILED",
            )
        C3_TRANSACTION = None
        C3_DUPLICATES.clear()
        C3_DUPLICATE_ORDER.clear()
        action = complete_parent(obs)
        fresh_surface = trace_snapshot()
        semantic = damage.semantic_action(obs, action)
        if semantic != tuple(transaction["parent_semantic"]):
            rebound = damage.rebind_semantic_action(
                obs, tuple(transaction["parent_semantic"])
            )
            if rebound is not None:
                _restore_delegate(
                    parent,
                    transaction["original_post"],
                    trace_restore,
                    restore_c3=False,
                )
                action = rebound
                parent_surface = transaction["parent_surface"]
                parent_trace = transaction["parent_trace"]
            else:
                parent_surface = fresh_surface
                parent_trace = (
                    fresh_surface.get("LAST_STAGED_POLICY_TRACE")
                    if isinstance(fresh_surface, dict)
                    else None
                )
            trace = _merge_trace(
                parent_trace,
                transaction["decision"],
                applied_action=action,
                stage="ABORTED_AFTER_REENTRY",
                failure="FULL_POLICY_SEMANTIC_REENTRY_MISMATCH",
            )
            _publish(trace_publish, trace, parent_surface)
            return action
        current_surface = fresh_surface
        current_parent_trace = (
            current_surface.get("LAST_STAGED_POLICY_TRACE")
            if isinstance(current_surface, dict)
            else None
        )
        trace = _merge_trace(
            current_parent_trace,
            transaction["decision"],
            applied_action=action,
            stage="COMPLETED",
        )
        trace["proposed_action"] = list(action)
        _publish(trace_publish, trace, current_surface)
        return action

    pre = _delegate_snapshot(parent, trace_snapshot)
    parent_action = complete_parent(obs)
    post = _delegate_snapshot(parent, trace_snapshot)
    parent_surface = post["trace_surface"]
    parent_trace = (
        parent_surface.get("LAST_STAGED_POLICY_TRACE")
        if isinstance(parent_surface, dict)
        else None
    )
    try:
        decision = damage.evaluate_survival_decision(
            obs, parent_action, copy.deepcopy(PUBLIC_LEDGER)
        )
    except Exception as error:
        _restore_delegate(parent, post, trace_restore, restore_c3=False)
        decision = {
            "schema_version": damage.SCHEMA_VERSION,
            "rule_version": RULE_VERSION,
            "parent_closure_sha256": damage.PARENT_CLOSURE_SHA256,
            "candidate_closure_sha256": damage.policy_closure_sha256(),
            "raw_parent_action": parent_action,
            "proposed_action": parent_action,
            "applied_action": parent_action,
            "guard_class": "UNSUPPORTED_NO_ACTION",
            "guard_failure": f"METRIC_EXCEPTION:{type(error).__name__}",
            "transaction_stage": "NO_ACTION",
            "promotion_removal_context": None,
            "metric_exception": type(error).__name__,
        }
    try:
        parsed_observation = parent.to_observation_class(copy.deepcopy(obs))
        raw_parsed_agree = runtime_model.raw_parsed_agree(
            obs, parsed_observation
        )
    except Exception:
        raw_parsed_agree = False
    if not raw_parsed_agree:
        decision["selected_basic"] = None
        decision["proposed_action"] = copy.deepcopy(parent_action)
        decision["applied_action"] = copy.deepcopy(parent_action)
        decision["guard_class"] = "UNSUPPORTED_NO_ACTION"
        decision["guard_failure"] = "RAW_PARSED_DISAGREEMENT"
        decision["transaction_stage"] = "NO_ACTION"
    if (
        pre.get("integrated_transaction") is not None
        or pre.get("v1_transaction") is not None
        or post.get("integrated_transaction") is not None
        or post.get("v1_transaction") is not None
    ):
        decision["selected_basic"] = None
        decision["proposed_action"] = copy.deepcopy(parent_action)
        decision["applied_action"] = copy.deepcopy(parent_action)
        decision["guard_class"] = "UNSUPPORTED_NO_ACTION"
        decision["guard_failure"] = "PARENT_TRANSACTION_IN_PROGRESS"
        decision["transaction_stage"] = "NO_ACTION"
    selected = decision.get("selected_basic")
    if not isinstance(selected, dict) or decision.get("transaction_stage") != "PROPOSED":
        trace = _merge_trace(
            parent_trace,
            decision,
            applied_action=parent_action,
            stage="NO_ACTION",
        )
        _publish(trace_publish, trace, parent_surface)
        return parent_action

    public_state = _public_state(obs)
    semantic = damage.semantic_action(obs, parent_action)
    if public_state is None or semantic is None:
        _restore_delegate(parent, post, trace_restore, restore_c3=False)
        return parent_action
    proposed = _rebind_basic(obs, selected["card_id"], selected["serial"])
    if proposed is None:
        _restore_delegate(parent, post, trace_restore, restore_c3=False)
        trace = _merge_trace(
            parent_trace,
            decision,
            applied_action=parent_action,
            stage="NO_ACTION",
            failure="INITIAL_BASIC_REBIND_FAILED",
        )
        _publish(trace_publish, trace, parent_surface)
        return parent_action

    _restore_delegate(parent, pre, trace_restore, restore_c3=True)
    C3_TRANSACTION = {
        "decision_id": decision["decision_id"],
        "fingerprint": fingerprint,
        "turn": public_state["turn"],
        "action_count": public_state["action_count"],
        "owner": public_state["owner"],
        "public_state": public_state,
        "selected_basic": copy.deepcopy(selected),
        "parent_semantic": list(semantic),
        "parent_action": copy.deepcopy(parent_action),
        "pre": pre,
        "original_post": post,
        "parent_trace": copy.deepcopy(parent_trace),
        "parent_surface": copy.deepcopy(parent_surface),
        "decision": copy.deepcopy(decision),
    }
    if fingerprint is not None:
        _remember_duplicate(
            fingerprint,
            ("PLAY", selected["card_id"], selected["serial"]),
        )
    trace = _merge_trace(
        parent_trace,
        decision,
        applied_action=proposed,
        stage="ARMED",
    )
    _publish(trace_publish, trace, parent_surface)
    return proposed


__all__ = [
    "C3_DUPLICATES",
    "C3_TRANSACTION",
    "LAST_C3_TRACE",
    "PUBLIC_LEDGER",
    "RULE_VERSION",
    "agent",
    "exact_deck",
    "reset",
    "update_public_ledger",
]
