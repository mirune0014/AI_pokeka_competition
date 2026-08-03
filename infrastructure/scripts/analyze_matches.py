from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / "_local_generated" / "logs"


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize local N's Zoroark action logs and eval results.")
    parser.add_argument("--action-log", type=Path, default=LOG_DIR / "action_log.jsonl")
    parser.add_argument("--eval-summary", type=Path, default=LOG_DIR / "eval_summary.csv")
    parser.add_argument("--out", type=Path, default=LOG_DIR / "match_analysis.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.action_log)
    by_game: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_game[str(row.get("game_id", ""))].append(row)

    action_counts = Counter()
    selected_reason_counts = Counter()
    phase_counts = Counter()
    zoroark_evolve_games = set()
    night_joker_count = 0
    trade_count = 0
    tome_or_substitute_count = 0
    end_count = 0
    suspicious_end = 0

    for row in rows:
        text = row.get("selected_option_text", "")
        reason = row.get("selected_reason", "")
        phase = row.get("phase", "")
        selected_reason_counts[reason] += 1
        phase_counts[phase] += 1
        action_type = text.split(" | ", 1)[0] if text else ""
        action_counts[action_type] += 1
        if "Zoroark ex" in text and "EVOLVE" in text:
            zoroark_evolve_games.add(str(row.get("game_id", "")))
        if "Night Joker" in text or "Night Joker" in reason:
            night_joker_count += 1
        if "Trade" in reason:
            trade_count += 1
        if "Dusk Ball substitute" in reason or "Transformation" in text:
            tome_or_substitute_count += 1
        if action_type == "END":
            end_count += 1
            top_text = " ".join(str(item.get("text", "")) for item in row.get("top5_options", []))
            if "ATTACK" in top_text:
                suspicious_end += 1

    analysis_rows = [
        {"metric": "decisions", "value": len(rows)},
        {"metric": "games_with_logs", "value": len(by_game)},
        {"metric": "zoroark_evolve_games", "value": len(zoroark_evolve_games)},
        {"metric": "trade_uses", "value": trade_count},
        {"metric": "night_joker_uses", "value": night_joker_count},
        {"metric": "transformation_tome_or_substitute_uses", "value": tome_or_substitute_count},
        {"metric": "end_turns", "value": end_count},
        {"metric": "suspicious_attack_available_end", "value": suspicious_end},
    ]
    for name, count in action_counts.most_common():
        analysis_rows.append({"metric": f"action_type:{name}", "value": count})
    for name, count in phase_counts.most_common():
        analysis_rows.append({"metric": f"phase:{name}", "value": count})
    for name, count in selected_reason_counts.most_common(20):
        analysis_rows.append({"metric": f"reason:{name}", "value": count})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(analysis_rows)

    print(f"Wrote {args.out}")
    for row in analysis_rows[:12]:
        print(f"{row['metric']}: {row['value']}")


if __name__ == "__main__":
    main()
