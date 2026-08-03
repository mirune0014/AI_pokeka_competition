from __future__ import annotations

import copy
import csv
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
PARENT = ROOT / "archaludon" / "candidates" / (
    "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = ROOT / "archaludon" / "live" / "55070349" / (
    "refresh_20260729_1241"
) / "shadow_corpus_196_prior_plus_11_new"
SOURCE_MANIFEST = ROOT / "archaludon" / "strategy" / (
    "archaludon_human_fundamentals_planner_20260731"
) / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw"
) / "source_manifest.json"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "pre_edit_jumbo_ice_cream_actionability_census_raw"

ICE = 1147
EXPECTED_NAME = "Jumbo Ice Cream"
EXPECTED_TEXT = (
    "Heal 80 damage from your Active Pokémon that has 3 or more Energy attached."
)

FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "parent_action", "parent_roles", "parent_valid",
    "owner_state", "ice_roles", "ice_serials", "selected_ice_role",
    "historical_ice_play", "active_ref", "active_hp", "active_max_hp",
    "active_energy_count", "effective_heal", "attack_roles",
    "no_heal_plans", "heal_plans", "no_heal_selection_reason",
    "heal_selection_reason", "no_heal_best", "heal_best",
    "first_hard_difference", "purpose", "direction",
    "candidate_first_role", "action_queue", "uniquely_emittable",
    "predicted_first_difference", "rejection_reason",
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


def snapshot_hash(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest().upper()


def load_parent():
    sys.path.insert(0, str(PARENT))
    spec = importlib.util.spec_from_file_location(
        "ice_pre_edit_parent", PARENT / "main.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(PARENT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module) -> None:
    for function, reason in (
        ("_pfgear_reset_active", "ice_census_reset"),
        ("_pcrd_clear", "ice_census_reset"),
        ("_pfc_clear", "ice_census_reset"),
        ("_cum_reset_runtime", "ice_census_reset"),
        ("_dper_reset_runtime", "ice_census_reset"),
    ):
        if hasattr(module, function):
            getattr(module, function)(reason)
    for name in (
        "_h2_transaction", "_h6_transaction", "_pfgear_transaction",
        "_pfgear_veto_watch", "_cum_active_transaction_owner",
        "_cum_owner_meta", "_pcrd_transaction", "_pfc_transaction",
    ):
        if hasattr(module, name):
            setattr(module, name, None)


def roles(module, obs, action):
    try:
        if not module._cum_valid_action(obs, action):
            return None
        return module._pcrd_action_roles(obs, action)
    except Exception as error:
        return ("ERROR", type(error).__name__, str(error))


def owners(module):
    result = {}
    for name in (
        "_h2_transaction", "_h6_transaction", "_pfgear_transaction",
        "_pfgear_veto_watch", "_cum_active_transaction_owner",
        "_cum_owner_meta", "_pcrd_transaction", "_pfc_transaction",
    ):
        value = getattr(module, name, None)
        if value is not None:
            result[name] = freeze(value)
    return result


def metadata(module):
    card = module.CARD_DB.get(ICE)
    skills = [] if card is None else [
        {"name": getattr(skill, "name", None), "text": getattr(skill, "text", None)}
        for skill in tuple(getattr(card, "skills", None) or ())
    ]
    result = {
        "card_id": ICE,
        "name": None if card is None else getattr(card, "name", None),
        "skills": skills,
    }
    return {
        "exact": bool(
            result["name"] == EXPECTED_NAME
            and len(skills) == 1
            and skills[0]["name"] == EXPECTED_NAME
            and skills[0]["text"] == EXPECTED_TEXT
        ),
        **result,
    }


def option_rows(module, obs):
    result = []
    for position, option in enumerate(obs.select.option):
        card = module.option_card(obs, option)
        target = module.option_target(obs, option)
        result.append({
            "position": position,
            "option_type": int(option.type),
            "attack_id": getattr(option, "attackId", None),
            "card_id": getattr(card, "id", None),
            "card_serial": module._pcrd_serial(card),
            "target_id": getattr(target, "id", None),
            "target_serial": module._pcrd_serial(target),
            "role": module._pcrd_option_role(obs, option),
        })
    return result


def role_equal(left, right):
    return canonical(left) == canonical(right)


def parent_is_ice(parent_roles, ice_rows):
    if parent_roles is None or len(parent_roles) != 1:
        return False
    return any(role_equal(parent_roles[0], row["role"]) for row in ice_rows)


def select_ice_row(ice_rows):
    if not ice_rows:
        return None, "ice_option_absent"
    by_serial = defaultdict(list)
    for row in ice_rows:
        by_serial[row["card_serial"]].append(row)
    if any(serial is None or len(rows) != 1 for serial, rows in by_serial.items()):
        return None, "ice_option_duplicate_or_serial_unknown"
    serial = min(by_serial)
    return by_serial[serial][0], None


def attack_rows(module, obs):
    by_attack = defaultdict(list)
    for row in option_rows(module, obs):
        if row["option_type"] == int(module.OptionType.ATTACK):
            by_attack[row["attack_id"]].append(row)
    if not by_attack:
        return None, "no_actual_attack_option"
    result = []
    for attack_id in sorted(by_attack):
        rows = by_attack[attack_id]
        role_map = {canonical(row["role"]): row["role"] for row in rows}
        if not isinstance(attack_id, int) or len(role_map) != 1:
            return None, "attack_role_unknown_or_ambiguous"
        result.append({
            "attack_id": attack_id,
            "role": next(iter(role_map.values())),
            "positions": [row["position"] for row in rows],
        })
    return result, None


def summarize_plan(module, obs, plan, attack_row):
    fields = plan.get("fields") or {}
    certificate = plan.get("current_certificate") or {}
    target = module.opp_active_pokemon(obs)
    damage = certificate.get("final_damage")
    hits = None
    if (
        target is not None and isinstance(getattr(target, "hp", None), int)
        and isinstance(damage, int) and damage > 0
    ):
        hits = 1 if certificate.get("ko") else math.ceil(target.hp / damage)
    backup_ready = fields.get("exact_backup_ready")
    backup_prizes = fields.get("exact_backup_next_prizes")
    backup_turns = fields.get("exact_turns_to_next_prize")
    return {
        "attack_id": attack_row["attack_id"],
        "attack_role": attack_row["role"],
        "status": plan.get("status"),
        "certificate": freeze(certificate),
        "fields": freeze({
            key: fields.get(key) for key in (
                "current_win", "certain_terminal_reply", "current_prizes",
                "current_ko", "certain_return_prizes",
                "current_attacker_survival", "next_turn_payable_attack",
                "exact_backup_ready", "exact_backup_next_prizes",
                "exact_turns_to_next_prize", "active_prize_liability",
            )
        }),
        "hits_to_ko": hits,
        "backup_ready": backup_ready,
        "backup_prizes": backup_prizes,
        "backup_turns": backup_turns,
        "actions": freeze(plan.get("actions") or ()),
    }


def make_world(module, obs, attacks, use_ice):
    plans = []
    errors = []
    for attack_row in attacks:
        try:
            plan = module._pcrd_make_plan(
                obs,
                evolution=None,
                attack_id=attack_row["attack_id"],
                use_fml=False,
                use_cape=False,
                use_ice=use_ice,
                require_current_attack_option=True,
            )
        except Exception as error:
            plan = None
            errors.append(
                str(attack_row["attack_id"]) + ":" + type(error).__name__
            )
        if plan is None:
            errors.append(str(attack_row["attack_id"]) + ":unavailable")
            continue
        if plan.get("status") != "EXACT":
            errors.append(
                str(attack_row["attack_id"]) + ":" + str(plan.get("status"))
            )
            continue
        plans.append(summarize_plan(module, obs, plan, attack_row))
    return plans, errors


def plan_layers(plan):
    fields = plan["fields"]
    required = (
        "current_win", "certain_terminal_reply", "current_prizes",
        "current_ko", "certain_return_prizes", "current_attacker_survival",
        "next_turn_payable_attack", "exact_backup_ready",
    )
    if any(fields.get(key) is None for key in required):
        return None
    hits = plan.get("hits_to_ko")
    if hits is None:
        return None
    backup_ready = bool(fields["exact_backup_ready"])
    backup_prizes = fields.get("exact_backup_next_prizes")
    backup_turns = fields.get("exact_turns_to_next_prize")
    if backup_ready and not isinstance(backup_prizes, int):
        return None
    if not backup_ready:
        backup_prizes = 0
        backup_turns = None
    turn_score = -backup_turns if isinstance(backup_turns, int) else -999
    return (
        (int(bool(fields["current_win"])),),
        (int(not bool(fields["certain_terminal_reply"])),),
        (int(fields["current_prizes"]), int(bool(fields["current_ko"]))),
        (
            int(bool(fields["current_attacker_survival"])),
            -int(fields["certain_return_prizes"]),
            -int(hits),
            int(bool(fields["next_turn_payable_attack"])),
        ),
        (int(backup_ready), int(backup_prizes), turn_score),
    )


def select_best(plans):
    ranked = []
    for plan in plans:
        layers = plan_layers(plan)
        if layers is None:
            continue
        ranked.append((layers, plan))
    if not ranked:
        return None, "no_fully_rankable_plan"
    best_layers = max(row[0] for row in ranked)
    best = [plan for layers, plan in ranked if layers == best_layers]
    if len(best) != 1:
        return None, "multiple_nondominated_best_plans"
    result = dict(best[0])
    result["hard_layers"] = freeze(best_layers)
    return result, None


def compare_worlds(no_heal, heal):
    no_layers = plan_layers(no_heal)
    heal_layers = plan_layers(heal)
    if no_layers is None or heal_layers is None:
        return None, "INCOMPARABLE"
    layer_names = (
        "EXACT_WIN", "TERMINAL_LOSS_AVOIDANCE", "CURRENT_PRIZE_KO",
        "SURVIVAL_RETURN_HITS_CONTINUITY", "BACKUP_NEXT_PRIZE",
    )
    for index, (left, right) in enumerate(zip(no_layers, heal_layers), start=2):
        if left == right:
            continue
        direction = "PLAY_ICE" if right > left else "HOLD_ICE"
        return {
            "layer": index,
            "layer_name": layer_names[index - 2],
            "no_heal": left,
            "heal": right,
            "direction": direction,
        }, direction
    return {
        "layer": None,
        "layer_name": None,
        "no_heal": None,
        "heal": None,
        "direction": "EQUAL",
    }, "EQUAL"


def purpose_for(direction, difference, no_heal, heal, module):
    if direction == "PLAY_ICE" and difference["layer"] in {3, 4, 5, 6}:
        return "SURVIVAL_OR_PRIZE_CLOCK"
    if direction == "HOLD_ICE":
        no_cert = no_heal.get("certificate") or {}
        heal_cert = heal.get("certificate") or {}
        if (
            no_heal.get("attack_id") == module.RAGING_HAMMER
            and (
                bool(no_cert.get("terminal")) > bool(heal_cert.get("terminal"))
                or bool(no_cert.get("ko")) > bool(heal_cert.get("ko"))
                or int(no_cert.get("prize_yield") or 0)
                > int(heal_cert.get("prize_yield") or 0)
            )
        ):
            return "RAGING_HAMMER_KO_PRESERVATION"
        return "NO_HEAL_HARD_ADVANTAGE"
    return None


def main() -> dict:
    if OUTPUT.exists():
        protected = (OUTPUT / "opportunity_rows.csv", OUTPUT / "summary.json")
        if any(path.exists() for path in protected):
            raise SystemExit("refusing to overwrite frozen census output")
    else:
        OUTPUT.mkdir(parents=False)

    module = load_parent()
    effect_metadata = metadata(module)
    if not effect_metadata["exact"]:
        raise SystemExit("Jumbo Ice Cream metadata mismatch")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    replay_cache = {}
    historical_physical = set()
    historical_turns = set()
    mismatches = []
    for entry in manifest:
        replay_path = CORPUS / entry["replay"]
        replay_sha = sha256(replay_path)
        if replay_sha != entry["sha256"]:
            mismatches.append(entry["replay"])
            continue
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        replay_cache[entry["replay"]] = (replay_sha, replay)
        for seat in entry["target_seats"]:
            for step in replay["steps"]:
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat:
                    continue
                for position, log in enumerate(raw.get("logs") or ()):
                    if (
                        log.get("type") == int(module.LogType.PLAY)
                        and log.get("playerIndex") == seat
                        and log.get("cardId") == ICE
                    ):
                        key = (
                            entry["replay"], seat, current.get("turn"),
                            log.get("serial"), position,
                        )
                        historical_physical.add(key)
                        historical_turns.add(key[:3])

    rows_path = OUTPUT / "opportunity_rows.csv"
    counts = Counter()
    row_keys = set()
    duplicate_keys = 0
    calls = 0
    invalid_parent = 0
    strict_turns = set()
    strict_replays = set()
    strict_seats = set()
    actionable_turns = set()
    actionable_replays = set()
    actionable_seats = set()
    predicted_turns = set()
    predicted_replays = set()
    predicted_seats = set()
    direction_turns = defaultdict(set)
    purpose_turns = defaultdict(set)

    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for entry in manifest:
            cached = replay_cache.get(entry["replay"])
            if cached is None:
                continue
            replay_sha, replay = cached
            for seat in entry["target_seats"]:
                reset(module)
                for step_index, step in enumerate(replay["steps"]):
                    raw = step[seat].get("observation") or {}
                    current = raw.get("current") or {}
                    if current.get("yourIndex") != seat or raw.get("select") is None:
                        continue
                    calls += 1
                    parent_action = module.agent(copy.deepcopy(raw))
                    obs = module.to_observation_class(copy.deepcopy(raw))
                    parent_roles = roles(module, obs, parent_action)
                    parent_valid = parent_roles is not None
                    invalid_parent += int(not parent_valid)
                    if obs.select.context != module.SelectContext.MAIN:
                        continue
                    all_options = option_rows(module, obs)
                    ice_rows = [
                        row for row in all_options
                        if row["option_type"] == int(module.OptionType.PLAY)
                        and row["card_id"] == ICE
                    ]
                    if not ice_rows:
                        continue
                    row_key = (
                        entry["replay"], seat, step_index,
                        current.get("turn"), snapshot_hash(raw),
                    )
                    duplicate_keys += int(row_key in row_keys)
                    row_keys.add(row_key)
                    turn_key = (entry["replay"], seat, current.get("turn"))
                    owner_state = owners(module)
                    selected_ice, ice_reason = select_ice_row(ice_rows)
                    attacks, attack_reason = attack_rows(module, obs)
                    active = module.active_pokemon(obs)
                    no_plans = heal_plans = []
                    no_errors = heal_errors = []
                    no_best = heal_best = None
                    no_reason = heal_reason = None
                    difference = None
                    purpose = None
                    direction = "REJECT"
                    candidate_role = None
                    queue = []
                    unique = False
                    predicted = False
                    rejection = None

                    if selected_ice is None:
                        rejection = ice_reason
                    elif owner_state:
                        rejection = "live_owner_collision"
                    elif active is None:
                        rejection = "active_missing"
                    elif attacks is None:
                        rejection = attack_reason
                    else:
                        no_plans, no_errors = make_world(
                            module, obs, attacks, False
                        )
                        heal_plans, heal_errors = make_world(
                            module, obs, attacks, True
                        )
                        no_best, no_reason = select_best(no_plans)
                        heal_best, heal_reason = select_best(heal_plans)
                        if no_best is None:
                            rejection = "no_heal:" + str(no_reason)
                        elif heal_best is None:
                            rejection = "heal:" + str(heal_reason)
                        else:
                            difference, certified_direction = compare_worlds(
                                no_best, heal_best
                            )
                            if certified_direction == "INCOMPARABLE":
                                rejection = "world_comparison_incomparable"
                            else:
                                parent_ice = parent_is_ice(parent_roles, ice_rows)
                                purpose = purpose_for(
                                    certified_direction, difference,
                                    no_best, heal_best, module,
                                )
                                if certified_direction == "PLAY_ICE":
                                    direction = (
                                        "APPROVE_PARENT_ICE"
                                        if parent_ice else "PLAY_ICE"
                                    )
                                    candidate_role = selected_ice["role"]
                                    queue = [
                                        {
                                            "kind": "PLAY_JUMBO_ICE_CREAM",
                                            "card_serial": selected_ice["card_serial"],
                                        },
                                        {
                                            "kind": "ATTACK",
                                            "attack_id": heal_best["attack_id"],
                                            "role": heal_best["attack_role"],
                                        },
                                    ]
                                    unique = True
                                    predicted = direction == "PLAY_ICE"
                                elif certified_direction == "HOLD_ICE" and parent_ice:
                                    direction = "HOLD_ICE"
                                    candidate_role = no_best["attack_role"]
                                    queue = [{
                                        "kind": "ATTACK",
                                        "attack_id": no_best["attack_id"],
                                        "role": no_best["attack_role"],
                                    }]
                                    unique = True
                                    predicted = True
                                else:
                                    direction = "EQUAL"

                    if rejection:
                        direction = "REJECT"
                    if direction in {
                        "PLAY_ICE", "HOLD_ICE", "APPROVE_PARENT_ICE", "EQUAL"
                    } and difference is not None:
                        strict_turns.add(turn_key)
                        strict_replays.add(entry["replay"])
                        strict_seats.add(seat)
                    if direction in {"PLAY_ICE", "HOLD_ICE"} and unique:
                        actionable_turns.add(turn_key)
                        actionable_replays.add(entry["replay"])
                        actionable_seats.add(seat)
                        direction_turns[direction].add(turn_key)
                        if purpose:
                            purpose_turns[purpose].add(turn_key)
                    if predicted:
                        predicted_turns.add(turn_key)
                        predicted_replays.add(entry["replay"])
                        predicted_seats.add(seat)
                    counts["rows"] += 1
                    counts["direction:" + direction] += 1
                    if rejection:
                        counts["rejection:" + rejection] += 1

                    heal_amount = None
                    if active is not None:
                        heal_amount = min(80, max(0, active.maxHp - active.hp))
                    writer.writerow({
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "step": step_index,
                        "turn": current.get("turn"),
                        "snapshot_sha256": row_key[-1],
                        "parent_action": canonical(parent_action),
                        "parent_roles": canonical(parent_roles),
                        "parent_valid": parent_valid,
                        "owner_state": canonical(owner_state),
                        "ice_roles": canonical([row["role"] for row in ice_rows]),
                        "ice_serials": canonical([row["card_serial"] for row in ice_rows]),
                        "selected_ice_role": canonical(
                            None if selected_ice is None else selected_ice["role"]
                        ),
                        "historical_ice_play": turn_key in historical_turns,
                        "active_ref": canonical(
                            None if active is None else module._pcrd_card_ref(active)
                        ),
                        "active_hp": None if active is None else active.hp,
                        "active_max_hp": None if active is None else active.maxHp,
                        "active_energy_count": (
                            None if active is None else len(tuple(active.energyCards or ()))
                        ),
                        "effective_heal": heal_amount,
                        "attack_roles": canonical(attacks),
                        "no_heal_plans": canonical({
                            "plans": no_plans, "errors": no_errors,
                        }),
                        "heal_plans": canonical({
                            "plans": heal_plans, "errors": heal_errors,
                        }),
                        "no_heal_selection_reason": no_reason,
                        "heal_selection_reason": heal_reason,
                        "no_heal_best": canonical(no_best),
                        "heal_best": canonical(heal_best),
                        "first_hard_difference": canonical(difference),
                        "purpose": purpose,
                        "direction": direction,
                        "candidate_first_role": canonical(candidate_role),
                        "action_queue": canonical(queue),
                        "uniquely_emittable": unique,
                        "predicted_first_difference": predicted,
                        "rejection_reason": rejection,
                    })

    summary = {
        "parent_main_sha256": sha256(PARENT / "main.py"),
        "deck_sha256": sha256(PARENT / "deck.csv"),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "runner_sha256": sha256(Path(__file__)),
        "row_csv_sha256": sha256(rows_path),
        "ice_metadata": effect_metadata,
        "ice_metadata_sha256": hashlib.sha256(
            canonical(effect_metadata).encode("utf-8")
        ).hexdigest().upper(),
        "manifest_entries": len(manifest),
        "manifest_mismatches": mismatches,
        "target_seats": sum(len(entry["target_seats"]) for entry in manifest),
        "global_parent_calls": calls,
        "invalid_parent_actions": invalid_parent,
        "historical_ice_physical_plays": len(historical_physical),
        "historical_ice_play_turns": len(historical_turns),
        "historical_ice_play_seats": sorted({row[1] for row in historical_turns}),
        "row_count": len(row_keys),
        "duplicate_row_keys": duplicate_keys,
        "strict_two_world_turns": len(strict_turns),
        "strict_two_world_replays": len(strict_replays),
        "strict_two_world_seats": sorted(strict_seats),
        "actionable_turns": len(actionable_turns),
        "actionable_replays": len(actionable_replays),
        "actionable_seats": sorted(actionable_seats),
        "predicted_first_difference_turns": len(predicted_turns),
        "predicted_first_difference_replays": len(predicted_replays),
        "predicted_first_difference_seats": sorted(predicted_seats),
        "direction_unique_turns": {
            key: len(value) for key, value in sorted(direction_turns.items())
        },
        "direction_seats": {
            key: sorted({row[1] for row in value})
            for key, value in sorted(direction_turns.items())
        },
        "purpose_unique_turns": {
            key: len(value) for key, value in sorted(purpose_turns.items())
        },
        "purpose_seats": {
            key: sorted({row[1] for row in value})
            for key, value in sorted(purpose_turns.items())
        },
        "counts": dict(sorted(counts.items())),
    }
    summary_path = OUTPUT / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if mismatches or invalid_parent or duplicate_keys:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    main()
