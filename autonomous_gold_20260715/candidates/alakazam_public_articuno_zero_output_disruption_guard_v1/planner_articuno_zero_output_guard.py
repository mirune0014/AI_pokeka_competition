"""Public Articuno zero-output Enhanced Hammer transaction.

The rule is intentionally narrow.  It recognizes only the frozen public
metadata needed to prove that Powerful Hand places no counters, that one
physical Team Rocket's Energy is the sole Enhanced Hammer target, and that
all printed attacks of the protected Active are unpaid after its removal.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from typing import Any

import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model
from planner_model import BaseRole, ResourceLedger


KIND = "PUBLIC_ARTICUNO_ZERO_OUTPUT_DISRUPTION_GUARD_V1"
ARTICUNO = 414
ALAKAZAM = 743
POWERFUL_HAND = 1072
ENHANCED_HAMMER = 1081
TEAM_ROCKET_ENERGY = 15
TELEPATH_PSYCHIC = 19
ENRICHING_ENERGY = 13

ARTICUNO_SKILL = (
    " Repelling Veil",
    "Prevent all effects of attacks used by your opponent’s Pokémon done to "
    "your Basic Team Rocket’s Pokémon. (Existing effects are not removed. "
    "Damage is not an effect.)",
)
POWERFUL_HAND_TEXT = (
    "Place 2 damage counters on your opponent’s Active Pokémon for each card "
    "in your hand."
)
HAMMER_TEXT = "Discard a Special Energy from 1 of your opponent’s Pokémon."
TEAM_ROCKET_ENERGY_TEXT = (
    "This card can only be attached to a Team Rocket’s Pokémon. If this card "
    "is attached to anything other than a Team Rocket’s Pokémon, discard this "
    "card.\n\nAs long as this card is attached to a Pokémon, it provides 2 in "
    "any combination of {P} Energy and {D} Energy."
)
TELEPATH_TEXT = (
    "As long as this card is attached to a Pokémon, it provides {P} Energy.\n"
    "When you attach this card from your hand to a {P} Pokémon, search your "
    "deck for up to 2 Basic {P} Pokémon and put them onto your Bench. Then, "
    "shuffle your deck."
)
ENRICHING_TEXT = (
    "As long as this card is attached to a Pokémon, it provides {C} Energy.\n\n"
    "When you attach this card from your hand to a Pokémon, draw 4 cards."
)

_BASIC_NAMES = {
    1: "Basic {G} Energy",
    2: "Basic {R} Energy",
    3: "Basic {W} Energy",
    4: "Basic {L} Energy",
    5: "Basic {P} Energy",
    6: "Basic {F} Energy",
    7: "Basic {D} Energy",
    8: "Basic {M} Energy",
}

_SAFE_POKEMON_SKILLS = {
    343: {
        (
            " Flower Curtain",
            "Prevent all damage done to your Benched Pokémon that don’t have a "
            "Rule Box by attacks from your opponent’s Pokémon. (Pokémon {ex}, "
            "Pokémon {V}, etc. have Rule Boxes.)",
        )
    },
    142: {
        (
            "ACE Nullifier",
            "If this Pokémon has a Pokémon Tool attached, your opponent can’t "
            "play any {ACE SPEC} cards from their hand.",
        )
    },
    858: {
        (
            " Damp",
            "Pokémon in play\u00a0(both yours and your opponent’s)\u00a0lose any "
            "Ability that requires the Pokémon using it to Knock Out itself.",
        )
    },
    859: {
        (
            " Damp",
            "Pokémon in play\u00a0(both yours and your opponent’s)\u00a0lose any "
            "Ability that requires the Pokémon using it to Knock Out itself.",
        )
    },
    401: {
        (
            " Charging Up",
            "Once during your turn, you may attach a Basic Energy card from "
            "your discard pile to this Pokémon.",
        )
    },
    431: {
        (
            " Power Saver",
            "This Pokémon can’t attack unless you have 4 or more Team Rocket’s "
            "Pokémon in play.",
        )
    },
    742: {
        (
            " Psychic Draw",
            "Once during your turn, when you play this Pokémon from your hand "
            "to evolve 1 of your Pokémon, you may use this Ability. Draw 2 cards.",
        )
    },
    743: {
        (
            " Psychic Draw",
            "Once during your turn, when you play this Pokémon from your hand "
            "to evolve 1 of your Pokémon, you may use this Ability. Draw 3 cards.",
        )
    },
}


def _api():
    import planner_final_policy as api

    return api


def _is_int(value: Any) -> bool:
    return type(value) is int


def _card_row(card: Any, owner: int | None = None):
    if card is None:
        return None
    row = (
        getattr(card, "id", None),
        getattr(card, "serial", None),
        getattr(card, "playerIndex", None),
    )
    if (
        not all(_is_int(value) for value in row)
        or row[0] <= 0
        or row[1] <= 0
        or row[2] not in (0, 1)
        or (owner is not None and row[2] != owner)
    ):
        return None
    return row


def _nonpokemon_shell(
    parent: Any,
    data: Any,
    card_id: int,
    name: str,
    card_type: Any,
    energy_type: int,
    *,
    ace_spec: bool = False,
) -> bool:
    return (
        data is not None
        and _is_int(data.cardId)
        and data.cardId == card_id
        and data.name == name
        and data.cardType == card_type
        and data.retreatCost == 0
        and data.hp == 0
        and data.weakness is None
        and data.resistance is None
        and data.energyType == energy_type
        and data.basic is False
        and data.stage1 is False
        and data.stage2 is False
        and data.ex is False
        and data.megaEx is False
        and data.tera is False
        and data.aceSpec is ace_spec
        and data.evolvesFrom is None
        and isinstance(data.skills, list)
        and isinstance(data.attacks, list)
        and not data.attacks
    )


def _one_skill(data: Any, name: str, text: str) -> bool:
    return (
        data is not None
        and len(data.skills or ()) == 1
        and data.skills[0].name == name
        and data.skills[0].text == text
    )


def _basic_energy_units(parent: Any, card_id: int):
    data = parent.card_table.get(card_id)
    name = _BASIC_NAMES.get(card_id)
    if (
        name is None
        or not _nonpokemon_shell(
            parent,
            data,
            card_id,
            name,
            parent.CardType.BASIC_ENERGY,
            card_id,
        )
        or data.skills
    ):
        return None
    return (card_id,)


def _team_rocket_energy_units(parent: Any, card_id: int, pokemon_data: Any):
    data = parent.card_table.get(card_id)
    team_rocket = int(parent.EnergyType.TEAM_ROCKET)
    if (
        card_id != TEAM_ROCKET_ENERGY
        or pokemon_data is None
        or not pokemon_data.name.startswith("Team Rocket's ")
        or not _nonpokemon_shell(
            parent,
            data,
            TEAM_ROCKET_ENERGY,
            "Team Rocket's Energy",
            parent.CardType.SPECIAL_ENERGY,
            int(parent.EnergyType.COLORLESS),
        )
        or not _one_skill(
            data, "Team Rocket's Energy", TEAM_ROCKET_ENERGY_TEXT
        )
    ):
        return None
    return (team_rocket, team_rocket)


def _telepath_units(parent: Any, card_id: int):
    data = parent.card_table.get(card_id)
    if (
        card_id != TELEPATH_PSYCHIC
        or not _nonpokemon_shell(
            parent,
            data,
            TELEPATH_PSYCHIC,
            "Telepath Psychic Energy",
            parent.CardType.SPECIAL_ENERGY,
            int(parent.EnergyType.PSYCHIC),
        )
        or not _one_skill(data, "Telepath Psychic Energy", TELEPATH_TEXT)
    ):
        return None
    return (int(parent.EnergyType.PSYCHIC),)


def _enriching_units(parent: Any, card_id: int):
    data = parent.card_table.get(card_id)
    if (
        card_id != ENRICHING_ENERGY
        or not _nonpokemon_shell(
            parent,
            data,
            ENRICHING_ENERGY,
            "Enriching Energy",
            parent.CardType.SPECIAL_ENERGY,
            int(parent.EnergyType.COLORLESS),
            ace_spec=True,
        )
        or not _one_skill(data, "Enriching Energy", ENRICHING_TEXT)
    ):
        return None
    return (int(parent.EnergyType.COLORLESS),)


def _energy_parts(parent: Any, pokemon: Any):
    data = parent.card_table.get(getattr(pokemon, "id", None))
    cards = getattr(pokemon, "energyCards", None)
    observed = getattr(pokemon, "energies", None)
    if data is None or not isinstance(cards, list) or not isinstance(observed, list):
        return None
    parts = []
    for card in cards:
        row = _card_row(card, getattr(pokemon, "playerIndex", None))
        card_data = parent.card_table.get(getattr(card, "id", None))
        if row is None or card_data is None:
            return None
        if card_data.cardType == parent.CardType.BASIC_ENERGY:
            units = _basic_energy_units(parent, card.id)
        elif card.id == TEAM_ROCKET_ENERGY:
            units = _team_rocket_energy_units(parent, card.id, data)
        elif card.id == TELEPATH_PSYCHIC:
            units = _telepath_units(parent, card.id)
        elif card.id == ENRICHING_ENERGY:
            units = _enriching_units(parent, card.id)
        else:
            return None
        if units is None:
            return None
        parts.append((row, tuple(units)))
    flattened = tuple(unit for _, units in parts for unit in units)
    try:
        actual = tuple(int(unit) for unit in observed)
    except (TypeError, ValueError):
        return None
    return tuple(parts) if actual == flattened else None


def _lineage_is_exact(parent: Any, pokemon: Any, data: Any, owner: int) -> bool:
    lineage = getattr(pokemon, "preEvolution", None)
    if not isinstance(lineage, list):
        return False
    if data.basic:
        return (
            not lineage
            and not data.stage1
            and not data.stage2
            and data.evolvesFrom is None
        )
    if (
        pokemon.id == ALAKAZAM
        and parent._two_prize_alakazam_lineage_is_complete(pokemon, owner)
    ):
        return True
    expected = data.evolvesFrom
    if not isinstance(expected, str) or not expected:
        return False
    expected_count = 1 if data.stage1 and not data.stage2 else 2 if data.stage2 and not data.stage1 else -1
    if len(lineage) != expected_count:
        return False
    for card in reversed(lineage):
        row = _card_row(card, owner)
        prior = parent.card_table.get(getattr(card, "id", None))
        if (
            row is None
            or prior is None
            or prior.cardType != parent.CardType.POKEMON
            or prior.name != expected
        ):
            return False
        expected = prior.evolvesFrom
    bottom = parent.card_table.get(lineage[0].id) if lineage else None
    return bool(bottom is not None and bottom.basic and expected is None)


def _stack_is_exact(parent: Any, pokemon: Any, owner: int) -> bool:
    data = parent.card_table.get(getattr(pokemon, "id", None))
    if (
        data is None
        or data.cardType != parent.CardType.POKEMON
        or not _is_int(getattr(pokemon, "serial", None))
        or pokemon.serial <= 0
        or not _is_int(getattr(pokemon, "hp", None))
        or not _is_int(getattr(pokemon, "maxHp", None))
        or pokemon.maxHp != data.hp
        or not 0 < pokemon.hp <= pokemon.maxHp
        or type(getattr(pokemon, "appearThisTurn", None)) is not bool
        or not _lineage_is_exact(parent, pokemon, data, owner)
        or _energy_parts(parent, pokemon) is None
        or any(_card_row(card, owner) is None for card in pokemon.energyCards)
        or not isinstance(getattr(pokemon, "tools", None), list)
    ):
        return False
    for tool in pokemon.tools:
        row = _card_row(tool, owner)
        metadata = parent.card_table.get(getattr(tool, "id", None))
        if row is None or metadata is None or metadata.cardType != parent.CardType.TOOL:
            return False
    serials = [
        pokemon.serial,
        *(card.serial for card in pokemon.preEvolution),
        *(card.serial for card in pokemon.energyCards),
        *(card.serial for card in pokemon.tools),
    ]
    return len(serials) == len(set(serials))


def _attack_is_exact(parent: Any, attack_id: int):
    attack = parent.attack_table.get(attack_id)
    valid_units = {int(value) for value in parent.EnergyType}
    if (
        attack is None
        or not _is_int(attack.attackId)
        or attack.attackId != attack_id
        or not isinstance(attack.name, str)
        or not attack.name
        or not isinstance(attack.text, str)
        or not _is_int(attack.damage)
        or attack.damage < 0
        or not isinstance(attack.energies, list)
        or any(not _is_int(unit) or unit not in valid_units for unit in attack.energies)
    ):
        return None
    return attack


def _printed_attack_rows(parent: Any, pokemon: Any):
    data = parent.card_table.get(getattr(pokemon, "id", None))
    if data is None or not isinstance(data.attacks, list) or not data.attacks:
        return None
    rows = []
    for attack_id in data.attacks:
        attack = _attack_is_exact(parent, attack_id)
        if attack is None:
            return None
        rows.append(
            (attack.attackId, attack.name, attack.text, attack.damage, tuple(attack.energies))
        )
    return tuple(rows)
def _articuno_metadata_is_exact(parent: Any) -> bool:
    data = parent.card_table.get(ARTICUNO)
    attack = _attack_is_exact(parent, 583)
    return (
        data is not None
        and data.cardId == ARTICUNO
        and data.name == "Team Rocket's Articuno"
        and data.cardType == parent.CardType.POKEMON
        and data.retreatCost == 1
        and data.hp == 120
        and data.weakness == int(parent.EnergyType.LIGHTNING)
        and data.resistance == int(parent.EnergyType.FIGHTING)
        and data.energyType == int(parent.EnergyType.WATER)
        and data.basic is True
        and data.stage1 is False
        and data.stage2 is False
        and data.ex is False
        and data.megaEx is False
        and data.tera is False
        and data.aceSpec is False
        and data.evolvesFrom is None
        and _one_skill(data, *ARTICUNO_SKILL)
        and data.attacks == [583]
        and attack is not None
        and attack.name == "Dark Frost"
        and attack.text
        == "If this Pokémon has any Team Rocket’s Energy attached, this attack does 60 more damage."
        and attack.damage == 60
        and attack.energies
        == [int(parent.EnergyType.WATER), 0, 0]
    )


def _alakazam_metadata_is_exact(parent: Any) -> bool:
    data = parent.card_table.get(ALAKAZAM)
    attack = _attack_is_exact(parent, POWERFUL_HAND)
    return (
        data is not None
        and data.cardId == ALAKAZAM
        and data.name == "Alakazam"
        and data.cardType == parent.CardType.POKEMON
        and data.retreatCost == 1
        and data.hp == 140
        and data.weakness == int(parent.EnergyType.DARKNESS)
        and data.resistance == int(parent.EnergyType.FIGHTING)
        and data.energyType == int(parent.EnergyType.PSYCHIC)
        and data.basic is False
        and data.stage1 is False
        and data.stage2 is True
        and data.ex is False
        and data.megaEx is False
        and data.tera is False
        and data.aceSpec is False
        and data.evolvesFrom == "Kadabra"
        and tuple((skill.name, skill.text) for skill in data.skills)
        == tuple(_SAFE_POKEMON_SKILLS[ALAKAZAM])
        and data.attacks == [POWERFUL_HAND]
        and attack is not None
        and attack.name == "Powerful Hand"
        and attack.text == POWERFUL_HAND_TEXT
        and attack.damage == 0
        and attack.energies == [int(parent.EnergyType.PSYCHIC)]
    )


def _hammer_metadata_is_exact(parent: Any) -> bool:
    data = parent.card_table.get(ENHANCED_HAMMER)
    return (
        _nonpokemon_shell(
            parent,
            data,
            ENHANCED_HAMMER,
            "Enhanced Hammer",
            parent.CardType.ITEM,
            int(parent.EnergyType.COLORLESS),
        )
        and _one_skill(data, "Enhanced Hammer", HAMMER_TEXT)
    )


def _pokemon_skills_are_classified(parent: Any, pokemon: Any) -> bool:
    data = parent.card_table.get(pokemon.id)
    if data is None or not isinstance(data.skills, list):
        return False
    actual = {(skill.name, skill.text) for skill in data.skills}
    if pokemon.id == ARTICUNO:
        return actual == {ARTICUNO_SKILL}
    if not actual:
        return True
    return actual == _SAFE_POKEMON_SKILLS.get(pokemon.id, set())


def _visible_effects_are_exact(parent: Any, state: Any) -> bool:
    for player in state.players:
        for pokemon in list(player.active) + list(player.bench):
            if not _pokemon_skills_are_classified(parent, pokemon):
                return False
            # No attached Tool effect is classified by this narrow rule.
            if pokemon.tools:
                return False
            if _energy_parts(parent, pokemon) is None:
                return False
    if not isinstance(state.stadium, list) or len(state.stadium) > 1:
        return False
    if not state.stadium:
        return True
    stadium = state.stadium[0]
    data = parent.card_table.get(stadium.id)
    return (
        _card_row(stadium) is not None
        and stadium.id == 1264
        and _nonpokemon_shell(
            parent,
            data,
            1264,
            "Battle Cage",
            parent.CardType.STADIUM,
            int(parent.EnergyType.COLORLESS),
        )
        and _one_skill(
            data,
            "Battle Cage",
            "Prevent all damage counters from being placed on Benched Pokémon "
            "(both yours and your opponent’s) by effects of attacks and Abilities "
            "from the opponent’s Pokémon. (Damage from attacks is still taken.)",
        )
    )


def _rows(parent: Any, cards: Any, owner: int | None):
    if not isinstance(cards, list):
        return None
    result = []
    for card in cards:
        row = _card_row(card, owner)
        if row is None or parent.card_table.get(row[0]) is None:
            return None
        result.append(row)
    return tuple(result) if len({row[1] for row in result}) == len(result) else None


def _pokemon_fingerprint(parent: Any, pokemon: Any):
    parts = _energy_parts(parent, pokemon)
    if parts is None:
        return None
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        pokemon.appearThisTurn,
        getattr(pokemon, "playerIndex", None),
        tuple(pokemon.energies),
        tuple(row for row, _ in parts),
        tuple(_card_row(card) for card in pokemon.tools),
        tuple(_card_row(card) for card in pokemon.preEvolution),
    )


def _snapshot(parent: Any, obs: Any):
    state = obs.current
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or len(state.players) != 2
        or not _is_int(state.turn)
        or state.turn <= 0
        or not _is_int(state.turnActionCount)
        or state.turnActionCount < 0
        or state.result != -1
        or state.looking is not None
        or any(
            type(value) is not bool
            for value in (
                state.supporterPlayed,
                state.stadiumPlayed,
                state.energyAttached,
                state.retreated,
            )
        )
    ):
        return None
    owner = state.yourIndex
    mine = state.players[owner]
    board = []
    visible_serials = []
    for player_owner, player in enumerate(state.players):
        if (
            len(player.active) != 1
            or not isinstance(player.bench, list)
            or not _is_int(player.deckCount)
            or player.deckCount < 0
            or not _is_int(player.handCount)
            or player.handCount < 0
            or not _is_int(player.benchMax)
            or player.benchMax < len(player.bench)
            or any(
                type(value) is not bool
                for value in (
                    player.poisoned,
                    player.burned,
                    player.asleep,
                    player.paralyzed,
                    player.confused,
                )
            )
        ):
            return None
        for area, pokemon_rows in (("active", player.active), ("bench", player.bench)):
            for index, pokemon in enumerate(pokemon_rows):
                if not _stack_is_exact(parent, pokemon, player_owner):
                    return None
                fingerprint = _pokemon_fingerprint(parent, pokemon)
                if fingerprint is None:
                    return None
                board.append((player_owner, area, index, fingerprint))
                visible_serials.extend(
                    [
                        pokemon.serial,
                        *(card.serial for card in pokemon.preEvolution),
                        *(card.serial for card in pokemon.energyCards),
                        *(card.serial for card in pokemon.tools),
                    ]
                )
    if not isinstance(mine.hand, list) or mine.handCount != len(mine.hand):
        return None
    own_hand = _rows(parent, mine.hand, owner)
    discards = tuple(
        _rows(parent, player.discard, player_owner)
        for player_owner, player in enumerate(state.players)
    )
    stadium = _rows(parent, state.stadium, None)
    if own_hand is None or stadium is None or any(row is None for row in discards):
        return None
    visible_serials.extend(row[1] for row in own_hand)
    for rows in discards:
        visible_serials.extend(row[1] for row in rows)
    visible_serials.extend(row[1] for row in stadium)
    if len(visible_serials) != len(set(visible_serials)):
        return None
    if not _visible_effects_are_exact(parent, state):
        return None
    status = lambda player: (
        player.poisoned,
        player.burned,
        player.asleep,
        player.paralyzed,
        player.confused,
    )
    return {
        "owner": owner,
        "turn": state.turn,
        "action_count": state.turnActionCount,
        "flags": (
            state.supporterPlayed,
            state.stadiumPlayed,
            state.energyAttached,
            state.retreated,
        ),
        "own_hand": own_hand,
        "discards": discards,
        "stadium": stadium,
        "board": tuple(board),
        "decks": tuple(player.deckCount for player in state.players),
        "hands": tuple(player.handCount for player in state.players),
        "prizes": tuple(len(player.prize) for player in state.players),
        "bench_max": tuple(player.benchMax for player in state.players),
        "statuses": tuple(status(player) for player in state.players),
    }


def _main_envelope(parent: Any, obs: Any) -> bool:
    select = obs.select
    return (
        select.context == parent.SelectContext.MAIN
        and int(select.type) == 0
        and select.minCount == 1
        and select.maxCount == 1
        and getattr(select, "remainDamageCounter", None) == 0
        and getattr(select, "remainEnergyCost", None) == 0
        and getattr(select, "deck", None) is None
        and select.contextCard is None
        and select.effect is None
    )


def _status_unlocked(player: Any) -> bool:
    values = (
        player.poisoned,
        player.burned,
        player.asleep,
        player.paralyzed,
        player.confused,
    )
    return all(type(value) is bool for value in values) and not any(values[2:])


def _can_pay(parent: Any, available: tuple[int, ...], required: Any):
    try:
        costs = tuple(int(unit) for unit in (required or ()))
    except (TypeError, ValueError):
        return None
    valid = {int(value) for value in parent.EnergyType}
    if any(unit not in valid for unit in costs) or any(unit not in valid for unit in available):
        return None
    pool = list(available)
    colorless = int(parent.EnergyType.COLORLESS)
    rainbow = int(parent.EnergyType.RAINBOW)
    team_rocket = int(parent.EnergyType.TEAM_ROCKET)
    for need in (unit for unit in costs if unit != colorless):
        choices = []
        for index, unit in enumerate(pool):
            if unit == need:
                rank = 0
            elif unit == rainbow:
                rank = 1
            elif team_rocket == unit and need in (
                int(parent.EnergyType.PSYCHIC),
                int(parent.EnergyType.DARKNESS),
            ):
                rank = 2
            else:
                continue
            choices.append((rank, index))
        if not choices:
            return False
        _, chosen = min(choices)
        pool.pop(chosen)
    return len(pool) >= sum(unit == colorless for unit in costs)


def _attacks_all_unpaid(parent: Any, pokemon: Any, available: tuple[int, ...]) -> bool:
    data = parent.card_table.get(pokemon.id)
    if data is None or not isinstance(data.attacks, list) or not data.attacks:
        return False
    for attack_id in data.attacks:
        attack = _attack_is_exact(parent, attack_id)
        if attack is None or _can_pay(parent, available, attack.energies) is not False:
            return False
    return True


def _parent_snapshot_hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(repr(snapshot).encode("utf-8")).hexdigest().upper()


def _hammer_options(parent: Any, obs: Any):
    api = _api()
    owner = obs.current.yourIndex
    hand = obs.current.players[owner].hand
    rows = []
    seen = set()
    for option_index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.PLAY:
            continue
        index = getattr(option, "index", None)
        if not _is_int(index) or not 0 <= index < len(hand):
            return None
        card = hand[index]
        if card.id != ENHANCED_HAMMER:
            continue
        if (
            not api._option_is_exact(
                parent, option, parent.OptionType.PLAY, owner, index=index
            )
            or _card_row(card, owner) is None
        ):
            return None
        key = runtime_model.stable_option_key(parent, obs, option)
        if key is None or card.serial in seen:
            return None
        seen.add(card.serial)
        rows.append((card.serial, option_index, key, card))
    if not rows:
        return ()
    center_total = min(row[0] for row in rows) + max(row[0] for row in rows)
    ranked = []
    for serial, option_index, key, card in rows:
        selection_key = (
            "enhanced_hammer",
            abs(2 * serial - center_total),
            -serial,
            card.id,
            owner,
        )
        ranked.append((selection_key, serial, option_index, key, card))
    return tuple(sorted(ranked))


def _special_energy_rows(parent: Any, state: Any, opponent: int):
    rows = []
    for area, pokemon_rows in (
        ("active", state.players[opponent].active),
        ("bench", state.players[opponent].bench),
    ):
        for pokemon_index, pokemon in enumerate(pokemon_rows):
            parts = _energy_parts(parent, pokemon)
            if parts is None:
                return None
            for energy_index, (row, units) in enumerate(parts):
                data = parent.card_table.get(row[0])
                if data is not None and data.cardType == parent.CardType.SPECIAL_ENERGY:
                    rows.append(
                        (area, pokemon_index, pokemon.serial, energy_index, row, units)
                    )
    return tuple(rows)


def certificate(
    parent: Any,
    obs: Any,
    snap: Any,
    parent_action: list[int],
    parent_pre: dict[str, Any],
    parent_post: dict[str, Any],
):
    api = _api()
    state = obs.current
    owner = state.yourIndex
    opponent = 1 - owner
    mine = state.players[owner]
    theirs = state.players[opponent]
    snapshot = _snapshot(parent, obs)
    powerful = [
        index
        for index, option in enumerate(obs.select.option)
        if api._option_is_exact(
            parent,
            option,
            parent.OptionType.ATTACK,
            owner,
            attackId=POWERFUL_HAND,
        )
    ]
    if (
        snapshot is None
        or not _main_envelope(parent, obs)
        or not api._options_are_unambiguous(parent, obs)
        or powerful != parent_action
        or len(powerful) != 1
        or core.INTEGRATED_TRANSACTION is not None
        or core.parent_owner_active(parent_pre)
        or core.parent_owner_active(parent_post)
        or not _alakazam_metadata_is_exact(parent)
        or not _articuno_metadata_is_exact(parent)
        or not _hammer_metadata_is_exact(parent)
        or not _status_unlocked(mine)
        or len(mine.active) != 1
        or len(theirs.active) != 1
    ):
        return None
    attacker = mine.active[0]
    target = theirs.active[0]
    target_data = parent.card_table.get(target.id)
    attacker_parts = _energy_parts(parent, attacker)
    attacker_units = (
        tuple(unit for _, units in attacker_parts for unit in units)
        if attacker_parts is not None
        else None
    )
    attack = parent.attack_table.get(POWERFUL_HAND)
    if (
        attacker.id != ALAKAZAM
        or not _stack_is_exact(parent, attacker, owner)
        or attacker_units is None
        or _can_pay(parent, attacker_units, attack.energies) is not True
        or target_data is None
        or target_data.cardType != parent.CardType.POKEMON
        or not target_data.name.startswith("Team Rocket's ")
        or target_data.basic is not True
        or target_data.stage1 is not False
        or target_data.stage2 is not False
        or target_data.evolvesFrom is not None
        or target.preEvolution
        or not _stack_is_exact(parent, target, opponent)
        or attack.damage != 0
        or attack.text != POWERFUL_HAND_TEXT
    ):
        return None
    articuno_rows = []
    for area, pokemon_rows in (("active", theirs.active), ("bench", theirs.bench)):
        for index, pokemon in enumerate(pokemon_rows):
            if pokemon.id == ARTICUNO:
                fingerprint = _pokemon_fingerprint(parent, pokemon)
                if fingerprint is None:
                    return None
                articuno_rows.append((area, index, pokemon.serial, fingerprint))
    if not articuno_rows:
        return None
    hammer_rows = _hammer_options(parent, obs)
    special_rows = _special_energy_rows(parent, state, opponent)
    if not hammer_rows or special_rows is None or len(special_rows) != 1:
        return None
    hammer_selection_key, _, hammer_index, hammer_key, hammer = hammer_rows[0]
    area, pokemon_index, pokemon_serial, energy_index, energy_row, energy_units = special_rows[0]
    target_parts = _energy_parts(parent, target)
    if (
        area != "active"
        or pokemon_index != 0
        or pokemon_serial != target.serial
        or energy_row[0] != TEAM_ROCKET_ENERGY
        or _team_rocket_energy_units(parent, energy_row[0], target_data) != energy_units
        or target_parts is None
    ):
        return None
    remaining_units = tuple(
        unit
        for row, units in target_parts
        if row[1] != energy_row[1]
        for unit in units
    )
    printed_attacks = _printed_attack_rows(parent, target)
    if printed_attacks is None or not _attacks_all_unpaid(parent, target, remaining_units):
        return None
    target_fingerprint = _pokemon_fingerprint(parent, target)
    if target_fingerprint is None:
        return None
    parent_powerful_key = runtime_model.stable_option_key(
        parent, obs, obs.select.option[powerful[0]]
    )
    if parent_powerful_key is None:
        return None
    target_semantic_key = (
        "special_energy",
        opponent,
        int(parent.AreaType.ACTIVE),
        target.serial,
        energy_row,
        tuple(energy_units),
    )
    data = {
        "owner": owner,
        "opponent": opponent,
        "turn": state.turn,
        "start_action_count": state.turnActionCount,
        "start_snapshot": snapshot,
        "initial_snapshot_hash": snap.sha256,
        "duplicate_key": snap.sha256,
        "parent_pre_snapshot": copy.deepcopy(parent_pre),
        "parent_pre_snapshot_hash": _parent_snapshot_hash(parent_pre),
        "parent_post_snapshot_hash": _parent_snapshot_hash(parent_post),
        "parent_powerful_key": parent_powerful_key,
        "hammer_row": _card_row(hammer, owner),
        "hammer_option_key": hammer_key,
        "hammer_selection_key": hammer_selection_key,
        "energy_row": energy_row,
        "energy_units": tuple(energy_units),
        "remaining_units": remaining_units,
        "target_semantic_key": target_semantic_key,
        "expected_end_semantic_key": (int(parent.OptionType.END), owner),
        "attacker_serial": attacker.serial,
        "attacker_fingerprint": _pokemon_fingerprint(parent, attacker),
        "target_id": target.id,
        "target_serial": target.serial,
        "target_fingerprint": target_fingerprint,
        "articuno_rows": tuple(articuno_rows),
        "printed_attacks": printed_attacks,
    }
    return data, [hammer_index]


def build_plan(
    parent: Any,
    obs: Any,
    snap: Any,
    parent_action: list[int],
    data: dict[str, Any],
    action: list[int],
):
    line = model.lineage_key(
        obs.current.players[data["owner"]].active[0], data["owner"]
    )
    ledger = ResourceLedger()
    if line is not None:
        ledger = ledger.assign_role(line, BaseRole.H0)
        ledger = (
            None
            if ledger is None
            else ledger.reserve(
                f"card:{data['hammer_row'][1]}",
                BaseRole.H0,
                "deny protected Active's unique Special Energy",
            )
        )
    if line is None or ledger is None:
        return None
    plan = core._make_plan(
        parent,
        obs,
        snap.sha256,
        parent_action,
        KIND,
        action,
        stage="select_special_energy",
        ledger=ledger,
        H0=line,
        aborts=(
            "Hammer selection context or stable Energy key becomes stale",
            "frozen Active, Articuno, Energy, or public board changes",
            "post-Hammer printed attack denial is no longer exact",
            "unique END is unavailable",
            "higher-precedence parent owner appears",
        ),
        metadata={
            "attacker_serial": data["attacker_serial"],
            "target_serial": data["target_serial"],
            "articuno_serial": data["articuno_rows"][0][2],
            "hammer_serial": data["hammer_row"][1],
            "energy_serial": data["energy_row"][1],
            "intended_attack": POWERFUL_HAND,
        },
    )
    transaction = {
        "kind": KIND,
        "stage": "select_special_energy",
        "plan": plan,
        "data": data,
    }
    return plan, action, {"transaction": transaction}


def _set_stage(transaction: dict[str, Any], stage: str) -> None:
    transaction["stage"] = stage
    transaction["plan"] = replace(transaction["plan"], expected_stage=stage)


def _log_is_exact(log: Any, log_type: int, expected: dict[str, Any]) -> bool:
    if int(getattr(log, "type", -1)) != log_type:
        return False
    values = vars(log)
    allowed = {"type", *expected}
    return not any(values.get(key) != value for key, value in expected.items()) and all(
        key in allowed or value is None for key, value in values.items()
    )


def _expected_without(rows: tuple, serial: int):
    result = tuple(row for row in rows if row[1] != serial)
    return result if len(result) + 1 == len(rows) else None


def _base_snapshot_matches(
    actual: dict[str, Any],
    start: dict[str, Any],
    *,
    action_delta: int,
) -> bool:
    fixed = (
        "owner",
        "turn",
        "flags",
        "stadium",
        "decks",
        "prizes",
        "bench_max",
        "statuses",
    )
    return (
        actual["action_count"] == start["action_count"] + action_delta
        and all(actual[key] == start[key] for key in fixed)
    )


def _select_energy_action(parent: Any, obs: Any, data: dict[str, Any]):
    api = _api()
    state = obs.current
    select = obs.select
    start = data["start_snapshot"]
    current = _snapshot(parent, obs)
    expected_hand = _expected_without(start["own_hand"], data["hammer_row"][1])
    if (
        current is None
        or not _alakazam_metadata_is_exact(parent)
        or not _articuno_metadata_is_exact(parent)
        or not _hammer_metadata_is_exact(parent)
        or expected_hand is None
        or state.yourIndex != data["owner"]
        or state.turn != data["turn"]
        or select.context != parent.SelectContext.DISCARD_ENERGY
        or int(select.type) != 4
        or select.minCount != 1
        or select.maxCount != 1
        or getattr(select, "remainDamageCounter", None) != 0
        or getattr(select, "remainEnergyCost", None) != 1
        or getattr(select, "deck", None) is not None
        or select.contextCard is not None
        or _card_row(select.effect, data["owner"]) != data["hammer_row"]
        or not _base_snapshot_matches(current, start, action_delta=1)
        or current["own_hand"] != expected_hand
        or current["hands"][data["owner"]] != start["hands"][data["owner"]] - 1
        or current["hands"][data["opponent"]] != start["hands"][data["opponent"]]
        or current["discards"] != start["discards"]
        or current["board"] != start["board"]
        or len(obs.logs) != 1
        or not _log_is_exact(
            obs.logs[0],
            10,
            {
                "playerIndex": data["owner"],
                "cardId": ENHANCED_HAMMER,
                "serial": data["hammer_row"][1],
            },
        )
        or not api._options_are_unambiguous(parent, obs)
    ):
        return None
    target = state.players[data["opponent"]].active[0]
    if (
        target.serial != data["target_serial"]
        or _pokemon_fingerprint(parent, target) != data["target_fingerprint"]
        or _printed_attack_rows(parent, target) != data["printed_attacks"]
    ):
        return None
    matches = []
    for option_index, option in enumerate(select.option):
        if option.type != parent.OptionType.ENERGY:
            continue
        energy_index = getattr(option, "energyIndex", None)
        if not _is_int(energy_index) or not 0 <= energy_index < len(target.energyCards):
            return None
        attached = target.energyCards[energy_index]
        key = runtime_model.stable_option_key(parent, obs, option)
        if (
            _card_row(attached, data["opponent"]) == data["energy_row"]
            and api._option_is_exact(
                parent,
                option,
                parent.OptionType.ENERGY,
                data["opponent"],
                area=parent.AreaType.ACTIVE,
                index=0,
                energyIndex=energy_index,
                count=len(data["energy_units"]),
            )
            and key is not None
            and key[-1] == data["energy_row"][1]
        ):
            matches.append((repr(key), option_index, key))
    if len(matches) != 1:
        return None
    _, option_index, key = matches[0]
    data["target_option_key"] = key
    return [option_index]


def _project_target_without_energy(
    parent: Any, fingerprint: tuple, energy_serial: int, energy_units: tuple[int, ...]
):
    rows = list(fingerprint[7])
    matches = [index for index, row in enumerate(rows) if row[1] == energy_serial]
    if len(matches) != 1:
        return None
    rows.pop(matches[0])
    observed = list(fingerprint[6])
    units = list(energy_units)
    found = None
    for start in range(len(observed) - len(units) + 1):
        if observed[start : start + len(units)] == units:
            if found is not None:
                return None
            found = start
    if found is None:
        return None
    del observed[found : found + len(units)]
    result = list(fingerprint)
    result[6] = tuple(observed)
    result[7] = tuple(rows)
    return tuple(result)


def _verify_and_end_action(parent: Any, obs: Any, data: dict[str, Any]):
    api = _api()
    state = obs.current
    start = data["start_snapshot"]
    current = _snapshot(parent, obs)
    expected_hand = _expected_without(start["own_hand"], data["hammer_row"][1])
    expected_target = _project_target_without_energy(
        parent,
        data["target_fingerprint"],
        data["energy_row"][1],
        data["energy_units"],
    )
    expected_board = []
    for owner, area, index, fingerprint in start["board"]:
        if owner == data["opponent"] and area == "active" and index == 0:
            fingerprint = expected_target
        expected_board.append((owner, area, index, fingerprint))
    discards = list(start["discards"])
    own_discard = discards[data["owner"]] + (data["hammer_row"],)
    opponent_discard = discards[data["opponent"]] + (data["energy_row"],)
    discards[data["owner"]] = own_discard
    discards[data["opponent"]] = opponent_discard
    if (
        current is None
        or not _alakazam_metadata_is_exact(parent)
        or not _articuno_metadata_is_exact(parent)
        or not _hammer_metadata_is_exact(parent)
        or expected_hand is None
        or expected_target is None
        or state.yourIndex != data["owner"]
        or state.turn != data["turn"]
        or not _main_envelope(parent, obs)
        or not _base_snapshot_matches(current, start, action_delta=2)
        or current["own_hand"] != expected_hand
        or current["hands"][data["owner"]] != start["hands"][data["owner"]] - 1
        or current["hands"][data["opponent"]] != start["hands"][data["opponent"]]
        or current["discards"] != tuple(discards)
        or current["board"] != tuple(expected_board)
        or len(obs.logs) != 1
        or not _log_is_exact(
            obs.logs[0],
            6,
            {
                "playerIndex": data["opponent"],
                "cardId": data["energy_row"][0],
                "serial": data["energy_row"][1],
                "fromArea": parent.AreaType.ENERGY,
                "toArea": parent.AreaType.DISCARD,
            },
        )
        or not api._options_are_unambiguous(parent, obs)
    ):
        return None
    target = state.players[data["opponent"]].active[0]
    parts = _energy_parts(parent, target)
    available = (
        tuple(unit for _, units in parts for unit in units) if parts is not None else None
    )
    articuno_rows = []
    theirs = state.players[data["opponent"]]
    for area, pokemon_rows in (("active", theirs.active), ("bench", theirs.bench)):
        for index, pokemon in enumerate(pokemon_rows):
            if pokemon.id == ARTICUNO:
                articuno_rows.append(
                    (area, index, pokemon.serial, _pokemon_fingerprint(parent, pokemon))
                )
    if (
        target.serial != data["target_serial"]
        or _pokemon_fingerprint(parent, target) != expected_target
        or _printed_attack_rows(parent, target) != data["printed_attacks"]
        or available != data["remaining_units"]
        or not _attacks_all_unpaid(parent, target, available)
        or tuple(articuno_rows) != data["articuno_rows"]
        or any(card.serial == data["energy_row"][1] for card in target.energyCards)
        or any(card.serial == data["hammer_row"][1] for card in state.players[data["owner"]].hand)
    ):
        return None
    ends = []
    for option_index, option in enumerate(obs.select.option):
        if api._option_is_exact(
            parent, option, parent.OptionType.END, data["owner"]
        ):
            key = runtime_model.stable_option_key(parent, obs, option)
            if key is None:
                return None
            ends.append((repr(key), option_index, key))
    if len(ends) != 1:
        return None
    _, option_index, key = ends[0]
    data["end_option_key"] = key
    return [option_index]


def advance(parent: Any, obs: Any, transaction: dict[str, Any]):
    api = _api()
    data = transaction["data"]
    stage = transaction["stage"]
    if api._parent_owner_now(parent):
        return "abort", None, "HIGHER_PRECEDENCE_PARENT_OWNER"
    if stage == "select_special_energy":
        action = _select_energy_action(parent, obs, data)
        if action is None:
            return "abort", None, "HAMMER_SELECTION_OR_FROZEN_STATE_STALE"
        snap = core.public_snapshot(parent, obs)
        if snap is None:
            return "abort", None, "HAMMER_SELECTION_SNAPSHOT_INCOMPLETE"
        data["select_snapshot_hash"] = snap.sha256
        _set_stage(transaction, "verify_and_end")
        return "override", action, "FROZEN_UNIQUE_SPECIAL_ENERGY"
    if stage == "verify_and_end":
        action = _verify_and_end_action(parent, obs, data)
        if action is None:
            return "abort", None, "HAMMER_RESOLUTION_OR_END_STALE"
        snap = core.public_snapshot(parent, obs)
        if snap is None:
            return "abort", None, "POST_HAMMER_SNAPSHOT_INCOMPLETE"
        data["end_snapshot_hash"] = snap.sha256
        data["end_return_action"] = tuple(action)
        _set_stage(transaction, "end_returned")
        return "override", action, "UNIQUE_END_AFTER_CERTIFIED_ATTACK_DENIAL"
    return "abort", None, "UNKNOWN_ARTICUNO_GUARD_STAGE"


def finalize_return(action: list[int]) -> None:
    """Clear the one-shot latch after the verified END has been returned.

    The duplicate cache remains intact, so a repeated identical callback is
    rebound without another cumulative-parent call while no transaction state
    survives across the opponent turn.
    """

    transaction = core.INTEGRATED_TRANSACTION
    if (
        transaction is not None
        and transaction.get("kind") == KIND
        and transaction.get("stage") == "end_returned"
        and tuple(action) == tuple(transaction["data"].get("end_return_action") or ())
    ):
        core.INTEGRATED_TRANSACTION = None
