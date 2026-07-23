"""Exact lexicographic arbitration and pre-override structural gate."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import planner_integrated as integrated
import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_semantics as semantics
import planner_validation as validation
from planner_model import BaseRole, OutcomeKind, PlanObjective, PrizeLane, ResourceLedger


_CONTINUATION_PARENT_ACTION: list[int] | None = None
_INSTALLED = False
_BASE_BUILD_TURN_BUDGET = runtime_model.build_turn_budget
_BASE_ADVANCE_TRANSACTION = core._advance_transaction
_BASE_DUPLICATE_ACTION = core._duplicate_action


PSYCHIC_READINESS_KIND = "PSYCHIC_ATTACK_READINESS_RESERVATION_V1"
SUPER_PSY_BOLT = 1071
_PSYCHIC_ATTACKS = {
    742: SUPER_PSY_BOLT,
    743: semantics.POWERFUL_HAND,
}
_PSYCHIC_ENERGIES = (semantics.BASIC_PSYCHIC, semantics.TELEPATH_PSYCHIC)


def _build_turn_budget(parent: Any, obs: Any, ability_flags: dict[str, bool]):
    budget = _BASE_BUILD_TURN_BUDGET(parent, obs, ability_flags)
    effect_id = getattr(getattr(obs.select, "effect", None), "id", None)
    # Hilda's second child prompt explicitly reserves the future manual attach;
    # no attack/Ability opportunity is exposed at this child callback.
    if (
        obs.select.context == parent.SelectContext.TO_HAND
        and effect_id == parent.Hilda
        and not bool(obs.current.energyAttached)
    ):
        budget = replace(budget, manual_attachment=True)
    return budget


def _ordered_draw_clock(parent: Any, obs: Any):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    own = model.DeckClock(mine.deckCount)
    opponent = model.DeckClock(theirs.deckCount)
    helmet_forced = 0
    if mine.active and any(card.id == semantics.LUCKY_HELMET for card in mine.active[0].tools):
        if semantics.public_positive_attack_response(parent, obs):
            helmet_forced = 2
    events = (
        ("current_optional_draw_or_search", 0, True),
        ("opponent_turn_helmet_or_fan", helmet_forced, helmet_forced == 0),
        ("next_mandatory_draw", 1, False),
        ("H1_or_recovery", 0, True),
        ("next_opponent_turn", 0, False),
        ("H2_mandatory_draw", 1, False),
    )
    for name, count, optional in events:
        advanced = own.after(name, count, optional)
        if advanced is None:
            return model.DrawClock(model.DeckClock(-1, own.ordered_draws + ((name, count, optional),)), opponent)
        own = advanced
    return model.DrawClock(own, opponent)


def _normalize_tie(*values: Any) -> tuple[str, ...]:
    return tuple(repr(value) for value in values)


def _action_source(parent: Any, obs: Any, action: list[int]):
    if len(action) != 1 or not 0 <= action[0] < len(obs.select.option):
        return None, None
    option = obs.select.option[action[0]]
    return option, core._option_card(parent, obs, option)


def _parent_objective(parent: Any, obs: Any, action: list[int], roles: Any) -> PlanObjective:
    base = semantics.objective_for_state(parent, obs, roles, tie=())
    option, source = _action_source(parent, obs, action)
    abandoned = 0
    preserve_h0 = base.preserve_H0_lethal
    preserve_h1 = base.preserve_H1_attack
    preserve_h2 = base.preserve_H2_route
    if source is not None and source.id == semantics.TELEPATH_PSYCHIC and not semantics.has_psychic_telepath_target(parent, obs):
        abandoned += 1
    if option is not None and option.type == parent.OptionType.END and roles.H0 is None and roles.H1 is None:
        preserve_h2 = False
    lethal = core._h0_lethal_powerful_hand(parent, obs)
    if lethal is not None and option is not None and option.type != parent.OptionType.ATTACK:
        required = lethal[1]
        if not core._parent_step_retains_h0_and_successor(parent, obs, option, required):
            preserve_h0 = False
    keys = tuple(
        runtime_model.stable_option_key(parent, obs, obs.select.option[index])
        for index in action
    ) if model.action_is_valid(obs, action) else ()
    return replace(
        base,
        preserve_H0_lethal=preserve_h0,
        preserve_H1_attack=preserve_h1,
        preserve_H2_route=preserve_h2,
        fewer_abandoned_reservations=-abandoned,
        stable_semantic_tie_break=_normalize_tie("parent_fallback", keys),
    )


def _candidate_objective(parent: Any, obs: Any, plan: Any, roles: Any) -> PlanObjective:
    kind = dict(plan.metadata).get("kind", "")
    base = semantics.objective_for_state(parent, obs, roles, tie=())
    win_now = base.win_now
    avoid_loss = base.avoid_public_forced_loss
    preserve_h0 = base.preserve_H0_lethal
    preserve_h1 = base.preserve_H1_attack
    preserve_h2 = base.preserve_H2_route
    prizes_now = base.prizes_now
    deck = obs.current.players[obs.current.yourIndex].deckCount
    if kind == "TERMINAL_PSYCHIC_ATTACH_V5":
        win_now = True
        preserve_h0 = True
        prizes_now = len(obs.current.players[obs.current.yourIndex].prize)
    elif kind == "POWERFUL_HAND_FLOOR":
        preserve_h0 = True
    elif kind == "HILDA_ENRICHING_SETUP":
        preserve_h2 = True
        deck -= 5
    elif kind == "RUN_AWAY_SETUP_CLOCK":
        preserve_h2 = True
        deck -= min(3, deck)
    elif kind == "HANDHELD_FAN_RESPONSE":
        preserve_h2 = True
        avoid_loss = True
    elif kind == "INTEGRATED_SETUP_STOP_ATTACK":
        preserve_h0 = True
    lane_attacks = plan.prize_lane.attacks if plan.prize_lane.certified else 999
    return replace(
        base,
        win_now=win_now,
        avoid_public_forced_loss=avoid_loss,
        preserve_H0_lethal=preserve_h0,
        prizes_now=prizes_now,
        preserve_H1_attack=preserve_h1,
        preserve_H2_route=preserve_h2,
        shorter_certified_prize_lane=-lane_attacks,
        # All surviving plan reservations are named and consumed; required
        # reservations are not "abandoned" and receive no penalty.
        fewer_abandoned_reservations=0,
        safer_deck_clock=max(0, deck),
        stable_semantic_tie_break=_normalize_tie("integrated", kind, plan.plan_id),
    )


def _add_missing_role_for_reservations(parent: Any, obs: Any, plan: Any):
    ledger = plan.resource_ledger
    assigned = set(role for _, role in ledger.roles)
    missing = {reservation.role for reservation in ledger.reservations} - assigned
    if not missing:
        return plan
    owner = obs.current.yourIndex
    public = list(obs.current.players[owner].active) + list(obs.current.players[owner].bench)
    for role in sorted(missing, key=lambda row: row.value):
        free = None
        occupied = dict(ledger.roles)
        for pokemon in public:
            line = model.lineage_key(pokemon, owner)
            if line is not None and line not in occupied:
                free = line
                break
        if free is None:
            return None
        ledger = ledger.assign_role(free, role)
        if ledger is None:
            return None
    return replace(plan, resource_ledger=ledger)


def _restore_lost_named_reservation(parent: Any, obs: Any, plan: Any):
    metadata = dict(plan.metadata)
    kind = metadata.get("kind")
    ledger = plan.resource_ledger
    if kind == "HANDHELD_FAN_RESPONSE":
        token = f"tool:{metadata.get('fan_serial')}"
        if not any(row.token == token for row in ledger.reservations):
            role_map = dict(ledger.roles)
            line = model.lineage_key(obs.current.players[obs.current.yourIndex].active[0], obs.current.yourIndex)
            role = role_map.get(line)
            if role is None:
                return None
            ledger = ledger.reserve(token, role, "Handheld Fan public response")
            if ledger is None:
                return None
    return replace(plan, resource_ledger=ledger)


def _certify_candidate(parent: Any, obs: Any, candidate: Any):
    plan, action, commit = candidate
    certificate = integrated._domain_certificate(parent, obs, list(plan.fallback), candidate)
    if not certificate["eligible"]:
        return None
    integrated._replace_plan_evidence.parent = parent
    integrated._replace_plan_evidence.obs = obs
    plan = integrated._replace_plan_evidence(plan, certificate)
    plan = _restore_lost_named_reservation(parent, obs, plan)
    plan = _add_missing_role_for_reservations(parent, obs, plan) if plan is not None else None
    if plan is None:
        return None
    roles = certificate["roles"]
    plan = replace(plan, objective=_candidate_objective(parent, obs, plan, roles))
    ok, _ = validation.validate_plan(parent, obs, plan, action, current_stage=plan.expected_stage)
    if not ok:
        return None
    if commit and commit.get("transaction"):
        commit["transaction"]["plan"] = plan
    return plan, action, commit


def _setup_stop_candidate(parent: Any, obs: Any, snap: Any, parent_action: list[int], roles: Any):
    attack = integrated._one_attack(parent, obs, roles)
    option, source = _action_source(parent, obs, parent_action)
    if attack is None or option is None or option.type == parent.OptionType.ATTACK:
        return None
    if option.type not in (parent.OptionType.PLAY, parent.OptionType.ABILITY, parent.OptionType.END):
        return None
    protected = {
        semantics.BOSS_ORDERS,
        semantics.ENHANCED_HAMMER,
        semantics.NIGHT_STRETCHER,
        semantics.SACRED_ASH,
        semantics.BATTLE_CAGE,
    }
    if source is not None and source.id in protected:
        return None
    plan = core._make_plan(
        parent,
        obs,
        snap.sha256,
        parent_action,
        "INTEGRATED_SETUP_STOP_ATTACK",
        attack,
        stage="single_attack",
        H0=roles.H0.line if roles.H0 else None,
        H1=roles.H1.line if roles.H1 else None,
        H2=roles.H2.line if roles.H2 else None,
        ledger=roles.ledger,
        aborts=("H0 no longer ready", "optional step gains certified continuity"),
        metadata={"dependency_order": integrated.DEPENDENCY_ORDER},
    )
    return plan, attack, None


def _exact_immediate_prize_or_terminal(parent: Any, obs: Any, action: list[int]) -> bool:
    '''Certify a unique current attack that KOs the public Active now.'''
    option, _ = _action_source(parent, obs, action)
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    if (
        option is None
        or option.type != parent.OptionType.ATTACK
        or len(mine.active) != 1
        or len(theirs.active) != 1
    ):
        return False
    matching = [
        index
        for index, candidate in enumerate(obs.select.option)
        if candidate.type == parent.OptionType.ATTACK
        and candidate.attackId == option.attackId
    ]
    if matching != action:
        return False
    target = theirs.active[0]
    if (
        option.attackId != core.POWERFUL_HAND
        or mine.hand is None
        or len(mine.hand) != mine.handCount
        or not parent._powerful_hand_target_is_publicly_clear(obs.current, target)
    ):
        return False
    outcome = integrated._target_outcome(
        parent,
        obs,
        mine.active[0],
        target,
        option.attackId,
    )
    if outcome is None or integrated._hits_to_ko(outcome, target.hp) != 1:
        return False
    prizes = semantics.prize_value(parent, target)
    prize_now = prizes is not None and prizes >= 1
    terminal_now = not theirs.bench or (
        prizes is not None and prizes >= len(mine.prize)
    )
    return prize_now or terminal_now


def _exact_lethal_floor_guard(
    parent: Any,
    obs: Any,
    snap: Any,
    parent_action: list[int],
    action: list[int],
) -> bool:
    '''Require an exact floor plus a deterministic parent transition below it.'''
    floor = core._build_powerful_hand_floor(parent, obs, snap, parent_action)
    lethal = core._h0_lethal_powerful_hand(parent, obs)
    chosen = core._parent_chosen_option(obs, parent_action)
    if floor is None or lethal is None or chosen is None or floor[1] != action:
        return False
    _, required, _, _ = lethal
    if chosen.type != parent.OptionType.PLAY:
        return False
    if core._parent_step_retains_h0_and_successor(parent, obs, chosen, required):
        return False
    mine = obs.current.players[obs.current.yourIndex]
    source = core._option_card(parent, obs, chosen)
    data = parent.card_table.get(source.id) if source is not None else None
    unchanged_deck_basics = {
        getattr(parent, 'Abra', -1),
        getattr(parent, 'Dunsparce', -1),
        getattr(parent, 'Psyduck', -1),
        semantics.SHAYMIN,
        semantics.GENESECT,
        semantics.FEZANDIPITI_EX,
    }
    return (
        mine.hand is not None
        and len(mine.hand) == mine.handCount
        and source is not None
        and source.id in unchanged_deck_basics
        and data is not None
        and data.cardType == parent.CardType.POKEMON
        and data.basic
        and any(card.serial == source.serial for card in mine.hand)
        and mine.handCount - 1 < required
    )


def _exact_post_resolution_surviving_board(parent: Any, obs: Any, plan: Any) -> bool:
    '''Require a known Pokemon to remain after Run Away removes its source.'''
    source_serial = dict(plan.metadata).get('source_serial')
    if type(source_serial) is not int:
        return False
    mine = obs.current.players[obs.current.yourIndex]
    survivors = [
        pokemon
        for pokemon in list(mine.active) + list(mine.bench)
        if getattr(pokemon, 'serial', None) != source_serial
    ]
    return any(
        type(getattr(pokemon, 'serial', None)) is int
        and getattr(pokemon, 'id', None) in parent.card_table
        and parent.card_table[pokemon.id].cardType == parent.CardType.POKEMON
        for pokemon in survivors
    )


def _admit_integrated_override(
    parent: Any,
    obs: Any,
    snap: Any,
    parent_action: list[int],
    candidate: Any,
) -> tuple[bool, str]:
    '''Apply the fail-closed gate after all inherited admission checks.'''
    plan, action, _ = candidate
    kind = dict(plan.metadata).get('kind')
    if kind == 'INTEGRATED_SETUP_STOP_ATTACK' and not (
        _exact_immediate_prize_or_terminal(parent, obs, action)
        or _exact_lethal_floor_guard(parent, obs, snap, parent_action, action)
    ):
        return False, 'setup-stop lacks exact immediate Prize/terminal or exact lethal-floor guard'
    if kind == 'RUN_AWAY_SETUP_CLOCK' and not _exact_post_resolution_surviving_board(
        parent, obs, plan
    ):
        return False, 'Run Away source removal leaves no publicly known Pokemon'
    return True, ''


def _card_fingerprint(card: Any) -> tuple[int, int, int] | None:
    return model.card_row(card)


def _hand_fingerprint(parent: Any, player: Any, owner: int):
    hand = getattr(player, "hand", None)
    if hand is None or len(hand) != getattr(player, "handCount", -1):
        return None
    rows = tuple(_card_fingerprint(card) for card in hand)
    if (
        any(row is None or row[2] != owner or parent.card_table.get(row[0]) is None for row in rows)
        or len({row[1] for row in rows}) != len(rows)
    ):
        return None
    return rows


def _pokemon_static_fingerprint(parent: Any, pokemon: Any, owner: int):
    if not parent._bridge_pokemon_is_publicly_complete(pokemon, owner):
        return None
    lineage_complete = parent._two_prize_lineage_is_complete(pokemon, owner)
    if pokemon.id == parent.Alakazam:
        lineage_complete = lineage_complete or parent._two_prize_alakazam_lineage_is_complete(
            pokemon, owner
        )
    if not lineage_complete:
        return None
    tools = tuple(_card_fingerprint(card) for card in (pokemon.tools or []))
    lineage = tuple(_card_fingerprint(card) for card in (pokemon.preEvolution or []))
    if any(row is None for row in tools + lineage):
        return None
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        bool(pokemon.appearThisTurn),
        tools,
        lineage,
    )


def _target_fingerprint(parent: Any, state: Any, target: Any, owner: int):
    if not parent._bridge_pokemon_is_publicly_complete(target, owner):
        return None
    return parent._bridge_target_fingerprint(target, state.players[owner])


def _status_is_unlocked(player: Any) -> bool:
    values = (
        player.poisoned,
        player.burned,
        player.asleep,
        player.paralyzed,
        player.confused,
    )
    return all(type(value) is bool for value in values) and not any(
        (player.asleep, player.paralyzed, player.confused)
    )


def _options_are_unambiguous(parent: Any, obs: Any) -> bool:
    keys = tuple(
        runtime_model.stable_option_key(parent, obs, option)
        for option in obs.select.option
    )
    return not any(key is None for key in keys) and len(keys) == len(set(keys))


def _option_is_exact(parent: Any, option: Any, option_type: Any, owner: int, **expected: Any) -> bool:
    for field, value in vars(option).items():
        if field == "type":
            wanted = option_type
        elif field == "playerIndex":
            if value not in (None, owner):
                return False
            wanted = value
        else:
            wanted = expected.get(field)
        if value != wanted:
            return False
    return True


def _strict_positive_outcome(
    parent: Any,
    obs: Any,
    attacker: Any,
    target: Any,
    attack_id: int,
    hand_count: int,
):
    state = obs.current
    target_clear = parent._powerful_hand_target_is_publicly_clear(state, target)
    if not target_clear and target.id == semantics.SHAYMIN:
        target_data = parent.card_table.get(target.id)
        skills = tuple(
            parent._normalized_skill_text(skill.text)
            for skill in (target_data.skills or ())
        ) if target_data is not None else ()
        target_clear = (
            target_data is not None
            and target_data.resistance != parent.EnergyType.PSYCHIC
            and not target.energyCards
            and not target.tools
            and not state.stadium
            and len(skills) == 1
            and "prevent all damage done to your benched pokemon" in skills[0]
            and "rule box" in skills[0]
        )
    if not target_clear:
        target_data = parent.card_table.get(target.id)
        neutral_zone_only = (
            target_data is not None
            and attacker.id in (parent.Kadabra, parent.Alakazam)
            and not parent.card_table[attacker.id].ex
            and not parent.card_table[attacker.id].megaEx
            and target_data.resistance != parent.EnergyType.PSYCHIC
            and semantics.MIST_ENERGY not in {card.id for card in target.energyCards}
            and not (
                20 in {card.id for card in target.energyCards}
                and target_data.energyType == parent.EnergyType.FIGHTING
            )
            and all(
                parent.card_table.get(card.id) is not None
                and (
                    parent.card_table[card.id].cardType == parent.CardType.BASIC_ENERGY
                    or card.id in (12, semantics.ENRICHING_ENERGY, semantics.TELEPATH_PSYCHIC, 20)
                )
                for card in target.energyCards
            )
            and not target.tools
            and len(state.stadium) == 1
            and state.stadium[0].id == 1247
            and not any(
                parent._skill_may_change_powerful_hand_damage(skill.text)
                for skill in (target_data.skills or ())
            )
        )
        target_clear = neutral_zone_only
    if hand_count < 0 or not target_clear:
        return None
    attack = parent.attack_table.get(attack_id)
    if attack is None or attack.attackId != attack_id:
        return None
    expected_kind = (
        OutcomeKind.PLACE_COUNTERS
        if attack_id == semantics.POWERFUL_HAND
        else OutcomeKind.ATTACK_DAMAGE
    )
    if expected_kind is OutcomeKind.ATTACK_DAMAGE:
        target_data = parent.card_table.get(target.id)
        if target_data is None:
            return None
        target_attacks = tuple(
            (printed_id, parent.attack_table.get(printed_id))
            for printed_id in (target_data.attacks or ())
        )
        if any(
            printed is None or printed.attackId != printed_id
            for printed_id, printed in target_attacks
        ):
            return None
        for _, printed in target_attacks:
            text = parent._normalized_skill_text(printed.text)
            if (
                "during your opponent's next turn" in text
                and ("less damage" in text or "prevent all damage" in text)
            ):
                return None
    outcome = semantics.outcome_for_attack(
        parent,
        attacker,
        attack,
        target,
        hand_count=hand_count,
    )
    outcome = semantics.resolve_public_outcome(
        parent,
        state,
        attacker,
        target,
        outcome,
        target_is_bench=False,
    )
    if (
        outcome.kind is not expected_kind
        or outcome.prevented
        or type(outcome.amount) is not int
        or outcome.amount <= 0
    ):
        return None
    return outcome


def _certify_psychic_attacker(
    parent: Any,
    obs: Any,
    pokemon: Any,
    owner: int,
    target: Any,
    post_attach_hand_count: int,
):
    attack_id = _PSYCHIC_ATTACKS.get(getattr(pokemon, "id", None))
    static = _pokemon_static_fingerprint(parent, pokemon, owner)
    line = model.lineage_key(pokemon, owner)
    data = parent.card_table.get(getattr(pokemon, "id", None))
    attack = parent.attack_table.get(attack_id)
    units = semantics.energy_units(parent, pokemon)
    psychic = int(parent.EnergyType.PSYCHIC)
    if (
        attack_id is None
        or static is None
        or line is None
        or data is None
        or tuple(data.attacks or ()) != (attack_id,)
        or attack is None
        or attack.attackId != attack_id
        or tuple(int(value) for value in (attack.energies or ())) != (psychic,)
        or units is None
        or semantics.missing_energy(parent, units, attack.energies) != (psychic,)
        or semantics.missing_energy(parent, units + (psychic,), attack.energies)
    ):
        return None
    outcome = _strict_positive_outcome(
        parent,
        obs,
        pokemon,
        target,
        attack_id,
        post_attach_hand_count,
    )
    if outcome is None:
        return None
    energy_rows = tuple(_card_fingerprint(card) for card in (pokemon.energyCards or []))
    if any(row is None or row[2] != owner for row in energy_rows):
        return None
    return {
        "line": line,
        "attacker_id": pokemon.id,
        "attacker_serial": pokemon.serial,
        "attacker_static": static,
        "pre_energy_cards": energy_rows,
        "pre_energy_units": tuple(units),
        "attack_id": attack_id,
        "initial_outcome": (outcome.kind.value, outcome.amount, outcome.prevented),
    }


def _psychic_energy_is_exact(parent: Any, energy: Any, owner: int) -> bool:
    row = _card_fingerprint(energy)
    data = parent.card_table.get(getattr(energy, "id", None))
    if row is None or row[2] != owner or energy.id not in _PSYCHIC_ENERGIES or data is None:
        return False
    if energy.id == semantics.BASIC_PSYCHIC:
        return (
            data.cardType == parent.CardType.BASIC_ENERGY
            and int(data.energyType) == int(parent.EnergyType.PSYCHIC)
        )
    return (
        data.cardType == parent.CardType.SPECIAL_ENERGY
        and int(data.energyType) == int(parent.EnergyType.PSYCHIC)
        and parent._active_psychic_telepath_text_certified()
    )
def _attach_rows(parent: Any, obs: Any, data: dict[str, Any]):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    target_area = parent.AreaType.ACTIVE if data["origin_role"] == "H0" else parent.AreaType.BENCH
    target_index = 0 if data["origin_role"] == "H0" else data["bench_index"]
    rows = []
    for option_index, option in enumerate(obs.select.option):
        if (
            option.type != parent.OptionType.ATTACH
            or option.area != parent.AreaType.HAND
            or option.inPlayArea != target_area
            or option.inPlayIndex != target_index
            or not isinstance(option.index, int)
            or isinstance(option.index, bool)
            or not 0 <= option.index < len(mine.hand or [])
            or not _option_is_exact(
                parent,
                option,
                parent.OptionType.ATTACH,
                owner,
                area=parent.AreaType.HAND,
                index=option.index,
                inPlayArea=target_area,
                inPlayIndex=target_index,
            )
        ):
            continue
        energy = mine.hand[option.index]
        if not _psychic_energy_is_exact(parent, energy, owner):
            continue
        key = runtime_model.stable_option_key(parent, obs, option)
        if key is None:
            return None
        rows.append(
            (
                0 if energy.id == semantics.BASIC_PSYCHIC else 1,
                energy.serial,
                repr(key),
                option_index,
                option.index,
                energy,
                key,
            )
        )
    return sorted(rows, key=lambda row: row[:3])


def _parent_consumes_attachment(parent: Any, obs: Any, action: list[int]):
    option, source = _action_source(parent, obs, action)
    owner = obs.current.yourIndex
    if option is None:
        return None
    if option.type == parent.OptionType.END:
        if not _option_is_exact(parent, option, parent.OptionType.END, owner):
            return None
        return "END"
    if option.type != parent.OptionType.ATTACH or source is None:
        return None
    data = parent.card_table.get(source.id)
    target = core._target_pokemon(parent, obs, option)
    if (
        data is None
        or data.cardType not in (parent.CardType.BASIC_ENERGY, parent.CardType.SPECIAL_ENERGY)
        or target is None
        or option.area != parent.AreaType.HAND
        or option.inPlayArea not in (parent.AreaType.ACTIVE, parent.AreaType.BENCH)
        or not _option_is_exact(
            parent,
            option,
            parent.OptionType.ATTACH,
            owner,
            area=parent.AreaType.HAND,
            index=option.index,
            inPlayArea=option.inPlayArea,
            inPlayIndex=option.inPlayIndex,
        )
    ):
        return None
    return "ATTACH"


def _psychic_readiness_certificate(
    parent: Any,
    obs: Any,
    snap: Any,
    parent_action: list[int],
):
    state = obs.current
    select = obs.select
    owner = state.yourIndex
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    hand = _hand_fingerprint(parent, mine, owner)
    if (
        select.context != parent.SelectContext.MAIN
        or int(select.type) != 0
        or select.minCount != 1
        or select.maxCount != 1
        or select.effect is not None
        or select.contextCard is not None
        or state.result != -1
        or state.turn < 2
        or state.looking is not None
        or bool(state.energyAttached)
        or hand is None
        or not _status_is_unlocked(mine)
        or not _options_are_unambiguous(parent, obs)
        or len(mine.active) != 1
        or len(theirs.active) != 1
    ):
        return None
    target = theirs.active[0]
    target_fingerprint = _target_fingerprint(parent, state, target, 1 - owner)
    if target_fingerprint is None:
        return None
    attacker_data = _certify_psychic_attacker(
        parent,
        obs,
        mine.active[0],
        owner,
        target,
        mine.handCount - 1,
    )
    role = "H0" if attacker_data is not None else "H1"
    bench_index = None
    if attacker_data is None:
        if mine.active[0].id in (parent.Abra, parent.Kadabra, parent.Alakazam):
            return None
        if any(
            option.type in (parent.OptionType.ATTACK, parent.OptionType.RETREAT)
            for option in select.option
        ):
            return None
        bench_candidates = []
        for index, pokemon in enumerate(mine.bench):
            certified = _certify_psychic_attacker(
                parent,
                obs,
                pokemon,
                owner,
                target,
                mine.handCount - 1,
            )
            if certified is not None:
                bench_candidates.append((index, certified))
        if len(bench_candidates) != 1:
            return None
        bench_index, attacker_data = bench_candidates[0]
    data = {
        **attacker_data,
        "origin_role": role,
        "role": role,
        "owner": owner,
        "turn": state.turn,
        "turn_action_count": state.turnActionCount,
        "bench_index": bench_index,
        "original_active_serial": mine.active[0].serial,
        "original_active_fingerprint": parent._bridge_pokemon_fingerprint(mine.active[0]),
        "target_serial": target.serial,
        "target_fingerprint": target_fingerprint,
        "initial_snapshot_hash": snap.sha256,
    }
    attach_rows = _attach_rows(parent, obs, data)
    trigger = _parent_consumes_attachment(parent, obs, parent_action)
    if not attach_rows or trigger is None:
        return None
    _, _, _, action_index, hand_index, energy, option_key = attach_rows[0]
    protected = [
        *parent._bridge_pokemon_component_serials(
            mine.active[0] if role == "H0" else mine.bench[bench_index]
        ),
        *parent._bridge_pokemon_component_serials(target),
        energy.serial,
    ]
    if not parent._bridge_protected_serials_are_unique(state, protected):
        return None
    data.update(
        energy_id=energy.id,
        energy_serial=energy.serial,
        energy_fingerprint=_card_fingerprint(energy),
        attach_option_key=option_key,
        expected_hand=hand[:hand_index] + hand[hand_index + 1 :],
        trigger=trigger,
        initial_parent_action=tuple(parent_action),
        returned_attach_action=(action_index,),
        parent_identical=parent_action == [action_index],
        saw_switch_prompt=False,
    )
    return data, [action_index]


def _psychic_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], data: dict[str, Any], action: list[int]):
    role = BaseRole.H0 if data["origin_role"] == "H0" else BaseRole.H1
    ledger = ResourceLedger().assign_role(data["line"], role)
    if ledger is None:
        return None
    ledger = ledger.reserve(
        f"energy:{data['energy_serial']}",
        role,
        f"pay exact Psychic attack {data['attack_id']}",
    )
    budget = core.build_turn_budget(
        parent,
        obs,
        {
            "dudunsparce": bool(parent.ability_used_dudunsparce),
            "fezandipiti": bool(parent.ability_used_fezandipiti),
        },
    )
    budget = budget.spend("manual_attachment")
    if ledger is None or budget is None:
        return None
    plan = core._make_plan(
        parent,
        obs,
        snap.sha256,
        parent_action,
        PSYCHIC_READINESS_KIND,
        action,
        stage="await_attach_resolution",
        budget=budget,
        ledger=ledger,
        H0=data["line"] if role is BaseRole.H0 else None,
        H1=data["line"] if role is BaseRole.H1 else None,
        aborts=(
            "reserved attacker or Energy becomes stale",
            "exact positive public attack ceases to exist",
            "higher-precedence parent owner appears",
        ),
        metadata={
            "origin_role": data["origin_role"],
            "attacker_serial": data["attacker_serial"],
            "energy_id": data["energy_id"],
            "energy_serial": data["energy_serial"],
            "intended_attack": data["attack_id"],
        },
    )
    transaction = {
        "kind": PSYCHIC_READINESS_KIND,
        "stage": "await_attach_resolution",
        "plan": plan,
        "data": data,
    }
    return plan, action, {"transaction": transaction}


def _psychic_trace(
    classification: str,
    transaction: dict[str, Any],
    snapshot_hash: str | None,
    parent_action: list[int],
    returned_action: list[int],
    reason_code: str,
    *,
    stage: str | None = None,
) -> None:
    data = transaction["data"]
    plan = transaction["plan"]
    trace_stage = stage or transaction["stage"]
    core._trace(
        classification,
        plan,
        snapshot_hash,
        parent_action=parent_action,
        override_action=returned_action,
        reason=reason_code,
        stage=trace_stage,
    )
    row = core.INTEGRATED_LATEST_TRACE
    if row is not None:
        row.update(
            psychic_role=data.get("role"),
            origin_role=data.get("origin_role"),
            psychic_lineage=tuple(data.get("line") or ()),
            attacker_serial=data.get("attacker_serial"),
            energy_id=data.get("energy_id"),
            energy_serial=data.get("energy_serial"),
            intended_attack=data.get("attack_id"),
            exact_parent_action=tuple(parent_action),
            exact_returned_action=tuple(returned_action),
            public_snapshot_hash=snapshot_hash,
            reason_code=reason_code,
        )
    data["last_parent_action"] = tuple(parent_action)
    data["last_returned_action"] = tuple(returned_action)


def _set_psychic_stage(transaction: dict[str, Any], stage: str) -> None:
    transaction["stage"] = stage
    transaction["plan"] = replace(transaction["plan"], expected_stage=stage)


def _current_snapshot_hash(parent: Any, obs: Any):
    snap = core.public_snapshot(parent, obs)
    return snap.sha256 if snap is not None else None


def _current_parent_action(parent: Any, obs: Any) -> list[int]:
    if _CONTINUATION_PARENT_ACTION is not None:
        return list(_CONTINUATION_PARENT_ACTION)

    action = getattr(parent, "_last_decision_action", None)
    if isinstance(action, (list, tuple)):
        parsed = list(action)
        if model.action_is_valid(obs, parsed):
            return parsed
    return []
def _find_reserved(parent: Any, obs: Any, data: dict[str, Any]):
    owner = data["owner"]
    mine = obs.current.players[owner]
    matches = []
    for area, pokemon in (
        *((parent.AreaType.ACTIVE, pokemon) for pokemon in mine.active),
        *((parent.AreaType.BENCH, pokemon) for pokemon in mine.bench),
    ):
        if (
            pokemon.serial == data["attacker_serial"]
            and model.lineage_key(pokemon, owner) == data["line"]
        ):
            matches.append((area, pokemon))
    return matches[0] if len(matches) == 1 else None


def _reservation_is_exact(parent: Any, obs: Any, data: dict[str, Any]) -> bool:
    state = obs.current
    owner = data["owner"]
    if state.yourIndex != owner or len(state.players) != 2:
        return False
    found = _find_reserved(parent, obs, data)
    if found is None:
        return False
    _, attacker = found
    static = _pokemon_static_fingerprint(parent, attacker, owner)
    turn_delta = state.turn - data["turn"]
    expected_static = tuple(data["attacker_static"])
    if turn_delta in (1, 2):
        expected_static = expected_static[:4] + (False,) + expected_static[5:]
    elif turn_delta != 0:
        return False
    energy_rows = tuple(_card_fingerprint(card) for card in (attacker.energyCards or []))
    units = semantics.energy_units(parent, attacker)
    expected_rows = tuple(data["pre_energy_cards"]) + (data["energy_fingerprint"],)
    expected_units = tuple(data["pre_energy_units"]) + (int(parent.EnergyType.PSYCHIC),)
    attack = parent.attack_table.get(data["attack_id"])
    return (
        static == expected_static
        and len(energy_rows) == len(expected_rows)
        and sorted(energy_rows) == sorted(expected_rows)
        and energy_rows.count(data["energy_fingerprint"]) == 1
        and units is not None
        and sorted(units) == sorted(expected_units)
        and attack is not None
        and not semantics.missing_energy(parent, units, attack.energies)
    )


def _post_attach_is_exact(parent: Any, obs: Any, data: dict[str, Any]) -> bool:
    state = obs.current
    owner = data["owner"]
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    hand = _hand_fingerprint(parent, mine, owner)
    found = _find_reserved(parent, obs, data)
    if (
        state.turn != data["turn"]
        or state.yourIndex != owner
        or not bool(state.energyAttached)
        or hand != tuple(data["expected_hand"])
        or found is None
        or not _reservation_is_exact(parent, obs, data)
        or len(theirs.active) != 1
        or theirs.active[0].serial != data["target_serial"]
        or _target_fingerprint(parent, state, theirs.active[0], 1 - owner)
        != data["target_fingerprint"]
    ):
        return False
    expected_area = (
        parent.AreaType.ACTIVE
        if data["origin_role"] == "H0"
        else parent.AreaType.BENCH
    )
    return found[0] == expected_area


def _optional_telepath_prompt_is_exact(parent: Any, obs: Any, data: dict[str, Any]) -> bool:
    select = obs.select
    owner = data["owner"]
    mine = obs.current.players[owner]
    effect_ids = {
        getattr(select.effect, "id", None),
        getattr(select.contextCard, "id", None),
    }
    effect_ids.discard(None)
    if (
        data["energy_id"] != semantics.TELEPATH_PSYCHIC
        or select.context != parent.SelectContext.TO_BENCH
        or int(select.type) != 1
        or select.minCount != 0
        or not 0 <= select.maxCount <= 2
        or effect_ids != {semantics.TELEPATH_PSYCHIC}
        or select.maxCount > max(0, mine.benchMax - len(mine.bench))
        or not _options_are_unambiguous(parent, obs)
    ):
        return False
    serials = []
    for option in select.option:
        card = core._option_card(parent, obs, option)
        card_data = parent.card_table.get(getattr(card, "id", None))
        if (
            option.type != parent.OptionType.CARD
            or option.area not in (parent.AreaType.DECK, parent.AreaType.LOOKING)
            or card is None
            or card_data is None
            or card_data.cardType != parent.CardType.POKEMON
            or not card_data.basic
            or int(card_data.energyType) != int(parent.EnergyType.PSYCHIC)
            or not _option_is_exact(
                parent,
                option,
                parent.OptionType.CARD,
                owner,
                area=option.area,
                index=option.index,
            )
        ):
            return False
        serials.append(card.serial)
    return len(serials) == len(set(serials))


def _prepare_current_target(parent: Any, obs: Any, data: dict[str, Any]) -> bool:
    owner = data["owner"]
    theirs = obs.current.players[1 - owner]
    if len(theirs.active) != 1:
        return False
    target = theirs.active[0]
    fingerprint = _target_fingerprint(parent, obs.current, target, 1 - owner)
    found = _find_reserved(parent, obs, data)
    if found is None or fingerprint is None:
        return False
    _, attacker = found
    outcome = _strict_positive_outcome(
        parent,
        obs,
        attacker,
        target,
        data["attack_id"],
        obs.current.players[owner].handCount,
    )
    if outcome is None:
        return False
    if (
        data.get("origin_role") == "H1"
        and obs.select.context in (parent.SelectContext.SWITCH, parent.SelectContext.TO_ACTIVE)
        and isinstance(fingerprint, tuple)
        and len(fingerprint) > 4
    ):
        fingerprint = fingerprint[:4] + (False,) + fingerprint[5:]
    data["target_serial"] = target.serial
    data["target_fingerprint"] = fingerprint
    return True


def _exact_attack_action(parent: Any, obs: Any, data: dict[str, Any]):
    state = obs.current
    select = obs.select
    owner = data["owner"]
    mine = state.players[owner]
    theirs = state.players[1 - owner]
    found = _find_reserved(parent, obs, data)
    if (
        state.yourIndex != owner
        or select.context != parent.SelectContext.MAIN
        or int(select.type) != 0
        or select.minCount != 1
        or select.maxCount != 1
        or len(mine.active) != 1
        or found is None
        or found[0] != parent.AreaType.ACTIVE
        or mine.active[0].serial != data["attacker_serial"]
        or not _status_is_unlocked(mine)
        or not _reservation_is_exact(parent, obs, data)
        or len(theirs.active) != 1
        or theirs.active[0].serial != data["target_serial"]
        or _target_fingerprint(parent, state, theirs.active[0], 1 - owner)
        != data["target_fingerprint"]
        or _hand_fingerprint(parent, mine, owner) is None
        or not _options_are_unambiguous(parent, obs)
    ):
        return None
    attacks = [
        (index, option)
        for index, option in enumerate(select.option)
        if option.type == parent.OptionType.ATTACK
    ]
    if len(attacks) != 1 or attacks[0][1].attackId != data["attack_id"]:
        return None
    index, option = attacks[0]
    if not _option_is_exact(
        parent,
        option,
        parent.OptionType.ATTACK,
        owner,
        attackId=data["attack_id"],
    ):
        return None
    outcome = _strict_positive_outcome(
        parent,
        obs,
        mine.active[0],
        theirs.active[0],
        data["attack_id"],
        mine.handCount,
    )
    return [index] if outcome is not None else None


def _original_active_is_gone(parent: Any, obs: Any, data: dict[str, Any]) -> bool:
    mine = obs.current.players[data["owner"]]
    return not any(
        pokemon.serial == data["original_active_serial"]
        for pokemon in list(mine.active) + list(mine.bench)
    )


def _forced_promotion_action(parent: Any, obs: Any, data: dict[str, Any]):
    select = obs.select
    owner = data["owner"]
    mine = obs.current.players[owner]
    if (
        select.context not in (parent.SelectContext.SWITCH, parent.SelectContext.TO_ACTIVE)
        or int(select.type) != 1
        or select.minCount != 1
        or select.maxCount != 1
        or select.effect is not None
        or select.contextCard is not None
        or mine.active
        or not _original_active_is_gone(parent, obs, data)
        or not _reservation_is_exact(parent, obs, data)
        or not _options_are_unambiguous(parent, obs)
    ):
        return None
    matches = []
    for index, option in enumerate(select.option):
        pokemon = core._option_card(parent, obs, option)
        if (
            option.type != parent.OptionType.CARD
            or option.area != parent.AreaType.BENCH
            or pokemon is None
            or not _option_is_exact(
                parent,
                option,
                parent.OptionType.CARD,
                owner,
                area=parent.AreaType.BENCH,
                index=option.index,
            )
        ):
            return None
        if pokemon.serial == data["attacker_serial"]:
            matches.append(index)
    return [matches[0]] if len(matches) == 1 else None


def _parent_owner_now(parent: Any) -> bool:
    try:
        return core.parent_owner_active(core.parent_state_snapshot(parent))
    except Exception:
        return True


def _parent_selected_exact_end(parent: Any, obs: Any, action: list[int]) -> bool:
    if len(action) != 1 or not 0 <= action[0] < len(obs.select.option):
        return False
    return _option_is_exact(
        parent,
        obs.select.option[action[0]],
        parent.OptionType.END,
        obs.current.yourIndex,
    )


def _arbitrate_h0_main(
    parent: Any,
    obs: Any,
    transaction: dict[str, Any],
    snap_hash: str | None,
    parent_action: list[int],
    abort: Any,
):
    stage = transaction["stage"]
    action = _exact_attack_action(parent, obs, transaction["data"])
    if action is None:
        return abort("H0_EXACT_ATTACK_UNAVAILABLE")
    if parent_action == action:
        _psychic_trace(
            "PSYCHIC_READINESS_COMPLETE",
            transaction,
            snap_hash,
            parent_action,
            parent_action,
            "PARENT_SELECTED_INTENDED_ATTACK",
            stage=stage,
        )
        return "complete", None, "PARENT_SELECTED_INTENDED_ATTACK"
    if not _parent_selected_exact_end(parent, obs, parent_action):
        return abort("PARENT_MAIN_ACTION_REMAINS_OWNER")
    _set_psychic_stage(transaction, "await_resolution")
    _psychic_trace(
        "PSYCHIC_READINESS_ATTACK",
        transaction,
        snap_hash,
        parent_action,
        action,
        "PARENT_END_TO_EXACT_ATTACK",
        stage=stage,
    )
    return "override", action, "PARENT_END_TO_EXACT_ATTACK"


def _advance_psychic_transaction(parent: Any, obs: Any, transaction: dict[str, Any]):
    data = transaction["data"]
    stage = transaction["stage"]
    snap_hash = _current_snapshot_hash(parent, obs)
    parent_action = _current_parent_action(parent, obs)

    def abort(reason: str):
        _psychic_trace(
            "PSYCHIC_READINESS_ABORT",
            transaction,
            snap_hash,
            parent_action,
            parent_action,
            reason,
            stage=stage,
        )
        return "abort", None, reason

    if _parent_owner_now(parent):
        return abort("HIGHER_PRECEDENCE_PARENT_OWNER")
    if stage == "await_resolution":
        _psychic_trace(
            "PSYCHIC_READINESS_COMPLETE",
            transaction,
            snap_hash,
            parent_action,
            parent_action,
            "EXACT_ATTACK_ISSUED",
            stage=stage,
        )
        return "complete", None, "EXACT_ATTACK_ISSUED"
    if stage == "await_attach_resolution":
        if not _post_attach_is_exact(parent, obs, data):
            return abort("ATTACHMENT_DELTA_STALE")
        if obs.select.context == parent.SelectContext.TO_BENCH:
            if not _optional_telepath_prompt_is_exact(parent, obs, data):
                return abort("TELEPATH_PROMPT_MANDATORY_OR_INCOMPLETE")
            next_stage = (
                "await_post_attach_main"
                if data["role"] == "H0"
                else "reserved_until_exposure"
            )
            _set_psychic_stage(transaction, next_stage)
            _psychic_trace(
                "PSYCHIC_READINESS_PARENT_IDENTICAL",
                transaction,
                snap_hash,
                parent_action,
                parent_action,
                "OPTIONAL_TELEPATH_SEARCH_REMAINS_PARENT_OWNED",
                stage=next_stage,
            )
            return "pass", None, "OPTIONAL_TELEPATH_SEARCH_REMAINS_PARENT_OWNED"
        if obs.select.context != parent.SelectContext.MAIN:
            return abort("POST_ATTACH_CONTEXT_UNEXPECTED")
        if data["role"] == "H0":
            return _arbitrate_h0_main(parent, obs, transaction, snap_hash, parent_action, abort)
        _set_psychic_stage(transaction, "reserved_until_exposure")
        _psychic_trace(
            "PSYCHIC_READINESS_PARENT_IDENTICAL",
            transaction,
            snap_hash,
            parent_action,
            parent_action,
            "H1_RESERVATION_MATERIALIZED",
            stage="reserved_until_exposure",
        )
        return "pass", None, "H1_RESERVATION_MATERIALIZED"
    if stage == "reserved_until_exposure":
        if not _reservation_is_exact(parent, obs, data):
            return abort("H1_RESERVATION_STALE")
        found = _find_reserved(parent, obs, data)
        if found is not None and found[0] == parent.AreaType.ACTIVE:
            data["role"] = "H0"
            if not _prepare_current_target(parent, obs, data):
                return abort("PROMOTED_TARGET_NOT_EXACT_POSITIVE")
            return _arbitrate_h0_main(parent, obs, transaction, snap_hash, parent_action, abort)
        if obs.select.context in (parent.SelectContext.SWITCH, parent.SelectContext.TO_ACTIVE):
            if _original_active_is_gone(parent, obs, data):
                action = _forced_promotion_action(parent, obs, data)
                if action is None or not _prepare_current_target(parent, obs, data):
                    return abort("FORCED_PROMOTION_NOT_EXACT")
                data["role"] = "H0"
                _set_psychic_stage(transaction, "await_post_attach_main")
                if parent_action == action:
                    _psychic_trace(
                        "PSYCHIC_READINESS_PARENT_IDENTICAL",
                        transaction,
                        snap_hash,
                        parent_action,
                        parent_action,
                        "PARENT_SELECTED_RESERVED_PROMOTION",
                        stage="reserved_until_exposure",
                    )
                    return "pass", None, "PARENT_SELECTED_RESERVED_PROMOTION"
                _psychic_trace(
                    "PSYCHIC_READINESS_PROMOTE",
                    transaction,
                    snap_hash,
                    parent_action,
                    action,
                    "FORCED_PROMOTION_RESERVED_ATTACKER",
                    stage="reserved_until_exposure",
                )
                return "override", action, "FORCED_PROMOTION_RESERVED_ATTACKER"
            return abort("ORDINARY_SWITCH_REMAINS_PARENT_OWNED")
        if obs.select.context == parent.SelectContext.MAIN:
            later_turn = (
                obs.current.turn != data["turn"]
                or obs.current.turnActionCount < data["turn_action_count"]
            )
            if later_turn or data.get("saw_switch_prompt"):
                _psychic_trace(
                    "PSYCHIC_READINESS_COMPLETE",
                    transaction,
                    snap_hash,
                    parent_action,
                    parent_action,
                    "H1_NOT_EXPOSED_AT_LATER_MAIN",
                    stage=stage,
                )
                return "complete", None, "H1_NOT_EXPOSED_AT_LATER_MAIN"
        _psychic_trace(
            "PSYCHIC_READINESS_PARENT_IDENTICAL",
            transaction,
            snap_hash,
            parent_action,
            parent_action,
            "H1_RESERVATION_REMAINS_EXACT",
            stage=stage,
        )
        return "pass", None, "H1_RESERVATION_REMAINS_EXACT"
    if stage == "await_post_attach_main":
        return _arbitrate_h0_main(parent, obs, transaction, snap_hash, parent_action, abort)
    return abort("UNKNOWN_PSYCHIC_READINESS_STAGE")


def _duplicate_action(parent: Any, obs: Any, snapshot_hash: str):
    transaction = core.INTEGRATED_TRANSACTION
    action = _BASE_DUPLICATE_ACTION(parent, obs, snapshot_hash)
    if (
        action is not None
        and transaction is not None
        and transaction.get("kind") == PSYCHIC_READINESS_KIND
    ):
        data = transaction["data"]
        parent_action = list(data.get("last_parent_action") or ())
        _psychic_trace(
            "PSYCHIC_READINESS_DUPLICATE",
            transaction,
            snapshot_hash,
            parent_action,
            action,
            "IDENTICAL_CALLBACK_CACHED_NO_PARENT_CALL",
        )
    return action

def _reconcile_psychic_trace(action: list[int]) -> None:
    latest = core.INTEGRATED_LATEST_TRACE
    if latest is None:
        return
    custom = next(
        (
            row
            for row in reversed(core.INTEGRATED_TRACE_LOG)
            if str(row.get("classification", "")).startswith("PSYCHIC_READINESS_")
            and (
                row is latest
                or (
                    latest.get("kind") == PSYCHIC_READINESS_KIND
                    and row.get("plan_id") == latest.get("plan_id")
                )
            )
        ),
        None,
    )
    if custom is None:
        return
    if latest is not custom and latest.get("kind") == PSYCHIC_READINESS_KIND:
        parent_action = tuple(latest.get("parent_action") or ())
    elif custom.get("classification") in (
        "PSYCHIC_READINESS_PARENT_IDENTICAL",
        "PSYCHIC_READINESS_COMPLETE",
        "PSYCHIC_READINESS_ABORT",
    ):
        parent_action = tuple(action)
    else:
        parent_action = tuple(custom.get("exact_parent_action") or ())
    returned_action = tuple(action)
    custom.update(
        parent_action=parent_action,
        override_action=returned_action,
        exact_parent_action=parent_action,
        exact_returned_action=returned_action,
    )
    if latest is not custom and latest.get("kind") == PSYCHIC_READINESS_KIND:
        for field in (
            "psychic_role",
            "origin_role",
            "psychic_lineage",
            "attacker_serial",
            "energy_id",
            "energy_serial",
            "intended_attack",
            "public_snapshot_hash",
            "reason_code",
        ):
            latest[field] = custom.get(field)
        latest["classification"] = custom.get("classification")
        latest["reason"] = custom.get("reason_code") or custom.get("reason") or ""
        latest["stage"] = custom.get("stage")
        latest["public_snapshot_hash"] = latest.get("snapshot_hash")
        custom["snapshot_hash"] = latest.get("snapshot_hash")
        custom["public_snapshot_hash"] = latest.get("snapshot_hash")
        latest["exact_parent_action"] = parent_action
        latest["exact_returned_action"] = returned_action
        transaction = core.INTEGRATED_TRANSACTION
        plan = transaction.get("plan") if transaction is not None else None
        if plan is not None:
            latest.setdefault("H0", plan.H0)
            latest.setdefault("H1", plan.H1)
            latest.setdefault("H2", plan.H2)
            latest.setdefault(
                "ledger",
                {
                    "roles": tuple(
                        (line, role.value) for line, role in plan.resource_ledger.roles
                    ),
                    "reservations": tuple(
                        (
                            reservation.token,
                            reservation.role.value,
                            reservation.purpose,
                            tuple(sorted(reservation.branches)),
                        )
                        for reservation in plan.resource_ledger.reservations
                    ),
                },
            )
def _arbitrate_new_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], parent_pre: dict[str, Any], parent_post: dict[str, Any]):
    owners = core.parent_owner_active(parent_pre) or core.parent_owner_active(parent_post)
    psychic = None
    if not owners:
        certificate = _psychic_readiness_certificate(
            parent, obs, snap, parent_action
        )
        if certificate is not None:
            data, action = certificate
            psychic = _psychic_plan(
                parent, obs, snap, parent_action, data, action
            )

    def selected_psychic():
        if psychic is None:
            return None
        plan, action, commit = psychic
        transaction = commit["transaction"]
        role = transaction["data"]["origin_role"]
        reason = (
            "PARENT_SELECTED_CERTIFIED_ATTACHMENT"
            if transaction["data"]["parent_identical"]
            else "PARENT_ATTACHMENT_BUDGET_CONFLICT"
            if transaction["data"]["trigger"] == "ATTACH"
            else "PARENT_END_BUDGET_ABANDONED"
        )
        _psychic_trace(
            f"PSYCHIC_READINESS_COMMIT_{role}",
            transaction,
            snap.sha256,
            parent_action,
            action,
            reason,
            stage="await_attach_resolution",
        )
        if transaction["data"]["parent_identical"]:
            _psychic_trace(
                "PSYCHIC_READINESS_PARENT_IDENTICAL",
                transaction,
                snap.sha256,
                parent_action,
                action,
                "PARENT_SELECTED_CERTIFIED_ATTACHMENT",
                stage="await_attach_resolution",
            )
        return psychic

    raw_candidates = []
    hilda = core._build_hilda_enriching(parent, obs, snap, parent_action, parent_pre)
    if hilda is not None:
        raw_candidates.append(hilda)
    if not owners:
        for builder in (
            core._build_powerful_hand_floor,
            core._build_run_away,
            core._terminal_attach_candidate,
            core._build_fan_attach,
        ):
            result = builder(parent, obs, snap, parent_action)
            if result is not None:
                raw_candidates.append(result)
        roles = semantics.public_roles(parent, obs)
        stopped = _setup_stop_candidate(parent, obs, snap, parent_action, roles)
        if stopped is not None:
            raw_candidates.append(stopped)
    certified = []
    for candidate in raw_candidates:
        result = _certify_candidate(parent, obs, candidate)
        if result is not None:
            certified.append(result)
    roles = semantics.public_roles(parent, obs)
    parent_objective = _parent_objective(parent, obs, parent_action, roles)
    if not certified:
        return selected_psychic()
    winner = max(certified, key=lambda row: row[0].objective.vector())
    if winner[0].objective.vector() <= parent_objective.vector():
        return selected_psychic()
    admitted, rejection = _admit_integrated_override(
        parent, obs, snap, parent_action, winner
    )
    if not admitted:
        core._trace(
            'ADMISSIBILITY_REJECT',
            winner[0],
            snap.sha256,
            parent_action=parent_action,
            override_action=winner[1],
            reason=rejection,
        )
        return selected_psychic()
    return winner
def _advance_transaction(parent: Any, obs: Any):
    transaction = core.INTEGRATED_TRANSACTION
    if transaction is not None and transaction.get("kind") == PSYCHIC_READINESS_KIND:
        return _advance_psychic_transaction(parent, obs, transaction)
    result = _BASE_ADVANCE_TRANSACTION(parent, obs)
    outcome, action, reason = result
    if outcome != "override" or action is None or transaction is None:
        return result
    stage = transaction.get("stage", "unknown")
    plan = validation.advance_plan_step(parent, obs, transaction["plan"], action, stage)
    if plan is None:
        return "abort", None, "continuation action could not be rebound"
    ok, why = validation.validate_plan(parent, obs, plan, action, current_stage=stage)
    if not ok:
        return "abort", None, f"continuation plan invalid: {why}"
    transaction["plan"] = plan
    return outcome, action, reason


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    core.build_turn_budget = _build_turn_budget
    core.ordered_draw_clock = _ordered_draw_clock
    semantics.ordered_draw_clock = _ordered_draw_clock
    core._new_plan = _arbitrate_new_plan
    core._advance_transaction = _advance_transaction
    core._duplicate_action = _duplicate_action
    _INSTALLED = True


def agent(parent: Any, parent_agent: Any, obs_dict: dict) -> list[int]:
    install()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        core.reset_integrated_state()
        return parent_agent(obs_dict)
    try:
        obs = parent.to_observation_class(obs_dict)
    except Exception:
        return parent_agent(obs_dict)
    if not runtime_model.raw_parsed_agree(obs_dict, obs):
        core.reset_integrated_state()
        return parent_agent(obs_dict)
    global _CONTINUATION_PARENT_ACTION

    def capture_parent_action(raw: dict) -> list[int]:
        global _CONTINUATION_PARENT_ACTION
        returned = parent_agent(raw)
        _CONTINUATION_PARENT_ACTION = list(returned) if isinstance(returned, (list, tuple)) else None
        return returned

    _CONTINUATION_PARENT_ACTION = None
    try:
        action = integrated.agent(parent, capture_parent_action, obs_dict)
    finally:
        _CONTINUATION_PARENT_ACTION = None
    _reconcile_psychic_trace(action)
    return action


install()
