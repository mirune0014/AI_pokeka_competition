"""Fail closed to the cumulative parent on unowned empty-board placeholders."""

import copy

import planner_final_policy as final_policy
import planner_policy as core
import planner_runtime_model as runtime_model


_ORIGINAL_AGENT = final_policy.agent


def _paired_placeholder(raw, obs):
    try:
        found = False
        for raw_player, parsed_player in zip(raw["current"]["players"], obs.current.players):
            for zone in ("active", "bench"):
                raw_zone = raw_player[zone]
                parsed_zone = getattr(parsed_player, zone)
                if len(raw_zone) != len(parsed_zone):
                    return False
                raw_mask = tuple(value is None for value in raw_zone)
                parsed_mask = tuple(value is None for value in parsed_zone)
                if raw_mask != parsed_mask:
                    return False
                found = found or any(raw_mask)
        return found
    except (KeyError, TypeError, AttributeError):
        return False


def agent(parent, parent_agent, obs_dict):
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return _ORIGINAL_AGENT(parent, parent_agent, obs_dict)
    try:
        obs = parent.to_observation_class(copy.deepcopy(obs_dict))
    except Exception:
        return _ORIGINAL_AGENT(parent, parent_agent, obs_dict)
    # The shortcut must never bypass the full raw/parsed boundary.  On a
    # mismatch, call the cumulative parent once with no cache or override.
    if not runtime_model.raw_parsed_agree(obs_dict, obs):
        core.reset_integrated_state()
        action = parent_agent(obs_dict)
        if core.action_is_valid(obs, action):
            core._trace(
                "PARITY_PARENT_FALLBACK",
                None,
                None,
                parent_action=action,
                reason="raw/parsed mismatch; cache disabled",
            )
            return action
        return core._emergency_lowest_legal(parent, obs_dict, "invalid cumulative-parent parity fallback")
    if not _paired_placeholder(obs_dict, obs):
        return _ORIGINAL_AGENT(parent, parent_agent, obs_dict)
    # A live atomic plan owns its placeholder callback.  In particular, Run
    # Away resolves through a TO_ACTIVE prompt with an empty Active sentinel;
    # the normal transaction path must advance or explicitly abort it.
    if core.INTEGRATED_TRANSACTION is not None:
        return _ORIGINAL_AGENT(parent, parent_agent, obs_dict)

    snapshot = core.public_snapshot(parent, obs)
    if snapshot is None:
        return _ORIGINAL_AGENT(parent, parent_agent, obs_dict)
    duplicate = core._duplicate_action(parent, obs, snapshot.sha256)
    if duplicate is not None:
        return duplicate

    # With no transaction owner there is no certifiable board role.  Do not
    # enter plan enumeration: call the cumulative parent exactly once,
    # validate its action, and cache the semantic choice.
    action = parent_agent(obs_dict)
    if not core.action_is_valid(obs, action):
        return core._emergency_lowest_legal(parent, obs_dict, "invalid cumulative-parent placeholder action")
    core._trace(
        "PLACEHOLDER_PARENT_FALLBACK",
        None,
        snapshot.sha256,
        parent_action=action,
        reason="paired empty-board placeholder without transaction owner",
    )
    return core._remember(parent, obs, snapshot.sha256, action)


final_policy.agent = agent
