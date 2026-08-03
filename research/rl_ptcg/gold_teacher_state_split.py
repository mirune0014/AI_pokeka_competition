"""Leakage-safe episode split for upper-tier teacher states."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

from .gold_oracle_states import canonical_sha256, file_sha256, write_once
from .gold_upper_tier_states import verify_gold_upper_tier_states


SCHEMA_VERSION = "gold_teacher_state_split.v1"
ALLOWED_SPLITS = frozenset(("train", "development", "policy_family_holdout"))


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain an object" % path)
    return value


def _read_states(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_bytes().splitlines()
    except OSError as error:
        raise ValueError("could not read teacher states") from error
    if not lines or any(not line for line in lines):
        raise ValueError("teacher states must be non-empty JSONL without blank rows")
    result = []
    for raw in lines:
        try:
            value = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("teacher states contain invalid JSONL") from error
        if not isinstance(value, dict):
            raise ValueError("teacher state row must be an object")
        result.append(value)
    return result


def _resolve(path: str | Path, workspace: Path) -> Path:
    value = Path(path)
    resolved = (value if value.is_absolute() else workspace / value).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _relative(path: Path, workspace: Path) -> str:
    value = str(path.resolve().relative_to(workspace.resolve())).replace("\\", "/")
    return value or "."


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _normalized_assignments(assignments: Mapping[str, str]) -> dict[str, str]:
    result = {}
    for episode, split in assignments.items():
        key, value = str(episode), str(split)
        if not key or value not in ALLOWED_SPLITS or key in result:
            raise ValueError("episode split assignments must be unique and explicitly non-blind")
        result[key] = value
    if not result:
        raise ValueError("episode split assignments must be non-empty")
    return dict(sorted(result.items()))


def _build_value(corpus: Path, workspace: Path, assignments: Mapping[str, str]) -> dict[str, Any]:
    verify_gold_upper_tier_states(corpus, workspace)
    episode_splits = _normalized_assignments(assignments)
    states = _read_states(corpus / "states.jsonl")
    episodes = {str(state.get("episode_id", "")) for state in states}
    if "" in episodes or episodes != set(episode_splits):
        raise ValueError("episode split assignments must cover the corpus exactly")
    state_ids, decision_ids = set(), set()
    items = []
    for state in states:
        state_id, decision_id = state.get("state_id"), state.get("decision_id")
        episode = str(state.get("episode_id"))
        if (
            not isinstance(state_id, str) or not state_id
            or not isinstance(decision_id, str) or not decision_id
            or state_id in state_ids or decision_id in decision_ids
        ):
            raise ValueError("teacher states must map one-to-one to decisions")
        if state.get("split") not in ALLOWED_SPLITS:
            raise ValueError("source teacher state is blind or has an unknown split")
        metadata = state.get("current_metadata")
        if not isinstance(metadata, Mapping) or not isinstance(metadata.get("opponent_archetype"), str):
            raise ValueError("teacher state has no opponent archetype metadata")
        items.append({
            "state_id": state_id,
            "decision_id": decision_id,
            "episode_id": episode,
            "opponent_archetype": metadata["opponent_archetype"],
            "split": episode_splits[episode],
        })
        state_ids.add(state_id)
        decision_ids.add(decision_id)
    items.sort(key=lambda item: (item["episode_id"], item["state_id"]))
    split_states = Counter(item["split"] for item in items)
    split_episodes = Counter(episode_splits.values())
    archetype_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        archetype_counts[item["opponent_archetype"]][item["split"]] += 1
    value = {
        "schema_version": SCHEMA_VERSION,
        "corpus": {
            "path": _relative(corpus, workspace),
            "manifest_file_sha256": file_sha256(corpus / "manifest.json"),
            "manifest_sha256": _read_object(corpus / "manifest.json").get("manifest_sha256"),
            "selection_manifest_file_sha256": file_sha256(corpus / "selection_manifest.json"),
            "states_file_sha256": file_sha256(corpus / "states.jsonl"),
        },
        "assignment_policy": {
            "group_key": "episode_id",
            "assignment_source": "explicit_pre_label_episode_map",
            "allowed_signals": ["episode_id"],
            "forbidden_signals": [
                "recorded_action", "candidate_action", "rollout_result", "terminal_result",
                "post_decision_history", "teacher_label",
            ],
            "blind_split_allowed": False,
        },
        "episode_splits": episode_splits,
        "items": items,
        "counts": {
            "states": len(items),
            "episodes": len(episode_splits),
            "split_states": {key: split_states.get(key, 0) for key in sorted(ALLOWED_SPLITS)},
            "split_episodes": {key: split_episodes.get(key, 0) for key in sorted(ALLOWED_SPLITS)},
            "archetype_split_states": {
                archetype: {key: counts.get(key, 0) for key in sorted(ALLOWED_SPLITS)}
                for archetype, counts in sorted(archetype_counts.items())
            },
        },
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_teacher_state_split(
    corpus_dir: str | Path,
    episode_splits: Mapping[str, str],
    output_path: str | Path,
    workspace_root: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    corpus, output = _resolve(corpus_dir, workspace), _resolve(output_path, workspace)
    value = _build_value(corpus, workspace, episode_splits)
    write_once(output, value)
    return verify_teacher_state_split(output, workspace)


def verify_teacher_state_split(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    value = _read_object(output)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("manifest_sha256") != _self_hash(value):
        raise ValueError("teacher state split self-hash mismatch")
    corpus = _resolve(str(value.get("corpus", {}).get("path", "")), workspace)
    expected = _build_value(corpus, workspace, value.get("episode_splits", {}))
    if value != expected:
        raise ValueError("teacher state split does not reproduce")
    return {
        "verified": True,
        "states": value["counts"]["states"],
        "episodes": value["counts"]["episodes"],
        "manifest_sha256": value["manifest_sha256"],
        "split_by_decision_id": {item["decision_id"]: item["split"] for item in value["items"]},
        "output_path": str(output),
    }

