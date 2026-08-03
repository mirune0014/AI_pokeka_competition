from __future__ import annotations

import copy
import importlib.util
import json
import os
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
SOURCE_REPLAY = (
    ROOT
    / "archaludon"
    / "evidence"
    / "live_54927163_refresh_20260729_0344"
    / "episode_88584180_replay.json"
)
CORPUS = (
    ROOT
    / "archaludon"
    / "live"
    / "55070349"
    / "refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(CANDIDATE))
AGENT = load_module("h6_focused_candidate", CANDIDATE / "main.py")
REPLAY = json.loads(SOURCE_REPLAY.read_text(encoding="utf-8"))


def reset(last_attack=937):
    AGENT._h6_reset()
    AGENT._opp_last_attack_id = last_attack
    AGENT._cur_turn_logs.clear()


def observation(row):
    return AGENT.to_observation_class(
        copy.deepcopy(REPLAY["steps"][row][1]["observation"])
    )


def cards(observation):
    for player in observation.current.players:
        for card in list(player.hand or ()) + list(player.discard or ()):
            if card:
                yield card
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if not pokemon:
                continue
            yield pokemon
            yield from pokemon.energyCards or ()
            yield from pokemon.tools or ()
            yield from pokemon.preEvolution or ()
    yield from observation.current.stadium or ()
    yield from observation.select.deck or ()
    if observation.select.effect:
        yield observation.select.effect
    if observation.select.contextCard:
        yield observation.select.contextCard


def mirror(observation):
    observation = copy.deepcopy(observation)
    observation.current.players.reverse()
    observation.current.yourIndex = 1 - observation.current.yourIndex
    if observation.current.firstPlayer in (0, 1):
        observation.current.firstPlayer = 1 - observation.current.firstPlayer
    seen = set()
    for card in cards(observation):
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
    return observation


def semantic(observation, selected):
    output = []
    for position in selected:
        option = observation.select.option[position]
        card = AGENT.option_card(observation, option)
        target = AGENT.option_target(observation, option)
        output.append(
            (
                int(option.type),
                getattr(card, "id", None),
                getattr(card, "serial", None),
                getattr(target, "id", None),
                getattr(target, "serial", None),
                option.attackId,
            )
        )
    return output


def parent_and_candidate(observation):
    parent = AGENT._historical_silver_choose_options(observation)
    candidate = AGENT.choose_options(observation)
    return parent, candidate


def permute_semantic_options(observation, mode):
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


def prepare_safe_effect_continuation(logical_seat, card_id, option_mode):
    transform = (lambda state: state) if logical_seat == 1 else mirror
    reset()
    armed = transform(observation(90))
    AGENT.choose_options(armed)
    transaction = AGENT._h6_transaction
    if (
        transaction is None
        or transaction["stage"] != "RESERVED_PRE_ATTACH"
    ):
        raise AssertionError(("safe continuation failed arm", logical_seat))
    serial = next(
        card.serial
        for card in AGENT.my_state(armed).hand
        if card is not None and card.id == card_id
    )
    transaction["directive"] = None
    transaction["stage"] = "SAFE_EFFECT"
    transaction["history"] += ("SAFE_EFFECT",)
    transaction["safe_effect"] = {
        "card_id": card_id,
        "card_serial": serial,
        "prior_stage": "RESERVED_PRE_ATTACH",
    }
    continued = transform(observation(90))
    continued.current.turnActionCount += 1
    permute_semantic_options(continued, option_mode)
    return continued, transaction["energy_serial"]


def mutate_continuation_hand(observation, mutation):
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


def safe_effect_uniqueness_cases():
    rows = []
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
    for safe_name, card_id in safe_cards:
        for logical_seat in (1, 0):
            for case_name, mutation, option_mode in breach_cases:
                state, reserved = prepare_safe_effect_continuation(
                    logical_seat, card_id, option_mode
                )
                mutate_continuation_hand(state, mutation)
                parent = AGENT._historical_silver_choose_options(state)
                candidate = AGENT.choose_options(state)
                cleared_after_breach = AGENT._h6_transaction is None
                repeated = AGENT.choose_options(state)
                if (
                    semantic(state, parent) != semantic(state, candidate)
                    or candidate != repeated
                    or not cleared_after_breach
                ):
                    raise AssertionError(
                        (
                            safe_name,
                            mutation,
                            logical_seat,
                            semantic(state, parent),
                            semantic(state, candidate),
                            candidate,
                            repeated,
                            AGENT._h6_transaction,
                        )
                    )
                rows.append(
                    {
                        "case": f"{safe_name}_{case_name}",
                        "logical_seat": logical_seat,
                        "reserved_energy_serial": reserved,
                        "option_mode": option_mode,
                        "parent_equal": True,
                        "repeated_duplicate_deterministic": True,
                        "transaction_clear": True,
                    }
                )
                AGENT._h6_reset()

            for option_mode in ("identity", "reverse", "duplicate"):
                state, reserved = prepare_safe_effect_continuation(
                    logical_seat, card_id, option_mode
                )
                mutate_continuation_hand(state, "unchanged_sole_reserved")
                parent = AGENT._historical_silver_choose_options(state)
                candidate = AGENT.choose_options(state)
                transaction = copy.deepcopy(AGENT._h6_transaction)
                repeated = AGENT.choose_options(state)
                repeated_transaction = copy.deepcopy(
                    AGENT._h6_transaction
                )
                if (
                    semantic(state, parent) != semantic(state, candidate)
                    or candidate != repeated
                    or transaction != repeated_transaction
                    or transaction is None
                    or transaction["energy_serial"] != reserved
                ):
                    raise AssertionError(
                        (
                            safe_name,
                            "unchanged_sole_reserved",
                            logical_seat,
                            option_mode,
                            semantic(state, parent),
                            semantic(state, candidate),
                            transaction,
                            repeated_transaction,
                        )
                    )
                rows.append(
                    {
                        "case": f"{safe_name}_unchanged_sole_reserved",
                        "logical_seat": logical_seat,
                        "reserved_energy_serial": reserved,
                        "option_mode": option_mode,
                        "parent_equal": True,
                        "repeated_duplicate_deterministic": True,
                        "transaction_preserved": True,
                    }
                )
                AGENT._h6_reset()
    return rows


def remove_attach_options(observation):
    observation.select.option = [
        option
        for option in observation.select.option
        if option.type != AGENT.OptionType.ATTACH
    ]


def mutate_zero_hand_metal(observation):
    mine = AGENT.my_state(observation)
    mine.hand = [card for card in mine.hand if card.id != AGENT.METAL_ENERGY]
    mine.handCount = len(mine.hand)
    remove_attach_options(observation)


def mutate_two_hand_metal(observation):
    mine = AGENT.my_state(observation)
    extra = copy.deepcopy(next(card for card in mine.hand if card.id == 8))
    extra.serial = 998
    mine.hand.append(extra)
    mine.handCount = len(mine.hand)


def mutate_one_active_energy(observation):
    active = AGENT.active_pokemon(observation)
    active.energyCards.pop()
    active.energies.pop()


def mutate_three_active_energy(observation):
    active = AGENT.active_pokemon(observation)
    extra = copy.deepcopy(active.energyCards[-1])
    extra.serial = 998
    active.energyCards.append(extra)
    active.energies.append(8)


def mutate_used_attachment(observation):
    observation.current.energyAttached = True


def mutate_missing_attach(observation):
    remove_attach_options(observation)


def mutate_wrong_target_attach(observation):
    active_serial = AGENT.active_pokemon(observation).serial
    observation.select.option = [
        option
        for option in observation.select.option
        if not (
            option.type == AGENT.OptionType.ATTACH
            and getattr(AGENT.option_target(observation, option), "serial", None)
            == active_serial
        )
    ]


def mutate_active_id(card_id):
    def apply(observation):
        AGENT.active_pokemon(observation).id = card_id

    return apply


def mutate_mixed_energy(observation):
    active = AGENT.active_pokemon(observation)
    active.energyCards[0].id = 7
    active.energies[0] = 7


def mutate_status(name):
    def apply(observation):
        setattr(AGENT.my_state(observation), name, True)

    return apply


def mutate_target(card_id, hp, max_hp):
    def apply(observation):
        target = AGENT.opp_active_pokemon(observation)
        target.id = card_id
        target.hp = hp
        target.maxHp = max_hp
        target.tools = []
        target.preEvolution = []

    return apply


def mutate_ko(observation):
    AGENT.opp_active_pokemon(observation).hp = 200


def mutate_forced_terminal(observation):
    AGENT.active_pokemon(observation).hp = 150
    AGENT.opp_state(observation).prize = [None, None]


def mutate_unknown_stadium(observation):
    observation.current.stadium[0].id = 999999


def mutate_unknown_tool(observation):
    tool = copy.deepcopy(AGENT.my_state(observation).hand[0])
    tool.id = 999999
    tool.serial = 997
    AGENT.opp_active_pokemon(observation).tools = [tool]


def mutate_attack_already_legal(observation):
    mutate_three_active_energy(observation)
    option = copy.deepcopy(
        next(
            item
            for item in observation.select.option
            if item.type == AGENT.OptionType.END
        )
    )
    option.type = AGENT.OptionType.ATTACK
    option.attackId = AGENT.METAL_DEFENDER
    observation.select.option.append(option)


def mutate_bench_only(observation):
    mutate_wrong_target_attach(observation)


def mutate_ultra_insufficient(observation):
    mine = AGENT.my_state(observation)
    keep = {90, 81, 120}
    mine.hand = [card for card in mine.hand if card.serial in keep]
    mine.handCount = len(mine.hand)
    for option in observation.select.option:
        if option.type == AGENT.OptionType.PLAY:
            card = AGENT.option_card(observation, option)
            if card and card.id == AGENT.ULTRA_BALL:
                option.index = next(
                    index
                    for index, item in enumerate(mine.hand)
                    if item.id == AGENT.ULTRA_BALL
                )
        elif option.type == AGENT.OptionType.ATTACH:
            option.index = next(
                index
                for index, item in enumerate(mine.hand)
                if item.id == AGENT.METAL_ENERGY
            )


NEGATIVE_MUTATIONS = [
    ("zero_visible_basic_metal", mutate_zero_hand_metal),
    ("two_visible_basic_metal", mutate_two_hand_metal),
    ("active_one_energy", mutate_one_active_energy),
    ("active_three_energy", mutate_three_active_energy),
    ("manual_attachment_used", mutate_used_attachment),
    ("missing_attachment_option", mutate_missing_attach),
    ("wrong_target_attachment_only", mutate_wrong_target_attach),
    ("active_duraludon", mutate_active_id(169)),
    ("active_nonex_archaludon", mutate_active_id(840)),
    ("active_cinderace", mutate_active_id(666)),
    ("mixed_attached_energy", mutate_mixed_energy),
    ("bench_only_completion", mutate_bench_only),
    ("asleep", mutate_status("asleep")),
    ("paralyzed", mutate_status("paralyzed")),
    ("confused", mutate_status("confused")),
    ("poisoned_uncertainty", mutate_status("poisoned")),
    ("burned_uncertainty", mutate_status("burned")),
    ("cornerstone_prevention", mutate_target(117, 210, 210)),
    ("crustle_prevention", mutate_target(345, 150, 150)),
    ("unknown_target_text", mutate_target(999999, 310, 320)),
    ("projected_ko", mutate_ko),
    ("forced_terminal_loss_route", mutate_forced_terminal),
    ("unknown_stadium", mutate_unknown_stadium),
    ("unknown_tool", mutate_unknown_tool),
    ("attack_already_legal", mutate_attack_already_legal),
    ("ultra_fewer_than_two_nonreserved", mutate_ultra_insufficient),
]


def negative_cases():
    rows = []
    for name, mutation in NEGATIVE_MUTATIONS:
        for logical_seat in (1, 0):
            state = observation(90)
            mutation(state)
            if logical_seat == 0:
                state = mirror(state)
            reset()
            parent, candidate = parent_and_candidate(state)
            if semantic(state, parent) != semantic(state, candidate):
                raise AssertionError((name, logical_seat, parent, candidate))
            if AGENT._h6_transaction is not None:
                raise AssertionError((name, logical_seat, AGENT._h6_transaction))
            rows.append(
                {
                    "case": name,
                    "logical_seat": logical_seat,
                    "parent_equal": True,
                    "transaction_clear": True,
                }
            )

    for name, card_id in (
        ("target_changing_boss_parent", AGENT.BOSS),
        ("unknown_parent_action", 999999),
    ):
        for logical_seat in (1, 0):
            state = observation(90)
            mine = AGENT.my_state(state)
            card = copy.deepcopy(mine.hand[-1])
            card.id = card_id
            card.serial = 996
            mine.hand.append(card)
            mine.handCount = len(mine.hand)
            option = copy.deepcopy(state.select.option[1])
            option.index = len(mine.hand) - 1
            state.select.option.append(option)
            chosen = [len(state.select.option) - 1]
            if logical_seat == 0:
                state = mirror(state)
            reset()
            if AGENT._h6_build_certificate(state, chosen) is not None:
                raise AssertionError((name, logical_seat))
            rows.append(
                {
                    "case": name,
                    "logical_seat": logical_seat,
                    "parent_equal": True,
                    "transaction_clear": True,
                }
            )

    for logical_seat in (1, 0):
        state = observation(90)
        if logical_seat == 0:
            state = mirror(state)
        reset(last_attack=AGENT.METAL_DEFENDER)
        parent, candidate = parent_and_candidate(state)
        if semantic(state, parent) != semantic(state, candidate):
            raise AssertionError(("persistent restriction", logical_seat))
        if AGENT._h6_transaction is not None:
            raise AssertionError(("persistent restriction armed", logical_seat))
        rows.append(
            {
                "case": "unknown_persistent_restriction",
                "logical_seat": logical_seat,
                "parent_equal": True,
                "transaction_clear": True,
            }
        )
    return rows


def positive_and_controls():
    checks = []
    for logical_seat in (1, 0):
        transform = (lambda state: state) if logical_seat == 1 else mirror
        reset()
        row90 = transform(observation(90))
        parent90, candidate90 = parent_and_candidate(row90)
        repeat90 = AGENT.choose_options(row90)
        if (
            semantic(row90, candidate90)
            != [(7, 1121, 81, None, None, None)]
            or candidate90 != repeat90
            or AGENT._h6_transaction["stage"] != "RESERVED_PRE_ATTACH"
        ):
            raise AssertionError(("row90", logical_seat))
        row91 = transform(observation(91))
        parent91, candidate91 = parent_and_candidate(row91)
        repeat91 = AGENT.choose_options(row91)
        if (
            {
                (item[1], item[2]) for item in semantic(row91, candidate91)
            }
            != {(1097, 90), (1147, 94)}
            or candidate91 != repeat91
            or AGENT._h6_transaction["stage"] != "SAFE_EFFECT"
        ):
            raise AssertionError(("row91", logical_seat))
        row92 = transform(observation(92))
        parent92, candidate92 = parent_and_candidate(row92)
        if (
            semantic(row92, parent92) != semantic(row92, candidate92)
            or AGENT._h6_transaction is not None
        ):
            raise AssertionError(("row92 rollback", logical_seat))
        checks.append(
            {
                "case": "source_recorded_branch",
                "logical_seat": logical_seat,
                "row90_parent_equal": semantic(row90, parent90)
                == semantic(row90, candidate90),
                "row91_parent": semantic(row91, parent91),
                "row91_candidate": semantic(row91, candidate91),
                "row92_rollback_equal": True,
            }
        )

        reset()
        expected = {
            111: (7, 1244),
            112: (8, 8),
            113: (7, 1147),
            114: (13, 253),
        }
        control_rows = []
        for row, (option_type, value) in expected.items():
            state = transform(observation(row))
            parent, candidate = parent_and_candidate(state)
            actual = semantic(state, candidate)
            if semantic(state, parent) != actual:
                raise AssertionError(("neutral control", logical_seat, row))
            selected = actual[0]
            actual_value = selected[5] if option_type == 13 else selected[1]
            if selected[0] != option_type or actual_value != value:
                raise AssertionError(("neutral semantic", row, actual))
            control_rows.append(row)
        checks.append(
            {
                "case": "action_neutral_control",
                "logical_seat": logical_seat,
                "rows": control_rows,
                "parent_equal": True,
            }
        )

        reset()
        for row in (142, 143):
            state = transform(observation(row))
            parent, candidate = parent_and_candidate(state)
            if semantic(state, parent) != semantic(state, candidate):
                raise AssertionError(("KO control", logical_seat, row))
            if AGENT._h6_transaction is not None:
                raise AssertionError(("KO control armed", logical_seat, row))
        checks.append(
            {
                "case": "projected_ko_control",
                "logical_seat": logical_seat,
                "rows": [142, 143],
                "parent_equal": True,
                "transaction_clear": True,
            }
        )
    return checks


def rollback_cases():
    rows = []
    mutations = {
        "stored_energy_serial": lambda state: setattr(
            next(card for card in AGENT.my_state(state).hand if card.id == 8),
            "serial",
            997,
        ),
        "active_serial": lambda state: setattr(
            AGENT.active_pokemon(state), "serial", 997
        ),
        "opponent_active_serial": lambda state: setattr(
            AGENT.opp_active_pokemon(state), "serial", 997
        ),
        "active_hp": lambda state: setattr(
            AGENT.active_pokemon(state), "hp", 290
        ),
        "status": lambda state: setattr(
            AGENT.my_state(state), "asleep", True
        ),
        "stadium": lambda state: setattr(
            state.current.stadium[0], "serial", 997
        ),
        "prize": lambda state: AGENT.my_state(state).prize.pop(),
        "target_damage": lambda state: setattr(
            AGENT.opp_active_pokemon(state), "hp", 300
        ),
    }
    for name, mutation in mutations.items():
        for logical_seat in (1, 0):
            transform = (lambda state: state) if logical_seat == 1 else mirror
            reset()
            armed = transform(observation(90))
            AGENT.choose_options(armed)
            if AGENT._h6_transaction is None:
                raise AssertionError(("failed arm", name, logical_seat))
            broken = transform(observation(90))
            mutation(broken)
            broken.current.turnActionCount += 1
            parent = AGENT._historical_silver_choose_options(broken)
            candidate = AGENT.choose_options(broken)
            if semantic(broken, parent) != semantic(broken, candidate):
                raise AssertionError((name, logical_seat, "delegate mismatch"))
            if AGENT._h6_transaction is not None:
                raise AssertionError((name, logical_seat, "stale"))
            rows.append(
                {
                    "case": name,
                    "logical_seat": logical_seat,
                    "parent_equal": True,
                    "transaction_clear": True,
                }
            )

    for logical_seat in (1, 0):
        transform = (lambda state: state) if logical_seat == 1 else mirror
        reset()
        armed = transform(observation(90))
        AGENT.choose_options(armed)
        original = tuple(AGENT.ALL_ATTACKS[253].energies)
        try:
            AGENT.ALL_ATTACKS[253].energies = [8, 8, 8, 8]
            broken = transform(observation(90))
            broken.current.turnActionCount += 1
            parent = AGENT._historical_silver_choose_options(broken)
            candidate = AGENT.choose_options(broken)
        finally:
            AGENT.ALL_ATTACKS[253].energies = list(original)
        if semantic(broken, parent) != semantic(broken, candidate):
            raise AssertionError(("cost mutation", logical_seat))
        if AGENT._h6_transaction is not None:
            raise AssertionError(("cost mutation stale", logical_seat))
        rows.append(
            {
                "case": "attack_cost",
                "logical_seat": logical_seat,
                "parent_equal": True,
                "transaction_clear": True,
            }
        )

    for logical_seat in (1, 0):
        transform = (lambda state: state) if logical_seat == 1 else mirror
        reset()
        for row in (111, 112, 113):
            AGENT.choose_options(transform(observation(row)))
        if AGENT._h6_transaction["stage"] != "ATTACK_READY":
            raise AssertionError(("post attach stage", logical_seat))
        broken = transform(observation(113))
        AGENT.opp_active_pokemon(broken).serial = 997
        broken.current.turnActionCount += 1
        parent = AGENT._historical_silver_choose_options(broken)
        candidate = AGENT.choose_options(broken)
        if semantic(broken, parent) != semantic(broken, candidate):
            raise AssertionError(("irreversible rollback", logical_seat))
        if AGENT._h6_transaction is not None:
            raise AssertionError(("irreversible stale", logical_seat))
        if len(AGENT.active_pokemon(broken).energyCards) != 3:
            raise AssertionError(("attached energy was changed", logical_seat))
        rows.append(
            {
                "case": "post_attachment_irreversible_delegate",
                "logical_seat": logical_seat,
                "parent_equal": True,
                "attached_energy_count": 3,
                "transaction_clear": True,
            }
        )
    return rows


def mandatory_count_and_resets():
    rows = []
    for logical_seat in (1, 0):
        transform = (lambda state: state) if logical_seat == 1 else mirror
        reset()
        AGENT.choose_options(transform(observation(90)))
        discard = transform(observation(91))
        reserved = AGENT._h6_transaction["energy_serial"]
        keep = []
        kept_other = False
        for option in discard.select.option:
            card = AGENT.option_card(discard, option)
            if card.serial == reserved or not kept_other:
                keep.append(option)
                kept_other = kept_other or card.serial != reserved
        discard.select.option = keep
        parent = AGENT._historical_silver_choose_options(discard)
        candidate = AGENT.choose_options(discard)
        if semantic(discard, parent) != semantic(discard, candidate):
            raise AssertionError(("mandatory fallback", logical_seat))
        if len(candidate) != discard.select.minCount:
            raise AssertionError(("mandatory count", logical_seat, candidate))
        if AGENT._h6_transaction is not None:
            raise AssertionError(("mandatory stale", logical_seat))
        rows.append(
            {
                "case": "unavoidable_reserved_mandatory_choice",
                "logical_seat": logical_seat,
                "legal_count": len(candidate),
                "parent_equal": True,
                "transaction_clear": True,
            }
        )

        reset()
        armed = transform(observation(90))
        AGENT.choose_options(armed)
        changed = transform(observation(90))
        changed.current.turn += 1
        AGENT._h6_choose(changed, [])
        if AGENT._h6_transaction is not None:
            raise AssertionError(("turn reset", logical_seat))
        rows.append(
            {
                "case": "turn_reset",
                "logical_seat": logical_seat,
                "transaction_clear": True,
            }
        )

    reset()
    AGENT.choose_options(observation(90))
    prior = pathlib.Path.cwd()
    try:
        os.chdir(CANDIDATE)
        deck = AGENT.agent(
            {
                "select": None,
                "logs": [],
                "current": None,
                "search_begin_input": None,
            }
        )
    finally:
        os.chdir(prior)
    if len(deck) != 60 or AGENT._h6_transaction is not None:
        raise AssertionError(("deck reset", len(deck)))
    rows.append(
        {
            "case": "deck_new_game_reset",
            "deck_count": len(deck),
            "transaction_clear": True,
        }
    )

    reset()
    state = observation(90)
    parent = AGENT._historical_silver_choose_options(state)
    AGENT._h6_transaction = {"sentinel": True}
    original = AGENT._h6_choose
    try:
        AGENT._h6_choose = lambda *_: (_ for _ in ()).throw(
            RuntimeError("injected")
        )
        candidate = AGENT._h6_safe_choose(state, parent)
    finally:
        AGENT._h6_choose = original
    if candidate is not None or AGENT._h6_transaction is not None:
        raise AssertionError("exception did not fail closed")
    rows.append(
        {
            "case": "exception_fail_closed",
            "cached_parent_available": True,
            "transaction_clear": True,
        }
    )

    reset()
    count = {"calls": 0}
    original_parent = AGENT._historical_silver_choose_options
    try:
        def counted(state):
            count["calls"] += 1
            return original_parent(state)

        AGENT._historical_silver_choose_options = counted
        AGENT.choose_options(observation(90))
    finally:
        AGENT._historical_silver_choose_options = original_parent
    if count["calls"] != 1:
        raise AssertionError(("parent call count", count))
    rows.append(
        {
            "case": "cached_parent_once",
            "parent_calls": count["calls"],
        }
    )
    return rows


def sibling_context_negatives():
    rows = []
    sources = [
        (88457867, 1, [144], "H1"),
        (88017509, 1, [114], "H2"),
        (88684114, 0, [20], "H3"),
        (87825800, 1, [116], "H4"),
        (87892692, 0, [48], "H4"),
        (87996118, 1, [96], "H5"),
        (88660007, 1, [78, 79, 80, 81, 82, 83], "H7-A"),
        (88507294, 0, [38, 73, 77], "H7-B"),
    ]
    for episode, seat, source_rows, label in sources:
        replay = json.loads(
            (CORPUS / f"episode_{episode}_replay.json").read_text(
                encoding="utf-8"
            )
        )
        for row in source_rows:
            record = replay["steps"][row][seat]
            obs_dict = record.get("observation")
            if (
                record.get("status") != "ACTIVE"
                or not obs_dict
                or not obs_dict.get("select")
                or not obs_dict["select"].get("option")
            ):
                continue
            base = AGENT.to_observation_class(copy.deepcopy(obs_dict))
            for logical_seat in (seat, 1 - seat):
                state = base if logical_seat == seat else mirror(base)
                reset()
                parent, candidate = parent_and_candidate(state)
                if semantic(state, parent) != semantic(state, candidate):
                    raise AssertionError((label, row, logical_seat))
                if AGENT._h6_transaction is not None:
                    raise AssertionError((label, row, "armed"))
                rows.append(
                    {
                        "case": label,
                        "episode": episode,
                        "row": row,
                        "logical_seat": logical_seat,
                        "parent_equal": True,
                        "transaction_clear": True,
                    }
                )
    return rows


def main():
    positives = positive_and_controls()
    negatives = negative_cases()
    rollbacks = rollback_cases()
    uniqueness = safe_effect_uniqueness_cases()
    resets = mandatory_count_and_resets()
    siblings = sibling_context_negatives()
    output = {
        "positive_and_control_cases": positives,
        "negative_cases": negatives,
        "rollback_cases": rollbacks,
        "safe_effect_uniqueness_cases": uniqueness,
        "mandatory_reset_exception_cases": resets,
        "sibling_context_cases": siblings,
        "positive_case_count": len(positives),
        "negative_case_count": len(negatives),
        "rollback_case_count": len(rollbacks),
        "safe_effect_uniqueness_case_count": len(uniqueness),
        "mandatory_reset_exception_case_count": len(resets),
        "sibling_context_case_count": len(siblings),
        "logical_seats": [0, 1],
        "parent_action_mismatches": 0,
        "invalid_actions": 0,
        "mandatory_count_violations": 0,
        "exceptions": 0,
        "stale_transactions": 0,
    }
    path = HERE / "focused_results.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
