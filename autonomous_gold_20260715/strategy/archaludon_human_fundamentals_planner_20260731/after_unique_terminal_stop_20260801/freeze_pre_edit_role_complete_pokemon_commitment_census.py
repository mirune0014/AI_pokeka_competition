from __future__ import annotations

import copy
import csv
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLANNER = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
PARENT = ROOT / "autonomous_gold_20260715" / "candidates" / (
    "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = ROOT / "autonomous_gold_20260715" / "live" / "55070349" / (
    "refresh_20260729_1241"
) / "shadow_corpus_196_prior_plus_11_new"
TERMINAL_RUNNER = PLANNER / "next_after_search_guard_no_actionable_boundary_20260801" / (
    "freeze_pre_edit_unique_terminal_attack_census.py"
)
MANIFEST = PLANNER / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw/source_manifest.json"
)
STRATEGY = HERE / (
    "STRATEGY_SELECTION_PUBLIC_ROLE_COMPLETE_POKEMON_COMMITMENT_DOMINANCE_V1.md"
)
TERMINAL_STOP = PLANNER / "next_after_search_guard_no_actionable_boundary_20260801" / (
    "ROOT_PUBLIC_UNIQUE_TERMINAL_ATTACK_CENSUS_VERIFICATION.md"
)
TERMINAL_AUDIT = PLANNER / "next_after_search_guard_no_actionable_boundary_20260801" / (
    "_local_generated/analysis_outputs/PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_V1_INDEPENDENT_AUDIT.md"
)
OUTPUT = HERE / "pre_edit_role_complete_pokemon_commitment_census_raw"

EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "terminal_runner": "1F52AA13AC94105C0226BD0E14263938EF45CB870A46D63E201B43C45756A0B4",
    "strategy": "B0223A65081382006E64277F60EC8D17D6A0BF5E8231667BDA11ECAA517AD4B4",
    "terminal_stop": "DC8A74945964896603583AECA068B80661DD231FE9759C05BE3441EFCE56D77E",
    "terminal_audit": "F41954FFA3538D77B1495FDAF153EC15F9FE1499BFF7E27CF220FBD718B57B69",
}

FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "turn_action_count", "snapshot_sha256", "context", "min_count",
    "max_count", "result", "clear_main", "forced", "option_multiset",
    "pre_owner_vector", "post_owner_vector", "parent_started_owner",
    "parent_action", "parent_semantic", "parent_valid",
    "parent_action_family", "parent_card_id", "parent_card_serial",
    "owner_collision", "basic_play_count", "basic_plan_ids",
    "basic_plan_serials", "active_id", "active_serial", "target_id",
    "target_serial", "bench_count", "bench_max", "hand_count",
    "current_attack_count", "current_attack_id", "current_attack_semantic",
    "current_payment", "current_oracle", "current_final_damage",
    "current_ko", "current_prize_yield", "current_terminal",
    "current_threat_metrics", "post_attack_equal", "per_basic_roles",
    "role_labels", "contract_action", "contract_semantic",
    "contract_valid", "raw_redundant_play", "predicted_difference",
    "duplicate_retry", "first_causal_difference",
    "unreachable_after_first_difference", "classification",
    "rejection_reason", "hidden_info_used", "terminal_rule_recreation",
    "error",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_basic_options(module, obs):
    result = []
    for position, option in enumerate(obs.select.option):
        if option.type != module.OptionType.PLAY:
            continue
        card = module.option_card(obs, option)
        card_id = module._pcrd_get(card, "id")
        data = module.CARD_DB.get(card_id)
        if data is None or not bool(module._pcrd_get(data, "basic")):
            continue
        serial = module._pcrd_serial(card)
        result.append({
            "position": position,
            "card_id": card_id,
            "serial": serial,
            "role": module._pcrd_option_role(obs, option),
        })
    return tuple(result)


def project_basic_play(module, obs, plan):
    if plan["serial"] is None:
        return None, "basic_serial_unknown"
    projected = copy.deepcopy(obs)
    mine = module.my_state(projected)
    hand = list(tuple(mine.hand or ()))
    matches = [
        index for index, card in enumerate(hand)
        if module._pcrd_serial(card) == plan["serial"]
        and module._pcrd_get(card, "id") == plan["card_id"]
    ]
    if len(matches) != 1:
        return None, "basic_hand_binding_not_unique"
    bench = list(tuple(mine.bench or ()))
    bench_max = module._pcrd_int(module._pcrd_get(mine, "benchMax"))
    if bench_max is None or len(bench) >= bench_max:
        return None, "bench_capacity_unknown_or_full"
    card = copy.deepcopy(hand.pop(matches[0]))
    data = module.CARD_DB.get(plan["card_id"])
    active = module.active_pokemon(projected)
    hp = module._pcrd_int(module._pcrd_get(data, "hp"))
    if data is None or active is None or hp is None or hp <= 0:
        return None, "basic_in_play_metadata_unknown"
    pokemon_class = type(active)
    try:
        played = pokemon_class(
            id=plan["card_id"], serial=plan["serial"], hp=hp, maxHp=hp,
            appearThisTurn=True, energies=[], energyCards=[], tools=[],
            preEvolution=[],
        )
    except Exception:
        return None, "basic_in_play_construction_failed"
    bench.append(played)
    mine.hand[:] = hand
    mine.bench[:] = bench
    hand_count = module._pcrd_int(module._pcrd_get(mine, "handCount"))
    if hand_count is not None:
        mine.handCount = max(0, hand_count - 1)
    # The real next MAIN callback no longer offers the consumed PLAY option.
    # Retaining that stale hand-bound option would duplicate the physical
    # serial now on the Bench and make the public reply graph unknowable.
    projected.select.option[:] = [
        copy.deepcopy(option)
        for option in obs.select.option
        if option.type == module.OptionType.ATTACK
    ]
    projected.select.minCount = 1
    projected.select.maxCount = 1
    return projected, None


def certificate_fingerprint(common, row):
    certificate = row["certificate"]
    keys = (
        "status", "effect_id", "source_id", "source_serial",
        "source_stage", "source_type", "attack_id", "attack_name",
        "attack_mode", "attack_damage", "payment", "readiness",
        "target_id", "target_serial", "target_hp", "target_max_hp",
        "weakness", "resistance", "weakness_suppressed",
        "full_metal_lab", "cape_count", "coated_prevention",
        "printed_or_formula_damage", "final_damage", "remaining_hp", "ko",
        "sturdy_applied", "prize_yield", "printed_prize_yield",
        "bench_components", "target_attack_effects_prevented",
        "post_damage_counter_return", "post_attack_resource_ledger",
        "post_reply_resource_ledger", "persistent_effects",
        "persistent_progress", "run_away_draw_executable",
        "attacker_survival", "next_payable_attack",
        "next_payable_attack_ids", "exact_backup_conversion",
        "saved_callback_transaction", "pipeline", "unsupported_text",
        "assumptions", "consumers_updated",
    )
    return common.canonical({key: certificate.get(key) for key in keys})


def exact_threat_metrics(module, active, graph):
    if not isinstance(graph, dict) or not bool(graph.get("complete")):
        return None
    metrics = module._pcrd_attack_effective_hp_metrics(active, graph)
    if not isinstance(metrics, dict) or any(value is None for value in metrics.values()):
        return None
    return metrics


def reply_improved(before, after):
    if before is None or after is None:
        return None
    if after["current_attacker_survival"] and not before["current_attacker_survival"]:
        return True
    for key in ("certain_terminal_routes", "certain_return_prizes", "one_attach_ko_routes"):
        if after[key] < before[key]:
            return True
    before_hits = before["hits_to_ko"]
    after_hits = after["hits_to_ko"]
    if isinstance(before_hits, (int, float)) and isinstance(after_hits, (int, float)):
        if after_hits > before_hits:
            return True
    return False


def visible_evolution_conversion(module, obs, plan):
    if plan["card_id"] != module.DURALUDON:
        return False
    mine = module.my_state(obs)
    hand = tuple(mine.hand or ())
    discard = tuple(mine.discard or ())
    ex_count = sum(module._pcrd_get(card, "id") == module.ARCHALUDON_EX for card in hand)
    if ex_count == 0:
        return False
    metal_hand = sum(
        module._pcrd_get(card, "id") == module.METAL_ENERGY
        and module._pcrd_serial(card) != plan["serial"]
        for card in hand
    )
    metal_discard = sum(
        module._pcrd_get(card, "id") == module.METAL_ENERGY
        for card in discard
    )
    attach_windows = 1 + (0 if bool(obs.current.energyAttached) else 1)
    manual = min(metal_hand, attach_windows)
    alloy = min(2, metal_discard)
    return manual + alloy >= 3


def existing_ready_backup(module, obs, target):
    stadium = module._pcrd_stadium_state(obs)
    if not isinstance(stadium, dict) or stadium.get("status") != "EXACT":
        return None
    return module._pcrd_backup_readiness(obs, target, stadium)


def one_prize_wall_role(module, obs, graph, plan):
    if plan["card_id"] != module.DURALUDON:
        return False
    active = module.active_pokemon(obs)
    active_prize = None if active is None else module._h2_visible_prize_value(active)
    if active is None or active_prize is None or active_prize < 2:
        return False
    for pokemon in tuple(module.my_state(obs).bench or ()):
        if pokemon is not None and module._h2_visible_prize_value(pokemon) == 1:
            return False
    if not isinstance(graph, dict) or not graph.get("complete"):
        return None
    for route in tuple(graph.get("routes", ())):
        certificate = route.get("certificate") or {}
        if (
            route.get("tier") in {
                module._PCRD_READY_NOW, module._PCRD_KNOWN_PUBLIC_RESOURCE,
            }
            and certificate.get("status") == "EXACT"
            and bool(certificate.get("ko"))
        ):
            return True
    return False


def plan_roles(module, common, obs, current_row, current_metrics, plan):
    projected, project_error = project_basic_play(module, obs, plan)
    if project_error is not None:
        return None, None, project_error
    if plan["card_id"] != module.DURALUDON:
        return None, None, "non_duraludon_basic_role_not_exhaustive"
    post_rows, reason = module._pfgear_current_attack_rows(
        projected, allow_duplicate_ui=True
    )
    if post_rows is None:
        return None, None, reason or "post_play_attack_unknown"
    matching = [
        row for row in post_rows
        if row["attack_id"] == current_row["attack_id"]
    ]
    if len(matching) != 1:
        return None, None, "post_play_same_attack_not_unique"
    post_row = matching[0]
    post_active = module.active_pokemon(projected)
    post_metrics = exact_threat_metrics(
        module, post_active, post_row["threat_graph"]
    )
    improvement = reply_improved(current_metrics, post_metrics)
    if improvement is None:
        return None, None, "reply_metric_unknown"
    same_attack = bool(
        common.canonical(current_row["payment"])
        == common.canonical(post_row["payment"])
        and certificate_fingerprint(common, current_row)
        == certificate_fingerprint(common, post_row)
    )
    roles = []
    mine = module.my_state(obs)
    target = module.opp_active_pokemon(obs)
    if len(tuple(mine.bench or ())) == 0:
        roles.append("BOARD_OUT_PROTECTION")
    if current_row["attack_id"] == 965:
        roles.append("ACCELERATION_RECIPIENT")
    conversion = visible_evolution_conversion(module, obs, plan)
    if conversion:
        roles.append("EVOLUTION_ATTACHMENT_CONVERSION")
        ready = existing_ready_backup(module, obs, target)
        if ready is None:
            return None, None, "existing_backup_unknown"
        if not ready:
            roles.append("FIRST_EXECUTABLE_BACKUP")
    wall = one_prize_wall_role(module, obs, current_row["threat_graph"], plan)
    if wall is None:
        return None, None, "one_prize_wall_reply_unknown"
    if wall:
        roles.append("ONE_PRIZE_WALL")
    if improvement:
        roles.append("EXACT_REPLY_IMPROVEMENT")
    if not same_attack:
        roles.append("ATTACK_EFFECT_CHANGE")
    return tuple(sorted(set(roles))), same_attack, None


def main():
    if OUTPUT.exists():
        raise SystemExit("refusing to reuse Pokemon-commitment census destination")
    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "deck": sha256(PARENT / "deck.csv"),
        "manifest": sha256(MANIFEST),
        "terminal_runner": sha256(TERMINAL_RUNNER),
        "strategy": sha256(STRATEGY),
        "terminal_stop": sha256(TERMINAL_STOP),
        "terminal_audit": sha256(TERMINAL_AUDIT),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input hash mismatch: " + json.dumps(actual_hashes, sort_keys=True))
    OUTPUT.mkdir(parents=False, exist_ok=False)
    (OUTPUT / "source_manifest.json").write_bytes(MANIFEST.read_bytes())

    terminal = load_module("commitment_terminal", TERMINAL_RUNNER)
    common = terminal.load_module("commitment_common", terminal.COMMON)
    helper = common.load_module("commitment_helper", terminal.HELPER)
    module = helper.load_parent()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    opportunities = []
    causal_rows = []
    retry_rows = {}
    raw_keys = set()
    calls = 0
    target_seats = 0
    invalid_parent = 0
    manifest_mismatches = []
    duplicate_retries = 0
    nonidentical_retries = 0

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
            causal_seen = False
            for step_index, step in enumerate(replay["steps"]):
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat or raw.get("select") is None:
                    continue
                calls += 1
                snapshot = common.digest(raw)
                raw_key = (entry["replay"], seat, step_index, current.get("turn"), snapshot)
                if raw_key in raw_keys:
                    raise SystemExit("duplicate raw callback key")
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = terminal.owner_vector(module, common)
                parent_action = module.agent(copy.deepcopy(raw))
                post_owners = terminal.owner_vector(module, common)
                parent_valid = bool(module._cum_valid_action(obs, parent_action))
                parent_semantic = module._pcrd_action_roles(obs, parent_action) if parent_valid else None
                if not parent_valid or parent_semantic is None:
                    invalid_parent += 1
                family, parent_card_id = terminal.parent_family(module, obs, parent_action)
                option = terminal.parent_option(module, obs, parent_action)
                parent_card = module.option_card(obs, option) if option is not None else None
                parent_serial = module._pcrd_serial(parent_card)
                clear = common.clear_main(module, obs)
                forced = bool(obs.select.minCount == obs.select.maxCount and len(obs.select.option) == obs.select.minCount)
                owner_collision = bool(pre_owners or post_owners)
                basic_plans = public_basic_options(module, obs) if clear else ()
                active = module.active_pokemon(obs)
                target = module.opp_active_pokemon(obs)
                mine = module.my_state(obs)

                current_row = None
                attack_row_count = None
                current_metrics = None
                current_terminal = False
                rejection = None
                per_basic_roles = []
                all_roles = set()
                post_equal = None
                raw_redundant = False
                predicted = False
                first_causal = False
                contract_action = list(parent_action)
                contract_semantic = parent_semantic
                contract_valid = parent_valid
                error = None

                is_parent_pokemon = bool(family == "PLAY_POKEMON")
                if not is_parent_pokemon:
                    classification = "NON_POKEMON_PARENT"
                elif not clear:
                    classification = "NON_CLEAR_POKEMON_HOLD"; rejection = "non_clear_main"
                elif owner_collision:
                    classification = "OWNER_POKEMON_HOLD"; rejection = "owner_collision"
                elif parent_card_id != module.DURALUDON:
                    classification = "NON_DURALUDON_PARENT_HOLD"; rejection = "parent_basic_not_duraludon"
                elif not basic_plans or any(plan["serial"] is None for plan in basic_plans):
                    classification = "BASIC_BINDING_HOLD"; rejection = "basic_option_binding_unknown"
                else:
                    attack_rows, attack_error = module._pfgear_current_attack_rows(obs, allow_duplicate_ui=True)
                    if attack_rows is None:
                        classification = "ATTACK_UNKNOWN_HOLD"; rejection = attack_error or "attack_rows_unknown"
                    else:
                        attack_row_count = len(attack_rows)
                    if attack_rows is not None and len(attack_rows) != 1:
                        classification = "ATTACK_NOT_UNIQUE_HOLD"; rejection = "current_attack_semantic_count_not_one"
                    elif attack_rows is not None:
                        current_row = attack_rows[0]
                        certificate = current_row["certificate"]
                        remaining = len(tuple(mine.prize or ()))
                        opponent_bench = len(tuple(card for card in tuple(module.opp_state(obs).bench or ()) if card is not None))
                        current_terminal = bool(certificate.get("ko")) and (
                            module._pcrd_int(certificate.get("prize_yield")) >= remaining
                            or opponent_bench == 0
                        )
                        if current_terminal:
                            classification = "CURRENT_TERMINAL_EXCLUDED"; rejection = "stopped_terminal_rule_not_recreated"
                        else:
                            current_metrics = exact_threat_metrics(module, active, current_row["threat_graph"])
                            if current_metrics is None:
                                classification = "REPLY_UNKNOWN_HOLD"; rejection = "current_reply_metric_unknown"
                            else:
                                plan_error = None
                                equal_rows = []
                                for plan in basic_plans:
                                    roles, same_attack, plan_error = plan_roles(module, common, obs, current_row, current_metrics, plan)
                                    if plan_error is not None:
                                        break
                                    per_basic_roles.append((plan["card_id"], plan["serial"], roles))
                                    all_roles.update(roles)
                                    equal_rows.append(bool(same_attack))
                                if plan_error is not None:
                                    classification = "ROLE_UNKNOWN_HOLD"; rejection = plan_error
                                elif all_roles:
                                    post_equal = all(equal_rows)
                                    classification = "PLAY_HAS_PUBLIC_ROLE"
                                else:
                                    post_equal = all(equal_rows)
                                    raw_redundant = True
                                    if causal_seen:
                                        classification = "UNREACHABLE_REDUNDANT_PLAY"
                                    else:
                                        attack_action, attack_semantic, bind_error = terminal.bind_terminal(
                                            module, obs, current_row
                                        )
                                        if bind_error is not None:
                                            classification = "ATTACK_BINDING_HOLD"; rejection = bind_error
                                        else:
                                            contract_action = attack_action
                                            contract_semantic = attack_semantic
                                            contract_valid = bool(module._cum_valid_action(obs, contract_action))
                                            predicted = contract_valid and common.canonical(parent_semantic) != common.canonical(contract_semantic)
                                            first_causal = predicted
                                            classification = "REDUNDANT_POKEMON_PLAY" if predicted else "ATTACK_BINDING_HOLD"
                                            if predicted:
                                                causal_seen = True
                                            else:
                                                error = "redundant_contract_invalid_or_equal"

                row = {
                    "replay": entry["replay"], "replay_sha256": replay_sha,
                    "seat": seat, "step": step_index, "turn": current.get("turn"),
                    "turn_action_count": current.get("turnActionCount"),
                    "snapshot_sha256": snapshot,
                    "context": module._pcrd_int(obs.select.context),
                    "min_count": obs.select.minCount, "max_count": obs.select.maxCount,
                    "result": current.get("result"), "clear_main": clear,
                    "forced": forced, "option_multiset": terminal.option_multiset(module, obs),
                    "pre_owner_vector": pre_owners, "post_owner_vector": post_owners,
                    "parent_started_owner": bool(not pre_owners and post_owners),
                    "parent_action": parent_action, "parent_semantic": parent_semantic,
                    "parent_valid": parent_valid, "parent_action_family": family,
                    "parent_card_id": parent_card_id, "parent_card_serial": parent_serial,
                    "owner_collision": owner_collision, "basic_play_count": len(basic_plans),
                    "basic_plan_ids": tuple(plan["card_id"] for plan in basic_plans),
                    "basic_plan_serials": tuple(plan["serial"] for plan in basic_plans),
                    "active_id": module._pcrd_get(active, "id"), "active_serial": module._pcrd_serial(active),
                    "target_id": module._pcrd_get(target, "id"), "target_serial": module._pcrd_serial(target),
                    "bench_count": len(tuple(mine.bench or ())), "bench_max": module._pcrd_get(mine, "benchMax"),
                    "hand_count": module._pcrd_get(mine, "handCount"),
                    "current_attack_count": attack_row_count,
                    "current_attack_id": None if current_row is None else current_row["attack_id"],
                    "current_attack_semantic": None if current_row is None else current_row["role"],
                    "current_payment": None if current_row is None else current_row["payment"],
                    "current_oracle": None if current_row is None else current_row["certificate"].get("status"),
                    "current_final_damage": None if current_row is None else current_row["certificate"].get("final_damage"),
                    "current_ko": None if current_row is None else bool(current_row["certificate"].get("ko")),
                    "current_prize_yield": None if current_row is None else current_row["certificate"].get("prize_yield"),
                    "current_terminal": current_terminal, "current_threat_metrics": current_metrics,
                    "post_attack_equal": post_equal, "per_basic_roles": tuple(per_basic_roles),
                    "role_labels": tuple(sorted(all_roles)), "contract_action": contract_action,
                    "contract_semantic": contract_semantic, "contract_valid": contract_valid,
                    "raw_redundant_play": raw_redundant, "predicted_difference": predicted,
                    "duplicate_retry": False, "first_causal_difference": first_causal,
                    "unreachable_after_first_difference": bool(causal_seen and not first_causal),
                    "classification": classification, "rejection_reason": rejection,
                    "hidden_info_used": False, "terminal_rule_recreation": False,
                    "error": error,
                }
                retry_key = (replay_sha, seat, row["context"], snapshot)
                prior = retry_rows.get(retry_key)
                if prior is not None:
                    duplicate_retries += 1
                    row["duplicate_retry"] = True
                    invariant = (
                        "turn", "turn_action_count", "result", "option_multiset",
                        "parent_action", "parent_semantic", "parent_valid",
                        "pre_owner_vector", "post_owner_vector", "current_attack_id",
                        "current_oracle", "current_terminal", "role_labels",
                        "raw_redundant_play", "rejection_reason", "error",
                    )
                    if any(common.canonical(prior[key]) != common.canonical(row[key]) for key in invariant):
                        nonidentical_retries += 1
                        raise SystemExit("non-identical Pokemon-commitment retry")
                    if prior["classification"] in {"REDUNDANT_POKEMON_PLAY", "DUPLICATE_REDUNDANT_RETRY"}:
                        row["contract_action"] = copy.deepcopy(prior["contract_action"])
                        row["contract_semantic"] = copy.deepcopy(prior["contract_semantic"])
                        row["contract_valid"] = prior["contract_valid"]
                        row["predicted_difference"] = False
                        row["first_causal_difference"] = False
                        row["unreachable_after_first_difference"] = False
                        row["classification"] = "DUPLICATE_REDUNDANT_RETRY"
                    elif any(
                        common.canonical(prior[key]) != common.canonical(row[key])
                        for key in ("contract_action", "contract_semantic", "contract_valid", "classification")
                    ):
                        nonidentical_retries += 1
                        raise SystemExit("non-identical Pokemon-commitment hold retry")
                else:
                    retry_rows[retry_key] = copy.deepcopy(row)
                for field in FIELDS:
                    value = row.get(field)
                    if isinstance(value, (dict, list, tuple, set, frozenset)):
                        row[field] = common.canonical(value)
                    else:
                        row.setdefault(field, None)
                rows.append(row)
                if is_parent_pokemon:
                    opportunities.append(dict(row))
                if first_causal:
                    causal_rows.append(dict(row))

    if manifest_mismatches:
        raise SystemExit("manifest mismatch")
    for filename, data in (
        ("all_callback_rows.csv", rows),
        ("pokemon_commitment_opportunities.csv", opportunities),
        ("causal_first_differences.csv", causal_rows),
    ):
        with (OUTPUT / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(data)

    classifiable = [
        row for row in opportunities
        if row["classification"] in {
            "REDUNDANT_POKEMON_PLAY", "UNREACHABLE_REDUNDANT_PLAY",
            "PLAY_HAS_PUBLIC_ROLE",
        }
        and row["duplicate_retry"] is False
    ]
    controls = [row for row in opportunities if row["classification"] == "PLAY_HAS_PUBLIC_ROLE"]
    role_counts = Counter()
    for row in controls:
        for role in json.loads(row["role_labels"]):
            role_counts[role] += 1
    causal_attack_ids = {row["current_attack_id"] for row in causal_rows}
    violations = {
        "invalid_parent_actions": invalid_parent,
        "invalid_contract_actions": sum(row["contract_valid"] is not True for row in causal_rows),
        "hidden_information": sum(row["hidden_info_used"] is True for row in causal_rows),
        "owner_collisions": sum(row["owner_collision"] is True for row in causal_rows),
        "terminal_rule_recreation": sum(row["terminal_rule_recreation"] is True or row["current_terminal"] is True for row in causal_rows),
        "semantic_copy_predictions": sum(row["parent_semantic"] == row["contract_semantic"] for row in causal_rows),
        "predicted_errors": sum(bool(row["error"]) for row in causal_rows),
        "nonidentical_retries": nonidentical_retries,
    }
    orientation = {
        "rows": len(opportunities),
        "turns": len({(row["replay"], row["seat"], row["turn"]) for row in opportunities}),
        "replays": len({row["replay"] for row in opportunities}),
        "card_ids": dict(Counter(row["parent_card_id"] for row in opportunities)),
        "owner_free_rows": sum(row["owner_collision"] is False for row in opportunities),
    }
    required_role_groups = {
        "FIRST_EXECUTABLE_BACKUP", "BOARD_OUT_PROTECTION",
        "ACCELERATION_RECIPIENT", "EVOLUTION_ATTACHMENT_CONVERSION",
        "ONE_PRIZE_WALL", "EXACT_REPLY_IMPROVEMENT",
    }
    covered_role_groups = set(role_counts) & required_role_groups
    gate = {
        "integrity": bool(len(manifest) == 207 and target_seats == 209 and calls == 25880 and len(raw_keys) == calls and invalid_parent == 0),
        "orientation": bool(orientation["rows"] == 700 and orientation["turns"] == 523 and orientation["replays"] == 201 and orientation["card_ids"] == {module.DURALUDON: 700} and orientation["owner_free_rows"] == 696),
        "classifiable_surface": bool(len(classifiable) >= 64 and len({row["replay"] for row in classifiable}) >= 40 and {row["seat"] for row in classifiable} == {0, 1}),
        "causal_volume": bool(len(causal_rows) >= 32 and len({row["replay"] for row in causal_rows}) >= 24 and all(sum(row["seat"] == seat for row in causal_rows) >= 12 for seat in (0, 1))),
        "positive_controls": bool(len(controls) >= 48 and len({row["replay"] for row in controls}) >= 32 and {row["seat"] for row in controls} == {0, 1}),
        "role_breadth": len(covered_role_groups) >= 3,
        "attack_and_ko_breadth": bool(len(causal_attack_ids) >= 2 and {row["current_ko"] for row in causal_rows} == {False, True}),
        "zero_violations": not any(violations.values()),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "integrity": {
            "replays": len(manifest), "target_seats": target_seats,
            "parent_calls": calls, "unique_raw_keys": len(raw_keys),
            "callback_rows": len(rows), "duplicate_retries": duplicate_retries,
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
        },
        "orientation": orientation,
        "census": {
            "classifiable_rows": len(classifiable),
            "classifiable_replays": len({row["replay"] for row in classifiable}),
            "classifiable_seats": sorted({row["seat"] for row in classifiable}),
            "causal_rows": len(causal_rows),
            "causal_replays": len({row["replay"] for row in causal_rows}),
            "causal_seats": dict(Counter(row["seat"] for row in causal_rows)),
            "causal_attack_ids": sorted(causal_attack_ids),
            "causal_ko": dict(Counter(row["current_ko"] for row in causal_rows)),
            "controls": len(controls),
            "control_replays": len({row["replay"] for row in controls}),
            "control_seats": sorted({row["seat"] for row in controls}),
            "role_counts": dict(role_counts),
            "covered_required_roles": sorted(covered_role_groups),
            "classification": dict(Counter(row["classification"] for row in opportunities)),
            "rejections": dict(Counter(row["rejection_reason"] for row in opportunities if row["rejection_reason"])),
        },
        "violations": violations,
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "decision_if_gate_fails": "STOP__PUBLIC_ROLE_COMPLETE_POKEMON_COMMITMENT_NOT_BROADLY_ACTIONABLE",
        "root_qualitative_audit": "PENDING",
    }
    (OUTPUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
