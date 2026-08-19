import json

import pytest

from research.experiments.archaludon_multideterminization_q_v1.multidet_q import worker
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _task(group, index):
    return BranchTask.create(
        source_episode_id="round_00_test_seat0_seed1",
        opponent_id="test",
        seat=0,
        seed=1,
        branch_step_index=1,
        candidate_index=index,
        candidate_action=[index],
        candidate_identity=f"{group}-{index}",
        baseline_candidate_index=0,
        baseline_action=[0],
        branch_group=group,
        public_state={"select": {"context": 0}},
        candidates=[{"candidate_index": index, "action": [index], "canonical_identity": f"{group}-{index}"}],
    )


def _row(group, tasks):
    return {
        "schema_version": worker.GROUP_SCHEMA,
        "branch_group_id": group,
        "status": "OK",
        "candidates": [{"task_id": task.task_id} for task in tasks],
        "rollout_count": 1,
    }


def test_complete_group_skip_and_truncated_final_line(tmp_path):
    group = "1" * 64
    tasks = [_task(group, 0), _task(group, 1)]
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(_row(group, tasks)) + "\n{" , encoding="utf-8")
    rows, completed, truncated = worker._read_existing(path, {group: tasks})
    assert len(rows) == 1
    assert completed == {group}
    assert truncated == 1
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_partial_group_is_rerun_and_duplicate_is_rejected(tmp_path, monkeypatch):
    group = "2" * 64
    tasks = [_task(group, 0), _task(group, 1)]
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(_row(group, tasks[:1])) + "\n", encoding="utf-8")
    rows, completed, _ = worker._read_existing(path, {group: tasks})
    assert rows == []
    assert completed == set()
    assert path.read_text(encoding="utf-8") == ""

    monkeypatch.setattr(worker, "run_group", lambda config, group_tasks, rollout_count: _row(group, group_tasks))
    summary = worker.run_groups(
        object(),
        {group: tasks},
        output_file=path,
        rollout_count=1,
    )
    assert summary["written_groups"] == 1
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    path.write_text(path.read_text(encoding="utf-8") + path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(RuntimeError, match="duplicate group"):
        worker._read_existing(path, {group: tasks})
