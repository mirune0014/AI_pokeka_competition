"""Cache every validated first-seen callback action before parent reinvocation."""

import copy

import planner_final_policy as final_policy
import planner_policy as core


_ORIGINAL_AGENT = final_policy.agent


def agent(parent, parent_agent, obs_dict):
    action = _ORIGINAL_AGENT(parent, parent_agent, obs_dict)
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return action
    try:
        obs = parent.to_observation_class(copy.deepcopy(obs_dict))
        snapshot = core.public_snapshot(parent, obs)
        if snapshot is not None and core.action_is_valid(obs, action):
            # Overrides may already be present. _remember is idempotent for
            # the same semantic action and extends coverage to parent fallback,
            # transaction pass/complete/abort and other validated returns.
            core._remember(parent, obs, snapshot.sha256, action)
    except Exception:
        # A cache failure cannot make an already validated action illegal. The
        # duplicate shadow treats a subsequent parent call as structural fail.
        pass
    return action


final_policy.agent = agent

