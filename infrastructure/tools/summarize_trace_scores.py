from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path


def iter_trace_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.jsonl"))


def load_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def name_lookup(engine_dir: Path) -> tuple[dict[int, str], dict[int, str]]:
    ensure_engine_on_path(engine_dir)
    from cg.api import all_attack, all_card_data

    return (
        {card.cardId: card.name for card in all_card_data()},
        {attack.attackId: attack.name for attack in all_attack()},
    )


def describe_option(option: dict[str, Any], card_names: dict[int, str], attack_names: dict[int, str]) -> str:
    cid = option.get("cardId")
    aid = option.get("attackId")
    parts = [f"type={option.get('type')}"]
    if cid is not None:
        parts.append(f"card={card_names.get(int(cid), str(cid))}({cid})")
    if aid is not None:
        parts.append(f"attack={attack_names.get(int(aid), str(aid))}({aid})")
    for key in ("playerIndex", "area", "index", "inPlayArea", "inPlayIndex", "number"):
        if key in option:
            parts.append(f"{key}={option[key]}")
    return " ".join(parts)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize selected score reasons from local battle JSONL traces.")
    parser.add_argument("trace_path", type=Path)
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--out", type=Path, default=Path("_local_generated/analysis_outputs/trace_score_reasons.csv"))
    parser.add_argument("--game-out", type=Path, default=Path("_local_generated/analysis_outputs/trace_score_reason_games.csv"))
    parser.add_argument(
        "--pattern",
        action="append",
        help="Optional substring filter for reasons. Repeat to count multiple trigger patterns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    card_names, attack_names = name_lookup(args.engine_dir)

    reason_counts: Counter[tuple[str, int, int, str, str]] = Counter()
    pattern_counts: Counter[tuple[str, str, int]] = Counter()
    game_rows: list[dict[str, Any]] = []
    patterns = args.pattern or []

    for path in iter_trace_files(args.trace_path):
        final_result = ""
        final_turn = ""
        selected_reasons: Counter[str] = Counter()
        pattern_hits: Counter[str] = Counter()
        step_count = 0
        for row in load_rows(path):
            step_count += 1
            snapshot = row.get("snapshot") or {}
            final_result = snapshot.get("result", final_result)
            final_turn = snapshot.get("turn", final_turn)
            player = int(row.get("player", -1))
            context = int(row.get("context", -1)) if row.get("context") is not None else -1
            for score_row in row.get("scores") or []:
                if not score_row.get("selected"):
                    continue
                reason = str(score_row.get("reason", ""))
                option = score_row.get("option") or {}
                option_desc = describe_option(option, card_names, attack_names)
                reason_counts[(path.parent.name, player, context, reason, option_desc)] += 1
                selected_reasons[reason] += 1
                for pattern in patterns:
                    if pattern in reason:
                        pattern_counts[(path.parent.name, pattern, player)] += 1
                        pattern_hits[pattern] += 1

        game_row = {
            "trace": str(path),
            "bucket": path.parent.name,
            "game": path.stem,
            "steps": step_count,
            "result": final_result,
            "turn": final_turn,
            "selected_reasons": "; ".join(f"{reason} x{count}" for reason, count in selected_reasons.most_common(12)),
        }
        for pattern in patterns:
            game_row[f"pattern:{pattern}"] = pattern_hits.get(pattern, 0)
        game_rows.append(game_row)

    reason_rows = [
        {
            "bucket": bucket,
            "player": player,
            "context": context,
            "reason": reason,
            "option": option,
            "count": count,
        }
        for (bucket, player, context, reason, option), count in reason_counts.most_common()
    ]
    write_csv(args.out, reason_rows, ["bucket", "player", "context", "reason", "option", "count"])

    game_fieldnames = ["trace", "bucket", "game", "steps", "result", "turn", "selected_reasons"]
    game_fieldnames.extend(f"pattern:{pattern}" for pattern in patterns)
    write_csv(args.game_out, game_rows, game_fieldnames)

    print(f"Wrote {args.out}")
    print(f"Wrote {args.game_out}")
    if patterns:
        for (bucket, pattern, player), count in pattern_counts.most_common():
            print(f"{bucket} player={player} pattern={pattern!r}: {count}")


if __name__ == "__main__":
    main()
