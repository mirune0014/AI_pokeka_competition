from __future__ import annotations

import copy
import csv
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
PLANNER = Path(__file__).resolve().parents[2]
PARENT = ROOT / "archaludon" / "candidates" / (
    "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = ROOT / "archaludon" / "live" / "55070349" / (
    "refresh_20260729_1241"
) / "shadow_corpus_196_prior_plus_11_new"
MANIFEST = PLANNER / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw/source_manifest.json"
)
HELPER_PATH = PLANNER / "next_after_lillie_one_direction_fail_20260801" / (
    "freeze_pre_edit_jumbo_ice_cream_actionability_census.py"
)
STRATEGY = HERE / "STRATEGY_SELECTION_HERO_CAPE_ARBITRATION_V1.md"
RETURN_ROOT = PLANNER / (
    "next_after_neutralization_no_actionable_boundary_20260801"
) / "ROOT_PRE_EDIT_RETURN_RELEVANCE_VERIFICATION.md"
RETURN_AUDIT = PLANNER / (
    "next_after_neutralization_no_actionable_boundary_20260801"
) / "RETURN_RELEVANCE_NUMERICAL_AUDIT_SOL_ULTRA.md"
OUTPUT = HERE / "pre_edit_parent_initiated_hero_cape_census_raw"

HERO_CAPE = 1159
EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "strategy": "C973A81410538E176CEA41FEDB53A9D03D117255CBB67576B25C82D7A1E244B9",
    "return_root": "74307DB1660C13CA1BFDDA9D3A449C853006FB24003A6D5DAFE4BE5B3BFC8903",
    "return_audit": "E5DCD079F492E1A7A6E2340B63CDD8116C10F1B55CFADBE2CB096E0590D86D7A",
}

CALLBACK_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "context", "min_count", "max_count",
    "parent_action", "parent_roles", "parent_valid",
    "pre_call_owners", "post_call_owners", "activation_boundary",
    "clear_owner_boundary", "cape_serial", "cape_metadata_sha256",
    "parent_target_id", "parent_target_serial", "cape_roles",
    "attack_roles", "historical_attach_target", "historical_attach_step",
    "comparison_complete", "comparison_reason", "direction",
    "first_hard_difference", "predicted_role",
    "predicted_first_difference", "predicted_emittable",
    "boundary_class", "errors",
)

WORLD_FIELDS = (
    "replay", "seat", "step", "turn", "snapshot_sha256",
    "world_kind", "cape_serial", "cape_target_id", "cape_target_serial",
    "target_hp_before", "target_max_hp_before", "target_hp_after",
    "target_max_hp_after", "target_tools_before", "target_tools_after",
    "attack_id", "attack_role", "plan_status", "complete",
    "rejection_reason", "current_damage", "current_ko", "current_prize",
    "current_win", "return_source_id", "return_source_serial",
    "return_attack_id", "return_damage", "return_ko", "return_prize",
    "return_terminal", "hits_to_ko", "attacker_survival",
    "forced_promotion", "next_payable_attack", "ready_backup",
    "resource_ledger", "hard_vector",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def freeze(value):
    if isinstance(value, dict):
        return {str(key): freeze(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((freeze(item) for item in value), key=repr)
    if hasattr(value, "value") and isinstance(value.value, int):
        return int(value.value)
    if hasattr(value, "__dict__"):
        return {"__class__": type(value).__name__, **freeze(vars(value))}
    return value


def canonical(value) -> str:
    return json.dumps(freeze(value), ensure_ascii=False, sort_keys=True)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest().upper()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cape_metadata(module):
    card = module.CARD_DB.get(HERO_CAPE)
    skills = [] if card is None else [
        {
            "name": getattr(skill, "name", None),
            "text": getattr(skill, "text", None),
            "text_hash": module._dper_text_hash(getattr(skill, "text", None)),
        }
        for skill in tuple(getattr(card, "skills", ()) or ())
    ]
    result = {
        "card_id": HERO_CAPE,
        "name": None if card is None else getattr(card, "name", None),
        "ace_spec": None if card is None else bool(getattr(card, "aceSpec", False)),
        "skills": skills,
    }
    exact = bool(
        card is not None
        and module._pcrd_exact_trainer(
            HERO_CAPE,
            "Hero's Cape",
            module._PCRD_CAPE_TEXT,
            ace_spec=True,
        )
    )
    return {"exact": exact, **result}


def option_rows(module, obs):
    rows = []
    for position, option in enumerate(obs.select.option):
        card = module.option_card(obs, option)
        target = module.option_target(obs, option)
        rows.append({
            "position": position,
            "type": module._pcrd_int(option.type),
            "card_id": module._pcrd_get(card, "id"),
            "card_serial": module._pcrd_serial(card),
            "target_id": module._pcrd_get(target, "id"),
            "target_serial": module._pcrd_serial(target),
            "attack_id": module._pcrd_int(
                module._pcrd_get(option, "attackId")
            ),
            "role": module._pcrd_option_role(obs, option),
        })
    return rows


def parent_is_cape(module, parent_roles):
    return bool(
        parent_roles is not None
        and len(parent_roles) == 1
        and parent_roles[0][0] == module._pcrd_int(module.OptionType.ATTACH)
        and parent_roles[0][1] == HERO_CAPE
        and parent_roles[0][2] is not None
        and parent_roles[0][5] is not None
    )


def project_cape_world(module, obs, cape_serial, target_serial):
    world = copy.deepcopy(obs)
    mine = module.my_state(world)
    hand = tuple(mine.hand or ())
    capes = [
        card for card in hand
        if module._pcrd_get(card, "id") == HERO_CAPE
        and module._pcrd_serial(card) == cape_serial
    ]
    targets = [
        pokemon for pokemon in module._pcrd_board_pokemon(mine)
        if module._pcrd_serial(pokemon) == target_serial
    ]
    if len(capes) != 1 or len(targets) != 1:
        return None, "cape_or_target_not_unique"
    cape = capes[0]
    target = targets[0]
    tools = tuple(module._pcrd_get(target, "tools", ()) or ())
    hp = module._pcrd_get(target, "hp")
    maximum = module._pcrd_get(target, "maxHp")
    if tools or not isinstance(hp, int) or not isinstance(maximum, int):
        return None, "occupied_tool_or_unknown_hp"
    if hp <= 0 or hp > maximum:
        return None, "invalid_hp"
    mine.hand = [
        card for card in hand if module._pcrd_serial(card) != cape_serial
    ]
    if not isinstance(mine.handCount, int) or mine.handCount <= 0:
        return None, "invalid_hand_count"
    mine.handCount -= 1
    target.hp = hp + 100
    target.maxHp = maximum + 100
    target.tools = [cape]
    return world, None


def plan_complete(plan):
    if not isinstance(plan, dict) or plan.get("status") != "EXACT":
        return False, "plan_not_exact"
    fields = plan.get("fields") or {}
    requirements = (
        ("chosen_public_reply", "status"),
        ("post_action_ledger", "status"),
        ("post_reply_ledger", "status"),
        ("backup_conversion_proof", "status"),
    )
    for name, status_key in requirements:
        value = fields.get(name) or {}
        if value.get(status_key) != "EXACT":
            return False, name + "_not_exact"
    return True, None


def compact_fields(plan):
    if not isinstance(plan, dict):
        return None
    fields = plan.get("fields") or {}
    return {
        "current_win": fields.get("current_win"),
        "current_prizes": fields.get("current_prizes"),
        "current_ko": fields.get("current_ko"),
        "certain_terminal_routes": fields.get("certain_terminal_routes"),
        "certain_return_prizes": fields.get("certain_return_prizes"),
        "current_attacker_survival": fields.get("current_attacker_survival"),
        "hits_to_ko": fields.get("hits_to_ko"),
        "next_turn_payable_attack": fields.get("next_turn_payable_attack"),
        "exact_backup_ready": fields.get("exact_backup_ready"),
        "exact_backup_next_prizes": fields.get("exact_backup_next_prizes"),
        "exact_turns_to_next_prize": fields.get("exact_turns_to_next_prize"),
        "chosen_public_reply": fields.get("chosen_public_reply"),
    }


def world_row(
        module, key, *, world_kind, cape_serial, target_before,
        target_after, attack_id, attack_role, plan, rejection_reason):
    fields = {} if plan is None else (plan.get("fields") or {})
    current = {} if plan is None else (plan.get("current_certificate") or {})
    reply = fields.get("chosen_public_reply") or {}
    route = reply.get("route") or {}
    certificate = route.get("certificate") or {}
    complete, reason = plan_complete(plan)
    if rejection_reason is None:
        rejection_reason = reason
    sequence = canonical(route.get("sequence", ()))
    return {
        **key,
        "world_kind": world_kind,
        "cape_serial": cape_serial,
        "cape_target_id": None if target_before is None else module._pcrd_get(target_before, "id"),
        "cape_target_serial": None if target_before is None else module._pcrd_serial(target_before),
        "target_hp_before": None if target_before is None else module._pcrd_get(target_before, "hp"),
        "target_max_hp_before": None if target_before is None else module._pcrd_get(target_before, "maxHp"),
        "target_hp_after": None if target_after is None else module._pcrd_get(target_after, "hp"),
        "target_max_hp_after": None if target_after is None else module._pcrd_get(target_after, "maxHp"),
        "target_tools_before": canonical(() if target_before is None else module._pcrd_get(target_before, "tools", ())),
        "target_tools_after": canonical(() if target_after is None else module._pcrd_get(target_after, "tools", ())),
        "attack_id": attack_id,
        "attack_role": canonical(attack_role),
        "plan_status": None if plan is None else plan.get("status"),
        "complete": complete,
        "rejection_reason": rejection_reason,
        "current_damage": current.get("final_damage"),
        "current_ko": current.get("ko"),
        "current_prize": current.get("prize_yield"),
        "current_win": fields.get("current_win"),
        "return_source_id": route.get("source_id"),
        "return_source_serial": route.get("source_serial"),
        "return_attack_id": route.get("attack_id"),
        "return_damage": certificate.get("final_damage"),
        "return_ko": certificate.get("ko"),
        "return_prize": route.get("prize_yield"),
        "return_terminal": route.get("terminal"),
        "hits_to_ko": fields.get("hits_to_ko"),
        "attacker_survival": fields.get("current_attacker_survival"),
        "forced_promotion": "FREE_PROMOTION" in sequence,
        "next_payable_attack": fields.get("next_turn_payable_attack"),
        "ready_backup": fields.get("exact_backup_ready"),
        "resource_ledger": canonical(fields.get("post_reply_ledger")),
        "hard_vector": canonical(
            None if plan is None else module._pcrd_lexicographic_layers(plan)
        ),
    }


def unique_best(module, plans):
    if not plans or any(not plan_complete(plan)[0] for plan in plans):
        return None
    best = []
    for plan in plans:
        if any(
            other is not plan
            and module._pcrd_compare_lexicographic(other, plan).get("decision")
            == "CANDIDATE"
            for other in plans
        ):
            continue
        best.append(plan)
    return best[0] if len(best) == 1 else None


def decision(module, parent_role, cape_best, attack_best, cape_roles):
    if attack_best is None or not cape_best or any(
            plan is None for plan in cape_best.values()):
        return {
            "direction": "DEFER_PARENT",
            "reason": "incomplete_or_nonunique_world",
            "first_difference": None,
            "role": parent_role,
            "boundary_class": None,
        }
    attack_vs_all = [
        module._pcrd_compare_lexicographic(attack_best, plan)
        for plan in cape_best.values()
    ]
    if all(row.get("decision") == "CANDIDATE" for row in attack_vs_all):
        first = attack_vs_all[0].get("first_difference")
        attack_step = next(
            step for step in attack_best["actions"] if step["kind"] == "ATTACK"
        )
        role = (
            module._pcrd_int(module.OptionType.ATTACK),
            None,
            None,
            attack_step["attack_id"],
            None,
            None,
            None,
            None,
        )
        return {
            "direction": "VETO_TO_ATTACK",
            "reason": "attack_strictly_dominates_every_cape_world",
            "first_difference": first,
            "role": role,
            "boundary_class": "FINISH_OR_NO_PURPOSE_CONSERVATION",
        }

    target_rows = list(cape_best.items())
    winners = []
    for serial, plan in target_rows:
        if any(
            other_plan is not plan
            and module._pcrd_compare_lexicographic(
                other_plan, plan
            ).get("decision") == "CANDIDATE"
            for _, other_plan in target_rows
        ):
            continue
        winners.append((serial, plan))
    if len(winners) != 1:
        return {
            "direction": "DEFER_PARENT",
            "reason": "cape_targets_tied_or_incomparable",
            "first_difference": None,
            "role": parent_role,
            "boundary_class": None,
        }
    target_serial, winner = winners[0]
    parent_serial = parent_role[5]
    parent_plan = cape_best.get(parent_serial)
    if parent_plan is None:
        return {
            "direction": "DEFER_PARENT",
            "reason": "parent_target_world_missing",
            "first_difference": None,
            "role": parent_role,
            "boundary_class": None,
        }
    comparison = module._pcrd_compare_lexicographic(winner, parent_plan)
    first = comparison.get("first_difference")
    if target_serial == parent_serial:
        return {
            "direction": "APPROVE_PARENT_CAPE",
            "reason": "parent_target_unique_nondominated",
            "first_difference": first,
            "role": parent_role,
            "boundary_class": (
                "SURVIVAL_PRIZE_CONTINUITY"
                if first in {
                    "CURRENT_EXACT_WIN", "EXACT_TERMINAL_LOSS_AVOIDANCE",
                    "CURRENT_PRIZE_KO", "PUBLIC_RETURN_SURVIVAL_CONTINUITY",
                    "EXACT_READY_BACKUP_CONVERSION",
                }
                else None
            ),
        }
    winner_role = None
    for role in cape_roles:
        if role[5] == target_serial:
            winner_role = role
            break
    if winner_role is None or comparison.get("decision") != "CANDIDATE":
        return {
            "direction": "DEFER_PARENT",
            "reason": "retarget_not_uniquely_strict_or_unbound",
            "first_difference": first,
            "role": parent_role,
            "boundary_class": None,
        }
    return {
        "direction": "RETARGET_CAPE",
        "reason": "alternate_target_strictly_dominates_parent_target",
        "first_difference": first,
        "role": winner_role,
        "boundary_class": "SURVIVAL_PRIZE_CONTINUITY",
    }


def historical_attach(module, replay, seat, start_step, turn, cape_serial):
    seen = set()
    current_raw = replay["steps"][start_step][seat].get("observation") or {}
    for entry in current_raw.get("logs") or ():
        seen.add(canonical(entry))
    for step_index in range(start_step + 1, len(replay["steps"])):
        raw = replay["steps"][step_index][seat].get("observation") or {}
        current = raw.get("current") or {}
        if isinstance(turn, int) and current.get("turn") != turn:
            if current.get("turn", turn) > turn:
                break
            continue
        for entry in raw.get("logs") or ():
            fingerprint = canonical(entry)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            if (
                entry.get("type") == 11
                and entry.get("playerIndex") == seat
                and entry.get("cardId") == HERO_CAPE
                and entry.get("serial") == cape_serial
            ):
                return entry.get("serialTarget"), step_index
    return None, None


def main():
    protected = (
        OUTPUT / "callback_rows.csv",
        OUTPUT / "target_world_rows.csv",
        OUTPUT / "summary.json",
    )
    if OUTPUT.exists() and any(path.exists() for path in protected):
        raise SystemExit("refusing to overwrite frozen Hero Cape census")
    OUTPUT.mkdir(parents=False, exist_ok=False)

    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "deck": sha256(PARENT / "deck.csv"),
        "manifest": sha256(MANIFEST),
        "strategy": sha256(STRATEGY),
        "return_root": sha256(RETURN_ROOT),
        "return_audit": sha256(RETURN_AUDIT),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input mismatch: " + canonical(actual_hashes))

    helper = load_module("cape_census_helper", HELPER_PATH)
    module = helper.load_parent()
    metadata = cape_metadata(module)
    if not metadata["exact"]:
        raise SystemExit("Hero Cape metadata mismatch")
    metadata_sha = digest(metadata)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    callback_rows = []
    world_rows = []
    raw_keys = set()
    calls = 0
    target_seats = 0
    invalid_parent = 0
    manifest_mismatches = []
    opportunity_turns = set()
    opportunity_replays = set()
    opportunity_seats = set()
    clear_turns = set()
    clear_replays = set()
    clear_seats = set()
    complete_independent_turns = set()
    complete_independent_replays = set()
    complete_independent_seats = set()
    classifiable_turns = set()
    classifiable_replays = set()
    classifiable_seats = set()
    predicted_turns = set()
    predicted_replays = set()
    predicted_seats = set()
    direction_turns = defaultdict(set)
    direction_replays = defaultdict(set)
    direction_seats = defaultdict(set)
    boundary_turns = defaultdict(set)
    earliest_seen = set()

    for entry in manifest:
        path = CORPUS / entry["replay"]
        replay_sha = sha256(path)
        if replay_sha != entry["sha256"]:
            manifest_mismatches.append(entry["replay"])
            continue
        replay = json.loads(path.read_text(encoding="utf-8"))
        target_seats += len(entry["target_seats"])
        for seat in entry["target_seats"]:
            helper.reset(module)
            for step_index, step in enumerate(replay["steps"]):
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat or raw.get("select") is None:
                    continue
                calls += 1
                raw_key = (
                    entry["replay"], seat, step_index, current.get("turn"),
                    digest(raw),
                )
                if raw_key in raw_keys:
                    raise SystemExit("duplicate raw key")
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = helper.owners(module)
                activation = bool(
                    module._pcrd_activation_boundary(obs) and not pre_owners
                )
                parent_action = module.agent(copy.deepcopy(raw))
                parent_roles = helper.roles(module, obs, parent_action)
                parent_valid = parent_roles is not None
                invalid_parent += int(not parent_valid)
                post_owners = helper.owners(module)
                if not parent_is_cape(module, parent_roles):
                    continue

                turn_key = (entry["replay"], seat, current.get("turn"))
                opportunity_turns.add(turn_key)
                opportunity_replays.add(entry["replay"])
                opportunity_seats.add(seat)
                rows = option_rows(module, obs)
                parent_role = tuple(parent_roles[0])
                cape_serial = parent_role[2]
                cape_rows = [
                    row for row in rows
                    if row["type"] == module._pcrd_int(module.OptionType.ATTACH)
                    and row["card_id"] == HERO_CAPE
                    and row["card_serial"] == cape_serial
                ]
                attack_rows = [
                    row for row in rows
                    if row["type"] == module._pcrd_int(module.OptionType.ATTACK)
                    and row["attack_id"] is not None
                ]
                cape_roles = tuple(row["role"] for row in cape_rows)
                attack_roles = tuple(row["role"] for row in attack_rows)
                clear = bool(
                    activation
                    and not post_owners
                    and module._pcrd_int(obs.select.context)
                    == module._pcrd_int(module.SelectContext.MAIN)
                    and obs.select.minCount == 1
                    and obs.select.maxCount == 1
                )
                if clear:
                    clear_turns.add(turn_key)
                    clear_replays.add(entry["replay"])
                    clear_seats.add(seat)

                errors = []
                plans_by_target = defaultdict(list)
                attack_only_plans = []
                key = {
                    "replay": entry["replay"],
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "snapshot_sha256": raw_key[-1],
                }

                if clear and cape_rows and attack_rows:
                    for attack_row in attack_rows:
                        plan = module._pcrd_make_plan(
                            obs,
                            evolution=None,
                            attack_id=attack_row["attack_id"],
                            use_fml=False,
                            use_cape=False,
                            use_ice=False,
                            require_current_attack_option=True,
                        )
                        attack_only_plans.append(plan)
                        world_rows.append(world_row(
                            module,
                            key,
                            world_kind="ATTACK_NOW",
                            cape_serial=cape_serial,
                            target_before=None,
                            target_after=None,
                            attack_id=attack_row["attack_id"],
                            attack_role=attack_row["role"],
                            plan=plan,
                            rejection_reason=None,
                        ))
                    for cape_row in cape_rows:
                        target_before = module._pcrd_find_own_pokemon(
                            obs, cape_row["target_serial"]
                        )
                        world, projection_reason = project_cape_world(
                            module, obs, cape_serial, cape_row["target_serial"]
                        )
                        target_after = (
                            None if world is None else module._pcrd_find_own_pokemon(
                                world, cape_row["target_serial"]
                            )
                        )
                        for attack_row in attack_rows:
                            plan = None
                            if world is not None:
                                plan = module._pcrd_make_plan(
                                    world,
                                    evolution=None,
                                    attack_id=attack_row["attack_id"],
                                    use_fml=False,
                                    use_cape=False,
                                    use_ice=False,
                                    require_current_attack_option=True,
                                )
                            plans_by_target[cape_row["target_serial"]].append(plan)
                            world_rows.append(world_row(
                                module,
                                key,
                                world_kind="CAPE_THEN_ATTACK",
                                cape_serial=cape_serial,
                                target_before=target_before,
                                target_after=target_after,
                                attack_id=attack_row["attack_id"],
                                attack_role=attack_row["role"],
                                plan=plan,
                                rejection_reason=projection_reason,
                            ))

                attack_best = unique_best(module, attack_only_plans)
                cape_best = {
                    serial: unique_best(module, plans)
                    for serial, plans in plans_by_target.items()
                }
                complete = bool(
                    clear
                    and cape_rows
                    and attack_rows
                    and attack_best is not None
                    and len(cape_best) == len(cape_rows)
                    and all(plan is not None for plan in cape_best.values())
                )
                result = (
                    decision(
                        module, parent_role, cape_best, attack_best, cape_roles
                    )
                    if complete
                    else {
                        "direction": "DEFER_PARENT",
                        "reason": (
                            "live_owner_or_nonboundary"
                            if not clear else "incomplete_target_worlds"
                        ),
                        "first_difference": None,
                        "role": parent_role,
                        "boundary_class": None,
                    }
                )
                predicted_role = tuple(result["role"])
                predicted_difference = canonical(predicted_role) != canonical(parent_role)
                emitted = module._pcrd_bind_roles(obs, (predicted_role,))
                emittable = emitted is not None
                independent = bool(
                    activation and turn_key not in earliest_seen
                )
                if independent:
                    earliest_seen.add(turn_key)
                if independent and complete:
                    complete_independent_turns.add(turn_key)
                    complete_independent_replays.add(entry["replay"])
                    complete_independent_seats.add(seat)
                if independent and complete and result["direction"] != "DEFER_PARENT" and emittable:
                    classifiable_turns.add(turn_key)
                    classifiable_replays.add(entry["replay"])
                    classifiable_seats.add(seat)
                    direction_turns[result["direction"]].add(turn_key)
                    direction_replays[result["direction"]].add(entry["replay"])
                    direction_seats[result["direction"]].add(seat)
                    if result["boundary_class"]:
                        boundary_turns[result["boundary_class"]].add(turn_key)
                    if predicted_difference:
                        predicted_turns.add(turn_key)
                        predicted_replays.add(entry["replay"])
                        predicted_seats.add(seat)
                historical_target, historical_step = historical_attach(
                    module, replay, seat, step_index, current.get("turn"), cape_serial
                )
                callback_rows.append({
                    "replay": entry["replay"],
                    "replay_sha256": replay_sha,
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "snapshot_sha256": raw_key[-1],
                    "context": module._pcrd_int(obs.select.context),
                    "min_count": obs.select.minCount,
                    "max_count": obs.select.maxCount,
                    "parent_action": canonical(parent_action),
                    "parent_roles": canonical(parent_roles),
                    "parent_valid": parent_valid,
                    "pre_call_owners": canonical(pre_owners),
                    "post_call_owners": canonical(post_owners),
                    "activation_boundary": activation,
                    "clear_owner_boundary": clear,
                    "cape_serial": cape_serial,
                    "cape_metadata_sha256": metadata_sha,
                    "parent_target_id": parent_role[4],
                    "parent_target_serial": parent_role[5],
                    "cape_roles": canonical(cape_roles),
                    "attack_roles": canonical(attack_roles),
                    "historical_attach_target": historical_target,
                    "historical_attach_step": historical_step,
                    "comparison_complete": complete,
                    "comparison_reason": result["reason"],
                    "direction": result["direction"],
                    "first_hard_difference": result["first_difference"],
                    "predicted_role": canonical(predicted_role),
                    "predicted_first_difference": predicted_difference,
                    "predicted_emittable": emittable,
                    "boundary_class": result["boundary_class"],
                    "errors": canonical(errors),
                })

    if manifest_mismatches:
        raise SystemExit("manifest mismatch")

    with (OUTPUT / "callback_rows.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALLBACK_FIELDS)
        writer.writeheader()
        writer.writerows(callback_rows)
    with (OUTPUT / "target_world_rows.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=WORLD_FIELDS)
        writer.writeheader()
        writer.writerows(world_rows)

    direction_summary = {
        name: {
            "turns": len(direction_turns[name]),
            "replays": len(direction_replays[name]),
            "seats": sorted(direction_seats[name]),
        }
        for name in sorted(direction_turns)
    }
    gate = {
        "integrity": bool(
            len(manifest) == 207
            and target_seats == 209
            and calls == 25880
            and len(raw_keys) == calls
            and invalid_parent == 0
            and not manifest_mismatches
        ),
        "natural_support": bool(
            len(clear_turns) >= 40
            and clear_seats == {0, 1}
            and len(clear_replays) >= 20
        ),
        "exact_comparisons": bool(
            len(complete_independent_turns) >= 40
            and complete_independent_seats == {0, 1}
        ),
        "actionability": bool(
            len(classifiable_turns) >= 20
            and classifiable_seats == {0, 1}
            and len(classifiable_replays) >= 12
        ),
        "predicted_differences": bool(
            len(predicted_turns) >= 12
            and predicted_seats == {0, 1}
            and len(predicted_replays) >= 8
        ),
        "two_sided_boundary": bool(
            len(direction_turns["RETARGET_CAPE"]) >= 3
            and len(direction_turns["VETO_TO_ATTACK"]) >= 3
            and direction_seats["RETARGET_CAPE"] == {0, 1}
            and direction_seats["VETO_TO_ATTACK"] == {0, 1}
        ),
        "mechanism_repetition": bool(
            len(boundary_turns["SURVIVAL_PRIZE_CONTINUITY"]) >= 3
            and len(boundary_turns[
                "FINISH_OR_NO_PURPOSE_CONSERVATION"
            ]) >= 3
        ),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "cape_metadata": metadata,
        "cape_metadata_sha256": metadata_sha,
        "integrity": {
            "replays": len(manifest),
            "target_seats": target_seats,
            "parent_calls": calls,
            "unique_raw_keys": len(raw_keys),
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
            "callback_rows": len(callback_rows),
            "world_rows": len(world_rows),
        },
        "opportunities": {
            "parent_cape_turns": len(opportunity_turns),
            "parent_cape_replays": len(opportunity_replays),
            "parent_cape_seats": sorted(opportunity_seats),
            "clear_turns": len(clear_turns),
            "clear_replays": len(clear_replays),
            "clear_seats": sorted(clear_seats),
            "complete_independent_turns": len(complete_independent_turns),
            "complete_independent_replays": len(complete_independent_replays),
            "complete_independent_seats": sorted(complete_independent_seats),
            "classifiable_turns": len(classifiable_turns),
            "classifiable_replays": len(classifiable_replays),
            "classifiable_seats": sorted(classifiable_seats),
            "predicted_difference_turns": len(predicted_turns),
            "predicted_difference_replays": len(predicted_replays),
            "predicted_difference_seats": sorted(predicted_seats),
        },
        "directions": direction_summary,
        "boundary_turns": {
            key: len(value) for key, value in sorted(boundary_turns.items())
        },
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "decision_if_gate_fails": (
            "STOP__PARENT_CAPE_NOT_ONE_BROAD_ACTIONABLE_BOUNDARY"
        ),
        "root_qualitative_audit": "PENDING",
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
