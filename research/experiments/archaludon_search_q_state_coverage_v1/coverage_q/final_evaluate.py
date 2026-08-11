"""Fixed 2,000-game paired evaluation adapter (not run by the Pilot)."""

from __future__ import annotations

import math
from typing import Any

from .config import CoverageConfig, output_path, write_json


def mcnemar_p_value(loss_to_win: int, win_to_loss: int) -> float:
    n = int(loss_to_win) + int(win_to_loss)
    if n == 0:
        return 1.0
    k = min(int(loss_to_win), int(win_to_loss))
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def final_evaluate(config: CoverageConfig) -> dict[str, Any]:
    import json
    from research.experiments.archaludon_multideterminization_q_v1.multidet_q.evaluate import LivePolicy, _run_game
    from research.experiments.archaludon_multideterminization_q_v1.multidet_q.model import load_checkpoint
    from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec as load_rollout_spec
    from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _opponent_rows, resolve_opponent_dir

    gate = json.loads(output_path(config, "offline_test", "offline_test_summary.json").read_text(encoding="utf-8"))
    if gate.get("status") != "OFFLINE_TEST_PASSED":
        raise RuntimeError("final evaluation is gated by offline-test success")
    selected = json.loads(output_path(config, "calibration", "selected_candidate.json").read_text(encoding="utf-8"))["selected"]
    if not selected:
        raise RuntimeError("selected candidate is missing")
    models = [load_checkpoint(output_path(config, "checkpoints", selected["milestone"], f"seed_{int(seed)}.pt"))[0] for seed in config.training_seeds]
    old_config = load_rollout_spec()
    rows: list[dict[str, Any]] = []
    opponents = _opponent_rows()
    if len(opponents) != 8:
        raise ValueError("final evaluation requires eight opponents")
    for opponent_index, opponent_row in enumerate(opponents):
        opponent_id = str(opponent_row["id"])
        opponent_dir = resolve_opponent_dir(opponent_row, old_config)
        for seat in (0, 1):
            for game_index in range(125):
                seed = int(config.source_seed_bases["final_evaluation"]) + opponent_index * 100000 + seat * 1000 + game_index
                baseline = _run_game(config, opponent_id=opponent_id, opponent_dir=opponent_dir, seat=seat, seed=seed, candidate=False, models=models, threshold=float(selected["threshold"]), max_steps=config.maximum_search_steps)
                candidate = _run_game(config, opponent_id=opponent_id, opponent_dir=opponent_dir, seat=seat, seed=seed, candidate=True, models=models, threshold=float(selected["threshold"]), max_steps=config.maximum_search_steps)
                rows.append({"opponent_id": opponent_id, "seat": seat, "seed": seed, "baseline": baseline, "candidate": candidate, "baseline_win": bool(baseline["win"]), "candidate_win": bool(candidate["win"])})
    result_path = output_path(config, "evaluation", "paired_results.jsonl")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
    baseline_wins = sum(int(row["baseline_win"]) for row in rows)
    candidate_wins = sum(int(row["candidate_win"]) for row in rows)
    loss_to_win = sum(int(not row["baseline_win"] and row["candidate_win"]) for row in rows)
    win_to_loss = sum(int(row["baseline_win"] and not row["candidate_win"]) for row in rows)
    p_value = mcnemar_p_value(loss_to_win, win_to_loss)
    summary = {
        "schema_version": "archaludon-search-q-final-evaluation-v1",
        "games": len(rows),
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "loss_to_win": loss_to_win,
        "win_to_loss": win_to_loss,
        "paired_net": candidate_wins - baseline_wins,
        "mcnemar_p_value": p_value,
        "override_count": sum(int(row["candidate"]["override_count"]) for row in rows),
        "override_games": sum(int(row["candidate"]["override_count"] > 0) for row in rows),
        "action_error": sum(int(row["baseline"]["action_errors"] + row["candidate"]["action_errors"]) for row in rows),
        "max_step": sum(int(row["baseline"]["max_step_hit"] or row["candidate"]["max_step_hit"]) for row in rows),
        "model_failure": sum(int(row["candidate"]["model_failure_count"]) for row in rows),
        "promotion": bool(candidate_wins > baseline_wins and loss_to_win > win_to_loss and candidate_wins - baseline_wins >= config.final_evaluation_required_paired_net and p_value < config.final_evaluation_required_p_value and sum(int(row["baseline"]["action_errors"] + row["candidate"]["action_errors"]) for row in rows) == 0 and sum(int(row["baseline"]["max_step_hit"] or row["candidate"]["max_step_hit"]) for row in rows) == 0 and sum(int(row["candidate"]["model_failure_count"]) for row in rows) == 0),
        "path": str(result_path),
    }
    write_json(output_path(config, "evaluation", "evaluation_summary.json"), summary)
    return summary


__all__ = ["final_evaluate", "mcnemar_p_value"]
