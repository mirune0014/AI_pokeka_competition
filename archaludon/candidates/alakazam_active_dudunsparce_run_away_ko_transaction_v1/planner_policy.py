"""Atomic policy wrapper for the integrated public-state turn planner."""

from __future__ import annotations

import copy
import hashlib
from math import ceil
from typing import Any

from planner_model import (
    BaseRole,
    DrawClock,
    IntegratedTurnPlan,
    PlanStep,
    PrizeLane,
    ResourceLedger,
    TurnBudget,
    action_is_valid,
    build_turn_budget,
    card_row,
    lineage_key,
    public_snapshot,
    rebind_option_keys,
    stable_option_key,
)
from planner_semantics import (
    BASIC_PSYCHIC,
    BOSS_ORDERS,
    ENRICHING_ENERGY,
    GENESECT,
    HANDHELD_FAN,
    POWERFUL_HAND,
    RUN_AWAY_DRAW_CARD,
    TELEPATH_PSYCHIC,
    attack_certificates,
    best_ready_attack,
    energy_units,
    enriching_four_draw_is_safe,
    has_psychic_telepath_target,
    missing_energy,
    objective_for_state,
    ordered_draw_clock,
    public_positive_attack_response,
    public_roles,
    run_away_draw_is_safe,
)


PARENT_MUTABLE_FIELDS = (
    "pre_turn",
    "ability_used_dudunsparce",
    "ability_used_fezandipiti",
    "_hilda_source_latch",
    "_enriching_reserve_latch",
    "_fez_ko_bridge_latch",
    "_active_psychic_ko_latch",
    "_stranded_retreat_ko_latch",
    "_guarded_teleportation_latch",
    "_turn_objective_recovery_latch",
    "_guarded_teleportation_semantic_failure",
    "_last_decision_signature",
    "_last_decision_action",
    "_exact_prize_lane_boss_latch",
    "_exact_prize_lane_duplicate",
)

PARENT_OWNER_FIELDS = (
    "_hilda_source_latch",
    "_enriching_reserve_latch",
    "_fez_ko_bridge_latch",
    "_active_psychic_ko_latch",
    "_stranded_retreat_ko_latch",
    "_guarded_teleportation_latch",
    "_turn_objective_recovery_latch",
    "_exact_prize_lane_boss_latch",
)


INTEGRATED_TRANSACTION: dict[str, Any] | None = None
INTEGRATED_DUPLICATE_CACHE: dict[str, tuple[tuple[Any, ...], ...]] = {}
_DUPLICATE_ORDER: list[str] = []
INTEGRATED_TRACE_LOG: list[dict[str, Any]] = []
INTEGRATED_LATEST_TRACE: dict[str, Any] | None = None
_CACHE_LIMIT = 128


def reset_integrated_state() -> None:
    global INTEGRATED_TRANSACTION, INTEGRATED_LATEST_TRACE
    INTEGRATED_TRANSACTION = None
    INTEGRATED_DUPLICATE_CACHE.clear()
    _DUPLICATE_ORDER.clear()
    INTEGRATED_TRACE_LOG.clear()
    INTEGRATED_LATEST_TRACE = None


def parent_state_snapshot(parent: Any) -> dict[str, Any]:
    missing = [name for name in PARENT_MUTABLE_FIELDS if not hasattr(parent, name)]
    if missing:
        raise AttributeError(f"missing parent state: {missing}")
    return {name: copy.deepcopy(getattr(parent, name)) for name in PARENT_MUTABLE_FIELDS}


def restore_parent_state(parent: Any, snapshot: dict[str, Any]) -> None:
    if set(snapshot) != set(PARENT_MUTABLE_FIELDS):
        raise ValueError("incomplete parent rollback snapshot")
    for name in PARENT_MUTABLE_FIELDS:
        current = getattr(parent, name)
        saved = copy.deepcopy(snapshot[name])
        if isinstance(current, dict) and isinstance(saved, dict):
            current.clear()
            current.update(saved)
        elif isinstance(current, list) and isinstance(saved, list):
            current[:] = saved
        else:
            setattr(parent, name, saved)


def parent_owner_active(snapshot: dict[str, Any]) -> bool:
    return any(bool(snapshot[name]) for name in PARENT_OWNER_FIELDS)


def _trace(
    classification: str,
    plan: IntegratedTurnPlan | None,
    snapshot_hash: str | None,
    *,
    parent_action: list[int] | None = None,
    override_action: list[int] | None = None,
    reason: str = "",
    stage: str | None = None,
) -> None:
    global INTEGRATED_LATEST_TRACE
    row = {
        "classification": classification,
        "plan_id": plan.plan_id if plan is not None else None,
        "snapshot_hash": snapshot_hash,
        "kind": dict(plan.metadata).get("kind") if plan is not None else None,
        "stage": stage or (plan.expected_stage if plan is not None else None),
        "objective": plan.objective.vector() if plan is not None else None,
        "parent_action": tuple(parent_action or ()),
        "override_action": tuple(override_action or ()),
        "reason": reason,
    }
    INTEGRATED_TRACE_LOG.append(row)
    INTEGRATED_LATEST_TRACE = row


def _remember(parent: Any, obs: Any, snapshot_hash: str, action: list[int]) -> list[int]:
    keys = tuple(stable_option_key(parent, obs, obs.select.option[index]) for index in action)
    INTEGRATED_DUPLICATE_CACHE[snapshot_hash] = keys
    if snapshot_hash in _DUPLICATE_ORDER:
        _DUPLICATE_ORDER.remove(snapshot_hash)
    _DUPLICATE_ORDER.append(snapshot_hash)
    while len(_DUPLICATE_ORDER) > _CACHE_LIMIT:
        stale = _DUPLICATE_ORDER.pop(0)
        INTEGRATED_DUPLICATE_CACHE.pop(stale, None)
    return list(action)


def _duplicate_action(parent: Any, obs: Any, snapshot_hash: str):
    keys = INTEGRATED_DUPLICATE_CACHE.get(snapshot_hash)
    if keys is None:
        return None
    action = rebind_option_keys(parent, obs, keys)
    if action is None or not action_is_valid(obs, action):
        INTEGRATED_DUPLICATE_CACHE.pop(snapshot_hash, None)
        if snapshot_hash in _DUPLICATE_ORDER:
            _DUPLICATE_ORDER.remove(snapshot_hash)
        return None
    _trace("DUPLICATE_REPLAY", None, snapshot_hash, override_action=action)
    return action


def _option_card(parent: Any, obs: Any, option: Any):
    area = getattr(option, "area", None)
    index = getattr(option, "index", None)
    owner = getattr(option, "playerIndex", None)
    if owner not in (0, 1):
        owner = obs.current.yourIndex
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    if area == parent.AreaType.DECK:
        zone = obs.select.deck or []
    elif area == parent.AreaType.LOOKING:
        zone = obs.current.looking or []
    else:
        player = obs.current.players[owner]
        zones = {
            parent.AreaType.HAND: player.hand or [],
            parent.AreaType.DISCARD: player.discard,
            parent.AreaType.ACTIVE: player.active,
            parent.AreaType.BENCH: player.bench,
            parent.AreaType.PRIZE: player.prize,
            parent.AreaType.STADIUM: obs.current.stadium,
        }
        zone = zones.get(area, [])
    return zone[index] if index < len(zone) else None


def _target_pokemon(parent: Any, obs: Any, option: Any):
    owner = obs.current.yourIndex
    area = getattr(option, "inPlayArea", None)
    index = getattr(option, "inPlayIndex", None)
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    mine = obs.current.players[owner]
    zone = mine.active if area == parent.AreaType.ACTIVE else mine.bench if area == parent.AreaType.BENCH else []
    return zone[index] if index < len(zone) else None


def _plan_id(snapshot_hash: str, kind: str, keys: tuple[tuple[Any, ...], ...]) -> str:
    material = repr((snapshot_hash, kind, keys)).encode("utf-8")
    return hashlib.sha256(material).hexdigest().upper()


def _make_plan(
    parent: Any,
    obs: Any,
    snapshot_hash: str,
    parent_action: list[int],
    kind: str,
    action: list[int],
    *,
    stage: str,
    budget: TurnBudget | None = None,
    ledger: ResourceLedger | None = None,
    H0=None,
    H1=None,
    H2=None,
    aborts: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> IntegratedTurnPlan:
    keys = tuple(stable_option_key(parent, obs, obs.select.option[index]) for index in action)
    roles = public_roles(parent, obs)
    objective = objective_for_state(parent, obs, roles, tie=(kind, keys))
    meta = {"kind": kind, **(metadata or {})}
    return IntegratedTurnPlan(
        _plan_id(snapshot_hash, kind, keys), snapshot_hash, objective,
        tuple(parent_action), H0, H1, H2,
        budget or build_turn_budget(
            parent,
            obs,
            {
                "dudunsparce": bool(parent.ability_used_dudunsparce),
                "fezandipiti": bool(parent.ability_used_fezandipiti),
            },
        ),
        ledger or roles.ledger,
        PrizeLane(), ordered_draw_clock(parent, obs),
        (PlanStep(stage, keys, int(obs.select.context)),),
        stage, keys, aborts, tuple(sorted(meta.items(), key=lambda row: row[0])),
    )


def _parent_chosen_option(obs: Any, parent_action: list[int]):
    if len(parent_action) != 1:
        return None
    index = parent_action[0]
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(obs.select.option):
        return None
    return obs.select.option[index]


def _h0_lethal_powerful_hand(parent: Any, obs: Any):
    state = obs.current
    owner = state.yourIndex
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    if len(mine.active) != 1 or len(theirs.active) != 1:
        return None
    active, target = mine.active[0], theirs.active[0]
    if active.id != parent.Alakazam:
        return None
    available = energy_units(parent, active)
    if available is None or int(parent.EnergyType.PSYCHIC) not in available:
        return None
    if not parent._powerful_hand_target_is_publicly_clear(state, target):
        return None
    if any(card.id == getattr(parent, "Mist_Energy", 11) for card in target.energyCards):
        return None
    required = ceil(max(0, target.hp) / 20)
    if mine.hand is None or len(mine.hand) != mine.handCount or mine.handCount < required:
        return None
    matches = [
        index for index, option in enumerate(obs.select.option)
        if option.type == parent.OptionType.ATTACK and option.attackId == POWERFUL_HAND
    ]
    return (matches[0], required, active, target) if len(matches) == 1 else None


def _parent_step_retains_h0_and_successor(parent: Any, obs: Any, option: Any, required: int) -> bool:
    if option.type not in (parent.OptionType.ATTACH, parent.OptionType.EVOLVE):
        return False
    source = _option_card(parent, obs, option)
    target = _target_pokemon(parent, obs, option)
    mine = obs.current.players[obs.current.yourIndex]
    if source is None or target is None or mine.handCount - 1 < required:
        return False
    if getattr(option, "inPlayArea", None) != parent.AreaType.BENCH:
        return False
    if source.id == TELEPATH_PSYCHIC:
        data = parent.card_table.get(target.id)
        return data is not None and data.energyType == parent.EnergyType.PSYCHIC
    if source.id in (parent.Kadabra, parent.Alakazam, parent.Rare_Candy):
        return target.id in (parent.Abra, parent.Kadabra)
    return False


def _build_powerful_hand_floor(parent: Any, obs: Any, snap: Any, parent_action: list[int]):
    lethal = _h0_lethal_powerful_hand(parent, obs)
    chosen = _parent_chosen_option(obs, parent_action)
    if lethal is None or chosen is None:
        return None
    attack_index, required, active, target = lethal
    if chosen.type == parent.OptionType.ATTACK:
        return None
    if _parent_step_retains_h0_and_successor(parent, obs, chosen, required):
        return None
    action = [attack_index]
    budget = build_turn_budget(parent, obs, {
        "dudunsparce": parent.ability_used_dudunsparce,
        "fezandipiti": parent.ability_used_fezandipiti,
    })
    budget = budget.spend("attack")
    if budget is None:
        return None
    line = lineage_key(active, obs.current.yourIndex)
    ledger = ResourceLedger().assign_role(line, BaseRole.H0) if line else None
    if ledger is None:
        return None
    for card in active.energyCards:
        ledger = ledger.reserve(f"energy:{card.serial}", BaseRole.H0, "current Powerful Hand")
        if ledger is None:
            return None
    return _make_plan(
        parent, obs, snap.sha256, parent_action, "POWERFUL_HAND_FLOOR", action,
        stage="single_attack", budget=budget, ledger=ledger, H0=line,
        aborts=("target changed", "hand below lethal floor", "Mist/effect protection"),
        metadata={"required_hand": required, "target_serial": target.serial},
    ), action, None


def _all_public_cards(obs: Any, owner: int):
    player = obs.current.players[owner]
    cards = list(player.hand or []) + list(player.discard)
    for pokemon in list(player.active) + list(player.bench):
        cards.extend(pokemon.energyCards or [])
        cards.extend(pokemon.tools or [])
        cards.extend(pokemon.preEvolution or [])
    return cards


def _build_hilda_enriching(parent: Any, obs: Any, snap: Any, parent_action: list[int], parent_pre: dict[str, Any]):
    select = obs.select
    state = obs.current
    owner = state.yourIndex
    effect_id = getattr(select.effect, "id", None)
    hilda = parent_pre.get("_hilda_source_latch") or {}
    if (
        select.context != parent.SelectContext.TO_HAND
        or effect_id != parent.Hilda
        or hilda.get("stage") != "await_energy"
        or select.minCount > 1 or select.maxCount < 1
        or select.deck is None
    ):
        return None
    offered = []
    for index, option in enumerate(select.option):
        card = _option_card(parent, obs, option)
        data = parent.card_table.get(card.id) if card is not None else None
        if card is None or data is None or data.cardType not in (parent.CardType.BASIC_ENERGY, parent.CardType.SPECIAL_ENERGY):
            return None
        offered.append((index, card))
    enriching = [(index, card) for index, card in offered if card.id == ENRICHING_ENERGY]
    roles = public_roles(parent, obs)
    H0_takes_prize = False
    theirs = state.players[1 - owner]
    if roles.H0 is not None and theirs.active:
        H0_takes_prize = roles.H0.outcome.amount >= theirs.active[0].hp
    unspent = all(card.id != ENRICHING_ENERGY for card in _all_public_cards(obs, owner))
    if (
        len(enriching) != 1
        or not unspent
        or H0_takes_prize
        or roles.H1 is not None
        or has_psychic_telepath_target(parent, obs)
        or not enriching_four_draw_is_safe(parent, obs, search_removes=1)
    ):
        return None
    option_index, card = enriching[0]
    budget = build_turn_budget(parent, obs, {
        "dudunsparce": parent.ability_used_dudunsparce,
        "fezandipiti": parent.ability_used_fezandipiti,
    })
    if not budget.manual_attachment:
        return None
    ledger = roles.ledger.reserve(f"card:{card.serial}", BaseRole.ENGINE, "mandatory Enriching setup draw")
    if ledger is None:
        return None
    ledger = ledger.reserve("budget:manual_attachment", BaseRole.ENGINE, "attach selected Enriching")
    if ledger is None:
        return None
    action = [option_index]
    plan = _make_plan(
        parent, obs, snap.sha256, parent_action, "HILDA_ENRICHING_SETUP", action,
        stage="await_enriching_attach", budget=budget, ledger=ledger,
        H0=roles.H0.line if roles.H0 else None,
        H1=roles.H1.line if roles.H1 else None,
        H2=roles.H2.line if roles.H2 else None,
        aborts=("Enriching not unique", "unsafe four-draw clock", "no legal attachment", "stale Hilda prompt"),
        metadata={"energy_serial": card.serial, "owner": owner, "start_deck": state.players[owner].deckCount},
    )
    transaction = {"plan": plan, "kind": "HILDA_ENRICHING_SETUP", "stage": "await_enriching_attach", "data": dict(plan.metadata)}
    return plan, action, {"transaction": transaction, "consume": ("_hilda_source_latch",)}


def _build_run_away(parent: Any, obs: Any, snap: Any, parent_action: list[int]):
    chosen = _parent_chosen_option(obs, parent_action)
    state = obs.current
    owner = state.yourIndex
    mine = state.players[owner]
    if (
        obs.select.context != parent.SelectContext.MAIN
        or chosen is None or chosen.type != parent.OptionType.END
        or len(mine.active) != 1 or mine.active[0].id != RUN_AWAY_DRAW_CARD
        or mine.active[0].energyCards or mine.active[0].energies
        or not run_away_draw_is_safe(obs)
    ):
        return None
    roles = public_roles(parent, obs)
    if roles.H0 is not None or roles.H1 is not None:
        return None
    data = parent.card_table.get(RUN_AWAY_DRAW_CARD)
    if data is None or len(data.skills or []) != 1 or data.skills[0].name != "Run Away Draw":
        return None
    matches = []
    for index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.ABILITY:
            continue
        card = _option_card(parent, obs, option)
        if card is not None and card.serial == mine.active[0].serial:
            matches.append(index)
    if len(matches) != 1:
        return None
    line = lineage_key(mine.active[0], owner)
    budget = build_turn_budget(parent, obs, {
        "dudunsparce": parent.ability_used_dudunsparce,
        "fezandipiti": parent.ability_used_fezandipiti,
    })
    budget = budget.spend("ability", line)
    if budget is None:
        return None
    ledger = roles.ledger.assign_role(line, BaseRole.ENGINE) if line else None
    if ledger is None:
        return None
    action = [matches[0]]
    plan = _make_plan(
        parent, obs, snap.sha256, parent_action, "RUN_AWAY_SETUP_CLOCK", action,
        stage="await_run_away_resolution", budget=budget, ledger=ledger,
        aborts=("draw did not resolve", "source did not shuffle", "promotion ambiguous", "deck clock changed"),
        metadata={
            "source_serial": mine.active[0].serial, "owner": owner,
            "start_deck": mine.deckCount, "start_hand": mine.handCount,
            "attached_count": len(mine.active[0].energyCards) + len(mine.active[0].tools),
        },
    )
    transaction = {"plan": plan, "kind": "RUN_AWAY_SETUP_CLOCK", "stage": "await_run_away_resolution", "data": dict(plan.metadata)}
    return plan, action, {"transaction": transaction}


def _fan_metadata_exact(parent: Any) -> bool:
    data = parent.card_table.get(HANDHELD_FAN)
    if data is None or data.cardType != parent.CardType.TOOL or len(data.skills or []) != 1:
        return False
    text = " ".join(data.skills[0].text.lower().replace("pokémon", "pokemon").split())
    return (
        data.skills[0].name == "Handheld Fan"
        and "in the active spot" in text
        and "damaged by an attack" in text
        and "move an energy from the attacking pokemon" in text
        and "opponent's benched pokemon" in text
    )


def _build_fan_attach(parent: Any, obs: Any, snap: Any, parent_action: list[int]):
    state = obs.current
    owner = state.yourIndex
    mine = state.players[owner]
    if (
        obs.select.context != parent.SelectContext.MAIN
        or state.energyAttached and False
        or len(mine.active) != 1
        or mine.active[0].tools
        or not _fan_metadata_exact(parent)
        or not public_positive_attack_response(parent, obs)
        or _h0_lethal_powerful_hand(parent, obs) is not None
    ):
        return None
    matches = []
    for index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.ATTACH:
            continue
        card = _option_card(parent, obs, option)
        target = _target_pokemon(parent, obs, option)
        if card is not None and card.id == HANDHELD_FAN and target is not None and target.serial == mine.active[0].serial:
            matches.append((card.serial, stable_option_key(parent, obs, option), index, card))
    if not matches:
        return None
    _, _, index, fan = min(matches, key=lambda row: (row[0], repr(row[1])))
    roles = public_roles(parent, obs)
    line = lineage_key(mine.active[0], owner)
    role = BaseRole.ENGINE if mine.active[0].id == GENESECT else BaseRole.H0 if roles.H0 and roles.H0.line == line else BaseRole.SACRIFICE
    ledger = roles.ledger.assign_role(line, role) if line else None
    if ledger is None:
        return None
    ledger = ledger.reserve(f"tool:{fan.serial}", role, "Handheld Fan public response")
    if ledger is None:
        return None
    budget = build_turn_budget(parent, obs, {
        "dudunsparce": parent.ability_used_dudunsparce,
        "fezandipiti": parent.ability_used_fezandipiti,
    })
    budget = budget.spend("tool_slot", line)
    if budget is None:
        return None
    action = [index]
    plan = _make_plan(
        parent, obs, snap.sha256, parent_action, "HANDHELD_FAN_RESPONSE", action,
        stage="await_fan_attachment", budget=budget, ledger=ledger,
        H0=roles.H0.line if roles.H0 else None, H1=roles.H1.line if roles.H1 else None,
        H2=roles.H2.line if roles.H2 else None,
        aborts=("Fan not attached", "no positive attack-damage trigger", "source option ambiguous", "recipient option ambiguous"),
        metadata={"fan_serial": fan.serial, "target_serial": mine.active[0].serial, "target_line": line, "owner": owner},
    )
    transaction = {"plan": plan, "kind": "HANDHELD_FAN_RESPONSE", "stage": "await_fan_attachment", "data": dict(plan.metadata)}
    return plan, action, {"transaction": transaction}


def _terminal_attach_candidate(parent: Any, obs: Any, snap: Any, parent_action: list[int]):
    """Cumulative port of terminal Basic-Psychic -> Powerful-Hand v5.

    The cumulative parent normally owns the broader attach transaction first;
    this exact helper activates only when no parent latch did, so it adds no
    general handoff and remains a fail-closed terminal backstop.
    """
    state = obs.current
    owner = state.yourIndex
    mine, theirs = state.players[owner], state.players[1 - owner]
    chosen = _parent_chosen_option(obs, parent_action)
    if (
        obs.select.context != parent.SelectContext.MAIN or state.energyAttached
        or len(mine.active) != 1 or len(theirs.active) != 1
        or mine.active[0].id != parent.Alakazam or mine.active[0].energyCards
        or len(mine.prize) != 2 or parent.prize_count(theirs.active[0]) != 2
        or chosen is None or chosen.type != parent.OptionType.ATTACH
        or _option_card(parent, obs, chosen).id != parent.Enriching_Energy
        or getattr(chosen, "inPlayArea", None) != parent.AreaType.BENCH
        or not parent._powerful_hand_target_is_publicly_clear(state, theirs.active[0])
    ):
        return None
    matches = []
    for index, option in enumerate(obs.select.option):
        card = _option_card(parent, obs, option)
        if (
            option.type == parent.OptionType.ATTACH and card is not None
            and card.id == BASIC_PSYCHIC
            and option.inPlayArea == parent.AreaType.ACTIVE and option.inPlayIndex == 0
        ):
            matches.append((card.serial, index, card))
    if len(matches) != 1 or mine.handCount - 1 < ceil(theirs.active[0].hp / 20):
        return None
    serial, index, card = matches[0]
    action = [index]
    line = lineage_key(mine.active[0], owner)
    budget = build_turn_budget(parent, obs, {
        "dudunsparce": parent.ability_used_dudunsparce,
        "fezandipiti": parent.ability_used_fezandipiti,
    })
    budget = budget.spend("manual_attachment")
    ledger = ResourceLedger().assign_role(line, BaseRole.H0) if line else None
    ledger = ledger.reserve(f"energy:{serial}", BaseRole.H0, "terminal Powerful Hand") if ledger else None
    if budget is None or ledger is None:
        return None
    plan = _make_plan(
        parent, obs, snap.sha256, parent_action, "TERMINAL_PSYCHIC_ATTACH_V5", action,
        stage="await_terminal_attack", budget=budget, ledger=ledger, H0=line,
        aborts=("post-attach state mismatch", "Powerful Hand not unique", "two-Prize prompt mismatch"),
        metadata={"energy_serial": card.serial, "active_serial": mine.active[0].serial, "target_serial": theirs.active[0].serial, "owner": owner},
    )
    transaction = {"plan": plan, "kind": "TERMINAL_PSYCHIC_ATTACH_V5", "stage": "await_terminal_attack", "data": dict(plan.metadata)}
    return plan, action, {"transaction": transaction}


def _new_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], parent_pre: dict[str, Any], parent_post: dict[str, Any]):
    hilda = _build_hilda_enriching(parent, obs, snap, parent_action, parent_pre)
    if hilda is not None:
        return hilda
    if parent_owner_active(parent_pre) or parent_owner_active(parent_post):
        return None
    for builder in (_build_powerful_hand_floor, _build_run_away, _terminal_attach_candidate, _build_fan_attach):
        result = builder(parent, obs, snap, parent_action)
        if result is not None:
            return result
    return None


def _find_pokemon_by_serial(state: Any, serial: int):
    for owner, player in enumerate(state.players):
        for area, pokemon in [("active", p) for p in player.active] + [("bench", p) for p in player.bench]:
            if pokemon is not None and pokemon.serial == serial:
                return owner, area, pokemon
    return None


def _advance_hilda_enriching(parent: Any, obs: Any, transaction: dict[str, Any]):
    plan = transaction["plan"]
    data = transaction["data"]
    owner = data["owner"]
    mine = obs.current.players[owner]
    if transaction["stage"] == "await_enriching_attach":
        if obs.current.yourIndex != owner or obs.select.context != parent.SelectContext.MAIN or mine.deckCount != data["start_deck"] - 1:
            return "abort", None, "post-Hilda MAIN/deck mismatch"
        hand = [card for card in (mine.hand or []) if card.serial == data["energy_serial"] and card.id == ENRICHING_ENERGY]
        if len(hand) != 1:
            return "abort", None, "selected Enriching not unique in hand"
        rows = []
        for index, option in enumerate(obs.select.option):
            card = _option_card(parent, obs, option)
            target = _target_pokemon(parent, obs, option)
            if option.type == parent.OptionType.ATTACH and card is not None and card.serial == data["energy_serial"] and target is not None and (option.inPlayArea == parent.AreaType.ACTIVE or target.id == GENESECT):
                priority = 0 if option.inPlayArea == parent.AreaType.ACTIVE else 1
                rows.append((priority, target.serial, repr(stable_option_key(parent, obs, option)), index, target))
        if not rows:
            return "abort", None, "no named legal Enriching attachment"
        _, _, _, index, target = min(rows)
        transaction["stage"] = "await_enriching_draw"
        data["target_serial"] = target.serial
        data["pre_attach_deck"] = mine.deckCount
        data["pre_attach_hand"] = mine.handCount
        return "override", [index], "reserved Enriching attachment"
    if transaction["stage"] == "await_enriching_draw":
        found = _find_pokemon_by_serial(obs.current, data["target_serial"])
        if found is None or found[0] != owner:
            return "abort", None, "Enriching target missing"
        pokemon = found[2]
        attached = [card for card in pokemon.energyCards if card.serial == data["energy_serial"] and card.id == ENRICHING_ENERGY]
        if len(attached) != 1 or mine.deckCount != data["pre_attach_deck"] - 4 or mine.handCount != data["pre_attach_hand"] - 1 + 4:
            return "abort", None, "mandatory Enriching four-draw delta mismatch"
        return "complete", None, "Enriching setup transaction complete"
    return "abort", None, "unknown Enriching stage"


def _advance_run_away(parent: Any, obs: Any, transaction: dict[str, Any]):
    data = transaction["data"]
    owner = data["owner"]
    mine = obs.current.players[owner]
    drawn = min(3, data["start_deck"])
    expected_deck = data["start_deck"] - drawn + 1 + data["attached_count"]
    if mine.deckCount != expected_deck or mine.handCount != data["start_hand"] + drawn:
        return "abort", None, "Run Away draw/shuffle delta mismatch"
    if _find_pokemon_by_serial(obs.current, data["source_serial"]) is not None:
        return "abort", None, "Run Away source remained public"
    if obs.select.context == parent.SelectContext.TO_ACTIVE:
        rows = []
        for index, option in enumerate(obs.select.option):
            if option.type != parent.OptionType.CARD:
                continue
            card = _option_card(parent, obs, option)
            if card is not None and option.playerIndex == owner and option.area == parent.AreaType.BENCH:
                rows.append((0 if card.id == GENESECT else 1, card.serial, repr(stable_option_key(parent, obs, option)), index))
        if not rows:
            return "abort", None, "Run Away promotion unavailable"
        transaction["stage"] = "await_run_away_main"
        return "override", [min(rows)[3]], "atomic post-Run Away promotion"
    if obs.select.context == parent.SelectContext.MAIN:
        return "complete", None, "Run Away setup transaction complete"
    return "abort", None, "unexpected post-Run Away callback"


def _fan_tool_attached(obs: Any, data: dict[str, Any]) -> bool:
    found = _find_pokemon_by_serial(obs.current, data["target_serial"])
    return bool(found and any(card.id == HANDHELD_FAN and card.serial == data["fan_serial"] for card in found[2].tools))


def _fan_source_score(parent: Any, obs: Any, option: Any):
    owner = obs.current.yourIndex
    opponent = obs.current.players[1 - owner]
    if not opponent.active or option.type != parent.OptionType.ENERGY or option.area != parent.AreaType.ACTIVE or option.playerIndex != 1 - owner:
        return None
    attacker = opponent.active[option.index]
    idx = option.energyIndex
    available = list(energy_units(parent, attacker) or ())
    if not isinstance(idx, int) or not 0 <= idx < len(available):
        return None
    removed_type = available[idx]
    before_best = 99
    after_best = 99
    data = parent.card_table.get(attacker.id)
    if data is None:
        return None
    for attack_id in data.attacks or []:
        attack = parent.attack_table.get(attack_id)
        if attack is None:
            return None
        before_best = min(before_best, len(missing_energy(parent, tuple(available), attack.energies)))
        after = available[:idx] + available[idx + 1 :]
        after_best = min(after_best, len(missing_energy(parent, tuple(after), attack.energies)))
    card = attacker.energyCards[idx] if idx < len(attacker.energyCards) else None
    if card is None:
        return None
    return (after_best - before_best, after_best, card.serial, removed_type, attacker.serial)


def _recipient_benefit(parent: Any, obs: Any, pokemon: Any, energy_type: int):
    before = 99
    after = 99
    data = parent.card_table.get(pokemon.id)
    available = energy_units(parent, pokemon)
    if data is None or available is None:
        return None
    for attack_id in data.attacks or []:
        attack = parent.attack_table.get(attack_id)
        if attack is None:
            return None
        before = min(before, len(missing_energy(parent, available, attack.energies)))
        after = min(after, len(missing_energy(parent, available + (energy_type,), attack.energies)))
    retreat = getattr(data, "retreatCost", 99)
    retreat_before = max(0, retreat - len(available))
    retreat_after = max(0, retreat - len(available) - 1)
    return ((before - after), (retreat_before - retreat_after), -after, -retreat_after)


def _advance_fan(parent: Any, obs: Any, transaction: dict[str, Any]):
    data = transaction["data"]
    stage = transaction["stage"]
    effect_id = getattr(obs.select.effect, "id", None)
    if stage == "await_fan_attachment":
        if not _fan_tool_attached(obs, data):
            return "abort", None, "Fan attachment did not resolve"
        transaction["stage"] = "await_fan_trigger"
        stage = "await_fan_trigger"
    if stage == "await_fan_trigger":
        if effect_id != HANDHELD_FAN:
            if not _fan_tool_attached(obs, data):
                return "complete", None, "Fan left play without positive attack-damage trigger"
            return "pass", None, "waiting for public attack-damage response"
        if obs.select.context != parent.SelectContext.SWITCH_ENERGY:
            return "abort", None, "Fan source prompt context mismatch"
        rows = []
        for index, option in enumerate(obs.select.option):
            score = _fan_source_score(parent, obs, option)
            if score is not None:
                rows.append((-score[0], -score[1], score[2], repr(stable_option_key(parent, obs, option)), index, score))
        if not rows:
            return "abort", None, "Fan source mapping incomplete"
        row = min(rows)
        score = row[-1]
        data.update(source_energy_serial=score[2], energy_type=score[3], source_serial=score[4])
        transaction["stage"] = "await_fan_recipient"
        return "override", [row[4]], "maximal attacker payment deficit"
    if stage == "await_fan_recipient":
        if effect_id != HANDHELD_FAN or obs.select.context != parent.SelectContext.ATTACH_FROM:
            return "abort", None, "Fan recipient prompt context mismatch"
        rows = []
        owner = obs.current.yourIndex
        opponent = obs.current.players[1 - owner]
        for index, option in enumerate(obs.select.option):
            if option.type != parent.OptionType.CARD or option.area != parent.AreaType.BENCH or option.playerIndex != 1 - owner:
                continue
            pokemon = opponent.bench[option.index] if isinstance(option.index, int) and 0 <= option.index < len(opponent.bench) else None
            benefit = _recipient_benefit(parent, obs, pokemon, data["energy_type"]) if pokemon is not None else None
            if benefit is not None:
                rows.append((benefit, pokemon.serial, repr(stable_option_key(parent, obs, option)), index, pokemon.serial))
        if not rows:
            return "abort", None, "Fan recipient mapping incomplete"
        row = min(rows)
        data["recipient_serial"] = row[4]
        transaction["stage"] = "await_fan_complete"
        return "override", [row[3]], "minimal recipient attack/retreat readiness"
    if stage == "await_fan_complete":
        source = _find_pokemon_by_serial(obs.current, data["source_serial"])
        recipient = _find_pokemon_by_serial(obs.current, data["recipient_serial"])
        source_has = bool(source and any(card.serial == data["source_energy_serial"] for card in source[2].energyCards))
        recipient_has = bool(recipient and any(card.serial == data["source_energy_serial"] for card in recipient[2].energyCards))
        if source_has or not recipient_has:
            return "abort", None, "Fan atomic move delta mismatch"
        return "complete", None, "Fan source/recipient transaction complete"
    return "abort", None, "unknown Fan stage"


def _advance_terminal(parent: Any, obs: Any, transaction: dict[str, Any]):
    data = transaction["data"]
    if transaction["stage"] == "await_terminal_attack":
        found = _find_pokemon_by_serial(obs.current, data["active_serial"])
        if found is None or not any(card.serial == data["energy_serial"] for card in found[2].energyCards):
            return "abort", None, "terminal Psychic attachment mismatch"
        matches = [index for index, option in enumerate(obs.select.option) if option.type == parent.OptionType.ATTACK and option.attackId == POWERFUL_HAND]
        if obs.select.context != parent.SelectContext.MAIN or len(matches) != 1:
            return "abort", None, "terminal Powerful Hand not unique"
        transaction["stage"] = "await_terminal_prizes"
        return "override", [matches[0]], "terminal Powerful Hand"
    if transaction["stage"] == "await_terminal_prizes":
        if obs.select.context != parent.SelectContext.TO_HAND or obs.select.minCount != 2 or obs.select.maxCount != 2 or len(obs.select.option) != 2:
            return "abort", None, "terminal two-Prize prompt mismatch"
        rows = []
        for index, option in enumerate(obs.select.option):
            if option.type == parent.OptionType.CARD and option.area == parent.AreaType.PRIZE and option.playerIndex == data["owner"]:
                rows.append((option.index, index))
        if len(rows) != 2:
            return "abort", None, "terminal Prize mapping ambiguous"
        transaction["stage"] = "await_terminal_result"
        return "override", [index for _, index in sorted(rows)], "terminal exact Prize selection"
    if transaction["stage"] == "await_terminal_result":
        return "complete", None, "terminal v5 route complete"
    return "abort", None, "unknown terminal stage"


def _advance_transaction(parent: Any, obs: Any):
    transaction = INTEGRATED_TRANSACTION
    if transaction is None:
        return "none", None, ""
    kind = transaction["kind"]
    if kind == "HILDA_ENRICHING_SETUP":
        return _advance_hilda_enriching(parent, obs, transaction)
    if kind == "RUN_AWAY_SETUP_CLOCK":
        return _advance_run_away(parent, obs, transaction)
    if kind == "HANDHELD_FAN_RESPONSE":
        return _advance_fan(parent, obs, transaction)
    if kind == "TERMINAL_PSYCHIC_ATTACH_V5":
        return _advance_terminal(parent, obs, transaction)
    return "abort", None, "unknown transaction kind"


def _consume_parent_sources(parent: Any, fields: tuple[str, ...]) -> None:
    for name in fields:
        value = getattr(parent, name)
        if isinstance(value, dict):
            value.clear()
        elif isinstance(value, list):
            value.clear()
        else:
            setattr(parent, name, None)


def _emergency_lowest_legal(parent: Any, obs_dict: dict, reason: str):
    try:
        obs = parent.to_observation_class(obs_dict)
        if obs.select is None:
            return parent.my_deck
        action = list(range(min(obs.select.minCount, len(obs.select.option))))
        if action_is_valid(obs, action):
            _trace("EMERGENCY_LOWEST_LEGAL", None, None, override_action=action, reason=reason)
            return action
    except Exception:
        pass
    return []


def agent(parent: Any, parent_agent: Any, obs_dict: dict) -> list[int]:
    """Call the cumulative parent once, then atomically arbitrate one plan."""
    global INTEGRATED_TRANSACTION
    try:
        if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
            reset_integrated_state()
            return parent_agent(obs_dict)
        obs = parent.to_observation_class(obs_dict)
        snap = public_snapshot(parent, obs)
        if snap is None:
            return parent_agent(obs_dict)
        duplicate = _duplicate_action(parent, obs, snap.sha256)
        if duplicate is not None:
            return duplicate
        parent_pre = parent_state_snapshot(parent)
        had_transaction = INTEGRATED_TRANSACTION is not None
        parent_action = parent_agent(obs_dict)
        parent_post = parent_state_snapshot(parent)
        if not action_is_valid(obs, parent_action):
            return _emergency_lowest_legal(parent, obs_dict, "invalid cumulative-parent action")

        if had_transaction:
            plan = INTEGRATED_TRANSACTION["plan"]
            outcome, override, reason = _advance_transaction(parent, obs)
            if outcome == "override" and override is not None and action_is_valid(obs, override):
                restore_parent_state(parent, parent_pre)
                _trace("PLANNER_OVERRIDE", plan, snap.sha256, parent_action=parent_action, override_action=override, reason=reason, stage=INTEGRATED_TRANSACTION["stage"])
                return _remember(parent, obs, snap.sha256, override)
            if outcome == "complete":
                _trace("TRANSACTION_COMPLETE", plan, snap.sha256, parent_action=parent_action, reason=reason, stage=INTEGRATED_TRANSACTION["stage"])
                INTEGRATED_TRANSACTION = None
                return parent_action
            if outcome == "pass":
                return parent_action
            _trace("TRANSACTION_ABORT", plan, snap.sha256, parent_action=parent_action, reason=reason, stage=INTEGRATED_TRANSACTION["stage"])
            INTEGRATED_TRANSACTION = None
            return parent_action

        result = _new_plan(parent, obs, snap, parent_action, parent_pre, parent_post)
        if result is None:
            return parent_action
        plan, override, commit = result
        if not action_is_valid(obs, override):
            _trace("TRANSACTION_ABORT", plan, snap.sha256, parent_action=parent_action, reason="candidate override invalid")
            return parent_action
        restore_parent_state(parent, parent_pre)
        if commit:
            _consume_parent_sources(parent, tuple(commit.get("consume", ())))
            INTEGRATED_TRANSACTION = commit.get("transaction")
        _trace("PLANNER_OVERRIDE", plan, snap.sha256, parent_action=parent_action, override_action=override, reason="lexicographic integrated plan selected")
        return _remember(parent, obs, snap.sha256, override)
    except Exception as exc:
        return _emergency_lowest_legal(parent, obs_dict, f"integrated exception: {type(exc).__name__}: {exc}")
