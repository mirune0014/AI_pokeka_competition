"""Compact dataset construction and one-round DAgger aggregation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import torch

from .build_complete_bc_dataset import DATASET_SCHEMA_VERSION
from .encoders import ACTION_DIM, STATE_DIM


def _tensor_count(value: torch.Tensor) -> int:
    return int(value.shape[0])


def payload_from_dagger_rows(
    *,
    episodes: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Pack actor-visited, teacher-labelled rows into the standard BC schema."""

    if not episodes or not rows:
        raise ValueError("DAgger payload requires episodes and decisions")
    if any(str(row.get("split")) != "train" for row in episodes):
        raise ValueError("DAgger episodes must be train-only")
    episode_ids = [str(row.get("episode_id", "")) for row in episodes]
    if any(not value for value in episode_ids) or len(set(episode_ids)) != len(episode_ids):
        raise ValueError("DAgger episode IDs must be present and unique")

    family_names = sorted({str(row["family"]) for row in rows})
    family_table = {name: index for index, name in enumerate(family_names)}
    decision_count = len(rows)
    option_total = sum(len(row["option_vectors"]) for row in rows)
    candidate_total = sum(len(row["candidate_members"]) for row in rows)
    member_total = sum(
        len(members)
        for row in rows
        for members in row["candidate_members"]
    )
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

    option_cursor = candidate_cursor = member_cursor = 0
    option_offsets[0] = 0
    decision_candidate_offsets[0] = 0
    candidate_member_offsets[0] = 0
    maximum_candidates = 0
    for row_index, row in enumerate(rows):
        state = row["state"]
        options = row["option_vectors"]
        candidates = row["candidate_members"]
        episode_index = int(row["episode_index"])
        target = int(row["target"])
        if len(state) != STATE_DIM:
            raise ValueError("DAgger row has the wrong state dimension")
        if any(len(option) != ACTION_DIM for option in options):
            raise ValueError("DAgger row has the wrong action dimension")
        if not 0 <= episode_index < len(episodes):
            raise ValueError("DAgger row episode index is invalid")
        if not candidates or not 0 <= target < len(candidates):
            raise ValueError("DAgger row target is outside its candidates")
        if any(
            any(not 0 <= int(member) < len(options) for member in members)
            for members in candidates
        ):
            raise ValueError("DAgger candidate membership is invalid")

        states[row_index] = torch.tensor(state, dtype=torch.float32)
        next_option = option_cursor + len(options)
        if options:
            option_vectors[option_cursor:next_option] = torch.tensor(
                options, dtype=torch.float32
            )
        option_cursor = next_option
        option_offsets[row_index + 1] = option_cursor

        maximum_candidates = max(maximum_candidates, len(candidates))
        for members in candidates:
            next_member = member_cursor + len(members)
            if members:
                candidate_members[member_cursor:next_member] = torch.tensor(
                    members, dtype=torch.int32
                )
            member_cursor = next_member
            candidate_cursor += 1
            candidate_member_offsets[candidate_cursor] = member_cursor
        decision_candidate_offsets[row_index + 1] = candidate_cursor
        targets[row_index] = target
        episode_indices[row_index] = episode_index
        family_indices[row_index] = family_table[str(row["family"])]
        optional_flags[row_index] = bool(row["optional"])
        multiple_flags[row_index] = bool(row["multiple"])

    duplicate_total = sum(int(row.get("duplicate_canonical_actions", 0)) for row in rows)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "episodes": [dict(row) for row in episodes],
        "family_table": family_table,
        "split_algorithm": {
            "unit": "episode",
            "dagger_round": 1,
            "all_actor_visited_episodes_are_training_only": True,
        },
        "source": dict(source),
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
            "train_episodes": len(episodes),
            "validation_episodes": 0,
            "decisions": decision_count,
            "options": option_total,
            "candidates": candidate_total,
            "candidate_members": member_total,
            "duplicate_canonical_actions": duplicate_total,
            "maximum_candidates_per_decision": maximum_candidates,
            "representability_failures": 0,
        },
    }


def _offset_concat(
    payloads: Sequence[Mapping[str, Any]], key: str
) -> torch.Tensor:
    pieces: list[torch.Tensor] = [torch.zeros(1, dtype=torch.int64)]
    running = 0
    for payload in payloads:
        offsets = payload["tensors"][key].to(dtype=torch.int64, device="cpu")
        if offsets.ndim != 1 or len(offsets) < 2 or int(offsets[0]) != 0:
            raise ValueError(f"dataset {key} is malformed")
        pieces.append(offsets[1:] + running)
        running += int(offsets[-1])
    return torch.cat(pieces)


def merge_complete_bc_payloads(
    *,
    base: Mapping[str, Any],
    additions: Sequence[Mapping[str, Any]],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Append train-only DAgger payloads while preserving locked validation."""

    if not additions:
        raise ValueError("at least one DAgger addition is required")
    payloads = [base, *additions]
    for payload in payloads:
        if (
            payload.get("schema_version") != DATASET_SCHEMA_VERSION
            or int(payload.get("state_dim", -1)) != STATE_DIM
            or int(payload.get("action_dim", -1)) != ACTION_DIM
        ):
            raise ValueError("complete-action dataset schema mismatch")
    if not any(row.get("split") == "validation" for row in base["episodes"]):
        raise ValueError("base dataset has no locked validation episodes")
    if any(
        row.get("split") != "train"
        for payload in additions
        for row in payload["episodes"]
    ):
        raise ValueError("DAgger additions may not add validation episodes")

    episodes: list[dict[str, Any]] = []
    episode_offsets: list[int] = []
    seen_episode_ids: set[str] = set()
    for payload in payloads:
        episode_offsets.append(len(episodes))
        for raw in payload["episodes"]:
            row = dict(raw)
            episode_id = str(row.get("episode_id", ""))
            if not episode_id or episode_id in seen_episode_ids:
                raise ValueError("merged episode IDs must be present and unique")
            seen_episode_ids.add(episode_id)
            episodes.append(row)

    family_names = sorted(
        {
            str(name)
            for payload in payloads
            for name in payload["family_table"]
        }
    )
    family_table = {name: index for index, name in enumerate(family_names)}
    family_parts: list[torch.Tensor] = []
    episode_index_parts: list[torch.Tensor] = []
    for payload, episode_offset in zip(payloads, episode_offsets):
        inverse = {int(value): str(name) for name, value in payload["family_table"].items()}
        old_family = payload["tensors"]["family_indices"].tolist()
        family_parts.append(
            torch.tensor(
                [family_table[inverse[int(value)]] for value in old_family],
                dtype=torch.int16,
            )
        )
        episode_index_parts.append(
            payload["tensors"]["episode_indices"].to(dtype=torch.int32, device="cpu")
            + episode_offset
        )

    tensors = {
        "states": torch.cat(
            [payload["tensors"]["states"].to(device="cpu") for payload in payloads]
        ),
        "option_vectors": torch.cat(
            [payload["tensors"]["option_vectors"].to(device="cpu") for payload in payloads]
        ),
        "option_offsets": _offset_concat(payloads, "option_offsets"),
        "decision_candidate_offsets": _offset_concat(
            payloads, "decision_candidate_offsets"
        ),
        "candidate_member_offsets": _offset_concat(
            payloads, "candidate_member_offsets"
        ),
        "candidate_members": torch.cat(
            [payload["tensors"]["candidate_members"].to(device="cpu") for payload in payloads]
        ),
        "targets": torch.cat(
            [payload["tensors"]["targets"].to(device="cpu") for payload in payloads]
        ),
        "episode_indices": torch.cat(episode_index_parts),
        "family_indices": torch.cat(family_parts),
        "optional_flags": torch.cat(
            [payload["tensors"]["optional_flags"].to(device="cpu") for payload in payloads]
        ),
        "multiple_flags": torch.cat(
            [payload["tensors"]["multiple_flags"].to(device="cpu") for payload in payloads]
        ),
    }
    split_values = {str(row.get("split")) for row in episodes}
    if split_values != {"train", "validation"}:
        raise ValueError("merged dataset must preserve train and validation splits")
    decision_count = _tensor_count(tensors["states"])
    if any(
        _tensor_count(tensors[key]) != decision_count
        for key in (
            "targets",
            "episode_indices",
            "family_indices",
            "optional_flags",
            "multiple_flags",
        )
    ):
        raise ValueError("merged decision tensors have inconsistent lengths")

    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "episodes": episodes,
        "family_table": family_table,
        "split_algorithm": {
            "unit": "episode",
            "base_locked_validation_preserved": True,
            "dagger_additions_split": "train",
            "dagger_rounds": 1,
            "base_split_algorithm": dict(base.get("split_algorithm") or {}),
        },
        "source": dict(source),
        "tensors": tensors,
        "counts": {
            "episodes": len(episodes),
            "train_episodes": sum(row.get("split") == "train" for row in episodes),
            "validation_episodes": sum(
                row.get("split") == "validation" for row in episodes
            ),
            "decisions": decision_count,
            "options": _tensor_count(tensors["option_vectors"]),
            "candidates": int(tensors["decision_candidate_offsets"][-1]),
            "candidate_members": _tensor_count(tensors["candidate_members"]),
            "duplicate_canonical_actions": sum(
                int(payload["counts"].get("duplicate_canonical_actions", 0))
                for payload in payloads
            ),
            "maximum_candidates_per_decision": max(
                int(payload["counts"].get("maximum_candidates_per_decision", 0))
                for payload in payloads
            ),
            "representability_failures": sum(
                int(payload["counts"].get("representability_failures", 0))
                for payload in payloads
            ),
        },
    }
