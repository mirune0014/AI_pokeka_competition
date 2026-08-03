from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


GIBLE = 379
GABITE = 380
GARCHOMP_EX = 381
ROSELIA = 341
ROSERADE = 342
MAIN_LINE = {GIBLE, GABITE, GARCHOMP_EX}
TO_HAND = 7


def option_card_id(row: dict[str, Any], option_index: int) -> int | None:
    options = row.get("options") or []
    if option_index < 0 or option_index >= len(options):
        return None
    option = options[option_index] or {}
    if option.get("cardId") is not None:
        return int(option["cardId"])
    deck_index = option.get("index")
    deck = row.get("selection_deck_ids") or []
    if deck_index is None or int(deck_index) < 0 or int(deck_index) >= len(deck):
        return None
    card = deck[int(deck_index)]
    return int(card) if card is not None else None


def legal_card_ids(row: dict[str, Any]) -> list[int]:
    return [
        card
        for index in range(len(row.get("options") or []))
        if (card := option_card_id(row, index)) is not None
    ]


def route_target(row: dict[str, Any]) -> tuple[int | None, str]:
    player = int(row["player"])
    snapshot = row.get("snapshot") or {}
    active = snapshot.get(f"p{player}_active")
    bench = snapshot.get(f"p{player}_bench") or []
    in_play = [int(card) for card in ([active] + list(bench)) if card is not None]
    hand = [int(card) for card in (row.get("own_hand_ids") or [])]
    known = hand + in_play
    legal = set(legal_card_ids(row))

    attacker_secured = GARCHOMP_EX in known
    main_count = sum(card in MAIN_LINE for card in in_play)
    roselia_secured = ROSELIA in known or ROSERADE in in_play
    roserade_secured = ROSERADE in known

    if not attacker_secured and GARCHOMP_EX in legal:
        return GARCHOMP_EX, "secure first Garchomp attacker"

    if attacker_secured and main_count >= 2 and not (roselia_secured and roserade_secured):
        if not roselia_secured and ROSELIA in legal:
            return ROSELIA, "secure missing Roselia base"
        if not roserade_secured and ROSERADE in legal:
            return ROSERADE, "secure missing Roserade evolution"

    return None, "baseline fallback"


def iter_call_rows(trace_dirs: list[Path]):
    for trace_dir in trace_dirs:
        for path in sorted(trace_dir.glob("*.jsonl")):
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if row.get("context") == TO_HAND and row.get("effect_card_id") == GABITE:
                    yield path, row


def analyze(trace_dirs: list[Path]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path, row in iter_call_rows(trace_dirs):
        action = row.get("action") or []
        chosen = option_card_id(row, int(action[0])) if action else None
        target, reason = route_target(row)
        player = int(row["player"])
        snapshot = row.get("snapshot") or {}
        active = snapshot.get(f"p{player}_active")
        bench = snapshot.get(f"p{player}_bench") or []
        in_play = [int(card) for card in ([active] + list(bench)) if card is not None]
        hand = [int(card) for card in (row.get("own_hand_ids") or [])]
        output.append(
            {
                "trace": str(path),
                "game": row.get("game"),
                "step": row.get("step"),
                "player": player,
                "turn": snapshot.get("turn"),
                "chosen_card": chosen,
                "route_target": target,
                "route_reason": reason,
                "would_change": target is not None and target != chosen,
                "main_in_play": sum(card in MAIN_LINE for card in in_play),
                "bench_count": len(bench),
                "bench_max": snapshot.get(f"p{player}_bench_max"),
                "garchomp_known": GARCHOMP_EX in hand or GARCHOMP_EX in in_play,
                "roselia_known": ROSELIA in hand or ROSELIA in in_play or ROSERADE in in_play,
                "roserade_known": ROSERADE in hand or ROSERADE in in_play,
                "hand_ids": ":".join(map(str, hand)),
                "in_play_ids": ":".join(map(str, in_play)),
                "legal_cynthia_ids": ":".join(
                    map(str, [card for card in legal_card_ids(row) if card in {341, 342, 379, 380, 381, 387}])
                ),
            }
        )
    return output


def write_outputs(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "champions_call_opportunities.csv"
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    targets = Counter(row["route_reason"] for row in rows if row["route_target"] is not None)
    changes = [row for row in rows if row["would_change"]]
    by_player = Counter(int(row["player"]) for row in changes)
    summary = {
        "call_rows": len(rows),
        "route_target_rows": sum(row["route_target"] is not None for row in rows),
        "baseline_already_matches": sum(
            row["route_target"] is not None and row["route_target"] == row["chosen_card"] for row in rows
        ),
        "would_change": len(changes),
        "would_change_by_player": dict(sorted(by_player.items())),
        "target_reasons": dict(sorted(targets.items())),
        "changed_choice_pairs": dict(
            sorted(Counter(f'{row["chosen_card"]}->{row["route_target"]}' for row in changes).items())
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Champion's Call Route Diagnostic",
        "",
        f"- Call selections: {summary['call_rows']}",
        f"- Route had a preferred target: {summary['route_target_rows']}",
        f"- Baseline already matched: {summary['baseline_already_matches']}",
        f"- Proposed action changes: {summary['would_change']}",
        f"- Changes by player: {summary['would_change_by_player']}",
        f"- Target reasons: {summary['target_reasons']}",
        f"- Choice changes: {summary['changed_choice_pairs']}",
        "",
        "This diagnostic identifies the legal action surface only. It is not win-rate evidence.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Cynthia Champion's Call route choices in local traces.")
    parser.add_argument("--trace-dir", action="append", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = analyze(args.trace_dir)
    write_outputs(rows, args.out_dir)
    print(json.dumps({"rows": len(rows), "out_dir": str(args.out_dir)}))


if __name__ == "__main__":
    main()
