from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def card_name(card: dict[str, Any] | None) -> str:
    if not card:
        return ""
    name = card.get("name")
    if name:
        return str(name)
    return str(card.get("id", ""))


def cards_summary(cards: list[dict[str, Any]] | None) -> str:
    if not cards:
        return ""
    counts = Counter(card_name(card) for card in cards if card)
    return "; ".join(f"{name} x{count}" for name, count in counts.most_common())


def zone_ids(cards: list[dict[str, Any]] | None) -> str:
    if not cards:
        return ""
    return ";".join(str(card.get("id", "")) for card in cards if card)


def snapshot_row(path: Path, episode_id: Any, step_index: int, agent_index: int, entry: dict[str, Any]) -> dict[str, Any]:
    obs = entry.get("observation") or {}
    current = obs.get("current") or {}
    players = current.get("players") or [{}, {}]
    while len(players) < 2:
        players.append({})
    p0, p1 = players[0], players[1]
    p0_active = (p0.get("active") or [None])[0]
    p1_active = (p1.get("active") or [None])[0]
    logs = obs.get("logs") or []
    attack_counts = Counter()
    played_counts = Counter()
    attach_counts = Counter()
    for log in logs:
        typ = log.get("type")
        pid = log.get("playerIndex")
        if typ == 15:
            attack_counts[f"p{pid}:{log.get('cardId')}:{log.get('attackId')}"] += 1
        elif typ == 10:
            played_counts[f"p{pid}:{log.get('cardId')}"] += 1
        elif typ == 11:
            attach_counts[f"p{pid}:{log.get('cardId')}->{log.get('cardIdTarget')}"] += 1

    return {
        "source": str(path),
        "episode_id": episode_id,
        "step_index": step_index,
        "agent_index": agent_index,
        "status": entry.get("status", ""),
        "reward": entry.get("reward", ""),
        "action": " ".join(str(x) for x in (entry.get("action") or [])),
        "turn": current.get("turn", ""),
        "result": current.get("result", ""),
        "your_index": current.get("yourIndex", ""),
        "p0_deck": p0.get("deckCount", ""),
        "p1_deck": p1.get("deckCount", ""),
        "p0_hand": p0.get("handCount", ""),
        "p1_hand": p1.get("handCount", ""),
        "p0_prizes": len([x for x in (p0.get("prize") or []) if x is None]),
        "p1_prizes": len([x for x in (p1.get("prize") or []) if x is None]),
        "p0_active": card_name(p0_active),
        "p0_active_hp": "" if not p0_active else p0_active.get("hp", ""),
        "p1_active": card_name(p1_active),
        "p1_active_hp": "" if not p1_active else p1_active.get("hp", ""),
        "p0_bench": cards_summary(p0.get("bench")),
        "p1_bench": cards_summary(p1.get("bench")),
        "p0_hand_cards": zone_ids(p0.get("hand")),
        "p1_hand_cards": zone_ids(p1.get("hand")),
        "p0_discard": cards_summary(p0.get("discard")),
        "p1_discard": cards_summary(p1.get("discard")),
        "logs_played": "; ".join(f"{k} x{v}" for k, v in played_counts.items()),
        "logs_attached": "; ".join(f"{k} x{v}" for k, v in attach_counts.items()),
        "logs_attacks": "; ".join(f"{k} x{v}" for k, v in attack_counts.items()),
    }


def iter_entries(data: dict[str, Any], path: Path):
    episode_id = (data.get("info") or {}).get("EpisodeId", "")
    for step_index, pair in enumerate(data.get("steps") or []):
        for agent_index, entry in enumerate(pair or []):
            if not isinstance(entry, dict):
                continue
            yield snapshot_row(path, episode_id, step_index, agent_index, entry)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Kaggle episode replay JSON.")
    parser.add_argument("replay", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--tail", type=int, default=12)
    args = parser.parse_args()

    data = json.loads(args.replay.read_text(encoding="utf-8"))
    rows = list(iter_entries(data, args.replay))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)

    print(
        json.dumps(
            {
                "episode_id": (data.get("info") or {}).get("EpisodeId", ""),
                "team_names": (data.get("info") or {}).get("TeamNames", []),
                "rewards": data.get("rewards", []),
                "statuses": data.get("statuses", []),
                "rows": len(rows),
            },
            ensure_ascii=False,
        )
    )
    for row in rows[-args.tail :]:
        print(
            f"step={row['step_index']} agent={row['agent_index']} status={row['status']} "
            f"reward={row['reward']} turn={row['turn']} result={row['result']} "
            f"p0={row['p0_active']}({row['p0_active_hp']}) bench=[{row['p0_bench']}] "
            f"p1={row['p1_active']}({row['p1_active_hp']}) bench=[{row['p1_bench']}] "
            f"logs={row['logs_played']} {row['logs_attacks']}"
        )


if __name__ == "__main__":
    main()
