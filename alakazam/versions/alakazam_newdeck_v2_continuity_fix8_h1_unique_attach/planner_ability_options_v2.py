"""Reject duplicate or owner-confused Ability identities."""

import planner_model as model
import planner_runtime_model as runtime_model


def legal_ability_rows(parent, obs):
    rows = []
    if obs.select is None:
        return ()
    owner = obs.current.yourIndex
    for option in obs.select.option:
        if option.type != parent.OptionType.ABILITY:
            continue
        if option.area in (parent.AreaType.ACTIVE, parent.AreaType.BENCH):
            # Pokemon Ability choices are actor-owned.  An omitted owner is a
            # valid engine shorthand; an explicit opponent owner is not.
            if option.playerIndex not in (None, owner):
                return None
            pokemon = model._pokemon_for_area(parent, obs, option.area, option.index, owner)
            if pokemon is None:
                return None
            line = model.lineage_key(pokemon, owner)
            if line is None:
                return None
            rows.append((line, pokemon.serial, pokemon.id))
            continue
        if option.area == parent.AreaType.STADIUM:
            # Stadium is global.  Its physical card may belong to either
            # player, so option.playerIndex is deliberately not actor-gated.
            card = model._option_card(parent, obs, option)
            if card is None or not any(
                public.serial == card.serial and public.id == card.id for public in obs.current.stadium
            ):
                return None
            rows.append(((2, card.serial), card.serial, card.id))
            continue
        return None
    if len(rows) != len(set(rows)):
        return None
    return tuple(sorted(rows))


runtime_model._legal_ability_rows = legal_ability_rows
