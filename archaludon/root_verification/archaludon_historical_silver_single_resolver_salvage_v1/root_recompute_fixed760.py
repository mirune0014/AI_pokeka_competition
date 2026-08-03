from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SPEC_PATH = (
    REPO
    / "archaludon"
    / "evaluation_specs"
    / "archaludon_historical_silver_single_resolver_salvage_v1"
    / "fixed760_spec.json"
)
RAW = (
    REPO
    / "archaludon"
    / "evaluations"
    / "archaludon_historical_silver_single_resolver_salvage_v1"
    / "fixed760_raw_20260803"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def trace_for(manifest: dict, game: int) -> Path:
    command = manifest["command"]
    trace_dir = Path(command[command.index("--trace-dir") + 1])
    return trace_dir / f"game_{game:04d}.jsonl"


def action_signature(row: dict) -> tuple:
    return (
        int(row["context"]),
        row.get("context_card_id"),
        row.get("effect_card_id"),
        tuple(int(value) for value in row["action"]),
    )


def next_log_card_ids(rows: list[dict], step: int, limit: int = 4) -> list[int]:
    card_ids: list[int] = []
    seen = 0
    for row in rows:
        if int(row["step"]) <= step:
            continue
        for log in row.get("logs", []):
            if log.get("cardId") is not None:
                card_ids.append(int(log["cardId"]))
        seen += 1
        if seen >= limit:
            break
    return card_ids


def next_log_attack_ids(rows: list[dict], step: int, limit: int = 4) -> list[int]:
    attack_ids: list[int] = []
    seen = 0
    for row in rows:
        if int(row["step"]) <= step:
            continue
        for log in row.get("logs", []):
            if log.get("attackId") is not None:
                attack_ids.append(int(log["attackId"]))
        seen += 1
        if seen >= limit:
            break
    return attack_ids


def first_policy_difference(
    baseline_path: Path, candidate_path: Path, seat: int
) -> dict | None:
    baseline_all = read_jsonl(baseline_path)
    candidate_all = read_jsonl(candidate_path)
    baseline = [row for row in baseline_all if int(row["player"]) == seat]
    candidate = [row for row in candidate_all if int(row["player"]) == seat]
    for index, (left, right) in enumerate(zip(baseline, candidate)):
        if action_signature(left) == action_signature(right):
            continue
        base_step = int(left["step"])
        candidate_step = int(right["step"])
        base_followup_ids = next_log_card_ids(baseline_all, base_step)
        candidate_followup_ids = next_log_card_ids(candidate_all, candidate_step)
        base_followup_attacks = next_log_attack_ids(baseline_all, base_step)
        candidate_followup_attacks = next_log_attack_ids(
            candidate_all, candidate_step
        )
        exact_rule1 = bool(
            int(left["context"]) == 2
            and int(right["context"]) == 2
            and left["action"] == []
            and len(right["action"]) == 1
            and 169 in right.get("own_hand_ids", [])
            and int(right.get("snapshot", {}).get("turn", -1)) == 0
        )
        exact_rule4 = bool(
            int(left["context"]) == 0
            and int(right["context"]) == 0
            and 1227 in base_followup_ids
            and any(
                card_id in candidate_followup_ids
                for card_id in (169, 190, 840, 8, 1244)
            )
        )
        exact_rule5_boss = bool(
            int(right["context"]) == 0 and 1182 in candidate_followup_ids
        )
        exact_rule5_direct = bool(
            int(right["context"]) == 0
            and any(
                attack_id in {223, 224, 253, 1212}
                for attack_id in candidate_followup_attacks
            )
        )
        if exact_rule1:
            rule = "RULE1_EXACTLY_ONE_DURALUDON_SETUP"
        elif exact_rule4:
            rule = "RULE4_PRE_LILLIE_EXACT_MATERIALIZATION"
        elif exact_rule5_boss:
            rule = "RULE5_UNIQUE_HIGHER_PRIZE_BOSS"
        elif exact_rule5_direct:
            rule = "RULE5_DIRECT_EXACT_CURRENT_WIN"
        else:
            rule = "UNCLASSIFIED_OR_RULE5_DIRECT_WIN"
        return {
            "policy_index": index,
            "rule": rule,
            "baseline_step": base_step,
            "candidate_step": candidate_step,
            "baseline_context": int(left["context"]),
            "candidate_context": int(right["context"]),
            "baseline_action": left["action"],
            "candidate_action": right["action"],
            "baseline_turn": left.get("snapshot", {}).get("turn"),
            "candidate_turn": right.get("snapshot", {}).get("turn"),
            "baseline_followup_card_ids": base_followup_ids,
            "candidate_followup_card_ids": candidate_followup_ids,
            "baseline_followup_attack_ids": base_followup_attacks,
            "candidate_followup_attack_ids": candidate_followup_attacks,
        }
    if len(baseline) != len(candidate):
        return {
            "policy_index": min(len(baseline), len(candidate)),
            "rule": "TRACE_LENGTH_ONLY",
            "baseline_policy_rows": len(baseline),
            "candidate_policy_rows": len(candidate),
        }
    return None


def bucket(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "baseline_wins": sum(row["baseline_win"] for row in rows),
        "candidate_wins": sum(row["candidate_win"] for row in rows),
        "delta": sum(row["candidate_win"] - row["baseline_win"] for row in rows),
        "gains": sum(
            row["baseline_win"] == 0 and row["candidate_win"] == 1
            for row in rows
        ),
        "regressions": sum(
            row["baseline_win"] == 1 and row["candidate_win"] == 0
            for row in rows
        ),
    }


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    paired: list[dict] = []
    manifests: dict[str, list[dict]] = {}
    reports: dict[str, dict] = {}
    raw_hashes: dict[str, dict[str, str]] = {}

    for panel in spec["panels"]:
        label = panel["label"]
        panel_root = RAW / panel["output"]
        with (panel_root / "paired_results.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            for row in csv.DictReader(handle):
                parsed = dict(row)
                parsed["panel"] = label
                for field in (
                    "seat",
                    "game",
                    "seed",
                    "baseline_result",
                    "candidate_result",
                    "baseline_win",
                    "candidate_win",
                    "baseline_steps",
                    "candidate_steps",
                ):
                    parsed[field] = int(parsed[field])
                paired.append(parsed)
        manifests[label] = read_jsonl(panel_root / "manifest.jsonl")
        reports[label] = json.loads(
            (panel_root / "report.json").read_text(encoding="utf-8")
        )
        raw_hashes[label] = {
            name: sha256(panel_root / name)
            for name in ("paired_results.csv", "manifest.jsonl", "report.json")
        }

    expected_keys: set[tuple[str, str, int, int]] = set()
    for panel in spec["panels"]:
        for opponent in panel["opponents"]:
            for seat in (0, 1):
                for game in range(int(panel["games_per_seat"])):
                    expected_keys.add(
                        (
                            panel["label"],
                            opponent["label"],
                            seat,
                            int(panel["seed_base"]) + game,
                        )
                    )
    actual_keys = [
        (row["panel"], row["opponent"], row["seat"], row["seed"])
        for row in paired
    ]
    win_flag_errors = sum(
        row["baseline_win"] != int(row["baseline_result"] == row["seat"])
        or row["candidate_win"] != int(row["candidate_result"] == row["seat"])
        for row in paired
    )

    summary_rows: list[dict] = []
    manifest_nonzero_exit = 0
    for panel, rows in manifests.items():
        for manifest in rows:
            manifest_nonzero_exit += int(manifest["exit_code"] != 0)
            command = manifest["command"]
            summary = Path(command[command.index("--summary") + 1])
            summary_rows.extend(read_jsonl(summary))

    by_manifest: dict[tuple[str, str, int, str], dict] = {}
    for panel, rows in manifests.items():
        for row in rows:
            by_manifest[(panel, row["opponent"], int(row["seat"]), row["role"])] = row

    duplicate_trace_mismatches = 0
    candidate_trace_differences: list[dict] = []
    outcome_differences: list[dict] = []
    for row in paired:
        key = (row["panel"], row["opponent"], row["seat"])
        baseline_a = trace_for(by_manifest[(*key, "baseline_a")], row["game"])
        baseline_b = trace_for(by_manifest[(*key, "baseline_b")], row["game"])
        candidate = trace_for(by_manifest[(*key, "candidate")], row["game"])
        baseline_hash = sha256(baseline_a)
        if baseline_hash != sha256(baseline_b):
            duplicate_trace_mismatches += 1
        first_difference = None
        if baseline_hash != sha256(candidate):
            first_difference = first_policy_difference(
                baseline_a, candidate, row["seat"]
            )
            candidate_trace_differences.append(
                {
                    "panel": row["panel"],
                    "opponent": row["opponent"],
                    "seat": row["seat"],
                    "game": row["game"],
                    "seed": row["seed"],
                    "baseline_win": row["baseline_win"],
                    "candidate_win": row["candidate_win"],
                    "first_difference": first_difference,
                }
            )
        if row["baseline_win"] != row["candidate_win"]:
            outcome_differences.append(
                {
                    "panel": row["panel"],
                    "opponent": row["opponent"],
                    "seat": row["seat"],
                    "game": row["game"],
                    "seed": row["seed"],
                    "direction": (
                        "gain" if row["candidate_win"] == 1 else "regression"
                    ),
                    "baseline_steps": row["baseline_steps"],
                    "candidate_steps": row["candidate_steps"],
                    "first_difference": first_difference,
                }
            )

    grouped: dict[str, dict[str, list[dict]]] = {
        "panel": defaultdict(list),
        "seat": defaultdict(list),
        "opponent": defaultdict(list),
        "panel_seat_opponent": defaultdict(list),
    }
    for row in paired:
        grouped["panel"][row["panel"]].append(row)
        grouped["seat"][str(row["seat"])].append(row)
        grouped["opponent"][row["opponent"]].append(row)
        grouped["panel_seat_opponent"][
            f"{row['panel']}|{row['opponent']}|seat{row['seat']}"
        ].append(row)
    buckets = {
        name: {key: bucket(values) for key, values in sorted(groups.items())}
        for name, groups in grouped.items()
    }

    baseline_wins = sum(row["baseline_win"] for row in paired)
    candidate_wins = sum(row["candidate_win"] for row in paired)
    gains = sum(
        row["baseline_win"] == 0 and row["candidate_win"] == 1
        for row in paired
    )
    regressions = sum(
        row["baseline_win"] == 1 and row["candidate_win"] == 0
        for row in paired
    )
    rule_counts: dict[str, int] = defaultdict(int)
    for row in candidate_trace_differences:
        difference = row["first_difference"]
        rule_counts[
            "NO_POLICY_DIFFERENCE" if difference is None else difference["rule"]
        ] += 1

    seat_gate = all(
        value["candidate_wins"] >= value["baseline_wins"] - 2
        for value in buckets["seat"].values()
    )
    adjacent_gate = all(
        value["candidate_wins"] >= value["baseline_wins"] - 5
        for opponent, value in buckets["opponent"].items()
        if opponent != "historical_silver"
    )
    mechanical = {
        "manifest_rows": sum(len(rows) for rows in manifests.values()),
        "manifest_nonzero_exit": manifest_nonzero_exit,
        "summary_rows": len(summary_rows),
        "not_started": sum(not bool(row.get("started")) for row in summary_rows),
        "action_errors": sum(int(row.get("action_errors", 0)) for row in summary_rows),
        "max_step_hits": sum(bool(row.get("hit_max_steps")) for row in summary_rows),
        "checked_report_invalid": sum(not report.get("valid") for report in reports.values()),
        "checked_duplicate_mismatches": sum(
            int(report.get("duplicate_mismatch_count", 0))
            for report in reports.values()
        ),
        "duplicate_byte_trace_mismatches": duplicate_trace_mismatches,
    }
    mirror = buckets["panel"]["historical_silver"]
    retention = {
        "candidate_wins_at_least_478": candidate_wins >= 478,
        "gains_at_least_regressions": gains >= regressions,
        "each_seat_drop_at_most_2": seat_gate,
        "mirror_at_least_98": mirror["candidate_wins"] >= 98,
        "each_adjacent_opponent_drop_at_most_5": adjacent_gate,
        "mechanical_zero": all(
            mechanical[key] == 0
            for key in (
                "manifest_nonzero_exit",
                "not_started",
                "action_errors",
                "max_step_hits",
                "checked_report_invalid",
                "checked_duplicate_mismatches",
                "duplicate_byte_trace_mismatches",
            )
        ),
        "schedule_exact": (
            len(paired) == len(set(actual_keys)) == len(expected_keys) == 760
            and set(actual_keys) == expected_keys
        ),
        "result_to_win_errors_zero": win_flag_errors == 0,
        "all_outcome_differences_have_policy_difference": all(
            row["first_difference"] is not None for row in outcome_differences
        ),
    }
    retention["pass_before_qualitative"] = all(retention.values())
    strengthened = {
        "candidate_wins_at_least_486": candidate_wins >= 486,
        "both_seats_nonworse": all(
            value["candidate_wins"] >= value["baseline_wins"]
            for value in buckets["seat"].values()
        ),
    }
    strengthened["pass"] = all(strengthened.values())

    result = {
        "spec_sha256": sha256(SPEC_PATH),
        "raw_hashes": raw_hashes,
        "row_count": len(paired),
        "unique_key_count": len(set(actual_keys)),
        "expected_key_count": len(expected_keys),
        "missing_keys": sorted(expected_keys - set(actual_keys)),
        "extra_keys": sorted(set(actual_keys) - expected_keys),
        "win_flag_errors": win_flag_errors,
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "delta_wins": candidate_wins - baseline_wins,
        "paired_gains": gains,
        "paired_regressions": regressions,
        "paired_ties": len(paired) - gains - regressions,
        "buckets": buckets,
        "mechanical": mechanical,
        "candidate_trace_difference_count": len(candidate_trace_differences),
        "candidate_trace_rule_counts": dict(sorted(rule_counts.items())),
        "unclassified_trace_differences": [
            row
            for row in candidate_trace_differences
            if row["first_difference"] is None
            or row["first_difference"]["rule"]
            in {"UNCLASSIFIED_OR_RULE5_DIRECT_WIN", "TRACE_LENGTH_ONLY"}
        ],
        "outcome_difference_count": len(outcome_differences),
        "outcome_differences": outcome_differences,
        "retention_gates_before_qualitative": retention,
        "strengthened_gates": strengthened,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
