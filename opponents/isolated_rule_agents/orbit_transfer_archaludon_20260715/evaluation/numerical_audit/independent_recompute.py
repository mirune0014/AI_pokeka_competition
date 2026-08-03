from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / "opponents" / "isolated_rule_agents" / "orbit_transfer_archaludon_20260715" / "evaluation"
OUT = Path(__file__).with_name("independent_recompute.json")
PAIRED_FIELDS = [
    "seed_base", "opponent", "seat", "game", "seed",
    "baseline_result", "candidate_result", "baseline_win", "candidate_win",
    "baseline_steps", "candidate_steps",
]
GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
CONFIGS = {
    "historical_silver": {
        "directory": EVAL / "historical_silver",
        "seed_base": 271828182,
        "games": 100,
        "block_size": 50,
        "opponents": ["historical_silver"],
        "hashes": {
            "paired_results.csv": "00233D11B66F1D1EC2EC44008F80D6515BBEA9CF30AC15936A8C3A1289472C1E",
            "report.json": "F54D80C469309306C2558E9F92F4ED26A8832BBEE4A906A827F0FCA22B96A48B",
            "manifest.jsonl": "CB1246BB224D1F95D19C47E7085EE14689495F1642F41E9F9F4DAC0B2FF4684C",
        },
    },
    "adjacent_population": {
        "directory": EVAL / "adjacent_population",
        "seed_base": 271958313,
        "games": 40,
        "block_size": 40,
        "opponents": [
            "arch_peak", "arch_shumpei", "cynthia_v23", "kang_v23",
            "marnie_kazuki", "marnie_tonakai",
        ],
        "hashes": {
            "paired_results.csv": "B859124EAF67BB96A72EEF1D9C597B8606206F3612977395AF1B74595A11F974",
            "report.json": "6F35113E195795FA24E55400AB8BEB705A9A53AF4D6037B07FA9EC041E309E80",
            "manifest.jsonl": "3D8FCF20EDEE086854B3806D9B245B24577C1982909B3994BF03D4019BCAED72",
        },
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(rows: list[dict]) -> dict:
    baseline = sum(row["baseline_win"] for row in rows)
    candidate = sum(row["candidate_win"] for row in rows)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in rows)
    losses = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in rows)
    both_wins = sum(row["baseline_win"] == row["candidate_win"] == 1 for row in rows)
    both_losses = sum(row["baseline_win"] == row["candidate_win"] == 0 for row in rows)
    discordant = gains + losses
    if discordant:
        tail = sum(math.comb(discordant, k) for k in range(min(gains, losses) + 1))
        mcnemar = min(1.0, 2.0 * tail / (2**discordant))
    else:
        mcnemar = 1.0
    return {
        "rows": len(rows), "baseline_wins": baseline, "candidate_wins": candidate,
        "delta_wins": candidate - baseline, "gains": gains, "losses": losses,
        "outcome_ties": len(rows) - discordant, "both_wins": both_wins,
        "both_losses": both_losses, "discordant": discordant,
        "mcnemar_exact_two_sided_p": mcnemar,
        "discordance_rate_one_sided_95pct_upper":
            (1.0 - 0.05 ** (1.0 / len(rows))) if rows and discordant == 0 else None,
    }


def grouped(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    return [dict(zip(fields, key)) | summarize(values) for key, values in sorted(groups.items())]


def step_groups(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if row["baseline_win"] == 0 and row["candidate_win"] == 1:
            outcome = "gain"
        elif row["baseline_win"] == 1 and row["candidate_win"] == 0:
            outcome = "loss"
        elif row["baseline_win"] == 1:
            outcome = "both_win"
        else:
            outcome = "both_loss"
        groups[(outcome, row["opponent"], row["seat"])].append(row)
    output = []
    for (outcome, opponent, seat), values in sorted(groups.items()):
        deltas = [row["candidate_steps"] - row["baseline_steps"] for row in values]
        output.append({
            "outcome": outcome, "opponent": opponent, "seat": seat, "rows": len(values),
            "step_equal": sum(delta == 0 for delta in deltas),
            "step_different": sum(delta != 0 for delta in deltas),
            "candidate_fewer": sum(delta < 0 for delta in deltas),
            "candidate_more": sum(delta > 0 for delta in deltas),
            "candidate_minus_baseline_steps_sum": sum(deltas),
            "candidate_minus_baseline_steps_min": min(deltas),
            "candidate_minus_baseline_steps_max": max(deltas),
        })
    return output


def value_after(command: list[str], flag: str) -> str | None:
    try:
        return command[command.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def audit_panel(name: str, cfg: dict) -> tuple[dict, list[dict]]:
    directory: Path = cfg["directory"]
    hashes = {filename: sha256(directory / filename) for filename in cfg["hashes"]}
    hash_matches = {filename: hashes[filename] == expected for filename, expected in cfg["hashes"].items()}

    with (directory / "paired_results.csv").open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames
        rows = []
        for raw in reader:
            rows.append({field: (raw[field] if field == "opponent" else int(raw[field])) for field in PAIRED_FIELDS})

    key_counts = Counter((r["seed_base"], r["opponent"], r["seat"], r["seed"]) for r in rows)
    actual_schedule = set(key_counts)
    expected_schedule = {
        (cfg["seed_base"], opponent, seat, cfg["seed_base"] + game)
        for opponent in cfg["opponents"] for seat in (0, 1) for game in range(cfg["games"])
    }
    game_seed_valid = all(r["game"] in range(cfg["games"]) and r["seed"] == cfg["seed_base"] + r["game"] for r in rows)
    win_fields_valid = all(
        r["baseline_win"] == int(r["baseline_result"] == r["seat"])
        and r["candidate_win"] == int(r["candidate_result"] == r["seat"])
        for r in rows
    )
    blocks: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        blocks[(row["opponent"], row["seat"], row["game"] // cfg["block_size"])].append(row)
    block_summaries = [
        {"opponent": key[0], "seat": key[1], "block": key[2], **summarize(values)}
        for key, values in sorted(blocks.items())
    ]

    manifest = read_jsonl(directory / "manifest.jsonl")
    expected_manifest = [
        (opponent, seat, role)
        for opponent in cfg["opponents"] for seat in (0, 1)
        for role in ("baseline_a", "baseline_b", "candidate")
    ]
    command_issues = []
    summary_rows_total = 0
    summary_action_errors = 0
    summary_max_step_hits = 0
    summary_started_false = 0
    summary_schedule_issues = 0
    summary_by_cell_role: dict[tuple, list[dict]] = {}
    for index, row in enumerate(manifest):
        command = row["command"]
        expected_cell = expected_manifest[index] if index < len(expected_manifest) else None
        checks = {
            "sequence": row["sequence"] == index,
            "cell_role": expected_cell == (row["opponent"], row["seat"], row["role"]),
            "exit_code": row["exit_code"] == 0,
            "battle_runner": len(command) > 1 and Path(command[1]).name == "run_local_battle.py",
            "engine": value_after(command, "--engine-dir") == "_local_generated\analysis_outputs\\cynthia_v9_vs_v11_poffin_role_selection_20260713\\seeded_engine",
            "games": value_after(command, "--games") == str(cfg["games"]),
            "max_steps": value_after(command, "--max-steps") == "1000",
            "seed_base": value_after(command, "--seed-base") == str(cfg["seed_base"]),
            "engine_seed": "--engine-seed" in command,
        }
        if not all(checks.values()):
            command_issues.append({"manifest_index": index, "checks": checks})
        summary_path = Path(value_after(command, "--summary") or "")
        summary = read_jsonl(summary_path) if summary_path.is_file() else []
        summary_by_cell_role[(row["opponent"], row["seat"], row["role"])] = summary
        summary_rows_total += len(summary)
        summary_action_errors += sum(int(item.get("action_errors", 0)) for item in summary)
        summary_max_step_hits += sum(bool(item.get("hit_max_steps")) for item in summary)
        summary_started_false += sum(not bool(item.get("started")) for item in summary)
        if len(summary) != cfg["games"]:
            summary_schedule_issues += 1
        for game, item in enumerate(summary):
            if item.get("game") != game or item.get("seed") != cfg["seed_base"] + game:
                summary_schedule_issues += 1

    duplicate_control_mismatches = 0
    for opponent in cfg["opponents"]:
        for seat in (0, 1):
            left = summary_by_cell_role.get((opponent, seat, "baseline_a"), [])
            right = summary_by_cell_role.get((opponent, seat, "baseline_b"), [])
            for game in range(max(len(left), len(right))):
                a = left[game] if game < len(left) else {}
                b = right[game] if game < len(right) else {}
                if tuple(a.get(field) for field in GAME_FIELDS) != tuple(b.get(field) for field in GAME_FIELDS):
                    duplicate_control_mismatches += 1

    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    total = summarize(rows)
    runner_aggregate_matches = report.get("aggregates") == {
        "baseline_wins": total["baseline_wins"], "candidate_wins": total["candidate_wins"],
        "games": total["rows"], "delta_wins": total["delta_wins"],
    }
    result = {
        "input_hashes": hashes,
        "input_hashes_match_frozen": hash_matches,
        "paired_header_exact": header == PAIRED_FIELDS,
        "total": total,
        "by_opponent": grouped(rows, ("opponent",)),
        "by_seat": grouped(rows, ("seat",)),
        "blocks": block_summaries,
        "step_differences_by_outcome_opponent_seat": step_groups(rows),
        "schedule": {
            "expected_rows": len(expected_schedule), "actual_rows": len(rows),
            "unique_keys": len(actual_schedule),
            "duplicate_key_count": sum(count - 1 for count in key_counts.values() if count > 1),
            "missing_keys": [list(key) for key in sorted(expected_schedule - actual_schedule)],
            "extra_keys": [list(key) for key in sorted(actual_schedule - expected_schedule)],
            "exact": actual_schedule == expected_schedule and len(rows) == len(expected_schedule),
            "game_seed_valid": game_seed_valid, "win_fields_valid": win_fields_valid,
        },
        "execution": {
            "manifest_rows": len(manifest), "expected_manifest_rows": len(expected_manifest),
            "exit_codes": dict(sorted(Counter(str(row["exit_code"]) for row in manifest).items())),
            "command_issue_count": len(command_issues), "command_issues": command_issues,
            "summary_rows_total": summary_rows_total,
            "expected_summary_rows_total": len(expected_manifest) * cfg["games"],
            "summary_action_errors": summary_action_errors,
            "summary_max_step_hits": summary_max_step_hits,
            "summary_started_false": summary_started_false,
            "summary_schedule_issue_count": summary_schedule_issues,
            "duplicate_control_mismatches": duplicate_control_mismatches,
        },
        "runner_report": {
            "valid": report.get("valid"), "invalid_reasons": report.get("invalid_reasons"),
            "duplicate_mismatch_count": report.get("duplicate_mismatch_count"),
            "aggregate_matches_independent": runner_aggregate_matches,
        },
    }
    return result, rows


def main() -> None:
    panels = {}
    all_rows = []
    for name, config in CONFIGS.items():
        panels[name], rows = audit_panel(name, config)
        all_rows.extend(rows)
    total_step_different = sum(
        item["step_different"]
        for panel in panels.values()
        for item in panel["step_differences_by_outcome_opponent_seat"]
    )
    total_candidate_fewer = sum(
        item["candidate_fewer"]
        for panel in panels.values()
        for item in panel["step_differences_by_outcome_opponent_seat"]
    )
    output = {
        "method": "independent Python stdlib recomputation from raw paired CSV, manifest, report, and every summary JSONL",
        "panels": panels,
        "combined": summarize(all_rows) | {
            "step_different": total_step_different,
            "candidate_fewer": total_candidate_fewer,
            "candidate_more": total_step_different - total_candidate_fewer,
            "strength_gate_has_required_gain": any(
                row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in all_rows
            ),
        },
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(output["combined"], indent=2))


if __name__ == "__main__":
    main()
