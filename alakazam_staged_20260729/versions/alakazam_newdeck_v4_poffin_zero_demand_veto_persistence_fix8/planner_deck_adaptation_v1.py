"""Six narrow, fail-closed interventions for the new-deck v1 package."""

from __future__ import annotations

import copy
import hashlib
import json
from math import ceil
from typing import Any

import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_semantics as semantics

KADABRA = 742
ALAKAZAM = 743
ABRA = 741
DUNSPARCE = 305
BUDDY_BUDDY_POFFIN = 1086
EXACT_DECK_SIZE = 60
EXACT_DECK_ROLE_COUNTS = {ABRA: 4, DUNSPARCE: 3}
POWERFUL_HAND = 1072
ENHANCED_HAMMER = 1081
BOSS_ORDERS = 1182
LANAS_AID = 1184
XEROSIC = 1197
NIGHTTIME_MINE = 1266
TEAM_ROCKETS_ARTICUNO = 414
REPELLING_VEIL_TEXT = (
    "Prevent all effects of attacks used by your opponent\u2019s Pok\u00e9mon "
    "done to your Basic Team Rocket\u2019s Pok\u00e9mon. (Existing effects are "
    "not removed. Damage is not an effect.)"
)
TEAM_ROCKET_NAME_PREFIX = "Team Rocket's "
REMOVED_OWN_CARD_IDS = frozenset({142, 858, 1156, 1161, 1264})
EXACT_DECK_ALAKAZAM_COUNT = 4
LANA_ALLOWLIST = frozenset({741, 742, 743, 305, 66, 343, 5})
LANA_EXCLUDED = frozenset({140, 13, 19})
UNKNOWN_IDS = frozenset({BOSS_ORDERS, NIGHTTIME_MINE, ALAKAZAM})
RULE_XEROSIC = "V1_XEROSIC_H_MINUS_1_CURRENT_KO"
RULE_LANA = "V1_LANA_H_MINUS_1_PLUS_K_CURRENT_KO"
RULE_HAMMER = "V1_HAMMER_UNIQUE_SPECIAL_ENERGY_CURRENT_KO"
RULE_BOSS = "V1_BOSS_TERMINAL_PRIZE_KO"
RULE_BOSS_READY_STOP = "V1_BOSS_UNIQUE_READY_ATTACKER_STOP"
RULE_MINE = "V1_MINE_EXACT_TERA_ATTACK_STOP"
RULE_ALAKAZAM = "V1_ALAKAZAM_EXACT_EVOLUTION_RECOVERY"
RULE_ALAKAZAM_READY_BENCH = "V1_ALAKAZAM_4TH_READY_BENCH"
RULE_PSYCHIC_DRAW_OPTIONAL = "V3_PSYCHIC_DRAW_OPTIONAL_DECK_FLOOR"
RULE_ALAKAZAM_EXACT_EVOLUTION_KO = (
    "V3_ALAKAZAM_EXACT_EVOLUTION_KO_PRIORITY"
)
RULE_POFFIN_ZERO_DEMAND_VETO = "V4_POFFIN_ZERO_DEMAND_VETO_PERSISTENCE_FIX8"

V1_TRANSACTION: dict[str, Any] | None = None
V1_DUPLICATES: dict[str, tuple[tuple[Any, ...], ...]] = {}
POFFIN_ZERO_DEMAND_LATCH: dict[str, Any] | None = None
REMOVED_RULE_HITS: list[dict[str, Any]] = []
LAST_V1_PACKAGE_TRACE: dict[str, Any] = {
    "public_snapshot_hash": None, "context": None, "selected_action": [],
    "selected_rule": None, "reason_tags": [], "added_rule_hits": [],
    "removed_rule_hit_status": "KNOWN", "removed_rule_hits": [],
}
LAST_V4_POFFIN_ZERO_VETO_TRACE: dict[str, Any] = {
    "rule": RULE_POFFIN_ZERO_DEMAND_VETO,
    "stage": "RESET",
    "reason": "MODULE_INIT",
    "eligibility_hash": None,
    "parent_action": [],
    "proposed_action": [],
    "applied_action": [],
}
V4_POFFIN_ZERO_VETO_TRACE_HISTORY: list[dict[str, Any]] = []

class UnrecoverableObservationFault(RuntimeError):
    """Raised when no returned action can be proved legal from the callback."""



def reset() -> None:
    global V1_TRANSACTION, POFFIN_ZERO_DEMAND_LATCH
    V1_TRANSACTION = None
    POFFIN_ZERO_DEMAND_LATCH = None
    V1_DUPLICATES.clear()
    V4_POFFIN_ZERO_VETO_TRACE_HISTORY.clear()


def _reset_v1_only() -> None:
    """Clear inherited v1 ownership without erasing the independent Fix8 latch."""
    global V1_TRANSACTION
    V1_TRANSACTION = None
    V1_DUPLICATES.clear()


def _trace(snapshot_hash, context, action, rule, *tags) -> None:
    global LAST_V1_PACKAGE_TRACE
    LAST_V1_PACKAGE_TRACE = {
        "public_snapshot_hash": snapshot_hash,
        "context": context,
        "selected_action": list(action) if isinstance(action, (list, tuple)) else [],
        "selected_rule": rule,
        "reason_tags": list(tags),
        "added_rule_hits": [rule] if rule is not None else [],
        "removed_rule_hit_status": "KNOWN",
        "removed_rule_hits": copy.deepcopy(REMOVED_RULE_HITS),
    }


def _card_row(card):
    return model.card_row(card)


def _option_census(parent, obs):
    keys = tuple(runtime_model.stable_option_key(parent, obs, option) for option in obs.select.option)
    if any(key is None for key in keys) or len(keys) != len(set(keys)):
        return None
    return keys


def _child_prompt_envelope(
    parent,
    obs,
    *,
    select_type,
    context,
    context_card=None,
    effect=None,
    min_count=1,
    max_count=1,
    remain_energy_cost=0,
):
    select = obs.select
    if select is None:
        return None
    try:
        exact_type = int(select.type) == int(select_type)
    except (TypeError, ValueError):
        return None
    if (
        not exact_type
        or select.context != context
        or type(select.minCount) is not int
        or select.minCount != min_count
        or type(select.maxCount) is not int
        or select.maxCount != max_count
        or type(select.remainDamageCounter) is not int
        or select.remainDamageCounter != 0
        or type(select.remainEnergyCost) is not int
        or select.remainEnergyCost != remain_energy_cost
        or select.deck is not None
        or (
            select.contextCard is not None
            if context_card is None
            else _card_row(select.contextCard) != context_card
        )
        or (
            select.effect is not None
            if effect is None
            else _card_row(select.effect) != effect
        )
    ):
        return None
    return _option_census(parent, obs)

def _select_envelope_mismatch_reason(
    parent,
    obs,
    *,
    select_type,
    context,
    context_card=None,
    effect=None,
    min_count=1,
    max_count=1,
    remain_energy_cost=0,
):
    select = obs.select
    if select is None:
        return "SELECT_MISSING"
    try:
        if int(select.type) != int(select_type):
            return "SELECT_TYPE"
    except (TypeError, ValueError):
        return "SELECT_TYPE"
    checks = (
        (select.context == context, "SELECT_CONTEXT"),
        (type(select.minCount) is int and select.minCount == min_count, "SELECT_MIN"),
        (type(select.maxCount) is int and select.maxCount == max_count, "SELECT_MAX"),
        (type(select.remainDamageCounter) is int and select.remainDamageCounter == 0, "SELECT_REMAIN_DAMAGE"),
        (
            type(select.remainEnergyCost) is int
            and select.remainEnergyCost == remain_energy_cost,
            "SELECT_REMAIN_ENERGY",
        ),
        (select.deck is None, "SELECT_DECK"),
        (
            select.contextCard is None
            if context_card is None
            else _card_row(select.contextCard) == context_card,
            "SELECT_CONTEXT_CARD",
        ),
        (
            select.effect is None
            if effect is None
            else _card_row(select.effect) == effect,
            "SELECT_EFFECT",
        ),
        (_option_census(parent, obs) is not None, "SELECT_OPTION_CENSUS"),
    )
    for passed, reason in checks:
        if not passed:
            return reason
    return None


def _owned_stage_rejection_reason(parent, obs, transaction):
    stage = transaction.get("stage")
    specifications = {
        "await_boss_child": (1, parent.SelectContext.SWITCH, None, transaction["card_row"], 1, 1, 0),
        "await_boss_attack": (0, parent.SelectContext.MAIN, None, None, 1, 1, 0),
        "await_hammer_child": (4, parent.SelectContext.DISCARD_ENERGY, None, transaction["card_row"], 1, 1, 1),
        "await_lana_child": (1, parent.SelectContext.TO_HAND, None, transaction["card_row"], 1, getattr(obs.select, "maxCount", None), 0),
        "await_xerosic_verify": (0, parent.SelectContext.MAIN, None, None, 1, 1, 0),
        "await_mine_attack": (0, parent.SelectContext.MAIN, None, None, 1, 1, 0),
        "await_alakazam_ability": (9, parent.SelectContext.ACTIVATE, transaction["card_row"], None, 1, 1, 0),
        "await_alakazam_attack": (0, parent.SelectContext.MAIN, None, None, 1, 1, 0),
        "await_backup_alakazam_ability": (9, parent.SelectContext.ACTIVATE, transaction["card_row"], None, 1, 1, 0),
        "await_backup_alakazam_attack": (0, parent.SelectContext.MAIN, None, None, 1, 1, 0),
    }
    specification = specifications.get(stage)
    if specification is not None:
        reason = _select_envelope_mismatch_reason(
            parent,
            obs,
            select_type=specification[0],
            context=specification[1],
            context_card=specification[2],
            effect=specification[3],
            min_count=specification[4],
            max_count=specification[5],
            remain_energy_cost=specification[6],
        )
        if reason is not None:
            return reason
    if stage == "await_added_attack_verify":
        return "ATTACK_POSTCONDITION"
    return "EXACT_PUBLIC_DELTA_OR_RULE_POSTCONDITION"

def _exact_option(option, option_type, **expected):
    for field, value in vars(option).items():
        wanted = option_type if field == "type" else expected.get(field)
        if value != wanted:
            return False
    return True


def _psychic_draw_metadata_exact(parent, card_id):
    expected = {
        KADABRA: (
            " Psychic Draw",
            "Once during your turn, when you play this Pok\u00e9mon from your hand "
            "to evolve 1 of your Pok\u00e9mon, you may use this Ability. Draw 2 cards.",
        ),
        ALAKAZAM: (
            " Psychic Draw",
            "Once during your turn, when you play this Pok\u00e9mon from your hand "
            "to evolve 1 of your Pok\u00e9mon, you may use this Ability. Draw 3 cards.",
        ),
    }.get(card_id)
    data = parent.card_table.get(card_id)
    return bool(
        expected is not None
        and data is not None
        and len(data.skills or ()) == 1
        and (data.skills[0].name, data.skills[0].text) == expected
    )


def _psychic_draw_prompt(parent, obs):
    state, select = obs.current, obs.select
    if state is None or select is None or state.yourIndex not in (0, 1):
        return None
    owner = state.yourIndex
    mine = state.players[owner]
    context_row = _card_row(select.contextCard)
    if (
        context_row is None
        or context_row[0] not in (KADABRA, ALAKAZAM)
        or context_row[2] != owner
        or type(mine.deckCount) is not int
        or mine.deckCount < 0
        or not _psychic_draw_metadata_exact(parent, context_row[0])
        or _child_prompt_envelope(
            parent,
            obs,
            select_type=9,
            context=parent.SelectContext.ACTIVATE,
            context_card=context_row,
        )
        is None
        or len(select.option) != 2
    ):
        return None
    yes = [
        index
        for index, option in enumerate(select.option)
        if option.type == parent.OptionType.YES
        and _exact_option(option, parent.OptionType.YES)
    ]
    no = [
        index
        for index, option in enumerate(select.option)
        if option.type == parent.OptionType.NO
        and _exact_option(option, parent.OptionType.NO)
    ]
    matches = [
        pokemon
        for pokemon in list(mine.active) + list(mine.bench)
        if pokemon.id == context_row[0] and pokemon.serial == context_row[1]
    ]
    if len(yes) != 1 or len(no) != 1 or len(matches) != 1:
        return None
    pokemon = matches[0]
    lineage = tuple(card.id for card in pokemon.preEvolution)
    expected_lineage = (
        ((parent.Abra,),)
        if context_row[0] == KADABRA
        else ((parent.Abra,), (parent.Abra, parent.Kadabra))
    )
    protected = parent._bridge_pokemon_component_serials(pokemon)
    if (
        lineage not in expected_lineage
        or not parent._bridge_pokemon_is_publicly_complete(pokemon, owner)
        or not parent._bridge_protected_serials_are_unique(state, protected)
    ):
        return None
    draw_count = 2 if context_row[0] == KADABRA else 3
    projected_deck = mine.deckCount - min(mine.deckCount, draw_count)
    return {
        "yes_index": yes[0],
        "no_index": no[0],
        "card_id": context_row[0],
        "card_serial": context_row[1],
        "draw_count": draw_count,
        "deck_count": mine.deckCount,
        "projected_deck": projected_deck,
    }


def _psychic_draw_optional_decision(parent, obs, baseline_action):
    prompt = _psychic_draw_prompt(parent, obs)
    if (
        prompt is None
        or not isinstance(baseline_action, (list, tuple))
        or list(baseline_action) != [prompt["yes_index"]]
    ):
        return None
    prompt["overridden"] = prompt["projected_deck"] < 1
    prompt["action"] = (
        [prompt["no_index"]] if prompt["overridden"] else baseline_action
    )
    return prompt


def _psychic_draw_trace_tags(decision):
    return (
        (
            "V3_PSYCHIC_DRAW_OPTIONAL_NO",
            "V3_BASELINE_YES_OVERRIDDEN",
            "V3_PROJECTED_DECK_0",
        )
        if decision["overridden"]
        else (
            "V3_PSYCHIC_DRAW_BASELINE_YES_PRESERVED",
            "V3_PROJECTED_DECK_1_PLUS",
        )
    ) + (
        f"V3_PSYCHIC_DRAW_CARD_{decision['card_id']}",
        f"V3_PSYCHIC_DRAW_COUNT_{decision['draw_count']}",
        "EXACT_PSYCHIC_DRAW_PROMPT",
    )


def _record_owned_psychic_draw_choice(transaction, state, decision):
    drawn = decision["draw_count"] if not decision["overridden"] else 0
    transaction["psychic_draw_choice"] = (
        "NO" if decision["overridden"] else "YES"
    )
    transaction["psychic_draw_card_id"] = decision["card_id"]
    transaction["psychic_draw_count"] = decision["draw_count"]
    transaction["psychic_draw_projected_deck"] = decision["projected_deck"]
    transaction["expected_deck_after_psychic_draw"] = (
        state["own_deck"] - min(state["own_deck"], drawn)
    )
    transaction["expected_hand_after_psychic_draw"] = (
        state["own_hand_count"] + min(state["own_deck"], drawn)
    )
    transaction["expected_new_cards_after_psychic_draw"] = min(
        state["own_deck"], drawn
    )


def _psychic_draw_post_prompt_delta(current, post, transaction):
    expected_new = transaction.get("expected_new_cards_after_psychic_draw")
    hand_delta_exact = (
        current["own_hand"] == post["own_hand"]
        if expected_new == 0
        else (
            type(expected_new) is int
            and expected_new > 0
            and set(post["own_hand"]).issubset(set(current["own_hand"]))
            and len(current["own_hand"]) - len(post["own_hand"])
            == expected_new
        )
    )
    return bool(
        type(expected_new) is int
        and expected_new >= 0
        and current["own_deck"]
        == transaction.get("expected_deck_after_psychic_draw")
        and current["own_hand_count"]
        == transaction.get("expected_hand_after_psychic_draw")
        and hand_delta_exact
    )


def _metadata_exact(parent, card_id):
    data = parent.card_table.get(card_id)
    expected = {
        ENHANCED_HAMMER: (
            "Enhanced Hammer", parent.CardType.ITEM, "Enhanced Hammer",
            "Discard a Special Energy from 1 of your opponent’s Pokémon.",
        ),
        LANAS_AID: (
            "Lana’s Aid", parent.CardType.SUPPORTER, "Lana’s Aid",
            "Put up to 3 in any combination of Pokémon that don’t have a Rule Box and Basic Energy cards from your discard pile into your hand. (Pokémon {ex}, Pokémon {V}, etc. have Rule Boxes.)",
        ),
        BOSS_ORDERS: (
            "Boss\u2019s Orders", parent.CardType.SUPPORTER, "Boss\u2019s Orders",
            "Switch in 1 of your opponent\u2019s Benched Pok\u00e9mon to the Active Spot.",
        ),
        NIGHTTIME_MINE: (
            "Nighttime Mine", parent.CardType.STADIUM, "Nighttime Mine",
            "Attacks used by each Tera Pok\u00e9mon in play (both yours and your opponent\u2019s) cost {C} more.",
        ),
        XEROSIC: (
            "Xerosic’s Machinations", parent.CardType.SUPPORTER, "Xerosic’s Machinations",
            "Your opponent discards cards from their hand until they have 3 cards in their hand.",
        ),
    }.get(card_id)
    if data is None or expected is None or len(data.skills or ()) != 1:
        return False
    name, card_type, skill_name, text = expected
    return (
        data.cardId == card_id and data.name == name and data.cardType == card_type
        and not data.aceSpec and not data.attacks
        and data.skills[0].name == skill_name and data.skills[0].text == text
    )


def _public_state(parent, obs):
    state = obs.current
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or state.firstPlayer not in (0, 1)
        or len(state.players) != 2
    ):
        return None
    owner = state.yourIndex
    mine, theirs = state.players[owner], state.players[1 - owner]
    if (
        mine.hand is None
        or len(mine.hand) != mine.handCount
        or theirs.hand is not None
        or state.looking is not None
        or any(
            type(player.benchMax) is not int
            or player.benchMax < len(player.bench)
            for player in state.players
        )
        or any(
            type(flag) is not bool
            for player in state.players
            for flag in (
                player.poisoned,
                player.burned,
                player.asleep,
                player.paralyzed,
                player.confused,
            )
        )
    ):
        return None

    def rows(values, expected_owner):
        result = tuple(_card_row(card) for card in values)
        if any(row is None or (expected_owner is not None and row[2] != expected_owner) for row in result):
            return None
        return result

    def prizes(values, expected_owner):
        result = []
        for card in values:
            if card is None:
                result.append(("HIDDEN",))
                continue
            row = _card_row(card)
            if row is None or row[2] != expected_owner:
                return None
            result.append(("PUBLIC",) + row)
        return tuple(result)

    def status(player):
        return (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        )

    own_hand = rows(mine.hand, owner)
    own_discard = rows(mine.discard, owner)
    opponent_discard = rows(theirs.discard, 1 - owner)
    stadium = rows(state.stadium, None)
    own_prize = prizes(mine.prize, owner)
    opponent_prize = prizes(theirs.prize, 1 - owner)
    if any(
        value is None
        for value in (
            own_hand,
            own_discard,
            opponent_discard,
            stadium,
            own_prize,
            opponent_prize,
        )
    ):
        return None
    serials = parent._bridge_public_serials(state)
    if any(type(serial) is not int or serial <= 0 for serial in serials) or len(serials) != len(set(serials)):
        return None
    player_fields = []
    for player_owner, player in enumerate(state.players):
        active, bench = [], []
        for area, result in ((player.active, active), (player.bench, bench)):
            for pokemon in area:
                if not parent._bridge_pokemon_is_publicly_complete(pokemon, player_owner) or semantics.energy_units(parent, pokemon) is None:
                    return None
                result.append(parent._bridge_pokemon_fingerprint(pokemon))
        player_fields.append((tuple(active), tuple(bench)))
    own_active, own_bench = player_fields[owner]
    opponent_active, opponent_bench = player_fields[1 - owner]
    fields = []
    for active, bench in player_fields:
        fields.extend(active)
        fields.extend(bench)
    return {
        "turn": state.turn,
        "first_player": state.firstPlayer,
        "action_count": state.turnActionCount,
        "result": state.result,
        "supporter_played": bool(state.supporterPlayed), "stadium_played": bool(state.stadiumPlayed),
        "energy_attached": bool(state.energyAttached), "retreated": bool(state.retreated),
        "own_deck": mine.deckCount, "opponent_deck": theirs.deckCount,
        "own_bench_max": mine.benchMax, "opponent_bench_max": theirs.benchMax,
        "own_status": status(mine), "opponent_status": status(theirs),
        "own_prize": own_prize, "opponent_prize": opponent_prize,
        "own_hand_count": mine.handCount, "opponent_hand_count": theirs.handCount,
        "own_hand": own_hand, "own_discard": own_discard,
        "opponent_discard": opponent_discard, "stadium": stadium,
        "own_active": own_active, "own_bench": own_bench,
        "opponent_active": opponent_active, "opponent_bench": opponent_bench,
        "fields": tuple(fields),
    }


def _added_public_invariants_unchanged(current, previous):
    return all(
        current[key] == previous[key]
        for key in (
            "first_player",
            "own_bench_max",
            "opponent_bench_max",
            "own_prize",
            "opponent_prize",
            "own_status",
            "opponent_status",
        )
    )


def _boss_switch_public_delta_is_exact(current, previous, transaction):
    target_index = transaction["target_bench_index"]
    if (
        current["first_player"] != previous["first_player"]
        or current["own_bench_max"] != previous["own_bench_max"]
        or current["opponent_bench_max"] != previous["opponent_bench_max"]
        or current["own_prize"] != previous["own_prize"]
        or current["opponent_prize"] != previous["opponent_prize"]
        or current["own_status"] != previous["own_status"]
        or current["opponent_status"] != (False, False, False, False, False)
        or current["own_active"] != previous["own_active"]
        or current["own_bench"] != previous["own_bench"]
        or len(previous["opponent_active"]) != 1
        or not 0 <= target_index < len(previous["opponent_bench"])
    ):
        return False
    expected_bench = list(previous["opponent_bench"])
    expected_active = (expected_bench[target_index],)
    expected_bench[target_index] = previous["opponent_active"][0]
    return (
        current["opponent_active"] == expected_active
        and current["opponent_bench"] == tuple(expected_bench)
    )

def _boss_resolved_public_delta_is_exact(current, post, transaction):
    unchanged = (
        "turn", "first_player", "result", "supporter_played",
        "stadium_played", "energy_attached", "retreated", "own_deck",
        "opponent_deck", "own_bench_max", "opponent_bench_max",
        "own_status", "own_prize", "opponent_prize", "own_hand_count",
        "opponent_hand_count", "own_hand", "opponent_discard", "stadium",
        "own_active", "own_bench",
    )
    return bool(
        _public_keys_equal(current, post, unchanged)
        and current["action_count"] == post["action_count"] + 1
        and _same_multiset(
            current["own_discard"],
            post["own_discard"] + (transaction["card_row"],),
        )
        and _boss_switch_public_delta_is_exact(current, post, transaction)
    )

def _main_envelope(parent, obs):
    select, state = obs.select, obs.current
    if (
        select is None or state is None or select.context != parent.SelectContext.MAIN
        or int(select.type) != 0 or select.minCount != 1 or select.maxCount != 1
        or select.effect is not None or select.contextCard is not None
        or state.result != -1 or state.turn < 2 or _option_census(parent, obs) is None
    ):
        return None
    return _public_state(parent, obs)


def _attack_index(parent, obs):
    matches = [
        index for index, option in enumerate(obs.select.option)
        if option.type == parent.OptionType.ATTACK and option.attackId == POWERFUL_HAND
        and _exact_option(option, parent.OptionType.ATTACK, attackId=POWERFUL_HAND)
    ]
    return matches[0] if len(matches) == 1 else None


def _repelling_veil_state(parent, state, target, target_owner):
    """Return True for protected, False for exact N/A, and None for unknown."""
    if (
        state is None
        or target_owner not in (0, 1)
        or len(getattr(state, "players", ())) != 2
    ):
        return None
    target_field = state.players[target_owner]
    sources = [
        pokemon
        for pokemon in list(target_field.active) + list(target_field.bench)
        if pokemon is not None and pokemon.id == TEAM_ROCKETS_ARTICUNO
    ]
    if not sources:
        return False

    source_data = parent.card_table.get(TEAM_ROCKETS_ARTICUNO)
    if (
        source_data is None
        or source_data.cardId != TEAM_ROCKETS_ARTICUNO
        or source_data.name != "Team Rocket's Articuno"
        or source_data.cardType != parent.CardType.POKEMON
        or source_data.basic is not True
        or source_data.stage1 is not False
        or source_data.stage2 is not False
        or len(source_data.skills or ()) != 1
        or source_data.skills[0].name != " Repelling Veil"
        or source_data.skills[0].text != REPELLING_VEIL_TEXT
        or any(
            not parent._bridge_pokemon_is_publicly_complete(
                source, target_owner
            )
            for source in sources
        )
    ):
        return None

    target_data = parent.card_table.get(getattr(target, "id", None))
    if (
        not parent._bridge_pokemon_is_publicly_complete(target, target_owner)
        or target_data is None
        or target_data.cardId != target.id
        or target_data.cardType != parent.CardType.POKEMON
        or type(target_data.basic) is not bool
        or type(target_data.stage1) is not bool
        or type(target_data.stage2) is not bool
        or sum(
            (target_data.basic, target_data.stage1, target_data.stage2)
        )
        != 1
        or not isinstance(target_data.name, str)
    ):
        return None
    if target_data.basic:
        if target_data.evolvesFrom is not None or target.preEvolution:
            return None
        suffix = target_data.name[len(TEAM_ROCKET_NAME_PREFIX):]
        return bool(
            target_data.name.startswith(TEAM_ROCKET_NAME_PREFIX)
            and suffix
        )
    if not parent._two_prize_lineage_is_complete(target, target_owner):
        return None
    return False


def _v1_powerful_hand_target_is_publicly_clear(
    parent, state, target, target_owner
):
    veil_state = _repelling_veil_state(
        parent, state, target, target_owner
    )
    return bool(
        veil_state is False
        and parent._powerful_hand_target_is_publicly_clear(state, target)
    )


def _powerful_hand_ko(parent, obs, hand_count):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if (
        hand_count < 0 or len(mine.active) != 1 or len(theirs.active) != 1
        or mine.active[0].id != ALAKAZAM
        or not parent._two_prize_powerful_hand_metadata_is_exact()
        or parent.card_table[ALAKAZAM].tera
        or not parent._two_prize_alakazam_is_ready(mine.active[0], owner)
        or mine.asleep or mine.paralyzed or mine.confused
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, theirs.active[0], 1 - owner
        )
        or hand_count < ceil(theirs.active[0].hp / 20)
        or _attack_index(parent, obs) is None
    ):
        return False
    protected = parent._bridge_pokemon_component_serials(mine.active[0]) + parent._bridge_pokemon_component_serials(theirs.active[0])
    return parent._bridge_protected_serials_are_unique(obs.current, protected)


def _delegate_state_snapshot(parent):
    """Capture every mutable surface the v0 delegate may touch."""
    return {
        "parent": core.parent_state_snapshot(parent),
        "transaction": copy.deepcopy(core.INTEGRATED_TRANSACTION),
        "duplicate_cache": copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE),
        "duplicate_order": list(core._DUPLICATE_ORDER),
        "trace_log": copy.deepcopy(core.INTEGRATED_TRACE_LOG),
        "latest_trace": core.INTEGRATED_LATEST_TRACE,
    }


def _restore_delegate_state(parent, snapshot):
    core.restore_parent_state(parent, snapshot["parent"])
    core.INTEGRATED_TRANSACTION = copy.deepcopy(snapshot["transaction"])
    core.INTEGRATED_DUPLICATE_CACHE.clear()
    core.INTEGRATED_DUPLICATE_CACHE.update(copy.deepcopy(snapshot["duplicate_cache"]))
    core._DUPLICATE_ORDER[:] = snapshot["duplicate_order"]
    core.INTEGRATED_TRACE_LOG[:] = copy.deepcopy(snapshot["trace_log"])
    core.INTEGRATED_LATEST_TRACE = snapshot["latest_trace"]


def _deterministic_legal_action(obs, *, prefer_nonempty=True):
    select = getattr(obs, "select", None)
    if select is None:
        return None
    options = getattr(select, "option", None)
    minimum = getattr(select, "minCount", None)
    maximum = getattr(select, "maxCount", None)
    if (
        not isinstance(options, list)
        or type(minimum) is not int
        or type(maximum) is not int
        or minimum < 0
        or maximum < minimum
        or maximum > len(options)
    ):
        return None
    count = minimum
    if prefer_nonempty and options and maximum >= 1:
        count = max(1, count)
    action = list(range(count))
    return action if model.action_is_valid(obs, action) else None


def _certify_delegate_action(obs, action):
    if model.action_is_valid(obs, action):
        return action
    return _deterministic_legal_action(obs)

def _require_certified_action(obs, action):
    certified = _certify_delegate_action(obs, action)
    if certified is None:
        raise UnrecoverableObservationFault(
            "V1_UNRECOVERABLE_ACTION_CERTIFICATION"
        )
    return certified


def _raw_action_is_valid(obs_dict, action):
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    if not isinstance(select, dict) or not isinstance(action, list):
        return False
    options = select.get("option")
    minimum = select.get("minCount")
    maximum = select.get("maxCount")
    return bool(
        isinstance(options, list)
        and type(minimum) is int
        and type(maximum) is int
        and 0 <= minimum <= maximum <= len(options)
        and minimum <= len(action) <= maximum
        and len(set(action)) == len(action)
        and all(
            type(index) is int and 0 <= index < len(options)
            for index in action
        )
    )


def _certify_raw_action(obs_dict, action, *, prefer_nonempty=True):
    if _raw_action_is_valid(obs_dict, action):
        return action
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    if not isinstance(select, dict):
        return None
    options = select.get("option")
    minimum = select.get("minCount")
    maximum = select.get("maxCount")
    if (
        not isinstance(options, list)
        or type(minimum) is not int
        or type(maximum) is not int
        or not 0 <= minimum <= maximum <= len(options)
    ):
        return None
    count = max(1, minimum) if prefer_nonempty and options and maximum >= 1 else minimum
    emergency = list(range(count))
    return emergency if _raw_action_is_valid(obs_dict, emergency) else None



def _attack_target_moves(parent, target, opponent):
    rows = (
        ((target.id, target.serial, opponent), int(parent.AreaType.ACTIVE)),
        *((_card_row(card), int(parent.AreaType.PRE_EVOLUTION)) for card in reversed(target.preEvolution)),
        *((_card_row(card), int(parent.AreaType.ENERGY)) for card in reversed(target.energyCards)),
        *((_card_row(card), int(parent.AreaType.TOOL)) for card in target.tools),
    )
    if (
        any(row is None or row[2] != opponent for row, _ in rows)
        or len({row[1] for row, _ in rows}) != len(rows)
    ):
        return None
    return tuple((row[0], row[1], area) for row, area in rows)


def _arm_attack_resolution(parent, obs, transaction):
    current = _public_state(parent, obs)
    if current is None:
        return None
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if (
        obs.current.yourIndex != owner
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or mine.active[0].serial != transaction["attacker_serial"]
        or theirs.active[0].serial != transaction["target_serial"]
    ):
        return None
    moves = _attack_target_moves(parent, theirs.active[0], 1 - owner)
    target_prizes = parent.prize_count(theirs.active[0])
    if moves is None or type(target_prizes) is not int or target_prizes < 1:
        return None
    transaction["attack_resolution"] = {
        "pre": current,
        "target_moves": moves,
        "target_prizes": target_prizes,
        "expected_damage": 20 * mine.handCount,
        "attacker_id": mine.active[0].id,
        "attacker_serial": mine.active[0].serial,
        "target_id": theirs.active[0].id,
        "target_serial": theirs.active[0].serial,
    }
    transaction["stage"] = "await_added_attack_verify"
    return [_attack_index(parent, obs)]


def _log_is_exact(log, log_type, expected):
    try:
        if int(getattr(log, "type", -1)) != int(log_type):
            return False
    except (TypeError, ValueError):
        return False
    values = vars(log)
    if any(values.get(key) != value for key, value in expected.items()):
        return False
    allowed = {"type", *expected}
    return all(key in allowed or value is None for key, value in values.items())


def _exact_attack_resolution(parent, obs, transaction):
    proof = transaction.get("attack_resolution")
    current = _public_state(parent, obs)
    if not isinstance(proof, dict) or current is None:
        return False
    pre = proof.get("pre")
    if not isinstance(pre, dict):
        return False
    owner = transaction["owner"]
    target_moves = proof.get("target_moves")
    target_prizes = proof.get("target_prizes")
    if not isinstance(target_moves, tuple) or type(target_prizes) is not int:
        return False
    expected_taken = min(target_prizes, len(pre["own_prize"]))
    unchanged = (
        "turn", "first_player", "result", "supporter_played", "stadium_played",
        "energy_attached", "retreated", "own_deck", "opponent_deck",
        "own_bench_max", "opponent_bench_max", "own_status", "own_prize",
        "opponent_prize", "own_hand_count", "opponent_hand_count", "own_hand",
        "own_discard", "stadium", "own_active", "own_bench", "opponent_bench",
    )
    expected_discard = pre["opponent_discard"] + tuple(
        (card_id, serial, 1 - owner) for card_id, serial, _ in target_moves
    )
    select = obs.select
    if (
        obs.current.yourIndex != owner
        or current["action_count"] != pre["action_count"] + 1
        or any(current[key] != pre[key] for key in unchanged)
        or current["result"] != -1
        or current["opponent_status"] != (False, False, False, False, False)
        or current["opponent_active"] != ()
        or current["opponent_discard"] != expected_discard
        or int(select.type) != 1
        or select.context != parent.SelectContext.TO_HAND
        or select.minCount != expected_taken
        or select.maxCount != expected_taken
        or len(select.option) != len(pre["own_prize"])
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.deck is not None
        or select.contextCard is not None
        or select.effect is not None
    ):
        return False
    for index, option in enumerate(select.option):
        if not _exact_option(
            option, parent.OptionType.CARD, area=parent.AreaType.PRIZE,
            index=index, playerIndex=owner,
        ):
            return False
    if len(obs.logs) != 2 + len(target_moves):
        return False
    if not _log_is_exact(obs.logs[0], 15, {
        "playerIndex": owner, "cardId": proof["attacker_id"],
        "serial": proof["attacker_serial"], "attackId": POWERFUL_HAND,
    }):
        return False
    if not _log_is_exact(obs.logs[1], 16, {
        "playerIndex": 1 - owner, "cardId": proof["target_id"],
        "serial": proof["target_serial"], "value": -proof["expected_damage"],
        "putDamageCounter": True,
    }):
        return False
    return all(
        _log_is_exact(log, 6, {
            "playerIndex": 1 - owner, "cardId": card_id, "serial": serial,
            "fromArea": parent.AreaType(from_area), "toArea": parent.AreaType.DISCARD,
        })
        for log, (card_id, serial, from_area) in zip(obs.logs[2:], target_moves)
    )


def _verify_boss_attack_resolution(parent, obs, transaction):
    proof = transaction.get("attack_resolution", {})
    pre = proof.get("pre", {})
    return bool(
        pre.get("action_count") == transaction["start"]["action_count"] + 2
        and pre.get("supporter_played") is True
        and _exact_attack_resolution(parent, obs, transaction)
    )


def _verify_mine_attack_resolution(parent, obs, transaction):
    proof = transaction.get("attack_resolution", {})
    pre = proof.get("pre", {})
    return bool(
        pre.get("action_count") == transaction["start"]["action_count"] + 1
        and pre.get("stadium_played") is True
        and _exact_attack_resolution(parent, obs, transaction)
    )


def _verify_alakazam_attack_resolution(parent, obs, transaction):
    proof = transaction.get("attack_resolution", {})
    pre = proof.get("pre", {})
    return bool(
        pre.get("action_count") == transaction["start"]["action_count"] + 2
        and _exact_attack_resolution(parent, obs, transaction)
    )
def _v0_current_ko(parent, obs, action):
    return (
        len(action) == 1 and type(action[0]) is int and 0 <= action[0] < len(obs.select.option)
        and obs.select.option[action[0]].type == parent.OptionType.ATTACK
        and obs.select.option[action[0]].attackId == POWERFUL_HAND
        and _powerful_hand_ko(parent, obs, obs.current.players[obs.current.yourIndex].handCount)
    )


def _play_rows(parent, obs, card_id):
    if not _metadata_exact(parent, card_id):
        return None
    owner, mine = obs.current.yourIndex, obs.current.players[obs.current.yourIndex]
    result = []
    for option_index, option in enumerate(obs.select.option):
        card = core._option_card(parent, obs, option)
        if (
            option.type != parent.OptionType.PLAY or card is None or card.id != card_id
            or _card_row(card) != (card_id, card.serial, owner)
            or not _exact_option(option, parent.OptionType.PLAY, index=option.index)
            or not 0 <= option.index < len(mine.hand) or mine.hand[option.index].serial != card.serial
        ):
            continue
        key = runtime_model.stable_option_key(parent, obs, option)
        if key is None:
            return None
        result.append((card.serial, repr(key), option_index, card, key))
    return sorted(result)


def _unknown_present(parent, obs):
    for option in obs.select.option:
        if option.type not in (parent.OptionType.PLAY, parent.OptionType.EVOLVE):
            continue
        card = core._option_card(parent, obs, option)
        if card is not None and card.id in UNKNOWN_IDS:
            return True
    return False


def _remove_serial(rows, serial):
    matches = [index for index, row in enumerate(rows) if row[1] == serial]
    if len(matches) != 1:
        return None
    index = matches[0]
    return rows[:index] + rows[index + 1:]


def _same_multiset(left, right):
    return sorted(left) == sorted(right)


def _exact_multiset_remove(rows, removed):
    values = list(rows)
    try:
        values.remove(removed)
    except ValueError:
        return None
    return tuple(values)


def _public_keys_equal(current, previous, keys):
    return all(current[key] == previous[key] for key in keys)


def _base_transaction(rule, snap, obs, public, index, card, key):
    return {
        "rule": rule, "owner": obs.current.yourIndex,
        "stage": {RULE_BOSS: "await_boss_child", RULE_MINE: "await_mine_attack", RULE_ALAKAZAM: "await_alakazam_ability", RULE_ALAKAZAM_EXACT_EVOLUTION_KO: "await_alakazam_ability", RULE_XEROSIC: "await_xerosic_verify", RULE_LANA: "await_lana_child", RULE_HAMMER: "await_hammer_child"}[rule],
        "snapshot_hash": snap.sha256, "start": public, "card_row": _card_row(card),
        "card_serial": card.serial, "option_key": key, "action": (index,),
    }


def _candidate_xerosic(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if obs.current.supporterPlayed or theirs.hand is not None or theirs.handCount < 4 or not _powerful_hand_ko(parent, obs, mine.handCount - 1):
        return None
    rows = _play_rows(parent, obs, XEROSIC)
    if not rows:
        return None
    _, _, index, card, key = rows[0]
    protected = [card.serial] + parent._bridge_pokemon_component_serials(mine.active[0]) + parent._bridge_pokemon_component_serials(theirs.active[0])
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_XEROSIC, snap, obs, public, index, card, key)
    transaction.update(opponent_discards=theirs.handCount - 3, protected_serials=tuple(protected))
    return [index], transaction


def _candidate_lana(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if obs.current.supporterPlayed or len(theirs.active) != 1:
        return None
    required, base = ceil(theirs.active[0].hp / 20), mine.handCount - 1
    recoverable = []
    for card in mine.discard:
        data = parent.card_table.get(card.id)
        if (
            card.id not in LANA_ALLOWLIST or card.id in LANA_EXCLUDED or data is None
            or data.cardType not in (parent.CardType.POKEMON, parent.CardType.BASIC_ENERGY)
            or (data.cardType == parent.CardType.POKEMON and (data.ex or data.megaEx))
        ):
            continue
        recoverable.append((0 if card.id == ALAKAZAM else 1, card.id, card.serial, card))
    needed = required - base
    if base >= required or not 1 <= needed <= 3 or needed > len(recoverable) or not _powerful_hand_ko(parent, obs, base + needed):
        return None
    rows = _play_rows(parent, obs, LANAS_AID)
    if not rows:
        return None
    _, _, index, card, key = rows[0]
    chosen = tuple(row[3] for row in sorted(recoverable)[:needed])
    protected = [card.serial] + [item.serial for item in chosen] + parent._bridge_pokemon_component_serials(mine.active[0]) + parent._bridge_pokemon_component_serials(theirs.active[0])
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_LANA, snap, obs, public, index, card, key)
    transaction.update(selected_rows=tuple(_card_row(item) for item in chosen), recovery_count=needed, protected_serials=tuple(protected))
    return [index], transaction


def _exact_ready_attacks(parent, state, pokemon, owner):
    data = parent.card_table.get(pokemon.id)
    units = semantics.energy_units(parent, pokemon)
    if (
        data is None
        or units is None
        or not parent._bridge_pokemon_is_publicly_complete(pokemon, owner)
        or not _cost_environment_clear(parent, state)
    ):
        return None
    effect_cards = [data]
    for tool in pokemon.tools:
        tool_data = parent.card_table.get(tool.id)
        if tool_data is None:
            return None
        effect_cards.append(tool_data)
    if any(
        "cost" in parent._normalized_skill_text(skill.text)
        for effect_card in effect_cards
        for skill in (effect_card.skills or ())
    ):
        return None
    ready = []
    for attack_id in data.attacks or ():
        attack = parent.attack_table.get(attack_id)
        if attack is None or attack.attackId != attack_id:
            return None
        if not semantics.missing_energy(parent, units, attack.energies):
            ready.append(attack_id)
    return tuple(ready)


def _without_energy_card(pokemon, energy_index):
    if not 0 <= energy_index < len(pokemon.energyCards):
        return None
    if len(pokemon.energyCards) != len(pokemon.energies):
        return None
    virtual = copy.deepcopy(pokemon)
    virtual.energyCards.pop(energy_index)
    virtual.energies.pop(energy_index)
    return virtual


def _hammer_enables_current_ko(parent, obs, area, pokemon, energy_index):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    virtual = _without_energy_card(pokemon, energy_index)
    hand_after = mine.handCount - 1
    if (
        area != parent.AreaType.ACTIVE
        or len(theirs.active) != 1
        or theirs.active[0].serial != pokemon.serial
        or virtual is None
        or _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, pokemon, 1 - owner
        )
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, virtual, 1 - owner
        )
        or hand_after < ceil(pokemon.hp / 20)
        or len(mine.active) != 1
        or mine.active[0].id != ALAKAZAM
        or not parent._two_prize_powerful_hand_metadata_is_exact()
        or parent.card_table[ALAKAZAM].tera
        or not parent._two_prize_alakazam_is_ready(mine.active[0], owner)
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or _attack_index(parent, obs) is None
    ):
        return False
    return True


def _hammer_stops_sole_backup(parent, obs, area, pokemon, energy_index):
    owner = obs.current.yourIndex
    theirs = obs.current.players[1 - owner]
    if area != parent.AreaType.BENCH:
        return False
    ready = []
    for field_area, group in (
        (parent.AreaType.ACTIVE, theirs.active),
        (parent.AreaType.BENCH, theirs.bench),
    ):
        for field_index, candidate in enumerate(group):
            attacks = _exact_ready_attacks(parent, obs.current, candidate, 1 - owner)
            if attacks is None:
                return False
            if attacks:
                ready.append((field_area, field_index, candidate.serial))
    if len(ready) != 1 or ready[0][2] != pokemon.serial:
        return False
    virtual = _without_energy_card(pokemon, energy_index)
    if virtual is None:
        return False
    after = _exact_ready_attacks(parent, obs.current, virtual, 1 - owner)
    return after == ()


def _energy_type_is_exact(parent, value):
    return bool(
        isinstance(value, int)
        and not isinstance(value, bool)
        and int(value) in {int(member) for member in parent.EnergyType}
    )


def _fingerprint_without_energy(
    fingerprint,
    energy_index,
    energy_row,
    *,
    grow_grass_target,
):
    if (
        type(fingerprint) is not tuple
        or len(fingerprint) != 10
        or type(energy_index) is not int
        or type(energy_row) is not tuple
        or len(energy_row) != 3
        or any(type(value) is not int for value in energy_row)
        or energy_row[0] <= 0
        or energy_row[1] <= 0
        or energy_row[2] not in (0, 1)
        or type(grow_grass_target) is not bool
        or type(fingerprint[2]) is not int
        or type(fingerprint[3]) is not int
        or not 0 < fingerprint[2] <= fingerprint[3]
        or type(fingerprint[6]) is not tuple
        or type(fingerprint[7]) is not tuple
        or len(fingerprint[6]) != len(fingerprint[7])
        or not 0 <= energy_index < len(fingerprint[6])
        or type(fingerprint[6][energy_index]) is not int
        or fingerprint[7][energy_index] != energy_row
    ):
        return None
    values = list(fingerprint)
    if energy_row[0] == 18 and grow_grass_target:
        next_hp = fingerprint[2] - 20
        next_max_hp = fingerprint[3] - 20
        if not 0 < next_hp <= next_max_hp:
            return None
        values[2] = next_hp
        values[3] = next_max_hp
    values[6] = (
        fingerprint[6][:energy_index] + fingerprint[6][energy_index + 1:]
    )
    values[7] = (
        fingerprint[7][:energy_index] + fingerprint[7][energy_index + 1:]
    )
    return tuple(values)


def _hammer_target_certificate(
    parent,
    public,
    owner,
    area,
    pokemon_index,
    pokemon,
    energy_index,
    energy,
):
    if area == parent.AreaType.ACTIVE:
        area_key = "opponent_active"
    elif area == parent.AreaType.BENCH:
        area_key = "opponent_bench"
    else:
        return None
    other_area_key = (
        "opponent_bench"
        if area_key == "opponent_active"
        else "opponent_active"
    )
    if (
        public is None
        or type(pokemon_index) is not int
        or not 0 <= pokemon_index < len(public[area_key])
        or sum(
            row[1] == pokemon.serial
            for row in public[area_key] + public[other_area_key]
        )
        != 1
    ):
        return None
    target_data = parent.card_table.get(pokemon.id)
    before = parent._bridge_pokemon_fingerprint(pokemon)
    energy_row = _card_row(energy)
    if (
        target_data is None
        or target_data.cardId != pokemon.id
        or target_data.cardType != parent.CardType.POKEMON
        or not _energy_type_is_exact(parent, target_data.energyType)
        or before != public[area_key][pokemon_index]
        or type(energy_row) is not tuple
        or energy_row[2] != 1 - owner
    ):
        return None
    expected_after = _fingerprint_without_energy(
        before,
        energy_index,
        energy_row,
        grow_grass_target=(
            int(target_data.energyType) == int(parent.EnergyType.GRASS)
        ),
    )
    if expected_after is None:
        return None
    return before, expected_after, energy_row


def _candidate_hammer(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    special = []
    for area, group in (
        (parent.AreaType.ACTIVE, theirs.active),
        (parent.AreaType.BENCH, theirs.bench),
    ):
        for pokemon_index, pokemon in enumerate(group):
            if semantics.energy_units(parent, pokemon) is None:
                return None
            for energy_index, energy in enumerate(pokemon.energyCards):
                data = parent.card_table.get(energy.id)
                if data is None:
                    return None
                if data.cardType == parent.CardType.SPECIAL_ENERGY:
                    special.append(
                        (area, pokemon_index, pokemon, energy_index, energy)
                    )
    if len(special) != 1:
        return None
    area, pokemon_index, pokemon, energy_index, energy = special[0]
    if _hammer_enables_current_ko(parent, obs, area, pokemon, energy_index):
        mode = "ENABLE_COUNTER_KO"
    elif (
        _powerful_hand_ko(parent, obs, mine.handCount - 1)
        and _hammer_stops_sole_backup(
            parent, obs, area, pokemon, energy_index
        )
    ):
        mode = "STOP_SOLE_BACKUP"
    else:
        return None
    target_certificate = _hammer_target_certificate(
        parent,
        public,
        owner,
        area,
        pokemon_index,
        pokemon,
        energy_index,
        energy,
    )
    if target_certificate is None:
        return None
    target_before, target_expected_after, energy_row = target_certificate
    rows = _play_rows(parent, obs, ENHANCED_HAMMER)
    if not rows:
        return None
    _, _, index, card, key = rows[0]
    protected = (
        [card.serial]
        + parent._bridge_pokemon_component_serials(mine.active[0])
        + parent._bridge_pokemon_component_serials(theirs.active[0])
    )
    if pokemon.serial != theirs.active[0].serial:
        protected += parent._bridge_pokemon_component_serials(pokemon)
    if not parent._bridge_protected_serials_are_unique(
        obs.current, protected
    ):
        return None
    transaction = _base_transaction(
        RULE_HAMMER, snap, obs, public, index, card, key
    )
    transaction.update(
        energy_area=int(area),
        pokemon_index=pokemon_index,
        pokemon_serial=pokemon.serial,
        energy_index=energy_index,
        energy_id=energy.id,
        energy_serial=energy.serial,
        energy_owner=energy.playerIndex,
        energy_row=energy_row,
        target_before_fingerprint=target_before,
        target_expected_after_fingerprint=target_expected_after,
        hammer_mode=mode,
        protected_serials=tuple(protected),
    )
    return [index], transaction
def _played_delta(
    parent,
    obs,
    transaction,
    opponent_changes=False,
    action_count_delta=1,
    card_in_discard=False,
):
    current, start = _public_state(parent, obs), transaction["start"]
    expected_hand = _exact_multiset_remove(
        start["own_hand"], transaction["card_row"]
    )
    if current is None or expected_hand is None:
        return None
    unchanged = (
        "turn", "first_player", "result", "stadium_played",
        "energy_attached", "retreated", "own_deck", "opponent_deck",
        "own_bench_max", "opponent_bench_max", "own_status",
        "opponent_status", "own_prize", "opponent_prize", "stadium",
        "own_active", "own_bench", "opponent_active", "opponent_bench",
        "fields",
    )
    if (
        obs.current.yourIndex != transaction["owner"]
        or not _public_keys_equal(current, start, unchanged)
    ):
        return None
    if (
        current["action_count"] != start["action_count"] + action_count_delta
        or not _same_multiset(current["own_hand"], expected_hand)
        or current["own_hand_count"] != start["own_hand_count"] - 1
        or not _same_multiset(
            current["own_discard"],
            (
                start["own_discard"] + (transaction["card_row"],)
                if card_in_discard
                else start["own_discard"]
            ),
        )
    ):
        return None
    if transaction["rule"] in (
        RULE_BOSS, RULE_BOSS_READY_STOP, RULE_XEROSIC, RULE_LANA
    ):
        if start["supporter_played"] or not current["supporter_played"]:
            return None
    elif current["supporter_played"] != start["supporter_played"]:
        return None
    if not opponent_changes and (
        current["opponent_hand_count"] != start["opponent_hand_count"]
        or not _same_multiset(
            current["opponent_discard"], start["opponent_discard"]
        )
    ):
        return None
    return current

def _find_pokemon(parent, obs, owner, serial):
    matches = []
    player = obs.current.players[owner]
    for area, group in ((parent.AreaType.ACTIVE, player.active), (parent.AreaType.BENCH, player.bench)):
        for index, pokemon in enumerate(group):
            if pokemon.serial == serial:
                matches.append((area, index, pokemon))
    return matches[0] if len(matches) == 1 else None


def _advance_lana(parent, obs, transaction):
    select, owner = obs.select, transaction["owner"]
    if (
        _played_delta(parent, obs, transaction) is None
        or obs.current.yourIndex != owner
        or type(select.maxCount) is not int
        or not 1 <= select.maxCount <= 3
        or _child_prompt_envelope(
            parent,
            obs,
            select_type=1,
            context=parent.SelectContext.TO_HAND,
            effect=transaction["card_row"],
            min_count=1,
            max_count=select.maxCount,
        ) is None
    ):
        return None
    census = _option_census(parent, obs)
    if census is None:
        return None
    legal_indices = []
    for option_index, option in enumerate(select.option):
        card = core._option_card(parent, obs, option)
        data = parent.card_table.get(getattr(card, "id", None))
        if (
            option.type == parent.OptionType.CARD
            and option.area == parent.AreaType.DISCARD
            and option.playerIndex == owner
            and _exact_option(
                option,
                parent.OptionType.CARD,
                area=parent.AreaType.DISCARD,
                index=option.index,
                playerIndex=owner,
            )
            and card is not None
            and card.id in LANA_ALLOWLIST
            and card.id not in LANA_EXCLUDED
            and data is not None
            and data.cardType in (parent.CardType.POKEMON, parent.CardType.BASIC_ENERGY)
            and not (
                data.cardType == parent.CardType.POKEMON
                and (data.ex or data.megaEx)
            )
        ):
            legal_indices.append(option_index)
    if select.maxCount != min(3, len(legal_indices)):
        return None
    chosen = []
    for wanted in transaction["selected_rows"]:
        matches = []
        for option_index, option in enumerate(select.option):
            card = core._option_card(parent, obs, option)
            data = parent.card_table.get(getattr(card, "id", None))
            if (
                option.type == parent.OptionType.CARD and option.area == parent.AreaType.DISCARD
                and option.playerIndex == owner
                and _exact_option(option, parent.OptionType.CARD, area=parent.AreaType.DISCARD, index=option.index, playerIndex=owner)
                and _card_row(card) == wanted and card.id in LANA_ALLOWLIST and card.id not in LANA_EXCLUDED
                and data is not None and data.cardType in (parent.CardType.POKEMON, parent.CardType.BASIC_ENERGY)
                and not (data.cardType == parent.CardType.POKEMON and (data.ex or data.megaEx))
            ):
                matches.append((option_index, census[option_index]))
        if len(matches) != 1:
            return None
        chosen.append(matches[0])
    if len({index for index, _ in chosen}) != transaction["recovery_count"]:
        return None
    transaction["stage"] = "await_lana_verify"
    transaction["post_play"] = _public_state(parent, obs)
    return [index for index, _ in chosen]


def _advance_hammer(parent, obs, transaction):
    select, owner = obs.select, transaction["owner"]
    current = _played_delta(parent, obs, transaction)
    found = _find_pokemon(
        parent, obs, 1 - owner, transaction["pokemon_serial"]
    )
    if transaction["energy_area"] == int(parent.AreaType.ACTIVE):
        area_key = "opponent_active"
    elif transaction["energy_area"] == int(parent.AreaType.BENCH):
        area_key = "opponent_bench"
    else:
        return None
    if (
        current is None
        or obs.current.yourIndex != owner
        or found is None
        or found[0] != parent.AreaType(transaction["energy_area"])
        or found[1] != transaction["pokemon_index"]
        or parent._bridge_pokemon_fingerprint(found[2])
        != transaction.get("target_before_fingerprint")
        or not 0 <= transaction["pokemon_index"] < len(current[area_key])
        or current[area_key][transaction["pokemon_index"]]
        != transaction.get("target_before_fingerprint")
        or _child_prompt_envelope(
            parent,
            obs,
            select_type=4,
            context=parent.SelectContext.DISCARD_ENERGY,
            effect=transaction["card_row"],
            remain_energy_cost=1,
        ) is None
    ):
        return None
    census = _option_census(parent, obs)
    if census is None:
        return None
    matches = []
    for option_index, option in enumerate(select.option):
        if (
            option.type != parent.OptionType.ENERGY
            or int(option.area) != transaction["energy_area"]
            or option.index != transaction["pokemon_index"]
            or option.playerIndex != 1 - owner
            or option.energyIndex != transaction["energy_index"]
            or option.count != 1
            or not _exact_option(
                option,
                parent.OptionType.ENERGY,
                area=parent.AreaType(transaction["energy_area"]),
                index=transaction["pokemon_index"],
                playerIndex=1 - owner,
                energyIndex=transaction["energy_index"],
                count=1,
            )
            or found[0] != option.area
            or found[1] != option.index
            or not 0 <= option.energyIndex < len(found[2].energyCards)
            or _card_row(found[2].energyCards[option.energyIndex])
            != transaction["energy_row"]
            or found[2].energyCards[option.energyIndex].id
            != transaction["energy_id"]
            or found[2].energyCards[option.energyIndex].serial
            != transaction["energy_serial"]
            or found[2].energyCards[option.energyIndex].playerIndex
            != transaction["energy_owner"]
        ):
            continue
        matches.append((option_index, census[option_index]))
    if len(matches) != 1:
        return None
    transaction["stage"] = "await_hammer_verify"
    transaction["post_play"] = current
    return [matches[0][0]]

def _verify_lana(parent, obs, transaction):
    current, post = _public_state(parent, obs), transaction["post_play"]
    selected = transaction["selected_rows"]
    expected_discard = post["own_discard"] + (transaction["card_row"],)
    for row in selected:
        expected_discard = _exact_multiset_remove(expected_discard, row)
        if expected_discard is None:
            return False
    unchanged = (
        "turn", "first_player", "result",
        "supporter_played", "stadium_played", "energy_attached",
        "retreated", "own_deck", "opponent_deck", "own_bench_max",
        "opponent_bench_max", "own_status", "opponent_status",
        "own_prize", "opponent_prize", "opponent_hand_count",
        "opponent_discard", "stadium", "own_active", "own_bench",
        "opponent_active", "opponent_bench", "fields",
    )
    return bool(
        current is not None
        and _child_prompt_envelope(
            parent, obs, select_type=0, context=parent.SelectContext.MAIN
        ) is not None
        and _public_keys_equal(current, post, unchanged)
        and current["action_count"] == post["action_count"] + 1
        and current["own_hand_count"]
        == post["own_hand_count"] + transaction["recovery_count"]
        and _same_multiset(current["own_hand"], post["own_hand"] + selected)
        and _same_multiset(current["own_discard"], expected_discard)
        and len(obs.logs) == len(selected)
        and all(
            _log_is_exact(
                log,
                6,
                {
                    "playerIndex": transaction["owner"],
                    "cardId": row[0],
                    "serial": row[1],
                    "fromArea": parent.AreaType.DISCARD,
                    "toArea": parent.AreaType.HAND,
                },
            )
            for log, row in zip(obs.logs, selected)
        )
        and _powerful_hand_ko(parent, obs, current["own_hand_count"])
    )



def _verify_hammer(parent, obs, transaction):
    current = _public_state(parent, obs)
    post = transaction.get("post_play")
    found = _find_pokemon(
        parent, obs, 1 - transaction["owner"], transaction["pokemon_serial"]
    )
    if transaction["energy_area"] == int(parent.AreaType.ACTIVE):
        area_key = "opponent_active"
    elif transaction["energy_area"] == int(parent.AreaType.BENCH):
        area_key = "opponent_bench"
    else:
        return False
    other_area_key = (
        "opponent_bench"
        if area_key == "opponent_active"
        else "opponent_active"
    )
    before_rows = () if post is None else post[area_key]
    expected_rows = None
    target_index = transaction.get("pokemon_index")
    target_before = transaction.get("target_before_fingerprint")
    target_expected_after = transaction.get(
        "target_expected_after_fingerprint"
    )
    if (
        type(target_index) is int
        and 0 <= target_index < len(before_rows)
        and before_rows[target_index] == target_before
        and sum(
            row[1] == transaction["pokemon_serial"]
            for row in before_rows + post[other_area_key]
        )
        == 1
    ):
        expected_rows = list(before_rows)
        expected_rows[target_index] = target_expected_after
        expected_rows = tuple(expected_rows)
    unchanged = (
        "turn", "first_player", "result",
        "supporter_played", "stadium_played", "energy_attached",
        "retreated", "own_deck", "opponent_deck", "own_bench_max",
        "opponent_bench_max", "own_status", "opponent_status",
        "own_prize", "opponent_prize", "own_hand_count",
        "opponent_hand_count", "own_hand", "stadium",
        "own_active", "own_bench",
    )
    mode_ok = False
    if current is not None and found is not None:
        if transaction["hammer_mode"] == "ENABLE_COUNTER_KO":
            mode_ok = _powerful_hand_ko(parent, obs, current["own_hand_count"])
        elif transaction["hammer_mode"] == "STOP_SOLE_BACKUP":
            mode_ok = (
                _exact_ready_attacks(
                    parent, obs.current, found[2], 1 - transaction["owner"]
                )
                == ()
            )
    return bool(
        current is not None
        and _child_prompt_envelope(
            parent, obs, select_type=0, context=parent.SelectContext.MAIN
        ) is not None
        and found is not None
        and found[0] == parent.AreaType(transaction["energy_area"])
        and found[1] == target_index
        and parent._bridge_pokemon_fingerprint(found[2])
        == target_expected_after
        and expected_rows is not None
        and _public_keys_equal(current, post, unchanged)
        and current["action_count"] == post["action_count"] + 1
        and _same_multiset(
            current["own_discard"],
            post["own_discard"] + (transaction["card_row"],),
        )
        and current[area_key] == expected_rows
        and current[other_area_key] == post[other_area_key]
        and _same_multiset(
            current["opponent_discard"],
            post["opponent_discard"] + (transaction["energy_row"],),
        )
        and len(obs.logs) == 1
        and _log_is_exact(
            obs.logs[0],
            6,
            {
                "playerIndex": 1 - transaction["owner"],
                "cardId": transaction["energy_row"][0],
                "serial": transaction["energy_row"][1],
                "fromArea": parent.AreaType.ENERGY,
                "toArea": parent.AreaType.DISCARD,
            },
        )
        and mode_ok
    )

def _verify_xerosic(parent, obs, transaction):
    current = _played_delta(
        parent,
        obs,
        transaction,
        opponent_changes=True,
        action_count_delta=2,
        card_in_discard=True,
    )
    start_discard = transaction["start"]["opponent_discard"]
    added = None
    if (
        current is not None
        and current["opponent_discard"][: len(start_discard)] == start_discard
    ):
        added = current["opponent_discard"][len(start_discard):]
    logs_exact = bool(
        added is not None
        and len(obs.logs) == 1 + len(added)
        and _log_is_exact(
            obs.logs[0],
            10,
            {
                "playerIndex": transaction["owner"],
                "cardId": transaction["card_row"][0],
                "serial": transaction["card_row"][1],
            },
        )
        and all(
            _log_is_exact(
                log,
                6,
                {
                    "playerIndex": 1 - transaction["owner"],
                    "cardId": row[0],
                    "serial": row[1],
                    "fromArea": parent.AreaType.HAND,
                    "toArea": parent.AreaType.DISCARD,
                },
            )
            for log, row in zip(obs.logs[1:], added)
        )
    )
    return bool(
        current is not None
        and _child_prompt_envelope(
            parent, obs, select_type=0, context=parent.SelectContext.MAIN
        ) is not None
        and current["opponent_hand_count"] == 3
        and added is not None
        and len(added) == transaction["opponent_discards"]
        and logs_exact
        and _powerful_hand_ko(parent, obs, current["own_hand_count"])
    )

def _remember(parent, obs, snap_hash, action):
    V1_DUPLICATES[snap_hash] = tuple(runtime_model.stable_option_key(parent, obs, obs.select.option[index]) for index in action)


def _rebind_duplicate(parent, obs, snap_hash):
    keys = V1_DUPLICATES.get(snap_hash)
    if keys is None:
        return None
    action = model.rebind_option_keys(parent, obs, keys)
    if action is None or not model.action_is_valid(obs, action):
        V1_DUPLICATES.pop(snap_hash, None)
        return None
    return action


def _record_removed_rule_hits(parent, obs, action, blocked_route):
    global REMOVED_RULE_HITS
    hits = []
    if isinstance(action, (list, tuple)):
        for option_index in action:
            if type(option_index) is not int or not 0 <= option_index < len(obs.select.option):
                continue
            row = _owned_removed_option(parent, obs, obs.select.option[option_index])
            if row is None:
                continue
            hits.append({
                "card_id": row[0],
                "card_serial": row[1],
                "owner": row[2],
                "blocked_route": blocked_route,
            })
    REMOVED_RULE_HITS = hits


def _record_removed_parent_owner(obs, blocked_route):
    global REMOVED_RULE_HITS
    REMOVED_RULE_HITS = [{
        "card_id": None,
        "card_serial": None,
        "owner": obs.current.yourIndex,
        "blocked_route": blocked_route,
    }]


def _irreversible_fault_action(parent, obs):
    forced = False
    try:
        action, forced = _lowest_legal_without_removed(parent, obs)
        if not action and obs.select.option and obs.select.maxCount >= 1:
            action = _deterministic_legal_action(obs)
    except Exception:
        action = _deterministic_legal_action(obs)
    if action is None or not model.action_is_valid(obs, action):
        action = _deterministic_legal_action(obs, prefer_nonempty=False)
    if action is None:
        raise UnrecoverableObservationFault(
            "V1_UNRECOVERABLE_IRREVERSIBLE_FAULT_ACTION"
        )
    if forced:
        _record_removed_rule_hits(
            parent, obs, action, "V1_IRREVERSIBLE_ABORT_FAULT_FORCED_PROMPT"
        )
    return action


# --- v4 Fix8: persistent, main-only zero-demand Poffin veto. ---

def _v4_poffin_zero_trace(
    stage,
    reason,
    *,
    eligibility=None,
    parent_action=None,
    proposed_action=None,
    applied_action=None,
    source=None,
):
    global LAST_V4_POFFIN_ZERO_VETO_TRACE
    eligibility = eligibility if isinstance(eligibility, dict) else {}
    LAST_V4_POFFIN_ZERO_VETO_TRACE = {
        "rule": RULE_POFFIN_ZERO_DEMAND_VETO,
        "stage": stage,
        "reason": reason,
        "source": source,
        "eligibility_hash": eligibility.get("sha256"),
        "eligibility": copy.deepcopy(eligibility.get("payload")),
        "parent_action": (
            list(parent_action)
            if isinstance(parent_action, (list, tuple))
            else []
        ),
        "proposed_action": (
            list(proposed_action)
            if isinstance(proposed_action, (list, tuple))
            else []
        ),
        "applied_action": (
            list(applied_action)
            if isinstance(applied_action, (list, tuple))
            else []
        ),
    }
    V4_POFFIN_ZERO_VETO_TRACE_HISTORY.append(
        copy.deepcopy(LAST_V4_POFFIN_ZERO_VETO_TRACE)
    )
    if len(V4_POFFIN_ZERO_VETO_TRACE_HISTORY) > 128:
        del V4_POFFIN_ZERO_VETO_TRACE_HISTORY[:-128]


def _v4_clear_poffin_zero_latch(reason, *, source=None):
    global POFFIN_ZERO_DEMAND_LATCH
    previous = POFFIN_ZERO_DEMAND_LATCH
    POFFIN_ZERO_DEMAND_LATCH = None
    _v4_poffin_zero_trace(
        "RELEASE",
        reason,
        eligibility=previous,
        source=source,
    )


def _v4_poffin_zero_clock_guard(obs):
    """Release stale state without making turnActionCount part of eligibility."""
    global POFFIN_ZERO_DEMAND_LATCH
    latch = POFFIN_ZERO_DEMAND_LATCH
    if latch is None:
        return
    state = getattr(obs, "current", None)
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or type(state.turn) is not int
        or type(state.turnActionCount) is not int
        or state.result != -1
    ):
        _v4_clear_poffin_zero_latch("GAME_OR_HANDSHAKE_RESET")
        return
    if state.yourIndex != latch.get("owner"):
        _v4_clear_poffin_zero_latch("OWNER_CHANGED")
        return
    if state.turn != latch.get("turn"):
        _v4_clear_poffin_zero_latch("TURN_CHANGED")
        return
    previous_action_count = latch.get("last_action_count")
    if (
        type(previous_action_count) is not int
        or state.turnActionCount < previous_action_count
    ):
        _v4_clear_poffin_zero_latch("TURN_ACTION_COUNT_ROLLBACK")
        return
    latch["last_action_count"] = state.turnActionCount


def _v4_structural_role_board(parent, obs):
    """Return field identity relevant to Poffin demand, excluding attachments."""
    state = obs.current
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or len(state.players) != 2
    ):
        return None
    owner = state.yourIndex
    mine = state.players[owner]
    if (
        type(mine.benchMax) is not int
        or mine.benchMax < 0
        or mine.benchMax < len(mine.bench)
    ):
        return None
    field_rows = []
    serials = []
    abra_count = 0
    dunsparce_count = 0
    for area_name, pokemon_rows in (
        ("ACTIVE", mine.active),
        ("BENCH", mine.bench),
    ):
        for position, pokemon in enumerate(pokemon_rows):
            if (
                pokemon is None
                or not parent._bridge_pokemon_is_publicly_complete(
                    pokemon, owner
                )
            ):
                return None
            component_serials = parent._bridge_pokemon_component_serials(
                pokemon
            )
            if (
                any(
                    type(serial) is not int or serial <= 0
                    for serial in component_serials
                )
                or len(component_serials) != len(set(component_serials))
            ):
                return None
            serials.extend(component_serials)
            lineage = tuple(
                (card.id, card.serial)
                for card in pokemon.preEvolution
            )
            field_rows.append(
                (
                    area_name,
                    position,
                    pokemon.id,
                    pokemon.serial,
                    lineage,
                )
            )
            abra_count += pokemon.id in (ABRA, KADABRA, ALAKAZAM)
            dunsparce_count += pokemon.id in (DUNSPARCE, 66)
    if len(serials) != len(set(serials)):
        return None
    return {
        "owner": owner,
        "A": abra_count,
        "N": dunsparce_count,
        "F": mine.benchMax - len(mine.bench),
        "field_fingerprints": tuple(field_rows),
    }


def _v4_public_role_inventory(parent, obs, obs_dict):
    """Prove remaining Abra/Dunsparce inventory from the exact public partition."""
    state = obs.current
    if (
        state is None
        or state.yourIndex not in (0, 1)
        or len(state.players) != 2
    ):
        return None
    owner = state.yourIndex
    mine = state.players[owner]
    try:
        raw_state = obs_dict["current"]
        raw_mine = raw_state["players"][owner]
        raw_public_cards = list(raw_mine["hand"]) + list(
            raw_mine["discard"]
        )
        for raw_pokemon in (
            list(raw_mine["active"]) + list(raw_mine["bench"])
        ):
            raw_public_cards.append(raw_pokemon)
            raw_public_cards.extend(raw_pokemon["preEvolution"])
            raw_public_cards.extend(raw_pokemon["energyCards"])
            raw_public_cards.extend(raw_pokemon["tools"])
        raw_public_cards.extend(
            card for card in raw_mine["prize"] if card is not None
        )
        raw_public_cards.extend(
            card
            for card in raw_state["stadium"]
            if card.get("playerIndex") == owner
        )
        if any(
            card.get("playerIndex") != owner
            for card in raw_public_cards
        ):
            return None
    except (KeyError, TypeError, IndexError, AttributeError):
        return None
    if (
        mine.hand is None
        or len(mine.hand) != mine.handCount
        or type(mine.deckCount) is not int
        or mine.deckCount < 0
    ):
        return None
    public_cards = []

    def add(card, *, pokemon_top=False):
        row = (
            (
                getattr(card, "id", None),
                getattr(card, "serial", None),
                owner,
            )
            if pokemon_top
            else _card_row(card)
        )
        if (
            row is None
            or row[2] != owner
            or type(row[0]) is not int
            or row[0] <= 0
            or type(row[1]) is not int
            or row[1] <= 0
        ):
            return False
        public_cards.append(row)
        return True

    for card in list(mine.hand) + list(mine.discard):
        if not add(card):
            return None
    for pokemon in list(mine.active) + list(mine.bench):
        if (
            pokemon is None
            or not parent._bridge_pokemon_is_publicly_complete(
                pokemon, owner
            )
            or not add(pokemon, pokemon_top=True)
        ):
            return None
        for card in (
            list(pokemon.preEvolution)
            + list(pokemon.energyCards)
            + list(pokemon.tools)
        ):
            if not add(card):
                return None
    hidden_prizes = 0
    for card in mine.prize:
        if card is None:
            hidden_prizes += 1
        elif not add(card):
            return None
    for card in state.stadium:
        row = _card_row(card)
        if row is None:
            return None
        if row[2] == owner and not add(card):
            return None
    serials = [row[1] for row in public_cards]
    if (
        len(serials) != len(set(serials))
        or len(public_cards) + mine.deckCount + hidden_prizes
        != EXACT_DECK_SIZE
    ):
        return None
    public_role_counts = {
        card_id: sum(row[0] == card_id for row in public_cards)
        for card_id in EXACT_DECK_ROLE_COUNTS
    }
    if any(
        public_role_counts[card_id] > exact_count
        for card_id, exact_count in EXACT_DECK_ROLE_COUNTS.items()
    ):
        return None
    unknown_role_counts = {
        card_id: EXACT_DECK_ROLE_COUNTS[card_id]
        - public_role_counts[card_id]
        for card_id in EXACT_DECK_ROLE_COUNTS
    }
    return {
        "public_card_count": len(public_cards),
        "hidden_prize_count": hidden_prizes,
        "deck_count": mine.deckCount,
        "public_role_counts": public_role_counts,
        "unknown_role_counts": unknown_role_counts,
    }


def _v4_exact_poffin_play_rows(parent, obs):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    rows = []
    for option_index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.PLAY:
            continue
        if (
            type(option.index) is not int
            or not 0 <= option.index < len(mine.hand or ())
        ):
            return None
        card = mine.hand[option.index]
        if card.id != BUDDY_BUDDY_POFFIN:
            continue
        key = runtime_model.stable_option_key(parent, obs, option)
        if (
            not _exact_option(
                option, parent.OptionType.PLAY, index=option.index
            )
            or _card_row(card)
            != (BUDDY_BUDDY_POFFIN, card.serial, owner)
            or key is None
        ):
            return None
        rows.append(
            {
                "option_index": option_index,
                "hand_index": option.index,
                "card_serial": card.serial,
                "option_key": key,
                "option_key_repr": repr(key),
            }
        )
    return tuple(rows)


def _v4_selected_poffin_row(parent, obs, action, poffin_rows):
    if (
        not isinstance(action, (list, tuple))
        or len(action) != 1
        or type(action[0]) is not int
    ):
        return None
    matches = [
        row for row in poffin_rows
        if row["option_index"] == action[0]
    ]
    return matches[0] if len(matches) == 1 else None


def _v4_poffin_zero_eligibility(parent, obs, obs_dict):
    select = obs.select
    if (
        select is None
        or select.context != parent.SelectContext.MAIN
        or int(select.type) != 0
        or select.minCount != 1
        or select.maxCount != 1
        or select.remainDamageCounter != 0
        or select.remainEnergyCost != 0
        or select.effect is not None
        or select.contextCard is not None
        or select.deck is not None
        or obs.current.result != -1
        or _option_census(parent, obs) is None
    ):
        return None, "NOT_EXACT_NORMAL_MAIN"
    board = _v4_structural_role_board(parent, obs)
    inventory = _v4_public_role_inventory(parent, obs, obs_dict)
    poffin_rows = _v4_exact_poffin_play_rows(parent, obs)
    if board is None:
        return None, "PUBLIC_ROLE_BOARD_NOT_EXACT"
    if inventory is None:
        return None, "PUBLIC_ROLE_INVENTORY_NOT_EXACT"
    if not poffin_rows:
        return None, "NO_EXACT_POFFIN_PLAY"
    unknown_abra = inventory["unknown_role_counts"][ABRA]
    unknown_dunsparce = inventory["unknown_role_counts"][DUNSPARCE]
    normal_capacity = min(2, max(0, board["F"] - 1))
    abra_final_slot_exception = bool(
        board["A"] == 0
        and board["F"] == 1
        and unknown_abra >= 1
    )
    zero_demand_reason = None
    if board["F"] == 0:
        zero_demand_reason = "NO_LEGAL_EMPTY_BENCH"
    elif unknown_abra == 0 and unknown_dunsparce == 0:
        zero_demand_reason = "PUBLIC_ROLE_BASICS_DEPLETED"
    elif normal_capacity == 0 and not abra_final_slot_exception:
        zero_demand_reason = "ZERO_NORMAL_CAPACITY_NO_ABRA_EXCEPTION"
    elif board["A"] >= 2 and board["N"] >= 2:
        zero_demand_reason = "ZERO_ROLE_DEMAND"
    payload = {
        "schema": "V4_POFFIN_ZERO_ELIGIBILITY_FIX8",
        "owner": board["owner"],
        "turn": obs.current.turn,
        "first_player": obs.current.firstPlayer,
        "normal_main": True,
        "poffin_play_keys": tuple(
            sorted(row["option_key_repr"] for row in poffin_rows)
        ),
        "A": board["A"],
        "N": board["N"],
        "F": board["F"],
        "field_fingerprints": board["field_fingerprints"],
        "public_role_counts": {
            "Abra": inventory["public_role_counts"][ABRA],
            "Dunsparce": inventory["public_role_counts"][DUNSPARCE],
        },
        "unknown_role_counts": {
            "Abra": unknown_abra,
            "Dunsparce": unknown_dunsparce,
        },
        "public_card_count": inventory["public_card_count"],
        "hidden_prize_count": inventory["hidden_prize_count"],
        "deck_count": inventory["deck_count"],
        "normal_capacity": normal_capacity,
        "abra_final_slot_exception": abra_final_slot_exception,
        "zero_demand_reason": zero_demand_reason,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return {
        "sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest().upper(),
        "canonical": canonical,
        "payload": payload,
        "poffin_rows": poffin_rows,
    }, None


def _v4_filtered_parent_rerank(
    parent,
    v0_agent,
    obs_dict,
    obs,
    delegate_pre,
    poffin_rows,
):
    """Run the unchanged C2 parent on a clone with every Poffin PLAY removed."""
    original_post = _delegate_state_snapshot(parent)
    removed_indices = {row["option_index"] for row in poffin_rows}
    if not removed_indices:
        return None, "NO_POFFIN_OPTIONS_TO_FILTER"
    filtered_raw = copy.deepcopy(obs_dict)
    raw_options = filtered_raw.get("select", {}).get("option")
    if not isinstance(raw_options, list) or max(removed_indices) >= len(
        raw_options
    ):
        return None, "RAW_OPTION_FILTER_MISSING"
    filtered_raw["select"]["option"] = [
        option
        for index, option in enumerate(raw_options)
        if index not in removed_indices
    ]
    try:
        _restore_delegate_state(parent, delegate_pre)
        filtered_obs = parent.to_observation_class(filtered_raw)
        if (
            not runtime_model.raw_parsed_agree(filtered_raw, filtered_obs)
            or _option_census(parent, filtered_obs) is None
        ):
            raise ValueError("FILTERED_PARENT_OBSERVATION_NOT_EXACT")
        filtered_action = _require_certified_action(
            filtered_obs, v0_agent(filtered_raw)
        )
        filtered_keys = tuple(
            runtime_model.stable_option_key(
                parent,
                filtered_obs,
                filtered_obs.select.option[index],
            )
            for index in filtered_action
        )
        if any(key is None for key in filtered_keys):
            raise ValueError("FILTERED_PARENT_ACTION_KEY_MISSING")
        rerank_post = _delegate_state_snapshot(parent)
        original_map = {}
        for index, option in enumerate(obs.select.option):
            key = runtime_model.stable_option_key(parent, obs, option)
            original_map.setdefault(key, []).append(index)
        applied_action = []
        for key in filtered_keys:
            matches = original_map.get(key, ())
            if len(matches) != 1:
                raise ValueError("FILTERED_PARENT_ACTION_REBIND_AMBIGUOUS")
            applied_action.append(matches[0])
        if (
            not model.action_is_valid(obs, applied_action)
            or any(index in removed_indices for index in applied_action)
        ):
            raise ValueError("FILTERED_PARENT_ACTION_REBIND_INVALID")
        _restore_delegate_state(parent, rerank_post)
        return applied_action, None
    except Exception as error:
        _restore_delegate_state(parent, original_post)
        return None, f"RERANK_{type(error).__name__}_{error}"


def _v4_consider_poffin_zero_veto(
    parent,
    v0_agent,
    obs_dict,
    obs,
    snap,
    parent_action,
    delegate_pre,
    *,
    source,
):
    """Return a handled action record, or None when Fix8 must not intervene."""
    global POFFIN_ZERO_DEMAND_LATCH
    if (
        V1_TRANSACTION is not None
        or core.INTEGRATED_TRANSACTION is not None
        or core.parent_owner_active(core.parent_state_snapshot(parent))
    ):
        if POFFIN_ZERO_DEMAND_LATCH is not None:
            _v4_poffin_zero_trace(
                "HOLD",
                "ACTIVE_TRANSACTION_PRECEDENCE",
                eligibility=POFFIN_ZERO_DEMAND_LATCH,
                parent_action=parent_action,
                applied_action=parent_action,
                source=source,
            )
        return None
    if (
        obs.select is None
        or obs.select.context != parent.SelectContext.MAIN
        or int(obs.select.type) != 0
    ):
        if POFFIN_ZERO_DEMAND_LATCH is not None:
            _v4_poffin_zero_trace(
                "HOLD",
                "NON_MAIN_CALLBACK",
                eligibility=POFFIN_ZERO_DEMAND_LATCH,
                parent_action=parent_action,
                applied_action=parent_action,
                source=source,
            )
        return None
    eligibility, certificate_reason = _v4_poffin_zero_eligibility(
        parent, obs, obs_dict
    )
    if eligibility is None:
        if POFFIN_ZERO_DEMAND_LATCH is not None:
            _v4_clear_poffin_zero_latch(
                certificate_reason, source=source
            )
        return None
    prior_latch = POFFIN_ZERO_DEMAND_LATCH
    if (
        prior_latch is not None
        and prior_latch.get("sha256") != eligibility["sha256"]
    ):
        _v4_clear_poffin_zero_latch(
            "ELIGIBILITY_CHANGED", source=source
        )
        prior_latch = None
    selected_poffin = _v4_selected_poffin_row(
        parent, obs, parent_action, eligibility["poffin_rows"]
    )
    if selected_poffin is None:
        if POFFIN_ZERO_DEMAND_LATCH is not None:
            POFFIN_ZERO_DEMAND_LATCH["last_action_count"] = (
                obs.current.turnActionCount
            )
            _v4_poffin_zero_trace(
                "HOLD",
                "PARENT_SELECTED_NON_POFFIN",
                eligibility=POFFIN_ZERO_DEMAND_LATCH,
                parent_action=parent_action,
                applied_action=parent_action,
                source=source,
            )
        return None
    zero_reason = eligibility["payload"]["zero_demand_reason"]
    if zero_reason is None:
        if POFFIN_ZERO_DEMAND_LATCH is not None:
            _v4_clear_poffin_zero_latch(
                "POSITIVE_PUBLIC_DEMAND", source=source
            )
        return None
    stage = "HOLD" if prior_latch is not None else "ARM"
    eligibility.update(
        owner=obs.current.yourIndex,
        turn=obs.current.turn,
        last_action_count=obs.current.turnActionCount,
    )
    POFFIN_ZERO_DEMAND_LATCH = eligibility
    reranked_action, rerank_error = _v4_filtered_parent_rerank(
        parent,
        v0_agent,
        obs_dict,
        obs,
        delegate_pre,
        eligibility["poffin_rows"],
    )
    if reranked_action is None:
        _v4_poffin_zero_trace(
            "FAIL_CLOSED",
            rerank_error,
            eligibility=eligibility,
            parent_action=parent_action,
            proposed_action=None,
            applied_action=parent_action,
            source=source,
        )
        POFFIN_ZERO_DEMAND_LATCH = None
        _trace(
            snap.sha256,
            int(obs.select.context),
            parent_action,
            None,
            "V4_POFFIN_ZERO_VETO_FAIL_CLOSED",
            "V0_FALLBACK",
        )
        return {"action": parent_action, "changed": False}
    _v4_poffin_zero_trace(
        stage,
        zero_reason,
        eligibility=eligibility,
        parent_action=parent_action,
        proposed_action=reranked_action,
        applied_action=reranked_action,
        source=source,
    )
    _trace(
        snap.sha256,
        int(obs.select.context),
        reranked_action,
        RULE_POFFIN_ZERO_DEMAND_VETO,
        f"V4_POFFIN_ZERO_VETO_{stage}",
        zero_reason,
        f"ELIGIBILITY_{eligibility['sha256']}",
    )
    return {"action": reranked_action, "changed": True}


def agent(parent, v0_agent, obs_dict):
    """Own certified v1 transactions before consulting the inherited v0."""
    global V1_TRANSACTION, REMOVED_RULE_HITS
    context, v0_action = None, None
    active_transaction = V1_TRANSACTION
    REMOVED_RULE_HITS = []
    try:
        if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
            _v4_clear_poffin_zero_latch(
                "HANDSHAKE_OR_MISSING_SELECT", source="AGENT_ENTRY"
            )
            raise UnrecoverableObservationFault(
                "V1_OWNED_CALLBACK_MISSING_SELECT"
                if active_transaction is not None
                else "V1_CALLBACK_MISSING_SELECT"
            )
        obs = parent.to_observation_class(obs_dict)
        context = int(obs.select.context)
        _v4_poffin_zero_clock_guard(obs)
        if not runtime_model.raw_parsed_agree(obs_dict, obs):
            _v4_clear_poffin_zero_latch(
                "RAW_PARSED_MISMATCH", source="AGENT_ENTRY"
            )
            if active_transaction is not None:
                fault_action = _irreversible_fault_action(parent, obs)
                failed_rule = active_transaction.get("rule")
                _reset_v1_only()
                _trace(
                    None, context, fault_action, failed_rule,
                    "V1_IRREVERSIBLE_ABORT_FAULT", "RAW_PARSED_MISMATCH",
                )
                return fault_action
            _reset_v1_only()
            v0_action = _require_certified_action(obs, v0_agent(obs_dict))
            _trace(
                None, context, v0_action, None,
                "RAW_PARSED_MISMATCH", "V0_FALLBACK",
            )
            return v0_action
        snap = runtime_model.public_snapshot(parent, obs)
        if snap is None or _option_census(parent, obs) is None:
            _v4_clear_poffin_zero_latch(
                "AMBIGUOUS_PUBLIC_METADATA", source="AGENT_ENTRY"
            )
            if active_transaction is not None:
                fault_action = _irreversible_fault_action(parent, obs)
                failed_rule = active_transaction.get("rule")
                _reset_v1_only()
                _trace(
                    None, context, fault_action, failed_rule,
                    "V1_IRREVERSIBLE_ABORT_FAULT",
                    "AMBIGUOUS_PUBLIC_METADATA",
                )
                return fault_action
            _reset_v1_only()
            v0_action = _require_certified_action(obs, v0_agent(obs_dict))
            _trace(
                None, context, v0_action, None,
                "AMBIGUOUS_PUBLIC_METADATA", "V0_FALLBACK",
            )
            return v0_action
        if (
            V1_TRANSACTION is None
            and snap.sha256 in core.INTEGRATED_DUPLICATE_CACHE
        ):
            v0_action = _require_certified_action(obs, v0_agent(obs_dict))
            optional_draw = _psychic_draw_optional_decision(
                parent, obs, v0_action
            )
            if optional_draw is not None:
                action = optional_draw["action"]
                _trace(
                    snap.sha256,
                    context,
                    action,
                    (
                        RULE_PSYCHIC_DRAW_OPTIONAL
                        if optional_draw["overridden"]
                        else None
                    ),
                    "INHERITED_DUPLICATE_OWNER",
                    *_psychic_draw_trace_tags(optional_draw),
                )
                return action
            _trace(
                snap.sha256, context, v0_action, None,
                "INHERITED_DUPLICATE_OWNER", "V0_FALLBACK",
            )
            return v0_action
        if V1_TRANSACTION is None:
            V1_DUPLICATES.clear()
        duplicate = _rebind_duplicate(parent, obs, snap.sha256)
        if duplicate is not None:
            _trace(
                snap.sha256,
                context,
                duplicate,
                V1_TRANSACTION.get("rule") if V1_TRANSACTION else None,
                "V1_DUPLICATE_REBIND",
            )
            return duplicate

        delegate_pre = _delegate_state_snapshot(parent)
        parent_pre = delegate_pre["parent"]
        inherited_at_entry = (
            core.INTEGRATED_TRANSACTION is not None
            or core.parent_owner_active(parent_pre)
        )
        if V1_TRANSACTION is None and inherited_at_entry:
            had_removed_parent_transaction = _removed_parent_transaction_active()
            v0_action = _require_certified_action(obs, v0_agent(obs_dict))
            removed = _sanitize_removed_owned_action(parent, obs, v0_action)
            removed_parent_transaction = (
                had_removed_parent_transaction
                or _removed_parent_transaction_active()
            )
            if removed_parent_transaction or removed is not None:
                _restore_delegate_state(parent, delegate_pre)
                core.INTEGRATED_TRANSACTION = None
                _reset_v1_only()
                if removed is not None:
                    _record_removed_rule_hits(
                        parent, obs, v0_action, "INHERITED_V0_ACTION"
                    )
                    action, forced = removed
                else:
                    _record_removed_parent_owner(
                        obs, "HANDHELD_FAN_RESPONSE"
                    )
                    action, forced = _lowest_legal_without_removed(parent, obs)
                tags = ["V1_REMOVED_PARENT_TRANSACTION_FILTER"]
                tags.append(
                    "V1_REMOVED_CARD_FORCED_PROMPT_ONLY"
                    if forced
                    else "V1_REMOVED_OWN_CARD_FILTER"
                )
                _trace(snap.sha256, context, action, None, *tags)
                return action
            poffin_zero = _v4_consider_poffin_zero_veto(
                parent,
                v0_agent,
                obs_dict,
                obs,
                snap,
                v0_action,
                delegate_pre,
                source="INHERITED_ENTRY_POST_DELEGATE",
            )
            if poffin_zero is not None:
                return poffin_zero["action"]
            optional_draw = _psychic_draw_optional_decision(
                parent, obs, v0_action
            )
            if optional_draw is not None:
                action = optional_draw["action"]
                _reset_v1_only()
                _trace(
                    snap.sha256,
                    context,
                    action,
                    (
                        RULE_PSYCHIC_DRAW_OPTIONAL
                        if optional_draw["overridden"]
                        else None
                    ),
                    "INHERITED_TRANSACTION_OWNER",
                    "V3_PSYCHIC_DRAW_INHERITED_OWNER_PRESERVED",
                    *_psychic_draw_trace_tags(optional_draw),
                )
                return action
            _reset_v1_only()
            _trace(
                snap.sha256, context, v0_action, None,
                "INHERITED_TRANSACTION_OWNER", "V0_FALLBACK",
            )
            return v0_action

        if V1_TRANSACTION is not None:
            transaction, action, complete = V1_TRANSACTION, None, False
            stage = transaction["stage"]
            if stage == "await_boss_child":
                action = _advance_boss(parent, obs, transaction)
            elif stage == "await_boss_attack":
                action = _advance_boss_attack(parent, obs, transaction)
            elif stage == "await_backup_alakazam_ability":
                action = _advance_backup_alakazam_ability(parent, obs, transaction)
            elif stage == "await_backup_alakazam_attack":
                action = _advance_backup_alakazam_attack(parent, obs, transaction)
            elif stage == "await_mine_attack":
                action = _advance_mine_attack(parent, obs, transaction)
            elif stage == "await_alakazam_ability":
                action = _advance_alakazam_ability(parent, obs, transaction)
            elif stage == "await_alakazam_attack":
                action = _advance_alakazam_attack(parent, obs, transaction)
            elif stage == "await_added_attack_verify":
                if transaction["rule"] in (RULE_BOSS, RULE_BOSS_READY_STOP):
                    complete = _verify_boss_attack_resolution(
                        parent, obs, transaction
                    )
                elif transaction["rule"] == RULE_MINE:
                    complete = _verify_mine_attack_resolution(
                        parent, obs, transaction
                    )
                elif transaction["rule"] in (
                    RULE_ALAKAZAM,
                    RULE_ALAKAZAM_READY_BENCH,
                    RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
                ):
                    complete = _verify_alakazam_attack_resolution(
                        parent, obs, transaction
                    )
            elif stage == "await_lana_child":
                action = _advance_lana(parent, obs, transaction)
            elif stage == "await_hammer_child":
                action = _advance_hammer(parent, obs, transaction)
            elif stage == "await_lana_verify":
                complete = _verify_lana(parent, obs, transaction)
            elif stage == "await_hammer_verify":
                complete = _verify_hammer(parent, obs, transaction)
            elif stage == "await_xerosic_verify":
                complete = _verify_xerosic(parent, obs, transaction)
            if action is not None and model.action_is_valid(obs, action):
                _remember(parent, obs, snap.sha256, action)
                psychic_tags = ()
                if stage in (
                    "await_alakazam_ability",
                    "await_backup_alakazam_ability",
                ):
                    choice = transaction.get("psychic_draw_choice")
                    psychic_tags = (
                        f"V3_PSYCHIC_DRAW_OPTIONAL_{choice}",
                        f"V3_PSYCHIC_DRAW_CARD_{transaction.get('psychic_draw_card_id')}",
                        f"V3_PSYCHIC_DRAW_COUNT_{transaction.get('psychic_draw_count')}",
                        f"V3_PROJECTED_DECK_{transaction.get('psychic_draw_projected_deck')}",
                        "EXACT_PSYCHIC_DRAW_PROMPT",
                        "V3_OWNED_TRANSACTION_NO_DRAW_SAFE"
                        if choice == "NO"
                        else "V3_OWNED_TRANSACTION_DRAW_DELTA",
                    )
                _trace(
                    snap.sha256, context, action, transaction["rule"],
                    "EXACT_CHILD_PROMPT", "SERIAL_REBOUND", *psychic_tags,
                )
                return action
            if complete:
                completed_rule = transaction["rule"]
                _reset_v1_only()
                v0_action = _require_certified_action(obs, v0_agent(obs_dict))
                removed_parent_transaction = _removed_parent_transaction_active()
                removed = _sanitize_removed_owned_action(
                    parent, obs, v0_action
                )
                if removed_parent_transaction:
                    _restore_delegate_state(parent, delegate_pre)
                    core.INTEGRATED_TRANSACTION = None
                    _record_removed_parent_owner(
                        obs, "POST_V1_COMPLETION_HANDHELD_FAN_RESPONSE"
                    )
                    action, forced = _lowest_legal_without_removed(parent, obs)
                    tags = [
                        "V1_TRANSACTION_COMPLETE",
                        "V1_REMOVED_PARENT_TRANSACTION_FILTER",
                    ]
                    tags.append(
                        "V1_REMOVED_CARD_FORCED_PROMPT_ONLY"
                        if forced
                        else "V1_REMOVED_OWN_CARD_FILTER"
                    )
                    _trace(
                        snap.sha256, context, action, completed_rule, *tags
                    )
                    return action
                if removed is not None:
                    _restore_delegate_state(parent, delegate_pre)
                    _record_removed_rule_hits(
                        parent, obs, v0_action,
                        "POST_V1_COMPLETION_V0_ACTION",
                    )
                    action, forced = removed
                    tags = ["V1_TRANSACTION_COMPLETE"]
                    tags.append(
                        "V1_REMOVED_CARD_FORCED_PROMPT_ONLY"
                        if forced
                        else "V1_REMOVED_OWN_CARD_FILTER"
                    )
                    _trace(
                        snap.sha256, context, action, completed_rule, *tags
                    )
                    return action
                poffin_zero = _v4_consider_poffin_zero_veto(
                    parent,
                    v0_agent,
                    obs_dict,
                    obs,
                    snap,
                    v0_action,
                    delegate_pre,
                    source="V1_COMPLETION_POST_DELEGATE",
                )
                if poffin_zero is not None:
                    return poffin_zero["action"]
                _trace(
                    snap.sha256, context, v0_action, completed_rule,
                    "V1_TRANSACTION_COMPLETE",
                )
                return v0_action
            fault_action = _irreversible_fault_action(parent, obs)
            failed_rule = transaction.get("rule")
            failed_stage = transaction.get("stage", stage)
            _reset_v1_only()
            _v4_clear_poffin_zero_latch(
                "V1_TRANSACTION_ABORT", source="V1_OWNED_STAGE"
            )
            legacy_diagnostic = _transaction_abort_tag(transaction)
            predicate_reason = _owned_stage_rejection_reason(
                parent, obs, transaction
            )
            tags = tuple(
                tag for tag in (
                    "V1_IRREVERSIBLE_ABORT_FAULT",
                    legacy_diagnostic,
                    f"V1_OWNED_STAGE_REJECTED_{failed_stage}",
                    f"V1_PREDICATE_{predicate_reason}",
                )
                if tag is not None
            )
            _trace(
                snap.sha256,
                context,
                fault_action,
                failed_rule,
                *tags,
            )
            return fault_action

        had_removed_parent_transaction = _removed_parent_transaction_active()
        v0_action = _require_certified_action(obs, v0_agent(obs_dict))
        parent_post = core.parent_state_snapshot(parent)
        removed = _sanitize_removed_owned_action(parent, obs, v0_action)
        removed_parent_transaction = (
            had_removed_parent_transaction or _removed_parent_transaction_active()
        )
        if removed_parent_transaction or removed is not None:
            _restore_delegate_state(parent, delegate_pre)
            core.INTEGRATED_TRANSACTION = None
            _reset_v1_only()
            if removed is not None:
                _record_removed_rule_hits(
                    parent, obs, v0_action, "INHERITED_V0_ACTION"
                )
                action, forced = removed
            else:
                _record_removed_parent_owner(obs, "HANDHELD_FAN_RESPONSE")
                action, forced = _lowest_legal_without_removed(parent, obs)
            tags = ["V1_REMOVED_PARENT_TRANSACTION_FILTER"]
            tags.append(
                "V1_REMOVED_CARD_FORCED_PROMPT_ONLY"
                if forced
                else "V1_REMOVED_OWN_CARD_FILTER"
            )
            _trace(snap.sha256, context, action, None, *tags)
            return action
        inherited_owner = (
            core.INTEGRATED_TRANSACTION is not None
            or core.parent_owner_active(parent_post)
        )
        if inherited_owner:
            optional_draw = _psychic_draw_optional_decision(
                parent, obs, v0_action
            )
            if optional_draw is not None:
                action = optional_draw["action"]
                _reset_v1_only()
                _trace(
                    snap.sha256,
                    context,
                    action,
                    (
                        RULE_PSYCHIC_DRAW_OPTIONAL
                        if optional_draw["overridden"]
                        else None
                    ),
                    "INHERITED_TRANSACTION_OWNER",
                    "V3_PSYCHIC_DRAW_INHERITED_OWNER_PRESERVED",
                    "V3_PSYCHIC_DRAW_OWNER_ESTABLISHED_BY_DELEGATE",
                    *_psychic_draw_trace_tags(optional_draw),
                )
                return action
            _reset_v1_only()
            _trace(
                snap.sha256, context, v0_action, None,
                "INHERITED_TRANSACTION_OWNER", "V0_FALLBACK",
            )
            return v0_action

        poffin_zero = _v4_consider_poffin_zero_veto(
            parent,
            v0_agent,
            obs_dict,
            obs,
            snap,
            v0_action,
            delegate_pre,
            source="NORMAL_MAIN_POST_DELEGATE",
        )
        if poffin_zero is not None:
            return poffin_zero["action"]

        optional_draw = _psychic_draw_optional_decision(
            parent, obs, v0_action
        )
        if optional_draw is not None:
            action = optional_draw["action"]
            _trace(
                snap.sha256,
                context,
                action,
                (
                    RULE_PSYCHIC_DRAW_OPTIONAL
                    if optional_draw["overridden"]
                    else None
                ),
                *_psychic_draw_trace_tags(optional_draw),
            )
            return action

        public = _main_envelope(parent, obs)
        if public is None:
            _trace(
                snap.sha256, context, v0_action, None,
                "MAIN_ENVELOPE_NOT_EXACT", "V0_FALLBACK",
            )
            return v0_action
        _clear_compliance_block()
        if _v0_current_ko(parent, obs, v0_action):
            if _current_ko_is_terminal(parent, obs):
                _trace(
                    snap.sha256, context, v0_action, None,
                    "CURRENT_EXACT_TERMINAL_KO_PRECEDENCE", "V0_FALLBACK",
                )
                return v0_action
            candidate = (
                _candidate_boss(parent, obs, snap, public)
                or _candidate_boss_ready_stop(parent, obs, snap, public)
                or _candidate_alakazam_ready_bench(parent, obs, snap, public)
            )
            if candidate is None:
                block_tag = _take_compliance_block()
                tags = tuple(
                    tag for tag in (
                        block_tag,
                        "CURRENT_EXACT_KO_PRECEDENCE",
                        "CURRENT_EXACT_NONTERMINAL_KO_PRESERVED",
                        "V0_FALLBACK",
                    )
                    if tag is not None
                )
                _trace(snap.sha256, context, v0_action, None, *tags)
                return v0_action
        else:
            candidate = (
                _candidate_boss(parent, obs, snap, public)
                or _candidate_mine(parent, obs, snap, public)
                or _candidate_alakazam(parent, obs, snap, public)
                or _candidate_alakazam_exact_evolution_ko(
                    parent, obs, snap, public
                )
                or _candidate_xerosic(parent, obs, snap, public)
                or _candidate_lana(parent, obs, snap, public)
                or _candidate_hammer(parent, obs, snap, public)
            )
        if candidate is None:
            tags = (
                ("UNKNOWN_NOT_IMPLEMENTED_FAIL_CLOSED", "V0_FALLBACK")
                if _unknown_present(parent, obs)
                else ("V0_NONFIRE_EXACT", "V0_FALLBACK")
            )
            _trace(snap.sha256, context, v0_action, None, *tags)
            return v0_action
        action, transaction = candidate
        if not model.action_is_valid(obs, action):
            _trace(
                snap.sha256, context, v0_action, None,
                "V1_ACTION_INVALID", "V0_FALLBACK",
            )
            return v0_action
        _restore_delegate_state(parent, delegate_pre)
        V1_TRANSACTION = transaction
        _remember(parent, obs, snap.sha256, action)
        _trace(
            snap.sha256, context, action, transaction["rule"],
            *_candidate_trace_tags(transaction),
        )
        return action
    except UnrecoverableObservationFault as error:
        failed_rule = (
            active_transaction.get("rule")
            if active_transaction is not None
            else None
        )
        _reset_v1_only()
        _v4_clear_poffin_zero_latch(
            f"UNRECOVERABLE_{type(error).__name__}",
            source="AGENT_EXCEPTION",
        )
        tags = ["V1_UNRECOVERABLE_OBSERVATION_FAULT", str(error)]
        if active_transaction is not None:
            tags.insert(0, "V1_IRREVERSIBLE_ABORT_FAULT")
        _trace(None, context, None, failed_rule, *tags)
        raise
    except Exception as error:
        _v4_clear_poffin_zero_latch(
            f"EXCEPTION_{type(error).__name__}",
            source="AGENT_EXCEPTION",
        )
        if active_transaction is not None and v0_action is None:
            try:
                parsed = parent.to_observation_class(obs_dict)
            except Exception:
                parsed = None
            if parsed is not None and parsed.select is not None:
                try:
                    fault_action = _irreversible_fault_action(parent, parsed)
                except Exception:
                    fault_action = _deterministic_legal_action(parsed)
                if not model.action_is_valid(parsed, fault_action):
                    fault_action = _deterministic_legal_action(parsed)
                if fault_action is None:
                    failed_rule = active_transaction.get("rule")
                    failed_stage = active_transaction.get("stage")
                    _reset_v1_only()
                    _trace(
                        None, context, None, failed_rule,
                        "V1_IRREVERSIBLE_ABORT_FAULT",
                        "V1_UNRECOVERABLE_OBSERVATION_FAULT",
                        f"V1_OWNED_STAGE_EXCEPTION_{failed_stage}",
                        "V1_UNRECOVERABLE_ACTION_CERTIFICATION",
                    )
                    raise UnrecoverableObservationFault(
                        "V1_UNRECOVERABLE_ACTION_CERTIFICATION"
                    ) from error
            else:
                fault_action = _certify_raw_action(obs_dict, None)
                failed_rule = active_transaction.get("rule")
                failed_stage = active_transaction.get("stage")
                if fault_action is None:
                    _reset_v1_only()
                    _trace(
                        None, context, None, failed_rule,
                        "V1_IRREVERSIBLE_ABORT_FAULT",
                        "V1_UNRECOVERABLE_OBSERVATION_FAULT",
                        f"V1_OWNED_STAGE_EXCEPTION_{failed_stage}",
                        "V1_UNRECOVERABLE_REPARSE_FAILURE",
                    )
                    raise UnrecoverableObservationFault(
                        "V1_UNRECOVERABLE_REPARSE_FAILURE"
                    ) from error
                _reset_v1_only()
                _trace(
                    None, context, fault_action, failed_rule,
                    "V1_IRREVERSIBLE_ABORT_FAULT",
                    f"V1_OWNED_STAGE_EXCEPTION_{failed_stage}",
                    "V1_RAW_SELECT_STRUCTURAL_CERTIFICATE",
                    f"V1_FAIL_CLOSED_{type(error).__name__}",
                )
                return fault_action
            failed_rule = active_transaction.get("rule")
            failed_stage = active_transaction.get("stage")
            _reset_v1_only()
            _trace(
                None,
                context,
                fault_action,
                failed_rule,
                "V1_IRREVERSIBLE_ABORT_FAULT",
                f"V1_OWNED_STAGE_EXCEPTION_{failed_stage}",
                f"V1_FAIL_CLOSED_{type(error).__name__}",
            )
            return fault_action
        _reset_v1_only()
        if v0_action is None:
            v0_action = v0_agent(obs_dict)
        try:
            parsed = parent.to_observation_class(obs_dict)
        except Exception:
            parsed = None
        if parsed is not None and parsed.select is not None:
            v0_action = _certify_delegate_action(parsed, v0_action)
            if v0_action is None:
                _reset_v1_only()
                _trace(None, context, None, None, "V1_UNRECOVERABLE_OBSERVATION_FAULT", "V1_UNRECOVERABLE_ACTION_CERTIFICATION", f"V1_FAIL_CLOSED_{type(error).__name__}")
                raise UnrecoverableObservationFault(
                    "V1_UNRECOVERABLE_ACTION_CERTIFICATION"
                ) from error
        else:
            v0_action = _certify_raw_action(obs_dict, v0_action)
            if v0_action is None:
                _reset_v1_only()
                _trace(None, context, None, None, "V1_UNRECOVERABLE_OBSERVATION_FAULT", "V1_UNRECOVERABLE_REPARSE_FAILURE", f"V1_FAIL_CLOSED_{type(error).__name__}")
                raise UnrecoverableObservationFault(
                    "V1_UNRECOVERABLE_REPARSE_FAILURE"
                ) from error
            _reset_v1_only()
            _trace(None, context, v0_action, None, "V1_RAW_SELECT_STRUCTURAL_CERTIFICATE", f"V1_FAIL_CLOSED_{type(error).__name__}", "V0_FALLBACK")
            return v0_action
        _trace(
            None, context, v0_action, None,
            f"V1_FAIL_CLOSED_{type(error).__name__}", "V0_FALLBACK",
        )
        return v0_action


# --- Strict remaining v1 corridors: Boss, Mine, and Alakazam evolution. ---

def _target_powerful_hand_ko(parent, obs, target, hand_count):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    if (
        hand_count < 0 or len(mine.active) != 1 or mine.active[0].id != ALAKAZAM
        or not parent._two_prize_powerful_hand_metadata_is_exact()
        or parent.card_table[ALAKAZAM].tera
        or not parent._two_prize_alakazam_is_ready(mine.active[0], owner)
        or mine.asleep or mine.paralyzed or mine.confused
        or not parent._bridge_pokemon_is_publicly_complete(target, 1 - owner)
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, target, 1 - owner
        )
        or hand_count < ceil(target.hp / 20) or _attack_index(parent, obs) is None
    ):
        return False
    protected = parent._bridge_pokemon_component_serials(mine.active[0]) + parent._bridge_pokemon_component_serials(target)
    return parent._bridge_protected_serials_are_unique(obs.current, protected)


def _candidate_boss(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if obs.current.supporterPlayed or len(mine.prize) < 1 or len(theirs.active) != 1:
        return None
    hand_after = mine.handCount - 1
    terminal = []
    for bench_index, target in enumerate(theirs.bench):
        if (
            _target_powerful_hand_ko(parent, obs, target, hand_after)
            and parent.prize_count(target) >= len(mine.prize)
        ):
            terminal.append((target.serial, bench_index, target))
    if len(terminal) != 1:
        return None
    rows = _play_rows(parent, obs, BOSS_ORDERS)
    if not rows:
        return None
    _, _, option_index, card, key = rows[0]
    _, bench_index, target = terminal[0]
    protected = (
        [card.serial]
        + parent._bridge_pokemon_component_serials(mine.active[0])
        + parent._bridge_pokemon_component_serials(theirs.active[0])
        + parent._bridge_pokemon_component_serials(target)
    )
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_BOSS, snap, obs, public, option_index, card, key)
    transaction.update(
        target_serial=target.serial, target_bench_index=bench_index,
        old_active_serial=theirs.active[0].serial, attacker_serial=mine.active[0].serial,
        hand_after=hand_after, protected_serials=tuple(protected),
    )
    return [option_index], transaction


def _advance_boss(parent, obs, transaction):
    select, owner = obs.select, transaction["owner"]
    post_play = _played_delta(parent, obs, transaction)
    census = _child_prompt_envelope(
        parent,
        obs,
        select_type=1,
        context=parent.SelectContext.SWITCH,
        effect=transaction["card_row"],
    )
    if (
        post_play is None
        or obs.current.yourIndex != owner
        or census is None
    ):
        return None
    opponent = obs.current.players[1 - owner]
    matches = []
    for option_index, option in enumerate(select.option):
        if (
            option.type == parent.OptionType.CARD and option.area == parent.AreaType.BENCH
            and option.playerIndex == 1 - owner
            and _exact_option(option, parent.OptionType.CARD, area=parent.AreaType.BENCH, index=option.index, playerIndex=1 - owner)
            and 0 <= option.index < len(opponent.bench)
            and opponent.bench[option.index].serial == transaction["target_serial"]
        ):
            matches.append((option_index, census[option_index]))
    if len(matches) != 1:
        return None
    transaction["stage"] = "await_boss_attack"
    transaction["post_play"] = post_play
    return [matches[0][0]]


def _advance_boss_attack(parent, obs, transaction):
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    current, post = _public_state(parent, obs), transaction["post_play"]
    if (
        current is None or obs.current.yourIndex != owner
        or obs.select.context != parent.SelectContext.MAIN or int(obs.select.type) != 0
        or current["action_count"] != post["action_count"] + 1
        or current["own_hand"] != post["own_hand"]
        or not _same_multiset(
            current["own_discard"],
            post["own_discard"] + (transaction["card_row"],),
        )
        or current["own_deck"] != post["own_deck"] or current["opponent_deck"] != post["opponent_deck"]
        or current["stadium"] != post["stadium"] or sorted(map(repr, current["fields"])) != sorted(map(repr, post["fields"]))
        or len(mine.active) != 1 or mine.active[0].serial != transaction["attacker_serial"]
        or len(theirs.active) != 1 or theirs.active[0].serial != transaction["target_serial"]
        or sum(pokemon.serial == transaction["old_active_serial"] for pokemon in theirs.bench) != 1
        or mine.handCount != transaction["hand_after"]
        or not _powerful_hand_ko(parent, obs, mine.handCount)
    ):
        return None
    return _arm_attack_resolution(parent, obs, transaction)


def _cost_environment_clear(parent, state, *, allow_mine=False):
    if len(state.stadium) > 1:
        return False
    for card in state.stadium:
        data = parent.card_table.get(card.id)
        if data is None or data.cardType != parent.CardType.STADIUM:
            return False
        if allow_mine and card.id == NIGHTTIME_MINE and _metadata_exact(parent, NIGHTTIME_MINE):
            continue
        if any("cost" in parent._normalized_skill_text(skill.text) for skill in (data.skills or ())):
            return False
    return True


def _mine_stop(parent, obs, *, allow_mine=False):
    owner = obs.current.yourIndex
    theirs = obs.current.players[1 - owner]
    if len(theirs.active) != 1 or not _cost_environment_clear(parent, obs.current, allow_mine=allow_mine):
        return None
    target = theirs.active[0]
    data = parent.card_table.get(target.id)
    units = semantics.energy_units(parent, target)
    if (
        data is None or not data.tera or units is None
        or not parent._bridge_pokemon_is_publicly_complete(target, 1 - owner)
        or any("cost" in parent._normalized_skill_text(skill.text) for skill in (data.skills or ()))
    ):
        return None
    ready = []
    for attack_id in data.attacks or ():
        attack = parent.attack_table.get(attack_id)
        if attack is None or attack.attackId != attack_id:
            return None
        if not semantics.missing_energy(parent, units, attack.energies):
            ready.append((attack_id, attack))
    if len(ready) != 1:
        return None
    attack_id, attack = ready[0]
    with_mine = tuple(attack.energies or ()) + (parent.EnergyType.COLORLESS,)
    if not semantics.missing_energy(parent, units, with_mine):
        return None
    return target, attack_id


def _candidate_mine(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if obs.current.stadiumPlayed or len(theirs.active) != 1 or not _powerful_hand_ko(parent, obs, mine.handCount - 1):
        return None
    stopped = _mine_stop(parent, obs)
    rows = _play_rows(parent, obs, NIGHTTIME_MINE)
    if stopped is None or not rows:
        return None
    _, _, option_index, card, key = rows[0]
    target, attack_id = stopped
    protected = [card.serial] + parent._bridge_pokemon_component_serials(mine.active[0]) + parent._bridge_pokemon_component_serials(target)
    protected += [row[1] for row in public["stadium"]]
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_MINE, snap, obs, public, option_index, card, key)
    transaction.update(
        stopped_serial=target.serial, stopped_attack_id=attack_id,
        attacker_serial=mine.active[0].serial, target_serial=theirs.active[0].serial,
        hand_after=mine.handCount - 1, protected_serials=tuple(protected),
    )
    return [option_index], transaction


def _mine_played_delta(parent, obs, transaction):
    current, start = _public_state(parent, obs), transaction["start"]
    expected_hand = _remove_serial(start["own_hand"], transaction["card_serial"])
    if current is None or expected_hand is None:
        return None
    expected_own_discard, expected_opponent_discard = start["own_discard"], start["opponent_discard"]
    for prior in start["stadium"]:
        if prior[2] == transaction["owner"]:
            expected_own_discard += (prior,)
        else:
            expected_opponent_discard += (prior,)
    if (
        current["turn"] != start["turn"] or current["result"] != start["result"]
        or current["action_count"] != start["action_count"] + 1
        or current["own_hand"] != expected_hand or current["own_hand_count"] != start["own_hand_count"] - 1
        or current["own_discard"] != expected_own_discard or current["opponent_discard"] != expected_opponent_discard
        or current["stadium"] != (transaction["card_row"],) or not current["stadium_played"]
        or current["supporter_played"] != start["supporter_played"]
        or current["energy_attached"] != start["energy_attached"] or current["retreated"] != start["retreated"]
        or current["own_deck"] != start["own_deck"] or current["opponent_deck"] != start["opponent_deck"]
        or current["fields"] != start["fields"]
    ):
        return None
    return current


def _advance_mine_attack(parent, obs, transaction):
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    stopped = _mine_stop(parent, obs, allow_mine=True)
    if (
        _mine_played_delta(parent, obs, transaction) is None
        or obs.select.context != parent.SelectContext.MAIN or int(obs.select.type) != 0
        or len(mine.active) != 1 or mine.active[0].serial != transaction["attacker_serial"]
        or len(theirs.active) != 1 or theirs.active[0].serial != transaction["target_serial"]
        or stopped is None or stopped[0].serial != transaction["stopped_serial"] or stopped[1] != transaction["stopped_attack_id"]
        or mine.handCount != transaction["hand_after"] or not _powerful_hand_ko(parent, obs, mine.handCount)
    ):
        return None
    return _arm_attack_resolution(parent, obs, transaction)


def _evolve_rows(parent, obs):
    owner, mine = obs.current.yourIndex, obs.current.players[obs.current.yourIndex]
    all_evolves = [(index, option) for index, option in enumerate(obs.select.option) if option.type == parent.OptionType.EVOLVE]
    if len(all_evolves) != 1:
        return None
    option_index, option = all_evolves[0]
    card, target = core._option_card(parent, obs, option), core._target_pokemon(parent, obs, option)
    if (
        card is None or card.id != ALAKAZAM or _card_row(card) != (ALAKAZAM, card.serial, owner)
        or target is None or target.id != parent.Kadabra
        or option.area != parent.AreaType.HAND or option.inPlayArea != parent.AreaType.ACTIVE or option.inPlayIndex != 0
        or not _exact_option(option, parent.OptionType.EVOLVE, area=parent.AreaType.HAND, index=option.index, inPlayArea=parent.AreaType.ACTIVE, inPlayIndex=0)
        or not 0 <= option.index < len(mine.hand) or mine.hand[option.index].serial != card.serial
    ):
        return None
    key = runtime_model.stable_option_key(parent, obs, option)
    return None if key is None else (option_index, card, target, key)


def _candidate_alakazam(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    row = _evolve_rows(parent, obs)
    if row is None or len(mine.active) != 1 or len(theirs.active) != 1 or mine.deckCount < 4:
        return None
    option_index, card, kadabra, key = row
    units = semantics.energy_units(parent, kadabra)
    attack = parent.attack_table.get(POWERFUL_HAND)
    target = theirs.active[0]
    if (
        kadabra.serial != mine.active[0].serial or kadabra.appearThisTurn or kadabra.tools
        or not parent._two_prize_lineage_is_complete(kadabra, owner)
        or tuple(item.id for item in kadabra.preEvolution) != (parent.Abra,)
        or units is None or attack is None or semantics.missing_energy(parent, units, attack.energies)
        or not parent._two_prize_powerful_hand_metadata_is_exact() or parent.card_table[ALAKAZAM].tera
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, target, 1 - owner
        )
        or mine.handCount + 2 < ceil(target.hp / 20)
    ):
        return None
    protected = [card.serial] + parent._bridge_pokemon_component_serials(kadabra) + parent._bridge_pokemon_component_serials(target)
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_ALAKAZAM, snap, obs, public, option_index, card, key)
    transaction.update(
        kadabra_serial=kadabra.serial, attacker_serial=card.serial, target_serial=target.serial,
        start_deck=mine.deckCount, hand_after_draw=mine.handCount + 2,
        own_bench=tuple(parent._bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench),
        opponent_fields=tuple(parent._bridge_pokemon_fingerprint(pokemon) for pokemon in list(theirs.active) + list(theirs.bench)),
        protected_serials=tuple(protected),
    )
    return [option_index], transaction


def _advance_alakazam_ability(parent, obs, transaction):
    select, owner = obs.select, transaction["owner"]
    state, start = _public_state(parent, obs), transaction["start"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    expected_hand = _remove_serial(start["own_hand"], transaction["card_serial"])
    if (
        state is None or expected_hand is None or obs.current.yourIndex != owner
        or select.context != parent.SelectContext.ACTIVATE or int(select.type) != 9
        or select.minCount != 1 or select.maxCount != 1 or select.effect is not None
        or _card_row(select.contextCard) != transaction["card_row"]
        or state["turn"] != start["turn"] or state["action_count"] != start["action_count"] + 1
        or state["own_hand"] != expected_hand or state["own_discard"] != start["own_discard"]
        or state["own_deck"] != start["own_deck"] or state["opponent_deck"] != start["opponent_deck"]
        or state["supporter_played"] != start["supporter_played"] or state["stadium"] != start["stadium"]
        or tuple(parent._bridge_pokemon_fingerprint(pokemon) for pokemon in mine.bench) != transaction["own_bench"]
        or tuple(parent._bridge_pokemon_fingerprint(pokemon) for pokemon in list(theirs.active) + list(theirs.bench)) != transaction["opponent_fields"]
        or len(mine.active) != 1 or mine.active[0].id != ALAKAZAM or mine.active[0].serial != transaction["attacker_serial"]
        or tuple(card.id for card in mine.active[0].preEvolution) != (parent.Abra, parent.Kadabra)
        or transaction["kadabra_serial"] not in {card.serial for card in mine.active[0].preEvolution}
        or not parent._two_prize_alakazam_is_ready(mine.active[0], owner)
        or len(theirs.active) != 1 or theirs.active[0].serial != transaction["target_serial"]
    ):
        return None
    if (
        transaction["rule"] == RULE_ALAKAZAM_EXACT_EVOLUTION_KO
        and not _exact_evolution_ko_evolution_delta(
            state, start, transaction
        )
    ):
        return None
    prompt = _psychic_draw_prompt(parent, obs)
    decision = _psychic_draw_optional_decision(
        parent,
        obs,
        [prompt["yes_index"]] if prompt is not None else None,
    )
    if decision is None or decision["card_id"] != ALAKAZAM:
        return None
    if transaction["rule"] == RULE_ALAKAZAM_EXACT_EVOLUTION_KO:
        planned_choice = transaction.get("planned_psychic_draw_choice")
        actual_choice = "NO" if decision["overridden"] else "YES"
        if actual_choice != planned_choice:
            return None
    transaction["stage"] = "await_alakazam_attack"
    transaction["post_evolve"] = state
    _record_owned_psychic_draw_choice(transaction, state, decision)
    return decision["action"]


def _advance_alakazam_attack(parent, obs, transaction):
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    current, post = _public_state(parent, obs), transaction["post_evolve"]
    if (
        current is None or obs.select.context != parent.SelectContext.MAIN or int(obs.select.type) != 0
        or current["action_count"] != post["action_count"] + 1
        or not _psychic_draw_post_prompt_delta(current, post, transaction)
        or current["own_discard"] != post["own_discard"] or current["opponent_discard"] != post["opponent_discard"]
        or current["stadium"] != post["stadium"] or current["fields"] != post["fields"]
        or len(mine.active) != 1 or mine.active[0].serial != transaction["attacker_serial"]
        or len(theirs.active) != 1 or theirs.active[0].serial != transaction["target_serial"]
        or (
            transaction["rule"] == RULE_ALAKAZAM_EXACT_EVOLUTION_KO
            and (
                not _exact_evolution_ko_post_draw_delta(
                    current, post, transaction
                )
                or
                current["own_hand_count"]
                != transaction.get("planned_post_hand")
                or current["own_deck"]
                != transaction.get("planned_post_deck")
                or parent.prize_count(theirs.active[0])
                != transaction.get("target_prizes")
            )
        )
        or not _powerful_hand_ko(parent, obs, mine.handCount)
    ):
        return None
    return _arm_attack_resolution(parent, obs, transaction)





# --- V1 compliance patch overrides ---

COMPLIANCE_BLOCK_TAG = None


def _clear_compliance_block():
    global COMPLIANCE_BLOCK_TAG
    COMPLIANCE_BLOCK_TAG = None


def _set_compliance_block(tag):
    global COMPLIANCE_BLOCK_TAG
    if COMPLIANCE_BLOCK_TAG is None:
        COMPLIANCE_BLOCK_TAG = tag


def _take_compliance_block():
    global COMPLIANCE_BLOCK_TAG
    tag = COMPLIANCE_BLOCK_TAG
    COMPLIANCE_BLOCK_TAG = None
    return tag


def _transaction_abort_tag(transaction):
    if transaction.get("rule") == RULE_BOSS_READY_STOP:
        return "V1_BOSS_PUBLIC_MUTATION_ABORT"
    if transaction.get("rule") == RULE_ALAKAZAM_READY_BENCH:
        return "V1_ALAKAZAM_PUBLIC_MUTATION_ABORT"
    if transaction.get("rule") == RULE_ALAKAZAM_EXACT_EVOLUTION_KO:
        return "V3_ALAKAZAM_EXACT_EVOLUTION_KO_PUBLIC_MUTATION_ABORT"
    return None


def _candidate_trace_tags(transaction):
    rule = transaction.get("rule")
    if rule == RULE_BOSS_READY_STOP:
        return ("V1_BOSS_UNIQUE_READY_ATTACKER_STOP", "EXACT_PUBLIC_PROOF", "H_FLOOR_CERTIFIED")
    if rule == RULE_ALAKAZAM_READY_BENCH:
        return ("V1_ALAKAZAM_4TH_READY_BENCH", "V1_ALAKAZAM_4TH_PUBLICLY_PROVEN", "EXACT_PUBLIC_PROOF", "H_FLOOR_CERTIFIED")
    if rule == RULE_ALAKAZAM:
        return (transaction.get("identity_reason", "UNKNOWN_IDENTICAL_CARD_ID"), "EXACT_PUBLIC_PROOF", "H_FLOOR_CERTIFIED")
    if rule == RULE_ALAKAZAM_EXACT_EVOLUTION_KO:
        return (
            RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
            "V3_ALL_EVOLVE_ROWS_EXACTLY_RESOLVED",
            "V3_UNRELATED_EVOLUTIONS_DISJOINT",
            f"V3_PSYCHIC_DRAW_PLANNED_{transaction['planned_psychic_draw_choice']}",
            transaction.get(
                "identity_reason", "UNKNOWN_IDENTICAL_CARD_ID"
            ),
            "EXACT_PUBLIC_PROOF",
            "H_FLOOR_CERTIFIED",
        )
    return ("EXACT_PUBLIC_PROOF", "H_FLOOR_CERTIFIED")


def _owned_removed_option(parent, obs, option):
    owner = obs.current.yourIndex
    if option.type not in (
        parent.OptionType.PLAY,
        parent.OptionType.ATTACH,
        parent.OptionType.EVOLVE,
        parent.OptionType.CARD,
        parent.OptionType.ABILITY,
    ):
        return None
    card = core._option_card(parent, obs, option)
    row = _card_row(card)
    if row is None or row[2] != owner or row[0] not in REMOVED_OWN_CARD_IDS:
        return None
    if option.type == parent.OptionType.CARD and option.playerIndex not in (None, owner):
        return None
    return row


def _removed_parent_transaction_active():
    transaction = core.INTEGRATED_TRANSACTION
    if not isinstance(transaction, dict):
        return False
    kind = transaction.get("kind")
    plan = transaction.get("plan")
    if kind is None and plan is not None:
        kind = dict(getattr(plan, "metadata", ()) or ()).get("kind")
    return kind == "HANDHELD_FAN_RESPONSE"


def _lowest_legal_without_removed(parent, obs):
    if _option_census(parent, obs) is None:
        raise ValueError("ambiguous option census")

    def key(index):
        row = _card_row(core._option_card(parent, obs, obs.select.option[index]))
        return (0, row[1], index) if row is not None and type(row[1]) is int else (1, index, index)

    allowed = sorted(
        (index for index, option in enumerate(obs.select.option) if _owned_removed_option(parent, obs, option) is None),
        key=key,
    )
    denied = sorted(
        (index for index, option in enumerate(obs.select.option) if _owned_removed_option(parent, obs, option) is not None),
        key=key,
    )
    minimum = int(obs.select.minCount)
    chosen = allowed[:minimum]
    forced = len(chosen) < minimum
    if forced:
        chosen += denied[: minimum - len(chosen)]
    if not model.action_is_valid(obs, chosen):
        raise ValueError("no deterministic legal action after removed-card gate")
    return chosen, forced

def _sanitize_removed_owned_action(parent, obs, action):
    if not isinstance(action, (list, tuple)) or not action:
        return None
    if any(type(index) is not int or not 0 <= index < len(obs.select.option) for index in action):
        return None
    if not any(_owned_removed_option(parent, obs, obs.select.option[index]) is not None for index in action):
        return None
    if _option_census(parent, obs) is None:
        return None

    def key(index):
        row = _card_row(core._option_card(parent, obs, obs.select.option[index]))
        return (0, row[1], index) if row is not None and type(row[1]) is int else (1, index, index)

    allowed = sorted(
        (index for index, option in enumerate(obs.select.option) if _owned_removed_option(parent, obs, option) is None),
        key=key,
    )
    denied = sorted(
        (index for index, option in enumerate(obs.select.option) if _owned_removed_option(parent, obs, option) is not None),
        key=key,
    )
    minimum = int(obs.select.minCount)
    maximum = int(obs.select.maxCount)
    wanted = max(minimum, min(len(action), maximum))
    chosen = allowed[:wanted]
    forced = len(chosen) < wanted
    if forced:
        chosen += denied[: wanted - len(chosen)]
    if len(chosen) < minimum or len(chosen) > maximum or not model.action_is_valid(obs, chosen):
        return None
    return chosen, forced


def _current_ko_is_terminal(parent, obs):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    return bool(
        len(mine.prize) >= 1
        and len(theirs.active) == 1
        and parent.prize_count(theirs.active[0]) >= len(mine.prize)
    )


def _attack_access_effect_clear(parent, data):
    for skill in data.skills or ():
        if not isinstance(skill.text, str):
            return False
        text = parent._normalized_skill_text(skill.text)
        compact = text.replace("'", "")
        if "cost" in text:
            return False
        if "attack" in text and any(
            marker in compact
            for marker in (
                "cant attack",
                "cannot attack",
                "cant use",
                "cannot use",
                "unable to attack",
                "prevent this pokemon from attacking",
                "prevents this pokemon from attacking",
                "attacks cannot be used",
            )
        ):
            return False
    return True


def _ready_cost_environment_exact(parent, state):
    if not _cost_environment_clear(parent, state):
        return False
    for stadium in state.stadium:
        data = parent.card_table.get(stadium.id)
        if data is None or data.cardId != stadium.id or not _attack_access_effect_clear(parent, data):
            return False
    for owner, player in enumerate(state.players):
        for pokemon in list(player.active) + list(player.bench):
            data = parent.card_table.get(pokemon.id)
            if (
                data is None
                or data.cardId != pokemon.id
                or not parent._bridge_pokemon_is_publicly_complete(pokemon, owner)
                or not _attack_access_effect_clear(parent, data)
            ):
                return False
            for tool in pokemon.tools:
                tool_data = parent.card_table.get(tool.id)
                if (
                    tool_data is None
                    or tool_data.cardId != tool.id
                    or not _attack_access_effect_clear(parent, tool_data)
                ):
                    return False
            for energy in pokemon.energyCards:
                energy_data = parent.card_table.get(energy.id)
                if (
                    energy_data is None
                    or energy_data.cardId != energy.id
                    or energy_data.skills
                ):
                    return False
    return True

def _compliance_ready_attacks(parent, state, pokemon, owner):
    data = parent.card_table.get(pokemon.id)
    units = semantics.energy_units(parent, pokemon)
    player = state.players[owner]
    active_status_blocks = (
        any(active.serial == pokemon.serial for active in player.active)
        and (player.asleep or player.paralyzed or player.confused)
    )
    if (
        active_status_blocks
        or
        data is None
        or data.cardId != pokemon.id
        or units is None
        or not _ready_cost_environment_exact(parent, state)
        or not parent._bridge_pokemon_is_publicly_complete(pokemon, owner)
    ):
        return None
    ready = []
    for attack_id in data.attacks or ():
        attack = parent.attack_table.get(attack_id)
        if (
            attack is None
            or attack.attackId != attack_id
            or not isinstance(attack.name, str)
            or not isinstance(attack.text, str)
            or attack.text != ""
            or type(attack.damage) is not int
            or not isinstance(attack.energies, list)
        ):
            return None
        if not semantics.missing_energy(parent, units, attack.energies):
            ready.append(attack_id)
    return tuple(ready)


def _opponent_ready_set(parent, obs):
    owner = obs.current.yourIndex
    opponent = obs.current.players[1 - owner]
    ready = []
    for area, group in ((parent.AreaType.ACTIVE, opponent.active), (parent.AreaType.BENCH, opponent.bench)):
        for index, pokemon in enumerate(group):
            attacks = _compliance_ready_attacks(parent, obs.current, pokemon, 1 - owner)
            if attacks is None:
                return None
            if attacks:
                ready.append((area, index, pokemon.serial, attacks))
    return tuple(ready)


_ORIGINAL_CANDIDATE_BOSS = _candidate_boss
_ORIGINAL_ADVANCE_BOSS_ATTACK = _advance_boss_attack
_ORIGINAL_CANDIDATE_ALAKAZAM = _candidate_alakazam


def _candidate_boss(parent, obs, snap, public):
    candidate = _ORIGINAL_CANDIDATE_BOSS(parent, obs, snap, public)
    if candidate is not None:
        candidate[1]["mode"] = "TERMINAL_PRIZE_KO"
    return candidate


def _candidate_boss_ready_stop(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    if (
        obs.current.supporterPlayed
        or len(mine.prize) < 1
        or len(theirs.active) != 1
        or not _powerful_hand_ko(parent, obs, mine.handCount)
        or _current_ko_is_terminal(parent, obs)
    ):
        return None
    rows = _play_rows(parent, obs, BOSS_ORDERS)
    if rows is None or len(rows) != 1:
        return None
    ready = _opponent_ready_set(parent, obs)
    if ready is None or len(ready) != 1 or ready[0][0] != parent.AreaType.BENCH:
        _set_compliance_block("V1_BOSS_READY_SET_AMBIGUOUS")
        return None
    _, bench_index, target_serial, _ = ready[0]
    if not 0 <= bench_index < len(theirs.bench):
        return None
    target = theirs.bench[bench_index]
    hand_after = mine.handCount - 1
    if target.serial != target_serial or parent.prize_count(target) >= len(mine.prize):
        return None
    if not _target_powerful_hand_ko(parent, obs, target, hand_after):
        if hand_after < ceil(target.hp / 20):
            _set_compliance_block("V1_BOSS_H_MINUS_1_FLOOR_BLOCK")
        return None
    _, _, option_index, card, key = rows[0]

    protected = (
        [card.serial]
        + parent._bridge_pokemon_component_serials(mine.active[0])
        + parent._bridge_pokemon_component_serials(theirs.active[0])
        + parent._bridge_pokemon_component_serials(target)
    )
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_BOSS, snap, obs, public, option_index, card, key)
    transaction.update(
        rule=RULE_BOSS_READY_STOP,
        mode="UNIQUE_READY_ATTACKER_STOP",
        target_serial=target.serial,
        target_bench_index=bench_index,
        old_active_serial=theirs.active[0].serial,
        attacker_serial=mine.active[0].serial,
        hand_after=hand_after,
        protected_serials=tuple(protected),
        ready_proof=ready,
    )
    return [option_index], transaction


def _advance_boss_attack(parent, obs, transaction):
    current = _public_state(parent, obs)
    post = transaction.get("post_play")
    if (
        current is None
        or post is None
        or _child_prompt_envelope(
            parent,
            obs,
            select_type=0,
            context=parent.SelectContext.MAIN,
        ) is None
        or not _boss_resolved_public_delta_is_exact(
            current, post, transaction
        )
    ):
        return None
    if transaction.get("mode") != "UNIQUE_READY_ATTACKER_STOP":
        return _ORIGINAL_ADVANCE_BOSS_ATTACK(parent, obs, transaction)
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    ready = _opponent_ready_set(parent, obs)
    if (
        obs.current.yourIndex != owner
        or current["turn"] != post["turn"]
        or current["result"] != post["result"]
        or current["action_count"] != post["action_count"] + 1
        or current["supporter_played"] != post["supporter_played"]
        or current["stadium_played"] != post["stadium_played"]
        or current["energy_attached"] != post["energy_attached"]
        or current["retreated"] != post["retreated"]
        or current["own_hand_count"] != post["own_hand_count"]
        or current["opponent_hand_count"] != post["opponent_hand_count"]
        or current["own_hand"] != post["own_hand"]
        or not _same_multiset(
            current["own_discard"],
            post["own_discard"] + (transaction["card_row"],),
        )
        or current["opponent_discard"] != post["opponent_discard"]
        or current["own_deck"] != post["own_deck"]
        or current["opponent_deck"] != post["opponent_deck"]
        or current["stadium"] != post["stadium"]
        or len(mine.active) != 1
        or mine.active[0].serial != transaction["attacker_serial"]
        or len(theirs.active) != 1
        or theirs.active[0].serial != transaction["target_serial"]
        or sum(pokemon.serial == transaction["old_active_serial"] for pokemon in theirs.bench) != 1
        or mine.handCount != transaction["hand_after"]
        or not _powerful_hand_ko(parent, obs, mine.handCount)
        or ready is None
        or len(ready) != 1
        or ready[0][0] != parent.AreaType.ACTIVE
        or ready[0][2] != transaction["target_serial"]
    ):
        return None
    return _arm_attack_resolution(parent, obs, transaction)

def _public_other_alakazam_serials(parent, obs, excluded_serial):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    serials = []
    for card in mine.discard:
        if card.id == ALAKAZAM and _card_row(card) == (ALAKAZAM, card.serial, owner):
            serials.append(card.serial)
    for pokemon in list(mine.active) + list(mine.bench):
        if pokemon.id == ALAKAZAM and type(pokemon.serial) is int and pokemon.serial > 0:
            serials.append(pokemon.serial)
        for card in pokemon.preEvolution:
            if card.id == ALAKAZAM and _card_row(card) == (ALAKAZAM, card.serial, owner):
                serials.append(card.serial)
    if (
        len(getattr(parent, "my_deck", ())) != 60
        or tuple(getattr(parent, "my_deck", ())).count(ALAKAZAM) != EXACT_DECK_ALAKAZAM_COUNT
        or excluded_serial in serials
        or len(serials) != 3
        or len(set(serials)) != 3
    ):
        return None
    return tuple(sorted(serials))


def _candidate_alakazam(parent, obs, snap, public):
    candidate = _ORIGINAL_CANDIDATE_ALAKAZAM(parent, obs, snap, public)
    if candidate is not None:
        transaction = candidate[1]
        proof = _public_other_alakazam_serials(parent, obs, transaction["card_serial"])
        transaction["identity_reason"] = (
            "V1_ALAKAZAM_4TH_PUBLICLY_PROVEN" if proof is not None else "UNKNOWN_IDENTICAL_CARD_ID"
        )
        transaction["public_other_alakazam_serials"] = proof or ()
    return candidate


def _exact_evolution_ko_evolution_delta(current, start, transaction):
    unchanged = (
        "turn",
        "first_player",
        "result",
        "supporter_played",
        "stadium_played",
        "energy_attached",
        "retreated",
        "own_deck",
        "opponent_deck",
        "own_bench_max",
        "opponent_bench_max",
        "own_status",
        "opponent_status",
        "own_prize",
        "opponent_prize",
        "opponent_hand_count",
        "own_discard",
        "opponent_discard",
        "stadium",
        "own_bench",
        "opponent_active",
        "opponent_bench",
    )
    expected_hand = _remove_serial(
        start["own_hand"], transaction["card_serial"]
    )
    return bool(
        expected_hand is not None
        and _public_keys_equal(current, start, unchanged)
        and current["action_count"] == start["action_count"] + 1
        and current["own_hand_count"] == start["own_hand_count"] - 1
        and current["own_hand"] == expected_hand
        and start["own_active"]
        == (transaction.get("kadabra_fingerprint"),)
        and current["own_active"]
        == (transaction.get("expected_active_after_evolve"),)
    )


def _exact_evolution_ko_post_draw_delta(current, post, transaction):
    unchanged = (
        "turn",
        "first_player",
        "result",
        "supporter_played",
        "stadium_played",
        "energy_attached",
        "retreated",
        "opponent_deck",
        "own_bench_max",
        "opponent_bench_max",
        "own_status",
        "opponent_status",
        "own_prize",
        "opponent_prize",
        "opponent_hand_count",
        "own_discard",
        "opponent_discard",
        "stadium",
        "fields",
    )
    return bool(
        _public_keys_equal(current, post, unchanged)
        and current["action_count"] == post["action_count"] + 1
        and _psychic_draw_post_prompt_delta(current, post, transaction)
        and current["own_hand_count"]
        == transaction.get("planned_post_hand")
        and current["own_deck"]
        == transaction.get("planned_post_deck")
    )


def _exact_evolution_ko_prize_value(parent, target, target_owner):
    if not parent._bridge_pokemon_is_publicly_complete(
        target, target_owner
    ):
        return None
    data = parent.card_table.get(target.id)
    if (
        data is None
        or data.cardId != target.id
        or type(data.ex) is not bool
        or type(data.megaEx) is not bool
        or (data.ex and data.megaEx)
    ):
        return None
    expected = 3 if data.megaEx else 2 if data.ex else 1
    for card in list(target.energyCards) + list(target.tools):
        attached = parent.card_table.get(card.id)
        if attached is None or attached.cardId != card.id:
            return None
        for skill in attached.skills or ():
            text = parent._normalized_skill_text(skill.text)
            if "prize" not in text:
                continue
            if (
                card.id == 1172
                and attached.name == "Lillie’s Pearl"
                and skill.name == "Lillie’s Pearl"
                and skill.text
                == (
                    "If the Lillie’s Pokémon this card is attached to is "
                    "Knocked Out by damage from an attack from your "
                    "opponent’s Pokémon, that player takes 1 fewer Prize "
                    "card."
                )
                and "Lillie" in data.name
            ):
                expected -= 1
                continue
            return None
    expected = max(0, expected)
    actual = parent.prize_count(target)
    return (
        expected
        if type(actual) is int and actual == expected and expected >= 1
        else None
    )


def _exact_evolution_ko_public_effects_clear(
    parent, obs, target, target_owner
):
    state = obs.current
    harmless = {
        140: (
            "Flip the Script",
            "Once during your turn, if any of your Pokémon were Knocked "
            "Out during your opponent’s last turn, you may draw 3 cards. "
            "You can’t use more than 1 Flip the Script Ability each turn.",
        ),
        343: (
            " Flower Curtain",
            "Prevent all damage done to your Benched Pokémon that don’t "
            "have a Rule Box by attacks from your opponent’s Pokémon. "
            "(Pokémon {ex}, Pokémon {V}, etc. have Rule Boxes.)",
        ),
    }
    for field_owner, player in enumerate(state.players):
        for pokemon in list(player.active) + list(player.bench):
            data = parent.card_table.get(pokemon.id)
            if (
                data is None
                or data.cardId != pokemon.id
                or not parent._bridge_pokemon_is_publicly_complete(
                    pokemon, field_owner
                )
            ):
                return False
            for skill in data.skills or ():
                if pokemon.id in (KADABRA, ALAKAZAM):
                    if _psychic_draw_metadata_exact(parent, pokemon.id):
                        continue
                    return False
                if harmless.get(pokemon.id) == (skill.name, skill.text):
                    continue
                if (
                    pokemon.id == TEAM_ROCKETS_ARTICUNO
                    and skill.name == " Repelling Veil"
                    and skill.text == REPELLING_VEIL_TEXT
                    and _repelling_veil_state(
                        parent, state, target, target_owner
                    )
                    is False
                ):
                    continue
                return False
            for attached_card in list(pokemon.energyCards) + list(
                pokemon.tools
            ):
                attached = parent.card_table.get(attached_card.id)
                if (
                    attached is None
                    or attached.cardId != attached_card.id
                    or attached.skills
                ):
                    return False
    if not state.stadium:
        return True
    if len(state.stadium) != 1:
        return False
    stadium = state.stadium[0]
    return bool(
        (
            stadium.id == NIGHTTIME_MINE
            and _metadata_exact(parent, NIGHTTIME_MINE)
            and parent.card_table[ALAKAZAM].tera is False
        )
        or parent._two_prize_stadium_is_clear(state)
    )


def _resolved_evolve_rows(parent, obs):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    rows = []
    keys = []
    for option_index, option in enumerate(obs.select.option):
        if option.type != parent.OptionType.EVOLVE:
            continue
        explicit_owner = getattr(option, "playerIndex", None)
        option_owner = (
            explicit_owner if explicit_owner in (0, 1) else owner
        )
        card = core._option_card(parent, obs, option)
        target = core._target_pokemon(parent, obs, option)
        source_data = parent.card_table.get(getattr(card, "id", None))
        target_data = parent.card_table.get(getattr(target, "id", None))
        key = runtime_model.stable_option_key(parent, obs, option)
        target_zone = (
            mine.active
            if option.inPlayArea == parent.AreaType.ACTIVE
            else mine.bench
            if option.inPlayArea == parent.AreaType.BENCH
            else ()
        )
        if (
            option_owner != owner
            or option.area != parent.AreaType.HAND
            or option.inPlayArea
            not in (parent.AreaType.ACTIVE, parent.AreaType.BENCH)
            or not _exact_option(
                option,
                parent.OptionType.EVOLVE,
                area=parent.AreaType.HAND,
                index=option.index,
                playerIndex=explicit_owner,
                inPlayArea=option.inPlayArea,
                inPlayIndex=option.inPlayIndex,
            )
            or type(option.index) is not int
            or not 0 <= option.index < len(mine.hand)
            or type(option.inPlayIndex) is not int
            or not 0 <= option.inPlayIndex < len(target_zone)
            or card is None
            or target is None
            or _card_row(card) != (card.id, card.serial, owner)
            or mine.hand[option.index].serial != card.serial
            or target_zone[option.inPlayIndex].serial != target.serial
            or not parent._bridge_pokemon_is_publicly_complete(
                target, owner
            )
            or source_data is None
            or target_data is None
            or source_data.cardId != card.id
            or target_data.cardId != target.id
            or source_data.cardType != parent.CardType.POKEMON
            or target_data.cardType != parent.CardType.POKEMON
            or source_data.evolvesFrom != target_data.name
            or type(source_data.basic) is not bool
            or type(source_data.stage1) is not bool
            or type(source_data.stage2) is not bool
            or type(target_data.basic) is not bool
            or type(target_data.stage1) is not bool
            or type(target_data.stage2) is not bool
            or sum(
                (source_data.basic, source_data.stage1, source_data.stage2)
            )
            != 1
            or sum(
                (target_data.basic, target_data.stage1, target_data.stage2)
            )
            != 1
            or (
                (0 if source_data.basic else 1 if source_data.stage1 else 2)
                != (
                    0
                    if target_data.basic
                    else 1
                    if target_data.stage1
                    else 2
                )
                + 1
            )
            or type(card.serial) is not int
            or card.serial <= 0
            or type(target.serial) is not int
            or target.serial <= 0
            or card.serial == target.serial
            or key is None
        ):
            return None
        keys.append(key)
        rows.append(
            {
                "option_index": option_index,
                "option": option,
                "source": card,
                "source_serial": card.serial,
                "target": target,
                "target_serial": target.serial,
                "key": key,
            }
        )
    if len(keys) != len(set(keys)):
        return None
    return tuple(rows)


def _candidate_alakazam_exact_evolution_ko(
    parent, obs, snap, public
):
    owner = obs.current.yourIndex
    mine, theirs = (
        obs.current.players[owner],
        obs.current.players[1 - owner],
    )
    rows = _resolved_evolve_rows(parent, obs)
    if (
        rows is None
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or len(theirs.bench) < 1
        or len(mine.prize) < 1
        or type(mine.handCount) is not int
        or type(mine.deckCount) is not int
        or mine.handCount < 1
        or mine.deckCount < 0
    ):
        return None
    hand_alakazam = [
        card
        for card in mine.hand
        if card.id == ALAKAZAM
        and _card_row(card) == (ALAKAZAM, card.serial, owner)
    ]
    matches = [
        row
        for row in rows
        if row["source"].id == ALAKAZAM
        and row["target"].id == KADABRA
        and row["option"].inPlayArea == parent.AreaType.ACTIVE
        and row["option"].inPlayIndex == 0
        and row["target_serial"] == mine.active[0].serial
    ]
    if len(hand_alakazam) != 1 or len(matches) != 1:
        return None
    row = matches[0]
    if hand_alakazam[0].serial != row["source_serial"] or any(
        other is not row
        and (
            other["source_serial"] == row["source_serial"]
            or other["target_serial"] == row["target_serial"]
        )
        for other in rows
    ):
        return None
    card, kadabra = row["source"], row["target"]
    target = theirs.active[0]
    units = semantics.energy_units(parent, kadabra)
    attack = parent.attack_table.get(POWERFUL_HAND)
    target_prizes = _exact_evolution_ko_prize_value(
        parent, target, 1 - owner
    )
    if mine.deckCount >= 4:
        planned_choice = "YES"
        post_hand = mine.handCount + 2
        post_deck = mine.deckCount - 3
    else:
        planned_choice = "NO"
        post_hand = mine.handCount - 1
        post_deck = mine.deckCount
    if (
        kadabra.serial != mine.active[0].serial
        or kadabra.appearThisTurn is not False
        or kadabra.tools
        or not parent._two_prize_lineage_is_complete(kadabra, owner)
        or tuple(item.id for item in kadabra.preEvolution)
        != (parent.Abra,)
        or units is None
        or attack is None
        or semantics.missing_energy(parent, units, attack.energies)
        or not parent._two_prize_powerful_hand_metadata_is_exact()
        or not _psychic_draw_metadata_exact(parent, ALAKAZAM)
        or parent.card_table[ALAKAZAM].tera
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, target, 1 - owner
        )
        or not _exact_evolution_ko_public_effects_clear(
            parent, obs, target, 1 - owner
        )
        or type(target_prizes) is not int
        or target_prizes < 1
        or type(target.hp) is not int
        or target.hp <= 0
        or 20 * post_hand < target.hp
        or (
            mine.deckCount == 0
            and target_prizes < len(mine.prize)
        )
    ):
        return None
    protected = (
        [card.serial]
        + parent._bridge_pokemon_component_serials(kadabra)
        + parent._bridge_pokemon_component_serials(target)
    )
    if not parent._bridge_protected_serials_are_unique(
        obs.current, protected
    ):
        return None
    proof = _public_other_alakazam_serials(parent, obs, card.serial)
    alakazam_data = parent.card_table[ALAKAZAM]
    post_hp = alakazam_data.hp - (kadabra.maxHp - kadabra.hp)
    if post_hp <= 0:
        return None
    expected_active_after_evolve = (
        ALAKAZAM,
        card.serial,
        post_hp,
        alakazam_data.hp,
        True,
        getattr(kadabra, "playerIndex", None),
        tuple(int(energy) for energy in kadabra.energies),
        tuple(_card_row(item) for item in kadabra.energyCards),
        tuple(_card_row(item) for item in kadabra.tools),
        tuple(_card_row(item) for item in kadabra.preEvolution)
        + ((KADABRA, kadabra.serial, owner),),
    )
    transaction = _base_transaction(
        RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
        snap,
        obs,
        public,
        row["option_index"],
        card,
        row["key"],
    )
    transaction.update(
        kadabra_serial=kadabra.serial,
        attacker_serial=card.serial,
        target_serial=target.serial,
        target_prizes=target_prizes,
        start_deck=mine.deckCount,
        hand_after_draw=post_hand,
        planned_psychic_draw_choice=planned_choice,
        planned_post_hand=post_hand,
        planned_post_deck=post_deck,
        own_bench=tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for pokemon in mine.bench
        ),
        opponent_fields=tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for pokemon in list(theirs.active) + list(theirs.bench)
        ),
        protected_serials=tuple(protected),
        identity_reason=(
            "V1_ALAKAZAM_4TH_PUBLICLY_PROVEN"
            if proof is not None
            else "UNKNOWN_IDENTICAL_CARD_ID"
        ),
        public_other_alakazam_serials=proof or (),
        kadabra_fingerprint=parent._bridge_pokemon_fingerprint(kadabra),
        expected_active_after_evolve=expected_active_after_evolve,
    )
    return [row["option_index"]], transaction


def _bench_evolve_row(parent, obs):
    owner, mine = obs.current.yourIndex, obs.current.players[obs.current.yourIndex]
    all_evolves = [(index, option) for index, option in enumerate(obs.select.option) if option.type == parent.OptionType.EVOLVE]
    if len(all_evolves) != 1:
        return None
    option_index, option = all_evolves[0]
    card, target = core._option_card(parent, obs, option), core._target_pokemon(parent, obs, option)
    if (
        card is None
        or card.id != ALAKAZAM
        or _card_row(card) != (ALAKAZAM, card.serial, owner)
        or target is None
        or target.id != parent.Kadabra
        or option.area != parent.AreaType.HAND
        or option.inPlayArea != parent.AreaType.BENCH
        or not _exact_option(
            option,
            parent.OptionType.EVOLVE,
            area=parent.AreaType.HAND,
            index=option.index,
            inPlayArea=parent.AreaType.BENCH,
            inPlayIndex=option.inPlayIndex,
        )
        or not 0 <= option.index < len(mine.hand)
        or mine.hand[option.index].serial != card.serial
        or not 0 <= option.inPlayIndex < len(mine.bench)
        or mine.bench[option.inPlayIndex].serial != target.serial
    ):
        return None
    key = runtime_model.stable_option_key(parent, obs, option)
    return None if key is None else (option_index, card, target, key, option.inPlayIndex)


def _candidate_alakazam_ready_bench(parent, obs, snap, public):
    owner = obs.current.yourIndex
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    row = _bench_evolve_row(parent, obs)
    if (
        row is None
        or len(mine.active) != 1
        or len(theirs.active) != 1
        or mine.deckCount < 4
        or not _powerful_hand_ko(parent, obs, mine.handCount)
        or _current_ko_is_terminal(parent, obs)
    ):
        return None
    option_index, card, kadabra, key, bench_index = row
    mature = []
    attack = parent.attack_table.get(POWERFUL_HAND)
    for index, pokemon in enumerate(mine.bench):
        units = semantics.energy_units(parent, pokemon)
        if (
            pokemon.id == parent.Kadabra
            and not pokemon.appearThisTurn
            and parent._two_prize_lineage_is_complete(pokemon, owner)
            and tuple(item.id for item in pokemon.preEvolution) == (parent.Abra,)
            and units is not None
            and attack is not None
            and not semantics.missing_energy(parent, units, attack.energies)
        ):
            mature.append((index, pokemon))
    proof = _public_other_alakazam_serials(parent, obs, card.serial)
    target = theirs.active[0]
    if (
        proof is not None
        and len(mature) == 1
        and mature[0][0] == bench_index
        and mature[0][1].serial == kadabra.serial
        and mine.handCount + 2 < ceil(target.hp / 20)
    ):
        _set_compliance_block("V1_ALAKAZAM_H0_FLOOR_BLOCK")
    if (
        len(mature) != 1
        or mature[0][0] != bench_index
        or mature[0][1].serial != kadabra.serial
        or proof is None
        or mine.handCount + 2 < ceil(target.hp / 20)
        or not parent._two_prize_powerful_hand_metadata_is_exact()
        or parent.card_table[ALAKAZAM].tera
        or not _v1_powerful_hand_target_is_publicly_clear(
            parent, obs.current, target, 1 - owner
        )
    ):
        return None
    attacker_components = list(
        parent._bridge_pokemon_component_serials(mine.active[0])
    )
    attacker_top = [
        index
        for index, serial in enumerate(attacker_components)
        if serial == mine.active[0].serial
    ]
    if len(attacker_top) != 1 or mine.active[0].serial not in proof:
        return None
    del attacker_components[attacker_top[0]]
    components = (
        [card.serial]
        + attacker_components
        + parent._bridge_pokemon_component_serials(kadabra)
        + parent._bridge_pokemon_component_serials(target)
        + list(proof)
    )
    protected = tuple(components)
    if not parent._bridge_protected_serials_are_unique(obs.current, protected):
        return None
    transaction = _base_transaction(RULE_ALAKAZAM, snap, obs, public, option_index, card, key)
    transaction.update(
        rule=RULE_ALAKAZAM_READY_BENCH,
        stage="await_backup_alakazam_ability",
        kadabra_serial=kadabra.serial,
        backup_serial=card.serial,
        backup_bench_index=bench_index,
        attacker_serial=mine.active[0].serial,
        target_serial=target.serial,
        start_deck=mine.deckCount,
        hand_after_draw=mine.handCount + 2,
        active_fingerprint=parent._bridge_pokemon_fingerprint(mine.active[0]),
        other_bench=tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for index, pokemon in enumerate(mine.bench)
            if index != bench_index
        ),
        opponent_fields=tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for pokemon in list(theirs.active) + list(theirs.bench)
        ),
        public_other_alakazam_serials=proof,
        protected_serials=protected,
    )
    return [option_index], transaction


def _advance_backup_alakazam_ability(parent, obs, transaction):
    select, owner = obs.select, transaction["owner"]
    state, start = _public_state(parent, obs), transaction["start"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    expected_hand = _remove_serial(start["own_hand"], transaction["card_serial"])
    found = _find_pokemon(parent, obs, owner, transaction["backup_serial"])
    census = _child_prompt_envelope(
        parent,
        obs,
        select_type=9,
        context=parent.SelectContext.ACTIVATE,
        context_card=transaction["card_row"],
    )
    if (
        state is None
        or expected_hand is None
        or obs.current.yourIndex != owner
        or census is None
        or not _added_public_invariants_unchanged(state, start)
        or state["turn"] != start["turn"]
        or state["result"] != start["result"]
        or state["action_count"] != start["action_count"] + 1
        or state["supporter_played"] != start["supporter_played"]
        or state["stadium_played"] != start["stadium_played"]
        or state["energy_attached"] != start["energy_attached"]
        or state["retreated"] != start["retreated"]
        or state["own_hand_count"] != start["own_hand_count"] - 1
        or state["opponent_hand_count"] != start["opponent_hand_count"]
        or state["own_hand"] != expected_hand
        or state["own_discard"] != start["own_discard"]
        or state["opponent_discard"] != start["opponent_discard"]
        or state["own_deck"] != start["own_deck"]
        or state["opponent_deck"] != start["opponent_deck"]
        or state["stadium"] != start["stadium"]
        or len(mine.active) != 1
        or parent._bridge_pokemon_fingerprint(mine.active[0]) != transaction["active_fingerprint"]
        or tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for pokemon in mine.bench
            if pokemon.serial != transaction["backup_serial"]
        ) != transaction["other_bench"]
        or tuple(
            parent._bridge_pokemon_fingerprint(pokemon)
            for pokemon in list(theirs.active) + list(theirs.bench)
        ) != transaction["opponent_fields"]
        or found is None
        or found[0] != parent.AreaType.BENCH
        or found[2].id != ALAKAZAM
        or tuple(card.id for card in found[2].preEvolution) != (parent.Abra, parent.Kadabra)
        or transaction["kadabra_serial"] not in {card.serial for card in found[2].preEvolution}
        or not parent._two_prize_alakazam_is_ready(found[2], owner)
        or len(theirs.active) != 1
        or theirs.active[0].serial != transaction["target_serial"]
    ):
        return None
    prompt = _psychic_draw_prompt(parent, obs)
    decision = _psychic_draw_optional_decision(
        parent,
        obs,
        [prompt["yes_index"]] if prompt is not None else None,
    )
    if decision is None or decision["card_id"] != ALAKAZAM:
        return None
    transaction["stage"] = "await_backup_alakazam_attack"
    transaction["post_evolve"] = state
    transaction["backup_fingerprint"] = parent._bridge_pokemon_fingerprint(found[2])
    _record_owned_psychic_draw_choice(transaction, state, decision)
    return decision["action"]

def _advance_backup_alakazam_attack(parent, obs, transaction):
    owner = transaction["owner"]
    mine, theirs = obs.current.players[owner], obs.current.players[1 - owner]
    current, post = _public_state(parent, obs), transaction["post_evolve"]
    found = _find_pokemon(parent, obs, owner, transaction["backup_serial"])
    if (
        current is None
        or obs.current.yourIndex != owner
        or _child_prompt_envelope(
            parent,
            obs,
            select_type=0,
            context=parent.SelectContext.MAIN,
        ) is None
        or not _added_public_invariants_unchanged(current, post)
        or current["turn"] != post["turn"]
        or current["result"] != post["result"]
        or current["action_count"] != post["action_count"] + 1
        or current["supporter_played"] != post["supporter_played"]
        or current["stadium_played"] != post["stadium_played"]
        or current["energy_attached"] != post["energy_attached"]
        or current["retreated"] != post["retreated"]
        or not _psychic_draw_post_prompt_delta(current, post, transaction)
        or current["opponent_hand_count"] != post["opponent_hand_count"]
        or current["opponent_deck"] != post["opponent_deck"]
        or current["own_discard"] != post["own_discard"]
        or current["opponent_discard"] != post["opponent_discard"]
        or current["stadium"] != post["stadium"]
        or current["fields"] != post["fields"]
        or len(mine.active) != 1
        or mine.active[0].serial != transaction["attacker_serial"]
        or found is None
        or found[0] != parent.AreaType.BENCH
        or parent._bridge_pokemon_fingerprint(found[2]) != transaction["backup_fingerprint"]
        or len(theirs.active) != 1
        or theirs.active[0].serial != transaction["target_serial"]
        or not _powerful_hand_ko(parent, obs, mine.handCount)
    ):
        return None
    return _arm_attack_resolution(parent, obs, transaction)
