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
HELPER = PLANNER / "next_after_lillie_one_direction_fail_20260801" / (
    "freeze_pre_edit_jumbo_ice_cream_actionability_census.py"
)
STRATEGY = HERE / (
    "STRATEGY_SELECTION_FIRST_TURBO_PUBLIC_EXACT_ROLE_FILL_V1.md"
)
OPENING_STOP = PLANNER / "next_after_hero_cape_no_broad_boundary_20260801" / (
    "ROOT_PRE_EDIT_OPENING_TIMING_FEASIBILITY.md"
)
HERO_STOP = PLANNER / (
    "next_after_return_relevance_no_actionable_boundary_20260801"
) / "hero_cape_ko_prize_arbitration_v1" / (
    "ROOT_PRE_EDIT_HERO_CAPE_ARBITRATION_VERIFICATION.md"
)
OUTPUT = HERE / "pre_edit_first_turbo_exact_role_fill_census_raw"

METAL = 8
CINDERACE = 666
TURBO = 965
ROLE_ATTACKS = {
    169: (224, "RAGING_HAMMER", 0),
    190: (253, "METAL_DEFENDER", 1),
    840: (1212, "COATED_ATTACK", 2),
    666: (965, "TURBO_FLARE", 3),
}
EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "helper": "3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B",
    "strategy": "E3E6C7BBA58DB125FCF2594FD0EA3A2DE826563DDE5B96DD95682BB213C0389D",
    "opening_stop": "456536AA5494B398DC9B4651431AEF604355B1F2879777F77F8D47A8025D1293",
    "hero_stop": "FB01EBB6451ED5696D3FA0C17EDD81BBE9C53ADF72AE54B20C671551D2C38627",
}

CALLBACK_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "turn_action_count", "snapshot_sha256", "context", "stage",
    "effect_id", "effect_serial", "context_energy_serial",
    "attack_log_confirmed", "first_turbo", "pre_owners", "post_owners",
    "h3_owned", "min_count", "max_count", "bench_snapshot",
    "legal_semantics", "parent_action", "parent_semantic", "parent_valid",
    "contract_action", "contract_semantic", "contract_valid",
    "desired_energy_count", "selected_energy_serials", "target_id",
    "target_serial", "role_attack_id", "role_cost", "missing_before",
    "missing_after", "parent_vector", "contract_vector", "direction",
    "predicted_difference", "hidden_info_used", "classification", "error",
)
TRANSACTION_FIELDS = (
    "replay", "replay_sha256", "seat", "turn", "source_serial",
    "start_step", "start_snapshot_sha256", "callback_rows", "target_rows",
    "owner_clear", "h3_owned", "metadata_exact", "bench_exact",
    "parent_valid", "contract_valid", "selected_energy_count",
    "desired_energy_count", "predicted_difference", "difference_stage",
    "classification", "direction", "parent_equal", "rejection_reason",
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


def live_owners(module):
    owners = []
    for name, value in tuple(vars(module).items()):
        if value is None or callable(value):
            continue
        if (
            name.endswith("_transaction")
            or name.endswith("_watch")
            or name == "_cum_active_transaction_owner"
        ):
            owners.append(name)
    return tuple(sorted(owners))


def h3_owned(owners):
    return any(name.startswith("_h3_") for name in owners)


def turbo_log(module, obs, seat, source_serial):
    matches = [
        entry
        for entry in tuple(obs.logs or ())
        if (
            module._pcrd_int(module._pcrd_get(entry, "type"))
            == module._pcrd_int(module.LogType.ATTACK)
            and module._pcrd_int(module._pcrd_get(entry, "playerIndex")) == seat
            and module._pcrd_int(module._pcrd_get(entry, "attackId")) == TURBO
            and module._pcrd_serial(entry) == source_serial
        )
    ]
    return len(matches) == 1


def option_semantics(module, obs):
    return tuple(
        module._pcrd_option_role(obs, option) for option in obs.select.option
    )


def role_rows(module, obs):
    if not module._pcrd_static_metadata_supported():
        return None, "static_metadata_unknown"
    bench = tuple(module.my_state(obs).bench or ())
    seen = set()
    rows = []
    for pokemon in bench:
        if pokemon is None:
            return None, "null_bench_slot"
        card_id = module._pcrd_get(pokemon, "id")
        serial = module._pcrd_serial(pokemon)
        if serial is None or serial in seen:
            return None, "bench_serial_unknown_or_duplicate"
        seen.add(serial)
        binding = ROLE_ATTACKS.get(card_id)
        if binding is None:
            return None, "unsupported_bench_role"
        attack_id, role_name, role_rank = binding
        data = module.CARD_DB.get(card_id)
        attack = module.ALL_ATTACKS.get(attack_id)
        if (
            data is None
            or attack is None
            or attack_id not in tuple(module._pcrd_get(data, "attacks", ()) or ())
        ):
            return None, "role_attack_metadata_unknown"
        costs = tuple(
            module._pcrd_int(value)
            for value in (module._pcrd_get(attack, "energies", ()) or ())
        )
        energy_rows = module._pcrd_energy_rows(pokemon)
        missing = module._pcrd_missing_energy_count(pokemon, attack)
        if (
            not costs
            or any(value is None for value in costs)
            or energy_rows is None
            or missing is None
        ):
            return None, "role_cost_or_energy_unknown"
        rows.append({
            "target_id": card_id,
            "target_serial": serial,
            "role_attack_id": attack_id,
            "role_name": role_name,
            "role_rank": role_rank,
            "role_cost": len(costs),
            "attached_energy": len(energy_rows),
            "missing": missing,
        })
    return tuple(rows), None


def useful_count(rows, maximum):
    if rows is None:
        return None
    return min(maximum, sum(row["missing"] for row in rows))


def metal_positions(module, obs):
    rows = []
    for position, option in enumerate(obs.select.option):
        card = module.option_card(obs, option)
        if (
            option.type == module.OptionType.CARD
            and module._pcrd_get(card, "id") == METAL
            and module._pcrd_serial(card) is not None
        ):
            rows.append((position, module._pcrd_serial(card)))
    return tuple(rows)


def choose_energy_action(module, obs, parent_action, desired):
    rows = metal_positions(module, obs)
    if desired is None or desired < obs.select.minCount or desired > obs.select.maxCount:
        return None, "desired_count_outside_callback_bounds", ()
    if desired > len({serial for _, serial in rows}):
        return None, "insufficient_unique_metal_options", ()
    parent = tuple(parent_action or ())
    parent_metal = [
        (position, module._pcrd_serial(module.option_card(obs, obs.select.option[position])))
        for position in parent
        if (
            isinstance(position, int)
            and 0 <= position < len(obs.select.option)
            and module._pcrd_get(
                module.option_card(obs, obs.select.option[position]), "id"
            ) == METAL
        )
    ]
    if len(parent_metal) == len(parent) and len(parent) >= desired:
        selected = parent_metal[:desired]
    else:
        selected = sorted(rows, key=lambda row: (row[1], row[0]))[:desired]
    serials = tuple(serial for _, serial in selected)
    if len(serials) != desired or len(set(serials)) != desired:
        return None, "energy_copy_binding_ambiguous", ()
    action = [position for position, _ in selected]
    return action, None, serials


def choose_target_action(module, obs, parent_action, rows):
    legal = []
    by_serial = {row["target_serial"]: row for row in tuple(rows or ())}
    for position, option in enumerate(obs.select.option):
        pokemon = module.option_card(obs, option)
        serial = module._pcrd_serial(pokemon)
        row = by_serial.get(serial)
        if option.type == module.OptionType.CARD and row is not None:
            legal.append((position, row))
    incomplete = [(position, row) for position, row in legal if row["missing"] > 0]
    if not incomplete:
        return None, "no_incomplete_role_target", None
    best_key = min((row["missing"], row["role_rank"]) for _, row in incomplete)
    best = [
        (position, row)
        for position, row in incomplete
        if (row["missing"], row["role_rank"]) == best_key
    ]
    if len(best) != 1:
        return list(parent_action), None, None
    position, row = best[0]
    return [position], None, row


def finalize(transaction, transaction_rows):
    if transaction is None:
        return
    transaction_rows.append({
        key: canonical(value) if isinstance(value, (dict, list, tuple, set)) else value
        for key, value in transaction.items()
        if key in TRANSACTION_FIELDS
    })


def main():
    protected = (
        OUTPUT / "first_turbo_callback_rows.csv",
        OUTPUT / "first_turbo_transaction_rows.csv",
        OUTPUT / "predicted_first_differences.csv",
        OUTPUT / "source_manifest.json",
        OUTPUT / "summary.json",
    )
    if OUTPUT.exists():
        raise SystemExit("refusing to reuse first-Turbo census destination")

    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "deck": sha256(PARENT / "deck.csv"),
        "manifest": sha256(MANIFEST),
        "helper": sha256(HELPER),
        "strategy": sha256(STRATEGY),
        "opening_stop": sha256(OPENING_STOP),
        "hero_stop": sha256(HERO_STOP),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input hash mismatch: " + canonical(actual_hashes))

    OUTPUT.mkdir(parents=False, exist_ok=False)
    (OUTPUT / "source_manifest.json").write_bytes(MANIFEST.read_bytes())

    helper = load_module("first_turbo_helper", HELPER)
    module = helper.load_parent()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    callback_rows = []
    transaction_rows = []
    differences = []
    raw_keys = set()
    callback_keys = set()
    transaction_keys = set()
    calls = 0
    target_seats = 0
    invalid_parent = 0
    manifest_mismatches = []
    all_errors = []

    for entry in manifest:
        replay_path = CORPUS / entry["replay"]
        replay_sha = sha256(replay_path)
        if replay_sha != entry["sha256"]:
            manifest_mismatches.append(entry["replay"])
            continue
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        target_seats += len(entry["target_seats"])
        for seat in entry["target_seats"]:
            helper.reset(module)
            first_started = False
            transaction = None
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
                    raise SystemExit("duplicate raw callback key")
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = live_owners(module)
                parent_action = module.agent(copy.deepcopy(raw))
                post_owners = live_owners(module)
                parent_valid = bool(module._cum_valid_action(obs, parent_action))
                invalid_parent += int(not parent_valid)
                parent_roles = (
                    module._pcrd_action_roles(obs, parent_action)
                    if parent_valid else None
                )
                if parent_roles is None:
                    invalid_parent += int(parent_valid)

                context = module._pcrd_int(obs.select.context)
                effect_id = module._pcrd_get(obs.select.effect, "id")
                effect_serial = module._pcrd_serial(obs.select.effect)
                starts = bool(
                    not first_started
                    and context == module._pcrd_int(module.SelectContext.ATTACH_TO)
                    and effect_id == CINDERACE
                    and effect_serial is not None
                    and turbo_log(module, obs, seat, effect_serial)
                )
                if starts:
                    finalize(transaction, transaction_rows)
                    first_started = True
                    rows, role_error = role_rows(module, obs)
                    desired = useful_count(rows, min(3, obs.select.maxCount))
                    action, action_error, selected_serials = choose_energy_action(
                        module, obs, parent_action, desired
                    )
                    contract_valid = bool(
                        action is not None and module._cum_valid_action(obs, action)
                    )
                    contract_roles = (
                        module._pcrd_action_roles(obs, action)
                        if contract_valid else None
                    )
                    owner_clear = not pre_owners and not post_owners
                    error = role_error or action_error
                    predicted = bool(
                        owner_clear
                        and error is None
                        and parent_valid
                        and contract_valid
                        and len(parent_action) != len(action)
                    )
                    direction = (
                        "REDUCE_ENERGY_COUNT"
                        if predicted and len(action) < len(parent_action)
                        else "INCREASE_ENERGY_COUNT"
                        if predicted
                        else "PARENT_EQUAL"
                        if error is None and contract_valid
                        else "DEFER_PARENT"
                    )
                    classification = (
                        "OVERFILL_AVOIDANCE"
                        if predicted and len(action) < len(parent_action)
                        else "EXACT_COST_FILL"
                        if predicted
                        else "PARENT_EQUAL"
                        if direction == "PARENT_EQUAL"
                        else "DEFER_OWNER"
                        if not owner_clear
                        else "UNKNOWN"
                    )
                    transaction_key = (
                        entry["replay"], seat, current.get("turn"), effect_serial
                    )
                    if transaction_key in transaction_keys:
                        raise SystemExit("duplicate first-Turbo transaction key")
                    transaction_keys.add(transaction_key)
                    transaction = {
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "turn": current.get("turn"),
                        "source_serial": effect_serial,
                        "start_step": step_index,
                        "start_snapshot_sha256": raw_key[-1],
                        "callback_rows": 1,
                        "target_rows": 0,
                        "owner_clear": owner_clear,
                        "h3_owned": h3_owned(pre_owners + post_owners),
                        "metadata_exact": module._pcrd_static_metadata_supported(),
                        "bench_exact": rows is not None,
                        "parent_valid": parent_valid,
                        "contract_valid": contract_valid,
                        "selected_energy_count": len(parent_action),
                        "desired_energy_count": desired,
                        "predicted_difference": predicted,
                        "difference_stage": "ATTACH_TO" if predicted else None,
                        "classification": classification,
                        "direction": direction,
                        "parent_equal": bool(
                            owner_clear and error is None and contract_valid and not predicted
                        ),
                        "rejection_reason": error or (
                            "owner_live" if not owner_clear else None
                        ),
                        "selected_energy_serials_internal": selected_serials,
                        "diverged_internal": predicted,
                    }
                    row = {
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "step": step_index,
                        "turn": current.get("turn"),
                        "turn_action_count": current.get("turnActionCount"),
                        "snapshot_sha256": raw_key[-1],
                        "context": context,
                        "stage": "ATTACH_TO",
                        "effect_id": effect_id,
                        "effect_serial": effect_serial,
                        "context_energy_serial": None,
                        "attack_log_confirmed": True,
                        "first_turbo": True,
                        "pre_owners": canonical(pre_owners),
                        "post_owners": canonical(post_owners),
                        "h3_owned": transaction["h3_owned"],
                        "min_count": obs.select.minCount,
                        "max_count": obs.select.maxCount,
                        "bench_snapshot": canonical(rows),
                        "legal_semantics": canonical(option_semantics(module, obs)),
                        "parent_action": canonical(parent_action),
                        "parent_semantic": canonical(parent_roles),
                        "parent_valid": parent_valid,
                        "contract_action": canonical(action),
                        "contract_semantic": canonical(contract_roles),
                        "contract_valid": contract_valid,
                        "desired_energy_count": desired,
                        "selected_energy_serials": canonical(selected_serials),
                        "target_id": None,
                        "target_serial": None,
                        "role_attack_id": None,
                        "role_cost": None,
                        "missing_before": None,
                        "missing_after": None,
                        "parent_vector": canonical({"selected_count": len(parent_action)}),
                        "contract_vector": canonical({"selected_count": desired}),
                        "direction": direction,
                        "predicted_difference": predicted,
                        "hidden_info_used": False,
                        "classification": classification,
                        "error": error,
                    }
                    callback_key = (
                        replay_sha, seat, row["stage"], row["snapshot_sha256"]
                    )
                    if callback_key in callback_keys:
                        raise SystemExit("duplicate semantic first-Turbo callback key")
                    callback_keys.add(callback_key)
                    callback_rows.append(row)
                    if predicted:
                        differences.append(dict(row))
                    continue

                if transaction is None:
                    continue
                is_target = bool(
                    context == module._pcrd_int(module.SelectContext.ATTACH_FROM)
                    and effect_id == CINDERACE
                    and effect_serial == transaction["source_serial"]
                )
                if not is_target:
                    finalize(transaction, transaction_rows)
                    transaction = None
                    continue
                transaction["callback_rows"] += 1
                transaction["target_rows"] += 1
                if transaction["diverged_internal"]:
                    continue
                owners = tuple(sorted(set(pre_owners + post_owners)))
                rows, role_error = role_rows(module, obs)
                action, target_error, selected_row = choose_target_action(
                    module, obs, parent_action, rows
                )
                contract_valid = bool(
                    action is not None and module._cum_valid_action(obs, action)
                )
                contract_roles = (
                    module._pcrd_action_roles(obs, action)
                    if contract_valid else None
                )
                error = role_error or target_error
                predicted = bool(
                    not owners
                    and error is None
                    and parent_valid
                    and contract_valid
                    and canonical(contract_roles) != canonical(parent_roles)
                )
                parent_target = (
                    None
                    if not parent_roles or len(parent_roles) != 1
                    else parent_roles[0][2]
                )
                selected_target = (
                    None if selected_row is None else selected_row["target_serial"]
                )
                direction = "RETARGET_EXACT_ROLE_FILL" if predicted else (
                    "PARENT_EQUAL" if error is None and contract_valid else "DEFER_PARENT"
                )
                classification = "EXACT_COST_FILL" if predicted else (
                    "PARENT_EQUAL" if direction == "PARENT_EQUAL" else
                    "DEFER_OWNER" if owners else "UNKNOWN"
                )
                row = {
                    "replay": entry["replay"],
                    "replay_sha256": replay_sha,
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "turn_action_count": current.get("turnActionCount"),
                    "snapshot_sha256": raw_key[-1],
                    "context": context,
                    "stage": "ATTACH_FROM",
                    "effect_id": effect_id,
                    "effect_serial": effect_serial,
                    "context_energy_serial": module._pcrd_serial(obs.select.contextCard),
                    "attack_log_confirmed": True,
                    "first_turbo": True,
                    "pre_owners": canonical(pre_owners),
                    "post_owners": canonical(post_owners),
                    "h3_owned": h3_owned(owners),
                    "min_count": obs.select.minCount,
                    "max_count": obs.select.maxCount,
                    "bench_snapshot": canonical(rows),
                    "legal_semantics": canonical(option_semantics(module, obs)),
                    "parent_action": canonical(parent_action),
                    "parent_semantic": canonical(parent_roles),
                    "parent_valid": parent_valid,
                    "contract_action": canonical(action),
                    "contract_semantic": canonical(contract_roles),
                    "contract_valid": contract_valid,
                    "desired_energy_count": transaction["desired_energy_count"],
                    "selected_energy_serials": canonical(
                        transaction["selected_energy_serials_internal"]
                    ),
                    "target_id": None if selected_row is None else selected_row["target_id"],
                    "target_serial": selected_target,
                    "role_attack_id": None if selected_row is None else selected_row["role_attack_id"],
                    "role_cost": None if selected_row is None else selected_row["role_cost"],
                    "missing_before": None if selected_row is None else selected_row["missing"],
                    "missing_after": None if selected_row is None else max(0, selected_row["missing"] - 1),
                    "parent_vector": canonical({"target_serial": parent_target}),
                    "contract_vector": canonical({"target_serial": selected_target}),
                    "direction": direction,
                    "predicted_difference": predicted,
                    "hidden_info_used": False,
                    "classification": classification,
                    "error": error,
                }
                callback_key = (
                    replay_sha, seat, row["stage"], row["snapshot_sha256"]
                )
                if callback_key in callback_keys:
                    raise SystemExit("duplicate semantic first-Turbo callback key")
                callback_keys.add(callback_key)
                callback_rows.append(row)
                if not parent_valid:
                    transaction["parent_valid"] = False
                    transaction["parent_equal"] = False
                if not contract_valid:
                    transaction["contract_valid"] = False
                    transaction["parent_equal"] = False
                if owners:
                    transaction["owner_clear"] = False
                    transaction["parent_equal"] = False
                    transaction["classification"] = "DEFER_OWNER"
                    transaction["direction"] = "DEFER_PARENT"
                    transaction["h3_owned"] = bool(
                        transaction["h3_owned"] or h3_owned(owners)
                    )
                if predicted:
                    differences.append(dict(row))
                    transaction["predicted_difference"] = True
                    transaction["difference_stage"] = "ATTACH_FROM"
                    transaction["classification"] = classification
                    transaction["direction"] = direction
                    transaction["parent_equal"] = False
                    transaction["diverged_internal"] = True
                elif error is not None and error != "equal_role_targets_preserve_parent":
                    transaction["rejection_reason"] = error
                    transaction["parent_equal"] = False
            finalize(transaction, transaction_rows)

    if manifest_mismatches:
        raise SystemExit("manifest mismatch")

    for row in transaction_rows:
        for field in TRANSACTION_FIELDS:
            row.setdefault(field, None)
    for row in callback_rows:
        for field in CALLBACK_FIELDS:
            row.setdefault(field, None)
    for row in differences:
        for field in CALLBACK_FIELDS:
            row.setdefault(field, None)

    with (OUTPUT / "first_turbo_callback_rows.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=CALLBACK_FIELDS)
        writer.writeheader()
        writer.writerows(callback_rows)
    with (OUTPUT / "first_turbo_transaction_rows.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=TRANSACTION_FIELDS)
        writer.writeheader()
        writer.writerows(transaction_rows)
    with (OUTPUT / "predicted_first_differences.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=CALLBACK_FIELDS)
        writer.writeheader()
        writer.writerows(differences)

    natural = [row for row in transaction_rows]
    predicted = [row for row in transaction_rows if row["predicted_difference"] is True]
    controls = [row for row in transaction_rows if row["parent_equal"] is True]
    exact_cost = [
        row for row in predicted
        if row["classification"] in {"EXACT_COST_FILL", "OVERFILL_AVOIDANCE"}
    ]
    predicted_callbacks = [row for row in callback_rows if row["predicted_difference"]]
    violations = {
        "invalid_contract_actions": sum(
            not row["contract_valid"] for row in predicted_callbacks
        ),
        "hidden_information": sum(row["hidden_info_used"] for row in predicted_callbacks),
        "h3_changes": sum(row["h3_owned"] for row in predicted_callbacks),
        "owner_collisions": sum(
            row["pre_owners"] != "[]" or row["post_owners"] != "[]"
            for row in predicted_callbacks
        ),
        "non_turbo_changes": sum(
            row["effect_id"] != CINDERACE
            or row["stage"] not in {"ATTACH_TO", "ATTACH_FROM"}
            for row in predicted_callbacks
        ),
        "semantic_copy_noise": sum(
            row["predicted_difference"]
            and row["parent_semantic"] == row["contract_semantic"]
            for row in predicted_callbacks
        ),
    }
    gate = {
        "integrity": bool(
            len(manifest) == 207
            and target_seats == 209
            and calls == 25880
            and len(raw_keys) == calls
            and len(callback_keys) == len(callback_rows)
            and invalid_parent == 0
            and not manifest_mismatches
        ),
        "natural_support": bool(
            len(natural) >= 80
            and len({row["replay"] for row in natural}) >= 64
            and {int(row["seat"]) for row in natural} == {0, 1}
        ),
        "predicted_differences": bool(
            len(predicted) >= 16
            and len(predicted_callbacks) >= 24
            and len({row["replay"] for row in predicted}) >= 12
            and {int(row["seat"]) for row in predicted} == {0, 1}
        ),
        "exact_cost_or_overfill": len(exact_cost) >= 8,
        "negative_controls": bool(
            len(controls) >= 16
            and sum(int(row["callback_rows"]) for row in controls) >= 24
            and {int(row["seat"]) for row in controls} == {0, 1}
        ),
        "zero_violations": not any(violations.values()),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "integrity": {
            "replays": len(manifest),
            "target_seats": target_seats,
            "parent_calls": calls,
            "unique_raw_keys": len(raw_keys),
            "unique_semantic_callback_keys": len(callback_keys),
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
            "callback_rows": len(callback_rows),
            "transaction_rows": len(transaction_rows),
            "predicted_difference_rows": len(differences),
        },
        "transactions": {
            "natural": len(natural),
            "replays": len({row["replay"] for row in natural}),
            "seats": sorted({int(row["seat"]) for row in natural}),
            "predicted": len(predicted),
            "predicted_callbacks": len(predicted_callbacks),
            "predicted_replays": len({row["replay"] for row in predicted}),
            "predicted_seats": sorted({int(row["seat"]) for row in predicted}),
            "parent_equal_controls": len(controls),
            "exact_cost_or_overfill": len(exact_cost),
            "classification": dict(Counter(row["classification"] for row in natural)),
            "direction": dict(Counter(row["direction"] for row in natural)),
        },
        "violations": violations,
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "decision_if_gate_fails": "STOP__FIRST_TURBO_EXACT_ROLE_FILL_NOT_ACTIONABLE",
        "root_qualitative_audit": "PENDING",
        "errors": all_errors,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
