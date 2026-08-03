from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TASK_DIRS = {
    "task6": ROOT / "fixed760_task6_raw",
    "task9": ROOT / "fixed760_task9_raw",
}
PANELS = ("historical_silver", "adjacent_population")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_rows(task: str) -> tuple[list[dict], dict]:
    root = TASK_DIRS[task]
    rows: list[dict] = []
    evidence = {"paired_csv": {}, "report": {}}
    for panel in PANELS:
        csv_path = root / panel / "paired_results.csv"
        report_path = root / panel / "report.json"
        if not csv_path.is_file() or not report_path.is_file():
            raise FileNotFoundError(f"incomplete {task}/{panel}")
        evidence["paired_csv"][panel] = {
            "path": str(csv_path),
            "sha256": sha256(csv_path),
        }
        report = json.loads(report_path.read_text(encoding="utf-8"))
        evidence["report"][panel] = {
            "path": str(report_path),
            "sha256": sha256(report_path),
            "valid": report.get("valid"),
            "invalid_reasons": report.get("invalid_reasons"),
            "duplicate_mismatch_count": report.get("duplicate_mismatch_count"),
            "reported_aggregates": report.get("aggregates"),
        }
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            for raw in csv.DictReader(handle):
                row = dict(raw)
                for key in (
                    "seed_base",
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
                    row[key] = int(row[key])
                row["panel"] = panel
                row["task"] = task
                expected_baseline = int(row["baseline_result"] == row["seat"])
                expected_candidate = int(row["candidate_result"] == row["seat"])
                if row["baseline_win"] != expected_baseline:
                    raise AssertionError(f"baseline_win mismatch: {row}")
                if row["candidate_win"] != expected_candidate:
                    raise AssertionError(f"candidate_win mismatch: {row}")
                rows.append(row)
    return rows, evidence


def schedule_key(row: dict) -> tuple:
    return row["panel"], row["opponent"], row["seat"], row["seed"]


def summarize(rows: list[dict]) -> dict:
    def one(group: list[dict]) -> dict:
        baseline = sum(row["baseline_win"] for row in group)
        candidate = sum(row["candidate_win"] for row in group)
        gains = sum(
            row["baseline_win"] == 0 and row["candidate_win"] == 1
            for row in group
        )
        regressions = sum(
            row["baseline_win"] == 1 and row["candidate_win"] == 0
            for row in group
        )
        return {
            "games": len(group),
            "baseline_wins": baseline,
            "candidate_wins": candidate,
            "delta_wins": candidate - baseline,
            "paired_gains": gains,
            "paired_regressions": regressions,
            "paired_ties": len(group) - gains - regressions,
            "baseline_max_steps": sum(row["baseline_steps"] >= 1000 for row in group),
            "candidate_max_steps": sum(row["candidate_steps"] >= 1000 for row in group),
        }

    dimensions = {
        "overall": lambda row: "all",
        "panel": lambda row: row["panel"],
        "opponent": lambda row: row["opponent"],
        "seat": lambda row: str(row["seat"]),
        "panel_seat": lambda row: f'{row["panel"]}|seat{row["seat"]}',
        "opponent_seat": lambda row: f'{row["opponent"]}|seat{row["seat"]}',
    }
    output = {}
    for name, key_fn in dimensions.items():
        buckets: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            buckets[key_fn(row)].append(row)
        output[name] = {key: one(group) for key, group in sorted(buckets.items())}
    return output


def main() -> None:
    all_rows = {}
    evidence = {}
    for task in TASK_DIRS:
        rows, task_evidence = read_rows(task)
        if len(rows) != 760:
            raise AssertionError(f"{task}: expected 760 rows, got {len(rows)}")
        keys = [schedule_key(row) for row in rows]
        if len(set(keys)) != 760:
            raise AssertionError(f"{task}: duplicate schedule keys")
        all_rows[task] = rows
        evidence[task] = task_evidence

    task6 = {schedule_key(row): row for row in all_rows["task6"]}
    task9 = {schedule_key(row): row for row in all_rows["task9"]}
    if set(task6) != set(task9):
        raise AssertionError("Task6 and Task9 schedule mismatch")

    baseline_result_mismatches = []
    direct = []
    for key in sorted(task6):
        left = task6[key]
        right = task9[key]
        if (
            left["baseline_result"],
            left["baseline_win"],
            left["baseline_steps"],
        ) != (
            right["baseline_result"],
            right["baseline_win"],
            right["baseline_steps"],
        ):
            baseline_result_mismatches.append({
                "key": key,
                "task6": {
                    "result": left["baseline_result"],
                    "win": left["baseline_win"],
                    "steps": left["baseline_steps"],
                },
                "task9": {
                    "result": right["baseline_result"],
                    "win": right["baseline_win"],
                    "steps": right["baseline_steps"],
                },
            })
        direct.append({
            "panel": left["panel"],
            "opponent": left["opponent"],
            "seat": left["seat"],
            "seed": left["seed"],
            "task6_win": left["candidate_win"],
            "task9_win": right["candidate_win"],
            "task6_result": left["candidate_result"],
            "task9_result": right["candidate_result"],
            "task6_steps": left["candidate_steps"],
            "task9_steps": right["candidate_steps"],
        })

    def direct_summary(group: list[dict]) -> dict:
        task6_wins = sum(row["task6_win"] for row in group)
        task9_wins = sum(row["task9_win"] for row in group)
        gains = sum(row["task6_win"] == 0 and row["task9_win"] == 1 for row in group)
        regressions = sum(row["task6_win"] == 1 and row["task9_win"] == 0 for row in group)
        return {
            "games": len(group),
            "task6_wins": task6_wins,
            "task9_wins": task9_wins,
            "delta_wins": task9_wins - task6_wins,
            "task9_gains": gains,
            "task9_regressions": regressions,
            "ties": len(group) - gains - regressions,
        }

    direct_dimensions = {
        "overall": lambda row: "all",
        "panel": lambda row: row["panel"],
        "opponent": lambda row: row["opponent"],
        "seat": lambda row: str(row["seat"]),
        "opponent_seat": lambda row: f'{row["opponent"]}|seat{row["seat"]}',
    }
    direct_summaries = {}
    for name, key_fn in direct_dimensions.items():
        buckets = defaultdict(list)
        for row in direct:
            buckets[key_fn(row)].append(row)
        direct_summaries[name] = {
            key: direct_summary(group) for key, group in sorted(buckets.items())
        }

    direct_discordant = [
        row for row in direct if row["task6_win"] != row["task9_win"]
    ]
    output = {
        "valid": True,
        "expected_rows_per_task": 760,
        "schedule_equal": True,
        "baseline_result_mismatch_count": len(baseline_result_mismatches),
        "baseline_result_mismatches": baseline_result_mismatches,
        "evidence": evidence,
        "historical_silver_vs_task6": summarize(all_rows["task6"]),
        "historical_silver_vs_task9": summarize(all_rows["task9"]),
        "task6_vs_task9": direct_summaries,
        "task6_vs_task9_discordant": direct_discordant,
    }
    json_path = ROOT / "ROOT_RECOMPUTE_FIXED760.json"
    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = ROOT / "TASK6_VS_TASK9_DISCORDANT_KEYS.csv"
    fieldnames = list(direct[0])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(direct_discordant)
    print(json.dumps({
        "json": str(json_path),
        "json_sha256": sha256(json_path),
        "discordant_csv": str(csv_path),
        "discordant_csv_sha256": sha256(csv_path),
        "task6_overall": output["historical_silver_vs_task6"]["overall"]["all"],
        "task9_overall": output["historical_silver_vs_task9"]["overall"]["all"],
        "task6_vs_task9": output["task6_vs_task9"]["overall"]["all"],
    }, indent=2))


if __name__ == "__main__":
    main()
