"""One fail-closed H1 attachment transaction layered over certified fix5 v1."""

from __future__ import annotations

import copy
from math import ceil
from typing import Any

import planner_deck_adaptation_v1 as v1
import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_semantics as semantics


ALAKAZAM = 743
POWERFUL_HAND = 1072
BASIC_PSYCHIC = 5
TELEPATH_PSYCHIC = 19

RULE = "V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO"
TAG_ATTACH_BASIC = "V2_H1_ATTACH_BASIC_PSYCHIC"
TAG_ATTACH_TELEPATH = "V2_H1_ATTACH_TELEPATH_PSYCHIC"
TAG_TELEPATH_EMPTY = "V2_H1_TELEPATH_EMPTY_CHILD"
TAG_ATTACH_VERIFIED = "V2_H1_ATTACH_VERIFIED"
TAG_ATTACK_DISPATCHED = "V2_H1_POWERFUL_HAND_DISPATCHED"
TAG_KO_RESOLVED = "V2_H1_KO_RESOLVED"
TAG_H_FLOOR = "V2_H1_H_FLOOR_BLOCK"
TAG_NON_UNIQUE = "V2_H1_NON_UNIQUE_ROUTE"
TAG_METADATA = "V2_H1_METADATA_UNPROVEN"
TAG_PUBLIC_ABORT = "V2_H1_PUBLIC_MUTATION_ABORT"
TAG_IRREVERSIBLE = "V2_H1_IRREVERSIBLE_ABORT_FAULT"
TAG_DEFER = "V2_DEFER_V1_OWNER"
TAG_FALLBACK = "V2_BASELINE_FALLBACK"


V2_TRANSACTION: dict[str, Any] | None = None
LAST_V2_CONTINUITY_TRACE: dict[str, Any] = {}


def _empty_trace() -> dict[str, Any]:
    return {
        "public_snapshot_hash": None,
        "context": None,
        "selected_action": [],
        "selected_rule": None,
        "stage": "RESET",
        "reason_tags": [],
        "transaction_outcome": "NONE",
        "transaction_abort_reason": None,
        "irreversible_abort_fault": False,
        "H0_attacker_serial": None,
        "H1_alakazam_serial": None,
        "energy_id": None,
        "energy_serial": None,
        "target_serial": None,
        "Hreq": None,
        "start_hand": None,
        "final_hand": None,
        "attach_verified": False,
        "attack_dispatched": False,
        "KO_resolved": False,
        "transaction_started": False,
    }


LAST_V2_CONTINUITY_TRACE = _empty_trace()


def reset() -> None:
    global V2_TRANSACTION, LAST_V2_CONTINUITY_TRACE
    V2_TRANSACTION = None
    LAST_V2_CONTINUITY_TRACE = _empty_trace()


def _context(obs: Any = None, raw: Any = None) -> int | None:
    try:
        if obs is not None and obs.select is not None:
            return int(obs.select.context)
        return int(raw["select"]["context"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _trace(
    *,
    snapshot_hash: str | None,
    context: int | None,
    action: Any,
    rule: str | None,
    stage: str,
    tags: tuple[str, ...] | list[str],
    outcome: str,
    transaction: dict[str, Any] | None = None,
    abort_reason: str | None = None,
    irreversible: bool = False,
    attach_event: bool = False,
    attack_event: bool = False,
    ko_event: bool = False,
    started_event: bool = False,
) -> None:
    global LAST_V2_CONTINUITY_TRACE
    transaction = transaction or {}
    LAST_V2_CONTINUITY_TRACE = {
        "public_snapshot_hash": snapshot_hash,
        "context": context,
        "selected_action": (
            list(action) if isinstance(action, (list, tuple)) else []
        ),
        "selected_rule": rule,
        "stage": stage,
        "reason_tags": list(tags),
        "transaction_outcome": outcome,
        "transaction_abort_reason": abort_reason,
        "irreversible_abort_fault": irreversible,
        "H0_attacker_serial": transaction.get("attacker_serial"),
        "H1_alakazam_serial": transaction.get("h1_serial"),
        "energy_id": transaction.get("energy_id"),
        "energy_serial": transaction.get("energy_serial"),
        "target_serial": transaction.get("target_serial"),
        "Hreq": transaction.get("hreq"),
        "start_hand": transaction.get("start_hand"),
        "final_hand": transaction.get("final_hand"),
        "attach_verified": attach_event,
        "attack_dispatched": attack_event,
        "KO_resolved": ko_event,
        "transaction_started": started_event,
    }


def _policy_snapshot(parent: Any) -> dict[str, Any]:
    return {
        "delegate": v1._delegate_state_snapshot(parent),
        "v1_transaction": copy.deepcopy(v1.V1_TRANSACTION),
        "v1_duplicates": copy.deepcopy(v1.V1_DUPLICATES),
        "removed_rule_hits": copy.deepcopy(v1.REMOVED_RULE_HITS),
        "last_v1_trace": v1.LAST_V1_PACKAGE_TRACE,
        "compliance_block": v1.COMPLIANCE_BLOCK_TAG,
    }


def _restore_policy_snapshot(parent: Any, snapshot: dict[str, Any]) -> None:
    v1._restore_delegate_state(parent, snapshot["delegate"])
    v1.V1_TRANSACTION = copy.deepcopy(snapshot["v1_transaction"])
    v1.V1_DUPLICATES.clear()
    v1.V1_DUPLICATES.update(copy.deepcopy(snapshot["v1_duplicates"]))
    v1.REMOVED_RULE_HITS = copy.deepcopy(snapshot["removed_rule_hits"])
    v1.LAST_V1_PACKAGE_TRACE = snapshot["last_v1_trace"]
    v1.COMPLIANCE_BLOCK_TAG = snapshot["compliance_block"]


def _trace_has_defer_tag(trace: Any) -> bool:
    if not isinstance(trace, dict):
        return True
    tags = trace.get("reason_tags")
    if not isinstance(tags, list):
        return True
    for raw_tag in tags:
        tag = str(raw_tag).upper()
        if (
            "FAULT" in tag
            or "REMOVED" in tag
            or "FILTER" in tag
            or "IRREVERSIBLE" in tag
            or "DUPLICATE" in tag
            or ("TERMINAL" in tag and "NONTERMINAL" not in tag)
        ):
            return True
    return False


def _duplicate_owner(
    snapshot_hash: str | None,
    policy_snapshot: dict[str, Any] | None = None,
    include_duplicate_cache: bool = True,
) -> bool:
    if snapshot_hash is None:
        return False
    if policy_snapshot is None:
        return bool(
            snapshot_hash in v1.V1_DUPLICATES
            or snapshot_hash in core.INTEGRATED_DUPLICATE_CACHE
        )
    delegate = policy_snapshot["delegate"]
    return bool(
        snapshot_hash in policy_snapshot["v1_duplicates"]
        or snapshot_hash in delegate["duplicate_cache"]
    )


def _parent_duplicate_owner(
    parent: Any,
    obs: Any,
    obs_dict: dict,
) -> bool:
    try:
        decision_signature = parent._decision_signature(obs, obs_dict)
        decision_duplicate = bool(
            parent._last_decision_signature == decision_signature
            and parent._last_decision_action is not None
        )
        raw_signature = parent._two_prize_freeze_raw(obs_dict)
        prize_duplicate = (
            parent._exact_prize_lane_duplicate_action(raw_signature)
            is not None
        )
        return decision_duplicate or prize_duplicate
    except Exception:
        return False


def _owner_active(
    parent: Any,
    *,
    snapshot_hash: str | None,
    policy_snapshot: dict[str, Any] | None = None,
    include_duplicate_cache: bool = True,
) -> bool:
    if policy_snapshot is None:
        parent_state = core.parent_state_snapshot(parent)
        return bool(
            v1.V1_TRANSACTION is not None
            or core.INTEGRATED_TRANSACTION is not None
            or core.parent_owner_active(parent_state)
            or (
                include_duplicate_cache
                and _duplicate_owner(snapshot_hash)
            )
            or v1.LAST_V1_PACKAGE_TRACE.get("selected_rule") is not None
            or _trace_has_defer_tag(v1.LAST_V1_PACKAGE_TRACE)
        )
    delegate = policy_snapshot["delegate"]
    trace = policy_snapshot["last_v1_trace"]
    return bool(
        policy_snapshot["v1_transaction"] is not None
        or delegate["transaction"] is not None
        or core.parent_owner_active(delegate["parent"])
        or (
            include_duplicate_cache
            and _duplicate_owner(snapshot_hash, policy_snapshot)
        )
        or not isinstance(trace, dict)
        or trace.get("selected_rule") is not None
        or _trace_has_defer_tag(trace)
    )


def _metadata_shape_is_exact(data: Any) -> bool:
    return bool(
        data is not None
        and set(vars(data)) == {
            "cardId",
            "name",
            "cardType",
            "retreatCost",
            "hp",
            "weakness",
            "resistance",
            "energyType",
            "basic",
            "stage1",
            "stage2",
            "ex",
            "megaEx",
            "tera",
            "aceSpec",
            "evolvesFrom",
            "skills",
            "attacks",
        }
    )


def _energy_metadata_is_exact(parent: Any, card_id: int) -> bool:
    data = parent.card_table.get(card_id)
    if not _metadata_shape_is_exact(data):
        return False
    fixed = (
        data.cardId,
        data.name,
        int(data.cardType),
        data.retreatCost,
        data.hp,
        data.weakness,
        data.resistance,
        int(data.energyType),
        data.basic,
        data.stage1,
        data.stage2,
        data.ex,
        data.megaEx,
        data.tera,
        data.aceSpec,
        data.evolvesFrom,
        tuple(data.attacks or ()),
    )
    if card_id == BASIC_PSYCHIC:
        return bool(
            fixed
            == (
                BASIC_PSYCHIC,
                "Basic {P} Energy",
                int(parent.CardType.BASIC_ENERGY),
                0,
                0,
                None,
                None,
                int(parent.EnergyType.PSYCHIC),
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                None,
                (),
            )
            and data.skills == []
        )
    if card_id != TELEPATH_PSYCHIC or len(data.skills or ()) != 1:
        return False
    skill = data.skills[0]
    return bool(
        fixed
        == (
            TELEPATH_PSYCHIC,
            "Telepath Psychic Energy",
            int(parent.CardType.SPECIAL_ENERGY),
            0,
            0,
            None,
            None,
            int(parent.EnergyType.PSYCHIC),
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            None,
            (),
        )
        and set(vars(skill)) == {"name", "text"}
        and skill.name == "Telepath Psychic Energy"
        and skill.text
        == (
            "As long as this card is attached to a Pokémon, it provides {P} "
            "Energy.\nWhen you attach this card from your hand to a {P} "
            "Pokémon, search your deck for up to 2 Basic {P} Pokémon and put "
            "them onto your Bench. Then, shuffle your deck."
        )
    )


def _main_public(parent: Any, obs: Any) -> dict[str, Any] | None:
    select = getattr(obs, "select", None)
    state = getattr(obs, "current", None)
    if select is None or state is None:
        return None
    try:
        exact_type = int(select.type) == 0
    except (TypeError, ValueError):
        return None
    if (
        not exact_type
        or select.context != parent.SelectContext.MAIN
        or type(select.minCount) is not int
        or select.minCount != 1
        or type(select.maxCount) is not int
        or select.maxCount != 1
        or type(select.remainDamageCounter) is not int
        or select.remainDamageCounter != 0
        or type(select.remainEnergyCost) is not int
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or state.result != -1
        or state.turn < 2
        or v1._option_census(parent, obs) is None
    ):
        return None
    return v1._public_state(parent, obs)


def _expected_target_fingerprint(
    start_fingerprint: tuple[Any, ...],
    energy_row: tuple[int, int, int],
    psychic: int,
) -> tuple[Any, ...] | None:
    if not isinstance(start_fingerprint, tuple) or len(start_fingerprint) != 10:
        return None
    result = list(start_fingerprint)
    units = result[6]
    cards = result[7]
    if not isinstance(units, tuple) or not isinstance(cards, tuple):
        return None
    result[6] = units + (psychic,)
    result[7] = cards + (energy_row,)
    return tuple(result)


def _candidate(
    parent: Any,
    obs: Any,
    action: Any,
    snapshot: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    public = _main_public(parent, obs)
    if public is None:
        return None, None
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    attack_index = v1._attack_index(parent, obs)
    if (
        not isinstance(action, list)
        or len(action) != 1
        or attack_index is None
        or action[0] != attack_index
        or not model.action_is_valid(obs, action)
        or not v1._v0_current_ko(parent, obs, action)
    ):
        return None, None
    if (
        v1._current_ko_is_terminal(parent, obs)
        or not theirs.bench
        or public["energy_attached"] is not False
    ):
        return None, None
    if not v1._ready_cost_environment_exact(parent, obs.current):
        return None, TAG_METADATA
    target = theirs.active[0]
    hreq = ceil(target.hp / 20)
    if mine.handCount - 1 < hreq:
        return None, TAG_H_FLOOR

    bench_rows = [
        (index, pokemon)
        for index, pokemon in enumerate(mine.bench)
        if pokemon.id == ALAKAZAM
    ]
    if len(bench_rows) != 1:
        return None, TAG_NON_UNIQUE
    bench_index, h1 = bench_rows[0]
    attack = parent.attack_table.get(POWERFUL_HAND)
    available = semantics.energy_units(parent, h1)
    if (
        not parent._two_prize_powerful_hand_metadata_is_exact()
        or not parent._bridge_pokemon_is_publicly_complete(h1, owner)
        or not parent._two_prize_alakazam_lineage_is_complete(h1, owner)
        or attack is None
        or available is None
        or semantics.missing_energy(parent, available, attack.energies)
        != (int(parent.EnergyType.PSYCHIC),)
    ):
        return None, TAG_METADATA

    energy_rows = []
    for hand_index, card in enumerate(mine.hand):
        if card.id not in (BASIC_PSYCHIC, TELEPATH_PSYCHIC):
            continue
        if (
            not _energy_metadata_is_exact(parent, card.id)
            or v1._card_row(card) != (card.id, card.serial, owner)
        ):
            return None, TAG_METADATA
        virtual = copy.deepcopy(h1)
        virtual.energies.append(parent.EnergyType.PSYCHIC)
        virtual.energyCards.append(copy.deepcopy(card))
        virtual_units = semantics.energy_units(parent, virtual)
        if (
            virtual_units is not None
            and not semantics.missing_energy(
                parent, virtual_units, attack.energies
            )
            and parent._two_prize_alakazam_is_ready(virtual, owner)
        ):
            energy_rows.append((hand_index, card))
    if len(energy_rows) != 1:
        return None, TAG_NON_UNIQUE
    hand_index, energy = energy_rows[0]

    route_options = []
    for option_index, option in enumerate(obs.select.option):
        if not v1._exact_option(
            option,
            parent.OptionType.ATTACH,
            area=parent.AreaType.HAND,
            index=hand_index,
            inPlayArea=parent.AreaType.BENCH,
            inPlayIndex=bench_index,
        ):
            continue
        key = runtime_model.stable_option_key(parent, obs, option)
        if key is None:
            return None, TAG_METADATA
        route_options.append((option_index, key))
    if len(route_options) != 1:
        return None, TAG_NON_UNIQUE
    option_index, attach_key = route_options[0]
    attack_key = runtime_model.stable_option_key(
        parent, obs, obs.select.option[attack_index]
    )
    if attack_key is None:
        return None, TAG_METADATA

    protected = (
        parent._bridge_pokemon_component_serials(mine.active[0])
        + parent._bridge_pokemon_component_serials(h1)
        + parent._bridge_pokemon_component_serials(target)
        + [energy.serial]
    )
    if not parent._bridge_protected_serials_are_unique(
        obs.current, protected
    ):
        return None, TAG_METADATA
    expected_h1 = _expected_target_fingerprint(
        parent._bridge_pokemon_fingerprint(h1),
        (energy.id, energy.serial, owner),
        int(parent.EnergyType.PSYCHIC),
    )
    if expected_h1 is None:
        return None, TAG_METADATA

    return {
        "rule": RULE,
        "owner": owner,
        "turn": obs.current.turn,
        "stage": (
            "await_telepath_child"
            if energy.id == TELEPATH_PSYCHIC
            else "await_attach_main"
        ),
        "start_snapshot_hash": snapshot.sha256,
        "start_logs": _logs_fingerprint(obs.logs),
        "start_public": copy.deepcopy(public),
        "v1_attack_action_object": action,
        "attack_key": attack_key,
        "attacker_id": mine.active[0].id,
        "attacker_serial": mine.active[0].serial,
        "attacker_fingerprint": parent._bridge_pokemon_fingerprint(
            mine.active[0]
        ),
        "target_id": target.id,
        "target_serial": target.serial,
        "target_hp": target.hp,
        "target_fingerprint": parent._bridge_pokemon_fingerprint(target),
        "hreq": hreq,
        "start_hand": mine.handCount,
        "final_hand": None,
        "energy_id": energy.id,
        "energy_serial": energy.serial,
        "energy_owner": owner,
        "energy_row": (energy.id, energy.serial, owner),
        "energy_card": copy.deepcopy(energy),
        "energy_hand_index": hand_index,
        "h1_bench_index": bench_index,
        "h1_serial": h1.serial,
        "h1_fingerprint": parent._bridge_pokemon_fingerprint(h1),
        "expected_h1_fingerprint": expected_h1,
        "attach_key": attach_key,
        "protected_serials": tuple(protected),
        "attach_verified_status": False,
        "attack_dispatched_status": False,
        "ko_resolved_status": False,
    }, None


def _logs_fingerprint(logs: Any) -> tuple[Any, ...] | None:
    if not isinstance(logs, list):
        return None
    rows = []
    for log in logs:
        if not hasattr(log, "__dict__"):
            return None
        rows.append(
            tuple(
                (key, model.enum_int(value))
                for key, value in sorted(vars(log).items())
            )
        )
    return tuple(rows)


def _rebind(
    parent: Any,
    obs: Any,
    key: tuple[Any, ...],
) -> list[int] | None:
    action = model.rebind_option_keys(parent, obs, (key,))
    return action if model.action_is_valid(obs, action) else None


def _find_h1(parent: Any, obs: Any, transaction: dict[str, Any]) -> Any:
    owner = transaction["owner"]
    mine = obs.current.players[owner]
    index = transaction["h1_bench_index"]
    if not 0 <= index < len(mine.bench):
        return None
    pokemon = mine.bench[index]
    return pokemon if pokemon.serial == transaction["h1_serial"] else None


def _attach_delta_exact(
    parent: Any,
    obs: Any,
    transaction: dict[str, Any],
) -> dict[str, Any] | None:
    current = v1._public_state(parent, obs)
    start = transaction["start_public"]
    if current is None:
        return None
    unchanged = (
        "turn",
        "first_player",
        "result",
        "supporter_played",
        "stadium_played",
        "retreated",
        "own_deck",
        "opponent_deck",
        "own_bench_max",
        "opponent_bench_max",
        "own_status",
        "opponent_status",
        "own_prize",
        "opponent_prize",
        "opponent_hand_count",
        "own_discard",
        "opponent_discard",
        "stadium",
        "own_active",
        "opponent_active",
        "opponent_bench",
    )
    hand_index = transaction["energy_hand_index"]
    expected_hand = (
        start["own_hand"][:hand_index]
        + start["own_hand"][hand_index + 1 :]
    )
    expected_bench = list(start["own_bench"])
    bench_index = transaction["h1_bench_index"]
    if not 0 <= bench_index < len(expected_bench):
        return None
    expected_bench[bench_index] = transaction["expected_h1_fingerprint"]
    h1 = _find_h1(parent, obs, transaction)
    if (
        obs.current.yourIndex != transaction["owner"]
        or current["turn"] != transaction["turn"]
        or any(current[key] != start[key] for key in unchanged)
        or current["action_count"] != start["action_count"] + 1
        or start["energy_attached"] is not False
        or current["energy_attached"] is not True
        or current["own_hand_count"] != start["own_hand_count"] - 1
        or current["own_hand"] != expected_hand
        or current["own_bench"] != tuple(expected_bench)
        or h1 is None
        or parent._bridge_pokemon_fingerprint(h1)
        != transaction["expected_h1_fingerprint"]
        or not parent._bridge_protected_serials_are_unique(
            obs.current, transaction["protected_serials"]
        )
        or current["own_hand_count"] < transaction["hreq"]
        or len(obs.logs) != 1
        or not v1._log_is_exact(
            obs.logs[0],
            11,
            {
                "playerIndex": transaction["owner"],
                "cardId": transaction["energy_id"],
                "serial": transaction["energy_serial"],
                "cardIdTarget": ALAKAZAM,
                "serialTarget": transaction["h1_serial"],
            },
        )
    ):
        return None
    units = semantics.energy_units(parent, h1)
    attack = parent.attack_table.get(POWERFUL_HAND)
    if (
        units is None
        or attack is None
        or semantics.missing_energy(parent, units, attack.energies)
        or not parent._two_prize_alakazam_is_ready(
            h1, transaction["owner"]
        )
    ):
        return None
    return current


def _search_card_is_exact(parent: Any, card: Any, owner: int) -> bool:
    row = v1._card_row(card)
    data = parent.card_table.get(getattr(card, "id", None))
    return bool(
        row is not None
        and row[2] == owner
        and _metadata_shape_is_exact(data)
        and data.cardId == card.id
        and data.cardType == parent.CardType.POKEMON
        and data.basic is True
        and data.stage1 is False
        and data.stage2 is False
        and int(data.energyType) == int(parent.EnergyType.PSYCHIC)
    )


def _telepath_child_is_exact(
    parent: Any,
    obs: Any,
    transaction: dict[str, Any],
) -> dict[str, Any] | None:
    select = obs.select
    if select is None:
        return None
    try:
        exact_type = int(select.type) == 1
    except (TypeError, ValueError):
        return None
    context_rows = [
        v1._card_row(card)
        for card in (select.effect, select.contextCard)
        if card is not None
    ]
    current = _attach_delta_exact(parent, obs, transaction)
    owner = transaction["owner"]
    mine = obs.current.players[owner]
    if (
        current is None
        or not exact_type
        or select.context != parent.SelectContext.TO_BENCH
        or type(select.minCount) is not int
        or select.minCount != 0
        or type(select.maxCount) is not int
        or not 0 <= select.maxCount <= 2
        or type(select.remainDamageCounter) is not int
        or select.remainDamageCounter != 0
        or type(select.remainEnergyCost) is not int
        or select.remainEnergyCost != 0
        or not isinstance(select.deck, list)
        or obs.current.looking is not None
        or not context_rows
        or any(row != transaction["energy_row"] for row in context_rows)
        or v1._option_census(parent, obs) is None
        or len(select.deck) != len(select.option)
        or select.maxCount
        != min(
            2,
            max(0, mine.benchMax - len(mine.bench)),
            len(select.option),
        )
    ):
        return None
    serials = []
    for index, (card, option) in enumerate(
        zip(select.deck, select.option)
    ):
        if (
            not _search_card_is_exact(parent, card, owner)
            or not v1._exact_option(
                option,
                parent.OptionType.CARD,
                area=parent.AreaType.DECK,
                index=index,
                playerIndex=owner,
            )
            or core._option_card(parent, obs, option) is not card
        ):
            return None
        serials.append(card.serial)
    public_serials = parent._bridge_public_serials(obs.current)
    if (
        len(serials) != len(set(serials))
        or any(serial in public_serials for serial in serials)
    ):
        return None
    return current


def _public_exact(left: Any, right: Any) -> bool:
    return isinstance(left, dict) and isinstance(right, dict) and left == right


def _pre_attack_exact(
    parent: Any,
    obs: Any,
    transaction: dict[str, Any],
    expected_public: dict[str, Any],
) -> Any:
    public = _main_public(parent, obs)
    owner = transaction["owner"]
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    if (
        public is None
        or not _public_exact(public, expected_public)
        or obs.current.turn != transaction["turn"]
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or mine.active[0].serial != transaction["attacker_serial"]
        or theirs.active[0].serial != transaction["target_serial"]
        or parent._bridge_pokemon_fingerprint(mine.active[0])
        != transaction["attacker_fingerprint"]
        or parent._bridge_pokemon_fingerprint(theirs.active[0])
        != transaction["target_fingerprint"]
        or mine.handCount < transaction["hreq"]
        or not v1._powerful_hand_ko(parent, obs, mine.handCount)
        or v1._current_ko_is_terminal(parent, obs)
    ):
        return None
    return runtime_model.public_snapshot(parent, obs)


def _fault_action(parent: Any, obs: Any) -> list[int] | None:
    select = getattr(obs, "select", None)
    if select is None:
        return None
    options = getattr(select, "option", None)
    minimum = getattr(select, "minCount", None)
    maximum = getattr(select, "maxCount", None)
    if (
        not isinstance(options, list)
        or type(minimum) is not int
        or type(maximum) is not int
        or not 0 <= minimum <= maximum <= len(options)
    ):
        return None
    action = list(range(minimum))
    return action if model.action_is_valid(obs, action) else None


def _abort(
    parent: Any,
    obs_dict: dict,
    obs: Any,
    transaction: dict[str, Any],
    reason: str,
    snapshot_hash: str | None = None,
) -> list[int]:
    global V2_TRANSACTION
    action = _fault_action(parent, obs)
    if action is None:
        action = v1._certify_raw_action(
            obs_dict, None, prefer_nonempty=False
        )
    if action is None:
        V2_TRANSACTION = None
        _trace(
            snapshot_hash=snapshot_hash,
            context=_context(obs, obs_dict),
            action=[],
            rule=RULE,
            stage="FAULT_ABORT",
            tags=(TAG_PUBLIC_ABORT, TAG_IRREVERSIBLE),
            outcome="FAULT_ABORT",
            transaction=transaction,
            abort_reason=reason,
            irreversible=True,
        )
        raise v1.UnrecoverableObservationFault(
            "V2_UNRECOVERABLE_IRREVERSIBLE_FAULT_ACTION"
        )
    V2_TRANSACTION = None
    _trace(
        snapshot_hash=snapshot_hash,
        context=_context(obs, obs_dict),
        action=action,
        rule=RULE,
        stage="FAULT_ABORT",
        tags=(TAG_PUBLIC_ABORT, TAG_IRREVERSIBLE),
        outcome="FAULT_ABORT",
        transaction=transaction,
        abort_reason=reason,
        irreversible=True,
    )
    return action


def _dispatch_attack(
    parent: Any,
    v1_agent: Any,
    obs_dict: dict,
    obs: Any,
    transaction: dict[str, Any],
    expected_public: dict[str, Any],
) -> list[int]:
    global V2_TRANSACTION
    snapshot = _pre_attack_exact(
        parent, obs, transaction, expected_public
    )
    if snapshot is None or _owner_active(
        parent, snapshot_hash=getattr(snapshot, "sha256", None)
    ):
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            "PRE_ATTACK_PUBLIC_OR_OWNER_MISMATCH",
            getattr(snapshot, "sha256", None),
        )

    probe_pre = _policy_snapshot(parent)
    try:
        action = v1_agent(obs_dict)
        retained_snapshot = runtime_model.public_snapshot(parent, obs)
    except Exception:
        _restore_policy_snapshot(parent, probe_pre)
        raise
    retained_hash = getattr(retained_snapshot, "sha256", None)
    if (
        retained_snapshot is None
        or _owner_active(
            parent,
            snapshot_hash=retained_hash,
        )
        or _duplicate_owner(snapshot.sha256)
        or _parent_duplicate_owner(parent, obs, obs_dict)
        or not isinstance(action, list)
        or len(action) != 1
        or not model.action_is_valid(obs, action)
    ):
        _restore_policy_snapshot(parent, probe_pre)
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            "V1_ATTACK_OWNER_OR_ACTION_MISMATCH",
            retained_hash,
        )
    option = obs.select.option[action[0]]
    action_key = runtime_model.stable_option_key(parent, obs, option)
    if (
        option.type != parent.OptionType.ATTACK
        or option.attackId != POWERFUL_HAND
        or action_key != transaction["attack_key"]
        or v1._attack_index(parent, obs) != action[0]
    ):
        _restore_policy_snapshot(parent, probe_pre)
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            "V1_POWERFUL_HAND_MISMATCH",
            retained_hash,
        )
    proof_action = v1._arm_attack_resolution(parent, obs, transaction)
    if (
        proof_action != action
        or not isinstance(transaction.get("attack_resolution"), dict)
    ):
        _restore_policy_snapshot(parent, probe_pre)
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            "ATTACK_RESOLUTION_PROOF_FAILED",
            retained_hash,
        )
    transaction["stage"] = "await_attack_resolution"
    transaction["attack_snapshot_hash"] = retained_hash
    transaction["attack_logs"] = _logs_fingerprint(obs.logs)
    transaction["attack_dispatched_status"] = True
    transaction["final_hand"] = obs.current.players[
        transaction["owner"]
    ].handCount
    V2_TRANSACTION = transaction
    tags = [TAG_ATTACK_DISPATCHED]
    _trace(
        snapshot_hash=retained_hash,
        context=int(obs.select.context),
        action=action,
        rule=RULE,
        stage="ATTACK_DISPATCHED",
        tags=tags,
        outcome="ACTIVE",
        transaction=transaction,
        attack_event=True,
    )
    return action


def _advance_impl(
    parent: Any,
    v1_agent: Any,
    obs_dict: dict,
    transaction: dict[str, Any],
) -> list[int]:
    global V2_TRANSACTION
    try:
        obs = parent.to_observation_class(obs_dict)
    except Exception:
        action = v1._certify_raw_action(
            obs_dict, None, prefer_nonempty=False
        )
        V2_TRANSACTION = None
        _trace(
            snapshot_hash=None,
            context=_context(None, obs_dict),
            action=action,
            rule=RULE,
            stage="FAULT_ABORT",
            tags=(TAG_PUBLIC_ABORT, TAG_IRREVERSIBLE),
            outcome="FAULT_ABORT",
            transaction=transaction,
            abort_reason="REPARSE_FAILURE",
            irreversible=True,
        )
        if action is None:
            raise v1.UnrecoverableObservationFault(
                "V2_UNRECOVERABLE_REPARSE_FAILURE"
            )
        return action
    if (
        obs.select is None
        or obs.current is None
        or not runtime_model.raw_parsed_agree(obs_dict, obs)
    ):
        return _abort(
            parent, obs_dict, obs, transaction, "RAW_PARSED_MISMATCH"
        )
    snapshot = runtime_model.public_snapshot(parent, obs)
    snapshot_hash = getattr(snapshot, "sha256", None)
    if (
        v1.V1_TRANSACTION is not None
        or core.INTEGRATED_TRANSACTION is not None
        or core.parent_owner_active(core.parent_state_snapshot(parent))
        or v1.LAST_V1_PACKAGE_TRACE.get("selected_rule") is not None
        or _trace_has_defer_tag(v1.LAST_V1_PACKAGE_TRACE)
    ):
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            "NEW_V1_OWNER_DURING_V2",
            snapshot_hash,
        )

    stage = transaction["stage"]
    if (
        stage in ("await_attach_main", "await_telepath_child")
        and snapshot_hash == transaction["start_snapshot_hash"]
        and _logs_fingerprint(obs.logs) == transaction["start_logs"]
    ):
        duplicate_public = _main_public(parent, obs)
        if not _public_exact(
            duplicate_public, transaction.get("start_public")
        ):
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "ATTACH_DUPLICATE_PUBLIC_MISMATCH",
                snapshot_hash,
            )
        action = _rebind(parent, obs, transaction["attach_key"])
        if action is None:
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "ATTACH_DUPLICATE_REBIND_FAILED",
                snapshot_hash,
            )
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=action,
            rule=RULE,
            stage="ATTACH_DUPLICATE_REBOUND",
            tags=(
                TAG_ATTACH_TELEPATH
                if transaction["energy_id"] == TELEPATH_PSYCHIC
                else TAG_ATTACH_BASIC,
            ),
            outcome="ACTIVE",
            transaction=transaction,
        )
        return action

    if stage == "await_telepath_child":
        current = _telepath_child_is_exact(parent, obs, transaction)
        if (
            snapshot_hash is None
            or current is None
            or not model.action_is_valid(obs, [])
        ):
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "TELEPATH_CHILD_MISMATCH",
                snapshot_hash,
            )
        transaction["post_attach_public"] = copy.deepcopy(current)
        transaction["telepath_child_snapshot_hash"] = snapshot_hash
        transaction["telepath_child_logs"] = _logs_fingerprint(obs.logs)
        transaction["attach_verified_status"] = True
        transaction["final_hand"] = current["own_hand_count"]
        transaction["stage"] = "await_telepath_main"
        V2_TRANSACTION = transaction
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=[],
            rule=RULE,
            stage="TELEPATH_EMPTY_CHILD",
            tags=(TAG_TELEPATH_EMPTY, TAG_ATTACH_VERIFIED),
            outcome="ACTIVE",
            transaction=transaction,
            attach_event=True,
        )
        return []

    if stage == "await_telepath_main":
        if (
            snapshot_hash
            == transaction.get("telepath_child_snapshot_hash")
            and _logs_fingerprint(obs.logs)
            == transaction.get("telepath_child_logs")
        ):
            duplicate_public = _telepath_child_is_exact(
                parent, obs, transaction
            )
            if (
                not _public_exact(
                    duplicate_public,
                    transaction.get("post_attach_public"),
                )
                or not model.action_is_valid(obs, [])
            ):
                return _abort(
                    parent,
                    obs_dict,
                    obs,
                    transaction,
                    "TELEPATH_CHILD_DUPLICATE_INVALID",
                    snapshot_hash,
                )
            _trace(
                snapshot_hash=snapshot_hash,
                context=int(obs.select.context),
                action=[],
                rule=RULE,
                stage="TELEPATH_EMPTY_CHILD_DUPLICATE_REBOUND",
                tags=(TAG_TELEPATH_EMPTY, TAG_ATTACH_VERIFIED),
                outcome="ACTIVE",
                transaction=transaction,
            )
            return []
        public = _main_public(parent, obs)
        if (
            public is None
            or not _public_exact(
                public, transaction.get("post_attach_public")
            )
            or public["own_deck"]
            != transaction["start_public"]["own_deck"]
        ):
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "POST_TELEPATH_PUBLIC_MUTATION",
                snapshot_hash,
            )
        return _dispatch_attack(
            parent,
            v1_agent,
            obs_dict,
            obs,
            transaction,
            public,
        )

    if stage == "await_attach_main":
        public = _main_public(parent, obs)
        current = _attach_delta_exact(parent, obs, transaction)
        if public is None or current is None or public != current:
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "BASIC_ATTACH_DELTA_MISMATCH",
                snapshot_hash,
            )
        transaction["post_attach_public"] = copy.deepcopy(current)
        transaction["attach_verified_status"] = True
        transaction["final_hand"] = current["own_hand_count"]
        action = _dispatch_attack(
            parent,
            v1_agent,
            obs_dict,
            obs,
            transaction,
            current,
        )
        if V2_TRANSACTION is not None:
            LAST_V2_CONTINUITY_TRACE["reason_tags"].insert(
                0, TAG_ATTACH_VERIFIED
            )
            LAST_V2_CONTINUITY_TRACE["attach_verified"] = True
        return action

    if stage == "await_attack_resolution":
        if (
            snapshot_hash == transaction.get("attack_snapshot_hash")
            and _logs_fingerprint(obs.logs)
            == transaction.get("attack_logs")
        ):
            duplicate_snapshot = _pre_attack_exact(
                parent,
                obs,
                transaction,
                transaction.get("post_attach_public"),
            )
            if duplicate_snapshot is None:
                return _abort(
                    parent,
                    obs_dict,
                    obs,
                    transaction,
                    "ATTACK_DUPLICATE_PUBLIC_MISMATCH",
                    snapshot_hash,
                )
            action = _rebind(parent, obs, transaction["attack_key"])
            if action is None:
                return _abort(
                    parent,
                    obs_dict,
                    obs,
                    transaction,
                    "ATTACK_DUPLICATE_REBIND_FAILED",
                    snapshot_hash,
                )
            _trace(
                snapshot_hash=snapshot_hash,
                context=int(obs.select.context),
                action=action,
                rule=RULE,
                stage="ATTACK_DUPLICATE_REBOUND",
                tags=(),
                outcome="ACTIVE",
                transaction=transaction,
            )
            return action
        if not v1._exact_attack_resolution(parent, obs, transaction):
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "EXACT_KO_RESOLUTION_MISMATCH",
                snapshot_hash,
            )
        transaction["ko_resolved_status"] = True
        transaction["stage"] = "complete"
        completion_pre = _policy_snapshot(parent)
        V2_TRANSACTION = None
        try:
            action = v1_agent(obs_dict)
        except Exception:
            _restore_policy_snapshot(parent, completion_pre)
            return _abort(
                parent,
                obs_dict,
                obs,
                transaction,
                "COMPLETION_DELEGATE_EXCEPTION",
                snapshot_hash,
            )
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=action,
            rule=RULE,
            stage="KO_RESOLVED",
            tags=(TAG_KO_RESOLVED,),
            outcome="COMPLETE",
            transaction=transaction,
            ko_event=True,
        )
        return action

    return _abort(
        parent,
        obs_dict,
        obs,
        transaction,
        "UNKNOWN_V2_STAGE",
        snapshot_hash,
    )


def _post_attach_exception_abort(
    parent: Any,
    obs_dict: dict,
    transaction: dict[str, Any],
    policy_pre: dict[str, Any] | None,
    reason: str,
) -> list[int]:
    global V2_TRANSACTION
    if policy_pre is not None:
        try:
            _restore_policy_snapshot(parent, policy_pre)
        except Exception:
            pass
    obs = None
    snapshot_hash = None
    try:
        obs = parent.to_observation_class(obs_dict)
        snapshot = runtime_model.public_snapshot(parent, obs)
        snapshot_hash = getattr(snapshot, "sha256", None)
    except Exception:
        pass
    if obs is not None:
        return _abort(
            parent,
            obs_dict,
            obs,
            transaction,
            reason,
            snapshot_hash,
        )
    action = v1._certify_raw_action(
        obs_dict, None, prefer_nonempty=False
    )
    V2_TRANSACTION = None
    _trace(
        snapshot_hash=None,
        context=_context(None, obs_dict),
        action=action,
        rule=RULE,
        stage="FAULT_ABORT",
        tags=(TAG_PUBLIC_ABORT, TAG_IRREVERSIBLE),
        outcome="FAULT_ABORT",
        transaction=transaction,
        abort_reason=reason,
        irreversible=True,
    )
    if action is None:
        raise v1.UnrecoverableObservationFault(
            "V2_UNRECOVERABLE_POST_ATTACH_EXCEPTION"
        )
    return action


def _advance(
    parent: Any,
    v1_agent: Any,
    obs_dict: dict,
    transaction: dict[str, Any],
) -> list[int]:
    policy_pre = None
    try:
        policy_pre = _policy_snapshot(parent)
        return _advance_impl(parent, v1_agent, obs_dict, transaction)
    except v1.UnrecoverableObservationFault:
        if V2_TRANSACTION is None:
            raise
        return _post_attach_exception_abort(
            parent,
            obs_dict,
            transaction,
            policy_pre,
            "POST_ATTACH_UNRECOVERABLE",
        )
    except Exception:
        return _post_attach_exception_abort(
            parent,
            obs_dict,
            transaction,
            policy_pre,
            "POST_ATTACH_EXCEPTION",
        )


def agent(parent: Any, v1_agent: Any, obs_dict: dict) -> list[int]:
    """Delegate once when idle; own only the certified attach-to-KO chain."""
    global V2_TRANSACTION
    if V2_TRANSACTION is not None:
        return _advance(parent, v1_agent, obs_dict, V2_TRANSACTION)

    policy_pre = _policy_snapshot(parent)
    pre_obs = None
    pre_snapshot = None
    try:
        pre_obs = parent.to_observation_class(obs_dict)
        if (
            pre_obs.select is not None
            and pre_obs.current is not None
            and runtime_model.raw_parsed_agree(obs_dict, pre_obs)
        ):
            pre_snapshot = runtime_model.public_snapshot(parent, pre_obs)
    except Exception:
        pre_obs = None
    pre_snapshot_hash = getattr(pre_snapshot, "sha256", None)
    pre_parent_duplicate = bool(
        pre_obs is not None
        and pre_snapshot is not None
        and _parent_duplicate_owner(parent, pre_obs, obs_dict)
    )

    action = v1_agent(obs_dict)
    obs = None
    snapshot = None
    try:
        obs = parent.to_observation_class(obs_dict)
        if (
            obs.select is not None
            and obs.current is not None
            and runtime_model.raw_parsed_agree(obs_dict, obs)
        ):
            snapshot = runtime_model.public_snapshot(parent, obs)
    except Exception:
        obs = None
    snapshot_hash = getattr(snapshot, "sha256", None)
    post_parent_duplicate = bool(
        obs is not None
        and snapshot is not None
        and _parent_duplicate_owner(parent, obs, obs_dict)
    )

    if (
        pre_obs is None
        or pre_snapshot is None
        or obs is None
        or snapshot is None
        or _owner_active(
            parent,
            snapshot_hash=pre_snapshot_hash,
            policy_snapshot=policy_pre,
        )
        or _owner_active(
            parent,
            snapshot_hash=snapshot_hash,
        )
        or _duplicate_owner(pre_snapshot_hash)
        or pre_parent_duplicate
        or post_parent_duplicate
    ):
        _trace(
            snapshot_hash=snapshot_hash,
            context=_context(obs, obs_dict),
            action=action,
            rule=None,
            stage="BASELINE_FALLBACK",
            tags=(TAG_DEFER, TAG_FALLBACK),
            outcome="NONE",
        )
        return action

    transaction, block_tag = _candidate(parent, obs, action, snapshot)
    if transaction is None:
        tags = (
            (block_tag, TAG_FALLBACK)
            if block_tag is not None
            else (TAG_FALLBACK,)
        )
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=action,
            rule=None,
            stage="BASELINE_FALLBACK",
            tags=tags,
            outcome="NONE",
        )
        return action

    policy_post = _policy_snapshot(parent)
    _restore_policy_snapshot(parent, policy_pre)
    try:
        retained_snapshot = runtime_model.public_snapshot(parent, obs)
    except Exception:
        retained_snapshot = None
    retained_hash = getattr(retained_snapshot, "sha256", None)
    if retained_snapshot is None:
        _restore_policy_snapshot(parent, policy_post)
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=action,
            rule=None,
            stage="BASELINE_FALLBACK",
            tags=(TAG_METADATA, TAG_FALLBACK),
            outcome="NONE",
        )
        return action
    transaction["start_snapshot_hash"] = retained_hash
    V2_TRANSACTION = transaction
    attach_action = _rebind(parent, obs, transaction["attach_key"])
    if attach_action is None:
        V2_TRANSACTION = None
        _restore_policy_snapshot(parent, policy_post)
        _trace(
            snapshot_hash=snapshot_hash,
            context=int(obs.select.context),
            action=action,
            rule=None,
            stage="BASELINE_FALLBACK",
            tags=(TAG_NON_UNIQUE, TAG_FALLBACK),
            outcome="NONE",
        )
        return action
    attach_tag = (
        TAG_ATTACH_TELEPATH
        if transaction["energy_id"] == TELEPATH_PSYCHIC
        else TAG_ATTACH_BASIC
    )
    _trace(
        snapshot_hash=retained_hash,
        context=int(obs.select.context),
        action=attach_action,
        rule=RULE,
        stage="ATTACH_DISPATCHED",
        tags=(RULE, attach_tag),
        outcome="ACTIVE",
        transaction=transaction,
        started_event=True,
    )
    return attach_action
