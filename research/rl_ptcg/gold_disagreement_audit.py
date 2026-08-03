"""Bounded, reproducible rule-agent audit of non-blind Gold replay decisions."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import blake2b, sha256
import itertools
import json
import math
import platform
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

from .canonical_actions import canonicalize_prompt_action
from .gold_replay_dataset import verify_gold_replay_dataset
from .probe_search import score_options
from .replay_records import ReplayDecisionRecord
from .replay_reconstruction import iter_replay_decisions
from .search_expert import candidate_actions


SCHEMA_VERSION = "gold_disagreement_audit.v1"
DEFAULT_SOURCES = ("train", "development", "policy_family_holdout")
STRATA = ("own_archaludon", "gold_opponent_vs_archaludon", "mega_lucario", "neutral")
STRATUM_FRACTIONS = (0.35, 0.30, 0.20, 0.15)


def _json(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("ascii")


def _hash(value: Any) -> str:
    return blake2b(_json(value), digest_size=32).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return sha256(_json(value)).hexdigest()


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _implementation_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    relative_paths = (
        "research/rl_ptcg/canonical_actions.py",
        "research/rl_ptcg/gold_disagreement_audit.py",
        "research/rl_ptcg/gold_replay_dataset.py",
        "research/rl_ptcg/probe_search.py",
        "research/rl_ptcg/replay_reconstruction.py",
        "research/rl_ptcg/replay_records.py",
        "research/rl_ptcg/search_expert.py",
        "infrastructure/tools/ptcg_common.py",
        "infrastructure/tools/run_gold_disagreement_audit.py",
    )
    return {
        relative: _file_hash(root / relative)
        for relative in relative_paths
    }


def _contains(value: Any, needle: str) -> bool:
    normalized_value = "".join(character for character in str(value or "").lower() if character.isalnum())
    normalized_needle = "".join(character for character in str(needle).lower() if character.isalnum())
    return normalized_needle in normalized_value


def selection_stratum(record: Any) -> str:
    """Classify without consulting action scores or disagreement outcomes."""
    own = getattr(record, "own_archetype", None)
    opponent = getattr(record, "opponent_archetype", None)
    if _contains(own, "archaludon"):
        return "own_archaludon"
    if _contains(opponent, "archaludon"):
        return "gold_opponent_vs_archaludon"
    if _contains(own, "mega lucario") or _contains(opponent, "mega lucario") or _contains(own, "megalucario") or _contains(opponent, "megalucario"):
        return "mega_lucario"
    return "neutral"


def _priority(record: Any, seed: str) -> tuple[str, str]:
    return (_hash({"seed": str(seed), "decision_id": str(getattr(record, "decision_id"))}), str(getattr(record, "decision_id")))


def _diversity_key(record: Any) -> tuple[str, str, str, str, str]:
    source = getattr(record, "source_metadata", {}) or {}
    terminal = getattr(record, "terminal_result", {}) or {}
    action = getattr(record, "chosen_canonical_action", {}) or {}
    return (str(getattr(record, "style_id", "unknown")), str(terminal.get("seat_reward", "unknown")),
            str(source.get("gold_proxy_confidence", "unknown")), _turn_band(getattr(record, "turn", None)),
            str(action.get("selection_context", "unknown")))


def _take_diverse(items: Sequence[Any], count: int, seed: str) -> list[Any]:
    """Round-robin metadata cells, then use the stable hash inside each cell."""
    cells: dict[tuple[str, str, str, str, str], list[Any]] = defaultdict(list)
    for item in items: cells[_diversity_key(item)].append(item)
    for values in cells.values(): values.sort(key=lambda item: _priority(item, seed))
    order = sorted(cells, key=lambda key: _hash({"seed": str(seed), "cell": key}))
    selected: list[Any] = []
    while order and len(selected) < count:
        next_order = []
        for key in order:
            if cells[key] and len(selected) < count: selected.append(cells[key].pop(0))
            if cells[key]: next_order.append(key)
        order = next_order
    return selected


def sample_records(records: Iterable[Any], *, target_count: int, seed: str) -> tuple[list[Any], dict[str, Any]]:
    """Freeze stratified IDs deterministically; no score/disagreement field is read."""
    values = sorted(records, key=lambda value: str(getattr(value, "decision_id")))
    if target_count < 0:
        raise ValueError("target_count must be non-negative")
    available = min(target_count, len(values))
    requested = {name: int(target_count * fraction) for name, fraction in zip(STRATA, STRATUM_FRACTIONS)}
    for name in STRATA[:target_count - sum(requested.values())]:
        requested[name] += 1
    buckets = {name: sorted((item for item in values if selection_stratum(item) == name), key=lambda item: _priority(item, seed)) for name in STRATA}
    selected: list[Any] = []
    realized: dict[str, int] = {}
    for name in STRATA:
        chosen = _take_diverse(buckets[name], requested[name], seed)
        selected.extend(chosen)
        realized[name] = len(chosen)
    selected_ids = {str(getattr(item, "decision_id")) for item in selected}
    remainder = sorted((item for item in values if str(getattr(item, "decision_id")) not in selected_ids), key=lambda item: _priority(item, seed))
    selected.extend(_take_diverse(remainder, max(0, available - len(selected)), seed))
    selected = sorted(selected, key=lambda item: str(getattr(item, "decision_id")))
    realized = dict(sorted(Counter(selection_stratum(item) for item in selected).items()))
    return selected, {"requested": requested, "realized": realized, "available": len(values), "selected": len(selected)}


def make_sample_manifest(records: Iterable[Any], *, target_count: int, seed: str, dataset_hash: str, split_hash: str, baseline_map_hash: str) -> dict[str, Any]:
    selected, quotas = sample_records(records, target_count=target_count, seed=seed)
    payload = {"schema_version": SCHEMA_VERSION, "source_splits": list(DEFAULT_SOURCES), "seed": str(seed),
               "target_count": target_count, "dataset_sha256": dataset_hash, "split_manifest_sha256": split_hash,
               "baseline_map_canonical_sha256": baseline_map_hash, "strata": list(STRATA), "quotas": quotas,
               "decision_ids": [str(item.decision_id) for item in selected]}
    payload["manifest_blake2b"] = _hash(payload)
    payload["manifest_sha256"] = sha256(_json(payload)).hexdigest()
    return payload


def write_once_json(path: Path, value: Any) -> None:
    data = _json(value, pretty=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"refusing to replace non-identical artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _semantic_difference(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("selection_context", "minimum_count", "maximum_count")
    result = {key: {"gold": left.get(key), "baseline": right.get(key)} for key in keys if left.get(key) != right.get(key)}
    gold = left.get("selections", [])
    baseline = right.get("selections", [])
    fields = ("action_type", "source_card_id", "target_card_id", "attack_id", "effect_source_id", "selection_context")
    result["cardinality"] = {"gold": len(gold), "baseline": len(baseline)}
    result["selection_fields"] = {field: {"gold": sorted(str(x.get(field)) for x in gold), "baseline": sorted(str(x.get(field)) for x in baseline)}
                                  for field in fields if sorted(str(x.get(field)) for x in gold) != sorted(str(x.get(field)) for x in baseline)}
    return result


def rank_complete_actions(observation: Any, scores: Sequence[float], baseline: Sequence[int], gold: Sequence[int], *, max_complete_actions: int) -> dict[str, Any]:
    """Rank semantic complete actions; ordinals and option order cannot choose ties."""
    try:
        raw = candidate_actions(observation, scores, baseline, mode="complete", max_complete_actions=max_complete_actions)
        scope = "exact"
    except ValueError as error:
        if "exceeds max_complete_actions" not in str(error):
            raise
        raw = candidate_actions(observation, scores, baseline, mode="ranked", max_actions=max_complete_actions)
        scope = "truncated"
    gold_id = canonicalize_prompt_action(observation, gold).stable_id
    generated_semantic_ids = {
        canonicalize_prompt_action(observation, action).stable_id
        for action in raw
    }
    gold_generated = gold_id in generated_semantic_ids
    for action in (list(baseline), list(gold)):
        if action not in raw:
            raw.append(action)
    candidates: dict[str, dict[str, Any]] = {}
    for action in raw:
        canonical = canonicalize_prompt_action(observation, action)
        identifier = canonical.stable_id
        score = sum(float(scores[index]) for index in action)
        old = candidates.get(identifier)
        if old is None or score > old["score"] or (score == old["score"] and list(action) < old["action"]):
            candidates[identifier] = {"semantic_id": identifier, "action": list(action), "canonical": canonical.to_dict(), "score": score}
    ranked = sorted(candidates.values(), key=lambda row: (-row["score"], row["semantic_id"]))
    ranks = {row["semantic_id"]: index + 1 for index, row in enumerate(ranked)}
    baseline_id = canonicalize_prompt_action(observation, baseline).stable_id
    return {"scope": scope, "candidate_count": len(ranked), "ranked": ranked,
            "gold_rank": ranks.get(gold_id), "baseline_rank": ranks.get(baseline_id),
            "gold_generated": gold_generated, "gold_injected_for_ranking": not gold_generated,
            "gold_feasible": gold_id in ranks, "gold_semantic_id": gold_id, "baseline_semantic_id": baseline_id}


def same_state_agreement(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, set[str]] = defaultdict(set)
    styles: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        groups[str(row.get("state_id"))].add(str(row.get("gold_semantic_id")))
        styles[str(row.get("state_id"))].add(str(row.get("style_id")))
    eligible = [key for key, value in styles.items() if len(value) > 1]
    agreeing = sum(len(groups[key]) == 1 for key in eligible)
    return {"eligible_same_state_cross_style": len(eligible), "agreeing": agreeing,
            "coverage": 0.0 if not eligible else agreeing / len(eligible)}


def _turn_band(turn: Any) -> str:
    try: value = int(turn)
    except (TypeError, ValueError): return "unknown"
    return "early" if value <= 3 else "mid" if value <= 8 else "late"


def _action_type(record: Any) -> str:
    choices = record.chosen_canonical_action.get("selections", [])
    return str(choices[0].get("action_type", "none")) if choices else "none"


def _record_meta(record: Any, split: str) -> dict[str, Any]:
    source = record.source_metadata or {}
    terminal = record.terminal_result or {}
    return {"decision_id": record.decision_id, "state_id": record.state_id, "episode_id": record.episode_id,
            "acting_seat": record.acting_seat, "replay_step": record.replay_step, "style_id": record.style_id,
            "split": split, "own_archetype": record.own_archetype or "unknown", "opponent_archetype": record.opponent_archetype or "unknown",
            "terminal_win_loss": str(terminal.get("seat_reward", "unknown")), "proxy_confidence": str(source.get("gold_proxy_confidence", "unknown")),
            "turn_band": _turn_band(record.turn), "selection_context": str(record.chosen_canonical_action.get("selection_context")),
            "action_type": _action_type(record), "sampling_stratum": selection_stratum(record),
            "source_replay_path": source.get("source_replay_path"), "replay_sha256": source.get("replay_sha256")}


def _resolve_replay(path: str, dataset_dir: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists(): return candidate
    for root in (dataset_dir, dataset_dir.parent, Path.cwd()):
        probe = root / candidate
        if probe.exists(): return probe
    raise FileNotFoundError(path)


def _group_metrics(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    result = {}
    for value in sorted({str(row.get(key, "unknown")) for row in rows}):
        subset = [row for row in rows if str(row.get(key, "unknown")) == value]
        valid = [row for row in subset if "error" not in row]
        rankable = [row for row in valid if bool(row.get("rule_rank_available"))]
        result[value] = {"count": len(subset), "semantic_equal": sum(bool(row.get("semantic_equal")) for row in subset),
                         "gold_top3": sum(bool(row.get("gold_top3")) for row in subset),
                         "gold_top10": sum(bool(row.get("gold_top10")) for row in subset),
                         "gold_generated": sum(bool(row.get("gold_generated")) for row in subset),
                         "valid_count": len(valid), "rankable_count": len(rankable),
                         "unranked_count": len(valid) - len(rankable),
                         "errors": len(subset) - len(valid)}
    return result


def _summary_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if "error" not in row]
    rankable = [row for row in valid if bool(row.get("rule_rank_available"))]
    return {
        "count": len(rows),
        "valid_count": len(valid),
        "rankable_count": len(rankable),
        "unranked_count": len(valid) - len(rankable),
        "errors": len(rows) - len(valid),
        "semantic_equal": sum(bool(row.get("semantic_equal")) for row in valid),
        "semantic_equal_rate": 0.0 if not valid else sum(bool(row.get("semantic_equal")) for row in valid) / len(valid),
        "gold_top3": sum(bool(row.get("gold_top3")) for row in rankable),
        "gold_top3_rate": 0.0 if not rankable else sum(bool(row.get("gold_top3")) for row in rankable) / len(rankable),
        "gold_top10": sum(bool(row.get("gold_top10")) for row in rankable),
        "gold_top10_rate": 0.0 if not rankable else sum(bool(row.get("gold_top10")) for row in rankable) / len(rankable),
        "gold_generated": sum(bool(row.get("gold_generated")) for row in valid),
        "gold_generated_rate": 0.0 if not valid else sum(bool(row.get("gold_generated")) for row in valid) / len(valid),
    }


def _seed_rule_agent(agent: Any, experiment_seed: str, episode_id: str, seat: int) -> int:
    payload = _json({"experiment_seed": str(experiment_seed), "episode_id": str(episode_id), "seat": int(seat)})
    value = int.from_bytes(blake2b(payload, digest_size=8).digest(), "big")
    seen: set[int] = set()
    for name in ("random", "_residual_random"):
        rng = getattr(agent.module, name, None)
        if hasattr(rng, "seed") and id(rng) not in seen:
            rng.seed(value)
            seen.add(id(rng))
    return value


def run_gold_disagreement_audit(dataset_dir: str | Path, engine_dir: str | Path, baseline_map: Mapping[str, str], output_dir: str | Path, *, seed: str = "0", target_count: int = 512, max_complete_actions: int = 4096) -> dict[str, Any]:
    if int(max_complete_actions) < 1: raise ValueError("max_complete_actions must be positive")
    root, output = Path(dataset_dir), Path(output_dir)
    verified = verify_gold_replay_dataset(root)
    membership = {str(item["item_id"]): str(item["split"]) for item in verified["split_manifest"]["items"]}
    eligible = [record for record in verified["records"] if membership[record.decision_id] in DEFAULT_SOURCES]
    baseline_map = {str(key): str(value) for key, value in baseline_map.items()}
    manifest = make_sample_manifest(eligible, target_count=target_count, seed=str(seed), dataset_hash=_file_hash(root / "decision_records.jsonl"),
                                    split_hash=_file_hash(root / "split_manifest.json"), baseline_map_hash=_canonical_sha256(baseline_map))
    write_once_json(output / "sample_manifest.json", manifest)
    selected = {item.decision_id: item for item in eligible if item.decision_id in set(manifest["decision_ids"])}
    from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent
    ensure_engine_on_path(Path(engine_dir))
    by_episode_seat: dict[tuple[str, int], list[Any]] = defaultdict(list)
    for record in eligible: by_episode_seat[(record.episode_id, record.acting_seat)].append(record)
    rows: list[dict[str, Any]] = []
    errors: Counter[str] = Counter()
    for (episode, seat), records in sorted(by_episode_seat.items()):
        wanted = {record.replay_step: record for record in records if record.decision_id in selected}
        if not wanted: continue
        record0 = next(iter(wanted.values()))
        episode_rows: list[dict[str, Any]] = []
        completed_ids: set[str] = set()
        try:
            replay_path = _resolve_replay(str(record0.source_metadata.get("source_replay_path", "")), root)
            if _file_hash(replay_path) != str(record0.source_metadata.get("replay_sha256", "")): raise ValueError("replay checksum mismatch")
            replay = json.loads(replay_path.read_text(encoding="utf-8"))
            decisions = list(iter_replay_decisions(replay, seats=[seat]))
            agent_dir = baseline_map.get(record0.own_archetype) or baseline_map.get("*")
            if not agent_dir: raise ValueError(f"no baseline agent for archetype {record0.own_archetype!r}")
            agent = load_agent(Path(agent_dir), "gold_audit_%s_%s" % (episode, seat))
            agent_seed = _seed_rule_agent(agent, str(seed), episode, seat)
            seen_steps: set[int] = set()
            last_wanted_step = max(wanted)
            for decision in decisions:
                if decision.replay_step > last_wanted_step:
                    break
                baseline = agent(dict(decision.observation))
                record = wanted.get(decision.replay_step)
                if record is None: continue
                seen_steps.add(decision.replay_step)
                if decision.canonical_action.to_dict() != record.chosen_canonical_action: raise ValueError("stored chosen canonical action mismatch")
                reconstructed = ReplayDecisionRecord.from_observation(
                    decision.observation,
                    decision.raw_action,
                    episode_id=record.episode_id,
                    submission_id=record.submission_id,
                    style_id=record.style_id,
                    decision_step=record.decision_step,
                    replay_step=record.replay_step,
                    acting_seat=record.acting_seat,
                    own_archetype=record.own_archetype,
                    opponent_archetype=record.opponent_archetype,
                    public_history=decision.public_history,
                    private_action_history=decision.private_action_history,
                    terminal_result=record.terminal_result,
                    timestamp=record.timestamp,
                    source_metadata=record.source_metadata,
                    label_source=record.label_source,
                )
                if reconstructed.state_id != record.state_id or reconstructed.decision_id != record.decision_id:
                    raise ValueError("stored acting-player state or decision ID mismatch")
                rank_available = callable(getattr(agent.module, "score_option", None))
                if rank_available:
                    converted, scores, _reasons = score_options(agent, dict(decision.observation))
                else:
                    converter = getattr(agent.module, "to_observation_class", None)
                    if not callable(converter):
                        raise AttributeError("rule module exposes neither score_option nor to_observation_class")
                    converted = converter(dict(decision.observation))
                    scores = [0.0] * len(list(converted.select.option or []))
                ranked = rank_complete_actions(converted, scores, baseline, list(decision.raw_action), max_complete_actions=max_complete_actions)
                if not rank_available:
                    ranked["gold_rank"] = None
                    ranked["baseline_rank"] = None
                gold = decision.canonical_action.to_dict(); rule = canonicalize_prompt_action(converted, baseline).to_dict()
                row = _record_meta(record, membership[record.decision_id])
                row.update({key: value for key, value in ranked.items() if key != "ranked"})
                row.update({"gold_semantic_id": ranked["gold_semantic_id"], "semantic_equal": ranked["gold_semantic_id"] == ranked["baseline_semantic_id"],
                            "rule_rank_available": rank_available,
                            "rule_rank_unavailable_reason": None if rank_available else "score_option API unavailable",
                            "gold_top3": None if not rank_available else bool(ranked["gold_rank"] and ranked["gold_rank"] <= 3),
                            "gold_top10": None if not rank_available else bool(ranked["gold_rank"] and ranked["gold_rank"] <= 10),
                            "gold_outside_top3": None if not rank_available else not bool(ranked["gold_rank"] and ranked["gold_rank"] <= 3),
                            "gold_outside_top10": None if not rank_available else not bool(ranked["gold_rank"] and ranked["gold_rank"] <= 10),
                            "gold_not_generated": not ranked["gold_generated"], "rule_agent_seed": agent_seed,
                            "differences": _semantic_difference(gold, rule)})
                episode_rows.append(row)
                completed_ids.add(record.decision_id)
            for replay_step, record in wanted.items():
                if replay_step not in seen_steps:
                    errors["MissingReplayDecision"] += 1
                    episode_rows.append({**_record_meta(record, membership[record.decision_id]), "error": "MissingReplayDecision: selected replay step was not reconstructed"})
                    completed_ids.add(record.decision_id)
        except Exception as error:  # retain a deterministic auditable failure row for every requested decision.
            message = "%s: %s" % (type(error).__name__, error)
            unprocessed = [record for record in wanted.values() if record.decision_id not in completed_ids]
            errors[type(error).__name__] += len(unprocessed)
            for record in unprocessed:
                episode_rows.append({**_record_meta(record, membership[record.decision_id]), "error": message})
                completed_ids.add(record.decision_id)
        rows.extend(episode_rows)
    rows.sort(key=lambda row: str(row["decision_id"]))
    row_ids = [str(row["decision_id"]) for row in rows]
    if len(row_ids) != len(manifest["decision_ids"]) or len(set(row_ids)) != len(row_ids) or set(row_ids) != set(manifest["decision_ids"]):
        raise RuntimeError("audit did not produce exactly one row per frozen decision ID")
    rows_bytes = b"".join(_json(row) for row in rows)
    rows_path = output / "rows.jsonl"
    if rows_path.exists() and rows_path.read_bytes() != rows_bytes: raise FileExistsError(f"refusing to replace non-identical artifact: {rows_path}")
    output.mkdir(parents=True, exist_ok=True)
    if not rows_path.exists(): rows_path.write_bytes(rows_bytes)
    metrics = {key: _group_metrics(rows, key) for key in ("own_archetype", "opponent_archetype", "style_id", "split", "acting_seat", "terminal_win_loss", "proxy_confidence", "turn_band", "selection_context", "action_type", "sampling_stratum")}
    report = {"schema_version": SCHEMA_VERSION, "rows": len(rows), "errors": dict(sorted(errors.items())),
              "truncated": sum(row.get("scope") == "truncated" for row in rows), "same_state_cross_style": same_state_agreement(rows), "metrics": metrics,
              "overall": _summary_metrics(rows),
              "sample_manifest_blake2b": manifest["manifest_blake2b"], "rows_sha256": sha256(rows_bytes).hexdigest()}
    write_once_json(output / "report.json", report)
    binding = {"schema_version": SCHEMA_VERSION, "sample_manifest_sha256": _file_hash(output / "sample_manifest.json"), "rows_sha256": _file_hash(rows_path), "report_sha256": _file_hash(output / "report.json"),
               "dataset_manifest_sha256": _file_hash(root / "dataset_manifest.json"), "split_manifest_sha256": _file_hash(root / "split_manifest.json"), "baseline_map_canonical_sha256": _canonical_sha256(baseline_map),
               "baseline_files": {key: {name: _file_hash(Path(value) / name) for name in ("main.py", "deck.csv") if (Path(value) / name).is_file()} for key, value in sorted(baseline_map.items())},
               "implementation_files_sha256": _implementation_hashes(),
               "python": sys.version, "platform": platform.platform(), "command": list(sys.argv),
               "config": {"seed": str(seed), "target_count": target_count, "max_complete_actions": max_complete_actions}}
    binding["manifest_blake2b"] = _hash(binding)
    write_once_json(output / "checksum_manifest.json", binding)
    return {"sampled": len(manifest["decision_ids"]), "rows": len(rows), "errors": sum(errors.values()), "truncated": report["truncated"], "output_dir": str(output)}
