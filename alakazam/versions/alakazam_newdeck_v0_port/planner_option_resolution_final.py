"""Exact engine option-source resolution for implicit MAIN PLAY options."""

from typing import Any

import planner_model as model
import planner_policy as core


def option_card(parent: Any, obs: Any, option: Any):
    area = getattr(option, "area", None)
    index = getattr(option, "index", None)
    explicit_owner = getattr(option, "playerIndex", None)
    if explicit_owner is not None and explicit_owner not in (0, 1):
        return None
    owner = explicit_owner if explicit_owner in (0, 1) else obs.current.yourIndex
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    # Checked-engine MAIN PLAY options omit area/playerIndex and address the
    # acting player's hand by index.  No other omitted-area option is inferred.
    if area is None and option.type == parent.OptionType.PLAY:
        hand = obs.current.players[obs.current.yourIndex].hand or []
        return hand[index] if owner == obs.current.yourIndex and index < len(hand) else None
    if area == parent.AreaType.DECK:
        zone = obs.select.deck or []
    elif area == parent.AreaType.LOOKING:
        zone = obs.current.looking or []
    else:
        player = obs.current.players[owner]
        zones = {
            parent.AreaType.HAND: player.hand or [],
            parent.AreaType.DISCARD: player.discard,
            parent.AreaType.ACTIVE: player.active,
            parent.AreaType.BENCH: player.bench,
            parent.AreaType.PRIZE: player.prize,
            parent.AreaType.STADIUM: obs.current.stadium,
        }
        if area not in zones:
            return None
        zone = zones[area]
    return zone[index] if index < len(zone) else None


model._option_card = option_card
core._option_card = option_card

