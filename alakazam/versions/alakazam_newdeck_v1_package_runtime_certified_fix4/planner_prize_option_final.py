"""Opaque semantic keys for hidden Prize-slot selection options."""

import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model


_ORIGINAL_STABLE_KEY = runtime_model.stable_option_key


def stable_option_key(parent, obs, option):
    if getattr(option, "area", None) == parent.AreaType.PRIZE:
        owner = getattr(option, "playerIndex", None)
        index = getattr(option, "index", None)
        if owner not in (0, 1) or not isinstance(index, int) or isinstance(index, bool) or index < 0:
            return None
        prize_count = len(obs.current.players[owner].prize)
        if index >= prize_count:
            return None
        normalized = []
        for field in model.OPTION_FIELDS:
            value = model.enum_int(getattr(option, field, None))
            normalized.append(value)
        # Prize contents/order remain hidden. The public selectable slot is an
        # opaque stable identity and retains no card id/serial.
        return tuple(normalized) + (("hidden_prize_slot", owner, index), None, None, None)
    return _ORIGINAL_STABLE_KEY(parent, obs, option)


runtime_model.stable_option_key = stable_option_key
model.stable_option_key = stable_option_key
core.stable_option_key = stable_option_key

