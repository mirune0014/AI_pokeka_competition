"""Paired information-set rollout runner for frozen Gold oracle states.

The persisted artifact contains semantic action identifiers only. Raw engine
option coordinates exist only while a replay state is reconstructed and a
Search API branch is executed.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import blake2b
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
from typing import Any, Mapping, Sequence

from .belief import SearchGuess, sample_search_guess
from .canonical_actions import (
    CanonicalOption,
    CanonicalPromptAction,
    canonicalize_prompt_action,
    resolve_prompt_action,
)
from .gold_oracle_states import (
    SCHEMA_VERSION as GOLD_ORACLE_STATES_SCHEMA_VERSION,
    canonical_sha256,
    file_sha256,
    verify_gold_oracle_states,
)
from .gold_upper_tier_states import (
    LEGACY_SCHEMA_VERSION as GOLD_UPPER_TIER_STATES_LEGACY_SCHEMA_VERSION,
    SCHEMA_VERSION as GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
    assert_no_gold_candidate_tags,
    verify_gold_upper_tier_states,
)
from .gold_oracle_statistics import summarize_direct_comparisons, summarize_gold_oracle
from .gold_candidate_selection import verify_candidate_selection
from .probe_search import score_options
from .replay_records import ReplayDecisionRecord
from .replay_reconstruction import iter_replay_decisions
from .rollout_expert import choose_with_rollout
from .teacher_statistics import summarize_teacher_batches


SCHEMA_VERSION = "gold_oracle_rollout.v1"
SHARD_SCHEMA_VERSION = "gold_oracle_rollout_shard.v1"
REPORT_SCHEMA_VERSION = "gold_oracle_rollout_report.v1"
_CANDIDATE_SETS = (
    "baseline", "rule_top3", "rule_topK", "rule_diverse", "rule_plus_gold",
)
_OPPONENT_POPULATION_MODES = (
    "path_distinct_v1", "structural_unique_v1",
)
_ROLLOUT_SEED_MODES = (
    "policy_id_v1", "common_stream_v1", "common_population_v2",
)
_STATE_CORPUS_SCHEMAS = frozenset((
    GOLD_ORACLE_STATES_SCHEMA_VERSION,
    GOLD_UPPER_TIER_STATES_LEGACY_SCHEMA_VERSION,
    GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
))


def stable_seed(*parts: Any) -> int:
    payload = json.dumps(
        parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return int.from_bytes(blake2b(payload, digest_size=8).digest(), "big")


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _resolve_inside(path: str | Path, workspace: Path) -> Path:
    value = Path(path)
    resolved = (value if value.is_absolute() else workspace / value).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _portable_relative(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace.resolve())).replace("\\", "/")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("could not read %s" % path) from error
    output = []
    for number, line in enumerate(lines, 1):
        if not line:
            raise ValueError("blank JSONL row in %s" % path)
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid JSONL row %d in %s" % (number, path)) from error
        if not isinstance(value, dict):
            raise ValueError("JSONL rows must be objects")
        output.append(value)
    return output


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain an object" % path)
    return value


def verify_state_corpus(corpus_dir: Path, workspace: Path) -> dict[str, Any]:
    """Dispatch to a schema-specific, fail-closed state-corpus verifier."""
    corpus = _resolve_inside(corpus_dir, workspace)
    schema = _read_json_object(corpus / "manifest.json").get("schema_version")
    if schema == GOLD_ORACLE_STATES_SCHEMA_VERSION:
        verified = verify_gold_oracle_states(
            corpus, workspace, allow_implementation_drift=True,
        )
    elif schema in {
        GOLD_UPPER_TIER_STATES_LEGACY_SCHEMA_VERSION,
        GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
    }:
        verified = verify_gold_upper_tier_states(corpus, workspace)
    else:
        raise ValueError("unsupported state corpus schema: %s" % schema)
    result = dict(verified)
    result["schema_version"] = schema
    result["output_dir"] = str(corpus)
    return result


def canonical_action_from_dict(value: Mapping[str, Any]) -> CanonicalPromptAction:
    expected = {"selection_context", "minimum_count", "maximum_count", "selections"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("canonical action has an invalid schema")
    selections = value["selections"]
    allowed = set(CanonicalOption.__dataclass_fields__)
    if not isinstance(selections, list):
        raise ValueError("canonical action selections must be a list")
    parsed = []
    for selection in selections:
        if not isinstance(selection, Mapping) or set(selection) != allowed:
            raise ValueError("canonical option has an invalid schema")
        parsed.append(CanonicalOption(**dict(selection)))
    action = CanonicalPromptAction(
        value["selection_context"], value["minimum_count"],
        value["maximum_count"], tuple(parsed),
    )
    if action.to_dict() != dict(value):
        raise ValueError("canonical action does not round trip")
    return action


def resolve_semantic_candidates(
    observation: Any, state: Mapping[str, Any], candidate_set: str,
) -> tuple[list[list[int]], dict[tuple[int, ...], str], str]:
    """Resolve one frozen semantic candidate set against current options."""
    if candidate_set not in _CANDIDATE_SETS:
        raise ValueError("unknown candidate set: %s" % candidate_set)
    identifiers = state["candidate_sets"][candidate_set]
    by_id = {candidate["semantic_id"]: candidate for candidate in state["candidates"]}
    raw_actions = []
    raw_to_semantic: dict[tuple[int, ...], str] = {}
    for identifier in identifiers:
        candidate = by_id.get(identifier)
        if candidate is None:
            raise ValueError("candidate set has a dangling semantic identifier")
        raw = sorted(resolve_prompt_action(
            observation, canonical_action_from_dict(candidate["canonical"]),
        ))
        resolved = canonicalize_prompt_action(observation, raw)
        if resolved.stable_id != identifier:
            raise ValueError("resolved action semantic identifier mismatch")
        key = tuple(raw)
        previous = raw_to_semantic.setdefault(key, identifier)
        if previous != identifier:
            raise ValueError("distinct semantic actions resolved to one raw action")
        raw_actions.append(raw)
    baseline_id = state["candidate_sets"]["baseline"][0]
    if baseline_id not in identifiers:
        raise ValueError("evaluated candidate set omits the baseline")
    return raw_actions, raw_to_semantic, baseline_id


def _guess_payload(guess: SearchGuess) -> dict[str, list[int]]:
    return {
        name: [int(card_id) for card_id in getattr(guess, name)]
        for name in SearchGuess.__dataclass_fields__
    }


def _guess_from_payload(value: Mapping[str, Sequence[int]]) -> SearchGuess:
    if set(value) != set(SearchGuess.__dataclass_fields__):
        raise ValueError("invalid SearchGuess payload")
    return SearchGuess(**{
        name: [int(card_id) for card_id in value[name]]
        for name in SearchGuess.__dataclass_fields__
    })


def sample_world_payloads(
    observation: Any,
    own_deck: Sequence[int],
    opponent_deck: Sequence[int],
    basic_pokemon_ids: set[int],
    *,
    count: int,
    seed_parts: Sequence[Any],
) -> list[dict[str, list[int]]]:
    if count < 1:
        raise ValueError("particle count must be positive")
    return [
        _guess_payload(sample_search_guess(
            observation, own_deck, opponent_deck,
            random.Random(stable_seed(*seed_parts, particle_index)),
            basic_pokemon_ids,
        ))
        for particle_index in range(count)
    ]


def _policy_descriptor(
    path: Path, workspace: Path, expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = _resolve_inside(path, workspace)
    main = resolved / "main.py"
    deck = resolved / "deck.csv"
    if not main.is_file() or not deck.is_file():
        raise ValueError("policy directory must contain main.py and deck.csv: %s" % path)
    descriptor = {
        "path": str(expected["path"]) if expected is not None else _portable_relative(resolved, workspace),
        "main_sha256": file_sha256(main),
        "deck_sha256": file_sha256(deck),
    }
    model_manifest = resolved / "gold_prompt_ranker_manifest.json"
    if model_manifest.is_file():
        model_binding = json.loads(model_manifest.read_text(encoding="ascii"))
        auxiliary = {
            "gold_prompt_ranker_manifest.json": file_sha256(model_manifest),
        }
        for key in ("checkpoint", "evaluation_report"):
            bound = _resolve_inside(resolved / str(model_binding[key]), workspace)
            try:
                relative = str(bound.relative_to(resolved)).replace("\\", "/")
            except ValueError as error:
                raise ValueError("policy model file escapes its directory") from error
            auxiliary[relative] = file_sha256(bound)
        for binding in model_binding.get("implementation", {}).values():
            bound = _resolve_inside(resolved / str(binding["snapshot"]), workspace)
            try:
                relative = str(bound.relative_to(resolved)).replace("\\", "/")
            except ValueError as error:
                raise ValueError("policy model snapshot escapes its directory") from error
            auxiliary[relative] = file_sha256(bound)
        descriptor["auxiliary_files_sha256"] = dict(sorted(auxiliary.items()))
    descriptor["policy_id"] = canonical_sha256(descriptor)
    return descriptor


def _effective_opponent_policies(
    descriptors: Sequence[Mapping[str, Any]], mode: str,
) -> list[dict[str, Any]]:
    """Return the population units used for equal-weight rollout averaging."""
    if mode not in _OPPONENT_POPULATION_MODES:
        raise ValueError("unknown opponent population mode")
    values = [dict(descriptor) for descriptor in descriptors]
    if mode == "path_distinct_v1":
        return values
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for descriptor in values:
        key = (
            str(descriptor["main_sha256"]),
            str(descriptor["deck_sha256"]),
            canonical_sha256(descriptor.get("auxiliary_files_sha256", {})),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(descriptor)
    return result


def _rollout_scenario_seed(
    config: Mapping[str, Any], state_id: str, batch_id: int,
    hypothesis_signature: str, policy: Mapping[str, Any],
    continuation: Mapping[str, Any],
) -> int:
    """Bind paired randomness independently from population weighting when requested."""
    mode = str(config.get("rollout_seed_mode", "policy_id_v1"))
    if mode == "policy_id_v1":
        return stable_seed(
            config["seed"], state_id, int(batch_id), hypothesis_signature,
            policy["policy_id"], continuation["policy_id"], "rollout",
        )
    if mode == "common_stream_v1":
        return stable_seed(
            config["seed"], state_id, int(batch_id), hypothesis_signature,
            continuation["policy_id"], 0, "rollout",
        )
    if mode == "common_population_v2":
        return stable_seed(
            config["seed"], state_id, int(batch_id), hypothesis_signature,
            0, 0, "rollout",
        )
    raise ValueError("unknown rollout seed mode")


def _engine_descriptor(
    path: Path, workspace: Path, expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = _resolve_inside(path, workspace)
    api = resolved / "cg" / "api.py"
    if not api.is_file():
        raise ValueError("engine directory has no cg/api.py")
    if expected is not None and "dll_sha256" in expected:
        dll = resolved / "cg" / "cg.dll"
        if not dll.is_file():
            raise ValueError("bound legacy engine has no cg/cg.dll")
        return {
            "path": str(expected["path"]),
            "api_sha256": file_sha256(api),
            "dll_sha256": file_sha256(dll),
        }
    if expected is not None and "binary_name" in expected:
        binary_name = str(expected["binary_name"])
    else:
        binary_name = {
            "Windows": "cg.dll",
            "Darwin": "libcg.dylib",
        }.get(platform.system(), "libcg.so")
    if binary_name not in {"cg.dll", "libcg.so", "libcg.dylib", "libcg-arm64.so"}:
        raise ValueError("unsupported engine binary binding: %s" % binary_name)
    binary = resolved / "cg" / binary_name
    if not binary.is_file():
        raise ValueError("engine directory has no cg/%s" % binary_name)
    python_files = {}
    for name in ("__init__.py", "api.py", "game.py", "sim.py", "utils.py"):
        source = resolved / "cg" / name
        if source.is_file():
            python_files[name] = file_sha256(source)
    path_value = str(expected["path"]) if expected is not None else _portable_relative(resolved, workspace)
    return {
        "path": path_value,
        "api_sha256": file_sha256(api),
        "binary_name": binary_name,
        "binary_sha256": file_sha256(binary),
        "python_files_sha256": python_files,
    }


def _implementation_paths(cli_path: Path, workspace: Path) -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    paths = (
        Path(__file__),
        cli_path,
        root / "rl_ptcg" / "rollout_expert.py",
        root / "rl_ptcg" / "belief.py",
        root / "rl_ptcg" / "canonical_actions.py",
        root / "rl_ptcg" / "replay_records.py",
        root / "rl_ptcg" / "replay_reconstruction.py",
        root / "rl_ptcg" / "teacher_statistics.py",
        root / "rl_ptcg" / "gold_oracle_statistics.py",
        root / "rl_ptcg" / "gold_oracle_states.py",
        root / "rl_ptcg" / "gold_upper_tier_states.py",
        root / "rl_ptcg" / "gold_candidate_selection.py",
        root / "rl_ptcg" / "probe_search.py",
        root / "tools" / "ptcg_common.py",
        root / "tools" / "build_gold_candidate_selection.py",
    )
    return sorted((_resolve_inside(path, workspace) for path in paths), key=str)


def _write_bytes_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(".%s.%d.tmp" % (path.name, os.getpid()))
    if temporary.exists():
        raise FileExistsError("temporary artifact already exists: %s" % temporary)
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            if path.read_bytes() != data:
                raise FileExistsError("refusing to replace non-identical artifact: %s" % path)
        else:
            os.replace(temporary, path)
        if path.read_bytes() != data:
            raise ValueError("atomic artifact write did not preserve bytes: %s" % path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_once(path: Path, value: Any) -> None:
    data = (json.dumps(
        value, sort_keys=True, ensure_ascii=True, indent=2,
    ) + "\n").encode("ascii")
    _write_bytes_once(path, data)


def snapshot_implementation(
    cli_path: Path, output_dir: Path, workspace: Path,
) -> dict[str, dict[str, str]]:
    result = {}
    for source in _implementation_paths(cli_path, workspace):
        source_relative = source.relative_to(workspace)
        snapshot = output_dir / "source_snapshot" / source_relative
        data = source.read_bytes()
        _write_bytes_once(snapshot, data)
        digest = file_sha256(source)
        if file_sha256(snapshot) != digest:
            raise ValueError("implementation snapshot hash mismatch")
        result[str(source_relative).replace("\\", "/")] = {
            "source_sha256": digest,
            "snapshot_path": _portable_relative(snapshot, workspace),
            "snapshot_sha256": digest,
        }
    return dict(sorted(result.items()))


def make_run_manifest(
    corpus_dir: Path,
    baseline_dir: Path,
    engine_dir: Path,
    opponent_policies: Mapping[str, Sequence[Path]],
    continuation_policies: Sequence[Path],
    state_ids: Sequence[str],
    *,
    batches: int,
    particles_per_scenario: int,
    max_rollout_steps: int,
    candidate_set: str,
    seed: str,
    bootstrap_repetitions: int,
    workspace: Path,
    implementation_bindings: Mapping[str, Mapping[str, str]],
    candidate_selection: Mapping[str, Any] | None,
    opponent_population_mode: str = "path_distinct_v1",
    rollout_seed_mode: str = "policy_id_v1",
) -> dict[str, Any]:
    if batches < 1 or particles_per_scenario < 1 or max_rollout_steps < 1:
        raise ValueError("batches, particles, and rollout steps must be positive")
    if candidate_selection is None and candidate_set not in _CANDIDATE_SETS:
        raise ValueError("unknown candidate set")
    if candidate_selection is not None:
        selection_states = candidate_selection.get("states")
        if not isinstance(selection_states, Mapping) or not set(state_ids) <= set(selection_states):
            raise ValueError("explicit candidate selection does not cover every run state")
    if opponent_population_mode not in _OPPONENT_POPULATION_MODES:
        raise ValueError("unknown opponent population mode")
    if rollout_seed_mode not in _ROLLOUT_SEED_MODES:
        raise ValueError("unknown rollout seed mode")
    corpus = _resolve_inside(corpus_dir, workspace)
    baseline = _policy_descriptor(baseline_dir, workspace)
    continuations = []
    seen = set()
    for path in [baseline_dir, *continuation_policies]:
        descriptor = _policy_descriptor(path, workspace)
        if descriptor["policy_id"] not in seen:
            continuations.append(descriptor)
            seen.add(descriptor["policy_id"])
    configured_policies = {
        archetype: [_policy_descriptor(path, workspace) for path in paths]
        for archetype, paths in sorted(opponent_policies.items())
    }
    policies = {
        archetype: _effective_opponent_policies(values, opponent_population_mode)
        for archetype, values in configured_policies.items()
    }
    if not policies or any(not values for values in policies.values()):
        raise ValueError("every configured archetype needs an opponent policy")
    corpus_schema = _read_json_object(corpus / "manifest.json").get("schema_version")
    if corpus_schema not in _STATE_CORPUS_SCHEMAS:
        raise ValueError("unsupported state corpus schema: %s" % corpus_schema)
    result = {
        "schema_version": SCHEMA_VERSION,
        "corpus": {
            "path": _portable_relative(corpus, workspace),
            "schema_version": corpus_schema,
            "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
            "states_sha256": file_sha256(corpus / "states.jsonl"),
            "manifest_sha256": file_sha256(corpus / "manifest.json"),
        },
        "baseline": baseline,
        "engine": _engine_descriptor(engine_dir, workspace),
        "opponent_policies": policies,
        "opponent_population_audit": {
            archetype: {
                "configured_policy_ids": [item["policy_id"] for item in configured_policies[archetype]],
                "effective_policy_ids": [item["policy_id"] for item in policies[archetype]],
                "configured_count": len(configured_policies[archetype]),
                "effective_count": len(policies[archetype]),
            }
            for archetype in sorted(policies)
        },
        "continuation_policies": continuations,
        "state_ids": sorted(str(identifier) for identifier in state_ids),
        "batch_ids": list(range(batches)),
        "config": {
            "particles_per_scenario": int(particles_per_scenario),
            "max_rollout_steps": int(max_rollout_steps),
            "candidate_mode": "explicit_selection" if candidate_selection is not None else "named_set",
            "candidate_set": "explicit_selection" if candidate_selection is not None else candidate_set,
            "candidate_selection": None if candidate_selection is None else dict(candidate_selection),
            "seed": str(seed),
            "bootstrap_repetitions": int(bootstrap_repetitions),
            "opponent_population_mode": opponent_population_mode,
            "rollout_seed_mode": rollout_seed_mode,
        },
        "implementation": {
            str(path): dict(binding)
            for path, binding in sorted(implementation_bindings.items())
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
        },
    }
    result["manifest_sha256"] = _self_hash(result)
    return result


def _load_tools():
    root = Path(__file__).resolve().parents[1]
    tools_dir = root / "tools"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from tools.ptcg_common import dataclass_to_dict, load_agent, pushd

    class AgentChooser:
        def __init__(self, agent: Any):
            self.agent = agent

        def choose_options(self, observation: Any) -> list[int]:
            chooser = getattr(self.agent.module, "choose_options", None)
            if not callable(chooser):
                return self.agent(dataclass_to_dict(observation))
            with pushd(self.agent.agent_dir):
                return chooser(observation)

    return load_agent, AgentChooser


def validate_reconstruction_provenance(
    state: Mapping[str, Any], recorded_action_id: str,
) -> None:
    """Validate corpus semantics without promoting provenance-only actions."""
    schema = state.get("schema_version")
    candidates = state.get("candidates")
    candidate_sets = state.get("candidate_sets")
    if not isinstance(candidates, list) or not isinstance(candidate_sets, Mapping):
        raise ValueError("state candidate schema mismatch")
    if schema == GOLD_ORACLE_STATES_SCHEMA_VERSION:
        gold_ids = {
            candidate["semantic_id"]
            for candidate in candidates
            if "gold" in candidate.get("source_tags", ())
        }
        if recorded_action_id not in gold_ids:
            raise ValueError("recorded Gold action does not match frozen candidate")
        return
    if schema in {
        GOLD_UPPER_TIER_STATES_LEGACY_SCHEMA_VERSION,
        GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
    }:
        assert_no_gold_candidate_tags(candidates)
        metadata = state.get("current_metadata")
        if (
            state.get("gold_incremental") is not False
            or candidate_sets.get("rule_plus_gold") != candidate_sets.get("rule_diverse")
            or not isinstance(metadata, Mapping)
            or metadata.get("corpus_role") != "upper_tier_state_distribution"
            or metadata.get("recorded_action_role") != "provenance_only"
        ):
            raise ValueError("upper-tier corpus provenance declarations mismatch")
        return
    raise ValueError("unsupported state corpus schema: %s" % schema)


def reconstruct_rollout_input(
    state: Mapping[str, Any], baseline_dir: Path, workspace: Path, module_tag: str,
) -> tuple[Any, list[float], list[int], list[list[int]], dict[tuple[int, ...], str], str]:
    """Replay the frozen rule module through the target state and verify IDs."""
    load_agent, _chooser = _load_tools()
    replay_path = _resolve_inside(state["source_replay_path"], workspace)
    if file_sha256(replay_path) != state["replay_sha256"]:
        raise ValueError("source replay hash changed")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    agent = load_agent(baseline_dir, module_tag)
    target_step = int(state["replay_step"])
    for decision in iter_replay_decisions(replay, seats=[int(state["acting_seat"])]):
        baseline_action = agent(dict(decision.observation))
        if decision.replay_step != target_step:
            continue
        reconstructed = ReplayDecisionRecord.from_observation(
            decision.observation,
            decision.raw_action,
            episode_id=state["episode_id"],
            submission_id=state["submission_id"],
            style_id=state["style_id"],
            decision_step=0,
            replay_step=target_step,
            acting_seat=state["acting_seat"],
            own_archetype=state["current_metadata"]["own_archetype"],
            opponent_archetype=state["current_metadata"]["opponent_archetype"],
            public_history=decision.public_history,
            private_action_history=decision.private_action_history,
        )
        if (
            reconstructed.state_id != state["state_id"]
            or reconstructed.decision_id != state["decision_id"]
        ):
            raise ValueError("target replay state no longer reconstructs to frozen IDs")
        recorded_action_id = canonicalize_prompt_action(
            decision.observation, decision.raw_action,
        ).stable_id
        validate_reconstruction_provenance(state, recorded_action_id)
        scores = score_options(agent, dict(decision.observation))[1]
        raw_actions, raw_to_semantic, baseline_id = resolve_semantic_candidates(
            decision.observation, state, "rule_plus_gold",
        )
        baseline_semantic = canonicalize_prompt_action(
            decision.observation, baseline_action,
        ).stable_id
        if baseline_semantic != baseline_id:
            raise ValueError("frozen baseline action changed")
        return (
            decision.observation, list(scores), list(baseline_action), raw_actions,
            raw_to_semantic, baseline_id,
        )
    raise ValueError("target replay step was not reconstructed")


def semanticize_scenario_values(
    values: Sequence[Mapping[str, Any]],
    raw_to_semantic: Mapping[tuple[int, ...], str],
    *,
    state: Mapping[str, Any],
    batch_id: int,
    hypothesis: Mapping[str, Any],
    policy_index: int,
    policy_id: str,
    continuation_index: int,
    continuation_id: str,
    scenario_weight: float,
) -> list[dict[str, Any]]:
    top3 = set(state["candidate_sets"]["rule_top3"])
    baseline_id = state["candidate_sets"]["baseline"][0]
    rows = []
    for value in values:
        raw = value.get("action")
        if not isinstance(raw, list) or not all(isinstance(index, int) for index in raw):
            raise ValueError("rollout scenario row has no raw action")
        semantic_id = raw_to_semantic.get(tuple(sorted(raw)))
        if semantic_id is None:
            raise ValueError("rollout returned an action outside the frozen candidate set")
        utility = float(value["terminal_utility"])
        if utility not in (-1.0, 0.0, 1.0):
            raise ValueError("terminal utility must be -1, 0, or 1")
        rows.append({
            "state_id": state["state_id"],
            "decision_id": state["decision_id"],
            "episode_id": state["episode_id"],
            "batch_id": int(batch_id),
            "baseline_action": baseline_id,
            "particle_index": int(value["particle_index"]),
            # The legacy statistics field names end in "index", but their
            # values are stable content/path policy IDs, never list ordinals.
            "opponent_policy_index": policy_id,
            "continuation_policy_index": continuation_id,
            "hypothesis_signature": str(hypothesis["signature"]),
            "hypothesis_kind": str(hypothesis["kind"]),
            "posterior_mass": float(hypothesis["posterior_mass"]),
            "scenario_weight": float(scenario_weight),
            "hidden_world_id": str(value["hidden_world_id"]),
            "action": semantic_id,
            "outside_rule_top3": semantic_id not in top3,
            "terminal_utility": utility,
        })
    return rows


def _row_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row["hypothesis_signature"], row["opponent_policy_index"],
        row["continuation_policy_index"], row["particle_index"], row["action"],
    )


def assert_order_parity(
    forward: Sequence[Mapping[str, Any]], reverse: Sequence[Mapping[str, Any]],
) -> None:
    left = sorted((dict(row) for row in forward), key=_row_sort_key)
    right = sorted((dict(row) for row in reverse), key=_row_sort_key)
    if left != right:
        if len(left) != len(right):
            detail = "row_count=%d/%d" % (len(left), len(right))
        else:
            index = next(
                (number for number, pair in enumerate(zip(left, right)) if pair[0] != pair[1]),
                -1,
            )
            differing = sorted(
                key for key in set(left[index]) | set(right[index])
                if left[index].get(key) != right[index].get(key)
            ) if index >= 0 else []
            detail = "first_row=%d fields=%s" % (index, ",".join(differing))
        raise ValueError("forward/reverse root branch order parity failed: %s" % detail)


def _seed_agent_randomness(agents: Sequence[Any], seed: int) -> None:
    """Reset shared and module-local RNGs after fresh policy imports."""
    random.seed(seed)
    for agent in agents:
        module_random = getattr(agent.module, "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)


def _run_order(
    state: Mapping[str, Any],
    observation: Any,
    scores: Sequence[float],
    baseline_action: Sequence[int],
    raw_actions: Sequence[Sequence[int]],
    raw_to_semantic: Mapping[tuple[int, ...], str],
    hypothesis: Mapping[str, Any],
    policy: Mapping[str, Any],
    continuation: Mapping[str, Any],
    world_payloads: Sequence[Mapping[str, Sequence[int]]],
    *,
    batch_id: int,
    policy_index: int,
    continuation_index: int,
    scenario_weight: float,
    branch_order: str,
    rollout_seed: int,
    max_rollout_steps: int,
    basic_pokemon_ids: set[int],
    workspace: Path,
) -> list[dict[str, Any]]:
    load_agent, AgentChooser = _load_tools()
    tag = "%s_%s_%s_%d_%d_%s" % (
        state["state_id"][:12], hypothesis["signature"][:12],
        policy["policy_id"][:12], batch_id, continuation_index, branch_order,
    )
    baseline_path = _resolve_inside(
        state["runner_baseline_path"], workspace,
    ) if "runner_baseline_path" in state else None
    if baseline_path is None:
        raise ValueError("runner baseline path is missing")
    seat = int(state["acting_seat"])

    def fresh_modules(suffix: str, module_seed: int) -> dict[int, Any]:
        opponent = load_agent(
            _resolve_inside(policy["path"], workspace),
            "gold_opp_%s_%s" % (tag, suffix),
        )
        continuation_agent = load_agent(
            _resolve_inside(continuation["path"], workspace),
            "gold_cont_%s_%s" % (tag, suffix),
        )
        _seed_agent_randomness((opponent, continuation_agent), module_seed)
        return {
            seat: AgentChooser(continuation_agent),
            1 - seat: AgentChooser(opponent),
        }

    initial = fresh_modules("initial", rollout_seed)

    def module_factory(
        determination_index: int, _policy_index: int,
        _continuation_index: int, action: Sequence[int],
    ) -> Mapping[int, Any]:
        action_digest = blake2b(
            json.dumps(sorted(int(index) for index in action)).encode("ascii"),
            digest_size=6,
        ).hexdigest()
        suffix = "d%d_a%s" % (determination_index, action_digest)
        return fresh_modules(
            suffix, stable_seed(rollout_seed, determination_index, "policy"),
        )

    decision = choose_with_rollout(
        observation,
        initial,
        state["own_deck"]["decklist"],
        hypothesis["decklist"],
        scores,
        baseline_action,
        random.Random(rollout_seed),
        determinizations=len(world_payloads),
        max_steps=max_rollout_steps,
        risk_penalty=0.0,
        improvement_margin=0.0,
        confidence_z=0.0,
        min_successful_determinizations=len(world_payloads),
        basic_pokemon_ids=basic_pokemon_ids,
        opponent_policy_modules=[initial[1 - seat]],
        your_policy_modules=[initial[seat]],
        hypothesis_strategy="first",
        search_guesses=[_guess_from_payload(deepcopy(value)) for value in world_payloads],
        return_scenario_values=True,
        explicit_candidate_actions=raw_actions,
        branch_order=branch_order,
        fresh_root_per_branch=True,
        rollout_modules_factory=module_factory,
        seed_native_search=True,
    )
    if (
        decision.errors
        or decision.determinizations != len(world_payloads)
        or decision.scenario_errors
    ):
        raise RuntimeError(
            "rollout scenario failed: determinizations=%s errors=%s details=%s"
            % (decision.determinizations, decision.errors, decision.scenario_errors)
        )
    expected = len(world_payloads) * len(raw_actions)
    if len(decision.scenario_values or []) != expected:
        raise RuntimeError("rollout scenario row count mismatch")
    return semanticize_scenario_values(
        decision.scenario_values or [], raw_to_semantic,
        state=state, batch_id=batch_id, hypothesis=hypothesis,
        policy_index=policy_index, policy_id=policy["policy_id"],
        continuation_index=continuation_index,
        continuation_id=continuation["policy_id"],
        scenario_weight=scenario_weight,
    )


def run_state_batch(
    state: Mapping[str, Any],
    manifest: Mapping[str, Any],
    batch_id: int,
    basic_pokemon_ids: set[int],
    workspace: Path,
) -> dict[str, Any]:
    config = manifest["config"]
    baseline_path = manifest["baseline"]["path"]
    working_state = dict(state)
    working_state["runner_baseline_path"] = baseline_path
    observation, scores, baseline_action, all_raw_actions, raw_to_semantic, baseline_id = reconstruct_rollout_input(
        working_state,
        _resolve_inside(baseline_path, workspace),
        workspace,
        "gold_reconstruct_%s_%d" % (state["state_id"][:16], batch_id),
    )
    if config["candidate_mode"] == "explicit_selection":
        selection_entry = config["candidate_selection"]["states"][state["state_id"]]
        selected_ids = list(selection_entry["candidate_ids"])
    else:
        selection_entry = None
        selected_ids = state["candidate_sets"][config["candidate_set"]]
    selected_raw = [
        action for action in all_raw_actions
        if raw_to_semantic[tuple(sorted(action))] in set(selected_ids)
    ]
    if len(selected_raw) != len(selected_ids):
        raise ValueError("selected candidate set did not resolve exactly")
    archetype = state["belief"]["archetype"]
    policies = manifest["opponent_policies"].get(archetype)
    if not policies:
        raise ValueError("no opponent policy population for %s" % archetype)
    continuations = manifest["continuation_policies"]
    particles = int(config["particles_per_scenario"])
    rows = []
    scenario_count = 0
    for hypothesis in state["belief"]["hypotheses"]:
        world_payloads = sample_world_payloads(
            observation,
            state["own_deck"]["decklist"],
            hypothesis["decklist"],
            basic_pokemon_ids,
            count=particles,
            seed_parts=(config["seed"], state["state_id"], batch_id, hypothesis["signature"], "world"),
        )
        weight = float(hypothesis["posterior_mass"]) / (len(policies) * len(continuations))
        for policy_index, policy in enumerate(policies):
            for continuation_index, continuation in enumerate(continuations):
                scenario_seed = _rollout_scenario_seed(
                    config, state["state_id"], batch_id,
                    hypothesis["signature"], policy, continuation,
                )
                forward = _run_order(
                    working_state, observation, scores, baseline_action, selected_raw,
                    raw_to_semantic, hypothesis, policy, continuation, world_payloads,
                    batch_id=batch_id, policy_index=policy_index,
                    continuation_index=continuation_index, scenario_weight=weight,
                    branch_order="forward", rollout_seed=scenario_seed,
                    max_rollout_steps=int(config["max_rollout_steps"]),
                    basic_pokemon_ids=basic_pokemon_ids, workspace=workspace,
                )
                reverse = _run_order(
                    working_state, observation, scores, baseline_action, selected_raw,
                    raw_to_semantic, hypothesis, policy, continuation, world_payloads,
                    batch_id=batch_id, policy_index=policy_index,
                    continuation_index=continuation_index, scenario_weight=weight,
                    branch_order="reverse", rollout_seed=scenario_seed,
                    max_rollout_steps=int(config["max_rollout_steps"]),
                    basic_pokemon_ids=basic_pokemon_ids, workspace=workspace,
                )
                assert_order_parity(forward, reverse)
                rows.extend(forward)
                scenario_count += 1
    rows.sort(key=_row_sort_key)
    payload = {
        "schema_version": SHARD_SCHEMA_VERSION,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "state_id": state["state_id"],
        "decision_id": state["decision_id"],
        "episode_id": state["episode_id"],
        "batch_id": int(batch_id),
        "candidate_set": config["candidate_set"],
        "candidate_ids": list(selected_ids),
        "candidate_memberships": {
            identifier: (
                [name for name in _CANDIDATE_SETS if identifier in state["candidate_sets"][name]]
                + ([] if selection_entry is None else [
                    role for role, key in (
                        ("screen_baseline", "baseline_action"),
                        ("screen_rule_comparator", "rule_comparator_action"),
                        ("screen_gold", "gold_action"),
                    ) if selection_entry[key] == identifier
                ])
            )
            for identifier in selected_ids
        },
        "baseline_action": baseline_id,
        "scenario_count": scenario_count,
        "particles_per_scenario": particles,
        "forward_reverse_parity": True,
        "rows_sha256": canonical_sha256(rows),
        "rows": rows,
    }
    payload["manifest_sha256"] = _self_hash(payload)
    return payload


def _semantic_only(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered.startswith("raw") or lowered in {"observation", "raw_action", "option_indices"}:
                raise ValueError("raw engine coordinate leaked into artifact at %s" % ".".join(path + (str(key),)))
            _semantic_only(item, path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _semantic_only(item, path + (str(index),))


def verify_shard(
    shard: Mapping[str, Any], state: Mapping[str, Any], manifest: Mapping[str, Any],
) -> None:
    if shard.get("schema_version") != SHARD_SCHEMA_VERSION or shard.get("manifest_sha256") != _self_hash(shard):
        raise ValueError("rollout shard self-hash mismatch")
    if shard.get("run_manifest_sha256") != manifest["manifest_sha256"]:
        raise ValueError("rollout shard uses a different run manifest")
    if (
        shard.get("state_id") != state["state_id"]
        or shard.get("decision_id") != state["decision_id"]
        or shard.get("episode_id") != state["episode_id"]
        or shard.get("candidate_set") != manifest["config"]["candidate_set"]
    ):
        raise ValueError("rollout shard state binding mismatch")
    config = manifest["config"]
    if config["candidate_mode"] == "explicit_selection":
        candidates = config["candidate_selection"]["states"][state["state_id"]]["candidate_ids"]
    else:
        candidates = state["candidate_sets"][config["candidate_set"]]
    if shard.get("candidate_ids") != candidates:
        raise ValueError("rollout shard candidate set mismatch")
    if not shard.get("forward_reverse_parity"):
        raise ValueError("rollout shard did not pass order parity")
    rows = shard.get("rows")
    if not isinstance(rows, list) or shard.get("rows_sha256") != canonical_sha256(rows):
        raise ValueError("rollout shard row hash mismatch")
    _semantic_only(shard)
    expected_actions = set(candidates)
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("action"), str):
            raise ValueError("rollout rows must use semantic action IDs")
        if row["action"] not in expected_actions or row.get("baseline_action") != candidates[0]:
            raise ValueError("rollout row action is outside the frozen set")
        key = (
            row["hypothesis_signature"], row["opponent_policy_index"],
            row["continuation_policy_index"], row["particle_index"],
            row["hidden_world_id"],
        )
        grouped[key].append(row)
    if not grouped or any({row["action"] for row in values} != expected_actions for values in grouped.values()):
        raise ValueError("rollout shard is not a balanced paired action design")
    particles = int(manifest["config"]["particles_per_scenario"])
    scenario_particles: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    world_reuse: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    unique_weights: dict[tuple[Any, ...], float] = {}
    for row in rows:
        scenario = (
            row["hypothesis_signature"], row["opponent_policy_index"],
            row["continuation_policy_index"],
        )
        scenario_particles[scenario].add(int(row["particle_index"]))
        world_reuse[(row["hypothesis_signature"], row["particle_index"])].add(row["hidden_world_id"])
        unique_weights.setdefault(scenario, float(row["scenario_weight"]))
        if not math.isclose(unique_weights[scenario], float(row["scenario_weight"]), abs_tol=1e-12):
            raise ValueError("scenario weight changed inside one stratum")
    if any(values != set(range(particles)) for values in scenario_particles.values()):
        raise ValueError("scenario particle support is incomplete")
    if any(len(values) != 1 for values in world_reuse.values()):
        raise ValueError("hidden world was not reused across policy scenarios")
    if not math.isclose(sum(unique_weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("scenario weights do not sum to one")


def _weighted_candidate_set_report(
    rows: Sequence[Mapping[str, Any]], states: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["state_id"]), int(row["batch_id"]))].append(row)
    units = []
    for (state_id, batch_id), values in sorted(grouped.items()):
        weighted_sum: dict[str, float] = defaultdict(float)
        weight_sum: dict[str, float] = defaultdict(float)
        for row in values:
            weight = float(row["scenario_weight"])
            action = str(row["action"])
            weighted_sum[action] += weight * float(row["terminal_utility"])
            weight_sum[action] += weight
        means = {action: weighted_sum[action] / weight_sum[action] for action in weighted_sum}
        state = states[state_id]
        baseline = state["candidate_sets"]["baseline"][0]
        set_values = {
            name: max(means[action] for action in identifiers)
            for name in _CANDIDATE_SETS
            for identifiers in [state["candidate_sets"][name]]
            if set(identifiers) <= set(means)
        }
        gap = (
            set_values["rule_plus_gold"] - set_values["rule_diverse"]
            if {"rule_plus_gold", "rule_diverse"} <= set(set_values)
            else None
        )
        units.append({
            "state_id": state_id,
            "batch_id": batch_id,
            "episode_id": state["episode_id"],
            "baseline_value": means[baseline],
            "candidate_set_values": set_values,
            "rule_plus_gold_gap_vs_rule_diverse": gap,
        })
    gaps = [
        unit["rule_plus_gold_gap_vs_rule_diverse"] for unit in units
        if unit["rule_plus_gold_gap_vs_rule_diverse"] is not None
    ]
    return {
        "unit_count": len(units),
        "mean_rule_plus_gold_gap_vs_rule_diverse": (
            sum(gaps) / len(gaps) if gaps else None
        ),
        "gap_unit_count": len(gaps),
        "positive_gap_units": sum(value > 0 for value in gaps),
        "per_state_batch": units,
    }


def make_report(
    shards: Sequence[Mapping[str, Any]],
    states: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [row for shard in shards for row in shard["rows"]]
    statistics = summarize_teacher_batches(
        rows,
        bootstrap_repetitions=int(manifest["config"]["bootstrap_repetitions"]),
        bootstrap_seed=stable_seed(manifest["config"]["seed"], "bootstrap"),
    )
    posterior_statistics = summarize_gold_oracle(
        rows,
        states,
        bootstrap_repetitions=int(manifest["config"]["bootstrap_repetitions"]),
        bootstrap_seed=stable_seed(manifest["config"]["seed"], "posterior-bootstrap"),
    )
    direct_comparisons = None
    selection = manifest["config"].get("candidate_selection")
    if selection is not None:
        comparisons = {
            state_id: {
                "reference_action": entry["rule_comparator_action"],
                "candidate_action": entry["gold_action"],
            }
            for state_id, entry in selection["states"].items()
        }
        direct_comparisons = summarize_direct_comparisons(
            rows,
            states,
            comparisons,
            bootstrap_repetitions=int(manifest["config"]["bootstrap_repetitions"]),
            bootstrap_seed=stable_seed(manifest["config"]["seed"], "direct-bootstrap"),
        )
    result = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shard_count": len(shards),
        "row_count": len(rows),
        "teacher_statistics_unweighted": statistics,
        "posterior_weighted_teacher_statistics": posterior_statistics,
        "direct_gold_upper_bound_statistics": direct_comparisons,
        "posterior_weighted_candidate_sets": _weighted_candidate_set_report(rows, states),
    }
    result["manifest_sha256"] = _self_hash(result)
    return result


def collect_rollout_shards(
    output: Path,
    states: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[tuple[str, int]]]:
    """Verify every present shard and return deterministic missing work."""
    shards: list[dict[str, Any]] = []
    missing: list[tuple[str, int]] = []
    for state_id in manifest["state_ids"]:
        state = states.get(state_id)
        if state is None:
            raise ValueError("run manifest state is absent from corpus")
        for batch_id in manifest["batch_ids"]:
            path = output / "shards" / state_id / ("batch_%03d.json" % batch_id)
            if not path.is_file():
                missing.append((state_id, int(batch_id)))
                continue
            try:
                shard = json.loads(path.read_text(encoding="ascii"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("invalid rollout shard: %s" % path) from error
            verify_shard(shard, state, manifest)
            shards.append(shard)
    return shards, missing


def run_oracle(
    corpus_dir: Path,
    baseline_dir: Path,
    engine_dir: Path,
    output_dir: Path,
    opponent_policies: Mapping[str, Sequence[Path]],
    continuation_policies: Sequence[Path],
    *,
    state_ids: Sequence[str] | None,
    batches: int,
    particles_per_scenario: int,
    max_rollout_steps: int,
    candidate_set: str,
    seed: str,
    bootstrap_repetitions: int,
    workspace_root: Path,
    cli_path: Path,
    candidate_selection_path: Path | None = None,
    max_new_shards: int | None = None,
    opponent_population_mode: str = "path_distinct_v1",
    rollout_seed_mode: str = "policy_id_v1",
) -> dict[str, Any]:
    if max_new_shards is not None and max_new_shards < 1:
        raise ValueError("max_new_shards must be positive when provided")
    workspace = workspace_root.resolve()
    verified = verify_state_corpus(corpus_dir, workspace)
    corpus = _resolve_inside(verified["output_dir"], workspace)
    available = {state["state_id"]: state for state in _read_jsonl(corpus / "states.jsonl")}
    selection_config = None
    if candidate_selection_path is not None:
        verified_selection = verify_candidate_selection(candidate_selection_path, workspace)
        selection_payload = verified_selection["payload"]
        selection_config = {
            "path": _portable_relative(_resolve_inside(candidate_selection_path, workspace), workspace),
            "file_sha256": file_sha256(_resolve_inside(candidate_selection_path, workspace)),
            "manifest_sha256": selection_payload["manifest_sha256"],
            "mode": selection_payload["mode"],
            "states": selection_payload["states"],
        }
        default_states = sorted(selection_payload["states"])
    else:
        default_states = sorted(available)
    selected = sorted(state_ids or default_states)
    if len(selected) != len(set(selected)) or not set(selected) <= set(available):
        raise ValueError("selected state IDs are duplicate or absent from corpus")
    output = _resolve_inside(output_dir, workspace)
    implementation = snapshot_implementation(cli_path, output, workspace)
    manifest = make_run_manifest(
        corpus, baseline_dir, engine_dir, opponent_policies, continuation_policies,
        selected, batches=batches, particles_per_scenario=particles_per_scenario,
        max_rollout_steps=max_rollout_steps, candidate_set=candidate_set, seed=seed,
        bootstrap_repetitions=bootstrap_repetitions, workspace=workspace,
        implementation_bindings=implementation, candidate_selection=selection_config,
        opponent_population_mode=opponent_population_mode,
        rollout_seed_mode=rollout_seed_mode,
    )
    _write_json_once(output / "run_manifest.json", manifest)
    shards, missing = collect_rollout_shards(output, available, manifest)
    work = missing if max_new_shards is None else missing[:max_new_shards]
    if work:
        from tools.ptcg_common import ensure_engine_on_path
        ensure_engine_on_path(_resolve_inside(engine_dir, workspace))
        from cg.api import all_card_data
        basic_ids = {int(card.cardId) for card in all_card_data() if card.basic}
        for state_id, batch_id in work:
            state = available[state_id]
            shard = run_state_batch(state, manifest, batch_id, basic_ids, workspace)
            verify_shard(shard, state, manifest)
            shard_path = output / "shards" / state_id / ("batch_%03d.json" % batch_id)
            _write_json_once(shard_path, shard)
    shards, missing = collect_rollout_shards(output, available, manifest)
    complete = not missing
    report = None
    report_path = output / "report.json"
    if complete:
        report = make_report(shards, available, manifest)
        _write_json_once(report_path, report)
    elif report_path.exists():
        raise ValueError("incomplete rollout output unexpectedly contains a report")
    return {
        "complete": complete,
        "states": len(selected),
        "batches": batches,
        "expected_shards": len(selected) * batches,
        "shards": len(shards),
        "new_shards": len(work),
        "remaining_shards": len(missing),
        "next_missing_shard": None if not missing else {
            "state_id": missing[0][0], "batch_id": missing[0][1],
        },
        "rows": sum(len(shard["rows"]) for shard in shards),
        "run_manifest_sha256": manifest["manifest_sha256"],
        "report_manifest_sha256": None if report is None else report["manifest_sha256"],
        "output_dir": str(output),
    }


def verify_oracle_output(
    output_dir: Path, workspace_root: Path, *, allow_incomplete: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    output = _resolve_inside(output_dir, workspace)
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="ascii"))
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("manifest_sha256") != _self_hash(manifest):
        raise ValueError("run manifest self-hash mismatch")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, Mapping) or set(runtime) != {"python", "platform"}:
        raise ValueError("run manifest runtime binding mismatch")
    current_runtime = {"python": sys.version, "platform": platform.platform()}
    runtime_drift = sorted(
        name for name in current_runtime if current_runtime[name] != runtime[name]
    )
    corpus = _resolve_inside(manifest["corpus"]["path"], workspace)
    verified_corpus = verify_state_corpus(corpus, workspace)
    expected_corpus = {
        "path": manifest["corpus"]["path"],
        "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
        "states_sha256": file_sha256(corpus / "states.jsonl"),
        "manifest_sha256": file_sha256(corpus / "manifest.json"),
    }
    if "schema_version" in manifest["corpus"]:
        expected_corpus["schema_version"] = verified_corpus["schema_version"]
    if manifest["corpus"] != expected_corpus:
        raise ValueError("run manifest corpus binding mismatch")
    for descriptor in [manifest["baseline"], *manifest["continuation_policies"]]:
        if _policy_descriptor(
            _resolve_inside(descriptor["path"], workspace), workspace, expected=descriptor,
        ) != descriptor:
            raise ValueError("policy binding changed")
    for policies in manifest["opponent_policies"].values():
        for descriptor in policies:
            if _policy_descriptor(
                _resolve_inside(descriptor["path"], workspace), workspace, expected=descriptor,
            ) != descriptor:
                raise ValueError("opponent policy binding changed")
    engine = _engine_descriptor(
        _resolve_inside(manifest["engine"]["path"], workspace), workspace,
        expected=manifest["engine"],
    )
    if engine != manifest["engine"]:
        raise ValueError("engine binding changed")
    implementation = manifest.get("implementation")
    if not isinstance(implementation, Mapping) or not implementation:
        raise ValueError("run manifest has no implementation bindings")
    current_drift = []
    for path, binding in implementation.items():
        if (
            not isinstance(binding, Mapping)
            or set(binding) != {"source_sha256", "snapshot_path", "snapshot_sha256"}
            or binding["source_sha256"] != binding["snapshot_sha256"]
        ):
            raise ValueError("invalid implementation snapshot binding: %s" % path)
        snapshot = _resolve_inside(binding["snapshot_path"], workspace)
        if not snapshot.is_file() or file_sha256(snapshot) != binding["snapshot_sha256"]:
            raise ValueError("implementation snapshot changed: %s" % path)
        source = _resolve_inside(path, workspace)
        if not source.is_file() or file_sha256(source) != binding["source_sha256"]:
            current_drift.append(str(path))
    selection_config = manifest["config"].get("candidate_selection")
    if selection_config is not None:
        selection_path = _resolve_inside(selection_config["path"], workspace)
        verified_selection = verify_candidate_selection(selection_path, workspace)
        if (
            file_sha256(selection_path) != selection_config["file_sha256"]
            or verified_selection["manifest_sha256"] != selection_config["manifest_sha256"]
            or verified_selection["payload"]["states"] != selection_config["states"]
        ):
            raise ValueError("candidate selection binding changed")
    states = {state["state_id"]: state for state in _read_jsonl(corpus / "states.jsonl")}
    shards, missing = collect_rollout_shards(output, states, manifest)
    report_path = output / "report.json"
    if missing:
        if report_path.exists():
            raise ValueError("incomplete rollout output unexpectedly contains a report")
        if not allow_incomplete:
            state_id, batch_id = missing[0]
            raise ValueError("missing rollout shard: %s" % (
                output / "shards" / state_id / ("batch_%03d.json" % batch_id)
            ))
        return {
            "complete": False,
            "states": len(manifest["state_ids"]),
            "batches": len(manifest["batch_ids"]),
            "expected_shards": len(manifest["state_ids"]) * len(manifest["batch_ids"]),
            "shards": len(shards),
            "remaining_shards": len(missing),
            "next_missing_shard": {"state_id": missing[0][0], "batch_id": missing[0][1]},
            "rows": sum(len(shard["rows"]) for shard in shards),
            "run_manifest_sha256": manifest["manifest_sha256"],
            "report_manifest_sha256": None,
            "report_recomputed": False,
            "current_implementation_drift": current_drift,
            "current_runtime_drift": runtime_drift,
            "output_dir": str(output),
        }
    if not report_path.is_file():
        if allow_incomplete:
            return {
                "complete": False,
                "states": len(manifest["state_ids"]),
                "batches": len(manifest["batch_ids"]),
                "expected_shards": len(shards),
                "shards": len(shards),
                "remaining_shards": 0,
                "next_missing_shard": None,
                "rows": sum(len(shard["rows"]) for shard in shards),
                "run_manifest_sha256": manifest["manifest_sha256"],
                "report_manifest_sha256": None,
                "report_recomputed": False,
                "current_implementation_drift": current_drift,
                "current_runtime_drift": runtime_drift,
                "output_dir": str(output),
            }
        raise ValueError("complete rollout shards have no report")
    report = json.loads(report_path.read_text(encoding="ascii"))
    if report.get("manifest_sha256") != _self_hash(report):
        raise ValueError("rollout report self-hash mismatch")
    report_recomputed = not current_drift and not runtime_drift
    if report_recomputed:
        expected_report = make_report(shards, states, manifest)
        if report != expected_report:
            raise ValueError("rollout report does not reproduce from shards")
    return {
        "complete": True,
        "states": len(manifest["state_ids"]),
        "batches": len(manifest["batch_ids"]),
        "expected_shards": len(shards),
        "shards": len(shards),
        "remaining_shards": 0,
        "next_missing_shard": None,
        "rows": sum(len(shard["rows"]) for shard in shards),
        "run_manifest_sha256": manifest["manifest_sha256"],
        "report_manifest_sha256": report["manifest_sha256"],
        "report_recomputed": report_recomputed,
        "current_implementation_drift": current_drift,
        "current_runtime_drift": runtime_drift,
        "output_dir": str(output),
    }
