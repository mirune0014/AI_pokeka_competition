"""Extract public-state Garchomp rotation opportunities from local traces."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path, write_csv


GARCHOMP_EX = 381


def iter_trace_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.jsonl"))


def option_type_value(value: Any) -> Any:
    return getattr(value, "value", value)


def selected_types(row: dict[str, Any]) -> str:
    options = row.get("options") or []
    names: list[str] = []
    for index in row.get("action") or []:
        if isinstance(index, int) and 0 <= index < len(options):
            names.append(str(options[index].get("type", "")))
    return " ".join(names)


def audit_trace(path: Path, retreat_type: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    retreat_value = option_type_value(retreat_type)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        trace = json.loads(line)
        player = trace.get("player")
        if player not in (0, 1):
            continue
        snapshot = trace.get("snapshot") or {}
        prefix = f"p{player}_"
        if snapshot.get(prefix + "active") != GARCHOMP_EX:
            continue

        hp = snapshot.get(prefix + "active_hp")
        max_hp = snapshot.get(prefix + "active_max_hp")
        if not isinstance(hp, int) or not isinstance(max_hp, int) or hp >= max_hp:
            continue

        bench_ids = snapshot.get(prefix + "bench") or []
        bench_hp = snapshot.get(prefix + "bench_hp") or []
        bench_energy = snapshot.get(prefix + "bench_energy") or []
        ready_indices = [
            index for index, card_id in enumerate(bench_ids)
            if card_id == GARCHOMP_EX
            and index < len(bench_energy)
            and isinstance(bench_energy[index], int)
            and bench_energy[index] >= 2
        ]
        if not ready_indices:
            continue

        options = trace.get("options") or []
        retreat_indices = [
            index for index, option in enumerate(options)
            if option_type_value(option.get("type")) == retreat_value
        ]
        if not retreat_indices:
            continue

        action = trace.get("action") or []
        active_energy_ids = snapshot.get(prefix + "active_energy_ids") or []
        active_tool_ids = snapshot.get(prefix + "active_tool_ids") or []
        rows.append(
            {
                "trace": str(path),
                "game": trace.get("game", ""),
                "step": trace.get("step", ""),
                "player": player,
                "turn": snapshot.get("turn", ""),
                "prizes": snapshot.get(prefix + "prizes", ""),
                "active_hp": hp,
                "active_max_hp": max_hp,
                "active_damage": max_hp - hp,
                "active_energy": snapshot.get(prefix + "active_energy", 0),
                "active_energy_ids": " ".join(str(card_id) for card_id in active_energy_ids),
                "active_tool_ids": " ".join(str(card_id) for card_id in active_tool_ids),
                "ready_bench_count": len(ready_indices),
                "ready_bench_hp": " ".join(
                    str(bench_hp[index]) for index in ready_indices if index < len(bench_hp)
                ),
                "ready_bench_energy": " ".join(str(bench_energy[index]) for index in ready_indices),
                "selected_types": selected_types(trace),
                "selected_retreat": bool(set(action) & set(retreat_indices)),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local Cynthia Garchomp rotation states.")
    parser.add_argument("traces", type=Path, nargs="+")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import OptionType

    rows: list[dict[str, Any]] = []
    files = list(iter_trace_files(args.traces))
    for path in files:
        rows.extend(audit_trace(path, OptionType.RETREAT))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else [
        "trace", "game", "step", "player", "turn", "prizes", "active_hp",
        "active_max_hp", "active_damage", "active_energy", "active_energy_ids",
        "active_tool_ids", "ready_bench_count", "ready_bench_hp",
        "ready_bench_energy", "selected_types", "selected_retreat",
    ]
    write_csv(args.output_dir / "rotation_states.csv", rows, fields)
    summary = {
        "trace_files": len(files),
        "rotation_states": len(rows),
        "episodes": len({(row["trace"], row["game"]) for row in rows}),
        "damage_ge_150": sum(int(row["active_damage"] >= 150) for row in rows),
        "damage_ge_200": sum(int(row["active_damage"] >= 200) for row in rows),
        "damage_ge_250": sum(int(row["active_damage"] >= 250) for row in rows),
        "selected_retreats": sum(int(row["selected_retreat"]) for row in rows),
    }
    (args.output_dir / "report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
