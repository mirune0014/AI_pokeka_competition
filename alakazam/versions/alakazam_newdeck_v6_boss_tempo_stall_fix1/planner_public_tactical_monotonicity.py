"""Callback-local Stage-1 tactical monotonicity around complete C2."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
from typing import Any, Callable, Iterable
import planner_deck_adaptation_v1 as deck_v1
import planner_model as model
import planner_policy as core
import planner_public_survival_bench0 as survival
import planner_runtime_model as runtime_model

RULE_VERSION = "V4_PUBLIC_TACTICAL_MONOTONICITY_BUNDLE_FIX9"
PARENT_CLOSURE_SHA256 = "5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134"
ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE, SHAYMIN = 305, 66, 343
POFFIN, BOSS, POWERFUL_HAND, RARE_CANDY = 1086, 1182, 1072, 1079
PSYCHIC_ENERGY_IDS = frozenset({5, 19})
ROLE_COUNTS = {ABRA: 4, DUNSPARCE: 3}
LINE_IDS = frozenset({ABRA, KADABRA, ALAKAZAM})
LAST_FIX9_TRACE: dict[str, Any] | None = None

def _int(value):
    if isinstance(value, bool): return None
    try: return int(value)
    except (TypeError, ValueError): return None

def _card_id(card):
    if isinstance(card, dict): return _int(card.get("id", card.get("cardId")))
    return _int(getattr(card, "id", getattr(card, "cardId", None)))

def _serial(card):
    return _int(card.get("serial")) if isinstance(card, dict) else _int(getattr(card, "serial", None))

def _owner(card):
    return _int(card.get("playerIndex")) if isinstance(card, dict) else _int(getattr(card, "playerIndex", None))

_RUNTIME_MAIN_SHA256 = "5100355E5756C16B4E38276DA79551A7F9D1F47D62B863C295D9302B06AE4A24"
_RUNTIME_MAIN_SIZE = 1251

def _closure_row(logical_name, payload):
    return f"{logical_name}\0{hashlib.sha256(payload).hexdigest().upper()}\0{len(payload)}\n"

def _closure():
    try:
        root = Path(__file__).resolve().parent
        wrapper = root / "main.py"; packaged_policy = root / "_policy_main.py"
        packaged = packaged_policy.is_file()
        if not wrapper.is_file(): return None
        policy = packaged_policy if packaged else wrapper
        rows = [_closure_row("main.py", policy.read_bytes())]
        for path in root.glob("*.py"):
            if path.name.startswith("test") or path.name in {"main.py", "_policy_main.py"}: continue
            rows.append(_closure_row(path.name, path.read_bytes()))
        runtime = root / "runtime" / "main.py"
        if runtime.is_file():
            payload = runtime.read_bytes()
            if (len(payload) != _RUNTIME_MAIN_SIZE
                or hashlib.sha256(payload).hexdigest().upper() != _RUNTIME_MAIN_SHA256): return None
            rows.append(_closure_row("runtime/main.py", payload))
        elif packaged:
            rows.append(f"runtime/main.py\0{_RUNTIME_MAIN_SHA256}\0{_RUNTIME_MAIN_SIZE}\n")
        else:
            return None
        rows.append(_closure_row("deck.csv", (root / "deck.csv").read_bytes()))
        return hashlib.sha256("".join(sorted(rows)).encode()).hexdigest().upper()
    except Exception: return None

def reset():
    global LAST_FIX9_TRACE
    LAST_FIX9_TRACE = None

def _surface_trace(surface):
    return surface.get("LAST_STAGED_POLICY_TRACE") if isinstance(surface, dict) else None

def _publish(publish, surface, parent_action, action, rule, reasons, **extra):
    global LAST_FIX9_TRACE
    trace = copy.deepcopy(_surface_trace(surface) or {})
    trace.update({
        "schema_version": 9, "rule_version": RULE_VERSION,
        "parent_closure_sha256": PARENT_CLOSURE_SHA256,
        "candidate_closure_sha256": _closure(),
        "fix9_parent_action": copy.deepcopy(parent_action),
        "proposed_action": copy.deepcopy(action), "applied_action": copy.deepcopy(action),
        "selected_rule": rule, "reason_tags": list(reasons),
    })
    trace.update(copy.deepcopy(extra))
    raw_action = trace.get("raw_parent_action", parent_action)
    equal = raw_action == action
    trace["action_identity"] = {
        "value_equal": equal, "type_equal": type(raw_action) is type(action),
        "order_equal": equal,
        "returned_parent_object_unchanged": equal and type(raw_action) is type(action),
    }
    LAST_FIX9_TRACE = copy.deepcopy(trace)
    publish(copy.deepcopy(trace), copy.deepcopy(surface))

def _normal_main(parent, obs):
    select = getattr(obs, "select", None)
    return bool(select is not None and obs.current is not None
        and select.context == parent.SelectContext.MAIN and int(select.type) == 0
        and select.minCount == 1 and select.maxCount == 1
        and select.effect is None and select.contextCard is None and obs.current.result == -1)

def _selected(obs, action):
    if (not isinstance(action, (list, tuple)) or len(action) != 1
        or type(action[0]) is not int or not 0 <= action[0] < len(obs.select.option)):
        return None
    return obs.select.option[action[0]]

def _source(parent, obs, option):
    try: return core._option_card(parent, obs, option)
    except Exception: return None

def _rows(parent, obs):
    result, seen = [], set()
    for index, option in enumerate(obs.select.option):
        key = runtime_model.stable_option_key(parent, obs, option)
        if key is None or key in seen: return None
        seen.add(key)
        card = _source(parent, obs, option)
        result.append({"index": index, "key": key, "key_repr": repr(key),
            "option": option, "source_id": _card_id(card), "source_serial": _serial(card)})
    return result

def _importance(parent_trace):
    source = parent_trace.get("line_importance_rows") if isinstance(parent_trace, dict) else None
    values = {r.get("importance") for r in source or () if isinstance(r, dict)}
    if "UNIQUE" in values: return "UNIQUE"
    if "IMPORTANT" in values: return "IMPORTANT"
    return "REDUNDANT" if values and values <= {"REDUNDANT"} else None

def _board(raw):
    try:
        current = raw["current"]; mine = current["players"][current["yourIndex"]]
        field = list(mine["active"]) + list(mine["bench"]); bench_max = mine["benchMax"]
    except (KeyError, TypeError, IndexError): return None
    if type(bench_max) is not int or bench_max < len(mine["bench"]) or any(not isinstance(c, dict) for c in field): return None
    ids = [_card_id(card) for card in field]
    return {"A": sum(i in LINE_IDS for i in ids), "N": sum(i in (DUNSPARCE, DUDUNSPARCE) for i in ids),
        "F": bench_max-len(mine["bench"]), "bench_count": len(mine["bench"]), "bench_max": bench_max}

def _inventory(raw):
    """Exact fixed-deck count proof over all known own zones."""
    try:
        current = raw["current"]; owner = current["yourIndex"]; mine = current["players"][owner]
        public = list(mine["hand"]) + list(mine["discard"])
        for pokemon in list(mine["active"]) + list(mine["bench"]):
            public.append(pokemon)
            public += list(pokemon["preEvolution"]) + list(pokemon["energyCards"]) + list(pokemon["tools"])
        hidden = 0
        for card in mine["prize"]:
            if card is None: hidden += 1
            else: public.append(card)
        public += [c for c in current["stadium"] if _owner(c) == owner]
        deck_count = mine["deckCount"]
    except (KeyError, TypeError, IndexError): return None
    serials = [_serial(c) for c in public]
    if (type(deck_count) is not int or deck_count < 0
        or any(not isinstance(c, dict) or _owner(c) != owner for c in public)
        or any(s is None or s <= 0 for s in serials) or len(serials) != len(set(serials))
        or len(public) + deck_count + hidden != 60): return None
    known = {cid: sum(_card_id(c) == cid for c in public) for cid in ROLE_COUNTS}
    if any(known[cid] > ROLE_COUNTS[cid] for cid in ROLE_COUNTS): return None
    return {"known": known, "unknown": {cid: ROLE_COUNTS[cid]-known[cid] for cid in ROLE_COUNTS},
        "deck_count": deck_count, "hidden_prizes": hidden}

def _priorities(board, importance):
    result = []
    if board["A"] == 0: result.append(("FIRST_ABRA", ABRA))
    if board["A"] == 1 and importance in ("UNIQUE", "IMPORTANT"): result.append(("IMPORTANT_BACKUP_ABRA", ABRA))
    if board["N"] == 0: result.append(("FIRST_DUNSPARCE", DUNSPARCE))
    if board["A"] < 2: result.append(("SECOND_ABRA", ABRA))
    if board["N"] < 2: result.append(("SECOND_DUNSPARCE", DUNSPARCE))
    return tuple(result)

def _poffin_rows(parent, rows):
    return [r for r in rows or () if r["option"].type == parent.OptionType.PLAY and r["source_id"] == POFFIN]

def _selected_is(parent, obs, action, card_id):
    option = _selected(obs, action)
    return bool(option is not None and option.type == parent.OptionType.PLAY and _card_id(_source(parent, obs, option)) == card_id)

def _role_gain(board, inventory, importance):
    if board["F"] <= 0: return False
    unknown = inventory.get("unknown") if isinstance(inventory, dict) else None
    return any(unknown is None or unknown.get(cid, 0) > 0 for _, cid in _priorities(board, importance))

def _immediate(parent, obs, rows):
    result = []
    for row in rows or ():
        option = row["option"]; source = _source(parent, obs, option)
        try: target = core._target_pokemon(parent, obs, option)
        except Exception: target = None
        reason = None
        if option.type == parent.OptionType.ATTACK and getattr(option, "attackId", None) == POWERFUL_HAND:
            try:
                mine = obs.current.players[obs.current.yourIndex]
                if deck_v1._powerful_hand_ko(parent, obs, mine.handCount): reason = "EXACT_CURRENT_KO"
            except Exception: pass
        elif option.type == parent.OptionType.EVOLVE:
            if _card_id(source) in (KADABRA, ALAKAZAM) and _card_id(target) in (ABRA, KADABRA):
                reason = "EVOLVE_IMPROVES_ALAKAZAM_ROUTE"
            elif _card_id(source) == DUDUNSPARCE and _card_id(target) == DUNSPARCE:
                reason = "EVOLVE_ENABLES_RUN_AWAY_CAPACITY"
        elif option.type == parent.OptionType.ABILITY:
            pokemon = _source(parent, obs, option)
            if _card_id(pokemon) == DUDUNSPARCE: reason = "RUN_AWAY_FREES_CAPACITY"
            elif _card_id(pokemon) in (KADABRA, ALAKAZAM): reason = "PSYCHIC_DRAW_IMPROVES_ATTACKER"
        elif option.type == parent.OptionType.ATTACH and _card_id(source) in PSYCHIC_ENERGY_IDS and _card_id(target) in LINE_IDS:
            reason = "PSYCHIC_ATTACH_IMPROVES_ALAKAZAM_ROUTE"
        if reason: result.append({"index": row["index"], "key_repr": row["key_repr"], "reason": reason})
    return result

def _poffin_defer(parent, obs, raw, action, parent_trace, rows):
    if not _normal_main(parent, obs) or not _selected_is(parent, obs, action, POFFIN): return None
    board = _board(raw)
    if board is None: return None
    inventory = _inventory(raw); importance = _importance(parent_trace)
    immediate = _immediate(parent, obs, rows); role_gain = _role_gain(board, inventory, importance)
    unknown = inventory.get("unknown") if isinstance(inventory, dict) else None
    reasons, mechanical = [], False
    if board["F"] == 0: reasons.append("BENCH_FULL_MECHANICAL_WHIFF"); mechanical = True
    if unknown == {ABRA: 0, DUNSPARCE: 0}: reasons.append("EXACT_ROLE_INVENTORY_DEPLETED"); mechanical = True
    if not role_gain: reasons.append("NO_INDEPENDENT_ROLE_GAIN")
    reasons += [r["reason"] for r in immediate]
    return None if not reasons else {"board": board, "inventory": inventory, "importance": importance,
        "role_gain": role_gain, "immediate_actions": immediate, "mechanical": mechanical, "reasons": reasons}

def _ready(parent, obs):
    try:
        owner = obs.current.yourIndex; mine = obs.current.players[owner]
        return bool(len(mine.active) == 1 and mine.active[0].id == ALAKAZAM
            and parent._two_prize_powerful_hand_metadata_is_exact() and not parent.card_table[ALAKAZAM].tera
            and parent._two_prize_alakazam_is_ready(mine.active[0], owner)
            and not mine.asleep and not mine.paralyzed and not mine.confused)
    except Exception: return False

def _prizes(parent, target, owner):
    try: return deck_v1._exact_evolution_ko_prize_value(parent, target, owner)
    except Exception: return None

_MIST_TEXT = (
    "As long as this card is attached to a Pok\u00e9mon, it provides {C} Energy.\n\n"
    "Prevent all effects of attacks used by your opponent\u2019s Pok\u00e9mon done to the "
    "Pok\u00e9mon this card is attached to.\u00a0(Existing effects are not removed. Damage is not an effect.)"
)
_ROCK_FIGHTING_TEXT = (
    "As long as this card is attached to a Pok\u00e9mon, it provides {F} Energy.\n"
    "Prevent all effects of attacks used by your opponent\u2019s Pok\u00e9mon done to the {F} "
    "Pok\u00e9mon this card is attached to.\u00a0(Existing effects are not removed. Damage is not an effect.)"
)
_RARE_CANDY_TEXT = (
    "Choose 1 of your Basic Pok\u00e9mon in play. If you have a Stage 2 card in your hand that evolves "
    "from that Pok\u00e9mon, put that card onto the Basic Pok\u00e9mon to evolve it, skipping the Stage 1. "
    "You can\u2019t use this card during your first turn or on a Basic Pok\u00e9mon that was put into play this turn."
)

def _fixed_metadata(parent, card_id, name, card_type, energy_type, skill_text):
    data = parent.card_table.get(card_id)
    return bool(data is not None and data.cardId == card_id and data.name == name
        and data.cardType == card_type and data.retreatCost == 0 and data.hp == 0
        and data.weakness is None and data.resistance is None and data.energyType == energy_type
        and all(getattr(data, field) is False for field in
            ("basic", "stage1", "stage2", "ex", "megaEx", "tera", "aceSpec"))
        and data.evolvesFrom is None and data.attacks == []
        and tuple((skill.name, skill.text) for skill in (data.skills or ())) == ((name, skill_text),))

def _energy_known_zero(parent, obs, target, target_owner):
    try:
        state = obs.current; data = parent.card_table.get(target.id)
        if (not parent._two_prize_public_pokemon_is_complete(target, target_owner)
            or data is None or data.cardId != target.id or data.cardType != parent.CardType.POKEMON
            or not parent._bridge_protected_serials_are_unique(
                state, parent._bridge_pokemon_component_serials(target))):
            return None
        for index, card in enumerate(target.energyCards):
            if (card.id == 11 and target.energies[index] == parent.EnergyType.COLORLESS
                and _fixed_metadata(parent, 11, "Mist Energy", parent.CardType.SPECIAL_ENERGY,
                    parent.EnergyType.COLORLESS, _MIST_TEXT)):
                return "KNOWN_ZERO_MIST_ENERGY"
            if (card.id == 20 and data.energyType == parent.EnergyType.FIGHTING
                and target.energies[index] == parent.EnergyType.FIGHTING
                and _fixed_metadata(parent, 20, "Rock Fighting Energy", parent.CardType.SPECIAL_ENERGY,
                    parent.EnergyType.FIGHTING, _ROCK_FIGHTING_TEXT)):
                return "KNOWN_ZERO_ROCK_FIGHTING_ENERGY"
    except Exception:
        return None
    return None

def _is_known_zero(row):
    return isinstance(row, dict) and str(row.get("effective", "")).startswith("KNOWN_ZERO_")

def _rare_candy_cost_is_exact(parent, obs, option):
    try:
        owner = obs.current.yourIndex; mine = obs.current.players[owner]; source = _source(parent, obs, option)
        if (option.type != parent.OptionType.PLAY or _card_id(source) != RARE_CANDY
            or mine.hand is None or len(mine.hand) != mine.handCount
            or _owner(source) != owner or _serial(source) is None or _serial(source) <= 0
            or sum(_serial(card) == _serial(source) for card in mine.hand) != 1
            or not any(_card_id(card) == ALAKAZAM and _owner(card) == owner
                and _serial(card) is not None and _serial(card) > 0 for card in mine.hand)
            or not parent._two_prize_powerful_hand_metadata_is_exact()):
            return False
        return _fixed_metadata(parent, RARE_CANDY, "Rare Candy", parent.CardType.ITEM,
            parent.EnergyType.COLORLESS, _RARE_CANDY_TEXT)
    except Exception:
        return False

def _projection(parent, obs, target, target_owner, hand_count):
    result = {"target_id": _card_id(target), "target_serial": _serial(target), "hand_count": hand_count,
        "damage": None, "remaining_hp": _int(getattr(target, "hp", None)), "ko": False,
        "prizes": None, "terminal": False, "effective": "UNKNOWN"}
    if not _ready(parent, obs) or hand_count < 0: return result
    try:
        clear = deck_v1._v1_powerful_hand_target_is_publicly_clear(parent, obs.current, target, target_owner)
        veil = deck_v1._repelling_veil_state(parent, obs.current, target, target_owner)
        energy_zero = _energy_known_zero(parent, obs, target, target_owner)
    except Exception: return result
    if veil is True: result["damage"] = 0; result["effective"] = "KNOWN_ZERO_REPELLING_VEIL"
    elif energy_zero is not None: result["damage"] = 0; result["effective"] = energy_zero
    elif clear: result["damage"] = 20*hand_count; result["effective"] = "DAMAGEABLE"
    else: return result
    hp = result["remaining_hp"]
    result["ko"] = isinstance(hp, int) and result["damage"] > 0 and result["damage"] >= hp
    result["prizes"] = _prizes(parent, target, target_owner)
    try: own_prizes = len(obs.current.players[obs.current.yourIndex].prize)
    except Exception: own_prizes = None
    result["terminal"] = bool(result["ko"] and isinstance(result["prizes"], int)
        and isinstance(own_prizes, int) and result["prizes"] >= own_prizes)
    return result

def _current_projection(parent, obs, delta=0):
    try:
        owner = obs.current.yourIndex; mine = obs.current.players[owner]; theirs = obs.current.players[1-owner]
        if len(theirs.active) != 1: return None
        return _projection(parent, obs, theirs.active[0], 1-owner, mine.handCount+delta)
    except Exception: return None

def _ko_certificate(parent, obs):
    if not _normal_main(parent, obs): return None
    try:
        mine = obs.current.players[obs.current.yourIndex]; attack = deck_v1._attack_index(parent, obs)
        current = _current_projection(parent, obs)
        if attack is None or not deck_v1._powerful_hand_ko(parent, obs, mine.handCount) or not current or not current["ko"]: return None
        return {"attack_index": attack, "hand_count": mine.handCount, "damage": current["damage"],
            "remaining_hp": current["remaining_hp"], "terminal": current["terminal"],
            "prizes": current["prizes"], "target_serial": current["target_serial"]}
    except Exception: return None

def _boss_targets(parent, obs):
    try:
        owner = obs.current.yourIndex; mine = obs.current.players[owner]; theirs = obs.current.players[1-owner]
        return [dict(_projection(parent, obs, target, 1-owner, mine.handCount-1), bench_index=i)
            for i, target in enumerate(theirs.bench)]
    except Exception: return []

def _boss_admissible(parent, obs):
    current = _current_projection(parent, obs); targets = _boss_targets(parent, obs)
    positive = [r for r in targets if isinstance(r.get("damage"), int) and r["damage"] > 0]
    terminal = [r for r in positive if r["terminal"]]
    higher = [r for r in positive if r["ko"] and isinstance(r.get("prizes"), int)
        and (not isinstance(current, dict) or not isinstance(current.get("prizes"), int) or r["prizes"] > current["prizes"])]
    if terminal: return True, targets, "CERTIFIED_TERMINAL_BOSS_KO"
    if higher: return True, targets, "CERTIFIED_HIGHER_PRIZE_BOSS_KO"
    if isinstance(current, dict) and isinstance(current.get("damage"), int) and current["damage"] > 0 and targets and not positive \
        and all(_is_known_zero(r) for r in targets):
        return False, targets, "BOSS_REPLACES_POSITIVE_WITH_KNOWN_ZERO"
    if isinstance(current, dict) and current.get("ko") and not any(r.get("ko") for r in positive):
        return False, targets, "BOSS_CROSSES_CURRENT_KO_FLOOR"
    return True, targets, None

def _ko_harm(parent, obs, action, certificate):
    if certificate is None: return None
    option = _selected(obs, action)
    if option is None: return "EXACT_KO_ACTION_UNRESOLVED"
    if option.type == parent.OptionType.ATTACK and getattr(option, "attackId", None) == POWERFUL_HAND: return None
    if option.type == parent.OptionType.END: return "END_BEFORE_EXACT_KO"
    if option.type == parent.OptionType.PLAY and _card_id(_source(parent, obs, option)) == BOSS:
        allowed, targets, reason = _boss_admissible(parent, obs)
        if not allowed:
            return reason or "BOSS_NOT_CERTIFIED_ABOVE_EXACT_KO"
        current = _current_projection(parent, obs)
        retained = [
            row for row in targets
            if row.get("ko")
            and isinstance(row.get("prizes"), int)
            and isinstance(current, dict)
            and isinstance(current.get("prizes"), int)
            and row["prizes"] >= current["prizes"]
        ]
        return None if retained else "BOSS_NOT_CERTIFIED_ABOVE_EXACT_KO"
    if option.type in (parent.OptionType.PLAY, parent.OptionType.ATTACH, parent.OptionType.EVOLVE):
        try:
            hand_cost = 2 if _rare_candy_cost_is_exact(parent, obs, option) else 1
            hand_after = obs.current.players[obs.current.yourIndex].handCount-hand_cost
            if not deck_v1._powerful_hand_ko(parent, obs, hand_after): return "ACTION_CROSSES_EXACT_KO_HAND_FLOOR"
        except Exception: return "ACTION_KO_FLOOR_UNKNOWN"
    return None

def _final_slot_harm(parent, obs, raw, action, parent_trace):
    board = _board(raw); option = _selected(obs, action)
    if board is None or board["F"] != 1 or option is None or option.type != parent.OptionType.PLAY: return None
    source_id = _card_id(_source(parent, obs, option)); importance = _importance(parent_trace)
    if source_id not in (ABRA, DUNSPARCE, SHAYMIN): return None
    if source_id == ABRA and (board["A"] == 0 or importance in ("UNIQUE", "IMPORTANT")): return None
    if source_id in (DUNSPARCE, SHAYMIN) and board["A"] == 0: return "FINAL_SLOT_DENIES_FIRST_ALAKAZAM_LINE"
    return None

def _harm(parent, obs, raw, action, parent_trace, certificate, rows):
    if _selected_is(parent, obs, action, POFFIN):
        board = _board(raw); inventory = _inventory(raw)
        if board is not None and (board["F"] == 0 or (inventory and inventory["unknown"] == {ABRA: 0, DUNSPARCE: 0})):
            return "RESELECTED_DEAD_POFFIN"
    harm = _ko_harm(parent, obs, action, certificate)
    if harm: return harm
    if _selected_is(parent, obs, action, BOSS):
        allowed, _, reason = _boss_admissible(parent, obs)
        if not allowed: return reason
    return _final_slot_harm(parent, obs, raw, action, parent_trace)

def _filter(raw, excluded, parent):
    try:
        clone = copy.deepcopy(raw); parsed = parent.to_observation_class(clone); rows = _rows(parent, parsed)
        remove = {r["index"] for r in rows or () if r["key"] in excluded}
        if not remove: return None, None
        clone["select"]["option"] = [o for i, o in enumerate(clone["select"]["option"]) if i not in remove]
        filtered = parent.to_observation_class(clone)
        return (clone, filtered) if runtime_model.raw_parsed_agree(clone, filtered) else (None, None)
    except Exception: return None, None

def _rebind(parent, filtered, action, original):
    if not isinstance(action, (list, tuple)) or not model.action_is_valid(filtered, list(action)): return None
    keys = []
    for index in action:
        if type(index) is not int or not 0 <= index < len(filtered.select.option): return None
        key = runtime_model.stable_option_key(parent, filtered, filtered.select.option[index])
        if key is None: return None
        keys.append(key)
    original_rows = _rows(parent, original)
    mapping = {r["key"]: r["index"] for r in original_rows or ()}
    if any(key not in mapping for key in keys): return None
    rebound = [mapping[key] for key in keys]
    return rebound if model.action_is_valid(original, rebound) else None

def _rerank(raw, obs, parent, delegate, trace_snapshot, trace_restore, pre, original_post, excluded, certificate):
    excluded = set(excluded); attempts = []
    for number in range(1, len(_rows(parent, obs) or ()) + 2):
        filtered_raw, filtered_obs = _filter(raw, excluded, parent)
        if filtered_raw is None: break
        try:
            survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
            filtered_action = delegate(filtered_raw); candidate_post = survival._delegate_snapshot(parent, trace_snapshot)
            rebound = _rebind(parent, filtered_obs, filtered_action, obs)
            if rebound is None: raise ValueError("STABLE_REBIND_FAILED")
            candidate_trace = _surface_trace(candidate_post["trace_surface"])
            harm = _harm(parent, obs, raw, rebound, candidate_trace, certificate, _rows(parent, obs))
            selected = _selected(obs, rebound)
            key = runtime_model.stable_option_key(parent, obs, selected) if selected is not None else None
            attempts.append({"attempt": number, "candidate": list(rebound), "selected_key": repr(key), "harm": harm})
            if harm is None:
                survival._restore_delegate(parent, candidate_post, trace_restore, restore_c3=True)
                return rebound, candidate_post, attempts
            if key is None or key in excluded: break
            excluded.add(key)
        except Exception as error:
            attempts.append({"attempt": number, "candidate": None, "selected_key": None, "harm": f"RERANK_{type(error).__name__}"})
            break
    survival._restore_delegate(parent, original_post, trace_restore, restore_c3=True)
    return None, None, attempts

def _direct_non_poffin(parent, obs, raw, trace, certificate, rows):
    end = [r for r in rows or () if r["option"].type == parent.OptionType.END]
    ordered = end if len(end) == 1 else sorted(rows or (), key=lambda r: r["key_repr"])
    for row in ordered:
        action = [row["index"]]
        if row["source_id"] == POFFIN: continue
        if model.action_is_valid(obs, action) and _harm(parent, obs, raw, action, trace, certificate, rows) is None: return action
    return None

def _poffin_child(parent, obs, raw, parent_action, parent_trace):
    select = obs.select
    if (select is None or select.context != parent.SelectContext.TO_BENCH or int(select.type) != 1
        or select.minCount != 0 or select.maxCount not in (1, 2) or not isinstance(select.deck, list)): return None
    effect_ids = {_card_id(c) for c in (select.effect, select.contextCard) if c is not None}
    if effect_ids != {POFFIN}: return None
    board = _board(raw)
    if board is None: return None
    candidates, seen = [], set()
    for index, option in enumerate(select.option):
        if option.type != parent.OptionType.CARD or option.area != parent.AreaType.DECK \
            or type(option.index) is not int or not 0 <= option.index < len(select.deck): return None
        card = select.deck[option.index]; serial = _serial(card); key = runtime_model.stable_option_key(parent, obs, option)
        if key is None or serial is None or serial <= 0 or serial in seen: return None
        seen.add(serial); candidates.append({"option_index": index, "card_id": _card_id(card), "serial": serial, "key_repr": repr(key)})
    candidates.sort(key=lambda r: (r["card_id"] if r["card_id"] is not None else 10**9, r["serial"], r["key_repr"]))
    importance = _importance(parent_trace); capacity = min(select.maxCount, board["F"], 2)
    priorities = _priorities(board, importance)
    final_slot_abra_only = board["A"] == 0 and capacity == 1
    if final_slot_abra_only: priorities = (("FIRST_ABRA", ABRA),)
    selected, used, projected = [], set(), dict(board)
    for role, card_id in priorities:
        if len(selected) >= capacity: break
        if card_id == ABRA and projected["A"] >= 2: continue
        if card_id == DUNSPARCE and projected["N"] >= 2: continue
        chosen = next((r for r in candidates if r["card_id"] == card_id and r["serial"] not in used), None)
        if chosen is None: continue
        chosen = dict(chosen, role=role); selected.append(chosen); used.add(chosen["serial"])
        projected["A" if card_id == ABRA else "N"] += 1
    action = [r["option_index"] for r in selected]
    if not model.action_is_valid(obs, action): return None
    return action, {"stage": "OPTIONAL_TO_BENCH", "board": board, "importance": importance,
        "legal_capacity": capacity, "final_slot_abra_only": final_slot_abra_only,
        "parent_action": list(parent_action), "selected_cardinality": len(action),
        "selected": selected, "candidates": candidates}

def _boss_child_envelope(parent, obs):
    try:
        state, select = obs.current, obs.select; owner = state.yourIndex; theirs = state.players[1-owner]
        effect_cards = [card for card in (select.effect, select.contextCard) if card is not None]
        if (state.result != -1 or int(select.type) != 1 or select.context != parent.SelectContext.SWITCH
            or select.minCount != 1 or select.maxCount != 1 or select.remainDamageCounter != 0
            or select.remainEnergyCost != 0 or select.deck is not None or len(effect_cards) != 1
            or _card_id(effect_cards[0]) != BOSS or _serial(effect_cards[0]) is None
            or _serial(effect_cards[0]) <= 0 or _owner(effect_cards[0]) != owner
            or not parent._exact_prize_lane_boss_metadata_is_exact()
            or len(select.option) != len(theirs.bench)):
            return False
        actual = []
        for option in select.option:
            if (option.type != parent.OptionType.CARD or option.area != parent.AreaType.BENCH
                or type(option.index) is not int or not 0 <= option.index < len(theirs.bench)
                or getattr(option, "playerIndex", None) != 1-owner):
                return False
            actual.append(option.index)
        return actual == list(range(len(theirs.bench)))
    except Exception:
        return False

def _target_order(rows):
    return sorted(rows, key=lambda r: (-int(bool(r.get("terminal"))), -int(bool(r.get("ko"))),
        -(r["prizes"] if isinstance(r.get("prizes"), int) else -1),
        -(r["damage"] if isinstance(r.get("damage"), int) else -1),
        r["target_serial"] if isinstance(r.get("target_serial"), int) else 10**9))

def _boss_child(parent, obs, parent_action):
    if not _boss_child_envelope(parent, obs): return None
    owner = obs.current.yourIndex; hand_count = obs.current.players[owner].handCount; targets = []
    for index, option in enumerate(obs.select.option):
        row = _projection(parent, obs, _source(parent, obs, option), 1-owner, hand_count)
        row["option_index"] = index; targets.append(row)
    positive = [r for r in targets if isinstance(r.get("damage"), int) and r["damage"] > 0]
    selected_index = parent_action[0] if isinstance(parent_action, (list, tuple)) and len(parent_action) == 1 else None
    chosen = next((r for r in targets if r["option_index"] == selected_index), None)
    if not positive or chosen is None: return None
    terminal = [r for r in positive if r.get("terminal")]
    if terminal and not chosen.get("terminal"):
        replacement, reason = _target_order(terminal)[0], "TARGET_CHILD_SELECT_TERMINAL"
    else:
        chosen_prizes = chosen.get("prizes")
        higher = [r for r in positive if r.get("ko") and isinstance(r.get("prizes"), int)
            and isinstance(chosen_prizes, int) and r["prizes"] > chosen_prizes]
        if higher:
            replacement, reason = _target_order(higher)[0], "TARGET_CHILD_SELECT_HIGHER_PRIZE_KO"
        elif (isinstance(chosen.get("damage"), int) and chosen["damage"] > 0
            and not chosen.get("ko") and isinstance(chosen_prizes, int)):
            ko_dominant = [r for r in positive if r.get("ko")
                and isinstance(r.get("prizes"), int) and r["prizes"] == chosen_prizes]
            if not ko_dominant: return None
            replacement, reason = _target_order(ko_dominant)[0], "TARGET_CHILD_SELECT_KO_DOMINANCE"
        elif _is_known_zero(chosen):
            replacement, reason = _target_order(positive)[0], "TARGET_CHILD_REJECT_KNOWN_ZERO"
        else:
            return None
    return [replacement["option_index"]], targets, reason

def _transaction_in_progress(snapshot):
    if not isinstance(snapshot, dict):
        return False
    c3_state = snapshot.get("c3_state")
    return bool(
        snapshot.get("integrated_transaction") is not None
        or snapshot.get("v1_transaction") is not None
        or (
            isinstance(c3_state, dict)
            and c3_state.get("transaction") is not None
        )
    )
def agent(raw: dict[str, Any], delegate: Callable[[dict[str, Any]], Any], *, parent: Any,
          trace_snapshot: Callable[[], Any], trace_restore: Callable[[Any], None],
          trace_publish: Callable[[dict[str, Any], Any], None]):
    """Apply the explicit Stage-1 priority bundle outside complete C2+C3."""
    if isinstance(raw, dict) and raw.get("select") is None and raw.get("current") is None:
        reset(); return delegate(raw)
    pre = survival._delegate_snapshot(parent, trace_snapshot)
    parent_action = delegate(raw)
    post = survival._delegate_snapshot(parent, trace_snapshot)
    surface = post["trace_surface"]; parent_trace = _surface_trace(surface)
    if _transaction_in_progress(pre) or _transaction_in_progress(post):
        _publish(
            trace_publish,
            surface,
            parent_action,
            parent_action,
            None,
            ["PARENT_TRANSACTION_IN_PROGRESS"],
        )
        return parent_action
    try:
        obs = parent.to_observation_class(copy.deepcopy(raw))
        if not runtime_model.raw_parsed_agree(raw, obs): raise ValueError("RAW_PARSED_DISAGREEMENT")
    except Exception as error:
        _publish(trace_publish, surface, parent_action, parent_action, None, [f"FAIL_CLOSED_{type(error).__name__}"])
        return parent_action

    child = _poffin_child(parent, obs, raw, parent_action, parent_trace)
    if child is not None:
        action, details = child
        survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
        _publish(trace_publish, surface, parent_action, action, "POFFIN_ROLE_CARDINALITY",
            [f"POFFIN_CHILD_SELECT_{len(action)}"], poffin=details)
        return action
    target_child = _boss_child(parent, obs, parent_action)
    if target_child is not None:
        action, targets, reason = target_child
        survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
        _publish(trace_publish, surface, parent_action, action, "EFFECTIVE_TARGET_SAFETY",
            [reason], effective_targets=targets)
        return action
    if not _normal_main(parent, obs):
        _publish(trace_publish, surface, parent_action, parent_action, None, [])
        return parent_action

    rows = _rows(parent, obs); certificate = _ko_certificate(parent, obs)
    option = _selected(obs, parent_action); source_id = _card_id(_source(parent, obs, option))
    if certificate is not None and certificate["terminal"]:
        action = [certificate["attack_index"]]
        if action != list(parent_action) and model.action_is_valid(obs, action):
            survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
            _publish(trace_publish, surface, parent_action, action, "TERMINAL_WIN",
                ["CURRENT_TERMINAL_KO"], exact_ko=certificate)
            return action

    if option is not None and option.type == parent.OptionType.PLAY and source_id == BOSS:
        boss_ok, targets, reason = _boss_admissible(parent, obs)
        if boss_ok and reason is not None:
            _publish(trace_publish, surface, parent_action, parent_action, "CERTIFIED_HIGHER_PRIZE_KO",
                [reason], exact_ko=certificate, effective_targets=targets)
            return parent_action

    ko_harm = _ko_harm(parent, obs, parent_action, certificate)
    if ko_harm is not None and certificate is not None:
        action = [certificate["attack_index"]]
        if model.action_is_valid(obs, action):
            survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
            _publish(trace_publish, surface, parent_action, action, "EXACT_KO_FLOOR",
                [ko_harm], exact_ko=certificate)
            return action

    if option is not None and option.type == parent.OptionType.PLAY and source_id == BOSS:
        boss_ok, targets, reason = _boss_admissible(parent, obs)
        if not boss_ok:
            excluded = {r["key"] for r in rows or () if r["option"].type == parent.OptionType.PLAY and r["source_id"] == BOSS}
            action, selected_post, attempts = _rerank(raw, obs, parent, delegate, trace_snapshot, trace_restore,
                pre, post, excluded, certificate)
            if action is not None:
                selected_surface = selected_post["trace_surface"]
                _publish(trace_publish, selected_surface, parent_action, action, "EFFECTIVE_TARGET_SAFETY",
                    [reason], exact_ko=certificate, effective_targets=targets, rerank_attempts=attempts)
                return action

    final_slot_harm = _final_slot_harm(parent, obs, raw, parent_action, parent_trace)
    if final_slot_harm is not None:
        selected = _selected(obs, parent_action)
        selected_key = runtime_model.stable_option_key(parent, obs, selected) if selected is not None else None
        action, selected_post, attempts = None, None, []
        if selected_key is not None:
            action, selected_post, attempts = _rerank(raw, obs, parent, delegate, trace_snapshot, trace_restore,
                pre, post, {selected_key}, certificate)
        if action is not None:
            selected_surface = selected_post["trace_surface"]
            _publish(trace_publish, selected_surface, parent_action, action, "FINAL_SLOT_PROTECTION",
                [final_slot_harm], exact_ko=certificate, rerank_attempts=attempts)
            return action

    poffin = _poffin_defer(parent, obs, raw, parent_action, parent_trace, rows)
    if poffin is not None:
        action = [certificate["attack_index"]] if poffin["mechanical"] and certificate is not None else None
        selected_post, attempts = None, []
        if action is None:
            excluded = {r["key"] for r in _poffin_rows(parent, rows)}
            action, selected_post, attempts = _rerank(raw, obs, parent, delegate, trace_snapshot, trace_restore,
                pre, post, excluded, certificate)
        if action is None and poffin["mechanical"]:
            action = _direct_non_poffin(parent, obs, raw, parent_trace, certificate, rows)
            if action is not None: survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
        if action is not None:
            selected_surface = selected_post["trace_surface"] if isinstance(selected_post, dict) else surface
            _publish(trace_publish, selected_surface, parent_action, action, "POFFIN_ONE_STEP_DEFER",
                poffin["reasons"], exact_ko=certificate, poffin=poffin, rerank_attempts=attempts)
            return action
        if poffin["mechanical"]:
            _publish(
                trace_publish,
                surface,
                parent_action,
                parent_action,
                "POFFIN_DEFER_UNRESOLVED",
                ["NO_LEGAL_NON_POFFIN_ACTION_FAIL_CLOSED"],
                exact_ko=certificate,
                poffin=poffin,
                rerank_attempts=attempts,
            )
            return parent_action

    _publish(trace_publish, surface, parent_action, parent_action, None, [], exact_ko=certificate)
    return parent_action

__all__ = ["LAST_FIX9_TRACE", "PARENT_CLOSURE_SHA256", "RULE_VERSION", "agent", "reset"]


