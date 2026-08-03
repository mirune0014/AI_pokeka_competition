"""Add exact public looking-zone parity to the complete raw gate."""

from dataclasses import asdict

import planner_raw_parity_final as v1
import planner_runtime_model as runtime_model


def raw_parsed_agree(raw, obs):
    if not v1.raw_parsed_agree(raw, obs):
        return False
    try:
        parsed = asdict(obs)
        raw_looking = raw["current"].get("looking")
        parsed_looking = parsed["current"].get("looking")
        if raw_looking is None or parsed_looking is None:
            return raw_looking is None and parsed_looking is None
        return v1._cards(raw_looking, parsed_looking)
    except (KeyError, TypeError, AttributeError):
        return False


runtime_model.raw_parsed_agree = raw_parsed_agree

