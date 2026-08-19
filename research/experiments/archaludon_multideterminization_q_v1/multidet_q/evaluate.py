"""Run the frozen 640-game panel with the calibrated live expected-Q policy."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline, load_opponent
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _player, _terminal
from research.experiments.archaludon_rollout_q_v1.rollout_q.complete_action import observation_complete_actions, observation_option_rows
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec as load_rollout_config
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _battle_start, _load_engine, _opponent_rows, resolve_opponent_dir
from research.experiments.archaludon_latest_v1_rl_pcgrad_candidate_20260801.archaludon_rl.public_state import enum_int, project_public_state

from .calibrate import calibrate
from .config import MultiDetConfig, output_path, write_json
from .dataset import _family
from .model import load_checkpoint


class LivePolicy:
    def __init__(self, baseline: Any, models: Sequence[Any], threshold: float) -> None:
        if len(models) != 3:
            raise ValueError("exactly three expected-Q models are required")
        self.baseline = baseline
        self.models = tuple(models)
        self.threshold = float(threshold)
        self.override_count = 0
        self.fallback_count = 0
        self.model_failure_count = 0
        self.last_error: str | None = None

    def _fallback(self, reason: str, action: Sequence[int]) -> list[int]:
        self.fallback_count += 1
        self.last_error = reason
        return [int(value) for value in action]

    def __call__(self, observation: Any) -> list[int]:
        baseline_action = [int(value) for value in self.baseline(observation)]
        try:
            candidates = observation_complete_actions(observation)
            option_rows = observation_option_rows(observation)
            baseline_index = candidates.candidate_index_for(option_rows, baseline_action)
            if baseline_index is None:
                return self._fallback("baseline_not_legal", baseline_action)
            public_state = project_public_state(observation)
            candidate_rows: list[dict[str, Any]] = []
            for candidate in candidates.candidates:
                candidate_rows.append(
                    {
                        "candidate_index": int(candidate.candidate_index),
                        "canonical_identity": candidate.canonical_identity,
                        "is_baseline": int(candidate.candidate_index) == int(baseline_index),
                        "action": list(candidate.action),
                        "selected_options": [dict(item) for item in candidate.selected_options],
                        "order_sensitive": bool(candidate.order_sensitive),
                        "family": _family({"selected_options": candidate.selected_options}),
                    }
                )
            context = int(enum_int(getattr(getattr(observation, "select", None), "context", None)) or 0)
            score_rows = []
            for model in self.models:
                scores = model.score_group({"public_state": public_state, "context": context, "candidates": candidate_rows}).detach().cpu().float()
                if scores.numel() != len(candidate_rows) or not bool(scores.isfinite().all()):
                    raise FloatingPointError("non-finite or malformed live expected-Q score")
                score_rows.append(scores.tolist())
            winners = []
            for scores in score_rows:
                best = max(range(len(candidate_rows)), key=lambda index: (float(scores[index]), str(candidate_rows[index]["canonical_identity"])))
                winners.append(candidate_rows[best]["canonical_identity"])
            if len(set(winners)) != 1:
                return self._fallback("ensemble_disagreement", baseline_action)
            selected_identity = winners[0]
            selected_index = next(index for index, row in enumerate(candidate_rows) if row["canonical_identity"] == selected_identity)
            if selected_index == int(baseline_index):
                return self._fallback("baseline_selected", baseline_action)
            margins = [float(scores[selected_index]) - float(scores[baseline_index]) for scores in score_rows]
            if any(not math.isfinite(value) for value in margins) or min(margins) < self.threshold:
                return self._fallback("margin_threshold", baseline_action)
            selected_action = candidates.candidates[selected_index].action
            if candidates.candidate_index_for(option_rows, selected_action) != selected_index:
                return self._fallback("candidate_not_legal", baseline_action)
            self.override_count += 1
            return list(selected_action)
        except Exception as exc:
            self.model_failure_count += 1
            return self._fallback(f"{type(exc).__name__}: {exc}", baseline_action)


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
    policy: Any = LivePolicy(baseline, models, threshold) if candidate else baseline
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
            "fallback_count": int(policy.fallback_count),
            "model_failure_count": int(policy.model_failure_count),
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
        "fallback_count": 0,
        "model_failure_count": 0,
    }


def evaluate(config: MultiDetConfig) -> dict[str, Any]:
    calibration = json.loads(output_path(config, "calibration_summary.json").read_text(encoding="utf-8"))
    if not calibration.get("passed") or calibration.get("selected_threshold") is None:
        raise RuntimeError("calibration gate did not pass; fixed evaluation is prohibited")
    models = []
    for seed in config.training_seeds:
        model, _ = load_checkpoint(output_path(config, "checkpoints", f"multidet_q_seed{int(seed)}.pt"))
        models.append(model)
    old_config = load_rollout_config()
    evaluation_dir = output_path(config, "evaluation")
    output = evaluation_dir / "paired_results.jsonl"
    if output.exists():
        raise FileExistsError(output)
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    opponents = _opponent_rows()
    if len(opponents) != 8:
        raise ValueError("fixed evaluation requires exactly eight opponents")
    for opponent_index, row in enumerate(opponents):
        opponent_id = str(row["id"])
        opponent_dir = resolve_opponent_dir(row, old_config)
        for seat in (0, 1):
            for game_index in range(40):
                seed = old_config.evaluation_seed_base + opponent_index * 1000 + seat * 100 + game_index
                baseline_result = _run_game(config, opponent_id=opponent_id, opponent_dir=opponent_dir, seat=seat, seed=seed, candidate=False, models=models, threshold=float(calibration["selected_threshold"]), max_steps=old_config.worker_max_steps)
                candidate_result = _run_game(config, opponent_id=opponent_id, opponent_dir=opponent_dir, seat=seat, seed=seed, candidate=True, models=models, threshold=float(calibration["selected_threshold"]), max_steps=old_config.worker_max_steps)
                rows.append(
                    {
                        "panel": "paired",
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
    summary = {
        "schema_version": "archaludon-multidet-evaluation-summary-v1",
        "games": len(rows),
        "baseline_wins": sum(int(row["baseline_win"]) for row in rows),
        "candidate_wins": sum(int(row["candidate_win"]) for row in rows),
        "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in rows),
        "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in rows),
        "override_count": sum(int(row["candidate"]["override_count"]) for row in rows),
        "override_games": sum(int(row["candidate"]["override_count"] > 0) for row in rows),
        "fallback_count": sum(int(row["candidate"]["fallback_count"]) for row in rows),
        "model_failure": sum(int(row["candidate"]["model_failure_count"]) for row in rows),
        "action_errors": sum(int(row["baseline"]["action_errors"] + row["candidate"]["action_errors"]) for row in rows),
        "max_step": sum(int(row["baseline"]["max_step_hit"] or row["candidate"]["max_step_hit"]) for row in rows),
        "evaluation_path": str(output),
    }
    write_json(evaluation_dir / "evaluation_summary.json", summary)
    return summary


def report(config: MultiDetConfig) -> dict[str, Any]:
    path = output_path(config, "evaluation", "paired_results.jsonl")
    if not path.is_file():
        raise FileNotFoundError(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != config.evaluation_games:
        raise ValueError("evaluation row count does not match frozen 640-game panel")
    from collections import defaultdict
    def aggregate(key: str) -> dict[str, Any]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            buckets[str(row[key])].append(row)
        return {
            name: {
                "games": len(values),
                "baseline_wins": sum(int(row["baseline_win"]) for row in values),
                "candidate_wins": sum(int(row["candidate_win"]) for row in values),
                "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in values),
                "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in values),
            }
            for name, values in sorted(buckets.items())
        }
    value = {
        "schema_version": "archaludon-multidet-report-v1",
        "games": len(rows),
        "baseline_wins": sum(int(row["baseline_win"]) for row in rows),
        "candidate_wins": sum(int(row["candidate_win"]) for row in rows),
        "paired_net": sum(int(row["candidate_win"]) - int(row["baseline_win"]) for row in rows),
        "loss_to_win": sum(int(not row["baseline_win"] and row["candidate_win"]) for row in rows),
        "win_to_loss": sum(int(row["baseline_win"] and not row["candidate_win"]) for row in rows),
        "opponent": aggregate("opponent_id"),
        "seat": aggregate("seat"),
        "override_count": sum(int(row["candidate"]["override_count"]) for row in rows),
        "override_games": sum(int(row["candidate"]["override_count"] > 0) for row in rows),
        "fallback_count": sum(int(row["candidate"]["fallback_count"]) for row in rows),
        "model_failure": sum(int(row["candidate"]["model_failure_count"]) for row in rows),
        "baseline_action_errors": sum(int(row["baseline"]["action_errors"]) for row in rows),
        "candidate_action_errors": sum(int(row["candidate"]["action_errors"]) for row in rows),
        "baseline_max_step": sum(int(row["baseline"]["max_step_hit"]) for row in rows),
        "candidate_max_step": sum(int(row["candidate"]["max_step_hit"]) for row in rows),
    }
    write_json(output_path(config, "evaluation", "report.json"), value)
    lines = [
        "# Multi-Determinization Search-Q v1 evaluation",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| games | {value['games']} |",
        f"| baseline wins | {value['baseline_wins']} |",
        f"| candidate wins | {value['candidate_wins']} |",
        f"| paired net | {value['paired_net']} |",
        f"| loss to win | {value['loss_to_win']} |",
        f"| win to loss | {value['win_to_loss']} |",
        f"| override count | {value['override_count']} |",
        f"| override games | {value['override_games']} |",
        f"| fallback count | {value['fallback_count']} |",
        f"| model failure | {value['model_failure']} |",
        f"| action errors | {value['baseline_action_errors'] + value['candidate_action_errors']} |",
        f"| max-step | {value['baseline_max_step'] + value['candidate_max_step']} |",
        "",
        "## Opponent",
        "",
        "| opponent | games | baseline wins | candidate wins | loss→win | win→loss |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, item in value["opponent"].items():
        lines.append(f"| {name} | {item['games']} | {item['baseline_wins']} | {item['candidate_wins']} | {item['loss_to_win']} | {item['win_to_loss']} |")
    lines.extend(["", "## Seat", "", "| seat | games | baseline wins | candidate wins | loss→win | win→loss |", "|---|---:|---:|---:|---:|---:|"])
    for name, item in value["seat"].items():
        lines.append(f"| {name} | {item['games']} | {item['baseline_wins']} | {item['candidate_wins']} | {item['loss_to_win']} | {item['win_to_loss']} |")
    output_path(config, "evaluation", "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return value


__all__ = ["LivePolicy", "evaluate", "report"]
