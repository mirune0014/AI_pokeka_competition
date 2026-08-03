#!/usr/bin/env python3
"""Extract the first policy-relevant split from staged Alakazam traces.

The extractor is deliberately fail-closed.  It first binds every checked
paired-result row to the matching metric-suite outcome, then joins the
instrumentation sidecar to the target policy's rows in the battle trace.
Only after those validations does it compare canonical pre-state, legal-set,
and selected-action payloads.

Comparison A has no retained callback trace.  It is therefore represented as
an operational deck/state split with explicit callback-unavailable provenance.
Comparisons B and C are same-deck policy comparisons with fixed role bindings.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


PRE_STATE_SCHEMA = "alakazam-observable-pre-state-v1"
LEGAL_SCHEMA = "alakazam-ordered-legal-options-v1"
SEMANTIC_LEGAL_SCHEMA = "alakazam-semantic-legal-multiset-v1"
SEMANTIC_ACTION_SCHEMA = "alakazam-semantic-action-multiset-v1"

ROLE_BINDINGS = {
    "B": ("v0", "v1"),
    "C": ("v1", "v2"),
}

CLASS_TRACE_INVALID = "TRACE_INVALID"
CLASS_OPERATIONAL_SPLIT = "OPERATIONAL_DECK_STATE_SPLIT"
CLASS_PRE_STATE_SPLIT = "UNEXPECTED_PRE_STATE_SPLIT"
CLASS_LEGAL_SET_SPLIT = "UNEXPECTED_LEGAL_SET_SPLIT"
CLASS_POLICY_DIVERGENCE = "TRUE_POLICY_DIVERGENCE"
CLASS_RAW_ORDER_ONLY = "RAW_ORDER_ONLY"
CLASS_NO_DIVERGENCE = "NO_POLICY_DIVERGENCE"

CSV_FIELDS = (
    "comparison",
    "schedule_key",
    "opponent",
    "seat",
    "seed_base",
    "game",
    "seed",
    "baseline_version",
    "candidate_version",
    "baseline_deck_hash",
    "candidate_deck_hash",
    "baseline_result",
    "candidate_result",
    "baseline_win",
    "candidate_win",
    "baseline_steps",
    "candidate_steps",
    "classification",
    "trace_status",
    "callback_ordinal",
    "battle_step",
    "turn",
    "turn_action_count",
    "context",
    "baseline_pre_state_sha256",
    "candidate_pre_state_sha256",
    "baseline_legal_sha256",
    "candidate_legal_sha256",
    "baseline_semantic_legal_sha256",
    "candidate_semantic_legal_sha256",
    "baseline_semantic_action_sha256",
    "candidate_semantic_action_sha256",
    "baseline_selected_action",
    "candidate_selected_action",
    "baseline_selected_options",
    "candidate_selected_options",
    "raw_order_only_count",
    "first_raw_order_only_ordinal",
    "detail",
)

REQUIRED_PAIRED_COLUMNS = frozenset(
    {
        "seed_base",
        "opponent",
        "seat",
        "game",
        "seed",
        "baseline_result",
        "candidate_result",
        "baseline_win",
        "candidate_win",
        "baseline_steps",
        "candidate_steps",
    }
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class InputValidationError(ValueError):
    """The comparison input or immutable configuration is invalid."""


class TraceValidationError(ValueError):
    """One schedule row's trace evidence is invalid or cannot be joined."""


def canonical_json(value: Any) -> str:
    """Return the exact canonical JSON representation used for hashing."""

    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise InputValidationError(f"{label} must be an integer, got bool")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be an integer: {value!r}") from exc


def _canonical_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return str(value)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise TraceValidationError(f"missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TraceValidationError(
                    f"invalid JSON at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise TraceValidationError(
                    f"JSONL row must be an object at {path}:{line_number}"
                )
            rows.append(value)
    return rows


@dataclass(frozen=True)
class ScheduleRow:
    seed_base: int
    opponent: str
    seat: int
    game: int
    seed: int
    baseline_result: int
    candidate_result: int
    baseline_win: int
    candidate_win: int
    baseline_steps: int
    candidate_steps: int

    @property
    def key(self) -> tuple[str, int, int, int]:
        return (self.opponent, self.seat, self.seed, self.game)

    @property
    def key_json(self) -> str:
        return canonical_json(list(self.key))


@dataclass(frozen=True)
class ExtractionConfig:
    comparison: str
    paired_results: Path
    output_dir: Path
    output_name: str
    baseline_version: str
    candidate_version: str
    baseline_deck_hash: str
    candidate_deck_hash: str
    baseline_suite: Path | None = None
    candidate_suite: Path | None = None

    def validated(self) -> "ExtractionConfig":
        comparison = self.comparison.upper()
        if comparison not in {"A", "B", "C"}:
            raise InputValidationError(
                f"comparison must be A, B, or C: {self.comparison!r}"
            )
        if not self.paired_results.is_file():
            raise InputValidationError(
                f"paired-results file does not exist: {self.paired_results}"
            )
        if (
            not self.output_name
            or self.output_name in {".", ".."}
            or Path(self.output_name).name != self.output_name
        ):
            raise InputValidationError(
                "output-name must be a non-empty basename without directories"
            )
        for label, value in (
            ("baseline-deck-hash", self.baseline_deck_hash),
            ("candidate-deck-hash", self.candidate_deck_hash),
        ):
            if not SHA256_RE.fullmatch(value):
                raise InputValidationError(f"{label} must be a 64-digit SHA-256")
        if not self.baseline_version or not self.candidate_version:
            raise InputValidationError("both version names are required")
        if comparison in ROLE_BINDINGS:
            expected = ROLE_BINDINGS[comparison]
            actual = (self.baseline_version, self.candidate_version)
            if actual != expected:
                raise InputValidationError(
                    f"comparison {comparison} role binding must be "
                    f"baseline={expected[0]}, candidate={expected[1]}; got {actual}"
                )
            if self.baseline_deck_hash.lower() != self.candidate_deck_hash.lower():
                raise InputValidationError(
                    f"comparison {comparison} must compare the same deck hash"
                )
            if self.baseline_suite is None or self.candidate_suite is None:
                raise InputValidationError(
                    f"comparison {comparison} requires both raw metric suites"
                )
            if not self.baseline_suite.is_dir():
                raise InputValidationError(
                    f"baseline suite does not exist: {self.baseline_suite}"
                )
            if not self.candidate_suite.is_dir():
                raise InputValidationError(
                    f"candidate suite does not exist: {self.candidate_suite}"
                )
        elif self.baseline_suite is not None or self.candidate_suite is not None:
            raise InputValidationError(
                "comparison A uses checked paired rows only; callback suites must be omitted"
            )
        return ExtractionConfig(
            comparison=comparison,
            paired_results=self.paired_results,
            output_dir=self.output_dir,
            output_name=self.output_name,
            baseline_version=self.baseline_version,
            candidate_version=self.candidate_version,
            baseline_deck_hash=self.baseline_deck_hash.lower(),
            candidate_deck_hash=self.candidate_deck_hash.lower(),
            baseline_suite=self.baseline_suite,
            candidate_suite=self.candidate_suite,
        )


@dataclass(frozen=True)
class CallbackEvidence:
    ordinal: int
    battle_step: int
    turn: int
    turn_action_count: int
    context: int
    pre_state_payload: dict[str, Any]
    pre_state_sha256: str
    legal_payload: dict[str, Any]
    legal_sha256: str
    semantic_legal_payload: dict[str, Any]
    semantic_legal_sha256: str
    semantic_action_payload: dict[str, Any]
    semantic_action_sha256: str
    selected_action: list[int]
    selected_options: list[dict[str, Any]]


def load_paired_rows(path: Path) -> list[ScheduleRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise InputValidationError(f"paired-results has no header: {path}")
        missing = REQUIRED_PAIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise InputValidationError(
                f"paired-results is missing columns: {sorted(missing)}"
            )
        raw_rows = list(reader)
    if not raw_rows:
        raise InputValidationError("paired-results contains no data rows")

    rows: list[ScheduleRow] = []
    seen: set[tuple[str, int, int, int]] = set()
    for row_number, raw in enumerate(raw_rows, start=2):
        opponent = (raw.get("opponent") or "").strip()
        if not opponent:
            raise InputValidationError(
                f"paired-results row {row_number}: opponent is empty"
            )
        values = {
            name: _as_int(raw.get(name), f"row {row_number} {name}")
            for name in REQUIRED_PAIRED_COLUMNS
            if name != "opponent"
        }
        row = ScheduleRow(opponent=opponent, **values)
        if row.seat not in (0, 1):
            raise InputValidationError(
                f"paired-results row {row_number}: seat must be 0 or 1"
            )
        if row.game < 0 or row.seed_base < 0 or row.seed < 0:
            raise InputValidationError(
                f"paired-results row {row_number}: game and seeds must be non-negative"
            )
        if row.seed != row.seed_base + row.game:
            raise InputValidationError(
                f"paired-results row {row_number}: seed must equal seed_base + game"
            )
        if row.baseline_result not in (0, 1) or row.candidate_result not in (0, 1):
            raise InputValidationError(
                f"paired-results row {row_number}: results must be player 0 or 1"
            )
        expected_baseline_win = int(row.baseline_result == row.seat)
        expected_candidate_win = int(row.candidate_result == row.seat)
        if row.baseline_win != expected_baseline_win:
            raise InputValidationError(
                f"paired-results row {row_number}: baseline_win disagrees with "
                "baseline_result and seat"
            )
        if row.candidate_win != expected_candidate_win:
            raise InputValidationError(
                f"paired-results row {row_number}: candidate_win disagrees with "
                "candidate_result and seat"
            )
        if row.baseline_steps < 0 or row.candidate_steps < 0:
            raise InputValidationError(
                f"paired-results row {row_number}: steps must be non-negative"
            )
        if row.key in seen:
            raise InputValidationError(
                f"duplicate paired schedule key at row {row_number}: {row.key_json}"
            )
        seen.add(row.key)
        rows.append(row)
    return sorted(rows, key=lambda item: item.key)


def _suite_manifest(suite: Path, version: str) -> dict[str, Any]:
    path = suite / "suite_manifest.json"
    if not path.is_file():
        raise InputValidationError(f"suite manifest is missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InputValidationError(f"cannot read suite manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise InputValidationError(f"suite manifest must be an object: {path}")
    versions = manifest.get("versions")
    names = {
        str(value.get("name"))
        for value in versions or []
        if isinstance(value, Mapping) and value.get("name") is not None
    }
    if version not in names:
        raise InputValidationError(
            f"suite {suite} does not declare version {version!r}; found {sorted(names)}"
        )
    return manifest


def _run_dir(suite: Path, version: str, row: ScheduleRow) -> Path:
    return (
        suite
        / "runs"
        / version
        / row.opponent
        / f"seed_{row.seed_base}"
        / f"seat_{row.seat}"
    )


def _summary_for_game(
    run_dir: Path,
    row: ScheduleRow,
    *,
    expected_result: int,
    expected_steps: int,
    role: str,
) -> dict[str, Any]:
    path = run_dir / "summary.jsonl"
    rows = _read_jsonl(path)
    by_game: dict[int, dict[str, Any]] = {}
    for value in rows:
        try:
            game = _as_int(value.get("game"), f"{path} game")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if game in by_game:
            raise TraceValidationError(f"duplicate summary game {game}: {path}")
        by_game[game] = value
    if row.game not in by_game:
        raise TraceValidationError(f"summary game {row.game} is missing: {path}")
    summary = by_game[row.game]
    try:
        seed = _as_int(summary.get("seed"), f"{role} summary seed")
        result = _as_int(summary.get("result"), f"{role} summary result")
        steps = _as_int(summary.get("steps"), f"{role} summary steps")
        action_errors = _as_int(
            summary.get("action_errors"), f"{role} summary action_errors"
        )
    except InputValidationError as exc:
        raise TraceValidationError(str(exc)) from exc
    if seed != row.seed:
        raise TraceValidationError(
            f"{role} summary seed mismatch: expected {row.seed}, got {seed}"
        )
    if result != expected_result:
        raise TraceValidationError(
            f"{role} summary result mismatch: expected {expected_result}, got {result}"
        )
    if steps != expected_steps:
        raise TraceValidationError(
            f"{role} summary steps mismatch: expected {expected_steps}, got {steps}"
        )
    if summary.get("started") is not True:
        raise TraceValidationError(f"{role} summary is not marked started")
    if summary.get("hit_max_steps") is not False:
        raise TraceValidationError(f"{role} summary hit max steps")
    if action_errors != 0:
        raise TraceValidationError(
            f"{role} summary reports {action_errors} action errors"
        )
    return summary


def _normalize_option_multiset(
    options: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    stripped = [
        {str(key): value for key, value in option.items() if key != "option_index"}
        for option in options
    ]
    return sorted(stripped, key=canonical_json)


def _validate_sidecar_pairs(
    path: Path,
    *,
    version: str,
    row: ScheduleRow,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    events = _read_jsonl(path)
    if not events:
        raise TraceValidationError(f"empty sidecar: {path}")
    starts: dict[int, dict[str, Any]] = {}
    ends: dict[int, dict[str, Any]] = {}
    run_id: str | None = None
    for event_index, event in enumerate(events):
        kind = event.get("event")
        if kind not in {"CALL_START", "CALL_END"}:
            raise TraceValidationError(
                f"unknown sidecar event {kind!r} at row {event_index}: {path}"
            )
        try:
            ordinal = _as_int(
                event.get("callback_ordinal"), f"{path} callback_ordinal"
            )
            game = _as_int(event.get("game"), f"{path} game")
            seed = _as_int(event.get("seed"), f"{path} seed")
            seat = _as_int(event.get("policy_seat"), f"{path} policy_seat")
            seed_base = _as_int(event.get("seed_base"), f"{path} seed_base")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if ordinal < 0:
            raise TraceValidationError(f"negative callback ordinal in {path}")
        expected_identity = (version, row.opponent, row.seat, row.game, row.seed)
        actual_identity = (
            str(event.get("version")),
            str(event.get("opponent")),
            seat,
            game,
            seed,
        )
        if actual_identity != expected_identity:
            raise TraceValidationError(
                "sidecar identity mismatch "
                "(version, opponent, policy_seat, game, seed): "
                f"expected {expected_identity}, got {actual_identity}"
            )
        if seed_base != row.seed_base:
            raise TraceValidationError(
                f"sidecar seed_base mismatch: expected {row.seed_base}, got {seed_base}"
            )
        event_run_id = event.get("run_id")
        if not isinstance(event_run_id, str) or not event_run_id:
            raise TraceValidationError(f"missing run_id in sidecar event: {path}")
        if run_id is None:
            run_id = event_run_id
        elif event_run_id != run_id:
            raise TraceValidationError(
                f"sidecar run_id mismatch: expected {run_id!r}, got {event_run_id!r}"
            )
        target = starts if kind == "CALL_START" else ends
        if ordinal in target:
            raise TraceValidationError(
                f"duplicate {kind} event for callback {ordinal}: {path}"
            )
        target[ordinal] = event
    all_ordinals = sorted(set(starts) | set(ends))
    expected_ordinals = list(range(len(all_ordinals)))
    if all_ordinals != expected_ordinals:
        raise TraceValidationError(
            f"sidecar callback ordinals are not a zero-based prefix: {all_ordinals}"
        )
    missing_start = sorted(set(ends) - set(starts))
    missing_end = sorted(set(starts) - set(ends))
    if missing_start or missing_end:
        raise TraceValidationError(
            f"orphan sidecar events: missing_start={missing_start}, "
            f"missing_end={missing_end}"
        )
    return [(starts[index], ends[index]) for index in all_ordinals]


def _selected_action_evidence(
    start: Mapping[str, Any],
    end: Mapping[str, Any],
    *,
    ordinal: int,
) -> tuple[
    list[int],
    list[dict[str, Any]],
    dict[str, Any],
    str,
    dict[str, Any],
    str,
    dict[str, Any],
    str,
]:
    observation = start.get("observation")
    if not isinstance(observation, Mapping):
        raise TraceValidationError(
            f"callback {ordinal}: CALL_START observation is not an object"
        )
    options_value = observation.get("options")
    if not isinstance(options_value, list) or not all(
        isinstance(option, Mapping) for option in options_value
    ):
        raise TraceValidationError(
            f"callback {ordinal}: observation options must be an object list"
        )
    options = [dict(option) for option in options_value]
    for position, option in enumerate(options):
        try:
            recorded_position = _as_int(
                option.get("option_index"),
                f"callback {ordinal} options[{position}].option_index",
            )
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if recorded_position != position:
            raise TraceValidationError(
                f"callback {ordinal}: options[{position}].option_index="
                f"{recorded_position}, expected {position}"
            )
    try:
        option_count = _as_int(
            observation.get("option_count"), f"callback {ordinal} option_count"
        )
    except InputValidationError as exc:
        raise TraceValidationError(str(exc)) from exc
    if option_count != len(options):
        raise TraceValidationError(
            f"callback {ordinal}: option_count={option_count} but "
            f"{len(options)} options were recorded"
        )
    selected_action_value = end.get("selected_action")
    if not isinstance(selected_action_value, list):
        raise TraceValidationError(
            f"callback {ordinal}: selected_action must be a list"
        )
    selected_action: list[int] = []
    for position, value in enumerate(selected_action_value):
        try:
            index = _as_int(value, f"callback {ordinal} action[{position}]")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if not 0 <= index < len(options):
            raise TraceValidationError(
                f"callback {ordinal}: selected option index {index} is out of range"
            )
        selected_action.append(index)
    if len(selected_action) != len(set(selected_action)):
        raise TraceValidationError(
            f"callback {ordinal}: selected_action contains duplicate indices"
        )
    selected_options = [options[index] for index in selected_action]
    recorded_selected = end.get("selected_options")
    if not isinstance(recorded_selected, list) or not all(
        isinstance(option, Mapping) for option in recorded_selected
    ):
        raise TraceValidationError(
            f"callback {ordinal}: selected_options must be an object list"
        )
    if canonical_json(recorded_selected) != canonical_json(selected_options):
        raise TraceValidationError(
            f"callback {ordinal}: selected_options do not match selected_action"
        )
    if end.get("structurally_valid") is not True:
        raise TraceValidationError(
            f"callback {ordinal}: sidecar marks the action structurally invalid"
        )
    if end.get("exception") is not None:
        raise TraceValidationError(
            f"callback {ordinal}: policy exception: {end.get('exception')!r}"
        )

    legal_payload = {"schema": LEGAL_SCHEMA, "options": options}
    semantic_legal_payload = {
        "schema": SEMANTIC_LEGAL_SCHEMA,
        "options": _normalize_option_multiset(options),
    }
    semantic_action_payload = {
        "schema": SEMANTIC_ACTION_SCHEMA,
        "selected_options": _normalize_option_multiset(selected_options),
    }
    return (
        selected_action,
        selected_options,
        legal_payload,
        canonical_sha256(legal_payload),
        semantic_legal_payload,
        canonical_sha256(semantic_legal_payload),
        semantic_action_payload,
        canonical_sha256(semantic_action_payload),
    )


def _validate_battle_row(
    battle: Mapping[str, Any],
    start: Mapping[str, Any],
    end: Mapping[str, Any],
    *,
    row: ScheduleRow,
    ordinal: int,
) -> CallbackEvidence:
    observation = start.get("observation")
    if not isinstance(observation, Mapping):
        raise TraceValidationError(
            f"callback {ordinal}: CALL_START observation is not an object"
        )
    (
        selected_action,
        selected_options,
        legal_payload,
        legal_sha256,
        semantic_legal_payload,
        semantic_legal_sha256,
        semantic_action_payload,
        semantic_action_sha256,
    ) = _selected_action_evidence(start, end, ordinal=ordinal)

    integer_pairs = (
        ("game", row.game, battle.get("game")),
        ("player", row.seat, battle.get("player")),
        ("context", observation.get("context"), battle.get("context")),
        ("select_type", observation.get("select_type"), battle.get("select_type")),
        ("min_count", observation.get("min_count"), battle.get("min_count")),
        ("max_count", observation.get("max_count"), battle.get("max_count")),
        ("option_count", observation.get("option_count"), battle.get("option_count")),
        ("turn", observation.get("turn"), (battle.get("snapshot") or {}).get("turn")),
        (
            "turn_action_count",
            observation.get("turn_action_count"),
            (battle.get("snapshot") or {}).get("turn_action_count"),
        ),
        (
            "snapshot_your_index",
            row.seat,
            (battle.get("snapshot") or {}).get("your_index"),
        ),
    )
    for label, expected_value, actual_value in integer_pairs:
        try:
            expected = _as_int(expected_value, f"callback {ordinal} {label} expected")
            actual = _as_int(actual_value, f"callback {ordinal} {label} actual")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if actual != expected:
            raise TraceValidationError(
                f"callback {ordinal}: battle {label} mismatch; "
                f"expected {expected}, got {actual}"
            )
    if "seed" in battle:
        try:
            battle_seed = _as_int(battle.get("seed"), f"callback {ordinal} seed")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if battle_seed != row.seed:
            raise TraceValidationError(
                f"callback {ordinal}: battle seed mismatch; "
                f"expected {row.seed}, got {battle_seed}"
            )
    if battle.get("action") != selected_action:
        raise TraceValidationError(
            f"callback {ordinal}: battle action does not match sidecar CALL_END"
        )

    own_hand = observation.get("own_hand")
    if not isinstance(own_hand, list):
        raise TraceValidationError(
            f"callback {ordinal}: observation own_hand must be a list"
        )
    hand_ids: list[Any] = []
    for position, pair in enumerate(own_hand):
        if not isinstance(pair, list) or len(pair) != 2:
            raise TraceValidationError(
                f"callback {ordinal}: own_hand[{position}] must be [card_id, serial]"
            )
        hand_ids.append(pair[0])
    if battle.get("own_hand_ids") != hand_ids:
        raise TraceValidationError(
            f"callback {ordinal}: battle hand IDs do not match sidecar observation"
        )

    options = observation.get("options")
    if not isinstance(options, list):
        raise TraceValidationError(
            f"callback {ordinal}: observation options must be a list"
        )
    battle_options = battle.get("options")
    if not isinstance(battle_options, list):
        raise TraceValidationError(
            f"callback {ordinal}: battle options must be a list"
        )
    if battle_options:
        sidecar_raw_options = [
            option.get("raw") if isinstance(option, Mapping) else None
            for option in options
        ]
        if canonical_json(battle_options) != canonical_json(sidecar_raw_options):
            raise TraceValidationError(
                f"callback {ordinal}: battle options do not match sidecar raw options"
            )

    observation_without_legal = {
        str(key): value
        for key, value in observation.items()
        if key not in {"options", "option_count"}
    }
    pre_state_payload = {
        "schema": PRE_STATE_SCHEMA,
        "observation": observation_without_legal,
        "context_card_id": battle.get("context_card_id"),
        "effect_card_id": battle.get("effect_card_id"),
        "selection_deck_ids": battle.get("selection_deck_ids"),
        "own_hand_ids": battle.get("own_hand_ids"),
        "snapshot": battle.get("snapshot"),
        "logs": battle.get("logs"),
    }
    try:
        battle_step = _as_int(battle.get("step"), f"callback {ordinal} battle step")
        turn = _as_int(observation.get("turn"), f"callback {ordinal} turn")
        turn_action_count = _as_int(
            observation.get("turn_action_count"),
            f"callback {ordinal} turn_action_count",
        )
        context = _as_int(
            observation.get("context"), f"callback {ordinal} context"
        )
    except InputValidationError as exc:
        raise TraceValidationError(str(exc)) from exc
    return CallbackEvidence(
        ordinal=ordinal,
        battle_step=battle_step,
        turn=turn,
        turn_action_count=turn_action_count,
        context=context,
        pre_state_payload=pre_state_payload,
        pre_state_sha256=canonical_sha256(pre_state_payload),
        legal_payload=legal_payload,
        legal_sha256=legal_sha256,
        semantic_legal_payload=semantic_legal_payload,
        semantic_legal_sha256=semantic_legal_sha256,
        semantic_action_payload=semantic_action_payload,
        semantic_action_sha256=semantic_action_sha256,
        selected_action=selected_action,
        selected_options=selected_options,
    )


def load_game_callbacks(
    suite: Path,
    version: str,
    row: ScheduleRow,
    *,
    expected_result: int,
    expected_steps: int,
    role: str,
) -> list[CallbackEvidence]:
    run_dir = _run_dir(suite, version, row)
    summary = _summary_for_game(
        run_dir,
        row,
        expected_result=expected_result,
        expected_steps=expected_steps,
        role=role,
    )
    sidecar_path = run_dir / "sidecars" / f"game_{row.game:04d}.jsonl"
    battle_path = run_dir / "battle_traces" / f"game_{row.game:04d}.jsonl"
    pairs = _validate_sidecar_pairs(sidecar_path, version=version, row=row)
    battles = _read_jsonl(battle_path)
    if len(battles) != expected_steps:
        raise TraceValidationError(
            f"{role} battle trace rows={len(battles)} but checked steps={expected_steps}"
        )
    for position, battle in enumerate(battles):
        try:
            step = _as_int(battle.get("step"), f"{role} battle step {position}")
            game = _as_int(battle.get("game"), f"{role} battle game {position}")
            player = _as_int(battle.get("player"), f"{role} battle player {position}")
        except InputValidationError as exc:
            raise TraceValidationError(str(exc)) from exc
        if step != position:
            raise TraceValidationError(
                f"{role} battle steps are not a zero-based prefix at row {position}: {step}"
            )
        if game != row.game:
            raise TraceValidationError(
                f"{role} battle game mismatch at step {step}: {game}"
            )
        if player not in (0, 1):
            raise TraceValidationError(
                f"{role} battle player must be 0 or 1 at step {step}: {player}"
            )
        if "seed" in battle:
            try:
                battle_seed = _as_int(
                    battle.get("seed"), f"{role} battle seed {position}"
                )
            except InputValidationError as exc:
                raise TraceValidationError(str(exc)) from exc
            if battle_seed != row.seed:
                raise TraceValidationError(
                    f"{role} battle seed mismatch at step {step}: {battle_seed}"
                )
    target_rows = [battle for battle in battles if battle.get("player") == row.seat]
    if len(target_rows) != len(pairs):
        raise TraceValidationError(
            f"{role} callback/battle target-row count mismatch: "
            f"callbacks={len(pairs)}, target_rows={len(target_rows)}"
        )
    evidence = [
        _validate_battle_row(
            battle,
            start,
            end,
            row=row,
            ordinal=ordinal,
        )
        for ordinal, ((start, end), battle) in enumerate(zip(pairs, target_rows))
    ]
    # The summary path is already bound above.  Reading this field ensures a
    # malformed trace redirect cannot silently supply a different game.
    trace_value = summary.get("trace")
    if trace_value is not None and Path(str(trace_value)).name != battle_path.name:
        raise TraceValidationError(
            f"{role} summary trace basename does not match expected battle trace"
        )
    return evidence


def _base_output_row(config: ExtractionConfig, row: ScheduleRow) -> dict[str, Any]:
    return {
        "comparison": config.comparison,
        "schedule_key": row.key_json,
        "opponent": row.opponent,
        "seat": row.seat,
        "seed_base": row.seed_base,
        "game": row.game,
        "seed": row.seed,
        "baseline_version": config.baseline_version,
        "candidate_version": config.candidate_version,
        "baseline_deck_hash": config.baseline_deck_hash,
        "candidate_deck_hash": config.candidate_deck_hash,
        "baseline_result": row.baseline_result,
        "candidate_result": row.candidate_result,
        "baseline_win": row.baseline_win,
        "candidate_win": row.candidate_win,
        "baseline_steps": row.baseline_steps,
        "candidate_steps": row.candidate_steps,
        "classification": "",
        "trace_status": "",
        "callback_ordinal": None,
        "battle_step": None,
        "turn": None,
        "turn_action_count": None,
        "context": None,
        "baseline_pre_state_sha256": "",
        "candidate_pre_state_sha256": "",
        "baseline_legal_sha256": "",
        "candidate_legal_sha256": "",
        "baseline_semantic_legal_sha256": "",
        "candidate_semantic_legal_sha256": "",
        "baseline_semantic_action_sha256": "",
        "candidate_semantic_action_sha256": "",
        "baseline_selected_action": None,
        "candidate_selected_action": None,
        "baseline_selected_options": None,
        "candidate_selected_options": None,
        "raw_order_only_count": 0,
        "first_raw_order_only_ordinal": None,
        "detail": "",
    }


def _attach_callback(
    output: dict[str, Any],
    baseline: CallbackEvidence,
    candidate: CallbackEvidence,
) -> None:
    output.update(
        {
            "callback_ordinal": baseline.ordinal,
            "battle_step": baseline.battle_step,
            "turn": baseline.turn,
            "turn_action_count": baseline.turn_action_count,
            "context": baseline.context,
            "baseline_pre_state_sha256": baseline.pre_state_sha256,
            "candidate_pre_state_sha256": candidate.pre_state_sha256,
            "baseline_legal_sha256": baseline.legal_sha256,
            "candidate_legal_sha256": candidate.legal_sha256,
            "baseline_semantic_legal_sha256": baseline.semantic_legal_sha256,
            "candidate_semantic_legal_sha256": candidate.semantic_legal_sha256,
            "baseline_semantic_action_sha256": baseline.semantic_action_sha256,
            "candidate_semantic_action_sha256": candidate.semantic_action_sha256,
            "baseline_selected_action": baseline.selected_action,
            "candidate_selected_action": candidate.selected_action,
            "baseline_selected_options": baseline.selected_options,
            "candidate_selected_options": candidate.selected_options,
        }
    )


def analyze_schedule(
    config: ExtractionConfig,
    row: ScheduleRow,
) -> dict[str, Any]:
    output = _base_output_row(config, row)
    if config.comparison == "A":
        output.update(
            {
                "classification": CLASS_OPERATIONAL_SPLIT,
                "trace_status": "CALLBACK_TRACE_UNAVAILABLE",
                "detail": (
                    "Comparison A changes the deck/state trajectory and retained "
                    "checked callback traces are unavailable; no policy-level "
                    "first-divergence claim is made."
                ),
            }
        )
        return output

    assert config.baseline_suite is not None
    assert config.candidate_suite is not None
    try:
        baseline = load_game_callbacks(
            config.baseline_suite,
            config.baseline_version,
            row,
            expected_result=row.baseline_result,
            expected_steps=row.baseline_steps,
            role="baseline",
        )
        candidate = load_game_callbacks(
            config.candidate_suite,
            config.candidate_version,
            row,
            expected_result=row.candidate_result,
            expected_steps=row.candidate_steps,
            role="candidate",
        )
    except TraceValidationError as exc:
        output.update(
            {
                "classification": CLASS_TRACE_INVALID,
                "trace_status": "INVALID",
                "detail": str(exc),
            }
        )
        return output

    raw_order_count = 0
    first_raw_order: int | None = None
    common_count = min(len(baseline), len(candidate))
    for ordinal in range(common_count):
        before = baseline[ordinal]
        after = candidate[ordinal]
        raw_order_here = False
        if before.ordinal != after.ordinal:
            output.update(
                {
                    "classification": CLASS_TRACE_INVALID,
                    "trace_status": "INVALID",
                    "detail": (
                        f"cross-version callback ordinal mismatch: "
                        f"{before.ordinal} != {after.ordinal}"
                    ),
                }
            )
            return output
        if before.pre_state_sha256 != after.pre_state_sha256:
            _attach_callback(output, before, after)
            output.update(
                {
                    "classification": CLASS_PRE_STATE_SPLIT,
                    "trace_status": "VALID",
                    "raw_order_only_count": raw_order_count,
                    "first_raw_order_only_ordinal": first_raw_order,
                    "detail": (
                        "The canonical observable pre-state differs before any "
                        "policy action can be attributed; comparison stops here."
                    ),
                }
            )
            return output
        if before.legal_sha256 != after.legal_sha256:
            if before.semantic_legal_sha256 == after.semantic_legal_sha256:
                raw_order_here = True
            else:
                _attach_callback(output, before, after)
                output.update(
                    {
                        "classification": CLASS_LEGAL_SET_SPLIT,
                        "trace_status": "VALID",
                        "raw_order_only_count": raw_order_count,
                        "first_raw_order_only_ordinal": first_raw_order,
                        "detail": (
                            "The canonical legal-option multisets differ at the "
                            "same observable pre-state; comparison stops here."
                        ),
                    }
                )
                return output
        if before.semantic_action_sha256 != after.semantic_action_sha256:
            _attach_callback(output, before, after)
            output.update(
                {
                    "classification": CLASS_POLICY_DIVERGENCE,
                    "trace_status": "VALID",
                    "raw_order_only_count": raw_order_count,
                    "first_raw_order_only_ordinal": first_raw_order,
                    "detail": (
                        "The selected semantic option multisets first differ at "
                        "this validated callback; no later re-alignment is used."
                    ),
                }
            )
            return output
        if before.selected_action != after.selected_action:
            raw_order_here = True
        if raw_order_here:
            raw_order_count += 1
            if first_raw_order is None:
                first_raw_order = ordinal

    if len(baseline) != len(candidate):
        output.update(
            {
                "classification": CLASS_TRACE_INVALID,
                "trace_status": "INVALID",
                "raw_order_only_count": raw_order_count,
                "first_raw_order_only_ordinal": first_raw_order,
                "detail": (
                    "Cross-version callback counts differ without an earlier "
                    "validated semantic policy divergence: "
                    f"baseline={len(baseline)}, candidate={len(candidate)}"
                ),
            }
        )
        return output

    output.update(
        {
            "classification": (
                CLASS_RAW_ORDER_ONLY if raw_order_count else CLASS_NO_DIVERGENCE
            ),
            "trace_status": "VALID",
            "raw_order_only_count": raw_order_count,
            "first_raw_order_only_ordinal": first_raw_order,
            "detail": (
                "Only raw option/action ordering differed; semantic comparison "
                "continued through the complete trace."
                if raw_order_count
                else "No policy divergence was found in the complete validated trace."
            ),
        }
    )
    return output


def extract_rows(config: ExtractionConfig) -> list[dict[str, Any]]:
    config = config.validated()
    rows = load_paired_rows(config.paired_results)
    if config.comparison in ROLE_BINDINGS:
        assert config.baseline_suite is not None
        assert config.candidate_suite is not None
        _suite_manifest(config.baseline_suite, config.baseline_version)
        _suite_manifest(config.candidate_suite, config.candidate_version)
    return [analyze_schedule(config, row) for row in rows]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: _canonical_cell(row.get(field)) for field in CSV_FIELDS}
            )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json(dict(row)) + "\n")


def _markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _write_markdown(
    path: Path,
    config: ExtractionConfig,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        name = str(row["classification"])
        counts[name] = counts.get(name, 0) + 1
    lines = [
        f"# Alakazam comparison {config.comparison}: first-divergence evidence",
        "",
        "This report records deterministic trace classification only. It does not "
        "interpret win rates or recommend a policy.",
        "",
        "## Provenance",
        "",
        f"- Paired results: `{config.paired_results.resolve()}`",
        f"- Paired results SHA-256: `{sha256_file(config.paired_results)}`",
        f"- Baseline version: `{config.baseline_version}`",
        f"- Candidate version: `{config.candidate_version}`",
        f"- Baseline deck SHA-256: `{config.baseline_deck_hash}`",
        f"- Candidate deck SHA-256: `{config.candidate_deck_hash}`",
    ]
    if config.baseline_suite is not None:
        baseline_manifest = config.baseline_suite / "suite_manifest.json"
        candidate_manifest = config.candidate_suite / "suite_manifest.json"  # type: ignore[operator]
        lines.extend(
            [
                f"- Baseline suite: `{config.baseline_suite.resolve()}`",
                f"- Baseline suite manifest SHA-256: `{sha256_file(baseline_manifest)}`",
                f"- Candidate suite: `{config.candidate_suite.resolve()}`",  # type: ignore[union-attr]
                f"- Candidate suite manifest SHA-256: `{sha256_file(candidate_manifest)}`",
            ]
        )
    else:
        lines.append(
            "- Callback provenance: `CALLBACK_TRACE_UNAVAILABLE` "
            "(comparison A is an operational deck/state split)."
        )
    lines.extend(["", "## Classification counts", ""])
    for name in sorted(counts):
        lines.append(f"- `{name}`: {counts[name]}")
    lines.extend(
        [
            "",
            "## Per-schedule evidence",
            "",
            "| opponent | seat | seed | game | classification | callback | detail |",
            "|---|---:|---:|---:|---|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {opponent} | {seat} | {seed} | {game} | {classification} | "
            "{callback} | {detail} |".format(
                opponent=_markdown_escape(row["opponent"]),
                seat=row["seat"],
                seed=row["seed"],
                game=row["game"],
                classification=_markdown_escape(row["classification"]),
                callback=(
                    ""
                    if row.get("callback_ordinal") is None
                    else row["callback_ordinal"]
                ),
                detail=_markdown_escape(row["detail"]),
            )
        )
    lines.extend(
        [
            "",
            "Canonical hashes use "
            "`json.dumps(ensure_ascii=True, sort_keys=True, separators=(',', ':'))` "
            "followed by SHA-256.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_outputs(
    config: ExtractionConfig,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": config.output_dir / f"{config.output_name}.csv",
        "jsonl": config.output_dir / f"{config.output_name}.jsonl",
        "markdown": config.output_dir / f"{config.output_name}.md",
    }
    _write_csv(paths["csv"], rows)
    _write_jsonl(paths["jsonl"], rows)
    _write_markdown(paths["markdown"], config, rows)
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract first validated Alakazam trace splits for comparison A, B, or C."
        )
    )
    parser.add_argument("--comparison", choices=("A", "B", "C"), required=True)
    parser.add_argument("--paired-results", type=Path, required=True)
    parser.add_argument("--baseline-suite", type=Path)
    parser.add_argument("--candidate-suite", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-name", required=True)
    parser.add_argument("--baseline-version", required=True)
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument("--baseline-deck-hash", required=True)
    parser.add_argument("--candidate-deck-hash", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ExtractionConfig(
        comparison=args.comparison,
        paired_results=args.paired_results,
        baseline_suite=args.baseline_suite,
        candidate_suite=args.candidate_suite,
        output_dir=args.output_dir,
        output_name=args.output_name,
        baseline_version=args.baseline_version,
        candidate_version=args.candidate_version,
        baseline_deck_hash=args.baseline_deck_hash,
        candidate_deck_hash=args.candidate_deck_hash,
    )
    try:
        config = config.validated()
        rows = extract_rows(config)
        paths = write_outputs(config, rows)
    except (InputValidationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = {
        "comparison": config.comparison,
        "rows": len(rows),
        "classifications": {
            name: sum(row["classification"] == name for row in rows)
            for name in sorted({str(row["classification"]) for row in rows})
        },
        "outputs": {
            name: {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for name, path in paths.items()
        },
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
