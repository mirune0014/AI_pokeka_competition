"""Run the fixed 320-game schedule for three behavior-cloned actor seeds."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

from .frozen_sources import find_repo_root, seeded_engine_dir, sha256_file


REPO_ROOT = find_repo_root()
RUN_LOCAL_BATTLE = REPO_ROOT / "tools" / "run_local_battle.py"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _resolve(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _opponents(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    population = _load_json(_resolve(spec["fixed_evaluation"]["opponents_spec"]))
    return [dict(row) for row in population["opponents"]]


def _training_arms(
    training_root: Path,
    *,
    report_glob: str = "bc_seed*.json",
    arm_prefix: str = "bc_seed",
) -> list[dict[str, Any]]:
    arms: list[dict[str, Any]] = []
    for report_path in sorted((training_root / "training").glob(report_glob)):
        report = _load_json(report_path)
        seed = int(report["seed"])
        checkpoint = Path(report["checkpoint"]["path"])
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        checkpoint_sha = sha256_file(checkpoint)
        if checkpoint_sha != str(report["checkpoint"]["sha256"]).upper():
            raise ValueError(f"BC checkpoint/report hash mismatch for seed {seed}")
        arms.append(
            {
                "arm_id": f"{arm_prefix}{seed}",
                "seed": seed,
                "checkpoint": checkpoint.resolve(),
                "checkpoint_sha256": checkpoint_sha,
                "training_report": report_path.resolve(),
            }
        )
    if len(arms) != 3 or len({arm["seed"] for arm in arms}) != 3:
        raise ValueError("fixed BC evaluation requires exactly three training seeds")
    return arms


def _validate_summary(
    rows: Sequence[Mapping[str, Any]],
    expected_seeds: Sequence[int],
) -> None:
    if len(rows) != len(expected_seeds):
        raise ValueError("BC evaluation summary row count mismatch")
    if [int(row.get("seed", -1)) for row in rows] != list(expected_seeds):
        raise ValueError("BC evaluation seed sequence mismatch")
    for row in rows:
        if (
            row.get("started") is not True
            or not isinstance(row.get("action_errors"), int)
            or isinstance(row.get("action_errors"), bool)
            or not isinstance(row.get("hit_max_steps"), bool)
            or not isinstance(row.get("turn"), int)
            or isinstance(row.get("turn"), bool)
        ):
            raise ValueError("BC evaluation summary row is incomplete")


def _audit_rows(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("deployment-audit-*.jsonl")):
        rows.extend(_read_jsonl(path))
    if not rows:
        raise ValueError(f"BC deployment audit is empty: {directory}")
    return rows


def _fallback_category(reason: Any) -> str:
    text = "" if reason is None else str(reason)
    if "representability_failure" in text:
        return "representability_failure"
    if "unsupported_cardinality" in text:
        return "unsupported_cardinality"
    if "model_or_selection_failure" in text:
        return "model_or_selection_failure"
    if "schema_or_encoding_failure" in text:
        return "schema_or_encoding_failure"
    if "explicit_major_safety" in text:
        return "other_explicit_major_safety"
    if "unselectable_actor_surface" in text:
        return "unselectable_actor_surface"
    return "other"


def _run_cell(
    *,
    spec: Mapping[str, Any],
    arm: Mapping[str, Any],
    opponent: Mapping[str, Any],
    seat: int,
    output_root: Path,
) -> dict[str, Any]:
    arm_id = str(arm["arm_id"])
    opponent_id = str(opponent["id"])
    cell_id = f"{opponent_id}_seat{seat}"
    cell_root = output_root / "evaluation" / arm_id
    summary_path = cell_root / "summaries" / f"{cell_id}.jsonl"
    audit_dir = cell_root / "audits" / cell_id
    log_path = output_root / "logs" / f"{arm_id}_{cell_id}.log"
    receipt_path = cell_root / "receipts" / f"{cell_id}.json"
    if any(path.exists() for path in (summary_path, audit_dir, log_path, receipt_path)):
        raise FileExistsError(f"BC evaluation cell output already exists: {arm_id}/{cell_id}")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    policy_dir = _resolve(spec["deployment"]["policy_dir"])
    opponent_dir = _resolve(str(opponent["path"]))
    if seat == 0:
        agent_a, agent_b = policy_dir, opponent_dir
    else:
        agent_a, agent_b = opponent_dir, policy_dir
    expected_seeds = [int(value) for value in spec["fixed_evaluation"]["seeds"]]
    command = [
        sys.executable,
        "-B",
        str(RUN_LOCAL_BATTLE),
        "--engine-dir",
        str(seeded_engine_dir(REPO_ROOT)),
        "--agent-a",
        str(agent_a),
        "--deck-a",
        str(agent_a / "deck.csv"),
        "--agent-b",
        str(agent_b),
        "--deck-b",
        str(agent_b / "deck.csv"),
        "--games",
        str(len(expected_seeds)),
        "--max-steps",
        "1000",
        "--seed-base",
        str(int(spec["fixed_evaluation"]["seed_base"])),
        "--engine-seed",
        "--summary",
        str(summary_path),
        "--no-trace",
    ]
    environment = os.environ.copy()
    environment.update(
        {
            str(spec["deployment"].get("checkpoint_env", "ARCHALUDON_BC_CHECKPOINT")): str(arm["checkpoint"]),
            str(spec["deployment"].get("device_env", "ARCHALUDON_BC_DEVICE")): "cpu",
            "ARCHALUDON_RL_DEPLOYMENT_AUDIT_DIR": str(audit_dir),
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    duration = time.monotonic() - started
    log_path.write_text(
        "COMMAND\n" + json.dumps(command) + "\nSTDOUT\n" + completed.stdout + "\nSTDERR\n" + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"BC evaluation failed for {arm_id}/{cell_id} with exit {completed.returncode}; see {log_path}"
        )
    rows = _read_jsonl(summary_path)
    _validate_summary(rows, expected_seeds)
    audit = _audit_rows(audit_dir)
    fallback_rows = [row for row in audit if row.get("fallback_used") is True]
    checkpoint_sha = str(arm["checkpoint_sha256"])
    for row in audit:
        if (
            row.get("schema_version") != "archaludon-deployment-audit-v1"
            or row.get("checkpoint_sha256") != checkpoint_sha
            or row.get("collection_mode") != "deployment"
            or row.get("residuals_finite") is not True
            or row.get("teacher_call_count") != 1
        ):
            raise ValueError(f"BC deployment row invalid in {arm_id}/{cell_id}")
        if row.get("protected") and row.get("action") != row.get("teacher_action"):
            raise ValueError(f"BC protected fallback changed action in {arm_id}/{cell_id}")
    fallback_categories = Counter(
        _fallback_category(row.get("fallback_reason")) for row in fallback_rows
    )
    receipt = {
        "arm_id": arm_id,
        "opponent": opponent_id,
        "seat": seat,
        "games": len(rows),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint_sha256": checkpoint_sha,
        "decision_count": len(audit),
        "fallback_count": len(fallback_rows),
        "fallback_categories": dict(sorted(fallback_categories.items())),
        "model_failure_count": sum(row.get("model_failure_kind") is not None for row in audit),
        "duration_seconds": duration,
    }
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


def _rollup(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    games = len(records)
    wins = sum(int(row["win"]) for row in records)
    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games,
        "mean_turns": sum(int(row["turn"]) for row in records) / games,
        "action_errors": sum(int(row["action_errors"]) for row in records),
        "max_step_hits": sum(int(row["max_step_hit"]) for row in records),
    }


def _aggregate_arm(
    *,
    spec: Mapping[str, Any],
    arm: Mapping[str, Any],
    opponents: Sequence[Mapping[str, Any]],
    output_root: Path,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    fallback_count = 0
    decision_count = 0
    model_failures = 0
    fallback_categories: Counter[str] = Counter()
    expected_seeds = [int(value) for value in spec["fixed_evaluation"]["seeds"]]
    for opponent in opponents:
        opponent_id = str(opponent["id"])
        for seat in (0, 1):
            cell_id = f"{opponent_id}_seat{seat}"
            root = output_root / "evaluation" / str(arm["arm_id"])
            summary_path = root / "summaries" / f"{cell_id}.jsonl"
            receipt = _load_json(root / "receipts" / f"{cell_id}.json")
            rows = _read_jsonl(summary_path)
            _validate_summary(rows, expected_seeds)
            if receipt["summary_sha256"] != sha256_file(summary_path):
                raise ValueError(f"BC evaluation receipt mismatch: {arm['arm_id']}/{cell_id}")
            fallback_count += int(receipt["fallback_count"])
            decision_count += int(receipt["decision_count"])
            model_failures += int(receipt["model_failure_count"])
            fallback_categories.update(receipt["fallback_categories"])
            for row in rows:
                records.append(
                    {
                        "opponent": opponent_id,
                        "seat": seat,
                        "seed": int(row["seed"]),
                        "win": int(row.get("result") == seat),
                        "turn": int(row["turn"]),
                        "action_errors": int(row["action_errors"]),
                        "max_step_hit": int(row["hit_max_steps"]),
                    }
                )
    keys = {(row["opponent"], row["seat"], row["seed"]) for row in records}
    if len(records) != 320 or len(keys) != 320:
        raise ValueError(f"BC fixed schedule is incomplete for {arm['arm_id']}")
    by_opponent = {
        opponent_id: _rollup([row for row in records if row["opponent"] == opponent_id])
        for opponent_id in sorted({row["opponent"] for row in records})
    }
    by_seat = {
        str(seat): _rollup([row for row in records if row["seat"] == seat])
        for seat in (0, 1)
    }
    return {
        **arm,
        "checkpoint": str(arm["checkpoint"]),
        "training_report": str(arm["training_report"]),
        "overall": _rollup(records),
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "decision_count": decision_count,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_count / decision_count,
        "fallback_categories": dict(sorted(fallback_categories.items())),
        "model_failure_count": model_failures,
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    spec = _load_json(Path(args.spec))
    output_root = Path(args.output_dir).resolve()
    if output_root.exists():
        raise FileExistsError("BC evaluation output directory already exists")
    output_root.mkdir(parents=True)
    arms = _training_arms(
        Path(args.training_root),
        report_glob=str(spec["deployment"].get("training_report_glob", "bc_seed*.json")),
        arm_prefix=str(spec["deployment"].get("arm_prefix", "bc_seed")),
    )
    opponents = _opponents(spec)
    jobs = [
        (arm, opponent, seat)
        for arm in arms
        for opponent in opponents
        for seat in (0, 1)
    ]
    completed_jobs = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                _run_cell,
                spec=spec,
                arm=arm,
                opponent=opponent,
                seat=seat,
                output_root=output_root,
            ): (arm["arm_id"], opponent["id"], seat)
            for arm, opponent, seat in jobs
        }
        for future in as_completed(futures):
            label = futures[future]
            future.result()
            completed_jobs += 1
            print(
                json.dumps(
                    {"completed_cells": completed_jobs, "total_cells": len(jobs), "last": label},
                    ensure_ascii=False,
                ),
                flush=True,
            )
    arm_results = [
        _aggregate_arm(
            spec=spec,
            arm=arm,
            opponents=opponents,
            output_root=output_root,
        )
        for arm in arms
    ]
    baseline_source = _load_json(Path(args.baseline_result))
    baseline = dict(baseline_source["baseline"])
    thresholds = spec["provisional_pass"]["fixed_320_no_clear_collapse"]
    for arm in arm_results:
        arm["comparison_to_iteration004"] = {
            "overall_win_rate_delta": arm["overall"]["win_rate"] - baseline["overall"]["win_rate"],
            "by_opponent_win_rate_delta": {
                opponent_id: arm["by_opponent"][opponent_id]["win_rate"] - baseline["by_opponent"][opponent_id]["win_rate"]
                for opponent_id in sorted(arm["by_opponent"])
            },
            "by_seat_win_rate_delta": {
                seat: arm["by_seat"][seat]["win_rate"] - baseline["by_seat"][seat]["win_rate"]
                for seat in ("0", "1")
            },
        }
        comparison = arm["comparison_to_iteration004"]
        arm["fixed_320_no_clear_collapse"] = bool(
            comparison["overall_win_rate_delta"]
            >= -float(thresholds["overall_drop_from_iteration004_maximum_percentage_points"]) / 100.0
            and min(comparison["by_opponent_win_rate_delta"].values())
            >= -float(thresholds["opponent_drop_maximum_percentage_points"]) / 100.0
            and min(comparison["by_seat_win_rate_delta"].values())
            >= -float(thresholds["seat_drop_maximum_percentage_points"]) / 100.0
            and arm["overall"]["action_errors"] == int(thresholds["action_errors"])
        )
    result = {
        "schema_version": "behavior-cloning-fixed-evaluation-v1",
        "fixed_schedule_games_per_checkpoint": 320,
        "baseline": baseline,
        "arms": arm_results,
    }
    result_path = output_root / "evaluation_summary.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": str(result_path), "arms": arm_results}, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--training-root", required=True)
    parser.add_argument("--baseline-result", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 1 <= args.workers <= 4:
        raise ValueError("BC evaluation workers must be in [1,4]")
    evaluate(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
