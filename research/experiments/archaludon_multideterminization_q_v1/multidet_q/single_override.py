"""Single-override Search-Q policy and its independent fixed evaluation."""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline, load_opponent
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _player, _terminal
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec as load_rollout_config
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _battle_start, _load_engine, _opponent_rows, resolve_opponent_dir

from .config import MultiDetConfig, output_path, write_json
from .evaluate import LivePolicy
from .model import load_checkpoint


SINGLE_OVERRIDE_THRESHOLD = 0.10
SINGLE_OVERRIDE_EVALUATION_SEED_BASE = 870000000


class SingleOverrideLivePolicy(LivePolicy):
    """Existing Search-Q policy with a per-game override budget of one."""

    def __init__(self, baseline: Any, models: Sequence[Any], threshold: float) -> None:
        super().__init__(baseline, models, threshold)
        self.override_budget_initial = 1
        self.overrides_used = 0
        self.override_budget_exhausted_count = 0

    def __call__(self, observation: Any) -> list[int]:
        if self.overrides_used >= self.override_budget_initial:
            baseline_action = [int(value) for value in self.baseline(observation)]
            self.fallback_count += 1
            self.last_error = "override_budget_exhausted"
            self.override_budget_exhausted_count += 1
            return baseline_action
        previous_override_count = self.override_count
        action = super().__call__(observation)
        if self.override_count > previous_override_count:
            self.overrides_used += 1
        return action


def _run_game(
    config: MultiDetConfig,
    *,
    opponent_id: str,
    opponent_dir: Path,
    seat: int,
    seed: int,
    candidate: bool,
    models: Sequence[Any],
    threshold: float,
    max_steps: int,
) -> dict[str, Any]:
    battle_start, battle_select, battle_finish, _ = _load_engine()
    baseline = load_baseline(config.baseline_dir, config.baseline_dir.name)
    opponent = load_opponent(opponent_dir, opponent_id)
    baseline.seed(seed)
    opponent.seed(seed)
    policy: Any = SingleOverrideLivePolicy(baseline, models, threshold) if candidate else baseline
    decks = (baseline.deck, opponent.deck) if seat == 0 else (opponent.deck, baseline.deck)
    observation: Any = None
    started = False
    steps = 0
    action_errors = 0
    max_step_hit = False
    result: int | None = None
    error: str | None = None
    try:
        observation, start_data = _battle_start(battle_start, decks, seed)
        if not observation:
            raise RuntimeError(f"engine start failed: {getattr(start_data, 'errorPlayer', None)}/{getattr(start_data, 'errorType', None)}")
        started = True
        while steps < max_steps:
            result = _terminal(observation)
            if result is not None:
                break
            if not isinstance(observation, Mapping) or not observation.get("select"):
                break
            try:
                action = policy(observation) if _player(observation) == seat else opponent(observation)
                observation = battle_select(list(action))
            except Exception:
                action_errors += 1
                raise
            steps += 1
        result = _terminal(observation)
        max_step_hit = steps >= max_steps and result is None
        clean = result in (0, 1, 2) and action_errors == 0 and not max_step_hit
    except Exception as exc:
        clean = False
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if started:
            try:
                battle_finish()
            except Exception as exc:
                clean = False
                error = error or f"{type(exc).__name__}: {exc}"
    if candidate:
        return {
            "result": result,
            "win": bool(clean and result == seat),
            "engine_steps": steps,
            "action_errors": action_errors,
            "max_step_hit": max_step_hit,
            "clean_terminal": clean,
            "error": error,
            "override_count": int(policy.override_count),
            "override_budget_exhausted_count": int(policy.override_budget_exhausted_count),
            "fallback_count": int(policy.fallback_count),
            "model_failure_count": int(policy.model_failure_count),
            "max_overrides": int(policy.override_count),
        }
    return {
        "result": result,
        "win": bool(clean and result == seat),
        "engine_steps": steps,
        "action_errors": action_errors,
        "max_step_hit": max_step_hit,
        "clean_terminal": clean,
        "error": error,
        "override_count": 0,
        "override_budget_exhausted_count": 0,
        "fallback_count": 0,
        "model_failure_count": 0,
        "max_overrides": 0,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row[key])].append(row)
    return {
        name: {
            "games": len(values),
            "baseline_wins": sum(int(row["baseline_win"]) for row in values),
            "candidate_wins": sum(int(row["candidate_win"]) for row in values),
            "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in values),
            "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in values),
            "paired_net": sum(int(row["candidate_win"]) - int(row["baseline_win"]) for row in values),
        }
        for name, values in sorted(buckets.items())
    }


def evaluate_single_override(config: MultiDetConfig) -> dict[str, Any]:
    calibration_path = output_path(config, "calibration_summary.json")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    selected_threshold = calibration.get("selected_threshold")
    if not calibration.get("passed") or selected_threshold is None or not math.isclose(float(selected_threshold), SINGLE_OVERRIDE_THRESHOLD, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("single-override evaluation requires the frozen calibration threshold 0.10")

    models = []
    for seed in config.training_seeds:
        model, _ = load_checkpoint(output_path(config, "checkpoints", f"multidet_q_seed{int(seed)}.pt"))
        models.append(model)

    old_config = load_rollout_config()
    evaluation_dir = output_path(config, "single_override_evaluation_v1")
    if evaluation_dir.exists() and any(evaluation_dir.iterdir()):
        raise FileExistsError(evaluation_dir)
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    output = evaluation_dir / "paired_results.jsonl"
    rows: list[dict[str, Any]] = []
    opponents = _opponent_rows()
    if len(opponents) != 8:
        raise ValueError("single-override evaluation requires exactly eight opponents")
    for opponent_index, row in enumerate(opponents):
        opponent_id = str(row["id"])
        opponent_dir = resolve_opponent_dir(row, old_config)
        for seat in (0, 1):
            for game_index in range(40):
                seed = SINGLE_OVERRIDE_EVALUATION_SEED_BASE + opponent_index * 1000 + seat * 100 + game_index
                baseline_result = _run_game(
                    config,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    candidate=False,
                    models=models,
                    threshold=SINGLE_OVERRIDE_THRESHOLD,
                    max_steps=old_config.worker_max_steps,
                )
                candidate_result = _run_game(
                    config,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    candidate=True,
                    models=models,
                    threshold=SINGLE_OVERRIDE_THRESHOLD,
                    max_steps=old_config.worker_max_steps,
                )
                rows.append(
                    {
                        "panel": "single_override_paired",
                        "opponent_id": opponent_id,
                        "seat": seat,
                        "seed": seed,
                        "baseline": baseline_result,
                        "candidate": candidate_result,
                        "baseline_win": bool(baseline_result["win"]),
                        "candidate_win": bool(candidate_result["win"]),
                    }
                )
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")

    override_count = sum(int(row["candidate"]["override_count"]) for row in rows)
    override_games = sum(int(row["candidate"]["override_count"] > 0) for row in rows)
    max_overrides = max((int(row["candidate"]["max_overrides"]) for row in rows), default=0)
    summary = {
        "schema_version": "archaludon-single-override-evaluation-v1",
        "evaluation_seed_base": SINGLE_OVERRIDE_EVALUATION_SEED_BASE,
        "games": len(rows),
        "baseline_wins": sum(int(row["baseline_win"]) for row in rows),
        "candidate_wins": sum(int(row["candidate_win"]) for row in rows),
        "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in rows),
        "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in rows),
        "paired_net": sum(int(row["candidate_win"]) - int(row["baseline_win"]) for row in rows),
        "override_count": override_count,
        "override_games": override_games,
        "override_no_games": len(rows) - override_games,
        "max_overrides_per_game": max_overrides,
        "override_budget_exhausted_count": sum(int(row["candidate"]["override_budget_exhausted_count"]) for row in rows),
        "fallback_count": sum(int(row["candidate"]["fallback_count"]) for row in rows),
        "model_failure": sum(int(row["candidate"]["model_failure_count"]) for row in rows),
        "action_errors": sum(int(row["baseline"]["action_errors"] + row["candidate"]["action_errors"]) for row in rows),
        "max_step": sum(int(row["baseline"]["max_step_hit"] or row["candidate"]["max_step_hit"]) for row in rows),
        "override_count_equals_games": override_count == override_games,
        "max_overrides_at_most_one": max_overrides <= 1,
        "evaluation_path": str(output),
    }
    write_json(evaluation_dir / "evaluation_summary.json", summary)
    if not summary["override_count_equals_games"] or not summary["max_overrides_at_most_one"] or summary["action_errors"] != 0 or summary["max_step"] != 0 or summary["model_failure"] != 0:
        raise RuntimeError("single-override evaluation mandatory checks failed")
    return summary


def report_single_override(config: MultiDetConfig) -> dict[str, Any]:
    evaluation_dir = output_path(config, "single_override_evaluation_v1")
    path = evaluation_dir / "paired_results.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != config.evaluation_games:
        raise ValueError("single-override evaluation row count does not match the frozen 640-game panel")
    override_count = sum(int(row["candidate"]["override_count"]) for row in rows)
    override_games = sum(int(row["candidate"]["override_count"] > 0) for row in rows)
    value = {
        "schema_version": "archaludon-single-override-report-v1",
        "evaluation_seed_base": SINGLE_OVERRIDE_EVALUATION_SEED_BASE,
        "games": len(rows),
        "baseline_wins": sum(int(row["baseline_win"]) for row in rows),
        "candidate_wins": sum(int(row["candidate_win"]) for row in rows),
        "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in rows),
        "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in rows),
        "paired_net": sum(int(row["candidate_win"]) - int(row["baseline_win"]) for row in rows),
        "override_count": override_count,
        "override_games": override_games,
        "override_no_games": len(rows) - override_games,
        "max_overrides_per_game": max((int(row["candidate"]["max_overrides"]) for row in rows), default=0),
        "override_budget_exhausted_count": sum(int(row["candidate"]["override_budget_exhausted_count"]) for row in rows),
        "opponent": _aggregate(rows, "opponent_id"),
        "seat": _aggregate(rows, "seat"),
        "action_errors": sum(int(row["baseline"]["action_errors"] + row["candidate"]["action_errors"]) for row in rows),
        "max_step": sum(int(row["baseline"]["max_step_hit"] or row["candidate"]["max_step_hit"]) for row in rows),
        "model_failure": sum(int(row["candidate"]["model_failure_count"]) for row in rows),
    }
    write_json(evaluation_dir / "report.json", value)
    lines = [
        "# Search-Q single-override evaluation",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| games | {value['games']} |",
        f"| baseline wins | {value['baseline_wins']} |",
        f"| candidate wins | {value['candidate_wins']} |",
        f"| loss to win | {value['loss_to_win']} |",
        f"| win to loss | {value['win_to_loss']} |",
        f"| paired net | {value['paired_net']} |",
        f"| override count | {value['override_count']} |",
        f"| override games | {value['override_games']} |",
        f"| override no-games | {value['override_no_games']} |",
        f"| max overrides per game | {value['max_overrides_per_game']} |",
        f"| override budget exhausted | {value['override_budget_exhausted_count']} |",
        f"| action errors | {value['action_errors']} |",
        f"| max-step | {value['max_step']} |",
        f"| model failure | {value['model_failure']} |",
        "",
        "## Opponent",
        "",
        "| opponent | games | baseline wins | candidate wins | loss to win | win to loss | paired net |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in value["opponent"].items():
        lines.append(f"| {name} | {item['games']} | {item['baseline_wins']} | {item['candidate_wins']} | {item['loss_to_win']} | {item['win_to_loss']} | {item['paired_net']} |")
    lines.extend([
        "",
        "## Seat",
        "",
        "| seat | games | baseline wins | candidate wins | loss to win | win to loss | paired net |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, item in value["seat"].items():
        lines.append(f"| {name} | {item['games']} | {item['baseline_wins']} | {item['candidate_wins']} | {item['loss_to_win']} | {item['win_to_loss']} | {item['paired_net']} |")
    (evaluation_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return value


__all__ = ["SINGLE_OVERRIDE_EVALUATION_SEED_BASE", "SINGLE_OVERRIDE_THRESHOLD", "SingleOverrideLivePolicy", "evaluate_single_override", "report_single_override"]
