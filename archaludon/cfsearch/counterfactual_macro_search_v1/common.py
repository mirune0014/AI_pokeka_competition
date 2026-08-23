"""Small, deterministic helpers shared by the counterfactual MVP."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rl_ptcg.canonical_actions import canonicalize_prompt_action
from research.rl_ptcg.replay_reconstruction import ReplayDecision, iter_replay_decisions


SCHEMA_VERSION = "archaludon_counterfactual_root_action_search_mvp.v1"


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = (json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ) + "\n").encode("ascii")
    return sha256(payload).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {line_number} is not an object")
        rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _integer(value: Any, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def legal_action(observation: Mapping[str, Any], action: Sequence[int]) -> bool:
    """Check only the public prompt contract, not card effects."""
    if not isinstance(action, (list, tuple)):
        return False
    select = observation.get("select") or {}
    options = select.get("option") or []
    minimum = _integer(select.get("minCount", select.get("min_count", 0)), 0)
    maximum = _integer(select.get("maxCount", select.get("max_count", len(options))), len(options))
    if minimum is None or maximum is None or minimum > maximum:
        return False
    if not minimum <= len(action) <= maximum:
        return False
    if len(set(action)) != len(action):
        return False
    return all(
        isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(options)
        for index in action
    )


def singleton_action_semantics(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return unique legal singleton actions using semantic IDs.

    The extractor intentionally does not inspect replay visualizer frames or
    hidden world fields.  If canonicalization is ambiguous, the option is
    omitted rather than guessed.
    """
    select = observation.get("select") or {}
    options = select.get("option") or []
    if not options or not legal_action(observation, [0]):
        return []
    by_semantic: dict[str, dict[str, Any]] = {}
    for index in range(len(options)):
        action = [index]
        if not legal_action(observation, action):
            continue
        try:
            semantic_id = canonicalize_prompt_action(observation, action).stable_id
        except Exception:
            continue
        by_semantic.setdefault(semantic_id, {
            "semantic_id": semantic_id,
            "action": action,
            "option_index": index,
        })
    return [by_semantic[key] for key in sorted(by_semantic)]


def observation_hash(observation: Mapping[str, Any]) -> str:
    return canonical_sha256(observation)


def find_replay_decision(
    replay: Mapping[str, Any], *, replay_step: int, acting_seat: int,
) -> ReplayDecision:
    for decision in iter_replay_decisions(replay, seats=[acting_seat]):
        if decision.replay_step == replay_step and decision.acting_seat == acting_seat:
            return decision
    raise ValueError(
        f"decision not found at replay_step={replay_step}, acting_seat={acting_seat}"
    )


def public_root_descriptor(
    decision: ReplayDecision,
    parent_action: Sequence[int],
) -> dict[str, Any]:
    observation = dict(decision.observation)
    options = singleton_action_semantics(observation)
    if not legal_action(observation, parent_action):
        raise ValueError("parent action is not legal for the recorded prompt")
    if len(parent_action) != 1:
        raise ValueError("MVP roots require a singleton parent action")
    parent_semantic = canonicalize_prompt_action(observation, list(parent_action)).stable_id
    if parent_semantic not in {row["semantic_id"] for row in options}:
        raise ValueError("parent action is not represented by the singleton semantic set")
    alternatives = [row for row in options if row["semantic_id"] != parent_semantic]
    if not alternatives:
        raise ValueError("root has no distinct singleton alternative")
    return {
        "schema_version": SCHEMA_VERSION,
        "episode_id": decision.episode_id,
        "replay_step": int(decision.replay_step),
        "acting_seat": int(decision.acting_seat),
        "turn": decision.turn,
        "target_observation_sha256": observation_hash(observation),
        "target_option_semantic_ids": [row["semantic_id"] for row in options],
        "parent_action": list(parent_action),
        "parent_semantic_id": parent_semantic,
        "alternatives": alternatives,
        "public_history_length": len(decision.public_history),
    }
