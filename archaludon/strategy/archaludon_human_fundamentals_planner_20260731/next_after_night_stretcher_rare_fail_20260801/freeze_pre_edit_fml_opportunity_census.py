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
OUTPUT = HERE / "pre_edit_fml_opportunity_census_raw"
FML = 1244

FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "parent_action", "parent_roles", "parent_valid",
    "owner_state", "fml_roles", "fml_serials", "prior_stadium",
    "stadium_played", "attack_id", "attack_roles", "keep_status",
    "fml_status", "keep_current", "fml_current", "keep_fields",
    "fml_fields", "first_hard_difference", "direction", "rejection_reason",
)

HIERARCHY = (
    (("current_win", "MAX"),),
    (("certain_terminal_routes", "MIN"),),
    (("current_prizes", "MAX"), ("current_ko", "MAX")),
    (("certain_return_prizes", "MIN"), ("current_attacker_survival", "MAX")),
    (
        ("executable_next_attacker", "MAX"),
        ("next_turn_payable_attack", "MAX"),
        ("own_exact_turns_to_finish", "MIN"),
    ),
)
FIELD_NAMES = tuple(
    name for group in HIERARCHY for name, _ in group
) + (
    "hits_to_ko", "hits_to_same_prize", "active_prize_liability",
    "opponent_exact_turns_to_finish", "retained_metal",
    "retained_line_pieces", "retained_boss", "retained_recovery",
    "retained_ace_spec", "post_reply_ledger",
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


def sha256_snapshot(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest().upper()


def load_parent():
    sys.path.insert(0, str(PARENT))
    spec = importlib.util.spec_from_file_location(
        "fml_pre_edit_parent", PARENT / "main.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(PARENT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module) -> None:
    for function, reason in (
        ("_pfgear_reset_active", "fml_census_reset"),
        ("_pcrd_clear", "fml_census_reset"),
        ("_pfc_clear", "fml_census_reset"),
        ("_cum_reset_runtime", "fml_census_reset"),
        ("_dper_reset_runtime", "fml_census_reset"),
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


def owner_state(module):
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


def selected_fields(plan):
    if not isinstance(plan, dict):
        return None
    fields = plan.get("fields")
    if not isinstance(fields, dict):
        return None
    return {name: freeze(fields.get(name)) for name in FIELD_NAMES}


def current_certificate(plan):
    if not isinstance(plan, dict):
        return None
    certificate = plan.get("current_certificate")
    if not isinstance(certificate, dict):
        return None
    return {
        key: freeze(certificate.get(key))
        for key in (
            "status", "attack_id", "raw_damage", "final_damage",
            "remaining_hp", "ko", "prize_yield", "terminal",
            "persistent_effects", "assumptions", "unsupported",
        )
    }


def compare_group(keep, play, group):
    play_better = False
    keep_better = False
    comparisons = []
    for name, direction in group:
        left = keep.get(name)
        right = play.get(name)
        comparisons.append((name, direction, left, right))
        if left is None or right is None:
            if left != right:
                return "INCOMPARABLE", comparisons
            continue
        if isinstance(left, bool):
            left = int(left)
        if isinstance(right, bool):
            right = int(right)
        if not isinstance(left, (int, float)) or not isinstance(
            right, (int, float)
        ):
            if left != right:
                return "INCOMPARABLE", comparisons
            continue
        if left == right:
            continue
        if direction == "MAX":
            play_better |= right > left
            keep_better |= left > right
        else:
            play_better |= right < left
            keep_better |= left < right
    if play_better and keep_better:
        return "INCOMPARABLE", comparisons
    if play_better:
        return "PLAY_FML", comparisons
    if keep_better:
        return "KEEP", comparisons
    return "EQUAL", comparisons


def hard_direction(keep_plan, fml_plan):
    keep = selected_fields(keep_plan)
    play = selected_fields(fml_plan)
    if keep is None or play is None:
        return None, "INCOMPARABLE"
    for index, group in enumerate(HIERARCHY, start=1):
        direction, comparisons = compare_group(keep, play, group)
        if direction != "EQUAL":
            return {
                "layer": index,
                "direction": direction,
                "comparisons": comparisons,
            }, direction
    return {"layer": None, "direction": "EQUAL", "comparisons": []}, "EQUAL"


def exact_plan(module, obs, attack_id, use_fml):
    try:
        return module._pcrd_make_plan(
            obs,
            evolution=None,
            attack_id=attack_id,
            use_fml=use_fml,
            use_cape=False,
            use_ice=False,
            require_current_attack_option=True,
        )
    except Exception:
        return None


def main() -> dict:
    if OUTPUT.exists():
        protected = (OUTPUT / "opportunity_rows.csv", OUTPUT / "summary.json")
        if any(path.exists() for path in protected):
            raise SystemExit("refusing to overwrite frozen census output")
    else:
        OUTPUT.mkdir(parents=False)

    module = load_parent()
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    rows_path = OUTPUT / "opportunity_rows.csv"
    counts = Counter()
    opportunity_turns = set()
    opportunity_replays = set()
    opportunity_seats = set()
    exact_turns = set()
    exact_replays = set()
    exact_seats = set()
    historical_fml = set()
    manifest_mismatches = []
    global_calls = 0
    invalid_parent = 0

    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for entry in manifest:
            replay_path = CORPUS / entry["replay"]
            replay_sha = sha256(replay_path)
            if replay_sha != entry["sha256"]:
                manifest_mismatches.append(entry["replay"])
                continue
            replay = json.loads(replay_path.read_text(encoding="utf-8"))
            for seat in entry["target_seats"]:
                reset(module)
                for step_index, step in enumerate(replay["steps"]):
                    raw = step[seat].get("observation") or {}
                    current = raw.get("current") or {}
                    if current.get("yourIndex") != seat:
                        continue
                    turn = current.get("turn")
                    for position, log in enumerate(raw.get("logs") or ()):
                        if (
                            log.get("type") == int(module.LogType.PLAY)
                            and log.get("playerIndex") == seat
                            and log.get("cardId") == FML
                        ):
                            historical_fml.add(
                                (
                                    entry["replay"], seat, turn,
                                    log.get("serial"), position,
                                )
                            )
                    if raw.get("select") is None:
                        continue
                    global_calls += 1
                    parent_action = module.agent(copy.deepcopy(raw))
                    obs = module.to_observation_class(copy.deepcopy(raw))
                    parent_roles = roles(module, obs, parent_action)
                    parent_valid = parent_roles is not None
                    invalid_parent += int(not parent_valid)
                    if obs.select.context != module.SelectContext.MAIN:
                        continue
                    fml_options = []
                    for position, option in enumerate(obs.select.option):
                        card = module.option_card(obs, option)
                        if (
                            option.type == module.OptionType.PLAY
                            and getattr(card, "id", None) == FML
                        ):
                            fml_options.append(
                                (
                                    position,
                                    module._pcrd_option_role(obs, option),
                                    getattr(card, "serial", None),
                                )
                            )
                    if not fml_options:
                        continue
                    turn_key = (entry["replay"], seat, turn)
                    opportunity_turns.add(turn_key)
                    opportunity_replays.add(entry["replay"])
                    opportunity_seats.add(seat)
                    attack_options = []
                    for position, option in enumerate(obs.select.option):
                        if option.type == module.OptionType.ATTACK:
                            attack_options.append(
                                (
                                    position,
                                    getattr(option, "attackId", None),
                                    module._pcrd_option_role(obs, option),
                                )
                            )
                    prior_stadium = tuple(
                        module._pcrd_card_ref(card)
                        for card in tuple(obs.current.stadium or ())
                    )
                    if not attack_options:
                        writer.writerow({
                            "replay": entry["replay"],
                            "replay_sha256": replay_sha,
                            "seat": seat, "step": step_index, "turn": turn,
                            "snapshot_sha256": sha256_snapshot(raw),
                            "parent_action": canonical(parent_action),
                            "parent_roles": canonical(parent_roles),
                            "parent_valid": parent_valid,
                            "owner_state": canonical(owner_state(module)),
                            "fml_roles": canonical([row[1] for row in fml_options]),
                            "fml_serials": canonical([row[2] for row in fml_options]),
                            "prior_stadium": canonical(prior_stadium),
                            "stadium_played": current.get("stadiumPlayed"),
                            "attack_id": None, "attack_roles": canonical([]),
                            "keep_status": None, "fml_status": None,
                            "keep_current": canonical(None),
                            "fml_current": canonical(None),
                            "keep_fields": canonical(None),
                            "fml_fields": canonical(None),
                            "first_hard_difference": canonical(None),
                            "direction": "REJECT",
                            "rejection_reason": "no_actual_attack_option",
                        })
                        counts["rows"] += 1
                        counts["no_actual_attack_option"] += 1
                        continue
                    attack_ids = sorted(
                        {
                            attack_id for _, attack_id, _ in attack_options
                            if isinstance(attack_id, int)
                        }
                    )
                    if len(attack_ids) != len(attack_options):
                        counts["duplicate_or_unknown_attack_roles"] += 1
                    for attack_id in attack_ids:
                        keep = exact_plan(module, obs, attack_id, False)
                        play = exact_plan(module, obs, attack_id, True)
                        keep_status = None if keep is None else keep.get("status")
                        play_status = None if play is None else play.get("status")
                        if keep is None:
                            reason = "keep_plan_unavailable"
                        elif play is None:
                            reason = "fml_plan_unavailable"
                        elif keep_status != "EXACT":
                            reason = "keep_return_not_exact"
                        elif play_status != "EXACT":
                            reason = "fml_return_not_exact"
                        else:
                            reason = None
                        if reason is None:
                            first_difference, direction = hard_direction(keep, play)
                            exact_turns.add(turn_key)
                            exact_replays.add(entry["replay"])
                            exact_seats.add(seat)
                            counts["exact_pairs"] += 1
                            counts["direction:" + direction] += 1
                        else:
                            first_difference, direction = None, "REJECT"
                            counts[reason] += 1
                        selected_attack_roles = [
                            role for _, row_attack, role in attack_options
                            if row_attack == attack_id
                        ]
                        writer.writerow({
                            "replay": entry["replay"],
                            "replay_sha256": replay_sha,
                            "seat": seat, "step": step_index, "turn": turn,
                            "snapshot_sha256": sha256_snapshot(raw),
                            "parent_action": canonical(parent_action),
                            "parent_roles": canonical(parent_roles),
                            "parent_valid": parent_valid,
                            "owner_state": canonical(owner_state(module)),
                            "fml_roles": canonical([row[1] for row in fml_options]),
                            "fml_serials": canonical([row[2] for row in fml_options]),
                            "prior_stadium": canonical(prior_stadium),
                            "stadium_played": current.get("stadiumPlayed"),
                            "attack_id": attack_id,
                            "attack_roles": canonical(selected_attack_roles),
                            "keep_status": keep_status,
                            "fml_status": play_status,
                            "keep_current": canonical(current_certificate(keep)),
                            "fml_current": canonical(current_certificate(play)),
                            "keep_fields": canonical(selected_fields(keep)),
                            "fml_fields": canonical(selected_fields(play)),
                            "first_hard_difference": canonical(first_difference),
                            "direction": direction,
                            "rejection_reason": reason,
                        })
                        counts["rows"] += 1

    historical_turns = {
        (replay, seat, turn) for replay, seat, turn, _, _ in historical_fml
    }
    summary = {
        "parent_main_sha256": sha256(PARENT / "main.py"),
        "deck_sha256": sha256(PARENT / "deck.csv"),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "runner_sha256": sha256(Path(__file__)),
        "row_csv_sha256": sha256(rows_path),
        "manifest_entries": len(manifest),
        "manifest_mismatches": manifest_mismatches,
        "target_seats": sum(len(entry["target_seats"]) for entry in manifest),
        "global_parent_calls": global_calls,
        "invalid_parent_actions": invalid_parent,
        "historical_fml_play_turns": len(historical_turns),
        "historical_fml_play_replays": len({row[0] for row in historical_turns}),
        "historical_fml_play_seats": sorted({row[1] for row in historical_turns}),
        "opportunity_turns": len(opportunity_turns),
        "opportunity_replays": len(opportunity_replays),
        "opportunity_seats": sorted(opportunity_seats),
        "exact_two_world_turns": len(exact_turns),
        "exact_two_world_replays": len(exact_replays),
        "exact_two_world_seats": sorted(exact_seats),
        "counts": dict(sorted(counts.items())),
    }
    summary_path = OUTPUT / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if manifest_mismatches or invalid_parent:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    main()

