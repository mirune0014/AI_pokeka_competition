"""Non-blind upper-tier state distribution collector for paired rollouts.

Gold membership is an eligibility signal for the opposing *seat* only.  This
module deliberately never uses the recorded action as a candidate or label.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from hashlib import blake2b, sha256
import json
from pathlib import Path
import platform
import random
import sys
from typing import Any, Mapping, Sequence

from .canonical_actions import canonicalize_prompt_action
from .gold_oracle_states import (
    _visible_cards, build_beliefs, canonical_sha256, deck_signature,
    file_sha256, portable_inventory_source, validate_no_leakage,
    verified_actor_deck, verify_inventory_source_binding, write_once,
    _verify_state_belief,
)
from .probe_search import score_options
from .search_expert import candidate_actions
from .replay_records import ReplayDecisionRecord
from .replay_reconstruction import iter_replay_decisions


LEGACY_SCHEMA_VERSION = "gold_upper_tier_states.v1"
SCHEMA_VERSION = "gold_upper_tier_states.v2"
SUPPORTED_SCHEMA_VERSIONS = frozenset((LEGACY_SCHEMA_VERSION, SCHEMA_VERSION))
EXACT_COMPLETE_ACTION_CAP = 4096
CANDIDATE_SET_NAMES = ("baseline", "rule_top3", "rule_topK", "rule_diverse", "rule_plus_gold")
SUPPORTED_PROXY_CONFIDENCES = frozenset((
    "postgame_same_submission", "pregame_snapshot_unconfirmed_continuity",
    "single_snapshot_temporal_gate",
))
STATE_KEYS = {
    "schema_version", "decision_id", "state_id", "episode_id", "acting_seat",
    "source_replay_path", "replay_sha256", "split", "style_id", "submission_id",
    "replay_step", "safe_observation", "known_private_info", "public_history",
    "legal_semantic_options", "current_metadata", "candidates", "candidate_sets",
    "gold_incremental", "own_deck", "belief",
}
CODE_INPUT_NAMES = frozenset((
    "canonical_actions_module", "disagreement_audit_module",
    "oracle_state_helpers_module", "replay_records_module",
    "replay_reconstruction_module", "search_expert_module",
))


def _json(value: Any, pretty: bool = False) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("ascii")


def _write_bytes_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain an object" % path)
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_state_spec(value: str) -> tuple[str, int, int]:
    parts = value.split(":")
    if len(parts) != 3 or not parts[0]:
        raise ValueError("--state must be EPISODE:ACTING_SEAT:REPLAY_STEP")
    try:
        seat, step = int(parts[1]), int(parts[2])
    except ValueError as error:
        raise ValueError("--state must be EPISODE:ACTING_SEAT:REPLAY_STEP") from error
    if seat not in (0, 1) or step < 0:
        raise ValueError("state seat must be 0 or 1 and replay step non-negative")
    return parts[0], seat, step


def multiset_replacement_distance(left: Sequence[int], right: Sequence[int]) -> int:
    """Number of one-card replacements needed to transform one 60-card deck."""
    if len(left) != 60 or len(right) != 60:
        raise ValueError("replacement distance requires two 60-card decks")
    return sum((Counter(map(int, left)) - Counter(map(int, right))).values())


def _date(value: str) -> str:
    return str(value).split("T", 1)[0]


def _row_deck(row: Mapping[str, str]) -> list[int]:
    deck = [int(value) for value in str(row.get("deck", "")).split()]
    if len(deck) != 60:
        raise ValueError("inventory row does not contain a 60-card deck")
    return deck


def _same_replay(left: Mapping[str, str], right: Mapping[str, str]) -> bool:
    return (str(left.get("file")) == str(right.get("file")) and
            str(left.get("replay_sha256")).lower() == str(right.get("replay_sha256")).lower())


def eligible_state(
    episode_id: str, acting_seat: int, inventory_rows: Sequence[Mapping[str, str]],
    gold_rows: Sequence[Mapping[str, str]], blind_dates: set[str], baseline_deck: Sequence[int],
    max_deck_replacements: int,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Perform every metadata-only eligibility check before a replay is opened."""
    actor = [row for row in inventory_rows if str(row.get("episode_id")) == str(episode_id)
             and str(row.get("player_index")) == str(acting_seat)]
    opponent_seat = 1 - int(acting_seat)
    opponent = [row for row in inventory_rows if str(row.get("episode_id")) == str(episode_id)
                and str(row.get("player_index")) == str(opponent_seat)]
    if len(actor) != 1 or len(opponent) != 1:
        raise ValueError("expected exactly one actor and opponent inventory row")
    actor_row, opponent_row = actor[0], opponent[0]
    if not _same_replay(actor_row, opponent_row):
        raise ValueError("episode seats do not have one joined replay binding")
    if _date(str(actor_row.get("match_timestamp_utc", ""))) in blind_dates:
        raise ValueError("blind date is forbidden before replay loading")
    if not str(actor_row.get("archetype", "")).lower().startswith("archaludon"):
        raise ValueError("actor is not Archaludon")
    if multiset_replacement_distance(_row_deck(actor_row), baseline_deck) > max_deck_replacements:
        raise ValueError("actor deck exceeds allowed baseline replacements")
    joined = [row for row in gold_rows if str(row.get("episode_id")) == str(episode_id)
              and str(row.get("player_index")) == str(opponent_seat) and _same_replay(row, opponent_row)]
    if len(joined) != 1:
        raise ValueError("opposing seat lacks an exact unique Gold catalog join")
    gold = joined[0]
    try:
        rank = int(str(gold.get("gold_rank")))
    except ValueError as error:
        raise ValueError("Gold rank is not an integer") from error
    if not 1 <= rank <= 20 or str(gold.get("gold_proxy_confidence")) not in SUPPORTED_PROXY_CONFIDENCES:
        raise ValueError("opposing seat has unsupported Gold proxy metadata")
    return dict(actor_row), dict(opponent_row), dict(gold)


def _action_type(action: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(sorted(int(item.get("action_type", -1)) for item in action.get("selections", [])))


def exact_rule_candidates(observation: Any, scores: Sequence[float], baseline_action: Sequence[int], *, top_k: int, max_diverse: int) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Enumerate every legal complete action.  No recorded replay action enters here."""
    actions = candidate_actions(
        observation,
        scores,
        baseline_action,
        mode="complete",
        max_complete_actions=EXACT_COMPLETE_ACTION_CAP,
    )
    baseline = [int(item) for item in baseline_action]
    baseline_id = canonicalize_prompt_action(observation, baseline).stable_id
    if not any(canonicalize_prompt_action(observation, action).stable_id == baseline_id for action in actions):
        raise ValueError("baseline action is not an exact legal complete action")
    by_id: dict[str, dict[str, Any]] = {}
    for action in actions:
        canonical = canonicalize_prompt_action(observation, action)
        item = {"semantic_id": canonical.stable_id, "canonical": canonical.to_dict(),
                "additive_rule_score": float(sum(float(scores[index]) for index in action)), "source_tags": []}
        old = by_id.get(canonical.stable_id)
        if old is None or item["additive_rule_score"] > old["additive_rule_score"]:
            by_id[canonical.stable_id] = item
    ranked = sorted(by_id.values(), key=lambda item: (-item["additive_rule_score"], item["semantic_id"]))
    top3 = list(dict.fromkeys([baseline_id] + [item["semantic_id"] for item in ranked[:3]]))
    top = list(dict.fromkeys([baseline_id] + [item["semantic_id"] for item in ranked[:top_k]]))
    if len(top) > max_diverse:
        raise ValueError("rule_topK exceeds max-diverse-actions")
    diverse, seen = list(top), {_action_type(by_id[item]["canonical"]) for item in top}
    added = []
    for item in ranked:
        if len(diverse) >= max_diverse:
            break
        signature = _action_type(item["canonical"])
        if signature not in seen:
            diverse.append(item["semantic_id"]); added.append(item["semantic_id"]); seen.add(signature)
    sets = {"baseline": [baseline_id], "rule_top3": top3, "rule_topK": top,
            "rule_diverse": diverse, "rule_plus_gold": list(diverse)}
    for name, ids in sets.items():
        for identifier in ids:
            by_id[identifier]["source_tags"].append(name)
    for identifier in added:
        by_id[identifier]["source_tags"].append("action_type_diverse")
    candidates = [by_id[item["semantic_id"]] for item in ranked]
    return candidates, sets


def _bound_inputs(baseline_dir: Path, engine_dir: Path, inventory: Path, gold: Path, catalog: Path, split: Path, extras: Mapping[str, Sequence[Path]]) -> dict[str, Path]:
    result = {"baseline_main": baseline_dir / "main.py", "baseline_deck": baseline_dir / "deck.csv",
              "inventory_csv": inventory, "gold_candidates_csv": gold, "gold_catalog_manifest": catalog,
              "split_manifest": split,
              "canonical_actions_module": Path(__file__).resolve().parent / "canonical_actions.py",
              "disagreement_audit_module": Path(__file__).resolve().parent / "gold_disagreement_audit.py",
              "oracle_state_helpers_module": Path(__file__).resolve().parent / "gold_oracle_states.py",
              "replay_records_module": Path(__file__).resolve().parent / "replay_records.py",
              "replay_reconstruction_module": Path(__file__).resolve().parent / "replay_reconstruction.py",
              "search_expert_module": Path(__file__).resolve().parent / "search_expert.py"}
    ordinal = 0
    for archetype, paths in sorted(extras.items()):
        for path in paths:
            result["extra_deck:%03d:%s" % (ordinal, archetype)] = path
            ordinal += 1
    return result


def _portable_path(path: Path, workspace: Path) -> str:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("bound path escapes workspace") from error
    return str(relative).replace("\\", "/")


def _engine_binding(engine_dir: Path) -> dict[str, Any]:
    cg = engine_dir / "cg"
    binary_name = "cg.dll"
    binary = cg / binary_name
    if not binary.is_file() or not (cg / "api.py").is_file():
        raise ValueError("collector engine is missing cg.dll or api.py")
    python_files = {}
    for name in ("__init__.py", "api.py", "game.py", "sim.py", "utils.py"):
        path = cg / name
        if path.is_file():
            python_files[name] = file_sha256(path)
    return {
        "binary_name": binary_name,
        "binary_sha256": file_sha256(binary),
        "python_files_sha256": python_files,
    }


def _manifest_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _verify_catalog_binding(catalog: Mapping[str, Any], gold_csv: Path) -> None:
    if catalog.get("schema_version") != "gold_seat_candidates.v1":
        raise ValueError("unsupported Gold catalog manifest")
    if catalog.get("catalog_sha256") != file_sha256(gold_csv):
        raise ValueError("Gold catalog manifest does not bind candidate CSV")
    # The frozen inventory predates the newline-terminated manifest convention
    # used by the Phase 3 artifacts. Verify its original compact JSON hash.
    unsigned = {key: item for key, item in catalog.items() if key != "manifest_sha256"}
    catalog_self_hash = sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()
    if catalog.get("manifest_sha256") != catalog_self_hash:
        raise ValueError("Gold catalog manifest self-hash mismatch")


def _resolve(path: str, workspace: Path) -> Path:
    result = (Path(path) if Path(path).is_absolute() else workspace / path).resolve()
    try: result.relative_to(workspace.resolve())
    except ValueError as error: raise ValueError("bound path escapes workspace") from error
    return result


def _state_verify(
    state: Mapping[str, Any], config: Mapping[str, Any], schema_version: str = SCHEMA_VERSION,
) -> None:
    if set(state) != STATE_KEYS or state.get("schema_version") != schema_version or state.get("split") != "development":
        raise ValueError("state schema or split mismatch")
    if state.get("gold_incremental") is not False or state.get("candidate_sets", {}).get("rule_plus_gold") != state.get("candidate_sets", {}).get("rule_diverse"):
        raise ValueError("upper-tier state has Gold candidate semantics")
    candidates, sets = state.get("candidates"), state.get("candidate_sets")
    if not isinstance(candidates, list) or not isinstance(sets, Mapping) or set(sets) != set(CANDIDATE_SET_NAMES):
        raise ValueError("candidate schema mismatch")
    ids = set()
    assert_no_gold_candidate_tags(candidates)
    for item in candidates:
        if set(item) != {"semantic_id", "canonical", "additive_rule_score", "source_tags"}:
            raise ValueError("candidate Gold leakage or schema mismatch")
        encoded = json.dumps(item["canonical"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if item["semantic_id"] != blake2b(encoded, digest_size=32).hexdigest() or item["semantic_id"] in ids:
            raise ValueError("candidate semantic identity mismatch")
        ids.add(item["semantic_id"])
    if len(sets["baseline"]) != 1 or not set(sets["rule_topK"]) <= set(sets["rule_diverse"]) or not all(set(values) <= ids and len(values) == len(set(values)) for values in sets.values()):
        raise ValueError("candidate set semantics mismatch")
    if len(sets["rule_diverse"]) > int(config["max_diverse_actions"]):
        raise ValueError("candidate set exceeds configured bound")
    meta = state.get("current_metadata", {})
    allowed_metadata = {"turn", "own_archetype", "opponent_archetype", "corpus_role", "recorded_action_role"}
    if set(meta) != allowed_metadata or meta.get("corpus_role") != "upper_tier_state_distribution" or meta.get("recorded_action_role") != "provenance_only":
        raise ValueError("state provenance declarations missing")
    _verify_state_belief(state)
    validate_no_leakage(state)


def assert_no_gold_candidate_tags(candidates: Sequence[Mapping[str, Any]]) -> None:
    for item in candidates:
        tags = item.get("source_tags")
        if not isinstance(tags, list) or "gold" in tags:
            raise ValueError("candidate has forbidden Gold source tag")


def verify_gold_upper_tier_states(output_dir: str | Path, workspace_root: str | Path | None = None) -> dict[str, Any]:
    workspace = Path(workspace_root or Path(__file__).resolve().parents[2]).resolve()
    output = _resolve(str(output_dir), workspace)
    selection, manifest = _read_object(output / "selection_manifest.json"), _read_object(output / "manifest.json")
    schema_version = selection.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS or selection.get("manifest_sha256") != _manifest_hash(selection):
        raise ValueError("selection manifest self-hash mismatch")
    if manifest.get("schema_version") != schema_version or manifest.get("manifest_sha256") != _manifest_hash(manifest):
        raise ValueError("manifest self-hash mismatch")
    if manifest.get("corpus_role") != "upper_tier_state_distribution" or manifest.get("direct_gold_candidates") is not False or manifest.get("recorded_action_role") != "provenance_only":
        raise ValueError("manifest role declarations mismatch")
    if manifest.get("selection_manifest_sha256") != file_sha256(output / "selection_manifest.json") or manifest.get("states_sha256") != file_sha256(output / "states.jsonl"):
        raise ValueError("artifact binding mismatch")
    inputs = selection.get("inputs", {})
    implementation_drift = []
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("invalid input binding")
        path = _resolve(str(binding["path"]), workspace)
        if not path.is_file() or file_sha256(path) != binding["sha256"]:
            if name in CODE_INPUT_NAMES:
                implementation_drift.append("input:%s" % name)
                continue
            raise ValueError("input hash mismatch: %s" % name)
    required = {"inventory_csv", "gold_candidates_csv", "gold_catalog_manifest", "split_manifest", "baseline_main", "baseline_deck", "canonical_actions_module", "disagreement_audit_module", "oracle_state_helpers_module", "replay_records_module", "replay_reconstruction_module", "search_expert_module"}
    if schema_version == LEGACY_SCHEMA_VERSION:
        required.update(("engine_api", "engine_dll"))
    if not required <= set(inputs): raise ValueError("required input bindings missing")
    for name, binding in selection.get("implementation", {}).items():
        if not isinstance(binding, Mapping):
            raise ValueError("invalid implementation snapshot binding")
        snapshot = output / str(binding.get("snapshot", ""))
        if (not snapshot.is_file() or file_sha256(snapshot) != binding.get("snapshot_sha256")
                or binding.get("source_sha256") != binding.get("snapshot_sha256")):
            raise ValueError("implementation snapshot mismatch: %s" % name)
        source = _resolve(str(binding.get("source_path", "")), workspace)
        if not source.is_file() or file_sha256(source) != binding.get("source_sha256"):
            implementation_drift.append(str(name))
    if schema_version == SCHEMA_VERSION:
        engine_binding = selection.get("engine_binding")
        if (
            not isinstance(engine_binding, Mapping)
            or set(engine_binding) != {"binary_name", "binary_sha256", "python_files_sha256"}
            or engine_binding.get("binary_name") != "cg.dll"
            or not isinstance(engine_binding.get("python_files_sha256"), Mapping)
            or any(len(str(value)) != 64 for value in (
                engine_binding.get("binary_sha256"),
                *engine_binding.get("python_files_sha256", {}).values(),
            ))
            or manifest.get("engine_binding") != engine_binding
        ):
            raise ValueError("portable engine binding mismatch")
        configured_paths = sorted(
            str(path) for paths in selection.get("config", {}).get("extra_decks", {}).values()
            for path in paths
        )
        input_paths = sorted(
            str(binding["path"]) for name, binding in inputs.items()
            if name.startswith("extra_deck:")
        )
        if configured_paths != input_paths or any(
            Path(path).is_absolute() or ":" in Path(path).parts[0] or ".." in Path(path).parts
            for path in configured_paths
        ):
            raise ValueError("portable extra-deck bindings mismatch")
    _verify_catalog_binding(_read_object(_resolve(inputs["gold_catalog_manifest"]["path"], workspace)), _resolve(inputs["gold_candidates_csv"]["path"], workspace))
    inventory_rows = _read_csv(_resolve(inputs["inventory_csv"]["path"], workspace))
    gold_rows = _read_csv(_resolve(inputs["gold_candidates_csv"]["path"], workspace))
    blind_dates = {str(item) for item in _read_object(_resolve(inputs["split_manifest"]["path"], workspace)).get("blind_date_periods", [])}
    baseline_deck = [int(value) for value in _resolve(inputs["baseline_deck"]["path"], workspace).read_text(encoding="ascii").splitlines() if value.strip()]
    states = []
    for line in (output / "states.jsonl").read_text(encoding="ascii").splitlines():
        if not line: raise ValueError("blank state row")
        states.append(json.loads(line))
    specs = [tuple(item) for item in selection.get("state_specs", [])]
    if len(states) != len(specs) or len({state.get("decision_id") for state in states}) != len(states) or len({state.get("state_id") for state in states}) != len(states):
        raise ValueError("state identity/count mismatch")
    for state in states: _state_verify(state, selection["config"], schema_version)
    if { (str(item["episode_id"]), int(item["acting_seat"]), int(item["replay_step"])) for item in states } != set(specs):
        raise ValueError("selected state specs mismatch")
    replay_bindings = manifest.get("source_replays")
    if not isinstance(replay_bindings, list) or manifest.get("source_replays_sha256") != canonical_sha256(replay_bindings):
        raise ValueError("source replay aggregate binding mismatch")
    by_state_path = {str(item["source_replay_path"]): str(item["replay_sha256"]) for item in states}
    if len(by_state_path) != len(replay_bindings):
        raise ValueError("source replay bindings are duplicated or incomplete")
    for binding in replay_bindings:
        if not isinstance(binding, Mapping) or set(binding) != {"source_replay_path", "replay_sha256"}:
            raise ValueError("invalid source replay binding")
        path, digest = str(binding["source_replay_path"]), str(binding["replay_sha256"])
        if by_state_path.get(path) != digest or file_sha256(_resolve(path, workspace)) != digest:
            raise ValueError("source replay hash mismatch")
    expected_gold_meta = []
    for state in states:
        actor, _opponent, gold = eligible_state(
            str(state["episode_id"]), int(state["acting_seat"]), inventory_rows,
            gold_rows, blind_dates, baseline_deck,
            int(selection["config"]["max_deck_replacements"]),
        )
        if not _same_replay(actor, {"file": state["source_replay_path"], "replay_sha256": state["replay_sha256"]}):
            raise ValueError("state source replay does not match inventory")
        replay = json.loads(_resolve(str(state["source_replay_path"]), workspace).read_text(encoding="utf-8"))
        inventory_path = _resolve(inputs["inventory_csv"]["path"], workspace)
        deck, source = verified_actor_deck(
            replay, inventory_path, str(state["episode_id"]), int(state["acting_seat"]),
        )
        own_deck = state.get("own_deck")
        if (
            not isinstance(own_deck, Mapping)
            or own_deck.get("decklist") != deck
            or own_deck.get("sha256") != canonical_sha256(deck)
            or not isinstance(own_deck.get("inventory_source"), Mapping)
        ):
            raise ValueError("state own deck no longer matches replay and inventory")
        verify_inventory_source_binding(
            own_deck["inventory_source"], source, inputs["inventory_csv"]["path"],
        )
        expected_gold_meta.append({"episode_id": str(state["episode_id"]), "acting_seat": int(state["acting_seat"]),
            "opponent_seat": 1 - int(state["acting_seat"]), "gold_rank": int(gold["gold_rank"]),
            "gold_proxy_confidence": gold["gold_proxy_confidence"],
            "gold_snapshot_sha256": gold.get("gold_snapshot_sha256")})
    expected_counts = {"states": len(states), "episodes": len({item["episode_id"] for item in states}),
        "candidate_coverage": {name: sum(bool(item["candidate_sets"][name]) for item in states) for name in CANDIDATE_SET_NAMES}}
    if manifest.get("counts") != expected_counts:
        raise ValueError("manifest aggregate counts mismatch")
    if manifest.get("opponent_gold_proxy_metadata") != sorted(expected_gold_meta, key=lambda item: (item["episode_id"], item["acting_seat"])):
        raise ValueError("manifest Gold proxy metadata mismatch")
    if schema_version == LEGACY_SCHEMA_VERSION:
        if manifest.get("engine_files_sha256") != {"cg/api.py": inputs["engine_api"]["sha256"], "cg/cg.dll": inputs["engine_dll"]["sha256"]}:
            raise ValueError("manifest engine binding mismatch")
    elif "engine_files_sha256" in manifest:
        raise ValueError("portable manifest contains legacy engine files")
    return {"schema_version": schema_version, "states": len(states), "verified": True,
             "implementation_drift": sorted(implementation_drift)}


def run_collector(*, baseline_dir: Path, engine_dir: Path, inventory_csv: Path, gold_candidates_csv: Path, gold_catalog_manifest: Path, split_manifest: Path, output_dir: Path, workspace_root: Path, state_specs: Sequence[tuple[str, int, int]], extra_decks: Mapping[str, Sequence[Path]], rule_top_k: int = 6, max_diverse_actions: int = 12, max_known_hypotheses: int = 3, unknown_mass: float = 0.15, max_deck_replacements: int = 4, seed: str) -> dict[str, Any]:
    if not state_specs or len(set(state_specs)) != len(state_specs): raise ValueError("state specs must be unique and non-empty")
    if rule_top_k < 1 or max_diverse_actions < rule_top_k + 1 or max_known_hypotheses < 1 or not 0 <= unknown_mass < 1 or max_deck_replacements < 0: raise ValueError("invalid limits")
    workspace = workspace_root.resolve()
    baseline_dir, engine_dir, inventory_csv, gold_candidates_csv, gold_catalog_manifest, split_manifest, output_dir = (
        _resolve(str(path), workspace) for path in (baseline_dir, engine_dir, inventory_csv, gold_candidates_csv, gold_catalog_manifest, split_manifest, output_dir)
    )
    extra_decks = {name: [_resolve(str(path), workspace) for path in paths] for name, paths in extra_decks.items()}
    inventory_rows, gold_rows = _read_csv(inventory_csv), _read_csv(gold_candidates_csv)
    catalog_manifest, split = _read_object(gold_catalog_manifest), _read_object(split_manifest)
    _verify_catalog_binding(catalog_manifest, gold_candidates_csv)
    blind_dates = {str(item) for item in split.get("blind_date_periods", [])}
    baseline_deck = [int(value.strip()) for value in (baseline_dir / "deck.csv").read_text(encoding="ascii").splitlines() if value.strip()]
    inputs = _bound_inputs(baseline_dir, engine_dir, inventory_csv, gold_candidates_csv, gold_catalog_manifest, split_manifest, extra_decks)
    config = {"rule_top_k": rule_top_k, "max_diverse_actions": max_diverse_actions, "max_known_hypotheses": max_known_hypotheses, "unknown_mass": unknown_mass, "max_deck_replacements": max_deck_replacements, "seed": str(seed), "extra_decks": {name: [_portable_path(path, workspace) for path in paths] for name, paths in sorted(extra_decks.items())}}
    implementation = {}
    for name, source in {"collector_module": Path(__file__), "collector_cli": Path(__file__).resolve().parents[2] / "infrastructure" / "tools" / "build_gold_upper_tier_states.py"}.items():
        snapshot = output_dir / "source_snapshot" / source.name
        _write_bytes_once(snapshot, source.read_bytes())
        implementation[name] = {"source_path": str(source.resolve().relative_to(workspace)).replace("\\", "/"),
            "source_sha256": file_sha256(source), "snapshot": str(snapshot.relative_to(output_dir)).replace("\\", "/"),
            "snapshot_sha256": file_sha256(snapshot)}
    selection = {"schema_version": SCHEMA_VERSION, "state_specs": [list(item) for item in sorted(state_specs)], "inputs": {name: {"path": _portable_path(path, workspace), "sha256": file_sha256(path)} for name, path in sorted(inputs.items())}, "engine_binding": _engine_binding(engine_dir), "config": config, "implementation": implementation, "source_snapshots": {"inventory_sha256": file_sha256(inventory_csv), "gold_candidates_sha256": file_sha256(gold_candidates_csv), "gold_catalog_manifest_sha256": file_sha256(gold_catalog_manifest), "split_manifest_sha256": file_sha256(split_manifest)}}
    selection["manifest_sha256"] = _manifest_hash(selection); write_once(output_dir / "selection_manifest.json", selection)
    # All metadata eligibility happens before the first replay file is read.
    selected = {spec: eligible_state(spec[0], spec[1], inventory_rows, gold_rows, blind_dates, baseline_deck, max_deck_replacements) for spec in state_specs}
    from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent
    ensure_engine_on_path(engine_dir)
    states, replay_bindings, gold_meta = [], {}, []
    from .gold_oracle_states import build_catalog
    from .gold_disagreement_audit import _seed_rule_agent
    for spec in sorted(state_specs):
        episode, seat, target_step = spec; actor_row, opponent_row, gold_row = selected[spec]
        replay_path = _resolve(actor_row["file"], workspace); replay_hash = str(actor_row["replay_sha256"])
        if file_sha256(replay_path) != replay_hash: raise ValueError("source replay hash mismatch")
        replay = json.loads(replay_path.read_text(encoding="utf-8")); own_deck, inventory_source = verified_actor_deck(replay, inventory_csv, episode, seat)
        inventory_source = portable_inventory_source(
            inventory_source, inventory_csv, workspace,
        )
        catalog = build_catalog(inventory_csv, extra_decks, {str(row["episode_id"]) for row in inventory_rows if _date(row.get("match_timestamp_utc", "")) not in blind_dates}, {(episode, 1 - seat)})
        agent = load_agent(baseline_dir, "gold_upper_tier_actor_%s_%s" % (episode, seat))
        _seed_rule_agent(agent, str(seed), str(episode), int(seat))
        found = False
        for decision in iter_replay_decisions(replay, seats=[seat]):
            # Call every prior actor prompt in replay order before using the target action.
            baseline = agent(dict(decision.observation))
            if decision.replay_step != target_step: continue
            found = True; converted, scores, _ = score_options(agent, dict(decision.observation))
            record = ReplayDecisionRecord.from_observation(decision.observation, decision.raw_action, episode_id=episode, submission_id="upper_tier_provenance", style_id="upper_tier_distribution", decision_step=target_step, replay_step=target_step, acting_seat=seat, own_archetype=actor_row["archetype"], opponent_archetype=opponent_row["archetype"], public_history=decision.public_history, private_action_history=decision.private_action_history)
            candidates, sets = exact_rule_candidates(converted, scores, baseline, top_k=rule_top_k, max_diverse=max_diverse_actions)
            belief = build_beliefs(catalog, opponent_row["archetype"], _visible_cards(record.safe_observation), max_known=max_known_hypotheses, unknown_mass=unknown_mass, observation=decision.observation, own_deck=own_deck, preflight_seed="%s:%s" % (seed, record.decision_id))
            state = {"schema_version": SCHEMA_VERSION, "decision_id": record.decision_id, "state_id": record.state_id, "episode_id": episode, "acting_seat": seat, "source_replay_path": actor_row["file"], "replay_sha256": replay_hash, "split": "development", "style_id": "upper_tier_distribution", "submission_id": "upper_tier_provenance", "replay_step": target_step, "safe_observation": record.safe_observation, "known_private_info": record.known_private_info, "public_history": record.public_history, "legal_semantic_options": list(record.legal_semantic_options), "current_metadata": {"turn": record.turn, "own_archetype": actor_row["archetype"], "opponent_archetype": opponent_row["archetype"], "corpus_role": "upper_tier_state_distribution", "recorded_action_role": "provenance_only"}, "candidates": candidates, "candidate_sets": sets, "gold_incremental": False, "own_deck": {"decklist": own_deck, "sha256": canonical_sha256(own_deck), "inventory_source": inventory_source}, "belief": belief}
            _state_verify(state, config, SCHEMA_VERSION); states.append(state); replay_bindings[actor_row["file"]] = replay_hash
            break
        if not found: raise ValueError("requested replay step was not reconstructed")
        gold_meta.append({"episode_id": episode, "acting_seat": seat, "opponent_seat": 1 - seat, "gold_rank": int(gold_row["gold_rank"]), "gold_proxy_confidence": gold_row["gold_proxy_confidence"], "gold_snapshot_sha256": gold_row.get("gold_snapshot_sha256")})
    states.sort(key=lambda item: item["decision_id"]); states_bytes = b"".join(_json(item) for item in states)
    states_path = output_dir / "states.jsonl"; _write_bytes_once(states_path, states_bytes)
    source_replays = [{"source_replay_path": path, "replay_sha256": digest} for path, digest in sorted(replay_bindings.items())]
    manifest = {"schema_version": SCHEMA_VERSION, "corpus_role": "upper_tier_state_distribution", "direct_gold_candidates": False, "recorded_action_role": "provenance_only", "selection_manifest_sha256": file_sha256(output_dir / "selection_manifest.json"), "states_sha256": file_sha256(states_path), "source_replays": source_replays, "source_replays_sha256": canonical_sha256(source_replays), "opponent_gold_proxy_metadata": sorted(gold_meta, key=lambda item: (item["episode_id"], item["acting_seat"])), "engine_binding": selection["engine_binding"], "python": sys.version, "platform": platform.platform(), "command": list(sys.argv), "source_snapshots": selection["source_snapshots"], "counts": {"states": len(states), "episodes": len({item["episode_id"] for item in states}), "candidate_coverage": {name: sum(bool(item["candidate_sets"][name]) for item in states) for name in CANDIDATE_SET_NAMES}}}
    manifest["manifest_sha256"] = _manifest_hash(manifest); write_once(output_dir / "manifest.json", manifest)
    return verify_gold_upper_tier_states(output_dir, workspace)
