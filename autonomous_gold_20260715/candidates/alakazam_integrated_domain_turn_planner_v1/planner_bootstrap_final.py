"""Install final model corrections before any policy module captures them."""

import planner_runtime_model as runtime_model
import planner_validation as validation


runtime_model._DRAW_EVENTS.update(
    {
        "next mandatory draw",
        "H2 mandatory draw",
    }
)
runtime_model.install()
validation.install()

