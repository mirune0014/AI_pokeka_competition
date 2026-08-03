"""Public-board Boss tempo rule for buying one setup turn."""
from __future__ import annotations

import copy
from typing import Any, Callable

import planner_boss_powerful_hand_exact_ko_reservation as fix10
import planner_model as model
import planner_public_survival_bench0 as survival
import planner_public_tactical_monotonicity as fix9
import planner_runtime_model as runtime_model

RULE_VERSION = "V6_BOSS_TEMPO_STALL_FIX1"
RULE_NAME = "BOSS_TEMPO_STALL"
PARENT_CLOSURE_SHA256 = "C438D6C5986C794017F4F5E57319725A4FF7388C9A0483AFA7A4BD443E969E19"

ABRA, KADABRA, ALAKAZAM = 741, 742, 743
RARE_CANDY, BOSS = 1079, 1182
PSYCHIC_ENERGIES = frozenset({5, 19})
LINE_IDS = frozenset({ABRA, KADABRA, ALAKAZAM})

LAST_TEMPO_BOSS_TRACE: dict[str, Any] | None = None
TEMPO_BOSS_TRANSACTION: dict[str, Any] | None = None


def reset() -> None:
    global LAST_TEMPO_BOSS_TRACE, TEMPO_BOSS_TRANSACTION
    LAST_TEMPO_BOSS_TRACE = None
    TEMPO_BOSS_TRANSACTION = None


def _surface_trace(surface: Any) -> dict[str, Any]:
    if not isinstance(surface, dict):
        return {}
    trace = surface.get("LAST_STAGED_POLICY_TRACE")
    return copy.deepcopy(trace) if isinstance(trace, dict) else {}


def _publish(
    publish: Callable[[dict[str, Any], Any], None],
    surface: Any,
    parent_action: Any,
    action: Any,
    *,
    stage: str,
    reasons: list[str],
    certificate: dict[str, Any] | None,
) -> None:
    global LAST_TEMPO_BOSS_TRACE
    inherited = _surface_trace(surface)
    trace = copy.deepcopy(inherited)
    trace.update(
        {
            "schema_version": 12,
            "rule_version": RULE_VERSION,
            "parent_closure_sha256": PARENT_CLOSURE_SHA256,
            "candidate_closure_sha256": fix10._closure(),
            "tempo_boss_parent_action": copy.deepcopy(parent_action),
            "proposed_action": copy.deepcopy(action),
            "applied_action": copy.deepcopy(action),
            "selected_rule": RULE_NAME,
            "reason_tags": list(reasons),
            "transaction_stage": stage,
            "boss_tempo_certificate": copy.deepcopy(certificate),
            "parent_policy_trace": inherited,
        }
    )
    equal = parent_action is not None and parent_action == action
    trace["action_identity"] = {
        "value_equal": equal,
        "type_equal": parent_action is not None and type(parent_action) is type(action),
        "order_equal": equal,
        "returned_parent_object_unchanged": action is parent_action,
    }
    LAST_TEMPO_BOSS_TRACE = copy.deepcopy(trace)
    publish(copy.deepcopy(trace), copy.deepcopy(surface))


def _complete_public_pokemon(parent: Any, state: Any, pokemon: Any, owner: int) -> bool:
    try:
        data = parent.card_table.get(pokemon.id)
        serials = parent._bridge_pokemon_component_serials(pokemon)
        return bool(
            data is not None
            and data.cardType == parent.CardType.POKEMON
            and parent._bridge_pokemon_is_publicly_complete(pokemon, owner)
            and parent._bridge_protected_serials_are_unique(state, serials)
            and type(data.retreatCost) is int
            and data.retreatCost >= 0
            and isinstance(data.attacks, list)
            and len(data.attacks) == len(set(data.attacks))
        )
    except Exception:
        return False


def _energy_units(parent: Any, pokemon: Any) -> tuple[int, ...] | None:
    try:
        units = parent._bridge_retaliation_energy_units(pokemon)
        return tuple(int(unit) for unit in units) if units is not None else None
    except Exception:
        return None


def _attack_extra_units(parent: Any, pokemon: Any) -> int | None:
    """Minimum additional single-unit attachments required by printed attacks.

    A value of 0 means that at least one attack is payable now.
    A value of 1 means that some one-unit Energy attachment can make an attack
    payable.  Two or more means that a normal one-unit attachment does not let
    the promoted target attack immediately.
    """
    units = _energy_units(parent, pokemon)
    data = parent.card_table.get(getattr(pokemon, "id", None))
    if units is None or data is None or not data.attacks:
        return None
    energy_types = tuple(int(value) for value in parent.EnergyType)
    best: int | None = None
    for attack_id in data.attacks:
        attack = parent.attack_table.get(attack_id)
        if attack is None or attack.attackId != attack_id:
            return None
        cost = tuple(int(unit) for unit in attack.energies)
        try:
            if parent._bridge_retaliation_can_pay(units, cost) is True:
                return 0
            if any(
                parent._bridge_retaliation_can_pay(units + (energy_type,), cost) is True
                for energy_type in energy_types
            ):
                best = 1 if best is None else min(best, 1)
                continue
            if any(
                parent._bridge_retaliation_can_pay(
                    units + (first, second), cost
                )
                is True
                for first in energy_types
                for second in energy_types
            ):
                best = 2 if best is None else min(best, 2)
                continue
            missing = max(3, len(cost) - len(units))
            best = missing if best is None else min(best, missing)
        except Exception:
            return None
    return best


def _active_only_benefit(parent: Any, pokemon: Any) -> bool:
    try:
        data = parent.card_table[pokemon.id]
        for skill in data.skills or ():
            text = " ".join(str(skill.text).lower().split())
            if "in the active spot" in text and (
                "draw" in text or "search your deck" in text or "attach" in text
            ):
                return True
        return False
    except Exception:
        return True


def _retreat_deficit(parent: Any, pokemon: Any) -> int | None:
    units = _energy_units(parent, pokemon)
    try:
        cost = parent.card_table[pokemon.id].retreatCost
    except Exception:
        return None
    if units is None or type(cost) is not int or cost < 0:
        return None
    return max(0, cost - len(units))


def _target_rows(parent: Any, obs: Any) -> list[dict[str, Any]]:
    owner = obs.current.yourIndex
    state = obs.current
    theirs = state.players[1 - owner]
    rows: list[dict[str, Any]] = []
    for bench_index, pokemon in enumerate(theirs.bench):
        if not _complete_public_pokemon(parent, state, pokemon, 1 - owner):
            continue
        attack_extra = _attack_extra_units(parent, pokemon)
        retreat_deficit = _retreat_deficit(parent, pokemon)
        if (
            attack_extra is None
            or attack_extra < 2
            or retreat_deficit is None
            or retreat_deficit < 2
            or _active_only_benefit(parent, pokemon)
        ):
            continue
        rows.append(
            {
                "bench_index": bench_index,
                "card_id": pokemon.id,
                "serial": pokemon.serial,
                "attack_extra_units": attack_extra,
                "retreat_deficit": retreat_deficit,
                "retreat_cost": parent.card_table[pokemon.id].retreatCost,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -row["attack_extra_units"],
            -row["retreat_deficit"],
            -row["retreat_cost"],
            row["serial"],
        ),
    )


def _current_attacker_ready(parent: Any, obs: Any) -> dict[str, Any] | None:
    owner = obs.current.yourIndex
    state = obs.current
    theirs = state.players[1 - owner]
    if len(theirs.active) != 1:
        return None
    active = theirs.active[0]
    if not _complete_public_pokemon(parent, state, active, 1 - owner):
        return None
    extra = _attack_extra_units(parent, active)
    if extra != 0:
        return None
    return {"card_id": active.id, "serial": active.serial, "attack_extra_units": extra}


def _target_of_option(parent: Any, obs: Any, option: Any) -> Any:
    try:
        return parent.get_card(
            obs,
            option.inPlayArea,
            option.inPlayIndex,
            obs.current.yourIndex,
        )
    except Exception:
        return None


def _direct_setup_progress(parent: Any, obs: Any) -> list[dict[str, Any]]:
    rows = fix9._rows(parent, obs)
    if rows is None:
        return []
    progress: list[dict[str, Any]] = []
    for row in rows:
        option = row["option"]
        source = fix9._source(parent, obs, option)
        target = _target_of_option(parent, obs, option)
        source_id = fix9._card_id(source)
        target_id = fix9._card_id(target)
        reason = None
        if option.type == parent.OptionType.EVOLVE and target_id in (ABRA, KADABRA):
            reason = "LEGAL_EVOLUTION_PROGRESS"
        elif (
            option.type == parent.OptionType.ATTACH
            and source_id in PSYCHIC_ENERGIES
            and target_id in LINE_IDS
        ):
            reason = "LEGAL_PSYCHIC_ATTACHMENT_PROGRESS"
        elif option.type == parent.OptionType.PLAY and source_id == RARE_CANDY:
            reason = "LEGAL_RARE_CANDY_PROGRESS"
        if reason is not None:
            progress.append(
                {
                    "index": row["index"],
                    "reason": reason,
                    "source_id": source_id,
                    "target_id": target_id,
                }
            )
    return progress


def _reserved_boss_ko_exists(parent: Any, obs: Any) -> bool:
    """Protect an immediate terminal or multi-prize Boss KO from a stall Boss."""
    try:
        owner = obs.current.yourIndex
        mine = obs.current.players[owner]
        theirs = obs.current.players[1 - owner]
        attack_hand = mine.handCount - fix10.BOSS_HAND_COST
        if (
            attack_hand < 0
            or fix10.deck_v1._attack_index(parent, obs) is None
            or not fix9._ready(parent, obs)
            or not fix10._boss_rows(parent, obs)
        ):
            return False
        for target in theirs.bench:
            projection = fix9._projection(
                parent,
                obs,
                target,
                1 - owner,
                attack_hand,
            )
            if (
                projection.get("effective") == "DAMAGEABLE"
                and isinstance(projection.get("damage"), int)
                and projection["damage"] > 0
                and fix10._eligible_reserved_ko(projection)
            ):
                return True
        return False
    except Exception:
        return False


def _certificate(parent: Any, obs: Any, parent_action: Any) -> dict[str, Any] | None:
    if not fix9._normal_main(parent, obs):
        return None
    if (
        obs.current.supporterPlayed
        or fix9._ko_certificate(parent, obs) is not None
        or _reserved_boss_ko_exists(parent, obs)
    ):
        return None
    try:
        if not parent._exact_prize_lane_boss_metadata_is_exact():
            return None
    except Exception:
        return None
    boss_rows = fix10._boss_rows(parent, obs)
    progress = _direct_setup_progress(parent, obs)
    threat = _current_attacker_ready(parent, obs)
    targets = _target_rows(parent, obs)
    if not boss_rows or not progress or threat is None or not targets:
        return None
    boss = boss_rows[0]
    action = [boss["index"]]
    if not model.action_is_valid(obs, action):
        return None
    target = targets[0]
    selected = fix9._selected(obs, parent_action)
    selected_source = fix9._source(parent, obs, selected)
    return {
        "boss_action": action,
        "boss_serial": boss["source_serial"],
        "target": target,
        "current_threat": threat,
        "direct_setup_progress": progress,
        "parent_selected_type": (
            int(selected.type) if selected is not None else None
        ),
        "parent_selected_source_id": fix9._card_id(selected_source),
        "hidden_switch_risk_accepted": True,
    }


def _advance_target(
    raw: dict[str, Any],
    delegate: Callable[[dict[str, Any]], Any],
    *,
    parent: Any,
    trace_snapshot: Callable[[], Any],
    trace_publish: Callable[[dict[str, Any], Any], None],
) -> Any:
    global TEMPO_BOSS_TRANSACTION
    transaction = copy.deepcopy(TEMPO_BOSS_TRANSACTION)
    TEMPO_BOSS_TRANSACTION = None
    try:
        obs = parent.to_observation_class(copy.deepcopy(raw))
        if not runtime_model.raw_parsed_agree(raw, obs):
            raise ValueError("RAW_PARSED_DISAGREEMENT")
        if (
            obs.current.yourIndex != transaction["owner"]
            or obs.current.turn != transaction["turn"]
            or not fix9._boss_child_envelope(parent, obs)
            or fix10._boss_effect_serial(parent, obs) != transaction["boss_serial"]
        ):
            raise ValueError("EXPECTED_BOSS_TARGET_PROMPT")
        action = fix10._target_action_by_serial(
            parent, obs, transaction["target_serial"]
        )
        if action is None:
            raise ValueError("TARGET_ACTION_UNRESOLVED")
        surface = trace_snapshot()
        _publish(
            trace_publish,
            surface,
            None,
            action,
            stage="TARGET_REBOUND",
            reasons=["PUBLIC_TEMPO_TARGET_REBOUND"],
            certificate=transaction["certificate"],
        )
        return action
    except Exception as error:
        action = delegate(raw)
        surface = trace_snapshot()
        _publish(
            trace_publish,
            surface,
            action,
            action,
            stage="ABORTED",
            reasons=[f"TEMPO_TRANSACTION_{type(error).__name__}"],
            certificate=transaction.get("certificate") if isinstance(transaction, dict) else None,
        )
        return action


def agent(
    raw: dict[str, Any],
    delegate: Callable[[dict[str, Any]], Any],
    *,
    parent: Any,
    trace_snapshot: Callable[[], Any],
    trace_restore: Callable[[Any], None],
    trace_publish: Callable[[dict[str, Any], Any], None],
) -> Any:
    global TEMPO_BOSS_TRANSACTION
    if isinstance(raw, dict) and raw.get("select") is None and raw.get("current") is None:
        reset()
        return delegate(raw)
    if TEMPO_BOSS_TRANSACTION is not None:
        return _advance_target(
            raw,
            delegate,
            parent=parent,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
        )

    # The inner Fix10 wrapper owns an atomic Boss transaction of its own.
    # Never inspect or replace one of its child-prompt actions.
    if fix10.FIX10_TRANSACTION is not None:
        return delegate(raw)

    pre = survival._delegate_snapshot(parent, trace_snapshot)
    parent_action = delegate(raw)
    post = survival._delegate_snapshot(parent, trace_snapshot)
    if (
        fix10.FIX10_TRANSACTION is not None
        or fix9._transaction_in_progress(pre)
        or fix9._transaction_in_progress(post)
    ):
        return parent_action
    try:
        obs = parent.to_observation_class(copy.deepcopy(raw))
        if not runtime_model.raw_parsed_agree(raw, obs):
            return parent_action
        certificate = _certificate(parent, obs, parent_action)
    except Exception:
        return parent_action
    if certificate is None:
        return parent_action

    action = certificate["boss_action"]
    target_serial = certificate["target"]["serial"]
    boss_serial = certificate["boss_serial"]
    if (
        type(target_serial) is not int
        or target_serial <= 0
        or type(boss_serial) is not int
        or boss_serial <= 0
    ):
        return parent_action

    survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
    TEMPO_BOSS_TRANSACTION = {
        "stage": "EXPECT_TARGET",
        "owner": obs.current.yourIndex,
        "turn": obs.current.turn,
        "boss_serial": boss_serial,
        "target_serial": target_serial,
        "certificate": copy.deepcopy(certificate),
    }
    _publish(
        trace_publish,
        post["trace_surface"],
        parent_action,
        action,
        stage="ARMED_TARGET",
        reasons=[
            "CURRENT_ATTACKER_PUBLICLY_READY",
            "TARGET_NEEDS_TWO_ATTACK_ENERGY_UNITS",
            "TARGET_NEEDS_TWO_RETREAT_ENERGY_UNITS",
            "DIRECT_SETUP_PROGRESS_AVAILABLE",
            "HIDDEN_SWITCH_RISK_ACCEPTED",
        ],
        certificate=certificate,
    )
    return action


__all__ = [
    "LAST_TEMPO_BOSS_TRACE",
    "PARENT_CLOSURE_SHA256",
    "RULE_NAME",
    "RULE_VERSION",
    "TEMPO_BOSS_TRANSACTION",
    "agent",
    "reset",
]
