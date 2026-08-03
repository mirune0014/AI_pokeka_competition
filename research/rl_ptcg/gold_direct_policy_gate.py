"""Fail-closed deck applicability gate for Gold direct-policy supervision."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
from typing import Any, Iterable, Mapping, Sequence

from .gold_oracle_states import canonical_sha256, file_sha256, verify_gold_oracle_states


SCHEMA_VERSION = "gold_direct_policy_gate.v1"
DEFAULT_MAX_REPLACEMENTS = 4
DEFAULT_SENSITIVITY_THRESHOLDS = (0, 1, 2, 4, 6, 8, 13)


def _json(value: Any, pretty: bool = False) -> bytes:
    return (json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n").encode("ascii")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not lines or any(not line for line in lines):
        raise ValueError("%s must be non-empty JSONL without blank rows" % path)
    result = []
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid JSONL row %d in %s" % (number, path)) from error
        if not isinstance(value, dict):
            raise ValueError("JSONL row %d is not an object" % number)
        result.append(value)
    return result


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain a JSON object" % path)
    return value


def _read_deck(path: Path) -> list[int]:
    try:
        deck = [int(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("could not read deck %s: %s" % (path, error)) from error
    _validate_deck(deck, str(path))
    return deck


def _validate_deck(deck: Sequence[int], label: str) -> None:
    if (
        len(deck) != 60
        or not all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in deck)
    ):
        raise ValueError("%s must contain exactly 60 integer card IDs" % label)


def deck_replacement_distance(left: Sequence[int], right: Sequence[int]) -> int:
    """Return the minimum same-size card replacements between two deck multisets."""
    _validate_deck(left, "left deck")
    _validate_deck(right, "right deck")
    left_counts = Counter(left)
    right_counts = Counter(right)
    return sum((left_counts - right_counts).values())


def multiset_overlap(left: Sequence[int], right: Sequence[int]) -> int:
    _validate_deck(left, "left deck")
    _validate_deck(right, "right deck")
    return sum((Counter(left) & Counter(right)).values())


def _gold_candidate(state: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = state.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("state has no candidate list")
    gold = [
        candidate for candidate in candidates
        if isinstance(candidate, Mapping) and "gold" in candidate.get("source_tags", [])
    ]
    if len(gold) != 1:
        raise ValueError("state must contain exactly one Gold candidate")
    return gold[0]


def action_self_card_dependencies(
    canonical: Mapping[str, Any], source_deck: Iterable[int],
) -> list[int]:
    """Extract actor-owned cards required by a complete canonical action."""
    source_ids = set(int(card_id) for card_id in source_deck)
    selections = canonical.get("selections")
    if not isinstance(selections, list) or not selections:
        raise ValueError("canonical action has no selections")
    required = set()
    for selection in selections:
        if not isinstance(selection, Mapping):
            raise ValueError("canonical action selection is not an object")
        source = selection.get("source_card_id")
        if selection.get("source_relation") == "self" and isinstance(source, int):
            required.add(source)
        target = selection.get("target_card_id")
        if selection.get("target_relation") == "self" and isinstance(target, int):
            required.add(target)
        effect = selection.get("effect_source_id")
        if isinstance(effect, int) and effect in source_ids:
            required.add(effect)
    return sorted(required)


def build_gate_rows(
    states: Sequence[Mapping[str, Any]],
    target_deck: Sequence[int],
    target_archetype: str,
    max_replacements: int = DEFAULT_MAX_REPLACEMENTS,
) -> list[dict[str, Any]]:
    _validate_deck(target_deck, "target deck")
    if not target_archetype:
        raise ValueError("target_archetype must be non-empty")
    if max_replacements < 0:
        raise ValueError("max_replacements must be non-negative")
    target_counts = Counter(target_deck)
    rows = []
    seen_decisions = set()
    for state in states:
        state_id = state.get("state_id")
        decision_id = state.get("decision_id")
        if not isinstance(state_id, str) or not state_id:
            raise ValueError("state IDs must be non-empty strings")
        if (
            not isinstance(decision_id, str)
            or not decision_id
            or decision_id in seen_decisions
        ):
            raise ValueError("decision IDs must be unique non-empty strings")
        seen_decisions.add(decision_id)
        own = state.get("own_deck")
        source_deck = own.get("decklist") if isinstance(own, Mapping) else None
        if not isinstance(source_deck, list):
            raise ValueError("state has no actor deck")
        _validate_deck(source_deck, "state actor deck")
        candidate = _gold_candidate(state)
        canonical = candidate.get("canonical")
        if not isinstance(canonical, Mapping):
            raise ValueError("Gold candidate has no canonical action")
        dependencies = action_self_card_dependencies(canonical, source_deck)
        missing = sorted(card_id for card_id in dependencies if target_counts[card_id] == 0)
        distance = deck_replacement_distance(source_deck, target_deck)
        overlap = multiset_overlap(source_deck, target_deck)
        current = state.get("current_metadata")
        source_archetype = current.get("own_archetype") if isinstance(current, Mapping) else None
        same_archetype = source_archetype == target_archetype
        near_deck = distance <= max_replacements
        action_available = not missing
        reasons = []
        if not same_archetype:
            reasons.append("archetype_mismatch")
        if not near_deck:
            reasons.append("deck_replacements_exceed_limit")
        if not action_available:
            reasons.append("gold_action_cards_absent_target_deck")
        eligible = not reasons
        rows.append({
            "schema_version": SCHEMA_VERSION,
            "state_id": state_id,
            "decision_id": decision_id,
            "episode_id": str(state.get("episode_id")),
            "submission_id": str(state.get("submission_id")),
            "style_id": str(state.get("style_id")),
            "source_archetype": source_archetype,
            "target_archetype": target_archetype,
            "source_deck_sha256": str(own.get("sha256")),
            "target_deck_sha256": canonical_sha256(list(target_deck)),
            "deck_replacements": distance,
            "deck_multiset_overlap": overlap,
            "deck_overlap_fraction": overlap / 60.0,
            "max_replacements": max_replacements,
            "same_archetype": same_archetype,
            "near_deck": near_deck,
            "gold_semantic_id": str(candidate.get("semantic_id")),
            "gold_action_self_card_dependencies": dependencies,
            "missing_target_card_ids": missing,
            "gold_action_available_in_target_deck": action_available,
            "direct_policy_eligible": eligible,
            "exclusion_reasons": reasons,
            "allowed_uses": (
                ["belief_teacher_action_candidate", "direct_policy_prior", "upper_tier_state_distribution"]
                if eligible else
                ["source_deck_policy_model", "upper_tier_state_distribution"]
            ),
        })
    return sorted(rows, key=lambda row: (row["decision_id"], row["state_id"]))


def summarize_rows(
    rows: Sequence[Mapping[str, Any]],
    thresholds: Sequence[int] = DEFAULT_SENSITIVITY_THRESHOLDS,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("gate rows must be non-empty")
    source_decks: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    reasons: Counter[str] = Counter()
    for row in rows:
        source_decks[str(row["source_deck_sha256"])].append(row)
        reasons.update(str(reason) for reason in row["exclusion_reasons"])
    sensitivity = {}
    for threshold in thresholds:
        if threshold < 0:
            raise ValueError("sensitivity thresholds must be non-negative")
        eligible = sum(
            bool(row["same_archetype"])
            and bool(row["gold_action_available_in_target_deck"])
            and int(row["deck_replacements"]) <= int(threshold)
            for row in rows
        )
        sensitivity[str(int(threshold))] = eligible
    return {
        "states": len(rows),
        "episodes": len({str(row["episode_id"]) for row in rows}),
        "source_decks": len(source_decks),
        "direct_policy_eligible": sum(bool(row["direct_policy_eligible"]) for row in rows),
        "near_deck": sum(bool(row["near_deck"]) for row in rows),
        "gold_action_available_in_target_deck": sum(
            bool(row["gold_action_available_in_target_deck"]) for row in rows
        ),
        "exclusion_reasons": dict(sorted(reasons.items())),
        "per_source_deck": {
            deck_sha: {
                "states": len(values),
                "episodes": len({str(row["episode_id"]) for row in values}),
                "deck_replacements": sorted({int(row["deck_replacements"]) for row in values}),
                "direct_policy_eligible": sum(bool(row["direct_policy_eligible"]) for row in values),
            }
            for deck_sha, values in sorted(source_decks.items())
        },
        "threshold_sensitivity_direct_eligible": sensitivity,
    }


def _resolve(path: str | Path, workspace: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _write_bytes_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def run_gate(
    corpus_dir: str | Path,
    target_deck_path: str | Path,
    output_dir: str | Path,
    *,
    target_archetype: str,
    max_replacements: int = DEFAULT_MAX_REPLACEMENTS,
    sensitivity_thresholds: Sequence[int] = DEFAULT_SENSITIVITY_THRESHOLDS,
    workspace_root: str | Path | None = None,
    cli_path: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    corpus = _resolve(corpus_dir, workspace)
    target_path = _resolve(target_deck_path, workspace)
    output = _resolve(output_dir, workspace)
    verify_gold_oracle_states(corpus, workspace)
    states_path = corpus / "states.jsonl"
    target_deck = _read_deck(target_path)
    rows = build_gate_rows(
        _load_jsonl(states_path), target_deck, target_archetype, max_replacements,
    )
    rows_bytes = b"".join(_json(row) for row in rows)
    rows_path = output / "rows.jsonl"
    _write_bytes_once(rows_path, rows_bytes)

    module_path = Path(__file__).resolve()
    cli = _resolve(cli_path, workspace) if cli_path else workspace / "infrastructure" / "tools" / "build_gold_direct_policy_gate.py"
    snapshots = {}
    for source in (module_path, cli):
        relative = source.relative_to(workspace)
        snapshot = output / "source_snapshot" / relative
        _write_bytes_once(snapshot, source.read_bytes())
        snapshots[str(relative)] = {
            "source_sha256": file_sha256(source),
            "snapshot_path": str(snapshot.relative_to(workspace)),
            "snapshot_sha256": file_sha256(snapshot),
        }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "corpus_manifest": {
                "path": str((corpus / "manifest.json").relative_to(workspace)),
                "sha256": file_sha256(corpus / "manifest.json"),
            },
            "corpus_states": {
                "path": str(states_path.relative_to(workspace)),
                "sha256": file_sha256(states_path),
            },
            "target_deck": {
                "path": str(target_path.relative_to(workspace)),
                "sha256": file_sha256(target_path),
            },
        },
        "implementation": snapshots,
        "config": {
            "target_archetype": target_archetype,
            "max_replacements": max_replacements,
            "sensitivity_thresholds": [int(value) for value in sensitivity_thresholds],
        },
        "target_deck_canonical_sha256": canonical_sha256(target_deck),
        "rows_sha256": sha256(rows_bytes).hexdigest(),
        "counts": summarize_rows(rows, sensitivity_thresholds),
        "python": sys.version,
        "platform": platform.platform(),
        "command": list(sys.argv),
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    _write_bytes_once(output / "manifest.json", _json(manifest, pretty=True))
    return verify_gate_output(output, workspace)


def verify_gate_output(
    output_dir: str | Path, workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    output = _resolve(output_dir, workspace)
    manifest = _read_object(output / "manifest.json")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("manifest_sha256") != canonical_sha256(unsigned)
    ):
        raise ValueError("direct-policy gate manifest self-hash mismatch")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, Mapping) or set(inputs) != {
        "corpus_manifest", "corpus_states", "target_deck",
    }:
        raise ValueError("invalid direct-policy gate input bindings")
    resolved_inputs = {}
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("invalid input binding: %s" % name)
        path = _resolve(str(binding["path"]), workspace)
        if not path.is_file() or file_sha256(path) != binding["sha256"]:
            raise ValueError("input hash mismatch: %s" % name)
        resolved_inputs[name] = path
    corpus = resolved_inputs["corpus_states"].parent
    verify_gold_oracle_states(corpus, workspace)

    implementation = manifest.get("implementation")
    if not isinstance(implementation, Mapping) or not implementation:
        raise ValueError("missing implementation snapshot bindings")
    drift = []
    for relative, binding in implementation.items():
        if not isinstance(binding, Mapping) or set(binding) != {
            "source_sha256", "snapshot_path", "snapshot_sha256",
        }:
            raise ValueError("invalid implementation binding")
        snapshot = _resolve(str(binding["snapshot_path"]), workspace)
        if not snapshot.is_file() or file_sha256(snapshot) != binding["snapshot_sha256"]:
            raise ValueError("implementation snapshot mismatch: %s" % relative)
        source = _resolve(str(relative), workspace)
        if not source.is_file() or file_sha256(source) != binding["source_sha256"]:
            drift.append(str(relative))

    rows_path = output / "rows.jsonl"
    if not rows_path.is_file() or file_sha256(rows_path) != manifest.get("rows_sha256"):
        raise ValueError("direct-policy gate rows hash mismatch")
    rows = _load_jsonl(rows_path)
    config = manifest.get("config")
    if not isinstance(config, Mapping):
        raise ValueError("invalid gate config")
    if summarize_rows(rows, config["sensitivity_thresholds"]) != manifest.get("counts"):
        raise ValueError("direct-policy gate count mismatch")
    recomputed = False
    if not drift:
        target_deck = _read_deck(resolved_inputs["target_deck"])
        expected = build_gate_rows(
            _load_jsonl(resolved_inputs["corpus_states"]),
            target_deck,
            str(config["target_archetype"]),
            int(config["max_replacements"]),
        )
        if expected != rows:
            raise ValueError("direct-policy gate rows do not recompute")
        recomputed = True
    return {
        "output_dir": str(output),
        "states": len(rows),
        "direct_policy_eligible": manifest["counts"]["direct_policy_eligible"],
        "rows_sha256": manifest["rows_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "current_implementation_drift": drift,
        "rows_recomputed": recomputed,
    }
