from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW = (
    ROOT
    / "archaludon"
    / "evaluations"
    / "archaludon_certified_late_boundary_ultra_ball_route_v3"
    / "fixed160_raw"
)
PANELS = ("historical_silver", "adjacent_population")


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def player_rows(path: Path, seat: int) -> list[dict]:
    return [row for row in read_jsonl(path) if int(row["player"]) == seat]


def first_policy_difference(left: Path, right: Path, seat: int) -> dict | None:
    baseline = player_rows(left, seat)
    candidate = player_rows(right, seat)
    for index, (a, b) in enumerate(zip(baseline, candidate)):
        a_signature = (
            int(a["context"]),
            a.get("context_card_id"),
            a.get("effect_card_id"),
            tuple(a["action"]),
        )
        b_signature = (
            int(b["context"]),
            b.get("context_card_id"),
            b.get("effect_card_id"),
            tuple(b["action"]),
        )
        if a_signature != b_signature:
            return {
                "policy_index": index,
                "baseline_step": int(a["step"]),
                "candidate_step": int(b["step"]),
                "baseline_context": int(a["context"]),
                "candidate_context": int(b["context"]),
                "baseline_action": a["action"],
                "candidate_action": b["action"],
                "turn": int(b["snapshot"]["turn"]),
                "turn_action_count": int(b["snapshot"]["turn_action_count"]),
            }
    if len(baseline) != len(candidate):
        return {
            "policy_index": min(len(baseline), len(candidate)),
            "baseline_policy_rows": len(baseline),
            "candidate_policy_rows": len(candidate),
        }
    return None


def main() -> None:
    paired: list[dict] = []
    manifest_rows: list[dict] = []
    summary_rows: list[dict] = []
    differences: list[dict] = []
    duplicate_mismatches = 0

    for panel in PANELS:
        panel_root = RAW / panel
        with (panel_root / "paired_results.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            for row in csv.DictReader(handle):
                parsed = {**row, "panel": panel}
                for field in (
                    "seat",
                    "game",
                    "seed",
                    "baseline_win",
                    "candidate_win",
                    "baseline_steps",
                    "candidate_steps",
                ):
                    parsed[field] = int(parsed[field])
                paired.append(parsed)

        report = json.loads((panel_root / "report.json").read_text(encoding="utf-8"))
        if not report.get("valid") or report.get("invalid_reasons"):
            raise AssertionError((panel, report))
        duplicate_mismatches += int(report["duplicate_mismatch_count"])

        manifest = read_jsonl(panel_root / "manifest.jsonl")
        manifest_rows.extend({**row, "panel": panel} for row in manifest)
        by_cell = {
            (row["opponent"], int(row["seat"]), row["role"]): row
            for row in manifest
        }
        for row in manifest:
            command = row["command"]
            summary = Path(command[command.index("--summary") + 1])
            summary_rows.extend(
                {
                    **item,
                    "panel": panel,
                    "opponent": row["opponent"],
                    "seat": int(row["seat"]),
                    "role": row["role"],
                }
                for item in read_jsonl(summary)
            )

        for row in [item for item in paired if item["panel"] == panel]:
            key = (row["opponent"], row["seat"])
            baseline = by_cell[(*key, "baseline_a")]
            candidate = by_cell[(*key, "candidate")]
            baseline_command = baseline["command"]
            candidate_command = candidate["command"]
            baseline_trace = (
                Path(baseline_command[baseline_command.index("--trace-dir") + 1])
                / f"game_{row['game']:04d}.jsonl"
            )
            candidate_trace = (
                Path(candidate_command[candidate_command.index("--trace-dir") + 1])
                / f"game_{row['game']:04d}.jsonl"
            )
            difference = first_policy_difference(
                baseline_trace, candidate_trace, row["seat"]
            )
            if difference is not None:
                differences.append(
                    {
                        "panel": panel,
                        "opponent": row["opponent"],
                        "seat": row["seat"],
                        "game": row["game"],
                        "seed": row["seed"],
                        **difference,
                    }
                )

    keys = [
        (row["panel"], row["opponent"], row["seat"], row["seed"])
        for row in paired
    ]
    gains = sum(
        row["baseline_win"] == 0 and row["candidate_win"] == 1
        for row in paired
    )
    regressions = sum(
        row["baseline_win"] == 1 and row["candidate_win"] == 0
        for row in paired
    )

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
                "delta": sum(
                    row["candidate_win"] - row["baseline_win"] for row in rows
                ),
            }
            for key, rows in sorted(grouped.items())
        }

    output = {
        "rows": len(paired),
        "unique_keys": len(set(keys)),
        "schedule_exact": len(paired) == len(set(keys)) == 160,
        "baseline_wins": sum(row["baseline_win"] for row in paired),
        "candidate_wins": sum(row["candidate_win"] for row in paired),
        "paired_gains": gains,
        "paired_regressions": regressions,
        "paired_ties": len(paired) - gains - regressions,
        "buckets": buckets,
        "mechanical": {
            "manifest_rows": len(manifest_rows),
            "manifest_nonzero_exit": sum(
                int(row["exit_code"]) != 0 for row in manifest_rows
            ),
            "summary_rows": len(summary_rows),
            "not_started": sum(not bool(row.get("started")) for row in summary_rows),
            "action_errors": sum(
                int(row.get("action_errors", 0)) for row in summary_rows
            ),
            "max_step_hits": sum(
                bool(row.get("hit_max_steps")) for row in summary_rows
            ),
            "duplicate_mismatches": duplicate_mismatches,
        },
        "first_difference_count": len(differences),
        "first_differences": differences,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
