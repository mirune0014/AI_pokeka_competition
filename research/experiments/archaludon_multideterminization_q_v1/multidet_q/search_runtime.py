"""Prefix replay and paired continuation through the seeded public search API."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline, load_opponent
from research.experiments.archaludon_rollout_q_v1.rollout_q.complete_action import (
    observation_complete_actions,
    observation_option_rows,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _battle_start,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
    trace_observation_hash,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import (
    BranchPoint,
    BranchTask,
    SourceTrace,
)
from research.experiments.archaludon_latest_v1_rl_pcgrad_candidate_20260801.archaludon_rl.public_state import (
    enum_int,
    project_public_state,
)

from .config import MultiDetConfig, REPO_ROOT
from .hidden_sampler import HiddenZones


class PrefixReplayMismatch(RuntimeError):
    pass


class SearchRootMismatch(RuntimeError):
    pass


class SearchRuntimeError(RuntimeError):
    pass


@dataclass
class ReplayedRoot:
    observation: dict[str, Any]
    source_policy: Any
    opponent_policy: Any
    policy_seat: int
    baseline_action: tuple[int, ...]
    branch_point: BranchPoint


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _terminal(observation: Any) -> int | None:
    current = _get(observation, "current", None)
    result = _int(_get(current, "result", None))
    return result if result in (0, 1, 2) else None


def _int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    raw = getattr(value, "value", value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _player(observation: Any) -> int:
    value = _int(_get(_get(observation, "current", None), "yourIndex", 0))
    if value not in (0, 1):
        raise SearchRuntimeError("current.yourIndex is not 0 or 1")
    return int(value)


def _policy_owner(policy: Any) -> Any:
    return getattr(policy, "owner", None)


def _resolve_opponent(config: MultiDetConfig, opponent_id: str) -> Path:
    for row in _opponent_rows():
        if str(row.get("id")) == str(opponent_id):
            # The old resolver only relies on the two policy-path properties,
            # which the new immutable config exposes with the same names.
            return resolve_opponent_dir(row, config)  # type: ignore[arg-type]
    raise KeyError(opponent_id)


def _as_plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {key: _as_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_plain(item) for item in value]
    return value


def _drop_search_nonpublic(value: Any) -> Any:
    value = _as_plain(value)
    if isinstance(value, Mapping):
        return {
            key: _drop_search_nonpublic(item)
            for key, item in value.items()
            if key not in {"logs", "search_begin_input"}
        }
    if isinstance(value, list):
        return [_drop_search_nonpublic(item) for item in value]
    return value


def _canonical_projection(value: Any) -> str:
    return json.dumps(_drop_search_nonpublic(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _public_projection(value: Any) -> dict[str, Any]:
    projection = dict(project_public_state(value))
    projection.pop("logs", None)
    return projection


def _load_api() -> Any:
    _load_engine()
    api = importlib.import_module("cg.api")
    required = (
        "to_observation_class",
        "search_begin",
        "search_step",
        "search_release",
        "search_end",
        "all_card_data",
        "all_attack",
    )
    missing = [name for name in required if not callable(getattr(api, name, None))]
    if missing:
        raise SearchRuntimeError(f"BLOCKED: seeded engine cg.api missing {','.join(missing)}")
    return api


def check_api_surface() -> dict[str, Any]:
    api = _load_api()
    names = (
        "to_observation_class",
        "search_begin",
        "search_step",
        "search_release",
        "search_end",
        "all_card_data",
        "all_attack",
    )
    return {"present": list(names), "missing": [name for name in names if not callable(getattr(api, name, None))]}


def replay_to_branch_root(
    config: MultiDetConfig,
    task: BranchTask,
    trace: SourceTrace,
) -> ReplayedRoot:
    """Recreate the original battle prefix and return a fresh branch root."""

    engine = _load_engine()
    battle_start, battle_select, battle_finish, _ = engine
    baseline = load_baseline(config.baseline_dir, config.baseline_dir.name)
    opponent = load_opponent(_resolve_opponent(config, task.opponent_id), task.opponent_id)
    baseline.seed(task.seed)
    opponent.seed(task.seed)
    baseline_deck = baseline.deck
    opponent_deck = opponent.deck
    decks = (baseline_deck, opponent_deck) if task.seat == 0 else (opponent_deck, baseline_deck)
    observation: Any = None
    started = False
    branch_observation: dict[str, Any] | None = None
    branch_point: BranchPoint | None = None
    trace_steps = {step.step_index: step for step in trace.steps}
    try:
        observation, start_data = _battle_start(battle_start, decks, task.seed)
        if not observation:
            raise PrefixReplayMismatch(
                f"engine start failed: {getattr(start_data, 'errorPlayer', None)}/{getattr(start_data, 'errorType', None)}"
            )
        started = True
        for step_index in range(int(config.maximum_search_steps)):
            if _terminal(observation) is not None:
                break
            if not isinstance(observation, Mapping) or not observation.get("select"):
                raise PrefixReplayMismatch(f"missing select at step {step_index}")
            expected = trace_steps.get(step_index)
            if expected is None:
                raise PrefixReplayMismatch(f"missing trace step {step_index}")
            if trace_observation_hash(observation) != expected.raw_observation_sha256:
                raise PrefixReplayMismatch(f"raw observation mismatch at step {step_index}")
            current_player = _player(observation)
            if current_player != expected.current_player:
                raise PrefixReplayMismatch(f"current player mismatch at step {step_index}")
            if current_player == task.seat:
                owner_before = _policy_owner(baseline)
                predicted = tuple(int(item) for item in baseline(observation))
                owner_after = _policy_owner(baseline)
                if predicted != tuple(expected.action):
                    raise PrefixReplayMismatch(f"source policy action mismatch at step {step_index}")
                if step_index == task.branch_step_index:
                    if owner_before is not None or owner_after is not None:
                        raise SearchRootMismatch("branch policy owner is not empty")
                    if tuple(task.baseline_action) != predicted:
                        raise SearchRootMismatch("task baseline action differs from trace")
                    live_candidates = observation_complete_actions(observation)
                    option_rows = observation_option_rows(observation)
                    live_baseline = live_candidates.candidate_index_for(option_rows, predicted)
                    live_selected = live_candidates.candidate_index_for(option_rows, task.candidate_action)
                    if live_baseline != task.baseline_candidate_index:
                        raise SearchRootMismatch("baseline candidate index differs at root")
                    if live_selected != task.candidate_index:
                        raise SearchRootMismatch("candidate identity differs at root")
                    expected_identities = [str(item["canonical_identity"]) for item in task.candidates]
                    actual_identities = [str(item.canonical_identity) for item in live_candidates.candidates]
                    if sorted(expected_identities) != sorted(actual_identities):
                        raise SearchRootMismatch("root candidate identity set differs from BranchPoint")
                    point = next((item for item in trace.branch_points if item.branch_group_id == task.branch_group_id), None)
                    if point is None:
                        raise SearchRootMismatch("trace does not contain branch group")
                    if point.step_index != task.branch_step_index:
                        raise SearchRootMismatch("branch step differs from trace BranchPoint")
                    if project_public_state(observation) != point.public_state:
                        raise SearchRootMismatch("branch public state differs from trace")
                    branch_observation = deepcopy(dict(observation))
                    branch_point = point
                    break
                action = list(predicted)
            else:
                predicted = tuple(int(item) for item in opponent(observation))
                if predicted != tuple(expected.action):
                    raise PrefixReplayMismatch(f"opponent policy action mismatch at step {step_index}")
                action = list(predicted)
            observation = battle_select(action)
        else:
            raise PrefixReplayMismatch("maximum steps reached before branch root")
        if branch_observation is None or branch_point is None:
            raise PrefixReplayMismatch("branch root was not reached")
        if _policy_owner(baseline) is not None:
            raise SearchRootMismatch("source policy owner changed at branch root")
        return ReplayedRoot(
            observation=branch_observation,
            source_policy=baseline,
            opponent_policy=opponent,
            policy_seat=int(task.seat),
            baseline_action=tuple(task.baseline_action),
            branch_point=branch_point,
        )
    finally:
        if started:
            battle_finish()


def _coin_action(observation: Any, branch_group_id: str, rollout_index: int, coin_event_index: int) -> list[int]:
    payload = f"{branch_group_id}|{int(rollout_index)}|{int(coin_event_index)}|coin-v1"
    choose_yes = int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[-1], 16) & 1
    desired = 1 if choose_yes else 2  # OptionType.YES / OptionType.NO
    select = _get(observation, "select")
    options = list(_get(select, "option", ()) or ())
    for index, option in enumerate(options):
        if _int(_get(option, "type")) == desired:
            return [index]
    raise SearchRuntimeError("coin schedule selected an illegal YES/NO option")


def _reward(result: int, policy_seat: int) -> float:
    if result == 2:
        return 0.0
    if result == policy_seat:
        return 1.0
    if result in (0, 1):
        return -1.0
    raise SearchRuntimeError(f"unknown terminal result: {result}")


def _search_observation_for_agent(observation: Any) -> dict[str, Any]:
    value = _as_plain(observation)
    if not isinstance(value, dict):
        raise SearchRuntimeError("search observation is not a dataclass mapping")
    return value


def run_candidate_search(
    replayed_root: ReplayedRoot,
    hidden: HiddenZones,
    candidate_action: Sequence[int],
    *,
    branch_group_id: str,
    rollout_index: int,
    max_steps: int,
    manual_coin: bool = True,
) -> float:
    """Run one candidate continuation and return terminal reward."""

    api = _load_api()
    raw_observation = replayed_root.observation
    agent_observation = api.to_observation_class(raw_observation)
    root = None
    current_state = None
    started = False
    try:
        root = api.search_begin(
            agent_observation=agent_observation,
            your_deck=list(hidden.your_deck),
            your_prize=list(hidden.your_prize),
            opponent_deck=list(hidden.opponent_deck),
            opponent_prize=list(hidden.opponent_prize),
            opponent_hand=list(hidden.opponent_hand),
            opponent_active=list(hidden.opponent_active),
            manual_coin=bool(manual_coin),
        )
        started = True
        root_observation = root.observation
        if _public_projection(root_observation) != _public_projection(raw_observation):
            raise SearchRootMismatch("root public projection differs from branch observation")
        try:
            branch_candidates = observation_complete_actions(raw_observation)
            root_candidates = observation_complete_actions(root_observation)
            branch_rows = observation_option_rows(raw_observation)
            root_rows = observation_option_rows(root_observation)
            branch_ids = {item.canonical_identity for item in branch_candidates.candidates}
            root_ids = {item.canonical_identity for item in root_candidates.candidates}
            if branch_ids != root_ids:
                raise SearchRootMismatch("root candidate identity set differs")
            branch_index = branch_candidates.candidate_index_for(branch_rows, candidate_action)
            root_index = root_candidates.candidate_index_for(root_rows, candidate_action)
            if branch_index != root_index:
                raise SearchRootMismatch("candidate index differs between branch and search root")
        except SearchRootMismatch:
            raise
        except Exception as exc:
            raise SearchRootMismatch(f"cannot validate root candidate identities: {exc}") from exc

        current_state = root
        action = [int(item) for item in candidate_action]
        current_state = api.search_step(current_state.searchId, action)
        api.search_release(root.searchId)
        root = None
        coin_event_index = 0
        for step_index in range(int(max_steps)):
            observation = current_state.observation
            result = _terminal(observation)
            if result is not None:
                api.search_release(current_state.searchId)
                current_state = None
                return _reward(result, replayed_root.policy_seat)
            if _get(observation, "select", None) is None:
                raise SearchRuntimeError("search continuation has no terminal result or select")
            if _int(_get(_get(observation, "select"), "context")) == 46:
                next_action = _coin_action(observation, branch_group_id, rollout_index, coin_event_index)
                coin_event_index += 1
            else:
                agent_view = _search_observation_for_agent(observation)
                policy = (
                    replayed_root.source_policy
                    if _player(observation) == replayed_root.policy_seat
                    else replayed_root.opponent_policy
                )
                next_action = [int(item) for item in policy(agent_view)]
            previous_id = current_state.searchId
            next_state = api.search_step(previous_id, next_action)
            api.search_release(previous_id)
            current_state = next_state
        raise SearchRuntimeError("maximum search steps reached")
    except SearchRuntimeError:
        raise
    except Exception as exc:
        raise SearchRuntimeError(f"search API error: {type(exc).__name__}: {exc}") from exc
    finally:
        if current_state is not None:
            try:
                api.search_release(current_state.searchId)
            except Exception:
                pass
        if root is not None:
            try:
                api.search_release(root.searchId)
            except Exception:
                pass
        if started:
            try:
                api.search_end()
            except Exception:
                pass


__all__ = [
    "PrefixReplayMismatch",
    "ReplayedRoot",
    "SearchRootMismatch",
    "SearchRuntimeError",
    "check_api_surface",
    "replay_to_branch_root",
    "run_candidate_search",
]
