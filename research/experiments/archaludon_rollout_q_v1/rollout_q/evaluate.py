'''Run the fixed 640-game paired evaluation for one expert-iteration round.'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .agent_loader import load_baseline, load_opponent
from .branch_runner import _terminal, _player
from .config import RolloutQConfig, round_dir, write_json
from .override_policy import RolloutQOverridePolicy, RoundPolicyResources
from .source_collector import _battle_start, _load_engine, _opponent_rows, resolve_opponent_dir


def _run_game(
    *,
    config: RolloutQConfig,
    opponent_id: str,
    opponent_dir: Path,
    seat: int,
    seed: int,
    candidate: bool,
    resources: RoundPolicyResources | None = None,
) -> dict[str, Any]:
    battle_start, battle_select, battle_finish, _ = _load_engine()
    baseline = load_baseline(config.baseline_dir, config.baseline_dir.name)
    opponent = load_opponent(opponent_dir, opponent_id)
    baseline.seed(seed)
    opponent.seed(seed)
    policy: Any = baseline
    if candidate:
        if resources is None:
            raise ValueError('candidate evaluation requires shared round policy resources')
        policy = resources.bind(baseline, config)
    baseline_deck = baseline.deck
    opponent_deck = opponent.deck
    decks = (baseline_deck, opponent_deck) if seat == 0 else (opponent_deck, baseline_deck)
    observation: Any = None
    started = False
    steps = 0
    action_errors = 0
    max_step_hit = False
    result: int | None = None
    try:
        observation, start_data = _battle_start(battle_start, decks, seed)
        if not observation:
            error_player = getattr(start_data, 'errorPlayer', None)
            error_type = getattr(start_data, 'errorType', None)
            raise RuntimeError(f'engine start failed: {error_player}/{error_type}')
        started = True
        while steps < config.worker_max_steps:
            result = _terminal(observation)
            if result is not None:
                break
            if not isinstance(observation, Mapping) or not observation.get('select'):
                break
            current_player = _player(observation)
            try:
                action = policy(observation) if current_player == seat else opponent(observation)
                observation = battle_select(list(action))
            except Exception:
                action_errors += 1
                raise
            steps += 1
        result = _terminal(observation)
        max_step_hit = steps >= config.worker_max_steps and result is None
        clean_terminal = result in (0, 1, 2) and action_errors == 0 and not max_step_hit
    except Exception as exc:
        clean_terminal = False
        error = f'{type(exc).__name__}: {exc}'
    else:
        error = None
    finally:
        if started:
            try:
                battle_finish()
            except Exception as exc:
                clean_terminal = False
                error = error or f'{type(exc).__name__}: {exc}'
    telemetry = policy.telemetry if candidate else {}
    win = bool(clean_terminal and result == seat)
    return {
        'result': result,
        'win': win,
        'engine_steps': steps,
        'action_errors': action_errors,
        'max_step_hit': max_step_hit,
        'clean_terminal': clean_terminal,
        'error': error,
        'override_count': int(getattr(telemetry, 'override_count', 0)),
        'fallback_count': int(getattr(telemetry, 'fallback_count', 0)),
        'model_failure_count': int(getattr(telemetry, 'model_failure_count', 0)),
    }


def evaluate_round(config: RolloutQConfig, round_index: int) -> dict[str, Any]:
    if config.evaluation_games != 640:
        raise ValueError('v1 evaluation_games must remain 640')
    resources = RoundPolicyResources.load(config, int(round_index))
    evaluation_dir = round_dir(config, round_index) / 'evaluation'
    output = evaluation_dir / 'paired_results.jsonl'
    if output.exists():
        raise FileExistsError(output)
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    opponents = _opponent_rows()
    if len(opponents) != 8:
        raise ValueError('fixed evaluation requires exactly eight opponents')
    for opponent_index, row in enumerate(opponents):
        opponent_id = str(row['id'])
        opponent_dir = resolve_opponent_dir(row, config)
        for seat in (0, 1):
            for game_index in range(40):
                seed = config.evaluation_seed_base + opponent_index * 1000 + seat * 100 + game_index
                baseline_result = _run_game(
                    config=config,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    candidate=False,
                    resources=resources,
                )
                candidate_result = _run_game(
                    config=config,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    candidate=True,
                    resources=resources,
                )
                rows.append(
                    {
                        'panel': 'paired',
                        'opponent_id': opponent_id,
                        'seat': seat,
                        'seed': seed,
                        'baseline': baseline_result,
                        'candidate': candidate_result,
                        'baseline_win': bool(baseline_result['win']),
                        'candidate_win': bool(candidate_result['win']),
                    }
                )
    with output.open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False))
            handle.write('\n')
    summary = {
        'schema_version': 'archaludon-evaluation-summary-v1',
        'round': int(round_index),
        'games': len(rows),
        'baseline_wins': sum(int(row['baseline_win']) for row in rows),
        'candidate_wins': sum(int(row['candidate_win']) for row in rows),
        'loss_to_win': sum(int(not row['baseline_win'] and row['candidate_win']) for row in rows),
        'win_to_loss': sum(int(row['baseline_win'] and not row['candidate_win']) for row in rows),
        'override_count': sum(int(row['candidate']['override_count']) for row in rows),
        'fallback_count': sum(int(row['candidate']['fallback_count']) for row in rows),
        'model_failure': sum(int(row['candidate']['model_failure_count']) for row in rows),
        'action_errors': sum(int(row['baseline']['action_errors'] + row['candidate']['action_errors']) for row in rows),
        'max_step': sum(int(row['baseline']['max_step_hit'] or row['candidate']['max_step_hit']) for row in rows),
        'evaluation_path': str(output),
    }
    write_json(evaluation_dir / 'evaluation_summary.json', summary)
    return summary


def read_evaluation(config: RolloutQConfig, round_index: int) -> list[dict[str, Any]]:
    path = round_dir(config, round_index) / 'evaluation' / 'paired_results.jsonl'
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


__all__ = ['evaluate_round', 'read_evaluation']
