from __future__ import annotations

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW = HERE / "mismatch_diagnostics_raw_repair1"
DESTINATION = HERE / "MISMATCH_FIRST_DIFFERENCES.csv"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def telemetry_match(rows: list[dict], trace: dict) -> dict:
    matches = [
        row
        for row in rows
        if row.get("seat") == trace.get("player")
        and row.get("turn") == trace.get("snapshot", {}).get("turn")
        and row.get("turnActionCount")
        == trace.get("snapshot", {}).get("turn_action_count")
        and row.get("context") == trace.get("context")
        and row.get("action") == trace.get("action")
    ]
    if not matches:
        return {}
    semantic = {
        json.dumps(row.get("telemetry"), sort_keys=True, default=str)
        for row in matches
    }
    if len(semantic) != 1:
        raise AssertionError((trace, len(matches), len(semantic)))
    return matches[0].get("telemetry") or {}


def main() -> None:
    manifest = load_jsonl(RAW / "diagnostic_manifest.jsonl")
    output_rows = []
    for job in manifest:
        output = Path(job["output"])
        v2_telemetry = load_jsonl(output / "v2_telemetry.jsonl")
        v3_telemetry = load_jsonl(output / "v3_telemetry.jsonl")
        traces = output / "throwaway_traces"
        for seat in (0, 1):
            v2_trace_path = next(
                traces.glob(f"*_p{seat}_baseline_a/game_0000.jsonl")
            )
            v3_trace_path = next(
                traces.glob(f"*_p{seat}_candidate/game_0000.jsonl")
            )
            v2_trace = load_jsonl(v2_trace_path)
            v3_trace = load_jsonl(v3_trace_path)
            first = None
            for index in range(max(len(v2_trace), len(v3_trace))):
                left = v2_trace[index] if index < len(v2_trace) else None
                right = v3_trace[index] if index < len(v3_trace) else None
                if left != right:
                    first = (index, left, right)
                    break
            if first is None:
                continue
            index, left, right = first
            if left is None or right is None:
                raise AssertionError((job, seat, len(v2_trace), len(v3_trace)))
            v2 = telemetry_match(v2_telemetry, left)
            v3 = telemetry_match(v3_telemetry, right)
            v2_owner = v2.get("owner_after") or v2.get("owner_before") or {}
            v3_owner = v3.get("owner_after") or v3.get("owner_before") or {}
            output_rows.append(
                {
                    "opponent": job["opponent"],
                    "seed": job["seed"],
                    "seat": seat,
                    "trace_index": index,
                    "step": left.get("step"),
                    "turn": left.get("snapshot", {}).get("turn"),
                    "turn_action_count": left.get("snapshot", {}).get(
                        "turn_action_count"
                    ),
                    "context": left.get("context"),
                    "v2_action": json.dumps(left.get("action")),
                    "v3_action": json.dumps(right.get("action")),
                    "v2_selected_source": v2.get("selected_source"),
                    "v2_parent_semantic": json.dumps(v2.get("parent_semantic")),
                    "v2_proposal_semantic": json.dumps(v2.get("proposal_semantic")),
                    "v2_route": v2.get("rule3_route_kind")
                    or v2_owner.get("route_kind"),
                    "v2_stage": v2_owner.get("stage"),
                    "v2_rejection_reason": v2.get("rejection_reason"),
                    "v2_fault": bool(
                        v2.get("irreversible_abort_fault")
                        or v2.get("rule3_run_failed")
                    ),
                    "v3_selected_source": v3.get("selected_source"),
                    "v3_parent_semantic": json.dumps(v3.get("parent_semantic")),
                    "v3_proposal_semantic": json.dumps(v3.get("proposal_semantic")),
                    "v3_route": v3.get("rule3_route_kind")
                    or v3_owner.get("route_kind"),
                    "v3_stage": v3_owner.get("stage"),
                    "v3_rejection_reason": v3.get("rejection_reason"),
                    "v3_fault": bool(
                        v3.get("irreversible_abort_fault")
                        or v3.get("rule3_run_failed")
                    ),
                    "v2_steps": len(v2_trace),
                    "v3_steps": len(v3_trace),
                    "terminal_result": v2_trace[-1].get("snapshot", {}).get("result"),
                    "v2_trace": str(v2_trace_path),
                    "v3_trace": str(v3_trace_path),
                }
            )
    with DESTINATION.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(json.dumps({"rows": len(output_rows), "output": str(DESTINATION)}))


if __name__ == "__main__":
    main()
