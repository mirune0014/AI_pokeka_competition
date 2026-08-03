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


LITWICK = 97
CHANDELURE = 98
COMFEY = 164
SHAYMIN = 343
LAMPENT = 494

PSYCHIC_ENERGY = 5
TELEPATH_PSYCHIC_ENERGY = 19

BUDDY_POFFIN = 1086
RARE_CANDY = 1079
ENHANCED_HAMMER = 1081
NIGHT_STRETCHER = 1097
ENERGY_SEARCH = 1119
CRUSHING_HAMMER = 1120
SWITCH = 1123
POKE_PAD = 1152
GRAVITY_GEMSTONE = 1166
BOSS = 1182
ERI = 1186
XEROSIC = 1197
HILDA = 1225
LILLIE = 1227
DAWN = 1231
NEUTRALIZATION_ZONE = 1247
BATTLE_CAGE = 1264

CALL_FOR_FAMILY = 121
LIVE_COAL = 122
MIND_RULER = 123
FLOWER_SHOWER = 215
PLAY_ROUGH = 216
SMASH_KICK = 477
FIRE_BLAST = 699

BASICS = {LITWICK, COMFEY, SHAYMIN}
POKEMON = {LITWICK, LAMPENT, CHANDELURE, COMFEY, SHAYMIN}
ENERGIES = {PSYCHIC_ENERGY, TELEPATH_PSYCHIC_ENERGY}
SUPPORTERS = {BOSS, ERI, XEROSIC, HILDA, LILLIE, DAWN}
ITEMS = {
    BUDDY_POFFIN,
    RARE_CANDY,
    ENHANCED_HAMMER,
    NIGHT_STRETCHER,
    ENERGY_SEARCH,
    CRUSHING_HAMMER,
    SWITCH,
    POKE_PAD,
}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


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


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def bench_space(obs) -> int:
    return my_state(obs).benchMax - len(my_state(obs).bench)


def needs_litwick(obs) -> bool:
    return count_in_play(obs, LITWICK) + count_in_play(obs, LAMPENT) + count_in_play(obs, CHANDELURE) < 2


def needs_chandelure(obs) -> bool:
    return any(p.id in {LITWICK, LAMPENT} for p in all_my_pokemon(obs)) and count_in_play(obs, CHANDELURE) < 2


def ready_chandelure(obs) -> bool:
    return any(p.id == CHANDELURE and energy_count(p) >= 1 for p in all_my_pokemon(obs))


def attack_damage(obs, attack_id: int) -> int:
    if attack_id == MIND_RULER:
        return max(60, 20 * int(getattr(opp_state(obs), "handCount", 0) or 0))
    if attack_id == FLOWER_SHOWER:
        return 40
    if attack_id == PLAY_ROUGH:
        return 20
    if attack_id == FIRE_BLAST:
        return 50
    if attack_id == LIVE_COAL:
        return 20
    if attack_id == SMASH_KICK:
        return 30
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def best_attack_score(obs, attack_id: int) -> int:
    if attack_id == CALL_FOR_FAMILY:
        return 9000 if needs_litwick(obs) and bench_space(obs) > 0 else 100
    dmg = attack_damage(obs, attack_id)
    target = opp_active_pokemon(obs)
    if target and dmg >= hp(target):
        return 20000 + prize_value(target) * 2500
    if attack_id == MIND_RULER:
        return 9000 + dmg
    return dmg


def has_opponent_energy(obs) -> bool:
    return any(energy_count(p) > 0 for p in all_opp_pokemon(obs))


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2100, "prefer first") if opt.type == OptionType.YES else (1600, "second acceptable")
    if ctx == SelectContext.MULLIGAN:
        return (10000, "no mulligan") if opt.type == OptionType.NO else (0, "mulligan")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        if cid == LITWICK:
            return 9000, "setup active Litwick"
        if cid == COMFEY:
            return 7200, "setup active Comfey"
        if cid == SHAYMIN:
            return 1000, "setup active Shaymin"
        return 100, "setup active"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == LITWICK:
            return 8200 - count_in_play(obs, LITWICK) * 900, "setup bench Litwick"
        if cid == COMFEY:
            return 6500 - count_in_play(obs, COMFEY) * 900, "setup bench Comfey"
        if cid == SHAYMIN:
            return 700, "setup bench Shaymin"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    ids = hand_ids(obs)

    if cid == LITWICK:
        return (9500 if needs_litwick(obs) else 2200), "bench Litwick"
    if cid == COMFEY:
        return (7600 if count_in_play(obs, COMFEY) < 2 else 1600), "bench Comfey"
    if cid == SHAYMIN:
        return 900, "bench Shaymin"

    if cid == BUDDY_POFFIN:
        if not needs_litwick(obs) and count_in_play(obs, COMFEY) >= 2:
            return -400, "skip complete Poffin"
        return 21000, "use Poffin"
    if cid == RARE_CANDY:
        if CHANDELURE in ids and any(p.id == LITWICK for p in all_my_pokemon(obs)):
            return 23000, "Rare Candy to Chandelure"
        return -400, "save Rare Candy"
    if cid == ENERGY_SEARCH:
        return 17500 if not any(i in ENERGIES for i in ids) else 300, "Energy Search"
    if cid == CRUSHING_HAMMER:
        return 18000 if has_opponent_energy(obs) else 1200, "Crushing Hammer"
    if cid == ENHANCED_HAMMER:
        return 17000 if has_opponent_energy(obs) else 800, "Enhanced Hammer"
    if cid == SWITCH:
        active = active_pokemon(obs)
        if active and active.id != CHANDELURE and ready_chandelure(obs):
            return 19000, "Switch to Chandelure"
        return 600, "save Switch"
    if cid == NIGHT_STRETCHER:
        disc = discard_ids(obs)
        if CHANDELURE in disc or LITWICK in disc or any(e in disc for e in ENERGIES):
            return 16500, "Night Stretcher resource"
        return -300, "save Night Stretcher"
    if cid == POKE_PAD:
        return 15500, "Poke Pad"
    if cid in {GRAVITY_GEMSTONE, NEUTRALIZATION_ZONE, BATTLE_CAGE}:
        return 13000, "play stadium/tool"

    if cid in SUPPORTERS:
        if obs.current.supporterPlayed:
            return -1000, "supporter already used"
        if cid == BOSS:
            if not ready_chandelure(obs):
                return -300, "save Boss"
            return 15000, "Boss pressure"
        if cid in {XEROSIC, ERI}:
            return 17000, "hand disruption"
        if cid in {HILDA, LILLIE, DAWN}:
            return 14500, "draw/setup supporter"

    return 1000, "generic play"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == CHANDELURE and tid in {LITWICK, LAMPENT}:
        return 25000, "evolve Chandelure"
    if cid == LAMPENT and tid == LITWICK and CHANDELURE not in hand_ids(obs):
        return 12000, "evolve Lampent"
    if cid == LAMPENT and tid == LITWICK:
        return 4500, "hold Lampent if Candy line available"
    return 1000, "evolve"


def attach_target_score(obs, target) -> int:
    if target is None:
        return 0
    cid = getattr(target, "id", None)
    e = energy_count(target)
    if e >= 2:
        return -1000
    if cid == CHANDELURE:
        return 19000 if e == 0 else 7000
    if cid in {LITWICK, LAMPENT}:
        return 15000 if e == 0 else 4500
    if cid == COMFEY:
        return 9000 if e == 0 else 1000
    return 1000


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    if cid not in ENERGIES:
        return -500, "skip non-energy"
    if obs.current.energyAttached:
        return -1000, "already attached"
    return attach_target_score(obs, target), "attach Psychic"


def score_retreat(obs, opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id != CHANDELURE and ready_chandelure(obs):
        return 13500, "retreat to Chandelure"
    return -100, "avoid retreat"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    effect = getattr(obs.select, "effect", None)
    effect_id = getattr(effect, "id", None)

    if effect_id == BUDDY_POFFIN:
        if cid == LITWICK:
            return 24000 - count_in_play(obs, LITWICK) * 1000, "Poffin Litwick"
        if cid == COMFEY:
            return 20000 - count_in_play(obs, COMFEY) * 1000, "Poffin Comfey"
        return 1000, "Poffin fallback"

    if cid == CHANDELURE and needs_chandelure(obs):
        return 23000, "take Chandelure"
    if cid == RARE_CANDY and CHANDELURE in hand_ids(obs):
        return 21000, "take Rare Candy"
    if cid == LITWICK and needs_litwick(obs):
        return 19000, "take Litwick"
    if cid == LAMPENT and needs_chandelure(obs):
        return 13000, "take Lampent"
    if cid in ENERGIES:
        return 12000, "take Energy"
    if cid in {BOSS, XEROSIC, ERI}:
        return 10000, "take disruption"
    if cid in {HILDA, LILLIE, DAWN} and not obs.current.supporterPlayed:
        return 9000, "take supporter"
    if cid in ITEMS:
        return 6000, "take item"
    return 1000, "take"


def score_discard(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    ids = hand_ids(obs)
    if cid in {CHANDELURE, LITWICK}:
        return -5000, "keep core line"
    if cid in ENERGIES and ids.count(cid) <= 1:
        return -3000, "keep last energy"
    if cid == COMFEY and count_in_play(obs, COMFEY) < 2:
        return -1000, "keep Comfey"
    if cid in {HILDA, LILLIE, DAWN} and sum(1 for i in ids if i in {HILDA, LILLIE, DAWN}) > 1:
        return 9000, "discard spare draw"
    if cid in {GRAVITY_GEMSTONE, BATTLE_CAGE}:
        return 8500, "discard extra stadium/tool"
    if cid in ITEMS:
        return 5000, "discard item"
    return 1000, "discard"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    ctx = obs.select.context

    if ctx == SelectContext.ATTACH_TO:
        return (5000, "Psychic Energy") if cid in ENERGIES else (1000, "attach")
    if ctx == SelectContext.ATTACH_FROM:
        return attach_target_score(obs, card), "effect attach"
    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == CHANDELURE:
            return 24000, "target Chandelure"
        if cid == LAMPENT:
            return 15000, "target Lampent"
        if cid == LITWICK:
            return 18000, "target Litwick"
        if cid == COMFEY:
            return 12000, "target Comfey"
        return 1000, "target"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        yi = obs.current.yourIndex
        pi = getattr(opt, "playerIndex", yi)
        if pi != yi and card:
            dmg = attack_damage(obs, MIND_RULER)
            if dmg >= hp(card):
                return 22000 + prize_value(card) * 2500, "Boss KO"
            return 5000 + prize_value(card) * 1500 - hp(card), "Boss pressure"
        if cid == CHANDELURE:
            return 18000, "promote Chandelure"
        if cid == COMFEY:
            return 12000, "promote Comfey"
        if cid == LITWICK:
            return 9000, "promote Litwick"
        return 1000, "promote"
    if ctx == SelectContext.DAMAGE:
        return 10000 - hp(card), "damage lowest HP"
    return 1000, "target"


def score_option(obs, opt) -> tuple[int, str]:
    ctx = obs.select.context
    if ctx in {
        SelectContext.IS_FIRST,
        SelectContext.MULLIGAN,
        SelectContext.SETUP_ACTIVE_POKEMON,
        SelectContext.SETUP_BENCH_POKEMON,
    }:
        return setup_score(obs, opt)
    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.ACTIVATE:
            return (100000, "use ability") if opt.type == OptionType.YES else (-100000, "decline ability")
        return (1, "yes") if opt.type == OptionType.YES else (0, "no")
    if opt.type == OptionType.NUMBER:
        return opt.number or 0, "number"

    if ctx == SelectContext.MAIN:
        if opt.type == OptionType.PLAY:
            return score_play(obs, opt)
        if opt.type == OptionType.EVOLVE:
            return score_evolve(obs, opt)
        if opt.type == OptionType.ATTACH:
            return score_attach(obs, opt)
        if opt.type == OptionType.RETREAT:
            return score_retreat(obs, opt)
        if opt.type == OptionType.ABILITY:
            return 12000, "ability"
        if opt.type == OptionType.ATTACK:
            return best_attack_score(obs, opt.attackId), "attack"
        if opt.type == OptionType.END:
            return 0, "end turn"
        return 500, "main"
    if ctx == SelectContext.TO_HAND:
        return score_to_hand(obs, opt)
    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        return score_discard(obs, opt)
    if ctx in {
        SelectContext.ATTACH_TO,
        SelectContext.TO_FIELD,
        SelectContext.TO_BENCH,
        SelectContext.ATTACH_FROM,
        SelectContext.SWITCH,
        SelectContext.TO_ACTIVE,
        SelectContext.HEAL,
        SelectContext.DAMAGE,
    }:
        return score_target(obs, opt)
    if ctx == SelectContext.ATTACK:
        return best_attack_score(obs, opt.attackId), "attack"
    if opt.type == OptionType.CARD:
        return score_to_hand(obs, opt)
    if opt.type == OptionType.ENERGY:
        return 1000, "energy"
    if opt.type == OptionType.END:
        return 0, "end"
    return 100, "fallback"


def choose_options(obs):
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as exc:
            score, reason = -999999, f"error {type(exc).__name__}: {exc}"
        scored.append((score, i, reason))
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)

    selected = []
    for score, i, _ in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[: obs.select.minCount]]
    return selected


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()
    if not obs.select.option:
        return []
    return choose_options(obs)
