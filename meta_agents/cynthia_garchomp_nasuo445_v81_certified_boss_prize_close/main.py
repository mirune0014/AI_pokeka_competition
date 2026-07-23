from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


try:
    ROOT = Path(__file__).resolve().parent
except NameError:
    ROOT = Path.cwd()

for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, SelectContext, all_attack, all_card_data, to_observation_class


ROSELIA = 341
ROSERADE = 342
GIBLE = 379
GABITE = 380
GARCHOMP_EX = 381
SPIRITOMB = 387

BASIC_FIGHTING = 6
ROCK_FIGHTING = 20
ENERGIES = {BASIC_FIGHTING, ROCK_FIGHTING}

BUDDY_POFFIN = 1086
UNFAIR_STAMP = 1080
NIGHT_STRETCHER = 1097
SACRED_ASH = 1129
FIGHTING_GONG = 1142
POKE_PAD = 1152
POWER_WEIGHT = 1173
BOSS = 1182
XEROSIC = 1197
SURFER = 1203
HILDA = 1225
LILLIE = 1227
FOREST = 1261

SPIKE_STING = 475
LEAF_STEP = 476
ROCK_HURL = 529
DRAGONSLICE = 530
CORKSCREW_DIVE = 531
DRACONIC_BUSTER = 532
RAGING_CURSE = 540

DEVELOPMENT_OPTION_TYPES = {
    OptionType.PLAY,
    OptionType.EVOLVE,
    OptionType.ATTACH,
    OptionType.ABILITY,
    OptionType.RETREAT,
}

CYNTHIA_BASICS = {ROSELIA, GIBLE, SPIRITOMB}
CYNTHIA_LINE = {ROSELIA, ROSERADE, GIBLE, GABITE, GARCHOMP_EX, SPIRITOMB}
MAIN_LINE = {GIBLE, GABITE, GARCHOMP_EX}
DRAW_ITEMS = {BUDDY_POFFIN, POKE_PAD, FIGHTING_GONG}
GABITE_WIDTH_SAFETY_IDS = {58, 344, 345, 741, 742, 743}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


def card_name(card_id: int | None) -> str:
    card = CARD_DB.get(card_id)
    return card.name if card else str(card_id or "")


def get_card(obs, area, index, player_index):
    if area is None or index is None or obs.current is None:
        return None
    player = obs.current.players[player_index]
    if area == AreaType.DECK and obs.select and obs.select.deck is not None:
        return obs.select.deck[index] if index < len(obs.select.deck) else None
    if area == AreaType.HAND and player.hand is not None:
        return player.hand[index] if index < len(player.hand) else None
    if area == AreaType.DISCARD:
        return player.discard[index] if index < len(player.discard) else None
    if area == AreaType.ACTIVE:
        return player.active[index] if index < len(player.active) else None
    if area == AreaType.BENCH:
        return player.bench[index] if index < len(player.bench) else None
    if area == AreaType.PRIZE:
        return player.prize[index] if index < len(player.prize) else None
    if area == AreaType.STADIUM:
        return obs.current.stadium[index] if index < len(obs.current.stadium) else None
    if area == AreaType.LOOKING and obs.current.looking is not None:
        return obs.current.looking[index] if index < len(obs.current.looking) else None
    return None


def option_card(obs, opt):
    player_index = opt.playerIndex if opt.playerIndex is not None else obs.current.yourIndex
    if opt.type == OptionType.PLAY:
        return get_card(obs, AreaType.HAND, opt.index, player_index)
    return get_card(obs, opt.area, opt.index, player_index)


def option_target(obs, opt):
    if opt.inPlayArea is None or opt.inPlayIndex is None:
        return None
    return get_card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)


def me(obs):
    return obs.current.players[obs.current.yourIndex]


def opponent(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    player = me(obs)
    return player.active[0] if player.active else None


def opponent_active(obs):
    player = opponent(obs)
    return player.active[0] if player.active else None


def my_pokemon(obs):
    player = me(obs)
    return [p for p in (player.active + player.bench) if p]


def opponent_pokemon(obs):
    player = opponent(obs)
    return [p for p in (player.active + player.bench) if p]


def gabite_width_safety_visible(obs) -> bool:
    return any(p.id in GABITE_WIDTH_SAFETY_IDS for p in opponent_pokemon(obs))


def hand_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).hand or []) if card]


def discard_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).discard or []) if card]


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def has_energy_id(pokemon, energy_id: int) -> bool:
    return any(getattr(energy, "id", energy) == energy_id for energy in energy_cards(pokemon))


def lacks_rock_energy(pokemon) -> bool:
    return not has_energy_id(pokemon, ROCK_FIGHTING)


def has_rock_hungry_main_line(obs) -> bool:
    return any(p.id in MAIN_LINE and lacks_rock_energy(p) for p in my_pokemon(obs))


def basic_energy_is_visible_or_in_hand(obs) -> bool:
    if BASIC_FIGHTING in hand_ids(obs):
        return True
    visible_deck = getattr(obs.select, "deck", None) or []
    if any(getattr(card, "id", None) == BASIC_FIGHTING for card in visible_deck if card):
        return True
    return any(
        getattr(option_card(obs, option), "id", None) == BASIC_FIGHTING
        for option in (getattr(obs.select, "option", None) or [])
    )


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    return int(getattr(pokemon, "maxHp", getattr(card, "hp", 0)) or 0)


def damage_on(pokemon) -> int:
    return max(0, max_hp(pokemon) - hp(pokemon))


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def deck_count(obs) -> int:
    return int(getattr(me(obs), "deckCount", 0) or 0)


def roserade_bonus(obs) -> int:
    return 30 * count_in_play(obs, ROSERADE)


def ready_garchomp(obs) -> bool:
    return any(p.id == GARCHOMP_EX and energy_count(p) >= 2 for p in my_pokemon(obs))


def has_main_line(obs) -> bool:
    return any(p.id in MAIN_LINE for p in my_pokemon(obs))


def active_is_main_attacker(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id in {GARCHOMP_EX, ROSERADE, SPIRITOMB})


def opponent_has_no_bench(obs) -> bool:
    return not (getattr(opponent(obs), "bench", None) or [])


def has_energized_bench_main_line(obs) -> bool:
    return any(
        pokemon.id in MAIN_LINE and energy_count(pokemon) >= 1
        for pokemon in (getattr(me(obs), "bench", None) or [])
        if pokemon
    )


def is_approved_buster_conversion(obs) -> bool:
    """Allow Buster only for visible, decisive KOs that preserve Corkscrew's role."""
    target = opponent_active(obs)
    if not target:
        return False
    buster_ko = best_damage_for_active(obs, DRACONIC_BUSTER) >= hp(target)
    corkscrew_ko = best_damage_for_active(obs, CORKSCREW_DIVE) >= hp(target)
    remaining_prizes = len(getattr(me(obs), "prize", []) or [])
    return bool(
        buster_ko
        and not corkscrew_ko
        and (
            prize_value(target) >= remaining_prizes
            or opponent_has_no_bench(obs)
            or prize_value(target) >= 2
            or has_energized_bench_main_line(obs)
        )
    )


def has_legal_approved_buster(obs) -> bool:
    return bool(
        is_approved_buster_conversion(obs)
        and any(
            option.type == OptionType.ATTACK and option.attackId == DRACONIC_BUSTER
            for option in (getattr(obs.select, "option", None) or [])
        )
    )


def spiritomb_damage(obs) -> int:
    return sum(damage_on(p) for p in (me(obs).bench or []) if p and p.id in CYNTHIA_LINE)


def best_damage_for_active(obs, attack_id: int | None = None) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    bonus = roserade_bonus(obs)
    if attack_id == DRACONIC_BUSTER or (
        attack_id is None and active.id == GARCHOMP_EX and energy_count(active) >= 2
    ):
        return 260 + bonus
    if attack_id == CORKSCREW_DIVE or active.id == GARCHOMP_EX:
        return 100 + bonus
    if attack_id == LEAF_STEP or active.id == ROSERADE:
        return 80 + bonus
    if attack_id == RAGING_CURSE or active.id == SPIRITOMB:
        return spiritomb_damage(obs) + bonus
    if attack_id == DRAGONSLICE or active.id == GABITE:
        return 40 + bonus
    if attack_id == ROCK_HURL or active.id == GIBLE:
        return 20 + bonus
    if attack_id == SPIKE_STING or active.id == ROSELIA:
        return 20 + bonus
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2600, "go first to evolve") if opt.type == OptionType.YES else (1300, "second acceptable")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {GIBLE: 9800, ROSELIA: 6600, SPIRITOMB: 4200}
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == GIBLE:
            return 9000 - count_in_play(obs, GIBLE) * 700, "setup bench Gible"
        if cid == ROSELIA:
            return 6500 if count_in_play(obs, ROSELIA) < 2 else 1400, "setup bench Roselia"
        if cid == SPIRITOMB:
            return 3800 if count_in_play(obs, SPIRITOMB) < 1 else 700, "setup bench Spiritomb"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = deck_count(obs)
    if cid == GIBLE:
        return 8500 if count_in_play(obs, GIBLE) < 3 else 1000, "bench Gible"
    if cid == ROSELIA:
        return 6400 if count_in_play(obs, ROSELIA) < 2 else 1200, "bench Roselia"
    if cid == SPIRITOMB:
        return 3600 if count_in_play(obs, SPIRITOMB) < 1 else 700, "bench Spiritomb"
    if cid == BUDDY_POFFIN:
        return -800 if deck <= 8 else (8600 if count_in_play(obs, GIBLE) < 2 else 4200), "Buddy Poffin basics"
    if cid == FIGHTING_GONG:
        return -700 if deck <= 8 else (9000 if not has_main_line(obs) else 3600), "Fighting Gong"
    if cid == POKE_PAD:
        return -700 if deck <= 9 else 3100, "Poke Pad"
    if cid == LILLIE:
        return -700 if deck <= 9 else (6000 if len(hand_ids(obs)) <= 5 else 1800), "Lillie"
    if cid == HILDA:
        return -600 if deck <= 8 else 5400, "Hilda"
    if cid == BOSS:
        if not active_is_main_attacker(obs):
            return -400, "save Boss until attacker ready"
        target = best_boss_target(obs)
        if target and best_damage_for_active(obs) >= hp(target):
            return 19000, "Boss for KO"
        return 3600, "Boss pressure"
    if cid == XEROSIC:
        return 5200 if opponent(obs).handCount >= 8 else 900, "Xerosic"
    if cid == SURFER:
        if ready_garchomp(obs) and active_pokemon(obs) and active_pokemon(obs).id != GARCHOMP_EX:
            return 13000, "Surfer to Garchomp"
        return 2600 if len(hand_ids(obs)) <= 4 else 900, "Surfer"
    if cid == UNFAIR_STAMP:
        return 5200 if len(getattr(opponent(obs), "prize", []) or []) <= 4 else 800, "Unfair Stamp"
    if cid == NIGHT_STRETCHER:
        return 4600 if any(x in MAIN_LINE for x in discard_ids(obs)) else 900, "Night Stretcher"
    if cid == SACRED_ASH:
        return 3600 if sum(1 for x in discard_ids(obs) if x in CYNTHIA_LINE) >= 3 else 500, "Sacred Ash"
    if cid == FOREST:
        return 4200 if has_in_play(obs, ROSELIA) and not has_in_play(obs, ROSERADE) else 900, "Forest"
    if cid == POWER_WEIGHT:
        return 1200, "Power Weight handled as attach"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == GABITE and tid == GIBLE:
        return 19000 + energy_count(target) * 1200, "evolve Gabite"
    if cid == GARCHOMP_EX and tid == GABITE:
        return 25000 + energy_count(target) * 1800, "evolve Garchomp ex"
    if cid == ROSERADE and tid == ROSELIA:
        return 18000 + count_in_play(obs, GARCHOMP_EX) * 2000, "evolve Roserade support"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == POWER_WEIGHT:
        if tid == GARCHOMP_EX and not getattr(target, "tools", None):
            return 12500, "Power Weight Garchomp"
        if tid in {GABITE, GIBLE} and not getattr(target, "tools", None):
            return 7200, "Power Weight main line"
        return 800, "Power Weight"
    if cid not in ENERGIES:
        return 100, "attach"
    active = active_pokemon(obs)
    active_garchomp_unready = (
        active
        and active.id == GARCHOMP_EX
        and energy_count(active) < 2
    )
    active_garchomp_ready = (
        active
        and active.id == GARCHOMP_EX
        and energy_count(active) >= 2
    )
    rock_bonus = 180 if cid == ROCK_FIGHTING and tid in MAIN_LINE and lacks_rock_energy(target) else 0
    if active_garchomp_unready and opt.inPlayArea == AreaType.ACTIVE and tid == GARCHOMP_EX:
        return 12300 + max(0, 2 - energy_count(target)) * 1200 + rock_bonus, "ready active Garchomp"
    if active_garchomp_ready and opt.inPlayArea == AreaType.BENCH:
        if tid == GARCHOMP_EX and energy_count(target) < 2:
            return 14200 + rock_bonus, "preload bench Garchomp"
        if tid == GABITE and energy_count(target) < 2:
            return 12600 + rock_bonus, "preload bench Gabite"
        if tid == GIBLE and energy_count(target) < 2:
            return 11800 + rock_bonus, "preload bench Gible"
    if tid == GARCHOMP_EX:
        return 9800 + max(0, 2 - energy_count(target)) * 1200 + rock_bonus, "attach to Garchomp"
    if tid == GABITE:
        return 7800 + max(0, 2 - energy_count(target)) * 900 + rock_bonus, "preload Gabite"
    if tid == GIBLE:
        return 7200 + max(0, 2 - energy_count(target)) * 800 + rock_bonus, "preload Gible"
    if tid == ROSERADE:
        return 4200 + max(0, 1 - energy_count(target)) * 600, "attach Roserade"
    if tid == ROSELIA:
        return 3000, "preload Roselia"
    if tid == SPIRITOMB:
        return 2600, "attach Spiritomb"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id == GARCHOMP_EX and energy_count(active) >= 1:
        return -2500, "keep Garchomp active"
    if ready_garchomp(obs):
        return 12500, "retreat to Garchomp"
    if active and active.id not in {GABITE, GARCHOMP_EX} and any(
        p.id == GABITE and energy_count(p) >= 1 for p in my_pokemon(obs)
    ):
        return 7200, "retreat to Gabite"
    return 600, "retreat"


def best_boss_target(obs):
    bench = [p for p in (opponent(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    damage = best_damage_for_active(obs)
    cid = getattr(target, "id", None)
    if damage >= hp(target):
        return 36000 + prize_value(target) * 6000 - hp(target), f"Boss KO {card_name(cid)}"
    setup_bonus = 6500 if cid in {646, 647, 648, 169, 190, 741, 742, 743, 58, 344, 345} else 0
    return 4000 + setup_bonus + prize_value(target) * 1200 + energy_count(target) * 500 - hp(target), "Boss pressure"


def attack_score(obs, attack_id: int | None) -> tuple[int, str]:
    target = opponent_active(obs)
    damage = best_damage_for_active(obs, attack_id)
    if attack_id == DRACONIC_BUSTER:
        if not is_approved_buster_conversion(obs):
            corkscrew_score = 15000 if len(hand_ids(obs)) <= 4 else 9800
            return corkscrew_score - 1, "Draconic Buster rejected conversion"
        score, reason = 18500, "Draconic Buster"
    elif attack_id == CORKSCREW_DIVE:
        score, reason = (15000, "Corkscrew Dive draw") if len(hand_ids(obs)) <= 4 else (9800, "Corkscrew Dive")
    elif attack_id == LEAF_STEP:
        score, reason = 7600, "Leaf Step"
    elif attack_id == RAGING_CURSE:
        score, reason = 6200 + damage, "Raging Curse"
    else:
        score, reason = 5200 + damage, "attack"
    if target and damage >= hp(target):
        score += 14500 + prize_value(target) * 5200
        reason += " KO"
    return score, reason


def is_immediate_corkscrew_ko(obs, opt) -> bool:
    """True only when Corkscrew Dive visibly KOs the opposing active."""
    target = opponent_active(obs)
    return bool(
        opt.type == OptionType.ATTACK
        and opt.attackId == CORKSCREW_DIVE
        and target
        and best_damage_for_active(obs, CORKSCREW_DIVE) >= hp(target)
    )


def is_game_winning_corkscrew(obs, opt) -> bool:
    """True only when Corkscrew Dive visibly takes all remaining prizes."""
    target = opponent_active(obs)
    remaining_prizes = len(getattr(me(obs), "prize", []) or [])
    return bool(
        is_immediate_corkscrew_ko(obs, opt)
        and prize_value(target) >= remaining_prizes
    )


def corkscrew_development_index(obs, scored: list[tuple[int, int, str]]) -> int | None:
    """Find the best positive voluntary development action before Corkscrew."""
    if (
        obs.select.context != SelectContext.MAIN
        or getattr(active_pokemon(obs), "id", None) != GARCHOMP_EX
        or not has_in_play(obs, ROSERADE)
    ):
        return None
    corkscrew_options = [
        opt for opt in obs.select.option
        if opt.type == OptionType.ATTACK and opt.attackId == CORKSCREW_DIVE
    ]
    if not corkscrew_options or any(is_game_winning_corkscrew(obs, opt) for opt in corkscrew_options):
        return None
    development = [
        (score, index) for score, index, _reason in scored
        if score > 0 and obs.select.option[index].type in DEVELOPMENT_OPTION_TYPES
    ]
    return max(development, key=lambda row: (row[0], -row[1]))[1] if development else None


def discard_score(obs, cid: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if cid in MAIN_LINE and not ready_garchomp(obs):
        return -7000, f"keep setup {card_name(cid)}"
    if cid in {ROSELIA, ROSERADE} and count_in_play(obs, ROSERADE) < 1:
        return -4200, f"keep Roserade line {card_name(cid)}"
    if cid in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -2400, "keep early energy"
    if cid == BOSS:
        return -1300, "keep Boss"
    if cid is not None and hand.count(cid) >= 2:
        return 2800, f"discard duplicate {card_name(cid)}"
    return 300, f"discard {card_name(cid)}"


def score_to_hand(obs, opt, allow_support_pivot: bool = False) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    main_line_count = sum(1 for pokemon in my_pokemon(obs) if pokemon.id in MAIN_LINE)
    if cid == GARCHOMP_EX:
        return 15000 if has_in_play(obs, GABITE) else 6500, "take Garchomp ex"
    if cid == GABITE:
        if (
            has_in_play(obs, GIBLE)
            and count_in_play(obs, GABITE) < 3
            and not gabite_width_safety_visible(obs)
        ):
            return 16000, "take Gabite to widen Gible line"
        return 13500 if has_in_play(obs, GIBLE) else 4200, "take Gabite"
    if cid == GIBLE:
        return 12500 if count_in_play(obs, GIBLE) < 2 else 4200, "take Gible"
    if cid == ROSERADE:
        if allow_support_pivot and main_line_count >= 2 and has_in_play(obs, ROSELIA):
            return 13000, "take Roserade support pivot"
        return 9000 if has_in_play(obs, ROSELIA) else 3300, "take Roserade"
    if cid == ROSELIA:
        if allow_support_pivot and main_line_count >= 2 and count_in_play(obs, ROSELIA) < 2:
            return 13000, "take Roselia support pivot"
        return 6500 if count_in_play(obs, ROSELIA) < 2 else 1200, "take Roselia"
    if cid == SPIRITOMB:
        return 3400 if count_in_play(obs, SPIRITOMB) < 1 else 700, "take Spiritomb"
    if cid in ENERGIES:
        if (
            cid == ROCK_FIGHTING
            and has_rock_hungry_main_line(obs)
            and basic_energy_is_visible_or_in_hand(obs)
        ):
            return 6380, "take Rock for main line"
        return 6200, "take energy"
    if cid == POWER_WEIGHT:
        return 5200 if has_in_play(obs, GARCHOMP_EX) or has_in_play(obs, GABITE) else 1500, "take Power Weight"
    if cid == BOSS:
        return 5200 if active_is_main_attacker(obs) else 1700, "take Boss"
    if cid in {BUDDY_POFFIN, FIGHTING_GONG, POKE_PAD, LILLIE, HILDA, NIGHT_STRETCHER, SURFER, UNFAIR_STAMP}:
        return 3200, f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context
    if ctx == SelectContext.TO_BENCH:
        if cid == GIBLE:
            return (9000 - count_in_play(obs, GIBLE) * 700) if count_in_play(obs, GIBLE) < 3 else 1000, "bench Gible"
        if cid == ROSELIA:
            return 6500 if count_in_play(obs, ROSELIA) < 2 else 1200, "bench Roselia"
        if cid == SPIRITOMB:
            return 3800 if count_in_play(obs, SPIRITOMB) < 1 else 700, "bench Spiritomb"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi and card:
            return boss_target_score(obs, card)
        if cid == GARCHOMP_EX:
            return 13000 + energy_count(card) * 900 - damage_on(card), "promote Garchomp"
        if cid in {GABITE, GIBLE, ROSERADE, ROSELIA, SPIRITOMB}:
            return 3500 + energy_count(card) * 400 - damage_on(card), "promote backup"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == GARCHOMP_EX:
            return 10500, "effect to Garchomp"
        if cid == GABITE:
            return 8200, "effect to Gabite"
        if cid == GIBLE:
            return 7600, "effect to Gible"
        if cid in {ROSERADE, ROSELIA}:
            return 4200, "effect to Roserade line"
    if ctx == SelectContext.HEAL:
        return damage_on(card), "heal"
    if ctx == SelectContext.DAMAGE:
        if best_damage_for_active(obs) >= hp(card):
            return 22000 + prize_value(card) * 4000, "damage KO"
        return 3000 + prize_value(card) * 700 + energy_count(card) * 400 - hp(card), "damage"
    return 1000, f"target {card_name(cid)}"


def champions_call_score(obs) -> int | None:
    """Return the normal score of a currently legal Champion's Call option."""
    for option in obs.select.option:
        if option.type == OptionType.ABILITY and getattr(option_card(obs, option), "id", None) == GABITE:
            return score_option(obs, option)[0]
    return None


def matching_champions_call_evolve_score(obs, opt) -> int | None:
    """Preserve the established priority for a Call on the Gabite being evolved."""
    if opt.type != OptionType.ABILITY:
        return None
    gabite = option_card(obs, opt)
    if getattr(gabite, "id", None) != GABITE:
        return None
    gabite_serial = getattr(gabite, "serial", None)
    if gabite_serial is None:
        return None
    for evolve in obs.select.option:
        if evolve.type != OptionType.EVOLVE:
            continue
        evolution = option_card(obs, evolve)
        target = option_target(obs, evolve)
        if (
            getattr(evolution, "id", None) == GARCHOMP_EX
            and getattr(target, "id", None) == GABITE
            and getattr(target, "serial", None) == gabite_serial
        ):
            return score_evolve(obs, evolve)[0] + 1
    return None


def is_garchomp_ex_on_gabite_evolution(obs, opt) -> bool:
    return (
        opt.type == OptionType.EVOLVE
        and getattr(option_card(obs, opt), "id", None) == GARCHOMP_EX
        and getattr(option_target(obs, opt), "id", None) == GABITE
    )


def score_option(obs, opt) -> tuple[int, str]:
    ctx = obs.select.context
    if ctx in {SelectContext.IS_FIRST, SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return setup_score(obs, opt)
    if opt.type == OptionType.PLAY:
        return score_play(obs, opt)
    if opt.type == OptionType.EVOLVE:
        return score_evolve(obs, opt)
    if opt.type == OptionType.ATTACH:
        return score_attach(obs, opt)
    if opt.type == OptionType.RETREAT:
        return score_retreat(obs, opt)
    if opt.type == OptionType.ATTACK:
        return attack_score(obs, opt.attackId)
    if opt.type == OptionType.ABILITY:
        card = option_card(obs, opt)
        return (9500, "Champion's Call") if getattr(card, "id", None) == GABITE else (2600, "ability")
    if opt.type == OptionType.DISCARD:
        return discard_score(obs, getattr(option_card(obs, opt), "id", None))
    if opt.type == OptionType.CARD:
        if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
            return discard_score(obs, getattr(option_card(obs, opt), "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt, allow_support_pivot=ctx == SelectContext.TO_HAND)
        return score_target(obs, opt)
    if opt.type in {OptionType.YES, OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1000, "yes/card"
    if opt.type == OptionType.NO:
        return 100, "no"
    if opt.type == OptionType.END:
        return 0, "end"
    if opt.type == OptionType.NUMBER:
        return int(getattr(opt, "number", 0) or 0) * 100, "number"
    return 100, "fallback"


def score_option_with_champions_call_order(obs, opt) -> tuple[int, str]:
    """Keep legal Call ahead of Garchomp ex evolutions without raising Call globally."""
    score, reason = score_option(obs, opt)
    call_score = champions_call_score(obs)
    if call_score is not None and is_garchomp_ex_on_gabite_evolution(obs, opt):
        return min(score, call_score - 1), "Garchomp ex evolution after Champion's Call"
    return score, reason


def champions_call_route_index(obs) -> int | None:
    """Return the first legal option for the next incomplete Champion's Call role."""
    if (
        obs.select.context != SelectContext.TO_HAND
        or getattr(obs.select.effect, "id", None) != GABITE
        or obs.select.maxCount != 1
    ):
        return None

    player = me(obs)
    if player.hand is None:
        return None

    hand = {card.id for card in player.hand if card}
    in_play = {pokemon.id for pokemon in my_pokemon(obs)}
    legal_indices: dict[int, int] = {}
    for index, option in enumerate(obs.select.option):
        card_id = getattr(option_card(obs, option), "id", None)
        if card_id not in legal_indices:
            legal_indices[card_id] = index

    garchomp_secured = GARCHOMP_EX in hand or GARCHOMP_EX in in_play
    if not garchomp_secured:
        return legal_indices.get(GARCHOMP_EX)

    main_line_count = sum(1 for pokemon in my_pokemon(obs) if pokemon.id in MAIN_LINE)
    if main_line_count < 2:
        return None

    bench_is_open = len(player.bench) < player.benchMax
    roselia_in_hand = ROSELIA in hand
    roselia_in_play = ROSELIA in in_play
    roserade_in_hand = ROSERADE in hand
    roserade_in_play = ROSERADE in in_play

    if (
        not roselia_in_hand
        and not roselia_in_play
        and not roserade_in_play
        and bench_is_open
    ):
        roselia_index = legal_indices.get(ROSELIA)
        if roselia_index is not None:
            return roselia_index

    if (
        not roserade_in_hand
        and not roserade_in_play
        and (roselia_in_hand or roselia_in_play)
        and (roselia_in_play or bench_is_open)
    ):
        return legal_indices.get(ROSERADE)

    return None


def first_garchomp_route_missing_role(obs) -> int | None:
    """Return the next missing card in one fully visible Garchomp route."""
    in_play = {pokemon.id for pokemon in my_pokemon(obs)}
    hand = set(hand_ids(obs))
    if GARCHOMP_EX in in_play:
        return None
    if GARCHOMP_EX in hand and (
        GABITE in in_play or (GABITE in hand and GIBLE in in_play)
    ):
        return None
    if GABITE in in_play:
        return GARCHOMP_EX
    if GIBLE in in_play:
        return GABITE if GABITE not in hand else GARCHOMP_EX
    return GIBLE


def role_complete_deficit(obs) -> tuple[int, int] | None:
    """Return the earliest incomplete role and the card that advances it."""
    missing_route_role = first_garchomp_route_missing_role(obs)
    if missing_route_role is not None:
        return 1, missing_route_role
    if not has_in_play(obs, ROSERADE):
        return 2, ROSERADE if has_in_play(obs, ROSELIA) else ROSELIA
    main_line_count = sum(1 for pokemon in my_pokemon(obs) if pokemon.id in MAIN_LINE)
    if main_line_count < 2:
        return 3, GIBLE
    if (
        getattr(active_pokemon(obs), "id", None) == GARCHOMP_EX
        and not has_energized_bench_main_line(obs)
    ):
        return 4, BASIC_FIGHTING
    return None


def ordinary_attack_continuation_id(obs) -> int | None:
    """Infer whether a nested role search continues a paid non-KO attack turn."""
    active = active_pokemon(obs)
    attack_id = {
        GIBLE: ROCK_HURL,
        GABITE: DRAGONSLICE,
        GARCHOMP_EX: CORKSCREW_DIVE,
    }.get(getattr(active, "id", None))
    target = opponent_active(obs)
    player = me(obs)
    if (
        attack_id is None
        or target is None
        or energy_count(active) < 1
        or getattr(player, "asleep", False)
        or getattr(player, "paralyzed", False)
        or best_damage_for_active(obs, attack_id) >= hp(target)
        or (energy_count(active) >= 2 and is_approved_buster_conversion(obs))
    ):
        return None
    return attack_id


def role_complete_nested_index(obs, deficit: int, role_id: int) -> int | None:
    """Keep an eligible search resolution on the transaction's earliest role."""
    if obs.current.turn == 1:
        return None
    if ordinary_attack_continuation_id(obs) is None:
        return None
    if getattr(obs.select, "minCount", 0) > 1:
        return None

    effect_id = getattr(getattr(obs.select, "effect", None), "id", None)
    context = obs.select.context
    target_id = None
    required_area = None
    if effect_id == BUDDY_POFFIN and context == SelectContext.TO_BENCH:
        if role_id in {GIBLE, ROSELIA}:
            target_id, required_area = role_id, AreaType.DECK
    elif effect_id == FIGHTING_GONG and context == SelectContext.TO_HAND:
        if role_id == GIBLE or deficit == 4:
            target_id, required_area = role_id, AreaType.DECK
    elif effect_id == POKE_PAD and context == SelectContext.TO_HAND:
        if role_id in {GIBLE, GABITE, ROSELIA, ROSERADE}:
            target_id, required_area = role_id, AreaType.DECK
    elif effect_id == NIGHT_STRETCHER and context == SelectContext.TO_HAND:
        target_id, required_area = role_id, AreaType.DISCARD
    elif effect_id == GABITE and context == SelectContext.TO_HAND and deficit <= 3:
        target_id, required_area = role_id, AreaType.DECK
    if target_id is None:
        return None

    eligible = []
    for index, option in enumerate(obs.select.option):
        if (
            option.type == OptionType.CARD
            and option.area == required_area
            and getattr(option_card(obs, option), "id", None) == target_id
        ):
            score = score_option_with_champions_call_order(obs, option)[0]
            eligible.append((score, index))
    return max(eligible, key=lambda row: (row[0], -row[1]))[1] if eligible else None


def forest_enables_roserade_this_turn(obs) -> bool:
    """True only when Forest opens a visible same-turn Roserade evolution."""
    if ROSERADE not in hand_ids(obs):
        return False
    player = me(obs)
    if any(
        pokemon.id == ROSELIA and getattr(pokemon, "appearThisTurn", False) is True
        for pokemon in my_pokemon(obs)
    ):
        return True
    bench_is_open = len(getattr(player, "bench", None) or []) < player.benchMax
    return bool(
        bench_is_open
        and any(
            option.type == OptionType.PLAY
            and getattr(option_card(obs, option), "id", None) == ROSELIA
            for option in obs.select.option
        )
    )


def complete_role_cycle_selection(
    obs,
    scored: list[tuple[int, int, str]],
    forced_index: int,
) -> list[int]:
    ranked = sorted(scored, key=lambda row: (row[0], -row[1]), reverse=True)
    selected = [forced_index]
    for score, index, _reason in ranked:
        if len(selected) >= obs.select.maxCount:
            break
        if index in selected:
            continue
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(index)
    if len(selected) < obs.select.minCount:
        for _score, index, _reason in ranked:
            if len(selected) >= obs.select.minCount:
                break
            if index not in selected:
                selected.append(index)
    return selected


def role_complete_attack_cycle_index(
    obs,
    scored: list[tuple[int, int, str]],
) -> list[int] | None:
    """Advance exactly the earliest missing core role before an ordinary attack."""
    if not scored:
        return None
    deficit = role_complete_deficit(obs)
    if deficit is None:
        return None
    deficit_number, role_id = deficit

    if obs.select.context != SelectContext.MAIN:
        forced_index = role_complete_nested_index(obs, deficit_number, role_id)
        if forced_index is None:
            return None
        return complete_role_cycle_selection(obs, scored, forced_index)

    options = obs.select.option
    _top_score, top_index, _top_reason = max(scored, key=lambda row: (row[0], -row[1]))
    top_option = options[top_index]
    if (
        top_option.type != OptionType.ATTACK
        or top_option.attackId not in {ROCK_HURL, DRAGONSLICE, CORKSCREW_DIVE}
    ):
        return None
    target = opponent_active(obs)
    if target is None or best_damage_for_active(obs, top_option.attackId) >= hp(target):
        return None
    if has_legal_approved_buster(obs):
        return None
    if any(
        option.type == OptionType.ATTACK and option.attackId == RAGING_CURSE
        for option in options
    ):
        return None
    if crustle_spiritomb_counter_index(obs) is not None:
        return None

    hand = set(hand_ids(obs))
    discard = set(discard_ids(obs))
    player = me(obs)
    bench_is_open = len(getattr(player, "bench", None) or []) < player.benchMax
    score_by_index = {index: score for score, index, _reason in scored}
    eligible = []
    for index, option in enumerate(options):
        card_id = getattr(option_card(obs, option), "id", None)
        target_id = getattr(option_target(obs, option), "id", None)
        advances = False

        if option.type == OptionType.PLAY:
            if deficit_number == 1:
                advances = (
                    (card_id == GIBLE and role_id == GIBLE)
                    or (
                        card_id == BUDDY_POFFIN
                        and role_id == GIBLE
                        and bench_is_open
                    )
                    or (
                        card_id == FIGHTING_GONG
                        and role_id == GIBLE
                        and GIBLE not in hand
                    )
                    or (
                        card_id == POKE_PAD
                        and role_id in {GIBLE, GABITE}
                        and role_id not in hand
                    )
                    or (
                        card_id == NIGHT_STRETCHER
                        and role_id in discard
                        and role_id not in hand
                    )
                )
            elif deficit_number == 2:
                advances = (
                    (card_id == ROSELIA and role_id == ROSELIA)
                    or (
                        card_id == BUDDY_POFFIN
                        and role_id == ROSELIA
                        and bench_is_open
                    )
                    or (
                        card_id == POKE_PAD
                        and role_id in {ROSELIA, ROSERADE}
                        and role_id not in hand
                    )
                    or (
                        card_id == NIGHT_STRETCHER
                        and role_id in discard
                        and role_id not in hand
                    )
                    or (card_id == FOREST and forest_enables_roserade_this_turn(obs))
                )
            elif deficit_number == 3:
                advances = (
                    card_id == GIBLE
                    or (card_id == BUDDY_POFFIN and bench_is_open)
                    or (card_id in {FIGHTING_GONG, POKE_PAD} and GIBLE not in hand)
                    or (
                        card_id == NIGHT_STRETCHER
                        and GIBLE in discard
                        and GIBLE not in hand
                    )
                )
            elif deficit_number == 4:
                advances = (
                    (card_id == FIGHTING_GONG and not hand.intersection(ENERGIES))
                    or (
                        card_id == NIGHT_STRETCHER
                        and BASIC_FIGHTING in discard
                        and not hand.intersection(ENERGIES)
                    )
                )
            if card_id in {BUDDY_POFFIN, FIGHTING_GONG, POKE_PAD}:
                advances = advances and score_by_index[index] > 0

        elif option.type == OptionType.EVOLVE:
            advances = (
                deficit_number == 1
                and (
                    (card_id == GABITE and target_id == GIBLE)
                    or (card_id == GARCHOMP_EX and target_id == GABITE)
                )
            ) or (
                deficit_number == 2
                and card_id == ROSERADE
                and target_id == ROSELIA
            )
        elif option.type == OptionType.ABILITY:
            advances = (
                deficit_number <= 3
                and card_id == GABITE
                and role_id not in hand
            )
        elif option.type == OptionType.ATTACH:
            advances = (
                deficit_number == 4
                and option.inPlayArea == AreaType.BENCH
                and card_id in ENERGIES
                and target_id in MAIN_LINE
            )

        if advances:
            eligible.append((score_by_index[index], index))
    if not eligible:
        return None
    forced_index = max(eligible, key=lambda row: (row[0], -row[1]))[1]
    return complete_role_cycle_selection(obs, scored, forced_index)


def core_bridge_before_chip_index(obs, scored: list[tuple[int, int, str]]) -> int | None:
    """Return the best positive core bridge before a non-KO Gible-line chip."""
    if not scored:
        return None

    options = obs.select.option
    _top_score, top_index, _top_reason = max(scored, key=lambda row: (row[0], -row[1]))
    top_option = options[top_index]
    active_id = getattr(active_pokemon(obs), "id", None)
    expected_attack = {GIBLE: ROCK_HURL, GABITE: DRAGONSLICE}.get(active_id)
    if expected_attack is None or top_option.type != OptionType.ATTACK or top_option.attackId != expected_attack:
        return None

    target = opponent_active(obs)
    if target is None or best_damage_for_active(obs, top_option.attackId) >= hp(target):
        return None

    main_line_count = sum(1 for pokemon in my_pokemon(obs) if pokemon.id in MAIN_LINE)
    if has_in_play(obs, GARCHOMP_EX) and has_in_play(obs, ROSERADE) and main_line_count >= 2:
        return None

    bridge_ids = {GIBLE, ROSELIA, BUDDY_POFFIN, FIGHTING_GONG, POKE_PAD, FOREST}
    eligible = [
        (score, index)
        for score, index, _reason in scored
        if score > 0
        and options[index].type == OptionType.PLAY
        and getattr(option_card(obs, options[index]), "id", None) in bridge_ids
    ]
    return max(eligible, key=lambda row: (row[0], -row[1]))[1] if eligible else None


def prebuster_backup_attach_index(obs) -> int | None:
    """Return the best legal bench-main Energy attachment before approved Buster."""
    active = active_pokemon(obs)
    if (
        obs.select.context != SelectContext.MAIN
        or getattr(active, "id", None) != GARCHOMP_EX
        or energy_count(active) < 2
        or not has_in_play(obs, ROSERADE)
        or has_energized_bench_main_line(obs)
        or not any(
            option.type == OptionType.ATTACK and option.attackId == DRACONIC_BUSTER
            for option in obs.select.option
        )
        or not is_approved_buster_conversion(obs)
    ):
        return None

    eligible = []
    for index, option in enumerate(obs.select.option):
        if option.type != OptionType.ATTACH or option.inPlayArea != AreaType.BENCH:
            continue
        attached_card = option_card(obs, option)
        target = option_target(obs, option)
        if getattr(attached_card, "id", None) in ENERGIES and getattr(target, "id", None) in MAIN_LINE:
            eligible.append((score_attach(obs, option)[0], index))
    return max(eligible, key=lambda row: (row[0], -row[1]))[1] if eligible else None


def crustle_spiritomb_counter_index(obs) -> int | None:
    """Return the next legal step of the same-turn lethal Crustle counter."""
    options = getattr(obs.select, "option", None) or []
    context = obs.select.context
    active = active_pokemon(obs)
    target = opponent_active(obs)

    if (
        context == SelectContext.MAIN
        and getattr(obs.current, "retreated", None) is True
        and getattr(active, "id", None) == SPIRITOMB
        and energy_count(active) >= 1
        and getattr(target, "id", None) == 345
        and any(
            pokemon.id == GARCHOMP_EX and damage_on(pokemon) > 0
            for pokemon in (getattr(me(obs), "bench", None) or [])
            if pokemon
        )
        and best_damage_for_active(obs, RAGING_CURSE) >= hp(target)
    ):
        for index, option in enumerate(options):
            if option.type == OptionType.ATTACK and option.attackId == RAGING_CURSE:
                return index
        return None

    if context == SelectContext.SWITCH:
        if (
            getattr(obs.current, "retreated", None) is not True
            or getattr(active, "id", None) != GARCHOMP_EX
            or damage_on(active) <= 0
            or getattr(target, "id", None) != 345
        ):
            return None
        for index, option in enumerate(options):
            spiritomb = option_card(obs, option)
            projected_damage = (
                spiritomb_damage(obs)
                + damage_on(active)
                - damage_on(spiritomb)
                + roserade_bonus(obs)
            )
            if (
                option.type == OptionType.CARD
                and getattr(spiritomb, "id", None) == SPIRITOMB
                and energy_count(spiritomb) >= 1
                and projected_damage >= hp(target)
            ):
                return index
        return None

    if (
        context != SelectContext.MAIN
        or getattr(active, "id", None) != GARCHOMP_EX
        or damage_on(active) <= 0
        or getattr(target, "id", None) != 345
    ):
        return None

    retreat_indices = [
        index for index, option in enumerate(options)
        if option.type == OptionType.RETREAT
    ]
    if not retreat_indices:
        return None

    player = me(obs)
    bench_spiritombs = [
        pokemon for pokemon in (getattr(player, "bench", None) or [])
        if pokemon and pokemon.id == SPIRITOMB
    ]
    lethal_spiritombs = [
        spiritomb for spiritomb in bench_spiritombs
        if (
            spiritomb_damage(obs)
            + damage_on(active)
            - damage_on(spiritomb)
            + roserade_bonus(obs)
        ) >= hp(target)
    ]
    if any(energy_count(spiritomb) >= 1 for spiritomb in lethal_spiritombs):
        return retreat_indices[0]

    if getattr(obs.current, "energyAttached", None) is not False:
        return None

    eligible_attach_indices = [
        index for index, option in enumerate(options)
        if option.type == OptionType.ATTACH
        and getattr(option_card(obs, option), "id", None) in ENERGIES
        and option_target(obs, option) in lethal_spiritombs
    ]
    if eligible_attach_indices:
        return max(
            eligible_attach_indices,
            key=lambda index: (score_attach(obs, options[index])[0], -index),
        )
    if bench_spiritombs or player.hand is None:
        return None

    occupied_bench = sum(1 for pokemon in (player.bench or []) if pokemon)
    if occupied_bench >= player.benchMax:
        return None
    spiritomb_play_indices = [
        index for index, option in enumerate(options)
        if option.type == OptionType.PLAY
        and getattr(option_card(obs, option), "id", None) == SPIRITOMB
    ]
    energy_is_attachable = any(
        option.type == OptionType.ATTACH
        and getattr(option_card(obs, option), "id", None) in ENERGIES
        for option in options
    )
    projected_damage = spiritomb_damage(obs) + damage_on(active) + roserade_bonus(obs)
    if spiritomb_play_indices and energy_is_attachable and projected_damage >= hp(target):
        return spiritomb_play_indices[0]
    return None


def forced_promotion_attack_route_index(obs) -> int | None:
    """Promote a main line only for a complete, prize-safe attack route."""
    if (
        obs.select.context != SelectContext.TO_ACTIVE
        or active_pokemon(obs) is not None
    ):
        return None

    options = getattr(obs.select, "option", None) or []
    if not options:
        return None

    normal_scored = []
    for index, option in enumerate(options):
        try:
            score, _reason = score_option_with_champions_call_order(obs, option)
        except Exception:
            return None
        normal_scored.append((score, index))
    normal_index = max(normal_scored, key=lambda row: (row[0], -row[1]))[1]
    normal_id = getattr(option_card(obs, options[normal_index]), "id", None)
    if normal_id not in {ROSELIA, ROSERADE, SPIRITOMB}:
        return None

    legal_ids = {
        getattr(option_card(obs, option), "id", None)
        for option in options
        if option.type == OptionType.CARD
    }
    if GARCHOMP_EX in legal_ids:
        return None

    hand = set(hand_ids(obs))
    if GARCHOMP_EX not in hand:
        return None
    if len(getattr(opponent(obs), "prize", []) or []) <= 1:
        return None
    # TO_ACTIVE is resolved before the new turn's action flags are reset, so
    # energyAttached may still describe the preceding turn. A visible Energy
    # in hand is attachable after this mandatory promotion.
    manual_energy_available = bool(hand.intersection(ENERGIES))
    eligible = []
    for index, option in enumerate(options):
        if option.type != OptionType.CARD:
            continue
        pokemon = option_card(obs, option)
        pokemon_id = getattr(pokemon, "id", None)
        if pokemon_id not in {GIBLE, GABITE}:
            continue
        if getattr(pokemon, "appearThisTurn", True) is not False:
            continue
        if energy_count(pokemon) < 1 and not manual_energy_available:
            continue
        if pokemon_id == GIBLE and GABITE not in hand:
            continue
        eligible.append(
            (
                1 if pokemon_id == GABITE else 0,
                energy_count(pokemon),
                -damage_on(pokemon),
                -index,
                index,
            )
        )
    return max(eligible)[-1] if eligible else None


def normalized_energy_type(value) -> int | None:
    """Return a public EnergyType value without guessing unknown encodings."""
    value = getattr(value, "value", getattr(value, "id", value))
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def public_energy_types(pokemon) -> list[int] | None:
    """Return all publicly represented Energy units, failing closed on unknowns."""
    energies = getattr(pokemon, "energies", None)
    if energies is None:
        return None
    normalized = [normalized_energy_type(energy) for energy in energies]
    return None if any(energy is None for energy in normalized) else normalized


def attack_required_cost(attack_id: int) -> int | None:
    attack = ATTACK_DB.get(attack_id)
    costs = getattr(attack, "energies", None)
    if costs is None or any(normalized_energy_type(energy) is None for energy in costs):
        return None
    return len(costs)


def attack_cost_is_payable(active, attack_id: int) -> bool:
    """Conservatively match typed costs, with Colorless paid by any Energy."""
    attack = ATTACK_DB.get(attack_id)
    costs = getattr(attack, "energies", None)
    available = public_energy_types(active)
    if costs is None or available is None:
        return False
    required = [normalized_energy_type(energy) for energy in costs]
    if any(energy is None for energy in required):
        return False

    for energy_type in (energy for energy in required if energy != 0):
        matching_index = next(
            (index for index, provided in enumerate(available) if provided == energy_type),
            None,
        )
        if matching_index is None:
            matching_index = next(
                (index for index, provided in enumerate(available) if provided == 10),
                None,
            )
        if matching_index is None:
            return False
        available.pop(matching_index)
    return len(available) >= sum(energy == 0 for energy in required)


def attack_is_published_for_active(obs, attack_id: int) -> bool:
    active = active_pokemon(obs)
    published = getattr(CARD_DB.get(getattr(active, "id", None)), "attacks", None)
    return bool(
        active is not None
        and published is not None
        and attack_id in published
        and attack_id in ATTACK_DB
    )


def card_effect_text(card) -> str:
    card_id = getattr(card, "id", getattr(card, "cardId", None))
    data = CARD_DB.get(card_id)
    return " ".join(
        f"{getattr(skill, 'name', '')} {getattr(skill, 'text', '')}"
        for skill in (getattr(data, "skills", None) or [])
    ).lower().replace("’", "'")


def visible_damage_state_is_deterministic(obs, target) -> bool:
    """Reject status, protection, or modifiers that make a public KO ambiguous."""
    player = me(obs)
    if any(
        bool(getattr(player, status, False))
        for status in ("poisoned", "burned", "asleep", "paralyzed", "confused")
    ):
        return False
    if obs.select.context == SelectContext.MAIN and getattr(obs.select, "effect", None) is not None:
        return False

    active = active_pokemon(obs)
    for subject in (obs.current, active, target):
        if subject is None:
            return False
        for field in (
            "effects",
            "effectState",
            "attackEffect",
            "attackEffects",
            "attackDamageModifier",
            "damageBonus",
            "damageModifier",
            "damageReduction",
            "preventDamage",
            "protection",
        ):
            if getattr(subject, field, None):
                return False

    visible_cards = list(getattr(obs.current, "stadium", None) or [])
    for pokemon in my_pokemon(obs) + opponent_pokemon(obs):
        visible_cards.append(pokemon)
        visible_cards.extend(getattr(pokemon, "tools", None) or [])
        visible_cards.extend(energy_cards(pokemon))
    risky_phrases = (
        " less damage",
        "prevent all damage",
        "prevent damage",
        "no damage from attacks",
        "have no abilities",
        "has no abilities",
        "can't attack",
        "cannot attack",
    )
    return not any(
        phrase in card_effect_text(card)
        for card in visible_cards
        for phrase in risky_phrases
    )


def certified_public_damage(obs, target, attack_id: int) -> int | None:
    """Compute only visible deterministic damage, including Weakness/Resistance."""
    if (
        not attack_is_published_for_active(obs, attack_id)
        or not attack_cost_is_payable(active_pokemon(obs), attack_id)
        or not visible_damage_state_is_deterministic(obs, target)
    ):
        return None

    damage = best_damage_for_active(obs, attack_id)
    active_data = CARD_DB.get(getattr(active_pokemon(obs), "id", None))
    target_data = CARD_DB.get(getattr(target, "id", None))
    attack_type = normalized_energy_type(getattr(active_data, "energyType", None))
    weakness = normalized_energy_type(getattr(target_data, "weakness", None))
    resistance = normalized_energy_type(getattr(target_data, "resistance", None))
    attack_text = str(getattr(ATTACK_DB.get(attack_id), "text", "") or "").lower().replace("’", "'")
    if (
        attack_type is not None
        and weakness == attack_type
        and "isn't affected by weakness" not in attack_text
    ):
        damage *= 2
    if (
        attack_type is not None
        and resistance == attack_type
        and "isn't affected by resistance" not in attack_text
    ):
        damage = max(0, damage - 30)
    return damage


def attack_certifies_target(obs, target, attack_id: int) -> bool:
    damage = certified_public_damage(obs, target, attack_id)
    return damage is not None and damage >= hp(target)


def exposed_legal_attack_ids(obs) -> list[int]:
    return [
        option.attackId
        for option in (getattr(obs.select, "option", None) or [])
        if option.type == OptionType.ATTACK
        and option.attackId is not None
        and attack_is_published_for_active(obs, option.attackId)
        and attack_cost_is_payable(active_pokemon(obs), option.attackId)
    ]


def payable_published_attack_ids(obs) -> list[int]:
    active = active_pokemon(obs)
    return [
        attack_id
        for attack_id in (getattr(CARD_DB.get(getattr(active, "id", None)), "attacks", None) or [])
        if attack_is_published_for_active(obs, attack_id)
        and attack_cost_is_payable(active, attack_id)
    ]


def lethal_attack_ids(obs, target, attack_ids: list[int]) -> list[int]:
    return [
        attack_id
        for attack_id in attack_ids
        if attack_certifies_target(obs, target, attack_id)
    ]


def remaining_prizes(obs) -> int:
    return len(getattr(me(obs), "prize", None) or [])


def is_certified_nonwinning_active_ko(obs, target, attack_ids: list[int]) -> bool:
    prizes = remaining_prizes(obs)
    return bool(
        prizes > 0
        and target is not None
        and prize_value(target) < prizes
        and lethal_attack_ids(obs, target, attack_ids)
    )


def winning_target_attacks(obs, target, attack_ids: list[int]) -> list[int]:
    prizes = remaining_prizes(obs)
    if prizes <= 0 or target is None or prize_value(target) < prizes:
        return []
    return lethal_attack_ids(obs, target, attack_ids)


def target_is_visible_on_opponent_bench(obs, target) -> bool:
    target_serial = getattr(target, "serial", None)
    return any(
        pokemon is target
        or (
            target_serial is not None
            and getattr(pokemon, "serial", None) == target_serial
        )
        for pokemon in (getattr(opponent(obs), "bench", None) or [])
        if pokemon
    )


def certified_boss_prize_close_play_index(
    obs,
    scored: list[tuple[int, int, str]],
) -> int | None:
    """Replace only v80's next non-winning Active KO with a certified Boss finish."""
    if (
        obs.select.context != SelectContext.MAIN
        or not scored
        or getattr(obs.current, "supporterPlayed", None) is not False
    ):
        return None

    _score, baseline_index, _reason = max(scored, key=lambda row: (row[0], -row[1]))
    baseline_option = obs.select.option[baseline_index]
    legal_attack_ids = exposed_legal_attack_ids(obs)
    target = opponent_active(obs)
    if (
        baseline_option.type != OptionType.ATTACK
        or baseline_option.attackId not in legal_attack_ids
        or not is_certified_nonwinning_active_ko(obs, target, [baseline_option.attackId])
    ):
        return None

    boss_indices = [
        index
        for index, option in enumerate(obs.select.option)
        if option.type == OptionType.PLAY
        and getattr(option_card(obs, option), "id", None) == BOSS
    ]
    if not boss_indices:
        return None
    if not any(
        winning_target_attacks(obs, bench_target, legal_attack_ids)
        for bench_target in (getattr(opponent(obs), "bench", None) or [])
        if bench_target
    ):
        return None
    return boss_indices[0]


def log_type_value(log) -> int | None:
    value = getattr(log, "type", None)
    return normalized_energy_type(value)


def certified_boss_play_log(obs) -> bool:
    logs = list(getattr(obs, "logs", None) or [])
    return bool(
        len(logs) == 1
        and log_type_value(logs[0]) == 10
        and getattr(logs[0], "playerIndex", None) == obs.current.yourIndex
        and getattr(logs[0], "cardId", None) == BOSS
    )


def certified_boss_prize_close_target_index(obs) -> int | None:
    """Re-prove the original Active KO and choose the exact winning Bench target."""
    if (
        obs.select.context != SelectContext.SWITCH
        or getattr(getattr(obs.select, "effect", None), "id", None) != BOSS
        or getattr(obs.select, "minCount", None) != 1
        or getattr(obs.select, "maxCount", None) != 1
        or getattr(obs.current, "supporterPlayed", None) is not True
        or not certified_boss_play_log(obs)
    ):
        return None

    attack_ids = payable_published_attack_ids(obs)
    if not is_certified_nonwinning_active_ko(obs, opponent_active(obs), attack_ids):
        return None

    eligible = []
    for index, option in enumerate(obs.select.option):
        target = option_card(obs, option)
        winning_attacks = winning_target_attacks(obs, target, attack_ids)
        costs = [attack_required_cost(attack_id) for attack_id in winning_attacks]
        if (
            option.type != OptionType.CARD
            or not target_is_visible_on_opponent_bench(obs, target)
            or not winning_attacks
            or any(cost is None for cost in costs)
        ):
            continue
        eligible.append(
            (
                min(costs),
                -prize_value(target),
                hp(target),
                index,
            )
        )
    return min(eligible)[-1] if eligible else None


def switched_boss_targets(obs):
    """Return the unambiguous old/new opposing Actives from the latest switch."""
    if (
        obs.select.context != SelectContext.MAIN
        or getattr(obs.select, "effect", None) is not None
        or getattr(obs.current, "supporterPlayed", None) is not True
    ):
        return None
    logs = list(getattr(obs, "logs", None) or [])
    if len(logs) != 1 or log_type_value(logs[0]) != 8:
        return None
    switch = logs[0]
    if getattr(switch, "playerIndex", None) != 1 - obs.current.yourIndex:
        return None

    new_active = opponent_active(obs)
    old_serial = getattr(switch, "serialActive", None)
    new_serial = getattr(switch, "serialBench", None)
    if (
        new_active is None
        or old_serial is None
        or new_serial is None
        or getattr(new_active, "serial", None) != new_serial
    ):
        return None
    old_matches = [
        pokemon
        for pokemon in (getattr(opponent(obs), "bench", None) or [])
        if pokemon and getattr(pokemon, "serial", None) == old_serial
    ]
    if len(old_matches) != 1:
        return None
    return old_matches[0], new_active


def attack_resource_key(attack_id: int, option_index: int) -> tuple[int, int, int, int] | None:
    cost = attack_required_cost(attack_id)
    if cost is None:
        return None
    text = str(getattr(ATTACK_DB.get(attack_id), "text", "") or "").lower()
    consumes_resources = 1 if "discard" in text else 0
    corkscrew_preference = 0 if attack_id == CORKSCREW_DIVE else 1
    return cost, consumes_resources, corkscrew_preference, option_index


def certified_boss_prize_close_attack_index(obs) -> int | None:
    """After Boss, revalidate both KOs and take the cheapest certified lethal."""
    switched = switched_boss_targets(obs)
    if switched is None:
        return None
    old_active, winning_active = switched
    attack_ids = exposed_legal_attack_ids(obs)
    if (
        not is_certified_nonwinning_active_ko(obs, old_active, attack_ids)
        or not winning_target_attacks(obs, winning_active, attack_ids)
    ):
        return None

    eligible = []
    for index, option in enumerate(obs.select.option):
        if (
            option.type != OptionType.ATTACK
            or option.attackId not in winning_target_attacks(obs, winning_active, [option.attackId])
        ):
            continue
        key = attack_resource_key(option.attackId, index)
        if key is not None:
            eligible.append(key)
    return min(eligible)[-1] if eligible else None


def choose_options(obs):
    promotion_index = forced_promotion_attack_route_index(obs)
    if promotion_index is not None:
        return [promotion_index]
    counter_index = crustle_spiritomb_counter_index(obs)
    if counter_index is not None:
        return [counter_index]
    prize_close_attack_index = certified_boss_prize_close_attack_index(obs)
    if prize_close_attack_index is not None:
        return [prize_close_attack_index]
    backup_attach_index = prebuster_backup_attach_index(obs)
    if backup_attach_index is not None:
        return [backup_attach_index]
    route_index = champions_call_route_index(obs)
    if route_index is not None:
        return [route_index]
    prize_close_target_index = certified_boss_prize_close_target_index(obs)
    if prize_close_target_index is not None:
        return [prize_close_target_index]
    scored: list[tuple[int, int, str]] = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option_with_champions_call_order(obs, opt)
            call_before_evolve_score = matching_champions_call_evolve_score(obs, opt)
            if call_before_evolve_score is not None:
                score, reason = call_before_evolve_score, "Champion's Call before matching Garchomp ex evolution"
        except Exception as exc:
            score, reason = -999999, f"error {type(exc).__name__}: {exc}"
        scored.append((score, i, reason))
    cycle_selection = role_complete_attack_cycle_index(obs, scored)
    if cycle_selection is not None:
        return cycle_selection
    development_index = corkscrew_development_index(obs, scored)
    if development_index is not None:
        corkscrew_score = max(
            score for score, index, _reason in scored
            if obs.select.option[index].type == OptionType.ATTACK
            and obs.select.option[index].attackId == CORKSCREW_DIVE
        )
        for row_index, (score, index, reason) in enumerate(scored):
            if index == development_index:
                scored[row_index] = (max(score, corkscrew_score + 1), index, f"{reason} before Corkscrew")
                break
    if obs.select.context == SelectContext.MAIN:
        prize_close_play_index = certified_boss_prize_close_play_index(obs, scored)
        if prize_close_play_index is not None:
            return [prize_close_play_index]
        bridge_index = core_bridge_before_chip_index(obs, scored)
        if bridge_index is not None:
            return [bridge_index]
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    if obs.select.context == SelectContext.SETUP_BENCH_POKEMON and obs.select.minCount == 0:
        return [i for score, i, _reason in scored if score > 0][: obs.select.maxCount]
    selected: list[int] = []
    for score, i, _reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _score, i, _reason in scored[: obs.select.minCount]]
    return selected


def agent(observation: dict[str, Any]) -> list[int]:
    if observation.get("select") is None:
        return read_deck_csv()
    obs = to_observation_class(observation)
    return choose_options(obs)
