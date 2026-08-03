"""Final objective-schema validator used by the pre-override gate."""

from typing import Any

import planner_validation as validation


def valid_objective(plan: Any) -> bool:
    objective = plan.objective
    return (
        objective.shorter_certified_prize_lane <= 0
        and objective.fewer_abandoned_reservations <= 0
        and objective.lower_bench_prize_liability <= 0
        and isinstance(objective.stable_semantic_tie_break, tuple)
        and all(isinstance(value, str) for value in objective.stable_semantic_tie_break)
    )


validation._valid_objective = valid_objective

