from __future__ import annotations

import sys
from pathlib import Path


try:
    ROOT = Path(__file__).resolve().parent
except NameError:
    ROOT = Path.cwd()

for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, SelectContext, all_attack, all_card_data, to_observation_class


BASIC_GRASS = 1
BASIC_WATER = 3
BASIC_LIGHTNING = 4
BASIC_PSYCHIC = 5
BASIC_FIGHTING = 6

RAGING_BOLT_EX = 63
IRON_LEAVES_EX = 75
TEAL_MASK_OGERPON_EX = 96
WELLSPRING_MASK_OGERPON_EX = 108
FEZANDIPITI_EX = 140
LATIAS_EX = 184
CHIEN_PAO = 209
MEGA_KANGASKHAN_EX = 756
PASSIMIAN = 978
MEOWTH_EX = 1071

UNFAIR_STAMP = 1080
NIGHT_STRETCHER = 1097
GLASS_TRUMPET = 1098
ENERGY_SWITCH = 1116
ULTRA_BALL = 1121
CRISPIN = 1198
CYRANO = 1205
LILLIE = 1227
AREA_ZERO = 1250

BURST_ROAR = 71
BELLOWING_THUNDER = 72
PRISM_EDGE = 89
MYRIAD_LEAF_SHOWER = 120
TORRENTIAL_PUMP = 136
CRUEL_ARROW = 183
EON_BLADE = 243
ICICLE_LOOP = 281
RAPID_FIRE_COMBO = 1092
COORDINATED_THROWING = 1407
TUCK_TAIL = 1546

BASICS = {
    RAGING_BOLT_EX,
    IRON_LEAVES_EX,
    TEAL_MASK_OGERPON_EX,
    WELLSPRING_MASK_OGERPON_EX,
    FEZANDIPITI_EX,
    LATIAS_EX,
    CHIEN_PAO,
    MEGA_KANGASKHAN_EX,
    PASSIMIAN,
    MEOWTH_EX,
}
MAIN_ATTACKERS = {RAGING_BOLT_EX, MEGA_KANGASKHAN_EX, TEAL_MASK_OGERPON_EX, IRON_LEAVES_EX}
PIVOTS = {LATIAS_EX, FEZANDIPITI_EX, MEOWTH_EX}
ENERGIES = {BASIC_GRASS, BASIC_WATER, BASIC_LIGHTNING, BASIC_PSYCHIC, BASIC_FIGHTING}
SUPPORTERS = {CRISPIN, CYRANO, LILLIE}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


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


def deck_count(obs) -> int:
    return int(getattr(my_state(obs), "deckCount", 0) or 0)


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


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def bench_space(obs) -> int:
    return my_state(obs).benchMax - len(my_state(obs).bench)


def main_attacker_ready(obs) -> bool:
    return any(p.id in MAIN_ATTACKERS and energy_count(p) >= min_energy_needed(p.id) for p in all_my_pokemon(obs))


def min_energy_needed(card_id: int | None) -> int:
    if card_id == RAGING_BOLT_EX:
        return 2
    if card_id == MEGA_KANGASKHAN_EX:
        return 3
    if card_id == TEAL_MASK_OGERPON_EX:
        return 3
    if card_id == IRON_LEAVES_EX:
        return 3
    if card_id == WELLSPRING_MASK_OGERPON_EX:
        return 3
    if card_id in {LATIAS_EX, CHIEN_PAO}:
        return 3
    return 1


def attack_damage(obs, attack_id: int) -> int:
    if attack_id == BELLOWING_THUNDER:
        return max(70, total_energy_in_play(obs) * 70)
    if attack_id == CRUEL_ARROW:
        return 100
    if attack_id == COORDINATED_THROWING:
        return 90 if any(p.id in PIVOTS for p in all_my_pokemon(obs)) else 40
    if attack_id == MYRIAD_LEAF_SHOWER:
        active = active_pokemon(obs)
        opp_active = opp_active_pokemon(obs)
        return 30 + 30 * (energy_count(active) + energy_count(opp_active))
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        if opt.type == OptionType.NO:
            return 2300, "prefer second for Energy Switch pressure"
        return 1600, "going first acceptable"
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {
            TEAL_MASK_OGERPON_EX: 9800,
            MEGA_KANGASKHAN_EX: 9000,
            RAGING_BOLT_EX: 8400,
            MEOWTH_EX: 6200,
            IRON_LEAVES_EX: 5200,
            WELLSPRING_MASK_OGERPON_EX: 4600,
            LATIAS_EX: 4200,
            FEZANDIPITI_EX: 3600,
        }
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        return bench_basic_score(obs, cid), f"setup bench {card_name(cid)}"
    return 0, "setup"


def bench_basic_score(obs, cid: int | None) -> int:
    if cid == TEAL_MASK_OGERPON_EX:
        return 8600 - count_in_play(obs, TEAL_MASK_OGERPON_EX) * 1200
    if cid == RAGING_BOLT_EX:
        return 7800 - count_in_play(obs, RAGING_BOLT_EX) * 1000
    if cid == MEGA_KANGASKHAN_EX:
        return 7200 - count_in_play(obs, MEGA_KANGASKHAN_EX) * 900
    if cid == MEOWTH_EX:
        return 5200 - count_in_play(obs, MEOWTH_EX) * 1000
    if cid in {IRON_LEAVES_EX, WELLSPRING_MASK_OGERPON_EX, LATIAS_EX, FEZANDIPITI_EX}:
        return 4200 - count_in_play(obs, cid) * 900
    if cid in {CHIEN_PAO, PASSIMIAN}:
        return 2600 - count_in_play(obs, cid) * 700
    return 100


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    if cid in BASICS:
        return bench_basic_score(obs, cid), f"bench {card_name(cid)}"
    if cid == AREA_ZERO:
        return 7600 if len(all_my_pokemon(obs)) >= 3 else 4200, "Area Zero"
    if cid == ENERGY_SWITCH:
        loaded = any(energy_count(p) >= 1 for p in all_my_pokemon(obs))
        needs = any(p.id in MAIN_ATTACKERS and energy_count(p) < min_energy_needed(p.id) for p in all_my_pokemon(obs))
        return 9000 if loaded and needs else 1800, "Energy Switch"
    if cid == GLASS_TRUMPET:
        has_energy_discard = any(x in ENERGIES for x in discard_ids(obs))
        return 6600 if has_energy_discard and bench_space(obs) <= 1 else 2200, "Glass Trumpet"
    if cid == ULTRA_BALL:
        if count_in_play(obs, TEAL_MASK_OGERPON_EX) < 2 or not any(p.id in {RAGING_BOLT_EX, MEGA_KANGASKHAN_EX} for p in all_my_pokemon(obs)):
            return 7200, "Ultra Ball for core"
        return 2800, "Ultra Ball"
    if cid == NIGHT_STRETCHER:
        if any(x in discard_ids(obs) for x in {RAGING_BOLT_EX, TEAL_MASK_OGERPON_EX, MEGA_KANGASKHAN_EX} | ENERGIES):
            return 4400, "recover key resource"
        return 700, "Night Stretcher"
    if cid == UNFAIR_STAMP:
        return 5200 if len(my_state(obs).prize) < len(opp_state(obs).prize) else 1200, "Unfair Stamp"
    if cid == CRISPIN:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 8600 if not main_attacker_ready(obs) else 2800, "Crispin"
    if cid == CYRANO:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 7400 if count_in_play(obs, TEAL_MASK_OGERPON_EX) < 2 else 3200, "Cyrano"
    if cid == LILLIE:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if deck_count(obs) <= 8:
            return -600, "hold Lillie near deckout"
        return 6800 if my_state(obs).handCount <= 4 else 1600, "Lillie"
    return 500, f"play {card_name(cid)}"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid not in ENERGIES or target is None:
        return 100, "attach"
    if tid == RAGING_BOLT_EX:
        return 9200 + max(0, 2 - energy_count(target)) * 1200, "attach to Raging Bolt"
    if tid == MEGA_KANGASKHAN_EX:
        return 8600 + max(0, 3 - energy_count(target)) * 900, "attach to Kangaskhan"
    if tid == TEAL_MASK_OGERPON_EX:
        return 8200 + max(0, 3 - energy_count(target)) * 700, "attach to Teal Mask"
    if tid == IRON_LEAVES_EX:
        return 7600 + max(0, 3 - energy_count(target)) * 700, "attach to Iron Leaves"
    if tid in {WELLSPRING_MASK_OGERPON_EX, LATIAS_EX, CHIEN_PAO}:
        return 5600, f"attach to {card_name(tid)}"
    return 700, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if not active:
        return 0, "retreat"
    if active.id in MAIN_ATTACKERS and energy_count(active) >= min_energy_needed(active.id):
        return -1200, "keep ready attacker"
    if main_attacker_ready(obs):
        return 8500, "retreat to ready attacker"
    return 500, "retreat"


def best_active_damage(obs) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    if active.id == RAGING_BOLT_EX:
        return max(70, total_energy_in_play(obs) * 70)
    if active.id == MEGA_KANGASKHAN_EX:
        return 200
    if active.id == TEAL_MASK_OGERPON_EX:
        return 30 + 30 * (energy_count(active) + energy_count(opp_active_pokemon(obs)))
    if active.id == IRON_LEAVES_EX:
        return 180
    if active.id == LATIAS_EX:
        return 200
    if active.id == CHIEN_PAO:
        return 120
    if active.id == WELLSPRING_MASK_OGERPON_EX:
        return 120
    if active.id == FEZANDIPITI_EX:
        return 100
    if active.id == MEOWTH_EX:
        return 60
    return 0


def boss_target_score(obs, target) -> tuple[int, str]:
    cid = getattr(target, "id", None)
    damage = best_active_damage(obs)
    if damage >= hp(target):
        return 30000 + prize_value(target) * 5000 - hp(target), f"target KO {card_name(cid)}"
    setup_bonus = 4500 if cid in {169, 190, 741, 742, 743, 1030, 1031, 97, 98, 494} else 0
    return 3800 + setup_bonus + prize_value(target) * 1200 + energy_count(target) * 500 - hp(target), f"target {card_name(cid)}"


def attack_score(obs, attack_id: int) -> tuple[int, str]:
    target = opp_active_pokemon(obs)
    damage = attack_damage(obs, attack_id)
    ko = target is not None and damage >= hp(target)
    if attack_id == BELLOWING_THUNDER:
        return 12500 + damage + (9000 if ko else 0), "Bellowing Thunder"
    if attack_id == RAPID_FIRE_COMBO:
        return 12200 + damage + (8000 if ko else 0), "Rapid-Fire Combo"
    if attack_id == MYRIAD_LEAF_SHOWER:
        return 9800 + damage + (7000 if ko else 0), "Myriad Leaf Shower"
    if attack_id == BURST_ROAR:
        return 7600 if my_state(obs).handCount <= 5 else 2600, "Burst Roar"
    if attack_id in {PRISM_EDGE, EON_BLADE, ICICLE_LOOP, TORRENTIAL_PUMP}:
        return 9000 + damage + (7000 if ko else 0), "attack"
    if attack_id == CRUEL_ARROW:
        return 8200 + (7000 if ko else 0), "Cruel Arrow"
    if attack_id == TUCK_TAIL:
        return 6200 + (5000 if ko else 0), "Tuck Tail"
    return 4200 + damage + (6000 if ko else 0), "attack"


def discard_score(obs, card_id: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {RAGING_BOLT_EX, TEAL_MASK_OGERPON_EX, MEGA_KANGASKHAN_EX} and not main_attacker_ready(obs):
        return -5200, f"keep attacker {card_name(card_id)}"
    if card_id in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -1500, "keep early energy"
    if card_id in SUPPORTERS and not obs.current.supporterPlayed and my_state(obs).handCount <= 5:
        return -1200, f"keep supporter {card_name(card_id)}"
    if card_id is not None and hand.count(card_id) >= 2:
        return 2500, f"discard duplicate {card_name(card_id)}"
    if card_id in ENERGIES:
        return 900, "discard extra energy"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == TEAL_MASK_OGERPON_EX:
        return 9800 if count_in_play(obs, TEAL_MASK_OGERPON_EX) < 2 else 2800, "take Teal Mask"
    if cid == RAGING_BOLT_EX:
        return 9200 if count_in_play(obs, RAGING_BOLT_EX) < 1 else 2600, "take Raging Bolt"
    if cid == MEGA_KANGASKHAN_EX:
        return 8400 if count_in_play(obs, MEGA_KANGASKHAN_EX) < 1 else 2400, "take Kangaskhan"
    if cid in {ENERGY_SWITCH, CRISPIN, ULTRA_BALL, AREA_ZERO}:
        return 6500, f"take {card_name(cid)}"
    if cid in ENERGIES:
        return 5200, "take energy"
    if cid in {LILLIE, CYRANO, NIGHT_STRETCHER, GLASS_TRUMPET}:
        return 3600, f"take {card_name(cid)}"
    if cid in BASICS:
        return bench_basic_score(obs, cid), f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


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
        if cid in MAIN_ATTACKERS and energy_count(card) >= min_energy_needed(cid):
            return 9600 + energy_count(card) * 700, f"promote {card_name(cid)}"
        if cid in MAIN_ATTACKERS:
            return 4200 + energy_count(card) * 600, f"promote setup {card_name(cid)}"
        if cid in PIVOTS:
            return 2200, f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid in MAIN_ATTACKERS:
            return 9000 + max(0, min_energy_needed(cid) - energy_count(card)) * 500, f"effect to {card_name(cid)}"
        if cid in PIVOTS:
            return 3000, f"effect to pivot {card_name(cid)}"
    if ctx in {SelectContext.TO_BENCH, SelectContext.TO_FIELD}:
        return bench_basic_score(obs, cid), f"bench from effect {card_name(cid)}"
    if ctx in {SelectContext.DAMAGE, SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY}:
        if pi != yi:
            if best_active_damage(obs) >= hp(card):
                return 23000 + prize_value(card) * 3000, f"damage KO {card_name(cid)}"
            return 3000 + prize_value(card) * 700 + energy_count(card) * 400 - hp(card), f"damage {card_name(cid)}"
        return -5000, "avoid self damage"
    if ctx in {SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER}:
        return damage_on(card) if pi == yi else -100, "heal"
    return 1000, f"target {card_name(cid)}"


def score_option(obs, opt) -> tuple[int, str]:
    ctx = obs.select.context
    if ctx in {SelectContext.IS_FIRST, SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return setup_score(obs, opt)
    if opt.type == OptionType.PLAY:
        return score_play(obs, opt)
    if opt.type == OptionType.ATTACH:
        return score_attach(obs, opt)
    if opt.type == OptionType.RETREAT:
        return score_retreat(obs, opt)
    if opt.type == OptionType.ATTACK:
        return attack_score(obs, opt.attackId)
    if opt.type == OptionType.ABILITY:
        card = option_card(obs, opt)
        cid = getattr(card, "id", None)
        if cid == TEAL_MASK_OGERPON_EX:
            return 7600, "Teal Dance"
        if cid == FEZANDIPITI_EX:
            return 5800, "Flip the Script"
        return 1800, f"ability {card_name(cid)}"
    if opt.type == OptionType.DISCARD:
        card = option_card(obs, opt)
        return discard_score(obs, getattr(card, "id", None))
    if opt.type == OptionType.CARD:
        card = option_card(obs, opt)
        if ctx == SelectContext.DISCARD:
            return discard_score(obs, getattr(card, "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt)
        return score_target(obs, opt)
    if opt.type in {OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1200, "attached card"
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


def _agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()
    return choose_options(obs)


def agent(obs_dict: dict, configuration=None) -> list[int]:
    try:
        return _agent(obs_dict)
    except Exception:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return read_deck_csv()
        return list(range(min(obs.select.minCount, len(obs.select.option))))
