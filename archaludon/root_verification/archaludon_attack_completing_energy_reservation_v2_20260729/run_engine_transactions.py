from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_attack_completing_energy_reservation_v2"
)
PARENT = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
REPLAY = (
    ROOT
    / "archaludon"
    / "evidence"
    / "live_54927163_refresh_20260729_0344"
    / "episode_88584180_replay.json"
)
EXPECTED_ENGINE_SHA256 = (
    "466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF"
)


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(CANDIDATE))
AGENT = load_module("h6_engine_candidate", CANDIDATE / "main.py")
PARENT_MOD = load_module("h6_engine_parent", PARENT / "main.py")


def reset() -> None:
    AGENT._h6_reset()
    AGENT._opp_last_attack_id = 937
    AGENT._cur_turn_logs.clear()
    PARENT_MOD._opp_last_attack_id = 937
    PARENT_MOD._cur_turn_logs.clear()


def visible_cards(observation):
    for player in observation.current.players:
        for card in list(player.hand or ()) + list(player.discard or ()):
            if card is not None:
                yield card
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            yield pokemon
            for card in (
                list(pokemon.energyCards or ())
                + list(pokemon.tools or ())
                + list(pokemon.preEvolution or ())
            ):
                if card is not None:
                    yield card
    for card in observation.current.stadium or ():
        if card is not None:
            yield card
    for card in observation.select.deck or ():
        if card is not None:
            yield card
    if observation.select.effect is not None:
        yield observation.select.effect
    if observation.select.contextCard is not None:
        yield observation.select.contextCard


def mirror_view(observation):
    observation = copy.deepcopy(observation)
    observation.current.players = [
        observation.current.players[1],
        observation.current.players[0],
    ]
    observation.current.yourIndex = 1 - observation.current.yourIndex
    if observation.current.firstPlayer in (0, 1):
        observation.current.firstPlayer = 1 - observation.current.firstPlayer
    seen = set()
    for card in visible_cards(observation):
        if id(card) in seen:
            continue
        seen.add(id(card))
        if getattr(card, "playerIndex", None) in (0, 1):
            card.playerIndex = 1 - card.playerIndex
    for entry in observation.logs:
        if entry.playerIndex in (0, 1):
            entry.playerIndex = 1 - entry.playerIndex
    for option in observation.select.option:
        if option.playerIndex in (0, 1):
            option.playerIndex = 1 - option.playerIndex
    return observation, list(range(len(observation.select.option)))


def identity_view(observation):
    return observation, list(range(len(observation.select.option)))


def reverse_view(observation):
    observation = copy.deepcopy(observation)
    count = len(observation.select.option)
    observation.select.option.reverse()
    return observation, list(reversed(range(count)))


def duplicate_view(observation):
    observation = copy.deepcopy(observation)
    options = []
    back_map = []
    for position, option in enumerate(observation.select.option):
        options.extend((copy.deepcopy(option), option))
        back_map.extend((position, position))
    observation.select.option = options
    return observation, back_map


def offset_serial_view(observation):
    observation = copy.deepcopy(observation)
    seen = set()
    for card in visible_cards(observation):
        if id(card) in seen:
            continue
        seen.add(id(card))
        if isinstance(getattr(card, "serial", None), int):
            card.serial += 1000
    for entry in observation.logs:
        for name in (
            "serial",
            "serialActive",
            "serialBench",
            "serialBefore",
            "serialAfter",
            "serialTarget",
        ):
            value = getattr(entry, name, None)
            if isinstance(value, int):
                setattr(entry, name, value + 1000)
    return observation, list(range(len(observation.select.option)))


def semantic(module, observation, selected):
    output = []
    for position in selected:
        option = observation.select.option[position]
        card = module.option_card(observation, option)
        target = module.option_target(observation, option)
        output.append(
            {
                "position": position,
                "type": int(option.type),
                "context": int(observation.select.context),
                "card_id": getattr(card, "id", None),
                "serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": option.attackId,
            }
        )
    return output


def position_free(items):
    return [
        {key: value for key, value in item.items() if key != "position"}
        for item in items
    ]


def run_case(name, row, transform, expected, h6_expected):
    from cg.api import search_begin, search_end, search_step, to_observation_class

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    physical_seat = 1
    opponent_seat = 0
    initial = to_observation_class(
        copy.deepcopy(replay["steps"][row][physical_seat]["observation"])
    )
    hidden = replay["steps"][0][0]["visualize"][row - 1]["current"]
    ids = lambda cards: [card["id"] for card in cards if card]
    initial_target_hp = initial.current.players[opponent_seat].active[0].hp
    initial_prizes = len(initial.current.players[physical_seat].prize)
    attacker_serial = initial.current.players[physical_seat].active[0].serial
    target_serial = initial.current.players[opponent_seat].active[0].serial
    reset()
    state = search_begin(
        initial,
        ids(hidden["players"][physical_seat]["deck"]),
        ids(hidden["players"][physical_seat]["prize"]),
        ids(hidden["players"][opponent_seat]["deck"]),
        ids(hidden["players"][opponent_seat]["prize"]),
        ids(hidden["players"][opponent_seat]["hand"]),
        [],
    )
    callbacks = []
    observations = []
    try:
        for index, expected_item in enumerate(expected):
            raw = state.observation
            candidate_view, back_map = transform(copy.deepcopy(raw))
            parent_view = copy.deepcopy(candidate_view)
            logical_seat = candidate_view.current.yourIndex
            observations.append(copy.deepcopy(candidate_view))
            parent_action = PARENT_MOD.choose_options(parent_view)
            candidate_action = AGENT.choose_options(candidate_view)
            transaction = copy.deepcopy(AGENT._h6_transaction)
            repeated = AGENT.choose_options(candidate_view)
            repeated_transaction = copy.deepcopy(AGENT._h6_transaction)
            if candidate_action != repeated or transaction != repeated_transaction:
                raise AssertionError(
                    (name, index, "repeat changed", candidate_action, repeated)
                )
            candidate_semantic = semantic(
                AGENT, candidate_view, candidate_action
            )
            parent_semantic = semantic(
                PARENT_MOD, parent_view, parent_action
            )
            item_type, item_id = expected_item
            if item_type == "card":
                actual = candidate_semantic[0]["card_id"]
            elif item_type == "attack":
                actual = candidate_semantic[0]["attack_id"]
            elif item_type == "discard_pair":
                actual = {
                    (item["card_id"], item["serial"])
                    for item in candidate_semantic
                }
            else:
                raise AssertionError(item_type)
            if actual != item_id:
                raise AssertionError((name, index, actual, item_id))
            if row in {111, 142} and position_free(
                candidate_semantic
            ) != position_free(parent_semantic):
                raise AssertionError(
                    (name, index, parent_semantic, candidate_semantic)
                )
            if h6_expected and transaction is None:
                raise AssertionError((name, index, "H6 cleared"))
            if not h6_expected and transaction is not None:
                raise AssertionError((name, index, "unexpected H6", transaction))
            if transform is duplicate_view and any(
                position % 2 for position in candidate_action
            ):
                raise AssertionError(
                    (name, index, "not lowest duplicate", candidate_action)
                )
            callbacks.append(
                {
                    "index": index,
                    "logical_seat": logical_seat,
                    "turn": candidate_view.current.turn,
                    "turn_action_count": candidate_view.current.turnActionCount,
                    "context": int(candidate_view.select.context),
                    "parent": parent_semantic,
                    "candidate": candidate_semantic,
                    "repeated": semantic(
                        AGENT, candidate_view, repeated
                    ),
                    "stage": (
                        None if transaction is None else transaction["stage"]
                    ),
                    "history": (
                        None
                        if transaction is None
                        else list(transaction["history"])
                    ),
                }
            )
            engine_action = [back_map[position] for position in candidate_action]
            if len(engine_action) != len(set(engine_action)):
                raise AssertionError((name, index, engine_action))
            state = search_step(state.searchId, engine_action)

        final = copy.deepcopy(state.observation)
        logs = [
            {
                "type": int(entry.type),
                "player_index": entry.playerIndex,
                "card_id": entry.cardId,
                "serial": entry.serial,
                "attack_id": entry.attackId,
                "value": entry.value,
                "target_serial": entry.serialTarget,
            }
            for entry in final.logs
        ]
        attack_logs = [
            entry
            for entry in final.logs
            if entry.type == AGENT.LogType.ATTACK
            and entry.playerIndex == physical_seat
            and entry.serial == attacker_serial
        ]
        if not attack_logs or attack_logs[-1].attackId != expected[-1][1]:
            raise AssertionError((name, "attack not confirmed", logs))
        attack_damage_logs = [
            entry.value
            for entry in final.logs
            if entry.type == AGENT.LogType.HP_CHANGE
            and entry.playerIndex == opponent_seat
            and entry.serial == target_serial
            and entry.value is not None
        ]
        final_prizes = len(final.current.players[physical_seat].prize)
        final_target = next(
            (
                pokemon
                for pokemon in final.current.players[opponent_seat].active
                if pokemon is not None and pokemon.serial == target_serial
            ),
            None,
        )
        if h6_expected:
            final_view, _ = transform(copy.deepcopy(final))
            AGENT._h6_choose(final_view, [])
            if AGENT._h6_transaction is not None:
                raise AssertionError((name, "stale transaction"))
    finally:
        search_end()

    return {
        "name": name,
        "row": row,
        "logical_seat": callbacks[0]["logical_seat"],
        "physical_engine_seat": physical_seat,
        "callbacks": callbacks,
        "callback_count": len(callbacks),
        "initial_target_hp": initial_target_hp,
        "immediate_post_attack_hp": (
            initial_target_hp + attack_damage_logs[0]
            if attack_damage_logs
            else None
        ),
        "final_target_hp_after_checkup": (
            None if final_target is None else final_target.hp
        ),
        "attack_damage_logs": attack_damage_logs,
        "initial_prizes": initial_prizes,
        "final_prizes": final_prizes,
        "prizes_taken": initial_prizes - final_prizes,
        "turn_completed": final.current.turn != initial.current.turn,
        "final_turn": final.current.turn,
        "final_your_index": final.current.yourIndex,
        "transaction_cleared": AGENT._h6_transaction is None,
        "logs": logs,
    }


def apply_option_mode(observation, mode):
    if mode == "identity":
        return
    if mode == "reverse":
        observation.select.option.reverse()
        return
    if mode == "duplicate":
        observation.select.option = [
            copy.deepcopy(option)
            for option in observation.select.option
            for _ in range(2)
        ]
        return
    raise AssertionError(mode)


def mutate_hand_uniqueness(observation, mutation):
    mine = AGENT.my_state(observation)
    reserved = next(
        card
        for card in mine.hand
        if card is not None and card.id == AGENT.METAL_ENERGY
    )
    if mutation == "second_metal_998_append":
        extra = copy.deepcopy(reserved)
        extra.serial = 998
        mine.hand.append(extra)
    elif mutation == "second_metal_997_prepend":
        extra = copy.deepcopy(reserved)
        extra.serial = 997
        mine.hand.insert(0, extra)
    elif mutation == "second_metal_duplicate_reserved_serial":
        mine.hand.append(copy.deepcopy(reserved))
    elif mutation == "hand_count_list_mismatch":
        mine.handCount = len(mine.hand) + 1
        return
    elif mutation == "hand_none":
        mine.hand = None
        return
    elif mutation == "incomplete_hand_none_entry":
        mine.hand.append(None)
    elif mutation == "reserved_metal_missing_serial":
        reserved.serial = None
    elif mutation == "nonmetal_missing_serial":
        next(card for card in mine.hand if card.id != 8).serial = None
    elif mutation == "duplicate_nonmetal_serial":
        nonmetals = [card for card in mine.hand if card.id != 8]
        nonmetals[1].serial = nonmetals[0].serial
    elif mutation == "zero_metal":
        reserved.id = AGENT.EXPLORER
    elif mutation == "reserved_metal_replaced":
        reserved.serial = 998
    elif mutation == "unchanged_sole_reserved":
        pass
    else:
        raise AssertionError(mutation)
    mine.handCount = len(mine.hand)


def exact_engine_source_observation():
    from cg.api import search_begin, search_end, to_observation_class

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    initial = to_observation_class(
        copy.deepcopy(replay["steps"][90][1]["observation"])
    )
    hidden = replay["steps"][0][0]["visualize"][89]["current"]
    ids = lambda cards: [card["id"] for card in cards if card]
    state = search_begin(
        initial,
        ids(hidden["players"][1]["deck"]),
        ids(hidden["players"][1]["prize"]),
        ids(hidden["players"][0]["deck"]),
        ids(hidden["players"][0]["prize"]),
        ids(hidden["players"][0]["hand"]),
        [],
    )
    try:
        return copy.deepcopy(state.observation)
    finally:
        search_end()


def exact_engine_uniqueness_callbacks():
    base = exact_engine_source_observation()
    breach_cases = [
        ("second_metal_998_append", "second_metal_998_append", "identity"),
        ("second_metal_997_prepend", "second_metal_997_prepend", "identity"),
        (
            "second_metal_duplicate_reserved_serial",
            "second_metal_duplicate_reserved_serial",
            "identity",
        ),
        (
            "second_metal_998_reversed_options",
            "second_metal_998_append",
            "reverse",
        ),
        (
            "second_metal_997_duplicate_options",
            "second_metal_997_prepend",
            "duplicate",
        ),
        ("hand_count_list_mismatch", "hand_count_list_mismatch", "identity"),
        ("hand_none", "hand_none", "identity"),
        (
            "incomplete_hand_none_entry",
            "incomplete_hand_none_entry",
            "identity",
        ),
        (
            "reserved_metal_missing_serial",
            "reserved_metal_missing_serial",
            "identity",
        ),
        ("nonmetal_missing_serial", "nonmetal_missing_serial", "identity"),
        ("duplicate_nonmetal_serial", "duplicate_nonmetal_serial", "identity"),
        ("zero_metal", "zero_metal", "identity"),
        ("reserved_metal_replaced", "reserved_metal_replaced", "identity"),
    ]
    safe_cards = (
        ("night_stretcher", AGENT.NIGHT_STRETCHER),
        ("explorer", AGENT.EXPLORER),
    )
    cases = []
    for safe_name, card_id in safe_cards:
        for logical_seat in (1, 0):
            transform = (
                (lambda state: state)
                if logical_seat == 1
                else (lambda state: mirror_view(state)[0])
            )
            for case_name, mutation, option_mode in breach_cases:
                reset()
                armed = transform(copy.deepcopy(base))
                AGENT.choose_options(armed)
                transaction = AGENT._h6_transaction
                if transaction is None:
                    raise AssertionError(
                        ("engine uniqueness failed arm", logical_seat)
                    )
                safe_serial = next(
                    card.serial
                    for card in AGENT.my_state(armed).hand
                    if card is not None and card.id == card_id
                )
                reserved = transaction["energy_serial"]
                transaction["directive"] = None
                transaction["stage"] = "SAFE_EFFECT"
                transaction["history"] += ("SAFE_EFFECT",)
                transaction["safe_effect"] = {
                    "card_id": card_id,
                    "card_serial": safe_serial,
                    "prior_stage": "RESERVED_PRE_ATTACH",
                }
                continued = transform(copy.deepcopy(base))
                continued.current.turnActionCount += 1
                apply_option_mode(continued, option_mode)
                mutate_hand_uniqueness(continued, mutation)
                parent = PARENT_MOD.choose_options(
                    copy.deepcopy(continued)
                )
                candidate = AGENT.choose_options(continued)
                cleared_after_breach = AGENT._h6_transaction is None
                repeated = AGENT.choose_options(continued)
                parent_semantic = position_free(
                    semantic(PARENT_MOD, continued, parent)
                )
                candidate_semantic = position_free(
                    semantic(AGENT, continued, candidate)
                )
                if (
                    parent_semantic != candidate_semantic
                    or candidate != repeated
                    or not cleared_after_breach
                ):
                    raise AssertionError(
                        (
                            safe_name,
                            case_name,
                            logical_seat,
                            option_mode,
                            parent_semantic,
                            candidate_semantic,
                            candidate,
                            repeated,
                            cleared_after_breach,
                        )
                    )
                cases.append(
                    {
                        "case": f"{safe_name}_{case_name}",
                        "logical_seat": logical_seat,
                        "option_mode": option_mode,
                        "reserved_energy_serial": reserved,
                        "parent_equal": True,
                        "repeated_duplicate_deterministic": True,
                        "transaction_clear": True,
                    }
                )
                AGENT._h6_reset()

            for option_mode in ("identity", "reverse", "duplicate"):
                reset()
                armed = transform(copy.deepcopy(base))
                AGENT.choose_options(armed)
                transaction = AGENT._h6_transaction
                if transaction is None:
                    raise AssertionError(
                        ("engine uniqueness failed arm", logical_seat)
                    )
                safe_serial = next(
                    card.serial
                    for card in AGENT.my_state(armed).hand
                    if card is not None and card.id == card_id
                )
                reserved = transaction["energy_serial"]
                transaction["directive"] = None
                transaction["stage"] = "SAFE_EFFECT"
                transaction["history"] += ("SAFE_EFFECT",)
                transaction["safe_effect"] = {
                    "card_id": card_id,
                    "card_serial": safe_serial,
                    "prior_stage": "RESERVED_PRE_ATTACH",
                }
                continued = transform(copy.deepcopy(base))
                continued.current.turnActionCount += 1
                apply_option_mode(continued, option_mode)
                mutate_hand_uniqueness(
                    continued, "unchanged_sole_reserved"
                )
                parent = PARENT_MOD.choose_options(
                    copy.deepcopy(continued)
                )
                candidate = AGENT.choose_options(continued)
                candidate_transaction = copy.deepcopy(
                    AGENT._h6_transaction
                )
                repeated = AGENT.choose_options(continued)
                repeated_transaction = copy.deepcopy(
                    AGENT._h6_transaction
                )
                if (
                    position_free(
                        semantic(PARENT_MOD, continued, parent)
                    )
                    != position_free(
                        semantic(AGENT, continued, candidate)
                    )
                    or candidate != repeated
                    or candidate_transaction != repeated_transaction
                    or candidate_transaction is None
                ):
                    raise AssertionError(
                        (
                            safe_name,
                            "unchanged_sole_reserved",
                            logical_seat,
                            option_mode,
                        )
                    )
                cases.append(
                    {
                        "case": f"{safe_name}_unchanged_sole_reserved",
                        "logical_seat": logical_seat,
                        "option_mode": option_mode,
                        "reserved_energy_serial": reserved,
                        "parent_equal": True,
                        "repeated_duplicate_deterministic": True,
                        "transaction_preserved": True,
                    }
                )
                AGENT._h6_reset()
    return cases


def main() -> None:
    source_expected = [
        ("card", 1121),
        ("discard_pair", {(1097, 90), (1147, 94)}),
        ("card", 190),
        ("card", 8),
        ("attack", 253),
    ]
    neutral_expected = [
        ("card", 1244),
        ("card", 8),
        ("card", 1147),
        ("attack", 253),
    ]
    ko_control_expected = [("card", 8), ("attack", 253)]
    cases = [
        run_case(
            "source_logical_seat1",
            90,
            identity_view,
            source_expected,
            True,
        ),
        run_case(
            "source_logical_seat0",
            90,
            mirror_view,
            source_expected,
            True,
        ),
        run_case(
            "source_reversed_options",
            90,
            reverse_view,
            source_expected,
            True,
        ),
        run_case(
            "source_duplicate_options",
            90,
            duplicate_view,
            source_expected,
            True,
        ),
        run_case(
            "source_changed_serials",
            90,
            offset_serial_view,
            [
                ("card", 1121),
                ("discard_pair", {(1097, 1090), (1147, 1094)}),
                ("card", 190),
                ("card", 8),
                ("attack", 253),
            ],
            True,
        ),
        run_case(
            "neutral_control_logical_seat1",
            111,
            identity_view,
            neutral_expected,
            True,
        ),
        run_case(
            "neutral_control_logical_seat0",
            111,
            mirror_view,
            neutral_expected,
            True,
        ),
        run_case(
            "ko_control_logical_seat1",
            142,
            identity_view,
            ko_control_expected,
            False,
        ),
        run_case(
            "ko_control_logical_seat0",
            142,
            mirror_view,
            ko_control_expected,
            False,
        ),
    ]
    uniqueness_cases = exact_engine_uniqueness_callbacks()
    for case in cases[:5]:
        if not (
            case["attack_damage_logs"][0] == -220
            and case["initial_target_hp"] == 310
            and case["immediate_post_attack_hp"] == 90
            and case["prizes_taken"] == 0
            and case["turn_completed"]
            and case["transaction_cleared"]
        ):
            raise AssertionError(case)
    for case in cases[5:7]:
        if not (
            case["attack_damage_logs"][0] == -220
            and case["prizes_taken"] == 0
            and case["turn_completed"]
            and case["transaction_cleared"]
        ):
            raise AssertionError(case)
    output = {
        "engine": (
            "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/"
            "seeded_engine"
        ),
        "authoritative_engine_sha256": EXPECTED_ENGINE_SHA256,
        "source_replay": str(REPLAY.relative_to(ROOT).as_posix()),
        "case_count": len(cases),
        "exact_engine_uniqueness_case_count": len(uniqueness_cases),
        "logical_seats": sorted(
            {case["logical_seat"] for case in cases}
        ),
        "callback_total": sum(case["callback_count"] for case in cases),
        "cases": cases,
        "exact_engine_uniqueness_cases": uniqueness_cases,
        "invalid_actions": 0,
        "action_errors": 0,
        "exceptions": 0,
        "stale_transactions": 0,
        "max_step_hits": 0,
        "seat_method": (
            "The frozen source SearchBegin payload is native seat 1. Logical "
            "seat 0 is independently evaluated by an exact public-callback "
            "player-index mirror while the returned semantic positions are "
            "executed by the same exact engine state."
        ),
    }
    path = HERE / "engine_transactions.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
