"""Frozen three-boundary replay shadow for Historical-Silver, Task 6, Task 9."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
SILVER = ROOT / "analysis_outputs/reference_agents/historical_silver_archaludon_54495224"
TASK6 = AUTO / "candidates/archaludon_public_ultra_ball_declared_complete_route_transaction_v1"
TASK9 = AUTO / "candidates/archaludon_public_prize_race_threat_control_t9_v1"
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / "live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new"
OUTPUT = Path(__file__).with_name("replay_first_differences.json")

sys.path[:0] = [str(TASK9), str(ROOT), str(ROOT / "tools")]
from ptcg_common import read_deck  # noqa: E402
from rl_ptcg.label_replay_rollout import replay_decisions, target_seat_for_deck  # noqa: E402


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def reset(module: Any) -> None:
    if hasattr(module, "_opp_last_attack_id"):
        module._opp_last_attack_id = None
    if hasattr(module, "_cur_turn_logs"):
        module._cur_turn_logs = []
    if hasattr(module, "_t9_transaction"):
        module._t9_transaction = None
    if hasattr(module, "_t8_is_transaction") and module._t8_is_transaction():
        module._t8_abort([], "silver_task9_shadow_reset")
    if hasattr(module, "_t7_transaction"):
        module._t7_transaction = None
    if hasattr(module, "_pfgear_reset_active"):
        module._pfgear_reset_active("silver_task9_shadow_reset")
    if hasattr(module, "_pcrd_clear"):
        module._pcrd_clear("silver_task9_shadow_reset")
    if hasattr(module, "_pfc_clear"):
        module._pfc_clear("silver_task9_shadow_reset")
    if hasattr(module, "_cum_reset_runtime"):
        module._cum_reset_runtime("silver_task9_shadow_reset")
    if hasattr(module, "_dper_reset_runtime"):
        module._dper_reset_runtime("silver_task9_shadow_reset")


def target_seat(replay: dict[str, Any], deck: list[int]) -> int:
    names = tuple(replay.get("info", {}).get("TeamNames", ()))
    named = tuple(seat for seat, name in enumerate(names) if name == "rurumi")
    return named[0] if named else target_seat_for_deck(replay, deck)


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if hasattr(value, "value"):
        return jsonable(value.value)
    if hasattr(value, "__dict__"):
        return jsonable(vars(value))
    return repr(value)


def telemetry_snapshot(module: Any) -> dict[str, Any]:
    keep = {
        "rule_id", "source", "selected_source", "winner", "winner_rule",
        "purpose", "reason", "rejection_reason", "stage", "owner",
        "owner_before", "sub_rule", "selected", "parent_action",
        "exact_parent_action", "suppressed_rule_ids", "decision",
        "result", "branch", "counters", "conservation",
    }
    rows: dict[str, Any] = {}
    for name, value in sorted(vars(module).items()):
        if not name.endswith("_last_telemetry") or not isinstance(value, dict):
            continue
        compact = {key: jsonable(value[key]) for key in keep if key in value}
        if compact:
            rows[name] = compact
    return rows


def pokemon_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "id": value.get("id"),
        "serial": value.get("serial"),
        "hp": value.get("hp"),
        "maxHp": value.get("maxHp"),
        "appearThisTurn": value.get("appearThisTurn"),
        "energyIds": [
            item.get("id") if isinstance(item, dict) else item
            for item in (value.get("energyCards") or value.get("energies") or [])
        ],
        "toolIds": [
            item.get("id") if isinstance(item, dict) else item
            for item in (value.get("tools") or value.get("toolIds") or [])
        ],
    }


def public_state(obs: dict[str, Any]) -> dict[str, Any]:
    current = obs.get("current") or {}
    players = current.get("players") or []
    seat = int(current.get("yourIndex", 0))
    output: dict[str, Any] = {
        "turn": current.get("turn"),
        "turnActionCount": current.get("turnActionCount"),
        "yourIndex": seat,
        "firstPlayer": current.get("firstPlayer"),
        "selectType": (obs.get("select") or {}).get("type"),
        "selectContext": (obs.get("select") or {}).get("context"),
        "optionCount": len((obs.get("select") or {}).get("options") or []),
    }
    for index, player in enumerate(players):
        player = player or {}
        active = [item for item in (player.get("active") or []) if item]
        bench = [item for item in (player.get("bench") or []) if item]
        row = {
            "prizes": len(player.get("prize") or []),
            "deckCount": player.get("deckCount"),
            "handCount": player.get("handCount"),
            "active": pokemon_summary(active[0]) if active else None,
            "bench": [pokemon_summary(item) for item in bench],
        }
        if index == seat:
            row["handIds"] = [
                item.get("id") for item in (player.get("hand") or [])
                if isinstance(item, dict)
            ]
        output[f"p{index}"] = row
    return output


def family(module: Any, parsed: Any, action: list[int]) -> str:
    semantic = module._cum_action_semantic(parsed, action)
    text = repr(semantic).upper()
    for label in (
        "ATTACK", "EVOLVE", "ENERGY", "ABILITY", "RETREAT", "PLAY",
        "END", "YES", "NO", "CARD", "POKEMON",
    ):
        if label in text:
            return label
    return "OTHER"


def compare_pair(
    *,
    pair_name: str,
    left_path: Path,
    right_path: Path,
    replay_paths: tuple[tuple[str, Path], ...],
    deck: list[int],
) -> dict[str, Any]:
    left = load(left_path, f"{pair_name}_left")
    right = load(right_path, f"{pair_name}_right")
    semantic_module = right if hasattr(right, "_cum_action_semantic") else load(TASK9, f"{pair_name}_semantic")
    episodes = []
    first_differences = []
    invalid_actions = []
    unreadable = []
    for corpus, replay_path in replay_paths:
        try:
            replay = json.loads(replay_path.read_bytes())
        except json.JSONDecodeError as error:
            unreadable.append({"corpus": corpus, "path": str(replay_path), "error": str(error)})
            continue
        seat = target_seat(replay, deck)
        reset(left)
        reset(right)
        decisions = 0
        first = None
        for step, obs, recorded in replay_decisions(replay, seat):
            decisions += 1
            left_action = left.agent(copy.deepcopy(obs))
            right_action = right.agent(copy.deepcopy(obs))
            parsed = semantic_module.to_observation_class(copy.deepcopy(obs))
            for label, action in (("left", left_action), ("right", right_action)):
                if not semantic_module._cum_valid_action(parsed, action):
                    invalid_actions.append({
                        "pair": pair_name, "episode": replay_path.stem,
                        "step": step, "label": label, "action": action,
                    })
            left_semantic = semantic_module._cum_action_semantic(parsed, left_action)
            right_semantic = semantic_module._cum_action_semantic(parsed, right_action)
            if left_semantic != right_semantic:
                first = {
                    "pair": pair_name,
                    "corpus": corpus,
                    "episode": replay_path.stem,
                    "seat": seat,
                    "step": step,
                    "recorded": recorded,
                    "replay_target_result": replay.get("result"),
                    "state": public_state(obs),
                    "left_action": left_action,
                    "right_action": right_action,
                    "left_semantic": jsonable(left_semantic),
                    "right_semantic": jsonable(right_semantic),
                    "left_family": family(semantic_module, parsed, left_action),
                    "right_family": family(semantic_module, parsed, right_action),
                    "right_telemetry": telemetry_snapshot(right),
                }
                first_differences.append(first)
                break
        episodes.append({
            "pair": pair_name,
            "corpus": corpus,
            "episode": replay_path.stem,
            "seat": seat,
            "decisions_until_boundary": decisions,
            "first_difference": first,
        })
    return {
        "pair": pair_name,
        "left_path": str(left_path.relative_to(ROOT)),
        "right_path": str(right_path.relative_to(ROOT)),
        "left_main_sha256": sha256(left_path / "main.py"),
        "right_main_sha256": sha256(right_path / "main.py"),
        "readable_episodes": len(episodes),
        "unreadable": unreadable,
        "first_difference_count": len(first_differences),
        "invalid_actions": invalid_actions,
        "family_transitions": {
            f"{left_family}->{right_family}": sum(
                row["left_family"] == left_family and row["right_family"] == right_family
                for row in first_differences
            )
            for left_family, right_family in sorted({
                (row["left_family"], row["right_family"]) for row in first_differences
            })
        },
        "first_differences": first_differences,
        "episodes": episodes,
    }


current_paths = tuple(("current", path) for path in sorted(CURRENT.glob("episode_*_replay.json")))
historical_all = tuple(sorted(HISTORICAL.glob("episode_*_replay.json")))
historical_paths = tuple(
    ("historical_sample", path)
    for path in sorted(
        sorted(
            historical_all,
            key=lambda path: hashlib.sha256(path.name.encode("utf-8")).hexdigest(),
        )[:32]
    )
)
replay_paths = current_paths + historical_paths
snapshot = hashlib.sha256()
for corpus, replay_path in replay_paths:
    snapshot.update(corpus.encode())
    snapshot.update(replay_path.name.encode())
    snapshot.update(hashlib.sha256(replay_path.read_bytes()).digest())
assert snapshot.hexdigest().upper() == "B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004"

deck = read_deck(SILVER / "deck.csv")
pairs = (
    ("silver_to_task6", SILVER, TASK6),
    ("task6_to_task9", TASK6, TASK9),
    ("silver_to_task9", SILVER, TASK9),
)
results = [
    compare_pair(
        pair_name=name,
        left_path=left,
        right_path=right,
        replay_paths=replay_paths,
        deck=deck,
    )
    for name, left, right in pairs
]
output = {
    "spec_sha256": sha256(Path(__file__).with_name("IMMUTABLE_COMPARISON_SPEC.md")),
    "corpus_snapshot_sha256": snapshot.hexdigest().upper(),
    "corpus_counts": {"current": len(current_paths), "historical_sample": len(historical_paths)},
    "historical_available": len(historical_all),
    "results": results,
}
OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({
    "snapshot": output["corpus_snapshot_sha256"],
    "pairs": [
        {
            "pair": row["pair"],
            "readable": row["readable_episodes"],
            "unreadable": len(row["unreadable"]),
            "first_differences": row["first_difference_count"],
            "invalid_actions": len(row["invalid_actions"]),
            "family_transitions": row["family_transitions"],
        }
        for row in results
    ],
}, indent=2))
