import json
from dataclasses import asdict

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.config import input_path, load_config
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.hidden_sampler import sample_hidden_zones
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.search_runtime import (
    _as_plain,
    _load_api,
    _player,
    replay_to_branch_root,
    run_candidate_search,
)
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.worker import load_task_groups
from research.experiments.archaludon_rollout_q_v1.rollout_q.complete_action import observation_complete_actions, observation_option_rows
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import SourceTrace
from research.experiments.archaludon_latest_v1_rl_pcgrad_candidate_20260801.archaludon_rl.public_state import project_public_state


def test_real_engine_search_surface_root_and_paired_continuation():
    config = load_config()
    task = next(iter(next(iter(load_task_groups(config).values()))))
    trace = SourceTrace.from_dict(json.loads(input_path(config, "source_traces", f"{task.source_episode_id}.json").read_text(encoding="utf-8")))
    replayed = replay_to_branch_root(config, task, trace)
    api = _load_api()
    hidden = sample_hidden_zones(
        replayed.observation,
        branch_group_id=task.branch_group_id,
        rollout_index=0,
        your_deck=replayed.source_policy.deck,
        opponent_deck=replayed.opponent_policy.deck,
        api_module=api,
    )
    root = api.search_begin(
        api.to_observation_class(replayed.observation),
        list(hidden.your_deck),
        list(hidden.your_prize),
        list(hidden.opponent_deck),
        list(hidden.opponent_prize),
        list(hidden.opponent_hand),
        list(hidden.opponent_active),
        manual_coin=True,
    )
    current = root
    opponent_turn_seen = False
    try:
        root_projection = project_public_state(root.observation)
        raw_projection = project_public_state(replayed.observation)
        root_projection.pop("logs", None)
        raw_projection.pop("logs", None)
        assert root_projection == raw_projection
        assert root.observation.current.players[1].hand is None
        branch_candidates = observation_complete_actions(replayed.observation)
        root_candidates = observation_complete_actions(root.observation)
        assert {item.canonical_identity for item in branch_candidates.candidates} == {item.canonical_identity for item in root_candidates.candidates}
        assert branch_candidates.candidate_index_for(observation_option_rows(replayed.observation), task.baseline_action) == task.baseline_candidate_index
        current = api.search_step(root.searchId, list(task.baseline_action))
        api.search_release(root.searchId)
        for _ in range(100):
            observation = current.observation
            result = getattr(observation.current, "result", -1) if observation.current is not None else -1
            if _player(observation) != task.seat:
                opponent_turn_seen = True
                assert observation.current.players[_player(observation)].hand is not None
                break
            if result in (0, 1, 2) or observation.select is None:
                break
            action = replayed.source_policy(_as_plain(observation))
            next_state = api.search_step(current.searchId, list(action))
            api.search_release(current.searchId)
            current = next_state
        assert opponent_turn_seen
    finally:
        try:
            api.search_release(current.searchId)
        except Exception:
            pass
        api.search_end()
    reward = run_candidate_search(
        replayed,
        hidden,
        task.baseline_action,
        branch_group_id=task.branch_group_id,
        rollout_index=0,
        max_steps=config.maximum_search_steps,
        manual_coin=True,
    )
    assert reward in (-1.0, 0.0, 1.0)
