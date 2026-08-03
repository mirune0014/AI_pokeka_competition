from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKED_ROOT_RECOMPUTE = (
    ROOT
    / "autonomous_gold_20260715"
    / "root_verification"
    / "archaludon_certified_late_boundary_ultra_ball_route_v3_20260803"
    / "root_recompute_fixed160.py"
)
RAW = (
    ROOT
    / "autonomous_gold_20260715"
    / "evaluations"
    / "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1"
    / "fixed160_raw"
)


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "checked_rule3_v3_root_recompute", CHECKED_ROOT_RECOMPUTE
    )
    if spec is None or spec.loader is None:
        raise AssertionError("failed to bind checked root recomputation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RAW = RAW
    module.main()


if __name__ == "__main__":
    main()
