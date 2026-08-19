from __future__ import annotations

from dataclasses import replace

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.schedule import all_plans, plans_by_episode
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q import search_plan as search_plan_module
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.search_plan import STAGES, build_plan, group_shard, select_group_records
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchPoint, SourceTrace


def test_stage_names_and_fixed_group_shard() -> None:
    assert STAGES == ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment")
    group_id = "0123456789abcdef" + "0" * 48
    assert group_shard(group_id, 6) == int(group_id[:16], 16) % 6
    assert group_shard(group_id, 6) == group_shard(group_id, 6)


def test_pilot_caps_are_not_used_by_full_group_selection() -> None:
    config = load_config()
    plans = plans_by_episode(all_plans(config, pilot=True))
    records = []
    for plan in plans.values():
        if plan.split == "calibration":
            stage = "calibration"
        elif plan.split == "offline_test":
            stage = "offline_test"
        else:
            stage = "train_m05"
        for index in range(10):
            records.append(
                {
                    "branch_group_id": f"{plan.episode_id}-synthetic-{index}",
                    "source_episode_id": plan.episode_id,
                    "stage": stage,
                }
            )

    full = select_group_records(records, plans, pilot=False)
    pilot = select_group_records(records, plans, pilot=True)

    assert len(full) == len(records)
    assert len(pilot) < len(full)
    assert len({row["branch_group_id"] for row in full}) == len(full)
    assert {row["stage"] for row in full} == {"train_m05", "calibration", "offline_test"}
    assert all(sum(row["branch_group_id"] == group_id for row in full) == 1 for group_id in {row["branch_group_id"] for row in full})


def test_full_plan_consumes_all_synthetic_source_groups(tmp_path, monkeypatch) -> None:
    base = load_config()
    small = replace(
        base,
        source_games={"training": 64, "calibration": 16, "offline_test": 16},
        output_root=str(tmp_path / "full"),
    )
    plans = all_plans(small)
    traces = []
    for plan in plans:
        points = tuple(
            BranchPoint(
                branch_group_id=f"{plan.episode_id}-group-{index}",
                step_index=index,
                raw_observation_sha256=f"{index:064x}",
                public_state={"step": index},
                baseline_action=(0,),
                baseline_candidate_index=0,
                candidates=(
                    {"candidate_index": 0, "action": [0], "canonical_identity": "baseline"},
                    {"candidate_index": 1, "action": [1], "canonical_identity": "alternative"},
                ),
            )
            for index in range(10)
        )
        traces.append(
            SourceTrace(
                episode_id=plan.episode_id,
                opponent_id=plan.opponent_id,
                seat=plan.seat,
                seed=plan.seed,
                terminal_result=1,
                terminal_reward=1.0,
                clean_terminal=True,
                steps=(),
                branch_points=points,
            )
        )

    monkeypatch.setattr(search_plan_module, "load_source_traces", lambda config, plans: traces)
    full_result = build_plan(small, pilot=False)
    pilot = replace(small, output_root=str(tmp_path / "pilot"))
    pilot_result = build_plan(pilot, pilot=True)

    assert full_result["groups"] == 960
    assert full_result["stage_counts"] == {"calibration": 160, "offline_test": 160, "train_m05": 640, "train_m10_increment": 0, "train_m20_increment": 0}
    assert pilot_result["groups"] == 160
