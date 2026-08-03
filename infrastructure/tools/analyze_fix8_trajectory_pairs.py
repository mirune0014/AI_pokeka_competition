#!/usr/bin/env python3
"""Export raw, mechanical C2/Fix8 same-seed trajectory evidence.

No causal labels, action ratings, aggregate performance claims, or adoption
recommendations are emitted. Both the 86-row discordant schedule and a full
paired schedule drawn from the same immutable source CSV are supported.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

from alakazam_staged_metrics import game_metrics

SCHEMA_VERSION = "fix8-trajectory-mechanical-v1"
BASELINE_VERSION = "c2"
CANDIDATE_VERSION = "fix8"
POFFIN_ID = 1086
ABRA_ID, KADABRA_ID, ALAKAZAM_ID = 741, 742, 743
DUNSPARCE_ID, DUDUNSPARCE_ID = 305, 343
REJOIN_FOLLOWING_CALLBACKS = 3
REQUIRED_COLUMNS = frozenset({
    "seed_base", "opponent", "seat", "game", "seed", "baseline_result",
    "candidate_result", "baseline_win", "candidate_win", "baseline_steps",
    "candidate_steps",
})
SEMANTIC_FIELDS = (
    "type", "card_id", "serial", "attack_id", "area", "in_play_area",
    "in_play_index", "player_index",
)
STATE_POINTS = (
    "divergence_pre", "next_policy_callback", "same_turn_end",
    "next_own_turn_start",
)
STATE_SCALARS = (
    "turn", "context", "hand_count", "poffin_hand_count", "own_deck_count",
    "own_prizes", "active_card_id", "active_serial", "active_hp",
    "active_energy_count", "bench_count", "abra_board_count",
    "kadabra_board_count", "alakazam_board_count", "dunsparce_board_count",
    "dudunsparce_board_count",
)
STATE_JSON_FIELDS = (
    "hand_card_ids", "active_energy_ids", "bench_line", "bench_card_ids",
    "bench_hp", "bench_energy_counts", "bench_energy_ids",
)
GAME_METRIC_FIELDS = (
    "first_attack_turn", "attack_turn_count", "attack_gap_tail_count",
    "attack_gap_tail_denominator", "attack_gap_between_count",
    "attack_gap_between_denominator", "max_consecutive_attack_turns",
    "attack_hand_mean", "second_alakazam_line_before_first_attack",
    "post_ko_continuity_count", "post_ko_continuity_denominator",
)

class IntegrityError(ValueError):
    """A structural fault that prevents trusted mechanical extraction."""

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def as_int(value: Any, *, label: str = "value") -> int:
    if isinstance(value, bool):
        raise IntegrityError(f"{label} must be an integer, got bool")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise IntegrityError(f"{label} must be an integer: {value!r}") from exc

def optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def resolve_input(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value.resolve() if value.is_absolute() else (root / value).resolve()

def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise IntegrityError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"JSON root must be an object: {path}")
    return value

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise IntegrityError(f"missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise IntegrityError(f"invalid JSON at {path}:{number}") from exc
            if not isinstance(value, dict):
                raise IntegrityError(f"non-object JSON row at {path}:{number}")
            rows.append(value)
    if not rows:
        raise IntegrityError(f"empty JSONL file: {path}")
    return rows

def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise IntegrityError(f"missing CSV file: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise IntegrityError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)

@dataclass(frozen=True)
class TargetKey:
    source_seed_base: int
    opponent: str
    seat: int
    source_game: int
    seed: int
    baseline_result: int
    candidate_result: int
    baseline_win: int
    candidate_win: int
    baseline_steps: int
    candidate_steps: int

    @property
    def key(self) -> tuple[str, int, int]:
        return self.opponent, self.seat, self.seed

    @property
    def outcome_stratum(self) -> str:
        return {
            (0, 1): "candidate_gain", (1, 0): "candidate_loss",
            (1, 1): "same_win", (0, 0): "same_loss",
        }[(self.baseline_win, self.candidate_win)]

@dataclass
class Callback:
    ordinal: int
    start: dict[str, Any]
    end: dict[str, Any]
    battle: dict[str, Any]

    @property
    def observation(self) -> dict[str, Any]:
        value = self.start.get("observation")
        return dict(value) if isinstance(value, Mapping) else {}

    @property
    def selected_options(self) -> list[dict[str, Any]]:
        value = self.end.get("selected_options")
        return [dict(row) for row in value] if isinstance(value, list) else []

@dataclass
class LoadedGame:
    version: str
    summary_path: Path
    sidecar_path: Path
    battle_path: Path
    summary: dict[str, Any]
    callbacks: list[Callback]
    battles: list[dict[str, Any]]

def parse_target_rows(path: Path) -> list[TargetKey]:
    fields, raw_rows = load_csv(path)
    missing = REQUIRED_COLUMNS.difference(fields)
    if missing:
        raise IntegrityError(f"keys CSV is missing columns: {sorted(missing)}")
    if not raw_rows:
        raise IntegrityError("keys CSV contains no data rows")
    output: list[TargetKey] = []
    seen: set[tuple[str, int, int]] = set()
    for number, raw in enumerate(raw_rows, 2):
        opponent = (raw.get("opponent") or "").strip()
        row = TargetKey(
            as_int(raw.get("seed_base"), label=f"row {number} seed_base"), opponent,
            as_int(raw.get("seat"), label=f"row {number} seat"),
            as_int(raw.get("game"), label=f"row {number} game"),
            as_int(raw.get("seed"), label=f"row {number} seed"),
            as_int(raw.get("baseline_result"), label="baseline_result"),
            as_int(raw.get("candidate_result"), label="candidate_result"),
            as_int(raw.get("baseline_win"), label="baseline_win"),
            as_int(raw.get("candidate_win"), label="candidate_win"),
            as_int(raw.get("baseline_steps"), label="baseline_steps"),
            as_int(raw.get("candidate_steps"), label="candidate_steps"),
        )
        if not opponent or row.seat not in (0, 1):
            raise IntegrityError(f"row {number} has invalid opponent/seat")
        if row.seed != row.source_seed_base + row.source_game:
            raise IntegrityError(f"row {number} seed != seed_base + game")
        if row.baseline_win != int(row.baseline_result == row.seat):
            raise IntegrityError(f"row {number} baseline outcome is inconsistent")
        if row.candidate_win != int(row.candidate_result == row.seat):
            raise IntegrityError(f"row {number} candidate outcome is inconsistent")
        if row.key in seen:
            raise IntegrityError(f"duplicate target key: {row.key}")
        seen.add(row.key)
        output.append(row)
    return sorted(output, key=lambda row: row.key)

def semantic_option(option: Mapping[str, Any], *, include_serial: bool = True) -> dict[str, Any]:
    fields = SEMANTIC_FIELDS if include_serial else tuple(
        field for field in SEMANTIC_FIELDS if field != "serial"
    )
    return {field: option.get(field) for field in fields}

def semantic_multiset(
    options: Iterable[Mapping[str, Any]], *, include_serial: bool = True
) -> list[dict[str, Any]]:
    return sorted(
        [semantic_option(row, include_serial=include_serial) for row in options],
        key=canonical_json,
    )

def semantic_action(callback: Callback, *, include_serial: bool = True) -> list[dict[str, Any]]:
    return semantic_multiset(callback.selected_options, include_serial=include_serial)

def semantic_legal(callback: Callback, *, include_serial: bool = True) -> list[dict[str, Any]]:
    options = callback.observation.get("options")
    if not isinstance(options, list) or not all(isinstance(row, Mapping) for row in options):
        raise IntegrityError(f"callback {callback.ordinal} options are invalid")
    return semantic_multiset(options, include_serial=include_serial)

def validate_source_binding(
    spec: Mapping[str, Any], targets: Sequence[TargetKey], keys_path: Path, root: Path
) -> dict[str, Any]:
    source = spec.get("source")
    if not isinstance(source, Mapping):
        raise IntegrityError("execution spec source must be an object")
    paired = resolve_input(str(source.get("paired_csv")), root)
    actual_sha = sha256_file(paired)
    if actual_sha != str(source.get("sha256") or "").lower():
        raise IntegrityError("source paired CSV SHA mismatch")
    fields, rows = load_csv(paired)
    if REQUIRED_COLUMNS.difference(fields):
        raise IntegrityError("source paired CSV is missing required columns")
    if len(rows) != as_int(source.get("total_rows"), label="source.total_rows"):
        raise IntegrityError("source paired CSV row count mismatch")
    source_rows = {
        (str(row["opponent"]), as_int(row["seat"]), as_int(row["seed"])): row
        for row in rows
    }
    if len(source_rows) != len(rows):
        raise IntegrityError("source paired key is not unique")
    for target in targets:
        raw = source_rows.get(target.key)
        if raw is None:
            raise IntegrityError(f"target absent from source: {target.key}")
        expected = {
            "seed_base": target.source_seed_base, "game": target.source_game,
            "baseline_result": target.baseline_result,
            "candidate_result": target.candidate_result,
            "baseline_win": target.baseline_win, "candidate_win": target.candidate_win,
            "baseline_steps": target.baseline_steps, "candidate_steps": target.candidate_steps,
        }
        if any(as_int(raw[field]) != value for field, value in expected.items()):
            raise IntegrityError(f"source/target field mismatch: {target.key}")
    key_sha = sha256_file(keys_path)
    declared = str((spec.get("output") or {}).get("discordant_keys_sha256") or "").lower()
    if key_sha == declared:
        discordant = {
            key for key, row in source_rows.items()
            if as_int(row["baseline_win"]) != as_int(row["candidate_win"])
        }
        if (
            len(targets) != as_int(source.get("discordant_rows"))
            or {row.key for row in targets} != discordant
        ):
            raise IntegrityError("declared discordant schedule does not match source")
    elif key_sha == actual_sha and len(targets) != len(rows):
        raise IntegrityError("full-source keys SHA supplied with non-full target set")
    return {
        "path": str(paired), "sha256": actual_sha, "rows": len(rows),
        "keys_sha256": key_sha, "target_rows": len(targets),
    }

def validate_declared_files(spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    runtime = spec.get("runtime")
    if not isinstance(runtime, Mapping):
        raise IntegrityError("execution spec runtime must be an object")
    pairs = (
        ("metric_runner", "metric_runner_sha256"),
        ("metric_module", "metric_module_sha256"),
        ("battle_runner", "battle_runner_sha256"),
    )
    verified = []
    for path_key, sha_key in pairs:
        path = resolve_input(str(runtime.get(path_key)), root)
        actual = sha256_file(path)
        if actual != str(runtime.get(sha_key) or "").lower():
            raise IntegrityError(f"{path_key} SHA mismatch")
        verified.append({"label": path_key, "path": str(path), "sha256": actual})
    for path_key, sha_key in (
        ("baseline", "baseline_main_sha256"),
        ("candidate", "candidate_main_sha256"),
    ):
        path = resolve_input(str(runtime.get(path_key)), root) / "main.py"
        actual = sha256_file(path)
        if actual != str(runtime.get(sha_key) or "").lower():
            raise IntegrityError(f"{path_key} main SHA mismatch")
        verified.append({"label": f"{path_key}_main", "path": str(path), "sha256": actual})
    return {"verified_files": verified}

def pair_callback_events(
    rows: Sequence[Mapping[str, Any]], *, version: str | None = None,
    opponent: str | None = None, seat: int | None = None, seed: int | None = None,
    seed_base: int | None = None, game: int | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    starts: dict[int, dict[str, Any]] = {}
    ends: dict[int, dict[str, Any]] = {}
    identity: tuple[Any, ...] | None = None
    for position, raw in enumerate(rows):
        event = dict(raw)
        kind = event.get("event")
        if kind not in {"CALL_START", "CALL_END"}:
            raise IntegrityError(f"unknown sidecar event at row {position}: {kind!r}")
        ordinal = as_int(event.get("callback_ordinal"), label="callback_ordinal")
        actual = (
            event.get("run_id"), event.get("version"), event.get("opponent"),
            as_int(event.get("policy_seat")), as_int(event.get("game")),
            as_int(event.get("seed")), as_int(event.get("seed_base")),
        )
        if not isinstance(actual[0], str) or not actual[0]:
            raise IntegrityError("sidecar run_id is missing")
        if identity is None:
            identity = actual
        elif actual != identity:
            raise IntegrityError(f"mixed sidecar identity: {actual} != {identity}")
        expected = (
            (version, actual[1]), (opponent, actual[2]), (seat, actual[3]),
            (game, actual[4]), (seed, actual[5]), (seed_base, actual[6]),
        )
        if any(want is not None and want != got for want, got in expected):
            raise IntegrityError("sidecar identity does not match target")
        destination = starts if kind == "CALL_START" else ends
        if ordinal in destination:
            raise IntegrityError(f"duplicate {kind} ordinal {ordinal}")
        destination[ordinal] = event
    ordinals = sorted(set(starts) | set(ends))
    if ordinals != list(range(len(ordinals))):
        raise IntegrityError("callback ordinals are not a zero-based prefix")
    if set(starts) != set(ends):
        raise IntegrityError("orphan callback events")
    return [(starts[index], ends[index]) for index in ordinals]

def validate_selected_action(start: Mapping[str, Any], end: Mapping[str, Any], ordinal: int) -> None:
    observation = start.get("observation")
    if not isinstance(observation, Mapping):
        raise IntegrityError(f"callback {ordinal} observation is invalid")
    options = observation.get("options")
    action = end.get("selected_action")
    selected = end.get("selected_options")
    if not isinstance(options, list) or not all(isinstance(row, Mapping) for row in options):
        raise IntegrityError(f"callback {ordinal} options are invalid")
    if as_int(observation.get("option_count")) != len(options):
        raise IntegrityError(f"callback {ordinal} option_count mismatch")
    if any(as_int(row.get("option_index")) != index for index, row in enumerate(options)):
        raise IntegrityError(f"callback {ordinal} option_index mismatch")
    if not isinstance(action, list):
        raise IntegrityError(f"callback {ordinal} action is invalid")
    indices = [as_int(value) for value in action]
    if len(indices) != len(set(indices)) or any(index not in range(len(options)) for index in indices):
        raise IntegrityError(f"callback {ordinal} action index is invalid")
    expected = [options[index] for index in indices]
    if not isinstance(selected, list) or canonical_json(selected) != canonical_json(expected):
        raise IntegrityError(f"callback {ordinal} selected_options mismatch")
    if end.get("structurally_valid") is not True or end.get("exception") is not None:
        raise IntegrityError(f"callback {ordinal} policy result is invalid")

def validate_battles(battles: Sequence[Mapping[str, Any]], summary: Mapping[str, Any], game: int, seed: int) -> None:
    if len(battles) != as_int(summary.get("steps")):
        raise IntegrityError("battle row count differs from summary steps")
    for position, row in enumerate(battles):
        if as_int(row.get("step")) != position or as_int(row.get("game")) != game:
            raise IntegrityError(f"battle step/game mismatch at {position}")
        if as_int(row.get("player")) not in (0, 1):
            raise IntegrityError(f"invalid battle player at {position}")
    if as_int(summary.get("seed")) != seed or summary.get("started") is not True:
        raise IntegrityError("summary seed/started mismatch")
    if summary.get("hit_max_steps") is not False or as_int(summary.get("action_errors")) != 0:
        raise IntegrityError("summary reports max-step or action error")
    if as_int(summary.get("result")) not in (0, 1, 2):
        raise IntegrityError("summary result is invalid")

def load_game(
    suite: Path, *, version: str, opponent: str, seat: int, seed: int,
    run_seed_base: int, game: int,
) -> LoadedGame:
    run = suite / "runs" / version / opponent / f"seed_{run_seed_base}" / f"seat_{seat}"
    summary_path = run / "summary.jsonl"
    sidecar_path = run / "sidecars" / f"game_{game:04d}.jsonl"
    battle_path = run / "battle_traces" / f"game_{game:04d}.jsonl"
    summaries = load_jsonl(summary_path)
    by_game = {as_int(row.get("game")): row for row in summaries}
    if len(by_game) != len(summaries) or game not in by_game:
        raise IntegrityError(f"missing or duplicate summary game {game}: {summary_path}")
    summary = by_game[game]
    battles = load_jsonl(battle_path)
    validate_battles(battles, summary, game, seed)
    pairs = pair_callback_events(
        load_jsonl(sidecar_path), version=version, opponent=opponent, seat=seat,
        seed=seed, seed_base=run_seed_base, game=game,
    )
    target_battles = [dict(row) for row in battles if as_int(row.get("player")) == seat]
    if len(target_battles) != len(pairs):
        raise IntegrityError("sidecar/battle target callback count mismatch")
    callbacks = []
    for ordinal, ((start, end), battle) in enumerate(zip(pairs, target_battles)):
        validate_selected_action(start, end, ordinal)
        obs = start["observation"]
        checks = {
            "context": (obs.get("context"), battle.get("context")),
            "select_type": (obs.get("select_type"), battle.get("select_type")),
            "min_count": (obs.get("min_count"), battle.get("min_count")),
            "max_count": (obs.get("max_count"), battle.get("max_count")),
            "option_count": (obs.get("option_count"), battle.get("option_count")),
            "turn": (obs.get("turn"), (battle.get("snapshot") or {}).get("turn")),
            "turn_action_count": (obs.get("turn_action_count"), (battle.get("snapshot") or {}).get("turn_action_count")),
        }
        if any(as_int(left) != as_int(right) for left, right in checks.values()):
            raise IntegrityError(f"callback {ordinal} sidecar/battle observation mismatch")
        action = [as_int(value) for value in end["selected_action"]]
        hand = obs.get("own_hand")
        hand_ids = [row[0] for row in hand or [] if isinstance(row, list) and len(row) == 2]
        if action != battle.get("action") or len(hand_ids) != len(hand or []) or hand_ids != battle.get("own_hand_ids"):
            raise IntegrityError(f"callback {ordinal} sidecar/battle action or hand mismatch")
        callbacks.append(Callback(ordinal, dict(start), dict(end), dict(battle)))
    return LoadedGame(version, summary_path, sidecar_path, battle_path, summary, callbacks, battles)

def resolve_suite_layout(metric_root: Path, opponents: Iterable[str]) -> dict[str, Path]:
    """Resolve one multi-opponent suite or one child suite per opponent."""
    names = sorted(set(opponents))
    if (metric_root / "suite_execution_summary.json").is_file():
        return {name: metric_root.resolve() for name in names}
    return {name: (metric_root / name).resolve() for name in names}

def validate_suite(
    suite: Path, *, targets_by_opponent: Mapping[str, Sequence[TargetKey]],
    spec: Mapping[str, Any], root: Path,
) -> tuple[dict[str, Any], dict[tuple[str, int, int], tuple[int, int]]]:
    expected_opponent_names = set(targets_by_opponent)
    if not expected_opponent_names:
        raise IntegrityError("suite target opponent set is empty")
    manifest_path = suite / "suite_manifest.json"
    execution_path = suite / "suite_execution_summary.json"
    ledger_path = suite / "block_ledger.jsonl"
    manifest = load_json(manifest_path)
    execution = load_json(execution_path)
    ledger = load_jsonl(ledger_path)
    runtime = spec.get("runtime") or {}
    if manifest.get("schema_version") != "alakazam-staged-metrics-v1":
        raise IntegrityError(f"unexpected suite schema: {suite}")
    games = as_int(manifest.get("games_per_block"), label="games_per_block")
    if games <= 0 or manifest.get("max_steps") != runtime.get("max_steps"):
        raise IntegrityError(f"suite games/max_steps mismatch: {suite}")
    expected_hashes = {
        "launcher_sha256": str(runtime.get("metric_runner_sha256") or "").lower(),
        "common_module_sha256": str(runtime.get("metric_module_sha256") or "").lower(),
        "run_local_battle_sha256": str(runtime.get("battle_runner_sha256") or "").lower(),
    }
    if any(str(manifest.get(field) or "").lower() != value for field, value in expected_hashes.items()):
        raise IntegrityError(f"suite runner/module identity mismatch: {suite}")
    opponents = {
        str(row.get("name")): row for row in manifest.get("opponents") or []
        if isinstance(row, Mapping)
    }
    if set(opponents) != expected_opponent_names:
        raise IntegrityError(f"suite opponent declaration mismatch: {suite}")
    for opponent in expected_opponent_names:
        expected_path = resolve_input(str((spec.get("opponents") or {}).get(opponent)), root)
        if Path(str(opponents[opponent].get("path"))).resolve() != expected_path:
            raise IntegrityError(f"suite opponent path mismatch: {suite} {opponent}")
    versions = {
        str(row.get("name")): row for row in manifest.get("versions") or []
        if isinstance(row, Mapping)
    }
    if set(versions) != {BASELINE_VERSION, CANDIDATE_VERSION}:
        raise IntegrityError(f"suite version declaration mismatch: {suite}")
    expected_targets = {
        BASELINE_VERSION: resolve_input(str(runtime.get("baseline")), root),
        CANDIDATE_VERSION: resolve_input(str(runtime.get("candidate")), root),
    }
    if any(Path(str(versions[name].get("target"))).resolve() != path for name, path in expected_targets.items()):
        raise IntegrityError(f"suite version target mismatch: {suite}")
    seeds = {as_int(value) for value in manifest.get("seed_bases") or []}
    target_locations: dict[tuple[str, int, int], tuple[int, int]] = {}
    for targets in targets_by_opponent.values():
        for target in targets:
            if games == 1 and target.seed in seeds:
                location = target.seed, 0
            elif target.source_seed_base in seeds and 0 <= target.source_game < games:
                location = target.source_seed_base, target.source_game
            else:
                raise IntegrityError(f"target has no suite block/game: {target.key}")
            target_locations[target.key] = location
    expected_blocks = len(seeds) * 4 * len(expected_opponent_names)
    if len(ledger) != expected_blocks:
        raise IntegrityError(f"suite ledger rows mismatch: {len(ledger)} != {expected_blocks}")
    if execution.get("all_blocks_complete") is not True or as_int(execution.get("blocks")) != expected_blocks:
        raise IntegrityError(f"suite execution is incomplete: {suite}")
    seen: set[tuple[str, str, int, int]] = set()
    counts = {"summary_files": 0, "sidecar_files": 0, "battle_trace_files": 0}
    for block in ledger:
        identity = (
            str(block.get("version")), str(block.get("opponent")),
            as_int(block.get("seat")), as_int(block.get("seed_base")),
        )
        if identity in seen:
            raise IntegrityError(f"duplicate ledger identity: {identity}")
        seen.add(identity)
        version, block_opponent, seat, seed_base = identity
        if version not in versions or block_opponent not in opponents or seat not in (0, 1) or seed_base not in seeds:
            raise IntegrityError(f"unexpected ledger identity: {identity}")
        if block.get("block_complete") is not True or as_int(block.get("return_code")) != 0 or block.get("timed_out") is not False:
            raise IntegrityError(f"failed/partial ledger block: {identity}")
        block_dir = suite / "runs" / version / block_opponent / f"seed_{seed_base}" / f"seat_{seat}"
        if Path(str(block.get("block_dir"))).resolve() != block_dir.resolve():
            raise IntegrityError(f"ledger block path mismatch: {identity}")
        summary = block_dir / "summary.jsonl"
        if not summary.is_file() or not summary.stat().st_size:
            raise IntegrityError(f"missing/empty summary: {summary}")
        if sha256_file(summary) != str(block.get("summary_sha256") or "").lower():
            raise IntegrityError(f"ledger summary SHA mismatch: {identity}")
        summary_rows = load_jsonl(summary)
        if len(summary_rows) != games or {as_int(row.get("game")) for row in summary_rows} != set(range(games)):
            raise IntegrityError(f"summary game set mismatch: {identity}")
        counts["summary_files"] += 1
        for game in range(games):
            sidecar = block_dir / "sidecars" / f"game_{game:04d}.jsonl"
            battle = block_dir / "battle_traces" / f"game_{game:04d}.jsonl"
            if not sidecar.is_file() or not sidecar.stat().st_size:
                raise IntegrityError(f"missing/empty sidecar: {sidecar}")
            if not battle.is_file() or not battle.stat().st_size:
                raise IntegrityError(f"missing/empty battle trace: {battle}")
            counts["sidecar_files"] += 1
            counts["battle_trace_files"] += 1
    report = {
        "suite": str(suite), "games_per_block": games,
        "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "execution_summary": str(execution_path), "execution_summary_sha256": sha256_file(execution_path),
        "ledger": str(ledger_path), "ledger_sha256": sha256_file(ledger_path),
        "ledger_rows": len(ledger), **counts,
    }
    return report, target_locations

def normalized_observation(callback: Callback) -> dict[str, Any]:
    return {
        str(key): value for key, value in callback.observation.items()
        if key not in {"options", "option_count"}
    }

def first_semantic_divergence(
    baseline: Sequence[Callback], candidate: Sequence[Callback]
) -> dict[str, Any]:
    prior_equal = True
    raw_order_only = 0
    for ordinal in range(min(len(baseline), len(candidate))):
        left, right = baseline[ordinal], candidate[ordinal]
        if left.ordinal != right.ordinal:
            raise IntegrityError("cross-version callback ordinal mismatch")
        state_equal = canonical_json(normalized_observation(left)) == canonical_json(normalized_observation(right))
        legal_equal = semantic_legal(left) == semantic_legal(right)
        left_action, right_action = semantic_action(left), semantic_action(right)
        if left_action != right_action:
            return {
                "found": True, "ordinal": ordinal,
                "prior_observation_states_equal": prior_equal,
                "divergence_pre_observation_equal": state_equal,
                "divergence_semantic_legal_equal": legal_equal,
                "raw_order_only_before_divergence": raw_order_only,
                "baseline_action": left_action, "candidate_action": right_action,
                "baseline_action_no_serial": semantic_action(left, include_serial=False),
                "candidate_action_no_serial": semantic_action(right, include_serial=False),
            }
        if state_equal and legal_equal and left.end.get("selected_action") != right.end.get("selected_action"):
            raw_order_only += 1
        if not state_equal:
            return {
                "found": False, "ordinal": ordinal,
                "prior_observation_states_equal": prior_equal,
                "divergence_pre_observation_equal": False,
                "divergence_semantic_legal_equal": legal_equal,
                "raw_order_only_before_divergence": raw_order_only,
                "reason": "OBSERVATION_SPLIT_BEFORE_SEMANTIC_ACTION_SPLIT",
            }
        prior_equal = prior_equal and state_equal
    return {
        "found": False, "ordinal": min(len(baseline), len(candidate)),
        "prior_observation_states_equal": prior_equal,
        "divergence_pre_observation_equal": None,
        "divergence_semantic_legal_equal": None,
        "raw_order_only_before_divergence": raw_order_only,
        "reason": "CALLBACK_LENGTH_SPLIT" if len(baseline) != len(candidate) else "NO_SEMANTIC_ACTION_SPLIT",
    }

def board_entries(callback: Callback, seat: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    obs, snapshot = callback.observation, callback.battle.get("snapshot") or {}
    prefix = f"p{seat}_"
    pair = obs.get("own_active")
    active = None
    if isinstance(pair, list) and len(pair) >= 2:
        active = {
            "card_id": optional_int(pair[0]), "serial": optional_int(pair[1]),
            "hp": optional_int(snapshot.get(prefix + "active_hp")),
            "max_hp": optional_int(snapshot.get(prefix + "active_max_hp")),
            "energy_count": optional_int(snapshot.get(prefix + "active_energy")) or 0,
            "energy_ids": list(snapshot.get(prefix + "active_energy_ids") or []),
            "tool_ids": list(snapshot.get(prefix + "active_tool_ids") or []),
        }
    pairs = obs.get("own_bench") or []
    ids, hp = list(snapshot.get(prefix + "bench") or []), list(snapshot.get(prefix + "bench_hp") or [])
    max_hp = list(snapshot.get(prefix + "bench_max_hp") or [])
    energy = list(snapshot.get(prefix + "bench_energy") or [])
    energy_ids = list(snapshot.get(prefix + "bench_energy_ids") or [])
    tools = list(snapshot.get(prefix + "bench_tool_ids") or [])
    count = max(len(pairs), len(ids), len(hp), len(energy))
    bench = []
    for index in range(count):
        item = pairs[index] if index < len(pairs) else None
        bench.append({
            "index": index,
            "card_id": optional_int(item[0]) if isinstance(item, list) and item else optional_int(ids[index]) if index < len(ids) else None,
            "serial": optional_int(item[1]) if isinstance(item, list) and len(item) > 1 else None,
            "hp": optional_int(hp[index]) if index < len(hp) else None,
            "max_hp": optional_int(max_hp[index]) if index < len(max_hp) else None,
            "energy_count": optional_int(energy[index]) or 0 if index < len(energy) else 0,
            "energy_ids": list(energy_ids[index] or []) if index < len(energy_ids) else [],
            "tool_ids": list(tools[index] or []) if index < len(tools) else [],
        })
    return active, bench

def state_features(callback: Callback, seat: int) -> dict[str, Any]:
    obs, snapshot = callback.observation, callback.battle.get("snapshot") or {}
    prefix = f"p{seat}_"
    hand = obs.get("own_hand") or []
    hand_ids = [optional_int(pair[0]) for pair in hand if isinstance(pair, list) and pair]
    active, bench = board_entries(callback, seat)
    board_ids = ([active["card_id"]] if active and active.get("card_id") is not None else []) + [row["card_id"] for row in bench if row.get("card_id") is not None]
    return {
        "callback_ordinal": callback.ordinal,
        "battle_step": optional_int(callback.battle.get("step")),
        "turn": optional_int(obs.get("turn")), "context": optional_int(obs.get("context")),
        "hand_count": len(hand), "hand_card_ids": hand_ids,
        "poffin_hand_count": hand_ids.count(POFFIN_ID),
        "own_deck_count": optional_int(snapshot.get(prefix + "deck")),
        "own_prizes": optional_int(snapshot.get(prefix + "prizes")),
        "active_card_id": active.get("card_id") if active else None,
        "active_serial": active.get("serial") if active else None,
        "active_hp": active.get("hp") if active else None,
        "active_energy_count": active.get("energy_count") if active else 0,
        "active_energy_ids": active.get("energy_ids") if active else [],
        "bench_count": len(bench), "bench_line": bench,
        "bench_card_ids": [row["card_id"] for row in bench],
        "bench_hp": [row["hp"] for row in bench],
        "bench_energy_counts": [row["energy_count"] for row in bench],
        "bench_energy_ids": [row["energy_ids"] for row in bench],
        "abra_board_count": board_ids.count(ABRA_ID),
        "kadabra_board_count": board_ids.count(KADABRA_ID),
        "alakazam_board_count": board_ids.count(ALAKAZAM_ID),
        "dunsparce_board_count": board_ids.count(DUNSPARCE_ID),
        "dudunsparce_board_count": board_ids.count(DUDUNSPARCE_ID),
    }

def state_point_indices(callbacks: Sequence[Callback], divergence: int) -> dict[str, int | None]:
    if divergence not in range(len(callbacks)):
        return {point: None for point in STATE_POINTS}
    turn = optional_int(callbacks[divergence].observation.get("turn"))
    same_turn = [index for index in range(divergence, len(callbacks)) if optional_int(callbacks[index].observation.get("turn")) == turn]
    next_main = next((
        index for index in range(divergence + 1, len(callbacks))
        if optional_int(callbacks[index].observation.get("context")) == 0
        and optional_int(callbacks[index].observation.get("turn")) is not None
        and (turn is None or optional_int(callbacks[index].observation.get("turn")) > turn)
    ), None)
    return {
        "divergence_pre": divergence,
        "next_policy_callback": divergence + 1 if divergence + 1 < len(callbacks) else None,
        "same_turn_end": same_turn[-1] if same_turn else divergence,
        "next_own_turn_start": next_main,
    }

def extract_state_points(callbacks: Sequence[Callback], divergence: int, seat: int) -> dict[str, Any]:
    return {
        point: state_features(callbacks[index], seat) if index is not None else None
        for point, index in state_point_indices(callbacks, divergence).items()
    }

def rejoin_state(callback: Callback, seat: int) -> dict[str, Any]:
    snapshot = callback.battle.get("snapshot") or {}
    public: dict[str, Any] = {}
    suffixes = (
        "deck", "hand", "prizes", "bench_max", "active", "active_hp",
        "active_max_hp", "active_energy", "active_energy_ids", "active_tool_ids",
        "bench", "bench_hp", "bench_max_hp", "bench_energy", "bench_energy_ids",
        "bench_tool_ids",
    )
    for player in (0, 1):
        for suffix in suffixes:
            public[f"p{player}_{suffix}"] = snapshot.get(f"p{player}_{suffix}")
    hand = sorted(
        optional_int(pair[0]) for pair in callback.observation.get("own_hand") or []
        if isinstance(pair, list) and pair and optional_int(pair[0]) is not None
    )
    return {
        "turn": optional_int(callback.observation.get("turn")), "player": seat,
        "context": optional_int(callback.observation.get("context")),
        "public_snapshot": public, "own_hand_card_id_multiset": hand,
        "semantic_legal_multiset": semantic_legal(callback),
    }

def find_certified_observable_rejoin(
    baseline: Sequence[Callback], candidate: Sequence[Callback], *,
    baseline_start: int, candidate_start: int, seat: int,
    following_callbacks: int = REJOIN_FOLLOWING_CALLBACKS,
) -> dict[str, Any]:
    window = 1 + following_callbacks
    for left in range(max(0, baseline_start), len(baseline) - window + 1):
        anchor = rejoin_state(baseline[left], seat)
        for right in range(max(0, candidate_start), len(candidate) - window + 1):
            if anchor != rejoin_state(candidate[right], seat):
                continue
            matched = all(
                rejoin_state(baseline[left + offset], seat) == rejoin_state(candidate[right + offset], seat)
                and semantic_action(baseline[left + offset]) == semantic_action(candidate[right + offset])
                for offset in range(1, window)
            )
            if matched:
                return {
                    "certified_observable_rejoin": True,
                    "baseline_callback_ordinal": baseline[left].ordinal,
                    "candidate_callback_ordinal": candidate[right].ordinal,
                    "turn": anchor["turn"], "context": anchor["context"],
                    "following_callbacks_verified": following_callbacks,
                    "scope": "OBSERVABLE_ONLY; does not certify deck order or hidden RNG state",
                }
    return {
        "certified_observable_rejoin": False,
        "baseline_callback_ordinal": None, "candidate_callback_ordinal": None,
        "turn": None, "context": None, "following_callbacks_verified": 0,
        "scope": "NO_CERTIFIED_OBSERVABLE_REJOIN_FOUND",
    }

def recursive_named_mappings(value: Any, name: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == name and isinstance(item, Mapping):
                found.append(dict(item))
            found.extend(recursive_named_mappings(item, name))
    elif isinstance(value, list):
        for item in value:
            found.extend(recursive_named_mappings(item, name))
    return found

def fix8_trace_from_end(end: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    trace = end.get("version_trace")
    if not isinstance(trace, Mapping):
        return None, "MISSING_VERSION_TRACE"
    parent = trace.get("parent_trace")
    if isinstance(parent, Mapping):
        nested = parent.get("LAST_V4_POFFIN_ZERO_VETO_TRACE")
        if isinstance(nested, Mapping):
            return dict(nested), "version_trace.parent_trace.LAST_V4_POFFIN_ZERO_VETO_TRACE"
    if trace.get("rule") == "V4_POFFIN_ZERO_DEMAND_VETO_PERSISTENCE_FIX8":
        return dict(trace), "version_trace"
    recursive = recursive_named_mappings(trace, "LAST_V4_POFFIN_ZERO_VETO_TRACE")
    return (recursive[0], "version_trace.recursive.LAST_V4_POFFIN_ZERO_VETO_TRACE") if recursive else (None, "NOT_FOUND")

def outcome_check(summary: Mapping[str, Any], seat: int, expected_win: int) -> dict[str, Any]:
    result = as_int(summary.get("result"), label="summary result")
    rerun_win = int(result == seat)
    return {
        "rerun_result": result, "rerun_policy_win": rerun_win,
        "source_policy_win": expected_win, "matches_source": rerun_win == expected_win,
    }

def prize_progression(battles: Sequence[Mapping[str, Any]], seat: int) -> list[dict[str, Any]]:
    key, output, previous, initialized = f"p{seat}_prizes", [], None, False
    for row in battles:
        snapshot = row.get("snapshot") or {}
        value = optional_int(snapshot.get(key))
        if value is None:
            continue
        initialized = initialized or value > 0
        if initialized and value != previous:
            output.append({
                "step": optional_int(row.get("step")), "turn": optional_int(snapshot.get("turn")),
                "prizes": value, "delta": None if previous is None else value - previous,
            })
        previous = value
    return output

def ko_events(battles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    previous: list[dict[str, Any]] = []
    cumulative = any(
        left and len(right) > len(left) and right[:len(left)] == left
        for left, right in zip(
            ((row.get("logs") or []) for row in battles),
            ((row.get("logs") or []) for row in battles[1:]),
        )
    )
    for row in battles:
        logs = row.get("logs") or []
        new = logs[len(previous):] if cumulative and previous and logs[:len(previous)] == previous else logs
        previous = logs
        for log in new:
            if not isinstance(log, Mapping):
                continue
            if optional_int(log.get("type")) == 6 and optional_int(log.get("fromArea")) in {4, 5} and optional_int(log.get("toArea")) == 3:
                output.append({
                    "step": optional_int(row.get("step")),
                    "turn": optional_int((row.get("snapshot") or {}).get("turn")),
                    "player": optional_int(log.get("playerIndex")),
                    "card_id": optional_int(log.get("cardId")),
                    "serial": optional_int(log.get("serial")),
                    "from_area": optional_int(log.get("fromArea")),
                })
    return output

def poffin_after(callbacks: Sequence[Callback], divergence: int) -> dict[str, Any]:
    events = []
    for callback in callbacks[divergence + 1:]:
        selected = [row for row in callback.selected_options if optional_int(row.get("card_id")) == POFFIN_ID]
        if selected:
            events.append({
                "callback_ordinal": callback.ordinal,
                "turn": optional_int(callback.observation.get("turn")),
                "context": optional_int(callback.observation.get("context")),
                "selected_options": selected,
            })
    return {"count": len(events), "events": events}

def callback_window(callbacks: Sequence[Callback], divergence: int) -> list[dict[str, Any]]:
    output = []
    for callback in callbacks[max(0, divergence - 2):min(len(callbacks), divergence + 5)]:
        output.append({
            "callback_ordinal": callback.ordinal, "observation": callback.observation,
            "selected_action": callback.end.get("selected_action"),
            "selected_options": callback.selected_options,
            "semantic_action": semantic_action(callback),
            "semantic_action_no_serial": semantic_action(callback, include_serial=False),
            "battle_step": callback.battle.get("step"),
            "battle_snapshot": callback.battle.get("snapshot"),
            "battle_logs": callback.battle.get("logs"),
        })
    return output

def load_card_names(engine_dir: Path) -> dict[int, str]:
    try:
        from ptcg_common import ensure_engine_on_path
        ensure_engine_on_path(engine_dir)
        from cg.api import all_card_data
        return {int(card.cardId): str(card.name) for card in all_card_data()}
    except Exception:
        return {}

def selected_with_names(options: Sequence[Mapping[str, Any]], names: Mapping[int, str]) -> list[dict[str, Any]]:
    output = []
    for option in options:
        card_id = optional_int(option.get("card_id"))
        output.append({
            "option_index": option.get("option_index"),
            **semantic_option(option),
            "card_name": names.get(card_id) if card_id is not None else None,
        })
    return output

def flatten_state(row: dict[str, Any], version: str, states: Mapping[str, Any]) -> None:
    for point in STATE_POINTS:
        state = states.get(point)
        for field in STATE_SCALARS:
            row[f"{version}_{point}_{field}"] = state.get(field) if state else None
        for field in STATE_JSON_FIELDS:
            row[f"{version}_{point}_{field}"] = canonical_json(state.get(field)) if state else ""

def flatten_metrics(
    row: dict[str, Any], version: str, metrics: Mapping[str, Any], attack_count: int,
    prizes: Sequence[Mapping[str, Any]], kos: Sequence[Mapping[str, Any]], poffin: Mapping[str, Any],
) -> None:
    for field in GAME_METRIC_FIELDS:
        row[f"{version}_{field}"] = metrics.get(field)
    row[f"{version}_attack_count"] = attack_count
    row[f"{version}_hand_power_attacks"] = canonical_json(metrics.get("hand_power_attacks"))
    row[f"{version}_post_ko_events"] = canonical_json(metrics.get("post_ko_events"))
    row[f"{version}_prize_progression"] = canonical_json(prizes)
    row[f"{version}_ko_events"] = canonical_json(kos)
    row[f"{version}_poffin_later_use_count"] = poffin.get("count")
    row[f"{version}_poffin_later_use_events"] = canonical_json(poffin.get("events"))

def analyze_pair(
    target: TargetKey, suite: Path, run_location: tuple[int, int],
    card_names: Mapping[int, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    run_seed_base, game = run_location
    baseline = load_game(
        suite, version=BASELINE_VERSION, opponent=target.opponent, seat=target.seat,
        seed=target.seed, run_seed_base=run_seed_base, game=game,
    )
    candidate = load_game(
        suite, version=CANDIDATE_VERSION, opponent=target.opponent, seat=target.seat,
        seed=target.seed, run_seed_base=run_seed_base, game=game,
    )
    b_out = outcome_check(baseline.summary, target.seat, target.baseline_win)
    c_out = outcome_check(candidate.summary, target.seat, target.candidate_win)
    divergence = first_semantic_divergence(baseline.callbacks, candidate.callbacks)
    index = optional_int(divergence.get("ordinal"))
    aligned = (
        divergence.get("found") is True
        and index is not None
        and divergence.get("prior_observation_states_equal") is True
        and divergence.get("divergence_pre_observation_equal") is True
        and divergence.get("divergence_semantic_legal_equal") is True
    )
    outcomes_match = b_out["matches_source"] and c_out["matches_source"]
    exclusions = []
    if not b_out["matches_source"]:
        exclusions.append("BASELINE_OUTCOME_MISMATCH")
    if not c_out["matches_source"]:
        exclusions.append("CANDIDATE_OUTCOME_MISMATCH")
    if not divergence.get("found"):
        exclusions.append(str(divergence.get("reason") or "NO_SEMANTIC_ACTION_SPLIT"))
    elif not aligned:
        exclusions.append("UNTRUSTED_PRE_DIVERGENCE_ALIGNMENT")
    eligible = outcomes_match and aligned
    valid_index = index is not None and index < len(baseline.callbacks) and index < len(candidate.callbacks)
    b_callback = baseline.callbacks[index] if valid_index else None
    c_callback = candidate.callbacks[index] if valid_index else None
    b_states = extract_state_points(baseline.callbacks, index, target.seat) if valid_index else {point: None for point in STATE_POINTS}
    c_states = extract_state_points(candidate.callbacks, index, target.seat) if valid_index else {point: None for point in STATE_POINTS}
    rejoin = find_certified_observable_rejoin(
        baseline.callbacks, candidate.callbacks,
        baseline_start=(index or 0) + 1, candidate_start=(index or 0) + 1,
        seat=target.seat,
    ) if divergence.get("found") else {
        "certified_observable_rejoin": False,
        "baseline_callback_ordinal": None, "candidate_callback_ordinal": None,
        "turn": None, "context": None, "following_callbacks_verified": 0,
        "scope": "NO_SEMANTIC_DIVERGENCE",
    }
    b_pairs = [{"start": row.start, "end": row.end} for row in baseline.callbacks]
    c_pairs = [{"start": row.start, "end": row.end} for row in candidate.callbacks]
    b_metrics = game_metrics(b_pairs, baseline.summary, timed_out=False)
    c_metrics = game_metrics(c_pairs, candidate.summary, timed_out=False)
    attack_count = lambda rows: sum(
        any(optional_int(option.get("type")) == 13 for option in row.selected_options)
        for row in rows
    )
    b_prizes, c_prizes = prize_progression(baseline.battles, target.seat), prize_progression(candidate.battles, target.seat)
    b_kos, c_kos = ko_events(baseline.battles), ko_events(candidate.battles)
    b_poffin = poffin_after(baseline.callbacks, index) if valid_index else {"count": 0, "events": []}
    c_poffin = poffin_after(candidate.callbacks, index) if valid_index else {"count": 0, "events": []}
    fix8_rule, fix8_path = fix8_trace_from_end(c_callback.end) if c_callback else (None, "NO_DIVERGENCE_CALLBACK")
    version_trace = c_callback.end.get("version_trace") if c_callback else None
    row: dict[str, Any] = {
        "opponent": target.opponent, "seat": target.seat, "seed": target.seed,
        "source_seed_base": target.source_seed_base, "source_game": target.source_game,
        "suite_seed_base": run_seed_base, "suite_game": game,
        "outcome_stratum": target.outcome_stratum,
        "source_baseline_win": target.baseline_win, "source_candidate_win": target.candidate_win,
        "rerun_baseline_result": b_out["rerun_result"], "rerun_candidate_result": c_out["rerun_result"],
        "rerun_baseline_win": b_out["rerun_policy_win"], "rerun_candidate_win": c_out["rerun_policy_win"],
        "baseline_outcome_matches_source": b_out["matches_source"],
        "candidate_outcome_matches_source": c_out["matches_source"],
        "source_outcomes_reproduced": outcomes_match,
        "mechanical_comparison_eligible": eligible,
        "mechanical_exclusion_reasons": ";".join(exclusions),
        "baseline_source_steps": target.baseline_steps, "candidate_source_steps": target.candidate_steps,
        "baseline_rerun_steps": baseline.summary.get("steps"), "candidate_rerun_steps": candidate.summary.get("steps"),
        "baseline_steps_match_source": baseline.summary.get("steps") == target.baseline_steps,
        "candidate_steps_match_source": candidate.summary.get("steps") == target.candidate_steps,
        "semantic_divergence_found": divergence.get("found"),
        "first_divergence_callback_ordinal": index,
        "prior_observation_states_equal": divergence.get("prior_observation_states_equal"),
        "divergence_pre_observation_equal": divergence.get("divergence_pre_observation_equal"),
        "divergence_semantic_legal_equal": divergence.get("divergence_semantic_legal_equal"),
        "raw_order_only_before_divergence": divergence.get("raw_order_only_before_divergence"),
        "divergence_turn": optional_int(b_callback.observation.get("turn")) if b_callback else None,
        "divergence_context": optional_int(b_callback.observation.get("context")) if b_callback else None,
        "baseline_selected_action_indices": canonical_json(b_callback.end.get("selected_action") if b_callback else None),
        "candidate_selected_action_indices": canonical_json(c_callback.end.get("selected_action") if c_callback else None),
        "baseline_selected_options": canonical_json(selected_with_names(b_callback.selected_options, card_names) if b_callback else None),
        "candidate_selected_options": canonical_json(selected_with_names(c_callback.selected_options, card_names) if c_callback else None),
        "baseline_semantic_action": canonical_json(divergence.get("baseline_action")),
        "candidate_semantic_action": canonical_json(divergence.get("candidate_action")),
        "baseline_semantic_action_no_serial": canonical_json(divergence.get("baseline_action_no_serial")),
        "candidate_semantic_action_no_serial": canonical_json(divergence.get("candidate_action_no_serial")),
        "fix8_trace_path": fix8_path,
        "fix8_stage": fix8_rule.get("stage") if fix8_rule else None,
        "fix8_reason": fix8_rule.get("reason") if fix8_rule else None,
        "fix8_eligibility_hash": fix8_rule.get("eligibility_hash") if fix8_rule else None,
        "fix8_parent_action": canonical_json(fix8_rule.get("parent_action") if fix8_rule else None),
        "fix8_proposed_action": canonical_json(fix8_rule.get("proposed_action") if fix8_rule else None),
        "fix8_applied_action": canonical_json(fix8_rule.get("applied_action") if fix8_rule else None),
        "version_trace_raw_parent_action": canonical_json(version_trace.get("raw_parent_action") if isinstance(version_trace, Mapping) else None),
        "observable_rejoin_certified": rejoin["certified_observable_rejoin"],
        "rejoin_baseline_callback_ordinal": rejoin["baseline_callback_ordinal"],
        "rejoin_candidate_callback_ordinal": rejoin["candidate_callback_ordinal"],
        "rejoin_turn": rejoin["turn"], "rejoin_context": rejoin["context"],
        "rejoin_following_callbacks_verified": rejoin["following_callbacks_verified"],
        "rejoin_scope": rejoin["scope"],
        "baseline_summary_path": str(baseline.summary_path), "candidate_summary_path": str(candidate.summary_path),
        "baseline_sidecar_path": str(baseline.sidecar_path), "candidate_sidecar_path": str(candidate.sidecar_path),
        "baseline_battle_trace_path": str(baseline.battle_path), "candidate_battle_trace_path": str(candidate.battle_path),
        "baseline_sidecar_sha256": sha256_file(baseline.sidecar_path),
        "candidate_sidecar_sha256": sha256_file(candidate.sidecar_path),
        "baseline_battle_trace_sha256": sha256_file(baseline.battle_path),
        "candidate_battle_trace_sha256": sha256_file(candidate.battle_path),
    }
    flatten_state(row, BASELINE_VERSION, b_states)
    flatten_state(row, CANDIDATE_VERSION, c_states)
    flatten_metrics(row, BASELINE_VERSION, b_metrics, attack_count(baseline.callbacks), b_prizes, b_kos, b_poffin)
    flatten_metrics(row, CANDIDATE_VERSION, c_metrics, attack_count(candidate.callbacks), c_prizes, c_kos, c_poffin)
    details = {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "opponent": target.opponent, "seat": target.seat, "seed": target.seed,
            "source_seed_base": target.source_seed_base, "source_game": target.source_game,
            "suite_seed_base": run_seed_base, "suite_game": game,
            "outcome_stratum": target.outcome_stratum,
        },
        "source_outcomes": {
            "baseline_result": target.baseline_result, "candidate_result": target.candidate_result,
            "baseline_win": target.baseline_win, "candidate_win": target.candidate_win,
            "baseline_steps": target.baseline_steps, "candidate_steps": target.candidate_steps,
        },
        "rerun_outcomes": {BASELINE_VERSION: b_out, CANDIDATE_VERSION: c_out},
        "mechanical_comparison_eligible": eligible,
        "mechanical_exclusion_reasons": exclusions,
        "trace_references": {
            BASELINE_VERSION: {
                "summary": str(baseline.summary_path), "summary_sha256": sha256_file(baseline.summary_path),
                "sidecar": str(baseline.sidecar_path), "sidecar_sha256": row["baseline_sidecar_sha256"],
                "battle_trace": str(baseline.battle_path), "battle_trace_sha256": row["baseline_battle_trace_sha256"],
            },
            CANDIDATE_VERSION: {
                "summary": str(candidate.summary_path), "summary_sha256": sha256_file(candidate.summary_path),
                "sidecar": str(candidate.sidecar_path), "sidecar_sha256": row["candidate_sidecar_sha256"],
                "battle_trace": str(candidate.battle_path), "battle_trace_sha256": row["candidate_battle_trace_sha256"],
            },
        },
        "divergence": divergence,
        "divergence_selected_options_with_names": {
            BASELINE_VERSION: selected_with_names(b_callback.selected_options, card_names) if b_callback else None,
            CANDIDATE_VERSION: selected_with_names(c_callback.selected_options, card_names) if c_callback else None,
        },
        "fix8_version_trace": version_trace, "fix8_rule_trace": fix8_rule,
        "fix8_rule_trace_path": fix8_path,
        "state_points": {BASELINE_VERSION: b_states, CANDIDATE_VERSION: c_states},
        "observable_rejoin": rejoin,
        "game_metrics": {
            BASELINE_VERSION: {
                "checked_metrics": b_metrics, "selected_attack_count": attack_count(baseline.callbacks),
                "prize_progression": b_prizes, "ko_events": b_kos, "poffin_later_use": b_poffin,
            },
            CANDIDATE_VERSION: {
                "checked_metrics": c_metrics, "selected_attack_count": attack_count(candidate.callbacks),
                "prize_progression": c_prizes, "ko_events": c_kos, "poffin_later_use": c_poffin,
            },
        },
        "divergence_windows": {
            BASELINE_VERSION: callback_window(baseline.callbacks, index) if valid_index else [],
            CANDIDATE_VERSION: callback_window(candidate.callbacks, index) if valid_index else [],
        },
    }
    return row, details

def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return value

def field_dictionary(fields: Sequence[str]) -> str:
    lines = [
        "# Fix8 trajectory mechanical field dictionary", "",
        "This artifact contains raw mechanical evidence only.", "",
        "It does not rate an action, assign causality, aggregate performance, or recommend adoption.", "",
        "## Integrity and eligibility", "",
        "- `outcome_stratum` is one of candidate_gain, candidate_loss, same_win, or same_loss.",
        "- `source_*` comes from the immutable paired CSV; `rerun_*` comes from the bound metric suite.",
        "- `mechanical_comparison_eligible` requires reproduced source outcomes and an aligned first semantic split.",
        "- Rows without a semantic split remain present and carry an explicit exclusion reason.", "",
        "## First divergence", "",
        "- Raw option indices and semantic type/card_id/serial selections are both retained.",
        "- Card names are copied only when existing engine metadata resolves the card ID; no name is guessed.",
        "- The no-serial semantic action is provided separately.",
        "- Earlier observation equality and divergence pre-state/legal equality are explicit gates.", "",
        "## Fix8 trace", "",
        "- The preferred path is `version_trace.parent_trace.LAST_V4_POFFIN_ZERO_VETO_TRACE`.",
        "- Direct and recursive fallbacks are explicit; absent fields remain empty.",
        "- The complete candidate version_trace and selected rule trace are in pair_mechanical_details.jsonl.", "",
        "## State and whole-game evidence", "",
        "- State points are divergence_pre, next_policy_callback, same_turn_end, and next_own_turn_start.",
        "- Attack timing/gaps, Hand Power evidence, and continuity reuse alakazam_staged_metrics.game_metrics.",
        "- Prize progression, KO rows, later Poffin selection, and callback windows are raw chronological evidence.",
        "- Unavailable values are not imputed.", "",
        "## Observable rejoin", "",
        "- A rejoin requires equal turn/player/context, public board/counts, own-hand card-ID multiset, and semantic legal multiset.",
        f"- The following {REJOIN_FOLLOWING_CALLBACKS} callbacks must also match in observable state and semantic action.",
        "- It never certifies hidden deck order or RNG state.", "", "## CSV columns", "",
    ]
    lines.extend(f"- `{field}`" for field in fields)
    return "\n".join(lines) + "\n"

def build_outputs(
    *, execution_spec: Path, keys_path: Path, metric_root: Path,
    output_dir: Path, workspace_root: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise IntegrityError(f"output directory already exists: {output_dir}")
    spec = load_json(execution_spec)
    targets = parse_target_rows(keys_path)
    declared_report = validate_declared_files(spec, workspace_root)
    source_report = validate_source_binding(spec, targets, keys_path, workspace_root)
    declared_opponents = set((spec.get("opponents") or {}).keys())
    by_opponent: dict[str, list[TargetKey]] = {}
    for target in targets:
        by_opponent.setdefault(target.opponent, []).append(target)
    if set(by_opponent) != declared_opponents:
        raise IntegrityError("target opponent set differs from execution spec")
    suite_by_opponent = resolve_suite_layout(metric_root, by_opponent)
    groups_by_suite: dict[Path, dict[str, Sequence[TargetKey]]] = {}
    for opponent, suite in suite_by_opponent.items():
        groups_by_suite.setdefault(suite, {})[opponent] = by_opponent[opponent]
    suite_reports = []
    locations: dict[tuple[str, int, int], tuple[int, int]] = {}
    for suite in sorted(groups_by_suite, key=str):
        report, mapping = validate_suite(
            suite, targets_by_opponent=groups_by_suite[suite],
            spec=spec, root=workspace_root,
        )
        suite_reports.append(report)
        locations.update(mapping)
    if len(locations) != len(targets):
        raise IntegrityError("target-to-suite location mapping is incomplete")
    declared_discordant = str((spec.get("output") or {}).get("discordant_keys_sha256") or "").lower()
    total_blocks = sum(row["ledger_rows"] for row in suite_reports)
    if sha256_file(keys_path) == declared_discordant:
        expected_blocks = as_int((spec.get("output") or {}).get("expected_blocks"))
        if total_blocks != expected_blocks:
            raise IntegrityError(f"declared discordant suite blocks {total_blocks} != {expected_blocks}")
    engine = resolve_input(str((spec.get("runtime") or {}).get("engine")), workspace_root)
    card_names = load_card_names(engine)
    rows, details = [], []
    for target in targets:
        row, detail = analyze_pair(
            target, suite_by_opponent[target.opponent],
            locations[target.key], card_names,
        )
        rows.append(row)
        details.append(detail)
    fields = list(rows[0])
    if any(list(row) != fields for row in rows):
        raise IntegrityError("mechanical rows have inconsistent field order")
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "pair_mechanical_rows.csv"
    detail_path = output_dir / "pair_mechanical_details.jsonl"
    dictionary_path = output_dir / "field_dictionary.md"
    integrity_path = output_dir / "integrity_report.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: csv_value(row.get(field)) for field in fields} for row in rows)
    with detail_path.open("w", encoding="utf-8", newline="\n") as handle:
        for detail in details:
            handle.write(json.dumps(detail, ensure_ascii=False, sort_keys=True) + "\n")
    dictionary_path.write_text(field_dictionary(fields), encoding="utf-8")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "STRUCTURALLY_VALID",
        "interpretation": "RAW_MECHANICAL_EVIDENCE_ONLY",
        "execution_spec": {
            "path": str(execution_spec), "sha256": sha256_file(execution_spec),
            "declared_schema_version": spec.get("schema_version"),
        },
        "declared_inputs": declared_report, "source": source_report,
        "metric_root": str(metric_root), "suite_reports": suite_reports,
        "card_metadata": {
            "engine_dir": str(engine), "resolved_card_name_count": len(card_names),
            "unresolved_names_are_left_null": True,
        },
        "counts": {
            "target_rows": len(targets), "unique_target_keys": len({row.key for row in targets}),
            "suite_blocks": total_blocks, "pair_mechanical_rows": len(rows),
            "detail_rows": len(details),
            "source_outcome_mismatches": sum(not bool(row["source_outcomes_reproduced"]) for row in rows),
            "mechanical_comparison_eligible_rows": sum(bool(row["mechanical_comparison_eligible"]) for row in rows),
            "semantic_divergence_found_rows": sum(bool(row["semantic_divergence_found"]) for row in rows),
        },
        "outputs": {
            "pair_mechanical_rows": str(csv_path), "pair_mechanical_rows_sha256": sha256_file(csv_path),
            "pair_mechanical_details": str(detail_path), "pair_mechanical_details_sha256": sha256_file(detail_path),
            "field_dictionary": str(dictionary_path), "field_dictionary_sha256": sha256_file(dictionary_path),
        },
        "notes": [
            "Outcome mismatches are row-level exclusions, not causal labels.",
            "Rows with no semantic action divergence are retained.",
            "Observable rejoin never certifies hidden deck order or RNG state.",
            "No aggregate performance or adoption judgment is emitted.",
        ],
    }
    integrity_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "rows": len(rows), "details": len(details),
        "outcome_mismatches": report["counts"]["source_outcome_mismatches"],
        "output_dir": str(output_dir), "integrity_report": str(integrity_path),
    }

def write_failure_report(output_dir: Path, execution_spec: Path, keys_path: Path, error: Exception) -> None:
    if output_dir.exists():
        return
    output_dir.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema_version": SCHEMA_VERSION, "status": "INTEGRITY_ERROR",
        "error": str(error),
        "execution_spec": str(execution_spec),
        "execution_spec_sha256": sha256_file(execution_spec) if execution_spec.is_file() else None,
        "keys": str(keys_path), "keys_sha256": sha256_file(keys_path) if keys_path.is_file() else None,
        "pair_outputs_emitted": False,
    }
    (output_dir / "integrity_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-spec", type=Path, required=True)
    parser.add_argument("--keys", "--discordant-keys", dest="keys", type=Path, required=True)
    parser.add_argument("--metric-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)

def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    spec, keys, metric, output, root = (
        args.execution_spec.resolve(), args.keys.resolve(), args.metric_root.resolve(),
        args.output_dir.resolve(), args.workspace_root.resolve(),
    )
    try:
        result = build_outputs(
            execution_spec=spec, keys_path=keys, metric_root=metric,
            output_dir=output, workspace_root=root,
        )
    except IntegrityError as exc:
        try:
            write_failure_report(output, spec, keys, exc)
        except OSError:
            pass
        print(json.dumps({"status": "INTEGRITY_ERROR", "error": str(exc)}))
        return 2
    print(json.dumps({"status": "OK", **result}, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
