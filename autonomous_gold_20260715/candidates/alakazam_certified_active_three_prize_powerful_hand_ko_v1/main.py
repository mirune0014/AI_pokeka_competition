import copy
import os
import sys
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, Observation, SelectContext, SelectType, OptionType, Card, Pokemon, all_attack, all_card_data, to_observation_class

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
Hariyama = 674
Mega_Lucario_ex = 678
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
_certified_turn_plan_latch = {}
_draw_survival_terminal_latch = {}
_draw_free_terminal_evolution_latch = {}
_enriching_zero_boss_lucario_latch = {}
_merge_start_quarantine_depth = 0
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


def _clear_certified_turn_plan_latch() -> None:
    _certified_turn_plan_latch.clear()


def _clear_draw_survival_terminal_latch() -> None:
    _draw_survival_terminal_latch.clear()


def _clear_draw_free_terminal_evolution_latch() -> None:
    _draw_free_terminal_evolution_latch.clear()


def _clear_enriching_zero_boss_lucario_latch() -> None:
    _enriching_zero_boss_lucario_latch.clear()


def _merge_push_start_quarantine() -> None:
    global _merge_start_quarantine_depth
    _merge_start_quarantine_depth += 1


def _merge_pop_start_quarantine() -> None:
    global _merge_start_quarantine_depth
    _merge_start_quarantine_depth = max(0, _merge_start_quarantine_depth - 1)


def _clear_decision_cache() -> None:
    global _last_decision_signature, _last_decision_action
    _last_decision_signature = None
    _last_decision_action = None


def _clear_emergency_state(*, clear_cache: bool = False) -> None:
    global _merge_start_quarantine_depth
    _clear_hilda_source_latch()
    _clear_enriching_reserve_latch()
    _clear_fez_ko_bridge_latch()
    _clear_active_psychic_ko_latch()
    _clear_stranded_retreat_ko_latch()
    _clear_certified_turn_plan_latch()
    _clear_draw_survival_terminal_latch()
    _clear_draw_free_terminal_evolution_latch()
    _clear_enriching_zero_boss_lucario_latch()
    _merge_start_quarantine_depth = 0
    if clear_cache:
        _clear_decision_cache()
        _clear_draw_survival_wrapper_cache()
        _clear_draw_free_terminal_wrapper_cache()
        _clear_enriching_zero_boss_lucario_wrapper_cache()


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
    turn_plan_guard_signature = None
    if _certified_turn_plan_latch:
        # Keep repeated callbacks idempotent without hiding any public
        # mutation that the frozen source-transition contract must inspect.
        turn_plan_guard_signature = (
            state.turnActionCount,
            state.firstPlayer,
            state.retreated,
            state.energyAttached,
            state.supporterPlayed,
            state.stadiumPlayed,
            state.result,
            len(mine.prize),
            len(theirs.prize),
            mine.handCount,
            theirs.handCount,
            mine.deckCount,
            theirs.deckCount,
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
            tuple(_bridge_card_fingerprint(card) for card in theirs.discard),
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
        turn_plan_guard_signature,
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
        (_certified_turn_plan_latch, _clear_certified_turn_plan_latch),
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
        or _certified_turn_plan_latch
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
        or _certified_turn_plan_latch
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


def _turn_plan_card_group_fingerprint(
    cards, player_index: int | None = None
) -> tuple | None:
    """Freeze a complete public card group with unique positive serials."""
    rows = []
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
        rows.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def _turn_plan_status_fingerprint(state) -> tuple:
    return tuple(
        (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        )
        for player in state.players
    )


def _turn_plan_board_rows(player, player_index: int) -> tuple | None:
    rows = []
    for area, pokemon_list in (
        (AreaType.ACTIVE, player.active),
        (AreaType.BENCH, player.bench),
    ):
        for index, pokemon in enumerate(pokemon_list):
            if pokemon is None:
                continue
            if not _bridge_pokemon_is_publicly_complete(
                pokemon, player_index
            ):
                return None
            rows.append(
                (
                    int(area),
                    index,
                    pokemon.serial,
                    _bridge_pokemon_fingerprint(pokemon),
                )
            )
    top_serials = [row[2] for row in rows]
    if len(top_serials) != len(set(top_serials)):
        return None
    return tuple(rows)


def _turn_plan_fixed_own_rows(
    mine, player_index: int, excluded_serials: set[int]
) -> tuple | None:
    rows = _turn_plan_board_rows(mine, player_index)
    if rows is None:
        return None
    return tuple(row for row in rows if row[2] not in excluded_serials)


def _turn_plan_freeze_common(
    obs: Observation, *, excluded_own_serials: set[int]
) -> dict | None:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    hand = _active_psychic_hand_fingerprint(mine, my_index)
    own_discard = _turn_plan_card_group_fingerprint(
        mine.discard, my_index
    )
    opponent_discard = _turn_plan_card_group_fingerprint(
        theirs.discard, 1 - my_index
    )
    stadium = _turn_plan_card_group_fingerprint(state.stadium)
    fixed_own = _turn_plan_fixed_own_rows(
        mine, my_index, excluded_own_serials
    )
    opponent_board = _turn_plan_board_rows(theirs, 1 - my_index)
    full_own = _turn_plan_board_rows(mine, my_index)
    if any(
        value is None
        for value in (
            hand,
            own_discard,
            opponent_discard,
            stadium,
            fixed_own,
            opponent_board,
            full_own,
        )
    ):
        return None
    return {
        "turn": state.turn,
        "player": my_index,
        "start_turn_action_count": state.turnActionCount,
        "first_player": state.firstPlayer,
        "result": state.result,
        "start_hand_fingerprint": hand,
        "start_hand_count": mine.handCount,
        "start_deck_count": mine.deckCount,
        "own_prize_count": len(mine.prize),
        "opponent_prize_count": len(theirs.prize),
        "opponent_hand_count": theirs.handCount,
        "opponent_deck_count": theirs.deckCount,
        "own_discard_fingerprint": own_discard,
        "opponent_discard_fingerprint": opponent_discard,
        "stadium_fingerprint": stadium,
        "status_fingerprint": _turn_plan_status_fingerprint(state),
        "supporter_played": state.supporterPlayed,
        "stadium_played": state.stadiumPlayed,
        "start_energy_attached": state.energyAttached,
        "start_retreated": state.retreated,
        "fixed_own_rows": fixed_own,
        "opponent_board_rows": opponent_board,
        "own_field_count": len(full_own),
    }


def _turn_plan_common_is_same(
    obs: Observation,
    latch: dict,
    *,
    hand_count: int,
    deck_count: int,
    action_count_delta: int,
) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    fixed_own = _turn_plan_fixed_own_rows(
        mine,
        my_index,
        set(latch.get("excluded_own_serials") or ()),
    )
    opponent_board = _turn_plan_board_rows(theirs, 1 - my_index)
    opponent_discard = _turn_plan_card_group_fingerprint(
        theirs.discard, 1 - my_index
    )
    stadium = _turn_plan_card_group_fingerprint(state.stadium)
    own_discard = _turn_plan_card_group_fingerprint(
        mine.discard, my_index
    )
    full_own = _turn_plan_board_rows(mine, my_index)
    return (
        state.turn == latch.get("turn")
        and my_index == latch.get("player")
        and state.turnActionCount
        == latch.get("start_turn_action_count") + action_count_delta
        and state.firstPlayer == latch.get("first_player")
        and state.result == latch.get("result") == -1
        and mine.hand is not None
        and len(mine.hand) == mine.handCount == hand_count
        and mine.deckCount == deck_count
        and len(mine.prize) == latch.get("own_prize_count")
        and len(theirs.prize) == latch.get("opponent_prize_count")
        and theirs.handCount == latch.get("opponent_hand_count")
        and theirs.deckCount == latch.get("opponent_deck_count")
        and opponent_discard
        == latch.get("opponent_discard_fingerprint")
        and stadium == latch.get("stadium_fingerprint")
        and _turn_plan_status_fingerprint(state)
        == latch.get("status_fingerprint")
        and state.supporterPlayed == latch.get("supporter_played")
        and state.stadiumPlayed == latch.get("stadium_played")
        and state.energyAttached == latch.get("start_energy_attached")
        and state.retreated == latch.get("start_retreated")
        and own_discard == latch.get("own_discard_fingerprint")
        and fixed_own == latch.get("fixed_own_rows")
        and opponent_board == latch.get("opponent_board_rows")
        and full_own is not None
        and len(full_own) == latch.get("own_field_count")
    )


def _turn_plan_hand_without_selected(
    mine, player_index: int, selected_fingerprint: tuple
) -> tuple | None:
    hand = _active_psychic_hand_fingerprint(mine, player_index)
    if hand is None or hand.count(selected_fingerprint) != 1:
        return None
    return tuple(row for row in hand if row != selected_fingerprint)


def _turn_plan_hand_has_frozen_prefix(
    mine,
    *,
    player_index: int,
    frozen_cards: tuple,
    selected_fingerprint: tuple,
    new_count: int,
) -> bool:
    hand = _active_psychic_hand_fingerprint(mine, player_index)
    if hand is None or selected_fingerprint in hand:
        return False
    if len(hand) != len(frozen_cards) + new_count:
        return False
    frozen_set = set(frozen_cards)
    if len(frozen_set) != len(frozen_cards) or not frozen_set <= set(hand):
        return False
    old_serials = {old[1] for old in frozen_cards}
    new_rows = [row for row in hand if row not in frozen_set]
    return (
        len(new_rows) == new_count
        and all(row[1] not in old_serials for row in new_rows)
    )


def _turn_plan_skill_is_yield_irrelevant(
    text: str,
    *,
    source_kind: str,
    owner: int | None,
    player_index: int,
) -> bool:
    normalized = _bridge_retaliation_normalized_text(text)
    if (
        "prevent all effects of attacks used by your opponent" in normalized
        and "done to" in normalized
    ):
        return False
    if _bridge_retaliation_skill_is_certified_irrelevant(
        text, source_kind=source_kind
    ):
        return True
    if (
        "can use any attack from its previous evolutions" in normalized
        and "damage" not in normalized
        and "prevent" not in normalized
    ):
        return True
    if (
        owner is not None
        and owner != player_index
        and normalized.startswith(
            "attacks used by the pokemon this card is attached to do"
        )
        and "prevent" not in normalized
        and "less damage" not in normalized
    ):
        return True
    return False


def _turn_plan_visible_effect_fingerprint(state) -> tuple | None:
    """Certify every visible static source relevant to attack yield."""
    records = []
    protected = []
    for owner, player in enumerate(state.players):
        for area, pokemon_list in (
            (AreaType.ACTIVE, player.active),
            (AreaType.BENCH, player.bench),
        ):
            for index, pokemon in enumerate(pokemon_list):
                if pokemon is None:
                    continue
                if not _bridge_pokemon_is_publicly_complete(pokemon, owner):
                    return None
                data = card_table.get(pokemon.id)
                if data is None or data.cardType != CardType.POKEMON:
                    return None
                if not all(
                    _turn_plan_skill_is_yield_irrelevant(
                        skill.text,
                        source_kind="pokemon",
                        owner=owner,
                        player_index=state.yourIndex,
                    )
                    for skill in (data.skills or [])
                ):
                    return None
                protected.extend(_bridge_pokemon_component_serials(pokemon))
                records.append(
                    (
                        owner,
                        int(area),
                        index,
                        "pokemon",
                        _bridge_pokemon_fingerprint(pokemon),
                        _bridge_metadata_skill_fingerprint(data),
                    )
                )
                for kind, cards, allowed in (
                    ("tool", pokemon.tools, {CardType.TOOL}),
                    (
                        "energy",
                        pokemon.energyCards,
                        {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY},
                    ),
                ):
                    for card in cards:
                        card_data = card_table.get(card.id)
                        if (
                            card_data is None
                            or card_data.cardType not in allowed
                            or card.serial <= 0
                            or getattr(card, "playerIndex", None) != owner
                            or (
                                kind == "energy"
                                and _bridge_retaliation_energy_unit(card)
                                is None
                            )
                            or not all(
                                _turn_plan_skill_is_yield_irrelevant(
                                    skill.text,
                                    source_kind=kind,
                                    owner=owner,
                                    player_index=state.yourIndex,
                                )
                                for skill in (card_data.skills or [])
                            )
                        ):
                            return None
                        records.append(
                            (
                                owner,
                                int(area),
                                index,
                                kind,
                                _bridge_card_fingerprint(card),
                                _bridge_metadata_skill_fingerprint(card_data),
                            )
                        )
    if (
        len(protected) != len(set(protected))
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None
    for stadium in state.stadium:
        data = card_table.get(stadium.id)
        if (
            data is None
            or data.cardType != CardType.STADIUM
            or stadium.id <= 0
            or stadium.serial <= 0
            or not all(
                _turn_plan_skill_is_yield_irrelevant(
                    skill.text,
                    source_kind="stadium",
                    owner=None,
                    player_index=state.yourIndex,
                )
                for skill in (data.skills or [])
            )
        ):
            return None
        records.append(
            (
                None,
                int(AreaType.STADIUM),
                0,
                "stadium",
                _bridge_card_fingerprint(stadium),
                _bridge_metadata_skill_fingerprint(data),
            )
        )
    return tuple(sorted(records, key=repr))


def _turn_plan_attack_certificate(
    state,
    *,
    attacker_id: int,
    attack_id: int,
    energy_units: tuple[int, ...],
    hand_count: int,
    target: Pokemon,
    player_index: int,
) -> dict | None:
    """Return an exact Super Psy Bolt or Powerful Hand public yield."""
    mine = state.players[player_index]
    theirs = state.players[1 - player_index]
    if (
        mine.asleep
        or mine.paralyzed
        or mine.confused
        or hand_count < 0
        or target is None
        or not _bridge_pokemon_is_publicly_complete(target, 1 - player_index)
        or target.hp <= 0
    ):
        return None
    attacker_data = card_table.get(attacker_id)
    target_data = card_table.get(target.id)
    attack = attack_table.get(attack_id)
    if (
        attacker_data is None
        or target_data is None
        or attack is None
        or attack.attackId != attack_id
        or (
            attacker_id == Kadabra
            and attack_id != ATTACK_SUPER_PSY_BOLT
        )
        or (
            attacker_id == Alakazam
            and attack_id != ATTACK_POWERFUL_HAND
        )
        or attacker_id not in (Kadabra, Alakazam)
        or _bridge_retaliation_can_pay(
            energy_units, tuple(attack.energies)
        )
        is not True
    ):
        return None
    effects = _turn_plan_visible_effect_fingerprint(state)
    if effects is None:
        return None

    if attack_id == ATTACK_SUPER_PSY_BOLT:
        if attack.damage != 30 or (attack.text or "").strip():
            return None
        amount = 30
        attack_type = int(attacker_data.energyType)
        if (
            target_data.weakness is not None
            and int(target_data.weakness) == attack_type
        ):
            amount *= 2
        if (
            target_data.resistance is not None
            and int(target_data.resistance) == attack_type
        ):
            amount = max(0, amount - 30)
        effect_kind = "damage"
    else:
        normalized = " ".join(
            _normalized_skill_text(attack.text).split()
        )
        if (
            attack.damage != 0
            or "2 damage counters" not in normalized
            or "for each card in your hand" not in normalized
        ):
            return None
        amount = 20 * hand_count
        effect_kind = "damage_counters"

    target_prizes = prize_count(target)
    if amount <= 0 or target_prizes <= 0:
        return None
    return {
        "attack_id": attack_id,
        "effect_kind": effect_kind,
        "amount": amount,
        "target_serial": target.serial,
        "target_fingerprint": _bridge_target_fingerprint(target, theirs),
        "target_prizes": target_prizes,
        "prize_yield": target_prizes if amount >= target.hp else 0,
        "ko": amount >= target.hp,
        "visible_effect_fingerprint": effects,
    }


def _turn_plan_attack_for_pokemon(
    state,
    pokemon: Pokemon,
    *,
    hand_count: int,
    target: Pokemon,
    player_index: int,
) -> dict | None:
    if pokemon.id == Kadabra:
        attack_id = ATTACK_SUPER_PSY_BOLT
    elif pokemon.id == Alakazam:
        attack_id = ATTACK_POWERFUL_HAND
    else:
        return None
    units = _bridge_retaliation_energy_units(pokemon)
    if units is None:
        return None
    return _turn_plan_attack_certificate(
        state,
        attacker_id=pokemon.id,
        attack_id=attack_id,
        energy_units=tuple(units),
        hand_count=hand_count,
        target=target,
        player_index=player_index,
    )


def _turn_plan_selected_hand_card(
    obs: Observation, option, player_index: int
) -> Card | None:
    mine = obs.current.players[player_index]
    if (
        option.area != AreaType.HAND
        or option.playerIndex not in (None, player_index)
        or not isinstance(option.index, int)
        or option.index < 0
        or option.index >= len(mine.hand or [])
    ):
        return None
    card = mine.hand[option.index]
    return card if card is not None else None


def _start_evolve_active_ready(
    obs: Observation, parent_option
) -> list[int] | None:
    """Redirect one ordinary Bench evolution to the uniquely ready Active."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if len(mine.active) == 1 else None
    target = theirs.active[0] if len(theirs.active) == 1 else None
    if (
        select.context != SelectContext.MAIN
        or state.turn < 2
        or _certified_turn_plan_latch
        or _draw_survival_terminal_latch
        or _draw_free_terminal_evolution_latch
        or _enriching_zero_boss_lucario_latch
        or _merge_start_quarantine_depth
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or parent_option is None
        or parent_option.type != OptionType.EVOLVE
        or parent_option.inPlayArea != AreaType.BENCH
        or active is None
        or active.id not in (Abra, Kadabra)
        or active.appearThisTurn
        or not any(
            card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards
        )
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or target is None
        or select.minCount != 1
        or select.maxCount != 1
    ):
        return None

    evolution = _turn_plan_selected_hand_card(obs, parent_option, my_index)
    expected_id = Kadabra if active.id == Abra else Alakazam
    expected_attack = (
        ATTACK_SUPER_PSY_BOLT
        if expected_id == Kadabra
        else ATTACK_POWERFUL_HAND
    )
    expected_draw = 2 if expected_id == Kadabra else 3
    if (
        evolution is None
        or evolution.id != expected_id
        or evolution.serial <= 0
        or getattr(evolution, "playerIndex", None) != my_index
        or mine.deckCount - expected_draw <= len(mine.prize)
        or sum(card.id == expected_id for card in mine.hand) != 1
    ):
        return None

    active_options = [
        option_index
        for option_index, option in enumerate(select.option)
        if option.type == OptionType.EVOLVE
        and option.area == AreaType.HAND
        and option.index == parent_option.index
        and option.inPlayArea == AreaType.ACTIVE
        and option.inPlayIndex == 0
        and option.playerIndex in (None, my_index)
    ]
    if len(active_options) != 1:
        return None
    energy_units = _bridge_retaliation_energy_units(active)
    if energy_units is None:
        return None
    projected_hand_count = mine.handCount - 1 + expected_draw
    candidate_certificate = _turn_plan_attack_certificate(
        state,
        attacker_id=expected_id,
        attack_id=expected_attack,
        energy_units=energy_units,
        hand_count=projected_hand_count,
        target=target,
        player_index=my_index,
    )
    if candidate_certificate is None:
        return None
    parent_certificate = _turn_plan_attack_for_pokemon(
        state,
        active,
        hand_count=projected_hand_count,
        target=target,
        player_index=my_index,
    )
    parent_prize_yield = (
        0 if parent_certificate is None else parent_certificate["prize_yield"]
    )
    parent_amount = (
        0 if parent_certificate is None else parent_certificate["amount"]
    )
    if (
        candidate_certificate["prize_yield"] < parent_prize_yield
        or candidate_certificate["amount"] < parent_amount
        or (
            candidate_certificate["prize_yield"] == parent_prize_yield
            and candidate_certificate["amount"] == parent_amount
        )
    ):
        return None

    parent_target = get_card(
        obs, parent_option.inPlayArea, parent_option.inPlayIndex, my_index
    )
    if (
        parent_target is None
        or parent_target.id != active.id
        or not _bridge_pokemon_is_publicly_complete(parent_target, my_index)
        or any(
            card.id in PSYCHIC_ENERGY_IDS
            for card in parent_target.energyCards
        )
    ):
        return None
    common = _turn_plan_freeze_common(
        obs, excluded_own_serials={active.serial, evolution.serial}
    )
    selected_fingerprint = _bridge_card_fingerprint(evolution)
    hand_after = _turn_plan_hand_without_selected(
        mine, my_index, selected_fingerprint
    )
    protected = [
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(parent_target),
        *_bridge_pokemon_component_serials(target),
        evolution.serial,
    ]
    if (
        common is None
        or hand_after is None
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None

    source_damage = active.maxHp - active.hp
    expected_data = card_table.get(expected_id)
    if (
        source_damage < 0
        or expected_data is None
        or expected_data.hp <= source_damage
    ):
        return None
    _certified_turn_plan_latch.update(
        common,
        stage="await_optional_draw",
        branch="EVOLVE_ACTIVE_READY",
        excluded_own_serials=(active.serial, evolution.serial),
        selected_card_fingerprint=selected_fingerprint,
        frozen_hand_after_action=hand_after,
        source_id=active.id,
        source_serial=active.serial,
        source_damage=source_damage,
        source_energy_fingerprints=tuple(
            _bridge_card_fingerprint(card) for card in active.energyCards
        ),
        source_energy_units=tuple(int(unit) for unit in active.energies),
        source_tool_fingerprints=tuple(
            _bridge_card_fingerprint(card) for card in active.tools
        ),
        source_pre_evolution_fingerprints=tuple(
            _bridge_card_fingerprint(card) for card in active.preEvolution
        ),
        expected_evolution_id=expected_id,
        expected_evolution_serial=evolution.serial,
        expected_evolution_max_hp=expected_data.hp,
        expected_evolution_hp=expected_data.hp - source_damage,
        expected_draw_count=expected_draw,
        expected_attack_id=expected_attack,
        certificate_core=(
            candidate_certificate["attack_id"],
            candidate_certificate["amount"],
            candidate_certificate["prize_yield"],
            candidate_certificate["target_serial"],
        ),
    )
    return [active_options[0]]


def _turn_plan_unique_evolved_active(mine, latch: dict) -> Pokemon | None:
    active = [pokemon for pokemon in mine.active if pokemon is not None]
    matches = [
        pokemon
        for pokemon in active
        if pokemon.id == latch.get("expected_evolution_id")
        and pokemon.serial == latch.get("expected_evolution_serial")
    ]
    if len(active) != 1 or len(matches) != 1:
        return None
    return matches[0]


def _turn_plan_evolved_source_is_same(
    obs: Observation, latch: dict
) -> Pokemon | None:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    pokemon = _turn_plan_unique_evolved_active(mine, latch)
    target = theirs.active[0] if len(theirs.active) == 1 else None
    expected_pre = tuple(
        latch.get("source_pre_evolution_fingerprints") or ()
    ) + (
        (
            latch.get("source_id"),
            latch.get("source_serial"),
            my_index,
        ),
    )
    if (
        pokemon is None
        or target is None
        or not _bridge_pokemon_is_publicly_complete(pokemon, my_index)
        or pokemon.maxHp != latch.get("expected_evolution_max_hp")
        or pokemon.hp != latch.get("expected_evolution_hp")
        or pokemon.appearThisTurn is not True
        or tuple(
            _bridge_card_fingerprint(card) for card in pokemon.energyCards
        )
        != latch.get("source_energy_fingerprints")
        or tuple(int(unit) for unit in pokemon.energies)
        != latch.get("source_energy_units")
        or tuple(
            _bridge_card_fingerprint(card) for card in pokemon.tools
        )
        != latch.get("source_tool_fingerprints")
        or tuple(
            _bridge_card_fingerprint(card) for card in pokemon.preEvolution
        )
        != expected_pre
        or not _bridge_protected_serials_are_unique(
            state,
            [
                *_bridge_pokemon_component_serials(pokemon),
                *_bridge_pokemon_component_serials(target),
            ],
        )
    ):
        return None
    return pokemon


def _turn_plan_certificate_is_same(
    obs: Observation, latch: dict, pokemon: Pokemon
) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if len(theirs.active) == 1 else None
    certificate = _turn_plan_attack_for_pokemon(
        state,
        pokemon,
        hand_count=(
            latch.get("start_hand_count")
            - 1
            + latch.get("expected_draw_count")
        ),
        target=target,
        player_index=my_index,
    )
    return (
        certificate is not None
        and (
            certificate["attack_id"],
            certificate["amount"],
            certificate["prize_yield"],
            certificate["target_serial"],
        )
        == latch.get("certificate_core")
    )


def _turn_plan_evolution_overlay(
    obs: Observation, latch: dict
) -> list[int] | None:
    select = obs.select
    my_index = obs.current.yourIndex
    mine = obs.current.players[my_index]
    draw_count = latch.get("expected_draw_count")
    selected = latch.get("selected_card_fingerprint")
    if (
        latch.get("stage") != "await_optional_draw"
        or latch.get("branch") != "EVOLVE_ACTIVE_READY"
    ):
        _clear_certified_turn_plan_latch()
        return None

    if select.context == SelectContext.ACTIVATE:
        pokemon = _turn_plan_evolved_source_is_same(obs, latch)
        context_card = select.contextCard
        if (
            pokemon is None
            or context_card is None
            or _bridge_card_fingerprint(context_card) != selected
            or not _turn_plan_common_is_same(
                obs,
                latch,
                hand_count=latch.get("start_hand_count") - 1,
                deck_count=latch.get("start_deck_count"),
                action_count_delta=1,
            )
            or not _turn_plan_hand_has_frozen_prefix(
                mine,
                player_index=my_index,
                frozen_cards=latch.get("frozen_hand_after_action"),
                selected_fingerprint=selected,
                new_count=0,
            )
            or not _turn_plan_certificate_is_same(obs, latch, pokemon)
        ):
            _clear_certified_turn_plan_latch()
            return None
        yes = [
            index
            for index, option in enumerate(select.option)
            if option.type == OptionType.YES
        ]
        if len(yes) != 1 or select.minCount != 1 or select.maxCount != 1:
            _clear_certified_turn_plan_latch()
            return None
        return [yes[0]]

    if select.context != SelectContext.MAIN:
        _clear_certified_turn_plan_latch()
        return None
    pokemon = _turn_plan_evolved_source_is_same(obs, latch)
    attack_matches = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK
        and option.attackId == latch.get("expected_attack_id")
    ]
    valid = (
        pokemon is not None
        and _turn_plan_common_is_same(
            obs,
            latch,
            hand_count=latch.get("start_hand_count") - 1 + draw_count,
            deck_count=latch.get("start_deck_count") - draw_count,
            action_count_delta=2,
        )
        and _turn_plan_hand_has_frozen_prefix(
            mine,
            player_index=my_index,
            frozen_cards=latch.get("frozen_hand_after_action"),
            selected_fingerprint=selected,
            new_count=draw_count,
        )
        and _turn_plan_certificate_is_same(obs, latch, pokemon)
        and len(attack_matches) == 1
        and select.minCount == 1
        and select.maxCount == 1
    )
    _clear_certified_turn_plan_latch()
    if not valid:
        return None
    # Exact v3 owns the entire same MAIN callback.  In particular, it may
    # evolve a second line before attacking.
    return None


def _certified_turn_plan_overlay(
    obs: Observation,
) -> list[int] | None:
    if not _certified_turn_plan_latch:
        return None
    if _certified_turn_plan_latch.get("branch") != "EVOLVE_ACTIVE_READY":
        _clear_certified_turn_plan_latch()
        return None
    return _turn_plan_evolution_overlay(obs, _certified_turn_plan_latch)


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
        or _certified_turn_plan_latch
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


def _direct_terminal_local_energy_hp_delta(
    energy: Card, source: Pokemon
) -> int | None:
    """Certify one exact, source-local attached-Energy HP modifier."""
    data = card_table.get(energy.id)
    source_data = card_table.get(source.id)
    if data is None or source_data is None:
        return None
    texts = [
        " ".join(
            _normalized_skill_text(skill.text)
            .replace("pokémon", "pokemon")
            .split()
        )
        for skill in (data.skills or [])
    ]
    hp_texts = [text for text in texts if " hp" in text]
    if not hp_texts:
        return 0
    token = {
        int(EnergyType.GRASS): "{g}",
        int(EnergyType.FIRE): "{r}",
        int(EnergyType.WATER): "{w}",
        int(EnergyType.LIGHTNING): "{l}",
        int(EnergyType.PSYCHIC): "{p}",
        int(EnergyType.FIGHTING): "{f}",
        int(EnergyType.DARKNESS): "{d}",
        int(EnergyType.METAL): "{m}",
    }.get(int(data.energyType))
    if (
        data.cardType != CardType.SPECIAL_ENERGY
        or len(texts) != 1
        or len(hp_texts) != 1
        or token is None
        or int(source_data.energyType) != int(data.energyType)
    ):
        return None
    prefix = (
        f"as long as this card is attached to a pokemon, it provides {token} "
        f"energy. the {token} pokemon this card is attached to gets +"
    )
    suffix = " hp."
    text = hp_texts[0]
    if not text.startswith(prefix) or not text.endswith(suffix):
        return None
    amount = text[len(prefix) : -len(suffix)]
    return int(amount) if amount.isdigit() and int(amount) > 0 else None


def _direct_terminal_max_hp_is_exact(state, pokemon: Pokemon) -> bool:
    """Match printed HP plus exact public source-local Energy bonuses."""
    data = card_table.get(pokemon.id)
    if data is None or data.hp <= 0:
        return False
    expected = data.hp
    for player in state.players:
        for source in list(player.active) + list(player.bench):
            source_data = card_table.get(source.id)
            if source_data is None:
                return False
            for skill in source_data.skills or []:
                if " hp" in (
                    " "
                    + " ".join(
                        _normalized_skill_text(skill.text)
                        .replace("pokémon", "pokemon")
                        .split()
                    )
                ):
                    return False
            for tool in source.tools:
                tool_data = card_table.get(tool.id)
                if tool_data is None:
                    return False
                if any(
                    " hp" in (
                        " "
                        + " ".join(
                            _normalized_skill_text(skill.text)
                            .replace("pokémon", "pokemon")
                            .split()
                        )
                    )
                    for skill in (tool_data.skills or [])
                ):
                    return False
            for energy in source.energyCards:
                delta = _direct_terminal_local_energy_hp_delta(energy, source)
                if delta is None:
                    return False
                if source.serial == pokemon.serial:
                    expected += delta
    for stadium in state.stadium:
        stadium_data = card_table.get(stadium.id)
        if stadium_data is None:
            return False
        if any(
            " hp" in (
                " "
                + " ".join(
                    _normalized_skill_text(skill.text)
                    .replace("pokémon", "pokemon")
                    .split()
                )
            )
            for skill in (stadium_data.skills or [])
        ):
            return False
    return pokemon.maxHp == expected


def _direct_terminal_counter_target_is_clear(
    obs: Observation, target: Pokemon
) -> bool:
    """Retain the shared guard, allowing only an exact local HP Energy."""
    if _draw_survival_counter_target_is_clear(obs, target):
        return True
    state = obs.current
    opponent_index = 1 - state.yourIndex
    data = card_table.get(target.id)
    if data is None or data.resistance == EnergyType.PSYCHIC:
        return False
    energy_ids = {card.id for card in target.energyCards}
    if Mist_Energy in energy_ids or (
        Rock_Fighting_Energy in energy_ids
        and data.energyType == EnergyType.FIGHTING
    ):
        return False
    known_nondefensive_special = {
        12,
        Enriching_Energy,
        Telepath_Psychic_Energy,
        Rock_Fighting_Energy,
    }
    certified_hp_energy = False
    for energy in target.energyCards:
        energy_data = card_table.get(energy.id)
        if energy_data is None:
            return False
        if (
            energy_data.cardType == CardType.SPECIAL_ENERGY
            and energy.id not in known_nondefensive_special
        ):
            delta = _direct_terminal_local_energy_hp_delta(energy, target)
            if delta is None or delta <= 0:
                return False
            certified_hp_energy = True

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
    if any(
        _skill_may_change_powerful_hand_damage(skill.text)
        for effect_card in public_effect_cards
        for skill in (effect_card.skills or [])
    ):
        return False

    theirs = state.players[opponent_index]
    public_sources = []
    for pokemon in list(theirs.active) + list(theirs.bench):
        public_sources.append(pokemon.id)
        public_sources.extend(card.id for card in pokemon.tools)
        public_sources.extend(card.id for card in pokemon.energyCards)
    public_sources.extend(card.id for card in state.stadium)
    for card_id in public_sources:
        source_data = card_table.get(card_id)
        if source_data is None:
            return False
        for skill in source_data.skills or []:
            normalized = " ".join((skill.text or "").lower().split())
            if (
                "prevent all effects of attacks" in normalized
                or "prevent all damage from and effects of attacks" in normalized
            ) and card_id not in (Mist_Energy, Rock_Fighting_Energy):
                return False
    if any(
        getattr(log, "cardId", None) == 1228
        and getattr(log, "playerIndex", None) == opponent_index
        for log in obs.logs
    ):
        return False
    return certified_hp_energy


def _direct_terminal_powerful_hand_action(
    obs: Observation,
    obs_dict: dict,
) -> list[int] | None:
    """Take one certified, immediately winning Powerful Hand attack."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    if (
        not _draw_free_exact_main_envelope(select)
        or state.result != -1
        or state.looking is not None
        or state.turn < 2
        or _merge_start_quarantine_depth != 0
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _certified_turn_plan_latch
        or _draw_survival_terminal_latch
        or _draw_free_terminal_evolution_latch
        or _enriching_zero_boss_lucario_latch
        or not _draw_survival_public_state_is_complete(obs)
        or not _draw_free_powerful_hand_metadata_certified()
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or _draw_free_status(mine) != (False, False, False, False, False)
    ):
        return None

    active = mine.active[0]
    target = theirs.active[0]
    raw_current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    raw_players = (
        raw_current.get("players") if isinstance(raw_current, dict) else None
    )
    if not isinstance(raw_players, list) or len(raw_players) != 2:
        return None
    raw_mine = raw_players[my_index]
    raw_theirs = raw_players[1 - my_index]
    raw_active = raw_mine.get("active") if isinstance(raw_mine, dict) else None
    raw_target = raw_theirs.get("active") if isinstance(raw_theirs, dict) else None
    if (
        not isinstance(raw_active, list)
        or len(raw_active) != 1
        or not isinstance(raw_active[0], dict)
        or raw_active[0].get("playerIndex") != my_index
        or raw_active[0].get("id") != active.id
        or raw_active[0].get("serial") != active.serial
        or not isinstance(raw_target, list)
        or len(raw_target) != 1
        or not isinstance(raw_target[0], dict)
        or raw_target[0].get("playerIndex") != 1 - my_index
        or raw_target[0].get("id") != target.id
        or raw_target[0].get("serial") != target.serial
    ):
        return None
    active_data = card_table.get(active.id)
    target_data = card_table.get(target.id)
    hand = _draw_survival_exact_hand(mine, my_index)
    if (
        active.id != Alakazam
        or active_data is None
        or active_data.hp <= 0
        or not _direct_terminal_max_hp_is_exact(state, active)
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or target_data is None
        or target_data.hp <= 0
        or not _direct_terminal_max_hp_is_exact(state, target)
        or not _draw_survival_known_stack_is_exact(target, 1 - my_index)
        or not _direct_terminal_counter_target_is_clear(obs, target)
        or hand is None
        or len(hand) != mine.handCount
    ):
        return None

    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    energy_units = _bridge_retaliation_energy_units(active)
    if (
        powerful is None
        or energy_units is None
        or _bridge_retaliation_can_pay(energy_units, powerful.energies) is not True
    ):
        return None

    attack_options = []
    for option_index, option in enumerate(select.option):
        if option.type != OptionType.ATTACK and option.attackId is None:
            continue
        if (
            not _draw_survival_attack_option_is_exact(option)
            or option.attackId != ATTACK_POWERFUL_HAND
        ):
            return None
        attack_options.append(option_index)
    if len(attack_options) != 1:
        return None

    target_prizes = prize_count(target)
    own_prizes = len(mine.prize)
    terminal_by_prize = target_prizes >= own_prizes
    terminal_by_board = len(theirs.bench) == 0
    if (
        20 * len(hand) < target.hp
        or target_prizes <= 0
        or own_prizes <= 0
        or not (terminal_by_prize or terminal_by_board)
    ):
        return None
    return [attack_options[0]]


def _source_transition_v2_parent_agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        _clear_emergency_state(clear_cache=True)
        return my_deck

    state = obs.current
    select = obs.select
    context = select.context
    direct_terminal_owner_at_entry = bool(
        _merge_start_quarantine_depth
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _certified_turn_plan_latch
        or _draw_survival_terminal_latch
        or _draw_free_terminal_evolution_latch
        or _enriching_zero_boss_lucario_latch
    )
    had_turn_plan_at_entry = bool(_certified_turn_plan_latch)
    _prepare_emergency_state(obs)
    turn_plan_prepare_cleared = (
        had_turn_plan_at_entry and not _certified_turn_plan_latch
    )
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
        return _remember_action(decision_signature, emergency_action)

    transaction_action = _active_psychic_immediate_ko_overlay(obs)
    if transaction_action is not None:
        return _remember_action(decision_signature, transaction_action)

    had_turn_plan_latch = bool(_certified_turn_plan_latch)
    transaction_action = _certified_turn_plan_overlay(obs)
    if transaction_action is not None:
        return _remember_action(decision_signature, transaction_action)
    turn_plan_delegated = bool(
        turn_plan_prepare_cleared
        or (had_turn_plan_latch and not _certified_turn_plan_latch)
    )
    if turn_plan_delegated:
        # Success and fail-closed paths cache the parent's answer against the
        # public signature after the private latch has been cleared.
        decision_signature = _decision_signature(obs)

    direct_terminal_action = _direct_terminal_powerful_hand_action(obs, obs_dict)
    if (
        not direct_terminal_owner_at_entry
        and direct_terminal_action is not None
    ):
        return _remember_action(decision_signature, direct_terminal_action)

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
    # This transaction is a terminal-choice replacement, not an early tactical
    # override.  The exact parent first computes every MAIN score and all of its
    # ordinary overlays.  Only replace its finalized ordinary END with the
    # already certified retreat -> promotion -> Powerful Hand route.
    if (
        not stranded_retreat_delegated
        and context == SelectContext.MAIN
        and len(chosen_action) == 1
        and select.option[chosen_action[0]].type == OptionType.END
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _certified_turn_plan_latch
    ):
        transaction_action = _start_stranded_retreat_ko_bridge(obs)
        if transaction_action is not None:
            # The first activation created the latch after decision_signature
            # was computed.  Recompute once so an identical repeated callback
            # returns the exact cached RETREAT instead of advancing the latch.
            return _remember_action(_decision_signature(obs), transaction_action)

    if (
        not turn_plan_delegated
        and context == SelectContext.MAIN
        and len(chosen_action) == 1
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _certified_turn_plan_latch
    ):
        transaction_action = _start_evolve_active_ready(
            obs, select.option[chosen_action[0]]
        )
        if transaction_action is not None:
            return _remember_action(
                _decision_signature(obs), transaction_action
            )

    if (
        context == SelectContext.MAIN
        and chosen_action
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _certified_turn_plan_latch
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
        or _certified_turn_plan_latch
        or turn_plan_delegated
    ):
        return _remember_action(
            _decision_signature(obs) if turn_plan_delegated else decision_signature,
            chosen_action,
        )
    _clear_decision_cache()
    return chosen_action


# ---------------------------------------------------------------------------
# NEXT_TURN_DRAW_SURVIVAL_CERTIFICATE
#
# The frozen exact-v3 policy above remains the first policy evaluated.  The
# public entry point below may replace only its finalized selection of one
# engine-verified fixed draw effect that would leave no card for the next
# turn.  Replacement choices are restricted to an already legal attack or the
# unique legal END option.  No generic score or ``safe_draws`` value changes.
# ---------------------------------------------------------------------------

_draw_survival_last_observation = None
_draw_survival_last_action = None


def _clear_draw_survival_wrapper_cache() -> None:
    global _draw_survival_last_observation, _draw_survival_last_action
    _draw_survival_last_observation = None
    _draw_survival_last_action = None


def _draw_survival_remember(observation: dict, action: list[int]) -> list[int]:
    global _draw_survival_last_observation, _draw_survival_last_action
    _draw_survival_last_observation = copy.deepcopy(observation)
    _draw_survival_last_action = tuple(action)
    return list(action)


def _draw_survival_snapshot_parent_state() -> dict:
    return {
        "pre_turn": pre_turn,
        "ability_used_dudunsparce": ability_used_dudunsparce,
        "ability_used_fezandipiti": ability_used_fezandipiti,
        "hilda": copy.deepcopy(_hilda_source_latch),
        "enriching": copy.deepcopy(_enriching_reserve_latch),
        "fez": copy.deepcopy(_fez_ko_bridge_latch),
        "active_psychic": copy.deepcopy(_active_psychic_ko_latch),
        "stranded": copy.deepcopy(_stranded_retreat_ko_latch),
        "certified_turn_plan": copy.deepcopy(_certified_turn_plan_latch),
        "decision_signature": copy.deepcopy(_last_decision_signature),
        "decision_action": copy.deepcopy(_last_decision_action),
    }


def _draw_survival_restore_parent_state(snapshot: dict) -> None:
    global pre_turn, ability_used_dudunsparce, ability_used_fezandipiti
    global _last_decision_signature, _last_decision_action
    pre_turn = snapshot["pre_turn"]
    ability_used_dudunsparce = snapshot["ability_used_dudunsparce"]
    ability_used_fezandipiti = snapshot["ability_used_fezandipiti"]
    for latch, key in (
        (_hilda_source_latch, "hilda"),
        (_enriching_reserve_latch, "enriching"),
        (_fez_ko_bridge_latch, "fez"),
        (_active_psychic_ko_latch, "active_psychic"),
        (_stranded_retreat_ko_latch, "stranded"),
        (_certified_turn_plan_latch, "certified_turn_plan"),
    ):
        latch.clear()
        latch.update(copy.deepcopy(snapshot[key]))
    _last_decision_signature = copy.deepcopy(snapshot["decision_signature"])
    _last_decision_action = copy.deepcopy(snapshot["decision_action"])


def _draw_survival_inherited_latch_active(snapshot: dict) -> bool:
    return any(
        bool(snapshot[key])
        for key in (
            "hilda",
            "enriching",
            "fez",
            "active_psychic",
            "stranded",
            "certified_turn_plan",
        )
    )


def _draw_survival_card_is_exact(card, player_index: int) -> bool:
    return (
        card is not None
        and isinstance(getattr(card, "id", None), int)
        and card.id > 0
        and card_table.get(card.id) is not None
        and isinstance(getattr(card, "serial", None), int)
        and card.serial > 0
        and getattr(card, "playerIndex", None) == player_index
    )


def _draw_survival_pokemon_is_exact(pokemon, player_index: int) -> bool:
    if (
        pokemon is None
        or not isinstance(getattr(pokemon, "id", None), int)
        or pokemon.id <= 0
        or card_table.get(pokemon.id) is None
        or not isinstance(getattr(pokemon, "serial", None), int)
        or pokemon.serial <= 0
        or not isinstance(getattr(pokemon, "hp", None), int)
        or not isinstance(getattr(pokemon, "maxHp", None), int)
        or pokemon.hp <= 0
        or pokemon.maxHp <= 0
        or pokemon.hp > pokemon.maxHp
        or not isinstance(getattr(pokemon, "appearThisTurn", None), bool)
        or not isinstance(pokemon.energies, list)
        or not isinstance(pokemon.energyCards, list)
        or not isinstance(pokemon.tools, list)
        or not isinstance(pokemon.preEvolution, list)
        or len(pokemon.energies) != len(pokemon.energyCards)
    ):
        return False
    if not all(
        _draw_survival_card_is_exact(card, player_index)
        for card in (
            list(pokemon.energyCards)
            + list(pokemon.tools)
            + list(pokemon.preEvolution)
        )
    ):
        return False
    if not all(
        card_table[card.id].cardType
        in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY)
        for card in pokemon.energyCards
    ):
        return False
    if not all(card_table[card.id].cardType == CardType.TOOL for card in pokemon.tools):
        return False
    serials = _bridge_pokemon_component_serials(pokemon)
    return len(serials) == len(set(serials))


def _draw_survival_known_stack_is_exact(pokemon, player_index: int) -> bool:
    if not _draw_survival_pokemon_is_exact(pokemon, player_index):
        return False
    pre_ids = [card.id for card in pokemon.preEvolution]
    if pokemon.id == Abra:
        return not pre_ids
    if pokemon.id == Kadabra:
        return pre_ids == [Abra]
    if pokemon.id == Alakazam:
        return pre_ids in ([Abra], [Abra, Kadabra])
    if pokemon.id == Dunsparce:
        return not pre_ids
    if pokemon.id == Dudunsparce:
        return pre_ids == [Dunsparce]
    data = card_table[pokemon.id]
    return (data.basic and not pre_ids) or (
        (data.stage1 or data.stage2) and bool(pre_ids)
    )


def _draw_survival_exact_hand(mine, player_index: int) -> tuple | None:
    if mine.hand is None or len(mine.hand) != mine.handCount:
        return None
    rows = []
    for card in mine.hand:
        if not _draw_survival_card_is_exact(card, player_index):
            return None
        rows.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def _draw_survival_field_rows(player, player_index: int) -> tuple | None:
    rows = []
    for area, pokemon_list in (
        (AreaType.ACTIVE, player.active),
        (AreaType.BENCH, player.bench),
    ):
        for pokemon in pokemon_list:
            if pokemon is None or not _draw_survival_known_stack_is_exact(
                pokemon, player_index
            ):
                return None
            rows.append((pokemon.serial, int(area), _bridge_pokemon_fingerprint(pokemon)))
    if len({row[0] for row in rows}) != len(rows):
        return None
    return tuple(sorted(rows, key=lambda row: row[:2]))


def _draw_survival_public_state_is_complete(obs: Observation) -> bool:
    state = obs.current
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or len(state.players) != 2
        or not isinstance(state.turn, int)
        or state.turn <= 0
        or not isinstance(state.turnActionCount, int)
        or state.turnActionCount < 0
        or state.result != -1
        or not isinstance(state.stadium, list)
        or any(
            not isinstance(value, bool)
            for value in (
                state.supporterPlayed,
                state.stadiumPlayed,
                state.energyAttached,
                state.retreated,
            )
        )
    ):
        return False
    mine = state.players[state.yourIndex]
    theirs = state.players[1 - state.yourIndex]
    if (
        _draw_survival_exact_hand(mine, state.yourIndex) is None
        or not isinstance(mine.deckCount, int)
        or mine.deckCount < 0
        or not 1 <= len(mine.prize) <= 6
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or _draw_survival_field_rows(mine, state.yourIndex) is None
        or _draw_survival_field_rows(theirs, 1 - state.yourIndex) is None
        or any(
            not isinstance(value, bool)
            for player in (mine, theirs)
            for value in (
                player.poisoned,
                player.burned,
                player.asleep,
                player.paralyzed,
                player.confused,
            )
        )
    ):
        return False
    for owner, player in enumerate(state.players):
        if not isinstance(player.discard, list) or any(
            not _draw_survival_card_is_exact(card, owner) for card in player.discard
        ):
            return False
        for card in player.prize:
            if card is not None and not _draw_survival_card_is_exact(card, owner):
                return False
    if any(
        not _draw_survival_card_is_exact(card, card.playerIndex)
        or card.playerIndex not in (0, 1)
        for card in state.stadium
    ):
        return False
    public_serials = _bridge_public_serials(state)
    return (
        all(isinstance(serial, int) and serial > 0 for serial in public_serials)
        and len(public_serials) == len(set(public_serials))
    )


def _draw_survival_fixed_metadata_certified() -> bool:
    expected = {
        Kadabra: (
            " Psychic Draw",
            "Once during your turn, when you play this Pok\u00e9mon from your hand "
            "to evolve 1 of your Pok\u00e9mon, you may use this Ability. Draw 2 cards.",
        ),
        Alakazam: (
            " Psychic Draw",
            "Once during your turn, when you play this Pok\u00e9mon from your hand "
            "to evolve 1 of your Pok\u00e9mon, you may use this Ability. Draw 3 cards.",
        ),
        Enriching_Energy: (
            "Enriching Energy",
            "As long as this card is attached to a Pok\u00e9mon, it provides {C} Energy.\n\n"
            "When you attach this card from your hand to a Pok\u00e9mon, draw 4 cards.",
        ),
        Dudunsparce: (
            "Run Away Draw",
            "Once during your turn, you may draw 3 cards. If you drew any cards "
            "in this way, shuffle this Pok\u00e9mon and all attached cards into your deck.",
        ),
        Fezandipiti_ex: (
            "Flip the Script",
            "Once during your turn, if any of your Pok\u00e9mon were Knocked Out during "
            "your opponent\u2019s last turn, you may draw 3 cards. You can\u2019t use more "
            "than 1 Flip the Script Ability each turn.",
        ),
    }
    for card_id, (name, text) in expected.items():
        data = card_table.get(card_id)
        if data is None or len(data.skills or []) != 1:
            return False
        skill = data.skills[0]
        if skill.name != name or skill.text != text:
            return False
    return True


def _draw_survival_option_unused_fields_are_none(option, allowed: set[str]) -> bool:
    fields = (
        "number",
        "area",
        "index",
        "playerIndex",
        "toolIndex",
        "energyIndex",
        "count",
        "inPlayArea",
        "inPlayIndex",
        "attackId",
        "cardId",
        "serial",
        "specialConditionType",
    )
    return all(name in allowed or getattr(option, name, None) is None for name in fields)


def _draw_survival_yes_no_indices(select) -> tuple[int, int] | None:
    if (
        select.minCount != 1
        or select.maxCount != 1
        or len(select.option) != 2
        or any(
            option.type not in (OptionType.YES, OptionType.NO)
            or not _draw_survival_option_unused_fields_are_none(option, set())
            for option in select.option
        )
    ):
        return None
    yes = [index for index, option in enumerate(select.option) if option.type == OptionType.YES]
    no = [index for index, option in enumerate(select.option) if option.type == OptionType.NO]
    return (yes[0], no[0]) if len(yes) == len(no) == 1 else None


def _draw_survival_field_card(mine, area, index):
    if area == AreaType.ACTIVE:
        cards = mine.active
    elif area == AreaType.BENCH:
        cards = mine.bench
    else:
        return None
    if not isinstance(index, int) or index < 0 or index >= len(cards):
        return None
    return cards[index]


def _draw_survival_dudunsparce_return_count(
    state, pokemon, player_index: int
) -> int | None:
    """Return 1 + preEvolution + Energy + Tools after exact stack validation."""
    if (
        pokemon.id != Dudunsparce
        or not _draw_survival_known_stack_is_exact(pokemon, player_index)
        or len(pokemon.preEvolution) != 1
        or pokemon.preEvolution[0].id != Dunsparce
    ):
        return None
    components = (
        [pokemon]
        + list(pokemon.preEvolution)
        + list(pokemon.energyCards)
        + list(pokemon.tools)
    )
    serials = [card.serial for card in components]
    if (
        len(serials) != len(set(serials))
        or not _bridge_protected_serials_are_unique(state, serials)
    ):
        return None
    return len(components)


def _draw_survival_projected_deck(
    deck_count: int, draw_count: int, return_count: int = 0
) -> int:
    return deck_count - min(deck_count, draw_count) + return_count


def _draw_survival_selected_main_effect(
    obs: Observation, parent_action: list[int]
) -> dict | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    if (
        select.context != SelectContext.MAIN
        or select.contextCard is not None
        or select.effect is not None
        or select.deck is not None
        or select.minCount != 1
        or select.maxCount != 1
        or len(parent_action) != 1
        or not 0 <= parent_action[0] < len(select.option)
    ):
        return None
    option_index = parent_action[0]
    option = select.option[option_index]
    effect = None

    if option.type == OptionType.EVOLVE:
        if (
            option.area != AreaType.HAND
            or option.inPlayArea not in (AreaType.ACTIVE, AreaType.BENCH)
            or option.playerIndex not in (None, my_index)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex", "inPlayArea", "inPlayIndex", "cardId", "serial"}
            )
            or not isinstance(option.index, int)
            or option.index < 0
            or option.index >= len(mine.hand)
        ):
            return None
        evolution = mine.hand[option.index]
        target = _draw_survival_field_card(mine, option.inPlayArea, option.inPlayIndex)
        if (
            not _draw_survival_card_is_exact(evolution, my_index)
            or evolution.id not in (Kadabra, Alakazam)
            or option.cardId not in (None, evolution.id)
            or option.serial not in (None, evolution.serial)
            or target is None
            or not _draw_survival_known_stack_is_exact(target, my_index)
            or (evolution.id == Kadabra and target.id != Abra)
            or (evolution.id == Alakazam and target.id != Kadabra)
        ):
            return None
        effect = {
            "kind": "kadabra_psychic_draw" if evolution.id == Kadabra else "alakazam_psychic_draw",
            "draw_count": 2 if evolution.id == Kadabra else 3,
            "selected_card": _bridge_card_fingerprint(evolution),
            "selected_hand_index": option.index,
            "source_serial": evolution.serial,
            "target_serial": target.serial,
            "target_area": int(option.inPlayArea),
            "target_index": option.inPlayIndex,
            "pre_target_fingerprint": _bridge_pokemon_fingerprint(target),
            "excluded_field_serial": target.serial,
        }

    elif option.type == OptionType.ATTACH:
        if (
            option.area != AreaType.HAND
            or option.inPlayArea not in (AreaType.ACTIVE, AreaType.BENCH)
            or option.playerIndex not in (None, my_index)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex", "inPlayArea", "inPlayIndex", "cardId", "serial"}
            )
            or not isinstance(option.index, int)
            or option.index < 0
            or option.index >= len(mine.hand)
        ):
            return None
        energy = mine.hand[option.index]
        target = _draw_survival_field_card(mine, option.inPlayArea, option.inPlayIndex)
        if (
            not _draw_survival_card_is_exact(energy, my_index)
            or energy.id != Enriching_Energy
            or option.cardId not in (None, energy.id)
            or option.serial not in (None, energy.serial)
            or target is None
            or not _draw_survival_known_stack_is_exact(target, my_index)
        ):
            return None
        effect = {
            "kind": "enriching_attachment",
            "draw_count": 4,
            "selected_card": _bridge_card_fingerprint(energy),
            "selected_hand_index": option.index,
            "source_serial": energy.serial,
            "target_serial": target.serial,
            "target_area": int(option.inPlayArea),
            "target_index": option.inPlayIndex,
            "pre_target_fingerprint": _bridge_pokemon_fingerprint(target),
            "excluded_field_serial": target.serial,
        }

    elif option.type == OptionType.ABILITY:
        if (
            option.area not in (AreaType.ACTIVE, AreaType.BENCH)
            or option.playerIndex not in (None, my_index)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex", "cardId", "serial"}
            )
        ):
            return None
        source = _draw_survival_field_card(mine, option.area, option.index)
        if (
            source is None
            or not _draw_survival_known_stack_is_exact(source, my_index)
            or option.cardId not in (None, source.id)
            or option.serial not in (None, source.serial)
        ):
            return None
        if source.id == Dudunsparce:
            returned = _draw_survival_dudunsparce_return_count(
                state, source, my_index
            )
            if returned is None:
                return None
            effect = {
                "kind": "dudunsparce_run_away_draw",
                "draw_count": 3,
                "return_count": returned,
                "source_serial": source.serial,
                "source_fingerprint": _bridge_pokemon_fingerprint(source),
                "excluded_field_serial": source.serial,
            }
        elif source.id == Fezandipiti_ex:
            effect = {
                "kind": "fezandipiti_draw",
                "draw_count": 3,
                "return_count": 0,
                "source_serial": source.serial,
                "source_fingerprint": _bridge_pokemon_fingerprint(source),
                "excluded_field_serial": None,
            }
        else:
            return None
    else:
        return None

    hand = _draw_survival_exact_hand(mine, my_index)
    if hand is None:
        return None
    selected = effect.get("selected_card")
    if selected is None:
        carried = hand
        post_hand_count = len(hand) + min(mine.deckCount, effect["draw_count"])
    else:
        selected_index = effect["selected_hand_index"]
        if hand[selected_index] != selected or hand.count(selected) != 1:
            return None
        carried = hand[:selected_index] + hand[selected_index + 1 :]
        post_hand_count = len(carried) + min(mine.deckCount, effect["draw_count"])
    effect.update(
        option_index=option_index,
        pre_hand=hand,
        carried_hand=carried,
        pre_hand_count=len(hand),
        post_hand_count=post_hand_count,
        pre_deck=mine.deckCount,
        projected_deck=_draw_survival_projected_deck(
            mine.deckCount,
            effect["draw_count"],
            effect.get("return_count", 0),
        ),
    )
    return effect


def _draw_survival_psychic_activate_no(
    obs: Observation, parent_action: list[int]
) -> int | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    context_card = select.contextCard
    if (
        select.context != SelectContext.ACTIVATE
        or select.effect is not None
        or select.deck is not None
        or context_card is None
        or context_card.id not in (Kadabra, Alakazam)
        or not _draw_survival_card_is_exact(context_card, my_index)
        or mine.deckCount <= 0
    ):
        return None
    yes_no = _draw_survival_yes_no_indices(select)
    if yes_no is None:
        return None
    yes, no = yes_no
    if parent_action != [yes]:
        return None
    matches = [
        pokemon
        for pokemon in list(mine.active) + list(mine.bench)
        if pokemon.serial == context_card.serial
        and pokemon.id == context_card.id
        and _draw_survival_known_stack_is_exact(pokemon, my_index)
    ]
    if len(matches) != 1:
        return None
    draws = 2 if context_card.id == Kadabra else 3
    return no if _draw_survival_projected_deck(mine.deckCount, draws) < 1 else None


def _draw_survival_attack_option_is_exact(option) -> bool:
    return (
        option.type == OptionType.ATTACK
        and isinstance(option.attackId, int)
        and option.attackId > 0
        and _draw_survival_option_unused_fields_are_none(option, {"attackId"})
    )


def _draw_survival_end_option_is_exact(option) -> bool:
    return option.type == OptionType.END and _draw_survival_option_unused_fields_are_none(
        option, set()
    )


def _draw_survival_counter_target_is_clear(obs: Observation, target) -> bool:
    state = obs.current
    opponent_index = 1 - state.yourIndex
    if not _powerful_hand_target_is_publicly_clear(state, target):
        return False
    public_sources = []
    theirs = state.players[opponent_index]
    for pokemon in list(theirs.active) + list(theirs.bench):
        public_sources.append(pokemon.id)
        public_sources.extend(card.id for card in pokemon.tools)
        public_sources.extend(card.id for card in pokemon.energyCards)
    public_sources.extend(card.id for card in state.stadium)
    for card_id in public_sources:
        data = card_table.get(card_id)
        if data is None:
            return False
        for skill in data.skills or []:
            normalized = " ".join((skill.text or "").lower().split())
            if (
                "prevent all effects of attacks" in normalized
                or "prevent all damage from and effects of attacks" in normalized
            ):
                if card_id not in (Mist_Energy, Rock_Fighting_Energy):
                    return False
    # Acerola's Mischief has a public one-turn attack-effect shield, but the
    # checked observation does not expose its chosen target unambiguously.
    if any(
        getattr(log, "cardId", None) == 1228
        and getattr(log, "playerIndex", None) == opponent_index
        for log in obs.logs
    ):
        return False
    return True


def _draw_survival_ready_active_and_target(obs: Observation) -> dict | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0]
    target = theirs.active[0]
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    attacks = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK
        and option.attackId == ATTACK_POWERFUL_HAND
        and _draw_survival_attack_option_is_exact(option)
    ]
    if (
        select.context != SelectContext.MAIN
        or select.minCount != 1
        or select.maxCount != 1
        or len(attacks) != 1
        or active.id != Alakazam
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or card_table[Alakazam].attacks != [ATTACK_POWERFUL_HAND]
        or powerful is None
        or powerful.name != "Powerful Hand"
        or powerful.text
        != "Place 2 damage counters on your opponent\u2019s Active Pok\u00e9mon for each card in your hand."
        or powerful.damage != 0
        or powerful.energies != [int(EnergyType.PSYCHIC)]
        or not any(
            card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards
        )
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or not _draw_survival_pokemon_is_exact(target, 1 - my_index)
        or not _draw_survival_counter_target_is_clear(obs, target)
    ):
        return None
    target_prizes = prize_count(target)
    terminal = target_prizes >= len(mine.prize) or not theirs.bench
    if target_prizes <= 0 or not terminal:
        return None
    return {
        "attack_index": attacks[0],
        "active": active,
        "target": target,
        "target_prizes": target_prizes,
    }


def _draw_survival_conserved_field_rows(
    rows: tuple, excluded_serial: int | None
) -> tuple:
    return tuple(row for row in rows if row[0] != excluded_serial)


def _draw_survival_start_terminal_latch(
    obs: Observation, effect: dict
) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    attack = _draw_survival_ready_active_and_target(obs)
    own_rows = _draw_survival_field_rows(mine, my_index)
    opponent_rows = _draw_survival_field_rows(theirs, 1 - my_index)
    target = attack["target"] if attack is not None else None
    if (
        attack is None
        or own_rows is None
        or opponent_rows is None
        or effect["projected_deck"] >= 1
        or 20 * effect["pre_hand_count"] >= target.hp
        or 20 * effect["post_hand_count"] < target.hp
    ):
        return False
    excluded = effect.get("excluded_field_serial")
    _draw_survival_terminal_latch.update(
        stage="await_effect_resolution",
        activation_confirmed=False,
        turn=state.turn,
        player=my_index,
        start_action_count=state.turnActionCount,
        kind=effect["kind"],
        draw_count=effect["draw_count"],
        pre_deck=effect["pre_deck"],
        expected_deck=effect["projected_deck"],
        pre_hand_count=effect["pre_hand_count"],
        carried_hand=effect["carried_hand"],
        expected_hand_count=effect["post_hand_count"],
        selected_card=effect.get("selected_card"),
        source_serial=effect.get("source_serial"),
        source_fingerprint=effect.get("source_fingerprint"),
        target_serial=effect.get("target_serial"),
        target_area=effect.get("target_area"),
        target_index=effect.get("target_index"),
        pre_target_fingerprint=effect.get("pre_target_fingerprint"),
        conserved_own_field=_draw_survival_conserved_field_rows(
            own_rows, excluded
        ),
        expected_own_field_count=len(own_rows),
        opponent_field=opponent_rows,
        active_serial=attack["active"].serial,
        active_fingerprint=_bridge_pokemon_fingerprint(attack["active"]),
        opponent_active_serial=target.serial,
        opponent_target_fingerprint=_bridge_target_fingerprint(target, theirs),
        target_prizes=attack["target_prizes"],
        own_prize_count=len(mine.prize),
        opponent_prize_count=len(theirs.prize),
        opponent_bench_count=len(theirs.bench),
        mine_discard=tuple(_bridge_card_fingerprint(card) for card in mine.discard),
        opponent_discard=tuple(
            _bridge_card_fingerprint(card) for card in theirs.discard
        ),
        stadium=tuple(_bridge_card_fingerprint(card) for card in state.stadium),
        mine_status=(
            mine.poisoned,
            mine.burned,
            mine.asleep,
            mine.paralyzed,
            mine.confused,
        ),
        opponent_status=(
            theirs.poisoned,
            theirs.burned,
            theirs.asleep,
            theirs.paralyzed,
            theirs.confused,
        ),
        supporter_played=state.supporterPlayed,
        stadium_played=state.stadiumPlayed,
        energy_attached_before=state.energyAttached,
        retreated=state.retreated,
        bench_max=mine.benchMax,
    )
    return True


def _draw_survival_common_terminal_state(obs: Observation, latch: dict) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if len(theirs.active) == 1 else None
    return (
        state.turn == latch.get("turn")
        and my_index == latch.get("player")
        and state.result == -1
        and len(mine.prize) == latch.get("own_prize_count")
        and len(theirs.prize) == latch.get("opponent_prize_count")
        and len(theirs.bench) == latch.get("opponent_bench_count")
        and mine.benchMax == latch.get("bench_max")
        and tuple(_bridge_card_fingerprint(card) for card in mine.discard)
        == latch.get("mine_discard")
        and tuple(_bridge_card_fingerprint(card) for card in theirs.discard)
        == latch.get("opponent_discard")
        and tuple(_bridge_card_fingerprint(card) for card in state.stadium)
        == latch.get("stadium")
        and (
            mine.poisoned,
            mine.burned,
            mine.asleep,
            mine.paralyzed,
            mine.confused,
        )
        == latch.get("mine_status")
        and (
            theirs.poisoned,
            theirs.burned,
            theirs.asleep,
            theirs.paralyzed,
            theirs.confused,
        )
        == latch.get("opponent_status")
        and state.supporterPlayed == latch.get("supporter_played")
        and state.stadiumPlayed == latch.get("stadium_played")
        and state.retreated == latch.get("retreated")
        and target is not None
        and target.serial == latch.get("opponent_active_serial")
        and _bridge_target_fingerprint(target, theirs)
        == latch.get("opponent_target_fingerprint")
        and prize_count(target) == latch.get("target_prizes")
        and _draw_survival_counter_target_is_clear(obs, target)
        and _draw_survival_field_rows(theirs, 1 - my_index)
        == latch.get("opponent_field")
    )


def _draw_survival_evolved_source(obs: Observation, latch: dict):
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    selected = latch.get("selected_card")
    if selected is None:
        return None
    matches = [
        pokemon
        for pokemon in list(mine.active) + list(mine.bench)
        if pokemon.serial == selected[1]
        and pokemon.id == selected[0]
        and _draw_survival_known_stack_is_exact(pokemon, my_index)
    ]
    if len(matches) != 1:
        return None
    evolved = matches[0]
    pre = latch.get("pre_target_fingerprint")
    if pre is None:
        return None
    old_id, old_serial, old_hp, old_max_hp, old_appear = pre[:5]
    old_energies, old_energy_cards, old_tools, old_pre = pre[6:10]
    expected_pre = tuple(old_pre) + ((old_id, old_serial, my_index),)
    expected_max_hp = card_table[evolved.id].hp
    expected_hp = expected_max_hp - (old_max_hp - old_hp)
    if (
        evolved.hp != expected_hp
        or evolved.maxHp != expected_max_hp
        or evolved.appearThisTurn != old_appear
        or tuple(int(energy) for energy in evolved.energies) != old_energies
        or tuple(_bridge_card_fingerprint(card) for card in evolved.energyCards)
        != old_energy_cards
        or tuple(_bridge_card_fingerprint(card) for card in evolved.tools) != old_tools
        or tuple(_bridge_card_fingerprint(card) for card in evolved.preEvolution)
        != expected_pre
    ):
        return None
    rows = _draw_survival_field_rows(mine, my_index)
    if (
        rows is None
        or len(rows) != latch.get("expected_own_field_count")
        or _draw_survival_conserved_field_rows(rows, evolved.serial)
        != latch.get("conserved_own_field")
    ):
        return None
    return evolved


def _draw_survival_validate_evolution_prompt(
    obs: Observation, latch: dict
) -> int | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    if (
        not _draw_survival_common_terminal_state(obs, latch)
        or select.context != SelectContext.ACTIVATE
        or select.effect is not None
        or select.deck is not None
        or state.turnActionCount <= latch.get("start_action_count")
        or mine.deckCount != latch.get("pre_deck")
        or _draw_survival_exact_hand(mine, my_index) != latch.get("carried_hand")
    ):
        return None
    context_card = select.contextCard
    if (
        context_card is None
        or not _draw_survival_card_is_exact(context_card, my_index)
        or _bridge_card_fingerprint(context_card) != latch.get("selected_card")
    ):
        return None
    yes_no = _draw_survival_yes_no_indices(select)
    evolved = _draw_survival_evolved_source(obs, latch)
    if yes_no is None or evolved is None:
        return None
    active = mine.active[0]
    if (
        active.serial != latch.get("active_serial")
        or _bridge_pokemon_fingerprint(active) != latch.get("active_fingerprint")
    ):
        return None
    latch["activation_confirmed"] = True
    latch["resolved_field"] = _draw_survival_field_rows(mine, my_index)
    latch["effect_prompt_action_count"] = state.turnActionCount
    return yes_no[0]


def _draw_survival_hand_has_exact_carry(
    mine, player_index: int, carried: tuple, expected_count: int
) -> bool:
    hand = _draw_survival_exact_hand(mine, player_index)
    if hand is None or len(hand) != expected_count:
        return False
    carried_set = set(carried)
    hand_set = set(hand)
    if len(carried_set) != len(carried) or not carried_set <= hand_set:
        return False
    new_rows = [row for row in hand if row not in carried_set]
    return len(new_rows) == expected_count - len(carried)


def _draw_survival_validate_enriching_target(obs: Observation, latch: dict) -> bool:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    target = next(
        (
            pokemon
            for pokemon in list(mine.active) + list(mine.bench)
            if pokemon.serial == latch.get("target_serial")
        ),
        None,
    )
    if target is None or not _draw_survival_known_stack_is_exact(target, my_index):
        return False
    pre = latch.get("pre_target_fingerprint")
    selected = latch.get("selected_card")
    if pre is None or selected is None:
        return False
    current_energy = tuple(_bridge_card_fingerprint(card) for card in target.energyCards)
    expected_energy = tuple(pre[7]) + (selected,)
    if (
        target.id != pre[0]
        or target.serial != pre[1]
        or target.hp != pre[2]
        or target.maxHp != pre[3]
        or target.appearThisTurn != pre[4]
        or sorted(int(energy) for energy in target.energies)
        != sorted(tuple(pre[6]) + (int(EnergyType.COLORLESS),))
        or sorted(current_energy) != sorted(expected_energy)
        or current_energy.count(selected) != 1
        or tuple(_bridge_card_fingerprint(card) for card in target.tools) != pre[8]
        or tuple(_bridge_card_fingerprint(card) for card in target.preEvolution) != pre[9]
    ):
        return False
    rows = _draw_survival_field_rows(mine, my_index)
    return (
        rows is not None
        and len(rows) == latch.get("expected_own_field_count")
        and _draw_survival_conserved_field_rows(rows, target.serial)
        == latch.get("conserved_own_field")
    )


def _draw_survival_post_effect_is_exact(obs: Observation, latch: dict) -> bool:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    if (
        not _draw_survival_common_terminal_state(obs, latch)
        or select.context != SelectContext.MAIN
        or select.minCount != 1
        or select.maxCount != 1
        or state.turnActionCount <= latch.get("start_action_count")
        or mine.deckCount != latch.get("expected_deck")
        or not _draw_survival_hand_has_exact_carry(
            mine,
            my_index,
            latch.get("carried_hand") or (),
            latch.get("expected_hand_count"),
        )
        or 20 * mine.handCount < theirs.active[0].hp
    ):
        return False
    active = mine.active[0]
    if (
        active.serial != latch.get("active_serial")
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or active.id != Alakazam
        or not any(card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards)
        or mine.asleep
        or mine.paralyzed
        or mine.confused
    ):
        return False
    kind = latch.get("kind")
    rows = _draw_survival_field_rows(mine, my_index)
    if kind in ("kadabra_psychic_draw", "alakazam_psychic_draw"):
        if (
            not latch.get("activation_confirmed")
            or rows != latch.get("resolved_field")
            or state.energyAttached != latch.get("energy_attached_before")
        ):
            return False
    elif kind == "enriching_attachment":
        if not state.energyAttached or not _draw_survival_validate_enriching_target(
            obs, latch
        ):
            return False
    elif kind == "fezandipiti_draw":
        if (
            rows != latch.get("conserved_own_field")
            or state.energyAttached != latch.get("energy_attached_before")
        ):
            return False
    else:
        return False
    powerful = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK
        and option.attackId == ATTACK_POWERFUL_HAND
        and _draw_survival_attack_option_is_exact(option)
    ]
    return len(powerful) == 1


def _draw_survival_advance_terminal_latch(
    obs: Observation,
) -> list[int] | None:
    if not _draw_survival_terminal_latch:
        return None
    latch = _draw_survival_terminal_latch
    stage = latch.get("stage")
    if stage == "await_resolution":
        _clear_draw_survival_terminal_latch()
        return None
    if stage == "await_effect_resolution":
        if latch.get("kind") in (
            "kadabra_psychic_draw",
            "alakazam_psychic_draw",
        ) and not latch.get("activation_confirmed"):
            yes = _draw_survival_validate_evolution_prompt(obs, latch)
            if yes is None:
                _clear_draw_survival_terminal_latch()
                return None
            return [yes]
        if not _draw_survival_post_effect_is_exact(obs, latch):
            _clear_draw_survival_terminal_latch()
            return None
        latch["stage"] = "await_attack"
        stage = "await_attack"
    if stage == "await_attack":
        if not _draw_survival_post_effect_is_exact(obs, latch):
            _clear_draw_survival_terminal_latch()
            return None
        matches = [
            index
            for index, option in enumerate(obs.select.option)
            if option.type == OptionType.ATTACK
            and option.attackId == ATTACK_POWERFUL_HAND
            and _draw_survival_attack_option_is_exact(option)
        ]
        if len(matches) != 1:
            _clear_draw_survival_terminal_latch()
            return None
        latch["stage"] = "await_resolution"
        return [matches[0]]
    _clear_draw_survival_terminal_latch()
    return None


def _draw_survival_rerun_parent(
    obs_dict: dict, before_parent: dict, allowed_indices: list[int]
) -> list[int] | None:
    reranked = copy.deepcopy(obs_dict)
    raw_select = reranked.get("select")
    if not isinstance(raw_select, dict):
        return None
    raw_options = raw_select.get("option")
    if (
        not isinstance(raw_options, list)
        or not allowed_indices
        or len(allowed_indices) != len(set(allowed_indices))
        or any(
            not isinstance(index, int) or index < 0 or index >= len(raw_options)
            for index in allowed_indices
        )
        or raw_select.get("minCount") != 1
        or raw_select.get("maxCount") != 1
    ):
        return None
    raw_select["option"] = [raw_options[index] for index in allowed_indices]
    _draw_survival_restore_parent_state(before_parent)
    reranked_action = _source_transition_v2_parent_agent(reranked)
    if (
        not isinstance(reranked_action, list)
        or len(reranked_action) != 1
        or not isinstance(reranked_action[0], int)
        or not 0 <= reranked_action[0] < len(allowed_indices)
    ):
        return None
    return [allowed_indices[reranked_action[0]]]


def _draw_survival_attack_or_end_indices(obs: Observation) -> list[int] | None:
    attacks = []
    for index, option in enumerate(obs.select.option):
        if option.type == OptionType.ATTACK:
            if not _draw_survival_attack_option_is_exact(option):
                return None
            attacks.append(index)
    if attacks:
        return attacks
    ends = [
        index
        for index, option in enumerate(obs.select.option)
        if option.type == OptionType.END
    ]
    if len(ends) != 1 or not _draw_survival_end_option_is_exact(
        obs.select.option[ends[0]]
    ):
        return None
    return ends


def _draw_survival_prepare_overlay(obs_dict: dict) -> None:
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    if select is None or not isinstance(current, dict):
        _clear_draw_survival_terminal_latch()
        return
    turn = current.get("turn")
    player = current.get("yourIndex")
    result = current.get("result")
    context = select.get("context") if isinstance(select, dict) else None
    if (
        turn == 0
        or result != -1
        or context
        in (
            int(SelectContext.IS_FIRST),
            int(SelectContext.MULLIGAN),
            int(SelectContext.SETUP_ACTIVE_POKEMON),
            int(SelectContext.SETUP_BENCH_POKEMON),
        )
    ):
        _clear_draw_survival_terminal_latch()
        return
    if _draw_survival_terminal_latch and (
        _draw_survival_terminal_latch.get("turn") != turn
        or _draw_survival_terminal_latch.get("player") != player
    ):
        _clear_draw_survival_terminal_latch()


def _draw_survival_v1_parent_agent(obs_dict: dict) -> list[int]:
    """Compute exact-v3 first, then apply the draw-survival transformer."""
    if (
        _draw_survival_last_observation is not None
        and obs_dict == _draw_survival_last_observation
        and _draw_survival_last_action is not None
    ):
        return list(_draw_survival_last_action)

    had_draw_transaction = bool(_draw_survival_terminal_latch)
    inherited_quarantine = bool(_merge_start_quarantine_depth)
    higher_owner = bool(
        _draw_free_terminal_evolution_latch
        or _enriching_zero_boss_lucario_latch
    )
    _draw_survival_prepare_overlay(obs_dict)
    stale_draw_cleared = (
        had_draw_transaction and not _draw_survival_terminal_latch
    )
    before_parent = _draw_survival_snapshot_parent_state()
    block_inner_start = bool(
        had_draw_transaction
        or stale_draw_cleared
        or higher_owner
        or inherited_quarantine
    )
    if block_inner_start:
        _merge_push_start_quarantine()
    try:
        parent_action = _source_transition_v2_parent_agent(
            copy.deepcopy(obs_dict)
        )
    finally:
        if block_inner_start:
            _merge_pop_start_quarantine()
    after_parent = _draw_survival_snapshot_parent_state()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return _draw_survival_remember(obs_dict, parent_action)

    try:
        obs = to_observation_class(copy.deepcopy(obs_dict))
        if (
            obs.current is None
            or obs.select is None
            or not isinstance(parent_action, list)
            or len(parent_action) < obs.select.minCount
            or len(parent_action) > obs.select.maxCount
            or len(parent_action) != len(set(parent_action))
            or any(
                not isinstance(index, int)
                or index < 0
                or index >= len(obs.select.option)
                for index in parent_action
            )
        ):
            return _draw_survival_remember(obs_dict, parent_action)

        if _draw_survival_inherited_latch_active(
            before_parent
        ) or _draw_survival_inherited_latch_active(after_parent):
            if had_draw_transaction:
                _clear_draw_survival_terminal_latch()
            return _draw_survival_remember(obs_dict, parent_action)

        if stale_draw_cleared or higher_owner or inherited_quarantine:
            return _draw_survival_remember(obs_dict, parent_action)

        if _draw_survival_terminal_latch:
            terminal_action = _draw_survival_advance_terminal_latch(obs)
            if terminal_action is None:
                return _draw_survival_remember(obs_dict, parent_action)
            if terminal_action != parent_action:
                replacement = _draw_survival_rerun_parent(
                    obs_dict, before_parent, terminal_action
                )
                if replacement != terminal_action:
                    _draw_survival_restore_parent_state(after_parent)
                    _clear_draw_survival_terminal_latch()
                    return _draw_survival_remember(obs_dict, parent_action)
            return _draw_survival_remember(obs_dict, terminal_action)

        if (
            not _draw_survival_fixed_metadata_certified()
            or not _draw_survival_public_state_is_complete(obs)
            or obs.current.players[obs.current.yourIndex].deckCount <= 0
        ):
            return _draw_survival_remember(obs_dict, parent_action)

        psychic_no = _draw_survival_psychic_activate_no(obs, parent_action)
        if psychic_no is not None:
            replacement = _draw_survival_rerun_parent(
                obs_dict, before_parent, [psychic_no]
            )
            if replacement == [psychic_no]:
                return _draw_survival_remember(obs_dict, replacement)
            _draw_survival_restore_parent_state(after_parent)
            return _draw_survival_remember(obs_dict, parent_action)

        effect = _draw_survival_selected_main_effect(obs, parent_action)
        if effect is None or effect["projected_deck"] >= 1:
            return _draw_survival_remember(obs_dict, parent_action)

        if _draw_survival_start_terminal_latch(obs, effect):
            return _draw_survival_remember(obs_dict, parent_action)

        allowed = _draw_survival_attack_or_end_indices(obs)
        if allowed is None:
            return _draw_survival_remember(obs_dict, parent_action)
        replacement = _draw_survival_rerun_parent(
            obs_dict, before_parent, allowed
        )
        if replacement is not None and replacement != parent_action:
            return _draw_survival_remember(obs_dict, replacement)
        if replacement == parent_action:
            return _draw_survival_remember(obs_dict, parent_action)
        _draw_survival_restore_parent_state(after_parent)
        return _draw_survival_remember(obs_dict, parent_action)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        _draw_survival_restore_parent_state(after_parent)
        _clear_draw_survival_terminal_latch()
        return _draw_survival_remember(obs_dict, parent_action)


# ---------------------------------------------------------------------------
# DRAW_FREE_TERMINAL_EVOLUTION
#
# V1 above remains the immediate parent policy.  This correction can restore
# only an exact-v3 Active Kadabra -> Alakazam selection that V1 replaced with
# END solely because Psychic Draw could consume the last deck card.  The
# restored route refuses that optional draw, attaches one already-visible
# Psychic Energy frozen at the start, and converts a fully certified terminal
# Powerful Hand.  It never treats an unseen card as a resource.
# ---------------------------------------------------------------------------

_draw_free_terminal_last_observation = None
_draw_free_terminal_last_action = None


def _clear_draw_free_terminal_wrapper_cache() -> None:
    global _draw_free_terminal_last_observation
    global _draw_free_terminal_last_action
    _draw_free_terminal_last_observation = None
    _draw_free_terminal_last_action = None


def _draw_free_terminal_remember(
    observation: dict, action: list[int]
) -> list[int]:
    global _draw_free_terminal_last_observation
    global _draw_free_terminal_last_action
    _draw_free_terminal_last_observation = copy.deepcopy(observation)
    _draw_free_terminal_last_action = tuple(action)
    return list(action)


def _draw_free_snapshot_v1_state() -> dict:
    snapshot = _draw_survival_snapshot_parent_state()
    snapshot.update(
        draw_survival_terminal=copy.deepcopy(
            _draw_survival_terminal_latch
        ),
        draw_survival_last_observation=copy.deepcopy(
            _draw_survival_last_observation
        ),
        draw_survival_last_action=copy.deepcopy(
            _draw_survival_last_action
        ),
    )
    return snapshot


def _draw_free_restore_v1_state(snapshot: dict) -> None:
    global _draw_survival_last_observation, _draw_survival_last_action
    _draw_survival_restore_parent_state(snapshot)
    _draw_survival_terminal_latch.clear()
    _draw_survival_terminal_latch.update(
        copy.deepcopy(snapshot["draw_survival_terminal"])
    )
    _draw_survival_last_observation = copy.deepcopy(
        snapshot["draw_survival_last_observation"]
    )
    _draw_survival_last_action = copy.deepcopy(
        snapshot["draw_survival_last_action"]
    )


def _draw_free_inherited_latch_active(snapshot: dict) -> bool:
    return _draw_survival_inherited_latch_active(snapshot) or bool(
        snapshot.get("draw_survival_terminal")
    )


def _draw_free_action_is_valid(obs: Observation, action) -> bool:
    select = obs.select
    return (
        select is not None
        and isinstance(action, list)
        and select.minCount <= len(action) <= select.maxCount
        and len(action) == len(set(action))
        and all(
            isinstance(index, int)
            and 0 <= index < len(select.option)
            for index in action
        )
    )


def _draw_free_prize_rows(player) -> tuple:
    return tuple(
        None if card is None else _bridge_card_fingerprint(card)
        for card in player.prize
    )


def _draw_free_status(player) -> tuple:
    return (
        player.poisoned,
        player.burned,
        player.asleep,
        player.paralyzed,
        player.confused,
    )


def _draw_free_without_exact_card(
    rows: tuple, fingerprint: tuple
) -> tuple | None:
    matches = [index for index, row in enumerate(rows) if row == fingerprint]
    if len(matches) != 1:
        return None
    index = matches[0]
    return rows[:index] + rows[index + 1 :]


def _draw_free_exact_main_envelope(select) -> bool:
    return (
        select.type == SelectType.MAIN
        and select.context == SelectContext.MAIN
        and select.minCount == 1
        and select.maxCount == 1
        and select.remainDamageCounter == 0
        and select.remainEnergyCost == 0
        and select.deck is None
        and select.contextCard is None
        and select.effect is None
    )


def _draw_free_exact_evolution_option(option) -> bool:
    return (
        option.type == OptionType.EVOLVE
        and option.area == AreaType.HAND
        and isinstance(option.index, int)
        and option.inPlayArea == AreaType.ACTIVE
        and option.inPlayIndex == 0
        and option.playerIndex is None
        and _draw_survival_option_unused_fields_are_none(
            option, {"area", "index", "inPlayArea", "inPlayIndex"}
        )
    )


def _draw_free_exact_attach_option(option) -> bool:
    return (
        option.type == OptionType.ATTACH
        and option.area == AreaType.HAND
        and isinstance(option.index, int)
        and option.inPlayArea == AreaType.ACTIVE
        and option.inPlayIndex == 0
        and option.playerIndex is None
        and _draw_survival_option_unused_fields_are_none(
            option, {"area", "index", "inPlayArea", "inPlayIndex"}
        )
    )


def _draw_free_card_at_hand_index(mine, index: int):
    hand = mine.hand
    if hand is None or index < 0 or index >= len(hand):
        return None
    return hand[index]


def _draw_free_option_for_hand_serial(
    obs: Observation,
    *,
    serial: int,
    option_kind: OptionType,
) -> list[int]:
    mine = obs.current.players[obs.current.yourIndex]
    matches = []
    for option_index, option in enumerate(obs.select.option):
        exact = (
            _draw_free_exact_evolution_option(option)
            if option_kind == OptionType.EVOLVE
            else _draw_free_exact_attach_option(option)
        )
        if not exact:
            continue
        card = _draw_free_card_at_hand_index(mine, option.index)
        if card is not None and card.serial == serial:
            matches.append(option_index)
    return matches


def _draw_free_energy_witness(
    obs: Observation, hand: tuple
) -> tuple[tuple, int] | None:
    candidates = []
    for row in hand:
        card_id, serial, player_index = row
        if card_id not in PSYCHIC_ENERGY_IDS:
            continue
        priority = 0 if card_id == Basic_Psychic_Energy else 1
        candidates.append((priority, serial, row, player_index))
    if not candidates:
        return None
    _, _, selected, player_index = min(candidates, key=lambda row: row[:2])
    if player_index != obs.current.yourIndex:
        return None
    if selected[0] == Telepath_Psychic_Energy and not (
        _active_psychic_telepath_text_certified()
    ):
        return None
    options = _draw_free_option_for_hand_serial(
        obs, serial=selected[1], option_kind=OptionType.ATTACH
    )
    return (selected, options[0]) if len(options) == 1 else None


def _draw_free_powerful_hand_metadata_certified() -> bool:
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    return (
        powerful is not None
        and card_table.get(Alakazam) is not None
        and card_table[Alakazam].attacks == [ATTACK_POWERFUL_HAND]
        and powerful.name == "Powerful Hand"
        and powerful.text
        == "Place 2 damage counters on your opponent\u2019s Active Pok\u00e9mon for each card in your hand."
        and powerful.damage == 0
        and powerful.energies == [int(EnergyType.PSYCHIC)]
    )


def _draw_free_target_cards(target, opponent_index: int) -> tuple:
    return (
        (target.id, target.serial, opponent_index),
        *(
            _bridge_card_fingerprint(card)
            for card in (
                list(target.preEvolution)
                + list(target.energyCards)
                + list(target.tools)
            )
        ),
    )


def _draw_free_start_terminal_evolution(
    obs: Observation,
    v1_action: list[int],
    exact_action: list[int],
    before_v1: dict,
    after_v1: dict,
    after_exact: dict,
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if len(mine.active) == 1 else None
    target = theirs.active[0] if len(theirs.active) == 1 else None
    if (
        not _draw_free_exact_main_envelope(select)
        or state.turn < 2
        or state.result != -1
        or state.energyAttached
        or state.looking is not None
        or mine.deckCount != 1
        or len(v1_action) != 1
        or not _draw_survival_end_option_is_exact(
            select.option[v1_action[0]]
        )
        or len(exact_action) != 1
        or any(
            _draw_free_inherited_latch_active(snapshot)
            for snapshot in (before_v1, after_v1, after_exact)
        )
        or _draw_free_terminal_evolution_latch
        or not _draw_survival_fixed_metadata_certified()
        or not _draw_free_powerful_hand_metadata_certified()
        or not _draw_survival_public_state_is_complete(obs)
        or active is None
        or active.id != Kadabra
        or active.appearThisTurn
        or active.energies
        or active.energyCards
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or [card.id for card in active.preEvolution] != [Abra]
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or target is None
        or not _draw_survival_known_stack_is_exact(
            target, 1 - my_index
        )
        or not _draw_survival_counter_target_is_clear(obs, target)
    ):
        return None

    exact_index = exact_action[0]
    exact_option = select.option[exact_index]
    if not _draw_free_exact_evolution_option(exact_option):
        return None
    evolution = _draw_free_card_at_hand_index(mine, exact_option.index)
    if (
        evolution is None
        or evolution.id != Alakazam
        or not _draw_survival_card_is_exact(evolution, my_index)
    ):
        return None
    evolution_options = _draw_free_option_for_hand_serial(
        obs, serial=evolution.serial, option_kind=OptionType.EVOLVE
    )
    if evolution_options != [exact_index]:
        return None

    hand = _draw_survival_exact_hand(mine, my_index)
    evolution_fingerprint = _bridge_card_fingerprint(evolution)
    if hand is None:
        return None
    hand_after_evolution = _draw_free_without_exact_card(
        hand, evolution_fingerprint
    )
    if hand_after_evolution is None:
        return None
    energy_witness = _draw_free_energy_witness(obs, hand_after_evolution)
    if energy_witness is None:
        return None
    energy_fingerprint, initial_energy_option = energy_witness
    hand_after_attach = _draw_free_without_exact_card(
        hand_after_evolution, energy_fingerprint
    )
    if hand_after_attach is None:
        return None

    expected_damage = 20 * len(hand_after_attach)
    target_prizes = prize_count(target)
    terminal_by_prize = target_prizes >= len(mine.prize)
    terminal_by_board = len(theirs.bench) == 0
    if (
        expected_damage < target.hp
        or target_prizes <= 0
        or not (terminal_by_prize or terminal_by_board)
    ):
        return None

    own_rows = _draw_survival_field_rows(mine, my_index)
    opponent_rows = _draw_survival_field_rows(
        theirs, 1 - my_index
    )
    if own_rows is None or opponent_rows is None:
        return None
    expected_evolved_hp = (
        active.hp + card_table[Alakazam].hp - active.maxHp
    )
    protected = (
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(target),
        evolution.serial,
        energy_fingerprint[1],
    )
    if (
        expected_evolved_hp <= 0
        or expected_evolved_hp > card_table[Alakazam].hp
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None

    _draw_free_terminal_evolution_latch.update(
        transaction="DRAW_FREE_TERMINAL_EVOLUTION",
        stage="await_activate_no",
        turn=state.turn,
        player=my_index,
        start_action_count=state.turnActionCount,
        expected_action_count=state.turnActionCount + 1,
        supporter_played=state.supporterPlayed,
        stadium_played=state.stadiumPlayed,
        retreated=state.retreated,
        bench_max=mine.benchMax,
        mine_status=_draw_free_status(mine),
        opponent_status=_draw_free_status(theirs),
        mine_discard=tuple(
            _bridge_card_fingerprint(card) for card in mine.discard
        ),
        opponent_discard=tuple(
            _bridge_card_fingerprint(card) for card in theirs.discard
        ),
        mine_prize=_draw_free_prize_rows(mine),
        opponent_prize=_draw_free_prize_rows(theirs),
        stadium=tuple(
            _bridge_card_fingerprint(card) for card in state.stadium
        ),
        start_hand=hand,
        hand_after_evolution=hand_after_evolution,
        hand_after_attach=hand_after_attach,
        selected_evolution_option=exact_index,
        selected_evolution_fingerprint=evolution_fingerprint,
        selected_energy_initial_option=initial_energy_option,
        selected_energy_fingerprint=energy_fingerprint,
        source_serial=active.serial,
        source_fingerprint=_bridge_pokemon_fingerprint(active),
        source_hp=active.hp,
        source_max_hp=active.maxHp,
        source_tools=tuple(
            _bridge_card_fingerprint(card) for card in active.tools
        ),
        source_pre_evolution=tuple(
            _bridge_card_fingerprint(card)
            for card in active.preEvolution
        ),
        expected_evolved_hp=expected_evolved_hp,
        own_conserved_field=tuple(
            row for row in own_rows if row[0] != active.serial
        ),
        own_field_count=len(own_rows),
        opponent_field=opponent_rows,
        opponent_bench_field=tuple(
            row for row in opponent_rows if row[1] == int(AreaType.BENCH)
        ),
        target_serial=target.serial,
        target_fingerprint=_bridge_target_fingerprint(target, theirs),
        target_cards=_draw_free_target_cards(
            target, 1 - my_index
        ),
        target_hp=target.hp,
        target_prizes=target_prizes,
        own_prize_count=len(mine.prize),
        opponent_prize_count=len(theirs.prize),
        opponent_bench_count=len(theirs.bench),
        expected_damage=expected_damage,
        terminal_by_prize=terminal_by_prize,
        terminal_by_board=terminal_by_board,
        telepath_prompt_seen=False,
    )
    return list(exact_action)


def _draw_free_evolved_active(
    obs: Observation, latch: dict, *, attached: bool
):
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    active = mine.active[0] if len(mine.active) == 1 else None
    evolution = latch.get("selected_evolution_fingerprint")
    energy = latch.get("selected_energy_fingerprint")
    expected_pre = tuple(latch.get("source_pre_evolution") or ()) + (
        (Kadabra, latch.get("source_serial"), my_index),
    )
    expected_energy_cards = (energy,) if attached else ()
    expected_energy_units = (
        (int(EnergyType.PSYCHIC),) if attached else ()
    )
    if (
        active is None
        or evolution is None
        or energy is None
        or active.id != Alakazam
        or active.serial != evolution[1]
        or active.hp != latch.get("expected_evolved_hp")
        or active.maxHp != card_table[Alakazam].hp
        or not active.appearThisTurn
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or tuple(int(unit) for unit in active.energies)
        != expected_energy_units
        or tuple(
            _bridge_card_fingerprint(card)
            for card in active.energyCards
        )
        != expected_energy_cards
        or tuple(
            _bridge_card_fingerprint(card) for card in active.tools
        )
        != latch.get("source_tools")
        or tuple(
            _bridge_card_fingerprint(card)
            for card in active.preEvolution
        )
        != expected_pre
    ):
        return None
    return active


def _draw_free_common_state_is_same(
    obs: Observation,
    latch: dict,
    *,
    expected_hand: tuple,
    expected_action_count: int,
    attached: bool,
) -> bool:
    if not _draw_survival_public_state_is_complete(obs):
        return False
    state = obs.current
    my_index = state.yourIndex
    if my_index not in (0, 1):
        return False
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    target = theirs.active[0] if len(theirs.active) == 1 else None
    active = _draw_free_evolved_active(obs, latch, attached=attached)
    own_rows = _draw_survival_field_rows(mine, my_index)
    return (
        state.turn == latch.get("turn")
        and my_index == latch.get("player")
        and state.turnActionCount == expected_action_count
        and state.result == -1
        and state.supporterPlayed == latch.get("supporter_played")
        and state.stadiumPlayed == latch.get("stadium_played")
        and state.energyAttached is attached
        and state.retreated == latch.get("retreated")
        and mine.deckCount == 1
        and mine.benchMax == latch.get("bench_max")
        and _draw_free_status(mine) == latch.get("mine_status")
        and _draw_free_status(theirs) == latch.get("opponent_status")
        and tuple(
            _bridge_card_fingerprint(card) for card in mine.discard
        )
        == latch.get("mine_discard")
        and tuple(
            _bridge_card_fingerprint(card) for card in theirs.discard
        )
        == latch.get("opponent_discard")
        and _draw_free_prize_rows(mine) == latch.get("mine_prize")
        and _draw_free_prize_rows(theirs)
        == latch.get("opponent_prize")
        and tuple(
            _bridge_card_fingerprint(card) for card in state.stadium
        )
        == latch.get("stadium")
        and _draw_survival_exact_hand(mine, my_index) == expected_hand
        and active is not None
        and own_rows is not None
        and len(own_rows) == latch.get("own_field_count")
        and tuple(
            row for row in own_rows if row[0] != active.serial
        )
        == latch.get("own_conserved_field")
        and target is not None
        and target.serial == latch.get("target_serial")
        and target.hp == latch.get("target_hp")
        and _bridge_target_fingerprint(target, theirs)
        == latch.get("target_fingerprint")
        and prize_count(target) == latch.get("target_prizes")
        and len(mine.prize) == latch.get("own_prize_count")
        and len(theirs.prize) == latch.get("opponent_prize_count")
        and len(theirs.bench) == latch.get("opponent_bench_count")
        and _draw_survival_field_rows(theirs, 1 - my_index)
        == latch.get("opponent_field")
        and _draw_survival_counter_target_is_clear(obs, target)
        and 20 * len(expected_hand) >= target.hp
    )


def _draw_free_log_has_exact_evolution(
    obs: Observation, latch: dict
) -> bool:
    selected = latch.get("selected_evolution_fingerprint")
    return selected is not None and any(
        int(getattr(log, "type", -1)) == 12
        and getattr(log, "playerIndex", None) == latch.get("player")
        and getattr(log, "cardId", None) == Alakazam
        and getattr(log, "serial", None) == selected[1]
        and getattr(log, "cardIdTarget", None) == Kadabra
        and getattr(log, "serialTarget", None)
        == latch.get("source_serial")
        for log in obs.logs
    )


def _draw_free_log_has_exact_attachment(
    obs: Observation, latch: dict
) -> bool:
    energy = latch.get("selected_energy_fingerprint")
    evolution = latch.get("selected_evolution_fingerprint")
    return energy is not None and evolution is not None and any(
        int(getattr(log, "type", -1)) == 11
        and getattr(log, "playerIndex", None) == latch.get("player")
        and getattr(log, "cardId", None) == energy[0]
        and getattr(log, "serial", None) == energy[1]
        and getattr(log, "cardIdTarget", None) == Alakazam
        and getattr(log, "serialTarget", None) == evolution[1]
        for log in obs.logs
    )


def _draw_free_activate_no(obs: Observation, latch: dict) -> list[int] | None:
    select = obs.select
    selected = latch.get("selected_evolution_fingerprint")
    context_card = select.contextCard
    if (
        not _draw_free_common_state_is_same(
            obs,
            latch,
            expected_hand=latch.get("hand_after_evolution"),
            expected_action_count=latch.get("expected_action_count"),
            attached=False,
        )
        or select.context != SelectContext.ACTIVATE
        or select.type != SelectType.YES_NO
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.effect is not None
        or context_card is None
        or not _draw_survival_card_is_exact(
            context_card, latch.get("player")
        )
        or _bridge_card_fingerprint(context_card) != selected
        or not _draw_free_log_has_exact_evolution(obs, latch)
    ):
        return None
    yes_no = _draw_survival_yes_no_indices(select)
    return [yes_no[1]] if yes_no is not None else None


def _draw_free_attach_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    if (
        not _draw_free_common_state_is_same(
            obs,
            latch,
            expected_hand=latch.get("hand_after_evolution"),
            expected_action_count=latch.get("expected_action_count"),
            attached=False,
        )
        or not _draw_free_exact_main_envelope(obs.select)
    ):
        return None
    energy = latch.get("selected_energy_fingerprint")
    matches = _draw_free_option_for_hand_serial(
        obs, serial=energy[1], option_kind=OptionType.ATTACH
    )
    if len(matches) != 1:
        return None
    option = obs.select.option[matches[0]]
    card = _draw_free_card_at_hand_index(
        obs.current.players[latch.get("player")], option.index
    )
    return (
        [matches[0]]
        if card is not None
        and _bridge_card_fingerprint(card) == energy
        else None
    )


def _draw_free_effect_card_fingerprint(card, player: int):
    if card is None:
        return None
    if not _draw_survival_card_is_exact(card, player):
        return False
    return _bridge_card_fingerprint(card)


def _draw_free_optional_telepath_is_exact(
    obs: Observation, latch: dict
) -> bool:
    select = obs.select
    player = latch.get("player")
    selected = latch.get("selected_energy_fingerprint")
    context_fingerprint = _draw_free_effect_card_fingerprint(
        select.contextCard, player
    )
    effect_fingerprint = _draw_free_effect_card_fingerprint(
        select.effect, player
    )
    if (
        selected is None
        or selected[0] != Telepath_Psychic_Energy
        or select.context != SelectContext.TO_BENCH
        or select.type != SelectType.CARD
        or select.minCount != 0
        or not isinstance(select.maxCount, int)
        or select.maxCount < 0
        or select.maxCount > len(select.option)
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or selected not in (context_fingerprint, effect_fingerprint)
        or any(
            fingerprint not in (None, selected)
            for fingerprint in (context_fingerprint, effect_fingerprint)
        )
    ):
        return False

    visible = select.deck
    if visible is not None:
        rows = []
        for card in visible:
            if not _draw_survival_card_is_exact(card, player):
                return False
            rows.append(_bridge_card_fingerprint(card))
        if len({row[1] for row in rows}) != len(rows):
            return False
    for option in select.option:
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.DECK
            or not isinstance(option.index, int)
            or option.index < 0
            or option.playerIndex not in (None, player)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
            or visible is None
            or option.index >= len(visible)
        ):
            return False
    option_keys = tuple(
        (option.area, option.index, option.playerIndex)
        for option in select.option
    )
    return len(option_keys) == len(set(option_keys))


def _draw_free_powerful_hand_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    if (
        not _draw_free_common_state_is_same(
            obs,
            latch,
            expected_hand=latch.get("hand_after_attach"),
            expected_action_count=latch.get("expected_action_count"),
            attached=True,
        )
        or not _draw_free_exact_main_envelope(obs.select)
        or not _draw_free_powerful_hand_metadata_certified()
        or 20 * len(latch.get("hand_after_attach"))
        != latch.get("expected_damage")
    ):
        return None
    matches = [
        index
        for index, option in enumerate(obs.select.option)
        if option.type == OptionType.ATTACK
        and option.attackId == ATTACK_POWERFUL_HAND
        and _draw_survival_attack_option_is_exact(option)
    ]
    return [matches[0]] if len(matches) == 1 else None


def _draw_free_resolution_is_exact(
    obs: Observation, latch: dict
) -> bool:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    if my_index not in (0, 1):
        return False
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = _draw_free_evolved_active(obs, latch, attached=True)
    own_rows = _draw_survival_field_rows(mine, my_index)
    opponent_rows = _draw_survival_field_rows(
        theirs, 1 - my_index
    )
    expected_taken = min(
        latch.get("target_prizes"), latch.get("own_prize_count")
    )
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
        or state.turnActionCount != latch.get("expected_action_count")
        or state.result != -1
        or state.supporterPlayed != latch.get("supporter_played")
        or state.stadiumPlayed != latch.get("stadium_played")
        or not state.energyAttached
        or state.retreated != latch.get("retreated")
        or mine.deckCount != 1
        or mine.benchMax != latch.get("bench_max")
        or _draw_free_status(mine) != latch.get("mine_status")
        or _draw_free_status(theirs) != latch.get("opponent_status")
        or tuple(
            _bridge_card_fingerprint(card) for card in mine.discard
        )
        != latch.get("mine_discard")
        or _draw_free_prize_rows(mine) != latch.get("mine_prize")
        or _draw_free_prize_rows(theirs)
        != latch.get("opponent_prize")
        or tuple(
            _bridge_card_fingerprint(card) for card in state.stadium
        )
        != latch.get("stadium")
        or _draw_survival_exact_hand(mine, my_index)
        != latch.get("hand_after_attach")
        or active is None
        or own_rows is None
        or len(own_rows) != latch.get("own_field_count")
        or tuple(
            row for row in own_rows if row[0] != active.serial
        )
        != latch.get("own_conserved_field")
        or theirs.active
        or opponent_rows is None
        or opponent_rows != latch.get("opponent_bench_field")
        or select.context != SelectContext.TO_HAND
        or select.type != SelectType.CARD
        or select.minCount != expected_taken
        or select.maxCount != expected_taken
        or len(select.option) != latch.get("own_prize_count")
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
    ):
        return False

    discard = tuple(
        _bridge_card_fingerprint(card) for card in theirs.discard
    )
    frozen_discard = tuple(latch.get("opponent_discard") or ())
    target_cards = tuple(latch.get("target_cards") or ())
    if (
        len(discard) != len(frozen_discard) + len(target_cards)
        or any(
            discard.count(row) != frozen_discard.count(row)
            for row in frozen_discard
        )
        or any(discard.count(row) != 1 for row in target_cards)
    ):
        return False
    expected_options = tuple(
        (AreaType.PRIZE, index, my_index)
        for index in range(latch.get("own_prize_count"))
    )
    actual_options = []
    for option in select.option:
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.PRIZE
            or not isinstance(option.index, int)
            or option.playerIndex != my_index
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
        ):
            return False
        actual_options.append(
            (option.area, option.index, option.playerIndex)
        )
    if tuple(actual_options) != expected_options:
        return False

    evolution = latch.get("selected_evolution_fingerprint")
    attack_logged = any(
        int(getattr(log, "type", -1)) == 15
        and getattr(log, "playerIndex", None) == my_index
        and getattr(log, "cardId", None) == Alakazam
        and getattr(log, "serial", None) == evolution[1]
        and getattr(log, "attackId", None) == ATTACK_POWERFUL_HAND
        for log in obs.logs
    )
    damage_logged = any(
        int(getattr(log, "type", -1)) == 16
        and getattr(log, "playerIndex", None) == 1 - my_index
        and getattr(log, "serial", None) == latch.get("target_serial")
        and getattr(log, "value", None) == -latch.get("expected_damage")
        and getattr(log, "putDamageCounter", None) is True
        for log in obs.logs
    )
    return attack_logged and damage_logged


def _draw_free_advance_terminal_evolution(
    obs: Observation,
) -> list[int] | None:
    latch = _draw_free_terminal_evolution_latch
    if not latch:
        return None
    stage = latch.get("stage")

    if stage == "await_activate_no":
        action = _draw_free_activate_no(obs, latch)
        if action is None:
            _clear_draw_free_terminal_evolution_latch()
            return None
        latch["stage"] = "await_attach"
        latch["expected_action_count"] += 1
        return action

    if stage == "await_attach":
        action = _draw_free_attach_action(obs, latch)
        if action is None:
            _clear_draw_free_terminal_evolution_latch()
            return None
        latch["stage"] = "await_post_attach"
        latch["expected_action_count"] += 1
        return action

    if stage == "await_post_attach":
        if (
            not _draw_free_common_state_is_same(
                obs,
                latch,
                expected_hand=latch.get("hand_after_attach"),
                expected_action_count=latch.get(
                    "expected_action_count"
                ),
                attached=True,
            )
            or not _draw_free_log_has_exact_attachment(obs, latch)
        ):
            _clear_draw_free_terminal_evolution_latch()
            return None
        if obs.select.context == SelectContext.TO_BENCH:
            if not _draw_free_optional_telepath_is_exact(obs, latch):
                _clear_draw_free_terminal_evolution_latch()
                return None
            latch["telepath_prompt_seen"] = True
            latch["stage"] = "await_attack"
            latch["expected_action_count"] += 1
            return []
        action = _draw_free_powerful_hand_action(obs, latch)
        if action is None:
            _clear_draw_free_terminal_evolution_latch()
            return None
        latch["stage"] = "await_resolution"
        latch["expected_action_count"] += 1
        return action

    if stage == "await_attack":
        action = _draw_free_powerful_hand_action(obs, latch)
        if action is None:
            _clear_draw_free_terminal_evolution_latch()
            return None
        latch["stage"] = "await_resolution"
        latch["expected_action_count"] += 1
        return action

    if stage == "await_resolution":
        _draw_free_resolution_is_exact(obs, latch)
        _clear_draw_free_terminal_evolution_latch()
        return None

    _clear_draw_free_terminal_evolution_latch()
    return None


def _draw_free_rerun_v1_parent(
    obs_dict: dict,
    before_v1: dict,
    desired_action: list[int],
) -> list[int] | None:
    select = obs_dict.get("select")
    if not isinstance(select, dict):
        return None
    options = select.get("option")
    if not isinstance(options, list):
        return None
    if any(
        not isinstance(index, int) or index < 0 or index >= len(options)
        for index in desired_action
    ):
        return None
    reranked = copy.deepcopy(obs_dict)
    reranked_select = reranked["select"]
    reranked_select["option"] = [
        copy.deepcopy(options[index]) for index in desired_action
    ]
    reranked_select["maxCount"] = len(desired_action)
    if reranked_select.get("minCount", 0) > len(desired_action):
        return None
    _draw_free_restore_v1_state(before_v1)
    reranked_action = _draw_survival_v1_parent_agent(reranked)
    if not isinstance(reranked_action, list) or any(
        not isinstance(index, int)
        or index < 0
        or index >= len(desired_action)
        for index in reranked_action
    ):
        return None
    return [desired_action[index] for index in reranked_action]


def _draw_free_prepare_overlay(obs_dict: dict) -> bool:
    """Clear stale state and report that this callback must only delegate."""
    if not _draw_free_terminal_evolution_latch:
        return False
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    if not isinstance(select, dict) or not isinstance(current, dict):
        _clear_draw_free_terminal_evolution_latch()
        return True
    if (
        current.get("turn")
        != _draw_free_terminal_evolution_latch.get("turn")
        or current.get("yourIndex")
        != _draw_free_terminal_evolution_latch.get("player")
        or current.get("result") != -1
    ):
        _clear_draw_free_terminal_evolution_latch()
        return True
    return False


def _draw_free_v2_parent_agent(obs_dict: dict) -> list[int]:
    """Apply one fail-closed correction after the frozen V1 policy."""
    if (
        _draw_free_terminal_last_observation is not None
        and obs_dict == _draw_free_terminal_last_observation
        and _draw_free_terminal_last_action is not None
    ):
        return list(_draw_free_terminal_last_action)

    inherited_quarantine = bool(_merge_start_quarantine_depth)
    higher_owner = bool(_enriching_zero_boss_lucario_latch)
    stale_cleared = _draw_free_prepare_overlay(obs_dict)
    had_transaction = bool(_draw_free_terminal_evolution_latch)
    before_v1 = _draw_free_snapshot_v1_state()
    block_lower_start = bool(
        stale_cleared
        or had_transaction
        or higher_owner
        or inherited_quarantine
    )
    if block_lower_start:
        _merge_push_start_quarantine()
    try:
        v1_action = _draw_survival_v1_parent_agent(
            copy.deepcopy(obs_dict)
        )
    finally:
        if block_lower_start:
            _merge_pop_start_quarantine()
    after_v1 = _draw_free_snapshot_v1_state()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return _draw_free_terminal_remember(obs_dict, v1_action)

    try:
        obs = to_observation_class(copy.deepcopy(obs_dict))
        if (
            obs.current is None
            or obs.select is None
            or not _draw_free_action_is_valid(obs, v1_action)
            or stale_cleared
        ):
            return _draw_free_terminal_remember(obs_dict, v1_action)

        lower_owner = any(
            bool(snapshot.get(key))
            for snapshot in (before_v1, after_v1)
            for key in (
                "certified_turn_plan",
                "draw_survival_terminal",
            )
        )
        if lower_owner:
            if had_transaction:
                _clear_draw_free_terminal_evolution_latch()
            return _draw_free_terminal_remember(obs_dict, v1_action)

        if (higher_owner or inherited_quarantine) and not had_transaction:
            return _draw_free_terminal_remember(obs_dict, v1_action)

        if had_transaction:
            transaction_action = _draw_free_advance_terminal_evolution(
                obs
            )
            if transaction_action is None:
                return _draw_free_terminal_remember(obs_dict, v1_action)
            if not _draw_free_action_is_valid(obs, transaction_action):
                _clear_draw_free_terminal_evolution_latch()
                return _draw_free_terminal_remember(obs_dict, v1_action)
            if transaction_action != v1_action:
                replacement = _draw_free_rerun_v1_parent(
                    obs_dict, before_v1, transaction_action
                )
                if replacement != transaction_action:
                    _draw_free_restore_v1_state(after_v1)
                    _clear_draw_free_terminal_evolution_latch()
                    return _draw_free_terminal_remember(
                        obs_dict, v1_action
                    )
            return _draw_free_terminal_remember(
                obs_dict, transaction_action
            )

        mine = obs.current.players[obs.current.yourIndex]
        active = mine.active[0] if len(mine.active) == 1 else None
        if (
            not _draw_free_exact_main_envelope(obs.select)
            or mine.deckCount != 1
            or active is None
            or active.id != Kadabra
            or len(v1_action) != 1
            or not _draw_survival_end_option_is_exact(
                obs.select.option[v1_action[0]]
            )
        ):
            return _draw_free_terminal_remember(obs_dict, v1_action)

        _draw_free_restore_v1_state(before_v1)
        exact_action = _source_transition_v2_parent_agent(copy.deepcopy(obs_dict))
        after_exact = _draw_free_snapshot_v1_state()
        if not _draw_free_action_is_valid(obs, exact_action):
            _draw_free_restore_v1_state(after_v1)
            return _draw_free_terminal_remember(obs_dict, v1_action)
        transaction_action = _draw_free_start_terminal_evolution(
            obs,
            v1_action,
            exact_action,
            before_v1,
            after_v1,
            after_exact,
        )
        if transaction_action is None:
            _draw_free_restore_v1_state(after_v1)
            return _draw_free_terminal_remember(obs_dict, v1_action)
        return _draw_free_terminal_remember(
            obs_dict, transaction_action
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        _draw_free_restore_v1_state(after_v1)
        _clear_draw_free_terminal_evolution_latch()
        return _draw_free_terminal_remember(obs_dict, v1_action)


# ---------------------------------------------------------------------------
# ENRICHING_DRAW_ZERO_BOSS_LUCARIO_TERMINAL_OVERRIDE
#
# V2 above remains the immediate parent.  This outer transaction recognizes
# only a fully public state where V2's Powerful Hand would take one Prize,
# exact-v3's Enriching attachment would consume a four-card deck, and the
# unique Boss -> Mega Lucario ex route is already a same-turn final-Prize KO.
# ---------------------------------------------------------------------------

_enriching_zero_boss_lucario_last_observation = None
_enriching_zero_boss_lucario_last_action = None


def _clear_enriching_zero_boss_lucario_wrapper_cache() -> None:
    global _enriching_zero_boss_lucario_last_observation
    global _enriching_zero_boss_lucario_last_action
    _enriching_zero_boss_lucario_last_observation = None
    _enriching_zero_boss_lucario_last_action = None


def _enriching_zero_boss_lucario_remember(
    observation: dict, action: list[int]
) -> list[int]:
    global _enriching_zero_boss_lucario_last_observation
    global _enriching_zero_boss_lucario_last_action
    _enriching_zero_boss_lucario_last_observation = copy.deepcopy(observation)
    _enriching_zero_boss_lucario_last_action = tuple(action)
    return list(action)


def _enriching_zero_boss_lucario_snapshot_v2_state() -> dict:
    snapshot = _draw_free_snapshot_v1_state()
    snapshot.update(
        draw_free_terminal=copy.deepcopy(
            _draw_free_terminal_evolution_latch
        ),
        draw_free_last_observation=copy.deepcopy(
            _draw_free_terminal_last_observation
        ),
        draw_free_last_action=copy.deepcopy(
            _draw_free_terminal_last_action
        ),
    )
    return snapshot


def _enriching_zero_boss_lucario_restore_v2_state(snapshot: dict) -> None:
    global _draw_free_terminal_last_observation
    global _draw_free_terminal_last_action
    _draw_free_restore_v1_state(snapshot)
    _draw_free_terminal_evolution_latch.clear()
    _draw_free_terminal_evolution_latch.update(
        copy.deepcopy(snapshot["draw_free_terminal"])
    )
    _draw_free_terminal_last_observation = copy.deepcopy(
        snapshot["draw_free_last_observation"]
    )
    _draw_free_terminal_last_action = copy.deepcopy(
        snapshot["draw_free_last_action"]
    )


def _merge_snapshot_complete_state() -> dict:
    """Freeze the full four-layer policy state for atomic rerun checks."""
    snapshot = _enriching_zero_boss_lucario_snapshot_v2_state()
    snapshot.update(
        enriching_zero_boss_lucario=copy.deepcopy(
            _enriching_zero_boss_lucario_latch
        ),
        enriching_zero_boss_lucario_last_observation=copy.deepcopy(
            _enriching_zero_boss_lucario_last_observation
        ),
        enriching_zero_boss_lucario_last_action=copy.deepcopy(
            _enriching_zero_boss_lucario_last_action
        ),
        merge_start_quarantine_depth=_merge_start_quarantine_depth,
    )
    return snapshot


def _merge_restore_complete_state(snapshot: dict) -> None:
    """Restore one complete snapshot without partially adopting a rerun."""
    global _enriching_zero_boss_lucario_last_observation
    global _enriching_zero_boss_lucario_last_action
    global _merge_start_quarantine_depth
    _enriching_zero_boss_lucario_restore_v2_state(snapshot)
    _enriching_zero_boss_lucario_latch.clear()
    _enriching_zero_boss_lucario_latch.update(
        copy.deepcopy(snapshot["enriching_zero_boss_lucario"])
    )
    _enriching_zero_boss_lucario_last_observation = copy.deepcopy(
        snapshot["enriching_zero_boss_lucario_last_observation"]
    )
    _enriching_zero_boss_lucario_last_action = copy.deepcopy(
        snapshot["enriching_zero_boss_lucario_last_action"]
    )
    _merge_start_quarantine_depth = snapshot[
        "merge_start_quarantine_depth"
    ]


def _enriching_zero_boss_lucario_inherited_latch_active(
    snapshot: dict,
) -> bool:
    return _draw_free_inherited_latch_active(snapshot) or bool(
        snapshot.get("draw_free_terminal")
    )


def _enriching_zero_boss_lucario_metadata_certified() -> bool:
    boss = card_table.get(Boss_Orders)
    hariyama = card_table.get(Hariyama)
    lucario = card_table.get(Mega_Lucario_ex)
    return (
        _draw_survival_fixed_metadata_certified()
        and _draw_free_powerful_hand_metadata_certified()
        and boss is not None
        and boss.name == "Boss\u2019s Orders"
        and boss.cardType == CardType.SUPPORTER
        and len(boss.skills or []) == 1
        and boss.skills[0].text
        == "Switch in 1 of your opponent\u2019s Benched Pok\u00e9mon to the Active Spot."
        and hariyama is not None
        and hariyama.name == "Hariyama"
        and hariyama.hp == 150
        and hariyama.stage1
        and not hariyama.ex
        and not hariyama.megaEx
        and lucario is not None
        and lucario.name == "Mega Lucario ex"
        and lucario.hp == 340
        and lucario.stage1
        and not lucario.ex
        and lucario.megaEx
    )


def _enriching_zero_boss_lucario_ordered_cards(
    cards, player: int | None
) -> tuple | None:
    if cards is None:
        return None
    rows = []
    for card in cards:
        expected_player = (
            player if player is not None else getattr(card, "playerIndex", None)
        )
        if not _draw_survival_card_is_exact(card, expected_player):
            return None
        rows.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def _enriching_zero_boss_lucario_snapshot(
    obs: Observation,
) -> dict | None:
    if not _draw_survival_public_state_is_complete(obs):
        return None
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    hand = _draw_survival_exact_hand(mine, my_index)
    own_discard = _enriching_zero_boss_lucario_ordered_cards(
        mine.discard, my_index
    )
    opponent_discard = _enriching_zero_boss_lucario_ordered_cards(
        theirs.discard, 1 - my_index
    )
    stadium = _enriching_zero_boss_lucario_ordered_cards(
        state.stadium, None
    )
    if None in (hand, own_discard, opponent_discard, stadium):
        return None
    return {
        "turn": state.turn,
        "action_count": state.turnActionCount,
        "result": state.result,
        "supporter_played": state.supporterPlayed,
        "stadium_played": state.stadiumPlayed,
        "energy_attached": state.energyAttached,
        "retreated": state.retreated,
        "looking": state.looking,
        "own_hand": hand,
        "own_discard": own_discard,
        "own_prize": _draw_free_prize_rows(mine),
        "own_deck": mine.deckCount,
        "own_bench_max": mine.benchMax,
        "own_status": _draw_free_status(mine),
        "own_active": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.active
        ),
        "own_bench": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        ),
        "opponent_discard": opponent_discard,
        "opponent_prize": _draw_free_prize_rows(theirs),
        "opponent_deck": theirs.deckCount,
        "opponent_hand_count": theirs.handCount,
        "opponent_bench_max": theirs.benchMax,
        "opponent_status": _draw_free_status(theirs),
        "opponent_active": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.active
        ),
        "opponent_bench": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.bench
        ),
        "stadium": stadium,
    }


def _enriching_zero_boss_lucario_play_option_is_exact(option) -> bool:
    return (
        option.type == OptionType.PLAY
        and isinstance(option.index, int)
        and _draw_survival_option_unused_fields_are_none(option, {"index"})
    )


def _enriching_zero_boss_lucario_boss_option(
    obs: Observation,
) -> tuple[int, tuple] | None:
    mine = obs.current.players[obs.current.yourIndex]
    matches = []
    for option_index, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = _draw_free_card_at_hand_index(mine, option.index)
        if card is not None and card.id == Boss_Orders:
            matches.append((option_index, option, card))
    if len(matches) != 1:
        return None
    option_index, option, card = matches[0]
    fingerprint = _bridge_card_fingerprint(card)
    if (
        not _enriching_zero_boss_lucario_play_option_is_exact(option)
        or not _draw_survival_card_is_exact(card, obs.current.yourIndex)
        or sum(1 for item in mine.hand if item.id == Boss_Orders) != 1
        or sum(1 for item in mine.hand if item.serial == card.serial) != 1
    ):
        return None
    return option_index, fingerprint


def _enriching_zero_boss_lucario_log_is_exact(
    log, log_type: int, expected: dict
) -> bool:
    if int(getattr(log, "type", -1)) != log_type:
        return False
    values = vars(log)
    if any(values.get(key) != value for key, value in expected.items()):
        return False
    allowed = {"type", *expected}
    return all(key in allowed or value is None for key, value in values.items())


def _enriching_zero_boss_lucario_target_moves(target) -> tuple:
    return (
        (target.id, target.serial, int(AreaType.ACTIVE)),
        *(
            (card.id, card.serial, int(AreaType.PRE_EVOLUTION))
            for card in target.preEvolution
        ),
        *(
            (card.id, card.serial, int(AreaType.ENERGY))
            for card in target.energyCards
        ),
        *(
            (card.id, card.serial, int(AreaType.TOOL))
            for card in target.tools
        ),
    )


def _enriching_zero_boss_lucario_start(
    obs: Observation,
    v2_action: list[int],
    exact_action: list[int],
    before_v2: dict,
    after_v2: dict,
    after_exact: dict,
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if len(mine.active) == 1 else None
    current_target = theirs.active[0] if len(theirs.active) == 1 else None
    if (
        not _draw_free_exact_main_envelope(select)
        or state.result != -1
        or state.looking is not None
        or state.supporterPlayed
        or state.energyAttached
        or mine.deckCount != 4
        or len(mine.prize) != 2
        or _enriching_zero_boss_lucario_latch
        or any(
            _enriching_zero_boss_lucario_inherited_latch_active(snapshot)
            for snapshot in (before_v2, after_v2, after_exact)
        )
        or not _enriching_zero_boss_lucario_metadata_certified()
        or not _draw_survival_public_state_is_complete(obs)
        or active is None
        or active.id != Alakazam
        or active.maxHp != card_table[Alakazam].hp
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or not any(
            energy.id in PSYCHIC_ENERGY_IDS
            for energy in active.energyCards
        )
        or _draw_free_status(mine) != (False, False, False, False, False)
        or current_target is None
        or current_target.id != Hariyama
        or current_target.maxHp != card_table[Hariyama].hp
        or not _draw_survival_known_stack_is_exact(
            current_target, 1 - my_index
        )
        or not _draw_survival_counter_target_is_clear(obs, current_target)
        or prize_count(current_target) != 1
        or prize_count(current_target) >= len(mine.prize)
        or 20 * mine.handCount < current_target.hp
        or len(v2_action) != 1
        or not 0 <= v2_action[0] < len(select.option)
        or not _draw_survival_attack_option_is_exact(
            select.option[v2_action[0]]
        )
        or select.option[v2_action[0]].attackId != ATTACK_POWERFUL_HAND
        or sum(
            1
            for option in select.option
            if _draw_survival_attack_option_is_exact(option)
            and option.attackId == ATTACK_POWERFUL_HAND
        )
        != 1
    ):
        return None

    effect = _draw_survival_selected_main_effect(obs, exact_action)
    if (
        effect is None
        or effect.get("kind") != "enriching_attachment"
        or effect.get("pre_deck") != 4
        or effect.get("projected_deck") != 0
    ):
        return None
    boss = _enriching_zero_boss_lucario_boss_option(obs)
    if boss is None:
        return None
    boss_option, boss_fingerprint = boss

    post_boss_damage = 20 * (mine.handCount - 1)
    candidates = []
    for bench_index, target in enumerate(theirs.bench):
        if (
            target.id == Mega_Lucario_ex
            and target.maxHp == card_table[Mega_Lucario_ex].hp
            and _draw_survival_known_stack_is_exact(target, 1 - my_index)
            and _draw_survival_counter_target_is_clear(obs, target)
            and prize_count(target) >= len(mine.prize)
            and post_boss_damage >= target.hp
        ):
            candidates.append((bench_index, target))
    if len(candidates) != 1:
        return None
    target_index, target = candidates[0]

    snapshot = _enriching_zero_boss_lucario_snapshot(obs)
    hand = snapshot.get("own_hand") if snapshot is not None else None
    if hand is None:
        return None
    post_hand = _draw_free_without_exact_card(hand, boss_fingerprint)
    protected = (
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(current_target),
        *_bridge_pokemon_component_serials(target),
        boss_fingerprint[1],
        effect["selected_card"][1],
    )
    if (
        post_hand is None
        or len(post_hand) != mine.handCount - 1
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None

    post_bench = list(snapshot["opponent_bench"])
    post_bench[target_index] = snapshot["opponent_active"][0]
    expected_target_prompt = copy.deepcopy(snapshot)
    expected_target_prompt.update(
        action_count=state.turnActionCount + 1,
        supporter_played=True,
        own_hand=post_hand,
    )
    expected_attack = copy.deepcopy(expected_target_prompt)
    expected_attack.update(
        action_count=state.turnActionCount + 2,
        own_discard=snapshot["own_discard"] + (boss_fingerprint,),
        opponent_status=(False, False, False, False, False),
        opponent_active=(_bridge_pokemon_fingerprint(target),),
        opponent_bench=tuple(post_bench),
    )
    _enriching_zero_boss_lucario_latch.update(
        transaction="ENRICHING_DRAW_ZERO_BOSS_LUCARIO_TERMINAL_OVERRIDE",
        stage="await_boss_target",
        turn=state.turn,
        player=my_index,
        start_action_count=state.turnActionCount,
        boss_option=boss_option,
        boss_fingerprint=boss_fingerprint,
        enriching_fingerprint=effect["selected_card"],
        target_index=target_index,
        target_serial=target.serial,
        target_fingerprint=_bridge_pokemon_fingerprint(target),
        target_prizes=prize_count(target),
        target_moves=_enriching_zero_boss_lucario_target_moves(target),
        current_target_serial=current_target.serial,
        current_target_fingerprint=_bridge_pokemon_fingerprint(
            current_target
        ),
        post_boss_hand=post_hand,
        expected_damage=post_boss_damage,
        start_snapshot=snapshot,
        expected_target_prompt=expected_target_prompt,
        expected_attack=expected_attack,
    )
    return [boss_option]


def _enriching_zero_boss_lucario_target_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    if (
        _enriching_zero_boss_lucario_snapshot(obs)
        != latch.get("expected_target_prompt")
        or select.type != SelectType.CARD
        or select.context != SelectContext.SWITCH
        or select.minCount != 1
        or select.maxCount != 1
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is None
        or _bridge_card_fingerprint(select.effect)
        != latch.get("boss_fingerprint")
        or len(obs.logs) != 1
        or not _enriching_zero_boss_lucario_log_is_exact(
            obs.logs[0],
            10,
            {
                "playerIndex": latch.get("player"),
                "cardId": Boss_Orders,
                "serial": latch.get("boss_fingerprint")[1],
            },
        )
    ):
        return None
    expected_options = tuple(
        (AreaType.BENCH, index, 1 - latch.get("player"))
        for index in range(
            len(latch.get("start_snapshot")["opponent_bench"])
        )
    )
    actual_options = []
    matches = []
    theirs = state.players[1 - latch.get("player")]
    for option_index, option in enumerate(select.option):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.BENCH
            or not isinstance(option.index, int)
            or option.playerIndex != 1 - latch.get("player")
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
        ):
            return None
        actual_options.append((option.area, option.index, option.playerIndex))
        if (
            0 <= option.index < len(theirs.bench)
            and theirs.bench[option.index].serial == latch.get("target_serial")
            and _bridge_pokemon_fingerprint(theirs.bench[option.index])
            == latch.get("target_fingerprint")
        ):
            matches.append(option_index)
    if tuple(actual_options) != expected_options or len(matches) != 1:
        return None
    return [matches[0]]


def _enriching_zero_boss_lucario_attack_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if len(mine.active) == 1 else None
    target = theirs.active[0] if len(theirs.active) == 1 else None
    if (
        _enriching_zero_boss_lucario_snapshot(obs)
        != latch.get("expected_attack")
        or not _draw_free_exact_main_envelope(select)
        or active is None
        or active.id != Alakazam
        or target is None
        or target.serial != latch.get("target_serial")
        or _bridge_pokemon_fingerprint(target)
        != latch.get("target_fingerprint")
        or not _draw_survival_counter_target_is_clear(obs, target)
        or prize_count(target) != latch.get("target_prizes")
        or 20 * mine.handCount != latch.get("expected_damage")
        or latch.get("expected_damage") < target.hp
        or len(obs.logs) != 1
        or not _enriching_zero_boss_lucario_log_is_exact(
            obs.logs[0],
            8,
            {
                "playerIndex": 1 - my_index,
                "cardIdActive": Hariyama,
                "serialActive": latch.get("current_target_serial"),
                "cardIdBench": Mega_Lucario_ex,
                "serialBench": latch.get("target_serial"),
            },
        )
    ):
        return None
    matches = [
        option_index
        for option_index, option in enumerate(select.option)
        if _draw_survival_attack_option_is_exact(option)
        and option.attackId == ATTACK_POWERFUL_HAND
    ]
    return [matches[0]] if len(matches) == 1 else None


def _enriching_zero_boss_lucario_resolution_is_exact(
    obs: Observation, latch: dict
) -> bool:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    if my_index not in (0, 1) or len(state.players) != 2:
        return False
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    expected = latch.get("expected_attack")
    if not isinstance(expected, dict):
        return False
    own_active = tuple(
        _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.active
    )
    own_bench = tuple(
        _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
    )
    opponent_bench = tuple(
        _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.bench
    )
    own_discard = _enriching_zero_boss_lucario_ordered_cards(
        mine.discard, my_index
    )
    opponent_discard = _enriching_zero_boss_lucario_ordered_cards(
        theirs.discard, 1 - my_index
    )
    expected_taken = min(
        latch.get("target_prizes"), len(expected.get("own_prize"))
    )
    if (
        state.turn != latch.get("turn")
        or state.turnActionCount != latch.get("start_action_count") + 3
        or state.result != -1
        or not state.supporterPlayed
        or state.stadiumPlayed != expected.get("stadium_played")
        or state.energyAttached != expected.get("energy_attached")
        or state.retreated != expected.get("retreated")
        or state.looking is not None
        or mine.deckCount != 4
        or theirs.deckCount != expected.get("opponent_deck")
        or mine.benchMax != expected.get("own_bench_max")
        or theirs.benchMax != expected.get("opponent_bench_max")
        or _draw_free_status(mine) != expected.get("own_status")
        or _draw_free_status(theirs) != (False, False, False, False, False)
        or _draw_survival_exact_hand(mine, my_index)
        != latch.get("post_boss_hand")
        or own_discard != expected.get("own_discard")
        or _draw_free_prize_rows(mine) != expected.get("own_prize")
        or own_active != expected.get("own_active")
        or own_bench != expected.get("own_bench")
        or theirs.active
        or opponent_bench != expected.get("opponent_bench")
        or _draw_free_prize_rows(theirs) != expected.get("opponent_prize")
        or theirs.handCount != expected.get("opponent_hand_count")
        or opponent_discard
        != expected.get("opponent_discard") + tuple(
            (card_id, serial, 1 - my_index)
            for card_id, serial, _ in latch.get("target_moves")
        )
        or _enriching_zero_boss_lucario_ordered_cards(state.stadium, None)
        != expected.get("stadium")
        or select.type != SelectType.CARD
        or select.context != SelectContext.TO_HAND
        or select.minCount != expected_taken
        or select.maxCount != expected_taken
        or len(select.option) != len(expected.get("own_prize"))
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
    ):
        return False
    expected_options = tuple(
        (AreaType.PRIZE, index, my_index)
        for index in range(len(expected.get("own_prize")))
    )
    actual_options = []
    for option in select.option:
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.PRIZE
            or not isinstance(option.index, int)
            or option.playerIndex != my_index
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
        ):
            return False
        actual_options.append((option.area, option.index, option.playerIndex))
    if tuple(actual_options) != expected_options:
        return False
    if len(obs.logs) != 2 + len(latch.get("target_moves")):
        return False
    if not _enriching_zero_boss_lucario_log_is_exact(
        obs.logs[0],
        15,
        {
            "playerIndex": my_index,
            "cardId": Alakazam,
            "serial": expected.get("own_active")[0][1],
            "attackId": ATTACK_POWERFUL_HAND,
        },
    ):
        return False
    if not _enriching_zero_boss_lucario_log_is_exact(
        obs.logs[1],
        16,
        {
            "playerIndex": 1 - my_index,
            "cardId": Mega_Lucario_ex,
            "serial": latch.get("target_serial"),
            "value": -latch.get("expected_damage"),
            "putDamageCounter": True,
        },
    ):
        return False
    for log, (card_id, serial, from_area) in zip(
        obs.logs[2:], latch.get("target_moves")
    ):
        if not _enriching_zero_boss_lucario_log_is_exact(
            log,
            6,
            {
                "playerIndex": 1 - my_index,
                "cardId": card_id,
                "serial": serial,
                "fromArea": AreaType(from_area),
                "toArea": AreaType.DISCARD,
            },
        ):
            return False
    return True


def _enriching_zero_boss_lucario_advance(
    obs: Observation,
) -> list[int] | None:
    latch = _enriching_zero_boss_lucario_latch
    if not latch:
        return None
    stage = latch.get("stage")
    if stage == "await_boss_target":
        action = _enriching_zero_boss_lucario_target_action(obs, latch)
        if action is None:
            _clear_enriching_zero_boss_lucario_latch()
            return None
        latch["stage"] = "await_attack"
        return action
    if stage == "await_attack":
        action = _enriching_zero_boss_lucario_attack_action(obs, latch)
        if action is None:
            _clear_enriching_zero_boss_lucario_latch()
            return None
        latch["stage"] = "await_resolution"
        return action
    if stage == "await_resolution":
        _enriching_zero_boss_lucario_resolution_is_exact(obs, latch)
        _clear_enriching_zero_boss_lucario_latch()
        return None
    _clear_enriching_zero_boss_lucario_latch()
    return None


def _enriching_zero_boss_lucario_rerun_v2(
    obs_dict: dict, before_v2: dict, desired_action: list[int]
) -> list[int] | None:
    raw_select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    raw_options = raw_select.get("option") if isinstance(raw_select, dict) else None
    if (
        not isinstance(raw_options, list)
        or not desired_action
        or len(desired_action) != len(set(desired_action))
        or any(
            not isinstance(index, int)
            or index < 0
            or index >= len(raw_options)
            for index in desired_action
        )
        or raw_select.get("minCount") != 1
        or raw_select.get("maxCount") != 1
    ):
        return None
    reranked = copy.deepcopy(obs_dict)
    reranked["select"]["option"] = [
        copy.deepcopy(raw_options[index]) for index in desired_action
    ]
    _enriching_zero_boss_lucario_restore_v2_state(before_v2)
    reranked_action = _draw_free_v2_parent_agent(reranked)
    if (
        not isinstance(reranked_action, list)
        or len(reranked_action) != 1
        or not isinstance(reranked_action[0], int)
        or not 0 <= reranked_action[0] < len(desired_action)
    ):
        return None
    return [desired_action[reranked_action[0]]]


def _enriching_zero_boss_lucario_prepare(obs_dict: dict) -> bool:
    if not _enriching_zero_boss_lucario_latch:
        return False
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    if not isinstance(select, dict) or not isinstance(current, dict):
        _clear_enriching_zero_boss_lucario_latch()
        return True
    if (
        current.get("turn")
        != _enriching_zero_boss_lucario_latch.get("turn")
        or current.get("yourIndex")
        != _enriching_zero_boss_lucario_latch.get("player")
        or current.get("result") != -1
    ):
        _clear_enriching_zero_boss_lucario_latch()
        return True
    return False


def _exposed_dudunsparce_parent_agent(obs_dict: dict) -> list[int]:
    """Apply only the certified zero-deck Boss/Lucario terminal override."""
    if (
        _enriching_zero_boss_lucario_last_observation is not None
        and obs_dict == _enriching_zero_boss_lucario_last_observation
        and _enriching_zero_boss_lucario_last_action is not None
    ):
        return list(_enriching_zero_boss_lucario_last_action)

    inherited_quarantine = bool(_merge_start_quarantine_depth)
    stale_cleared = _enriching_zero_boss_lucario_prepare(obs_dict)
    had_transaction = bool(_enriching_zero_boss_lucario_latch)
    before_v2 = _enriching_zero_boss_lucario_snapshot_v2_state()
    block_lower_start = bool(
        stale_cleared or had_transaction or inherited_quarantine
    )
    if block_lower_start:
        _merge_push_start_quarantine()
    try:
        v2_action = _draw_free_v2_parent_agent(copy.deepcopy(obs_dict))
    finally:
        if block_lower_start:
            _merge_pop_start_quarantine()
    after_v2 = _enriching_zero_boss_lucario_snapshot_v2_state()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return _enriching_zero_boss_lucario_remember(obs_dict, v2_action)

    try:
        obs = to_observation_class(copy.deepcopy(obs_dict))
        if (
            obs.current is None
            or obs.select is None
            or not _draw_free_action_is_valid(obs, v2_action)
            or stale_cleared
        ):
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )

        lower_owner = any(
            bool(snapshot.get(key))
            for snapshot in (before_v2, after_v2)
            for key in (
                "certified_turn_plan",
                "draw_survival_terminal",
                "draw_free_terminal",
            )
        )
        if lower_owner:
            if had_transaction:
                _clear_enriching_zero_boss_lucario_latch()
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )

        if inherited_quarantine and not had_transaction:
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )

        if had_transaction:
            transaction_action = _enriching_zero_boss_lucario_advance(obs)
            if transaction_action is None:
                return _enriching_zero_boss_lucario_remember(
                    obs_dict, v2_action
                )
            if not _draw_free_action_is_valid(obs, transaction_action):
                _clear_enriching_zero_boss_lucario_latch()
                return _enriching_zero_boss_lucario_remember(
                    obs_dict, v2_action
                )
            if transaction_action != v2_action:
                replacement = _enriching_zero_boss_lucario_rerun_v2(
                    obs_dict, before_v2, transaction_action
                )
                if replacement != transaction_action:
                    _enriching_zero_boss_lucario_restore_v2_state(after_v2)
                    _clear_enriching_zero_boss_lucario_latch()
                    return _enriching_zero_boss_lucario_remember(
                        obs_dict, v2_action
                    )
            return _enriching_zero_boss_lucario_remember(
                obs_dict, transaction_action
            )

        _enriching_zero_boss_lucario_restore_v2_state(before_v2)
        exact_action = _source_transition_v2_parent_agent(copy.deepcopy(obs_dict))
        after_exact = _enriching_zero_boss_lucario_snapshot_v2_state()
        if not _draw_free_action_is_valid(obs, exact_action):
            _enriching_zero_boss_lucario_restore_v2_state(after_v2)
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )
        transaction_action = _enriching_zero_boss_lucario_start(
            obs,
            v2_action,
            exact_action,
            before_v2,
            after_v2,
            after_exact,
        )
        if transaction_action is None:
            _enriching_zero_boss_lucario_restore_v2_state(after_v2)
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )
        replacement = _enriching_zero_boss_lucario_rerun_v2(
            obs_dict, before_v2, transaction_action
        )
        if replacement != transaction_action:
            _enriching_zero_boss_lucario_restore_v2_state(after_v2)
            _clear_enriching_zero_boss_lucario_latch()
            return _enriching_zero_boss_lucario_remember(
                obs_dict, v2_action
            )
        return _enriching_zero_boss_lucario_remember(
            obs_dict, transaction_action
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        _enriching_zero_boss_lucario_restore_v2_state(after_v2)
        _clear_enriching_zero_boss_lucario_latch()
        return _enriching_zero_boss_lucario_remember(obs_dict, v2_action)


# ---------------------------------------------------------------------------
# EXPOSED_DUDUNSPARCE_RUN_AWAY_READY_ALAKAZAM_KO_TRANSACTION_V1
#
# The complete direct-terminal policy above remains the immediate parent.  The
# outer transaction below may replace only that parent's finalized unique END
# in an exact MAIN state.  It owns the resulting Run Away Draw -> promotion ->
# Powerful Hand callbacks only while every frozen public invariant survives.
# ---------------------------------------------------------------------------

_exposed_dudunsparce_transaction_latch = {}
_exposed_dudunsparce_last_observation = None
_exposed_dudunsparce_last_action = None

_EXPOSED_PARENT_LATCH_KEYS = (
    "hilda",
    "enriching",
    "fez",
    "active_psychic",
    "stranded",
    "certified_turn_plan",
    "draw_survival_terminal",
    "draw_free_terminal",
    "enriching_zero_boss_lucario",
)


def _clear_exposed_dudunsparce_transaction(*, clear_cache: bool = False) -> None:
    global _exposed_dudunsparce_last_observation
    global _exposed_dudunsparce_last_action
    _exposed_dudunsparce_transaction_latch.clear()
    if clear_cache:
        _exposed_dudunsparce_last_observation = None
        _exposed_dudunsparce_last_action = None


def _exposed_dudunsparce_remember(
    observation: dict, action: list[int]
) -> list[int]:
    global _exposed_dudunsparce_last_observation
    global _exposed_dudunsparce_last_action
    _exposed_dudunsparce_last_observation = copy.deepcopy(observation)
    _exposed_dudunsparce_last_action = tuple(action)
    return list(action)


def _exposed_dudunsparce_parent_owner(snapshot: dict) -> bool:
    return any(bool(snapshot.get(key)) for key in _EXPOSED_PARENT_LATCH_KEYS)


def _exposed_dudunsparce_action_is_valid(
    obs: Observation, action: list[int]
) -> bool:
    return (
        isinstance(action, list)
        and obs.select is not None
        and obs.select.minCount <= len(action) <= obs.select.maxCount
        and len(action) == len(set(action))
        and all(
            isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(obs.select.option)
            for index in action
        )
    )


def _exposed_dudunsparce_status_is_clear(player) -> bool:
    return _draw_free_status(player) == (False, False, False, False, False)


def _exposed_dudunsparce_public_counter_sources_are_clear(state) -> bool:
    """Reject every visible modifier that could change counter placement/KO."""
    dangerous = (
        "damage",
        "damage counter",
        "prevent",
        "protect",
        "weakness",
        "resistance",
        "knocked out",
        "can't be knocked out",
        "cannot be knocked out",
    )
    sources = []
    for player in state.players:
        for pokemon in list(player.active) + list(player.bench):
            if pokemon is None:
                return False
            sources.append(pokemon.id)
            sources.extend(card.id for card in pokemon.energyCards)
            sources.extend(card.id for card in pokemon.tools)
    sources.extend(card.id for card in state.stadium)
    for card_id in sources:
        data = card_table.get(card_id)
        if data is None:
            return False
        for skill in data.skills or []:
            text = _bridge_retaliation_normalized_text(skill.text)
            if any(marker in text for marker in dangerous):
                return False
    return True


def _exposed_dudunsparce_next_turn_ko_exposure(
    obs: Observation, source: Pokemon
) -> tuple | None:
    """Certify the opponent's already-payable Active Powerful Hand KO."""
    state = obs.current
    my_index = state.yourIndex
    theirs = state.players[1 - my_index]
    if (
        len(theirs.active) != 1
        or not _exposed_dudunsparce_status_is_clear(theirs)
        or not isinstance(theirs.handCount, int)
        or isinstance(theirs.handCount, bool)
        or theirs.handCount < 0
        or not _draw_free_powerful_hand_metadata_certified()
        or not _powerful_hand_target_is_publicly_clear(state, source)
        or not _exposed_dudunsparce_public_counter_sources_are_clear(state)
    ):
        return None
    attacker = theirs.active[0]
    if (
        attacker.id != Alakazam
        or not _draw_survival_known_stack_is_exact(attacker, 1 - my_index)
        or not _direct_terminal_max_hp_is_exact(state, attacker)
    ):
        return None
    energy_units = _bridge_retaliation_energy_units(attacker)
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    if (
        energy_units is None
        or powerful is None
        or _bridge_retaliation_can_pay(energy_units, powerful.energies) is not True
        or 20 * theirs.handCount < source.hp
    ):
        return None
    protected = (
        *_bridge_pokemon_component_serials(source),
        *_bridge_pokemon_component_serials(attacker),
    )
    if not _bridge_protected_serials_are_unique(state, protected):
        return None
    return (
        _bridge_pokemon_fingerprint(attacker),
        energy_units,
        theirs.handCount,
        20 * theirs.handCount,
        _bridge_target_fingerprint(source, state.players[my_index]),
    )


def _exposed_dudunsparce_ready_alakazam(
    obs: Observation,
) -> tuple[int, Pokemon, tuple[int, ...]] | None:
    state = obs.current
    my_index = state.yourIndex
    mine = state.players[my_index]
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    if powerful is None:
        return None
    ready = []
    for bench_index, pokemon in enumerate(mine.bench):
        if pokemon.id != Alakazam:
            continue
        if (
            not _draw_survival_known_stack_is_exact(pokemon, my_index)
            or not _direct_terminal_max_hp_is_exact(state, pokemon)
            or not _bridge_protected_serials_are_unique(
                state, _bridge_pokemon_component_serials(pokemon)
            )
        ):
            return None
        energy_units = _bridge_retaliation_energy_units(pokemon)
        if energy_units is None:
            return None
        payable = _bridge_retaliation_can_pay(energy_units, powerful.energies)
        if payable is None:
            return None
        if payable:
            ready.append((bench_index, pokemon, energy_units))
    return ready[0] if len(ready) == 1 else None


def _exposed_dudunsparce_ability_option(obs: Observation) -> int | None:
    matches = []
    for index, option in enumerate(obs.select.option):
        if (
            option.type == OptionType.ABILITY
            and option.area == AreaType.ACTIVE
            and option.index == 0
            and option.playerIndex is None
            and _draw_survival_option_unused_fields_are_none(
                option, {"area", "index"}
            )
        ):
            matches.append(index)
    return matches[0] if len(matches) == 1 else None


def _exposed_dudunsparce_target_certificate(
    obs: Observation, target: Pokemon
) -> tuple | None:
    state = obs.current
    opponent_index = 1 - state.yourIndex
    if (
        not _draw_survival_known_stack_is_exact(target, opponent_index)
        or not _direct_terminal_max_hp_is_exact(state, target)
        or not _direct_terminal_counter_target_is_clear(obs, target)
        or not _exposed_dudunsparce_status_is_clear(
            state.players[opponent_index]
        )
    ):
        return None
    commitment = _bridge_target_commitment_fingerprint(
        state, target, opponent_index
    )
    if commitment is None:
        return None
    return (
        _bridge_pokemon_fingerprint(target),
        commitment,
        _bridge_target_fingerprint(target, state.players[opponent_index]),
    )


def _exposed_dudunsparce_source_moves(source: Pokemon) -> tuple:
    return (
        (source.id, source.serial, int(AreaType.ACTIVE)),
        *(
            (card.id, card.serial, int(AreaType.PRE_EVOLUTION))
            for card in source.preEvolution
        ),
        *(
            (card.id, card.serial, int(AreaType.ENERGY))
            for card in source.energyCards
        ),
        *(
            (card.id, card.serial, int(AreaType.TOOL))
            for card in source.tools
        ),
    )


def _exposed_dudunsparce_public_snapshot(
    obs: Observation, *, allow_own_empty: bool = False
) -> dict | None:
    """Materialize the full public state, permitting the promotion vacancy."""
    state = obs.current
    if state is None or state.yourIndex not in (0, 1) or len(state.players) != 2:
        return None
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    allowed_own_active = (0, 1) if allow_own_empty else (1,)
    if (
        not isinstance(state.turn, int)
        or isinstance(state.turn, bool)
        or state.turn <= 0
        or not isinstance(state.turnActionCount, int)
        or isinstance(state.turnActionCount, bool)
        or state.turnActionCount < 0
        or state.result != -1
        or not isinstance(state.stadium, list)
        or any(
            not isinstance(value, bool)
            for value in (
                state.supporterPlayed,
                state.stadiumPlayed,
                state.energyAttached,
                state.retreated,
            )
        )
        or len(mine.active) not in allowed_own_active
        or len(theirs.active) != 1
        or _draw_survival_exact_hand(mine, my_index) is None
        or not isinstance(mine.deckCount, int)
        or isinstance(mine.deckCount, bool)
        or mine.deckCount < 0
        or not isinstance(theirs.deckCount, int)
        or isinstance(theirs.deckCount, bool)
        or theirs.deckCount < 0
        or not isinstance(theirs.handCount, int)
        or isinstance(theirs.handCount, bool)
        or theirs.handCount < 0
        or not 1 <= len(mine.prize) <= 6
        or not 1 <= len(theirs.prize) <= 6
        or any(
            not isinstance(value, bool)
            for player in (mine, theirs)
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
    for owner, player in enumerate(state.players):
        if (
            not isinstance(player.active, list)
            or not isinstance(player.bench, list)
            or any(
                pokemon is None
                or not _draw_survival_known_stack_is_exact(pokemon, owner)
                for pokemon in list(player.active) + list(player.bench)
            )
            or not isinstance(player.discard, list)
            or any(
                not _draw_survival_card_is_exact(card, owner)
                for card in player.discard
            )
            or any(
                card is not None
                and not _draw_survival_card_is_exact(card, owner)
                for card in player.prize
            )
        ):
            return None
    if any(
        not _draw_survival_card_is_exact(card, card.playerIndex)
        or card.playerIndex not in (0, 1)
        for card in state.stadium
    ):
        return None
    public_serials = _bridge_public_serials(state)
    if (
        any(not isinstance(serial, int) or serial <= 0 for serial in public_serials)
        or len(public_serials) != len(set(public_serials))
    ):
        return None
    own_hand = _draw_survival_exact_hand(mine, my_index)
    own_discard = _enriching_zero_boss_lucario_ordered_cards(
        mine.discard, my_index
    )
    opponent_discard = _enriching_zero_boss_lucario_ordered_cards(
        theirs.discard, 1 - my_index
    )
    stadium = _enriching_zero_boss_lucario_ordered_cards(state.stadium, None)
    if None in (own_hand, own_discard, opponent_discard, stadium):
        return None
    return {
        "turn": state.turn,
        "action_count": state.turnActionCount,
        "result": state.result,
        "supporter_played": state.supporterPlayed,
        "stadium_played": state.stadiumPlayed,
        "energy_attached": state.energyAttached,
        "retreated": state.retreated,
        "looking": state.looking,
        "own_hand": own_hand,
        "own_discard": own_discard,
        "own_prize": _draw_free_prize_rows(mine),
        "own_deck": mine.deckCount,
        "own_bench_max": mine.benchMax,
        "own_status": _draw_free_status(mine),
        "own_active": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.active
        ),
        "own_bench": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        ),
        "opponent_discard": opponent_discard,
        "opponent_prize": _draw_free_prize_rows(theirs),
        "opponent_deck": theirs.deckCount,
        "opponent_hand_count": theirs.handCount,
        "opponent_bench_max": theirs.benchMax,
        "opponent_status": _draw_free_status(theirs),
        "opponent_active": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.active
        ),
        "opponent_bench": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.bench
        ),
        "stadium": stadium,
    }


def _exposed_dudunsparce_start(
    obs: Observation,
    parent_action: list[int],
    before_parent: dict,
    after_parent: dict,
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    if (
        not _draw_free_exact_main_envelope(select)
        or state.turn < 2
        or state.result != -1
        or state.looking is not None
        or not state.supporterPlayed
        or not state.energyAttached
        or not _draw_survival_fixed_metadata_certified()
        or not _draw_free_powerful_hand_metadata_certified()
        or not _draw_survival_public_state_is_complete(obs)
        or not _exposed_dudunsparce_status_is_clear(mine)
        or _exposed_dudunsparce_transaction_latch
        or _exposed_dudunsparce_parent_owner(before_parent)
        or _exposed_dudunsparce_parent_owner(after_parent)
        or len(parent_action) != 1
        or not 0 <= parent_action[0] < len(select.option)
        or not _draw_survival_end_option_is_exact(
            select.option[parent_action[0]]
        )
        or sum(
            1
            for option in select.option
            if option.type == OptionType.END
            and _draw_survival_end_option_is_exact(option)
        )
        != 1
        or len(mine.active) != 1
        or len(theirs.active) != 1
    ):
        return None

    source = mine.active[0]
    if (
        source.id != Dudunsparce
        or source.appearThisTurn
        or source.hp >= source.maxHp
        or source.maxHp != card_table[Dudunsparce].hp
        or not _draw_survival_known_stack_is_exact(source, my_index)
        or [card.id for card in source.preEvolution] != [Dunsparce]
        or len(source.energyCards) > 2
        or source.tools
        or _bridge_retaliation_energy_units(source) is None
        or not _bridge_protected_serials_are_unique(
            state, _bridge_pokemon_component_serials(source)
        )
    ):
        return None
    ability_option = _exposed_dudunsparce_ability_option(obs)
    exposure = _exposed_dudunsparce_next_turn_ko_exposure(obs, source)
    promotion = _exposed_dudunsparce_ready_alakazam(obs)
    if ability_option is None or exposure is None or promotion is None:
        return None
    promotion_index, promotion_pokemon, promotion_energy = promotion

    target = theirs.active[0]
    target_certificate = _exposed_dudunsparce_target_certificate(obs, target)
    hand = _draw_survival_exact_hand(mine, my_index)
    if (
        target_certificate is None
        or hand is None
        or 20 * len(hand) < target.hp
    ):
        return None

    return_count = 1 + len(source.preEvolution) + len(source.energyCards)
    expected_deck = mine.deckCount - 3 + return_count
    target_prizes = prize_count(target)
    post_ko_prizes = len(mine.prize) - target_prizes
    snapshot = _exposed_dudunsparce_public_snapshot(obs)
    source_moves = _exposed_dudunsparce_source_moves(source)
    protected = (
        *_bridge_pokemon_component_serials(source),
        *_bridge_pokemon_component_serials(promotion_pokemon),
        *_bridge_pokemon_component_serials(target),
    )
    if (
        snapshot is None
        or not isinstance(mine.deckCount, int)
        or isinstance(mine.deckCount, bool)
        or mine.deckCount < 3
        or expected_deck < 1
        or target_prizes <= 0
        or post_ko_prizes < 0
        or not (post_ko_prizes == 0 or expected_deck > post_ko_prizes)
        or len(source_moves) != return_count
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None

    _exposed_dudunsparce_transaction_latch.update(
        transaction="EXPOSED_DUDUNSPARCE_RUN_AWAY_READY_ALAKAZAM_KO_TRANSACTION_V1",
        stage="await_promotion",
        turn=state.turn,
        player=my_index,
        start_action_count=state.turnActionCount,
        source_serial=source.serial,
        source_fingerprint=_bridge_pokemon_fingerprint(source),
        source_moves=source_moves,
        source_component_serials=tuple(
            _bridge_pokemon_component_serials(source)
        ),
        promotion_start_index=promotion_index,
        promotion_serial=promotion_pokemon.serial,
        promotion_fingerprint=_bridge_pokemon_fingerprint(promotion_pokemon),
        promotion_energy_units=promotion_energy,
        target_serial=target.serial,
        target_hp=target.hp,
        target_prizes=target_prizes,
        target_certificate=target_certificate,
        target_moves=_enriching_zero_boss_lucario_target_moves(target),
        pre_draw_hand=hand,
        pre_draw_damage=20 * len(hand),
        expected_hand_count=len(hand) + 3,
        expected_deck=expected_deck,
        own_prizes=len(mine.prize),
        post_ko_prizes=post_ko_prizes,
        return_count=return_count,
        exposure_certificate=exposure,
        start_snapshot=snapshot,
    )
    return [ability_option]


def _exposed_dudunsparce_snapshot_delta(
    actual: dict, expected: dict, changing: set[str]
) -> bool:
    return all(
        key in actual and (key in changing or actual[key] == value)
        for key, value in expected.items()
    )


def _exposed_dudunsparce_draw_logs_are_exact(
    obs: Observation, latch: dict, new_hand: tuple
) -> bool:
    my_index = latch["player"]
    draw_logs = [log for log in obs.logs if int(getattr(log, "type", -1)) == 4]
    move_logs = [log for log in obs.logs if int(getattr(log, "type", -1)) == 6]
    other_logs = [
        log
        for log in obs.logs
        if int(getattr(log, "type", -1)) not in (4, 6)
    ]
    if (
        len(draw_logs) != 3
        or len(move_logs) != latch.get("return_count")
        or len(other_logs) != 1
        or not _enriching_zero_boss_lucario_log_is_exact(
            other_logs[0], 0, {"playerIndex": my_index}
        )
    ):
        return False
    draw_rows = []
    for log in draw_logs:
        expected = {
            "playerIndex": my_index,
            "cardId": getattr(log, "cardId", None),
            "serial": getattr(log, "serial", None),
        }
        if not _enriching_zero_boss_lucario_log_is_exact(log, 4, expected):
            return False
        draw_rows.append(
            (expected["cardId"], expected["serial"], my_index)
        )
    if len(set(draw_rows)) != 3 or set(draw_rows) != set(new_hand):
        return False
    actual_moves = []
    for log in move_logs:
        expected = {
            "playerIndex": my_index,
            "cardId": getattr(log, "cardId", None),
            "serial": getattr(log, "serial", None),
            "fromArea": getattr(log, "fromArea", None),
            "toArea": AreaType.DECK,
        }
        if not _enriching_zero_boss_lucario_log_is_exact(log, 6, expected):
            return False
        actual_moves.append(
            (
                expected["cardId"],
                expected["serial"],
                int(expected["fromArea"]),
            )
        )
    return len(set(actual_moves)) == len(actual_moves) and set(actual_moves) == set(
        latch.get("source_moves") or ()
    )


def _exposed_dudunsparce_promotion_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    snapshot = _exposed_dudunsparce_public_snapshot(
        obs, allow_own_empty=True
    )
    start = latch.get("start_snapshot")
    if (
        snapshot is None
        or start is None
        or select.type != SelectType.CARD
        or select.context != SelectContext.TO_ACTIVE
        or select.minCount != 1
        or select.maxCount != 1
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or state.turnActionCount != latch.get("start_action_count") + 1
        or snapshot.get("own_active") != tuple()
        or snapshot.get("own_bench") != start.get("own_bench")
        or snapshot.get("own_deck") != latch.get("expected_deck")
        or snapshot.get("own_hand") is None
        or len(snapshot["own_hand"]) != latch.get("expected_hand_count")
        or not _exposed_dudunsparce_snapshot_delta(
            snapshot,
            start,
            {"action_count", "own_active", "own_hand", "own_deck"},
        )
        or any(
            serial in _bridge_public_serials(state)
            for serial in latch.get("source_component_serials") or ()
        )
    ):
        return None
    carried = set(latch.get("pre_draw_hand") or ())
    current_hand = tuple(snapshot["own_hand"])
    if len(carried) != len(latch.get("pre_draw_hand") or ()) or not carried <= set(
        current_hand
    ):
        return None
    new_hand = tuple(row for row in current_hand if row not in carried)
    if len(new_hand) != 3 or not _exposed_dudunsparce_draw_logs_are_exact(
        obs, latch, new_hand
    ):
        return None

    matching = []
    for option_index, option in enumerate(select.option):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.BENCH
            or option.playerIndex != my_index
            or not isinstance(option.index, int)
            or isinstance(option.index, bool)
            or not 0 <= option.index < len(mine.bench)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
        ):
            return None
        pokemon = mine.bench[option.index]
        if pokemon.serial == latch.get("promotion_serial"):
            matching.append(option_index)
    if len(matching) != 1:
        return None
    promotion = next(
        (
            pokemon
            for pokemon in mine.bench
            if pokemon.serial == latch.get("promotion_serial")
        ),
        None,
    )
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    units = None if promotion is None else _bridge_retaliation_energy_units(promotion)
    if (
        promotion is None
        or _bridge_pokemon_fingerprint(promotion)
        != latch.get("promotion_fingerprint")
        or units != latch.get("promotion_energy_units")
        or powerful is None
        or _bridge_retaliation_can_pay(units, powerful.energies) is not True
        or _exposed_dudunsparce_target_certificate(
            obs, state.players[1 - my_index].active[0]
        )
        != latch.get("target_certificate")
        or _exposed_dudunsparce_next_turn_ko_exposure_from_latch(obs, latch)
        is not True
    ):
        return None
    latch["post_draw_snapshot"] = snapshot
    latch["post_draw_hand"] = current_hand
    latch["new_draws"] = new_hand
    latch["stage"] = "await_attack"
    return [matching[0]]


def _exposed_dudunsparce_next_turn_ko_exposure_from_latch(
    obs: Observation, latch: dict
) -> bool:
    """Revalidate the frozen source exposure after it entered the hidden deck."""
    state = obs.current
    attacker = state.players[1 - state.yourIndex].active[0]
    certificate = latch.get("exposure_certificate")
    return (
        certificate is not None
        and _bridge_pokemon_fingerprint(attacker) == certificate[0]
        and _bridge_retaliation_energy_units(attacker) == certificate[1]
        and state.players[1 - state.yourIndex].handCount == certificate[2]
        and 20 * certificate[2] == certificate[3]
        and _exposed_dudunsparce_status_is_clear(
            state.players[1 - state.yourIndex]
        )
        and _exposed_dudunsparce_public_counter_sources_are_clear(state)
    )


def _exposed_dudunsparce_attack_action(
    obs: Observation, latch: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    snapshot = _exposed_dudunsparce_public_snapshot(obs)
    post_draw = latch.get("post_draw_snapshot")
    if (
        snapshot is None
        or post_draw is None
        or not _draw_free_exact_main_envelope(select)
        or state.turnActionCount != latch.get("start_action_count") + 2
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or snapshot.get("own_hand") != latch.get("post_draw_hand")
        or snapshot.get("own_deck") != latch.get("expected_deck")
        or not _exposed_dudunsparce_snapshot_delta(
            snapshot,
            post_draw,
            {"action_count", "own_active", "own_bench"},
        )
    ):
        return None
    promotion = mine.active[0]
    target = theirs.active[0]
    expected_bench = list(post_draw.get("own_bench") or ())
    matches = [
        index
        for index, row in enumerate(expected_bench)
        if row[1] == latch.get("promotion_serial")
    ]
    if len(matches) != 1:
        return None
    expected_bench.pop(matches[0])
    if (
        snapshot.get("own_active") != (latch.get("promotion_fingerprint"),)
        or snapshot.get("own_bench") != tuple(expected_bench)
        or _bridge_pokemon_fingerprint(promotion)
        != latch.get("promotion_fingerprint")
        or _exposed_dudunsparce_target_certificate(obs, target)
        != latch.get("target_certificate")
        or not _exposed_dudunsparce_status_is_clear(mine)
        or 20 * mine.handCount < target.hp
        or latch.get("pre_draw_damage", 0) < target.hp
        or not (
            latch.get("post_ko_prizes") == 0
            or mine.deckCount > latch.get("post_ko_prizes")
        )
        or _exposed_dudunsparce_next_turn_ko_exposure_from_latch(obs, latch)
        is not True
    ):
        return None
    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    energy_units = _bridge_retaliation_energy_units(promotion)
    if (
        powerful is None
        or energy_units != latch.get("promotion_energy_units")
        or _bridge_retaliation_can_pay(energy_units, powerful.energies) is not True
    ):
        return None
    if (
        len(obs.logs) != 1
        or not _enriching_zero_boss_lucario_log_is_exact(
            obs.logs[0],
            6,
            {
                "playerIndex": my_index,
                "cardId": Alakazam,
                "serial": latch.get("promotion_serial"),
                "fromArea": AreaType.BENCH,
                "toArea": AreaType.ACTIVE,
            },
        )
    ):
        return None
    attacks = []
    for option_index, option in enumerate(select.option):
        if option.type != OptionType.ATTACK and option.attackId is None:
            continue
        if (
            not _draw_survival_attack_option_is_exact(option)
            or option.attackId != ATTACK_POWERFUL_HAND
        ):
            return None
        attacks.append(option_index)
    if len(attacks) != 1:
        return None
    latch["pre_attack_snapshot"] = snapshot
    latch["actual_damage"] = 20 * mine.handCount
    latch["stage"] = "await_resolution"
    return [attacks[0]]


def _exposed_dudunsparce_resolution_is_exact(
    obs: Observation, latch: dict
) -> bool:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    expected = latch.get("pre_attack_snapshot")
    if (
        expected is None
        or state.turn != latch.get("turn")
        or state.turnActionCount != latch.get("start_action_count") + 3
        or state.result != -1
        or state.looking is not None
        or select.type != SelectType.CARD
        or select.context != SelectContext.TO_HAND
        or select.minCount != latch.get("target_prizes")
        or select.maxCount != latch.get("target_prizes")
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or _draw_survival_exact_hand(mine, my_index) != expected.get("own_hand")
        or mine.deckCount != expected.get("own_deck")
        or tuple(_bridge_pokemon_fingerprint(p) for p in mine.active)
        != expected.get("own_active")
        or tuple(_bridge_pokemon_fingerprint(p) for p in mine.bench)
        != expected.get("own_bench")
        or _enriching_zero_boss_lucario_ordered_cards(
            mine.discard, my_index
        )
        != expected.get("own_discard")
        or _draw_free_prize_rows(mine) != expected.get("own_prize")
        or len(theirs.active) != 0
        or tuple(_bridge_pokemon_fingerprint(p) for p in theirs.bench)
        != expected.get("opponent_bench")
        or theirs.deckCount != expected.get("opponent_deck")
        or theirs.handCount != expected.get("opponent_hand_count")
        or _draw_free_prize_rows(theirs) != expected.get("opponent_prize")
        or _draw_free_status(mine) != expected.get("own_status")
        or _draw_free_status(theirs) != expected.get("opponent_status")
        or _enriching_zero_boss_lucario_ordered_cards(state.stadium, None)
        != expected.get("stadium")
    ):
        return False
    target_rows = tuple(
        (card_id, serial, 1 - my_index)
        for card_id, serial, _ in latch.get("target_moves") or ()
    )
    before_discard = expected.get("opponent_discard") or ()
    after_discard = _enriching_zero_boss_lucario_ordered_cards(
        theirs.discard, 1 - my_index
    )
    if after_discard != before_discard + target_rows:
        return False
    for option in select.option:
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.PRIZE
            or option.playerIndex != my_index
            or not isinstance(option.index, int)
            or isinstance(option.index, bool)
            or not 0 <= option.index < len(mine.prize)
            or not _draw_survival_option_unused_fields_are_none(
                option, {"area", "index", "playerIndex"}
            )
        ):
            return False
    if len(select.option) < select.minCount:
        return False
    logs = obs.logs
    target_moves = latch.get("target_moves") or ()
    if len(logs) != 2 + len(target_moves):
        return False
    if not _enriching_zero_boss_lucario_log_is_exact(
        logs[0],
        15,
        {
            "playerIndex": my_index,
            "cardId": Alakazam,
            "serial": latch.get("promotion_serial"),
            "attackId": ATTACK_POWERFUL_HAND,
        },
    ) or not _enriching_zero_boss_lucario_log_is_exact(
        logs[1],
        16,
        {
            "playerIndex": 1 - my_index,
            "cardId": target_moves[0][0],
            "serial": latch.get("target_serial"),
            "value": -latch.get("actual_damage"),
            "putDamageCounter": True,
        },
    ):
        return False
    for log, (card_id, serial, from_area) in zip(logs[2:], target_moves):
        if not _enriching_zero_boss_lucario_log_is_exact(
            log,
            6,
            {
                "playerIndex": 1 - my_index,
                "cardId": card_id,
                "serial": serial,
                "fromArea": AreaType(from_area),
                "toArea": AreaType.DISCARD,
            },
        ):
            return False
    return True


def _exposed_dudunsparce_advance(obs: Observation) -> list[int] | None:
    latch = _exposed_dudunsparce_transaction_latch
    stage = latch.get("stage")
    if stage == "await_promotion":
        action = _exposed_dudunsparce_promotion_action(obs, latch)
        if action is None:
            _clear_exposed_dudunsparce_transaction()
        return action
    if stage == "await_attack":
        action = _exposed_dudunsparce_attack_action(obs, latch)
        if action is None:
            _clear_exposed_dudunsparce_transaction()
        return action
    if stage == "await_resolution":
        _exposed_dudunsparce_resolution_is_exact(obs, latch)
        _clear_exposed_dudunsparce_transaction()
        return None
    _clear_exposed_dudunsparce_transaction()
    return None


def _exposed_dudunsparce_prepare(obs_dict: dict) -> bool:
    if not _exposed_dudunsparce_transaction_latch:
        return False
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    if not isinstance(select, dict) or not isinstance(current, dict):
        _clear_exposed_dudunsparce_transaction()
        return True
    if (
        current.get("turn")
        != _exposed_dudunsparce_transaction_latch.get("turn")
        or current.get("yourIndex")
        != _exposed_dudunsparce_transaction_latch.get("player")
        or current.get("result") != -1
    ):
        _clear_exposed_dudunsparce_transaction()
        return True
    return False


def _exposed_dudunsparce_rerun_parent(
    obs_dict: dict, before_parent: dict, desired_action: list[int]
) -> list[int] | None:
    raw_select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    raw_options = raw_select.get("option") if isinstance(raw_select, dict) else None
    if (
        not isinstance(raw_options, list)
        or not desired_action
        or len(desired_action) != len(set(desired_action))
        or any(
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= len(raw_options)
            for index in desired_action
        )
        or raw_select.get("minCount") != 1
        or raw_select.get("maxCount") != 1
    ):
        return None
    reranked = copy.deepcopy(obs_dict)
    reranked["select"]["option"] = [
        copy.deepcopy(raw_options[index]) for index in desired_action
    ]
    _merge_restore_complete_state(before_parent)
    _merge_push_start_quarantine()
    try:
        reranked_action = _exposed_dudunsparce_parent_agent(reranked)
    finally:
        _merge_pop_start_quarantine()
    if (
        not isinstance(reranked_action, list)
        or len(reranked_action) != 1
        or not isinstance(reranked_action[0], int)
        or isinstance(reranked_action[0], bool)
        or not 0 <= reranked_action[0] < len(desired_action)
    ):
        return None
    return [desired_action[reranked_action[0]]]


def _active_three_prize_parent_agent(obs_dict: dict) -> list[int]:
    """Apply only the exposed-Dudunsparce atomic KO transaction."""
    if (
        _exposed_dudunsparce_last_observation is not None
        and obs_dict == _exposed_dudunsparce_last_observation
        and _exposed_dudunsparce_last_action is not None
    ):
        return list(_exposed_dudunsparce_last_action)

    inherited_quarantine = bool(_merge_start_quarantine_depth)
    stale_cleared = _exposed_dudunsparce_prepare(obs_dict)
    had_transaction = bool(_exposed_dudunsparce_transaction_latch)
    before_parent = _merge_snapshot_complete_state()
    block_lower_start = bool(
        stale_cleared or had_transaction or inherited_quarantine
    )
    if block_lower_start:
        _merge_push_start_quarantine()
    try:
        parent_action = _exposed_dudunsparce_parent_agent(
            copy.deepcopy(obs_dict)
        )
    finally:
        if block_lower_start:
            _merge_pop_start_quarantine()
    after_parent = _merge_snapshot_complete_state()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        _clear_exposed_dudunsparce_transaction()
        return _exposed_dudunsparce_remember(obs_dict, parent_action)

    try:
        obs = to_observation_class(copy.deepcopy(obs_dict))
        if (
            obs.current is None
            or obs.select is None
            or stale_cleared
            or not _exposed_dudunsparce_action_is_valid(obs, parent_action)
        ):
            return _exposed_dudunsparce_remember(obs_dict, parent_action)

        lower_owner = _exposed_dudunsparce_parent_owner(
            before_parent
        ) or _exposed_dudunsparce_parent_owner(after_parent)
        if lower_owner:
            if had_transaction:
                _clear_exposed_dudunsparce_transaction()
            return _exposed_dudunsparce_remember(obs_dict, parent_action)
        if inherited_quarantine and not had_transaction:
            return _exposed_dudunsparce_remember(obs_dict, parent_action)

        if had_transaction:
            transaction_action = _exposed_dudunsparce_advance(obs)
            if transaction_action is None:
                return _exposed_dudunsparce_remember(obs_dict, parent_action)
            if not _exposed_dudunsparce_action_is_valid(
                obs, transaction_action
            ):
                _clear_exposed_dudunsparce_transaction()
                return _exposed_dudunsparce_remember(obs_dict, parent_action)
            if transaction_action != parent_action:
                replacement = _exposed_dudunsparce_rerun_parent(
                    obs_dict, before_parent, transaction_action
                )
                if replacement != transaction_action:
                    _merge_restore_complete_state(after_parent)
                    _clear_exposed_dudunsparce_transaction()
                    return _exposed_dudunsparce_remember(
                        obs_dict, parent_action
                    )
            return _exposed_dudunsparce_remember(
                obs_dict, transaction_action
            )

        transaction_action = _exposed_dudunsparce_start(
            obs, parent_action, before_parent, after_parent
        )
        if transaction_action is None:
            return _exposed_dudunsparce_remember(obs_dict, parent_action)
        replacement = _exposed_dudunsparce_rerun_parent(
            obs_dict, before_parent, transaction_action
        )
        if replacement != transaction_action:
            _merge_restore_complete_state(after_parent)
            _clear_exposed_dudunsparce_transaction()
            return _exposed_dudunsparce_remember(obs_dict, parent_action)
        return _exposed_dudunsparce_remember(obs_dict, transaction_action)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        _merge_restore_complete_state(after_parent)
        _clear_exposed_dudunsparce_transaction()
        return _exposed_dudunsparce_remember(obs_dict, parent_action)


# ---------------------------------------------------------------------------
# CERTIFIED_ACTIVE_THREE_PRIZE_POWERFUL_HAND_KO_V1
#
# This outer, stateless guard may replace only one exact MAIN decision with the
# unique immediately lethal Powerful Hand attack against a publicly certified
# three-Prize Active.  Every inherited transaction keeps precedence, and the
# parent's complete state is restored after the quarantined witness rerun.
# ---------------------------------------------------------------------------

_active_three_prize_last_observation = None
_active_three_prize_last_action = None


def _active_three_prize_snapshot_parent_state() -> dict:
    return {
        "merge": _merge_snapshot_complete_state(),
        "exposed_dudunsparce": copy.deepcopy(
            _exposed_dudunsparce_transaction_latch
        ),
        "exposed_dudunsparce_last_observation": copy.deepcopy(
            _exposed_dudunsparce_last_observation
        ),
        "exposed_dudunsparce_last_action": copy.deepcopy(
            _exposed_dudunsparce_last_action
        ),
    }


def _active_three_prize_restore_parent_state(snapshot: dict) -> None:
    global _exposed_dudunsparce_last_observation
    global _exposed_dudunsparce_last_action
    _merge_restore_complete_state(snapshot["merge"])
    _exposed_dudunsparce_transaction_latch.clear()
    _exposed_dudunsparce_transaction_latch.update(
        copy.deepcopy(snapshot["exposed_dudunsparce"])
    )
    _exposed_dudunsparce_last_observation = copy.deepcopy(
        snapshot["exposed_dudunsparce_last_observation"]
    )
    _exposed_dudunsparce_last_action = copy.deepcopy(
        snapshot["exposed_dudunsparce_last_action"]
    )


def _active_three_prize_parent_owner(snapshot: dict) -> bool:
    return bool(snapshot.get("exposed_dudunsparce")) or (
        _exposed_dudunsparce_parent_owner(snapshot["merge"])
    )


def _active_three_prize_remember(
    observation: dict, action: list[int]
) -> list[int]:
    global _active_three_prize_last_observation
    global _active_three_prize_last_action
    _active_three_prize_last_observation = copy.deepcopy(observation)
    _active_three_prize_last_action = tuple(action)
    return list(action)


def _active_three_prize_local_tool_hp_delta(tool: Card) -> int | None:
    """Certify one exact, attachment-local Tool HP modifier."""
    data = card_table.get(tool.id)
    if data is None:
        return None
    texts = [
        " ".join(
            _normalized_skill_text(skill.text)
            .replace("pokﾃｩmon", "pokemon")
            .split()
        )
        for skill in (data.skills or [])
    ]
    hp_texts = [text for text in texts if " hp" in text]
    if not hp_texts:
        return 0
    prefix = "the pokemon this card is attached to gets +"
    suffix = " hp."
    if (
        data.cardType != CardType.TOOL
        or len(texts) != 1
        or len(hp_texts) != 1
        or not hp_texts[0].startswith(prefix)
        or not hp_texts[0].endswith(suffix)
    ):
        return None
    amount = hp_texts[0][len(prefix) : -len(suffix)]
    return int(amount) if amount.isdigit() and int(amount) > 0 else None


def _active_three_prize_max_hp_is_exact(state, pokemon: Pokemon) -> bool:
    """Match printed HP plus exact attachment-local Energy and Tool bonuses."""
    data = card_table.get(pokemon.id)
    if data is None or data.hp <= 0:
        return False
    expected = data.hp
    for player in state.players:
        for source in list(player.active) + list(player.bench):
            source_data = card_table.get(source.id)
            if source_data is None:
                return False
            if any(
                " hp" in (
                    " "
                    + " ".join(
                        _normalized_skill_text(skill.text)
                        .replace("pokﾃｩmon", "pokemon")
                        .split()
                    )
                )
                for skill in (source_data.skills or [])
            ):
                return False
            for tool in source.tools:
                delta = _active_three_prize_local_tool_hp_delta(tool)
                if delta is None:
                    return False
                if source.serial == pokemon.serial:
                    expected += delta
            for energy in source.energyCards:
                delta = _direct_terminal_local_energy_hp_delta(energy, source)
                if delta is None:
                    return False
                if source.serial == pokemon.serial:
                    expected += delta
    for stadium in state.stadium:
        stadium_data = card_table.get(stadium.id)
        if stadium_data is None or any(
            " hp" in (
                " "
                + " ".join(
                    _normalized_skill_text(skill.text)
                    .replace("pokﾃｩmon", "pokemon")
                    .split()
                )
            )
            for skill in (stadium_data.skills or [])
        ):
            return False
    return pokemon.maxHp == expected


def _active_three_prize_powerful_hand_action(
    obs: Observation, obs_dict: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    if (
        not _draw_free_exact_main_envelope(select)
        or state.result != -1
        or state.looking is not None
        or not isinstance(state.turn, int)
        or isinstance(state.turn, bool)
        or state.turn < 2
        or _merge_start_quarantine_depth != 0
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _certified_turn_plan_latch
        or _draw_survival_terminal_latch
        or _draw_free_terminal_evolution_latch
        or _enriching_zero_boss_lucario_latch
        or _exposed_dudunsparce_transaction_latch
        or not _draw_survival_public_state_is_complete(obs)
        or not _draw_free_powerful_hand_metadata_certified()
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or not _exposed_dudunsparce_status_is_clear(mine)
        or not _exposed_dudunsparce_status_is_clear(theirs)
    ):
        return None

    active = mine.active[0]
    target = theirs.active[0]
    raw_current = obs_dict.get("current") if isinstance(obs_dict, dict) else None
    raw_players = (
        raw_current.get("players") if isinstance(raw_current, dict) else None
    )
    if not isinstance(raw_players, list) or len(raw_players) != 2:
        return None
    raw_mine = raw_players[my_index]
    raw_theirs = raw_players[1 - my_index]
    raw_active = raw_mine.get("active") if isinstance(raw_mine, dict) else None
    raw_target = raw_theirs.get("active") if isinstance(raw_theirs, dict) else None
    if (
        not isinstance(raw_active, list)
        or len(raw_active) != 1
        or not isinstance(raw_active[0], dict)
        or raw_active[0].get("playerIndex") != my_index
        or raw_active[0].get("id") != active.id
        or raw_active[0].get("serial") != active.serial
        or not isinstance(raw_target, list)
        or len(raw_target) != 1
        or not isinstance(raw_target[0], dict)
        or raw_target[0].get("playerIndex") != 1 - my_index
        or raw_target[0].get("id") != target.id
        or raw_target[0].get("serial") != target.serial
    ):
        return None

    hand = _draw_survival_exact_hand(mine, my_index)
    active_data = card_table.get(active.id)
    target_data = card_table.get(target.id)
    target_energy_ids = {card.id for card in target.energyCards}
    if (
        active.id != Alakazam
        or active_data is None
        or active_data.hp <= 0
        or not _draw_survival_known_stack_is_exact(active, my_index)
        or not _active_three_prize_max_hp_is_exact(state, active)
        or target_data is None
        or target_data.hp <= 0
        or not _draw_survival_known_stack_is_exact(target, 1 - my_index)
        or not _active_three_prize_max_hp_is_exact(state, target)
        or Mist_Energy in target_energy_ids
        or Rock_Fighting_Energy in target_energy_ids
        or not _direct_terminal_counter_target_is_clear(obs, target)
        or _turn_plan_visible_effect_fingerprint(state) is None
        or hand is None
        or len(hand) != mine.handCount
        or prize_count(target) != 3
        or not isinstance(target.hp, int)
        or isinstance(target.hp, bool)
        or target.hp <= 0
        or 20 * len(hand) < target.hp
    ):
        return None

    powerful = attack_table.get(ATTACK_POWERFUL_HAND)
    energy_units = _bridge_retaliation_energy_units(active)
    if (
        powerful is None
        or energy_units is None
        or _bridge_retaliation_can_pay(energy_units, powerful.energies) is not True
    ):
        return None

    powerful_options = []
    for option_index, option in enumerate(select.option):
        if option.type != OptionType.ATTACK and option.attackId is None:
            continue
        if (
            not _draw_survival_attack_option_is_exact(option)
            or option.attackId != ATTACK_POWERFUL_HAND
        ):
            return None
        powerful_options.append(option_index)
    return [powerful_options[0]] if len(powerful_options) == 1 else None


def _active_three_prize_rerun_parent(
    obs_dict: dict,
    before_parent: dict,
    after_parent: dict,
    desired_action: list[int],
) -> list[int] | None:
    raw_select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    raw_options = raw_select.get("option") if isinstance(raw_select, dict) else None
    if (
        not isinstance(raw_options, list)
        or len(desired_action) != 1
        or not isinstance(desired_action[0], int)
        or isinstance(desired_action[0], bool)
        or not 0 <= desired_action[0] < len(raw_options)
        or raw_select.get("minCount") != 1
        or raw_select.get("maxCount") != 1
    ):
        return None
    reranked = copy.deepcopy(obs_dict)
    reranked["select"]["option"] = [
        copy.deepcopy(raw_options[desired_action[0]])
    ]
    try:
        _active_three_prize_restore_parent_state(before_parent)
        _merge_push_start_quarantine()
        try:
            reranked_action = _active_three_prize_parent_agent(reranked)
        finally:
            _merge_pop_start_quarantine()
        if (
            not isinstance(reranked_action, list)
            or len(reranked_action) != 1
            or reranked_action[0] != 0
        ):
            return None
        return list(desired_action)
    finally:
        _active_three_prize_restore_parent_state(after_parent)


def agent(obs_dict: dict) -> list[int]:
    """Apply only the certified immediate Active three-Prize KO guard."""
    if (
        _active_three_prize_last_observation is not None
        and obs_dict == _active_three_prize_last_observation
        and _active_three_prize_last_action is not None
    ):
        return list(_active_three_prize_last_action)

    before_parent = _active_three_prize_snapshot_parent_state()
    parent_action = _active_three_prize_parent_agent(copy.deepcopy(obs_dict))
    after_parent = _active_three_prize_snapshot_parent_state()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        return _active_three_prize_remember(obs_dict, parent_action)
    try:
        obs = to_observation_class(copy.deepcopy(obs_dict))
        if (
            obs.current is None
            or obs.select is None
            or not _exposed_dudunsparce_action_is_valid(obs, parent_action)
            or _merge_start_quarantine_depth != 0
            or _active_three_prize_parent_owner(before_parent)
            or _active_three_prize_parent_owner(after_parent)
        ):
            return _active_three_prize_remember(obs_dict, parent_action)
        desired_action = _active_three_prize_powerful_hand_action(obs, obs_dict)
        if (
            desired_action is None
            or not _exposed_dudunsparce_action_is_valid(obs, desired_action)
        ):
            return _active_three_prize_remember(obs_dict, parent_action)
        rerun_action = _active_three_prize_rerun_parent(
            obs_dict, before_parent, after_parent, desired_action
        )
        if rerun_action != desired_action:
            return _active_three_prize_remember(obs_dict, parent_action)
        return _active_three_prize_remember(obs_dict, desired_action)
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError):
        _active_three_prize_restore_parent_state(after_parent)
        return _active_three_prize_remember(obs_dict, parent_action)
