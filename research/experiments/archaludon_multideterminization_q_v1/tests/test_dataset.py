from types import SimpleNamespace

from research.experiments.archaludon_multideterminization_q_v1.multidet_q import dataset as dataset_module
from research.experiments.archaludon_rollout_q_v1.rollout_q.dataset import episode_split
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def test_group_dataset_keeps_episode_split_and_baseline(monkeypatch, tmp_path):
    group = "3" * 64
    candidates = [
        {"candidate_index": 0, "action": [0], "canonical_identity": "baseline", "selected_options": [], "order_sensitive": False},
        {"candidate_index": 1, "action": [1], "canonical_identity": "alternative", "selected_options": [{"semantic_payload": {"option_type": 7}}], "order_sensitive": False},
    ]
    tasks = [
        BranchTask.create(
            source_episode_id="round_00_test_seat0_seed1",
            opponent_id="test",
            seat=0,
            seed=1,
            branch_step_index=1,
            candidate_index=index,
            candidate_action=[index],
            candidate_identity=candidates[index]["canonical_identity"],
            baseline_candidate_index=0,
            baseline_action=[0],
            branch_group=group,
            public_state={"select": {"context": 0}, "players": []},
            candidates=candidates,
        )
        for index in range(2)
    ]
    merged = [{
        "schema_version": dataset_module.GROUP_SCHEMA,
        "branch_group_id": group,
        "status": "OK",
        "candidates": [
            {"task_id": tasks[1].task_id, "candidate_index": 1, "canonical_identity": "alternative", "mean_reward": 1.0, "mean_delta": 1.0, "delta_lcb90": 0.5, "delta_ucb90": 1.5, "positive_delta_count": 1, "zero_delta_count": 0, "negative_delta_count": 0, "rewards": [1.0]},
            {"task_id": tasks[0].task_id, "candidate_index": 0, "canonical_identity": "baseline", "mean_reward": 0.0, "rewards": [0.0]},
        ],
    }]
    fake_config = SimpleNamespace()
    monkeypatch.setattr(dataset_module, "load_task_groups", lambda config: {group: tasks})
    monkeypatch.setattr(dataset_module, "_read_merged", lambda config: merged)
    monkeypatch.setattr(dataset_module, "output_path", lambda config, *parts: tmp_path.joinpath(*parts))
    written = {}
    monkeypatch.setattr(dataset_module, "write_json", lambda path, value: written.setdefault(str(path), value))

    summary = dataset_module.build_dataset(fake_config)
    payload = written[str(tmp_path / "dataset_through_round_00.json")]
    row = payload["rows"][0]
    assert summary["group_count"] == 1
    assert row["split"] == episode_split("round_00_test_seat0_seed1")
    assert row["candidates"][0]["is_baseline"] is True
    assert row["candidates"][1]["canonical_identity"] == "alternative"
    assert row["candidates"][1]["target_q"] == 1.0
