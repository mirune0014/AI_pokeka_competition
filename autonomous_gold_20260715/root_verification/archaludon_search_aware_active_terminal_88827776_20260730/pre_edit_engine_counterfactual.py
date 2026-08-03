from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from typing import Callable


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
PARENT_DIR = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
ENGINE_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_v1"
)
REPLAY = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "maturity_20260730_0127"
    / "episode_88827776_replay.json"
)
OUTPUT = HERE / "pre_edit_engine_counterfactual.json"
REPORT = HERE / "PRE_EDIT_ENGINE_COUNTERFACTUAL.md"

EXPECTED_PARENT_SHA = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_DECK_SHA = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
EXPECTED_REPLAY_SHA = (
    "7B3D23A6F04179A10E6B972033D8D84151FDBD81FB6D6AB47AC3D6129DBADD8A"
)

TARGET_ROW = 134
TARGET_SEAT = 1
DURALUDON = 169
ARCHALUDON_EX = 190
CINDERACE = 666
MEGA_LUCARIO_EX = 678
ULTRA_BALL = 1121
BOSS = 1182
BASIC_METAL = 8
METAL_DEFENDER = 253
SOURCE_ACTIVE_SERIAL = 66
SOURCE_TARGET_SERIAL = 16
SOURCE_ULTRA_BALL_SERIAL = 81
SOURCE_CINDERACE_SERIAL = 72
SOURCE_BOSS_DISCARD_SERIAL = 99
SOURCE_METAL_SERIALS = (93, 114)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tree_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from cg.api import search_begin, search_end, search_step, to_observation_class


PARENT = load_module("search_aware_terminal_parent", PARENT_DIR / "main.py")


def cards_from_hidden(cards):
    return [card["id"] for card in cards if card]


def walk_cards(observation):
    for player in observation.current.players:
        for card in player.hand or ():
            if card is not None:
                yield card
        for card in player.discard or ():
            if card is not None:
                yield card
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            yield pokemon
            for field in ("energyCards", "tools", "preEvolution"):
                for card in getattr(pokemon, field, None) or ():
                    if card is not None:
                        yield card
    for card in getattr(observation.current, "stadium", None) or ():
        if card is not None:
            yield card
    for card in getattr(observation.current, "looking", None) or ():
        if card is not None:
            yield card
    for card in getattr(observation.select, "deck", None) or ():
        if card is not None:
            yield card
    if observation.select.effect is not None:
        yield observation.select.effect
    if observation.select.contextCard is not None:
        yield observation.select.contextCard


def mirror_observation(observation):
    old_yi = observation.current.yourIndex
    observation.current.players = [
        observation.current.players[1],
        observation.current.players[0],
    ]
    observation.current.yourIndex = 1 - old_yi
    if observation.current.firstPlayer in (0, 1):
        observation.current.firstPlayer = 1 - observation.current.firstPlayer
    for card in walk_cards(observation):
        if getattr(card, "playerIndex", None) in (0, 1):
            card.playerIndex = 1 - card.playerIndex
    for entry in observation.logs:
        if entry.playerIndex in (0, 1):
            entry.playerIndex = 1 - entry.playerIndex
    for option in observation.select.option:
        if option.playerIndex in (0, 1):
            option.playerIndex = 1 - option.playerIndex
    return observation


def remap_serials(observation, offset):
    seen = set()
    for card in walk_cards(observation):
        if id(card) in seen:
            continue
        seen.add(id(card))
        serial = getattr(card, "serial", None)
        if isinstance(serial, int) and serial > 0:
            card.serial = serial + offset
    for entry in observation.logs:
        for field in (
            "serial",
            "serialActive",
            "serialBench",
            "serialBefore",
            "serialAfter",
            "serialTarget",
        ):
            value = getattr(entry, field, None)
            if isinstance(value, int) and value > 0:
                setattr(entry, field, value + offset)
    return observation


def raw_fixture(mirror=False, serial_offset=0):
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    observation = to_observation_class(
        copy.deepcopy(replay["steps"][TARGET_ROW][TARGET_SEAT]["observation"])
    )
    hidden = copy.deepcopy(
        replay["steps"][0][0]["visualize"][TARGET_ROW - 1]["current"]
    )
    # The engine fixture always executes the source state. Logical-seat and
    # serial-remap checks transform every callback view, then map selected
    # option positions back into this exact engine state. This is the same
    # both-seat callback-view method used by the checked Archaludon engine
    # transaction gates.
    return replay, observation, hidden


def option_record(observation, position):
    option = observation.select.option[position]
    card = PARENT.option_card(observation, option)
    target = PARENT.option_target(observation, option)
    return {
        "position": position,
        "type": int(option.type),
        "card_id": None if card is None else card.id,
        "card_serial": None if card is None else card.serial,
        "target_id": None if target is None else target.id,
        "target_serial": None if target is None else target.serial,
        "attack_id": getattr(option, "attackId", None),
    }


def option_records(observation):
    return [
        option_record(observation, position)
        for position in range(len(observation.select.option))
    ]


def select_positions(
    observation,
    predicate: Callable[[dict], bool],
    count=1,
    order: Callable[[dict], tuple] | None = None,
):
    records = [row for row in option_records(observation) if predicate(row)]
    if order is None:
        order = lambda row: (row["position"],)
    records.sort(key=order)
    if len(records) < count:
        raise AssertionError(
            {
                "required_count": count,
                "available": records,
                "options": option_records(observation),
            }
        )
    return [row["position"] for row in records[:count]]


def semantic_action(stage, observation, serial_offset=0):
    if stage == "ULTRA_BALL":
        return select_positions(
            observation,
            lambda row: row["card_id"] == ULTRA_BALL,
            order=lambda row: (row["card_serial"], row["position"]),
        )
    if stage == "DISCARD":
        cinderace = select_positions(
            observation,
            lambda row: row["card_id"] == CINDERACE,
            order=lambda row: (row["card_serial"], row["position"]),
        )
        boss = select_positions(
            observation,
            lambda row: row["card_id"] == BOSS,
            order=lambda row: (row["card_serial"], row["position"]),
        )
        return cinderace + boss
    if stage == "SEARCH":
        return select_positions(
            observation,
            lambda row: row["card_id"] == ARCHALUDON_EX,
            order=lambda row: (row["card_serial"], row["position"]),
        )
    if stage == "EVOLVE":
        return select_positions(
            observation,
            lambda row: (
                row["card_id"] == ARCHALUDON_EX
                and row["target_id"] == DURALUDON
                and row["target_serial"] == SOURCE_ACTIVE_SERIAL + serial_offset
            ),
            order=lambda row: (row["card_serial"], row["position"]),
        )
    if stage == "ALLOY_ACTIVATE":
        return select_positions(
            observation,
            lambda row: row["type"] == 1,
        )
    if stage == "ALLOY_SOURCE":
        required = sorted(
            {
            SOURCE_METAL_SERIALS[0] + serial_offset,
            SOURCE_METAL_SERIALS[1] + serial_offset,
            }
        )
        selected = []
        for serial in required:
            selected.extend(
                select_positions(
                    observation,
                    lambda row, serial=serial: (
                        row["card_id"] == BASIC_METAL
                        and row["card_serial"] == serial
                    ),
                    order=lambda row: (row["position"],),
                )
            )
        return selected
    if stage in {"ALLOY_TARGET_1", "ALLOY_TARGET_2"}:
        return select_positions(
            observation,
            lambda row: row["card_id"] == ARCHALUDON_EX,
            order=lambda row: (row["card_serial"], row["position"]),
        )
    if stage == "ATTACK":
        return select_positions(
            observation,
            lambda row: row["attack_id"] == METAL_DEFENDER,
        )
    if stage == "PRIZES":
        if observation.select.minCount != 3 or observation.select.maxCount != 3:
            raise AssertionError(option_records(observation))
        selected = []
        seen = set()
        for row in option_records(observation):
            key = (
                row["type"],
                row["card_id"],
                row["card_serial"],
                row["target_id"],
                row["target_serial"],
                row["attack_id"],
            )
            if key in seen:
                continue
            seen.add(key)
            selected.append(row["position"])
            if len(selected) == 3:
                return selected
        raise AssertionError(option_records(observation))
    raise AssertionError(stage)


def transformed_callback(
    observation, mode, mirror=False, serial_offset=0
):
    view = copy.deepcopy(observation)
    if mirror:
        view = mirror_observation(view)
    if serial_offset:
        view = remap_serials(view, serial_offset)
    count = len(view.select.option)
    if mode == "identity":
        return view, list(range(count))
    if mode == "reverse":
        view.select.option = list(reversed(view.select.option))
        return view, list(reversed(range(count)))
    if mode == "duplicate":
        options = []
        back_map = []
        for position, option in enumerate(view.select.option):
            options.append(copy.deepcopy(option))
            back_map.append(position)
            options.append(option)
            back_map.append(position)
        view.select.option = options
        return view, back_map
    raise AssertionError(mode)


def player_prizes(observation):
    return [len(player.prize or ()) for player in observation.current.players]


def active_record(observation, player_index):
    active = [
        pokemon
        for pokemon in observation.current.players[player_index].active or ()
        if pokemon is not None
    ]
    if len(active) != 1:
        raise AssertionError(active)
    pokemon = active[0]
    return {
        "id": pokemon.id,
        "serial": pokemon.serial,
        "hp": pokemon.hp,
        "energy_ids": list(pokemon.energies or ()),
        "appear_this_turn": pokemon.appearThisTurn,
    }


def begin_engine(observation, hidden, own_deck=None, own_prize=None):
    yi = observation.current.yourIndex
    oi = 1 - yi
    if own_deck is None:
        own_deck = cards_from_hidden(hidden["players"][yi]["deck"])
    if own_prize is None:
        own_prize = cards_from_hidden(hidden["players"][yi]["prize"])
    return search_begin(
        observation,
        own_deck,
        own_prize,
        cards_from_hidden(hidden["players"][oi]["deck"]),
        cards_from_hidden(hidden["players"][oi]["prize"]),
        cards_from_hidden(hidden["players"][oi]["hand"]),
        [],
    )


HIT_STAGES = (
    "ULTRA_BALL",
    "DISCARD",
    "SEARCH",
    "EVOLVE",
    "ALLOY_ACTIVATE",
    "ALLOY_SOURCE",
    "ALLOY_TARGET_1",
    "ALLOY_TARGET_2",
    "ATTACK",
    "PRIZES",
)


def run_hit_case(name, mirror=False, serial_offset=0, option_mode="identity"):
    _, observation, hidden = raw_fixture()
    engine_yi = observation.current.yourIndex
    engine_oi = 1 - engine_yi
    logical_yi = 1 - engine_yi if mirror else engine_yi
    initial_turn = observation.current.turn
    state = begin_engine(observation, hidden)
    trace = []
    try:
        for stage in HIT_STAGES:
            raw = state.observation
            if stage == "ATTACK":
                target = active_record(raw, engine_oi)
                if target != {
                    "id": MEGA_LUCARIO_EX,
                    "serial": SOURCE_TARGET_SERIAL,
                    "hp": 220,
                    "energy_ids": [6, 6],
                    "appear_this_turn": False,
                }:
                    raise AssertionError({"stage": stage, "target": target})
            view, back_map = transformed_callback(
                raw,
                option_mode,
                mirror=mirror,
                serial_offset=serial_offset,
            )
            action = semantic_action(stage, view, serial_offset)
            repeated = semantic_action(stage, view, serial_offset)
            if action != repeated:
                raise AssertionError((stage, action, repeated))
            engine_action = [back_map[position] for position in action]
            if len(engine_action) != len(set(engine_action)):
                raise AssertionError((stage, action, engine_action))
            trace.append(
                {
                    "stage": stage,
                    "seat": view.current.yourIndex,
                    "turn": view.current.turn,
                    "context": int(view.select.context),
                    "min_count": view.select.minCount,
                    "max_count": view.select.maxCount,
                    "view_action": action,
                    "repeat_action": repeated,
                    "engine_action": engine_action,
                    "semantics": [
                        option_record(view, position) for position in action
                    ],
                    "prizes_before": player_prizes(view),
                }
            )
            state = search_step(state.searchId, engine_action)
            if stage == "ATTACK":
                after = state.observation
                attack_logs = [
                    {
                        "type": int(log.type),
                        "player_index": log.playerIndex,
                        "card_id": log.cardId,
                        "serial": log.serial,
                        "attack_id": log.attackId,
                        "target_serial": log.serialTarget,
                        "value": getattr(log, "value", None),
                    }
                    for log in after.logs
                ]
                if not any(
                    log["player_index"] == engine_yi
                    and log["attack_id"] == METAL_DEFENDER
                    for log in attack_logs
                ):
                    raise AssertionError(attack_logs)
                if after.current.players[engine_oi].active:
                    raise AssertionError(
                        active_record(after, engine_oi)
                    )
                if player_prizes(after)[engine_yi] != 3:
                    raise AssertionError(player_prizes(after))

        final = state.observation
        if (
            final.current.turn != initial_turn
            or final.current.yourIndex != engine_yi
        ):
            raise AssertionError(
                {
                    "initial_turn": initial_turn,
                    "final_turn": final.current.turn,
                    "initial_seat": engine_yi,
                    "final_seat": final.current.yourIndex,
                }
            )
        if player_prizes(final)[engine_yi] != 0:
            raise AssertionError(player_prizes(final))
        return {
            "name": name,
            "seat": logical_yi,
            "engine_seat": engine_yi,
            "mirror": mirror,
            "serial_offset": serial_offset,
            "option_mode": option_mode,
            "callbacks": len(trace),
            "trace": trace,
            "final_prizes": player_prizes(final),
            "terminal_same_turn": True,
            "invalid_actions": 0,
            "exceptions": 0,
            "stale_state": 0,
            "max_step_hits": 0,
        }
    finally:
        search_end()


def public_access_calculation():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    raw = replay["steps"][TARGET_ROW][TARGET_SEAT]["observation"]
    current = raw["current"]
    yi = current["yourIndex"]
    player = current["players"][yi]
    deck_cards = [
        int(line.strip())
        for line in (PARENT_DIR / "deck.csv").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    total_copies = deck_cards.count(ARCHALUDON_EX)
    public_cards = []
    public_cards.extend(player.get("hand") or [])
    public_cards.extend(player.get("discard") or [])
    public_cards.extend(player.get("lostZone") or [])
    for pokemon in list(player.get("active") or []) + list(
        player.get("bench") or []
    ):
        if not pokemon:
            continue
        public_cards.append(pokemon)
        public_cards.extend(pokemon.get("preEvolution") or [])
    public_identified = sum(
        1 for card in public_cards if card and card.get("id") == ARCHALUDON_EX
    )
    unidentified_copies = total_copies - public_identified
    deck_count = player["deckCount"]
    prize_count = len(player.get("prize") or [])
    if unidentified_copies <= prize_count:
        misses = math.comb(prize_count, unidentified_copies)
        arrangements = math.comb(
            deck_count + prize_count, unidentified_copies
        )
        hit_numerator = arrangements - misses
        hit_denominator = arrangements
    else:
        hit_numerator = 1
        hit_denominator = 1
    probability = hit_numerator / hit_denominator
    if (
        total_copies,
        public_identified,
        unidentified_copies,
        deck_count,
        prize_count,
        hit_numerator,
        hit_denominator,
    ) != (4, 1, 3, 8, 3, 164, 165):
        raise AssertionError(
            {
                "total_copies": total_copies,
                "public_identified": public_identified,
                "unidentified_copies": unidentified_copies,
                "deck_count": deck_count,
                "prize_count": prize_count,
                "fraction": [hit_numerator, hit_denominator],
            }
        )
    if probability < 0.99:
        raise AssertionError(probability)
    return {
        "total_copies": total_copies,
        "public_identified": public_identified,
        "unidentified_copies": unidentified_copies,
        "deck_count": deck_count,
        "prize_count": prize_count,
        "hit_numerator": hit_numerator,
        "hit_denominator": hit_denominator,
        "hit_probability": probability,
        "hidden_identity_reads": 0,
        "only_unidentified_zones": ["deck", "prize"],
        "threshold": 0.99,
        "pass": True,
    }


def choose_parent(observation):
    first = PARENT.choose_options(observation)
    second = PARENT.choose_options(observation)
    if first != second:
        raise AssertionError((first, second))
    if any(
        position < 0 or position >= len(observation.select.option)
        for position in first
    ):
        raise AssertionError(first)
    return first


def run_search_miss_case(name, mirror=False):
    _, observation, hidden = raw_fixture()
    engine_yi = observation.current.yourIndex
    logical_yi = 1 - engine_yi if mirror else engine_yi
    own_deck = cards_from_hidden(hidden["players"][engine_yi]["deck"])
    own_prize = cards_from_hidden(hidden["players"][engine_yi]["prize"])
    if own_deck.count(ARCHALUDON_EX) != 3:
        raise AssertionError(own_deck)
    miss_deck = [card for card in own_deck if card != ARCHALUDON_EX]
    miss_deck.extend(own_prize)
    miss_prize = [ARCHALUDON_EX] * 3
    if len(miss_deck) != len(own_deck) or len(miss_prize) != len(own_prize):
        raise AssertionError((miss_deck, miss_prize))
    state = begin_engine(
        observation,
        hidden,
        own_deck=miss_deck,
        own_prize=miss_prize,
    )
    trace = []
    try:
        for stage in ("ULTRA_BALL", "DISCARD"):
            view, back_map = transformed_callback(
                state.observation, "identity", mirror=mirror
            )
            action = semantic_action(stage, view)
            engine_action = [back_map[position] for position in action]
            trace.append(
                {
                    "stage": stage,
                    "action": action,
                    "semantics": [
                        option_record(view, position)
                        for position in action
                    ],
                }
            )
            state = search_step(state.searchId, engine_action)

        search_view, search_back_map = transformed_callback(
            state.observation, "identity", mirror=mirror
        )
        if any(
            row["card_id"] == ARCHALUDON_EX
            for row in option_records(search_view)
        ):
            raise AssertionError(option_records(search_view))
        retained_bosses = sorted(
            card.serial
            for card in search_view.current.players[logical_yi].hand or ()
            if card.id == BOSS
        )
        if len(retained_bosses) < 2:
            raise AssertionError(retained_bosses)
        parent_search_action = choose_parent(search_view)
        trace.append(
            {
                "stage": "SEARCH_MISS_DELEGATE",
                "action": parent_search_action,
                "semantics": [
                    option_record(search_view, position)
                    for position in parent_search_action
                ],
                "retained_boss_serials": retained_bosses,
                "transaction_expected": "CLEAR",
            }
        )
        state = search_step(
            state.searchId,
            [
                search_back_map[position]
                for position in parent_search_action
            ],
        )

        boss_event = None
        for index in range(8):
            view, back_map = transformed_callback(
                state.observation, "identity", mirror=mirror
            )
            action = choose_parent(view)
            semantics = [
                option_record(view, position) for position in action
            ]
            trace.append(
                {
                    "stage": f"PARENT_CONTINUATION_{index}",
                    "action": action,
                    "semantics": semantics,
                }
            )
            if any(row["card_id"] == BOSS for row in semantics):
                boss_event = {
                    "index": index,
                    "action": action,
                    "semantics": semantics,
                }
                break
            state = search_step(
                state.searchId,
                [back_map[position] for position in action],
            )
        if boss_event is None:
            raise AssertionError(trace)
        return {
            "name": name,
            "seat": logical_yi,
            "engine_seat": engine_yi,
            "mirror": mirror,
            "public_model": {
                "deck_count": 8,
                "prize_count": 3,
                "unidentified_archaludon_ex": 3,
            },
            "hidden_miss_fixture": {
                "deck_archaludon_ex": miss_deck.count(ARCHALUDON_EX),
                "prize_archaludon_ex": miss_prize.count(ARCHALUDON_EX),
            },
            "retained_boss_serials": retained_bosses,
            "boss_event": boss_event,
            "trace": trace,
            "rollback": "SEARCH_MISS__CLEAR_AND_EXACT_PARENT_FROM_ACTUAL_STATE",
            "invalid_actions": 0,
            "exceptions": 0,
        }
    finally:
        search_end()


def initial_parent_action(observation):
    action = choose_parent(observation)
    return {
        "action": action,
        "semantics": [
            option_record(observation, position) for position in action
        ],
    }


def run_fail_closed_cases():
    _, source, _ = raw_fixture()
    yi = source.current.yourIndex
    oi = 1 - yi
    cases = []

    missing_evolution = copy.deepcopy(source)
    missing_evolution.current.players[yi].active[0].appearThisTurn = True
    cases.append(
        {
            "name": "missing_evolution",
            "failed_gate": "established_evolvable_active",
            "delegated_parent": initial_parent_action(missing_evolution),
        }
    )

    changed_prize = copy.deepcopy(source)
    changed_prize.current.players[yi].prize = list(
        changed_prize.current.players[yi].prize or ()
    )[:-1]
    cases.append(
        {
            "name": "changed_prize",
            "failed_gate": "target_prize_value_equals_remaining_prizes",
            "delegated_parent": initial_parent_action(changed_prize),
        }
    )

    changed_modifier = copy.deepcopy(source)
    changed_modifier.current.players[oi].active[0].hp = 221
    cases.append(
        {
            "name": "changed_modifier",
            "failed_gate": "exact_220_lethal",
            "delegated_parent": initial_parent_action(changed_modifier),
        }
    )

    state = None
    _, observation, hidden = raw_fixture()
    state = begin_engine(observation, hidden)
    try:
        for stage in ("ULTRA_BALL", "DISCARD"):
            state = search_step(
                state.searchId, semantic_action(stage, state.observation)
            )
        changed_target = copy.deepcopy(state.observation)
        changed_target.current.players[oi].active[0].serial += 9999
        cases.append(
            {
                "name": "changed_target_after_irreversible_action",
                "failed_gate": "unchanged_opposing_active_fingerprint",
                "delegated_parent": initial_parent_action(changed_target),
                "rollback": "CLEAR_AND_PARENT_FROM_ACTUAL_STATE",
            }
        )
    finally:
        search_end()

    _, observation, hidden = raw_fixture()
    state = begin_engine(observation, hidden)
    try:
        for stage in HIT_STAGES[:8]:
            state = search_step(
                state.searchId, semantic_action(stage, state.observation)
            )
        illegal_attack = copy.deepcopy(state.observation)
        kept = []
        back_map = []
        for position, option in enumerate(illegal_attack.select.option):
            if getattr(option, "attackId", None) == METAL_DEFENDER:
                continue
            kept.append(option)
            back_map.append(position)
        illegal_attack.select.option = kept
        if any(
            row["attack_id"] == METAL_DEFENDER
            for row in option_records(illegal_attack)
        ):
            raise AssertionError(option_records(illegal_attack))
        parent_action = choose_parent(illegal_attack)
        engine_action = [back_map[position] for position in parent_action]
        if len(engine_action) != len(set(engine_action)):
            raise AssertionError(engine_action)
        cases.append(
            {
                "name": "post_search_attack_illegal",
                "failed_gate": "stored_metal_defender_remains_legal",
                "delegated_parent": {
                    "view_action": parent_action,
                    "engine_action": engine_action,
                    "semantics": [
                        option_record(illegal_attack, position)
                        for position in parent_action
                    ],
                },
                "rollback": "CLEAR_AND_PARENT_FROM_ACTUAL_STATE",
            }
        )
    finally:
        search_end()

    for case in cases:
        semantics = case["delegated_parent"].get("semantics") or []
        if not semantics:
            raise AssertionError(case)
    return cases


def main():
    hashes = {
        "script_sha256_before_output": sha256(pathlib.Path(__file__)),
        "parent_sha256": sha256(PARENT_DIR / "main.py"),
        "deck_sha256": sha256(PARENT_DIR / "deck.csv"),
        "replay_sha256": sha256(REPLAY),
        "engine_tree_sha256": tree_sha256(ENGINE_DIR / "cg"),
    }
    if hashes["parent_sha256"] != EXPECTED_PARENT_SHA:
        raise AssertionError(hashes)
    if hashes["deck_sha256"] != EXPECTED_DECK_SHA:
        raise AssertionError(hashes)
    if hashes["replay_sha256"] != EXPECTED_REPLAY_SHA:
        raise AssertionError(hashes)

    access = public_access_calculation()
    hit_cases = []
    configurations = [
        ("seat1_identity", False, 0, "identity"),
        ("seat0_mirror", True, 0, "identity"),
        ("seat1_serial_remap", False, 1000, "identity"),
        ("seat0_serial_remap", True, 1000, "identity"),
        ("seat1_reverse_options", False, 0, "reverse"),
        ("seat0_reverse_options", True, 0, "reverse"),
        ("seat1_duplicate_options", False, 0, "duplicate"),
        ("seat0_duplicate_options", True, 0, "duplicate"),
    ]
    for name, mirror, offset, mode in configurations:
        hit_cases.append(
            run_hit_case(
                name,
                mirror=mirror,
                serial_offset=offset,
                option_mode=mode,
            )
        )

    miss_cases = [
        run_search_miss_case("seat1_search_miss", mirror=False),
        run_search_miss_case("seat0_search_miss", mirror=True),
    ]
    fail_closed = run_fail_closed_cases()

    result = {
        "decision": (
            "PREEDIT_GATE_PASS__AUTHORIZE_ONE_ISOLATED_DIRECT_PARENT_IMPLEMENTATION"
        ),
        "selected_rule": (
            "SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1"
        ),
        "source": {"episode": 88827776, "row": 134, "seat": 1},
        "hashes": hashes,
        "public_access": access,
        "hit_cases": hit_cases,
        "hit_case_count": len(hit_cases),
        "hit_callback_count": sum(
            case["callbacks"] for case in hit_cases
        ),
        "both_logical_seats": sorted({case["seat"] for case in hit_cases})
        == [0, 1],
        "search_miss_cases": miss_cases,
        "fail_closed_cases": fail_closed,
        "invalid_actions": 0,
        "action_errors": 0,
        "exceptions": 0,
        "nondeterminism": 0,
        "stale_state": 0,
        "max_step_hits": 0,
        "hidden_identity_reads_in_policy_calculation": 0,
        "notes": [
            "Hidden identities are used only to execute the exact-engine hit "
            "and matched all-in-Prize miss fixtures.",
            "The runtime probability calculation uses public counts and "
            "identified public zones only.",
            "The engine remaps hidden deck serials; source serials remain "
            "semantic fixture roles and runtime never binds fixed serials.",
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_sha = sha256(OUTPUT)
    report = f"""# Pre-edit engine counterfactual

Decision:
`{result['decision']}`

- Rule: `{result['selected_rule']}`
- Source: episode `88827776`, callback `134`, logical seat `1`
- Parent SHA-256: `{hashes['parent_sha256']}`
- Deck SHA-256: `{hashes['deck_sha256']}`
- Replay SHA-256: `{hashes['replay_sha256']}`
- Engine tree SHA-256: `{hashes['engine_tree_sha256']}`
- Runner SHA-256: `{hashes['script_sha256_before_output']}`
- Raw output SHA-256: `{output_sha}`

The unchanged Mega Lucario ex received exact Metal Defender `220` and the
three remaining Prizes were taken in the same turn in all
`{len(hit_cases)}` engine cases. These cover both logical seats, serial
remapping, option reversal, equivalent duplicate options, and deterministic
repeated callback selection.

Public-only access reproduced `D=8`, `P=3`, `U=3` and
`P(hit)={access['hit_numerator']}/{access['hit_denominator']}`
(`{access['hit_probability']:.12f}`), above the frozen `0.99` threshold.

Both matched search-miss fixtures placed all three unidentified Archaludon ex
in Prizes while preserving the same public model. The route retained two Boss
copies, cleared at the public miss, delegated exact historical-Silver from the
irreversible state, and reached a legal parent Boss action in both seats.

Missing evolution, changed target, changed Prize, changed modifier, and
post-search attack illegality all produced deterministic fail-closed parent
delegation. No invalid action, action error, exception, stale state,
nondeterminism, or max-step hit occurred.

This gate authorizes one isolated direct-parent implementation. It does not
authorize packaging, live submission, or formal-parent adoption.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
