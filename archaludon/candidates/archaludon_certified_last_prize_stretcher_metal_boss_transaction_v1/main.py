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

# H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS transaction.  The snapshot is
# public-only and owns exactly six semantic choices:
# Stretcher -> Metal -> attach -> Boss -> target -> Metal Defender.
_h2_transaction = None
_h2_last_seat = None
_h2_last_turn = None


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


def _h2_reset():
    global _h2_transaction
    _h2_transaction = None


def _h2_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None


def _h2_card_fingerprint(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h2_serial(card))


def _h2_pokemon_fingerprint(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h2_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", pokemon.hp),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(int(e) for e in (getattr(pokemon, "energies", None) or ())),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "energyCards", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "tools", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "preEvolution", None) or ())),
            key=repr,
        )),
    )


def _h2_pokemon_static_fingerprint(pokemon):
    fingerprint = _h2_pokemon_fingerprint(pokemon)
    if fingerprint is None:
        return None
    return fingerprint[:5] + fingerprint[7:]


def _h2_board_fingerprint(player):
    pokes = ([player.active[0]] if player.active else []) + list(player.bench or ())
    return tuple(sorted(
        (_h2_pokemon_fingerprint(pokemon) for pokemon in pokes if pokemon),
        key=repr,
    ))


def _h2_stadium_fingerprint(obs):
    return tuple(_h2_card_fingerprint(c) for c in (obs.current.stadium or ()))


def _h2_conditions(player):
    return (
        bool(player.poisoned),
        bool(player.burned),
        bool(player.asleep),
        bool(player.paralyzed),
        bool(player.confused),
    )


def _h2_visible_cards(obs):
    for player in obs.current.players:
        for card in (player.hand or ()):
            if card:
                yield card
        for card in (player.discard or ()):
            if card:
                yield card
        for card in (player.prize or ()):
            if card:
                yield card
        for pokemon in (
                ([player.active[0]] if player.active else [])
                + list(player.bench or ())):
            if pokemon is None:
                continue
            yield pokemon
            for card in (getattr(pokemon, "energyCards", None) or ()):
                if card:
                    yield card
            for card in (getattr(pokemon, "tools", None) or ()):
                if card:
                    yield card
            for card in (getattr(pokemon, "preEvolution", None) or ()):
                if card:
                    yield card
    for card in (obs.current.stadium or ()):
        if card:
            yield card


def _h2_visible_serial_is_unique(obs, serial):
    if serial is None:
        return False
    return sum(1 for card in _h2_visible_cards(obs)
               if _h2_serial(card) == serial) == 1


def _h2_energy_ready_types(energies, attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return False
    available = [int(e) for e in (energies or ())]
    required = [int(e) for e in (getattr(attack, "energies", None) or ())]
    for energy_type in [value for value in required if value != 0]:
        match = next(
            (i for i, value in enumerate(available)
             if value in {energy_type, 10}),
            None,
        )
        if match is None:
            return False
        available.pop(match)
    return len(available) >= sum(1 for value in required if value == 0)


def _h2_energy_ready(pokemon, attack_id):
    return pokemon is not None and _h2_energy_ready_types(
        getattr(pokemon, "energies", None) or (),
        attack_id,
    )


def _h2_exactly_one_metal_short(active):
    if active is None:
        return False
    energies = tuple(int(e) for e in (getattr(active, "energies", None) or ()))
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    required = tuple(int(e) for e in (getattr(attack, "energies", None) or ()))
    return (
        required == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and len(energies) == 2
        and not _h2_energy_ready_types(energies, METAL_DEFENDER)
        and _h2_energy_ready_types(energies + (METAL_ENERGY,), METAL_DEFENDER)
    )


def _h2_basic_metal(card):
    data = CARD_DB.get(getattr(card, "id", None))
    return (
        card is not None
        and card.id == METAL_ENERGY
        and data is not None
        and int(getattr(data, "cardType", -1)) == 5
        and int(getattr(data, "energyType", -1)) == METAL_ENERGY
        and _h2_serial(card) is not None
    )


def _h2_known_tools_only(pokemon):
    # Hero's Cape is fully reflected by public hp/maxHp.  Any other Tool fails
    # closed because its damage, immunity, or attack-legality effect may matter.
    return all(getattr(tool, "id", None) == HERO_CAPE
               for tool in (getattr(pokemon, "tools", None) or ()))


def _h2_known_stadium(obs):
    stadium = list(obs.current.stadium or ())
    return len(stadium) <= 1 and (
        not stadium or stadium[0].id == FULL_METAL_LAB
    )


def _h2_has_public_damage_protection(pokemon):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    if data is None:
        return True
    for skill in (getattr(data, "skills", None) or ()):
        text = (getattr(skill, "text", "") or "").lower()
        if (
            ("prevent" in text and "damage" in text)
            or ("takes " in text and "less damage" in text)
            or "reduce damage" in text
            or "reduced by" in text
            or "isn't affected" in text
            or "not affected by" in text
        ):
            return True
    return False


def _h2_metal_defender_damage(obs, target):
    """Exact public Metal Defender damage, or None when v1 must fail closed."""
    if (
        target is None
        or not _h2_known_stadium(obs)
        or not _h2_known_tools_only(target)
        or _h2_has_public_damage_protection(target)
    ):
        return None
    data = CARD_DB.get(target.id)
    if data is None or int(getattr(data, "cardType", -1)) != 0:
        return None
    damage = int(getattr(ALL_ATTACKS.get(METAL_DEFENDER), "damage", 0) or 0)
    if damage != 220:
        return None
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def _h2_visible_prize_value(pokemon):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    if data is None or int(getattr(data, "cardType", -1)) != 0:
        return None
    if getattr(data, "megaEx", False):
        return 3
    if getattr(data, "ex", False):
        return 2
    return 1


def _h2_active_attack_is_certain(obs, active):
    mine = my_state(obs)
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    if (
        active is None
        or attack is None
        or active.id != ARCHALUDON_EX
        or _h2_serial(active) is None
        or not getattr(active, "preEvolution", None)
        or not _h2_known_tools_only(active)
        or mine.asleep is not False
        or mine.paralyzed is not False
        or mine.confused is not False
    ):
        return False
    attack_text = (getattr(attack, "text", "") or "").lower()
    if "flip a coin" in attack_text or "can't use" in attack_text:
        return False
    if _opp_last_attack_id is not None:
        previous = ALL_ATTACKS.get(_opp_last_attack_id)
        previous_text = (getattr(previous, "text", "") or "").lower()
        if (
            "opponent" in previous_text
            and (
                "can't attack" in previous_text
                or "cannot attack" in previous_text
                or "flip a coin" in previous_text
            )
        ):
            return False
    return True


def _h2_play_options(obs, card_id, required_serial=None):
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        serial = _h2_serial(card)
        if card and card.id == card_id and serial is not None:
            if required_serial is None or serial == required_serial:
                choices.append((i, serial))
    return choices


def _h2_recovery_option_indices(obs, metal_serial):
    yi = obs.current.yourIndex
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        pi = option.playerIndex if option.playerIndex is not None else yi
        card = option_card(obs, option)
        if (
            pi == yi
            and option.area == AreaType.DISCARD
            and _h2_basic_metal(card)
            and card.serial == metal_serial
        ):
            choices.append(i)
    return choices


def _h2_attach_option_indices(obs, metal_serial, active_serial):
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.ATTACH:
            continue
        card = option_card(obs, option)
        target = option_target(obs, option)
        if (
            _h2_basic_metal(card)
            and card.serial == metal_serial
            and option.inPlayArea == AreaType.ACTIVE
            and target is not None
            and _h2_serial(target) == active_serial
        ):
            choices.append(i)
    return choices


def _h2_target_option_indices(obs, target_serial):
    yi = obs.current.yourIndex
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        pi = option.playerIndex if option.playerIndex is not None else yi
        card = option_card(obs, option)
        if (
            pi != yi
            and option.area == AreaType.BENCH
            and card is not None
            and _h2_serial(card) == target_serial
        ):
            choices.append(i)
    return choices


def _h2_attack_option_indices(obs, attack_id):
    return [
        i for i, option in enumerate(obs.select.option)
        if option.type == OptionType.ATTACK and option.attackId == attack_id
    ]


def _h2_fixed_attack_damage(obs, target, attack_id):
    active = active_pokemon(obs)
    if active is None or target is None:
        return None
    if attack_id == METAL_DEFENDER:
        return _h2_metal_defender_damage(obs, target)
    if attack_id == RAGING_HAMMER:
        base = 80 + damage_on(active) // 10 * 10
    else:
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        text = (getattr(attack, "text", "") or "").lower()
        if any(marker in text for marker in (
                "more damage", "damage for each", " for each ",
                "damage counter on", "damage counters on", "flip a coin")):
            return None
        base = int(getattr(attack, "damage", 0) or 0)
        if base <= 0:
            return None
    if (
        not _h2_known_stadium(obs)
        or not _h2_known_tools_only(target)
        or _h2_has_public_damage_protection(target)
    ):
        return None
    data = CARD_DB.get(target.id)
    if data is None:
        return None
    damage = base
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def _h2_has_precedent_terminal(obs):
    """Protect an existing immediate win or already-complete Boss route."""
    mine = my_state(obs)
    opp = opp_state(obs)
    if not opp.active:
        return True
    attack_ids = [
        option.attackId for option in obs.select.option
        if option.type == OptionType.ATTACK and option.attackId is not None
    ]
    for attack_id in attack_ids:
        damage = _h2_fixed_attack_damage(obs, opp.active[0], attack_id)
        if damage is not None and damage >= opp.active[0].hp:
            if (
                (_h2_visible_prize_value(opp.active[0]) or 0) >= len(mine.prize)
                or not opp.bench
            ):
                return True
    if _h2_play_options(obs, BOSS) and not obs.current.supporterPlayed:
        for target in (opp.bench or ()):
            if (_h2_visible_prize_value(target) or 0) < len(mine.prize):
                continue
            for attack_id in attack_ids:
                damage = _h2_fixed_attack_damage(obs, target, attack_id)
                if damage is None or damage >= target.hp:
                    return True
    return False


def _h2_build_certificate(obs):
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or getattr(obs.select, "effect", None) is not None
    ):
        return None
    mine = my_state(obs)
    opp = opp_state(obs)
    active = active_pokemon(obs)
    opposing_active = opp_active_pokemon(obs)
    stretcher_options = _h2_play_options(obs, NIGHT_STRETCHER)
    boss_options = _h2_play_options(obs, BOSS)
    if (
        len(mine.prize) != 1
        or obs.current.energyAttached is not False
        or obs.current.supporterPlayed is not False
        or METAL_ENERGY in hand_ids(obs)
        or not stretcher_options
        or not boss_options
        or not _h2_active_attack_is_certain(obs, active)
        or not _h2_exactly_one_metal_short(active)
        or not _h2_known_stadium(obs)
        or opposing_active is None
        or _h2_serial(opposing_active) is None
        or _h2_has_precedent_terminal(obs)
    ):
        return None

    metals = sorted(
        {
            card.serial for card in (mine.discard or ())
            if _h2_basic_metal(card)
            and _h2_visible_serial_is_unique(obs, card.serial)
        }
    )
    if not metals:
        return None

    opposing_damage = _h2_metal_defender_damage(obs, opposing_active)
    opposing_prize = _h2_visible_prize_value(opposing_active)
    if (
        opposing_damage is None
        or opposing_prize is None
        or opposing_damage >= opposing_active.hp
        or not opp.bench
    ):
        return None

    targets = []
    for pokemon in (opp.bench or ()):
        serial = _h2_serial(pokemon)
        prize = _h2_visible_prize_value(pokemon)
        damage = _h2_metal_defender_damage(obs, pokemon)
        if (
            serial is not None
            and _h2_visible_serial_is_unique(obs, serial)
            and prize is not None
            and prize >= len(mine.prize)
            and damage is not None
            and damage >= pokemon.hp
        ):
            targets.append(pokemon)
    target_serials = {pokemon.serial for pokemon in targets}
    if len(target_serials) != 1:
        return None
    target = targets[0]

    stretcher_choice, stretcher_serial = min(
        stretcher_options,
        key=lambda value: (value[1], value[0]),
    )
    boss_choice, boss_serial = min(
        boss_options,
        key=lambda value: (value[1], value[0]),
    )
    for serial in (
        active.serial,
        stretcher_serial,
        boss_serial,
        opposing_active.serial,
        target.serial,
    ):
        if not _h2_visible_serial_is_unique(obs, serial):
            return None

    return {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "prizes": (len(mine.prize), len(opp.prize)),
        "active_before": _h2_pokemon_fingerprint(active),
        "active_static": _h2_pokemon_static_fingerprint(active),
        "active_serial": active.serial,
        "active_conditions": _h2_conditions(mine),
        "stretcher_serial": stretcher_serial,
        "eligible_metal_serials": tuple(metals),
        "metal_serial": metals[0],
        "boss_serial": boss_serial,
        "original_active_serial": opposing_active.serial,
        "original_active": _h2_pokemon_fingerprint(opposing_active),
        "original_active_prize": opposing_prize,
        "target_serial": target.serial,
        "target": _h2_pokemon_fingerprint(target),
        "target_hp": target.hp,
        "target_prize": _h2_visible_prize_value(target),
        "attack_id": METAL_DEFENDER,
        "own_bench": tuple(sorted(
            (_h2_pokemon_fingerprint(p) for p in (mine.bench or ()) if p),
            key=repr,
        )),
        "opponent_board": _h2_board_fingerprint(opp),
        "opponent_hand_count": opp.handCount,
        "opponent_deck_count": opp.deckCount,
        "stadium": _h2_stadium_fingerprint(obs),
        "retreated": bool(obs.current.retreated),
        "stadium_played": bool(obs.current.stadiumPlayed),
        "public_modifiers": (
            _h2_conditions(mine),
            _h2_stadium_fingerprint(obs),
            _h2_pokemon_fingerprint(opposing_active),
            _h2_pokemon_fingerprint(target),
        ),
        "stretcher_choice": stretcher_choice,
        "boss_choice": boss_choice,
    }


def _h2_base_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    return (
        obs.current.yourIndex == transaction["seat"]
        and obs.current.turn == transaction["turn"]
        and obs.current.result == -1
        and (len(mine.prize), len(opp.prize)) == transaction["prizes"]
        and _h2_conditions(mine) == transaction["active_conditions"]
        and tuple(sorted(
            (_h2_pokemon_fingerprint(p) for p in (mine.bench or ()) if p),
            key=repr,
        )) == transaction["own_bench"]
        and _h2_board_fingerprint(opp) == transaction["opponent_board"]
        and opp.handCount == transaction["opponent_hand_count"]
        and opp.deckCount == transaction["opponent_deck_count"]
        and _h2_stadium_fingerprint(obs) == transaction["stadium"]
        and bool(obs.current.retreated) == transaction["retreated"]
        and bool(obs.current.stadiumPlayed) == transaction["stadium_played"]
    )


def _h2_active_valid(obs, transaction, attached):
    active = active_pokemon(obs)
    if (
        active is None
        or _h2_pokemon_static_fingerprint(active) != transaction["active_static"]
    ):
        return False
    if not attached:
        return _h2_pokemon_fingerprint(active) == transaction["active_before"]
    before = transaction["active_before"]
    expected_energies = tuple(sorted(before[5] + (METAL_ENERGY,)))
    actual_energies = tuple(sorted(
        int(e) for e in (getattr(active, "energies", None) or ())
    ))
    expected_cards = tuple(sorted(
        before[6] + ((METAL_ENERGY, transaction["metal_serial"]),),
        key=repr,
    ))
    actual_cards = tuple(sorted(
        (_h2_card_fingerprint(card)
         for card in (getattr(active, "energyCards", None) or ())),
        key=repr,
    ))
    return (
        actual_energies == expected_energies
        and actual_cards == expected_cards
        and _h2_energy_ready(active, transaction["attack_id"])
    )


def _h2_card_in(cards, card_id, serial):
    return any(
        card and card.id == card_id and _h2_serial(card) == serial
        for card in (cards or ())
    )


def _h2_stretcher_confirmed(obs, transaction):
    effect = getattr(obs.select, "effect", None)
    if not (
        obs.select.context == SelectContext.TO_HAND
        and effect is not None
        and effect.id == NIGHT_STRETCHER
        and _h2_serial(effect) == transaction["stretcher_serial"]
    ):
        return False
    logged = any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == NIGHT_STRETCHER
        and entry.serial == transaction["stretcher_serial"]
        for entry in obs.logs
    )
    mine = my_state(obs)
    consumed = (
        not _h2_card_in(mine.hand, NIGHT_STRETCHER, transaction["stretcher_serial"])
        and _h2_card_in(mine.discard, NIGHT_STRETCHER, transaction["stretcher_serial"])
    )
    return logged or consumed


def _h2_metal_recovered(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_card_in(mine.hand, METAL_ENERGY, transaction["metal_serial"])
        and not _h2_card_in(mine.discard, METAL_ENERGY, transaction["metal_serial"])
    )


def _h2_boss_confirmed(obs, transaction):
    logged = any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == BOSS
        and entry.serial == transaction["boss_serial"]
        for entry in obs.logs
    )
    mine = my_state(obs)
    consumed = (
        obs.current.supporterPlayed
        and not _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and _h2_card_in(mine.discard, BOSS, transaction["boss_serial"])
    )
    return logged or consumed


def _h2_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == transaction["attack_id"]
        and entry.serial == transaction["active_serial"]
        for entry in obs.logs
    )


def _h2_pre_stretcher_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.current.turnActionCount == transaction["turn_action_count"]
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and not any(card and card.id == METAL_ENERGY for card in (mine.hand or ()))
        and bool(_h2_play_options(
            obs, NIGHT_STRETCHER, transaction["stretcher_serial"]))
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
    )


def _h2_recovery_callback_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and _h2_stretcher_confirmed(obs, transaction)
        and _h2_card_in(
            mine.discard, METAL_ENERGY, transaction["metal_serial"])
        and bool(_h2_recovery_option_indices(
            obs, transaction["metal_serial"]))
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
    )


def _h2_recovered_state_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.select.context == SelectContext.MAIN
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and _h2_metal_recovered(obs, transaction)
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
        and bool(_h2_attach_option_indices(
            obs,
            transaction["metal_serial"],
            transaction["active_serial"],
        ))
    )


def _h2_attached_state_valid(obs, transaction, require_main):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and (not require_main or obs.select.context == SelectContext.MAIN)
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is False
        and not _h2_card_in(
            mine.hand, METAL_ENERGY, transaction["metal_serial"])
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
    )


def _h2_gust_callback_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    effect = getattr(obs.select, "effect", None)
    target = next(
        (pokemon for pokemon in (opp.bench or ())
         if _h2_serial(pokemon) == transaction["target_serial"]),
        None,
    )
    opposing_active = opp_active_pokemon(obs)
    damage = _h2_metal_defender_damage(obs, target)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and obs.select.context in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is True
        and _h2_boss_confirmed(obs, transaction)
        and (
            effect is None
            or (
                effect.id == BOSS
                and _h2_serial(effect) == transaction["boss_serial"]
            )
        )
        and opposing_active is not None
        and _h2_serial(opposing_active) == transaction["original_active_serial"]
        and target is not None
        and _h2_pokemon_fingerprint(target) == transaction["target"]
        and damage is not None
        and damage >= target.hp
        and bool(_h2_target_option_indices(
            obs, transaction["target_serial"]))
    )


def _h2_target_state_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    target = opp_active_pokemon(obs)
    original = next(
        (pokemon for pokemon in (opp.bench or ())
         if _h2_serial(pokemon) == transaction["original_active_serial"]),
        None,
    )
    damage = _h2_metal_defender_damage(obs, target)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and obs.select.context in {SelectContext.MAIN, SelectContext.ATTACK}
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is True
        and _h2_card_in(mine.discard, BOSS, transaction["boss_serial"])
        and target is not None
        and _h2_pokemon_fingerprint(target) == transaction["target"]
        and original is not None
        and _h2_pokemon_fingerprint(original) == transaction["original_active"]
        and damage is not None
        and damage >= target.hp
        and (_h2_visible_prize_value(target) or 0) >= len(mine.prize)
        and bool(_h2_attack_option_indices(
            obs, transaction["attack_id"]))
    )


def _h2_choose(obs):
    global _h2_transaction
    transaction = _h2_transaction
    if transaction is None:
        certificate = _h2_build_certificate(obs)
        if certificate is None:
            return None
        _h2_transaction = certificate
        choices = _h2_play_options(
            obs, NIGHT_STRETCHER, certificate["stretcher_serial"])
        return [min(i for i, _ in choices)]

    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or _h2_attack_confirmed(obs, transaction)
        or any(
            entry.type == LogType.TURN_END
            and entry.playerIndex == transaction["seat"]
            for entry in obs.logs
        )
    ):
        transaction["stage"] = "DONE"
        _h2_reset()
        return None

    stage = transaction["stage"]
    if stage == "ARMED":
        if _h2_stretcher_confirmed(obs, transaction):
            if not _h2_recovery_callback_valid(obs, transaction):
                _h2_reset()
                return None
            transaction["stage"] = "RECOVERY_SELECT"
            stage = "RECOVERY_SELECT"
        else:
            if not _h2_pre_stretcher_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_play_options(
                obs, NIGHT_STRETCHER, transaction["stretcher_serial"])
            if obs.select.context != SelectContext.MAIN or not choices:
                _h2_reset()
                return None
            return [min(i for i, _ in choices)]

    if stage == "RECOVERY_SELECT":
        if _h2_metal_recovered(obs, transaction):
            transaction["stage"] = "METAL_RECOVERED"
            stage = "METAL_RECOVERED"
        else:
            if not _h2_recovery_callback_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_recovery_option_indices(
                obs, transaction["metal_serial"])
            return [min(choices)]

    if stage == "METAL_RECOVERED":
        if _h2_active_valid(obs, transaction, attached=True):
            transaction["stage"] = "ATTACHED"
            stage = "ATTACHED"
        else:
            if not _h2_recovered_state_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_attach_option_indices(
                obs,
                transaction["metal_serial"],
                transaction["active_serial"],
            )
            return [min(choices)]

    if stage == "ATTACHED":
        if _h2_boss_confirmed(obs, transaction):
            if not _h2_gust_callback_valid(obs, transaction):
                _h2_reset()
                return None
            transaction["stage"] = "GUST_SELECT"
            stage = "GUST_SELECT"
        else:
            if not _h2_attached_state_valid(
                    obs, transaction, require_main=True):
                _h2_reset()
                return None
            choices = _h2_play_options(
                obs, BOSS, transaction["boss_serial"])
            return [min(i for i, _ in choices)]

    if stage == "GUST_SELECT":
        opposing_active = opp_active_pokemon(obs)
        if (
            opposing_active is not None
            and _h2_serial(opposing_active) == transaction["target_serial"]
        ):
            transaction["stage"] = "TARGET_CONFIRMED"
            stage = "TARGET_CONFIRMED"
        else:
            if not _h2_gust_callback_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_target_option_indices(
                obs, transaction["target_serial"])
            return [min(choices)]

    if stage == "TARGET_CONFIRMED":
        if not _h2_target_state_valid(obs, transaction):
            _h2_reset()
            return None
        choices = _h2_attack_option_indices(
            obs, transaction["attack_id"])
        return [min(choices)]

    _h2_reset()
    return None


def _h2_observation_boundary(obs):
    global _h2_last_seat, _h2_last_turn
    seat = obs.current.yourIndex
    turn = obs.current.turn
    transaction = _h2_transaction
    if (
        (_h2_last_seat is not None and seat != _h2_last_seat)
        or (_h2_last_turn is not None and turn != _h2_last_turn)
        or obs.current.result != -1
        or (
            transaction is not None
            and any(
                (
                    entry.type == LogType.TURN_END
                    and entry.playerIndex == transaction["seat"]
                )
                or (
                    entry.type == LogType.ATTACK
                    and entry.playerIndex == transaction["seat"]
                    and entry.attackId == transaction["attack_id"]
                    and entry.serial == transaction["active_serial"]
                )
                or entry.type == LogType.RESULT
                for entry in obs.logs
            )
        )
    ):
        _h2_reset()
    _h2_last_seat = seat
    _h2_last_turn = turn


def _h2_safe_choose(obs):
    try:
        return _h2_choose(obs)
    except Exception:
        _h2_reset()
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
        global _opp_last_attack_id, _cur_turn_logs, _h2_last_seat, _h2_last_turn
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _h2_reset()
        _h2_last_seat = None
        _h2_last_turn = None
        return read_deck_csv()
    _h2_observation_boundary(obs)
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        return []
    try:
        h2_action = _h2_safe_choose(obs)
        if h2_action is not None:
            return h2_action
        return choose_options(obs)
    except Exception:
        _h2_reset()
        return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)
