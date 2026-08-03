"""Separate public identities for Pokemon and Stadium Ability options."""

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
            pokemon = model._pokemon_for_area(parent, obs, option.area, option.index, owner)
            if pokemon is None:
                return None
            line = model.lineage_key(pokemon, owner)
            if line is None:
                return None
            rows.append((line, pokemon.serial, pokemon.id))
            continue
        if option.area == parent.AreaType.STADIUM:
            card = model._option_card(parent, obs, option)
            if card is None or not any(public.serial == card.serial and public.id == card.id for public in obs.current.stadium):
                return None
            # Owner indices are 0/1; sentinel 2 is a distinct global Stadium
            # ability namespace and can never collide with a Pokemon lineage.
            rows.append(((2, card.serial), card.serial, card.id))
            continue
        return None
    unique = tuple(sorted(set(rows)))
    return unique


runtime_model._legal_ability_rows = legal_ability_rows

