"""Leakage-safe collector for fixed Gold replay distillation decisions."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from hashlib import blake2b, sha256
import json
import math
from pathlib import Path
import platform
import random
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

from .belief import sample_search_guess
from .canonical_actions import canonicalize_prompt_action
from .gold_disagreement_audit import DEFAULT_SOURCES, rank_complete_actions
from .gold_disagreement_verify import verify_gold_disagreement_audit
from .gold_replay_dataset import verify_gold_replay_dataset
from .probe_search import score_options
from .replay_records import ReplayDecisionRecord
from .replay_reconstruction import iter_replay_decisions


SCHEMA_VERSION = "gold_oracle_states.v1"
EXACT_COMPLETE_ACTION_CAP = 4096
_CANDIDATE_SET_NAMES = (
    "baseline", "rule_top3", "rule_topK", "rule_diverse", "rule_plus_gold",
)


def _json(value: Any, pretty: bool = False) -> bytes:
    return (json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n").encode("ascii")


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256(_json(value)).hexdigest()


def deck_signature(deck: Iterable[int]) -> str:
    return canonical_sha256(sorted(int(card_id) for card_id in deck))


def write_once(path: Path, value: Any, *, pretty: bool = True) -> None:
    data = _json(value, pretty)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def make_selection_manifest(
    ids: Sequence[str], inputs: Mapping[str, Path], config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "decision_ids": sorted(str(identifier) for identifier in ids),
        "inputs": {
            name: {"path": str(path), "sha256": file_sha256(path)}
            for name, path in sorted(inputs.items())
        },
        "config": dict(config),
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def validate_selection_manifest(value: Mapping[str, Any]) -> None:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("manifest_sha256") != canonical_sha256(unsigned)
    ):
        raise ValueError("selection manifest checksum does not validate")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def select_audited_records(
    records: Sequence[ReplayDecisionRecord],
    membership: Mapping[str, str],
    audit_rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
) -> dict[str, ReplayDecisionRecord]:
    requested = set(ids)
    if len(requested) != len(ids):
        raise ValueError("decision IDs must be unique")
    audit = {str(row.get("decision_id")): row for row in audit_rows}
    output = {record.decision_id: record for record in records if record.decision_id in requested}
    if set(output) != requested:
        raise ValueError("requested decision is absent from dataset")
    for identifier, record in output.items():
        row = audit.get(identifier)
        if membership.get(identifier) not in DEFAULT_SOURCES:
            raise ValueError("blind or unsupported split requested: %s" % identifier)
        if (
            row is None
            or row.get("error")
            or row.get("semantic_equal")
            or row.get("scope") != "exact"
            or not row.get("rule_rank_available")
        ):
            raise ValueError(
                "decision is not an available non-equal exact audit row: %s" % identifier,
            )
        if not (record.own_archetype or "").lower().startswith("archaludon"):
            raise ValueError("decision actor is not Archaludon: %s" % identifier)
    return output


def _action_type_tuple(action: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(sorted(
        int(selection.get("action_type", -1))
        for selection in action.get("selections", [])
    ))


def candidate_sets(
    ranked: Mapping[str, Any],
    baseline_action: Sequence[int],
    gold_action: Sequence[int],
    observation: Any,
    *,
    top_k: int,
    max_diverse: int,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    if ranked.get("scope") != "exact":
        raise ValueError("truncated complete actions are forbidden")
    baseline_id = canonicalize_prompt_action(observation, baseline_action).stable_id
    gold_id = canonicalize_prompt_action(observation, gold_action).stable_id
    candidates = []
    for row in ranked["ranked"]:
        tags = []
        if row["semantic_id"] == baseline_id:
            tags.append("baseline")
        if row["semantic_id"] == gold_id:
            tags.append("gold")
        candidates.append({
            "semantic_id": row["semantic_id"],
            "canonical": row["canonical"],
            "additive_rule_score": float(row["score"]),
            "source_tags": tags,
        })
    by_id = {candidate["semantic_id"]: candidate for candidate in candidates}
    if baseline_id not in by_id or gold_id not in by_id:
        raise ValueError("baseline or Gold semantic action is absent from exact ranking")

    top3 = list(dict.fromkeys(
        [baseline_id] + [candidate["semantic_id"] for candidate in candidates[:3]],
    ))
    top = [candidate["semantic_id"] for candidate in candidates[:top_k]]
    top_with_baseline = list(dict.fromkeys([baseline_id] + top))
    if len(top_with_baseline) > max_diverse:
        raise ValueError("rule_topK exceeds max_diverse")

    diverse = list(top_with_baseline)
    seen_types = {_action_type_tuple(by_id[identifier]["canonical"]) for identifier in diverse}
    diversity_added = []
    for candidate in candidates:
        if len(diverse) >= max_diverse:
            break
        signature = _action_type_tuple(candidate["canonical"])
        if signature not in seen_types:
            diverse.append(candidate["semantic_id"])
            diversity_added.append(candidate["semantic_id"])
            seen_types.add(signature)

    sets = {
        "baseline": [baseline_id],
        "rule_top3": top3,
        "rule_topK": top_with_baseline,
        "rule_diverse": diverse,
        "rule_plus_gold": list(dict.fromkeys(diverse + [gold_id])),
    }
    for name, identifiers in sets.items():
        for identifier in identifiers:
            by_id[identifier]["source_tags"] = sorted(set(
                by_id[identifier]["source_tags"] + [name],
            ))
    for identifier in diversity_added:
        by_id[identifier]["source_tags"] = sorted(set(
            by_id[identifier]["source_tags"] + ["action_type_diverse"],
        ))
    return candidates, sets


def rank_target_actions(
    observation: Any,
    scores: Sequence[float],
    baseline_action: Sequence[int],
    gold_action: Sequence[int],
) -> dict[str, Any]:
    return rank_complete_actions(
        observation,
        scores,
        baseline_action,
        gold_action,
        max_complete_actions=EXACT_COMPLETE_ACTION_CAP,
    )


def _visible_cards(safe_observation: Mapping[str, Any]) -> Counter[int]:
    result: Counter[int] = Counter()
    for opponent in safe_observation.get("opponents", []):
        for zone in ("active", "bench", "discard", "lostZone"):
            for card in opponent.get(zone, []) or []:
                if isinstance(card, Mapping) and isinstance(card.get("id"), int):
                    result[int(card["id"])] += 1
                energies = card.get("energyCards", []) if isinstance(card, Mapping) else []
                for energy in energies:
                    if isinstance(energy, Mapping) and isinstance(energy.get("id"), int):
                        result[int(energy["id"])] += 1
                tools = card.get("tools", []) if isinstance(card, Mapping) else []
                for tool in tools:
                    if isinstance(tool, Mapping) and isinstance(tool.get("id"), int):
                        result[int(tool["id"])] += 1
    return result


def _read_deck_file(path: Path) -> list[int]:
    deck = [
        int(line.strip())
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(deck) != 60:
        raise ValueError("%s has %d cards; expected 60" % (path, len(deck)))
    return deck


def _catalog_descriptor(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "archetype": entry["archetype"],
        "signature": entry["signature"],
        "deck_sha256": entry["deck_sha256"],
        "sources": entry["sources"],
    }


def build_catalog(
    inventory_csv: Path,
    extra_decks: Mapping[str, Sequence[Path]],
    allowed_episodes: set[str],
    excluded_seats: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    def add(archetype: str, deck: Sequence[int], source: Mapping[str, Any]) -> None:
        values = sorted(int(card_id) for card_id in deck)
        if len(values) != 60:
            raise ValueError("catalog deck must contain exactly 60 cards")
        signature = deck_signature(values)
        key = (str(archetype), signature)
        entry = grouped.setdefault(key, {
            "archetype": str(archetype),
            "decklist": values,
            "signature": signature,
            "deck_sha256": canonical_sha256(values),
            "sources": [],
        })
        normalized_source = dict(source)
        if normalized_source not in entry["sources"]:
            entry["sources"].append(normalized_source)

    with inventory_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (str(row["episode_id"]), int(row["player_index"]))
            if key in excluded_seats or key[0] not in allowed_episodes:
                continue
            deck = [int(card_id) for card_id in row["deck"].split()]
            add(str(row["archetype"]), deck, {
                "source_kind": "inventory",
                "source_path": str(inventory_csv),
                "source_row_id": str(row.get("deck_id") or "%s_p%s" % key),
                "source_sha256": str(row.get("deck_sha256") or deck_signature(deck)),
            })
    for archetype, paths in sorted(extra_decks.items()):
        for path in paths:
            deck = _read_deck_file(path)
            add(str(archetype), deck, {
                "source_kind": "extra_public_deck",
                "source_path": str(path),
                "source_row_id": None,
                "source_sha256": file_sha256(path),
            })
    for entry in grouped.values():
        entry["sources"].sort(key=lambda item: _json(item))
    return sorted(grouped.values(), key=lambda item: (item["archetype"], item["signature"]))


def compatible_decks(
    catalog: Sequence[Mapping[str, Any]], archetype: str, required: Counter[int],
) -> list[dict[str, Any]]:
    output = []
    for entry in catalog:
        if entry.get("archetype") != archetype:
            continue
        counts = Counter(int(card_id) for card_id in entry["decklist"])
        if len(entry["decklist"]) == 60 and all(
            counts[card_id] >= amount for card_id, amount in required.items()
        ):
            output.append(dict(entry))
    return output


def _preflight_one(
    observation: Any,
    own_deck: Sequence[int],
    entry: Mapping[str, Any],
    seed: str,
) -> str | None:
    try:
        sample_search_guess(
            observation,
            own_deck,
            entry["decklist"],
            random.Random("%s:%s" % (seed, entry["signature"])),
        )
    except (TypeError, ValueError) as error:
        return "%s: %s" % (type(error).__name__, error)
    return None


def _selection_priority(entry: Mapping[str, Any], seed: str) -> tuple[str, str]:
    return (
        canonical_sha256({"seed": str(seed), "signature": entry["signature"]}),
        str(entry["signature"]),
    )


def _source_diversity_key(entry: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({str(source["source_kind"]) for source in entry["sources"]}))


def select_known_entries(
    entries: Sequence[Mapping[str, Any]], max_known: int, seed: str,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        buckets[_source_diversity_key(entry)].append(dict(entry))
    for values in buckets.values():
        values.sort(key=lambda item: _selection_priority(item, seed))
    order = sorted(
        buckets,
        key=lambda key: canonical_sha256({"seed": str(seed), "source_kinds": key}),
    )
    selected = []
    while order and len(selected) < max_known:
        next_order = []
        for key in order:
            if buckets[key] and len(selected) < max_known:
                selected.append(buckets[key].pop(0))
            if buckets[key]:
                next_order.append(key)
        order = next_order
    return selected


def _toward_donor_candidates(
    base: Mapping[str, Any],
    donor: Mapping[str, Any],
    required: Counter[int],
) -> Iterable[tuple[list[int], int]]:
    deck = list(base["decklist"])
    counts = Counter(deck)
    donor_counts = Counter(int(card_id) for card_id in donor["decklist"])
    for swap_count in range(1, 5):
        additions = sorted(
            card_id for card_id, amount in donor_counts.items()
            if amount > counts[card_id]
        )
        removable = sorted(
            card_id for card_id, amount in counts.items()
            if amount > required[card_id] and amount > donor_counts[card_id]
        )
        if not additions or not removable:
            break
        remove = removable[0]
        add = additions[0]
        deck.remove(remove)
        deck.append(add)
        counts[remove] -= 1
        counts[add] += 1
        if all(counts[card_id] >= amount for card_id, amount in required.items()):
            yield sorted(deck), swap_count


def _make_synthetic(
    all_same_archetype: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
    required: Counter[int],
    observation: Any | None,
    own_deck: Sequence[int] | None,
    seed: str,
) -> tuple[dict[str, Any] | None, str, list[dict[str, Any]]]:
    catalog_signatures = {str(entry["signature"]) for entry in all_same_archetype}
    selected_signatures = {str(entry["signature"]) for entry in selected}
    donors = [
        entry for entry in all_same_archetype
        if entry["signature"] not in selected_signatures
    ]
    donors.sort(key=lambda item: _selection_priority(item, seed + ":donor"))
    bases = sorted(selected, key=lambda item: _selection_priority(item, seed + ":base"))
    attempts = []
    saw_preflight_failure = False
    for base in bases:
        for donor in donors:
            produced = False
            for deck, swaps in _toward_donor_candidates(base, donor, required):
                signature = deck_signature(deck)
                if signature in catalog_signatures:
                    continue
                produced = True
                candidate = {
                    "kind": "synthetic_unknown",
                    "archetype": base["archetype"],
                    "decklist": deck,
                    "signature": signature,
                    "deck_sha256": canonical_sha256(deck),
                    "sources": [{
                        "source_kind": "synthetic_donor_swap",
                        "source_path": None,
                        "source_row_id": None,
                        "source_sha256": canonical_sha256({
                            "base": base["signature"],
                            "donor": donor["signature"],
                            "swaps": swaps,
                        }),
                    }],
                    "base_signature": base["signature"],
                    "donor_signature": donor["signature"],
                    "swap_count": swaps,
                }
                reason = None
                if observation is not None and own_deck is not None:
                    reason = _preflight_one(observation, own_deck, candidate, seed + ":synthetic")
                attempts.append({
                    "base_signature": base["signature"],
                    "donor": _catalog_descriptor(donor),
                    "candidate_signature": signature,
                    "swap_count": swaps,
                    "status": "accepted" if reason is None else "rejected_preflight",
                    "reason": reason,
                })
                if reason is None:
                    return candidate, "created", attempts
                saw_preflight_failure = True
            if not produced:
                attempts.append({
                    "base_signature": base["signature"],
                    "donor": _catalog_descriptor(donor),
                    "candidate_signature": None,
                    "swap_count": 0,
                    "status": "no_novel_candidate",
                    "reason": "no <=4-swap candidate outside all catalog signatures",
                })
    if not donors:
        return None, "no_unselected_donor", attempts
    if saw_preflight_failure:
        return None, "rejected_preflight", attempts
    return None, "no_novel_candidate", attempts


def build_beliefs(
    catalog: Sequence[Mapping[str, Any]],
    archetype: str,
    required: Counter[int],
    *,
    max_known: int,
    unknown_mass: float,
    observation: Any | None = None,
    own_deck: Sequence[int] | None = None,
    preflight_seed: str = "0",
) -> dict[str, Any]:
    same_archetype = [dict(entry) for entry in catalog if entry.get("archetype") == archetype]
    compatible = compatible_decks(same_archetype, archetype, required)
    accepted = []
    rejected = []
    status_by_signature: dict[str, dict[str, Any]] = {}
    for entry in compatible:
        reason = None
        if observation is not None and own_deck is not None:
            reason = _preflight_one(observation, own_deck, entry, preflight_seed)
        descriptor = _catalog_descriptor(entry)
        if reason is None:
            accepted.append(entry)
            status_by_signature[entry["signature"]] = {"status": "accepted", "reason": None}
        else:
            rejected.append({**descriptor, "reason": reason})
            status_by_signature[entry["signature"]] = {
                "status": "rejected_preflight", "reason": reason,
            }
    if not accepted:
        raise ValueError("known=0 same-archetype hypotheses after preflight")

    selected = select_known_entries(accepted, max_known, preflight_seed)
    selected_signatures = {entry["signature"] for entry in selected}
    synthetic, synthetic_status, synthetic_attempts = _make_synthetic(
        same_archetype,
        selected,
        required,
        observation,
        own_deck,
        preflight_seed,
    )
    hypotheses = [
        {
            "kind": "known",
            "archetype": entry["archetype"],
            "decklist": entry["decklist"],
            "signature": entry["signature"],
            "deck_sha256": entry["deck_sha256"],
            "sources": entry["sources"],
        }
        for entry in selected
    ]
    if synthetic is not None:
        hypotheses.append(synthetic)

    unknown = float(unknown_mass) if synthetic is not None else 0.0
    known_mass = (1.0 - unknown) / len(selected)
    for hypothesis in hypotheses:
        hypothesis["posterior_mass"] = (
            unknown if hypothesis["kind"] == "synthetic_unknown" else known_mass
        )
    entropy = -sum(
        hypothesis["posterior_mass"] * math.log(hypothesis["posterior_mass"])
        for hypothesis in hypotheses
        if hypothesis["posterior_mass"]
    )

    catalog_results = []
    compatible_signatures = {entry["signature"] for entry in compatible}
    for entry in same_archetype:
        if entry["signature"] not in compatible_signatures:
            status = {"status": "board_incompatible", "reason": "visible count mismatch"}
        else:
            status = status_by_signature[entry["signature"]]
        if entry["signature"] in selected_signatures:
            status = {"status": "selected_known", "reason": None}
        catalog_results.append({**_catalog_descriptor(entry), **status})

    counts = {
        "all_catalog_count": len(same_archetype),
        "board_compatible_count": len(compatible),
        "preflight_accepted_count": len(accepted),
        "preflight_rejected_count": len(rejected),
        "selected_known_count": len(selected),
        "synthetic_donor_count": len(same_archetype) - len(selected_signatures),
        "synthetic_attempt_count": len(synthetic_attempts),
        "synthetic_success_count": int(synthetic is not None),
    }
    return {
        "archetype": archetype,
        "visible_requirements": dict(sorted(required.items())),
        "hypotheses": hypotheses,
        "catalog_results": catalog_results,
        "preflight_rejections": rejected,
        "synthetic_status": synthetic_status,
        "synthetic_attempts": synthetic_attempts,
        "unknown_mass": unknown,
        "top1_mass": max(hypothesis["posterior_mass"] for hypothesis in hypotheses),
        "entropy": entropy,
        "counts": counts,
    }


_BANNED_EXACT_KEYS = {
    "search_begin_input", "terminal_result", "gold_rank", "gold_score",
    "leaderboard_score",
}
_BANNED_KEY_SEGMENTS = {
    "terminal", "future", "search", "raw", "serial", "index", "ordinal",
    "winner", "reward", "outcome", "leaderboard",
}


def _key_segments(key: Any) -> list[str]:
    with_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key))
    return [segment for segment in re.split(r"[^A-Za-z0-9]+", with_boundaries.lower()) if segment]


def validate_no_leakage(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            segments = _key_segments(key)
            if normalized in _BANNED_EXACT_KEYS or any(
                segment in _BANNED_KEY_SEGMENTS for segment in segments
            ):
                raise ValueError("leakage field: %s%s" % (path, key))
            validate_no_leakage(item, path + str(key) + ".")
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_no_leakage(item, path)


def inventory_actor_deck(
    inventory_csv: Path, episode_id: str, actor_seat: int,
) -> tuple[list[int], dict[str, Any]]:
    target = (str(episode_id), int(actor_seat))
    with inventory_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (str(row["episode_id"]), int(row["player_index"]))
            if key != target:
                continue
            deck = [int(card_id) for card_id in row["deck"].split()]
            return deck, {
                "source_path": str(inventory_csv),
                "source_row_id": str(row.get("deck_id") or "%s_p%s" % target),
                "source_sha256": str(row.get("deck_sha256") or deck_signature(deck)),
            }
    raise ValueError("missing actor inventory row: %s seat %d" % target)


def replay_actor_initial_deck(replay: Mapping[str, Any], actor_seat: int) -> list[int]:
    """Read only the actor element; the target opponent element is never inspected."""
    for step in replay.get("steps", []):
        if not isinstance(step, list) or actor_seat >= len(step):
            continue
        actor_record = step[actor_seat]
        action = actor_record.get("action") if isinstance(actor_record, Mapping) else None
        if (
            isinstance(action, list)
            and len(action) == 60
            and all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in action)
        ):
            return list(action)
    raise ValueError("replay has no actor initial 60-card deck")


def verified_actor_deck(
    replay: Mapping[str, Any], inventory_csv: Path, episode_id: str, actor_seat: int,
) -> tuple[list[int], dict[str, Any]]:
    replay_deck = replay_actor_initial_deck(replay, actor_seat)
    inventory_deck, inventory_source = inventory_actor_deck(
        inventory_csv, episode_id, actor_seat,
    )
    if replay_deck != inventory_deck:
        raise ValueError("actor replay deck does not exactly match inventory")
    if len(replay_deck) != 60:
        raise ValueError("actor deck must contain exactly 60 cards")
    return replay_deck, inventory_source


def portable_inventory_source(
    source: Mapping[str, Any], inventory_csv: Path, workspace: Path,
) -> dict[str, Any]:
    result = dict(source)
    resolved = inventory_csv.resolve()
    try:
        relative = resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("inventory source escapes workspace") from error
    result["source_path"] = str(relative).replace("\\", "/")
    return result


def verify_inventory_source_binding(
    stored: Mapping[str, Any],
    current: Mapping[str, Any],
    bound_relative_path: str,
) -> None:
    required = {"source_path", "source_row_id", "source_sha256"}
    if set(stored) != required or set(current) != required:
        raise ValueError("inventory source schema mismatch")
    if (
        stored["source_row_id"] != current["source_row_id"]
        or stored["source_sha256"] != current["source_sha256"]
    ):
        raise ValueError("inventory source row or deck hash mismatch")

    bound = str(bound_relative_path).replace("\\", "/").strip("/")
    if not bound or bound.startswith("../") or "/../" in ("/" + bound + "/"):
        raise ValueError("invalid bound inventory path")

    def matches(value: Any) -> bool:
        normalized = str(value).replace("\\", "/").rstrip("/")
        return normalized == bound or normalized.endswith("/" + bound)

    if not matches(stored["source_path"]) or not matches(current["source_path"]):
        raise ValueError("inventory source path does not match bound input")


def _selection_inputs(
    dataset_dir: Path,
    audit_dir: Path,
    baseline_dir: Path,
    engine_dir: Path,
    inventory_csv: Path,
    extra_decks: Mapping[str, Sequence[Path]],
    workspace: Path,
) -> dict[str, Path]:
    inputs = {
        "dataset_manifest": dataset_dir / "dataset_manifest.json",
        "split_manifest": dataset_dir / "split_manifest.json",
        "decision_records": dataset_dir / "decision_records.jsonl",
        "audit_checksum_manifest": audit_dir / "checksum_manifest.json",
        "audit_sample_manifest": audit_dir / "sample_manifest.json",
        "inventory": inventory_csv,
        "baseline_main": baseline_dir / "main.py",
        "baseline_deck": baseline_dir / "deck.csv",
        "engine_api": engine_dir / "cg" / "api.py",
        "engine_dll": engine_dir / "cg" / "cg.dll",
        "collector_module": Path(__file__),
        "collector_cli": workspace / "tools" / "build_gold_oracle_states.py",
    }
    ordinal = 0
    for archetype, paths in sorted(extra_decks.items()):
        for path in paths:
            inputs["extra_deck:%03d:%s" % (ordinal, archetype)] = path
            ordinal += 1
    return inputs


def _extra_path_config(extra_decks: Mapping[str, Sequence[Path]]) -> dict[str, list[str]]:
    return {
        archetype: [str(path) for path in paths]
        for archetype, paths in sorted(extra_decks.items())
    }


def _coverage(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        name: sum(bool(item["candidate_sets"][name]) for item in items)
        for name in _CANDIDATE_SET_NAMES
    }


_STATE_KEYS = {
    "schema_version", "decision_id", "state_id", "episode_id", "acting_seat",
    "source_replay_path", "replay_sha256", "split", "style_id", "submission_id",
    "replay_step", "safe_observation", "known_private_info", "public_history",
    "legal_semantic_options", "current_metadata", "candidates", "candidate_sets",
    "gold_incremental", "own_deck", "belief",
}


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain a JSON object" % path)
    return value


def _resolve_bound_path(path: str, workspace: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("bound input path escapes workspace: %s" % path) from error
    return resolved


def _verify_self_hash(value: Mapping[str, Any], label: str) -> None:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    if value.get("manifest_sha256") != canonical_sha256(unsigned):
        raise ValueError("%s self-hash mismatch" % label)


def _verify_state_candidates(state: Mapping[str, Any], config: Mapping[str, Any]) -> None:
    candidates = state.get("candidates")
    sets = state.get("candidate_sets")
    if not isinstance(candidates, list) or not isinstance(sets, dict):
        raise ValueError("invalid candidate payload")
    identifiers = [candidate.get("semantic_id") for candidate in candidates if isinstance(candidate, Mapping)]
    if (
        len(identifiers) != len(candidates)
        or not all(isinstance(identifier, str) and identifier for identifier in identifiers)
        or len(identifiers) != len(set(identifiers))
    ):
        raise ValueError("candidate semantic IDs must be unique non-empty strings")
    for candidate in candidates:
        if set(candidate) != {
            "semantic_id", "canonical", "additive_rule_score", "source_tags",
        }:
            raise ValueError("candidate schema mismatch")
        canonical = candidate["canonical"]
        if not isinstance(canonical, Mapping):
            raise ValueError("candidate canonical action must be an object")
        encoded = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")
        if candidate["semantic_id"] != blake2b(encoded, digest_size=32).hexdigest():
            raise ValueError("candidate semantic ID does not match canonical action")
        try:
            score = float(candidate["additive_rule_score"])
        except (TypeError, ValueError) as error:
            raise ValueError("invalid additive rule score") from error
        tags = candidate["source_tags"]
        if (
            not math.isfinite(score)
            or not isinstance(tags, list)
            or len(tags) != len(set(tags))
            or not all(isinstance(tag, str) for tag in tags)
        ):
            raise ValueError("invalid candidate score or source tags")
    candidate_ids = set(identifiers)
    if set(sets) != set(_CANDIDATE_SET_NAMES):
        raise ValueError("candidate set schema mismatch")
    for name, values in sets.items():
        if (
            not isinstance(values, list)
            or len(values) != len(set(values))
            or not set(values) <= candidate_ids
        ):
            raise ValueError("candidate set has dangling or duplicate IDs: %s" % name)
    baseline = sets["baseline"]
    if len(baseline) != 1 or baseline[0] not in sets["rule_top3"]:
        raise ValueError("baseline must be present in rule_top3")
    max_diverse = int(config.get("max_diverse_actions", -1))
    if len(sets["rule_topK"]) > max_diverse or len(sets["rule_diverse"]) > max_diverse:
        raise ValueError("bounded candidate set exceeds max_diverse_actions")
    if not set(sets["rule_topK"]) <= set(sets["rule_diverse"]):
        raise ValueError("rule_diverse must contain rule_topK")
    if not set(sets["rule_diverse"]) <= set(sets["rule_plus_gold"]):
        raise ValueError("rule_plus_gold must contain rule_diverse")


def _verify_state_belief(state: Mapping[str, Any]) -> None:
    belief = state.get("belief")
    if not isinstance(belief, Mapping):
        raise ValueError("invalid belief payload")
    hypotheses = belief.get("hypotheses")
    requirements = belief.get("visible_requirements")
    if not isinstance(hypotheses, list) or not hypotheses or not isinstance(requirements, Mapping):
        raise ValueError("belief must have hypotheses and visible requirements")
    required = Counter()
    for card_id, amount in requirements.items():
        try:
            card = int(card_id)
            count = int(amount)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid visible requirement") from error
        if count < 0:
            raise ValueError("invalid visible requirement count")
        required[card] = count
    mass = 0.0
    signatures = set()
    synthetic_count = 0
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, Mapping):
            raise ValueError("invalid hypothesis")
        deck = hypothesis.get("decklist")
        if (
            not isinstance(deck, list)
            or len(deck) != 60
            or not all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in deck)
        ):
            raise ValueError("hypothesis deck must contain 60 integer cards")
        counts = Counter(deck)
        if not all(counts[card_id] >= amount for card_id, amount in required.items()):
            raise ValueError("hypothesis violates visible requirements")
        signature = deck_signature(deck)
        if hypothesis.get("signature") != signature:
            raise ValueError("hypothesis signature mismatch")
        if hypothesis.get("deck_sha256") != canonical_sha256(deck):
            raise ValueError("hypothesis deck SHA256 mismatch")
        if signature in signatures:
            raise ValueError("duplicate belief hypothesis")
        signatures.add(signature)
        try:
            posterior = float(hypothesis["posterior_mass"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid posterior mass") from error
        if not math.isfinite(posterior) or posterior < 0 or posterior > 1:
            raise ValueError("invalid posterior mass")
        mass += posterior
        synthetic_count += int(hypothesis.get("kind") == "synthetic_unknown")
    if not math.isclose(mass, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("belief posterior mass does not sum to one")
    if synthetic_count > 1:
        raise ValueError("belief has multiple synthetic hypotheses")
    expected_unknown = sum(
        float(hypothesis["posterior_mass"])
        for hypothesis in hypotheses
        if hypothesis.get("kind") == "synthetic_unknown"
    )
    if not math.isclose(float(belief.get("unknown_mass", -1)), expected_unknown, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("belief unknown mass mismatch")


def verify_gold_oracle_states(
    output_dir: str | Path, workspace_root: str | Path | None = None,
    *, allow_implementation_drift: bool = False,
) -> dict[str, Any]:
    """Fail closed while reconnecting a runner to immutable Phase 3a states."""
    workspace = (
        Path(workspace_root).resolve()
        if workspace_root is not None
        else Path(__file__).resolve().parents[1]
    )
    output = Path(output_dir)
    if not output.is_absolute():
        output = workspace / output
    selection_path = output / "selection_manifest.json"
    states_path = output / "states.jsonl"
    manifest_path = output / "manifest.json"
    selection = _read_object(selection_path)
    validate_selection_manifest(selection)
    manifest = _read_object(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported Gold oracle manifest schema")
    _verify_self_hash(manifest, "manifest")
    if manifest.get("selection_manifest_sha256") != file_sha256(selection_path):
        raise ValueError("selection manifest file hash mismatch")
    if manifest.get("states_sha256") != file_sha256(states_path):
        raise ValueError("states file hash mismatch")

    inputs = selection.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("selection manifest has no input bindings")
    implementation_drift = []
    for name, binding in inputs.items():
        if (
            not isinstance(name, str)
            or not isinstance(binding, Mapping)
            or set(binding) != {"path", "sha256"}
            or not isinstance(binding["path"], str)
            or not isinstance(binding["sha256"], str)
        ):
            raise ValueError("invalid selection input binding")
        path = _resolve_bound_path(binding["path"], workspace)
        if not path.is_file() or file_sha256(path) != binding["sha256"]:
            if allow_implementation_drift and name in {"collector_module", "collector_cli"}:
                implementation_drift.append(name)
                continue
            raise ValueError("bound input hash mismatch: %s" % name)
    required_inputs = {
        "dataset_manifest", "split_manifest", "decision_records",
        "audit_checksum_manifest", "audit_sample_manifest", "inventory",
        "baseline_main", "baseline_deck", "engine_api", "engine_dll",
        "collector_module", "collector_cli",
    }
    if not required_inputs <= set(inputs):
        raise ValueError("selection manifest is missing required input bindings")
    configured_extra_paths = []
    extra_config = selection.get("config", {}).get("extra_decks", {})
    if not isinstance(extra_config, Mapping):
        raise ValueError("invalid extra deck config")
    for paths in extra_config.values():
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise ValueError("invalid extra deck path list")
        configured_extra_paths.extend(paths)
    bound_extra_paths = [
        str(binding["path"])
        for name, binding in inputs.items()
        if name.startswith("extra_deck:")
    ]
    if Counter(configured_extra_paths) != Counter(bound_extra_paths):
        raise ValueError("extra deck config and input bindings mismatch")
    engine_hashes = manifest.get("engine_files_sha256")
    expected_engine = {
        "cg/api.py": inputs["engine_api"]["sha256"],
        "cg/cg.dll": inputs["engine_dll"]["sha256"],
    }
    if engine_hashes != expected_engine:
        raise ValueError("manifest engine bindings mismatch selection inputs")

    source_replays = manifest.get("source_replays")
    if (
        not isinstance(source_replays, list)
        or manifest.get("source_replays_sha256") != canonical_sha256(source_replays)
    ):
        raise ValueError("source replay aggregate binding mismatch")
    replay_bindings: dict[str, str] = {}
    for binding in source_replays:
        if not isinstance(binding, Mapping) or set(binding) != {"source_replay_path", "replay_sha256"}:
            raise ValueError("invalid source replay binding")
        path = str(binding["source_replay_path"])
        checksum = str(binding["replay_sha256"])
        if path in replay_bindings:
            raise ValueError("duplicate source replay binding")
        replay_bindings[path] = checksum
        replay_path = _resolve_bound_path(path, workspace)
        if not replay_path.is_file() or file_sha256(replay_path) != checksum:
            raise ValueError("source replay current hash mismatch: %s" % path)

    try:
        lines = states_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("could not read states.jsonl") from error
    if not lines or any(not line for line in lines):
        raise ValueError("states.jsonl must be non-empty and contain no blank rows")
    states = []
    for number, line in enumerate(lines, 1):
        try:
            state = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid states.jsonl row %d" % number) from error
        if (
            not isinstance(state, dict)
            or set(state) != _STATE_KEYS
            or state.get("schema_version") != SCHEMA_VERSION
        ):
            raise ValueError("invalid state schema at row %d" % number)
        validate_no_leakage(state)
        _verify_state_candidates(state, selection.get("config", {}))
        _verify_state_belief(state)
        own = state.get("own_deck")
        deck = own.get("decklist") if isinstance(own, Mapping) else None
        if (
            not isinstance(deck, list)
            or len(deck) != 60
            or not all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in deck)
            or own.get("sha256") != canonical_sha256(deck)
        ):
            raise ValueError("own deck length or hash mismatch")
        replay_path = state.get("source_replay_path")
        if replay_bindings.get(replay_path) != state.get("replay_sha256"):
            raise ValueError("state source replay is not manifest-bound")
        if state.get("split") not in DEFAULT_SOURCES:
            raise ValueError("state uses blind or unsupported split")
        states.append(state)
    identifiers = [state["decision_id"] for state in states]
    selected_ids = selection.get("decision_ids")
    if (
        len(identifiers) != len(set(identifiers))
        or not isinstance(selected_ids, list)
        or set(identifiers) != set(selected_ids)
        or len(identifiers) != len(selected_ids)
    ):
        raise ValueError("state decision IDs do not uniquely match selection manifest")
    if manifest.get("counts", {}).get("states") != len(states):
        raise ValueError("manifest state count mismatch")
    used_replays = {
        (str(state["source_replay_path"]), str(state["replay_sha256"]))
        for state in states
    }
    if used_replays != set(replay_bindings.items()):
        raise ValueError("manifest source replay set does not exactly match states")
    by_episode: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_matchup: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    aggregate_belief_counts: Counter[str] = Counter()
    for state in states:
        by_episode[str(state["episode_id"])].append(state)
        current = state["current_metadata"]
        matchup = "%s__vs__%s" % (
            current["own_archetype"], current["opponent_archetype"],
        )
        by_matchup[matchup].append(state)
        aggregate_belief_counts.update(state["belief"]["counts"])
    expected_counts = {
        "states": len(states),
        "episodes": len(by_episode),
        "candidate_coverage": _coverage(states),
        "belief": dict(sorted(aggregate_belief_counts.items())),
        "per_episode_candidate_coverage": {
            key: _coverage(value) for key, value in sorted(by_episode.items())
        },
        "per_matchup_candidate_coverage": {
            key: _coverage(value) for key, value in sorted(by_matchup.items())
        },
    }
    if manifest.get("counts") != expected_counts:
        raise ValueError("manifest aggregate counts mismatch states")
    return {
        "states": len(states),
        "decision_ids": identifiers,
        "source_replays": len(replay_bindings),
        "states_sha256": manifest["states_sha256"],
        "implementation_drift": sorted(implementation_drift),
        "output_dir": str(output),
    }


def run_collector(
    dataset_dir: Path,
    audit_dir: Path,
    baseline_dir: Path,
    engine_dir: Path,
    inventory_csv: Path,
    output_dir: Path,
    decision_ids: Sequence[str],
    extra_decks: Mapping[str, Sequence[Path]],
    *,
    rule_top_k: int,
    max_diverse_actions: int,
    max_known_hypotheses: int,
    unknown_mass: float,
    seed: str,
) -> dict[str, Any]:
    if max_diverse_actions < rule_top_k + 1:
        raise ValueError("max_diverse_actions must be at least rule_top_k + 1")
    workspace = Path(__file__).resolve().parents[1]
    baseline_map = json.loads(
        (baseline_dir.parent / "baseline_map.json").read_text(encoding="utf-8"),
    )
    verify_gold_disagreement_audit(audit_dir, dataset_dir, baseline_map, workspace)
    verified = verify_gold_replay_dataset(dataset_dir)
    membership = {
        str(item["item_id"]): str(item["split"])
        for item in verified["split_manifest"]["items"]
    }
    selected = select_audited_records(
        verified["records"],
        membership,
        _load_jsonl(audit_dir / "rows.jsonl"),
        decision_ids,
    )
    config = {
        "rule_top_k": rule_top_k,
        "max_diverse_actions": max_diverse_actions,
        "max_known_hypotheses": max_known_hypotheses,
        "unknown_mass": unknown_mass,
        "seed": str(seed),
        "extra_decks": _extra_path_config(extra_decks),
    }
    inputs = _selection_inputs(
        dataset_dir,
        audit_dir,
        baseline_dir,
        engine_dir,
        inventory_csv,
        extra_decks,
        workspace,
    )
    selection_manifest = make_selection_manifest(decision_ids, inputs, config)
    write_once(output_dir / "selection_manifest.json", selection_manifest)

    from tools.ptcg_common import ensure_engine_on_path, load_agent
    ensure_engine_on_path(engine_dir)
    by_seat: dict[tuple[str, int], list[ReplayDecisionRecord]] = defaultdict(list)
    for record in selected.values():
        by_seat[(record.episode_id, record.acting_seat)].append(record)
    allowed_episodes = {
        record.episode_id
        for record in verified["records"]
        if membership.get(record.decision_id) in DEFAULT_SOURCES
    }

    states = []
    replay_bindings: dict[str, str] = {}
    for (episode_id, seat), wanted in sorted(by_seat.items()):
        catalog = build_catalog(
            inventory_csv,
            extra_decks,
            allowed_episodes,
            {(episode_id, 1 - seat)},
        )
        record0 = wanted[0]
        source_replay_path = str(record0.source_metadata["source_replay_path"])
        replay_path = Path(source_replay_path)
        if not replay_path.is_absolute():
            replay_path = workspace / replay_path
        expected_replay_sha256 = str(record0.source_metadata["replay_sha256"])
        if file_sha256(replay_path) != expected_replay_sha256:
            raise ValueError("replay checksum mismatch")
        previous = replay_bindings.setdefault(source_replay_path, expected_replay_sha256)
        if previous != expected_replay_sha256:
            raise ValueError("one replay path has conflicting checksums")
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        own_deck, own_inventory_source = verified_actor_deck(
            replay, inventory_csv, episode_id, seat,
        )
        own_inventory_source = portable_inventory_source(
            own_inventory_source, inventory_csv, workspace,
        )
        agent = load_agent(baseline_dir, "gold_oracle_%s_%s" % (episode_id, seat))
        targets = {record.replay_step: record for record in wanted}
        for decision in iter_replay_decisions(replay, seats=[seat]):
            baseline = agent(dict(decision.observation))
            record = targets.get(decision.replay_step)
            if record is None:
                continue
            if (
                str(record.source_metadata.get("source_replay_path")) != source_replay_path
                or str(record.source_metadata.get("replay_sha256")) != expected_replay_sha256
            ):
                raise ValueError("target record replay provenance mismatch")
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
                label_source=record.label_source,
            )
            if (
                reconstructed.state_id != record.state_id
                or reconstructed.decision_id != record.decision_id
                or decision.canonical_action.to_dict() != record.chosen_canonical_action
            ):
                raise ValueError("replay decision reconstruction mismatch")
            converted, scores, _reasons = score_options(agent, dict(decision.observation))
            ranked = rank_target_actions(
                converted, scores, baseline, list(decision.raw_action),
            )
            candidates, sets = candidate_sets(
                ranked,
                baseline,
                decision.raw_action,
                converted,
                top_k=rule_top_k,
                max_diverse=max_diverse_actions,
            )
            beliefs = build_beliefs(
                catalog,
                record.opponent_archetype or "unknown",
                _visible_cards(record.safe_observation),
                max_known=max_known_hypotheses,
                unknown_mass=unknown_mass,
                observation=decision.observation,
                own_deck=own_deck,
                preflight_seed="%s:%s" % (seed, record.decision_id),
            )
            gold_id = canonicalize_prompt_action(converted, decision.raw_action).stable_id
            state = {
                "schema_version": SCHEMA_VERSION,
                "decision_id": record.decision_id,
                "state_id": record.state_id,
                "episode_id": episode_id,
                "acting_seat": seat,
                "source_replay_path": source_replay_path,
                "replay_sha256": expected_replay_sha256,
                "split": membership[record.decision_id],
                "style_id": record.style_id,
                "submission_id": record.submission_id,
                "replay_step": record.replay_step,
                "safe_observation": record.safe_observation,
                "known_private_info": record.known_private_info,
                "public_history": record.public_history,
                "legal_semantic_options": list(record.legal_semantic_options),
                "current_metadata": {
                    "turn": record.turn,
                    "own_archetype": record.own_archetype,
                    "opponent_archetype": record.opponent_archetype,
                },
                "candidates": candidates,
                "candidate_sets": sets,
                "gold_incremental": gold_id not in sets["rule_diverse"],
                "own_deck": {
                    "decklist": own_deck,
                    "sha256": canonical_sha256(own_deck),
                    "inventory_source": own_inventory_source,
                },
                "belief": beliefs,
            }
            validate_no_leakage(state)
            states.append(state)

    if {state["decision_id"] for state in states} != set(decision_ids):
        raise ValueError("collector did not emit every requested decision")
    states.sort(key=lambda state: state["decision_id"])
    states_bytes = b"".join(_json(state) for state in states)
    states_path = output_dir / "states.jsonl"
    if states_path.exists() and states_path.read_bytes() != states_bytes:
        raise FileExistsError("refusing to replace non-identical states")
    output_dir.mkdir(parents=True, exist_ok=True)
    if not states_path.exists():
        states_path.write_bytes(states_bytes)

    by_episode: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_matchup: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    aggregate_belief_counts: Counter[str] = Counter()
    for state in states:
        by_episode[str(state["episode_id"])].append(state)
        current = state["current_metadata"]
        matchup = "%s__vs__%s" % (
            current["own_archetype"], current["opponent_archetype"],
        )
        by_matchup[matchup].append(state)
        aggregate_belief_counts.update(state["belief"]["counts"])
    source_replays = [
        {"source_replay_path": path, "replay_sha256": checksum}
        for path, checksum in sorted(replay_bindings.items())
    ]
    final = {
        "schema_version": SCHEMA_VERSION,
        "selection_manifest_sha256": file_sha256(
            output_dir / "selection_manifest.json",
        ),
        "states_sha256": file_sha256(states_path),
        "source_replays": source_replays,
        "source_replays_sha256": canonical_sha256(source_replays),
        "engine_files_sha256": {
            "cg/api.py": file_sha256(engine_dir / "cg" / "api.py"),
            "cg/cg.dll": file_sha256(engine_dir / "cg" / "cg.dll"),
        },
        "python": sys.version,
        "platform": platform.platform(),
        "command": list(sys.argv),
        "counts": {
            "states": len(states),
            "episodes": len(by_episode),
            "candidate_coverage": _coverage(states),
            "belief": dict(sorted(aggregate_belief_counts.items())),
            "per_episode_candidate_coverage": {
                key: _coverage(value) for key, value in sorted(by_episode.items())
            },
            "per_matchup_candidate_coverage": {
                key: _coverage(value) for key, value in sorted(by_matchup.items())
            },
        },
    }
    final["manifest_sha256"] = canonical_sha256(final)
    write_once(output_dir / "manifest.json", final)
    return verify_gold_oracle_states(output_dir, workspace)
