"""Atomic Active Dudunsparce Run Away -> ready Psychic KO transaction."""
from __future__ import annotations
from dataclasses import replace
from typing import Any
import planner_model as model
import planner_policy as core
import planner_semantics as semantics
from planner_model import BaseRole, OutcomeKind, ResourceLedger

KIND = "ACTIVE_DUDUNSPARCE_RUN_AWAY_KO_TRANSACTION_V1"
DUNSPARCE = 305
DUDUNSPARCE = 66
SUPER_PSY_BOLT = 1071

def _api():
    import planner_final_policy as api
    return api

def _all_statuses_clear(player: Any) -> bool:
    return (player.poisoned, player.burned, player.asleep, player.paralyzed, player.confused) == (False,) * 5

def _card_rows(parent: Any, cards: Any, owner: int | None):
    api = _api()
    if not isinstance(cards, list):
        return None
    rows = []
    for card in cards:
        row = api._card_fingerprint(card)
        if row is None or row[0] not in parent.card_table or (owner is not None and row[2] != owner):
            return None
        rows.append(row)
    return tuple(rows) if len({row[1] for row in rows}) == len(rows) else None

def _stack_is_exact(parent: Any, pokemon: Any, owner: int) -> bool:
    if not parent._bridge_pokemon_is_publicly_complete(pokemon, owner) or type(getattr(pokemon, "appearThisTurn", None)) is not bool:
        return False
    data = parent.card_table.get(pokemon.id)
    lineage_ok = parent._two_prize_lineage_is_complete(pokemon, owner)
    if pokemon.id == parent.Alakazam:
        lineage_ok = lineage_ok or parent._two_prize_alakazam_lineage_is_complete(pokemon, owner)
    if data is None or data.cardType != parent.CardType.POKEMON or pokemon.maxHp != data.hp or not 0 < pokemon.hp <= pokemon.maxHp or not lineage_ok:
        return False
    for card in pokemon.energyCards:
        card_data = parent.card_table.get(card.id)
        if card_data is None or card_data.cardType not in (parent.CardType.BASIC_ENERGY, parent.CardType.SPECIAL_ENERGY):
            return False
    for card in pokemon.tools:
        card_data = parent.card_table.get(card.id)
        if card_data is None or card_data.cardType != parent.CardType.TOOL:
            return False
    serials = parent._bridge_pokemon_component_serials(pokemon)
    return all(type(serial) is int and serial > 0 for serial in serials) and len(serials) == len(set(serials))

def _one_prize_exact(parent: Any, pokemon: Any, owner: int) -> bool:
    if not _stack_is_exact(parent, pokemon, owner):
        return False
    data = parent.card_table.get(pokemon.id)
    if data is None or type(data.ex) is not bool or type(data.megaEx) is not bool or data.ex or data.megaEx:
        return False
    metadata = [parent.card_table.get(card.id) for card in list(pokemon.energyCards) + list(pokemon.tools)]
    if any(item is None for item in metadata) or any("prize" in parent._normalized_skill_text(skill.text) for item in (data, *metadata) for skill in (item.skills or ())):
        return False
    return parent.prize_count(pokemon) == 1

def _fixed_metadata_is_exact(parent: Any) -> bool:
    dudunsparce = parent.card_table.get(DUDUNSPARCE)
    super_psy = parent.attack_table.get(SUPER_PSY_BOLT)
    powerful = parent.attack_table.get(semantics.POWERFUL_HAND)
    if dudunsparce is None or len(dudunsparce.skills or ()) != 1:
        return False
    draw_text = parent._normalized_skill_text(dudunsparce.skills[0].text)
    powerful_text = parent._normalized_skill_text(getattr(powerful, "text", ""))
    psychic = (int(parent.EnergyType.PSYCHIC),)
    return (
        dudunsparce.skills[0].name.strip() == "Run Away Draw"
        and "draw 3 cards" in draw_text and "shuffle this pok" in draw_text
        and "all attached cards into your deck" in draw_text and "coin" not in draw_text
        and super_psy is not None and super_psy.attackId == SUPER_PSY_BOLT
        and super_psy.name == "Super Psy Bolt" and super_psy.text == "" and super_psy.damage == 30
        and tuple(int(value) for value in super_psy.energies) == psychic
        and powerful is not None and powerful.attackId == semantics.POWERFUL_HAND
        and powerful.name == "Powerful Hand" and powerful.damage == 0
        and tuple(int(value) for value in powerful.energies) == psychic
        and "place 2 damage counters" in powerful_text and "for each card in your hand" in powerful_text
        and "coin" not in powerful_text
    )

def _visible_effects_are_clear(parent: Any, state: Any) -> bool:
    dangerous = ("prevent", "protect", "less damage", "takes no damage", "isn't affected", "is not affected", "weakness", "resistance", "can't be knocked out", "cannot be knocked out", "redirect")
    sources = []
    for player in state.players:
        for pokemon in list(player.active) + list(player.bench):
            sources.append(pokemon.id)
            sources.extend(card.id for card in pokemon.energyCards)
            sources.extend(card.id for card in pokemon.tools)
    sources.extend(card.id for card in state.stadium)
    for card_id in sources:
        if card_id == 1264:  # Battle Cage affects only Benched counter placement.
            continue
        data = parent.card_table.get(card_id)
        if data is None:
            return False
        if any(any(marker in parent._normalized_skill_text(skill.text) for marker in dangerous) for skill in (data.skills or ())):
            return False
    return True

def _lingering_opponent_attacks_are_clear(parent: Any, state: Any, owner: int) -> bool:
    """Fail closed on printed attacks that can leave this KO route stateful."""
    dangerous = (
        "prevent", "protect", "less damage", "takes no damage", "no weakness",
        "can't attack", "cannot attack", "can't use attack", "cannot use attack",
        "can't use that attack", "cannot use that attack", "tries to use an attack",
        "attacks used by the defending pokemon", "attack used by the defending pokemon",
        "damage counter", "will be knocked out", "discard the defending pokemon",
        "attacking pokemon", "redirect",
    )
    opponent = state.players[1 - owner]
    for pokemon in list(opponent.active) + list(opponent.bench):
        data = parent.card_table.get(pokemon.id)
        if data is None:
            return False
        for attack_id in data.attacks or ():
            attack = parent.attack_table.get(attack_id)
            if attack is None or attack.attackId != attack_id:
                return False
            text = parent._normalized_skill_text(attack.text).replace("\u2018", "'").replace("\u2019", "'")
            persists = (
                "during your opponent's next turn" in text
                or "at the end of your opponent's next turn" in text
            )
            if persists and any(marker in text for marker in dangerous):
                return False
    return True
def _target_ko_effects_are_clear(parent: Any, target: Any) -> bool:
    """Reject public target effects that can defeat the frozen KO proof."""
    dangerous = ("is not knocked out", "isn't knocked out", "damage counter")
    sources = (target.id, *(card.id for card in target.energyCards), *(card.id for card in target.tools))
    for card_id in sources:
        data = parent.card_table.get(card_id)
        if data is None:
            return False
        for skill in data.skills or ():
            text = parent._normalized_skill_text(skill.text).replace("\u2018", "'").replace("\u2019", "'")
            if any(marker in text for marker in dangerous):
                return False
    return True

def _moves(parent: Any, pokemon: Any, first_area: Any) -> tuple[tuple[int, int, int], ...]:
    return (
        (pokemon.id, pokemon.serial, int(first_area)),
        *((card.id, card.serial, int(parent.AreaType.PRE_EVOLUTION)) for card in pokemon.preEvolution),
        *((card.id, card.serial, int(parent.AreaType.ENERGY)) for card in pokemon.energyCards),
        *((card.id, card.serial, int(parent.AreaType.TOOL)) for card in pokemon.tools),
    )

def _snapshot(parent: Any, obs: Any, *, allow_empty_active: bool = False):
    state = obs.current
    if state is None or state.yourIndex not in (0, 1) or len(state.players) != 2 or type(state.turn) is not int or type(state.turnActionCount) is not int or state.turn <= 0 or state.turnActionCount < 0 or state.result != -1 or state.looking is not None:
        return None
    if any(type(value) is not bool for value in (state.supporterPlayed, state.stadiumPlayed, state.energyAttached, state.retreated)):
        return None
    owner = state.yourIndex
    mine, theirs = state.players[owner], state.players[1 - owner]
    if len(mine.active) not in ((0, 1) if allow_empty_active else (1,)) or len(theirs.active) != 1:
        return None
    if any(type(value) is not int or value < 0 for value in (mine.deckCount, theirs.deckCount, theirs.handCount)):
        return None
    for field_owner, player in enumerate(state.players):
        if any(not _stack_is_exact(parent, pokemon, field_owner) for pokemon in list(player.active) + list(player.bench)):
            return None
    own_hand = _card_rows(parent, mine.hand, owner)
    own_discard = _card_rows(parent, mine.discard, owner)
    opponent_discard = _card_rows(parent, theirs.discard, 1 - owner)
    stadium = _card_rows(parent, state.stadium, None)
    if any(value is None for value in (own_hand, own_discard, opponent_discard, stadium)):
        return None
    public_serials = parent._bridge_public_serials(state)
    if any(type(serial) is not int or serial <= 0 for serial in public_serials) or len(public_serials) != len(set(public_serials)):
        return None
    status = lambda player: (player.poisoned, player.burned, player.asleep, player.paralyzed, player.confused)
    fp = parent._bridge_pokemon_fingerprint
    return {
        "turn": state.turn, "action_count": state.turnActionCount,
        "supporter_played": state.supporterPlayed, "stadium_played": state.stadiumPlayed,
        "energy_attached": state.energyAttached, "retreated": state.retreated,
        "own_hand": own_hand, "own_discard": own_discard, "own_prizes": len(mine.prize),
        "own_deck": mine.deckCount, "own_bench_max": mine.benchMax, "own_status": status(mine),
        "own_active": tuple(fp(pokemon) for pokemon in mine.active), "own_bench": tuple(fp(pokemon) for pokemon in mine.bench),
        "opponent_discard": opponent_discard, "opponent_prizes": len(theirs.prize),
        "opponent_deck": theirs.deckCount, "opponent_hand_count": theirs.handCount,
        "opponent_bench_max": theirs.benchMax, "opponent_status": status(theirs),
        "opponent_active": tuple(fp(pokemon) for pokemon in theirs.active), "opponent_bench": tuple(fp(pokemon) for pokemon in theirs.bench),
        "stadium": stadium,
    }

def _snapshot_delta(actual: dict, expected: dict, changing: set[str]) -> bool:
    return all(key in actual and (key in changing or actual[key] == value) for key, value in expected.items())

def _log_is_exact(log: Any, log_type: int, expected: dict[str, Any]) -> bool:
    if int(getattr(log, "type", -1)) != log_type:
        return False
    values = vars(log)
    allowed = {"type", *expected}
    return not any(values.get(key) != value for key, value in expected.items()) and all(key in allowed or value is None for key, value in values.items())

def _main_envelope(parent: Any, obs: Any) -> bool:
    select = obs.select
    return select.context == parent.SelectContext.MAIN and int(select.type) == 0 and select.minCount == 1 and select.maxCount == 1 and getattr(select, "remainDamageCounter", 0) == 0 and getattr(select, "remainEnergyCost", 0) == 0 and getattr(select, "deck", None) is None and select.contextCard is None and select.effect is None

def _ability_action(parent: Any, obs: Any):
    api = _api()
    owner = obs.current.yourIndex
    matches = [index for index, option in enumerate(obs.select.option) if option.type == parent.OptionType.ABILITY and option.area == parent.AreaType.ACTIVE and option.index == 0 and api._option_is_exact(parent, option, parent.OptionType.ABILITY, owner, area=parent.AreaType.ACTIVE, index=0)]
    return [matches[0]] if len(matches) == 1 else None

def _attacker_certificate(parent: Any, obs: Any, pokemon: Any, target: Any, hand_count: int):
    api = _api()
    owner = obs.current.yourIndex
    attack_id = {parent.Kadabra: SUPER_PSY_BOLT, parent.Alakazam: semantics.POWERFUL_HAND}.get(getattr(pokemon, "id", None))
    data, attack = parent.card_table.get(getattr(pokemon, "id", None)), parent.attack_table.get(attack_id)
    units, line = semantics.energy_units(parent, pokemon), model.lineage_key(pokemon, owner)
    if attack_id is None or data is None or attack is None or attack.attackId != attack_id or tuple(data.attacks or ()) != (attack_id,) or tuple(int(value) for value in (attack.energies or ())) != (int(parent.EnergyType.PSYCHIC),) or line is None or not _one_prize_exact(parent, pokemon, owner) or units is None or semantics.missing_energy(parent, units, attack.energies) or not _target_ko_effects_are_clear(parent, target) or not _lingering_opponent_attacks_are_clear(parent, obs.current, owner):
        return None
    outcome = api._strict_positive_outcome(parent, obs, pokemon, target, attack_id, hand_count)
    if outcome is None or outcome.amount < target.hp:
        return None
    energy_rows = tuple(api._card_fingerprint(card) for card in pokemon.energyCards)
    if not energy_rows or any(row is None or row[2] != owner for row in energy_rows) or len({row[1] for row in energy_rows}) != len(energy_rows):
        return None
    return {"line": line, "attacker_id": pokemon.id, "attacker_serial": pokemon.serial,
            "attacker_fingerprint": parent._bridge_pokemon_fingerprint(pokemon),
            "attacker_energy_rows": energy_rows, "attacker_energy_units": tuple(units),
            "attack_id": attack_id, "outcome_kind": outcome.kind.value, "outcome_amount": outcome.amount}

def certificate(parent: Any, obs: Any, snap: Any, parent_action: list[int]):
    api = _api()
    state = obs.current
    owner = state.yourIndex
    mine, theirs = state.players[owner], state.players[1 - owner]
    snapshot = _snapshot(parent, obs)
    exact_ends = [index for index, option in enumerate(obs.select.option) if api._option_is_exact(parent, option, parent.OptionType.END, owner)]
    if (
        snapshot is None or not _main_envelope(parent, obs) or not _fixed_metadata_is_exact(parent)
        or not api._options_are_unambiguous(parent, obs)
        or not api._parent_selected_exact_end(parent, obs, parent_action) or exact_ends != parent_action
        or core.INTEGRATED_TRANSACTION is not None or state.turn < 2 or not _all_statuses_clear(mine)
        or len(mine.active) != 1 or len(theirs.active) != 1 or not theirs.bench
        or len(mine.prize) <= 1 or mine.deckCount < 3 or not _visible_effects_are_clear(parent, state)
    ):
        return None
    source = mine.active[0]
    source_data = parent.card_table.get(source.id)
    if (
        source.id != DUDUNSPARCE or source_data is None or source.maxHp != source_data.hp
        or not 0 < source.hp < source.maxHp or not _stack_is_exact(parent, source, owner)
        or tuple(card.id for card in source.preEvolution) != (DUNSPARCE,)
        or len(source.energyCards) > 1 or len(source.tools) > 1
        or semantics.energy_units(parent, source) is None
    ):
        return None
    ability = _ability_action(parent, obs)
    target = theirs.active[0]
    target_fingerprint = api._target_fingerprint(parent, state, target, 1 - owner)
    if ability is None or target_fingerprint is None or not _one_prize_exact(parent, target, 1 - owner):
        return None
    attackers = []
    for bench_index, pokemon in enumerate(mine.bench):
        certified = _attacker_certificate(parent, obs, pokemon, target, mine.handCount + 3)
        if certified is not None:
            attackers.append((bench_index, pokemon, certified))
    if len(attackers) != 1:
        return None
    bench_index, attacker, attacker_data = attackers[0]
    source_moves = _moves(parent, source, parent.AreaType.ACTIVE)
    target_moves = _moves(parent, target, parent.AreaType.ACTIVE)
    protected = (*parent._bridge_pokemon_component_serials(source), *parent._bridge_pokemon_component_serials(attacker), *parent._bridge_pokemon_component_serials(target))
    if not parent._bridge_protected_serials_are_unique(state, protected) or len(source_moves) != 1 + len(source.preEvolution) + len(source.energyCards) + len(source.tools):
        return None
    hand = api._hand_fingerprint(parent, mine, owner)
    if hand is None:
        return None
    data = {
        **attacker_data, "owner": owner, "turn": state.turn,
        "start_action_count": state.turnActionCount, "source_serial": source.serial,
        "source_fingerprint": parent._bridge_pokemon_fingerprint(source),
        "source_component_serials": tuple(parent._bridge_pokemon_component_serials(source)),
        "source_moves": source_moves, "return_count": len(source_moves),
        "attacker_bench_index": bench_index, "target_id": target.id, "target_serial": target.serial,
        "target_hp": target.hp, "target_fingerprint": target_fingerprint, "target_moves": target_moves,
        "target_prizes": 1, "pre_draw_hand": hand, "expected_hand_count": mine.handCount + 3,
        "expected_deck": mine.deckCount - 3 + len(source_moves), "start_snapshot": snapshot,
        "initial_snapshot_hash": snap.sha256, "initial_parent_action": tuple(parent_action),
    }
    return data, ability

def build_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], data: dict, action: list[int]):
    ledger = ResourceLedger().assign_role(data["line"], BaseRole.H0)
    for row in data["attacker_energy_rows"]:
        ledger = None if ledger is None else ledger.reserve(f"energy:{row[1]}", BaseRole.H0, f"pay frozen attack {data['attack_id']}")
    budget = core.build_turn_budget(parent, obs, {"dudunsparce": bool(parent.ability_used_dudunsparce), "fezandipiti": bool(parent.ability_used_fezandipiti)})
    source_line = model.lineage_key(obs.current.players[data["owner"]].active[0], data["owner"])
    budget = budget.spend("ability", source_line) if source_line is not None else None
    if ledger is None or budget is None:
        return None
    plan = core._make_plan(
        parent, obs, snap.sha256, parent_action, KIND, action, stage="await_promotion",
        budget=budget, ledger=ledger, H0=data["line"],
        aborts=("exact three-card Run Away delta becomes stale", "frozen promotion, Energy, target, or KO becomes stale", "higher-precedence parent owner appears"),
        metadata={"source_serial": data["source_serial"], "attacker_serial": data["attacker_serial"], "target_serial": data["target_serial"], "intended_attack": data["attack_id"]},
    )
    transaction = {"kind": KIND, "stage": "await_promotion", "plan": plan, "data": data}
    return plan, action, {"transaction": transaction}

def _set_stage(transaction: dict[str, Any], stage: str) -> None:
    transaction["stage"] = stage
    transaction["plan"] = replace(transaction["plan"], expected_stage=stage)

def _draw_logs_are_exact(parent: Any, obs: Any, data: dict, new_hand: tuple) -> bool:
    owner = data["owner"]
    draw_logs = [log for log in obs.logs if int(getattr(log, "type", -1)) == 4]
    move_logs = [log for log in obs.logs if int(getattr(log, "type", -1)) == 6]
    other_logs = [log for log in obs.logs if int(getattr(log, "type", -1)) not in (4, 6)]
    if len(draw_logs) != 3 or len(move_logs) != data["return_count"] or len(other_logs) != 1 or not _log_is_exact(other_logs[0], 0, {"playerIndex": owner}):
        return False
    draw_rows = []
    for log in draw_logs:
        expected = {"playerIndex": owner, "cardId": getattr(log, "cardId", None), "serial": getattr(log, "serial", None)}
        if not _log_is_exact(log, 4, expected):
            return False
        draw_rows.append((expected["cardId"], expected["serial"], owner))
    if len(set(draw_rows)) != 3 or set(draw_rows) != set(new_hand):
        return False
    actual_moves = []
    for log in move_logs:
        expected = {"playerIndex": owner, "cardId": getattr(log, "cardId", None), "serial": getattr(log, "serial", None), "fromArea": getattr(log, "fromArea", None), "toArea": parent.AreaType.DECK}
        if not _log_is_exact(log, 6, expected):
            return False
        actual_moves.append((expected["cardId"], expected["serial"], int(expected["fromArea"])))
    return len(set(actual_moves)) == len(actual_moves) and set(actual_moves) == set(data["source_moves"])

def _promotion_action(parent: Any, obs: Any, data: dict):
    api = _api()
    state, select = obs.current, obs.select
    owner = data["owner"]
    mine = state.players[owner]
    snapshot = _snapshot(parent, obs, allow_empty_active=True)
    start = data["start_snapshot"]
    if (
        snapshot is None or state.yourIndex != owner or state.turn != data["turn"]
        or select.context != parent.SelectContext.TO_ACTIVE or int(select.type) != 1
        or select.minCount != 1 or select.maxCount != 1
        or getattr(select, "remainDamageCounter", 0) != 0 or getattr(select, "remainEnergyCost", 0) != 0
        or getattr(select, "deck", None) is not None or select.contextCard is not None or select.effect is not None
        or state.turnActionCount != data["start_action_count"] + 1 or snapshot["own_active"] != ()
        or snapshot["own_bench"] != start["own_bench"] or snapshot["own_deck"] != data["expected_deck"]
        or len(snapshot["own_hand"]) != data["expected_hand_count"]
        or not _snapshot_delta(snapshot, start, {"action_count", "own_active", "own_hand", "own_deck"})
        or any(serial in parent._bridge_public_serials(state) for serial in data["source_component_serials"])
    ):
        return None
    carried, current_hand = set(data["pre_draw_hand"]), tuple(snapshot["own_hand"])
    if len(carried) != len(data["pre_draw_hand"]) or not carried <= set(current_hand):
        return None
    new_hand = tuple(row for row in current_hand if row not in carried)
    if len(new_hand) != 3 or not _draw_logs_are_exact(parent, obs, data, new_hand):
        return None
    target = state.players[1 - owner].active[0]
    attacker = next((pokemon for pokemon in mine.bench if pokemon.serial == data["attacker_serial"]), None)
    certified = None if attacker is None else _attacker_certificate(parent, obs, attacker, target, mine.handCount)
    if attacker is None or parent._bridge_pokemon_fingerprint(attacker) != data["attacker_fingerprint"] or api._target_fingerprint(parent, state, target, 1 - owner) != data["target_fingerprint"] or certified is None or certified["attacker_energy_rows"] != data["attacker_energy_rows"]:
        return None
    matches = []
    for option_index, option in enumerate(select.option):
        pokemon = core._option_card(parent, obs, option)
        if option.type != parent.OptionType.CARD or option.area != parent.AreaType.BENCH or pokemon is None or not api._option_is_exact(parent, option, parent.OptionType.CARD, owner, area=parent.AreaType.BENCH, index=option.index):
            return None
        if pokemon.serial == data["attacker_serial"]:
            matches.append(option_index)
    if len(matches) != 1:
        return None
    data["post_draw_snapshot"], data["post_draw_hand"], data["new_draws"] = snapshot, current_hand, new_hand
    return [matches[0]]

def _attack_action(parent: Any, obs: Any, data: dict):
    api = _api()
    state, owner = obs.current, data["owner"]
    mine, theirs = state.players[owner], state.players[1 - owner]
    snapshot, post_draw = _snapshot(parent, obs), data.get("post_draw_snapshot")
    if (
        snapshot is None or post_draw is None or state.yourIndex != owner or state.turn != data["turn"]
        or not _main_envelope(parent, obs) or state.turnActionCount != data["start_action_count"] + 2
        or snapshot["own_hand"] != data["post_draw_hand"] or snapshot["own_deck"] != data["expected_deck"]
        or not _snapshot_delta(snapshot, post_draw, {"action_count", "own_active", "own_bench"})
        or len(mine.active) != 1 or len(theirs.active) != 1 or not _all_statuses_clear(mine)
    ):
        return None
    attacker, target = mine.active[0], theirs.active[0]
    expected_bench = list(post_draw["own_bench"])
    matches = [index for index, row in enumerate(expected_bench) if row[1] == data["attacker_serial"]]
    if len(matches) != 1:
        return None
    expected_bench.pop(matches[0])
    certified = _attacker_certificate(parent, obs, attacker, target, mine.handCount)
    if (
        snapshot["own_active"] != (data["attacker_fingerprint"],) or snapshot["own_bench"] != tuple(expected_bench)
        or parent._bridge_pokemon_fingerprint(attacker) != data["attacker_fingerprint"]
        or api._target_fingerprint(parent, state, target, 1 - owner) != data["target_fingerprint"]
        or certified is None or certified["attack_id"] != data["attack_id"]
        or certified["attacker_energy_rows"] != data["attacker_energy_rows"]
        or certified["attacker_energy_units"] != data["attacker_energy_units"]
        or not _visible_effects_are_clear(parent, state) or len(obs.logs) != 1
        or not _log_is_exact(obs.logs[0], 6, {"playerIndex": owner, "cardId": data["attacker_id"], "serial": data["attacker_serial"], "fromArea": parent.AreaType.BENCH, "toArea": parent.AreaType.ACTIVE})
    ):
        return None
    attacks = []
    for option_index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.ATTACK:
            continue
        if not api._option_is_exact(parent, option, parent.OptionType.ATTACK, owner, attackId=data["attack_id"]):
            return None
        attacks.append(option_index)
    if len(attacks) != 1:
        return None
    data["pre_attack_snapshot"] = snapshot
    data["actual_outcome_kind"], data["actual_outcome_amount"] = certified["outcome_kind"], certified["outcome_amount"]
    return [attacks[0]]

def _resolution_is_exact(parent: Any, obs: Any, data: dict) -> bool:
    api = _api()
    state, select, owner = obs.current, obs.select, data["owner"]
    mine, theirs = state.players[owner], state.players[1 - owner]
    before = data.get("pre_attack_snapshot")
    own_status = (mine.poisoned, mine.burned, mine.asleep, mine.paralyzed, mine.confused)
    opponent_status = (theirs.poisoned, theirs.burned, theirs.asleep, theirs.paralyzed, theirs.confused)
    fp = parent._bridge_pokemon_fingerprint
    if (
        before is None or state.yourIndex != owner or state.turn != data["turn"]
        or state.turnActionCount != data["start_action_count"] + 3 or state.result != -1 or state.looking is not None
        or select.context != parent.SelectContext.TO_HAND or int(select.type) != 1
        or select.minCount != 1 or select.maxCount != 1
        or getattr(select, "remainDamageCounter", 0) != 0 or getattr(select, "remainEnergyCost", 0) != 0
        or getattr(select, "deck", None) is not None or select.contextCard is not None or select.effect is not None
        or api._hand_fingerprint(parent, mine, owner) != before["own_hand"] or mine.deckCount != before["own_deck"]
        or len(mine.prize) != before["own_prizes"] or tuple(fp(p) for p in mine.active) != before["own_active"]
        or tuple(fp(p) for p in mine.bench) != before["own_bench"] or _card_rows(parent, mine.discard, owner) != before["own_discard"]
        or len(theirs.active) != 0 or tuple(fp(p) for p in theirs.bench) != before["opponent_bench"]
        or theirs.deckCount != before["opponent_deck"] or theirs.handCount != before["opponent_hand_count"]
        or len(theirs.prize) != before["opponent_prizes"] or own_status != before["own_status"]
        or opponent_status != before["opponent_status"] or _card_rows(parent, state.stadium, None) != before["stadium"]
    ):
        return False
    target_rows = tuple((card_id, serial, 1 - owner) for card_id, serial, _ in data["target_moves"])
    if _card_rows(parent, theirs.discard, 1 - owner) != before["opponent_discard"] + target_rows:
        return False
    for option in select.option:
        if option.type != parent.OptionType.CARD or option.area != parent.AreaType.PRIZE or not api._option_is_exact(parent, option, parent.OptionType.CARD, owner, area=parent.AreaType.PRIZE, index=option.index):
            return False
    logs = obs.logs
    if not select.option or len(logs) != 2 + len(data["target_moves"]):
        return False
    if not _log_is_exact(logs[0], 15, {"playerIndex": owner, "cardId": data["attacker_id"], "serial": data["attacker_serial"], "attackId": data["attack_id"]}):
        return False
    counters = data["actual_outcome_kind"] == OutcomeKind.PLACE_COUNTERS.value
    if not _log_is_exact(logs[1], 16, {"playerIndex": 1 - owner, "cardId": data["target_id"], "serial": data["target_serial"], "value": -data["actual_outcome_amount"], "putDamageCounter": counters}):
        return False
    for log, (card_id, serial, from_area) in zip(logs[2:], data["target_moves"]):
        if not _log_is_exact(log, 6, {"playerIndex": 1 - owner, "cardId": card_id, "serial": serial, "fromArea": parent.AreaType(from_area), "toArea": parent.AreaType.DISCARD}):
            return False
    return True

def advance(parent: Any, obs: Any, transaction: dict[str, Any]):
    api = _api()
    data, stage = transaction["data"], transaction["stage"]
    if api._parent_owner_now(parent):
        return "abort", None, "HIGHER_PRECEDENCE_PARENT_OWNER"
    if stage == "await_promotion":
        action = _promotion_action(parent, obs, data)
        if action is None:
            return "abort", None, "RUN_AWAY_DRAW_DELTA_OR_PROMOTION_STALE"
        _set_stage(transaction, "await_attack")
        return "override", action, "FROZEN_READY_ATTACKER_PROMOTION"
    if stage == "await_attack":
        action = _attack_action(parent, obs, data)
        if action is None:
            return "abort", None, "FROZEN_ATTACK_OR_KO_CERTIFICATE_STALE"
        _set_stage(transaction, "await_resolution")
        return "override", action, "FROZEN_CERTIFIED_KO_ATTACK"
    if stage == "await_resolution":
        if not _resolution_is_exact(parent, obs, data):
            return "abort", None, "ATTACK_KO_RESOLUTION_STALE"
        return "complete", None, "KO_VERIFIED_PRIZE_SELECTION_PARENT_OWNED"
    return "abort", None, "UNKNOWN_ACTIVE_DUDUNSPARCE_STAGE"
