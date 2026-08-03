"""Leakage-resistant expansion screen for upper-tier target states."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_states import canonical_sha256, file_sha256
from .gold_upper_tier_states import verify_gold_upper_tier_states
from .replay_records import ReplayDecisionRecord
from .replay_reconstruction import is_main_menu_prompt, iter_replay_decisions


SCHEMA_VERSION = "gold_upper_tier_state_screen.v2"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _resolve(path: str | Path, workspace: Path) -> Path:
    value = Path(path)
    resolved = (value if value.is_absolute() else workspace / value).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("JSON input must contain an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="ascii").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("JSONL input must contain objects")
    return rows


def _option_count(observation: Mapping[str, Any]) -> int:
    select = observation.get("select") or {}
    options = select.get("option", select.get("options", []))
    return len(options) if isinstance(options, list) else 0


def select_additional_rows(
    rows: Sequence[Mapping[str, Any]], base_turns: set[tuple[str, int, int]],
    base_state_ids: set[str], *, minimum_legal_options: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select the earliest qualifying root in each previously unrepresented turn."""
    pool = []
    for source in rows:
        row = dict(source)
        episode = str(row["episode_id"])
        seat = int(row["acting_seat"])
        turn = row.get("turn")
        represented = turn is not None and (episode, seat, int(turn)) in base_turns
        state_represented = str(row["state_id"]) in base_state_ids
        screened = (
            bool(row["main_menu"])
            and int(row["legal_option_count"]) >= minimum_legal_options
            and not state_represented
        )
        eligible = screened and turn is not None and not represented
        row["eligible_additional"] = eligible
        if screened:
            pool.append(row)
    earliest: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in sorted((item for item in pool if item["eligible_additional"]), key=lambda item: (
        str(item["episode_id"]), int(item["acting_seat"]),
        int(item["turn"]), int(item["replay_step"]), str(item["state_id"]),
    )):
        key = (str(row["episode_id"]), int(row["acting_seat"]), int(row["turn"]))
        earliest.setdefault(key, row)
    selected = sorted(earliest.values(), key=lambda item: (
        str(item["episode_id"]), int(item["acting_seat"]), int(item["replay_step"]),
    ))
    if len({row["state_id"] for row in selected}) != len(selected):
        raise ValueError("selected additional roots contain duplicate state IDs")
    selected_specs = {
        (str(row["episode_id"]), int(row["acting_seat"]), int(row["replay_step"]))
        for row in selected
    }
    for row in pool:
        row["selected_additional"] = (
            str(row["episode_id"]), int(row["acting_seat"]), int(row["replay_step"])
        ) in selected_specs
    return pool, selected


def build_screen_payload(
    base_corpus_dir: Path, workspace_root: Path, cli_path: Path,
    *, minimum_legal_options: int = 4,
) -> dict[str, Any]:
    if minimum_legal_options < 2:
        raise ValueError("minimum legal options must be at least two")
    workspace = workspace_root.resolve()
    base = _resolve(base_corpus_dir, workspace)
    verified = verify_gold_upper_tier_states(base, workspace)
    base_manifest = _read_json(base / "manifest.json")
    base_states = _read_jsonl(base / "states.jsonl")
    base_ids = {str(state["state_id"]) for state in base_states}
    base_specs = sorted({
        (str(state["episode_id"]), int(state["acting_seat"]), int(state["replay_step"]))
        for state in base_states
    })
    base_turns = {
        (str(state["episode_id"]), int(state["acting_seat"]), int(state["current_metadata"]["turn"]))
        for state in base_states
    }
    bindings = {
        str(item["source_replay_path"]): str(item["replay_sha256"])
        for item in base_manifest["source_replays"]
    }
    pairs = sorted({(str(state["episode_id"]), int(state["acting_seat"])) for state in base_states})
    state_by_pair = {
        (str(state["episode_id"]), int(state["acting_seat"])): state
        for state in base_states
    }
    rows = []
    for episode, seat in pairs:
        state = state_by_pair[(episode, seat)]
        replay_path = _resolve(state["source_replay_path"], workspace)
        if file_sha256(replay_path) != bindings[state["source_replay_path"]]:
            raise ValueError("source replay hash mismatch")
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        for decision in iter_replay_decisions(replay, seats=[seat]):
            record = ReplayDecisionRecord.from_observation(
                decision.observation, decision.raw_action,
                episode_id=episode, submission_id="screen_provenance",
                style_id="upper_tier_distribution", decision_step=decision.replay_step,
                replay_step=decision.replay_step, acting_seat=seat,
                public_history=decision.public_history,
                private_action_history=decision.private_action_history,
            )
            rows.append({
                "episode_id": episode,
                "acting_seat": seat,
                "replay_step": int(decision.replay_step),
                "turn": decision.turn,
                "state_id": record.state_id,
                "main_menu": bool(is_main_menu_prompt(decision.observation)),
                "legal_option_count": _option_count(decision.observation),
            })
    pool, selected = select_additional_rows(
        rows, base_turns, base_ids, minimum_legal_options=minimum_legal_options,
    )
    additional_specs = [
        [str(row["episode_id"]), int(row["acting_seat"]), int(row["replay_step"])]
        for row in selected
    ]
    final_specs = sorted([list(item) for item in base_specs] + additional_specs)
    implementation = {}
    for name, path in {
        "screen_module": Path(__file__).resolve(),
        "screen_cli": cli_path.resolve(),
    }.items():
        implementation[name] = {
            "path": str(path.relative_to(workspace)).replace("\\", "/"),
            "sha256": file_sha256(path),
        }
    result = {
        "schema_version": SCHEMA_VERSION,
        "base_corpus": {
            "path": str(base.relative_to(workspace)).replace("\\", "/"),
            "manifest_file_sha256": file_sha256(base / "manifest.json"),
            "manifest_sha256": base_manifest["manifest_sha256"],
            "states_sha256": file_sha256(base / "states.jsonl"),
            "verified": verified,
        },
        "criteria": {
            "source_episode_seat_pairs": "base_corpus_only",
            "prompt_kind": "main_menu_transaction_root",
            "minimum_legal_options": minimum_legal_options,
            "per_turn_rule": "earliest_qualifying_root_in_unrepresented_actor_turn",
            "deduplication_key": "state_id",
            "recorded_action_role": "state_id_reconstruction_provenance_only",
            "forbidden_selection_signals": ["recorded_action", "terminal_result", "post_target_frames"],
        },
        "counts": {
            "base_states": len(base_states),
            "actor_prompts": len(rows),
            "nonbase_main_menu_legal_option_pool": len(pool),
            "eligible_unrepresented_turn_pool": sum(bool(row["eligible_additional"]) for row in pool),
            "selected_additional_states": len(selected),
            "final_states": len(final_specs),
            "unique_final_episode_seat_turns": len(base_turns) + len(selected),
            "unique_selected_additional_state_ids": len({row["state_id"] for row in selected}),
        },
        "base_state_specs": [list(item) for item in base_specs],
        "selected_additional": selected,
        "candidate_pool": pool,
        "final_state_specs": final_specs,
        "source_replays": base_manifest["source_replays"],
        "implementation": implementation,
    }
    result["manifest_sha256"] = _self_hash(result)
    return result


def write_screen(
    base_corpus_dir: Path, output_path: Path, workspace_root: Path, cli_path: Path,
    *, minimum_legal_options: int = 4,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    output = _resolve(output_path, workspace)
    payload = build_screen_payload(
        base_corpus_dir, workspace, cli_path,
        minimum_legal_options=minimum_legal_options,
    )
    data = (json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode("ascii")
    if output.exists() and output.read_bytes() != data:
        raise FileExistsError("refusing to replace non-identical screen artifact")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_bytes(data)
    return verify_screen(output, workspace, cli_path)


def verify_screen(path: Path, workspace_root: Path, cli_path: Path) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    resolved = _resolve(path, workspace)
    payload = _read_json(resolved)
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("manifest_sha256") != _self_hash(payload):
        raise ValueError("screen manifest self-hash mismatch")
    base_path = _resolve(payload["base_corpus"]["path"], workspace)
    recomputed = build_screen_payload(
        base_path, workspace, cli_path,
        minimum_legal_options=int(payload["criteria"]["minimum_legal_options"]),
    )
    if recomputed != payload:
        raise ValueError("screen artifact no longer reproduces")
    return {
        "verified": True,
        "actor_prompts": payload["counts"]["actor_prompts"],
        "candidate_pool": payload["counts"]["nonbase_main_menu_legal_option_pool"],
        "selected_additional_states": payload["counts"]["selected_additional_states"],
        "final_states": payload["counts"]["final_states"],
        "manifest_sha256": payload["manifest_sha256"],
    }
