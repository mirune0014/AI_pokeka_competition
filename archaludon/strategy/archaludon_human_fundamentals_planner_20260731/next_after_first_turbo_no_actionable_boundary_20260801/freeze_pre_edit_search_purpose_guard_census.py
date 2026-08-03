from __future__ import annotations

import copy
import csv
from collections import Counter
import hashlib
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLANNER = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
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
    "STRATEGY_SELECTION_PUBLIC_SECURED_ATTACK_POKEMON_SEARCH_PURPOSE_GUARD_V1.md"
)
FIRST_TURBO_STOP = PLANNER / "next_after_opening_timing_fail_20260801" / (
    "first_turbo_public_exact_role_fill_v1/ROOT_FIRST_TURBO_CENSUS_VERIFICATION.md"
)
TODO = PLANNER / "TODO.md"
MATRIX = PLANNER / "PLAYER_FUNDAMENTALS_ACCEPTANCE_MATRIX_JA.md"
FREQUENCY = PLANNER / "ROOT_TARGET_SEAT_ACTION_FREQUENCY.md"
EFFECT_GAPS = PLANNER / "ROOT_PUBLIC_EFFECT_COVERAGE_GAPS.md"
OUTPUT = HERE / "pre_edit_search_purpose_guard_census_raw"

EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "helper": "3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B",
    "strategy": "6D98BF4300BC059F1E7E7B9EA31FD98CBCE15CA68510DBF168F2DB26A2F7E69A",
    "first_turbo_stop": "7277B8ECD82C577CF775CCF2C058DACAAA01435F00A9A99B9041C1889B21F458",
    "todo": "8AE7B706CF5BE4E3EF659A10CEB4F8C5E516E67BECDA4421173AF06567BB1224",
    "matrix": "F273C043D4C479F15CC464600B14D51823BECF55D4AF22F68A0B8971F166A386",
    "frequency": "9A440FA409161153F8801354884FD66EC88DE522B14D5067D23ADDCBA0804ECC",
    "effect_gaps": "253F8CB535DFF70F561E93EA57066E3C5E563DCE9735F91AF56AF327A714D3D1",
}

ORIENTATION_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "turn_action_count", "snapshot_sha256", "pre_owners", "post_owners",
    "search_families", "attack_ids", "parent_action", "parent_semantic",
    "parent_search_family", "duplicate_retry",
)
CALLBACK_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "turn_action_count", "game_epoch", "snapshot_sha256", "context",
    "pre_owners", "post_owners", "search_family", "search_card_id",
    "search_serial", "search_role_unique", "public_effect_exact",
    "discard_requirement", "discard_pairs", "all_discard_pairs_touch_protected",
    "legal_semantics", "legal_attack_ids", "parent_action",
    "parent_semantic", "parent_valid", "contract_action",
    "contract_semantic", "contract_valid", "attack_id", "attack_kind",
    "attack_ko", "attack_prize", "attack_terminal", "backup_ready",
    "backup_routes", "visible_role_deficits", "productive_other_options",
    "public_outcome_parent", "public_outcome_attack", "classifiable",
    "predicted_difference", "classification", "rejection_reason",
    "hidden_info_used", "owner_collision", "duplicate_retry", "error",
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


def clear_main(module, obs):
    return bool(
        obs is not None
        and obs.current is not None
        and obs.select is not None
        and obs.current.result == -1
        and obs.select.context == module.SelectContext.MAIN
        and obs.select.minCount == 1
        and obs.select.maxCount == 1
        and obs.select.effect is None
        and obs.select.contextCard is None
        and obs.current.looking is None
    )


def semantic_action(module, obs, action):
    return module._pcrd_action_roles(obs, action)


def search_options(module, obs):
    rows = []
    for position, option in enumerate(obs.select.option):
        if option.type != module.OptionType.PLAY:
            continue
        card = module.option_card(obs, option)
        card_id = module._pcrd_get(card, "id")
        if card_id not in (module.POKE_PAD, module.ULTRA_BALL):
            continue
        rows.append({
            "position": position,
            "family": "POKE_PAD" if card_id == module.POKE_PAD else "ULTRA_BALL",
            "card_id": card_id,
            "serial": module._pcrd_serial(card),
            "role": module._pcrd_option_role(obs, option),
        })
    return tuple(rows)


def raw_attack_options(module, obs):
    rows = []
    for position, option in enumerate(obs.select.option):
        if option.type == module.OptionType.ATTACK:
            rows.append({
                "position": position,
                "attack_id": module._pcrd_int(option.attackId),
                "role": module._pcrd_option_role(obs, option),
            })
    return tuple(rows)


def selected_search(module, obs, parent_action, searches):
    if not module._cum_valid_action(obs, parent_action) or len(parent_action) != 1:
        return None
    position = parent_action[0]
    matches = [row for row in searches if row["position"] == position]
    if len(matches) != 1:
        return None
    row = dict(matches[0])
    row["unique"] = bool(
        row["serial"] is not None
        and sum(candidate["role"] == row["role"] for candidate in searches) == 1
    )
    return row


def choose_attack(module, obs):
    rows, reason = module._pfgear_current_attack_rows(
        obs, allow_duplicate_ui=True
    )
    if rows is None:
        return None, None, reason or "attack_rows_unknown"
    if not rows:
        return None, None, "no_payable_attack"
    remaining = len(tuple(module.my_state(obs).prize or ()))
    terminal = [
        row for row in rows
        if row["certificate"]["ko"]
        and row["certificate"]["prize_yield"] >= remaining
    ]
    if len(terminal) == 1:
        return terminal[0], "DIRECT_FINISH", None
    if terminal:
        return None, None, "multiple_terminal_attacks"
    kos = [row for row in rows if row["certificate"]["ko"]]
    if kos:
        if any(
            module._pcrd_int(row["certificate"].get("final_damage")) is None
            for row in kos
        ):
            return None, None, "ko_damage_unknown"
        best_value = max(
            (row["certificate"]["prize_yield"],
             row["certificate"]["final_damage"])
            for row in kos
        )
        best = [
            row for row in kos
            if (row["certificate"]["prize_yield"],
                row["certificate"]["final_damage"]) == best_value
        ]
        if len(best) == 1:
            return best[0], "UNIQUE_CURRENT_KO", None
        return None, None, "multiple_incomparable_ko_attacks"
    successors = []
    for row in rows:
        successor = module._pfgear_veto_successor(obs, row)
        if successor is None:
            return None, None, "nonko_successor_unknown"
        successors.append((row, successor))
    winners = []
    for row, candidate in successors:
        comparisons = [
            module._pfgear_componentwise_nonworse(candidate, other)
            for other_row, other in successors
            if other_row is not row
        ]
        if all(value[0] for value in comparisons) and (
            len(successors) == 1 or any(value[1] for value in comparisons)
        ):
            winners.append(row)
    if len(winners) != 1:
        return None, None, "multiple_incomparable_nonko_attacks"
    return winners[0], "SECURED_NONWORSE_ATTACK", None


def ready_backup(module, obs):
    target = module.opp_active_pokemon(obs)
    if target is None:
        return None, "missing_opponent_active"
    routes = module._pfgear_ready_bench_set(obs, target)
    if routes is None:
        return None, "backup_readiness_unknown"
    return routes, None


def role_deficits(module, obs, backup_routes):
    mine = module.my_state(obs)
    opponent = module.opp_state(obs)
    hand = module._pcrd_hand(obs)
    board = tuple(module._pcrd_board_pokemon(mine))
    if hand is None or any(module._pcrd_serial(card) is None for card in hand):
        return None, "own_hand_unknown"
    active = module.active_pokemon(obs)
    active_serial = module._pcrd_serial(active)
    ids = [module._pcrd_get(card, "id") for card in board]
    hand_ids = [module._pcrd_get(card, "id") for card in hand]
    line_ids = {module.DURALUDON, module.ARCHALUDON, module.ARCHALUDON_EX}
    independent_line = [
        card for card in board
        if module._pcrd_get(card, "id") in line_ids
        and module._pcrd_serial(card) != active_serial
    ]
    eligible_duraludon = [
        card for card in board
        if module._pcrd_get(card, "id") == module.DURALUDON
        and not bool(module._pcrd_get(card, "appearThisTurn", False))
    ]
    deficits = []
    if len(board) <= 1:
        deficits.append("ONE_POKEMON_LOSS_RISK")
    if not backup_routes:
        deficits.append("NO_READY_BACKUP")
    if not independent_line:
        deficits.append("NO_INDEPENDENT_EVOLUTION_CHASSIS")
    if (
        eligible_duraludon
        and not any(card_id in (module.ARCHALUDON, module.ARCHALUDON_EX)
                    for card_id in hand_ids)
    ):
        deficits.append("EVOLUTION_SEARCH_PURPOSE")
    opponent_prizes = len(tuple(opponent.prize or ()))
    if (
        opponent_prizes <= 2
        and module.ARCHALUDON not in ids
        and module.ARCHALUDON not in hand_ids
    ):
        deficits.append("ONE_PRIZE_WALL_PURPOSE")
    if (
        module._pcrd_get(active, "id") == module.CINDERACE
        and not any(card_id in line_ids for card_id in ids)
    ):
        deficits.append("POST_TURBO_LINE_PURPOSE")
    return tuple(sorted(set(deficits))), None


def productive_other_options(module, obs, selected, searches, terminal):
    if terminal:
        return ()
    ignored = {row["position"] for row in searches}
    rows = []
    for position, option in enumerate(obs.select.option):
        if position in ignored or option.type in (module.OptionType.ATTACK,
                                                   module.OptionType.END):
            continue
        rows.append(module._pcrd_option_role(obs, option))
    return tuple(rows)


def discard_pairs(module, obs, selected):
    if selected["family"] != "ULTRA_BALL":
        return (), False, None
    hand = module._pcrd_hand(obs)
    if hand is None:
        return None, None, "own_hand_unknown"
    other = [
        card for card in hand
        if module._pcrd_serial(card) != selected["serial"]
    ]
    if len(other) < 2:
        return None, None, "ultra_ball_discard_pair_missing"
    pairs = []
    protected = {
        module.METAL_ENERGY, module.DURALUDON, module.ARCHALUDON,
        module.ARCHALUDON_EX, module.BOSS, module.NIGHT_STRETCHER,
        module.HERO_CAPE, module.FULL_METAL_LAB,
    }
    for left, right in combinations(other, 2):
        refs = tuple(sorted((
            (module._pcrd_get(left, "id"), module._pcrd_serial(left)),
            (module._pcrd_get(right, "id"), module._pcrd_serial(right)),
        )))
        touches = False
        for card in (left, right):
            data = module.CARD_DB.get(module._pcrd_get(card, "id"))
            if (
                module._pcrd_get(card, "id") in protected
                or (data is not None and bool(module._pcrd_get(data, "aceSpec")))
            ):
                touches = True
        pairs.append((refs, touches))
    return tuple(pairs), all(row[1] for row in pairs), None


def classify(module, obs, parent_action, selected, pre_owners, post_owners):
    parent_roles = semantic_action(module, obs, parent_action)
    base = {
        "contract_action": list(parent_action),
        "contract_semantic": parent_roles,
        "contract_valid": True,
        "attack_id": None,
        "attack_kind": None,
        "attack_ko": None,
        "attack_prize": None,
        "attack_terminal": None,
        "backup_ready": None,
        "backup_routes": None,
        "visible_role_deficits": None,
        "productive_other_options": None,
        "discard_pairs": None,
        "all_discard_pairs_touch_protected": None,
        "classifiable": False,
        "predicted_difference": False,
        "classification": "UNKNOWN_HOLD",
        "rejection_reason": None,
        "hidden_info_used": False,
        "owner_collision": bool(pre_owners or post_owners),
        "error": None,
    }
    if pre_owners or post_owners:
        base.update(classification="OWNER_HOLD", rejection_reason="owner_live")
        return base
    if not module._pfc_fixed_card_semantics_supported() or not selected["unique"]:
        base.update(
            rejection_reason="search_effect_or_physical_binding_unknown"
        )
        return base
    attack_row, attack_kind, attack_error = choose_attack(module, obs)
    if attack_row is None:
        base.update(
            classification="ATTACK_UNKNOWN_HOLD",
            rejection_reason=attack_error,
        )
        return base
    positions = tuple(attack_row["positions"])
    attack_action = [min(positions)] if positions else None
    if attack_action is None or not module._cum_valid_action(obs, attack_action):
        base.update(error="selected_attack_invalid")
        return base
    attack_roles = semantic_action(module, obs, attack_action)
    if attack_roles is None or len(set(attack_roles)) != 1:
        base.update(error="selected_attack_semantic_ambiguous")
        return base
    certificate = attack_row["certificate"]
    terminal = attack_kind == "DIRECT_FINISH"
    if terminal:
        pairs, unsafe_pairs, pair_error = discard_pairs(module, obs, selected)
        classification = (
            "POKE_PAD_NO_PURPOSE_ATTACK"
            if selected["family"] == "POKE_PAD"
            else "ULTRA_UNSAFE_RESERVE_ATTACK"
            if unsafe_pairs is True
            else "ULTRA_NO_PURPOSE_ATTACK"
        )
        base.update(
            contract_action=attack_action,
            contract_semantic=attack_roles,
            contract_valid=module._cum_valid_action(obs, attack_action),
            attack_id=attack_row["attack_id"],
            attack_kind=attack_kind,
            attack_ko=True,
            attack_prize=certificate["prize_yield"],
            attack_terminal=True,
            backup_ready=True,
            backup_routes=(),
            visible_role_deficits=(),
            productive_other_options=(),
            discard_pairs=() if pairs is None else pairs,
            all_discard_pairs_touch_protected=unsafe_pairs,
            classifiable=True,
            predicted_difference=canonical(parent_roles) != canonical(attack_roles),
            classification=classification,
            rejection_reason=None,
        )
        if not base["predicted_difference"]:
            base.update(classification="SEMANTIC_EQUAL_HOLD")
        return base
    backup, backup_error = ready_backup(module, obs)
    if backup is None:
        base.update(
            classification="PURPOSE_HOLD",
            rejection_reason=backup_error,
            attack_id=attack_row["attack_id"],
            attack_kind=attack_kind,
        )
        return base
    deficits, deficit_error = role_deficits(module, obs, backup)
    if deficits is None:
        base.update(
            classification="PURPOSE_HOLD",
            rejection_reason=deficit_error,
            attack_id=attack_row["attack_id"],
            attack_kind=attack_kind,
        )
        return base
    other = productive_other_options(
        module, obs, selected, search_options(module, obs), terminal
    )
    pairs, unsafe_pairs, pair_error = discard_pairs(module, obs, selected)
    base.update(
        contract_action=attack_action,
        contract_semantic=attack_roles,
        contract_valid=module._cum_valid_action(obs, attack_action),
        attack_id=attack_row["attack_id"],
        attack_kind=attack_kind,
        attack_ko=bool(certificate["ko"]),
        attack_prize=certificate["prize_yield"],
        attack_terminal=terminal,
        backup_ready=bool(backup),
        backup_routes=backup,
        visible_role_deficits=deficits,
        productive_other_options=other,
        discard_pairs=pairs,
        all_discard_pairs_touch_protected=unsafe_pairs,
        classifiable=pair_error is None,
    )
    if pair_error is not None:
        base.update(classification="PURPOSE_HOLD", rejection_reason=pair_error)
        return base
    if deficits:
        base.update(
            classification="PURPOSE_HOLD",
            rejection_reason="visible_role_deficit:" + ",".join(deficits),
        )
        return base
    if other:
        base.update(
            classification="PURPOSE_HOLD",
            rejection_reason="unfinished_productive_main_action",
        )
        return base
    classification = (
        "POKE_PAD_NO_PURPOSE_ATTACK"
        if selected["family"] == "POKE_PAD"
        else "ULTRA_UNSAFE_RESERVE_ATTACK"
        if unsafe_pairs
        else "ULTRA_NO_PURPOSE_ATTACK"
    )
    base.update(
        predicted_difference=canonical(parent_roles) != canonical(attack_roles),
        classification=classification,
        rejection_reason=None,
    )
    if not base["predicted_difference"]:
        base.update(classification="SEMANTIC_EQUAL_HOLD")
    return base


def main():
    if OUTPUT.exists():
        raise SystemExit("refusing to reuse search-purpose census destination")
    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "deck": sha256(PARENT / "deck.csv"),
        "manifest": sha256(MANIFEST),
        "helper": sha256(HELPER),
        "strategy": sha256(STRATEGY),
        "first_turbo_stop": sha256(FIRST_TURBO_STOP),
        "todo": sha256(TODO),
        "matrix": sha256(MATRIX),
        "frequency": sha256(FREQUENCY),
        "effect_gaps": sha256(EFFECT_GAPS),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input hash mismatch: " + canonical(actual_hashes))
    OUTPUT.mkdir(parents=False, exist_ok=False)
    (OUTPUT / "source_manifest.json").write_bytes(MANIFEST.read_bytes())

    helper = load_module("search_guard_helper", HELPER)
    module = helper.load_parent()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    orientation_rows = []
    callback_rows = []
    differences = []
    raw_keys = set()
    orientation_by_key = {}
    callback_by_key = {}
    target_seats = 0
    calls = 0
    invalid_parent = 0
    manifest_mismatches = []
    orientation_retries = 0
    callback_retries = 0

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
            for step_index, step in enumerate(replay["steps"]):
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat or raw.get("select") is None:
                    continue
                calls += 1
                snapshot = digest(raw)
                raw_key = (entry["replay"], seat, step_index,
                           current.get("turn"), snapshot)
                if raw_key in raw_keys:
                    raise SystemExit("duplicate raw callback key")
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = live_owners(module)
                searches = search_options(module, obs) if clear_main(module, obs) else ()
                attacks = raw_attack_options(module, obs) if clear_main(module, obs) else ()
                parent_action = module.agent(copy.deepcopy(raw))
                post_owners = live_owners(module)
                parent_valid = bool(module._cum_valid_action(obs, parent_action))
                if not parent_valid:
                    invalid_parent += 1
                parent_roles = semantic_action(module, obs, parent_action) if parent_valid else None
                if parent_valid and parent_roles is None:
                    invalid_parent += 1

                if searches and attacks:
                    parent_selected = selected_search(
                        module, obs, parent_action, searches
                    ) if parent_valid else None
                    orientation = {
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "step": step_index,
                        "turn": current.get("turn"),
                        "turn_action_count": current.get("turnActionCount"),
                        "snapshot_sha256": snapshot,
                        "pre_owners": canonical(pre_owners),
                        "post_owners": canonical(post_owners),
                        "search_families": canonical(sorted(set(row["family"] for row in searches))),
                        "attack_ids": canonical(sorted(set(row["attack_id"] for row in attacks))),
                        "parent_action": canonical(parent_action),
                        "parent_semantic": canonical(parent_roles),
                        "parent_search_family": None if parent_selected is None else parent_selected["family"],
                        "duplicate_retry": False,
                    }
                    key = (replay_sha, seat, "ORIENTATION", snapshot)
                    prior = orientation_by_key.get(key)
                    if prior is not None:
                        signature = (
                            "pre_owners", "post_owners", "search_families",
                            "attack_ids", "parent_semantic", "parent_search_family",
                        )
                        if any(prior[field] != orientation[field] for field in signature):
                            raise SystemExit("non-identical orientation retry")
                        orientation_retries += 1
                    else:
                        orientation_by_key[key] = orientation
                        orientation_rows.append(orientation)

                selected = selected_search(
                    module, obs, parent_action, searches
                ) if parent_valid and searches else None
                if selected is None:
                    continue
                result = classify(
                    module, obs, parent_action, selected,
                    pre_owners, post_owners,
                )
                row = {
                    "replay": entry["replay"],
                    "replay_sha256": replay_sha,
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "turn_action_count": current.get("turnActionCount"),
                    "game_epoch": 0,
                    "snapshot_sha256": snapshot,
                    "context": module._pcrd_int(obs.select.context),
                    "pre_owners": canonical(pre_owners),
                    "post_owners": canonical(post_owners),
                    "search_family": selected["family"],
                    "search_card_id": selected["card_id"],
                    "search_serial": selected["serial"],
                    "search_role_unique": selected["unique"],
                    "public_effect_exact": module._pfc_fixed_card_semantics_supported(),
                    "discard_requirement": 0 if selected["family"] == "POKE_PAD" else 2,
                    "legal_semantics": canonical(tuple(module._pcrd_option_role(obs, option) for option in obs.select.option)),
                    "legal_attack_ids": canonical(tuple(row["attack_id"] for row in attacks)),
                    "parent_action": canonical(parent_action),
                    "parent_semantic": canonical(parent_roles),
                    "parent_valid": parent_valid,
                    "public_outcome_parent": canonical({"kind": "SEARCH", "family": selected["family"]}),
                    "public_outcome_attack": canonical({
                        "terminal": result["attack_terminal"],
                        "ko": result["attack_ko"],
                        "prize": result["attack_prize"],
                        "backup": result["backup_ready"],
                    }),
                    "duplicate_retry": False,
                    **result,
                }
                for field in CALLBACK_FIELDS:
                    value = row.get(field)
                    if isinstance(value, (dict, list, tuple, set, frozenset)):
                        row[field] = canonical(value)
                    else:
                        row.setdefault(field, None)
                key = (replay_sha, seat, "PARENT_SEARCH", snapshot)
                prior = callback_by_key.get(key)
                if prior is not None:
                    signature = (
                        "pre_owners", "post_owners", "search_family",
                        "parent_semantic", "contract_semantic", "parent_valid",
                        "contract_valid", "classification", "rejection_reason",
                        "predicted_difference", "error",
                    )
                    if any(prior[field] != row[field] for field in signature):
                        raise SystemExit("non-identical parent-search retry")
                    callback_retries += 1
                    continue
                callback_by_key[key] = row
                callback_rows.append(row)
                if row["predicted_difference"] is True:
                    differences.append(dict(row))

    if manifest_mismatches:
        raise SystemExit("manifest mismatch")
    for rows, fields in (
        (orientation_rows, ORIENTATION_FIELDS),
        (callback_rows, CALLBACK_FIELDS),
        (differences, CALLBACK_FIELDS),
    ):
        for row in rows:
            for field in fields:
                row.setdefault(field, None)

    with (OUTPUT / "orientation_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ORIENTATION_FIELDS)
        writer.writeheader(); writer.writerows(orientation_rows)
    with (OUTPUT / "search_guard_callback_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALLBACK_FIELDS)
        writer.writeheader(); writer.writerows(callback_rows)
    with (OUTPUT / "predicted_first_differences.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALLBACK_FIELDS)
        writer.writeheader(); writer.writerows(differences)

    classifiable = [row for row in callback_rows if row["classifiable"] is True]
    predicted = [row for row in callback_rows if row["predicted_difference"] is True]
    purpose_controls = [
        row for row in callback_rows
        if row["classification"] == "PURPOSE_HOLD"
        and row["classifiable"] is True
    ]
    owner_controls = [row for row in callback_rows if row["classification"] == "OWNER_HOLD"]
    pad = [row for row in predicted if row["classification"] == "POKE_PAD_NO_PURPOSE_ATTACK"]
    ultra = [row for row in predicted if row["classification"].startswith("ULTRA_")]
    predicted_turns = {(row["replay"], row["seat"], row["turn"]) for row in predicted}
    eligible_turns = {(row["replay"], row["seat"], row["turn"]) for row in classifiable}
    violations = {
        "invalid_parent_actions": invalid_parent,
        "invalid_predicted_contract_actions": sum(row["contract_valid"] is not True for row in predicted),
        "hidden_information": sum(row["hidden_info_used"] is True for row in predicted),
        "owner_collisions_in_predictions": sum(row["owner_collision"] is True for row in predicted),
        "semantic_copy_noise": sum(row["parent_semantic"] == row["contract_semantic"] for row in predicted),
        "non_main_predictions": sum(row["context"] != module._pcrd_int(module.SelectContext.MAIN) for row in predicted),
        "predicted_errors": sum(bool(row["error"]) for row in predicted),
    }
    gate = {
        "integrity": bool(
            len(manifest) == 207 and target_seats == 209 and calls == 25880
            and len(raw_keys) == calls and invalid_parent == 0
            and len(orientation_by_key) == len(orientation_rows)
            and len(callback_by_key) == len(callback_rows)
        ),
        "eligible_surface": bool(
            len(eligible_turns) >= 80
            and len({row[0] for row in eligible_turns}) >= 50
            and {row[1] for row in eligible_turns} == {0, 1}
        ),
        "predicted_differences": bool(
            len(predicted) >= 24 and len(predicted_turns) >= 24
            and len({row["replay"] for row in predicted}) >= 16
            and {row["seat"] for row in predicted} == {0, 1}
        ),
        "both_search_families": len(pad) >= 8 and len(ultra) >= 8,
        "purposeful_controls": bool(
            len(purpose_controls) >= 24
            and len({row["replay"] for row in purpose_controls}) >= 16
            and {row["search_family"] for row in purpose_controls}
            == {"POKE_PAD", "ULTRA_BALL"}
        ),
        "inherited_owner_controls": bool(owner_controls),
        "zero_violations": not any(violations.values()),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "integrity": {
            "replays": len(manifest), "target_seats": target_seats,
            "parent_calls": calls, "unique_raw_keys": len(raw_keys),
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
            "orientation_rows": len(orientation_rows),
            "orientation_retries_collapsed": orientation_retries,
            "callback_rows": len(callback_rows),
            "callback_retries_collapsed": callback_retries,
            "predicted_rows": len(predicted),
        },
        "orientation": {
            "rows": len(orientation_rows),
            "turns": len({(row["replay"], row["seat"], row["turn"]) for row in orientation_rows}),
            "replays": len({row["replay"] for row in orientation_rows}),
            "seats": sorted({row["seat"] for row in orientation_rows}),
            "root_reproduction_or_explanation": "PENDING",
        },
        "census": {
            "classifiable_rows": len(classifiable),
            "eligible_turns": len(eligible_turns),
            "eligible_replays": len({row[0] for row in eligible_turns}),
            "eligible_seats": sorted({row[1] for row in eligible_turns}),
            "predicted_rows": len(predicted),
            "predicted_turns": len(predicted_turns),
            "predicted_replays": len({row["replay"] for row in predicted}),
            "predicted_seats": sorted({row["seat"] for row in predicted}),
            "pad_predictions": len(pad), "ultra_predictions": len(ultra),
            "purpose_controls": len(purpose_controls),
            "owner_controls": len(owner_controls),
            "classification": dict(Counter(row["classification"] for row in callback_rows)),
            "rejection_reasons": dict(Counter(str(row["rejection_reason"]) for row in callback_rows)),
        },
        "violations": violations,
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "decision_if_gate_fails": "STOP__PUBLIC_SECURED_ATTACK_SEARCH_GUARD_NOT_BROADLY_ACTIONABLE",
        "root_qualitative_audit": "PENDING",
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
