from __future__ import annotations

import copy
import csv
from collections import Counter
import hashlib
import importlib.util
import json
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
MANIFEST = PLANNER / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw/source_manifest.json"
)
HELPER = PLANNER / "next_after_lillie_one_direction_fail_20260801" / (
    "freeze_pre_edit_jumbo_ice_cream_actionability_census.py"
)
COMMON = PLANNER / "next_after_first_turbo_no_actionable_boundary_20260801" / (
    "freeze_pre_edit_search_purpose_guard_census.py"
)
STRATEGY = HERE / (
    "STRATEGY_SELECTION_PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_V1.md"
)
SEARCH_STOP = PLANNER / "next_after_first_turbo_no_actionable_boundary_20260801" / (
    "ROOT_SEARCH_PURPOSE_GUARD_CENSUS_VERIFICATION.md"
)
OUTPUT = HERE / "pre_edit_unique_terminal_attack_census_raw"

EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "helper": "3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B",
    "common": "A60CDB559DBC0BC6B985654B3BCDC499F2C6D712F7795526D7DC190EE77803F8",
    "strategy": "7165420EB6F84BC28CFDC1096F9C8851B85196796B916015AC7B8696CB48EB43",
    "search_stop": "4CE04C09BCEA147DF80F90620BDB2CE91332D7154B9D883835C59E8F38ECAC9D",
}

FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "turn_action_count", "snapshot_sha256", "context", "min_count",
    "max_count", "result", "clear_main", "forced", "option_multiset",
    "pre_owner_vector", "post_owner_vector", "parent_started_owner",
    "parent_action", "parent_semantic", "parent_valid",
    "parent_action_family", "parent_card_id", "inherited_terminal_kind",
    "attacker_serial", "target_serial", "remaining_prizes",
    "opponent_bench_count", "legal_attack_semantics",
    "duplicate_attack_groups", "attack_access_statuses", "attack_payments",
    "oracle_statuses", "unsupported_reasons", "attack_damage", "attack_ko",
    "attack_prize_yield", "terminal_kind", "terminal_semantic_count",
    "terminal_attack_id", "contract_action", "contract_semantic",
    "contract_valid", "raw_terminal_replacement", "predicted_difference",
    "duplicate_retry", "first_causal_difference",
    "unreachable_after_terminal_override", "classification",
    "hidden_info_used", "owner_collision", "error",
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


def option_multiset(module, obs):
    return tuple(sorted(
        (module._pcrd_option_role(obs, option) for option in obs.select.option),
        key=repr,
    ))


def owner_vector(module, common):
    owners = list(common.live_owners(module))
    if getattr(module, "_dper_active_callback", None) is not None:
        owners.append("_dper_active_callback")
    return tuple(sorted(set(owners)))


def parent_option(module, obs, action):
    if (
        not module._cum_valid_action(obs, action)
        or len(action) != 1
        or not isinstance(action[0], int)
        or action[0] < 0
        or action[0] >= len(obs.select.option)
    ):
        return None
    return obs.select.option[action[0]]


def parent_family(module, obs, action):
    option = parent_option(module, obs, action)
    if option is None:
        return "OTHER_MAIN", None
    try:
        name = module.OptionType(option.type).name.upper()
    except (TypeError, ValueError):
        name = str(option.type).upper()
    card = module.option_card(obs, option)
    card_id = module._pcrd_get(card, "id")
    if option.type == module.OptionType.PLAY:
        data = module.CARD_DB.get(card_id)
        if data is not None and any(bool(module._pcrd_get(data, field)) for field in (
            "basic", "stage1", "stage2",
        )):
            return "PLAY_POKEMON", card_id
        if card_id in (module.POKE_PAD, module.ULTRA_BALL, module.POKEGEAR):
            return "PLAY_ITEM_SEARCH", card_id
        if card_id in (module.BOSS, module.EXPLORER, module.LILLIE):
            return "PLAY_SUPPORTER", card_id
        if card_id == module.FULL_METAL_LAB:
            return "PLAY_STADIUM", card_id
        if card_id == module.HERO_CAPE:
            return "PLAY_TOOL", card_id
        return "PLAY_ITEM_OTHER", card_id
    mapping = {
        "EVOLVE": "EVOLVE",
        "ATTACH": "ATTACH",
        "RETREAT": "RETREAT",
        "ABILITY": "ABILITY",
        "USE_ABILITY": "ABILITY",
        "END": "END",
        "ATTACK": "ATTACK",
    }
    return mapping.get(name, "OTHER_MAIN"), card_id


def telemetry_terminal_kind(module):
    telemetry = getattr(module, "_pfgear_last_telemetry", None)
    if not isinstance(telemetry, dict):
        return None
    source = telemetry.get("selected_source")
    return source if source in {
        "DIRECT_FINISH", "POSITIVE_GEAR_TRANSACTION",
        "REPEATED_GEAR_VETO",
    } else None


def terminal_scan(module, obs):
    active = module.active_pokemon(obs)
    target = module.opp_active_pokemon(obs)
    mine = module.my_state(obs)
    opponent = module.opp_state(obs)
    base = {
        "attacker_serial": module._pcrd_serial(active),
        "target_serial": module._pcrd_serial(target),
        "remaining_prizes": len(tuple(mine.prize or ())),
        "opponent_bench_count": len(tuple(
            card for card in tuple(opponent.bench or ()) if card is not None
        )),
        "legal_attack_semantics": (),
        "duplicate_attack_groups": (),
        "attack_access_statuses": (),
        "attack_payments": (),
        "oracle_statuses": (),
        "unsupported_reasons": (),
        "attack_damage": (),
        "attack_ko": (),
        "attack_prize_yield": (),
        "terminal_kind": None,
        "terminal_semantic_count": 0,
        "terminal_attack_id": None,
        "terminal_row": None,
    }
    raw_attacks = [
        (position, option)
        for position, option in enumerate(obs.select.option)
        if option.type == module.OptionType.ATTACK
    ]
    base["legal_attack_semantics"] = tuple(
        module._pcrd_option_role(obs, option) for _, option in raw_attacks
    )
    if not raw_attacks:
        return base, None
    rows, reason = module._pfgear_current_attack_rows(
        obs, allow_duplicate_ui=True
    )
    if rows is None:
        base["unsupported_reasons"] = (reason or "attack_rows_unknown",)
        return base, reason or "attack_rows_unknown"
    base["duplicate_attack_groups"] = tuple(
        (row["attack_id"], len(tuple(row["positions"])))
        for row in rows if len(tuple(row["positions"])) > 1
    )
    base["attack_access_statuses"] = tuple(
        (row["attack_id"], "EXACT") for row in rows
    )
    base["attack_payments"] = tuple(
        (row["attack_id"], row["payment"]) for row in rows
    )
    base["oracle_statuses"] = tuple(
        (row["attack_id"], row["certificate"].get("status")) for row in rows
    )
    base["attack_damage"] = tuple(
        (row["attack_id"], row["certificate"].get("final_damage")) for row in rows
    )
    base["attack_ko"] = tuple(
        (row["attack_id"], bool(row["certificate"].get("ko"))) for row in rows
    )
    base["attack_prize_yield"] = tuple(
        (row["attack_id"], row["certificate"].get("prize_yield")) for row in rows
    )
    terminal = []
    for row in rows:
        certificate = row["certificate"]
        ko = bool(certificate.get("ko"))
        prize = module._pcrd_int(certificate.get("prize_yield"))
        damage = module._pcrd_int(certificate.get("final_damage"))
        if prize is None or damage is None:
            base["unsupported_reasons"] = (
                "terminal_damage_or_prize_unknown",
            )
            return base, "terminal_damage_or_prize_unknown"
        prize_terminal = ko and prize >= base["remaining_prizes"]
        board_terminal = ko and base["opponent_bench_count"] == 0
        if prize_terminal or board_terminal:
            terminal.append((row, prize_terminal, board_terminal))
    base["terminal_semantic_count"] = len(terminal)
    if len(terminal) == 1:
        row, prize_terminal, board_terminal = terminal[0]
        base["terminal_row"] = row
        base["terminal_attack_id"] = row["attack_id"]
        base["terminal_kind"] = (
            "PRIZE_AND_BOARD"
            if prize_terminal and board_terminal
            else "PRIZE_EXHAUSTION"
            if prize_terminal
            else "NO_OPPOSING_POKEMON"
        )
    return base, None


def bind_terminal(module, obs, terminal_row):
    if terminal_row is None:
        return None, None, "terminal_row_missing"
    positions = tuple(terminal_row.get("positions", ()))
    roles = tuple(
        module._pcrd_option_role(obs, obs.select.option[position])
        for position in positions
    )
    if not positions or len(set(roles)) != 1:
        return None, None, "terminal_binding_ambiguous"
    action = [min(positions)]
    if not module._cum_valid_action(obs, action):
        return None, None, "terminal_action_invalid"
    return action, module._pcrd_action_roles(obs, action), None


def main():
    if OUTPUT.exists():
        raise SystemExit("refusing to reuse terminal census destination")
    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "deck": sha256(PARENT / "deck.csv"),
        "manifest": sha256(MANIFEST),
        "helper": sha256(HELPER),
        "common": sha256(COMMON),
        "strategy": sha256(STRATEGY),
        "search_stop": sha256(SEARCH_STOP),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input hash mismatch: " + json.dumps(actual_hashes, sort_keys=True))
    OUTPUT.mkdir(parents=False, exist_ok=False)
    (OUTPUT / "source_manifest.json").write_bytes(MANIFEST.read_bytes())

    common = load_module("terminal_common", COMMON)
    helper = common.load_module("terminal_helper", HELPER)
    module = helper.load_parent()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    causal_rows = []
    raw_keys = set()
    semantic_retry_rows = {}
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
                raw_key = (
                    entry["replay"], seat, step_index,
                    current.get("turn"), snapshot,
                )
                if raw_key in raw_keys:
                    raise SystemExit("duplicate raw callback key")
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = owner_vector(module, common)
                parent_action = module.agent(copy.deepcopy(raw))
                post_owners = owner_vector(module, common)
                parent_valid = bool(module._cum_valid_action(obs, parent_action))
                parent_semantic = (
                    module._pcrd_action_roles(obs, parent_action)
                    if parent_valid else None
                )
                if not parent_valid or parent_semantic is None:
                    invalid_parent += 1
                family, parent_card_id = parent_family(
                    module, obs, parent_action
                )
                clear = common.clear_main(module, obs)
                forced = bool(
                    obs.select.minCount == obs.select.maxCount
                    and len(obs.select.option) == obs.select.minCount
                )
                owner_collision = bool(pre_owners or post_owners)
                started_owner = bool(not pre_owners and post_owners)
                scan = {
                    "attacker_serial": None, "target_serial": None,
                    "remaining_prizes": None, "opponent_bench_count": None,
                    "legal_attack_semantics": (), "duplicate_attack_groups": (),
                    "attack_access_statuses": (), "attack_payments": (),
                    "oracle_statuses": (), "unsupported_reasons": (),
                    "attack_damage": (), "attack_ko": (),
                    "attack_prize_yield": (), "terminal_kind": None,
                    "terminal_semantic_count": 0, "terminal_attack_id": None,
                    "terminal_row": None,
                }
                scan_error = None
                if clear and module._pcrd_all_public_serials(obs) is not None:
                    scan, scan_error = terminal_scan(module, obs)

                contract_action = list(parent_action)
                contract_semantic = parent_semantic
                contract_valid = parent_valid
                raw_replacement = False
                predicted = False
                first_causal = False
                unreachable = causal_seen
                error = None
                if not clear:
                    classification = "NON_CLEAR_PARENT"
                elif module._pcrd_all_public_serials(obs) is None:
                    classification = "PUBLIC_SERIALS_UNKNOWN_HOLD"
                elif scan_error is not None:
                    classification = "UNSUPPORTED_ATTACK_HOLD"
                elif scan["terminal_semantic_count"] == 0:
                    classification = "NO_TERMINAL_HOLD"
                elif scan["terminal_semantic_count"] > 1:
                    classification = "MULTIPLE_TERMINAL_HOLD"
                else:
                    attack_action, attack_semantic, bind_error = bind_terminal(
                        module, obs, scan["terminal_row"]
                    )
                    if bind_error is not None:
                        classification = "TERMINAL_BINDING_HOLD"
                        error = bind_error
                    else:
                        raw_replacement = (
                            common.canonical(parent_semantic)
                            != common.canonical(attack_semantic)
                        )
                        if owner_collision:
                            classification = "OWNER_TERMINAL_HOLD"
                        elif not raw_replacement:
                            classification = "PARENT_TERMINAL_HOLD"
                        elif causal_seen:
                            classification = "UNREACHABLE_AFTER_TERMINAL_OVERRIDE"
                        else:
                            contract_action = attack_action
                            contract_semantic = attack_semantic
                            contract_valid = bool(
                                module._cum_valid_action(obs, contract_action)
                            )
                            predicted = bool(contract_valid)
                            first_causal = predicted
                            classification = (
                                "TERMINAL_OVERRIDE"
                                if predicted else "TERMINAL_BINDING_HOLD"
                            )
                            if predicted:
                                causal_seen = True
                                unreachable = False
                            else:
                                error = "terminal_contract_invalid"

                row = {
                    "replay": entry["replay"],
                    "replay_sha256": replay_sha,
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "turn_action_count": current.get("turnActionCount"),
                    "snapshot_sha256": snapshot,
                    "context": module._pcrd_int(obs.select.context),
                    "min_count": obs.select.minCount,
                    "max_count": obs.select.maxCount,
                    "result": current.get("result"),
                    "clear_main": clear,
                    "forced": forced,
                    "option_multiset": option_multiset(module, obs),
                    "pre_owner_vector": pre_owners,
                    "post_owner_vector": post_owners,
                    "parent_started_owner": started_owner,
                    "parent_action": parent_action,
                    "parent_semantic": parent_semantic,
                    "parent_valid": parent_valid,
                    "parent_action_family": family,
                    "parent_card_id": parent_card_id,
                    "inherited_terminal_kind": telemetry_terminal_kind(module),
                    **{key: value for key, value in scan.items() if key != "terminal_row"},
                    "contract_action": contract_action,
                    "contract_semantic": contract_semantic,
                    "contract_valid": contract_valid,
                    "raw_terminal_replacement": raw_replacement,
                    "predicted_difference": predicted,
                    "duplicate_retry": False,
                    "first_causal_difference": first_causal,
                    "unreachable_after_terminal_override": unreachable,
                    "classification": classification,
                    "hidden_info_used": False,
                    "owner_collision": owner_collision,
                    "error": error,
                }
                retry_key = (
                    replay_sha, seat, row["context"], snapshot
                )
                prior = semantic_retry_rows.get(retry_key)
                if prior is not None:
                    duplicate_retries += 1
                    row["duplicate_retry"] = True
                    signature_fields = (
                        "turn", "turn_action_count", "result",
                        "option_multiset", "parent_action", "parent_semantic",
                        "parent_valid",
                        "pre_owner_vector", "post_owner_vector",
                        "terminal_semantic_count", "terminal_attack_id",
                        "terminal_kind", "error",
                    )
                    if any(
                        common.canonical(prior[field])
                        != common.canonical(row[field])
                        for field in signature_fields
                    ):
                        nonidentical_retries += 1
                        raise SystemExit("non-identical terminal callback retry")
                    if prior["classification"] in {
                        "TERMINAL_OVERRIDE", "DUPLICATE_TERMINAL_RETRY",
                    }:
                        # The contract requires an identical callback retry to
                        # rebind the same winning semantic.  It is not a new
                        # causal start and therefore must not inflate the
                        # earliest-difference census.
                        row["contract_action"] = copy.deepcopy(
                            prior["contract_action"]
                        )
                        row["contract_semantic"] = copy.deepcopy(
                            prior["contract_semantic"]
                        )
                        row["contract_valid"] = prior["contract_valid"]
                        row["raw_terminal_replacement"] = prior[
                            "raw_terminal_replacement"
                        ]
                        row["predicted_difference"] = False
                        row["first_causal_difference"] = False
                        row["unreachable_after_terminal_override"] = False
                        row["classification"] = "DUPLICATE_TERMINAL_RETRY"
                    elif any(
                        common.canonical(prior[field])
                        != common.canonical(row[field])
                        for field in (
                            "contract_action", "contract_semantic",
                            "contract_valid", "raw_terminal_replacement",
                            "predicted_difference", "classification",
                        )
                    ):
                        nonidentical_retries += 1
                        raise SystemExit(
                            "non-identical nonterminal callback retry"
                        )
                else:
                    semantic_retry_rows[retry_key] = copy.deepcopy(row)
                for field in FIELDS:
                    value = row.get(field)
                    if isinstance(value, (dict, list, tuple, set, frozenset)):
                        row[field] = common.canonical(value)
                    else:
                        row.setdefault(field, None)
                rows.append(row)
                if predicted:
                    causal_rows.append(dict(row))

    if manifest_mismatches:
        raise SystemExit("manifest mismatch")
    with (OUTPUT / "all_callback_rows.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
    with (OUTPUT / "causal_first_differences.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(causal_rows)

    unique_terminal = [
        row for row in rows
        if row["clear_main"] is True
        and row["terminal_semantic_count"] == 1
    ]
    parent_equal = [
        row for row in unique_terminal
        if row["classification"] == "PARENT_TERMINAL_HOLD"
    ]
    raw_search = [
        row for row in unique_terminal
        if row["raw_terminal_replacement"] is True
        and row["owner_collision"] is False
        and row["parent_action_family"] == "PLAY_ITEM_SEARCH"
        and row["parent_card_id"] in (module.POKE_PAD, module.ULTRA_BALL)
    ]
    raw_search_counts = Counter(
        "POKE_PAD" if row["parent_card_id"] == module.POKE_PAD else "ULTRA_BALL"
        for row in raw_search
    )
    raw_search_first_starts = {}
    for row in raw_search:
        key = (row["replay_sha256"], row["seat"])
        raw_search_first_starts.setdefault(key, row)
    causal_family = Counter(row["parent_action_family"] for row in causal_rows)
    outside_search = [
        row for row in causal_rows
        if row["parent_action_family"] != "PLAY_ITEM_SEARCH"
    ]
    clear_unclassified = [
        row for row in rows
        if row["clear_main"] is True and not row["classification"]
    ]
    violations = {
        "invalid_parent_actions": invalid_parent,
        "invalid_contract_actions": sum(
            row["contract_valid"] is not True for row in causal_rows
        ),
        "hidden_information": sum(
            row["hidden_info_used"] is True for row in causal_rows
        ),
        "owner_collisions_in_predictions": sum(
            row["owner_collision"] is True for row in causal_rows
        ),
        "semantic_copy_predictions": sum(
            row["parent_semantic"] == row["contract_semantic"]
            for row in causal_rows
        ),
        "predicted_errors": sum(bool(row["error"]) for row in causal_rows),
        "nonidentical_retries": nonidentical_retries,
        "unclassified_clear_main": len(clear_unclassified),
    }
    residue = {
        "raw_rows": len(raw_search),
        "raw_replays": len({row["replay"] for row in raw_search}),
        "raw_seats": sorted({row["seat"] for row in raw_search}),
        "families": dict(raw_search_counts),
        "all_metal_defender": all(
            row["terminal_attack_id"] == module.METAL_DEFENDER
            for row in raw_search
        ),
        # This reproduces the old search-only census within its original
        # scope.  The broader rule can (correctly) find an earlier winning
        # override in the same turn, so global causal ordering must not erase
        # the known search residue.
        "search_scope_earliest_starts": len(raw_search_first_starts),
    }
    single_family_share = (
        max(causal_family.values()) / len(causal_rows)
        if causal_rows else 1.0
    )
    family_floor_count = sum(value >= 3 for value in causal_family.values())
    outside_families = {
        row["parent_action_family"] for row in outside_search
    }
    gate = {
        "integrity": bool(
            len(manifest) == 207 and target_seats == 209 and calls == 25880
            and len(raw_keys) == calls and invalid_parent == 0
            and not manifest_mismatches
        ),
        "zero_violations": not any(violations.values()),
        "known_residue": bool(
            residue["raw_rows"] == 4
            and residue["raw_replays"] == 3
            and residue["raw_seats"] == [0, 1]
            and residue["families"] == {"POKE_PAD": 3, "ULTRA_BALL": 1}
            and residue["all_metal_defender"]
            and residue["search_scope_earliest_starts"] == 3
        ),
        "causal_volume": bool(
            len(causal_rows) >= 24
            and len({row["replay"] for row in causal_rows}) >= 16
        ),
        "seat_floor": all(
            sum(row["seat"] == seat for row in causal_rows) >= 6
            for seat in (0, 1)
        ),
        "family_breadth": family_floor_count >= 3,
        "outside_search": bool(
            len(outside_search) >= 12 and len(outside_families) >= 2
        ),
        "family_concentration": single_family_share <= 0.75,
        "parent_equal_controls": bool(
            len(parent_equal) >= 24
            and len({row["replay"] for row in parent_equal}) >= 16
            and {row["seat"] for row in parent_equal} == {0, 1}
        ),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "integrity": {
            "replays": len(manifest), "target_seats": target_seats,
            "parent_calls": calls, "unique_raw_keys": len(raw_keys),
            "callback_rows": len(rows), "causal_rows": len(causal_rows),
            "duplicate_retries": duplicate_retries,
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
        },
        "census": {
            "clear_main_rows": sum(row["clear_main"] is True for row in rows),
            "unique_terminal_rows": len(unique_terminal),
            "parent_equal_controls": len(parent_equal),
            "parent_equal_replays": len({row["replay"] for row in parent_equal}),
            "parent_equal_seats": sorted({row["seat"] for row in parent_equal}),
            "causal_rows": len(causal_rows),
            "causal_replays": len({row["replay"] for row in causal_rows}),
            "causal_seats": dict(Counter(row["seat"] for row in causal_rows)),
            "causal_families": dict(causal_family),
            "outside_search_rows": len(outside_search),
            "outside_search_families": sorted(outside_families),
            "largest_family_share": single_family_share,
            "classification": dict(Counter(row["classification"] for row in rows)),
            "unsupported_reasons": dict(Counter(row["unsupported_reasons"] for row in rows if row["unsupported_reasons"] != "[]")),
        },
        "known_search_residue": residue,
        "violations": violations,
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "decision_if_gate_fails": "STOP__PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_NOT_BROADLY_ACTIONABLE",
        "root_qualitative_audit": "PENDING",
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
