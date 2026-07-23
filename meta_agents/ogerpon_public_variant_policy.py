from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

for path in (Path.cwd(), Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, SelectContext, all_attack, all_card_data, to_observation_class


BASIC_GRASS = 1
BASIC_FIRE = 2
BASIC_WATER = 3
BASIC_LIGHTNING = 4
BASIC_PSYCHIC = 5
BASIC_FIGHTING = 6
LEGACY_ENERGY = 12
PRISM_ENERGY = 16

POLTCHAGEIST = 28
SINISTCHA_EX = 29
SINISTCHA = 94
APPLIN = 42
DIPPLIN = 93
TEAL_OGERPON_EX = 96
HEARTHFLAME_OGERPON_EX = 99
WELLSPRING_OGERPON_EX = 108
CORNERSTONE_OGERPON_EX = 117
RAGING_BOLT_EX = 63
IRON_LEAVES_EX = 75
HYDRAPPLE_EX = 150
MEGANIUM = 710
MEGA_MEGANIUM_EX = 919
MEGA_KANGASKHAN_EX = 756
MEGA_LOPUNNY_EX = 849
ARBOLIVA_EX = 404
CHIKORITA = 708
BAYLEEF = 709
SMOLIV = 402
DOLLIV = 403
LATIAS_EX = 184
FEZANDIPITI_EX = 140
MEOWTH_EX = 1071
BUDEW = 235
TAPU_BULU = 920
CELEBI = 655
SHAYMIN = 45
CHIEN_PAO = 209
PSYDUCK = 858
PASSIMIAN = 978

BUDDY_POFFIN = 1086
PRIME_CATCHER = 1088
NIGHT_STRETCHER = 1097
ENERGY_SWITCH = 1116
ENERGY_RETRIEVAL = 1118
ENERGY_SEARCH = 1119
CRUSHING_HAMMER = 1120
ULTRA_BALL = 1121
POKEGEAR = 1122
TERA_ORB = 1127
POKE_PAD = 1152
AIR_BALLOON = 1174
ERI = 1186
CRISPIN = 1198
BRIAR = 1201
CYRANO = 1205
HILDA = 1225
LILLIE = 1227
DAWN = 1231
AREA_ZERO = 1250
WATCHTOWER = 1256
FOREST_OF_VITALITY = 1261

MYRIAD_LEAF_SHOWER = 120
SYRUP_STORM = 195
BELLOWING_THUNDER = 72
BURST_ROAR = 71
SPILL_THE_TEA = 117
RE_BREW = 15
OIL_SALVO = 564

ENERGIES = {
    BASIC_GRASS,
    BASIC_FIRE,
    BASIC_WATER,
    BASIC_LIGHTNING,
    BASIC_PSYCHIC,
    BASIC_FIGHTING,
    LEGACY_ENERGY,
    PRISM_ENERGY,
}

BASIC_POKEMON = {
    POLTCHAGEIST,
    APPLIN,
    TEAL_OGERPON_EX,
    HEARTHFLAME_OGERPON_EX,
    WELLSPRING_OGERPON_EX,
    CORNERSTONE_OGERPON_EX,
    RAGING_BOLT_EX,
    IRON_LEAVES_EX,
    CHIKORITA,
    SMOLIV,
    LATIAS_EX,
    FEZANDIPITI_EX,
    MEOWTH_EX,
    BUDEW,
    TAPU_BULU,
    CELEBI,
    SHAYMIN,
    CHIEN_PAO,
    PSYDUCK,
    PASSIMIAN,
    MEGA_KANGASKHAN_EX,
}

EVOLUTIONS = {
    SINISTCHA_EX,
    SINISTCHA,
    DIPPLIN,
    HYDRAPPLE_EX,
    BAYLEEF,
    MEGANIUM,
    MEGA_MEGANIUM_EX,
    DOLLIV,
    ARBOLIVA_EX,
    MEGA_LOPUNNY_EX,
}

ATTACKERS = {
    TEAL_OGERPON_EX,
    HEARTHFLAME_OGERPON_EX,
    WELLSPRING_OGERPON_EX,
    CORNERSTONE_OGERPON_EX,
    RAGING_BOLT_EX,
    IRON_LEAVES_EX,
    HYDRAPPLE_EX,
    MEGANIUM,
    MEGA_MEGANIUM_EX,
    ARBOLIVA_EX,
    SINISTCHA_EX,
    SINISTCHA,
    MEGA_KANGASKHAN_EX,
    MEGA_LOPUNNY_EX,
    TAPU_BULU,
    CELEBI,
    SHAYMIN,
    BUDEW,
}

LINE_BASICS = {
    CHIKORITA: {BAYLEEF, MEGANIUM, MEGA_MEGANIUM_EX},
    APPLIN: {DIPPLIN, HYDRAPPLE_EX},
    POLTCHAGEIST: {SINISTCHA, SINISTCHA_EX},
    SMOLIV: {DOLLIV, ARBOLIVA_EX},
}

SETUP_PRIORITY = {
    TEAL_OGERPON_EX: 9800,
    CORNERSTONE_OGERPON_EX: 9400,
    RAGING_BOLT_EX: 9200,
    MEGA_KANGASKHAN_EX: 9000,
    IRON_LEAVES_EX: 8600,
    HYDRAPPLE_EX: 8500,
    HEARTHFLAME_OGERPON_EX: 8400,
    WELLSPRING_OGERPON_EX: 8200,
    MEGA_LOPUNNY_EX: 8000,
    MEGA_MEGANIUM_EX: 8000,
    ARBOLIVA_EX: 7800,
    SINISTCHA_EX: 7600,
    MEGANIUM: 7400,
    TAPU_BULU: 7200,
    CELEBI: 6500,
    SHAYMIN: 6000,
    CHIKORITA: 5600,
    APPLIN: 5400,
    POLTCHAGEIST: 5200,
    SMOLIV: 5000,
    LATIAS_EX: 3600,
    FEZANDIPITI_EX: 3400,
    MEOWTH_EX: 3000,
    BUDEW: 2800,
}

ENERGY_NEED = {
    TEAL_OGERPON_EX: 1,
    CORNERSTONE_OGERPON_EX: 3,
    RAGING_BOLT_EX: 3,
    MEGA_KANGASKHAN_EX: 3,
    HYDRAPPLE_EX: 2,
    MEGA_MEGANIUM_EX: 2,
    MEGANIUM: 2,
    ARBOLIVA_EX: 3,
    SINISTCHA_EX: 2,
    SINISTCHA: 1,
    HEARTHFLAME_OGERPON_EX: 3,
    WELLSPRING_OGERPON_EX: 3,
    IRON_LEAVES_EX: 3,
    MEGA_LOPUNNY_EX: 2,
}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


@lru_cache(maxsize=64)
def _read_deck(path: str) -> tuple[int, ...]:
    return tuple(int(line.strip()) for line in Path(path).read_text().splitlines() if line.strip())


def read_deck_csv() -> list[int]:
    for candidate in (Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return list(_read_deck(str(candidate.resolve())))
    raise FileNotFoundError("deck.csv was not found")


def deck_set() -> set[int]:
    return set(read_deck_csv())


def card_name(card_id: int | None) -> str:
    if card_id is None:
        return ""
    card = CARD_DB.get(card_id)
    return card.name if card else str(card_id)


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
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    if opt.type == OptionType.PLAY:
        return get_card(obs, AreaType.HAND, opt.index, pi)
    return get_card(obs, opt.area, opt.index, pi)


def option_target(obs, opt):
    if opt.inPlayArea is None or opt.inPlayIndex is None:
        return None
    return get_card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)


def my_state(obs):
    return obs.current.players[obs.current.yourIndex]


def opp_state(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    player = my_state(obs)
    return player.active[0] if player.active else None


def opp_active_pokemon(obs):
    player = opp_state(obs)
    return player.active[0] if player.active else None


def all_my_pokemon(obs):
    player = my_state(obs)
    return [p for p in (player.active + player.bench) if p]


def all_opp_pokemon(obs):
    player = opp_state(obs)
    return [p for p in (player.active + player.bench) if p]


def hand_ids(obs) -> list[int]:
    hand = my_state(obs).hand
    return [card.id for card in hand if card] if hand else []


def discard_ids(obs) -> list[int]:
    return [card.id for card in (my_state(obs).discard or []) if card]


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def total_energy_in_play(obs) -> int:
    return sum(energy_count(p) for p in all_my_pokemon(obs))


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    return int(getattr(pokemon, "maxHp", getattr(CARD_DB.get(getattr(pokemon, "id", None)), "hp", 0)) or 0)


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
    return int(getattr(my_state(obs), "deckCount", 0) or 0)


def is_needed_line_basic(obs, card_id: int) -> bool:
    wanted = LINE_BASICS.get(card_id, set())
    return bool(wanted & deck_set()) and count_in_play(obs, card_id) < 2


def target_priority(card_id: int | None) -> int:
    if card_id is None:
        return 0
    return SETUP_PRIORITY.get(card_id, 3000 if card_id in ATTACKERS else 1200)


def attacker_ready(pokemon) -> bool:
    if not pokemon or pokemon.id not in ATTACKERS:
        return False
    return energy_count(pokemon) >= ENERGY_NEED.get(pokemon.id, 2)


def main_attacker_ready(obs) -> bool:
    return any(attacker_ready(p) for p in all_my_pokemon(obs))


def active_is_attacker(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id in ATTACKERS)


def best_my_attacker(obs):
    pokemon = all_my_pokemon(obs)
    if not pokemon:
        return None
    return max(
        pokemon,
        key=lambda p: (
            target_priority(getattr(p, "id", None)),
            energy_count(p),
            max_hp(p),
            -damage_on(p),
        ),
    )


def attack_damage(attack_id: int) -> int:
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def effective_attack_damage(obs, attack_id: int) -> int:
    active = active_pokemon(obs)
    opp = opp_active_pokemon(obs)
    base = attack_damage(attack_id)
    if attack_id == MYRIAD_LEAF_SHOWER:
        return 30 + 30 * (energy_count(active) + energy_count(opp))
    if attack_id == SYRUP_STORM:
        return max(base, 30 * max(1, total_energy_in_play(obs)))
    if attack_id == BELLOWING_THUNDER:
        return max(90, 70 * max(1, total_energy_in_play(obs)))
    if attack_id == SPILL_THE_TEA:
        grass_discard = sum(1 for cid in discard_ids(obs) if cid == BASIC_GRASS)
        return max(70, 30 * max(1, grass_discard))
    if attack_id == RE_BREW:
        return 80 + min(120, sum(damage_on(p) for p in all_my_pokemon(obs)) // 2)
    if attack_id == OIL_SALVO:
        return 110 if energy_count(active) >= 2 else 50
    if attack_id == BURST_ROAR:
        return 0
    return base


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (1600, "go first") if opt.type == OptionType.YES else (1900, "prefer second")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        bonus = 1600 if cid in deck_set() and cid in ATTACKERS else 0
        if is_needed_line_basic(obs, cid):
            bonus += 1200
        return target_priority(cid) + bonus, f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid in BASIC_POKEMON:
            duplicates = count_in_play(obs, cid)
            if cid in {LATIAS_EX, FEZANDIPITI_EX, MEOWTH_EX, BUDEW} and duplicates:
                return 200, f"avoid duplicate support {card_name(cid)}"
            line_bonus = 1400 if is_needed_line_basic(obs, cid) else 0
            return max(600, target_priority(cid) - duplicates * 1800 + line_bonus), f"setup bench {card_name(cid)}"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = deck_count(obs)
    if cid in BASIC_POKEMON:
        duplicates = count_in_play(obs, cid)
        line_bonus = 1800 if is_needed_line_basic(obs, cid) else 0
        if cid in {LATIAS_EX, FEZANDIPITI_EX, MEOWTH_EX, BUDEW} and duplicates:
            return 300, f"skip duplicate support {card_name(cid)}"
        return target_priority(cid) + line_bonus - duplicates * 1700, f"bench {card_name(cid)}"
    if cid in {FOREST_OF_VITALITY, AREA_ZERO, WATCHTOWER}:
        return 4800, f"stadium {card_name(cid)}"
    if cid == ULTRA_BALL:
        return 7600 if not main_attacker_ready(obs) else 2600, "Ultra Ball"
    if cid in {BUDDY_POFFIN, TERA_ORB}:
        return 6200 if not main_attacker_ready(obs) else 2600, card_name(cid)
    if cid == BUG_CATCHING_SET:
        return 6400 if deck > 8 else -600, "Bug Catching Set"
    if cid in {CRISPIN, DAWN, HILDA}:
        return 6100 if not main_attacker_ready(obs) else 3000, card_name(cid)
    if cid == LILLIE:
        return -800 if deck <= 8 else (5600 if len(hand_ids(obs)) <= 5 else 2200), "Lillie"
    if cid in {POKE_PAD, POKEGEAR}:
        return -700 if deck <= 9 else 3300, card_name(cid)
    if cid in {ENERGY_SWITCH, ENERGY_RETRIEVAL, ENERGY_SEARCH}:
        return 4200 if all_my_pokemon(obs) else 800, card_name(cid)
    if cid == NIGHT_STRETCHER:
        key_discarded = any(x in discard_ids(obs) for x in ATTACKERS | ENERGIES)
        return 4300 if key_discarded else 900, "Night Stretcher"
    if cid in {PRIME_CATCHER, BRIAR}:
        return 5200 if active_is_attacker(obs) else 1500, card_name(cid)
    if cid in {ERI, CRUSHING_HAMMER}:
        return 1800, card_name(cid)
    return 700, f"play {card_name(cid)}"


BUG_CATCHING_SET = 1094


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid in EVOLUTIONS:
        return target_priority(cid) + 2600, f"evolve {card_name(cid)}"
    return 1200, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == AIR_BALLOON:
        return 5200 if tid in ATTACKERS else 900, "Air Balloon"
    if cid not in ENERGIES:
        return 400 + target_priority(tid) // 20, "attach"
    need = ENERGY_NEED.get(tid, 2)
    missing = max(0, need - energy_count(target))
    return target_priority(tid) + missing * 900 + max(0, 4 - energy_count(target)) * 180, f"energy to {card_name(tid)}"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    best = best_my_attacker(obs)
    if not active or not best:
        return 0, "retreat"
    if active.id == best.id and energy_count(active) >= energy_count(best):
        return -1300, "keep best active"
    if attacker_ready(best):
        return 8500 + target_priority(best.id), f"retreat to {card_name(best.id)}"
    return 500, "retreat"


def best_active_damage(obs) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    attacks = getattr(CARD_DB.get(active.id), "attacks", None) or []
    return max([effective_attack_damage(obs, aid) for aid in attacks] or [0])


def best_boss_target(obs):
    bench = [p for p in (opp_state(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    cid = getattr(target, "id", None)
    damage = best_active_damage(obs)
    if damage >= hp(target):
        return 28000 + prize_value(target) * 5000 - hp(target), f"target KO {card_name(cid)}"
    return 4200 + prize_value(target) * 1400 + energy_count(target) * 700 - hp(target), f"target {card_name(cid)}"


def attack_score(obs, attack_id: int) -> tuple[int, str]:
    active = opp_active_pokemon(obs)
    damage = effective_attack_damage(obs, attack_id)
    if attack_id == BURST_ROAR:
        return 6500 if len(hand_ids(obs)) <= 4 else 900, "Burst Roar"
    score = 7000 + damage * 22
    reason = ATTACK_DB.get(attack_id).name if attack_id in ATTACK_DB else "attack"
    if active and damage >= hp(active):
        score += 14000 + prize_value(active) * 5000
        reason += " KO"
    return score, reason


def discard_score(obs, card_id: int | None) -> tuple[int, str]:
    if card_id is None:
        return 0, "discard unknown"
    hand = hand_ids(obs)
    if card_id in ATTACKERS and not main_attacker_ready(obs):
        return -5200, f"keep attacker {card_name(card_id)}"
    if card_id in BASIC_POKEMON and is_needed_line_basic(obs, card_id):
        return -3600, f"keep line basic {card_name(card_id)}"
    if card_id in ENERGIES and total_energy_in_play(obs) < 3:
        return -1800, "keep energy"
    if hand.count(card_id) >= 2:
        return 2600, f"discard duplicate {card_name(card_id)}"
    if card_id in {LILLIE, BUG_CATCHING_SET, ULTRA_BALL, CRISPIN, DAWN, HILDA} and len(hand) <= 5:
        return -900, f"keep draw/search {card_name(card_id)}"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid in ATTACKERS:
        present = count_in_play(obs, cid)
        return target_priority(cid) + (2800 if not present else 500), f"take attacker {card_name(cid)}"
    if cid in BASIC_POKEMON and is_needed_line_basic(obs, cid):
        return target_priority(cid) + 2200, f"take line basic {card_name(cid)}"
    if cid in EVOLUTIONS:
        return target_priority(cid) + 1600, f"take evolution {card_name(cid)}"
    if cid in ENERGIES:
        return 4700 if total_energy_in_play(obs) < 4 else 1800, "take energy"
    if cid in {BUG_CATCHING_SET, ULTRA_BALL, BUDDY_POFFIN, TERA_ORB, LILLIE, CRISPIN, DAWN, HILDA, NIGHT_STRETCHER}:
        return 3600, f"take {card_name(cid)}"
    return 700, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "target unknown"
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi:
            return boss_target_score(obs, card)
        return target_priority(cid) + energy_count(card) * 800 - damage_on(card) // 2, f"promote {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        return target_priority(cid) + max(0, ENERGY_NEED.get(cid, 2) - energy_count(card)) * 900, f"attach target {card_name(cid)}"
    if ctx == SelectContext.HEAL:
        return damage_on(card) + target_priority(cid) // 8, f"heal {card_name(cid)}"
    if ctx == SelectContext.DAMAGE:
        damage = best_active_damage(obs)
        if damage >= hp(card):
            return 24000 + prize_value(card) * 4000, f"damage KO {card_name(cid)}"
        return 3500 + prize_value(card) * 900 + energy_count(card) * 500 - hp(card), f"damage {card_name(cid)}"
    return 1000, f"target {card_name(cid)}"


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
        cid = getattr(card, "id", None)
        return 4200 if cid in {TEAL_OGERPON_EX, FEZANDIPITI_EX, MEOWTH_EX} else 1400, f"ability {card_name(cid)}"
    if opt.type == OptionType.DISCARD:
        card = option_card(obs, opt)
        return discard_score(obs, getattr(card, "id", None))
    if opt.type == OptionType.CARD:
        if ctx == SelectContext.DISCARD:
            card = option_card(obs, opt)
            return discard_score(obs, getattr(card, "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt)
        return score_target(obs, opt)
    if opt.type in {OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1000, "attached card"
    if opt.type == OptionType.YES:
        return 1500, "yes"
    if opt.type == OptionType.NO:
        return 300, "no"
    if opt.type == OptionType.END:
        return 0, "end"
    if opt.type == OptionType.NUMBER:
        return int(getattr(opt, "number", 0) or 0) * 100, "number"
    return 100, "fallback"


def choose_options(obs):
    scored: list[tuple[int, int, str]] = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as exc:
            score, reason = -999999, f"error {type(exc).__name__}: {exc}"
        scored.append((score, i, reason))
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
