import os
import sys
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, Observation, SelectContext, OptionType, Card, Pokemon, all_card_data, to_observation_class

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


def _clear_decision_cache() -> None:
    global _last_decision_signature, _last_decision_action
    _last_decision_signature = None
    _last_decision_action = None


def _clear_emergency_state(*, clear_cache: bool = False) -> None:
    _clear_hilda_source_latch()
    _clear_enriching_reserve_latch()
    _clear_fez_ko_bridge_latch()
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
                (
                    pokemon.id,
                    pokemon.serial,
                    pokemon.hp,
                    tuple((card.id, card.serial) for card in pokemon.energyCards),
                    tuple((card.id, card.serial) for card in pokemon.tools),
                )
                for pokemon in mine.bench
            ),
            None
            if opponent is None
            else (
                tuple((card.id, card.serial) for card in opponent.preEvolution),
                tuple((card.id, card.serial) for card in opponent.energyCards),
                tuple((card.id, card.serial) for card in opponent.tools),
                theirs.poisoned,
                theirs.burned,
                theirs.asleep,
                theirs.paralyzed,
                theirs.confused,
            ),
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


def _bridge_target_fingerprint(pokemon: Pokemon, player_state) -> tuple:
    return _bridge_pokemon_fingerprint(pokemon) + (
        player_state.poisoned,
        player_state.burned,
        player_state.asleep,
        player_state.paralyzed,
        player_state.confused,
    )


def _bridge_pokemon_is_publicly_complete(pokemon: Pokemon | None) -> bool:
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
    return all(card.id > 0 and card.serial > 0 for card in attached)


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


def _bridge_bench_destination(mine) -> tuple[int, Pokemon] | None:
    candidates = []
    for bench_index, pokemon in enumerate(mine.bench):
        if (
            pokemon.id != Alakazam
            or pokemon.serial <= 0
            or not _bridge_pokemon_is_publicly_complete(pokemon)
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


def _bridge_find_pokemon(mine, serial: int) -> tuple[AreaType, int, Pokemon] | None:
    if mine.active and mine.active[0] is not None and mine.active[0].serial == serial:
        return AreaType.ACTIVE, 0, mine.active[0]
    for index, pokemon in enumerate(mine.bench):
        if pokemon.serial == serial:
            return AreaType.BENCH, index, pokemon
    return None


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
        or target is None
        or not _bridge_pokemon_is_publicly_complete(target)
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
        or parent_top_option is None
        or parent_top_option.type == OptionType.ATTACK
        or active is None
        or active.id != Fezandipiti_ex
        or active.serial <= 0
        or target is None
        or not _bridge_pokemon_is_publicly_complete(active)
        or not _bridge_pokemon_is_publicly_complete(target)
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

    destination = _bridge_bench_destination(mine)
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

    if not _bridge_same_counts_target(obs, latch):
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
            current_serials = tuple(
                card.serial for card in source_pokemon.energyCards
            )
            expected_current = tuple(
                serial
                for serial in latch.get("source_energy_serials", ())
                if serial not in payment_serials[:paid_count]
            )
            if current_serials != expected_current:
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
            current_payment_serials = {
                card.serial for card in source_pokemon.energyCards
            }
            discarded_serials = {card.serial for card in mine.discard}
            if (
                any(serial in current_payment_serials for serial in payment_serials)
                or not set(payment_serials).issubset(discarded_serials)
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

    emergency_action = _fez_ko_bridge_overlay(obs)
    if emergency_action is not None:
        return _remember_action(decision_signature, emergency_action)

    emergency_action = _enriching_reserve_overlay(obs)
    if emergency_action is not None:
        return _remember_action(decision_signature, emergency_action)

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
                if need_dudunsparce_draw:
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

    if context == SelectContext.MAIN:
        o = select.option[desc_indices[0]]
        if o.type == OptionType.ABILITY:
            card = get_card(obs, o.area, o.index, my_index)
            if card is not None:
                if card.id == Dudunsparce:
                    ability_used_dudunsparce = True
                elif card.id == Fezandipiti_ex:
                    ability_used_fezandipiti = True

    chosen_action = desc_indices[:select.maxCount]
    if (
        context == SelectContext.MAIN
        and chosen_action
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
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
    ):
        return _remember_action(decision_signature, chosen_action)
    _clear_decision_cache()
    return chosen_action
