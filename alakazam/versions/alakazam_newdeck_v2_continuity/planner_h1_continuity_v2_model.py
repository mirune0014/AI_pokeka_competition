"""Pure public-state certificates for V2_CERTIFIED_H1_CONTINUITY."""
from __future__ import annotations
from math import ceil

import planner_deck_adaptation_v1 as v1
import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime
import planner_semantics as semantics

RULE = "V2_CERTIFIED_H1_CONTINUITY"
ABRA, KADABRA, ALAKAZAM = 741, 742, 743
CANDY, STRETCHER, LANA, HILDA = 1079, 1097, 1184, 1225
BASIC, TELEPATH, ENRICHING = 5, 19, 13
POWERFUL_HAND = 1072
PSYCHIC = frozenset((BASIC, TELEPATH))
TOTALS = {ABRA: 4, KADABRA: 4, ALAKAZAM: 4, CANDY: 3, BASIC: 2, TELEPATH: 4}


def card_row(card):
    return model.card_row(card)


def exact_option(option, option_type, **expected):
    return v1._exact_option(option, option_type, **expected)


def census(parent, obs):
    return v1._option_census(parent, obs)


def public_exact(parent, obs):
    try:
        serials = parent._bridge_public_serials(obs.current)
        return (v1._public_state(parent, obs) is not None
                and all(type(s) is int and s > 0 for s in serials)
                and len(serials) == len(set(serials)))
    except (AttributeError, TypeError, ValueError):
        return False


def metadata_exact(parent):
    expected = {
        ABRA: ("Abra", parent.CardType.POKEMON),
        KADABRA: ("Kadabra", parent.CardType.POKEMON),
        ALAKAZAM: ("Alakazam", parent.CardType.POKEMON),
        CANDY: ("Rare Candy", parent.CardType.ITEM),
        STRETCHER: ("Night Stretcher", parent.CardType.ITEM),
        LANA: ("Lana’s Aid", parent.CardType.SUPPORTER),
        HILDA: ("Hilda", parent.CardType.SUPPORTER),
        BASIC: ("Basic {P} Energy", parent.CardType.BASIC_ENERGY),
        TELEPATH: ("Telepath Psychic Energy", parent.CardType.SPECIAL_ENERGY),
    }
    if any(parent.card_table.get(i) is None or
           (parent.card_table[i].name, parent.card_table[i].cardType) != row
           for i, row in expected.items()):
        return False
    return (sum(i == CANDY for i in parent.my_deck) == 3
            and parent.card_table[KADABRA].evolvesFrom == "Abra"
            and parent.card_table[ALAKAZAM].evolvesFrom == "Kadabra"
            and tuple(parent.card_table[ALAKAZAM].attacks) == (POWERFUL_HAND,)
            and len(parent.card_table[CANDY].skills) == 1
            and parent.card_table[CANDY].skills[0].name == "Rare Candy"
            and len(parent.card_table[STRETCHER].skills) == 1
            and parent.card_table[STRETCHER].skills[0].name == "Night Stretcher"
            and len(parent.card_table[HILDA].skills) == 1
            and parent.card_table[HILDA].skills[0].name == "Hilda")


def visible_counts(obs):
    mine = obs.current.players[obs.current.yourIndex]
    if mine.hand is None or len(mine.hand) != mine.handCount:
        return None
    counts = {i: 0 for i in TOTALS}
    def add(card):
        if card.id in counts:
            counts[card.id] += 1
    for card in list(mine.hand) + list(mine.discard):
        add(card)
    for pokemon in list(mine.active) + list(mine.bench):
        add(pokemon)
        for card in list(pokemon.preEvolution) + list(pokemon.energyCards) + list(pokemon.tools):
            add(card)
    return None if any(counts[i] > TOTALS[i] for i in counts) else counts


def resource_intervals(obs):
    counts = visible_counts(obs)
    mine = obs.current.players[obs.current.yourIndex]
    D, P = mine.deckCount, len(mine.prize)
    if counts is None or type(D) is not int or D < 0:
        return None
    result = {}
    for card_id, N in TOTALS.items():
        V = counts[card_id]
        U = N - V
        result[card_id] = {"N": N, "V": V, "D": D, "P": P, "U": U,
                           "deck_lb": max(0, U - P), "deck_ub": min(U, D),
                           "prize_lb": max(0, U - D), "prize_ub": min(U, P)}
    return result


def hand_rows(obs, ids, excluded=()):
    mine = obs.current.players[obs.current.yourIndex]
    excluded = set(excluded)
    return sorted(((c.id, c.serial, c) for c in mine.hand
                   if c.id in ids and c.serial not in excluded),
                  key=lambda row: (row[0], row[1]))


def first_hand(obs, ids, excluded=()):
    rows = hand_rows(obs, set(ids), excluded)
    return rows[0] if rows else None


def attached_psychic(pokemon):
    rows = sorted((c for c in pokemon.energyCards if c.id in PSYCHIC),
                  key=lambda c: c.serial)
    return rows[0] if rows else None


def ready_alakazam(parent, state, pokemon, owner):
    units = semantics.energy_units(parent, pokemon)
    attack = parent.attack_table.get(POWERFUL_HAND)
    return bool(pokemon.id == ALAKAZAM and units is not None and attack is not None
                and not semantics.missing_energy(parent, units, attack.energies)
                and parent._two_prize_lineage_is_complete(pokemon, owner))


def h1_certificate(parent, obs, h0_serial=None):
    """The strongest of the four contract-listed H1 certificate shapes."""
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    energy, ala, candy = (first_hand(obs, PSYCHIC), first_hand(obs, {ALAKAZAM}),
                           first_hand(obs, {CANDY}))
    result = []
    for area, group in ((parent.AreaType.ACTIVE, mine.active),
                        (parent.AreaType.BENCH, mine.bench)):
        for index, pokemon in enumerate(group):
            if pokemon.serial == h0_serial:
                continue
            attached = attached_psychic(pokemon)
            reserves, score, kind = [], 0, None
            if ready_alakazam(parent, obs.current, pokemon, owner):
                score, kind = 40, "ENERGIZED_ALAKAZAM"
            elif pokemon.id == ALAKAZAM and energy:
                score, kind, reserves = 30, "ALAKAZAM_RESERVED_PSYCHIC", [energy]
            elif (pokemon.id == KADABRA and not pokemon.appearThisTurn and ala
                  and (attached or energy)):
                score, kind, reserves = 20, "KADABRA_RESERVED_ALAKAZAM_PSYCHIC", [ala]
                if not attached:
                    reserves.append(energy)
            elif (pokemon.id == ABRA and not pokemon.appearThisTurn and candy and ala
                  and (attached or energy)):
                score, kind, reserves = 10, "OLD_ABRA_CANDY_ALAKAZAM_PSYCHIC", [candy, ala]
                if not attached:
                    reserves.append(energy)
            if kind:
                serials = [pokemon.serial]
                if attached:
                    serials.append(attached.serial)
                serials.extend(row[1] for row in reserves)
                if len(serials) == len(set(serials)):
                    result.append((score, pokemon.serial, {"score": score, "kind": kind,
                        "field_serial": pokemon.serial, "area": area, "index": index,
                        "serials": tuple(serials)}))
    return sorted(result, key=lambda row: (-row[0], row[1]))[0][2] if result else None


def partial_score(parent, obs, h0_serial):
    cert = h1_certificate(parent, obs, h0_serial)
    best = cert["score"] if cert else 0
    for pokemon in obs.current.players[obs.current.yourIndex].bench:
        if pokemon.serial == h0_serial:
            continue
        attached = bool(attached_psychic(pokemon))
        if pokemon.id == ALAKAZAM:
            best = max(best, 25)
        elif pokemon.id == KADABRA:
            best = max(best, 15 + 2 * attached)
        elif pokemon.id == ABRA and not pokemon.appearThisTurn:
            best = max(best, 5 + 2 * attached)
    return best


def safe_draw(obs, count):
    mine = obs.current.players[obs.current.yourIndex]
    return mine.deckCount - count > len(mine.prize)


def option_card(parent, obs, option):
    card = core._option_card(parent, obs, option)
    if card is not None:
        return card
    index = getattr(option, "index", None)
    if (option.type in (parent.OptionType.PLAY, parent.OptionType.EVOLVE, parent.OptionType.ATTACH)
        and getattr(option, "area", None) in (None, parent.AreaType.HAND)
        and type(index) is int and index >= 0):
        hand = obs.current.players[obs.current.yourIndex].hand or []
        return hand[index] if index < len(hand) else None
    return None


def target_pokemon(parent, obs, option):
    return core._target_pokemon(parent, obs, option)


def prep_candidates(parent, obs, h0_serial, hreq, future_delta=0, allow_active=False):
    """Exact one-substep improvements, ordered by resulting readiness."""
    keys = census(parent, obs)
    if keys is None:
        return []
    mine = obs.current.players[obs.current.yourIndex]
    score0, rows = partial_score(parent, obs, h0_serial), []
    allowed_areas = ((parent.AreaType.BENCH, parent.AreaType.ACTIVE) if allow_active
                     else (parent.AreaType.BENCH,))
    def add(index, card, target, score, delta, reason, kind, roles, stage, draw=0):
        hfinal = mine.handCount + delta + future_delta
        serials = tuple(roles)
        if score > score0 and hfinal >= hreq and len(serials) == len(set(serials)):
            rows.append({"action": [index], "key": keys[index], "reason": reason,
                         "kind": kind, "source_row": card_row(card),
                         "source_serial": card.serial,
                         "target_serial": getattr(target, "serial", None),
                         "score": score, "Hfinal": hfinal, "h1_serials": serials,
                         "next_stage": stage, "draw_count": draw})
    for index, option in enumerate(obs.select.option):
        card, target = option_card(parent, obs, option), target_pokemon(parent, obs, option)
        if card is None:
            continue
        if (option.type == parent.OptionType.PLAY and card.id == ABRA
            and len(mine.bench) < mine.benchMax
            and exact_option(option, parent.OptionType.PLAY, index=option.index)):
            candy, ala, energy = (first_hand(obs, {CANDY}, (card.serial,)),
                                   first_hand(obs, {ALAKAZAM}, (card.serial,)),
                                   first_hand(obs, PSYCHIC, (card.serial,)))
            if candy and ala and energy:
                add(index, card, None, 10, -1, "V2_H1_PREP_ABRA", "PLAY_ABRA",
                    (card.serial, candy[1], ala[1], energy[1]), "await_main")
        if (option.type == parent.OptionType.EVOLVE and target is not None
            and option.area == parent.AreaType.HAND
            and option.inPlayArea in allowed_areas and not target.appearThisTurn
            and exact_option(option, parent.OptionType.EVOLVE, area=parent.AreaType.HAND,
                index=option.index, inPlayArea=option.inPlayArea,
                inPlayIndex=option.inPlayIndex)):
            attached = attached_psychic(target)
            if card.id == KADABRA and target.id == ABRA:
                ala = first_hand(obs, {ALAKAZAM}, (card.serial,))
                energy = None if attached else first_hand(obs, PSYCHIC, (card.serial,))
                if ala and (attached or energy):
                    draw = 2 if safe_draw(obs, 2) else 0
                    add(index, card, target, 20, -1 + draw, "V2_H1_PREP_EVOLVE", "EVOLVE",
                        (card.serial, target.serial, ala[1],
                         attached.serial if attached else energy[1]),
                        "await_optional_draw", draw)
            elif card.id == ALAKAZAM and target.id == KADABRA:
                energy = None if attached else first_hand(obs, PSYCHIC, (card.serial,))
                if attached or energy:
                    draw = 3 if safe_draw(obs, 3) else 0
                    add(index, card, target, 40 if attached else 30, -1 + draw,
                        "V2_H1_PREP_EVOLVE", "EVOLVE",
                        (card.serial, target.serial,
                         attached.serial if attached else energy[1]),
                        "await_optional_draw", draw)
        if (option.type == parent.OptionType.ATTACH and card.id in PSYCHIC
            and target is not None and option.area == parent.AreaType.HAND
            and option.inPlayArea in allowed_areas and not obs.current.energyAttached
            and exact_option(option, parent.OptionType.ATTACH, area=parent.AreaType.HAND,
                index=option.index, inPlayArea=option.inPlayArea,
                inPlayIndex=option.inPlayIndex)):
            roles, valid, score = [target.serial, card.serial], False, 0
            if target.id == ALAKAZAM:
                valid, score = True, 40
            elif target.id == KADABRA and not target.appearThisTurn:
                ala = first_hand(obs, {ALAKAZAM}, (card.serial,))
                valid, score = ala is not None, 22
                if ala: roles.append(ala[1])
            elif target.id == ABRA and not target.appearThisTurn:
                candy, ala = first_hand(obs, {CANDY}, (card.serial,)), first_hand(obs, {ALAKAZAM}, (card.serial,))
                valid, score = candy is not None and ala is not None, 12
                if valid: roles.extend((candy[1], ala[1]))
            if valid:
                add(index, card, target, score, -1, "V2_H1_PREP_PSYCHIC", "ATTACH",
                    roles, "await_telepath_or_main" if card.id == TELEPATH else "await_main")
        if (option.type == parent.OptionType.PLAY and card.id == CANDY
            and exact_option(option, parent.OptionType.PLAY, index=option.index)):
            candy_fields = list(mine.bench) + (list(mine.active) if allow_active else [])
            abras = sorted((p for p in candy_fields if p.id == ABRA and not p.appearThisTurn), key=lambda p:p.serial)
            ala = first_hand(obs, {ALAKAZAM}, (card.serial,))
            if abras and ala:
                abra, attached = abras[0], attached_psychic(abras[0])
                energy = None if attached else first_hand(obs, PSYCHIC, (card.serial, ala[1]))
                if attached or energy:
                    draw = 3 if safe_draw(obs, 3) else 0
                    roles = (card.serial, abra.serial, ala[1], attached.serial if attached else energy[1])
                    add(index, card, abra, 40 if attached else 30, -2 + draw,
                        "V2_H1_PREP_EVOLVE", "CANDY", roles, "await_candy", draw)
                    rows[-1]["evolution_serial"] = ala[1]
    return sorted(rows, key=lambda r: (-r["score"], r["reason"], r["source_serial"], r.get("target_serial") or -1))


def current_h0(parent, obs, action):
    if not isinstance(action, (list, tuple)) or len(action) != 1 or type(action[0]) is not int:
        return None
    if not 0 <= action[0] < len(obs.select.option):
        return None
    option = obs.select.option[action[0]]
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1-owner]
    if (option.type != parent.OptionType.ATTACK or option.attackId != POWERFUL_HAND
        or not exact_option(option, parent.OptionType.ATTACK, attackId=POWERFUL_HAND)
        or len(mine.active) != 1 or len(theirs.active) != 1
        or not v1._powerful_hand_ko(parent, obs, mine.handCount)):
        return None
    target = theirs.active[0]
    return {"owner": owner, "attacker": mine.active[0], "target": target,
            "Hreq": ceil(target.hp / 20),
            "terminal": (parent.prize_count(target) >= len(mine.prize) or not theirs.bench)}


def play_rows(parent, obs, card_id):
    keys = census(parent, obs)
    if keys is None: return []
    rows = []
    for index, option in enumerate(obs.select.option):
        card = option_card(parent, obs, option)
        if (option.type == parent.OptionType.PLAY and card is not None and card.id == card_id
            and exact_option(option, parent.OptionType.PLAY, index=option.index)):
            rows.append((card.serial, index, card, keys[index]))
    return sorted(rows)


def recovery_candidate(parent, obs, hreq):
    """Shortest exact one-card recovery proof for a visible lower line."""
    mine = obs.current.players[obs.current.yourIndex]
    intervals = resource_intervals(obs)
    if intervals is None: return None, "V2_H1_RESOURCE_INTERVAL_UNPROVEN"
    ala_hand, energy_hand, candy = first_hand(obs,{ALAKAZAM}), first_hand(obs,PSYCHIC), first_hand(obs,{CANDY})
    fields = sorted(list(mine.active)+list(mine.bench), key=lambda p:p.serial)
    for field in fields:
        attached = attached_psychic(field)
        missing, direct_delta = [], 0
        if field.id == ALAKAZAM:
            if not attached and not energy_hand: missing=["energy"]
            direct_delta = -1 if not attached else 0
        elif field.id == KADABRA and not field.appearThisTurn:
            if not ala_hand: missing.append("alakazam")
            if not attached and not energy_hand: missing.append("energy")
            direct_delta = 2 - (0 if attached else 1)
        elif field.id == ABRA and not field.appearThisTurn and candy:
            if not ala_hand: missing.append("alakazam")
            if not attached and not energy_hand: missing.append("energy")
            direct_delta = 1 - (0 if attached else 1)
        else: continue
        wanted=[]
        if "alakazam" in missing:
            found=sorted((c for c in mine.discard if c.id==ALAKAZAM),key=lambda c:c.serial)
            if found: wanted.append(found[0])
        if "energy" in missing:
            found=sorted((c for c in mine.discard if c.id==BASIC),key=lambda c:c.serial)
            if found: wanted.append(found[0])
        for card_id, reason in ((STRETCHER,"V2_H1_RECOVER_STRETCHER"),(LANA,"V2_H1_RECOVER_LANA")):
            if len(wanted)!=len(missing) or not wanted or (card_id==STRETCHER and len(wanted)!=1): continue
            if card_id==LANA and obs.current.supporterPlayed: continue
            plays=play_rows(parent,obs,card_id)
            hfinal=mine.handCount+(0 if card_id==STRETCHER else len(wanted)-1)+direct_delta
            if plays and hfinal>=hreq:
                serial,index,card,key=plays[0]
                return {"action":[index],"key":key,"reason":reason,"kind":"RECOVERY",
                    "source_row":card_row(card),"source_serial":serial,"target_serial":field.serial,
                    "wanted_rows":tuple(card_row(c) for c in wanted),"wanted_ids":tuple(c.id for c in wanted),
                    "score":1,"Hfinal":hfinal,"h1_serials":tuple([field.serial]+[c.serial for c in wanted]),
                    "next_stage":"await_recovery_child","draw_count":0},None
        if "alakazam" in missing and not obs.current.supporterPlayed and intervals[ALAKAZAM]["deck_lb"]>=1:
            energy_id = BASIC if intervals[BASIC]["deck_lb"]>=1 else TELEPATH if intervals[TELEPATH]["deck_lb"]>=1 else None
            if energy_id is None: continue
            if mine.deckCount-2<=len(mine.prize): return None,"V2_H1_DECK_CLOCK_BLOCK"
            plays=play_rows(parent,obs,HILDA); hfinal=mine.handCount+1+direct_delta
            if plays and hfinal>=hreq:
                serial,index,card,key=plays[0]
                return {"action":[index],"key":key,"reason":"V2_H1_RECOVER_HILDA","kind":"RECOVERY",
                    "source_row":card_row(card),"source_serial":serial,"target_serial":field.serial,
                    "wanted_rows":(),"wanted_ids":(ALAKAZAM,energy_id),"score":1,"Hfinal":hfinal,
                    "h1_serials":(field.serial,),"next_stage":"await_recovery_child","draw_count":0},None
    return None,"V2_H1_RESOURCE_INTERVAL_UNPROVEN"