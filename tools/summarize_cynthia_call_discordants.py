from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analyze_cynthia_champions_call_route import (
    GABITE,
    GARCHOMP_EX,
    GIBLE,
    MAIN_LINE,
    ROSELIA,
    ROSERADE,
    option_card_id,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def first_action_divergence(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    for left, right in zip(baseline, candidate):
        if left.get("action") != right.get("action"):
            return left, right
    raise ValueError("no action divergence found")


def pokemon_with_appear(snapshot: dict[str, Any], player: int) -> list[tuple[int, bool | None]]:
    output: list[tuple[int, bool | None]] = []
    active = snapshot.get(f"p{player}_active")
    if active is not None:
        output.append((int(active), snapshot.get(f"p{player}_active_appear_this_turn")))
    bench = snapshot.get(f"p{player}_bench") or []
    appear = snapshot.get(f"p{player}_bench_appear_this_turn") or []
    output.extend(
        (int(card), appear[index] if index < len(appear) else None)
        for index, card in enumerate(bench)
        if card is not None
    )
    return output


def route_state(card_id: int | None) -> str:
    if card_id == GARCHOMP_EX:
        return "attacker"
    if card_id == ROSELIA:
        return "support_base"
    if card_id == ROSERADE:
        return "support_evolution"
    return "unexpected"


def summarize(paired_csv: Path, trace_root: Path) -> list[dict[str, Any]]:
    with paired_csv.open(encoding="utf-8", newline="") as handle:
        paired = list(csv.DictReader(handle))
    output: list[dict[str, Any]] = []
    for pair in paired:
        if pair["baseline_win"] == pair["candidate_win"]:
            continue
        seed = int(pair["seed"])
        seat = int(pair["seat"])
        flip = "gain" if pair["candidate_win"] == "1" else "loss"
        stem = f"seed_{seed}_p{seat}_{flip}"
        left = read_jsonl(trace_root / f"{stem}_baseline" / "game_0000.jsonl")
        right = read_jsonl(trace_root / f"{stem}_candidate" / "game_0000.jsonl")
        baseline_row, candidate_row = first_action_divergence(left, right)
        snapshot = baseline_row.get("snapshot") or {}
        pokemon = pokemon_with_appear(snapshot, seat)
        hand = [int(card) for card in (baseline_row.get("own_hand_ids") or [])]
        baseline_action = baseline_row.get("action") or []
        candidate_action = candidate_row.get("action") or []
        baseline_card = option_card_id(baseline_row, int(baseline_action[0])) if baseline_action else None
        candidate_card = option_card_id(candidate_row, int(candidate_action[0])) if candidate_action else None
        first_player = snapshot.get("first_player")
        output.append(
            {
                "seed": seed,
                "seat": seat,
                "flip": flip,
                "route_state": route_state(candidate_card),
                "step": baseline_row.get("step"),
                "turn": snapshot.get("turn"),
                "went_first": first_player is not None and int(first_player) == seat,
                "stadium_id": (snapshot.get("stadium") or baseline_row.get("stadium_id")),
                "effect_card_id": baseline_row.get("effect_card_id"),
                "baseline_card": baseline_card,
                "candidate_card": candidate_card,
                "main_in_play": sum(card in MAIN_LINE for card, _appear in pokemon),
                "gible_in_play": sum(card == GIBLE for card, _appear in pokemon),
                "eligible_gible": sum(card == GIBLE and appear is False for card, appear in pokemon),
                "gabite_in_play": sum(card == GABITE for card, _appear in pokemon),
                "eligible_gabite": sum(card == GABITE and appear is False for card, appear in pokemon),
                "unknown_age_gabite": sum(card == GABITE and appear is None for card, appear in pokemon),
                "garchomp_known": GARCHOMP_EX in hand or any(card == GARCHOMP_EX for card, _ in pokemon),
                "roselia_known": ROSELIA in hand or any(card == ROSELIA for card, _ in pokemon),
                "roserade_known": ROSERADE in hand or any(card == ROSERADE for card, _ in pokemon),
                "bench_count": len(snapshot.get(f"p{seat}_bench") or []),
                "own_active": snapshot.get(f"p{seat}_active"),
                "own_hand_ids": ":".join(map(str, hand)),
                "own_in_play_ids": ":".join(str(card) for card, _appear in pokemon),
                "opponent_active": snapshot.get(f"p{1 - seat}_active"),
            }
        )
    return output


def write(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "call_discordants.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["seed"])
        writer.writeheader()
        writer.writerows(rows)

    state_flip = Counter((row["route_state"], row["flip"]) for row in rows)
    attacker_age = Counter(
        ("gible_chain" if row["eligible_gible"] else "no_gible_chain", row["flip"])
        for row in rows
        if row["route_state"] == "attacker"
    )
    first_order = Counter((row["went_first"], row["flip"]) for row in rows)
    summary = {
        "discordant": len(rows),
        "state_flip": {f"{state}:{flip}": count for (state, flip), count in sorted(state_flip.items())},
        "attacker_gible_chain": {
            f"{age}:{flip}": count for (age, flip), count in sorted(attacker_age.items())
        },
        "turn_order": {f"went_first={first}:{flip}": count for (first, flip), count in sorted(first_order.items())},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(
        "\n".join(
            [
                "# Cynthia v50 Champion's Call Discordants",
                "",
                f"- Discordant games: {len(rows)}",
                f"- Route state by outcome: {summary['state_flip']}",
                f"- Attacker state by eligible Gible chain: {summary['attacker_gible_chain']}",
                f"- Turn order by outcome: {summary['turn_order']}",
                "",
                "These are post-selection outcome associations, not causal proof for a new guard.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize v50 Champion's Call discordant traces.")
    parser.add_argument("--paired-csv", type=Path, required=True)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = summarize(args.paired_csv, args.trace_root)
    write(rows, args.out_dir)
    print(json.dumps({"rows": len(rows), "out_dir": str(args.out_dir)}))


if __name__ == "__main__":
    main()
