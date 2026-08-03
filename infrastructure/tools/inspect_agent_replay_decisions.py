from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ptcg_common import load_agent, pushd


def _enum_name(value: Any) -> str:
    return getattr(value, "name", str(value))


def _card_label(card: Any) -> str:
    if not card:
        return ""
    name = getattr(card, "name", None)
    cid = getattr(card, "id", None)
    return f"{cid}:{name or ''}"


def _zone_ids(cards: list[Any]) -> str:
    values = []
    for card in cards or []:
        if card:
            values.append(str(getattr(card, "id", "")))
    return " ".join(values)


def _bench_ids(player: Any) -> str:
    return _zone_ids([p for p in getattr(player, "bench", []) if p])


def _active_id(player: Any) -> str:
    active = getattr(player, "active", []) or []
    return _card_label(active[0]) if active else ""


def _describe_option(module: Any, obs_obj: Any, opt: Any) -> dict[str, Any]:
    card = module.option_card(obs_obj, opt)
    target = module.option_target(obs_obj, opt)
    return {
        "type": _enum_name(getattr(opt, "type", "")),
        "card": _card_label(card),
        "target": _card_label(target),
        "attackId": getattr(opt, "attackId", ""),
        "area": _enum_name(getattr(opt, "inPlayArea", getattr(opt, "area", ""))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect scored decisions in a Kaggle replay using a candidate agent.")
    parser.add_argument("replay", type=Path)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--team", default="rurumi")
    parser.add_argument("--tail", type=int, default=8)
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args()

    data = json.loads(args.replay.read_text(encoding="utf-8"))
    teams = (data.get("info") or {}).get("TeamNames") or []
    try:
        target_agent_index = teams.index(args.team)
    except ValueError:
        raise SystemExit(f"team {args.team!r} not found in {teams!r}")

    sys.path.insert(0, str(Path("tools").resolve()))
    agent = load_agent(args.agent_dir, f"inspect_{args.agent_dir.name}")
    module = agent.module
    rows: list[dict[str, Any]] = []

    for step_index, pair in enumerate(data.get("steps") or []):
        if target_agent_index >= len(pair or []):
            continue
        entry = pair[target_agent_index]
        if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
            continue
        obs = entry.get("observation") or {}
        if not obs.get("select"):
            continue
        with pushd(args.agent_dir):
            action = agent(obs)
            obs_obj = module.to_observation_class(obs)
            scored = []
            for i, opt in enumerate(obs_obj.select.option):
                try:
                    value = module.score_option(obs_obj, opt)
                    if isinstance(value, tuple):
                        score, reason = value
                    else:
                        score, reason = value, ""
                except Exception as exc:  # pragma: no cover - debug script
                    score, reason = -999999, f"{type(exc).__name__}: {exc}"
                desc = _describe_option(module, obs_obj, opt)
                scored.append({"index": i, "score": score, "reason": reason, **desc})
            scored.sort(key=lambda row: (row["score"], -row["index"]), reverse=True)
        cur = obs_obj.current
        mine = cur.players[cur.yourIndex]
        opp = cur.players[1 - cur.yourIndex]
        rows.append(
            {
                "step": step_index,
                "turn": getattr(cur, "turn", ""),
                "context": _enum_name(getattr(obs_obj.select, "context", "")),
                "min": getattr(obs_obj.select, "minCount", ""),
                "max": getattr(obs_obj.select, "maxCount", ""),
                "action": action,
                "my_active": _active_id(mine),
                "my_bench": _bench_ids(mine),
                "my_hand": _zone_ids(getattr(mine, "hand", [])),
                "opp_active": _active_id(opp),
                "opp_bench": _bench_ids(opp),
                "top": scored[: args.top],
            }
        )

    print(json.dumps(rows[-args.tail :], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
