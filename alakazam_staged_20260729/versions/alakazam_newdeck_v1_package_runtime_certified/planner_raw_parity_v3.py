"""Final raw parity: logs and known search-zone ownership."""

from dataclasses import asdict

import planner_raw_parity_v2 as v2
import planner_raw_parity_final as helpers
import planner_runtime_model as runtime_model


def raw_parsed_agree(raw, obs):
    if not v2.raw_parsed_agree(raw, obs):
        return False
    try:
        parsed = asdict(obs)
        owner = raw["current"]["yourIndex"]
        raw_deck = raw["select"].get("deck")
        parsed_deck = parsed["select"].get("deck")
        if raw_deck is not None and not helpers._cards(raw_deck, parsed_deck, owner):
            return False
        raw_looking = raw["current"].get("looking")
        parsed_looking = parsed["current"].get("looking")
        if raw_looking is not None and not helpers._cards(raw_looking, parsed_looking, owner):
            return False
        raw_logs = raw.get("logs", [])
        parsed_logs = parsed.get("logs", [])
        if len(raw_logs) != len(parsed_logs):
            return False
        for left, right in zip(raw_logs, parsed_logs):
            for field, value in left.items():
                if field == "head":
                    continue
                if helpers._value(value) != helpers._value(right.get(field)):
                    return False
        return True
    except (KeyError, TypeError, AttributeError):
        return False


runtime_model.raw_parsed_agree = raw_parsed_agree

