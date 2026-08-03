"""Run the precommitted 4/12/24-epoch PPO comparison in one batch.

Fresh-rollout collection, checkpoint training, checked deployment evaluation,
and aggregate-only reporting are separate stages. Individual games are never
emitted or interpreted by this module.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from .frozen_sources import find_repo_root, seeded_engine_dir


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = find_repo_root().resolve()
RUN_LOCAL_BATTLE = REPO_ROOT / "infrastructure" / "tools" / "run_local_battle.py"
THREAD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "PYTHONUNBUFFERED": "1",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row at {path}:{line_number}")
        rows.append(value)
    return rows


def _last_json_object(path: Path) -> dict[str, Any]:
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError(f"no JSON object found in log: {path}")


def _paths(spec: Mapping[str, Any]) -> dict[str, Path]:
    outputs = spec["outputs"]
    return {
        "raw": _resolve(str(outputs["raw_root"])),
        "result_json": _resolve(str(outputs["result_json"])),
        "result_markdown": _resolve(str(outputs["result_markdown"])),
        "initial_checkpoint": _resolve(
            str(spec["bindings"]["initial_checkpoint"]["path"])
        ),
        "population": _resolve(
            str(spec["bindings"]["opponent_population"]["path"])
        ),
        "runtime_agent": _resolve(str(spec["evaluation"]["policy_dir"])),
        "engine": seeded_engine_dir(REPO_ROOT).resolve(),
    }


def _verify_binding(binding: Mapping[str, Any]) -> None:
    path = _resolve(str(binding["path"]))
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    expected = str(binding["sha256"]).upper()
    if actual != expected:
        raise ValueError(f"hash mismatch for {path}: {actual} != {expected}")


def _reserved_seeds(spec: Mapping[str, Any]) -> set[int]:
    training = {
        int(row["seed_base"]) + offset
        for row in spec["training"]["replicates"]
        for offset in range(int(spec["training"]["episodes_per_seat"]))
    }
    evaluation = {int(seed) for seed in spec["evaluation"]["seeds"]}
    if training & evaluation:
        raise ValueError("training and evaluation seeds overlap")
    return training | evaluation


def _assert_seeds_unused(
    spec: Mapping[str, Any], *, output_root: Path
) -> int:
    reserved = _reserved_seeds(spec)
    checked = 0
    candidate_test_outputs = CANDIDATE_ROOT / "test_outputs"
    if not candidate_test_outputs.exists():
        return checked
    for manifest_path in candidate_test_outputs.rglob("run_manifest.json"):
        try:
            manifest_path.resolve().relative_to(output_root.resolve())
            continue
        except ValueError:
            pass
        manifest = _load_json(manifest_path)
        used = {
            int(row["seed"])
            for row in manifest.get("schedule", [])
            if isinstance(row, dict) and isinstance(row.get("seed"), int)
        }
        overlap = sorted(reserved & used)
        if overlap:
            raise ValueError(
                f"precommitted seed already used in {manifest_path}: {overlap}"
            )
        checked += 1
    return checked


def validate_plan(spec: Mapping[str, Any]) -> dict[str, Any]:
    if spec.get("schema_version") != "archaludon-rl-epoch-sweep-v1":
        raise ValueError("unexpected epoch sweep schema")
    for binding in (
        spec["bindings"]["initial_checkpoint"],
        spec["bindings"]["opponent_population"],
        *spec["bindings"]["code"],
    ):
        _verify_binding(binding)

    epochs = [int(value) for value in spec["training"]["epochs"]]
    replicates = list(spec["training"]["replicates"])
    evaluation_seeds = [int(value) for value in spec["evaluation"]["seeds"]]
    opponents = _load_json(_paths(spec)["population"])["opponents"]
    if epochs != [4, 12, 24] or len(replicates) != 3:
        raise ValueError("the sweep must be epochs 4/12/24 with three seeds")
    if len({int(row["seed_base"]) for row in replicates}) != 3:
        raise ValueError("training seed bases must be unique")
    if len(evaluation_seeds) != 20 or len(set(evaluation_seeds)) != 20:
        raise ValueError("evaluation must use exactly 20 unique seeds")
    if len(opponents) != 8:
        raise ValueError("the locked population must contain eight opponents")
    _reserved_seeds(spec)

    train_games_per_seed = (
        len(opponents)
        * 2
        * int(spec["training"]["episodes_per_seat"])
    )
    evaluation_games_per_arm = len(opponents) * 2 * len(evaluation_seeds)
    expected = spec["expected_counts"]
    computed = {
        "fresh_rollouts": len(replicates),
        "training_checkpoints": len(epochs) * len(replicates),
        "training_games": train_games_per_seed * len(replicates),
        "evaluation_arms": 1 + len(epochs) * len(replicates),
        "evaluation_games_per_arm": evaluation_games_per_arm,
        "evaluation_games": evaluation_games_per_arm
        * (1 + len(epochs) * len(replicates)),
    }
    computed["total_games"] = (
        computed["training_games"] + computed["evaluation_games"]
    )
    for key, value in computed.items():
        if int(expected[key]) != value:
            raise ValueError(f"expected_counts.{key} mismatch")
    if evaluation_games_per_arm < 300:
        raise ValueError("evaluation must contain at least 300 games per arm")
    checked_manifests = _assert_seeds_unused(
        spec, output_root=_paths(spec)["raw"]
    )
    return {
        **computed,
        "opponents": len(opponents),
        "seats": [0, 1],
        "evaluation_seed_min": min(evaluation_seeds),
        "evaluation_seed_max": max(evaluation_seeds),
        "checked_prior_manifests": checked_manifests,
        "hash_bindings_verified": 2 + len(spec["bindings"]["code"]),
    }


def _run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    timeout_seconds: int,
    extra_environment: Mapping[str, str] | None = None,
) -> float:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(THREAD_ENVIRONMENT)
    if extra_environment:
        environment.update(extra_environment)
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"command": list(command)}, ensure_ascii=True) + "\n")
        log.flush()
        completed = subprocess.run(
            list(command),
            cwd=str(cwd),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    duration = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"subprocess failed with exit {completed.returncode}; see {log_path}"
        )
    return duration


def _run_parallel(
    items: Sequence[Any],
    *,
    workers: int,
    label: str,
    function: Callable[[Any], Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    results: list[Mapping[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(function, item): item for item in items}
        for completed_index, future in enumerate(
            concurrent.futures.as_completed(pending), 1
        ):
            try:
                result = future.result()
            except Exception:
                for other in pending:
                    other.cancel()
                raise
            results.append(result)
            print(
                json.dumps(
                    {
                        "event": "completed",
                        "stage": label,
                        "completed": completed_index,
                        "total": len(items),
                        **dict(result),
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                flush=True,
            )
    return results


def _manifest_complete(
    path: Path,
    *,
    expected_checkpoint_sha256: str,
    expected_count: int,
) -> dict[str, Any]:
    manifest = _load_json(path)
    schedule = manifest.get("schedule")
    receipts = manifest.get("episode_receipts")
    if (
        manifest.get("complete") is not True
        or manifest.get("checkpoint_sha256") != expected_checkpoint_sha256
        or not isinstance(schedule, list)
        or not isinstance(receipts, list)
        or len(schedule) != expected_count
        or len(receipts) != expected_count
    ):
        raise ValueError(f"incomplete or mismatched rollout manifest: {path}")
    schedule_keys = {
        (row["opponent_id"], int(row["seat"]), int(row["seed"]))
        for row in schedule
    }
    receipt_keys = {
        (row["opponent_id"], int(row["seat"]), int(row["seed"]))
        for row in receipts
    }
    if len(schedule_keys) != expected_count or schedule_keys != receipt_keys:
        raise ValueError(f"rollout schedule/receipt mismatch: {path}")
    return manifest


def _rollout_jobs(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in spec["training"]["replicates"]]


def _checkpoint_jobs(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "arm_id": f"e{int(epoch):02d}_{replicate['id']}",
            "epochs": int(epoch),
            "replicate": str(replicate["id"]),
            "seed_base": int(replicate["seed_base"]),
        }
        for epoch in spec["training"]["epochs"]
        for replicate in spec["training"]["replicates"]
    ]


def _collect_one_rollout(
    spec: Mapping[str, Any], job: Mapping[str, Any]
) -> Mapping[str, Any]:
    paths = _paths(spec)
    raw = paths["raw"]
    replicate = str(job["id"])
    output_dir = raw / "training" / "rollouts" / replicate
    manifest_path = output_dir / "run_manifest.json"
    receipt_path = raw / "training" / "receipts" / f"rollout_{replicate}.json"
    expected_count = int(spec["training"]["games_per_rollout"])
    checkpoint_hash = str(
        spec["bindings"]["initial_checkpoint"]["sha256"]
    ).upper()
    if receipt_path.is_file():
        _manifest_complete(
            manifest_path,
            expected_checkpoint_sha256=checkpoint_hash,
            expected_count=expected_count,
        )
        return {"job": replicate, "status": "skipped"}
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"incomplete rollout output exists: {output_dir}")

    command = [
        sys.executable,
        "-B",
        "-m",
        "archaludon_rl.collect_rollouts",
        "--checkpoint",
        str(paths["initial_checkpoint"]),
        "--opponent-population",
        str(paths["population"]),
        "--output-dir",
        str(output_dir),
        "--run-id",
        f"epoch-sweep-train-{replicate}",
        "--seed-base",
        str(int(job["seed_base"])),
        "--episodes-per-seat",
        str(int(spec["training"]["episodes_per_seat"])),
        "--seat",
        "both",
        "--max-steps",
        str(int(spec["runtime"]["max_steps"])),
        "--timeout-seconds",
        str(spec["runtime"]["model_timeout_seconds"]),
        "--device",
        "cpu",
        "--preflight-require-zero-residuals",
    ]
    log_path = raw / "logs" / f"collect_{replicate}.log"
    duration = _run_process(
        command,
        cwd=CANDIDATE_ROOT,
        log_path=log_path,
        timeout_seconds=int(spec["runtime"]["subprocess_timeout_seconds"]),
    )
    manifest = _manifest_complete(
        manifest_path,
        expected_checkpoint_sha256=checkpoint_hash,
        expected_count=expected_count,
    )
    _write_json(
        receipt_path,
        {
            "replicate": replicate,
            "seed_base": int(job["seed_base"]),
            "games": expected_count,
            "manifest_sha256": _sha256(manifest_path),
            "dataset_sha256": manifest["dataset_sha256"],
            "duration_seconds": duration,
        },
    )
    return {"job": replicate, "status": "ran"}


def _train_one_checkpoint(
    spec: Mapping[str, Any], job: Mapping[str, Any]
) -> Mapping[str, Any]:
    paths = _paths(spec)
    raw = paths["raw"]
    arm_id = str(job["arm_id"])
    replicate = str(job["replicate"])
    checkpoint_path = raw / "checkpoints" / f"{arm_id}.pt"
    receipt_path = raw / "training" / "receipts" / f"train_{arm_id}.json"
    manifest_path = (
        raw / "training" / "rollouts" / replicate / "run_manifest.json"
    )
    input_hash = str(spec["bindings"]["initial_checkpoint"]["sha256"]).upper()
    _manifest_complete(
        manifest_path,
        expected_checkpoint_sha256=input_hash,
        expected_count=int(spec["training"]["games_per_rollout"]),
    )
    if receipt_path.is_file():
        receipt = _load_json(receipt_path)
        if (
            checkpoint_path.is_file()
            and _sha256(checkpoint_path)
            == str(receipt["output_checkpoint_sha256"]).upper()
            and int(receipt["epochs"]) == int(job["epochs"])
        ):
            return {"job": arm_id, "status": "skipped"}
        raise ValueError(f"checkpoint receipt mismatch: {receipt_path}")
    if checkpoint_path.exists():
        raise FileExistsError(f"unreceipted checkpoint exists: {checkpoint_path}")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-B",
        "-m",
        "archaludon_rl.train_ppo",
        "--input-checkpoint",
        str(paths["initial_checkpoint"]),
        "--manifest",
        str(manifest_path),
        "--output-checkpoint",
        str(checkpoint_path),
        "--device",
        "cpu",
        "--epochs",
        str(int(job["epochs"])),
    ]
    log_path = raw / "logs" / f"train_{arm_id}.log"
    duration = _run_process(
        command,
        cwd=CANDIDATE_ROOT,
        log_path=log_path,
        timeout_seconds=int(spec["runtime"]["subprocess_timeout_seconds"]),
    )
    report = _last_json_object(log_path)
    checkpoint_hash = _sha256(checkpoint_path)
    if str(report.get("output_checkpoint_sha256", "")).upper() != checkpoint_hash:
        raise ValueError(f"trainer/checkpoint hash mismatch for {arm_id}")
    _write_json(
        receipt_path,
        {
            "arm_id": arm_id,
            "epochs": int(job["epochs"]),
            "replicate": replicate,
            "seed_base": int(job["seed_base"]),
            "input_checkpoint_sha256": input_hash,
            "rollout_manifest_sha256": _sha256(manifest_path),
            "output_checkpoint_sha256": checkpoint_hash,
            "duration_seconds": duration,
        },
    )
    return {"job": arm_id, "status": "ran"}


def run_rollouts(spec: Mapping[str, Any], workers: int) -> None:
    _run_parallel(
        _rollout_jobs(spec),
        workers=1,
        label="fresh_rollouts",
        function=lambda job: _collect_one_rollout(spec, job),
    )


def run_training(spec: Mapping[str, Any], workers: int) -> None:
    _run_parallel(
        _checkpoint_jobs(spec),
        workers=workers,
        label="checkpoint_training",
        function=lambda job: _train_one_checkpoint(spec, job),
    )


def _population_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in _load_json(_paths(spec)["population"])["opponents"]
    ]


def _evaluation_arms(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = _paths(spec)
    arms: list[dict[str, Any]] = [
        {
            "arm_id": "iteration004",
            "epochs": 0,
            "replicate": "baseline",
            "training_seed_base": None,
            "checkpoint_path": paths["initial_checkpoint"],
            "checkpoint_sha256": str(
                spec["bindings"]["initial_checkpoint"]["sha256"]
            ).upper(),
        }
    ]
    for job in _checkpoint_jobs(spec):
        receipt_path = (
            paths["raw"]
            / "training"
            / "receipts"
            / f"train_{job['arm_id']}.json"
        )
        receipt = _load_json(receipt_path)
        checkpoint_path = (
            paths["raw"] / "checkpoints" / f"{job['arm_id']}.pt"
        )
        checkpoint_hash = _sha256(checkpoint_path)
        if (
            checkpoint_hash
            != str(receipt["output_checkpoint_sha256"]).upper()
        ):
            raise ValueError(f"checkpoint receipt mismatch: {job['arm_id']}")
        arms.append(
            {
                **job,
                "training_seed_base": int(job["seed_base"]),
                "checkpoint_path": checkpoint_path,
                "checkpoint_sha256": checkpoint_hash,
            }
        )
    return arms


def _evaluation_jobs(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {**arm, "opponent": opponent, "seat": seat}
        for arm in _evaluation_arms(spec)
        for opponent in _population_rows(spec)
        for seat in (0, 1)
    ]


def _audit_rows(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("deployment-audit-*.jsonl")):
        rows.extend(_read_jsonl(path))
    if not rows:
        raise ValueError(f"deployment audit contains no rows: {directory}")
    return rows


def _severe_abnormal_count(
    rows: Sequence[Mapping[str, Any]], *, checkpoint_sha256: str
) -> int:
    severe = 0
    for row in rows:
        if (
            row.get("schema_version") != "archaludon-deployment-audit-v1"
            or row.get("collection_mode") != "deployment"
            or row.get("checkpoint_sha256") != checkpoint_sha256
            or not isinstance(row.get("protected"), bool)
            or not isinstance(row.get("action"), list)
            or not isinstance(row.get("teacher_action"), list)
        ):
            raise ValueError("deployment audit structural mismatch")
        severe += int(
            row["protected"] and row["action"] != row["teacher_action"]
        )
    return severe


def _validate_evaluation_rows(
    rows: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> None:
    expected_seeds = [int(seed) for seed in spec["evaluation"]["seeds"]]
    if len(rows) != len(expected_seeds):
        raise ValueError("evaluation summary row count mismatch")
    if [int(row.get("seed", -1)) for row in rows] != expected_seeds:
        raise ValueError("evaluation summary seed sequence mismatch")
    for row in rows:
        if (
            row.get("started") is not True
            or not isinstance(row.get("action_errors"), int)
            or isinstance(row.get("action_errors"), bool)
            or not isinstance(row.get("hit_max_steps"), bool)
            or not isinstance(row.get("turn"), int)
            or isinstance(row.get("turn"), bool)
        ):
            raise ValueError("evaluation summary row is incomplete")


def _evaluate_one_cell(
    spec: Mapping[str, Any], job: Mapping[str, Any]
) -> Mapping[str, Any]:
    paths = _paths(spec)
    raw = paths["raw"]
    arm_id = str(job["arm_id"])
    opponent = dict(job["opponent"])
    opponent_id = str(opponent["id"])
    seat = int(job["seat"])
    cell_id = f"{opponent_id}_seat{seat}"
    arm_root = raw / "evaluation" / arm_id
    summary_path = arm_root / "summaries" / f"{cell_id}.jsonl"
    audit_dir = arm_root / "audits" / cell_id
    receipt_path = arm_root / "receipts" / f"{cell_id}.json"
    checkpoint_path = Path(job["checkpoint_path"]).resolve()
    checkpoint_hash = str(job["checkpoint_sha256"]).upper()
    expected_games = int(spec["evaluation"]["games_per_cell"])

    if receipt_path.is_file():
        receipt = _load_json(receipt_path)
        rows = _read_jsonl(summary_path)
        _validate_evaluation_rows(rows, spec)
        audit = _audit_rows(audit_dir)
        if (
            _sha256(summary_path) != str(receipt["summary_sha256"]).upper()
            or checkpoint_hash != str(receipt["checkpoint_sha256"]).upper()
            or len(rows) != expected_games
            or len(audit) != int(receipt["decision_count"])
        ):
            raise ValueError(f"evaluation receipt mismatch: {receipt_path}")
        return {"job": f"{arm_id}/{cell_id}", "status": "skipped"}
    if summary_path.exists() or (
        audit_dir.exists() and any(audit_dir.iterdir())
    ):
        raise FileExistsError(
            f"incomplete evaluation cell exists: {arm_id}/{cell_id}"
        )

    policy_dir = paths["runtime_agent"]
    opponent_dir = _resolve(str(opponent["path"]))
    if seat == 0:
        agent_a, agent_b = policy_dir, opponent_dir
    else:
        agent_a, agent_b = opponent_dir, policy_dir
    command = [
        sys.executable,
        "-B",
        str(RUN_LOCAL_BATTLE),
        "--engine-dir",
        str(paths["engine"]),
        "--agent-a",
        str(agent_a),
        "--deck-a",
        str(agent_a / "deck.csv"),
        "--agent-b",
        str(agent_b),
        "--deck-b",
        str(agent_b / "deck.csv"),
        "--games",
        str(expected_games),
        "--max-steps",
        str(int(spec["runtime"]["max_steps"])),
        "--seed-base",
        str(int(spec["evaluation"]["seed_base"])),
        "--engine-seed",
        "--summary",
        str(summary_path),
        "--no-trace",
    ]
    log_path = raw / "logs" / f"eval_{arm_id}_{cell_id}.log"
    duration = _run_process(
        command,
        cwd=REPO_ROOT,
        log_path=log_path,
        timeout_seconds=int(spec["runtime"]["subprocess_timeout_seconds"]),
        extra_environment={
            "ARCHALUDON_RL_CHECKPOINT": str(checkpoint_path),
            "ARCHALUDON_RL_DEVICE": "cpu",
            "ARCHALUDON_RL_DEPLOYMENT_AUDIT_DIR": str(audit_dir),
        },
    )
    rows = _read_jsonl(summary_path)
    _validate_evaluation_rows(rows, spec)
    audit = _audit_rows(audit_dir)
    severe = _severe_abnormal_count(
        audit, checkpoint_sha256=checkpoint_hash
    )
    _write_json(
        receipt_path,
        {
            "arm_id": arm_id,
            "opponent": opponent_id,
            "seat": seat,
            "games": len(rows),
            "checkpoint_sha256": checkpoint_hash,
            "summary_sha256": _sha256(summary_path),
            "decision_count": len(audit),
            "severe_abnormal_actions": severe,
            "duration_seconds": duration,
        },
    )
    return {"job": f"{arm_id}/{cell_id}", "status": "ran"}


def run_evaluation(spec: Mapping[str, Any], workers: int) -> None:
    _run_parallel(
        _evaluation_jobs(spec),
        workers=workers,
        label="checked_evaluation_cells",
        function=lambda job: _evaluate_one_cell(spec, job),
    )


def _load_arm_cells(
    spec: Mapping[str, Any], arm: Mapping[str, Any]
) -> list[dict[str, Any]]:
    raw = _paths(spec)["raw"]
    arm_id = str(arm["arm_id"])
    checkpoint_hash = str(arm["checkpoint_sha256"]).upper()
    cells: list[dict[str, Any]] = []
    for opponent in _population_rows(spec):
        opponent_id = str(opponent["id"])
        for seat in (0, 1):
            cell_id = f"{opponent_id}_seat{seat}"
            arm_root = raw / "evaluation" / arm_id
            summary_path = arm_root / "summaries" / f"{cell_id}.jsonl"
            audit_dir = arm_root / "audits" / cell_id
            receipt_path = arm_root / "receipts" / f"{cell_id}.json"
            receipt = _load_json(receipt_path)
            rows = _read_jsonl(summary_path)
            _validate_evaluation_rows(rows, spec)
            audit = _audit_rows(audit_dir)
            severe = _severe_abnormal_count(
                audit, checkpoint_sha256=checkpoint_hash
            )
            if (
                receipt.get("checkpoint_sha256") != checkpoint_hash
                or receipt.get("summary_sha256") != _sha256(summary_path)
                or int(receipt.get("decision_count", -1)) != len(audit)
                or int(receipt.get("severe_abnormal_actions", -1)) != severe
            ):
                raise ValueError(f"evaluation receipt mismatch: {receipt_path}")
            records = [
                {
                    "opponent": opponent_id,
                    "seat": seat,
                    "seed": int(row["seed"]),
                    "win": int(row.get("result") == seat),
                    "turn": int(row["turn"]),
                    "action_errors": int(row["action_errors"]),
                    "max_step_hit": int(row["hit_max_steps"]),
                }
                for row in rows
            ]
            cells.append(
                {
                    "opponent": opponent_id,
                    "seat": seat,
                    "records": records,
                    "decision_count": len(audit),
                    "severe_abnormal_actions": severe,
                }
            )
    expected = int(spec["evaluation"]["games_per_arm"])
    keys = {
        (row["opponent"], row["seat"], row["seed"])
        for cell in cells
        for row in cell["records"]
    }
    if len(keys) != expected:
        raise ValueError(f"evaluation key count mismatch for {arm_id}")
    return cells


def _rollup(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    records = [
        row
        for cell in cells
        for row in cell["records"]
    ]
    games = len(records)
    decisions = sum(int(cell["decision_count"]) for cell in cells)
    severe = sum(
        int(cell["severe_abnormal_actions"]) for cell in cells
    )
    if not games or not decisions:
        raise ValueError("cannot aggregate an empty evaluation")
    wins = sum(int(row["win"]) for row in records)
    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games,
        "mean_turns": sum(int(row["turn"]) for row in records) / games,
        "action_errors": sum(
            int(row["action_errors"]) for row in records
        ),
        "max_step_hits": sum(int(row["max_step_hit"]) for row in records),
        "severe_abnormal_actions": severe,
        "decision_count": decisions,
        "severe_abnormal_action_rate": severe / decisions,
    }


def _group_rollups(
    cells: Sequence[Mapping[str, Any]], key: str
) -> dict[str, dict[str, Any]]:
    values = sorted({cell[key] for cell in cells}, key=str)
    return {
        str(value): _rollup(
            [cell for cell in cells if cell[key] == value]
        )
        for value in values
    }


def _win_map(cells: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int, int], int]:
    return {
        (str(row["opponent"]), int(row["seat"]), int(row["seed"])): int(
            row["win"]
        )
        for cell in cells
        for row in cell["records"]
    }


def _paired_delta(
    cells: Sequence[Mapping[str, Any]],
    baseline_wins: Mapping[tuple[str, int, int], int],
) -> dict[str, Any]:
    deltas: list[int] = []
    for cell in cells:
        for row in cell["records"]:
            key = (
                str(row["opponent"]),
                int(row["seat"]),
                int(row["seed"]),
            )
            if key not in baseline_wins:
                raise ValueError(f"candidate key absent from baseline: {key}")
            deltas.append(int(row["win"]) - int(baseline_wins[key]))
    if not deltas:
        raise ValueError("paired comparison is empty")
    return {
        "paired_delta_wins": sum(deltas),
        "paired_delta_win_rate": sum(deltas) / len(deltas),
    }


def _arm_metrics(
    arm: Mapping[str, Any],
    cells: Sequence[Mapping[str, Any]],
    baseline_wins: Mapping[tuple[str, int, int], int],
) -> dict[str, Any]:
    paired = (
        {"paired_delta_wins": 0, "paired_delta_win_rate": 0.0}
        if arm["arm_id"] == "iteration004"
        else _paired_delta(cells, baseline_wins)
    )
    return {
        "arm_id": arm["arm_id"],
        "epochs": int(arm["epochs"]),
        "replicate": arm["replicate"],
        "training_seed_base": arm["training_seed_base"],
        "checkpoint_sha256": arm["checkpoint_sha256"],
        "overall": {**_rollup(cells), **paired},
        "by_opponent": _group_rollups(cells, "opponent"),
        "by_seat": _group_rollups(cells, "seat"),
    }


def _condition_metrics(
    *,
    epochs: int,
    arm_metrics: Sequence[Mapping[str, Any]],
    arm_cells: Mapping[str, Sequence[Mapping[str, Any]]],
    baseline_wins: Mapping[tuple[str, int, int], int],
) -> dict[str, Any]:
    selected = [arm for arm in arm_metrics if int(arm["epochs"]) == epochs]
    if len(selected) != 3:
        raise ValueError(f"expected three replicates for epochs={epochs}")
    pooled = [
        cell
        for arm in selected
        for cell in arm_cells[str(arm["arm_id"])]
    ]
    return {
        "epochs": epochs,
        "replicate_arms": [str(arm["arm_id"]) for arm in selected],
        "overall": {
            **_rollup(pooled),
            **_paired_delta(pooled, baseline_wins),
        },
        "by_opponent": _group_rollups(pooled, "opponent"),
        "by_seat": _group_rollups(pooled, "seat"),
    }


def _percent(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def _markdown_report(result: Mapping[str, Any]) -> str:
    baseline = result["baseline"]
    conditions = result["conditions"]
    arms = result["arms"]
    lines = [
        "## Material Passport",
        "",
        "- Origin Skill: experiment-agent",
        "- Origin Mode: run",
        "- Origin Date: 2026-08-01",
        "- Verification Status: UNVERIFIED",
        "- Version Label: exp_result_v1",
        "",
        "# PPO epoch一括比較結果",
        "",
        "個別試合・個別局面・行動確率の追加解析は行っていない。",
        "",
        "## 条件集計",
        "",
        "| 条件 | 試合 | 総勝率 | baselineとのpaired差 | 平均ターン | 行動エラー | 最大手数到達 | 重大異常行動率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    base_overall = baseline["overall"]
    lines.append(
        "| iteration004 | "
        f"{base_overall['games']} | {_percent(base_overall['win_rate'])} | "
        f"{_percent(base_overall['paired_delta_win_rate'])} | "
        f"{base_overall['mean_turns']:.3f} | "
        f"{base_overall['action_errors']} | {base_overall['max_step_hits']} | "
        f"{_percent(base_overall['severe_abnormal_action_rate'])} |"
    )
    for condition in conditions:
        overall = condition["overall"]
        lines.append(
            f"| {condition['epochs']} epoch | {overall['games']} | "
            f"{_percent(overall['win_rate'])} | "
            f"{_percent(overall['paired_delta_win_rate'])} | "
            f"{overall['mean_turns']:.3f} | {overall['action_errors']} | "
            f"{overall['max_step_hits']} | "
            f"{_percent(overall['severe_abnormal_action_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## 学習seed別checkpoint",
            "",
            "| checkpoint | epoch | 学習seed | 総勝率 | paired差 | 平均ターン | 行動エラー | 最大手数到達 | 重大異常行動率 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in arms:
        overall = arm["overall"]
        lines.append(
            f"| {arm['arm_id']} | {arm['epochs']} | "
            f"{arm['training_seed_base']} | {_percent(overall['win_rate'])} | "
            f"{_percent(overall['paired_delta_win_rate'])} | "
            f"{overall['mean_turns']:.3f} | {overall['action_errors']} | "
            f"{overall['max_step_hits']} | "
            f"{_percent(overall['severe_abnormal_action_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## 相手別勝率",
            "",
            "| 条件 | 相手 | 試合 | 勝率 |",
            "|---|---|---:|---:|",
        ]
    )
    for label, values in [
        ("iteration004", baseline),
        *[(f"{row['epochs']} epoch", row) for row in conditions],
    ]:
        for opponent, metrics in values["by_opponent"].items():
            lines.append(
                f"| {label} | {opponent} | {metrics['games']} | "
                f"{_percent(metrics['win_rate'])} |"
            )

    lines.extend(
        [
            "",
            "## 席順別勝率",
            "",
            "| 条件 | 席順 | 試合 | 勝率 |",
            "|---|---:|---:|---:|",
        ]
    )
    for label, values in [
        ("iteration004", baseline),
        *[(f"{row['epochs']} epoch", row) for row in conditions],
    ]:
        for seat, metrics in values["by_seat"].items():
            lines.append(
                f"| {label} | {seat} | {metrics['games']} | "
                f"{_percent(metrics['win_rate'])} |"
            )
    return "\n".join(lines) + "\n"


def summarize(spec: Mapping[str, Any]) -> dict[str, Any]:
    arms = _evaluation_arms(spec)
    arm_cells = {
        str(arm["arm_id"]): _load_arm_cells(spec, arm) for arm in arms
    }
    baseline_cells = arm_cells["iteration004"]
    baseline_wins = _win_map(baseline_cells)
    candidate_arms = [arm for arm in arms if arm["arm_id"] != "iteration004"]
    baseline_metrics = _arm_metrics(
        arms[0], baseline_cells, baseline_wins
    )
    candidate_metrics = [
        _arm_metrics(arm, arm_cells[str(arm["arm_id"])], baseline_wins)
        for arm in candidate_arms
    ]
    conditions = [
        _condition_metrics(
            epochs=epochs,
            arm_metrics=candidate_metrics,
            arm_cells=arm_cells,
            baseline_wins=baseline_wins,
        )
        for epochs in (4, 12, 24)
    ]
    result = {
        "material_passport": {
            "origin_skill": "experiment-agent",
            "origin_mode": "run",
            "origin_date": "2026-08-01",
            "verification_status": "UNVERIFIED",
            "version_label": "exp_result_v1",
        },
        "experiment_id": spec["experiment_id"],
        "metric_definitions": spec["reporting"],
        "baseline": baseline_metrics,
        "arms": candidate_metrics,
        "conditions": conditions,
    }
    paths = _paths(spec)
    _write_json(paths["result_json"], result)
    paths["result_markdown"].write_text(
        _markdown_report(result), encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--stage",
        choices=("rollouts", "training", "evaluation", "all"),
        default="all",
    )
    run_parser.add_argument("--workers", type=int, default=4)
    subparsers.add_parser("summarize")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = _load_json(args.spec.resolve())
    plan = validate_plan(spec)
    if args.command == "plan":
        print(json.dumps(plan, sort_keys=True))
        return 0
    if args.command == "summarize":
        result = summarize(spec)
        print(
            json.dumps(
                {
                    "experiment_id": result["experiment_id"],
                    "arms": len(result["arms"]) + 1,
                    "status": "summarized",
                },
                sort_keys=True,
            )
        )
        return 0
    if args.workers <= 0 or args.workers > 4:
        raise ValueError("--workers must be between 1 and 4")
    if args.stage in ("rollouts", "all"):
        run_rollouts(spec, args.workers)
    if args.stage in ("training", "all"):
        run_training(spec, args.workers)
    if args.stage in ("evaluation", "all"):
        run_evaluation(spec, args.workers)
    if args.stage == "all":
        summarize(spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
