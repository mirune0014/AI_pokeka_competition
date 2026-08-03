import os
import sys
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, Observation, SelectContext, OptionType, Card, Pokemon, all_attack, all_card_data, to_observation_class

"""
Alakazam Deck
This deck uses Alakazam's Powerful Hand attack (20 damage per card in hand)
with a draw engine built around Kadabra/Alakazam Psychic Draw, Dudunsparce's
Run Away Draw, and Fezandipiti ex's Flip the Script.
"""

# Load deck.csv in the dataset
file_path = "deck.csv"
if not os.path.exists(file_path):
    file_path = "/kaggle_simulations/agent/" + file_path
with open(file_path, "r") as file:
    csv = file.read().split("\n")
my_deck = []
for i in range(60):
    my_deck.append(int(csv[i]))

# Fetch card metadata database and create an ID-to-Card lookup table
all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}
attack_table = {attack.attackId: attack for attack in all_attack()}

# Decklist
Abra = 741              # x4
Kadabra = 742            # x4
Alakazam = 743           # x3
Dunsparce = 305          # x3
Dudunsparce = 66         # x2
Fezandipiti_ex = 140     # x1
Genesect = 142           # x1
Psyduck = 858            # x1
Shaymin = 343            # x1
Rare_Candy = 1079        # x3
Enhanced_Hammer = 1081   # x3
Buddy_Buddy_Poffin = 1086  # x4
Night_Stretcher = 1097   # x1
Sacred_Ash = 1129        # x1
Poke_Pad = 1152          # x4
Lucky_Helmet = 1156      # x3
Boss_Orders = 1182       # x2
Hilda = 1225             # x4
Dawn = 1231              # x4
Battle_Cage = 1264       # x4
Team_Rockets_Watchtower = 1256
Basic_Psychic_Energy = 5   # x2
Telepath_Psychic_Energy = 19  # x4
Enriching_Energy = 13    # x1  (ACE SPEC)

# Opponent card IDs to watch for
Duskull = 131
Solrock = 676
Riolu = 677
Staryu = 1030
Slowpoke_IDs = (162, 327)
Froakie_IDs = (33, 945)
Wellspring_Mask_Ogerpon_ex = 108
N_Darumaka = 257
Dreepy = 119
Drakloak = 120
Dragapult_ex = 121
Mega_Starmie_ex = 1031
Mist_Energy = 11
Rock_Fighting_Energy = 20
Basic_Fire_Energy = 2
Basic_Water_Energy = 3

# Attack IDs
ATTACK_TELEPORTATION = 1070   # Abra: 10 dmg, cost {P}
ATTACK_SUPER_PSY_BOLT = 1071  # Kadabra: 30 dmg, cost {P}
ATTACK_POWERFUL_HAND = 1072   # Alakazam: 20 per card in hand, cost {P}

# Card ID sets
ABRA_LINE = {Abra, Kadabra, Alakazam}
DUNSPARCE_LINE = {Dunsparce, Dudunsparce}
PSYCHIC_ENERGY_IDS = {Basic_Psychic_Energy, Telepath_Psychic_Energy}
RESERVE_BASIC_PRIORITY = (Abra, Dunsparce, Shaymin, Psyduck, Genesect, Fezandipiti_ex)
POKE_PAD_BASIC_PRIORITY = (Abra, Dunsparce, Shaymin, Psyduck, Genesect)
SINGLETON_LOSS_THREATS = {Solrock, Riolu, Duskull, Staryu}

pre_turn = 0
ability_used_dudunsparce = False
ability_used_fezandipiti = False
_hilda_source_latch = {}
_enriching_reserve_latch = {}
_fez_ko_bridge_latch = {}
_active_psychic_ko_latch = {}
_stranded_retreat_ko_latch = {}
_kadabra_resource_first_latch = {}
_reserve_terminal_win_latch = {}
_last_decision_signature = None
_last_decision_action = None


def get_card(obs: Observation, area: AreaType, index: int, player_index: int) -> Pokemon | Card | None:
    ps = obs.current.players[player_index]
    match area:
        case AreaType.DECK:
            return obs.select.deck[index]
        case AreaType.HAND:
            return ps.hand[index]
        case AreaType.DISCARD:
            return ps.discard[index]
        case AreaType.ACTIVE:
            return ps.active[index]
        case AreaType.BENCH:
            return ps.bench[index]
        case AreaType.PRIZE:
            return ps.prize[index]
        case AreaType.STADIUM:
            return obs.current.stadium[index]
        case AreaType.LOOKING:
            return obs.current.looking[index]
        case _:
            return None


def _clear_hilda_source_latch() -> None:
    _hilda_source_latch.clear()


def _clear_enriching_reserve_latch() -> None:
    _enriching_reserve_latch.clear()


def _clear_fez_ko_bridge_latch() -> None:
    _fez_ko_bridge_latch.clear()


def _clear_active_psychic_ko_latch() -> None:
    _active_psychic_ko_latch.clear()


def _clear_stranded_retreat_ko_latch() -> None:
    _stranded_retreat_ko_latch.clear()


def _clear_kadabra_resource_first_latch() -> None:
    _kadabra_resource_first_latch.clear()


def _clear_reserve_terminal_win_latch() -> None:
    _reserve_terminal_win_latch.clear()


def _clear_decision_cache() -> None:
    global _last_decision_signature, _last_decision_action
    _last_decision_signature = None
    _last_decision_action = None


def _clear_emergency_state(*, clear_cache: bool = False) -> None:
    _clear_hilda_source_latch()
    _clear_enriching_reserve_latch()
    _clear_fez_ko_bridge_latch()
    _clear_active_psychic_ko_latch()
    _clear_stranded_retreat_ko_latch()
    _clear_kadabra_resource_first_latch()
    _clear_reserve_terminal_win_latch()
    if clear_cache:
        _clear_decision_cache()


def _decision_signature(obs: Observation) -> tuple:
    """Return a public-state signature for idempotent repeated callbacks."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent = theirs.active[0] if theirs.active else None

    option_signature = tuple(
        (
            int(option.type),
            option.number,
            int(option.area) if option.area is not None else None,
            option.index,
            option.playerIndex,
            int(option.inPlayArea) if option.inPlayArea is not None else None,
            option.inPlayIndex,
            option.attackId,
            option.cardId,
            option.serial,
        )
        for option in select.option
    )
    fez_guard_signature = None
    if _fez_ko_bridge_latch:
        fez_guard_signature = (
            state.retreated,
            len(mine.prize),
            len(theirs.prize),
            mine.handCount,
            theirs.handCount,
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in mine.active
                if pokemon is not None
            ),
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in mine.bench
            ),
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in theirs.active
                if pokemon is not None
            ),
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in theirs.bench
            ),
            tuple(_bridge_card_fingerprint(card) for card in mine.discard),
            tuple(_bridge_card_fingerprint(card) for card in state.stadium),
            (
                mine.poisoned,
                mine.burned,
                mine.asleep,
                mine.paralyzed,
                mine.confused,
                theirs.poisoned,
                theirs.burned,
                theirs.asleep,
                theirs.paralyzed,
                theirs.confused,
            ),
        )
    stranded_guard_signature = None
    if _stranded_retreat_ko_latch:
        stranded_guard_signature = (
            state.retreated,
            len(mine.prize),
            len(theirs.prize),
            mine.handCount,
            mine.deckCount,
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in mine.active
                if pokemon is not None
            ),
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in mine.bench
            ),
            tuple(
                _bridge_pokemon_fingerprint(pokemon)
                for pokemon in theirs.active
                if pokemon is not None
            ),
            tuple(_bridge_card_fingerprint(card) for card in mine.discard),
            tuple(_bridge_card_fingerprint(card) for card in state.stadium),
        )
    resource_guard_signature = None
    if _kadabra_resource_first_latch:
        resource_guard_signature = (
            tuple(
                _kadabra_resource_first_latch.get(key)
                for key in (
                    "stage",
                    "turn",
                    "player",
                    "active_serial",
                    "opponent_serial",
                    "basic_serial",
                    "hammer_serial",
                    "target_energy_serial",
                    "deck_count",
                    "own_prizes",
                    "opponent_prizes",
                    "turn_action_count",
                )
            ),
            state.turnActionCount,
            state.energyAttached,
            len(mine.prize),
            len(theirs.prize),
            _reserve_cards_fingerprint(mine.hand),
            _reserve_cards_fingerprint(mine.discard),
            _reserve_cards_fingerprint(theirs.discard),
            None if active is None else _bridge_pokemon_fingerprint(active),
            None if opponent is None else _bridge_pokemon_fingerprint(opponent),
            _reserve_pokemon_rows(mine.bench),
            _reserve_pokemon_rows(theirs.bench),
            _reserve_cards_fingerprint(state.stadium),
            _reserve_status_fingerprint(state),
        )
    terminal_guard_signature = None
    if _reserve_terminal_win_latch:
        terminal_guard_signature = tuple(
            sorted(_reserve_terminal_win_latch.items(), key=lambda item: item[0])
        )
    return (
        state.turn,
        state.turnActionCount,
        my_index,
        int(select.context),
        getattr(select.effect, "id", None),
        getattr(select.effect, "serial", None),
        getattr(select.contextCard, "id", None),
        getattr(select.contextCard, "serial", None),
        mine.deckCount,
        tuple((card.id, card.serial) for card in (mine.hand or [])),
        None if active is None else (active.id, active.serial),
        tuple(
            (card.id, card.serial)
            for card in (active.energyCards if active is not None else [])
        ),
        tuple((card.id, card.serial) for card in mine.bench),
        None if opponent is None else (opponent.id, opponent.serial, opponent.hp),
        state.energyAttached,
        fez_guard_signature,
        stranded_guard_signature,
        resource_guard_signature,
        terminal_guard_signature,
        option_signature,
    )


def _remember_action(signature: tuple, action: list[int]) -> list[int]:
    global _last_decision_signature, _last_decision_action
    _last_decision_signature = signature
    _last_decision_action = tuple(action)
    return list(action)


def _prepare_emergency_state(obs: Observation) -> None:
    """Clear every latch at a game/turn/seat boundary before using it."""
    state = obs.current
    context = obs.select.context
    if (
        state.turn == 0
        or context
        in (
            SelectContext.IS_FIRST,
            SelectContext.MULLIGAN,
            SelectContext.SETUP_ACTIVE_POKEMON,
            SelectContext.SETUP_BENCH_POKEMON,
        )
        or state.result != -1
    ):
        _clear_emergency_state(clear_cache=True)
        return

    for latch, clear in (
        (_hilda_source_latch, _clear_hilda_source_latch),
        (_enriching_reserve_latch, _clear_enriching_reserve_latch),
        (_fez_ko_bridge_latch, _clear_fez_ko_bridge_latch),
        (_active_psychic_ko_latch, _clear_active_psychic_ko_latch),
        (_stranded_retreat_ko_latch, _clear_stranded_retreat_ko_latch),
        (_kadabra_resource_first_latch, _clear_kadabra_resource_first_latch),
        (_reserve_terminal_win_latch, _clear_reserve_terminal_win_latch),
    ):
        if latch and (
            latch.get("turn") != state.turn
            or latch.get("player") != state.yourIndex
        ):
            clear()


def _resolved_selection_cards(
    obs: Observation, my_index: int
) -> list[tuple[int, object, Card | Pokemon]] | None:
    """Resolve a card-only selection; ambiguity or a foreign option fails."""
    select = obs.select
    if not select.option:
        return None
    resolved = []
    for option_index, option in enumerate(select.option):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.DECK
            or option.playerIndex != my_index
        ):
            return None
        card = get_card(obs, option.area, option.index, my_index)
        if card is None:
            return None
        resolved.append((option_index, option, card))
    return resolved


def _all_energy_selection(
    resolved: list[tuple[int, object, Card | Pokemon]] | None,
) -> bool:
    return bool(resolved) and all(
        card_table[card.id].cardType
        in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY)
        for _, _, card in resolved
    )


def _all_evolution_selection(
    resolved: list[tuple[int, object, Card | Pokemon]] | None,
) -> bool:
    return bool(resolved) and all(
        card_table[card.id].cardType == CardType.POKEMON
        and not card_table[card.id].basic
        and (card_table[card.id].stage1 or card_table[card.id].stage2)
        for _, _, card in resolved
    )


def _enriching_is_unspent(my_state) -> bool:
    if any(card.id == Enriching_Energy for card in my_state.discard):
        return False
    for pokemon in list(my_state.active) + list(my_state.bench):
        if pokemon is not None and any(
            card.id == Enriching_Energy for card in pokemon.energyCards
        ):
            return False
    return True


def _lone_dunsparce_energy_choice_certified(
    *,
    context: SelectContext,
    effect_card_id: int | None,
    source_stage: str,
    all_offered_energy: bool,
    enriching_option_count: int,
    turn: int,
    own_prizes: int,
    active_id: int,
    active_energy_count: int,
    bench_count: int,
    hand_ids: set[int],
    opponent_active_id: int,
    deck_count: int,
    enriching_unspent: bool,
    emergency_latch_active: bool,
) -> bool:
    """Pure public certificate for the frozen Hilda Energy branch."""
    return (
        context == SelectContext.TO_HAND
        and effect_card_id == Hilda
        and source_stage == "await_energy"
        and all_offered_energy
        and enriching_option_count == 1
        and turn <= 3
        and own_prizes == 6
        and active_id == Dunsparce
        and active_energy_count == 0
        and bench_count == 0
        and not (set(RESERVE_BASIC_PRIORITY) | {Buddy_Buddy_Poffin, Poke_Pad})
        & hand_ids
        and opponent_active_id in SINGLETON_LOSS_THREATS
        and deck_count - 6 > own_prizes
        and enriching_unspent
        and not emergency_latch_active
    )


def _same_public_emergency_board(
    obs: Observation,
    latch: dict,
    *,
    require_unattached: bool,
) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent = theirs.active[0] if theirs.active else None
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
        or state.turn > 3
        or len(mine.prize) != 6
        or active is None
        or active.id != Dunsparce
        or active.serial != latch.get("active_serial")
        or mine.bench
        or opponent is None
        or opponent.id != latch.get("opponent_id")
        or opponent.serial != latch.get("opponent_serial")
    ):
        return False
    if require_unattached:
        hand_ids = {card.id for card in (mine.hand or [])}
        return (
            not active.energyCards
            and not state.energyAttached
            and not (set(RESERVE_BASIC_PRIORITY) | {Buddy_Buddy_Poffin, Poke_Pad})
            & hand_ids
            and mine.deckCount - 6 > len(mine.prize)
            and _enriching_is_unspent(mine)
        )
    return (
        state.energyAttached
        and any(
            card.id == Enriching_Energy
            and card.serial == latch.get("enriching_serial")
            for card in active.energyCards
        )
    )


def _first_legal_play(
    obs: Observation,
    my_index: int,
    card_ids: tuple[int, ...],
    *,
    required_serial: int | None = None,
) -> tuple[int, Card] | None:
    for card_id in card_ids:
        matches = []
        for option_index, option in enumerate(obs.select.option):
            if option.type != OptionType.PLAY:
                continue
            card = get_card(obs, AreaType.HAND, option.index, my_index)
            if (
                card is not None
                and card.id == card_id
                and (required_serial is None or card.serial == required_serial)
            ):
                matches.append((option_index, card))
        if matches:
            return min(matches, key=lambda item: item[0])
    return None


def _enriching_reserve_overlay(obs: Observation) -> list[int] | None:
    """Advance only the frozen Hilda -> Enriching -> one-reserve latch."""
    state = obs.current
    select = obs.select
    context = select.context
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent = theirs.active[0] if theirs.active else None
    effect_card_id = getattr(select.effect, "id", None)

    if _enriching_reserve_latch:
        latch = _enriching_reserve_latch
        stage = latch.get("stage")

        if stage == "await_attach":
            if context != SelectContext.MAIN or not _same_public_emergency_board(
                obs, latch, require_unattached=True
            ):
                _clear_enriching_reserve_latch()
                return None
            matches = []
            for option_index, option in enumerate(select.option):
                if (
                    option.type != OptionType.ATTACH
                    or option.area != AreaType.HAND
                    or option.inPlayArea != AreaType.ACTIVE
                    or option.inPlayIndex != 0
                ):
                    continue
                energy = get_card(obs, AreaType.HAND, option.index, my_index)
                target = get_card(obs, AreaType.ACTIVE, 0, my_index)
                if (
                    energy is not None
                    and target is not None
                    and energy.id == Enriching_Energy
                    and energy.serial == latch.get("enriching_serial")
                    and target.id == Dunsparce
                    and target.serial == latch.get("active_serial")
                ):
                    matches.append(option_index)
            if len(matches) != 1:
                _clear_enriching_reserve_latch()
                return None
            latch["stage"] = "await_reserve"
            latch["pre_attach_hand"] = len(mine.hand or [])
            latch["pre_attach_deck"] = mine.deckCount
            return [matches[0]]

        if stage == "await_reserve":
            if (
                context != SelectContext.MAIN
                or not _same_public_emergency_board(
                    obs, latch, require_unattached=False
                )
                or mine.deckCount != latch.get("pre_attach_deck") - 4
                or len(mine.hand or []) != latch.get("pre_attach_hand") + 3
            ):
                _clear_enriching_reserve_latch()
                return None

            direct = _first_legal_play(
                obs, my_index, RESERVE_BASIC_PRIORITY
            )
            if direct is not None:
                latch["stage"] = "await_bench_confirmation"
                latch["route"] = "direct"
                return [direct[0]]

            poffin = _first_legal_play(
                obs, my_index, (Buddy_Buddy_Poffin,)
            )
            if poffin is not None:
                latch["stage"] = "await_poffin_bench"
                latch["route"] = "poffin"
                return [poffin[0]]

            poke_pad = _first_legal_play(obs, my_index, (Poke_Pad,))
            if poke_pad is not None:
                latch["stage"] = "await_poke_pad_hand"
                latch["route"] = "poke_pad"
                return [poke_pad[0]]

            _clear_enriching_reserve_latch()
            return None

        if stage == "await_poffin_bench":
            if (
                context != SelectContext.TO_BENCH
                or effect_card_id != Buddy_Buddy_Poffin
                or not _same_public_emergency_board(
                    obs, latch, require_unattached=False
                )
                or select.minCount > 1
                or select.maxCount < 1
            ):
                _clear_enriching_reserve_latch()
                return None
            resolved = _resolved_selection_cards(obs, my_index)
            if resolved is None:
                _clear_enriching_reserve_latch()
                return None
            for card_id in (Abra, Dunsparce):
                choices = [
                    (option_index, card)
                    for option_index, _, card in resolved
                    if card.id == card_id
                ]
                if choices:
                    latch["stage"] = "await_bench_confirmation"
                    latch["selected_reserve_id"] = card_id
                    return [min(choices, key=lambda item: item[0])[0]]
            _clear_enriching_reserve_latch()
            return None

        if stage == "await_poke_pad_hand":
            if (
                context != SelectContext.TO_HAND
                or effect_card_id != Poke_Pad
                or not _same_public_emergency_board(
                    obs, latch, require_unattached=False
                )
                or select.minCount > 1
                or select.maxCount < 1
            ):
                _clear_enriching_reserve_latch()
                return None
            resolved = _resolved_selection_cards(obs, my_index)
            if resolved is None:
                _clear_enriching_reserve_latch()
                return None
            for card_id in POKE_PAD_BASIC_PRIORITY:
                choices = []
                for option_index, _, card in resolved:
                    data = card_table[card.id]
                    if (
                        card.id == card_id
                        and data.cardType == CardType.POKEMON
                        and data.basic
                        and not data.ex
                        and not data.megaEx
                    ):
                        choices.append((option_index, card))
                if choices:
                    option_index, card = min(choices, key=lambda item: item[0])
                    latch["stage"] = "await_poke_pad_play"
                    latch["selected_reserve_id"] = card.id
                    latch["selected_reserve_serial"] = card.serial
                    return [option_index]
            _clear_enriching_reserve_latch()
            return None

        if stage == "await_poke_pad_play":
            if context != SelectContext.MAIN or not _same_public_emergency_board(
                obs, latch, require_unattached=False
            ):
                _clear_enriching_reserve_latch()
                return None
            play = _first_legal_play(
                obs,
                my_index,
                (latch.get("selected_reserve_id"),),
                required_serial=latch.get("selected_reserve_serial"),
            )
            if play is None:
                _clear_enriching_reserve_latch()
                return None
            latch["stage"] = "await_bench_confirmation"
            return [play[0]]

        if stage == "await_bench_confirmation":
            if mine.bench:
                _clear_enriching_reserve_latch()
            else:
                _clear_enriching_reserve_latch()
            return None

        _clear_enriching_reserve_latch()
        return None

    if not _hilda_source_latch:
        return None
    latch = _hilda_source_latch
    if context != SelectContext.TO_HAND or effect_card_id != Hilda:
        _clear_hilda_source_latch()
        return None

    resolved = _resolved_selection_cards(obs, my_index)
    if latch.get("stage") == "await_evolution":
        if not _all_evolution_selection(resolved):
            _clear_hilda_source_latch()
        else:
            latch["stage"] = "await_energy"
        return None

    if latch.get("stage") != "await_energy":
        _clear_hilda_source_latch()
        return None

    enriching = [
        (option_index, card)
        for option_index, _, card in (resolved or [])
        if card.id == Enriching_Energy
    ]
    certified = _lone_dunsparce_energy_choice_certified(
        context=context,
        effect_card_id=effect_card_id,
        source_stage=latch.get("stage", ""),
        all_offered_energy=_all_energy_selection(resolved),
        enriching_option_count=len(enriching),
        turn=state.turn,
        own_prizes=len(mine.prize),
        active_id=active.id if active is not None else -1,
        active_energy_count=len(active.energyCards) if active is not None else -1,
        bench_count=len(mine.bench),
        hand_ids={card.id for card in (mine.hand or [])},
        opponent_active_id=opponent.id if opponent is not None else -1,
        deck_count=mine.deckCount,
        enriching_unspent=_enriching_is_unspent(mine),
        emergency_latch_active=False,
    )
    if (
        not certified
        or active is None
        or active.serial != latch.get("active_serial")
        or opponent is None
        or select.minCount > 1
        or select.maxCount < 1
    ):
        _clear_hilda_source_latch()
        return None

    option_index, enriching_card = enriching[0]
    _enriching_reserve_latch.update(
        stage="await_attach",
        turn=state.turn,
        player=my_index,
        active_serial=active.serial,
        enriching_serial=enriching_card.serial,
        opponent_id=opponent.id,
        opponent_serial=opponent.serial,
    )
    _clear_hilda_source_latch()
    return [option_index]


def prize_count(pokemon: Pokemon) -> int:
    data = card_table[pokemon.id]
    count = 3 if data.megaEx else 2 if data.ex else 1
    for card in pokemon.energyCards:
        if card.id == 12:  # Legacy Energy
            count -= 1
    for card in pokemon.tools:
        if card.id == 1172 and "Lillie" in data.name:
            count -= 1
    return max(0, count)


def count_special_defense_energies(pokemon: Pokemon) -> int:
    cnt = 0
    for ec in pokemon.energyCards:
        if ec.id == Mist_Energy or ec.id == Rock_Fighting_Energy:
            cnt += 1
    return cnt


def _hit_bound_reduced(remaining_hp: int, hand_size: int, draws: int = 3) -> bool:
    """Whether ``draws`` cards strictly reduce Powerful Hand's hit bound."""
    if remaining_hp <= 0 or hand_size <= 0 or draws <= 0:
        return False
    hits_before = (remaining_hp + 20 * hand_size - 1) // (20 * hand_size)
    after_hand = hand_size + draws
    hits_after = (remaining_hp + 20 * after_hand - 1) // (20 * after_hand)
    return hits_before > hits_after


def _run_away_draw_cost_certified(
    remaining_hp: int,
    hand_size: int,
    attached_cards: int,
    target_prizes: int,
    draws: int = 3,
) -> bool:
    """Whether the public source/target cost permits the hit-bound overlay."""
    if remaining_hp <= 0 or hand_size <= 0 or draws <= 0:
        return False
    post_draw_hand = hand_size + draws
    post_draw_hits = (remaining_hp + 20 * post_draw_hand - 1) // (
        20 * post_draw_hand
    )
    cost_requires_immediate_ko = attached_cards > 0 or target_prizes <= 1
    return not cost_requires_immediate_ko or post_draw_hits == 1


def _fragile_bench_prize_clock_guard_certified(
    *,
    context: SelectContext,
    parent_top_type: OptionType,
    parent_top_card_id: int | None,
    active_id: int,
    active_has_psychic: bool,
    has_powerful_hand: bool,
    opponent_prizes: int,
    opponent_active_id: int,
    opponent_energy_ids: set[int],
    own_has_shaymin: bool,
    stadium_id: int,
    bench_ids: set[int],
    hand_has_alakazam: bool,
) -> bool:
    """Certify the public H0 -> exposed Bench Prize -> H1 guard."""
    if (
        context != SelectContext.MAIN
        or parent_top_type != OptionType.PLAY
        or parent_top_card_id != Abra
        or active_id != Alakazam
        or not active_has_psychic
        or not has_powerful_hand
        or opponent_prizes > 3
    ):
        return False

    if opponent_active_id == Mega_Starmie_ex:
        ready_spread = (
            Basic_Water_Energy in opponent_energy_ids and not own_has_shaymin
        )
    elif opponent_active_id == Dragapult_ex:
        ready_spread = (
            Basic_Fire_Energy in opponent_energy_ids
            and bool(PSYCHIC_ENERGY_IDS & opponent_energy_ids)
            and stadium_id != Battle_Cage
        )
    else:
        ready_spread = False

    stage_dominated = (
        Alakazam in bench_ids
        or (Kadabra in bench_ids and hand_has_alakazam)
    )
    return ready_spread and stage_dominated


def _legal_bench_dudunsparce_options(
    obs: Observation, options: list, my_index: int
) -> list[tuple[int, int, int]]:
    """Return legal Bench Dudunsparce options as attachment/index/option keys."""
    candidates = []
    for option_index, option in enumerate(options):
        if option.type != OptionType.ABILITY or option.area != AreaType.BENCH:
            continue
        if option.playerIndex is not None and option.playerIndex != my_index:
            continue
        source = get_card(obs, AreaType.BENCH, option.index, my_index)
        if source is None or source.id != Dudunsparce:
            continue
        attached_cards = len(source.energyCards) + len(source.tools)
        candidates.append((attached_cards, option.index, option_index))
    return sorted(candidates)


def _bridge_card_fingerprint(card: Card) -> tuple:
    return (card.id, card.serial, getattr(card, "playerIndex", None))


def _bridge_pokemon_fingerprint(pokemon: Pokemon) -> tuple:
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        pokemon.appearThisTurn,
        getattr(pokemon, "playerIndex", None),
        tuple(int(energy) for energy in pokemon.energies),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.energyCards),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.tools),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.preEvolution),
    )


def _bridge_pokemon_component_serials(pokemon: Pokemon) -> list[int]:
    return [
        pokemon.serial,
        *(
            card.serial
            for card in (
                list(pokemon.energyCards)
                + list(pokemon.tools)
                + list(pokemon.preEvolution)
            )
        ),
    ]


def _bridge_target_fingerprint(pokemon: Pokemon, player_state) -> tuple:
    return _bridge_pokemon_fingerprint(pokemon) + (
        player_state.poisoned,
        player_state.burned,
        player_state.asleep,
        player_state.paralyzed,
        player_state.confused,
    )


def _bridge_pokemon_is_publicly_complete(
    pokemon: Pokemon | None, expected_player: int | None = None
) -> bool:
    if (
        pokemon is None
        or pokemon.id <= 0
        or pokemon.serial <= 0
        or pokemon.hp <= 0
        or pokemon.maxHp <= 0
        or pokemon.hp > pokemon.maxHp
        or len(pokemon.energies) != len(pokemon.energyCards)
    ):
        return False
    attached = (
        list(pokemon.energyCards)
        + list(pokemon.tools)
        + list(pokemon.preEvolution)
    )
    return all(
        card.id > 0
        and card.serial > 0
        and (
            expected_player is None
            or getattr(card, "playerIndex", None) == expected_player
        )
        for card in attached
    )


def _bridge_public_serials(state) -> tuple[int, ...]:
    """Materialize every serial that is visible in the public state."""
    serials = [card.serial for card in state.stadium]
    for player in state.players:
        serials.extend(card.serial for card in player.discard)
        serials.extend(
            card.serial for card in (player.hand or []) if card is not None
        )
        serials.extend(
            card.serial for card in player.prize if card is not None
        )
        for pokemon in list(player.active) + list(player.bench):
            if pokemon is None:
                continue
            serials.extend(_bridge_pokemon_component_serials(pokemon))
    return tuple(serials)


def _bridge_protected_serials_are_unique(state, serials) -> bool:
    protected = tuple(serials)
    if (
        any(not isinstance(serial, int) or serial <= 0 for serial in protected)
        or len(protected) != len(set(protected))
    ):
        return False
    public_serials = _bridge_public_serials(state)
    return all(public_serials.count(serial) == 1 for serial in protected)


def _bridge_target_commitment_fingerprint(
    state, target: Pokemon, opponent_index: int
) -> tuple | None:
    """Freeze every public card committed underneath/on the KO target."""
    if not _bridge_pokemon_is_publicly_complete(target, opponent_index):
        return None
    groups = (
        tuple(target.preEvolution),
        tuple(target.energyCards),
        tuple(target.tools),
    )
    expected_types = (
        {CardType.POKEMON},
        {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY},
        {CardType.TOOL},
    )
    cards = []
    for group, allowed_types in zip(groups, expected_types):
        for card in group:
            data = card_table.get(card.id)
            if (
                data is None
                or data.cardType not in allowed_types
                or card.id <= 0
                or card.serial <= 0
                or getattr(card, "playerIndex", None) != opponent_index
            ):
                return None
            cards.append(card)
    if not _bridge_protected_serials_are_unique(
        state, (card.serial for card in cards)
    ):
        return None
    return tuple(
        tuple(_bridge_card_fingerprint(card) for card in group)
        for group in groups
    )


def _bridge_lock_text_affects_bench_dudunsparce(
    text: str, area: AreaType | None
) -> bool:
    """Conservatively classify persistent public Ability-loss clauses."""
    normalized = (
        _normalized_skill_text(text)
        .replace("pokémon", "pokemon")
        .replace("’", "'")
    )
    lock_markers = (
        "have no abilities",
        "has no abilities",
        "lose any ability",
        "loses any ability",
    )
    if not any(marker in normalized for marker in lock_markers):
        return False
    if "as long as this pokemon is in the active spot" in normalized:
        if area != AreaType.ACTIVE:
            return False
    if "as long as this pokemon is on your bench" in normalized:
        if area != AreaType.BENCH:
            return False

    # These complete public clauses cannot remove Run Away Draw from a
    # non-Rule-Box Stage-1 Dudunsparce that remains on the Bench.
    known_inapplicable = (
        "pokemon with a rule box",
        "opponent's active pokemon",
        "benched stage 2 pokemon",
        "requires the pokemon using it to knock out itself",
    )
    if any(marker in normalized for marker in known_inapplicable):
        return False
    # Team Rocket's Watchtower is the current exact relevant clause:
    # Colorless Pokemon in play have no Abilities.  Any future unrecognized
    # persistent Ability-loss wording also fails closed here.
    return True


def _bridge_public_ability_lock_present(state) -> bool:
    public_sources = []
    for owner, player in enumerate(state.players):
        for pokemon in player.active:
            if pokemon is not None:
                public_sources.append((pokemon.id, AreaType.ACTIVE, owner))
                public_sources.extend(
                    (tool.id, None, owner) for tool in pokemon.tools
                )
        for pokemon in player.bench:
            public_sources.append((pokemon.id, AreaType.BENCH, owner))
            public_sources.extend(
                (tool.id, None, owner) for tool in pokemon.tools
            )
    public_sources.extend((card.id, None, None) for card in state.stadium)

    for card_id, area, _ in public_sources:
        data = card_table.get(card_id)
        if data is None:
            return True
        if card_id == Team_Rockets_Watchtower:
            return True
        if any(
            _bridge_lock_text_affects_bench_dudunsparce(skill.text, area)
            for skill in (data.skills or [])
        ):
            return True
    return False


def _bridge_dudunsparce_reserve_certificate(
    state,
    mine,
    *,
    player_index: int,
    post_ko_prizes: int,
) -> dict | None:
    """Choose one public next-turn Run Away Draw witness."""
    recovery_margin = mine.deckCount - 4 - post_ko_prizes
    if recovery_margin <= 0 or _bridge_public_ability_lock_present(state):
        return None

    candidates = []
    for bench_index, pokemon in enumerate(mine.bench):
        if (
            pokemon.id != Dudunsparce
            or not _bridge_pokemon_is_publicly_complete(
                pokemon, player_index
            )
            or len(pokemon.preEvolution) != 1
            or pokemon.preEvolution[0].id != Dunsparce
            or card_table.get(pokemon.preEvolution[0].id) is None
            or card_table[pokemon.preEvolution[0].id].cardType
            != CardType.POKEMON
            or getattr(pokemon.preEvolution[0], "playerIndex", None)
            != player_index
            or any(
                card_table.get(card.id) is None
                or card_table[card.id].cardType
                not in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY)
                for card in pokemon.energyCards
            )
            or any(
                card_table.get(card.id) is None
                or card_table[card.id].cardType != CardType.TOOL
                for card in pokemon.tools
            )
            or not _bridge_protected_serials_are_unique(
                state, _bridge_pokemon_component_serials(pokemon)
            )
        ):
            continue
        attached_count = len(pokemon.energyCards) + len(pokemon.tools)
        candidates.append(
            (
                attached_count,
                bench_index,
                pokemon.serial,
                pokemon,
            )
        )
    if not candidates:
        return None
    _, bench_index, _, witness = min(
        candidates, key=lambda row: row[:3]
    )
    return {
        "witness_index": bench_index,
        "witness_serial": witness.serial,
        "witness_fingerprint": _bridge_pokemon_fingerprint(witness),
        "recovery_margin": recovery_margin,
    }


_RETALIATION_GUARD_VERSION = "public_retaliation_guard_v2"


def _bridge_retaliation_normalized_text(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("\xa0", " ")
        .replace("pokﾃｩmon", "pokemon")
        .replace("pokémon", "pokemon")
    )


def _bridge_metadata_skill_fingerprint(data) -> tuple:
    return tuple(
        (skill.name, skill.text) for skill in (data.skills or [])
    )


def _bridge_retaliation_energy_unit(card: Card) -> int | None:
    """Return one exact engine Energy unit, or fail for a variable unit."""
    data = card_table.get(card.id)
    if data is None:
        return None
    if data.cardType == CardType.BASIC_ENERGY:
        unit = int(data.energyType)
        return unit if unit in range(1, 9) and not data.skills else None
    if data.cardType != CardType.SPECIAL_ENERGY or len(data.skills or []) != 1:
        return None

    text = _bridge_retaliation_normalized_text(data.skills[0].text)
    if not text.startswith(
        "as long as this card is attached to a pokemon, it provides"
    ):
        return None
    ambiguous_markers = (
        "provides only 2 energy",
        "provides 2 in any combination",
        "provides {c}{c}{c} energy instead",
        "if this card is attached to a basic pokemon",
        "if this card is attached to a stage 2 pokemon",
    )
    if any(marker in text for marker in ambiguous_markers):
        return None
    if (
        "provides every type of energy but provides only 1 energy at a time"
        in text
    ):
        return int(EnergyType.RAINBOW)

    unit = int(data.energyType)
    token = {
        int(EnergyType.COLORLESS): "{c}",
        int(EnergyType.GRASS): "{g}",
        int(EnergyType.FIRE): "{r}",
        int(EnergyType.WATER): "{w}",
        int(EnergyType.LIGHTNING): "{l}",
        int(EnergyType.PSYCHIC): "{p}",
        int(EnergyType.FIGHTING): "{f}",
        int(EnergyType.DARKNESS): "{d}",
        int(EnergyType.METAL): "{m}",
    }.get(unit)
    if token is None or f"provides {token} energy" not in text:
        return None
    return unit


def _bridge_retaliation_energy_units(pokemon: Pokemon) -> tuple[int, ...] | None:
    """Certify every current attached Energy card against engine units."""
    if len(pokemon.energies) != len(pokemon.energyCards):
        return None
    expected = []
    for card in pokemon.energyCards:
        unit = _bridge_retaliation_energy_unit(card)
        if unit is None:
            return None
        expected.append(unit)
    observed = tuple(int(unit) for unit in pokemon.energies)
    return observed if observed == tuple(expected) else None


def _bridge_retaliation_can_pay(
    energy_units: tuple[int, ...], attack_cost
) -> bool | None:
    """Match the engine's colored-first then Colorless payment semantics."""
    costs = tuple(int(unit) for unit in attack_cost)
    if any(unit not in range(0, 12) for unit in costs):
        return None
    available = list(energy_units)
    colored = [unit for unit in costs if unit != int(EnergyType.COLORLESS)]
    colorless_count = len(costs) - len(colored)
    for required in colored:
        candidates = []
        for index, unit in enumerate(available):
            if unit == required:
                priority = 0
            elif unit == int(EnergyType.RAINBOW):
                priority = 1
            elif (
                unit == int(EnergyType.TEAM_ROCKET)
                and required
                in (int(EnergyType.PSYCHIC), int(EnergyType.DARKNESS))
            ):
                priority = 2
            else:
                continue
            candidates.append((priority, index))
        if not candidates:
            return False
        _, chosen = min(candidates)
        available.pop(chosen)
    return len(available) >= colorless_count


def _bridge_retaliation_skill_is_certified_irrelevant(
    text: str, *, source_kind: str
) -> bool:
    """Accept only public effects whose text proves no immediate damage change."""
    normalized = _bridge_retaliation_normalized_text(text)
    if not normalized:
        return True

    # Activated and on-play Abilities are future policy choices, not static
    # modifiers of a currently ready printed attack.
    if (
        normalized.startswith("once during your turn")
        or normalized.startswith("when you play this pokemon")
    ):
        return True

    # Exact semantic classes whose consequences are already reflected in the
    # public state or happen only after the certified damage is dealt.
    if (
        "is damaged by an attack from your opponent's pokemon" in normalized
        and "draw " in normalized
        and "less damage" not in normalized
        and "prevent" not in normalized
    ):
        return True
    if (
        "gets +" in normalized
        and " hp" in normalized
        and "damage" not in normalized
        and "attack" not in normalized
    ):
        return True
    if (
        "prevent all damage counters from being placed on benched pokemon"
        in normalized
        and "damage from attacks is still taken" in normalized
    ):
        return True
    if "prevent all damage done to your benched pokemon" in normalized:
        return True

    if source_kind == "energy":
        if (
            normalized.startswith(
                "as long as this card is attached to a pokemon, it provides"
            )
            and not any(
                marker in normalized
                for marker in (
                    "more damage",
                    "less damage",
                    "prevent damage",
                    "takes no damage",
                    "weakness",
                    "resistance",
                )
            )
        ):
            return True

    # Any static change to the printed attack set, attack multiplicity, or
    # Energy cost invalidates an attached-Energy-only printed-cost proof.
    attack_payability_markers = (
        "attacks used by",
        "attacks it uses",
        "attack it has",
        "can use any attack",
        "can use the attack",
        "can use attacks",
        "may use an attack",
        "use an attack it has",
        "attack again",
        "attack for {",
        "used by this pokemon costs",
        "that attack costs",
        "costs of attacks",
        "attack costs",
        "cost {c} less",
        "cost {c} more",
        "costs 1 energy less",
        "can't attack",
        "cannot attack",
        "ignore all {c} energy",
        "provides {g}{g}",
        "provides {r}{r}",
        "provides {w}{w}",
        "provides {l}{l}",
        "provides {p}{p}",
        "provides {f}{f}",
        "provides {d}{d}",
        "provides {m}{m}",
        "provides {c}{c}",
    )
    if any(marker in normalized for marker in attack_payability_markers):
        return False

    # A remaining plain search/draw/attach/switch/retreat/Ability-lock clause
    # does not modify printed immediate attack damage.  Any clause mentioning
    # damage, protection, W/R, attack modification, or KO remains unknown.
    dangerous_markers = (
        "damage",
        "weakness",
        "resistance",
        "protect",
        "prevent",
        "attack does",
        "attacks do",
        "attack's damage",
        "can't be knocked out",
        "cannot be knocked out",
    )
    return not any(marker in normalized for marker in dangerous_markers)


def _bridge_retaliation_projected_pokemon_fingerprint(
    pokemon: Pokemon, excluded_energy_serials: tuple[int, ...]
) -> tuple | None:
    """Normalize the already-paid retreat Energy out of the two-ply state."""
    if len(pokemon.energies) != len(pokemon.energyCards):
        return None
    excluded = set(excluded_energy_serials)
    kept = [
        (int(unit), card)
        for unit, card in zip(pokemon.energies, pokemon.energyCards)
        if card.serial not in excluded
    ]
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        pokemon.appearThisTurn,
        getattr(pokemon, "playerIndex", None),
        tuple(unit for unit, _ in kept),
        tuple(_bridge_card_fingerprint(card) for _, card in kept),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.tools),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.preEvolution),
    )


def _bridge_retaliation_visible_effect_fingerprint(
    state,
    *,
    player_index: int,
    primary_serial: int,
    source_serial: int | None,
    payment_serials: tuple[int, ...],
) -> tuple[tuple | None, str | None]:
    """Freeze every projected in-play public source that could alter damage."""
    records = []
    projected = []
    mine = state.players[player_index]
    theirs = state.players[1 - player_index]
    for pokemon in list(mine.active) + list(mine.bench):
        if pokemon is None:
            continue
        role = (
            "primary_active"
            if pokemon.serial == primary_serial
            else "own_projected_bench"
        )
        projected.append((player_index, role, pokemon))
    for pokemon in theirs.bench:
        projected.append((1 - player_index, "opponent_attacker_pool", pokemon))

    seen_projected_serials = []
    for owner, role, pokemon in projected:
        if not _bridge_pokemon_is_publicly_complete(pokemon, owner):
            return None, "incomplete_visible_pokemon"
        data = card_table.get(pokemon.id)
        if data is None or data.cardType != CardType.POKEMON:
            return None, "unknown_visible_pokemon_metadata"
        seen_projected_serials.extend(
            _bridge_pokemon_component_serials(pokemon)
        )
        for card in pokemon.preEvolution:
            card_data = card_table.get(card.id)
            if (
                card_data is None
                or card_data.cardType != CardType.POKEMON
                or card.serial <= 0
                or getattr(card, "playerIndex", None) != owner
            ):
                return None, "unknown_visible_preevolution_metadata"
        excluded = (
            payment_serials if pokemon.serial == source_serial else tuple()
        )
        projected_fingerprint = _bridge_retaliation_projected_pokemon_fingerprint(
            pokemon, excluded
        )
        if projected_fingerprint is None:
            return None, "ambiguous_projected_energy_fingerprint"
        skills = _bridge_metadata_skill_fingerprint(data)
        if not all(
            _bridge_retaliation_skill_is_certified_irrelevant(
                skill.text, source_kind="pokemon"
            )
            for skill in (data.skills or [])
        ):
            return None, "unknown_visible_pokemon_modifier"
        records.append(
            (
                owner,
                role,
                "pokemon",
                pokemon.serial,
                projected_fingerprint,
                skills,
            )
        )

        for kind, cards, allowed_type in (
            ("tool", pokemon.tools, {CardType.TOOL}),
            (
                "energy",
                [
                    card
                    for card in pokemon.energyCards
                    if card.serial not in set(excluded)
                ],
                {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY},
            ),
        ):
            for card in cards:
                card_data = card_table.get(card.id)
                if (
                    card_data is None
                    or card_data.cardType not in allowed_type
                    or card.serial <= 0
                    or getattr(card, "playerIndex", None) != owner
                ):
                    return None, f"unknown_visible_{kind}_metadata"
                if kind == "energy" and _bridge_retaliation_energy_unit(card) is None:
                    return None, "ambiguous_visible_special_energy"
                if not all(
                    _bridge_retaliation_skill_is_certified_irrelevant(
                        skill.text, source_kind=kind
                    )
                    for skill in (card_data.skills or [])
                ):
                    return None, f"unknown_visible_{kind}_modifier"
                records.append(
                    (
                        owner,
                        role,
                        kind,
                        pokemon.serial,
                        _bridge_card_fingerprint(card),
                        _bridge_metadata_skill_fingerprint(card_data),
                    )
                )

    if len(seen_projected_serials) != len(set(seen_projected_serials)):
        return None, "duplicate_visible_component_serial"
    if not _bridge_protected_serials_are_unique(
        state, seen_projected_serials
    ):
        return None, "nonunique_visible_component_serial"

    for stadium in state.stadium:
        data = card_table.get(stadium.id)
        if (
            data is None
            or data.cardType != CardType.STADIUM
            or stadium.serial <= 0
        ):
            return None, "unknown_stadium_metadata"
        if not all(
            _bridge_retaliation_skill_is_certified_irrelevant(
                skill.text, source_kind="stadium"
            )
            for skill in (data.skills or [])
        ):
            return None, "unknown_stadium_modifier"
        records.append(
            (
                None,
                "stadium",
                "stadium",
                stadium.serial,
                _bridge_card_fingerprint(stadium),
                _bridge_metadata_skill_fingerprint(data),
            )
        )
    return tuple(sorted(records, key=repr)), None


def _bridge_retaliation_attack_damage(
    attacker_data, attack, primary_data
) -> tuple[dict | None, str | None]:
    """Certify a printed fixed immediate-damage upper bound."""
    if (
        not isinstance(attack.damage, int)
        or attack.damage < 0
        or attack.attackId <= 0
    ):
        return None, "invalid_attack_damage_metadata"
    text = _bridge_retaliation_normalized_text(attack.text)
    dangerous_markers = (
        "coin",
        "damage counter",
        "more damage",
        "less damage",
        "for each",
        " times ",
        "×",
        "damage equal",
        "number of cards",
        "remaining hp",
        "use it as this attack",
        "use 1 of",
        "choose 1 of",
        "can't use this attack",
        "cannot use this attack",
        "you may use this attack only",
    )
    if any(marker in text for marker in dangerous_markers):
        return None, "variable_coin_hidden_or_conditional_attack"
    if (
        attack.damage == 0
        and "damage" in text
        and "this attack does nothing" not in text
    ):
        return None, "nonfixed_zero_base_damage_effect"

    ignores_wr = any(
        marker in text
        for marker in (
            "this attack's damage isn't affected by weakness or resistance",
            "this attack's damage is not affected by weakness or resistance",
        )
    )
    # A Bench-only parenthetical, such as Shadow Bullet, never disables W/R
    # for the promoted Active Alakazam.
    if "for benched pokemon" in text:
        ignores_wr = False

    damage = int(attack.damage)
    steps = [("printed", damage)]
    attack_type = int(attacker_data.energyType)
    weakness = (
        None if primary_data.weakness is None else int(primary_data.weakness)
    )
    resistance = (
        None
        if primary_data.resistance is None
        else int(primary_data.resistance)
    )
    if not ignores_wr:
        if weakness == attack_type:
            damage *= 2
            steps.append(("weakness_x2", damage))
        if resistance == attack_type:
            damage = max(0, damage - 30)
            steps.append(("resistance_minus_30", damage))
    else:
        steps.append(("ignore_weakness_resistance", damage))
    return {
        "printed_damage": int(attack.damage),
        "attack_type": attack_type,
        "weakness": weakness,
        "resistance": resistance,
        "ignores_weakness_resistance": ignores_wr,
        "damage_steps": tuple(steps),
        "certified_damage": damage,
    }, None


def _bridge_public_retaliation_analysis(
    state,
    primary: Pokemon,
    *,
    player_index: int,
    source_serial: int | None = None,
    payment_serials: tuple[int, ...] = tuple(),
) -> dict:
    """Evaluate every current opponent Bench attack without policy guesses."""
    base = {
        "version": _RETALIATION_GUARD_VERSION,
        "allowed": False,
        "failure_reason": None,
        "primary_serial": getattr(primary, "serial", None),
        "primary_fingerprint": None,
        "primary_remaining_hp": getattr(primary, "hp", None),
        "primary_weakness": None,
        "primary_resistance": None,
        "visible_effect_fingerprint": None,
        "opponent_bench": tuple(),
    }
    if not _bridge_pokemon_is_publicly_complete(primary, player_index):
        return {**base, "failure_reason": "incomplete_primary"}
    primary_data = card_table.get(primary.id)
    if primary_data is None or primary_data.cardType != CardType.POKEMON:
        return {**base, "failure_reason": "unknown_primary_metadata"}
    if not _bridge_protected_serials_are_unique(
        state, _bridge_pokemon_component_serials(primary)
    ):
        return {**base, "failure_reason": "nonunique_primary_serial"}

    base.update(
        primary_fingerprint=_bridge_pokemon_fingerprint(primary),
        primary_remaining_hp=primary.hp,
        primary_weakness=(
            None
            if primary_data.weakness is None
            else int(primary_data.weakness)
        ),
        primary_resistance=(
            None
            if primary_data.resistance is None
            else int(primary_data.resistance)
        ),
    )
    visible_effects, effect_failure = (
        _bridge_retaliation_visible_effect_fingerprint(
            state,
            player_index=player_index,
            primary_serial=primary.serial,
            source_serial=source_serial,
            payment_serials=payment_serials,
        )
    )
    if visible_effects is None:
        return {**base, "failure_reason": effect_failure}
    base["visible_effect_fingerprint"] = visible_effects

    opponent_index = 1 - player_index
    opponent = state.players[opponent_index]
    bench_profiles = []
    for bench_index, attacker in enumerate(opponent.bench):
        if not _bridge_pokemon_is_publicly_complete(attacker, opponent_index):
            return {**base, "failure_reason": "incomplete_opponent_bench"}
        attacker_data = card_table.get(attacker.id)
        if attacker_data is None or attacker_data.cardType != CardType.POKEMON:
            return {**base, "failure_reason": "unknown_opponent_bench_metadata"}
        components = _bridge_pokemon_component_serials(attacker)
        if not _bridge_protected_serials_are_unique(state, components):
            return {**base, "failure_reason": "nonunique_opponent_bench_serial"}
        energy_units = _bridge_retaliation_energy_units(attacker)
        if energy_units is None:
            return {**base, "failure_reason": "ambiguous_special_energy_units"}
        if (
            not isinstance(attacker_data.attacks, list)
            or len(attacker_data.attacks) != len(set(attacker_data.attacks))
        ):
            return {**base, "failure_reason": "ambiguous_printed_attack_list"}

        attack_profiles = []
        for attack_id in attacker_data.attacks:
            attack = attack_table.get(attack_id)
            if attack is None or attack.attackId != attack_id:
                return {**base, "failure_reason": "unknown_printed_attack"}
            cost = tuple(int(unit) for unit in attack.energies)
            payable = _bridge_retaliation_can_pay(energy_units, cost)
            if payable is None:
                return {**base, "failure_reason": "ambiguous_attack_cost"}
            attack_profile = {
                "attack_id": attack_id,
                "name": attack.name,
                "text": attack.text,
                "cost": cost,
                "payable": payable,
                "reason": "insufficient_energy" if not payable else None,
                "damage": None,
            }
            if payable:
                damage, failure = _bridge_retaliation_attack_damage(
                    attacker_data, attack, primary_data
                )
                if damage is None:
                    attack_profile["reason"] = failure
                    attack_profiles.append(tuple(sorted(attack_profile.items())))
                    bench_profiles.append(
                        (
                            bench_index,
                            _bridge_pokemon_fingerprint(attacker),
                            energy_units,
                            tuple(attack_profiles),
                        )
                    )
                    return {
                        **base,
                        "failure_reason": failure,
                        "opponent_bench": tuple(bench_profiles),
                    }
                attack_profile["reason"] = "fixed_damage_certified"
                attack_profile["damage"] = tuple(sorted(damage.items()))
                if damage["certified_damage"] >= primary.hp:
                    attack_profile["reason"] = "ready_return_ko"
                    attack_profiles.append(tuple(sorted(attack_profile.items())))
                    bench_profiles.append(
                        (
                            bench_index,
                            _bridge_pokemon_fingerprint(attacker),
                            energy_units,
                            tuple(attack_profiles),
                        )
                    )
                    return {
                        **base,
                        "failure_reason": "ready_return_ko",
                        "opponent_bench": tuple(bench_profiles),
                    }
            attack_profiles.append(tuple(sorted(attack_profile.items())))
        bench_profiles.append(
            (
                bench_index,
                _bridge_pokemon_fingerprint(attacker),
                energy_units,
                tuple(attack_profiles),
            )
        )

    return {
        **base,
        "allowed": True,
        "failure_reason": None,
        "opponent_bench": tuple(bench_profiles),
    }


def _bridge_public_retaliation_certificate(
    state,
    primary: Pokemon,
    *,
    player_index: int,
    source_serial: int | None = None,
    payment_serials: tuple[int, ...] = tuple(),
) -> dict | None:
    analysis = _bridge_public_retaliation_analysis(
        state,
        primary,
        player_index=player_index,
        source_serial=source_serial,
        payment_serials=payment_serials,
    )
    return analysis if analysis["allowed"] else None


def _bridge_exchange_resilience_certificate(
    state,
    mine,
    target: Pokemon,
    *,
    player_index: int,
    target_prizes: int,
    post_ko_prizes: int,
    continuity: dict,
    primary: Pokemon | None = None,
    source_serial: int | None = None,
    payment_serials: tuple[int, ...] = tuple(),
) -> dict | None:
    """Apply fixed branch precedence to the immediate public exchange."""
    commitment = _bridge_target_commitment_fingerprint(
        state, target, 1 - player_index
    )
    if commitment is None:
        return None
    commitment_count = sum(len(group) for group in commitment)

    common = {
        "target_commitment_fingerprint": commitment,
        "witness_index": None,
        "witness_serial": None,
        "witness_fingerprint": None,
        "recovery_margin": None,
        "retaliation_guard_version": None,
        "retaliation_guard_certificate": None,
    }
    if post_ko_prizes == 0:
        return {"branch": "final_prize", **common}
    if target_prizes >= 2:
        return {"branch": "multi_prize", **common}
    if (
        target_prizes != 1
        or post_ko_prizes <= 0
        or continuity.get("branch") != "known_successor"
        or continuity.get("rank") not in range(4)
    ):
        return None
    if commitment_count >= 1:
        return {"branch": "target_public_commitment", **common}

    reserve = _bridge_dudunsparce_reserve_certificate(
        state,
        mine,
        player_index=player_index,
        post_ko_prizes=post_ko_prizes,
    )
    if reserve is None:
        return None
    if primary is None:
        destination = _bridge_bench_destination(mine, player_index)
        if destination is None:
            return None
        _, primary = destination
    retaliation = _bridge_public_retaliation_certificate(
        state,
        primary,
        player_index=player_index,
        source_serial=source_serial,
        payment_serials=payment_serials,
    )
    if retaliation is None:
        return None
    return {
        "branch": "next_turn_dudunsparce_reserve",
        "target_commitment_fingerprint": commitment,
        **reserve,
        "retaliation_guard_version": _RETALIATION_GUARD_VERSION,
        "retaliation_guard_certificate": retaliation,
    }


def _normalized_skill_text(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("’", "'")
        .replace("\xa0", " ")
        .replace("pokémon", "pokemon")
    )


def _skill_may_change_powerful_hand_damage(text: str) -> bool:
    normalized = _normalized_skill_text(text)
    markers = (
        "prevent all damage",
        "prevent damage",
        "less damage",
        "takes no damage",
        "isn't affected",
        "is not affected",
        "can't be knocked out",
        "cannot be knocked out",
        "damage done to this pokemon",
    )
    if not any(marker in normalized for marker in markers):
        return False
    # Alakazam 743 is non-ex.  This is the exact public Crustle-style
    # prevention clause and is therefore inapplicable rather than unknown.
    if (
        "prevent all damage done to this pokemon by attacks from your opponent's pokemon {ex}"
        in normalized
        and not card_table[Alakazam].ex
    ):
        return False
    # Battle Cage explicitly concerns counters on Benched Pokemon and says
    # direct attack damage is still taken; the frozen target is Active.
    if (
        "benched pokemon" in normalized
        and "damage from attacks is still taken" in normalized
    ):
        return False
    return True


def _powerful_hand_target_is_publicly_clear(state, target: Pokemon) -> bool:
    data = card_table.get(target.id)
    if data is None or data.resistance == EnergyType.PSYCHIC:
        return False

    energy_ids = {card.id for card in target.energyCards}
    if Mist_Energy in energy_ids:
        return False
    if (
        Rock_Fighting_Energy in energy_ids
        and data.energyType == EnergyType.FIGHTING
    ):
        return False

    known_nondefensive_special = {
        12,  # Legacy Energy: handled by prize_count.
        Enriching_Energy,
        Telepath_Psychic_Energy,
        Rock_Fighting_Energy,
    }
    for energy in target.energyCards:
        energy_data = card_table.get(energy.id)
        if energy_data is None:
            return False
        if (
            energy_data.cardType == CardType.SPECIAL_ENERGY
            and energy.id not in known_nondefensive_special
        ):
            return False

    public_effect_cards = [data]
    for tool in target.tools:
        tool_data = card_table.get(tool.id)
        if tool_data is None:
            return False
        public_effect_cards.append(tool_data)
    for stadium in state.stadium:
        if stadium.id <= 0 or stadium.serial <= 0:
            return False
        stadium_data = card_table.get(stadium.id)
        if stadium_data is None:
            return False
        public_effect_cards.append(stadium_data)
    for effect_card in public_effect_cards:
        if any(
            _skill_may_change_powerful_hand_damage(skill.text)
            for skill in (effect_card.skills or [])
        ):
            return False
    return True


def _active_psychic_hand_fingerprint(mine, player_index: int) -> tuple | None:
    """Freeze a fully visible own hand without inferring hidden resources."""
    if mine.hand is None or len(mine.hand) != mine.handCount:
        return None
    fingerprint = []
    for card in mine.hand:
        if (
            card is None
            or card.id <= 0
            or card.serial <= 0
            or card_table.get(card.id) is None
            or getattr(card, "playerIndex", None) != player_index
        ):
            return None
        fingerprint.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in fingerprint}) != len(fingerprint):
        return None
    return tuple(fingerprint)


def _active_psychic_static_fingerprint(pokemon: Pokemon) -> tuple:
    """Fingerprint every public Active field except the attached Energy list."""
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        pokemon.appearThisTurn,
        getattr(pokemon, "playerIndex", None),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.tools),
        tuple(
            _bridge_card_fingerprint(card) for card in pokemon.preEvolution
        ),
    )


def _active_psychic_telepath_text_certified() -> bool:
    """Certify the checked optional Bench-search text of exact card 19."""
    data = card_table.get(Telepath_Psychic_Energy)
    if (
        data is None
        or data.cardType != CardType.SPECIAL_ENERGY
        or data.energyType != EnergyType.PSYCHIC
        or len(data.skills or []) != 1
    ):
        return False
    text = " ".join(_normalized_skill_text(data.skills[0].text).split())
    return text == (
        "as long as this card is attached to a pokemon, it provides {p} "
        "energy. when you attach this card from your hand to a {p} pokemon, "
        "search your deck for up to 2 basic {p} pokemon and put them onto "
        "your bench. then, shuffle your deck."
    )


def _active_psychic_attach_candidates(
    obs: Observation, my_index: int
) -> list[tuple[int, int, int, Card]]:
    """Return exact legal Psychic-to-Active options in the frozen tie order."""
    mine = obs.current.players[my_index]
    candidates = []
    for option_index, option in enumerate(obs.select.option):
        if (
            option.type != OptionType.ATTACH
            or option.area != AreaType.HAND
            or option.inPlayArea != AreaType.ACTIVE
            or option.inPlayIndex != 0
            or option.playerIndex not in (None, my_index)
            or not isinstance(option.index, int)
            or option.index < 0
            or option.index >= len(mine.hand or [])
        ):
            continue
        energy = mine.hand[option.index]
        if (
            energy is None
            or energy.id not in PSYCHIC_ENERGY_IDS
            or energy.serial <= 0
            or getattr(energy, "playerIndex", None) != my_index
        ):
            continue
        priority = 0 if energy.id == Basic_Psychic_Energy else 1
        candidates.append((priority, energy.serial, option_index, energy))
    return sorted(candidates, key=lambda row: row[:3])


def _start_active_psychic_immediate_ko(
    obs: Observation,
) -> list[int] | None:
    """Start one certified attach -> immediate Powerful Hand transaction."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    target = theirs.active[0] if theirs.active else None
    if (
        select.context != SelectContext.MAIN
        or state.turn < 2
        or state.energyAttached
        or _active_psychic_ko_latch
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _stranded_retreat_ko_latch
        or _kadabra_resource_first_latch
        or _reserve_terminal_win_latch
        or active is None
        or active.id != Alakazam
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or any(card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards)
        or target is None
        or not _bridge_pokemon_is_publicly_complete(target, 1 - my_index)
        or target.hp <= 0
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or select.minCount > 1
        or select.maxCount < 1
    ):
        return None

    hand_fingerprint = _active_psychic_hand_fingerprint(mine, my_index)
    candidates = _active_psychic_attach_candidates(obs, my_index)
    if hand_fingerprint is None or not candidates:
        return None
    _, _, option_index, energy = candidates[0]
    if (
        energy.id == Telepath_Psychic_Energy
        and not _active_psychic_telepath_text_certified()
    ):
        return None

    conservative_damage = 20 * (mine.handCount - 1)
    target_prizes = prize_count(target)
    own_prizes = len(mine.prize)
    if (
        own_prizes <= 0
        or target_prizes <= 0
        or conservative_damage < target.hp
    ):
        return None
    post_ko_prizes = max(0, own_prizes - target_prizes)
    if (
        energy.id == Telepath_Psychic_Energy
        and post_ko_prizes > 0
        and mine.deckCount <= post_ko_prizes
    ):
        return None

    protected_serials = [
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(target),
        energy.serial,
    ]
    if not _bridge_protected_serials_are_unique(state, protected_serials):
        return None

    selected_hand_index = obs.select.option[option_index].index
    post_attach_hand = (
        hand_fingerprint[:selected_hand_index]
        + hand_fingerprint[selected_hand_index + 1 :]
    )
    _active_psychic_ko_latch.update(
        stage="await_attack",
        turn=state.turn,
        player=my_index,
        active_serial=active.serial,
        active_static_fingerprint=_active_psychic_static_fingerprint(active),
        active_energy_fingerprints=tuple(
            _bridge_card_fingerprint(card) for card in active.energyCards
        ),
        active_energy_units=tuple(int(energy) for energy in active.energies),
        target_serial=target.serial,
        target_fingerprint=_bridge_target_fingerprint(target, theirs),
        selected_energy_id=energy.id,
        selected_energy_serial=energy.serial,
        selected_energy_fingerprint=_bridge_card_fingerprint(energy),
        post_attach_hand_fingerprint=post_attach_hand,
        own_prize_count=own_prizes,
        target_prizes=target_prizes,
        post_ko_prizes=post_ko_prizes,
        conservative_damage=conservative_damage,
    )
    return [option_index]


def _active_psychic_post_attach_is_same(
    obs: Observation, latch: dict
) -> bool:
    """Revalidate the exact public transaction after the Energy attachment."""
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    target = theirs.active[0] if theirs.active else None
    hand_fingerprint = _active_psychic_hand_fingerprint(mine, my_index)
    selected = latch.get("selected_energy_fingerprint")
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
        or not state.energyAttached
        or active is None
        or active.id != Alakazam
        or active.serial != latch.get("active_serial")
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or _active_psychic_static_fingerprint(active)
        != latch.get("active_static_fingerprint")
        or target is None
        or target.serial != latch.get("target_serial")
        or not _bridge_pokemon_is_publicly_complete(target, 1 - my_index)
        or _bridge_target_fingerprint(target, theirs)
        != latch.get("target_fingerprint")
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or hand_fingerprint != latch.get("post_attach_hand_fingerprint")
        or selected is None
        or selected in hand_fingerprint
        or len(mine.prize) != latch.get("own_prize_count")
        or prize_count(target) != latch.get("target_prizes")
        or 20 * mine.handCount != latch.get("conservative_damage")
        or 20 * mine.handCount < target.hp
    ):
        return False

    current_energy = tuple(
        _bridge_card_fingerprint(card) for card in active.energyCards
    )
    expected_energy = tuple(latch.get("active_energy_fingerprints") or ()) + (
        selected,
    )
    if (
        len(current_energy) != len(expected_energy)
        or sorted(current_energy) != sorted(expected_energy)
        or current_energy.count(selected) != 1
        or sorted(int(energy) for energy in active.energies)
        != sorted(
            tuple(latch.get("active_energy_units") or ())
            + (int(EnergyType.PSYCHIC),)
        )
    ):
        return False

    post_ko_prizes = max(0, len(mine.prize) - prize_count(target))
    if post_ko_prizes != latch.get("post_ko_prizes"):
        return False
    if (
        latch.get("selected_energy_id") == Telepath_Psychic_Energy
        and post_ko_prizes > 0
        and mine.deckCount <= post_ko_prizes
    ):
        return False

    protected_serials = [
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(target),
    ]
    return _bridge_protected_serials_are_unique(state, protected_serials)


def _active_psychic_immediate_ko_overlay(
    obs: Observation,
) -> list[int] | None:
    """Advance only the frozen Active-Alakazam KO transaction."""
    if not _active_psychic_ko_latch:
        return None
    latch = _active_psychic_ko_latch
    select = obs.select
    stage = latch.get("stage")

    if stage == "await_resolution":
        _clear_active_psychic_ko_latch()
        return None
    if stage != "await_attack" or not _active_psychic_post_attach_is_same(
        obs, latch
    ):
        _clear_active_psychic_ko_latch()
        return None

    effect_card_id = getattr(select.effect, "id", None)
    context_card_id = getattr(select.contextCard, "id", None)
    if select.context == SelectContext.TO_BENCH:
        if (
            latch.get("selected_energy_id") != Telepath_Psychic_Energy
            or Telepath_Psychic_Energy
            not in (effect_card_id, context_card_id)
        ):
            _clear_active_psychic_ko_latch()
            return None
        if select.minCount == 0 and select.maxCount >= 0:
            return []
        # A required search is delegated to the inherited legal selector.  The
        # latch remains frozen and the exact attack is rechecked at MAIN.
        return None

    if select.context != SelectContext.MAIN:
        _clear_active_psychic_ko_latch()
        return None
    matches = [
        option_index
        for option_index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK
        and option.attackId == ATTACK_POWERFUL_HAND
    ]
    if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
        _clear_active_psychic_ko_latch()
        return None
    latch["stage"] = "await_resolution"
    return [matches[0]]


def _bridge_retreat_cost_is_publicly_exact(state, active: Pokemon) -> bool:
    """Reject visible effects that can make the printed retreat cost stale."""
    visible_cards = []
    for player in state.players:
        visible_cards.extend(
            pokemon
            for pokemon in list(player.active) + list(player.bench)
            if pokemon is not None
        )
    for pokemon in visible_cards:
        data = card_table.get(pokemon.id)
        if data is None:
            return False
        if any(
            "retreat" in _normalized_skill_text(skill.text)
            for skill in (data.skills or [])
        ):
            return False
        for tool in pokemon.tools:
            tool_data = card_table.get(tool.id)
            if tool_data is None:
                return False
            if any(
                "retreat" in _normalized_skill_text(skill.text)
                for skill in (tool_data.skills or [])
            ):
                return False
    for stadium in state.stadium:
        stadium_data = card_table.get(stadium.id)
        if stadium_data is None:
            return False
        if any(
            "retreat" in _normalized_skill_text(skill.text)
            for skill in (stadium_data.skills or [])
        ):
            return False
    return card_table[active.id].retreatCost > 0


def _bridge_bench_destination(
    mine, player_index: int | None = None
) -> tuple[int, Pokemon] | None:
    candidates = []
    for bench_index, pokemon in enumerate(mine.bench):
        if (
            pokemon.id != Alakazam
            or pokemon.serial <= 0
            or not _bridge_pokemon_is_publicly_complete(
                pokemon, player_index
            )
            or not any(
                card.id in PSYCHIC_ENERGY_IDS for card in pokemon.energyCards
            )
        ):
            continue
        attached_cards = len(pokemon.energyCards) + len(pokemon.tools)
        candidates.append(
            (-attached_cards, bench_index, pokemon.serial, pokemon)
        )
    if not candidates:
        return None
    _, bench_index, _, pokemon = min(candidates, key=lambda row: row[:3])
    return bench_index, pokemon


def _bridge_exact_hand_cards(mine, card_ids: set[int], player_index: int) -> list[Card]:
    """Return deterministic, fully known resource cards from our hand."""
    if mine.hand is None or len(mine.hand) != mine.handCount:
        return []
    cards = [
        card
        for card in mine.hand
        if card.id in card_ids
        and card.serial > 0
        and getattr(card, "playerIndex", None) == player_index
    ]
    return sorted(cards, key=lambda card: (card.id, card.serial))


def _bridge_kadabra_has_complete_evolution_fingerprint(
    pokemon: Pokemon, player_index: int
) -> bool:
    """A public Kadabra must expose the exact Abra it evolved from."""
    return (
        pokemon.id == Kadabra
        and _bridge_pokemon_is_publicly_complete(pokemon, player_index)
        and len(pokemon.preEvolution) == 1
        and pokemon.preEvolution[0].id == Abra
        and pokemon.preEvolution[0].serial > 0
        and getattr(pokemon.preEvolution[0], "playerIndex", None)
        == player_index
    )


def _bridge_continuity_certificate(
    mine,
    *,
    player_index: int,
    primary_serial: int,
    target_prizes: int,
    post_ko_prizes: int,
) -> dict | None:
    """Certify one known-draw-free next-own-turn Powerful Hand path.

    Final- and multi-Prize KOs are terminal/exchange certificates.  Otherwise
    the secondary attacker is chosen by the strategy's fixed rank, then Bench
    index and serial; exact hand resources use card-id then serial tie-breaks.
    """
    if post_ko_prizes == 0:
        return {
            "branch": "final_prize",
            "rank": None,
            "successor_index": None,
            "successor_serial": None,
            "successor_fingerprint": None,
            "hand_alakazam_fingerprint": None,
            "hand_energy_fingerprint": None,
        }
    if target_prizes >= 2:
        return {
            "branch": "two_plus_prize",
            "rank": None,
            "successor_index": None,
            "successor_serial": None,
            "successor_fingerprint": None,
            "hand_alakazam_fingerprint": None,
            "hand_energy_fingerprint": None,
        }

    hand_energies = _bridge_exact_hand_cards(
        mine, set(PSYCHIC_ENERGY_IDS), player_index
    )
    hand_alakazams = _bridge_exact_hand_cards(
        mine, {Alakazam}, player_index
    )
    candidates = []
    for bench_index, pokemon in enumerate(mine.bench):
        if (
            pokemon.serial == primary_serial
            or pokemon.serial <= 0
            or not _bridge_pokemon_is_publicly_complete(
                pokemon, player_index
            )
        ):
            continue
        has_psychic = any(
            card.id in PSYCHIC_ENERGY_IDS for card in pokemon.energyCards
        )
        hand_alakazam = None
        hand_energy = None
        if pokemon.id == Alakazam and has_psychic:
            rank = 0
        elif pokemon.id == Alakazam and not has_psychic and hand_energies:
            rank = 1
            hand_energy = hand_energies[0]
        elif (
            _bridge_kadabra_has_complete_evolution_fingerprint(
                pokemon, player_index
            )
            and has_psychic
            and hand_alakazams
        ):
            rank = 2
            hand_alakazam = hand_alakazams[0]
        elif (
            _bridge_kadabra_has_complete_evolution_fingerprint(
                pokemon, player_index
            )
            and not has_psychic
            and hand_alakazams
            and hand_energies
        ):
            rank = 3
            hand_alakazam = hand_alakazams[0]
            hand_energy = hand_energies[0]
        else:
            continue

        resource_serials = [
            card.serial
            for card in (hand_alakazam, hand_energy)
            if card is not None
        ]
        if (
            pokemon.serial in resource_serials
            or primary_serial in resource_serials
            or len(resource_serials) != len(set(resource_serials))
        ):
            continue
        candidates.append(
            (
                rank,
                bench_index,
                pokemon.serial,
                0 if hand_alakazam is None else hand_alakazam.serial,
                0 if hand_energy is None else hand_energy.id,
                0 if hand_energy is None else hand_energy.serial,
                pokemon,
                hand_alakazam,
                hand_energy,
            )
        )

    if not candidates:
        return None
    (
        rank,
        bench_index,
        _,
        _,
        _,
        _,
        pokemon,
        hand_alakazam,
        hand_energy,
    ) = min(candidates, key=lambda row: row[:6])
    return {
        "branch": "known_successor",
        "rank": rank,
        "successor_index": bench_index,
        "successor_serial": pokemon.serial,
        "successor_fingerprint": _bridge_pokemon_fingerprint(pokemon),
        "hand_alakazam_fingerprint": (
            None
            if hand_alakazam is None
            else _bridge_card_fingerprint(hand_alakazam)
        ),
        "hand_energy_fingerprint": (
            None
            if hand_energy is None
            else _bridge_card_fingerprint(hand_energy)
        ),
    }


def _bridge_find_hand_card(mine, fingerprint: tuple | None) -> Card | None:
    if fingerprint is None:
        return None
    matches = [
        card
        for card in (mine.hand or [])
        if _bridge_card_fingerprint(card) == fingerprint
    ]
    return matches[0] if len(matches) == 1 else None


def _bridge_frozen_continuity_is_same(obs: Observation, latch: dict) -> bool:
    """Recheck every frozen successor/resource through the atomic retreat."""
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    branch = latch.get("continuity_branch")
    if branch in ("final_prize", "two_plus_prize"):
        return (
            latch.get("continuity_rank") is None
            and latch.get("successor_serial") is None
            and latch.get("successor_fingerprint") is None
            and latch.get("hand_alakazam_fingerprint") is None
            and latch.get("hand_energy_fingerprint") is None
        )
    if branch != "known_successor" or latch.get("continuity_rank") not in range(4):
        return False

    successor = _bridge_find_pokemon(mine, latch.get("successor_serial"))
    if (
        successor is None
        or successor[0] != AreaType.BENCH
        or _bridge_pokemon_fingerprint(successor[2])
        != latch.get("successor_fingerprint")
    ):
        return False
    expected_alakazam = latch.get("hand_alakazam_fingerprint")
    expected_energy = latch.get("hand_energy_fingerprint")
    if (
        expected_alakazam is not None
        and _bridge_find_hand_card(mine, expected_alakazam) is None
    ):
        return False
    if (
        expected_energy is not None
        and _bridge_find_hand_card(mine, expected_energy) is None
    ):
        return False

    rank = latch.get("continuity_rank")
    pokemon = successor[2]
    has_psychic = any(
        card.id in PSYCHIC_ENERGY_IDS for card in pokemon.energyCards
    )
    return (
        (rank == 0 and pokemon.id == Alakazam and has_psychic)
        or (
            rank == 1
            and pokemon.id == Alakazam
            and not has_psychic
            and expected_energy is not None
            and expected_alakazam is None
        )
        or (
            rank == 2
            and _bridge_kadabra_has_complete_evolution_fingerprint(
                pokemon, my_index
            )
            and has_psychic
            and expected_alakazam is not None
            and expected_energy is None
        )
        or (
            rank == 3
            and _bridge_kadabra_has_complete_evolution_fingerprint(
                pokemon, my_index
            )
            and not has_psychic
            and expected_alakazam is not None
            and expected_energy is not None
            and expected_alakazam[1] != expected_energy[1]
        )
    )


def _bridge_find_pokemon(mine, serial: int) -> tuple[AreaType, int, Pokemon] | None:
    if mine.active and mine.active[0] is not None and mine.active[0].serial == serial:
        return AreaType.ACTIVE, 0, mine.active[0]
    for index, pokemon in enumerate(mine.bench):
        if pokemon.serial == serial:
            return AreaType.BENCH, index, pokemon
    return None


def _bridge_frozen_exchange_is_same(obs: Observation, latch: dict) -> bool:
    """Recheck the complete exchange branch without trusting Bench indices."""
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if theirs.active else None
    if (
        target is None
        or mine.deckCount != latch.get("exchange_start_deck_count")
        or len(mine.prize) != latch.get("exchange_start_prize_count")
    ):
        return False
    commitment = _bridge_target_commitment_fingerprint(
        state, target, 1 - my_index
    )
    if (
        commitment is None
        or commitment != latch.get("target_commitment_fingerprint")
    ):
        return False
    commitment_count = sum(len(group) for group in commitment)
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    branch = latch.get("exchange_branch")

    empty_witness = (
        latch.get("dudunsparce_witness_serial") is None
        and latch.get("dudunsparce_witness_fingerprint") is None
        and latch.get("dudunsparce_recovery_margin") is None
        and latch.get("retaliation_guard_version") is None
        and latch.get("retaliation_guard_certificate") is None
    )
    if branch == "final_prize":
        return (
            post_ko_prizes == 0
            and latch.get("continuity_branch") == "final_prize"
            and empty_witness
        )
    if branch == "multi_prize":
        return (
            post_ko_prizes > 0
            and target_prizes >= 2
            and latch.get("continuity_branch") == "two_plus_prize"
            and empty_witness
        )
    if (
        target_prizes != 1
        or post_ko_prizes <= 0
        or latch.get("continuity_branch") != "known_successor"
        or latch.get("continuity_rank") not in range(4)
    ):
        return False
    if branch == "target_public_commitment":
        return commitment_count >= 1 and empty_witness
    if branch != "next_turn_dudunsparce_reserve" or commitment_count != 0:
        return False

    witness_serial = latch.get("dudunsparce_witness_serial")
    found = _bridge_find_pokemon(mine, witness_serial)
    if (
        found is None
        or found[0] != AreaType.BENCH
        or _bridge_pokemon_fingerprint(found[2])
        != latch.get("dudunsparce_witness_fingerprint")
    ):
        return False
    reserve = _bridge_dudunsparce_reserve_certificate(
        state,
        mine,
        player_index=my_index,
        post_ko_prizes=post_ko_prizes,
    )
    primary = _bridge_find_pokemon(
        mine, latch.get("destination_serial")
    )
    if primary is None:
        return False
    retaliation = _bridge_public_retaliation_certificate(
        state,
        primary[2],
        player_index=my_index,
        source_serial=latch.get("source_serial"),
        payment_serials=tuple(latch.get("payment_serials") or ()),
    )
    return (
        reserve is not None
        and reserve["witness_serial"] == witness_serial
        and reserve["witness_fingerprint"]
        == latch.get("dudunsparce_witness_fingerprint")
        and reserve["recovery_margin"]
        == latch.get("dudunsparce_recovery_margin")
        and mine.deckCount - 4 > post_ko_prizes
        and latch.get("retaliation_guard_version")
        == _RETALIATION_GUARD_VERSION
        and retaliation is not None
        and retaliation == latch.get("retaliation_guard_certificate")
    )


def _bridge_same_counts_target(obs: Observation, latch: dict) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if theirs.active else None
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
        or mine.hand is None
        or len(mine.hand) != mine.handCount
        or mine.handCount != latch.get("hand_count")
        or mine.deckCount != latch.get("deck_count")
        or len(mine.prize) != latch.get("prize_count")
        or tuple(
            _bridge_card_fingerprint(card) for card in state.stadium
        )
        != latch.get("stadium_fingerprint")
        or target is None
        or not _bridge_pokemon_is_publicly_complete(
            target, 1 - my_index
        )
        or _bridge_target_fingerprint(target, theirs)
        != latch.get("target_fingerprint")
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or 20 * mine.handCount < target.hp
    ):
        return False
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    return (
        target_prizes == latch.get("target_prizes")
        and post_ko_prizes == latch.get("post_ko_prizes")
        and post_ko_prizes >= 0
        and (post_ko_prizes == 0 or mine.deckCount > post_ko_prizes)
    )


def _bridge_retreat_energy_serial(obs: Observation, option) -> int | None:
    state = obs.current
    mine = state.players[state.yourIndex]
    active = mine.active[0] if mine.active else None
    energy_index = option.energyIndex
    if (
        active is None
        or energy_index is None
        or energy_index < 0
        or energy_index >= len(active.energyCards)
    ):
        return None
    return active.energyCards[energy_index].serial


def _stranded_retreat_card_group_fingerprint(
    cards, player_index: int | None = None
) -> tuple | None:
    """Freeze a complete public card group without guessing hidden cards."""
    fingerprint = []
    for card in cards:
        if (
            card is None
            or card.id <= 0
            or card.serial <= 0
            or card_table.get(card.id) is None
            or (
                player_index is not None
                and getattr(card, "playerIndex", None) != player_index
            )
        ):
            return None
        fingerprint.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in fingerprint}) != len(fingerprint):
        return None
    return tuple(fingerprint)


def _stranded_retreat_source_energy_rows(pokemon: Pokemon) -> tuple | None:
    """Pair each exact single-unit Energy card with its public Energy unit."""
    single_unit_ids = {
        Basic_Psychic_Energy,
        Telepath_Psychic_Energy,
        Enriching_Energy,
    }
    if len(pokemon.energyCards) != len(pokemon.energies):
        return None
    rows = []
    for card, energy in zip(pokemon.energyCards, pokemon.energies):
        data = card_table.get(card.id)
        if (
            card.id not in single_unit_ids
            or card.serial <= 0
            or data is None
            or data.cardType
            not in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY)
        ):
            return None
        rows.append((_bridge_card_fingerprint(card), int(energy)))
    if len({row[0][1] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def _stranded_retreat_expected_source_rows(
    latch: dict, paid_count: int
) -> tuple | None:
    payment_serials = tuple(latch.get("payment_serials") or ())
    source_rows = tuple(latch.get("source_energy_rows") or ())
    retreat_cost = latch.get("retreat_cost")
    if (
        not isinstance(retreat_cost, int)
        or retreat_cost <= 0
        or paid_count < 0
        or paid_count > retreat_cost
        or len(payment_serials) != retreat_cost
    ):
        return None
    paid = set(payment_serials[:paid_count])
    return tuple(row for row in source_rows if row[0][1] not in paid)


def _stranded_retreat_discard_is_same(
    mine, latch: dict, paid_count: int
) -> bool:
    initial = tuple(latch.get("initial_discard_fingerprint") or ())
    payments = tuple(latch.get("payment_fingerprints") or ())
    current = _stranded_retreat_card_group_fingerprint(
        mine.discard, latch.get("player")
    )
    if current is None or paid_count < 0 or paid_count > len(payments):
        return False
    expected = initial + payments[:paid_count]
    return len(current) == len(expected) and set(current) == set(expected)


def _stranded_retreat_source_is_same(
    source: Pokemon, mine, latch: dict, paid_count: int
) -> bool:
    expected_rows = _stranded_retreat_expected_source_rows(latch, paid_count)
    current_rows = _stranded_retreat_source_energy_rows(source)
    return (
        expected_rows is not None
        and current_rows == expected_rows
        and _bridge_pokemon_is_publicly_complete(
            source, latch.get("player")
        )
        and _active_psychic_static_fingerprint(source)
        == latch.get("source_static_fingerprint")
        and _stranded_retreat_discard_is_same(mine, latch, paid_count)
    )


def _stranded_retreat_public_commitment_is_same(
    obs: Observation, latch: dict
) -> bool:
    """Recheck every frozen count, target, hand card, and clock guard."""
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if theirs.active else None
    hand_fingerprint = _active_psychic_hand_fingerprint(mine, my_index)
    stadium_fingerprint = _stranded_retreat_card_group_fingerprint(
        state.stadium
    )
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
        or state.energyAttached != latch.get("energy_attached")
        or hand_fingerprint != latch.get("hand_fingerprint")
        or mine.handCount != latch.get("hand_count")
        or mine.deckCount != latch.get("deck_count")
        or len(mine.prize) != latch.get("prize_count")
        or len(theirs.prize) != latch.get("opponent_prize_count")
        or stadium_fingerprint != latch.get("stadium_fingerprint")
        or target is None
        or target.serial != latch.get("target_serial")
        or not _bridge_pokemon_is_publicly_complete(
            target, 1 - my_index
        )
        or _bridge_target_fingerprint(target, theirs)
        != latch.get("target_fingerprint")
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or 20 * mine.handCount != latch.get("powerful_hand_damage")
        or 20 * mine.handCount < target.hp
    ):
        return False
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    return (
        target_prizes == latch.get("target_prizes")
        and post_ko_prizes == latch.get("post_ko_prizes")
        and post_ko_prizes >= 0
        and (post_ko_prizes == 0 or mine.deckCount > post_ko_prizes)
    )


def _stranded_retreat_protected_serials_are_unique(
    state, source: Pokemon, destination: Pokemon, target: Pokemon, latch: dict
) -> bool:
    payment_serials = tuple(latch.get("payment_serials") or ())
    source_components = _bridge_pokemon_component_serials(source)
    protected = [
        *source_components,
        *_bridge_pokemon_component_serials(destination),
        *_bridge_pokemon_component_serials(target),
        *(serial for serial in payment_serials if serial not in source_components),
    ]
    return _bridge_protected_serials_are_unique(state, protected)


def _start_stranded_retreat_ko_bridge(
    obs: Observation,
) -> list[int] | None:
    """Start one exact stranded-Active retreat -> Powerful Hand KO route."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    target = theirs.active[0] if theirs.active else None
    if (
        select.context != SelectContext.MAIN
        or state.turn < 2
        or state.retreated
        or _stranded_retreat_ko_latch
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _kadabra_resource_first_latch
        or _reserve_terminal_win_latch
        or active is None
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or (
            active.id == Alakazam
            and any(
                card.id in PSYCHIC_ENERGY_IDS
                for card in active.energyCards
            )
        )
        or any(option.type == OptionType.ATTACK for option in select.option)
        or target is None
        or not _bridge_pokemon_is_publicly_complete(
            target, 1 - my_index
        )
        or not _bridge_retreat_cost_is_publicly_exact(state, active)
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or select.minCount > 1
        or select.maxCount < 1
    ):
        return None

    retreat_options = [
        option_index
        for option_index, option in enumerate(select.option)
        if option.type == OptionType.RETREAT
    ]
    if not retreat_options:
        return None

    retreat_cost = int(card_table[active.id].retreatCost)
    source_energy_rows = _stranded_retreat_source_energy_rows(active)
    if (
        retreat_cost <= 0
        or source_energy_rows is None
        or len(source_energy_rows) < retreat_cost
    ):
        return None
    attached_serials = tuple(row[0][1] for row in source_energy_rows)
    payment_serials = tuple(sorted(attached_serials)[:retreat_cost])
    payment_fingerprints = tuple(
        next(row[0] for row in source_energy_rows if row[0][1] == serial)
        for serial in payment_serials
    )

    destination = _bridge_bench_destination(mine, my_index)
    if destination is None:
        return None
    destination_index, destination_pokemon = destination

    hand_fingerprint = _active_psychic_hand_fingerprint(mine, my_index)
    initial_discard = _stranded_retreat_card_group_fingerprint(
        mine.discard, my_index
    )
    stadium_fingerprint = _stranded_retreat_card_group_fingerprint(
        state.stadium
    )
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    opponent_prize_count = len(theirs.prize)
    if (
        hand_fingerprint is None
        or initial_discard is None
        or stadium_fingerprint is None
        or 20 * mine.handCount < target.hp
        or target_prizes <= 0
        or post_ko_prizes < 0
        or not (post_ko_prizes < opponent_prize_count)
        or (post_ko_prizes != 0 and mine.deckCount <= post_ko_prizes)
        or not _stranded_retreat_protected_serials_are_unique(
            state, active, destination_pokemon, target,
            {"payment_serials": payment_serials},
        )
    ):
        return None

    _stranded_retreat_ko_latch.update(
        stage="await_payment_or_promotion",
        turn=state.turn,
        player=my_index,
        source_serial=active.serial,
        source_static_fingerprint=_active_psychic_static_fingerprint(active),
        source_energy_rows=source_energy_rows,
        payment_serials=payment_serials,
        payment_fingerprints=payment_fingerprints,
        retreat_cost=retreat_cost,
        destination_start_index=destination_index,
        destination_serial=destination_pokemon.serial,
        destination_fingerprint=_bridge_pokemon_fingerprint(
            destination_pokemon
        ),
        target_serial=target.serial,
        target_fingerprint=_bridge_target_fingerprint(target, theirs),
        target_prizes=target_prizes,
        post_ko_prizes=post_ko_prizes,
        hand_fingerprint=hand_fingerprint,
        hand_count=mine.handCount,
        deck_count=mine.deckCount,
        prize_count=len(mine.prize),
        opponent_prize_count=len(theirs.prize),
        stadium_fingerprint=stadium_fingerprint,
        initial_discard_fingerprint=initial_discard,
        powerful_hand_damage=20 * mine.handCount,
        energy_attached=state.energyAttached,
    )
    return [min(retreat_options)]


def _stranded_retreat_ko_overlay(
    obs: Observation,
) -> list[int] | None:
    """Advance only the frozen retreat payment, promotion, and KO."""
    if not _stranded_retreat_ko_latch:
        return None
    latch = _stranded_retreat_ko_latch
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    stage = latch.get("stage")

    if stage == "await_resolution":
        _clear_stranded_retreat_ko_latch()
        return None
    if not _stranded_retreat_public_commitment_is_same(obs, latch):
        _clear_stranded_retreat_ko_latch()
        return None

    source_found = _bridge_find_pokemon(mine, latch.get("source_serial"))
    destination_found = _bridge_find_pokemon(
        mine, latch.get("destination_serial")
    )
    target = theirs.active[0] if theirs.active else None
    if (
        source_found is None
        or destination_found is None
        or target is None
    ):
        _clear_stranded_retreat_ko_latch()
        return None
    source_area, _, source = source_found
    destination_area, _, destination = destination_found

    if stage == "await_payment_or_promotion":
        retreat_cost = latch.get("retreat_cost")
        payment_serials = tuple(latch.get("payment_serials") or ())
        if select.context == SelectContext.DISCARD_ENERGY:
            remain = select.remainEnergyCost
            if (
                source_area != AreaType.ACTIVE
                or destination_area != AreaType.BENCH
                or _bridge_pokemon_fingerprint(destination)
                != latch.get("destination_fingerprint")
                or not _bridge_retreat_cost_is_publicly_exact(state, source)
                or not isinstance(retreat_cost, int)
                or not isinstance(remain, int)
                or remain <= 0
                or remain > retreat_cost
            ):
                _clear_stranded_retreat_ko_latch()
                return None
            paid_count = retreat_cost - remain
            if not _stranded_retreat_source_is_same(
                source, mine, latch, paid_count
            ):
                _clear_stranded_retreat_ko_latch()
                return None
            expected_serial = payment_serials[paid_count]
            matches = []
            for option_index, option in enumerate(select.option):
                if (
                    option.type != OptionType.ENERGY
                    or option.count not in (None, 1)
                    or option.area not in (None, AreaType.ACTIVE)
                    or option.index not in (None, 0)
                    or option.playerIndex not in (None, my_index)
                    or _bridge_retreat_energy_serial(obs, option)
                    != expected_serial
                ):
                    continue
                matches.append(option_index)
            if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
                _clear_stranded_retreat_ko_latch()
                return None
            return [matches[0]]

        if select.context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
            if (
                source_area != AreaType.ACTIVE
                or destination_area != AreaType.BENCH
                or _bridge_pokemon_fingerprint(destination)
                != latch.get("destination_fingerprint")
                or not _stranded_retreat_source_is_same(
                    source, mine, latch, retreat_cost
                )
                or not _stranded_retreat_protected_serials_are_unique(
                    state, source, destination, target, latch
                )
            ):
                _clear_stranded_retreat_ko_latch()
                return None
            matches = []
            for option_index, option in enumerate(select.option):
                if (
                    option.type != OptionType.CARD
                    or option.area != AreaType.BENCH
                    or option.playerIndex not in (None, my_index)
                ):
                    continue
                pokemon = get_card(
                    obs, AreaType.BENCH, option.index, my_index
                )
                if (
                    pokemon is not None
                    and pokemon.id == Alakazam
                    and pokemon.serial == latch.get("destination_serial")
                    and _bridge_pokemon_fingerprint(pokemon)
                    == latch.get("destination_fingerprint")
                ):
                    matches.append(option_index)
            if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
                _clear_stranded_retreat_ko_latch()
                return None
            latch["stage"] = "await_attack"
            latch["promotion_context"] = int(select.context)
            return [matches[0]]

        _clear_stranded_retreat_ko_latch()
        return None

    if stage == "await_attack":
        retreat_cost = latch.get("retreat_cost")
        if (
            select.context != SelectContext.MAIN
            or not state.retreated
            or destination_area != AreaType.ACTIVE
            or source_area != AreaType.BENCH
            or destination.id != Alakazam
            or destination.serial != latch.get("destination_serial")
            or _bridge_pokemon_fingerprint(destination)
            != latch.get("destination_fingerprint")
            or not any(
                card.id in PSYCHIC_ENERGY_IDS
                for card in destination.energyCards
            )
            or not _stranded_retreat_source_is_same(
                source, mine, latch, retreat_cost
            )
            or not _stranded_retreat_protected_serials_are_unique(
                state, source, destination, target, latch
            )
        ):
            _clear_stranded_retreat_ko_latch()
            return None
        matches = [
            option_index
            for option_index, option in enumerate(select.option)
            if option.type == OptionType.ATTACK
            and option.attackId == ATTACK_POWERFUL_HAND
        ]
        if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
            _clear_stranded_retreat_ko_latch()
            return None
        latch["stage"] = "await_resolution"
        return [matches[0]]

    _clear_stranded_retreat_ko_latch()
    return None


def _start_fez_ko_bridge(
    obs: Observation, parent_top_option
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    target = theirs.active[0] if theirs.active else None
    if (
        select.context != SelectContext.MAIN
        or state.turn < 2
        or state.retreated
        or _fez_ko_bridge_latch
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _kadabra_resource_first_latch
        or _reserve_terminal_win_latch
        or parent_top_option is None
        or parent_top_option.type in (OptionType.ATTACK, OptionType.RETREAT)
        or active is None
        or active.id != Fezandipiti_ex
        or active.serial <= 0
        or target is None
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or not _bridge_pokemon_is_publicly_complete(
            target, 1 - my_index
        )
        or mine.hand is None
        or len(mine.hand) != mine.handCount
        or not _bridge_retreat_cost_is_publicly_exact(state, active)
        or not _powerful_hand_target_is_publicly_clear(state, target)
        or select.minCount > 1
        or select.maxCount < 1
    ):
        return None

    retreat_options = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.RETREAT
    ]
    if not retreat_options:
        return None

    retreat_cost = int(card_table[active.id].retreatCost)
    single_unit_ids = {
        Basic_Psychic_Energy,
        Telepath_Psychic_Energy,
        Enriching_Energy,
    }
    attached = list(active.energyCards)
    attached_serials = [card.serial for card in attached]
    if (
        retreat_cost <= 0
        or len(attached) < retreat_cost
        or len(active.energies) != len(attached)
        or any(card.id not in single_unit_ids for card in attached)
        or any(serial <= 0 for serial in attached_serials)
        or len(set(attached_serials)) != len(attached_serials)
    ):
        return None
    payment_serials = tuple(sorted(attached_serials)[:retreat_cost])

    destination = _bridge_bench_destination(mine, my_index)
    if destination is None:
        return None
    destination_index, destination_pokemon = destination

    if 20 * mine.handCount < target.hp:
        return None
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    if (
        post_ko_prizes < 0
        or (post_ko_prizes != 0 and mine.deckCount <= post_ko_prizes)
    ):
        return None

    continuity = _bridge_continuity_certificate(
        mine,
        player_index=my_index,
        primary_serial=destination_pokemon.serial,
        target_prizes=target_prizes,
        post_ko_prizes=post_ko_prizes,
    )
    if continuity is None:
        return None
    exchange = _bridge_exchange_resilience_certificate(
        state,
        mine,
        target,
        player_index=my_index,
        target_prizes=target_prizes,
        post_ko_prizes=post_ko_prizes,
        continuity=continuity,
        primary=destination_pokemon,
        source_serial=active.serial,
        payment_serials=payment_serials,
    )
    if exchange is None:
        return None

    required_serials = [
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(destination_pokemon),
        *_bridge_pokemon_component_serials(target),
    ]
    successor_serial = continuity.get("successor_serial")
    if successor_serial is not None:
        successor = next(
            (
                pokemon
                for pokemon in mine.bench
                if pokemon.serial == successor_serial
            ),
            None,
        )
        if successor is None:
            return None
        required_serials.extend(
            _bridge_pokemon_component_serials(successor)
        )
    for key in (
        "hand_alakazam_fingerprint",
        "hand_energy_fingerprint",
    ):
        value = continuity.get(key)
        if value is not None:
            required_serials.append(value[1])
    witness_serial = exchange.get("witness_serial")
    if witness_serial is not None:
        witness = next(
            (
                pokemon
                for pokemon in mine.bench
                if pokemon.serial == witness_serial
            ),
            None,
        )
        if witness is None:
            return None
        required_serials.extend(
            _bridge_pokemon_component_serials(witness)
        )
    if exchange.get("retaliation_guard_certificate") is not None:
        for pokemon in theirs.bench:
            required_serials.extend(
                _bridge_pokemon_component_serials(pokemon)
            )
    if (
        any(serial <= 0 for serial in required_serials)
        or len(required_serials) != len(set(required_serials))
    ):
        return None

    _fez_ko_bridge_latch.update(
        stage="await_payment_or_promotion",
        turn=state.turn,
        player=my_index,
        source_serial=active.serial,
        source_static=(
            active.id,
            active.serial,
            active.hp,
            active.maxHp,
            active.appearThisTurn,
            getattr(active, "playerIndex", None),
            tuple(_bridge_card_fingerprint(card) for card in active.tools),
            tuple(_bridge_card_fingerprint(card) for card in active.preEvolution),
        ),
        source_energy_serials=tuple(attached_serials),
        source_energy_fingerprints=tuple(
            _bridge_card_fingerprint(card) for card in attached
        ),
        payment_serials=payment_serials,
        retreat_cost=retreat_cost,
        destination_index=destination_index,
        destination_serial=destination_pokemon.serial,
        destination_fingerprint=_bridge_pokemon_fingerprint(destination_pokemon),
        target_fingerprint=_bridge_target_fingerprint(target, theirs),
        target_prizes=target_prizes,
        post_ko_prizes=post_ko_prizes,
        hand_count=mine.handCount,
        deck_count=mine.deckCount,
        prize_count=len(mine.prize),
        stadium_fingerprint=tuple(
            _bridge_card_fingerprint(card) for card in state.stadium
        ),
        continuity_branch=continuity["branch"],
        continuity_rank=continuity["rank"],
        successor_index=continuity["successor_index"],
        successor_serial=continuity["successor_serial"],
        successor_fingerprint=continuity["successor_fingerprint"],
        hand_alakazam_fingerprint=continuity[
            "hand_alakazam_fingerprint"
        ],
        hand_energy_fingerprint=continuity["hand_energy_fingerprint"],
        exchange_branch=exchange["branch"],
        target_commitment_fingerprint=exchange[
            "target_commitment_fingerprint"
        ],
        dudunsparce_witness_start_index=exchange["witness_index"],
        dudunsparce_witness_serial=exchange["witness_serial"],
        dudunsparce_witness_fingerprint=exchange[
            "witness_fingerprint"
        ],
        exchange_start_deck_count=mine.deckCount,
        exchange_start_prize_count=len(mine.prize),
        dudunsparce_recovery_margin=exchange["recovery_margin"],
        retaliation_guard_version=exchange[
            "retaliation_guard_version"
        ],
        retaliation_guard_certificate=exchange[
            "retaliation_guard_certificate"
        ],
    )
    return [min(retreat_options)]


def _fez_ko_bridge_overlay(obs: Observation) -> list[int] | None:
    if not _fez_ko_bridge_latch:
        return None
    latch = _fez_ko_bridge_latch
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    stage = latch.get("stage")

    if (
        not _bridge_same_counts_target(obs, latch)
        or not _bridge_frozen_continuity_is_same(obs, latch)
        or not _bridge_frozen_exchange_is_same(obs, latch)
    ):
        _clear_fez_ko_bridge_latch()
        return None

    if stage == "await_payment_or_promotion":
        source = _bridge_find_pokemon(mine, latch.get("source_serial"))
        destination = _bridge_find_pokemon(
            mine, latch.get("destination_serial")
        )
        if source is None or destination is None:
            _clear_fez_ko_bridge_latch()
            return None
        source_area, _, source_pokemon = source
        destination_area, _, destination_pokemon = destination
        source_static = (
            source_pokemon.id,
            source_pokemon.serial,
            source_pokemon.hp,
            source_pokemon.maxHp,
            source_pokemon.appearThisTurn,
            getattr(source_pokemon, "playerIndex", None),
            tuple(
                _bridge_card_fingerprint(card) for card in source_pokemon.tools
            ),
            tuple(
                _bridge_card_fingerprint(card)
                for card in source_pokemon.preEvolution
            ),
        )
        if (
            source_static != latch.get("source_static")
            or destination_area != AreaType.BENCH
            or _bridge_pokemon_fingerprint(destination_pokemon)
            != latch.get("destination_fingerprint")
        ):
            _clear_fez_ko_bridge_latch()
            return None

        payment_serials = tuple(latch.get("payment_serials", ()))
        retreat_cost = latch.get("retreat_cost")
        if select.context == SelectContext.DISCARD_ENERGY:
            if source_area != AreaType.ACTIVE:
                _clear_fez_ko_bridge_latch()
                return None
            remain = select.remainEnergyCost
            if (
                not isinstance(remain, int)
                or remain <= 0
                or remain > retreat_cost
            ):
                _clear_fez_ko_bridge_latch()
                return None
            paid_count = retreat_cost - remain
            expected_serial = payment_serials[paid_count]
            current_fingerprints = tuple(
                _bridge_card_fingerprint(card)
                for card in source_pokemon.energyCards
            )
            expected_current = tuple(
                fingerprint
                for fingerprint in latch.get(
                    "source_energy_fingerprints", ()
                )
                if fingerprint[1] not in payment_serials[:paid_count]
            )
            if current_fingerprints != expected_current:
                _clear_fez_ko_bridge_latch()
                return None
            matches = []
            for option_index, option in enumerate(select.option):
                if (
                    option.type != OptionType.ENERGY
                    or option.count not in (None, 1)
                    or option.area not in (None, AreaType.ACTIVE)
                    or option.index not in (None, 0)
                    or option.playerIndex not in (None, my_index)
                    or _bridge_retreat_energy_serial(obs, option)
                    != expected_serial
                ):
                    continue
                matches.append(option_index)
            if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
                _clear_fez_ko_bridge_latch()
                return None
            return [matches[0]]

        if select.context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
            current_energy_fingerprints = tuple(
                _bridge_card_fingerprint(card)
                for card in source_pokemon.energyCards
            )
            expected_remaining = tuple(
                fingerprint
                for fingerprint in latch.get(
                    "source_energy_fingerprints", ()
                )
                if fingerprint[1] not in payment_serials
            )
            discarded_fingerprints = tuple(
                _bridge_card_fingerprint(card) for card in mine.discard
            )
            payment_fingerprints = tuple(
                fingerprint
                for fingerprint in latch.get(
                    "source_energy_fingerprints", ()
                )
                if fingerprint[1] in payment_serials
            )
            if (
                current_energy_fingerprints != expected_remaining
                or any(
                    discarded_fingerprints.count(fingerprint) != 1
                    for fingerprint in payment_fingerprints
                )
            ):
                _clear_fez_ko_bridge_latch()
                return None
            matches = []
            for option_index, option in enumerate(select.option):
                if (
                    option.type != OptionType.CARD
                    or option.area != AreaType.BENCH
                    or option.playerIndex != my_index
                ):
                    continue
                pokemon = get_card(
                    obs, AreaType.BENCH, option.index, my_index
                )
                if (
                    pokemon is not None
                    and pokemon.id == Alakazam
                    and pokemon.serial == latch.get("destination_serial")
                    and _bridge_pokemon_fingerprint(pokemon)
                    == latch.get("destination_fingerprint")
                ):
                    matches.append(option_index)
            if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
                _clear_fez_ko_bridge_latch()
                return None
            latch["stage"] = "await_attack"
            latch["promotion_context"] = int(select.context)
            return [matches[0]]

        _clear_fez_ko_bridge_latch()
        return None

    if stage == "await_attack":
        active = mine.active[0] if mine.active else None
        if (
            select.context != SelectContext.MAIN
            or not state.retreated
            or active is None
            or active.id != Alakazam
            or active.serial != latch.get("destination_serial")
            or _bridge_pokemon_fingerprint(active)
            != latch.get("destination_fingerprint")
            or not any(
                card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards
            )
        ):
            _clear_fez_ko_bridge_latch()
            return None
        matches = [
            option_index
            for option_index, option in enumerate(select.option)
            if option.type == OptionType.ATTACK
            and option.attackId == ATTACK_POWERFUL_HAND
        ]
        if len(matches) != 1 or select.minCount > 1 or select.maxCount < 1:
            _clear_fez_ko_bridge_latch()
            return None
        latch["stage"] = "await_resolution"
        return [matches[0]]

    _clear_fez_ko_bridge_latch()
    return None


def _safe_get_card(
    obs: Observation, area: AreaType, index: int, player_index: int
) -> Pokemon | Card | None:
    """Resolve a public option without allowing a malformed index to escape."""
    try:
        return get_card(obs, area, index, player_index)
    except (IndexError, TypeError):
        return None


def _reserve_status_fingerprint(state) -> tuple:
    return tuple(
        value
        for player in state.players
        for value in (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        )
    )


def _reserve_cards_fingerprint(cards) -> tuple:
    return tuple(_bridge_card_fingerprint(card) for card in (cards or []))


def _reserve_pokemon_rows(pokemon_rows) -> tuple:
    return tuple(_bridge_pokemon_fingerprint(pokemon) for pokemon in pokemon_rows)


def _reserve_remove_serial(rows: tuple, serial: int) -> tuple | None:
    matches = [index for index, row in enumerate(rows) if row[1] == serial]
    if len(matches) != 1:
        return None
    return rows[: matches[0]] + rows[matches[0] + 1 :]


def _reserve_attack_is_payable(pokemon: Pokemon) -> bool | None:
    """Resolve public energy units against every printed attack cost."""
    if not _bridge_pokemon_is_publicly_complete(
        pokemon, getattr(pokemon, "playerIndex", None)
    ):
        return None
    data = card_table.get(pokemon.id)
    if data is None or not data.attacks:
        return False
    try:
        available = [int(energy) for energy in pokemon.energies]
    except (TypeError, ValueError):
        return None
    for attack_id in data.attacks:
        attack = attack_table.get(attack_id)
        if attack is None:
            return None
        remaining = list(available)
        colorless = 0
        payable = True
        for cost in attack.energies:
            cost_value = int(cost)
            if cost_value == int(EnergyType.COLORLESS):
                colorless += 1
                continue
            try:
                remaining.remove(cost_value)
            except ValueError:
                payable = False
                break
        if payable and len(remaining) >= colorless:
            return True
    return False


def _resolve_attached_energy_option(
    obs: Observation, option
) -> tuple[int, AreaType, int, Pokemon, int, Card] | None:
    """Resolve OptionType.ENERGY through Pokemon.energyCards, not units."""
    if (
        option.type != OptionType.ENERGY
        or option.playerIndex not in (0, 1)
        or option.area not in (AreaType.ACTIVE, AreaType.BENCH)
        or option.index is None
        or option.energyIndex is None
        or option.count != 1
    ):
        return None
    pokemon = _safe_get_card(
        obs, option.area, option.index, option.playerIndex
    )
    if not isinstance(pokemon, Pokemon):
        return None
    if option.energyIndex < 0 or option.energyIndex >= len(pokemon.energyCards):
        return None
    energy = pokemon.energyCards[option.energyIndex]
    if energy is None or energy.id <= 0 or energy.serial <= 0:
        return None
    return (
        option.playerIndex,
        option.area,
        option.index,
        pokemon,
        option.energyIndex,
        energy,
    )


def _reserve_run_away_post_count(
    deck_count: int, source: Pokemon
) -> int | None:
    """Checked engine: draw min(3,d), then recycle physical components."""
    owner = getattr(source, "playerIndex", None)
    if (
        source.id != Dudunsparce
        or deck_count <= 0
        or not _bridge_pokemon_is_publicly_complete(source, owner)
    ):
        return None
    groups = (
        (source.preEvolution, {CardType.POKEMON}),
        (
            source.energyCards,
            {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY},
        ),
        (source.tools, {CardType.TOOL}),
    )
    for cards, allowed_types in groups:
        for card in cards:
            data = card_table.get(card.id)
            if data is None or data.cardType not in allowed_types:
                return None
    recycled = (
        1
        + len(source.preEvolution)
        + len(source.energyCards)
        + len(source.tools)
    )
    return deck_count - min(3, deck_count) + recycled


def _reserve_main_post_deck_count(
    obs: Observation, option_index: int
) -> int | None:
    """Return a covered fixed-effect post count; None means deck-neutral."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    if select.context != SelectContext.MAIN:
        return None
    if option_index < 0 or option_index >= len(select.option):
        return None
    option = select.option[option_index]
    deck_count = mine.deckCount

    if option.type == OptionType.ABILITY:
        if option.area not in (AreaType.ACTIVE, AreaType.BENCH):
            return None
        source = _safe_get_card(obs, option.area, option.index, my_index)
        if source is None:
            return -1
        if source.id == Fezandipiti_ex:
            if not _bridge_pokemon_is_publicly_complete(source, my_index):
                return -1
            return deck_count - min(3, deck_count)
        if source.id == Dudunsparce:
            post_count = _reserve_run_away_post_count(deck_count, source)
            return -1 if post_count is None else post_count
        return None

    if option.type == OptionType.ATTACH and option.area == AreaType.HAND:
        energy = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
        if energy is None:
            return -1
        if energy.id == Enriching_Energy:
            return deck_count - min(4, deck_count)
    return None


def _reserve_named_search_action(
    obs: Observation, parent_action: list[int]
) -> list[int] | None:
    """Cap one engine-verified hidden-deck callback at d-1."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    effect_id = getattr(select.effect, "id", None)
    effect_serial = getattr(select.effect, "serial", None)
    effect_player = getattr(select.effect, "playerIndex", None)
    named = {
        Telepath_Psychic_Energy,
        Buddy_Buddy_Poffin,
        Poke_Pad,
        Hilda,
        Dawn,
    }
    if effect_id not in named:
        return None
    if (
        not isinstance(effect_serial, int)
        or effect_serial <= 0
        or effect_player != my_index
        or select.context not in (SelectContext.TO_BENCH, SelectContext.TO_HAND)
        or select.minCount != 0
        or select.maxCount < 0
        or select.deck is None
    ):
        return None

    resolved = []
    for option_index, option in enumerate(select.option):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.DECK
            or option.playerIndex != my_index
            or option.index is None
        ):
            return None
        card = _safe_get_card(obs, AreaType.DECK, option.index, my_index)
        data = card_table.get(card.id) if card is not None else None
        if card is None or data is None:
            return None
        resolved.append((option_index, card, data))

    def all_match(predicate) -> bool:
        return all(predicate(card, data) for _, card, data in resolved)

    if effect_id == Telepath_Psychic_Energy:
        valid = (
            select.context == SelectContext.TO_BENCH
            and select.maxCount <= min(2, mine.benchMax - len(mine.bench))
            and all_match(
                lambda card, data: data.cardType == CardType.POKEMON
                and data.basic
                and data.energyType == EnergyType.PSYCHIC
            )
        )
    elif effect_id == Buddy_Buddy_Poffin:
        valid = (
            select.context == SelectContext.TO_BENCH
            and select.maxCount <= min(2, mine.benchMax - len(mine.bench))
            and all_match(
                lambda card, data: data.cardType == CardType.POKEMON
                and data.basic
                and data.hp <= 70
            )
        )
    elif effect_id == Poke_Pad:
        valid = (
            select.context == SelectContext.TO_HAND
            and select.maxCount <= 1
            and all_match(
                lambda card, data: data.cardType == CardType.POKEMON
                and not data.ex
                and not data.megaEx
            )
        )
    elif effect_id == Hilda:
        evolution_phase = all_match(
            lambda card, data: data.cardType == CardType.POKEMON
            and (data.stage1 or data.stage2)
        )
        energy_phase = all_match(
            lambda card, data: data.cardType
            in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY)
        )
        valid = (
            select.context == SelectContext.TO_HAND
            and select.maxCount <= 1
            and (not resolved or evolution_phase != energy_phase)
        )
    else:
        basic_phase = all_match(
            lambda card, data: data.cardType == CardType.POKEMON and data.basic
        )
        stage1_phase = all_match(
            lambda card, data: data.cardType == CardType.POKEMON and data.stage1
        )
        stage2_phase = all_match(
            lambda card, data: data.cardType == CardType.POKEMON and data.stage2
        )
        valid = (
            select.context == SelectContext.TO_HAND
            and select.maxCount <= 1
            and (
                not resolved
                or sum((basic_phase, stage1_phase, stage2_phase)) == 1
            )
        )
    if not valid:
        return None
    if any(
        not isinstance(index, int)
        or index < 0
        or index >= len(select.option)
        for index in parent_action
    ):
        return None
    safe_max = min(select.maxCount, max(0, mine.deckCount - 1))
    if safe_max < select.minCount:
        return None
    return list(parent_action[:safe_max])


def _reserve_psychic_draw_action(
    obs: Observation, parent_action: list[int]
) -> list[int] | None:
    """Decline only the checked Kadabra/Alakazam Psychic Draw prompt."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    context_card = select.contextCard
    card_id = getattr(context_card, "id", None)
    card_serial = getattr(context_card, "serial", None)
    card_player = getattr(context_card, "playerIndex", None)
    draw_count = {Kadabra: 2, Alakazam: 3}.get(card_id)
    if draw_count is None:
        return None
    yes = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.YES
    ]
    no = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.NO
    ]
    evolved_matches = [
        pokemon
        for pokemon in list(mine.active) + list(mine.bench)
        if pokemon is not None
        and pokemon.id == card_id
        and pokemon.serial == card_serial
    ]
    if (
        select.context != SelectContext.ACTIVATE
        or not isinstance(card_serial, int)
        or card_serial <= 0
        or card_player != my_index
        or select.minCount != 1
        or select.maxCount != 1
        or len(select.option) != 2
        or len(yes) != 1
        or len(no) != 1
        or len(evolved_matches) != 1
        or not _bridge_pokemon_is_publicly_complete(
            evolved_matches[0], my_index
        )
    ):
        return None
    post_count = mine.deckCount - min(draw_count, mine.deckCount)
    return [no[0]] if post_count < 1 else list(parent_action)


def _reserve_terminal_win_certificate(
    obs: Observation, option_index: int
) -> dict | None:
    """No v1 exemption: a complete modifier-aware certificate is unavailable."""
    return None


def _reserve_terminal_win_overlay(obs: Observation) -> list[int] | None:
    """Fail closed if an impossible/stale terminal latch is ever observed."""
    if _reserve_terminal_win_latch:
        _clear_reserve_terminal_win_latch()
    return None


def _apply_mandatory_draw_reserve(
    obs: Observation,
    parent_action: list[int],
    ordered_indices: list[int] | None = None,
) -> list[int]:
    """Post-parent one-card reserve overlay for only verified effect families."""
    named_search = _reserve_named_search_action(obs, parent_action)
    if named_search is not None:
        return named_search
    psychic_draw = _reserve_psychic_draw_action(obs, parent_action)
    if psychic_draw is not None:
        return psychic_draw
    if obs.select.context != SelectContext.MAIN or not parent_action:
        return list(parent_action)

    unsafe = []
    for option_index in parent_action:
        post_count = _reserve_main_post_deck_count(obs, option_index)
        if post_count is not None and post_count < 1:
            unsafe.append(option_index)
    if not unsafe:
        return list(parent_action)

    order = list(ordered_indices or [])
    if not order:
        order = [
            index
            for index, option in enumerate(obs.select.option)
            if option.type == OptionType.END
        ] + list(range(len(obs.select.option)))
    seen = set()
    safe_order = []
    for option_index in order:
        if option_index in seen:
            continue
        seen.add(option_index)
        post_count = _reserve_main_post_deck_count(obs, option_index)
        if post_count is None or post_count >= 1:
            safe_order.append(option_index)
        elif _reserve_terminal_win_certificate(obs, option_index) is not None:
            safe_order.append(option_index)
    if len(safe_order) >= obs.select.minCount:
        return safe_order[: obs.select.maxCount]
    return list(parent_action)


def _option_begins_optional_deck_chain(
    obs: Observation, option_index: int
) -> bool:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    if option_index < 0 or option_index >= len(select.option):
        return False
    option = select.option[option_index]
    if option.type == OptionType.ABILITY:
        source = _safe_get_card(obs, option.area, option.index, my_index)
        return source is not None and source.id in (Fezandipiti_ex, Dudunsparce)
    if option.type in (OptionType.ATTACH, OptionType.EVOLVE):
        card = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
        return card is not None and card.id in (
            Telepath_Psychic_Energy,
            Enriching_Energy,
            Kadabra,
            Alakazam,
        )
    if option.type == OptionType.PLAY:
        card = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
        return card is not None and card.id in (
            Fezandipiti_ex,
            Buddy_Buddy_Poffin,
            Poke_Pad,
            Hilda,
            Dawn,
        )
    return False


def _resource_fingerprint_without_energy(
    pokemon: Pokemon, energy_index: int
) -> tuple | None:
    fingerprint = _bridge_pokemon_fingerprint(pokemon)
    energies = fingerprint[6]
    energy_cards = fingerprint[7]
    if (
        energy_index < 0
        or energy_index >= len(energy_cards)
        or len(energies) != len(energy_cards)
    ):
        return None
    return fingerprint[:6] + (
        energies[:energy_index] + energies[energy_index + 1 :],
        energy_cards[:energy_index] + energy_cards[energy_index + 1 :],
    ) + fingerprint[8:]


def _resource_fingerprint_with_basic(
    pokemon: Pokemon, basic_card: Card
) -> tuple:
    fingerprint = _bridge_pokemon_fingerprint(pokemon)
    return fingerprint[:6] + (
        fingerprint[6] + (int(EnergyType.PSYCHIC),),
        fingerprint[7] + (_bridge_card_fingerprint(basic_card),),
    ) + fingerprint[8:]


def _resource_static_state_is_same(obs: Observation, latch: dict) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    return (
        state.turn == latch.get("turn")
        and my_index == latch.get("player")
        and mine.deckCount == latch.get("deck_count")
        and len(mine.prize) == latch.get("own_prizes")
        and len(theirs.prize) == latch.get("opponent_prizes")
        and _reserve_pokemon_rows(mine.bench) == latch.get("mine_bench")
        and _reserve_pokemon_rows(theirs.bench) == latch.get("opponent_bench")
        and _reserve_cards_fingerprint(state.stadium) == latch.get("stadium")
        and _reserve_status_fingerprint(state) == latch.get("statuses")
    )


def _resource_stage_state_is_same(obs: Observation, latch: dict) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent = theirs.active[0] if theirs.active else None
    if (
        not _resource_static_state_is_same(obs, latch)
        or active is None
        or opponent is None
    ):
        return False
    stage = latch.get("stage")
    if stage == "await_hammer_target":
        return (
            state.turnActionCount == latch.get("turn_action_count") + 1
            and not state.energyAttached
            and _bridge_pokemon_fingerprint(active) == latch.get("active_before")
            and _bridge_pokemon_fingerprint(opponent)
            == latch.get("opponent_before")
            and _reserve_cards_fingerprint(mine.hand)
            == latch.get("hand_after_hammer_play")
            and _reserve_cards_fingerprint(mine.discard)
            == latch.get("mine_discard_before")
            and _reserve_cards_fingerprint(theirs.discard)
            == latch.get("opponent_discard_before")
        )
    if stage == "await_basic_attach":
        return (
            state.turnActionCount == latch.get("turn_action_count") + 2
            and not state.energyAttached
            and _bridge_pokemon_fingerprint(active) == latch.get("active_before")
            and _bridge_pokemon_fingerprint(opponent)
            == latch.get("opponent_after_hammer")
            and _reserve_cards_fingerprint(mine.hand)
            == latch.get("hand_after_hammer_play")
            and _reserve_cards_fingerprint(mine.discard)
            == latch.get("mine_discard_after_hammer")
            and _reserve_cards_fingerprint(theirs.discard)
            == latch.get("opponent_discard_after_hammer")
        )
    if stage == "await_safe_parent":
        return (
            state.turnActionCount == latch.get("turn_action_count") + 3
            and state.energyAttached
            and _bridge_pokemon_fingerprint(active) == latch.get("active_after_basic")
            and _bridge_pokemon_fingerprint(opponent)
            == latch.get("opponent_after_hammer")
            and _reserve_cards_fingerprint(mine.hand)
            == latch.get("hand_after_basic")
            and _reserve_cards_fingerprint(mine.discard)
            == latch.get("mine_discard_after_hammer")
            and _reserve_cards_fingerprint(theirs.discard)
            == latch.get("opponent_discard_after_hammer")
        )
    return False


def _kadabra_resource_first_overlay(obs: Observation) -> list[int] | None:
    if not _kadabra_resource_first_latch:
        return None
    latch = _kadabra_resource_first_latch
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    opponent_index = 1 - my_index
    if not _resource_stage_state_is_same(obs, latch):
        _clear_kadabra_resource_first_latch()
        return None

    if latch.get("stage") == "await_hammer_target":
        if (
            select.context != SelectContext.DISCARD_ENERGY
            or getattr(select.effect, "id", None) != Enhanced_Hammer
            or getattr(select.effect, "serial", None) != latch.get("hammer_serial")
            or getattr(select.effect, "playerIndex", None) != my_index
            or select.minCount != 1
            or select.maxCount != 1
        ):
            _clear_kadabra_resource_first_latch()
            return None
        matches = []
        for option_index, option in enumerate(select.option):
            resolved = _resolve_attached_energy_option(obs, option)
            if resolved is None:
                continue
            owner, area, pokemon_index, pokemon, energy_index, energy = resolved
            if (
                owner == opponent_index
                and area == AreaType.ACTIVE
                and pokemon_index == 0
                and pokemon.serial == latch.get("opponent_serial")
                and energy_index == latch.get("target_energy_index")
                and energy.serial == latch.get("target_energy_serial")
                and energy.id == latch.get("target_energy_id")
            ):
                matches.append(option_index)
        if len(matches) != 1:
            _clear_kadabra_resource_first_latch()
            return None
        latch["stage"] = "await_basic_attach"
        return [matches[0]]

    if latch.get("stage") == "await_basic_attach":
        if select.context != SelectContext.MAIN:
            _clear_kadabra_resource_first_latch()
            return None
        matches = []
        for option_index, option in enumerate(select.option):
            if (
                option.type != OptionType.ATTACH
                or option.area != AreaType.HAND
                or option.inPlayArea != AreaType.ACTIVE
                or option.inPlayIndex != 0
            ):
                continue
            energy = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
            active = _safe_get_card(obs, AreaType.ACTIVE, 0, my_index)
            if (
                energy is not None
                and active is not None
                and energy.id == Basic_Psychic_Energy
                and energy.serial == latch.get("basic_serial")
                and active.id == Kadabra
                and active.serial == latch.get("active_serial")
            ):
                matches.append(option_index)
        if len(matches) != 1:
            _clear_kadabra_resource_first_latch()
            return None
        latch["stage"] = "await_safe_parent"
        return [matches[0]]

    if latch.get("stage") == "await_safe_parent":
        return None
    _clear_kadabra_resource_first_latch()
    return None


def _start_kadabra_resource_first(
    obs: Observation, parent_action: list[int]
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    opponent_index = 1 - my_index
    mine = state.players[my_index]
    theirs = state.players[opponent_index]
    active = mine.active[0] if mine.active else None
    opponent = theirs.active[0] if theirs.active else None
    if (
        select.context != SelectContext.MAIN
        or select.minCount != 1
        or select.maxCount != 1
        or len(parent_action) != 1
        or not _option_begins_optional_deck_chain(obs, parent_action[0])
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _kadabra_resource_first_latch
        or _reserve_terminal_win_latch
        or active is None
        or active.id != Kadabra
        or active.appearThisTurn
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or active.energies
        or active.energyCards
        or mine.poisoned
        or mine.burned
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or opponent is None
        or not _bridge_pokemon_is_publicly_complete(opponent, opponent_index)
        or mine.hand is None
        or len(mine.hand) != mine.handCount
        or state.energyAttached
    ):
        return None

    exhausted = (
        sum(card.id == Alakazam for card in mine.discard)
        == my_deck.count(Alakazam)
        and sum(card.id == Night_Stretcher for card in mine.discard)
        == my_deck.count(Night_Stretcher)
        and sum(card.id == Sacred_Ash for card in mine.discard)
        == my_deck.count(Sacred_Ash)
    )
    if not exhausted:
        return None
    for pokemon in mine.bench:
        ready = _reserve_attack_is_payable(pokemon)
        if ready is not False:
            return None

    basic_matches = []
    hammer_matches = []
    for option_index, option in enumerate(select.option):
        if option.type == OptionType.ATTACH:
            energy = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
            if (
                energy is not None
                and energy.id == Basic_Psychic_Energy
                and option.area == AreaType.HAND
                and option.inPlayArea == AreaType.ACTIVE
                and option.inPlayIndex == 0
            ):
                basic_matches.append((option_index, energy))
        elif option.type == OptionType.PLAY:
            card = _safe_get_card(obs, AreaType.HAND, option.index, my_index)
            if card is not None and card.id == Enhanced_Hammer:
                hammer_matches.append((option_index, card))
    special_targets = []
    for energy_index, energy in enumerate(opponent.energyCards):
        data = card_table.get(energy.id)
        if data is not None and data.cardType == CardType.SPECIAL_ENERGY:
            special_targets.append((energy_index, energy))
    if (
        len(basic_matches) != 1
        or len(hammer_matches) != 1
        or len(special_targets) != 1
    ):
        return None
    basic_option, basic = basic_matches[0]
    hammer_option, hammer = hammer_matches[0]
    target_energy_index, target_energy = special_targets[0]
    if not _bridge_protected_serials_are_unique(
        state,
        (
            active.serial,
            opponent.serial,
            basic.serial,
            hammer.serial,
            target_energy.serial,
        ),
    ):
        return None

    active_before = _bridge_pokemon_fingerprint(active)
    opponent_before = _bridge_pokemon_fingerprint(opponent)
    opponent_after = _resource_fingerprint_without_energy(
        opponent, target_energy_index
    )
    active_after = _resource_fingerprint_with_basic(active, basic)
    hand_before = _reserve_cards_fingerprint(mine.hand)
    hand_after_hammer = _reserve_remove_serial(hand_before, hammer.serial)
    hand_after_basic = (
        _reserve_remove_serial(hand_after_hammer, basic.serial)
        if hand_after_hammer is not None
        else None
    )
    if opponent_after is None or hand_after_hammer is None or hand_after_basic is None:
        return None
    mine_discard_before = _reserve_cards_fingerprint(mine.discard)
    opponent_discard_before = _reserve_cards_fingerprint(theirs.discard)
    hammer_fp = _bridge_card_fingerprint(hammer)
    target_energy_fp = _bridge_card_fingerprint(target_energy)
    _kadabra_resource_first_latch.update(
        stage="await_hammer_target",
        turn=state.turn,
        player=my_index,
        turn_action_count=state.turnActionCount,
        active_serial=active.serial,
        opponent_serial=opponent.serial,
        basic_serial=basic.serial,
        hammer_serial=hammer.serial,
        target_energy_serial=target_energy.serial,
        target_energy_id=target_energy.id,
        target_energy_index=target_energy_index,
        deck_count=mine.deckCount,
        own_prizes=len(mine.prize),
        opponent_prizes=len(theirs.prize),
        active_before=active_before,
        active_after_basic=active_after,
        opponent_before=opponent_before,
        opponent_after_hammer=opponent_after,
        mine_bench=_reserve_pokemon_rows(mine.bench),
        opponent_bench=_reserve_pokemon_rows(theirs.bench),
        stadium=_reserve_cards_fingerprint(state.stadium),
        statuses=_reserve_status_fingerprint(state),
        hand_after_hammer_play=hand_after_hammer,
        hand_after_basic=hand_after_basic,
        mine_discard_before=mine_discard_before,
        mine_discard_after_hammer=mine_discard_before + (hammer_fp,),
        opponent_discard_before=opponent_discard_before,
        opponent_discard_after_hammer=(
            opponent_discard_before + (target_energy_fp,)
        ),
        basic_option=basic_option,
    )
    return [hammer_option]


def agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        _clear_emergency_state(clear_cache=True)
        return my_deck

    state = obs.current
    select = obs.select
    context = select.context
    _prepare_emergency_state(obs)
    decision_signature = _decision_signature(obs)
    if (
        _last_decision_signature == decision_signature
        and _last_decision_action is not None
    ):
        return list(_last_decision_action)

    my_index = state.yourIndex
    my_state = state.players[my_index]
    op_state = state.players[1 - my_index]
    my_prize_count = len(my_state.prize)

    global pre_turn, ability_used_dudunsparce, ability_used_fezandipiti
    if pre_turn != state.turn:
        pre_turn = state.turn
        ability_used_dudunsparce = False
        ability_used_fezandipiti = False

    # ---- Count cards on field / hand / discard ----
    field_counts = defaultdict(int)
    hand_counts = defaultdict(int)
    discard_counts = defaultdict(int)

    my_field = []  # (field_index, pokemon) where 0=active, 1..=bench
    for card in my_state.active:
        if card is not None:
            field_counts[card.id] += 1
            my_field.append((0, card))
    for idx, card in enumerate(my_state.bench):
        if card is not None:
            field_counts[card.id] += 1
            my_field.append((idx + 1, card))

    for card in my_state.hand:
        hand_counts[card.id] += 1

    for card in my_state.discard:
        discard_counts[card.id] += 1

    abra_line_on_field = field_counts[Abra] + field_counts[Kadabra] + field_counts[Alakazam]
    dunsparce_line_on_field = field_counts[Dunsparce] + field_counts[Dudunsparce]

    # ---- Opponent field analysis ----
    op_all_pokemon = []
    for card in op_state.active:
        if card is not None:
            op_all_pokemon.append(card)
    for card in op_state.bench:
        if card is not None:
            op_all_pokemon.append(card)

    op_has_duskull = any(p.id == Duskull for p in op_all_pokemon)
    op_has_water_threat = any(
        p.id in Slowpoke_IDs or p.id in Froakie_IDs
        or p.id == Wellspring_Mask_Ogerpon_ex or p.id == N_Darumaka
        for p in op_all_pokemon
    )
    op_has_dragapult_line = any(
        p.id in (Dreepy, Drakloak, Dragapult_ex) for p in op_all_pokemon
    )

    # Detect if opponent has used ACE SPEC
    op_used_ace_spec = False
    for log in obs.logs:
        if hasattr(log, 'cardId') and log.cardId is not None:
            cd = card_table.get(log.cardId)
            if cd and cd.aceSpec and hasattr(log, 'playerIndex') and log.playerIndex == (1 - my_index):
                op_used_ace_spec = True

    stadium_id = 0
    for card in state.stadium:
        stadium_id = card.id

    bench_count = len(my_state.bench)
    bench_max = my_state.benchMax
    bench_free = bench_max - bench_count

    # ---- Active pokemon info ----
    active_pokemon = my_state.active[0] if my_state.active else None
    active_id = active_pokemon.id if active_pokemon else -1
    active_has_psychic = False
    if active_pokemon:
        for ec in active_pokemon.energyCards:
            if ec.id in PSYCHIC_ENERGY_IDS:
                active_has_psychic = True
                break

    # ---- Opponent active info ----
    op_active = op_state.active[0] if op_state.active else None
    op_active_hp = op_active.hp if op_active else 9999

    had_resource_first_latch = bool(_kadabra_resource_first_latch)
    resource_action = _kadabra_resource_first_overlay(obs)
    if resource_action is not None:
        return _remember_action(_decision_signature(obs), resource_action)
    resource_first_delegated = (
        had_resource_first_latch and not _kadabra_resource_first_latch
    )

    terminal_action = _reserve_terminal_win_overlay(obs)
    if terminal_action is not None:
        return _remember_action(_decision_signature(obs), terminal_action)

    had_stranded_retreat_latch = bool(_stranded_retreat_ko_latch)
    emergency_action = _stranded_retreat_ko_overlay(obs)
    if emergency_action is not None:
        return _remember_action(decision_signature, emergency_action)
    # Once a frozen route becomes stale, this callback belongs wholly to the
    # exact parent.  Do not restart a new retreat transaction in the same
    # observation after clearing the failed latch.
    stranded_retreat_delegated = (
        had_stranded_retreat_latch and not _stranded_retreat_ko_latch
    )

    emergency_action = _fez_ko_bridge_overlay(obs)
    if emergency_action is not None:
        return _remember_action(decision_signature, emergency_action)

    emergency_action = _enriching_reserve_overlay(obs)
    if emergency_action is not None:
        reserve_action = _apply_mandatory_draw_reserve(obs, emergency_action)
        if reserve_action != emergency_action:
            _clear_hilda_source_latch()
            _clear_enriching_reserve_latch()
            return _remember_action(_decision_signature(obs), reserve_action)
        return _remember_action(decision_signature, reserve_action)

    transaction_action = _active_psychic_immediate_ko_overlay(obs)
    if transaction_action is not None:
        return _remember_action(decision_signature, transaction_action)

    transaction_action = _start_active_psychic_immediate_ko(obs)
    if transaction_action is not None:
        return _remember_action(decision_signature, transaction_action)

    # ---- Estimate Powerful Hand damage range ----
    hand_size = len(my_state.hand) if my_state.hand else my_state.handCount

    def estimate_hand_increase():
        """Returns (min_increase, max_increase) of hand size this turn from draw effects."""
        min_inc = 0
        max_inc = 0
        for _, p in my_field:
            if p.id == Abra and hand_counts[Kadabra] > 0:
                max_inc += 1  # evolve Kadabra: hand -1, draw +2 = net +1
            elif p.id == Abra and hand_counts[Rare_Candy] > 0 and hand_counts[Alakazam] > 0:
                max_inc += 1  # Rare Candy + Alakazam: hand -2, draw +3 = net +1
            elif p.id == Kadabra and hand_counts[Alakazam] > 0:
                max_inc += 2  # evolve Alakazam: hand -1, draw +3 = net +2
            elif p.id == Dunsparce and hand_counts[Dudunsparce] > 0:
                max_inc += 1  # evolve: hand -1, ability draw +2 = net +1
            elif p.id == Dudunsparce:
                if not ability_used_dudunsparce:
                    max_inc += 3  # Run Away Draw
            elif p.id == Fezandipiti_ex:
                if not ability_used_fezandipiti:
                    max_inc += 3  # Flip the Script
        if hand_counts[Fezandipiti_ex] > 0 and bench_free > 0 and field_counts[Fezandipiti_ex] == 0:
            max_inc += 2  # play -1, ability +3 = net +2

        # Supporter (only 1 can be used)
        supporter_options = []
        if not state.supporterPlayed:
            if hand_counts[Hilda] > 0:
                supporter_options.append(1)   # play -1, search +2 = net +1
            if hand_counts[Dawn] > 0:
                supporter_options.append(2)   # play -1, search +3 = net +2
            if hand_counts[Boss_Orders] > 0:
                supporter_options.append(-1)  # play -1 = net -1
        if supporter_options:
            max_inc += max(supporter_options)

        # Enriching Energy attach: hand -1, draw +4 = net +3
        if hand_counts[Enriching_Energy] > 0 and not state.energyAttached:
            if active_id == Alakazam and active_has_psychic:
                max_inc += 3
        return min_inc, max_inc

    min_hand_inc, max_hand_inc = estimate_hand_increase()
    max_hand_size = hand_size + max_hand_inc
    min_hand_size = hand_size + min_hand_inc
    max_damage = max_hand_size * 20
    min_damage = min_hand_size * 20

    # ---- Target selection for attack ----
    target_idx = -1       # 0 = active, 1.. = bench
    target_pokemon = None
    target_use_boss = False
    target_can_kill = False
    target_prize_gain = 0
    target_hammer_needed = 0
    use_kadabra_finish = False

    if state.turn >= 2 and op_active is not None:
        # Check Kadabra finisher: opponent active HP <= 30
        if op_active_hp <= 30 and (field_counts[Kadabra] >= 1 or active_id == Kadabra):
            target_idx = 0
            target_pokemon = op_active
            target_use_boss = False
            target_can_kill = True
            target_prize_gain = prize_count(op_active)
            use_kadabra_finish = True
        else:
            # Evaluate all opponent pokemon
            all_op = [(0, op_active)]
            for bi, bp in enumerate(op_state.bench):
                if bp is not None:
                    all_op.append((bi + 1, bp))

            candidates = []
            for oi, pkmn in all_op:
                pz = prize_count(pkmn)
                sp_e = count_special_defense_energies(pkmn)
                eff_max_dmg = max_damage
                hm_need = 0
                if sp_e > 0:
                    if hand_counts[Enhanced_Hammer] >= sp_e:
                        hm_need = sp_e
                        eff_max_dmg = (max_hand_size - hm_need) * 20
                    else:
                        eff_max_dmg = 0
                ck = pkmn.hp <= eff_max_dmg and eff_max_dmg > 0
                candidates.append((oi, pkmn, pz, ck, hm_need))

            # Priority 1: kill wins the game
            win_cands = [(oi, pk, pz, ck, hm) for oi, pk, pz, ck, hm in candidates if ck and my_prize_count <= pz]
            if win_cands:
                # Among winners, prefer active (no boss needed), then highest HP
                best = min(win_cands, key=lambda x: (0 if x[0] == 0 else 1, -x[1].hp))
                target_idx, target_pokemon, target_prize_gain, target_can_kill, target_hammer_needed = best
                target_use_boss = target_idx != 0
            else:
                # Priority 2: killable target with most prizes
                killable = [(oi, pk, pz, ck, hm) for oi, pk, pz, ck, hm in candidates if ck]
                if killable:
                    best = max(killable, key=lambda x: (x[2], x[1].hp))
                    target_idx, target_pokemon, target_prize_gain, target_can_kill, target_hammer_needed = best
                    target_use_boss = target_idx != 0
                else:
                    # Priority 3: just hit active
                    target_idx = 0
                    target_pokemon = op_active
                    target_use_boss = False
                    target_can_kill = False
                    target_prize_gain = 0

    # Should we use Dudunsparce's ability?
    need_dudunsparce_draw = False
    if target_pokemon is not None and target_can_kill:
        needed = target_pokemon.hp
        current_dmg = (hand_size - target_hammer_needed) * 20
        if current_dmg < needed:
            need_dudunsparce_draw = True

    # Do we need to attach energy to the active to retreat?
    need_retreat_energy = False
    if active_pokemon is not None and state.turn >= 2:
        active_is_attacker = (active_id == Alakazam and active_has_psychic) or (use_kadabra_finish and active_id == Kadabra)
        if not active_is_attacker:
            # Check if there's a better attacker on bench
            has_bench_attacker = False
            if use_kadabra_finish and field_counts[Kadabra] >= 1 and active_id != Kadabra:
                has_bench_attacker = True
            elif field_counts[Alakazam] >= 1 and active_id != Alakazam:
                has_bench_attacker = True
            elif field_counts[Kadabra] >= 1 and active_id != Kadabra:
                has_bench_attacker = True
            if has_bench_attacker:
                retreat_cost = card_table[active_pokemon.id].retreatCost
                active_energy_count = len(active_pokemon.energies)
                if active_energy_count < retreat_cost:
                    need_retreat_energy = True

    # Do we need Fezandipiti ex's Flip the Script to kill the target?
    fez_hand_contribution = 0
    if field_counts[Fezandipiti_ex] >= 1 and not ability_used_fezandipiti:
        fez_hand_contribution = 3
    elif hand_counts[Fezandipiti_ex] > 0 and bench_free > 0 and field_counts[Fezandipiti_ex] == 0:
        fez_hand_contribution = 2  # play -1, ability +3 = net +2
    need_fezandipiti_draw = False
    if target_pokemon is not None and target_can_kill and fez_hand_contribution > 0:
        max_damage_without_fez = (max_hand_size - fez_hand_contribution - target_hammer_needed) * 20
        if max_damage_without_fez < target_pokemon.hp:
            need_fezandipiti_draw = True

    # Also allow Fezandipiti if drawing could find key enablers (Boss, Rare Candy, Alakazam, Energy)
    need_fezandipiti_for_setup = False
    if target_pokemon is not None and target_can_kill and fez_hand_contribution > 0 and not need_fezandipiti_draw:
        # Missing Boss's Orders for bench target
        missing_boss = (target_use_boss and hand_counts[Boss_Orders] == 0
                        and not state.supporterPlayed)
        # Check if we have a ready attacker (Alakazam with psychic energy)
        has_ready_attacker = (active_id == Alakazam and active_has_psychic)
        if not has_ready_attacker:
            for _, p in my_field:
                if p.id == Alakazam and any(ec.id in PSYCHIC_ENERGY_IDS for ec in p.energyCards):
                    has_ready_attacker = True
                    break
        missing_attacker = False
        missing_energy = False
        if not has_ready_attacker:
            # Can we set up Alakazam this turn?
            can_evolve_to_alakazam = (field_counts[Kadabra] >= 1 and hand_counts[Alakazam] >= 1)
            can_rare_candy_alakazam = (field_counts[Abra] >= 1 and hand_counts[Rare_Candy] >= 1
                                       and hand_counts[Alakazam] >= 1)
            if not can_evolve_to_alakazam and not can_rare_candy_alakazam:
                # Missing evolution pieces
                if field_counts[Kadabra] >= 1 and hand_counts[Alakazam] == 0:
                    missing_attacker = True
                elif field_counts[Abra] >= 1 and (hand_counts[Rare_Candy] == 0 or hand_counts[Alakazam] == 0):
                    missing_attacker = True
            # Check if energy is available for the attacker
            energy_in_hand = (hand_counts[Basic_Psychic_Energy] + hand_counts[Telepath_Psychic_Energy]
                              + hand_counts[Enriching_Energy])
            if not state.energyAttached and energy_in_hand == 0:
                has_energized = any(
                    p.id in ABRA_LINE and any(ec.id in PSYCHIC_ENERGY_IDS for ec in p.energyCards)
                    for _, p in my_field
                )
                if not has_energized:
                    missing_energy = True
        if missing_boss or missing_attacker or missing_energy:
            need_fezandipiti_for_setup = True

    # Deck safety: don't let deck count drop to <= prize count unless winning this turn
    can_win_this_turn = target_can_kill and my_prize_count <= target_prize_gain
    deck_count = my_state.deckCount
    # safe_draws: max cards we can draw from deck while keeping deck > prize count
    # We also need 1 card for the draw at start of next turn
    safe_draws = deck_count - my_prize_count - 1 if not can_win_this_turn else 999

    # ---- Score each option ----
    scores = []
    for o in select.option:
        score = 0

        if o.type == OptionType.NUMBER:
            score = o.number

        elif o.type == OptionType.YES:
            score = 1

        elif o.type == OptionType.CARD:
            card = get_card(obs, o.area, o.index, o.playerIndex)
            if card is None:
                scores.append(score)
                continue
            energy_count = len(card.energies) if isinstance(card, Pokemon) else 0

            if context == SelectContext.SWITCH or context == SelectContext.TO_ACTIVE:
                if o.playerIndex == my_index:
                    if card.id == Alakazam:
                        score += 100 + energy_count * 10
                    elif card.id == Kadabra:
                        score += 90 if (op_active_hp <= 30) else 30
                    elif card.id == Abra:
                        score += 10
                    elif card.id in DUNSPARCE_LINE:
                        score += 5
                    else:
                        score += 1
                else:
                    if target_use_boss and target_pokemon is not None:
                        if o.index == target_idx - 1:
                            score += 100

            elif context == SelectContext.SETUP_ACTIVE_POKEMON:
                if card.id == Abra:
                    score = 10
                elif card.id == Dunsparce:
                    score = 5
                elif card.id == Psyduck:
                    score = 2
                elif card.id == Shaymin:
                    score = 1

            elif context == SelectContext.SETUP_BENCH_POKEMON:
                if card.id == Abra:
                    cur = field_counts[Abra] + field_counts[Kadabra] + field_counts[Alakazam]
                    score = 200 if cur == 0 else 100 + (3 - cur) * 10
                elif card.id == Dunsparce:
                    score = 150 if dunsparce_line_on_field == 0 else 50

            elif context == SelectContext.TO_HAND:
                score = 200 - hand_counts.get(card.id, 0) * 50
                if card.id == Dudunsparce:
                    score += 80 if (field_counts[Dunsparce] >= 1 and field_counts[Dudunsparce] == 0) else -50
                elif card.id == Kadabra:
                    score += 70 if field_counts[Abra] >= 1 else -20
                elif card.id == Alakazam:
                    score += 60 if (field_counts[Kadabra] >= 1 or field_counts[Abra] >= 1) else -20
                elif card.id == Abra:
                    score += 50 if abra_line_on_field < 3 else -50
                elif card.id == Dunsparce:
                    score += 40 if dunsparce_line_on_field < 2 else -50
                elif card.id in PSYCHIC_ENERGY_IDS:
                    score += 30 if not state.energyAttached else -10
                elif card.id == Enriching_Energy:
                    score += 20
                elif card.id == Rare_Candy:
                    score += 40 if field_counts[Abra] >= 1 else -10

            elif context == SelectContext.ATTACH_FROM:
                if isinstance(card, Pokemon):
                    if need_retreat_energy and o.area == AreaType.ACTIVE:
                        score = 150  # Must attach to active to retreat
                    elif len(card.energyCards) >= 1:
                        score = -1  # Don't attach 2+ energy to the same pokemon
                    elif card.id in ABRA_LINE:
                        score = 100
                        if card.id == Alakazam:
                            score += 20
                        elif card.id == Kadabra:
                            score += 10
                        if o.area == AreaType.ACTIVE:
                            score += 5
                    elif card.id in DUNSPARCE_LINE:
                        score = 50
                    else:
                        score = 10

            elif context == SelectContext.TO_BENCH:
                if card.id == Abra:
                    score = 100
                elif card.id == Dunsparce:
                    score = 80
                elif card.id == Psyduck:
                    if op_has_duskull:
                        score = 60
                    else:
                        score = -1
                elif card.id == Shaymin:
                    if op_has_water_threat:
                        score = 40
                    else:
                        score = -1

            elif context == SelectContext.TO_DECK:
                if card.id in ABRA_LINE:
                    score = 100
                elif card.id in DUNSPARCE_LINE:
                    score = 50
                else:
                    score = 10

        elif o.type == OptionType.PLAY:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            data = card_table[card.id]

            if data.cardType == CardType.POKEMON:
                score = 20000
                is_early = state.turn <= 2

                if card.id == Abra:
                    if is_early:
                        score += 500
                    elif abra_line_on_field < 3:
                        score += 200
                    elif bench_free <= 1:
                        score = -1
                    else:
                        score += 50

                elif card.id == Dunsparce:
                    if dunsparce_line_on_field < 1:
                        score += 400 if is_early else 100
                    elif dunsparce_line_on_field < 2:
                        score += 50
                    else:
                        score = -1

                elif card.id == Fezandipiti_ex:
                    if need_fezandipiti_draw or need_fezandipiti_for_setup:
                        score += 80 if not is_early else 30
                    else:
                        score = -1  # Don't play unless Flip the Script is needed to kill

                elif card.id == Genesect:
                    if not op_used_ace_spec and (hand_counts[Lucky_Helmet] > 0 or hand_counts[Poke_Pad] > 0):
                        score += 100
                    else:
                        score = -1

                elif card.id == Psyduck:
                    if op_has_duskull:
                        score += 300
                    else:
                        score = -1

                elif card.id == Shaymin:
                    if op_has_water_threat:
                        score += 300
                    else:
                        score = -1

                # Keep at least 1 bench slot free
                if bench_free <= 1 and score > 0:
                    score -= 5000

            else:
                score = 10000

                if card.id == Buddy_Buddy_Poffin:
                    if safe_draws < 2:
                        score = -1  # Deck too thin (searches deck)
                    elif state.turn <= 2:
                        if abra_line_on_field < 3 or dunsparce_line_on_field < 1:
                            score = 18000
                        else:
                            score = 8000
                    else:
                        if abra_line_on_field < 3 or dunsparce_line_on_field < 2:
                            score = 15000
                        elif target_can_kill:
                            score = 8000
                        else:
                            score = -1

                elif card.id == Poke_Pad:
                    if safe_draws < 1:
                        score = -1  # Deck too thin (searches deck)
                    elif state.turn <= 2:
                        score = 17000
                    else:
                        score = 14000 if abra_line_on_field < 3 else 12000

                elif card.id == Rare_Candy:
                    if field_counts[Abra] >= 1 and hand_counts[Alakazam] >= 1 and safe_draws >= 3:
                        score = 16000
                    else:
                        score = -1

                elif card.id == Night_Stretcher:
                    dis_abra = discard_counts[Abra] + discard_counts[Kadabra] + discard_counts[Alakazam]
                    if dis_abra >= 1:
                        score = 13000
                    elif discard_counts[Basic_Psychic_Energy] + discard_counts[Telepath_Psychic_Energy] >= 1:
                        score = 11000
                    else:
                        score = -1

                elif card.id == Sacred_Ash:
                    dis_abra = discard_counts[Abra] + discard_counts[Kadabra] + discard_counts[Alakazam]
                    if dis_abra >= 2:
                        score = 13500
                    elif dis_abra >= 1:
                        score = 11000
                    else:
                        score = -1

                elif card.id == Enhanced_Hammer:
                    if target_hammer_needed > 0:
                        score = 6500
                    else:
                        # Check if any opponent pokemon has special defense energy
                        any_special = any(count_special_defense_energies(p) > 0 for p in op_all_pokemon)
                        if any_special:
                            score = 5000
                        else:
                            score = -1

                elif card.id == Lucky_Helmet:
                    score = 7000  # Will be handled via ATTACH

                elif card.id == Boss_Orders:
                    if target_use_boss and target_can_kill:
                        score = 3200
                    else:
                        score = -1

                elif card.id == Hilda:
                    if safe_draws >= 2:
                        score = 3000
                    else:
                        score = -1

                elif card.id == Dawn:
                    if safe_draws >= 3:
                        score = 3100
                    else:
                        score = -1

                elif card.id == Battle_Cage:
                    if op_has_dragapult_line:
                        score = 19000
                    elif stadium_id != 0:
                        score = 7000
                    else:
                        score = -1

        elif o.type == OptionType.ATTACH:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)

            if card.id == Lucky_Helmet:
                score = 7000
                if pokemon.id == Genesect and not op_used_ace_spec:
                    score += 300
                elif o.inPlayArea == AreaType.ACTIVE:
                    score += 200
                else:
                    score += 50

            elif card.id in PSYCHIC_ENERGY_IDS:
                if need_retreat_energy and o.inPlayArea == AreaType.ACTIVE:
                    score = 9500  # Must attach to active to retreat
                elif len(pokemon.energyCards) >= 1:
                    score = -1  # Don't attach 2+ energy to the same pokemon
                elif pokemon.id in ABRA_LINE:
                    score = 8000
                    if pokemon.id == Alakazam:
                        score += 30
                    elif pokemon.id == Kadabra:
                        score += 20
                    elif pokemon.id == Abra:
                        score += 10
                    if o.inPlayArea == AreaType.ACTIVE:
                        score += 5
                else:
                    score = -1
                # Telepath Psychic Energy searches 2 from deck
                if card.id == Telepath_Psychic_Energy and safe_draws < 2 and score > 0:
                    score = -1

            elif card.id == Enriching_Energy:
                if need_retreat_energy and o.inPlayArea == AreaType.ACTIVE:
                    score = 9500  # Must attach to active to retreat
                elif len(pokemon.energyCards) >= 1:
                    score = -1  # Don't attach 2+ energy to the same pokemon
                elif pokemon.id in DUNSPARCE_LINE:
                    score = 8500
                    if pokemon.id == Dudunsparce:
                        score += 10
                else:
                    score = -1
                # Enriching Energy draws 4 from deck
                if card.id == Enriching_Energy and safe_draws < 4 and score > 0:
                    score = -1

        elif o.type == OptionType.EVOLVE:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
            score = 9000

            if card.id == Alakazam:
                if safe_draws < 3:
                    score = -1  # Deck too thin for Psychic Draw (3 cards)
                elif o.inPlayArea == AreaType.ACTIVE:
                    score += 200  # Active Alakazam = highest
                else:
                    score += 50  # Bench Alakazam
                score += len(pokemon.energies) * 10

            elif card.id == Kadabra:
                if safe_draws < 2:
                    score = -1  # Deck too thin for Psychic Draw (2 cards)
                else:
                    score += 100
                    if len(pokemon.energies) == 0:
                        score += 50  # Evolve non-energy Abra first
                    else:
                        score -= 20
                        if hand_counts[Rare_Candy] > 0 and hand_counts[Alakazam] > 0:
                            score -= 100  # Save energy Abra for Rare Candy -> Alakazam

            elif card.id == Dudunsparce:
                if safe_draws < 2:
                    score = -1  # Deck too thin for draw on evolve
                else:
                    score += 80

        elif o.type == OptionType.ABILITY:
            card = get_card(obs, o.area, o.index, my_index)
            if card is None:
                scores.append(score)
                continue

            if card.id == Dudunsparce:
                # Run Away Draw shuffles Dudunsparce and every card attached
                # to it into the deck.  If it is our only Pokemon, using the
                # Ability removes the last Pokemon from play and loses the
                # game immediately.  This public board invariant takes
                # priority over every draw/damage estimate.
                if active_id == Dudunsparce and bench_count == 0:
                    score = -1
                elif need_dudunsparce_draw:
                    if safe_draws >= 3:
                        score = 30000
                    else:
                        score = -1  # Deck too thin
                else:
                    score = -1
            elif card.id == Fezandipiti_ex:
                if (need_fezandipiti_draw or need_fezandipiti_for_setup) and safe_draws >= 3:
                    score = 29000
                else:
                    score = -1  # Don't use unless needed to kill target
            elif card.id == Battle_Cage:
                score = 1
            else:
                score = 28000

        elif o.type == OptionType.RETREAT:
            if active_id == Alakazam and active_has_psychic:
                score = -1
            elif use_kadabra_finish and active_id != Kadabra and field_counts[Kadabra] >= 1:
                score = 2500  # Retreat to bring Kadabra forward for finish
            elif active_id in (Abra, Dunsparce, Dudunsparce, Psyduck, Shaymin, Genesect):
                if field_counts[Alakazam] >= 1 or field_counts[Kadabra] >= 1:
                    score = 2000
                else:
                    score = -1
            else:
                score = -1

        elif o.type == OptionType.ATTACK:
            score = 1000
            if o.attackId == ATTACK_POWERFUL_HAND:
                score += 500
            elif o.attackId == ATTACK_SUPER_PSY_BOLT:
                if op_active_hp <= 30:
                    score += 600  # Kadabra finisher
                else:
                    score += 100
            elif o.attackId == ATTACK_TELEPORTATION:
                score += 50

        scores.append(score)

    # Preserve the exact parent winner before applying the isolated post-prefix
    # Run Away Draw hit-bound overlay.
    parent_desc_indices = [
        i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    ]
    if context == SelectContext.MAIN and parent_desc_indices:
        parent_index = parent_desc_indices[0]
        parent_option = select.option[parent_index]
        parent_is_powerful_hand = (
            parent_option.type == OptionType.ATTACK
            and parent_option.attackId == ATTACK_POWERFUL_HAND
            and scores[parent_index] == 1500
        )
        target_blocks_counters = False
        if op_active is not None:
            attached_energy_ids = {energy.id for energy in op_active.energyCards}
            target_blocks_counters = Mist_Energy in attached_energy_ids
            if (
                Rock_Fighting_Energy in attached_energy_ids
                and card_table[op_active.id].energyType == EnergyType.FIGHTING
            ):
                target_blocks_counters = True

        if (
            parent_is_powerful_hand
            and active_id == Alakazam
            and active_has_psychic
            and op_active is not None
            and op_active_hp > 0
            and not target_blocks_counters
            and safe_draws >= 3
            and deck_count >= 3
            and _hit_bound_reduced(op_active_hp, hand_size, 3)
        ):
            legal_dudunsparce = _legal_bench_dudunsparce_options(
                obs, select.option, my_index
            )
            if legal_dudunsparce:
                attached_cards, _, chosen_option_index = legal_dudunsparce[0]
                if _run_away_draw_cost_certified(
                    op_active_hp,
                    hand_size,
                    attached_cards,
                    prize_count(op_active),
                    3,
                ):
                    scores[chosen_option_index] = 1550

    # Compute the exact v3 winner after its Run Away Draw overlay.  The second
    # overlay can only suppress an already top-ranked Abra Bench placement.
    v3_desc_indices = [
        i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    ]
    if context == SelectContext.MAIN and v3_desc_indices:
        v3_top_option = select.option[v3_desc_indices[0]]
        v3_top_card_id = None
        if v3_top_option.type == OptionType.PLAY:
            v3_top_card = get_card(
                obs, AreaType.HAND, v3_top_option.index, my_index
            )
            if v3_top_card is not None:
                v3_top_card_id = v3_top_card.id

        has_powerful_hand = any(
            option.type == OptionType.ATTACK
            and option.attackId == ATTACK_POWERFUL_HAND
            for option in select.option
        )
        opponent_energy_ids = (
            {energy.id for energy in op_active.energyCards}
            if op_active is not None
            else set()
        )
        bench_ids = {
            pokemon.id for pokemon in my_state.bench if pokemon is not None
        }
        if _fragile_bench_prize_clock_guard_certified(
            context=context,
            parent_top_type=v3_top_option.type,
            parent_top_card_id=v3_top_card_id,
            active_id=active_id,
            active_has_psychic=active_has_psychic,
            has_powerful_hand=has_powerful_hand,
            opponent_prizes=len(op_state.prize),
            opponent_active_id=op_active.id if op_active is not None else -1,
            opponent_energy_ids=opponent_energy_ids,
            own_has_shaymin=field_counts[Shaymin] > 0,
            stadium_id=stadium_id,
            bench_ids=bench_ids,
            hand_has_alakazam=hand_counts[Alakazam] > 0,
        ):
            for option_index, option in enumerate(select.option):
                if option.type != OptionType.PLAY:
                    continue
                played_card = get_card(
                    obs, AreaType.HAND, option.index, my_index
                )
                if played_card is not None and played_card.id == Abra:
                    scores[option_index] = -1

    # Select in descending order of score
    desc_indices = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]

    fez_bridge_action = _start_fez_ko_bridge(
        obs,
        select.option[desc_indices[0]] if desc_indices else None,
    )
    if fez_bridge_action is not None:
        return _remember_action(decision_signature, fez_bridge_action)

    chosen_action = desc_indices[:select.maxCount]

    if _kadabra_resource_first_latch:
        if (
            _kadabra_resource_first_latch.get("stage") != "await_safe_parent"
            or not _resource_stage_state_is_same(
                obs, _kadabra_resource_first_latch
            )
        ):
            _clear_kadabra_resource_first_latch()
        else:
            reserve_action = _apply_mandatory_draw_reserve(
                obs, chosen_action, desc_indices
            )
            _clear_kadabra_resource_first_latch()
            if context == SelectContext.MAIN and reserve_action:
                selected = select.option[reserve_action[0]]
                if selected.type == OptionType.ABILITY:
                    card = _safe_get_card(
                        obs, selected.area, selected.index, my_index
                    )
                    if card is not None and card.id == Dudunsparce:
                        ability_used_dudunsparce = True
                    elif card is not None and card.id == Fezandipiti_ex:
                        ability_used_fezandipiti = True
            return _remember_action(_decision_signature(obs), reserve_action)

    if not resource_first_delegated:
        resource_action = _start_kadabra_resource_first(obs, chosen_action)
        if resource_action is not None:
            return _remember_action(_decision_signature(obs), resource_action)

    exact_parent_action = list(chosen_action)
    chosen_action = _apply_mandatory_draw_reserve(
        obs, exact_parent_action, desc_indices
    )
    reserve_replaced_parent = chosen_action != exact_parent_action

    if context == SelectContext.MAIN and chosen_action:
        selected = select.option[chosen_action[0]]
        if selected.type == OptionType.ABILITY:
            card = _safe_get_card(obs, selected.area, selected.index, my_index)
            if card is not None:
                if card.id == Dudunsparce:
                    ability_used_dudunsparce = True
                elif card.id == Fezandipiti_ex:
                    ability_used_fezandipiti = True

    # This transaction is a terminal-choice replacement, not an early tactical
    # override.  The exact parent first computes every MAIN score and all of its
    # ordinary overlays.  Only replace its finalized ordinary END with the
    # already certified retreat -> promotion -> Powerful Hand route.
    if (
        not stranded_retreat_delegated
        and not reserve_replaced_parent
        and context == SelectContext.MAIN
        and len(chosen_action) == 1
        and select.option[chosen_action[0]].type == OptionType.END
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _kadabra_resource_first_latch
        and not _reserve_terminal_win_latch
    ):
        transaction_action = _start_stranded_retreat_ko_bridge(obs)
        if transaction_action is not None:
            # The first activation created the latch after decision_signature
            # was computed.  Recompute once so an identical repeated callback
            # returns the exact cached RETREAT instead of advancing the latch.
            return _remember_action(_decision_signature(obs), transaction_action)

    if (
        context == SelectContext.MAIN
        and chosen_action
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _kadabra_resource_first_latch
        and not _reserve_terminal_win_latch
    ):
        chosen_option = select.option[chosen_action[0]]
        if chosen_option.type == OptionType.PLAY:
            chosen_card = get_card(
                obs, AreaType.HAND, chosen_option.index, my_index
            )
            if chosen_card is not None and chosen_card.id == Hilda:
                _hilda_source_latch.update(
                    stage="await_evolution",
                    turn=state.turn,
                    player=my_index,
                    active_serial=(
                        active_pokemon.serial
                        if active_pokemon is not None
                        else None
                    ),
                )

    if (
        _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _kadabra_resource_first_latch
        or _reserve_terminal_win_latch
    ):
        return _remember_action(decision_signature, chosen_action)
    _clear_decision_cache()
    return chosen_action
