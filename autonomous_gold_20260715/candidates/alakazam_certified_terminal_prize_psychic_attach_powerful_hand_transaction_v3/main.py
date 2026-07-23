import os
import sys
import hashlib
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
Full_Metal_Lab = 1244

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
_guarded_teleportation_latch = {}
_turn_objective_recovery_latch = {}
_terminal_prize_psychic_attach_latch = {}
_guarded_teleportation_semantic_failure = {}
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


def _clear_guarded_teleportation_latch() -> None:
    _guarded_teleportation_latch.clear()


def _clear_turn_objective_recovery_latch() -> None:
    _turn_objective_recovery_latch.clear()


def _clear_terminal_prize_psychic_attach_latch() -> None:
    _terminal_prize_psychic_attach_latch.clear()


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
    _clear_guarded_teleportation_latch()
    _clear_turn_objective_recovery_latch()
    _clear_terminal_prize_psychic_attach_latch()
    if clear_cache:
        _clear_decision_cache()


def _two_prize_freeze_raw(value):
    """Make the public raw callback hashable for fail-closed cache reuse."""
    if isinstance(value, dict):
        return tuple(
            (key, _two_prize_freeze_raw(item))
            for key, item in sorted(value.items())
        )
    if isinstance(value, list):
        return tuple(_two_prize_freeze_raw(item) for item in value)
    return value


def _decision_signature(
    obs: Observation, raw_obs: dict | None = None
) -> tuple:
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
    teleport_guard_signature = None
    if _guarded_teleportation_latch:
        teleport_guard_signature = (
            _guarded_teleportation_latch.get("stage"),
            _guarded_teleportation_latch.get("turn"),
            _guarded_teleportation_latch.get("player"),
            _guarded_teleportation_latch.get("source_serial"),
            _guarded_teleportation_latch.get("target_serial"),
            _guarded_teleportation_latch.get("target_id"),
            _guarded_teleportation_latch.get("target_index"),
            _guarded_teleportation_latch.get("target_score"),
            _guarded_teleportation_latch.get("start_action_count"),
        )
    recovery_guard_signature = None
    if _turn_objective_recovery_latch:
        recovery_guard_signature = (
            _turn_objective_recovery_latch.get("plan_id"),
            _turn_objective_recovery_latch.get("snapshot_hash"),
            _turn_objective_recovery_latch.get("stage"),
            _turn_objective_recovery_latch.get("turn"),
            _turn_objective_recovery_latch.get("player"),
            _turn_objective_recovery_latch.get("ash_serial"),
            _turn_objective_recovery_latch.get("selected_serials"),
        )
    terminal_prize_attach_signature = None
    if _terminal_prize_psychic_attach_latch:
        terminal_prize_attach_signature = _two_prize_freeze_raw(
            _terminal_prize_psychic_attach_latch
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
        teleport_guard_signature,
        recovery_guard_signature,
        terminal_prize_attach_signature,
        option_signature,
        (
            None
            if raw_obs is None
            else _two_prize_freeze_raw(
                {
                    "current": raw_obs.get("current"),
                    "select": raw_obs.get("select"),
                    "logs": raw_obs.get("logs"),
                }
            )
        ),
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
        (
            _guarded_teleportation_latch,
            _clear_guarded_teleportation_latch,
        ),
        (
            _turn_objective_recovery_latch,
            _clear_turn_objective_recovery_latch,
        ),
        (
            _terminal_prize_psychic_attach_latch,
            _clear_terminal_prize_psychic_attach_latch,
        ),
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


def _exact_v3_switch_score(
    pokemon: Pokemon, opponent_active_hp: int
) -> int:
    """Purely reproduce the parent's SWITCH score for one Bench slot."""
    if pokemon.id == Alakazam:
        return 100 + 10 * len(pokemon.energies)
    if pokemon.id == Kadabra:
        return 90 if opponent_active_hp <= 30 else 30
    if pokemon.id == Abra:
        return 10
    if pokemon.id in DUNSPARCE_LINE:
        return 5
    return 1


def _predict_exact_v3_retreat_promotion(
    bench: list[Pokemon], opponent_active_hp: int, player_index: int
) -> tuple[int, int, int, int, tuple] | None:
    """Predict the unique exact-v3 promotion from the current Bench order."""
    if (
        not isinstance(opponent_active_hp, int)
        or opponent_active_hp <= 0
        or not bench
    ):
        return None
    scored = []
    for bench_index, pokemon in enumerate(bench):
        if not _bridge_pokemon_is_publicly_complete(pokemon, player_index):
            return None
        score = _exact_v3_switch_score(pokemon, opponent_active_hp)
        scored.append((score, bench_index, pokemon))
    highest = max(row[0] for row in scored)
    winners = [row for row in scored if row[0] == highest]
    if len(winners) != 1:
        return None
    score, bench_index, pokemon = winners[0]
    return (
        bench_index,
        pokemon.serial,
        pokemon.id,
        score,
        _bridge_pokemon_fingerprint(pokemon),
    )


def _guarded_teleportation_effects_are_publicly_clear(
    state, opponent_active: Pokemon, player_index: int
) -> bool:
    """Reject public damage reactions or effects that can alter the switch."""
    opponent_index = 1 - player_index
    if (
        not _bridge_pokemon_is_publicly_complete(
            opponent_active, opponent_index
        )
        or opponent_active.hp <= 10
        or not _powerful_hand_target_is_publicly_clear(
            state, opponent_active
        )
    ):
        return False

    reaction_markers = (
        "when this pokemon is damaged by an attack",
        "if this pokemon is damaged by an attack",
        "whenever this pokemon is damaged by an attack",
        "after this pokemon is damaged by an attack",
        "the attacking pokemon",
        "pokemon that attacked",
        "when your opponent's pokemon attacks",
        "whenever your opponent's pokemon attacks",
        "switch the attacking pokemon",
        "put the attacking pokemon",
        "shuffle the attacking pokemon",
        "return the attacking pokemon",
    )
    switch_block_markers = (
        "can't be switched",
        "cannot be switched",
        "can't switch",
        "cannot switch",
    )
    visible_effect_cards = []
    for owner_index, owner in enumerate(state.players):
        for pokemon in list(owner.active) + list(owner.bench):
            if not _bridge_pokemon_is_publicly_complete(
                pokemon, owner_index
            ):
                return False
            data = card_table.get(pokemon.id)
            if data is None:
                return False
            visible_effect_cards.append(data)
            for attached in list(pokemon.energyCards) + list(pokemon.tools):
                attached_data = card_table.get(attached.id)
                if attached_data is None:
                    return False
                visible_effect_cards.append(attached_data)
    for stadium in state.stadium:
        stadium_data = card_table.get(stadium.id)
        if stadium_data is None:
            return False
        visible_effect_cards.append(stadium_data)

    for data in visible_effect_cards:
        for skill in data.skills or []:
            text = " ".join(_normalized_skill_text(skill.text).split())
            if any(marker in text for marker in reaction_markers):
                return False
            if any(marker in text for marker in switch_block_markers):
                return False
    return True


def _guarded_teleportation_static_pokemon_fingerprint(
    pokemon: Pokemon,
) -> tuple:
    """Fingerprint a Pokemon while allowing only its current HP to change."""
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.maxHp,
        pokemon.appearThisTurn,
        getattr(pokemon, "playerIndex", None),
        tuple(int(energy) for energy in pokemon.energies),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.energyCards),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.tools),
        tuple(_bridge_card_fingerprint(card) for card in pokemon.preEvolution),
    )


def _guarded_teleportation_conditions(state) -> tuple:
    return tuple(
        condition
        for player in state.players
        for condition in (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        )
    )


def _guarded_teleportation_group_fingerprint(cards) -> tuple | None:
    rows = []
    for card in cards:
        if (
            card is None
            or card.id <= 0
            or card.serial <= 0
            or card_table.get(card.id) is None
        ):
            return None
        rows.append(_bridge_card_fingerprint(card))
    if len({row[1] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def _mark_guarded_teleportation_failure(
    obs: Observation, reason: str
) -> None:
    state = obs.current
    select = obs.select
    _guarded_teleportation_semantic_failure.clear()
    _guarded_teleportation_semantic_failure.update(
        reason=reason,
        turn=getattr(state, "turn", None),
        player=getattr(state, "yourIndex", None),
        context=(
            int(select.context)
            if select is not None and select.context is not None
            else None
        ),
    )
    _clear_guarded_teleportation_latch()


def _start_guarded_teleportation_continuity(
    obs: Observation, scores: list[int], parent_action: list[int]
) -> list[int] | None:
    """Replace only a finalized exact-v3 RETREAT with Teleportation."""
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent_active = theirs.active[0] if theirs.active else None
    if (
        select.context != SelectContext.MAIN
        or len(parent_action) != 1
        or parent_action[0] < 0
        or parent_action[0] >= len(select.option)
        or len(scores) != len(select.option)
        or select.option[parent_action[0]].type != OptionType.RETREAT
        or select.minCount > 1
        or select.maxCount < 1
        or state.turn < 2
        or state.result != -1
        or state.retreated
        or _guarded_teleportation_latch
        or _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or active is None
        or active.id != Abra
        or not _bridge_pokemon_is_publicly_complete(active, my_index)
        or opponent_active is None
        or mine.hand is None
        or len(mine.hand) != mine.handCount
        or any(
            (
                mine.poisoned,
                mine.burned,
                mine.asleep,
                mine.paralyzed,
                mine.confused,
            )
        )
        or not any(
            card.id in PSYCHIC_ENERGY_IDS for card in active.energyCards
        )
        or EnergyType.PSYCHIC not in active.energies
    ):
        return None

    teleport_data = attack_table.get(ATTACK_TELEPORTATION)
    if (
        teleport_data is None
        or teleport_data.damage != 10
        or tuple(teleport_data.energies) != (EnergyType.PSYCHIC,)
        or " ".join(
            _normalized_skill_text(teleport_data.text).split()
        )
        != "switch this pokemon with 1 of your benched pokemon."
        or card_table.get(Abra) is None
        or tuple(card_table[Abra].attacks) != (ATTACK_TELEPORTATION,)
    ):
        return None

    allowed_counts = {
        OptionType.ATTACK: 0,
        OptionType.RETREAT: 0,
        OptionType.END: 0,
    }
    teleport_indices = []
    invariant_play_ids = []
    for option_index, option in enumerate(select.option):
        if option.type == OptionType.PLAY:
            # This narrow two-card dead-option certificate does not admit the
            # separate single-PLAY census controls.  Battle Cage's score
            # depends only on the opponent/stadium and Genesect's only on
            # opponent ACE use plus Helmet/Poke Pad in hand; neither can
            # change when our recorded Kadabra becomes Active.
            played = get_card(
                obs, AreaType.HAND, option.index, my_index
            )
            if (
                played is None
                or played.id not in (Battle_Cage, Genesect)
                or scores[option_index] > 0
            ):
                return None
            invariant_play_ids.append(played.id)
            continue
        if option.type not in allowed_counts:
            return None
        allowed_counts[option.type] += 1
        if option.type == OptionType.ATTACK:
            if option.attackId != ATTACK_TELEPORTATION:
                return None
            teleport_indices.append(option_index)
    if (
        allowed_counts
        != {
            OptionType.ATTACK: 1,
            OptionType.RETREAT: 1,
            OptionType.END: 1,
        }
        or len(teleport_indices) != 1
        or invariant_play_ids not in (
            [],
            [Battle_Cage, Genesect],
            [Genesect, Battle_Cage],
        )
    ):
        return None

    prediction = _predict_exact_v3_retreat_promotion(
        mine.bench, opponent_active.hp, my_index
    )
    if prediction is None:
        return None
    (
        target_index,
        target_serial,
        target_id,
        target_score,
        target_fingerprint,
    ) = prediction
    target = mine.bench[target_index]
    target_data = card_table.get(target.id)
    if (
        target_data is None
        or not target_data.attacks
        or any(
            attack_table.get(attack_id) is None
            or not attack_table[attack_id].energies
            for attack_id in target_data.attacks
        )
        or target.energies
        or target.energyCards
        or not _guarded_teleportation_effects_are_publicly_clear(
            state, opponent_active, my_index
        )
    ):
        return None

    if not state.energyAttached:
        for option in select.option:
            if (
                option.type == OptionType.ATTACH
                and option.inPlayArea == AreaType.BENCH
                and option.inPlayIndex == target_index
                and option.playerIndex in (None, my_index)
            ):
                card = get_card(obs, AreaType.HAND, option.index, my_index)
                data = card_table.get(card.id) if card is not None else None
                if data is None or data.cardType in (
                    CardType.BASIC_ENERGY,
                    CardType.SPECIAL_ENERGY,
                ):
                    return None

    hand_fingerprint = _guarded_teleportation_group_fingerprint(mine.hand)
    discard_fingerprint = _guarded_teleportation_group_fingerprint(
        mine.discard
    )
    opponent_discard_fingerprint = (
        _guarded_teleportation_group_fingerprint(theirs.discard)
    )
    stadium_fingerprint = _guarded_teleportation_group_fingerprint(
        state.stadium
    )
    protected = [
        *_bridge_pokemon_component_serials(active),
        *(
            serial
            for pokemon in mine.bench
            for serial in _bridge_pokemon_component_serials(pokemon)
        ),
        *_bridge_pokemon_component_serials(opponent_active),
        *(
            serial
            for pokemon in theirs.bench
            for serial in _bridge_pokemon_component_serials(pokemon)
        ),
    ]
    if (
        hand_fingerprint is None
        or discard_fingerprint is None
        or opponent_discard_fingerprint is None
        or stadium_fingerprint is None
        or not _bridge_protected_serials_are_unique(state, protected)
    ):
        return None

    _guarded_teleportation_semantic_failure.clear()
    _guarded_teleportation_latch.update(
        stage="await_switch",
        turn=state.turn,
        player=my_index,
        start_action_count=state.turnActionCount,
        source_serial=active.serial,
        source_fingerprint=_bridge_pokemon_fingerprint(active),
        bench_fingerprints=tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        ),
        target_serial=target_serial,
        target_id=target_id,
        target_index=target_index,
        target_score=target_score,
        target_fingerprint=target_fingerprint,
        opponent_active_start_hp=opponent_active.hp,
        opponent_active_static=(
            _guarded_teleportation_static_pokemon_fingerprint(
                opponent_active
            )
        ),
        opponent_bench_fingerprints=tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.bench
        ),
        hand_fingerprint=hand_fingerprint,
        discard_fingerprint=discard_fingerprint,
        opponent_discard_fingerprint=opponent_discard_fingerprint,
        stadium_fingerprint=stadium_fingerprint,
        own_deck_count=mine.deckCount,
        opponent_deck_count=theirs.deckCount,
        own_prize_count=len(mine.prize),
        opponent_prize_count=len(theirs.prize),
        energy_attached=state.energyAttached,
        supporter_played=state.supporterPlayed,
        stadium_played=state.stadiumPlayed,
        retreated=state.retreated,
        conditions=_guarded_teleportation_conditions(state),
    )
    return [teleport_indices[0]]


def _guarded_teleportation_overlay(
    obs: Observation,
) -> list[int] | None:
    """Select the frozen target on only the immediate Teleport SWITCH."""
    if not _guarded_teleportation_latch:
        return None
    latch = _guarded_teleportation_latch
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    active = mine.active[0] if mine.active else None
    opponent_active = theirs.active[0] if theirs.active else None

    if latch.get("stage") != "await_switch":
        _mark_guarded_teleportation_failure(obs, "invalid_stage")
        return None
    if (
        state.turn != latch.get("turn")
        or my_index != latch.get("player")
    ):
        _clear_guarded_teleportation_latch()
        return None
    if (
        select.context != SelectContext.SWITCH
        or state.turnActionCount != latch.get("start_action_count") + 1
        or state.result != -1
        or state.energyAttached != latch.get("energy_attached")
        or state.supporterPlayed != latch.get("supporter_played")
        or state.stadiumPlayed != latch.get("stadium_played")
        or state.retreated != latch.get("retreated")
        or select.minCount > 1
        or select.maxCount < 1
        or active is None
        or active.serial != latch.get("source_serial")
        or _bridge_pokemon_fingerprint(active)
        != latch.get("source_fingerprint")
        or tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        )
        != latch.get("bench_fingerprints")
        or _guarded_teleportation_group_fingerprint(mine.hand)
        != latch.get("hand_fingerprint")
        or _guarded_teleportation_group_fingerprint(mine.discard)
        != latch.get("discard_fingerprint")
        or _guarded_teleportation_group_fingerprint(theirs.discard)
        != latch.get("opponent_discard_fingerprint")
        or _guarded_teleportation_group_fingerprint(state.stadium)
        != latch.get("stadium_fingerprint")
        or mine.deckCount != latch.get("own_deck_count")
        or theirs.deckCount != latch.get("opponent_deck_count")
        or len(mine.prize) != latch.get("own_prize_count")
        or len(theirs.prize) != latch.get("opponent_prize_count")
        or _guarded_teleportation_conditions(state)
        != latch.get("conditions")
        or opponent_active is None
        or _guarded_teleportation_static_pokemon_fingerprint(
            opponent_active
        )
        != latch.get("opponent_active_static")
        or tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in theirs.bench
        )
        != latch.get("opponent_bench_fingerprints")
        or not isinstance(latch.get("opponent_active_start_hp"), int)
        or opponent_active.hp <= 0
        or (
            latch.get("opponent_active_start_hp") - opponent_active.hp
            not in (10, 20)
        )
    ):
        _mark_guarded_teleportation_failure(
            obs, "unexpected_or_stale_switch"
        )
        return None

    context_ids = {
        getattr(select.effect, "id", None),
        getattr(select.contextCard, "id", None),
    } - {None}
    if context_ids and context_ids != {Abra}:
        _mark_guarded_teleportation_failure(
            obs, "unexpected_switch_effect"
        )
        return None

    matches = []
    offered_serials = []
    for option_index, option in enumerate(select.option):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.BENCH
            or option.playerIndex not in (None, my_index)
            or not isinstance(option.index, int)
            or option.index < 0
            or option.index >= len(mine.bench)
        ):
            _mark_guarded_teleportation_failure(
                obs, "malformed_switch_option"
            )
            return None
        pokemon = mine.bench[option.index]
        offered_serials.append(pokemon.serial)
        if (
            option.index == latch.get("target_index")
            and pokemon.serial == latch.get("target_serial")
            and pokemon.id == latch.get("target_id")
            and _bridge_pokemon_fingerprint(pokemon)
            == latch.get("target_fingerprint")
        ):
            matches.append(option_index)
    if (
        len(offered_serials) != len(set(offered_serials))
        or len(matches) != 1
    ):
        _mark_guarded_teleportation_failure(
            obs, "recorded_target_unavailable"
        )
        return None

    action = [matches[0]]
    _clear_guarded_teleportation_latch()
    return action


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


def _two_prize_raw_matches(parsed, raw) -> bool:
    """Require every raw public field to agree with its parsed value."""
    if parsed is None:
        return raw is None
    if isinstance(parsed, bool):
        return isinstance(raw, bool) and parsed is raw
    if isinstance(parsed, int):
        return (
            isinstance(raw, int)
            and not isinstance(raw, bool)
            and int(parsed) == raw
        )
    if isinstance(parsed, (str, float)):
        return type(parsed) is type(raw) and parsed == raw
    if isinstance(parsed, list):
        return isinstance(raw, list) and len(parsed) == len(raw) and all(
            _two_prize_raw_matches(left, right)
            for left, right in zip(parsed, raw)
        )
    if hasattr(parsed, "__dataclass_fields__"):
        if not isinstance(raw, dict):
            return False
        fields = vars(parsed)
        allowed = set(fields)
        if isinstance(parsed, Pokemon):
            # The wire Pokemon includes ownership while the public dataclass
            # omits it.  Ownership is checked against its containing zone by
            # _two_prize_raw_parsed_agree.
            allowed.add("playerIndex")
        if not set(raw).issubset(allowed):
            return False
        for key, value in fields.items():
            if key in raw:
                if not _two_prize_raw_matches(value, raw[key]):
                    return False
            elif value is not None:
                return False
        return True
    return type(parsed) is type(raw) and parsed == raw


def _two_prize_raw_pokemon_owner_is_exact(raw: dict, owner: int) -> bool:
    if raw.get("playerIndex") != owner:
        return False
    for group in ("energyCards", "tools", "preEvolution"):
        cards = raw.get(group)
        if not isinstance(cards, list) or any(
            not isinstance(card, dict) or card.get("playerIndex") != owner
            for card in cards
        ):
            return False
    return True


def _two_prize_raw_parsed_agree(obs_dict: dict, obs: Observation) -> bool:
    """Check the complete current/select/log public envelope and ownership."""
    if (
        not isinstance(obs_dict, dict)
        or obs.current is None
        or obs.select is None
        or not _two_prize_raw_matches(
            obs.current, obs_dict.get("current")
        )
        or not _two_prize_raw_matches(obs.select, obs_dict.get("select"))
        or not _two_prize_raw_matches(obs.logs, obs_dict.get("logs"))
    ):
        return False
    raw_state = obs_dict["current"]
    raw_players = raw_state.get("players")
    if not isinstance(raw_players, list) or len(raw_players) != 2:
        return False
    for owner, raw_player in enumerate(raw_players):
        if not isinstance(raw_player, dict):
            return False
        for zone in ("active", "bench"):
            pokemon = raw_player.get(zone)
            if not isinstance(pokemon, list) or any(
                not isinstance(card, dict)
                or not _two_prize_raw_pokemon_owner_is_exact(card, owner)
                for card in pokemon
                if card is not None
            ):
                return False
    return True


def _two_prize_option_is_exact(
    option, option_type: OptionType, **expected
) -> bool:
    for field, value in vars(option).items():
        wanted = option_type if field == "type" else expected.get(field)
        if value != wanted:
            return False
    return True


def _two_prize_lineage_is_complete(
    pokemon: Pokemon, owner: int
) -> bool:
    data = card_table.get(pokemon.id)
    if data is None or data.cardType != CardType.POKEMON:
        return False
    lineage = list(pokemon.preEvolution)
    if any(
        card.id <= 0
        or card.serial <= 0
        or card.playerIndex != owner
        or card_table.get(card.id) is None
        or card_table[card.id].cardType != CardType.POKEMON
        for card in lineage
    ):
        return False
    if data.basic:
        return not data.stage1 and not data.stage2 and not lineage
    if data.stage1:
        if data.stage2 or len(lineage) != 1:
            return False
        base = card_table[lineage[0].id]
        return base.basic and data.evolvesFrom == base.name
    if not data.stage2 or len(lineage) != 2:
        return False
    base = card_table[lineage[0].id]
    middle = card_table[lineage[1].id]
    return (
        base.basic
        and middle.stage1
        and not middle.stage2
        and middle.evolvesFrom == base.name
        and data.evolvesFrom == middle.name
    )


def _two_prize_alakazam_lineage_is_complete(
    pokemon: Pokemon, owner: int
) -> bool:
    lineage = tuple(card.id for card in pokemon.preEvolution)
    if lineage not in ((Abra,), (Abra, Kadabra)):
        return False
    if any(
        card.serial <= 0 or card.playerIndex != owner
        for card in pokemon.preEvolution
    ):
        return False
    if lineage == (Abra,):
        return card_table[Abra].basic
    return (
        card_table[Abra].basic
        and card_table[Kadabra].stage1
        and card_table[Kadabra].evolvesFrom == card_table[Abra].name
        and card_table[Alakazam].evolvesFrom == card_table[Kadabra].name
    )


def _two_prize_public_pokemon_is_complete(
    pokemon: Pokemon | None, owner: int
) -> bool:
    if (
        not _bridge_pokemon_is_publicly_complete(pokemon, owner)
        or not isinstance(pokemon.appearThisTurn, bool)
    ):
        return False
    data = card_table.get(pokemon.id)
    if (
        data is None
        or data.cardType != CardType.POKEMON
        or pokemon.maxHp != data.hp
        or pokemon.hp <= 0
        or pokemon.hp > pokemon.maxHp
        or not _two_prize_lineage_is_complete(pokemon, owner)
    ):
        return False
    for card in pokemon.energyCards:
        energy = card_table.get(card.id)
        if energy is None or energy.cardType not in (
            CardType.BASIC_ENERGY,
            CardType.SPECIAL_ENERGY,
        ):
            return False
    return all(
        card_table.get(tool.id) is not None
        and card_table[tool.id].cardType == CardType.TOOL
        for tool in pokemon.tools
    )


def _two_prize_powerful_hand_metadata_is_exact() -> bool:
    data = card_table.get(Alakazam)
    attack = attack_table.get(ATTACK_POWERFUL_HAND)
    return (
        data is not None
        and data.cardType == CardType.POKEMON
        and data.hp == 140
        and data.stage2
        and not data.basic
        and not data.stage1
        and data.evolvesFrom == card_table[Kadabra].name
        and tuple(data.attacks or ()) == (ATTACK_POWERFUL_HAND,)
        and tuple(
            (skill.name, skill.text) for skill in (data.skills or [])
        )
        == (
            (
                " Psychic Draw",
                "Once during your turn, when you play this Pok\u00e9mon from "
                "your hand to evolve 1 of your Pok\u00e9mon, you may use this "
                "Ability. Draw 3 cards.",
            ),
        )
        and attack is not None
        and attack.name == "Powerful Hand"
        and attack.text
        == (
            "Place 2 damage counters on your opponent\u2019s Active Pok\u00e9mon "
            "for each card in your hand."
        )
        and attack.damage == 0
        and tuple(int(unit) for unit in attack.energies)
        == (int(EnergyType.PSYCHIC),)
    )


def _two_prize_alakazam_is_ready(
    pokemon: Pokemon | None, owner: int
) -> bool:
    if (
        pokemon is None
        or pokemon.id != Alakazam
        or not _bridge_pokemon_is_publicly_complete(pokemon, owner)
        or not isinstance(pokemon.appearThisTurn, bool)
        or pokemon.maxHp != card_table[Alakazam].hp
        or pokemon.hp <= 0
        or pokemon.hp > pokemon.maxHp
        or pokemon.tools
        or not _two_prize_alakazam_lineage_is_complete(pokemon, owner)
    ):
        return False
    units = _bridge_retaliation_energy_units(pokemon)
    if units is None:
        return False
    payable = _bridge_retaliation_can_pay(
        units, attack_table[ATTACK_POWERFUL_HAND].energies
    )
    return payable is True


def _two_prize_pokemon_skills_are_clear(data) -> bool:
    """Accept only resolved evolution on-play effects on opposing Pokemon."""
    for skill in data.skills or []:
        text = _bridge_retaliation_normalized_text(skill.text)
        if not text.startswith(
            "when you play this pokemon from your hand to evolve"
        ):
            return False
    return True


def _two_prize_opponent_pokemon_is_clear(
    state, pokemon: Pokemon, owner: int
) -> bool:
    if (
        not _two_prize_public_pokemon_is_complete(pokemon, owner)
        or pokemon.tools
        or any(
            card_table[energy.id].cardType != CardType.BASIC_ENERGY
            for energy in pokemon.energyCards
        )
    ):
        return False
    data = card_table[pokemon.id]
    return (
        _two_prize_pokemon_skills_are_clear(data)
        and _powerful_hand_target_is_publicly_clear(state, pokemon)
    )


def _two_prize_stadium_is_clear(state) -> bool:
    if not state.stadium:
        return True
    if len(state.stadium) != 1:
        return False
    stadium = state.stadium[0]
    data = card_table.get(stadium.id)
    return (
        stadium.id == Battle_Cage
        and stadium.serial > 0
        and data is not None
        and data.cardType == CardType.STADIUM
        and tuple(skill.text for skill in (data.skills or []))
        == (
            "Prevent all damage counters from being placed on Benched "
            "Pok\u00e9mon (both yours and your opponent\u2019s) by effects of attacks "
            "and Abilities from the opponent\u2019s Pok\u00e9mon. (Damage from attacks "
            "is still taken.)",
        )
    )


def _two_prize_inherited_owner_active() -> bool:
    return bool(
        _hilda_source_latch
        or _enriching_reserve_latch
        or _fez_ko_bridge_latch
        or _active_psychic_ko_latch
        or _stranded_retreat_ko_latch
        or _guarded_teleportation_latch
        or _turn_objective_recovery_latch
    )


def _two_prize_policy_state_snapshot() -> tuple:
    return (
        _two_prize_freeze_raw(_hilda_source_latch),
        _two_prize_freeze_raw(_enriching_reserve_latch),
        _two_prize_freeze_raw(_fez_ko_bridge_latch),
        _two_prize_freeze_raw(_active_psychic_ko_latch),
        _two_prize_freeze_raw(_stranded_retreat_ko_latch),
        _two_prize_freeze_raw(_guarded_teleportation_latch),
        _two_prize_freeze_raw(_turn_objective_recovery_latch),
        _two_prize_freeze_raw(_terminal_prize_psychic_attach_latch),
        pre_turn,
        ability_used_dudunsparce,
        ability_used_fezandipiti,
    )


_TURN_GUARD_KNOWN_ONE_CARD_PLAYS = {
    Abra,
    Dunsparce,
    Fezandipiti_ex,
    Genesect,
    Psyduck,
    Shaymin,
    Rare_Candy,
    Enhanced_Hammer,
    Buddy_Buddy_Poffin,
    Night_Stretcher,
    Sacred_Ash,
    Poke_Pad,
    Boss_Orders,
    Hilda,
    Dawn,
    Battle_Cage,
}


def _turn_guard_hand_card(mine, index: int, owner: int) -> Card | None:
    if (
        not isinstance(index, int)
        or isinstance(index, bool)
        or mine.hand is None
        or not 0 <= index < len(mine.hand)
    ):
        return None
    card = mine.hand[index]
    if (
        card.id <= 0
        or card.serial <= 0
        or card.playerIndex != owner
        or card_table.get(card.id) is None
    ):
        return None
    return card


def _turn_guard_night_stretcher_replaces_its_hand_card(mine) -> bool:
    data = card_table.get(Night_Stretcher)
    if (
        data is None
        or data.cardType != CardType.ITEM
        or tuple((skill.name, skill.text) for skill in (data.skills or []))
        != (
            (
                "Night Stretcher",
                "Put a Pokémon or a Basic Energy card from your discard "
                "pile into your hand.",
            ),
        )
    ):
        return False
    return any(
        card_table.get(card.id) is not None
        and card_table[card.id].cardType
        in (CardType.POKEMON, CardType.BASIC_ENERGY)
        for card in mine.discard
    )


def _turn_guard_parent_projection(
    obs: Observation,
    option,
    successor_serial: int,
) -> dict | None:
    """Return a guaranteed public floor after one finalized MAIN option.

    The projection intentionally counts only effects forced by the selected
    option.  Optional or hidden-deck search results contribute zero cards.
    """
    state = obs.current
    mine = state.players[state.yourIndex]
    hand_count = mine.handCount

    if option.type == OptionType.PLAY:
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        if (
            card is None
            or not _two_prize_option_is_exact(
                option, OptionType.PLAY, index=option.index
            )
            or card.id not in _TURN_GUARD_KNOWN_ONE_CARD_PLAYS
        ):
            return None
        data = card_table[card.id]
        if data.cardType == CardType.POKEMON and not data.basic:
            return None
        same_serial = [
            index
            for index, candidate in enumerate(obs.select.option)
            if candidate.type == OptionType.PLAY
            and isinstance(candidate.index, int)
            and not isinstance(candidate.index, bool)
            and 0 <= candidate.index < len(mine.hand)
            and mine.hand[candidate.index].serial == card.serial
        ]
        if len(same_serial) != 1:
            return None
        floor = hand_count - 1
        if (
            card.id == Night_Stretcher
            and _turn_guard_night_stretcher_replaces_its_hand_card(mine)
        ):
            floor += 1
        return {
            "post_hand_floor": floor,
            "post_deck_floor": mine.deckCount,
            "destroys_h0": False,
            "consumes_h1": False,
        }

    if option.type == OptionType.ATTACH:
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        target = get_card(
            obs, option.inPlayArea, option.inPlayIndex, state.yourIndex
        )
        if (
            card is None
            or target is None
            or not _two_prize_option_is_exact(
                option,
                OptionType.ATTACH,
                area=AreaType.HAND,
                index=option.index,
                inPlayArea=option.inPlayArea,
                inPlayIndex=option.inPlayIndex,
            )
            or card.id
            not in (
                Basic_Psychic_Energy,
                Telepath_Psychic_Energy,
                Enriching_Energy,
                Lucky_Helmet,
            )
        ):
            return None
        if card.id == Enriching_Energy:
            data = card_table[Enriching_Energy]
            if (
                mine.deckCount < 4
                or tuple(
                    (skill.name, skill.text) for skill in (data.skills or [])
                )
                != (
                    (
                        "Enriching Energy",
                        "As long as this card is attached to a Pokémon, it "
                        "provides {C} Energy.\n\nWhen you attach this card from "
                        "your hand to a Pokémon, draw 4 cards.",
                    ),
                )
            ):
                return None
            return {
                "post_hand_floor": hand_count + 3,
                "post_deck_floor": mine.deckCount - 4,
                "destroys_h0": False,
                "consumes_h1": False,
            }
        return {
            "post_hand_floor": hand_count - 1,
            "post_deck_floor": mine.deckCount,
            "destroys_h0": False,
            "consumes_h1": False,
        }

    if option.type == OptionType.EVOLVE:
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        target = get_card(
            obs, option.inPlayArea, option.inPlayIndex, state.yourIndex
        )
        if (
            card is None
            or target is None
            or not _two_prize_option_is_exact(
                option,
                OptionType.EVOLVE,
                area=AreaType.HAND,
                index=option.index,
                inPlayArea=option.inPlayArea,
                inPlayIndex=option.inPlayIndex,
            )
            or card_table[card.id].cardType != CardType.POKEMON
            or not (card_table[card.id].stage1 or card_table[card.id].stage2)
        ):
            return None
        return {
            "post_hand_floor": hand_count - 1,
            "post_deck_floor": mine.deckCount,
            "destroys_h0": False,
            "consumes_h1": target.serial == successor_serial,
        }

    if option.type == OptionType.ABILITY:
        pokemon = get_card(obs, option.area, option.index, state.yourIndex)
        if (
            pokemon is None
            or not _two_prize_option_is_exact(
                option,
                OptionType.ABILITY,
                area=option.area,
                index=option.index,
            )
        ):
            return None
        if pokemon.id in (Dudunsparce, Fezandipiti_ex, Alakazam):
            draw_count = 3
            if mine.deckCount < draw_count:
                return None
            return {
                "post_hand_floor": hand_count + draw_count,
                "post_deck_floor": mine.deckCount - draw_count,
                "destroys_h0": False,
                "consumes_h1": False,
            }
        if pokemon.id == Battle_Cage:
            return {
                "post_hand_floor": hand_count,
                "post_deck_floor": mine.deckCount,
                "destroys_h0": False,
                "consumes_h1": False,
            }
        return None

    if option.type == OptionType.RETREAT and _two_prize_option_is_exact(
        option, OptionType.RETREAT
    ):
        return {
            "post_hand_floor": hand_count,
            "post_deck_floor": mine.deckCount,
            "destroys_h0": True,
            "consumes_h1": False,
        }
    if option.type == OptionType.END and _two_prize_option_is_exact(
        option, OptionType.END
    ):
        return {
            "post_hand_floor": hand_count,
            "post_deck_floor": mine.deckCount,
            "destroys_h0": True,
            "consumes_h1": False,
        }
    return None


def _turn_guard_has_superior_boss_route(
    obs: Observation, active_prizes: int, hand_count: int
) -> bool | None:
    state = obs.current
    mine = state.players[state.yourIndex]
    theirs = state.players[1 - state.yourIndex]
    boss_options = []
    for option in obs.select.option:
        if option.type != OptionType.PLAY:
            continue
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        if card is None:
            return None
        if card.id != Boss_Orders:
            continue
        if not _two_prize_option_is_exact(
            option, OptionType.PLAY, index=option.index
        ):
            return None
        boss_options.append(option)
    if not boss_options:
        return False
    boss_damage = 20 * (hand_count - 1)
    active_wins = active_prizes >= len(mine.prize)
    for pokemon in theirs.bench:
        if not _two_prize_opponent_pokemon_is_clear(
            state, pokemon, 1 - state.yourIndex
        ):
            return None
        prizes = prize_count(pokemon)
        if boss_damage < pokemon.hp:
            continue
        boss_wins = prizes >= len(mine.prize)
        if (boss_wins and not active_wins) or (
            not active_wins and prizes > active_prizes
        ):
            return True
    return False


def _turn_guard_h0_h1_action(obs: Observation, chosen_action: list[int]) -> list[int] | None:
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    attack_options = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK
    ]
    if (
        not _two_prize_powerful_hand_metadata_is_exact()
        or not _two_prize_stadium_is_clear(state)
        or len(attack_options) != 1
        or not _two_prize_option_is_exact(
            select.option[attack_options[0]],
            OptionType.ATTACK,
            attackId=ATTACK_POWERFUL_HAND,
        )
        or len(mine.active) != 1
        or not _two_prize_alakazam_is_ready(mine.active[0], my_index)
        or len(theirs.active) != 1
        or any(
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
            )
        )
    ):
        return None
    active = mine.active[0]
    target = theirs.active[0]
    if not _two_prize_opponent_pokemon_is_clear(
        state, target, 1 - my_index
    ):
        return None
    hand_count = mine.handCount
    required_hand = (target.hp + 19) // 20
    target_prizes = prize_count(target)
    if target_prizes <= 0 or hand_count < required_hand:
        return None
    active_wins = target_prizes >= len(mine.prize)
    successors = [
        pokemon
        for pokemon in mine.bench
        if pokemon.serial != active.serial
        and _two_prize_alakazam_is_ready(pokemon, my_index)
    ]
    if not active_wins and len(successors) != 1:
        return None
    parent_option = select.option[chosen_action[0]]
    if (
        parent_option.type == OptionType.ATTACK
        and parent_option.attackId == ATTACK_POWERFUL_HAND
    ):
        return None
    projection = _turn_guard_parent_projection(
        obs,
        parent_option,
        successors[0].serial if len(successors) == 1 else -1,
    )
    if projection is None:
        return None
    destroys_objective = (
        projection["destroys_h0"]
        or projection["consumes_h1"]
        or projection["post_hand_floor"] < required_hand
        or (
            not active_wins
            and projection["post_deck_floor"] <= 0
        )
    )
    if not destroys_objective:
        return None
    superior_boss = _turn_guard_has_superior_boss_route(
        obs, target_prizes, hand_count
    )
    if superior_boss is None or superior_boss:
        return None
    return [attack_options[0]]


def _turn_guard_same_turn_recycle_is_certified(obs: Observation) -> bool:
    state = obs.current
    mine = state.players[state.yourIndex]
    needed = max(0, 3 - mine.deckCount)
    for option in obs.select.option:
        if option.type == OptionType.ABILITY:
            pokemon = get_card(obs, option.area, option.index, state.yourIndex)
            if pokemon is not None and pokemon.id == Dudunsparce:
                return True
        if option.type != OptionType.PLAY:
            continue
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        if card is None or card.id != Sacred_Ash:
            continue
        public_pokemon = sum(
            1
            for discarded in mine.discard
            if card_table.get(discarded.id) is not None
            and card_table[discarded.id].cardType == CardType.POKEMON
        )
        if public_pokemon >= needed:
            return True
    return False


def _turn_guard_thin_deck_helmet_action(
    obs: Observation, chosen_action: list[int]
) -> list[int] | None:
    state = obs.current
    select = obs.select
    mine = state.players[state.yourIndex]
    parent_option = select.option[chosen_action[0]]
    if parent_option.type != OptionType.ATTACH or mine.deckCount > 2:
        return None
    card = _turn_guard_hand_card(
        mine, parent_option.index, state.yourIndex
    )
    target = get_card(
        obs,
        parent_option.inPlayArea,
        parent_option.inPlayIndex,
        state.yourIndex,
    )
    helmet = card_table.get(Lucky_Helmet)
    if (
        card is None
        or card.id != Lucky_Helmet
        or target is None
        or parent_option.inPlayArea != AreaType.ACTIVE
        or len(mine.active) != 1
        or target.serial != mine.active[0].serial
        or not _two_prize_option_is_exact(
            parent_option,
            OptionType.ATTACH,
            area=AreaType.HAND,
            index=parent_option.index,
            inPlayArea=AreaType.ACTIVE,
            inPlayIndex=parent_option.inPlayIndex,
        )
        or helmet is None
        or tuple((skill.name, skill.text) for skill in (helmet.skills or []))
        != (
            (
                "Lucky Helmet",
                "If the Pokémon this card is attached to is in the Active "
                "Spot and is damaged by an attack from your opponent’s "
                "Pokémon (even if this Pokémon is Knocked Out), draw 2 "
                "cards.",
            ),
        )
        or _turn_guard_same_turn_recycle_is_certified(obs)
    ):
        return None
    attacks = []
    ends = []
    for index, option in enumerate(select.option):
        if option.type == OptionType.ATTACK:
            if (
                not isinstance(option.attackId, int)
                or isinstance(option.attackId, bool)
                or attack_table.get(option.attackId) is None
                or not _two_prize_option_is_exact(
                    option, OptionType.ATTACK, attackId=option.attackId
                )
            ):
                return None
            attacks.append(index)
        elif option.type == OptionType.END:
            if not _two_prize_option_is_exact(option, OptionType.END):
                return None
            ends.append(index)
    if len(attacks) == 1:
        return [attacks[0]]
    if not attacks and len(ends) == 1:
        return [ends[0]]
    return None


def _turn_guard_zero_deck_sacred_ash_action(
    obs: Observation, chosen_action: list[int]
) -> list[int] | None:
    """Recover a public Pokemon before a nonterminal attack at deck zero."""
    state = obs.current
    select = obs.select
    mine = state.players[state.yourIndex]
    theirs = state.players[1 - state.yourIndex]
    parent_option = select.option[chosen_action[0]]
    if (
        mine.deckCount != 0
        or parent_option.type != OptionType.ATTACK
        or len(theirs.active) != 1
    ):
        return None
    attack = attack_table.get(parent_option.attackId)
    target = theirs.active[0]
    if (
        attack is None
        or parent_option.attackId
        not in (ATTACK_SUPER_PSY_BOLT, ATTACK_POWERFUL_HAND)
        or not _two_prize_option_is_exact(
            parent_option,
            OptionType.ATTACK,
            attackId=parent_option.attackId,
        )
    ):
        return None
    if parent_option.attackId == ATTACK_SUPER_PSY_BOLT:
        takes_prizes = attack.damage >= target.hp
    else:
        takes_prizes = 20 * mine.handCount >= target.hp
    if takes_prizes and prize_count(target) >= len(mine.prize):
        return None
    ash_options = []
    for index, option in enumerate(select.option):
        if option.type != OptionType.PLAY:
            continue
        card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
        if card is None:
            return None
        if card.id != Sacred_Ash:
            continue
        if not _two_prize_option_is_exact(
            option, OptionType.PLAY, index=option.index
        ):
            return None
        ash_options.append(index)
    recoverable = [
        card
        for card in mine.discard
        if card_table.get(card.id) is not None
        and card_table[card.id].cardType == CardType.POKEMON
        and card.id > 0
        and card.serial > 0
        and card.playerIndex == state.yourIndex
    ]
    ash = card_table.get(Sacred_Ash)
    if (
        len(ash_options) != 1
        or not recoverable
        or ash is None
        or ash.cardType != CardType.ITEM
        or tuple((skill.name, skill.text) for skill in (ash.skills or []))
        != (
            (
                "Sacred Ash",
                "Shuffle up to 5 Pokémon from your discard pile into your "
                "deck.",
            ),
        )
    ):
        return None
    return [ash_options[0]]


def _turn_guard_recovery_snapshot_hash(payload) -> str:
    frozen = _two_prize_freeze_raw(payload)
    return hashlib.sha256(repr(frozen).encode("utf-8")).hexdigest()


def _start_turn_guard_recovery_latch(
    obs: Observation, action: list[int]
) -> bool:
    state = obs.current
    select = obs.select
    mine = state.players[state.yourIndex]
    theirs = state.players[1 - state.yourIndex]
    if len(action) != 1 or not 0 <= action[0] < len(select.option):
        return False
    option = select.option[action[0]]
    card = _turn_guard_hand_card(mine, option.index, state.yourIndex)
    recoverable = tuple(
        sorted(
            discarded.serial
            for discarded in mine.discard
            if card_table.get(discarded.id) is not None
            and card_table[discarded.id].cardType == CardType.POKEMON
            and discarded.id > 0
            and discarded.serial > 0
            and discarded.playerIndex == state.yourIndex
        )
    )
    if (
        _turn_objective_recovery_latch
        or card is None
        or card.id != Sacred_Ash
        or not recoverable
        or mine.deckCount != 0
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or not _two_prize_option_is_exact(
            option, OptionType.PLAY, index=option.index
        )
    ):
        return False
    snapshot = {
        "turn": state.turn,
        "player": state.yourIndex,
        "turn_action_count": state.turnActionCount,
        "hand_serials": tuple(card.serial for card in mine.hand),
        "discard_serials": tuple(card.serial for card in mine.discard),
        "active": _bridge_pokemon_fingerprint(mine.active[0]),
        "bench": tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        ),
        "target": _bridge_pokemon_fingerprint(theirs.active[0]),
        "own_prizes": len(mine.prize),
        "opponent_prizes": len(theirs.prize),
        "ash_serial": card.serial,
        "recoverable_serials": recoverable,
    }
    _turn_objective_recovery_latch.update(
        plan_id="public_h0_h1_zero_deck_sacred_ash_v1",
        snapshot_hash=_turn_guard_recovery_snapshot_hash(snapshot),
        stage="await_discard_selection",
        turn=state.turn,
        player=state.yourIndex,
        start_action_count=state.turnActionCount,
        start_hand_serials=snapshot["hand_serials"],
        start_discard_serials=snapshot["discard_serials"],
        active_fingerprint=snapshot["active"],
        bench_fingerprints=snapshot["bench"],
        target_fingerprint=snapshot["target"],
        own_prizes=snapshot["own_prizes"],
        opponent_prizes=snapshot["opponent_prizes"],
        ash_serial=card.serial,
        reserved_cards_and_slots=(card.serial, recoverable, None),
        recoverable_serials=recoverable,
        expected_callback=(9, Sacred_Ash, card.serial),
        abort_conditions=(
            "turn_or_player_changed",
            "board_or_prizes_changed",
            "non_sacred_ash_selection",
            "reserved_discard_changed",
            "resolution_did_not_restore_deck",
        ),
        selected_serials=(),
    )
    return True


def _turn_guard_recovery_board_is_same(obs: Observation, latch: dict) -> bool:
    state = obs.current
    mine = state.players[state.yourIndex]
    theirs = state.players[1 - state.yourIndex]
    return (
        state.turn == latch.get("turn")
        and state.yourIndex == latch.get("player")
        and len(mine.active) == 1
        and len(theirs.active) == 1
        and _bridge_pokemon_fingerprint(mine.active[0])
        == latch.get("active_fingerprint")
        and tuple(
            _bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench
        )
        == latch.get("bench_fingerprints")
        and _bridge_pokemon_fingerprint(theirs.active[0])
        == latch.get("target_fingerprint")
        and len(mine.prize) == latch.get("own_prizes")
        and len(theirs.prize) == latch.get("opponent_prizes")
    )


def _turn_guard_recovery_overlay(obs: Observation) -> list[int] | None:
    latch = _turn_objective_recovery_latch
    if not latch:
        return None
    state = obs.current
    select = obs.select
    mine = state.players[state.yourIndex]
    if not _turn_guard_recovery_board_is_same(obs, latch):
        _clear_turn_objective_recovery_latch()
        return None

    if latch.get("stage") == "await_discard_selection":
        expected_hand = tuple(
            serial
            for serial in latch.get("start_hand_serials", ())
            if serial != latch.get("ash_serial")
        )
        # The checked engine holds the Item as ``select.effect`` while its
        # discard targets are chosen; it is not placed in discard until the
        # effect resolves.
        expected_discard = tuple(latch.get("start_discard_serials", ()))
        if (
            state.turnActionCount != latch.get("start_action_count") + 1
            or mine.deckCount != 0
            or tuple(card.serial for card in mine.hand) != expected_hand
            or tuple(card.serial for card in mine.discard) != expected_discard
            or int(select.context) != 9
            or select.contextCard is not None
            or select.deck is not None
            or select.effect is None
            or select.effect.id != Sacred_Ash
            or select.effect.serial != latch.get("ash_serial")
            or select.minCount < 1
            or select.maxCount < select.minCount
            or select.maxCount > 5
        ):
            _clear_turn_objective_recovery_latch()
            return None
        resolved = []
        for option_index, option in enumerate(select.option):
            if (
                option.type != OptionType.CARD
                or option.area != AreaType.DISCARD
                or option.playerIndex != state.yourIndex
            ):
                _clear_turn_objective_recovery_latch()
                return None
            card = get_card(
                obs, AreaType.DISCARD, option.index, state.yourIndex
            )
            if (
                card is None
                or card.serial not in latch.get("recoverable_serials", ())
                or card_table.get(card.id) is None
                or card_table[card.id].cardType != CardType.POKEMON
            ):
                _clear_turn_objective_recovery_latch()
                return None
            resolved.append((option_index, card.serial))
        if not resolved or len({serial for _, serial in resolved}) != len(resolved):
            _clear_turn_objective_recovery_latch()
            return None
        chosen = resolved[: select.maxCount]
        if len(chosen) < select.minCount:
            _clear_turn_objective_recovery_latch()
            return None
        latch["stage"] = "await_resolution"
        latch["selected_serials"] = tuple(serial for _, serial in chosen)
        return [option_index for option_index, _ in chosen]

    if latch.get("stage") == "await_resolution":
        selected = tuple(latch.get("selected_serials", ()))
        valid = (
            select.context == SelectContext.MAIN
            and state.turnActionCount == latch.get("start_action_count") + 2
            and selected
            and mine.deckCount == len(selected)
            and all(
                serial not in {card.serial for card in mine.discard}
                for serial in selected
            )
            and latch.get("ash_serial")
            in {card.serial for card in mine.discard}
        )
        _clear_turn_objective_recovery_latch()
        if not valid:
            return None
        return None

    _clear_turn_objective_recovery_latch()
    return None


def _public_h0_h1_turn_objective_guard_unsafe(
    obs_dict: dict,
    obs: Observation,
    chosen_action: list[int],
    inherited_owner_at_entry: bool,
) -> list[int] | None:
    state = obs.current
    select = obs.select
    if (
        inherited_owner_at_entry
        or _two_prize_inherited_owner_active()
        or state is None
        or select is None
        or not _two_prize_raw_parsed_agree(obs_dict, obs)
        or state.result != -1
        or not isinstance(state.turn, int)
        or isinstance(state.turn, bool)
        or state.turn < 2
        or state.looking is not None
        or int(select.type) != 0
        or select.context != SelectContext.MAIN
        or select.minCount != 1
        or select.maxCount != 1
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or len(chosen_action) != 1
    ):
        return None

    end_options = [
        index
        for index, option in enumerate(select.option)
        if option.type == OptionType.END
    ]
    if (
        len(end_options) != 1
        or not _two_prize_option_is_exact(
            select.option[end_options[0]], OptionType.END
        )
    ):
        return None

    my_index = state.yourIndex
    if my_index not in (0, 1) or len(state.players) != 2:
        return None
    mine = state.players[my_index]
    theirs = state.players[1 - my_index]
    if (
        mine.hand is None
        or len(mine.hand) != mine.handCount
        or mine.handCount <= 0
        or any(
            card.id <= 0
            or card.serial <= 0
            or card.playerIndex != my_index
            or card_table.get(card.id) is None
            for card in mine.hand
        )
    ):
        return None
    public_serials = _bridge_public_serials(state)
    if (
        not public_serials
        or any(serial <= 0 for serial in public_serials)
        or len(public_serials) != len(set(public_serials))
    ):
        return None

    if not 0 <= chosen_action[0] < len(select.option):
        return None
    deck_recovery_action = _turn_guard_zero_deck_sacred_ash_action(
        obs, chosen_action
    )
    if deck_recovery_action is not None:
        return deck_recovery_action
    h0_h1_action = _turn_guard_h0_h1_action(obs, chosen_action)
    if h0_h1_action is not None:
        return h0_h1_action
    return _turn_guard_thin_deck_helmet_action(obs, chosen_action)


def _public_h0_h1_turn_objective_guard(
    obs_dict: dict,
    obs: Observation,
    chosen_action: list[int],
    inherited_owner_at_entry: bool,
) -> list[int] | None:
    """Atomic fail-closed lexicographic H0/H1/deck-clock guard."""
    before = _two_prize_policy_state_snapshot()
    try:
        action = _public_h0_h1_turn_objective_guard_unsafe(
            obs_dict, obs, chosen_action, inherited_owner_at_entry
        )
    except Exception:
        return None
    if before != _two_prize_policy_state_snapshot():
        return None
    return action


def _terminal_basic_psychic_metadata_is_exact() -> bool:
    data = card_table.get(Basic_Psychic_Energy)
    return (
        data is not None
        and data.cardId == Basic_Psychic_Energy
        and data.name == "Basic {P} Energy"
        and data.cardType == CardType.BASIC_ENERGY
        and data.retreatCost == 0
        and data.hp == 0
        and data.weakness is None
        and data.resistance is None
        and data.energyType == EnergyType.PSYCHIC
        and not data.basic
        and not data.stage1
        and not data.stage2
        and not data.ex
        and not data.megaEx
        and not data.tera
        and not data.aceSpec
        and data.evolvesFrom is None
        and tuple(data.skills or ()) == ()
        and tuple(data.attacks or ()) == ()
    )


def _terminal_enriching_metadata_is_exact() -> bool:
    data = card_table.get(Enriching_Energy)
    return (
        data is not None
        and data.cardId == Enriching_Energy
        and data.name == "Enriching Energy"
        and data.cardType == CardType.SPECIAL_ENERGY
        and data.retreatCost == 0
        and data.hp == 0
        and data.weakness is None
        and data.resistance is None
        and data.energyType == EnergyType.COLORLESS
        and not data.basic
        and not data.stage1
        and not data.stage2
        and not data.ex
        and not data.megaEx
        and not data.tera
        and data.aceSpec
        and data.evolvesFrom is None
        and tuple(data.attacks or ()) == ()
        and tuple(
            (skill.name, skill.text) for skill in (data.skills or [])
        )
        == (
            (
                "Enriching Energy",
                "As long as this card is attached to a Pok\u00e9mon, it provides "
                "{C} Energy.\n\nWhen you attach this card from your hand to a "
                "Pok\u00e9mon, draw 4 cards.",
            ),
        )
    )


def _terminal_full_metal_lab_metadata_is_exact() -> bool:
    data = card_table.get(Full_Metal_Lab)
    return (
        data is not None
        and data.cardId == Full_Metal_Lab
        and data.name == "Full Metal Lab"
        and data.cardType == CardType.STADIUM
        and data.retreatCost == 0
        and data.hp == 0
        and data.weakness is None
        and data.resistance is None
        and data.energyType == EnergyType.COLORLESS
        and not data.basic
        and not data.stage1
        and not data.stage2
        and not data.ex
        and not data.megaEx
        and not data.tera
        and not data.aceSpec
        and data.evolvesFrom is None
        and tuple(data.attacks or ()) == ()
        and tuple(
            (skill.name, skill.text) for skill in (data.skills or [])
        )
        == (
            (
                "Full Metal Lab",
                "{M} Pok\u00e9mon (both yours and your opponent\u2019s) take 30 "
                "less damage from attacks from the opponent\u2019s Pok\u00e9mon "
                "(after applying Weakness and Resistance).",
            ),
        )
    )


def _terminal_main_select_is_ordinary(select) -> bool:
    return (
        int(select.type) == 0
        and select.context == SelectContext.MAIN
        and select.minCount == 1
        and select.maxCount == 1
        and select.remainDamageCounter == 0
        and select.remainEnergyCost == 0
        and select.deck is None
        and select.contextCard is None
        and select.effect is None
    )


def _terminal_active_status_is_clear(player_state) -> bool:
    return not any(
        (
            player_state.poisoned,
            player_state.burned,
            player_state.asleep,
            player_state.paralyzed,
            player_state.confused,
        )
    )


def _terminal_public_cards_are_owned_and_unique(state) -> bool:
    for owner, player in enumerate(state.players):
        groups = [player.discard]
        if player.hand is not None:
            groups.append(player.hand)
        groups.append(tuple(card for card in player.prize if card is not None))
        for group in groups:
            for card in group:
                if (
                    card is None
                    or card.id <= 0
                    or card.serial <= 0
                    or card.playerIndex != owner
                    or card_table.get(card.id) is None
                ):
                    return False
    for stadium in state.stadium:
        if (
            stadium.id <= 0
            or stadium.serial <= 0
            or stadium.playerIndex not in (0, 1)
            or card_table.get(stadium.id) is None
        ):
            return False
    serials = _bridge_public_serials(state)
    return (
        bool(serials)
        and all(isinstance(serial, int) and serial > 0 for serial in serials)
        and len(serials) == len(set(serials))
    )


def _terminal_unpaid_alakazam_is_complete(
    pokemon: Pokemon | None, owner: int
) -> bool:
    return (
        pokemon is not None
        and pokemon.id == Alakazam
        and _bridge_pokemon_is_publicly_complete(pokemon, owner)
        and isinstance(pokemon.appearThisTurn, bool)
        and pokemon.maxHp == card_table[Alakazam].hp
        and pokemon.hp == pokemon.maxHp == 140
        and not pokemon.tools
        and not pokemon.energyCards
        and not pokemon.energies
        and _two_prize_alakazam_lineage_is_complete(pokemon, owner)
    )


def _terminal_two_prize_target_is_clear(
    state, pokemon: Pokemon | None, owner: int
) -> bool:
    if (
        pokemon is None
        or not _two_prize_public_pokemon_is_complete(pokemon, owner)
        or pokemon.tools
    ):
        return False
    data = card_table.get(pokemon.id)
    if (
        data is None
        or not data.ex
        or data.megaEx
        or data.tera
        or data.resistance == EnergyType.PSYCHIC
        or prize_count(pokemon) != 2
        or not _two_prize_pokemon_skills_are_clear(data)
        or any(
            _skill_may_change_powerful_hand_damage(skill.text)
            for skill in (data.skills or [])
        )
    ):
        return False
    for unit, energy in zip(pokemon.energies, pokemon.energyCards):
        energy_data = card_table.get(energy.id)
        if (
            energy_data is None
            or energy_data.cardType != CardType.BASIC_ENERGY
            or int(unit) != int(energy_data.energyType)
        ):
            return False
    return True


def _terminal_full_metal_lab_reduction(
    state, target: Pokemon
) -> int | None:
    if not state.stadium:
        return 0
    if len(state.stadium) != 1 or not _terminal_full_metal_lab_metadata_is_exact():
        return None
    stadium = state.stadium[0]
    target_data = card_table.get(target.id)
    if (
        stadium.id != Full_Metal_Lab
        or stadium.serial <= 0
        or stadium.playerIndex not in (0, 1)
        or target_data is None
    ):
        return None
    return 30 if target_data.energyType == EnergyType.METAL else 0


def _terminal_card_group_fingerprint(cards) -> tuple:
    return tuple(_bridge_card_fingerprint(card) for card in cards)


def _terminal_bench_fingerprint(player_state) -> tuple:
    return tuple(
        _bridge_pokemon_fingerprint(pokemon)
        for pokemon in player_state.bench
    )


_TERMINAL_HARMLESS_OPPONENT_BENCH_SKILLS = {
    57: (
        "Relicanth",
        (
            (
                "Memory Dive",
                "Each of your evolved Pokémon can use any attack from its "
                "previous Evolutions. (You still need the necessary Energy to "
                "use each attack.)",
            ),
        ),
    ),
    666: (
        "Cinderace",
        (
            (
                " Explosiveness",
                "If this Pokémon is in your hand when you are setting up to "
                "play, you may put it face down in the Active Spot.",
            ),
        ),
    ),
}


def _terminal_opponent_bench_skills_are_harmless(
    player_state, owner: int
) -> bool:
    """Accept only skill-free Bench Pokémon or two exact harmless witnesses."""
    for pokemon in player_state.bench:
        data = card_table.get(pokemon.id)
        if (
            not _bridge_pokemon_is_publicly_complete(pokemon, owner)
            or data is None
            or data.cardId != pokemon.id
            or data.cardType != CardType.POKEMON
            or data.hp != pokemon.maxHp
        ):
            return False
        skills = _bridge_metadata_skill_fingerprint(data)
        expected = _TERMINAL_HARMLESS_OPPONENT_BENCH_SKILLS.get(pokemon.id)
        if expected is not None:
            if expected != (data.name, skills):
                return False
        elif skills:
            return False
    return True


_TERMINAL_TRANSIENT_DAMAGE_REDUCER_IDS = frozenset((1140, 1228))


def _terminal_attack_leaves_next_turn_damage_reduction(text: str) -> bool:
    normalized = _bridge_retaliation_normalized_text(text)
    if "during your opponent" not in normalized or "next turn" not in normalized:
        return False
    return any(
        (
            "less damage from attacks" in normalized,
            "prevent all damage" in normalized,
            "prevent damage" in normalized,
            "takes no damage" in normalized,
            "damage is reduced" in normalized,
            (
                "attacks used by the defending pokemon do" in normalized
                and "less damage" in normalized
            ),
        )
    )


def _terminal_visible_pokemon_attacks_are_clear(card_id: int) -> bool:
    data = card_table.get(card_id)
    if (
        data is None
        or data.cardId != card_id
        or data.cardType != CardType.POKEMON
        or not isinstance(data.attacks, list)
        or len(data.attacks) != len(set(data.attacks))
    ):
        return False
    for attack_id in data.attacks:
        attack = attack_table.get(attack_id)
        if (
            not isinstance(attack_id, int)
            or isinstance(attack_id, bool)
            or attack_id <= 0
            or attack is None
            or attack.attackId != attack_id
            or not isinstance(attack.name, str)
            or not attack.name
            or not isinstance(attack.text, str)
            or not isinstance(attack.energies, list)
            or _terminal_attack_leaves_next_turn_damage_reduction(
                attack.text
            )
        ):
            return False
    return True


def _terminal_opponent_public_transient_damage_is_clear(
    player_state, owner: int
) -> bool:
    """Reject public sources that can leave a next-turn damage modifier."""
    visible_pokemon_ids = []
    for pokemon in list(player_state.active) + list(player_state.bench):
        if (
            pokemon is None
            or not _bridge_pokemon_is_publicly_complete(pokemon, owner)
        ):
            return False
        visible_pokemon_ids.append(pokemon.id)
        visible_pokemon_ids.extend(card.id for card in pokemon.preEvolution)

    zones = (player_state.discard, getattr(player_state, "lost", ()))
    for cards in zones:
        if not isinstance(cards, (list, tuple)):
            return False
        for card in cards:
            data = card_table.get(card.id) if card is not None else None
            if (
                card is None
                or card.id <= 0
                or card.serial <= 0
                or card.playerIndex != owner
                or data is None
                or data.cardId != card.id
                or card.id in _TERMINAL_TRANSIENT_DAMAGE_REDUCER_IDS
            ):
                return False
            if data.cardType == CardType.POKEMON:
                visible_pokemon_ids.append(card.id)

    return all(
        _terminal_visible_pokemon_attacks_are_clear(card_id)
        for card_id in visible_pokemon_ids
    )


def _terminal_unique_basic_psychic_active_attach(
    obs: Observation, owner: int
) -> tuple[int, Card] | None:
    mine = obs.current.players[owner]
    matches = []
    for option_index, option in enumerate(obs.select.option):
        if (
            not isinstance(option.index, int)
            or option.index < 0
            or option.index >= len(mine.hand or [])
            or not _two_prize_option_is_exact(
                option,
                OptionType.ATTACH,
                area=AreaType.HAND,
                index=option.index,
                inPlayArea=AreaType.ACTIVE,
                inPlayIndex=0,
            )
        ):
            continue
        energy = mine.hand[option.index]
        if energy.id == Basic_Psychic_Energy:
            matches.append((option_index, energy))
    if len(matches) != 1:
        return None
    return matches[0]


def _terminal_parent_enriching_to_nonactive(
    obs: Observation, parent_action: list[int]
) -> tuple[Card, Pokemon] | None:
    if len(parent_action) != 1:
        return None
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    option_index = parent_action[0]
    if (
        not isinstance(option_index, int)
        or isinstance(option_index, bool)
        or option_index < 0
        or option_index >= len(obs.select.option)
    ):
        return None
    option = obs.select.option[option_index]
    if (
        not isinstance(option.index, int)
        or option.index < 0
        or option.index >= len(mine.hand or [])
        or not isinstance(option.inPlayIndex, int)
        or option.inPlayIndex < 0
        or option.inPlayIndex >= len(mine.bench)
        or not _two_prize_option_is_exact(
            option,
            OptionType.ATTACH,
            area=AreaType.HAND,
            index=option.index,
            inPlayArea=AreaType.BENCH,
            inPlayIndex=option.inPlayIndex,
        )
    ):
        return None
    source = mine.hand[option.index]
    target = mine.bench[option.inPlayIndex]
    if (
        source.id != Enriching_Energy
        or source.serial <= 0
        or source.playerIndex != owner
        or target.serial <= 0
        or target.serial == mine.active[0].serial
        or not _bridge_pokemon_is_publicly_complete(target, owner)
        or not _terminal_enriching_metadata_is_exact()
    ):
        return None
    semantic_matches = []
    for candidate_index, candidate_option in enumerate(obs.select.option):
        if (
            candidate_option.type != OptionType.ATTACH
            or candidate_option.area != AreaType.HAND
            or candidate_option.inPlayArea != AreaType.BENCH
            or candidate_option.inPlayIndex != option.inPlayIndex
            or not isinstance(candidate_option.index, int)
            or candidate_option.index < 0
            or candidate_option.index >= len(mine.hand or [])
        ):
            continue
        candidate_source = mine.hand[candidate_option.index]
        if candidate_source.serial == source.serial:
            semantic_matches.append(candidate_index)
    if semantic_matches != [option_index]:
        return None
    return source, target


def _terminal_parent_policy_snapshot() -> tuple:
    return (
        _two_prize_freeze_raw(_hilda_source_latch),
        _two_prize_freeze_raw(_enriching_reserve_latch),
        _two_prize_freeze_raw(_fez_ko_bridge_latch),
        _two_prize_freeze_raw(_active_psychic_ko_latch),
        _two_prize_freeze_raw(_stranded_retreat_ko_latch),
        _two_prize_freeze_raw(_guarded_teleportation_latch),
        _two_prize_freeze_raw(_turn_objective_recovery_latch),
        _two_prize_freeze_raw(_guarded_teleportation_semantic_failure),
        pre_turn,
        ability_used_dudunsparce,
        ability_used_fezandipiti,
        _last_decision_signature,
        _last_decision_action,
    )


def _start_terminal_prize_psychic_attach_unsafe(
    obs_dict: dict,
    obs: Observation,
    parent_action: list[int],
    inherited_owner_at_entry: bool,
) -> list[int] | None:
    """Start the exact final-two-prize Basic Psychic -> Powerful Hand route."""
    state = obs.current
    select = obs.select
    if (
        inherited_owner_at_entry
        or _two_prize_inherited_owner_active()
        or _terminal_prize_psychic_attach_latch
        or state.result != -1
        or state.turn < 2
        or state.yourIndex not in (0, 1)
        or len(state.players) != 2
        or state.looking is not None
        or state.energyAttached
        or not _terminal_main_select_is_ordinary(select)
        or not _two_prize_raw_parsed_agree(obs_dict, obs)
        or not _terminal_basic_psychic_metadata_is_exact()
        or not _terminal_enriching_metadata_is_exact()
        or not _two_prize_powerful_hand_metadata_is_exact()
        or not _terminal_public_cards_are_owned_and_unique(state)
        or any(option.type == OptionType.ATTACK for option in select.option)
        or len(
            [
                option
                for option in select.option
                if _two_prize_option_is_exact(option, OptionType.END)
            ]
        )
        != 1
    ):
        return None

    owner = state.yourIndex
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    if (
        len(mine.active) != 1
        or len(theirs.active) != 1
        or not _terminal_active_status_is_clear(mine)
        or not _terminal_active_status_is_clear(theirs)
        or not _terminal_opponent_bench_skills_are_harmless(
            theirs, 1 - owner
        )
        or not _terminal_opponent_public_transient_damage_is_clear(
            theirs, 1 - owner
        )
    ):
        return None
    active = mine.active[0]
    target = theirs.active[0]
    if (
        not _terminal_unpaid_alakazam_is_complete(active, owner)
        or not _terminal_two_prize_target_is_clear(state, target, 1 - owner)
        or len(mine.prize) != 2
        or prize_count(target) != 2
        or len(mine.prize) > prize_count(target)
    ):
        return None

    hand_fingerprint = _active_psychic_hand_fingerprint(mine, owner)
    attach = _terminal_unique_basic_psychic_active_attach(obs, owner)
    parent_enriching = _terminal_parent_enriching_to_nonactive(
        obs, parent_action
    )
    reduction = _terminal_full_metal_lab_reduction(state, target)
    if (
        hand_fingerprint is None
        or attach is None
        or parent_enriching is None
        or reduction is None
        or sum(
            card.id == Basic_Psychic_Energy for card in (mine.hand or [])
        )
        != 1
        or _bridge_retaliation_can_pay(
            (int(EnergyType.PSYCHIC),),
            attack_table[ATTACK_POWERFUL_HAND].energies,
        )
        is not True
    ):
        return None
    option_index, energy = attach
    parent_energy, parent_target = parent_enriching
    selected_hand_index = select.option[option_index].index
    if (
        energy.id != Basic_Psychic_Energy
        or energy.serial <= 0
        or energy.playerIndex != owner
        or hand_fingerprint[selected_hand_index]
        != _bridge_card_fingerprint(energy)
    ):
        return None

    post_attach_hand_count = mine.handCount - 1
    damage_floor = 20 * post_attach_hand_count - reduction
    if post_attach_hand_count < 0 or damage_floor < target.hp:
        return None
    protected_serials = [
        *_bridge_pokemon_component_serials(active),
        *_bridge_pokemon_component_serials(target),
        energy.serial,
        *(stadium.serial for stadium in state.stadium),
    ]
    if not _bridge_protected_serials_are_unique(state, protected_serials):
        return None

    post_attach_hand = (
        hand_fingerprint[:selected_hand_index]
        + hand_fingerprint[selected_hand_index + 1 :]
    )
    _terminal_prize_psychic_attach_latch.update(
        stage="await_attack",
        expected_callback="post_attach_main",
        turn=state.turn,
        player=owner,
        first_player=state.firstPlayer,
        start_action_count=state.turnActionCount,
        supporter_played=state.supporterPlayed,
        stadium_played=state.stadiumPlayed,
        retreated=state.retreated,
        active_serial=active.serial,
        active_static_fingerprint=_active_psychic_static_fingerprint(active),
        target_serial=target.serial,
        target_fingerprint=_bridge_target_fingerprint(target, theirs),
        selected_energy_serial=energy.serial,
        selected_energy_fingerprint=_bridge_card_fingerprint(energy),
        replaced_parent_energy_serial=parent_energy.serial,
        replaced_parent_target_serial=parent_target.serial,
        replaced_parent_target_fingerprint=_bridge_pokemon_fingerprint(
            parent_target
        ),
        pre_hand_count=mine.handCount,
        post_attach_hand_fingerprint=post_attach_hand,
        own_deck_count=mine.deckCount,
        opponent_deck_count=theirs.deckCount,
        own_prize_count=len(mine.prize),
        opponent_prize_count=len(theirs.prize),
        opponent_hand_count=theirs.handCount,
        own_bench_max=mine.benchMax,
        opponent_bench_max=theirs.benchMax,
        own_bench_fingerprint=_terminal_bench_fingerprint(mine),
        opponent_bench_fingerprint=_terminal_bench_fingerprint(theirs),
        own_discard_fingerprint=_terminal_card_group_fingerprint(mine.discard),
        opponent_discard_fingerprint=_terminal_card_group_fingerprint(
            theirs.discard
        ),
        stadium_fingerprint=_terminal_card_group_fingerprint(state.stadium),
        target_prizes=prize_count(target),
        target_resolution_moves=(
            (target.id, target.serial, int(AreaType.ACTIVE)),
            *(
                (card.id, card.serial, int(AreaType.PRE_EVOLUTION))
                for card in target.preEvolution
            ),
            *(
                (card.id, card.serial, int(AreaType.ENERGY))
                for card in target.energyCards
            ),
        ),
        stadium_reduction=reduction,
        damage_floor=damage_floor,
    )
    return [option_index]


def _start_terminal_prize_psychic_attach(
    obs_dict: dict,
    obs: Observation,
    parent_action: list[int],
    inherited_owner_at_entry: bool,
) -> list[int] | None:
    before = _terminal_parent_policy_snapshot()
    try:
        action = _start_terminal_prize_psychic_attach_unsafe(
            obs_dict,
            obs,
            parent_action,
            inherited_owner_at_entry,
        )
    except Exception:
        _clear_terminal_prize_psychic_attach_latch()
        return None
    if before != _terminal_parent_policy_snapshot():
        _clear_terminal_prize_psychic_attach_latch()
        return None
    if action is None and _terminal_prize_psychic_attach_latch:
        _clear_terminal_prize_psychic_attach_latch()
    return action


def _terminal_prize_post_attach_is_same(
    obs_dict: dict, obs: Observation, latch: dict
) -> bool:
    state = obs.current
    if (
        state.result != -1
        or state.yourIndex != latch.get("player")
        or state.turn != latch.get("turn")
        or state.firstPlayer != latch.get("first_player")
        or state.turnActionCount != latch.get("start_action_count") + 1
        or state.supporterPlayed != latch.get("supporter_played")
        or state.stadiumPlayed != latch.get("stadium_played")
        or state.retreated != latch.get("retreated")
        or not state.energyAttached
        or state.looking is not None
        or not _terminal_main_select_is_ordinary(obs.select)
        or not _two_prize_raw_parsed_agree(obs_dict, obs)
        or not _terminal_basic_psychic_metadata_is_exact()
        or not _two_prize_powerful_hand_metadata_is_exact()
        or not _terminal_public_cards_are_owned_and_unique(state)
        or _two_prize_inherited_owner_active()
        or len(
            [
                option
                for option in obs.select.option
                if _two_prize_option_is_exact(option, OptionType.END)
            ]
        )
        != 1
        or not _terminal_attachment_log_is_exact(obs, latch)
    ):
        return False

    owner = state.yourIndex
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    if (
        len(mine.active) != 1
        or len(theirs.active) != 1
        or not _terminal_active_status_is_clear(mine)
        or not _terminal_active_status_is_clear(theirs)
    ):
        return False
    active = mine.active[0]
    target = theirs.active[0]
    hand_fingerprint = _active_psychic_hand_fingerprint(mine, owner)
    selected = latch.get("selected_energy_fingerprint")
    if (
        not _bridge_pokemon_is_publicly_complete(active, owner)
        or active.id != Alakazam
        or active.serial != latch.get("active_serial")
        or _active_psychic_static_fingerprint(active)
        != latch.get("active_static_fingerprint")
        or active.tools
        or tuple(active.energies) != (EnergyType.PSYCHIC,)
        or tuple(_bridge_card_fingerprint(card) for card in active.energyCards)
        != (selected,)
        or selected is None
        or selected[0] != Basic_Psychic_Energy
        or selected[1] != latch.get("selected_energy_serial")
        or selected[2] != owner
        or not _two_prize_alakazam_lineage_is_complete(active, owner)
        or target.serial != latch.get("target_serial")
        or _bridge_target_fingerprint(target, theirs)
        != latch.get("target_fingerprint")
        or not _terminal_two_prize_target_is_clear(state, target, 1 - owner)
        or hand_fingerprint != latch.get("post_attach_hand_fingerprint")
        or mine.handCount != latch.get("pre_hand_count") - 1
        or selected in hand_fingerprint
        or mine.deckCount != latch.get("own_deck_count")
        or theirs.deckCount != latch.get("opponent_deck_count")
        or len(mine.prize) != latch.get("own_prize_count")
        or len(theirs.prize) != latch.get("opponent_prize_count")
        or theirs.handCount != latch.get("opponent_hand_count")
        or mine.benchMax != latch.get("own_bench_max")
        or theirs.benchMax != latch.get("opponent_bench_max")
        or _terminal_bench_fingerprint(mine)
        != latch.get("own_bench_fingerprint")
        or _terminal_bench_fingerprint(theirs)
        != latch.get("opponent_bench_fingerprint")
        or not _terminal_opponent_bench_skills_are_harmless(
            theirs, 1 - owner
        )
        or not _terminal_opponent_public_transient_damage_is_clear(
            theirs, 1 - owner
        )
        or _terminal_card_group_fingerprint(mine.discard)
        != latch.get("own_discard_fingerprint")
        or _terminal_card_group_fingerprint(theirs.discard)
        != latch.get("opponent_discard_fingerprint")
        or _terminal_card_group_fingerprint(state.stadium)
        != latch.get("stadium_fingerprint")
        or prize_count(target) != latch.get("target_prizes")
        or len(mine.prize) > prize_count(target)
    ):
        return False

    reduction = _terminal_full_metal_lab_reduction(state, target)
    damage_floor = 20 * mine.handCount - (reduction or 0)
    if (
        reduction is None
        or reduction != latch.get("stadium_reduction")
        or damage_floor != latch.get("damage_floor")
        or damage_floor < target.hp
    ):
        return False
    return _bridge_protected_serials_are_unique(
        state,
        [
            *_bridge_pokemon_component_serials(active),
            *_bridge_pokemon_component_serials(target),
            *(stadium.serial for stadium in state.stadium),
        ],
    )


def _terminal_log_is_exact(log, **expected) -> bool:
    return all(
        value == expected.get(field)
        for field, value in vars(log).items()
    )


def _terminal_attachment_log_is_exact(obs: Observation, latch: dict) -> bool:
    if len(obs.logs) != 1:
        return False
    return _terminal_log_is_exact(
        obs.logs[0],
        type=11,
        playerIndex=latch.get("player"),
        cardId=Basic_Psychic_Energy,
        serial=latch.get("selected_energy_serial"),
        cardIdTarget=Alakazam,
        serialTarget=latch.get("active_serial"),
    )


def _terminal_prize_resolution_logs_are_exact(
    obs: Observation, latch: dict
) -> bool:
    moves = tuple(latch.get("target_resolution_moves") or ())
    if len(obs.logs) != 2 + len(moves):
        return False
    target = latch.get("target_fingerprint")
    if (
        not isinstance(target, tuple)
        or len(target) < 2
        or not _terminal_log_is_exact(
            obs.logs[0],
            type=15,
            playerIndex=latch.get("player"),
            cardId=Alakazam,
            serial=latch.get("active_serial"),
            attackId=ATTACK_POWERFUL_HAND,
        )
        or not _terminal_log_is_exact(
            obs.logs[1],
            type=16,
            playerIndex=1 - latch.get("player"),
            cardId=target[0],
            serial=target[1],
            value=-20 * (latch.get("pre_hand_count") - 1),
            putDamageCounter=True,
        )
    ):
        return False
    observed_moves = []
    for log in obs.logs[2:]:
        if not _terminal_log_is_exact(
            log,
            type=6,
            playerIndex=1 - latch.get("player"),
            cardId=log.cardId,
            serial=log.serial,
            fromArea=log.fromArea,
            toArea=AreaType.DISCARD,
        ):
            return False
        observed_moves.append((log.cardId, log.serial, int(log.fromArea)))
    return sorted(observed_moves) == sorted(moves)


def _terminal_two_prize_prompt_action(
    obs_dict: dict, obs: Observation, latch: dict
) -> list[int] | None:
    state = obs.current
    select = obs.select
    owner = state.yourIndex
    if (
        state.result != -1
        or owner != latch.get("player")
        or state.turn != latch.get("turn")
        or state.firstPlayer != latch.get("first_player")
        or state.turnActionCount != latch.get("start_action_count") + 2
        or state.supporterPlayed != latch.get("supporter_played")
        or state.stadiumPlayed != latch.get("stadium_played")
        or state.retreated != latch.get("retreated")
        or not state.energyAttached
        or state.looking is not None
        or int(select.type) != 1
        or select.context != SelectContext.TO_HAND
        or select.minCount != 2
        or select.maxCount != 2
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
        or not _two_prize_raw_parsed_agree(obs_dict, obs)
        or not _terminal_public_cards_are_owned_and_unique(state)
        or _two_prize_inherited_owner_active()
        or not _terminal_prize_resolution_logs_are_exact(obs, latch)
    ):
        return None
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    if (
        len(mine.active) != 1
        or theirs.active
        or not _terminal_active_status_is_clear(mine)
        or not _terminal_active_status_is_clear(theirs)
    ):
        return None
    active = mine.active[0]
    selected = latch.get("selected_energy_fingerprint")
    hand_fingerprint = _active_psychic_hand_fingerprint(mine, owner)
    if (
        active.id != Alakazam
        or active.serial != latch.get("active_serial")
        or _active_psychic_static_fingerprint(active)
        != latch.get("active_static_fingerprint")
        or tuple(active.energies) != (EnergyType.PSYCHIC,)
        or tuple(_bridge_card_fingerprint(card) for card in active.energyCards)
        != (selected,)
        or hand_fingerprint != latch.get("post_attach_hand_fingerprint")
        or mine.handCount != latch.get("pre_hand_count") - 1
        or mine.deckCount != latch.get("own_deck_count")
        or theirs.deckCount != latch.get("opponent_deck_count")
        or len(mine.prize) != latch.get("own_prize_count")
        or len(theirs.prize) != latch.get("opponent_prize_count")
        or theirs.handCount != latch.get("opponent_hand_count")
        or mine.benchMax != latch.get("own_bench_max")
        or theirs.benchMax != latch.get("opponent_bench_max")
        or _terminal_bench_fingerprint(mine)
        != latch.get("own_bench_fingerprint")
        or _terminal_bench_fingerprint(theirs)
        != latch.get("opponent_bench_fingerprint")
        or not _terminal_opponent_bench_skills_are_harmless(
            theirs, 1 - owner
        )
        or not _terminal_opponent_public_transient_damage_is_clear(
            theirs, 1 - owner
        )
        or _terminal_card_group_fingerprint(mine.discard)
        != latch.get("own_discard_fingerprint")
        or _terminal_card_group_fingerprint(state.stadium)
        != latch.get("stadium_fingerprint")
    ):
        return None
    before_discard = tuple(latch.get("opponent_discard_fingerprint") or ())
    current_discard = _terminal_card_group_fingerprint(theirs.discard)
    expected_added = tuple(
        (card_id, serial, 1 - owner)
        for card_id, serial, _ in latch.get("target_resolution_moves", ())
    )
    if (
        current_discard[: len(before_discard)] != before_discard
        or sorted(current_discard[len(before_discard) :])
        != sorted(expected_added)
    ):
        return None
    matches = []
    for option_index, option in enumerate(select.option):
        if _two_prize_option_is_exact(
            option,
            OptionType.CARD,
            area=AreaType.PRIZE,
            index=option.index,
            playerIndex=owner,
        ):
            matches.append((option.index, option_index))
    if (
        len(select.option) != 2
        or len(matches) != 2
        or {prize_index for prize_index, _ in matches} != {0, 1}
    ):
        return None
    return [
        option_index
        for _, option_index in sorted(matches, key=lambda row: row[0])
    ]


def _terminal_prize_psychic_attach_overlay_unsafe(
    obs_dict: dict, obs: Observation
) -> list[int] | None:
    """Advance only the frozen terminal attachment transaction."""
    if not _terminal_prize_psychic_attach_latch:
        return None
    latch = _terminal_prize_psychic_attach_latch
    if latch.get("stage") == "await_terminal":
        _clear_terminal_prize_psychic_attach_latch()
        return None
    if latch.get("stage") == "await_resolution":
        if latch.get("expected_callback") != "two_prize_prompt":
            _clear_terminal_prize_psychic_attach_latch()
            return None
        action = _terminal_two_prize_prompt_action(obs_dict, obs, latch)
        if action is None:
            _clear_terminal_prize_psychic_attach_latch()
            return None
        latch["stage"] = "await_terminal"
        latch["expected_callback"] = "terminal_resolution"
        return action
    if (
        latch.get("stage") != "await_attack"
        or latch.get("expected_callback") != "post_attach_main"
        or not _terminal_prize_post_attach_is_same(obs_dict, obs, latch)
    ):
        _clear_terminal_prize_psychic_attach_latch()
        return None
    matches = [
        option_index
        for option_index, option in enumerate(obs.select.option)
        if _two_prize_option_is_exact(
            option,
            OptionType.ATTACK,
            attackId=ATTACK_POWERFUL_HAND,
        )
    ]
    if len(matches) != 1:
        _clear_terminal_prize_psychic_attach_latch()
        return None
    latch["stage"] = "await_resolution"
    latch["expected_callback"] = "two_prize_prompt"
    return [matches[0]]


def _terminal_prize_psychic_attach_overlay(
    obs_dict: dict, obs: Observation
) -> list[int] | None:
    try:
        return _terminal_prize_psychic_attach_overlay_unsafe(obs_dict, obs)
    except Exception:
        _clear_terminal_prize_psychic_attach_latch()
        return None


def agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        _clear_emergency_state(clear_cache=True)
        return my_deck

    state = obs.current
    select = obs.select
    context = select.context
    terminal_prize_owner_at_entry = bool(
        _terminal_prize_psychic_attach_latch
    )
    inherited_owner_at_entry = _two_prize_inherited_owner_active()
    _prepare_emergency_state(obs)
    terminal_prize_stale_prepared = (
        terminal_prize_owner_at_entry
        and not _terminal_prize_psychic_attach_latch
    )
    decision_signature = _decision_signature(obs, obs_dict)
    if (
        _last_decision_signature == decision_signature
        and _last_decision_action is not None
    ):
        return list(_last_decision_action)

    had_terminal_prize_attach_latch = bool(
        _terminal_prize_psychic_attach_latch
    )
    terminal_prize_action = _terminal_prize_psychic_attach_overlay(
        obs_dict, obs
    )
    if terminal_prize_action is not None:
        return _remember_action(
            _decision_signature(obs, obs_dict), terminal_prize_action
        )
    terminal_prize_attach_delegated = (
        terminal_prize_stale_prepared
        or (
            had_terminal_prize_attach_latch
            and not _terminal_prize_psychic_attach_latch
        )
    )

    my_index = state.yourIndex
    my_state = state.players[my_index]
    op_state = state.players[1 - my_index]
    my_prize_count = len(my_state.prize)

    had_turn_objective_recovery_latch = bool(
        _turn_objective_recovery_latch
    )
    recovery_action = _turn_guard_recovery_overlay(obs)
    if recovery_action is not None:
        return _remember_action(
            _decision_signature(obs, obs_dict), recovery_action
        )
    turn_objective_recovery_delegated = (
        had_turn_objective_recovery_latch
        and not _turn_objective_recovery_latch
    )

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

    had_guarded_teleportation_latch = bool(
        _guarded_teleportation_latch
    )
    guarded_teleportation_action = _guarded_teleportation_overlay(obs)
    if guarded_teleportation_action is not None:
        return _remember_action(
            _decision_signature(obs, obs_dict), guarded_teleportation_action
        )
    guarded_teleportation_delegated = (
        had_guarded_teleportation_latch
        and not _guarded_teleportation_latch
    )

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
    turn_objective_action = None
    if not turn_objective_recovery_delegated:
        turn_objective_action = _public_h0_h1_turn_objective_guard(
            obs_dict,
            obs,
            chosen_action,
            inherited_owner_at_entry,
        )
    if turn_objective_action is not None:
        guarded_option = select.option[turn_objective_action[0]]
        guarded_card = None
        if guarded_option.type == OptionType.PLAY:
            guarded_card = _turn_guard_hand_card(
                my_state, guarded_option.index, my_index
            )
        if guarded_card is not None and guarded_card.id == Sacred_Ash:
            if not _start_turn_guard_recovery_latch(
                obs, turn_objective_action
            ):
                turn_objective_action = None
            else:
                return _remember_action(
                    _decision_signature(obs, obs_dict),
                    turn_objective_action,
                )
        else:
            return _remember_action(
                decision_signature, turn_objective_action
            )

    # The exact-v3 policy and all inherited overlays have finalized their
    # ordinary MAIN choice.  Only its unique RETREAT can start this isolated
    # attack-to-switch continuity transaction.
    if (
        not guarded_teleportation_delegated
        and context == SelectContext.MAIN
        and len(chosen_action) == 1
    ):
        teleportation_action = _start_guarded_teleportation_continuity(
            obs, scores, chosen_action
        )
        if teleportation_action is not None:
            return _remember_action(
                _decision_signature(obs, obs_dict), teleportation_action
            )

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
        and not _guarded_teleportation_latch
    ):
        transaction_action = _start_stranded_retreat_ko_bridge(obs)
        if transaction_action is not None:
            # The first activation created the latch after decision_signature
            # was computed.  Recompute once so an identical repeated callback
            # returns the exact cached RETREAT instead of advancing the latch.
            return _remember_action(
                _decision_signature(obs, obs_dict), transaction_action
            )

    if not terminal_prize_attach_delegated:
        terminal_prize_action = _start_terminal_prize_psychic_attach(
            obs_dict,
            obs,
            chosen_action,
            inherited_owner_at_entry,
        )
        if terminal_prize_action is not None:
            return _remember_action(
                _decision_signature(obs, obs_dict), terminal_prize_action
            )

    if (
        context == SelectContext.MAIN
        and chosen_action
        and not _hilda_source_latch
        and not _enriching_reserve_latch
        and not _fez_ko_bridge_latch
        and not _active_psychic_ko_latch
        and not _stranded_retreat_ko_latch
        and not _guarded_teleportation_latch
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
        or _guarded_teleportation_latch
    ):
        return _remember_action(decision_signature, chosen_action)
    _clear_decision_cache()
    return chosen_action
