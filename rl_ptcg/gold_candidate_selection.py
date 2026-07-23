"""Freeze screened rule comparators for high-particle Gold upper-bound tests."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_states import (
    canonical_sha256,
    file_sha256,
    verify_gold_oracle_states,
    write_once,
)


SCHEMA_VERSION = "gold_candidate_selection.v1"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object: %s" % path)
    return value


def _read_states(path: Path) -> dict[str, dict[str, Any]]:
    return {
        value["state_id"]: value
        for line in path.read_text(encoding="ascii").splitlines()
        for value in [json.loads(line)]
    }


def _resolve(path: str | Path, workspace: Path) -> Path:
    value = Path(path)
    resolved = (value if value.is_absolute() else workspace / value).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _report_source(path: Path, workspace: Path) -> dict[str, Any]:
    directory = _resolve(path, workspace)
    report_path = directory / "report.json"
    run_path = directory / "run_manifest.json"
    report = _read_object(report_path)
    run = _read_object(run_path)
    if report.get("manifest_sha256") != _self_hash(report):
        raise ValueError("source report self-hash mismatch: %s" % path)
    if run.get("manifest_sha256") != _self_hash(run):
        raise ValueError("source run manifest self-hash mismatch: %s" % path)
    statistics = report.get("posterior_weighted_teacher_statistics")
    if not isinstance(statistics, Mapping):
        raise ValueError("source report has no posterior-weighted statistics")
    return {
        "path": str(directory.relative_to(workspace)),
        "report_sha256": file_sha256(report_path),
        "report_manifest_sha256": report["manifest_sha256"],
        "run_manifest_file_sha256": file_sha256(run_path),
        "run_manifest_sha256": run["manifest_sha256"],
        "particles_per_scenario": int(run["config"]["particles_per_scenario"]),
        "batch_count": len(run["batch_ids"]),
        "statistics": statistics,
    }


def _incremental_gold(state: Mapping[str, Any]) -> str:
    incremental = [
        identifier for identifier in state["candidate_sets"]["rule_plus_gold"]
        if identifier not in state["candidate_sets"]["rule_diverse"]
    ]
    if len(incremental) != 1 or not state.get("gold_incremental"):
        raise ValueError("state does not have exactly one incremental Gold action")
    return incremental[0]


def build_candidate_selection(
    corpus_dir: Path,
    source_report_dirs: Sequence[Path],
    output_path: Path,
    *,
    state_ids: Sequence[str] | None,
    workspace_root: Path,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    verified = verify_gold_oracle_states(corpus_dir, workspace)
    corpus = _resolve(verified["output_dir"], workspace)
    states = _read_states(corpus / "states.jsonl")
    requested = sorted(state_ids or [
        state_id for state_id, state in states.items() if state.get("gold_incremental")
    ])
    if len(requested) != len(set(requested)) or not set(requested) <= set(states):
        raise ValueError("selected states are duplicate or absent from corpus")
    sources = [_report_source(path, workspace) for path in source_report_dirs]
    if not sources:
        raise ValueError("at least one source report is required")
    units_by_source_state: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for source in sources:
        for unit in source["statistics"]["per_state_batch"]:
            units_by_source_state[(source["path"], unit["state_id"])].append(unit)
    entries = {}
    for state_id in requested:
        state = states[state_id]
        available = [
            source for source in sources
            if units_by_source_state.get((source["path"], state_id))
        ]
        if not available:
            raise ValueError("no screening report covers state: %s" % state_id)
        source = max(
            available,
            key=lambda value: (
                value["particles_per_scenario"], value["batch_count"], value["path"],
            ),
        )
        units = units_by_source_state[(source["path"], state_id)]
        rule_ids = list(state["candidate_sets"]["rule_diverse"])
        means = {}
        for identifier in rule_ids:
            values = [
                float(unit["actions"][identifier]["mean_terminal_utility"])
                for unit in units if identifier in unit["actions"]
            ]
            if len(values) != len(units):
                raise ValueError("screening report omits a rule candidate")
            means[identifier] = sum(values) / len(values)
        best_value = max(means.values())
        tied = sorted(
            identifier for identifier, value in means.items()
            if math.isclose(value, best_value, rel_tol=0.0, abs_tol=1e-12)
        )
        baseline = state["candidate_sets"]["baseline"][0]
        comparator = baseline if baseline in tied else tied[0]
        gold = _incremental_gold(state)
        gold_values = [
            float(unit["actions"][gold]["mean_terminal_utility"])
            for unit in units
        ]
        candidate_ids = list(dict.fromkeys([baseline, comparator, gold]))
        entries[state_id] = {
            "decision_id": state["decision_id"],
            "episode_id": state["episode_id"],
            "replay_step": state["replay_step"],
            "baseline_action": baseline,
            "rule_comparator_action": comparator,
            "gold_action": gold,
            "candidate_ids": candidate_ids,
            "screening_source_path": source["path"],
            "screening_particles_per_scenario": source["particles_per_scenario"],
            "screening_batch_count": source["batch_count"],
            "rule_comparator_mean_utility": means[comparator],
            "gold_mean_utility": sum(gold_values) / len(gold_values),
            "screen_gold_minus_comparator_win_probability": (
                (sum(gold_values) / len(gold_values) - means[comparator]) / 2.0
            ),
            "is_upper_bound_on_gold_vs_full_rule_oracle": True,
        }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": "screened_gold_upper_bound",
        "corpus": {
            "path": str(corpus.relative_to(workspace)),
            "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
            "states_sha256": file_sha256(corpus / "states.jsonl"),
            "manifest_sha256": file_sha256(corpus / "manifest.json"),
        },
        "source_reports": [
            {key: value for key, value in source.items() if key != "statistics"}
            for source in sources
        ],
        "states": entries,
    }
    payload["manifest_sha256"] = _self_hash(payload)
    output = _resolve(output_path, workspace)
    write_once(output, payload)
    return {
        "states": len(entries),
        "manifest_sha256": payload["manifest_sha256"],
        "output": str(output),
    }


def verify_candidate_selection(
    path: Path, workspace_root: Path,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    resolved = _resolve(path, workspace)
    payload = _read_object(resolved)
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("manifest_sha256") != _self_hash(payload):
        raise ValueError("candidate selection self-hash mismatch")
    corpus = _resolve(payload["corpus"]["path"], workspace)
    verify_gold_oracle_states(corpus, workspace)
    expected_corpus = {
        "path": payload["corpus"]["path"],
        "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
        "states_sha256": file_sha256(corpus / "states.jsonl"),
        "manifest_sha256": file_sha256(corpus / "manifest.json"),
    }
    if payload["corpus"] != expected_corpus:
        raise ValueError("candidate selection corpus binding mismatch")
    states = _read_states(corpus / "states.jsonl")
    for source in payload["source_reports"]:
        directory = _resolve(source["path"], workspace)
        if (
            file_sha256(directory / "report.json") != source["report_sha256"]
            or file_sha256(directory / "run_manifest.json") != source["run_manifest_file_sha256"]
        ):
            raise ValueError("candidate selection source report changed")
    for state_id, entry in payload["states"].items():
        state = states.get(state_id)
        if state is None or entry["decision_id"] != state["decision_id"]:
            raise ValueError("candidate selection state binding mismatch")
        baseline = state["candidate_sets"]["baseline"][0]
        if (
            entry["baseline_action"] != baseline
            or entry["rule_comparator_action"] not in state["candidate_sets"]["rule_diverse"]
            or entry["gold_action"] != _incremental_gold(state)
            or entry["candidate_ids"] != list(dict.fromkeys([
                entry["baseline_action"], entry["rule_comparator_action"], entry["gold_action"],
            ]))
            or not entry.get("is_upper_bound_on_gold_vs_full_rule_oracle")
        ):
            raise ValueError("candidate selection role invariant failed")
    return {
        "states": len(payload["states"]),
        "manifest_sha256": payload["manifest_sha256"],
        "output": str(resolved),
        "payload": payload,
    }
