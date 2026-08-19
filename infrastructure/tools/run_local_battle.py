from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

try:
    from infrastructure.tools.ptcg_common import (
        DEFAULT_AGENT_DIR,
        DEFAULT_ENGINE_DIR,
        ensure_engine_on_path,
        load_agent,
        pushd,
        read_deck,
    )
except ModuleNotFoundError:  # Direct execution from infrastructure/tools.
    from ptcg_common import (
        DEFAULT_AGENT_DIR,
        DEFAULT_ENGINE_DIR,
        ensure_engine_on_path,
        load_agent,
        pushd,
        read_deck,
    )


class AgentValidationMonitor:
    """Fail-closed validation hooks for agents that explicitly expose them."""

    def __init__(self, agents: list[Any]) -> None:
        self._agents = agents
        self._hooked = [False for _ in agents]
        self._failure_codes: list[str] = []
        self._record_count = 0
        self._records: list[dict[str, Any]] = []
        self._last_status: dict[str, Any] = {}
        self._next_drain_sequence = 0
        for index, agent in enumerate(agents):
            module = getattr(agent, "module", None)
            status_hook = getattr(module, "validation_status", None)
            if not callable(status_hook):
                continue
            self._hooked[index] = True
            drain_hook = getattr(module, "drain_validation_telemetry", None)
            finalize_hook = getattr(module, "finalize_validation_game", None)
            if not callable(drain_hook) or not callable(finalize_hook):
                self._fail("AGENT_{0}_VALIDATION_HOOK_INCOMPLETE".format(index))
                continue
            self._sample(index, drain=False)

    def _fail(self, code: object) -> None:
        value = str(code).replace("\r", " ").replace("\n", " ")[:256]
        if value and value not in self._failure_codes:
            self._failure_codes.append(value)

    def _module(self, index: int) -> Any:
        return getattr(self._agents[index], "module", None)

    def _ingest_status(self, index: int, status: Any) -> None:
        if not isinstance(status, Mapping):
            self._fail("AGENT_{0}_VALIDATION_STATUS_INVALID".format(index))
            return
        normalized = dict(status)
        self._last_status[str(index)] = normalized
        if normalized.get("telemetry_enabled") is not True:
            self._fail("AGENT_{0}_TELEMETRY_DISABLED".format(index))
        health = normalized.get("telemetry_health")
        if not isinstance(health, Mapping) or health.get("healthy") is not True:
            self._fail("AGENT_{0}_TELEMETRY_HEALTH_FAILED".format(index))
        if normalized.get("run_failed") is True:
            codes = normalized.get("failure_codes", ())
            if isinstance(codes, (tuple, list)):
                for code in codes:
                    self._fail("AGENT_{0}:{1}".format(index, code))
            else:
                self._fail("AGENT_{0}_RUN_FAILED".format(index))

    def _ingest_drain(self, index: int, envelope: Any) -> None:
        if not isinstance(envelope, Mapping):
            self._fail("AGENT_{0}_VALIDATION_DRAIN_INVALID".format(index))
            return
        status = envelope.get("status")
        if status is not None:
            self._ingest_status(index, status)
        telemetry = envelope.get("telemetry")
        if not isinstance(telemetry, Mapping):
            self._fail("AGENT_{0}_TELEMETRY_ENVELOPE_INVALID".format(index))
            return
        records = telemetry.get("records", ())
        if not isinstance(records, (tuple, list)):
            self._fail("AGENT_{0}_TELEMETRY_RECORDS_INVALID".format(index))
            return
        drain_sequence = self._next_drain_sequence
        self._next_drain_sequence += 1
        self._record_count += len(records)
        for drain_record_index, record in enumerate(records):
            if not isinstance(record, Mapping):
                self._fail(
                    "AGENT_{0}_TELEMETRY_RECORD_INVALID".format(index)
                )
                continue
            preserved = dict(record)
            preserved.update(
                agent_index=index,
                drain_sequence=drain_sequence,
                drain_record_index=drain_record_index,
            )
            self._records.append(preserved)
        lifetime = telemetry.get("lifetime_health")
        if isinstance(lifetime, Mapping) and lifetime.get("healthy") is not True:
            self._fail("AGENT_{0}_TELEMETRY_LIFETIME_FAILED".format(index))

    def _sample(self, index: int, *, drain: bool) -> None:
        if not self._hooked[index]:
            return
        module = self._module(index)
        try:
            self._ingest_status(index, module.validation_status())
            if drain:
                self._ingest_drain(index, module.drain_validation_telemetry())
        except Exception as exc:
            self._fail(
                "AGENT_{0}_VALIDATION_HOOK_ERROR:{1}".format(
                    index,
                    type(exc).__name__,
                )
            )

    def after_callback(self, index: int) -> None:
        self._sample(index, drain=True)

    def finalize_all(self, reason: str) -> None:
        for index, hooked in enumerate(self._hooked):
            if not hooked:
                continue
            module = self._module(index)
            try:
                self._ingest_status(
                    index,
                    module.finalize_validation_game(reason),
                )
            except Exception as exc:
                self._fail(
                    "AGENT_{0}_VALIDATION_FINALIZE_ERROR:{1}".format(
                        index,
                        type(exc).__name__,
                    )
                )
            self._sample(index, drain=True)

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(record) for record in self._records)

    def summary(self) -> dict[str, Any]:
        if not any(self._hooked):
            return {}
        return {
            "validation_hooked": True,
            "validation_failed": bool(self._failure_codes),
            "validation_failure_codes": tuple(self._failure_codes),
            "failure_codes": tuple(self._failure_codes),
            "validation_record_count": self._record_count,
            "validation_last_status": self._last_status,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_line(record: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(record),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def write_validation_trace(
    trace_dir: Path,
    game_index: int,
    records: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    path = trace_dir / f"game_{game_index:04d}.validation.jsonl"
    payload = "".join(canonical_json_line(record) for record in records).encode(
        "utf-8"
    )
    path.write_bytes(payload)
    return {
        "validation_trace": str(path),
        "validation_trace_sha256": hashlib.sha256(payload).hexdigest(),
        "validation_trace_record_count": len(records),
    }


def compact_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for entry in logs:
        item = {"type": entry.get("type"), "playerIndex": entry.get("playerIndex")}
        for key in (
            "cardId",
            "attackId",
            "serial",
            "serialTarget",
            "serialBench",
            "serialBefore",
            "serialAfter",
            "area",
            "index",
            "result",
            "reason",
            "value",
            "putDamageCounter",
            "cardIdTarget",
            "cardIdActive",
            "cardIdBench",
            "fromArea",
            "toArea",
        ):
            if key in entry:
                item[key] = entry[key]
        compact.append(item)
    return compact


def attached_card_ids(pokemon: dict[str, Any] | None, cards_key: str, ids_key: str) -> list[int]:
    if not pokemon:
        return []
    attached = pokemon.get(cards_key) or pokemon.get(ids_key) or []
    return [
        int(card.get("id")) if isinstance(card, dict) else int(card)
        for card in attached
        if card is not None and (not isinstance(card, dict) or card.get("id") is not None)
    ]


def player_snapshot(obs: dict[str, Any]) -> dict[str, Any]:
    current = obs.get("current") or {}
    players = current.get("players") or []
    output = {
        "turn": current.get("turn"),
        "turn_action_count": current.get("turnActionCount"),
        "your_index": current.get("yourIndex"),
        "first_player": current.get("firstPlayer"),
        "result": current.get("result"),
    }
    for i, player in enumerate(players):
        output[f"p{i}_deck"] = player.get("deckCount")
        output[f"p{i}_hand"] = player.get("handCount")
        output[f"p{i}_prizes"] = len(player.get("prize") or [])
        output[f"p{i}_bench_max"] = player.get("benchMax")
        active = player.get("active") or []
        active_pokemon = active[0] if active and active[0] else None
        output[f"p{i}_active"] = active_pokemon.get("id") if active_pokemon else None
        output[f"p{i}_active_hp"] = active_pokemon.get("hp") if active_pokemon else None
        output[f"p{i}_active_max_hp"] = active_pokemon.get("maxHp") if active_pokemon else None
        output[f"p{i}_active_appear_this_turn"] = (
            active_pokemon.get("appearThisTurn") if active_pokemon else None
        )
        active_energy_ids = attached_card_ids(active_pokemon, "energyCards", "energies")
        output[f"p{i}_active_energy"] = len(active_energy_ids)
        output[f"p{i}_active_energy_ids"] = active_energy_ids
        output[f"p{i}_active_tool_ids"] = attached_card_ids(active_pokemon, "tools", "toolIds")

        bench = [pokemon for pokemon in (player.get("bench") or []) if pokemon]
        output[f"p{i}_bench"] = [pokemon.get("id") for pokemon in bench]
        output[f"p{i}_bench_hp"] = [pokemon.get("hp") for pokemon in bench]
        output[f"p{i}_bench_max_hp"] = [pokemon.get("maxHp") for pokemon in bench]
        output[f"p{i}_bench_appear_this_turn"] = [
            pokemon.get("appearThisTurn") for pokemon in bench
        ]
        bench_energy_ids = [
            attached_card_ids(pokemon, "energyCards", "energies") for pokemon in bench
        ]
        output[f"p{i}_bench_energy"] = [len(ids) for ids in bench_energy_ids]
        output[f"p{i}_bench_energy_ids"] = bench_energy_ids
        output[f"p{i}_bench_tool_ids"] = [
            attached_card_ids(pokemon, "tools", "toolIds") for pokemon in bench
        ]
    return output


def compact_option(option: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "type",
        "area",
        "index",
        "playerIndex",
        "cardId",
        "attackId",
        "inPlayArea",
        "inPlayIndex",
        "inPlayPlayerIndex",
        "targetArea",
        "targetIndex",
        "targetPlayerIndex",
        "energyIndex",
        "toolIndex",
        "number",
    )
    return {key: option.get(key) for key in keys if key in option}


def card_id(card: dict[str, Any] | None) -> int | None:
    if not isinstance(card, dict) or card.get("id") is None:
        return None
    return int(card["id"])


def visible_card_ids(cards: list[dict[str, Any] | None] | None) -> list[int | None]:
    return [card_id(card) for card in (cards or [])]


def acting_hand_ids(obs: dict[str, Any]) -> list[int]:
    current = obs.get("current") or {}
    players = current.get("players") or []
    player = int(current.get("yourIndex", 0))
    if player < 0 or player >= len(players):
        return []
    hand = (players[player] or {}).get("hand") or []
    return [cid for card in hand if (cid := card_id(card)) is not None]


def score_trace(agent: Any, obs: dict[str, Any], action: list[int], limit: int) -> list[dict[str, Any]]:
    module = getattr(agent, "module", None)
    agent_dir = getattr(agent, "agent_dir", None)
    score_option = getattr(module, "score_option", None)
    to_observation_class = getattr(module, "to_observation_class", None)
    if not callable(score_option) or not callable(to_observation_class) or agent_dir is None:
        return []

    select = obs.get("select") or {}
    raw_options = select.get("option") or []
    selected = set(action)
    rows: list[dict[str, Any]] = []
    try:
        obs_obj = to_observation_class(obs)
        with pushd(agent_dir):
            for i, opt in enumerate(obs_obj.select.option):
                try:
                    score, reason = score_option(obs_obj, opt)
                except Exception as exc:
                    score, reason = -999999, f"error {type(exc).__name__}: {exc}"
                raw = raw_options[i] if i < len(raw_options) and isinstance(raw_options[i], dict) else {}
                rows.append(
                    {
                        "index": i,
                        "selected": i in selected,
                        "score": score,
                        "reason": reason,
                        "option": compact_option(raw),
                    }
                )
    except Exception as exc:
        return [{"index": -1, "selected": False, "score": -999999, "reason": f"trace error {type(exc).__name__}: {exc}", "option": {}}]

    rows.sort(key=lambda row: (row["score"], -row["index"]), reverse=True)
    if limit <= 0 or len(rows) <= limit:
        return rows
    top = rows[:limit]
    included = {row["index"] for row in top}
    top.extend(row for row in rows[limit:] if row["selected"] and row["index"] not in included)
    return top


def run_game(args: argparse.Namespace, game_index: int) -> dict[str, Any]:
    from cg.game import battle_finish, battle_select, battle_start

    seed_base = getattr(args, "seed_base", None)
    seed = None if seed_base is None else int(seed_base) + int(game_index)
    if seed is not None:
        random.seed(seed)

    agent_a_dir = args.agent_a.resolve()
    agent_b_dir = args.agent_b.resolve()
    deck_a = read_deck(args.deck_a or (agent_a_dir / "deck.csv"))
    deck_b = read_deck(args.deck_b or (agent_b_dir / "deck.csv"))
    agent_a = load_agent(agent_a_dir, f"agent_a_{game_index}")
    agent_b = load_agent(agent_b_dir, f"agent_b_{game_index}")
    agents = [agent_a, agent_b]
    validation = AgentValidationMonitor(agents)
    if seed is not None:
        for agent in agents:
            module_random = getattr(getattr(agent, "module", None), "random", None)
            if hasattr(module_random, "seed"):
                module_random.seed(seed)

    try:
        if getattr(args, "engine_seed", False):
            if seed is None:
                raise ValueError("--engine-seed requires --seed-base")
            obs, start_data = battle_start(deck_a, deck_b, seed=seed)
        else:
            obs, start_data = battle_start(deck_a, deck_b)
    except Exception:
        validation.finalize_all("BATTLE_START_EXCEPTION")
        raise
    if not obs:
        validation.finalize_all("BATTLE_START_FAILED")
        return {
            "game": game_index,
            "seed": seed if seed is not None else "",
            "started": False,
            "error_player": start_data.errorPlayer,
            "error_type": start_data.errorType,
            **validation.summary(),
        }

    trace_path = None
    trace_file = None
    if args.trace_dir:
        args.trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = args.trace_dir / f"game_{game_index:04d}.jsonl"
        trace_file = trace_path.open("w", encoding="utf-8")

    steps = 0
    action_errors = 0
    context_counts: Counter[int] = Counter()
    final_obs = obs
    try:
        while obs and obs.get("select") and steps < args.max_steps:
            current = obs.get("current") or {}
            if current.get("result") not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            select = obs.get("select") or {}
            if not select.get("option"):
                break
            context = select.get("context")
            if context is not None:
                context_counts[int(context)] += 1

            try:
                action = agents[player](obs)
            except Exception as exc:
                action_errors += 1
                raise RuntimeError(f"agent {player} failed at step {steps}: {exc}") from exc
            validation.after_callback(player)

            if trace_file:
                scored_options = (
                    score_trace(agents[player], obs, action, getattr(args, "trace_score_limit", 8))
                    if getattr(args, "trace_scores", False)
                    else []
                )
                trace_file.write(
                    json.dumps(
                        {
                            "game": game_index,
                            "step": steps,
                            "player": player,
                            "context": context,
                            "context_card_id": card_id(select.get("contextCard")),
                            "effect_card_id": card_id(select.get("effect")),
                            "select_type": select.get("type"),
                            "min_count": select.get("minCount"),
                            "max_count": select.get("maxCount"),
                            "option_count": len(select.get("option") or []),
                            "selection_deck_ids": visible_card_ids(select.get("deck")),
                            "options": [
                                compact_option(option)
                                for option in (select.get("option") or [])
                            ] if getattr(args, "trace_options", False) else [],
                            "action": action,
                            "own_hand_ids": acting_hand_ids(obs),
                            "snapshot": player_snapshot(obs),
                            "logs": compact_logs(obs.get("logs") or []),
                            "scores": scored_options,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            obs = battle_select(action)
            final_obs = obs
            steps += 1
    finally:
        final_current = (final_obs or {}).get("current") or {}
        if final_current.get("result") not in (None, -1):
            finalize_reason = "GAME_END"
        elif steps >= args.max_steps:
            finalize_reason = "MAX_STEPS"
        elif action_errors:
            finalize_reason = "AGENT_EXCEPTION_ABORT"
        else:
            finalize_reason = "RUNNER_ABORT"
        validation.finalize_all(finalize_reason)
        if trace_file:
            trace_file.close()
        battle_finish()

    if trace_path is not None:
        trace_metadata = {
            "trace": str(trace_path),
            "trace_sha256": sha256_file(trace_path),
            **write_validation_trace(
                args.trace_dir,
                game_index,
                validation.records,
            ),
        }
    else:
        trace_metadata = {
            "trace": "",
            "trace_sha256": "",
            "validation_trace": "",
            "validation_trace_sha256": "",
            "validation_trace_record_count": 0,
        }
    final_current = (final_obs or {}).get("current") or {}
    return {
        "game": game_index,
        "seed": seed if seed is not None else "",
        "started": True,
        "steps": steps,
        "hit_max_steps": steps >= args.max_steps,
        "result": final_current.get("result"),
        "turn": final_current.get("turn"),
        "action_errors": action_errors,
        **trace_metadata,
        "context_counts": dict(sorted(context_counts.items())),
        **validation.summary(),
        **player_snapshot(final_obs or {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local Pokemon TCG AI Battle games through the packaged cg engine."
    )
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--agent-a", type=Path, default=DEFAULT_AGENT_DIR)
    parser.add_argument("--agent-b", type=Path, default=DEFAULT_AGENT_DIR)
    parser.add_argument("--deck-a", type=Path)
    parser.add_argument("--deck-b", type=Path)
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--trace-dir", type=Path, default=Path("_local_generated/analysis_outputs/traces"))
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Do not create per-game trace files.",
    )
    parser.add_argument("--trace-scores", action="store_true", help="Include candidate score/reason data in traces when available.")
    parser.add_argument("--trace-score-limit", type=int, default=8, help="Number of top scored options to store per step.")
    parser.add_argument("--trace-options", action="store_true", help="Include compact identities for every legal option in traces.")
    parser.add_argument("--seed-base", type=int, help="Seed Python-side randomness as seed_base + game_index.")
    parser.add_argument(
        "--engine-seed", action="store_true",
        help="Pass the per-game seed to the local BattleStartSeeded API.",
    )
    parser.add_argument("--summary", type=Path, default=Path("_local_generated/analysis_outputs/local_battle_summary.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.no_trace:
        args.trace_dir = None
    ensure_engine_on_path(args.engine_dir)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", encoding="utf-8") as summary_file:
        validation_failed = False
        for game_index in range(args.games):
            result = run_game(args, game_index)
            summary_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(json.dumps(result, ensure_ascii=False))
            validation_failed = validation_failed or result.get("validation_failed", False)
    if validation_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
