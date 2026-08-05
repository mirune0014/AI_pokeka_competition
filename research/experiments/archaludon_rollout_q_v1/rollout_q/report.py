'''Produce raw aggregate JSON and concise Markdown for a fixed evaluation.'''

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import RolloutQConfig, round_dir, write_json
from .evaluate import read_evaluation


def _aggregate(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    result: dict[str, Any] = {}
    for name, values in sorted(groups.items()):
        result[name] = {
            'games': len(values),
            'baseline_wins': sum(int(item['baseline_win']) for item in values),
            'candidate_wins': sum(int(item['candidate_win']) for item in values),
            'loss_to_win': sum(int(not item['baseline_win'] and item['candidate_win']) for item in values),
            'win_to_loss': sum(int(item['baseline_win'] and not item['candidate_win']) for item in values),
            'baseline_action_errors': sum(int(item['baseline']['action_errors']) for item in values),
            'candidate_action_errors': sum(int(item['candidate']['action_errors']) for item in values),
            'baseline_max_step': sum(int(item['baseline']['max_step_hit']) for item in values),
            'candidate_max_step': sum(int(item['candidate']['max_step_hit']) for item in values),
        }
    return result


def report_round(config: RolloutQConfig, round_index: int) -> dict[str, Any]:
    rows = read_evaluation(config, round_index)
    if len(rows) != config.evaluation_games:
        raise ValueError('evaluation row count does not match fixed schedule')
    report = {
        'schema_version': 'archaludon-rollout-q-report-v1',
        'round': int(round_index),
        'games': len(rows),
        'baseline_wins': sum(int(row['baseline_win']) for row in rows),
        'candidate_wins': sum(int(row['candidate_win']) for row in rows),
        'paired_net': sum(int(row['candidate_win']) - int(row['baseline_win']) for row in rows),
        'loss_to_win': sum(int(not row['baseline_win'] and row['candidate_win']) for row in rows),
        'win_to_loss': sum(int(row['baseline_win'] and not row['candidate_win']) for row in rows),
        'opponent': _aggregate(rows, 'opponent_id'),
        'seat': _aggregate(rows, 'seat'),
        'override_count': sum(int(row['candidate']['override_count']) for row in rows),
        'override_games': sum(int(row['candidate']['override_count'] > 0) for row in rows),
        'override_wins': sum(int(row['candidate']['override_count'] > 0 and row['candidate_win']) for row in rows),
        'fallback_count': sum(int(row['candidate']['fallback_count']) for row in rows),
        'model_failure': sum(int(row['candidate']['model_failure_count']) for row in rows),
        'baseline_action_errors': sum(int(row['baseline']['action_errors']) for row in rows),
        'candidate_action_errors': sum(int(row['candidate']['action_errors']) for row in rows),
        'baseline_max_step': sum(int(row['baseline']['max_step_hit']) for row in rows),
        'candidate_max_step': sum(int(row['candidate']['max_step_hit']) for row in rows),
    }
    report_path = round_dir(config, round_index) / 'evaluation' / 'report.json'
    markdown_path = round_dir(config, round_index) / 'evaluation' / 'report.md'
    write_json(report_path, report)
    games = report['games']
    baseline_wins = report['baseline_wins']
    candidate_wins = report['candidate_wins']
    paired_net = report['paired_net']
    loss_to_win = report['loss_to_win']
    win_to_loss = report['win_to_loss']
    override_games = report['override_games']
    override_wins = report['override_wins']
    fallback_count = report['fallback_count']
    model_failure = report['model_failure']
    candidate_action_errors = report['candidate_action_errors']
    candidate_max_step = report['candidate_max_step']
    lines = [
        f'# Rollout-Q v1 evaluation (round {round_index})',
        '',
        '| metric | value |',
        '|---|---:|',
        f'| games | {games} |',
        f'| baseline wins | {baseline_wins} |',
        f'| candidate wins | {candidate_wins} |',
        f'| paired net | {paired_net} |',
        f'| loss to win | {loss_to_win} |',
        f'| win to loss | {win_to_loss} |',
        f'| override games | {override_games} |',
        f'| override wins | {override_wins} |',
        f'| fallback count | {fallback_count} |',
        f'| model failure | {model_failure} |',
        f'| candidate action errors | {candidate_action_errors} |',
        f'| candidate max-step | {candidate_max_step} |',
        '',
        '## Opponent',
        '',
        '| opponent | games | baseline wins | candidate wins | loss_to_win | win_to_loss |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for opponent, values in report['opponent'].items():
        games = values['games']
        baseline_wins = values['baseline_wins']
        candidate_wins = values['candidate_wins']
        loss_to_win = values['loss_to_win']
        win_to_loss = values['win_to_loss']
        lines.append(f'| {opponent} | {games} | {baseline_wins} | {candidate_wins} | {loss_to_win} | {win_to_loss} |')
    lines.extend([
        '',
        '## Seat',
        '',
        '| seat | games | baseline wins | candidate wins | loss_to_win | win_to_loss |',
        '|---|---:|---:|---:|---:|---:|',
    ])
    for seat, values in report['seat'].items():
        games = values['games']
        baseline_wins = values['baseline_wins']
        candidate_wins = values['candidate_wins']
        loss_to_win = values['loss_to_win']
        win_to_loss = values['win_to_loss']
        lines.append(f'| {seat} | {games} | {baseline_wins} | {candidate_wins} | {loss_to_win} | {win_to_loss} |')
    markdown_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


__all__ = ['report_round']
