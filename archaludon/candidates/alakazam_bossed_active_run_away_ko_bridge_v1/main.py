import os
import sys
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, LogType, Observation, SelectContext, OptionType, Card, Pokemon, all_card_data, to_observation_class

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
Acerola_Mischief = 1228    # opponent lingering effect guard
Hilda = 1225             # x4
Dawn = 1231              # x4
Battle_Cage = 1264       # x4
Basic_Psychic_Energy = 5   # x2
Telepath_Psychic_Energy = 19  # x4
Enriching_Energy = 13    # x1  (ACE SPEC)

# Opponent card IDs to watch for
Duskull = 131
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

pre_turn = 0
ability_used_dudunsparce = False
ability_used_fezandipiti = False
_bossed_active_bridge_latch = None


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


def _clear_bossed_active_bridge_latch() -> None:
    """Clear the explicit Boss -> Run Away -> promotion -> attack bridge."""
    global _bossed_active_bridge_latch
    _bossed_active_bridge_latch = None


def _positive_serial(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _previous_opponent_turn_bounds(
    logs: list, my_index: int
) -> tuple[int, int, int] | None:
    """Return exact previous-opponent/start-end/current-start log bounds."""
    if my_index not in (0, 1):
        return None
    opponent_index = 1 - my_index
    my_starts = [
        index
        for index, entry in enumerate(logs)
        if entry.type == LogType.TURN_START and entry.playerIndex == my_index
    ]
    if not my_starts:
        return None
    my_start = my_starts[-1]
    opponent_starts = [
        index
        for index, entry in enumerate(logs[:my_start])
        if entry.type == LogType.TURN_START
        and entry.playerIndex == opponent_index
    ]
    if not opponent_starts:
        return None
    opponent_start = opponent_starts[-1]
    turn_starts = [
        (index, entry.playerIndex)
        for index, entry in enumerate(logs[opponent_start : my_start + 1], opponent_start)
        if entry.type == LogType.TURN_START
    ]
    if turn_starts != [
        (opponent_start, opponent_index),
        (my_start, my_index),
    ]:
        return None
    opponent_ends = [
        index
        for index, entry in enumerate(logs[opponent_start + 1 : my_start], opponent_start + 1)
        if entry.type == LogType.TURN_END
        and entry.playerIndex == opponent_index
    ]
    if len(opponent_ends) != 1:
        return None
    return opponent_start, opponent_ends[0], my_start


def _boss_forced_switch_chain_certified(
    logs: list, my_index: int, active_serial: int
) -> bool:
    """Prove one unambiguous Boss-and-switch chain in the previous turn."""
    if not _positive_serial(active_serial):
        return False
    bounds = _previous_opponent_turn_bounds(logs, my_index)
    if bounds is None:
        return False
    opponent_start, opponent_end, my_start = bounds
    opponent_index = 1 - my_index

    boss_plays = [
        index
        for index, entry in enumerate(logs[opponent_start + 1 : opponent_end], opponent_start + 1)
        if entry.type == LogType.PLAY
        and entry.playerIndex == opponent_index
        and entry.cardId == Boss_Orders
        and _positive_serial(entry.serial)
    ]
    if len(boss_plays) != 1:
        return False
    boss_play = boss_plays[0]

    forced_switches = [
        (index, entry)
        for index, entry in enumerate(logs[boss_play + 1 : opponent_end], boss_play + 1)
        if entry.type == LogType.SWITCH and entry.playerIndex == my_index
    ]
    if len(forced_switches) != 1:
        return False
    switch_index, switch_entry = forced_switches[0]
    if (
        switch_entry.cardIdBench != Dudunsparce
        or switch_entry.serialBench != active_serial
        or not _positive_serial(switch_entry.serialActive)
        or switch_entry.serialActive == switch_entry.serialBench
    ):
        return False

    intervening_action_types = {
        LogType.PLAY,
        LogType.ATTACH,
        LogType.EVOLVE,
        LogType.DEVOLVE,
        LogType.ATTACK,
        LogType.TURN_END,
    }
    if any(
        entry.type in intervening_action_types
        for entry in logs[boss_play + 1 : switch_index]
    ):
        return False
    return boss_play < switch_index < opponent_end < my_start


def _card_fingerprint(card: Card) -> tuple | None:
    if (
        card is None
        or not isinstance(card.id, int)
        or not _positive_serial(card.serial)
    ):
        return None
    return (card.id, card.serial)


def _pokemon_fingerprint(pokemon: Pokemon) -> tuple | None:
    if (
        pokemon is None
        or not isinstance(pokemon.id, int)
        or not _positive_serial(pokemon.serial)
        or not isinstance(pokemon.hp, int)
        or not isinstance(pokemon.maxHp, int)
        or not isinstance(pokemon.energyCards, list)
        or not isinstance(pokemon.tools, list)
        or not isinstance(pokemon.preEvolution, list)
    ):
        return None
    energies = tuple(_card_fingerprint(card) for card in pokemon.energyCards)
    tools = tuple(_card_fingerprint(card) for card in pokemon.tools)
    pre_evolution = tuple(_card_fingerprint(card) for card in pokemon.preEvolution)
    if (
        any(item is None for item in energies)
        or any(item is None for item in tools)
        or any(item is None for item in pre_evolution)
    ):
        return None
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        energies,
        tools,
        pre_evolution,
    )


def _metadata_blocks_counter_attack_effect(card_id: int) -> bool | None:
    """Return whether known printed metadata can block Powerful Hand's effect."""
    data = card_table.get(card_id)
    if data is None or not isinstance(data.skills, list):
        return None
    for skill in data.skills:
        text = getattr(skill, "text", None)
        if not isinstance(text, str):
            return None
        normalized = " ".join(text.lower().split())
        if (
            "prevent all effects of attacks" in normalized
            or "prevent all damage from and effects of attacks" in normalized
        ):
            return True
    return False


def _target_counter_certificate_and_fingerprint(
    obs: Observation, my_index: int
) -> tuple | None:
    """Return an immutable public target certificate, or fail closed."""
    if obs.current is None or my_index not in (0, 1):
        return None
    opponent_index = 1 - my_index
    op_state = obs.current.players[opponent_index]
    if len(op_state.active) != 1 or op_state.active[0] is None:
        return None
    target = op_state.active[0]
    target_fingerprint = _pokemon_fingerprint(target)
    if target_fingerprint is None or target.hp <= 0:
        return None

    statuses = (
        op_state.poisoned,
        op_state.burned,
        op_state.asleep,
        op_state.paralyzed,
        op_state.confused,
    )
    if any(not isinstance(value, bool) for value in statuses):
        return None

    target_data = card_table.get(target.id)
    if target_data is None or target_data.energyType is None:
        return None
    attached_energy_ids = {card.id for card in target.energyCards}
    if Mist_Energy in attached_energy_ids:
        return None
    if (
        Rock_Fighting_Energy in attached_energy_ids
        and target_data.energyType == EnergyType.FIGHTING
    ):
        return None

    visible_opponent = [
        pokemon
        for pokemon in list(op_state.active) + list(op_state.bench)
        if pokemon is not None
    ]
    field_fingerprints = []
    for pokemon in visible_opponent:
        fingerprint = _pokemon_fingerprint(pokemon)
        if fingerprint is None:
            return None
        field_fingerprints.append(fingerprint)
        blocked = _metadata_blocks_counter_attack_effect(pokemon.id)
        if blocked is None or blocked:
            return None

    for attached in list(target.energyCards) + list(target.tools):
        if attached.id in (Mist_Energy, Rock_Fighting_Energy):
            # Their exact printed conditions were handled above.
            continue
        blocked = _metadata_blocks_counter_attack_effect(attached.id)
        if blocked is None or blocked:
            return None

    # Acerola's lingering one-turn protection is public in the immediately
    # preceding opponent-turn logs. Its target selection is not represented
    # unambiguously enough here, so any such play fails closed.
    previous_turn = _previous_opponent_turn_bounds(obs.logs, my_index)
    if previous_turn is not None:
        opponent_start, opponent_end, _ = previous_turn
        if any(
            entry.type == LogType.PLAY
            and entry.playerIndex == opponent_index
            and entry.cardId == Acerola_Mischief
            for entry in obs.logs[opponent_start + 1 : opponent_end]
        ):
            return None

    stadium_fingerprint = tuple(
        item
        for card in obs.current.stadium
        if (item := _card_fingerprint(card)) is not None
    )
    if len(stadium_fingerprint) != len(obs.current.stadium):
        return None

    return (
        target_fingerprint,
        tuple(field_fingerprints),
        statuses,
        stadium_fingerprint,
    )


def _ready_alakazam_promotion(my_state) -> tuple[int, int] | None:
    """Freeze max attached-card count, then lowest Bench index."""
    ready = []
    for bench_index, pokemon in enumerate(my_state.bench):
        if (
            pokemon is None
            or pokemon.id != Alakazam
            or not _positive_serial(pokemon.serial)
            or not any(
                energy.id in PSYCHIC_ENERGY_IDS
                for energy in pokemon.energyCards
            )
        ):
            continue
        attached_count = len(pokemon.energyCards) + len(pokemon.tools)
        ready.append((-attached_count, bench_index, pokemon.serial))
    if not ready:
        return None
    _, bench_index, serial = min(ready)
    return bench_index, serial


def _bossed_active_bridge_start_certificate(
    obs: Observation,
) -> tuple[int, dict] | None:
    """Return the Active ability option and a frozen three-stage latch."""
    if obs.current is None or obs.select is None:
        return None
    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    if (
        select.context != SelectContext.MAIN
        or select.minCount != 1
        or select.maxCount != 1
        or state.turnActionCount != 1
        or my_index not in (0, 1)
    ):
        return None

    my_state = state.players[my_index]
    if (
        my_state.hand is None
        or len(my_state.hand) != my_state.handCount
        or len(my_state.active) != 1
        or my_state.active[0] is None
    ):
        return None
    active = my_state.active[0]
    if (
        active.id != Dudunsparce
        or not _positive_serial(active.serial)
        or len(active.preEvolution) != 1
        or active.preEvolution[0].id != Dunsparce
        or not _positive_serial(active.preEvolution[0].serial)
        or active.energyCards
        or active.energies
        or active.tools
    ):
        return None
    if not _boss_forced_switch_chain_certified(
        obs.logs, my_index, active.serial
    ):
        return None

    ability_options = []
    for option_index, option in enumerate(select.option):
        if (
            option.type == OptionType.ABILITY
            and option.area == AreaType.ACTIVE
            and option.index == 0
            and (option.playerIndex is None or option.playerIndex == my_index)
        ):
            ability_options.append(option_index)
    if len(ability_options) != 1:
        return None

    # With zero Energy the Active Dudunsparce has no legal certified attack.
    # Therefore no parent same-turn KO can preserve this Active position.
    if any(option.type == OptionType.ATTACK for option in select.option):
        return None

    promotion = _ready_alakazam_promotion(my_state)
    if promotion is None:
        return None
    promotion_bench_index, promotion_serial = promotion

    target_certificate = _target_counter_certificate_and_fingerprint(
        obs, my_index
    )
    if target_certificate is None:
        return None
    target = state.players[1 - my_index].active[0]
    if not _positive_serial(target.serial) or target.hp <= 0:
        return None

    deck_count = my_state.deckCount
    hand_count = my_state.handCount
    if not isinstance(deck_count, int) or deck_count < 3:
        return None
    expected_hand = hand_count + 3
    returned_count = 2
    expected_deck = deck_count - 3 + returned_count
    if 20 * expected_hand < target.hp:
        return None

    target_prizes = prize_count(target)
    post_ko_prizes = len(my_state.prize) - target_prizes
    if not (
        post_ko_prizes == 0
        or expected_deck > post_ko_prizes
    ):
        return None

    latch = {
        "stage": "await_promotion",
        "turn": state.turn,
        "my_index": my_index,
        "source_serial": active.serial,
        "promotion_bench_index": promotion_bench_index,
        "promotion_serial": promotion_serial,
        "target_serial": target.serial,
        "target_hp": target.hp,
        "target_certificate": target_certificate,
        "expected_hand": expected_hand,
        "expected_deck": expected_deck,
        "own_prizes": len(my_state.prize),
        "post_ko_prizes": post_ko_prizes,
        "returned_count": returned_count,
    }
    return ability_options[0], latch


def _bossed_active_bridge_option_index(obs: Observation) -> int | None:
    """Advance the exact three-stage latch; otherwise clear and delegate."""
    global _bossed_active_bridge_latch

    if obs.current is None or obs.select is None:
        _clear_bossed_active_bridge_latch()
        return None

    state = obs.current
    select = obs.select
    my_index = state.yourIndex
    latch = _bossed_active_bridge_latch

    if latch is None:
        started = _bossed_active_bridge_start_certificate(obs)
        if started is None:
            return None
        option_index, latch = started
        _bossed_active_bridge_latch = latch
        return option_index

    if (
        state.turn != latch["turn"]
        or my_index != latch["my_index"]
        or select.minCount != 1
        or select.maxCount != 1
    ):
        _clear_bossed_active_bridge_latch()
        return None

    my_state = state.players[my_index]
    target_certificate = _target_counter_certificate_and_fingerprint(
        obs, my_index
    )
    common_ok = (
        my_state.hand is not None
        and len(my_state.hand) == my_state.handCount
        and my_state.handCount == latch["expected_hand"]
        and my_state.deckCount == latch["expected_deck"]
        and len(my_state.prize) == latch["own_prizes"]
        and target_certificate == latch["target_certificate"]
    )
    if not common_ok:
        _clear_bossed_active_bridge_latch()
        return None

    if latch["stage"] == "await_promotion":
        if (
            select.context != SelectContext.TO_ACTIVE
            or any(pokemon is not None for pokemon in my_state.active)
        ):
            _clear_bossed_active_bridge_latch()
            return None
        matching_options = []
        for option_index, option in enumerate(select.option):
            if (
                option.type != OptionType.CARD
                or option.area != AreaType.BENCH
                or option.playerIndex not in (None, my_index)
                or option.index is None
                or option.index < 0
                or option.index >= len(my_state.bench)
            ):
                continue
            pokemon = my_state.bench[option.index]
            if (
                pokemon is not None
                and pokemon.id == Alakazam
                and pokemon.serial == latch["promotion_serial"]
            ):
                matching_options.append(option_index)
        if len(matching_options) != 1:
            _clear_bossed_active_bridge_latch()
            return None
        _bossed_active_bridge_latch = {
            **latch,
            "stage": "await_attack",
        }
        return matching_options[0]

    if latch["stage"] == "await_attack":
        if (
            select.context != SelectContext.MAIN
            or len(my_state.active) != 1
            or my_state.active[0] is None
        ):
            _clear_bossed_active_bridge_latch()
            return None
        active = my_state.active[0]
        own_statuses = (
            my_state.poisoned,
            my_state.burned,
            my_state.asleep,
            my_state.paralyzed,
            my_state.confused,
        )
        if (
            active.id != Alakazam
            or active.serial != latch["promotion_serial"]
            or not any(
                energy.id in PSYCHIC_ENERGY_IDS
                for energy in active.energyCards
            )
            or any(not isinstance(value, bool) or value for value in own_statuses)
            or 20 * my_state.handCount < latch["target_hp"]
            or not (
                latch["post_ko_prizes"] == 0
                or my_state.deckCount > latch["post_ko_prizes"]
            )
        ):
            _clear_bossed_active_bridge_latch()
            return None

        attack_options = [
            option_index
            for option_index, option in enumerate(select.option)
            if option.type == OptionType.ATTACK
            and option.attackId == ATTACK_POWERFUL_HAND
        ]
        _clear_bossed_active_bridge_latch()
        if len(attack_options) != 1:
            return None
        return attack_options[0]

    _clear_bossed_active_bridge_latch()
    return None


def agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        _clear_bossed_active_bridge_latch()
        return my_deck

    state = obs.current
    select = obs.select
    context = select.context
    my_index = state.yourIndex
    my_state = state.players[my_index]
    op_state = state.players[1 - my_index]
    my_prize_count = len(my_state.prize)

    global pre_turn, ability_used_dudunsparce, ability_used_fezandipiti
    if pre_turn != state.turn:
        pre_turn = state.turn
        ability_used_dudunsparce = False
        ability_used_fezandipiti = False
        if (
            _bossed_active_bridge_latch is not None
            and _bossed_active_bridge_latch.get("turn") != state.turn
        ):
            _clear_bossed_active_bridge_latch()

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

    # Three-stage public bridge: the first choice starts the latch; the next
    # two choices must be the frozen promotion and immediate Powerful Hand.
    bridge_option_index = _bossed_active_bridge_option_index(obs)
    if bridge_option_index is not None:
        bridge_option = select.option[bridge_option_index]
        if bridge_option.type == OptionType.ABILITY:
            ability_used_dudunsparce = True
        return [bridge_option_index]

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

    if context == SelectContext.MAIN:
        o = select.option[desc_indices[0]]
        if o.type == OptionType.ABILITY:
            card = get_card(obs, o.area, o.index, my_index)
            if card is not None:
                if card.id == Dudunsparce:
                    ability_used_dudunsparce = True
                elif card.id == Fezandipiti_ex:
                    ability_used_fezandipiti = True

    return desc_indices[:select.maxCount]
