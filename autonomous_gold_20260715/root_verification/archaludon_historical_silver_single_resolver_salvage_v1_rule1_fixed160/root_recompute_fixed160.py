from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RAW = REPO / "autonomous_gold_20260715" / "evaluations" / "archaludon_historical_silver_single_resolver_salvage_v1" / "rule1_fixed160_raw"
PANELS = ("historical_silver", "adjacent_population")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def first_policy_difference(left: Path, right: Path, seat: int) -> dict | None:
    left_rows = [row for row in read_jsonl(left) if int(row["player"]) == seat]
    right_rows = [row for row in read_jsonl(right) if int(row["player"]) == seat]
    for index, (a, b) in enumerate(zip(left_rows, right_rows)):
        signature_a = (a["context"], a.get("context_card_id"), a.get("effect_card_id"), a["action"])
        signature_b = (b["context"], b.get("context_card_id"), b.get("effect_card_id"), b["action"])
        if signature_a != signature_b:
            return {"policy_index": index, "baseline": a, "candidate": b}
    if len(left_rows) != len(right_rows):
        return {
            "policy_index": min(len(left_rows), len(right_rows)),
            "baseline_length": len(left_rows),
            "candidate_length": len(right_rows),
        }
    return None


def main() -> None:
    paired: list[dict] = []
    manifest_rows: list[dict] = []
    summary_rows: list[dict] = []
    first_differences: list[dict] = []

    for panel in PANELS:
        panel_root = RAW / panel
        with (panel_root / "paired_results.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                parsed = dict(row)
                parsed["panel"] = panel
                for field in ("seat", "game", "seed", "baseline_win", "candidate_win"):
                    parsed[field] = int(parsed[field])
                paired.append(parsed)

        manifest = read_jsonl(panel_root / "manifest.jsonl")
        manifest_rows.extend({**row, "panel": panel} for row in manifest)
        by_cell = {(row["opponent"], int(row["seat"]), row["role"]): row for row in manifest}

        for row in manifest:
            command = row["command"]
            summary = Path(command[command.index("--summary") + 1])
            for item in read_jsonl(summary):
                summary_rows.append({**item, "panel": panel, "role": row["role"], "opponent": row["opponent"], "seat": int(row["seat"])})

        for row in paired:
            if row["panel"] != panel:
                continue
            opponent = row["opponent"]
            seat = row["seat"]
            game = row["game"]
            base = by_cell[(opponent, seat, "baseline_a")]
            cand = by_cell[(opponent, seat, "candidate")]
            base_command = base["command"]
            cand_command = cand["command"]
            base_trace = Path(base_command[base_command.index("--trace-dir") + 1]) / f"game_{game:04d}.jsonl"
            cand_trace = Path(cand_command[cand_command.index("--trace-dir") + 1]) / f"game_{game:04d}.jsonl"
            difference = first_policy_difference(base_trace, cand_trace, seat)
            if difference is not None:
                first_differences.append({
                    "panel": panel,
                    "opponent": opponent,
                    "seat": seat,
                    "game": game,
                    "seed": row["seed"],
                    **difference,
                })

    keys = [(row["panel"], row["opponent"], row["seat"], row["seed"]) for row in paired]
    unique_keys = len(set(keys))
    baseline_wins = sum(row["baseline_win"] for row in paired)
    candidate_wins = sum(row["candidate_win"] for row in paired)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in paired)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in paired)

    buckets: dict[str, dict] = {}
    for label, selector in (
        ("seat", lambda row: str(row["seat"])),
        ("opponent", lambda row: row["opponent"]),
    ):
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in paired:
            grouped[selector(row)].append(row)
        buckets[label] = {
            key: {
                "games": len(rows),
                "baseline_wins": sum(row["baseline_win"] for row in rows),
                "candidate_wins": sum(row["candidate_win"] for row in rows),
                "delta": sum(row["candidate_win"] - row["baseline_win"] for row in rows),
                "gains": sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in rows),
                "regressions": sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in rows),
            }
            for key, rows in sorted(grouped.items())
        }

    mechanical = {
        "manifest_rows": len(manifest_rows),
        "manifest_nonzero_exit": sum(int(row["exit_code"]) != 0 for row in manifest_rows),
        "summary_rows": len(summary_rows),
        "not_started": sum(not bool(row.get("started")) for row in summary_rows),
        "action_errors": sum(int(row.get("action_errors", 0)) for row in summary_rows),
        "max_step_hits": sum(bool(row.get("hit_max_steps")) for row in summary_rows),
    }

    starts_by_seat = Counter()
    classified: list[dict] = []
    for diff in first_differences:
        base = diff.get("baseline")
        cand = diff.get("candidate")
        exact_rule1 = bool(
            base
            and cand
            and int(base["context"]) == 2
            and int(cand["context"]) == 2
            and base["action"] == []
            and len(cand["action"]) == 1
            and 169 in cand.get("own_hand_ids", [])
            and int(cand.get("snapshot", {}).get("turn", -1)) == 0
        )
        if exact_rule1:
            starts_by_seat[str(diff["seat"])] += 1
        classified.append({
            "panel": diff["panel"],
            "opponent": diff["opponent"],
            "seat": diff["seat"],
            "game": diff["game"],
            "seed": diff["seed"],
            "exact_rule1_shape": exact_rule1,
            "baseline_context": None if not base else base["context"],
            "candidate_context": None if not cand else cand["context"],
            "baseline_action": None if not base else base["action"],
            "candidate_action": None if not cand else cand["action"],
            "candidate_turn": None if not cand else cand.get("snapshot", {}).get("turn"),
            "candidate_hand_has_duraludon": None if not cand else 169 in cand.get("own_hand_ids", []),
        })

    report = {
        "row_count": len(paired),
        "unique_key_count": unique_keys,
        "schedule_exact": len(paired) == unique_keys == 160,
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "delta_wins": candidate_wins - baseline_wins,
        "paired_gains": gains,
        "paired_regressions": regressions,
        "paired_ties": len(paired) - gains - regressions,
        "buckets": buckets,
        "mechanical": mechanical,
        "first_difference_count": len(first_differences),
        "exact_rule1_first_difference_count": sum(item["exact_rule1_shape"] for item in classified),
        "starts_by_seat": dict(starts_by_seat),
        "all_first_differences_rule1_shape": all(item["exact_rule1_shape"] for item in classified),
        "stage_gate": {
            "schedule": len(paired) == unique_keys == 160,
            "mechanical_zero": all(value == 0 for key, value in mechanical.items() if key in {"manifest_nonzero_exit", "not_started", "action_errors", "max_step_hits"}),
            "natural_starts_at_least_4": len(first_differences) >= 4,
            "both_seats_exercised": all(starts_by_seat.get(str(seat), 0) >= 1 for seat in (0, 1)),
            "gains_ge_regressions": gains >= regressions,
            "no_seat_or_opponent_minus_3": all(bucket["delta"] > -3 for group in buckets.values() for bucket in group.values()),
            "all_differences_classified": all(item["exact_rule1_shape"] for item in classified),
        },
        "first_differences": classified,
    }
    report["stage_gate"]["pass"] = all(report["stage_gate"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
