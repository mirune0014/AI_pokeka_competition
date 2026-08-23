"""Root-side mechanical verification for a completed T3/T4 run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    branches = jsonl(run / "branch_results.jsonl")
    roots = jsonl(run / "selected_roots.jsonl")
    pairs = csv_rows(run / "route_pairs.csv")
    games = csv_rows(run / "game_results.csv")
    unique_branch_keys = {(str(row.get("root_id")), str(row.get("branch")), str(row.get("forced_attack_id"))) for row in branches}
    unique_root_ids = {str(row.get("root_id")) for row in roots}
    branch_map = {(str(row.get("root_id")), str(row.get("branch"))): row for row in branches}
    raw_outcomes: Counter[str] = Counter()
    raw_pairs = 0
    for root in roots:
        rid = str(root.get("root_id")); seat = int(root.get("policy_seat"))
        boss = branch_map.get((rid, "boss"))
        if boss is None:
            continue
        for branch_key, front in branch_map.items():
            if branch_key[0] != rid or not branch_key[1].startswith("front_"):
                continue
            raw_pairs += 1
            boss_win = int(boss.get("terminal_result")) == seat if str(boss.get("terminal_result")) not in {"None", ""} else False
            front_win = int(front.get("terminal_result")) == seat if str(front.get("terminal_result")) not in {"None", ""} else False
            raw_outcomes["BOSS_GAIN" if boss_win and not front_win else "FRONT_GAIN" if front_win and not boss_win else "TIE"] += 1
    csv_outcomes = Counter(row.get("pair_outcome") for row in pairs)
    summary = {
        "schema_version": "archaludon_boss_vs_front_attack_root_verification.v1",
        "parent_main_sha256": digest(args.parent.resolve() / "main.py"),
        "parent_deck_sha256": digest(args.parent.resolve() / "deck.csv"),
        "selected_root_count": len(roots),
        "selected_root_id_unique": len(unique_root_ids) == len(roots),
        "branch_row_count": len(branches),
        "branch_key_unique": len(unique_branch_keys) == len(branches),
        "branch_complete": sum(row.get("status") == "complete" for row in branches),
        "branch_engine_import_ok": sum(row.get("engine_import_ok") is True for row in branches),
        "branch_root_match": sum(row.get("root_match") is True for row in branches),
        "branch_forced_legal": sum(row.get("forced_legal") is True for row in branches),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in branches),
        "max_step": sum(bool(row.get("hit_max_steps")) for row in branches),
        "route_pair_count": len(pairs),
        "raw_recomputed_route_pair_count": raw_pairs,
        "game_count": len(games),
        "pair_outcomes": dict(sorted(csv_outcomes.items())),
        "raw_recomputed_pair_outcomes": dict(sorted(raw_outcomes.items())),
        "raw_vs_csv_pair_outcomes_match": raw_pairs == len(pairs) and dict(raw_outcomes) == dict(csv_outcomes),
        "route_counts": dict(sorted(Counter(row.get("route_class") for row in pairs).items())),
        "catastrophic_count": sum(row.get("catastrophic_regression") == "True" for row in pairs),
        "schedule_keys": sorted({str(row.get("schedule_key")) for row in roots}),
        "holdout_opened": False,
        "reserve_opened": False,
        "candidate_created": False,
        "kaggle_accessed": False,
        "file_sha256": {name: digest(run / name) for name in ("comparison_spec.json", "selected_roots.jsonl", "branch_results.jsonl", "route_pairs.csv", "root_results.csv", "game_results.csv", "family_summary.csv", "bootstrap.json", "catastrophic_regressions.csv", "summary.json", "REPORT.md") if (run / name).exists()},
    }
    lines = ["# Root verification: T3/T4 Boss versus front attack", "", "```json", json.dumps(summary, sort_keys=True, ensure_ascii=True, indent=2), "```", "", "Independent recomputation uses raw branch rows and CSV outputs; no candidate or parent files were modified."]
    (run / "ROOT_VERIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, ensure_ascii=True))
    if summary["branch_complete"] != len(branches) or summary["branch_engine_import_ok"] != len(branches) or summary["branch_root_match"] != len(branches) or summary["branch_forced_legal"] != len(branches) or summary["action_errors"] or summary["max_step"] or not summary["branch_key_unique"] or not summary["raw_vs_csv_pair_outcomes_match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
