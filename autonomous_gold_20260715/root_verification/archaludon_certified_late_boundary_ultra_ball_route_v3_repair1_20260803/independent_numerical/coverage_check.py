from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


OUT_DIR = Path(__file__).resolve().parent
VERIFICATION_DIR = OUT_DIR.parent
TELEMETRY = [
    VERIFICATION_DIR / "natural_seed_recheck/seat0_seed271828198_telemetry.jsonl",
    VERIFICATION_DIR / "natural_seed_recheck/seat1_seed271828188_telemetry.jsonl",
]
EXPECTED_TELEMETRY_HASHES = {
    "seat0_seed271828198_telemetry.jsonl": "DD9896772E1B060CEC45BFF48F1E9D98423088A108A78555EAA3FCA0CA7F6975",
    "seat1_seed271828188_telemetry.jsonl": "2D2C104EB370183D1FB4E1061C0392A8D96428EE9D5AB4652D036140B5D48326",
}
RULE_ID = "CERTIFIED_LATE_BOUNDARY_ULTRA_BALL_ROUTE_V3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    starts: list[dict[str, Any]] = []
    flagged_rows: list[dict[str, Any]] = []
    input_hashes: dict[str, str] = {}
    for path in TELEMETRY:
        actual_hash = sha256(path)
        input_hashes[path.name] = actual_hash
        if actual_hash != EXPECTED_TELEMETRY_HASHES[path.name]:
            raise AssertionError(f"telemetry hash mismatch: {path}")
        for row_index, row in enumerate(read_jsonl(path)):
            telemetry = row.get("telemetry") or {}
            owner_after = telemetry.get("owner_after")
            if (
                telemetry.get("rule_id") == RULE_ID
                and telemetry.get("selected_source") == RULE_ID
                and telemetry.get("owner_before") is None
                and isinstance(owner_after, dict)
                and owner_after.get("stage") == "ULTRA_PLAY_EMITTED"
            ):
                starts.append(
                    {
                        "file": path.name,
                        "row_index": row_index,
                        "seat": int(row["seat"]),
                        "turn": int(row["turn"]),
                        "turn_action_count": int(row["turnActionCount"]),
                    }
                )
            flags = {
                field: telemetry.get(field)
                for field in (
                    "rule3_fault_latched",
                    "rule3_run_failed",
                    "irreversible_abort_fault",
                )
                if telemetry.get(field)
            }
            if flags:
                flagged_rows.append(
                    {"file": path.name, "row_index": row_index, "flags": flags}
                )

    first_differences_path = VERIFICATION_DIR / "fixed160_first_differences.csv"
    with first_differences_path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_differences = list(csv.DictReader(handle))
    starts_by_seat = Counter(start["seat"] for start in starts)
    minimum_total = 4
    minimum_per_seat = 1
    coverage = {
        "definition": (
            "A natural start is a telemetry row where the Rule3 policy is the "
            "selected source, owner_before is null, and owner_after enters "
            "ULTRA_PLAY_EMITTED. No gameplay action semantics are interpreted."
        ),
        "input_hashes": input_hashes,
        "first_differences_path": str(first_differences_path),
        "first_differences_sha256": sha256(first_differences_path),
        "first_difference_rows": len(first_differences),
        "starts": starts,
        "starts_total": len(starts),
        "starts_by_seat": {str(seat): starts_by_seat.get(seat, 0) for seat in (0, 1)},
        "minimum_total": minimum_total,
        "minimum_per_seat": minimum_per_seat,
        "total_coverage_pass": len(starts) >= minimum_total,
        "per_seat_coverage_pass": all(
            starts_by_seat.get(seat, 0) >= minimum_per_seat for seat in (0, 1)
        ),
        "coverage_shortfall": max(0, minimum_total - len(starts)),
        "fault_flagged_rows": flagged_rows,
        "fault_flagged_row_count": len(flagged_rows),
    }
    (OUT_DIR / "coverage_summary.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "starts": len(starts),
                "minimum": minimum_total,
                "coverage_pass": coverage["total_coverage_pass"],
                "faults": len(flagged_rows),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
