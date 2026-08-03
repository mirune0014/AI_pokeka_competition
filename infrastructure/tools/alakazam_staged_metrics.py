"""Deterministic, policy-read-only instrumentation for staged Alakazam agents.

This module is evaluation infrastructure.  It never writes into a policy
package and the wrapped policy never reads the JSONL sidecar.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import types
from typing import Any, Callable, Iterable, Mapping, Sequence


SCHEMA_VERSION = "alakazam-staged-metrics-v1"
TRACE_NAMES = (
    "LAST_STAGED_POLICY_TRACE",
    "LAST_V2_CONTINUITY_TRACE",
    "LAST_V1_PACKAGE_TRACE",
    "LAST_V0_PORT_TRACE",
)
FALLBACK_CLASSES = frozenset(
    {"ADMISSIBILITY_REJECT", "PLACEHOLDER_PARENT_FALLBACK", "PARITY_PARENT_FALLBACK"}
)
FIRST_LEGAL_CLASS = "EMERGENCY_LOWEST_LEGAL"
ADDED_ONLY_IDS = frozenset({1184, 1197, 1266})
INCREASED_IDS = frozenset({743, 1081, 1182})
ADDED_SLOT_IDS = frozenset(ADDED_ONLY_IDS | INCREASED_IDS)
ALAKAZAM_LINE_IDS = frozenset({741, 742, 743})
ALAKAZAM_ID = 743
HAND_POWER_ATTACK_ID = 1072
OPTION_PLAY = 7
OPTION_EVOLVE = 9
OPTION_ATTACK = 13
LOG_MOVE_CARD = 6
LOG_PLAY = 10
LOG_EVOLVE = 12
LOG_ATTACK = 15
LOG_HP_CHANGE = 16
AREA_HAND = 2
AREA_DISCARD = 3
AREA_ACTIVE = 4
AREA_BENCH = 5
SERIAL_KEYS = (
    "serial",
    "serialActive",
    "serialBench",
    "serialBefore",
    "serialAfter",
    "serialTarget",
)
MODULE_PURGE_NAMES = frozenset({"_cumulative_parent"})
MODULE_PURGE_PREFIXES = ("planner_",)


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return repr(value)
        return value
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(item) for item in value]
    if hasattr(value, "__dict__"):
        return json_safe(vars(value))
    return repr(value)


def stable_json(value: Any) -> str:
    return json.dumps(
        json_safe(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def card_pair(card: Any) -> list[int | None] | None:
    if not isinstance(card, Mapping):
        return None
    return [as_int(card.get("id", card.get("cardId"))), as_int(card.get("serial"))]


def card_pairs(cards: Any) -> list[list[int | None] | None]:
    if not isinstance(cards, list):
        return []
    return [card_pair(card) for card in cards]


def first_card(cards: Any) -> Mapping[str, Any] | None:
    if isinstance(cards, list) and cards and isinstance(cards[0], Mapping):
        return cards[0]
    return None


def attached_energy(card: Mapping[str, Any] | None) -> list[list[int | None] | None]:
    if not card:
        return []
    values = card.get("energyCards")
    if isinstance(values, list):
        return card_pairs(values)
    energies = card.get("energies")
    if isinstance(energies, list):
        return [[as_int(value), None] for value in energies]
    return []


def player_at(obs: Mapping[str, Any], seat: int) -> Mapping[str, Any]:
    players = ((obs.get("current") or {}).get("players") or [])
    if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
        return players[seat]
    return {}


def raw_log_rows(obs: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    logs = obs.get("logs")
    if not isinstance(logs, list):
        return rows
    for value in logs:
        if not isinstance(value, Mapping):
            continue
        rows.append({str(key): json_safe(item) for key, item in value.items()})
    return rows


def log_serial_rows(logs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "type",
        "playerIndex",
        "cardId",
        "cardIdActive",
        "cardIdBench",
        "cardIdBefore",
        "cardIdAfter",
        "cardIdTarget",
        "attackId",
        *SERIAL_KEYS,
        "fromArea",
        "toArea",
        "value",
        "putDamageCounter",
    )
    return [
        {field: json_safe(log[field]) for field in fields if field in log}
        for log in logs
        if any(field in log for field in SERIAL_KEYS)
    ]


def option_source_card(
    obs: Mapping[str, Any], option: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    current = obs.get("current") or {}
    select = obs.get("select") or {}
    seat = as_int(current.get("yourIndex"))
    owner = as_int(option.get("playerIndex"))
    if owner not in (0, 1):
        owner = seat
    index = as_int(option.get("index"))
    area = as_int(option.get("area"))
    option_type = as_int(option.get("type"))
    if index is None or index < 0:
        return None
    if option_type in (OPTION_PLAY, 8, OPTION_EVOLVE):
        area = AREA_HAND
        owner = seat
    player = player_at(obs, owner if owner is not None else -1)
    sources: Any = None
    if area == AREA_HAND:
        sources = player.get("hand")
    elif area == AREA_DISCARD:
        sources = player.get("discard")
    elif area == AREA_ACTIVE:
        sources = player.get("active")
    elif area == AREA_BENCH:
        sources = player.get("bench")
    elif area == 6:
        sources = player.get("prize")
    elif area == 7:
        sources = current.get("stadium")
    elif area == 12:
        sources = current.get("looking")
    elif area == 1:
        sources = select.get("deck")
    if isinstance(sources, list) and 0 <= index < len(sources):
        value = sources[index]
        return value if isinstance(value, Mapping) else None
    return None


def option_identity(
    obs: Mapping[str, Any], option: Mapping[str, Any], index: int
) -> dict[str, Any]:
    source = option_source_card(obs, option)
    card_id = as_int(option.get("cardId"))
    serial = as_int(option.get("serial"))
    if source is not None:
        card_id = as_int(source.get("id", source.get("cardId"))) or card_id
        serial = as_int(source.get("serial")) or serial
    return {
        "option_index": index,
        "type": as_int(option.get("type")),
        "area": as_int(option.get("area")),
        "index": as_int(option.get("index")),
        "player_index": as_int(option.get("playerIndex")),
        "card_id": card_id,
        "serial": serial,
        "attack_id": as_int(option.get("attackId")),
        "in_play_area": as_int(option.get("inPlayArea")),
        "in_play_index": as_int(option.get("inPlayIndex")),
        "raw": json_safe(option),
    }


def structural_action_status(obs: Mapping[str, Any], action: Any) -> dict[str, Any]:
    select = obs.get("select") or {}
    options = select.get("option") or []
    minimum = as_int(select.get("minCount"))
    maximum = as_int(select.get("maxCount"))
    reasons: list[str] = []
    if not isinstance(action, list):
        reasons.append("ACTION_NOT_LIST")
        values: list[Any] = []
    else:
        values = action
    if isinstance(action, list):
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            reasons.append("NON_INTEGER_INDEX")
        integer_values = [
            value
            for value in values
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        if len(integer_values) != len(set(integer_values)):
            reasons.append("DUPLICATE_INDEX")
        if any(value < 0 or value >= len(options) for value in integer_values):
            reasons.append("INDEX_OUT_OF_RANGE")
        if minimum is not None and len(values) < minimum:
            reasons.append("BELOW_MIN_COUNT")
        if maximum is not None and len(values) > maximum:
            reasons.append("ABOVE_MAX_COUNT")
    return {"valid": not reasons, "reasons": reasons}


def observation_snapshot(obs: Mapping[str, Any]) -> dict[str, Any]:
    current = obs.get("current") or {}
    select = obs.get("select") or {}
    seat = as_int(current.get("yourIndex"))
    mine = player_at(obs, seat if seat is not None else -1)
    opponent = player_at(obs, 1 - seat if seat in (0, 1) else -1)
    own_active = first_card(mine.get("active"))
    opponent_active = first_card(opponent.get("active"))
    options = select.get("option") if isinstance(select.get("option"), list) else []
    logs = raw_log_rows(obs)
    return {
        "turn": as_int(current.get("turn")),
        "turn_action_count": as_int(current.get("turnActionCount")),
        "your_index": seat,
        "first_player": as_int(current.get("firstPlayer")),
        "result": as_int(current.get("result")),
        "context": as_int(select.get("context")),
        "select_type": as_int(select.get("type")),
        "min_count": as_int(select.get("minCount")),
        "max_count": as_int(select.get("maxCount")),
        "option_count": len(options),
        "options": [
            option_identity(obs, option, index)
            for index, option in enumerate(options)
            if isinstance(option, Mapping)
        ],
        "own_hand": card_pairs(mine.get("hand")),
        "own_active": card_pair(own_active),
        "own_active_hp": as_int(own_active.get("hp")) if own_active else None,
        "own_active_energy": attached_energy(own_active),
        "own_bench": card_pairs(mine.get("bench")),
        "own_discard": card_pairs(mine.get("discard")),
        "opponent_active": card_pair(opponent_active),
        "opponent_active_hp": (
            as_int(opponent_active.get("hp")) if opponent_active else None
        ),
        "opponent_active_energy": attached_energy(opponent_active),
        "logs_raw": logs,
        "log_serial_fields": log_serial_rows(logs),
    }


def _module_path(module: types.ModuleType) -> Path | None:
    raw = getattr(module, "__file__", None)
    try:
        return Path(raw).resolve() if raw else None
    except OSError:
        return None


def policy_modules(root: types.ModuleType, target_dir: Path) -> list[types.ModuleType]:
    """Return target-local modules in a stable order without importing anything."""
    target = target_dir.resolve()
    seen: set[int] = set()
    queue: list[types.ModuleType] = [root]
    result: list[types.ModuleType] = []
    while queue:
        module = queue.pop(0)
        if id(module) in seen:
            continue
        seen.add(id(module))
        result.append(module)
        children: list[tuple[str, types.ModuleType]] = []
        for name, value in vars(module).items():
            if not isinstance(value, types.ModuleType):
                continue
            path = _module_path(value)
            if path is None:
                continue
            try:
                local = path.is_relative_to(target)
            except ValueError:
                local = False
            if local or name in {"_module", "_source_module", "_integrated", "core"}:
                children.append((name, value))
        queue.extend(value for _, value in sorted(children, key=lambda item: item[0]))
    return result


def integrated_log_state(
    modules: Sequence[types.ModuleType],
) -> tuple[types.ModuleType | None, list[Any]]:
    candidates: list[tuple[int, str, types.ModuleType, list[Any]]] = []
    for module in modules:
        value = getattr(module, "INTEGRATED_TRACE_LOG", None)
        if isinstance(value, list):
            candidates.append(
                (len(value), getattr(module, "__name__", ""), module, copy.deepcopy(value))
            )
    if not candidates:
        return None, []
    _, _, owner, rows = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
    return owner, rows


def integrated_suffix(
    before_owner: types.ModuleType | None,
    before_rows: Sequence[Any],
    modules: Sequence[types.ModuleType],
) -> tuple[str, list[Any], bool]:
    owner, after = integrated_log_state(modules)
    owner_name = getattr(owner, "__name__", "") if owner else ""
    prefix_ok = (
        owner is before_owner
        and len(after) >= len(before_rows)
        and list(after[: len(before_rows)]) == list(before_rows)
    )
    if prefix_ok:
        return owner_name, copy.deepcopy(after[len(before_rows) :]), False
    return owner_name, copy.deepcopy(after), bool(before_owner or before_rows or after)


def version_trace(
    modules: Sequence[types.ModuleType],
) -> tuple[str, dict[str, Any] | None]:
    for name in TRACE_NAMES:
        for module in modules:
            value = getattr(module, name, None)
            if isinstance(value, Mapping):
                return name, copy.deepcopy(dict(value))
    return "", None


def _trace_list(trace: Mapping[str, Any] | None, key: str) -> list[Any] | None:
    if not isinstance(trace, Mapping) or key not in trace:
        return None
    value = trace.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def normalized_trace_fields(
    suffix: Sequence[Any], trace_name: str, trace: Mapping[str, Any] | None
) -> dict[str, Any]:
    rows = [row for row in suffix if isinstance(row, Mapping)]
    classifications = [str(row.get("classification")) for row in rows]
    reason_tags = _trace_list(trace, "reason_tags")
    added_hits = _trace_list(trace, "added_rule_hits")
    removed_hits = _trace_list(trace, "removed_rule_hits")
    continuity_hits = _trace_list(trace, "continuity_rule_hits")
    explicit_generic = None
    if isinstance(trace, Mapping):
        for key in ("generic_fallback_selected", "selected_generic_fallback"):
            if key in trace:
                explicit_generic = bool(trace.get(key))
                break
    if explicit_generic is None and reason_tags is not None:
        generic_selected_tags = {str(tag) for tag in reason_tags}
        explicit_generic = "V0_GENERIC_FORCED_DISCARD" in generic_selected_tags or any(
            tag.startswith("GENERIC_")
            and ("SELECTED" in tag or "FALLBACK" in tag)
            for tag in generic_selected_tags
        )
    handler_hits: list[Any] = []
    explicit_handler = _trace_list(trace, "generic_handler_selected")
    if explicit_handler:
        handler_hits.extend(explicit_handler)
    for tag in reason_tags or []:
        if str(tag) in {"V0_GENERIC_HOLD", "V0_GENERIC_FORCED_DISCARD"}:
            handler_hits.append(tag)
    return {
        "integrated_classifications": classifications,
        "version_trace_name": trace_name or None,
        "version_trace": json_safe(trace),
        "reason_tags": json_safe(reason_tags),
        "added_rule_hits": json_safe(added_hits),
        "removed_rule_hits": json_safe(removed_hits),
        "removed_rule_hit_status": "KNOWN" if removed_hits is not None else "UNKNOWN",
        "continuity_rule_hits": json_safe(continuity_hits),
        "generic_handler_hits": json_safe(handler_hits),
        "generic_fallback_selected": explicit_generic,
        "generic_fallback_status": (
            "KNOWN" if explicit_generic is not None else "UNKNOWN"
        ),
        "parent_fallback_selected": any(
            value in FALLBACK_CLASSES for value in classifications
        ),
        "first_legal_fallback_selected": FIRST_LEGAL_CLASS in classifications,
        "selected_owner": (
            rows[-1].get("classification") if rows else None
        ),
    }


def selected_options(
    obs: Mapping[str, Any], action: Any
) -> list[dict[str, Any]]:
    options = ((obs.get("select") or {}).get("option") or [])
    if not isinstance(action, list):
        return []
    rows: list[dict[str, Any]] = []
    for index in action:
        if (
            isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(options)
            and isinstance(options[index], Mapping)
        ):
            rows.append(option_identity(obs, options[index], index))
    return rows


def append_jsonl_flush(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        json_safe(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _game_index(module_name: str) -> int:
    match = re.search(r"_(\d+)$", module_name)
    if not match:
        raise RuntimeError(f"metric adapter module name lacks game index: {module_name}")
    return int(match.group(1))


def purge_policy_modules() -> None:
    for name in tuple(sys.modules):
        if name in MODULE_PURGE_NAMES or name.startswith(MODULE_PURGE_PREFIXES):
            sys.modules.pop(name, None)


def load_target_module(
    target_dir: Path, version: str, game_index: int
) -> types.ModuleType:
    """Load one game-local target with strict path/cwd restoration."""
    target = target_dir.resolve()
    source = target / "main.py"
    if not source.is_file():
        raise FileNotFoundError(source)
    purge_policy_modules()
    previous_path = list(sys.path)
    previous_cwd = Path.cwd()
    try:
        target_text = str(target)
        sys.path[:] = [target_text] + [
            entry for entry in sys.path if entry != target_text
        ]
        os.chdir(target)
        name = f"_alakazam_metric_target_{version}_{game_index}_{time.time_ns()}"
        spec = importlib.util.spec_from_file_location(name, source)
        if spec is None or spec.loader is None:
            raise ImportError(f"could not load {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path


def build_metric_entrypoint(
    *,
    adapter_file: str,
    module_name: str,
    version: str,
    target_dir: str,
) -> tuple[Callable[[dict[str, Any]], list[int]], types.ModuleType]:
    game_index = _game_index(module_name)
    target = Path(target_dir).resolve()
    module = load_target_module(target, version, game_index)
    policy = getattr(module, "agent", None)
    if not callable(policy):
        raise AttributeError(f"{target / 'main.py'} does not define agent")
    sidecar_dir_raw = os.environ.get("ALAKAZAM_METRIC_SIDECAR_DIR")
    if not sidecar_dir_raw:
        raise RuntimeError("ALAKAZAM_METRIC_SIDECAR_DIR is required")
    sidecar = Path(sidecar_dir_raw).resolve() / f"game_{game_index:04d}.jsonl"
    run_id = os.environ.get("ALAKAZAM_METRIC_RUN_ID", "")
    opponent = os.environ.get("ALAKAZAM_METRIC_OPPONENT", "")
    policy_seat = as_int(os.environ.get("ALAKAZAM_METRIC_POLICY_SEAT"))
    seed_base = as_int(os.environ.get("ALAKAZAM_METRIC_SEED_BASE"))
    seed = seed_base + game_index if seed_base is not None else None
    callback_ordinal = 0

    def wrapped(obs: dict[str, Any]) -> list[int]:
        nonlocal callback_ordinal
        ordinal = callback_ordinal
        callback_ordinal += 1
        snapshot = observation_snapshot(obs)
        modules_before = policy_modules(module, target)
        before_owner, before_rows = integrated_log_state(modules_before)
        common = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "version": version,
            "opponent": opponent,
            "policy_seat": policy_seat,
            "game": game_index,
            "seed_base": seed_base,
            "seed": seed,
            "callback_ordinal": ordinal,
        }
        append_jsonl_flush(
            sidecar,
            {**common, "event": "CALL_START", "observation": snapshot},
        )
        action: Any = None
        exception: dict[str, Any] | None = None
        caught_exception: BaseException | None = None
        previous_path = list(sys.path)
        previous_cwd = Path.cwd()
        decision_ns = 0
        try:
            target_text = str(target)
            sys.path[:] = [target_text] + [
                entry for entry in sys.path if entry != target_text
            ]
            os.chdir(target)
            started = time.perf_counter_ns()
            try:
                action = policy(obs)
            except BaseException as exc:
                caught_exception = exc
                exception = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            finally:
                decision_ns = time.perf_counter_ns() - started
        finally:
            os.chdir(previous_cwd)
            sys.path[:] = previous_path
        modules_after = policy_modules(module, target)
        owner, suffix, reset = integrated_suffix(
            before_owner, before_rows, modules_after
        )
        trace_name, trace = version_trace(modules_after)
        status = structural_action_status(obs, action)
        selection = selected_options(obs, action)
        end = {
            **common,
            "event": "CALL_END",
            "selected_action": json_safe(action),
            "selected_options": selection,
            "selected_card_ids": [row.get("card_id") for row in selection],
            "selected_serials": [row.get("serial") for row in selection],
            "decision_ns": decision_ns,
            "structurally_valid": status["valid"] if exception is None else False,
            "structural_invalid_reasons": status["reasons"],
            "exception": exception,
            "integrated_trace_owner": owner or None,
            "integrated_trace_prefix_reset": reset,
            "integrated_trace_suffix": json_safe(suffix),
            **normalized_trace_fields(suffix, trace_name, trace),
        }
        append_jsonl_flush(sidecar, end)
        if caught_exception is not None:
            raise caught_exception
        return action

    setattr(wrapped, "_metric_target_module", module)
    setattr(wrapped, "_metric_target_dir", target)
    setattr(wrapped, "_metric_sidecar", sidecar)
    return wrapped, module


def nearest_rank_p95(values: Sequence[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(int(value) for value in values)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL {path}:{line_number}")
        rows.append(value)
    return rows


def pair_callback_events(
    rows: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    starts: dict[tuple[Any, ...], dict[str, Any]] = {}
    complete: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    keys = (
        "run_id",
        "version",
        "opponent",
        "policy_seat",
        "game",
        "seed",
        "callback_ordinal",
    )
    for raw in rows:
        row = dict(raw)
        key = tuple(row.get(name) for name in keys)
        event = row.get("event")
        if event == "CALL_START":
            if key in starts:
                diagnostics.append({"kind": "DUPLICATE_CALL_START", "key": key})
            starts[key] = row
        elif event == "CALL_END":
            start = starts.pop(key, None)
            if start is None:
                diagnostics.append({"kind": "ORPHAN_CALL_END", "key": key})
            else:
                complete.append({"key": key, "start": start, "end": row})
        else:
            diagnostics.append({"kind": "UNKNOWN_EVENT", "key": key})
    for key in sorted(starts, key=repr):
        diagnostics.append({"kind": "CALL_START_WITHOUT_END", "key": key})
    complete.sort(key=lambda row: tuple(repr(value) for value in row["key"]))
    return complete, diagnostics


def selected_attack(callback: Mapping[str, Any]) -> tuple[bool, int | None]:
    selected = callback["end"].get("selected_options") or []
    for option in selected:
        if isinstance(option, Mapping) and as_int(option.get("type")) == OPTION_ATTACK:
            return True, as_int(option.get("attack_id"))
    return False, None


def visible_pairs(snapshot: Mapping[str, Any]) -> list[tuple[int, int | None]]:
    rows: list[tuple[int, int | None]] = []
    for key in ("own_hand", "own_bench", "own_discard"):
        for pair in snapshot.get(key) or []:
            if isinstance(pair, list) and pair and as_int(pair[0]) is not None:
                rows.append((as_int(pair[0]), as_int(pair[1])))
    active = snapshot.get("own_active")
    if isinstance(active, list) and active and as_int(active[0]) is not None:
        rows.append((as_int(active[0]), as_int(active[1])))
    return rows


def game_metrics(
    callbacks: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any] | None,
    *,
    timed_out: bool,
) -> dict[str, Any]:
    """Compute diagnostic game metrics without inventing UNKNOWN values."""
    ordered = sorted(
        callbacks,
        key=lambda row: as_int(row["start"].get("callback_ordinal")) or 0,
    )
    main_by_turn: dict[int, list[Mapping[str, Any]]] = {}
    attacks: list[tuple[int, Mapping[str, Any], int | None]] = []
    decision_ns: list[int] = []
    exposed: dict[int, set[int]] = {card_id: set() for card_id in ADDED_SLOT_IDS}
    played: dict[int, set[int]] = {card_id: set() for card_id in ADDED_SLOT_IDS}
    invalid_count = 0
    exception_count = 0
    parent_fallback_count = 0
    first_legal_count = 0
    generic_fallback_known = 0
    generic_fallback_true = 0
    generic_handler_count = 0
    removed_known = 0
    removed_hits: list[Any] = []
    removed_hit_callbacks = 0
    all_logs: list[Mapping[str, Any]] = []
    for callback in ordered:
        start = callback["start"]
        end = callback["end"]
        snapshot = start.get("observation") or {}
        turn = as_int(snapshot.get("turn"))
        if as_int(snapshot.get("context")) == 0 and turn is not None:
            main_by_turn.setdefault(turn, []).append(callback)
        is_attack, attack_id = selected_attack(callback)
        if is_attack and turn is not None:
            attacks.append((turn, callback, attack_id))
        value = as_int(end.get("decision_ns"))
        if value is not None:
            decision_ns.append(value)
        invalid_count += not bool(end.get("structurally_valid"))
        exception_count += bool(end.get("exception"))
        parent_fallback_count += bool(end.get("parent_fallback_selected"))
        first_legal_count += bool(end.get("first_legal_fallback_selected"))
        if end.get("generic_fallback_status") == "KNOWN":
            generic_fallback_known += 1
            generic_fallback_true += bool(end.get("generic_fallback_selected"))
        generic_handler_count += bool(end.get("generic_handler_hits"))
        if end.get("removed_rule_hit_status") == "KNOWN":
            removed_known += 1
            removed_hits.extend(end.get("removed_rule_hits") or [])
            removed_hit_callbacks += bool(end.get("removed_rule_hits"))
        for card_id, serial in visible_pairs(snapshot):
            if card_id in ADDED_SLOT_IDS and serial is not None:
                exposed[card_id].add(serial)
        logs = snapshot.get("logs_raw") or []
        all_logs.extend(log for log in logs if isinstance(log, Mapping))
        for log in logs:
            if not isinstance(log, Mapping):
                continue
            if (
                as_int(log.get("playerIndex")) == as_int(start.get("policy_seat"))
                and as_int(log.get("type")) in (LOG_PLAY, LOG_EVOLVE)
            ):
                cid, serial = as_int(log.get("cardId")), as_int(log.get("serial"))
                if cid in ADDED_SLOT_IDS and serial is not None:
                    played[cid].add(serial)

    attack_turns = sorted({turn for turn, _, _ in attacks})
    main_turns = sorted(main_by_turn)
    first_attack_turn = attack_turns[0] if attack_turns else None
    after_first = (
        [turn for turn in main_turns if first_attack_turn is not None and turn >= first_attack_turn]
        if first_attack_turn is not None
        else []
    )
    missing_tail = [turn for turn in after_first if turn not in attack_turns]
    between = (
        [
            turn
            for turn in main_turns
            if first_attack_turn is not None
            and attack_turns
            and first_attack_turn <= turn <= attack_turns[-1]
            and turn not in attack_turns
        ]
        if attacks
        else []
    )
    longest = 0
    current_run = 0
    previous: int | None = None
    for turn in attack_turns:
        if previous is not None and turn == previous + 2:
            current_run += 1
        else:
            current_run = 1
        longest = max(longest, current_run)
        previous = turn
    attack_hands: list[int] = []
    hand_power_rows: list[dict[str, Any]] = []
    ko_miss_known = 0
    ko_miss_count = 0
    for turn, callback, attack_id in attacks:
        snapshot = callback["start"].get("observation") or {}
        hand_count = len(snapshot.get("own_hand") or [])
        attack_hands.append(hand_count)
        if attack_id == HAND_POWER_ATTACK_ID:
            opponent_hp = as_int(snapshot.get("opponent_active_hp"))
            counters = 2 * hand_count
            required = math.ceil(opponent_hp / 10) if opponent_hp is not None else None
            trace = callback["end"].get("version_trace") or {}
            guard = trace.get("ko_guard_status") if isinstance(trace, Mapping) else None
            certified = guard in {"CERTIFIED_CLEAR", "CLEAR"} or trace.get(
                "counter_prevention_certified_clear"
            ) is True if isinstance(trace, Mapping) else False
            miss: bool | None = None
            if certified and required is not None:
                ko_miss_known += 1
                miss = counters < required
                ko_miss_count += bool(miss)
            hand_power_rows.append(
                {
                    "turn": turn,
                    "hand_cards": hand_count,
                    "damage_counters": counters,
                    "damage": 20 * hand_count,
                    "required_ko_counters": required,
                    "ko_guard_status": guard,
                    "certified_clear_ko_miss": miss,
                }
            )
    top_serials_before_first: set[int] = set()
    first_hand_power_callback = next(
        (callback for _, callback, attack_id in attacks if attack_id == HAND_POWER_ATTACK_ID),
        None,
    )
    if first_hand_power_callback is not None:
        snapshot = first_hand_power_callback["start"].get("observation") or {}
        board_pairs = [snapshot.get("own_active"), *(snapshot.get("own_bench") or [])]
        for pair in board_pairs:
            if not isinstance(pair, list) or not pair:
                continue
            cid, serial = as_int(pair[0]), as_int(pair[1])
            if cid in ALAKAZAM_LINE_IDS and serial is not None:
                top_serials_before_first.add(serial)
    second_line: bool | None = (
        len(top_serials_before_first) >= 2
        if first_hand_power_callback is not None
        else None
    )

    hand_power_attackers: list[dict[str, Any]] = []
    for callback_index, callback in enumerate(ordered):
        attacked, attack_id = selected_attack(callback)
        if not attacked or attack_id != HAND_POWER_ATTACK_ID:
            continue
        snapshot = callback["start"].get("observation") or {}
        active = snapshot.get("own_active")
        if (
            isinstance(active, list)
            and len(active) >= 2
            and as_int(active[0]) == ALAKAZAM_ID
            and as_int(active[1]) is not None
        ):
            hand_power_attackers.append(
                {
                    "callback_index": callback_index,
                    "callback_ordinal": callback["start"].get("callback_ordinal"),
                    "turn": as_int(snapshot.get("turn")),
                    "serial": as_int(active[1]),
                }
            )

    ko_events: list[dict[str, Any]] = []
    consumed_death_serials: set[int] = set()
    for callback_index, callback in enumerate(ordered):
        snapshot = callback["start"].get("observation") or {}
        seat = as_int(callback["start"].get("policy_seat"))
        death_turn = as_int(snapshot.get("turn"))
        for log in snapshot.get("logs_raw") or []:
            if not (
                isinstance(log, Mapping)
                and as_int(log.get("type")) == LOG_MOVE_CARD
                and as_int(log.get("playerIndex")) == seat
                and as_int(log.get("fromArea")) == AREA_ACTIVE
                and as_int(log.get("toArea")) == AREA_DISCARD
                and as_int(log.get("cardId")) == ALAKAZAM_ID
            ):
                continue
            serial = as_int(log.get("serial"))
            if serial is None or serial in consumed_death_serials:
                continue
            matching_attacks = [
                row
                for row in hand_power_attackers
                if row["serial"] == serial and row["callback_index"] <= callback_index
            ]
            if not matching_attacks:
                continue
            attack_event = matching_attacks[-1]
            consumed_death_serials.add(serial)
            first_main_turn = None
            for later in ordered[callback_index:]:
                later_snapshot = later["start"].get("observation") or {}
                later_turn = as_int(later_snapshot.get("turn"))
                if as_int(later_snapshot.get("context")) != 0:
                    continue
                if death_turn is not None and later_turn is not None and later_turn < death_turn:
                    continue
                first_main_turn = later_turn
                break
            if first_main_turn is None:
                status = "UNKNOWN_TERMINAL_OR_UNOBSERVED"
                next_attack = None
            else:
                status = "KNOWN"
                next_attack = any(
                    as_int((later["start"].get("observation") or {}).get("context")) == 0
                    and as_int((later["start"].get("observation") or {}).get("turn"))
                    == first_main_turn
                    and selected_attack(later)[0]
                    for later in ordered[callback_index:]
                )
            ko_events.append(
                {
                    "death_turn": death_turn,
                    "serial": serial,
                    "hand_power_turn": attack_event["turn"],
                    "hand_power_callback_ordinal": attack_event["callback_ordinal"],
                    "next_policy_main_turn": first_main_turn,
                    "status": status,
                    "attacked_next_own_turn": next_attack,
                }
            )
    known_ko = [row for row in ko_events if row["status"] == "KNOWN"]
    exposed_rows = [
        {"card_id": cid, "serial": serial}
        for cid in sorted(exposed)
        for serial in sorted(exposed[cid])
    ]
    played_rows = [
        {"card_id": cid, "serial": serial}
        for cid in sorted(played)
        for serial in sorted(played[cid])
    ]
    new_only_exposed = {
        (row["card_id"], row["serial"])
        for row in exposed_rows
        if row["card_id"] in ADDED_ONLY_IDS
    }
    new_only_played = {
        (row["card_id"], row["serial"])
        for row in played_rows
        if row["card_id"] in ADDED_ONLY_IDS
    }
    started = bool(summary and summary.get("started"))
    complete = bool(
        summary
        and started
        and not summary.get("hit_max_steps")
        and as_int(summary.get("action_errors")) == 0
        and as_int(summary.get("result")) in (0, 1, 2)
        and not timed_out
    )
    return {
        "formal_rate_eligible": complete,
        "partial_diagnostic_only": not complete,
        "started": started,
        "result": summary.get("result") if summary else None,
        "steps": summary.get("steps") if summary else None,
        "hit_max_steps": summary.get("hit_max_steps") if summary else None,
        "timed_out": timed_out,
        "callback_count": len(ordered),
        "first_attack_turn": first_attack_turn,
        "attack_turn_count": len(attack_turns),
        "attack_gap_tail_count": len(missing_tail) if first_attack_turn is not None else None,
        "attack_gap_tail_denominator": len(after_first) if first_attack_turn is not None else None,
        "attack_gap_between_count": len(between) if len(attack_turns) >= 2 else None,
        "attack_gap_between_denominator": (
            len([turn for turn in main_turns if attack_turns[0] <= turn <= attack_turns[-1]])
            if len(attack_turns) >= 2
            else None
        ),
        "max_consecutive_attack_turns": longest if attack_turns else 0,
        "attack_hand_sizes": attack_hands,
        "attack_hand_mean": (
            sum(attack_hands) / len(attack_hands) if attack_hands else None
        ),
        "hand_power_attacks": hand_power_rows,
        "hand_power_counter_unit": "2_COUNTERS_PER_HAND_CARD",
        "hand_power_damage_unit": "20_DAMAGE_PER_HAND_CARD",
        "certified_clear_ko_miss_count": ko_miss_count if ko_miss_known else None,
        "certified_clear_ko_miss_denominator": ko_miss_known,
        "second_alakazam_line_before_first_attack": second_line,
        "second_alakazam_line_before_first_hand_power": second_line,
        "second_line_top_serials": sorted(top_serials_before_first),
        "post_ko_events": ko_events,
        "post_ko_continuity_count": (
            sum(bool(row["attacked_next_own_turn"]) for row in known_ko)
            if known_ko
            else None
        ),
        "post_ko_continuity_denominator": len(known_ko),
        "added_slot_exposed_serials": exposed_rows,
        "added_slot_played_serials": played_rows,
        "added_new_only_unused_serials": [
            {"card_id": cid, "serial": serial}
            for cid, serial in sorted(new_only_exposed - new_only_played)
        ],
        "increased_copy_attribution_status": "UNKNOWN_IDENTICAL_CARD_ID",
        "generic_handler_callback_count": generic_handler_count,
        "generic_fallback_selected_count": (
            generic_fallback_true if generic_fallback_known else None
        ),
        "generic_fallback_known_callbacks": generic_fallback_known,
        "parent_fallback_selected_count": parent_fallback_count,
        "first_legal_fallback_selected_count": first_legal_count,
        "removed_rule_hits": removed_hits if removed_known else None,
        "removed_rule_hit_count": len(removed_hits) if removed_known else None,
        "removed_rule_hit_callback_count": (
            removed_hit_callbacks if removed_known else None
        ),
        "removed_rule_hit_known_callbacks": removed_known,
        "removed_rule_hit_status": (
            "KNOWN" if ordered and removed_known == len(ordered)
            else "PARTIAL" if removed_known else "UNKNOWN"
        ),
        "invalid_callback_count": invalid_count,
        "exception_callback_count": exception_count,
        "avg_decision_ns": (
            sum(decision_ns) / len(decision_ns) if decision_ns else None
        ),
        "p95_decision_ns_nearest_rank": nearest_rank_p95(decision_ns),
    }
