"""Global physical-serial uniqueness including public selection zones."""

import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model


_ORIGINAL_PUBLIC_SNAPSHOT = runtime_model.public_snapshot


def _register(seen, card):
    row = model.card_row(card)
    if row is None or row[1] in seen:
        return False
    seen.add(row[1])
    return True


def _register_pokemon(seen, pokemon, owner):
    card_id = getattr(pokemon, "id", None)
    serial = getattr(pokemon, "serial", None)
    if not isinstance(card_id, int) or not isinstance(serial, int) or card_id <= 0 or serial <= 0 or serial in seen:
        return False
    seen.add(serial)
    for cards in (
        pokemon.energyCards or [],
        pokemon.tools or [],
        pokemon.preEvolution or [],
    ):
        for card in cards:
            if getattr(card, "playerIndex", None) != owner or not _register(seen, card):
                return False
    return True


def public_snapshot(parent, obs):
    seen = set()
    owner = obs.current.yourIndex
    for index, player in enumerate(obs.current.players):
        for pokemon in list(player.active) + list(player.bench):
            if not _register_pokemon(seen, pokemon, index):
                return None
        public_zones = [player.discard, getattr(player, "lost", None) or []]
        if index == owner:
            public_zones.append(player.hand or [])
        for cards in public_zones:
            for card in cards:
                if not _register(seen, card):
                    return None
    for card in obs.current.stadium:
        if not _register(seen, card):
            return None
    # Search/looking cards are currently exposed exact choices and must be
    # internally unique.  They are not allowed to alias another public zone.
    for cards in (obs.select.deck or [], obs.current.looking or []):
        for card in cards:
            if not _register(seen, card):
                return None
    return _ORIGINAL_PUBLIC_SNAPSHOT(parent, obs)


runtime_model.public_snapshot = public_snapshot
model.public_snapshot = public_snapshot
core.public_snapshot = public_snapshot

