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
Slowpoke_IDs = (162, 327)
Froakie_IDs = (33, 945)
Wellspring_Mask_Ogerpon_ex = 108
N_Darumaka = 257
Dreepy = 119
Drakloak = 120
Dragapult_ex = 121
Mist_Energy = 11
Rock_Fighting_Energy = 20
Great_Tusk = 58

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


def has_psychic_energy(pokemon: Pokemon | None) -> bool:
    return pokemon is not None and any(
        card.id in PSYCHIC_ENERGY_IDS for card in pokemon.energyCards
    )


def option_hand_card(obs: Observation, option, my_index: int) -> Card | None:
    if option.type not in (OptionType.PLAY, OptionType.ATTACH, OptionType.EVOLVE):
        return None
    return get_card(obs, AreaType.HAND, option.index, my_index)


def option_targets(option, area: AreaType, index: int) -> bool:
    return option.inPlayArea == area and option.inPlayIndex == index


def find_main_option(obs: Observation, predicate):
    if obs.select.context != SelectContext.MAIN:
        return None
    for index, option in enumerate(obs.select.option):
        if predicate(option):
            return index
    return None


def direct_active_alakazam_evolution(obs: Observation, my_index: int):
    return find_main_option(
        obs,
        lambda option: (
            option.type == OptionType.EVOLVE
            and option_targets(option, AreaType.ACTIVE, 0)
            and option_hand_card(obs, option, my_index) is not None
            and option_hand_card(obs, option, my_index).id == Alakazam
        ),
    )


def psychic_attach_option(
    obs: Observation,
    my_index: int,
    area: AreaType,
    index: int,
):
    return find_main_option(
        obs,
        lambda option: (
            option.type == OptionType.ATTACH
            and option_targets(option, area, index)
            and option_hand_card(obs, option, my_index) is not None
            and option_hand_card(obs, option, my_index).id in PSYCHIC_ENERGY_IDS
        ),
    )


def play_options_for_card(obs: Observation, my_index: int, card_id: int) -> list[int]:
    if obs.select.context != SelectContext.MAIN:
        return []
    result = []
    for index, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_hand_card(obs, option, my_index)
        if card is not None and card.id == card_id:
            result.append(index)
    return result


def attack_option(obs: Observation, attack_id: int):
    return find_main_option(
        obs,
        lambda option: option.type == OptionType.ATTACK and option.attackId == attack_id,
    )


def retreat_option(obs: Observation):
    return find_main_option(obs, lambda option: option.type == OptionType.RETREAT)


def alakazam_ko_certificate(
    obs: Observation,
    my_index: int,
    active_pokemon: Pokemon | None,
    target: Pokemon,
    hammer_count: int,
    boss_required: bool,
):
    """Certify only a presently legal, deterministic same-turn Powerful Hand route.

    Unknown Telepath Energy search cards and every optional draw are deliberately
    worth zero.  The calculation therefore uses a public lower bound on the hand
    that will remain after all required cards are spent.
    """
    if obs.select.context != SelectContext.MAIN or active_pokemon is None:
        return None

    state = obs.current
    my_state = state.players[my_index]
    if state.turn < 2:
        return None

    evolution_index = None
    evolution_hand_delta = 0
    if active_pokemon.id == Alakazam:
        pass
    elif active_pokemon.id == Kadabra:
        evolution_index = direct_active_alakazam_evolution(obs, my_index)
        if evolution_index is None or my_state.deckCount < 3:
            return None
        # Alakazam leaves hand and Psychic Draw adds three cards.
        evolution_hand_delta = 2
    else:
        return None

    attachment_index = None
    if not has_psychic_energy(active_pokemon):
        if state.energyAttached:
            return None
        attachment_index = psychic_attach_option(obs, my_index, AreaType.ACTIVE, 0)
        if attachment_index is None:
            return None

    hammer_options = play_options_for_card(obs, my_index, Enhanced_Hammer)
    if hammer_count > len(hammer_options):
        return None

    boss_options = play_options_for_card(obs, my_index, Boss_Orders)
    if boss_required:
        if state.supporterPlayed or not boss_options:
            return None

    current_hand = len(my_state.hand) if my_state.hand is not None else my_state.handCount
    remaining_hand = (
        current_hand
        + evolution_hand_delta
        - int(attachment_index is not None)
        - hammer_count
        - int(boss_required)
    )
    if remaining_hand <= 0 or remaining_hand * 20 < target.hp:
        return None

    # If Alakazam is already ready, verify that no current attack lock hides
    # Powerful Hand.  When evolution/attachment is the only missing step, the
    # engine will expose the attack after that legal action.
    if evolution_index is None and attachment_index is None:
        if attack_option(obs, ATTACK_POWERFUL_HAND) is None:
            return None

    if evolution_index is not None:
        next_kind, next_index = "evolve", evolution_index
    elif attachment_index is not None:
        next_kind, next_index = "attach", attachment_index
    elif hammer_count > 0:
        next_kind, next_index = "hammer", hammer_options[0]
    elif boss_required:
        next_kind, next_index = "boss", boss_options[0]
    else:
        next_kind, next_index = "attack", attack_option(obs, ATTACK_POWERFUL_HAND)

    return {
        "next_kind": next_kind,
        "next_index": next_index,
        "remaining_hand": remaining_hand,
        "hammer_count": hammer_count,
    }


def best_boss_alakazam_route(
    obs: Observation,
    my_index: int,
    active_pokemon: Pokemon | None,
    op_state,
    my_prize_count: int,
):
    candidates = []
    for bench_index, pokemon in enumerate(op_state.bench):
        if count_special_defense_energies(pokemon) > 0:
            continue
        route = alakazam_ko_certificate(
            obs,
            my_index,
            active_pokemon,
            pokemon,
            hammer_count=0,
            boss_required=True,
        )
        if route is None:
            continue
        prizes = prize_count(pokemon)
        wins_game = my_prize_count <= prizes
        candidates.append((wins_game, prizes, pokemon.hp, -bench_index, bench_index, route))
    if not candidates:
        return None
    wins_game, prizes, _, _, bench_index, route = max(
        candidates, key=lambda row: row[:4]
    )
    return {
        "bench_index": bench_index,
        "route": route,
        "wins_game": wins_game,
        "prizes": prizes,
    }


def ready_bench_kadabra_indices(my_state) -> list[int]:
    return [
        index
        for index, pokemon in enumerate(my_state.bench)
        if pokemon.id == Kadabra and has_psychic_energy(pokemon)
    ]


def protected_tusk_plan(
    obs: Observation,
    my_index: int,
    my_state,
    op_state,
    active_pokemon: Pokemon | None,
    my_prize_count: int,
):
    op_active = op_state.active[0] if op_state.active else None
    if (
        op_active is None
        or op_active.id != Great_Tusk
        or count_special_defense_energies(op_active) == 0
    ):
        return None

    select = obs.select
    context = select.context

    # Resolve a Hammer's mandatory energy choice without cross-call state.
    effect = getattr(select, "effect", None)
    if context == SelectContext.DISCARD_ENERGY and effect is not None and effect.id == Enhanced_Hammer:
        for option_index, option in enumerate(select.option):
            if (
                option.type == OptionType.ENERGY
                and option.playerIndex == 1 - my_index
                and option.area == AreaType.ACTIVE
                and option.index == 0
                and option.energyIndex is not None
                and option.energyIndex < len(op_active.energyCards)
                and op_active.energyCards[option.energyIndex].id in (Mist_Energy, Rock_Fighting_Energy)
            ):
                return {"kind": "hammer_energy", "option_index": option_index}
        return None

    # Boss target selection occurs while Great Tusk is still Active.
    if context == SelectContext.SWITCH and effect is not None and effect.id == Boss_Orders:
        if active_pokemon is None or active_pokemon.id != Alakazam or not has_psychic_energy(active_pokemon):
            return None
        hand_size = len(my_state.hand) if my_state.hand is not None else my_state.handCount
        candidates = []
        for option_index, option in enumerate(select.option):
            if option.type != OptionType.CARD or option.playerIndex != 1 - my_index:
                continue
            target = get_card(obs, option.area, option.index, option.playerIndex)
            if target is None or count_special_defense_energies(target) > 0:
                continue
            if hand_size * 20 < target.hp:
                continue
            prizes = prize_count(target)
            wins_game = my_prize_count <= prizes
            candidates.append((wins_game, prizes, target.hp, -option.index, option_index))
        if candidates:
            return {"kind": "boss_target", "option_index": max(candidates, key=lambda row: row[:4])[4]}
        return None

    ready_bench = ready_bench_kadabra_indices(my_state)

    # A retreat has no effect card and retains the old Active until this choice.
    if (
        context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE)
        and effect is None
        and active_pokemon is not None
        and ready_bench
    ):
        target_index = ready_bench[0]
        for option_index, option in enumerate(select.option):
            if (
                option.type == OptionType.CARD
                and option.playerIndex == my_index
                and option.area == AreaType.BENCH
                and option.index == target_index
            ):
                return {"kind": "retreat_target", "option_index": option_index}
        return None

    if context != SelectContext.MAIN or active_pokemon is None or obs.current.turn < 2:
        return None

    # 1. An already legal fixed-damage attack that wins the game.
    if my_prize_count <= prize_count(op_active):
        fixed_attacks = []
        if active_pokemon.id == Kadabra and has_psychic_energy(active_pokemon):
            fixed_attacks.append((ATTACK_SUPER_PSY_BOLT, 60))
        if active_pokemon.id == Abra and has_psychic_energy(active_pokemon):
            fixed_attacks.append((ATTACK_TELEPORTATION, 20))
        for attack_id, damage in fixed_attacks:
            option_index = attack_option(obs, attack_id)
            if option_index is not None and damage >= op_active.hp:
                return {"kind": "fixed_win", "option_index": option_index}

    # Compute both exact Alakazam lanes.  When they take the same prizes and do
    # not win the game, preserve the no-Supporter Active Hammer route.  This is
    # the explicit p0/2026071579 safety fixture.  A superior/winning Boss lane,
    # or any Boss lane when Hammer is unavailable, still has higher priority
    # than Kadabra bypass play.
    boss_route = best_boss_alakazam_route(
        obs, my_index, active_pokemon, op_state, my_prize_count
    )
    hammer_count = count_special_defense_energies(op_active)
    hammer_route = alakazam_ko_certificate(
        obs,
        my_index,
        active_pokemon,
        op_active,
        hammer_count=hammer_count,
        boss_required=False,
    )

    # 2. Boss a public unprotected target only when the entire KO is certified.
    if boss_route is not None and (
        hammer_route is None
        or boss_route["wins_game"]
        or boss_route["prizes"] > prize_count(op_active)
    ):
        return {"kind": "boss_ko", **boss_route}

    # 3. Remove every protecting Energy before the certified Powerful Hand KO.
    if hammer_route is not None:
        return {"kind": "hammer_ko", "route": hammer_route}

    # 4. Ready Active Kadabra attacks without being evolved away.
    if active_pokemon.id == Kadabra and has_psychic_energy(active_pokemon):
        bolt_index = attack_option(obs, ATTACK_SUPER_PSY_BOLT)
        if bolt_index is not None:
            return {"kind": "active_kadabra_ready", "option_index": bolt_index}

    # 5. The turn attachment belongs to an unready Active Kadabra first.
    if active_pokemon.id == Kadabra and not has_psychic_energy(active_pokemon):
        attach_index = psychic_attach_option(obs, my_index, AreaType.ACTIVE, 0)
        if attach_index is not None:
            return {"kind": "active_kadabra_attach", "option_index": attach_index}

    # 6. A ready Bench Kadabra is actionable only when RETREAT is legal now.
    retreat_index = retreat_option(obs)
    if ready_bench and retreat_index is not None:
        return {
            "kind": "retreat_ready_kadabra",
            "option_index": retreat_index,
            "bench_index": ready_bench[0],
        }

    # 7. No speculative reservation: attach a Bench Kadabra only when it can
    # immediately be promoted by the already-legal RETREAT and attack this turn.
    if retreat_index is not None:
        for bench_index, pokemon in enumerate(my_state.bench):
            if pokemon.id != Kadabra or has_psychic_energy(pokemon):
                continue
            attach_index = psychic_attach_option(obs, my_index, AreaType.BENCH, bench_index)
            if attach_index is not None:
                return {
                    "kind": "bench_kadabra_attack_setup",
                    "option_index": attach_index,
                    "bench_index": bench_index,
                }

    return None


def apply_protected_tusk_plan_score(
    obs: Observation,
    option_index: int,
    option,
    score: int,
    plan,
    my_index: int,
):
    if plan is None:
        return score

    kind = plan["kind"]
    if kind == "fixed_win":
        return 50000 if option_index == plan["option_index"] else score

    if kind in ("boss_ko", "hammer_ko"):
        route = plan["route"]
        if option_index != route["next_index"]:
            return score
        if route["next_kind"] in ("hammer", "boss"):
            return 49000
        # General parent PLAY/ABILITY/search options remain above this band.
        return max(score, 9900)

    if kind in ("hammer_energy", "boss_target", "retreat_target"):
        return 50000 if option_index == plan["option_index"] else score

    if kind in (
        "active_kadabra_ready",
        "active_kadabra_attach",
        "retreat_ready_kadabra",
        "bench_kadabra_attack_setup",
    ) and option_index == plan["option_index"]:
        score = max(score, 9900)

    # Preserve every Kadabra that is actionable in the current same-turn lane.
    protected_area = None
    protected_index = None
    if kind in ("active_kadabra_ready", "active_kadabra_attach"):
        protected_area, protected_index = AreaType.ACTIVE, 0
    elif kind in ("retreat_ready_kadabra", "bench_kadabra_attack_setup"):
        protected_area, protected_index = AreaType.BENCH, plan["bench_index"]

    if protected_area is not None and option.type == OptionType.EVOLVE:
        card = option_hand_card(obs, option, my_index)
        if (
            card is not None
            and card.id == Alakazam
            and option_targets(option, protected_area, protected_index)
        ):
            return -100000

    if kind == "retreat_ready_kadabra" and option.type == OptionType.ATTACK:
        if option.attackId == ATTACK_POWERFUL_HAND:
            return -100000

    return score


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

    bypass_plan = protected_tusk_plan(
        obs,
        my_index,
        my_state,
        op_state,
        active_pokemon,
        my_prize_count,
    )

    # ---- Score each option ----
    scores = []
    for option_index, o in enumerate(select.option):
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

        score = apply_protected_tusk_plan_score(
            obs,
            option_index,
            o,
            score,
            bypass_plan,
            my_index,
        )
        scores.append(score)

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
