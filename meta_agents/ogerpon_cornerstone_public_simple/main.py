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
BASIC_PSYCHIC = 5
BASIC_FIGHTING = 6

EEVEE = 43
SYLVEON = 134
PATRAT = 626
NINCADA = 712
NINJASK = 713
SHEDINJA = 748
CORNERSTONE_OGERPON_EX = 117

BUDDY_POFFIN = 1086
CRUSHING_HAMMER = 1120
ULTRA_BALL = 1121
POKEGEAR = 1122
POKE_PAD = 1152
MAXIMUM_BELT = 1158
AIR_BALLOON = 1174
CRISPIN = 1198
HILDA = 1225
LILLIE = 1227
BATTLE_CAGE = 1264

SCRATCH = 1030
U_TURN = 1031
DAMAGE_BEAT = 1080
DEMOLISH = 148
ASCENSION = 39
QUICK_ATTACK = 40
MYSTICAL_RETURN = 173
DISARMING_VOICE = 174
PROCUREMENT = 903
GNAW = 904

BASICS = {CORNERSTONE_OGERPON_EX, NINCADA, EEVEE, PATRAT}
EVOLUTIONS = {NINJASK, SHEDINJA, SYLVEON}
MAIN_ATTACKERS = {CORNERSTONE_OGERPON_EX, NINJASK, SHEDINJA, SYLVEON}
ENERGIES = {BASIC_GRASS, BASIC_PSYCHIC, BASIC_FIGHTING}
SUPPORTERS = {CRISPIN, HILDA, LILLIE}

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


def min_energy_needed(card_id: int | None) -> int:
    if card_id == CORNERSTONE_OGERPON_EX:
        return 3
    if card_id == NINJASK:
        return 2
    if card_id in {SHEDINJA, SYLVEON}:
        return 1
    return 1


def main_attacker_ready(obs) -> bool:
    return any(p.id in MAIN_ATTACKERS and energy_count(p) >= min_energy_needed(p.id) for p in all_my_pokemon(obs))


def attack_damage(obs, attack_id: int) -> int:
    if attack_id == DAMAGE_BEAT:
        target = opp_active_pokemon(obs)
        return max(30, damage_on(target) * 2)
    if attack_id == MYSTICAL_RETURN:
        return 70
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def bench_basic_score(obs, cid: int | None) -> int:
    if cid == CORNERSTONE_OGERPON_EX:
        return 9800 - count_in_play(obs, CORNERSTONE_OGERPON_EX) * 1700
    if cid == NINCADA:
        return 8200 - count_in_play(obs, NINCADA) * 1000
    if cid == EEVEE:
        return 6200 - count_in_play(obs, EEVEE) * 900
    if cid == PATRAT:
        return 2400 - count_in_play(obs, PATRAT) * 800
    return 100


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2200, "prefer second") if opt.type == OptionType.NO else (1700, "first acceptable")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {
            CORNERSTONE_OGERPON_EX: 10500,
            NINCADA: 7000,
            EEVEE: 5200,
            PATRAT: 2500,
        }
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        return bench_basic_score(obs, cid), f"setup bench {card_name(cid)}"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    if cid in BASICS:
        return bench_basic_score(obs, cid), f"bench {card_name(cid)}"
    if cid == BATTLE_CAGE:
        return 6800, "Battle Cage"
    if cid == BUDDY_POFFIN:
        return 7600 if count_in_play(obs, NINCADA) < 2 or count_in_play(obs, EEVEE) < 1 else 1800, "Buddy-Buddy Poffin"
    if cid == ULTRA_BALL:
        if count_in_play(obs, CORNERSTONE_OGERPON_EX) < 1 or (has_in_play(obs, NINCADA) and count_in_play(obs, SHEDINJA) + count_in_play(obs, NINJASK) < 1):
            return 7600, "Ultra Ball for wall line"
        return 2200, "Ultra Ball"
    if cid == POKE_PAD:
        return -500 if deck_count(obs) <= 8 else 3600, "Poke Pad"
    if cid == POKEGEAR:
        return -500 if deck_count(obs) <= 8 else 3400, "Pokegear"
    if cid == CRUSHING_HAMMER:
        return 5200 if any(energy_count(p) > 0 for p in all_opp_pokemon(obs)) else 400, "Crushing Hammer"
    if cid == CRISPIN:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 7600 if not main_attacker_ready(obs) else 2200, "Crispin"
    if cid == HILDA:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 6400 if my_state(obs).handCount <= 5 else 1800, "Hilda"
    if cid == LILLIE:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if deck_count(obs) <= 8:
            return -600, "hold Lillie near deckout"
        return 6800 if my_state(obs).handCount <= 4 else 1700, "Lillie"
    if cid == AIR_BALLOON:
        return 5200, "Air Balloon"
    if cid == MAXIMUM_BELT:
        return 6200 if any(p.id == CORNERSTONE_OGERPON_EX for p in all_my_pokemon(obs)) else 1400, "Maximum Belt"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == SHEDINJA and tid in {NINCADA, NINJASK}:
        return 9800, "evolve Shedinja"
    if cid == NINJASK and tid == NINCADA:
        return 9000, "evolve Ninjask"
    if cid == SYLVEON and tid == EEVEE:
        return 7600, "evolve Sylveon"
    if cid in EVOLUTIONS:
        return 5200, f"evolve {card_name(cid)}"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == AIR_BALLOON and target is not None:
        return 6200 if tid in MAIN_ATTACKERS else 1800, "Air Balloon target"
    if cid == MAXIMUM_BELT and target is not None:
        return 7800 if tid == CORNERSTONE_OGERPON_EX else 1600, "Maximum Belt target"
    if cid not in ENERGIES or target is None:
        return 100, "attach"
    if tid == CORNERSTONE_OGERPON_EX:
        return 9000 + max(0, 3 - energy_count(target)) * 1000, "attach to Cornerstone"
    if tid == NINJASK:
        return 7200 + max(0, 2 - energy_count(target)) * 800, "attach to Ninjask"
    if tid in {SHEDINJA, SYLVEON}:
        return 6600 + max(0, 1 - energy_count(target)) * 1000, f"attach to {card_name(tid)}"
    if tid in {NINCADA, EEVEE}:
        return 3000, "preload evolution base"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if not active:
        return 0, "retreat"
    if active.id == CORNERSTONE_OGERPON_EX and energy_count(active) >= 2:
        return -1400, "keep Cornerstone active"
    if active.id in MAIN_ATTACKERS and energy_count(active) >= min_energy_needed(active.id):
        return -800, "keep attacker active"
    if main_attacker_ready(obs):
        return 8200, "retreat to attacker"
    return 500, "retreat"


def best_active_damage(obs) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    if active.id == CORNERSTONE_OGERPON_EX:
        return 140
    if active.id == NINJASK:
        return 90
    if active.id == SYLVEON:
        return 90
    if active.id == SHEDINJA:
        return attack_damage(obs, DAMAGE_BEAT)
    if active.id == EEVEE:
        return 20
    if active.id == PATRAT:
        return 10
    return 0


def target_score(obs, target) -> tuple[int, str]:
    cid = getattr(target, "id", None)
    damage = best_active_damage(obs)
    if damage >= hp(target):
        return 30000 + prize_value(target) * 5000 - hp(target), f"KO {card_name(cid)}"
    setup_bonus = 5000 if cid in {169, 190, 741, 742, 743, 1030, 1031, 97, 98, 494} else 0
    return 4200 + setup_bonus + prize_value(target) * 1100 + energy_count(target) * 500 - hp(target), f"pressure {card_name(cid)}"


def attack_score(obs, attack_id: int) -> tuple[int, str]:
    target = opp_active_pokemon(obs)
    damage = attack_damage(obs, attack_id)
    ko = target is not None and damage >= hp(target)
    if attack_id == DEMOLISH:
        return 11800 + damage + (8500 if ko else 0), "Demolish"
    if attack_id == DAMAGE_BEAT:
        return 9800 + damage + (7000 if ko else 0), "Damage Beat"
    if attack_id in {U_TURN, DISARMING_VOICE}:
        return 8200 + damage + (6500 if ko else 0), "attack"
    if attack_id == ASCENSION:
        return 7600 if any(x in hand_ids(obs) for x in {SYLVEON}) else 4200, "Ascension"
    if attack_id == PROCUREMENT:
        return 5200 if my_state(obs).handCount <= 4 else 1600, "Procurement"
    return 3000 + damage + (5000 if ko else 0), "attack"


def discard_score(obs, card_id: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {CORNERSTONE_OGERPON_EX, NINCADA, SHEDINJA, NINJASK} and not main_attacker_ready(obs):
        return -5200, f"keep wall line {card_name(card_id)}"
    if card_id in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -1500, "keep early energy"
    if card_id in SUPPORTERS and not obs.current.supporterPlayed and my_state(obs).handCount <= 5:
        return -1200, f"keep supporter {card_name(card_id)}"
    if card_id is not None and hand.count(card_id) >= 2:
        return 2400, f"discard duplicate {card_name(card_id)}"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == CORNERSTONE_OGERPON_EX:
        return 9600 if count_in_play(obs, CORNERSTONE_OGERPON_EX) < 1 else 2500, "take Cornerstone"
    if cid == NINCADA:
        return 8200 if count_in_play(obs, NINCADA) < 2 else 1800, "take Nincada"
    if cid in {SHEDINJA, NINJASK}:
        return 7600 if has_in_play(obs, NINCADA) else 2200, f"take {card_name(cid)}"
    if cid == SYLVEON:
        return 6200 if has_in_play(obs, EEVEE) else 1500, "take Sylveon"
    if cid in ENERGIES:
        return 5000, "take energy"
    if cid in {CRISPIN, LILLIE, HILDA, ULTRA_BALL, BUDDY_POFFIN, POKE_PAD, BATTLE_CAGE}:
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
            return target_score(obs, card)
        if cid == CORNERSTONE_OGERPON_EX:
            return 10500 + energy_count(card) * 800, "promote Cornerstone"
        if cid in MAIN_ATTACKERS and energy_count(card) >= min_energy_needed(cid):
            return 8600 + energy_count(card) * 500, f"promote {card_name(cid)}"
        if cid in {NINCADA, EEVEE, PATRAT}:
            return 1200, f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid in MAIN_ATTACKERS:
            return 9000 + max(0, min_energy_needed(cid) - energy_count(card)) * 500, f"effect to {card_name(cid)}"
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
        return 1600, f"ability {card_name(getattr(card, 'id', None))}"
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
        return 1400, "yes"
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
