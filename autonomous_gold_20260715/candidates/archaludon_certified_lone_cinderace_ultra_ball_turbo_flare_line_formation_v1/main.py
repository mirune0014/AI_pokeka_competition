"""Archaludon ex + Cinderace — Rule-based agent (Public version)

Deck Concept:
  Cinderace's Explosiveness places it face-down as Active during setup.
  Turn 1 Turbo Flare ({C}=50) accelerates up to 3 Basic Energy from deck
  to benched Duraludon. Evolving into Archaludon ex triggers Assemble Alloy,
  attaching up to 2 Basic Metal Energy from discard to Metal Pokemon.
  Metal Defender ({M}{M}{M}=220) is the main attack; no Weakness next turn.
  Non-ex Archaludon is included as an Ogerpon answer: Coated Attack does 120
  and prevents attack damage from Basic Pokemon on the next opponent turn.
  Duraludon can attack directly with Raging Hammer ({M}{M}{C}=80 + 10 per
  damage counter) without evolving. This variant cuts Relicanth to restore a
  third Full Metal Lab while keeping Boss's Orders x4. Hero's Cape gives +100
  HP (HP400). Full Metal Lab reduces attack damage to Metal Pokemon by 30.

Pokemon:
  Duraludon (169)      - Basic Metal HP130. Hammer In {M}=30.
                         Raging Hammer {M}{M}{C}=80+10*damage_counters.
  Archaludon ex (190)  - Stage 1 from Duraludon, HP300. Assemble Alloy: on evolve
                         from hand, attach up to 2 Metal Energy from discard.
                         Metal Defender {M}{M}{M}=220, no Weakness next turn.
  Archaludon (840)     - Stage 1 from Duraludon, HP180. Coated Attack
                         {M}{M}{M}=120, prevents Basic Pokemon attack damage.
  Cinderace (666)      - Stage 2 HP160. Explosiveness: place face-down as Active
                         in setup from opening hand. Turbo Flare {C}=50, attach
                         up to 3 Basic Energy from deck to benched Pokemon.

Trainers:
  Poke Pad (1152), Ultra Ball (1121), Pokegear 3.0 (1122), Night Stretcher (1097),
  Jumbo Ice Cream (1147), Hero's Cape (1159), Boss's Orders (1182),
  Explorer's Guidance (1185), Lillie's Determination (1227), Full Metal Lab (1244) x3.

Energy: Basic Metal Energy (8) x11

Score system:
  Setup/play/evolve/attach: 1000~28000 (high = do first)
  Attack: damage value (always last — attacking ends the turn)
  Negative = skip if above minCount
"""

import os
import random
import sys
import math

try:
    ROOT = __file__
except NameError:
    ROOT = None
CG_PATH = "/kaggle_simulations/agent"
for p in ([os.path.dirname(os.path.abspath(ROOT))] if ROOT else []) + [CG_PATH]:
    if p and p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

from cg.api import (
    AreaType,
    LogType,
    OptionType,
    SelectContext,
    all_card_data,
    to_observation_class,
)

try:
    from cg.api import all_attack
    ALL_ATTACKS = {a.attackId: a for a in all_attack()}
except Exception:
    ALL_ATTACKS = {}

# ── Card IDs ──

DURALUDON = 169
ARCHALUDON = 840
ARCHALUDON_EX = 190
CINDERACE = 666
RELICANTH = 57
CRUSTLE_LINE = {344, 345, 532}
GREAT_TUSK_LINE = {58, 607}
STARMIE_LINE = {1030, 1031}
LUCARIO_LINE = {677, 678}
OGERPON_LINE = {116, 117, 1051, 1052, 1256, 134, 712, 713, 748}
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
HOP_SNORLAX = 304
CHANDELURE_LINE = {97, 98, 494}

METAL_ENERGY = 8

POKE_PAD = 1152
ULTRA_BALL = 1121
POKEGEAR = 1122
NIGHT_STRETCHER = 1097
JUMBO_ICE_CREAM = 1147
HERO_CAPE = 1159
BOSS = 1182
EXPLORER = 1185
LILLIE = 1227
FULL_METAL_LAB = 1244

RAGING_HAMMER = 224
COATED_ATTACK = 1212
METAL_DEFENDER = 253

_ATTACK_BASE_DMG = {METAL_DEFENDER: 220, COATED_ATTACK: 120, 965: 50, 223: 30, 61: 30}

_SETUP_ACTIVE_PRIORITY = {
    CINDERACE: (100000, "Active: Cinderace Explosiveness"),
    DURALUDON: (20000, "Active fallback: Duraludon"),
    RELICANTH: (5000, "Active fallback: Relicanth"),
}

ALWAYS_SAFE_DISCARD = {METAL_ENERGY, CINDERACE}

CARD_DB = {c.cardId: c for c in all_card_data()}

MEGA_BRAVE = 983
PREMIUM_POWER_PRO = 1141
HARIYAMA_LINE = {673, 674}

# Track opponent's last-turn attack via logs
_opp_last_attack_id = None
_cur_turn_logs = []

# H3 owns only the certified lone-Cinderace Ultra Ball -> Turbo Flare
# transaction.  It is deliberately independent of all other candidate rules.
_h3_transaction = None
_h3_last_seat = None
_h3_last_turn = None


def _update_opp_attack_tracking(obs):
    global _opp_last_attack_id, _cur_turn_logs
    yi = obs.current.yourIndex
    for entry in obs.logs:
        if entry.type == LogType.TURN_END:
            for prev in _cur_turn_logs:
                if prev.type == LogType.ATTACK and getattr(prev, 'playerIndex', yi) != yi:
                    _opp_last_attack_id = prev.attackId
            _cur_turn_logs.clear()
        else:
            _cur_turn_logs.append(entry)


# ── Board helpers ──

def read_deck_csv():
    fp = "deck.csv"
    if not os.path.exists(fp):
        fp = "/kaggle_simulations/agent/deck.csv"
    with open(fp) as f:
        return [int(line) for line in f.read().strip().split("\n")]


def get_card(obs, area, index, player_index):
    if area is None or index is None:
        return None
    ps = obs.current.players[player_index]
    if area == AreaType.DECK and obs.select and obs.select.deck is not None:
        return obs.select.deck[index] if index < len(obs.select.deck) else None
    if area == AreaType.HAND and ps.hand is not None:
        return ps.hand[index] if index < len(ps.hand) else None
    if area == AreaType.DISCARD:
        return ps.discard[index] if index < len(ps.discard) else None
    if area == AreaType.ACTIVE:
        return ps.active[index] if index < len(ps.active) else None
    if area == AreaType.BENCH:
        return ps.bench[index] if index < len(ps.bench) else None
    if area == AreaType.PRIZE:
        return ps.prize[index] if index < len(ps.prize) else None
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
    ps = my_state(obs)
    return ps.active[0] if ps.active else None


def opp_active_pokemon(obs):
    ps = opp_state(obs)
    return ps.active[0] if ps.active else None


def opp_bench_pokemon(obs):
    return [p for p in opp_state(obs).bench if p]


def all_my_pokemon(obs):
    ps = my_state(obs)
    return [p for p in (ps.active + ps.bench) if p]


def hand_ids(obs):
    hand = my_state(obs).hand
    return [c.id for c in hand if c] if hand else []


def discard_ids(obs):
    return [c.id for c in (my_state(obs).discard or []) if c]


def opp_visible_card_ids(obs):
    opp = opp_state(obs)
    ids = [c.id for c in (opp.discard or []) if c]
    for pokemon in (opp.active + opp.bench):
        if not pokemon:
            continue
        ids.append(pokemon.id)
        ids.extend(c.id for c in (getattr(pokemon, "energyCards", None) or []) if c)
        ids.extend(c.id for c in (getattr(pokemon, "tools", None) or []) if c)
    return set(ids)


def metal_in_discard(obs):
    return sum(1 for c in (my_state(obs).discard or []) if c and c.id == METAL_ENERGY)


def energy_count(pokemon):
    if pokemon is None:
        return 0
    if getattr(pokemon, "energyCards", None) is not None:
        return len(pokemon.energyCards)
    return len(getattr(pokemon, "energies", []) or [])


def retreat_cost(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    return getattr(data, "retreatCost", 0) if data else 0


def damage_on(pokemon):
    if pokemon is None:
        return 0
    return max(0, getattr(pokemon, "maxHp", pokemon.hp) - pokemon.hp)


def has_tool(pokemon):
    return bool(getattr(pokemon, "tools", []) or [])


def count_in_play(obs, card_id):
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id):
    return any(p.id == card_id for p in all_my_pokemon(obs))


def live_alakazam_marker_visible(obs):
    if detect_matchup(obs) != "alakazam":
        return False
    seen = opp_visible_card_ids(obs)
    if seen & KETCHUM_ALAKAZAM_MARKERS:
        return False
    return bool(seen & LIVE_ALAKAZAM_MARKERS)


def need_duraludon(obs):
    if detect_matchup(obs) == "alakazam":
        target_count = 4 if live_alakazam_marker_visible(obs) else 3
        return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < target_count
    return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < 2


def need_archaludon(obs):
    has_dura, ex_count = False, 0
    for p in all_my_pokemon(obs):
        if p.id == DURALUDON:
            has_dura = True
        elif p.id == ARCHALUDON_EX:
            ex_count += 1
    if detect_matchup(obs) == "alakazam":
        target_ex_count = 4 if live_alakazam_marker_visible(obs) else 3
    else:
        target_ex_count = 2
    return has_dura and ex_count < target_ex_count


def need_nonex_archaludon(obs):
    if detect_matchup(obs) != "ogerpon":
        return False
    has_dura = any(p.id == DURALUDON for p in all_my_pokemon(obs))
    return has_dura and not has_in_play(obs, ARCHALUDON)


def final_prize_nonex_no_backup(obs):
    matchup = detect_matchup(obs)
    if matchup not in {"iono", "alakazam"}:
        return False
    if len(opp_state(obs).prize or []) > 2:
        return False
    if matchup == "alakazam":
        if not live_alakazam_marker_visible(obs):
            return False
    return not any(prize_value(p) == 1 for p in my_state(obs).bench if p)


def safe_discard_count(obs):
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    safe = 0
    for cid in ids:
        if cid == METAL_ENERGY and mt + safe < 2:
            safe += 1
        elif cid == CINDERACE:
            safe += 1
    draw_in_hand = sum(1 for c in ids if c in (LILLIE, EXPLORER))
    if draw_in_hand >= 2:
        safe += draw_in_hand - 1
    return safe


def prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data and getattr(data, "megaEx", False):
        return 3
    if data and getattr(data, "ex", False):
        return 2
    return 1


def best_attack_damage(obs, attack_id):
    if attack_id == RAGING_HAMMER:
        return 80 + damage_on(active_pokemon(obs)) // 10 * 10
    return _ATTACK_BASE_DMG.get(attack_id, 0)


def is_metal_weak(pokemon):
    if pokemon is None:
        return False
    data = CARD_DB.get(pokemon.id)
    w = getattr(data, "weakness", None) if data else None
    if w is None:
        return False
    return getattr(w, "value", w) == METAL_ENERGY


def effective_damage(base_damage, target):
    return base_damage * 2 if is_metal_weak(target) else base_damage


# ── H3 certified lone-Cinderace transaction ──

_H3_TURBO_FLARE = 965
_H3_DURALUDON_COPIES = 4
_H3_METAL_COPIES = 12
_H3_ACCESS_THRESHOLD = 0.999


def _h3_reset():
    global _h3_transaction
    _h3_transaction = None


def _h3_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) else None


def _h3_card_key(card):
    return (getattr(card, "id", -1), _h3_serial(card))


def _h3_prize_count(player):
    # Prize contents are hidden.  H3 uses the public count only.
    return len(getattr(player, "prize", None) or ())


def _h3_energy_key(card):
    return (getattr(card, "id", -1), _h3_serial(card))


def _h3_pokemon_fingerprint(pokemon, include_hp=True):
    if pokemon is None:
        return None
    output = (
        pokemon.id,
        _h3_serial(pokemon),
        getattr(pokemon, "maxHp", None),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(sorted(
            _h3_energy_key(card)
            for card in (getattr(pokemon, "energyCards", None) or ())
            if card is not None
        )),
        tuple(sorted(
            _h3_card_key(card)
            for card in (getattr(pokemon, "tools", None) or ())
            if card is not None
        )),
        tuple(sorted(
            _h3_card_key(card)
            for card in (getattr(pokemon, "preEvolution", None) or ())
            if card is not None
        )),
    )
    if include_hp:
        output += (getattr(pokemon, "hp", None),)
    return output


def _h3_player_conditions(player):
    return tuple(
        bool(getattr(player, name, False))
        for name in (
            "poisoned",
            "burned",
            "asleep",
            "paralyzed",
            "confused",
        )
    )


def _h3_stadium_fingerprint(obs):
    return tuple(
        _h3_card_key(card)
        for card in (getattr(obs.current, "stadium", None) or ())
        if card is not None
    )


def _h3_opponent_fingerprint(obs, include_active_hp=True):
    opponent = opp_state(obs)
    active = opponent.active[0] if opponent.active else None
    return (
        _h3_pokemon_fingerprint(active, include_active_hp),
        tuple(
            _h3_pokemon_fingerprint(pokemon, True)
            for pokemon in (opponent.bench or ())
            if pokemon is not None
        ),
        _h3_player_conditions(opponent),
    )


def _h3_public_own_cards(obs):
    """Yield only our publicly visible cards, never hidden deck/Prize cards."""
    player = my_state(obs)
    for card in (player.hand or ()):
        if card is not None:
            yield card
    for card in (player.discard or ()):
        if card is not None:
            yield card
    for pokemon in list(player.active or ()) + list(player.bench or ()):
        if pokemon is None:
            continue
        yield pokemon
        for name in ("energyCards", "tools", "preEvolution"):
            for card in (getattr(pokemon, name, None) or ()):
                if card is not None:
                    yield card


def _h3_public_count(obs, card_id):
    serials = {
        _h3_serial(card)
        for card in _h3_public_own_cards(obs)
        if getattr(card, "id", None) == card_id
        and _h3_serial(card) is not None
    }
    return len(serials)


def _h3_access_probability(deck_count, prize_count, unseen_copies):
    if not all(
        isinstance(value, int) and value >= 0
        for value in (deck_count, prize_count, unseen_copies)
    ):
        return None
    hidden_positions = deck_count + prize_count
    if unseen_copies <= 0 or unseen_copies > hidden_positions:
        return 0.0
    if deck_count <= 0:
        return 0.0
    if unseen_copies > prize_count:
        return 1.0
    return 1.0 - (
        math.comb(prize_count, unseen_copies)
        / math.comb(hidden_positions, unseen_copies)
    )


def _h3_duraludon_access(obs):
    player = my_state(obs)
    public_count = _h3_public_count(obs, DURALUDON)
    unseen = _H3_DURALUDON_COPIES - public_count
    deck_count = getattr(player, "deckCount", None)
    prize_count = _h3_prize_count(player)
    known_access = any(
        card is not None and card.id == DURALUDON
        for card in (getattr(obs.current, "looking", None) or ())
    )
    probability = (
        1.0
        if known_access
        else _h3_access_probability(deck_count, prize_count, unseen)
    )
    return {
        "public_count": public_count,
        "unseen": unseen,
        "deck_count": deck_count,
        "prize_count": prize_count,
        "known_access": known_access,
        "probability": probability,
    }


def _h3_metal_supply(obs):
    player = my_state(obs)
    public_count = _h3_public_count(obs, METAL_ENERGY)
    unseen = _H3_METAL_COPIES - public_count
    prize_count = _h3_prize_count(player)
    lower_bound = max(0, unseen - prize_count)
    return {
        "public_count": public_count,
        "unseen": unseen,
        "prize_count": prize_count,
        "deck_lower_bound": lower_bound,
    }


def _h3_option_key(obs, option):
    card = option_card(obs, option)
    target = option_target(obs, option)
    return (
        int(option.type),
        getattr(card, "id", -1) if card is not None else -1,
        _h3_serial(card) if card is not None else -1,
        getattr(option, "attackId", None)
        if getattr(option, "attackId", None) is not None
        else -1,
        getattr(target, "id", -1) if target is not None else -1,
        _h3_serial(target) if target is not None else -1,
    )


def _h3_option_signature(obs):
    return tuple(sorted(_h3_option_key(obs, option) for option in obs.select.option))


def _h3_matching_options(
    obs,
    option_type=None,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    positions = []
    for position, option in enumerate(obs.select.option):
        if option_type is not None and option.type != option_type:
            continue
        if attack_id is not None and option.attackId != attack_id:
            continue
        card = option_card(obs, option)
        if card_id is not None and (card is None or card.id != card_id):
            continue
        if serial is not None and (
            card is None or _h3_serial(card) != serial
        ):
            continue
        if target_serial is not None:
            target = option_target(obs, option)
            direct = card is not None and _h3_serial(card) == target_serial
            attached = target is not None and _h3_serial(target) == target_serial
            if not (direct or attached):
                continue
        positions.append(position)
    return positions


def _h3_lowest_semantic_position(obs, positions):
    if not positions:
        return None
    return min(
        positions,
        key=lambda position: (
            _h3_option_key(obs, obs.select.option[position]),
            position,
        ),
    )


def _h3_unique_public_serials(obs):
    seen = set()
    for card in _h3_public_own_cards(obs):
        serial = _h3_serial(card)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
    opponent = opp_state(obs)
    for pokemon in list(opponent.active or ()) + list(opponent.bench or ()):
        if pokemon is None:
            continue
        serial = _h3_serial(pokemon)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
        for name in ("energyCards", "tools", "preEvolution"):
            for card in (getattr(pokemon, name, None) or ()):
                serial = _h3_serial(card)
                if serial is None or serial in seen:
                    return False
                seen.add(serial)
    return True


def _h3_attack_energy_ready(pokemon, attack):
    cards = [
        card
        for card in (getattr(pokemon, "energyCards", None) or ())
        if card is not None
    ]
    available = [card.id for card in cards]
    colored = [energy for energy in (attack.energies or ()) if energy != 0]
    for required in colored:
        if required not in available:
            return False
        available.remove(required)
    colorless = sum(1 for energy in (attack.energies or ()) if energy == 0)
    return len(available) >= colorless


def _h3_card_damage_modifier_unknown(pokemon):
    if pokemon is None:
        return True
    if getattr(pokemon, "tools", None):
        return True
    data = CARD_DB.get(pokemon.id)
    if data is None:
        return True
    for skill in (getattr(data, "skills", None) or ()):
        text = (getattr(skill, "text", "") or "").lower()
        if any(
            marker in text
            for marker in (
                "prevent all damage",
                "takes less damage",
                "takes no damage",
                "damage done to this pok",
                "flip a coin",
            )
        ):
            return True
    return False


def _h3_turbo_damage(obs, target):
    if target is None or _h3_stadium_fingerprint(obs):
        return None
    if _h3_card_damage_modifier_unknown(target):
        return None
    attack = ALL_ATTACKS.get(_H3_TURBO_FLARE)
    attacker_data = CARD_DB.get(CINDERACE)
    target_data = CARD_DB.get(target.id)
    if (
        attack is None
        or attacker_data is None
        or target_data is None
        or not isinstance(getattr(attack, "damage", None), int)
    ):
        return None
    damage = attack.damage
    attack_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(target_data, "resistance", None)
    resistance = getattr(resistance, "value", resistance)
    if weakness == attack_type:
        damage *= 2
    if resistance == attack_type:
        damage = max(0, damage - 20)
    return damage


def _h3_boss_is_safe(obs):
    opponent = opp_state(obs)
    targets = [
        pokemon
        for pokemon in list(opponent.active or ()) + list(opponent.bench or ())
        if pokemon is not None
    ]
    serials = [_h3_serial(pokemon) for pokemon in targets]
    if (
        not targets
        or any(serial is None for serial in serials)
        or len(serials) != len(set(serials))
    ):
        return False
    # Controlling amendment: every legal current target must fail all exact
    # same-turn KO/Prize/match/parent-finishing conversions.
    for target in targets:
        damage = _h3_turbo_damage(obs, target)
        if damage is None or damage >= target.hp:
            return False
    return True


def _h3_safe_discard_pair(obs, ultra_serial):
    player = my_state(obs)
    active = active_pokemon(obs)
    if active is None or active.hp != active.maxHp:
        return None
    if not _h3_boss_is_safe(obs):
        return None
    ice = sorted(
        (
            _h3_card_key(card),
            card,
        )
        for card in (player.hand or ())
        if card is not None
        and card.id == JUMBO_ICE_CREAM
        and _h3_serial(card) != ultra_serial
    )
    bosses = sorted(
        (
            _h3_card_key(card),
            card,
        )
        for card in (player.hand or ())
        if card is not None
        and card.id == BOSS
        and _h3_serial(card) != ultra_serial
    )
    if not ice or not bosses:
        return None
    pairs = []
    for _, ice_card in ice:
        for _, boss_card in bosses:
            semantic = tuple(sorted(
                (_h3_card_key(ice_card), _h3_card_key(boss_card))
            ))
            pairs.append((semantic, (ice_card, boss_card)))
    pairs.sort(key=lambda item: item[0])
    return pairs[0][1]


def _h3_has_harmful_public_spread(obs):
    opponent = opp_state(obs)
    active = opponent.active[0] if opponent.active else None
    if active is None:
        return True
    data = CARD_DB.get(active.id)
    if data is None:
        return True
    for attack_id in (getattr(data, "attacks", None) or ()):
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return True
        if not _h3_attack_energy_ready(active, attack):
            continue
        text = (getattr(attack, "text", "") or "").lower()
        if "bench" in text and (
            "damage" in text or "damage counter" in text
        ):
            return True
    return False


def _h3_turbo_is_deterministic(obs):
    player = my_state(obs)
    active = active_pokemon(obs)
    if (
        active is None
        or active.id != CINDERACE
        or any(_h3_player_conditions(player))
        or getattr(active, "tools", None)
        or _h3_stadium_fingerprint(obs)
    ):
        return False
    attack = ALL_ATTACKS.get(_H3_TURBO_FLARE)
    if attack is None:
        return False
    text = (getattr(attack, "text", "") or "").lower()
    if "coin" in text or "random" in text:
        return False
    return bool(_h3_matching_options(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=_H3_TURBO_FLARE,
    ))


def _h3_hand_contains(obs, card_id, serial):
    return any(
        card is not None
        and card.id == card_id
        and _h3_serial(card) == serial
        for card in (my_state(obs).hand or ())
    )


def _h3_discard_contains(obs, card_id, serial):
    return any(
        card is not None
        and card.id == card_id
        and _h3_serial(card) == serial
        for card in (my_state(obs).discard or ())
    )


def _h3_bench_pokemon(obs, card_id, serial):
    for pokemon in (my_state(obs).bench or ()):
        if (
            pokemon is not None
            and pokemon.id == card_id
            and _h3_serial(pokemon) == serial
        ):
            return pokemon
    return None


def _h3_protected_hand_valid(obs, transaction):
    visible = {
        _h3_card_key(card)
        for card in (my_state(obs).hand or ())
        if card is not None
    }
    return all(
        protected in visible
        for protected in transaction["protected_hand"]
    )


def _h3_log_matches(
    obs,
    log_type,
    player_index,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    for entry in obs.logs:
        if entry.type != log_type:
            continue
        if getattr(entry, "playerIndex", None) != player_index:
            continue
        if card_id is not None and getattr(entry, "cardId", None) != card_id:
            continue
        if serial is not None and getattr(entry, "serial", None) != serial:
            continue
        if attack_id is not None and getattr(entry, "attackId", None) != attack_id:
            continue
        if (
            target_serial is not None
            and getattr(entry, "serialTarget", None) != target_serial
        ):
            continue
        return True
    return False


def _h3_base_valid(obs, transaction, after_attack=False):
    if (
        obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or tuple(
            _h3_prize_count(player)
            for player in obs.current.players
        ) != transaction["prize_counts"]
        or _h3_pokemon_fingerprint(active_pokemon(obs), True)
        != transaction["cinderace"]
        or _h3_stadium_fingerprint(obs) != transaction["stadium"]
        or not _h3_protected_hand_valid(obs, transaction)
    ):
        return False
    if after_attack:
        opponent = opp_state(obs)
        active = opponent.active[0] if opponent.active else None
        before = transaction["opponent"]
        if (
            _h3_pokemon_fingerprint(active, False) != before["active_static"]
            or active is None
            or active.hp != before["active_hp"] - transaction["turbo_damage"]
            or tuple(
                _h3_pokemon_fingerprint(pokemon, True)
                for pokemon in (opponent.bench or ())
                if pokemon is not None
            ) != before["bench"]
            or _h3_player_conditions(opponent) != before["conditions"]
        ):
            return False
    else:
        if _h3_opponent_fingerprint(obs, True) != transaction[
            "opponent_full"
        ]:
            return False
    return True


def _h3_build_certificate(obs):
    if (
        obs.select.context != SelectContext.MAIN
        or obs.current.result not in (-1, None)
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
    ):
        return None
    player = my_state(obs)
    opponent = opp_state(obs)
    active = active_pokemon(obs)
    if (
        active is None
        or active.id != CINDERACE
        or len([p for p in (player.active or ()) if p is not None]) != 1
        or any(p is not None for p in (player.bench or ()))
        or len(player.bench or ()) >= getattr(player, "benchMax", 0)
        or player.hand is None
        or not _h3_unique_public_serials(obs)
        or any(_h3_player_conditions(player))
    ):
        return None
    if any(
        card.id == DURALUDON
        for card in (player.hand or ())
        if card is not None
    ):
        return None
    if not _h3_turbo_is_deterministic(obs):
        return None
    opponent_active = opp_active_pokemon(obs)
    turbo_damage = _h3_turbo_damage(obs, opponent_active)
    if (
        turbo_damage is None
        or opponent_active is None
        or turbo_damage >= opponent_active.hp
        or _h3_has_harmful_public_spread(obs)
    ):
        return None
    ultra_options = _h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=ULTRA_BALL,
    )
    if not ultra_options:
        return None
    ultra_position = min(
        ultra_options,
        key=lambda position: (
            _h3_serial(option_card(obs, obs.select.option[position])),
            position,
        ),
    )
    ultra_card = option_card(obs, obs.select.option[ultra_position])
    ultra_serial = _h3_serial(ultra_card)
    if ultra_serial is None:
        return None
    access = _h3_duraludon_access(obs)
    if (
        access["probability"] is None
        or access["probability"] < _H3_ACCESS_THRESHOLD
    ):
        return None
    metal = _h3_metal_supply(obs)
    if metal["deck_lower_bound"] < 3:
        return None
    pair = _h3_safe_discard_pair(obs, ultra_serial)
    if pair is None:
        return None
    discard_cards = tuple(sorted(
        (_h3_card_key(card) for card in pair),
    ))
    consumed_serials = {ultra_serial} | {
        serial for _, serial in discard_cards
    }
    protected = tuple(sorted(
        _h3_card_key(card)
        for card in (player.hand or ())
        if card is not None and _h3_serial(card) not in consumed_serials
    ))
    opponent_active = opponent.active[0] if opponent.active else None
    transaction = {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "prize_counts": tuple(
            _h3_prize_count(state)
            for state in obs.current.players
        ),
        "cinderace": _h3_pokemon_fingerprint(active, True),
        "cinderace_serial": _h3_serial(active),
        "ultra_serial": ultra_serial,
        "discard_cards": discard_cards,
        "protected_hand": protected,
        "deck_count": player.deckCount,
        "prize_count": _h3_prize_count(player),
        "duraludon_public_count": access["public_count"],
        "duraludon_unseen": access["unseen"],
        "duraludon_known_access": access["known_access"],
        "duraludon_probability": access["probability"],
        "metal_public_count": metal["public_count"],
        "metal_unseen": metal["unseen"],
        "metal_lower_bound": metal["deck_lower_bound"],
        "opponent_full": _h3_opponent_fingerprint(obs, True),
        "opponent": {
            "active_static": _h3_pokemon_fingerprint(
                opponent_active, False
            ),
            "active_hp": opponent_active.hp,
            "bench": tuple(
                _h3_pokemon_fingerprint(pokemon, True)
                for pokemon in (opponent.bench or ())
                if pokemon is not None
            ),
            "conditions": _h3_player_conditions(opponent),
        },
        "turbo_damage": turbo_damage,
        "stadium": _h3_stadium_fingerprint(obs),
        "option_signature": _h3_option_signature(obs),
        "reserved_duraludon_serial": None,
        "metal_serials": (),
    }
    return transaction, [ultra_position]


def _h3_arm_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.MAIN
        or not _h3_base_valid(obs, transaction, False)
        or _h3_option_signature(obs) != transaction["option_signature"]
        or not _h3_hand_contains(
            obs, ULTRA_BALL, transaction["ultra_serial"]
        )
    ):
        return False
    return bool(_h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=ULTRA_BALL,
        serial=transaction["ultra_serial"],
    ))


def _h3_ultra_confirmed(obs, transaction):
    effect = getattr(obs.select, "effect", None)
    return (
        effect is not None
        and effect.id == ULTRA_BALL
        and _h3_serial(effect) == transaction["ultra_serial"]
        and _h3_log_matches(
            obs,
            LogType.PLAY,
            transaction["seat"],
            ULTRA_BALL,
            transaction["ultra_serial"],
        )
    )


def _h3_discard_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.DISCARD
        or obs.select.minCount != 2
        or obs.select.maxCount != 2
        or not _h3_base_valid(obs, transaction, False)
        or not _h3_ultra_confirmed(obs, transaction)
    ):
        return False
    return all(
        _h3_hand_contains(obs, card_id, serial)
        for card_id, serial in transaction["discard_cards"]
    )


def _h3_discard_action(obs, transaction):
    action = []
    for card_id, serial in transaction["discard_cards"]:
        positions = _h3_matching_options(
            obs,
            option_type=OptionType.CARD,
            card_id=card_id,
            serial=serial,
        )
        if not positions:
            return None
        action.append(min(positions))
    if len(action) != 2 or len(set(action)) != 2:
        return None
    return action


def _h3_discards_confirmed(obs, transaction):
    return all(
        _h3_discard_contains(obs, card_id, serial)
        and _h3_log_matches(
            obs,
            LogType.MOVE_CARD,
            transaction["seat"],
            card_id,
            serial,
        )
        for card_id, serial in transaction["discard_cards"]
    )


def _h3_discards_present(obs, transaction):
    return all(
        _h3_discard_contains(obs, card_id, serial)
        for card_id, serial in transaction["discard_cards"]
    )


def _h3_search_callback_valid(obs, transaction):
    return (
        obs.select.context == SelectContext.TO_HAND
        and obs.select.minCount == 0
        and obs.select.maxCount >= 1
        and _h3_base_valid(obs, transaction, False)
        and _h3_discards_confirmed(obs, transaction)
        and getattr(obs.select, "effect", None) is not None
        and obs.select.effect.id == ULTRA_BALL
        and _h3_serial(obs.select.effect) == transaction["ultra_serial"]
    )


def _h3_search_action(obs, transaction):
    matches = []
    for position in _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=DURALUDON,
    ):
        card = option_card(obs, obs.select.option[position])
        serial = _h3_serial(card)
        if serial is not None:
            matches.append((serial, position))
    if not matches:
        if obs.select.minCount == 0:
            _h3_reset()
            return []
        return None
    if transaction["reserved_duraludon_serial"] is None:
        serial, position = min(matches)
        transaction["reserved_duraludon_serial"] = serial
        return [position]
    positions = [
        position
        for serial, position in matches
        if serial == transaction["reserved_duraludon_serial"]
    ]
    return [min(positions)] if positions else None


def _h3_duraludon_hand_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    return (
        serial is not None
        and obs.select.context == SelectContext.MAIN
        and _h3_base_valid(obs, transaction, False)
        and _h3_discards_present(obs, transaction)
        and _h3_hand_contains(obs, DURALUDON, serial)
        and _h3_log_matches(
            obs,
            LogType.MOVE_CARD,
            transaction["seat"],
            DURALUDON,
            serial,
        )
        and not any(p is not None for p in (my_state(obs).bench or ()))
    )


def _h3_play_duraludon_action(obs, transaction):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=DURALUDON,
        serial=transaction["reserved_duraludon_serial"],
    )
    position = _h3_lowest_semantic_position(obs, positions)
    return [position] if position is not None else None


def _h3_duraludon_bench_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    bench = [
        pokemon
        for pokemon in (my_state(obs).bench or ())
        if pokemon is not None
    ]
    return (
        serial is not None
        and obs.select.context == SelectContext.MAIN
        and _h3_base_valid(obs, transaction, False)
        and len(bench) == 1
        and bench[0].id == DURALUDON
        and _h3_serial(bench[0]) == serial
        and not (getattr(bench[0], "energyCards", None) or ())
        and _h3_log_matches(
            obs,
            LogType.PLAY,
            transaction["seat"],
            DURALUDON,
            serial,
        )
    )


def _h3_turbo_action(obs):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=_H3_TURBO_FLARE,
    )
    return [min(positions)] if positions else None


def _h3_attack_effect_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    bench = [
        pokemon
        for pokemon in (my_state(obs).bench or ())
        if pokemon is not None
    ]
    effect = getattr(obs.select, "effect", None)
    return (
        obs.select.context == SelectContext.ATTACH_TO
        and obs.select.minCount == 0
        and obs.select.maxCount >= 1
        and _h3_base_valid(obs, transaction, True)
        and len(bench) == 1
        and bench[0].id == DURALUDON
        and _h3_serial(bench[0]) == serial
        and not (getattr(bench[0], "energyCards", None) or ())
        and effect is not None
        and effect.id == CINDERACE
        and _h3_serial(effect) == transaction["cinderace_serial"]
        and _h3_log_matches(
            obs,
            LogType.ATTACK,
            transaction["seat"],
            attack_id=_H3_TURBO_FLARE,
        )
    )


def _h3_metal_action(obs, transaction):
    matches = {}
    for position in _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=METAL_ENERGY,
    ):
        card = option_card(obs, obs.select.option[position])
        serial = _h3_serial(card)
        if serial is not None:
            matches.setdefault(serial, []).append(position)
    count = min(3, obs.select.maxCount, len(matches))
    if count < 3 or obs.select.minCount > count:
        return None
    if not transaction["metal_serials"]:
        transaction["metal_serials"] = tuple(sorted(matches)[:count])
    serials = transaction["metal_serials"]
    if len(serials) != count or any(serial not in matches for serial in serials):
        return None
    return [min(matches[serial]) for serial in serials]


def _h3_target_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.ATTACH_FROM
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or not _h3_base_valid(obs, transaction, True)
    ):
        return False
    serial = transaction["reserved_duraludon_serial"]
    pokemon = _h3_bench_pokemon(obs, DURALUDON, serial)
    context_card = getattr(obs.select, "contextCard", None)
    effect = getattr(obs.select, "effect", None)
    if (
        pokemon is None
        or context_card is None
        or context_card.id != METAL_ENERGY
        or effect is None
        or effect.id != CINDERACE
        or _h3_serial(effect) != transaction["cinderace_serial"]
    ):
        return False
    attached = {
        _h3_serial(card)
        for card in (getattr(pokemon, "energyCards", None) or ())
        if card is not None and card.id == METAL_ENERGY
    }
    selected = transaction["metal_serials"]
    prefix = 0
    while prefix < len(selected) and selected[prefix] in attached:
        prefix += 1
    if any(serial in attached for serial in selected[prefix + 1:]):
        return False
    if attached != set(selected[:prefix]) or prefix >= len(selected):
        return False
    if _h3_serial(context_card) != selected[prefix]:
        return False
    for index, previous in enumerate(selected[:prefix]):
        if not _h3_log_matches(
            obs,
            LogType.ATTACH,
            transaction["seat"],
            METAL_ENERGY,
            previous,
            target_serial=serial,
        ) and previous not in attached:
            return False
    return True


def _h3_target_action(obs, transaction):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=DURALUDON,
        serial=transaction["reserved_duraludon_serial"],
        target_serial=transaction["reserved_duraludon_serial"],
    )
    return [min(positions)] if positions else None


def _h3_choose(obs):
    global _h3_transaction
    if _h3_transaction is None:
        built = _h3_build_certificate(obs)
        if built is None:
            return None
        _h3_transaction, action = built
        return action

    transaction = _h3_transaction
    stage = transaction["stage"]
    action = None

    if stage == "ARMED":
        if _h3_arm_callback_valid(obs, transaction):
            positions = _h3_matching_options(
                obs,
                option_type=OptionType.PLAY,
                card_id=ULTRA_BALL,
                serial=transaction["ultra_serial"],
            )
            action = [min(positions)] if positions else None
        elif _h3_discard_callback_valid(obs, transaction):
            transaction["stage"] = "DISCARD_PAIR"
            action = _h3_discard_action(obs, transaction)
    elif stage == "DISCARD_PAIR":
        if _h3_discard_callback_valid(obs, transaction):
            action = _h3_discard_action(obs, transaction)
        elif _h3_search_callback_valid(obs, transaction):
            transaction["stage"] = "SEARCH_DURALUDON"
            action = _h3_search_action(obs, transaction)
    elif stage == "SEARCH_DURALUDON":
        if _h3_search_callback_valid(obs, transaction):
            action = _h3_search_action(obs, transaction)
        elif _h3_duraludon_hand_valid(obs, transaction):
            transaction["stage"] = "DURALUDON_IN_HAND"
            action = _h3_play_duraludon_action(obs, transaction)
    elif stage == "DURALUDON_IN_HAND":
        if _h3_duraludon_hand_valid(obs, transaction):
            action = _h3_play_duraludon_action(obs, transaction)
        elif _h3_duraludon_bench_valid(obs, transaction):
            transaction["stage"] = "DURALUDON_BENCHED"
            action = _h3_turbo_action(obs)
    elif stage == "DURALUDON_BENCHED":
        if _h3_duraludon_bench_valid(obs, transaction):
            action = _h3_turbo_action(obs)
        elif _h3_attack_effect_valid(obs, transaction):
            transaction["stage"] = "SELECT_METALS"
            action = _h3_metal_action(obs, transaction)
    elif stage == "SELECT_METALS":
        if _h3_attack_effect_valid(obs, transaction):
            action = _h3_metal_action(obs, transaction)
        elif _h3_target_callback_valid(obs, transaction):
            transaction["stage"] = "TARGET_METALS"
            action = _h3_target_action(obs, transaction)
    elif stage == "TARGET_METALS":
        if _h3_target_callback_valid(obs, transaction):
            action = _h3_target_action(obs, transaction)

    if action is None:
        _h3_reset()
        return None
    return action


def _h3_observation_boundary(obs):
    global _h3_last_seat, _h3_last_turn
    seat = obs.current.yourIndex
    turn = obs.current.turn
    if _h3_transaction is not None:
        transaction = _h3_transaction
        result_seen = (
            obs.current.result not in (-1, None)
            or any(entry.type == LogType.RESULT for entry in obs.logs)
        )
        own_turn_end = any(
            entry.type == LogType.TURN_END
            and getattr(entry, "playerIndex", transaction["seat"])
            == transaction["seat"]
            for entry in obs.logs
        )
        unexpected_attack = any(
            entry.type == LogType.ATTACK
            and getattr(entry, "playerIndex", None) == transaction["seat"]
            and (
                entry.attackId != _H3_TURBO_FLARE
                or transaction["stage"] not in {
                    "DURALUDON_BENCHED",
                    "SELECT_METALS",
                    "TARGET_METALS",
                }
            )
            for entry in obs.logs
        )
        if (
            seat != transaction["seat"]
            or turn != transaction["turn"]
            or result_seen
            or own_turn_end
            or unexpected_attack
        ):
            _h3_reset()
    if (
        _h3_last_seat is not None
        and (seat != _h3_last_seat or turn < _h3_last_turn)
    ):
        _h3_reset()
    _h3_last_seat = seat
    _h3_last_turn = turn


def _h3_safe_choose(obs):
    try:
        return _h3_choose(obs)
    except Exception:
        _h3_reset()
        return None


def _first_option_index(obs, card_id):
    for o in obs.select.option:
        oc = option_card(obs, o)
        if oc and oc.id == card_id:
            return getattr(o, 'index', None)
    return None


# ── Attack routes ──

def direct_attack_energy_route(obs, pokemon):
    e = energy_count(pokemon)
    if e >= 3:
        return True, False
    if e == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def can_evolve_to_archaludon_now(pokemon, obs):
    if pokemon is None or pokemon.id != DURALUDON:
        return False
    if ARCHALUDON_EX not in hand_ids(obs):
        return False
    return not getattr(pokemon, "appearThisTurn", True)


def alloy_attack_energy_route(obs, pokemon):
    if not can_evolve_to_archaludon_now(pokemon, obs):
        return False, False
    current = energy_count(pokemon)
    alloy = min(2, metal_in_discard(obs))
    total = current + alloy
    if total >= 3:
        return True, False
    if total == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def attack_energy_route(obs, pokemon):
    if pokemon is None:
        return False, False
    if pokemon.id == ARCHALUDON:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == ARCHALUDON_EX:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == DURALUDON:
        ok, uses_attach = direct_attack_energy_route(obs, pokemon)
        if ok:
            return True, uses_attach
        return alloy_attack_energy_route(obs, pokemon)
    return False, False


def archaludon_ex_attack_route(obs):
    active = active_pokemon(obs)
    if active and active.id in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
        ok, uses_attach = attack_energy_route(obs, active)
        if ok:
            return {"attacker": active, "uses_attach": uses_attach, "needs_retreat": False}

    if active is None or obs.current.retreated or energy_count(active) < retreat_cost(active):
        return None
    ps = my_state(obs)
    for pokemon in [p for p in ps.bench if p]:
        if pokemon.id not in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
            continue
        ok, uses_attach = attack_energy_route(obs, pokemon)
        if ok:
            return {"attacker": pokemon, "uses_attach": uses_attach, "needs_retreat": True}
    return None


def planned_archaludon_attacks(obs):
    route = archaludon_ex_attack_route(obs)
    if route is None:
        return []
    attacker = route["attacker"]
    attacks = []
    if attacker.id == ARCHALUDON:
        attacks.append({"damage": 120})
    if attacker.id == ARCHALUDON_EX:
        attacks.append({"damage": 220})
        if has_in_play(obs, RELICANTH):
            attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
    if attacker.id == DURALUDON:
        attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
        if can_evolve_to_archaludon_now(attacker, obs):
            attacks.append({"damage": 220})
    return attacks


# ── Matchup detection & opponent max damage ──

ALAKAZAM_LINE = {741, 742, 743}
IONO_LINE = {265, 268, 269, 270, 271}
KETCHUM_ALAKAZAM_MARKERS = {1246, 1247}
LIVE_ALAKAZAM_MARKERS = {1264, 858, 174}
ARCHALUDON_LINE = {169, 190, 840}
_ALA_BOARD_GAIN = {66: 3, 742: 2, 305: 2, 65: 2, 741: 1}  # Dudunsparce, Kadabra, Dunsparce×2, Abra


def _estimate_alakazam_from_pokes(opp, pokes):
    """(floor, ceiling, ceiling_with_boss) damage from visible Alakazam line."""
    ids = [p.id for p in pokes if p]
    if not (ALAKAZAM_LINE & set(ids)):
        return 0, 0, 0
    base = opp.handCount + 1
    gain = sum(_ALA_BOARD_GAIN.get(i, 0) for i in ids)
    enriching_seen = (
        any(c and c.id == 13 for c in (opp.discard or []))
        or any(c and c.id == 13 for p in pokes if p for c in (getattr(p, "energyCards", None) or []))
    )
    if not enriching_seen:
        gain += 3
    if any(i == 140 for i in ids):
        gain += 3
    return base * 20, (base + gain + 2) * 20, (base + gain - 1) * 20


def _estimate_alakazam(obs):
    """(floor, ceiling, ceiling_with_boss) damage from Powerful Hand."""
    opp = opp_state(obs)
    pokes = ([opp.active[0]] if opp.active else []) + list(opp.bench or [])
    return _estimate_alakazam_from_pokes(opp, pokes)


def detect_matchup(obs):
    opp = opp_state(obs)
    ids = {p.id for p in (opp.active + opp.bench) if p}
    if ids & (CRUSTLE_LINE | GREAT_TUSK_LINE):
        return "crustle"
    if ids & OGERPON_LINE:
        return "ogerpon"
    if ids & HOP_LINE:
        return "hop"
    if ids & STARMIE_LINE:
        return "starmie"
    if ids & LUCARIO_LINE:
        return "lucario"
    if ids & CHANDELURE_LINE:
        return "chandelure"
    if ids & ALAKAZAM_LINE:
        return "alakazam"
    if ids & IONO_LINE:
        return "iono"
    if ids & ARCHALUDON_LINE:
        return "archaludon"
    return "generic"


def opp_max_damage(obs):
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        _, ceiling, _ = _estimate_alakazam(obs)
        return ceiling
    if matchup == "crustle":
        return 120
    if matchup == "ogerpon":
        return 180
    if matchup == "hop":
        return 220
    if matchup == "lucario":
        return 270  # Mega Brave base. PPP adds +30 each but unpredictable
    if matchup == "starmie":
        return 210
    if matchup == "chandelure":
        return max(60, 20 * int(getattr(my_state(obs), "handCount", 0) or 0))
    return 220


# ── Overrides ──

def apply_overrides(obs, opt, score, reason):
    # Hard rule: don't Explorer with low deck
    if opt.type == OptionType.PLAY:
        card = option_card(obs, opt)
        cid = card.id if card else None
        if detect_matchup(obs) == "chandelure" and my_state(obs).deckCount <= 25 and cid == EXPLORER:
            return -5000, "Chandelure: don't Explorer near deckout"
        if my_state(obs).deckCount <= 10 and cid == EXPLORER:
            return -5000, "hard: don't Explorer with low deck"

    if detect_matchup(obs) == "ogerpon":
        card = option_card(obs, opt)
        cid = card.id if card else getattr(opt, 'cardId', None)
        ctx = obs.select.context
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        cornerstone_seen = 117 in opp_ids

        opp_act = opp_active_pokemon(obs)
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX and opp_act and opp_act.id == 117:
            return -10000, "Ogerpon: don't evolve into Ability attacker"
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON:
            return max(score, 30000), "Ogerpon: evolve to non-Ability Archaludon"
        if cornerstone_seen and opt.type == OptionType.ATTACK:
            aid = getattr(opt, 'attackId', None)
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            if active and active.id == ARCHALUDON and opp_act and opp_act.id == 117 and aid == COATED_ATTACK:
                return max(score, 28000), "Ogerpon: Coated Attack Cornerstone"
            if active and active.id == ARCHALUDON_EX and opp_act and opp_act.id == 117 and aid == METAL_DEFENDER:
                return -5000, "Ogerpon: Metal Defender blocked"
            if active and active.id == DURALUDON and aid == RAGING_HAMMER:
                return max(score, 25000), "Ogerpon: Duraludon Raging Hammer"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
            return -3000, "Ogerpon: skip Archaludon ex"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON:
            return 25000, "Ogerpon: take non-Ability Archaludon"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON_EX:
            return 9000, "Ogerpon: discard Archaludon ex"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON:
            return -5000, "Ogerpon: keep non-Ability Archaludon"

    if detect_matchup(obs) != "crustle":
        return score, reason

    # Crustle overrides
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, 'cardId', None)
    ctx = obs.select.context

    if opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX:
        return -10000, "Crustle: don't evolve to ex"

    if opt.type == OptionType.ATTACK:
        aid = getattr(opt, 'attackId', None)
        active = active_pokemon(obs)
        opp_act = opp_active_pokemon(obs)
        opp_has_spiky = bool(opp_act and any(
            getattr(c, 'id', None) == 14
            for c in (getattr(opp_act, 'energyCards', None) or [])))
        if (active and active.id == DURALUDON and active.hp == 130
                and opp_act and opp_act.id == 345 and energy_count(opp_act) >= 2
                and opp_has_spiky):
            return -3000, "Crustle: full HP Duraludon waits out Spiky"
        if aid == METAL_DEFENDER:
            return -5000, "Crustle: Metal Defender does 0"
        if aid == RAGING_HAMMER:
            rh_dmg = 80 + damage_on(active_pokemon(obs)) // 10 * 10
            return max(score, 200), "Crustle: Raging Hammer"

    if opt.type == OptionType.PLAY:
        if cid == RELICANTH:
            return -5000, "Crustle: skip Relicanth"
        dc = my_state(obs).deckCount
        hc = my_state(obs).handCount
        line_count = (
            count_in_play(obs, DURALUDON)
            + count_in_play(obs, ARCHALUDON)
            + count_in_play(obs, ARCHALUDON_EX)
        )
        has_stable_attacker = any(
            p and p.id in {DURALUDON, ARCHALUDON, ARCHALUDON_EX} and energy_count(p) >= 3
            for p in all_my_pokemon(obs)
        )
        if cid == LILLIE and dc <= 16:
            if hc > 6:
                return 18000 + min(5000, (hc - 6) * 1000), "Crustle: Lillie refills low deck"
            if dc <= 10:
                return -5000, "Crustle: skip Lillie with low deck and small hand"
        if cid in (POKE_PAD, POKEGEAR) and (dc <= 18 or has_stable_attacker):
            return -5000, "Crustle: preserve deck, skip search item"
        if cid == EXPLORER and (dc <= 24 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
            return -5000, "Crustle: preserve deck, skip Explorer"
        if cid == ULTRA_BALL and dc <= 18 and line_count >= 2:
            return -3000, "Crustle: preserve deck, skip Ultra Ball"
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        if opp_ids & GREAT_TUSK_LINE:
            if cid == LILLIE and dc <= 38:
                if hc > 6:
                    return 17000 + min(5000, (hc - 6) * 1000), "Great Tusk: Lillie refills deck earlier"
                return -5000, "Great Tusk: skip Lillie with low deck and small hand"
            if cid in (POKE_PAD, POKEGEAR) and (dc <= 30 or has_stable_attacker):
                return -5000, "Great Tusk: preserve deck, skip search item"
            if cid == EXPLORER and (dc <= 40 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
                return -5000, "Great Tusk: preserve deck, skip Explorer"
            if cid == ULTRA_BALL and dc <= 34 and line_count >= 2:
                return -3000, "Great Tusk: preserve deck, skip Ultra Ball"
        if dc <= 10 and cid in (EXPLORER, LILLIE):
            if cid == LILLIE and dc <= 3 and my_state(obs).handCount >= dc + 6:
                return 15000, "Crustle: Lillie to refill deck"
            return -5000, "Crustle: don't draw with low deck"
        if cid == LILLIE:
            has_metal = any(c and c.id == METAL_ENERGY for c in (my_state(obs).hand or []) if c)
            if not has_metal:
                return score, "Crustle: Lillie OK (no energy in hand)"

    if opt.type == OptionType.ATTACH:
        target = option_target(obs, opt)
        tid = target.id if target else None
        if getattr(opt, 'inPlayArea', None) == AreaType.BENCH and tid == DURALUDON:
            return score + 10000, "Crustle: bench Duraludon energy priority"
        if getattr(opt, 'inPlayArea', None) == AreaType.ACTIVE:
            active = active_pokemon(obs)
            if active and energy_count(active) >= 2:
                return score + 3000, "Crustle: Active 3rd energy"

    if ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
        return -3000, "Crustle: skip Archaludon ex"

    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        if cid == ARCHALUDON_EX and score < 0:
            return 9000, "Crustle: discard Archaludon ex"

    return score, reason


# ── Scoring ──

def score_setup(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ctx = obs.select.context

    if ctx == SelectContext.MULLIGAN:
        return (10000, "no mulligan") if opt.type == OptionType.NO else (0, "mulligan")
    if ctx == SelectContext.IS_FIRST:
        return (10000, "choose second") if opt.type == OptionType.NO else (0, "go first")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        return _SETUP_ACTIVE_PRIORITY.get(cid, (0, "unknown Active"))
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        return -10000, "never bench during setup"
    return 0, "non-setup"


# HP threshold per matchup: skip Ice Cream if HP > this value
_ICE_CREAM_HP_THRESHOLD = {
    "lucario": 270,
    "starmie": 210,
    "crustle": 120,
    "hop": 220,
    "generic": 230,
}


def should_skip_ice_cream(obs, active):
    """Decide whether to skip Jumbo Ice Cream. Returns (skip: bool, reason: str)."""
    # 1. Active must be Archaludon ex
    if active.id != ARCHALUDON_EX:
        return True, "skip Ice Cream: not Archaludon ex"
    # 2. Raging Hammer KO guard: don't heal if it loses a KO (but 220 Metal Defender still KOs → heal OK)
    opp_act = opp_active_pokemon(obs)
    if opp_act and has_in_play(obs, RELICANTH):
        md_kills = effective_damage(220, opp_act) >= opp_act.hp
        if not md_kills:
            rh_dmg = 80 + damage_on(active) // 10 * 10
            rh_after = 80 + max(0, damage_on(active) - 80) // 10 * 10
            if effective_damage(rh_dmg, opp_act) >= opp_act.hp and effective_damage(rh_after, opp_act) < opp_act.hp:
                return True, "skip Ice Cream: healing loses Raging Hammer KO"
    # 3. Alakazam: all-or-nothing Ice Cream decision
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        floor, ceiling, _ = _estimate_alakazam(obs)
        opp_a = opp_active_pokemon(obs)
        attacks = planned_archaludon_attacks(obs)
        if opp_a and attacks and any(effective_damage(a["damage"], opp_a) >= opp_a.hp for a in attacks):
            _, ceiling, _ = _estimate_alakazam_from_pokes(opp_state(obs), opp_bench_pokemon(obs))
        ice_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id == JUMBO_ICE_CREAM)
        max_hp = getattr(active, "maxHp", active.hp)
        hp_after_all = min(max_hp, active.hp + ice_count * 80)
        if hp_after_all <= active.hp:
            return True, "skip Ice Cream: no effective healing"
        if hp_after_all < floor:
            return True, f"skip Ice Cream: even {ice_count}x heal ({hp_after_all}) < floor {floor}"
        if hp_after_all >= ceiling:
            return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) >= ceil {ceiling}"
        return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) between floor={floor} ceil={ceiling}"
    # 4. HP above matchup threshold
    threshold = _ICE_CREAM_HP_THRESHOLD.get(matchup, 220)
    if active.hp > threshold:
        return True, f"skip Ice Cream: HP {active.hp} > {threshold} ({matchup})"
    # 5. Use it
    return False, ""


ITEMS = {POKE_PAD, ULTRA_BALL, POKEGEAR, NIGHT_STRETCHER, JUMBO_ICE_CREAM, HERO_CAPE}


def score_play(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ids = hand_ids(obs)

    # ── Pokemon: bench if available ──
    if cid in {DURALUDON, RELICANTH}:
        return 18000, "play Pokemon"

    # ── Stadium ──
    if cid == FULL_METAL_LAB:
        active = active_pokemon(obs)
        if active and active.id not in {DURALUDON, ARCHALUDON_EX}:
            return -200, "skip FML: Active not Metal"
        return 20000, "play Full Metal Lab"

    # ── Items: default 20000, only negative exceptions ──
    if cid in ITEMS:
        if cid == HERO_CAPE:
            if not any(p.id in {ARCHALUDON_EX, DURALUDON} and not has_tool(p) for p in all_my_pokemon(obs)):
                return -500, "save Hero's Cape: no target"
        if cid == JUMBO_ICE_CREAM:
            active = active_pokemon(obs)
            if active:
                skip, reason = should_skip_ice_cream(obs, active)
                if skip:
                    return -500, reason
        if cid == NIGHT_STRETCHER:
            disc = discard_ids(obs)
            line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
            mirror_rebuild = detect_matchup(obs) == "archaludon" and (
                (DURALUDON in disc and DURALUDON not in ids and line_count <= 2)
                or (
                    ARCHALUDON_EX in disc
                    and ARCHALUDON_EX not in ids
                    and has_in_play(obs, DURALUDON)
                    and count_in_play(obs, ARCHALUDON_EX) <= 1
                )
            )
            has_urgent = (
                (DURALUDON in disc and DURALUDON not in ids and count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX) <= 1)
                or (ARCHALUDON_EX in disc and ARCHALUDON_EX not in ids and has_in_play(obs, DURALUDON))
                or (METAL_ENERGY in disc and not obs.current.energyAttached
                    and sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY) == 0
                    and any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) == 2 for p in all_my_pokemon(obs)))
                or mirror_rebuild
            )
            if not has_urgent:
                return -500, "save Night Stretcher"
        if cid == ULTRA_BALL:
            bench_empty = len([p for p in my_state(obs).bench if p]) == 0
            if bench_empty:
                return 300, "Ultra Ball: bench empty (donk risk)"
            metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_in_trash = metal_in_discard(obs)
            if metal_in_trash == 0 and metal_in_hand >= 1:
                return 20000, "Ultra Ball: fuel Alloy"
            if safe_discard_count(obs) >= 2 and (need_archaludon(obs) or need_duraludon(obs)):
                return 20000, "Ultra Ball: search line"
            return -1000, "skip Ultra Ball"
        return 20000, "play item"

    if cid == EXPLORER:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 16000, "play Explorer"

    if cid == LILLIE:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "chandelure":
            dc = my_state(obs).deckCount
            if dc <= 8 and my_state(obs).handCount >= dc + 6:
                return 26000, "Chandelure: Lillie refills low deck"
        if detect_matchup(obs) == "chandelure" and my_state(obs).handCount >= 7:
            return 17500, "Chandelure: Lillie lowers Mind Ruler damage"
        if BOSS in ids and planned_archaludon_attacks(obs):
            return -500, "save Lillie: Boss in hand with attacker ready"
        return 5000, "play Lillie"

    if cid == BOSS:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "ogerpon":
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            if attacks and opp_act and opp_act.id == 117:
                if any(p.id != 117 for p in opp_bench_pokemon(obs)):
                    return 26000, "Boss: bypass Cornerstone Ogerpon"
        # vs Hop: Boss Snorlax to remove Extra Helpings (+30) ASAP
        if detect_matchup(obs) == "hop":
            active = active_pokemon(obs)
            opp_has_snorlax = any(p.id == HOP_SNORLAX for p in opp_bench_pokemon(obs))
            if opp_has_snorlax and active:
                # Case 1: Cinderace active + bench has Duraludon → Turbo Flare Snorlax
                if active.id == CINDERACE:
                    has_dura_bench = any(p.id in {DURALUDON, ARCHALUDON_EX}
                                        for p in my_state(obs).bench if p)
                    if has_dura_bench:
                        return 16500, "Boss: pull Snorlax (Cinderace Turbo Flare)"
                # Case 2: Archaludon active, HP > 220, can attack → Boss Snorlax
                if active.id == ARCHALUDON_EX and active.hp > 220:
                    ok, _ = attack_energy_route(obs, active)
                    if ok:
                        return 16500, "Boss: pull Snorlax (Arch can tank Revenge 220)"
        if detect_matchup(obs) == "archaludon":
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            can_ko_active = opp_act and any(
                effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
            remaining = len(my_state(obs).prize)
            if active and attacks and not can_ko_active:
                lethal_bench = any(
                    prize_value(target) >= remaining
                    and any(effective_damage(atk["damage"], target) >= target.hp for atk in attacks)
                    for target in opp_bench_pokemon(obs)
                )
                relcanth_ko = any(
                    p.id == RELICANTH
                    and any(effective_damage(atk["damage"], p) >= p.hp for atk in attacks)
                    for p in opp_bench_pokemon(obs)
                )
                if relcanth_ko and not lethal_bench:
                    return 15500, "Boss: remove mirror Relicanth"
        if _opp_last_attack_id == MEGA_BRAVE:
            return -500, "save Boss: Mega Brave stuck"
        attacks = planned_archaludon_attacks(obs)
        if not attacks:
            return -500, "save Boss: no attacker"
        opp_act = opp_active_pokemon(obs)
        can_ko_active = opp_act and any(
            effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
        remaining = len(my_state(obs).prize)
        if can_ko_active:
            if prize_value(opp_act) >= remaining:
                return -500, "save Boss: Active KO wins"
            for target in opp_bench_pokemon(obs):
                for atk in attacks:
                    if effective_damage(atk["damage"], target) >= target.hp:
                        if prize_value(target) >= remaining:
                            return 20000, "LETHAL Boss"
                        break
            return -500, "save Boss: can KO Active"
        best_score = -500
        best_reason = "save Boss"
        for target in opp_bench_pokemon(obs):
            for atk in attacks:
                if effective_damage(atk["damage"], target) >= target.hp:
                    pv = prize_value(target)
                    if pv >= remaining:
                        return 20000, "LETHAL Boss"
                    s = 4000 + pv * 200 + energy_count(target) * 100
                    if s > best_score:
                        best_score = s
                        best_reason = "Boss: pull bench target"
                    break
        if best_score <= 0:
            metal_total = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_total += sum(energy_count(p) for p in all_my_pokemon(obs) if p)
            has_cind = has_in_play(obs, CINDERACE)
            draw_in_hand = any(c and c.id in (EXPLORER, LILLIE) for c in (my_state(obs).hand or []) if c)
            if metal_total <= 2 and not has_cind and not draw_in_hand:
                best_stall = -500
                stall_reason = "save Boss"
                for target in opp_bench_pokemon(obs):
                    te = energy_count(target)
                    cd = CARD_DB.get(target.id)
                    rc = cd.retreatCost if cd else 0
                    min_atk = 99
                    if cd and cd.attacks:
                        for aid in cd.attacks:
                            atk = ALL_ATTACKS.get(aid)
                            if atk:
                                min_atk = min(min_atk, len(atk.energies))
                    if min_atk == 99:
                        min_atk = 1
                    ss = 4000 + rc * 1000 + min_atk * 500 - te * 800
                    if ss > best_stall:
                        best_stall = ss
                        stall_reason = "Boss stall"
                return best_stall, stall_reason
        return best_score, best_reason

    return 1000, "generic play"


def score_evolve(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None
    if cid == ARCHALUDON and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            if target and energy_count(target) >= 3:
                return 32000, "Endgame: evolve ready non-ex Archaludon"
            return 24000, "Endgame: evolve non-ex prize wall"
        if detect_matchup(obs) == "ogerpon":
            if target and energy_count(target) >= 3:
                return 30000, "Ogerpon: evolve non-ex Archaludon ready"
            return 18000, "Ogerpon: evolve non-ex Archaludon"
        return -1000, "hold non-ex Archaludon outside Ogerpon"
    if cid == ARCHALUDON_EX and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            return -8000, "Endgame: avoid final-prize ex evolve"
        target_is_active = opt.inPlayArea == AreaType.ACTIVE
        mc = metal_in_discard(obs)
        if target_is_active:
            if (
                detect_matchup(obs) == "lucario"
                and target.hp <= 70
                and any(p and p.id == DURALUDON for p in my_state(obs).bench)
            ):
                return 6000, "Lucario: preserve low-HP active, evolve bench"
            if energy_count(target) >= 3 and not has_in_play(obs, ARCHALUDON_EX):
                return 17000, "evolve Active 3-energy Duraludon"
            if mc >= 2:
                return 28000 + mc * 2000, "evolve Active Duraludon"
            if mc == 1:
                return 8000, "delay Active evolve: 1 Metal"
            return -500, "hold: no Metal in discard"
        if mc >= 2:
            return 14000 + mc * 1000, "evolve Bench Duraludon"
        return -1000, "hold: evolve Active first"
    return 10000, "generic evolution"


def attach_target_score(obs, target, area):
    if target is None:
        return 0
    cid = target.id
    e = energy_count(target)

    if e >= 3:
        return -5000
    if cid == CINDERACE and e >= 1:
        return -3000

    score = 0
    if cid == CINDERACE:
        score = 3000
        if e == 0:
            score += 7000 + (12000 if area == AreaType.ACTIVE else 5000)
    elif cid in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
        score = 6000 if cid == ARCHALUDON_EX else 5500
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            score += 5000
        score += {2: 12000, 1: 7000, 0: 4000}.get(e, -1000)
        score += 1000 if area == AreaType.ACTIVE else 500
    else:
        score = 1000 + (1000 if e == 0 else 0)

    # HP-based adjustment
    if target.hp > 0:
        max_hp = getattr(target, "maxHp", target.hp)
        ratio = target.hp / max_hp if max_hp > 0 else 1
        if ratio <= 0.25:
            score -= 1500
        elif ratio <= 0.50:
            score -= 500
        else:
            score += min(1000, target.hp // 40 * 100)
    return score


def score_attach(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None

    if cid == HERO_CAPE:
        if tid == ARCHALUDON_EX and target and not has_tool(target):
            return 11000, "Hero's Cape on Archaludon ex"
        if tid == DURALUDON and target and not has_tool(target) and energy_count(target) >= 1:
            return 8000, "Hero's Cape on Duraludon"
        return -1000, "save Hero's Cape"

    if cid != METAL_ENERGY:
        return -500, "skip non-Metal"
    if obs.current.energyAttached:
        return -1000, "already attached"

    return attach_target_score(obs, target, opt.inPlayArea), "attach Metal"


def score_retreat(obs, opt):
    active = active_pokemon(obs)
    if active and active.id == ARCHALUDON_EX and has_tool(active) and active.hp > 200:
        return -5000, "don't retreat HP400 tank"
    route = archaludon_ex_attack_route(obs)
    if route and route["needs_retreat"]:
        return 13000, "retreat to attack-ready ex"
    return -100, "avoid retreat"


_MAIN_DISPATCH = {
    OptionType.PLAY: score_play, OptionType.EVOLVE: score_evolve,
    OptionType.ATTACH: score_attach, OptionType.RETREAT: score_retreat,
}


def score_option(obs, opt):
    ctx = obs.select.context

    if ctx in {SelectContext.IS_FIRST, SelectContext.MULLIGAN,
               SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return score_setup(obs, opt)

    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.IS_FIRST:
            return score_setup(obs, opt)
        if ctx == SelectContext.ACTIVATE:
            return (100000, "Explosiveness") if opt.type == OptionType.YES else (-100000, "never decline")
        return (1, "yes") if opt.type == OptionType.YES else (0, "no")

    if opt.type == OptionType.NUMBER:
        return (opt.number or 0), "number"

    if ctx == SelectContext.MAIN:
        fn = _MAIN_DISPATCH.get(opt.type)
        if fn:
            score, reason = fn(obs, opt)
        elif opt.type == OptionType.ABILITY:
            score, reason = 1, "ability"
        elif opt.type == OptionType.ATTACK:
            score, reason = best_attack_damage(obs, opt.attackId), "attack"
        elif opt.type == OptionType.END:
            score, reason = 0, "end turn"
        else:
            score, reason = 500, "generic MAIN"
    elif ctx == SelectContext.TO_HAND:
        score, reason = score_to_hand(obs, opt)
    elif ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        score, reason = score_discard(obs, opt)
    elif ctx in {SelectContext.ATTACH_TO, SelectContext.TO_FIELD, SelectContext.TO_BENCH,
                 SelectContext.ATTACH_FROM, SelectContext.SWITCH, SelectContext.TO_ACTIVE,
                 SelectContext.HEAL, SelectContext.DAMAGE}:
        score, reason = score_target(obs, opt)
    elif ctx == SelectContext.ATTACK:
        score, reason = best_attack_damage(obs, opt.attackId), "attack"
    elif opt.type == OptionType.CARD:
        score, reason = score_to_hand(obs, opt)
    elif opt.type == OptionType.ENERGY:
        score, reason = 1000, "energy"
    elif opt.type == OptionType.END:
        score, reason = 0, "end"
    else:
        score, reason = 100, "fallback"

    return apply_overrides(obs, opt, score, reason)


def score_to_hand(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if effect_id == EXPLORER:
        has_ready = any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) >= 3
                        for p in all_my_pokemon(obs))
        metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)

        if cid == HERO_CAPE:
            has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
            return (27000 if has_target else 22000), "Explorer: Hero's Cape"
        if cid == METAL_ENERGY:
            if has_ready or metal_in_hand > 0:
                return 0, "Explorer: skip energy"
            if getattr(opt, 'index', 0) == _first_option_index(obs, METAL_ENERGY):
                return 25000, "Explorer: take 1st energy"
            return 0, "Explorer: skip 2nd energy"
        if cid == ARCHALUDON_EX and need_archaludon(obs):
            return 20000, "Explorer: take Archaludon ex"
        if cid == ARCHALUDON and need_nonex_archaludon(obs):
            return 19000, "Explorer: take non-ex Archaludon"
        if cid == DURALUDON and need_duraludon(obs):
            return 18000, "Explorer: take Duraludon"
        if cid == RELICANTH and not has_in_play(obs, RELICANTH) and RELICANTH not in ids:
            return 15000, "Explorer: take Relicanth"
        sup_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id in (EXPLORER, LILLIE))
        if cid in (EXPLORER, LILLIE) and sup_count == 0:
            return 12000, "Explorer: take supporter"
        return 0, "Explorer: let discard"

    if effect_id == NIGHT_STRETCHER and detect_matchup(obs) == "archaludon":
        line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
        if cid == ARCHALUDON_EX and has_in_play(obs, DURALUDON) and count_in_play(obs, ARCHALUDON_EX) <= 1:
            return 24000, "Stretcher mirror: take Archaludon ex"
        if cid == DURALUDON and DURALUDON not in ids and line_count <= 2:
            return 23000, "Stretcher mirror: take Duraludon"
        if cid == METAL_ENERGY:
            return 9000, "Stretcher mirror: take Metal fallback"

    dura_ex_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
    if cid == DURALUDON and DURALUDON not in ids and dura_ex_count <= 1:
        return 22000, "take Duraludon: backup"
    if cid == ARCHALUDON and need_nonex_archaludon(obs):
        return 21000, "take non-ex Archaludon"
    if cid == ARCHALUDON_EX and need_archaludon(obs):
        return 20000, "take Archaludon ex"
    if cid == DURALUDON and need_duraludon(obs):
        return 18000, "take Duraludon"
    if cid == CINDERACE:
        return -2000, "skip Cinderace"
    if cid == RELICANTH and not has_in_play(obs, RELICANTH):
        return 9000, "take Relicanth"
    if cid == METAL_ENERGY:
        return 8000, "take Metal Energy"
    if cid == EXPLORER and not obs.current.supporterPlayed:
        return 7500, "take Explorer"
    if cid == LILLIE and not obs.current.supporterPlayed:
        return 6500, "take Lillie"
    if cid == HERO_CAPE:
        has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
        return (6000, "take Hero's Cape") if has_target else (1000, "generic take")
    if cid == FULL_METAL_LAB:
        return 5000, "take Full Metal Lab"
    if cid == BOSS:
        return 2500, "take Boss"
    return 1000, "generic take"


def score_discard(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if effect_id == ULTRA_BALL:
        mh = ids.count(METAL_ENERGY)
        if cid == METAL_ENERGY:
            if mt < 2 and mh >= 1:
                if getattr(opt, 'index', None) == _first_option_index(obs, METAL_ENERGY):
                    return 20000, "UB: 1st Metal"
                return 8000, "UB: 2nd Metal"
            return 8000, "UB: Metal"
        if cid == CINDERACE:
            return (18000, "UB: Cinderace") if (mt >= 2 or mh == 0) else (14000, "UB: Cinderace")
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return -5000, "UB: keep non-ex Archaludon"
        draw_count = ids.count(LILLIE) + ids.count(EXPLORER)
        if cid in (LILLIE, EXPLORER) and draw_count >= 2:
            return (12000 if cid == LILLIE else 11000), "UB: surplus supporter"
        if cid == ULTRA_BALL and ids.count(ULTRA_BALL) > 1:
            return 10000, "UB: duplicate"
        if cid in (LILLIE, EXPLORER) and draw_count <= 1:
            return -3000, "UB: keep last supporter"

    if cid == METAL_ENERGY:
        if mt < 2:
            return 15000, "discard Metal"
        return (12000, "discard extra Metal") if ids.count(METAL_ENERGY) > 1 else (-1000, "keep last Metal")
    if cid == CINDERACE:
        return 10000, "discard Cinderace"
    if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
        return -5000, "keep non-ex Archaludon"
    if cid in {BOSS, FULL_METAL_LAB, POKEGEAR}:
        return 8500, "discard utility"
    if cid in {LILLIE, EXPLORER} and ids.count(cid) > 1:
        return 8000, "discard duplicate supporter"
    if cid == RELICANTH and (has_in_play(obs, RELICANTH) or ids.count(RELICANTH) > 1):
        return 6500, "discard extra Relicanth"
    if cid == ARCHALUDON_EX:
        return -5000, "keep Archaludon ex"
    if cid == DURALUDON:
        return -4000, "keep Duraludon"
    return 1000, "generic discard"


def score_target(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ctx = obs.select.context

    if ctx == SelectContext.ATTACH_TO:
        return (5000, "Metal") if cid == METAL_ENERGY else (1000, "attach")

    if ctx == SelectContext.ATTACH_FROM:
        if card and energy_count(card) >= 3:
            return -5000, "skip: 3+ energy"
        if card and cid == CINDERACE and energy_count(card) >= 1:
            return -3000, "skip: Cinderace ready"
        return attach_target_score(obs, card, opt.area), "effect attach"

    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return 20000, "target non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 18000, "target Archaludon ex"
        if cid == DURALUDON:
            return 16000, "target Duraludon"
        if cid == CINDERACE:
            return 3000, "avoid Cinderace"

    if ctx == SelectContext.HEAL:
        return (20000 + damage_on(card), "heal Archaludon ex") if cid == ARCHALUDON_EX else (damage_on(card), "heal")

    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        yi = obs.current.yourIndex
        pi = getattr(opt, 'playerIndex', yi)
        if pi != yi and card:
            if detect_matchup(obs) == "archaludon" and cid == RELICANTH:
                killable = any(effective_damage(a["damage"], card) >= card.hp
                               for a in planned_archaludon_attacks(obs))
                if killable:
                    return 22500 + energy_count(card) * 100, "Boss: mirror Relicanth"
            if detect_matchup(obs) == "ogerpon":
                if cid == 117:
                    return -2000, "Boss: avoid Cornerstone blocker"
                priority = {
                    1051: 36000,
                    112: 34000,
                    675: 33000,
                    676: 33000,
                    116: 32000,
                    1052: 30000,
                }.get(cid, 22000)
                return priority - card.hp + energy_count(card) * 300, "Boss: Ogerpon non-blocker"
            # vs Hop: prioritize Snorlax (remove Extra Helpings)
            if detect_matchup(obs) == "hop" and cid == HOP_SNORLAX and card:
                active = active_pokemon(obs)
                e = energy_count(card)
                tools = len(getattr(card, 'tools', None) or [])
                if active and active.id == CINDERACE:
                    # Cinderace: pull the least mobile Snorlax (low energy, no tools, high HP)
                    return 30000 - e * 100 - tools * 50 + card.hp, "Boss: Snorlax (immobile target)"
                else:
                    # Archaludon: pull the most threatening Snorlax (high energy, tools, high HP)
                    return 30000 + e * 100 + tools * 50 + card.hp, "Boss: Snorlax (biggest threat)"
            pv = prize_value(card)
            te = energy_count(card)
            killable = any(effective_damage(a["damage"], card) >= card.hp
                           for a in planned_archaludon_attacks(obs))
            if killable:
                return 20000 + pv * 3000 + te * 100, "Boss: KO"
            return 5000 + pv * 1000 + te * 200, "Boss: drag"
        if cid == CINDERACE:
            return 16000, "promote Cinderace (retreat 0)"
        if cid == ARCHALUDON:
            return 15500, "promote non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 15000, "promote Archaludon ex"
        if cid == DURALUDON:
            return 8000, "promote Duraludon"
        return 1000, "generic promote"

    if ctx == SelectContext.DAMAGE:
        hp = getattr(card, "hp", 999) if card else 999
        return 10000 - hp, "damage: lowest HP"

    return 1000, "generic target"


# ── Choose & Agent ──

def choose_options(obs):
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as e:
            score, reason = -999999, f"error {type(e).__name__}: {e}"
        scored.append((score, i, reason))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    selected = []
    for score, i, reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)

    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[:obs.select.minCount]]

    return selected


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs, _h3_last_seat, _h3_last_turn
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _h3_reset()
        _h3_last_seat = None
        _h3_last_turn = None
        return read_deck_csv()
    _h3_observation_boundary(obs)
    _update_opp_attack_tracking(obs)
    try:
        h3_action = _h3_safe_choose(obs)
        if h3_action is not None:
            return h3_action
        if not obs.select.option:
            return []
        return choose_options(obs)
    except Exception:
        _h3_reset()
        return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)
