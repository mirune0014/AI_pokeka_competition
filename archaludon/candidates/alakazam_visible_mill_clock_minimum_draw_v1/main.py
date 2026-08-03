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
Great_Tusk = 58
Duskull = 131
Slowpoke_IDs = (162, 327)
Froakie_IDs = (33, 945)
Wellspring_Mask_Ogerpon_ex = 108
N_Darumaka = 257
Dreepy = 119
Drakloak = 120
Dragapult_ex = 121
Mist_Energy = 11
Rock_Fighting_Energy = 20

# Attack IDs
ATTACK_LAND_COLLAPSE = 62
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


def _visible_mill_clock_mode(opponent_card_ids, logs, opponent_index, deck_count,
                             remaining_prizes):
    """Fail-closed public Great Tusk plus conservative deck-clock predicate."""
    if deck_count is None or remaining_prizes is None:
        return False
    visible_tusk = Great_Tusk in opponent_card_ids
    logged_land_collapse = any(
        getattr(log, "attackId", None) == ATTACK_LAND_COLLAPSE
        and getattr(log, "playerIndex", None) == opponent_index
        for log in (logs or [])
    )
    return bool(
        (visible_tusk or logged_land_collapse)
        and deck_count <= 5 * remaining_prizes + 1
    )


def _has_psychic_energy(pokemon):
    if pokemon is None:
        return False
    return any(
        getattr(card, "id", None) in PSYCHIC_ENERGY_IDS
        for card in (getattr(pokemon, "energyCards", None) or [])
    )


def _psychic_energy_in_hand(hand_counts):
    return sum(hand_counts[card_id] for card_id in PSYCHIC_ENERGY_IDS) > 0


def _has_ready_successor(bench, hand_counts):
    """Certify one distinct next-turn Alakazam route without another search."""
    energy_in_hand = _psychic_energy_in_hand(hand_counts)
    for pokemon in bench or []:
        attached = _has_psychic_energy(pokemon)
        if pokemon.id == Alakazam and attached:
            return True
        if pokemon.id == Kadabra:
            if hand_counts[Alakazam] > 0 and (attached or energy_in_hand):
                return True
        if pokemon.id == Abra:
            if (hand_counts[Rare_Candy] > 0 and hand_counts[Alakazam] > 0
                    and (attached or energy_in_hand)):
                return True
    return False


def _successor_wanted_card_ids(bench, hand_counts):
    """Missing cards for the closest public, no-further-search successor bundle."""
    plans = []
    energy_in_hand = _psychic_energy_in_hand(hand_counts)
    for bench_index, pokemon in enumerate(bench or []):
        missing = set()
        attached = _has_psychic_energy(pokemon)
        if pokemon.id == Alakazam:
            if not attached:
                missing.update(PSYCHIC_ENERGY_IDS)
        elif pokemon.id == Kadabra:
            if hand_counts[Alakazam] == 0:
                missing.add(Alakazam)
            if not attached and not energy_in_hand:
                missing.update(PSYCHIC_ENERGY_IDS)
        elif pokemon.id == Abra:
            if hand_counts[Rare_Candy] == 0:
                missing.add(Rare_Candy)
            if hand_counts[Alakazam] == 0:
                missing.add(Alakazam)
            if not attached and not energy_in_hand:
                missing.update(PSYCHIC_ENERGY_IDS)
        else:
            continue
        if missing:
            # The two Energy IDs are alternatives, not two missing cards.
            missing_units = len(missing - PSYCHIC_ENERGY_IDS)
            if missing & PSYCHIC_ENERGY_IDS:
                missing_units += 1
            plans.append((missing_units, bench_index, missing))
    if not plans:
        return set()
    return min(plans, key=lambda item: (item[0], item[1]))[2]


def _current_exact_ko_attack(active, opponent_active, legal_attack_ids, hand_size):
    """Certify an exact current-Active KO; never substitutes a bench attacker."""
    if active is None or opponent_active is None:
        return None
    if count_special_defense_energies(opponent_active) > 0:
        return None
    if (active.id == Alakazam and _has_psychic_energy(active)
            and ATTACK_POWERFUL_HAND in legal_attack_ids
            and hand_size * 20 >= opponent_active.hp):
        return ATTACK_POWERFUL_HAND
    if (active.id == Kadabra and _has_psychic_energy(active)
            and ATTACK_SUPER_PSY_BOLT in legal_attack_ids
            and opponent_active.hp <= 30):
        return ATTACK_SUPER_PSY_BOLT
    if (active.id == Abra and _has_psychic_energy(active)
            and ATTACK_TELEPORTATION in legal_attack_ids
            and opponent_active.hp <= 10):
        return ATTACK_TELEPORTATION
    return None


def _main_option_card(obs, option, my_index):
    if option.type in (OptionType.PLAY, OptionType.ATTACH, OptionType.EVOLVE):
        return get_card(obs, AreaType.HAND, option.index, my_index)
    if option.type == OptionType.ABILITY:
        return get_card(obs, option.area, option.index, my_index)
    return None


def _hilda_can_complete_successor(bench, hand_counts):
    energy_in_hand = _psychic_energy_in_hand(hand_counts)
    for pokemon in bench or []:
        attached = _has_psychic_energy(pokemon)
        if pokemon.id == Alakazam:
            if not attached and not energy_in_hand:
                return True
        elif pokemon.id == Kadabra:
            # Hilda can supply the missing Evolution, Energy, or both.
            if hand_counts[Alakazam] == 0 or (not attached and not energy_in_hand):
                return True
        elif pokemon.id == Abra and hand_counts[Rare_Candy] > 0:
            if hand_counts[Alakazam] == 0 or (not attached and not energy_in_hand):
                return True
    return False


def _single_alakazam_search_completes_successor(bench, hand_counts):
    if hand_counts[Alakazam] > 0:
        return False
    energy_in_hand = _psychic_energy_in_hand(hand_counts)
    for pokemon in bench or []:
        attached = _has_psychic_energy(pokemon)
        if pokemon.id == Kadabra and (attached or energy_in_hand):
            return True
        if (pokemon.id == Abra and hand_counts[Rare_Candy] > 0
                and (attached or energy_in_hand)):
            return True
    return False


def _critical_followup_order(obs, parent_order, my_index, hand_counts):
    """Minimize optional search selections after a certified critical action."""
    select = obs.select
    context = select.context
    effect_id = getattr(select.effect, "id", None)
    search_effects = {
        Buddy_Buddy_Poffin, Poke_Pad, Hilda, Dawn, Telepath_Psychic_Energy,
    }
    if effect_id not in search_effects:
        return parent_order, select.maxCount

    my_state = obs.current.players[my_index]
    op_state = obs.current.players[1 - my_index]
    active = my_state.active[0] if my_state.active else None
    opponent_active = op_state.active[0] if op_state.active else None
    legal_attack_ids = {
        option.attackId for option in select.option
        if option.type == OptionType.ATTACK
    }
    # Follow-up search observations normally contain CARD options, so infer the
    # already-legal attack from the actual Active and attached Psychic Energy.
    attack_is_publicly_payable = bool(
        active is not None
        and obs.current.turn >= 2
        and not my_state.asleep
        and not my_state.paralyzed
        and not my_state.confused
        and _has_psychic_energy(active)
    )
    if attack_is_publicly_payable:
        if active.id == Alakazam:
            legal_attack_ids.add(ATTACK_POWERFUL_HAND)
        elif active.id == Kadabra:
            legal_attack_ids.add(ATTACK_SUPER_PSY_BOLT)
        elif active.id == Abra:
            legal_attack_ids.add(ATTACK_TELEPORTATION)
    exact_ko = _current_exact_ko_attack(
        active, opponent_active, legal_attack_ids, len(my_state.hand or []),
    )
    successor_ready = _has_ready_successor(my_state.bench, hand_counts)
    if select.minCount == 0 and (exact_ko is not None or successor_ready):
        return parent_order, 0

    wanted = _successor_wanted_card_ids(my_state.bench, hand_counts)
    needs_ko_card = bool(
        attack_is_publicly_payable
        and active.id == Alakazam
        and opponent_active is not None
        and count_special_defense_energies(opponent_active) == 0
        and len(my_state.hand or []) * 20 < opponent_active.hp
    )
    ranked = list(parent_order)
    if context == SelectContext.TO_HAND and wanted:
        matching = [
            index for index in parent_order
            if get_card(obs, select.option[index].area,
                        select.option[index].index,
                        select.option[index].playerIndex).id in wanted
        ]
        if not matching and select.minCount == 0 and not needs_ko_card:
            return parent_order, 0
        ranked.sort(key=lambda index: (
            0 if (get_card(obs, select.option[index].area,
                           select.option[index].index,
                           select.option[index].playerIndex).id in wanted) else 1,
            parent_order.index(index),
        ))
    elif context == SelectContext.TO_BENCH:
        can_make_abra = (
            hand_counts[Rare_Candy] > 0
            and hand_counts[Alakazam] > 0
            and _psychic_energy_in_hand(hand_counts)
        )
        if can_make_abra:
            ranked.sort(key=lambda index: (
                0 if (get_card(obs, select.option[index].area,
                               select.option[index].index,
                               select.option[index].playerIndex).id == Abra) else 1,
                parent_order.index(index),
            ))
        elif select.minCount == 0:
            return parent_order, 0

    # Every search choice is optional in this package. Select only the minimum
    # legal count now and let the next public observation decide whether to stop.
    count = max(select.minCount, 1)
    return ranked, min(count, select.maxCount)


def _critical_main_order(obs, parent_order, my_index, hand_counts,
                         target_idx, target_pokemon, target_use_boss,
                         target_can_kill, target_prize_gain,
                         target_hammer_needed, need_retreat_energy):
    """Stable lexicographic Great Tusk route with parent order as final tie-break."""
    state = obs.current
    select = obs.select
    my_state = state.players[my_index]
    op_state = state.players[1 - my_index]
    active = my_state.active[0] if my_state.active else None
    opponent_active = op_state.active[0] if op_state.active else None
    hand_size = len(my_state.hand or [])
    legal_attack_ids = {
        option.attackId for option in select.option
        if option.type == OptionType.ATTACK
    }
    parent_rank = {index: rank for rank, index in enumerate(parent_order)}
    option_cards = {
        index: _main_option_card(obs, option, my_index)
        for index, option in enumerate(select.option)
    }
    play_indices = defaultdict(list)
    for index, option in enumerate(select.option):
        card = option_cards[index]
        if option.type == OptionType.PLAY and card is not None:
            play_indices[card.id].append(index)

    priorities = [7] * len(select.option)
    for index, option in enumerate(select.option):
        if option.type == OptionType.ATTACK:
            priorities[index] = 5
        elif option.type == OptionType.END:
            # When no certified route exists, preserve the deck instead of
            # falling through to an optional search, draw, or third line.
            priorities[index] = 6

    exact_attack_id = _current_exact_ko_attack(
        active, opponent_active, legal_attack_ids, hand_size,
    )
    exact_attack_indices = [
        index for index, option in enumerate(select.option)
        if option.type == OptionType.ATTACK and option.attackId == exact_attack_id
    ]
    if exact_attack_indices:
        final_prize = prize_count(opponent_active) >= len(my_state.prize)
        priorities[exact_attack_indices[0]] = 0 if final_prize else 1

    # Certify the parent's Boss/Hammer target only with the actual Active
    # attacker and after paying every known hand cost.
    route_target = None
    route_boss_cost = 0
    route_hammer_cost = 0
    route_needed_cards = None
    if (active is not None and active.id == Alakazam
            and _has_psychic_energy(active)
            and ATTACK_POWERFUL_HAND in legal_attack_ids):
        if target_can_kill and target_pokemon is not None:
            boss_ok = not target_use_boss or (
                not state.supporterPlayed and bool(play_indices[Boss_Orders])
            )
            hammer_ok = (
                target_hammer_needed == count_special_defense_energies(target_pokemon)
                and hand_counts[Enhanced_Hammer] >= target_hammer_needed
                and (target_hammer_needed == 0 or bool(play_indices[Enhanced_Hammer]))
            )
            if boss_ok and hammer_ok:
                route_target = target_pokemon
                route_boss_cost = 1 if target_use_boss else 0
                route_hammer_cost = target_hammer_needed
        elif opponent_active is not None and count_special_defense_energies(opponent_active) == 0:
            route_target = opponent_active

    if route_target is not None:
        cards_for_damage = (route_target.hp + 19) // 20
        route_needed_cards = max(
            0, cards_for_damage + route_boss_cost + route_hammer_cost - hand_size,
        )
        route_prizes = (
            target_prize_gain if route_target is target_pokemon
            else prize_count(route_target)
        )
        route_is_final = route_prizes >= len(my_state.prize)
        if route_needed_cards == 0:
            necessary = []
            if route_boss_cost:
                necessary.extend(play_indices[Boss_Orders])
            if route_hammer_cost:
                necessary.extend(play_indices[Enhanced_Hammer])
            if not necessary and route_target is opponent_active:
                necessary.extend(exact_attack_indices)
            if necessary:
                best = min(necessary, key=lambda index: parent_rank[index])
                priorities[best] = 0 if route_is_final else 1

    if min(priorities, default=7) > 1:
        # Category 3: one necessary, minimum-cost attack legalizer.
        enablers = []
        bench_ready_attackers = [
            (bench_index, pokemon) for bench_index, pokemon in enumerate(my_state.bench)
            if pokemon.id == Alakazam and _has_psychic_energy(pokemon)
        ]
        active_line_attack_legal = bool(
            active is not None and (
                (active.id == Alakazam and ATTACK_POWERFUL_HAND in legal_attack_ids)
                or (active.id == Kadabra and ATTACK_SUPER_PSY_BOLT in legal_attack_ids)
                or (active.id == Abra and ATTACK_TELEPORTATION in legal_attack_ids)
            )
        )
        if not active_line_attack_legal:
            for index, option in enumerate(select.option):
                card = option_cards[index]
                if option.type == OptionType.RETREAT and bench_ready_attackers:
                    enablers.append((0, 0, parent_rank[index], index))
                elif option.type == OptionType.ATTACH and card is not None:
                    pokemon = get_card(obs, option.inPlayArea, option.inPlayIndex, my_index)
                    is_basic = card.id == Basic_Psychic_Energy
                    is_telepath = card.id == Telepath_Psychic_Energy
                    if not (is_basic or is_telepath):
                        continue
                    if (active is not None and option.inPlayArea == AreaType.ACTIVE
                            and (active.id in ABRA_LINE or need_retreat_energy)):
                        enablers.append((0 if is_basic else 2, 1, parent_rank[index], index))
                    elif (pokemon is not None and pokemon.id == Alakazam
                            and option.inPlayArea == AreaType.BENCH):
                        enablers.append((0 if is_basic else 2, 2, parent_rank[index], index))
                elif option.type == OptionType.EVOLVE and card is not None:
                    pokemon = get_card(obs, option.inPlayArea, option.inPlayIndex, my_index)
                    if pokemon is None:
                        continue
                    target_is_active = option.inPlayArea == AreaType.ACTIVE
                    target_is_bench_attacker = (
                        option.inPlayArea == AreaType.BENCH
                        and pokemon.id == Kadabra
                        and _has_psychic_energy(pokemon)
                        and card.id == Alakazam
                    )
                    if (target_is_active and pokemon.id in (Abra, Kadabra)
                            and _has_psychic_energy(pokemon)):
                        cost = 2 if card.id == Kadabra else 3
                        enablers.append((cost, 3, parent_rank[index], index))
                    elif target_is_bench_attacker:
                        enablers.append((3, 4, parent_rank[index], index))
                elif (option.type == OptionType.PLAY and card is not None
                        and card.id == Rare_Candy and active is not None
                        and active.id == Abra and _has_psychic_energy(active)):
                    enablers.append((3, 5, parent_rank[index], index))
        if enablers:
            priorities[min(enablers)[3]] = 2

    successor_ready = _has_ready_successor(my_state.bench, hand_counts)

    if min(priorities, default=7) > 2 and route_needed_cards is not None and route_needed_cards > 0:
        # Category 4: exactly one minimum-deck-cost action that reaches the KO.
        converters = []
        first_successor_line = next((
            bench_index for bench_index, pokemon in enumerate(my_state.bench)
            if pokemon.id in ABRA_LINE
        ), None)
        for index, option in enumerate(select.option):
            card = option_cards[index]
            if option.type == OptionType.PLAY and card is not None:
                if (card.id == Hilda and route_boss_cost == 0
                        and route_needed_cards <= 1):
                    converters.append((2, 0, parent_rank[index], index))
                elif (card.id == Dawn and route_boss_cost == 0
                        and route_needed_cards <= 2):
                    converters.append((3, 1, parent_rank[index], index))
            elif option.type == OptionType.ABILITY and card is not None:
                if card.id in (Dudunsparce, Fezandipiti_ex) and route_needed_cards <= 3:
                    converters.append((3, 2, parent_rank[index], index))
            elif option.type == OptionType.EVOLVE and card is not None:
                if (not successor_ready and option.inPlayArea == AreaType.BENCH
                        and option.inPlayIndex == first_successor_line):
                    if card.id == Kadabra and route_needed_cards <= 1:
                        converters.append((2, 3, parent_rank[index], index))
                    elif card.id == Alakazam and route_needed_cards <= 2:
                        converters.append((3, 3, parent_rank[index], index))
            elif option.type == OptionType.ATTACH and card is not None:
                if card.id == Enriching_Energy and route_needed_cards <= 3:
                    converters.append((4, 4, parent_rank[index], index))
        converters = [item for item in converters if item[0] <= my_state.deckCount]
        if converters:
            priorities[min(converters)[3]] = 3

    if min(priorities, default=7) > 3 and not successor_ready:
        # Category 5: create one successor, never a second utility body.
        successor_actions = []
        for index, option in enumerate(select.option):
            card = option_cards[index]
            if card is None:
                continue
            if option.type == OptionType.ATTACH and card.id in PSYCHIC_ENERGY_IDS:
                pokemon = get_card(obs, option.inPlayArea, option.inPlayIndex, my_index)
                if (pokemon is not None and pokemon.id == Alakazam
                        and option.inPlayArea == AreaType.BENCH):
                    successor_actions.append((
                        0 if card.id == Basic_Psychic_Energy else 2,
                        0, parent_rank[index], index,
                    ))
            elif option.type == OptionType.PLAY and card.id == Abra:
                remaining_abra = hand_counts[Abra] - 1
                if (remaining_abra >= 0 and hand_counts[Rare_Candy] > 0
                        and hand_counts[Alakazam] > 0
                        and _psychic_energy_in_hand(hand_counts)):
                    successor_actions.append((0, 1, parent_rank[index], index))
            elif option.type == OptionType.PLAY and card.id == Buddy_Buddy_Poffin:
                if (hand_counts[Rare_Candy] > 0 and hand_counts[Alakazam] > 0
                        and _psychic_energy_in_hand(hand_counts)
                        and len(my_state.bench) < my_state.benchMax):
                    successor_actions.append((1, 2, parent_rank[index], index))
            elif option.type == OptionType.PLAY and card.id == Poke_Pad:
                if _single_alakazam_search_completes_successor(my_state.bench, hand_counts):
                    successor_actions.append((1, 3, parent_rank[index], index))
            elif option.type == OptionType.PLAY and card.id == Hilda:
                if _hilda_can_complete_successor(my_state.bench, hand_counts):
                    missing = _successor_wanted_card_ids(my_state.bench, hand_counts)
                    units = len(missing - PSYCHIC_ENERGY_IDS)
                    if missing & PSYCHIC_ENERGY_IDS:
                        units += 1
                    successor_actions.append((max(1, min(2, units)), 4, parent_rank[index], index))
            elif option.type == OptionType.PLAY and card.id == Dawn:
                if _single_alakazam_search_completes_successor(my_state.bench, hand_counts):
                    successor_actions.append((1, 5, parent_rank[index], index))
            elif option.type == OptionType.EVOLVE and card.id == Kadabra:
                pokemon = get_card(obs, option.inPlayArea, option.inPlayIndex, my_index)
                if (pokemon is not None and option.inPlayArea == AreaType.BENCH
                        and pokemon.id == Abra and hand_counts[Alakazam] > 0
                        and (_has_psychic_energy(pokemon)
                             or _psychic_energy_in_hand(hand_counts))):
                    successor_actions.append((2, 6, parent_rank[index], index))
        if successor_actions:
            priorities[min(successor_actions)[3]] = 4

    return sorted(parent_order, key=lambda index: priorities[index])


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


def agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
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

    visible_mill_clock_mode = _visible_mill_clock_mode(
        {pokemon.id for pokemon in op_all_pokemon},
        obs.logs,
        1 - my_index,
        my_state.deckCount,
        my_prize_count,
    )

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

    # Select in descending order of score
    desc_indices = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]
    result_count = select.maxCount

    if visible_mill_clock_mode:
        if context == SelectContext.MAIN:
            desc_indices = _critical_main_order(
                obs,
                desc_indices,
                my_index,
                hand_counts,
                target_idx,
                target_pokemon,
                target_use_boss,
                target_can_kill,
                target_prize_gain,
                target_hammer_needed,
                need_retreat_energy,
            )
        else:
            desc_indices, result_count = _critical_followup_order(
                obs, desc_indices, my_index, hand_counts,
            )

    if context == SelectContext.MAIN:
        o = select.option[desc_indices[0]]
        if o.type == OptionType.ABILITY:
            card = get_card(obs, o.area, o.index, my_index)
            if card is not None:
                if card.id == Dudunsparce:
                    ability_used_dudunsparce = True
                elif card.id == Fezandipiti_ex:
                    ability_used_fezandipiti = True

    return desc_indices[:result_count]
