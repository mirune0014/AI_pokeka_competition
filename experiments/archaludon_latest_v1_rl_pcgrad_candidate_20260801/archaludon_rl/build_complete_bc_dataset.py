"""Build a compact tensor dataset from complete-action teacher trajectories."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import torch

from .complete_action import recorded_complete_actions
from .encoders import ACTION_DIM, STATE_DIM
from .frozen_sources import sha256_file


DATASET_SCHEMA_VERSION = "complete-action-bc-tensor-dataset-v1"


def _episode_paths(directory: Path) -> list[Path]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("complete-action BC source has no episodes")
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise ValueError("complete-action BC source paths must be ordinary files")
    return paths


def _read_episode(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"episode is not an object: {path}")
    return payload


def _iter_decisions(paths: Sequence[Path]) -> Iterator[tuple[int, Mapping[str, Any], Mapping[str, Any]]]:
    for episode_index, path in enumerate(paths):
        episode = _read_episode(path)
        for decision in episode.get("decisions") or ():
            yield episode_index, episode, decision


def _episode_metadata(
    paths: Sequence[Path],
    *,
    validation_seed_base: int,
    validation_seed_modulus: int,
    validation_seed_residue: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        episode = _read_episode(path)
        episode_id = str(episode.get("episode_id", ""))
        if not episode_id or episode_id in seen:
            raise ValueError("episode IDs must be present and unique")
        seen.add(episode_id)
        seed = int(episode["seed"])
        validation = (
            (seed - validation_seed_base) % validation_seed_modulus
            == validation_seed_residue
        )
        result.append(
            {
                "episode_id": episode_id,
                "opponent_id": str(episode["opponent_id"]),
                "seat": int(episode["seat"]),
                "seed": seed,
                "split": "validation" if validation else "train",
                "path": path.name,
                "sha256": sha256_file(path),
                "terminal_result": int(episode.get("terminal_result", -1)),
                "action_errors": int(episode.get("action_errors", 0)),
                "max_step_hit": bool(episode.get("max_step_hit", False)),
            }
        )
    return result


def _validate_row(
    decision: Mapping[str, Any],
    *,
    require_teacher_trajectory: bool,
) -> tuple[Any, int, str]:
    state = decision.get("state_vector") or ()
    options = decision.get("legal_semantic_options") or ()
    vectors = decision.get("action_vectors") or ()
    teacher = tuple(decision.get("teacher_action") or ())
    if len(state) != STATE_DIM:
        raise ValueError("complete-action BC row has wrong state dimension")
    if len(options) != len(vectors) or any(len(vector) != ACTION_DIM for vector in vectors):
        raise ValueError("complete-action BC row has wrong option-vector dimensions")
    if require_teacher_trajectory and tuple(decision.get("final_action") or ()) != teacher:
        raise ValueError("rule-policy rollout contains a non-teacher executed action")
    candidates = recorded_complete_actions(decision)
    target = candidates.candidate_index_for(options, teacher)
    if target is None:
        raise ValueError("teacher action is not representable by complete candidates")
    selected_types = sorted(
        {str(options[index]["payload"]["option_type"]) for index in teacher}
    )
    family = "empty" if not selected_types else "+".join(selected_types)
    return candidates, target, family


def build(args: argparse.Namespace) -> dict[str, Any]:
    if args.validation_seed_modulus <= 1:
        raise ValueError("validation seed modulus must exceed one")
    if not 0 <= args.validation_seed_residue < args.validation_seed_modulus:
        raise ValueError("validation seed residue is outside the modulus")
    source_dir = args.episodes_dir.resolve()
    output = args.output.resolve()
    report_path = args.report.resolve()
    if output.exists() or report_path.exists():
        raise FileExistsError("complete-action dataset output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    paths = _episode_paths(source_dir)
    episodes = _episode_metadata(
        paths,
        validation_seed_base=args.validation_seed_base,
        validation_seed_modulus=args.validation_seed_modulus,
        validation_seed_residue=args.validation_seed_residue,
    )
    if args.expected_episodes and len(episodes) != args.expected_episodes:
        raise ValueError(f"episode count {len(episodes)} != {args.expected_episodes}")
    if set(row["split"] for row in episodes) != {"train", "validation"}:
        raise ValueError("episode split must contain train and validation")
    cell_counts = Counter((row["opponent_id"], row["seat"]) for row in episodes)
    if args.expected_episodes_per_cell and (
        not cell_counts
        or any(value != args.expected_episodes_per_cell for value in cell_counts.values())
    ):
        raise ValueError("opponent/seat episode cells are not balanced")
    if any(row["action_errors"] != 0 or row["max_step_hit"] for row in episodes):
        raise ValueError("source rollout contains action errors or max-step hits")

    decision_count = 0
    option_total = 0
    candidate_total = 0
    member_total = 0
    duplicate_total = 0
    maximum_candidates = 0
    family_names: set[str] = set()
    for _, _, decision in _iter_decisions(paths):
        candidates, _, family = _validate_row(
            decision,
            require_teacher_trajectory=args.require_teacher_trajectory,
        )
        decision_count += 1
        option_total += candidates.option_count
        candidate_total += len(candidates.candidates)
        member_total += sum(len(candidate.action) for candidate in candidates.candidates)
        duplicate_total += candidates.duplicate_canonical_action_count
        maximum_candidates = max(maximum_candidates, len(candidates.candidates))
        family_names.add(family)
    if decision_count == 0:
        raise ValueError("complete-action BC dataset has no decisions")
    if maximum_candidates > args.maximum_candidates:
        raise ValueError("complete-action candidate count exceeds fixed maximum")

    states = torch.empty((decision_count, STATE_DIM), dtype=torch.float32)
    option_vectors = torch.empty((option_total, ACTION_DIM), dtype=torch.float32)
    option_offsets = torch.empty(decision_count + 1, dtype=torch.int64)
    decision_candidate_offsets = torch.empty(decision_count + 1, dtype=torch.int64)
    candidate_member_offsets = torch.empty(candidate_total + 1, dtype=torch.int64)
    candidate_members = torch.empty(member_total, dtype=torch.int32)
    targets = torch.empty(decision_count, dtype=torch.int64)
    episode_indices = torch.empty(decision_count, dtype=torch.int32)
    family_indices = torch.empty(decision_count, dtype=torch.int16)
    optional_flags = torch.empty(decision_count, dtype=torch.bool)
    multiple_flags = torch.empty(decision_count, dtype=torch.bool)
    family_table = {name: index for index, name in enumerate(sorted(family_names))}

    row_cursor = option_cursor = candidate_cursor = member_cursor = 0
    option_offsets[0] = 0
    decision_candidate_offsets[0] = 0
    candidate_member_offsets[0] = 0
    for episode_index, _, decision in _iter_decisions(paths):
        candidates, target, family = _validate_row(
            decision,
            require_teacher_trajectory=args.require_teacher_trajectory,
        )
        vectors = decision.get("action_vectors") or ()
        state = decision.get("state_vector") or ()
        teacher = tuple(decision.get("teacher_action") or ())
        select = (decision.get("public_projection") or {}).get("select") or {}
        states[row_cursor] = torch.tensor(state, dtype=torch.float32)
        next_option = option_cursor + len(vectors)
        if vectors:
            option_vectors[option_cursor:next_option] = torch.tensor(vectors, dtype=torch.float32)
        option_cursor = next_option
        option_offsets[row_cursor + 1] = option_cursor
        targets[row_cursor] = target
        episode_indices[row_cursor] = episode_index
        family_indices[row_cursor] = family_table[family]
        optional_flags[row_cursor] = int(select.get("min_count", -1)) == 0
        multiple_flags[row_cursor] = len(teacher) > 1
        for candidate in candidates.candidates:
            next_member = member_cursor + len(candidate.action)
            if candidate.action:
                candidate_members[member_cursor:next_member] = torch.tensor(candidate.action, dtype=torch.int32)
            member_cursor = next_member
            candidate_cursor += 1
            candidate_member_offsets[candidate_cursor] = member_cursor
        decision_candidate_offsets[row_cursor + 1] = candidate_cursor
        row_cursor += 1
    if (row_cursor, option_cursor, candidate_cursor, member_cursor) != (
        decision_count,
        option_total,
        candidate_total,
        member_total,
    ):
        raise AssertionError("complete-action BC tensor fill accounting failed")

    payload = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "episodes": episodes,
        "family_table": family_table,
        "split_algorithm": {
            "unit": "episode",
            "validation_seed_base": args.validation_seed_base,
            "validation_seed_modulus": args.validation_seed_modulus,
            "validation_seed_residue": args.validation_seed_residue,
            "validation_selected_without_metric_access": True,
        },
        "source": {
            "episodes_dir": str(source_dir),
            "require_teacher_trajectory": bool(args.require_teacher_trajectory),
        },
        "tensors": {
            "states": states,
            "option_vectors": option_vectors,
            "option_offsets": option_offsets,
            "decision_candidate_offsets": decision_candidate_offsets,
            "candidate_member_offsets": candidate_member_offsets,
            "candidate_members": candidate_members,
            "targets": targets,
            "episode_indices": episode_indices,
            "family_indices": family_indices,
            "optional_flags": optional_flags,
            "multiple_flags": multiple_flags,
        },
        "counts": {
            "episodes": len(episodes),
            "train_episodes": sum(row["split"] == "train" for row in episodes),
            "validation_episodes": sum(row["split"] == "validation" for row in episodes),
            "decisions": decision_count,
            "options": option_total,
            "candidates": candidate_total,
            "candidate_members": member_total,
            "duplicate_canonical_actions": duplicate_total,
            "maximum_candidates_per_decision": maximum_candidates,
            "representability_failures": 0,
        },
    }
    torch.save(payload, output)
    report = {
        "schema_version": "complete-action-bc-dataset-build-report-v1",
        "dataset": str(output),
        "dataset_sha256": sha256_file(output),
        "dataset_bytes": output.stat().st_size,
        "counts": payload["counts"],
        "split_algorithm": payload["split_algorithm"],
        "cell_counts": {
            f"{opponent}:seat{seat}": count
            for (opponent, seat), count in sorted(cell_counts.items())
        },
        "source_episode_bytes": sum(path.stat().st_size for path in paths),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--validation-seed-base", type=int, required=True)
    parser.add_argument("--validation-seed-modulus", type=int, default=5)
    parser.add_argument("--validation-seed-residue", type=int, default=0)
    parser.add_argument("--expected-episodes", type=int, default=0)
    parser.add_argument("--expected-episodes-per-cell", type=int, default=0)
    parser.add_argument("--maximum-candidates", type=int, default=4096)
    parser.add_argument("--require-teacher-trajectory", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    build(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
